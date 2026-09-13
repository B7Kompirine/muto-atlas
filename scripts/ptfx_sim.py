#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_sim.py — bir `.ypt` efektini SIMULE edip animasyonlu GIF uretir.

⛔ NE OLDUGU KONUSUNDA NET OL: bu motorun kendisi DEGIL, motorun
   belgelenmis alan anlamlarini oynatan bir MODEL. RAGE Tools da ayni seyi
   yapiyor (shader yorumu: "The CPU sim evaluates size / colour / rotation
   from the asset's own keyframe curves"). Guclu bir vekil, kesin kanit
   degil -- son soz oyunda.

   Ama dosya seviyesi denetimin yakalayamadigi seyi yakalar: "71/71 zincir
   saglam" derken oyunda 38 efekt gorunmuyordu. Bu simulasyon o hatayi
   ekranda gosterirdi.

Oynatilan alanlar (hepsi bu oturumda olculdu):
  ptxCreationDomain:m_sizeOuterKFP  -> parcaciklarin dogdugu hacim (m)
  ptxTargetDomain:m_positionKFP     -> yon x mesafe (omur boyunca alinan yol)
  ptxu_Acceleration:m_xyzMinKFP     -> ivme (m/s^2)
  ptxu_Dampening:m_xyzMinKFP        -> surtunme (0..1, saniyede kalan oran)
  ptxu_Size:m_whdMinKFP x sizeScalar -> parcacik boyu (m)
  ptxu_Colour:m_rgbaMinKFP          -> renk + ALFA ZARFI (omur boyunca)
  m_spawnRateOverTimeKFP / m_particleLifeKFP -> oran ve omur

Kullanim:
  python ptfx_sim.py <ypt.xml> <efekt_adi> --cikti out.gif
  python ptfx_sim.py <ypt.xml> --hepsi --klasor gifler/
"""
from __future__ import annotations

import argparse
import io
import math
import os
import random
import re
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptfx_kalite_kapisi import bloklari, kfp, kfp_govde, zarf  # noqa: E402


def v3(blok, ad, vars=(0.0, 0.0, 0.0)):
    g = kfp_govde(blok, ad)
    if g is None:
        return list(vars)
    v = re.findall(r"<(?:Red|Green|Blue)ChannelColour value=\"([-0-9.eE]+)\"", g)
    return [float(x) for x in v[:3]] if len(v) >= 3 else list(vars)


def renk_rgb(blok):
    g = kfp_govde(blok, "ptxu_Colour:m_rgbaMinKFP")
    if g is None:
        return (1.0, 1.0, 1.0)
    v = re.findall(r"<RedChannelColour value=\"([-0-9.eE]+)\" />\s*"
                   r"<GreenChannelColour value=\"([-0-9.eE]+)\" />\s*"
                   r"<BlueChannelColour value=\"([-0-9.eE]+)\" />", g)
    return tuple(float(x) for x in v[0]) if v else (1.0, 1.0, 1.0)


def egri_deger(zarfi, t):
    """(zaman, deger) listesinden t anindaki degeri lineer interpolasyonla."""
    if not zarfi:
        return 1.0
    if t <= zarfi[0][0]:
        return zarfi[0][1]
    for i in range(1, len(zarfi)):
        if t <= zarfi[i][0]:
            t0, v0 = zarfi[i - 1]
            t1, v1 = zarfi[i]
            f = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
            return v0 + (v1 - v0) * f
    return zarfi[-1][1]


class Katman:
    """Tek bir emitter+particle cifti. Cok emitterli efekt bunlardan olusur."""

    def __init__(self, emb, prb, xml_yolu, gecikme=0.0, olcek=1.0):
        self.em, self.pr = emb, prb
        self.gecikme, self.katolcek = gecikme, olcek

        r = kfp(self.em, "m_spawnRateOverTimeKFP") or (10.0, 10.0)
        l = kfp(self.em, "m_particleLifeKFP") or (2.0, 2.0)
        sc = kfp(self.em, "m_sizeScalarKFP") or (100.0, 100.0)
        self.oran = (r[0] + r[1]) / 2.0
        self.omur = (l[0], l[1])
        self.dogus = v3(self.em, "ptxCreationDomain:m_sizeOuterKFP", (0.2,) * 3)
        self.hedef = v3(self.em, "ptxTargetDomain:m_positionKFP", (0, 0, 0.5))
        self.hedef_boy = v3(self.em, "ptxTargetDomain:m_sizeOuterKFP", (0, 0, 0))
        self.ivme = v3(self.pr, "ptxu_Acceleration:m_xyzMinKFP", (0, 0, 0))
        self.surt = v3(self.pr, "ptxu_Dampening:m_xyzMinKFP", (0, 0, 0))
        w = v3(self.pr, "ptxu_Size:m_whdMinKFP", (0.3,) * 3)
        self.boy = max(w) * max(sc[1], 1.0) / 100.0 * self.katolcek
        # ⛔ TEK ATIM: emitter'daki `Unknown628`. 1 ise emisyon bir kez olur,
        #    0 ise surer. Modellemezsek carpma efekti sonsuza kadar puskurur.
        import re as _re
        m628 = _re.search(r"<Unknown628 value=\"([-0-9.]+)\" />", self.em)
        self.tek_atim = bool(m628 and float(m628.group(1)) >= 1.0)
        self.zarf = zarf(self.pr, "ptxu_Colour:m_rgbaMinKFP") or [(0, 1), (1, 0)]
        self.renk = renk_rgb(self.pr)

        # doku: <FileName> ya da <Name>.dds, XML'in yanindan
        d = re.search(r"<TextureName>([^<]+)</TextureName>", self.pr)
        dad = d.group(1) if d else None
        self.sprite = None
        if dad:
            for aday in (dad + ".dds", dad + ".png"):
                p = os.path.join(os.path.dirname(xml_yolu), aday)
                if os.path.exists(p):
                    self.sprite = Image.open(p).convert("RGBA")
                    break


class Efekt:
    """Bir efekt = bir veya daha cok KATMAN.

    ⛔ Vanilla'nin %74'u cok emitterli; katman gecikmesi `Unknown10`,
       katman boyut carpani `ParticleScale` alanindan gelir.
    """

    def __init__(self, xml_yolu, ad):
        s = io.open(xml_yolu, encoding="utf-8", errors="replace").read()
        blok = None
        for a, b in bloklari(s, "EffectRuleDictionary"):
            if a == ad:
                blok = b
                break
        if blok is None:
            raise KeyError("efekt yok: %s" % ad)
        em = dict(bloklari(s, "EmitterRuleDictionary"))
        pr = dict(bloklari(s, "ParticleRuleDictionary"))
        i, j = blok.find("<EventEmitters>"), blok.find("</EventEmitters>")
        g = blok[i:j] if i >= 0 else blok
        cift = re.findall(
            r"<EmitterRule>([^<]*)</EmitterRule>\s*"
            r"<ParticleRule>([^<]*)</ParticleRule>\s*"
            r"<Unknown10 value=\"([-0-9.eE]+)\" />.*?"
            r"<ParticleScale value=\"([-0-9.eE]+)\"", g, re.S)
        self.ad = ad
        self.katmanlar = []
        for e, p, gec, olc in cift:
            if e in em and p in pr:
                self.katmanlar.append(
                    Katman(em[e], pr[p], xml_yolu, float(gec), float(olc)))
        if not self.katmanlar:
            raise KeyError("%s: katman cozulemedi" % ad)

    def sim(self, sure=3.0, fps=20, tohum=1):
        birlesik = []
        for n, k in enumerate(self.katmanlar):
            kk = k.sim(sure, fps, tohum + n * 17)
            gk = int(k.gecikme * fps)
            for i in range(len(kk)):
                while len(birlesik) <= i:
                    birlesik.append([])
            for i, kare in enumerate(kk):
                hedef = i + gk
                if hedef < len(birlesik):
                    birlesik[hedef].extend((q, k) for q in kare)
        return birlesik

    @property
    def sprite(self):
        return self.katmanlar[0].sprite

    @property
    def renk(self):
        return self.katmanlar[0].renk

    @property
    def boy(self):
        return max(k.boy for k in self.katmanlar)

    @property
    def zarf(self):
        return self.katmanlar[0].zarf


def _katman_sim(self, sure=3.0, fps=20, tohum=1):
        """Kareler uretir: her kare [(x, y, z, boy, alfa)]."""
        rng = random.Random(tohum)
        dt = 1.0 / fps
        parcaciklar = []
        kareler = []
        birikim = 0.0
        n = int(sure * fps)
        for k in range(n):
            # tek atimda emisyon yalniz ilk 0.08 sn surer
            # ⚠ Tek atim penceresi MODEL: 0.25 sn. Motorun gercek
            #   semantigi olculmedi (`StartParticleFxNonLooped`
            #   efekti bir kez oynatir, suresini motor bilir).
            if not self.tek_atim or k * dt < 0.25:
                birikim += self.oran * dt
            while birikim >= 1.0:
                birikim -= 1.0
                p = [rng.uniform(-1, 1) * self.dogus[0] * 0.5,
                     rng.uniform(-1, 1) * self.dogus[1] * 0.5,
                     rng.uniform(-1, 1) * self.dogus[2] * 0.5]
                omr = rng.uniform(self.omur[0], self.omur[1]) or 1.0
                # hedef = omur boyunca alinacak yol -> baslangic hizi
                sap = [rng.uniform(-1, 1) * self.hedef_boy[i] * 0.5 for i in range(3)]
                hiz = [(self.hedef[i] + sap[i]) / omr for i in range(3)]
                parcaciklar.append({"p": p, "v": hiz, "t": 0.0, "omr": omr,
                                    "d": rng.uniform(0, math.tau)})
            kare = []
            for pt in parcaciklar:
                pt["t"] += dt
                for i in range(3):
                    pt["v"][i] += self.ivme[i] * dt
                    if self.surt[i] > 0:
                        pt["v"][i] *= max(0.0, 1.0 - self.surt[i] * dt)
                    pt["p"][i] += pt["v"][i] * dt
                f = pt["t"] / pt["omr"]
                if f <= 1.0:
                    kare.append((pt["p"][0], pt["p"][1], pt["p"][2],
                                 self.boy, egri_deger(self.zarf, f), pt["d"]))
            parcaciklar = [q for q in parcaciklar if q["t"] < q["omr"]]
            kareler.append(kare)
        return kareler



# ⛔ Baglamayi DOSYA SONUNA koyma: `main()` `raise SystemExit(main())`
#    ile once calisiyor ve o an `Katman.sim` henuz tanimsiz oluyor
#    (AttributeError). Tanimin hemen ardina bagla.
Katman.sim = _katman_sim

def ciz(kareler, efekt, coz=384, kamera_m=4.0):
    """Kareleri yandan bakan ortografik goruntuye cizer.

    ⚠ Her parcacik KENDI KATMANININ sprite ve rengini kullanir; cok
      emitterli efektte katmanlar farkli dokular tasir.
    """
    piks = coz / kamera_m          # piksel / metre
    ims = []
    zemin = int(coz * 0.78)
    for kare in kareler:
        im = Image.new("RGB", (coz, coz), (26, 27, 30))
        d = np.asarray(im).copy()
        d[zemin:zemin + 1, :] = (70, 72, 78)
        im = Image.fromarray(d)
        # arkadan one: y'ye gore sirala ki ortusme dogru olsun
        for (q, kat) in sorted(kare, key=lambda t: -t[0][1]):
            x, y, z, boy, alfa, don = q
            if alfa <= 0.01 or kat.sprite is None:
                continue
            px = int(coz * 0.5 + x * piks)
            py = int(zemin - z * piks)
            bp = max(2, int(boy * piks))
            if bp > coz * 3 or px < -bp or px > coz + bp:
                continue
            s2 = kat.sprite.resize((bp, bp), Image.LANCZOS)
            if don:
                s2 = s2.rotate(math.degrees(don), expand=False)
            a = np.asarray(s2).astype(np.float32) / 255.0
            a[..., 0] *= kat.renk[0]
            a[..., 1] *= kat.renk[1]
            a[..., 2] *= kat.renk[2]
            a[..., 3] *= alfa
            par = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGBA")
            im.paste(par, (px - bp // 2, py - bp // 2), par)
        ims.append(im)
    return ims


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xml")
    ap.add_argument("efekt", nargs="?")
    ap.add_argument("--cikti", default=None)
    ap.add_argument("--sure", type=float, default=3.0)
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--coz", type=int, default=384)
    ap.add_argument("--kamera", type=float, default=4.0, help="gorus genisligi (m)")
    a = ap.parse_args()

    e = Efekt(a.xml, a.efekt)
    kareler = e.sim(a.sure, a.fps)
    top = sum(len(k) for k in kareler)
    tepe = max(len(k) for k in kareler) if kareler else 0
    ims = ciz(kareler, e, a.coz, a.kamera)
    cikti = a.cikti or (e.ad + ".gif")
    ims[0].save(cikti, save_all=True, append_images=ims[1:],
                duration=int(1000 / a.fps), loop=0, optimize=True)
    print("%-26s %d katman  parcacik tepe %3d  boy %.2f m  -> %s"
          % (e.ad, len(e.katmanlar), tepe, e.boy, os.path.basename(cikti)))
    if tepe == 0:
        print("   ⛔ HIC PARCACIK YOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
