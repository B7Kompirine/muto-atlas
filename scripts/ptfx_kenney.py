#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_kenney.py — extracts sprites from the Kenney CC0 particle textures.

⛔ WHY: procedural generation and hand-built 3D scenes did not give a
   professional result. The industry's own advice (realtimevfx.com forum)
   is, in order: **ready-made texture pack first**, then photo-bashing,
   procedural last. The Kenney packs fit this job exactly:

     · CC0 (public domain) -- personal AND commercial use allowed,
       attribution not required. No problem in a resource sold on Tebex.
     · GREYSCALE -- the engine's `ptxu_Colour` tint fully decides the
       colour. (Our measured rule: an orange sprite multiplied by blue
       gives mud; a neutral sprite gives the exact tone.)
     · Transparent PNG, 512x512, ONE object per sprite.

Packs:
  kenney_particle-pack.zip   80 textures (smoke/spark/star/flame/circle/dirt...)
  kenney_smoke-particles.zip 68 textures (blackSmoke/whitePuff/explosion/flash)

Usage:
  python ptfx_kenney.py --name smoke_07 --out out.png
  python ptfx_kenney.py --list
"""
from __future__ import annotations

import argparse
import io
import os
import tempfile
import zipfile

ROOT = os.path.join(tempfile.gettempdir(), "kenney")
PACKS = [
    (os.path.join(ROOT, "particle-pack.zip"), "PNG (Transparent)/"),
    (os.path.join(ROOT, "smoke-particles.zip"), "PNG/"),
]


def catalog():
    """name -> (zip path, path inside the zip)"""
    d = {}
    for zp, prefix in PACKS:
        if not os.path.exists(zp):
            continue
        with zipfile.ZipFile(zp) as z:
            for n in z.namelist():
                if not n.startswith(prefix) or not n.lower().endswith(".png"):
                    continue
                name = os.path.splitext(os.path.basename(n))[0]
                d.setdefault(name, (zp, n))
    return d


def extract(name, out, resolution=512):
    """⛔ Kenney textures are NOT tightly cropped; some have a wide empty
    margin. Crop to the alpha bbox, centre on a square, scale to the target
    resolution -- the "alpha coverage" rule (VFXDoc) requires this.
    """
    from PIL import Image
    k = catalog()
    if name not in k:
        return "no such texture: %s" % name
    zp, n = k[name]
    with zipfile.ZipFile(zp) as z:
        im = Image.open(io.BytesIO(z.read(n))).convert("RGBA")
    box = im.getchannel("A").getbbox()
    if box:
        im = im.crop(box)
    w, h = im.size
    s = max(w, h)
    margin = int(s * 0.05)
    canvas = Image.new("RGBA", (s + 2 * margin, s + 2 * margin), (0, 0, 0, 0))
    canvas.paste(im, (margin + (s - w) // 2, margin + (s - h) // 2))
    canvas = canvas.resize((resolution, resolution), Image.LANCZOS)
    canvas.save(out)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", "--ad", dest="name")
    ap.add_argument("--out", "--cikti", dest="out")
    ap.add_argument("--resolution", "--coz", dest="resolution", type=int, default=512)
    ap.add_argument("--list", "--liste", dest="list", action="store_true")
    a = ap.parse_args()

    k = catalog()
    if a.list or not a.name:
        print("%d textures:" % len(k))
        for x in sorted(k):
            print("  ", x)
        return 0
    err = extract(a.name, a.out, a.resolution)
    if err:
        print(err)
        return 1
    print("extracted: %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
