#!/usr/bin/env python3
"""cycle.py — hava timecycle'ini bir saatte degerlendir.

NEDEN VAR
=========
`timecycle.py` MODIFIER'lari bilir (odanin ezmesi). Bu modul onun altindaki
TABAN katmani bilir: hava cycle'i. "Prop neden boyle gorunuyor" sorusunun
sirasi sudur — once taban cycle (hangi hava, kacinci saat), sonra odanin
modifier'i, en sonda prop'un kendi isigi. Ikisi burada birlestirilebilir.

OLCULEN, TAHMIN EDILMEYEN
=========================
* Bir cycle dosyasi `cycle > region > <degisken>metin</degisken>` yapisindadir
  ve metin KEYFRAME BASINA bir deger tasir. **13 keyframe vardir, 24 saat
  degil.** "saat = indeks" varsayimi her seyi kaydirir.
* O 13 keyframe'in saatleri `time.xml`'dedir — ama IKI tane time.xml var.
  Dogrusu `common.rpf\\data\\levels\\gta5\\time.xml` (13 sample);
  `common.rpf\\data\\time.xml` 4 sample'lik bambaska bir dosyadir.
  Saatler: 0 5 6 7 10 12 16 17 18 19 20 21 22
* TUZAK: bir sample `name="09:00"` yazar ama `hour="10"` tasir. **Ad yalan
  soyler, `hour` niteligi esastir.** Ada bakan sonraki tum keyframe'leri bir
  saat kaydirir.
* Renkler zaten 0..1'dir (olculen maks 1.002); hicbir yerde /255 yoktur.
* `light_dir_mult` HDR'dir ve 54'e kadar cikar. Kirpma opsiyonel degildir.
* Bolge katmani vardir: GLOBAL ve URBAN. Varsayilan GLOBAL.

KIRPMA TAVANLARI
================
Asagidaki tavanlar MOTOR SABITI DEGIL, sunum kalibrasyonudur — bu yuzden
parametre, gomulu sabit degil. Varsayilanlar vanilla goruntuyle
karsilastirilarak dogrulanmalidir; degistirdiginde gunes/ortam dengesi degisir.

KULLANIM
========
    python assetdb.py cycle --liste
    python assetdb.py cycle w_clear --saat 20
    python assetdb.py cycle w_thunder --saat 3 --mod v_dark --guc 1.0
    python assetdb.py cycle w_clear --saat 12 --bolge URBAN

Veri yoksa: powershell -File build_cycle.ps1 -GtaFolder "<GTA folder>"
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from math import sin, cos, pi, sqrt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data", "timecycle")
MODS_TSV = os.path.join(os.path.dirname(HERE), "data", "timecycle.tsv.gz")

# Sunum kalibrasyonu — motor sabiti degil, bkz. yukarisi.
TAVAN_ORTAM = 0.5      # dogal/yapay/yonlu ortam terimlerinin tavani
TAVAN_GUNES = 1.0      # dogrudan gunes renginin tavani
TABAN_GUNES_CARPAN = 0.5   # light_dir_mult icin alt sinir

_cache = {}
_mods = None


# ----------------------------------------------------------------- veri okuma

def mevcut():
    if not os.path.isdir(DATA):
        return []
    return sorted(f[:-4] for f in os.listdir(DATA)
                  if f.startswith("w_") and f.endswith(".xml"))


def _saatler():
    root = ET.parse(os.path.join(DATA, "time.xml")).getroot()
    hrs = [int(s.get("hour")) for s in root.findall(".//sample")]   # name DEGIL
    sun = root.find(".//suninfo")
    moon = root.find(".//mooninfo")
    return (hrs,
            float(sun.get("sun_roll", 122.0)) if sun is not None else 122.0,
            float(moon.get("moon_roll", -122.0)) if moon is not None else -122.0)


def yukle(hava="w_clear", bolge="GLOBAL"):
    key = (hava, bolge)
    if key in _cache:
        return _cache[key]
    path = os.path.join(DATA, hava + ".xml")
    if not os.path.isfile(path):
        raise FileNotFoundError("no such cycle: %s (available: %s)" % (path, mevcut()))
    cyc = list(ET.parse(path).getroot())[0]
    regions = {r.get("name"): r for r in cyc}
    reg = regions.get(bolge)
    if reg is None:                      # Element dogruluk testi deprecated
        reg = list(regions.values())[0]
    vals = {}
    for el in reg:
        try:
            vals[el.tag] = [float(x) for x in (el.text or "").split()]
        except ValueError:
            continue
    hrs, sun_roll, moon_roll = _saatler()
    tc = {"hava": hava, "bolge": reg.get("name"), "vars": vals, "saatler": hrs,
          "sun_roll": sun_roll, "moon_roll": moon_roll, "cycle": cyc.get("name")}
    _cache[key] = tc
    return tc


def _mod_yukle():
    global _mods
    if _mods is not None:
        return _mods
    _mods = {}
    if not os.path.isfile(MODS_TSV):
        return _mods
    import gzip
    with gzip.open(MODS_TSV, "rt", encoding="utf-8") as fh:
        next(fh, None)
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 3:
                continue
            try:
                _mods.setdefault(p[0].lower(), {})[p[1]] = float(p[2])
            except ValueError:
                continue
    return _mods


def modifierlar(desen=""):
    d = desen.lower()
    return sorted(k for k in _mod_yukle() if d in k)


# ------------------------------------------------------------- ornekleme

def _ornekle_taban(tc, ad, saat, varsayilan=0.0):
    v = tc["vars"].get(ad)
    if not v:
        return varsayilan
    hrs = tc["saatler"]
    n = min(len(v), len(hrs))
    h = saat % 24.0
    if h < hrs[0]:                       # ilk anahtardan once -> sondan sar
        a, b = n - 1, 0
        span = (24.0 - hrs[a]) + hrs[b]
        t = ((h + 24.0) - hrs[a]) / span if span > 0 else 0.0
    else:
        a = 0
        for i in range(n):
            if hrs[i] <= h:
                a = i
        if a >= n - 1:
            a, b = n - 1, 0
            span = (24.0 - hrs[a]) + hrs[0]
            t = (h - hrs[a]) / span if span > 0 else 0.0
        else:
            b = a + 1
            span = float(hrs[b] - hrs[a])
            t = (h - hrs[a]) / span if span > 0 else 0.0
    return v[a] + (v[b] - v[a]) * min(max(t, 0.0), 1.0)


def _ornekle(tc, ad, saat, varsayilan=0.0, mod=None, guc=0.0):
    """Modifier bir DEGISTIRME degil, hedefe dogru harmandir."""
    taban = _ornekle_taban(tc, ad, saat, varsayilan)
    if mod and guc > 1e-4 and ad in mod:
        return taban + (mod[ad] - taban) * min(max(guc, 0.0), 1.0)
    return taban


def _renk(tc, kok, saat, yog=None, yog_var=1.0, mod=None, guc=0.0):
    rgb = [_ornekle(tc, kok + s, saat, 0.0, mod, guc) for s in ("_r", "_g", "_b")]
    k = _ornekle(tc, yog, saat, yog_var, mod, guc) if yog else yog_var
    return rgb, k


def _olcekle(rgb, k, tavan):
    return tuple(min(c * k, tavan) for c in rgb)


def gunes_yonu(tc, saat):
    """5h oncesi / 21h sonrasi ay devralir; Z asagi tasarsa 0'a kirpilir."""
    pitch = tc["sun_roll"] * pi / 180.0
    mroll = tc["moon_roll"] * pi / 180.0
    a = 0.5 + (saat - 6.0) / 14.0
    b = ((saat - 7.0) if saat > 12.0 else (saat + 17.0)) / 9.0
    sv = (sin(pi * a), -cos(pi * a), 0.0)
    mv = (-sin(pi * b), 0.0, -cos(pi * b))

    def rx(v, ang):
        c, s = cos(ang), sin(ang)
        return (v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c)

    v = rx(sv, pitch) if (5.0 <= saat <= 21.0) else rx(mv, -mroll)
    v = (v[0], v[1], max(v[2], 0.0))
    n = sqrt(sum(c * c for c in v)) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def ortam(hava="w_clear", saat=20.0, bolge="GLOBAL", hdr=False,
          modifier=None, guc=1.0,
          tavan_ortam=TAVAN_ORTAM, tavan_gunes=TAVAN_GUNES):
    """Bir saatteki ortam isigi + gunes. Onizleme shader'inin bekledigi adlarla."""
    tc = yukle(hava, bolge)
    ta = 1e9 if hdr else tavan_ortam
    tg = 1e9 if hdr else tavan_gunes

    mod = None
    if modifier:
        mod = _mod_yukle().get(modifier.lower())
        if mod is None:
            raise KeyError("no such modifier: %s (e.g. %s)"
                           % (modifier, modifierlar(modifier[:4])[:8]))
    else:
        guc = 0.0

    def S(ad, d=0.0):
        return _ornekle(tc, ad, saat, d, mod, guc)

    def C(kok, yog=None, d=1.0):
        return _renk(tc, kok, saat, yog, d, mod, guc)

    dc, dk = C("light_dir_col", "light_dir_mult")
    gunes = _olcekle(dc, max(dk, 0.0 if hdr else TABAN_GUNES_CARPAN), tg)

    ac, ak = C("light_directional_amb_col", "light_directional_amb_intensity")
    ak *= S("light_directional_amb_intensity_mult", 1.0)

    nu, nuk = C("light_natural_amb_up_col", "light_natural_amb_up_intensity")
    nuk *= S("light_natural_amb_up_intensity_mult", 1.0)
    nd, ndk = C("light_natural_amb_down_col", "light_natural_amb_down_intensity")
    au, auk = C("light_artificial_ext_up_col", "light_artificial_ext_up_intensity")
    ad, adk = C("light_artificial_ext_down_col", "light_artificial_ext_down_intensity")

    return {
        "amb_nat_up": _olcekle(nu, nuk, ta),
        "amb_nat_dn": _olcekle(nd, ndk, ta),
        "amb_art_up": _olcekle(au, auk, ta),
        "amb_art_dn": _olcekle(ad, adk, ta),
        "dir_amb": _olcekle(ac, ak, ta),
        "dir_col": gunes,
        "amb_down_wrap": S("light_amb_down_wrap", 1.0),
        "light_dir": gunes_yonu(tc, saat),
        "_meta": {"hava": tc["hava"], "bolge": tc["bolge"], "cycle": tc["cycle"],
                  "saat": saat, "modifier": modifier,
                  "guc": guc if modifier else 0.0},
    }


# ------------------------------------------------------------------- CLI

def calistir(args):
    if not os.path.isdir(DATA) or not mevcut():
        print("ERROR: the weather cycle layer is not installed.", file=sys.stderr)
        print("  powershell -File build_cycle.ps1 -GtaFolder \"<GTA klasoru>\"",
              file=sys.stderr)
        return 2
    if getattr(args, "liste", False) or not getattr(args, "hava", None):
        print("weather cycles (%d):" % len(mevcut()))
        for w in mevcut():
            print("  " + w)
        print("\nfor one cycle: assetdb.py cycle w_clear --hour 20")
        return 0
    try:
        a = ortam(args.hava, saat=args.saat, bolge=args.bolge,
                  modifier=args.mod, guc=args.guc)
    except (FileNotFoundError, KeyError) as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1
    m = a["_meta"]
    print("%s / %s  cycle=%s  hour=%s" % (m["hava"], m["bolge"], m["cycle"], m["saat"]))
    if m["modifier"]:
        print("modifier=%s  strength=%.2f" % (m["modifier"], m["guc"]))
    print()
    for k in ("dir_col", "dir_amb", "amb_nat_up", "amb_nat_dn",
              "amb_art_up", "amb_art_dn", "light_dir"):
        print("  %-14s %s" % (k, [round(v, 4) for v in a[k]]))
    print("  %-14s %s" % ("amb_down_wrap", round(a["amb_down_wrap"], 4)))
    return 0
