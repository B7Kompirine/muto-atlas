# -*- coding: utf-8 -*-
"""ycd_track2_ekle.py -- Sollumz'un yazdigi .ycd.xml'e eksik Track 2 (OLCEK) grubunu ekler.

NEDEN: Sollumz kemik basina yalnizca Track 0 (konum) ve Track 1 (donus) yazar.
Vanilla sozlesmesi UC track ister; olculdu (des_mutotest.ycd, 7 kemik -> 21 giris):

    Track 0 (konum)  Unk0=0   tum kemikler
    Track 1 (donus)  Unk0=1   tum kemikler
    Track 2 (olcek)  Unk0=0   tum kemikler   <- Sollumz bunu YAZMAZ

Track 2 yoksa klip oynar, faz ilerler, HICBIR HATA CIKMAZ ama mesh kipirdamaz.
Bu tam olarak yasandi ve tesihisi ancak calisan bir dosyayla alan alan
karsilastirarak bulundu.

BoneIds sirasi ile SequenceData sirasi BIREBIR eslesmek zorundadir.

Kullanim:  python ycd_track2_ekle.py <dosya.ycd.xml>
"""
import re, sys, shutil

def main(yol):
    s = open(yol, encoding='utf-8').read()
    bi_m = re.search(r'(<BoneIds>)(.*?)(</BoneIds>)', s, re.S)
    sd_m = re.search(r'(<SequenceData>)(.*?)(</SequenceData>)', s, re.S)
    if not bi_m or not sd_m:
        print('[!] BoneIds / SequenceData bulunamadi'); return 1

    girisler = re.findall(r'<Item>\s*<BoneId value="(\d+)"\s*/>\s*<Track value="(\d+)"\s*/>\s*<Unk0 value="(\d+)"\s*/>\s*</Item>',
                          bi_m.group(2))
    if not girisler:
        print('[!] BoneIds girisi ayristirilamadi'); return 1
    varolan = {(b, t) for b, t, _ in girisler}
    if any(t == '2' for _, t in varolan):
        print('[=] Track 2 zaten var, dokunulmadi'); return 0

    kemikler = []
    for b, t, _ in girisler:
        if t == '0' and b not in kemikler:
            kemikler.append(b)
    print(f'[*] kemik {len(kemikler)} | mevcut giris {len(girisler)}')

    # --- BoneIds: sona Track 2 grubu
    ek_bi = ''.join(
        f'\n    <Item>\n     <BoneId value="{b}" />\n     <Track value="2" />\n     <Unk0 value="0" />\n    </Item>'
        for b in kemikler)
    yeni_bi = bi_m.group(1) + bi_m.group(2).rstrip() + ek_bi + '\n   ' + bi_m.group(3)

    # --- SequenceData: her yeni giris icin StaticVector3(1,1,1)
    ek_sd = ''.join(
        '\n      <Item>\n       <Channels>\n        <Item>\n'
        '         <Type value="StaticVector3" />\n'
        '         <Value x="1" y="1" z="1" />\n'
        '        </Item>\n       </Channels>\n      </Item>'
        for _ in kemikler)
    yeni_sd = sd_m.group(1) + sd_m.group(2).rstrip() + ek_sd + '\n     ' + sd_m.group(3)

    s2 = s[:bi_m.start()] + yeni_bi + s[bi_m.end():]
    sd2 = re.search(r'(<SequenceData>)(.*?)(</SequenceData>)', s2, re.S)
    s2 = s2[:sd2.start()] + yeni_sd + s2[sd2.end():]

    # kendi ciktini DOGRULA
    import xml.etree.ElementTree as ET
    ET.fromstring(s2)
    n_bi = len(re.findall(r'<BoneId value=', re.search(r'<BoneIds>(.*?)</BoneIds>', s2, re.S).group(1)))
    n_sd = len(re.findall(r'<Item>\s*<Channels>', re.search(r'<SequenceData>(.*?)</SequenceData>', s2, re.S).group(1)))
    if n_bi != n_sd:
        print(f'[!] SIRA BOZUK: BoneIds {n_bi} != SequenceData {n_sd}'); return 1

    shutil.copyfile(yol, yol + '.yedek')
    open(yol, 'w', encoding='utf-8').write(s2)
    print(f'[+] Track 2 eklendi: {len(kemikler)} kemik')
    print(f'    BoneIds {len(girisler)} -> {n_bi} | SequenceData -> {n_sd}  (esit)')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
