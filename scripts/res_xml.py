#!/usr/bin/env python3
"""res_xml.py — binary RSC7 kaynagini gecici olarak XML'e dokup okutur.

NEDEN AYRI MODUL: doctor, diff ve light ucu de ayni sey ile baslar -- elde
binary bir .ycd/.ytyp/.yft var, incelenecek olan ise onun XML karsiligi.
Ucune ayri kopya yazmak, birinde duzelen bir hatanin digerlerinde kalmasi
demekti.

EN ONEMLI SOZLESME: donusturucu calistirilamazsa bu bir HATA olarak dondurulur,
sessizce "icerik yok" DEGIL. Cagiran taraf farki gormek zorunda; yoksa
"CodeWalker kurulu degil" durumu "dosya bos" diye raporlanir.
    "Aracin gostermemesi, o seyin yok oldugu anlamina gelmez."
"""
from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
RES_TO_XML = os.path.join(HERE, "res_to_xml.ps1")

# res_to_xml.ps1'in GERCEKTEN cevirebildigi uzantilar (o dosyadaki switch ile
# birebir). Burasi genis tutulursa cevrilemeyen her dosya "XML uretmedi" diye
# raporlanir ve sebep kaybolur -- olculdu: `.ymap` listede oldugu icin 204
# dosya boyle atlandi, oysa donusturucu `.ymap` KABUL ETMIYOR.
# Liste res_to_xml.ps1 ile senkron kalmali; oradaki `case` satirlari otoritedir.
RES_EXT = {".ycd", ".yed", ".yft", ".ydd", ".ydr", ".ybn", ".ytyp", ".ypt"}

# Bilinen ama bu hatta cevrilemeyen kaynaklar: sebebi ACIKCA soylenir,
# "XML uretmedi" gibi belirsiz bir mesajla gizlenmez.
CEVRILEMEYEN = {
    ".ymap": "res_to_xml.ps1 .ymap cevirmiyor (CodeWalker GUI ya da "
             "build_ymap_lod.ps1 kullan)",
}

ZAMAN_ASIMI = 180


def binary_to_xml(yol, tmp):
    """Binary kaynagi tmp klasorune XML olarak doker. (xml_yolu, hata) doner."""
    if not os.path.exists(RES_TO_XML):
        return None, f"res_to_xml.ps1 yok: {RES_TO_XML}"
    kabuk = shutil.which("powershell") or shutil.which("pwsh")
    if kabuk is None:
        return None, "powershell bulunamadi"
    try:
        p = subprocess.run(
            [kabuk, "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", RES_TO_XML, "-Path", yol, "-OutDir", tmp],
            capture_output=True, text=True, timeout=ZAMAN_ASIMI)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"res_to_xml.ps1 calistirilamadi: {exc}"
    if p.returncode != 0:
        hata = (p.stderr or p.stdout or "").strip().splitlines()
        return None, f"res_to_xml.ps1 hata: {hata[-1] if hata else p.returncode}"
    uretilen = [os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith(".xml")]
    if not uretilen:
        return None, "res_to_xml.ps1 XML uretmedi"
    return max(uretilen, key=os.path.getmtime), None


@contextlib.contextmanager
def acik_xml(yol):
    """`with acik_xml(p) as (xml_yolu, hata):` — XML ise dogrudan, binary ise
    gecici donusumle verir ve cikista temizler. hata doluysa xml_yolu None'dur."""
    if not os.path.exists(yol):
        yield None, "dosya yok"
        return
    if yol.lower().endswith(".xml"):
        yield yol, None
        return
    uz = os.path.splitext(yol)[1].lower()
    if uz not in RES_EXT:
        yield None, CEVRILEMEYEN.get(uz, f"desteklenmeyen uzanti ({uz})")
        return
    tmp = tempfile.mkdtemp(prefix="mutoxml_")
    try:
        yield binary_to_xml(yol, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _kabuk():
    return shutil.which("powershell") or shutil.which("pwsh")


def _toplu_cevir(yollar, tmp):
    """Tek PowerShell cagrisiyla birden cok dosyayi cevirir. {kaynak: xml} doner.

    NEDEN: dosya basina bir PowerShell + CodeWalker.Core yuklemesi ~0.6 sn.
    957 dosyalik bir stream klasoru icin bu 10 dakika demekti; toplu cagriyla
    tek yukleme yeter. 10 dakika suren bir kapi kullanilmaz, yani hiz burada
    dogruluk kadar onemli.
    """
    kabuk = _kabuk()
    if kabuk is None:
        return {}, "powershell bulunamadi"
    dizi = ",".join("'" + y.replace("'", "''") + "'" for y in yollar)
    komut = (f"& '{RES_TO_XML.replace(chr(39), chr(39) * 2)}' "
             f"-Path @({dizi}) -OutDir '{tmp.replace(chr(39), chr(39) * 2)}'")
    try:
        p = subprocess.run([kabuk, "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-Command", komut],
                           capture_output=True, text=True,
                           timeout=ZAMAN_ASIMI * 4)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {}, f"toplu donusum calistirilamadi: {exc}"
    if p.returncode != 0:
        satir = (p.stderr or p.stdout or "").strip().splitlines()
        return {}, f"toplu donusum hatasi: {satir[-1] if satir else p.returncode}"

    uretilen = {f: os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith(".xml")}
    esleme = {}
    for y in yollar:
        ad = os.path.basename(y) + ".xml"
        if ad in uretilen:
            esleme[y] = uretilen[ad]
    return esleme, None


def _benzersiz_gruplar(yollar, azami=60):
    """Ayni dosya adini tasiyan iki kaynak AYNI gruba konmaz.

    Cikti dosya adiyla eslendigi icin ayni ada sahip iki girdi ust uste yazar
    ve biri sessizce digerinin XML'ini alir -- ped bilesenlerinde (head_000_r
    her ped'de ayni ad) bu gercek bir tuzaktir.
    """
    grup, adlar = [], set()
    for y in yollar:
        ad = os.path.basename(y).lower()
        if ad in adlar or len(grup) >= azami:
            yield grup
            grup, adlar = [], set()
        grup.append(y)
        adlar.add(ad)
    if grup:
        yield grup


def toplu_kok_oku(yollar):
    """(yol, kok, hata) uretir. Binary'ler toplu cevrilir, XML'ler dogrudan."""
    binary = []
    for y in yollar:
        if not os.path.exists(y):
            yield y, None, "dosya yok"
        elif y.lower().endswith(".xml"):
            yield (y,) + _ayristir(y)
        elif os.path.splitext(y)[1].lower() in RES_EXT:
            binary.append(y)
        else:
            uz = os.path.splitext(y)[1].lower()
            yield y, None, CEVRILEMEYEN.get(uz, f"desteklenmeyen uzanti ({uz})")

    for grup in _benzersiz_gruplar(binary):
        tmp = tempfile.mkdtemp(prefix="mutoxml_")
        try:
            esleme, hata = _toplu_cevir(grup, tmp)
            for y in grup:
                if hata:
                    yield y, None, hata
                elif y not in esleme:
                    yield y, None, "res_to_xml.ps1 bu dosya icin XML uretmedi"
                else:
                    yield (y,) + _ayristir(esleme[y])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def _ayristir(xml_yolu):
    try:
        return ET.parse(xml_yolu).getroot(), None
    except ET.ParseError as exc:
        return None, f"XML ayristirilamadi: {exc}"
    except OSError as exc:
        return None, f"okunamadi: {exc}"


def kok_oku(yol):
    """(ElementTree kok, hata). Ayrisma hatasi da HATA olarak doner."""
    with acik_xml(yol) as (xml_yolu, hata):
        if hata:
            return None, hata
        try:
            return ET.parse(xml_yolu).getroot(), None
        except ET.ParseError as exc:
            return None, f"XML ayristirilamadi: {exc}"
        except OSError as exc:
            return None, f"okunamadi: {exc}"
