#!/usr/bin/env python3
"""build_decals.py — GTA V decalType tablosunu indeksler (`decals.dat`).

NEDEN: `AddDecal(decalType, ...)` native'inin ilk argumani bir SAYIDIR ve o
sayinin hangi gorsele denk geldigi hicbir yerde derli toplu yazili degil.
FiveM belgesindeki enum EKSIKTIR (yalnizca bir kismi). Gercek kaynak oyunun
kendi `common.rpf\\data\\effects\\decals.dat` dosyasidir.

DOSYA BICIMI: bosluk hizalanmis sabit sutunlu metin, '#' yorum.
  ID  DIFFUSE  NORMAL  SPECULAR  ROW COL IDA IDB  TIME MULT FALLOFF INTNSTY
  FRESNEL STEEP SCALE VALUE LENGTH  TEX_WRAP USE_ANISO WASHABLE UNDERWATER ROTATE

AYNI ID BIRDEN COK SATIRDA olabilir: motor o ID icin rastgele varyant secer
(orn. 1010 = kan sicramasi, birden cok doku bolgesi). O yuzden ID basina
satir sayisi = varyant sayisi.

Kullanim:
  python build_decals.py --src <decals.dat yolu>
  (yol verilmezse %TEMP%\\decals.dat aranir)
"""
from __future__ import annotations

import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


def main() -> int:
    ap = argparse.ArgumentParser(description="decals.dat -> tablo")
    ap.add_argument("--src", default=os.path.join(os.environ.get("TEMP", "."), "decals.dat"))
    ap.add_argument("--out", default=os.path.join(DATA, "decal_types.tsv"))
    args = ap.parse_args()

    if not os.path.exists(args.src):
        sys.exit(
            f"HATA: {args.src} yok.\n"
            "  CodeWalker ile cikar: common.rpf\\data\\effects\\decals.dat")

    # Son gorulen '# BASLIK' yorumu o satirlarin KATEGORISIDIR; dosyada
    # BLOOD SPLATTERS / WEAPON IMPACTS gibi bloklar halinde gruplanmis.
    kategori = ""
    kayit: list[dict] = []
    with open(args.src, encoding="utf-8", errors="replace") as fh:
        for satir in fh:
            s = satir.rstrip("\n")
            ham = s.strip()
            if not ham:
                continue
            if ham.startswith("#"):
                etiket = ham.lstrip("#").strip()
                # 'ID  DIFFUSE MAP ...' gibi sutun basliklarini kategori sanma
                if (etiket and not etiket.startswith("ID")
                        and "---" not in etiket and len(etiket) < 60
                        and etiket.upper() == etiket):
                    kategori = etiket
                continue
            if ham.startswith("DECAL_DEF"):
                continue
            parca = ham.split()
            if not parca or not parca[0].isdigit():
                continue
            kayit.append({
                "id": int(parca[0]),
                "kategori": kategori,
                "diffuse": parca[1] if len(parca) > 1 else "",
                "normal": parca[2] if len(parca) > 2 else "",
                "specular": parca[3] if len(parca) > 3 else "",
                # son bes sutun: TEX_WRAP USE_ANISO WASHABLE UNDERWATER ROTATE
                "washable": parca[-3] if len(parca) >= 3 else "",
                "underwater": parca[-2] if len(parca) >= 2 else "",
                "rotate": parca[-1] if parca else "",
            })

    if not kayit:
        sys.exit("HATA: hicbir decal satiri ayristirilamadi.")

    # ID basina topla: varyant sayisi + benzersiz doku adlari
    grup: dict[int, dict] = {}
    for r in kayit:
        g = grup.setdefault(r["id"], {
            "id": r["id"], "kategori": r["kategori"],
            "varyant": 0, "dokular": [], "washable": r["washable"],
            "underwater": r["underwater"],
        })
        g["varyant"] += 1
        if r["diffuse"] and r["diffuse"] not in g["dokular"]:
            g["dokular"].append(r["diffuse"])
        if not g["kategori"] and r["kategori"]:
            g["kategori"] = r["kategori"]

    os.makedirs(DATA, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["id", "kategori", "varyant", "washable", "underwater", "dokular"])
        for i in sorted(grup):
            g = grup[i]
            w.writerow([g["id"], g["kategori"], g["varyant"], g["washable"],
                        g["underwater"], ";".join(g["dokular"][:6])])

    kat = collections.Counter(g["kategori"] for g in grup.values())
    print(f"[+] {args.out}")
    print(f"[+] {len(grup)} benzersiz decalType / {len(kayit)} satir (varyant dahil)")
    print(f"[+] ID araligi: {min(grup)} - {max(grup)}")
    print("\nkategoriler:")
    for k, v in kat.most_common(20):
        print(f"   {k or '(kategorisiz)':<34} {v} tip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
