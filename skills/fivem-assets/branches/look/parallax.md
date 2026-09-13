# Parallax (`*_pxm`) — hole, recess, relief on a flat surface, 4-layer ground

**When to read:** a hole/damage in a wall, broken plaster, relief, depth on a large floor — a hole, recess or relief on a flat surface (`*_pxm`); layered parallax; "parallax does not animate", "it looks fake on the floor"; when parallax breaks on curved geometry.
**Source:** `parallax.md` (all of it) + the former SKILL/`/look` summary (2026-08) · **Measured:** 16 variants / 571 vanilla usages; a commercial MLO patch read field by field; a calibration board in game
**Read first:** `_branch.md` · trunk › `trunk/tool-pitfalls.md` §1-2

---

## PARALLAX — depth on a flat surface (`/look`)



Parallax **shifts the diffuse's UV by the view angle** according to the height map.
It does nothing else.

- ⛔ **It does not invent content** — the inside of the hole must be **painted** into the diffuse.
  Criterion: **with parallax off, the texture alone must look like a hole.**
  If it does not, parallax turns it into a **sliding sticker**, not a hole.
- ⛔ **It is not animation** — it does not move by itself, it changes only with the camera
  angle. An "it does not animate" complaint is **expected behavior**.
- ⛔ **It does not break the silhouette and carries no collision.** On a floor it looks fake at once, on a wall it does not.

Shader choice from the data (`assetdb.py shader pxm`): **`normal_spec_pxm` with 218
usages = default**; `normal_pxm` only 3 usages, do not pick it by reflex;
if alpha is required, `normal_spec_decal_pxm` (bucket 2, casts no shadow); large ground
**`terrain_cb_w_4lyr_pxm`** (12 textures, vanilla ratio 84% on near terrain,
**no** parallax in the LOD version).

For a hole/recess `heightBias` is **negative**. On a wall `heightScale` 0.03–0.05;
on the ground stay in the vanilla band (≈0.03) — the ground is always seen at a grazing angle,
parallax's worst case.

**Diagnosis:** flat when viewed straight on + deep at an oblique view → parallax. The depth of a real pit
shows **most when viewed straight on**; with parallax it is the opposite.

**It can be combined with UV animation** (measured in game) — but
⛔ **`normal_spec_pxm` HAS NO `globalAnimUV`**; a material that needs animation must switch to
`normal_pxm`. And ⛔ **the motion cannot be region-specific**: the matrix applies to
the material's whole UV space, so three balls in one texture all make the same motion.
For independent motion: several materials, a sprite sheet or layered planes.

⛔ **Vanilla interiors have NO parallax** (not a single `*_pxm` in v_coroner or v_abattoir).
This is a modern modder technique; R\* gets depth from geometry + texture +
vertex color + light. → `branches/map/vanilla-interiors.md`

---



---


Making a flat surface look like a hole/recess/relief. Measurement sources:
the `muto-atlas` shader table (249 shaders, vanilla usage counts), Sollumz
`szio/gta5/Shaders.xml`, the material of a commercial MLO read field by field, and
**our own test board run in game** (2026-08-23).

---

## 0. MECHANISM — three sentences

Parallax looks at the height map and **shifts the diffuse's UV by the view
angle**. It does nothing else.

- ⛔ **It does not invent content.** The inside of the hole (brick, wood, darkness, rubble)
  **has to be painted into the diffuse.** If it is not painted, there is nothing to shift.
- ⛔ **It is NOT animation.** It does not move by itself; it changes only when the **camera
  angle** changes. A player standing still sees nothing.
  *(measured: in game, 2026-08-23)*
- ⛔ **It does not break the silhouette and carries no collision.** The edge of the "pit" stays flat and
  the player walks on the flat plane. Nobody notices on a wall; **on a floor it looks fake**.

---

## 1. DIAGNOSIS — geometry, parallax or a flat texture

Compare the same spot from a **straight-on** and an **oblique** angle:

| straight on | oblique | diagnosis |
|---|---|---|
| flat | flat | **flat painted texture** |
| flat | deep | **parallax** |
| deep | deep (occludes) | **real geometry** |

The depth of a real pit shows **most when viewed straight on**. With parallax it is **the exact
opposite**: while the view ray is parallel to the height axis the UV shift ≈ 0.

*(measured twice: in a commercial MLO's promo video at t=0.4 vs t=2.8;
and on our own board, the control panel vs the `heightScale 0.12` panel.)*

---

## 2. SHADER CHOICE — by vanilla usage

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" shader normal_spec_pxm --exact
```

| shader | vanilla | bucket | textures | when |
|---|---|---|---|---|
| **`normal_spec_pxm`** | **218** | 0 opaque | Diffuse+height+Bump+Spec | **default choice** |
| `normal_pxm` | 3 | 0 opaque | Diffuse+height+Bump | when spec is not needed |
| `normal_spec_decal_pxm` | 196 | 2 decal | +alpha | when alpha is required — **casts no shadow** |
| `normal_decal_pxm` | 13 | 2 decal | | " |
| **`terrain_cb_w_4lyr_pxm`** | **74** | 0 opaque | **12 textures** | **large ground** |

Total `*_pxm` usage across the game: **571**.

⛔ **Do not pick `normal_pxm` by reflex.** Vanilla uses it only 3 times;
`normal_spec_pxm` does the same job, has 218 usages and brings the spec channel
too. It should be the default for a new asset.

⛔ **An opaque shader has NO alpha.** The hole's shape comes from the **mesh silhouette**:
the patch is cut to the damage outline, no rectangular quad is used.
*(measured example: 3 components, 263 vertices / 179 faces / 430 triangles, V−E+F = 3 →
all three are disk topology, i.e. an open surface.)*

---

## 3. PARAMETERS — measured bands

### Vanilla default (`normal_spec_pxm`)

```
HardAlphaBlend 1 · useTessellation 0 · wetnessMultiplier 1
parallaxSelfShadowAmount 0.95 · heightBias 0.015 · heightScale 0.03
bumpiness 1 · specMapIntMask (1,0,0) · specularIntensityMult 1
specularFalloffMult 35 · specularFresnel 0.75
```

### A commercial MLO's wall damage patch (read field by field)

| param | value | vanilla | effect |
|---|---|---|---|
| `heightScale` | 0.040 | 0.03 | amount of shift = visible depth |
| `heightBias` | **−0.200** | +0.015 | **negative = push the surface inward** |
| `parallaxSelfShadowAmount` | 1.000 | 0.95 | the cavity's own shadow |
| `bumpiness` | 0.000 | 1 | 0 = relief **only** from parallax |
| `specularFalloffMult` | 1.000 | 35–100 | 1 = inside of the cavity fully matte |

**Rule:** for a hole/recess `heightBias` is **negative**; for a bump it is
positive. On a wall the `heightScale` band is 0.03–0.05; **on the ground stay in the vanilla band
(≈0.03)**.

---

## 4. LARGE GROUND — there is a separate shader family

**R\* picks parallax by default on near terrain** (measured):

| | usage |
|---|---|
| `terrain_cb_w_4lyr_*` variants with parallax | **135** |
| without parallax | 25 |
| **LOD variants — NO parallax** | 72 |

→ **84% parallax** on near ground, **deliberately dropped** in the LOD version.

`terrain_cb_w_4lyr_pxm`: flag `IS_TERRAIN`, bucket 0, **12 textures** (for each of the 4 layers
`TextureSampler_layerN` + `BumpSampler_layerN` +
`heightMapSamplerLayerN`), a separate `heightScale0..3 = 0.03` and
`heightBias0..3 = 0.015` per layer.

Setup order:
1. **Split the ground with loop cuts** — painting the blend mask needs vertex density
   (`Colour1`: layer0 black, layer1 blue, layer2 green).
2. 4 layers × (diffuse + bump + height) = 12 textures.
3. `heightScale ≈ 0.03`, `heightBias ≈ 0.015` — do not give aggressive values like on a wall.
4. **In the LOD version drop to the variant without parallax** (`terrain_cb_w_4lyr_lod`).

---

## 5. SIZE AND CURVATURE

- **There is no limit in world scale.** `heightScale` is a **tangent/UV space** measure;
  it works the same on a 2 m patch and on 200 m of ground, and it can be tiled.
  *(inference — from the shader math; not measured in game)*
- **The real limits are three:** ① view angle ② the silhouette does not break ③ no collision.
- **The ground is the worst case** because it is always seen at a grazing angle; a wall is the
  best.
- **Curvature:** because it works in tangent space, **gentle curvature is fine** —
  the proof is terrain itself (it is curved, 74 usages). Where it breaks:
  - when the curvature radius approaches the displacement depth (pipe, column, thin cylinder)
  - a UV seam
  - ⛔ **mirrored UVs** — the tangent sign flips, and on one side of the seam the shift goes
    the **opposite way**
  - few segments (faceted tangent frame)
  *Practical threshold (inference, not measured): curvature radius ≥ 10 × (heightScale ×
  the texture's world size).*
- ⛔ **It works on a single plane.** On a patch that wraps a corner, parallax shifts in two directions
  at once and falls apart. In the measured example all three patches are on a flat wall, none
  touches a corner.

---

## 6. TEXTURE — this is the real half of the job

Parallax only shifts what is painted. So **the criterion is:**

> ⛔ **With parallax OFF, the texture alone must look like a hole.**
> If it does not, parallax does not make it a hole; it only makes a **sliding sticker**.

This test was skipped once and the fixture came out as junk. Concrete errors (measured,
in game):

1. ⛔ **The cavity came out LIGHTER than the surrounding wall.** A real hole is **darker**
   than its surroundings. If it stays light it looks like a sticker — that alone kills the illusion.
2. ⛔ **No depth painted into the diffuse** — without elements that create occlusion (beam, rubble,
   broken edge) the shifting thing reads as a flat pattern.
3. ⛔ **The edge is soft like an airbrush** (~22 px transition at 1024). Broken plaster
   is hard and jagged.
4. ⛔ **The height profile is a bowl; it should be a pit:** a **steep drop** at the edge,
   then a **flat floor**. A shallow ramp gives a blurry smear in parallax.

Also: **light.** White panel + overhead sun is the worst case for readability.
The effect reads in a dark, side-lit setting.

### Texture set (`normal_spec_pxm`)

| sampler | content | note |
|---|---|---|
| `DiffuseSampler` | inside of the hole **painted**, outside is the surface | DXT1 is enough |
| `heightSampler` | 1 = surface, 0 = deepest | DXT5 (keep it in alpha too → clean gradient) |
| `BumpSampler` | normal map | can be derived from height |
| `SpecSampler` | cavity matte, surface slightly glossy | DXT1 |

---


## 7. HIDING THE BREAKUP

Parallax vanishes when viewed straight on and swims at very flat angles. The measured commercial asset
put **iron bars** in front of the holes: they keep the player at a distance and break the
edges where the breakup is most visible. The bars are not decoration,
they are **the effect's mask**. *(inference — but consistent across all three holes.)*

---

## 8. SOLLUMZ SIDE

The shader registry is **not** in `cwxml.shader.ShaderManager`:
`…/sollumz/lib/python3.13/site-packages/szio/gta5/Shaders.xml`

```python
from bl_ext.user_default.sollumz.ydr.shader_materials import create_shader
mat = create_shader("normal_spec_pxm.sps")
mat.node_tree.nodes['heightScale'].outputs[0].default_value = 0.04
mat.node_tree.nodes['heightBias'].outputs[0].default_value = -0.20
mat.node_tree.nodes['DiffuseSampler'].image = img   # img.name = the texture name in the ytd
mat.node_tree.nodes['DiffuseSampler'].texture_properties.embedded = False
```

**Mesh requirement:** layout `Position / Normal / Colour0 / TexCoord0 /
TexCoord1 / TexCoord2 / Tangent` → in Blender create **`UVMap 0` / `1` / `2`**;
Sollumz generates the tangent.

⛔ **If `ob.sz_lods.high.mesh = ob.data` is not assigned, export SKIPS the drawable ENTIRELY.**
On meshes made by a script this field stays `None`.

⛔ **If `target_formats` is both NATIVE and CWXML, the output goes into `gen8/` and `gen9/`
SUBFOLDERS.** For FiveM use **gen8**.

---

## 9. VERIFICATION — do not say "done" without reading back

```bash
powershell -File "${CLAUDE_PLUGIN_ROOT}/scripts/res_to_xml.ps1" -Path out/gen8/x.ydr
```

What to check in the XML:
- material count = expected
- whether the `<FileName>` hash is the right shader — compare with JOAAT
  (`normal_spec_pxm.sps` → **`58C733F4`**, `normal_spec.sps` → **`14A780FD`**)
- whether the `heightScale` / `heightBias` values are **inside the binary**
- whether `ShaderIndex` binds the right material to each geometry

⛔ Do not assume the file is right because export gave "0 warnings". File size is not a
criterion either (RSC7 is zlib-compressed).

---

## 10. IN-GAME TEST — the calibration board pattern

N panels side by side in one `.ydr`, all sharing the same texture, **only
`heightScale` changes**, plus one **control panel without parallax**.
One walk answers N questions.

Viewing order:
1. **Straight on** — all panels must look identical. If not,
   the `heightBias` model is wrong.
2. **At an angle, stepping sideways** — this is where depth shows; which one is convincing,
   which one swims.
3. **Very flat** — see the angle where the breakup starts.

⛔ If the control panel **does not look like a hole on its own, the test measures
nothing** (§6).

Asset changed → **leave the server and reconnect**; restart is not enough.
