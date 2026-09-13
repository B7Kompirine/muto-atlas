#!/usr/bin/env python3
"""bake_to_gta.py -- converts a PBR map set baked in Blender into GTA V textures.

WHY: Blender/Substance output is metallic-roughness PBR. GTA V IS NOT.
  Measured (data/shaders.tsv, 249 shaders): Roughness sampler 0, Gloss 0,
  Metallic 0, AO/Occlusion 0. What exists is SpecSampler (130 shaders).
  So roughness goes into specular INVERTED, AO goes INTO the diffuse,
  and metallic goes to the shader SCALARS instead of a map.

Measured (400+ vanilla material .ytd, 1135 textures):
  normal   DXT1 278 / DXT5 18 / ATI2 6      -> DXT1 (92%)
  spec     DXT1  98 / DXT5  1               -> DXT1 (99%)
  diffuse  DXT1 570 / DXT5 161              -> DXT1 when there is no alpha
  mip      log2(short side)-1, ends at 4x4  -> 832/921 (90.3%)
  size     diffuse/normal/spec median is 512 for all three, max 2048

!! make_dds.py DOES NOT FIT THIS JOB: its --source path exits when there is NO
   alpha, because it was written for particle sprites. Material maps are
   opaque. This script reuses its dxt_dds() mip logic, not its alpha
   requirement.

Usage:
  python bake_to_gta.py <bake_folder> --name mtk_sidewalk --out <folder>
  python bake_to_gta.py bake/ --name mtk_sidewalk --out out/ --size 1024 --pxm
"""
from __future__ import annotations

import argparse
import math
import re
import struct
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")

# dxt_body: make_dds.py's compressed body of one mip level.
from make_dds import (MIN_MIP, DDSD_CAPS, DDSD_HEIGHT, DDSD_WIDTH,
                      DDSD_PIXELFORMAT, DDSD_MIPMAPCOUNT, DDSD_LINEARSIZE,
                      DDPF_FOURCC, DDSCAPS_COMPLEX, DDSCAPS_TEXTURE,
                      DDSCAPS_MIPMAP, dxt_dds, dxt_body)


def _dds_header(width: int, height: int, fourcc: str, levels: int) -> bytes:
    bpb = 8 if fourcc == "DXT1" else 16
    linear_size = max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * bpb
    flags = (DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT
             | DDSD_LINEARSIZE | DDSD_MIPMAPCOUNT)
    h = struct.pack("<7I", 124, flags, height, width, linear_size, 0, levels)
    h += b"\x00" * 44
    h += (struct.pack("<2I", 32, DDPF_FOURCC) + fourcc.encode("ascii")
          + struct.pack("<5I", 0, 0, 0, 0, 0))
    h += struct.pack("<5I", DDSCAPS_TEXTURE | DDSCAPS_MIPMAP | DDSCAPS_COMPLEX,
                     0, 0, 0, 0)
    return b"DDS " + h


def dxt_dds_coverage(rgb: "Image.Image", alpha: "Image.Image",
                     threshold: int = 128) -> tuple[bytes, int, list]:
    """Builds a mip chain that PRESERVES ALPHA COVERAGE for cutouts.

    !! WHY IT IS NEEDED -- MEASURED: with a plain downscale the coverage
       (share of alpha>=threshold) is 34.2% at 512px, climbs to 43.8% at 64px,
       then FALLS to 0% at 16px. So beyond a certain distance the grating
       VANISHES COMPLETELY and no error is raised -- it is only noticed as
       "cannot see it from afar".

    Fix (NVTT's alpha-coverage method): at every mip, scale the alpha by a k
    such that the share of pixels above the threshold equals mip 0.
    """
    import numpy as np

    def coverage(a: "np.ndarray") -> float:
        return float((a >= threshold).mean())

    a0 = np.asarray(alpha, dtype=np.float32)
    target = coverage(a0)

    levels, measurements = [], []
    r_im, a_im = rgb, alpha
    while r_im.width >= MIN_MIP and r_im.height >= MIN_MIP:
        a = np.asarray(a_im, dtype=np.float32)
        if levels and target > 0:
            # coverage(k) rises monotonically in k -> find the transition by binary search
            lo, hi = 0.0, 8.0
            for _ in range(28):
                mid = (lo + hi) / 2
                if coverage(np.clip(a * mid, 0, 255)) < target:
                    lo = mid
                else:
                    hi = mid
            # !! DO NOT TAKE THE TRANSITION POINT BLINDLY. At small mips the alpha
            #    is almost uniform, coverage is a step function and jumps from 0 to 1
            #    in a single step. Measured: at 4x4 the hi side is 68.75%
            #    (target 34.23%). Measure both sides and pick the one CLOSER TO THE TARGET.
            a_lo = np.clip(a * lo, 0, 255)
            a_hi = np.clip(a * hi, 0, 255)
            k_lo, k_hi = coverage(a_lo), coverage(a_hi)
            a = a_lo if abs(k_lo - target) <= abs(k_hi - target) else a_hi
            # ...but DO NOT let it vanish: if it drops below half the target,
            #    take the other side. A vanishing grating is worse than a thick one.
            if coverage(a) < target * 0.5:
                a = a_hi if coverage(a_hi) > coverage(a_lo) else a_lo
        measurements.append((r_im.width, coverage(a)))
        merged = Image.merge("RGBA", (*r_im.split(),
                                      Image.fromarray(a.astype("uint8"), "L")))
        levels.append(dxt_body(merged, "DXT5"))
        if r_im.width == MIN_MIP or r_im.height == MIN_MIP:
            break
        new_size = (max(MIN_MIP, r_im.width // 2), max(MIN_MIP, r_im.height // 2))
        r_im = r_im.resize(new_size, Image.LANCZOS)
        a_im = a_im.resize(new_size, Image.LANCZOS)

    header = _dds_header(rgb.width, rgb.height, "DXT5", len(levels))
    return header + b"".join(levels), len(levels), measurements

# Map-type detection from the file name. The names Blender's File Output node writes
# ("Base Color", "Roughness"...) and common Substance/Quixel names.
PATTERNS = {
    "basecolor":   r"base[\s_-]*color|basecolor|albedo|diffuse|_col\b|_d\b",
    "roughness":   r"rough",
    "normal":      r"normal|_nrm\b|_n\b",
    "height":      r"displace|height|_disp\b|_h\b",
    # !! DO NOT WRITE "\bao\b": underscore is a word character, "_ao" produces no boundary
    #    and the file is SILENTLY skipped. The separator class is written out explicitly.
    "ao":          r"(^|[_\-. ])(ao|occ)($|[_\-. ])|ambient|occlusion",
    "metallic":    r"metal",
    "alpha":       r"(^|[_\-. ])(alpha|opacity|mask|msk)($|[_\-. ])|transparen",
}

# find_maps() tries IN THIS ORDER; the first match wins. Do not change the order:
# "alpha" must come before basecolor so "..._BaseColor_Alpha" counts as alpha,
# and "basecolor" before normal so "normal_stone_basecolor" is not taken for
# a normal.
ORDER = ("ao", "metallic", "roughness", "height", "alpha", "basecolor", "normal")


def find_maps(folder: Path) -> tuple[dict[str, Path], list[Path]]:
    """Matches the images to map types -> (matched, UNMATCHED).

    !! The unmatched ones are RETURNED and PRINTED by the caller. Skipping them
       silently leads to taking a missing map for "it was not there" -- it happened
       once (the AO file did not match the "\\bao\\b" pattern and no warning was given).
    """
    extensions = {".png", ".tif", ".tiff", ".jpg", ".jpeg", ".exr", ".tga", ".bmp"}
    found: dict[str, Path] = {}
    leftover: list[Path] = []
    for p in sorted(folder.iterdir()):
        if not p.is_file() or p.suffix.lower() not in extensions:
            continue
        # !! STRIP THE FRAME NUMBER. Blender File Output always appends a frame
        #    number to the file name ("AO0001.png"). Unstripped, the "ao" pattern
        #    ("ao" + separator) DOES NOT MATCH and the map is skipped -- measured.
        stem = re.sub(r"\d+$", "", p.stem.lower())
        for kind in ORDER:
            if kind in found:
                continue
            if re.search(PATTERNS[kind], stem):
                found[kind] = p
                break
        else:
            leftover.append(p)
    return found, leftover


def load(p: Path, mode: str = "RGB") -> Image.Image:
    im = Image.open(p)
    if im.mode == "I;16":
        im = im.point(lambda v: v * (1 / 257)).convert("L")
    return im.convert(mode)


def square_resize(im: Image.Image, side: int) -> Image.Image:
    if im.width != im.height:
        print(f"    [!] not square ({im.width}x{im.height}) -- tiling may break")
    return im.resize((side, side), Image.LANCZOS)


def srgb_to_linear(im: Image.Image) -> Image.Image:
    lut = [int(round((((v / 255) / 12.92) if v / 255 <= 0.04045
                      else ((v / 255 + 0.055) / 1.055) ** 2.4) * 255))
           for v in range(256)]
    return im.point(lut * len(im.getbands()))


def normal_health(im: Image.Image, mask: Image.Image | None = None):
    """Returns the mean R,G,B (0-1) and the mean |N|.

    In a correct tangent-space normal map R~0.5, G~0.5, B is high and the length
    of the vector n = 2v-1 is ~1.0. If |N| clearly deviates from 1 the file is in
    the wrong colour space (written as sRGB and read raw).
    """
    import numpy as np
    from PIL import ImageFilter

    N = 256                                     # measurement resolution
    v = np.asarray(im.resize((N, N), Image.LANCZOS), dtype=np.float32) / 255.0
    n = v * 2.0 - 1.0
    length = np.sqrt((n ** 2).sum(axis=2))
    if mask is not None:
        # !! ERODE THE MASK AT FULL RESOLUTION, not AFTER the downscale.
        #    Because of antialiasing, edge pixels blend the surface normal with the
        #    background (0,0,0) and shorten the vector; they must be left out of the
        #    measurement. But if you downscale to 128 px and then erode, the bar is
        #    already ~3 px, the erosion wipes everything, the sample empties and the
        #    measurement silently falls back to the unmasked version -- it happened.
        eroded = mask.filter(ImageFilter.MinFilter(5)).resize((N, N), Image.NEAREST)
        m = np.asarray(eroded) >= 128
        if m.sum() >= 256:
            length, v = length[m], v[m]
        else:
            print(f"    [!] eroded mask too small ({int(m.sum())} px) -- "
                  f"measuring over the whole image, the result may mislead")
    return (float(v[..., 0].mean()), float(v[..., 1].mean()),
            float(v[..., 2].mean()), float(length.mean()))


def normal_fix(im: Image.Image, mask: Image.Image | None = None):
    """Raw or sRGB->linear -- PICKS the one that brings |N| closer to 1.0 (by measuring).

    !! LIMIT THE MEASUREMENT TO THE SOLID AREA -- IT HAPPENED: in a cutout texture
       71% of the image is HOLE, and in a hole the normal is (0,0,0). A mean taken
       over the whole image is decided by the holes; the measurement chose "raw"
       (0.920 vs 0.301) while in the SOLID area sRGB->linear was right. A wrong
       colour space raises no error, it only lights wrong.
    """
    candidates = [("raw", im), ("sRGB->linear", srgb_to_linear(im))]
    scored = []
    for label, k in candidates:
        *_, length = normal_health(k, mask)
        scored.append((abs(length - 1.0), label, k, length))
    scored.sort(key=lambda t: t[0])
    _, label, chosen, length = scored[0]
    other = [p for p in scored if p[1] != label][0]
    print(f"    |N| measurement: {label}={length:.3f}  {other[1]}={other[3]:.3f}  -> {label}")
    if abs(length - 1.0) > 0.15:
        print(f"    [!] |N|={length:.3f}, far from 1.0. Check that the normal map is "
              f"tangent-space and in the 0-1 range.")
    return chosen, label


def write_dds(im: Image.Image, target: Path, fourcc: str) -> None:
    data, mip = dxt_dds(im.convert("RGBA"), fourcc)
    target.write_bytes(data)
    expected = int(math.log2(min(im.size))) - 1
    mark = "OK" if mip == expected else f"!! expected {expected}"
    print(f"    -> {target.name}  {im.width}x{im.height} {fourcc}  "
          f"mip={mip} ({mark})  {len(data):,} bytes")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bake_dir", type=Path, help="folder of the baked maps")
    ap.add_argument("--name", "--ad", dest="name", required=True,
                    help="GTA texture base name (e.g. mtk_sidewalk)")
    ap.add_argument("--out", "--cikti", dest="out", type=Path, required=True)
    ap.add_argument("--size", "--boyut", dest="size", type=int, default=512,
                    help="output side length (vanilla median 512; 1024 is common too)")
    ap.add_argument("--pxm", action="store_true",
                    help="also write the height map (for _pxm parallax shaders)")
    ap.add_argument("--keep-green", "--yesil-koru", dest="keep_green", action="store_true",
                    help="do NOT flip the normal's GREEN channel (see below: the DX/GL note)")
    ap.add_argument("--ao-strength", "--ao-gucu", dest="ao_strength", type=float, default=1.0,
                    help="how much AO is mixed into the diffuse (0=off, 1=full)")
    ap.add_argument("--cutout", action="store_true",
                    help="binarise the alpha (fence/grating/leaf -- render bucket 3)")
    ap.add_argument("--threshold", "--esik", dest="threshold", type=int, default=128,
                    help="--cutout threshold (default 128)")
    a = ap.parse_args()

    if a.size & (a.size - 1):
        sys.exit(f"--size must be a power of 2: {a.size}")
    if not a.bake_dir.is_dir():
        sys.exit(f"folder not found: {a.bake_dir}")
    a.out.mkdir(parents=True, exist_ok=True)

    h, leftover = find_maps(a.bake_dir)
    if not h:
        sys.exit(f"no recognised map in {a.bake_dir}")
    print(f"[found] " + "  ".join(f"{k}={v.name}" for k, v in sorted(h.items())))
    if leftover:
        print("[!] UNMATCHED files (not used -- check their names):")
        for p in leftover:
            print(f"      {p.name}")
    print()

    if "basecolor" not in h:
        sys.exit("NO base color -- the diffuse cannot be built")
    if "metallic" in h:
        print("[!] a metallic map was found but GTA has NO metallic SAMPLER "
              "(0 of 249 shaders).\n"
              "    The metal look comes from the shader scalars:\n"
              "      specularIntensityMult raise (1 -> 2.5+)\n"
              "      specularFalloffMult   raise (100 -> 250+, sharp highlight)\n"
              "      specularFresnel       0.95+\n")

    # ---- DIFFUSE = base color (x AO) [+ alpha] ----------------------------
    print("[diffuse]")
    diff = square_resize(load(h["basecolor"]), a.size)
    if "ao" in h and a.ao_strength > 0:
        ao = square_resize(load(h["ao"], "L"), a.size)
        if a.ao_strength < 1.0:
            ao = ao.point(lambda v: int(255 - (255 - v) * a.ao_strength))
        diff = ImageChops.multiply(diff, Image.merge("RGB", (ao, ao, ao)))
        print(f"    AO multiplied into the diffuse (strength={a.ao_strength}) -- GTA has no AO sampler")

    # The alpha can come from a separate file or from the base color's own alpha channel.
    alpha = None
    if "alpha" in h:
        alpha = square_resize(load(h["alpha"], "L"), a.size)
        print(f"    alpha: {h['alpha'].name}")
    else:
        raw = Image.open(h["basecolor"])
        if raw.mode in ("RGBA", "LA") and raw.getchannel("A").getextrema()[0] < 255:
            alpha = square_resize(raw.convert("RGBA").getchannel("A").convert("L"), a.size)
            print("    alpha: the base color's own alpha channel")

    if alpha is not None:
        import numpy as np
        lo, hi = alpha.getextrema()
        av = np.asarray(alpha.resize((128, 128), Image.LANCZOS))
        mid = float(((av > 24) & (av < 231)).mean() * 100)
        print(f"    alpha range {lo}-{hi}, mid-tone share {mid:.1f}%")
        if a.cutout:
            alpha = alpha.point(lambda v: 255 if v >= a.threshold else 0)
            print(f"    cutout: alpha binarised at threshold {a.threshold}")
            data, mip, measurements = dxt_dds_coverage(diff, alpha, a.threshold)
            target = a.out / f"{a.name}.dds"
            target.write_bytes(data)
            print(f"    -> {target.name}  {a.size}x{a.size} DXT5  mip={mip}  "
                  f"{len(data):,} bytes")
            print("    coverage-preserving mip chain (with a plain downscale the grating "
                  "VANISHES from afar):")
            t0 = measurements[0][1]
            for side, cov in measurements:
                print(f"      {side:4d}px  {cov * 100:5.2f}%  "
                      f"({(cov - t0) * 100:+.2f} points)")
            # !! DO NOT JUDGE BY THE SMALLEST MIPS. A 4x4 has 16 pixels, so coverage
            #    can only be tuned in steps of 1/16 = 6.25 points; the deviation there
            #    is the floor of QUANTISATION, not of the algorithm.
            meaningful = [(side, k) for side, k in measurements if side >= 16]
            deviation = max(abs(k - t0) for _, k in meaningful)
            tail = max((abs(k - t0) for side, k in measurements if side < 16),
                       default=0.0)
            print(f"    max deviation (>=16px) {deviation * 100:.2f} points "
                  f"{'OK' if deviation < 0.08 else '!! high'}")
            if tail:
                print(f"    last two levels {tail * 100:.2f} points -- at 4x4 the "
                      f"quantisation step is already 6.25 points, normal")
        else:
            write_dds(Image.merge("RGBA", (*diff.split(), alpha)),
                      a.out / f"{a.name}.dds", "DXT5")
        print("    !! RENDER BUCKET: Sollumz picks the bucket from the SHADER.\n"
              "       cutout_fence / cutout_fence_normal -> 3 (Cutout) is RIGHT.\n"
              "       If you leave normal_spec the bucket stays 0 (Opaque), the alpha\n"
              "       DOES NOT WORK and RAISES NO ERROR either -- you have to set it to 3 by hand.")
    else:
        write_dds(diff, a.out / f"{a.name}.dds", "DXT1")

    # ---- SPEC = 1 - roughness -------------------------------------------
    if "roughness" in h:
        print("[spec]  roughness is INVERTED (GTA specular workflow)")
        rough = square_resize(load(h["roughness"], "L"), a.size)
        spec = ImageChops.invert(rough)
        write_dds(Image.merge("RGB", (spec, spec, spec)), a.out / f"{a.name}_s.dds", "DXT1")
        print("    note: specMapIntMask=1,0,0 in the shader -> only the R channel is read")
    else:
        print("[spec]  no roughness map -- skipped")

    # ---- NORMAL ----------------------------------------------------------
    if "normal" in h:
        print("[normal]")
        nrm = square_resize(load(h["normal"]), a.size)
        # with an alpha, the colour-space measurement is done ONLY in the solid area
        nrm, _ = normal_fix(nrm, alpha)
        if not a.keep_green:
            r, g, b = nrm.split()
            nrm = Image.merge("RGB", (r, ImageChops.invert(g), b))
            print("    green channel flipped (DirectX direction). If the relief looks "
                  "INVERTED in game, build again with --keep-green.")
        write_dds(nrm, a.out / f"{a.name}_n.dds", "DXT1")
    else:
        print("[normal] none -- skipped")

    # ---- HEIGHT (only _pxm shaders) --------------------------------------
    if a.pxm:
        if "height" in h:
            print("[height]")
            hh = square_resize(load(h["height"], "L"), a.size)
            write_dds(Image.merge("RGB", (hh, hh, hh)), a.out / f"{a.name}_h.dds", "DXT1")
            print("    the DEFAULT heightScale of the _pxm shader is 0.03 = 3 cm.\n"
                  "    It is NOT real displacement. Put deep relief into the normal.")
        else:
            print("[height] --pxm given but there is no displacement/height map")
    elif "height" in h:
        print("[height] found but --pxm not given -- not written "
              "(a flat shader has no height sampler)")

    print(f"\n[done] {a.out}")
    print("\nNEXT STEP -- Sollumz shader slots:")
    if a.cutout:
        # cutout_fence_normal has NO SpecSampler (measured: 2 textures).
        print("  shader: cutout_fence_normal   (117 vanilla uses, all 117 in bucket 3)")
        print("  Base Color  <- {0}.dds   (RGB + binary alpha)".format(a.name))
        print("  Normal      <- {0}_n.dds".format(a.name))
        if "roughness" in h:
            print("  !! {0}_s.dds WAS BUILT BUT cutout_fence_normal HAS NO SpecSampler."
                  .format(a.name))
            print("     Shine comes from the scalars: specularIntensityMult=0.4")
            print("     specularFalloffMult=20  specularFresnel=0.9  bumpiness=2")
            print("     If a spec map is a must, switch to normal_spec and set the bucket")
            print("     BY HAND to 3 (Cutout) -- otherwise the alpha silently does not work.")
    else:
        print("  Base Color  <- {0}.dds".format(a.name))
        print("  'Roughness' <- {0}_s.dds   !! THE FIELD NAME MISLEADS: specular goes in"
              .format(a.name))
        print("  Normal      <- {0}_n.dds".format(a.name))
        if a.pxm:
            print("  Height      <- {0}_h.dds  (shader: normal_spec_pxm)".format(a.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
