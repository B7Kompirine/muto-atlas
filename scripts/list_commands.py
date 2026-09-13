#!/usr/bin/env python3
"""list_commands.py -- plugin'in TUM komutlarini ve aciklamalarini listeler.

NEDEN: elle yazilan komut listesi eskir. Bu betik `commands/*.md`
frontmatter'ini OKUR, dolayisiyla liste her zaman gercek durumu gosterir.
Yeni komut eklendiginde burada hicbir sey degistirmek gerekmez.

Kullanim:
  python scripts/list_commands.py                 # gruplanmis tam liste
  python scripts/list_commands.py --duz           # tek satirlik ad + aciklama
  python scripts/list_commands.py <arama>         # ada/aciklamaya gore filtre
"""
from __future__ import annotations

import io
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOMUT_DIZINI = os.path.join(KOK, "commands")

# Komutlari isin turune gore grupla. Buradaki bir ad silinirse komut
# "Diger" grubuna duser -- liste yine eksiksiz kalir.
GRUPLAR = [
    ("Baslangic", ["help", "asset-setup", "paths"]),
    ("Veri sorgulama", ["asset", "where", "anim", "native", "native-lint"]),
    ("Dallar (kurallar + yapraklar)", ["map", "prop", "clothing", "particle", "look", "vehicle"]),
    ("Kurulum ve arac yollari", ["asset-build", "blender", "codewalker", "gta", "server"]),
]


def frontmatter(yol: str) -> dict:
    """--- ... --- blogundan basit key: value cikarir."""
    metin = io.open(yol, encoding="utf-8", errors="replace").read()
    if not metin.startswith("---"):
        return {}
    try:
        blok = metin.split("---", 2)[1]
    except IndexError:
        return {}
    out = {}
    for satir in blok.splitlines():
        m = re.match(r"^([a-zA-Z-]+):\s*(.*)$", satir)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def komutlari_oku() -> dict:
    if not os.path.isdir(KOMUT_DIZINI):
        sys.exit(f"commands/ bulunamadi: {KOMUT_DIZINI}")
    kayit = {}
    for f in sorted(os.listdir(KOMUT_DIZINI)):
        if not f.endswith(".md"):
            continue
        ad = f[:-3]
        fm = frontmatter(os.path.join(KOMUT_DIZINI, f))
        kayit[ad] = {
            "aciklama": fm.get("description", "(aciklama yok)"),
            "ipucu": fm.get("argument-hint", ""),
        }
    return kayit


def sarmala(metin: str, genislik: int, girinti: str) -> str:
    kelimeler, satirlar, cur = metin.split(), [], ""
    for k in kelimeler:
        if len(cur) + len(k) + 1 > genislik:
            satirlar.append(cur)
            cur = k
        else:
            cur = f"{cur} {k}".strip()
    if cur:
        satirlar.append(cur)
    return ("\n" + girinti).join(satirlar)


def main() -> int:
    args = [a for a in sys.argv[1:]]
    duz = "--duz" in args
    args = [a for a in args if not a.startswith("--")]
    arama = args[0].lower() if args else None

    kayit = komutlari_oku()
    if arama:
        kayit = {k: v for k, v in kayit.items()
                 if arama in k.lower() or arama in v["aciklama"].lower()}
        if not kayit:
            print(f"'{arama}' ile eslesen komut yok.")
            return 1

    if duz:
        for ad, v in sorted(kayit.items()):
            print(f"/muto-atlas:{ad}  --  {v['aciklama']}")
        return 0

    print("=" * 74)
    print(f"  muto-atlas -- {len(kayit)} komut")
    print("=" * 74)
    print("  Cagirma:  /muto-atlas:<ad>   ya da  /<ad>  (cakisma yoksa)")
    print()

    yerlesti = set()
    for baslik, adlar in GRUPLAR:
        # Bir komut birden fazla grupta gecebilir; ILK grupta gosterilir.
        uyeler = [a for a in adlar if a in kayit and a not in yerlesti]
        if not uyeler:
            continue
        print(f"-- {baslik} " + "-" * (70 - len(baslik)))
        for ad in uyeler:
            yerlesti.add(ad)
            v = kayit[ad]
            print(f"  /{ad}")
            print(f"      {sarmala(v['aciklama'], 62, '      ')}")
            if v["ipucu"]:
                print(f"      arguman: {v['ipucu']}")
        print()

    kalan = sorted(set(kayit) - yerlesti)
    if kalan:
        print("-- Diger " + "-" * 64)
        for ad in kalan:
            print(f"  /{ad}")
            print(f"      {sarmala(kayit[ad]['aciklama'], 62, '      ')}")
        print()

    print("-" * 74)
    print("  Veri katmani durumu :  python scripts/setup.py --plan")
    print("  Plugin butunlugu    :  python scripts/audit_plugin.py")
    print("  Tek satirlik liste  :  python scripts/list_commands.py --duz")
    print("  Arama               :  python scripts/list_commands.py <kelime>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
