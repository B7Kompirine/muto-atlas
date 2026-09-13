# A live, clickable screen on an object (DUI)

**When to read:** ATM keypad, till terminal, camera monitor, laptop, keypad, sign — real HTML/JS should run on an object and be clickable; raycast to UV; jitter when attached.
**Source:** `dui-screens.md` (whole file) + old SKILL summary (2026-07) · **Measured:** 5 models from the RPF; cr-3dnui v2.6 source read; jitter of a bone-attached panel measured
**Read first:** `_branch.md` · trunk › `trunk/flags.md` (`specialAttribute`), `trunk/tool-pitfalls.md` §1

---

## Five things to know before writing code

**`dui-screens.md`** · command: `/prop`

Five things to know before writing code:

- **There are three render paths and the data decides.** If the model has a real screen
  texture, `AddReplaceTexture` (most realistic); if not, a quad in world space
  (`CreatePanel`); on a moving entity, `AttachPanelToEntity`. **Ask which one
  it is, do not try**: `screentex.ps1 -Model <model>`.
- **`AddReplaceTexture` is per material and GLOBAL.** On that client every object
  that uses that texture changes. If a bank has 3 ATMs, all three show the same
  page → if you need different content, this path is wrong.
- **Screen = `emissive*` shader, and the texture is almost always EMBEDDED in the model**
  → `origTxd` = **the model name itself**. Measured: `prop_atm_01` →
  `prop_cashpoint_screen`, `prop_laptop_lester` → `prop_lester_screen`,
  `prop_tv_flat_01` → `script_rt_tvscreen`. **The `textureDict` field in the ytyp
  is NOT the screen dictionary** — do not read it there and write it as `origTxd`.
- **Keypads and CCTV cameras have NO screen texture** (measured on three keypad
  props; `hei_prop_hei_keypad_01` has 0 embedded textures).
  A keypad UI can only be made with a world quad.
- **DUI is client-only and NOT synced.** A panel is not a world object;
  every client builds its own panel. The state is kept on the server and reflected with
  `SendMessage`. **Password/code comparison is done on the server, not in the page** —
  the page's JS can be read and its messages can be faked.

When building a panel: `faceCamera=false` + `frontOnly=true` + an `up` **made
perpendicular** to the normal (unless both are given, the basis cache does not turn on and roll
is not supported), `resW:resH` equal to the panel ratio, the URL file in the consuming resource's
`files { }` list.




---


If you want **a clickable screen running real HTML/JS** on an object,
the path is clear: DUI (Direct UI) → runtime texture → drawing in world space
or material replacement, plus a UV calculation from a camera ray on top.

Source: `cr-3dnui` (codyraves) v2.6 — the library + 4 demos read line by line.
Every item here was **measured** either from that code or from this plugin's asset/native data.
Anything that is a guess is marked as one.

---

## 0. DECIDE FIRST: which of the three render paths

| Path | How it works | When |
|---|---|---|
| **A. World quad** (`CreatePanel`) | 2 triangles with `DrawTexturedPoly`, free position + normal | The model has **no** screen; wall, keypad face, board, empty air |
| **B. Entity-attached quad** (`AttachPanelToEntity` / `...ToBone`) | The same quad, refreshed from entity space every frame | Vehicle, ped, carried prop |
| **C. Material replacement** (`AddReplaceTexture`) | The DUI replaces the model's own screen texture | The model **has a real screen texture**: TV, laptop, monitor, ATM |

Path C looks the most realistic (the screen is inside the model, tilts correctly with the angle,
receives light) **but it has two hard limits**:

1. The model must have a screen texture. Otherwise there is nothing to apply it to.
2. `AddReplaceTexture` is **per material and GLOBAL** — on that client **every** object
   that uses that texture changes. If a bank has 3 ATMs, all three show
   the same page. If each one needs different content, path C is wrong.

> Trying path C on a model without a screen is the most common mistake.
> Whether the model has a screen is **queried, not tried** (§6).

---

## 1. THE DUI CHAIN — five steps, all required

```lua
local dui = CreateDui(url, resW, resH)          -- open a CEF page
local handle = GetDuiHandle(dui)                -- NUI window handle
local txd = CreateRuntimeTxd('my_txd')          -- runtime dictionary
CreateRuntimeTextureFromDuiHandle(txd, 'my_tex', handle)
-- 'my_txd' / 'my_tex' can now be used in drawing natives
DestroyDui(dui)                                 -- cleanup is REQUIRED
```

Verified signatures (plugin native index):

| Native | Signature | Note |
|---|---|---|
| `CreateDui` | `(char* url, int w, int h) -> long` | 0x23EAF899 |
| `GetDuiHandle` | `(long dui) -> char*` | 0x1655D41D |
| `IsDuiAvailable` | `(long dui) -> BOOL` | 0x7AAC3B4C — **not used, should be** (§9.3) |
| `SetDuiUrl` | `(long dui, char* url)` | 0xF761D9F3 — no need to recreate the DUI to change the page |
| `SendDuiMessage` | `(long dui, char* json)` | 0xCD380DA9 |
| `SendDuiMouseMove` | `(long dui, int x, int y)` | **PIXELS**, not UV |
| `SendDuiMouseDown/Up` | `(long dui, char* button)` | `'left'` / `'middle'` / `'right'` |
| `SendDuiMouseWheel` | `(long dui, int deltaY, int deltaX)` | **takes two deltas** (§9.4) |
| `AddReplaceTexture` | `(origTxd, origTxn, newTxd, newTxn)` | docs: "Experimental" |

### URL rule

`nui://<resource_name>/<path>/index.html` — and that file **must be in the
`files { }` list of that resource's `fxmanifest.lua`.** If it is not, the
DUI stays blank/black and raises no error.

`GetParentResourceName()` **may not exist** inside a DUI page. If the page
has to `fetch("https://<resource>/callback")`, pass the resource name
in the query string:

```lua
('nui://%s/html/index.html?res=%s'):format(res, res)
```

(the whiteboard demo does this; `RegisterNUICallback` catches a fetch from the DUI
like normal NUI — so **there is a DUI → Lua return path**; it is not
one-way.)

---

## 2. DRAWING THE QUAD — mirroring, roll and z-fighting

The panel is drawn from four corners; two `DrawTexturedPoly` calls.

```
v1 = c - r*hw + u*hh      v2 = c + r*hw + u*hh
v4 = c - r*hw - u*hh      v3 = c + r*hw - u*hh
```

- `right = cross(normal, up)`, `up = cross(right, normal)` — **right-handed**
  layout. If it is built the other way round, backface culling makes the panel invisible; this is
  the first cause of the complaint "the panel was created but is not on screen".
- If `up` is not given, world up (0,0,1) is used → **roll is not supported**.
  For a tilted monitor, a slanted dashboard, a sign lying on its side, `up` **must be given**.
  If `up` is parallel to the normal, the cross product is zero → the library falls back to (0,1,0);
  so it silently produces a wrong orientation. When you give your own `up`,
  **make it perpendicular to the normal first** (Gram-Schmidt):
  `up_ortho = normalize(up - normal * dot(normal, up))`
- **The UV is given flipped on the U axis** (v1→(0,1), v2→(1,1), v3→(1,0)).
  Without it the text comes out mirrored. If you write your own drawing, do not skip this.
- `zOffset` = how far the panel is pushed out from the surface. Default **0.002 m**;
  with `depthCompensation='screen'` it is **0.004 m** + a slope-dependent extra
  (`min(0.35, |normal.z|) * 0.002`). Too small gives z-fighting (a flickering
  screen); too large makes the panel stand off the surface.

### The `faceCamera` pitfall

`faceCamera=true` turns the normal towards the camera every frame. Result:
- the panel is readable from everywhere ✅
- but **the notion of front/back disappears** — the UI is visible from behind too,
  and the raycast hits from behind too ❌
- and the panel now counts as "dynamic", so **the basis cache is disabled**

For a fixed screen (monitor, ATM, keypad) the right setup is:
`faceCamera = false` + `frontOnly = true` (+ `frontDotMin` if you want).
For a free-standing info sign, `faceCamera = true` makes sense.

### Cache condition (perf)

The library does this:
```
isDynamic = (faceCamera and not frontOnly) or (orientationLock and not up)
```
Unless `isDynamic` is **false**, the corner points are recomputed every frame.
So **a static panel needs both `faceCamera=false` and `up`**;
giving only one of them does not turn the cache on.

---

## 3. RAYCAST → UV — plane intersection

```
denom = dot(dir, normal)              -- |denom| < 0.0001 -> ray parallel to the plane
t     = dot(center - camPos, normal) / denom
hit   = camPos + dir * t
rel   = hit - center
x     = dot(rel, right) / halfW       -- |x| > 1 -> outside the panel
y     = dot(rel, up)    / halfH
u = (x+1)/2 ;  v = (y+1)/2            -- 0..1
px = u * resW ;  py = v * resH        -- PIXELS sent to the DUI
```

Two consequences follow:

1. **This is not a shape test.** The ray intersects an infinite plane; it counts as a hit
   even if there is a wall in front of the panel. If you care whether something is in
   between, cast a separate `StartShapeTestRay` and compare the distances.
2. **`resW`/`resH` set both sharpness and click precision.** If the panel
   is 1.0 m wide and `resW=512`, one pixel is ~2 mm in the world.
   In a UI with small buttons, clicking feels "stepped". The panel ratio and
   the DUI ratio **must match** — a square DUI on a wide panel stretches the UI
   and shifts the hit point.

Suggested start: wide panel `1024×512`, square panel `1024×1024`. With dense
text, `2048×1024`.

---

## 4. ATTACHING TO A MOVING ENTITY — the real cause of jitter

`AttachPanelToEntity`, on every tick:
```
pos    = GetOffsetFromEntityInWorldCoords(ent, off.x, off.y, off.z)
normal = localNormal rotated by the entity matrix
```
and **one central thread** does this (`updateInterval`, `nextUpdate`).
If every consumer opens its own 0-tick loop, the update cadence becomes inconsistent
and the panel "steps" relative to the vehicle. **Do not write** your own loop; use the library's
driver.

- `updateInterval = 0` → every frame (smoothest, most expensive)
- `updateMaxDistance` → skips the transform update when far away
  (drawing is limited separately by `renderDistance` anyway)

### Measured finding: bone-attached prop + panel attached to the prop = jitter

cardemo tries three modes and the result is clear:

| Mode | What the panel is attached to | Result |
|---|---|---|
| `roof` | directly to the vehicle | no jitter |
| `dashprop` | to a bone-attached prop | **jitters** (left in as a reference mode) |
| `dashstable` | the prop's pose **baked** into vehicle space, attached to the vehicle | no jitter |

Cause: the bone transform and the entity transform are not refreshed at the same moment
in the same frame; the two-level chain produces a phase difference. The fix is to shorten the chain:

1. Attach the prop to the bone (for the **visual** only).
2. Convert the panel's prop-local pose to world space, and from there to **vehicle-local** space
   (`GetOffsetFromEntityGivenWorldCoords` + matrix projections).
3. Attach the panel to the **vehicle**, not to the prop.

This is all there is to what was called "vehicle ROT solved". The same rule holds for panels
attached to peds/props: **attach the panel to the highest stable entity possible
in the hierarchy.**

---

## 5. INTERACTION — three input models

| Mode | Where the cursor is | When |
|---|---|---|
| `uv` | screen centre (crosshair) — camera ray | A large panel on a wall; the player clicks by looking at it |
| `native_mouse` | the real NUI cursor (`GetNuiCursorPosition` → `GetWorldCoordFromScreenCoord`) | When NUI focus is already open |
| `key2dui` | a virtual cursor locked to the panel, driven by mouse delta | Laptop/terminal — camera fixed, the cursor moves on the screen |

### key2dui — measured details

```lua
DisableControlAction(0, 1, true)   -- LOOK_LR   (we take the delta ourselves)
DisableControlAction(0, 2, true)   -- LOOK_UD
DisableControlAction(0, 24, true)  -- ATTACK    (so it does not fire)
DisableControlAction(0, 25, true)  -- AIM
DisableControlAction(0, 257, true) -- ATTACK2
local dx = GetDisabledControlNormal(0, 1)
local dy = GetDisabledControlNormal(0, 2)
u = clamp01(u + dx * speed)        -- speed: 0.010 (whiteboard) … 0.030 (laptop)
v = clamp01(v + dy * speed)
```

- **Do not draw the cursor on the HUD; have it drawn INSIDE the DUI.** The whiteboard demo
  turns the HUD cursor off on purpose: a quad in world space and a sprite in screen space
  do not line up in perspective, which gives a "double cursor" and a sliding feel. The right way is
  to have the page draw the cursor itself with
  `SendMessage(panelId, {type='cursor', u=…, v=…})`.
- Do not send the cursor message every frame: the whiteboard demo throttles it with a **0.002 UV movement
  or 33 ms** threshold. Without throttling, ~60 JSON messages per second go out.
- **Do not miss** the mouse button release: mode change, leaving the panel, resource
  stop — call `SendMouseUp` in all of them, otherwise the page stays "pressed"
  (on the whiteboard that means the brush stays stuck).

### Keyboard — there is no real keyboard

**There is no native that injects a key event** into a DUI. What cr-3dnui does
is read the control with `IsDisabledControlJustPressed` and send the DUI a **message**:

```json
{ "type": "key", "key": "W", "code": 32 }
```

What this means:
- only **press** exists; no key-up, auto-repeat or modifiers
- **no text input** → if you need text, `DisplayOnscreenKeyboard`
  (the whiteboard demo does this: freeze the player → open the keyboard →
  `UpdateOnscreenKeyboard()` loop → send the result to the DUI as a message)
- **you** write which control maps to which letter with `SetFocusKeymap`

`BeginFocus(panelId, opts)` options (measured defaults):
`maxDist=7.0` · `strict` → `DisableAllControlActions(0)` ·
`autoExitOnMiss` + `missGraceMs=250` (so small misses do not exit at once) ·
`exitControls={200,177}` (ESC/BACKSPACE) · `allowLook` (camera free) ·
`sendFocusMessages` → `{type='focus', state=true/false}` to the page.

> The README says `focus_on` / `focus_off`; **the code sends `{type='focus', state=…}`.**
> If you write the page from the README, the focus message is never caught.
> The source tells the truth, not the README.

---

## 6. DOES THE MODEL HAVE A SCREEN — query, do not try

`AddReplaceTexture(origTxd, origTxn, …)` needs two names and **neither can be
guessed**: the prop name and the txd name are often different, a prop has 5-10 textures
and the name does not tell you which one is the screen. That is why the cr-3dnui laptop
demo keeps a list of 10 candidates and cycles through them one by one with `/lapnext`.
That is guessing. We have a query:

```bash
powershell -NoProfile -ExecutionPolicy Bypass \
  -File "${CLAUDE_PLUGIN_ROOT}/scripts/screentex.ps1" -Model <model> -All
```

### Measured results (5 models, straight from the RPF)

| Model | Screen texture | Shader | Dictionary |
|---|---|---|---|
| `prop_atm_01` | `prop_cashpoint_screen` | `emissive` | embedded → **origTxd = `prop_atm_01`** |
| `prop_laptop_lester` | `prop_lester_screen` | `emissive_speclum` | embedded → origTxd = `prop_laptop_lester` |
| `prop_monitor_01a` | `prop_moniter_desktop_01` | `emissive` | embedded → origTxd = `prop_monitor_01a` |
| `prop_tv_flat_01` | `script_rt_tvscreen` | `normal_spec_emissive` | embedded → origTxd = `prop_tv_flat_01` |
| `hei_prop_hei_keypad_01` | **NONE** (`Prop_Hei_LED_1` is only the LED strip) | — | embedded texture count **0** |
| `ch_prop_casino_keypad_01` | **NONE** (no emissive shader at all) | — | — |
| `prop_cctv_cam_01a` | **NONE** (a single shader) | — | — |

Rules that follow from this:

1. **Screen = `emissive*` shader.** It came out that way in all four. But that alone is not
   enough: `prop_tv_flat_01` has **two** emissive shaders, and the second
   (`prop_base_blue_03`) is not the screen but the **stand-by LED**. The right pick
   is the texture among the emissive shaders whose name contains `screen`/`scr`/`rt`.
2. **The `script_rt_*` name is special** — that texture is already reserved for the game's named render target
   system (`prop_tv_flat_01` → `script_rt_tvscreen`).
   If such a texture exists, it is the target.
3. **The screen texture is almost always EMBEDDED in the model** → `origTxd` =
   **the model name**. 4/4 came out that way. An external dictionary search (`-Deep`) takes minutes
   and is usually unnecessary.
4. **The `textureDict` field in the ytyp is NOT the screen dictionary.**
   `prop_monitor_01a`: ytyp `textureDict = 3126464848 → prop_desk_monitor.ytd`,
   but the screen texture is inside the model. Do not read this field in the `assetdb.py show` output
   and write it as `origTxd`.
5. **Keypads have no screen.** No screen texture came out of three different keypad props;
   `hei_prop_hei_keypad_01` has zero embedded textures. So
   **a keypad UI cannot be made with path C** — path A (a world quad aligned to the keypad's front
   face) is the only option. The same holds for a CCTV camera.

---

## 7. PERFORMANCE — how the library scales

Cadences in the source (`CR3D.CONFIG`):

| Setting | Value | What it does |
|---|---|---|
| `renderDistance` | 50.0 m | a panel farther than this is not drawn |
| `idleWait` | 100 ms | if no panel is near, the render loop sleeps |
| `activeWait` | 0 ms | every frame while drawing |
| `renderCheckInterval` | 500 ms | player position cache |
| `candidateScanInterval` | 250 ms | candidate list scan (default **off**) |
| `focusIdleWait` | 100 ms | while focus is off |
| `ATTACH_MAX_WAIT` | 250 ms | the attach driver sleeps while no panel is attached |

Rules for writing our own consumer:

- Panel drawing is already 0-tick. **Do not open a second 0-tick loop**; if what you
  need is `RaycastPanel`, throttle that too. The whiteboard demo throttles the
  raycast to **50 ms** while not drawing and reuses the last result in the frames between.
- As the panel count grows, `RaycastPanels()` walks all of them. Pre-filter your own list by
  distance (in the demo `nearbyBoards`, refreshed every 250 ms).
- `enableCandidateScan` and `enableCamForwardCull` are **off** by default
  (so behaviour does not change). In a scene with many panels, turn both on.
- Every DUI is a separate browser surface + runtime texture. **Count and
  resolution are directly VRAM.** `DestroyPanel` a panel you do not use;
  `SetPanelEnabled(false)` stops drawing but **keeps holding** the DUI and the
  texture.

---

## 8. SERVER AUTHORITY — DUI is entirely client-side

This section is binding for every script that builds an interactive screen.

- `CreateDui` and all cr-3dnui exports are **client-only**. A panel is not a world
  object; it is **never synced**. Other players do not see your panel,
  and you do not have it either unless you create it.
- If everyone should see a keypad screen, **every client builds its own
  panel**; what is shared is the *state* on the server.
  Pattern: the server holds the state → broadcasts it with `TriggerClientEvent` → every client
  reflects it into its own DUI with `SendMessage`.
- **Password/code checks are never done in the page.** The DUI page is on the client,
  its JS can be read and `SendMessage` can be faked. The page only
  carries the entered value to Lua; **the comparison is done on the server** and the server
  tells the result.
- `AddReplaceTexture` is client-wide, and **if it is not undone when the resource
  stops, the texture stays broken**. `RemoveReplaceTexture` + `DestroyDui`
  must be called in `onResourceStop` (cr-3dnui does this; our own
  wrapper must too).

---

## 9. PITFALL CATALOGUE — so it does not happen again

1. **The panel was created but is not on screen.** Check in order: (a) is `up` parallel to the normal
   (the basis collapses), (b) is the right-handed layout broken → backface culling, (c) the URL
   is not in `files{}`, (d) you are outside `renderDistance`.
2. **Mirrored text.** The U axis was not flipped. The library does this;
   if you write your own drawing, do not skip it.
3. **The first frame is black.** The runtime texture is empty until the DUI paints for the first time.
   The laptop demo waits a fixed 200 ms — **that is a guess**. The right way is
   to wait for `IsDuiAvailable(dui)` and only then show it.
4. **`SendMouseWheel` is half done.** The native `SendDuiMouseWheel(dui, deltaY, deltaX)`
   takes two deltas; cr-3dnui passes only one. If you use horizontal
   scrolling, pass the second one yourself.
5. **`SetPanelUrl` recreates the DUI.** If only the page changes,
   `SetDuiUrl` is enough — rebuilding the CEF instance and the runtime texture
   is a needless cost. Recreating is needed **only when the resolution changes**.
6. **The README and the code disagree** (focus message, §5). In an integration the source
   is what counts.
7. **`DrawSpritePoly` is not in the index.** The canonical name is `DrawTexturedPoly`
   (`0x29280002282F1928`, alias `_DRAW_SPRITE_POLY`). cr-3dnui uses the old name
   and it works, but **write the canonical name in our own code** — otherwise
   `/native-lint` flags it as an invented native.
8. **If there is a wall in front of the panel, it still gets clicked** (§3.1). If it matters, cast a
   separate shape test.
9. **`faceCamera=true` + `frontOnly=true` together make no sense** — the library
   already skips turning to the camera when `frontOnly` is set. Writing both is
   not "two safeguards"; one of them is silently ignored.
10. **A native `<select>` does not work in a DUI.** If you need a dropdown, write it with your own
    div (the whiteboard demo has an example).
11. **Mouse button stuck down** (§5). `SendMouseUp` on every exit path.
12. **If the player is frozen and never released, the game locks up.** In a flow that opens the on-screen keyboard,
    `FreezeEntityPosition(ped, false)` must also be called in `onResourceStop`.
13. **Panel count = DUI count = browser count.** Showing the same page on 10 objects
    means 10 CEF instances. If the same content is enough, consider one panel + one
    DUI **drawn** at different positions (the library does not support this;
    add it if needed).

---

---

## 9b. cr-3dnui v2.6's OWN FLAWS (found by reading the source)

Not knowing these before using it costs hours. All three are in the same export:
`AttachPanelToBone`.

**1. `AttachPanelToBone` silently cancels the attachment on the first tick.**
The panel table is keyed by **string** (`PANELS[tostring(id)]`), but this export
writes the attachment with a **number** key:

```lua
ATTACHMENTS[panelId] = { ... }        -- AttachPanelToBone  (number)
ATTACHMENTS[tostring(panelId)] = {…}  -- AttachPanelToEntity (string) ✅
```

The update loop looks up `PANELS[key]`; with a number key the panel is not found and it
**deletes** the entry with `ATTACHMENTS[key] = nil`. Result: the panel is created and visible,
but never follows the bone. No error either.

**2. Bone attachment is not implemented anyway.** The helpers `getBoneWorldPos` / `getBoneWorldRot`
are defined but the update loop **never calls them**; the loop only uses
`GetOffsetFromEntityInWorldCoords(a.entity, …)`, so `a.boneIndex`
is ignored entirely. Even with item 1 fixed, the panel follows **the entity root**,
not the bone.

**3. The owner is written wrong.** Inside `AttachPanelToBone`,
`createPanelInternal(opts, GetCurrentResourceName())` is called — that is
**`cr-3dnui` itself**, not the calling resource. The other exports
use `GetInvokingResource()`. Result: when the consuming resource stops,
the `onResourceStop` cleanup **does not claim** that panel, and the panel stays hanging on screen.

> Conclusion: **do not rely on this export to attach a panel to a bone.** Either use
> `AttachPanelToEntity` + baking the pose into entity space (§4 — that is the path that
> does not jitter anyway), or fix these three lines and fork it.

## 10. WHEN AN IMAGE IS NEEDED — do not generate it; suggest it and give a prompt

When a DUI page, icon, screen background, logo, texture or any other
image is needed:

**Do not generate something random or invent a placeholder.** In order:

1. **Describe the idea**: what it will show, which object it will sit on, from what distance it will be
   read, which tone/colour (screens sit on an `emissive` shader —
   a dark background + bright text looks realistic).
2. **Give the user a ready prompt** and ask **the user** to
   produce the image. The prompt should contain: content, style, aspect ratio
   (the **same** as the panel's `resW:resH` ratio), resolution, background (for a screen
   texture usually full bleed, no margin).
3. Until the image arrives, **build the layout with CSS** and leave an empty box of the right size
   in place of the image. That way only one file changes when the image arrives.

Reason: the screen content is the visible face of the project; an invented image
does not fit the tone and gets replaced entirely later — the work is done twice.

---

## 11. QUICK RECIPE — a new interactive screen in a script

1. `screentex.ps1 -Model <model>` → **does** it have a screen texture?
   - If yes, and there is **one** instance of that model in the scene → path C (ReplaceTexture)
   - If no, or there are several instances → path A (world quad)
2. Position/normal: `assetdb.py show <model>` (bbox → where the face is) +
   `assetdb.py where <model>` (real positions in the world). **Do not invent**
   coordinates.
3. Build the panel: `faceCamera=false`, `frontOnly=true`, give `up` (made
   perpendicular), `resW:resH` matching the panel ratio.
4. Pick the interaction mode (§5). Terminal/laptop → `key2dui`; wall panel → `uv`.
5. Keep the state **on the server**, reflect it with `SendMessage` (§8).
6. `onResourceStop` → `DestroyPanel` / `DestroyReplaceTexture` / `EndFocus` /
   release the ped freeze.
