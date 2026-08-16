#!/usr/bin/env python3
"""sahne.py — coklu obje + animasyon + isik sahnesi.

NEDEN VAR
=========
Isik editoru tek dosyayi gosteriyordu. Harita/prop isi tek dosyadan ibaret
degil: birden fazla obje, birbirine gore konum, ve animasyon. Bunlarin
hepsini oyuna girmeden gormek icin sahne kutugu burada.

OLCULEN, TAHMIN EDILMEYEN
=========================
* **Animasyon oynatilacaksa geometri PISIRILMEZ.** Pisirilmis vertex'e
  animasyon uygulanirsa kemik donusumu IKI KEZ girer ve model daginir.
  `light_sahne.oku(bake=False)` vertex'i kemik uzayinda birakir; dogrulandi:
  bind pozunda skinning uygulanmis sonuc, pisirilmis sonuca **0.000e+00 m**
  farkla esit.
* **Animasyon YEREL donusumu degistirir, dunya matrisini degil.** Her karede
  yerel TRS animasyondan alinir, dunya hiyerarsiden yeniden kurulur.
* **Klip kemige TAG ile baglanir, isimle degil.** Tag tutmazsa kanal sessizce
  duser; hata cikmaz, o kemik kimildamaz.
* **Prop animasyonlarinda hareket cogu zaman MOVER'dadir** (track 5/6), kemik
  kanallarinda degil: obje dunyada yol alir. Olculdu (`bomb_thermal_charge`):
  track 0/1 sabit, 5/6 242 kare boyunca degisiyor.

KULLANIM
========
    assetdb.py sahne --ekle prop_a.ydr --ekle prop_b.yft
    assetdb.py sahne --dosya sahnem.json
    assetdb.py sahne --dosya sahnem.json --ymap out.ymap --ad muto_sahne
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import light_sahne  # noqa: E402
import ycd_oku  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
YMAP_PS = os.path.join(HERE, "sahne_ymap.ps1")


def bos():
    return {"ad": "sahne", "lodDist": 160, "objeler": []}


def yukle(path):
    if not path or not os.path.isfile(path):
        return bos()
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    d.setdefault("objeler", [])
    d.setdefault("lodDist", 160)
    d.setdefault("ad", os.path.splitext(os.path.basename(path))[0])
    return d


def kaydet(sahne, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sahne, fh, indent=1, ensure_ascii=False)
    return path


def obje_ekle(sahne, model, konum=None, donus=None, anim=None):
    sahne["objeler"].append({
        "model": os.path.abspath(model),
        "arketip": os.path.splitext(os.path.basename(model))[0],
        "konum": konum or [0.0, 0.0, 0.0],
        "donus": donus or [0.0, 0.0, 0.0, 1.0],   # quaternion
        "anim": anim,                              # {"ycd": yol, "klip": ad}
    })
    return sahne


# ------------------------------------------------------------------- cozme

def _anim_coz(anim):
    """{"ycd":..., "klip":...} -> editorun bekledigi kanal sozlugu."""
    if not anim or not anim.get("ycd"):
        return None
    yol = anim["ycd"]
    if not os.path.isfile(yol):
        return {"hata": "no such .ycd: %s" % yol}
    d = ycd_oku.oku(yol)
    klip_ad = anim.get("klip")
    if not klip_ad:
        klip_ad = next(iter(d["klipler"]), None)
    k = d["klipler"].get(klip_ad)
    if not k:
        return {"hata": "no such clip: %s (available: %s)"
                % (klip_ad, list(d["klipler"])[:6])}
    a = d["animasyonlar"].get(k["anim"])
    if not a:
        return {"hata": "clip '%s' has no matching animation (%s)" % (klip_ad, k["anim"])}
    return {"ycd": os.path.basename(yol), "klip": klip_ad,
            "klipler": sorted(d["klipler"]),
            "kare": a["kare"], "sure": a["sure"], "fps": a["fps"],
            # tag -> track -> [kare][bilesen]; JSON anahtarlari metin olur
            "kemikler": {str(t): {str(tr): v for tr, v in trs.items()}
                         for t, trs in a["kemikler"].items()}}


def coz(sahne, maks_ucgen=None):
    """Editorun tuketecegi tam sahne: geometri + kemik + isik + animasyon."""
    objeler = []
    for o in sahne["objeler"]:
        if not os.path.isfile(o["model"]):
            objeler.append({"ad": o.get("arketip", "?"), "hata":
                            "no such model: %s" % o["model"], "konum": o["konum"],
                            "donus": o["donus"]})
            continue
        kw = {"bake": False}
        if maks_ucgen:
            kw["maks_ucgen"] = maks_ucgen
        g = light_sahne.oku(o["model"], **kw)
        g["konum"] = o["konum"]
        g["donus"] = o["donus"]
        g["arketip"] = o.get("arketip") or g["ad"]
        g["model"] = o["model"]
        g["anim"] = _anim_coz(o.get("anim"))
        objeler.append(g)
    return {"ad": sahne.get("ad", "sahne"), "lodDist": sahne.get("lodDist", 160),
            "objeler": objeler}


def _yaricap(o):
    b = o.get("bbox")
    if not b:
        return 2.0
    return max(2.0, max(abs(b["maks"][i] - b["min"][i]) for i in range(3)) / 2.0
               if isinstance(b, dict) and "maks" in b else
               max(abs(b["max"][i] - b["min"][i]) for i in range(3)) / 2.0)


def ymap_yaz(sahne, cikti, ad=None):
    """sahne_ymap.ps1'e devreder; o da yazdiktan sonra GERI OKUYUP dogrular."""
    ad = ad or sahne.get("ad", "muto_sahne")
    cozulmus = coz(sahne, maks_ucgen=1)      # geometri gerekmez, sadece bbox
    ent = []
    for o, ham in zip(cozulmus["objeler"], sahne["objeler"]):
        ent.append({"arketip": ham.get("arketip") or o.get("ad"),
                    "konum": ham["konum"], "donus": ham["donus"],
                    "yaricap": _yaricap(o)})
    gecici = os.path.join(os.path.dirname(os.path.abspath(cikti)),
                          "_sahne_ymap_girdi.json")
    with open(gecici, "w", encoding="utf-8") as fh:
        json.dump({"objeler": ent, "lodDist": sahne.get("lodDist", 160)}, fh)
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-File", YMAP_PS, "-Json", gecici,
                            "-YmapName", ad, "-OutFile", os.path.abspath(cikti)],
                           capture_output=True, text=True)
    finally:
        try:
            os.remove(gecici)
        except OSError:
            pass
    cik = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        raise RuntimeError("could not write the ymap:\n%s" % cik.strip()[:600])
    return cik.strip()


# --------------------------------------------------------------------- CLI

def calistir(args):
    dosya = getattr(args, "dosya", None)
    sahne = yukle(dosya)

    for m in (getattr(args, "ekle", None) or []):
        if not os.path.isfile(m):
            print("ERROR: no such model: %s" % m, file=sys.stderr)
            return 2
        obje_ekle(sahne, m)

    for spec in (getattr(args, "anim", None) or []):
        # bicim: <ycd yolu>[:<klip adi>]  -- surucu harfi ':' ile karisir,
        # o yuzden SON ':' bakilir ve solunda dosya varsa bolunur.
        ycd, klip = spec, None
        if ":" in spec[2:]:
            k = spec.rfind(":")
            if os.path.isfile(spec[:k]):
                ycd, klip = spec[:k], spec[k + 1:]
        if not os.path.isfile(ycd):
            print("ERROR: no such .ycd: %s" % ycd, file=sys.stderr)
            return 2
        if not sahne["objeler"]:
            print("ERROR: add an object first with --add", file=sys.stderr)
            return 2
        sahne["objeler"][-1]["anim"] = {"ycd": os.path.abspath(ycd), "klip": klip}

    if getattr(args, "sil", None) is not None:
        i = args.sil
        if not 0 <= i < len(sahne["objeler"]):
            print("ERROR: no such object index: %d" % i, file=sys.stderr)
            return 2
        sahne["objeler"].pop(i)

    if not sahne["objeler"]:
        print("ERROR: the scene is empty. Add one with --add <model.ydr>.", file=sys.stderr)
        return 2

    if dosya:
        kaydet(sahne, dosya)

    if getattr(args, "ymap", None):
        try:
            print(ymap_yaz(sahne, args.ymap, getattr(args, "ad", None)))
        except RuntimeError as e:
            print("ERROR: %s" % e, file=sys.stderr)
            return 2
        print("\n  The asset changed: LEAVE the server and rejoin - a restart is not enough.")
        return 0

    # varsayilan: ozet
    c = coz(sahne)
    print("%s - %d object(s)" % (c["ad"], len(c["objeler"])))
    for i, o in enumerate(c["objeler"]):
        if o.get("hata"):
            print("  #%d %-24s ERROR: %s" % (i, o.get("ad", "?"), o["hata"]))
            continue
        a = o.get("anim")
        anim = ("anim=%s %df/%.2fs" % (a["klip"], a["kare"], a["sure"])
                if a and not a.get("hata") else
                ("ANIM ERROR: %s" % a["hata"] if a else "-"))
        print("  #%d %-24s %5d tris  %2d bones  %d light(s)  %s"
              % (i, o["arketip"], len(o["mesh"]["idx"]) // 3, len(o["kemikler"]),
                 len(o["isiklar"]), anim))
    if dosya:
        print("\n  saved: %s" % dosya)
    return 0
