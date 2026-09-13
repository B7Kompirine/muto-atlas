#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_blender_render.py — parcacik sprite'ini BLENDER'da RENDER eder.

⛔ NEDEN: numpy ile hesaplanan siluet profesyonel durmuyor. Olculdu ve
   arastirildi -- vanilla'nin `ptfx_multi_sheet_00N_debris` atlaslari
   fotograf/3B render kaynakli, elle cizilmis degil; VFXDoc ve sektor
   kaynaklari da ayni seyi soyluyor: modelle/simule et, RENDER et,
   dokuya pisir.

Bu betik Blender'i ARKA PLANDA (-b) calistirir, tek bir kati parcayi
uretir, uc noktali isikla aydinlatir, ORTOGRAFIK ve saydam zeminle
render eder. Cikti dogrudan parcacik sprite'i olarak kullanilabilir.

Malzemeler: beton · cam · tahta · metal · kagit · buz

Kullanim:
  python ptfx_blender_render.py --malzeme beton --cikti out.png
  python ptfx_blender_render.py --malzeme cam --coz 512 --tohum 7
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

BLENDER = r"C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe"

# Blender icinde calisacak betik. `--` sonrasi argumanlari okur.
SAHNE = r'''
import bpy, bmesh, math, random, sys, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
malzeme, cikti, coz, tohum = argv[0], argv[1], int(argv[2]), int(argv[3])
random.seed(tohum)

# --- temiz sahne ---
bpy.ops.wm.read_factory_settings(use_empty=True)
sahne = bpy.context.scene

# --- malzeme tanimlari: (parca sayisi, puruzluluk, metalik, taban_renk, sekil) ---
TANIM = {
    "beton": dict(n=1, kaba=0.95, met=0.0, renk=(0.46, 0.44, 0.41, 1), sekil="blok",
                  bicim=(1.0, 0.86, 0.80), catlak=0.16),
    "cam":   dict(n=1, kaba=0.04, met=0.0, renk=(0.62, 0.76, 0.84, 1), sekil="levha",
                  bicim=(1.0, 0.90, 0.045), catlak=0.0),
    "tahta": dict(n=1, kaba=0.80, met=0.0, renk=(0.44, 0.29, 0.15, 1), sekil="cubuk",
                  bicim=(1.0, 0.17, 0.13), catlak=0.10),
    "metal": dict(n=1, kaba=0.35, met=0.9, renk=(0.55, 0.56, 0.58, 1), sekil="levha",
                  bicim=(1.0, 0.60, 0.12), catlak=0.20),
    "kagit": dict(n=1, kaba=0.88, met=0.0, renk=(0.80, 0.78, 0.72, 1), sekil="levha",
                  bicim=(1.0, 0.78, 0.015), catlak=0.0),
    "buz":   dict(n=1, kaba=0.15, met=0.0, renk=(0.78, 0.88, 0.94, 1), sekil="blok",
                  bicim=(1.0, 0.90, 0.80), catlak=0.10),
}
t = TANIM[malzeme]

# --- geometri: duzensiz konveks parca ---
bpy.ops.mesh.primitive_cube_add(size=2.0)
ob = bpy.context.active_object
ob.scale = t["bicim"]
bpy.ops.object.transform_apply(scale=True)

me = ob.data
bm = bmesh.new(); bm.from_mesh(me)

# koseleri rastgele it -> duzensiz kati
for v in bm.verts:
    v.co.x += random.uniform(-0.34, 0.34)
    v.co.y += random.uniform(-0.34, 0.34)
    v.co.z += random.uniform(-0.30, 0.30)

# birkac kez bol ve tekrar it -> daha zengin siluet
# ⚠ Blok malzemede YUZEYI bozma: bir kez bol, yalniz kaba bir
#   duzensizlik ver. Iki tur bolup her vertex'i itmek yuzeyi
#   lumpy yapiyor ve kati cisim hissi kayboluyor.
if t["catlak"] > 0.01:
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1,
                              use_grid_fill=True)
    k = t["catlak"]
    for v in bm.verts:
        v.co += Vector((random.uniform(-k, k), random.uniform(-k, k),
                        random.uniform(-k, k)))
    bmesh.ops.convex_hull(bm, input=bm.verts)

# cam/kagit: keskin kose istiyoruz -> konveks kabuk
if t["sekil"] == "levha":
    bmesh.ops.convex_hull(bm, input=bm.verts)

bm.to_mesh(me); bm.free()
me.update()

# tahta icin uzun eksende lif hissi: hafif kirisim
if malzeme == "tahta":
    m = ob.modifiers.new("simple", "SIMPLE_DEFORM")
    m.deform_method = "TWIST"; m.angle = math.radians(random.uniform(-25, 25))

# kose yumusatma (cam haric: cam keskin kalir)
if malzeme != "cam":
    bev = ob.modifiers.new("bevel", "BEVEL")
    bev.width = 0.02; bev.segments = 2
# ⛔ SHADE_SMOOTH ENKAZI BURUSUK KAGIDA CEVIRIR. Kati parca
#    KOSELIDIR: duz gölgeleme her yuzeyi ayri okutur, siluet ve
#    hacim boyle cikar. (Ilk render'da beton buruşuk torba gibiydi.)
bpy.ops.object.shade_flat()
ob.rotation_euler = (random.uniform(0, math.tau), random.uniform(0, math.tau),
                     random.uniform(0, math.tau))

# --- malzeme ---
mat = bpy.data.materials.new("m"); mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = t["renk"]
bsdf.inputs["Roughness"].default_value = t["kaba"]
bsdf.inputs["Metallic"].default_value = t["met"]
if malzeme in ("cam", "buz"):
    # ⛔ Gercek transmission oyunda islevsiz (sprite alfaya piser) ve
    #    render'i yavaslatir; camin okunmasini KENAR PARLAMASI saglar.
    bsdf.inputs["Roughness"].default_value = 0.05
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 1.0
ob.data.materials.append(mat)

# --- uc noktali isik: sekli okutan sey budur ---
def isik(ad, konum, guc, boy, renk=(1, 1, 1)):
    d = bpy.data.lights.new(ad, type="AREA")
    d.energy = guc; d.size = boy; d.color = renk
    o = bpy.data.objects.new(ad, d); sahne.collection.objects.link(o)
    o.location = konum
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(konum)).to_track_quat('-Z', 'Y').to_euler()
    return o

# ⛔ 900 W beton'u BEYAZA patlatti. Enkaz orta tonda okunmali.
isik("anahtar", (2.6, -2.2, 3.0), 260, 2.2, (1.0, 0.95, 0.88))
isik("dolgu",   (-3.0, -1.6, 0.6), 90, 4.0, (0.66, 0.76, 1.0))
isik("kenar",   (0.4, 3.2, 1.4), 150, 1.6, (1.0, 1.0, 1.0))

# --- ortografik kamera: sprite icin sart (perspektif carpitir) ---
kam_d = bpy.data.cameras.new("kam"); kam_d.type = "ORTHO"
kam_d.ortho_scale = 3.1
kam = bpy.data.objects.new("kam", kam_d); sahne.collection.objects.link(kam)
kam.location = (0, -6, 0); kam.rotation_euler = (math.radians(90), 0, 0)
sahne.camera = kam

# --- render ayarlari ---
# ⛔ Motor adini `RenderEngine.__subclasses__()` ile tarama: Blender 5.x'te
#    `HydraRenderEngine`in `bl_idname`i YOK ve AttributeError atiyor.
#    Dogrusu enum'un kendi ogelerine bakmak.
_motorlar = {e.identifier for e in
             bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
for _m in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
    if _m in _motorlar:
        sahne.render.engine = _m
        break
try:
    sahne.eevee.taa_render_samples = 64
except Exception:
    pass
sahne.render.film_transparent = True          # SAYDAM zemin -> alfa hazir
sahne.render.resolution_x = coz
sahne.render.resolution_y = coz
sahne.render.image_settings.file_format = "PNG"
sahne.render.image_settings.color_mode = "RGBA"
sahne.render.filepath = cikti
bpy.ops.render.render(write_still=True)
print("RENDER_TAMAM", cikti)
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--malzeme", required=True,
                    choices=["beton", "cam", "tahta", "metal", "kagit", "buz"])
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--coz", type=int, default=512)
    ap.add_argument("--tohum", type=int, default=0)
    a = ap.parse_args()

    if not os.path.exists(BLENDER):
        raise SystemExit("blender.exe yok: %s" % BLENDER)

    fd, betik = tempfile.mkstemp(suffix=".py")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(SAHNE)
    try:
        r = subprocess.run(
            [BLENDER, "-b", "--factory-startup", "-noaudio", "-P", betik, "--",
             a.malzeme, a.cikti, str(a.coz), str(a.tohum)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=600)
        if "RENDER_TAMAM" not in (r.stdout or ""):
            son = (r.stdout or "") + (r.stderr or "")
            print(son.strip()[-1500:])
            return 1
        print("render: %s (%d bayt)" % (a.cikti, os.path.getsize(a.cikti)))
        return 0
    finally:
        try:
            os.remove(betik)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
