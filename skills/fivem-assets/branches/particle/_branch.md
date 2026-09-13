# Particle — branch rules

Command: `/particle`
**Keywords:** particle, ptfx, .ypt, effect, smoke, fire, sparks, steam, dust, drops, flies, snow, leaves, explosion effect, fxName, StartParticleFx, amb_, dst_, brk_, core.ypt, fxType, CExtensionDefParticleEffect, flipbook, sprite sheet, sprite page, C4, emitter, keyframe, KFP, evolution, donor effect, transplant, effect catalogue, effect family, PtFxAssetStore, test bench, rcon, blood effect, bloodfx
**What belongs here:** **A visual effect** — smoke · fire · sparks · dust · liquid; `.ypt` authoring, ytyp particle extension. Boundary: light → `/look` · the breaking physics itself → `/prop`.

> The keywords above are **accelerators, not a complete list.** If a word is not on the list,
> routing does not stop — this definition is used. *“roller shutter”* is not on the list, but it is still a door object.


## Valid for every leaf in this branch

Measurement sources: `core.ypt` (45.5 MB) field by field; 2,549 vanilla effects / 368 `.ypt`; 64,209 ytyp extensions;
15 + 56 families measured in game with the test bench.

### Naming and links
- **The ytyp `fxName` and the effect name in the `.ypt` are NOT THE SAME** — the engine adds the `ent_` prefix (65.3%). Before writing
  an `fxName`, run `assetdb.py fx <name> --exact`. A wrong name **silently** never appears.
- **The emitter name is not the effect name**; `<ParticleRule>` is in the **effect** block, not in the emitter.
- In-game use carries **two separate names** (asset name + effect name); an asset name **has no capital letters**.

### `.ypt` authoring — the four silent breakdowns
- ⛔ **The CodeWalker XML reader does NOT WRITE `FxcFileHash` or `VFT`** → a `.ypt` without shader, nothing is drawn →
  `scripts/ypt_xml_to_bin.ps1` (writes the hash, reads back, exit 1 if zero).
- ⛔ **Every behaviour type has a fixed number of keyframe slots and all of them are written** (`Age`/`Velocity`/`Sprite` 0 · `Colour` 3 ·
  `Size`/`Rotation` 4); a missing slot crashes `Save()` in `AssignPositions` and does not say which slot.
- ⛔ **Do not assume the scale from the field name:** `m_sizeScalarKFP` is a **percentage** (neutral 100, median 57.6; writing `1.0` drops the size
  to 1%); `speed`/`life`/`playbackRate` ~1.0. An empty `m_tblrScalarKFP` means multiplier 0 → zero size. `FxcTechnique`
  is a closed list (`RGBA_lit_soft`), there is no `default`. `m_zoomScalarKFP` drives the whole spatial scale of the effect.
- ⛔ **Do not write 0 into an `Unknown*` field** — look at its distribution (`UnknownA4..B0` distance band, `Unknown10C` `0x10100`).
- **Particle texture is DXT + mip chain** (107/107 vanilla); no uncompressed/single-mip sample. `make_dds.py` default.
- ⛔ **A rule written from scratch does not make the engine apply the grid — the production path is TRANSPLANT** (`ypt_transplant.py`); the donor's technique
  was chosen for its own texture, do not use a multi-texture donor.

### Sprite sheet (flipbook) — measured
- **`C4` is not the grid, it is the index of the LAST FRAME to play.** The sheet is sliced but **there is no flipbook** — a particle is locked to the cell
  it was born in. If frame changes are wanted: **N emitters + `Unknown10` delay** (`layered-effects.md`).
- The last frame comes out empty (in 15 of 15 families) → three-stage gate; the frame must not touch the cell edge; one rng per pass.
- **Motion is not inherited, it is written** — a donor that gets its motion from the texture dies with a static sprite; check both the MIN and the MAX envelope.

### Runtime
- **`PtFxAssetStore Pool Full, Size == 400` counts files**; **a single large `.ypt` freezes the game** (measured threshold) → split it,
  a name map is required. Stream and commands **in separate resources**.
- **A non-zero handle only shows that the name was found**; "read back passed" does not mean the engine accepted it;
  **a particle composited on a white background misleads**; a screenshot is not a measurement → **test bench** (write the label on
  screen, call a vanilla effect as reference, count the lattice).
- ⛔ **A Turkish apostrophe closes a Lua string, `lua_check` misses it**; `Wait()` cannot be called in a command callback.

## Leaves

| wanted | file | status — source |
|---|---|---|
| Use an existing effect / attach it to a prop | ready-made-effects.md | measured — former ytyp-ymap reference §6 · SKILL queries |
| Build a `.ypt` from scratch (sheet, slots, transplant, motion) | ypt-from-scratch.md | measured — former ptfx-flipbook reference §1-6, §8, §13 · former ytyp-ymap reference §7c-7d |
| Texture sheet — frames, `C4`, grid, density, transplant | sprite-sheets.md | measured — former ptfx-flipbook reference §1-5 |
| Catalogue / family production and the quality gate | catalog.md | measured — former ptfx-flipbook reference §9-12, §14-15 |
| Layered (multi-emitter) effect | layered-effects.md | measured — former ptfx-flipbook reference §1e-BIS · ptfx_compose |
| Deployment and in-game measurement (test bench, rcon, pool) | deployment-measurements.md | measured — former ptfx-flipbook reference §1c, §7, §16-18 |

## Scripts (all in `scripts/`)
`ptfx_sheet.py` (sheet) · `make_dds.py` (DXT5+mip) · `build_custom_ptfx.py` / `ypt_transplant.py` (production) ·
`ypt_xml_to_bin.ps1` (hash + read back) · `ptfx_build_catalog.py` · `ptfx_quality_gate.py` · `ptfx_find_donor.py` ·
`ptfx_merge.py` · `ptfx_motion.py` · `ptfx_compose.py` (layer) · `ptfx_sim.py` (GIF simulation — a model, not the engine) ·
`ptfx_blender_render.py` / `ptfx_blender_energy.py` / `ptfx_blender_smoke.py` (`--kind smoke|fog|steam|fire`) (sprite render: solid / energy-liquid / volume) · `ptfx_kenney.py` ·
`ptfx_bench.py` (in-game measurement)

## Trunk files to read
- `trunk/flags.md` §6 particle extension flags · `trunk/tool-pitfalls.md` §3 (`YptFile.Load`, size is not the measure,
  `ResourcePointerArray64`), §4 (`while read` stdin), §6 FiveM (adding a file to stream takes three steps, ghost session)
- `trunk/verification-ladder.md` — `.ypt` read-back gate; in-game measurement is the last rung (test bench)
- Live in-game effect preview (`eco_effect`, `echo effect`), `.ypt` keyframe property documentation and `bloodfx.dat` field meanings → `sources/community-resources.md` §11 — **source note, not a rule.**
