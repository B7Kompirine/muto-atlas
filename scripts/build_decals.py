#!/usr/bin/env python3
"""build_decals.py — indexes the GTA V decalType table (`decals.dat`).

WHY: the first argument of the `AddDecal(decalType, ...)` native is a NUMBER, and
which image that number maps to is not written down in one place anywhere.
The enum in the FiveM docs is INCOMPLETE (only part of it). The real source is
the game's own `common.rpf\\data\\effects\\decals.dat` file.

FILE FORMAT: space-aligned fixed-column text, '#' comments.
  ID  DIFFUSE  NORMAL  SPECULAR  ROW COL IDA IDB  TIME MULT FALLOFF INTNSTY
  FRESNEL STEEP SCALE VALUE LENGTH  TEX_WRAP USE_ANISO WASHABLE UNDERWATER ROTATE

THE SAME ID CAN APPEAR ON SEVERAL ROWS: the engine picks a random variant for
that ID (e.g. 1010 = blood splatter, several texture regions). So the row count
per ID = the variant count.

Usage:
  python build_decals.py --src <path to decals.dat>
  (without a path, %TEMP%\\decals.dat is looked for)
"""
from __future__ import annotations

import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


def main() -> int:
    ap = argparse.ArgumentParser(description="decals.dat -> table")
    ap.add_argument("--src", default=os.path.join(os.environ.get("TEMP", "."), "decals.dat"))
    ap.add_argument("--out", default=os.path.join(DATA, "decal_types.tsv"))
    args = ap.parse_args()

    if not os.path.exists(args.src):
        sys.exit(
            f"ERROR: {args.src} not found.\n"
            "  Extract it with CodeWalker: common.rpf\\data\\effects\\decals.dat")

    # The last '# HEADING' comment seen is the CATEGORY of the rows below it; the
    # file groups them in blocks such as BLOOD SPLATTERS / WEAPON IMPACTS.
    category = ""
    records: list[dict] = []
    with open(args.src, encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            s = raw_line.rstrip("\n")
            stripped = s.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()
                # do not take column headings such as 'ID  DIFFUSE MAP ...' for a category
                if (heading and not heading.startswith("ID")
                        and "---" not in heading and len(heading) < 60
                        and heading.upper() == heading):
                    category = heading
                continue
            if stripped.startswith("DECAL_DEF"):
                continue
            parts = stripped.split()
            if not parts or not parts[0].isdigit():
                continue
            records.append({
                "id": int(parts[0]),
                "category": category,
                "diffuse": parts[1] if len(parts) > 1 else "",
                "normal": parts[2] if len(parts) > 2 else "",
                "specular": parts[3] if len(parts) > 3 else "",
                # last five columns: TEX_WRAP USE_ANISO WASHABLE UNDERWATER ROTATE
                "washable": parts[-3] if len(parts) >= 3 else "",
                "underwater": parts[-2] if len(parts) >= 2 else "",
                "rotate": parts[-1] if parts else "",
            })

    if not records:
        sys.exit("ERROR: no decal row could be parsed.")

    # group per ID: variant count + unique texture names
    groups: dict[int, dict] = {}
    for r in records:
        g = groups.setdefault(r["id"], {
            "id": r["id"], "category": r["category"],
            "variants": 0, "textures": [], "washable": r["washable"],
            "underwater": r["underwater"],
        })
        g["variants"] += 1
        if r["diffuse"] and r["diffuse"] not in g["textures"]:
            g["textures"].append(r["diffuse"])
        if not g["category"] and r["category"]:
            g["category"] = r["category"]

    os.makedirs(DATA, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        # The header is part of data/decal_types.tsv, which assetdb.py reads: keep these column
        # names as they are (kategori = category, varyant = variants, dokular = textures).
        w.writerow(["id", "kategori", "varyant", "washable", "underwater", "dokular"])
        for i in sorted(groups):
            g = groups[i]
            w.writerow([g["id"], g["category"], g["variants"], g["washable"],
                        g["underwater"], ";".join(g["textures"][:6])])

    per_category = collections.Counter(g["category"] for g in groups.values())
    print(f"[+] {args.out}")
    print(f"[+] {len(groups)} unique decalTypes / {len(records)} rows (variants included)")
    print(f"[+] ID range: {min(groups)} - {max(groups)}")
    print("\ncategories:")
    for k, v in per_category.most_common(20):
        print(f"   {k or '(no category)':<34} {v} types")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
