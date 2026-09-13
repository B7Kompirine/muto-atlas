# Decal — script (`AddDecal`), baked into the map (`decal.sps`), projection onto a surface in Blender; source packs

**When to read:** "graffiti on a wall / blood on the floor / a stain on the stairs"; which system — a runtime mark (`AddDecal`), a decal baked into the map (`decal.sps`), or projecting geometry onto a surface in Blender; the decal does not show / looks white / looks green; Void Tools; free texture packs and their licenses.
**Source:** `decal.md` §0-3, §7-8, §10, white/brightness · `trunk/flags.md` §8.5b-8.6 · the former `/look` command · the former decal texture source list (2026-08) · **Measured:** 194 decal types; 4096 rays on the ladder; A worked in game; 2,989-texture inventory
**Read first:** `_branch.md` · trunk › `trunk/tool-pitfalls.md` §1-2

---



Argument: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

below

Every number here is a measurement. The projection tool itself is not in this repository; this document
is the contract for that kind of tool, and the criteria stay here even if the tool changes.

---

## STEP 0 — WHICH SYSTEM? Choose before writing code

"Let's put a stain/graffiti/blood there" is **three separate jobs**, and none of them
can stand in for another:

| wanted | system |
|---|---|
| a runtime mark — blood, tire, bullet hole, leak, footprint | `AddDecal` (script) |
| **permanently baked** into the map — graffiti, logo, sign, road line | `decal.sps` shader + render bucket **2** |
| **projecting geometry** onto a model's surface (made in Blender) | projection decal (Blender add-on) |

If it is unclear, clarify with `AskUserQuestion`:
- Is the mark **permanent** (part of the map), or does it appear during play?
- Will **everyone see it at the same time**? → `AddDecal` is per client.
- Is the surface **flat**, curved, or a thin pipe/grating? → on the last one projection
  does not work; that is a painting job.

---

## 1. RUNTIME MARK — `AddDecal`

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" decal blood
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" decal <bullet|footprint|burn|oil|petrol>
```

A table of 194 types. **Do not guess** the type; pick it from the table.

## 2. DECAL BAKED INTO THE MAP — the shader side

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" shader decal
```

Render bucket **2**. `decal.sps` reads **the alpha of `Color 1`** as the blend
factor — if the vertex color is wrong, the decal either does not show at all or stays
half transparent.

## 3. PROJECTING GEOMETRY ONTO A SURFACE — three methods, three hard limits

| method | when | limit (measured) |
|---|---|---|
| ray grid | flat surface facing the rays | **can never hit a surface parallel to the rays** — on the ladder 2732 of 4096 rays were wasted, in an inside corner 1344 |
| box (triplanar) | a surface that needs wrapping | gives 39 normal bands on a cylinder (ray: 2), but the pattern **restarts at a corner** |
| single-axis clipping | a flat surface facing one direction | do **not pick the axis per face with `max()`** — if the surface normals are not aligned to the axis, the result comes out empty |

⛔ **`bmesh.ops.bisect_plane` does not clip open geometry, it DELETES FACES** — over six
calls the face count stayed at 637 while the area dropped 3.553 → 0.941 m².
Boolean INTERSECT is not reliable either (on the same wall one did not clip at all).
**The right way is Sutherland–Hodgman**: no solver, no failure mode.

Thin pipe / grating / complex curves → **none of them work**. There the path is
a surface copy + painting the alpha by hand (Surface Painter).

---

## IF THE DECAL DOES NOT SHOW — in order, all silent

1. Is the **NAME of the UV layer** the same as the material's — `"UVMap 0"`.
2. Was the target's **old UV layer** deleted (it comes along when geometry is copied).
3. **Is the `Color 1` alpha 1.0** — copied geometry inherits the target's;
   in the measured case it was 0.498 and the decal stayed half transparent.
4. **In the alpha map, row 0 is the BOTTOM of the image** — read upside down, the mask
   is applied upside down.
5. Is alpha culling too aggressive — if pixels that are not fully transparent are culled
   too, the pattern gets holes.

## BLENDER API PITFALLS — caught in this job

- ⛔ **`object.dimensions` DOES NOT INCLUDE ROTATION** (local bbox × scale). Rotating
  does not change it → "lay the longest axis down" logic silently does nothing.
  Use the world bbox.
- ⛔ **`select_set()` silently does nothing on a hidden object** — export
  says "successfully", the file comes out **0 bytes** (five of seven objects were written like this).
- `scene.ray_cast` uses the **viewport**; the view ray is cast from the real eye
  position, and the dot of an exactly perpendicular face is **0.000**.
- Entering Edit Mode **brings back the previous selection**.

## WHEN PRESENTING THE RESULT

- ⛔ **"The object was created, the numbers look reasonable" DOES NOT MEAN IT WORKS.** Every
  silent failure in this area had this pattern: hundreds of faces, reasonable area,
  no error, **nothing on screen.**
- ⛔ **A screenshot is not a measurement.** Before saying something is broken,
  **read** — the pixel, the file, the read-back.
- **Working at a single synthetic point is not enough** — try the fix on the
  user's real geometry, then say "done".


---

## DECAL — three separate systems, do not mix them (`/look`)

"Let's put blood/graffiti/a stain/a logo there" is one of three separate jobs, and none of them
can stand in for another:

| wanted | path |
|---|---|
| runtime mark (blood, tire, bullet, leak) | `AddDecal` → `assetdb.py decal <kind>` (table of 194 types) |
| **permanently baked** into the map (graffiti, logo, sign) | `decal.sps` shader + render bucket **2** → `assetdb.py shader decal` |
| **projecting geometry** onto a surface in Blender | below |

Three projection methods were measured, and all three have a hard limit:

- **A ray grid can NEVER hit a surface parallel to the rays** — on the ladder 2732 of
  4096 rays were wasted, in the room's inside corner 1344.
- **The box method** wraps (39 normal bands on a cylinder, 2 with rays), but the pattern
  restarts at a corner. On a thin pipe/grating **none of them work** — that is
  a painting job (Surface Painter).

If the decal does not show, check these **in order** (all silent):
is the UV layer name the same as the material's (`"UVMap 0"`) · was the target's old UV
layer deleted · is the `Color 1` alpha 1.0 (copied geometry brings the target's,
0.498 in the measured case) · in the alpha map **row 0 is the BOTTOM of the image**.

⛔ **`object.dimensions` DOES NOT INCLUDE ROTATION** (local bbox × scale) — building "lay the
longest axis down" logic on it silently does nothing.
⛔ **`select_set()` silently does nothing on a hidden object**: export says "successfully",
the file comes out **0 bytes** (five of seven objects were written like this).

The Blender tool is not in this repository. This document is the measured
contract for that kind of tool; if the tool changes, the document stays as the criterion.


---

## Decal — two separate systems (ytyp-ymap measurement)

| | **A · Runtime** | **B · Baked into the map** |
|---|---|---|
| How | the `AddDecal()` native | `.ydr` + ymap |
| Production | script, no Blender | Blender + Sollumz |
| Lifetime | removed by `timeout`, washes off | permanent |
| Cost | drawn on every client | near zero |
| When | event-based: blood, tire marks, leak | permanent: graffiti, logo, road line |

### A · Runtime decals

```lua
AddDecal(decalType, x,y,z, dirX,dirY,dirZ, sideX,sideY,sideZ,
         width, height, r,g,b, opacity, timeout, isLongRange, isDynamic, useComplexColn)
```

`dir` = the surface normal (`0,0,-1` for the floor), `side` = the decal's horizontal axis.
A negative `timeout` makes it permanent. The returned integer is used with `RemoveDecal` /
`IsDecalAlive` / `GetDecalWashLevel`.

**Ready helpers:** `AddPetrolDecal` (petrol — **flammable**) ·
`_AddOilDecal` · `StartPetrolTrailDecals` + `AddPetrolTrailDecalInfo` +
`EndPetrolTrailDecals` (trail behind a vehicle) · `ApplyPedDamageDecal` (wound on a ped)

**Bulk operations:** `RemoveDecalsInRange` · `FadeDecalsInRange` ·
`WashDecalsInRange` · `RemoveDecalsFromVehicle` / `FromObject` ·
`SetDisableDecalRenderingThisFrame`

**⭐ Dressing it in your own texture:** `PatchDecalDiffuseMap(decalType, txd, texture)`
— replaces the texture of an existing type; the way to make custom
blood/graffiti **without producing a new asset**. `UnpatchDecalDiffuseMap` reverts it.

### ⛔ DECAL TEXTURES ARE GREY MASKS — YOU PROVIDE THE COLOR

**Measured:** in `fxdecal_blood_pool2.dds` (256×256 DXT5) **all 800 sampled
color pairs are R=G=B**. The texture carries no color, only shape + alpha.

Symptom: *"the decals work but have no color"* — grey/white stains.

The color comes from **two separate places**, depending on which system you use:

| System | Where the color comes from |
|---|---|
| **A · `AddDecal`** | the `rCoef, gCoef, bCoef` parameters. `1,1,1` = neutral = **grey** |
| **B · model decal** | **vertex color** (`Color 1`). `decal.sps` has **no** color parameter |

Starting values (to be tuned): blood `0.35, 0.02, 0.02` · bloody trail
`0.30, 0.03, 0.03` · oil/petrol `0.10, 0.09, 0.06` · bullet mark `0.55` neutral grey.

⚠ The B side is **[NOT VERIFIED]**: because the `decal.sps` parameter list has no color
field, it was inferred that vertex color provides it; not confirmed in game.

### `decalType` table — 194 types

`data/decal_types.tsv` · query: `assetdb.py decal <kind>` or `--id <number>`

**Source: the game's own `common.rpf\data\effects\decals.dat`** (131 KB).
The enum in the FiveM docs **is incomplete**; this table is complete. ID range 1010–10031.

| Category | Types | Example ID |
|---|---:|---|
| VEHICLE BADGES | 32 | — |
| BANGS (bullet marks, referenced from `materialfx.dat`) | 18 | 4010 metal · 4020 concrete · 4050 wood |
| MUD / SCRAPES | 7 + 7 | — |
| BLOOD | 4 (+11 related) | **1010** splatter · 1015 directional · 1017 mist · **9001** pool |
| BURN SCORTCH MARKS | 4 | — |
| WATER / OIL / PETROL | 4+4+4 | — |
| *TRANSFER* (carrying blood/oil/petrol/mud/water) | 3 each | 2040 bloody footprint · 3100 bloody tire |
| FOOTPRINTS (mud/sand) | 2+2 | — |

⚠ **One ID carries several variants** and the engine **picks at random** — `1010`
has 3 variants. Stamping the same spot twice does not give the same image.

⚠ The `washable` and `underwater` columns set the behavior: with `washable=1`
rain/`WashDecalsInRange` removes it; with `underwater=1` it also forms under water.

## 8.6 B · Decal baked into the map — a stain/mark/text stuck to a surface

Source: "create basic decal" (Lamont Cranston, 61 s, no subtitles — watched frame
by frame) + the Sollumz shader table. Query: `assetdb.py shader decal`.

### Recipe (Blender 5.0 / Sollumz 2.8)

1. **`Add → Mesh → Plane`** — `Size 2m`, **`Generate UVs` ✓**, `Align: World`,
   location `0,0,0`. A decal is a flat quad; no other geometry is needed.
2. Rename it (`decal_example`).
3. **Sollumz → Drawables → `Convert to Drawable`** → hierarchy:
   `decal_example` (drawable) → `decal_example.model` → `Plane.001` (mesh).
4. **Shader Tools** → type **`decal`** into the search box → pick from the list →
   **`Create Shader Material`**.
5. Load the DDS into the material's `Texture Parameters → DiffuseSampler`,
   tick **`Embedded` ✓**, `Color Space: sRGB`.
6. **Do not touch the Render Bucket by hand — pick the right shader and Sollumz handles it.**
   Measured live (Blender 5.2 + Sollumz 2.8, material created and read):

   | Shader | Automatic bucket |
   |---|---|
   | `default.sps` | OPAQUE |
   | `decal.sps` · `decal_dirt` · `normal_decal` · `water_decal` | **DECAL** |
   | `cutout.sps` | CUTOUT |
   | `alpha.sps` · `glass.sps` · **`vehicle_decal.sps`** | ALPHA |

   `vehicle_decal → ALPHA` matches our vanilla measurement **exactly** (395/395
   usages bucket 1). Sollumz's per-shader defaults agree with what Rockstar
   actually ships.

   ⚠ **Correction:** the previous version of this document said "set the bucket to 2 by hand".
   **That was wrong.** The cause of `Opaque (0)` in the video is not a forgotten bucket —
   the author searched for `decal` but **left the `default` shader in place**
   (the status bar says "Added a **default.sps**", the material name is `default`).

7. ⛔ **THE REAL PITFALL: making a decal and staying on the `default` shader.** Then the bucket
   is `OPAQUE`, alpha does not work, the decal comes out as an opaque square — and
   **no error is given.**

   12,000 `.ydr` + 12,000 `.yft` were scanned; the **5,482
   usages** of decal shaders break down like this:

   | Bucket | Count | Share |
   |---|---:|---:|
   | **2 Decal** | **5,062** | **92.3%** |
   | 1 Alpha | 419 | 7.6% (almost all `vehicle_decal`) |
   | 0 Opaque | **1** | 0.0% |

   So in 5,482 usages Rockstar left Opaque **once**. Sollumz's
   default is `OPAQUE` (`ydr/properties.py:160`); if it is not changed the decal is drawn
   opaque, alpha does not work, and **no error is given either.**
   ⚠ Exception: **`vehicle_decal` uses bucket 1 (Alpha)** (395/395).

### Render Bucket — a field SEPARATE from the shader

`szio.gta5.drawables.RenderBucket`:

| Value | Name | Meaning |
|---:|---|---|
| 0 | Opaque | no alpha |
| 1 | Alpha | alpha but **no shadow** — usually glass |
| **2** | **Decal** | alpha decal, no shadow |
| 3 | Cutout | alpha **and shadow** — fence/cage |
| 4 | No Splash | only with `vehicle_nosplash` |
| 5 | No Water | only with `vehicle_nowater` |
| 6 | Water | water shaders |
| 7 | Displacement Alpha | drawn last; only with `glass_displacement` |

Query: `assetdb.py shader --buckets`

### Decal shaders (35 of them)

`assetdb.py shader decal` gives the full list. The most used ones and their
**required textures**:

| Shader | Texture | When |
|---|---|---|
| `decal` | `DiffuseSampler` | the simplest; only color + alpha |
| `decal_dirt` | `DiffuseSampler` | dirt/dust; has a `DirtDecalMask` parameter |
| `normal_decal` | + `BumpSampler` | if you want relief on the surface |
| `normal_spec_decal` | + `BumpSampler`, `SpecSampler` | if gloss is needed too |
| `decal_glue` | `DiffuseSampler` | glued on, like a poster/label |
| `decal_emissive_only` | — | glowing text/sign |
| `decal_tnt` | + `TintPaletteSampler` | tinted with a color palette |
| `vehicle_decal` | + `DamageSampler`, `SpecSampler` | on vehicles |
| `mirror_decal` · `reflect_decal` · `spec_reflect_decal` | | reflective |

`decal` parameters: `useTessellation=0` · `wetnessMultiplier=1` ·
`specularIntensityMult=0` · `specularFalloffMult=100` · `specularFresnel=0.97`

### Texture

Vanilla decal textures are in texture dictionaries such as `decals_stains`:
`decal_house_stain_03_a.dds`, `conc_stain1.dds`, `dirt_grime_01_*.dds`,
`dc_parking_splats_01*.dds`. **All are DDS with an alpha channel** — the decal's edge
fades out through alpha, not through geometry.

### Known pitfalls

- **A decal is not sunk into the floor; it is placed ON TOP.** To avoid z-fighting, lift it
  ~1-2 cm (video #7 uses the same method for fur grass: shift by `0.01`).
- A wrong shader is **a silent failure**: a decal made with the `default` shader comes out
  as an opaque square, alpha does not work. There is no error message.
- If the texture is not **embedded**, a separate `.ytd` is needed; for a single decal
  embedding is simpler.


---

## 0. THE MOST EXPENSIVE LESSON OF THIS SESSION

I handed over a decal tool as "fixed" for **six rounds**, and in all six
it did not work for the user. The cause was not a single bug; **each round had
a different silent failure**, and after fixing the previous one I said "ready"
without seeing the one that surfaced.

⛔ **RULE: before handing over a fix, test it in the user's REAL situation.**
Working at a single synthetic point is not enough. In this session I said
"it worked on a flat wall" and handed it over; the user tried it on a cylinder/ladder
and it broke — again and again.

⛔ **"The object was created, the numbers look reasonable" DOES NOT MEAN IT WORKS.** Every
silent failure in this session had this pattern: hundreds of faces, reasonable area,
no error, **nothing on screen.**

---

## 1. PROJECTION DECAL — THREE METHODS, THREE HARD LIMITS

There are three ways to put a decal on a surface. None of them can stand in for another.

| Method | How | Hard limit |
|---|---|---|
| **Ray grid** | Builds an even grid and casts rays at the surface | **Can never hit a surface parallel to the rays** |
| **Copy geometry** | Copies the target's triangles | UV comes from a single axis → the texture **stretches** on a perpendicular face |
| **Box (triplanar)** | Copies, but gives the UV along each face's own axis | The pattern **restarts** at a corner (seam) |

### The limit of the ray method, measured

A 64×64 grid in the room's inside corner: **1344 of 4096 cells found no
surface.** On the ladder **2732 of 4096**. The cause is geometric: the ladder
rungs are ~2 cm pipes with air between them; the rays pass tangentially.
**No angle/threshold setting fixes this.**

Measurement on a cylinder: ray method 288 faces / **2 distinct normal bands** (stays
flat), box method 89 faces / **39 normal bands** (wraps), area 3.5 times larger.

### Decision table

- Flat/wide surface (wall, lid, table top) → **ray** (continuous, cheap)
- Cylinder, corner, surface of revolution → **box**
- Thin pipe/grating (ladder, glazing bars) → **none**; Surface Painter
  or bake into the texture

---

## 2. SILENT FAILURES FOUND IN THE DECAL TOOL

All were found by measurement; none produced an error message.

### 2a. The NAME of the UV layer must match the material
The GTA/Sollumz material looks for **`"UVMap 0"`**. Write `"UVMap"` and the link is not
made, the UV falls to `(0,0)`, and the atlas's transparent corner is sampled.
**Measured:** a decal with 505 faces, correctly placed, 97% of it on filled alpha,
came out **completely empty** when rendered on its own.

### 2b. When geometry is copied, the target's UV comes along
When a second layer is opened with `.new()`, the material **still reads the first** — i.e.
the wall's tile UV. **Measured:** UV range `u 0.078..4.628`,
`v -1.750..18.440`; the atlas cell is `0.75..1.00 / 0.50..0.75`. The texture
repeated many times → "it places it piece by piece in every cell".
→ **Delete the existing UV layers before** adding the new one.

### 2c. The vertex color is inherited from the target too
The material multiplies alpha as `texture_alpha × Color1_alpha`. Copied
geometry brings the target's `Color 1`. **Measured:** a decal falling on
`v_2_bds_over_shadow` had Color1 alpha **0.498** → the decal is half transparent.
→ **Always** write `Color 1` / `Color 2` as (1,1,1,1); "create if missing" is not enough.

### 2d. In the alpha map, row 0 is the BOTTOM of the image
`bpy.types.Image.pixels` is laid out bottom to top: `v=0 → row 0`.
Writing `1-v` flips the culling vertically → **triangles are generated in the cells where the
texture is empty, and the filled ones are thrown away.** After the fix,
**97% of the generated cells have alpha > 0.5** (before: 1%).

### 2e. "The dominant normal around the cursor" is the WRONG CRITERION
On a table with the cursor on top, the tabletop's **underside** faces covered more area within a
0.8 m sphere, so the normal `(0,0,-1)` was chosen; the decal stuck **under the table**
(decal z −8.86..−8.71, table top −8.67). The user saw nothing.
→ The right criterion is **the view**: a ray from the camera to the cursor, the normal of the first face hit.
At the same point: old `(0,0,-1)`, new `(0.03,0.01,1.0)`.

### 2f. The view ray is cast from the REAL eye position
Starting it 30 m behind the cursor puts it **outside** the building in an enclosed space;
the ray hits the wall's **outer** face, the normal flips, and the grid hits
nothing → *"No surface found"*. That is exactly what happened inside the elevator.

### 2g. The dot of an exactly perpendicular face is 0.000
Writing back-face culling as `dot <= 0` counts **corner turn faces** as back faces and
culls them. In the room's inside corner 48 cells dropped because of this, leaving a grey strip.
→ The threshold should be a small negative such as `-0.05`.

### 2h. ⛔ `bmesh.ops.bisect_plane` DOES NOT CLIP THIS GEOMETRY, IT DELETES FACES
**Measurement (the clearest evidence):** over six bisect calls **the face count stayed
at 637** while the area dropped to `3.553 → 2.552 → 1.401 → 0.941 m²`. So
large faces were not cut with the inside part kept; **they went entirely.**
Result: the cabinet doors stayed, the wide panel between them vanished, and the decal
was **cut dead straight** at the door edge.

### 2i. Boolean INTERSECT is UNRELIABLE on open/thin meshes
Four decals on the same wall: one **was not clipped at all** (3.706 m², box 2.56),
one stayed almost **empty** (0.025 m²).

### 2j. THE FIX: Sutherland–Hodgman
Clip every triangle against the six half-spaces in turn, and compute the intersection points exactly.
**No solver → no failure mode.** Five tests (flat wall ×3, cylinder,
corner): **none exceeded the box area**, and in all of them the UV is inside the atlas cell.

### 2k. In the box method do NOT pick the axis PER FACE with `max()`
The wall is made of 0.3 m² panels whose normals differ slightly from each other;
`max()` picks **different axes** on neighboring panels, and each panel gets independent UV.
**Measured:** of the 10 faces around the cursor, 4 picked `n` and 6 picked `u`.
→ The main axis is **the decal's own direction**; a face switches to a side axis only if it deviates
**more than 70°**.

### 2l. The "selected object" criterion burns the user
A wall is not one object: the cabinet bank, shell, skirting board, frame and
pipes are **separate objects**. **Measured:** in the same box `bodydrawers` alone is
**0.656 m²**, all visible objects **6.318 m²** (10 times as much).
→ The default must be **"everything visible"**.

### 2m. But "everything visible" INCLUDES YOUR OWN DECOR TOO
Unfiltered, a 2×2 m box collected **20.5 m²** of surface — because
`my_mlo_veins`, earlier decals and collision boxes are "visible meshes" too.
That amounts to throwing decals on top of decals. With its own collections filtered out: **3.88 m²**
(box 4.00) — a single consistent layer.

### 2n. Not every face inside the box is VISIBLE (occlusion)
Behind the cabinet doors there is a flat back panel; with a depth of 0.40 both of them
fall inside the box. The copy method takes both, and the big flat back
panel comes forward and makes the decal look like **a board floating in the air**.
→ Cast a ray from the face center to the projector; if another face is in front of it, **drop it**.
(The ray method does not have this problem — it takes the first hit anyway.)

### 2o. The box method needs alpha culling too
The ray method had it, the box did not. **Measured:** 487 faces generated on a flat wall,
and by area only **1%** of them fell on filled texture. The fill ratio of the atlas
cells ranges from **6.8% to 32%**.

---

## 3. BLENDER API PITFALLS (caught in this session)

### 3a. ⛔ `object.dimensions` DOES NOT INCLUDE ROTATION
It gives local bbox × scale. Rotating the object **does not change** `dimensions`.
Building "bring the longest axis to X" logic on it silently does
nothing. → Use the world bbox: `matrix_world @ v for v in bound_box`.

### 3b. ⛔ `select_set()` SILENTLY DOES NOTHING ON A HIDDEN OBJECT
Export says "File exported successfully", the file comes out **0 bytes**.
**Measured:** 5 of 7 objects were written empty like this. → Before export `hide_set(False)`,
then **check the file size**.

### 3c. `scene.ray_cast` uses the VIEWPORT
An object visible in render but hidden in the viewport is **skipped** by the ray test.
That is why I found the wrong object while looking for the magenta one.

### 3d. Entering Edit Mode brings back the PREVIOUS SELECTION
After `bpy.ops.object.mode_set(mode='EDIT')` the old face selection comes back to life.
That is why Void Decal Tool produced **4089 decals**. → In Edit Mode first
`for f in bm.faces: f.select_set(False)`.

### 3e. Blender 5.x compositor
- `scene.node_tree` and `scene.use_nodes` **were removed** → `scene.compositing_node_group`
  (an independent `CompositorNodeTree` datablock; you create it and you delete it)
- The `CompositorNodeComposite` node **was deleted** → replaced by the group's `NodeGroupOutput`
  (+ an Image socket has to be added to the tree's interface)
- Node settings moved from RNA **to input sockets**:
  `Blur.filter_type/size_x/size_y` → `Type` (menu) + `Size` (2D vector),
  `Denoise.use_hdr` → `HDR` (bool socket)

---

## 7. PURCHASED MODEL PACKS

- **The `.mtl` is often not put in the zip.** None of the four packs had it → no OBJ has
  material assignments, and textures are matched by hand.
- **Scale is inconsistent even INSIDE a pack.** Measured: the same 675-vertex part is
  **1.07 m** on one body and **0.15 m** on another. Scaling with a single factor is wrong.
- **One `.obj` = one scene dump.** A single file can hold dozens of corpses
  (one had 196 connected components).
- **⛔ DEBRIS CHAINS THE CLUSTERING.** Of the 608 components of `model_12`
  only **4** are real parts, the rest are flesh crumbs; when all of them went into the clustering
  the crumbs bridged the bodies and **all 608 components fell into a single
  cluster** — nothing got separated, and no error was given.
  → First cluster only the large parts, then assign the crumbs to the nearest cluster.
- **A part without UVs cannot be textured.** In one pack 4 models came out without UVs.

---

## 8. VOID TOOLS (seto3d) — LESSONS

Install: extension zip, `seto.*` operator namespace, `Void Tools` N-panel tab.
Security scan: 155 files / 36,930 lines, no `eval`/`exec`/`subprocess`;
network access only for its own GitHub version check.

### Architecture lesson — the most valuable one
It **removed** the hard problem **instead of solving it**:
- *Decal Tool* → builds a basis from the surface normal+tangent and **a single quad**. No projection,
  no copying → it never breaks (but it is flat).
- *Surface Painter* → makes a **copy** of the surface and has its alpha **painted by hand**.
  The projection problem never comes up → works on a cylinder and on a ladder.
- *Edge Dirt / Wear / AO* → a strip from the edge.

### Transferable techniques
- **`decal.sps` reads the ALPHA of `Color 1` as the blend factor** (Sollumz's
  own node link). Painting alpha = painting visibility.
- **The normal goes through the inverse-transpose matrix, the tangent through the plain linear part.**
  Mix them up and there is no visible difference at uniform scale; at non-uniform scale
  every decal silently tilts off the surface.
- **It builds its own projection UV and does not inherit the wall's** — the wall's
  unwrap can consist of islands overlapping in 0-1, and the decal is then drawn once
  per island. (The correctly built form of our §2b bug.)
- **Non-destructive editing:** an unmodified copy of the UV + strokes at full strength are kept
  separately, so the sliders do not lose data.
- **Only data GTA reads goes to export:** `Color 1` + `UVMap 0`.

### Vertex Color Bake is the WRONG TOOL for a room shell
The resolution of vertex color **is the mesh's vertex density**. On a low-poly room
shell the AO comes out blotchy. It is right for dense-mesh **props**.
It is also **the only tool that WRITES TO the mesh**; the vanilla `Color 1` can be filled
(measured: `bsnt_shell` B channel 1.000) and it overwrites it.
⛔ The `.npy` backup **was useless** in this session; the recovery came from re-importing the
source `.ydr` and copying `Color 1`. → Before using this tool,
**make a dated copy of the `.blend`**.

### Shadow Map Baker
The GTA interiors' own technique: bake the light into a texture and put it back as a `decal_dirt`
decal. Resolution is independent of vertices → **the right tool** for a room.
Measured: AO 2048²/128 samples, 2.4 s. Room mean brightness
`62.98 → 59.24` (while post-process was broken), after the patch **57.97** (7.96%).

---

## 10. VERIFICATION HABITS (the ones that proved themselves in this session)

- **Read back after every write.** After the ytyp was compiled it was read back and
  the `timecycleName` hash was compared with `joaat()` — it matched.
- **Compare md5 after deployment.** "The command gave no error" is not proof of
  deployment.
- **A screenshot is not a measurement** — but the reverse is true too: **a number alone
  is not enough either.** In this session the "UV fully inside the cell" measurement was right
  and the decal still did not show (the layer name was wrong). Both are needed.
- **When the user says "it did not work", MEASURE first; do not get defensive.** Every
  "it did not work" in this session matched a real bug.

## ⛔ "The decal looks white" = the texture has no ALPHA, the name is not the problem

Measured (`my_floor_blood.ydr`): **8** of 13 blood decals were looking at a **16×16** texture
whose alpha was **255** everywhere. No alpha means no cutout →
the engine **draws the whole quad opaque**. Light rectangles appear on the floor,
and this reads as "the decals are white".

**The source files were broken, and no tool said so.** The header of `cd_blood_01..09_dec.dds`
says `512×512 DXT5 mip=10`; that size needs **349,552 bytes** of data,
and the files hold **174,660–259,884** bytes. They fit no valid (width, height,
mip) triple. This is how it broke the chain:

| layer | what it did |
|---|---|
| Blender | read the header, `img.size` showed **512×512**, `packed=True` |
| Sollumz | could not decode the pixels, wrote a **16×16 A8B8G8R8 placeholder** |
| export | **"0 warnings"** |
| texture gate (`DOKU_KAPISI`) | **PASSED** — the name resolved, the problem was in the content |
| CodeWalker | `GetTexture()` reads the header and returns 512×512; **`GetPixels()` blows up** |

⛔ **"The texture resolves" and "the texture is USABLE" are not the same thing.** The first is
checked by the texture gate `DOKU_KAPISI`, the second by the alpha gate `ALFA_KAPISI`. A resolving name
does not show that the content is sound — the same as §2: the tool not showing something does not
mean it is absent, and the reverse holds too.

**The criterion is NOT missing alpha but "no alpha + small + NOT FLAT".** In vanilla
`mh_v_solidwhite_d`, `mh_v_solidblack_d`, `v_glass_d`, `gz_v_white256`
really are 4×4 **flat fills** with no alpha; that is normal, the shader uses them as flat
color sources. A gate that looks only at missing alpha flags these four
by mistake and blocks every deployment (measured). What is broken is a real image **whose pixels
vary but which has lost its alpha**.

Gate: an alpha check step that runs before deployment (its script is not in the repository). Verified with
a negative test; on the 84 alpha textures of 228 models, false alarms: **0**.

**Hypotheses ruled out (by measurement):** vertex color channel order — vanilla
itself also writes byte0 as **0**, and on four models our values matched vanilla;
the missing DXT1 alpha of `v_2_shadowmap1/2/3` and `v_2_bds_over_decal` —
**identical** to the vanilla originals, not a regression.

## ⛔ Decal brightness is not ABSOLUTE; it is measured RELATIVE to the floor

On a map with a darkened floor, a decal authored at normal brightness
reads as a "white stain". The defect is not in the decal but **in the ratio**.

**The criterion is derived from vanilla.** Vanilla `decal_dirt` overlay
`mh_v_cor_flooroverlay_a` = **75**, the vanilla floor under it
`mh_v_floortiles02_d` = **175** → ratio **0.43**.

Morgue measurement: floor 55–101 (mean ~78) → decal target **~34**. Values found:
`my_wall_atlas_0` **109.7**, `_1` **94.8** — *brighter* than the floor. Dirt
should darken the floor, not lighten it. The factor comes from measurement (0.311 /
0.364); alpha **is not touched** (the shape is there).

### Two separate patterns, both give the same symptom

**1. Baking a mask texture into the map.** `fxdecal_blood_pool2` is pure **grey**
(R=G=B=175): the shape is in alpha, the RGB is only a mask. In vanilla the *script*
decal system (`AddDecal`) uses it and **colors it**. Baked into the map with `decal_dirt`,
it draws a raw white pool. The criterion is simple: **if R=G=B, that texture is a mask,
not a color** — color it before baking it in. The correct blood
textures in the same model were R≈38 G≈10 B≈10; the target was taken from there.

**2. Giving an alpha-carrying atlas to `decal_dirt`.** Vanilla `decal_dirt`
textures are **all** DXT1, greyscale, alpha 255, **0% transparent**
(`mh_v_cor_flooroverlay_a` · `mh_v_shadowsquare_a` · `mh_v_cor_numbers_a`).
The mask is in RGB, not in alpha. Our atlas was DXT5 + 70-90% transparent; the shape
still comes through, but because RGB is drawn directly the brightness becomes critical.

### Hypotheses ruled out (all by measurement)

| hypothesis | measurement | result |
|---|---|---|
| texture does not resolve | `DOKU_KAPISI`: 228 files, **0 missing** | ruled out |
| wrong shader | hash/bucket/param **identical to vanilla** (3645727493, bucket 2) | ruled out |
| vertex color channel wrongly zeroed | vanilla itself also writes byte0 as **0**, matched on 4 models | ruled out |
| shadowmap/over_decal alpha dropped | **identical** to the vanilla originals, DXT1/alpha 255 | ruled out |
| atlas is white | **0 pixels** above 205 among the visible pixels, mean 51 | ruled out |

⛔ **"The mean RGB is dark" is not evidence.** Because 70% of the atlas is transparent,
the overall mean came out at 43; the mean of **the region with filled alpha** was
109.7. The right question is not "is the texture dark" but **"is the drawn area dark"**.

## Do not touch the NORMAL MAP when darkening an overlay

In the decal bucket scan `mh_v_cor_normaldetails01_n` comes out near the top with **169.6**
brightness — but `_n` is a **normal map**; a flat normal is already
(128,128,255), so it has to be bright. Darkening it breaks the surface
normals. Before darkening blindly from a brightness list: **look at the texture's ROLE
first** (`_n` normal · `_s` spec · `_h` height · `_d`/`_a` albedo/alpha).

Left untouched in the same scan, with reasons: `gz_v_white256` (4×4 flat color
source), `mh_v_scresbolts01` (prop bolt, not floor),
`prop_ng_fruit_logo` (monitor logo). Only the large overlays lying on the floor were darkened:
`gz_v_co_shadowmap1/2/3` + `shadhandle`, with the same vanilla
ratio (`78/175 = 0.446`), **keeping the format** (a DXT1 source stays DXT1).


---

## Free decal texture sources and their licenses (2026-08-31)


All of them are **free and open for commercial use**. The files here are **raw PNG/JPG**;
before they go into FiveM they have to be compiled into a `.ytd` dictionary (see the bottom).

| Folder | Content | Count | Format | Source | License |
|---|---|---:|---|---|---|
| `blood/png` | blood splatter, drop, pool, smear | 132 | PNG **RGBA** — median 2764 px, max 4984 | Resource Boy — Blood Textures | RB license: personal + commercial use allowed, no attribution needed |
| `dirt/drip_png` | run / drip / leak marks | 106 | PNG **RGBA** — median 1493 px | Resource Boy — Drip Textures | same |
| `dirt/grunge_jpg` | dirt, wear, deep cracks | 250 | **JPG, NO alpha** — median 4000 px | Resource Boy — Grunge Textures | same |
| `damage/rust_jpg` | rust, corrosion, metal wear | 50 | **JPG, NO alpha** — median 6425 px | Resource Boy — Rust Textures | same |
| `broken/glass_jpg` | broken glass / cracked shop window | 251 | **JPG, NO alpha** — median 5376 px | Resource Boy — Broken Glass | same |
| `acg-leaking/png` | wall leak / water-dirt run | 39 assets | PNG 1K | ambientCG "Leaking" | **CC0** — completely free |

### Wave 2 — graffiti + apocalyptic (all Resource Boy, same license)

| Folder | Content | Count | Alpha | Median edge |
|---|---|---:|:--:|---:|
| `graffiti/spray` | spray paint marks, tags | 200 | ✅ | 4836 px |
| `graffiti/scribble` | scribbles / handwriting / scratched text | 501 | ✅ | 3889 px |
| `graffiti/brush` | brush strokes, paint smears | 100 | ✅ | 4980 px |
| `graffiti/wall` | 8K graffiti walls (full cover) | 300 | ⛔ JPG | 7680 px |
| `apoc/spider_web` | spider webs — abandoned places | 400 | 200 of them ✅ | 5001 px |
| `apoc/hand_print` | hand / finger prints (for a bloody hand print) | 115 | ✅ | 1049 px |
| `apoc/torn_paper` | torn poster / paper | 106 | ✅ | 4779 px |
| `apoc/splash` | general splashes | 104 | ✅ | 3934 px |
| `apoc/stain` | coffee/liquid stains | 100 | ✅ | 3057 px |
| `apoc/ink` | ink runs | 100 | ✅ | 4097 px |
| `apoc/footprint` | footprints (for a bloody trail) | 60 | ✅ | 4867 px |
| `apoc/barbed_wire` | barbed wire | 60 | ✅ | 7680 px |

**Grand total: 2989 textures — 1884 with alpha (ready for decals), 1105 JPG without alpha.**
Numeric inventory: `inventory.json`. The raw `.zip`s are still in the folders —
no longer needed since they were extracted; deleting them frees ~9 GB.

### Found but not downloaded (you need to download them by hand)

- **3DTexel** — 280+ CC0 decals, graffiti included, with alpha. https://3dtexel.com/decals/
  The price is €0, but it requires going through WooCommerce **checkout** (form + order),
  so it could not be downloaded automatically. The most cleanly licensed graffiti source; use this one for an asset you will sell.
- **Sketchfab — karlwirbelwind "[CC0] Decal – Graffiti Textures"** — Albedo + Opacity
  PNG, 2K/4K. The download requires a Sketchfab account.
- ambientCG has **no** graffiti/dirt/crack **decals** (measured: `q=graffiti` → 0 results;
  the decal catalog is only Leaking / RoadLines / ManholeCover). The `dirt` results are
  tileable ground materials, not decals.

### The ambientCG series splits in two (measured)

- **Leaking001–011 (15 items):** `_Color.png` **RGB** + a separate `_Opacity.png` →
  a ready decal; take the alpha from the opacity file.
- **Leaking012–019 (24 items):** `_Color.png` is **grayscale**, there is **no** opacity file
  → these are not color but **masks**; use them either as a multiplier (for dirtying) or directly
  as the alpha channel.

## License warning (important)

**The Resource Boy packs are NOT CC0.** License text (`License.txt`, inside the packs):

- ✅ You may use them in as many personal and commercial projects as you like, no attribution needed.
- ⛔ **You may not redistribute, sell or sublicense the files on their own** —
  distributing them "on their own or as an add-on separate from your work" is forbidden.

In practice: **using them embedded in a `.ytd` on a server is fine**
(part of the end product). But **selling these textures on Tebex as a "decal pack" or
sharing them as raw PNGs violates the license.** If they will go into an asset for sale,
use the `acg-leaking` (CC0) side, or make your own texture.

## Before putting them into FiveM

1. **Alpha is required.** Grunge / Rust / Broken glass are **JPG** and have no alpha — used as
   a decal they draw an **opaque rectangle**. They were made for overlaying in Photoshop with
   "screen/multiply". To turn them into decals, a luminance → alpha mask
   has to be generated (in broken glass brightness = glass crack, dark = empty; dirt/rust the reverse).
   The blood and drip PNGs are already RGBA, no conversion needed.
2. **Power-of-2 resolution.** Sizes like 421×1402 get scaled in the engine; resize to
   512/1024/2048.
3. Compile into a `.ytd` as **DXT5** (with alpha) / DXT1 (without alpha) + a mip chain.
4. Write the `.ytd` name into the archetype's `textureDictionary` field — if it stays empty the engine
   looks for the texture in the model's own dictionary, does not find it, and **draws it untextured without an error**.

## Source links

- Resource Boy — Blood: https://resourceboy.com/textures/blood-textures/
- Resource Boy — Drip: https://resourceboy.com/textures/drip-textures/
- Resource Boy — Rust: https://resourceboy.com/textures/rust-textures/
- Resource Boy — Grunge: https://resourceboy.com/textures/grunge-textures/
- Resource Boy — Broken Glass: https://resourceboy.com/textures/broken-glass-textures/
- ambientCG (CC0): https://ambientcg.com/list?type=Decal
