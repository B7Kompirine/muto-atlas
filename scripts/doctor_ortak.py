#!/usr/bin/env python3
"""doctor_ortak.py — doctor denetimlerinin ortak ilkelleri.

Ayri dosyada olmasinin sebebi dairesel import: doctor.py denetimleri cagirir,
denetimler de siddet seviyelerine ve Rapor'a ihtiyac duyar. Ortak parcalar
burada durunca iki yon de bu modulu import eder, birbirini degil.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n import get_lang  # noqa: E402

# --- SIDDET SEVIYELERI --------------------------------------------------------
# FATAL  : oyun coker ya da kaynagin TAMAMI duser (hicbir komut kaydolmaz)
# SILENT : hata vermeden calismaz -- en pahali sinif, turu yiyen budur
# WARN   : supheli, kasitli olabilir
FATAL, SILENT, WARN = "FATAL", "SILENT", "WARN"
SIRA = {FATAL: 0, SILENT: 1, WARN: 2}

# NOT: desteklenen binary uzantilari (RES_EXT) res_xml.py'de tanimlidir --
# donusumu yapan modulde. Iki kopya tutmak, birine uzanti eklendiginde
# digerinin sessizce eski kalmasi demekti.


def _tr(d):
    """Bilingual sozlukten aktif dile gore metin sec."""
    return d.get(get_lang(), d.get("en", next(iter(d.values()))))


class Bulgu:
    __slots__ = ("seviye", "kod", "yol", "mesaj", "ipucu")

    def __init__(self, seviye, kod, yol, mesaj, ipucu=""):
        self.seviye, self.kod, self.yol = seviye, kod, yol
        self.mesaj, self.ipucu = mesaj, ipucu


class Rapor:
    def __init__(self):
        self.bulgular = []
        self.atlanan = []      # (yol, sebep) -- DENETLENEMEDI
        self.denetlenen = 0

    def ekle(self, seviye, kod, yol, mesaj, ipucu=""):
        self.bulgular.append(Bulgu(seviye, kod, yol, mesaj, ipucu))

    def atla(self, yol, sebep):
        self.atlanan.append((yol, sebep))


BOS_HASH = {"", "0", "hash_0", "hash_00000000"}

# GTA klipleri 30 fps. OLCULDU (vanilla mp_safehousewine@ + move_m@brave ve
# kendi derlenmis ciktimiz): animasyonun Duration alani SON KARENIN zamanidir,
#     Duration == (FrameCount - 1) / 30
# ve vanilla'da klibin EndTime'i animasyonun Duration'ini HIC asmaz (olculen
# en buyuk fark -1 kare, 37 ciftte 0 ihlal). Bir klip Duration'i asiyorsa
# animasyonda olmayan bir kareyi istiyor demektir.
KARE = 1.0 / 30.0


def _oznitelik(el, ad="value"):
    if el is None:
        return None
    try:
        return float(el.get(ad))
    except (TypeError, ValueError):
        return None


def _hash_bos(deger):
    return (deger or "").strip().lower() in BOS_HASH
