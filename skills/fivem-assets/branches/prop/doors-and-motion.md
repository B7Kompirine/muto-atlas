# Door won't open / object won't move / lock / coordinates

**When to read:** the door won't open or a map object won't move, `AddDoorToSystem` does not hold, the object freezes, the door is defined wrong (`specialAttribute` door table), locking, or you are about to write a position into a config.
**Source:** old SKILL 'specialAttribute — DOOR TABLE', 'LAYERS OF MOVING AN OBJECT', 'IF THE ARCHETYPE IS DEFINED WRONG', 'Root-bone clips', 'COORDINATES' (2026-07) · **Measured:** distribution over 316,975 archetypes; Fleeca in game
**Read first:** `_branch.md` · trunk › `trunk/flags.md` (`specialAttribute`), `trunk/tool-pitfalls.md` §1 · if the object is inside an MLO, the fix is `branches/map/mlo-object-swap.md`

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" door  <name>   # does it open like a door
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" show  <name>   # pivot, bbox, physics, ytyp
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" where <name>   # in how many places on the map
```

## specialAttribute — DOOR TABLE

Verified from the distribution of 316k archetypes, not a guess:

| Value | Meaning | Does the door system work |
|---|---|---|
| **7** | hinged door | ✅ yes — `AddDoorToSystem` + `DoorSystemSetDoorState` |
| **8** | sliding door | ✅ yes |
| **5** | garage / rolling door | ✅ yes |
| **10** | roller shutter / elevator door | ✅ yes |
| **12** | railway barrier | ✅ yes |
| **0** | NOT a door | ❌ no — the object does not move even when registered |
| other | plant, furniture, traffic, SLOD... | ❌ no |

If `specialAttribute = 0`:
1. The door system **does nothing** — not worth trying.
2. The only in-script way: rewrite the transform with `SetEntityHeading`.
   For that to look right the pivot has to be on the edge → the bbox
   comment in the `show` output tells you.
3. The permanent correct fix: give it `specialAttribute = 7` with a ytyp override.

## LAYERS OF MOVING AN OBJECT

When you want to move a world object, verify in this order:

1. **Ownership** — `SetEntityAsMissionEntity` + `NetworkRequestControlOfEntity`.
   Without control, `FreezeEntityPosition` / `SetEntityCoords` /
   `SetEntityHeading` are **silently ignored**. This is the step skipped most often.
2. **Physics** — `FreezeEntityPosition(false)` alone is not enough; if the object is
   flagged "static", `SetEntityDynamic(true)` + `ActivatePhysics()` are needed.
3. **Hinge** — the door system only kicks in when `specialAttribute` fits.
4. **Sync** — map objects are NOT networked. Keep the state on the server and
   let every client apply it to its own copy; otherwise it only moves for you.

## IF THE ARCHETYPE IS DEFINED WRONG — ytyp override

If an object is defined wrong in its ytyp (something that should be a door has
`specialAttribute=0`), the correct fix is not a script but a ytyp correction:

```bash
powershell -File "${CLAUDE_PLUGIN_ROOT}/scripts/make_ytyp_override.ps1" `
    -Models v_ilev_gb_teldr -SpecialAttribute 7 `
    -YtypName <unique_name> -OutFile "<resource>\stream\<name>.ytyp"
```

It reads the source archetype from the RPF, **copies every field one to one** and changes only
the requested value — no invented fields. The output goes into the `stream/` folder
and is declared in fxmanifest with `data_file 'DLC_ITYP_REQUEST'`.

Warning: **every place** that uses the same archetype is affected (6 bank
branches in the Fleeca example). See the scope first with `assetdb.py where <model>`.

## Root-bone clips do not play on a frozen object

If a clip only animates tag 0, it moves the object **itself**, not an
inner part. `FreezeEntityPosition(obj, true)` blocks this completely:
the clip plays, `PlayEntityAnim` returns true, nothing happens on screen.
Unfreeze the object before playing a clip with root motion.



## COORDINATES — before hard-coding them in a config

If you need a coordinate for a prop/door, **do not ask the player; take it from the index**:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" where v_ilev_gb_teldr
# -> 6 unique locations (6 Fleeca bank branches)
```

Watch two things:

1. **The same prop can be in more than one place on the map.** The Fleeca teller door exists in 6
   bank branches. Do not build the config around one coordinate; either write all of them or
   search around the player.
2. **Locations marked `[mlo]` belong to an interior** — that prop only exists while that MLO
   is loaded. The square brackets in the `near` output tell you which MLO it
   is.

## Removing a map object's collision

`SetEntityCollision(mapObj, false, false)` is **not reliable** — the object becomes invisible but the collision stays. The right way is `CreateModelHide(x,y,z,r,hash,true)`; undo it with `RemoveModelHide` (if you forget, the object never comes back). The hide call invalidates the handle, so turn the collision off **first**.
