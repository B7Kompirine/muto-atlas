# Put your own prop / drawable into an MLO (new entity)

**When to read:** adding your own prop or drawable into an MLO as a new entity (box, door, animated deposit box); your own mesh is black/invisible in the MLO; room assignment; two MLO versions.
**Source:** former MLO prop pipeline + MLO drawable export findings references (2.5.0, in full, 2026-07/08) · **Measured:** Fleeca vault room 20 deposit boxes + 2 doors; `trees_normal.sps` A/B; v_coroner elevator cab
**Read first:** `branches/map/_branch.md` · trunk › `trunk/flags.md`, `trunk/tool-pitfalls.md`

---


The end-to-end pipeline built while placing 20 animated deposit boxes and two custom doors
in the Fleeca vault room. Every item was verified by in-game measurement.

**Read in order. Skip a step and it fails silently — this work gives no error,
just "nothing happens".**

---

## 0. DECIDE THIS FIRST

**Is the object inside an MLO interior or outside?** Everything depends on it.

| | **outside** the MLO | **inside** the MLO |
|---|---|---|
| your own ymap | ✅ | ❌ room/portal culls it, the object never appears |
| MLO entity list | — | ✅ the only way |
| script spawn | ⚠️ not a map object | ⚠️ same + a load on every client |

**The same interior can have more than one MLO version.** Fleeca has two:
`v_genbank` (`v_int_10.ytyp`) and `hei_generic_bank_dlc`
(`hei_dlc_generic_bank.ytyp`). Both share **the same MLO-local frame**
(the same prop sits at the same local coordinate in both) but their entity lists differ.
Patch one and skip the other, and nothing shows in the branch you test —
this happened once and was searched for in the wrong place for a long time.

---

## 1. REPLACING AN EXISTING OBJECT (model name swap)

The safest operation: the file size does not change, the MLO structure is not touched.

```
patch_vanilla_ytyp.ps1 -YtypName v_int_10.ytyp `
  -SwapEntity @('v_ilev_gb_teldr=my_teldr','v_ilev_gb_vauldr=my_vauldr') `
  -OutDir <...>\stream
```

- `data_file 'DLC_ITYP_REQUEST'` is **NOT ADDED** (vanilla file replacement).

## 2. ADDING A NEW ENTITY

```
add_mlo_entities.ps1 -YtypName v_int_10.ytyp -Mlo v_genbank `
  -Part v_10_gen_country_bank -Model my_depobox `
  -CellsJson <...>.json -Count 20 -Room bankvault -OutDir <...>\stream
```

Three things must be right at the same time; if one is missing the object is **invisible**:

| field | right | if wrong |
|---|---|---|
| `flags` | **18350080** (measured from a vanilla MLO entity) | ymap value `1572872` → the object is never created |
| `lodDist` | **-1** | — |
| **room** | an index must be added to `AttachedObjects` | **if not added, the object is never created and the MLO can break** |

Room assignment is the step most easily skipped: the entity shows in the `entities` array,
the ytyp loads fine, nothing appears in game.

**The coordinate must be MLO-LOCAL.** If there is part-local data, the chain is:
`panelLocal → (part pos/rot) → mloLocal`. If the reference part is not in the target MLO,
look for it in the other MLOs (both share the same frame).

## 3. PATCHES MUST STACK

If every script reads from the vanilla RPF, it **overwrites** the previous one. Real case: a door
swap was done, then boxes were added to the same ytyp and the doors went back
to vanilla. Both scripts now continue **from** the file in the output folder if
one exists.

---

## 4. BUILDING THE FRAGMENT

The one critical reminder here:

**The group with `parentIdx = 255` is the entity body and does NOT FOLLOW the bone.**
At least two groups are needed:

```
group[0]  fixed bone     parentIdx=255   → body / hinge
group[1]  moving         parentIdx=0     → turning part
```

What binds the bound to the bone is the **COPY_TRANSFORMS constraint** —
not `parent_bone`, not name matching.

### Static bit

If **32** is not added to the `flags` of a wall-mounted fragment, it **falls**
when the player touches it. `537526784` (animated fragment) + `32` = **537526816**.

---

## 5. YOUR OWN .ycd

Sollumz writes the `.ycd` as **XML** (it says "Successfully exported" but there is
no `.ycd` in the folder). Before converting to binary, add three things to the XML
**by hand** — Sollumz writes none of them:

```xml
<Clips><Item>
  <Hash>my_depobox_open</Hash>            ← clip hash
  <Name>pack:/my_depobox_open</Name>       ← pack:/ is NORMAL, do not touch
  <Tags /> <Properties />
  <AnimationHash>my_depobox_open</AnimationHash>
</Item></Clips>
<Animations><Item>
  <Hash>my_depobox_open</Hash>            ← ANIMATION hash
  <Unknown1C>hash_22E95D79</Unknown1C>      ← Sollumz writes hash_00000001
</Item></Animations>
```

Then:
```powershell
[CodeWalker.GameFiles.XmlMeta]::GetYcdData($doc)   # the path the GUI uses
```

**DO NOT USE `XmlYcd.GetYcd($doc).Save()`** — it goes into the object model,
and iterating `ClipDictionary.Clips` throws `NotImplementedException`.

### Verification (do not say "done" before you see this)

```
ClipMap = <joaat(clip)>     AnimMap = <joaat(clip)>
```

Both must be non-zero. If `AnimMap = 0`, `PlayEntityAnim` **returns true
but the bones do not move** — the most confusing symptom.

**Sollumz's output is not the same on every export.** Once it wrote
`<Hash>hash_00000000</Hash>` into the Animations block, another time it did not write the element
**at all**. A blind `replace` is not enough; read back every time and
verify `AnimMap`.

---

## 6. YTYP + EXPRESSION EXTENSION

Writing through the object model (`Archetype.Extensions`) **does not serialize**.
The way that holds is XML:

```powershell
[CodeWalker.GameFiles.XmlMeta]::GetData($doc, [MetaFormat]::RSC, "")
```

**There is no `ytyp`** in `MetaFormat` — a ytyp is an RSC meta.

Verification: `ext: MCExtensionDefExpression dict=<hash> name=<hash>`

---

## 7. CHOOSING THE ANIMATION — ped or prop?

**The bone count tells you:**

| bones | what |
|---|---|
| 44+32 (multi-track) | **ped** clip (body + facial) |
| 72 | usually a **prop** track (bag, tool) |
| 4-24 (single track) | prop track |

Real mistake: in the box robbery sequence I played `reward_p_m_bag_var22_arm_s_f`
(72 bones) on the ped — that is the **bag's** track. The character did not move at all.
The right ped clips were the multi-track ones: `enter` / `action` / `reward` /
`no_reward` / `rest_exit`.

Do not guess durations, read them with `assetdb.py anim <dict> --dict-only`.

### Ready-made sequences

- **Drilling a lockbox:** `anim@scripted@cbr5@ig3_drill_box@pattern_01@lockbox_01@male@`
  `enter 3.8 · action 8.0 · reward 4.57 · no_reward 4.10 · rest_exit 3.23`
  Drill prop: `ch_prop_vault_drill_01a`. **An empty-box variant is ready.**
- **Robbing a till/counter:** `oddjobs@shop_robbery@rob_till` (enter/loop/exit)

### Attaching the prop to a hand

`PH_R_Hand` (28422) may not resolve on every ped; when `GetPedBoneIndex` returns **-1**
the attach falls back to the root bone and the prop floats **in the air beside the body**.
Fallback: `SKEL_R_Hand` (57005). Offset and `rotationOrder` → `branches/prop/hand-attach.md`.

If the clip already takes the tool out of the bag, attach the prop **after the clip** —
otherwise two tools show.

### Synchronized scene clips need a position

These clips are made so that the ped's **position** relative to the object is fixed.
`TaskTurnPedToFaceCoord` alone is not enough; place the ped in front of the object with an offset.

**The FRONT of the object can be the BACK of the entity** — if the model's front face is at local `-Y`
(GTA entity forward is `+Y`), using `+forward` puts the player 90-180°
in the wrong place.

---

## 8. MISTAKES NOT TO REPEAT

All of them happened in this session and cost time.

### Asset / placement
1. **An object spawned by script is not a map object.** The door system
   cannot find it (the door fell through the floor), fragment collision does not follow
   the animation. And on a 60-player server it is a separate load on every client.
2. **A prop cannot be placed inside an MLO with a ymap.** Do not let a reference that uses a ymap
   mislead you — first check whether its prop is inside the MLO or outside.
3. **Do not forget to attach the entity to a room.** It is silently invisible.
4. **Do not give an MLO entity a ymap flag.** It is silently invisible.
5. **Do not skip the second MLO version of the same interior.**
6. **Fixing `specialAttribute` in the vanilla prop ytyp did not take** —
   the file was produced correctly but in-game physics did not load. The MLO entity swap
   worked.

### Tool behaviour
7. **CodeWalker cannot fully read `.yed`.** Seeing `ExprMap.Count == 0` does NOT
   MEAN "the file is empty" — it cannot write expression bytecode, it can only
   read it. Hours were lost thinking "`.yed` does not work" because of this.
   **A tool not showing something does not mean that thing does not exist.**
8. **Sollumz cannot produce binary `.ycd`/`.yed`/`.ymap`**, and when writing the `.ycd`
   as XML it says "Successfully exported".
11. **Escapes can break when a Lua file is written from Python.**
    `\n` turned into a real line break and split a Lua string; the file could not
    be parsed and **no command got registered**. `lua_check` shows the syntax
    clean, it does not catch a runtime error.
    → Write such lines directly with `Edit`.

### Logic
12. **Do not cache state, verify it continuously.** The same mistake was made in two places:
    the `doorRegistered[hash]` cache and the "did the entity handle change"
    comparison. FiveM can reuse a handle; if an animation fails once
    it is never tried again. The right way: ask **the reality**, e.g. `IsEntityPlayingAnim`.
13. **When you change the model name, update every config that looks for it.**
    `config/heists/fleeca.lua` was still looking for `v_ilev_gb_teldr`; when the door module
    could not recognise the door, the lock logic fell to the wrong side.
14. **"I fixed it, now it does not open at all" can be a false regression.**
    When the config points at the right name, the lock that had never worked until then kicks in
    for the first time. The door is locked by design.
15. **Single authority rule.** If two modules write state to the same object, the last writer
    wins. The lock was applied both through the door system and with `FreezeEntityPosition`;
    a frozen entity is not affected by the door system, so the door did not open
    even though `state=0` showed.
16. **When copying a reference, measure what actually does the work.** The reference having its own
    `.ycd` did not mean "a custom ycd is required"; the missing piece was `.yed` +
    the Expression extension. Once that was in place, the vanilla clip already worked.

### Test discipline
18. **Change one variable at a time.** If something does not work, break the chain
    into parts (take out the `.yed` / try a vanilla clip) — set up an A/B test that tells
    two completely different fixes apart in one test.
19. **Do not ask for a test before the whole chain is done.** A result from a half-built chain
    leads in the wrong direction.


---

# Putting your own drawable into an MLO — measured findings


Measured while building the `v_coroner` BodyStorage elevator scene. All of them are **silent**
failures: no error message, it says "successfully exported", the file is created, the result in game
is wrong.

Sibling notes: the entity/room pipeline in the first half of this file ·
`trunk/flags.md` (flags) · `branches/look/lights.md` (lights).

---

## 1. ⛔ `trees_normal.sps` RENDERS PITCH BLACK INDOORS

The most expensive finding. Put geometry with the `trees_normal` (or any other **foliage**)
shader into an MLO room and the model comes out **completely black**.

**Cause:** foliage shaders take their lighting from the **natural/sun** path. Inside an
MLO the natural ambient is near zero (`morgue_dark` 0.154, the `my_mlo_dark` derived from it
**0.045**), and the artificial ambient (0.300) is not read
by foliage → no light → black.

**Fix:** for interior geometry use `normal.sps` / `normal_spec.sps`
(render bucket 0). Use `trees_normal` only outdoors.

**THE COST — pay it knowingly:** the vertex wind of `trees_normal`
(`WindGlobalParams`, `Color 2`.B mask) goes too. **Indoors there is NO free way
to make “a net/fibres sway in the wind”.** If motion is wanted,
it needs a `.yed` expression chain or RayFire.

### Ruled out before the cause was found (all correct, none of them the cause)

Do not walk the same path again — these six were measured and came out clean:

| check | measured |
|---|---|
| embedded texture present | 2 textures, 1024 DXT1 ✓ |
| `DiffuseSampler` bound | bound to the right name, present in the dictionary ✓ |
| vertex color | `Colour0 = 255,255,255,255` ✓ |
| normals | real surface normals ✓ |
| `UseTreeNormals` | already **0** (the first theory, disproved) ✓ |
| UV / tangent | present ✓ |

### Diagnosis method: A/B in the same room

Change the shader of one layer, leave the other **on `trees_normal` as the control
group**, look at the same frame. In our case our layers got colour, the
control stayed black → the cause was confirmed. Saying "it is the shader" without a
single-variable test is a guess.

---

## 2. ⛔ IF A RESOURCE IS IN TWO PLACES, FiveM SILENTLY IGNORES ONE

If a resource with the same name exists in two folders, only one loads, and everything done to
the other **goes in the bin**. The warning is **only in the server log**; there is no
symptom in game:

```
Warning: my-resource exists in more than one place
([maps]\my-resource is used, the duplicate is [script]\my-resource)
```

**Rule: when "it does not show in game" is reported, THE FIRST PLACE TO LOOK IS THE SERVER LOG**,
`txData/default/logs/fxserver.log`. Look there before writing a diagnostic script or tinkering
with assets. This cost a round.

The second warning from the same log is a real risk too:

```
Asset X.ydr uses 64.0 MiB of physical memory. Oversized assets can and
WILL lead to streaming issues (such as models not loading/rendering).
```

A 4096 DXT5 texture triggers it. Dropping to 2048 cuts it by 4x
(measured: `.ydr` 5.35 MB → 1.85 MB, 64 MiB → ~16 MiB).

---

## 3. Sollumz export pitfalls

### ⛔ `use_custom_settings=False` IGNORES THE ARGUMENTS YOU PASS

In a `bpy.ops.sollumz.export_assets(...)` call this flag **defaults to False**,
and in that state the operator **does not use** the arguments you passed, it uses the scene's own
export settings. Measured result: although `limit_to_selected=True` was passed,
**the whole scene** (170+ drawables, 19 s) was exported, and
`target_versions={'GEN8'}` was ignored and the output was spread into `gen8/` + `gen9/`
**subfolders**. With `use_custom_settings=True`: 5 files, 1.2 s.

### ⛔ Texture `embedded` flag + PNG cannot be embedded

If `n.texture_properties.embedded` is **False** on the Sollumz texture node, the texture
is **never written** into the `.ydr`; export does not warn. Symptom: on read back
`TextureDictionary` is empty, the model has no texture in game.

Turn the flag on and the second gate comes:
`WARNING: Embedded texture '...' is not in DDS format.` — **a PNG cannot be embedded.**
Convert to DDS with `texconv -f DXT1 -m 0` (a mip chain is required).
The texture name is **derived from the file name**, so keep the file name.

### ⛔ `hide_select` SILENTLY drops `select_set()`

If an object or collection has `hide_select=True`, `select_set(True)` gives no error,
the selection **stays empty** and export says `No Sollumz objects selected!`. The object
is visible — you cannot tell by eye. `hide_select` can be on while `hide_viewport` / `hide_get()`
look clean; check all three.

### ⛔ If `sz_lods.high.mesh` is not set the drawable is skipped ENTIRELY

On mesh objects created by script this field stays `None` and export
says "has no Sollumz materials!" — the material is actually there.
`ob.sz_lods.high.mesh = ob.data`.

### ⛔ Every drawable must have `Color 1`

The engine gates natural/artificial ambient with the `.r`/`.g` channels of the vertex color,
and `decal.sps` reads its blend factor from the alpha. A mesh from OBJ has **no such
layer at all**. Write `(1,1,1,1)` — and use **`.color_srgb`**, not `.color`
(`.color` decodes gamma).

---

## 4. ⛔ DO NOT RESET the transform, BAKE IT INTO THE DATA

If you build the geometry in MLO-local world coordinates, the layers' transform
is already identity. But blindly setting `matrix_basis = Identity` on a **placed** object
(one that carries position + rotation) **teleports it to the origin**.

Measured: a corpse with bbMin `(15.94, 36.55, −9.28)` became
`(−0.408, −0.083, −0.506)` after the reset — 40 m away, invisible in game.

```python
if c.matrix_world != Matrix.Identity(4):
    c.data.transform(c.matrix_world)     # BAKE into the data
c.matrix_basis = Matrix.Identity(4)
```

⛔ Do not trust the `bpy.ops.object.transform_apply` operator — it may silently do
nothing.

---

## 5. ⛔ `view_layer.update()` before reading `matrix_world`

If `matrix_world` is read after assigning a parent / creating an object without updating the
depsgraph, it returns a **stale value**. In this session it led to a wrong diagnosis
twice: the lights showed at `(0,0,0)`, the corpse at `(27, 75, −18)` —
both were actually in the right place.

---

## 6. ⛔ DO NOT MAKE UP COORDINATES — they are in the database

If you need a world coordinate, do not guess:

```
assetdb.py where <model>      # world position (MLO interiors included)
assetdb.py near <x> <y> <z>   # what is around it
```

Measured: the elevator `v_2_bds_mesh_lift` → `vec3(286.05, −1350.90, 24.94)`.
The made-up value was 55 m away and needlessly raised the question "am I looking in the
wrong place".

---

## 7. ytyp OVERRIDE pattern and its verification

To change the MLO's own ytyp, put it in `stream/` **with the same name**.
⛔ `data_file 'DLC_ITYP_REQUEST'` is **NOT ADDED** — it registers twice.
(If you produce a new ytyp, add it; in an override, do not.)

### Patches must stack

Every build must read **from the previous output**, not from vanilla. In this session the live
ytyp (88 archetypes / 585 entities / `attachedObjects` 20) was decoded and verified,
then built on top of (93 / 590 / 25). The size difference (25,758 vs 25,901 bytes)
is **not a content difference**, it is PSO packing variance — do not look at the size and say "different
file".

### Reading/writing `.ytyp`

`xml_to_res.ps1` **does not support `.ytyp`** ("unsupported extension") and
CodeWalker.Core has **no** `XmlYtyp` type. The right way is `build_ytyp.ps1`
(the general `XmlMeta` importer). Read back:

```powershell
$y = New-Object CodeWalker.GameFiles.YtypFile
$y.Load($bytes)        # SINGLE-argument overload — does NOT need RpfFileEntry
```

⛔ Calling it as `Load($bytes, $rpfEntry)` **blows up** on a `.ytyp` and the file is taken
for broken. The reverse holds for `.ypt` (it needs `RpfFileEntry`) — do not
mix them up.

---

## 8. ⛔ A WRONG TEST PRODUCES A "NOT THERE" RESULT — happened three times

If you write a verification without accounting for the limits of the tool/format, you think something is "missing":

| test written | returned | reality |
|---|---|---|
| `.//Texture/Name` XPath | empty | the texture name is under `Item/Name`, **there were 3 textures** |
| string search in a binary file | not found | the ytyp stores `timecycleName` as a **hash** |
| `YtypFile.Load($d, $null)` | "Value cannot be null" | wrong overload, the file was fine |

**Rule (the catalogue's general rule):** *a tool not showing something does not mean
that thing does not exist.* Audit the measuring tool too.

Also: **a Blender path is relative, like `//x.dds`**; on Windows
`os.path.basename('//x.dds')` takes it for a UNC root and returns an **empty string**.
Resolve it with `bpy.path.abspath()`.

---

## 9. Measured elevator cab (v_coroner BodyStorage)

MLO-local coordinates, measured with a ray grid:

| surface | position |
|---|---|
| left / right wall | x = 14.485 / 18.212 |
| wire cage (back) | y = **35.196** — `ah_meshfence1`, a single plane, 2 faces |
| solid wall | y = 35.12 → **7.6 cm** between it and the cage |
| front (open mouth) | y ≈ 38.10 |
| floor / ceiling | z = −9.707 / −6.920 |
| outside the room mouth | ceiling −6.51 · floor −9.70 · wall x 13.44 / 25.86 |

⛔ **The elevator has NO light of its own:** `v_2_bds_mesh_lift.ydr` has a `<Lights>`
node **but it is empty**. Number of vanilla lights whose range reaches the cab, measured:
**0**. The lighting comes entirely from the lights you place.
