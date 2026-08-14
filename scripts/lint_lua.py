#!/usr/bin/env python3
"""Lint FiveM Lua for native misuse.

  lint_lua.py <path> [...]        lint files or directories
  lint_lua.py <path> --json       machine-readable
  lint_lua.py <path> --side auto  override side detection (auto|client|server|shared)

Checks
  E001  native does not exist (typo / invented)
  E002  client-only native called from server code (or vice versa)
  E003  wrong argument count for the native's signature
  W101  per-frame native in a Wait(0) loop that belongs outside it
  W102  GetGamePool / entity enumeration inside a tight loop
  W103  distance native called per-frame without a cached result

Side is inferred from the filename and from fxmanifest client_script /
server_script blocks when a manifest sits next to the file.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")

# Natives that are expensive enough that a per-frame call is almost always a bug.
HEAVY_PER_FRAME = {
    "GetGamePool": "W102",
    "GetActivePlayers": "W102",
    "GetPlayers": "W102",
    "GetDistanceBetweenCoords": "W103",
    "Vdist": "W103",
    "Vdist2": "W103",
    "GetClosestVehicle": "W102",
    "GetClosestPed": "W102",
    "RequestModel": "W101",
    "RequestAnimDict": "W101",
    "LoadResourceFile": "W101",
}

# Lua-level runtime API provided by the CitizenFX scripting runtime, not by a
# native. These resolve at runtime but never appear in the native database.
RUNTIME_API = {
    "CreateThread", "SetTimeout", "ClearTimeout", "RegisterNetEvent",
    "AddEventHandler", "RemoveEventHandler", "RegisterServerEvent",
    "TriggerEvent", "TriggerServerEvent", "TriggerClientEvent",
    "TriggerLatentClientEvent", "TriggerLatentServerEvent",
    "PerformHttpRequest", "GetPlayers", "GetPlayerIdentifiers",
    "StartServerEvent",
    # Upstream marks WAIT as a client-only GTA native, but the Lua `Wait` is the
    # Citizen scheduler yield and exists on both sides.
    "Wait",
}

# A native is always a bare global call. Anything reached through a table or a
# method (`Bridge.HasItem`, `QBCore:GetCoreObject`) is user code, never a native.
CALL_RE = re.compile(r"(?<![\w.:])([A-Z_][A-Za-z0-9_]{2,})\s*\(")

# Function definitions, so locally declared helpers are not mistaken for natives.
DEF_RES = [
    re.compile(r"\bfunction\s+([A-Za-z_]\w*)\s*\("),
    re.compile(r"\bfunction\s+[\w.]*[.:]([A-Za-z_]\w*)\s*\("),
    re.compile(r"\b([A-Za-z_]\w*)\s*=\s*function\s*[\(<]"),
    re.compile(r"\[\s*['\"]([A-Za-z_]\w*)['\"]\s*\]\s*=\s*function"),
]
COMMENT_RE = re.compile(r"^\s*--")
WAIT0_RE = re.compile(r"\bWait\s*\(\s*0*\s*\)|\bCitizen\.Wait\s*\(\s*0*\s*\)")

_DB = None


def db():
    global _DB
    if _DB is None:
        path = os.path.join(DATA, "natives.merged.json")
        if not os.path.exists(path):
            sys.exit("index missing - run: python scripts/build_index.py --fetch")
        with open(path, encoding="utf-8") as f:
            _DB = json.load(f)
    return _DB


def native_index():
    """Lua identifier -> record. Only Lua-callable spellings."""
    idx = {}
    for key, r in db().items():
        idx[key] = r
        for a in r.get("luaAliases") or []:
            idx.setdefault(a, r)
    return idx


def manifest_sides(root):
    """Map file path fragments to client/server from an fxmanifest, if present."""
    sides = {}
    for name in ("fxmanifest.lua", "__resource.lua"):
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        for kind, side in (
            ("client_scripts?", "client"),
            ("server_scripts?", "server"),
            ("shared_scripts?", "shared"),
        ):
            for m in re.finditer(
                r"\b{}\s*(?:\{{(.*?)\}}|['\"]([^'\"]+)['\"])".format(kind),
                text,
                re.S,
            ):
                block = m.group(1) or m.group(2) or ""
                for f2 in re.findall(r"['\"]([^'\"]+)['\"]", block) or [block]:
                    if f2.strip():
                        sides[f2.strip()] = side
    return sides


def detect_side(path, manifest):
    base = os.path.basename(path).lower()
    rel = path.replace("\\", "/")
    for pattern, side in manifest.items():
        pat = pattern.replace("\\", "/").replace("*", "")
        if pat and pat.rstrip("/") in rel:
            return side
    if "server" in base or "/server/" in rel:
        return "server"
    if "client" in base or "/client/" in rel:
        return "client"
    if "shared" in base or "config" in base:
        return "shared"
    return "unknown"


def split_args(text):
    """Count top-level comma-separated arguments in a call's argument text."""
    if not text.strip():
        return 0
    depth, count, instr, quote, prev = 0, 1, False, "", ""
    for ch in text:
        if instr:
            if ch == quote and prev != "\\":
                instr = False
        elif ch in "\"'":
            instr, quote = True, ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1
        prev = ch
    return count


def extract_call_args(line, start):
    """Return the argument text of a call whose '(' is at index start, or None."""
    depth, instr, quote, prev = 0, False, "", ""
    for i in range(start, len(line)):
        ch = line[i]
        if instr:
            if ch == quote and prev != "\\":
                instr = False
        elif ch in "\"'":
            instr, quote = True, ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return line[start + 1 : i]
        prev = ch
    return None


def _is_test_file(path):
    """Test kosumu dosyasi mi.

    ⚠ TEST TAKLITLERI PROJE API'SI DEGILDIR.
    Cevrimdisi test kosumlari native'leri global olarak taklit eder
    (`TaskWanderInArea = function() end`). Bu tanimlar `collect_definitions`
    tarafindan toplaninca linter o adi "proje fonksiyonu" sayiyor ve
    apiset denetimini HIC yapmiyor.

    Gercek bir vakada bunun bedeli olculdu: `TaskWanderInArea`
    (client-only) bir SUNUCU dosyasinda cagrildi. Test kosumunda ayni
    adin bir taklidi vardi; linter sustu, cevrimdisi testler gecti ve
    hata ancak oyunda ortaya cikti — davranis dongusu her tick'te
    oluyor ve zombiler tamamen spawn olmayi birakiyordu.

    Tek bir taklit eklemek IKI bagimsiz guvenlik agini birden kor etti.
    Kaynak agacinda testler ayri tutuldugu icin yol bazli eleme yeterli.
    """
    q = path.replace("\\", "/").lower()
    if "/tests/" in q or "/test/" in q:
        return True
    base = os.path.basename(q)
    return (base.startswith("test_") or base.endswith("_test.lua")
            or base.startswith("sahte_") or "selftest" in base)


def collect_definitions(files):
    """Every function name declared anywhere in the linted set.

    Test kosumu dosyalari HARIC — gerekcesi `_is_test_file` icinde.
    """
    defined = set()
    for path in files:
        if _is_test_file(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        for rx in DEF_RES:
            defined.update(rx.findall(text))
    return defined


def lint_file(path, idx, side_override=None, manifest=None, defined=frozenset()):
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    side = side_override or detect_side(path, manifest or {})
    findings = []
    loop_depth_until = -1

    for lineno, line in enumerate(lines, 1):
        if COMMENT_RE.match(line):
            continue
        code = line.split("--")[0] if "--" in line and '"' not in line else line
        in_tight_loop = WAIT0_RE.search(code) is not None or lineno <= loop_depth_until
        if WAIT0_RE.search(code):
            loop_depth_until = lineno + 25  # heuristic window for the loop body

        for m in CALL_RE.finditer(code):
            name = m.group(1)
            if name in RUNTIME_API or name in defined:
                continue

            # Cost check first: some hot calls are runtime helpers, not natives.
            if in_tight_loop and name in HEAVY_PER_FRAME:
                findings.append(
                    {
                        "rule": HEAVY_PER_FRAME[name],
                        "file": path,
                        "line": lineno,
                        "native": name,
                        "message": "{} called inside a Wait(0) loop - hoist it or cache the result".format(name),
                    }
                )

            rec = idx.get(name)

            # ==================================================================
            # ⚠ FIVEM'IN LUA ADI ALT CIZGI TASIYABILIR — VERITABANI TASIMAZ
            # ==================================================================
            # Native veritabani RESMI adi tutuyor (`GET_GROUND_Z_FOR_3D_COORD`
            # -> `GetGroundZFor3dCoord`), ama FiveM'in Lua'ya actigi ad
            # rakamla baslayan parcadan once ALT CIZGI aliyor:
            #     GetGroundZFor_3dCoord      (Lua'da gecerli olan bu)
            #     GetHeadingFromVector_2d    (Lua'da gecerli olan bu)
            #
            # Bu fark iki yonlu zarar veriyordu:
            #   1. Alt cizgili DOGRU adlar E001 diye raporlanyordu
            #      (bilinen yanlis pozitif, elle gormezden geliniyordu).
            #   2. Daha kotusu: o yanlis pozitife guvenip alt cizgisiz
            #      hali "dogru" sanildi ve koda yazildi. Oyunda
            #      `attempt to call a nil value (global
            #      'GetHeadingFromVector2d')` ile coktu — yani linter
            #      dogru kodu reddederken YANLIS kodu onaylamis oldu.
            #
            # Kural: alt cizgiler atildiginda bilinen bir native'e
            # esitse ad GECERLIDIR ve apiset denetimi o kayit uzerinden
            # yapilir.
            if rec is None and "_" in name:
                sade = name.replace("_", "")
                rec = idx.get(sade)
                if rec is None:
                    for k in idx:
                        if k.lower() == sade.lower():
                            rec = idx[k]
                            break

            if rec is None:
                # Only flag identifiers that look like natives, not user functions.
                if name in idx or not re.match(r"^(Get|Set|Is|Has|Does|Draw|Create|Request|Network|Add|Remove|Start|Stop|Clear|Task|Play)[A-Z]", name):
                    continue
                import difflib

                close = difflib.get_close_matches(name, list(idx), n=3, cutoff=0.8)
                findings.append(
                    {
                        "rule": "E001",
                        "file": path,
                        "line": lineno,
                        "native": name,
                        "message": "{} is not a native".format(name)
                        + (" - did you mean {}?".format(", ".join(close)) if close else ""),
                    }
                )
                continue

            if side in ("client", "server") and rec["apiset"] not in (side, "shared"):
                findings.append(
                    {
                        "rule": "E002",
                        "file": path,
                        "line": lineno,
                        "native": name,
                        "message": "{} is {}-only but this file is {} code".format(
                            name, rec["apiset"], side
                        ),
                    }
                )

            argtext = extract_call_args(code, m.end() - 1)
            if argtext is not None:
                got = split_args(argtext)
                want = len(rec["params"])
                signature = "{}({})".format(
                    rec["lua"],
                    ", ".join(
                        "{} {}".format(p.get("type", "?"), p.get("name", "?"))
                        for p in rec["params"]
                    ),
                )
                # Passing extra arguments is always wrong. Passing fewer is a
                # widespread FiveM idiom (trailing args arrive as nil/0), so it
                # only warrants a warning.
                if got > want:
                    findings.append(
                        {
                            "rule": "E003",
                            "file": path,
                            "line": lineno,
                            "native": name,
                            "message": "takes {} argument(s), got {} - {}".format(
                                want, got, signature
                            ),
                        }
                    )
                elif got < want:
                    findings.append(
                        {
                            "rule": "W104",
                            "file": path,
                            "line": lineno,
                            "native": name,
                            "message": "takes {} argument(s), got {} - trailing args default to nil/0 - {}".format(
                                want, got, signature
                            ),
                        }
                    )
    return side, findings


def collect(paths):
    files = []
    for p in paths:
        if os.path.isfile(p) and p.endswith(".lua"):
            files.append(p)
        elif os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "stream")]
                for n in names:
                    if n.endswith(".lua"):
                        files.append(os.path.join(root, n))
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--side", choices=["auto", "client", "server", "shared"], default="auto")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    idx = native_index()
    files = collect(args.paths)
    if not files:
        sys.exit("no .lua files found")

    defined = collect_definitions(files)
    all_findings = []
    for path in files:
        manifest = manifest_sides(os.path.dirname(path)) or manifest_sides(
            os.path.dirname(os.path.dirname(path))
        )
        override = None if args.side == "auto" else args.side
        side, findings = lint_file(path, idx, override, manifest, defined)
        all_findings.extend(findings)

    if args.json:
        print(json.dumps(all_findings, indent=1))
    else:
        errors = [f for f in all_findings if f["rule"].startswith("E")]
        warns = [f for f in all_findings if f["rule"].startswith("W")]
        for f in sorted(all_findings, key=lambda x: (x["file"], x["line"])):
            print("{}:{}: {} {}".format(f["file"], f["line"], f["rule"], f["message"]))
        print(
            "\n{} file(s), {} error(s), {} warning(s)".format(
                len(files), len(errors), len(warns)
            )
        )
    sys.exit(1 if any(f["rule"].startswith("E") for f in all_findings) else 0)


if __name__ == "__main__":
    main()
