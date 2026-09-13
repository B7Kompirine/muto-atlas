#!/usr/bin/env python3
"""verify_tables.py — shaders.tsv ve collision_materials.tsv'yi
oyunun KENDI dosyalarindan uretilen kullanim verisiyle capraz dogrular.

NEDEN: iki tablo da Sollumz kaynagindan cikarildi, yani TEK KAYNAK. Bu betik
ikinci kaynagi (build_usage.ps1 ciktisi) karsisina koyar. Uc soru:

  1) Kullanimda gorunup TABLODA OLMAYAN shader var mi?  -> tablo eksik
  2) Kullanilan collision materyal indeksleri tablo araliginda mi?
  3) DECAL shader'lari hangi RenderBucket ile kullaniliyor?
     (Sollumz varsayilani Opaque(0); dogrusunu ancak olcum soyler)

Kullanim: python verify_tables.py
"""
from __future__ import annotations

import collections
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")

BUCKET = {0: "Opaque", 1: "Alpha", 2: "Decal", 3: "Cutout",
          4: "NoSplash", 5: "NoWater", 6: "Water", 7: "DisplAlpha"}


def oku(ad):
    yol = os.path.join(DATA, ad)
    if not os.path.exists(yol):
        sys.exit(f"HATA: {yol} yok.\n  Uret: build_usage.ps1 / build_shaders.py")
    # utf-8-sig: eski surumler BOM yazmisti
    with open(yol, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def main():
    tanim = oku("shaders.tsv")
    kul = oku("shader_usage.tsv")
    mat_tanim = oku("collision_materials.tsv")
    mat_kul = oku("collision_usage.tsv")

    tanim_ad = {r["name"] for r in tanim}
    kul_ad = {r["shader"] for r in kul}

    print("=" * 68)
    print("DENETIM 1 — shader tablosu eksik mi?")
    print("=" * 68)
    print(f"  tanimli (Sollumz Shaders.xml) : {len(tanim_ad)}")
    print(f"  kullanimda gorulen (vanilla)  : {len(kul_ad)}")
    eksik = sorted(kul_ad - tanim_ad)
    print(f"  TABLODA OLMAYAN ama kullanilan: {len(eksik)}")
    for e in eksik[:20]:
        print(f"      {e}")
    if len(eksik) > 20:
        print(f"      ... {len(eksik)-20} tane daha")
    kullanilmayan = len(tanim_ad - kul_ad)
    print(f"  tabloda olup ornekte gorulmeyen: {kullanilmayan}"
          "   (ornek sinirli, kusur degil)")

    print()
    print("=" * 68)
    print("DENETIM 2 — collision materyal indeksleri aralikta mi?")
    print("=" * 68)
    ust = len(mat_tanim) - 1
    idx = [int(r["matIndex"]) for r in mat_kul]
    tasan = sorted(m for m in idx if m > ust)
    print(f"  tablo araligi : 0-{ust} ({len(mat_tanim)} materyal)")
    print(f"  kullanilan    : {len(idx)} farkli indeks, min={min(idx)} max={max(idx)}")
    print(f"  ARALIK DISI   : {len(tasan)}  {tasan[:12]}")

    ad = {int(r["index"]): r["name"] for r in mat_tanim}
    sayi = {int(r["matIndex"]): int(r["count"]) for r in mat_kul}
    print("\n  en cok kullanilan 10 materyal:")
    for i, n in sorted(sayi.items(), key=lambda x: -x[1])[:10]:
        print(f"     {i:>4} {ad.get(i,'(TABLODA YOK)'):<28} {n}")

    # proceduralId capraz kontrolu
    proc_gorulen = set()
    for r in mat_kul:
        for p in (r.get("proceduralIds") or "").split(","):
            if p.strip().isdigit():
                proc_gorulen.add(int(p))
    if proc_gorulen:
        proc_yol = os.path.join(DATA, "procedural.tsv")
        if os.path.exists(proc_yol):
            with open(proc_yol, encoding="utf-8-sig") as fh:
                pt = list(csv.DictReader(fh, delimiter="\t"))
            ustp = len(pt) - 1
            disi = sorted(p for p in proc_gorulen if p > ustp)
            print(f"\n  proceduralId: {len(proc_gorulen)} farkli deger kullanilmis, "
                  f"tablo 0-{ustp}, ARALIK DISI: {len(disi)} {disi[:10]}")

    print()
    print("=" * 68)
    print("DENETIM 3 — DECAL shader'lari hangi render bucket ile kullaniliyor?")
    print("=" * 68)
    dec = [r for r in kul if "decal" in r["shader"].lower()]
    if not dec:
        print("  ornekte decal shader'i gorulmedi.")
    else:
        toplam = collections.Counter()
        for r in dec:
            for parca in r["buckets"].split(";"):
                if ":" not in parca:
                    continue
                k, v = parca.split(":")
                toplam[int(k)] += int(v)
        genel = sum(toplam.values())
        print(f"  {len(dec)} farkli decal shader'i, {genel} kullanim:")
        for k, v in sorted(toplam.items(), key=lambda x: -x[1]):
            print(f"     bucket {k} {BUCKET.get(k,'?'):<12} {v:>7}  (%{100*v/genel:.1f})")
        print("\n  en cok kullanilan decal shader'lari:")
        for r in sorted(dec, key=lambda r: -int(r["total"]))[:8]:
            print(f"     {r['shader']:<34} {r['total']:>6}  buckets={r['buckets']}")

    print()
    print("=" * 68)
    print("GENEL render bucket dagilimi")
    print("=" * 68)
    g = collections.Counter()
    for r in kul:
        for parca in r["buckets"].split(";"):
            if ":" in parca:
                k, v = parca.split(":")
                g[int(k)] += int(v)
    t = sum(g.values())
    for k, v in sorted(g.items()):
        print(f"  {k} {BUCKET.get(k,'?'):<12} {v:>8}  (%{100*v/t:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
