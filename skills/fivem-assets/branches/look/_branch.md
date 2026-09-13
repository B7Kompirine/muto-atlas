# Look — branch rules (shader · texture · light · decal · timecycle · parallax · vertex color · emissive)

Command: `/look`
**Keywords:** shader, .sps, material, render bucket, emissive, cutout, alpha, texture, .ytd, DDS, DXT, DXT1, DXT5, mip, mipmap, power of two, normal map, spec, gloss, UVMap, Color 1, vertex color, vertex colour, ambient, parallax, pxm, hole, recess, relief, heightScale, light, lamp, dim light, not lighting up, TimeFlags, Flashiness, flicker, flickering, cone, gobo, projection, projected texture, culling plane, Tangent, decal, decal.sps, graffiti, stain, blood mark, AddDecal, timecycle, weather, dark, gloomy, wet, weathersync, emissive panel, fluorescent, bake, baking, PBR, roughness, trim sheet, tint
**What belongs here:** **How something LOOKS** — shader, texture/DDS, light, decal, timecycle, parallax, bake, emissive. Boundary: not the model's geometry, but the coating and light **on** it.

> The keywords above **speed things up; they are not exhaustive.** If a word is not in the list, routing
> does not stop — check this definition. *“roller shutter”* is not in the list, yet it is a door object.



## Holds for every leaf in this branch

Measurement sources: 249 shaders / 24,000 model usages; 72,539 embedded lights; 1,087 timecycle modifiers; 16 pxm variants / 571
usages; morgue MLO in game; the engine's shader source ported.

### Shader and texture
- ⛔ **Choosing a `.sps` chooses two things: program + render bucket.** The bucket is separate and **writable** (`renderbucket`); `emissive_clip.sps`
  sits in the OPAQUE bucket, and the opaque bucket **never reads alpha** (the holes closed). Look at the bucket, not the name. The name written
  to the ydr is the **program** name, not the `.sps` file name (`emissive_alpha.sps` → `emissive`).
- **The default opaque shader is `normal_spec.sps`** (diffuse + `_n` + `_s`); the wrong choice when tint/skin is wanted. The first material of a
  template `.ydr` may not be the right shader (`w_pi_pistol[0]` = `normal_spec_decal`) — build the material from scratch. `make_dds.py` DXT5+mip,
  `dds_to_ytd.ps1` dictionary; `bake_to_gta.py` for material maps (does not force alpha).
- **GTA is not PBR:** there is **no** roughness/metallic/AO sampler (249 shaders); roughness goes inverted into **spec**, AO **into the diffuse**,
  metallic into shader **scalars**. A material without a spec map is not matte (constant 0.1). The detail map does two jobs.
- **Texture = DXT + mip chain** (normal/spec DXT1 92-99%; diffuse DXT1 when it has no alpha; mips `log2(short side)−1`, ending at 4×4); PNG cannot
  be embedded; **power of two**; a non-square texture stretches the UV. Normal/spec maps are **Non-Color**. `dds_dxt1` carries no alpha — use
  `dds_rgba`/DXT5 for a texture with holes.
- ⛔ **Sollumz packs an embedded texture from the DDS ON DISK**; pixel edits inside Blender embedded a 16×16 placeholder in the `.ydr`, with no error.
  The embedded texture name comes **from the file name**. The same texture name holds different content in different dictionaries (22 of 175 copies) → pick by size.
- `UVMap 0` + `Color 1` are required; `.color` decodes gamma → use `.color_srgb`. The material must be a Sollumz shader; a flat color is not accepted → palette atlas.
- **Textures are not in the model** (map) — external dictionary + `gtxd.meta`; "this surface has no texture" ≠ texture missing (`shader.md`).
- **`AddReplaceTexture` is global for a prop** — the wrong path for per-object content.

### Light
- **A light is bound to a bone**, `Position/Direction/Tangent` are in bone space; in `prop_worklight_01a` the bone is 1.737 m up.
- **`TimeFlags` is a set of hours** (`14680095` = 21:00–05:00; 24/24 = `16777215`; 0 = never on). For "it does not light up", **check the hours first**.
- **`Flashiness` is a named enum** (Sollumz `enum_items`): 0 CONSTANT · 9 ALARM · 15 CANDLE · 17 FIRE · 19 ELECTRIC · 20 STROBE; all three guessed
  values were wrong. "Flicker does not work" → check `Intensity` first. A single Flashiness looks fake; spread the flicker through a variety of types.
- **Gobo:** `Tangent` = the projection's **up** axis (Sollumz writes local X, −90° roll); the texture ships in a `.ytd` of the same name and the archetype
  must reference `textureDictionary`; if the color is in the texture, **the light is white** (the engine multiplies; a doubled color turns purple); `static_shadows` stamps its own
  silhouette; keep the aspect ratio, vignette a square texture.
- **Export from Blender, three bindings:** a hidden light is not dropped, its position breaks · `intensity` is a proxy of `energy` · a bone-bound position is in bone space.
  Do not let the light's transform be wiped when mesh transforms are reset. Cone angles are **radians**. **The criterion is the read-back, not a calculation.**
- **Four formulas differ structurally from Blender:** falloff `a/((1-b)a+b)` on squared distance (`pow` deviates 17.3%) · cone linear in cosine ·
  ambient `downMult` (not a hemisphere lerp) · Hable filmic (white 11.2). Shadow bias in texel units.
- A vanilla decorative lantern has **no** embedded light; putting a light in a prop is a deliberate deviation.

### Timecycle and vertex color
- **Darkness has three layers:** weather cycle (13 keyframes, `levels/gta5/time.xml`; `name` lies, `hour` is right) → room modifier
  (per-param blend; do not touch a shared one, register your own modifier with `TIMECYCLEMOD_FILE`) → prop light.
- **Directional light is not blocked by geometry** — room `flags |= 4|8` (No Directional / No Exterior); a "diff against vanilla" does not catch this,
  the reference is another vanilla MLO doing the same job (vault/facility 111).
- **"The map is wet" has two separate paths**; `SetRainLevel` does not remove wetness; a race against qb-weathersync cannot be won, stop its loop.
- **Vertex color darkening only in `RenderBucket == 0`**; in a non-opaque bucket RGB is a multiplier, lowering R shifts the hue. `R == G > 200`
  ⇒ unpainted (opaque only). R is a direction decision, G an artistic value — do not pin G to one number. A shell must not get prop flags.

### Decal and parallax
- **Decal is three systems:** `AddDecal` (script, 194 types, the texture is a **grey mask** — `rCoef/gCoef/bCoef` give the color) · `decal.sps` + bucket 2
  (baked into the map) · Blender projection (add-on not in the repository). A ray grid cannot hit a parallel surface; the box restarts at corners; thin pipe/grating
  is a painting job. `bisect_plane` deletes faces → Sutherland–Hodgman.
- **Parallax does not invent content** (it is painted into the diffuse), is not animation, does not break the silhouette; `normal_spec_pxm` with 218 usages is the default,
  no `globalAnimUV`; `heightBias` negative for a hole; vanilla interiors have **no** parallax.

### Epistemics (paid for)
- **A screenshot is not a measurement** (a 0.617 grey was taken for "blown out"). **A tool's constant is tuned to its own scale.** A total is a measurement
  of a population; it cannot speak about a single member. If a new measurement refutes an old inference, the inference dies.

## Leaves

| wanted | file | status — source |
|---|---|---|
| Shader choice — program + bucket, PBR→GTA, "no texture" | shader.md | measured — Sollumz Discord shader notes · former light-math reference · bake_to_gta |
| Parallax — hole, recess, relief, 4-layer ground | parallax.md | measured — former parallax-pxm reference |
| Light — read/edit/write back, TimeFlags, Flashiness, gobo | lights.md | measured — former light-math reference · former decal & light reference §4,9 · former error log |
| Light math and Blender preview | light-math.md | measured — former light-math reference §1-8 |
| Timecycle — dark, wet, room flag | timecycle.md | measured — former light-math reference · former decal & light reference §5 · morgue notes |
| Vertex color — interior ambient, bucket rule | vertex-color.md | measured — former light-math reference, vertex color part |
| Emissive panel | emissive.md | measured — former decal & light reference §6 |
| Decal — three systems + source packs | decal.md | measured — former decal & light reference · former ytyp-ymap flags reference §8.5b-8.6 · former decal texture source list |

## Trunk files to read
- `trunk/tool-pitfalls.md` §1 (embedded texture DDS, `use_custom_settings`, cone radians, light export), §2 (`.color_srgb`, bisect, `bound_box`),
- `trunk/verification-ladder.md` — light/texture/decal without putting them in the game: `.ydr` light read-back, `.ytd` size/format
  §3 (`.ytd` schema, `GetXMLFormat`, RPF key)
- `trunk/flags.md` (Time archetype, Cast Shadows, Dont Render In Reflections) ·
  interior budget `branches/map/vanilla-interiors.md`
- Looking for a ready template / tool (Substance GTA baker, timecycle merging, lightshaft `flags 99`, vertex color master, R\* interior color scheme) → `sources/community-resources.md` §1-3, §9 — **source note, not a rule.**
