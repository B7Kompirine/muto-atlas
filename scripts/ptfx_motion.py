#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_motion.py — parcacigin HAREKETINI yazar (devralmaz).

⛔ NEDEN VAR: donorun hareketini oldugu gibi devralmak, o efekti yeni renk
   giydirmekten baska bir sey degildir. Gozun okudugu sey harekettir.
   Olculen uc vaka:

     · `cokme_tozu`  <- env_dust_devil_rural_lrg  : donorde `ptxAttractorDomain`
       var (dis 20.6 / ic 6.8). Attractor parcaciklari iceri-yukari sarmalar;
       oyunda HORTUM goruldu. Cunku donor bizzat bir toz seytani.
     · `bulasma_dalgasi` <- fire_extinguish : `ptxTargetDomain` 3.5 m yukariyi
       hedefliyor -- yangin sondurucu jeti. Halka spriteiyle halka fiskirtti.
     · `beton_kirilma` <- ent_ray_fam3_dust_motes : dogus hacmi **5x5x1 m**
       kutu. Kiymik carpma noktasindan degil, 5 metrelik alana sacilarak
       doguyor.

Olculen anlamlar (n=231 uygun donor):
   `ptxCreationDomain:m_sizeOuterKFP`  -> parcaciklarin DOGDUGU hacim
   `ptxTargetDomain:m_positionKFP`     -> yon x mesafe (hiz)
   `ptxu_Acceleration:m_xyzMin/MaxKFP` -> yercekimi / yukselis
   `ptxu_Dampening:m_xyzMin/MaxKFP`    -> surtunme
Ornekler: damla hedef [0,0,-4] ivme [0,0,-20] · zemin sisi hedef [0,0.3,0.01]
ivme [0,0,0] · kor hedef [0,0,0.1] · dusen enkaz hedef [0,0,-8].

Domain turleri: CreationDomain ve TargetDomain **%100** var; Attractor
yalnizca **%6** (14/231) -- hortum riski oradan gelir, silinir.
"""
from __future__ import annotations

import re

# ALFA keyframe'i: RGB + alfa birlikte. `KARE` yalnizca RGB yazar
# (hareket alanlari icin); zarf yaziminda alfa da gerekli.
KARE_A = ("       <Item>\n"
          "        <InterpolationInterval value=\"%g\" />\n"
          "        <KeyFrameMultiplier value=\"%g\" />\n"
          "        <RedChannelColour value=\"%g\" />\n"
          "        <GreenChannelColour value=\"%g\" />\n"
          "        <BlueChannelColour value=\"%g\" />\n"
          "        <AlphaChannelColour value=\"%g\" />\n"
          "       </Item>\n")

KARE = ("       <Item>\n"
        "        <InterpolationInterval value=\"0\" />\n"
        "        <KeyFrameMultiplier value=\"0\" />\n"
        "        <RedChannelColour value=\"%g\" />\n"
        "        <GreenChannelColour value=\"%g\" />\n"
        "        <BlueChannelColour value=\"%g\" />\n"
        "        <AlphaChannelColour value=\"0\" />\n"
        "       </Item>\n")


def kfp_yaz(blok, tam_ad, xyz):
    """Bir KFP'nin ilk keyframe'ini `xyz` yapar. (metin, yazildi_mi)

    ⛔ Alan BOS olabilir (`<Keyframes />`, kendi kapanan). O durumda
       `</Keyframes>` aranan desen yoktur; bunu gozden kacirmak bir tur
       boyunca KOMSU alanin degerini okutmustu. Burada bos hali de
       doldurulur -- yoksa hareket yazilamaz.
    """
    i = blok.find("<Name>%s</Name>" % tam_ad)
    if i < 0:
        return blok, False
    j = blok.find("<Name>", i + 6)
    son = j if j > 0 else len(blok)
    kesit = blok[i:son]
    yeni_kf = "<Keyframes>\n" + (KARE % tuple(xyz)) + "      </Keyframes>"
    if "<Keyframes />" in kesit:
        kesit2 = kesit.replace("<Keyframes />", yeni_kf, 1)
    elif "<Keyframes>" in kesit:
        kesit2 = re.sub(r"<Keyframes>.*?</Keyframes>", yeni_kf, kesit,
                        count=1, flags=re.S)
    else:
        return blok, False
    return blok[:i] + kesit2 + blok[son:], True


def domain_tipi_yaz(blok, indeks, tip):
    """`<DomainN><Type value="X" />` alanini degistirir."""
    d = "<Domain%d>" % indeks
    i = blok.find(d)
    if i < 0:
        return blok, False
    kesit = blok[i:i + 200]
    yeni = re.sub(r"<Type value=\"\w+\" />", "<Type value=\"%s\" />" % tip,
                  kesit, count=1)
    return blok[:i] + yeni + blok[i + 200:], yeni != kesit


def attractor_sil(blok):
    """Attractor domain'i etkisizlestirir -- hortum/sarmal buradan gelir.

    ⛔ Dugumu SILME: `<DomainN>` yuvalari konumsaldir, birini kaldirmak
       kalanlarin indekslerini kaydirir. Yaricapi sifirlamak hem guvenli
       hem yeterli (cekim alani yok olur).
    """
    n = 0
    for ad in ("ptxAttractorDomain:m_sizeOuterKFP",
               "ptxAttractorDomain:m_sizeInnerKFP"):
        blok, ok = kfp_yaz(blok, ad, (0.0, 0.0, 0.0))
        n += 1 if ok else 0
    return blok, n


# hareket sozlugu anahtari -> (hangi blok, tam KFP adi)
#   "em" = emitter rule govdesi, "pr" = particle rule govdesi
# ⛔ BOYUT DA YAZILMALI. Hareket yazildi ama boyut donorden birakildi ve
#    donorler birbiriyle uyumsuz cikti: olculdu, 56 ailenin **38'i** 0.2 m
#    altinda kaldi (besi tam 0.000) -- oyunda hicbir sey gorunmedi; ote
#    yandan `kan_sisi` 9.7 m ile ekrani kapladi. Vanilla bandi:
#    whdMin p50=1.0 p95=7.0 · whdMax p50=1.6 p95=9.9; whdMin'i sifir olan
#    kural yalnizca **68 / 1724 (%3,9)**.
#
# ⚠ `m_sizeScalarKFP` YUZDEDIR (notr 100). Boyutu whd ile yazip scalar'i
#   100'e sabitlemek gerekir; yoksa donorun scalar'i (0.44'ten 949'a)
#   yazdigimiz whd'yi carpitir.
ALANLAR = {
    "boy":     ("pr", "ptxu_Size:m_whdMinKFP"),
    "boy_maks": ("pr", "ptxu_Size:m_whdMaxKFP"),
    "dogus":   ("em", "ptxCreationDomain:m_sizeOuterKFP"),
    "dogus_ic": ("em", "ptxCreationDomain:m_sizeInnerKFP"),
    "hedef":   ("em", "ptxTargetDomain:m_positionKFP"),
    "hedef_boy": ("em", "ptxTargetDomain:m_sizeOuterKFP"),
    "ivme":    ("pr", "ptxu_Acceleration:m_xyzMinKFP"),
    "ivme_maks": ("pr", "ptxu_Acceleration:m_xyzMaxKFP"),
    "surtunme": ("pr", "ptxu_Dampening:m_xyzMinKFP"),
    "surtunme_maks": ("pr", "ptxu_Dampening:m_xyzMaxKFP"),
}


def _bolge(s, sozluk):
    """Bir sozlugun belgedeki (bas, son) araligi."""
    i = s.find("<%s>" % sozluk)
    j = s.find("</%s>" % sozluk)
    return (i, j) if i >= 0 and j > i else (0, len(s))


def _bolgede_yaz(s, sozluk, tam_ad, xyz):
    """KFP'yi YALNIZ o sozlugun icinde arar ve yazar.

    ⛔ BELGE GENELINDE ARAMA. `ptxEmitterRule:m_sizeScalarKFP` belgede IKI
       yerde gecer: EffectRule'un `EventEmitters/UnknownData/Unknown10`
       override listesinde ve asil EmitterRule'da. Ilk bulunana yazmak
       override listesini degistirir, gercek deger DOKUNULMADAN kalir --
       build "sizeScalar -> 100" der ama dosyada donorun 6.41'i durur ve
       parcacik 0.003 m cikip gorunmez. Bolgeye kilitle.
    """
    i, j = _bolge(s, sozluk)
    kesit, ok = kfp_yaz(s[i:j], tam_ad, xyz)
    return s[:i] + kesit + s[j:], ok


def uygula_belge(s, hareket):
    """Hareketi TEK emitterli/particle'li bir `.ypt.xml` belgesine yazar.

    (Cok emitterli bir belgede bunu KULLANMA.)
    """
    notlar = []
    if hareket.get("attractor_sil"):
        _i, _j = _bolge(s, "EmitterRuleDictionary")
        _k, n = attractor_sil(s[_i:_j])
        s = s[:_i] + _k + s[_j:]
        if n:
            notlar.append("attractor sifirlandi")
    if "zarf" in hareket:
        # ⛔ ALFA ZARFI DA YAZILABILMELI. `zarf_onar` yalniz BOZUK zarfi
        #    (tek keyframe / sonda pop) duzeltir; donorun gecerli ama
        #    ailemize UYMAYAN zarfina dokunmaz. Olculdu: kivilcim donoru
        #    `water_splash_veh_out` 0.75 sn'de alfayi 0.06'ya dusuruyor --
        #    su sicramasi icin dogru, kivilcim icin erken. Kivilcim omrunun
        #    cogunda PARLAK kalip sonda sonmeli.
        nok = hareket["zarf"]          # [(t, alfa), ...]
        for ad in ("ptxu_Colour:m_rgbaMinKFP", "ptxu_Colour:m_rgbaMaxKFP"):
            i0, j0 = _bolge(s, "ParticleRuleDictionary")
            kesit = s[i0:j0]
            i = kesit.find("<Name>%s</Name>" % ad)
            if i < 0:
                continue
            j = kesit.find("<Name>", i + 6)
            alt = kesit[i:j if j > 0 else len(kesit)]
            m = re.search(r"<RedChannelColour value=\"([-0-9.eE]+)\" />\s*"
                          r"<GreenChannelColour value=\"([-0-9.eE]+)\" />\s*"
                          r"<BlueChannelColour value=\"([-0-9.eE]+)\" />", alt)
            r, g, b = (float(x) for x in m.groups()) if m else (1.0, 1.0, 1.0)
            kare = ""
            for n2, (t, a2) in enumerate(nok):
                mult = 0.0 if n2 == 0 else 1.0 / max(t - nok[n2 - 1][0], 1e-4)
                kare += (KARE_A % (t, mult, r, g, b, a2))
            yeni_alt = re.sub(r"<Keyframes\s*/>|<Keyframes>.*?</Keyframes>",
                              "<Keyframes>\n" + kare + "      </Keyframes>",
                              alt, count=1, flags=re.S)
            kesit = kesit[:i] + yeni_alt + kesit[(j if j > 0 else len(kesit)):]
            s = s[:i0] + kesit + s[j0:]
        notlar.append("zarf yazildi: %d kare, tepe %.2f"
                      % (len(nok), max(a2 for _, a2 in nok)))

    if "tek_atim" in hareket:
        # ⛔ SUREKLI mi TEK ATIM mi -- emitter'daki `Unknown628`.
        #    Olculdu (n=964): `bul_*` mermi carpmalarinin **48/48'i**,
        #    `exp_*` patlamalarin **%80'i** 1; buna karsilik `fire_*`
        #    0/38, `wheel_*` 0/58, `env_*` 0/27. Yani 1 = tek atim/burst,
        #    0 = surekli. Carpma efekti 0 kalirsa sonsuza kadar puskurur.
        i0, j0 = _bolge(s, "EmitterRuleDictionary")
        kesit = s[i0:j0]
        yeni_k, n = re.subn(r"<Unknown628 value=\"[-0-9.]+\" />",
                            '<Unknown628 value="%d" />'
                            % (1 if hareket["tek_atim"] else 0), kesit)
        s = s[:i0] + yeni_k + s[j0:]
        notlar.append("tek_atim=%s (%d emitter)"
                      % (bool(hareket["tek_atim"]), n))
    if "tip" in hareket:
        s, ok = domain_tipi_yaz(s, 1, hareket["tip"])
        if ok:
            notlar.append("dogus tipi -> %s" % hareket["tip"])
    if "boy" in hareket:
        # scalar'i notre cek ki whd gercek metre olsun
        s, ok = _bolgede_yaz(s, "EmitterRuleDictionary",
                             "ptxEmitterRule:m_sizeScalarKFP",
                             (100.0, 100.0, 0.0))
        if ok:
            notlar.append("sizeScalar -> 100 (notr)")
        else:
            # ⛔ Bazi donorde `m_sizeScalarKFP` YOK (olculdu: fly_swarm,
            #    moths_swarm). O zaman scalar donorde ne ise oyle kalir ve
            #    yazdigimiz whd onunla CARPILIR -- `sinek_bulutu` 0.003 m
            #    cikti, gorunmez. Telafi: whd'yi 100/scalar ile buyut.
            import re as _re
            g = None
            i = s.find("<Name>ptxEmitterRule:m_sizeScalarKFP</Name>")
            if i >= 0:
                j = s.find("<Name>", i + 6)
                k2 = _re.search(r"<RedChannelColour value=\"([-0-9.eE]+)\"",
                                s[i:j if j > 0 else len(s)])
                if k2:
                    g = float(k2.group(1))
            if g and g > 1e-6:
                kat = 100.0 / g
                hareket = dict(hareket)
                hareket["boy"] = tuple(x * kat for x in hareket["boy"])
                notlar.append("sizeScalar yazilamadi (%.3g) -> boy x%.1f telafi"
                              % (g, kat))
            else:
                notlar.append("sizeScalar yazilamadi ⛔")
    SOZ = {"em": "EmitterRuleDictionary", "pr": "ParticleRuleDictionary"}
    for anah, (nere, tam) in ALANLAR.items():
        if anah not in hareket:
            continue
        v = hareket[anah]
        s, ok = _bolgede_yaz(s, SOZ[nere], tam, v)
        notlar.append("%s=[%g,%g,%g]%s"
                      % (anah, v[0], v[1], v[2], "" if ok else " ⛔YAZILAMADI"))
        ikiz = anah + "_maks"
        if not anah.endswith("_maks") and ikiz in ALANLAR and ikiz not in hareket:
            # ⚠ Vanilla'da whdMax / whdMin ~1.6 (p50 1.0 / 1.6). Ayni degeri
            #   yazmak butun parcaciklari ayni boyda yapar -- mekanik durur.
            kat = 1.6 if anah == "boy" else 1.0
            s, _ = _bolgede_yaz(s, SOZ[ALANLAR[ikiz][0]], ALANLAR[ikiz][1],
                                tuple(x * kat for x in v))
    return s, notlar


def uygula(emitter, particle, hareket):
    """Hareket spec'ini emitter+particle bloklarina yazar.

    hareket: {"dogus": (x,y,z), "hedef": (x,y,z), "ivme": (x,y,z),
              "surtunme": (x,y,z), "tip": "Sphere", "attractor_sil": True}
    Doner: (emitter, particle, notlar)
    """
    notlar = []
    if hareket.get("attractor_sil"):
        emitter, n = attractor_sil(emitter)
        if n:
            notlar.append("attractor sifirlandi (%d alan)" % n)
    if "tip" in hareket:
        emitter, ok = domain_tipi_yaz(emitter, 1, hareket["tip"])
        if ok:
            notlar.append("dogus hacmi tipi -> %s" % hareket["tip"])

    for anah, (nere, tam) in ALANLAR.items():
        if anah not in hareket:
            continue
        v = hareket[anah]
        if nere == "em":
            emitter, ok = kfp_yaz(emitter, tam, v)
        else:
            particle, ok = kfp_yaz(particle, tam, v)
        notlar.append("%s = [%g, %g, %g]%s"
                      % (anah, v[0], v[1], v[2], "" if ok else "  ⛔ YAZILAMADI"))
        # ⚠ ivme/surtunme min-maks CIFTIDIR; yalniz min yazmak arali
        #    donorun eski maks'iyla birakir. Maks acikca verilmediyse esitle.
        ikiz = anah + "_maks"
        if nere == "pr" and not anah.endswith("_maks") and ikiz not in hareket \
                and ikiz in ALANLAR:
            particle, _ = kfp_yaz(particle, ALANLAR[ikiz][1], v)
    return emitter, particle, notlar
