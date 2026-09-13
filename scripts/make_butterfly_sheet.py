#!/usr/bin/env python3
"""make_butterfly_sheet.py — writes a sprite sheet of a butterfly flapping its wings.

WHY PROCEDURAL: a text-to-image model cannot make 16 frames CONSISTENTLY --
in every frame the butterfly's body/proportions drift, the flapping jitters.
Because wing flapping is geometrically simple, procedural generation GUARANTEES
frame-to-frame consistency, centring and equal angular steps.
A sprite sheet needs all three.

⛔ THE OUTPUT IS A GREY MASK, not colored. The color of a particle texture comes
   from the engine (the particle rule's ptxu_Colour keyframe). If the texture is
   colored it stacks on the tint and color control is lost -- exactly this
   happened on the decal side (all 800 color pairs in the fxdecal textures are R=G=B).

Frames run LEFT TO RIGHT, TOP TO BOTTOM (row first).

Usage:
  python make_butterfly_sheet.py out.png --columns 4 --rows 4 --cell 128
"""
from __future__ import annotations

import sys

import argparse
import math

from PIL import Image, ImageDraw

SS = 4          # supersample factor (for edge smoothing)

# --- Butterfly body: normalised coordinates, y UP is positive, [-1,1] ---
# Top view. The wings are defined to the right of the body and MIRRORED to the left.
FRONT_WING = [
    (0.04, 0.34), (0.30, 0.52), (0.60, 0.66), (0.84, 0.60),
    (0.94, 0.36), (0.86, 0.14), (0.55, 0.02), (0.20, -0.02), (0.04, 0.02),
]
HIND_WING = [
    (0.04, -0.04), (0.34, -0.10), (0.62, -0.28), (0.70, -0.52),
    (0.56, -0.72), (0.30, -0.74), (0.12, -0.55), (0.04, -0.30),
]
# Wing pattern: (centre_x, centre_y, radius, alpha) -- relative to the body
SPOTS = [
    (0.62, 0.42, 0.13, 0.45), (0.40, 0.22, 0.09, 0.55),
    (0.44, -0.40, 0.11, 0.45), (0.28, -0.58, 0.07, 0.60),
]


def chaikin(p, passes=4):
    """Smooths a closed polygon (Chaikin corner cutting).

    A raw polygon reads ANGULAR in a 128px cell -- the breaks along the wing
    edge are visible. Each pass doubles the corner count and halves the breaks;
    4 passes are fully smooth at 128px."""
    for _ in range(passes):
        y = []
        for i in range(len(p)):
            a, b = p[i], p[(i + 1) % len(p)]
            y.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            y.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        p = y
    return p


def draw_wing(d, points, width_mult, scale, centre, fill):
    """Draws one wing. width_mult: flapping foreshortening (horizontal squash)."""
    p = [(centre + x * width_mult * scale, centre - y * scale)
         for x, y in chaikin(points)]
    d.polygon(p, fill=fill)


def draw_frame(size, phase, ss=SS):
    """Makes one frame (alpha mask in L mode). phase: 0..1 within the cycle."""
    n = size * ss
    im = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(im)
    centre = n / 2.0
    scale = n * 0.45          # keep off the cell edge

    # ⛔ In TOP VIEW the flap reads as horizontal shortening.
    #    Wing dihedral angle t -> on screen the width is multiplied by cos(t).
    #    Full cycle: back and forth with sin, so the sheet LOOPS SEAMLESSLY.
    angle = math.radians(62.0) * math.sin(2 * math.pi * phase)
    width_factor = math.cos(angle)
    # when the wings rise the body seems to slide down a little (sense of volume)
    shift = -0.05 * abs(math.sin(angle)) * scale

    for side in (1, -1):
        gc = width_factor * side
        draw_wing(d, FRONT_WING, gc, scale, centre, 235)
        draw_wing(d, HIND_WING, gc, scale, centre, 215)

    # wing pattern (low-alpha spots -> a sense of texture under the tint)
    for bx, by, br, ba in SPOTS:
        for side in (1, -1):
            cx = centre + bx * width_factor * side * scale
            cy = centre - by * scale
            r = br * scale * max(0.35, width_factor)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(255 * ba))

    # body: thin ellipse + head
    gw, gh = 0.055 * scale, 0.42 * scale
    d.ellipse([centre - gw, centre - gh + shift, centre + gw, centre + gh * 0.85 + shift], fill=255)
    head_r = 0.075 * scale
    d.ellipse([centre - head_r, centre - gh - head_r * 0.9 + shift,
               centre + head_r, centre - gh + head_r * 1.1 + shift], fill=255)

    # antennae
    for side in (1, -1):
        x0, y0 = centre + side * head_r * 0.5, centre - gh + shift
        x1, y1 = centre + side * 0.26 * scale, centre - 0.62 * scale + shift
        d.line([x0, y0, x1, y1], fill=200, width=max(1, int(n * 0.008)))
        tip_r = n * 0.012
        d.ellipse([x1 - tip_r, y1 - tip_r, x1 + tip_r, y1 + tip_r], fill=220)

    return im.resize((size, size), Image.LANCZOS)


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
    ap.add_argument("--columns", "--sutun", dest="columns", type=int, default=4)
    ap.add_argument("--rows", "--satir", dest="rows", type=int, default=4)
    ap.add_argument("--cell", "--hucre", dest="cell", type=int, default=128)
    args = ap.parse_args()

    frame_count = args.columns * args.rows
    width, height = args.columns * args.cell, args.rows * args.cell
    if width & (width - 1) or height & (height - 1):
        print(f"[!] WARNING: {width}x{height} is not a power of 2, DXT compression "
              f"may cause problems")

    sheet = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    for i in range(frame_count):
        m = draw_frame(args.cell, i / frame_count)
        # color WHITE, shape in ALPHA -- the engine's tint stacks on top
        cell = Image.merge("RGBA", (
            Image.new("L", m.size, 255), Image.new("L", m.size, 255),
            Image.new("L", m.size, 255), m))
        sheet.paste(cell, ((i % args.columns) * args.cell, (i // args.columns) * args.cell))

    sheet.save(args.out)
    print(f"[+] {args.out}  {width}x{height}  {args.columns}x{args.rows} = {frame_count} frames "
          f"(cell {args.cell}px)")
    print("    frames: left to right, top to bottom · seamless loop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
