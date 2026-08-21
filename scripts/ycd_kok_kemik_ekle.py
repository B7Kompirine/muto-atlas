# -*- coding: utf-8 -*-
"""ycd_kok_kemik_ekle.py -- .ycd.xml'e eksik KOK KEMIGI (BoneId 0) ekler.

NEDEN: Sollumz kok kemige kanal yazmiyor. Olculdu -- calisan des_crane.ycd
51 kemigin 51'ini de yaziyor (kok dahil, her track grubunun BASINDA);
bizim des_kopru.ycd 111 kemigin yalnizca 110'unu yaziyordu, kok yoktu.

Sinsi tarafi: 110/110/110 kendi icinde tutarli oldugu icin "dogrulandi"
gorunur. Olcut dosyanin kendi tutarliligi DEGIL, iskeletteki kemik sayisi
ve calisan referans dosyadir.

Kok kanal degerleri uydurulmaz; iki modelin kok rest pozu birebir ayni
olculdu: konum (0,0,0), donus (0.70710677,0,0,0.70710677), olcek (1,1,1).

BoneIds sirasi ile SequenceData sirasi BIREBIR eslesmek zorundadir.

Kullanim:  python ycd_kok_kemik_ekle.py <dosya.ycd.xml>
"""
import sys, shutil
import xml.etree.ElementTree as ET

KOK = 0
KOK_KANAL = {
    0: ('StaticVector3',    {'x': '0', 'y': '0', 'z': '0'}),
    1: ('StaticQuaternion', {'x': '0.70710677', 'y': '0', 'z': '0', 'w': '0.70710677'}),
    2: ('StaticVector3',    {'x': '1', 'y': '1', 'z': '1'}),
}
UNK0 = {0: '0', 1: '1', 2: '0'}     # crane'den olculdu


def kanal_ogesi(tip, deger):
    it = ET.Element('Item')
    ch = ET.SubElement(it, 'Channels')
    c = ET.SubElement(ch, 'Item')
    ET.SubElement(c, 'Type', {'value': tip})
    ET.SubElement(c, 'Value', deger)
    return it


def main(yol):
    t = ET.parse(yol)
    r = t.getroot()
    an = list(r.find('Animations'))[0]

    bi = an.find('BoneIds')
    sd = list(an.find('Sequences'))[0].find('SequenceData')
    girisler = list(bi)
    kanallar = list(sd)
    if len(girisler) != len(kanallar):
        print(f'[!] BASTAN BOZUK: BoneIds {len(girisler)} != SequenceData {len(kanallar)}')
        return 1

    mevcut = {(int(x.find('BoneId').get('value')), int(x.find('Track').get('value')))
              for x in girisler}
    if all((KOK, tr) in mevcut for tr in (0, 1, 2)):
        print('[=] kok kemik zaten var, dokunulmadi')
        return 0

    # Her track grubunun BASINA ekle (crane'de kok 0, 51, 102 indekslerinde).
    yeni_bi, yeni_sd = [], []
    onceki_track = None
    for g, k in zip(girisler, kanallar):
        tr = int(g.find('Track').get('value'))
        if tr != onceki_track:
            it = ET.Element('Item')
            ET.SubElement(it, 'BoneId', {'value': str(KOK)})
            ET.SubElement(it, 'Track', {'value': str(tr)})
            ET.SubElement(it, 'Unk0', {'value': UNK0[tr]})
            yeni_bi.append(it)
            tip, deg = KOK_KANAL[tr]
            yeni_sd.append(kanal_ogesi(tip, deg))
            onceki_track = tr
        yeni_bi.append(g)
        yeni_sd.append(k)

    for el, yeni in ((bi, yeni_bi), (sd, yeni_sd)):
        for c in list(el):
            el.remove(c)
        for c in yeni:
            el.append(c)

    # Unknown10: crane 1, bizde 0 idi.
    u = an.find('Unknown10')
    eski_u = u.get('value')
    u.set('value', '1')

    # Klip adi: crane 'pack:/des_crane_root.clip' -- sonek .clip
    ad = list(r.find('Clips'))[0].find('Name')
    eski_ad = ad.text
    if ad.text and not ad.text.endswith('.clip'):
        ad.text = ad.text + '.clip'

    # KENDI CIKTINI DOGRULA
    n_bi, n_sd = len(list(bi)), len(list(sd))
    if n_bi != n_sd:
        print(f'[!] SIRA BOZUK: BoneIds {n_bi} != SequenceData {n_sd}')
        return 1

    shutil.copyfile(yol, yol + '.kokoncesi')
    t.write(yol, encoding='utf-8', xml_declaration=True)
    print(f'[+] BoneIds {len(girisler)} -> {n_bi}   (kok 3 track)')
    print(f'[+] Unknown10 {eski_u} -> 1')
    print(f'[+] klip adi {eski_ad} -> {ad.text}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
