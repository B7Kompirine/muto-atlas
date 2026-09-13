#!/usr/bin/env python3
"""light_scene.py — bir .ydr/.yft'yi ISIK EDITORUNUN sahnesine cevirir.

NEDEN VAR
=========
Isigi duzenlemek icin onu GORMEK gerekiyor; gormek icin de prop'un kendi
geometrisi lazim. Bu modul XML turundan uc seyi cikarir ve tek bir sozluk
dondurur: mesh (pozisyon/normal/vertex rengi/ucgen), iskelet (kemik dunya
matrisleri) ve isiklar (40 alanin tamami + hesaplanmis dunya konumu).

OLCULEN, TAHMIN EDILMEYEN
=========================
* **Isik KEMIGE baglidir, modelin orijinine degil.** `prop_worklight_01a`de
  isik `BoneId=41615` (`Worklight_01A_Bulb`) uzerindedir ve o kemik zincirde
  1.737 m yukaridadir. Kemik zinciri uygulanmazsa isik yerde durur ve
  "isigim calismiyor" denir. Isigin `Position/Direction/Tangent` alanlari
  KEMIK UZAYINDADIR.
* **Vertex'ler de kemik uzayinda olabilir** (`HasSkin=1`). Prop'larda
  agirlik neredeyse her zaman tek kemige %100'dur, yani rijittir: en agir
  kemigin dunya matrisi uygulanir. Bu yapilmazsa cok parcali prop'lar
  (vinc, direk) ust uste yigilir.
* Layout `<Layout type="GTAV1">` altindaki COCUK SIRASI ile okunur; her
  semantigin bilesen sayisi sabittir. Bilinmeyen bir semantik gorulurse
  SESSIZCE ATLANMAZ, hata verilir -- yoksa satir kayar ve normal sanilan
  sey aslinda UV olur.
* Vertex rengi GTA'da MASKEDIR (dogal/yapay ortam kapisi), gorunur renk
  degil. Ham bayt/255 alinir; gamma cozulmez.

KULLANIM
========
    import light_scene
    s = light_scene.oku("prop_lamp.ydr")      # -> sozluk
    light_scene.yaz_json(s, "sahne.json")
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_xml import kok_oku  # noqa: E402

# Bir semantigin kac sayi tuketdigi. Layout cocuk sirasi = veri sutun sirasi.
# Bilinmeyen semantik = HATA (bkz. docstring): satir kaymasi sessiz bozulmadir.
SEMANTIK = {
    "Position": 3, "Normal": 3, "Binormal": 3,
    "BlendWeights": 4, "BlendIndices": 4, "Colour0": 4, "Colour1": 4,
    "Tangent": 4,
}
for _i in range(8):
    SEMANTIK["TexCoord%d" % _i] = 2

# Ucgen tavani. Asilirsa KIRPILDIGI SOYLENIR (sessiz kirpma yok).
MAKS_UCGEN = 400_000


# ------------------------------------------------------------------ matematik

def _birim():
    return [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]


def _carp(a, b):
    """Satir-major 4x4; nokta satir vektoru olarak sagdan carpilir (p*M)."""
    o = [0.0] * 16
    for r in range(4):
        for c in range(4):
            o[r * 4 + c] = sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4))
    return o


def _trs(t, q, s):
    x, y, z, w = q
    xx, yy, zz = x * x, y * y, z * z
    m = [
        1 - 2 * (yy + zz), 2 * (x * y + z * w), 2 * (x * z - y * w), 0.0,
        2 * (x * y - z * w), 1 - 2 * (xx + zz), 2 * (y * z + x * w), 0.0,
        2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (xx + yy), 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    for r in range(3):
        for c in range(3):
            m[r * 4 + c] *= s[r]
    m[12], m[13], m[14] = t
    return m


def _nokta(m, p):
    return [p[0] * m[0] + p[1] * m[4] + p[2] * m[8] + m[12],
            p[0] * m[1] + p[1] * m[5] + p[2] * m[9] + m[13],
            p[0] * m[2] + p[1] * m[6] + p[2] * m[10] + m[14]]


def _yon(m, v):
    o = [v[0] * m[0] + v[1] * m[4] + v[2] * m[8],
         v[0] * m[1] + v[1] * m[5] + v[2] * m[9],
         v[0] * m[2] + v[1] * m[6] + v[2] * m[10]]
    n = math.sqrt(sum(c * c for c in o))
    return [c / n for c in o] if n > 1e-9 else [0.0, 0.0, -1.0]


# --------------------------------------------------------------- XML yardimci

def _xyz(el, d=(0.0, 0.0, 0.0)):
    if el is None:
        return list(d)
    return [float(el.get(a, dd)) for a, dd in zip("xyz", d)]


def _v(el, d=0.0):
    if el is None:
        return d
    try:
        return float(el.get("value"))
    except (TypeError, ValueError):
        return d


# ------------------------------------------------------------------- iskelet

def _kemikler(kok):
    """ad/tag -> dunya matrisi. Zincir ebeveynden cocuga cozulur."""
    bones = kok.find(".//Skeleton/Bones")
    if bones is None:
        # ⛔ ISKELETSIZ DRAWABLE'DA DA AYNI BICIM DONMELI.
        # Bos dict donunce cagiranlar kmap["tag"] / kmap["idx"] derken
        # KeyError atiyordu ve hata "IC HATA: KeyError: 'idx'" diye cikip
        # sebebini gizliyordu. Statik prop'larin cogunda iskelet yoktur
        # (v_2_bds_mesh_ceiling boyle) -- yani isik duzenleme o dosyalarda
        # hic calismiyordu.
        return [], {"tag": {}, "idx": {}}
    ham = []
    for b in bones:
        ham.append({
            "ad": b.findtext("Name", ""),
            "tag": int(_v(b.find("Tag"))),
            "idx": int(_v(b.find("Index"))),
            "parent": int(_v(b.find("ParentIndex"), -1)),
            "t": _xyz(b.find("Translation")),
            "q": [float(b.find("Rotation").get(a, d)) for a, d in
                  zip("xyzw", (0, 0, 0, 1))] if b.find("Rotation") is not None
                 else [0.0, 0.0, 0.0, 1.0],
            "s": _xyz(b.find("Scale"), (1.0, 1.0, 1.0)),
        })
    ile_idx = {b["idx"]: b for b in ham}
    for b in ham:                      # ebeveyn once cozulmus olmali
        b["_yerel"] = _trs(b["t"], b["q"], b["s"])
    def dunya(b):
        if "_M" in b:
            return b["_M"]
        p = ile_idx.get(b["parent"])
        b["_M"] = _carp(b["_yerel"], dunya(p)) if p is not None else b["_yerel"]
        return b["_M"]
    for b in ham:
        dunya(b)
    tag_map = {b["tag"]: b["_M"] for b in ham}
    idx_map = {b["idx"]: b["_M"] for b in ham}
    # Yerel bind TRS + parent de disari verilir: animasyon YEREL donusumu
    # degistirir, dunya matrisi hiyerarsiden yeniden kurulur. Sadece dunya
    # matrisi verilirse animasyon uygulanamaz.
    return ([{"ad": b["ad"], "tag": b["tag"], "idx": b["idx"],
              "parent": b["parent"], "t": b["t"], "q": b["q"], "s": b["s"],
              "M": b["_M"]}
             for b in ham], {"tag": tag_map, "idx": idx_map})


# ---------------------------------------------------------------------- mesh

def _layout(vb):
    lay = vb.find("Layout")
    if lay is None:
        raise ValueError("no <Layout> inside VertexBuffer")
    alanlar, ofset = [], 0
    for c in lay:
        n = SEMANTIK.get(c.tag)
        if n is None:
            # Sessiz atlama satiri kaydirir: normal sanilan sey UV olur.
            raise ValueError("unknown vertex semantic: %s "
                             "(add it to the SEMANTIK table)" % c.tag)
        alanlar.append((c.tag, ofset, n))
        ofset += n
    return alanlar, ofset


def _geometriler(kok):
    """Tum LOD-High geometrileri; kemik uzayindakiler dunyaya tasinir."""
    dm = kok.find(".//DrawableModelsHigh")
    if dm is None:
        dm = kok.find(".//DrawableModels")
    return dm


def oku(path, maks_ucgen=MAKS_UCGEN, bake=True):
    """bake=True  : kemik donusumu vertex'e PISIRILIR (statik onizleme).
    bake=False : vertex kemik uzayinda BIRAKILIR + kemik indeksi/agirligi
                 disari verilir. Animasyon oynatilacaksa bu sarttir --
                 pisirilmis vertex'e animasyon uygulanamaz, kemik donusumu
                 iki kez girer ve model daginir.
    """
    # kok_oku (kok, hata) doner. Hata YUTULMAZ: "cevirici yok" durumu
    # "dosya bos" diye raporlanirsa sebep kaybolur.
    kok, hata = kok_oku(path)
    if hata:
        raise RuntimeError(hata)
    tip = kok.tag
    kemik_list, kmap = _kemikler(kok)

    pos, nrm, col, idx = [], [], [], []
    bidx, bagirlik = [], []        # skinning (bake=False)
    kemik_sira = [b["idx"] for b in kemik_list]
    sira_ile = {v: k for k, v in enumerate(kemik_sira)}
    kirpildi = 0
    dm = _geometriler(kok)
    if dm is not None:
        for model in dm:
            has_skin = int(_v(model.find("HasSkin"))) == 1
            bone_idx = int(_v(model.find("BoneIndex")))
            geos = model.find("Geometries")
            if geos is None:
                continue
            for g in geos:
                vb = g.find("VertexBuffer")
                ib = g.find("IndexBuffer")
                if vb is None or ib is None:
                    continue
                alanlar, genislik = _layout(vb)
                ham = (vb.findtext("Data") or "").split()
                if not ham or genislik == 0:
                    continue
                n_vert = len(ham) // genislik
                bone_ids = [int(x) for x in
                            (g.findtext("BoneIDs") or "").replace(",", " ").split()]
                yer = {a: (o, n) for a, o, n in alanlar}
                p_o = yer["Position"][0]
                n_o = yer.get("Normal", (None, 0))[0]
                c_o = yer.get("Colour0", (None, 0))[0]
                bi_o = yer.get("BlendIndices", (None, 0))[0]
                bw_o = yer.get("BlendWeights", (None, 0))[0]

                taban = len(pos) // 3
                for i in range(n_vert):
                    b = i * genislik
                    p = [float(ham[b + p_o]), float(ham[b + p_o + 1]),
                         float(ham[b + p_o + 2])]
                    nv = ([float(ham[b + n_o]), float(ham[b + n_o + 1]),
                           float(ham[b + n_o + 2])] if n_o is not None
                          else [0.0, 0.0, 1.0])
                    # Kemik uzayi -> dunya. Prop'ta agirlik tek kemige %100.
                    M = None
                    dort = []          # [(kemik_sirasi, agirlik) x4]
                    if has_skin and bi_o is not None and bone_ids:
                        en, eni = -1.0, 0
                        for k in range(4):
                            w = (float(ham[b + bw_o + k]) if bw_o is not None
                                 else (255.0 if k == 0 else 0.0))
                            bi = int(float(ham[b + bi_o + k]))
                            if w > en:
                                en, eni = w, bi
                            gi = (sira_ile.get(bone_ids[bi], 0)
                                  if bi < len(bone_ids) else 0)
                            dort.append((gi, w / 255.0))
                        if eni < len(bone_ids):
                            M = kmap["idx"].get(bone_ids[eni])
                    else:
                        M = kmap["idx"].get(bone_idx)
                        dort = [(sira_ile.get(bone_idx, 0), 1.0),
                                (0, 0.0), (0, 0.0), (0, 0.0)]
                    if bake and M:
                        p = _nokta(M, p)
                        nv = _yon(M, nv)
                    if not bake:
                        while len(dort) < 4:
                            dort.append((0, 0.0))
                        t = sum(w for _, w in dort) or 1.0
                        bidx.extend([d[0] for d in dort[:4]])
                        bagirlik.extend([d[1] / t for d in dort[:4]])
                    pos.extend(p)
                    nrm.extend(nv)
                    if c_o is not None:
                        col.extend([float(ham[b + c_o + k]) / 255.0
                                    for k in range(4)])
                    else:
                        col.extend([1.0, 1.0, 1.0, 1.0])

                ham_i = [int(x) for x in (ib.findtext("Data") or "").split()]
                for k in range(0, len(ham_i) - 2, 3):
                    if len(idx) // 3 >= maks_ucgen:
                        kirpildi += 1
                        continue
                    idx.extend([ham_i[k] + taban, ham_i[k + 1] + taban,
                                ham_i[k + 2] + taban])

    isiklar = _isiklar(kok, kmap)
    # bake=False'ta bbox kemik uzayindaki noktalardan cikar ve YANLIS olur;
    # kutuyu bind pozunda hesapla ki kamera dogru cerceve kursun.
    bbox_kaynak = pos
    if not bake:
        # ⛔ SLOT 0'I KORLEMESINE ALMA. Olculdu: `v_ilev_fib_door1_s`in
        # 330 vertexinin **%100'unde** slot 0'in agirligi sifirdir; gercek
        # kemik 2. slottadir. Slot 0'i almak birim matris secip bbox'i
        # 1.096 m yanlis verdi -- ve bbox hem kamerayi hem YMAP EXTENT'ini
        # besler, extent disinda kalan entity ise sessizce hic gorunmez.
        # Dogrusu agirlikli harman: pisirilmis sonucla birebir tutar.
        bbox_kaynak = []
        for v in range(len(pos) // 3):
            p = pos[v * 3:v * 3 + 3]
            acc, tw = [0.0, 0.0, 0.0], 0.0
            for k in range(4):
                w = bagirlik[v * 4 + k] if bagirlik else (1.0 if k == 0 else 0.0)
                if w <= 0.0:
                    continue
                gi = bidx[v * 4 + k] if bidx else 0
                M = kmap["idx"].get(kemik_sira[gi] if gi < len(kemik_sira) else 0)
                q = _nokta(M, p) if M else p
                for c in range(3):
                    acc[c] += q[c] * w
                tw += w
            bbox_kaynak.extend(acc if tw > 0 else p)
    bmin, bmax = _bbox(bbox_kaynak)
    mesh = {"pos": pos, "nrm": nrm, "col": col, "idx": idx}
    if not bake:
        mesh["bidx"] = bidx
        mesh["bw"] = bagirlik
    return {
        "ad": os.path.splitext(os.path.basename(path))[0],
        "tip": tip,
        "bake": bake,
        "bbox": {"min": bmin, "max": bmax},
        "mesh": mesh,
        "kemikler": kemik_list,
        "kemik_sira": kemik_sira,
        "isiklar": isiklar,
        "kirpilan_ucgen": kirpildi,
    }


def _bbox(pos):
    if not pos:
        return [-1.0, -1.0, 0.0], [1.0, 1.0, 2.0]
    mn = [min(pos[i::3]) for i in range(3)]
    mx = [max(pos[i::3]) for i in range(3)]
    return mn, mx


# -------------------------------------------------------------------- isiklar

# Editorun dokunabildigi alanlar. Geri yazma da bu adlarla yapilir.
ALANLAR_F = ["Intensity", "Falloff", "FalloffExponent", "ConeInnerAngle",
             "ConeOuterAngle", "CoronaSize", "CoronaIntensity", "CoronaZBias",
             "VolumeIntensity", "VolumeSizeScale", "VolumeOuterIntensity",
             "VolumeOuterExponent", "ShadowBlur", "ShadowNearClip",
             "ShadowFadeDistance", "SpecularFadeDistance",
             "VolumetricFadeDistance", "LightFadeDistance",
             "CullingPlaneOffset"]
ALANLAR_I = ["Flags", "TimeFlags", "BoneId", "GroupId", "Flashiness",
             "LightHash", "Unknown45", "Unknown46"]

TIP_NO = {"Point": 1, "Spot": 2, "Capsule": 4}


def _isiklar(kok, kmap):
    L = kok.find("Lights")
    if L is None:
        L = kok.find(".//Lights")
    out = []
    if L is None:
        return out
    for i, it in enumerate(L):
        d = {"_i": i, "Type": (it.findtext("Type") or "Point").strip()}
        d["Position"] = _xyz(it.find("Position"))
        d["Direction"] = _xyz(it.find("Direction"), (0.0, 0.0, -1.0))
        d["Tangent"] = _xyz(it.find("Tangent"), (1.0, 0.0, 0.0))
        d["Extent"] = _xyz(it.find("Extent"), (1.0, 1.0, 1.0))
        d["CullingPlaneNormal"] = _xyz(it.find("CullingPlaneNormal"))
        c = it.find("Colour")
        d["Colour"] = [int(float(c.get(k, 255))) for k in "rgb"] if c is not None \
            else [255, 255, 255]
        vc = it.find("VolumeOuterColour")
        d["VolumeOuterColour"] = [int(float(vc.get(k, 255))) for k in "rgb"] \
            if vc is not None else [255, 255, 255]
        for a in ALANLAR_F:
            d[a] = _v(it.find(a))
        for a in ALANLAR_I:
            d[a] = int(_v(it.find(a)))
        d["ProjectedTextureHash"] = (it.findtext("ProjectedTextureHash") or "").strip()

        # Kemik uzayi -> dunya. Kemik yoksa birim (model orijini).
        M = kmap["tag"].get(d["BoneId"]) or _birim()
        d["_dunya"] = {
            "pos": _nokta(M, d["Position"]),
            "dir": _yon(M, d["Direction"]),
            "tan": _yon(M, d["Tangent"]),
            "M": M,
        }
        d["_tipno"] = TIP_NO.get(d["Type"], 1)
        out.append(d)
    return out


def yaz_json(sahne, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sahne, fh, separators=(",", ":"))
    return path


if __name__ == "__main__":
    s = oku(sys.argv[1])
    print("%s (%s): %d triangles, %d vertices, %d bones, %d lights" % (
        s["ad"], s["tip"], len(s["mesh"]["idx"]) // 3,
        len(s["mesh"]["pos"]) // 3, len(s["kemikler"]), len(s["isiklar"])))
    for l in s["isiklar"]:
        print("  #%d %-8s world=%s" % (l["_i"], l["Type"],
                                       [round(v, 3) for v in l["_dunya"]["pos"]]))
