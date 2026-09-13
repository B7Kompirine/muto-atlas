#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_kalite_kapisi.py — uretilen `.ypt`yi VANILLA'ya karsi denetler.

Soru: "gereksiz fazla / gereksiz az efekt" var mi? Bu goz karari verilemez,
olculur. Iki ayri olcut kullanilir:

  1. DONOR SAPMASI (kesin referans). Uretilen efekt donorunun kendisiyle
     alan alan karsilastirilir. Spec'te override YAZILMAYAN bir alan
     degismisse bu KAZA'dir -> IHLAL. Yazilmis olan degisiklik beklenendir.

  2. VANILLA BANDI (populasyon referansi). Es zamanli parcacik yuku
     `yuk = ort(spawnRate) x ort(particleLife)` butun vanilla emitterlerin
     dagilimina konur. p05'in altinda "gereksiz az", p95'in ustunde
     "gereksiz fazla" demektir.

⛔ KFP kanal anlami olculdu: `RedChannelColour` = MIN, `GreenChannelColour`
   = MAX. Tek bir sayi okumak (ilk kanal) araligin ust ucunu gormezden
   gelir; seyrek gorunen bir emitter aslinda 3x daha yogun olabilir.
⛔ `m_sizeScalarKFP` YUZDEDIR (notr 100). 1.0 yazmak boyutu %1'e dusurur;
   kapi 1.0 civari bir sizeScalar gordugunde uyarir.

Kullanim:
  python ptfx_kalite_kapisi.py --grup virus_ambiyans
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptfx_katalog_kur import GRUPLAR, VANILLA, CIKTI  # noqa: E402
from ptfx_hareket import ALANLAR  # noqa: E402

# olculecek emitter alanlari -> (spec override anahtari, insan adi)
ALAN = {
    "m_spawnRateOverTimeKFP": ("oran", "spawn orani /sn"),
    "m_particleLifeKFP": ("omur", "parcacik omru sn"),
    "m_sizeScalarKFP": ("boyut", "boyut olcegi %"),
}


def kfp_govde(blok, tam_ad):
    """Bir KFP'nin YALNIZ KENDI <Keyframes> govdesini verir.

    ⛔ `<Name>X</Name>(.*?)</Keyframes>` YAZMA. Alan bossa XML'de
       `<Keyframes />` (kendi kapanan) durur; `</Keyframes>` aranan desen
       orada YOKTUR ve regex bir SONRAKI alanin govdesini yakalar. Olculdu:
       `ent_amb_fbi_smoke_land_hvy`in `ptxTargetDomain:m_positionKFP` alani
       bos, okuma `m_rotationKFP`e kayip konum diye **[90, -30, 0]** verdi --
       konum degil derece. Sessiz ve tamamen inandirici bir yanlis okuma.

    Dogrusu: once alanin KENDI sinirini kes (bir sonraki <Name>'e kadar),
    sonra icinde <Keyframes> ara.
    """
    i = blok.find("<Name>%s</Name>" % tam_ad)
    if i < 0:
        return None
    j = blok.find("<Name>", i + 6)
    kesit = blok[i:j if j > 0 else len(blok)]
    m = re.search(r"<Keyframes>(.*?)</Keyframes>", kesit, re.S)
    return m.group(1) if m else None


def kfp(blok, ad):
    """Bir emitter blogundan KFP'nin (min, max) degerini cikarir."""
    g = kfp_govde(blok, "ptxEmitterRule:%s" % ad)
    if g is None:
        return None
    k = re.findall(r"<(?:Red|Green)ChannelColour value=\"([-0-9.eE]+)\"", g)
    if len(k) < 2:
        return None
    return (float(k[0]), float(k[1]))


def bloklari(xml, sozluk):
    """Bir sozlugun icindeki her kurali (ad, blok) olarak verir."""
    i = xml.find("<%s>" % sozluk)
    j = xml.find("</%s>" % sozluk)
    if i < 0:
        return
    govde = xml[i:j]
    # ⛔ Ust duzey <Item> sinirini regex ile bolmek ic ice <Item>lere takilir.
    #    Emitterin kendi <Name> tepe noktalarindan bol: her emitter tam bir
    #    ad ile baslar ve bir sonrakine kadar surer.
    tepe = [m.start() for m in re.finditer(r"\n   <Name>[^<]+</Name>", govde)]
    for n, s in enumerate(tepe):
        e = tepe[n + 1] if n + 1 < len(tepe) else len(govde)
        blok = govde[s:e]
        ad = re.search(r"<Name>([^<]+)</Name>", blok).group(1)
        yield ad, blok


def zarf(blok, ad):
    """Bir KFP'nin (zaman, alfa) zarfini verir. zaman 0..1 = parcacik omru.

    ⛔ `.ypt`de "animasyon" budur. Sayfa dilimlemesi calismadigi icin
       (bkz. referans §1e) tek kare sprite kullaniyoruz; hareket hissi
       TAMAMEN bu egrilerden ve donusten geliyor. Egri duzse parcacik
       canli degil, yapistirma gorunur.
    """
    g = kfp_govde(blok, ad)
    if g is None:
        return None
    it = re.findall(r"<InterpolationInterval value=\"([-0-9.eE]+)\" />.*?"
                    r"<AlphaChannelColour value=\"([-0-9.eE]+)\" />", g, re.S)
    return [(float(a), float(b)) for a, b in it]


def yuk(rate, life):
    """Es zamanli parcacik sayisi ~ ort(oran) x ort(omur)."""
    if not rate or not life:
        return None
    return ((rate[0] + rate[1]) / 2.0) * ((life[0] + life[1]) / 2.0)


def yuzde(dizi, p):
    d = sorted(dizi)
    if not d:
        return 0.0
    k = (len(d) - 1) * p / 100.0
    a, b = int(k), min(int(k) + 1, len(d) - 1)
    return d[a] + (d[b] - d[a]) * (k - a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grup", default="virus_ambiyans")
    a = ap.parse_args()

    print("vanilla okunuyor...")
    van = io.open(VANILLA, encoding="utf-8", errors="replace").read()
    vem = {}
    yukler = []
    for ad, blok in bloklari(van, "EmitterRuleDictionary"):
        vem[ad] = blok
        y = yuk(kfp(blok, "m_spawnRateOverTimeKFP"), kfp(blok, "m_particleLifeKFP"))
        if y and y > 0:
            yukler.append(y)
    vefekt = {}
    for ad, blok in bloklari(van, "EffectRuleDictionary"):
        e = re.findall(r"<EmitterRule>([^<]*)</EmitterRule>", blok)
        if len(e) == 1:
            vefekt[ad] = e[0]
    p05, p50, p95 = yuzde(yukler, 5), yuzde(yukler, 50), yuzde(yukler, 95)
    print("vanilla emitter: %d | es zamanli yuk p05=%.0f  medyan=%.0f  p95=%.0f\n"
          % (len(vem), p05, p50, p95))

    basli, ihlal = 0, 0
    for kayit in GRUPLAR[a.grup]:
        aile, donor, sprite, renk, ovr, neden = kayit[:6]
        hareket = kayit[6] if len(kayit) > 6 else {}
        ad = "muto_" + aile
        yol = os.path.join(CIKTI, ad + ".ypt.xml")
        if not os.path.exists(yol):
            print("  DOSYA YOK %-18s" % aile)
            ihlal += 1
            continue
        s = io.open(yol, encoding="utf-8", errors="replace").read()
        bloklar = list(bloklari(s, "EmitterRuleDictionary"))
        if len(bloklar) != 1:
            print("  IHLAL  %-18s emitter sayisi %d (1 olmali)" % (aile, len(bloklar)))
            ihlal += 1
            continue
        bizim = bloklar[0][1]

        # ⛔ Emitter adi efekt adiyla AYNI DEGILDIR (`fire_extinguish` bu yuzden
        #    bulunamadi). Bag `<EmitterRule>ad</EmitterRule>` alanindadir --
        #    ada gore tahmin etmek yerine bagi oku.
        dblok = vem.get(vefekt.get(donor)) if donor in vefekt else None

        notlar, kotu = [], False

        # --- 1. donor sapmasi -------------------------------------------------
        if dblok:
            for alan, (anah, insan) in ALAN.items():
                bz, dn = kfp(bizim, alan), kfp(dblok, alan)
                if not bz or not dn:
                    continue
                fark = abs(bz[0] - dn[0]) > 1e-4 or abs(bz[1] - dn[1]) > 1e-4
                # ⚠ `boy` hareket spec'inde varsa `sizeScalar` KASTEN 100'e
                #   cekilir (yuzde olcegi notr olmali ki whd gercek metre
                #   olsun). Bu bildirilmis bir degisikliktir, kaza degil.
                if anah == "boyut" and "boy" in (hareket or {}):
                    continue
                if fark and anah not in ovr:
                    notlar.append("KAZA %s: %.4g-%.4g -> %.4g-%.4g (override yok)"
                                  % (insan, dn[0], dn[1], bz[0], bz[1]))
                    kotu = True
                elif not fark and anah in ovr:
                    notlar.append("ETKISIZ %s: override yazildi, deger degismedi" % insan)
                    kotu = True
                elif fark:
                    # gerekce ile yon tutuyor mu, gozle dogrulanabilsin
                    notlar.append("%s: %.4g-%.4g -> %.4g-%.4g"
                                  % (insan, dn[0], dn[1], bz[0], bz[1]))
        else:
            notlar.append("donor emitteri bulunamadi -- sapma olculemedi")
            kotu = True

        # --- 2. vanilla bandi -------------------------------------------------
        r, l = kfp(bizim, "m_spawnRateOverTimeKFP"), kfp(bizim, "m_particleLifeKFP")
        y = yuk(r, l)
        if y is None:
            notlar.append("oran/omur okunamadi")
            kotu = True
        else:
            # ⛔ Bandi KOSULSUZ uygulama. Vanilla'nin kendi efektlerinin
            #    %5'i tanim geregi p95'in ustundedir; donorun degerini
            #    koruyup bandi ihlal etmek "vanilla gibi" olmanin ta
            #    kendisidir. Band yalnizca BIZIM yuku donorden uzaga
            #    tasiyip tasimadigimizi olcmeli.
            dy = yuk(kfp(dblok, "m_spawnRateOverTimeKFP"),
                     kfp(dblok, "m_particleLifeKFP")) if dblok else None
            donora_yakin = dy and abs(y - dy) <= 0.02 * max(dy, 1.0)
            if donora_yakin:
                pass
            elif y > p95:
                notlar.append("GEREKSIZ FAZLA: yuk %.0f > p95 %.0f (donor %.0f)"
                              % (y, p95, dy or 0))
                kotu = True
            elif y < p05:
                notlar.append("GEREKSIZ AZ: yuk %.2f < p05 %.2f (donor %.0f)"
                              % (y, p05, dy or 0))
                kotu = True

        # --- 3. sessiz kiranlar -----------------------------------------------
        c4 = re.findall(r"<UnknownC4 value=\"(\d+)\"", s)
        if any(x != "0" for x in c4):
            notlar.append("UnknownC4=%s (sayfa dilimlemesi custom ypt'de calismiyor)"
                          % ",".join(c4))
            kotu = True
        tek = re.findall(r"<FxcTechnique>(\w+)</FxcTechnique>", s)
        if any(not t.startswith("RGBA") for t in tek):
            notlar.append("teknik %s alfayi yok sayar" % ",".join(tek))
            kotu = True
        dok = re.findall(r"<TextureName>([^<]+)</TextureName>", s)
        if dok != [ad]:
            notlar.append("doku adi %s (beklenen %s)" % (dok, ad))
            kotu = True
        # ⛔ Bu kural yalniz BIZ boyutu yazdiysak calisir. Donorun kendi
        #    degeri tanim geregi vanilla-dogrudur: `ent_amb_fbi_cinder`
        #    0.4437 tasir ve vanilla sizeScalar'in %2'si 1.5'in altindadir
        #    (n=1901). Donor degerini "hata" diye raporlamak yanlis alarmdir.
        sz = kfp(bizim, "m_sizeScalarKFP")
        if "boyut" in ovr and sz and 0 < sz[1] <= 1.5:
            notlar.append("sizeScalar %.4g -- YUZDE olcegi, notr 100" % sz[1])
            kotu = True

        # --- 4. ANIMASYON ZARFI ------------------------------------------------
        # Olculdu (n=1735 vanilla particle rule):
        #   t=1'de alfa 0'a inen  -> %88,2   (inmeyen POPLAR: pat diye kaybolur)
        #   t=0'da alfa 0'dan baslayan -> %44,7 (yani ani belirme NORMAL)
        #   keyframe sayisi medyan 3; %9,3'u tek keyframe = sabit alfa
        # ⛔ MIN ve MAX zarflarinin IKISINE birden bak. Bir tur boyunca yalniz
        #    min denetlendi ve `kagit_savrulma` ile `moloz_yagmuru`nun MAX
        #    zarfi 0.8'de biterek popladigi halde kapidan "gecti" aldi.
        prb = s[s.find("<ParticleRuleDictionary>"):]
        for kfpad, etiket in (("ptxu_Colour:m_rgbaMinKFP", "min"),
                              ("ptxu_Colour:m_rgbaMaxKFP", "max")):
            e = zarf(prb, kfpad)
            if not e:
                notlar.append("alfa zarfi (%s) okunamadi" % etiket)
                kotu = True
                continue
            # ⛔ MAX zarfi TAMAMEN SIFIR olabilir ve bu vanilla'da GECERLI
            #    bir kalip: olculdu, 1733 kuralin **87'si (%5,0)** boyle --
            #    `ent_amb_tnl_bubbles_lge` gibi oyunda calisan efektler
            #    dahil. Max sifirsa aralik yok demektir, min gecerlidir.
            #    Bunu "gorunmez/animasyonsuz" diye raporlamak yanlis alarm.
            if etiket == "max" and max(a for _, a in e) <= 1e-6:
                continue
            if len(e) < 2:
                notlar.append("ANIMASYON YOK (%s): alfa tek keyframe (sabit) -- "
                              "vanilla'nin %%90,7'si en az 2 tasiyor" % etiket)
                kotu = True
            elif e[-1][1] > 0.02:
                notlar.append("POP (%s): t=1'de alfa %.3g -- parcacik pat diye "
                              "kaybolur; vanilla'nin %%88,2'si 0'a iner"
                              % (etiket, e[-1][1]))
                kotu = True
            tp = max(a for _, a in e)
            if tp < 0.05:
                notlar.append("GORUNMEZ (%s): tepe alfa %.3g (vanilla p05 = 0.1)"
                              % (etiket, tp))
                kotu = True

        # --- 5. HAREKET GERI OKUMA --------------------------------------------
        # ⛔ "Yazdim" yeterli degil; dosyadan GERI OKU. Hareket bu hattaki
        #    en pahali hataydi (donorun hareketini devralmak = donoru yeni
        #    renkle yayinlamak) ve sessizce geri gelebilir.
        for anah, deger in (hareket or {}).items():
            if anah not in ALANLAR:
                continue
            g = kfp_govde(s, ALANLAR[anah][1])
            if g is None:
                notlar.append("HAREKET YOK: %s alani dosyada bulunamadi" % anah)
                kotu = True
                continue
            v = re.findall(r"<(?:Red|Green|Blue)ChannelColour value=\"([-0-9.eE]+)\"", g)
            if len(v) < 3:
                notlar.append("HAREKET okunamadi: %s" % anah)
                kotu = True
                continue
            okunan = tuple(float(x) for x in v[:3])
            if any(abs(okunan[i] - deger[i]) > 1e-3 for i in range(3)):
                notlar.append("HAREKET SAPMASI %s: yazilan %s, dosyada %s"
                              % (anah, tuple(deger), okunan))
                kotu = True
        if hareket.get("attractor_sil"):
            g = kfp_govde(s, "ptxAttractorDomain:m_sizeOuterKFP")
            if g and any(abs(float(x)) > 1e-6 for x in
                         re.findall(r"<(?:Red|Green|Blue)ChannelColour value=\"([-0-9.eE]+)\"", g)):
                notlar.append("ATTRACTOR HALA VAR -- hortum riski surer")
                kotu = True

        if kotu:
            ihlal += 1
        else:
            basli += 1
        bas = "IHLAL " if kotu else "gecti "
        if r and l:
            print("  %s %-18s yuk %6.0f   oran %.4g-%.4g /sn   omur %.4g-%.4g sn"
                  % (bas, aile, y or 0, r[0], r[1], l[0], l[1]))
        else:
            print("  %s %-18s (oran/omur okunamadi)" % (bas, aile))
        for n in notlar:
            print("           - %s" % n)

    print("\ngecen: %d / %d" % (basli, len(GRUPLAR[a.grup])))
    return 0 if not ihlal else 1


if __name__ == "__main__":
    raise SystemExit(main())
