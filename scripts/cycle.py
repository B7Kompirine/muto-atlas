#!/usr/bin/env python3
"""cycle.py — evaluates the weather timecycle at a given hour.

WHY IT EXISTS
=============
`timecycle.py` knows the MODIFIERS (the room's override). This module knows the
BASE layer beneath them: the weather cycle. The order for the question "why does
the prop look like this" is — first the base cycle (which weather, which hour),
then the room's modifier, last the prop's own light. The two can be combined here.

MEASURED, NOT GUESSED
=====================
* A cycle file has the structure `cycle > region > <variable>text</variable>`
  and the text carries one value PER KEYFRAME. **There are 13 keyframes, not
  24 hours.** Assuming "hour = index" shifts everything.
* The hours of those 13 keyframes are in `time.xml` — but there are TWO time.xml files.
  The right one is `common.rpf\\data\\levels\\gta5\\time.xml` (13 samples);
  `common.rpf\\data\\time.xml` is an entirely different 4-sample file.
  Hours: 0 5 6 7 10 12 16 17 18 19 20 21 22
* PITFALL: one sample says `name="09:00"` but carries `hour="10"`. **The name
  lies, the `hour` attribute is what counts.** Code that reads the name shifts
  every following keyframe by one hour.
* Colours are already 0..1 (measured max 1.002); there is no /255 anywhere.
* `light_dir_mult` is HDR and goes up to 54. Clamping is not optional.
* There is a region layer: GLOBAL and URBAN. The default is GLOBAL.

CLAMP CEILINGS
==============
The ceilings below are NOT ENGINE CONSTANTS, they are presentation calibration —
which is why they are parameters, not embedded constants. The defaults should be
verified against the vanilla image; changing them changes the sun/ambient balance.

USAGE
=====
    python assetdb.py cycle --list
    python assetdb.py cycle w_clear --hour 20
    python assetdb.py cycle w_thunder --hour 3 --modifier v_dark --strength 1.0
    python assetdb.py cycle w_clear --hour 12 --region URBAN

No data: powershell -File build_cycle.ps1 -GtaFolder "<GTA folder>"
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from math import sin, cos, pi, sqrt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data", "timecycle")
MODS_TSV = os.path.join(os.path.dirname(HERE), "data", "timecycle.tsv.gz")

# Presentation calibration — not an engine constant, see above.
AMBIENT_CAP = 0.5       # ceiling of the natural/artificial/directional ambient terms
SUN_CAP = 1.0           # ceiling of the direct sun colour
SUN_MULT_FLOOR = 0.5    # lower bound for light_dir_mult

_cache = {}
_mods = None


# ------------------------------------------------------------------ reading data

# blender_light_preview.py calls cycle.available() (the available weather cycles).
def available():
    if not os.path.isdir(DATA):
        return []
    return sorted(f[:-4] for f in os.listdir(DATA)
                  if f.startswith("w_") and f.endswith(".xml"))


def _hours():
    root = ET.parse(os.path.join(DATA, "time.xml")).getroot()
    hrs = [int(s.get("hour")) for s in root.findall(".//sample")]   # NOT name
    sun = root.find(".//suninfo")
    moon = root.find(".//mooninfo")
    return (hrs,
            float(sun.get("sun_roll", 122.0)) if sun is not None else 122.0,
            float(moon.get("moon_roll", -122.0)) if moon is not None else -122.0)


def load(weather="w_clear", region="GLOBAL"):
    key = (weather, region)
    if key in _cache:
        return _cache[key]
    path = os.path.join(DATA, weather + ".xml")
    if not os.path.isfile(path):
        raise FileNotFoundError("no such cycle: %s (available: %s)" % (path, available()))
    cyc = list(ET.parse(path).getroot())[0]
    regions = {r.get("name"): r for r in cyc}
    reg = regions.get(region)
    if reg is None:                      # truth-testing an Element is deprecated
        reg = list(regions.values())[0]
    vals = {}
    for el in reg:
        try:
            vals[el.tag] = [float(x) for x in (el.text or "").split()]
        except ValueError:
            continue
    hrs, sun_roll, moon_roll = _hours()
    tc = {"weather": weather, "region": reg.get("name"), "vars": vals, "hours": hrs,
          "sun_roll": sun_roll, "moon_roll": moon_roll, "cycle": cyc.get("name")}
    _cache[key] = tc
    return tc


def _load_mods():
    global _mods
    if _mods is not None:
        return _mods
    _mods = {}
    if not os.path.isfile(MODS_TSV):
        return _mods
    import gzip
    with gzip.open(MODS_TSV, "rt", encoding="utf-8") as fh:
        next(fh, None)
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 3:
                continue
            try:
                _mods.setdefault(p[0].lower(), {})[p[1]] = float(p[2])
            except ValueError:
                continue
    return _mods


# blender_light_preview.py calls cycle.modifiers(pattern) (modifier names).
def modifiers(pattern=""):
    d = pattern.lower()
    return sorted(k for k in _load_mods() if d in k)


# --------------------------------------------------------------------- sampling

def _sample_base(tc, name, hour, default=0.0):
    v = tc["vars"].get(name)
    if not v:
        return default
    hrs = tc["hours"]
    n = min(len(v), len(hrs))
    h = hour % 24.0
    if h < hrs[0]:                       # before the first key -> wrap from the end
        a, b = n - 1, 0
        span = (24.0 - hrs[a]) + hrs[b]
        t = ((h + 24.0) - hrs[a]) / span if span > 0 else 0.0
    else:
        a = 0
        for i in range(n):
            if hrs[i] <= h:
                a = i
        if a >= n - 1:
            a, b = n - 1, 0
            span = (24.0 - hrs[a]) + hrs[0]
            t = (h - hrs[a]) / span if span > 0 else 0.0
        else:
            b = a + 1
            span = float(hrs[b] - hrs[a])
            t = (h - hrs[a]) / span if span > 0 else 0.0
    return v[a] + (v[b] - v[a]) * min(max(t, 0.0), 1.0)


def _sample(tc, name, hour, default=0.0, mod=None, strength=0.0):
    """A modifier is not a REPLACEMENT, it is a blend towards the target."""
    base = _sample_base(tc, name, hour, default)
    if mod and strength > 1e-4 and name in mod:
        return base + (mod[name] - base) * min(max(strength, 0.0), 1.0)
    return base


def _colour(tc, stem, hour, intensity=None, intensity_default=1.0, mod=None, strength=0.0):
    rgb = [_sample(tc, stem + s, hour, 0.0, mod, strength) for s in ("_r", "_g", "_b")]
    k = (_sample(tc, intensity, hour, intensity_default, mod, strength) if intensity
         else intensity_default)
    return rgb, k


def _scale(rgb, k, cap):
    return tuple(min(c * k, cap) for c in rgb)


def sun_direction(tc, hour):
    """Before 5h / after 21h the moon takes over; if Z points down it is clamped to 0."""
    pitch = tc["sun_roll"] * pi / 180.0
    mroll = tc["moon_roll"] * pi / 180.0
    a = 0.5 + (hour - 6.0) / 14.0
    b = ((hour - 7.0) if hour > 12.0 else (hour + 17.0)) / 9.0
    sv = (sin(pi * a), -cos(pi * a), 0.0)
    mv = (-sin(pi * b), 0.0, -cos(pi * b))

    def rx(v, ang):
        c, s = cos(ang), sin(ang)
        return (v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c)

    v = rx(sv, pitch) if (5.0 <= hour <= 21.0) else rx(mv, -mroll)
    v = (v[0], v[1], max(v[2], 0.0))
    n = sqrt(sum(c * c for c in v)) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


# blender_light_preview.py calls cycle.ambient_at(weather=..., hour=..., region=..., strength=...).
def ambient_at(weather="w_clear", hour=20.0, region="GLOBAL", hdr=False,
               modifier=None, strength=1.0,
               ambient_cap=AMBIENT_CAP, sun_cap=SUN_CAP):
    """Ambient light + sun at one hour, under the names the preview shader expects."""
    tc = load(weather, region)
    a_cap = 1e9 if hdr else ambient_cap
    s_cap = 1e9 if hdr else sun_cap

    mod = None
    if modifier:
        mod = _load_mods().get(modifier.lower())
        if mod is None:
            raise KeyError("no such modifier: %s (e.g. %s)"
                           % (modifier, modifiers(modifier[:4])[:8]))
    else:
        strength = 0.0

    def S(name, d=0.0):
        return _sample(tc, name, hour, d, mod, strength)

    def C(stem, intensity=None, d=1.0):
        return _colour(tc, stem, hour, intensity, d, mod, strength)

    dc, dk = C("light_dir_col", "light_dir_mult")
    sun = _scale(dc, max(dk, 0.0 if hdr else SUN_MULT_FLOOR), s_cap)

    ac, ak = C("light_directional_amb_col", "light_directional_amb_intensity")
    ak *= S("light_directional_amb_intensity_mult", 1.0)

    nu, nuk = C("light_natural_amb_up_col", "light_natural_amb_up_intensity")
    nuk *= S("light_natural_amb_up_intensity_mult", 1.0)
    nd, ndk = C("light_natural_amb_down_col", "light_natural_amb_down_intensity")
    au, auk = C("light_artificial_ext_up_col", "light_artificial_ext_up_intensity")
    ad, adk = C("light_artificial_ext_down_col", "light_artificial_ext_down_intensity")

    # blender_light_preview.py stores and returns _meta.
    return {
        "amb_nat_up": _scale(nu, nuk, a_cap),
        "amb_nat_dn": _scale(nd, ndk, a_cap),
        "amb_art_up": _scale(au, auk, a_cap),
        "amb_art_dn": _scale(ad, adk, a_cap),
        "dir_amb": _scale(ac, ak, a_cap),
        "dir_col": sun,
        "amb_down_wrap": S("light_amb_down_wrap", 1.0),
        "light_dir": sun_direction(tc, hour),
        "_meta": {"weather": tc["weather"], "region": tc["region"], "cycle": tc["cycle"],
                  "hour": hour, "modifier": modifier,
                  "strength": strength if modifier else 0.0},
    }


# ------------------------------------------------------------------------- CLI

def run(args):
    if not os.path.isdir(DATA) or not available():
        print("ERROR: the weather cycle layer is not installed.", file=sys.stderr)
        print("  powershell -File build_cycle.ps1 -GtaFolder \"<GTA folder>\"",
              file=sys.stderr)
        return 2
    if getattr(args, "list", False) or not getattr(args, "weather", None):
        print("weather cycles (%d):" % len(available()))
        for w in available():
            print("  " + w)
        print("\nfor one cycle: assetdb.py cycle w_clear --hour 20")
        return 0
    try:
        a = ambient_at(args.weather, hour=args.hour, region=args.region,
                       modifier=args.modifier, strength=args.strength)
    except (FileNotFoundError, KeyError) as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1
    m = a["_meta"]
    print("%s / %s  cycle=%s  hour=%s" % (m["weather"], m["region"], m["cycle"], m["hour"]))
    if m["modifier"]:
        print("modifier=%s  strength=%.2f" % (m["modifier"], m["strength"]))
    print()
    for k in ("dir_col", "dir_amb", "amb_nat_up", "amb_nat_dn",
              "amb_art_up", "amb_art_dn", "light_dir"):
        print("  %-14s %s" % (k, [round(v, 4) for v in a[k]]))
    print("  %-14s %s" % ("amb_down_wrap", round(a["amb_down_wrap"], 4)))
    return 0
