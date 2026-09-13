#!/usr/bin/env python3
"""light_scene.py — turns a .ydr/.yft into the LIGHT EDITOR's scene.

WHY IT EXISTS
=============
To edit a light you need to SEE it; to see it you need the prop's own
geometry. This module pulls three things out of the XML and returns a single
dict: mesh (position/normal/vertex colour/triangles), skeleton (bone world
matrices) and lights (all 40 fields + the computed world position).

MEASURED, NOT GUESSED
=====================
* **A light is bound to a BONE, not to the model origin.** In `prop_worklight_01a`
  the light sits on `BoneId=41615` (`Worklight_01A_Bulb`) and that bone is
  1.737 m up the chain. If the bone chain is not applied the light sits on the
  ground and people say "my light does not work". The light's
  `Position/Direction/Tangent` fields are IN BONE SPACE.
* **Vertices can be in bone space too** (`HasSkin=1`). In props the weight is
  almost always 100% on a single bone, i.e. rigid: the world matrix of the
  heaviest bone is applied. Without this, multi-part props (crane, pole) pile
  up on top of each other.
* The layout is read in the CHILD ORDER under `<Layout type="GTAV1">`; each
  semantic has a fixed component count. An unknown semantic is NOT SILENTLY
  SKIPPED, it raises an error -- otherwise the row shifts and what you take
  for the normal is really the UV.
* Vertex colour in GTA is a MASK (natural/artificial ambient gate), not a
  visible colour. The raw byte/255 is taken; gamma is not decoded.

USAGE
=====
    import light_scene
    s = light_scene.read_scene("prop_lamp.ydr")      # -> dict
    light_scene.write_json(s, "scene.json")
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_xml import read_root  # noqa: E402

# How many numbers a semantic consumes. Layout child order = data column order.
# Unknown semantic = ERROR (see the docstring): a row shift is silent corruption.
SEMANTICS = {
    "Position": 3, "Normal": 3, "Binormal": 3,
    "BlendWeights": 4, "BlendIndices": 4, "Colour0": 4, "Colour1": 4,
    "Tangent": 4,
}
for _i in range(8):
    SEMANTICS["TexCoord%d" % _i] = 2

# Triangle ceiling. When it is exceeded the CLIPPING IS REPORTED (no silent clipping).
MAX_TRIANGLES = 400_000


# ------------------------------------------------------------------------ math

def _identity():
    return [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]


def _mul(a, b):
    """Row-major 4x4; a point is a row vector multiplied from the right (p*M)."""
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


def _point(m, p):
    return [p[0] * m[0] + p[1] * m[4] + p[2] * m[8] + m[12],
            p[0] * m[1] + p[1] * m[5] + p[2] * m[9] + m[13],
            p[0] * m[2] + p[1] * m[6] + p[2] * m[10] + m[14]]


def _direction(m, v):
    o = [v[0] * m[0] + v[1] * m[4] + v[2] * m[8],
         v[0] * m[1] + v[1] * m[5] + v[2] * m[9],
         v[0] * m[2] + v[1] * m[6] + v[2] * m[10]]
    n = math.sqrt(sum(c * c for c in o))
    return [c / n for c in o] if n > 1e-9 else [0.0, 0.0, -1.0]


# ----------------------------------------------------------------- XML helpers

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


# -------------------------------------------------------------------- skeleton

def _bones(root):
    """name/tag -> world matrix. The chain is resolved from parent to child."""
    bones = root.find(".//Skeleton/Bones")
    if bones is None:
        # ⛔ A DRAWABLE WITHOUT A SKELETON MUST RETURN THE SAME SHAPE TOO.
        # With an empty dict the callers raised KeyError on kmap["tag"] / kmap["idx"],
        # and the error came out as "INTERNAL ERROR: KeyError: 'idx'", hiding
        # the cause. Most static props have no skeleton
        # (v_2_bds_mesh_ceiling is one) -- so light editing did not work
        # on those files at all.
        return [], {"tag": {}, "idx": {}}
    raw = []
    for b in bones:
        raw.append({
            "name": b.findtext("Name", ""),
            "tag": int(_v(b.find("Tag"))),
            "idx": int(_v(b.find("Index"))),
            "parent": int(_v(b.find("ParentIndex"), -1)),
            "t": _xyz(b.find("Translation")),
            "q": [float(b.find("Rotation").get(a, d)) for a, d in
                  zip("xyzw", (0, 0, 0, 1))] if b.find("Rotation") is not None
                 else [0.0, 0.0, 0.0, 1.0],
            "s": _xyz(b.find("Scale"), (1.0, 1.0, 1.0)),
        })
    by_idx = {b["idx"]: b for b in raw}
    for b in raw:                      # the parent must be resolved first
        b["_local"] = _trs(b["t"], b["q"], b["s"])
    def world(b):
        if "_M" in b:
            return b["_M"]
        p = by_idx.get(b["parent"])
        b["_M"] = _mul(b["_local"], world(p)) if p is not None else b["_local"]
        return b["_M"]
    for b in raw:
        world(b)
    tag_map = {b["tag"]: b["_M"] for b in raw}
    idx_map = {b["idx"]: b["_M"] for b in raw}
    # The local bind TRS + parent are exported too: an animation changes the LOCAL
    # transform and the world matrix is rebuilt from the hierarchy. With only the
    # world matrix exported, an animation cannot be applied.
    return ([{"ad": b["name"], "tag": b["tag"], "idx": b["idx"],
              "parent": b["parent"], "t": b["t"], "q": b["q"], "s": b["s"],
              "M": b["_M"]}
             for b in raw], {"tag": tag_map, "idx": idx_map})


# ------------------------------------------------------------------------ mesh

def _layout(vb):
    lay = vb.find("Layout")
    if lay is None:
        raise ValueError("no <Layout> inside VertexBuffer")
    fields, offset = [], 0
    for c in lay:
        n = SEMANTICS.get(c.tag)
        if n is None:
            # A silent skip shifts the row: what you take for the normal becomes the UV.
            raise ValueError("unknown vertex semantic: %s "
                             "(add it to the SEMANTICS table)" % c.tag)
        fields.append((c.tag, offset, n))
        offset += n
    return fields, offset


def _geometries(root):
    """All LOD-High geometries; the ones in bone space are moved to world space."""
    dm = root.find(".//DrawableModelsHigh")
    if dm is None:
        dm = root.find(".//DrawableModels")
    return dm


def read_scene(path, max_triangles=MAX_TRIANGLES, bake=True):
    """bake=True  : the bone transform is BAKED into the vertices (static preview).
    bake=False : vertices are LEFT in bone space + bone index/weight are
                 exported. Required when an animation will be played --
                 an animation cannot be applied to baked vertices, the bone
                 transform enters twice and the model falls apart.
    """
    # read_root returns (root, error). The error is NOT SWALLOWED: if "no converter"
    # is reported as "empty file" the cause is lost.
    root, error = read_root(path)
    if error:
        raise RuntimeError(error)
    kind = root.tag
    bone_list, kmap = _bones(root)

    pos, nrm, col, idx = [], [], [], []
    bidx, bweight = [], []        # skinning (bake=False)
    bone_order = [b["idx"] for b in bone_list]
    order_of = {v: k for k, v in enumerate(bone_order)}
    clipped = 0
    dm = _geometries(root)
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
                fields, width = _layout(vb)
                raw = (vb.findtext("Data") or "").split()
                if not raw or width == 0:
                    continue
                n_vert = len(raw) // width
                bone_ids = [int(x) for x in
                            (g.findtext("BoneIDs") or "").replace(",", " ").split()]
                loc = {a: (o, n) for a, o, n in fields}
                p_o = loc["Position"][0]
                n_o = loc.get("Normal", (None, 0))[0]
                c_o = loc.get("Colour0", (None, 0))[0]
                bi_o = loc.get("BlendIndices", (None, 0))[0]
                bw_o = loc.get("BlendWeights", (None, 0))[0]

                base = len(pos) // 3
                for i in range(n_vert):
                    b = i * width
                    p = [float(raw[b + p_o]), float(raw[b + p_o + 1]),
                         float(raw[b + p_o + 2])]
                    nv = ([float(raw[b + n_o]), float(raw[b + n_o + 1]),
                           float(raw[b + n_o + 2])] if n_o is not None
                          else [0.0, 0.0, 1.0])
                    # Bone space -> world. In a prop the weight is 100% on one bone.
                    M = None
                    four = []          # [(bone_order, weight) x4]
                    if has_skin and bi_o is not None and bone_ids:
                        best, best_i = -1.0, 0
                        for k in range(4):
                            w = (float(raw[b + bw_o + k]) if bw_o is not None
                                 else (255.0 if k == 0 else 0.0))
                            bi = int(float(raw[b + bi_o + k]))
                            if w > best:
                                best, best_i = w, bi
                            gi = (order_of.get(bone_ids[bi], 0)
                                  if bi < len(bone_ids) else 0)
                            four.append((gi, w / 255.0))
                        if best_i < len(bone_ids):
                            M = kmap["idx"].get(bone_ids[best_i])
                    else:
                        M = kmap["idx"].get(bone_idx)
                        four = [(order_of.get(bone_idx, 0), 1.0),
                                (0, 0.0), (0, 0.0), (0, 0.0)]
                    if bake and M:
                        p = _point(M, p)
                        nv = _direction(M, nv)
                    if not bake:
                        while len(four) < 4:
                            four.append((0, 0.0))
                        t = sum(w for _, w in four) or 1.0
                        bidx.extend([d[0] for d in four[:4]])
                        bweight.extend([d[1] / t for d in four[:4]])
                    pos.extend(p)
                    nrm.extend(nv)
                    if c_o is not None:
                        col.extend([float(raw[b + c_o + k]) / 255.0
                                    for k in range(4)])
                    else:
                        col.extend([1.0, 1.0, 1.0, 1.0])

                raw_i = [int(x) for x in (ib.findtext("Data") or "").split()]
                for k in range(0, len(raw_i) - 2, 3):
                    if len(idx) // 3 >= max_triangles:
                        clipped += 1
                        continue
                    idx.extend([raw_i[k] + base, raw_i[k + 1] + base,
                                raw_i[k + 2] + base])

    lights = _lights(root, kmap)
    # With bake=False the bbox comes from points in bone space and is WRONG;
    # compute the box in the bind pose so the camera frames it correctly.
    bbox_src = pos
    if not bake:
        # ⛔ DO NOT TAKE SLOT 0 BLINDLY. Measured: in **100%** of the 330 vertices
        # of `v_ilev_fib_door1_s` the weight of slot 0 is zero; the real bone is
        # in the 2nd slot. Taking slot 0 picked the identity matrix and gave a bbox
        # 1.096 m off -- and the bbox feeds both the camera and the YMAP EXTENT,
        # while an entity outside the extent silently never shows.
        # The right way is a weighted blend: it matches the baked result exactly.
        bbox_src = []
        for v in range(len(pos) // 3):
            p = pos[v * 3:v * 3 + 3]
            acc, tw = [0.0, 0.0, 0.0], 0.0
            for k in range(4):
                w = bweight[v * 4 + k] if bweight else (1.0 if k == 0 else 0.0)
                if w <= 0.0:
                    continue
                gi = bidx[v * 4 + k] if bidx else 0
                M = kmap["idx"].get(bone_order[gi] if gi < len(bone_order) else 0)
                q = _point(M, p) if M else p
                for c in range(3):
                    acc[c] += q[c] * w
                tw += w
            bbox_src.extend(acc if tw > 0 else p)
    bmin, bmax = _bbox(bbox_src)
    mesh = {"pos": pos, "nrm": nrm, "col": col, "idx": idx}
    if not bake:
        mesh["bidx"] = bidx
        mesh["bw"] = bweight
    # The scene keys stay as they are (ad = name, tip = type, kemikler = bones,
    # kemik_sira = bone order, isiklar = lights, kirpilan_ucgen = clipped triangles):
    # light_edit.py reads them, and write_json() writes this dict out for the light editor.
    return {
        "ad": os.path.splitext(os.path.basename(path))[0],
        "tip": kind,
        "bake": bake,
        "bbox": {"min": bmin, "max": bmax},
        "mesh": mesh,
        "kemikler": bone_list,
        "kemik_sira": bone_order,
        "isiklar": lights,
        "kirpilan_ucgen": clipped,
    }


def _bbox(pos):
    if not pos:
        return [-1.0, -1.0, 0.0], [1.0, 1.0, 2.0]
    mn = [min(pos[i::3]) for i in range(3)]
    mx = [max(pos[i::3]) for i in range(3)]
    return mn, mx


# ---------------------------------------------------------------------- lights

# Fields the editor can touch. Writing back uses these names too.
FIELDS_F = ["Intensity", "Falloff", "FalloffExponent", "ConeInnerAngle",
            "ConeOuterAngle", "CoronaSize", "CoronaIntensity", "CoronaZBias",
            "VolumeIntensity", "VolumeSizeScale", "VolumeOuterIntensity",
            "VolumeOuterExponent", "ShadowBlur", "ShadowNearClip",
            "ShadowFadeDistance", "SpecularFadeDistance",
            "VolumetricFadeDistance", "LightFadeDistance",
            "CullingPlaneOffset"]
# The integer fields. light_edit.py reads light_scene.FIELDS_I.
FIELDS_I = ["Flags", "TimeFlags", "BoneId", "GroupId", "Flashiness",
             "LightHash", "Unknown45", "Unknown46"]

TYPE_NO = {"Point": 1, "Spot": 2, "Capsule": 4}


def _lights(root, kmap):
    L = root.find("Lights")
    if L is None:
        L = root.find(".//Lights")
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
        for a in FIELDS_F:
            d[a] = _v(it.find(a))
        for a in FIELDS_I:
            d[a] = int(_v(it.find(a)))
        d["ProjectedTextureHash"] = (it.findtext("ProjectedTextureHash") or "").strip()

        # Bone space -> world. No bone -> identity (model origin).
        # (_dunya = world, _tipno = type number: scene keys, kept.)
        M = kmap["tag"].get(d["BoneId"]) or _identity()
        d["_dunya"] = {
            "pos": _point(M, d["Position"]),
            "dir": _direction(M, d["Direction"]),
            "tan": _direction(M, d["Tangent"]),
            "M": M,
        }
        d["_tipno"] = TYPE_NO.get(d["Type"], 1)
        out.append(d)
    return out


def write_json(scene, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(scene, fh, separators=(",", ":"))
    return path


if __name__ == "__main__":
    s = read_scene(sys.argv[1])
    print("%s (%s): %d triangles, %d vertices, %d bones, %d lights" % (
        s["ad"], s["tip"], len(s["mesh"]["idx"]) // 3,
        len(s["mesh"]["pos"]) // 3, len(s["kemikler"]), len(s["isiklar"])))
    for l in s["isiklar"]:
        print("  #%d %-8s world=%s" % (l["_i"], l["Type"],
                                       [round(v, 3) for v in l["_dunya"]["pos"]]))
