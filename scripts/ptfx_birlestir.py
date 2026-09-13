#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_birlestir.py — cok sayida `.ypt`yi TEK bir `.ypt`ye birlestirir.

⛔ NEDEN GEREKLI: `PtFxAssetStore Pool Full, Size == 400`.

Havuz EFEKT KURALINI degil DOSYAYI sayar. Kanit kesin: `core.ypt` tek
dosyada **964 efekt kurali** tasiyor, havuz ise 400 -- kural sayilsaydi
vanilla kendi basina havuzu patlatirdi. `RequestNamedPtfxAsset` de dosya
adini alir. Yani "efekt basina bir dosya" savurganliktir: 35 aile 35 slot
yerine **1** slot harcayabilir.

Birlestirme = dort sozlugun `<Item>`larini birlestirmek:
  EffectRuleDictionary · EmitterRuleDictionary · ParticleRuleDictionary
  · TextureDictionary

⛔ `TextureDictionary` HASH SIRALI olmak zorunda (RAGE ikili arama yapar).
   Olculdu: vanilla `core.ypt`in 107 dokusu Jenkins hash'ine gore sirali;
   ote yandan uc kural sozlugu sirali DEGIL (ne alfabetik ne hash). Yani
   yalniz dokulari sirala, otekilere dokunma.

⛔ Dokular XML'e GOMULU DEGIL: `<FileName>x.dds</FileName>` ile disaridan
   okunur. Birlestirilmis XML'in yaninda butun `.dds` dosyalari bulunmali.

Kullanim:
  python ptfx_birlestir.py --ad muto_efektler --klasor <dizin>
  python ptfx_birlestir.py --ad muto_efektler --klasor <dizin> --disla muto_x
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

BETIK = os.path.dirname(os.path.abspath(__file__))
SOZLUKLER = ("EffectRuleDictionary", "EmitterRuleDictionary",
             "ParticleRuleDictionary", "TextureDictionary")


def jenkins(s):
    """RAGE'in isim hash'i. Vanilla doku sirasiyla dogrulandi."""
    h = 0
    for c in s.lower().encode("utf-8"):
        h = (h + c) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    h = (h + (h << 15)) & 0xFFFFFFFF
    return h


def ogeler(xml, sozluk):
    """Bir sozlugun ust duzey <Item> govdelerini (ad, metin) olarak verir."""
    i = xml.find("<%s>" % sozluk)
    if i < 0:
        return []
    j = xml.find("</%s>" % sozluk)
    govde = xml[i + len(sozluk) + 2:j]
    # ⛔ Ust duzey <Item>'i regex ile bolmek ic ice <Item>lere takilir.
    #    Her kural tam bir `\n   <Name>` ile baslar; tepe noktalarindan bol.
    tepe = [m.start() for m in re.finditer(r"\n   <Name>[^<]+</Name>", govde)]
    if not tepe:
        return []
    cikti = []
    for n, s in enumerate(tepe):
        e = tepe[n + 1] if n + 1 < len(tepe) else len(govde)
        parca = govde[s:e]
        ad = re.search(r"<Name>([^<]+)</Name>", parca).group(1)
        # <Item> acilisini geri koy: tepe noktasi <Name>'den basliyor
        cikti.append((ad, "  <Item>" + parca.rstrip().rsplit("</Item>", 1)[0]
                      + "</Item>\n"))
    return cikti


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ad", required=True, help="birlesik varligin adi")
    ap.add_argument("--klasor", required=True)
    ap.add_argument("--disla", action="append", default=[],
                    help="bu onekle baslayan dosyalari alma")
    ap.add_argument("--derleme", action="store_true", help="yalniz XML uret")
    ap.add_argument("--tekille", action="store_true",
                    help="ayni ad birden cok dosyadan gelirse HATA verme, "
                         "tekille. ⚠ Yalniz BILINCLI paylasimda kullan: "
                         "bir bestelenmis efekt ile onun kaynak katmanlari "
                         "ayni emitter/particle kurallarini PAYLASIR. Bayat "
                         "dosya kazasini gizlememesi icin varsayilan HATA.")
    a = ap.parse_args()

    kaynaklar = sorted(f for f in os.listdir(a.klasor)
                       if f.endswith(".ypt.xml")
                       and not f.startswith(a.ad + ".")
                       and not any(f.startswith(d) for d in a.disla))
    if not kaynaklar:
        raise SystemExit("birlestirilecek .ypt.xml yok: %s" % a.klasor)

    toplam = {d: [] for d in SOZLUKLER}
    gorulen = {d: set() for d in SOZLUKLER}
    cakisma, nereden = {}, {}
    for f in kaynaklar:
        s = io.open(os.path.join(a.klasor, f), encoding="utf-8",
                    errors="replace").read()
        for d in SOZLUKLER:
            for ad, metin in ogeler(s, d):
                # ⛔ AYNI ADI IKI KEZ YAZMA. Iki aile ayni donorden
                #    uretilmisse dokulari farkli ama kural adlari benzersiz;
                #    yine de guvenlik icin ad bazinda tekille -- cift kayit
                #    sozlugu bozar ve hata vermez.
                if ad in gorulen[d]:
                    # ⛔ SESSIZCE ELEME. Onceki surum ilk gorulen kaydi
                    #    tutup otekini atiyordu; girdi klasorunde kalan
                    #    ESKI birlesik dosya (`muto_katalog.ypt.xml`)
                    #    boylece karisti ve dogru surumun kazanmasi yalniz
                    #    ALFABETIK SIRAYA kaldi. Sans degil hata olmali.
                    cakisma.setdefault((d, ad), []).append(f)
                    continue
                gorulen[d].add(ad)
                nereden[(d, ad)] = f
                toplam[d].append((ad, metin))

    if cakisma and a.tekille:
        print("ⓘ %d ad birden cok dosyada -- tekillendi (--tekille)"
              % len(cakisma))
        cakisma = {}
    if cakisma:
        print("⛔ AYNI AD BIRDEN COK DOSYADAN GELDI -- birlestirme durduruldu.")
        for (d, ad), fs in sorted(cakisma.items())[:12]:
            print("   %-24s %-28s once: %s | ayrica: %s"
                  % (d, ad, nereden.get((d, ad), "?"), ", ".join(fs)))
        print("   Girdi klasorunde eski bir birlesik dosya kalmis olabilir.")
        return 1

    # ⛔ Yalniz dokular hash sirali. Kural sozlukleri vanilla'da da sirali
    #    degil; siralamak gereksiz ve dogrulamayi zorlastirir.
    toplam["TextureDictionary"].sort(key=lambda t: jenkins(t[0]))

    parcalar = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n",
                "<ParticleEffectsList>\n",
                " <Name>%s</Name>\n" % a.ad]
    for d in ("EffectRuleDictionary", "EmitterRuleDictionary",
              "ParticleRuleDictionary"):
        parcalar.append(" <%s>\n" % d)
        parcalar += [m for _, m in toplam[d]]
        parcalar.append(" </%s>\n" % d)
    parcalar.append(" <DrawableDictionary />\n")
    parcalar.append(" <TextureDictionary>\n")
    parcalar += [m for _, m in toplam["TextureDictionary"]]
    parcalar.append(" </TextureDictionary>\n")
    parcalar.append("</ParticleEffectsList>\n")
    metin = "".join(parcalar)

    ET.fromstring(metin)  # bozuk XML'i derleyiciye goturme
    xml = os.path.join(a.klasor, a.ad + ".ypt.xml")
    io.open(xml, "w", encoding="utf-8").write(metin)
    print("kaynak dosya: %d" % len(kaynaklar))
    for d in SOZLUKLER:
        print("  %-24s %d oge" % (d, len(toplam[d])))

    # doku dosyalari yaninda mi?
    eksik = [ad + ".dds" for ad, _ in toplam["TextureDictionary"]
             if not os.path.exists(os.path.join(a.klasor, ad + ".dds"))]
    if eksik:
        print("⛔ EKSIK .dds (%d): %s" % (len(eksik), ", ".join(eksik[:6])))
        return 1

    if a.derleme:
        return 0
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", os.path.join(BETIK, "ypt_xml_to_bin.ps1"),
                    "-Xml", xml], check=False)
    ypt = os.path.join(a.klasor, a.ad + ".ypt")
    if not os.path.exists(ypt):
        print("⛔ derlenmedi")
        return 1
    print("\n%s.ypt  %d bayt" % (a.ad, os.path.getsize(ypt)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
