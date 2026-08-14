#!/usr/bin/env python3
"""make_test_sheet.py — sprite sheet DILIMLEMESINI kesin sinayan test dokusu.

⛔ NEDEN GEREKLI: ayni sekli tekrar eden bir sheet ile "motor dilimliyor mu"
   sorusu EKRANDAN CEVAPLANAMAZ. Kelebek denemesinde tam bu yasandi --
   kelebegin dort kanadi var, tek hucre de 2x2 gibi okunuyor, tum sheet de.
   Iki durum gorsel olarak ayirt edilemeyince tur boyu yanlis yon kovalandi.

   Bu betik her hucreye BASKA bir sekil koyar. Oyunda:
     tek sekil goruyorsan   -> dilimleme CALISIYOR
     dort sekli birden      -> dilimleme YOK, tum doku ciziliyor
   Baska yorum yok.

Sekiller kasten kaba ve yuksek kontrastli: kucuk olcekte de ayirt edilsin.

Kullanim:
  python make_test_sheet.py cikti.png --hucre 128 --izgara 2
"""
from __future__ import annotations

import argparse
import math

from PIL import Image, ImageDraw

SS = 4     # supersample


def sekil_ciz(d, tur, n, dolgu=255):
    """n x n tuval icine tek sekil. Kenar payi birakilir ki hucre
    sinirinda tasma olmasin (tasma dilimlemeyi yanlis okutur)."""
    p = n * 0.14
    a, b = p, n - p
    orta = n / 2.0
    kal = int(n * 0.13)
    if tur == "disk":
        d.ellipse([a, a, b, b], fill=dolgu)
    elif tur == "halka":
        d.ellipse([a, a, b, b], outline=dolgu, width=kal)
    elif tur == "arti":
        d.rectangle([orta - kal, a, orta + kal, b], fill=dolgu)
        d.rectangle([a, orta - kal, b, orta + kal], fill=dolgu)
    elif tur == "ucgen":
        d.polygon([(orta, a), (b, b), (a, b)], fill=dolgu)
    elif tur == "kare":
        d.rectangle([a, a, b, b], outline=dolgu, width=kal)
    elif tur == "capraz":
        d.line([a, a, b, b], fill=dolgu, width=kal)
        d.line([a, b, b, a], fill=dolgu, width=kal)
    else:
        # numaralandirilmis nokta dizisi: 6+ hucre icin
        k = int(tur)
        r = n * 0.10
        for i in range(k):
            ac = 2 * math.pi * i / max(k, 1) - math.pi / 2
            cx, cy = orta + math.cos(ac) * n * 0.26, orta + math.sin(ac) * n * 0.26
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=dolgu)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cikti")
    ap.add_argument("--hucre", type=int, default=128)
    ap.add_argument("--izgara", type=int, default=2, help="izgara kenari (2 -> 2x2)")
    a = ap.parse_args()

    sekiller = ["disk", "halka", "arti", "ucgen", "kare", "capraz"]
    k = a.izgara
    gen = a.hucre * k
    sheet = Image.new("RGBA", (gen, gen), (255, 255, 255, 0))

    for i in range(k * k):
        n = a.hucre * SS
        m = Image.new("L", (n, n), 0)
        d = ImageDraw.Draw(m)
        sekil_ciz(d, sekiller[i] if i < len(sekiller) else str(i + 1), n)
        m = m.resize((a.hucre, a.hucre), Image.LANCZOS)
        hucre = Image.merge("RGBA", (
            Image.new("L", m.size, 255), Image.new("L", m.size, 255),
            Image.new("L", m.size, 255), m))
        sheet.paste(hucre, ((i % k) * a.hucre, (i // k) * a.hucre))

    sheet.save(a.cikti)
    ad = [sekiller[i] if i < len(sekiller) else str(i + 1) for i in range(k * k)]
    print(f"[+] {a.cikti}  {gen}x{gen}  {k}x{k} = {k*k} kare")
    print(f"    hucreler (soldan saga, yukaridan asagiya): {', '.join(ad)}")
    print("    OYUNDA: tek sekil -> dilimleme VAR | hepsi birden -> dilimleme YOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
