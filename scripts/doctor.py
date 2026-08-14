#!/usr/bin/env python3
"""doctor.py — SESSIZ HATA KAPISI: asseti oyuna sokmadan once denetler.

NEDEN VAR
=========
GTA V asset hatalarinin cogu SESSIZDIR. Dosya derlenir, arac "0 uyari" der,
sunucu "Started resource" yazar -- ve oyunda hicbir sey olmaz. Sebebi bulmak
icin tek yol tur atmaktir: derle -> dagit -> sunucuyu yeniden baslat ->
BAGLANTIYI KES -> yeniden baglan -> bak -> tahmin et -> bastan.

Bu turlarin cogu, dosyaya bakarak onceden yakalanabilecek hatalara harcanir.
Bu arac o hatalari tur ATMADAN yakalar.

EN ONEMLI TASARIM KURALI
========================
DENETLENEMEYEN DOSYA "TEMIZ" SAYILMAZ. Bir dosya acilamadiysa, donusturucu
yoksa ya da bir denetim calistirilamadiysa bu AYRI bir bolumde bildirilir ve
cikis kodu 2 olur. Aksi halde arac "sahte guven" uretir -- yani tam olarak
onlemeye calistigi hata sinifinin kendisi olur.
    "Aracin gostermemesi, o seyin yok oldugu anlamina gelmez."

CIKIS KODLARI
=============
    0  denetlendi, bulgu yok
    1  bulgu var
    2  en az bir dosya DENETLENEMEDI (arac/katman eksik)
    3  ic hata

KULLANIM
========
    python assetdb.py doctor <dosya|klasor> [...]
    python assetdb.py doctor stream/ --recursive
    python assetdb.py doctor x.ycd --level silent   (WARN'lari gizle)
"""
from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from doctor_ortak import FATAL, SIRA, SILENT, WARN, Rapor, _tr  # noqa: E402
from doctor_kontroller import DENETCI  # noqa: E402
from res_xml import RES_EXT, toplu_kok_oku  # noqa: E402


CIFT_TIRE = re.compile(r"<!--(?:(?!-->).)*?--(?:(?!>).)", re.S)


def _ayrisma_hatasi(yol, hata, rap):
    """Ayrisma hatasinin SEBEBINI soyler. XML yorumundaki iki tire dosyayi
    ayristirilamaz yapar ve oyun bu durumda hata VERMEZ -- tanim sessizce hic
    yuklenmez. Sebebi soylemeyen bir 'ayristirilamadi' mesaji tur yedirir."""
    ham = ""
    if yol.lower().endswith(".xml"):
        try:
            ham = open(yol, "r", encoding="utf-8", errors="replace").read()
        except OSError:
            ham = ""
    if ham and CIFT_TIRE.search(ham):
        rap.ekle(FATAL, "XML002", yol, _tr({
            "tr": "XML yorumunun icinde iki tire (--) var. Dosya ayristirilamaz; "
                  "oyun hata VERMEZ, tanim hic yuklenmez.",
            "en": "An XML comment contains a double hyphen (--). The file is "
                  "unparseable; the game reports NO error, the definition simply "
                  "never loads."}))
    else:
        rap.ekle(FATAL, "XML001", yol, _tr({
            "tr": f"XML ayristirilamadi: {hata}",
            "en": f"XML could not be parsed: {hata}"}))
    rap.denetlenen += 1


def denetle_kok(kok, yol, rap, derlenmis):
    fn = DENETCI.get(kok.tag)
    if fn is None:
        rap.atla(yol, _tr({
            "tr": f"'{kok.tag}' icin denetim yok (henuz)",
            "en": f"no checks for '{kok.tag}' (yet)"}))
        return
    fn(kok, yol, rap, derlenmis)
    rap.denetlenen += 1


def hedefleri_topla(yollar, rekursif):
    for y in yollar:
        if os.path.isdir(y):
            gez = os.walk(y) if rekursif else [(y, [], os.listdir(y))]
            for kok, _, dosyalar in gez:
                for d in sorted(dosyalar):
                    tam = os.path.join(kok, d)
                    if os.path.isfile(tam) and _ilgili(tam):
                        yield tam
        elif os.path.isfile(y):
            yield y
        else:
            yield y  # var olmayan yol -> asagida atlanan olarak raporlanir


def _ilgili(yol):
    d = yol.lower()
    return d.endswith(".xml") or os.path.splitext(d)[1] in RES_EXT


def denetle_hepsi(yollar, rap):
    """Binary'ler TOPLU cevrilir (dosya basina PowerShell acmak 957 dosyada
    ~10 dakika suruyordu). XML kaynak dosyalari 'derlenmis' SAYILMAZ: Sollumz
    formunda konumsal eslesme normaldir, derlenmis dosyada degildir."""
    for yol, kok, hata in toplu_kok_oku(yollar):
        if hata:
            if hata.startswith("XML ayristirilamadi"):
                _ayrisma_hatasi(yol, hata, rap)
            else:
                rap.atla(yol, hata)
            continue
        denetle_kok(kok, yol, rap, derlenmis=not yol.lower().endswith(".xml"))


# =============================================================================
# Rapor
# =============================================================================
BASLIK = {
    FATAL: {"tr": "OYUN COKER / KAYNAK DUSER", "en": "GAME CRASHES / RESOURCE DIES"},
    SILENT: {"tr": "SESSIZ HATA (hata vermeden calismaz)",
             "en": "SILENT FAILURE (fails without any error)"},
    WARN: {"tr": "SUPHELI", "en": "SUSPICIOUS"},
}


def _kisa(yol):
    """Ust klasor + dosya adi. Sadece basename yazmak yetmez: ayni ad farkli
    klasorlerde bulunur (ornegin sollumz ciktisi ile geri okuma) ve rapor
    hangi dosyadan bahsettigini soyleyemez hale gelir."""
    ust = os.path.basename(os.path.dirname(yol))
    return f"{ust}/{os.path.basename(yol)}" if ust else os.path.basename(yol)


def yazdir(rap, esik):
    izin = {s for s in (FATAL, SILENT, WARN) if SIRA[s] <= SIRA[esik]}
    gosterilen = [b for b in rap.bulgular if b.seviye in izin]

    for seviye in (FATAL, SILENT, WARN):
        grup = [b for b in gosterilen if b.seviye == seviye]
        if not grup:
            continue
        print(f"\n=== {seviye}: {_tr(BASLIK[seviye])} ({len(grup)}) ===")
        for b in grup:
            print(f"  [{b.kod}] {_kisa(b.yol)}")
            print(f"         {b.mesaj}")
            if b.ipucu:
                print(f"         -> {b.ipucu}")

    # DENETLENEMEYEN dosyalar asla sessizce gecmez.
    if rap.atlanan:
        print(f"\n=== {_tr({'tr': 'DENETLENEMEDI', 'en': 'NOT INSPECTED'})} "
              f"({len(rap.atlanan)}) ===")
        print("  " + _tr({
            "tr": "Bu dosyalar hakkinda HICBIR SEY iddia edilemez -- 'temiz' DEGIL.",
            "en": "NOTHING can be claimed about these files -- they are NOT 'clean'."}))
        for yol, sebep in rap.atlanan:
            print(f"  - {yol}\n      {sebep}")

    print()
    if not gosterilen and not rap.atlanan:
        print(_tr({"tr": f"TEMIZ - {rap.denetlenen} dosya denetlendi, bulgu yok.",
                   "en": f"CLEAN - {rap.denetlenen} file(s) inspected, no findings."}))
    else:
        print(_tr({
            "tr": f"{rap.denetlenen} dosya denetlendi | {len(gosterilen)} bulgu | "
                  f"{len(rap.atlanan)} denetlenemedi",
            "en": f"{rap.denetlenen} file(s) inspected | {len(gosterilen)} finding(s) | "
                  f"{len(rap.atlanan)} not inspected"}))


def calistir(args):
    rap = Rapor()
    denetle_hepsi(list(hedefleri_topla(args.paths, args.recursive)), rap)

    esik = {"fatal": FATAL, "silent": SILENT, "warn": WARN}[args.level]
    yazdir(rap, esik)

    if any(b.seviye in {s for s in (FATAL, SILENT, WARN) if SIRA[s] <= SIRA[esik]}
           for b in rap.bulgular):
        return 1
    if rap.atlanan:
        return 2
    return 0

