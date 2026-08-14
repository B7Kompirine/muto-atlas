#!/usr/bin/env python3
"""yed_expr.py — GTA V .yed (Expression Dictionary) bytecode cozumleyici.

NE ISE YARAR
============
Bir ped'in yuz animasyonu FB_ kemiklerini DOGRUDAN surmez. Yuz .ycd'si soyut
float kanallarini (Track 22 / Track 25) oynatir; bu kanallari gercek kemik
donusune ceviren sey EXPRESSION'dir (.yed):

    facials@*.ycd --(Track22 float / Track25 vec3)--> .yed expression
                  --(Track0 pos / Track1 rot / Track2 scale)--> FB_* kemikleri

Bu arac .yed icindeki yigin-tabanli bytecode'u CFG uzerinde simule edip
"hangi GIRIS kanali hangi CIKIS kemigini suruyor" tablosunu KESIN olarak
uretir (kaba blok atifi degil; her TrackSet'in operandi geriye izlenir).

ONEMLI: CodeWalker bu bytecode'u OKUR ama YAZAMAZ. Bir .yed'i CodeWalker ile
kaydedersen Streams bosalir ve yuz/prosedurel hareket tamamen olur. Duzenleme
gerekiyorsa `muto` Blender eklentisinin build_yed yolu kullanilir.

KULLANIM
========
    powershell -File res_to_xml.ps1 -Path <dosya.yed>      # once XML'e cevir

    python yed_expr.py list    <dosya.yed.xml>
    python yed_expr.py verify  <dosya.yed.xml>             # yigin dengesi denetimi
    python yed_expr.py io      <dosya.yed.xml> --expr mp_freemode
    python yed_expr.py drives  <dosya.yed.xml> --expr mp_freemode   # cikis <- giris
    python yed_expr.py channels <dosya.yed.xml> --expr mp_freemode  # giris -> cikis
    python yed_expr.py springs <dosya.yed.xml>
"""
import argparse
import collections
import gzip
import os
import sys
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------- track tablosu
# Sollumz tools/animationhelper.py Track enum'undan dogrulandi.
TRACK_NAMES = {
    0: "BonePosition", 1: "BoneRotation", 2: "BoneScale",
    5: "MoverPosition", 6: "MoverRotation",
    7: "CameraPosition", 8: "CameraRotation",
    17: "UV0", 18: "UV1",
    22: "Float22", 24: "Float24", 25: "Vector25", 26: "Quat26",
    27: "CameraFOV", 28: "CameraDOF",
    33: "Float33", 34: "Vector34",
    134: "Unk134", 136: "Unk136", 137: "Unk137",
    138: "Unk138", 139: "Unk139", 140: "Unk140",
}
FORMAT_NAMES = {0: "Vector3", 1: "Quaternion", 2: "Float"}

# ---------------------------------------------------------------- yigin aritesi
# (pop, push). Elle cozumlenen akislardan turetildi, sonra 184 stream /
# ~50k instruction uzerinde yigin-dengesi taramasiyla sinandi (`verify`).
#
# DOGRULANMIS SEMANTIK (4 farkli kombinasyon denenip olculdu):
#   * Jump / JumpIfTrue / JumpIfFalse hedefi = KENDI indeksi + offset
#     (i+off; i+1+off DEGIL).
#   * JumpIfTrue/JumpIfFalse kosulu POP ETMEZ — her iki dalin basinda ayri
#     bir `Pop` vardir. Olcum: peek+i+off -> 179/184 temiz akis, 105 dengesizlik;
#     en yakin alternatif (pop-on-taken + i+1+off) -> 180/184 ama 275 dengesizlik.
#   * ToVector 3 float alir -> 1 vektor verir (Push0,Push0,<z>,ToVector kalibi).
#
# BILINEN SINIR: 5 stream tam dengelenmiyor — default.yed'in prosedurel
# duzeltme ifadeleri (upperbody_fixup/_shadow, independent_mover,
# rootheight_fixup) ve p_m_zero faceinit. Bunlarda `drives`/`channels`
# cikisi YAKLASIKTIR. Bu is icin kritik olan mp_freemode (1/1) ve
# ambient.yed (19/19) tamamen dengeli, yani yuz kanali esleme verisi kesin.
# Muhtemel neden: InstructionOffset'in bayt tabanli olmasi (degisken boyutlu
# instruction), yogun bolgelerde indeks varsayimini bozuyor.
ARITY = {
    # uretici
    "Push0": (0, 1), "Push1": (0, 1), "PushFloat": (0, 1), "PushVector": (0, 1),
    "PushDeltaTime": (0, 1), "PushTime": (0, 1), "GetVariable": (0, 1),
    "TrackGet": (0, 1), "TrackGetComp": (0, 1), "TrackGetOffsetComp": (0, 1),
    "TrackGetBoneTransform": (0, 1), "TrackValid": (0, 1),
    # tuketici
    "Pop": (1, 0), "SetVariable": (1, 0),
    "TrackSet": (1, 0), "TrackSetComp": (1, 0), "TrackSetOffset": (1, 0),
    "TrackSetBoneTransform": (1, 0),
    "DefineSpring": (1, 0),
    # tekli
    "VectorNeg": (1, 1), "VectorNeg3": (1, 1), "VectorRcp": (1, 1),
    "VectorSaturate": (1, 1), "VectorRad2Deg": (1, 1), "VectorDeg2Rad": (1, 1),
    "FromEuler": (1, 1), "ToEuler": (1, 1),
    # ikili
    "VectorAdd": (2, 1), "VectorSub": (2, 1), "VectorMul": (2, 1),
    "VectorMin": (2, 1), "VectorMax": (2, 1),
    "VectorLessThan": (2, 1), "VectorLessEqual": (2, 1),
    "VectorGreaterThan": (2, 1), "VectorGreaterEqual": (2, 1),
    "VectorNotEqual": (2, 1), "QuatMul": (2, 1), "VectorTransform": (2, 1),
    # uclu
    "ToVector": (3, 1), "VectorMad": (3, 1), "VectorClamp": (3, 1),
    "VectorLerp": (3, 1), "QuatSlerp": (3, 1), "LookAt": (3, 1),
    # YIGINDAN DEGIL kendi <Sources> listesinden okur: her Source bir
    # <TrackIndex> tasir ve bu, expression'in Tracks[] dizisine indekstir.
    # Bu yuzden aritesi (0,1) — operandi yiginda aramak yanlis sonuc verir.
    "BlendVector": (0, 1), "BlendQuaternion": (0, 1),
    # yay tanimi: tum parametreler instruction icinde, yigina dokunmaz
    "DefineSpring": (0, 0),
    # kontrol akisi (yigina dokunmaz)
    "Jump": (0, 0), "JumpIfTrue": (0, 0), "JumpIfFalse": (0, 0),
    "Unk23": (0, 0),
}

BLEND_OPS = {"BlendVector", "BlendQuaternion"}

READ_OPS = {"TrackGet", "TrackGetComp", "TrackGetOffsetComp",
            "TrackGetBoneTransform", "TrackValid"}
WRITE_OPS = {"TrackSet", "TrackSetComp", "TrackSetOffset",
             "TrackSetBoneTransform"}
JUMP_OPS = {"Jump", "JumpIfTrue", "JumpIfFalse"}


def _iv(el, name, attr="value", cast=int):
    c = el.find(name)
    if c is None or attr not in c.attrib:
        return None
    try:
        return cast(c.get(attr))
    except (TypeError, ValueError):
        return None


def _chan(el):
    return (_iv(el, "BoneId"), _iv(el, "Track"), _iv(el, "Format"),
            _iv(el, "ComponentIndex"))


def load(path):
    root = ET.parse(path).getroot()
    exprs = []
    for item in root.findall("./Item"):
        name = (item.findtext("Name") or "").strip()
        if name.startswith("pack:/"):
            name = name[6:]
        if name.endswith(".expr"):
            name = name[:-5]
        streams = []
        for st in item.findall("./Streams/Item"):
            instrs = [(ins.get("type"), ins)
                      for ins in st.findall("./Instructions/Item")]
            streams.append({"name": (st.findtext("Name") or "").strip(),
                            "instrs": instrs})
        exprs.append({
            "name": name,
            "signature": _iv(item, "Signature"),
            "unk7c": _iv(item, "Unk7C"),
            "tracks": [_chan(t) for t in item.findall("./Tracks/Item")],
            "streams": streams,
            "springs": [{"chan": _chan(sp),
                         "raw": {c.tag: (c.get("value") if "value" in c.attrib
                                         else (c.text or "").strip())
                                 for c in sp}}
                        for sp in item.findall(".//Item[@type='DefineSpring']")],
        })
    return exprs


# ------------------------------------------------------------------- dataflow
class Unsupported(Exception):
    pass


def run_stream(instrs, tracks=None):
    """CFG uzerinde provenance (koken) simulasyonu.

    Yigindaki her deger, onu ureten GIRIS kanallarinin frozenset'idir.
    Birlesme noktalarinda kumeler birlestirilir (union). Sonuc:
        writes: [(cikis_kanali, kaynak_giris_kumesi, op)]
        errors: yigin dengesi/derinlik uyusmazliklari
    """
    tracks = tracks or []

    def track_ref(i):
        """Tracks[] dizisindeki i. kanal -> (boneId, track)."""
        if i is None or i < 0 or i >= len(tracks):
            return None
        t = tracks[i]
        return (t[0], t[1])

    n = len(instrs)
    writes = []
    errors = []
    # program noktasi -> yigin (frozenset listesi)
    seen = {}
    work = [(0, ())]
    guard = 0
    while work:
        pc, stack = work.pop()
        guard += 1
        if guard > 400000:
            errors.append("guard limiti asildi (dongu?)")
            break
        while True:
            if pc >= n:
                if len(stack) != 0:
                    errors.append(f"akis sonunda yigin bos degil: {len(stack)}")
                break
            key = pc
            prev = seen.get(key)
            if prev is not None:
                if len(prev) != len(stack):
                    errors.append(
                        f"pc={pc} yigin derinligi uyusmadi {len(prev)}!={len(stack)}")
                    break
                merged = tuple(a | b for a, b in zip(prev, stack))
                if merged == prev:
                    break              # yeni bilgi yok, dur
                stack = merged
            seen[key] = stack

            op, el = instrs[pc]
            if op not in ARITY:
                raise Unsupported(op)
            pop, push = ARITY[op]

            if op in JUMP_OPS:
                off = _iv(el, "InstructionOffset")
                if off is None:
                    errors.append(f"pc={pc} {op}: offset yok")
                    break
                tgt = pc + off          # offset KENDI indeksine gore relatif
                if op == "Jump":
                    pc = tgt
                    continue
                work.append((tgt, stack))   # kosul POP EDILMEZ
                pc += 1
                continue

            if pop > len(stack):
                errors.append(f"pc={pc} {op}: yigin yetersiz "
                              f"({len(stack)} var, {pop} gerek)")
                break
            args = stack[len(stack) - pop:] if pop else ()
            stack = stack[:len(stack) - pop]

            if op in WRITE_OPS:
                src = frozenset().union(*args) if args else frozenset()
                writes.append((_chan(el), src, op))
            elif op in READ_OPS:
                ch = _chan(el)
                stack = stack + (frozenset({(ch[0], ch[1])}),)
            elif op in BLEND_OPS:
                # operandlar <Sources><Item><TrackIndex> ile Tracks[]'e isaret eder
                srcs = set()
                for s in el.findall("./Sources/Item"):
                    r = track_ref(_iv(s, "TrackIndex"))
                    if r:
                        srcs.add(r)
                stack = stack + (frozenset(srcs),)
            else:
                merged = frozenset().union(*args) if args else frozenset()
                stack = stack + tuple(merged for _ in range(push))
            pc += 1
    return writes, errors


def analyse(expr):
    writes, errors = [], []
    for st in expr["streams"]:
        w, e = run_stream(st["instrs"], expr["tracks"])
        writes += w
        errors += [f"[{st['name']}] {x}" for x in e]
    return writes, errors


# ------------------------------------------------------------------- yardimci
def load_bone_names(model=None):
    root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.join(
        os.path.expanduser("~"), ".claude", "fivem-natives")
    p = os.path.join(root, "data", "skeletons.tsv.gz")
    if not os.path.exists(p):
        return {}
    models = {model} if model else {
        "mp_m_freemode_01", "mp_f_freemode_01",
        "player_zero", "player_one", "player_two"}
    names = {}
    with gzip.open(p, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 7 or f[0] not in models:
                continue
            try:
                names.setdefault(int(f[5]), f[4])
            except ValueError:
                pass
    return names


def fmt(ch, bones):
    bid, tr = ch[0], ch[1]
    nm = f" {bones[bid]}" if bones and bid in bones else ""
    return f"{bid}{nm} [{TRACK_NAMES.get(tr, f'Track{tr}')}]"


def split_io(writes):
    reads = {c for _, src, _ in writes for c in src}
    outs = {(w[0][0], w[0][1]) for w in writes}
    return reads - outs, outs


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["list", "verify", "io", "drives",
                                     "channels", "springs"])
    ap.add_argument("xml")
    ap.add_argument("--expr")
    ap.add_argument("--model")
    args = ap.parse_args()

    exprs = load(args.xml)
    if args.expr:
        exprs = [e for e in exprs if e["name"] == args.expr]
        if not exprs:
            print(f"[!] '{args.expr}' bulunamadi.", file=sys.stderr)
            return 1
    bones = load_bone_names(args.model)

    if args.mode == "list":
        print(f"{len(exprs)} expression")
        for e in exprs:
            ni = sum(len(s["instrs"]) for s in e["streams"])
            print(f"  {e['name']:<32} sig={e['signature']:<12} "
                  f"unk7C={e['unk7c']} tracks={len(e['tracks']):<4} "
                  f"stream={len(e['streams'])} instr={ni:<6} "
                  f"spring={len(e['springs'])}")
        return 0

    if args.mode == "verify":
        bad = 0
        unsup = collections.Counter()
        for e in exprs:
            try:
                writes, errors = analyse(e)
            except Unsupported as u:
                unsup[str(u)] += 1
                print(f"  [!] {e['name']}: bilinmeyen op {u}")
                bad += 1
                continue
            if errors:
                bad += 1
                print(f"  [!] {e['name']}: {len(errors)} sorun")
                for x in errors[:4]:
                    print(f"        {x}")
            else:
                print(f"  [ok] {e['name']:<32} {len(writes)} yazim, yigin dengeli")
        print(f"\n[=] {len(exprs)-bad}/{len(exprs)} expression temiz")
        if unsup:
            print(f"[!] bilinmeyen op: {dict(unsup)}")
        return 1 if bad else 0

    for e in exprs:
        writes, errors = analyse(e)
        print(f"===== {e['name']}  (sig={e['signature']}, Unk7C={e['unk7c']})")
        if errors:
            print(f"  [!] {len(errors)} analiz uyarisi (ilk 3): {errors[:3]}")
        ins, outs = split_io(writes)

        if args.mode == "io":
            byt = collections.Counter((t, f) for _, t, f, _ in e["tracks"])
            print(f"  Tracks bildirimi: {len(e['tracks'])}")
            for (t, f), n in sorted(byt.items()):
                print(f"    Track {t:<4}{TRACK_NAMES.get(t,''):<14} "
                      f"format={FORMAT_NAMES.get(f,f):<11} x{n}")
            print(f"\n  GIRIS kanallari ({len(ins)}):")
            for c in sorted(ins):
                print(f"    {fmt(c, bones)}")
            print(f"\n  CIKIS kanallari ({len(outs)}):")
            for c in sorted(outs):
                print(f"    {fmt(c, bones)}")

        elif args.mode == "drives":
            agg = collections.defaultdict(set)
            for out, src, _ in writes:
                agg[(out[0], out[1])] |= {c for c in src if c in ins}
            for k in sorted(agg, key=lambda k: (bones.get(k[0], "~"), k[1])):
                print(f"  {fmt(k, bones)}")
                s = sorted(agg[k])
                print("      <- " + (", ".join(fmt(c, bones) for c in s)
                                     if s else "(sabit / spring / zaman)"))

        elif args.mode == "channels":
            agg = collections.defaultdict(set)
            for out, src, _ in writes:
                for c in src:
                    if c in ins:
                        agg[c].add((out[0], out[1]))
            print(f"  {len(agg)} giris kanali\n")
            for c in sorted(agg, key=lambda c: -len(agg[c])):
                tgt = sorted(agg[c], key=lambda k: (bones.get(k[0], "~"), k[1]))
                print(f"  {fmt(c, bones)}  -> {len(tgt)} cikis")
                for k in tgt:
                    print(f"        {fmt(k, bones)}")

        elif args.mode == "springs":
            print(f"  {len(e['springs'])} DefineSpring")
            for sp in e["springs"]:
                print(f"    {fmt(sp['chan'], bones)}")
                for k, v in sp["raw"].items():
                    if k not in ("BoneId", "Track", "Format", "ComponentIndex"):
                        print(f"        {k} = {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
