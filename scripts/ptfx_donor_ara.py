#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_donor_ara.py — transplant'a UYGUN vanilla donor bulur.

Bir donorun ise yaramasi icin uc sart var ve ucu de sessizce kirilir:

  1. TEK EMITTERLI olmali. `ypt_transplant.py` cok emitterli efekti
     reddeder (964 efektin yalniz ~251'i tek emitterli).
  2. SPRITE tabanli olmali. Mesh parcaciklarda (`ParticleBehaviourModel`)
     `<TextureName>` yoktur -- `ent_amb_falling_leaves_*` bu yuzden
     kullanilamadi.
  3. Emitteri bulunabilmeli. Bag `<EmitterRule>` alanindadir; emitter adi
     efekt adiyla AYNI DEGILDIR.

Kullanim:
  python ptfx_donor_ara.py bang_concrete bul_glass scrape_metal
  python ptfx_donor_ara.py --ara concrete --ara glass      # alt dizge
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptfx_kalite_kapisi import bloklari, kfp  # noqa: E402
from ptfx_katalog_kur import VANILLA  # noqa: E402


def yukle():
    van = io.open(VANILLA, encoding="utf-8", errors="replace").read()
    em = dict(bloklari(van, "EmitterRuleDictionary"))
    pr = dict(bloklari(van, "ParticleRuleDictionary"))
    # ⛔ `<ParticleRule>` EMITTER blogunda DEGIL, EFEKT blogundadir.
    #    Emitterde aramak her efekti "MESH parcacik, doku yok" diye
    #    raporladi -- oysa ayni donorden dokulu bir efekt uretilmisti.
    #    Emitter blogunda hic `*Rule` etiketi yok (olculdu: bos kume).
    ef = {}
    for ad, blok in bloklari(van, "EffectRuleDictionary"):
        ef[ad] = (re.findall(r"<EmitterRule>([^<]*)</EmitterRule>", blok),
                  re.findall(r"<ParticleRule>([^<]*)</ParticleRule>", blok))
    return van, ef, em, pr


def incele(ad, ef, em, pr):
    """(uygun_mu, aciklama) dondurur."""
    if ad not in ef:
        return False, "efekt yok"
    e, p = ef[ad]
    if len(e) != 1:
        return False, "%d emitterli (tek emitterli olmali)" % len(e)
    blok = em.get(e[0])
    if blok is None:
        return False, "emitter '%s' sozlukte yok" % e[0]
    dok = None
    for x in p:
        pb = pr.get(x, "")
        d = re.findall(r"<TextureName>([^<]+)</TextureName>", pb)
        if d:
            dok = d[0]
            break
    if dok is None:
        return False, "MESH parcacik (doku yok) -- transplant edilemez"
    # ⛔ BIRDEN COK DOKULU donor kullanma. Olculdu: 231 uygun donorun 6'si
    #    boyle. `liquid_splash_petrol` `ptfx_gloop_n` (NORMAL MAP) +
    #    `ptfx_gloop` (renk) ister; transplant tek sprite'i IKISINE birden
    #    yazar ve shader yanlis isiklanir. Kapi bunu "doku adi ['x','x']"
    #    diye yakaladi. Cogunun tek dokulu bir ikizi var
    #    (petrol -> `liquid_splash_water`, ayni omur bandi).
    hepsi = []
    for x in p:
        hepsi += re.findall(r"<TextureName>([^<]+)</TextureName>", pr.get(x, ""))
    if len(hepsi) > 1:
        return False, "COK DOKULU (%s) -- tek sprite ikisine birden yazilir" % (
            ", ".join(hepsi))
    r, l, s = (kfp(blok, "m_spawnRateOverTimeKFP"),
               kfp(blok, "m_particleLifeKFP"),
               kfp(blok, "m_sizeScalarKFP"))
    def g(v):
        return "%.4g-%.4g" % v if v else "?"
    return True, "doku %-28s oran %-13s omur %-13s boyut %s" % (
        dok, g(r), g(l), g(s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("adlar", nargs="*")
    ap.add_argument("--ara", action="append", default=[],
                    help="alt dizge ile tara (uygun olanlari listeler)")
    ap.add_argument("--limit", type=int, default=14)
    a = ap.parse_args()

    van, ef, em, pr = yukle()
    print("vanilla: %d efekt, %d emitter, %d particle rule\n"
          % (len(ef), len(em), len(pr)))

    for ad in a.adlar:
        ok, aciklama = incele(ad, ef, em, pr)
        print("  %s %-34s %s" % ("UYGUN" if ok else "  -  ", ad, aciklama))

    for terim in a.ara:
        print("\n--- '%s' iceren UYGUN donorler ---" % terim)
        n = 0
        for ad in sorted(ef):
            if terim.lower() not in ad.lower():
                continue
            ok, aciklama = incele(ad, ef, em, pr)
            if ok:
                print("  %-34s %s" % (ad, aciklama))
                n += 1
                if n >= a.limit:
                    print("  ... (limit %d)" % a.limit)
                    break
        if n == 0:
            print("  (uygun donor yok)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
