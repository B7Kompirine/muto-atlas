#!/usr/bin/env python3
"""light.py — bir .ydr/.yft icindeki gomulu isiklari okur ve COZER.

NEDEN VAR
=========
Isik parametreleri sihirli sayilarla dolu: `TimeFlags = 15728703` bir sayi
degil, "saat 20'den 05'e kadar yanar" demektir. Bu sayiyi kopyalayip gecmek
en sik yapilan hata; isik yanlis saatte yanar ya da hic yanmaz ve sebebi
dosyaya bakinca gorunmez.
    "Sihirli sayiyi kopyalama, coz."

Isiklar `<kok>/Lights` altindadir -- hem Drawable (.ydr) hem Fragment (.yft)
kokunde AYNI yerde. Fragment'te `Drawable/Lights` DEGILDIR (olculdu:
prop_worklight_01a.yft -> Fragment/Lights=1, Fragment/Drawable/Lights yok).

KULLANIM
========
    python assetdb.py light <dosya.ydr|.yft|.xml>
    python assetdb.py light <dosya> --ham        (cozumsuz, ham alanlar)
    python assetdb.py light --tablo              (olculen vanilla referansi)
"""
from __future__ import annotations

import collections
import gzip
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_xml import kok_oku  # noqa: E402

# --- OLCULEN VANILLA REFERANSI ------------------------------------------------
# Referans GOMULU DEGILDIR; data/lights.tsv.gz katmanindan CANLI hesaplanir
# (build_lights.ps1 uretir, GTA'nin butun .ydr/.yft/.ydd dosyalarini tarar).
#
# Katman kurulu degilse uydurma bir aralik dondurmek yerine EXIT_NOLAYER
# verilir: "olculmus referans" diye sunulan sey gercekten olculmus olmali.
# Dagilima BAGLI OLMAYAN denetimler (TimeFlags 0, Intensity 0, Falloff 0,
# ters koni) katman olmadan da calisir -- onlar mantik, istatistik degil.
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LIGHTS = os.path.join(DATA, "lights.tsv.gz")

# Dagilim raporlanan sayisal alanlar: TSV sutun adi -> ekranda gorunen ad.
SAYISAL = [
    ("intensity", "Intensity"),
    ("falloff", "Falloff"),
    ("falloffExp", "FalloffExponent"),
    ("coneInner", "ConeInnerAngle"),
    ("coneOuter", "ConeOuterAngle"),
    ("coronaSize", "CoronaSize"),
    ("coronaIntensity", "CoronaIntensity"),
    ("volumeIntensity", "VolumeIntensity"),
]

SAAT_BITLERI = 24


def _f(el, ad="value"):
    if el is None:
        return None
    try:
        return float(el.get(ad))
    except (TypeError, ValueError):
        return None


def _i(el, ad="value"):
    v = _f(el, ad)
    return None if v is None else int(v)


def _v3(el):
    if el is None:
        return None
    try:
        return tuple(float(el.get(k)) for k in "xyz")
    except (TypeError, ValueError):
        return None


def _rgb(el):
    if el is None:
        return None
    try:
        return tuple(int(el.get(k)) for k in "rgb")
    except (TypeError, ValueError):
        return None


def isiklari_oku(kok):
    """<kok>/Lights/Item listesi -> sozluk listesi. Lights dugumu yoksa None."""
    L = kok.find("Lights")
    if L is None:
        return None
    out = []
    for it in L:
        out.append({
            "Type": (it.findtext("Type") or "?").strip(),
            "Position": _v3(it.find("Position")),
            "Colour": _rgb(it.find("Colour")),
            "Intensity": _f(it.find("Intensity")),
            "Falloff": _f(it.find("Falloff")),
            "FalloffExponent": _f(it.find("FalloffExponent")),
            "ConeInnerAngle": _f(it.find("ConeInnerAngle")),
            "ConeOuterAngle": _f(it.find("ConeOuterAngle")),
            "CoronaSize": _f(it.find("CoronaSize")),
            "CoronaIntensity": _f(it.find("CoronaIntensity")),
            "VolumeIntensity": _f(it.find("VolumeIntensity")),
            "VolumeSizeScale": _f(it.find("VolumeSizeScale")),
            "Flags": _i(it.find("Flags")),
            "TimeFlags": _i(it.find("TimeFlags")),
            "BoneId": _i(it.find("BoneId")),
            "GroupId": _i(it.find("GroupId")),
            "Flashiness": _i(it.find("Flashiness")),
            "ShadowBlur": _i(it.find("ShadowBlur")),
            "Direction": _v3(it.find("Direction")),
            "Extent": _v3(it.find("Extent")),
            "ProjectedTextureHash": (it.findtext("ProjectedTextureHash") or "").strip(),
        })
    return out


def aktif_saatler(timeflags):
    if timeflags is None:
        return []
    return [h for h in range(SAAT_BITLERI) if (timeflags >> h) & 1]


def saat_bloklari(saatler):
    """Dairesel bitisik saat bloklari. 20..5 tek blok olarak dondurulur."""
    s = sorted(saatler)
    if not s:
        return []
    if len(s) == SAAT_BITLERI:
        return [(0, 23)]
    bas = [i for i in range(len(s)) if s[i - 1] != (s[i] - 1) % SAAT_BITLERI]
    k = bas[0] if bas else 0
    s = s[k:] + s[:k]
    bloklar, basla, onceki = [], s[0], s[0]
    for h in s[1:]:
        if h == (onceki + 1) % SAAT_BITLERI:
            onceki = h
            continue
        bloklar.append((basla, onceki))
        basla = onceki = h
    bloklar.append((basla, onceki))
    return bloklar


def saat_metni(timeflags):
    saatler = aktif_saatler(timeflags)
    if timeflags is None:
        return "no TimeFlags"
    if not saatler:
        return "no hour bits at all (TimeFlags 0)"
    if len(saatler) == SAAT_BITLERI:
        return "every hour (24/24)"
    blok = ", ".join(f"{a:02d}:00-{(b + 1) % 24:02d}:00" for a, b in saat_bloklari(saatler))
    return f"{blok}  ({len(saatler)}h)"


def bitler(v):
    return [i for i in range(32) if v is not None and (v >> i) & 1]


def referans():
    """data/lights.tsv.gz -> (istatistik, bayrak, timeflag, ozet) ya da None.

    p05-p95 kullanilir, min-maks DEGIL: on binlerce isiklik bir korpusta tek
    bir uc deger araligi anlamsiz hale getirir ve denetim hicbir zaman
    tetiklenmez.
    """
    if not os.path.exists(LIGHTS):
        return None
    sutun, veri = None, collections.defaultdict(list)
    bayrak, tf, tip = collections.Counter(), collections.Counter(), collections.Counter()
    dosyalar = set()
    n = 0
    with gzip.open(LIGHTS, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if sutun is None:
                sutun = {ad: i for i, ad in enumerate(p)}
                continue
            if len(p) < len(sutun):
                continue
            n += 1
            dosyalar.add(p[sutun["model"]])
            tip[p[sutun["type"]]] += 1
            for anahtar, _ in SAYISAL:
                try:
                    veri[anahtar].append(float(p[sutun[anahtar]]))
                except (ValueError, KeyError):
                    pass
            try:
                bayrak[int(p[sutun["flags"]])] += 1
                tf[int(p[sutun["timeFlags"]])] += 1
            except ValueError:
                pass

    if not n:
        return None
    ist = {}
    for anahtar, gosterim in SAYISAL:
        v = sorted(veri[anahtar])
        if not v:
            continue
        ist[gosterim] = {
            "n": len(v), "min": v[0], "maks": v[-1],
            "p05": v[int(0.05 * (len(v) - 1))],
            "medyan": v[len(v) // 2],
            "p95": v[int(0.95 * (len(v) - 1))],
        }
    return {"ist": ist, "bayrak": bayrak, "tf": tf, "tip": tip,
            "n": n, "dosya": len(dosyalar)}


def supheli(isik, ref=None):
    """Isigi GORUNMEZ yapan ya da olculen araligin disina dusen durumlar.

    Mantik denetimleri her zaman calisir; aralik denetimi yalnizca referans
    katmani kuruluysa -- olcum yoksa "outside the range" denemez.
    """
    u = []
    if not aktif_saatler(isik["TimeFlags"]):
        # OLCULDU: 72.539 vanilla isikta TimeFlags 0 yalnizca 8 kez gecer
        # (%0,011) -- ve gectigi yerler ic mekan lamba prop'lari
        # (m232_lamp_office_01, m25_2_int_01_lp_m_bedroom, imp_lightrig01).
        # Bu yuzden 0'in "hic yanmaz" mi yoksa "no hour restriction" mu demek
        # oldugu BU VERIDEN COZULEMEZ. Nadir oldugu soylenir, davranis
        # IDDIA EDILMEZ; ayrimi ancak oyunda test etmek kapatir.
        u.append("TimeFlags 0: no hour bits at all. Very rare in vanilla "
                 "(8 of 72,539 lights, 0.011%) -- the data does not settle "
                 "what it does; test it in game")
    if isik["Intensity"] is not None and isik["Intensity"] <= 0:
        u.append("Intensity 0 -> emits nothing")
    if isik["Falloff"] is not None and isik["Falloff"] <= 0:
        u.append("Falloff 0 -> no range, the light reaches no surface")
    if isik["Type"] == "Spot":
        ic, dis = isik["ConeInnerAngle"], isik["ConeOuterAngle"]
        if dis is not None and dis <= 0:
            u.append("Spot but ConeOuterAngle 0 -> cone is shut")
        elif ic is not None and dis is not None and ic > dis:
            u.append(f"ConeInnerAngle ({ic:g}) > ConeOuterAngle ({dis:g}) -> cone inverted")
    if ref:
        for alan, s in ref["ist"].items():
            v = isik.get(alan)
            if v is None or v == 0:
                continue
            if v < s["p05"] or v > s["p95"]:
                u.append(f"{alan}={v:g} is outside vanilla's 90% band "
                         f"[{s['p05']:g}, {s['p95']:g}] (not an error - reference)")
    return u


def yaz_isik(idx, i, ham=False, ref=None):
    print(f"\n  #{idx}  {i['Type']}")
    if ham:
        for k, v in i.items():
            print(f"      {k:<22} {v}")
        return
    if i["Colour"]:
        r, g, b = i["Colour"]
        print(f"      colour       RGB({r},{g},{b})")
    if i["Intensity"] is not None:
        print(f"      intensity    {i['Intensity']:g}")
    if i["Falloff"] is not None:
        us = f"   (exp {i['FalloffExponent']:g})" if i["FalloffExponent"] is not None else ""
        print(f"      range        {i['Falloff']:g} m{us}")
    if i["Type"] == "Spot" and i["ConeOuterAngle"] is not None:
        print(f"      cone         inner {i['ConeInnerAngle']:g}deg -> outer "
              f"{i['ConeOuterAngle']:g}deg")
    if i["Type"] == "Capsule" and i["Extent"]:
        print(f"      extent       {i['Extent']}")
    print(f"      hours        {saat_metni(i['TimeFlags'])}"
          f"   [TimeFlags {i['TimeFlags']}]")
    if i["CoronaSize"]:
        print(f"      corona       size {i['CoronaSize']:g}  intensity "
              f"{i['CoronaIntensity']:g}")
    if i["VolumeIntensity"]:
        print(f"      volume       intensity {i['VolumeIntensity']:g}  scale "
              f"{i['VolumeSizeScale']:g}")
    if i["ShadowBlur"]:
        print(f"      shadow       blur {i['ShadowBlur']}")
    b = bitler(i["Flags"])
    yaygin = ""
    if ref and i["Flags"] in ref["bayrak"]:
        yaygin = f"  (vanilla x{ref['bayrak'][i['Flags']]})"
    print(f"      flags        {i['Flags']}  = bits {b or 'none'}{yaygin}")
    if i["BoneId"]:
        print(f"      bone         tag {i['BoneId']}")
    if i["ProjectedTextureHash"]:
        print(f"      projection   {i['ProjectedTextureHash']}")
    for s in supheli(i, ref):
        print(f"      ! {s}")


def yaz_tablo(ref):
    tip = ", ".join(f"{k} {v}" for k, v in ref["tip"].most_common())
    print("MEASURED VANILLA LIGHT REFERENCE")
    print(f"  source : data/lights.tsv.gz - {ref['n']} lights / {ref['dosya']} models")
    print(f"  types  : {tip}")
    print("  NOTE: outside the range is NOT an error, it means 'rare in vanilla'.\n")
    print(f"  {'field':<20} {'n':>7} {'min':>9} {'p05':>9} {'median':>9} "
          f"{'p95':>9} {'maks':>9}")
    for k, s in ref["ist"].items():
        print(f"  {k:<20} {s['n']:>7} {s['min']:>9g} {s['p05']:>9g} "
              f"{s['medyan']:>9g} {s['p95']:>9g} {s['maks']:>9g}")

    print("\n  Flags (8 most common):")
    for v, c in ref["bayrak"].most_common(8):
        print(f"    {v:<12} x{c:<7} bits {bitler(v) or 'none'}")
    print("  Bit NAMES are not in the database -> indices are shown, names are not invented.")

    print("\n  TimeFlags (8 most common):")
    for v, c in ref["tf"].most_common(8):
        print(f"    {v:<12} x{c:<7} {saat_metni(v)}")


def calistir(args):
    ref = referans()
    if args.tablo:
        if ref is None:
            print(f"ERROR: {LIGHTS} not found.", file=sys.stderr)
            print("  No measured reference - NOTHING can be claimed about ranges "
                  "edilemez. Uret: powershell -File build_lights.ps1",
                  file=sys.stderr)
            return 2
        yaz_tablo(ref)
        return 0
    if not args.path:
        print("ERROR: no file given (or use --table).", file=sys.stderr)
        return 2

    kok, hata = kok_oku(args.path)
    if hata:
        print(f"ERROR: {args.path}: {hata}", file=sys.stderr)
        print("  File could NOT be read - nothing can be said about the lights "
              "iddia edilemez.", file=sys.stderr)
        return 2

    isiklar = isiklari_oku(kok)
    if isiklar is None:
        print(f"{os.path.basename(args.path)} ({kok.tag}): has NO <Lights> node.")
        print("  This resource type may not carry lights at all; that is NOT the same "
              "DEGILDIR.")
        return 1
    if not isiklar:
        print(f"{os.path.basename(args.path)} ({kok.tag}): <Lights> var ama BOS "
              f"-> gomulu isik yok.")
        return 1

    print(f"{os.path.basename(args.path)} ({kok.tag}): {len(isiklar)} lights")
    for idx, i in enumerate(isiklar):
        yaz_isik(idx, i, args.ham, ref)
    toplam_uyari = sum(len(supheli(i, ref)) for i in isiklar)
    print(f"\n{len(isiklar)} lights | {toplam_uyari} warnings")
    return 0
