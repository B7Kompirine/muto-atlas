#!/usr/bin/env python3
"""timecycle.py — timecycle modifier query.

WHY IT EXISTS
=============
Indoors, the reason a prop looks dark is usually NOT in the prop or the light,
it is in the room's timecycle modifier. An MLO room is bound to a modifier
through `timecycleName`; that modifier overrides ambient light, exposure and fog.
If you set the light up correctly and still see "dark", look here first.

The most useful parameters (measured, with how many times they are defined
across 1087 modifiers):
    postfx_intensity_bloom                1634
    postfx_bright_pass_thresh             1581
    artificial_int_ambient_multiplier     1393   <- interior artificial ambient light
    natural_ambient_multiplier            1368   <- natural ambient light
    light_artificial_int_down_intensity   1291
    light_artificial_int_up_intensity     1274

THE SAME NAME IN MORE THAN ONE DLC
==================================
691 of the 1087 modifiers are defined in more than one source. Which one wins
depends on the DLC load order and CANNOT BE READ from this file. So the conflict
is NOT HIDDEN: `--sources` shows all of them and the default output warns about it.

USAGE
=====
    python assetdb.py timecycle <name>
    python assetdb.py timecycle --search hospital
    python assetdb.py timecycle <name> --param ambient
    python assetdb.py timecycle <name> --sources
"""
from __future__ import annotations

import collections
import gzip
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
TSV = os.path.join(DATA, "timecycle.tsv.gz")

# The parameters that directly answer "why is it dark" are put first.
KEY_PARAMS = (
    "artificial_int_ambient_multiplier",
    "natural_ambient_multiplier",
    "light_artificial_int_down_intensity",
    "light_artificial_int_up_intensity",
    "light_ambient_multiplier",
    "postfx_exposure",
)


def rows():
    if not os.path.exists(TSV):
        return None
    with gzip.open(TSV, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            p = line.split("\t")
            if len(p) >= 6:
                yield {"modifier": p[0], "param": p[1], "v1": p[2], "v2": p[3],
                       "numMods": p[4], "source": p[5]}


def _short_source(s):
    """Shortens the source in a DISTINGUISHING way.

    Taking the last two parts is not enough: every DLC has the same ending
    ('.../dlc.rpf/timecycle_mods_1.xml'), so four separate DLCs show up on
    screen as the same line and the conflict report becomes useless.
    The distinguishing part is the 'dlcpacks/<name>' segment.
    """
    s = s.replace("\\", "/")
    parts = [x for x in s.split("/") if x]
    dlc = ""
    for i, p in enumerate(parts):
        if p.lower() == "dlcpacks" and i + 1 < len(parts):
            dlc = parts[i + 1] + ":"
            break
    return dlc + "/".join(parts[-2:]) if len(parts) >= 2 else s


def cmd_search(pattern, limit):
    d = pattern.lower()
    found = collections.Counter()
    for r in rows():
        if d in r["modifier"].lower():
            found[r["modifier"]] += 1
    if not found:
        print(f"No modifier matches '{pattern}'.")
        return 1
    print(f"{len(found)} modifiers matched:\n")
    for name, n in found.most_common(limit):
        print(f"  {name:<44} {n} parameters")
    if len(found) > limit:
        print(f"\n  ... {len(found) - limit} more (raise it with --limit)")
    return 0


def cmd_show(name, param_filter, show_sources, limit):
    target = name.lower()
    by_source = collections.defaultdict(list)   # source -> [row]
    for r in rows():
        if r["modifier"].lower() == target:
            by_source[r["source"]].append(r)

    if not by_source:
        # suggest close names
        close = sorted({r["modifier"] for r in rows()
                        if target in r["modifier"].lower()})[:6]
        print(f"There is NO timecycle modifier named '{name}'.")
        if close:
            print("  similar: " + ", ".join(close))
        return 1

    sources = list(by_source)
    print(f"modifier: {name}")
    print(f"source  : defined in {len(sources)} files")
    if len(sources) > 1:
        print("  ! The same modifier is defined in more than one DLC. Which one wins "
              "depends on the DLC load order and CANNOT BE READ from this data.")
        for k in sources:
            print(f"    - {_short_source(k)}  ({len(by_source[k])} parameters)")

    # Default: show the first source (--sources for all of them)
    shown = sources if show_sources else sources[:1]

    for k in shown:
        if len(shown) > 1:
            print(f"\n--- {_short_source(k)} ---")
        source_rows = by_source[k]
        key = [r for r in source_rows if r["param"] in KEY_PARAMS]
        other = [r for r in source_rows if r["param"] not in KEY_PARAMS]
        if param_filter:
            f = param_filter.lower()
            key = [r for r in key if f in r["param"].lower()]
            other = [r for r in other if f in r["param"].lower()]

        if key:
            print("\n  LIGHT / AMBIENT (look at these first):")
            for r in key:
                print(f"    {r['param']:<40} {r['v1']:>10}  {r['v2']:>10}")
        if other:
            print(f"\n  other ({len(other)}):")
            for r in other[:limit]:
                print(f"    {r['param']:<40} {r['v1']:>10}  {r['v2']:>10}")
            if len(other) > limit:
                print(f"    ... {len(other) - limit} more (raise it with --limit)")
        if not key and not other:
            print("  (no parameter matches the filter)")
    return 0


def joaat(s):
    h = 0
    for c in s.lower():
        h = (h + ord(c)) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    h = (h + (h << 15)) & 0xFFFFFFFF
    return h


def _ambient_map():
    """{modifier: {param: value1}} — only the KEY_PARAMS parameters + hash->name.

    The `timecycleName` field of an MLO room sits in CodeWalker as an UNRESOLVED
    JOAAT hash (`hash_CDE50982`). Hashing the 1087 modifier names and mapping back
    makes it readable -- verified: CDE50982 -> int_extlight_small,
    55C419A1 -> gen_bank, BD2EC26B -> NEW_abattoir.
    """
    values = collections.defaultdict(dict)
    for r in rows():
        if r["param"] in KEY_PARAMS:
            values[r["modifier"]].setdefault(r["param"], r["v1"])
    hash_name = {joaat(a): a for a in values}
    return values, hash_name


def cmd_mlo(path):
    """Lists the rooms of an MLO ytyp together with their timecycles."""
    from res_xml import read_root

    root, error = read_root(path)
    if error:
        print(f"ERROR: {path}: {error}", file=sys.stderr)
        return 2

    values, hash_name = _ambient_map()

    def resolve(raw):
        raw = (raw or "").strip()
        if not raw:
            return None
        if raw.lower().startswith("hash_"):
            try:
                return hash_name.get(int(raw[5:], 16))
            except ValueError:
                return None
        return raw

    mlos = [a for a in root.findall("./archetypes/Item")
            if a.get("type") == "CMloArchetypeDef"]
    if not mlos:
        print(f"{os.path.basename(path)}: no MLO archetype.")
        return 1

    print(f"{os.path.basename(path)}: {len(mlos)} MLO")
    dark = 0
    for a in mlos:
        rooms = a.findall("./rooms/Item")
        print(f"\n  {a.findtext('name')}  ({len(rooms)} rooms)")
        for o in rooms:
            room = (o.findtext("name") or "?").strip()
            raw = (o.findtext("timecycleName") or "").strip()
            name = resolve(raw)
            if not raw:
                print(f"    {room:<26} (no timecycle)")
                continue
            if name is None:
                print(f"    {room:<26} {raw}  <- NOT RESOLVED (this name is not in the "
                      f"timecycle layer)")
                continue
            p = values.get(name, {})
            natural = p.get("natural_ambient_multiplier")
            artificial = p.get("artificial_int_ambient_multiplier")
            note = ""
            try:
                if natural is not None and artificial is not None \
                        and float(natural) == 0 and float(artificial) == 0:
                    note = "   <- BOTH AMBIENTS 0: everything not lit directly is BLACK"
                    dark += 1
            except ValueError:
                pass
            amb = ""
            if natural is not None or artificial is not None:
                amb = f"  ambient natural={natural or '-'} artificial={artificial or '-'}"
            print(f"    {room:<26} {name}{amb}{note}")

    if dark:
        print(f"\n  {dark} room(s) have their ambient light at exactly zero. For a prop "
              f"to show in these rooms a light that LIGHTS IT has to exist; "
              f"the prop's own colour/texture is not enough.")
    return 0


def run(args):
    from doctor_common import _localize

    if not os.path.exists(TSV):
        print(f"ERROR: {TSV} not found.", file=sys.stderr)
        # _localize() picks the text for the active interface language; the "tr" entry is the
        # Turkish localisation of the same message and stays.
        print("  " + _localize({
            "tr": "Katman kurulu degil: powershell -File build_timecycle.ps1",
            "en": "Layer not installed: powershell -File build_timecycle.ps1"}),
            file=sys.stderr)
        return 2

    if args.mlo:
        return cmd_mlo(args.mlo)
    if args.search:
        return cmd_search(args.search, args.limit)
    if not args.name:
        # summary
        mods = collections.Counter()
        params = collections.Counter()
        for r in rows():
            mods[r["modifier"]] += 1
            params[r["param"]] += 1
        print(f"timecycle layer: {len(mods)} modifiers, {len(params)} distinct "
              f"parameters, {sum(mods.values())} rows")
        print("\nmost often defined parameters:")
        for p, n in params.most_common(8):
            star = " *" if p in KEY_PARAMS else ""
            print(f"  {p:<40} {n}{star}")
        print("\n  * = directly answers 'why is it dark'")
        print("\nfor one modifier: assetdb.py timecycle <name>")
        return 0
    return cmd_show(args.name, args.param, args.sources, args.limit)
