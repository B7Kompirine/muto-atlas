# Particle catalogue / family production — family from a donor, quality gate, reference loop

**When to read:** you will produce many effect families from one pipeline (56 families): donor choice, `C4`, KFP min/max, the quality gate, colour and envelope auditing, user image → code.
**Source:** the former ptfx flipbook reference (2.5.0) §9-12, §14-15 (2026-09) · **Measured:** 56 families; `PtFxAssetStore` pool of 400; donor field meanings read from vanilla
**Read first:** `branches/particle/_branch.md` · trunk › `trunk/tool-pitfalls.md` §3 CodeWalker (`FxcFileHash`, `VFT`, `ResourcePointerArray64`) · scripts `ptfx_build_catalog.py`, `ptfx_quality_gate.py`, `ptfx_find_donor.py`, `ptfx_merge.py`

---

## 9. The 15 families produced — ⛔ OPEN WORK, READ THIS FIRST

`smoke · fire · fireball · dust · steam · spark · splash · ember · fog ·
bubble · debris · ring · electric · blood · leaf`

Deployment: `resources/[script]/my_ptfx/stream/` (33 `.ypt`; 15 are families,
the rest are diagnostic traces). The test bench is in a separate resource: `my_ptfx_test`.

### ⛔ THE OLD VERSION OF THIS SECTION WAS WRONG

It used to say "all 49 frames (7×7) @ 1024, `C4 = 48`". That was the state
**BEFORE the 4×4 finding in §1e** and had not been updated. Measured by
reading back the deployed files (`res_to_xml.ps1` → `AnimateTexture/UnknownC4`):

| file | `C4` | texture | assessment |
|---|---:|---:|---|
| `my_n4` (control, 4×4) | **15** | 1024 | correct |
| `my_n7` (control, 7×7) | **48** | 1024 | correct (old state) |
| **ALL 15 families** | **0** | **512** | ⛔ |

### ⛔ OPEN DEFECT: the families' `C4` is 0

According to §1, `C4` **is the index of the last frame to play**. `C4 = 0` means
**only frame 0 plays** — so the flipbook never turns and the effect stays frozen.
For a 4×4 sheet it should be **15**.

Two independent sources say the same thing: the rule itself (§1e "`UnknownC4`
**15** is written") and the control asset `my_n4` (C4=15). When the families were
regenerated at 19:32, this step was not written.

The texture resolution is also 512 (§1e's 4×4 grid divides 512 exactly into
128 px cells, so the grid is consistent — the problem is only `C4`).

⚠ **THIS DEPENDS ON AN OPEN QUESTION — READ §1e-BIS FIRST.** Whether the families'
`C4=0` is a defect or the correct production path **depends on whether slicing
works**, and as of 2026-09-02 this was not resolved:
§1b (`t1`) says it works, §1e says it does not; neither was closed with a clean
measurement.

- if slicing WORKS → `C4 = frames − 1` (4×4 sheet → **15**) must be written,
  and `C4=0` is a real defect
- if it DOES NOT WORK → `C4=0` is already correct, do not touch it

⛔ **Do not regenerate the families without choosing one of these two.** First
run the discriminating test in §1e-BIS cleanly.


## 10. Catalogue production pipeline — producing a family from a donor and AUDITING it

A family in the catalogue is not written from scratch; it is transplanted from a
vanilla donor (§1b) and then audited **by measurement**. Two scripts:

```
python ptfx_build_catalog.py    --group <group>   # builds
python ptfx_quality_gate.py  --group <group>   # audits against vanilla
```

**Principle: the donor's own values are KEPT.** Vanilla has already balanced
that effect. Only the field where the family really has to differ is
overridden, and **the reason for every override is written in the spec**. An override
without a reason is the fastest way to produce "needlessly too much / needlessly too little effect".

### ⛔ Do NOT COLLAPSE a range into a single number — measured

`--rate` / `--lifetime` once wrote **the same number** into the R and G slots.
This removes the particles' randomness: they all live exactly as long and
**die at the same moment**, and the eye reads that as "mechanical". Measurement (n=1989 emitters):

| field | gives a range | median max/min |
|---|---|---|
| `m_particleLifeKFP` | **90.3%** | 1.45 |
| `m_spawnRateOverTimeKFP` | 56.7% | 1.40 |

So writing a flat number **deviates from vanilla in most cases.** The right way:
keep the donor's own spread ratio and move the range to the wanted **mean**
(`mn·d/mean`, `mx·d/mean`). If the donor has no range, it stays flat — that too is the donor's
own choice.

### The two things the gate measures

1. **Donor deviation (exact reference).** If a field with *no* override in the spec
   has changed, that is an accident → violation. If an override is written but the value
   did not change, that is also a violation (ineffective override).
2. **Vanilla band (population reference).** The concurrent load
   `mean(rate) × mean(lifetime)` is placed in the distribution of all vanilla emitters:
   **p05 = 1 · median = 18 · p95 = 225**. Below it is "needlessly too little", above it is
   "needlessly too much".

Also the silent breakers: `UnknownC4 ≠ 0`, `RGB_*` technique (ignores alpha),
wrong texture name.

### ⛔ The emitter name is NOT THE SAME as the effect name

That is why the emitter of the `fire_extinguish` effect was not found and the gate
said "no donor emitter". The link is in the **`<EmitterRule>name</EmitterRule>`**
field. Do not guess from the name, read the link.

### ⛔ KFP channel meaning: `Red` = MIN, `Green` = MAX

Reading a single number (the first channel) ignores the top end of the range; an emitter
that looks sparse may actually be several times denser.

### ⛔ Do not report the donor's own value as an "error"

The gate used to warn wherever it saw `sizeScalar ≤ 1.5`, and it counted the **0.4437**
of `ent_amb_fbi_cinder` as a violation. That value is the donor's own
vanilla value, and **2%** of vanilla `sizeScalar` is below 1.5
(n=1901; p05 = 5.22, median = 65.5). The rule must fire only when **we** write that
field — otherwise it produces false alarms. (The same lesson as a sibling
of §2: a tool flagging something does not show that the thing is broken.)

### ⛔ Leaf/litter effects are NOT SPRITES

`ent_amb_falling_leaves_*` are MESH particles (`ParticleBehaviourModel`),
they have no textures, and the transplant fails with *"no `<TextureName>` in the particle rule"*.
Scattering/fluttering needs a sprite-based donor —
`ent_amb_fbi_falling_debris` worked.


## 11. Animation envelope — a single-frame sprite's motion comes FROM HERE

Since sheet slicing does not work (§1e), the sprite is static. The only motion
source left is **the alpha/size/colour curves over the lifetime**. If the curve is flat,
the particle does not look alive, it looks pasted on.

The curve is inside `ptxu_Colour:m_rgbaMinKFP` / `m_rgbaMaxKFP`.
`InterpolationInterval` = normalised lifetime 0..1, `AlphaChannelColour` = the alpha
at that moment. ⛔ **`KeyFrameMultiplier` is not made up:** measured,
`1 / (t[i] − t[i−1])`, 0 on the first frame.

**Measurement (n = 1735 vanilla particle rules):**

| | share |
|---|---|
| alpha 0 at `t=1` (fade-out) | **88.2%** |
| alpha 0 at `t=0` (fade-in) | 44.7% |
| median keyframe count | 3 (9.3% single frame = constant) |
| peak alpha | p05 0.1 · median 0.7 · p95 1 |

So **fade-out is almost mandatory, fade-in is not** — a spark should appear instantly.
When repairing, keep the donor's instant-appear choice and only remove the pop at the end.

### ⛔ A DONOR THAT GETS ITS MOTION FROM THE TEXTURE DIES WITH A STATIC SPRITE

The most expensive item. The alpha envelope of `ent_amb_dry_ice_vent` is a **single keyframe**
(constant 0.5) — but its texture is `ptfx_smoke_wispy_anim`, i.e. an animated sheet.
The texture was providing the motion. When we replaced the texture with a single-frame sprite,
**nothing changing was left** in that effect: the particle appears at full
alpha and vanishes at full alpha. A value that is correct in vanilla is a defect
in our pipeline.

Of 231 suitable donors, **20** have constant alpha and **14** pop with
alpha > 0 at the end — **14.7%** in total. The builder (`ptfx_build_catalog.py`, its envelope repair step)
rewrites a broken envelope in vanilla shape and reports what it did.

### ⛔ Check BOTH the MIN and the MAX envelope

For one round only `min` was audited; `paper_scatter` and
`rubble_rain` got a "pass" from the gate **even though their `max` envelope ended at 0.8 and
popped**. The two envelopes can break separately.

### ⛔ `<ParticleRule>` is in the EFFECT block, not in the EMITTER

The emitter block has no `*Rule` tag at all (measured: empty set). Searching in the wrong
place reported **every donor** as *"MESH particle, no texture"* — although a textured
effect had been produced from the same donor. (Same as §2.)

### ⛔ The catalogue's name references are NOT donors

**None** of the 18 references written for destruction (`bang_concrete`, `bul_glass`,
`scrape_metal` …) could be used: all of them are multi-emitter. The reason is
structural — an impact effect is by nature dust + splinters + puff, i.e. 3-6
emitters. Transplantable effects: **231 / 964**. Choose by **behaviour**,
not by name similarity: `ptfx_find_donor.py --search <term>`
and grouping by texture.

### ⛔ Exempt the band against the donor

By definition 5% of vanilla's own effects are above p95.
Keeping the donor's value and breaking the band is exactly what being "like vanilla"
means (`collapse_dust` load 244). The band must only measure whether **we** moved
the load away from the donor.

### ⛔ Do not read build output through GREP

A `for n in zn:` loop overwrote the outer counter `n`, the build crashed with
`TypeError` after the first repair, and **the remaining 8 files were never regenerated**. Because the output
was read through a `grep -E` filter (envelope and build-count lines only), the traceback was not visible; the gate
measured the stale files and said *"11/11 passed"*. Two rounds went by under this illusion.
Read the build script's output **unfiltered**, or use `set -o pipefail`
and check the exit code. ("The command gave no error" is not proof of
deployment — a sibling of §7.)


## 12. ⛔ `PtFxAssetStore Pool Full, Size == 400` — the pool counts FILES

Symptom: the game crashes at startup during `INIT_SESSION`
(`CExtraContentWrapper`, `c0000005`). There is no trace on the server side;
the error is in the client's own dialog box and states its reason plainly.

**The pool counts FILES, not effect rules.** The proof is conclusive: `core.ypt` carries
**964 effect rules** in a single file, while the pool is 400 — if rules were counted,
vanilla would overflow the pool on its own. `RequestNamedPtfxAsset` also takes a file
name.

Result: **"one file per effect" is wasteful.** 35 families can use **1** slot
instead of 35 slots. Measured: 35 files → a single `my_effects.ypt`
(1.49 MB), verification 35/35 chains and envelopes intact.

Tool: `ptfx_merge.py --name my_effects --folder <dir>`

### The four constraints of merging

- **`TextureDictionary` MUST BE SORTED BY HASH** (RAGE does a binary
  search). Measured: the 107 textures of vanilla `core.ypt` are sorted by Jenkins hash;
  on the other hand **the three rule dictionaries are NOT sorted** (neither alphabetically nor by
  hash). Sort only the textures, do not touch the others. The way to verify the hash function:
  vanilla's texture order comes out sorted by your hash.
- **Textures are NOT EMBEDDED in the XML** — they are read from outside via
  `<FileName>x.dds</FileName>`. All `.dds` files must sit next to the merged XML,
  otherwise the build silently comes out without textures.
- **After merging, ASSET name ≠ EFFECT name.** Now
  `RequestNamedPtfxAsset('my_effects')` +
  `UseParticleFxAssetNextCall('my_effects')` +
  `StartParticleFx*('my_smoke', …)`.
- ⛔ **Every record keyed by asset name BREAKS SILENTLY.** The harness
  stored handles in `acik[varlik]` (open handles by asset); after the merge all
  effects share the same asset, so every new effect overwrote the previous one's handle
  — `/ptfxdur` would have left 19 effects running. The key must be **the effect name**.
  Scan for such records before merging.

### Catch it in the first pass

Count the custom `.ypt` files on the server **per resource**
(`find resources -name '*.ypt'`). Folders outside `stream/` such as `_source/`
are not loaded, do not count them. Disable retired test resources with
`fxmanifest.lua.KAPALI` (KAPALI = off) — the server's own convention, it comes back
with a single rename.

### ⛔ `res_to_xml.ps1` does not take a folder with `-Path`

`-Path <folder>` says *"Access to the path is denied"* and reports **0 successful**;
the right form is `-Dir <folder> -Filter "*.ypt"`. The error message looks like a
permission problem, but the parameter is wrong.


## 14. Catalogue complete — 56 families, four new measured pitfalls

Eight groups, **56 / 56** passed the gate; together with the 15 production sprites
**71 effects in a single `.ypt`** (`my_effects.ypt`, 2.94 MB, 1 pool slot).
Read back from the binary: 71/71 chains, textures and envelopes intact.

**Two** of the catalogue's 58 families are **deliberately left out**, both of them, in the catalogue's
own words, not particle work:
`shield_dome` (mesh + shader) and `heat_haze` (refraction shader,
`ptfx_heathaze_n` is a normal-map texture). Imitating them with particles gives a bad
result; the reason is written in the spec.

### ⛔ Do not use a MULTI-TEXTURE donor

`liquid_splash_petrol` needs **two** textures: `ptfx_gloop_n` (NORMAL MAP) +
`ptfx_gloop` (colour). The transplant writes the single sprite into **both** and the
shader is lit wrongly. The gate caught it as *"texture name ['my_rocket','my_rocket']"*.
Measured: **6** of 231 suitable donors are multi-texture; most have a single-texture
twin (`petrol → liquid_splash_water`, same lifetime band).
`ptfx_find_donor.py` now filters them out.

### ⛔ `ptxu_Acceleration` has TWO variants

`m_xyzMinKFP`/`m_xyzMaxKFP` (1392 rules) **and** `m_strengthKFP` (24 rules,
scalar). `ent_amb_fly_swarm` uses the second; trying to write xyz
fails silently. Do not assume a field name has only one variant.

### ⛔ The MAX alpha envelope can be ENTIRELY ZERO — this is valid

Measured: **87 of 1733 rules (5.0%)** are like this, including effects that work in game
such as `ent_amb_tnl_bubbles_lge`. If max is zero there is no range, and min
applies. The gate reported this as *"INVISIBLE / NO ANIMATION"* — a false
alarm; now exempt. (There is **no** such exemption for the min envelope.)

### The donor is now a SKELETON

Since we write the motion, the donor's own motion is not a criterion. The selection
criteria are three: single emitter · **single texture** · carries the needed behaviour units.
Donors carrying all three units (Acceleration + Dampening + Rotation):
**115 / 231**. The one whose lifetime band is close to what the family wants is chosen; the rest
is written.

If a unit really is missing and the wanted value is a **no-op** (accel = 0),
**remove** the key — instead of asking for something it does not carry. `elec_crackle` and
`fbi_live_wires` have no motion unit at all, and that is right: an electric arc does not fly,
it flashes in place.

### ⛔ Do not feed the old merged output into a merge

`my_catalog.ypt.xml` (the previous round's merge of 20) had stayed in the input folder
and got mixed into the re-merge; the versions inside it from **before the motion was
written** were dropped in dedup only thanks to alphabetical order. That is not something
to leave to luck — clean the folder before merging and verify that the
`source files` count matches the expected families **exactly**.

### Test layout

If `/ptfxkat` lays out 56 effects 4 m apart, that makes 224 m and fits in no camera.
Grid: 8 columns × 7 rows (28 × 30 m). `/ptfxkat <n>` shows pages of 16,
for a close look.


## 15. Reference loop — the user generates the image, we carry the character into code

User decision (this pipeline's rule): **ChatGPT images are NOT USED directly as
sprites** — they are references. The only exception is the piece the user explicitly
liked (the purple rune circle). The images are
in a local folder (not in the repository).

Loop: have ChatGPT generate a 2×2 atlas (pure black background, no text) → compare side by side
(`ref_vs_ours`, reference vs ours) → reduce the difference to three or four concrete characteristics → rewrite the generator
for those characteristics → compare again.

Measured/experienced pitfalls:

- ⛔ **A multi-line message cannot be sent to ChatGPT with `type`** — the message is sent at the end
  of the first line, the rest of the description never arrives and the model makes up the subjects
  (the first atlas came out as four generic explosions). The prompt must be ONE line.
- ⛔ **If `type` starts before the page has loaded, most of the text is lost** — a leftover
  `--` was seen in the box. First verify with a screenshot that the box is there.
- Image URLs are hidden (auth token) — the download button is used,
  `Downloads/ChatGPT Image *.png`.
- Alpha from a black background: `a = max(R,G,B)`, then **unpremultiply**
  (`rgb/max(a,eps)`); otherwise the edges darken. Slicing: `atlas_slice.py`.
- ⛔ **A wavy radius does not produce glass, it produces a FLOWER** (happened). An angular shard
  = the **intersection of 5-6 half-planes** in random directions; edge = distance to the boundary.
- ⛔ Thin lines vanish under blur: a 0.01 radian spike ≈ 1 pixel
  (happened in the EMP ring). Think of line thickness in pixels.
- Fire character: white hot core + angle-dependent FILAMENT modulation
  + colour ramp from energy (`R=0.55+0.9e · G=1.55e−0.08 · B=2.6e−1.55`).
  A flat radial falloff gives an "orange disk".
- Electric character: not a cos^n spike but **real zigzag line geometry**
  (segmented polyline + side branches).
- Blood character: not a round dot — a **drop elongated in the direction of motion** +
  a viscous thread from the centre to the drop (short-lived).
- Spark shower: not a dot but a **thin bright line** (motion blur feel),
  branching at the tips.

When the sprite of the base 15 changes, `ptfx_all/my_<name>.dds` must be refreshed too —
the catalogue builder does not produce them, the merger takes ready-made DDS files.
