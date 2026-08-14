#!/usr/bin/env python3
"""fix_ycd_xml.py — Sollumz'un urettigi .ycd.xml'e eksik <Hash> alanlarini ekler.

NEDEN GEREKLI (olculdu)
=======================
Sollumz clip ve animation ogelerine `<Name>` yazar ama **`<Hash>` YAZMAZ**.
CodeWalker'in ClipMap/AnimMap'i HASH ile anahtarlanir; hash yoksa hepsi 0
olur ve ayni anahtara yazilan kayitlar birbirini EZER.

Somut olcum: 5 klipli bir sozluk export edildi ->
  export XML   : 5 klip, 5 animasyon   (veri dogru, 765 KB)
  binary .ycd  : **1 klip, 1 animasyon** (sadece SONUNCUSU kaldi)

Tek klipli sozluklerde sorun gorunmez — bu yuzden hata cok gec fark edilir.
Vanilla dosyalarda her iki oge de `<Hash>` tasir:
    <Item><Hash>mood_happy_2</Hash><Name>pack:/mood_happy_2.clip</Name>...
    <Item><Hash>hash_E641A4A0</Hash><Unknown10 .../>...

KULLANIM
    python fix_ycd_xml.py <dosya.ycd.xml> [-o cikti.xml]
    # sonra: powershell -File xml_to_ycd.ps1 -XmlPath <cikti.xml>
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET


def joaat(s):
    h = 0
    for c in s.lower():
        h = (h + ord(c)) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    h = (h + (h << 15)) & 0xFFFFFFFF
    return h


def clip_name(item):
    """<Name>pack:/xxx.clip</Name> -> xxx"""
    n = (item.findtext("Name") or "").strip()
    if n.startswith("pack:/"):
        n = n[6:]
    if n.endswith(".clip"):
        n = n[:-5]
    return n


def fix(path, out=None):
    tree = ET.parse(path)
    root = tree.getroot()
    clips = root.findall("./Clips/Item")
    anims = root.findall("./Animations/Item")

    added_c = added_a = 0
    names = []
    for it in clips:
        nm = clip_name(it)
        names.append(nm)
        if it.find("Hash") is None:
            h = ET.Element("Hash")
            h.text = nm if nm else "clip"
            it.insert(0, h)
            added_c += 1

    # Animasyon hash'i: klip adindan turet -> benzersiz ve tekrarlanabilir.
    anim_hashes = []
    for i, it in enumerate(anims):
        h = it.find("Hash")
        if h is None:
            base = names[i] if i < len(names) else f"anim_{i}"
            h = ET.Element("Hash")
            h.text = f"hash_{joaat('anim_' + base):08X}"
            it.insert(0, h)
            added_a += 1
        anim_hashes.append((h.text or "").strip())

    # KLIP -> ANIMASYON BAGI. Sollumz <AnimationHash> dugumunu HIC yazmaz;
    # bag kurulmazsa sozluk yuklenir, klip adiyla bulunur, ama hicbir animasyona
    # isaret etmedigi icin ped KIPIRDAMAZ ve hata da verilmez (olculdu).
    # Sollumz klipleri ve animasyonlari ayni sirada yazar -> i. klip = i. animasyon.
    added_link = 0
    for i, it in enumerate(clips):
        if i >= len(anim_hashes):
            break
        node = it.find("AnimationHash")
        if node is not None and (node.text or "").strip():
            continue
        if node is None:
            node = ET.Element("AnimationHash")
            # kanonik sira: ... Unknown30, AnimationHash, StartTime ...
            st = it.find("StartTime")
            it.insert(list(it).index(st) if st is not None else len(it), node)
        node.text = anim_hashes[i]
        added_link += 1

    dup_c = len(names) - len(set(names))
    dst = out or path
    tree.write(dst, encoding="UTF-8", xml_declaration=True)
    return {"clips": len(clips), "anims": len(anims),
            "hash_added_clips": added_c, "hash_added_anims": added_a,
            "anim_links_added": added_link,
            "duplicate_clip_names": dup_c, "out": dst}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xml")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    if not os.path.exists(a.xml):
        print(f"[!] yok: {a.xml}", file=sys.stderr)
        return 1
    r = fix(a.xml, a.out)
    print(f"[+] {r['clips']} klip / {r['anims']} animasyon")
    print(f"    klip <Hash> eklendi : {r['hash_added_clips']}")
    print(f"    anim <Hash> eklendi : {r['hash_added_anims']}")
    print(f"    klip->anim bagi     : {r['anim_links_added']}")
    if r["duplicate_clip_names"]:
        print(f"[!] {r['duplicate_clip_names']} TEKRAR EDEN klip adi var — "
              f"ayni hash'e duserler ve birbirini ezer.")
    print(f"[+] yazildi: {r['out']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
