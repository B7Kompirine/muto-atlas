#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_find_donor.py — finds vanilla donors SUITABLE for a transplant.

A donor works only if three conditions hold, and all three break silently:

  1. It must have a SINGLE EMITTER. `ypt_transplant.py` rejects a
     multi-emitter effect (only ~251 of 964 effects have one emitter).
  2. It must be SPRITE based. Mesh particles (`ParticleBehaviourModel`)
     have no `<TextureName>` -- that is why `ent_amb_falling_leaves_*`
     could not be used.
  3. Its emitter must be findable. The link is in the `<EmitterRule>` field;
     the emitter name is NOT THE SAME as the effect name.

Usage:
  python ptfx_find_donor.py bang_concrete bul_glass scrape_metal
  python ptfx_find_donor.py --search concrete --search glass      # substring
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptfx_quality_gate import iter_blocks, kfp  # noqa: E402
from ptfx_build_catalog import VANILLA  # noqa: E402


def load():
    van = io.open(VANILLA, encoding="utf-8", errors="replace").read()
    em = dict(iter_blocks(van, "EmitterRuleDictionary"))
    pr = dict(iter_blocks(van, "ParticleRuleDictionary"))
    # ⛔ `<ParticleRule>` is NOT in the EMITTER block, it is in the EFFECT block.
    #    Searching the emitter reported every effect as "MESH particle, no
    #    texture" -- yet a textured effect had been built from the same donor.
    #    The emitter block has no `*Rule` tag at all (measured: empty set).
    ef = {}
    for name, block in iter_blocks(van, "EffectRuleDictionary"):
        ef[name] = (re.findall(r"<EmitterRule>([^<]*)</EmitterRule>", block),
                    re.findall(r"<ParticleRule>([^<]*)</ParticleRule>", block))
    return van, ef, em, pr


def inspect(name, ef, em, pr):
    """Returns (suitable, description)."""
    if name not in ef:
        return False, "no such effect"
    e, p = ef[name]
    if len(e) != 1:
        return False, "%d emitters (must have one emitter)" % len(e)
    block = em.get(e[0])
    if block is None:
        return False, "emitter '%s' is not in the dictionary" % e[0]
    tex = None
    for x in p:
        pb = pr.get(x, "")
        d = re.findall(r"<TextureName>([^<]+)</TextureName>", pb)
        if d:
            tex = d[0]
            break
    if tex is None:
        return False, "MESH particle (no texture) -- cannot be transplanted"
    # ⛔ Do not use a donor with MORE THAN ONE TEXTURE. Measured: 6 of 231
    #    suitable donors are like this. `liquid_splash_petrol` needs
    #    `ptfx_gloop_n` (NORMAL MAP) + `ptfx_gloop` (colour); the transplant
    #    writes the single sprite into BOTH and the shader lights it wrong. The
    #    gate caught this as "texture name ['x','x']". Most have a
    #    single-texture twin (petrol -> `liquid_splash_water`, same life band).
    all_tex = []
    for x in p:
        all_tex += re.findall(r"<TextureName>([^<]+)</TextureName>", pr.get(x, ""))
    if len(all_tex) > 1:
        return False, "MULTI-TEXTURE (%s) -- the single sprite is written into both" % (
            ", ".join(all_tex))
    r, l, s = (kfp(block, "m_spawnRateOverTimeKFP"),
               kfp(block, "m_particleLifeKFP"),
               kfp(block, "m_sizeScalarKFP"))
    def g(v):
        return "%.4g-%.4g" % v if v else "?"
    return True, "texture %-28s rate %-13s life %-13s size %s" % (
        tex, g(r), g(l), g(s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--search", "--ara", dest="search", action="append", default=[],
                    help="scan by substring (lists the suitable ones)")
    ap.add_argument("--limit", type=int, default=14)
    a = ap.parse_args()

    van, ef, em, pr = load()
    print("vanilla: %d effects, %d emitters, %d particle rules\n"
          % (len(ef), len(em), len(pr)))

    for name in a.names:
        ok, description = inspect(name, ef, em, pr)
        print("  %s %-34s %s" % ("OK   " if ok else "  -  ", name, description))

    for term in a.search:
        print("\n--- SUITABLE donors containing '%s' ---" % term)
        n = 0
        for name in sorted(ef):
            if term.lower() not in name.lower():
                continue
            ok, description = inspect(name, ef, em, pr)
            if ok:
                print("  %-34s %s" % (name, description))
                n += 1
                if n >= a.limit:
                    print("  ... (limit %d)" % a.limit)
                    break
        if n == 0:
            print("  (no suitable donor)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
