# Prop — branch rules

Command: `/prop`
**Keywords:** prop, object, door, door won't open, lock, won't move, freeze, AddDoorToSystem, specialAttribute, pivot, bbox, physicsDictionary, fragment, breakable, yft, ytyp name, hash_, CreateObject, slot height, DUI, screen on object, ATM, keypad, monitor, attach to hand, PH_R_Hand
**What belongs here:** **A single portable / interactable object** — its door, physics, breaking, the screen on it, attaching it to a hand. Boundary: the object **moving** (animation) is outside this branch · placing it in the world in bulk → `/map`.

> The keywords above **speed up routing; they are not a complete list.** If a word is not in the list,
> routing does not stop — this definition is checked instead. *“roller shutter”* is not in the list, but it is still a door object.


## What holds for every leaf in this branch

Measurement sources: 316,975 archetypes, the Fleeca MLO doors, 5 screen models read from the RPF.

### Query first — no code
- **`assetdb.py show <name>` / `door <name>` / `where <name>`.** Is it a door, where is the pivot, does it have physics, in how many places does it exist.
  For the Fleeca teller door four natives were tried in turn; the answer was one line: `specialAttribute = 0` → not a door.
- **`specialAttribute` door table:** 7 hinged · 8 sliding · 5 garage · 10 roller shutter · 12 barrier → the door system
  works; **0 = NOT a door**, it does not move even when registered. All 21 values: `trunk/flags.md`.
- **Movement is four layers, in order:** ownership (without `NetworkRequestControlOfEntity`, `Freeze/SetCoords`
  are silently ignored) → physics (`SetEntityDynamic` + `ActivatePhysics`) → hinge (`specialAttribute`) →
  sync (a map object is not networked; the state lives on the server).
- **If the prop has no skeleton**, `PlayEntityAnim` and bone-index operations do not work on that model (`assetdb.py bones`).

### While building
- **Pivot X/Y centre, Z base** (`bbMin.z = 0`); a long part is laid flat + 90°. **`physicsDictionary` is never 0**
  (the model is visible, you walk through it) — on your own prop, its own name hash.
- **The bbox covers the whole animation, in two places** (`.ydr` + ytyp); otherwise it flickers/disappears at a distance.
- **The ytyp's own `<name>` is unique** (of three ytyps with the same name only one loaded); in CodeWalker XML
  `hash_XXXXXXXX` → resolve it with the joaat of the stream file names.
- Sollumz: an object made with `bpy.data.objects.new` carries no `sollum_type` → the file is never written; `sz_lods.high.mesh`;
  `holes_fill` samples UV (0,0); scale goes to the **largest** axis → `trunk/tool-pitfalls.md` §1-2.
- **Fragment root group pitfall:** the `parentIdx=255` group is the entity body and does not follow the bone → at least two groups,
  the moving part in the child group. The bound→bone link is a **`COPY_TRANSFORMS` constraint**, not a name match.

### In-game placement
- **`CreateObject` places at the bound base, `CreateObjectNoOffset` at the origin**; a stale bound lifts the object into the air —
  regenerate the bound from the visual mesh.
- **Slot/shelf height is measured, not guessed** — the model's widest horizontal surface (area of +Z-normal faces by z).
- **Attaching to a hand:** `PH_R_Hand` 28422 · `PH_L_Hand` 60309 · `SKEL_L_Hand` 18905; the burger clip eats with the **left** hand.
  An offset table is ported together with its `rotationOrder` (dpemotes 1 · ox_lib/qb 0) → `hand-attach.md`.
- ⛔ **Adding a bone to a prop gives no alignment** — GTA positions an attached object from its ORIGIN. The grip alignment is **baked into the model**:
  ORIGIN = grip point, forward +Y, attach `(0,0,0)`; the scale is baked too (a prop cannot be scaled at runtime).
- **An orphan sweeper also deletes display/diagnostic objects** → whitelist them; when diagnosing "models disappear", check your own code first.
- On a map object `SetEntityCollision(false)` is not reliable → `CreateModelHide`. A root-bone clip does not play on a frozen object.
- **An object spawned by script is not a map object**; a prop is not put inside an MLO with a ymap → `branches/map/_branch.md`.

### Screen / interaction
- **Three render paths, the data decides:** if there is a real screen texture, `AddReplaceTexture` (per material and **GLOBAL** —
  3 ATMs show the same page), otherwise a world quad, on a moving entity `AttachPanelToEntity`. Ask: `screentex.ps1 -Model <name>`.
  Screen = `emissive*` shader, texture embedded in the model → `origTxd` = model name; the ytyp `textureDict` is **not** the screen dictionary.
  Keypads and CCTV have **no** screen texture.
- **DUI/NUI is client-side, not synced** — compare passwords/codes on the server.

## Leaves

| wanted | file | status — source |
|---|---|---|
| Door won't open / object won't move / lock / coordinates | doors-and-motion.md | measured — old SKILL door/motion/override/coordinates |
| Breakable / boned prop (fragment) | fragment.md | measured — old SKILL fragment building |
| Live screen on an object (DUI) | dui-screens.md | measured — 3dnui-dui-panel |
| Attaching a prop to a bone — porting an offset table, rotationOrder, live offset editor | hand-attach.md | read + numeric — pg_attachproptoplayereditor, dpemotes, ox_lib, qb progressbar |

## Trunk files to read
- `trunk/flags.md` — `specialAttribute` 21 values, archetype flags, extension types (particle, ladder, buoyancy)
- `trunk/verification-ladder.md` — before putting the prop in the game: export size, bound, ytyp read back
- `trunk/tool-pitfalls.md` §1 Sollumz, §2 Blender (bake transforms), §6 FiveM (`CreateModelHide`, handle cache)
- The prop's light → `branches/look/lights.md`
- Looking for a ready example / tool (`yft.blend` that splits into 3 pieces, `blender_rayfirev`, drawable import cleanup, ⛔ empty `.col` = instant crash) → `sources/community-resources.md` §5, §8 — **source note, not a rule.**
