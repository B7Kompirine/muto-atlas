#!/usr/bin/env python3
"""build_shaders.py — GTA V shader tablosunu indeksler.

NEDEN: "bu yuzeye hangi shader?" sorusu tahminle cevaplanamaz. decal, cam,
emissive, terrain, kumas, arac -- hepsinin kendi shader'i ve kendi ZORUNLU
parametre seti var. Yanlis shader secmek sessiz hatadir: model yuklenir ama
yanlis cizilir (decal opak cikar, cam saydam olmaz, emissive yanmaz).

KAYNAK: Sollumz'un szio paketindeki Shaders.xml (249 shader). Bu dosya
CodeWalker'in shader tanimlarindan turetilmis; parametre adlari ve
varsayilanlari oyunun bekledigi degerlerdir.

Kullanim:
  python build_shaders.py [--src <Shaders.xml yolu>]

Sollumz kurulu degilse -src ile elle ver. Cikti: data/shaders.tsv
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")

# Sollumz surumleri farkli Blender surumlerine kuruluyor; en yenisini bul.
DESENLER = [
    os.path.expandvars(
        r"%APPDATA%\Blender Foundation\Blender\*\extensions\.user\*\sollumz"
        r"\lib\python*\site-packages\szio\gta5\Shaders.xml"),
    os.path.expandvars(
        r"%APPDATA%\Blender Foundation\Blender\*\extensions\*\sollumz"
        r"\lib\python*\site-packages\szio\gta5\Shaders.xml"),
]


def kaynak_bul() -> str | None:
    adaylar: list[str] = []
    for d in DESENLER:
        adaylar.extend(glob.glob(d))
    if not adaylar:
        return None
    # en yeni Blender surumu = yolda en buyuk surum numarasi; mtime yeterli
    return max(adaylar, key=os.path.getmtime)


def main() -> int:
    ap = argparse.ArgumentParser(description="GTA V shader tablosunu indeksle")
    ap.add_argument("--src", help="Shaders.xml yolu (otomatik bulunamazsa)")
    ap.add_argument("--out", default=os.path.join(DATA, "shaders.tsv"))
    args = ap.parse_args()

    src = args.src or kaynak_bul()
    if not src or not os.path.exists(src):
        sys.exit(
            "Shaders.xml bulunamadi. Sollumz kurulu degilse --src ile ver.\n"
            "  Tipik yol: %APPDATA%\\Blender Foundation\\Blender\\<surum>\\"
            "extensions\\.user\\user_default\\sollumz\\lib\\python*\\"
            "site-packages\\szio\\gta5\\Shaders.xml")

    print(f"kaynak: {src}")
    kok = ET.parse(src).getroot()

    os.makedirs(DATA, exist_ok=True)
    n = 0
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["name", "flags", "texCount", "valCount",
                    "textures", "params"])
        for it in kok:
            ad = (it.findtext("Name") or "").strip()
            if not ad:
                continue
            bayrak = (it.findtext("Flags") or "").strip()

            dokular, degerler = [], []
            ps = it.find("Parameters")
            if ps is not None:
                for p in ps:
                    pad = p.get("name", "")
                    tip = (p.get("type") or "").lower()
                    if tip == "texture":
                        uv = p.get("uv")
                        dokular.append(f"{pad}(uv{uv})" if uv is not None else pad)
                    else:
                        # skaler/vektor varsayilanlari: x,y,z,w
                        bilesen = [p.get(k) for k in ("x", "y", "z", "w")]
                        bilesen = [b for b in bilesen if b is not None]
                        alt = p.get("subtype")
                        etiket = f"{pad}={','.join(bilesen)}" if bilesen else pad
                        if alt:
                            etiket += f"[{alt}]"
                        degerler.append(etiket)

            w.writerow([ad, bayrak, len(dokular), len(degerler),
                        ";".join(dokular), ";".join(degerler)])
            n += 1

    print(f"[+] {args.out}  ({n} shader)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
