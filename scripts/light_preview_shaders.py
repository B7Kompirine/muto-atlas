"""GLSL for the engine preview: the forward model pass and the sun shadow pass.

Ported from the engine's own shader source (lighting_common.fxh, common.fxh,
postfx.fx). Blender 5.x killed GPUShader(vertexcode, fragcode) - everything
must go through gpu.shader.create_from_info, so the sources live here as plain
strings and the builders below assemble the CreateInfo.
"""

import gpu

MAX_LIGHTS = 64
SHADOW_RES = 2048

TYPEDEF = """
struct PrevLight {
  vec4 posType;    /* xyz world pos, w type: 1 point 2 spot 4 capsule */
  vec4 colFall;    /* rgb premultiplied colour, w falloff radius */
  vec4 dirExp;     /* xyz direction, w falloff exponent */
  vec4 cone;       /* x inner, y outer (rad), z capsule extent, w cullEnable */
  vec4 cullPlane;  /* xyz plane normal, w offset */
  vec4 flags;      /* x noSpecular, y dontLightAlpha, z castShadows */
};
"""

MODEL_VERT = """
void main() {
  vec4 wp = u_model * vec4(pos, 1.0);
  v_wpos = wp.xyz;
  v_wnrm = normalize(mat3(u_model) * nrm);
  v_vc = vcol;
  gl_Position = u_mvp * vec4(pos, 1.0);
}
"""

MODEL_FRAG = """
/* __powapprox: the engine does NOT use pow() here. Rational, exact at 0 and 1. */
float falloffPow(float a, float b) { return a / ((1.0 - b) * a + b); }

/* distanceFalloff operates on SQUARED distance */
float distanceFalloff(float d2, float invMaxD2, float e) {
  return falloffPow(clamp(1.0 - d2 * invMaxD2, 0.0, 1.0), e);
}

/* the spot cone is linear in the COSINE of the angle, not the angle */
float coneFalloff(float cosA, float inner, float outer) {
  float co = cos(outer), ci = cos(inner);
  float s = 1.0 / max(ci - co, 1e-4);
  return clamp(cosA * s + (-co * s), 0.0, 1.0);
}

float filmicCh(float x) {
  const float A=0.22,B=0.30,C=0.10,D=0.20,E=0.01,F=0.30;
  return ((x*(A*x+C*B)+D*E)/(x*(A*x+B)+D*F)) - E/F;
}
vec3 filmicTonemap(vec3 c) {
  float ooW = 1.0 / filmicCh(11.2);
  return clamp(vec3(filmicCh(c.r), filmicCh(c.g), filmicCh(c.b)) * ooW, 0.0, 1.0);
}

vec4 segNearest(vec3 v, vec3 a, vec3 b) {
  vec3 ab = b - a, av = v - a;
  if (dot(av, ab) <= 0.0) return vec4(av, length(av));
  vec3 bv = v - b;
  if (dot(bv, ab) >= 0.0) return vec4(bv, length(bv));
  vec3 abv = cross(ab, av);
  float d = length(abv) / length(ab);
  return vec4(normalize(cross(abv, ab)) * d, d);
}

/* The sun shadow map stores DISTANCE from a virtual sun position, not depth.
   Anything nearer than what is stored is occluded.

   Both biases are in WORLD UNITS DERIVED FROM THE TEXEL SIZE, not fixed metres.
   A fixed-metre bias only works at the scale it was tuned for: on a 660 m map
   one shadow texel covers ~0.4 m, the distance stored in it can be metres off
   the exact fragment, and a 0.15 m bias marks 72% of flat ground as occluded.
   u_sunBias.x/.y arrive already multiplied by the texel's world size.

   The normal offset does the heavy lifting: sampling from a point pushed off
   the surface beats depth bias alone, and it is what lets coplanar decal
   overlays (roads + their plates) stop shadowing each other. */
float sunShadowFactor(vec3 wpos, vec3 n) {
  if (u_sun.w < 0.5) return 1.0;
  vec3 L = normalize(u_sun.xyz - wpos);
  float ndl = clamp(dot(n, L), 0.0, 1.0);
  vec3 p = wpos + n * (u_sunBias.x * (1.0 + 2.0 * (1.0 - ndl)));

  vec4 sp = u_sunMvp * vec4(p, 1.0);
  if (sp.w <= 1e-5) return 1.0;
  vec2 uv = sp.xy / sp.w * 0.5 + 0.5;
  if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) return 1.0;

  float pdist = length(u_sun.xyz - p);
  float bias = u_sunBias.x + (1.0 - ndl) * u_sunBias.y;
  float texel = 1.5 * u_sunBias.z;
  float lit = 0.0;
  for (int i = -1; i <= 1; i++)
    for (int j = -1; j <= 1; j++) {
      float sd = texture(sunShadow, uv + vec2(i, j) * texel).r;
      lit += (pdist > sd + bias) ? 0.0 : 1.0;
    }
  return mix(1.0, lit / 9.0, clamp(u_sunBias.w, 0.0, 1.0));
}

/* calculateAmbient: colour0*downMult + colour1, NOT a hemisphere lerp.
   Natural (sky) ambient is gated by vertex colour 0 .r, artificial (interior)
   by .g - GTA's baked masks. u_masks scales both so they stay steerable, and
   u_counts.z says whether this mesh actually carries the bake. */
vec3 ambientTerm(vec3 n, vec2 gate) {
  float downMult = max(0.0, (n.z + u_params.y) * u_params.z);
  vec3 amb  = (u_ambNatUp.rgb * downMult + u_ambNatDn.rgb) * gate.x;
  amb += u_dirAmb.rgb * clamp(dot(u_lightDir.xyz, n), 0.0, 1.0) * gate.x;
  amb += (u_ambArtUp.rgb * downMult + u_ambArtDn.rgb) * clamp(gate.y, 0.0, 1.0);
  return amb;
}

vec3 computeLight(PrevLight l, vec3 wpos, vec3 camRel, vec3 n, vec3 albedo, vec4 spec) {
  vec3 srpos = l.posType.xyz - wpos;
  float ldist = length(srpos);
  if (l.cone.w > 0.5) {
    if (dot(srpos, l.cullPlane.xyz) - l.cullPlane.w > 0.0) return vec3(0.0);
  }
  if (l.posType.w > 3.5) {
    vec3 ext = l.dirExp.xyz * (l.cone.z * 0.5);
    vec4 sn = segNearest(srpos, ext, -ext);
    ldist = sn.w; srpos = sn.xyz;
  }
  if (ldist > l.colFall.w || ldist <= 0.0) return vec3(0.0);

  vec3 ldir = srpos / ldist;
  float invD2 = 1.0 / max(l.colFall.w * l.colFall.w, 1e-6);
  float lamt = distanceFalloff(ldist * ldist, invD2, l.dirExp.w);

  if (l.posType.w > 1.5 && l.posType.w < 2.5) {
    lamt *= coneFalloff(-dot(ldir, l.dirExp.xyz), l.cone.x, l.cone.y);
    if (lamt <= 0.0) return vec3(0.0);
  }

  float cosT = clamp(dot(ldir, n), 0.0, 1.0);
  float pclit = cosT * lamt;

  vec3 s = vec3(0.0);
  if (spec.r > 0.0 && cosT > 0.0 && l.flags.x < 0.5) {
    vec3 eye = normalize(-camRel);
    vec3 H = normalize(eye + ldir);
    float f = spec.b;
    float fres = (1.0 - f) + f * pow(1.0 - clamp(dot(H, eye), 0.0, 1.0), 5.0);
    float e = spec.g;
    float bp = pow(clamp(dot(H, n), 0.0, 1.0), e + 1e-8);
    s = l.colFall.rgb * ((fres * bp) * pclit * ((2.0 + e) / 8.0) * spec.r);
  }
  if (pclit <= 0.0) return s;
  return l.colFall.rgb * albedo * pclit + s;
}

void main() {
  vec3 n = normalize(v_wnrm);
  /* mode 3: the sun shadow factor on its own - the only way to tell "no shadow
     is being cast" apart from "the shadow term is not reaching the shader" */
  if (u_counts.y > 2.5) { fragColor = vec4(vec3(sunShadowFactor(v_wpos, n)), 1.0); return; }
  if (u_counts.y > 1.5) { fragColor = vec4(n * 0.5 + 0.5, 1.0); return; }

  vec3 albedo = vec3(u_params.w);
  vec3 camRel = v_wpos - u_camera.xyz;

  /* no spec map -> the game feeds a constant 0.1; it is NOT matte.
     exponent remap 0..500 -> 0..1500, 501..512 -> 1500..8192 */
  float rawExp = 0.1 * u_spec.y;
  float expand = max(0.0, rawExp - 500.0);
  vec4 spec = vec4(0.1 * u_spec.x, (rawExp - expand) * 3.0 + expand * 558.0,
                   clamp(u_spec.z, 0.0, 1.0), 0.0);

  /* u_counts.z: 1 = this mesh carries GTA's baked vertex-colour masks */
  vec2 gate = (u_counts.z > 0.5) ? v_vc.rg * u_masks.xy : u_masks.xy;

  vec3 c = vec3(0.0);
  if (u_counts.y < 0.5) {
    float lf = clamp(dot(u_lightDir.xyz, n), 0.0, 1.0) * sunShadowFactor(v_wpos, n);
    c = albedo * (u_dirCol.rgb * lf) + albedo * ambientTerm(n, gate);
  }
  int cnt = int(u_counts.x);
  for (int i = 0; i < cnt; i++)
    c += computeLight(lights[i], v_wpos, camRel, n, albedo, spec) * u_params.x;

  fragColor = vec4(filmicTonemap(c * u_exposure.x), 1.0);
}
"""

SHADOW_VERT = """
/* u_sunMvp is world->sun clip in BOTH passes, so the matrix uploaded here is
   the same one the model pass samples with. Object transform stays in u_model. */
void main() {
  vec4 wp = u_model * vec4(pos, 1.0);
  s_wpos = wp.xyz;
  gl_Position = u_sunMvp * wp;
}
"""

SHADOW_FRAG = """
void main() { fragColor = vec4(length(s_wpos - u_sunPos.xyz), 0.0, 0.0, 1.0); }
"""

_MODEL_PUSH = ["u_camera", "u_params", "u_spec", "u_counts", "u_exposure",
               "u_masks", "u_lightDir", "u_ambNatUp", "u_ambNatDn",
               "u_ambArtUp", "u_ambArtDn", "u_dirAmb", "u_dirCol",
               "u_sun", "u_sunBias"]


def build_model():
    iface = gpu.types.GPUStageInterfaceInfo("lp_model_iface")
    iface.smooth('VEC3', "v_wpos")
    iface.smooth('VEC3', "v_wnrm")
    iface.smooth('VEC4', "v_vc")
    info = gpu.types.GPUShaderCreateInfo()
    info.typedef_source(TYPEDEF)
    info.vertex_in(0, 'VEC3', "pos")
    info.vertex_in(1, 'VEC3', "nrm")
    info.vertex_in(2, 'VEC4', "vcol")
    info.vertex_out(iface)
    info.fragment_out(0, 'VEC4', "fragColor")
    info.uniform_buf(0, "PrevLight", "lights[%d]" % MAX_LIGHTS)
    info.sampler(0, 'FLOAT_2D', "sunShadow")
    info.push_constant('MAT4', "u_mvp")
    info.push_constant('MAT4', "u_model")
    info.push_constant('MAT4', "u_sunMvp")
    for n in _MODEL_PUSH:
        info.push_constant('VEC4', n)
    info.vertex_source(MODEL_VERT)
    info.fragment_source(MODEL_FRAG)
    return gpu.shader.create_from_info(info)


def build_shadow():
    iface = gpu.types.GPUStageInterfaceInfo("lp_shadow_iface")
    iface.smooth('VEC3', "s_wpos")
    info = gpu.types.GPUShaderCreateInfo()
    info.vertex_in(0, 'VEC3', "pos")
    info.vertex_in(1, 'VEC3', "nrm")
    info.vertex_in(2, 'VEC4', "vcol")
    info.vertex_out(iface)
    info.fragment_out(0, 'VEC4', "fragColor")
    info.push_constant('MAT4', "u_model")
    info.push_constant('MAT4', "u_sunMvp")
    info.push_constant('VEC4', "u_sunPos")
    info.vertex_source(SHADOW_VERT)
    info.fragment_source(SHADOW_FRAG)
    return gpu.shader.create_from_info(info)
