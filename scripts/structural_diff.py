#!/usr/bin/env python3
"""structural_diff.py — iki kaynagi DUGUM VARLIGI uzerinden karsilastirir.

NEDEN DEGER DEGIL YAPI
======================
Bir export'un "0 uyari" vermesi dosyanin dogru oldugunu GOSTERMEZ. Olculmus
vaka: Sollumz'un yazdigi ped .yft'i oyunu ~4 saniyede cokertiyordu; export
tek bir uyari vermemisti. Sebep bir alanin YANLIS DEGERI degil, bir dugumun
HIC OLMAMASIYDI. Alan alan deger karsilastiran hicbir denetim bunu yakalamaz;
"hangi dugumler var, hangileri yok" karsilastirmasi yakalar.

Olcum (bu arac yazilirken yapildi): vanilla mp_m_freemode_01.yft'te
`<Physics>` dugumu HIC YOKTUR. Yani "ped .yft'ini fiziksiz gonder" tavsiyesi
vanilla'nin zaten yaptigi seydir -- ve fazladan bir `Physics` dugumu bu diff'te
"SENDE VAR, VANILLA'DA YOK" olarak gorunur.

SINIR CIZGISI RAPORLANIR
========================
Bir alt agacin tamami eksikse her torunu ayri ayri yazmak gurultudur
(`Physics` yoksa altindaki 200 yol da yoktur). Bu yuzden yalnizca EBEVEYNI
IKI TARAFTA DA BULUNAN yollar bildirilir: farkin basladigi sinir.

KULLANIM
========
    python assetdb.py diff <seninki> <vanilla>
    python assetdb.py diff mine.yft vanilla.yft --limit 40
"""
from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_xml import kok_oku  # noqa: E402

# Ayni yolun iki tarafta da bulundugu ama adedin cok farkli oldugu durum.
# Esik olculmus bir sabit degil, gurultu filtresidir: 2 kat ve uzeri fark
# "ayni yapinin farkli doluluğu" degil, "farkli yapi" isaretidir.
ADET_ORANI = 2.0


def yol_sayaci(kok):
    """{indekssiz dugum yolu: adet}. Indeks atilir ki Item[3] ile Item[7]
    ayni yol sayilsin -- karsilastirilan sey yapi, icerik degil."""
    sayac = collections.Counter({kok.tag: 1})
    yigin = [(kok, kok.tag)]
    while yigin:
        el, yol = yigin.pop()
        for c in el:
            y = f"{yol}/{c.tag}"
            sayac[y] += 1
            yigin.append((c, y))
    return sayac


def _ebeveyn(yol):
    return yol.rsplit("/", 1)[0] if "/" in yol else None


def sinir_yollari(eksikler, ortak):
    """Farkin BASLADIGI yollar: ebeveyni iki tarafta da bulunanlar."""
    return [y for y in eksikler if _ebeveyn(y) is None or _ebeveyn(y) in ortak]


def karsilastir(a_sayac, b_sayac):
    """a=seninki, b=vanilla. (sende_yok, sende_fazla, adet_farki) dondurur."""
    a, b = set(a_sayac), set(b_sayac)
    ortak = a & b
    sende_yok = sorted(sinir_yollari(b - a, ortak))
    sende_fazla = sorted(sinir_yollari(a - b, ortak))

    # Adet farkinda da SINIR raporlanir. Bir dugum 3'e 1 farkliysa butun
    # cocuklari da 3'e 1 farklidir; 12 satirin tamami tek sebepten cikar.
    # Yalnizca EBEVEYNININ adetleri esit olan yollar bildirilir: farkin
    # basladigi yer. (Olculdu: custom prop vs vanilla supurge -> 12 satir 2'ye
    # dustu, bilgi kaybi olmadan.)
    adet = []
    for y in sorted(ortak):
        na, nb = a_sayac[y], b_sayac[y]
        if na == nb:
            continue
        buyuk, kucuk = max(na, nb), min(na, nb)
        if kucuk != 0 and buyuk / kucuk < ADET_ORANI:
            continue
        ust = _ebeveyn(y)
        if ust and ust in ortak and a_sayac[ust] != b_sayac[ust]:
            continue  # fark yukarida basliyor, burada tekrar etme
        adet.append((y, na, nb))
    return sende_yok, sende_fazla, adet


def _yaz(baslik, satirlar, limit, aciklama=""):
    if not satirlar:
        return
    print(f"\n=== {baslik} ({len(satirlar)}) ===")
    if aciklama:
        print(f"  {aciklama}")
    for s in satirlar[:limit]:
        print(f"  {s}")
    if len(satirlar) > limit:
        print(f"  ... ve {len(satirlar) - limit} tane daha (--limit ile artir)")


def calistir(args):
    from doctor_common import _tr

    kok_a, hata_a = kok_oku(args.mine)
    if hata_a:
        print(f"ERROR: {args.mine}: {hata_a}", file=sys.stderr)
        print("  " + _tr({
            "tr": "Karsilastirma YAPILMADI - sonuc hakkinda hicbir sey iddia edilemez.",
            "en": "Comparison NOT performed - nothing can be claimed about the result."}),
            file=sys.stderr)
        return 2
    kok_b, hata_b = kok_oku(args.vanilla)
    if hata_b:
        print(f"ERROR: {args.vanilla}: {hata_b}", file=sys.stderr)
        print("  " + _tr({
            "tr": "Karsilastirma YAPILMADI - sonuc hakkinda hicbir sey iddia edilemez.",
            "en": "Comparison NOT performed - nothing can be claimed about the result."}),
            file=sys.stderr)
        return 2

    if kok_a.tag != kok_b.tag:
        print(f"UYARI: kok dugumler farkli ({kok_a.tag} vs {kok_b.tag}) - "
              f"muhtemelen farkli kaynak tipleri karsilastiriliyor.")

    sa, sb = yol_sayaci(kok_a), yol_sayaci(kok_b)
    sende_yok, sende_fazla, adet = karsilastir(sa, sb)

    print(f"SENINKI : {os.path.basename(args.mine)}   ({kok_a.tag}, "
          f"{len(sa)} farkli yol)")
    print(f"VANILLA : {os.path.basename(args.vanilla)}   ({kok_b.tag}, "
          f"{len(sb)} farkli yol)")

    _yaz("VANILLA'DA VAR, SENDE YOK", sende_yok, args.limit,
         "En tehlikeli yon: motorun bekledigi bir yapi eksik olabilir.")
    _yaz("SENDE VAR, VANILLA'DA YOK", sende_fazla, args.limit,
         "Fazladan yapi. Ped .yft'inde 'Physics' burada gorunuyorsa cikar.")
    if adet:
        print(f"\n=== ADET FARKI ({len(adet)}) ===")
        print(f"  Ayni yol iki tarafta da var ama sayi {ADET_ORANI:g}x+ farkli.")
        for y, na, nb in adet[:args.limit]:
            print(f"  {y}   seninki={na}  vanilla={nb}")
        if len(adet) > args.limit:
            print(f"  ... ve {len(adet) - args.limit} tane daha")

    toplam = len(sende_yok) + len(sende_fazla) + len(adet)
    print()
    if toplam == 0:
        print("YAPISAL FARK YOK - iki dosya ayni dugum kumesine sahip.")
        return 0
    print(f"{len(sende_yok)} eksik | {len(sende_fazla)} fazla | "
          f"{len(adet)} adet farki")
    return 1
