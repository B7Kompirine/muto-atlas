# Replace an object inside an MLO with my own model (entity swap)

**When to read:** replacing an object that is already inside an MLO with your own model (entity swap): a door/object in the interior is defined wrong (`specialAttribute=0`), the animation plays but the collision stays, or the model itself has to change.
**Source:** former MLO object swap reference (2.5.0, in full) · old SKILL section 'FIXING AN OBJECT ON THE MAP' (2026-07/08) · **Measured:** Fleeca teller + vault door in game; the 4 rejected ways failed in game
**Read first:** `branches/map/_branch.md` · trunk › `trunk/flags.md`, `trunk/tool-pitfalls.md`

---


The Fleeca teller door (`v_ilev_gb_teldr`) and vault door (`v_ilev_gb_vauldr`)
were made to work this way. Every item below was verified by in-game
measurement; no "probably".

---

## 1. WHEN TO USE THIS RECIPE

When an object on the map does not behave the way you want:

- it should be a door but cannot be pushed (`specialAttribute = 0`)
- the animation plays but the collision stays in place (drawable, not fragment)
- the model itself is wrong / incomplete and you want to put in your own model

---

## 2. DECIDE THIS FIRST — EVERYTHING DEPENDS ON IT

**Is the object inside an MLO interior or outside?**

This one question decides which way works, and skipping it costs days.

| | **outside** the MLO (street, open area) | **inside** the MLO (bank, house, shop) |
|---|---|---|
| Placing with your own ymap | ✅ works | ❌ **the room/portal system culls it, the object never appears** |
| Changing the MLO entity list | — | ✅ **the only way that works** |

Do not let another resource's use of a ymap mislead you. First check the coordinate
of its prop: if it is outside the MLO, it does not match your case.

---

## 3. REJECTED WAYS (do not try again)

All were tried and failed by in-game measurement:

1. **Spawning your own copy with `CreateObject` and hiding the vanilla one**
   An object created by script **is not a map object**.
   - The door system looks for the door by model+position *on the map*, cannot find it →
     a loose physics prop is left → **when the door was touched it fell
     through the floor.**
   - The fragment's per-bone collision **did not follow** the animation.
   - Stop the fall with `FreezeEntityPosition` and the door system
     cannot push it.

2. **Placing with your own ymap (inside the MLO)**
   The entity is culled. The vanilla one is hidden too, so a **gap** is left.

3. **Fixing `specialAttribute` in the vanilla prop ytyp**
   (`int_lev_des.ytyp` → `v_ilev_gb_teldr` 0→7). The file was produced flawlessly
   (348/348 archetypes identical) but physics still did not load in game.

4. **Adding a new ytyp with the vanilla name**
   The game has already registered the first definition; they conflict.

---

## 4. THE WORKING RECIPE — STEP BY STEP

### Step 1 — Identify the object and its archetype

```
assetdb.py show <model_name>
```

Note down: `specialAttribute`, `assetType`, `physicsDict`, `bbMin/bbMax`.
`bbMin.x` / `bbMax.x` is critical for a door: **the pivot must be at the hinge**
(the bbox must be either `-W → 0` or `0 → +W`, hinge at X=0).

### Step 2 — Extract the model from the RPF

```
extract_asset.ps1 -Names <model>.ydr -Out <folder>
```

The script adds the RSC7 header back and applies deflate — without them
Sollumz says "Unsupported file format" / "DECOMPRESS_FAILED".

### Step 3 — Rebuild it in Blender UNDER OUR OWN NAME

Import with Sollumz → rename to `my_xxx` → export.

- For a **normal door**: a drawable is enough. Verify that the pivot is
  at the hinge. The collision (BoundComposite) must stay inside the mesh.
- For **collision that follows the animation**: build a FRAGMENT.
  Details: `branches/prop/fragment.md`.
  Summary, two rules:
  - What binds the bound to the bone is the `COPY_TRANSFORMS` constraint
    (not `parent_bone`, not name matching).
  - **At least two groups are needed.** The group with `parentIdx=255` is the entity
    body and does NOT FOLLOW the bone. The moving part must be in a child
    group:
    ```
    group[0] root bone (tag 0)  parentIdx=255  -> FIXED hinge
    group[1] moving bone        parentIdx=0    -> TURNING leaf
    ```
  - **Do not change** the bone tags — the vanilla clip playing depends on them.

### Step 4 — Generate your own archetype

```
make_ytyp_override.ps1 -Models <vanilla> -RenameTo <ours> `
  -SpecialAttribute <7|0> -AssetType <ASSET_TYPE_DRAWABLE|ASSET_TYPE_FRAGMENT> `
  -ClearDicts -PhysicsDictSelf -Flags <...> -LodDist <...> `
  -YtypName <ours> -OutFile <...>\stream\<ours>.ytyp
```

| | pushable door | animated fragment |
|---|---|---|
| `assetType` | `ASSET_TYPE_DRAWABLE` | `ASSET_TYPE_FRAGMENT` |
| `specialAttribute` | **7** (hinged) | **0** (the script plays the animation) |

- **`physicsDictionary` is NEVER left 0** → `-PhysicsDictSelf`.
  Give it 0 and the model shows but **you walk through it**. Not a single
  door prop in the vanilla archive has 0.
- `textureDictionary` may stay 0 (if the textures are embedded in the file).

fxmanifest:
```lua
files { 'stream/<ours>.ytyp' }
data_file 'DLC_ITYP_REQUEST' 'stream/<ours>.ytyp'
```

### Step 5 — Find which MLO holds the object

Scan all ytyps and look for the model hash in `MloArchetype.entities`.
Result for Fleeca:

```
v_int_10.ytyp            -> MLO v_genbank            (teller + vault)
hei_dlc_generic_bank.ytyp -> MLO hei_generic_bank_dlc (teller)
```

The same object can be in more than one MLO — change **all of them**.

### Step 6 — Change the name in the MLO entity list

```
powershell -Command "& patch_vanilla_ytyp.ps1 -YtypName 'v_int_10.ytyp' `
  -SwapEntity @('v_ilev_gb_teldr=my_teldr','v_ilev_gb_vauldr=my_vauldr') `
  -OutDir '<...>\stream'"
```

- This file **does NOT get `DLC_ITYP_REQUEST`** — it is a vanilla file replacement.
  Everything in `stream/` is streamed automatically anyway.
- After writing, the script reads the file back; if the signature (`arch / mlo / rooms /
  portals / entities`) differs from the source, or the old model is still there, it
  **deletes** the file. Streaming a broken ytyp breaks the whole MLO.

Expected output:
```
[*] signature: arch=51 mlo=2 rooms=7 portals=7 entities=427
[+] MLO v_genbank: entity v_ilev_gb_teldr -> my_teldr
[*] written signature: arch=51 mlo=2 rooms=7 portals=7 entities=427
    verify: new model in 2 entities, old model left in 0 entities
```

### Step 7 — Runtime

The vanilla object is now **never placed at all**. `CreateModelHide`,
`RemoveModelHide`, spawn, ymap — none of them are needed.

**Pushable door:**
```lua
AddDoorToSystem(h, model, x, y, z, false, false, false)
-- WAIT FOR THE PHYSICS TO LOAD, otherwise the next call is silently dropped
while not DoorSystemGetIsPhysicsLoaded(h) and GetGameTimer()-t < 3000 do Wait(50) end
DoorSystemSetDoorState(h, 0, true, true)   -- 0 = unlocked
```

**Animated fragment:**
```lua
PlayEntityAnim(obj, clip, dict, 1000.0, false, true, false, 0.0, 0)
-- DO NOT FREEZE. The root group carries the body, so it does not tip over.
```

### Step 8 — STREAMING: applying the state once is NOT ENOUGH

When the player moves away the MLO unloads; on return **the entity is created again**.
At that moment:

- the door system state **goes back to the default (locked)**
- an animation playing on the fragment **is lost**

Symptom: "after a while the door locks itself again". In the first
version I kept a cache `doorRegistered[hash] = true` and never applied the state
again — that was exactly the bug. **Do not cache, VERIFY the state
periodically:**

```lua
CreateThread(function()
  while true do
    local wait = 1500
    if nearest(DOOR) then
      -- register if not registered (idempotent)
      if not IsDoorRegisteredWithSystem(h) then AddDoorToSystem(h, model, x,y,z, false,false,false) end
      -- if physics is not ready do not touch it, check again on the next pass
      if DoorSystemGetIsPhysicsLoaded(h) and DoorSystemGetDoorState(h) ~= 0 then
        DoorSystemSetDoorState(h, 0, true, true)
      end
      wait = 2000
    end
    Wait(wait)
  end
end)
```

On the fragment side: **keep the entity handle**. If the handle changed, the interior
was reloaded; apply the wanted state again. Start the animation
with `delta = 1.0` (from the end of the clip), otherwise on every return the player
watches the door open from the start.

### Step 9 — UPDATE EVERY PLACE THAT LOOKS FOR THE OLD MODEL NAME

The moment you change the model name, **all** code and config that look for that name break —
but silently. They cannot find the object and give no error.

```
grep -rn "<old_model>" --include=*.lua config/ data/ modules/ core/
```

Real example: `config/heists/fleeca.lua` was still looking for `v_ilev_gb_teldr`.
Result: the door module could not recognise the door, the lock logic fell to the wrong side and
the door locked again every time the player came within 60 m.

### Lock/state conflict — single authority rule

If **two modules** write state to the same object, the last writer wins and the behaviour
looks random. Symptom: diagnostics say `state=0` (unlocked) but the door
does not open.

The cause is usually this: the lock is applied not only through the door system but also **by
freezing the entity** —
`FreezeEntityPosition(obj, isLocked and not isOpen)`. A frozen entity is not affected
by the door system, so `DoorSystemGetDoorState` misleads.

Rule: **let a single module manage the lock.** Do not let your new module race it;
point its config at the new model name, that is enough.

### "I fixed it, now it does not open at all" — false regression

The moment you point the config at the right model name, the lock logic that had **never
worked** until then kicks in for the first time. The door comes locked and it looks like
a breakage — while it is by design (`Config.Doors.Types.teller.locked =
true`, the door is a robbery target).

If the door "worked" before, the reason is that the lock module never
found the object. So the choice is: the lock never works, or it works and the door
stays closed.

To make a physical test possible, add **an explicit override command** —
not a loop that silently overrides all the time:

```lua
-- The lock has TWO layers: door system state + entity freeze.
-- Writing state 0 alone is NOT ENOUGH; a frozen entity does not move.
FreezeEntityPosition(door, false)
if DoorSystemGetDoorState(h) ~= 0 then DoorSystemSetDoorState(h, 0, true, true) end
```

While the override is on, reapply it at a short interval (~0.5 s): when the player
comes in range the lock module puts the lock back. Turn it off and authority returns to that module.

---

## 5. GENERAL PITFALLS (caught in this work)

- `SetEntityCollision(mapObj, false, false)` is **not reliable** on a map object
  — the object becomes invisible, the collision stays in place. If you need to hide it,
  use `CreateModelHide(x,y,z,r,hash,true)`.
- A clip that animates only the root bone (tag 0) moves the object **itself**.
  `FreezeEntityPosition(true)` blocks this completely: the clip plays,
  `PlayEntityAnim` returns true, nothing happens on screen.
- First check whether a clip that animates an inner part of a prop **exists**:
  take the model's bone tags from `skeletons.tsv.gz`, search the `bones` column of
  `clips.tsv.gz`. (Example: a clip that touches the drawers of `hei_prop_heist_deposit_box`
  does NOT exist among 312,748 clips.)
- There is **no** such thing as "collision animation" with `.yed` (expression).
  The `.yed` in the reference file was opened: it holds **0 expressions**, a 166-byte
  empty shell, not even registered in the fxmanifest. What did the work was the fragment structure.

---

## 6. WHAT YOU NEED TO TELL ME

For a similar job, tell me these three and I go straight into this recipe:

1. **Which object** — model name (`v_ilev_gb_teldr`) or "let me measure it in game"
2. **What you want it to do** —
   - "push like a normal door"
   - "open with an animation, and its collision moves with it"
   - "just change the model"
3. **Where** — like "inside the Fleeca". Interior or outside is
   the first thing to decide.

Short version, copy and use:

> I want to replace the `<model_name>` object with our own model.
> It is inside `<MLO name / place>`. It should be `<pushable door | animated + collision
> following | model only>`.
> Apply the `skills/fivem-assets/branches/map/mlo-object-swap.md` recipe.


---

## Old trunk summary — rejected ways and the working way

## FIXING AN OBJECT ON THE MAP (do not spawn — change the ytyp)

If a prop standing on the map is defined wrong (an object that should be a door has
`specialAttribute=0`), **do not hide it and spawn your own copy in its place.**
This way was tested and failed:

- An object created by script **is not a map object**. The door system looks for the door
  by model+position on the map and cannot find the script object.
- A loose physics prop is left: in game, when the door was touched it
  fell through the floor.
- Stop the fall with `FreezeEntityPosition` and the door system
  cannot push it — you gain nothing.

Other ways tried and **rejected** (all by in-game measurement):

- **Placing with your own ymap** — DOES NOT WORK INSIDE AN MLO INTERIOR. The room/portal
  system culls an entity placed from outside; the object never appears. It only applies
  to props outside the MLO (street, open area). Do not let a reference
  resource's use of a ymap mislead you — **first check whether that prop's
  coordinate is inside the MLO or outside.**
- **Fixing `specialAttribute` in the vanilla prop ytyp**
  (like `int_lev_des.ytyp`) — the file was produced correctly (348/348 archetypes
  identical) but door physics still did not load in game.
- **Adding a NEW ytyp with the vanilla name** — the game has already registered
  the first definition, so it conflicts and does not take.

**THE WORKING WAY: change the model name in the MLO's own entity list.**

The MLO ITSELF places the object: in the right room, at the right position, without hiding /
ymap / spawn, in every place where that MLO exists on the map at once.

```
patch_vanilla_ytyp.ps1 -YtypName v_int_10.ytyp `
  -SwapEntity @('v_ilev_gb_teldr=my_teldr','v_ilev_gb_vauldr=my_vauldr') `
  -OutDir <...>\stream
```

- `data_file 'DLC_ITYP_REQUEST'` is **NOT ADDED** — this is a file replacement,
  not a new ityp registration. `stream/` is streamed automatically anyway.
  (For your own new ytyp it IS ADDED.)
- After writing, the script reads the file back, compares the signature (archetype / room /
  portal / entity counts) with the source and counts how many entities the new model is in;
  if it does not match, it deletes the file. Streaming a broken ytyp breaks the whole
  MLO.

Full step-by-step recipe: above

### Removing a map object's collision

`SetEntityCollision(mapObj, false, false)` is **not reliable** — the object
becomes invisible but the collision stays in place. Symptom: the door you swapped
looks open, yet you cannot pass. The right way is `CreateModelHide(x,y,z,r,
hash, true)`; to undo, `RemoveModelHide` (forget it and the map object
never comes back). The hide call invalidates the handle, so turn off the collision
**first**.
