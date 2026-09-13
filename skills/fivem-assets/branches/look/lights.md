# Light — read/edit/write back a prop's light, TimeFlags, Flashiness, gobo (projection)

**When to read:** "my lamp is dim / does not light up / does not flicker"; read, edit or write back a prop's light; add a light; the cone is too wide, cone angle; TimeFlags, Flashiness, corona, culling plane; a projected light (gobo); light export from Blender.
**Source:** `lights.md` reading/gobo/flicker/export sections · `decal.md` §4, §9, Flashiness · the former `/look` command (2026-08/09) · **Measured:** 72,539 vanilla embedded lights (`lights.tsv.gz`); a set with 36 projected lights in game
**Read first:** `_branch.md` · trunk › `trunk/tool-pitfalls.md` §1-2

---



User's query: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

**Every** light job goes through this command: "my lamp is too dim", "the light
does not come on", "the cone is too wide", "add a light to my prop", "at what hour does this
light come on". Use it whenever lights come up, even if the user does not type `/look`.

## In order

**1. READ first — do not copy the magic number, decode it.**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <file>
```

`TimeFlags 14680095` is not a number; it means "on between 21:00 and 05:00".
Summarize the output for the user in a sentence or two: how many lights, their type, which hours,
any warnings.

**2. Propose a value against the MEASURED RANGE.**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light --table
```

The `p05 / median / p95` band computed from 72,539 vanilla lights. When proposing a value,
do not say "I think 20" — give that field's vanilla median and band,
and say where your proposal falls in the band. If the layer is not installed,
**do not make up a range**; say that you cannot give a reference.

**3. Write back and VERIFY.**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <file> --apply edits.json
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <file> --set 0.Intensity=8 --set 0.ConeOuterAngle=35
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <file> --add
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <file> --remove 1
```

Every write keeps the original as `<name>.yedek` (the backup) and verifies the result **by reading
it back**. If verification fails, the file does not change.

## A darkness complaint has three layers — check them in order

The answer is usually not in the prop's light:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" cycle w_clear --hour 20   # 1. base weather
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" timecycle --mlo <ytyp>    # 2. the room's modifier
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <file>             # 3. the prop's light
```

## When presenting the result

- **Decode every magic number.** `TimeFlags`, `Flags` — do not repeat the number,
  say what it means (`assetdb.py flags <number>`).
- **A light is bound to a bone.** If `BoneId` is not zero, the light is not at the model's
  origin but on that bone; describe its position accordingly.
- **Call out an hour mismatch.** If the user says "it does not light up", look at
  `TimeFlags` first — in most cases the light is fine and the hours are wrong.
- If the `cycle` layer is not installed, suggest `build_cycle.ps1` — **do not make it up**.

Full math, the three timecycle layers and the silent failure catalog:
`light-math.md`


---

## Measured, not guessed

**Every** light job starts here.

```bash
assetdb.py light prop_lamp.ydr              # read and DECODE (open up the magic numbers)
assetdb.py light prop_lamp.ydr --table      # measured band of 72,539 vanilla lights
assetdb.py light prop_lamp.ydr --apply edits.json
assetdb.py light prop_lamp.ydr --set 0.Intensity=8 --set 0.ConeOuterAngle=35
assetdb.py light prop_lamp.ydr --add | --remove 1
assetdb.py cycle w_clear --hour 20          # base layer of the weather cycle
assetdb.py timecycle int_hospital_dark      # the room's modifier
```

Writing back is a `res_to_xml → XML → xml_to_res` round trip, and every write is verified
**by reading it back**. When proposing a value use the measured band from `--table`
(p05 / median / p95 per field); if the layer is not installed, **do not make up** a range.

Measured, not guessed:

- **A light is bound to a bone.** In `prop_worklight_01a`, `BoneId 41615` sits
  **1.737 m** up the chain; if the bone chain is not applied, the light stays on the ground.
  `Position/Direction/Tangent` **are in bone space**, not at the model origin.
- **`TimeFlags` is not a number but a set of hours.** `14680095` = 21:00–05:00;
  at hour 20 the light is **off**. For a "does not light up" complaint this is the first place to look —
  in most cases the light is fine and the hours are wrong.
- **Size is not a validity criterion** (RSC7 is zlib): 15,056 → 15,904 bytes
  is the same content. The only criterion is **the read-back**; `--apply` always reads
  back and does not write if the light count does not match.

- **`Flashiness` (flicker) is not documented anywhere**; it was read from the distribution of 72,539 lights:
  **15** alarm · **17** tunnel · **9** emergency · **19** damaged ship
  (68,036 of them are 0). ⚠️ The vanilla prop named "broken light" has flashiness
  **0** — GTA makes "broken" with the model, not with flicker.
- **An emissive panel has no light** — the brightness is in `emissiveMultiplier`, and
  the panels in a room **share one geometry**; to break one you must split the
  geometry. Emissive geometry **cannot flicker**.
- **REGISTER your own timecycle modifier with `data_file 'TIMECYCLEMOD_FILE'`** —
  without registration the game never looks for it. Do not touch a shared vanilla modifier
  (`morgue_dark` is defined in 6 DLCs; which one wins cannot be read from the data).

Full math + the three timecycle layers: `lights.md`
Light/timecycle/emissive field findings: `decal.md`

## Reading and writing back a light — without going in game

```bash
assetdb.py light prop_lamp.ydr              # read + decode the magic numbers
assetdb.py light prop_lamp.ydr --apply edits.json
assetdb.py light prop_lamp.ydr --set 0.Intensity=8 --add --remove 1
```

The pipeline has two parts, and both were measured:

| part | what it does | file |
|---|---|---|
| decode | `.ydr/.yft` → mesh + bone world matrices + lights with 40 fields | `light_scene.py` |
| write back | `res_to_xml → XML → xml_to_res`, then **read back** | `light_edit.py` |

The measured vanilla distribution comes in live through `light.reference()`
(`data/lights.tsv.gz`; in this install 72,539 lights / 4,476 files):
`p05 / median / p95 / min / max` for every numeric field. Without the layer
**no range is made up**, and no reference is offered at all.

### Three silent bindings

- **A light is bound to a bone.** `prop_worklight_01a` → `BoneId 41615`
  (`Worklight_01A_Bulb`), **1.737 m** up the chain; the light's own
  `Position` (0, −0.015, 0.009) sits **on top of** that → world
  (0, −0.102, 1.746). If the bone chain is not built, the light stays on the ground and
  people say "my light is in the wrong place". Vertices are in bone space too when `HasSkin=1`
  (on a prop the weight is 100% on one bone, i.e. rigid).
- **`TimeFlags` is not a number but a set of hours.** `14680095` = `0xE0001F`
  → bits 0–4 and 21–23 = **8 hours**, 21:00–05:00. At hour 20 the light is **off**.
  When the user says "my light does not come on", the first place to look is not the light
  itself but the hours. A preview that does not apply this shows it bright in the tool,
  and it comes out dark in game.
- **Size is NOT a validity criterion.** The same content came out 15,056 → 15,904 bytes
  (RSC7 zlib). The only criterion is the read-back; after writing, `--apply` decodes
  the file again, errors out if the light count does not match, and keeps the original
  as `.yedek`.

### Origin

It is an independent implementation. The math is derived from the game's own shader files
(`lighting_common.fxh`, `common.fxh`, `postfx.fx`) and verified by measurement;
the reference bands are computed locally from the user's own install and
are not distributed (`data/` is gitignored). It contains **no** code, assets, interface, names
or branding of any third-party editing tool.

### When building a preview — state its limit up front

Any preview built with this math is **not a render**. Deliberately
left out: **texture** (albedo is a single number), **corona sprite**,
**volumetric beam**, the deferred pass's **SSAO/reflection**. The question it answers is
"where does the light fall and how much", not "the scene will look exactly like this".

Shadows differ too: the game stores **distance** from a virtual sun position. A preview built on a
depth map can keep the lesson (the normal offset does the heavy lifting,
bias scales with the texel's world size), but its storage is different.

This math was verified once by measurement (by reading pixels, **not** by looking at a
screenshot): hour 12 → `[107,109,110]`,
17 → `[93,95,96]`, 20 → `[14,19,32]`, 06 → `[20,30,38]` — a physically plausible
progression through the day.

---

## 4. EDITING LIGHTS

Lights are not in script but **in the `.ydr`'s own light array**. Editing the model and
putting it in `stream/` under the same name = override.

### First place to look: TimeFlags
`16777215` = 24/24 (every hour). The second most common value in vanilla is `14680191`
= 21:00–07:00. **The most common cause of "the light does not come on" is the hour window**,
not the light itself.

### Flashiness — its meaning is documented nowhere, it was read from the distribution
72,539 vanilla lights scanned, **68,036 = 0** (constant). The non-zero ones and
the models that use them:

| Value | Count | Models using it (hint) |
|---|---|---|
| 15 | 1096 | `v_med_cor_alarmlight`, `xm_prop_x17_sub_alarm_lamp` — red 255,5,0 **alarm** |
| 17 | 693 | `cs2_30_tunnel_det_*` — tunnel lamps |
| 11/12/13 | ~1400 | casino arcade, cinema — cycles |
| 9 | 344 | `prop_ld_alarm_alert`, `v_48_emerg_light_a` — **emergency** |
| 19 | 172 | `gr_prop_damship_01a` (**damaged ship**) |
| 20 | 39 | `ba_prop_battle_lights_fx_rige` — strobe |
| 14 | 22 | `v_73_elev_sec*` — elevator |

⚠️ **`h4_int_club_broken_light` ("broken light") has flashiness = 0.** So GTA
makes the "broken" look **with the model**, not with flashiness.

### Vanilla band (72,539 lights)
`Intensity` p05 0.25 · median 6 · p95 32 — outside the band does not mean an error, it means **rare**.

### A light is bound to a bone
`Position` **is in bone space**, not at the model origin. If `BoneId=0`, it is
the object's own space (most static props are like this).

---

## ⛔ A single Flashiness = fake. Spread the flicker through TYPE variety

In GTA the flicker **phase cannot be set**; only the **type** is chosen. Giving all
lights the same value (measured: 232/232 `ELECTRIC`) switches them all on and off in the same
pattern, and because it looks synchronized it looks fake.

Fix: assign each light a type from a pool with a **deterministic hash derived from its position**
— neighboring lights get different types, and because their periods differ
they drift apart over time. The weights used in the morgue:

`ELECTRIC 30` · `RANDOM 20` · `RANDOM_FLASHINESS 12` · **`CONSTANT 12`** ·
`ONCE_PER_SECOND 8` · `TWICE_PER_SECOND 7` · `THRESHOLD 6` · `CYCLE_1 3` ·
`CANDLE 2`

⛔ **Do not make them all flicker.** If some do not stay `CONSTANT`, the place becomes a disco;
the feel of a broken facility comes from the **mix** of working and broken lights.
Alarm lamps do not go into the pool; they have their own type (`ALARM`).

The script is not in the repository.

**Two PowerShell pitfalls showed up here too:**
- `(,19) * 30` does not build a weighted pool — it does not produce the expected repetition
  (measured: ELECTRIC 0.9% instead of 30%). Use an explicit loop.
- `-bxor`/`-band` do not keep unsigned types; the intermediate result falls to Int64, turns
  negative and blows up when cast back to `[uint64]`. Instead of bit operations use
  djb2 + modulo.

## ⛔ "Flicker does not work" — look at `Intensity` first, not `Flashiness`

Measured (morgue): **all 232 deployed lights had `Intensity = 0`**. In the vanilla copies of the
same models the values are between **0.58 and 32**. So every light on the
map was dead and the visible brightness came **entirely from the emissive
material**.

That alone explains why `Flashiness` did nothing:
**there was no light to flicker.** And emissive geometry cannot flicker — flicker is a
light property. Setting `Flashiness` to ELECTRIC, then varying it:
both led nowhere, because the problem was never there.

**The diagnosis order should be:**

1. Is `Intensity` > 0? If it is zero there is no light, and the rest is meaningless.
2. Do the `TimeFlags` cover that hour? (`14680095` = 21:00–05:00)
3. Is `Flashiness` the right type?
4. Does the visible brightness come from the light or **from the emissive**?

The fourth is sneaky: an emissive ceiling panel glows without a light too,
so "the lights are on" seems true. The cheap way to tell them apart is to compare
`Intensity` with the vanilla copy of the same model.

### When bringing lights back on a darkened map

Do not put the vanilla intensity back **one to one** — if the map was darkened on purpose,
it returns to vanilla brightness. Scale while keeping the ratio (in the morgue **0.30×**;
232 lights, result 0.12–9.6, mean 6.0).

And **turn the emissive down in the same round**, otherwise the total brightness goes up: while
adding light, lower the panel's own brightness; the net illumination stays the same, but
now there is a real light pool and flicker. Applied in the morgue:
`mh_v_downlight01_d` **8 → 3** (ceiling spot) · `my_flo_working_d`
**3 → 1.6** (working fluorescent) · the broken ones are already 0.

## Projected light (gobo) — built with Sollumz

A pattern falling on the floor does not come from the material; it comes from the light's
**projected texture** field. Measured end to end on a set of 36 lights;
all six issues produced a wrong result **without an error**.

### `Tangent` = the projection's UP axis, not `Direction`

⛔ The engine takes `Tangent` as the projection's *up* axis; **Sollumz writes the light
object's local X (the RIGHT axis) there.** They are exactly 90° apart, and the texture
lies on its side around the beam axis — the patch of tall arched windows stretches
sideways on the floor.

Fix: rotate the light **−90°** around its own beam axis. Blender's euler is
XYZ (`Rz@Ry@Rx`), so this roll cannot be written as an euler; derive it from a matrix:

```python
# egim = tilt angle in degrees
lo.rotation_euler = (Matrix.Rotation(radians(-(90 - egim)), 3, 'X')
                     @ Matrix.Rotation(radians(-90.0), 3, 'Z')).to_euler()
```

`+90` also gives the right axis, but **with the opposite sign** — the pattern ends up rotated 180°.
Criterion: `dot(Direction, Tangent) == 0` **and** `Tangent.z > 0`.

### The light's transform gets wiped while the mesh transforms are reset

⛔ In drawable generation the transform is baked into the geometry, so the meshes are pulled
to the origin. If the light is in the same collection **it is reset too**, and the `.ydr`
gets `Position (0,0,0)`, `Direction (0,0,-1)`: the beam points straight down at the foot of
the window. Tilt/cone settings look right in Blender,
**and vanish on export** — so changing a setting changes nothing
in game.

Keep the light out of the reset loop, and rebuild its position relative to the opening.

### The criterion is the READ-BACK, not a calculation

Calculating the distance from the scene misleads: the value in the scene can be right and the one
in the file wrong. Read the deployed file with `assetdb.py light <ydr>`.

```
direction  (0.000, 0.000, -1.000)   ← broken (straight down)
position   (0.000, 0.000,  0.000)   ← broken (at the origin)
```

### The gobo texture itself

- ⛔ **Keep the aspect ratio.** Squeezing the content into a square destroys the silhouette:
  the tall arch gets squat and looks round, the round window stays the same —
  in game it is seen as "the round ones pointed, the pointed ones round". Criterion:
  the gobo's width/height ratio must follow the window's ratio (gothic ≈ 0.49,
  rose = 1.00). If all of them are 1.00, the silhouette is gone.
- ⛔ **The spot cone is circular, the texture is square.** The texture's empty corners become
  pointed spikes in the projection (the rose window lands on the floor as an octagon). A circular vignette
  is required; criterion: corner brightness **0**.
- The content must fit in the cone's **inner circle** (≈ 80%), otherwise the tip of the arch is clipped.
- A gobo is **not** a sharp copy of the glass: vanilla `os_stainglasswindow1_light.dds`
  is a heavily blurred, glowing, low-contrast glow; no lead lines.
  A sharp mosaic copy, once projected, makes the pattern unreadable.
- The texture must be **DXT1 + mip**. Without PIL, writing DXT1 with numpy is 60 lines:
  4×4 blocks, two RGB565 endpoints from the ends of the principal axis, 2-bit indices.

### If the light does not show, check in order

1. **`time_flags`** — the default is `total = 0`, i.e. **no hour is on**
   and the light never comes on at any time of day. 24/24 = **16777215**
   (45,770 of the 72,539 vanilla lights use this). *For a light-does-not-come-on complaint
   this is the first place to look, not the light itself.*
2. **Archetype `<textureDictionary>`** — the projection texture ships in a `.ytd` with the same
   name as the drawable; if the archetype does not reference it, the game **never loads**
   that dictionary. The light "works", there is no pattern. (Once this was taken for a
   power problem and `intensity` went 6 → 15; power was not the cause.)
3. **Cone angles are RADIANS** — writing `cone_outer_angle = 45` means 45 radians,
   clamped to π/2; `40` becomes **0**.
4. **`static_shadows`** — if the light is behind the glass and shadows are on,
   frame + glass block their own beam, and a dark silhouette of the window falls in the middle
   of the patch. In vanilla 53% of projected lights have no shadow flag;
   turning it off is legitimate.

### Placement geometry

If the beam goes horizontal it never hits the floor. As the tilt gets smaller the patch moves away **and**
stretches; as it gets larger it comes closer and the silhouette is kept.

| tilt | patch center | length | readability |
|---|---|---|---|
| 30° | 4.0 m | ~12 m | silhouette falls apart |
| 48° | 2.0 m | 1.9 m | **balanced** |
| 61° | 1.2 m | 2.3 m | almost at the foot |

The tilt must be **larger** than the content's half-angle; otherwise the top edge of the cone
points upward and that part never touches the floor.

---

## Light export from Blender — three measured bindings

Source: Sollumz 5.2, `ydr/lights.py`, `ydr/properties.py`. All three are silent.

### ⛔ 1. A hidden light is NOT DROPPED from export; its position breaks

`export_lights()` walks **`parent_obj.children_recursive`** — it never looks at
visibility. But the position is computed by this line (`lights.py:159`):

```python
mat = root_mat.inverted() @ light_obj.matrix_world
```

If an object's `hide_viewport` is `True`, Blender takes it out of the depsgraph and
**`matrix_world` stays zero** — `view_layer.update()` and
`evaluated_depsgraph_get()` do not fix it either, because the object is never evaluated.
With zero going in, the result is the same for every light: **`−root`**.

So the symptom is not "the light disappeared" but **"all the lights gathered at one
point"**. Measured: the 4 lights of `v_2_cor1_mesh_delta2` collapsed to
`(0.056, −11.953, 7.958)`; the drawable root is `(−0.056, 11.953, −7.958)` —
exactly the negative. This is the **signature** of the diagnosis: if the collapse point is
the negative of the root, this is certainly the cause.

- **Do NOT HIDE a light to switch it off.** Write `intensity = 0` + `flashiness = OFF`.
- Gate: a check step that stops deployment when all the lights in a file sit at one point
  (script not in the repository). Verified with a negative test.

### ⛔ 2. `light_properties.intensity` is NOT a stored field — it is a proxy of `energy`

`properties.py:346`:

```python
def get(self): return self.id_data.energy / LIGHT_INTENSITY_SCALE_FACTOR   # 500
def set(self, v):     self.id_data.energy = v * LIGHT_INTENSITY_SCALE_FACTOR
```

So `energy = intensity × 500`. Writing `light.data.energy` for a preview
**divides intensity by 500**, and export carries that divided value. This happened:
the intensity of 232 lights went 1.6 → 0.0032, with no error at all.
**Write only `intensity`; do not touch `energy` by hand.**

### ⛔ 3. A bone-bound light's position is in BONE space

`lights.py:151-159` — if the light has a bone binding:

```python
root_mat = parent.matrix_world @ bone.matrix_local
bone_id  = bone.bone_properties.tag
```

Comparing the position in drawable space gives a fake deviation as large as the bone offset.
Measured: the rotating `V_Med_Cor_alarmLightSpin` bone of `v_med_cor_alarmlight`
(tag **36848**) is local `(0.0007, 0.0006, −0.0438)`; the light's position in drawable space
looked exactly **4.4 cm** off the server value, yet it was right. Trying to
"fix" the light from the fake deviation produces the real error.

⚠️ **The binding is `COPY_TRANSFORMS`, NOT `CHILD_OF`.** Sollumz changed it after 4.2
(`blenderhelper.py:297`, the reason is written in the code). A scan looking for `CHILD_OF`
says "no bone binding" and produces a **false negative** — this also
happened. Because the constraint is `owner_space=LOCAL`, the light's `location` field
**is already in bone space**; the import also writes the raw `light.position` there.

### Verification: do not look at the file, imitate the export formula

The only way to know whether Blender produced the deployed file is to run a formula that applies
all three rules inside Blender and compare it with the values read from the `.ydr`.
Criterion: position deviation < 1 mm, `bone_id` identical,
`intensity`/`falloff`/color/`flashiness`/`time_flags` deviation 0.
(In the morgue the maximum deviation over 225 lights was measured at **0.00008 m** — what is left
is entirely 4-digit rounding in the dump.)

### The safe way to hide a light — three icons, one is safe

Wanting "the rest out of sight" while editing lights is natural. But the choice of hiding method
can bring back the collapse from §1. Measured (save → `revert_mainfile`
→ compare positions, 8 samples, 5 of them hidden):

| method | in Blender | safe? |
|---|---|---|
| `layer_collection.hide_viewport` | the collection's **eye** icon | ✅ **yes** — after reload, 8/8 lights kept their position exactly |
| `collection.hide_viewport` | the collection's **monitor** icon | ⛔ do not use — the class that takes the object out of the depsgraph |
| `layer_collection.exclude` | the collection's **checkbox** | ⛔ do not use — same class |
| `object.hide_viewport` | the object's **monitor** icon | ⛔ **this is the cause of the collapse** |

⚠️ **Toggling within a session does NOT PRODUCE this error** — once `matrix_world` has been
computed it stays in the cache; switching the icon off and on does not reset it.
The collapse appears only when the file is **saved with a hidden light and reopened**
(the matrix is never computed). So "I tried it, it did not break" is not proof;
the measurement is done with a **save + reload** round.

**Moving collections does not affect export.** Sollumz collects the drawable from the object
hierarchy (`children_recursive`), not from collections — moving lights into
your own category does not break the parent link (measured: 140 lights moved,
0 detached from the hierarchy). But if a light stays in **no** visible collection,
it drops out of the view layer, and then you are back at §1.

---

## 9. TOOL BUGS — FIXED

### `light_scene.read_scene` crashed on a drawable without a skeleton
In the `bones is None` case it returned `return [], {}`, but the callers
expect `kmap["tag"]` / `kmap["idx"]` → `KeyError: 'idx'`, and the error surfaced as
*"INTERNAL ERROR"*, hiding its cause. **Most static props have no
skeleton** — so light editing never worked on those files.
→ `return [], {"tag": {}, "idx": {}}`

### Void Tools Shadow Map could not post-process in Blender 5.x
Three separate API breaks (see §3e), all falling into one `try/except` and swallowed with a
single-line warning; the user got the **raw bake**.
→ The helpers `_make_compositor_tree`, `_link_compositor_output`, `_set_node_option`
were added; it works on 4.x and 5.x alike.

## Shadowmap (community)

- ⚠️ **Shadowmap: two separate methods, do not mix them.** The old method uses Blender's
  **Shadow *render pass*** and, because that was removed, needs **Blender 3.3**;
  the new method uses **bake type = Shadow**, so it works in current Blender.
