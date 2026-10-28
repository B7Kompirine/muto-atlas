#!/usr/bin/env python3
"""Query the FiveM native database.

  nativedb.py check  <name> [...]      exists? which side? (hallucination guard)
  nativedb.py show   <name> [...]      full signature, docs, params, examples
  nativedb.py search <query>           substring/keyword search
  nativedb.py ns     [NAMESPACE]       list namespaces, or natives in one
  nativedb.py stats                    index counts + provenance

Common flags:
  --apiset client|server|shared   restrict to natives callable on that side
  --ns NAMESPACE                  restrict to a namespace
  --limit N                       cap results (default 25)
  --json                          machine-readable output
"""
import argparse
import difflib
import json
import os
import sys
from i18n import t
from native_names import binding_record, callable_index, load_database, reference_record

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
DOCS = "https://docs.fivem.net/natives/?_{}"

_DB = None


def db():
    global _DB
    if _DB is None:
        path = os.path.join(DATA, "natives.merged.json")
        _DB = load_database(path)
    return _DB


def lookup_map():
    """Every accepted spelling -> canonical Lua key."""
    m = {}
    for key, r in db().items():
        if r["luaVerified"]:
            for name in r["luaBindings"]:
                m[name.lower()] = key
    for key, r in db().items():
        m.setdefault(r["name"].lower(), key)
        m[r["hash"].lower()] = key
        m["0x{:016x}".format(int(r["hash"], 16))] = key
        for a in r.get("aliases") or []:
            m.setdefault(a.lower(), key)
        for h in r.get("altHash") or []:
            m.setdefault(h.lower(), key)
            m.setdefault("0x{:016x}".format(int(h, 16)), key)
    return m


def sig(r):
    if not r["luaVerified"]:
        return t("native_no_lua_wrapper", native=r["name"])
    params = ", ".join(
        "{} {}".format(p.get("type", "?"), p.get("name", "?")) for p in r["params"]
    )
    return "{}({}) -> {}".format(r["lua"], params, r.get("results") or "void")


def side_note(r):
    return {
        "client": "client-only (client.lua)",
        "server": "server-only (server.lua)",
        "shared": "client + server",
    }[r["apiset"]]


def resolve(name, m):
    if name.lower().startswith("0x"):
        try:
            key = m.get("0x{:016x}".format(int(name, 16)))
            if key:
                return key, []
        except ValueError:
            pass
    key = m.get(name.lower())
    if key:
        return key, []
    # A native is reachable under several spellings, so dedupe to canonical keys.
    close, seen = [], set()
    for c in difflib.get_close_matches(name.lower(), list(m), n=12, cutoff=0.72):
        key = m[c]
        if key not in seen and db()[key]["luaVerified"]:
            seen.add(key)
            close.append(db()[key]["lua"])
    return None, close[:5]


def cmd_check(args):
    m = lookup_map()
    callable_names = callable_index(db(), args.apiset)
    out, ok = [], True
    for name in args.names:
        key, close = resolve(name, m)
        r = callable_names.get(name)
        if r is None and key and name.lower().startswith("0x") and db()[key]["luaVerified"]:
            source = db()[key]
            r = reference_record(source, name, args.apiset)
        if r and r["luaVerified"] and (not args.apiset or r["apiset"] in (args.apiset, "shared")):
            out.append(
                {
                    "query": name,
                    "exists": True,
                    "lua": r["lua"],
                    "apiset": r["apiset"],
                    "ns": r["ns"],
                    "hash": r["hash"],
                    "signature": sig(r),
                    "paramCount": len(r["params"]),
                }
            )
        else:
            ok = False
            if key and db()[key]["luaVerified"]:
                close = [db()[key]["lua"]]
            out.append({"query": name, "exists": False, "suggestions": close})
    if args.json:
        print(json.dumps(out, indent=1))
    else:
        for o in out:
            if o["exists"]:
                print("OK    {}  [{}]  {}".format(o["lua"], o["apiset"], o["ns"]))
                print("      {}".format(o["signature"]))
            else:
                print("FAIL  " + t("native_lua_not_callable", name=o["query"]))
                if o["suggestions"]:
                    print("      did you mean: {}".format(", ".join(o["suggestions"])))
                else:
                    print("      no close match - do not invent this native")
    return 0 if ok else 1


def cmd_show(args):
    m = lookup_map()
    callable_names = callable_index(db(), args.apiset)
    for name in args.names:
        key, close = resolve(name, m)
        if not key:
            print("FAIL  {} does not exist".format(name))
            if close:
                print("      did you mean: {}".format(", ".join(close)))
            continue
        r = db()[key]
        if r["luaVerified"]:
            r = callable_names.get(name) or reference_record(r, name, args.apiset)
        if args.json:
            print(json.dumps(r, indent=1, ensure_ascii=False))
            continue
        print("=" * 70)
        print(sig(r))
        print("native    {}".format(r["name"]))
        print("namespace {}".format(r["ns"]))
        print("apiset    {} -> {}".format(r["apiset"], side_note(r)))
        print("hash      {}".format(r["hash"]))
        print("docs      {}".format(DOCS.format(r["hash"])))
        aliases = [alias for alias in r["luaAliases"] if not alias.startswith("N_0x")]
        if aliases:
            print("{}   {}".format(t("native_lua_aliases"), ", ".join(aliases)))
        if r.get("description"):
            print("\n{}".format(r["description"].strip()))
        if r["params"]:
            print("\nparams:")
            for p in r["params"]:
                desc = (p.get("description") or "").strip().replace("\n", " ")
                print(
                    "  {:<22} {:<12} {}".format(
                        p.get("name", "?"), p.get("type", "?"), desc
                    )
                )
        if r.get("resultsDescription"):
            print("\nreturns: {}".format(r["resultsDescription"].strip()))
        for ex in r.get("examples") or []:
            if ex.get("lang") == "lua":
                print("\nlua example:\n{}".format(ex.get("code", "").strip()))
                break
    return 0


def matches(r, args):
    if not r["luaVerified"]:
        return False
    if args.apiset:
        want = args.apiset
        if want == "server" and r["apiset"] not in ("server", "shared"):
            return False
        if want == "client" and r["apiset"] not in ("client", "shared"):
            return False
        if want == "shared" and r["apiset"] != "shared":
            return False
    if args.ns and r["ns"].upper() != args.ns.upper():
        return False
    return True


def cmd_search(args):
    terms = [t.lower() for t in args.query]
    hits = []
    for r in db().values():
        if r["luaVerified"]:
            r = binding_record(r, r["lua"], args.apiset)
        if not matches(r, args):
            continue
        hay = "{} {} {}".format(r["lua"], r["ns"], r.get("description", "")).lower()
        if all(t in hay for t in terms):
            # Rank: name match beats description match.
            score = 0 if all(t in r["lua"].lower() for t in terms) else 1
            hits.append((score, len(r["lua"]), r))
    hits.sort(key=lambda h: (h[0], h[1]))
    hits = hits[: args.limit]
    if args.json:
        print(json.dumps([h[2] for h in hits], indent=1, ensure_ascii=False))
        return 0
    if not hits:
        print("no match")
        return 1
    for _, _, r in hits:
        print("{:<10} {:<14} {}".format(r["apiset"], r["ns"], sig(r)))
    print("\n{} shown. use `show <name>` for full docs.".format(len(hits)))
    return 0


def cmd_ns(args):
    if not args.namespace:
        counts = {}
        for r in db().values():
            if not r["luaVerified"]:
                continue
            counts.setdefault(r["ns"], []).append(r["apiset"])
        for ns in sorted(counts):
            sides = counts[ns]
            srv = sum(1 for s in sides if s in ("server", "shared"))
            print("{:<16} {:>5} natives  ({} server-callable)".format(ns, len(sides), srv))
        return 0
    want = args.namespace.upper()
    records = [binding_record(r, r["lua"], args.apiset) for r in db().values() if r["luaVerified"]]
    rows = [r for r in records if r["ns"].upper() == want and matches(r, args)]
    if not rows:
        print("unknown namespace: {}".format(args.namespace))
        return 1
    for r in sorted(rows, key=lambda x: x["lua"])[: args.limit]:
        print("{:<10} {}".format(r["apiset"], sig(r)))
    print("\n{} of {} shown.".format(min(len(rows), args.limit), len(rows)))
    return 0


def cmd_stats(args):
    with open(os.path.join(DATA, "meta.json"), encoding="utf-8") as f:
        print(f.read())
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--apiset", choices=["client", "server", "shared"])
        sp.add_argument("--ns")
        sp.add_argument("--limit", type=int, default=25)
        sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("check"); sp.add_argument("names", nargs="+"); common(sp); sp.set_defaults(fn=cmd_check)
    sp = sub.add_parser("show"); sp.add_argument("names", nargs="+"); common(sp); sp.set_defaults(fn=cmd_show)
    sp = sub.add_parser("search"); sp.add_argument("query", nargs="+"); common(sp); sp.set_defaults(fn=cmd_search)
    sp = sub.add_parser("ns"); sp.add_argument("namespace", nargs="?"); common(sp); sp.set_defaults(fn=cmd_ns)
    sp = sub.add_parser("stats"); common(sp); sp.set_defaults(fn=cmd_stats)

    args = p.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
