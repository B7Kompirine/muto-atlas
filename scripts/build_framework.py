#!/usr/bin/env python3
"""build_framework.py — FiveM framework API index (exports / events / functions).

  python scripts/build_framework.py --resources <server resources folder>

WHY IT EXISTS
-------------
Today lint_lua.py only verifies GTA NATIVES. But in a QBCore/ox resource most
errors are not in natives, they are in FRAMEWORK calls:

    exports['qb-core']:GetCoreObj()          -- typo, returns nil
    TriggerServerEvent('qb-inventory:server:closeInv')  -- event that does not exist, silent
    lib.showTextUI(...)                       -- ox_lib module misspelled

None of these THROWS an error. When the event does not exist the trigger silently
goes nowhere; when the export does not exist `nil value` only blows up when that
line RUNS - and in game that line may run once a month.

CHOICE OF AUTHORITY (important)
-------------------------------
This index is built from the resources INSTALLED ON THE SERVER, not from upstream
GitHub. Reason: upstream master and the installed version are not the same. If an
export was added upstream but does not exist in your qb-core, calling it "valid"
misleads. The installed version is the only valid authority. The `version` field
of the fxmanifest is recorded too.

DEFINED vs USED
---------------
The `kind` column separates two classes:
  export/event/function  -> DEFINITION (this resource provides it) = AUTHORITY
  export_use/event_use   -> USE (this resource calls it)            = CANDIDATE
A use that matches no definition is suspicious. But do not call it an "error"
automatically: the definition may be in another resource, in another language
(JS/C#) or generated at runtime. So the lint side produces a WARNING, not an ERROR.
"""
from __future__ import annotations

import argparse
import datetime
import gzip
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
OUT = os.path.join(DATA, "framework_api.tsv.gz")

COLS = ["resource", "kind", "name", "side", "file", "line", "version"]

# --- patterns ---------------------------------------------------------------
# In Lua the quote can be single or double; catch both.
Q = r"""['"]([^'"]+)['"]"""

DEFINITIONS = [
    ("export", re.compile(r"\bexports\(\s*" + Q)),                 # exports('name', fn)
    ("event", re.compile(r"\bRegisterNetEvent\(\s*" + Q)),
    ("event", re.compile(r"\bAddEventHandler\(\s*" + Q)),
    ("command", re.compile(r"\bRegisterCommand\(\s*" + Q)),
    ("command", re.compile(r"\blib\.addCommand\(\s*" + Q)),
    ("callback", re.compile(r"\blib\.callback\.register\(\s*" + Q)),
    ("callback", re.compile(r"CreateCallback\(\s*" + Q)),          # QBCore.Functions.CreateCallback
]

USES = [
    ("event_use", re.compile(r"\bTriggerServerEvent\(\s*" + Q)),
    ("event_use", re.compile(r"\bTriggerClientEvent\(\s*" + Q)),
    ("event_use", re.compile(r"\bTriggerEvent\(\s*" + Q)),
    ("callback_use", re.compile(r"\blib\.callback\(\s*" + Q)),
    ("callback_use", re.compile(r"TriggerCallback\(\s*" + Q)),
]

# exports.<resource>:<name>(   and   exports['<resource>']:<name>(
EXP_USE = re.compile(r"\bexports(?:\.(\w+)|\[\s*['\"]([\w-]+)['\"]\s*\])\s*:\s*(\w+)")
# lib.<module>  (ox_lib)
LIB_USE = re.compile(r"\blib\.(\w+)")

COMMENT = re.compile(r"^\s*--")


def manifest_info(root):
    """Version + which file is on which side, from the fxmanifest.

    The side is taken from the manifest, NOT from the file name: 'main.lua' can be
    both client and server, and guessing from the name silently assigns the wrong side.
    """
    version, sides = "", {}
    for name in ("fxmanifest.lua", "__resource.lua"):
        p = os.path.join(root, name)
        if not os.path.exists(p):
            continue
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        m = re.search(r"^\s*version\s+['\"]([^'\"]+)['\"]", t, re.M)
        if m:
            version = m.group(1)
        for block, side in (("client_scripts?", "client"), ("server_scripts?", "server"),
                            ("shared_scripts?", "shared")):
            for mb in re.finditer(block + r"\s*\{(.*?)\}", t, re.S):
                for f in re.findall(Q, mb.group(1)):
                    sides[f.replace("\\", "/").lower()] = side
            for mb in re.finditer(block + r"\s+" + Q, t):
                sides[mb.group(1).replace("\\", "/").lower()] = side
        break
    return version, sides


def find_side(rel, side_map):
    """Manifest match; glob (*) patterns are matched roughly too."""
    r = rel.replace("\\", "/").lower()
    if r in side_map:
        return side_map[r]
    for pattern, side in side_map.items():
        if "*" in pattern:
            rx = re.escape(pattern).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
            if re.fullmatch(rx, r):
                return side
    # If the manifest is silent, FALL BACK to the name hint, but mark it as 'shared':
    # a wrong side assignment does more harm than having no side information.
    if "/server" in r or r.startswith("server"):
        return "server"
    if "/client" in r or r.startswith("client"):
        return "client"
    return "shared"


# An UNQUOTED first argument such as exports(index, value) = a dynamic export loop.
# ox_target does exactly this:  for index, value in pairs(api) do exports(index, value) end
DYNAMIC_EXPORT = re.compile(r"\bexports\(\s*(?!['\"])\w+\s*,")
# function api.addBoxZone(...)  /  function Core.GetPlayer(...)
TABLE_FN = re.compile(r"^\s*function\s+(\w+)\.(\w+)\s*\(")


def scan(resource_root):
    resource = os.path.basename(resource_root)
    version, side_map = manifest_info(resource_root)
    rows = []
    # First check for a dynamic export: if there is one, the table functions are exports too.
    # ⛔ This was measured: ox_target's 30+ real exports ('addBoxZone', 'addLocalEntity',
    # 'removeZone'...) NEVER appear with a literal quote; they are only defined as
    # `function api.X(` and handed out in the loop. A check that does not know this
    # pattern flags them as "undefined export" and the rule becomes unusable.
    dynamic = False
    for dirp, dirs, files in os.walk(resource_root):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "stream", "web")]
        for f in files:
            if f.endswith(".lua"):
                try:
                    if DYNAMIC_EXPORT.search(open(os.path.join(dirp, f), encoding="utf-8",
                                                  errors="replace").read()):
                        dynamic = True
                        break
                except Exception:
                    pass
        if dynamic:
            break
    for dirp, dirs, files in os.walk(resource_root):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "stream", "web")]
        for f in files:
            if not f.endswith(".lua"):
                continue
            full = os.path.join(dirp, f)
            rel = os.path.relpath(full, resource_root).replace("\\", "/")
            side = find_side(rel, side_map)
            try:
                text = open(full, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for i, line in enumerate(text.split("\n"), 1):
                if COMMENT.match(line):
                    continue
                for kind, rx in DEFINITIONS:
                    for m in rx.finditer(line):
                        rows.append([resource, kind, m.group(1), side, rel, str(i), version])
                for kind, rx in USES:
                    for m in rx.finditer(line):
                        rows.append([resource, kind, m.group(1), side, rel, str(i), version])
                for m in EXP_USE.finditer(line):
                    target = m.group(1) or m.group(2)
                    rows.append([resource, "export_use", f"{target}:{m.group(3)}",
                                 side, rel, str(i), version])
                for m in LIB_USE.finditer(line):
                    rows.append([resource, "lib_use", m.group(1), side, rel, str(i), version])
                if dynamic:
                    m = TABLE_FN.match(line)
                    if m:
                        rows.append([resource, "export", m.group(2), side, rel, str(i), version])
    return rows


LIB_DEF = re.compile(r"(?:function\s+lib\.(\w+)\s*\(|\blib\.(\w+)\s*=)")


def oxlib_modules(root):
    """The REAL API surface of ox_lib.

    ⛔ MEASURED PITFALL: counting only the `imports/` subfolders is WRONG.
    imports/ gives 59 folders, but most of the real functions are defined under
    `resource/` - `lib.notify` lives there
    (resource/interface/client/notify.lua:33). The first version, which only
    looked at imports/, flagged 46.8% of 2216 `lib.*` calls as "module does not
    exist"; `lib.notify` alone is used 380 times. A linter that complains about
    everything becomes unusable, and you miss the REAL errors too.

    The right way: collect the `function lib.X(` and `lib.X =` definitions across
    the whole tree and add the imports/ folders (the UNION of both).
    """
    out, seen = [], set()
    version, _ = manifest_info(root)

    imp = os.path.join(root, "imports")
    if os.path.isdir(imp):
        for d in sorted(os.listdir(imp)):
            if os.path.isdir(os.path.join(imp, d)):
                seen.add(d.lower())
                out.append(["ox_lib", "lib_module", d, "shared", f"imports/{d}", "0", version])

    for dirp, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "web")]
        for f in files:
            if not f.endswith(".lua"):
                continue
            full = os.path.join(dirp, f)
            rel = os.path.relpath(full, root).replace("\\", "/")
            side = "server" if "/server" in "/" + rel else ("client" if "/client" in "/" + rel else "shared")
            try:
                text = open(full, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for i, line in enumerate(text.split("\n"), 1):
                if COMMENT.match(line):
                    continue
                for m in LIB_DEF.finditer(line):
                    name = m.group(1) or m.group(2)
                    if not name or name.startswith("__") or name.lower() in seen:
                        continue
                    seen.add(name.lower())
                    out.append(["ox_lib", "lib_module", name, side, rel, str(i), version])
    return out


def main():
    ap = argparse.ArgumentParser(description="FiveM framework API index")
    ap.add_argument("--resources", required=True, help="server resources folder")
    ap.add_argument("--only", nargs="*", help="only these resources")
    a = ap.parse_args()

    if not os.path.isdir(a.resources):
        sys.exit(f"ERROR: resources folder not found: {a.resources}")

    # Resource = every folder with an fxmanifest in it ([category] folders included).
    roots = []
    for dirp, dirs, files in os.walk(a.resources):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "stream")]
        if "fxmanifest.lua" in files or "__resource.lua" in files:
            roots.append(dirp)
            dirs[:] = []
    if a.only:
        selected = {x.lower() for x in a.only}
        roots = [k for k in roots if os.path.basename(k).lower() in selected]

    print(f"Resources to scan: {len(roots)}")
    all_rows = []
    for k in sorted(roots):
        name = os.path.basename(k)
        version, _ = manifest_info(k)
        # ⛔ THE INSTALLED RESOURCE LIST IS WRITTEN SEPARATELY.
        # Deriving the installed set from the rows is WRONG: a resource that defines no
        # export/event produces zero rows and looks "not installed". This is exactly
        # what happened. No rows is NOT the same as no resource.
        all_rows.append([name, "resource", name, "shared", os.path.relpath(k, a.resources).replace("\\", "/"),
                         "0", version])
        r = scan(k)
        if name == "ox_lib":
            r += oxlib_modules(k)
        all_rows += r

    tmp = OUT + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(COLS) + "\n")
        for r in all_rows:
            fh.write("\t".join(x.replace("\t", " ") for x in r) + "\n")
    with gzip.open(tmp, "rt", encoding="utf-8") as fh:
        head = fh.readline().rstrip("\n").split("\t")
        n = sum(1 for _ in fh)
    if head != COLS or n != len(all_rows):
        os.remove(tmp)
        sys.exit(f"ERROR: read-back did not match ({n} vs {len(all_rows)})")
    os.replace(tmp, OUT)

    counts = {}
    for r in all_rows:
        counts[r[1]] = counts.get(r[1], 0) + 1
    print(f"\n  framework_api.tsv.gz  {n} rows  {os.path.getsize(OUT)/1024:.1f} KB")
    for k in sorted(counts, key=lambda x: -counts[x]):
        print(f"    {k:<14} {counts[k]:>6}")

    meta_p = os.path.join(DATA, "dumps.meta.json")
    meta = {}
    if os.path.exists(meta_p):
        try:
            meta = json.load(open(meta_p, encoding="utf-8"))
        except Exception:
            meta = {}
    meta.setdefault("rows", {})["framework_api"] = n
    meta["frameworkScannedAtUtc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    meta["frameworkSource"] = a.resources
    meta["frameworkResources"] = len(roots)
    with open(meta_p, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
