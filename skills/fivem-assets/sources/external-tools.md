# External tool observations — what can be measured from someone else's pipeline

**Source note — not a rule.** The measurable part of external tools (Five Toolkit etc.) and the [verified]/[refuted] tag system. Moved: `sources/external-tools.md` (2026-09-05). Raw copies are kept alongside, in `_external/`.

This file **is not the atlas's measurement corpus.** Some of the numbers here
are a third-party tool's product choices; values measured from vanilla are
in the tables under `data/` and in the other references.

| Tag | Meaning |
|---|---|
| **[verified]** | Compared with our data, it held. Usable. |
| **[external]** | The tool's own data. May be right; it is not a measurement. |
| **[refuted]** | Confirmed to contradict our measurement. Do not use. |
| **[adopt]** | Worth taking into our pipeline as a policy/approach. |

⛔ **General rule:** if an external tool gives a number (tag, flag, lodDist,
material index), that number is **a claim, not evidence**. Verify it with `assetdb.py`.
Do not take an unverified number from this file into code or an asset —
if it does not carry the `[verified]` tag, measure it first.

---

## 1. FIVE TOOLKIT — `tools.scarfacemlo.com`

**Examined:** 2026-09-01 (home page, `tools.scarfacemlo.com/docs`, 2.09 MB JS bundle, open API
endpoints). The free, Discord-login-gated, browser-based FiveM asset production pipeline
of the Scarface MLO / "3D Academy" team.
Its slogan: *"From 3D model to FiveM server, no Blender."*

### 1.0 Access and architecture [external]

React + three.js (R3F) + zustand + GSAP, Vite; Caddy + Cloudflare.
**Everything that touches GTA runs on the server** — the browser is only the editor.
Login `/api/auth/discord/login`; `/api/auth/me` →
`{authEnabled, authenticated, inGuild}`. The tool pages (**/armes**, **/props**, **/optimiseur**, **/shell**)
are behind login; `/api/shaders` and
`/api/shells/catalog` are **open**.

The CSP has `wasm-unsafe-eval` (WASM runs on the browser side).
`connect-src`: Sketchfab + `*.amazonaws.com` + `*.cloudfront.net`.
Sketchfab import uses **the user's own API token**; the token is stored only on the
client. They claim that models are not stored.

Tools: Weapons Creator (12 steps), Props Creator (6 steps), Resource
Optimizer (3 steps), Tattoo Creator, Vehicle Debadger, Weapon Editor;
in development: Shell Creator, Cloth Creator, Map Conflict Fix.

⚠️ The client has **no library/plugin attribution at all** (`sollumz`, `codewalker`,
`plugin`, `credit`, `powered by`, `open source` — zero matches). Which pipeline they
use cannot be seen from outside; to find out, you would have to log in, produce an output
and compare it byte by byte with vanilla.

### 1a. ⛔ The weapon bone tag table is WRONG [refuted]

Summary: `gun_root 0` and
`gun_gripr 18308` are right; `gun_muzzle 55863` and `gun_vfx_eject 5103` are wrong
(correct: **17833** / **28405**); bones called `gun_mag` · `gun_slide` · `gun_bolt` ·
`gun_pump` **do not exist at all** (the magazine slot is `WAPClip` 1477, the cocking handle
`Gun_Cock1` 39439). The tool marks this skeleton internally as a *"procedural silhouette"*,
but the interface says *"GTA names and IDs are preserved"* — so to the
user it looks correct.

### 1b. [adopt] The "byte-for-byte" policy

The written rules of Weapon Editor and Optimizer. This is the right stance for any job that
touches someone else's installed resource:

- A file that is not changed comes back **bit for bit identical**.
- The weapon's **technical name is never changed** — the resource is already installed; renaming
  it breaks the inventory and the scripts that reference it.
- If `cl_weaponNames.lua` does not exist, **no `client_script` is added to someone else's
  `fxmanifest.lua`**.
- Vanilla component models (suppressor, scope…) are **never rewritten**;
  they keep their own texture.
- A file protected by `fxap` (escrow) is **detected and left untouched**; a broken/empty
  file is **only reported**, with no attempt to fix it.
- An added component goes **on top of** the existing ones; none of them are changed.
- The 3D view draws **only the weapon body**; components that are already installed are separate
  models, so they are not shown — and the user is told this explicitly while placing a new part.
  ("Say what I am not showing" is a good pattern.)

### 1c. [external] Thresholds — product choices, not measurements

| Threshold | Value | Context |
|---|---:|---|
| Weapon "high poly" badge | 60,000 vertices | warning on Sketchfab import |
| Prop "high poly" badge | 37,000 vertices | *"a prop fills streaming faster than a weapon"* |
| "Very dense model" | 150,000 triangles | precise collision calculation slows down |
| Upload ceiling | 100 MB | model + textures, or a full resource |

Collision simplification: 1e-4 weld → `SimplifyModifier`, the ratio is clamped to the
**[0.02, 1]** range. Collision modes: **None / Box / Precise**
(default `none`, ratio `0.5`, material `default`).

⚠️ These numbers **do not replace** our polygon budget measurements
(e.g. vanilla `a_c_rottweiler_02.ydd` = 11,303 triangles). When you give the user a budget,
measure it from vanilla; do not take it from here.

### 1d. [external] Collision materials — a short list of 20

The `bound material` names offered in their interface (our full table has **185**
materials, `assetdb.py mat`):

```
default · concrete · brick · stone · marble · tarmac · sand_loose · grass
wood_solid_medium · wood_hollow_medium · metal_solid_medium
metal_hollow_medium · metal_corrugated_iron · glass_shoot_through
plastic · rubber · cardboard_box · cloth · leather · ceramic
```

The name format is right (vanilla `METAL_SOLID_MEDIUM` = index 56). "Offer the user 20
options, do not show 185" is a good product decision — in our tools too, a short list
+ a way out to the full list is the right pattern.

### 1e. [external] `/api/shaders` — an open table of 106 shaders

It requires no authentication. Fields: `name`, `sps`, `renderBucket`, vertex
`layout`, `textures[{sampler, required}]`, `params[{name, value}]`.
Copy: `_external/five_toolkit_shaders.json`.

Bucket distribution: 0 → 55 · 1 → 18 · 2 → 26 · 3 → 6 · 7 → 1
(the only shader in bucket 7 is `glass_displacement`).

**We already have something better** (`assetdb.py shader`, 249 shaders), and ours
gives the render bucket **from the usage distribution**:

```
normal_spec → ours:    bucket 0 = 6405 · bucket 3 = 166 · bucket 1 = 75
              theirs:  renderBucket 0 (a single number)
```

Difference: for `normal_spec`, `specularIntensityMult` is the vanilla default
**1** in ours and **0.125** in theirs. That is a choice; do not take it as the vanilla value. They do not
list `specMapIntMask`, which we have; we do not count their `globalAnimUV0/1` as
a default.

⛔ **The `required` field carries no information — measured.** In **105** of the 106 shaders
the only `required` sampler is `DiffuseSampler`, and it is **always in position 0**;
there is **no** shader with more than one `required`; the only shader with no `required`
at all is `cable`. So the field says nothing more than "the first sampler is diffuse".
Not worth adding to `build_shaders.py` — because it was measured first, this field
did not enter our corpus.

### 1f. [external] Shell Creator grid contract

A ready set of dimensions if we ever do shell/housing work of our own
(`_external/five_toolkit_shells_catalog.json`):

```
module 2.0 m · floor height 3.0 m · max 4 floors · 21×21 grid
tiles: vanilla se_stud_wall_1..16 · se_stud_tile_*
cell content: tile · ceiling · stairs · walls{} · decor{}
options: void (closing gaps) · shadowMask
output: one merged prop (.ydr + collision) + .ytd + .ytyp
        + layout.json (spawn offset for the housing script included)
```

### 1g. [external] Camo / sticker approach

They do not bother with the tint palette shader: camo and stickers are **merged into a single
texture on export**, and the `.ytd` of a cut-out magazine gets a copy of the weapon's
texture. Vertex colour is offered as a global multiplier
(*"white = no effect; any other value paints the weapon"* — this is right, the engine multiplies vertex
colour with the texture; default `[255,255,255,255]`).

Camo textures are `/camo/<id>.webp`, generated with 2×2 grid mirroring + a mip chain,
and coloured with the `hue-rotate` + `saturate` CSS filters.
14 ready patterns: `darkmatter · eclaire · zombie_nuk · diamant · or_emeraude ·
sable · romain · crane · flamme · miami · weed · weed2 · coeur · rose`.

⚠️ Their own warning is right too: if a cut-out magazine spans more than one material,
in game it carries **a single texture** and the remaining faces come out wrong.

### 1h. [external] Texture re-encoding

*"Changed textures are re-encoded to DXT5; DXT1 ones become about twice
as heavy."* Consistent with our measurement (`core.ypt` embedded particle
textures: DXT5 75 · DXT1 32). Telling the user about the size increase **in advance** is a
good pattern.

### 1i. Base weapon catalogue — 28 classes

**Model names [verified]:** **all** 28 exist in our skeleton corpus as
real `.ydr` files (tried one by one with `assetdb.py bones`; none returned
"no skeleton"). The bone counts are our measurement:

| id | model | class | bones | damage | range | clipSize | tbs (ms) |
|---|---|---|---:|---:|---:|---:|---:|
| pistol | `w_pi_pistol` | pistol | 12 | 26 | 60 | 12 | 250 |
| combatpistol | `w_pi_combatpistol` | pistol | 12 | 27 | 60 | 12 | 240 |
| appistol | `w_pi_appistol` | pistol | 12 | 28 | 55 | 18 | 100 |
| pistol50 | `w_pi_pistol50` | pistol | 11 | 51 | 60 | 9 | 350 |
| stungun | `w_pi_stungun` | pistol | 6 | 1 | 12 | 1 | 1000 |
| microsmg | `w_sb_microsmg` | smg | 15 | 21 | 40 | 16 | 90 |
| smg | `w_sb_smg` | smg | 18 | 22 | 45 | 30 | 90 |
| assaultsmg | `w_sb_assaultsmg` | smg | 14 | 23 | 50 | 30 | 80 |
| machinepistol | `w_sb_compactsmg` | smg | 9 | 27 | **120** | 12 | 118 |
| assaultrifle | `w_ar_assaultrifle` | rifle | 16 | 30 | 90 | 30 | 100 |
| carbinerifle | `w_ar_carbinerifle` | rifle | 17 | 32 | 90 | 30 | 100 |
| advancedrifle | `w_ar_advancedrifle` | rifle | 14 | 34 | 90 | 30 | 95 |
| mg | `w_mg_mg` | rifle | 16/15 | 40 | 100 | 54 | 110 |
| combatmg | `w_mg_combatmg` | rifle | 17 | 45 | 100 | 100 | 100 |
| sniperrifle | `w_sr_sniperrifle` | sniper | 16 | 101 | 1500 | 10 | 1000 |
| heavysniper | `w_sr_heavysniper` | sniper | 12 | 216 | 1500 | 6 | 1200 |
| marksmanrifle | `w_sr_marksmanrifle` | sniper | 18 | 65 | 1000 | 8 | 300 |
| pumpshotgun | `w_sg_pumpshotgun` | shotgun | 12 | 116 | 40 | 8 | 600 |
| assaultshotgun | `w_sg_assaultshotgun` | shotgun | 14 | 108 | 35 | 8 | 300 |
| sawnoffshotgun | `w_sg_sawnoff` | shotgun | 10 | 130 | 25 | 8 | 550 |
| grenadelauncher | `w_lr_grenadelauncher` | **shotgun** | 15/14 | 100 | 120 | 10 | 800 |
| golfclub | `w_me_gclub` | melee | 4 | 10 | 2 | 1 | 500 |
| knife | `w_me_knife_01` | melee | 3 | 15 | 2 | 1 | 500 |
| bat | `w_me_bat` | melee | 3 | 12 | 2 | 1 | 500 |
| crowbar | `w_me_crowbar` | melee | 3 | 12 | 2 | 1 | 500 |
| hammer | `w_me_hammer` | melee | 3 | 12 | 2 | 1 | 500 |
| nightstick | `w_me_nightstick` | melee | 3 | 10 | 2 | 1 | 500 |
| ball | `w_am_baseball` | thrown | 3 | 5 | 40 | 1 | 1000 |

**Stat columns [external] — could not be verified.** Our `weapons.tsv.gz`
holds category/model/ammo/component/livery/flags; the `Damage`, `WeaponRange`,
`ClipSize`, `TimeBetweenShots` fields **are not in our corpus**. Reasonable as starting
values; do not pass them on as "this is vanilla".

Two suspicious points: the `machinepistol` range of **120** (the other SMGs 40-50) and
`grenadelauncher` being tied to **shotgun** as its bone class —
the second is a deliberate simplification (the `gun_pump` slot is used).

Application default (no base selected): `damage 30 · range 60 · clipSize 12 ·
timeBetweenShots 250`, namespace `weapon_`.

### 1j. Tattoo pipeline

**Zone names [verified]** — the real `PedDecorationCollection` zones:

```
ZONE_HEAD · ZONE_TORSO · ZONE_LEFT_ARM · ZONE_RIGHT_ARM
ZONE_LEFT_LEG · ZONE_RIGHT_LEG
```

Payload: `{collection, tattoos:[{name, zone, gender, uvPos, scale, rotation}]}`
+ a PNG per tattoo. Output: **`PedDecorationCollection` XML + stream `.ytd` +
fxmanifest + README**. Stages: *read the images → DDS → .ytd + XML →
package the resource*. Every tattoo must have **a unique and valid name (hash)**.
The input is **transparent PNG**; gender is kept separate.

This structure is the known correct structure — our own tattoo work uses the same skeleton.

### 1k. Vehicle Debadger

Input: a full resource folder or only `_hi.yft`. Extensions kept on
export: `yft · ytd · meta · lua · ycd`. Flow:

1. **Parts** — tuning parts and logos are detected automatically; you choose which
   parts are mounted on the vehicle. *Changing parts rebuilds the vehicle
   and cancels any debadging in progress.*
2. **Debadging** — embossed badges are deleted. Selection has three modes: `Part`
   (connected component) · `Face` (triangle by triangle) · **`Material`** (everything that shares the same
   texture — often the whole "badges" material).
3. **Textures** — flat-painted logos (steering wheel, grille, rims) are removed with a stamp,
   or the texture is replaced entirely; it can be overlaid on the material's UV.
   Without a `.ytd` this step does not work.
4. **Export** — *"your YFT is rewritten one to one; only the badges are missing:
   collision, deformation, doors and windows untouched."*
   The far LOD (the `.yft` that is not `_hi`) is **touched on purpose**.

⚠️ One resource = one vehicle. If more than one vehicle is detected, it refuses.

### 1l. Resource Optimizer

File states: `OK · Optimizable · Corrupted · Empty · Protected (fxap) ·
Ignored`. Only **oversized `.ytd` files** are shrunk; the zip structure is kept
one to one. A broken/empty file is **not fixed, it is reported**. `fxap` is not flagged
as an error but as "locked by its owner", and it is returned unchanged.
Individual files accepted: `ytd ydr ydd yft ybn ymap ytyp lua meta xml
cfg`. **A folder cannot be uploaded** — a zip is required.

Result headers: `X-Original-Size`, `X-Optimized-Size`, `X-Optimized-Count`.

### 1m. API surface and payload shapes [external]

```
GET  /api/auth/me · /api/auth/logout · /api/auth/recheck · /api/auth/discord/login
GET  /api/shaders                (open)
GET  /api/shells/catalog         (open)
POST /api/convert                → {jobId}     (weapon — queued)
GET  /api/convert/status?jobId=  → {state, stage, queue, error}
GET  /api/convert/result?jobId=  → zip
POST /api/props/convert          → zip         (synchronous)
POST /api/tattoo/convert         → {jobId}     (shared status/result)
POST /api/shells/convert
POST /api/optimizer/analyze  ·  POST /api/optimizer/apply?jobId=
POST /api/vehicle/preview    ·  POST /api/vehicle/export
POST /api/import/scan        ·  POST /api/import/export   (Weapon Editor)
```

Status is polled **every 2 seconds**; the queue position is shown to the user.

**Prop payload** — a good checklist of what a minimal prop pipeline
needs:

```json
{ "name": "...", "lodDist": 0,
  "model": {"filename": "...", "sketchfab": {...}|null},
  "collision": {"mode": "none|box|mesh", "ratio": 0.5, "material": "default"},
  "transform": {...},
  "materials": [{"name": "...", "shader": "...", "params": {}, "textures": {}}],
  "vertexColor": [255,255,255,255] }
```

The collision mesh is sent as a separate part, as a **raw float32 position buffer**
(an unindexed triangle list). Textures are attached with the field name
`tex:<materialIndex>:<samplerName>`.

**Weapon stages (6):** *read model → bake → skeleton + weights →
textures → DDS → .ytd → metas → packaging.*

### 1n. Step flows — as product design [adopt]

**Weapon (12):** Upload → Cleanup → Base weapon → **Alignment** → Bones →
Magazine → Components → Vertex group → Render → Configuration → Preview →
Export. *The only mandatory step is choosing the base weapon;* in a simple case
`Upload → Base → Alignment → Export` is enough, and the rest passes with defaults.

**Prop (6):** Upload → Cleanup → **Placement** → Render → Configuration →
Export. Placement has a ghost ped as a scale reference, offered in **three poses**:
*standing · sitting (to size a chair) · walking (for a stair
step)*. Position and scale are **baked** into the geometry on export.

**Optimizer (3):** Upload → Analysis → Export.

Three patterns worth adopting:
- **Two-mode selection**: `Part` (one click selects a connected component) and `Face` (triangle
  by triangle) — they write explicitly "if the part is welded to the body, switch to Face".
- **Every step says "you can skip this step".** Which step is really
  mandatory is not left unclear.
- **They say in advance that the preview will lie**: *"RAGE shaders light things differently
  in game — only the in-game test is binding."*
  This is the product form of our `⛔ A SCREENSHOT IS NOT A MEASUREMENT` rule.

### 1o. Accepted formats [external]

| Tool | Format |
|---|---|
| Weapons | **GLB only** (single-piece static); textures as separate PNG/JPG |
| Props | GLB recommended, GLTF accepted; FBX/OBJ **rejected** |
| Component import | GLB · GLTF · FBX · OBJ |
| Optimizer | resource zip or individual files |
| Vehicle | full resource folder or `_hi.yft` |
| Tattoo | transparent PNG |

For models from Sketchfab their own warning is right: *"some have no texture
or use a material that is incompatible with GTA (procedural, multi-UV) — prefer
single-texture ones."*

### 1p. Not adopted, and why

- **Bone tag table** — refuted (§1a).
- **Shader `required` field** — measured, carries no information (§1e).
- **Shader default params** — our measured table is wider, and theirs deviates from vanilla
  in at least one place (§1e).
- **Weapon stats** — no counterpart in our corpus, could not be verified; the table
  stays as `[external]` (§1i).
- **Polygon thresholds** — a product choice; does not replace the vanilla budget (§1c).
- **The conversion pipeline itself** — on the server, behind a Discord login.
  Which library they build with could not be measured; whoever wants to measure it should log in, produce a
  prop and compare the resulting `.ydr`/`.ytyp` with vanilla field by field.

---

## Adding a new tool to this file

1. First write **what you measured**, then what is claimed.
2. Mark every number with `[verified]` / `[external]` / `[refuted]` / `[adopt]`.
   Do not leave an untagged number.
3. If you find a number that contradicts our measurement, put a warning block **in the related
   reference's own file** — this file is an archive; the point of impact is there.
4. Before saying "they have it and we don't", **measure first**: the `required` field in §1e
   was ruled out exactly this way.


---

## 2. Sollumz Discord `#tutorials` extraction (2026-08-21) — map of the local `notes/` folder

75 messages, 57 video transcripts; the raw data **does not enter the repo**. The distilled items were distributed to the matching branch leaves (community practice, not measurement; on a conflict the measurement wins). Topic → local file:

The full step-by-step procedures are in the `notes/` directory of the local extraction folder
(not in the repo). Topic → file mapping:

| topic | file |
|---|---|
| animated prop+collision, fragment, prop/ped cloth, ped animation, retarget | `notes/01` |
| UV animation, MLO light, shadowmap, reflection proxy, vertex AO, material, YBN alignment, doortuning | `notes/02` |
| `.yed`/IG_/CS_, weight painting, skintone `_r`, freemode garment, ped scaling, `p_eyes`/`p_ears`, ped prop, weapon | `notes/03` |
| vehicle setup, MLO production, interior LOD, terrain blending, parallax, timecycle, audio occlusion, sound emitter, radio | `notes/04` |
| graffiti/decal (Substance → DDS → render bucket 2 → ymap) | `notes/05` |
| time bound prop, Cable Tools, terrain/building replacement | `notes/06` |
| Sollumz Discord new channels tour | `notes/07` |
| the four grass systems, terrain anatomy, `@ma`, grass batch, the two LOD mechanisms, Sketchfab animated drawable | `notes/08` (→ `branches/map/grass-procedural.md`, `lod.md`) |
| vehicle add-on inventory | `notes/09` (→ `branches/vehicle/`) |

### Unreachable sources (retried)
- `ttKh1iOorIU` Shadowmap (YamK Mods) — **the video was made private**
- `IIrBh13-lG4` One room MLO (gta5 modder) — **the video was removed**

The topics of both are covered by other videos.


---


> Shader = program + render bucket measurement → `branches/look/shader.md`.


## 3. Tool inventory — pattern scan of 178 transcripts (2026-08, community)

Sollumz's own buttons, external add-ons, non-Blender tools, FiveM helpers, reference sites and **what we have that the community does not**. Number = in how many separate videos it appears. Source `notes/09` (not in the repo).


**All** 178 transcripts went through the pattern scan (the ones already read + the ones
not read yet). The number next to each item is **in how many separate videos it appears** —
the measure of whether it is a community standard.
Raw output: `tool_inventory.txt`

> ⚠️ Tools in videos without subtitles **do not show up** in this scan
> (some, such as `Catenary`, `Substance 3D Painter`, `NVIDIA Texture Tools`, are
> known only from the frame tour). They are marked separately below.

---

## A. Sollumz's OWN tools — not add-ons, mostly unknown

These are already installed; there is nothing separate to download. The real gain here:
several jobs we were trying to do by hand turned out to have a ready button.

| tool | where | what it does |
|---|---|---|
| ⭐ **Add Bone Constraint** | Drawables → Bone Tools | Sets up the constraint that ties collision to a bone **by itself and sets its space correctly**. This turned out to be the cause of the `Child Of` ↔ `Copy Transforms` confusion — nobody picks it by hand. |
| ⭐ **Apply Bone Flags: rotation and translation** | Drawables → Bone Tools | The in-Sollumz fix for the *"Sollumz leaves `Flags` at zero"* problem in atlas §1.5. |
| **Bone Tools → Limit** | same panel | Resets and limits the flags of a single bone (weapon magazine alignment). |
| ⭐ **Vertex Painter (`Shift+T`)** | viewport | RGBA channel isolation · palette · **multi-object vertex paint** · ⭐ **Terrain Paint** (paints the texture 1-4 layer blend directly). |
| ⭐ **Cloth Tools → Diagnostics → Refresh** | Drawables | The **real verification gate** for ped cloth — counts binding and material errors. Target: zero. |
| **Cloth Tools → Pin / mass / pin radius** | Drawables | Cloth pinned points and vertex masses. |
| ⭐ **Cable Tools** | Drawables | Per-vertex `Radius` · `Diffuse Factor` · `Micromovements` · `Phase Offset` (+`Randomize`) · `Material Index`. |
| **LOD Tools → Generate LODs** | Drawables | Reference mesh + Medium/Low, decimation default 0.6. |
| **Light Tools + Light Presets (`+`)** | Drawables | Saves your own light preset. |
| **Shader Tools → Convert to \<shader\>** | Drawables | Converts a normal material to `ped`, `ped_cloth`, `ped_emissive`, `normal_spec` etc. |
| **Order Shaders** | Drawable hierarchy | Puts the UV-animated material in order (required before Sollumz 2.9). |
| **Fragments → Set Mass → Calculate** | Fragments | Calculates the mass of the collision boxes. |
| **Create Physic Bones (at Objects) + "Parent to selected bone"** | Fragments | Builds a fragment bone chain. |
| **Create Box From Selection** | Collisions | Makes a bound box from the selected geometry. |
| **Map Data → Create YMAP / Create Entities** | Sollumz | Produces a ymap from Blender. |
| **Archetype Definition → Auto-Create From Selected** | Sollumz | Produces a ytyp archetype; **if type `Time` is picked instead of `Base`**, a 24-hour box grid opens. |
| **Extensions tab + `Duplicate Extension`** | ytyp | Particle/ladder/audio extensions. ⛔ They are not duplicated with `Shift`+drag; this button is required. |
| **`Fill Animation Data`** | Animations | ⛔ **BROKEN** — writes the frame count wrong; enter it by hand. |

---

## B. Blender add-ons (installed from outside)

| add-on | in how many videos | what for |
|---|---|---|
| **Sushi Cleanups** | 3 | Cleans up empty vertex groups (required after a weight transfer). |
| **Vertex Color Master** | 3 | Per-channel vertex painting + **Data Transfer** (moving AO into the R channel of `Colour 1`). |
| **Vicho Tools** | 2 | Mentioned as a "requirement" for animation production; also **`.ytd` production from inside Blender**. |
| **Rokoko** | 2 | Retarget. ⛔ **`Auto Scale` must be off** — when it is on, root motion is deleted. |
| **DeepBump** | 1 | Makes a normal map from a diffuse. |
| **Collider Tools** | 1 | Makes producing collision boxes easier. |
| **UV Packmaster** | — | UV packing (mentioned, not required). |
| ⚠️ **Catenary** | *(from a video without subtitles)* | Generates a real catenary curve for a cable. Used together with Sollumz Cable Tools. |
| **Quixotic's ped list** | 1 | `R0sGnIgvBq0` — *"My Fave Blender Addons for Ped Editing"*, **not read yet**. |

---

## C. External tools (outside Blender)

| tool | in how many videos | note |
|---|---|---|
| **YMT Editor** (grzybeek) | **9** | The most mentioned tool. Ped components, prop categories, **render flags**, the `hash_07AE529D` height offset, **Generate Creature Metadata**. |
| **Folders to YTD** | 5 | Builds a `.ytd` from a folder, converting to DDS if needed. |
| **OpenIV** | 5 | In most videos as the **old way**; CodeWalker RPF Explorer is preferred. |
| **3ds Max** | 5 | GTA IV → GTA V rigging pipeline (wolffiremodz). Not a Sollumz alternative; a different pipeline. |
| **Notepad++** | 4 | XML editing; the way to merge many clips into one `.ycd`. |
| **V Weapons Toolkit** | 3 | ⚠️ **Version `1.0.3`** — later versions are broken. |
| **FXDK / Cfx Development Kit** | 2 | Timecycle editor (`timecycleeditor 1`). ⚠️ **Remove ReShade `dxgi.dll`** first. |
| **vMenu** | 2 | To change the game time while adjusting timecycle/lights. |
| **Audacity** | 2 | Splitting sound into **left/right mono** (radio + static emitter). |
| **NVIDIA Texture Tools** | 2 *(+frame tour)* | DDS export. Setting measured for decals: **BC3 · mipmap MAX · Gamma Correct · Premultiplied Alpha**. |
| **Blender 3.3 (portable)** | 2 | ⚠️ **Only for the old shadowmap method** — because the Shadow *render pass* was removed. The new method works in current Blender. |
| **Audio Occlusion Tool** | 1 | Produces `.dat151` + `.ymt` from ytyp+ymap XML. |
| **AnimKit** | 1 | Animation tool on the 3ds Max side. |
| ⚠️ **Substance 3D Painter** | *(no subtitles)* | Graffiti/decal texture production; the `Opacity` channel is required. |
| ⚠️ **JPEXS + Adobe Flash CS6** | *(text guide)* | For MLOScaleformTools — Scaleform screens inside an MLO. |

---

## D. FiveM-side helpers

| | what it does |
|---|---|
| ⭐ **`echo effect`** | Searches and previews particle effects **in game** with sliders. The first thing to install if you are getting into particle work. |
| **A console command like `str_request_flush`** | Refreshes the stream without restarting the server; mentioned in two videos, **the exact name is from hearing it** — must be verified. May need a Canary/unstable build. |

---

## E. Reference sites and lists

| source | what for |
|---|---|
| ⭐ **Pleb Masters: Forge** (3 videos) | Prop browser. Shows **a prop's particle effect**, procedural models and freemode clothing components. The most practical way to look up a particle name. |
| **Derek Deck**'s list | Tested, **working ambient particle** names. |
| **Dirty Free** GTA 5 data dump | The full list of all particle names. |
| **docs.sollumz.org** | Official documentation; the Legacy→Enhanced conversion is there. |
| **CodeWalker Discord** | ⚠️ Download CodeWalker **only from here** — other sites are old/risky. |

---

## F. What we have that the community does not

| ours | the community's way |
|---|---|
| **`assetdb.py fx --exact`** | Scanning lists by hand. One video lost **a test round** to a typo. |
| **`assetdb.py flags`** | Flag numbers are copied by hand. |
| **`assetdb.py light --table`** (72,539 lights p05/median/p95) | *"Look at vanilla and imitate it"*, no numbers. |
| **RayFire (`des_*`) production pipeline** | Not mentioned in any video. |
