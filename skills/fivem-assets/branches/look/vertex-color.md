# Vertex color — interior ambient, measured meaning of the channels, "unpainted white", bucket rule

**When to read:** your own model glows / is too bright in an interior; interior ambient shading through vertex colors; what the `Color 1` channels mean; R/G target values; fake bounce light; a green tint on a decal.
**Source:** `lights.md` vertex color sections + 'interior rule' (morgue MLO measurement, 2026-08) · **Measured:** facility 66 files, vault, v_coroner shell; 105 files with read-back
**Read first:** `_branch.md` · trunk › `trunk/tool-pitfalls.md` §1-2 · vanilla interior bands `branches/map/vanilla-interiors.md` §4

---

### ⛔ INTERIOR RULE: vanilla writes `R = 0` — a Blender round trip BREAKS it

This is a measured rule, and it once cost a great deal.

**On vanilla interior (MLO) surfaces the R channel of vertex color 0 is EXACTLY 0.**
This is what isolates the MLO from the outside world: R=0 → the sky/natural ambient layer
is off → the interior is not affected by the outside weather, sun and sky reflection.

A Blender import/export round trip does not keep this zero. Measured (v_coroner morgue,
214 models):

| | vanilla | after the Blender round trip |
|---|---|---|
| `v_med_cor_offglass` | **0** / 153.6 / 38 | **118.4** / 135.8 / 109 |
| `v_ilev_cor_doorglassa` | **0** / 90.7 / 121.2 | **53.2** / 107 / 134.4 |
| `v_2_ala_mesh_delta` | **0** / 120 / 152 | **120.1** / 124.8 / 154.6 |

**The symptom — and the hardest part to diagnose:** the user says "the map is far too wet,
everything reflects like crazy". It looks like a lighting setting, but it is not.
Because the natural ambient layer is open, the interior picks up the outside light and the
sky reflection.

⛔ **While chasing this symptom, ALL of these are the wrong address** (each was measured
separately and each came out in the vanilla band — they cost rounds):
spec texture brightness · bright speckle ratio in the spec texture · normal
map strength · `specularintensitymult` / `specularfalloffmult` /
`specularfresnel` / `bumpiness` / `reflectivepower` · `environmentsampler`
binding · diffuse bound into the spec channel (vanilla does this MUCH more than we do) ·
generated dirty textures · room/portal flags · weather cycle (rain).

**The right measurement and fix:** compare the model's vertex color 0 R mean with its vanilla
counterpart; if vanilla is `< 5`, ours must be `0` too.

```powershell
# do not assume the offset is fixed - take it from the declaration
$ofs = $vd.Info.GetComponentOffset([CodeWalker.GameFiles.VertexComponentType]::Colour0)
for($i=0; $i -lt $vd.VertexCount; $i++){ $vd.VertexBytes[$i*$vd.VertexStride+$ofs] = [byte]0 }
```

After the fix, the criterion: the vertex color mean must match vanilla
(measured case: 64.5 → **61.7**, vanilla 60.8).

⚠️ **Do not zero the G channel blindly** — that switches off the artificial interior layer and
makes the room pitch black. Only R.

#### This rule must become a GATE, not something left to memory

This breakage **comes back with every Blender export**. Left to memory,
the user has to go in game every round and say "wet again" —
this happened, many times. The right way is to tie deployment to one gated script:

```
<deploy_script> -Source <folder> [-Test]      (example pipeline; script not in the repository)
  1) vertex color R -> 0   (fixes it automatically, nothing to remember)
  2) texture gate          (does every referenced texture resolve)
  3) collision gate        (if vanilla has a bound, do we have one too)
  4) structural gate       (physics + geometry + R final check)
  → if any one fails, it does NOT TOUCH stream/ AT ALL
```

⛔ **Writing the gate is not enough; run its NEGATIVE TEST too.** Set one model's R to
128 on purpose and watch the script fix it. An unproven gate is not a gate —
a gate that said "checked 0 files, passed" happened once in this project.

⛔ In the file filter do NOT USE `Get-ChildItem -Include *.ydr,*.yft -Recurse`:
it also catches `.ycd/.ytd/.ytyp` and raises a false "no geometry" alarm.
Use `-File | Where-Object { $_.Extension -in '.ydr','.yft' }`.

## Vertex color channels — MEASURED, and my earlier note was WRONG

⛔ **This file used to say "gated by the .r and .g channels of vertex color 0
(natural/artificial)". WRONG.** Sollumz's own documentation
(`docs.sollumz.org/2.6/tutorials/creating-interiors/texturing`) and the vanilla
measurement say this — `Color 1` (= `Colour0`, CORNER domain, BYTE_COLOR):

| channel | what it does | vanilla usage |
|---|---|---|
| **R** | **night ambient occlusion.** The higher it is, the DARKER at night. | mostly pushed to **255** on surfaces without a night lamp |
| **G** | **artificial light.** 255 = self-lit effect. | raised on surfaces near a lamp/light source |
| **B** | **moonlight reflection.** The higher it is, the more outside light it takes. | R\* uses it often so the place does not go fully dark |

**Height rule (from the user, verified in vanilla):** lower half of the shell
green→dark green, upper half blue→dark blue; red-yellow around windows/doors that open
to the outside and where the sun will hit. In a two-storey interior the
first floor is mostly green, the second floor mostly blue.

Measurement — `v_57_franklin_int` (vanilla, single storey), `Colour0` offset 24, RGBA:

| z band | R | G | **B** |
|---|---|---|---|
| −1.50…−1.11 (floor) | 49 | 116 | **4** |
| −1.11…−0.72 | 174 | 132 | **0** |
| −0.32…0.07 | 82 | 108 | **41** |
| 0.07…0.46 | 220 | 89 | **255** |
| 1.25…1.64 (ceiling) | 94 | 76 | **255** |

Blue is ~0 at the floor and 255 at the ceiling — the gradient is real.

⚠️ **A vanilla interior does not mean "dark".** The `v_coroner` morgue was measured:
R ≈ 0–29 (almost no night AO), B ≈ 234–255 (takes the moonlight fully).
So that interior is painted to be **bright**. If a dark/horror theme
is wanted, timecycle alone is not enough; **the vertex color has to change
too** (R up, B down).

### ⛔ The right way to FIND the color offset in CodeWalker

The wrong offset was read THREE TIMES in one round. The causes, in order:

1. There is **NO member** `[CodeWalker.GameFiles.VertexComponentType]::Colour0`
   (the real members: `Nothing, Half2, Float, Half4, FloatUnk, Float2, Float3,
   Float4, UByte4, Colour, Dec3N, Unk1..Unk5`). For a static member that does not exist PowerShell
   **gives no error, it returns `$null`**; `GetComponentOffset($null)` → **0**,
   i.e. the POSITION is read. (§ "the tool not showing it does not mean it is absent")
2. `GetComponentOffset(Colour)` returned **36** — that is the offset of **Tangent0**.
   This function looks up the data type, not the semantic slot.
3. On a mesh without a color component it still returns a number (equal to the stride) — it does
   not tell the "absent" case apart.

**The right way is to compute it from the declaration.** `Info.Flags` tells bit by bit which
semantic slots exist, `Info.Types` gives a 4-bit type per slot:

```
slot order : Position BlendWeights BlendIndices Normal Colour0 Colour1
             TexCoord0..7 Tangent0 Tangent1 Binormal0 Binormal1
type size  : Nothing 0 · Half2/Float/UByte4/Colour/Dec3N 4 · Half4/Float2 8
             Float3 12 · Float4 16
```

**Criterion: the computed total = `VertexStride`.** If it does not match, the decoding is wrong.
For `DefaultEx` (Flags=16473): Position 0 · Normal 12 · **Colour0 24** ·
TexCoord0 28 · Tangent0 36, total 52 = stride ✓

**Byte order RGBA** (cross-checked against Blender's Sollumz decoding:
binary `[12,56,255,240]` ↔ Blender `R=12 G=56 B=255 A=240`).

Safest path: if possible, take the measurement **in Blender** through `color_attributes["Color 1"]`
— Sollumz already decodes it correctly, and the painting will be done there anyway.

### Vertex color — MEASURED TARGET VALUES (vanilla interiors)

⚠️ **The R description in the Sollumz documentation is misleading.** It says "R is night AO,
mostly pushed to 255 so it gets very dark"; the measurement shows the opposite:

| interior | R | G |
|---|---|---|
| `v_55_shell` (torture room, **very dark**) | 0–20 | 1–22 |
| `v_44_shell` (Michael's house, **bright**) | 71–132 | 58–167 |
| `v_57_franklin_int` (bright house) | 49–220 | 76–132 |
| `v_2_*` (morgue, vanilla) | 0–29 | 0–92 |

**Higher R/G = brighter.** For a dark/horror theme R and G must stay
low (0–25 band).

**The BLUE vertical gradient is universal** — at normalized height (0%=floor, 100%=ceiling):

| model | 10% | 20% | 40% | 50% | 60% | 70% | 90% | 100% |
|---|---|---|---|---|---|---|---|---|
| `v_55` dark | 0 | 0 | 0 | 0 | 66 | 184 | 255 | 208 |
| `v_44` bright | 5 | 0 | 22 | 2 | 63 | 255 | 255 | 255 |
| `v_57` franklin | 4 | 0 | 43 | 17 | 255 | 206 | 255 | 255 |

**Rule: lower 50% → B ≈ 0–40 · transition 50–60% · upper 40% → B ≈ 200–255.**
That is exactly the "green below / blue above" in the vertex paint view:
below, B=0 + G>0 reads green; above, B=255 reads blue.

Other measured links:

- **`Colour1` (Sollumz "Color 2") is NEVER used in interior shells**
  (`v_55`, `v_44`, `v_57`, morgue — 0 geometries in all four). Only `Color 1`.
- **Alpha is 255 in shells.** Alpha below 255 shows up only on decal/overlay meshes
  (blend factor): morgue `over_decal` 76, `bsnt_shell` 127 in places.
- **There is NO shader that does not read vertex color.** In 60 vanilla interior files,
  250+ geometries, every geometry of every shader declares `Colour0` —
  not a single exception. If the declaration has `Colour0`, the shader reads it;
  there is no need to also ask "does this shader ignore the paint".
- Morgue side: **all** 994 geometries have `Colour0`, all of them paintable.

---

## Vertex color: detecting "unpainted white" and the measured meaning of the channels

**Measurement pipeline** (1,626 geometries / 4 interiors, built this round):
`extract_asset.ps1 -Pattern '*.ydr' -PathFilter '<interior>.rpf'` → CodeWalker
`YdrFile` → `VertexBuffer.Info.GetComponentOffset(4)`.

### Five silent pitfalls — all five happened this round

1. ⛔ **`GetComponentOffset` takes a SLOT INDEX, not the type enum.**
   `Colour0` = **slot 4**. `VertexComponentType.Colour` (=9) is a *type*;
   passing it as an index reads slot 9 and returns **offset 36** (Tangent0).
   Slot order: 0 Position · 1 BlendWeights · 2 BlendIndices · 3 Normal ·
   **4 Colour0** · 5 Colour1 · 6-13 TexCoord0-7 · 14-15 Tangent0-1.
   Verification: `DefaultEx` (Flags=16473) → Colour0 offset **24**, stride 52.
   Presence check `Flags & 16` (Colour0), `Flags & 32` (Colour1).
2. ⛔ **`VertexBuffer.Data1` is NOT a byte[]; it is a `VertexData` object.**
   The bytes are in `Data1.VertexBytes`. `$data.Length` returns `$null`,
   the comparison `$p+3 -ge $null` triggers `break` and **the loop silently runs empty**:
   0 rows, 0 errors. `Data1` and `Data2` **are the same object** (ReferenceEquals
   True) — patching one is enough.
3. ⛔ **A shader parameter's `Data` is NOT a `System.Numerics.Vector4`.**
   `-is [System.Numerics.Vector4]` silently drops every parameter and the table
   comes out empty. Do not look at the type name, look at the field: `$dv.PSObject.Properties['X']`.
   (Seeing `Data=Vector4` in the diagnostic output is misleading — that is not `ToString()`,
   it is the ELSE branch that prints `GetType().Name`.)
4. ⛔ **A list file written by Python on Windows carries CRLF**; a name read with bash
   `while read` gets a `\r` stuck to it and PowerShell
   says *"Illegal characters in path"*. `tr -d '\r'`.
5. ⛔ **`| tee x | head -N` closes the pipe early**, the log file is cut off halfway
   and you read **a false success count** such as "8 files processed". Verify whether the
   file was really patched **by measuring again**.

### Meaning of the channels — measurement, not doctrine

| interior | R | G | B | "unpainted white" (R=G>200) |
|---|---:|---:|---:|---:|
| `xm_x17dlc_int_facility` (gloomy, fully buried) | **0.0** | 109.7 | 187.6 | **0.0%** |
| `ch_dlc_int_09_ch` (vault — enclosed **but bright**) | 186.2 | 205.3 | 135.5 | **69.9%** |
| `v_coroner` basement shell (vanilla) | 12.7 | 33.8 | — | — |

⚠️ **There is NO rule "R must be zero in an enclosed interior"** — the vault refutes it:
underground, windowless, and 70% of its geometry is R=G=255. The difference is the
lighting direction, not the enclosure. R is zeroed in **gloomy** places:
across facility's **66 files and all four of its subgroups (shell/detail/blend/other),
R = 0.0 without exception**; G meanwhile varies freely between 37 and 153.
So **R is a direction decision, G is an artistic value** — do not pin G to one number.

**`R == G` and both >200 ⇒ the mesh was never painted** (the Blender/Sollumz
default white). What gives it away is the equality: in a mesh that was really painted
R and G are independent. Scan the models you add with this test —
measured: **8 of 9** of our own `my_*` models sat at R=G=225-255,
while the shell they stood on was R=12.7. The defect is not "R is high",
it is **the model not matching the map it was placed in**.

**Choosing the target:** a floor decal takes the value of **the mesh it lies on**
(here `v_2_bsnt_shell` → R=12 G=47). For an object/prop **do not touch** G,
only pull R down to the shell level — readability is kept. Measured result:
R 83.0 → 16.3, unpainted share 19.7% → **0.0%**, G 102.4 → 94.9 (almost
unchanged), B did not change at all.

### Specular side: do not say "let me turn it down" without looking

Medians in the same measurement — **ours was already far below the darkest vanilla
reference**, there was nothing to gain there:

| param | vault | facility | ours |
|---|---:|---:|---:|
| `specularintensitymult` | 1.000 | 0.800 | **0.071** |
| `specularfresnel` | 0.920 | 0.950 | 0.750 |
| `bumpiness` | 1.000 | 0.800 | 0.700 |
| `wetnessmultiplier` | 1.000 | 1.000 | **0.000** |
| `emissivemultiplier` | 8.000 | 6.000 | 0.900 |
| reflective shader (vertex share) | 1.7% | 7.8% | 7.7% |

Our reflective shader share is identical to facility (7.7% / 7.8%) — so the
diagnosis "there is too much reflective material" was not based on measurement either.

### A SURFACE you add to an MLO must not get prop flags

⛔ **`Dont Render In Reflections` (bit24, 16777216) is normal for a prop,
a defect for a surface.** Measured (`v_coroner`): **61.6%** of 583 vanilla entities
carry **`18350080`** — so this is Rockstar's prop standard in this MLO,
not an anomaly. **But it treats the shells differently:**
`v_2_bsnt_shell` / `v_2_strs_shell` / `v_2_tpoff_shell` → **`1572864`**
(Cast Static + Cast Dynamic, **visible** in reflections).

The `AttachedObjects` of the `limbo` room shows the split: vanilla put
only 3 shells + 3 `v_2_shadowmap*` there. The shadowmap proxies are
`22544384` = shell flag + **`Disable shadow`** + `Dont Render In
Reflections` — invisible helpers that exist only to cast shadows.

**Conclusion:** when adding your own ceiling/floor/shell to an MLO, copy the flag
from the neighboring **SHELL, not from the neighboring prop**. Getting it wrong has two separate
symptoms, and both read as "the reflection is broken":

- ceiling missing from reflections → the floor reflects **the void/sky**;
- your floor overlay missing from reflections → a dirty floor when looking directly,
  **spotless vanilla tiles in the reflection**.

The third face of the same error was measured earlier: a shell carrying `18350080`
**had not loaded at all** (the archetype's `textureDictionary` was 0 too).
Finding it once and fixing it **only on that object** is not enough — do a **sweep** over `limbo`
and all the entities you added.

Check (one line): dump the `AttachedObjects` of `limbo` and see whether the flags of the
ones you added match those of the vanilla shells.

### ⛔ Vertex color darkening applies ONLY to bucket 0

The `R == G > 200 => unpainted` heuristic from the previous section holds **only for
`RenderBucket == 0`** (opaque, lit surface). There RGB are three
separate **light masks** and asymmetry is normal (vanilla shell 12/32/42,
facility 0/110/188).

**In a non-opaque bucket (1 glass / 2 decal / 3 / 7) RGB behaves like a multiplier**,
and lowering R while leaving G **shifts the hue**. Measured: when the floor decal
went from 227/227 -> 12/47, the ratio went from 1:1 to **1:3.9** and the floor turned
green. Every other source of green was ruled out: the atlas texture is rust (R=54 G=12 B=8,
green-dominant cells in a 10x10 grid: **0**), **all 217 lights** on the map are
warm red-orange (255,76,46).

⚠️ "G=R on a decal" is **not universal** either: it holds in this map's
vanilla (`decal_dirt` 31/31, `decal_normal_only` 158/158,
`normal_decal` 222/222 -- in all three `G-R = 0.0`), but in facility bucket
2 has `|G-R| = 144` and a G=R share of **0%**. The reference is always **the map's own
vanilla**, not another DLC.

If you touched it by mistake, revert **per geometry**, not per file --
the gain in the opaque part must be kept. The backup and the live file keep the same
geometry order (if only vertex bytes changed); copying the Colour0 R/G/B bytes of the
geometries with `RenderBucket != 0` is enough.

⛔ Also: **PowerShell variables are case-insensitive.** The grid
size `$N` and the loop counter `$n` are the same variable; in the second file `$N` was
reset and produced **a false measurement**: "0 green cells".
