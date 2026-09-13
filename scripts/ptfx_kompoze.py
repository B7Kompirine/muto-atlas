#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_kompoze.py — COK EMITTERLI efekt besteler (katmanlama).

⛔ NEDEN: olculdu, vanilla efektlerinin **%74'u cok emitterli**
   (713/964); `exp_grd_grenade` 6, `exp_grd_molotov` 7 katman tasiyor.
   Bizim katalogun tamami TEK emitterliydi -- formatin en basit %26'si.
   "Hepsi birbirinin turevi" goruntusunun sebebi budur: profesyonel VFX
   derinligini katmanlardan alir (beyaz cekirdek + turuncu top + yukselen
   duman + enkaz + sok halkasi UST USTE).

Vanilla'dan okunan katman alanlari:
   `<EmitterRule>` / `<ParticleRule>`  -> katmanin kaynagi
   `Unknown10`      -> katmanin GECIKMESI (saniye). exp_grd_grenade'de
                       0 / 0.034 / 0.068 -- 30 fps'te 0, 1, 2 kare.
   `ParticleScale`  -> katman basina boyut carpani (molotov'da 1.2)
   `Unknown14`      -> katman omur/yogunluk carpani (0.7 - 1.0)

Kullanim:
  python ptfx_kompoze.py --ad my_patlama --klasor <dizin> \\
      --katman my_ark_carpmasi:0:1.0 \\
      --katman my_alev_topu:0.034:1.2 \\
      --katman my_duman:0.10:1.4
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
sys.path.insert(0, BETIK)
from ptfx_birlestir import jenkins, ogeler  # noqa: E402

SOZLUKLER = ("EmitterRuleDictionary", "ParticleRuleDictionary",
             "TextureDictionary")

# Bir EventEmitter kalemi. Alan sirasi vanilla ile birebir -- CodeWalker
# XML okuyucusu sirayi onemsiyor.
KALEM = """  <Item>
     <EmitterRule>%(em)s</EmitterRule>
     <ParticleRule>%(pr)s</ParticleRule>
     <Unknown10 value="%(gecikme)g" />
     <Unknown14 value="%(omur)g" />
     <MoveSpeedScale value="1" />
     <MoveSpeedScaleModifier value="1" />
     <ParticleScale value="%(olcek)g" />
     <ParticleScaleModifier value="1" />
     <Colour1 value="0xFFFFFFFF" />
     <Colour2 value="0xFFFFFFFF" />
     <UnknownData>
      <EventEmitterFlags>
       <Item>LOD</Item>
      </EventEmitterFlags>
      <Unknown10 />
     </UnknownData>
    </Item>
"""


def tek_bul(s, sozluk):
    """Sozlukteki TEK ogenin (ad, govde) ciftini verir."""
    o = ogeler(s, sozluk)
    return o[0] if o else (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ad", required=True)
    ap.add_argument("--klasor", required=True,
                    help="katman kaynaklarinin bulundugu dizin")
    ap.add_argument("--katman", action="append", required=True,
                    metavar="EFEKT[:gecikme[:olcek[:omur]]]")
    ap.add_argument("--derleme", action="store_true")
    a = ap.parse_args()

    kalemler = []
    biriken = {d: [] for d in SOZLUKLER}
    gorulen = {d: set() for d in SOZLUKLER}
    sablon = None

    for tarif in a.katman:
        parca = tarif.split(":")
        efekt = parca[0]
        gecikme = float(parca[1]) if len(parca) > 1 and parca[1] else 0.0
        olcek = float(parca[2]) if len(parca) > 2 and parca[2] else 1.0
        omur = float(parca[3]) if len(parca) > 3 and parca[3] else 1.0

        yol = os.path.join(a.klasor, efekt + ".ypt.xml")
        if not os.path.exists(yol):
            raise SystemExit("katman kaynagi yok: %s" % yol)
        s = io.open(yol, encoding="utf-8", errors="replace").read()
        if sablon is None:
            sablon = s

        emad, _ = tek_bul(s, "EmitterRuleDictionary")
        prad, _ = tek_bul(s, "ParticleRuleDictionary")
        if not emad or not prad:
            raise SystemExit("%s: emitter/particle bulunamadi" % efekt)

        for d in SOZLUKLER:
            for ad, metin in ogeler(s, d):
                # ⛔ Ayni ad iki kez yazilmaz. Iki katman ayni sprite'i
                #    kullaniyorsa doku bir kez girer.
                if ad in gorulen[d]:
                    continue
                gorulen[d].add(ad)
                biriken[d].append((ad, metin))

        kalemler.append(KALEM % {"em": emad, "pr": prad, "gecikme": gecikme,
                                 "olcek": olcek, "omur": omur})

    # --- efekt kuralini sablondan al, EventEmitters'i degistir ---
    i = sablon.find("<EffectRuleDictionary>")
    j = sablon.find("</EffectRuleDictionary>")
    kural = sablon[i + len("<EffectRuleDictionary>"):j]
    kural = re.sub(r"(\n   <Name>)[^<]+(</Name>)", r"\g<1>%s\g<2>" % a.ad,
                   kural, count=1)
    ei = kural.find("<EventEmitters>")
    ej = kural.find("</EventEmitters>")
    if ei < 0:
        raise SystemExit("sablonda <EventEmitters> yok")
    kural = (kural[:ei] + "<EventEmitters>\n" + "".join(kalemler)
             + "   </EventEmitters>" + kural[ej + len("</EventEmitters>"):])

    biriken["TextureDictionary"].sort(key=lambda t: jenkins(t[0]))

    p = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n",
         "<ParticleEffectsList>\n", " <Name>%s</Name>\n" % a.ad,
         " <EffectRuleDictionary>", kural, "</EffectRuleDictionary>\n"]
    for d in ("EmitterRuleDictionary", "ParticleRuleDictionary"):
        p.append(" <%s>\n" % d)
        p += [m for _, m in biriken[d]]
        p.append(" </%s>\n" % d)
    p.append(" <DrawableDictionary />\n")
    p.append(" <TextureDictionary>\n")
    p += [m for _, m in biriken["TextureDictionary"]]
    p.append(" </TextureDictionary>\n")
    p.append("</ParticleEffectsList>\n")
    metin = "".join(p)

    ET.fromstring(metin)
    xml = os.path.join(a.klasor, a.ad + ".ypt.xml")
    io.open(xml, "w", encoding="utf-8").write(metin)
    print("%s: %d katman | %d emitter, %d particle, %d doku"
          % (a.ad, len(kalemler), len(biriken["EmitterRuleDictionary"]),
             len(biriken["ParticleRuleDictionary"]),
             len(biriken["TextureDictionary"])))

    eksik = [ad + ".dds" for ad, _ in biriken["TextureDictionary"]
             if not os.path.exists(os.path.join(a.klasor, ad + ".dds"))]
    if eksik:
        print("⛔ EKSIK .dds: %s" % ", ".join(eksik[:6]))
        return 1
    if a.derleme:
        return 0
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", os.path.join(BETIK, "ypt_xml_to_bin.ps1"),
                    "-Xml", xml], check=False)
    ypt = os.path.join(a.klasor, a.ad + ".ypt")
    print("  -> %s (%d bayt)" % (os.path.basename(ypt),
                                 os.path.getsize(ypt)) if os.path.exists(ypt)
          else "  ⛔ derlenmedi")
    return 0 if os.path.exists(ypt) else 1


if __name__ == "__main__":
    raise SystemExit(main())
