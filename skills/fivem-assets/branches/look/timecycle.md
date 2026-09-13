# Timecycle — dark/gloomy room, weather cycle, wet map, sun leaking into an MLO

**When to read:** "why is it dark", "the interior stays bright", "the floor shines as if wet", the room is dark or washed out; a modifier for mood, applying a timecycle modifier to an MLO, `TIMECYCLEMOD_FILE`; a weather cycle; a wet map.
**Source:** `lights.md` 'Timecycle layer', 'wet', 'MLO room' · `decal.md` §5 · morgue MLO notes (2026-08) · **Measured:** 1,087 modifiers + 17 weather cycles (`timecycle.tsv.gz`); v_coroner room flags; casino vault / facility 111
**Read first:** `_branch.md` · trunk › `trunk/tool-pitfalls.md` §1-2

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" cycle w_clear --hour 20   # 1. base weather cycle
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" timecycle <modifier>     # 2. the room's modifier
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <file>           # 3. the prop's light
```

A darkness complaint **has three layers** and they are checked in order: base weather cycle → the room's modifier → the prop's light. The answer is usually not in the third.

## Timecycle layer

How a scene looks is three layers, in this order:
**base weather cycle → the room's modifier → the prop's own light.**
If you are saying "I set the light up right but it is still wrong", look at the first two.

Measured, not to be guessed:

- A cycle file has the structure `cycle > region > <variable>text</variable>`
  and the text carries one value **per keyframe**. **There are 13 keyframes, not 24
  hours.** Assuming "hour = index" shifts everything.
- The hour schedule is in a separate file and **there are two `time.xml` files**. The right one is
  `common.rpf\data\levels\gta5\time.xml` (13 samples);
  `common.rpf\data\time.xml` is a completely different file with 4 samples.
  Hours: `0 5 6 7 10 12 16 17 18 19 20 21 22`
- ⛔ A sample says `name="09:00"` but carries `hour="10"`. **The name lies,
  the `hour` attribute is what counts.** Reading the name shifts every later keyframe by one hour.
- Colors are already 0–1 (measured max 1.002); there is no /255 anywhere
- `light_dir_mult` is HDR and goes up to **54** — clipping is not optional
- There is a region layer: `GLOBAL` and `URBAN`
- A modifier is **a blend, not a replacement**: `base + (mod − base) × strength`,
  and it works per param (a modifier can zero natural while leaving artificial
  untouched). The modifier table holds two values per param;
  the **first** one is the one that applies.

> **The clip ceilings are calibration, not engine constants.** `AMBIENT_CAP` / `SUN_CAP`
> in `cycle.py` are parameters; verify them against a vanilla
> image, do not treat them as embedded constants.

---

## 5. TIMECYCLE

Darkness **has three layers**, checked in order:
**weather cycle → the room's modifier → prop lights.** The answer is usually
not in the third.

### DO NOT TOUCH a shared modifier
`morgue_dark` is defined in **6 DLC files** and the whole morgue shares it.
Which one wins depends on the DLC load order and **cannot be read from the data.**
→ Write your own modifier and change the room's `timecycleName` in the ytyp.

### Schema (copied from vanilla, not made up)
```xml
<timecycle_modifier_data version="1.000000">
  <modifier name="my_mlo_dark" numMods="44" userFlags="0">
    <natural_ambient_multiplier>0.045 0.000</natural_ambient_multiplier>
    ...
  </modifier>
</timecycle_modifier_data>
```
The element text is `"value1 value2"`. `numMods` must match the real element count.

### FiveM registration is REQUIRED
```lua
files { 'data/timecycle_mods_custom.xml' }
data_file 'TIMECYCLEMOD_FILE' 'data/timecycle_mods_custom.xml'
```
Without registration the game **does not look for** the modifier and the room stays vanilla.

### The four most effective parameters for mood (measured effect)
| Parameter | vanilla morgue_dark | dark |
|---|---|---|
| `natural_ambient_multiplier` | 0.154 | 0.045 |
| `artificial_int_ambient_multiplier` | 0.632 | 0.300 |
| `ssao_inten` | 6.300 | 9.500 |
| `postfx_vignetting_intensity` | 0.000 | **0.550** ← most visible difference |

**Do not lower** `fog_start` (73 → 4 was tried and not liked — if you do not want fog
in the interior, leave it at the vanilla 73).

---

### ⛔ "THE MAP IS WET" HAS TWO SEPARATE PATHS — fixing one does not close the other

The vertex `R = 0` rule above closes **natural ambient leaking in**. Surface
wetness is **a separate global path** and R does not close it. Putting one in place of
the other burns a round: after R was set to 0 on 228/228 models the map
was still getting wet, because the cause was never there.

**If the symptom depends on time, do not look at the asset side.** "After working inside
for 15 minutes it is wet again" — the file did not change, so the source is at runtime.

### `SetRainLevel` does NOT REMOVE wetness

`_SET_RAIN_LEVEL` (lua: `_SetRainLevel`, alias `SetRainLevel`,
`0x643E26EA6E024D92`) is the rain **intensity**. Surface wetness is driven by the
**weather type itself**. As long as the type stays `RAIN`, zeroing the rain level
changes nothing.

⚠️ One round got the wrong diagnosis "this native does not exist". In the index the lua name is
`_SetRainLevel`, in lua-defs it is `SetRainLevel` — **both exist in FiveM**.
`GET_RAIN_LEVEL` is `GetRainLevel`.

### You cannot WIN A RACE against qb-weathersync — stop its loop

Measured (`qb-weathersync/client.lua`): the main loop runs with **`Wait(100)`** and
rewrites these **every iteration**:

```
ClearOverrideWeather / ClearWeatherTypePersist
SetWeatherTypePersist(lastWeather) / SetWeatherTypeNow / SetWeatherTypeNowPersist
RAIN -> SetRainLevel(0.3)   THUNDER -> SetRainLevel(0.5)
```

A 500 ms suppression loop **loses 5 to 1** against this. Writing every frame is not a fix
either: in the frame qb writes, the type is `RAIN` again.

**The right way is to stop qb:**

```lua
TriggerEvent('qb-weathersync:client:DisableSync')   -- disable = true
-- on exit:
TriggerEvent('qb-weathersync:client:EnableSync')    -- asks the server for the state
```

It is registered with `RegisterNetEvent`, so `TriggerEvent` works locally.

⛔ **`DisableSync` PINS THE CLOCK TO 18:00** (`client.lua:25`,
`NetworkOverrideClockTime(18,0,0)`). A tuned dark interior tone is fed by the clock,
so this shifts that tone. **Read the time before entering, then
put it back:**

```lua
local h,m,sn = GetClockHours(), GetClockMinutes(), GetClockSeconds()
TriggerEvent('qb-weathersync:client:DisableSync')
NetworkOverrideClockTime(h, m, sn)
```

⛔ **If the resource stops, the player is left with "weather sync off"** — call `EnableSync`
in `onResourceStop`.

Mechanism: `Config.DynamicWeather = true` → the weather changes every 10 minutes →
the loop regularly enters `RAIN`/`THUNDER`. That is exactly the period of the
"it comes back every 15 minutes" complaint.


## Outside light entering an MLO room = ROOM FLAG, not geometry

⛔ **If the sun leaks into a dark interior, the first place to look is not the shell/cube
but the room's own `flags` field.** Directional light (sun/moon) in GTA is
not blocked by geometry; it is switched off **with the room flag**. A shell only
creates a *shadow*, and the shadow map resolution is not enough at the edge → bright dots
lined up along the edge (shadow acne). The symptom looks like "tearing"
and pushes you to fix the geometry; the cause is not there.

**Room flag bits — Sollumz `RoomFlags` enum (NOT a guess):**

| bit | value | name | bit | value | name |
|---:|---:|---|---:|---:|---|
| 0 | 1 | Freeze Vehicles | 5 | 32 | Reduce Cars |
| 1 | 2 | Freeze Peds | 6 | 64 | Reduce Peds |
| **2** | **4** | **No Directional Light** | 7 | 128 | Force Directional Light On |
| **3** | **8** | **No Exterior Lights** | 8 | 256 | Dont Render Exterior |
| 4 | 16 | Force Freeze | 9 | 512 | Mirror Potentially Visible |

Source: `sollumz/ytyp/properties/flags.py` → `class RoomFlags`.
The portal table is in the same file, `class PortalFlags` (1 One Way · 2 Link Interiors
Together · 4 Mirror · 8 Disable Timecycle Modifier · 16 Mirror Using
Expensive Shaders · 32 Low LOD Only · …).

⛔ **`assetdb.py flags <n>` GIVES THE WRONG ANSWER for this job** — that tool knows only
the **archetype/entity** table; the room/portal table is separate and there is no `--room`
option. It decodes 111 as "Wet Road Reflection | Dont Fade | Draw Last |
Climbable By AI | Static | Disable alpha sorting"; all of it is
irrelevant. This is another face of §2: **a tool can silently answer from a different
table.** Before asking what a field means, check which table the tool
maps that field to.

**Measured vanilla reference** (four MLOs opened this round):

| MLO | rooms | flag |
|---|---|---|
| `ch_dlc_int_09_ch` (casino vault, pitch dark) | 5 | **5/5 → 111** |
| `xm_x17dlc_int_facility` (fully buried) | 18 | **18/18 → 111** |
| `dt1_02_carpark` (underground car park) | 2 | 108 · 104 |
| `v_int_2` (v_coroner, **vanilla**) | 14 | mostly 111, **but** `MainStairs` 99 · `CorridorTop` 107 · `topoff_*` 99/99/**0** |

**111 = Freeze×2 + Reduce×2 + No Directional Light + No Exterior Lights.**
That is the signature of a dark interior. Note: none of them **SETS 256 `Dont Render
Exterior`** — that bit is not needed for darkness, do not set it.

**Rockstar's own logic:** underground rooms 111, above-ground rooms 99/107/0.
So in vanilla `v_coroner` the sun enters the stairwell (`MainStairs`, z extent
**18.6 m**) **on purpose**. If you are making an apocalyptic/dark version, pull these
to 111 one by one; the defect is not in your change but **in vanilla itself**,
so a "diff against vanilla" check will NEVER catch it. The reference must not be
the same vanilla file but **another vanilla MLO doing the same job**.

Do not touch the ped/vehicle population bits: apply only `flags |= 4|8`.
Do not touch the `limbo` room (always 96 in vanilla).

**Write pipeline:** `ytyp_to_xml.ps1` (script not in the repository) → patch `flags` in the XML →
`meta_xml_to_bin.ps1` (for `.ytyp`/`.ymap`; `xml_to_res.ps1` does NOT
RECOGNIZE these two) → read back. Round-trip losslessness is verified **per node**:
measured, of 14,257 nodes 0 lost / 0 added / exactly 5 changed.

---
