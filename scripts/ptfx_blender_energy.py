#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_blender_energy.py — ENERJI ve SIVI sprite'larini Blender'da render eder.

`ptfx_blender_render.py` KATI parcalar icindir (beton/cam/tahta). Bu betik
onun kardesidir ve iki ayri aileyi kapsar:

  ENERJI (emissive + bloom):  halka · sok · emp · yildiz · kure · ark
  SIVI   (metaball):          damla · sicrama · tac · kan

⛔ NEDEN AYRI: enerji efektinde okunan sey GEOMETRI DEGIL ISIKTIR --
   emissive yuzey + bloom. Kati parcanin uc noktali isigi burada yanlis;
   tersine sahnede HIC dis isik olmamali, nesnenin kendisi isik yaymali.
   Sivida ise yuzey GERILIMI gerekir: ayri kureler degil, birlesip
   eriyen metaball'lar -- gercek damla boyle okunur.

Kullanim:
  python ptfx_blender_energy.py --tur halka --cikti out.png
  python ptfx_blender_energy.py --tur sicrama --cikti out.png --tohum 3
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile

BLENDER = r"C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe"

TURLER = ["halka", "sok", "emp", "yildiz", "kure", "ark",
          "damla", "sicrama", "tac", "kan"]

SAHNE = r'''
import bpy, bmesh, math, random, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
tur, cikti, coz, tohum = argv[0], argv[1], int(argv[2]), int(argv[3])
random.seed(tohum)

bpy.ops.wm.read_factory_settings(use_empty=True)
sahne = bpy.context.scene
ENERJI = tur in ("halka", "sok", "emp", "yildiz", "kure", "ark")


def emissive(ob, guc, renk=(1, 1, 1)):
    """⛔ Enerji efektinde dis isik YOK; nesne kendi isigini yayar."""
    m = bpy.data.materials.new("e")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (renk[0], renk[1], renk[2], 1)
    em.inputs["Strength"].default_value = guc
    nt.links.new(em.outputs["Emission"],
                 nt.nodes["Material Output"].inputs["Surface"])
    ob.data.materials.append(m)
    return ob


def cember(yaricap, kalinlik, guc, renk):
    bpy.ops.mesh.primitive_torus_add(major_radius=yaricap,
                                     minor_radius=kalinlik,
                                     major_segments=96, minor_segments=12)
    return emissive(bpy.context.active_object, guc, renk)


if tur == "halka":
    # duz, temiz enerji cemberi
    o = cember(1.0, 0.055, 9.0, (1.0, 0.96, 0.90))

elif tur == "sok":
    # sok dalgasi: ince cember + hafif konik etek (yayilma hissi)
    # ⛔ Dolu koni halkayi ORTTU (beyaz disk cikti). Sok dalgasi ICI BOS
    #    kalmali: ana cember + disinda soluk ikinci cember = yayilma.
    cember(0.86, 0.030, 18.0, (1.0, 1.0, 1.0))
    cember(1.02, 0.012, 4.0, (0.88, 0.94, 1.0))

elif tur == "emp":
    # EMP: cember + kenarindan disa firlayan zikzak arklar
    cember(0.92, 0.038, 12.0, (0.42, 0.72, 1.0))
    for i in range(16):
        a0 = random.uniform(0, math.tau)
        bm = bmesh.new()
        onceki = None
        r = 0.92
        for s in range(5):
            r += random.uniform(0.05, 0.13)
            a = a0 + random.uniform(-0.10, 0.10)
            v = bm.verts.new((math.cos(a) * r, math.sin(a) * r,
                              random.uniform(-0.03, 0.03)))
            if onceki:
                bm.edges.new((onceki, v))
            onceki = v
        me = bpy.data.meshes.new("ark")
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new("ark", me)
        sahne.collection.objects.link(ob)
        # ⛔ Cizgi mesh'i render edilmez; kalinlik SART -- ama `bevel_depth`
        #    CURVE alanidir, Mesh'te YOK (AttributeError verdi). Mesh'te
        #    kalinlik SKIN modifier'indan gelir.
        ob.modifiers.new("skin", "SKIN")
        for v in me.skin_vertices[0].data:
            v.radius = (0.016, 0.016)
        emissive(ob, 16.0, (0.62, 0.84, 1.0))

elif tur == "yildiz":
    # merkezden disa sivri isinlar + parlak cekirdek
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, segments=24, ring_count=12)
    emissive(bpy.context.active_object, 40.0, (1.0, 1.0, 1.0))
    for i in range(11):
        a0 = i * math.tau / 11 + random.uniform(-0.12, 0.12)
        boy = random.uniform(0.55, 1.05)
        bpy.ops.mesh.primitive_cone_add(radius1=0.035, radius2=0.0, depth=boy,
                                        vertices=8)
        c = bpy.context.active_object
        # ⛔ Elle Euler VERME. Kamera -Y'den bakiyor, gorunen duzlem XZ;
        #    `(pi/2, 0, -a)` konileri kameraya DIK cevirdi ve yildiz tek
        #    cizgi gibi render oldu. Yonu vektorden turet.
        yon = Vector((math.cos(a0), 0.0, math.sin(a0)))
        c.rotation_euler = yon.to_track_quat('Z', 'Y').to_euler()
        c.location = yon * (boy / 2)
        emissive(c, 12.0, (0.90, 0.95, 1.0))

elif tur == "kure":
    # yumusak enerji kuresi (sifa / toplanma / cerenkov)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.62, segments=48, ring_count=24)
    o = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    emissive(o, 7.0, (1.0, 1.0, 1.0))

elif tur == "ark":
    # tek zikzak elektrik kolu
    bm = bmesh.new()
    onceki = None
    y = -1.0
    for s in range(11):
        v = bm.verts.new((random.uniform(-0.22, 0.22), 0, y))
        if onceki:
            bm.edges.new((onceki, v))
        onceki = v
        y += 2.0 / 10
    me = bpy.data.meshes.new("a")
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("a", me)
    sahne.collection.objects.link(ob)
    ob.modifiers.new("skin", "SKIN")
    for v in me.skin_vertices[0].data:
        v.radius = (0.022, 0.022)
    emissive(ob, 22.0, (0.72, 0.88, 1.0))

else:
    # ---- SIVI: metaball, yuzey gerilimi icin ----
    mb = bpy.data.metaballs.new("mb")
    # ⛔ Metaball'lar BIRLESMEZSE ayri toplar gorunur ve sivi
    #    okunmaz (goruldu: sicrama/tac/kan dagilmis kirinti).
    #    Birlesme `threshold` ile yaricap oraninin isi; esigi
    #    dusur, yaricaplari buyut.
    mb.resolution = 0.018
    mb.threshold = 0.28
    ob = bpy.data.objects.new("mb", mb)
    sahne.collection.objects.link(ob)

    def top(x, y, z, r):
        e = mb.elements.new()
        e.co = (x, y, z)
        e.radius = r

    if tur == "damla":
        # gozyasi: buyuk alt kure + kuculerek yukselen kuyruk
        top(0, 0, -0.34, 0.74)
        for i in range(6):
            f = i / 5.0
            top(0, 0, -0.34 + 0.86 * f, 0.60 * (1.0 - f) ** 1.5 + 0.05)
    elif tur == "tac":
        # su tac sicramasi: halka uzerinde yukselen sivri sutunlar
        for i in range(11):
            a = i * math.tau / 11
            yb = 0.62 + random.uniform(-0.05, 0.05)
            for j in range(4):
                f = j / 3.0
                top(math.cos(a) * (yb + 0.10 * f), math.sin(a) * (yb + 0.10 * f),
                    -0.25 + 0.72 * f, 0.26 * (1.0 - 0.45 * f))
            top(math.cos(a) * (yb + 0.16), math.sin(a) * (yb + 0.16), 0.55,
                0.13)
        for i in range(18):
            a = random.uniform(0, math.tau)
            top(math.cos(a) * random.uniform(0.5, 0.95),
                math.sin(a) * random.uniform(0.5, 0.95),
                random.uniform(-0.30, -0.10), 0.22)
    elif tur == "sicrama":
        top(0, 0, 0, 0.58)
        for i in range(9):
            a = random.uniform(0, math.tau)
            d = random.uniform(0.35, 0.80)
            top(math.cos(a) * d, math.sin(a) * d,
                random.uniform(-0.18, 0.30), random.uniform(0.20, 0.34))
    else:  # kan
        top(0, 0, 0, 0.48)
        for i in range(13):
            a = random.uniform(0, math.tau)
            d = random.uniform(0.30, 0.92)
            top(math.cos(a) * d, math.sin(a) * d,
                random.uniform(-0.14, 0.14), random.uniform(0.16, 0.28))

    mat = bpy.data.materials.new("s")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    if tur == "kan":
        b.inputs["Base Color"].default_value = (0.34, 0.02, 0.015, 1)
        b.inputs["Roughness"].default_value = 0.16
    else:
        b.inputs["Base Color"].default_value = (0.72, 0.86, 0.94, 1)
        b.inputs["Roughness"].default_value = 0.08
    ob.data.materials.append(mat)
    # ⚠ Metaball varsayilan olarak FASETLI cizilir; sivi yuzeyi
    #   duzgun olmali (kil gorunumunu bu veriyor).
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass

    # sivi KATI gibi isiklandirilir -- islak parlama kenardan gelir
    def isik(konum, guc, boy, renk=(1, 1, 1)):
        d = bpy.data.lights.new("l", type="AREA")
        d.energy = guc; d.size = boy; d.color = renk
        o2 = bpy.data.objects.new("l", d); sahne.collection.objects.link(o2)
        o2.location = konum
        o2.rotation_euler = (Vector((0, 0, 0)) - Vector(konum)) \
            .to_track_quat('-Z', 'Y').to_euler()
    isik((2.4, -2.0, 2.6), 300, 2.0, (1.0, 0.97, 0.93))
    isik((-2.6, -1.4, 0.5), 110, 3.4, (0.66, 0.78, 1.0))
    isik((0.2, 3.0, 1.2), 220, 1.6)

# --- kamera: ortografik, sprite icin sart ---
kd = bpy.data.cameras.new("k"); kd.type = "ORTHO"
kd.ortho_scale = 2.9 if ENERJI else 2.2
kam = bpy.data.objects.new("k", kd); sahne.collection.objects.link(kam)
if tur in ("halka", "sok", "emp", "tac"):
    # halka/tac USTTEN bakilir
    kam.location = (0, 0, 6); kam.rotation_euler = (0, 0, 0)
else:
    kam.location = (0, -6, 0); kam.rotation_euler = (math.radians(90), 0, 0)
sahne.camera = kam

_motorlar = {e.identifier for e in
             bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
for _m in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
    if _m in _motorlar:
        sahne.render.engine = _m
        break
try:
    sahne.eevee.taa_render_samples = 64
    # ⛔ BLOOM enerji efektinin YARISIDIR. Blender 4.2+ bunu compositor'a
    #    tasidi (`use_bloom` kalkti); Glare dugumu ile kurulur.
except Exception:
    pass

sahne.render.film_transparent = True
sahne.render.resolution_x = coz
sahne.render.resolution_y = coz
sahne.render.image_settings.file_format = "PNG"
sahne.render.image_settings.color_mode = "RGBA"

if ENERJI:
    # ⛔ Blender 5.x'te `Scene.node_tree` YOK: compositor bir NODE GROUP'a
    #    tasindi (`scene.compositing_node_group`). Eski surumde ise
    #    `use_nodes = True` + `scene.node_tree`. Ikisini de destekle.
    nt = None
    if hasattr(sahne, "compositing_node_group"):
        ng = bpy.data.node_groups.new("kompozit", "CompositorNodeTree")
        sahne.compositing_node_group = ng
        nt = ng
    else:
        sahne.use_nodes = True
        nt = sahne.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers")
    gl = nt.nodes.new("CompositorNodeGlare")
    # ⛔ ALAN ADINI VARSAYMA. Blender 5.x Glare dugumunde `glare_type` ve
    #    `quality` artik RNA property DEGIL -- `properties["glare_type"]`
    #    dogrudan KeyError atiyor. Once varligini sor, sonra yaz.
    def _ayar(dugum, ad, deger):
        try:
            if dugum.bl_rna.properties.get(ad) is None:
                return False
            setattr(dugum, ad, deger)
            return True
        except Exception:
            return False

    for _ad in ("glare_type", "type"):
        if _ayar(gl, _ad, "BLOOM") or _ayar(gl, _ad, "FOG_GLOW"):
            break
    _ayar(gl, "quality", "HIGH")
    _ayar(gl, "threshold", 0.55)
    _ayar(gl, "size", 8)
    nt.links.new(rl.outputs["Image"], gl.inputs["Image"])
    # 5.x node group: cikis Group Output; eski surum: Composite dugumu
    if hasattr(sahne, "compositing_node_group"):
        go = nt.nodes.new("NodeGroupOutput")
        if not nt.interface.items_tree:
            nt.interface.new_socket("Image", in_out="OUTPUT",
                                    socket_type="NodeSocketColor")
        nt.links.new(gl.outputs["Image"], go.inputs[0])
    else:
        cm = nt.nodes.new("CompositorNodeComposite")
        nt.links.new(gl.outputs["Image"], cm.inputs["Image"])

sahne.render.filepath = cikti
bpy.ops.render.render(write_still=True)
print("RENDER_TAMAM", cikti)
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tur", required=True, choices=TURLER)
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
             a.tur, a.cikti, str(a.coz), str(a.tohum)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=900)
        if "RENDER_TAMAM" not in (r.stdout or ""):
            print(((r.stdout or "") + (r.stderr or "")).strip()[-1600:])
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
