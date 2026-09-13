#!/usr/bin/env python3
"""light.py — reads and DECODES the lights embedded in a .ydr/.yft.

WHY IT EXISTS
=============
Light parameters are full of magic numbers: `TimeFlags = 15728703` is not a
number, it means "lit from 20:00 to 05:00". Copying that number and moving on
is the most common mistake; the light turns on at the wrong hour or never, and
the reason is not visible when you look at the file.
    "Do not copy the magic number, decode it."

Lights live under `<root>/Lights` -- in the SAME place in both a Drawable (.ydr)
and a Fragment (.yft) root. In a Fragment it is NOT `Drawable/Lights` (measured:
prop_worklight_01a.yft -> Fragment/Lights=1, no Fragment/Drawable/Lights).

USAGE
=====
    python assetdb.py light <file.ydr|.yft|.xml>
    python assetdb.py light <file> --raw          (undecoded, raw fields)
    python assetdb.py light --table               (measured vanilla reference)
"""
from __future__ import annotations

import collections
import gzip
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_xml import read_root  # noqa: E402

# --- MEASURED VANILLA REFERENCE ------------------------------------------------
# The reference is NOT EMBEDDED; it is computed LIVE from the data/lights.tsv.gz
# layer (produced by build_lights.ps1, which scans every .ydr/.yft/.ydd file of GTA).
#
# If the layer is not installed, EXIT_NOLAYER is returned instead of an invented
# range: what is presented as a "measured reference" must really be measured.
# The checks that do NOT DEPEND on the distribution (TimeFlags 0, Intensity 0,
# Falloff 0, inverted cone) work without the layer too -- they are logic, not statistics.
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LIGHTS = os.path.join(DATA, "lights.tsv.gz")

# Numeric fields whose distribution is reported: TSV column name -> name shown on screen.
NUMERIC = [
    ("intensity", "Intensity"),
    ("falloff", "Falloff"),
    ("falloffExp", "FalloffExponent"),
    ("coneInner", "ConeInnerAngle"),
    ("coneOuter", "ConeOuterAngle"),
    ("coronaSize", "CoronaSize"),
    ("coronaIntensity", "CoronaIntensity"),
    ("volumeIntensity", "VolumeIntensity"),
]

HOUR_BITS = 24


def _f(el, attr="value"):
    if el is None:
        return None
    try:
        return float(el.get(attr))
    except (TypeError, ValueError):
        return None


def _i(el, attr="value"):
    v = _f(el, attr)
    return None if v is None else int(v)


def _v3(el):
    if el is None:
        return None
    try:
        return tuple(float(el.get(k)) for k in "xyz")
    except (TypeError, ValueError):
        return None


def _rgb(el):
    if el is None:
        return None
    try:
        return tuple(int(el.get(k)) for k in "rgb")
    except (TypeError, ValueError):
        return None


# doctor_checks.py calls light.read_lights().
def read_lights(root):
    """<root>/Lights/Item list -> list of dicts. None when there is no Lights node."""
    L = root.find("Lights")
    if L is None:
        return None
    out = []
    for it in L:
        out.append({
            "Type": (it.findtext("Type") or "?").strip(),
            "Position": _v3(it.find("Position")),
            "Colour": _rgb(it.find("Colour")),
            "Intensity": _f(it.find("Intensity")),
            "Falloff": _f(it.find("Falloff")),
            "FalloffExponent": _f(it.find("FalloffExponent")),
            "ConeInnerAngle": _f(it.find("ConeInnerAngle")),
            "ConeOuterAngle": _f(it.find("ConeOuterAngle")),
            "CoronaSize": _f(it.find("CoronaSize")),
            "CoronaIntensity": _f(it.find("CoronaIntensity")),
            "VolumeIntensity": _f(it.find("VolumeIntensity")),
            "VolumeSizeScale": _f(it.find("VolumeSizeScale")),
            "Flags": _i(it.find("Flags")),
            "TimeFlags": _i(it.find("TimeFlags")),
            "BoneId": _i(it.find("BoneId")),
            "GroupId": _i(it.find("GroupId")),
            "Flashiness": _i(it.find("Flashiness")),
            "ShadowBlur": _i(it.find("ShadowBlur")),
            "Direction": _v3(it.find("Direction")),
            "Extent": _v3(it.find("Extent")),
            "ProjectedTextureHash": (it.findtext("ProjectedTextureHash") or "").strip(),
        })
    return out


# doctor_checks.py calls light.active_hours().
def active_hours(timeflags):
    if timeflags is None:
        return []
    return [h for h in range(HOUR_BITS) if (timeflags >> h) & 1]


def hour_blocks(hours):
    """Circular contiguous hour blocks. 20..5 is returned as a single block."""
    s = sorted(hours)
    if not s:
        return []
    if len(s) == HOUR_BITS:
        return [(0, 23)]
    starts = [i for i in range(len(s)) if s[i - 1] != (s[i] - 1) % HOUR_BITS]
    k = starts[0] if starts else 0
    s = s[k:] + s[:k]
    blocks, start, prev = [], s[0], s[0]
    for h in s[1:]:
        if h == (prev + 1) % HOUR_BITS:
            prev = h
            continue
        blocks.append((start, prev))
        start = prev = h
    blocks.append((start, prev))
    return blocks


def hours_text(timeflags):
    hours = active_hours(timeflags)
    if timeflags is None:
        return "no TimeFlags"
    if not hours:
        return "no hour bits at all (TimeFlags 0)"
    if len(hours) == HOUR_BITS:
        return "every hour (24/24)"
    block = ", ".join(f"{a:02d}:00-{(b + 1) % 24:02d}:00" for a, b in hour_blocks(hours))
    return f"{block}  ({len(hours)}h)"


def bits(v):
    return [i for i in range(32) if v is not None and (v >> i) & 1]


def reference():
    """data/lights.tsv.gz -> (statistics, flags, timeflags, summary) or None.

    p05-p95 is used, NOT min-max: in a corpus of tens of thousands of lights a
    single extreme value makes the range meaningless and the check never
    fires.
    """
    if not os.path.exists(LIGHTS):
        return None
    cols, values = None, collections.defaultdict(list)
    flags, tf, types = collections.Counter(), collections.Counter(), collections.Counter()
    models = set()
    n = 0
    with gzip.open(LIGHTS, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if cols is None:
                cols = {name: i for i, name in enumerate(p)}
                continue
            if len(p) < len(cols):
                continue
            n += 1
            models.add(p[cols["model"]])
            types[p[cols["type"]]] += 1
            for key, _ in NUMERIC:
                try:
                    values[key].append(float(p[cols[key]]))
                except (ValueError, KeyError):
                    pass
            try:
                flags[int(p[cols["flags"]])] += 1
                tf[int(p[cols["timeFlags"]])] += 1
            except ValueError:
                pass

    if not n:
        return None
    stats = {}
    for key, shown in NUMERIC:
        v = sorted(values[key])
        if not v:
            continue
        stats[shown] = {
            "n": len(v), "min": v[0], "max": v[-1],
            "p05": v[int(0.05 * (len(v) - 1))],
            "median": v[len(v) // 2],
            "p95": v[int(0.95 * (len(v) - 1))],
        }
    return {"stats": stats, "flags": flags, "tf": tf, "types": types,
            "n": n, "models": len(models)}


def suspicious(light, ref=None):
    """Cases that make the light INVISIBLE or fall outside the measured range.

    The logic checks always run; the range check only when the reference
    layer is installed -- without a measurement you cannot say "outside the range".
    """
    issues = []
    if not active_hours(light["TimeFlags"]):
        # MEASURED: among 72,539 vanilla lights TimeFlags 0 occurs only 8 times
        # (0.011%) -- and where it occurs it is interior lamp props
        # (m232_lamp_office_01, m25_2_int_01_lp_m_bedroom, imp_lightrig01).
        # So whether 0 means "never lit" or "no hour restriction" CANNOT BE
        # SETTLED FROM THIS DATA. It is reported as rare, the behaviour is NOT
        # CLAIMED; only a test in game settles the difference.
        issues.append("TimeFlags 0: no hour bits at all. Very rare in vanilla "
                      "(8 of 72,539 lights, 0.011%) -- the data does not settle "
                      "what it does; test it in game")
    if light["Intensity"] is not None and light["Intensity"] <= 0:
        issues.append("Intensity 0 -> emits nothing")
    if light["Falloff"] is not None and light["Falloff"] <= 0:
        issues.append("Falloff 0 -> no range, the light reaches no surface")
    if light["Type"] == "Spot":
        inner, outer = light["ConeInnerAngle"], light["ConeOuterAngle"]
        if outer is not None and outer <= 0:
            issues.append("Spot but ConeOuterAngle 0 -> cone is shut")
        elif inner is not None and outer is not None and inner > outer:
            issues.append(f"ConeInnerAngle ({inner:g}) > ConeOuterAngle ({outer:g}) -> cone inverted")
    if ref:
        for field, s in ref["stats"].items():
            v = light.get(field)
            if v is None or v == 0:
                continue
            if v < s["p05"] or v > s["p95"]:
                issues.append(f"{field}={v:g} is outside vanilla's 90% band "
                              f"[{s['p05']:g}, {s['p95']:g}] (not an error - reference)")
    return issues


def print_light(idx, i, raw=False, ref=None):
    print(f"\n  #{idx}  {i['Type']}")
    if raw:
        for k, v in i.items():
            print(f"      {k:<22} {v}")
        return
    if i["Colour"]:
        r, g, b = i["Colour"]
        print(f"      colour       RGB({r},{g},{b})")
    if i["Intensity"] is not None:
        print(f"      intensity    {i['Intensity']:g}")
    if i["Falloff"] is not None:
        exp = f"   (exp {i['FalloffExponent']:g})" if i["FalloffExponent"] is not None else ""
        print(f"      range        {i['Falloff']:g} m{exp}")
    if i["Type"] == "Spot" and i["ConeOuterAngle"] is not None:
        print(f"      cone         inner {i['ConeInnerAngle']:g}deg -> outer "
              f"{i['ConeOuterAngle']:g}deg")
    if i["Type"] == "Capsule" and i["Extent"]:
        print(f"      extent       {i['Extent']}")
    print(f"      hours        {hours_text(i['TimeFlags'])}"
          f"   [TimeFlags {i['TimeFlags']}]")
    if i["CoronaSize"]:
        print(f"      corona       size {i['CoronaSize']:g}  intensity "
              f"{i['CoronaIntensity']:g}")
    if i["VolumeIntensity"]:
        print(f"      volume       intensity {i['VolumeIntensity']:g}  scale "
              f"{i['VolumeSizeScale']:g}")
    if i["ShadowBlur"]:
        print(f"      shadow       blur {i['ShadowBlur']}")
    b = bits(i["Flags"])
    common = ""
    if ref and i["Flags"] in ref["flags"]:
        common = f"  (vanilla x{ref['flags'][i['Flags']]})"
    print(f"      flags        {i['Flags']}  = bits {b or 'none'}{common}")
    if i["BoneId"]:
        print(f"      bone         tag {i['BoneId']}")
    if i["ProjectedTextureHash"]:
        print(f"      projection   {i['ProjectedTextureHash']}")
    for s in suspicious(i, ref):
        print(f"      ! {s}")


def print_table(ref):
    types = ", ".join(f"{k} {v}" for k, v in ref["types"].most_common())
    print("MEASURED VANILLA LIGHT REFERENCE")
    print(f"  source : data/lights.tsv.gz - {ref['n']} lights / {ref['models']} models")
    print(f"  types  : {types}")
    print("  NOTE: outside the range is NOT an error, it means 'rare in vanilla'.\n")
    print(f"  {'field':<20} {'n':>7} {'min':>9} {'p05':>9} {'median':>9} "
          f"{'p95':>9} {'max':>9}")
    for k, s in ref["stats"].items():
        print(f"  {k:<20} {s['n']:>7} {s['min']:>9g} {s['p05']:>9g} "
              f"{s['median']:>9g} {s['p95']:>9g} {s['max']:>9g}")

    print("\n  Flags (8 most common):")
    for v, c in ref["flags"].most_common(8):
        print(f"    {v:<12} x{c:<7} bits {bits(v) or 'none'}")
    print("  Bit NAMES are not in the database -> indices are shown, names are not invented.")

    print("\n  TimeFlags (8 most common):")
    for v, c in ref["tf"].most_common(8):
        print(f"    {v:<12} x{c:<7} {hours_text(v)}")


def run(args):
    ref = reference()
    if args.table:
        if ref is None:
            print(f"ERROR: {LIGHTS} not found.", file=sys.stderr)
            print("  No measured reference - NOTHING can be claimed about the "
                  "ranges. Build it: powershell -File build_lights.ps1",
                  file=sys.stderr)
            return 2
        print_table(ref)
        return 0
    if not args.path:
        print("ERROR: no file given (or use --table).", file=sys.stderr)
        return 2

    root, error = read_root(args.path)
    if error:
        print(f"ERROR: {args.path}: {error}", file=sys.stderr)
        print("  File could NOT be read - nothing can be claimed about whether "
              "it holds lights.", file=sys.stderr)
        return 2

    lights = read_lights(root)
    if lights is None:
        print(f"{os.path.basename(args.path)} ({root.tag}): NO <Lights> node.")
        print("  This resource type may not carry lights; that is NOT the same "
              "as 'no lights'.")
        return 1
    if not lights:
        print(f"{os.path.basename(args.path)} ({root.tag}): <Lights> exists but is EMPTY "
              f"-> no embedded lights.")
        return 1

    print(f"{os.path.basename(args.path)} ({root.tag}): {len(lights)} lights")
    for idx, i in enumerate(lights):
        print_light(idx, i, args.raw, ref)
    total_warnings = sum(len(suspicious(i, ref)) for i in lights)
    print(f"\n{len(lights)} lights | {total_warnings} warnings")
    return 0
