# Clothing — branch rules

Command: `/clothing`
**Keywords:** clothing, garment, outfit, freemode, component, .ydd, head_000_r, uppr, lowr, jbib, feet, accs, skintone, _r suffix, _uni, ped prop, hat, glasses, p_head, p_eyes, p_ears, propsName, YMT, texture variant, colour variant, Colour 0, Colour 1, UVMap 1, blood map, Mesh Domain, ped scaling, MH_hair_scale, cloth physics, cape, skirt, veil, .yld, ped cloth, shoes, heels, heel, height offset, taller, MP_HEELS, CreatureMetadataName, jiggle, spring bone
**What belongs here:** **A component worn or attached ON a ped** — garment, hair, hat/glasses, skin-tone variant, ped height/scale. Boundary: the ped's own skeleton and animation are outside this branch.

> The keywords above **speed up routing; they are not a complete list.** If a word is not in the list,
> routing does not stop — this definition is checked instead. *“roller shutter”* is not in the list, but it is still a door object.


## What holds for every leaf in this branch

⚠️ **This branch is not measured yet.** All of its sources are community videos (`notes/03`); the weight rules
and skeleton counts match our own measurements, the rest is `[video]`. When a build is done, the
measurement is written here and the `status` column changes.

⚠️ **[video] — community explanation, not our measurement.** Where it gives a number, verify it with `assetdb.py`; on a conflict the measurement wins.
  Most sources of this branch are community videos; **this holds for every leaf**.

### Files and skeleton
- **Component file names are the same on every ped** (`head_000_r.ydd`, `uppr_000_u.ydd`) → when extracting from the RPF,
  `extract_asset.ps1 -PathFilter '<ped>'` is required; without the filter dozens of peds write to the same file and the last one wins.
- **`.ydd` face bones are `FB_*_000`, `.yft` ones `FB_*_045`** — same tag, different name (21 bones); Blender binds by name,
  and on a wrong match the face does not deform and no error is raised.
- **Freemode has 128 bones, a typical ped 98**; the difference is `MH_hair_scale` + skirt rolls (`SM_*SkirtRoll`) + face bones.
  Moving a freemode garment to 98 = weight transfer (**Source Layers = By Name**), or delete the missing bones and
  **Normalize All**.
- **Weights:** ≤ 4 bones per vertex (extra ones are silently cut), total exactly 1.0, in 1/255 steps.
- **Ped cloth sim mesh ≤ 254 vertices** (Sollumz `CLOTH_CHAR_MAX_VERTICES`, vanilla `csb_bride.yld` exactly 254). Fabric that ripples with motion → `ped-cloth.md`; prop env cloth does not see the ped's motion.
- **A ped `.yft` has no physics** (Sollumz ped physics crashes the game).

### Mesh and texture

**Texture naming rule** (learn it by heart; the same in every leaf):

```
<component>_diff_<NNN>_<letter>_<suffix>     jbib_diff_000_a_uni
<component>_normal_<NNN>                     jbib_normal_000
<component>_spec_<NNN>                       jbib_spec_000
```
- `<component>`: `jbib` `uppr` `lowr` `feet` `hand` `teef` `accs` `task` `berd` `hair`
- `<NNN>`: component index in the YMT
- `<letter>`: texture variation, **`a`–`z`, up to 25 variations**
- `<suffix>`: `uni` (universal) or a skin-tone variant (`r`, `lat` …)

- **Two UV maps are required:** `UVMap 0` texture, **`UVMap 1` blood map** (do not touch).
- **Vertex colours:** `Colour 0` = `FF8000` (lighting; without it the part is shaded dark in sunlight), `Colour 1` = `000000`
  alpha 0 (wind + sweat; alpha > 0 makes the garment sway/shine). An emissive part: white vertex colour + `ped_emissive`.
- ⛔ **Export → Drawable → `Mesh Domain` = `Face Corner`**; `Vertex` only for MP freemode **heads**.
- **Freemode:** spec + bump are embedded, **diffuse is not embedded** (texture swaps in game). **A non-streamed ped has no embedded
  texture at all** — if a `textures/` folder appeared in the export folder, something is still embedded somewhere.
- **`Exclude Skeleton` OFF for a component export, ON for a ped prop export.**
- **Texture names follow the Rockstar rule:** `<component>_diff_<NNN>_<letter>_<suffix>` · `_normal_<NNN>` · `_spec_<NNN>`;
  on a prop only the letter (`_a`, `_b`). A random name → skin tone silently switches off. **The texture is square.**
- **`_r` (skintone):** the skin texture is not in the garment's `.ytd` (`mp_fm_skin`); the skin UV is **not moved**; the mask is
  the **alpha** channel of the specular (white = fabric).
- **Ped prop `Render Flags` match the Blender shader** (`ped_alpha`/`ped_decal`/`ped_cutout`) — unimportant on MP freemode,
  effectively required on every other ped. `peds.meta` `propsName` is the only thing that activates props.
- LOD: Sollumz **LOD Tools → Generate LODs** (decimation 0.6); props only HIGH LOD.

## Leaves

| wanted | file | status — source |
|---|---|---|
| Adding freemode clothing / moving it to 98 bones / scaling | freemode-clothing.md | video — notes/03 §2, §4-7 |
| Ped prop — hat, glasses, headset | ped-prop.md | video — notes/03 §8-9 · sollumz-discord §4 |
| Texture / colour variant / skintone | texture-variants.md | video — notes/03 §3-4 |
| Cape / skirt / veil — fabric that flows with the character (`.yld`) | ped-cloth.md | Sollumz source + vanilla csb_bride dump (2026-09) |

## Trunk files to read
- `trunk/tool-pitfalls.md` §1 (Mesh Domain, embedded texture, `hide_select`), §4 (`-PathFilter`, `-LiteralPath`)
- `trunk/verification-ladder.md` — `.ydd` export size and embedded texture check
- `trunk/bone-tags.md` §4 ped bones
- Clothing texture colour/detail procedure and the ped DLC template (`customped.zip`) → `sources/community-resources.md` §9, §12 — **source note, not a rule.**
