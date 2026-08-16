#!/usr/bin/env python3
"""yol.py — dis arac ve klasor yollarinin TEK KAYNAGI.

NEDEN VAR
=========
Yollar betiklere dagilmisti: `CodeWalker.Core.dll` icin **29**, GTA klasoru
icin **23** ayri sabit tahmin vardi. Sonuclari:

* Kullanici CodeWalker'i baska yere kurunca 20+ dosya elle duzeltiliyordu.
* `data/config.json` zaten vardi ama betikler **okumuyordu**; ytd_ara.ps1
  okumaya calisirken `gtaFolder` yerine `gta` yazmisti -> PowerShell olmayan
  property'de hata vermez, `$null` doner: yapilandirma **sessizce** yok
  sayilip sabit tahminlere dusuyordu.
* Repoya kisisel yol sizmasi riski (bir kez temizlendi, geri geldi).

Burada tek kutuk var: `data/config.json`. `data/` .gitignore'da oldugu icin
kisisel yol **asla repoya girmez**.

BILINEN YOLLAR **KAPALI LISTE DEGILDIR**
========================================
`KAYITLI` sik kullanilanlari tanimlar (arama sirasi + dogrulama kurali ile).
Ama istedigin adi kaydedebilirsin:

    assetdb.py yol gizmo "C:\\Araclar\\Gizmo.exe"
    assetdb.py yol gizmo            -> nerede oldugunu soyler

Boylece yeni bir arac icin kod degistirmek gerekmez.

KULLANIM
========
    assetdb.py yol                       # hepsini goster (var/yok)
    assetdb.py yol codewalker            # tek birini goster
    assetdb.py yol codewalker "C:\\...\\CodeWalker.Core.dll"   # ayarla
    assetdb.py yol codewalker --sil      # kaydi kaldir

    import yol
    yol.coz("codewalker")   # -> (yol, kaynak) ya da (None, sebep)
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
CONFIG = os.path.join(DATA, "config.json")


def _kul(*p):
    return os.path.join(os.path.expanduser("~"), *p)


# ad -> (config anahtari, aciklama, tip, aday yollar)
# tip: "file" | "folder".  Adaylar SIRAYLA denenir; ilk var olan kazanir.
KAYITLI = {
    "codewalker": (
        "codeWalker", "CodeWalker.Core.dll - decodes .ydr/.yft/.ycd", "file",
        [_kul("Desktop", "FiveM", "CodeWalker30_dev46", "CodeWalker.Core.dll"),
         _kul("Desktop", "CodeWalker", "CodeWalker.Core.dll"),
         _kul("Desktop", "Programlar", "CodeWalker", "CodeWalker.Core.dll")],
    ),
    "gta": (
        "gtaFolder", "GTA V install folder - source of every data layer", "folder",
        [r"C:\Program Files\Rockstar Games\Grand Theft Auto V",
         r"C:\Program Files\Epic Games\GTAV",
         r"C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V",
         r"C:\SteamLibrary\steamapps\common\Grand Theft Auto V",
         r"D:\SteamLibrary\steamapps\common\Grand Theft Auto V",
         r"E:\Grand Theft Auto V"],
    ),
    "server": (
        "resources", "your FiveM server resources folder - framework index",
        "folder", [],
    ),
    "blender": (
        "blender", "blender.exe - to run scripts headless", "file",
        [r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
         r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"],
    ),
}

# Kayitli olmayan adlar da saklanir; carpismasin diye bu on ek ile.
SERBEST_ONEK = "yol_"

# Eski Turkce adlar takma ad olarak kalir: eski komut satirlari kirilmasin.
TAKMA = {"sunucu": "server", "yol": "path"}


def config_oku():
    if os.path.exists(CONFIG):
        try:
            return json.load(open(CONFIG, encoding="utf-8-sig"))
        except (ValueError, OSError):
            return {}
    return {}


def config_yaz(d):
    os.makedirs(DATA, exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=2, ensure_ascii=False)


def _anahtar(ad):
    ad = TAKMA.get(ad.lower(), ad.lower())
    k = KAYITLI.get(ad)
    return k[0] if k else SERBEST_ONEK + ad.lower()


def _var_mi(p, tip):
    if not p:
        return False
    return os.path.isdir(p) if tip == "folder" else os.path.isfile(p)


def coz(ad):
    """(yol, kaynak) dondurur. Bulunamazsa (None, sebep).

    Sira: config.json -> bilinen adaylar. Config'de YAZILI ama diskte YOK
    ise bu ayrica soylenir -- "ayarladim ama calismiyor" en sik durum.
    """
    ad = TAKMA.get(ad.lower(), ad.lower())
    kayit = KAYITLI.get(ad)
    tip = kayit[2] if kayit else "file"
    cfg = config_oku()
    yazili = cfg.get(_anahtar(ad))
    if yazili:
        if _var_mi(yazili, tip):
            return yazili, "config.json"
        return None, "set in config.json but MISSING on disk: %s" % yazili
    for aday in (kayit[3] if kayit else []):
        if _var_mi(aday, tip):
            return aday, "found automatically"
    return None, "not set, and not found automatically"


def ayarla(ad, deger):
    """Diskte olmayan yolu KABUL ETMEZ: sessizce bozuk kayit birakmaktansa
    hemen soyler."""
    ad = TAKMA.get(ad.lower(), ad.lower())
    kayit = KAYITLI.get(ad)
    tip = kayit[2] if kayit else None
    deger = os.path.abspath(os.path.expanduser(deger))
    if tip is None:
        tip = "folder" if os.path.isdir(deger) else "file"
    if not _var_mi(deger, tip):
        raise ValueError("no such %s: %s" % (tip, deger))
    cfg = config_oku()
    cfg[_anahtar(ad)] = deger
    config_yaz(cfg)
    return deger


def sil(ad):
    cfg = config_oku()
    k = _anahtar(ad.lower())
    if k not in cfg:
        return False
    del cfg[k]
    config_yaz(cfg)
    return True


def hepsi():
    """[(ad, yol, kaynak, aciklama)] — kayitlilar + serbest kaydedilenler."""
    out = []
    for ad, k in KAYITLI.items():
        p, kaynak = coz(ad)
        out.append((ad, p, kaynak, k[1]))
    cfg = config_oku()
    for k in sorted(cfg):
        if k.startswith(SERBEST_ONEK):
            ad = k[len(SERBEST_ONEK):]
            p, kaynak = coz(ad)
            out.append((ad, p, kaynak, "(user-defined)"))
    return out


# --------------------------------------------------------------------- CLI

def calistir(args):
    ad = getattr(args, "ad", None)
    deger = getattr(args, "deger", None)

    if ad and getattr(args, "sil", False):
        print("removed: %s" % ad if sil(ad) else "not stored anyway: %s" % ad)
        return 0

    if ad and deger:
        try:
            p = ayarla(ad, deger)
        except ValueError as e:
            print("ERROR: %s" % e, file=sys.stderr)
            return 2
        print("%-12s -> %s" % (ad, p))
        print("  saved to: %s" % CONFIG)
        return 0

    if ad:
        p, kaynak = coz(ad)
        if p:
            print("%s\n  %s  (%s)" % (ad, p, kaynak))
            return 0
        print("%s\n  MISSING - %s" % (ad, kaynak), file=sys.stderr)
        k = KAYITLI.get(ad.lower())
        if k and k[3]:
            print("  looked in:", file=sys.stderr)
            for a in k[3]:
                print("    %s" % a, file=sys.stderr)
        print('\n  set it with: assetdb.py path %s "<path>"' % ad, file=sys.stderr)
        return 1

    eksik = 0
    print("registry: %s\n" % CONFIG)
    for ad, p, kaynak, acik in hepsi():
        if p:
            print("  [+] %-11s %s" % (ad, p))
            print("      %-11s %s | %s" % ("", kaynak, acik))
        else:
            eksik += 1
            print("  [!] %-11s MISSING - %s" % (ad, kaynak))
            print("      %-11s %s" % ("", acik))
    print('\n  set:  assetdb.py path <name> "<path>"   |   drop: --remove')
    print("  any name works too: assetdb.py path gizmo \"C:\\...\\Gizmo.exe\"")
    return 1 if eksik else 0


if __name__ == "__main__":
    class A:
        ad = sys.argv[1] if len(sys.argv) > 1 else None
        deger = sys.argv[2] if len(sys.argv) > 2 else None
        sil = "--sil" in sys.argv
    sys.exit(calistir(A))
