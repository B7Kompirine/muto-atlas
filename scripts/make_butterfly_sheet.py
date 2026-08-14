#!/usr/bin/env python3
"""make_butterfly_sheet.py — kanat cirpan kelebek sprite sheet'i uretir.

NEDEN PROSEDUREL: bir metin-gorsel modeli 16 kareyi TUTARLI uretemez --
her karede kelebegin govdesi/oranlari kayar, cirpma titrer. Kanat cirpma
geometrik olarak basit oldugu icin prosedurel uretim hem kareler arasi
tutarliligi hem ortalanmayi hem esit acisal araligi GARANTI eder.
Sprite sheet'te bunlarin ucu de zorunludur.

⛔ CIKTI GRI MASKEDIR, renkli degil. Partikul dokusunun rengi motordan
   gelir (particle rule'un ptxu_Colour keyframe'i). Doku renkli olursa
   tint uzerine biner ve renk kontrolu kaybolur -- decal tarafinda tam
   bu yasandi (fxdecal dokularinda 800 renk ciftinin tamami R=G=B).

Kareler SOLDAN SAGA, YUKARIDAN ASAGIYA dizilir (satir onceligi).

Kullanim:
  python make_butterfly_sheet.py cikti.png --sutun 4 --satir 4 --hucre 128
"""
from __future__ import annotations

import argparse
import math

from PIL import Image, ImageDraw

SS = 4          # supersample carpani (kenar yumusatma icin)

# --- Kelebek govdesi: normalize koordinat, y YUKARI pozitif, [-1,1] ---
# Ust gorunum. Kanatlar govdenin saginda tanimli, sola AYNALANIR.
ON_KANAT = [
    (0.04, 0.34), (0.30, 0.52), (0.60, 0.66), (0.84, 0.60),
    (0.94, 0.36), (0.86, 0.14), (0.55, 0.02), (0.20, -0.02), (0.04, 0.02),
]
ARKA_KANAT = [
    (0.04, -0.04), (0.34, -0.10), (0.62, -0.28), (0.70, -0.52),
    (0.56, -0.72), (0.30, -0.74), (0.12, -0.55), (0.04, -0.30),
]
# Kanat deseni: (merkez_x, merkez_y, yaricap, alfa) -- govdeye gore
BENEK = [
    (0.62, 0.42, 0.13, 0.45), (0.40, 0.22, 0.09, 0.55),
    (0.44, -0.40, 0.11, 0.45), (0.28, -0.58, 0.07, 0.60),
]


def chaikin(p, tur=4):
    """Kapali cokgeni yumusatir (Chaikin kose kesme).

    Ham cokgen 128px hucrede KOSELI okunur -- kanat kenarindaki kirilmalar
    gozle secilir. Her tur kose sayisini ikiye katlayip kirikligi yariya
    indirir; 4 tur 128px'te tamamen puruzsuz."""
    for _ in range(tur):
        y = []
        for i in range(len(p)):
            a, b = p[i], p[(i + 1) % len(p)]
            y.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            y.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        p = y
    return p


def cokgen(d, noktalar, gen_carp, olcek, mrk, dolgu):
    """Bir kanadi cizer. gen_carp: cirpma foreshortening'i (yatay ezilme)."""
    p = [(mrk + x * gen_carp * olcek, mrk - y * olcek)
         for x, y in chaikin(noktalar)]
    d.polygon(p, fill=dolgu)


def kare_ciz(boy, faz, ss=SS):
    """Tek kareyi (L modunda alfa maskesi) uretir. faz: 0..1 cevrim icinde."""
    n = boy * ss
    im = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(im)
    mrk = n / 2.0
    olcek = n * 0.45          # hucre kenarina degmesin

    # ⛔ Cirpma UST GORUNUMDE yatay kisalma olarak okunur.
    #    Kanat dihedral acisi t -> ekranda genislik cos(t) ile carpilir.
    #    Tam cevrim: sin ile git-gel, boylece sheet KUSURSUZ DONGU olur.
    aci = math.radians(62.0) * math.sin(2 * math.pi * faz)
    geni = math.cos(aci)
    # kanat kalkinca govde biraz asagi kayar gibi durur (hacim hissi)
    kayma = -0.05 * abs(math.sin(aci)) * olcek

    for yon in (1, -1):
        gc = geni * yon
        cokgen(d, ON_KANAT, gc, olcek, mrk, 235)
        cokgen(d, ARKA_KANAT, gc, olcek, mrk, 215)

    # kanat deseni (alfa dusuk benekler -> tint'te doku hissi)
    for bx, by, br, ba in BENEK:
        for yon in (1, -1):
            cx = mrk + bx * geni * yon * olcek
            cy = mrk - by * olcek
            r = br * olcek * max(0.35, geni)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(255 * ba))

    # govde: ince elips + kafa
    gw, gh = 0.055 * olcek, 0.42 * olcek
    d.ellipse([mrk - gw, mrk - gh + kayma, mrk + gw, mrk + gh * 0.85 + kayma], fill=255)
    kr = 0.075 * olcek
    d.ellipse([mrk - kr, mrk - gh - kr * 0.9 + kayma,
               mrk + kr, mrk - gh + kr * 1.1 + kayma], fill=255)

    # antenler
    for yon in (1, -1):
        x0, y0 = mrk + yon * kr * 0.5, mrk - gh + kayma
        x1, y1 = mrk + yon * 0.26 * olcek, mrk - 0.62 * olcek + kayma
        d.line([x0, y0, x1, y1], fill=200, width=max(1, int(n * 0.008)))
        ur = n * 0.012
        d.ellipse([x1 - ur, y1 - ur, x1 + ur, y1 + ur], fill=220)

    return im.resize((boy, boy), Image.LANCZOS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cikti")
    ap.add_argument("--sutun", type=int, default=4)
    ap.add_argument("--satir", type=int, default=4)
    ap.add_argument("--hucre", type=int, default=128)
    a = ap.parse_args()

    kare_sayisi = a.sutun * a.satir
    gen, yuk = a.sutun * a.hucre, a.satir * a.hucre
    if gen & (gen - 1) or yuk & (yuk - 1):
        print(f"[!] UYARI: {gen}x{yuk} 2'nin kuvveti degil, DXT sikistirmasi "
              f"sorun cikarabilir")

    sheet = Image.new("RGBA", (gen, yuk), (255, 255, 255, 0))
    for i in range(kare_sayisi):
        m = kare_ciz(a.hucre, i / kare_sayisi)
        # renk BEYAZ, sekil ALFA'da -- motor tint'i uzerine biner
        hucre = Image.merge("RGBA", (
            Image.new("L", m.size, 255), Image.new("L", m.size, 255),
            Image.new("L", m.size, 255), m))
        sheet.paste(hucre, ((i % a.sutun) * a.hucre, (i // a.sutun) * a.hucre))

    sheet.save(a.cikti)
    print(f"[+] {a.cikti}  {gen}x{yuk}  {a.sutun}x{a.satir} = {kare_sayisi} kare "
          f"(hucre {a.hucre}px)")
    print("    kareler: soldan saga, yukaridan asagiya · dongu kusursuz")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
