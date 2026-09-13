#!/usr/bin/env python3
"""make_dds.py — writes a DXT5 DDS with a mip chain for a particle sprite.

WHY BY HAND: Blender CANNOT WRITE DDS (the 128-byte header is written by hand;
Blender keeps pixels bottom to top, DDS top to bottom).
VERSION NOTE (measured 2026-08-23): Sollumz 2.9.0 HAS .ytd export
(bpy.ops.sollumz.export_ytd); the old 'Sollumz cannot make .ytd' note is outdated.
DDS writing still goes through here.

⛔ DO NOT USE AN UNCOMPRESSED FORMAT. The first version of this script wrote
   A8R8G8B8 (single mip) and its reasoning was the ASSUMPTION "GTA accepts
   uncompressed too". Then it was measured: ALL 107 embedded particle textures
   in `core.ypt` are DXT compressed (DXT5 75 · DXT1 32), mip levels 4-9.
   There is NO uncompressed or single-mip EXAMPLE. That is why the default is now
   DXT5 + a mip chain.

⚠ DDS rows are written TOP TO BOTTOM (Blender gives pixels bottom to top);
  no problem here because we generate directly, but when exporting from Blender
  they must be flipped.

The generated patterns are TECHNICAL PRIMITIVES (soft radial mask), not art --
when a real visual is needed the user supplies their own texture.

Usage:
  python make_dds.py out.dds --pattern soft --size 128
  python make_dds.py out.dds --pattern ring --size 128 --inner-radius 0.45
  python make_dds.py out.dds --format A8R8G8B8      # old behaviour (not recommended)
"""
from __future__ import annotations

import argparse
import io
import math
import struct
import sys

from PIL import Image

DDSD_CAPS, DDSD_HEIGHT, DDSD_WIDTH, DDSD_PIXELFORMAT = 0x1, 0x2, 0x4, 0x1000
DDSD_PITCH, DDSD_MIPMAPCOUNT, DDSD_LINEARSIZE = 0x8, 0x20000, 0x80000
DDPF_ALPHAPIXELS, DDPF_FOURCC, DDPF_RGB = 0x1, 0x4, 0x40
DDSCAPS_COMPLEX, DDSCAPS_TEXTURE, DDSCAPS_MIPMAP = 0x8, 0x1000, 0x400

# ⛔ THE MIP CHAIN GOES DOWN TO 4x4. A DXT block is 4x4, below that is meaningless.
#    Measured: the mip count of vanilla particle textures follows the size exactly
#    as log2(edge)-1 -- 128x128 -> 6, 256x256 -> 7, 512x512 -> 8,
#    1024x1024 -> 9. Cutting the chain early makes the texture sample
#    wrongly at a distance.
MIN_MIP = 4

PATTERNS = ["soft", "ring", "hard"]
# Old Turkish pattern names are still accepted as input.
PATTERN_ALIASES = {"yumusak": "soft", "halka": "ring", "sert": "hard"}


def make_mask(width: int, height: int, pattern: str, inner: float) -> Image.Image:
    """RGBA: color WHITE, shape in the ALPHA channel.

    Particle textures are grey/white masks: the engine gives the color (the
    particle rule's ptxu_Colour keyframe). If the texture is colored it stacks
    on the tint and control is lost.
    """
    im = Image.new("RGBA", (width, height))
    px = im.load()
    mx, my = (width - 1) / 2.0, (height - 1) / 2.0
    radius = min(mx, my)
    for y in range(height):
        for x in range(width):
            d = math.hypot(x - mx, y - my) / radius      # 0 centre, 1 edge
            if pattern == "soft":
                a = max(0.0, 1.0 - d)
                a = a * a * (3 - 2 * a)                   # smoothstep
            elif pattern == "ring":
                a = max(0.0, 1.0 - abs(d - inner) / max(inner, 1e-6))
                a = a * a
                if d > 1.0:
                    a = 0.0
            elif pattern == "hard":
                a = 1.0 if d <= 1.0 else 0.0
            else:
                sys.exit(f"unknown pattern: {pattern}")
            px[x, y] = (255, 255, 255, int(round(max(0.0, min(1.0, a)) * 255)))
    return im


# bake_to_gta.py imports dxt_body.
def dxt_body(im: Image.Image, fourcc: str) -> bytes:
    """Compresses one level to DXT and drops the 128-byte DDS header."""
    b = io.BytesIO()
    im.save(b, format="DDS", pixel_format=fourcc)
    return b.getvalue()[128:]


def dxt_dds(base: Image.Image, fourcc: str = "DXT5") -> tuple[bytes, int]:
    """Writes a DXT DDS with a mip chain -> (bytes, mip_count).

    ⛔ DXT1 = 8 bytes/block, DXT5 = 16. The block size goes into the header's
    dwPitchOrLinearSize field; if it is written wrongly the mip chain
    shifts and the texture samples broken."""
    levels, im = [], base
    while im.width >= MIN_MIP and im.height >= MIN_MIP:
        levels.append(dxt_body(im, fourcc))
        if im.width == MIN_MIP or im.height == MIN_MIP:
            break
        im = im.resize((max(MIN_MIP, im.width // 2),
                        max(MIN_MIP, im.height // 2)), Image.LANCZOS)

    width, height = base.width, base.height
    bpb = 8 if fourcc == "DXT1" else 16
    block = max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * bpb
    flags = (DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT
             | DDSD_LINEARSIZE | DDSD_MIPMAPCOUNT)
    h = struct.pack("<7I", 124, flags, height, width, block, 0, len(levels))
    h += b"\x00" * 44                                              # dwReserved1[11]
    h += (struct.pack("<2I", 32, DDPF_FOURCC) + fourcc.encode("ascii")
          + struct.pack("<5I", 0, 0, 0, 0, 0))
    h += struct.pack("<5I", DDSCAPS_TEXTURE | DDSCAPS_MIPMAP | DDSCAPS_COMPLEX,
                     0, 0, 0, 0)
    return b"DDS " + h + b"".join(levels), len(levels)


def a8r8g8b8_dds(base: Image.Image) -> tuple[bytes, int]:
    """Uncompressed BGRA, single mip. NO example in vanilla -- kept only
    for comparison/diagnosis."""
    width, height = base.width, base.height
    flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_PITCH
    h = struct.pack("<7I", 124, flags, height, width, width * 4, 0, 0)
    h += b"\x00" * 44
    h += struct.pack("<8I", 32, DDPF_ALPHAPIXELS | DDPF_RGB, 0, 32,
                     0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    h += struct.pack("<5I", DDSCAPS_TEXTURE, 0, 0, 0, 0)
    px = base.load()
    data = bytearray()
    for y in range(height):
        for x in range(width):
            r, g, b, a = px[x, y]
            data += bytes((b, g, r, a))
    return b"DDS " + h + bytes(data), 1


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
    ap.add_argument("--pattern", "--desen", dest="pattern", default="soft",
                    type=lambda v: PATTERN_ALIASES.get(v, v), choices=PATTERNS)
    ap.add_argument("--size", "--boyut", dest="size", type=int, default=128)
    ap.add_argument("--inner-radius", "--ic", dest="inner_radius", type=float, default=0.5,
                    help="ring pattern: centre radius")
    ap.add_argument("--format", default="DXT5", choices=["DXT5", "DXT1", "A8R8G8B8"],
                    help="DXT5 is the default; A8R8G8B8 has NO EXAMPLE in vanilla")
    ap.add_argument("--source", "--kaynak", dest="source", default=None,
                    help="build from a ready PNG (--pattern/--size are ignored). "
                         "This is the one to use for sprite sheets.")
    args = ap.parse_args()

    if args.source:
        # ⛔ The source image must be a GREY MASK (black background, white-grey shape).
        #    Vanilla animation sheets are like this too -- measured
        #    (ptfx_smoke_billow_anim_rgba, ptfx_water_splashes_sheet).
        base = Image.open(args.source).convert("RGBA")
        for label, v in (("width", base.width), ("height", base.height)):
            if v & (v - 1):
                sys.exit(f"{label} must be a power of 2: {v}")
        if base.getextrema()[3][1] == 0:
            sys.exit("the source has no alpha -- the shape must be in the alpha channel")
    else:
        if args.size & (args.size - 1):
            sys.exit("size must be a power of 2 (64/128/256...)")
        base = make_mask(args.size, args.size, args.pattern, args.inner_radius)
    data, mip = (a8r8g8b8_dds(base) if args.format == "A8R8G8B8"
                 else dxt_dds(base, args.format))
    with open(args.out, "wb") as f:
        f.write(data)
    source_info = args.source if args.source else f"pattern={args.pattern}"
    print(f"[+] {args.out}  {base.width}x{base.height} {args.format}  "
          f"mip={mip}  {len(data):,} bytes  {source_info}")
    if args.format != "DXT5":
        print("[!] WARNING: all 107 particle textures in vanilla are DXT. "
              "An uncompressed texture may be rejected in the game.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
