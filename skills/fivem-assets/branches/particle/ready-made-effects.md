# Use an existing effect / attach it to a prop — `fxName`, `StartParticleFx`, ytyp extension

**When to read:** you are looking for an existing vanilla effect (smoke, fire, sparks, dust), attaching a particle to a prop, or "the effect never appears".
**Source:** `trunk/flags.md` §6 · SKILL query lines (2026-08) · **Measured:** 64,209 ytyp extensions, 2,549 effects / 368 `.ypt`; `ent_` prefix 65.3%
**Read first:** `branches/particle/_branch.md` · trunk › `trunk/tool-pitfalls.md` §3 CodeWalker (`FxcFileHash`, `VFT`, `ResourcePointerArray64`)

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" ptfx <prop|effect>   # ytyp particle extension, fxType
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" fx <name> --exact    # is the effect in the .ypt catalogue, in which file
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" ptfx --type 4        # Destroy (3 Break) — 'dust on break'
```

## ytyp particle extension (`CExtensionDefParticleEffect`)

```xml
<Item type="CExtensionDefParticleEffect">
  <name>prop_pallet_01a</name>
  <offsetPosition x="0" y="0" z="0" />
  <offsetRotation x="0" y="0" z="0" w="1" />
  <fxName>dst_wood_structures</fxName>
  <fxType value="4" />          <!-- Destroy -->
  <boneTag value="-1" />        <!-- -1 = ALL bones -->
  <scale value="1.4" />
  <probability value="100" />
  <flags value="0" />
  <color value="0xFFFFFFFF" />
</Item>
```

### The `fxType` enum

| Value | Name | Note |
|---:|---|---|
| 0 | Ambient | continuous/ambient; `amb_*` families |
| 1 | Collision | at impact |
| 2 | Shot | when shot |
| 3 | Break | when broken |
| 4 | Destroy | when destroyed (`dst_*`) |
| 5 | Animation (Unused) | not used |
| 6 | RayFire | *"Valid FX names are defined in the `ENTITYFX_RAYFIRE_PTFX` block"* |
| 7 | In Water | under water |

### Flags
`Ignore Damaged Model` · `Play on Parent` · `Only on Damaged Model` ·
`Allow Rubber Bullet Shot`

### ⛔ The ytyp `fxName` and the effect name in the `.ypt` are NOT THE SAME

**Measured** (406 unique `fxName` × 2,549-effect catalogue):

| Case | Count | Share |
|---|---:|---:|
| in the catalogue **as is** | 3 | 0.7% |
| found after adding the **`ent_` prefix** | 265 | 65.3% |
| found with the `ent_` prefix **+ a suffix** | 9 | 2.2% |
| **no relative at all** | 129 | 31.8% |

So you write `amb_steam_vent_round` into the ytyp, and the real name inside the `.ypt`
is **`ent_amb_steam_vent_round`**. Sometimes a suffix is added too:
`amb_butterflys` → **`ent_amb_butterflys_swarm`** ·
`amb_moths` → `ent_amb_moths_swarm` / `ent_amb_moths_cupboard` ·
`ray_shipwreck_splash` → `..._s` / `..._l`.

**Total resolvable: 68.2%.**

### ⚠ The remaining 31.8% are vanilla's own dangling references

**The index is not incomplete — proven:** `core.ypt` was opened to XML with CodeWalker
(45.5 MB) and **895 of the 895 effects** in `EffectRuleDictionary` appeared in the index,
**0** missed. So these names really do not exist in the game files.

The most striking: `amb_water_roof_drips_short` **5,621 uses** ·
`amb_wind_dust_swirl` 783 · `amb_wind_sand_dune` 547 · `amb_wind_dust` 475 ·
`amb_water_roof_pour_short` 374 · `dst_shop_plastic_cont` 256.

`amb_water_roof_drips` and `..._thin` exist but `_short` does not — so these are dead
references left over from effects deleted/renamed across versions. **If you copied a vanilla ytyp and inherited its effect,
that effect may already not work.**

Practical result: if you copied a vanilla prop's ytyp and inherited its effect,
that effect may already not work. **Verify before copying:**

```bash
assetdb.py fx <fxName> --exact
```

### Where to find the effect name (four ways)

1. **Learn it from the vanilla ytyp** — CodeWalker RPF Explorer → the relevant ytyp (e.g.
   `v_storage.ytyp`) → `Ctrl+F` the prop name → the particle block under
   `extensions`. The breaking pallet's effect is `DST_wood_structure`, **FX type 4**,
   **bone tag −1**.
2. **Pleb Masters: Forge** — click the prop, the particle effect is shown at the bottom
   (full search 121 pages of props).
3. Ready-made lists: Derek Deck's tested ambient list · Dirty Free's
   GTA 5 data dump.
4. ⭐ **`echo effect`** (FiveM helper resource) — searches and previews effects **in game**
   with sliders. Drop it into the resource folder + `ensure`.
   A second tool doing the same job: `eco_effect`
   (`sources/community-resources.md` §11).

### Blender side — setting up the extension

ytyp → *autocreate from selected* → **Extensions** tab → `+` → type
**Particle** → FX Name / FX Type / bone tag / scale / probability.
To see the gizmo: `T` in the viewport → the gizmo button on the toolbar.
**The gizmo only represents the position, not the effect.**

- ⛔ **An extension CANNOT be duplicated with `Shift`+drag** — nothing happens, and
  no error either. Use the **`Duplicate Extension`** button.
- ⚠️ **After moving the gizmo, the numbers are not applied until you click in the viewport.**
- ⚠️ **`scale = 1` is too big for most effects; the typical value is `0.2`.**
  (The `1.4` in the XML example above is the value measured for that prop, not a
  default.)

**Ambient names verified as visible in game** (the `amb_` prefix works directly from a ytyp
extension): `amb_generator_smoke` · `amb_cockroaches` ·
`amb_fly` · `amb_candle_flame` · `amb_sparking_wires` · `amb_moths_nighttime`
(night only) · `amb_water_drips_med` · `amb_cherry_blossom` ·
`CO_falling_snow` (collision) · `SHT_rubbish` (shot).

**Measured:** Stumpy Mason 38 min (`leiAB2aM3w8`), local notes `notes/07` §2, 2026-09 —
the typo pitfall happened **three times** in a single video (`sparking_wired`,
a misspelled `cockroaches`); the effect never appeared, and no error was given.
`assetdb.py fx <name> --exact` is exactly for this.

### Effect catalogue

`data/ptfx_effects.tsv.gz` — **2,549 unique effects** in 368 `.ypt`
(1,240 files scanned, 0 errors). `core.ypt` alone carries 895 effects.
Generator: `build_ptfx.ps1`.

### Measured pitfalls
- **A typo is silent.** A wrong `fxName` produces no error, the effect
  is invisible. When the extension is copied, the error is copied with it.
- `boneTag = -1` → all bones (it does not matter in which order the parts break off).
- `probability` really is a probability (20% → ~1 in 5 objects).
- **Rotation matters**: sparks set up upside down spray upwards.
- Effects with the `veh_` `ped_` `proj_` `wheel_` prefixes do not work from a ytype, they need a script.
- Some are conditional: `_nighttime` only at night, sea effects under water.

---
