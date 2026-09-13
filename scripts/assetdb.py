#!/usr/bin/env python3
"""assetdb.py — GTA V / FiveM archetype (prop, object, door) database queries.

  assetdb.py show   <name> [...]   archetype details + INTERPRETATION (is it a door, where is the pivot)
  assetdb.py search <part>         search by name
  assetdb.py door   <name> [...]   decision: "does this object open like a door"
  assetdb.py stats                 index summary

Data: data/archetypes.tsv.gz  (built by build_archetypes.ps1)

WHY IT EXISTS: before writing code for a prop/door you need to know what the
object is. specialAttribute and bbox are the only right source for the
question "does the door system play this object"; trying natives does not find it.
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import itertools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n import add_lang_arg, get_lang, set_lang, t  # noqa: E402

# The Windows console is cp1252; unless forced to UTF-8 it crashes on non-ASCII characters.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- EXIT CODES --------------------------------------------------------------
# A single "1" used to mean "the name you searched for does not exist", "the data
# file is not installed" and a Python exception alike. When a gate (lint / CI)
# cannot tell these three apart, a DATA error is reported as an ASSET error: a
# layer is missing so "0 results" come out, the caller says "this asset does NOT
# EXIST in the game" and produces a guess. House rule: "the tool not showing a
# thing does not mean the thing is not there."
EXIT_OK = 0        # found
EXIT_NOTFOUND = 1  # the query ran, the name is not in the authority
EXIT_NOLAYER = 2   # data layer not installed -> NOTHING can be said ABOUT the result
EXIT_INTERNAL = 3  # internal error (exception, external tool crashed)


def die_layer(msg):
    """Layer not installed -> EXIT_NOLAYER. Must not be confused with 'no result'."""
    print(f"ERROR: {msg}", file=sys.stderr)
    print(f"  {t('layer_missing_hint')}", file=sys.stderr)
    sys.exit(EXIT_NOLAYER)


def die_internal(msg):
    """External tool/environment error -> EXIT_INTERNAL."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(EXIT_INTERNAL)


HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
TSV = os.path.join(DATA, "archetypes.tsv.gz")
META = os.path.join(DATA, "assets.meta.json")
ENTDB = os.path.join(DATA, "entities.db")
ANIMS = os.path.join(DATA, "anims.tsv.gz")
CLIPS = os.path.join(DATA, "clips.tsv.gz")
PROPS = os.path.join(DATA, "props.tsv.gz")
SCENARIOS = os.path.join(DATA, "scenarios.tsv.gz")
SKELS = os.path.join(DATA, "skeletons.tsv.gz")
EXPRS = os.path.join(DATA, "expressions.tsv.gz")

# specialAttribute -> meaning.
#
# There are two layers and both are needed:
#   * LABEL       = the official engine name in the Sollumz 2.9 source
#                   (ytyp/properties/ytyp.py:53, SpecialAttribute IntEnum)
#   * DESCRIPTION = the real usage MEASURED on 316k vanilla archetypes
# Example: 2 is "Deprecated - Ladder" in the engine, but every prop that uses it
# is a tower crane -- the crane's ladder. 15 is "Dynamic Cover Bound" in the
# engine, but the props are tables; because a table gives cover. The engine name
# says WHY it behaves that way, the measured usage says WHAT is labelled that way.
#
# Full table + cross-check:
#   skills/fivem-assets/trunk/flags.md
SPECIAL = {
    0:  ("None", "Plain object. The game's DOOR SYSTEM does not recognise this object."),
    1:  ("Deprecated - Unused", "Does nothing in the engine; kept for compatibility "
         "with old files. Users are clutter/detail objects."),
    2:  ("Deprecated - Ladder", "Ladder; the Ladder extension is used now. "
         "In vanilla every user is a tower crane (prop_towercrane_*)."),
    3:  ("Traffic Light", "Traffic light / lamp rig."),
    4:  ("Unknown 4", "Sollumz does not know either. Examples are fence/edge details."),
    5:  ("Garage Door", "Engine-supported large door. The door system works."),
    6:  ("MLO Water Level", "That is the engine name, but most of its 630 users are "
         "unexpected: 84% are NOT SLOD, just ordinary rural map pieces (cs1_/ch1_/cs2_ "
         "prefixes, spread over 20 ytyps, lodDist median 80). Name and usage "
         "do not match; know both, do not decide from one alone."),
    7:  ("Normal Door", "Standard swing door. The door system works fully."),
    8:  ("Sliding Door", "Slides sideways. The door system works."),
    9:  ("Barrier Door", "Barrier gate. Only one example in vanilla "
         "(m26_1_prop_m61_sewer_gate) and it has NO door physics flag."),
    10: ("Sliding Vertical Door", "Vertical roller shutter / elevator door."),
    11: ("Bush", "Bush (NOISY_BUSH inside the engine)."),
    12: ("Rail Crossing Barrier Door", "Railway barrier arm."),
    13: ("Deformable Bush", "Bush/grass that can be flattened."),
    14: ("Single Axis Rotation", "PROCEDURAL ROTATION on one axis -- NOT a door. "
         "Vanilla examples are roof fans (prop_roofvent_*)."),
    15: ("Dynamic Cover Bound", "Provides dynamic cover. Examples are tables/air conditioners."),
    16: ("Rumble On Vehicle Collision", "Shakes when a vehicle hits it. Examples are "
         "construction barriers, pallets."),
    17: ("Rail Crossing Light", "Railway crossing lamp. Two examples "
         "(prop_traffic_rail_1a/_2) inside 'v_traffic_lights.ytyp' -- that is, "
         "the traffic LIGHT ytyp. Do not take 'rail' in the name for a road guard rail."),
    30: ("Clock", "Clock with hands -- the engine drives the hands animated."),
    31: ("Deprecated - Tree", "Same as the double-sided rendering flag; "
         "that flag is used now. Examples are ivy/leaves."),
    32: ("Street Light", "Street lamp. NEVER used in vanilla (0 entries)."),
}

# The types the door system (AddDoorToSystem) really plays.
#
# MEASURED, not guessed: the specialAttribute distribution of the 1176 archetypes
# that have the 'Enable Door Physics' flag (ARCH_FLAG bit 26, value 67108864) set
#   7 -> 646   0 -> 379   5 -> 77   8 -> 71   10 -> 7   12 -> 2   4 -> 1
# For 9 (Barrier Door) and 14 (Single Axis Rotation) this number is ZERO.
# 14 is not a door anyway, it is procedural rotation.
DOOR_CAPABLE = {5, 7, 8, 10, 12}

# WARNING: 379 archetypes carry door physics although specialAttribute=0.
# "Is it a door" cannot be answered by specialAttribute ALONE; look at the flag too.
ARCH_FLAG_DOOR_PHYSICS = 1 << 26


# ---------------------------------------------------------------------------
# FLAG TABLES
# ---------------------------------------------------------------------------
# Source: Sollumz 2.9 ytyp/properties/flags.py (ArchetypeFlags / EntityFlags).
#
# !! Sollumz names the properties flag1..flag32, but flag1 is the LOWEST
#    bit: value(flagN) = 2**(N-1). Writing 1<<N directly shifts the whole table
#    by one bit and silently produces wrong names.
#
# Cross-check (316,975 vanilla archetypes): of the 1308 archetypes with a filled
# clipDictionary, 470 have the 'Has Anim (YCD)' bit and 838 the 'UV anims (YCD)'
# bit; 0 have no anim bit. No false positives in the other direction either.
ARCH_FLAGS = [
    None, "Wet Road Reflection", "Dont Fade", "Draw Last", "Climbable By AI",
    "Suppress HD TXDs", "Static", "Disable alpha sorting", "Tough For Bullets",
    "Is Generic", "Has Anim (YCD)", "UV anims (YCD)", "Shadow Only",
    "Damage Model", "Dont Cast Shadows", "Cast Texture Shadows",
    "Dont Collide With Flyer", "Double-sided rendering", "Dynamic",
    "Override Physics Bounds", "Auto Start Anim",
    "Has Pre Reflected Water Proxy", "Has Drawable Proxy For Water Reflections",
    "Does Not Provide AI Cover", "Does Not Provide Player Cover",
    "Is Ladder Deprecated", "Has Cloth", "Enable Door Physics",
    "Is Fixed For Navigation", "Dont Avoid By Peds", "Use Ambient Scale",
    "Is Debug", "Has Alpha Shadow",
]

ENTITY_FLAGS = [
    None, "Allow full rotation", "Stream Low Priority",
    "Disable embedded collisions", "LOD in Parented YMAP", "LOD Adopt Me",
    "Static entity", "Interior LOD", "Unknown 8", "Unknown 9", "Unknown 10",
    "Unknown 11", "Unknown 12", "Unknown 13", "Unknown 14", "Unknown 15",
    # bit16 (65536): Sollumz says "Unused", CodeWalker "Underwater".
    # MEASURED -> CodeWalker is right: set only 14 times in 3,145,882 entities
    # and all of them are water props (prop_dock_bouy_1/2/3, prop_rub_wheel_01),
    # in harbour and river ymaps (po1_09_long_0, vb_rv_strm_1).
    "LOD Use Alt Fade", "Underwater", "Does Not Touch Water", "Does Not Spawn Peds",
    "Cast Static Shadows", "Cast Dynamic Shadows", "Ignore Day Night Settings",
    "Disable shadow for entity", "Disable entity, shadow casted",
    "Dont Render In Reflections", "Only Render In Reflections",
    "Dont Render In Water Reflections", "Only Render In Water Reflections",
    "Dont Render In Mirror Reflections", "Only Render In Mirror Reflections",
    "Unknown 31", "Unknown 32",
]

UNDECODED_PREFIX = "(undecoded bits"


def decode_flags(value, table):
    """Turns a flag integer into a list of names. flagN -> bit N-1."""
    try:
        value = int(value or 0)
    except (TypeError, ValueError):
        return []
    out = []
    for n in range(1, len(table)):
        if table[n] and value & (1 << (n - 1)):
            out.append(table[n])
    leftover = value & ~sum(1 << (n - 1) for n in range(1, len(table)) if table[n])
    if leftover:
        out.append(f"{UNDECODED_PREFIX}: {leftover})")
    return out

COLS = ["name", "hash", "src", "ytyp", "kind", "assetType", "specialAttribute",
        "flags", "lodDist", "bbMin", "bbMax", "bsRadius", "physicsDict",
        "textureDict", "clipDict"]


def rows():
    """Streams the TSV rows as dicts."""
    if not os.path.exists(TSV):
        die_layer(f"{TSV} not found. Run build_archetypes.ps1 first.")
    with gzip.open(TSV, "rt", encoding="utf-8", errors="replace") as fh:
        header = fh.readline()  # header line
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == len(COLS):
                yield dict(zip(COLS, parts))


def find(names):
    """Finds the given names (lower case) in a single pass."""
    want = {n.lower() for n in names}
    hits = {}
    for r in rows():
        nl = r["name"].lower()
        if nl in want:
            hits.setdefault(nl, []).append(r)
            if len(hits) == len(want) and all(len(v) >= 1 for v in hits.values()):
                pass  # the same name can be in more than one ytyp; keep scanning
    return hits


def vec(s):
    try:
        return [float(x) for x in s.split(",")]
    except Exception:
        return [0.0, 0.0, 0.0]


def pivot_note(r):
    """Derives the hinge/pivot position from the bbox.

    In door models the origin is usually at the door's EDGE (the hinge).
    If so, rotating with SetEntityHeading looks right; otherwise the object
    rotates around its own middle and looks wrong.
    """
    mn, mx = vec(r["bbMin"]), vec(r["bbMax"])
    out = []
    for i, ax in enumerate("XYZ"):
        lo, hi, span = mn[i], mx[i], mx[i] - mn[i]
        if span < 0.05:
            continue
        # if the origin is closer to an edge than 10% of the span: the hinge is there
        if abs(lo) < span * 0.10:
            out.append(t("v_pivot_low", ax=ax, span=span))
        elif abs(hi) < span * 0.10:
            out.append(t("v_pivot_high", ax=ax, span=span))
    return out


def verdict(r):
    """Says which route can make this object 'open like a door'."""
    sa = int(r["specialAttribute"] or 0)
    frag = "FRAGMENT" in r["assetType"].upper()
    has_phys = bool(r["physicsDict"].strip())
    lines = []

    label, desc = SPECIAL.get(sa, (t("v_unknown", sa=sa), t("v_undef")))
    # If a translation of the specialAttribute description exists, use it; otherwise the table.
    translated = t(f"sa_{sa}")
    if translated != f"sa_{sa}":
        desc = translated
    lines.append(f"specialAttribute={sa} -> {label}. {desc}")

    try:
        arch_flags = int(r["flags"] or 0)
    except (TypeError, ValueError):
        arch_flags = 0
    door_phys = bool(arch_flags & ARCH_FLAG_DOOR_PHYSICS)
    lines.append(f"{t('v_flag')}: {t('v_yes') if door_phys else t('v_no')}")

    if sa in DOOR_CAPABLE:
        lines.append(t("v_route_door"))
        if not door_phys:
            lines.append(t("v_warn_noflag"))
    elif door_phys:
        lines.append(t("v_route_flagonly"))
    else:
        lines.append(t("v_route_none"))
        piv = pivot_note(r)
        if piv:
            lines.append(t("v_pivot_edge"))
            lines.extend("       " + p for p in piv)
        else:
            lines.append(t("v_pivot_center"))
        lines.append(t("v_only_fix"))

    if not has_phys:
        lines.append(t("v_no_physics"))
    if frag:
        lines.append(t("v_fragment"))
    return lines


def fmt(r, with_verdict=True):
    out = [
        f"  {r['name']}   [{r['src']}]",
        f"    ytyp            {r['ytyp']}",
        f"    hash            {r['hash']}",
        f"    kind/assetType  {r['kind']} / {r['assetType']}",
        f"    specialAttr     {r['specialAttribute']}",
        f"    flags           {r['flags']}",
    ]
    flag_names = decode_flags(r["flags"], ARCH_FLAGS)
    if flag_names:
        out.append(f"                    -> {' | '.join(flag_names)}")
    out += [
        f"    lodDist         {r['lodDist']}",
        f"    bbMin / bbMax   {r['bbMin']}  /  {r['bbMax']}",
        f"    physicsDict     {r['physicsDict'] or '(none)'}",
        f"    textureDict     {r['textureDict'] or '(none)'}",
        f"    clipDict        {r['clipDict'] or '(none)'}",
    ]
    if with_verdict:
        out.append("    -- interpretation --")
        out.extend("    " + l for l in verdict(r))
    return "\n".join(out)


def cmd_show(args):
    hits = find(args.names)
    missing = 0
    for n in args.names:
        rs = hits.get(n.lower())
        if not rs:
            print(f"\n[{n}] NOT FOUND. Try `assetdb.py search {n}`.")
            missing += 1
            continue
        print(f"\n=== {n} ===")
        for r in rs:
            print(fmt(r, with_verdict=not args.raw))
    return EXIT_NOTFOUND if missing else EXIT_OK


def cmd_door(args):
    hits = find(args.names)
    missing = 0
    for n in args.names:
        rs = hits.get(n.lower())
        if not rs:
            print(f"{n}: NOT FOUND")
            missing += 1
            continue
        r = rs[0]
        sa = int(r["specialAttribute"] or 0)
        ok = t("door_yes") if sa in DOOR_CAPABLE else t("door_no")
        print(f"\n{n}  ->  {t('door_q')}: {ok}")
        for l in verdict(r):
            print("   " + l)
    return EXIT_NOTFOUND if missing else EXIT_OK


def cmd_search(args):
    q = args.query.lower()
    seen, n = set(), 0
    for r in rows():
        if q in r["name"].lower():
            key = (r["name"], r["ytyp"])
            if key in seen:
                continue
            seen.add(key)
            n += 1
            if n <= args.limit:
                print(f"  {r['name']:<40} specialAttr={r['specialAttribute']:<3} "
                      f"{r['assetType']:<22} [{r['src']}] {r['ytyp']}")
    extra = n - args.limit
    print("\n" + t("results", n=n)
          + (t("hidden", n=extra) if extra > 0 else ""))
    return EXIT_NOTFOUND if n == 0 else EXIT_OK


def ent_con():
    """Connects to the world location database."""
    import sqlite3
    if not os.path.exists(ENTDB):
        die_layer("entities.db not found. First:\n"
                  "  powershell -File build_entities.ps1\n"
                  "  python build_entities_db.py")
    return sqlite3.connect(f"file:{ENTDB}?mode=ro", uri=True)


def cmd_where(args):
    """All placements of an archetype in the world.

    'root' = placed directly in a ymap. 'mlo' = part of an interior (MLO);
    the location was computed with the MLO's world placement.
    """
    con = ent_con()
    missing = 0
    for name in args.names:
        print(f"\n=== {name} ===")

        # First name -> id (names is a small table). Then query ent by the nid
        # index; a join on ent with COLLATE NOCASE scans 3M rows.
        row = con.execute("SELECT id FROM names WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
        if not row:
            print("  no placement in the world (only defined as an archetype,"
                  " or caught by the LOD filter).")
            missing += 1
            continue

        rows_ = con.execute(
            "SELECT e.x, e.y, e.z, e.kind, ny.name, ni.name "
            "FROM ent e JOIN names ny ON ny.id = e.ymid "
            "LEFT JOIN names ni ON ni.id = e.iid "
            "WHERE e.nid = ?", (row[0],)).fetchall()

        # The same location appears in more than one ymap (DLC variants place
        # the same interior again). Merge by location, count the sources.
        groups = {}
        for x, y, z, kind, ymap, interior in rows_:
            key = (round(x, 2), round(y, 2), round(z, 2))
            g = groups.setdefault(key, {"kind": kind, "interior": interior, "ymaps": set()})
            g["ymaps"].add(ymap)

        for (x, y, z), g in sorted(groups.items())[:args.limit]:
            k = "mlo " if g["kind"] == 1 else "root"
            loc = f"  interior: {g['interior']}" if g["interior"] else ""
            dup = f"  ({len(g['ymaps'])} ymap)" if len(g["ymaps"]) > 1 else ""
            print(f"  [{k}] vec3({x:.4f}, {y:.4f}, {z:.4f}){loc}{dup}")

        extra = len(groups) - args.limit
        print(f"  -> {len(groups)} unique location(s) ({len(rows_)} record(s))"
              + (f", {extra} not shown" if extra > 0 else ""))
        if not groups:
            missing += 1
    con.close()
    return EXIT_NOTFOUND if missing else EXIT_OK


def cmd_near(args):
    """Entities around a point. For looking at what is there when you already have a coordinate."""
    con = ent_con()
    x, y, z, r = args.x, args.y, args.z, args.radius
    sql = ("SELECT n.name, e.x, e.y, e.z, e.kind, ni.name "
           "FROM ent e JOIN names n ON n.id = e.nid "
           "LEFT JOIN names ni ON ni.id = e.iid "
           "WHERE e.x BETWEEN ? AND ? AND e.y BETWEEN ? AND ? AND e.z BETWEEN ? AND ?")
    params = [x - r, x + r, y - r, y + r, z - r, z + r]
    if args.filter:
        sql += " AND n.name LIKE ?"
        params.append(f"%{args.filter}%")

    # The same object appears in more than one ymap (DLC variant); merge by name+location.
    seen = {}
    for nm, ex, ey, ez, kind, interior in con.execute(sql, params):
        d = ((ex - x) ** 2 + (ey - y) ** 2 + (ez - z) ** 2) ** 0.5
        if d > r:
            continue
        key = (nm.lower(), round(ex, 2), round(ey, 2), round(ez, 2))
        if key not in seen:
            seen[key] = (d, nm, ex, ey, ez, kind, interior)
    con.close()

    hits = sorted(seen.values(), key=lambda item: item[0])
    for d, nm, ex, ey, ez, kind, interior in hits[:args.limit]:
        k = "mlo " if kind == 1 else "root"
        loc = f"  [{interior}]" if interior else ""
        print(f"  {d:6.2f}m  [{k}] {nm:<38} vec3({ex:.4f}, {ey:.4f}, {ez:.4f}){loc}")
    extra = len(hits) - args.limit
    print(f"\n{len(hits)} entities within {r}m" + (f" ({extra} not shown)" if extra > 0 else ""))


def gz_lines(path, what, header=False):
    """Streams gzip TSV lines. header=True skips the first line (the header).

    clips/skeletons/expressions have a header; anims/props/scenarios do not.
    If the header is not skipped, a fake 'dict  clip  type...' line gets mixed
    into the query results.
    """
    if not os.path.exists(path):
        die_layer(f"{path} not found. Run the matching build script first ({what}).")
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        if header:
            fh.readline()
        for line in fh:
            line = line.rstrip("\n")
            if line:
                yield line


CLIP_COLS = ["dict", "clip", "type", "animCount", "duration", "rootMotion", "bones"]


def clip_rows():
    """clips.tsv.gz rows (extracted from the ycd: with duration + track count)."""
    for line in gz_lines(CLIPS, "clips", header=True):
        p = line.split("\t")
        if len(p) == len(CLIP_COLS):
            yield dict(zip(CLIP_COLS, p))


def clip_line(r, width=40):
    dur = float(r["duration"] or 0)
    kind = "multi-track " if r["type"] == "animlist" else "single-track"
    rm = " root-motion" if r["rootMotion"] == "1" else ""
    bones = r.get("bones") or "?"
    return f"  {r['clip']:<{width}} {dur:7.3f}s  {kind} tracks={r['animCount']} {t('ped_bones')}={bones}{rm}"


def anim_fallback(q, dict_only, limit):
    """If clips.tsv.gz (HEAVY layer) is missing, fall back to anims.tsv.gz.

    ⛔ Saying "layer missing" WHILE the user HAS data would be the tool's biggest
    flaw: someone without a GTA V install has 269,414 animation names but no
    duration/bone information. Instead of refusing outright, GIVE WHAT IS THERE
    and SAY what is missing.
    """
    n = 0
    for line in gz_lines(ANIMS, "animation names"):
        p_ = line.split("\t")
        if len(p_) != 2:
            continue
        d, c = p_
        hay = d.lower() if dict_only else f"{d}\t{c}".lower()
        if q not in hay:
            continue
        n += 1
        if n <= limit:
            print(f"  {d:<46} {c}")
    extra = n - limit
    print("\n" + t("results", n=n)
          + (t("hidden", n=extra) if extra > 0 else ""))
    print(f"{t('note')}: {t('anim_no_clips')}")
    print("       powershell -File scripts/build_clips.ps1")
    return EXIT_NOTFOUND if not n else EXIT_OK


def cmd_anim(args):
    """Animation search. Duration and track count come from the .ycd.

    Playing an animation in FiveM needs BOTH the dictionary AND the clip name
    (RequestAnimDict + TaskPlayAnim).
    """
    q = args.query.lower()

    # If the heavy layer is missing, fall back to the light layer (see anim_fallback).
    if not os.path.exists(CLIPS):
        if args.dict:
            print("clips.tsv.gz is not installed; --dict duration grouping is not possible.")
            print("For a name search run without --dict.")
            return EXIT_NOLAYER
        return anim_fallback(q, args.dict_only, args.limit)

    # --dict: dump the contents of one dictionary and GROUP BY DURATION.
    # Clips with the same duration in the same dictionary are written to play
    # in sync: one is the ped, the other the prop. This is where to look when
    # searching for a prop animation.
    if args.dict:
        rows_ = [r for r in clip_rows() if r["dict"].lower() == q]
        if not rows_:
            print(f"No dictionary named '{args.query}'. Search with `anim {args.query} --dict-only`.")
            return EXIT_NOTFOUND
        groups = {}
        for r in rows_:
            groups.setdefault(round(float(r["duration"] or 0), 3), []).append(r)

        print(f"=== {args.query} ===  {len(rows_)} clips")
        for dur, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            # Same duration + DIFFERENT skeleton = ped and prop in the same scene.
            # Same duration alone is not enough: _female/_suit variants have the
            # same duration too, but all of them use the same skeleton (ped).
            skels = {r.get("bones", "") for r in rs}
            pair = len(rs) > 1 and len(skels) > 1 and dur > 0
            tag = "  <-- same duration, DIFFERENT skeleton: ped + prop pair" if pair else ""
            print(f"\n  [{dur:.3f}s]{tag}")
            for r in sorted(rs, key=lambda x: x["clip"])[:args.limit]:
                print("  " + clip_line(r))
        print("\nSynchronized playback: NetworkCreateSynchronisedScene + TaskSynchronizedScene (ped)")
        print("                       + PlaySynchronizedEntityAnim / NetworkAddEntityToSynchronisedScene (prop)")
        return

    n = 0
    for r in clip_rows():
        hay = r["dict"].lower() if args.dict_only else f"{r['dict']}\t{r['clip']}".lower()
        if q not in hay:
            continue
        n += 1
        if n <= args.limit:
            print(f"  {r['dict']:<42}{clip_line(r, width=34)}")
    extra = n - args.limit
    print("\n" + t("results", n=n)
          + (t("hidden", n=extra) if extra > 0 else ""))
    if not n:
        return EXIT_NOTFOUND
    if n:
        print("Usage: RequestAnimDict('<dict>') -> HasAnimDictLoaded -> TaskPlayAnim(ped,'<dict>','<clip>',...)")
        print("Tip:   to see a dictionary's contents grouped by duration:  anim <dict> --dict")


SKEL_COLS = ["model", "src", "boneCount", "boneIndex", "boneName", "boneTag", "parentIndex"]


def cmd_bones(args):
    """A model's skeleton: bone name + TAG.

    Playing a prop with an animation, attaching something to it or giving its
    bone an offset needs the bone NAME (GetEntityBoneIndexByName) or its TAG.
    On a prop without a skeleton none of these work — this command says that first.
    """
    q = {n.lower() for n in args.names}

    # skeletons.tsv.gz indexes the same model from more than one RPF/DLC COPY;
    # each copy writes its own bones in order starting at index 0. So rows
    # repeat (measured: w_ar_assaultrifle 64 rows, 16 bones, exactly 4 copies)
    # — without de-duplication the list multiplies and the --limit overflow is
    # miscounted.
    #
    # Telling copies apart by the index reset is essential: in 289 models the
    # copies REALLY differ (base vs DLC skeleton). Moreover the difference does
    # not always show in boneCount — 'adder' has two separate 63-bone skeletons
    # (one has an extra 'extra_1', every later index shifts). Merged as a set of
    # rows, 76 bones get printed under a 63-bone header.
    # Verified on the whole file: 72,364 copies, each one's length equals its own
    # boneCount and its indices run 0..n-1 without gaps.
    found, cur, prev = {}, None, -1
    for line in gz_lines(SKELS, "skeletons", header=True):
        p = line.split("\t")
        if len(p) != len(SKEL_COLS):
            continue
        r = dict(zip(SKEL_COLS, p))
        key, idx = r["model"].lower(), int(r["boneIndex"])
        if key != cur or idx <= prev:      # a new copy started
            cur = key
            if key in q:
                found.setdefault(key, []).append([])
        prev = idx
        if key in q:
            found[key][-1].append(r)

    missing = 0
    for n in args.names:
        copies = found.get(n.lower())
        print(f"\n=== {n} ===")
        if not copies:
            print(t("bones_none"))
            print(t("bones_none_hint"))
            missing += 1
            continue

        # Drop copies of the same skeleton, keep the versions that really differ.
        seen, variants = set(), []
        for c in copies:
            sig = tuple((r["boneIndex"], r["boneName"], r["boneTag"]) for r in c)
            if sig in seen:
                continue
            seen.add(sig)
            variants.append(c)
        variants.sort(key=len, reverse=True)   # richest (newer/DLC) version first

        if len(variants) > 1:
            counts = " / ".join(t("bones_n", n=len(v)) for v in variants)
            print(f"  CAUTION: this model is indexed with {len(variants)} different")
            print(f"  skeleton versions ({counts}) — bone INDICES shift between")
            print("  versions, TAGs do not. Bind by tag, not by index.")
            # Name the divergence point: bone counts can be equal ('adder' twice
            # 63, the same bones in a different index order) and because the first
            # bones are the same, the versions look like pointless repeats on screen.
            key = lambda r: (r["boneName"], r["boneTag"])
            sets = [{key(r) for r in v} for v in variants]
            at = min(
                next((i for i in range(min(len(variants[0]), len(o)))
                      if key(variants[0][i]) != key(o[i])), min(len(variants[0]), len(o)))
                for o in variants[1:])
            excl = [s.difference(*(sets[:i] + sets[i + 1:])) for i, s in enumerate(sets)]
            if any(excl):
                which = "; ".join(
                    f"version {i + 1}: {', '.join(sorted(n for n, _ in e))}"
                    for i, e in enumerate(excl) if e)
                print(f"  First divergence: #{at} — bones only in that version -> {which}")
            else:
                print(f"  First divergence: #{at} — the bone set is the SAME, only the index order changes.")

        for v in variants:
            head = f"  {v[0]['src']} · " + t("bones_n", n=len(v))
            print(head if len(variants) == 1 else head + "  (version)")
            for r in v[:args.limit]:
                par = r["parentIndex"]
                par = "-" if par == "-1" else par
                print(f"    #{r['boneIndex']:<4} {r['boneName']:<32} tag={r['boneTag']:<6} parent={par}")
            extra = len(v) - args.limit
            if extra > 0:
                print("    " + t("bones_more", n=extra))
    return EXIT_NOTFOUND if missing else EXIT_OK


def cmd_clipfit(args):
    """WHICH MODEL can play a clip — by bone tag matching.

    Knowing how many bones a clip animates is not enough; which bone TAGs it
    targets is needed. That tag set alone determines the model.
    Example: bank_vault_door_opens -> tag {0,10596,50607} -> one model:
    hei_prop_heist_sec_door (the animated twin of the vault door on the map).
    """
    import subprocess

    ps = os.path.join(HERE, "clip_bones.ps1")
    if not os.path.exists(ps):
        die_internal(f"{ps} not found.")

    try:
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", ps, "-Dict", args.dict, "-Clip", args.clip, "-Json"],
            capture_output=True, text=True, timeout=900).stdout
    except Exception as e:
        die_internal(f"clip_bones.ps1 could not be run: {e}")

    line = next((l for l in out.splitlines() if l.strip().startswith("{")), None)
    if not line:
        die_internal(f"bone tags could not be extracted.\n{out.strip()[:400]}")
    data = json.loads(line)
    if "error" in data:
        print(f"NOT FOUND: {args.dict} / {args.clip}", file=sys.stderr)
        sys.exit(EXIT_NOTFOUND)

    want = set(data["tags"])
    print(f"=== {args.dict} / {args.clip} ===")
    print(f"  targeted bone tags ({len(want)}): {sorted(want)}\n")

    # If only the root bone (tag 0) is targeted, the clip plays the object as
    # ONE PIECE. In that case the tag set does not determine the model — any
    # prop can play it. Instead of listing 52k models, say so.
    if want == {0}:
        print("  This clip moves ONLY the root bone (tag 0).")
        print("  So it moves/rotates the object as one piece; no inner part moves.")
        print("  RESULT: the model cannot be determined from tags — EVERY prop with a")
        print("  root bone can play this clip. Find the right prop by name and duration match:")
        print(f"    assetdb.py anim {args.dict} --dict")
        return

    # Note: SKELS indexes the same model from more than one copy (see cmd_bones).
    # Because the tags go into a SET, repeated rows do not inflate the score; but
    # boneCount can differ between copies (base vs DLC) — pin it to the richest
    # version, not to file order.
    mtags, mcount, msrc = {}, {}, {}
    for line_ in gz_lines(SKELS, "skeletons", header=True):
        p = line_.split("\t")
        if len(p) != len(SKEL_COLS):
            continue
        mtags.setdefault(p[0], set()).add(int(p[5]))
        mcount[p[0]] = max(int(p[2]), mcount.get(p[0], 0))
        msrc[p[0]] = p[1]

    scored = []
    for m, tags in mtags.items():
        hit = len(want & tags)
        if hit:
            scored.append((hit, -mcount[m], m))
    scored.sort(reverse=True)

    full = [s for s in scored if s[0] == len(want)]
    if full:
        # Too many full matches = the tag set is not distinctive (usually
        # common/shared bone tags). Dumping a list misleads.
        if len(full) > 50:
            print(f"  {len(full)} models match fully -> this tag set is NOT DISTINCTIVE.")
            print("  (common/shared bone tags; the model cannot be determined from it)")
            print(f"  Look at the name and duration match:  assetdb.py anim {args.dict} --dict")
            return

        print(f"  FULL MATCH ({len(full)} models):")
        for hit, _, m in full[:args.limit]:
            print(f"    {m:<44} {mcount[m]} bones  [{msrc[m]}]")
        if len(full) == 1:
            print("\n  Single candidate -> the clip was made to be played on this model.")
            print(f"  Usage: PlayEntityAnim(obj, '{args.clip}', '{args.dict}', ...)")
    else:
        print("  NO model matches fully. Closest:")
        for hit, _, m in scored[:args.limit]:
            print(f"    {m:<44} {hit}/{len(want)} tags  {mcount[m]} bones")
        print("\n  Note: the clip may target a ped skeleton (ped animation),")
        print("  or its model may be a DLC/custom asset that is not in this index.")
        return EXIT_NOTFOUND


def cmd_expr(args):
    """Expression (.yed) search — procedural bone motion / spring / collision reaction."""
    q = args.query.lower()
    n = 0
    for line in gz_lines(EXPRS, "expressions", header=True):
        p = line.split("\t")
        if len(p) != 6:
            continue
        yed, name, h, streams, tracks, springs = p
        if q not in f"{yed}\t{name}".lower():
            continue
        n += 1
        if n <= args.limit:
            sp = f"  springs={springs}" if springs != "0" else ""
            print(f"  {yed:<34} {name:<34} tracks={tracks:<4} stream={streams}{sp}")
    extra = n - args.limit
    print("\n" + t("results", n=n)
          + (t("hidden", n=extra) if extra > 0 else ""))
    if n:
        print("Note: expressions with a spring count > 0 produce a physical reaction")
        print("      (bones that sway with collision/motion). They work through the")
        print("      model's expression, not through SetEntityAnimSpeed and the like.")
    return EXIT_NOTFOUND if n == 0 else EXIT_OK


def cmd_prop(args):
    q = args.query.lower()
    n = 0
    for name in gz_lines(PROPS, "props"):
        if q in name.lower():
            n += 1
            if n <= args.limit:
                print(f"  {name}")
    extra = n - args.limit
    print("\n" + t("results", n=n)
          + (t("hidden", n=extra) if extra > 0 else ""))
    if n:
        print("Note: this list holds the props that can be spawned with CREATE_OBJECT.")
        print("      For the object's door/physics properties: assetdb.py show <name>")
    return EXIT_NOTFOUND if n == 0 else EXIT_OK


def cmd_scenario(args):
    q = args.query.lower()
    hits = [s for s in gz_lines(SCENARIOS, "scenarios") if q in s.lower()]
    for s in hits[:args.limit]:
        print(f"  {s}")
    print("\n" + t("results", n=len(hits)))
    return EXIT_NOTFOUND if not hits else EXIT_OK



def cmd_propanim(args):
    """Find a PROP's REAL animations.

    WHY THIS WAY: the "same duration + different bone count" heuristic guesses
    the ped+prop pair; it is not certain. Measured: in synchronized scene clips
    the CLIP NAME is directly the PROP MODEL NAME (`prop_cs_walking_stick-3`,
    `v_ilev_store_door-0` -> `-N` is the scene slice suffix). When 312,748 clips
    were matched against the prop database, 1407 props / 53,181 real prop
    animations came out.
    """
    import collections
    q = args.query.lower()
    props = set()
    for name in gz_lines(PROPS, "props"):
        props.add(name.lower())

    want = {p for p in props if q in p} if q else props
    if not want:
        print(f"[!] '{args.query}' is not in the prop database. "
              f"First: assetdb.py prop {args.query}")
        return EXIT_NOTFOUND

    hits = collections.defaultdict(list)
    with gzip.open(CLIPS, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 7:
                continue
            c = f[1].lower()
            base = c.rsplit("-", 1)[0] if ("-" in c and c.rsplit("-", 1)[1].isdigit()) else c
            if base in want:
                hits[base].append((f[0], f[1], f[4], f[6]))

    if not hits:
        print(f"[=] a prop matching '{args.query}' was found but it has NO animations at all.")
        print("    If the prop has no bones/animation, PlayEntityAnim does not work.")
        return EXIT_NOTFOUND

    for p in sorted(hits, key=lambda k: -len(hits[k]))[:args.limit]:
        v = hits[p]
        print(f"\n=== {p}   ({len(v)} clips)")
        seen = set()
        for d, c, dur, b in v:
            if d in seen:
                continue
            seen.add(d)
            print(f"    {d:<46} {c:<30} {dur:>9}s  channels={b}")
            if len(seen) >= args.dicts:
                rest = len({x[0] for x in v}) - len(seen)
                if rest > 0:
                    print(f"    ... {rest} more dicts")
                break
    print(f"\n{len(hits)} props, {sum(len(v) for v in hits.values())} clips")
    print("Usage: the ped clip and the prop clip play in sync, in the SAME dict,")
    print("       with the SAME duration.")


FXTYPE = {
    0: "Ambient",  1: "Collision", 2: "Shot",    3: "Break",
    4: "Destroy",  5: "Animation (Unused)", 6: "RayFire", 7: "In Water",
}

EXT_TSV = os.path.join(DATA, "ytyp_extensions.tsv.gz")

# Column names of the data file written by build_extensions.ps1. 'detay' (details)
# is a data column name and stays as it is.
EXT_COLS = ["archetype", "src", "ytyp", "extType", "extName", "offsetPos",
            "fxName", "fxType", "boneTag", "scale", "probability",
            "extFlags", "detay"]


def ext_rows():
    """Iterates the ytyp extension rows. Gives a meaningful error if the index is missing."""
    if not os.path.exists(EXT_TSV):
        die_layer(
            f"{EXT_TSV} not found.\n"
            "  Build: powershell -NoProfile -ExecutionPolicy Bypass "
            "-File scripts/build_extensions.ps1"
        )
    with gzip.open(EXT_TSV, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()  # header line
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == len(EXT_COLS):
                yield dict(zip(EXT_COLS, parts))


PTFXTSV = os.path.join(DATA, "ptfx_effects.tsv.gz")


def ptfx_catalog():
    """The real effect catalog (from the .ypt files). name -> (emitter, ypt list).

    2549 unique effects / 368 ypts. Without it the question 'is the fxName
    right' cannot be answered -- and a wrong fxName is a SILENT failure: the
    effect never appears and no warning is given.
    """
    if not os.path.exists(PTFXTSV):
        return {}
    out = {}
    with gzip.open(PTFXTSV, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) == 3:
                out[p[0].lower()] = (p[0], p[1], p[2])
    return out


def cmd_fx(args):
    """Particle effect catalog: 'does such an effect exist, in which ypt'."""
    catalog = ptfx_catalog()
    if not catalog:
        die_layer(f"{PTFXTSV} not found.\n  Build: powershell -NoProfile "
                  "-ExecutionPolicy Bypass -File scripts/build_ptfx.ps1")

    q = (args.query or "").lower()
    if args.exact:
        # The fxName in the ytyp and the effect name in the .ypt are NOT THE SAME:
        # measured, of 406 fxNames only 3 exist as is, 265 (65.3%) need the
        # 'ent_' prefix. Try as is first, then with the prefix.
        r = catalog.get(q) or catalog.get("ent_" + q)
        if r and not catalog.get(q):
            print(f"\n  NOTE: the ytyp says '{args.query}' but the real name in the "
                  f".ypt is '{r[0]}'.")
            print("        The engine adds the 'ent_' prefix itself "
                  "(true for 65.3% of 406 fxNames).")
        if not r:
            # If something STARTS WITH 'ent_<name>', the name also got a suffix.
            # Measured: 9 of 406 fxNames are like this (e.g. amb_butterflys ->
            # ent_amb_butterflys_swarm).
            prefixed = "ent_" + q
            suffixed = sorted(v[0] for k, v in catalog.items() if k.startswith(prefixed))
            if suffixed:
                print(f"\n'{args.query}' does not exist as is, but a SUFFIXED form does:")
                for y in suffixed[:6]:
                    print(f"    {y}")
                print("\n  The ytyp name and the .ypt name can differ by both a prefix")
                print("  and a suffix. Make sure which one you want.")
                return 1

            print(f"\nNo effect named '{args.query}' EXISTS ({len(catalog)} effects scanned;")
            print("  the 'ent_' prefix and suffixed forms were tried too).")
            close = [v[0] for k, v in catalog.items() if q[:6] and q[:6] in k][:8]
            if close:
                print("  did you mean:")
                for y in close:
                    print(f"    {y}")
            print("\n  !! A wrong fxName is a SILENT failure: the effect never appears, no warning.")
            print("  !! BUT 'not found' does not always mean it is your mistake.")
            print("     MEASURED: 129 of 406 vanilla fxNames (31.8%) have no relative in")
            print("     any .ypt at all -- e.g. 'amb_water_roof_drips_short', although it")
            print("     is used 5621 times. The index is NOT incomplete: compared with")
            print("     core.ypt's XML, 895/895 effects were captured.")
            print("     So these are vanilla's own DANGLING REFERENCES.")
            print("     If you copied a vanilla ytyp and inherited its effect,")
            print("     that effect may already not work.")
            return 1
        name, emitter, ypts = r
        print(f"\n=== {name} ===")
        print(f"  event emitter : {emitter}")
        print(f"  found in ypt  : {ypts.replace(';', ', ')}")
        uses = [x for x in ext_rows()
                if x["extType"] == "Particle" and x["fxName"].lower() == q]
        print(f"  ytyp usage    : {len(uses)} props")
        for x in uses[:6]:
            print(f"     {x['archetype']:<34} fxType={x['fxType']} scale={x['scale']}")
        return 0

    found = [v for k, v in catalog.items() if not q or q in k]
    if not found:
        print(f"No effect matches '{args.query}'.")
        return 1
    found.sort(key=lambda v: v[0])
    print(f"\n{len(found)} effects" + (f" (containing '{args.query}')" if q else
                                       f" / {len(catalog)} total") + "\n")
    for name, emitter, ypts in found[: args.limit]:
        first = ypts.split(";")[0]
        print(f"  {name:<40} emitter={emitter:<3} {first}")
    if len(found) > args.limit:
        print(f"\n  ... {len(found)-args.limit} more (--limit)")
    print("\n  Details of one effect: assetdb.py fx <full_name> --exact")
    return 0


def cmd_ptfx(args):
    """Searches particle extensions: by prop name, effect name or fxType.

    Particles live in the YTYP, not in the script. The answer to the request
    'make dust come out when this prop breaks' is not a native but a
    CExtensionDefParticleEffect added to the archetype.
    """
    q = (args.query or "").lower()
    fx_type = args.type
    found, seen_fx = [], collections.Counter()

    for row in ext_rows():
        if row["extType"] != "Particle":
            continue
        if fx_type is not None and (row["fxType"] or "0") != str(fx_type):
            continue
        if q and q not in row["archetype"].lower() and q not in row["fxName"].lower():
            continue
        found.append(row)
        seen_fx[row["fxName"]] += 1

    if not found:
        print("no matching particle.")
        return 1

    print(f"\n{len(found)} particle extensions, {len(seen_fx)} distinct effects\n")
    for row in found[: args.limit]:
        ft = int(row["fxType"] or 0)
        bone = int(row["boneTag"] or 0)
        bone_s = "ALL bones" if bone == -1 else f"tag {bone}"
        print(f"  {row['archetype']:<38} {row['fxName']}")
        print(f"      fxType={ft} ({FXTYPE.get(ft, '?')})  {bone_s}  "
              f"scale={row['scale']}  probability={row['probability']}%")
        if row["offsetPos"] not in ("", "0,0,0"):
            print(f"      offset {row['offsetPos']}")
    if len(found) > args.limit:
        print(f"\n  ... {len(found) - args.limit} more rows (raise with --limit)")

    if len(seen_fx) > 1:
        print("\n  most frequent effects:")
        for name, n in seen_fx.most_common(8):
            print(f"    {name:<34} {n}")
    return 0


def cmd_ext(args):
    """ALL extensions of an archetype (14 types)."""
    query = args.name.lower()
    matches = [r for r in ext_rows() if query in r["archetype"].lower()]
    if not matches:
        print(f"No extensions for '{args.name}'.")
        print("  NOTE: most archetypes have no extensions at all -- this is normal.")
        return 1

    for arch, group in itertools.groupby(
            sorted(matches, key=lambda r: r["archetype"]), key=lambda r: r["archetype"]):
        group = list(group)
        print(f"\n{arch}   [{group[0]['src']}]  {group[0]['ytyp']}")
        for r in group:
            ext_type = r["extType"]
            if ext_type == "Particle":
                ft = int(r["fxType"] or 0)
                print(f"   Particle       {r['fxName']}  fxType={ft} ({FXTYPE.get(ft,'?')})"
                      f"  scale={r['scale']} {r['probability']}%")
            elif ext_type == "Expression":
                print(f"   Expression     {r['detay']}")
                print("                  -> .yed chain: exprDict is a BARE NAME "
                      "(NOT pack:/x.expr)")
            elif ext_type == "ProcObject":
                print(f"   ProcObject     {r['detay']}")
            else:
                print(f"   {ext_type:<14} {r['extName']}")
    return 0


def cmd_lod(args):
    """Vanilla reference for lodDist: 'what distance does an object of this size get'.

    lodDist is not guessed, it is measured. The table below is the joint
    distribution of the bbox longest edge and the lodDist of 316k vanilla archetypes.
    """
    buckets = [(0, 1, "<1m"), (1, 3, "1-3m"), (3, 10, "3-10m"),
               (10, 30, "10-30m"), (30, 100, "30-100m"), (100, float("inf"), ">100m")]
    by_bucket = collections.defaultdict(list)

    for row in rows():
        try:
            lo = [float(v) for v in row["bbMin"].split(",")]
            hi = [float(v) for v in row["bbMax"].split(",")]
            longest = max(hi[i] - lo[i] for i in range(3))
            ld = float(row["lodDist"])
        except (ValueError, IndexError, KeyError):
            continue
        if ld <= 0:
            continue
        for a, b, label in buckets:
            if a <= longest < b:
                by_bucket[label].append(ld)
                break

    print("\nVANILLA lodDist DISTRIBUTION (by bbox longest edge)\n")
    print(f"  {'size':<10}{'count':>8}{'median':>9}{'p25':>8}{'p75':>8}")
    for _, _, label in buckets:
        v = sorted(by_bucket[label])
        if not v:
            continue
        med = v[len(v) // 2]
        p25 = v[len(v) // 4]
        p75 = v[min(len(v) - 1, 3 * len(v) // 4)]
        print(f"  {label:<10}{len(v):>8}{med:>9.0f}{p25:>8.0f}{p75:>8.0f}")

    if args.size is not None:
        for a, b, label in buckets:
            if a <= args.size < b:
                v = sorted(by_bucket[label])
                med = v[len(v) // 2]
                print(f"\n  {args.size} m -> '{label}' bucket, SUGGESTED lodDist = {med:.0f}")
                break

    print("""
  LOD CHAIN -- MEASURED on 3.07M vanilla entities
    * ParentIndex is an ORDER number; CMapData.parent in the ymap header says
      which file's order it is. DO NOT TRUST FILE NAME PATTERNS:
      children whose name starts with the parent's name are only 79%.
    * -1 = end of chain. At intermediate levels the entity flag is 'LOD Adopt Me' (16).
    * HD entity flag 1572872 = LOD in Parented YMAP | Cast Static | Cast Dynamic
    * parent.childLodDist == child.lodDist  ->  86% true, 14% NOT.
      Not a rule, a strong convention.
    * THE LEVEL CHAIN IS NOT LINEAR. Measured real transitions (parent -> child):
        LOD   -> HD     693,260      SLOD2 -> SLOD1   13,628
        SLOD2 -> LOD     55,817      SLOD4 -> LOD      1,719
        SLOD3 -> LOD     40,250
      There is NO 'SLOD1 -> LOD' transition: SLOD1 is not inside the chain,
      it is a side branch of SLOD2. There are 7 levels (ORPHANHD HD LOD SLOD1..SLOD4).
    * ORPHANHD is the MOST COMMON level (1.53M) -- so most entities have no chain.
    * IF ONE LINK OF THE CHAIN IS DELETED THE WHOLE CHAIN BREAKS: all levels
      load at the same time, flicker, and ghost copies appear.

  To walk a real chain:  assetdb.py lodchain <archetype>""")
    return 0


LODTSV = os.path.join(DATA, "ymap_lod.tsv.gz")

# rpfPath is REQUIRED: 4751 of 8252 ymap names exist in more than one RPF
# (base + DLC). Reading by name stacks the copies and produces fake breaks.
# mapName: the ymap's INTERNAL name. CMapData.parent points at this, not at the
# file name; measured, the two differ in 177 of 3000 ymaps.
LOD_COLS = ["ymap", "mapName", "rpfPath", "parentYmap", "idx", "archetype",
            "flags", "parentIndex", "numChildren", "lodDist", "childLodDist",
            "lodLevel", "priority"]


def lod_rows():
    if not os.path.exists(LODTSV):
        die_layer(f"{LODTSV} not found.\n"
                  "  Build: powershell -NoProfile -ExecutionPolicy Bypass "
                  "-File scripts/build_ymap_lod.ps1")
    with gzip.open(LODTSV, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == len(LOD_COLS):
                yield dict(zip(LOD_COLS, parts))


DECALTSV = os.path.join(DATA, "decal_types.tsv")

# Work type -> decals.dat category. Someone who wants "a blood trail" should
# not have to type 'BLOOD'. The Turkish keys (kan, mermi, ayak ...) are
# intentional: Turkish input stays accepted next to the English words.
DECAL_WORK_TYPES = {
    "kan": "BLOOD", "blood": "BLOOD",
    "mermi": "BANGS", "kursun": "BANGS", "bullet": "BANGS", "impact": "BANGS",
    "ayak": "FOOTPRINT", "iz": "FOOTPRINT", "footprint": "FOOTPRINT",
    "yanik": "BURN", "burn": "BURN",
    "yag": "OIL", "oil": "OIL",
    "benzin": "PETROL", "petrol": "PETROL",
    "camur": "MUD", "mud": "MUD",
    "su": "WATER", "water": "WATER",
    "arac": "VEHICLE", "vehicle": "VEHICLE", "rozet": "VEHICLE BADGES",
    "sicrama": "SPLATTER", "splatter": "SPLATTER",
    "cizik": "SCRAPE", "scrape": "SCRAPE",
}


def cmd_decal(args):
    """decalType table -- the first argument of AddDecal().

    SOURCE: the game's own common.rpf\\data\\effects\\decals.dat file.
    The enum in the FiveM docs is INCOMPLETE; this table is complete.

    ONE ID CAN CARRY SEVERAL VARIANTS: the engine picks one at random.
    """
    if not os.path.exists(DECALTSV):
        die_layer(f"{DECALTSV} not found.\n  Build: python scripts/build_decals.py")

    # Columns 'kategori' (category), 'varyant' (variants) and 'dokular' (textures)
    # are data column names written by build_decals.py; they stay as they are.
    with open(DECALTSV, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        records = [dict(zip(header, l.rstrip("\n").split("\t"))) for l in fh if l.strip()]

    if args.id is not None:
        r = next((k for k in records if int(k["id"]) == args.id), None)
        if r is None:
            print(f"decalType {args.id} is not in the table.")
            nearest = sorted(records, key=lambda k: abs(int(k["id"]) - args.id))[:5]
            print("  nearest IDs:")
            for y in nearest:
                print(f"    {y['id']:<7} {y['kategori']}")
            return 1
        print(f"\ndecalType {r['id']}   [{r['kategori']}]")
        print(f"  variants    {r['varyant']}   (the engine picks at random)")
        print(f"  washable    {r['washable']}   forms under water: {r['underwater']}")
        print(f"  textures    {r['dokular'].replace(';', ', ')}")
        print("\n  Usage:")
        print(f"    AddDecal({r['id']}, x,y,z, 0,0,-1, 1,0,0, width,height,"
              " 1.0,1.0,1.0, opacity, duration, false, false, false)")
        print("    direction (0,0,-1) = downward-facing surface (floor). duration=-1 is permanent.")
        return 0

    q = (args.query or "").lower().strip()
    if q in DECAL_WORK_TYPES:
        q = DECAL_WORK_TYPES[q].lower()
    found = [k for k in records
             if not q or q in k["kategori"].lower() or q in k["dokular"].lower()]
    if not found:
        print(f"No match for '{args.query}'.")
        print("  work types: " + ", ".join(sorted(set(DECAL_WORK_TYPES))))
        return 1

    print(f"\n{len(found)} decalType" + (f" ('{args.query}')" if q else
                                         f" / {len(records)} total") + "\n")
    for r in found[: args.limit]:
        print(f"  {r['id']:<7} {r['kategori'][:34]:<36} variants={r['varyant']:<3} "
              f"{r['dokular'][:34]}")
    if len(found) > args.limit:
        print(f"\n  ... {len(found)-args.limit} more (--limit)")
    print("\n  Details of one type: assetdb.py decal --id <number>")
    print("  Dress it with your own texture: PatchDecalDiffuseMap(id, txd, texture)")
    return 0


SHADERTSV = os.path.join(DATA, "shaders.tsv")

# RENDER BUCKET -- per material, a field SEPARATE from the shader.
# Source: szio.gta5.drawables.RenderBucket + Sollumz ydr/render_bucket.py
# descriptions. The Sollumz DEFAULT leaves 'Opaque (0)'; unless it is changed by
# hand for decal/glass, the surface is drawn WRONG and no error is given.
RENDER_BUCKET = {
    0: ("Opaque", "Surface without alpha, opaque."),
    1: ("Alpha", "Has alpha but NO SHADOW. Usually glass."),
    2: ("Decal", "Decal with alpha, no shadow."),
    3: ("Cutout", "Has alpha AND a shadow. Like fences/cages."),
    4: ("No Splash", "Only with the 'vehicle_nosplash' shader."),
    5: ("No Water", "Only with the 'vehicle_nowater' shader."),
    6: ("Water", "Water shaders."),
    7: ("Displacement Alpha", "Drawn last, applies displacement to everything "
        "in the scene. Only with 'glass_displacement'."),
}

# Surface type -> shader family. A shortcut for "what do I use for this".
# The Turkish keys (cam, kumas, arac, su, cim) are intentional: Turkish input
# stays accepted next to the English words.
SHADER_WORK_TYPES = {
    "decal":    ("decal", "A stain/mark/text that sticks to a surface. Placed on a "
                 "FLAT PLANE, sits 1-2 cm above the ground."),
    "cam":      ("glass", "Transparent surface."),
    "glass":    ("glass", "Transparent surface."),
    "emissive": ("emissive", "A surface with its own light (sign, screen, LED)."),
    "terrain":  ("terrain", "Multi-layer ground blended with vertex color."),
    "kumas":    ("cloth", "Fabric that ripples in the wind."),
    "cloth":    ("cloth", "Fabric that ripples in the wind."),
    "arac":     ("vehicle", "Vehicle body/part."),
    "su":       ("water", "Water surface."),
    "water":    ("water", "Water surface."),
    "ped":      ("ped", "Character skin/clothing."),
    "cim":      ("grass", "Grass / vegetation cover."),
    "grass":    ("grass", "Grass / vegetation cover."),
}


SHADERUSE = os.path.join(DATA, "shader_usage.tsv")


def shader_usage():
    """Shader usage measured from vanilla files.

    MEASURED (12,000 ydr + 12,000 yft): 92.3% of decal shader uses are with
    render bucket 2 (Decal); bucket 0 (Opaque) was seen only once in 5482 uses.
    The Sollumz default is Opaque -- so if it is not changed it is almost
    certainly WRONG.
    """
    if not os.path.exists(SHADERUSE):
        return {}
    out = {}
    with open(SHADERUSE, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            b = {}
            for part in (r.get("buckets") or "").split(";"):
                if ":" in part:
                    k, v = part.split(":")
                    b[int(k)] = int(v)
            out[r["shader"]] = {"total": int(r["total"]), "buckets": b}
    return out


def cmd_shader(args):
    """GTA V shader table: which shader, which textures and parameters it wants.

    A wrong shader is a SILENT failure: the model loads but draws wrong --
    a decal comes out opaque, glass is not transparent, emissive does not glow.
    """
    if not os.path.exists(SHADERTSV):
        die_layer(f"{SHADERTSV} not found.\n  Build: python scripts/build_shaders.py")

    with open(SHADERTSV, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        records = [dict(zip(header, l.rstrip("\n").split("\t"))) for l in fh if l.strip()]

    q = (args.query or "").lower().strip()
    hint = None
    if q in SHADER_WORK_TYPES:
        q, hint = SHADER_WORK_TYPES[q]

    if args.exact:
        found = [k for k in records if k["name"] == args.query]
    else:
        found = [k for k in records if not q or q in k["name"].lower()]

    if not found:
        print(f"No shader matches '{args.query}' ({len(records)} shaders exist).")
        return 1

    if hint:
        print(f"\n  [{args.query}] -> '{q}' family. {hint}")

    if args.buckets or q in ("decal", "glass", "water", "cutout"):
        print("\n  RENDER BUCKET (per material, a field SEPARATE from the shader):")
        for v, (name, description) in RENDER_BUCKET.items():
            print(f"    {v}  {name:<20} {description}")
        print("  Sollumz sets the bucket BY SHADER itself -- MEASURED LIVE:")
        print("    default.sps -> OPAQUE   decal/decal_dirt/normal_decal/water_decal -> DECAL")
        print("    cutout.sps  -> CUTOUT   alpha/glass/vehicle_decal -> ALPHA")
        print("  So if you pick the RIGHT SHADER you do not need to touch the bucket by hand.")
        print("  !! THE REAL PITFALL: making a decal and leaving the 'default' shader. Then")
        print("     the bucket stays OPAQUE, alpha DOES NOT WORK and no error is given.")

    usage = shader_usage()

    # a single result or --exact: full dump
    if len(found) == 1 or args.exact:
        for r in found:
            print(f"\n=== {r['name']} ===")
            if r["flags"]:
                print(f"  flags     : {r['flags']}")
            u = usage.get(r["name"])
            if u:
                print(f"  VANILLA USAGE: {u['total']} times")
                for b, n in sorted(u["buckets"].items(), key=lambda x: -x[1]):
                    name = RENDER_BUCKET.get(b, ("?", ""))[0]
                    print(f"    render bucket {b} ({name}): {n}")
            elif usage:
                print("  VANILLA USAGE: not seen in the scanned sample")
            print(f"  TEXTURES ({r['texCount']}):")
            for tex in (r["textures"].split(";") if r["textures"] else []):
                print(f"    {tex}")
            print(f"  PARAMETERS ({r['valCount']}):")
            for p in (r["params"].split(";") if r["params"] else []):
                print(f"    {p}")
        return 0

    print(f"\n{len(found)} shaders" + (f" (containing '{q}')" if q else "") + "\n")
    for r in found[: args.limit]:
        print(f"  {r['name']:<38} textures={r['texCount']:<3} params={r['valCount']:<3} "
              f"{r['textures'][:46]}")
    if len(found) > args.limit:
        print(f"\n  ... {len(found)-args.limit} more (--limit)")
    print("\n  For the full parameter list: assetdb.py shader <full_name> --exact")
    return 0


MATTSV = os.path.join(DATA, "collision_materials.tsv")

# Collision material FLAGS (a 4x4 grid in the Sollumz UI).
# The material's own flags; SEPARATE from the bound composite flags.
COLL_FLAGS = [
    "STAIRS", "NOT COVER", "NO DECAL", "NO PTFX",
    "NOT CLIMBABLE", "WALKABLE PATH", "NO NAVMESH", "TOO STEEP FOR PLAYER",
    "SEE THROUGH", "NO CAM COLLISION", "NO RAGDOLL", "NO NETWORK SPAWN",
    "SHOOT THROUGH", "SHOOT THROUGH FX", "VEHICLE WHEEL",
    "NO CAM COLLISION ALLOW CLIPPING",
]

# Bound COMPOSITE flags -- a layer COMPLETELY SEPARATE from the material flags.
# Sollumz ybn/properties.py::BoundFlags, 31 flags. An object carries TWO sets:
#   composite_flags1 = "Type Flags"    (WHAT this bound is)
#   composite_flags2 = "Include Flags" (WHAT this bound collides with)
COMPOSITE_FLAGS = [
    "UNKNOWN", "MAP WEAPON", "MAP DYNAMIC", "MAP ANIMAL", "MAP COVER",
    "MAP VEHICLE", "VEHICLE NOT BVH", "VEHICLE BVH", "PED", "RAGDOLL",
    "ANIMAL", "ANIMAL RAGDOLL", "OBJECT", "OBJECT_ENV_CLOTH", "PLANT",
    "PROJECTILE", "EXPLOSION", "PICKUP", "FOLIAGE", "FORKLIFT FORKS",
    "TEST WEAPON", "TEST CAMERA", "TEST AI", "TEST SCRIPT",
    "TEST VEHICLE WHEEL", "GLASS", "MAP RIVER", "SMOKE", "UNSMASHED",
    "MAP STAIRS", "MAP DEEP SURFACE",
]


def cmd_mat(args):
    """Collision material table: index, name, colour, density.

    Source: Sollumz 2.9 ybn/collision_materials.py (185 materials, list order
    = the game's material index). Cross-checked: ANIMAL_DEFAULT = 171, the same
    as an earlier, independent measurement.
    """
    if not os.path.exists(MATTSV):
        die_layer(f"{MATTSV} not found.")

    with open(MATTSV, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        records = [dict(zip(header, l.rstrip("\n").split("\t"))) for l in fh if l.strip()]

    if args.index is not None:
        r = next((k for k in records if int(k["index"]) == args.index), None)
        if r is None:
            print(f"material index {args.index} does not exist (0-{len(records)-1}).")
            return 1
        print(f"\n[{r['index']}] {r['name']}   \"{r['ui_name']}\"")
        print(f"  colour    rgb({r['r']}, {r['g']}, {r['b']})")
        print(f"  density   {r['density']}")
        return 0

    q = (args.query or "").lower()
    found = [k for k in records
             if not q or q in k["name"].lower() or q in k["ui_name"].lower()]
    if not found:
        print("no match.")
        return 1

    print(f"\n{len(found)} materials" + (f" (filter: {args.query})" if q else
                                         f" / {len(records)} total") + "\n")
    for r in found[: args.limit]:
        print(f"  {r['index']:>4}  {r['name']:<30} {r['ui_name']:<28} "
              f"density={r['density']}")
    if len(found) > args.limit:
        print(f"\n  ... {len(found)-args.limit} more rows (--limit)")

    print("\n  MATERIAL FLAGS (the material's own flags, SEPARATE from composite):")
    for i in range(0, len(COLL_FLAGS), 4):
        print("    " + "  ".join(f"{f:<32}" for f in COLL_FLAGS[i:i+4]).rstrip())
    print("\n  COMPOSITE FLAGS -- A SEPARATE LAYER (31 flags, TWO sets:")
    print("  'Type Flags' = composite_flags1, 'Include Flags' = composite_flags2):")
    for i in range(0, len(COMPOSITE_FLAGS), 4):
        print("    " + "  ".join(f"{f:<22}" for f in COMPOSITE_FLAGS[i:i+4]).rstrip())
    print("\n  Pool/water measurement (vanilla): MAP WEAPON + MAP DYNAMIC + MAP ANIMAL")
    print("  + MAP COVER + MAP RIVER; material WATER, flags SEE THROUGH +")
    print("  SHOOT THROUGH + NO CAM COLLISION.")

    presets_path = os.path.join(DATA, "collision_flag_presets.tsv")
    if os.path.exists(presets_path):
        with open(presets_path, encoding="utf-8") as fh:
            header = fh.readline().rstrip("\n").split("\t")
            presets = [dict(zip(header, l.rstrip("\n").split("\t"))) for l in fh if l.strip()]
        print("\n  READY COMPOSITE PRESETS (the Sollumz 'Flag Presets' button):")
        for p in presets:
            type_flags = p["typeFlags"].split(";") if p["typeFlags"] else []
            include_flags = p["includeFlags"].split(";") if p["includeFlags"] else []
            print(f"    {p['name']:<20} type={len(type_flags):>2} include={len(include_flags):>2}")
        general = next((p for p in presets if p["name"].startswith("General (Default)")), None)
        if general:
            print("    -> 'General (Default)' is the right set for an ordinary map object:")
            print(f"       type   : {general['typeFlags'].replace(';', ' + ')}")
            print(f"       include: {general['includeFlags'].replace(';', ' + ')}")

    print("\n  Door standard: NOT COVER + NOT CLIMBABLE")
    print("  CAUTION: mesh collision + the 'Dynamic' archetype flag = the object DOES NOT")
    print("  INTERACT with world collision, it falls through the ground. On a dynamic")
    print("  object the collision must be a PRIMITIVE (bound box / cylinder).")
    return 0


def cmd_lodaudit(args):
    """Compares our own ymaps with vanilla behaviour.

    An absolute number means nothing; the YARDSTICK is vanilla. If we have a
    combination never seen in Rockstar's 3.07M entities, that is a defect.
    """
    LOD_PARENT = 1 << 3          # 'LOD in Parented YMAP'
    ADOPT_ME = 1 << 4            # 'LOD Adopt Me'

    counts = {"v_n": 0, "c_n": 0}
    defects = collections.defaultdict(lambda: {"v": 0, "c": 0})
    where_found = collections.Counter()

    for r in lod_rows():
        vanilla = ".rpf" in r["rpfPath"].lower()
        counts["v_n" if vanilla else "c_n"] += 1
        try:
            f = int(r["flags"])
            pi = int(r["parentIndex"])
            nc = int(r["numChildren"])
        except ValueError:
            continue

        findings = []
        if (f & LOD_PARENT) and pi < 0:
            findings.append("'LOD in Parented YMAP' bit set but parentIndex=-1")
        if (f & ADOPT_ME) and nc == 0:
            findings.append("'LOD Adopt Me' bit set but it has no children")
        if pi >= 0 and not r["parentYmap"]:
            findings.append("has a parentIndex but the ymap DECLARES NO parent")

        for b in findings:
            defects[b]["v" if vanilla else "c"] += 1
            if not vanilla:
                where_found[(b, r["ymap"])] += 1

    print(f"\nVANILLA {counts['v_n']} entities  |  OURS {counts['c_n']} entities\n")
    if not defects:
        print("  no inconsistency at all.")
        return 0

    for b, d in sorted(defects.items(), key=lambda x: -x[1]["c"]):
        vo = 100 * d["v"] / max(counts["v_n"], 1)
        co = 100 * d["c"] / max(counts["c_n"], 1)
        stamp = "  <-- NEVER IN VANILLA" if d["v"] == 0 and d["c"] else ""
        print(f"  {b}")
        print(f"     vanilla {d['v']:>8} ({vo:.2f}%)   ours {d['c']:>6} ({co:.2f}%){stamp}")
        top = [(ym, n) for (bb, ym), n in where_found.items() if bb == b]
        for ym, n in sorted(top, key=lambda x: -x[1])[:5]:
            print(f"       {ym:<40} {n}")
        print()

    print("  Verdict: everything above the vanilla rate is a defect of YOUR map.")
    print("  A combination that is ZERO in vanilla is certainly wrong --")
    print("  Rockstar never got into that state even once across 3M entities.")
    return 0


def cmd_lodchain(args):
    """Walks an archetype's REAL LOD chain from vanilla.

    Instead of describing how a chain should be built, it shows a working
    example: which ymap, which index, which distance, which flag.
    """
    target = args.name.lower()
    ent = collections.defaultdict(dict)
    parents = {}
    start = []

    for r in lod_rows():
        ent[r["ymap"]][int(r["idx"])] = r
        if r["parentYmap"]:
            parents[r["ymap"]] = r["parentYmap"]
        if target in r["archetype"].lower() and not start:
            start.append((r["ymap"], int(r["idx"])))

    if not start:
        print(f"'{args.name}' was not found in any ymap.")
        return 1

    def resolve(name):
        n = name if name.endswith(".ymap") else name + ".ymap"
        return n if n in ent else None

    ym, i = start[0]
    print(f"\nLOD CHAIN  <- {ent[ym][i]['archetype']}\n")
    for step in range(12):
        r = ent[ym][i]
        flag_names = decode_flags(r["flags"], ENTITY_FLAGS)
        print(f"  {step}. {r['archetype']}")
        print(f"     {r['lodLevel']}   ymap={r['ymap']} idx={i}")
        print(f"     lodDist={r['lodDist']}  childLodDist={r['childLodDist']}  "
              f"children={r['numChildren']}  priority={r['priority']}")
        if flag_names:
            print(f"     flags={r['flags']} -> {' | '.join(flag_names)}")
        pi = int(r["parentIndex"])
        if pi < 0:
            print("     parentIndex=-1  ->  END OF CHAIN")
            break
        parent_ymap = parents.get(ym)
        if not parent_ymap:
            print(f"     parentIndex={pi} but this ymap DECLARES NO parent -> cannot be followed")
            break
        parent_name = resolve(parent_ymap)
        if not parent_name or pi not in ent[parent_name]:
            print(f"     parentIndex={pi} -> {parent_ymap}  (NO entity at that index: broken chain)")
            break
        print(f"     parentIndex={pi}  ->  {parent_ymap}")
        print()
        ym, i = parent_name, pi
    return 0


PROCTSV = os.path.join(DATA, "procedural.tsv")


def cmd_proc(args):
    """Procedural plant/object table -- the 'Procedural ID' in a collision material.

    The only source that says WHAT will grow where you write that number into
    a ground collision. ID = the INDEX in <procTagTable> inside procedural.meta
    (not procObjInfos; the two are separate lists).
    """
    if not os.path.exists(PROCTSV):
        die_layer(f"{PROCTSV} not found.\n"
                  "  Build: powershell -NoProfile -ExecutionPolicy Bypass "
                  "-File scripts/build_procedural.ps1")

    with open(PROCTSV, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        records = [dict(zip(header, l.rstrip("\n").split("\t")))
                   for l in fh if l.strip()]

    # 'bos' (empty) is the kind value build_procedural.ps1 writes for an unused
    # index; it is data and stays as it is.
    unused_kind = "bos"

    if args.id is not None:
        r = next((k for k in records if int(k["id"]) == args.id), None)
        if r is None:
            print(f"Procedural ID {args.id} is outside the table (0-{len(records)-1}).")
            return 1
        print(f"\nProcedural ID {r['id']}  ->  {r['name']}")
        print(f"  kind       {r['kind']}")
        if r["procObjTag"]:
            print(f"  procObjTag {r['procObjTag']}   (solid object: rock/litter/bush model)")
        if r["plantTag"]:
            print(f"  plantTag   {r['plantTag']}   (grass/plant, drawn by a shader)")
        if r["models"]:
            print(f"  models     {r['models']}")
        if r["kind"] == unused_kind:
            print("  !! This index is NOT USED -- write it into the ground and nothing grows.")
        return 0

    q = (args.query or "").lower()
    found = [k for k in records
             if k["kind"] != unused_kind
             and (not q or q in k["name"].lower() or q in k["models"].lower())]
    if not found:
        print("no match.")
        return 1

    print(f"\n{len(found)} filled procedural IDs"
          f"{' (filter: ' + args.query + ')' if q else f' / {len(records)} total'}\n")
    for r in found[: args.limit]:
        line = f"  {r['id']:>4}  {r['name']:<34} {r['kind']}"
        if r["models"]:
            line += f"  [{r['models'][:52]}]"
        print(line)
    if len(found) > args.limit:
        print(f"\n  ... {len(found) - args.limit} more rows (--limit)")
    print("\n  Usage: this number goes into the 'Procedural ID' field of the collision material.")
    print("  But the grass system is very sensitive: if the triangles are small nothing")
    print("  appears, and if the game's 'Grass Quality' setting is low it NEVER shows.")
    return 0


def cmd_flags(args):
    """Decodes a flag integer into names.

    The source tables were taken verbatim from Sollumz 2.9
    ytyp/properties/flags.py; bit mapping flagN -> 2**(N-1) (see the note above
    ARCH_FLAGS).
    """
    raw = args.value.strip()
    try:
        value = int(raw, 0)
    except ValueError:
        print(f"invalid number: {raw}")
        return 1

    table, kind = (ENTITY_FLAGS, "ENTITY (ymap)") if args.entity else (ARCH_FLAGS, "ARCHETYPE (ytyp)")
    names = decode_flags(value, table)

    print(f"\n{value}  ({value:#x})  ->  {kind} flag")
    if not names:
        print("   (no bit set)")
        return 0
    for name in names:
        if name.startswith(UNDECODED_PREFIX):
            print(f"   {name}")
            continue
        bit = table.index(name)
        print(f"   {1 << (bit - 1):>12}  bit{bit - 1:<2}  {name}")

    if not args.entity and value & ARCH_FLAG_DOOR_PHYSICS:
        print("\n   NOTE: 'Enable Door Physics' is set -> the door system can work on")
        print("         this object even when specialAttribute is not a door type.")
    return 0


FRAMEWORK = os.path.join(DATA, "framework_api.tsv.gz")


def cmd_framework(args):
    """Framework API: export / event / callback / command / ox_lib module.

    WHY: lint only validates GTA NATIVEs. But most bugs in a QBCore/ox resource
    are in framework calls and NONE of them throws an error: an event that does
    not exist goes nowhere when triggered; an export that does not exist gives
    'nil value' only when that line RUNS - maybe once a month.

    The authority is the resources INSTALLED ON THE SERVER, not upstream GitHub.
    """
    rows = list(dump_rows(FRAMEWORK, "framework API"))
    installed = {r["name"].lower() for r in rows if r["kind"] == "resource"}

    if args.check:
        defined_exports = {(r["resource"].lower(), r["name"].lower())
                           for r in rows if r["kind"] == "export"}
        defined_events = {r["name"].lower() for r in rows if r["kind"] == "event"}
        modules = {r["name"].lower() for r in rows if r["kind"] == "lib_module"}
        missing_res, typos, events, libs = collections.Counter(), collections.Counter(), \
            collections.Counter(), collections.Counter()
        for r in rows:
            if r["kind"] == "export_use":
                res, _, name = r["name"].partition(":")
                if res.lower() not in installed:
                    missing_res[res.lower()] += 1
                elif (res.lower(), name.lower()) not in defined_exports:
                    typos[r["name"]] += 1
            elif r["kind"] == "event_use" and r["name"].lower() not in defined_events:
                events[r["name"]] += 1
            elif r["kind"] == "lib_use" and r["name"].lower() not in modules:
                libs[r["name"]] += 1
        # The unit words are localised inline: "kaynak" / "benzersiz" are the
        # Turkish output for --lang tr.
        print(t("fw_a"))
        for k, n in missing_res.most_common(args.limit):
            print(f"   {n:>4}x  {k}")
        print("   " + t("fw_calls", n=sum(missing_res.values()), u=len(missing_res),
                        unit="resources" if get_lang() == "en" else "kaynak") + "\n")
        print(t("fw_b"))
        for k, n in typos.most_common(args.limit):
            print(f"   {n:>4}x  {k}")
        print("   " + t("fw_calls", n=sum(typos.values()), u=len(typos), unit="unique" if get_lang() == "en" else "benzersiz"))
        print(f"   {t('note')}: {t('fw_b_note')}\n")
        print(t("fw_c"))
        for k, n in events.most_common(args.limit):
            print(f"   {n:>4}x  {k}")
        print("   " + t("fw_calls", n=sum(events.values()), u=len(events), unit="unique" if get_lang() == "en" else "benzersiz"))
        print(f"   {t('note')}: {t('fw_c_note')}\n")
        print(t("fw_d"))
        for k, n in libs.most_common(args.limit):
            print(f"   {n:>4}x  {k}")
        print("   " + t("fw_calls", n=sum(libs.values()), u=len(libs), unit="unique" if get_lang() == "en" else "benzersiz"))
        return EXIT_OK

    q = args.query.lower() if args.query else ""
    hits = [r for r in rows if r["kind"] != "resource"
            and (not q or q in r["name"].lower() or q in r["resource"].lower())]
    if args.kind:
        hits = [r for r in hits if r["kind"] == args.kind]
    if args.defs:
        hits = [r for r in hits if not r["kind"].endswith("_use")]
    for r in hits[:args.limit]:
        v = f" v{r['version']}" if r["version"] else ""
        print(f"  {r['kind']:<13} {r['name']:<48} [{r['resource']}{v}] "
              f"{r['side']:<7} {r['file']}:{r['line']}")
    extra = len(hits) - args.limit
    print("\n" + t("results", n=len(hits))
          + (t("hidden", n=extra) if extra > 0 else "")
          + "   |  " + t("fw_scanned", n=len(installed)))
    return EXIT_NOTFOUND if not hits else EXIT_OK


def layer_inventory():
    """PRESENT/MISSING state + size of every data layer.

    WHY: a missing layer silently produces "0 results" and the caller reads that
    as "asset not found". Without the inventory, "nothing was checked" and
    "everything is clean" look like the same screen.
    """
    layers = [
        ("archetypes.tsv.gz", TSV), ("entities.db", ENTDB), ("ymap_lod.tsv.gz", LODTSV),
        ("clips.tsv.gz", CLIPS), ("anims.tsv.gz", ANIMS), ("props.tsv.gz", PROPS),
        ("scenarios.tsv.gz", SCENARIOS), ("expressions.tsv.gz", EXPRS),
        ("ytyp_extensions.tsv.gz", EXT_TSV), ("ptfx_effects.tsv.gz", PTFXTSV),
        ("shaders.tsv", SHADERTSV), ("collision_materials.tsv", MATTSV),
        ("decal_types.tsv", DECALTSV), ("procedural.tsv", PROCTSV),
        # --- dump layers ---
        ("peds_meta.tsv.gz", PEDMETA), ("weapons.tsv.gz", WEAPONS),
        ("weapon_parts.tsv.gz", WPNPARTS), ("vehicles.tsv.gz", VEHICLES),
        ("mlo_interiors.tsv.gz", MLOS), ("ipls.tsv.gz", IPLS),
        ("world_objects.tsv.gz", WORLDOBJ),
        ("framework_api.tsv.gz", FRAMEWORK),
        # --- lights / timecycle ---
        ("lights.tsv.gz", os.path.join(DATA, "lights.tsv.gz")),
        ("timecycle.tsv.gz", os.path.join(DATA, "timecycle.tsv.gz")),
    ]
    print(t("inventory"))
    missing = 0
    for name, path in layers:
        if os.path.exists(path):
            mb = os.path.getsize(path) / (1024 * 1024)
            print(f"  [{t('inv_present')}] {name:<26} {mb:>8.2f} MB")
        else:
            missing += 1
            print(f"  [{t('inv_missing')}] {name:<26}        - {t('inv_missing_note')}")
    dm = os.path.join(DATA, "dumps.meta.json")
    if os.path.exists(dm):
        try:
            with open(dm, encoding="utf-8-sig") as fh:
                d = json.load(fh)
            print(f"\n  {t('dump_version'):<12}: {d.get('gameVersion') or '?'}")
            print(f"  {t('built_at'):<12}: {d.get('generatedAtUtc') or '?'}")
        except Exception:
            pass
    print("\n  " + t("inv_installed", n=len(layers) - missing, t=len(layers))
          + (t("inv_missing_count", n=missing) if missing else ""))
    return missing


def cmd_stats(args):
    """Layer inventory + archetype distribution.

    ⛔ stats NEVER RETURNS EXIT 2. This command is the answer to "what is
    installed?"; it failing because of a missing layer is like a fire alarm
    failing because of a fire. A new user runs this first - if they get an
    error here they lose the place where they would learn what is missing.
    """
    missing = layer_inventory()
    print()
    if os.path.exists(META):
        with open(META, encoding="utf-8-sig") as fh:
            print(json.dumps(json.load(fh), indent=2, ensure_ascii=False))
    if not os.path.exists(TSV):
        print("\nArchetype distribution: archetypes.tsv.gz is not installed (HEAVY layer).")
        print("  Build: powershell -File scripts/build_archetypes.ps1  (needs GTA V + CodeWalker)")
        return EXIT_OK
    dist, total = {}, 0
    for r in rows():
        total += 1
        dist[r["specialAttribute"]] = dist.get(r["specialAttribute"], 0) + 1
    print(f"\nTotal archetypes: {total}")
    print("specialAttribute distribution:")
    for k, v in sorted(dist.items(), key=lambda kv: -kv[1]):
        label = SPECIAL.get(int(k), ("?", ""))[0]
        print(f"  {k:>4} : {v:>7}   {label}")
    return EXIT_OK


# ============================================================================
# DUMP LAYERS (built by build_dumps.py) - ped meta, weapons, vehicles, MLOs,
# IPLs, world objects. Source: DurtyFree/gta-v-data-dumps.
#
# JOIN RULE: the name columns of these layers are written in the SOURCE's
# letter case (W_AR_ASSAULTRIFLE), the plugin's own layers are lower case.
# Comparison is ALWAYS done via .lower(). An exact join returns 0 for every
# family and that is SILENT: the table looks full, the match comes out empty,
# and "this model does not exist" gets said.
# ============================================================================
PEDMETA = os.path.join(DATA, "peds_meta.tsv.gz")
WEAPONS = os.path.join(DATA, "weapons.tsv.gz")
WPNPARTS = os.path.join(DATA, "weapon_parts.tsv.gz")
VEHICLES = os.path.join(DATA, "vehicles.tsv.gz")
MLOS = os.path.join(DATA, "mlo_interiors.tsv.gz")
IPLS = os.path.join(DATA, "ipls.tsv.gz")
WORLDOBJ = os.path.join(DATA, "world_objects.tsv.gz")


def dump_rows(path, what):
    """Gzip TSV with a header -> dict stream. Column names come from the header
    line, so this does not have to change when build_dumps.py adds a column."""
    if not os.path.exists(path):
        die_layer(f"{os.path.basename(path)} not found ({what}).\n"
                  "  Build: python scripts/build_dumps.py --dump <gta-v-data-dumps folder>")
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        cols = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == len(cols):
                yield dict(zip(cols, parts))


def cmd_pedmeta(args):
    """Ped profile: which clip dictionary, which expression, which movement clipset.

    WHY: in ped animation/face work the question "which expression does this
    ped consume" gets guessed, and a wrong match SILENTLY produces a wrong face.
    """
    q = args.query.lower()
    hits = [r for r in dump_rows(PEDMETA, "ped meta") if q in r["name"].lower()]
    for r in hits[:args.limit]:
        print(f"\n=== {r['name']} ===  [{r['pedtype'] or '?'}]  dlc={r['dlc'] or '-'}"
              f"  {t('ped_bones')}={r['boneCount']}")
        print(f"  {t('ped_clipdict'):<17}: {r['clipDict'] or '-'}")
        print(f"  expression       : set={r['exprSet'] or '-'}  "
              f"dict={r['exprDict'] or '-'}  name={r['exprName'] or '-'}")
        print(f"  {t('ped_movement'):<17}: {r['movementClipSet'] or '-'}")
        print(f"  {t('ped_strafe'):<17}: {r['strafeClipSet'] or '-'} / {r['gestureClipSet'] or '-'}")
        print(f"  {t('ped_face'):<17}: {r['visemeClipSet'] or '-'} / {r['facialClipsetGroup'] or '-'}")
        if r.get("propsName"):
            print(f"  {t('ped_props'):<17}: {r['propsName']}")
        if r.get("voiceGroup"):
            print(f"  {t('ped_voice'):<17}: {r['voiceGroup']}")
    extra = len(hits) - args.limit
    print("\n" + t("results", n=len(hits))
          + (t("hidden", n=extra) if extra > 0 else ""))
    if hits:
        print(f"{t('note')}: {t('ped_clipset_note')}")
    return EXIT_NOTFOUND if not hits else EXIT_OK


def cmd_weapon(args):
    """Weapon profile + components. Components and liveries are in the SAME table (kind column)."""
    q = args.query.lower()
    hits = [r for r in dump_rows(WEAPONS, "weapons")
            if q in r["name"].lower() or q in (r["model"] or "").lower()
            or q in (r["label"] or "").lower()]
    parts = {}
    if hits:
        names = {r["name"].lower() for r in hits}
        for pr in dump_rows(WPNPARTS, "weapon parts"):
            if pr["weapon"].lower() in names:
                parts.setdefault(pr["weapon"].lower(), []).append(pr)
    for r in hits[:args.limit]:
        print(f"\n=== {r['name']} ===  {r['label']}")
        print(f"  {t('wpn_category'):<15}: {r['category']}  /  {r['damageType']}")
        print(f"  {t('wpn_model'):<15}: {r['model'] or t('wpn_no_model')}")
        print(f"  ammo           : {r['ammoType']}  model={r['ammoModel'] or '-'}"
              f"  sp={r['maxAmmoSp']} mp={r['maxAmmoMp']}")
        print(f"  {t('wpn_dlc_tint'):<15}: {r['dlc']}  /  {r['tints'] or '-'}")
        ps = parts.get(r["name"].lower(), [])
        comp = [x for x in ps if x["kind"] == "component"]
        liv = [x for x in ps if x["kind"] == "livery"]
        print(f"  components={len(comp)}  liveries={len(liv)}")
        if args.parts:
            for x in comp:
                d = "  [default]" if x["isDefault"] == "1" else ""
                print(f"    C {x['name']:<44} {t('ped_bones')}={x['attachBone'] or '-':<16}{d}")
            for x in liv:
                print(f"    L {x['name']:<44} {x['label']}")
    extra = len(hits) - args.limit
    print("\n" + t("results", n=len(hits))
          + (t("hidden", n=extra) if extra > 0 else ""))
    if hits and not args.parts:
        print(f"{t('tip')}: {t('wpn_parts_tip')}")
        print(f"{t('note')}: {t('wpn_livery_note')}")
    return EXIT_NOTFOUND if not hits else EXIT_OK


def cmd_vehicle(args):
    """Vehicle profile. handlingId matches a handling.meta override."""
    q = args.query.lower()
    hits = [r for r in dump_rows(VEHICLES, "vehicles")
            if q in r["name"].lower() or q in (r["displayName"] or "").lower()
            or q in (r["manufacturer"] or "").lower()]
    for r in hits[:args.limit]:
        print(f"\n=== {r['name']} ===  {r['displayName']}  ({r['manufacturer'] or '?'})")
        print(f"  class/type  : {r['class']} / {r['type']}   seats={r['seats']}"
              f"  wheels={r['wheelsCount']}")
        print(f"  handlingId  : {r['handlingId']}     layout={r['layoutId']}")
        print(f"  {t('veh_dlc_price'):<12}: {r['dlc']}  /  {r['price']}")
        if r.get("modKits"):
            print(f"  modKit      : {r['modKits']}")
        if r.get("extras"):
            print(f"  extra       : {r['extras']}")
    extra = len(hits) - args.limit
    print("\n" + t("results", n=len(hits))
          + (t("hidden", n=extra) if extra > 0 else ""))
    return EXIT_NOTFOUND if not hits else EXIT_OK


def cmd_mlo(args):
    """MLO interiors. One line PER LOCATION: the same interior sits in more than one place."""
    q = args.query.lower()
    hits = [r for r in dump_rows(MLOS, "MLO interiors") if q in r["name"].lower()]
    groups = {}
    for r in hits:
        groups.setdefault(r["name"], []).append(r)
    for name, rs in list(groups.items())[:args.limit]:
        r0 = rs[0]
        placed = [r for r in rs if r["x"]]
        print(f"\n=== {name} ===  dlc={r0['dlc'] or '-'}  entity={r0['entityCount']}")
        print(f"  ytyp: {r0['ytypPath'] or '-'}")
        if not placed:
            print(f"  {t('mlo_unplaced')}")
        for r in placed[:args.locations]:
            print(f"  vec3({r['x']}, {r['y']}, {r['z']})  flags={r['flags'] or '-'}")
        if len(placed) > args.locations:
            print("  " + t("mlo_more", n=len(placed) - args.locations))
        print("  -> " + t("mlo_locations", n=len(placed)))
    extra = len(groups) - args.limit
    print(f"\n{len(groups)} interior(s)" + (f" ({extra} not shown)" if extra > 0 else ""))
    if len(groups) > 1:
        print(f"{t('note')}: {t('mlo_variant_note')}")
    return EXIT_NOTFOUND if not groups else EXIT_OK


def cmd_ipl(args):
    """IPL name + bounding box. Name check for RequestIpl/RemoveIpl."""
    q = args.query.lower()
    hits = [r for r in dump_rows(IPLS, "IPLs")
            if q in r["name"].lower() or q in (r["group"] or "").lower()
            or q in (r["category"] or "").lower()]
    for r in hits[:args.limit]:
        location = f"vec3({r['x']}, {r['y']}, {r['z']})" if r["x"] else "(no location)"
        print(f"  {r['name']:<40} {location}  [{r['group'] or '-'} / {r['category'] or '-'}]")
    extra = len(hits) - args.limit
    print("\n" + t("results", n=len(hits))
          + (t("hidden", n=extra) if extra > 0 else ""))
    if hits:
        print(f"{t('usage')}: {t('ipl_usage')}")
    return EXIT_NOTFOUND if not hits else EXIT_OK


def cmd_world(args):
    """World objects: family label + location + ROTATION.

    entities.tsv.gz says "what is where" with 3M rows but cannot say "this is
    an ATM" and holds no rotation. Both, needed for loot/spawn points and prop
    swapping, are here.
    """
    rows = list(dump_rows(WORLDOBJ, "world objects"))
    if args.families:
        counts = collections.Counter(r["family"] for r in rows)
        models = collections.defaultdict(set)
        for r in rows:
            models[r["family"]].add(r["model"])
        for fam, n in counts.most_common():
            print(f"  {fam:<26} {n:>6} objects  {len(models[fam]):>3} models")
        print("\n" + t("world_families", f=len(counts), n=len(rows)))
        return EXIT_OK

    hits = rows
    if args.family:
        f = args.family.lower()
        hits = [r for r in hits if f in r["family"].lower()]
    if args.model:
        m = args.model.lower()
        hits = [r for r in hits if m in r["model"].lower()]
    if args.near:
        try:
            cx, cy, cz = [float(v) for v in args.near.split(",")]
        except ValueError:
            print(t("world_near_fmt"), file=sys.stderr)
            return EXIT_INTERNAL
        r2 = args.radius * args.radius
        nearby = []
        for r in hits:
            dx = float(r["x"]) - cx
            dy = float(r["y"]) - cy
            dz = float(r["z"]) - cz
            d2 = dx * dx + dy * dy + dz * dz
            if d2 <= r2:
                nearby.append((d2 ** 0.5, r))
        nearby.sort(key=lambda item: item[0])
        for d, r in nearby[:args.limit]:
            print(f"  {d:6.1f}m  {r['family']:<20} {r['model']:<34} "
                  f"vec3({r['x']}, {r['y']}, {r['z']})  rotZ={r['rz']}")
        print("\n" + t("world_within", n=len(nearby), r=args.radius))
        return EXIT_NOTFOUND if not nearby else EXIT_OK

    for r in hits[:args.limit]:
        print(f"  {r['family']:<20} {r['model']:<34} vec3({r['x']}, {r['y']}, {r['z']})"
              f"  rot({r['rx']}, {r['ry']}, {r['rz']})")
    extra = len(hits) - args.limit
    print("\n" + t("results", n=len(hits))
          + (t("hidden", n=extra) if extra > 0 else ""))
    return EXIT_NOTFOUND if not hits else EXIT_OK


def cmd_doctor(args):
    """Silent failure gate. Returns its own exit codes (see doctor.py):

        0 clean | 1 findings | 2 AT LEAST ONE FILE WAS NOT INSPECTED

    2 is the same number as EXIT_NOLAYER and that is DELIBERATE: a file that
    could not be inspected is not "clean", just as a layer that is not
    installed is not "no result".
    """
    import doctor  # lazy: other commands should not pay the subprocess/tempfile import cost
    return doctor.run(args)


def cmd_timecycle(args):
    """Timecycle modifier query. 0 found | 1 not found | 2 layer not installed."""
    import timecycle
    return timecycle.run(args)


def cmd_cycle(args):
    """Weather cycle at an hour. 0 ok | 1 not found | 2 layer not installed."""
    import cycle
    return cycle.run(args)


def cmd_path(args):
    """External tool paths. 0 all found | 1 missing / not found | 2 invalid path."""
    import paths
    return paths.run(args)


def cmd_light(args):
    """Decode/edit embedded lights. 0 ok | 1 no lights | 2 file could not be read.

    Both modes live in one command because both start with the same step
    (decode the file): reading is the default, writing is (--apply/--set/--add/--remove).
    """
    if any([getattr(args, "apply", None), getattr(args, "set", None),
            getattr(args, "add", False), getattr(args, "remove", None)]):
        import light_edit
        return light_edit.run(args)
    import light
    return light.run(args)


def cmd_diff(args):
    """Structural diff. 0 no difference | 1 differences | 2 file could not be read."""
    import structural_diff
    return structural_diff.run(args)


def main():
    p = argparse.ArgumentParser(
        description="muto-atlas — GTA V / FiveM ground-truth asset database")
    add_lang_arg(p)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="archetype details + interpretation")
    s.add_argument("names", nargs="+")
    s.add_argument("--raw", action="store_true", help="no interpretation, raw fields only")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("door", help="decides whether it opens like a door")
    s.add_argument("names", nargs="+")
    s.set_defaults(func=cmd_door)

    s = sub.add_parser("search", help="search by name")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("where", help="where the archetype is in the world (ymap + MLO interior)")
    s.add_argument("names", nargs="+")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_where)

    s = sub.add_parser("near", help="what is around a coordinate")
    s.add_argument("x", type=float)
    s.add_argument("y", type=float)
    s.add_argument("z", type=float)
    s.add_argument("--radius", type=float, default=10.0)
    s.add_argument("--filter", help="part that must appear in the name (e.g. door)")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_near)

    s = sub.add_parser("anim", help="animation dict/clip search")
    s.add_argument("query")
    s.add_argument("--dict", action="store_true", help="treat the query as the EXACT dictionary name, list its clips")
    s.add_argument("--dict-only", action="store_true", help="search only in dictionary names")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_anim)

    s = sub.add_parser("bones", help="a model's skeleton: bone name + tag")
    s.add_argument("names", nargs="+")
    s.add_argument("--limit", type=int, default=60)
    s.set_defaults(func=cmd_bones)

    s = sub.add_parser("clipfit", help="which model can play this clip (bone tag match)")
    s.add_argument("dict")
    s.add_argument("clip")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_clipfit)

    s = sub.add_parser("expr", help="expression (.yed) search - procedural/spring motion")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_expr)

    s = sub.add_parser("prop", help="spawnable prop search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_prop)

    s = sub.add_parser("scenario", help="ped scenario search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_scenario)

    s = sub.add_parser("propanim", help="a PROP's real animations (clip name = prop model name)")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=6, help="how many props to show")
    s.add_argument("--dicts", type=int, default=8, help="dicts per prop")
    s.set_defaults(func=cmd_propanim)

    s = sub.add_parser("ptfx", help="particle extension search (prop name / effect name / fxType)")
    s.add_argument("query", nargs="?", default="", help="part of a prop name or effect name")
    s.add_argument("--type", type=int, choices=range(8), metavar="0-7",
                   help="fxType: 0=Ambient 1=Collision 2=Shot 3=Break 4=Destroy "
                        "5=Anim(unused) 6=RayFire 7=InWater")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_ptfx)

    s = sub.add_parser("fx", help="particle EFFECT catalog (.ypt): does the effect exist, in which ypt")
    s.add_argument("query", nargs="?", default="", help="effect name or part of it")
    s.add_argument("--exact", action="store_true", help="exact name; if missing it says so and suggests similar ones")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_fx)

    s = sub.add_parser("ext", help="ALL ytyp extensions of an archetype")
    s.add_argument("name", help="archetype name (a part works too)")
    s.set_defaults(func=cmd_ext)

    s = sub.add_parser("lod", help="vanilla lodDist reference + LOD chain rules")
    s.add_argument("--size", type=float, metavar="M",
                   help="the object's longest edge (m) -> suggested lodDist")
    s.set_defaults(func=cmd_lod)

    s = sub.add_parser("proc", help="procedural grass/object table (collision 'Procedural ID')")
    s.add_argument("query", nargs="?", default="", help="part of a name or model")
    s.add_argument("--id", type=int, help="decode one Procedural ID")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_proc)

    s = sub.add_parser("decal", help="decalType table (194) -- the first argument of AddDecal()")
    s.add_argument("query", nargs="?", default="",
                   help="work type: blood/bullet/footprint/burn/oil/petrol/mud/water/vehicle")
    s.add_argument("--id", type=int, help="decode one decalType")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_decal)

    s = sub.add_parser("shader", help="GTA V shader table (249): textures + parameters")
    s.add_argument("query", nargs="?", default="",
                   help="part of a name or work type: decal/glass/emissive/terrain/cloth/water/grass")
    s.add_argument("--exact", action="store_true", help="exact name, print all parameters")
    s.add_argument("--buckets", action="store_true", help="also print the render bucket table")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_shader)

    s = sub.add_parser("mat", help="collision material table (185 materials + flags)")
    s.add_argument("query", nargs="?", default="", help="part of a name, e.g. 'metal' / 'glass'")
    s.add_argument("--index", type=int, help="decode one material index")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_mat)

    s = sub.add_parser("lodaudit", help="compares your own ymaps with vanilla behaviour")
    s.set_defaults(func=cmd_lodaudit)

    s = sub.add_parser("lodchain", help="walks an archetype's REAL LOD chain from vanilla")
    s.add_argument("name", help="archetype name (a part works too)")
    s.set_defaults(func=cmd_lodchain)

    s = sub.add_parser("flags", help="decodes a flag integer into names (archetype/entity)")
    s.add_argument("value", help="flag value, e.g. 1572872 or 0x180008")
    s.add_argument("--entity", action="store_true",
                   help="decode as a ymap ENTITY flag (default: archetype)")
    s.set_defaults(func=cmd_flags)

    s = sub.add_parser("pedmeta", help="ped profile: clip dictionary, expression, movement clipset")
    s.add_argument("query", help="ped name (a part works too)")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_pedmeta)

    s = sub.add_parser("weapon", help="weapon profile + component/livery names")
    s.add_argument("query", help="weapon name, model name or label")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--parts", "--parcalar", dest="parts", action="store_true",
                   help="list component and livery names")
    s.set_defaults(func=cmd_weapon)

    s = sub.add_parser("vehicle", help="vehicle profile (handlingId, modkit, extra)")
    s.add_argument("query", help="vehicle name, display name or manufacturer")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_vehicle)

    s = sub.add_parser("mlo", help="MLO interiors and their world locations")
    s.add_argument("query", help="interior name (a part works too)")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--locations", "--konum", dest="locations", type=int, default=5,
                   help="locations shown per interior")
    s.set_defaults(func=cmd_mlo)

    s = sub.add_parser("ipl", help="IPL name + bounding box (RequestIpl check)")
    s.add_argument("query", help="ipl name, group or category")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_ipl)

    s = sub.add_parser("world", help="world objects: family + location + ROTATION")
    s.add_argument("--families", "--aileler", dest="families", action="store_true",
                   help="list families and counts")
    s.add_argument("--family", help="family filter (atms, cctvs, seats ...)")
    s.add_argument("--model", help="model name filter")
    s.add_argument("--near", help="x,y,z - objects near this point")
    s.add_argument("--radius", "--mesafe", dest="radius", type=float, default=50.0,
                   help="--near radius in metres")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_world)

    s = sub.add_parser("framework", help="QBCore/ox/ESX export-event-callback index")
    s.add_argument("query", nargs="?", help="name or resource (empty: all)")
    s.add_argument("--kind", choices=["export", "export_use", "event", "event_use",
                                      "callback", "callback_use", "command",
                                      "lib_module", "lib_use", "resource"])
    s.add_argument("--defs", "--tanim", dest="defs", action="store_true",
                   help="definitions only (the authority)")
    s.add_argument("--check", "--denetle", dest="check", action="store_true",
                   help="cross-check usage against definitions (A/B/C/D report)")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_framework)

    s = sub.add_parser("doctor", help="silent failure gate: check an asset before it goes into the game")
    s.add_argument("paths", nargs="+",
                   help="file or folder (.ycd .ytyp .ymap ... or .xml)")
    s.add_argument("-r", "--recursive", action="store_true",
                   help="walk folders including their subfolders")
    s.add_argument("--level", choices=["fatal", "silent", "warn"], default="warn",
                   help="lowest severity to report (default: warn = all)")
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("timecycle", help="timecycle modifier: why is the interior dark")
    s.add_argument("name", nargs="?", help="modifier name (empty: summary)")
    s.add_argument("--search", "--ara", dest="search", help="search by name")
    s.add_argument("--mlo", help="rooms of an MLO ytyp -> timecycle + ambient")
    s.add_argument("--param", help="parameter name filter")
    s.add_argument("--sources", "--kaynak", dest="sources", action="store_true",
                   help="show ALL sources that define the same name")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_timecycle)

    s = sub.add_parser("cycle", help="weather timecycle at a given hour: ambient + sun")
    s.add_argument("weather", nargs="?", metavar="WEATHER",
                   help="w_clear, w_thunder ... (omit to list them)")
    s.add_argument("--hour", "--saat", dest="hour", type=float, default=12.0)
    s.add_argument("--region", "--bolge", dest="region", default="GLOBAL",
                   help="GLOBAL | URBAN")
    s.add_argument("--modifier", "--mod", dest="modifier", metavar="NAME",
                   help="timecycle modifier to blend on top")
    s.add_argument("--strength", "--guc", dest="strength", type=float, default=1.0)
    s.add_argument("--list", "--liste", dest="list", action="store_true")
    s.set_defaults(func=cmd_cycle)

    # "yol" is the old Turkish command name, still accepted as an alias.
    s = sub.add_parser("path", aliases=["yol"],
                       help="external tool paths: show / set (codewalker, gta, ...)")
    s.add_argument("name", nargs="?", metavar="NAME",
                   help="codewalker | gta | server | blender | <any name you choose>")
    s.add_argument("value", nargs="?", metavar="PATH",
                   help="new path (omit to just show it)")
    s.add_argument("--remove", "--sil", dest="remove", action="store_true",
                   help="drop the stored entry")
    s.set_defaults(func=cmd_path)

    s = sub.add_parser("light", help="decode and edit the lights embedded in a .ydr/.yft")
    s.add_argument("path", nargs="?", help=".ydr / .yft / .xml")
    s.add_argument("--table", "--tablo", dest="table", action="store_true",
                   help="print the measured vanilla light reference")
    s.add_argument("--raw", "--ham", dest="raw", action="store_true",
                   help="raw fields, undecoded")
    # --- write back
    s.add_argument("--apply", "--uygula", dest="apply", metavar="JSON",
                   help="write a JSON edit set back into the file")
    s.add_argument("--set", action="append", metavar="[IDX.]FIELD=VALUE",
                   help="set a field: --set 0.Intensity=8 (repeatable)")
    s.add_argument("--add", "--ekle", dest="add", action="store_true",
                   help="add a light by copying the first one")
    s.add_argument("--remove", "--sil", dest="remove", type=int, action="append",
                   metavar="IDX", help="remove a light (repeatable)")
    s.set_defaults(func=cmd_light)

    s = sub.add_parser("diff", help="compare two resources by NODE PRESENCE")
    s.add_argument("mine", help="your file (.yft .ydr .ycd ... or .xml)")
    s.add_argument("vanilla", help="the vanilla counterpart")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_diff)

    s = sub.add_parser("stats", help="index summary")
    s.set_defaults(func=cmd_stats)

    a = p.parse_args()
    set_lang(getattr(a, "lang", None))
    return a.func(a) or EXIT_OK


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BrokenPipeError:
        sys.exit(EXIT_OK)
    except Exception as exc:  # an internal error must never look like "no result"
        print(f"INTERNAL ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(EXIT_INTERNAL)
