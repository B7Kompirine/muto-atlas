#!/usr/bin/env python3
"""pedrig.py - ped iskeleti / rest pose / yuz rig sorgu araci.

NEDEN: bir kemige animasyon yazmadan, prop takmadan ya da native cagirmadan
once o kemigin GERCEK verisine bakilir. Tahmin edilen kemik adi/tag'i sessizce
-1 dondurur; rest pose bilinmeden eklem acisi hesaplanamaz.

TEMEL GERCEKLER (olculmus - bkz. references/ped-kemik-yuz-rigging.md):
  • Kemigin uzunluk ekseni LOCAL +X'tir; translation = [uzunluk, 0, 0].
  • SKEL_Pelvis / SKEL_Spine_Root rest'te +-90 Y cevirici -> ASLA keyframe'lenmez
    (84 klip olcumunde sapma 0.0 derece).
  • Klipler uzuvlara SADECE rotasyon yazar; scale hic yazmaz.
  • FB_* yuz kemikleri kliple DEGIL expression (.yed) ile surulur.

KULLANIM
    python pedrig.py tree   <ped>                 # kemik agaci + tag
    python pedrig.py bone   <ped> <ad|tag>        # tek kemik: rest, uzunluk, cocuklar
    python pedrig.py rest   <ped> [--prefix SKEL] # rest pose tablosu
    python pedrig.py facial <ped>                 # FB_/FACIAL_ alt agaci
    python pedrig.py tag    <ad|tag> [...]        # ad <-> tag cevirisi
    python pedrig.py peds                         # mevcut ped'ler
    python pedrig.py groups <ped>                 # onek istatistigi
"""
import argparse
import gzip
import json
import math
import os
import sys

ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.join(
    os.path.expanduser("~"), ".claude", "fivem-natives")
RIG = os.path.join(ROOT, "data", "pedrig.json")
SKEL = os.path.join(ROOT, "data", "skeletons.tsv.gz")

PREFIX_DOC = {
    "SKEL_": "gercek deforme eden iskelet - mesh buna skinlenir; klip keyframeler",
    "IK_": "IK hedefi (el/ayak/kafa sabitleme)",
    "PH_": "physics/attach noktasi - prop takma buraya",
    "MH_": "muscle helper (dirsek/diz sismesi) - EXPRESSION surer",
    "RB_": "roll bone (burulma dagitimi) - EXPRESSION surer",
    "SM_": "etek/yumusak mesh paneli - EXPRESSION surer",
    "EO_": "ayakkabi/topuk override - EXPRESSION surer",
    "SPR_": "spring (yay fizigi) - EXPRESSION surer",
    "FB_": "yuz kemigi - KLIP DEGIL, expression surer",
    "FACIAL_": "yuz alt agacinin koku",
}
NEVER_KEY = {"SKEL_Pelvis", "SKEL_Spine_Root"}


def load_rig():
    if not os.path.exists(RIG):
        print(f"[!] {RIG} yok. Once uret:\n"
              f"    powershell -NoProfile -ExecutionPolicy Bypass -File "
              f"{os.path.join(ROOT,'scripts','build_pedrig.ps1')}", file=sys.stderr)
        return None
    with open(RIG, encoding="utf-8") as fh:
        return json.load(fh)["peds"]


def load_skel_names():
    """pedrig.json yoksa skeletons.tsv.gz'den ad/tag/parent kurtar."""
    if not os.path.exists(SKEL):
        return {}
    peds = {}
    with gzip.open(SKEL, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 7:
                continue
            try:
                peds.setdefault(f[0], []).append(
                    {"i": int(f[3]), "n": f[4], "tag": int(f[5]), "p": int(f[6])})
            except ValueError:
                pass
    return peds


def get_ped(rig, name):
    if rig and name in rig:
        return rig[name]
    sk = load_skel_names()
    if name in sk:
        print(f"[i] pedrig.json'da '{name}' yok - sadece ad/tag/parent "
              f"gosteriliyor (rest pose icin build_pedrig.ps1 calistir).",
              file=sys.stderr)
        return sk[name]
    return None


def quat_angle(q):
    """Rest kuaterniyonunun ebeveyn cercevesinden sapmasi (derece)."""
    w = max(-1.0, min(1.0, abs(q[3])))
    return 2 * math.degrees(math.acos(w))


def blen(bones, b):
    """Kemigin uzunlugu = TEK SKEL_ cocugunun local X translation'i.

    GTA ped iskeletinde zincir child'i +X'te durur, o yuzden bu gecerli bir
    uzunluk olcusu. Ama birden fazla SKEL_ cocugu olan dallanma kemiklerinde
    (Pelvis -> iki uyluk, Hand -> bes parmak, Spine3 -> iki klavikula + boyun)
    child X'i uzunluk DEGIL yan offset'tir; orada None doner. Yoksa Pelvis
    icin uyluk offset'ini "7.4cm kemik boyu" diye yanlis raporlar.
    """
    kids = [c for c in bones if c["p"] == b["i"]
            and c["n"].startswith("SKEL_") and "t" in c]
    if len(kids) != 1:
        return None
    return abs(kids[0]["t"][0])


def fmt_bone(b, bones, indent=0):
    pad = "  " * indent
    s = f'{pad}{b["n"]}  [tag={b["tag"]} idx={b["i"]}]'
    if "t" in b:
        L = blen(bones, b)
        if L:
            s += f"  len={L*100:.1f}cm"
    if b["n"] in NEVER_KEY:
        s += "   <-- KEYFRAME'LEMEYIN (rest'te 90 derece cevirici)"
    return s


def cmd_tree(bones, args):
    kids = {}
    for b in bones:
        kids.setdefault(b["p"], []).append(b)
    only = args.prefix

    def walk(pi, d):
        for b in sorted(kids.get(pi, []), key=lambda x: x["i"]):
            if not only or b["n"].startswith(only):
                print(fmt_bone(b, bones, d))
            walk(b["i"], d + 1 if (not only or b["n"].startswith(only)) else d)
    walk(-1, 0)
    print(f"\n[=] {len(bones)} kemik")


def cmd_bone(bones, args):
    q = args.query[0]
    hit = [b for b in bones if b["n"].lower() == q.lower()]
    if not hit and q.isdigit():
        hit = [b for b in bones if b["tag"] == int(q)]
    if not hit:
        hit = [b for b in bones if q.lower() in b["n"].lower()]
    if not hit:
        print(f"[!] '{q}' bulunamadi.", file=sys.stderr)
        return 1
    byidx = {b["i"]: b for b in bones}
    for b in hit[:8]:
        print(f'=== {b["n"]}')
        print(f'    tag         : {b["tag"]}   (GetPedBoneCoords / GetPedBoneIndex bunu alir)')
        print(f'    index       : {b["i"]}')
        par = byidx.get(b["p"])
        print(f'    parent      : {par["n"] if par else "(kok)"}')
        if "t" in b:
            t, r, s = b["t"], b["r"], b["s"]
            print(f'    translation : [{t[0]:.6f}, {t[1]:.6f}, {t[2]:.6f}]'
                  f'   -> ebeveynden {math.sqrt(sum(x*x for x in t))*100:.1f}cm')
            print(f'    rotation    : [{r[0]:.6f}, {r[1]:.6f}, {r[2]:.6f}, {r[3]:.6f}]'
                  f'  (xyzw, rest\'ten {quat_angle(r):.1f} derece)')
            print(f'    scale       : [{s[0]:.4f}, {s[1]:.4f}, {s[2]:.4f}]')
            L = blen(bones, b)
            if L:
                print(f'    kemik boyu  : {L*100:.1f}cm  (cocugun local +X translation\'i)')
        pre = next((p for p in PREFIX_DOC if b["n"].startswith(p)), None)
        if pre:
            print(f'    onek        : {pre} - {PREFIX_DOC[pre]}')
        if b["n"] in NEVER_KEY:
            print('    !! UYARI    : rest\'te +-90 Y cevirici. Keyframe koymak tum')
            print('                  hiyerarsiyi 90 derece yatirir. Olcum: sapma 0.0 derece.')
        kids = [c["n"] for c in bones if c["p"] == b["i"]]
        if kids:
            print(f'    cocuklar    : {", ".join(kids)}')
        print()
    return 0


def cmd_rest(bones, args):
    # ASCII basliklar: Windows konsolu (cp857/cp1254) '°' ve '—' karakterlerini
    # bozuk gosteriyor. Cikti okunabilir kalsin.
    print(f'{"kemik":<28}{"tag":>7}{"tX":>11}{"tY":>10}{"tZ":>10}{"restDeg":>9}{"boy cm":>9}')
    for b in sorted(bones, key=lambda x: x["i"]):
        if args.prefix and not b["n"].startswith(args.prefix):
            continue
        if "t" not in b:
            print(f'{b["n"]:<28}{b["tag"]:>7}   (rest pose yok)')
            continue
        t = b["t"]
        L = blen(bones, b)
        print(f'{b["n"]:<28}{b["tag"]:>7}{t[0]:>11.6f}{t[1]:>10.6f}{t[2]:>10.6f}'
              f'{quat_angle(b["r"]):>8.1f}{(L*100 if L else 0):>9.1f}')


def cmd_facial(bones, args):
    fb = [b for b in bones if b["n"].startswith(("FB_", "FACIAL_"))]
    if not fb:
        print("[!] bu ped'de yuz kemigi yok.")
        return 1
    print(f'{len(fb)} yuz kemigi\n')
    print("ONEMLI: bu kemikler KLIPLE surulmez. facials@*.ycd soyut float")
    print("kanallari (Track 22 / Track 25) oynatir; kanallari kemik donusune")
    print("ceviren sey .yed EXPRESSION'dir (genel ped icin ambient.yed -> facial).")
    print("Kanal haritasi: yed_expr.py channels ambient.yed.xml --expr facial\n")
    byidx = {b["i"]: b for b in bones}
    for b in sorted(fb, key=lambda x: x["i"]):
        par = byidx.get(b["p"])
        line = f'  {b["n"]:<30} tag={b["tag"]:<6} parent={par["n"] if par else "-"}'
        print(line)
    return 0


def cmd_groups(bones, args):
    import collections
    c = collections.Counter()
    for b in bones:
        pre = next((p for p in PREFIX_DOC if b["n"].startswith(p)), "(diger)")
        c[pre] += 1
    print(f'{len(bones)} kemik\n')
    for pre, n in c.most_common():
        doc = PREFIX_DOC.get(pre, "")
        print(f'  {pre:<10} {n:>4}  {doc}')


HUMAN_NEED = {"SKEL_Pelvis", "SKEL_Head", "SKEL_L_Hand", "SKEL_R_Hand",
              "SKEL_Spine3", "SKEL_L_Foot"}


def all_peds():
    """skeletons.tsv.gz'den TUM iskeletleri oku: model -> {tag: ad}."""
    import gzip as _gz
    out = {}
    if not os.path.exists(SKEL):
        return out
    with _gz.open(SKEL, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 7:
                continue
            try:
                out.setdefault(f[0], {})[int(f[5])] = f[4]
            except ValueError:
                pass
    return out


def humanoids(skip_animals=True):
    src = all_peds()
    out = {}
    for m, t in src.items():
        if skip_animals and m.startswith("a_c_"):
            continue
        if HUMAN_NEED <= set(t.values()):
            out[m] = t
    return out


def cluster(hum):
    """Ayni TAG KUMESINE sahip ped'ler ayni rig ailesidir."""
    import hashlib
    sig = {}
    for m, t in hum.items():
        h = hashlib.md5((",".join(map(str, sorted(t)))).encode()).hexdigest()[:10]
        sig.setdefault(h, []).append(m)
    return sorted(sig.items(), key=lambda kv: -len(kv[1]))


def cmd_families(args):
    hum = humanoids()
    fam = cluster(hum)
    tot = len(hum)
    print(f"{tot} humanoid ped iskeleti, {len(fam)} farkli rig ailesi\n")
    print(f'{"imza":<12}{"kemik":>7}{"ped":>6}  ornek')
    for h, ms in fam[:args.limit]:
        print(f"{h:<12}{len(hum[ms[0]]):>7}{len(ms):>6}  {sorted(ms)[:3]}")
    if len(fam) > args.limit:
        print(f"... {len(fam)-args.limit} aile daha")

    # kapsama katmanlari
    print("\nKAPSAMA: ilk N aileyi hedeflersen")
    cum = 0
    inter = None
    for i, (h, ms) in enumerate(fam, 1):
        cum += len(ms)
        s = set(hum[ms[0]])
        inter = s if inter is None else (inter & s)
        if i in (1, 2, 4, 8, 20, 40, len(fam)):
            print(f"  ilk {i:>3} aile -> {cum:>5} ped ({100*cum/tot:5.1f}%)  "
                  f"ortak kemik: {len(inter)}")
    print(f"\nEVRENSEL CEKIRDEK ({len(inter)} kemik) - her humanoid ped'de var:")
    ref = hum[fam[0][1][0]]
    print("  " + ", ".join(sorted(ref.get(t, f"?{t}") for t in inter)))
    print("\nBir klip yalnizca hedef ped'de VAR OLAN kemikleri surer; eksik")
    print("kemik sessizce rest'te kalir. Bu yuzden KUCUK sete gore yazilmis")
    print("animasyon buyuk rig'de calisir, tersi calismaz.")


def cmd_compat(args):
    hum = humanoids()
    me = args.ped
    if me not in hum:
        alt = [m for m in hum if me.lower() in m.lower()][:6]
        print(f"[!] '{me}' humanoid ped listesinde yok."
              + (f" Benzer: {alt}" if alt else ""), file=sys.stderr)
        return 1
    mine = set(hum[me])
    sup = [m for m, t in hum.items() if mine <= set(t)]
    sub = [m for m, t in hum.items() if set(t) <= mine]
    print(f"{me}: {len(mine)} kemik\n")
    print(f"Bu ped'in kemiklerinin TAMAMINA sahip ped: {len(sup)} "
          f"({100*len(sup)/len(hum):.1f}%)")
    print(f"  -> {me} icin yazilmis bir animasyon bu ped'lerde SORUNSUZ oynar.")
    print(f"Kemikleri bu ped'in ALT KUMESI olan ped: {len(sub)} "
          f"({100*len(sub)/len(hum):.1f}%)")
    print(f"  -> bu ped'ler icin yazilmis animasyon {me}'de sorunsuz oynar.")
    fam = cluster(hum)
    myfam = next((h for h, ms in fam if me in ms), None)
    if myfam:
        ms = dict(fam)[myfam]
        print(f"\nAyni rig ailesi ({myfam}): {len(ms)} ped")
        print(f"  {sorted(ms)[:10]}")
    # yuz rigi
    facial = [n for n in hum[me].values() if n.startswith(("FB_", "FACIAL_"))]
    fb = [n for n in facial if n.startswith("FB_")]
    fc = [n for n in facial if n.startswith("FACIAL_")]
    print(f"\nYUZ RIGI: {len(facial)} kemik  (FB_={len(fb)}  FACIAL_={len(fc)})")
    if len(fc) > 30:
        print("  YUKSEK DETAY 'FACIAL_*' rigi (hikaye karakteri). 21 kemikli")
        print("  FB_ rigine gore cok daha ince ifade uretebilir; surucusu")
        print("  <ped>.yed -> faceinit expression'idir.")
    elif fb:
        import re as _re
        suf = sorted({m.group(1) for n in fb
                      for m in [_re.search(r"_(\d{3})$", n)] if m})
        print(f"  standart FB_ rigi, ad son eki: {suf}")
        if suf == ["045"]:
            print("  !! '_045' son ekini TUM OYUNDA sadece mp_m_freemode_01 kullanir.")
            print("     Baska ped'in kafa .ydd'si _000/_001 tasir -> Blender'da")
            print("     armature modifier ADLA baglar, yuz sessizce deforme OLMAZ.")
    return 0


def cmd_tag(args):
    rig = load_rig()
    src = rig if rig else load_skel_names()
    idx = {}
    for ped, bones in src.items():
        for b in bones:
            idx.setdefault(b["n"].lower(), set()).add(b["tag"])
            idx.setdefault(str(b["tag"]), set()).add(b["n"])
    for q in args.query:
        v = idx.get(q.lower())
        print(f'{q:<32} -> {sorted(v) if v else "(bulunamadi)"}')


CLIPS = os.path.join(ROOT, "data", "clips.tsv.gz")

# creatures@ sozluk ailesi -> ped modeli (ad birebir eslesmez)
ANIM_AILE = {
    "rottweiler": ["a_c_rottweiler", "a_c_rottweiler_02", "a_c_chop", "a_c_chop_02"],
    "retriever": ["a_c_retriever"], "coyote": ["a_c_coyote", "a_c_coyote_02"],
    "cougar": ["a_c_mtlion", "a_c_mtlion_02", "a_c_panther"],
    "deer": ["a_c_deer", "a_c_deer_02"], "cow": ["a_c_cow"], "pig": ["a_c_pig"],
    "boar": ["a_c_boar", "a_c_boar_02"], "pug": ["a_c_pug", "a_c_pug_02"],
    "cat": ["a_c_cat_01", "a_c_cat_02"], "husky": ["a_c_husky"],
    "rabbit": ["a_c_rabbit_01", "a_c_rabbit_02"], "rat": ["a_c_rat"],
    "gull": ["a_c_seagull"], "crow": ["a_c_crow"], "pigeon": ["a_c_pigeon"],
    "hen": ["a_c_hen"], "cormorant": ["a_c_cormorant"],
    "chickenhawk": ["a_c_chickenhawk"], "monkey": ["a_c_chimp", "a_c_chimp_02",
                                                   "a_c_rhesus"],
    "shark": ["a_c_sharktiger"], "hammerhead": ["a_c_sharkhammer"],
    "killerwhale": ["a_c_killerwhale"], "dolphin": ["a_c_dolphin"],
    "humpback": ["a_c_humpback"], "stingray": ["a_c_stingray"],
    "fish": ["a_c_fish"], "dog": ["a_c_shepherd", "a_c_westy", "a_c_poodle"],
}


def _animal_skeletons():
    """a_c_* ped'lerin iskeletleri, KAYNAGA gore tekillestirilmis.

    IKI AYRI TEKRAR TUZAGI VAR, ikisi de satir saymayi YANLIS yapar:
      1. bazi ped'ler hem .yft hem .ydd kaynagindan gelir (src'ye gore ayir)
      2. ayni src icinde ayni kemik IKI KEZ yazilmis olabilir - model birden
         fazla RPF'te bulundugu icin. Olculdu: a_c_mtlion_02 -> 144 satir,
         72 benzersiz boneIndex, boneCount alani da 72 diyor.
    Tekillestirilmezse "bu ped iki kat zengin" diye yanlis iskelet secilir.
    boneCount kolonu dogruyu soyler; kontrol icin kullan.
    """
    out = {}
    if not os.path.exists(SKEL):
        return out
    with gzip.open(SKEL, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 7 or not f[0].startswith("a_c_"):
                continue
            try:
                out.setdefault(f[0], {}).setdefault(f[1], {})[int(f[3])] = {
                    "i": int(f[3]), "n": f[4], "tag": int(f[5]), "p": int(f[6])}
            except ValueError:
                pass
    return {m: list(max(s.values(), key=len).values()) for m, s in out.items()}


def _limb_chains(bones):
    """Govdeden (Spine/Pelvis/ROOT) cikan >=3 kemiklik seri uzuv zincirleri."""
    name = {b["i"]: b["n"] for b in bones}
    par = {b["i"]: b["p"] for b in bones}
    kids = {}
    for i, p in par.items():
        if p >= 0:
            kids.setdefault(p, []).append(i)
    core = {i for i, n in name.items()
            if "Spine" in n or "Pelvis" in n or n == "SKEL_ROOT"}
    chains = []
    for c in core:
        for k in kids.get(c, []):
            if k in core:
                continue
            best = []
            stack = [(k, [])]
            while stack:
                i, acc = stack.pop()
                acc = acc + [name[i]]
                ch = [x for x in kids.get(i, [])
                      if not name[x].startswith(("PH_", "IK_", "FB_", "FACIAL"))]
                if not ch and len(acc) > len(best):
                    best = acc
                for x in ch:
                    stack.append((x, acc))
            if len(best) >= 3 and not best[0].startswith(("FB_", "FACIAL")):
                chains.append(best)
    return chains


def _creature_clip_counts():
    """creatures@<aile>@ klip sayilari. Veri dosyasi okunamazsa BOS doner.

    Klip sayisi zenginlestirmedir; iskelet/zincir bilgisi asil degerdir. Veri
    dosyasi kilitli ya da yeniden uretiliyor olabilir (OSError/gzip.BadGzipFile)
    - bu durumda sorgu comeden calismali.
    """
    counts, dicts = {}, {}
    if not os.path.exists(CLIPS):
        return counts, dicts
    try:
        with gzip.open(CLIPS, "rt", encoding="utf-8", errors="replace") as fh:
            fh.readline()
            for line in fh:
                d = line.split("\t", 1)[0]
                if not d.startswith("creatures@"):
                    continue
                fam = d.split("@")[1]
                counts[fam] = counts.get(fam, 0) + 1
                dicts.setdefault(fam, set()).add(d)
    except (OSError, EOFError, gzip.BadGzipFile) as e:
        print(f"[i] {os.path.basename(CLIPS)} okunamadi ({type(e).__name__}) - "
              f"klip sayilari gosterilmiyor.", file=sys.stderr)
        return {}, {}
    return counts, dicts


def cmd_animals(args):
    """Hayvan ped'lerini uzuv zinciri ve HAZIR ANIMASYON sayisiyla siralar.

    Insan disi bir yaratigi rig'lerken dogru soru "hangi hayvana benziyor"
    degil, "hangi iskelet yeterli uzuv zinciri veriyor ve kac hazir klibi var".
    """
    sk = _animal_skeletons()
    if not sk:
        print(f"[!] {SKEL} yok.", file=sys.stderr)
        return 1
    counts, dicts = _creature_clip_counts()
    ped2fam = {p: f for f, ps in ANIM_AILE.items() for p in ps}

    if args.ped:                      # tek hayvanin detayi
        m = args.ped if args.ped in sk else next(
            (k for k in sk if args.ped.lower() in k.lower()), None)
        if not m:
            print(f"[!] '{args.ped}' hayvan ped'i degil.", file=sys.stderr)
            return 1
        fam = ped2fam.get(m)
        klip = (f"{counts.get(fam,0)} klip, {len(dicts.get(fam,()))} sozluk"
                if counts else "klip sayisi okunamadi")
        print(f"{m} — {len(sk[m])} kemik"
              + (f"  ·  creatures@{fam}@ : {klip}" if fam else ""))
        print("\nUZUV ZINCIRLERI (govdeden cikan, >=3 kemik):")
        for c in sorted(_limb_chains(sk[m]), key=len, reverse=True):
            print(f"  {len(c):>2} kemik  {' -> '.join(x.replace('SKEL_','') for x in c)}")
        return 0

    rows = []
    for m, bones in sk.items():
        fam = ped2fam.get(m)
        ch = _limb_chains(bones)
        rows.append((counts.get(fam, 0), len(ch), len(bones), m, fam,
                     sorted((len(c) for c in ch), reverse=True)))
    rows.sort(key=lambda r: (-r[0], -r[2]) if counts else (-r[2], r[3]))
    print(f"{len(sk)} hayvan ped'i — "
          + ("hazir klip sayisina gore" if counts else "kemik sayisina gore") + "\n")
    print(f'{"ped":<20}{"kemik":>6}{"zincir":>7}{"klip":>6}  zincir boylari')
    for clip, nch, nb, m, fam, lens in rows[:args.limit]:
        print(f"{m:<20}{nb:>6}{nch:>7}{clip if counts else '—':>6}  {lens}")
    if len(rows) > args.limit:
        print(f"... {len(rows)-args.limit} ped daha (--limit ile artir)")
    if counts:
        print("\nKlip sayisi = o iskeleti secince BEDAVA gelen animasyon.")
    print("Zincir boylari = yaratigin uzuvlarina dagitabilecegin kemik sayilari.")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["tree", "bone", "rest", "facial",
                                     "tag", "peds", "groups", "families",
                                     "compat", "animals"])
    ap.add_argument("ped", nargs="?")
    ap.add_argument("query", nargs="*")
    ap.add_argument("--prefix", help="sadece bu onekli kemikler")
    ap.add_argument("--limit", type=int, default=14)
    args = ap.parse_args()

    if args.mode == "families":
        cmd_families(args)
        return 0

    if args.mode == "animals":
        return cmd_animals(args) or 0

    if args.mode == "compat":
        if not args.ped:
            print("[!] ped adi gerekli.", file=sys.stderr)
            return 1
        return cmd_compat(args) or 0

    if args.mode == "peds":
        rig = load_rig() or {}
        sk = load_skel_names()
        print("pedrig.json (rest pose ile):")
        for k, v in sorted(rig.items()):
            print(f"  {k:<24} {len(v)} kemik")
        extra = [k for k in sk if k not in rig and
                 (k.startswith(("player_", "mp_m_", "mp_f_", "a_m_", "a_f_")))]
        print(f"\nskeletons.tsv.gz'de ayrica {len(extra)} ped var (rest pose yok).")
        return 0

    if args.mode == "tag":
        q = ([args.ped] if args.ped else []) + args.query
        if not q:
            print("[!] ad ya da tag ver.", file=sys.stderr)
            return 1
        args.query = q
        cmd_tag(args)
        return 0

    if not args.ped:
        print("[!] ped adi gerekli (ornek: mp_m_freemode_01). "
              "'pedrig.py peds' ile listele.", file=sys.stderr)
        return 1

    rig = load_rig()
    bones = get_ped(rig, args.ped)
    if bones is None:
        print(f"[!] '{args.ped}' bulunamadi. 'pedrig.py peds' ile listele.",
              file=sys.stderr)
        return 1

    if args.mode == "tree":
        cmd_tree(bones, args)
    elif args.mode == "bone":
        if not args.query:
            print("[!] kemik adi ya da tag ver.", file=sys.stderr)
            return 1
        return cmd_bone(bones, args)
    elif args.mode == "rest":
        cmd_rest(bones, args)
    elif args.mode == "facial":
        return cmd_facial(bones, args)
    elif args.mode == "groups":
        cmd_groups(bones, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
