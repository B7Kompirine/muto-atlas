#!/usr/bin/env python3
"""verify_tables.py — cross-checks shaders.tsv and collision_materials.tsv
against usage data built from the game's OWN files.

WHY: both tables were extracted from the Sollumz source, so there is ONE
SOURCE. This script sets a second source (the build_usage.ps1 output) against
them. Three questions:

  1) Is there a shader seen in use that is NOT IN THE TABLE?  -> table incomplete
  2) Are the collision material indices in use inside the table range?
  3) Which RenderBucket are DECAL shaders used with?
     (the Sollumz default is Opaque(0); only a measurement tells the right one)

Usage: python verify_tables.py
"""
from __future__ import annotations

import collections
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")

BUCKET = {0: "Opaque", 1: "Alpha", 2: "Decal", 3: "Cutout",
          4: "NoSplash", 5: "NoWater", 6: "Water", 7: "DisplAlpha"}


def read_tsv(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        sys.exit(f"ERROR: {path} not found.\n  Build it: build_usage.ps1 / build_shaders.py")
    # utf-8-sig: older versions wrote a BOM
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def main():
    shader_defs = read_tsv("shaders.tsv")
    shader_use = read_tsv("shader_usage.tsv")
    mat_defs = read_tsv("collision_materials.tsv")
    mat_use = read_tsv("collision_usage.tsv")

    defined_names = {r["name"] for r in shader_defs}
    used_names = {r["shader"] for r in shader_use}

    print("=" * 68)
    print("CHECK 1 — is the shader table incomplete?")
    print("=" * 68)
    print(f"  defined (Sollumz Shaders.xml) : {len(defined_names)}")
    print(f"  seen in use (vanilla)         : {len(used_names)}")
    missing = sorted(used_names - defined_names)
    print(f"  used but NOT IN THE TABLE     : {len(missing)}")
    for e in missing[:20]:
        print(f"      {e}")
    if len(missing) > 20:
        print(f"      ... {len(missing)-20} more")
    unused = len(defined_names - used_names)
    print(f"  in the table, not seen in the sample: {unused}"
          "   (the sample is limited, not a defect)")

    print()
    print("=" * 68)
    print("CHECK 2 — are the collision material indices in range?")
    print("=" * 68)
    top = len(mat_defs) - 1
    idx = [int(r["matIndex"]) for r in mat_use]
    out_of_range = sorted(m for m in idx if m > top)
    print(f"  table range   : 0-{top} ({len(mat_defs)} materials)")
    print(f"  in use        : {len(idx)} distinct indices, min={min(idx)} max={max(idx)}")
    print(f"  OUT OF RANGE  : {len(out_of_range)}  {out_of_range[:12]}")

    name = {int(r["index"]): r["name"] for r in mat_defs}
    count = {int(r["matIndex"]): int(r["count"]) for r in mat_use}
    print("\n  10 most used materials:")
    for i, n in sorted(count.items(), key=lambda x: -x[1])[:10]:
        print(f"     {i:>4} {name.get(i,'(NOT IN TABLE)'):<28} {n}")

    # proceduralId cross-check
    proc_seen = set()
    for r in mat_use:
        for p in (r.get("proceduralIds") or "").split(","):
            if p.strip().isdigit():
                proc_seen.add(int(p))
    if proc_seen:
        proc_path = os.path.join(DATA, "procedural.tsv")
        if os.path.exists(proc_path):
            with open(proc_path, encoding="utf-8-sig") as fh:
                pt = list(csv.DictReader(fh, delimiter="\t"))
            top_proc = len(pt) - 1
            outside = sorted(p for p in proc_seen if p > top_proc)
            print(f"\n  proceduralId: {len(proc_seen)} distinct values used, "
                  f"table 0-{top_proc}, OUT OF RANGE: {len(outside)} {outside[:10]}")

    print()
    print("=" * 68)
    print("CHECK 3 — which render bucket are DECAL shaders used with?")
    print("=" * 68)
    decals = [r for r in shader_use if "decal" in r["shader"].lower()]
    if not decals:
        print("  no decal shader seen in the sample.")
    else:
        totals = collections.Counter()
        for r in decals:
            for part in r["buckets"].split(";"):
                if ":" not in part:
                    continue
                k, v = part.split(":")
                totals[int(k)] += int(v)
        overall = sum(totals.values())
        print(f"  {len(decals)} distinct decal shaders, {overall} uses:")
        for k, v in sorted(totals.items(), key=lambda x: -x[1]):
            print(f"     bucket {k} {BUCKET.get(k,'?'):<12} {v:>7}  ({100*v/overall:.1f}%)")
        print("\n  most used decal shaders:")
        for r in sorted(decals, key=lambda r: -int(r["total"]))[:8]:
            print(f"     {r['shader']:<34} {r['total']:>6}  buckets={r['buckets']}")

    print()
    print("=" * 68)
    print("OVERALL render bucket distribution")
    print("=" * 68)
    g = collections.Counter()
    for r in shader_use:
        for part in r["buckets"].split(";"):
            if ":" in part:
                k, v = part.split(":")
                g[int(k)] += int(v)
    t = sum(g.values())
    for k, v in sorted(g.items()):
        print(f"  {k} {BUCKET.get(k,'?'):<12} {v:>8}  ({100*v/t:.2f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
