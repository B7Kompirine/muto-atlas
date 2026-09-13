# Attaching a prop to a bone — offset table, rotationOrder, live adjustment editor

**When to read:** you are attaching a prop to a ped bone (hand · forearm · back), porting another script's offset table (dpemotes, ox_lib, qb progressbar), or writing an editor that adjusts the offset live in game; "it looked right there, it is crooked here".
**Source:** PERPGamer/pg_attachproptoplayereditor `client.lua` (GPL-3.0, last push 2022-11-03; no new commits in the 19 listed forks) · citizenfx/natives `ATTACH_ENTITY_TO_ENTITY`, `GET_ENTITY_ROTATION` · andristum/dpemotes `Client/Emote.lua:260` + `AnimationList.lua` · overextended/ox_lib `progress.lua:66` · qbcore-framework/progressbar `client.lua:74` (2026-09-10) · **Measured:** source reading (4 scripts) + numeric comparison of Euler orders (4 angle triples, 2026-09-10). **No in-game test.**
**Read first:** `_branch.md` (hand tags, ORIGIN = grip contract) · trunk › `trunk/bone-tags.md` (tag ≠ index)

---

## 1. The call — what the tail means

```lua
AttachEntityToEntity(prop, ped, GetPedBoneIndex(ped, tag), x, y, z, rx, ry, rz,
    true,   -- p9: no effect
    true,   -- useSoftPinning
    false,  -- collision: false → the prop does not push the ped
    true,   -- isPed: when false, pitch does not work and roll only works when negative
    1,      -- rotationOrder: the ORDER in which rx/ry/rz are applied (0-5)
    true)   -- syncRot: false → the entity rotation is ignored
```

- In the four scripts examined the tail is `true, true, false, true, N, true` — **only `rotationOrder` changes**.
- An invalid bone index → the prop is attached to the entity's **centre**, no error (official docs).
  How it looks in game: floating beside the body → `branches/map/mlo-props.md`.

## 2. ⛔ An offset table is ported together with its `rotationOrder`

| source | `rotationOrder` |
|---|---|
| dpemotes `PropPlacement` · pg editor | **1** (`ROT_YZX`) |
| ox_lib `lib.progressBar` prop | `prop.rotOrder or 0` → default **0** (`ROT_ZYX`) |
| qb progressbar | **0**, fixed, no field |

At which angles it matters (largest element difference between the two rotation matrices):

| (rx, ry, rz) | 0 ↔ 1 | 0 ↔ 2 |
|---|---|---|
| (−50, 16, 60) | 0.18 **differs** | 0.18 **differs** |
| (−50, 0, 60) | 0 | 0 |
| (−50, 16, 0) | 0 | 0.21 **differs** |
| (0, 16, 60) | 0.24 **differs** | 0 |

- **0 ↔ 1** only diverge when `ry` **and** `rz` are both ≠ 0; **0 ↔ 2** only when `rx` **and** `ry` are ≠ 0.
  A single-axis angle is the same in every order — this is the symptom "some props are right, some are crooked".
- Concrete: a measured burger offset `(0.13, 0.05, 0.02) / (−50, 16, 60)` @ 18905 is **exactly** the dpemotes
  value (order 1). Put into `lib.progressBar` without `rotOrder = 1`, the orientation changes
  (maths; not checked in game). That ox_lib exposes a separate `rotOrder` field hints that the difference was seen in game; it is not proof.
- When porting: if the target lets you choose the order, give it the source's order; if it does not (qb), re-tune the angle.

## 3. Live offset editor

The working path of the pg editor: `/ptpeditor <tag> <model>` → take over the keys with `DisableControlAction`, and on every
change `DetachEntity` + the same `AttachEntityToEntity`. A token such as `~INPUT_CELLPHONE_LEFT~` in the help text
draws the icon of the player's **own key binding**.

The 2022 flaws of the same code — for when you write your own editor:
1. **Position and angle share one step** (0.01): angle 0.01°/frame → at 60 fps 90° ≈ 150 s; position, with the key held,
   60 cm/s. Separate steps: ~0.005 m and ~1°.
2. **The step is per frame** (`IsDisabledControlPressed` adds on every frame) → the speed depends on FPS. Multiply by `GetFrameTime()`.
3. **The step has no lower bound** → at 0 the keys freeze, when negative they work in reverse.
4. **The on/off flag is flipped before validation** → after an attempt with an invalid model the first valid command
   does not open the editor, the second one does. Flip the flag on a successful start.
5. **The result is lost:** on exit the object is deleted and the numbers were only on screen. On exit `print` the target line —
   tag, the 6 values **and `rotationOrder`**.
6. **No clip is playing:** the offset is in bone space and independent of the pose, but the grip and which hand holds the prop depend on the
   clip (the burger clip uses the **left** hand). Tune while the target clip plays in a loop.
7. **The editor object is networked** (`CreateObject(..., true, true, true)`): everyone sees it during tuning.
   In a tuning tool use `isNetwork = false`.
