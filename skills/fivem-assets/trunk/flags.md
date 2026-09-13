# Flags — ytyp / ymap / collision / specialAttribute / extension

**Trunk file.** A magic number you see is not copied, it is decoded:
`python scripts/assetdb.py flags <number> [--entity]`. The bit tables and the 21 values of
`specialAttribute` are here; measured on 316,975 archetypes + 3,145,882
entities. Source: `trunk/flags.md` §1-6, §8, §11
(moved into the trunk on 2026-09-05; §7 export format → `trunk/tool-pitfalls.md`
Detail B, §7c-7d particle → Particle branch, §8.5b-8.6 decal → Look branch,
§9 LOD → Map branch, §10 animation → Animation branch).

---

## 1. ⛔ Flag numbering: `flagN` is bit `N-1`

Sollumz names the properties `flag1 … flag32`, but **`flag1` is the lowest
bit**, i.e. value `1`. Formula:

```
value(flagN) = 2^(N-1)
```

Writing `1 << N` directly **shifts the whole table by one bit** and silently produces the wrong
name. Check: `flag16 = LOD Use Alt Fade → 2^15 = 32768`, exactly the value in CodeWalker's
checkbox list.

---

## 2. ARCHETYPE flags (`CBaseArchetypeDef.flags`)

| Value | Bit | Name |
|---:|---:|---|
| 1 | 0 | *(unnamed)* |
| 2 | 1 | Wet Road Reflection |
| 4 | 2 | Dont Fade |
| 8 | 3 | Draw Last |
| 16 | 4 | Climbable By AI |
| 32 | 5 | Suppress HD TXDs |
| 64 | 6 | Static |
| 128 | 7 | Disable alpha sorting |
| 256 | 8 | Tough For Bullets |
| **512** | 9 | **Has Anim (YCD)** |
| **1024** | 10 | **UV anims (YCD)** |
| 2048 | 11 | Shadow Only |
| 4096 | 12 | Damage Model |
| 8192 | 13 | Dont Cast Shadows |
| 16384 | 14 | Cast Texture Shadows |
| 32768 | 15 | Dont Collide With Flyer |
| 65536 | 16 | Double-sided rendering |
| **131072** | 17 | **Dynamic** |
| 262144 | 18 | Override Physics Bounds |
| **524288** | 19 | **Auto Start Anim** |
| 1048576 | 20 | Has Pre Reflected Water Proxy |
| 2097152 | 21 | Has Drawable Proxy For Water Reflections |
| 4194304 | 22 | Does Not Provide AI Cover |
| 8388608 | 23 | Does Not Provide Player Cover |
| 16777216 | 24 | Is Ladder Deprecated |
| 33554432 | 25 | Has Cloth |
| **67108864** | 26 | **Enable Door Physics** |
| 134217728 | 27 | Is Fixed For Navigation |
| 268435456 | 28 | Dont Avoid By Peds |
| 536870912 | 29 | Use Ambient Scale |
| 1073741824 | 30 | Is Debug |
| 2147483648 | 31 | Has Alpha Shadow |

### Which flag combination in practice — community usage
Source: `sources/external-tools.md` §2. These are not measurements but combinations seen to
work — though all three repeat in more than one video.

| job | flags |
|---|---|
| animated prop (clip plays by itself) | **`Has Anim` (512) + `Auto Start Anim` (524288)** |
| UV-animated prop / weapon skin | **`UV anims` (1024) + `Auto Start Anim`** |
| skeleton + UV animation **together** | **`Has Anim` + `UV anims`** — in this case `Auto Start Anim` is **not needed** |
| breakable fragment | **`Dynamic` (131072)**; opt. `Does Not Provide AI/Player Cover` |
| prop cloth | **`Has Cloth` (33554432) + `Dynamic` + `Double-sided rendering` (65536) + `Use Ambient Scale` (536870912)** |
| baked shadowmap plane | **`Dont Cast Shadows` (8192)** |
| reflection proxy | archetype flags **0**; the work is in the entity flags (`only render in reflections` + cast static/dynamic shadow) |

### ⭐ `Time` archetype — no need to write `TimeFlags` by hand
In Sollumz, if the archetype **`Type` field is set to `Time` instead of `Base`**, the panel opens a
**24-hour checkbox grid** (`12:00 AM–1:00 AM` … `11:00 PM–12:00 AM`)
and a **`Select from … to …`** range picker. The `TimeFlags` magic number in this file
(e.g. `14680095` = 21:00–05:00) is produced there.

Typical fields for a time-bound prop: `HD Texture Distance` **60**,
`Lod Distance` **60**, ymap **Content Flags `HD (1)` + `Physics (64)` = `65`**.
Verification: CodeWalker → Lighting → change the hour with the **`Time of day`** slider;
the prop must appear inside the range and disappear outside it.

### Cross-check (316,975 archetypes)

**1308** archetypes have the `clipDictionary` field filled:

| Subset | Count |
|---|---:|
| `Has Anim (YCD)` bit set | 470 |
| only the `UV anims (YCD)` bit set | 838 |
| **no anim bit set** | **0** |

And there are **0** archetypes with the `Has Anim` bit set and an empty `clipDictionary`.
So the mapping overlaps completely — the bit table is right.

Sample decode — vanilla `prop_pallet_01a`, `flags="549584896"`:
```
549584896 = Dynamic | Does Not Provide AI Cover
          | Does Not Provide Player Cover | Use Ambient Scale
```
(For a breakable pallet: dynamic, gives no cover, ambient-scaled. Consistent.)

### Flag sets used in videos

- Animated prop → `Dynamic` + `Has Anim (YCD)` + `Auto Start Anim`
- UV/spritesheet animation → `UV anims (YCD)`
- Door → `Dynamic` + `Enable Door Physics`

### ⭐ 2.1 REAL usage distribution — 316,975 archetypes, full count

The bit table above says "what each bit means"; this table says **what vanilla
actually writes**. Look here first when choosing flags: if you are setting a combination that is
not in the list, set it knowing why.

**There are 224 unique flag values, but three of them cover 90.5%.**

| value | count | % | cumulative | decode |
|---:|---:|---:|---:|---|
| `536870912` | 137,663 | 43.4 | 43.4 | Use Ambient Scale |
| `0` | 108,104 | 34.1 | 77.5 | *(none)* |
| `8192` | 41,210 | 13.0 | **90.5** | Dont Cast Shadows |
| `537001984` | 5,122 | 1.6 | 92.2 | Dynamic \| Ambient |
| `33685504` | 4,049 | 1.3 | 93.4 | Dynamic \| Has Cloth |
| `537002016` | 2,787 | 0.9 | 94.3 | Static \| Dynamic \| Ambient |
| `8196` | 2,486 | 0.8 | 95.1 | Draw Last \| Dont Cast Shadows |
| `549584896` | 1,723 | 0.5 | 95.6 | Dynamic \| No AI Cover \| No Player Cover \| Ambient |
| `32` | 1,287 | 0.4 | 96.0 | Static |
| `2097152` | 1,035 | 0.3 | 96.4 | Drawable Proxy Water Refl |
| `604110848` | 860 | 0.3 | 96.6 | Dynamic \| **Enable Door Physics** \| Ambient |
| `2048` | 849 | 0.3 | 96.9 | Shadow Only |
| `4` | 839 | 0.3 | 97.2 | Draw Last |
| `12582912` | 810 | 0.3 | 97.4 | No AI Cover \| No Player Cover |
| `549453824` | 593 | 0.2 | 97.6 | No AI/Player Cover \| Ambient |
| `536870944` | 550 | 0.2 | 97.8 | Static \| Ambient |
| `131072` | 425 | 0.1 | 97.9 | Dynamic |
| `1024` | 363 | 0.1 | 98.4 | UV anims |
| `536936448` | 232 | 0.1 | 98.6 | Double-sided \| Ambient *(plant)* |
| `570556416` | 177 | 0.1 | 98.7 | Dynamic \| Has Cloth \| Ambient *(flag/banner)* |
| `537264128` | 170 | 0.1 | 98.8 | Dynamic \| Override Physics Bounds \| Ambient |
| `67239936` | 158 | 0.0 | 98.8 | Dynamic \| Enable Door Physics *(no ambient)* |
| `536871424` | 149 | 0.0 | 98.9 | **Has Anim** \| Ambient *(RayFire roots: `des_*_root`)* |

Four things to read from it:

- **`Use Ambient Scale` is almost a free default** (43.4% on its own).
  If you are not sure, setting it is vanilla behaviour.
- **`Static` is rare** (0.4% on its own). "Static + Dynamic together", however,
  really exists in vanilla (`537002016`, 2,787 archetypes) — not a contradiction.
- **The door flag has two versions**: `604110848` (860, with ambient) and
  `67239936` (158, without ambient). Four out of five have ambient.
- **`536871424` = Has Anim + Ambient**, **no** `Auto Start Anim` — and
  its carriers are `des_*_root`, i.e. RayFire roots. The engine starts the RayFire clip,
  so no auto-start is needed. Setting `Auto Start Anim` on your own RayFire root
  is **not** the vanilla pattern.

⚠ **The same distribution for the ENTITY (ymap) side COULD NOT BE MEASURED** — the
`entities.tsv.gz` and `entities.db` schemas have no `flags` column (`name,x,y,z,kind,ymap,interior`).
The §3 bit table and the decoded magic numbers below hold, but the answer to "which entity flag
does vanilla write most" is **not in our hands**. If needed, a `flags` column must be added to the
ymap dump.

---

## 3. ENTITY flags (`CEntityDef.flags`, ymap)

> ⚠ This table was **generated** from `assetdb.py::ENTITY_FLAGS`, not written by hand.
> In its previous version everything after 128 had shifted by one row (a hand-copy error);
> the code was always right, the document was wrong. If you change it, regenerate it from the code.

| Value | Bit | Name |
|---:|---:|---|
| 1 | 0 | Allow full rotation |
| 2 | 1 | Stream Low Priority |
| 4 | 2 | Disable embedded collisions |
| **8** | 3 | **LOD in Parented YMAP** |
| **16** | 4 | **LOD Adopt Me** |
| 32 | 5 | Static entity |
| 64 | 6 | Interior LOD |
| 128 … 16384 | 7-14 | Unknown 8 … Unknown 15 |
| 32768 | 15 | LOD Use Alt Fade |
| **65536** | 16 | **Underwater** |
| 131072 | 17 | Does Not Touch Water |
| 262144 | 18 | Does Not Spawn Peds |
| **524288** | 19 | **Cast Static Shadows** |
| **1048576** | 20 | **Cast Dynamic Shadows** |
| 2097152 | 21 | Ignore Day Night Settings |
| 4194304 | 22 | Disable shadow for entity |
| 8388608 | 23 | Disable entity, shadow casted |
| **16777216** | 24 | **Dont Render In Reflections** |
| 33554432 | 25 | Only Render In Reflections |
| 67108864 | 26 | Dont Render In Water Reflections |
| 134217728 | 27 | Only Render In Water Reflections |
| 268435456 | 28 | Dont Render In Mirror Reflections |
| 536870912 | 29 | Only Render In Mirror Reflections |
| 1073741824 | 30 | Unknown 31 |
| 2147483648 | 31 | Unknown 32 |

### `65536` = Underwater — measured

The Sollumz source names this bit **"Unused"**, CodeWalker calls it
**"Underwater"**. 3,145,882 entities scanned: the bit is set **only 14 times**
and all of them are water props — `prop_dock_bouy_1/2/3` (dock buoy) and
`prop_rub_wheel_01`, in harbour/river ymaps (`po1_09_long_0`,
`vb_rv_strm_1`). **CodeWalker is right.**

### ⭐ The magic numbers we have now decode

```
1572872  = LOD in Parented YMAP | Cast Static Shadows | Cast Dynamic Shadows
1572865  = Allow full rotation  | Cast Static Shadows | Cast Dynamic Shadows
18350080 = Dont Render In Reflections | Cast Static Shadows | Cast Dynamic Shadows
```

- **`1572872` is the value of the HD entity in a LOD chain.** The `8` bit tells the engine
  "my LOD is in the PARENT map". If there is no parent map the entity **silently drops**.
  This is the reason for the old warning "if the ymap value is given the object does not
  spawn" — the value is not broken, it **belongs in the middle of a chain**.
- **The only difference from `1572865` is the `1` bit**: `Allow full rotation` instead of
  `LOD in Parented YMAP`. Flag/banner props use it (so they can turn in the wind).
- **`18350080` is an MLO entity**: the interior object is not drawn in reflections.

---

### `assetType` — not a field but a PROPERTY (`rage__fwArchetypeDef__eAssetType`)

`ASSET_TYPE_DRAWABLE` (`.ydr`) · `ASSET_TYPE_FRAGMENT` (`.yft`, per-bone collision **only** with this) · `ASSET_TYPE_DRAWABLEDICTIONARY`
(`.ydd`, LOD parents) · `ASSET_TYPE_ASSETLESS`. Producing a fragment and leaving `assetType` as drawable wastes all the work
(`branches/prop/fragment.md`); a RayFire root is a **drawable**, not a fragment (`branches/map/destruction.md`).

## 4. `specialAttribute` — all 21 values

Sollumz enum name = **the engine's semantics**; the "vanilla count" column = the **real usage**
we measured over 316k archetypes. The two are different layers and
both are needed.

| Value | Sollumz name | Vanilla count | Real use / example |
|---:|---|---:|---|
| 0 | None | 314,116 | not a door |
| 1 | Deprecated - Unused | 41 | *"Does nothing"* — `sm_boat_clutter2` |
| 2 | Deprecated - Ladder | 233 | ~~crane~~ → ladder; `prop_towercrane_02a..e` |
| 3 | Traffic Light | 80 | traffic light |
| 4 | Unknown 4 | 17 | Sollumz does not know either; `*_hedgedtl_*` (hedge detail) |
| 5 | Garage Door | 81 | garage/roll-up door |
| 6 | MLO Water Level | 630 | ⚠ examples `ch1_roadsb_slod*` — contradiction, §4.1 |
| 7 | Normal Door | 661 | hinged door |
| 8 | Sliding Door | 74 | sliding door |
| **9** | **Barrier Door** | **1** | `m26_1_prop_m61_sewer_gate` |
| 10 | Sliding Vertical Door | 8 | roller shutter / elevator door |
| 11 | Bush *(internally `NOISY_BUSH`)* | 39 | bush |
| 12 | Rail Crossing Barrier Door | 2 | `prop_railway_barrier_01/02` |
| 13 | Deformable Bush | 226 | crushable bush |
| 14 | Single Axis Rotation | 2 | *"procedural animation"*; `prop_roofvent_06a/14a` |
| 15 | Dynamic Cover Bound | 81 | gives cover; `v_ret_fh_dinetable`, `prop_aircon_m_10` |
| 16 | Rumble On Vehicle Collision | 207 | `prop_barrier_work01a..d`, `prop_pallet_01a` |
| 17 | Rail Crossing Light | 2 | ⚠ examples `prop_traffic_rail_*` — contradiction, §4.1 |
| 30 | Clock | 11 | *"animated clock hands"*; `prop_big_clock_01` (bone tags 0/419/418, NO clip) |
| 31 | Deprecated - Tree | 463 | *"same as double-sided rendering"* |
| **32** | **Street Light** | **0** | never used in vanilla |

### 4.1 Two name contradictions — one resolved, one narrowed

**17 → Sollumz is right, I was wrong.** The two examples `prop_traffic_rail_1a` and
`prop_traffic_rail_2` are both in **`v_traffic_lights.ytyp`** — i.e. the traffic *light*
ytyp. The "rail" in the name is not a road barrier but a railway crossing.
Our old label ("traffic barrier") **was wrong** and has been fixed.

**6 → the contradiction stands, but its shape changed.** Earlier I had said "all 630 examples
are `*_slod*`"; that was a wrong generalisation drawn from **a 6-row sample**.
Full measurement:

- **only 99 (15.7%)** of the 630 archetypes have `slod` in their name
- The rest are ordinary rural map pieces: `cs1_15b_barn`, `cs1_15b_bridge_det1`,
  `cs1_15b_chimneydet1` …
- Name prefixes: `cs1_` (474) · `ch1_` (37) · `cs2_` (21) · `cs6_` (18)
- Spread over 20 different ytyps, the densest being `country_01_metadata_010_strm.ytyp` (363)
- `lodDist` median **80** — too small to belong to an SLOD

So neither "all SLOD" is right, nor does the name "MLO Water Level" match the usage.
**Do not rename without measuring; know both.**

⚠ Lesson: I generalised from a 6-row sample and it turned out wrong. Every claim in this
table must come from a full count.

### 4.2 Which types the door system really animates

**Measured:** the `specialAttribute` distribution of the **1176** archetypes with the
`Enable Door Physics` bit (67108864) set:

| specialAttribute | Count |
|---:|---:|
| 7 Normal Door | 646 |
| **0 None** | **379** |
| 5 Garage Door | 77 |
| 8 Sliding Door | 71 |
| 10 Sliding Vertical | 7 |
| 12 Rail Crossing Barrier | 2 |
| 4 Unknown 4 | 1 |
| **9 Barrier Door** | **0** |
| **14 Single Axis Rotation** | **0** |

→ `DOOR_CAPABLE = {5, 7, 8, 10, 12}` **is right**. `9` and `14` are in the enum, but
vanilla gives them no door physics: `14` is a **procedural rotation** (roof
fan), not a door. A tutorial video that makes a door with `14` and sees it "open"
shows this procedural rotation, not the door system.
→ Also, **379 archetypes carry door physics while `specialAttribute=0`**:
saying whether something is a door by looking only at `specialAttribute` is incomplete,
look at the flag too.

---

## 5. ytyp EXTENSION types (14)

`ytyp/properties/extensions.py:29`. **The Sollumz UI shows only 11 of
them**; `DOOR`, `SPAWN_POINT_OVERRIDE`, `LIGHT_EFFECT` are not in the list but
are supported on the import path.

| Sollumz constant | XML class | In UI |
|---|---|:--:|
| `DOOR` | `CExtensionDefDoor` | — |
| `PARTICLE` | `CExtensionDefParticleEffect` | ✓ |
| `AUDIO_COLLISION` | `CExtensionDefAudioCollisionSettings` | ✓ |
| `AUDIO_EMITTER` | `CExtensionDefAudioEmitter` | ✓ |
| `EXPLOSION_EFFECT` | `CExtensionDefExplosionEffect` | ✓ |
| `LADDER` | `CExtensionDefLadder` | ✓ |
| `BUOYANCY` | `CExtensionDefBuoyancy` | ✓ |
| `LIGHT_SHAFT` | `CExtensionDefLightShaft` | ✓ |
| `SPAWN_POINT` | `CExtensionDefSpawnPoint` | ✓ |
| `SPAWN_POINT_OVERRIDE` | `CExtensionDefSpawnPointOverride` | — |
| `WIND_DISTURBANCE` | `CExtensionDefWindDisturbance` | ✓ |
| `PROC_OBJECT` | `CExtensionDefProcObject` | ✓ |
| **`EXPRESSION`** | **`CExtensionDefExpression`** | ✓ |
| `LIGHT_EFFECT` | `CExtensionDefLightEffect` | — |

⚠ **`EXPRESSION` is the ytyp leg of a `.yed` expression chain.**
The rule there: "add an Expression extension to the ytyp, write the **bare name**" — Sollumz
has a ready UI for it, no need to write the XML by hand.
`PROC_OBJECT` is the ytyp leg of the @ma procedural grass system.

---


> §6 particle extension → `branches/particle/ready-made-effects.md` (2026-09-05).

## 8. Collision — THREE SEPARATE FLAG LAYERS

Often confused. The three live in different places and do different jobs.

### 8.1 The material's own flags (16)

```
STAIRS          NOT COVER         NO DECAL        NO PTFX
NOT CLIMBABLE   WALKABLE PATH     NO NAVMESH      TOO STEEP FOR PLAYER
SEE THROUGH     NO CAM COLLISION  NO RAGDOLL      NO NETWORK SPAWN
SHOOT THROUGH   SHOOT THROUGH FX  VEHICLE WHEEL   NO CAM COLLISION ALLOW CLIPPING
```

In the same panel: `Procedural ID` · `Ped Density` · `Room ID` · `Material Color Index`.

### 8.2 Bound COMPOSITE flags (31, TWO separate sets)

`ybn/properties.py::BoundFlags`. An object carries **two** sets:
`composite_flags1` = **Type Flags** (what this bound *is*),
`composite_flags2` = **Include Flags** (what this bound *collides with*).

```
UNKNOWN          MAP WEAPON       MAP DYNAMIC      MAP ANIMAL
MAP COVER        MAP VEHICLE      VEHICLE NOT BVH  VEHICLE BVH
PED              RAGDOLL          ANIMAL           ANIMAL RAGDOLL
OBJECT           OBJECT_ENV_CLOTH PLANT            PROJECTILE
EXPLOSION        PICKUP           FOLIAGE          FORKLIFT FORKS
TEST WEAPON      TEST CAMERA      TEST AI          TEST SCRIPT
TEST VEHICLE WHEEL  GLASS         MAP RIVER        SMOKE
UNSMASHED        MAP STAIRS       MAP DEEP SURFACE
```

Measured example (pool/water): Type = `MAP WEAPON` + `MAP DYNAMIC` + `MAP ANIMAL`
+ `MAP COVER` + `MAP RIVER`; material `WATER`, material flags
`SEE THROUGH` + `SHOOT THROUGH` + `NO CAM COLLISION`.

### 8.3 Archetype flags

The table in §2 (`Dynamic`, `Enable Door Physics`, `Has Cloth` …). These are the flags
of the **archetype**, not of the collision.

### 8.4 Material table (185)

`data/collision_materials.tsv` · query: `assetdb.py mat [<name>|--index N]`
Source: Sollumz `ybn/collision_materials.py`; list order = the game's material
index. **Cross-checked:** `ANIMAL_DEFAULT = 171` — exactly the value of an earlier,
independent measurement.

Extremes: lightest `Fibreglass Hollow` (126.0), `Polystyrene` (157.5),
`Foam` (175.0); heaviest `Metal Solid Large` / `Metal Garage Door` /
`Metal Manhole` (31500.0). Common ones: `CONCRETE` 1 · `GRAVEL_SMALL` 31
· `GRASS_SHORT` 48 · `METAL_GARAGE_DOOR` 67 · `WOOD_SOLID_MEDIUM` 70 ·
`GLASS_SHOOT_THROUGH` 112 · `CAR_METAL` 116 · `WATER` 125 · `ANIMAL_DEFAULT` 171.

### 8.5 Measured behaviour

**`mesh` collision + `Dynamic` archetype flag = the object does not interact with world
collision and falls into the ground.** If you want a dynamic object the collision
must be a **primitive** (bound box / cylinder). Door standard: `NOT COVER` +
`NOT CLIMBABLE`.

---


## 11. Nametables — hash → name

In Blender, add a folder with `Preferences → Sollumz → Name Tables → +` and
restart Blender; imported models then show real names instead of `hash_...`.
The tables are distributed in the Sollumz Discord `#resources` channel (Oohk)
as `nametables.rpf` (~13.6 MB); drop it into RPF Explorer and extract the
`.nametable` files inside into the folder.

The benefit is not cosmetic: without a nametable two entities in a ymap come in as `hash_60F...`
and which one is `arch_lod` and which is `lod_canopy` can only be found by trying them one by one
with CodeWalker's hash calculator.
