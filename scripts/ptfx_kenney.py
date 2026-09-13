#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_kenney.py — Kenney CC0 partikul dokularindan sprite cikarir.

⛔ NEDEN: prosedurel uretim ve elle 3B sahne kurmak profesyonel sonuc
   vermedi. Sektorun kendi tavsiyesi (realtimevfx.com forumu) sirasiyla
   sudur: **once hazir doku paketi**, sonra photo-bashing, en son
   prosedurel. Kenney paketleri tam bu ise uygun:

     · CC0 (kamu mali) -- kisisel VE ticari kullanim serbest, atif
       zorunlu degil. Tebex'te satilan bir kaynakta sorun cikarmaz.
     · GRI TONLAMALI -- motorun `ptxu_Colour` tint'i rengi tamamen
       belirler. (Bizim olculmus kural: turuncu sprite maviyle
       carpilinca camur verir; notr sprite tam tonu verir.)
     · Saydam PNG, 512x512, sprite basina TEK nesne.

Paketler:
  kenney_particle-pack.zip   80 doku (smoke/spark/star/flame/circle/dirt...)
  kenney_smoke-particles.zip 68 doku (blackSmoke/whitePuff/explosion/flash)

Kullanim:
  python ptfx_kenney.py --ad smoke_07 --cikti out.png
  python ptfx_kenney.py --liste
"""
from __future__ import annotations

import argparse
import io
import os
import tempfile
import zipfile

KOK = os.path.join(tempfile.gettempdir(), "kenney")
PAKET = [
    (os.path.join(KOK, "particle-pack.zip"), "PNG (Transparent)/"),
    (os.path.join(KOK, "smoke-particles.zip"), "PNG/"),
]


def katalog():
    """ad -> (zip yolu, zip ici yol)"""
    d = {}
    for zp, on in PAKET:
        if not os.path.exists(zp):
            continue
        with zipfile.ZipFile(zp) as z:
            for n in z.namelist():
                if not n.startswith(on) or not n.lower().endswith(".png"):
                    continue
                ad = os.path.splitext(os.path.basename(n))[0]
                d.setdefault(ad, (zp, n))
    return d


def cikar(ad, cikti, coz=512):
    """⛔ Kenney dokulari SIKI KIRPILMIS degil; bazilarinda genis bos kenar
    var. Alfa bbox'ina kirp, kareye ortala, hedef coznurluge olcekle --
    "alpha coverage" kurali (VFXDoc) bunu gerektiriyor.
    """
    from PIL import Image
    k = katalog()
    if ad not in k:
        return "doku yok: %s" % ad
    zp, n = k[ad]
    with zipfile.ZipFile(zp) as z:
        im = Image.open(io.BytesIO(z.read(n))).convert("RGBA")
    kutu = im.getchannel("A").getbbox()
    if kutu:
        im = im.crop(kutu)
    w, h = im.size
    s = max(w, h)
    pay = int(s * 0.05)
    tuval = Image.new("RGBA", (s + 2 * pay, s + 2 * pay), (0, 0, 0, 0))
    tuval.paste(im, (pay + (s - w) // 2, pay + (s - h) // 2))
    tuval = tuval.resize((coz, coz), Image.LANCZOS)
    tuval.save(cikti)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ad")
    ap.add_argument("--cikti")
    ap.add_argument("--coz", type=int, default=512)
    ap.add_argument("--liste", action="store_true")
    a = ap.parse_args()

    k = katalog()
    if a.liste or not a.ad:
        print("%d doku:" % len(k))
        for x in sorted(k):
            print("  ", x)
        return 0
    h = cikar(a.ad, a.cikti, a.coz)
    if h:
        print(h)
        return 1
    print("cikarildi: %s" % a.cikti)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
