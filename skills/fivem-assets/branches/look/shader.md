# Shader choice — program + render bucket, texture samplers, "no texture"

**When to read:** which `.sps` (shader program and render bucket); why alpha/cutout does not work; `RenderBucket`; the shader name in a ydr; texture samplers; converting PBR maps to GTA; "this surface has no texture" / "the texture is there but nothing shows".
**Source:** `sources/external-tools.md` §2 shader section (Sollumz 2.9 measurement) · `lights.md` 'no texture' · `bake_to_gta.py` docstring (249 shaders, 1135 textures) · `sources/external-tools.md` §1e · **Measured:** 249-shader table (`shaders.tsv`), 24,000-model usage count, 400+ vanilla `.ytd`
**Read first:** `_branch.md` · trunk › `trunk/tool-pitfalls.md` §1-2

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" shader <kind>     # glass/emissive/terrain/cloth/vehicle/water/decal/pxm — textures + parameters
```

## Shader choice has two axes: program **and** render bucket

⛔ **Choosing a `.sps` does not choose a shader; it chooses two things at once:** the GTA shader
**program** and the **render bucket**. They are separate fields in Sollumz, and the bucket is
**writable** — you are not stuck with the bucket the `.sps` preset brings.

Measured (Sollumz 2.9.0):

| `.sps` | program | bucket | emissive |
|---|---|---|---|
| `cutout.sps` | `default` | CUTOUT | no |
| `emissive_alpha.sps` | `emissive` | ALPHA | yes |
| `emissive_clip.sps` | `emissive_clip` | **OPAQUE** | yes |

**The opaque bucket never reads alpha.** Choosing a `.sps` with "clip"/"alpha" in its name
does not guarantee that alpha will work: when a prop with holes was built with
`emissive_clip.sps`, **all the holes closed** in game — a solid box was drawn even though
the texture was transparent.

Bucket values: `OPAQUE / ALPHA / DECAL / CUTOUT / NO_SPLASH / NO_WATER /
WATER / DISPLACEMENT_ALPHA`. When alpha + emissive are wanted together, leave the program
emissive and set the bucket to `CUTOUT` by hand:

```python
m = create_shader("emissive_clip.sps")
m.shader_properties.renderbucket = "CUTOUT"   # writes RenderBucket 3 to the ydr
```

⚠️ **The name written to the ydr is the PROGRAM name, NOT the `.sps` FILE NAME.**
`emissive_alpha.sps` shows up in the ydr as `emissive`. Expecting the hash of
`emissive_alpha` and saying "the wrong shader was written" is a misdiagnosis.
When verifying, compare against `JenkHash.GenHash(<program name>)`.

**Measure both sides:** `shader_properties.name` (program),
`shader_properties.renderbucket` (bucket). Then read back from the ydr and verify with
`Shaders.data_items[i].Name` and `.RenderBucket`.


---

## PBR → GTA: which map goes where (measured)

GTA is not PBR: across 249 shaders there are **0** roughness/gloss/metallic/AO samplers; what exists is `SpecSampler` (130). Roughness goes inverted into **spec**, AO **into the diffuse**, metallic into shader **scalars**. Pipeline: `scripts/bake_to_gta.py`.


## "This surface has no texture" ≠ texture missing

Measured: the JS lid's texture (`my_js_door_d`) **was there and was correct** —
256×256, a real morgue drawer atlas (lid surface + lock/handle).
The door's UV also sampled the right region. The defect **was in the contrast**:

| | mean | std |
|---|---|---|
| door column (before) | **181** | **5.0** |
| floor (comparison) | 55–101 | — |
| door column (after) | 93 | 13.2 |

A mean of 181 and std 5 = a bright white, flat panel next to the floor. The user
reads this as **"no texture"**. Darkening + raising the contrast is enough; there is no need
to look for a new texture.

⛔ **Order matters: contrast FIRST, scaling SECOND.** In the reverse order the scaling
also divides the std, so the contrast gain is lost — measured: std 5.0 → 5.8,
i.e. nothing changed. In the right order 5.0 → 20.1 (13.2 after DXT1).

---
