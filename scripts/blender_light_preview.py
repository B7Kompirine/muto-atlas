"""Engine-accurate light preview inside Blender's viewport.

The per-light math is ported from the engine's own shader source (lighting_common.fxh
CalculateLightingForward + distanceFalloff/angularFalloff, common.fxh
__powapprox, postfx.fx fullFilmicTonemap). Blender's own lights CANNOT express
it: the engine's falloff is a rational approximation over SQUARED distance clamped at
the light's radius, and its cone is linear in the cosine. So this draws its own
pass with the game's formulas, reading Sollumz light objects directly.

    import blender_light_preview as rp
    rp.enable()
    rp.load_timecycle("w_clear", hour=20.5)            # real GTA ambient + sun
    rp.modifiers("v_")                                 # 1085 interior modifiers
    rp.load_timecycle("w_clear", 2, modifier="v_cashdepot", strength=1.0)
    rp.cfg(exposure=1.3, sun_shadow=True)              # cfg(), set() is a builtin
    rp.refresh()                                       # after editing the scene
    rp.report()
    rp.disable()

Three things the game does that this now does too:
  * natural vs artificial ambient is gated by GTA's baked vertex colour 0
    (.r and .g), read from Sollumz's "Color 1" attribute
  * the sun casts shadows through a distance map from a virtual sun position
  * interior timecycle modifiers blend over the weather cycle
"""

import bpy
import gpu
import numpy as np
from gpu_extras.batch import batch_for_shader
from mathutils import Vector, Matrix

import light_preview_shaders as shaders

MAX_LIGHTS = shaders.MAX_LIGHTS

SOLLUM_TYPE = {
    "sollumz_light_point": 1.0,
    "sollumz_light_spot": 2.0,
    "sollumz_light_capsule": 4.0,
}
VCOL_ATTR = "Color 1"          # what Sollumz names GTA's vertex colour 0


class _State:
    def __init__(self):
        self.handle = None
        self.shader = None
        self.shadow_shader = None
        self.batches = []          # (object, batch, has_vcol)
        self.ubo = None
        self.count = 0
        self.lights_report = []
        self.bounds = None         # (centre Vector, radius float)
        # sun shadow
        self.sun_shadow = True
        self.sun_offscreen = None
        self.sun_mvp = Matrix.Identity(4)
        self.sun_pos = Vector((0.0, 0.0, 0.0))
        self.sun_strength = 1.0
        # biases in SHADOW TEXELS, converted to world units at draw time - a
        # fixed metre value only holds at the scale it was tuned for
        self.sun_bias_texels = 2.0
        self.sun_bias_slope_texels = 12.0
        self.sun_texel_world = 1.0
        self.sun_valid = False
        # tunables
        self.exposure = 1.0
        self.albedo = 0.75
        self.lights_multiplier = 1.0
        self.mode = 0              # 0 lit, 1 lights only, 2 normals
        self.selection_only = False
        self.use_vcol_masks = True
        self.spec_intensity = 1.0
        self.spec_falloff_mult = 512.0
        self.spec_fresnel = 0.97
        # ambient - placeholders until load_timecycle()
        self.amb_down_wrap = 1.0
        self.natural_mask = 1.0
        self.artificial_mask = 1.0
        self.amb_nat_up = (0.20, 0.24, 0.30)
        self.amb_nat_dn = (0.05, 0.06, 0.08)
        self.amb_art_up = (0.18, 0.16, 0.13)
        self.amb_art_dn = (0.05, 0.05, 0.05)
        self.dir_amb = (0.10, 0.11, 0.13)
        self.dir_col = (0.00, 0.00, 0.00)
        self.light_dir = (-0.35, -0.45, -0.82)
        self.timecycle = None


_S = _State()


# ------------------------------------------------------------- light gathering

def _gather_lights():
    data = np.zeros((MAX_LIGHTS, 6, 4), dtype=np.float32)
    report = []
    n = 0
    for ob in bpy.context.scene.objects:
        if n >= MAX_LIGHTS or ob.type != 'LIGHT' or not ob.visible_get():
            continue
        la = ob.data
        ltype = SOLLUM_TYPE.get(getattr(la, "sollum_type", "sollumz_light_none"))
        if ltype is None:
            continue
        lp, lf = la.light_properties, la.light_flags
        mw = ob.matrix_world
        pos = mw.translation
        direction = (mw.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
        # premultiplied exactly as the game: rgb * (2*Intensity/255); Sollumz
        # already stores colour as byte/255, so this is colour * 2 * intensity
        k = 2.0 * lp.intensity
        cull_n = tuple(lp.culling_plane_normal)
        data[n, 0] = (pos.x, pos.y, pos.z, ltype)
        data[n, 1] = (la.color[0] * k, la.color[1] * k, la.color[2] * k, lp.falloff)
        data[n, 2] = (direction.x, direction.y, direction.z, lp.falloff_exponent)
        # Sollumz derives cone_inner/outer_angle from spot_blend / spot_size,
        # which only exist on a SPOT light. Reading them on a point or capsule
        # raises inside the getter - Blender swallows it and hands back junk.
        # Only a spot has a cone, so only a spot gets asked.
        inner = outer = 0.0
        if ltype == 2.0:
            inner, outer = lp.cone_inner_angle, lp.cone_outer_angle
        data[n, 3] = (inner, outer, lp.extent[0],
                      1.0 if lf.enable_culling_plane else 0.0)
        data[n, 4] = (cull_n[0], cull_n[1], cull_n[2], lp.culling_plane_offset)
        data[n, 5] = (1.0 if lf.no_specular else 0.0,
                      1.0 if lf.dont_light_alpha else 0.0,
                      1.0 if lf.cast_shadows else 0.0, 0.0)
        report.append({"ad": ob.name,
                       "tip": la.sollum_type.replace("sollumz_light_", ""),
                       "yogunluk": round(lp.intensity, 3),
                       "falloff": round(lp.falloff, 3),
                       "us": round(lp.falloff_exponent, 3),
                       "koni_derece": [round(inner * 57.2958, 1),
                                       round(outer * 57.2958, 1)] if ltype == 2.0 else None})
        n += 1
    return data, n, report


# --------------------------------------------------------------- mesh batching

def _mesh_batch(shader, ob, depsgraph):
    """Corner-domain triangle soup in object space; u_model does the transform."""
    eval_ob = ob.evaluated_get(depsgraph)
    try:
        me = eval_ob.to_mesh()
    except RuntimeError:
        return None, False
    if me is None:
        return None, False
    try:
        me.calc_loop_triangles()
        ntri = len(me.loop_triangles)
        if ntri == 0:
            return None, False

        loops = np.empty(ntri * 3, dtype=np.int32)
        me.loop_triangles.foreach_get("loops", loops)
        vidx = np.empty(len(me.loops), dtype=np.int32)
        me.loops.foreach_get("vertex_index", vidx)
        co = np.empty(len(me.vertices) * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        nrm = np.empty(len(me.loops) * 3, dtype=np.float32)
        me.corner_normals.foreach_get("vector", nrm)
        nrm = nrm.reshape(-1, 3)

        # GTA's baked masks. BYTE_COLOR exposes both `color` (gamma decoded to
        # linear) and `color_srgb` (the raw byte/255). The game uses the RAW
        # value as a multiplier, so reading `color` would silently darken every
        # mask - take color_srgb.
        attr = me.color_attributes.get(VCOL_ATTR)
        has_vcol = attr is not None and attr.domain == 'CORNER'
        if has_vcol:
            vc = np.empty(len(attr.data) * 4, dtype=np.float32)
            field = "color_srgb" if attr.data_type == 'BYTE_COLOR' else "color"
            attr.data.foreach_get(field, vc)
            vc = vc.reshape(-1, 4)[loops]
        else:
            vc = np.ones((ntri * 3, 4), dtype=np.float32)

        pos = co[vidx[loops]]
        batch = batch_for_shader(shader, 'TRIS',
                                 {"pos": pos, "nrm": nrm[loops], "vcol": vc})
        return batch, has_vcol
    finally:
        eval_ob.to_mesh_clear()


def _scene_bounds(objects):
    pts = []
    for ob in objects:
        for c in ob.bound_box:
            pts.append(ob.matrix_world @ Vector(c))
    if not pts:
        return None
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (mn + mx) * 0.5
    return c, max((mx - mn).length * 0.5, 1e-3)


# ------------------------------------------------------------------ sun shadow

def _sun_matrices():
    """Ortho view from a virtual sun position, covering the whole scene."""
    if _S.bounds is None:
        return None
    centre, radius = _S.bounds
    d = Vector(_S.light_dir)
    if d.length < 1e-5:
        return None
    d.normalize()
    eye = centre + d * (radius * 2.5)
    f = (centre - eye).normalized()
    up_ref = Vector((0.0, 0.0, 1.0)) if abs(f.z) < 0.99 else Vector((0.0, 1.0, 0.0))
    r = f.cross(up_ref).normalized()
    u = r.cross(f).normalized()
    view = Matrix((
        (r.x, r.y, r.z, -r.dot(eye)),
        (u.x, u.y, u.z, -u.dot(eye)),
        (-f.x, -f.y, -f.z, f.dot(eye)),
        (0.0, 0.0, 0.0, 1.0)))
    ext = radius * 1.15
    _S.sun_texel_world = 2.0 * ext / shaders.SHADOW_RES
    near, far = 0.01, radius * 6.0
    ortho = Matrix((
        (1.0 / ext, 0.0, 0.0, 0.0),
        (0.0, 1.0 / ext, 0.0, 0.0),
        (0.0, 0.0, -2.0 / (far - near), -(far + near) / (far - near)),
        (0.0, 0.0, 0.0, 1.0)))
    return ortho @ view, eye


def _render_sun_shadow():
    _S.sun_valid = False
    if not _S.sun_shadow or not _S.batches:
        return
    m = _sun_matrices()
    if m is None:
        return
    _S.sun_mvp, _S.sun_pos = m
    if _S.shadow_shader is None:
        _S.shadow_shader = shaders.build_shadow()
    res = shaders.SHADOW_RES
    if _S.sun_offscreen is None:
        _S.sun_offscreen = gpu.types.GPUOffScreen(res, res, format='RGBA32F')

    sh = _S.shadow_shader
    with _S.sun_offscreen.bind():
        fb = gpu.state.active_framebuffer_get()
        # a huge distance means "nothing occludes here"
        fb.clear(color=(1e9, 0.0, 0.0, 1.0), depth=1.0)
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.depth_mask_set(True)
        sh.bind()
        sh.uniform_float("u_sunMvp", _S.sun_mvp)
        sh.uniform_float("u_sunPos", (_S.sun_pos.x, _S.sun_pos.y, _S.sun_pos.z, 0.0))
        for ob, batch, _hv in _S.batches:
            sh.uniform_float("u_model", ob.matrix_world)
            batch.draw(sh)
        gpu.state.depth_mask_set(False)
        gpu.state.depth_test_set('NONE')
    _S.sun_valid = True


# ---------------------------------------------------------------------- build

def _rebuild():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    if _S.shader is None:
        _S.shader = shaders.build_model()

    data, n, report = _gather_lights()
    _S.ubo = gpu.types.GPUUniformBuf(data.tobytes())
    _S.count = n
    _S.lights_report = report

    _S.batches = []
    objs = []
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH' or not ob.visible_get():
            continue
        if _S.selection_only and not ob.select_get():
            continue
        b, hv = _mesh_batch(_S.shader, ob, depsgraph)
        if b is not None:
            _S.batches.append((ob, b, hv))
            objs.append(ob)
    _S.bounds = _scene_bounds(objs)
    _render_sun_shadow()


# ------------------------------------------------------------------- drawing

def _draw():
    if _S.shader is None or not _S.batches:
        return
    r3d = bpy.context.region_data
    if r3d is None:
        return
    sh = _S.shader
    sh.bind()
    sh.uniform_block("lights", _S.ubo)
    if _S.sun_offscreen is not None:
        sh.uniform_sampler("sunShadow", _S.sun_offscreen.texture_color)

    cam = r3d.view_matrix.inverted().translation
    sh.uniform_float("u_camera", (cam.x, cam.y, cam.z, 0.0))
    sh.uniform_float("u_params", (_S.lights_multiplier, _S.amb_down_wrap,
                                  1.0 / (1.0 + _S.amb_down_wrap), _S.albedo))
    sh.uniform_float("u_spec", (_S.spec_intensity, _S.spec_falloff_mult,
                                _S.spec_fresnel, 0.0))
    sh.uniform_float("u_exposure", (_S.exposure, 0.0, 0.0, 0.0))
    sh.uniform_float("u_masks", (_S.natural_mask, _S.artificial_mask, 0.0, 0.0))
    d = Vector(_S.light_dir).normalized()
    sh.uniform_float("u_lightDir", (d.x, d.y, d.z, 0.0))
    for name, v in (("u_ambNatUp", _S.amb_nat_up), ("u_ambNatDn", _S.amb_nat_dn),
                    ("u_ambArtUp", _S.amb_art_up), ("u_ambArtDn", _S.amb_art_dn),
                    ("u_dirAmb", _S.dir_amb), ("u_dirCol", _S.dir_col)):
        sh.uniform_float(name, (v[0], v[1], v[2], 0.0))
    on = 1.0 if (_S.sun_valid and _S.sun_shadow) else 0.0
    sh.uniform_float("u_sun", (_S.sun_pos.x, _S.sun_pos.y, _S.sun_pos.z, on))
    sh.uniform_float("u_sunBias", (_S.sun_bias_texels * _S.sun_texel_world,
                                   _S.sun_bias_slope_texels * _S.sun_texel_world,
                                   1.0 / shaders.SHADOW_RES, _S.sun_strength))
    sh.uniform_float("u_sunMvp", _S.sun_mvp)

    proj = gpu.matrix.get_projection_matrix()
    view = gpu.matrix.get_model_view_matrix()

    # Blender already drew these triangles in its solid pass; sharing its depth
    # buffer z-fights across every surface. Clearing depth makes this pass
    # authoritative wherever it covers.
    gpu.state.active_framebuffer_get().clear(depth=1.0)
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.depth_mask_set(True)
    gpu.state.face_culling_set('BACK')
    try:
        for ob, batch, has_vcol in _S.batches:
            m = ob.matrix_world
            sh.uniform_float("u_model", m)
            sh.uniform_float("u_mvp", proj @ view @ m)
            sh.uniform_float("u_counts", (float(_S.count), float(_S.mode),
                                          1.0 if (has_vcol and _S.use_vcol_masks) else 0.0,
                                          0.0))
            batch.draw(sh)
    finally:
        gpu.state.depth_mask_set(False)
        gpu.state.face_culling_set('NONE')
        gpu.state.depth_test_set('NONE')


# --------------------------------------------------------------------- API

def enable():
    disable()
    _rebuild()
    _S.handle = bpy.types.SpaceView3D.draw_handler_add(_draw, (), 'WINDOW', 'POST_VIEW')
    _tag_redraw()
    return report()


def disable():
    if _S.handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_S.handle, 'WINDOW')
        _S.handle = None
    _S.batches = []
    _tag_redraw()


def refresh():
    _rebuild()
    _tag_redraw()
    return report()


def cfg(**kw):
    for k, v in kw.items():
        if not hasattr(_S, k):
            raise KeyError("bilinmeyen ayar: %s" % k)
        setattr(_S, k, v)
    if "selection_only" in kw:
        _rebuild()
    elif "sun_shadow" in kw:
        _render_sun_shadow()
    _tag_redraw()


def load_timecycle(weather="w_clear", hour=20.0, region="GLOBAL",
                   modifier=None, strength=1.0, hdr=False):
    """Ambient + sun from a real GTA weather cycle, optionally with an interior
    timecycle modifier blended over it (base + (mod - base) * strength)."""
    import cycle
    a = cycle.ambient_at(weather=weather, hour=hour, region=region,
                         modifier=modifier, strength=strength, hdr=hdr)
    for k in ("amb_nat_up", "amb_nat_dn", "amb_art_up", "amb_art_dn",
              "dir_amb", "dir_col", "amb_down_wrap", "light_dir"):
        setattr(_S, k, a[k])
    _S.timecycle = a["_meta"]
    _render_sun_shadow()          # sun moved, the map is stale
    _tag_redraw()
    return a["_meta"]


def weathers():
    import cycle
    return cycle.available()


def modifiers(pattern=""):
    import cycle
    return cycle.modifiers(pattern)


def report():
    return {
        "aktif": _S.handle is not None,
        "timecycle": _S.timecycle,
        "isik_sayisi": _S.count,
        "mesh_batch": len(_S.batches),
        "vcol_maskeli_mesh": sum(1 for _o, _b, hv in _S.batches if hv),
        "gunes_golgesi": _S.sun_valid and _S.sun_shadow,
        "mod": ["lit", "sadece_isik", "normal", "golge_faktoru"][_S.mode],
        "isiklar": _S.lights_report,
    }


def _tag_redraw():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'VIEW_3D':
                a.tag_redraw()
