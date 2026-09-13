# Particle texture sheet — frames, `C4`, grid, density, donor transplant

**When to read:** you will produce the effect's **texture**: how many frames, which resolution, what `C4` does, whether the sheet is sliced, how to measure density/silhouette, which donor to transplant the sheet from.
**Source:** the former ptfx flipbook reference (2.5.0) §1-§5 (2026-08/09) · **Measured:** 15 families in game; sheet slicing with visual proof; 107/107 vanilla particle textures DXT
**Read first:** `branches/particle/_branch.md` · `ypt-from-scratch.md` (the file itself) · trunk › `trunk/gta-fundamentals.md` §5 texture

---

## 1. Frame count and resolution — ⛔ BOTH RULES WERE WRITTEN WRONG

In the first version I wrote two rules here; both were wrong and broke the
whole chain. The in-game symptom was: **every sprite drew the whole 8×8 sheet in a single
frame** — on screen "a grid made of small images". So the engine was
not applying the grid at all.

### ⛔ Wrong 1: "the grid must divide the texture exactly"

It does **not** have to. Vanilla `ptfx_smoke_wispy_anim` is **7×7** on 1024×1024:
1024/7 = **146.29**. The engine samples in UV space in `1/k` steps,
it does not look for pixel alignment. Because of this made-up condition 36 frames were rejected and
**the switch to 64 frames (8×8) was made** — that is where the real error came from.

### ⛔ Wrong 2: "above the 63 band, but the engine accepts it"

It does not. "Read back verified it" only verifies **that the file was written
that way**; not that the engine uses it. **781 `AnimateTexture` behaviours** in `core.ypt`
were measured:

| measurement | value |
|---|---|
| `Unknown_C4h` largest | **49** (i.e. at most 50 frames) |
| rules with `C4 > 48` | **1** |
| rules with `C4 > 63` | **0** |

64 frames are completely outside the vanilla band, and the engine does **not** apply the grid
at all. Safe ceiling **49 (7×7)** — both `ptfx_sheet.py` and
`build_custom_ptfx.py` now reject anything above 49.

### ⛔ `C4` is NOT the grid, it is the INDEX OF THE LAST FRAME to play

Trying to derive the grid from `C4` without making this distinction leads you the wrong way.
The same `ptfx_smoke_wispy_anim` texture (counted visually: **7×7 = 49
frames**) is used in vanilla with these `C4` values:
**21, 35, 37, 38, 40, 42, 43, 44, 47, 48**. So rules can play a
**sub-range** of the sheet.

The grid is read from the **dominant** `C4` value per texture (`grid = √(C4+1)`) and
verified by counting by eye:

| texture | grid (counted) | dominant `C4` |
|---|---|---|
| `ptfx_water_splashes_sheet_b` | 2×2 = 4 | 3 |
| `ptfx_bubbles_trail_anim` | **5×5 = 25** | 24 (11/11 rules) |
| `ptfx_flipbook_fire_rgb` | 5×5 = 25 | 24 (25/25) |
| `ptfx_smoke_billow_anim_rgba` | 6×6 = 36 | 35 (13/13) |
| `ptfx_smoke_wispy_anim` | **7×7 = 49** | 48 (342/405) |

**Do not use a sub-range when producing** — write `C4 = frames − 1` so the whole sheet
plays.

### Fields that do not carry the grid (ruled out, do not search again)

None of the following encodes the grid — **they vary freely for the same texture**,
measured:

- `Unknown_C0h` — 0 in 776/781
- `Unknown_C8h` — {0,1,2,4}; the same texture has both 0 and 1
- `Unknown_CCh` — {0x01010100, 0x01000000, 0x01000100, 0x01010000};
  the wispy texture alone has all four
- `Unknown_11Ch` — 12/14/16/18/20/22/23/33 for the same wispy texture
- `ShaderVars` — none of the 21 variables contains 7 or 1/7
  (`Unknown_18h` is a shader **register** index; `diffusetex2` register 4)

**Structurally our rule matched vanilla**: behaviour lists
(L1 `... AnimateTexture Colour Sprite`, L2/L3 the same without Sprite, L5 only
`Sprite`), technique (`RGBA_lit_soft`, in 567 rules in vanilla), `Sprite` block
(only difference `Unknown_44h` 0.5/0). The only real difference was the frame count.

Vanilla `core.ypt` measurement (1736 particle rules):
**781 (45%)** carry `ParticleBehaviourAnimateTexture`.
`Unknown_C4h` distribution: 48 ×401 · 35 ×70 · 24 ×49 · 3 ×128 · 15 ×8.
`Unknown_CCh` 0x1010100 ×367 · `C0`=0 ×776 · `C8`=1 ×476.

---

## 1b. ⛔ A RULE WRITTEN FROM SCRATCH DOES NOT MAKE THE ENGINE APPLY THE GRID — production path TRANSPLANT

The sheet is right, `C4` is right, the behaviour lists are the same as vanilla, the technique is the same,
`FxcFileHash` is filled — and in game every sprite draws **the whole sheet in a single frame**.
Measured with five colour-coded subjects (`t1..t5`, each a different colour;
reading by position led to a wrong diagnosis twice, **label by colour**):

| subject | rule | texture | result |
|---|---|---|---|
| t1 | **vanilla** (2×2 donor) | our 2×2 | ✅ **correct** |
| t2 | ours | vanilla wispy 7×7 | ❌ grid |
| t3 | ours | our 7×7 | ❌ grid |
| t4 | ours + vanilla's 21 shader variables | our 7×7 | ❌ grid |
| t5 | ours | our 2×2 | ❌ grid |

The reading is conclusive: **the texture pipeline is sound** (t1 slices the sheet we
produced), **the frame count is irrelevant** (t5 is 2×2 too), **the shader variables are
irrelevant** (t4). The whole variable is **in our rule block**.

Ruled-out fields (they vary freely for the same texture, they do not encode the
grid): `C0` (0 in 773/778), `C8`, `CC`, `Unknown_11Ch`,
`ShaderVars`, `Sprite.Unknown5C` (`0x100` in vanilla too).
Which field it is has **not been found yet**.

### Production path: `ypt_transplant.py`

A working vanilla rule is copied; only texture/colour/size change.
The donor must be **single-emitter** and its `C4` must match our sheet.

```bash
python ypt_transplant.py core.ypt.xml --effect veh_respray_smoke     --new-name my_smoke --texture my_smoke --folder .     --color 0.62 0.60 0.58 --size-mult 1.0
```

`core.ypt` has **120 single-emitter animated donors**; most are `C4=48`
(7×7). Measured choices: smoke/dust `veh_respray_smoke` ·
`weap_veh_turbulance_sand` · fire `fire_map` · ember `fire_ped_smoulder` ·
fog `veh_vent_rc` · steam `ent_amb_steam_prison` · splash/blood
`blood_mouth` · ring `fire_extinguish`.

⛔ **Do not split the donor search on the `<Name>` tag.** `<Name>` also appears in keyframe
properties; the rule boundary is the sequence `
  <Item>
   <Name>`.
Splitting wrongly made it say "there are **no** single-emitter animated donors" — in fact
there were 120, and it cost a round.

### ⛔ THE DONOR'S TECHNIQUE WAS CHOSEN FOR ITS OWN TEXTURE

The transplant also carries the donor's `FxcTechnique` field unchanged — and that technique
was chosen **for the donor's own texture**. The texture of the `fire_map` donor,
`ptfx_fire_v2`, has no alpha; its technique is `RGB_lit_soft`.

An `RGB_*` technique **ignores the texture's alpha channel**. The shape of our sheets
is in the alpha (DXT5) → every particle draws the whole cell as **an opaque square**.
In game the symptom looks very much like the grid and reads as "still square by square",
but the cause is completely different.

Measured: 13 of 15 transplant outputs are `RGBA_lit_soft`, two
(`fire`, `fireball` — both with the `fire_map` donor) are `RGB_lit_soft`.
The fix is `RGB_x` → `RGBA_x`; the technique is a plain string field.

**Gate:** check the technique after the transplant — an alpha texture + `RGB_*`
technique combination is a silent failure.

---

## 1d. Density and structure — the vanilla band

After the format worked, the remaining complaint was: *"not as dense as
the reference"* and *"the fog effect does not come out right because 1024 looks sharper"*.
Both are content problems, and both can be measured.

### ⛔ OUR SHEETS NEVER REACHED OPACITY

Measured — the alpha **peak** of the 15 families was 0.30–0.47, in vanilla smoke sheets
0.59–0.97. The effect is not wrong; it is just not opaque enough anywhere. The cause is not in
one place: edge mask + blur + lifetime fade stack up and
crush the peak. Instead of working family by family, the peak is scaled to the target **after**
the sheet is produced (the alpha-peak table in `ptfx_sheet.py`). The criterion is **not the maximum but the
99.7th percentile** — a single outlier pixel dims the whole sheet.

### ⛔ THE COMPARISON GRID MUST MATCH

Comparing density with vanilla's **2×2** sheet gave the wrong target.
In vanilla, the larger the grid, the **sparser** the sheet:

| vanilla sheet | grid | fill | alpha mean | alpha peak | structure |
|---|---|---|---|---|---|
| `ptfx_smoke_new_plumes` | 2×2 | 62.2% | 0.228 | 0.932 | 0.0120 |
| `ptfx_smoke_billow_anim_rgba` | 6×6 | 58.3% | 0.350 | 0.965 | 0.0119 |
| `ptfx_smoke_wispy_anim` | **7×7** | **18.7%** | **0.039** | 0.742 | **0.0052** |
| `ptfx_smoke_thin_anim` | 6×6 | 20.3% | 0.044 | 0.709 | 0.0057 |

The criterion for our 7×7 sheet is `wispy`, not `new_plumes`.

### ⛔ DO NOT RAISE DENSITY BY CRUSHING THE NOISE

To raise the fill, the multiplier was made `0.86 + 0.34·billow`; since the range was
almost constant, the fill rose but **the structure went completely flat** — composited on a grey
background it read like "a blurry ball". Density comes **from the mask and the
threshold**; the noise amplitude stays full.

### ⛔ A SINGLE OCTAVE GIVES NO CURL

Vanilla smoke has two scales: coarse billows + fine filaments. Without the second,
high-frequency layer (`_fbm(c, 3, 9, ...)`) smoke does not read as "smoke".
The criterion is the **gradient** (`structure`): vanilla 7×7 = 0.0052.

### ⛔ THE EROSION THRESHOLD RISES OVER TIME, IT DOES NOT FALL

With `threshold = 0.44 − 0.24·t` the threshold fell so low in late frames that
**all** of the noise passed, the modulation ended, and what remained was **the bare radial
mask — a flat disk**. Real smoke **breaks up** as it disperses:
`threshold = 0.34 + 0.26·t`.

### ⛔ THE SILHOUETTE MUST NOT BE A CIRCLE

If a constant floor (`0.10 + ...`) is added to the mask, a faint disk remains even where the noise is
empty, and the circle edge reads bare. The floor is removed, and the
radius is disturbed by noise (`r − 0.13·(d1 − 0.5)`).

### Measure density on a GREY background

A dark background forgives low-alpha content; a grey background does not. The density
comparison is done on `(120,122,126)`.

**Result (smoke 7×7):** fill 20.0% · alpha mean 0.058 · peak 0.618 ·
structure 0.0043 — within the vanilla `wispy` band.

---

## 1e-BIS. ✅ THE SHEET IS SLICED — VISUAL PROOF OBTAINED (2026-09-02)

**§1e's verdict "sheet slicing does not work at all in a custom `.ypt`"
IS WRONG.** §1b's `t1` row was right after all.

### Proof — an experiment with a single interpretation

2×2 sheet, **four different shapes** in four cells: disk · ring · plus · triangle.
In a single frame taken in game **all four appear separately, as whole particles**:
two rings (hollow centres), two triangles, one plus, two solid disks —
different position, different size, different rotation.

⏵ If the sheet were not sliced, **every particle would be a single square
stamp containing all four**, and all particles would look identical.

Image: `flipbook_experiment/P4_zoom.png` (a night background is the condition that makes the shapes
most readable — daytime frames could not be read at low contrast).

**Numerical confirmation:** **none** of 25 in-frame particles carries the whole-sheet
signature. Ground truth: disk/plus/triangle hole=0.00, ring hole=0.41,
**whole sheet hole=0.12**. Measured: all ≤ 0.045, most ≤ 0.02.
⚠ This count cannot catch rings (two overlapping rings fall into a single
component and their holes close) — the claim "there are different shapes" is read from the image,
the claim "no particle draws the whole sheet" is read from the numbers.

### ⛔ NO FLIPBOOK — A PARTICLE IS LOCKED TO THE CELL IT WAS BORN IN (measured)

Slicing was proven (above), but **there is no animation**. With a film strip
(one setup, one run, 8 frames 1 s apart, night) the same particle
was tracked **from second 9 to second 15**:

| track | frames | hole ratio sequence | range |
|---|---:|---|---|
| track0 | 7 | 0.00 0.02 0.02 0.00 0.00 0.00 0.00 | 0.00-0.02 |
| track1 | 5 | 0.00 0.02 0.03 0.02 0.01 | 0.00-0.03 |

The ring cell gives 0.41. **No track goes there.** In the image too
(`flipbook_experiment/SAME_PARTICLE.png`) the particle stays a **triangle** for 6 seconds;
it grows and fades, but the shape does not change. `animRate` came from the donor as
**0.8-2** (not zero), so a 4-frame cycle should have taken 2-5 s;
in 6 seconds it should have passed through the ring at least once. It did not.

**Result:** the sheet behaves like a **variety pool** — each particle
picks a cell when it is born and draws it for its whole lifetime. Under these conditions
the look "show one cell, then move to the others in turn" **CANNOT be achieved in a multi-particle
plume**: at any moment particles of different ages show different
cells, and the frame reads mixed.

**`animRate` WAS PUSHED, NOTHING CHANGED (measured).** The donor's 0.8-2 value
was set by hand to **12** (15 times) — a 4-frame cycle should have turned several times a
second. In the 6-second strip the hole range of **all** six tracks was
0.00-0.07; in the image (`d2_kareler.png`) the ring at the top stayed a ring, the triangle on the left
a triangle, the plus in the middle a plus.
**`UnknownC8` = 2** was tried (default 1) — all four tracks 0.00-0.04,
again no change.

⚠ Limit: measured with a single donor (`ent_amb_cig_smoke_linger`); `UnknownCC`
and `UnknownC0` were not tried. Another `animRate` / `UnknownC8` / `UnknownCC` combination may
behave differently — not tried.

### Solution: N emitters + `Unknown10` delay → `layered-effects.md`


### ⛔ OLD WARNING (still valid): SLICING ≠ FLIPBOOK

What was proven is **slicing**: different particles draw different cells.
**That a single particle moves between cells over its lifetime
was NOT PROVEN.** In a single multi-particle frame the two cases look exactly the same:

- **(A)** a particle picks a cell when it is born and draws it for its whole lifetime
- **(B)** a particle advances 0→1→2→… over time → A REAL FLIPBOOK

For the (A)/(B) distinction a **film strip** mode was added (`server.lua`, `kareler` = frames):
setup ONCE, frames in succession within the same run. The old `adim()` (step) restarted the
effect at every frame; two frames belonged to two separate runs. In one strip the
hole ratio stayed ~0.00 for 8 s — **a tendency towards (A)**, but in that run
the particles overlapped, so it is not decisive. **OPEN QUESTION.**

### ⛔ MEASUREMENT RECIPE — do not try again without following it

Six rounds were wasted before reaching this result; the reasons:

1. **Calibration is required.** Particle size is the PRODUCT of `--size-scale` (texture) and the step's
   `olcek` (scale, of the effect). If they are guessed separately, it either fills the frame
   or becomes invisible. **First deploy a single asset and sweep `olcek`**
   (0.5/1/2/3) — no rebuild needed. Measured: `olcek=2.0` → 8 isolated
   particles, diameter ~130 px, all inside the frame. That is what you are after.
2. **Donor type.** `exp_grd_grenade_smoke` is a JET — particles shoot upwards
   and leave the frame. Use one that stays in place:
   **`ent_amb_cig_smoke_linger`**.
3. **Discard the frame edge.** A component with `x<=2 || x>=1918` is a clipped
   piece; its diameter is read wrong (a 31×110 px "particle" came out).
4. **Density must be equal in both arms.** A dense arm merges particles
   (620 px cloud), a sparse arm spills out of the frame; no isolated
   particle is left to compare.
5. **A night background is BETTER than day.** Shapes read on a dark background.
6. **Mask the HUD corner** (`m[950:,1450:]=False`) — the "Downloading assets"
   notification came out as the most changing region and pulled the frame there.

Alternative discriminating test (`proof_sheet.py`): on a 2×2, only one cell filled +
a control with all four filled. If it is sliced, the isolated particle **diameter** stays equal
(the count drops to ~1/4); if it is not sliced, the diameter drops to **half**. Measured ratio
0.74× and 1.07× — both ~1.0, i.e. towards slicing (the sample count was small,
the visual proof is the main basis).

⛔ **THIS SECTION WAS ONCE WRITTEN TOO CONFIDENTLY AND WAS TAKEN BACK.** Its first version
said "sheet slicing works, measured". Its basis was an **interpretation** of
screenshots: the impression that different particles showed different shapes.
A measurement with a single interpretation **could not be made**.
Declaring §1e "invalid" for that reason was also premature.

**Status:** §1b's `t1` row (vanilla rule + our 2×2 sheet = ✅)
and §1e's "does not work at all" verdict contradict each other. Which one is right
is **still unknown**. The safe production path has not changed: single frame.

### The TWO SEPARATE questions being measured — do not mix them

1. **SLICING:** does the engine split the sheet into cells?
2. **FLIPBOOK:** does a single particle move between cells over its lifetime?

⚠ Even if (1) is true, (2) may not be: each particle may pick a
cell when it is born and draw it for its whole lifetime. In a single multi-particle frame
the two cases look **exactly the same**. **There is no clean measurement for either.**

### The tool that was built (works, usable)

- **Film strip mode** (`server.lua`, the `kareler` field): setup ONCE,
  frames in succession within the same run. The old `adim()` restarted the effect at every frame;
  two frames belonged to two separate runs, and the same particle could not be tracked.
  Question (2) can only be answered with this.
- **Clock freeze** (`SetMillisecondsPerGameMinute`): during a 15 s strip
  the GTA clock advanced and turned the scene to night; the base frame was day,
  and when the measurement frames were night the difference drowned in lighting and the "largest
  component" came out as the sky. One series was entirely invalid for this reason.
- **Discrimination sheet** (`flipbook_experiment/proof_sheet.py`): 2×2, only one
  cell filled + a control with all four filled. This is the test with a single interpretation:
  if it is sliced, the particle **size** stays the same in both conditions (the count drops to ~1/4);
  if it is not sliced, the particle count stays the same but the disk is at **half diameter**
  and sits in the top-left quarter of the square.

### ⛔ WHY NO RESULT WAS OBTAINED — do not repeat it

The two arms of the discriminating test **must have equal density**. The four-cell arm
(7.9% brightness) blended the particles into each other (620 px merged cloud),
while the single-cell arm (0.49%) spilled over the right edge of the frame and left only a clipped
piece (31×110 px, x=1904). **Both arms need isolated, fully visible
particles**; first the density is equalised with a low `--rate`, then
`--size-scale` and the step's `olcek` are tuned **together** (in this round they were always tuned in opposite
directions: while one enlarged, the other pushed it out of frame).
Criterion: **isolated particle diameter ratio** — ~1.0× sliced, ~2.0× not sliced.

⛔ **§1e BELOW IS INVALID. Read this first.** §1e said "slicing does not work
at all, grid size makes no difference" and set the production path as single frame
(`C4=0`). This was refuted by measurement. §1b's `t1` row
(vanilla rule + our 2×2 sheet = ✅) was right from the start; §1e overwrote it
without explaining it.

### What was measured

Six subjects, built via transplant; the sheet a **checkerboard** (cells
alternately a solid disk / a ring with a hollow centre), DXT5 + mip, `RGBA_lit_soft`,
`FxcFileHash` filled, all audited by read back:

| subject | donor (its own grid) | `C4` written | sheet | result |
|---|---|---:|---|---|
| b1 | `exp_grd_grenade_smoke` (2×2) | 3 | 2×2 | ✅ slices |
| b2 | same (2×2) | 15 | 4×4 | ✅ slices |
| **b3** | **same (2×2)** | **48** | **7×7** | **✅ slices** |
| b4 | `ent_amb_cig_smoke_linger` (7×7) | 48 | 7×7 | ✅ slices |
| b5 | 7×7 donor | 15 | 4×4 | ✅ slices |
| b6 | `ent_amb_bubble_stream` (5×5) | 24 | 5×5 | ✅ slices |

### ⛔ READ THIS FIRST: "SLICING" ≠ "FLIPBOOK"

The measurements below prove **that the sheet is sliced**: different particles
draw different cells of the sheet. **They DO NOT PROVE that a single particle MOVES between
cells over its lifetime.** In a single frame the two cases look exactly
the same:

- **(A)** each particle picks a cell when it is born and draws it for its whole lifetime
  → NO animation, only variety
- **(B)** each particle advances 0→1→2→... over time → A REAL FLIPBOOK

The distinction can only be made **within a single run, by tracking the same particle over time**.
For this a `kareler` (film strip) mode was added to the test bench:
setup ONCE, then frames in succession at the given moments (`server.lua`).
⚠ The old `adim()` restarted the effect FROM SCRATCH at every frame; two frames belonged to two separate
runs, and the same particle could not be tracked.

**As of 2026-09-02, whether it is (A) or (B) has NOT BEEN MEASURED YET.** The only
usable strip (`ent_amb_cig_smoke_linger` donor, 2x2, over 8 s)
showed the hole ratio **always ~0.00** — had the particle passed through the ring cell
it would have had to be 0.41, so **there is a tendency towards (A)** — but in that
run more than one particle overlapped, so it is not decisive.
Single-particle runs (`--rate 0.15-0.2`) came out too faint to read.

⛔ **The next session must NOT SAY "flipbook works" without resolving this distinction.**
Needed: a single particle (low `--rate`) + **big and bright enough to read**
(`--size-scale` and the step's `olcek` tuned together) + film strip +
frozen clock. Criterion: the hole ratio OSCILLATING between 0.00 ↔ 0.41
over time.

⛔ **FREEZE THE CLOCK.** When the film strip lasted 15 s, the GTA clock advanced and turned the scene
to night; the base frame was day, the measurement frames were night, and the difference
drowned in lighting — the "largest component" came out as the sky, and one series was
entirely invalid for this reason. `SetMillisecondsPerGameMinute(2147483647)`
was added inside `kur` (setup).

### ✅ RESULT (for SLICING only): `C4` DRIVES THE GRID, NOT THE DONOR

`b3` is decisive: **the `C4` of a donor with a 2×2 texture was set by hand to 48, and
the engine sliced our 7×7 sheet correctly.** So:

- There is **no source constraint, as a rule,** on grid size; `C4 = frames − 1`
  is written and the sheet is split on that grid.
- The grid of the donor's own texture is **not binding**. This matters, because
  **there is NO single-emitter 4×4 donor**: all 8 rules carrying `C4=15` are
  in 2-4 emitter effects (measured). Since `C4` can be written, this is not an
  obstacle.
- The vanilla band ceiling is still **49 frames (7×7, `C4=48`)** — rules with `C4>48`:
  1, with `C4>63`: 0. Do not go above 7×7.

### ✅ PRODUCTION PATH (REPLACING §1e's "single frame" recipe)

1. Produce the sheet, write **`C4 = frames − 1`** (2×2→3 · 4×4→15 · 5×5→24 · 7×7→48)
2. The donor must be **single-emitter**; **override** its `C4` to match our sheet
3. `FxcTechnique` must be **`RGBA_*`** (`RGB_*` ignores alpha — §1b)
4. Texture **DXT5 + mip**, size a power of 2; aim for 128-192 px cells
5. Build with `ypt_xml_to_bin.ps1` (hash), read back and audit `C4` + technique + size

### ⛔ THE PART THAT STILL STANDS: A RULE WRITTEN FROM SCRATCH

§1b's `t2..t5` rows are still valid: **the rule blocks our own generator writes
from scratch do not make the engine apply the grid** (2×2 included). The responsible field
has still not been found. The correct sentence is NOT "flipbook does not work in GTA", it is
"**our from-scratch rule writer does not work, transplant works**".

### ⛔ MEASUREMENT METHOD — THREE errors fixed in the test bench, all three SILENT

In this round the diagnosis "the effect does not appear" was wrongly made twice. Each time
the **reference step** (the game's own effect) also came out empty, which showed the defect was
not in our asset. **Do not measure without a reference step.**

1. `baslat()` (start) ignored the given asset and looked at the fixed `VARLIK` (asset) map;
   the map only knows the 15-family catalogue → the new asset **never spawned**.
   Fixed: the given asset is used + requested with `RequestNamedPtfxAsset`.
2. The target was placed on a fixed world axis (`k.y + distance`) → if the ped faces another way,
   the effect falls outside the frame. The target must be **on the forward vector**.
3. The camera was behind the ped → with the target on the forward vector, **the ped covers
   the effect**. The camera is placed **beside** the effect.

⛔ **BLEED BETWEEN STEPS IS REAL.** The living particles of the previous step stay in
the next frame; colour-based assignment is not reliable either (hue normalisation
blends different colours into each other). **For an exact reading each subject is shot ON ITS
OWN.** b3's verdict above was read from a single-subject frame (verified with the colour difference
R−38 G−9 B+63).

**Reading criterion (works on any grid):** checkerboard sheet → if there is slicing,
some particles are **without a hole** (disk) and some **with a hole**
(ring, ~0.41). If there is no slicing, EVERY particle also contains the ring cells →
a particle without a hole **cannot exist**, and the hole ratio comes out constant ~0.20.
⚠ This statistic weakens at 7×7 (the cell gets small on screen, the hole is
lost in JPEG) — there **visual reading** is required, but in a single-subject frame.

The experiment scripts are not in the repository (one-off measurement).

---


## 2. ⛔ THE LAST FRAME COMES OUT EMPTY — happened in 15 of 15 families

The family generators compute `t = i / (n - 1)`. If `n = frames` is passed, the last frame
gets `t = 1.0`, and the `(1 - t) ** k` fade factor in every family gives **exactly zero**.
`Unknown_C4h = frames − 1` makes the engine draw that frame too → the effect **blinks**
for one frame every loop.

**Solution:** `fn(i, frames + 1, ...)` — the last frame becomes `t = 48/49 = 0.980`;
the fade completes but does not empty.

This is **not enough on its own**: even after the fade factor was fixed, 4 families
still had empty frames, and the cause was the family's **own envelope**:

| family | empty frame | cause |
|---|---|---|
| `ring` | tail | the ring leaves the frame |
| `fog` | **head** (7 frames) | the envelope peaks at `t=0.5` and fades to both sides |
| `bubble` | frame 0 | the first bubble starts with a delay |
| `dust` | **frame 11 (middle)** | the generator dropping a frame |

So the head, the tail and the **middle** can all be empty; three separate causes.

### Three-stage gate (inside the sheet builder in `ptfx_sheet.py`, all in one place)

1. **`frames + 1`** — prevents the fade factor from reaching zero.
2. **Range narrowing, LOOPED.** Based on the measured first/last filled frame, the `t`
   range is fitted to `[t0, t1]`. ⛔ **A single pass does not converge** — narrowing
   can push the new boundary frames to zero again (measured: `ring` went from 1 empty frame
   to 1 empty frame in one pass, `fog` dropped from 7 to 2 but did not
   reach zero). At most 6 rounds, pushed 2% inwards each round.
   The range shift is built with `n` and `ofs`:
   `(n-1) = (frames-1)/(t1-t0)` and `ofs = t0*(n-1)`; **`ofs` is rounded
   to an integer** because some families also use `i` in the randomness seed
   (`_rng(2600 + i*3)`).
3. **Neighbour blend.** Every remaining empty frame is filled by linear blending from its nearest filled
   neighbours. This is the only stage that touches a gap in the middle.
   How many frames were filled **is reported** — the patch is visual, it does not hide the cause.

### ⛔ Measurement is done on the data that is SENT

Two rounds were wasted: the gate measured alpha as a **float**. A value of 0.0201
counted as "filled"; but `write_png()` rounds to uint8 (0.0201 → 5 → 0.0196), and the
frame that was sent fell **below** the threshold. The `smoke` last frame and the `fog`
frame 0 passed the gate and came out completely empty in the PNG.

```python
q = np.floor(np.clip(alpha, 0, 1) * 255.0 + 0.5) / 255.0
return float((q > 0.02).mean())
```

General rule: **if there is quantisation, the gate looks at the quantised value.**

---

## 3. ⛔ The frame must NOT TOUCH the cell edge

If a flipbook frame touches the cell edge, a **hard cut** appears at the border of the sprite quad
in game; in vanilla sheets frames sit inside a transparent border.

Measured: `fire` touched the edge with **0.44** alpha, `smoke`/`spark`
were clean with **0.00**. My first manual check only looked at 3 families and 9 frames,
so it missed 4 families; the automatic gate caught them all:
`ember` 0.43 · `bubble` 0.67 · `debris` 0.42 · `electric` **0.98**.

Two layers:
- The sheet builder applies a **smoothstep edge mask** to every frame (4.5% margin).
- The mask **does not hide**: if the raw overflow exceeds 0.35 it prints a warning, because content
  that overflows that much does not fit in the cell and the mask **clips** it (the effect thins out).

**The range must account for the radius.** Even if a grain's centre stays inside the cell,
its radius worth spills outside. Free-walking content (electric arc)
is **clamped** directly (`0.12..0.88`).

---

## 4. ⛔ rng must be ONE PER PASS

Creating a new `_rng(seed)` per frame gives every frame **the same** random
sequence; the frames come out identical (static sprite), and there is no
error. Since range narrowing has two passes, it is easy to fall into this pitfall.

---

## 5. Family design — three measured lessons

### Do not normalise the phase, build a FLOW
In the first version of `bubble` each bubble's phase was normalised with
`tk = (t - delay) / (1 - delay)` → even though they started with delays
**they all arrived at the same moment**. In the last frames three bubbles were side by side
at the same height; it read not as "rising bubbles" but as "three rings".
The right way is a continuous flow: `tk = (t + k/N) % 1.0`. Side benefit —
the sheet loops perfectly by itself.

### Do not build colour channel by channel
In `fireball` R/G/B were written with separate formulas; when the channels faded at different speeds,
the core came out first dull orange, then **greenish**. Channel
crossover silently makes up colours. The right way is to build a single **temperature field** and
interpolate between fixed colours: `smoke → fire → white`.

### The right colour alone is not enough — ALPHA must be in the core too
Even **after** the colour was fixed, the core looked grey: the alpha there was
~0.34 and the background showed through; at the edge the lobes overlapped, so
the alpha was high → **"grey centre, orange ring"**. The centre of an explosion is
its most opaque place.

### One effect is NOT a coloured version of another
The `fire` family generator initially called the `smoke` generator in its hot variant, and looked nothing
like fire. What defines smoke is dispersal; what defines fire is **tongues
rising upwards**. In the same way `fog` in its first version was identical to `steam`;
what sets fog apart is being **wide and low**, what sets steam apart is **wisps
stretching upwards**.

---
