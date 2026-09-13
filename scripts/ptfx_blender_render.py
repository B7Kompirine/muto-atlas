#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_blender_render.py — RENDERS a particle sprite in BLENDER.

⛔ WHY: a silhouette computed with numpy does not look professional. Measured
   and researched -- vanilla's `ptfx_multi_sheet_00N_debris` atlases come
   from photos/3D renders, not hand drawing; VFXDoc and industry sources say
   the same thing: model/simulate it, RENDER it, bake it into a texture.

This script runs Blender IN THE BACKGROUND (-b), builds a single solid
piece, lights it with three-point lighting, and renders it ORTHOGRAPHIC on
a transparent background. The output can be used directly as a particle
sprite.

Materials: concrete · glass · wood · metal · paper · ice

Usage:
  python ptfx_blender_render.py --material concrete --out out.png
  python ptfx_blender_render.py --material glass --resolution 512 --seed 7
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

BLENDER = r"C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe"
MATERIALS = ["concrete", "glass", "wood", "metal", "paper", "ice"]
# old Turkish material names still accepted on the command line
MATERIAL_ALIASES = {"beton": "concrete", "cam": "glass", "tahta": "wood",
                    "metal": "metal", "kagit": "paper", "buz": "ice"}

# Script that runs inside Blender. Reads the arguments after `--`.
SCENE = r'''
import bpy, bmesh, math, random, sys, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
material, out, resolution, seed = argv[0], argv[1], int(argv[2]), int(argv[3])
random.seed(seed)

# --- clean scene ---
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# --- material specs: (piece count, roughness, metallic, base colour, shape) ---
SPECS = {
    "concrete": dict(n=1, rough=0.95, metal=0.0, color=(0.46, 0.44, 0.41, 1), shape="block",
                     dims=(1.0, 0.86, 0.80), crack=0.16),
    "glass":    dict(n=1, rough=0.04, metal=0.0, color=(0.62, 0.76, 0.84, 1), shape="sheet",
                     dims=(1.0, 0.90, 0.045), crack=0.0),
    "wood":     dict(n=1, rough=0.80, metal=0.0, color=(0.44, 0.29, 0.15, 1), shape="rod",
                     dims=(1.0, 0.17, 0.13), crack=0.10),
    "metal":    dict(n=1, rough=0.35, metal=0.9, color=(0.55, 0.56, 0.58, 1), shape="sheet",
                     dims=(1.0, 0.60, 0.12), crack=0.20),
    "paper":    dict(n=1, rough=0.88, metal=0.0, color=(0.80, 0.78, 0.72, 1), shape="sheet",
                     dims=(1.0, 0.78, 0.015), crack=0.0),
    "ice":      dict(n=1, rough=0.15, metal=0.0, color=(0.78, 0.88, 0.94, 1), shape="block",
                     dims=(1.0, 0.90, 0.80), crack=0.10),
}
t = SPECS[material]

# --- geometry: irregular convex piece ---
bpy.ops.mesh.primitive_cube_add(size=2.0)
ob = bpy.context.active_object
ob.scale = t["dims"]
bpy.ops.object.transform_apply(scale=True)

me = ob.data
bm = bmesh.new(); bm.from_mesh(me)

# push the corners randomly -> irregular solid
for v in bm.verts:
    v.co.x += random.uniform(-0.34, 0.34)
    v.co.y += random.uniform(-0.34, 0.34)
    v.co.z += random.uniform(-0.30, 0.30)

# subdivide a few times and push again -> richer silhouette
# ⚠ On block materials do NOT wreck the SURFACE: subdivide once, give only a
#   coarse irregularity. Two subdivision rounds pushing every vertex make the
#   surface lumpy and the solid-body feel is lost.
if t["crack"] > 0.01:
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1,
                              use_grid_fill=True)
    k = t["crack"]
    for v in bm.verts:
        v.co += Vector((random.uniform(-k, k), random.uniform(-k, k),
                        random.uniform(-k, k)))
    bmesh.ops.convex_hull(bm, input=bm.verts)

# glass/paper: we want sharp corners -> convex hull
if t["shape"] == "sheet":
    bmesh.ops.convex_hull(bm, input=bm.verts)

bm.to_mesh(me); bm.free()
me.update()

# wood: grain feel along the long axis: slight twist
if material == "wood":
    m = ob.modifiers.new("simple", "SIMPLE_DEFORM")
    m.deform_method = "TWIST"; m.angle = math.radians(random.uniform(-25, 25))

# corner softening (except glass: glass stays sharp)
if material != "glass":
    bev = ob.modifiers.new("bevel", "BEVEL")
    bev.width = 0.02; bev.segments = 2
# ⛔ SHADE_SMOOTH TURNS DEBRIS INTO CRUMPLED PAPER. A solid piece is
#    FACETED: flat shading makes every face read separately, that is how the
#    silhouette and volume come out. (In the first render the concrete looked
#    like a crumpled bag.)
bpy.ops.object.shade_flat()
ob.rotation_euler = (random.uniform(0, math.tau), random.uniform(0, math.tau),
                     random.uniform(0, math.tau))

# --- material ---
mat = bpy.data.materials.new("m"); mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = t["color"]
bsdf.inputs["Roughness"].default_value = t["rough"]
bsdf.inputs["Metallic"].default_value = t["metal"]
if material in ("glass", "ice"):
    # ⛔ Real transmission is useless in game (the sprite bakes to alpha) and
    #    slows the render; RIM HIGHLIGHT is what makes glass read.
    bsdf.inputs["Roughness"].default_value = 0.05
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 1.0
ob.data.materials.append(mat)

# --- three-point light: this is what makes the shape read ---
def light(name, location, power, size, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, type="AREA")
    d.energy = power; d.size = size; d.color = color
    o = bpy.data.objects.new(name, d); scene.collection.objects.link(o)
    o.location = location
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(location)).to_track_quat('-Z', 'Y').to_euler()
    return o

# ⛔ 900 W blew the concrete out to WHITE. Debris must read in mid tones.
light("key",  (2.6, -2.2, 3.0), 260, 2.2, (1.0, 0.95, 0.88))
light("fill", (-3.0, -1.6, 0.6), 90, 4.0, (0.66, 0.76, 1.0))
light("rim",  (0.4, 3.2, 1.4), 150, 1.6, (1.0, 1.0, 1.0))

# --- orthographic camera: required for a sprite (perspective distorts) ---
cam_d = bpy.data.cameras.new("cam"); cam_d.type = "ORTHO"
cam_d.ortho_scale = 3.1
cam = bpy.data.objects.new("cam", cam_d); scene.collection.objects.link(cam)
cam.location = (0, -6, 0); cam.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam

# --- render settings ---
# ⛔ Do not scan engine names with `RenderEngine.__subclasses__()`: in Blender 5.x
#    `HydraRenderEngine` has NO `bl_idname` and raises AttributeError.
#    The right way is to look at the enum's own items.
_engines = {e.identifier for e in
            bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
for _e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
    if _e in _engines:
        scene.render.engine = _e
        break
try:
    scene.eevee.taa_render_samples = 64
except Exception:
    pass
scene.render.film_transparent = True          # TRANSPARENT background -> alpha ready
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
    ap.add_argument("--material", "--malzeme", dest="material", required=True,
                    choices=MATERIALS, type=lambda v: MATERIAL_ALIASES.get(v, v))
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
             a.material, a.out, str(a.resolution), str(a.seed)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=600)
        if "RENDER_DONE" not in (r.stdout or ""):
            output = (r.stdout or "") + (r.stderr or "")
            print(output.strip()[-1500:])
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
