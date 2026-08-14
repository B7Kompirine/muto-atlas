#!/usr/bin/env python3
"""ptfx_onizleme.py — derlenmis .ypt'den okunan VERIYLE animasyonlu onizleme.

⚠ NE OLDUGU KONUSUNDA NET OL: bu bir MOTOR CIKTISI DEGILDIR.
GTA'nin partikul sistemi burada calismiyor. Bu betik, `.ypt` ikili
dosyasindan GERI OKUNAN keyframe'leri (spawn orani, omur, boyut egrisi,
renk/alfa egrisi) ve GOMULU DOKUYU alip bir onizleme cizer.

Kanitladigi sey:  dosyanin ICINDEKI veri gorunur bir efekt tarif ediyor mu
Kanitlamadigi sey: oyunun/FiveM'in bu dosyayi kabul edip etmedigi

Girdi `ypt_dokum.ps1` benzeri bir dokumden gelir:
  doku_ham.bin   -> BGRA ham piksel (A8R8G8B8)
  ptfx_veri.txt  -> TAG|SAHIP|AD|interval|R|G|B|A satirlari

Kullanim:
  python ptfx_onizleme.py <klasor> [--cikti onizleme.gif]
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys

from PIL import Image

KARE = 30          # fps
SURE = 3.0         # gif uzunlugu (sn)
TUVAL = 460        # piksel
METRE_PX = 150.0   # 1 metre kac piksel


def veri_oku(yol):
    """ptfx_veri.txt -> {ad: [(interval, r, g, b, a), ...]} + doku boyutu."""
    kf, doku = {}, None
    with open(yol, encoding="utf-8-sig") as f:
        for satir in f:
            satir = satir.strip()
            if not satir or satir.startswith("#"):
                continue
            p = satir.split("|")
            if p[0] == "DOKU":
                doku = (p[1], int(p[2]), int(p[3]), p[4])
                continue
            if len(p) < 8:          # BOS satiri
                continue
            ad = p[2].split(":")[-1]
            kf.setdefault(ad, []).append(tuple(float(x) for x in p[3:8]))
    for v in kf.values():
        v.sort(key=lambda x: x[0])
    return kf, doku


def egri(kf, ad, kanal=0, varsayilan=0.0):
    """Normalize omur boyunca (t: 0..1) dogrusal interpolasyon."""
    d = kf.get(ad)
    if not d:
        return lambda t: varsayilan
    if len(d) == 1:
        v = d[0][1 + kanal]
        return lambda t: v

    def f(t):
        t = max(0.0, min(1.0, t))
        for i in range(len(d) - 1):
            t0, t1 = d[i][0], d[i + 1][0]
            if t0 <= t <= t1:
                o = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                return d[i][1 + kanal] * (1 - o) + d[i + 1][1 + kanal] * o
        return d[-1][1 + kanal]
    return f


def sprite_yukle(klasor, gen, yuk):
    """DDS -> alfa maskesi (L). Renk motordan gelir, dokudan degil.

    DXT5'i Pillow acar; sikistirilmamis eski dosyalar icin ham BGRA
    dokumu de destekleniyor."""
    dds = os.path.join(klasor, "doku.dds")
    if os.path.exists(dds):
        return Image.open(dds).convert("RGBA").split()[3]
    ham = open(os.path.join(klasor, "doku_ham.bin"), "rb").read()
    bekl = gen * yuk * 4
    if len(ham) < bekl:
        sys.exit(f"doku kisa: {len(ham)} < {bekl}")
    return Image.frombytes("L", (gen, yuk),
                           bytes(ham[i * 4 + 3] for i in range(gen * yuk)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("klasor")
    ap.add_argument("--cikti", default="ptfx_onizleme.gif")
    ap.add_argument("--doku-png", default=None)
    a = ap.parse_args()

    kf, doku = veri_oku(os.path.join(a.klasor, "ptfx_veri.txt"))
    if not doku:
        sys.exit("DOKU satiri yok")
    _, gen, yuk, _ = doku
    maske = sprite_yukle(a.klasor, gen, yuk)
    if a.doku_png:
        maske.save(a.doku_png)

    # --- dosyadan okunan degerler ---
    oran = kf["m_spawnRateOverTimeKFP"][0][1]
    omur = kf["m_particleLifeKFP"][0][1]
    hiz = kf["m_speedScalarKFP"][0][1]
    # ⛔ Yukselmeyi Velocity DEGIL, TARGET DOMAIN'in konumu yapar.
    #    (m_positionKFP: kanal sirasi interval|X|Y|Z|W -> Z = indeks 3)
    yuks = kf["m_positionKFP"][0][3] if "m_positionKFP" in kf else 0.0
    dogum_r = kf["m_sizeOuterKFP"][0][1] if "m_sizeOuterKFP" in kf else 0.25
    b_min, b_max = egri(kf, "m_whdMinKFP"), egri(kf, "m_whdMaxKFP")
    renk = kf["m_rgbaMinKFP"][0]                       # r,g,b sabit
    alfa_e = egri(kf, "m_rgbaMinKFP", kanal=3, varsayilan=1.0)
    print(f"[i] oran={oran}/sn omur={omur}s hiz={hiz} yukselme={yuks}m "
          f"dogum_r={dogum_r}m renk=({renk[1]:.2f},{renk[2]:.2f},{renk[3]:.2f}) "
          f"tepe_alfa={renk[4]:.2f}")

    rng = random.Random(20260812)
    kareler, parcaciklar, kalinti = [], [], 0.0
    dt = 1.0 / KARE
    rgb = (int(renk[1] * 255), int(renk[2] * 255), int(renk[3] * 255))

    # dolu bir gorunumle baslamak icin bir omur boyu onceden isit
    for adim in range(int((SURE + omur) * KARE)):
        kalinti += oran * dt
        while kalinti >= 1.0:
            kalinti -= 1.0
            # dogum kuresi: creation domain yaricapi 0.25 m
            u, v = rng.random(), rng.random()
            th, ph = 2 * math.pi * u, math.acos(2 * v - 1)
            r = dogum_r * rng.random() ** (1 / 3)
            x0 = r * math.sin(ph) * math.cos(th)
            y0 = r * math.cos(ph)
            # hedef: target domain (merkez 0,yuks; ayni yaricap)
            hr = dogum_r * rng.random() ** (1 / 3)
            ht = 2 * math.pi * rng.random()
            hx = hr * math.cos(ht)
            hy = yuks + hr * math.sin(ht) * 0.6
            parcaciklar.append({
                "x": x0, "y": y0,
                "vx": (hx - x0) / omur * hiz,
                "vy": (hy - y0) / omur * hiz,
                "t": 0.0,
                "k": rng.random(),        # min/max arasi karisim
            })
        for p in parcaciklar:
            p["t"] += dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
        parcaciklar = [p for p in parcaciklar if p["t"] < omur]

        if adim < omur * KARE:            # isitma kareleri kaydedilmez
            continue

        tuval = Image.new("RGB", (TUVAL, TUVAL), (26, 26, 28))
        for p in parcaciklar:
            n = p["t"] / omur
            boy = b_min(n) + (b_max(n) - b_min(n)) * p["k"]
            px = max(2, int(boy * METRE_PX))
            al = max(0.0, min(1.0, alfa_e(n)))
            if al <= 0.004:
                continue
            m = maske.resize((px, px), Image.BILINEAR)
            m = m.point(lambda q, s=al: int(q * s))
            kat = Image.new("RGB", (px, px), rgb)
            X = int(TUVAL / 2 + p["x"] * METRE_PX - px / 2)
            Y = int(TUVAL * 0.72 - p["y"] * METRE_PX - px / 2)
            tuval.paste(kat, (X, Y), m)
        kareler.append(tuval)

    if not kareler:
        sys.exit("kare uretilmedi")
    kareler[0].save(a.cikti, save_all=True, append_images=kareler[1:],
                    duration=int(1000 / KARE), loop=0, optimize=True)
    print(f"[+] {a.cikti}  {len(kareler)} kare  "
          f"{os.path.getsize(a.cikti):,} bayt")


if __name__ == "__main__":
    main()
