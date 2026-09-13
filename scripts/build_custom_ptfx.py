#!/usr/bin/env python3
"""build_custom_ptfx.py — SIFIRDAN ozel partikul efekti (.ypt) uretir.

Vanilla bir efekti kopyalayip degistirmez: efekt/emitter/particle kurallarini
ve dokuyu SIFIRDAN yazar. GTA'nin hicbir efekt adi, dokusu ya da egrisi
kullanilmaz.

⚠ DURUSTCE: `.ypt` ikili bir kaynak bicimidir ve semasinda anlami
cozulmemis (`Unknown*`) alanlar vardir. Bunlarin DEGERLERI bicimin
zorunlulugudur -- vanilla dosyalardan olculup guvenli sabitler olarak
alinmistir. GORSELIN kendisi (doku, renk, boyut, omur, hiz, spawn egrisi)
tamamen bizimdir.

HAT:
  1) make_dds.py ile kendi sprite'ini uret
  2) bu betik .ypt.xml yazar
  3) CodeWalker XmlYpt.GetYpt(xml, klasor) -> binary .ypt
     (DDS dosyasi XML ILE AYNI KLASORDE olmali, yoksa
      "Texture file not found" ile coker)

Kullanim:
  python build_custom_ptfx.py --ad muto_spore --doku muto_ptfx_soft \\
      --klasor <cikti> --renk 0.2 0.9 0.35 --omur 2.5 --boyut 0.35 --oran 25
"""
from __future__ import annotations

import argparse
import os
import sys

# --- bicim sabitleri: vanilla core.ypt'ten olculdu, anlami cozulmedi ---
# Bunlar "sihirli sayi" degil, semanin zorunlu alanlari. Degistirme.
#
# ⛔ BILINMEYEN ALANA 0 YAZMA -- vanilla'nin EN SIK degerini yaz.
#    core.ypt'teki 964 efekt kuralinda olculdu. Sifir cogu alanda
#    vanilla'da HIC gecmiyor (UnknownA4/A8/AC/B0 gibi); bunlar mesafe/
#    LOD bandi gorunumunde ve sifirlanirsa efekt hicbir mesafede
#    cizilmeyebilir. "Bilmiyorum, 0 birakayim" sessiz hata uretir.
EFEKT_SABIT = """   <Unknown50 value="0xFFFFFFFF" />
   <Unknown54 value="0x1000000" />
   <Unknown70 value="0" />
   <Unknown74 value="0.25" />
   <PlaybackDelay value="2" />
   <PlaybackDelayModifier value="2" />
   <PlaybackSpeedScale value="1" />
   <PlaybackSpeedScaleModifier value="1" />
   <Unknown88 value="0x1010100" />
   <Unknown8C value="0x10004" />
   <CullRadius value="0" />
   <CullDistance value="0" />
   <Unknown98 value="0" />
   <UnknownA0 value="0" />
   <UnknownA4 value="50" />
   <UnknownA8 value="60" />
   <UnknownAC value="10" />
   <UnknownB0 value="30" />
   <UnknownB4 value="0" />
   <UnknownB8 value="0" />
   <UnknownBC value="0x0" />
   <Unknown3A0 value="0x0" />"""

# ⛔ UsageFlags DOKU BOYUTUNA GORE DEGISIR -- sabit yazma.
#    core.ypt'teki 107 dokuda boyut basina olculdu. Yanlis bayrak
#    yazmak dokunun yanlis orneklenmesine yol acar ve SESSIZDIR.
DOKU_BAYRAK = {
    (32, 32):     "X16, UNK24",
    (64, 64):     "X64, X128, UNK24",
    (128, 128):   "X8, X32, X64, X128, UNK24",
    (256, 256):   "X64, Y64, X256, UNK24",
    (512, 512):   "X64, Y64, X256, Y512, UNK24",
    (1024, 1024): "X64, Y64, X256, Y512, Y1024, UNK24",
    (2048, 2048): "X32, X64, X128, X512, X1024, X2048, UNK24",
}

EFEKT_KFP = [
    ("ptxEffectRule:m_colourTintMinKFP", 63744),
    ("ptxEffectRule:m_colourTintMaxKFP", 64000),
    ("ptxEffectRule:m_zoomScalarKFP", 64256),
    ("ptxEffectRule:m_dataSphereKFP", 64512),
    ("ptxEffectRule:m_dataCapsuleKFP", 64768),
]

EMITTER_KFP = [
    ("ptxEmitterRule:m_spawnRateOverTimeKFP", 54272),
    ("ptxEmitterRule:m_spawnRateOverDistKFP", 54528),
    ("ptxEmitterRule:m_particleLifeKFP", 54784),
    ("ptxEmitterRule:m_playbackRateScalarKFP", 55040),
    ("ptxEmitterRule:m_speedScalarKFP", 55296),
    ("ptxEmitterRule:m_sizeScalarKFP", 55552),
    ("ptxEmitterRule:m_accnScalarKFP", 55808),
    ("ptxEmitterRule:m_dampeningScalarKFP", 56064),
    ("ptxEmitterRule:m_matrixWeightScalarKFP", 56320),
    ("ptxEmitterRule:m_inheritVelocityKFP", 56576),
]

DOMAIN_KFP = [
    ("m_positionKFP", 12800), ("m_rotationKFP", 13056),
    ("m_sizeOuterKFP", 13312), ("m_sizeInnerKFP", 13568),
]


def kf(interval=0.0, mult=0.0, r=0.0, g=0.0, b=0.0, a=0.0, girinti=7):
    """Tek keyframe. R/G/B/A adlari YANILTICI: bunlar genel dort kanaldir.
    Anlamlari, iceride bulunduklari <Name> alanina gore degisir --
    spawn rate icinde 'Red' = oran, xyz icinde 'Red' = X."""
    i = " " * girinti
    return (f"{i}<Item>\n"
            f"{i} <InterpolationInterval value=\"{interval:g}\" />\n"
            f"{i} <KeyFrameMultiplier value=\"{mult:g}\" />\n"
            f"{i} <RedChannelColour value=\"{r:g}\" />\n"
            f"{i} <GreenChannelColour value=\"{g:g}\" />\n"
            f"{i} <BlueChannelColour value=\"{b:g}\" />\n"
            f"{i} <AlphaChannelColour value=\"{a:g}\" />\n"
            f"{i}</Item>\n")


def kfp(ad, unk, kareler, girinti=4, etiket="Item"):
    i = " " * girinti
    ic = "".join(kareler)
    kf_blok = f"{i} <Keyframes>\n{ic}{i} </Keyframes>\n" if ic else f"{i} <Keyframes />\n"
    return (f"{i}<{etiket}>\n"
            f"{i} <Name>{ad}</Name>\n"
            f"{i} <Unknown6C value=\"{unk}\" />\n"
            f"{kf_blok}"
            f"{i}</{etiket}>\n")


def domain(tur, sinif, taban_unk, yaricap, konum_z=0.0, girinti=3):
    """Bir domain blogu.

    ⛔ PARCACIGI HAREKET ETTIREN SEY `Velocity` DAVRANISI DEGIL,
       TARGET DOMAIN'IN KONUMUDUR. (Velocity'nin 0 keyframe yuvasi var.)
       Olculdu: vanilla emitter'larin %89,2'sinde `Domain2:m_positionKFP`
       Z'si sifirdan farkli, medyan +0.400. Yukselen duman/spor bu
       ofsetle yapilir; iki domain de ayni merkezdeyse net yon olusmaz
       ve efekt yerinde durur.
    """
    i = " " * girinti
    p = ""
    for k, (ad, unk) in enumerate(DOMAIN_KFP):
        kareler = []
        if ad == "m_sizeOuterKFP":
            # kureyi bu yaricapta ac: parcaciklarin dogdugu hacim
            kareler = [kf(r=yaricap, g=yaricap, b=yaricap, girinti=girinti + 4)]
        elif ad == "m_positionKFP" and konum_z:
            kareler = [kf(b=konum_z, girinti=girinti + 4)]
        p += kfp(f"{sinif}:{ad}", taban_unk + k * 256, kareler,
                 girinti=girinti + 1, etiket=f"KeyframeProperty{k}")
    return (f"{i}<{tur}>\n"
            f"{i} <Type value=\"Sphere\" />\n"
            f"{i} <Unknown10 value=\"0x0\" />\n"
            f"{i} <Unknown258 value=\"{yaricap:g}\" />\n"
            f"{p}"
            f"{i}</{tur}>\n")


def uret_xml(ad, doku, renk, omur, boyut, oran, hiz, yaricap,
             dgen=128, dyuk=128, dmip=4, dfmt="D3DFMT_DXT5",
             yukselme=0.4, alfa=1.0, sheet_kare=1, anim_hiz=0.0,
             dbayrak="X64, Y64, X256, Y512, UNK24", renk2=None,
             ivme=0.0, donme=0.0, gurultu=0.0, sekme=0.0,
             isik=0.0, isik_menzil=3.0, parlama=0.0,
             anim_c8=1, anim_cc="0x1010100"):
    r, g, b = renk
    # ⛔ OMUR BOYUNCA RENK GECISI. Colour davranisinin keyframe'leri
    #    parcacigin OMRU boyunca interpole edilir: ilk kare dogum,
    #    son kare olum. Iki farkli renk vermek 'turuncu dogup yesile
    #    donen' asit gorunumunu tek efektte verir -- iki ayri efekt
    #    ust uste bindirmeye gerek kalmaz.
    r2, g2, b2 = renk2 if renk2 else (r, g, b)
    efekt, emit, part = ad, f"{ad}_em", f"{ad}_pr"

    # --- EFFECT RULE ---
    ekfp = "".join(kfp(n, u, [], girinti=4) for n, u in EFEKT_KFP)
    effect = (f"  <Item>\n"
              f"   <Name>{efekt}</Name>\n{EFEKT_SABIT}\n"
              f"   <EventEmitters>\n"
              f"    <Item>\n"
              f"     <EmitterRule>{emit}</EmitterRule>\n"
              f"     <ParticleRule>{part}</ParticleRule>\n"
              f"     <Unknown10 value=\"0\" />\n"
              f"     <Unknown14 value=\"1\" />\n"
              f"     <MoveSpeedScale value=\"1\" />\n"
              f"     <MoveSpeedScaleModifier value=\"1\" />\n"
              f"     <ParticleScale value=\"1\" />\n"
              f"     <ParticleScaleModifier value=\"1\" />\n"
              f"     <Colour1 value=\"0xFFFFFFFF\" />\n"
              f"     <Colour2 value=\"0xFFFFFFFF\" />\n"
              # ⛔ UnknownData ZORUNLU BLOK. Yazilmazsa XML sorunsuz ayrisir,
              #    kural sozlukleri dolu okunur, ama Save() sirasinda
              #    ResourceSystemBlock.set_FilePosition NULL referansta coker.
              #    Icerigi bos olabilir; VAR OLMASI gerekir.
              f"     <UnknownData>\n"
              f"      <EventEmitterFlags />\n"
              f"      <Unknown10 />\n"
              f"     </UnknownData>\n"
              f"    </Item>\n"
              f"   </EventEmitters>\n"
              f"   <KeyframeProperties>\n{ekfp}   </KeyframeProperties>\n"
              f"  </Item>\n")

    # --- EMITTER RULE: spawn orani, omur, hiz bizim ---
    deger = {
        "ptxEmitterRule:m_spawnRateOverTimeKFP": [kf(r=oran, g=oran, girinti=8)],
        "ptxEmitterRule:m_particleLifeKFP":      [kf(r=omur, g=omur, girinti=8)],
        "ptxEmitterRule:m_speedScalarKFP":       [kf(r=hiz,  g=hiz,  girinti=8)],
        # ⛔ sizeScalar YUZDE OLCEGINDEDIR, kesir DEGIL.
        #    Olculdu (2.097 keyframe): %5=1.0 · medyan=57.6 · %75=125 · %95=297.
        #    1.0 yazmak en alt %5'e dusmektir -> parcacik boyutunun ~%1'i ->
        #    OYUNDA HICBIR SEY GORUNMEZ. 100 = notr.
        #    Ayni yuzde olcegi accn/dampening/matrixWeight icin de gecerli
        #    (medyanlari 98.4 / 98.6 / 93.8); speed ve life ise ~1.0 olcegi.
        "ptxEmitterRule:m_sizeScalarKFP":        [kf(r=100.0, g=100.0, girinti=8)],
    }
    ekf = "".join(kfp(n, u, deger.get(n, []), girinti=5) for n, u in EMITTER_KFP)
    emitter = (f"  <Item>\n"
               f"   <Name>{emit}</Name>\n"
               f"   <Unknown10 value=\"2\" />\n"      # 1674/1993
               f"   <Unknown628 value=\"0\" />\n"     # 1116/1993
               f"{domain('Domain1', 'ptxCreationDomain', 12800, yaricap)}"
               f"{domain('Domain2', 'ptxTargetDomain', 13824, yaricap, yukselme)}"
               f"   <KeyframeProperties>\n{ekf}   </KeyframeProperties>\n"
               f"  </Item>\n")

    # --- PARTICLE RULE: renk ve boyut bizim ---
    # Degerler core.ypt'teki 1.736 particle rule'un EN SIK degeridir
    # (parantez icinde pay). 0 yazilan yerler zaten vanilla'da da 0.
    sabit = "".join(f"   <Unknown{k} value=\"{v}\" />\n" for k, v in (
        ("10", "2"),        # 1341/1736
        ("100", "2"),       # 1098/1736
        ("104", "0"),       # 1545/1736
        ("108", "2"),       # 1347/1736
        ("10C", "0x10100"), # 1638/1736  -- %94, neredeyse sabit
        ("118", "0"),       # 1121/1736
        ("11C", "0"),       # 398/1736 (3 ile basa bas)
        ("1D0", "5"),       # 890/1736
        ("1E0", "0"),       # 1398/1736
        ("1E4", "0"),       # 1732/1736
        ("1E8", "0x101"),   # 1044/1736
        ("1EC", "0"),       # 1722/1736
        ("220", "0x2")))    # 736/1736
    spawner = ("   <Spawner{n}>\n"
               "    <EffectRule />\n"
               "    <Unknown18 value=\"0\" />\n"
               "    <Unknown1C value=\"0\" />\n"
               "    <Unknown20 value=\"0x0\" />\n"
               "    <Unknown24 value=\"0\" />\n"
               "    <Unknown28 value=\"0\" />\n"
               "    <Unknown38 value=\"0\" />\n"
               "    <Unknown3C value=\"0\" />\n"
               "    <Unknown40 value=\"0x0\" />\n"
               "    <Unknown44 value=\"0\" />\n"
               "    <Unknown48 value=\"0\" />\n"
               "    <Unknown68 value=\"0\" />\n"
               "    <Unknown6C value=\"0x0\" />\n"
               "   </Spawner{n}>\n")

    # --- DAVRANISLAR ---
    # ⛔ HER DAVRANIS TIPININ YUVA SAYISI SABITTIR VE HEPSI YAZILMALIDIR.
    #    Yazilmayan yuva null blok birakir; XML sorunsuz ayrisir, sozlukler
    #    dolu okunur, ama Save() ResourceBuilder.AssignPositions icinde
    #    NullReferenceException ile coker. Hata mesaji hangi yuva oldugunu
    #    SOYLEMEZ -- bu yuzden tablo asagida, tahmin edilmez.
    #
    #    core.ypt'teki 15.430 davranista olculdu; her tip TEK bir yuva
    #    sayisi gosteriyor, istisna yok:
    #      Age 0 · Velocity 0 · Sprite 0 · MatrixWeight 1 · AnimateTexture 1
    #      Wind 1 · Trail 1 · Attractor 1 · Acceleration 2 · Dampening 2
    #      Collision 2 · ZCull 2 · Decal 2 · Colour 3 · Size 4 · Rotation 4
    #      Noise 4 · FogVolume 7 · Light 9
    #    <Name> degerleri 1736/1736 sabit (gercek sema). <Unknown6C> ise
    #    dosya ici konumdur, 256'sar artar; sabit degildir.
    #
    #    Velocity'nin 0 yuvasi olmasi sasirtici degil: parcacik hizi
    #    davranista degil, EMITTER kuralinin speedScalar'inda ve
    #    creation/target domain'lerinde tanimlanir.
    def dvr(tip, yuvalar=(), alanlar=(), taban=30208):
        g = "".join(f"     <Unknown{k} value=\"{v}\" />\n" for k, v in alanlar)
        p = ""
        for i, (ad, kareler) in enumerate(yuvalar):
            ic = "".join(kareler)
            kb = f"      <Keyframes>\n{ic}      </Keyframes>\n" if ic else "      <Keyframes />\n"
            p += (f"     <KeyframeProperty{i}>\n"
                  f"      <Name>{ad}</Name>\n"
                  f"      <Unknown6C value=\"{taban + i * 256}\" />\n"
                  f"{kb}"
                  f"     </KeyframeProperty{i}>\n")
        return f"    <Item>\n     <Type value=\"{tip}\" />\n{g}{p}    </Item>\n"

    # ⛔ DAVRANIS SIRASI RASTGELE DEGIL. core.ypt'te normalize konum
    #    ortalamasiyla olculdu (15.430 davranis) -- kanonik sira:
    #      Age · Acceleration · Attractor · Velocity · Rotation · Noise ·
    #      Size · Dampening · MatrixWeight · Wind · ZCull · Collision ·
    #      AnimateTexture · Light · Colour · Sprite/Model/Trail (hep son)
    #    AnimateTexture'in Sprite'tan once gelmesi 781/781 kuralda gecerli.
    dav = (
        dvr("Age")
        # ⛔ Acceleration xyz METRE/SN^2. Yukselen duman/bugu icin Z pozitif.
        + (dvr("Acceleration",
               (("ptxu_Acceleration:m_xyzMinKFP",
                 [kf(b=ivme * 0.6, girinti=8)]),
                ("ptxu_Acceleration:m_xyzMaxKFP",
                 [kf(b=ivme, girinti=8)])),
               (("158", "0"), ("15C", "0")), taban=11776)
           if ivme else "")
        + dvr("Velocity")
        # ⛔ Rotation: ilk iki yuva BASLANGIC acisi (rastgelelik), son iki
        #    yuva DONME HIZI. Derece cinsinden. Baslangic acisi verilmezse
        #    butun parcaciklar ayni yone bakar ve tekrar gozle secilir.
        + (dvr("Rotation",
               (("ptxu_Rotation:m_initialAngleMinKFP", [kf(r=0.0, girinti=8)]),
                ("ptxu_Rotation:m_initialAngleMaxKFP", [kf(r=360.0, girinti=8)]),
                ("ptxu_Rotation:m_angleMinKFP", [kf(r=-donme, girinti=8)]),
                ("ptxu_Rotation:m_angleMaxKFP", [kf(r=donme, girinti=8)])),
               (("270", "0"), ("274", "0"), ("278", "0x1"), ("27C", "0")),
               taban=18944)
           if donme else "")
        # ⛔ Noise = TURBULANS. pos gurultusu parcacigi kaydirir, vel
        #    gurultusu yonunu bozar. Ikisi birden olmadan duman duz gider.
        + (dvr("Noise",
               (("ptxu_Noise:m_posNoiseMinKFP",
                 [kf(r=-gurultu, g=-gurultu, b=-gurultu * .5, girinti=8)]),
                ("ptxu_Noise:m_posNoiseMaxKFP",
                 [kf(r=gurultu, g=gurultu, b=gurultu * .5, girinti=8)]),
                ("ptxu_Noise:m_velNoiseMinKFP",
                 [kf(r=-gurultu * .8, g=-gurultu * .8, b=0.0, girinti=8)]),
                ("ptxu_Noise:m_velNoiseMaxKFP",
                 [kf(r=gurultu * .8, g=gurultu * .8, b=0.0, girinti=8)])),
               (("270", "0"), ("274", "1")), taban=12544)
           if gurultu else "")
        + dvr("Size",
              # whd = width/height/depth. Vanilla'da B (depth) medyani 0.000 --
              # sprite duz bir quad oldugu icin derinlik yazilmaz.
              (("ptxu_Size:m_whdMinKFP",
                [kf(r=boyut * .6, g=boyut * .6, girinti=8),
                 kf(interval=1.0, r=boyut * 1.4, g=boyut * 1.4, girinti=8)]),
               ("ptxu_Size:m_whdMaxKFP",
                [kf(r=boyut, g=boyut, girinti=8),
                 kf(interval=1.0, r=boyut * 2.0, g=boyut * 2.0, girinti=8)]),
               # ⛔ tblrScalar BOS BIRAKILAMAZ. Vanilla'da 1727/1736 dolu
               #    (%99,5) ve degeri neredeyse her zaman 1.0 -- yani notr
               #    carpan. Bos birakmak carpani 0 yapar ve sprite sifir
               #    boyutta cizilir: efekt "calisir", hicbir sey gorunmez.
               ("ptxu_Size:m_tblrScalarKFP",
                [kf(r=1.0, g=1.0, b=1.0, girinti=8)]),
               # tblrVelScalar vanilla'da %83,6 bos -- bos birakmak normaldir.
               ("ptxu_Size:m_tblrVelScalarKFP", [])),
              (("270", "0"), ("274", "1")), taban=35840)
        # ⛔ Collision: parcacik dunyaya carpar. bounciness 0=yapisir,
        #    1=tam seker. bounceDirVar yon sapmasi -- 0 birakilirsa
        #    hepsi ayni acida seker ve mekanik durur.
        + (dvr("Collision",
               (("ptxu_Collision:m_bouncinessKFP", [kf(r=sekme, girinti=8)]),
                ("ptxu_Collision:m_bounceDirVarKFP", [kf(r=0.35, girinti=8)])),
               (("150", "0.1"), ("154", "0"), ("158", "100"), ("15C", "0")),
               taban=14336)
           if sekme else "")
        # ⛔ SPRITE SHEET ANIMASYONU = `AnimateTexture` davranisi.
        #    Olculdu, iki bagimsiz vanilla sheet'i GOZLE sayilarak:
        #      ptfx_smoke_billow_anim_rgba  1024x1024  6x6 = 36 kare  -> C4 = 35
        #      ptfx_water_splashes_sheet     512x512   2x2 =  4 kare  -> C4 =  3
        #    Yani `UnknownC4` = KARE SAYISI - 1 (son karenin indeksi).
        #    Izgara kare: sutun = satir = sqrt(kare). Kareler soldan saga,
        #    yukaridan asagiya.
        #    UnknownCC 0x1000100 degeri 6x6 sheet'lerin kullandigi kombinasyon.
        #    m_animRateKFP bos birakilirsa motor varsayilan hizda oynatir;
        #    deger verilirse cirpma hizi oradan ayarlanir.
        + (dvr("AnimateTexture",
               (("ptxu_AnimateTexture:m_animRateKFP",
                 [kf(r=anim_hiz, g=anim_hiz, girinti=8)] if anim_hiz else []),),
               (("C0", "0"), ("C4", str(max(0, sheet_kare - 1))),
                ("C8", str(anim_c8)), ("CC", anim_cc)), taban=31488)
           if sheet_kare > 1 else "")
        # ⛔ Light: parcacik GERCEK ISIK yayar -- zemini ve cevreyi
        #    aydinlatir. "Yerde duran duz renk" hissini kiran sey budur.
        #    9 yuvanin HEPSI yazilmali; korona yuvalari bos kalabilir.
        + (dvr("Light",
               (("ptxu_Light:m_rgbMinKFP", [kf(r=r, g=g, b=b, girinti=8)]),
                ("ptxu_Light:m_rgbMaxKFP", [kf(r=r2, g=g2, b=b2, girinti=8)]),
                ("ptxu_Light:m_intensityKFP",
                 [kf(r=isik, g=isik, girinti=8),
                  kf(interval=1.0, r=0.0, g=0.0, girinti=8)]),
                ("ptxu_Light:m_rangeKFP",
                 [kf(r=isik_menzil, g=isik_menzil, girinti=8)]),
                ("ptxu_Light:m_coronaRgbMinKFP", []),
                ("ptxu_Light:m_coronaRgbMaxKFP", []),
                ("ptxu_Light:m_coronaIntensityKFP", []),
                ("ptxu_Light:m_coronaSizeKFP", []),
                ("ptxu_Light:m_coronaFlareKFP", [])),
               (("540", "0"), ("544", "0x101"), ("548", "0x0"), ("54C", "0")),
               taban=40448)
           if isik else "")
        + dvr("Colour",
              (("ptxu_Colour:m_rgbaMinKFP",
                [kf(r=r, g=g, b=b, a=alfa, girinti=8),
                 kf(interval=1.0, r=r2, g=g2, b=b2, a=0.0, girinti=8)]),
               ("ptxu_Colour:m_rgbaMaxKFP",
                [kf(r=r, g=g, b=b, a=alfa, girinti=8),
                 kf(interval=1.0, r=r2, g=g2, b=b2, a=0.0, girinti=8)]),
               # Kendinden isikli parlama. Bos birakmak vanilla'da
               # %71,7 -- ama parlayan sivi/atesin sirri burada.
               ("ptxu_Colour:m_emissiveIntensityKFP",
                [kf(r=parlama, g=parlama, girinti=8)] if parlama else [])),
              (("1E0", "0"), ("1E4", "0x101")), taban=31744)
        + dvr("Sprite", (), (
            ("30", "0"), ("34", "0"), ("38", "0"), ("40", "0"), ("44", "0"),
            ("48", "0"), ("4C", "0"), ("50", "0"), ("54", "0"), ("58", "0"),
            ("5C", "0x100"), ("60", "0x0")))
    )

    # ⛔ DOKU BAGI <Behaviours> ICINDE DEGIL, <ShaderVars> ICINDEDIR.
    #    Olculdu (cut_arena + core): Behaviours yalniz su 10 tipi tasir --
    #    Age Acceleration Velocity Rotation Size Dampening MatrixWeight
    #    Wind Colour Sprite. Texture ORADA HIC GECMEZ.
    # ⛔ <Name> doku adi degil, SHADER SAMPLER YUVASI (diffusetex2 /
    #    normalspecmap / refractionmap); gercek ad <TextureName>'dedir.
    #    Ters yazilirsa XML ayrisir, hata cikmaz, doku BAGLANMAZ.
    shadervars = (f"    <Item>\n     <Type value=\"Texture\" />\n"
                  f"     <Name>diffusetex2</Name>\n"
                  f"     <Unknown18 value=\"4\" />\n     <Unknown3C value=\"0\" />\n"
                  f"     <TextureName>{doku}</TextureName>\n    </Item>\n")

    particle = (f"  <Item>\n"
                f"   <Name>{part}</Name>\n"
                # ⛔ FxcTechnique SERBEST METIN DEGIL. Vanilla'daki 1.736
                #    particle rule'da yalniz su 6 deger gecer:
                #      RGBA_lit_soft (904) · RGBA_lit (425) · RGB_lit_soft (136)
                #      RGB_lit (75) · RGB_soft (70) · RGBA_soft (30)
                #    'default' HIC GECMEZ -- yazilirsa shader cozulmez ve
                #    efekt sessizce cizilmez. RGBA = alfali doku (bizimki),
                #    _soft = derinlik gecisi (yumusak kenar).
                f"   <FxcFile>ptfx_sprite</FxcFile>\n"
                f"   <FxcTechnique>RGBA_lit_soft</FxcTechnique>\n"
                f"{sabit}"
                f"{spawner.replace('{n}', '1')}{spawner.replace('{n}', '2')}"
                f"   <Behaviours>\n{dav}   </Behaviours>\n"
                f"   <ShaderVars>\n{shadervars}   </ShaderVars>\n"
                f"  </Item>\n")

    return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<ParticleEffectsList>\n"
            f" <Name>{ad}</Name>\n"
            f" <EffectRuleDictionary>\n{effect} </EffectRuleDictionary>\n"
            f" <EmitterRuleDictionary>\n{emitter} </EmitterRuleDictionary>\n"
            f" <ParticleRuleDictionary>\n{particle} </ParticleRuleDictionary>\n"
            " <DrawableDictionary />\n"
            " <TextureDictionary>\n"
            # Width/Height/MipLevels/Format ZORUNLU.
            # ⛔ Degerler DDS BASLIGINDAN okunur, sabit yazilmaz. Yanlis
            #    bildirilen mip sayisi/format sessizce bozuk doku uretir.
            #    Vanilla'daki 107 partikul dokusunun tamami DXT (DXT5 75 /
            #    DXT1 32), mip 4-9; sikistirilmamis ORNEK YOK.
            f"  <Item>\n   <Name>{doku}</Name>\n"
            f"   <Unk32 value=\"32\" />\n   <Usage>DIFFUSE</Usage>\n"
            f"   <UsageFlags>X8, X16, X64, X128, UNK24</UsageFlags>\n"
            f"   <ExtraFlags value=\"0\" />\n"
            f"   <Width value=\"{dgen}\" />\n   <Height value=\"{dyuk}\" />\n"
            f"   <MipLevels value=\"{dmip}\" />\n   <Format>{dfmt}</Format>\n"
            f"   <FileName>{doku}.dds</FileName>\n  </Item>\n"
            " </TextureDictionary>\n"
            "</ParticleEffectsList>\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ad", required=True, help="efekt/asset adi, orn. muto_spore")
    ap.add_argument("--doku", required=True, help="DDS dosya adi (uzantisiz)")
    ap.add_argument("--klasor", required=True, help="XML ve DDS'in birlikte durdugu klasor")
    ap.add_argument("--renk", nargs=3, type=float, default=[0.2, 0.9, 0.35],
                    metavar=("R", "G", "B"))
    ap.add_argument("--omur", type=float, default=2.5, help="parcacik omru (sn)")
    ap.add_argument("--boyut", type=float, default=0.35, help="parcacik boyutu (m)")
    ap.add_argument("--oran", type=float, default=8.0,
                    help="spawn orani (adet/sn). Vanilla medyani 5, %%75'lik dilim 16.")
    ap.add_argument("--hiz", type=float, default=1.2,
                    help="speedScalar: target domain'e dogru hiz carpani "
                         "(vanilla medyani 0.85). Yon degil, HIZ.")
    ap.add_argument("--yaricap", type=float, default=0.45,
                    help="dogum kuresi yaricapi (m) -- dar birakilirsa "
                         "parcaciklar ust uste binip tek opak top gibi gorunur")
    # ⛔ Yukselmeyi Velocity davranisi DEGIL, target domain konumu yapar.
    #    Vanilla emitter'larin %89,2'sinde Domain2 Z'si != 0, medyan +0.400.
    ap.add_argument("--yukselme", type=float, default=0.4,
                    help="target domain Z ofseti (m) -- parcaciklari yukari ceker")
    ap.add_argument("--renk2", nargs=3, type=float, default=None,
                    metavar=("R", "G", "B"),
                    help="olumdeki renk; verilmezse --renk sabit kalir")
    # --- gorunumu canlandiran davranislar (0 = kapali) ---
    ap.add_argument("--ivme", type=float, default=0.0,
                    help="Z ivmesi m/sn^2; yukselen duman icin pozitif")
    ap.add_argument("--donme", type=float, default=0.0,
                    help="donme hizi (derece/sn); statik lekeyi canlandirir")
    ap.add_argument("--gurultu", type=float, default=0.0,
                    help="turbulans; duman duz gitmez, kivrilir")
    ap.add_argument("--sekme", type=float, default=0.0,
                    help="Collision: 0=yapisir 1=tam seker")
    ap.add_argument("--isik", type=float, default=0.0,
                    help="parcacik GERCEK isik yayar (siddet)")
    ap.add_argument("--isik-menzil", type=float, default=3.0, help="isik menzili (m)")
    ap.add_argument("--parlama", type=float, default=0.0,
                    help="emissive: kendinden isikli parlama")
    ap.add_argument("--alfa", type=float, default=1.0,
                    help="tepe opaklik 0..1; yogun efektte dusur")
    # ⛔ Kare sayisi DOKUYLA tutarli olmali: izgara kare (sqrt) varsayiliyor.
    ap.add_argument("--sheet", type=int, default=1, metavar="KARE",
                    help="sprite sheet kare sayisi (16 = 4x4). 1 = animasyon yok")
    ap.add_argument("--animhiz", type=float, default=0.0,
                    help="cirpma hizi; 0 = motor varsayilani")
    # AnimateTexture'in anlami cozulmemis iki alani. Vanilla dagilimi:
    #   C8: 1 x476 · 0 x251 · 2 x5 · 4 x1        (C4>0 olan kurallarda)
    #   CC: 0x01010100 x367 baskin; 0x01000100 / 0x01000000 / 0x01010000
    # Ikisi de AYNI doku icin degisiyor, yani izgarayi kodlamiyorlar --
    # ama varsayilan olarak BASKIN kombinasyon yazilir.
    ap.add_argument("--animc8", type=int, default=1, help="AnimateTexture C8")
    ap.add_argument("--animcc", default="0x1010100", help="AnimateTexture CC")
    a = ap.parse_args()

    dds = os.path.join(a.klasor, a.doku + ".dds")
    if not os.path.exists(dds):
        sys.exit(f"HATA: {dds} yok.\n"
                 f"  Once uret: python make_dds.py \"{dds}\" --desen yumusak")

    # ⛔ Boyut/mip/format DDS BASLIGINDAN okunur, tahmin edilmez.
    #    XML'de bildirilen deger dosyayla uyusmazsa doku sessizce bozulur.
    import struct
    with open(dds, "rb") as fh:
        bas = fh.read(128)
    _, _, dyuk, dgen, _, _, dmip = struct.unpack("<7I", bas[4:32])
    dmip = max(1, dmip)
    fourcc = bas[84:88]
    dfmt = {b"DXT1": "D3DFMT_DXT1", b"DXT3": "D3DFMT_DXT3",
            b"DXT5": "D3DFMT_DXT5"}.get(fourcc, "D3DFMT_A8R8G8B8")
    if dfmt == "D3DFMT_A8R8G8B8":
        print("[!] UYARI: doku sikistirilmamis. Vanilla'daki 107 partikul "
              "dokusunun tamami DXT -- oyunda reddedilebilir.")
    if a.sheet > 1:
        import math as _m
        k = _m.isqrt(a.sheet)
        if k * k != a.sheet:
            sys.exit(f"HATA: --sheet {a.sheet} tam kare degil. Izgara kare "
                     f"olmali (4/9/16/25/36...).")
        # ⛔ IZGARANIN DOKUYU TAM BOLMESI GEREKMEZ - bu sart YANLISTI ve
        #    zincirin tamamini bozdu. Vanilla `ptfx_smoke_wispy_anim`
        #    1024x1024 uzerinde 7x7'dir: 1024/7 = 146.29. Motor UV uzayinda
        #    1/k adimlarla orneklter, piksel hizasi aramaz. Bu yanlis sart
        #    yuzunden 36 kare reddedildi ve 64 kareye (8x8) gecildi -> asagiya bak.
        if dgen % k or dyuk % k:
            print(f"[i] not: {dgen}x{dyuk} dokuda {k}x{k} izgara tam bolunmuyor "
                  f"(hucre {dgen/k:.2f}px). Vanilla'da da boyle -- sorun degil.")

        # ⛔ KARE SAYISI VANILLA BANDINI ASMAMALI. core.ypt'te 781
        #    AnimateTexture davranisi olculdu: `Unknown_C4h` **maks 49**,
        #    yani en fazla 50 kare; C4 > 63 olan kural SIFIR. 64 kare (C4=63)
        #    denendi ve oyunda motor izgarayi HIC uygulamadi -- her sprite
        #    8x8 sayfanin TAMAMINI tek karede cizdi. Belirti "animasyon
        #    yavas/donuk" degil, "kucuk goruntulerden olusan bir izgara".
        #    Guvenli tavan olculmus vanilla bandidir: 36 (6x6) ya da 49 (7x7).
        if a.sheet > 49:
            sys.exit(f"HATA: --sheet {a.sheet} vanilla bandinin disinda "
                     f"(olculen maks 50 kare / C4=49). Motor izgarayi "
                     f"uygulamaz ve sayfanin tamamini tek karede cizer. "
                     f"36 (6x6) ya da 49 (7x7) kullan.")
        print(f"[i] sheet: {k}x{k} = {a.sheet} kare, hucre {dgen/k:.1f}x{dyuk/k:.1f}px "
              f"-> UnknownC4={a.sheet-1}")
    dbayrak = DOKU_BAYRAK.get((dgen, dyuk))
    if dbayrak is None:
        dbayrak = DOKU_BAYRAK[(512, 512)]
        print(f"[!] UYARI: {dgen}x{dyuk} icin olculmus UsageFlags yok, "
              f"512x512'ninki kullanildi -- dogrulanmadi.")
    print(f"[i] doku: {dgen}x{dyuk} {dfmt} mip={dmip}  bayrak={dbayrak}")
    xml = uret_xml(a.ad, a.doku, a.renk, a.omur, a.boyut, a.oran, a.hiz,
                   a.yaricap, dgen, dyuk, dmip, dfmt, a.yukselme, a.alfa,
                   a.sheet, a.animhiz, dbayrak, a.renk2,
                   a.ivme, a.donme, a.gurultu, a.sekme,
                   a.isik, a.isik_menzil, a.parlama,
                   anim_c8=a.animc8, anim_cc=a.animcc)

    # KENDI CIKTIINI DOGRULA: ayristirilamayan XML oyunda sessizce yuklenmez
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(xml)
    except ET.ParseError as e:
        sys.exit(f"HATA: uretilen XML ayristirilamiyor: {e}")

    yol = os.path.join(a.klasor, f"{a.ad}.ypt.xml")
    with open(yol, "w", encoding="utf-8", newline="\n") as f:
        f.write(xml)
    print(f"[+] {yol}  ({len(xml)} karakter)")
    print(f"[+] efekt={a.ad}  doku={a.doku}  renk={a.renk}  omur={a.omur}s "
          f"boyut={a.boyut}m oran={a.oran}/s")
    print("\nSiradaki: CodeWalker ile binary'ye cevir "
          "(XmlYpt.GetYpt + Save) -- DDS ayni klasorde olmali.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
