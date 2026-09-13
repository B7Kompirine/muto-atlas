#!/usr/bin/env python3
"""ypt_transplant.py — CALISAN bir vanilla efekti alip DOKUSUNU degistirir.

NEDEN: sifirdan yazilan bir kural calismadiginda "hangi alan eksik" sorusunu
alan alan aramak pahalidir; vanilla'da anlami cozulmemis onlarca `Unknown*`
alani var. Calisan bir yapilandirmayi BIREBIR kopyalayip TEK degiskeni
(dokuyu) degistirmek, kusuru tek turda ikiye boler:

  calisiyorsa  -> kusur bizim uretecimizin yazdigi alanlarda
  calismiyorsa -> kusur kuralda degil, hattin baska bir yerinde

Bu bir "vanilla efekt kullanma" yontemi DEGILDIR -- teshis araci. Uretim
icin build_custom_ptfx.py kullanilir.

Kullanim:
  python ypt_transplant.py core.ypt.xml --efekt ent_amb_fbi_cinder \\
      --yeni-ad my_kelebek2 --doku my_kelebek2 --klasor <cikti>
"""
from __future__ import annotations

import argparse
import os
import re
import struct
import sys

DOKU_BAYRAK = {
    (32, 32): "X16, UNK24",
    (64, 64): "X64, X128, UNK24",
    (128, 128): "X8, X32, X64, X128, UNK24",
    (256, 256): "X64, Y64, X256, UNK24",
    (512, 512): "X64, Y64, X256, Y512, UNK24",
    (1024, 1024): "X64, Y64, X256, Y512, Y1024, UNK24",
}


def blok(s, tag):
    a = s.find(f"<{tag}>")
    b = s.find(f"</{tag}>")
    return s[a:b] if a >= 0 else ""


def item_bul(sozluk, ad):
    """Sozluk icinde <Name>ad</Name> tasiyan ust seviye <Item> blogunu dondurur."""
    m = re.search(r"\n  <Item>\n   <Name>" + re.escape(ad) + r"</Name>(.*?)\n  </Item>",
                  sozluk, re.S)
    if not m:
        sys.exit(f"bulunamadi: {ad}")
    return "  <Item>\n   <Name>" + ad + "</Name>" + m.group(1) + "\n  </Item>\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kaynak_xml", help="vanilla .ypt.xml (orn. core.ypt.xml)")
    ap.add_argument("--efekt", required=True, help="kopyalanacak vanilla efekt adi")
    ap.add_argument("--yeni-ad", required=True)
    ap.add_argument("--doku", help="yeni doku adi (uzantisiz)")
    # ⛔ TESHIS MODU: dokuyu degistirme, donorun VANILLA dokusunu birak.
    #    Boylece "kural mi bizim dokumuz mu" sorusu ikiye bolunur:
    #      vanilla dokuyla dogru cizim -> kusur bizim dokumuzda
    #      vanilla dokuyla da bozuk    -> kusur hattin baska yerinde
    #    Vanilla doku core.ypt'te yasar; gomulu doku YAZILMAZ.
    ap.add_argument("--doku-koru", action="store_true",
                    help="donorun kendi dokusunu birak (gomulu doku yok)")
    # ⛔ KONTROL: BASKA bir VANILLA dokuya isimle bagla, gomme yapma.
    #    Boylece "vanilla doku gercekten dilimleniyor mu" sorusu, hucreleri
    #    BELIRGIN FARKLI bir vanilla sheet'iyle sinanabilir. Birbirine
    #    benzeyen hucreler (kor taneleri gibi) bu soruyu cevaplayamaz --
    #    dilimlenmis tek hucre ile dilimlenmemis tum sheet ayni gorunur.
    ap.add_argument("--vanilla-doku", default=None,
                    help="mevcut bir vanilla doku adina bagla (gomme yok)")
    ap.add_argument("--klasor", required=True)
    # ⛔ Boyutu `m_sizeScalarKFP` ile degil `m_whd*KFP` ile buyut.
    #    whd METRE cinsindendir ve anlami kesin olculdu; sizeScalar'in
    #    olcegi ise BELIRSIZ (dagilim yuzde gibi duruyor -- medyan 57.6 --
    #    ama donorde 0.44 degeriyle gorunur parcacik uretiyor). Belirsiz
    #    alani carpan olarak kullanmak teshisi bulandirir.
    ap.add_argument("--boyut-carpan", type=float, default=1.0,
                    help="Size davranisinin whd keyframe'lerini carpar (metre)")
    # `m_zoomScalarKFP` mesafeye gore olcekleme yapiyor gorunuyor: vanilla'da
    # deger efektin buyuklugu ile oluyor (minik efekt 0.75, dev gaz sutunu
    # 1200; medyan 51.8, %77.2 dolu). Yuksek degerde parcacik yaklasinca
    # KUCULUYOR gibi okunuyor. Bosaltmak mesru: vanilla'nin %22.8'i bos.
    ap.add_argument("--zoom-sifirla", action="store_true",
                    help="m_zoomScalarKFP keyframe'lerini bosaltir")
    # Donorun rengi de aynen gelir (kor efektinde turuncu->koyu kirmizi).
    # Rengi degistirirken ALFA EGRISI KORUNUR: sadece RGB yazilir, alfa
    # keyframe'i oldugu gibi birakilir -- yoksa efektin sonme davranisi
    # bozulur ve parcaciklar aniden kaybolur.
    ap.add_argument("--renk", nargs=3, type=float, metavar=("R", "G", "B"),
                    help="RGB 0..1; Colour davranisinin rengini degistirir")
    # UsageFlags bagimsiz bir alan DEGIL: CodeWalker'da `UsageData` tek bir
    # uint ve alt 5 bit Usage, ustu UsageFlags olarak paketleniyor
    # (Usage = UsageData & 0x1F, UsageFlags = UsageData >> 5). Yani yanlis
    # bayrak tum sozcugu degistirir. Donorun degerini birebir vermek icin.
    ap.add_argument("--doku-bayrak", default=None,
                    help="UsageFlags'i elle yaz (orn. 'X32, X64, X128, UNK24')")
    # `m_sizeScalarKFP` YUZDEDIR, notr deger 100. (KFPs.md: "Size Scalar --
    # width/height/depth percentages, max 1000%".) Olculdu: donorlerin
    # dagilimi 34 ile 694 arasinda -- `weap_veh_turb_dust` %693,6 ile
    # gokyuzunu kapatiyor, `td_blood_nose` %34,1 ile neredeyse gorunmuyor.
    # Donoru oldugu gibi almak efekti donorun sahnesine gore olceklendirir;
    # kendi efektimiz icin bandina oturtulmasi gerekir.
    ap.add_argument("--boyut-olcek", type=float, default=None,
                    help="m_sizeScalarKFP (YUZDE, notr=100)")
    ap.add_argument("--oran", type=float, default=None,
                    help="m_spawnRateOverTimeKFP (adet/sn)")
    ap.add_argument("--omur", type=float, default=None,
                    help="m_particleLifeKFP (saniye)")
    a = ap.parse_args()

    s = open(a.kaynak_xml, encoding="utf-8", errors="replace").read()
    er, em_d, pr_d = (blok(s, "EffectRuleDictionary"),
                      blok(s, "EmitterRuleDictionary"),
                      blok(s, "ParticleRuleDictionary"))

    efekt = item_bul(er, a.efekt)
    emitler = re.findall(r"<EmitterRule>([^<]*)</EmitterRule>", efekt)
    partler = re.findall(r"<ParticleRule>([^<]*)</ParticleRule>", efekt)
    if len(emitler) != 1 or len(partler) != 1:
        sys.exit(f"bu efektin {len(emitler)} emitter'i var -- tek emitterli birini sec")
    emitter = item_bul(em_d, emitler[0])
    particle = item_bul(pr_d, partler[0])

    # --- yeniden adlandirma ---
    ye, yem, ypa = a.yeni_ad, f"{a.yeni_ad}_em", f"{a.yeni_ad}_pr"
    efekt = efekt.replace(f"<Name>{a.efekt}</Name>", f"<Name>{ye}</Name>", 1)
    efekt = efekt.replace(f"<EmitterRule>{emitler[0]}</EmitterRule>",
                          f"<EmitterRule>{yem}</EmitterRule>")
    efekt = efekt.replace(f"<ParticleRule>{partler[0]}</ParticleRule>",
                          f"<ParticleRule>{ypa}</ParticleRule>")
    emitter = emitter.replace(f"<Name>{emitler[0]}</Name>", f"<Name>{yem}</Name>", 1)
    particle = particle.replace(f"<Name>{partler[0]}</Name>", f"<Name>{ypa}</Name>", 1)

    # --- DOKU DEGISIMI: TEK DEGISKEN BU ---
    eski = re.findall(r"<TextureName>([^<]+)</TextureName>", particle)
    if not eski:
        sys.exit("particle rule'da <TextureName> yok")
    if a.vanilla_doku:
        for e in set(eski):
            if e:
                particle = particle.replace(
                    f"<TextureName>{e}</TextureName>",
                    f"<TextureName>{a.vanilla_doku}</TextureName>")
        print(f"[i] VANILLA dokuya baglandi: {eski[0]} -> {a.vanilla_doku}")
    elif not a.doku_koru:
        if not a.doku:
            sys.exit("--doku ver ya da --doku-koru kullan")
        for e in set(eski):
            if e:
                particle = particle.replace(f"<TextureName>{e}</TextureName>",
                                            f"<TextureName>{a.doku}</TextureName>")

    if a.zoom_sifirla:
        yeni, n = re.subn(
            r"(<Name>ptxEffectRule:m_zoomScalarKFP</Name>\s*<Unknown6C[^>]*>\s*)"
            r"<Keyframes>.*?</Keyframes>",
            r"\1<Keyframes />", efekt, flags=re.S)
        if n:
            efekt = yeni
            print("[i] m_zoomScalarKFP bosaltildi")
        else:
            print("[!] UYARI: m_zoomScalarKFP zaten bos ya da bulunamadi")

    # --- boyut carpani: yalniz whd keyframe'leri ---
    if a.boyut_carpan != 1.0:
        def carp(m):
            govde = m.group(2)

            def kanal(k):
                return f"<{k.group(1)} value=\"{float(k.group(2)) * a.boyut_carpan:g}\" />"
            govde = re.sub(r"<(RedChannelColour|GreenChannelColour|BlueChannelColour)"
                           r" value=\"([-\d.eE+]+)\" />", kanal, govde)
            return m.group(1) + govde + m.group(3)

        n_once = particle
        particle = re.sub(
            r"(<Name>ptxu_Size:m_whd(?:Min|Max)KFP</Name>.*?<Keyframes>)(.*?)(</Keyframes>)",
            carp, particle, flags=re.S)
        if particle == n_once:
            print("[!] UYARI: whd keyframe'i bulunamadi, boyut DEGISMEDI")

    if a.boyut_olcek is not None:
        v = a.boyut_olcek

        def olcekle(m):
            govde = re.sub(r"<(RedChannelColour|GreenChannelColour) value=\"[-\d.eE+]+\" />",
                           lambda k: f"<{k.group(1)} value=\"{v:g}\" />", m.group(2))
            return m.group(1) + govde + m.group(3)

        once = emitter
        emitter = re.sub(
            r"(<Name>ptxEmitterRule:m_sizeScalarKFP</Name>.*?<Keyframes>)(.*?)(</Keyframes>)",
            olcekle, emitter, flags=re.S)
        print(f"[i] m_sizeScalarKFP = {v:g}" if emitter != once
              else "[!] UYARI: m_sizeScalarKFP bulunamadi")

    def emitter_kfp_yaz(blok_adi, deger, etiket):
        """Emitter kuralinda bir KFP'yi `deger` ORTALAMASINA olcekler.

        R = min, G = maks yuvasidir.

        ⛔ IKISINI DE AYNI YAZMA -- aralik cokerse rastgelelik kalkar ve
           butun parcaciklar ayni anda olur; goz bunu "mekanik" okur.
           Olculdu (n=1989): vanilla emitterlerin **%90,3**'u parcacik
           omrune min-max araligi verir, medyan maks/min **1.45**. Spawn
           oraninda da %56,7. Yani duz sayi yazmak coğunluk vakada
           vanilla'dan SAPMAKTIR.

        Dogrusu: donorun kendi yayilma oranini koru, araligi istenen
        ortalamaya tasi. Donorda aralik yoksa (min==max) duz kalir --
        o da donorun kendi tercihidir.
        """
        def yaz(m):
            govde = m.group(2)
            k = re.findall(r"<(?:Red|Green)ChannelColour value=\"([-\d.eE+]+)\" />",
                           govde)
            if len(k) >= 2:
                mn, mx = float(k[0]), float(k[1])
                ort = (mn + mx) / 2.0
                if ort > 1e-9:
                    yeni = (mn * deger / ort, mx * deger / ort)
                else:
                    yeni = (deger, deger)
            else:
                yeni = (deger, deger)
            it = iter(yeni)
            govde = re.sub(
                r"<(RedChannelColour|GreenChannelColour) value=\"[-\d.eE+]+\" />",
                lambda q: f"<{q.group(1)} value=\"{next(it, deger):g}\" />",
                govde, count=2)
            return m.group(1) + govde + m.group(3)
        return re.sub(r"(<Name>ptxEmitterRule:" + blok_adi + r"</Name>.*?<Keyframes>)"
                      r"(.*?)(</Keyframes>)", yaz, emitter, flags=re.S), etiket

    if a.oran is not None:
        once = emitter
        emitter, _ = emitter_kfp_yaz("m_spawnRateOverTimeKFP", a.oran, "oran")
        print(f"[i] spawn orani = {a.oran:g}/sn" if emitter != once
              else "[!] UYARI: m_spawnRateOverTimeKFP bulunamadi")
    if a.omur is not None:
        once = emitter
        emitter, _ = emitter_kfp_yaz("m_particleLifeKFP", a.omur, "omur")
        print(f"[i] parcacik omru = {a.omur:g} sn" if emitter != once
              else "[!] UYARI: m_particleLifeKFP bulunamadi")

    # --- renk: yalniz ptxu_Colour'un RGB kanallari, alfa egrisi korunur ---
    if a.renk:
        r, g, b = a.renk

        def renkle(m):
            def kf(k):
                return (f"<RedChannelColour value=\"{r:g}\" />\n"
                        f"        <GreenChannelColour value=\"{g:g}\" />\n"
                        f"        <BlueChannelColour value=\"{b:g}\" />")
            govde = re.sub(r"<RedChannelColour value=\"[-\d.eE+]+\" />\s*"
                           r"<GreenChannelColour value=\"[-\d.eE+]+\" />\s*"
                           r"<BlueChannelColour value=\"[-\d.eE+]+\" />",
                           kf, m.group(2))
            return m.group(1) + govde + m.group(3)

        once = particle
        particle = re.sub(
            r"(<Name>ptxu_Colour:m_rgba(?:Min|Max)KFP</Name>.*?<Keyframes>)(.*?)(</Keyframes>)",
            renkle, particle, flags=re.S)
        print("[i] renk yazildi" if particle != once
              else "[!] UYARI: Colour keyframe'i bulunamadi, renk DEGISMEDI")

    if a.doku_koru or a.vanilla_doku:
        print(f"[i] GOMULU DOKU YOK: {eski[0]}  (gomulu doku yazilmadi)")
        yol = os.path.join(a.klasor, ye + ".ypt.xml")
        xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
               "<ParticleEffectsList>\n"
               f" <Name>{ye}</Name>\n"
               f" <EffectRuleDictionary>\n{efekt} </EffectRuleDictionary>\n"
               f" <EmitterRuleDictionary>\n{emitter} </EmitterRuleDictionary>\n"
               f" <ParticleRuleDictionary>\n{particle} </ParticleRuleDictionary>\n"
               " <DrawableDictionary />\n <TextureDictionary />\n"
               "</ParticleEffectsList>\n")
        import xml.etree.ElementTree as ET
        try:
            ET.fromstring(xml)
        except ET.ParseError as e:
            sys.exit(f"URETILEN XML AYRISMIYOR: {e}")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"[+] {yol}  ({len(xml):,} karakter)")
        print(f"    donor efekt : {a.efekt}  ->  {ye}")
        return 0

    dds = os.path.join(a.klasor, a.doku + ".dds")
    if not os.path.exists(dds):
        sys.exit(f"DDS yok: {dds}")
    with open(dds, "rb") as fh:
        bas = fh.read(128)
    _, _, yuk, gen, _, _, mip = struct.unpack("<7I", bas[4:32])
    mip = max(1, mip)
    fmt = {b"DXT1": "D3DFMT_DXT1", b"DXT5": "D3DFMT_DXT5"}.get(
        bas[84:88], "D3DFMT_A8R8G8B8")
    bayrak = a.doku_bayrak or DOKU_BAYRAK.get((gen, yuk), DOKU_BAYRAK[(512, 512)])

    td = (f"  <Item>\n   <Name>{a.doku}</Name>\n"
          f"   <Unk32 value=\"128\" />\n   <Usage>DIFFUSE</Usage>\n"
          f"   <UsageFlags>{bayrak}</UsageFlags>\n"
          f"   <ExtraFlags value=\"0\" />\n"
          f"   <Width value=\"{gen}\" />\n   <Height value=\"{yuk}\" />\n"
          f"   <MipLevels value=\"{mip}\" />\n   <Format>{fmt}</Format>\n"
          f"   <FileName>{a.doku}.dds</FileName>\n  </Item>\n")

    xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<ParticleEffectsList>\n"
           f" <Name>{ye}</Name>\n"
           f" <EffectRuleDictionary>\n{efekt} </EffectRuleDictionary>\n"
           f" <EmitterRuleDictionary>\n{emitter} </EmitterRuleDictionary>\n"
           f" <ParticleRuleDictionary>\n{particle} </ParticleRuleDictionary>\n"
           " <DrawableDictionary />\n"
           f" <TextureDictionary>\n{td} </TextureDictionary>\n"
           "</ParticleEffectsList>\n")

    # uretici kendi ciktisini dogrular
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(xml)
    except ET.ParseError as e:
        sys.exit(f"URETILEN XML AYRISMIYOR: {e}")

    yol = os.path.join(a.klasor, ye + ".ypt.xml")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(xml)
    c4 = re.search(r'<UnknownC4 value="([^"]+)"', particle)
    print(f"[+] {yol}  ({len(xml):,} karakter)")
    print(f"    donor efekt : {a.efekt}  ->  {ye}")
    print(f"    doku        : {eski[0]}  ->  {a.doku}  ({gen}x{yuk} {fmt} mip={mip})")
    if c4:
        n = int(c4.group(1)) + 1
        print(f"    UnknownC4={c4.group(1)}  =>  {n} kare  (donorden AYNEN alindi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
