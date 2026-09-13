#!/usr/bin/env python3
"""make_test_sheet.py — test texture that checks sprite sheet SLICING for certain.

⛔ WHY IT IS NEEDED: with a sheet that repeats the same shape the question "does
   the engine slice" CANNOT BE ANSWERED FROM THE SCREEN. Exactly this happened in
   the butterfly test -- the butterfly has four wings, a single cell reads like a
   2x2, and so does the whole sheet. Because the two cases could not be told apart
   visually, the wrong lead was chased for a whole round.

   This script puts a DIFFERENT shape in every cell. In the game:
     you see one shape       -> slicing WORKS
     all four shapes at once -> NO slicing, the whole texture is drawn
   No other reading.

The shapes are deliberately crude and high-contrast, so they can be told apart
at a small scale too.

Usage:
  python make_test_sheet.py out.png --cell 128 --grid 2
"""
from __future__ import annotations

import sys

import argparse
import math

from PIL import Image, ImageDraw

SS = 4     # supersample


def draw_shape(d, kind, n, fill=255):
    """One shape inside an n x n canvas. A margin is left so nothing
    spills over the cell border (a spill makes the slicing read wrongly)."""
    p = n * 0.14
    a, b = p, n - p
    mid = n / 2.0
    stroke = int(n * 0.13)
    if kind == "disk":
        d.ellipse([a, a, b, b], fill=fill)
    elif kind == "ring":
        d.ellipse([a, a, b, b], outline=fill, width=stroke)
    elif kind == "plus":
        d.rectangle([mid - stroke, a, mid + stroke, b], fill=fill)
        d.rectangle([a, mid - stroke, b, mid + stroke], fill=fill)
    elif kind == "triangle":
        d.polygon([(mid, a), (b, b), (a, b)], fill=fill)
    elif kind == "square":
        d.rectangle([a, a, b, b], outline=fill, width=stroke)
    elif kind == "cross":
        d.line([a, a, b, b], fill=fill, width=stroke)
        d.line([a, b, b, a], fill=fill, width=stroke)
    else:
        # numbered dot pattern: for cells 6+
        k = int(kind)
        r = n * 0.10
        for i in range(k):
            ang = 2 * math.pi * i / max(k, 1) - math.pi / 2
            cx, cy = mid + math.cos(ang) * n * 0.26, mid + math.sin(ang) * n * 0.26
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def main() -> int:
    # Help and messages carry non-ASCII marks; a console with a legacy code page cannot encode
    # them and argparse would crash. Replace what the console cannot show.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--cell", "--hucre", dest="cell", type=int, default=128)
    ap.add_argument("--grid", "--izgara", dest="grid", type=int, default=2,
                    help="grid edge (2 -> 2x2)")
    args = ap.parse_args()

    shapes = ["disk", "ring", "plus", "triangle", "square", "cross"]
    k = args.grid
    width = args.cell * k
    sheet = Image.new("RGBA", (width, width), (255, 255, 255, 0))

    for i in range(k * k):
        n = args.cell * SS
        m = Image.new("L", (n, n), 0)
        d = ImageDraw.Draw(m)
        draw_shape(d, shapes[i] if i < len(shapes) else str(i + 1), n)
        m = m.resize((args.cell, args.cell), Image.LANCZOS)
        cell = Image.merge("RGBA", (
            Image.new("L", m.size, 255), Image.new("L", m.size, 255),
            Image.new("L", m.size, 255), m))
        sheet.paste(cell, ((i % k) * args.cell, (i // k) * args.cell))

    sheet.save(args.out)
    names = [shapes[i] if i < len(shapes) else str(i + 1) for i in range(k * k)]
    print(f"[+] {args.out}  {width}x{width}  {k}x{k} = {k*k} frames")
    print(f"    cells (left to right, top to bottom): {', '.join(names)}")
    print("    IN THE GAME: one shape -> slicing WORKS | all at once -> NO slicing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
