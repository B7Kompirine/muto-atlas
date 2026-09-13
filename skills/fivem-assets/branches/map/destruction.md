# Destruction / collapse / choreographed scene — RayFire `des_*`

**When to read:** destruction, collapse or a choreographed scene — a building, bridge, road, tower or scaffold should come down; "intact → animated collapse → debris"; permanent debris after an explosion; collision that moves with the choreography; RayFire `des_*` composites.
**Source:** the former RayFire reference (2.5.0, in full, 2026-08/09) · **Measured:** vanilla `des_stilthouse` field by field; `des_mytest`, `des_crane`, `des_bridge` in game
**Read first:** `branches/map/_branch.md` · trunk › `trunk/flags.md`, `trunk/tool-pitfalls.md`

---

⛔ **Path choice first:** this leaf is for the collapse of a building/tower/road/bridge. A single prop's lid/lever, or an engine-driven mover (clock, barrier), is a different recipe and is not in this version. A hybrid of the two recipes never worked.


**When:** a **choreographed** destruction of a building, tower, tree,
scaffold or any other map structure is wanted. NOT fragment breaking
(`prop_*` glass/wood shattering) — that is a different system. The system here
is the trio "intact state → played collapse animation → debris state".

Source: vanilla `des_stilthouse` was opened **field by field** (ytyp, ycd, 8 ydr,
3 ymap, 6 ybn, placer ymap), and an exact copy (`des_mytest`) was
built and verified working in game. None of the numbers here are
guesses. Cross-checked against: `des_protree`, `des_apartmentblock`,
`des_tvsmash`, `des_farmhouse`.

Query: `assetdb.py search des_` · `res_to_xml.ps1`

---

## 1. Mental model: a composite is not an OBJECT, it is a DIRECTOR

There **is no** archetype called `des_X`. What exists is a second
block inside the `.ytyp` — `compositeEntityTypes` — and that block tells the engine:

| field | meaning |
|---|---|
| `StartImapFile` | the ymap holding the intact state |
| `EndImapFile` | the ymap holding the debris state |
| `Animations[i].AnimatedModel` | the drawable **the engine creates** during the collapse |
| `Animations[i].AnimDict` / `AnimName` | the clip played on that drawable |
| `punchInPhase` / `punchOutPhase` | the phase range of the clip that is played (vanilla 0 → 1) |

When triggered, the engine's order:

1. `StartImapFile` turns off → the intact building disappears
2. The drawable in `AnimatedModel` **is created by the engine**
3. The clip plays from `punchIn` to `punchOut`
4. The clip ends, the drawable is deleted, `EndImapFile` turns on → the debris appears

**Result: what you see is three separate assets, not one archetype.** The intact state is a separate
prop, the debris is a separate prop, the motion in between is a third drawable.
"Making one object both animated and with collision" is the wrong
question in this system and burns hours.

### ⛔ The animated drawable is in NO ymap

Measured: the 8 `rootN` archetypes of `des_stilthouse` appear as entities in **none** of the
`imapstart`, `imapend` and `rebuild` ymaps. The composite
creates them. Calling them by hand with `CreateObject` / `rfspawn` steps outside
the system, and what you see is no longer RayFire.

### The composite ITSELF is placed as an ordinary entity

The placer is a normal `CEntityDef` in a normal ymap, and
`archetypeName` = `joaat(composite name)`. Without this entity
`GetRayfireMapObject` finds nothing.

Vanilla (`ch2_09b_strm_1.ymap`, contentFlags 65):
```
archetypeName = des_stilthouse   flags 1572864   parentIndex -1
lodLevel LODTYPES_DEPTH_ORPHANHD   lodDist 100   priorityLevel PRI_REQUIRED
```

### There are two patterns — do not mix them

- **A · imap swap** (`des_stilthouse`, `des_protree`, `des_apartmentblock`):
  `StartModel`/`EndModel` **empty**, `StartImapFile`/`EndImapFile` filled.
  Building/structure destruction uses this.
- **B · model swap** (`des_tvsmash`): `StartModel`/`EndModel` filled.
  A debris prop replaces a single prop. It is for small interior items.

---

## 2. `.ytyp` — measured fields

### Animated root archetype (`des_X_root`)

```
assetType          ASSET_TYPE_DRAWABLE      <- .ydr, NOT A FRAGMENT
flags              536871424                = Has Anim(512) + Use Ambient Scale
lodDist            100
hdTextureDist      5
clipDictionary     <ytyp name>              (= composite name)
textureDictionary  <txd name>
drawableDictionary EMPTY
physicsDictionary  EMPTY                    <- no collision during the animation
specialAttribute   0
extensions         CExtensionDefParticleEffect (fxType 6) — dust/rubble, optional
```

**All** 8 root archetypes of `des_stilthouse` are exact copies of this template;
the only differences are the name, the box and the particle count.

### `compositeEntityTypes` (single Item)

```
flags              536870912
lodDist            -1
specialAttribute   0
bsRadius           spherical radius of the structure (stilthouse 44.66)
StartModel/EndModel  EMPTY  (pattern A)
StartImapFile      des_X_imapstart
EndImapFile        des_X_imapend
PtFxAssetName      <.ypt name>  — EMPTY if there are no particles
Animations[N]:
   AnimDict        = ytyp name
   AnimName        = AnimatedModel = archetype name   <- ALL THREE THE SAME
   punchInPhase    0
   punchOutPhase   1
   effectsData     particle trigger list (between 0..19, optional)
```

In multi-part destruction there is more than one `Animations` entry (stilthouse 8) — each
drives its own drawable with its own clip, all play at the same time.

---

## 3. `.ydr` — how the mesh moves

**Rigid skinning.** A single `DrawableModel`, `HasSkin=1`, `BoneIndex=0`,
one bone per vertex:

```
Layout (GTAV1): Position, BlendWeights, BlendIndices, Normal, Colour0, TexCoord0
BlendWeights    0 0 255 0      <- 100% to a single bone
BlendIndices    0 0 20 0       <- index into the Geometry/BoneIDs palette
Unknown1        = bone count
Bounds          NONE           <- there is no collision during the animation
LodDistHigh     9998
FlagsHigh       15
```

### The bone hierarchy is FLAT

Measured: `des_stilthouse_root` has 102 bones, **the parent of all 101 others is 0**. No
chain. Bone[0] = `DES_StiltHouse_ROOT_bone`, `parent -1`, with `Unk0`
in its flags. Every part is locked to its own bone; wherever the bone goes, the part
goes. That is why weight painting, soft blending, Laplacian smoothing etc.
are **not needed** — and not wanted.

### `Tag`s are arbitrary

`des_stilthouse` tags are 0, 743, 3793, 4289, 16689, 17738… — neither ordered
nor produced by a formula. The only thing that matters is that the `.ycd` uses
the same numbers (§5 Link A).

---

## 4. `.ycd` — the measured contract

```
Clip:
  Hash            = archetype name         (des_stilthouse_root)
  Name            = pack:/<name>.clip      (SINGLE pack:/ prefix)
  Type            Animation
  Unknown30       1
  Tags            empty but PRESENT
  Properties      1 Item: NameHash hash_BF6A5D60 / UnkHash hash_996C3B27
                  Attributes: hash_BF6A5D60, Int, 32
  AnimationHash   = Hash
  StartTime 0 · EndTime (frames-1)/30 · Rate 1

Animation:
  Hash            = same as the clip Hash
  Unknown10       1
  FrameCount      579   (stilthouse)
  Duration        (frames-1)/30 = 19.266666
  BoneIds         bones x 3  — Track 0 (translation), 1 (rotation), 2 (scale), ALL
  SequenceFrameLimit 303 -> 579 frames split into 2 sequences (304 + 276)
```

- **Track 2 is not left empty.** Vanilla writes the scale channel explicitly with
  `StaticVector3(1,1,1)`. A channel that is not driven does not return to rest, it **stays in the pose
  of the previous animation**.
- **The sequence split must overlap by 1 frame**: `seq0 = limit+1`,
  `seq1 = total - limit`, total = frames+1. A 121-frame clip
  needs no split (Sollumz's `frames+30` limit does not split it anyway).
- ⛔ **THE WHOLE SKELETON IS WRITTEN, ROOT BONE (tag 0) INCLUDED.** Sollumz writes no
  channel for the root. Measured: `des_crane.ycd` writes all 51 of 51 bones, the root
  at the **start** of every track group (index 0, 51, 102). The root channels are rest
  values: Track 0 `StaticVector3`(root rest position), Track 1
  `StaticQuaternion`(rest rotation), Track 2 `StaticVector3(1,1,1)`.
- ⛔ **The benchmark for the `BoneIds` count is NOT the file's own consistency.**
  The benchmark is `skeleton bone count × 3`. This happened: `330 = 110×3` was
  consistent in itself, so it was taken as "verified", while the skeleton had **111**
  bones and the root was missing. Verification is always done against the bone count of the `.ydr` and
  **a working reference file**.

### Production pipeline — Sollumz output is NOT used DIRECTLY

> The `.ycd` patch scripts below are **not** in this public version; the pipeline only describes the contract.

```
Sollumz .ycd export (writes XML)
  -> fix_ycd_xml.py          fills any empty <Hash> left (safety net; adds 0 if filled)
  -> add-Track-2 step        Track 2 (scale) group is missing
  -> add-root-bone step      tag 0, at the START of all three tracks
  -> ycd patch step          five-field vanilla contract (below)
  -> xml_to_ycd.ps1          binary
  -> READ BACK and compare field by field with a working reference
```

The five fields the patch step measures (5 vanilla dictionaries / 27 clips, **no
exceptions**): `anim.Hash` = clip name · `clip.Name` = `pack:/<name>.clip` ·
`clip.Unknown30` = 1 · `anim.Unknown10` = 1 · `clip.Properties` = a single item.
⛔ This step is part of the pipeline; when it was skipped with "I'll align it by hand",
`clip.Properties` stayed missing and a round was lost.

`Unknown1C` **is not derived** — on the crane it is `anim.Hash+1`, on stilthouse unrelated.
No rule could be found; leave it as it is.

---

## 5. The FOUR LINKS that break silently

None of the four gives an error. The file compiles, verification says "1 clip", and in game
**nothing happens**.

**Link A — `.ycd` `BoneId` = skeleton `Tag`.**
If they do not match, the channel is silently dropped and the bone stays at rest. Sollumz's
automatic tag formula does not produce vanilla tags → **write** the bone's
`Bone Properties → Sollumz → Tag` field **by hand**
(`use_manual_tag = True` + `manual_tag`).

**Link B — clip name = model name = archetype name.**
In RayFire all three **are the same**. The rule *"the clip name must NOT BE THE SAME as
the model name"* from the `.yed`/expression recipe **does not belong here** — that rule belongs
to the fragment + expression path. Mixing these two rules once led to a wrong
diagnosis that lasted a whole round.

**Link C — the bbox must cover the WHOLE animation. IN TWO SEPARATE PLACES.**
Sollumz writes the box of the rest pose. The vanilla `des_stilthouse_root` box is
(−16.96, −5.76, −7.68)…(22.92, 26.67, 11.20) — much wider than the house itself,
because the collapse reaches that far. Leave the rest box and the object flickers
and disappears at distance.

⛔ **The box sits in two separate places and BOTH are fixed:**
```
.ydr  Drawable/BoundingBoxMin,Max + BoundingSphereCenter,Radius   <- Sollumz writes rest
.ytyp archetype bbMin,bbMax + bsCentre,bsRadius                   <- separate field
```
This happened: on the bridge only the `ytyp` was fixed, the drawable's stayed rest
(`x` was −44.75 while the animation went to −53.38) and the defect remained. In the crane
pipeline both are written. The reach is measured in Blender by scanning the frames,
with a ~0.6 m margin on top.

**Link D — ⛔ BONE FLAGS. Sollumz does NOT WRITE the `Flags` field, it leaves it zero.**
A bone whose flag is zero **accepts no transform**; the clip plays, the bone
does not move.

| file | distribution |
|---|---|
| vanilla `des_stilthouse_root` | `119`×55, `1911`×42, `7`×4, root `4215` |
| `des_crane_root` (works) | `119`×50, root `4215` |
| **Sollumz output (broken)** | **`0`×N, root `4096`** |

### ⛔ `119` IS NOT A CONSTANT, IT IS A PERMISSION SET — pick it by the tracks the clip drives

Bit table (read from Sollumz `flags_enum`, not guessed):

| bit | 1 | 2 | 4 | 16 | 32 | 64 | 256 | 512 | 1024 | 4096 |
|---|---|---|---|---|---|---|---|---|---|---|
| name | RotX | RotY | RotZ | TransX | TransY | TransZ | ScaleX | ScaleY | ScaleZ | Unk0 |

- `119` = `Rot*|Trans*` → **NO Scale bit**
- `1911` = `119 | Scale*` → all three free
- `4215` = `119 | Unk0`, `6007` = `1911 | Unk0` → the root bone gets `Unk0` added

The clip track and the flag must match: **Track 0 = translation,
Track 1 = rotation, Track 2 = scale.** A track the flag does not permit
**is silently discarded** — the file is fine, the clip plays, no error, that bone stands still.

⛔ **THIS ITEM BURNED A ROUND, AND THE CAUSE WAS EXACTLY THIS SUMMARY ITSELF.**
The table above said vanilla `des_stilthouse_root` carries **`1911`×42**;
even so the summary "root 4215, the others 119" was read and 119 was written to a
jumpscare drawable. That whole clip was driven by **bone scale**
(84 vine bones 0.001→1). Result: the doors (rotation)
played, the vines (scale) did **not** play **at all**, no error in the console.
Because the automatic fix tool also wrote 119, it became
the **source** of the defect itself.

**Rule: derive the flag from the clip, do not copy it from the table.** Whatever
tracks the clip uses, those bits must be on; if you are not sure write `1911`
(root `6007`) — extra permission is harmless, missing permission is silent.

**Gate:** an audit step (its script is not in the public version)
checks every track the `.ycd` uses against the skeleton flag and says
"scale channel on N bones but THE FLAG DOES NOT PERMIT IT". Verified with a negative
test.

**This is the most misleading symptom in the catalogue** and it burned a day:
```
PlayEntityAnim        -> 1          clip FOUND
animTime              0 -> 0.994    clip PLAYING
GetRayfireMapObjectAnimPhase advancing
mesh                  IN REST POSE  no bone moves
console error         NONE
```
What you see in game: intact state → (nothing) → debris. It reads as "the animation
does not play", but the clip is working flawlessly.

**Rule: the flags are checked after every animated `.ydr` export.**
The audit and automatic fix script are not in the public version.

---

## 5b. In-game diagnosis ladder — when "the animation does not play" is reported

In order, and **without skipping a step**. Without this ladder, running field-by-field
diffs costs rounds (it happened: eight rounds).

**1. Trigger a working reference** (`rfyik crane` / `rfyik stilthouse`).
If it plays, the composite path, ytyp registration, imap swap and server side are **fine**;
the defect is in your `.ydr`/`.ycd` pair. If it does not play, do not tinker with the asset, look at
the environment. — ⛔ *Files sitting on disk do not mean they work; the asset you use
as "reference" must be **verified** to play in game.*

**2. `rfmanuel <target>`** — disables the composite and spawns the model,
plays the clip with `PlayEntityAnim`. Read the output like this:

| `animTime` | mesh | diagnosis |
|---|---|---|
| stuck at 0.000 | — | clip NOT FOUND → Link A/B, dict name, `.ycd` hashes |
| advancing | **not moving** | **Link D (bone flag) or Link C (bbox)** |
| advancing | moving | the pair is fine → the defect is on the composite/ytyp/imap side |

**3. ⛔ Do not base a diagnosis on two numbers.**
`GetRayfireMapObjectAnimPhase` **is a counter** — it advances even when the clip is not
loaded. `animTime` advancing only says the clip was *found*,
it does **not** say it drives the bones. Both of these wrong inferences were made.

**4. The state machine does not skip steps.** Writing `6` directly while the state is `3`
**is rejected** (the read value stays `3`, phase 0.000). The right way: write `4` →
**wait for the state to settle** (not a fixed 100 ms, watch for the change) → `6`.
The engine moves it to `7`. `RequestAnimDict` is required before triggering; if the dictionary is not
loaded the model stays in rest pose and the symptom looks exactly like Link D.

---

## 6. Collision — it is state based, it does NOT FOLLOW the animation

- The animated `.ydr` **has no** `Bounds` node. There is no collision while it falls.
- Collision belongs to the **state**: the intact state's own bound, the debris's own
  bound. Vanilla carries this as a world-space `.ybn` per ymap
  (`imapstart_1.ybn`, `imapend_1.ybn` — Composite/GeometryBVH).
- In custom production the less fragile equivalent: a Bound Composite **embedded** in the state `.ydr`s
  (in Sollumz make the composite a child of the drawable)
  + `physicsDictionary = model name` on the archetype. Verified.

**That is why script tricks like `SetEntityCollision` / `FreezeEntityPosition` /
`DoorSystemSetOpenRatio` always backfire here:**
the system is already state based; there is no collision for a script to chase.

### Building the embedded bound — measured limits and order

Setup in Sollumz: `sollumz_bound_composite` (EMPTY, child of the drawable)
→ under it `sollumz_bound_geometry` (MESH). Making the mesh a copy of the visual mesh
is enough; no need to model a separate collision.

⛔ **DO NOT USE `sollumz_bound_geometrybvh`.** Sollumz does not read the mesh of that type,
the export crashes with `Bound GeometryBVH 'x' has no geometry!`. The working type is
`sollumz_bound_geometry`.

⛔ **Hard vertex ceilings** (both come out as an export error):
```
sollumz_bound_geometry (non-BVH)   max 16,383 vertices
BVH bound                          max 32,767 vertices
```
And the conversion ratio is not intuitive: **bound vertices ≈ mesh vertices × 1.52**
(measured: 11,396 mesh → 17,283 bound). I guessed 1.42 and got two
failed exports. Setting the target on the mesh side to **~9,500 vertices** gives
a safe band (→ ~14,400 bound).
If it exceeds that, thin it with the `DECIMATE` modifier — the loss is invisible in collision.

Material: `bpy.ops.sollumz.createcollisionmaterial()` creates a `DEFAULT`
material (**it needs a selected object**, otherwise it says "No objects selected" and
does nothing). Then pick the real material with `mat.collision_properties.collision_index`
(concrete = **1**, table `collision_materials.tsv`).
Reducing all faces to a single collision material is enough.

⛔ **If `physicsDictionary` stays empty the embedded bound is NEVER bound to the engine.**
Write the model name itself on the archetype. On an archetype that carries no bound, leave it
empty — pointing at a dictionary that does not exist is a new source of errors.

### ⛔ ORDER: first put in YOUR OWN collision, then cut the vanilla one

On archetypes with `physicsDict = 0`, vanilla collision is inside a **world-space `.ybn`**;
deleting the entity from the ymap removes the visual but **leaves the collision** —
after the collapse you walk on air. It must be cut, but if you cut vanilla
first, the intact state is holed too and you fall through it.

Measured distribution (bridge slice, triangle centre inside the slice):
```
hw1_rd_10.ybn   546 polygons  z 78..84   bridge deck + road surface
hw1_rd_9.ybn     44 polygons  z 80..84   edge of the slice
hw1_10_0.ybn     75 polygons  z >= 70    piers/body
hw1_10_0.ybn    260 polygons  z 56..70   PIT FLOOR -- DO NOT TOUCH
```
Note: when searching for polygons in a `.ybn`, do not require **all three corners of the triangle**
to be inside the area — the deck's large triangles cross the boundary and the count says "no deck collision".
Use the **triangle centre**.

---

## 7. ymaps

```
des_X_imapstart : ymap flags 1  contentFlags 577 (HD 1 + Physics 64 + Critical 512)
des_X_imapend   : ymap flags 1  contentFlags 65  (HD + Physics)
placer          : ymap flags 0  contentFlags 65

entity template (in all three):
  flags 1572864 · parentIndex -1 · LODTYPES_DEPTH_ORPHANHD · PRI_REQUIRED
  lodDist -1 (use the archetype's)  — 100 on the placer
```

`des_stilthouse` has a third ymap as well: `_rebuild` (85 entities) —
the repaired state. It is not required.

The `.ytyp` **must be registered**, putting it in stream is not enough:
```lua
files { 'stream/des_X.ytyp' }
data_file 'DLC_ITYP_REQUEST' 'stream/des_X.ytyp'
```
If it is not registered, both the ymap entities and `compositeEntityTypes` are **silently**
never created.

---

## 8. Sollumz deviations and the patch list

Measured with Sollumz 2.9. After export all of these must be fixed:

| # | Sollumz writes | should be |
|---|---|---|
| 1 | `pack:/pack:/x.clip` (double prefix) | `pack:/x.clip` |
| 2 | `Unknown30 = 0` | `1` |
| 3 | `Tags` / `Properties` blocks **missing entirely** | `Properties` 1 Item (Int 32) |
| 4 | `Unknown10 = 0` | `1` |
| 5 | `BoneIds` only Track 0+1 | Track 2 too (`StaticVector3 1,1,1`) |
| 6 | bbox = rest pose | the full reach of the animation |

Fix steps: the clip fields are rebuilt in vanilla order · Track 2
blocks are added to `SequenceData` · the three channels of the root bone (tag 0) are written at the start
of every track group. The scripts are not in the public version.

### Other Sollumz pitfalls (all happened)

- **If `sz_lods.high.mesh` is not set, export says "has no Sollumz materials!"
  and skips the drawable entirely.** The material is actually there; Sollumz
  reads materials through `child.sz_lods.get_lod(...)`. On newly created
  mesh objects this field stays **None** → `ob.sz_lods.high.mesh = ob.data`.
- `bpy.ops.object.select_all(DESELECT)` silently breaks the selection in an MCP
  context → use `bpy.context.temp_override(...)`.
- Bone axis pitfall when computing `pose_bone.matrix_basis` directly:
  in Sollumz bones local Y = the head→tail direction, not the world axes.
  The right formula: `basis = L.inverted() @ M @ L` — `M` is the wanted **world** rigid
  transform, `L = bone.matrix_local`. Writing `basis = L.inverted() @ M`
  becomes a rotation about the bone head and breaks the geometry even at frame 0.

### DO NOT WRITE `.ytyp` / `.ymap` XML BY HAND — use a generator script

A `des_*` set needs **one ytyp + three ymaps**, and all four are linked to each other through guid/name/
extent; write them by hand and one of the links silently breaks.
The repository has two working generators, both for **pattern A** (imap swap):

| script | what it produces |
|---|---|
| `scripts/gen_crane_meta.py <folder>` | `des_crane` — reference generator with fields measured from `des_stilthouse` |
| `scripts/gen_bridge_meta.py <folder>` | `des_bridge` — the version with the **permanent geometry split** of §11 applied (`_rest` on the placer) |

For a new `des_X`, copy one of them; **do not change** any field other than position, name and
entity list. The output is XML → `meta_xml_to_bin.ps1`.

### Binary `.ytyp` / `.ymap` production

Sollumz cannot write these as binary, and `xml_to_res.ps1` does not support them either. Use:
`XmlMeta::GetData(doc, MetaFormat.RSC, folder)` (see `meta_xml_to_bin.ps1`).

⛔ **Both are written through `MetaFormat.**RSC**` — do NOT LOOK for a member called
`ytyp`/`ymap` in the enum.** This happened: not finding it in the enum led to the conclusion
"CodeWalker cannot write this path", the composite was abandoned and a switch to the wrong
script-based path (`CreateObject` + `PlayEntityAnim`) lost rounds.
The tool was already working.

⛔ **`YtypFile.Save()` SILENTLY DROPS the `compositeEntityTypes` block**
(measured: 925 → 836 bytes, composite 0). The XML path does not drop it. Rewriting a ytyp
"without touching it" with `Load` + `Save` destroys the composite.

---

## 9. What can be tested without entering the game

The whole ladder: `trunk/verification-ladder.md`. The part specific to this system:

**Testable (seconds):**
- That the clip really drives the bones — evaluating the compiled `.ycd` per phase with
  CodeWalker.Core catches Link A and a dead tail (the tool is not in the public version).
- All three of Links A/B/C are checked by XML read back on the deployed files
  (tag set equality, clip Hash, bbox ⊇ animation box).
- The look of the motion — Blender timeline / viewport render.

**NOT testable (needs the game):**
- The composite state machine, imap swap, `punchIn/Out` timing
- Streaming, ytyp registration with `DLC_ITYP_REQUEST`
- Collision behaviour

**After an asset changes, leave the server COMPLETELY and reconnect** —
a restart is not enough, otherwise you test a stale asset.

---

## 10. Error catalogue — what happened

1. **Trying it with a fragment (`.yft`).** The RayFire root is a `.ydr`. On a `.yft`
   `PlayEntityAnim` leaves `animTime` at 0.000.
2. **Not writing the `compositeEntityTypes` block at all** → the archetypes register,
   there is no composite, `GetRayfireMapObject` returns 0.
3. **Adding `.yed` + an Expression extension.** RayFire has none; that chain is
   part of the fragment/expression path. Adding it does harm.
4. **Making the clip name different from the model name** (the reverse of Link B).
5. **Filling `physicsDictionary`** — it is empty on the vanilla root.
6. **Putting `rootN` into a ymap / spawning it by hand** → it is no longer RayFire.
7. **Mixing recipes.** In one round the asset had become `des_stilthouse`'s skinned
   mesh + `my_vauldr`'s fragment packaging; each recipe was right
   on its own, the hybrid did not work. **Pick one recipe and apply it
   all the way through.**

---

## 10b. Removing vanilla — NOT hiding, but deleting or moving

If you put your own destruction in place of a vanilla structure, the vanilla entity
must go; otherwise the two overlap and the destruction looks like it "never happened".
**All LOD levels + the `hei_` twins** are patched (`X_strm_N`, `X_long_N`,
the `_lod` in `X`).

⛔ **Hiding with entity flags (`bit22 Disable shadow` + `bit23 Disable
entity`) IS NOT USED.** Measured: when the HD entity is hidden, the engine starts drawing its
**LOD shell** — flat, single-colour, untextured triangle surfaces
appear on screen, and this reads as "our model is broken". The shell is coarse geometry anyway.

There are two right ways:

| way | what it does | when |
|---|---|---|
| **delete** | remove the entity from `entities`, shift **`parentIndex`** and decrement the parent's **`numChildren`** | permanent cleanup |
| **move** | take the entity 600 m down | never breaks indices, reversible |

### ⛔ TWO QUESTIONS BEFORE DELETING — all three happened, all three opened a hole in the world

**1. Is the entity's extent inside YOUR model's FOOTPRINT?**
Saying *"we merged this vanilla object into our model"* does **not** mean
*"we cover all of it"* — during the merge only the intersecting part was taken.
The criterion is one line: is `position + archetype bbMin/bbMax` inside your coverage.

Measured case (bridge, coverage `x 664…869, y −113…41`):
```
fwy_04_splita03   y −322 … −143   OUTSIDE  -> deleting it removed the freeway
fwy_04_splita02   y  +60 … +178   OUTSIDE
fwy_04_splita     y  −50 …  +85   OUTSIDE
hw1_rd_02_17      x 664 …  784    inside   -> safe to delete
```
**Structural** geometry that spills outside is not deleted; either leave it or produce the
remaining part of vanilla as your own drawable (the "road minus the collapsing
slice" method on the crane).

**2. Does this entity carry structure, or only a decal?**
`_ovly` / decal entities **can always be deleted** — their absence is not a hole,
only a missing stain/line. Measured: 4 `fwy_04_rd_*_ovly`, all
`parentIndex = −1` (orphan, no LOD parent) and `lodDist` 62–89.
But careful: the same decal can **also carry road markings**
(`im_roadmarkings*`, `im_roadblends*`) — delete it and the road looks patched.

**3. Do not leave a LOD with no children in place.**
When the HD entity is deleted, its parent is left with `numChildren = 0`, and that LOD **starts
drawing at every distance**. Symptom: "the road/ground is still there", or flat untextured
surfaces. Measured: `fwy_04[53,56,58,68]`, `hw1_rd[237,238]`,
`hw1_10[3,4]` — all `LODTYPES_DEPTH_LOD`, `lodDist` 350–500.
And a separate pitfall: **mid-distance** variants with an `_a` suffix like `hw1_10_land03_a`
carry the ground's **baked dirt texture**; do not label them "ground" and
move on, look at what they draw.

### ⛔ THERE ARE TWO WAYS TO WRITE A ymap AND WHICH ONE IS LOSSLESS DEPENDS ON THE FILE

| way | when |
|---|---|
| `XmlMeta.GetData` (XML round trip) | lossless on most ymaps, **but not on all** |
| `YmapFile.RemoveEntity` + `YmapFile.Save()` | on the binary, lossless in the measured case |

Measured — `hw1_rd_critical_1.ymap`, an XML round trip **without touching the file
at all**: **457 entities → 128**. A `Save()` round trip on the same file: **457 → 457**.
Had it been deployed, **325 objects** in the area (trees, signs, traffic lights, bins)
would have silently vanished; the tool gives no error, it says "success".

**Rule: after every ymap write, compare with the source entity count.**
`meta_xml_to_bin.ps1` now does this itself and deletes the output if it does not match.

### ⛔ DO NOT EMBED a vanilla prop in your own model

Adding vanilla props such as a street lamp or a bin into your `.ydr` breaks
the textures: their textures are in their own `.ytd`s (`prop_streetlight_01.ytd`); that dictionary does not
come along when you embed them and the materials fall onto the wrong textures — in the measured
case the lamp came out red-and-white striped. If you need the prop,
**leave the vanilla entity where it is** or **delete it from the ymap**; do not copy its
geometry.

When deleting, index repair is mandatory: when an entity leaves the parent ymap, the
`parentIndex` values in the child ymaps **shift by one** and silently point at the wrong
entity. Measured example (`hw1_10`):
```
hw1_10.ymap[9]  = hw1_10_bridge01_lod   deleted
                  -> parent[0].numChildren 6 -> 5
hw1_10_strm_0   3 entities with parentIndex > 9  -> -1
hw1_10_long_0   1 entity with parentIndex > 9    -> -1
```
Verification: the entity count of every ymap must be kept (except the deleted one) and the target
archetype hash must appear **0 times**.

⛔ **Do not touch the extent** (§1.6): removing an entity does not change the extent.

---

## 10c. ⛔ MEASUREMENT PITFALLS — all happened in this system, all SILENT

Every item in this section burned a round, some burned a day. What they share:
the tool gives no error, it returns a plausible-looking **wrong number**.

**`MetaHash` ≠ `UInt32`.** `entity._CEntityDef.archetypeName` is a `MetaHash`;
in a hashtable keyed by `UInt32`, `ContainsKey($archetypeName)` **never
matches** and reads as "0 left". An explicit cast is required:
`[uint32]$en._CEntityDef.archetypeName`. I wasted a whole verification round
because of this — the files I called "clean" had not been measured.

**PowerShell variables are case-INSENSITIVE.** The `$y` (YmapFile) used in a loop
overwrote the backup folder variable `$Y`, and the backup was written to the wrong path.
Short variable name + loop = this bug.

**`"$S\$n.ymap"` produces a wrong path** — PowerShell takes `$n.ymap` for a property access
and it returns empty. Use `"$($n).ymap"` or `Join-Path`.

**`@(@(x,y))` FLATTENS when it has a single element.** A one-coordinate list turns into
`@(x,y)`, `$k[0]`/`$k[1]` go haywire and the match silently misses. In the measured case
the bin to be deleted was 1.1 m away, and "0 deleted" was reported.

**`bpy` `bound_box` can be STALE.** After `mesh.transform()`,
`ob.bound_box` returns the old value; even when the transform was applied it
looks "not applied". Compute the box **from the vertices**.

**Grid sampling can ask the wrong question.** To check "is there ground" I cast a grid with 20 m
steps, 100/100 points hit and I said "no gaps" — but all the grid
points had landed on the road/bridge surface, and the places without ground were
never sampled. The measurement was right, **the question was wrong**.

**⛔ And the most expensive one: A SCREENSHOT IS NOT A MEASUREMENT.** In this session I looked at frames
three times and made a wrong diagnosis (once I said "there is a gap", there was none; once
I said "no gap", there was one). Before saying something is broken,
**read**: the file, the entity count, the read back.

---

## 11. SEPARATE permanent geometry from state geometry

A `des_*` job usually has three separate things:

| what | where | why |
|---|---|---|
| intact state | `StartImapFile` | the state machine turns it off |
| debris | `EndImapFile` | the state machine turns it on |
| **permanent ground / surroundings** | **the placer ymap** (next to the composite) | belongs to no state |

⛔ **ONLY the collapsing slice goes into the `start` imap, not the whole structure.**
It happened a second time, this time at a larger scale: `start` held **the whole
bridge** of 205 × 154 m, while `end` held only 82 × 69 m of debris.
On trigger `start` turns off and **all** of those 205 metres vanish; only the
debris comes back. The symptoms arrived as separate complaints and none of them
looked alike:
```
railings vanished · a hole opened in the road · decals left hanging in the air
```
All of them had this single cause. The right split:
```
placer (ALWAYS ON)  composite  +  <name>_rest    everything that does not collapse
start  (turns off)  <name>_intact                intact state of the collapsing slice
end    (turns on)   <name>_debris                debris
```
`_intact` = **a static export of frame 0** of the animation (the same on the crane).
`_rest` = the merged model with the collapsing slice **removed**.

⛔ **Do not put permanent geometry into the state imaps.** I had put the part of the road
that does not collapse into both `start` and `end`; at the moment `start` has turned off and `end`
has not yet turned on, **there is no road left**, and the sky shows underneath.
Symptom: the whole area is a hole. The right place is always the placer, which is always on.

```
des_crane_start    ['des_crane_intact']
des_crane_end      ['des_crane_debris']
des_crane_placer   ['des_crane', 'des_crane_road', 'des_crane_ov']   <- permanent
```

### ⛔ COMPUTE the imap EXTENT

In a ymap you generate, the extent must not come from a box written by hand;
it must be computed **from the union of the entities**. An entity that is not inside the extent
**is silently never visible**, and there is no error either.

Measured:
```
des_crane_start  declared z 28.6..43.8   actual z 28.6..108.9  -> 65 m of the intact crane OUTSIDE
des_crane_end    declared z 28.6..43.8   actual z 28.6.. 48.8  -> 5 m of the debris OUTSIDE
```

The same holds for the archetype box: the box of `des_X_root` must cover
**the whole animation** (the union of all parts over all frames),
not only the rest state.

### Make the guid deterministic

Do not use `abs(hash(name))` — Python's string hash is seeded randomly per process,
so every build writes a different guid. Use Jenkins.

---

## 12. Bind pose and skeleton link — recovery recipe

### Bind pose = world rest − ORIGIN

The vertices inside the animated `.ydr` are the coordinates of **the intact state**
(in drawable space). In game the `.ycd` drives the motion. So:

- `des_X_intact` and `des_X_root` carry **the same geometry**
- `des_X_debris` = the same geometry with the last-frame transform applied per part

### ⛔ DO NOT DERIVE part motion from `pose_bone.matrix`

In Sollumz bones local Y = head→tail; **the rotation of the pose matrix is not
the world rotation of the part**. Measured: `Translation(ORIGIN) @ pose.matrix`
gives the part's **position right** and its **orientation 90° wrong**. In game
the mast came out horizontal and the jib vertical.

⛔ **The bbox gate does NOT CATCH this error** — since the parts rotate around their own centres,
the union box looks plausible. Build the gate on **orientation**:
measure the direction of a known edge of a known part, or do the
bone-centre comparison in §12.

### Blender's armature modifier can be broken — that does not mean the file is broken

Measured: in the same scene, applying `pose @ bone.matrix_local⁻¹` by hand gives
**both** the bind and collapsed boxes exactly, but the armature
modifier's output scatters 500+ m. The `.ycd` working in game was fine.

**Lesson:** trust **the hand calculation and the deployed file**, not the viewport.
If the manual transform gives the right result the asset can be built; trying to fix the modifier
is unnecessary.

### Recover the right group→bone mapping from the WORKING `.ydr`

Weights are stored in the mesh by group **index**; if the object's group list is
recreated, the names land on the wrong indices and parts take each other's
motion. Recovery:

1. Dump the working `.ydr` to XML; read `BlendIndices` + `Position`.
2. Compute the **vertex centre** per bone index (skeleton order = index).
3. In Blender compute the vertex centre of each group, match it to the nearest bone.
4. Rename in two stages (first a `__t_` prefix, then the real name).

Measured: match median **0.093 m**, 50/50 groups under 0.5 m.

**Gate:** compare the per-bone vertex centres of the new `.ydr` with those of the working `.ydr`.
On the crane bones the deviation came out at a median of **0.040 m**; on the plates whose geometry
I changed on purpose a large deviation is normal.

### ⛔ Deleting a vertex group deletes the weights

If you do `vertex_groups.remove(...)` after `km.data = new_mesh`, the mesh's
weight data is gone. Export warns "42586 vertices are not weighted to any
group". Assign the mesh, **do not delete** the groups.

---

## 13. Work discipline — the two most expensive lessons of this round

### ⛔ SAVE THE BLEND

A day of Blender work existed only in the exported `.ydr`s;
the `.blend` on disk was **26 hours old**. When Blender closed, the motion tables held
in memory (`_target`, `_sim_M0`) were gone too and the work was rebuilt from scratch — and
rebuilt wrong (§12). After every export, `bpy.ops.wm.save_mainfile()`.

Intermediate data held in memory (`bpy._X`) is not persistent. What has to persist
is written either to the `.blend` or to disk.

### KEEP the last working output

Thanks to last night's `.ydr`s in the `out2/` folder, a broken deployment could be
rolled back with one command. Copy every verified version into a dated folder;
do not build without a way back.

### A screenshot is not a diagnosis

In this round a wrong diagnosis was made three times by looking at the pattern on screen (thought to be
overlapping plates → actually the natural overlap of rotated axis-aligned boxes;
thought to be an unresolved texture → actually `cpv_only`; thought to be the material → actually
the normals). A symptom tells you where to look, **a measurement tells you the cause**.

## 14. Fracturing — the three measures that decide whether destruction "looks like destruction"

Splitting a structure into cells and giving each cell a rigid transform is the right method,
but **cell size and layer separation decide the result.** All three were measured
(a bridge area of 115 × 72 m, 20 thousand faces).

### a. A lift-off-the-ground clamp CANCELS the collapse

When a clamp `if zmin < FLOOR: move up` is put on the parts "so they do not sink into the ground",
and a part contains **both deck and pier**, the pier's
base is already near the ground, so the clamp lifts the whole part back
up. Measured result: top surface drop **median 4.1 m**, 17 of 24 parts
dropped less than 8 m, two **rose**. To the eye: "the bridge does not collapse".

**The right way is to split into layers with a horizontal plane** (here z=77):
the deck layer drops freely **18-20 m**, the substructure layer **does not drop,
it topples** (25-60° tilt, 2-8 m). A pier does not sink — a pier *topples*.
Measured: median drop 4.1 → **18.9 m**, the part that dropped least 12.1 m.

### b. The measure of visible "tearing" is edge length, not the triangle ratio

Looking at the **ratio** of stretched triangles misleads: the vanilla bridge itself also comes out
at 14%, and "no problem" is concluded. On a rigid part stretching is mathematically
impossible anyway; what the eye sees is **the area a long edge inside
the part sweeps as it rotates**.

| grid | part diameter (median) | longest edge | parts >30 m |
|---|---|---|---|
| 23 m cells (44 parts) | 30.7 m | 16.2 m (max 25.5) | 23/44 |
| **11 m cells (88 parts)** | **21.8 m** | **7.3 m** (max 19.2) | **2/88** |

Target: longest edge **median < 8 m**. Cutting at the cell boundaries with `bisect_plane`
is required — assigning faces to a cell only by their centre leaves a face that crosses
the cell as it is, and a single triangle stretches to 60 m.

### c. Do not delete a small cell, merge it into a neighbour

If cells with fewer than 25 faces become separate parts, the skeleton bloats needlessly and
sliver parts fly around. Add them to the nearest large cell in the same layer.
88 parts + hand + root = **90 bones** exported without problems.

### d. When rebuilding, the order is fixed

When the part list changes, **everything** is rebuilt and none of it
can be skipped: debris (boolean) → armature → root mesh + weights →
animation → **clip dictionary** → export → `.ycd` patch → ytyp boxes →
deployment. If the clip dictionary keeps pointing at the old armature data-block, the
export gives `AssertionError: The armature bone-map is required at this point`
— delete the hierarchy and rebuild it **from scratch** with `create_clip_dictionary`;
fixing `target_id` by hand is not enough.

## 15. Cut surface — close the geometry, fix UV and material too

When cutting a vanilla part and turning it into debris, three separate defects appear, and
**each is caught by a separate criterion**. Measured (115 × 72 m bridge, 78 thousand triangles).

### a. Order: clean → CUT → solidify → fracture → fill holes

`remove_doubles` / `dissolve_degenerate` **melt the cell cuts back together**.
Do the cleanup after the cut and the longest edge jumps from 19.3 m to **88.6 m**,
and a single triangle sweeps across the whole scene. When the order breaks no
check warns; measure edge length after every step.

A vanilla road/ground is **a single-sided shell**: split into parts, its open edge
ratio is **51.1%**. The back of a toppling slab shows — this is reported as
"tearing". `SOLIDIFY` (0.6 m, `offset=-1`) + per-part `holes_fill`
closes the cut surfaces: **51.1% → 3.8%**.

Loose vertices pollute the measurement: `bmesh.ops.delete(context='FACES')` leaves the vertices
not connected to a face, and the part diameter reads **106.9 m instead of 22.5 m**.
Clean up with `context='VERTS'` before measuring.

### b. UV: the area ratio is NOT ENOUGH, measure anisotropy — and triangulate n-gons

`uv_area / world_area` **cannot see area-preserving stretch**: a triangle stretched 10×
along u and squeezed 10× along v keeps the same ratio. With this criterion
"fixed" was declared, and smear marks stayed on screen. The right criterion is **the singular
value ratio of the Jacobian** (`s0/s1`).

Also, if the measurement takes **the first three loops** of a face, the rest of the n-gons
that `holes_fill` produces are never measured. `triangulate` first, then measure.
Measured: while the n-gon measurement said "median 1.13, >3x 0.0%", the triangulated measurement
found **>3x 11.4%** on the same mesh.

### c. The UV scale is taken PER MATERIAL, not as one global median

Giving all faces one `uv/m` when re-projecting dresses the terrain in the road texture
and the road in the terrain texture. The target scale is taken from the median of the good
(anisotropy < 2) faces of **an untouched vanilla part** in the same material.
The measured vanilla values differ from each other several times over:
`im_road_001` **0.172 uv/m** (repeats every 5.8 m) · `rn_tf_canyonrock_009`
**0.087** (11.5 m). Using one number breaks one of the two.

### d. A cut surface INHERITS the source's material — give it concrete

The solidify side wall and the hole-fill face carry the material of the face they were cut from:
**road markings** or **grass** texture appear on a vertical wall.
The criterion is simple and measurable: `|n.z| < 0.55` **and** the material name
is from the road/ground family → the structure's own concrete (`hw10_bridge1_rn_rk_main`),
rock if it is ground (`rn_tf_canyonrock_009`). Measured: 10.1% of triangles → 0.00%.

### e. ⛔ Do not compare two renders taken from different distances

"Vanilla has dense checks, ours has bars" — the UV was thought to be broken; the two shots
were at different distances. The measurement said both were in the same band:
uv/m vanilla **0.216** · ours **0.178**; anisotropy >3x vanilla **7.5%**,
ours **0.3%**. A control shot is not a control without **the same target, the same distance,
the same lens**. (The same as §13: a screenshot is not a measurement.)
