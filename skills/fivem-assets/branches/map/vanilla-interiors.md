# Vanilla interior measurements — chamfer, budget, shader inventory, shadow/dirt mesh

**When to read:** building your own MLO/interior at vanilla quality or measuring a vanilla interior: how many mm the corner chamfer is, the polygon budget, scale, which shaders, vertex color, where the shadow comes from and how Rockstar handles it.
**Source:** former vanilla interior measurement notes (2.5.0, in full, 2026-08) · **Measured:** v_coroner + v_abattoir field by field
**Read first:** `branches/map/_branch.md` · trunk › `trunk/flags.md`, `trunk/tool-pitfalls.md`

---


Source: `Interior_References.7z` / `_V2.7z` (39 vanilla interiors, imported into
Blender with Sollumz). The two measured: **`v_coroner`** (windowless basement morgue)
and **`v_abattoir`** (slaughterhouse with daylight).
Method: Blender 5.2, `--background`, two passes. Vertex color read with **`.color_srgb`**
(on BYTE_COLOR, `.color` decodes gamma and silently darkens the mask).

⚠ These two files are 2013 launch interiors; later DLCs may differ.

---

## 1. BUDGET

| | `v_coroner` | `v_abattoir` |
|---|---|---|
| objects / meshes | 5,413 / 3,952 | 3,232 / 2,352 |
| **lights** | **249** | **120** |
| materials / textures | 1,667 / 755 | 1,094 / 471 |
| **triangles** | **613,730** | **548,147** |

Comparison: a modern MLO for sale has **537 objects / 183,574 triangles**. R\*'s morgue
has **3.3 times its triangles, 10 times its objects**.

**Rule:** do not squeeze polygons needlessly — but R\* gets the atmosphere **from 249 lights**,
not from polygons.

---

## 2. CHAMFER / BEVEL — corner softening measurement

Method: a GTA drawable comes in **triangulated** → first
`bmesh.ops.dissolve_limit(angle_limit=radians(2), delimit={'NORMAL'})`, then
a search for thin strip n-gons (min edge < 20 cm · max/min > 2.5 · >12° on ≥2 edges).

| | chamfer strips | hard 90° | ratio | **median** | p25 | p75 |
|---|---|---|---|---|---|---|
| **coroner shell** | 2,769 | 250 | **11.1 : 1** | **17.2 mm** | 11.1 | 23.9 |
| coroner props | 18,298 | 2,143 | 8.5 : 1 | 9.3 mm | 5.9 | 19.0 |
| abattoir shell | 3,695 | 1,835 | 2.0 : 1 | 23.3 mm | 15.6 | 32.5 |
| abattoir props | 24,727 | 7,021 | 3.5 : 1 | 20.2 mm | 12.0 | 41.2 |

**Rule: chamfer architectural corners by ~1.5–2 cm.** Not 1 mm, not 10 cm.
Finer on props (~9 mm). R\* leaves almost no corner sharp.

⚠ **Limit of the measurement:** the definition "thin strip between two angled faces" **also matches
cylinder tessellation** (pipe, pole, railing). The distinguishing indicator is
the **median turn angle**: coroner shell **60.1°** (a real corner chamfer, two ~30°
steps), abattoir shell **119.7°** (cylinders → that row is inflated).
The row to trust is **coroner shell**.

---

## 3. SHADER INVENTORY (by triangle)

**v_coroner:** `default` 139,983 · `default_spec` 118,042 · `normal_spec` 83,789 ·
`spec` 72,061 · `normal` 54,521 · `normal_spec_reflect_alpha` 22,296 ·
`normal_spec_detail` 16,786 · `glass_env` 8,360 · `emissive` 7,196

**v_abattoir:** `spec` 184,864 · `normal_spec` 114,816 · `default` 56,718 ·
`default_spec` 29,608 · `normal_spec_tnt` 20,768 · `cutout` 9,276 ·
`emissivenight` 3,114

⛔ **Neither interior has a single `*_pxm` shader.** The 4-layer terrain shader
is not near the top either. R\* builds these interiors with **the plainest shaders**.

→ **The `normal_pxm` trick is a modern modder technique, not an R\* signature.**
R\* gets depth from **geometry + texture + vertex color + light**.
(The parallax family is mostly exterior/terrain and later DLCs — see
`branches/look/parallax.md` §4.)

---

## 4. VERTEX COLOR — the "green at the bottom / blue at the top" claim is PARTLY WRONG

`Color 1` (= GTA `Colour0`), read by splitting the shell object into 4 bands along Z.

### v_coroner — windowless basement

| object | bottom | → | → | top |
|---|---|---|---|---|
| `v_2_bsnt_shell` | R.047 G.307 **B1.000** | G.157 B1.000 | G.111 B1.000 | G.197 B1.000 |
| `v_2_strs_shell` | R.000 G.103 **B1.000** | G.142 B1.000 | G.178 B1.000 | R.075 G.165 B1.000 |
| `v_2_tpoff_shell` | R.103 G.260 **B1.000** | G.224 B1.000 | G.287 B1.000 | G.344 B1.000 |

**The blue channel is fixed at 1.000 from top to bottom.** Red is low and nearly constant.
The only channel that changes is green, and its change is **not even monotonic** with height.
→ The "green at the bottom / blue at the top" recipe **does not come out** here.

### v_abattoir — with daylight

`v_11_abattoirshell`: green **0.225** at the base → **0.101** at the ceiling; red and
blue increase with height. → The direction is right, **not literally**.

**Rule:** these channels are not a paint palette, they are **an ambient light gate**
(natural / artificial ambient gate). Derive the value not from memory but **from the space's
lighting situation**: in a windowless space the natural layer is closed.

**Layer inventory:** only **`Color 1`** exists (coroner 922 meshes, abattoir 479).
**There is no `Color 2` at all.** Besides it, only the `TintColor (…_pal.dds)` layers
of tint props.

---

## 5. STRUCTURAL PATTERNS — copyable

### 5.1 Shadow is separate geometry

`v_2_shadowmap1/2/3.model` — **same bbox** as the shell, lower polygon count
(1,208–1,468 vs shell 1,979–4,165), vertex color **fully black (0,0,0)**.
abattoir equivalents: `v_11_abattoirshadprox` (168 poly), `v_11_abbcorrishad`,
`v_11_abbmnrmshad1`.

→ Interior shadow comes not from lights but **from a separate low-poly mesh**.
Consider this pattern before adding more lights.

### 5.2 Dirt and blood are separate overlay meshes

`v_11_abbnardirt`, `v_11_ab_dirty` (554 poly) and **`v_11_coolblood001`
(15.8 × 87 × 7.1 m)**. Not baked into the texture; placed on top of the shell as a **separate thin mesh**.
The coroner equivalent: `v_2_tpo_over_normal` ("over" = overlay).

### 5.3 The shell is split

coroner has no single giant shell, but **a separate shell per room group**:
`v_2_bsnt_shell` (42.8 × 54.0 × 4.2 m) · `v_2_strs_shell` (29.5 × 27.9 × 21.4) ·
`v_2_tpoff_shell` (35.6 × 19.7 × 4.3).

---

## 6. DIRECTLY APPLICABLE TAKEAWAYS

1. Chamfer corners by **~1.5–2 cm** (§2).
2. **Split the shell by room group**, do not make it one piece (§5.3).
3. For shadow, consider **a separate low-poly mesh** instead of more lights (§5.1).
4. Dirt/blood/stains as **separate overlay meshes**, not baked into the texture (§5.2).
5. Write vertex color **by the space's lighting situation**, not from a memorised palette (§4).
6. Parallax indoors is not an R\* pattern — take depth from geometry and light (§3).

---

## 7. MEASUREMENT SCRIPTS

Produced in the session scratchpad, not under `scripts/`; if they are to be moved:

- inventory + shader inventory + vertex color Z profile + light dump
- chamfer strip measurement after `dissolve_limit`, shell/prop split

**Not measured, open:** `v_genbank`, `v_hospital`, `v_janitor`, `v_fib01`,
`v_policehub` and 34 more interiors.
