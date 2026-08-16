#!/usr/bin/env python3
"""ycd_oku.py — bir .ycd'yi kare kare kemik donusumlerine acar.

NEDEN VAR
=========
Bir klibin gercekte hangi kemigi, hangi karede, ne kadar surdugunu bilmek
icin .ycd'nin kanallari burada cozulur -- oyuna girmeden.

OLCULEN, TAHMIN EDILMEYEN
=========================
* **CodeWalker XML'e cevirirken NICEMLEMEYI ZATEN COZER.** `QuantizeFloat`
  kanalinin `<Values>` alani kare kare DUZ float tasir; `Quantum`/`Offset`
  bilgi amaclidir. Kendi kuantum cozucunu yazma -- gereksiz ve hatali olur.
* **`CachedQuaternion` bir kanal DEGIL, ISARETCIDIR.** Degeri yoktur,
  `<QuatIndex>` tasir: dusurulen bilesenin hangisi oldugunu soyler. Kalan
  uc bilesen oteki kanallardadir; eksik olan `sqrt(1 - Σ)` ile kurulur,
  isareti tipin adindan gelir (`...1` -> +, `...2` -> -). Bunu ayirmadan
  okumak yaw'i **180 derece** kaydirir.
* **`IndirectQuantizeFloat`'ta `<Frames>` kare listesi DEGIL**, `<Values>`
  tablosuna INDEKS dizisidir.
* Bir track tek bir `StaticVector3`/`StaticQuaternion` kanali olabilir
  (tumu bir arada) ya da ayri skaler kanallara bolunmus olabilir. Ikisi de
  ayni sozlukte gecer; tek bicim varsaymak sessizce yanlis okur.
* Kanal bloklarinin sirasi `<BoneIds>` sirasidir: i. blok, i. (tag, track)
  ciftine aittir. Track 0 = konum, 1 = donus, 2 = olcek, 5/6 = mover.

Olculen kanal dagilimi (tek sozlukte, 71 animasyon):
StaticQuaternion 2717 · StaticFloat 1246 · StaticVector3 575 ·
CachedQuaternion1 345 · QuantizeFloat 314 · IndirectQuantizeFloat 2

KULLANIM
========
    import ycd_oku
    d = ycd_oku.oku("kapi.ycd")
    d["klipler"]                  # ad -> {anim, kare, sure}
    d["animasyonlar"][h]["kemikler"][tag][track]   # [kare][bilesen]
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_xml import kok_oku  # noqa: E402

TRACK_ADI = {0: "konum", 1: "donus", 2: "olcek", 5: "mover_konum", 6: "mover_donus"}


def _v(el, ad="value", d=0.0):
    if el is None:
        return d
    try:
        return float(el.get(ad, d))
    except (TypeError, ValueError):
        return d


def _sayilar(el):
    if el is None or not (el.text or "").strip():
        return []
    return [float(x) for x in el.text.split()]


def _kanal(ch, kare):
    """Bir kanali (tip, veri) olarak coz.

    Doner: ("skaler", [kare basina float])  |  ("vec3", [[x,y,z], ...])
           ("quat", [[x,y,z,w], ...])       |  ("isaretci", (quat_index, isaret))
    """
    t = ch.find("Type").get("value")

    if t == "StaticFloat":
        return "skaler", [_v(ch.find("Value"))] * kare
    if t == "StaticVector3":
        e = ch.find("Value")
        return "vec3", [[_v(e, "x"), _v(e, "y"), _v(e, "z")]] * kare
    if t == "StaticQuaternion":
        e = ch.find("Value")
        return "quat", [[_v(e, "x"), _v(e, "y"), _v(e, "z"), _v(e, "w", 1.0)]] * kare
    if t == "QuantizeFloat":
        # <Values> ZATEN cozulmus: Quantum/Offset'i tekrar uygulama.
        v = _sayilar(ch.find("Values"))
        return "skaler", (v + [v[-1] if v else 0.0] * kare)[:kare]
    if t == "IndirectQuantizeFloat":
        # <Frames> bir INDEKS tablosudur, kare listesi degil.
        v = _sayilar(ch.find("Values"))
        idx = [int(x) for x in _sayilar(ch.find("Frames"))]
        if not v:
            return "skaler", [0.0] * kare
        out = [v[i] if 0 <= i < len(v) else v[-1] for i in idx]
        return "skaler", (out + [out[-1] if out else 0.0] * kare)[:kare]
    if t and t.startswith("CachedQuaternion"):
        # Deger tasimaz; hangi bilesenin dusuruldugunu soyler.
        isaret = -1.0 if t.endswith("2") else 1.0
        return "isaretci", (int(_v(ch.find("QuatIndex"))), isaret)
    if t and t.startswith("Linear"):
        v = _sayilar(ch.find("Values"))
        return "skaler", (v + [v[-1] if v else 0.0] * kare)[:kare]

    raise ValueError("unknown channel type: %s" % t)


def _blok_coz(blok, kare):
    """Bir kemik blogunu kare basina bilesen listesine cevirir."""
    ch_el = blok.find("Channels")
    chs = list(ch_el) if ch_el is not None else []
    if not chs:
        return None
    cozum = [_kanal(c, kare) for c in chs]

    # Tek parca halinde gelen tipler
    for tip, veri in cozum:
        if tip in ("vec3", "quat") and len(cozum) == 1:
            return veri

    isaretci = next((v for t, v in cozum if t == "isaretci"), None)
    skalerler = [v for t, v in cozum if t == "skaler"]

    if isaretci is not None:
        # 3 skaler + isaretci: eksik bileseni sqrt(1-Σ) ile kur.
        qi, isaret = isaretci
        out = []
        for f in range(kare):
            p = [s[f] for s in skalerler[:3]]
            kalan = max(0.0, 1.0 - sum(x * x for x in p))
            eksik = isaret * math.sqrt(kalan)
            q = p[:]
            q.insert(min(max(qi, 0), 3), eksik)
            out.append(q[:4] if len(q) >= 4 else q + [1.0])
        return out

    if len(skalerler) >= 4:
        return [[s[f] for s in skalerler[:4]] for f in range(kare)]
    if len(skalerler) == 3:
        return [[s[f] for s in skalerler[:3]] for f in range(kare)]
    if len(skalerler) == 1:
        return [[skalerler[0][f]] for f in range(kare)]
    # Karisik durum (orn. vec3 + skaler): bilesenleri sirayla dizip birlestir
    duz = []
    for tip, veri in cozum:
        if tip == "skaler":
            duz.append(veri)
        elif tip == "vec3":
            for k in range(3):
                duz.append([v[k] for v in veri])
        elif tip == "quat":
            for k in range(4):
                duz.append([v[k] for v in veri])
    return [[s[f] for s in duz] for f in range(kare)] if duz else None


def oku(path):
    kok, hata = kok_oku(path)
    if hata:
        raise RuntimeError(hata)

    klipler = {}
    kl = kok.find("Clips")          # ⛔ `.//Clips` DEGIL
    for c in (kl if kl is not None else []):
        ad = (c.findtext("Name") or c.findtext("Hash") or "").strip()
        kisa = ad.rsplit("/", 1)[-1]
        if kisa.endswith(".clip"):
            kisa = kisa[:-5]
        tip = (c.find("Type").get("value") if c.find("Type") is not None else "Animation")
        # Iki klip tipi vardir ve ikisi de yaygin: `Animation` tek animasyona
        # baglanir, `AnimationList` bir LISTE tasir (vanilla movement
        # kliplerinin %86,7'si boyledir). Tek bicim varsaymak yariyi dusurur.
        refs = []
        if tip == "AnimationList":
            al = c.find("Animations")
            for it in (al if al is not None else []):
                refs.append({"anim": (it.findtext("AnimationHash") or "").strip(),
                             "baslangic": _v(it.find("StartTime")),
                             "bitis": _v(it.find("EndTime")),
                             "hiz": _v(it.find("Rate"), "value", 1.0)})
        else:
            refs.append({"anim": (c.findtext("AnimationHash") or "").strip(),
                         "baslangic": _v(c.find("StartTime")),
                         "bitis": _v(c.find("EndTime")),
                         "hiz": _v(c.find("Rate"), "value", 1.0)})
        klipler[kisa] = {"tip": tip, "refler": refs,
                         "anim": refs[0]["anim"] if refs else "",
                         "baslangic": refs[0]["baslangic"] if refs else 0.0,
                         "bitis": refs[0]["bitis"] if refs else 0.0,
                         "hiz": refs[0]["hiz"] if refs else 1.0}

    animler = {}
    # ⛔ `.//Animations` KLIBIN ICINDEKI referans listesini de yakalar ve
    #    "kare=1, kemik=0" gibi sessizce bos bir animasyon uretir. Olculdu.
    an = kok.find("Animations")
    for a in (an if an is not None else []):
        h = (a.findtext("Hash") or "").strip()
        kare = int(_v(a.find("FrameCount"), "value", 1)) or 1
        sure = _v(a.find("Duration"), "value", kare / 30.0)
        # i. blok <-> i. (tag, track): sira sozlesmedir, ad eslesmesi yoktur.
        cift = [(int(_v(b.find("BoneId"))), int(_v(b.find("Track"))))
                for b in (a.find("BoneIds") if a.find("BoneIds") is not None else [])]
        kemikler = {}
        i = 0
        sqs = a.find("Sequences")
        for sq in (sqs if sqs is not None else []):
            sd = sq.find("SequenceData")
            for blok in (sd if sd is not None else []):
                if i >= len(cift):
                    break
                tag, track = cift[i]
                i += 1
                veri = _blok_coz(blok, kare)
                if veri is None:
                    continue
                kemikler.setdefault(tag, {})[track] = veri
        animler[h] = {"kare": kare, "sure": sure, "fps": (kare / sure) if sure else 30.0,
                      "kemikler": kemikler}

    return {"klipler": klipler, "animasyonlar": animler,
            "ad": os.path.splitext(os.path.basename(path))[0]}


if __name__ == "__main__":
    d = oku(sys.argv[1])
    print("%s: %d clips, %d animations" % (d["ad"], len(d["klipler"]), len(d["animasyonlar"])))
    ara = sys.argv[2] if len(sys.argv) > 2 else None
    for ad, k in d["klipler"].items():
        if ara and ara not in ad:
            continue
        a = d["animasyonlar"].get(k["anim"])
        if not a:
            print("  %-34s -> NO ANIMATION (%s)" % (ad, k["anim"]))
            continue
        hareketli = sum(1 for t in a["kemikler"].values()
                        for v in t.values() if len({tuple(x) for x in v}) > 1)
        print("  %-34s frames=%-4d dur=%.2fs bones=%-3d moving channels=%d"
              % (ad, a["kare"], a["sure"], len(a["kemikler"]), hareketli))
