# Light math and Blender preview — the engine's four formulas, shadow bias, silent failure catalog

**When to read:** it looks one way in Blender and another in game; you are building your own light preview; what the engine's light formulas (falloff/cone/ambient/tone mapping) actually do; previewing a light in Blender before it goes in game.
**Source:** `lights.md` §1-8, 'Blender preview', 'Silent failure catalog', 'Data setup' (2026-08) · **Measured:** the engine's shader source (`lighting_common.fxh`) ported; `pow()` deviation 17.3%
**Read first:** `_branch.md` · trunk › `trunk/tool-pitfalls.md` §1-2 · tool `scripts/blender_light_preview.py`

---


When a prop's light looks one way in Blender and another in game, the cause
is almost never "I could not get the settings right". The four formulas the
engine uses are **structurally different** from the ones Blender (and most
preview tools) use. This file collects those four and the silent failures around them.

Queries:
```
python assetdb.py light <ydr|yft>          # decode the embedded lights
python assetdb.py cycle w_clear --hour 20  # weather cycle: ambient + sun
python assetdb.py timecycle <modifier>     # the room's override
```

---

## 1. The falloff curve is NOT `pow()`

The engine uses a rational approximation:

```
powApprox(a, b) = a / ((1 - b) * a + b)
```

It is exact at 0 and 1 and **approximates** `pow(a,b)` in between. The measured cost of
drawing the same curve with `pow()`: **17.3% deviation** (falloff 90 m, exponent 8).

Two more details; skipping either one silently gives the wrong curve:

- The function works on **squared distance**: `distanceFalloff(d², 1/max², exponent)`
- It is **cut off** at the light's radius — not inverse square, a bounded curve

## 2. The spot cone is linear in COSINE, not in angle

```
cosOuter = cos(outerAngle);  cosInner = cos(innerAngle)
scale    = 1 / max(cosInner - cosOuter, 1e-4)
result   = saturate(cosAngle * scale - cosOuter * scale)
```

A transition that is linear in angle (Blender's `spot_blend` included) softens the edge in
the wrong place. Sollumz keeps cone angles in **radians** (`subtype=ANGLE`,
0–π/2) — writing them in degrees opens the cone completely.

## 3. Capsule light = closest point on a line segment

The extent gives the ±axis as `direction * (extent.x * 0.5)`; the distance to the light is
the shortest distance to that segment, not to the centre. After that it is the same as a point light.

## 4. Ambient light is NOT a hemisphere lerp

```
downMult = max(0, (n.z + wrap) / (1 + wrap))
ambient  = UpColor * downMult + DownColor
```

`wrap` = `light_amb_down_wrap`, it comes from the timecycle (**default 1.0**).
Interiors often look "flat" because a hemisphere lerp is used
instead of this.

Ambient is also **two separate layers**, each gated by a different mask:

| layer | source | gate |
|---|---|---|
| natural (sky) | `light_natural_amb_*` | vertex color 0 **.r** |
| artificial (interior) | `light_artificial_ext_*` | vertex color 0 **.g** |

These are **baked masks**. Sollumz carries them under the name `"Color 1"`,
in the CORNER domain, as BYTE_COLOR.

> ⛔ **Blender BYTE_COLOR pitfall:** `.color` decodes gamma, `.color_srgb` gives the raw
> byte/255. The engine uses the raw value as a multiplier — reading `.color`
> silently darkens every mask, with no error.

## 5. Tone mapping: Hable filmic

```
A=0.22 B=0.30 C=0.10 D=0.20 E=0.01 F=0.30,  white point 11.2
f(x) = ((x(Ax+CB)+DE) / (x(Ax+B)+DF)) - E/F
result = saturate(f(color) / f(11.2))
```

A highlight rolloff you make up yourself clips the daytime to white. This curve does not clip.

## 6. Specular — three separate silent failures

- **A material without a spec map is not matte.** The engine feeds a constant **0.1**.
  Zeroing it makes every surface matte; this is the most common cause of the
  "specular does not show" complaint.
- **The channels are read separately, not dotted:** `x` = intensity, `y` = exponent.
- **Fresnel comes from the MATERIAL, not from the MAP** (`specularFresnel`, 0.97 when the
  preset does not set it). Taking it from the blue channel leaves the fresnel
  control useless on every material that has a spec map.
- The exponent is remapped: `0..500 → 0..1500`, `501..512 → 1500..8192`
  → `(raw - overflow) * 3 + overflow * 558`

## 7. The detail map does two jobs at once

One texture both bends the normal (XY) and darkens the diffuse (X). The fade comes
**from the spec map's alpha channel**. On PC the tile is sampled a second time at **3.17×**
scale and averaged — that odd ratio keeps the tiling from reading as a
grid.

## 8. Other constants

- Color is premultiplied on the CPU: `rgb * (2 * intensity / 255)` — the leading **2** gets dropped
- The UV transform is applied **once** and every sampler uses the result; if they are split,
  a scrolling sign's normal map slides out from under its diffuse
- Flag bits that work live: **6** cast shadows · **13** no specular ·
  **23** don't light alpha (skips alpha geometry completely)
- In game the projection texture must ship **inside a `.ytd` of the same name**
- Lights are written into the `.ydr`/`.yft` as RSC7 / gen8

---

## Blender preview

Blender's own lights **cannot express** this math (inverse square + cone linear in
angle). So the preview draws its own pass, reading the Sollumz lights
directly.

```python
import sys; sys.path.append(r"${CLAUDE_PLUGIN_ROOT}/scripts")
import blender_light_preview as lp
lp.enable()
lp.load_timecycle("w_clear", hour=19)
lp.cfg(albedo=0.35, exposure=1.6)      # real asphalt ~0.2-0.35
lp.load_timecycle("w_clear", 2, modifier="v_dark", strength=1.0)
lp.cfg(mode=3)                          # shadow factor visualization
lp.report(); lp.disable()
```

Modes: `0` lit · `1` light only · `2` normal · `3` shadow factor.

**Blender 5.x notes:** `GPUShader(vs, fs)` was removed, `create_from_info` is
required. There is no `GPUStorageBuf` — lights go through a UBO (that is where the cap of 64 comes from).
If the overlay draws at the same depth as Blender's solid pass, the whole scene
z-fights; the depth buffer is cleared before its own pass.

### Shadow bias must be in texel units

⛔ Do not copy a tool's shadow bias constant. A constant bias in metres is right only at
the scale it was tuned for: the 0.15 m that is right for a prop marked **72%** of the flat
ground as shadowed in a 660 m scene (texel 0.44 m). Bias scales with the texel
size and is used together with normal offset.

**Depth distribution, not a ratio, separates acne from real shadow.** Acne gathers just
above the bias. In the measured, corrected case: occlusion under 1 m
**0%**, median depth **7.3 m** → these are real shadows.

---

## Silent failure catalog

| symptom | real cause |
|---|---|
| falloff curve does not match the game | `pow()` used, not the rational approximation |
| cone edge softens in the wrong place | lerp in angle; should be in cosine |
| cone fully open | angle written in degrees, should be radians |
| interior looks flat | hemisphere lerp; should be the `downMult` formula |
| masks too dark | `.color` read, should be `.color_srgb` |
| every surface matte | 0 fed because there is no spec map, should be 0.1 |
| fresnel control does nothing | fresnel read from the map, should come from the material |
| daytime blows out to white | ad-hoc rolloff instead of filmic |
| timecycle off by one hour | `name` read in `time.xml`, should be `hour` |
| wrong timecycle loaded | the 4-sample `data/time.xml` used |
| flat ground shadowed | shadow bias not normalized to the scene scale |
| projection texture missing in game | not shipped with a `.ytd` of the same name |
| light never on at any hour of the day | `time_flags.total = 0` |
| projection lies on its side | `Tangent` = *up*; Sollumz writes local X there |
| tilt/cone setting changes nothing in game | the light's transform was wiped together with the mesh reset |
| round window lands pointed, pointed window lands round | gobo squeezed into a square, aspect ratio lost |
| corners of the floor patch are pointed | empty corners of a square texture; no vignette |
| dark ellipse in the middle of the patch | `static_shadows` on, the window blocks its own beam |

---

## Data setup

Weather cycles live in the game archive and **are not embedded in the layer** — they are
generated from the user's own install:

```
powershell -File build_cycle.ps1
python assetdb.py cycle --list
```
