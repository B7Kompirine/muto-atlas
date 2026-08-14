#!/usr/bin/env python3
"""Build the merged native index from upstream Cfx data.

Sources (all fetched live with --fetch, otherwise read from data/):
  data/natives_gta5.json  <- https://runtime.fivem.net/doc/natives.json
  data/natives_cfx.json   <- https://runtime.fivem.net/doc/natives_cfx.json
  data/server_extra.json  <- names extracted from citizenfx/fivem source

Outputs:
  data/natives.merged.json  full detail, keyed by Lua name
  data/natives.index.tsv    one line per native, for fast grep
  data/meta.json            provenance + counts

Usage:
  python build_index.py            # rebuild from local data/
  python build_index.py --fetch    # re-download upstream first
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")

SOURCES = {
    "natives_gta5.json": "https://runtime.fivem.net/doc/natives.json",
    "natives_cfx.json": "https://runtime.fivem.net/doc/natives_cfx.json",
}
# Server-side GTA natives registered outside the CFX declaration set.
SERVER_SRC = (
    "https://raw.githubusercontent.com/citizenfx/fivem/master/code/components/"
    "citizen-server-impl/src/state/ServerGameState_Scripting.cpp"
)


def fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "fivem-natives-plugin"})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    with open(dest, "wb") as f:
        f.write(body)
    return len(body)


def lua_name(native_name, hash_):
    """Convert a native name to the identifier Lua/JS actually calls."""
    if not native_name:
        return "N_" + hash_.lower()
    lead = len(native_name) - len(native_name.lstrip("_"))
    core = native_name.lstrip("_")
    parts = [p for p in core.split("_") if p]
    out = "".join(p[0].upper() + p[1:].lower() for p in parts)
    return "_" * lead + out


def param_sig(params):
    return ", ".join(
        "{} {}".format(p.get("type", "?"), p.get("name", "?")) for p in params
    )


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def build(do_fetch=False):
    if do_fetch:
        for name, url in SOURCES.items():
            size = fetch(url, os.path.join(DATA, name))
            print("fetched {} ({} bytes)".format(name, size))
        cpp = os.path.join(DATA, "_ServerGameState_Scripting.cpp")
        fetch(SERVER_SRC, cpp)
        with open(cpp, encoding="utf-8", errors="replace") as f:
            names = sorted(set(re.findall(r'RegisterNativeHandler\("([A-Z0-9_]+)"', f.read())))
        os.remove(cpp)
        with open(os.path.join(DATA, "server_extra.json"), "w", encoding="utf-8") as f:
            json.dump({"source": SERVER_SRC, "names": names}, f, indent=1)
        print("extracted {} server-registered names".format(len(names)))

    gta = load("natives_gta5.json")
    cfx = load("natives_cfx.json")
    try:
        server_extra = set(load("server_extra.json")["names"])
    except (OSError, KeyError, ValueError):
        server_extra = set()

    merged = {}
    collisions = 0

    def add(entry, source):
        nonlocal collisions
        name = entry.get("name")
        key = lua_name(name, entry["hash"])
        rec = merged.get(key)
        if rec is None:
            rec = {
                "lua": key,
                "name": name or ("N_" + entry["hash"].lower()),
                "ns": entry.get("ns", ""),
                "hash": entry["hash"],
                "cfxApiset": entry.get("apiset") or "",
                "game": entry.get("game", ""),
                "results": entry.get("results", "void"),
                "resultsDescription": entry.get("resultsDescription", ""),
                "params": entry.get("params", []),
                "description": (entry.get("description") or "").strip(),
                "examples": entry.get("examples", []),
                "aliases": entry.get("aliases", []),
                "sources": [source],
            }
            merged[key] = rec
            return
        collisions += 1
        rec["sources"].append(source)
        # CFX declaration is authoritative for apiset; GTA doc is usually richer prose.
        if entry.get("apiset"):
            rec["cfxApiset"] = entry["apiset"]
        if entry.get("game") and not rec["game"]:
            rec["game"] = entry["game"]
        if not rec["description"] and entry.get("description"):
            rec["description"] = entry["description"].strip()
        if not rec["params"] and entry.get("params"):
            rec["params"] = entry["params"]
        if not rec["examples"] and entry.get("examples"):
            rec["examples"] = entry["examples"]
        if entry["hash"] != rec["hash"]:
            rec.setdefault("altHash", []).append(entry["hash"])

    for ns, natives in gta.items():
        for entry in natives.values():
            add(entry, "gta5")
    for ns, natives in cfx.items():
        for entry in natives.values():
            add(entry, "cfx")

    # Resolve which side each native is callable on. Upstream marks a Cfx declaration
    # "server" even when the same native also exists in the GTA V client set, so the
    # two sides have to be unioned rather than overwritten.
    extra_applied = 0
    for rec in merged.values():
        cfx_set = rec.pop("cfxApiset", "")
        on_client = "gta5" in rec["sources"] or cfx_set in ("client", "shared")
        on_server = cfx_set in ("server", "shared")
        if not on_server and rec["name"] in server_extra:
            on_server = True
            rec["sources"].append("server-src")
            extra_applied += 1
        rec["apiset"] = (
            "shared" if on_client and on_server else "server" if on_server else "client"
        )
        # Aliases ship in NATIVE_CASE; callers write them in Lua case.
        rec["luaAliases"] = sorted(
            {lua_name(a, rec["hash"]) for a in (rec.get("aliases") or [])} - {rec["lua"]}
        )

    out_full = os.path.join(DATA, "natives.merged.json")
    with open(out_full, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, separators=(",", ":"))

    lines = ["# lua\tnative\tns\tapiset\thash\treturns\tparams"]
    for key in sorted(merged):
        r = merged[key]
        lines.append(
            "\t".join(
                [
                    r["lua"],
                    r["name"],
                    r["ns"],
                    r["apiset"],
                    r["hash"],
                    r["results"],
                    param_sig(r["params"]),
                ]
            )
        )
    out_idx = os.path.join(DATA, "natives.index.tsv")
    with open(out_idx, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    counts = {"client": 0, "server": 0, "shared": 0}
    for r in merged.values():
        counts[r["apiset"]] = counts.get(r["apiset"], 0) + 1
    meta = {
        "builtAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": dict(SOURCES, server_extra=SERVER_SRC),
        "total": len(merged),
        "apiset": counts,
        "mergedDuplicates": collisions,
        "serverExtraApplied": extra_applied,
        "note": (
            "GTA V natives carry no apiset upstream; docs.fivem.net treats them as "
            "client-only. Server availability comes from the CFX declaration set plus "
            "handlers registered in ServerGameState_Scripting.cpp."
        ),
    }
    with open(os.path.join(DATA, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)

    print(json.dumps(meta, indent=1))
    return meta


if __name__ == "__main__":
    build(do_fetch="--fetch" in sys.argv)
