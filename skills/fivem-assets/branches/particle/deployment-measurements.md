# Deployment and in-game measurement — test bench, rcon, `PtFxAssetStore`, "it looks broken"

**When to read:** you will put a `.ypt` on the server and test it in game, you say "the effect is broken / not showing", or the game freezes — test bench, rcon, `PtFxAssetStore` pool; "it looks wrong" is not a measurement.
**Source:** the former ptfx flipbook reference (2.5.0) §1c, §7, §16-18 (2026-09) · **Measured:** test bench pixel measurement; `PtFxAssetStore` 400; freeze threshold of a single large `.ypt`
**Read first:** `branches/particle/_branch.md` · trunk › `trunk/tool-pitfalls.md` §3 CodeWalker (`FxcFileHash`, `VFT`, `ResourcePointerArray64`) · tools `ptfx_bench.py`, `ptfx_sim.py` (a model, not the engine)

---

## 1c. Diagnosis method — lessons learned the expensive way in this round

### ⛔ NO DIAGNOSIS FROM AN IMAGE WITHOUT A REFERENCE

For five rounds things were called "broken" without knowing what is **normal** on screen.
Without a comparison point you cannot tell by eye whether a particle is drawn
right or wrong — especially at night, translucent and at large scale. Put
**the game's own effect** in the same frame as a reference:

```lua
UseParticleFxAssetNextCall('core')
StartParticleFxLoopedAtCoord('exp_grd_grenade_smoke', ...)
```

Side by side: reference · our file + vanilla texture · our file + our texture.
The texture source becomes the only variable.

Extra readability conditions (all of them were violated): daytime (`NetworkOverrideClockTime`),
small scale (`--size-mult 0.30`), ≥4 m between them, label by **colour**,
not by position.

### ✅ TEST BENCH — take the test away from the user, tie it to measurement

Five rounds were lost in the loop "put the user in the game → ask for a screenshot → interpret the screenshot",
and the interpretation layer produced a wrong diagnosis three times. The permanent
solution is to remove that layer.

`screenshot-basic` is already installed on most servers and can be driven
**from the server**:

```lua
exports['screenshot-basic']:requestClientScreenshot(src,
    { fileName = 'cache/my_ptfx/x.jpg', encoding = 'jpg', quality = 0.85 },
    function(err, file) ... end)
```

Setup: the resource polls the `is/istek.json` file once every 1 s (`istek` = request,
`sonuc` = result; the names stay because the resource reads them); for a job written
from outside it sets up the client (effect + **fixed camera**), waits, takes a
screenshot, writes `is/sonuc.json`. Driver and measurement:
`scripts/ptfx_bench.py`.

- **The camera is placed at the same point with the same direction at every step.** In frames
  taken by hand the distance/angle changed, so two effects could not be compared.
- Scene conditions are fixed: `NetworkOverrideClockTime(12,0,0)`,
  `SetWeatherTypeNowPersist('EXTRASUNNY')`, the ped is frozen.

**The criterion is a numbered diagnostic sheet**: each cell has its big number written on it.
The count of connected components separates the two cases exactly (measured):
the whole sheet → **89 components**, a single cell → **1 component**.

⛔ **Do NOT give `fileName` to `screenshot-basic`.** If it tries to write to a file,
it hits FiveM's file gate: *"Access to this API has been restricted.
Use --allow-fs-write"*. A call without `fileName` returns a base64 data URI;
we write that into our own resource with `SaveResourceFile` — that is a native,
not subject to node's fs gate.

⛔ **`StopParticleFxLooped(h, false)` DOES NOT REMOVE THE EFFECT IMMEDIATELY.** It stops
emission, but living particles stay on screen until their lifetime ends and
**leak into the next measurement** (measured: the numbers of a step with 4 s lifetime
were read in the next frame, a wrong diagnosis was made). Pass `true`, call
`RemoveParticleFx(h, true)` on top, and wait between steps.

⛔ **Do not place the camera along a fixed world direction.** If the effect sits along the player's forward
vector, putting the camera on a fixed axis such as `target.y - 3.2`
leaves it **inside the ped**; only the backpack is visible in the frame.
The camera must look at the target from the player's eye level.

⛔ **Framing is done by pulling the CAMERA BACK, not by SHRINKING the effect.**
When the effect was shrunk it became completely invisible (changed pixels 0.6%).

⛔ **Limit:** the screenshot is the client's render; the player must be
connected. And if a stream file changed, **reconnecting** is
required — `restart` is not enough. The test bench only measures an asset that is already deployed.

### ⛔ WRITE THE LABEL ON SCREEN — neither position nor colour can be trusted

The boxes were first matched **by position**, then **by colour**; both
led to misreadings. In the colour round it was verified by measurement that the right RGB
was written into the files (all four exactly at the requested value), but the "blue box"
was never found in the screenshot — so matching failed
even with correct data.

Solution: **write its name** above each effect with `DrawText3D`. The screenshot
itself must say which box is which; leave no room for
interpretation. `SetDrawOrigin(x,y,z,0)` + `DrawText(0,0)` + `ClearDrawOrigin()`.

### ⛔ CALLING A VANILLA EFFECT AS REFERENCE IS FREE

`UseParticleFxAssetNextCall('core')` + the game's own effect name — without shipping
a file, a guaranteed-correct comparison point. Put it in every visual
test.

### ⛔ AUDIT THE TEST ITSELF TOO — scale was applied twice

Even after the referenced test was set up, the result was misleading: the subjects
looked much smaller than the reference and read as "a cluster of dots".
The cause was not in the finding but **in the test's design** — the shrink had been
applied twice: `--size-mult 0.30` was baked into the file, and on top of that
`StartParticleFxLoopedAtCoord(..., 0.35)` was given in Lua. The reference got only
0.35, the subjects 0.30 × 0.35. So the subjects were **0.3 times** the reference,
and a smoke cloud reduced to 0.3 times naturally looks like small dots.

**Rule: in a comparative test every path must go through the same transforms.**
Every scale/colour change applied while preparing the subject must also be applied
to the reference, or to none of them. Verify this **by measuring** before the test:
compare the rule block with vanilla at text level —
the `Size`/`Colour`/`AnimateTexture`/`Velocity` blocks must be byte-for-byte equal,
and the only difference in the whole file must be the names (27 bytes in this case).

### ⛔ "It looks broken" is not a measurement — COUNT the lattice

A pattern suspected in a screenshot is measured with FFT / autocorrelation.
Measured: ~7 repeats inside the block (our grid is 7×7), period 20 px.
But the cells came out **uncorrelated with each other** (+0.002); the cells
of our sheet, on the other hand, resemble each other (+0.791). So what we saw was neither
"the whole sheet" nor "a repeat of a single cell" — both diagnoses made by eye
were wrong.

### Fields ruled out — at raw byte level

The `AnimateTexture` block (208 bytes) is **identical** to vanilla: only 7 of the 208
bytes differ, and both are pointers (0x10 and 0xA0, keyframe
addresses). CodeWalker hides no byte — the XML round trip only changes the VFT
pointers, not a single field of the behaviours shifts.
The texture metadata is the same too (`UsageFlags`, `UsageData`, `Unknown_32h`).

**Result: there is no place left to search inside the file.**

### ✅ CLOSED — a custom `.ypt` IS PROCESSED BY THE ENGINE LIKE VANILLA

In the referenced, equal-scale, daytime test, the game's own effect,
our `.ypt` (same rule, vanilla texture) and our `.ypt` + our sheet
**could not be told apart**. So the stream path, rule copying, texture embedding and sheet
animation are sound.

⚠ This **invalidates** the "file is broken / engine does not apply the grid"
diagnoses made in earlier rounds; all those tests were confounded
(double scale, reading without a reference, night, unlabelled boxes).

### ⛔ `rm my_t*` DELETES PRODUCTION WHILE DELETING SUBJECTS

The glob that cleaned up the `my_t1..t5` subjects also caught the dust family's file (`my_dust.ypt`
today; at the time its Turkish name began with `my_t`) and the file silently disappeared. After deployment
**compare every asset name Lua mentions with the stream contents** — without this gate
a round would have been lost to "one effect is missing" in game.

---

## 7. Deployment — stream and commands in SEPARATE resources

⛔ **A broken stream asset silently drops the WHOLE resource**:
the server writes `Started resource X`, no command registers on the client,
no print appears, there is no error in F8.

That is why the `.ypt` files are in `my_ptfx/stream/` (no Lua) and the test
commands in `my_ptfx_test/` (no stream). If the command runs but the effect does not
appear, the defect is in the stream; if the command does not exist at all, the defect is in Lua.

`ensure [script]` starts the whole folder — no need to add a line to the
cfg.

After copying, **compare hashes**; "the command gave no error" is not proof of
deployment.

### Lua side
- Wait for `RequestNamedPtfxAsset(name)` + `HasNamedPtfxAssetLoaded(name)`
  (set a timeout).
- `UseParticleFxAssetNextCall(name)` is renewed before **every** `StartParticleFx...` call.
- If the handle returns 0, it means **the asset loaded but the effect rule name was not found**
  — report the two separately.
- ⛔ `GetEntityRightVector` **is not a standard native**;
  in the `GetEntityMatrix` wrapper the return order is unclear. Derive the right vector
  from forward: `right = (forward.y, -forward.x)`.

### ⛔ AN ASSET NAME HAS NO CAPITAL LETTERS

An asset produced under the name `my_gA` **loads**, but
`StartParticleFxLoopedAtCoord` returns **handle 0**: "effect rule
not found". GTA computes name hashes after lowercasing;
`RequestNamedPtfxAsset` passes, the hash of the effect rule inside does not match.
The symptom is misleading — the asset looks loaded, the effect is not there.
**All asset/effect/texture names are lowercase.**

### ⛔ ADDING A NEW FILE TO STREAM TAKES THREE STEPS

1. copy the file into `stream/`
2. **`restart <resource>`** — the server rebuilds the stream list
3. **connect** the client again

If step 2 is skipped, the client never finds the asset (`asset NOT LOADED`) and
nothing appears on screen. The error shows only in the **client** log;
there is no trace in the server console. *Changing* an existing file does not change the manifest,
but *adding* a file does.

### ⛔ KILLING THE CLIENT LEAVES A GHOST SESSION

When the process is force-closed, the server still counts the player as connected, and
reconnecting is refused with **"Duplicate Rockstar License Found"**.
RCON has **neither** `clientkick` nor `drop` ("No such command"); the session
drops by its own timeout. Solution: wait ~25 s after killing.

### ⛔ IN A `while read` LOOP, powershell SWALLOWS STDIN

Calling `powershell`/`python` in the loop body consumes the remaining lines and
the loop skips lines. Measured: 5 of 15 families were built with wrong values, and
the cause was only seen through read back. Use a separate file descriptor:
`while read ... <&3; do ... </dev/null; done 3< file.txt`

### ⛔ THE FiveM PROTOCOL IS CALLED FROM THE SHELL

If `FiveM.exe fivem://connect/...` is started directly, it crashes with
*"This application should be launched directly from the shell or a web
browser"*. The call must come from the shell:
`Start-Process 'explorer.exe' -ArgumentList 'fivem://connect/<ip>'`

### ⛔ When an asset changes, LEAVE THE SERVER AND RECONNECT
FiveM caches stream files; `restart` is not enough.

---

## 16. ⛔ A TURKISH APOSTROPHE CLOSES A LUA STRING — `lua_check` MISSES IT

The line written:

```lua
print('^2[x]^7 ready - /ptfxkat <n> (8'er)  /ptfxall')
```

The apostrophe in `8'er` (a Turkish suffix) closes the string. The error FiveM gives is
`')' expected near 'er'` and the result is: **the WHOLE resource does not load.**
No command registers. In game the symptom does not look like a "Lua error" but like
*"no command"* — when the user typed `/ptfx`, only
another resource's command appeared.

⛔ **`lua_check` (lua-language-server) said "No diagnostics" for it.**
   Do not trust it as the only check. Verified second gate:
   `python lua_syntax.py <file.lua>` — it really follows Lua's string/comment
   rules (`'`/`"`, `\` escape, `--` line comment,
   `[[ ]]` and `[==[ ]==]` long block). Verified by measurement that it catches the broken line and
   passes the correct one.

**Rule:** if Turkish text contains an apostrophe, use **double quotes**
(`"8'er"`), or do not write the apostrophe at all.

Scope note: this script checks string/comment balance. It does not catch STRUCTURAL errors
such as `<eof> expected
near 'end'` (extra/missing `end`) — `lua_check` is still needed
for that. The two complement each other; neither replaces
the other.

## 17. `/ptfxkat` freeze — OVERDRAW, not data

Symptom: `Window Watchdog: FiveM has stopped responding`, in the crash dump
`Is Out of memory : No`. There is **not a single ptfx error** in the log, the asset
loads cleanly with `Mounted my_ptfx`.

Measured: opening 56 effects at once means **1784 concurrent particles**.
On top of that, the alpha coverage of the Kenney textures is **40-70%** (the old procedural
textures were 2-30%) — so even with the same particle count the fill
cost rose several times. VFXDoc's warning *"alpha coverage is one of the most
underestimated sources of performance"* is exactly this.

The five heaviest families: `collapse_dust` 244 · `wall_collapse` 215 ·
`water_explosion` 100 · `radioactive_fog` 88 · `fuel_barrel` 72.

**Lesson:** a bulk display command should open a PAGE by default.
`/ptfxkat` pages of 8, `/ptfxsira` one-by-one browsing; the path that opens
everything at once (`/ptfxkat hep`) prints a warning.


## 18. ⛔ A SINGLE LARGE `.ypt` FREEZES THE GAME — measured threshold

§12 said "the pool counts files, merge everything into one file". **On its own
this misleads:** merging has an UPPER limit.

Measured (by halving, in game):

| file | effects | size | result |
|---|---|---|---|
| `my_mini2` | 2 | 0.06 MB | **loaded** |
| `my_mini16` | 16 | 0.39 MB | **loaded** |
| `my_effects` | 71 | 1.88 MB | **FROZE** |

The threshold is between 16 and 71. Production was split into four parts of 18.

### How the diagnosis was made — three guesses, each proved wrong

1. **"Size"** → I reduced 6.56 MB to 1.88 MB with 256×256 textures, **it froze
   the same way**. Not size, ITEM COUNT.
2. **"`Wait` in the command callback"** → a real defect (below), but
   it still froze after the fix. It was not the only cause.
3. **"3D label drawing"** → turned off, still froze.

I got the definitive answer only **after making the harness produce evidence**:
non-blocking load + a log at every step. The log showed this —

```
[t1] start ✓  loaded right now: false ✓  requesting asset ✓
[t1] command finished (did not wait) ✓     <- Lua ran to the end
                                    <- 46 s later
Window Watchdog: FiveM has stopped responding
```

`asset READY` was never printed → the freeze is **after** `RequestNamedPtfxAsset`,
while GTA streams the asset. Lua was fully cleared.

⛔ **Lesson: the code must produce the difference between "it freezes" and "where it
freezes".** I spent three rounds guessing without a step log.

### ⛔ `Wait()` CANNOT BE CALLED IN A COMMAND CALLBACK

The `RegisterCommand` callback does not run inside a coroutine; calling
`Wait(0)` from it locks the main thread. The symptom is very misleading:
**not even a single print line appears**, the command looks as if it never ran.

This defect was in the code from the start but had never triggered: while the asset
was already loaded, `HasNamedPtfxAssetLoaded` returned early, the loop was not entered,
`Wait` was never called. It triggered for the first time after switching to a single large asset.

Solution: a registrar that wraps the body in `CreateThread`
(`komut(ad, fn)`, i.e. command(name, fn)), and better — **remove blocking waits
entirely**: the request is sent once, a persistent watcher thread tracks the state,
and the pending job runs when it is ready.

### A name map is REQUIRED for a split asset

`UseParticleFxAssetNextCall` wants the asset **that contains** the effect; if the wrong
asset is given it returns `handle 0` and no error appears. An effect name →
asset name map is generated and embedded in Lua.

### Texture resolution (still a win in this round)

The most common texture size in vanilla `core.ypt` is **256×256** (33 of 107 textures).
Where it uses 512 are **16-49 frame sheets** — ~73 pixels per frame.
For a single-frame sprite 512 is too much: 71 textures went from 23.7 MB down to **5.9 MB**.
