#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_blender_duman.py — HACIMSEL duman/ates/sis sprite'i render eder.

Uc kardes betigin ucuncusu:
  ptfx_blender_render.py   -> KATI parca   (beton/cam/tahta/kagit)
  ptfx_blender_enerji.py   -> ENERJI+SIVI  (halka/yildiz/kure/damla/tac)
  ptfx_blender_duman.py    -> HACIM        (duman/ates/sis/buhar)

⛔ NEDEN AYRI: duman ne kati bir yuzeydir ne de emissive bir cizgi.
   Hacimdir -- isik ICINDEN gecer, kendi golgesini kendi uzerine dusurur.
   Numpy ile ciziler duman "duz gri leke" olarak kaliyordu; derinligi
   veren sey tam olarak bu ic golgelemedir.

⛔ MANTAFLOW BAKE ETMIYORUZ. Arka planda duman simulasyonu bake etmek
   dakikalar suruyor ve tek kare sprite icin gereksiz. Prosedurel
   `Noise -> Principled Volume` ayni gorsel sonucu aninda veriyor;
   simulasyon ancak kare kare AKIS gerekseydi sart olurdu.

Turler: duman · sis · buhar · ates

Kullanim:
  python ptfx_blender_duman.py --tur duman --cikti out.png
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile

BLENDER = r"C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe"
TURLER = ["duman", "sis", "buhar", "ates"]

SAHNE = r'''
import bpy, math, random, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
tur, cikti, coz, tohum = argv[0], argv[1], int(argv[2]), int(argv[3])
random.seed(tohum)

bpy.ops.wm.read_factory_settings(use_empty=True)
sahne = bpy.context.scene

# tur -> (yogunluk, olcek, detay, biçim(z), emission, renk)
T = {
    "duman": dict(yog=9.0,  olcek=2.6, detay=7.0, zbicim=1.05, em=0.0,
                  renk=(0.52, 0.52, 0.54), esik=0.42),
    "sis":   dict(yog=3.4,  olcek=1.5, detay=4.5, zbicim=0.42, em=0.0,
                  renk=(0.72, 0.74, 0.78), esik=0.34),
    "buhar": dict(yog=6.0,  olcek=2.2, detay=6.0, zbicim=1.45, em=0.0,
                  renk=(0.88, 0.90, 0.93), esik=0.40),
    "ates":  dict(yog=7.0,  olcek=2.9, detay=8.0, zbicim=1.55, em=9.0,
                  renk=(1.00, 0.42, 0.08), esik=0.46),
}[tur]

# --- hacim kutusu ---
bpy.ops.mesh.primitive_cube_add(size=2.0)
kutu = bpy.context.active_object
kutu.scale = (1.0, 1.0, T["zbicim"])

mat = bpy.data.materials.new("v")
mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes):
    if n.type != "OUTPUT_MATERIAL":
        nt.nodes.remove(n)
cikis = nt.nodes["Material Output"]

koord = nt.nodes.new("ShaderNodeTexCoord")
# ⛔ Object koordinati kullan: Generated kutunun kendisine gore 0..1 verir
#    ve olcek degisince desen kayar.
esne = nt.nodes.new("ShaderNodeMapping")
esne.inputs["Location"].default_value = (random.uniform(-9, 9),
                                         random.uniform(-9, 9),
                                         random.uniform(-9, 9))
nt.links.new(koord.outputs["Object"], esne.inputs["Vector"])

gur = nt.nodes.new("ShaderNodeTexNoise")
gur.inputs["Scale"].default_value = T["olcek"]
gur.inputs["Detail"].default_value = T["detay"]
if "Roughness" in gur.inputs:
    gur.inputs["Roughness"].default_value = 0.62
nt.links.new(esne.outputs["Vector"], gur.inputs["Vector"])

# kure maskesi: kutunun koselerini kes, puf sekli olsun
gnd = nt.nodes.new("ShaderNodeNewGeometry")
uzak = nt.nodes.new("ShaderNodeVectorMath")
uzak.operation = "LENGTH"
nt.links.new(koord.outputs["Object"], uzak.inputs[0])
maske = nt.nodes.new("ShaderNodeMapRange")
maske.inputs["From Min"].default_value = 0.30
maske.inputs["From Max"].default_value = 0.98
maske.inputs["To Min"].default_value = 1.0
maske.inputs["To Max"].default_value = 0.0
maske.clamp = True
nt.links.new(uzak.outputs["Value"], maske.inputs["Value"])

# gurultu * maske -> yogunluk; esikle parcala (duman PARCALIDIR)
carp = nt.nodes.new("ShaderNodeMath"); carp.operation = "MULTIPLY"
nt.links.new(gur.outputs["Fac"], carp.inputs[0])
nt.links.new(maske.outputs["Result"], carp.inputs[1])

esik = nt.nodes.new("ShaderNodeMapRange")
esik.inputs["From Min"].default_value = T["esik"]
esik.inputs["From Max"].default_value = 0.92
esik.inputs["To Min"].default_value = 0.0
esik.inputs["To Max"].default_value = T["yog"]
esik.clamp = True
nt.links.new(carp.outputs["Value"], esik.inputs["Value"])

vol = nt.nodes.new("ShaderNodeVolumePrincipled")
vol.inputs["Color"].default_value = (T["renk"][0], T["renk"][1], T["renk"][2], 1)
nt.links.new(esik.outputs["Result"], vol.inputs["Density"])

if T["em"] > 0:
    # ates: yogunluga bagli EMISSION -- sicak cekirdek, sogumus uc
    em = nt.nodes.new("ShaderNodeMapRange")
    em.inputs["From Min"].default_value = T["esik"]
    em.inputs["From Max"].default_value = 0.95
    em.inputs["To Min"].default_value = 0.0
    em.inputs["To Max"].default_value = T["em"]
    em.clamp = True
    nt.links.new(carp.outputs["Value"], em.inputs["Value"])
    if "Emission Strength" in vol.inputs:
        nt.links.new(em.outputs["Result"], vol.inputs["Emission Strength"])
    if "Emission Color" in vol.inputs:
        vol.inputs["Emission Color"].default_value = (1.0, 0.46, 0.10, 1)

nt.links.new(vol.outputs["Volume"], cikis.inputs["Volume"])
kutu.data.materials.append(mat)

# --- isik: hacmin DERINLIGINI bu yaratir ---
def isik(konum, guc, boy, renk=(1, 1, 1)):
    d = bpy.data.lights.new("l", type="AREA")
    d.energy = guc; d.size = boy; d.color = renk
    o = bpy.data.objects.new("l", d)
    sahne.collection.objects.link(o)
    o.location = konum
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(konum)) \
        .to_track_quat('-Z', 'Y').to_euler()

if tur != "ates":
    # ⛔ Duman TEK yonden aydinlatilir; iki yandan esit isik hacmi
    #    duzlestirip yine "gri leke" yapar. Golgeli taraf SART.
    isik((3.2, -2.2, 2.6), 900, 3.0, (1.0, 0.97, 0.92))
    isik((-3.0, -1.0, -0.6), 120, 4.0, (0.60, 0.70, 1.0))
else:
    isik((2.0, -2.4, 1.4), 160, 2.0, (1.0, 0.80, 0.55))

# --- kamera ---
kd = bpy.data.cameras.new("k"); kd.type = "ORTHO"
kd.ortho_scale = 2.6
kam = bpy.data.objects.new("k", kd); sahne.collection.objects.link(kam)
kam.location = (0, -6, 0); kam.rotation_euler = (math.radians(90), 0, 0)
sahne.camera = kam

# ⛔ HACIM ICIN CYCLES. EEVEE hacmi kaba voxel'lerle ve gercek ic
#    golgeleme olmadan cizer; dumanin derinligi tam da o golgeden gelir.
sahne.render.engine = "CYCLES"
sahne.cycles.samples = 48
sahne.cycles.use_denoising = True
try:
    sahne.cycles.volume_step_rate = 0.4
    sahne.cycles.volume_max_steps = 256
except Exception:
    pass

sahne.render.film_transparent = True
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
            errors="replace", timeout=1800)
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
