# Sollumz Discord `#resources` — resource and tool catalogue

**Source note — not a rule.** The whole channel: **2022-09-12 → 2026-06-12,
110 messages**, 53 attachments downloaded. Raw dump and files:
local download folder (`_manifest.tsv` = file → CDN link;
the links go stale in ~24 hours).

⛔ No number here **is a measurement** — they are community claims. Before moving a value
into an asset or code, verify it with `assetdb.py`
(the entry rule of `sources/external-tools.md` holds here too).

This file is an **index**: the answer to "is there such a tool / template / reference?".
The method lives in the branches; the index lives here.

---

## Situations to check here before starting a job

| situation | what exists |
|---|---|
| interior / MLO vertex painting | §3 R\* interior colour scheme |
| decal · edge transition · terrain mask | §4 geonodes tools |
| cleanup of an imported drawable | §5 standard cleanup procedure |
| editing LOD ymap / YDD | §6 templates + `nametables.rpf` |
| ped rest pose · IK rig · vehicle seating | §7 ready `.blend` files |
| light · timecycle · lightshaft | §2 |
| bake · spec/gloss · Substance | §9 |
| ymap/ytyp batch processing · MLO export · water | §10 |
| particle preview · blood effect | §11 |
| how R\* did it — reference files | §12 interior libraries, `LS.zip` |

---

## 1. Shader / material

- **4-layer (blend) shader** — `Colour1` vertex colour: layer0 black,
  layer1 blue, layer2 green. `texcoord0` is for the main textures. If the shader has a
  `lookup sampler`, the mask = **the alpha channel of `Colour0`** + `texcoord1`.
- **Mirror-like surface** — `SpecularFalloff` very high + `SpecularFresnel` very
  low + raise `SpecularIntensity`.
- **Coloured water** — the `water_poolenv` shader, parameter **`FogColor`**
  (RGB/255; alpha = visibility depth).
- **If the texture breaks when two meshes are joined**, the two objects' **UV map names must
  be the same**.
- **Tint shader fix** (in the current project) — set the `interpolation` of the
  IMAGE_TEXTURE nodes inside geometry nodes to `Closest`
  (snippet in the raw dump).
- **Batch-rename UV layers** (`UVMap 0`, `UVMap 1` …) —
  Vicho's snippet, in the raw dump.
- Glass tint examples → `glass.blend` · meaning of the ped spec map →
  `ped_spec_meaning_fuller.png`.

> Texture size being a power of two is repeated here too; the rule
> lives in the trunk (`trunk/gta-fundamentals.md` §5) and is not taken from here.

## 2. Light / shadow / timecycle

- **Lightshaft:** `flags = 99` + `Direction Amount = 0` → visible only when the sun
  hits it, and it follows the sun direction.
- **Previewing a light projection texture in Blender:** Cycles + emission +
  Node Wrangler `CTRL+T`; switch the Texture Coordinate link **UV → Normal**,
  set the image **Repeat → Clip**, position via mapping XYZ, blur via `Radius`.
- **`lodlights` / `distlodlights` split:** `distlodlights.ymap` = colour/position ·
  `lodlights.ymap` = intensity, falloff, time flags, cone angle, corona.
- **R\* interior shadows** `v_66_shadowmap2.ydr`, `v_26_shadowtrash.ydr` —
  *"lights in the game never produce shadows like these"* (a baked shadow mesh).
- Light culling plane guide (PDF) · Flashiness reference video ·
  merge of `timecycle_mods_1..4.xml` + 426 weather files ·
  `timecycle-loader.zip` (test in game with `/timecycle <name>`).

## 3. Vertex color

- ⭐ **R\* interior colour scheme:** the **lower half of the shell green→dark green**,
  the **upper half blue→dark blue**. In window/door openings to the outside and
  everywhere the sun hits, **strong red→yellow** (fake lighting).
  On a 2-storey interior the first floor is mostly green, the second floor mostly blue.
- **Blocking rain (outside an MLO):** vertex colour **`#32383A`** on the collision
  mesh/primitive.
- **Fake cloth/wind:** any tree shader + two vertex colour channels;
  `Colour0` black-white (black = little movement, white = a lot), `Colour1` normal
  vertex colours.
- Tools: **Vertex Color Master** (4.x forks included) ·
  **Geonodes Paint Blend** `terrain_mask_v0_5.blend` (four channels automatically).

## 4. Decal / transition

- **Geonodes Edge Decal Tool** → `decal.blend` + `Decal_tool.gif` — builds a transition mesh for a building,
  ground or road; it is added to the Asset Browser.
  It is the only ready-made tool that directly covers corner wrapping / wall damage decals.

## 5. Geometry / mesh hygiene

- ⭐ **Standard cleanup after a drawable import:**
  1. Edit mode → `M` → **Merge by Distance**
  2. Object Data Properties → Geometry Data → **Clear Custom Split Normals Data**
  3. Edit mode `ALT+J` (Tris to Quads): Max Face Angle **90°**, Max Shape Angle
     **90°**, Compare **UVs / Seam / Sharp / Materials** on, **VCols off**
- **Face orientation check:** Show Face Orientation — blue is correct, red is flipped.
- ⛔ **An empty `.col` drawable = instant crash.** If the game crashes instantly when you switch to a mod
  part, this is the first suspect; delete it and export again.
- Primitive collision generation (Collider Tools) · vertex group transfer
  between meshes · weighted normal manipulation (videos in the raw dump).

## 6. LOD

- `FiveM_LOD_template_2_levels.zip` (2-level ymap/model parenting template) ·
  `lod_tuto.zip` + `lod_tutorial.blend` (2025, a stream you can try in game).
- ⛔ **Editing LOD (YDD) requires `nametables.rpf`** — it goes in the GTA 5
  **root folder**. It also contains animation and sound names.

## 7. Ped / animation / rig

- Rest pose templates: `A_pose.blend`, `T_pose.blend`, `FEMALE_A-POSE.blend`,
  modelling scale `ped_scale.fbx`.
- IK rigs: `IK_ForGTA.blend` · `Freemode_F_IK.blend` ·
  `Freemode_M_IK.blend` · **`Freemode_M_IK_Fixed.blend`** ← the version with the root rotation
  bug fixed, **use this one**.
- Vehicle seating reference: `STANDARD_driving_layout.blend`,
  `LOW_driving_layout.blend`.
- **FakeBones** (armature visualisation) · animation flag calculator
  (`vespura.com/fivem/animations/`).

## 8. Fragment / destruction / RayFire

- `yft.blend` — an example fragment that splits into 3 pieces.
- **`blender_rayfirev`** — an add-on that turns a baked animated mesh into a Sollumz 2.1+
  drawable (`github.com/ultrahacx/blender_rayfirev`).

## 9. Texture production / bake

- **GTA baker (Substance)** `Gta_baker.sbs`, `GTA_ColorSpec.sbsar`:
  Color → `COO` curvature overlay · `AOMO` AO · `NO` normal/height.
  Spec → `Invert` (GTA uses **gloss**, so it is inverted) · `COO` · `AOMO` ·
  `MMO` metallic multiplier. *Something with no metallic at all does not drop to black — a little spec
  is always needed.*
- Procedural material + bake playlist (Ryan King Art) · seamless texture video ·
  clothing texture colour/detail (Photoshop) · **Folders2YTD** (DDS folder → `.ytd`;
  now also doable inside Blender with Vicho's Tools).

## 10. Map / MLO / FiveM side

- **Arbolito** — YMAP splitter/merger, train tracks mover, YNV→ONV, prop
  replacer (`github.com/Hancapo/Arbolito`).
- **VichoTools** — save the selection to text, **export MLO transforms as a working
  `.xml.ymap`**, transform copying, YTD tools.
- **dolu_tool** · **ht_mlotool** (MLO audio occlusion) ·
  `tiwabs_audio_door_tool` (custom door sound) · `doortuning.zip`.
- **WaterEditor** (`water.xml` in Blender) · **Water XML Merger** (web).
- Dynamic ymap loading/unloading (`Dynamic-loaded-map-fivem`).
- **Disabling a vanilla interior properly:**
  ```lua
  CreateThread(function()
      local oldinterior = GetInteriorAtCoordsWithType(0.0, 0.0, 0.0, 'int_name')
      DisableInterior(oldinterior, true)
      UnpinInterior(oldinterior)
  end)
  ```
- ⚠️ **`str_requestFlush` is now off by default.** To turn it on in a test environment, add this at the end of
  `server.cfg` / `env.cfg`: `setr str_enableFlush true`
- Stream templates: `FiveM_Map_Resource.7z`,
  `FiveM_server_scenarios_example.zip`.

## 11. Particle / effect / blood

- **eco_effect** (`github.com/Ekhion76/eco_effect`) — watch particle effects
  **live in game**, search them, change scale and options.
  (A second tool that does the same job as `echo effect` —
  `branches/particle/ready-made-effects.md`.)
- **`.ypt` keyframe property documentation** — `github.com/krzysiula3000/ypt-research`.
- **BloodFX** — meaning of the `bloodfx.dat` fields, below.

### `bloodfx.dat` fields (Fadilj's research, third party)

| field | meaning |
|---|---|
| **PROB** | probability that the effect is used; `1.0` on, `0.0` off. Ped damage effects have a **separate** PROB (bullet hole entry only) |
| **SPLAT / SPRAY / MIST DCL ID** | each with a **NORM** and a **SOAK** variant; decal IDs that confirm which effect is used |
| **COL_TINT (R G B)** | colour of the blood splash on the ground |
| **SPRAY DOT_THRESH** | how many large stains/pools are produced on the ground (higher = more) |
| **MIST THRESH** | how close together the small spatter dots are (higher = closer) |
| **LOD RANGE (HI/LO)** | distance at which the effect can be seen; HI is the high-quality version |
| **NUM PROBES (HI/LO)** | **unclear** — the author changed the values and saw no difference |
| **PROBE DISTA** | distance travelled from the shot normal to search for a surface; if it finds one, **Diffuse A** |
| **PROBE DISTB** | searches **below half** of probe A, **only if Diffuse A did not happen**; if it finds one, **Diffuse B** |
| **PROBE VARITN** | how far / how much / how large the blood spreads |

⛔ Every numeric entry in the file must have **both an entry and an exit**
counterpart. The size and speed evolutions correspond to how fast and how large the effect
is shown.
Full text: `sollumz-discord-resources\BloodFX_Documentation.md`.

## 12. Reference libraries and other

- `Interior_References.7z` (207 MB) · `Interior_References_V2.7z` (849 MB,
  25 interiors) — ⚠️ **V2 is NOT a superset of V1**: `v_bahama` is in both,
  but it is 93 MB in V1 and 19.6 MB in V2 — different exports. **Keep both.**
- `LS.zip` (76 MB) — **all of Los Santos (SLOD2) for position and scale reference**.
- `Procedural_IDs.txt` — material IDs in collision YBNs that spawn grass/litter/debris
  (256 lines).
- `vmt_types.txt` — 38 `VMT_` carcols.meta cosmetic types.
- `custom_radios.zip` · `Vehicle-Siren-Meta-Files.zip` · `customped.zip`
  (SP/RageMP ped DLC template) · `asset-browser-guide.pdf`.
- `blender-3.3.7-windows-x64.zip` **not downloaded** (277 MB) — the channel keeps a portable 3.3.7
  because the shadow map render pass cannot be selected in 3.4+.
  That is the only reason to keep in mind if a shadow bake is ever needed.
