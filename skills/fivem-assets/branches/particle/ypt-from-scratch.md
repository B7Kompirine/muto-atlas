# Particle `.ypt` from scratch — sheet, keyframe slots, transplant, motion envelope

**When to read:** you will write your own particle (sparks, drops, energy, smoke): texture sheet, `C4`, keyframe slots, donor transplant, `FxcFileHash`, where the motion comes from, the silent failures; "the handle is filled but nothing is on screen".
**Source:** the former ptfx flipbook reference (2.5.0) §1-6, §8, §13 · `trunk/flags.md` §7c-7d (2026-08/09) · **Measured:** `core.ypt` 45.5 MB opened; 107 embedded textures DXT; 15 families in game; sheet slicing with visual proof
**Read first:** `branches/particle/_branch.md` · trunk › `trunk/tool-pitfalls.md` §3 CodeWalker (`FxcFileHash`, `VFT`, `ResourcePointerArray64`) · catalogue/family production `catalog.md` · layered effect `layered-effects.md`

---
## `.ypt` structure and the real XML schema (from `core.ypt`)

Source: JulioNIB, *"Creating and editing a new particle effect based on an
existing one"* (35 min). The structure claims were **verified** against the CodeWalker types.

### `.ypt` structure — five dictionaries

`ParticleEffectsList` (root) carries the following, and **when producing a custom effect all five
are carried over into the new file**:

| Dictionary | Content |
|---|---|
| `EffectRuleDictionary` | the effect itself; each has an **event emitter** list |
| `EmitterRuleDictionary` | emitter rules — **spawn rate** keyframes |
| `ParticleRuleDictionary` | particle rules — **colour/size/speed** keyframes |
| `DrawableDictionary` | models the effect uses (most effects use none) |
| `TextureDictionary` | textures the effect uses |

An effect can carry several **event emitters** (measured: `bang_carmetal`
has 6). **For every event emitter** both the emitter rule and the particle rule must be copied
separately.

### Pipeline

1. Find the `.ypt` that contains the effect → `assetdb.py fx <name> --exact` tells you.
2. **Export to XML** with CodeWalker.
3. **Open a new file** — do not edit the vanilla `.ypt`; it breaks other mods.
   The extension must be in the form `.<name>.ypt.xml` (asset extension before XML).
4. Copy the **opening/closing tags** of the five dictionaries into the new file.
5. Find the effect definition, then the emitter+particle rule of **every event emitter**,
   and paste them into the matching dictionary.
6. Also copy the **drawable and texture** entries used into their own dictionaries.
7. Change the **asset name** at the top of the file and the effect name — that is the name
   you will call in game.
8. ⛔ **Create a FOLDER with the same name as the file and put the texture files in it.**
   Otherwise the import fails with "texture not found". (In the video this step
   was forgotten and gave an error twice.)
9. Import back with CodeWalker.

### ✅ THE REAL XML SCHEMA — `core.ypt` opened and read (45.5 MB)

The root is **exactly five dictionaries** (the video is right):
```xml
<ParticleEffectsList>
  <Name>core</Name>
  <EffectRuleDictionary>   <EmitterRuleDictionary>
  <ParticleRuleDictionary> <DrawableDictionary>  <TextureDictionary>
```

**The effect → emitter link is made BY NAME**, not by index:
```xml
<EffectRuleDictionary><Item>
  <Name>_fog_foundry</Name>
  <PlaybackDelay value="2"/> <PlaybackSpeedScale value="1"/>
  <CullRadius value="2"/>    <CullDistance value="-4"/>
  <EventEmitters><Item>
    <EmitterRule>_fog_foundry_core</EmitterRule>
    <ParticleRule>_fog_foundry_core</ParticleRule>
    <MoveSpeedScale value="1"/> <ParticleScale value="1"/>
  </Item></EventEmitters>
</Item></EffectRuleDictionary>
```

### EMITTER RULE — 10 keyframe properties (real names)

Fields: `Name` · `Domain1` · `Domain2` · `KeyframeProperties`

| What for | `<Name>` value |
|---|---|
| **more/fewer particles (over time)** | `ptxEmitterRule:m_spawnRateOverTimeKFP` |
| more/fewer particles (over distance) | `ptxEmitterRule:m_spawnRateOverDistKFP` |
| **time on screen** | `ptxEmitterRule:m_particleLifeKFP` |
| playback speed | `ptxEmitterRule:m_playbackRateScalarKFP` |
| **how far it goes** | `ptxEmitterRule:m_speedScalarKFP` |
| size | `ptxEmitterRule:m_sizeScalarKFP` |
| acceleration | `ptxEmitterRule:m_accnScalarKFP` |
| damping | `ptxEmitterRule:m_dampeningScalarKFP` |
| matrix weight | `ptxEmitterRule:m_matrixWeightScalarKFP` |
| velocity inheritance | `ptxEmitterRule:m_inheritVelocityKFP` |

### ⛔ Keyframe field names are MISLEADING

```xml
<Keyframes><Item>
  <InterpolationInterval value="0"/>
  <KeyFrameMultiplier value="0"/>
  <RedChannelColour value="4"/>    <GreenChannelColour value="7"/>
  <BlueChannelColour value="0"/>   <AlphaChannelColour value="0"/>
</Item></Keyframes>
```

The `*ChannelColour` names are **four general-purpose channels**; they have nothing to do with colour.
`RedChannelColour=4` inside `m_spawnRateOverTimeKFP` means "spawn rate 4".
Inside `m_xyzMinKFP`, Red/Green/Blue = **X/Y/Z**.
This naming is CodeWalker's own choice; the field's meaning depends on **which
`<Name>` it is under**.

### PARTICLE RULE — behaviour list

Fields: `Name` · `FxcFile` · `FxcTechnique` · `Spawner1/2` · **`Behaviours`** ·
`ShaderVars`

The `<Type value="…"/>` values inside `Behaviours` (`core.ypt` count):

| Type | Count | Type | Count |
|---|---:|---|---:|
| Age | 1596 | AnimateTexture | 721 |
| Velocity | 1596 | Collision | 253 |
| **Size** | 1596 | Wind | 245 |
| **Colour** | 1596 | Noise | 119 |
| Sprite | 1444 | Model | 114 |
| Acceleration | 1289 | ZCull | 103 |
| Dampening | 1144 | Light | 65 |
| MatrixWeight | 1110 | Trail · Attractor · Decal · | |
| Rotation | 1109 | DecalPool · FogVolume · Liquid · River | single digit |

### COLOUR — real field names

```
ptxu_Colour:m_rgbaMinKFP            (in all 1596 particle rules)
ptxu_Colour:m_rgbaMaxKFP
ptxu_Colour:m_emissiveIntensityKFP
```

Here `RedChannelColour`/`Green`/`Blue`/`Alpha` **really are** colour.
Other commonly used properties: `ptxu_Size:m_whdMinKFP` / `m_whdMaxKFP`
(width-height-depth) · `ptxu_Rotation:m_angleMinKFP` / `Max` ·
`ptxu_Acceleration:m_xyzMinKFP` / `Max` · `ptxu_Light:m_rgbMinKFP` / `Max`.

⚠ **Still [NOT VERIFIED]:** which field is the flag that makes the colour
changeable from script. The video mentions "a variable" but does not name it;
it is probably one of the `Unknown*` fields of the `Colour` behaviour.
If `SetParticleFxColour` does not work, this is the reason.

## Production chain — CodeWalker.Core writes, works end to end

**Version: CodeWalker 30_dev46, `CodeWalker.Core.dll` 2023-12-13.**
With this version a `.ypt` was produced from scratch, saved in game format and verified by
reading it back. A newer version, the .NET SDK or the GUI is **not needed**.

Verified pipeline:

```
make_dds.py          -> 128x128 A8R8G8B8 sprite (our own)
build_custom_ptfx.py -> .ypt.xml (effect/emitter/particle rules from scratch)
XmlYpt.GetYpt()      -> object tree
YptFile.Save()       -> 7,865 byte RSC7
YptFile.Load()       -> read back: all names + texture in place
```

### ⛔ FIRST THIS: verify the property name BEFORE saying "I measured, it is not there"

The previous version of this section said **"CodeWalker CANNOT WRITE `.ypt`"**. It was wrong, and
it had a single cause: **property names that do not exist were read.**

| What I read | Real | Result |
|---|---|---|
| `EffectRuleDictionary.Effects` | `.EffectRules` | `$null.Length` → **0** |
| `PtfxList.EffectRuleDict` | `.EffectRuleDictionary` | `$null` |
| `AllEffects` | only `Load()` fills it, `GetYpt()` does not | 0 |

When PowerShell accesses a property that does not exist, it **gives no error, it returns `$null`**;
and `$null.Length` is `0`. So the measuring tool showed zero, I took that as the data
being zero and went the wrong way for hours, and even wrote "impossible" into the
document. (This is the general rule: **a tool not
showing something does not mean that thing does not exist.**)

Make it a reflex: when querying a foreign DLL, first write
`$obj.GetType().GetProperties() | % Name`, or use a guard —

```powershell
function P($o,$name){
  if(-not $o.PSObject.Properties[$name]){ throw "NO PROPERTY: $($o.GetType().Name).$name" }
  $o.$name }
```

### ⛔ The real cause of the silent crash: A KEYFRAME SLOT LEFT MISSING

The `NullReferenceException` inside `Save()`
(`ResourceBuilder.AssignPositions` → `ResourceSystemBlock.set_FilePosition`)
is almost always **a `KeyframeProperty` slot that was not written.**

Every behaviour type has a **fixed number of slots, and all of them must be written**.
An unwritten slot leaves a null block; the XML parses fine, the dictionaries read as
filled, the error comes one step later in `Save()` and **does not say which slot
it is.**

Measured in **15,430 behaviours** in `core.ypt` — every type shows ONE slot count,
no exceptions:

| KFP | Behaviour types |
|---:|---|
| 0 | `Age` · `Velocity` · `Sprite` · `DecalPool` · `Liquid` · `Model` · `River` |
| 1 | `MatrixWeight` · `AnimateTexture` · `Wind` · `Trail` · `Attractor` |
| 2 | `Acceleration` · `Dampening` · `Collision` · `ZCull` · `Decal` |
| 3 | `Colour` |
| 4 | `Size` · `Rotation` · `Noise` |
| 7 | `FogVolume` |
| 9 | `Light` |

The slot `<Name>`s are the real schema (1736/1736 fixed):

- `Size` → `m_whdMinKFP` · `m_whdMaxKFP` · `m_tblrScalarKFP` · `m_tblrVelScalarKFP`
- `Colour` → `m_rgbaMinKFP` · `m_rgbaMaxKFP` · `m_emissiveIntensityKFP`
- `Rotation` → `m_initialAngleMinKFP` · `m_initialAngleMaxKFP` · `m_angleMinKFP` · `m_angleMaxKFP`

`<Unknown6C>` on the other hand is **not fixed**: it is a position inside the file and grows by 256 per slot
(331 different values measured for Size KFP0). Start from whatever base you like.

**`Velocity` having 0 slots is not a mistake.** Particle velocity is defined
not in the behaviour but in the **emitter** rule's `speedScalar` and in the creation/target
domains. Trying to write keyframes into Velocity is the easiest way to crash `Save()`.

### ⛔ The other two required blocks

- **`EventEmitters/Item/UnknownData`** — its content may be empty, but it **must
  exist**: `<UnknownData><EventEmitterFlags /><Unknown10 /></UnknownData>`.
  Otherwise the same `Save()` crash.
- The **`Sprite`** behaviour takes 0 keyframes but requires all of the fields `Unknown30 34 38 40 44 48 4C
  50 54 58 5C 60` (`5C` = `0x100`).

### Production pipeline — which script does what

**Normal production is a single command**; do not run the intermediate steps by hand:

```powershell
scripts\ptfx_make.ps1 -Name my_spore -Color 0.2,0.9,0.35 -Target <stream folder>
scripts\ptfx_make.ps1 -Name my_x -Image own.png -Size 0.4 -Rise 0.8 -Target <folder>
```

Texture → XML → binary → fill in missing fields → verify → deploy.

| Script | Job |
|---|---|
| `ptfx_make.ps1` | **entry point** — the whole pipeline |
| `make_dds.py` | DDS with DXT5/DXT1 + mip chain (`--source` for a ready-made PNG) |
| `build_custom_ptfx.py` | effect/emitter/particle rule XML from scratch |
| `ypt_xml_to_bin.ps1` | XML→binary + **the fields CodeWalker skips** + verification + deployment |
| `ypt_transplant.py` | **diagnosis**: copies a working vanilla effect and changes a single variable |
| `make_test_sheet.py` | **diagnosis**: test sheet with differently shaped cells |
| `make_butterfly_sheet.py` | wing-flap sprite sheet (procedural, consistent frames) |
| `ptfx_preview.py` | animated preview from the data of a built `.ypt` (NOT engine output) |
| `build_ptfx.ps1` | indexes the vanilla effect catalogue (`assetdb.py ptfx/fx`) |

⛔ **Do not call** `XmlYpt.GetYpt` + `Save()` **by hand** — without `ypt_xml_to_bin.ps1`
the file comes out without shader and VFT, and silently breaks in game.

### ⛔⛔ The CodeWalker XML reader does NOT WRITE `VFT` either — the class id stays zero

The same class of error as `FxcFileHash`, but wider: in a `.ypt` produced from XML
**no block's `VFT` is written**; they all come out `0`. `VFT` is the
object's class id (vtable); if it is zero, the engine cannot resolve the block's type.

Measured — in `core.ypt` every type carries **a single** value, zero deviation:

| Block | Sample | VFT |
|---|---:|---|
| Texture | 107/107 | `1080137320` |
| EffectRule | 964/964 | `1080081688` |
| EmitterRule | 1993/1993 | `1080083608` |
| ParticleRule | 1736/1736 | `1080085192` |
| EventEmitter | 2543/2543 | `1080100952` |
| KeyframeProp | 4820/4820 | `1080085392` |
| EffectRuleDict / EmitterRuleDict / ParticleRuleDict | 1 | `1080048016` / `1080048056` / `1080048096` |

Behaviours, one value per type: `Age 1080067288 · Velocity 1080075080 ·
Size 1080074648 · Colour 1080070168 · Sprite 1080076760 · AnimateTexture
1080068072 · Acceleration 1080066920 · Rotation 1080073832 · Dampening
1080070840 · MatrixWeight 1080071352 · Noise 1080072136 · Wind 1080075768 ·
Model 1080077240 · Trail 1080078056 · Collision 1080069256 · Attractor
1080068456 · ZCull 1080175704 · Decal 1080170408 · DecalPool 1080170920 ·
FogVolume 1080172152 · Light 1080174040 · Liquid 1080174872 · River
1080175208`

Domains, one per shape: `Sphere 1080088936 · Box 1080088880 ·
Cylinder 1080088992 · Attractor 1080089048`

**`ShaderVars` entries have their own VFT too** — and this is the object that makes the texture link
(`Type=Texture`). It is easy to miss, because it is not in the behaviour list
but in a separate list:

| ShaderVar type | Sample | VFT |
|---|---:|---|
| `Texture` | 5108/5108 | `1080097544` |
| `Vector2` | 18846/18846 | `1080097368` |
| `Vector4` | 1686/1686 | `1080097368` |
| `Keyframe` | 10216/10216 | `1080097256` |

`Vector4` and `Vector2` share the same VFT.

`scripts/ypt_xml_to_bin.ps1` writes all of them and exits with **exit 1** if any stays zero.

### What MOVES the particle: the target domain's position

⛔ The `Velocity` behaviour has **0 keyframe slots** — velocity is not written
there. Rising smoke/spores are made **with the position of `Domain2` (target domain)**:
the particle is born in the creation domain and travels towards the target domain.

Measured: in **89.2%** of vanilla emitters the Z of
`ptxTargetDomain:m_positionKFP` is non-zero, **median +0.400**.
If both domains share the same centre, no net direction forms and the effect stays in place.

`m_speedScalarKFP` gives **speed**, not direction (vanilla median 0.85).

### ⛔ `m_zoomScalarKFP` drives the WHOLE spatial scale of the effect

Not just particle size; spread, distance and size, all at once.
Measured in game: when its value of 338 was emptied, the effect collapsed at every size, and
multiplying the `whd` keyframes **50×** did not compensate.

In vanilla the value scales with the size of the effect: a tiny sneeze
effect `0.75`, a giant gas column `1200`, **median 51.8**, 77.2% filled.
Emptying it is legitimate (22.8% are empty), but it shrinks the effect.

### ⛔ OPEN PROBLEM: in an EMBEDDED texture the sprite sheet is NOT SLICED

This is **not solved.** The measurements are here so that the next session does not search from scratch.

Table measured in game — all **the same particle rule**, the only variable is the texture:

| Test | Texture | Result |
|---|---|---|
| `vs2` | vanilla sheet, **by name** from `core.ypt` | **single cell** ✅ |
| `dict` | vanilla sheet by name + an embedded dictionary also in the file (unused) | **single cell** ✅ |
| `van` | **raw data of the same vanilla texture**, embedded in our file | four cells ❌ |
| `test3` | the DDS we produced, embedded | four cells ❌ |

Reading:

- The engine **really does slice** — since `ptfx_grass_blades` (not a sheet, a vanilla
  texture whose shape is beyond doubt) was drawn correctly, it is also proven that external texture resolution
  works; so `vs2`'s single cell is not a fallback texture.
- **Our DDS encoding is innocent** — `van` carries vanilla's raw data,
  and it fails too.
- **The presence of the embedded dictionary is innocent** — `dict` slices fine while
  the dictionary sits in the file.
- The defect appears when the rule is **bound to an embedded texture**.

Fixes that were tried and **ruled out** (all were real gaps and were fixed, but
they did not resolve the symptom): `FxcFileHash` · block `VFT`s · `FileVFT` ·
`ShaderVar` VFTs · `UsageFlags` · DXT1/DXT5 · mip depth.
The texture object is **field for field identical** to vanilla (`UsageData` included), and the texture
dictionary's hash table is consistent.

**The only concrete next direction:** instead of embedding the texture in our own `.ypt`,
add it to `core.ypt`'s texture dictionary and call it by name from the rule —
`vs2`/`dict` show that this works. This may be the reason why custom particle
mods in GTA edit existing `.ypt` files.

⚠ This limit **only affects sprite sheet animation**. A single-frame
custom texture, colour, size, lifetime, spawn rate, spread and rise work fine with an embedded
texture (verified in game).

### ⛔ `m_sizeScalarKFP` IS THE REAL SIZE LEVER — not `whd`

Measured in game: when the same effect's `whd` keyframes were multiplied **200×**,
the particle did not grow noticeably; only when `m_sizeScalarKFP`
was changed `0.4437 → 100` did it reach **giant size**.

So multiplying `whd` to make a particle bigger is wasted effort. The field's
mathematical scale is still not solved (the vanilla distribution with median 57.6
looks like a percentage, yet the donor produces a visible particle with 0.4437) —
but **which lever drives size** is now known by experiment.

### ⛔⛔ MOST IMPORTANT: CodeWalker does NOT WRITE `FxcFileHash` — a `.ypt` without shader

**This is a CodeWalker bug, not a defect of your XML.** **Every** `.ypt` produced from XML
comes out with a zero shader hash. Measured with an unmodified vanilla
file:

| | `FxcFileHash` |
|---|---|
| `cut_arena.ypt` binary read | `246470498` |
| **the same file**, from the XML round trip | **`0`** |

The `FxcFile` **text** looks right (`ptfx_sprite`), the hash is zero, and what the engine
looks at is the hash. The symptom is exactly this, and no other check
catches it:

- the file is valid, `Save()` does not crash
- the `YptFile.Load()` read-back round passes
- `RequestNamedPtfxAsset` succeeds
- `StartParticleFx*` returns a **non-zero handle**
- **nothing happens on screen**

The fix with JenkHash: `GenHash('ptfx_sprite') = 246470498` — identical to the vanilla binary
value. `FxcTechniqueHash` is `0` in vanilla too; **do not touch it**.

```powershell
foreach ($pr in $ypt.PtfxList.ParticleRuleDictionary.ParticleRules.data_items) {
    $pr.FxcFileHash = [CodeWalker.GameFiles.JenkHash]::GenHash([string]$pr.FxcFile)
}
```

Ready script: `scripts/ypt_xml_to_bin.ps1` — GetYpt → write hash → Save →
read back → **exit code 1** if `FxcFileHash` is zero. When producing a `.ypt`,
do not call `XmlYpt.GetYpt` + `Save()` by hand; use this script.

⚠ There may be other fields of the same class: **do not expect every field CodeWalker writes to XML
to come back with the same value when read back.** When producing a new resource
type, the first job is to export a vanilla file to XML, read it back,
and **compare the binary and the XML round trip field by field** — only that shows which
fields the tool drops.

### ⛔ DO NOT WRITE 0 INTO AN UNKNOWN FIELD

Saying "I don't know, I'll leave it 0" for `Unknown*` fields produces a silent failure.
Measured — for most of these values 0 **never occurs** in vanilla:

| EffectRule | Most frequent | Share |
|---|---|---|
| `Unknown50` | `0xFFFFFFFF` | 537/964 |
| `Unknown88` | `0x1010100` | 283/964 |
| `Unknown8C` | `0x10004` | 422/964 |
| `UnknownA4` | `50` | 144/964 |
| `UnknownA8` | `60` | 176/964 |
| `UnknownAC` | `10` | 176/964 |
| `UnknownB0` | `30` | 224/964 |

`UnknownA0/A4/A8/AC/B0` look like a distance/LOD band (0/50/60/10/30), and
if they are zeroed the effect may not be drawn at any distance.

| ParticleRule | Most frequent | Share |
|---|---|---|
| `Unknown10` | `2` | 1341/1736 |
| `Unknown100` | `2` | 1098/1736 |
| `Unknown108` | `2` | 1347/1736 |
| `Unknown10C` | `0x10100` | **1638/1736 (94%)** |
| `Unknown1D0` | `5` | 890/1736 |
| `Unknown1E8` | `0x101` | 1044/1736 |
| `Unknown220` | `0x2` | 736/1736 |

Rule: before writing a value into an `Unknown` field, **look at its distribution**
in `assetdb.py`/`core.ypt`; take the most frequent value.

### ⛔ The file is valid but NOTHING SHOWS IN GAME — three more causes

These three do not crash `Save()`, they pass the read-back round, and `StartParticleFx*`
returns a **non-zero handle** (so the engine found the effect), and still
nothing happens on screen. A filled handle does not mean "it works";
it only means **the name was found**.

**1. `FxcTechnique` is not free text, it is a closed list.**
In the 1,736 particle rules of `core.ypt` only six values occur:

| Technique | Count |
|---|---:|
| `RGBA_lit_soft` | 904 |
| `RGBA_lit` | 425 |
| `RGB_lit_soft` | 136 |
| `RGB_lit` | 75 |
| `RGB_soft` | 70 |
| `RGBA_soft` | 30 |

`default` **never occurs.** If it is written, the shader is not resolved and the effect silently
is not drawn. `RGBA` = texture with alpha, `_soft` = soft edge with depth fade.
`FxcFile` is only `ptfx_sprite` (1,686) or `ptfx_trail` (50).

**2. `m_sizeScalarKFP` is on a PERCENTAGE scale, not a fraction.**
Measured over 2,097 keyframes: `5% = 1.0` · **median 57.6** · `75% = 125` ·
`95% = 297` · max 1000. So writing `1.0` puts you in the bottom 5% —
~1% of the particle size, invisible to the eye. **100 = neutral.**

The same percentage scale also applies to `m_accnScalarKFP` (median 98.4), `m_dampeningScalarKFP`
(98.6) and `m_matrixWeightScalarKFP` (93.8).
**But not to all of them:** `m_speedScalarKFP` (median 0.85),
`m_particleLifeKFP` (1.40) and `m_playbackRateScalarKFP` (1.20) are on a ~1.0
scale. Do not assume the scale from the field name — **measure**.

**3. An empty keyframe slot ZEROES the multiplier.**
It is not enough for the slot to exist; some of them also have to be filled. Which ones
can be left empty is measured:

| Slot | Empty in vanilla | Can it be left empty |
|---|---:|---|
| `Size:m_tblrScalarKFP` | 0.5% | ⛔ **NO** — empty = multiplier 0 = zero size |
| `Size:m_whdMin/MaxKFP` | 0.7% / 0.8% | ⛔ no |
| `Colour:m_rgbaMin/MaxKFP` | 0.1% / 0.2% | ⛔ no |
| `Size:m_tblrVelScalarKFP` | 83.6% | ✅ yes |
| `Colour:m_emissiveIntensityKFP` | 71.7% | ✅ yes |
| `Emitter:m_matrixWeightScalarKFP` | 99.1% | ✅ yes |
| `Emitter:m_dampeningScalarKFP` | 95.8% | ✅ yes |
| `Emitter:m_particleLifeKFP` | 0.6% | ⛔ no |
| `Emitter:m_spawnRateOverTimeKFP` | 3.6% | ⛔ no |

Rule: **a slot that is empty in less than 5% of vanilla is required.**

`CullRadius` / `CullDistance` being `0` is normal (869/964 and 836/964) —
do not look there. `Unknown74` is **964/964 `0.25`**; it is fixed.

### Diagnosis method: NARROW DOWN BY SPLITTING, do not walk the block tree

Searching for null in the `GetReferences()`/`GetParts()` tree **does not help** —
`ResourcePointerArray64<T>` throws `NotImplementedException` in foreach
and the walk silently gives a wrong result.

The method that works: export a vanilla `.ypt` to XML (this XML passes the `Save()` round),
then replace blocks with your own **one at a time** and see which one
crashes. 4 tests at dictionary level, then 4 tests at section level — the defect is found
in eight runs.

### A SMALL saved file size is not an error

The `Save()` output is RSC7 and **zlib compressed**. `cut_arena.ypt`
32,768 bytes unpacked → `Save()` **3,077 bytes**. Earlier I looked at this difference and
concluded "the file is broken"; the criterion is not size, it is **read back**:

```powershell
$d=[IO.File]::ReadAllBytes($path)
$e=[CodeWalker.GameFiles.RpfFile]::CreateResourceFileEntry([ref]$d,0)
$d=[CodeWalker.GameFiles.ResourceBuilder]::Decompress($d)
$y=New-Object CodeWalker.GameFiles.YptFile; $y.Load($d,$e)
```

`YptFile.Load()` **needs an `RpfFileEntry`**; if `null` is passed it blows up, and that too
is mistaken for "the file is broken".

On read back `Behaviours` **shows 0 — this is not a loss.** Binary loading
fills `BehaviourList1..5`; `Behaviours` is the XML side's collector.
Vanilla `cut_arena` reads the same way.

### Schema: the texture link

⛔ **The texture link is NOT inside `<Behaviours>`, it is inside `<ShaderVars>`.**
Measured: `Behaviours` only carries these types — `Age Acceleration Velocity
Rotation Size Dampening MatrixWeight Wind Colour Sprite` (+ table above).
`Texture` **never occurs** there.

⛔ In a `Texture` entry `<Name>` **is not the texture name, it is the SAMPLER SLOT**
(`refractionmap` / `normalspecmap` / `diffusetex2`); the real texture name is in a separate
`<TextureName>` field. If they are written the other way round, the XML parses, **no error appears,
and the texture is not bound**:

```xml
<ShaderVars>
  <Item>
    <Type value="Texture" />
    <Name>diffusetex2</Name>       <!-- SAMPLER SLOT -->
    <Unknown18 value="4" />
    <Unknown3C value="0" />
    <TextureName>my_ptfx_soft</TextureName>   <!-- REAL texture name -->
  </Item>
</ShaderVars>
```

A `TextureDictionary` entry **requires** these:
`Name` · `Unk32` · `Usage` (**`DIFFUSE`**, not `DEFAULT`) · `UsageFlags` ·
`ExtraFlags` · **`Width`** · **`Height`** · **`MipLevels`** · **`Format`** ·
`FileName`. If they are missing, the texture silently stays empty.

⚠ DDS files must be **in the same folder as the XML**; otherwise it crashes with
`Texture file not found`. (This is the real reason behind the video's "create a folder with
the same name" warning.)

### Particle SPRITE SHEET animation — `AnimateTexture`

Particles that **change frame by frame**, such as a wing-flapping insect, a flame or splashing water,
are made not with mesh animation but by playing frames laid out on a single texture
via UV. In vanilla 781 particle rules use this.

**`UnknownC4` = frame count − 1** (the index of the last frame). Verified not by inference
but by **extracting two independent vanilla textures and counting by eye**:

| Texture | Size | Grid | Frames | `C4` |
|---|---|---|---:|---:|
| `ptfx_smoke_billow_anim_rgba` | 1024×1024 | 6×6 | 36 | **35** |
| `ptfx_water_splashes_sheet` | 512×512 | 2×2 | 4 | **3** |

The grid is **square**: columns = rows = √(frame count). Frames go left to right,
top to bottom. `UnknownCC` = `0x1000100` (the value of 6×6 sheets),
`C0` = 0, `C8` = 0. If `m_animRateKFP` is left empty, the engine plays at the default
speed.

Both are **a grey mask on a black background** — the colour comes from the engine.

⚠ The frame count must be consistent with the texture; `build_custom_ptfx.py --sheet N`
checks whether it is a perfect square and whether the texture divides exactly into the grid.

### A particle can be a 3D MODEL — the `Model` behaviour

A particle does not have to be a sprite. 133 particle rules draw a solid
mesh; the model is embedded in the `.ypt`'s own `DrawableDictionary`
(**46 models** in `core.ypt`: bullet casing, snowflake, leaf, glass shard).
The link is made **by name** in the `<Drawables>` block inside the rule:

```xml
<Type value="Model" />
<Drawables>
  <Name>ptfx_model_pistol_casing/ptfx_model_pistol_casing</Name>
</Drawables>
```

**Its limit:** a model particle is rigid — it is positioned, rotates and scales, but
**does not play skeletal animation.** For shape-changing things such as wing flapping or
flame flicker, the `AnimateTexture` path is used.

### FiveM custom `.ypt` streaming — VERIFIED

Measured in game: a custom `.ypt` placed in `stream/` registers as a named ptfx
asset under its file name.

```
[ptasset] my_spore   loaded=1
[ptplay]  handle=29442   alive after 0.6 s = 1
```

A `data_file` line is **not needed**. The texture is embedded in the `.ypt`; there is no separate `.ytd`.

⛔ But the texture **must be DXT**: the first version was `A8R8G8B8` (single mip), and the client
dropped the whole resource — not even the Lua loaded. Measurement:
all 107 particle textures in `core.ypt` are DXT (DXT5 75 · DXT1 32),
mip 4-9; no uncompressed sample.

⛔ **A broken stream asset drops the WHOLE resource, and it is silent.**
The server writes `Started resource X`; no command registers on the client,
no print appears, and there is no error in F8 either. Lua never gets its turn.
Diagnosis: set up a second resource **without** a `stream/` folder — if its command
works, the defect is in the stream asset.

⛔ After adding or removing a stream file, **`restart` that resource**.
The server scans the file list when the resource starts; if it is not restarted, the client
is promised a file that no longer exists and the mount drops again. (This
happened exactly: the file was deleted, the resource was not restarted, the symptom did not change.)

### In-game use — two separate names

**ASSET name = `.ypt` FILE name** (`RequestNamedPtfxAsset`),
**EFFECT name = the `EffectRule`'s `<Name>`** (`StartParticleFx*`).
They do not have to be the same, and usually they are not.

For a `.ypt` a `data_file` line is **not needed** — the file in `stream/`
registers by itself as a named ptfx asset under its file name.

⛔ `UseParticleFxAssetNextCall` is repeated before **every** `Start` call;
as the name says, it applies only to the next call. Calling it once and
entering a loop silently falls back to the vanilla asset.



---

## 6. Verification — read back is mandatory

### ⛔ Walking `ResourcePointerArray64` with `foreach` (happened again)
An audit using `foreach($rule in $pr)` reported **15/15 "AnimateTexture MISSING"**;
when the same file's behaviour list was read with an index loop,
`AnimateTexture` was there. When `$ErrorActionPreference='SilentlyContinue'`
swallows the error, the result silently comes out wrong. **Use an index loop.**

### Structural gate (for every `.ypt`)
- does every particle rule have `ParticleBehaviourAnimateTexture`
- `Unknown_C4h` == frames − 1
- `EffectRules` ≥ 1, `Textures` ≥ 1
- texture 1024×1024 · `D3DFMT_DXT5` · mip ≥ 5
- **`FxcFileHash` ≠ 0** (the CodeWalker XML reader does not write it;
  `ypt_xml_to_bin.ps1` fixes it)

### Content gate — DECODE the embedded texture BACK
`Texture.Data.FullData` is taken, a 128-byte DDS header is prepended,
it is opened with Pillow and **compared with the source PNG**. DXT5 loss is normal:
measured **PSNR 36–43 dB**. The embedded size is exactly **128 bytes**
smaller than the source `.dds` (the header).

DDS header (DXT5, with mip chain):
`flags = CAPS|HEIGHT|WIDTH|PIXELFORMAT|MIPMAP|LINEARSIZE`,
`pitch = ceil(w/4)*16`, `pf.flags = DDPF_FOURCC`, `fourcc = "DXT5"`,
`caps = TEXTURE|COMPLEX|MIPMAP`.

### ⛔ A particle composited on a white background MISLEADS
Because alpha is low, every effect looks pale and a wrong diagnosis of "faint"
is made. In game a particle is drawn over a dark/mid-toned world
→ composite the preview **on a dark background**.

### ⛔ "Read back passed" DOES NOT MEAN THE ENGINE ACCEPTED IT

This round's most expensive lesson. 15/15 files passed every structural gate — behaviour
present, `C4` written correctly, texture embedded, hash non-zero — and in game
**none of them worked**. Read back verifies that the file *was written*;
the only thing that verifies the engine *uses* it is the game. When writing a value outside the vanilla
band into a field, do not count the sentence "read back verified it" as
proof — **look at the distribution, stay inside the band.**

### ⛔ A screenshot is not a measurement (again)
Looking at the contact sheet I said `fire` "drifts left and spills out of the frame";
when the per-frame centre of mass was measured it came out **cx 0.49–0.54 constant** — there was
no drift. But the same measurement found the **real** defect the eye had caught:
touching the edge. Neither the number nor the screen is enough alone; both are needed.

---

## 13. ⛔ MOTION IS NOT INHERITED, IT IS WRITTEN — this pipeline's most expensive mistake

Transplanting from a donor and changing **the colour and the texture** does not make the effect
ours. What the eye reads is **motion**; if the motion is inherited, what shows
in game is the donor itself, in a new colour.

Three cases seen in game, with the diagnosis verified from the file:

| family | donor | cause in the file | seen in game |
|---|---|---|---|
| `collapse_dust` | `env_dust_devil_rural_lrg` | `ptxAttractorDomain` outer 20.6 / inner 6.8 | **tornado** |
| `infection_wave` | `fire_extinguish` | `ptxTargetDomain` 3.5 m up (jet) | spurts a ring |
| `concrete_break` | `ent_ray_fam3_dust_motes` | spawn volume **5×5×1 m box** | splinters scatter over a 5 m area |

All three had been chosen because "the donor name and the numbers looked suitable"; I had
never measured the motion.

### Measured field meanings

| field | meaning | example |
|---|---|---|
| `ptxCreationDomain:m_sizeOuterKFP` | the **volume the particle is born in** (m) | drop 1×0.05 flat · dust 5×5×1 |
| `ptxTargetDomain:m_positionKFP` | **direction × distance** = velocity | drop `[0,0,-4]` · ember `[0,0,0.1]` |
| `ptxu_Acceleration:m_xyzMin/MaxKFP` | gravity / rise | drop `[0,0,-20]` · ground fog `[0,0,0]` |
| `ptxu_Dampening` | friction | fog 0.9 · glass 0.05 |
| `<DomainN><Type>` | Box · Sphere · Cylinder · Attractor | **Domain1 = CreationDomain** |

Distribution (n=231 suitable donors): `CreationDomain` and `TargetDomain` **100%**,
`Attractor` only **6%** (14) — the spiral/tornado risk comes from there.
Behaviour units: `Acceleration` 77% · `Dampening` 77% · `Rotation` 62% ·
carrying all three **115 / 231**.

Tool: `ptfx_motion.py` (`apply_to_document`). The attractor is **not deleted; its radius is
zeroed** — the `<DomainN>` slots are positional, and removing a node shifts the indices
of the rest.

### ⛔ Motion that cannot be written is an ERROR, not a WARNING

If the donor's particle rule does not have that behaviour unit, the field is silently not written,
and the effect **keeps the donor's motion** — the very defect we wanted to
fix. `ent_amb_fbi_falling_debris` has neither `Acceleration` nor `Dampening`;
gravity could not be written for "falling debris". The generator now counts this as an
error, so the donor was replaced with `ent_amb_falling_cherry_bloss`
(it carries all three units, and it is already something that falls gliding).

If a field really is unnecessary, **remove the key** — instead of asking for something
it does not carry. `ent_amb_dust_motes` has no `Acceleration`, but for spores
acceleration is not critical; the target `(0,0,0.15)` already gives the slow rise.

### ⛔ DO NOT WRITE `<Name>X</Name>(.*?)</Keyframes>` — an empty field reads its neighbour

If the field is empty, the XML has `<Keyframes />` (self-closing); the `</Keyframes>`
pattern **is not there**, and the regex captures the body of the NEXT field.
Measured: `ptxTargetDomain:m_positionKFP` of `ent_amb_fbi_smoke_land_hvy`
is empty; the read slipped into `m_rotationKFP` and gave **[90, −30, 0]** as the position —
degrees, not a position. A silent and completely convincing misreading.

The right way (`kfp_body`): first cut the field's **own boundary** (up to the next
`<Name>`), then search for `<Keyframes>` inside it. After this bug was found
the alpha/load statistics were re-measured and **did not change**
(88.2% / 44.6% / 9.3%; band 1 / 18 / 230) — because those fields are rarely empty.
But **all** of the domain measurements were wrong.

### Honest limit: these are not "fully custom"

Ours: **texture, colour, spawn rate, lifetime, alpha envelope, and now motion**
(spawn volume, direction, speed, acceleration, friction, attractor).
From vanilla: the rule skeleton and the fields we do not touch
(`Rotation`, `MatrixWeight`, `ZCull`, shader technique, LOD behaviour).
Vanilla effects **are not modified** (not a replace); these are separate
assets. But they are not written from scratch either — the skeleton is inherited.


## 8. Small pitfalls

- ⛔ A `%` in `argparse` help text must be escaped (`%%`), otherwise when `--help`
  runs it blows up with `TypeError` and the cause is not visible.

---

## The texture sheet (flipbook) is a separate job

Frame count, `C4`, grid, density, transplant and donor choice → `sprite-sheets.md`.
