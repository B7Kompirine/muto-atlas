# Adding freemode clothing / moving a garment to a 98-bone ped / ped scaling

**When to read:** you are adding your own garment to `mp_m/f_freemode_01`; moving a freemode garment onto a local ped; the export comes out silently broken; changing ped height; making the ped taller in heels (§8).
**Source:** `notes/03` §2, §4-7 (Sollumz Discord videos, 2026-08) · **Measured:** video; the weight rules (4 bones / 1.0) match our measurement exactly
**Read first:** `branches/clothing/_branch.md` · trunk › `trunk/tool-pitfalls.md` §1

---

## 2. Weight painting — GTA's hard rules (`IbZ4xSCZt6I`)

**Exactly** the same as the measurements in atlas §7, confirmed from an independent source:

- **The weight sum per vertex** must be exactly `1.0`.
- **At most 4 bones per vertex.** Extra ones are **silently cut** on export.
- Blender equivalents (Weight Paint → Weights):
  - **Normalize All** (all groups, *lock active* off) → makes the sum 1.0
  - **Limit Total = 4** (all groups) → applies the 4-bone rule
  - **Smooth** (all groups, 1-2 times) → softens rough transitions

### Bone count facts (same as atlas §8)
- **`mp_m/f_freemode_01` = 128 bones**
- **Typical local/story ped = 98 bones**
- Difference: `MH_hair_scale` + front/back skirt rolls (`SM_L/R_Front/BackSkirtRoll`)
  + some face bones.

**Two ways to move a freemode garment onto a 98-bone ped:**
1. **Weight transfer (recommended)** — import the garment **WITHOUT an external skeleton**
   → the vertex groups come in empty → transfer weights from the target ped.
   The transfer only uses the bones the ped **actually has**.
2. **Manual deletion** — delete the missing bones (skirt rolls), then redistribute the
   remaining weight with **Normalize All** (`thigh_roll` goes up to 1.0 and the transition gets hard; fix it).

### Weight transfer procedure
1. Duplicate the target ped's **upper + lower** meshes → join them with `Ctrl+J`.
2. Edit Mode → **Merge by Distance** (unmerged vertices break the transfer),
   turn on sharp edges.
3. Select **the body first**, then the garment with `Shift` (body dark orange, garment light).
4. Weight Paint → Weights → **Transfer Weights**:
   - Vertex Mapping: **Nearest Vertex** (subjective, others are worth trying)
   - ⚠️ **Source Layers = `By Name`** (NOT Active Layer)
   - Destination = All Layers
5. Clean up empty vertex groups — the **Sushi Cleanups** add-on:
   *delete from active object → empty vertex groups*.
6. Common defect: **spine bones leak into the arm** → when the arm is raised, the underside of the arm sticks
   to the body. More frequent on loose-cut garments. Clean it by hand, then normalize again.

## 4. Freemode garment production 2025 (`uBBHJ4vG4fM`)

**The texture naming rule** holds for the whole branch → `branches/clothing/_branch.md`.

### Other steps
- Before starting, **`Ctrl+A` → Apply All Transforms**.
- The material must be **simple** (image nodes only), or build the Sollumz `ped` shader
  from scratch (the author's preference).
- **spec and bump are embedded, diffuse is NOT embedded** — so the texture can be swapped in game.
- LOD: Sollumz **LOD Tools → pick the reference mesh → Medium + Low → Generate LODs**,
  default decimation **0.6**. To do it by hand: duplicate → Decimate → apply →
  give the mesh a clear name → assign it to the original's Medium/Low slot.
- Move your own drawable model **under the imported vanilla drawable**,
  and delete the vanilla mesh.
- **Two UV maps are required**: `UVMap 0` = texture UV, **`UVMap 1` = blood mapping**
  (do not touch it).

## 5. Export pitfalls — silent breakers (`IbZ4xSCZt6I`, `Jm3Ps157z3s`)

- ⛔ **Export → Drawable → `Mesh Domain` = `Face Corner`.**
  The `Vertex` option is **only for MP freemode heads** (vertex order matters).
  With the wrong choice the export comes out silently broken. The author missed this in the first take
  and had to record the video again.
- **A non-streamed ped must have NO embedded texture** — they all go into the matching `.ytd`.
  If a `textures/` folder appeared in the export folder, something is still embedded somewhere.
  Correct output: only `<ped>.ydd.xml`.
- **`Exclude Skeleton` OFF for a component export** (needed for the head).
  **`Exclude Skeleton` ON for a ped prop export.**
- `Alt+P` → **Clear and Keep Transformation** to take the garment out of the hierarchy,
  then shift-drag it under the target `upper_00X`.

## 6. Ped vertex colours (`uVlBINnNTGA`)

Object Data Properties → **Color Attributes** (British spelling: **`Colour`**):

| name | domain | type | value | what it does |
|---|---|---|---|---|
| **`Colour 0`** | Face Corner | Byte Color | hex **`FF8000`** (orange) | **in-game lighting**. Without it the part is shaded strangely dark in sunlight. |
| **`Colour 1`** | Face Corner | Byte Color | hex **`000000`**, **Alpha = 0** | **wind + sweat effects**. With alpha > 0 the garment sways in the wind / shines needlessly. |

- Almost every ped `.ydd` has **two** of them.
- **Emissive garment**: `Colour 0` → pink (the video reads about `FF00BF`; verify the exact value
  by eye), `Colour 1` stays the same; make the material **`ped_emissive`** with Shader Tools;
  raise the brightness with the **emissive multiplier** (default 1) under `value parameters`.
- Some local peds come with a yellow-green palette; that is fine — set them all to
  `FF8000` if needed. The painting on the face is a subsurface-scattering-like lighting difference.
- ⚠️ In the 360 spin video (`ahPJhRZPiZQ`): **the vertex colour of emissive areas must be WHITE**,
  otherwise emissive does not work. That is why the emissive part is separated from the mesh with `Y` —
  so vertex colours can differ per part.

## 7. Ped scaling (`LfyCgqZMr3I`)

1. Put a **plane** at floor level → `Shift+S` → **Cursor to Selected**
   → set the pivot to **3D Cursor**.
2. Pose Mode → select everything **inside** `SKEL_ROOT` (pelvis etc.) → scale.
   **Copy** the scale value.
3. **The head skeleton is a separate armature** — do the same there and
   paste **the same scale value**.
4. **Apply the Armature modifier on every component and on EVERY LOD** (high/medium/low).
5. On both skeletons: Pose Mode → `A` → `Ctrl+A` → **Apply Pose as Rest Pose**.
6. Export: Select Hierarchy → **Selected Objects ON**, **Exclude Skeleton OFF**.
7. Take the original (unchanged) `.yft`; copy the **`<Skeleton>`** block from the `.ydd.xml`
   into the `.yft.xml`.
- ⚠️ **Known defect:** there is a side-to-side **sway** when running, because `SKEL_ROOT`
  itself is not scaled.
- ⚠️ **Does not work on animal peds with articulated skeletons** (consistent with the
  quadruped skeleton notes in atlas §10).


---

## 8. Height by shoes + hair scaling (the `.ymt` side)

The ped getting taller in heels comes **not** from the `.yed` but from the
`.ymt`. The details of the `.yed` side (`MP_HEELS.EXPR`, component order, jiggle) are not
in this release; the basic steps are below.

1. Copy `MP_HEELS.EXPR` from `AMBIENT.YED` → paste it as the FEET component
   → rename it **`FEET_000_U`** (**mind the order**).
2. `AP_M.XML` → **`CreatureMetadataName` = `mp_creaturemetadata`**.
   This is the value that turns on hair scaling **and** the height offset.
3. Open the `.ymt` with **YMTEditor** (grzybeek) → feet component → *View component
   properties* → the **`hash_07AE529D`** row has **5 numbers**;
   **only the rightmost** is the height offset. If the ped floats in the air, give a **negative** value.
- ⚠️ When adding a new feet component for height, **there is no need to change the `.yed`** —
  only the `.ymt` value.

**Measured:** NcProductions `.yed` Part 2 (`bxmVJfL8KcA`), `notes/07` §4, 2026-09.
