#!/usr/bin/env python3
"""light_edit.py — .ydr/.yft icindeki isiklari GERI YAZAR.

NEDEN VAR
=========
Okumak yetmiyor. Bir isigi duzeltmek icin tek yol CodeWalker GUI'sinde elle
alan alan girmekti; editorde ayarlayip dosyaya donmenin yolu yoktu.

HAT
===
    binary  --res_to_xml-->  XML  --(burasi)-->  XML  --xml_to_res-->  binary

Tur OLCULDU: prop_worklight_01a.yft uzerinde Intensity 2->8 ve
ConeOuterAngle 60->35 yazildi, geri okundu, birebir cikti. Dosya BOYUTU
degisir (RSC7 zlib'dir) -- **boyut gecerlilik olcutu degildir, tek olcut
geri okumadir**, o yuzden her yazma sonrasi dogrulama zorunlu.

GUVENLIK
========
Orijinal her zaman `<ad>.yedek` olarak saklanir ve kopyalama sonrasi
boyut karsilastirilir: "komut hata vermedi" dagitim kaniti degildir.

KULLANIM
========
    python assetdb.py light prop.ydr --uygula duzenleme.json
    python assetdb.py light prop.ydr --set 0.Intensity=8 --set 0.ConeOuterAngle=35
    python assetdb.py light prop.ydr --sil 2
    python assetdb.py light prop.ydr --ekle          (secili ilk isigi kopyalar)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import light_sahne  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RES_TO_XML = os.path.join(HERE, "res_to_xml.ps1")
XML_TO_RES = os.path.join(HERE, "xml_to_res.ps1")

VEC3 = ["Position", "Direction", "Tangent", "Extent", "CullingPlaneNormal"]
RGB = ["Colour", "VolumeOuterColour"]
METIN = ["Type", "ProjectedTextureHash"]

# Vanilla alan SIRASI (prop_worklight_01a.yft'ten olculdu). Sira korunur ki
# uretilen dugum vanilla ile yapisal olarak ayni kalsin.
SIRA = [
    "Position", "Colour", "Flashiness", "Intensity", "Flags", "BoneId", "Type",
    "GroupId", "TimeFlags", "Falloff", "FalloffExponent", "CullingPlaneNormal",
    "CullingPlaneOffset", "Unknown45", "Unknown46", "VolumeIntensity",
    "VolumeSizeScale", "VolumeOuterColour", "LightHash", "VolumeOuterIntensity",
    "CoronaSize", "VolumeOuterExponent", "LightFadeDistance", "ShadowBlur",
    "ShadowFadeDistance", "SpecularFadeDistance", "VolumetricFadeDistance",
    "ShadowNearClip", "CoronaIntensity", "CoronaZBias", "Direction", "Tangent",
    "ConeInnerAngle", "ConeOuterAngle", "Extent", "ProjectedTextureHash",
]
TAMSAYI = set(light_sahne.ALANLAR_I)


def _ps(betik, *arg):
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", betik] + list(arg),
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _sayi(v):
    """CodeWalker float bicimi: tamsayi ise noktasiz yaz."""
    f = float(v)
    return str(int(f)) if f == int(f) and abs(f) < 1e15 else repr(f)


def _yaz_isik(it, l):
    """Bir <Item>'i JSON sozlugunden bastan kurar."""
    for c in list(it):
        it.remove(c)
    for ad in SIRA:
        if ad not in l:
            continue
        e = ET.SubElement(it, ad)
        v = l[ad]
        if ad in VEC3:
            for k, x in zip("xyz", v):
                e.set(k, _sayi(x))
        elif ad in RGB:
            for k, x in zip("rgb", v):
                e.set(k, str(int(x)))
        elif ad in METIN:
            if str(v).strip():
                e.text = str(v).strip()
        elif ad in TAMSAYI:
            e.set("value", str(int(v)))
        else:
            e.set("value", _sayi(v))


def _lights_dugumu(kok):
    L = kok.find("Lights")
    if L is None:
        L = kok.find(".//Lights")
    return L


def uygula(path, isiklar, yedekle=True):
    """isiklar: light_sahne.oku()'nun dondurdugu bicimde sozluk listesi."""
    path = os.path.abspath(path)
    ad = os.path.basename(path)
    with tempfile.TemporaryDirectory(prefix="isikedit_") as td:
        gecici = os.path.join(td, ad)
        shutil.copyfile(path, gecici)

        rc, cikti = _ps(RES_TO_XML, "-Path", gecici)
        xml = gecici + ".xml"
        if rc != 0 or not os.path.isfile(xml):
            # Cevirici calismadiysa bu HATA'dir, "isik yok" degil.
            raise RuntimeError("XML uretilemedi (%d): %s" % (rc, cikti.strip()[:300]))

        agac = ET.parse(xml)
        kok = agac.getroot()
        L = _lights_dugumu(kok)
        if L is None:
            if not isiklar:
                raise RuntimeError("dosyada <Lights> yok ve eklenecek isik da yok")
            # Fragment'te Lights KOKTEDIR, Drawable/Lights degil (olculdu).
            L = ET.SubElement(kok, "Lights")
        for c in list(L):
            L.remove(c)
        for l in isiklar:
            _yaz_isik(ET.SubElement(L, "Item"), l)
        agac.write(xml, encoding="utf-8", xml_declaration=True)

        rc, cikti = _ps(XML_TO_RES, "-XmlPath", xml)
        if rc != 0 or not os.path.isfile(gecici):
            raise RuntimeError("binary derlenemedi (%d): %s" % (rc, cikti.strip()[:300]))

        # DOGRULAMA: tek gecerli olcut geri okumadir (boyut degil).
        try:
            geri = light_sahne.oku(gecici)
        except (RuntimeError, ValueError) as e:
            raise RuntimeError("derlendi ama geri OKUNAMADI: %s" % e)
        if len(geri["isiklar"]) != len(isiklar):
            raise RuntimeError("geri okumada isik sayisi tutmadi: %d yazildi, %d okundu"
                               % (len(isiklar), len(geri["isiklar"])))

        if yedekle:
            yed = path + ".yedek"
            if not os.path.isfile(yed):
                shutil.copyfile(path, yed)
        shutil.copyfile(gecici, path)
        # "Komut hata vermedi" dagitim kaniti degildir.
        if os.path.getsize(path) != os.path.getsize(gecici):
            raise RuntimeError("kopyalama dogrulanamadi: boyut tutmadi")
        return geri


# --------------------------------------------------------------------- CLI

def _set_uygula(isiklar, kurallar):
    """'0.Intensity=8' ya da 'Intensity=8' (hepsi)."""
    for k in kurallar:
        if "=" not in k:
            raise ValueError("--set bicimi: [idx.]Alan=deger  (gelen: %s)" % k)
        sol, deg = k.split("=", 1)
        sol = sol.strip()
        if "." in sol:
            i_s, alan = sol.split(".", 1)
            hedef = [int(i_s)]
        else:
            alan, hedef = sol, list(range(len(isiklar)))
        alan = alan.strip()
        for i in hedef:
            if not 0 <= i < len(isiklar):
                raise ValueError("isik indeksi yok: %d (0..%d)" % (i, len(isiklar) - 1))
            l = isiklar[i]
            if alan not in l:
                raise ValueError("boyle bir alan yok: %s" % alan)
            eski = l[alan]
            if isinstance(eski, list):
                p = [float(x) for x in deg.replace(",", " ").split()]
                if len(p) != len(eski):
                    raise ValueError("%s %d deger ister" % (alan, len(eski)))
                l[alan] = [int(x) for x in p] if alan in RGB else p
            elif isinstance(eski, str):
                l[alan] = deg.strip()
            elif alan in TAMSAYI:
                l[alan] = int(float(deg))
            else:
                l[alan] = float(deg)
    return isiklar


def calistir(args):
    yol = getattr(args, "path", None)
    if not yol or not os.path.isfile(yol):
        print("ERROR: dosya yok: %s" % yol, file=sys.stderr)
        return 2
    try:
        sahne = light_sahne.oku(yol)
    except (RuntimeError, ValueError) as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 2
    isiklar = [{k: v for k, v in l.items() if not k.startswith("_")}
               for l in sahne["isiklar"]]

    kaynak = None
    if getattr(args, "uygula", None):
        with open(args.uygula, encoding="utf-8") as fh:
            d = json.load(fh)
        yeni = d.get("isiklar", d if isinstance(d, list) else None)
        if yeni is None:
            print("ERROR: JSON icinde 'isiklar' yok", file=sys.stderr)
            return 2
        isiklar = [{k: v for k, v in l.items() if not k.startswith("_")}
                   for l in yeni]
        kaynak = args.uygula

    if getattr(args, "ekle", False):
        yeni = json.loads(json.dumps(isiklar[0])) if isiklar else None
        if yeni is None:
            print("ERROR: kopyalanacak isik yok (dosyada hic isik yok).",
                  file=sys.stderr)
            return 2
        isiklar.append(yeni)

    for i in sorted(getattr(args, "sil", None) or [], reverse=True):
        if not 0 <= i < len(isiklar):
            print("ERROR: silinecek indeks yok: %d" % i, file=sys.stderr)
            return 2
        isiklar.pop(i)

    if getattr(args, "set", None):
        try:
            _set_uygula(isiklar, args.set)
        except ValueError as e:
            print("ERROR: %s" % e, file=sys.stderr)
            return 2

    if kaynak is None and not any([getattr(args, "set", None),
                                   getattr(args, "sil", None),
                                   getattr(args, "ekle", False)]):
        print("ERROR: ne yapilacagi belirtilmedi (--uygula / --set / --ekle / --sil)",
              file=sys.stderr)
        return 2

    onceki = len(sahne["isiklar"])
    try:
        geri = uygula(yol, isiklar)
    except RuntimeError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 2

    print("%s: %d isik -> %d isik yazildi ve GERI OKUNARAK dogrulandi"
          % (os.path.basename(yol), onceki, len(geri["isiklar"])))
    for l in geri["isiklar"]:
        print("  #%d %-8s yog=%-6s menzil=%-5s koni=%s/%s"
              % (l["_i"], l["Type"], _sayi(l["Intensity"]), _sayi(l["Falloff"]),
                 _sayi(l["ConeInnerAngle"]), _sayi(l["ConeOuterAngle"])))
    print("  yedek: %s.yedek" % os.path.basename(yol))
    print("\n  Asset degisti: sunucudan CIKIP yeniden baglan — restart yetmez.")
    return 0
