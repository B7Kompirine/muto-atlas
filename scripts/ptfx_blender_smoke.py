#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_blender_smoke.py — renders a VOLUMETRIC smoke/fire/fog sprite.

Third of three sibling scripts:
  ptfx_blender_render.py   -> SOLID debris   (concrete/glass/wood/paper)
  ptfx_blender_energy.py   -> ENERGY+LIQUID  (ring/star/sphere/drop/crown)
  ptfx_blender_smoke.py    -> VOLUME         (smoke/fire/fog/steam)

⛔ WHY SEPARATE: smoke is neither a solid surface nor an emissive line.
   It is a volume -- light passes THROUGH it, it casts its own shadow onto
   itself. Smoke drawn with numpy stayed a "flat grey smudge"; what gives
   depth is exactly this internal shading.

⛔ WE DO NOT BAKE MANTAFLOW. Baking a smoke simulation in the background
   takes minutes and is unnecessary for a single-frame sprite. A procedural
   `Noise -> Principled Volume` gives the same visual result instantly;
   a simulation would only be required if frame-by-frame FLOW were needed.

Kinds: smoke · fog · steam · fire

Usage:
  python ptfx_blender_smoke.py --kind smoke --out out.png
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile

BLENDER = r"C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe"
KINDS = ["smoke", "fog", "steam", "fire"]
# old Turkish kind names still accepted on the command line
KIND_ALIASES = {"duman": "smoke", "sis": "fog", "buhar": "steam", "ates": "fire"}

SCENE = r'''
import bpy, math, random, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
kind, out, resolution, seed = argv[0], argv[1], int(argv[2]), int(argv[3])
random.seed(seed)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# kind -> (density, scale, detail, shape(z), emission, colour)
T = {
    "smoke": dict(density=9.0, scale=2.6, detail=7.0, zscale=1.05, emission=0.0,
                  color=(0.52, 0.52, 0.54), threshold=0.42),
    "fog":   dict(density=3.4, scale=1.5, detail=4.5, zscale=0.42, emission=0.0,
                  color=(0.72, 0.74, 0.78), threshold=0.34),
    "steam": dict(density=6.0, scale=2.2, detail=6.0, zscale=1.45, emission=0.0,
                  color=(0.88, 0.90, 0.93), threshold=0.40),
    "fire":  dict(density=7.0, scale=2.9, detail=8.0, zscale=1.55, emission=9.0,
                  color=(1.00, 0.42, 0.08), threshold=0.46),
}[kind]

# --- volume box ---
bpy.ops.mesh.primitive_cube_add(size=2.0)
box = bpy.context.active_object
box.scale = (1.0, 1.0, T["zscale"])

mat = bpy.data.materials.new("v")
mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes):
    if n.type != "OUTPUT_MATERIAL":
        nt.nodes.remove(n)
output = nt.nodes["Material Output"]

coords = nt.nodes.new("ShaderNodeTexCoord")
# ⛔ Use Object coordinates: Generated gives 0..1 relative to the box itself
#    and the pattern shifts when the scale changes.
mapping = nt.nodes.new("ShaderNodeMapping")
mapping.inputs["Location"].default_value = (random.uniform(-9, 9),
                                            random.uniform(-9, 9),
                                            random.uniform(-9, 9))
nt.links.new(coords.outputs["Object"], mapping.inputs["Vector"])

noise = nt.nodes.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = T["scale"]
noise.inputs["Detail"].default_value = T["detail"]
if "Roughness" in noise.inputs:
    noise.inputs["Roughness"].default_value = 0.62
nt.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])

# sphere mask: cut the box corners so it becomes a puff
geom = nt.nodes.new("ShaderNodeNewGeometry")
dist = nt.nodes.new("ShaderNodeVectorMath")
dist.operation = "LENGTH"
nt.links.new(coords.outputs["Object"], dist.inputs[0])
mask = nt.nodes.new("ShaderNodeMapRange")
mask.inputs["From Min"].default_value = 0.30
mask.inputs["From Max"].default_value = 0.98
mask.inputs["To Min"].default_value = 1.0
mask.inputs["To Max"].default_value = 0.0
mask.clamp = True
nt.links.new(dist.outputs["Value"], mask.inputs["Value"])

# noise * mask -> density; break it up with a threshold (smoke is BROKEN UP)
mult = nt.nodes.new("ShaderNodeMath"); mult.operation = "MULTIPLY"
nt.links.new(noise.outputs["Fac"], mult.inputs[0])
nt.links.new(mask.outputs["Result"], mult.inputs[1])

thresh = nt.nodes.new("ShaderNodeMapRange")
thresh.inputs["From Min"].default_value = T["threshold"]
thresh.inputs["From Max"].default_value = 0.92
thresh.inputs["To Min"].default_value = 0.0
thresh.inputs["To Max"].default_value = T["density"]
thresh.clamp = True
nt.links.new(mult.outputs["Value"], thresh.inputs["Value"])

vol = nt.nodes.new("ShaderNodeVolumePrincipled")
vol.inputs["Color"].default_value = (T["color"][0], T["color"][1], T["color"][2], 1)
nt.links.new(thresh.outputs["Result"], vol.inputs["Density"])

if T["emission"] > 0:
    # fire: density-driven EMISSION -- hot core, cooled tips
    em = nt.nodes.new("ShaderNodeMapRange")
    em.inputs["From Min"].default_value = T["threshold"]
    em.inputs["From Max"].default_value = 0.95
    em.inputs["To Min"].default_value = 0.0
    em.inputs["To Max"].default_value = T["emission"]
    em.clamp = True
    nt.links.new(mult.outputs["Value"], em.inputs["Value"])
    if "Emission Strength" in vol.inputs:
        nt.links.new(em.outputs["Result"], vol.inputs["Emission Strength"])
    if "Emission Color" in vol.inputs:
        vol.inputs["Emission Color"].default_value = (1.0, 0.46, 0.10, 1)

nt.links.new(vol.outputs["Volume"], output.inputs["Volume"])
box.data.materials.append(mat)

# --- light: this is what creates the DEPTH of the volume ---
def light(location, power, size, color=(1, 1, 1)):
    d = bpy.data.lights.new("l", type="AREA")
    d.energy = power; d.size = size; d.color = color
    o = bpy.data.objects.new("l", d)
    scene.collection.objects.link(o)
    o.location = location
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(location)) \
        .to_track_quat('-Z', 'Y').to_euler()

if kind != "fire":
    # ⛔ Smoke is lit from ONE side; equal light from two sides flattens the
    #    volume and makes a "grey smudge" again. A shadowed side is REQUIRED.
    light((3.2, -2.2, 2.6), 900, 3.0, (1.0, 0.97, 0.92))
    light((-3.0, -1.0, -0.6), 120, 4.0, (0.60, 0.70, 1.0))
else:
    light((2.0, -2.4, 1.4), 160, 2.0, (1.0, 0.80, 0.55))

# --- camera ---
kd = bpy.data.cameras.new("k"); kd.type = "ORTHO"
kd.ortho_scale = 2.6
cam = bpy.data.objects.new("k", kd); scene.collection.objects.link(cam)
cam.location = (0, -6, 0); cam.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam

# ⛔ CYCLES FOR VOLUMES. EEVEE draws a volume with coarse voxels and no real
#    internal shading; the depth of smoke comes exactly from that shadow.
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
try:
    scene.cycles.volume_step_rate = 0.4
    scene.cycles.volume_max_steps = 256
except Exception:
    pass

scene.render.film_transparent = True
scene.render.resolution_x = resolution
scene.render.resolution_y = resolution
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("RENDER_DONE", out)
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", "--tur", dest="kind", required=True, choices=KINDS,
                    type=lambda v: KIND_ALIASES.get(v, v))
    ap.add_argument("--out", "--cikti", dest="out", required=True)
    ap.add_argument("--resolution", "--coz", dest="resolution", type=int, default=512)
    ap.add_argument("--seed", "--tohum", dest="seed", type=int, default=0)
    a = ap.parse_args()

    if not os.path.exists(BLENDER):
        raise SystemExit("blender.exe not found: %s" % BLENDER)

    fd, script = tempfile.mkstemp(suffix=".py")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(SCENE)
    try:
        r = subprocess.run(
            [BLENDER, "-b", "--factory-startup", "-noaudio", "-P", script, "--",
             a.kind, a.out, str(a.resolution), str(a.seed)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=1800)
        if "RENDER_DONE" not in (r.stdout or ""):
            print(((r.stdout or "") + (r.stderr or "")).strip()[-1600:])
            return 1
        print("render: %s (%d bytes)" % (a.out, os.path.getsize(a.out)))
        return 0
    finally:
        try:
            os.remove(script)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
