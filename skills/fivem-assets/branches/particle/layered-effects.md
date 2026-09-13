# Layered (multi-emitter) effect — explosion, fire + smoke + debris stacked

**When to read:** the effect looks "flat / single layer"; you want vanilla-style core + fireball + smoke + debris + shock ring stacked with delays; splitting sheet cells across emitter delays.
**Source:** the former ptfx flipbook reference (2.5.0) §1e-BIS 'N emitters + Unknown10' · `scripts/ptfx_compose.py` docstring (2026-09) · **Measured:** 713 of 964 vanilla effects (74%) are multi-emitter; `exp_grd_grenade` 6, `exp_grd_molotov` 7 layers
**Read first:** `branches/particle/_branch.md` · trunk › `trunk/tool-pitfalls.md` §3 CodeWalker (`FxcFileHash`, `VFT`, `ResourcePointerArray64`)

---

## Why layers

Measured: **74% of vanilla effects are multi-emitter** (713/964); our catalogue was entirely single-emitter — that is why everything "looked like a variant of everything else". Professional VFX gets its depth from layers (white core + orange fireball + rising smoke + debris + shock ring **stacked**). Layer fields read from vanilla: `<EmitterRule>`/`<ParticleRule>` are the layer's source, `Unknown10` is the layer's **delay** (seconds). Tool: `scripts/ptfx_compose.py`.

## Playing sheet cells as layers

### N emitters + `Unknown10` DELAY (works, measured)

Since the engine does not advance frames, the sequence is built **inside the effect**: N separate
emitters, each with its own **single-frame** texture (`C4=0`) and its own
**start delay**. The engine runs the sequence; zero load in Lua, sync
guaranteed.

**`Unknown10` = emitter start delay (seconds).** It is in the EffectRule's
`<EventEmitters>` entry. Vanilla measurement: **91.1%** of 2543 entries are **0**;
the 226 non-zero ones are in the **0.0010-0.7500** range (median 0.042).
`exp_grd_grenade` emitters are staggered 0 / 0.034 / 0.068 / 0.
⛔ **Ceiling 0.75 s** — do not exceed it.

**The emitter MUST STOP, otherwise the stages PILE UP.** In the first attempt
the delays worked but the emitters kept spawning, so four shapes
stacked on top of each other. The vanilla solution is to write a **burst
curve** into `m_spawnRateOverTimeKFP` (example: `bang_metal_dust`):

| keyframe | `InterpolationInterval` (normalised time 0-1) | rate |
|---|---|---|
| 1 | 0 | rate |
| 2 | w | rate |
| 3 | w + 0.02 | **0** ← the emitter stops |

So `InterpolationInterval` is the **time axis**, `Red/Green` are the
min/max spawn rate at that moment.

**Measured working configuration** (`my_e2`): 4 emitters, delays
**0 / 0.2 / 0.4 / 0.6 s**, each emitter spawns at `w=0.08` and stops at `0.10`,
particle lifetime **0.30 s**, each stage has its own single-frame texture, `C4=0`.

Measured in game (single run, film strip):

| t (ms) | 80 | 200 | 320 | 440 | 560 | 680 | 800 | 950 |
|---|---|---|---|---|---|---|---|---|
| red coverage % | 0.04 | **34.5** | 17.0 | 6.9 | 5.4 | 3.4 | **0.04** | 12.6 |
| seen | — | disk | ring | plus | — | triangle | — | from start |

Coverage drops to zero and rises again → the sequence completes and the loop wraps
to the start. Image: `flipbook_experiment/strip_e2.png`.

**Generator:** `flipbook_experiment/strip_ypt.py` — builds an N-stage effect from a single-emitter
transplant output (multiplies EventEmitters/EmitterRule/
ParticleRule/TextureDictionary N times, writes the delays,
sets `C4` to 0, binds each stage to its own texture).

⚠ When the effect is called **looped**, the sequence wraps to the start (t=950 above).
For a one-shot explosion `StartParticleFxNonLooped*` should be used;
not tried.
