#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_blender_energy.py — renders ENERGY and LIQUID sprites in Blender.

`ptfx_blender_render.py` is for SOLID debris (concrete/glass/wood). This
script is its sibling and covers two separate families:

  ENERGY (emissive + bloom):  ring · shock · emp · star · sphere · arc
  LIQUID (metaball):          drop · splash · crown · blood

⛔ WHY SEPARATE: what reads in an energy effect is NOT GEOMETRY BUT LIGHT --
   an emissive surface + bloom. The three-point light of a solid piece is wrong
   here; on the contrary there must be NO external light in the scene, the
   object itself must emit light. A liquid needs surface TENSION: not separate
   spheres but metaballs that merge and melt together -- that is how a real
   drop reads.

Usage:
  python ptfx_blender_energy.py --kind ring --out out.png
  python ptfx_blender_energy.py --kind splash --out out.png --seed 3
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile

BLENDER = r"C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe"

KINDS = ["ring", "shock", "emp", "star", "sphere", "arc",
         "drop", "splash", "crown", "blood"]
# old Turkish kind names still accepted on the command line
KIND_ALIASES = {"halka": "ring", "sok": "shock", "emp": "emp", "yildiz": "star",
                "kure": "sphere", "ark": "arc", "damla": "drop", "sicrama": "splash",
                "tac": "crown", "kan": "blood"}

SCENE = r'''
import bpy, bmesh, math, random, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
kind, out, resolution, seed = argv[0], argv[1], int(argv[2]), int(argv[3])
random.seed(seed)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
ENERGY = kind in ("ring", "shock", "emp", "star", "sphere", "arc")


def emissive(ob, strength, color=(1, 1, 1)):
    """⛔ An energy effect has NO external light; the object emits its own light."""
    m = bpy.data.materials.new("e")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (color[0], color[1], color[2], 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"],
                 nt.nodes["Material Output"].inputs["Surface"])
    ob.data.materials.append(m)
    return ob


def circle(radius, thickness, strength, color):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius,
                                     minor_radius=thickness,
                                     major_segments=96, minor_segments=12)
    return emissive(bpy.context.active_object, strength, color)


if kind == "ring":
    # flat, clean energy circle
    o = circle(1.0, 0.055, 9.0, (1.0, 0.96, 0.90))

elif kind == "shock":
    # shock wave: thin circle + faint conical skirt (sense of spreading)
    # ⛔ A filled cone HID the ring (came out as a white disc). The shock wave
    #    must stay HOLLOW: main circle + faint second circle outside = spreading.
    circle(0.86, 0.030, 18.0, (1.0, 1.0, 1.0))
    circle(1.02, 0.012, 4.0, (0.88, 0.94, 1.0))

elif kind == "emp":
    # EMP: circle + zigzag arcs shooting out from its edge
    circle(0.92, 0.038, 12.0, (0.42, 0.72, 1.0))
    for i in range(16):
        a0 = random.uniform(0, math.tau)
        bm = bmesh.new()
        prev = None
        r = 0.92
        for s in range(5):
            r += random.uniform(0.05, 0.13)
            a = a0 + random.uniform(-0.10, 0.10)
            v = bm.verts.new((math.cos(a) * r, math.sin(a) * r,
                              random.uniform(-0.03, 0.03)))
            if prev:
                bm.edges.new((prev, v))
            prev = v
        me = bpy.data.meshes.new("arc")
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new("arc", me)
        scene.collection.objects.link(ob)
        # ⛔ A line mesh does not render; thickness is REQUIRED -- but `bevel_depth`
        #    is a CURVE field, Mesh does NOT have it (it raised AttributeError).
        #    On a mesh the thickness comes from the SKIN modifier.
        ob.modifiers.new("skin", "SKIN")
        for v in me.skin_vertices[0].data:
            v.radius = (0.016, 0.016)
        emissive(ob, 16.0, (0.62, 0.84, 1.0))

elif kind == "star":
    # sharp rays outward from the centre + bright core
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, segments=24, ring_count=12)
    emissive(bpy.context.active_object, 40.0, (1.0, 1.0, 1.0))
    for i in range(11):
        a0 = i * math.tau / 11 + random.uniform(-0.12, 0.12)
        length = random.uniform(0.55, 1.05)
        bpy.ops.mesh.primitive_cone_add(radius1=0.035, radius2=0.0, depth=length,
                                        vertices=8)
        c = bpy.context.active_object
        # ⛔ Do NOT set Euler by hand. The camera looks from -Y, the visible plane
        #    is XZ; `(pi/2, 0, -a)` turned the cones PERPENDICULAR to the camera
        #    and the star rendered as a single line. Derive the direction from a vector.
        direction = Vector((math.cos(a0), 0.0, math.sin(a0)))
        c.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
        c.location = direction * (length / 2)
        emissive(c, 12.0, (0.90, 0.95, 1.0))

elif kind == "sphere":
    # soft energy sphere (healing / gathering / cherenkov)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.62, segments=48, ring_count=24)
    o = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    emissive(o, 7.0, (1.0, 1.0, 1.0))

elif kind == "arc":
    # single zigzag electric branch
    bm = bmesh.new()
    prev = None
    y = -1.0
    for s in range(11):
        v = bm.verts.new((random.uniform(-0.22, 0.22), 0, y))
        if prev:
            bm.edges.new((prev, v))
        prev = v
        y += 2.0 / 10
    me = bpy.data.meshes.new("a")
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("a", me)
    scene.collection.objects.link(ob)
    ob.modifiers.new("skin", "SKIN")
    for v in me.skin_vertices[0].data:
        v.radius = (0.022, 0.022)
    emissive(ob, 22.0, (0.72, 0.88, 1.0))

else:
    # ---- LIQUID: metaball, for surface tension ----
    mb = bpy.data.metaballs.new("mb")
    # ⛔ If the metaballs do NOT MERGE they show as separate balls and the
    #    liquid does not read (seen: splash/crown/blood as scattered crumbs).
    #    Merging depends on `threshold` versus the radius ratio; lower the
    #    threshold, enlarge the radii.
    mb.resolution = 0.018
    mb.threshold = 0.28
    ob = bpy.data.objects.new("mb", mb)
    scene.collection.objects.link(ob)

    def ball(x, y, z, r):
        e = mb.elements.new()
        e.co = (x, y, z)
        e.radius = r

    if kind == "drop":
        # teardrop: big bottom sphere + tail rising and shrinking
        ball(0, 0, -0.34, 0.74)
        for i in range(6):
            f = i / 5.0
            ball(0, 0, -0.34 + 0.86 * f, 0.60 * (1.0 - f) ** 1.5 + 0.05)
    elif kind == "crown":
        # water crown splash: sharp columns rising on a ring
        for i in range(11):
            a = i * math.tau / 11
            yb = 0.62 + random.uniform(-0.05, 0.05)
            for j in range(4):
                f = j / 3.0
                ball(math.cos(a) * (yb + 0.10 * f), math.sin(a) * (yb + 0.10 * f),
                     -0.25 + 0.72 * f, 0.26 * (1.0 - 0.45 * f))
            ball(math.cos(a) * (yb + 0.16), math.sin(a) * (yb + 0.16), 0.55,
                 0.13)
        for i in range(18):
            a = random.uniform(0, math.tau)
            ball(math.cos(a) * random.uniform(0.5, 0.95),
                 math.sin(a) * random.uniform(0.5, 0.95),
                 random.uniform(-0.30, -0.10), 0.22)
    elif kind == "splash":
        ball(0, 0, 0, 0.58)
        for i in range(9):
            a = random.uniform(0, math.tau)
            d = random.uniform(0.35, 0.80)
            ball(math.cos(a) * d, math.sin(a) * d,
                 random.uniform(-0.18, 0.30), random.uniform(0.20, 0.34))
    else:  # blood
        ball(0, 0, 0, 0.48)
        for i in range(13):
            a = random.uniform(0, math.tau)
            d = random.uniform(0.30, 0.92)
            ball(math.cos(a) * d, math.sin(a) * d,
                 random.uniform(-0.14, 0.14), random.uniform(0.16, 0.28))

    mat = bpy.data.materials.new("s")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    if kind == "blood":
        b.inputs["Base Color"].default_value = (0.34, 0.02, 0.015, 1)
        b.inputs["Roughness"].default_value = 0.16
    else:
        b.inputs["Base Color"].default_value = (0.72, 0.86, 0.94, 1)
        b.inputs["Roughness"].default_value = 0.08
    ob.data.materials.append(mat)
    # ⚠ A metaball is drawn FACETED by default; a liquid surface must be
    #   smooth (that is what gives the clay look).
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass

    # a liquid is lit like a SOLID -- the wet highlight comes from the rim
    def light(location, power, size, color=(1, 1, 1)):
        d = bpy.data.lights.new("l", type="AREA")
        d.energy = power; d.size = size; d.color = color
        o2 = bpy.data.objects.new("l", d); scene.collection.objects.link(o2)
        o2.location = location
        o2.rotation_euler = (Vector((0, 0, 0)) - Vector(location)) \
            .to_track_quat('-Z', 'Y').to_euler()
    light((2.4, -2.0, 2.6), 300, 2.0, (1.0, 0.97, 0.93))
    light((-2.6, -1.4, 0.5), 110, 3.4, (0.66, 0.78, 1.0))
    light((0.2, 3.0, 1.2), 220, 1.6)

# --- camera: orthographic, required for a sprite ---
kd = bpy.data.cameras.new("k"); kd.type = "ORTHO"
kd.ortho_scale = 2.9 if ENERGY else 2.2
cam = bpy.data.objects.new("k", kd); scene.collection.objects.link(cam)
if kind in ("ring", "shock", "emp", "crown"):
    # ring/crown are viewed FROM ABOVE
    cam.location = (0, 0, 6); cam.rotation_euler = (0, 0, 0)
else:
    cam.location = (0, -6, 0); cam.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam

_engines = {e.identifier for e in
            bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
for _e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
    if _e in _engines:
        scene.render.engine = _e
        break
try:
    scene.eevee.taa_render_samples = 64
    # ⛔ BLOOM is HALF of an energy effect. Blender 4.2+ moved it to the
    #    compositor (`use_bloom` is gone); it is built with a Glare node.
except Exception:
    pass

scene.render.film_transparent = True
scene.render.resolution_x = resolution
scene.render.resolution_y = resolution
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"

if ENERGY:
    # ⛔ Blender 5.x has NO `Scene.node_tree`: the compositor moved to a NODE GROUP
    #    (`scene.compositing_node_group`). Older versions use
    #    `use_nodes = True` + `scene.node_tree`. Support both.
    nt = None
    if hasattr(scene, "compositing_node_group"):
        ng = bpy.data.node_groups.new("composite", "CompositorNodeTree")
        scene.compositing_node_group = ng
        nt = ng
    else:
        scene.use_nodes = True
        nt = scene.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers")
    gl = nt.nodes.new("CompositorNodeGlare")
    # ⛔ DO NOT ASSUME THE FIELD NAME. In Blender 5.x the Glare node's `glare_type`
    #    and `quality` are no longer RNA properties -- `properties["glare_type"]`
    #    raises KeyError directly. Ask whether it exists first, then write.
    def _set(node, name, value):
        try:
            if node.bl_rna.properties.get(name) is None:
                return False
            setattr(node, name, value)
            return True
        except Exception:
            return False

    for _name in ("glare_type", "type"):
        if _set(gl, _name, "BLOOM") or _set(gl, _name, "FOG_GLOW"):
            break
    _set(gl, "quality", "HIGH")
    _set(gl, "threshold", 0.55)
    _set(gl, "size", 8)
    nt.links.new(rl.outputs["Image"], gl.inputs["Image"])
    # 5.x node group: output is Group Output; older versions: Composite node
    if hasattr(scene, "compositing_node_group"):
        go = nt.nodes.new("NodeGroupOutput")
        if not nt.interface.items_tree:
            nt.interface.new_socket("Image", in_out="OUTPUT",
                                    socket_type="NodeSocketColor")
        nt.links.new(gl.outputs["Image"], go.inputs[0])
    else:
        cm = nt.nodes.new("CompositorNodeComposite")
        nt.links.new(gl.outputs["Image"], cm.inputs["Image"])

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
            errors="replace", timeout=900)
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
