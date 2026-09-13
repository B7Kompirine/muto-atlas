# Replace a vanilla part with my own model (road, prop, structure)

**When to read:** hiding a road slice, prop or structure part on the map and putting your own model in its place; recovering its textures; custom split normals; "clean up close, still there from afar", Z-fighting, white surfaces, map collision gone.
**Source:** former vanilla part replacement reference (2.5.0, in full, 2026-08) · a road destruction job (2026-09-01) · **Measured:** hw1_27 crane + fwy_01/dt1_rd1 freeway; LOD chain and `hei_` twins verified with entities.db
**Read first:** `branches/map/_branch.md` · trunk › `trunk/flags.md`, `trunk/tool-pitfalls.md`

---


**Replacing** a road slice, a prop or a structure part **with your own
model** is two separate jobs, and both are full of silent failures:

> ⭐ **Community confirmation (`trunk/tool-pitfalls.md` §7 / Sollumz Discord):** do NOT DELETE an object
> inside a `.ydd` dictionary, move it under the world. Deleting **also breaks the properties of the other
> linked objects** in the dictionary and the texture of that area starts to look
> blurry/low quality. Same rule as §1 below, from an independent source.
> Also: changing a single `.ydd` **does not need a ytyp/ymap.**

1. make the vanilla one **invisible** (without deleting — §1)
2. **build your own model from vanilla's own data** (§3) and
   **link its textures back** (§4)

Every number here was measured on the hw1_27 crane + fwy_01/dt1_rd1 freeway job.

---

## 1. Hiding the vanilla entity

### Do not delete, MOVE IT DOWN

If an entity with a child LOD is deleted, the indices in the array shift and the
`parentIndex` values of other ymaps silently point at the wrong entity.
The right way is `position.z -= 600`. Indices and counts are kept, and it can be undone.

### ⛔ DO NOT TOUCH THE EXTENTS

After moving the entity 600 m down, do not enlarge
`entitiesExtentsMin` / `streamingExtentsMin` because "it is outside the extent".
**Measured: deepening a ymap's streaming volume crashes that area's streaming
and physics grid — collision disappeared across the whole map.**

| file | original ent/str z | what I wrote | result |
|---|---|---|---|
| hw1_27_strm_0 | 31.0 / −111.1 | −650 / −650 | collision gone map-wide |
| dt1_rd1_strm_2 | 28.3 / −111.4 | −650 / −650 | same |

Once the entity is **outside** the extent it does not stream at all; that alone hides it.
Touching the extent is not needed, it is harmful.

### The WHOLE LOD CHAIN must be patched

A single visual object sits on the map in **three separate layers**:

```
X_strm_N.ymap   HD          (near)
X.ymap          LOD + SLOD1 (mid)
X_lod.ymap      SLOD2       (far, welds several blocks into one model)
```

The `parent` field gives the chain: `hw1_27_strm_0 → hw1_27 → hw1_lod`.
Hide only the HD and it is clean up close, a **ghost from afar**.

**SLOD2 usually cannot be hidden**: the SLOD2 named `hw1_lod_22_23_26_27`
has **15 children**; hiding it also takes away the distant view of 15 other structures.
The fix is not a ymap but **model surgery** (cutting the relevant part out of that drawable).

### ⛔ DO NOT FORGET THE `hei_` TWINS — this cost a round

With the mpheist DLC active, most ymaps of the map have a copy with the `hei_`
prefix, and **that is what actually loads**. Patching the base version and skipping
the `hei_` one gives the "clean up close, still there from afar" symptom.

```
hw1_27_strm_0      +  hei_hw1_27_strm_0        (HD)
hw1_27             +  hei_hw1_27               (LOD/SLOD1)
fwy_01             +  hei_fwy_01
dt1_rd1            +  hei_dt1_rd1
```

Look for both on every patch: `extract_asset.ps1 -Pattern 'hei_X*.ymap'`.

### Count EVERYTHING in the footprint first

Instead of guessing which entities to look for, query the database — list every
entity inside a footprint together with its ymap (`data/entities.tsv.gz`):

```python
# convert (x,y) -> (s,u) local frame, filter together with the z band
if -52<=s<=3 and -26<=u<=24 and 36<=z<=46: found.append(...)
```

Without this scan **`fwy_01_rd_09_ov`** was missed and Z-fighting was chased
for two rounds (§5).

---

## 2. Deciding what must be hidden: overlay and decal

A road surface is not a single model. There are at least three layers:

| suffix | what | if skipped |
|---|---|---|
| `X_rd_NN` | the actual road surface | the road disappears |
| `X_ovly_NN` | road overlay | — |
| `X_rd_NN_ov` | **decal** (shader name exactly `decal`) | stays **in the same plane** as your surface → Z-fighting |

`fwy_01_rd_09_ov` measurement: **3,417 vertices** in the footprint of the collapsing slice,
2,128 of them at z>40, median z **42.47** — the top faces of our plates are at
41.6–42.6. So exactly the same plane.

**Gate:** for every vanilla entity in the footprint where you place your own model, read the geometry
and ask "does its surface overlap mine" — a triangle pattern on screen is a sure sign of
Z-fighting but does not tell you the cause.

---

## 3. Cutting your own model from vanilla

### The cut must be complementary

Inside the footprint + outside = the whole original. A cut by face centre guarantees this
mathematically and is verified by measurement:

```
source total 14,956 faces = outside 13,058 + inside 1,898
```

No gap, no overlap. Cutting twice by two different criteria
(face centre in one place, `bisect_plane` in another) breaks complementarity.

### ⛔ DO NOT GUESS THE MATERIAL INDEX

A cut/join step can reset material indices
(if you see `distinct indices = 1`, that is exactly what happened). Re-deriving the lost assignment
"from the nearest vanilla polygon" **does not work**: the measured median
error was 0.7 m and the result is visibly broken (a barrier atlas was drawn instead of asphalt).

The right way: do not derive the assignment, **cut again from the original**. Since the faces are vanilla's
own, material and UV are right by definition.

Check: after the cut the polygon counts must match the original exactly
(like 9235 / 316 / 2636 / 871) and the `distinct indices` count must be close
to the slot count.

### Blender pitfalls (all happened, all silent)

- **`bpy.ops.object.transform_apply` may do nothing** → the mesh shifted 124 m,
  no error. Do not trust the operator, bake the transform into the data:
  `d.data.transform(d.matrix_world)` + `d.matrix_world = Identity`.
- **A manual bmesh join drops UV and color layers.** `bm.faces.new()`
  does not carry loop data. Use `mesh.transform()` + `bpy.ops.object.join()`;
  join merges layers by name.
- **DELETING a vertex group also deletes the weights.** If you clear the groups after
  assigning the mesh, the weight data is gone and export says "no vertex is
  weighted". Assign the mesh, **do not delete** the groups.

---

## 4. Texture recovery — a vanilla model's textures are NOT in the model

### Measurement

```
dt1_rd1_r1_06        shader=21  embedded tex=0   wanted tex=61
fwy_01_rd_01         shader=22  embedded tex=0   wanted tex=51
prop_towercrane_02a  shader= 9  embedded tex=0   wanted tex=15
```

**None of the seven source models has an embedded texture.** All of them use an external
dictionary. The archetype's `textureDictionary` field is the first link, the rest is
**the parent chain**.

### Following the chain

1. `assetdb.py show <model>` → the `textureDict` hash.
2. Resolve the hash to a name (jenkins). If that fails, scan all `.ytd` names in the game.
3. `gtxd.meta` gives the parents (`GlobalRoads`, `DowntownRD`, `CityEastRD`…).
4. The shared parent dictionaries are here: **`x64g.rpf/levels/gta5/generic/gtxd.rpf`**
   (771 ytd). For prop textures, also the model's `+hi` / `+hidr` twins.
5. Detail textures (`env_*`) are in **`x64a.rpf/mapdetail.ytd`**.

### Build a texture name index, do not guess

`scripts/ytd_index.ps1` — lists the texture **names** of all `.ytd`s in a folder
(without writing DDS). 948 dictionaries / 13,003 textures indexed; 116 of the 131
wanted textures were found in 9 dictionaries.

### ⛔ SAME NAME, DIFFERENT CONTENT

175 textures exist in more than one dictionary; **the content of 22 really differs**
(measured with md5). **Do not pick** among the copies **by size** — 174,888 bytes is
the standard size of 512×512 DXT1 + mip chain, so the size tells
you nothing. Pick in GTA's own resolution order:

```
the model's OWN dictionary  ->  its parents  ->  strangers (last)
fwy_01, dt1_rd1_1 …    ->  freewayrd, globalroads …  ->  paletoroadtemp …
```

### Names Sollumz makes up

- **Combined names** of the form `ABAB_a`: Sollumz names the material by joining the diffuse+alpha
  names. Some of them really exist in GTA
  (the vanilla `.ydr` uses the same name), some do not.
- `<model>_pal`: a name derived from the model name for a palette sampler that could not be bound.
  **No such texture exists in the game**, not worth searching for.

Telling them apart: dump the vanilla `.ydr` to XML and look at the texture parameter names. If vanilla
also uses that name, the name is real; otherwise Sollumz made it up.

### Building the `.ytd`

`scripts/dds_to_ytd.ps1` — after building, it **reads back** the file and verifies texture
count/name/format. Size is not a validity criterion.
Measured: 129 textures → 12 MB `.ytd`, 114/114 md5 identical on read back.

**If the archetype's `textureDictionary` points at a name that does not exist, no
texture resolves.** Link all archetypes to one dictionary of your own.

---

## 5. `cpv_only` and the decal layer — the real cause of white surfaces

`cpv_only` is a shader **with no texture**; it draws from vertex color only.
It is the **base layer** of the road, and in vanilla the decal covers it.

Measurement (25 plates): `cpv_only` covers 3,412 m²; of the 128 faces on top,
**113 are buried under other surfaces**, 15 are exposed.

Remove the decal from the footprint and this bare base shows and appears as **big
white triangles**. Making up a material is the wrong fix.

**The right way:** split the decal into the same cells too and **merge** it into the parts — when the road
breaks, its overlay breaks with it (2,280 faces).

---

## 6. Normals — the silent cost of solidify

### Measurement

Vanilla map meshes carry **custom split normals**:
`has_custom_normals=True`, sharp edges **0**, flat faces **0**. All
shading comes from baked normals.

Solidify turns the surface into a solid block; **the top face and the vertical
edge share the same vertices**, with smooth shading the normals at the 90° corner
are averaged and the side face gets a partly upward-facing normal — it reflects the sun
like the top face and looks blown-out white.

### Criterion

Distribution by the z component of the vertex normal; "MID" = `0.2 ≤ |nz| ≤ 0.85`:

```
VANILLA fwy_01_rd_01     MID=22%
VANILLA dt1_rd1_r1_06    MID=14%
VANILLA towercrane_02d   MID=21%
OURS   (broken)          MID=38%
OURS   (fixed)           MID=20%
```

**This criterion only means something on geometry that has not tipped over** — in the debris state
parts are tilted, so MID naturally rises to 46%; that is not a defect.

### Fix

**Do not** do a blanket "recalculate normals": vanilla's baked normals
deviate from the face normal by a median of 0.7° but **10% deviate by more than 24°**;
wiping them changes the road's shading.

```python
# KEEP the baked normal of the TOP faces, write FLAT (face normal)
# on the new faces that come from solidify.
nv=[Vector(me.corner_normals[i].vector) for i in range(len(me.loops))]
for p in me.polygons:
    if p.normal.z > 0.5: continue      # TOP: do not touch
    for li in p.loop_indices: nv[li]=p.normal.copy()
me.normals_split_custom_set(nv)
```

Also solidify **downward only** (`offset=-1`): the top face stays at the vanilla
level and does not rise to fight the decals. Measured: top face
height difference median **0.000 m**.

Give the bottom and side faces a real texture (bottom = `freeway_ubderbelly_new_01`,
edge = `mh_bridgebase03`), build the UV with a planar projection and **measure the scale
from the top faces** (0.167–0.197 UV/m on this job, so 1 repeat ≈ 5–6 m).

---

## 7. LOD — whatever the original prop does

Measurement:

```
prop_towercrane_02a  tris H=3455 M= 706  M/H=0.20  lodDist 70
prop_towercrane_02b  H=1544 M= 338        M/H=0.22  lodDist 70
prop_towercrane_02c  H= 740 M= 326        M/H=0.44  lodDist 70
prop_towercrane_02d  H=8006 M=5924        M/H=0.74  lodDist 75
fwy_01_rd_01         NO LOD (High only)   lodDist 9998
dt1_rd1_r1_06        NO LOD               lodDist 9998
```

- **A prop has a Medium LOD**, ratio ~20–44%.
- **Road models have no LOD** — the distant view of a road comes from separate `_lod`
  archetypes. Do not add a LOD to your own road drawable.

In Sollumz: `obj.sz_lods.medium.mesh` + `drawable.drawable_properties
.lod_dist_high / _med / _low / _vlow`.

⛔ **Decimate breaks the 4-influence rule.** When vertices merge, the weight spreads over more
than one group. On rigid parts, after building the LOD pull it back to 100% on one group
and verify **multi-group vertices = 0**.

---

## 8. Gate list (without entering the game)

| what | how | threshold |
|---|---|---|
| extent intact | compare the patched ymap with the original | identical |
| all LOD levels hidden | count in the base **and** `hei_` versions | HD+LOD+SLOD1 |
| cut is complementary | inside + outside = original face count | exact |
| material carried over | `distinct indices` count | close to the slot count |
| UV/color layer | `me.uv_layers`, `me.color_attributes` | `UVMap 0`, `Color 1` |
| object transform | matrix_world **right before** export | identity |
| textures resolve | `.ydr` texture parameters ∩ `.ytd` index | missing ≈ 0 |
| normals | MID ratio | vanilla band 14–22% |
| LOD weights | multi-group / unweighted vertices | 0 / 0 |


---

## Worked example — a 10 m road crack (`dt1_rd1_r1_28`, 2026-09-01)

The complete base data that **must be extracted first** when replacing a vanilla road part; repeat the same order for your own target.

### Target (user decision)

| measure | value |
|---|---|
| length | 10 m |
| width | avg. 2 m (one end wide, narrows further away) |
| depth | 3 m |
| bottom | visible rubble + rock (the player falls in, stops at the bottom) |
| line | starts wide, narrows into a crack further away |

### Target asset

| field | value |
|---|---|
| HD archetype | `dt1_rd1_r1_28` hash **700810582** |
| ytyp | `downtown_01_metadata_002_strm.ytyp` |
| position | 252.06, -946.04, 25.78 |
| bbox | -51.6977,-81.9242,-2.6449 / 51.6876,83.4316,2.6808 |
| lodDist | 148 |
| flags | 8192 = Dont Cast Shadows |
| textureDict | **`dt1_rd1_1`** (hash 1203152392 — VERIFIED with jenkins) |
| physicsDict | 0 -> collision in a separate .ybn |

Overlay (road lines, separate entity):

| field | value |
|---|---|
| name | `dt1_rd1_r1_ovly_38` hash 1433796416 |
| position | 251.91, -946.21, 25.77 (0.23 m from the HD) |
| lodDist | 93 |
| bbox | +-49.02 x +-67.48 x +-2.64 |
| textureDict | `dt1_rd1_1` (same) |

⛔ v1 did NOT count this overlay at all. If it is not removed, **road lines hang
in the air** above the crack.

### LOD chain (assetdb.py lodchain — verified)

| # | name | ymap | idx | lodDist |
|---|---|---|---|---|
| 0 | `dt1_rd1_r1_28` | `dt1_rd1_strm_6.ymap` | 66 | 148 |
| 1 | `3700422285` | `dt1_rd1.ymap` | 225 | 400 |
| 2 | `dt1_lod_12_13_22_23` | `dt1_lod.ymap` | 33 | 1500 |

SLOD2 (#2) **is not touched** — a 10 m crack is not visible from 1500 m.

LOD parent `3700422285` resolved (these were the 4 values the user gave):

| field | value |
|---|---|
| ytyp | `downtown_01_metadata_001.ytyp` |
| assetType | ASSET_TYPE_DRAWABLEDICTIONARY |
| assetName | `dt1_rd1_r5h_slod1_children` (.ydd) |
| textureDict | `dt1_rd1_lod` (hash 2280611059 — VERIFIED) |
| lodDist | 400, flags 8192 |

### The 4 ymaps to touch + the RIGHT base versions

⛔ The same ymap is in more than one RPF and **the versions differ**. Extracting with
`-Flatten $true` silently leaves the wrong version (the last one wins).

| ymap | RIGHT source | md5(12) |
|---|---|---|
| `dt1_rd1_strm_6.ymap` | **patchday27ng** | 4d16ad79331d |
| `dt1_rd1.ymap` | **patchday27ng** | dfe50afe6540 |
| `hei_dt1_rd1_strm_6.ymap` | **update.rpf/dlc_patch/mpheist** | 3d2d93bdd35b |
| `hei_dt1_rd1.ymap` | **update.rpf/dlc_patch/mpheist** | a8f3e2f171da |

In all four the patchday27ng / dlc_patch version DIFFERS from the others.
Right copies: `vanilla/correct/`.

The `hei_` twin **EXISTS** — the line "no hei_ twin (measured)" in v1's
`VANILLA_REMOVE.md` notes WAS WRONG (verified with entities.db).

### Collision

`dt1_rd1` collision is split into 12 .ybn files. The **ONLY** file that covers the target:

**`dt1_rd1_4.ybn`** — BoxMin 88.6,-981.9,23.1 / BoxMax 304.3,-768.4,53.0

The crack is 10 m, so it does not spill into neighbouring ybn files. (The neighbour `dt1_rd1_3` ends
at y=-969.6, our target is at -946.)

### Vanilla road geometry

| measure | value |
|---|---|
| model | 1 |
| geometry | 28 |
| triangles | 5660 |
| LodDistHigh/Med/Low/Vlow | 9998 (all) |
| embedded Skeleton | NONE |
| embedded Bound | NONE |

Shaders (2 kinds, resolved with jenkins):
- `normal_spec_detail` (3620052489) — asphalt body, 22 geometries
- `normal_spec_decal` (471606640) — overlay/line layer, 6 geometries

### Conflict (NOT RESOLVED — awaiting a decision)

Three resources stream **differently edited** versions of the same vanilla ymaps.
In FiveM one of them wins; which one is undefined.

| ymap | conflicting resource |
|---|---|
| `dt1_rd1.ymap`, `hei_dt1_rd1.ymap` | `[maps]/my-test-map` |
| `hei_dt1_rd1_strm_6.ymap` | `[script]/crux_bennysautos/crux_crucialfix` |

### CodeWalker.Core — right property names (measured in this session)

⛔ A wrong name **gives no error, it returns $null** (§5). Measured right names:

| object | WRONG | RIGHT |
|---|---|---|
| Bound | `BoundingBoxMin/Max` | **`BoxMin`** / **`BoxMax`** |
| Drawable | `DrawableModelsHigh` | **`DrawableModels`** / **`AllModels`** |

⛔ `ShaderGroup.Shaders` throws **NotImplementedException** in foreach
(`ResourcePointerArray64<T>`). Fix: iterate over `.data_items`.
