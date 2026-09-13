# Ped prop — hat, glasses, headset (`p_head`, `p_eyes`, `p_ears`)

**When to read:** you are adding a prop worn by a ped (hat, glasses, headset — `p_head`, `p_eyes`, `p_ears`); positioning it (`IK_Head`), texture naming, `Render Flags`, `propsName`, Creature Metadata; adding one to a non-streamed ped.
**Source:** `notes/03` §8-9 · `sources/external-tools.md` §2 §4 (2026-08) · **Measured:** video
**Read first:** `branches/clothing/_branch.md` · trunk › `trunk/tool-pitfalls.md` §1

---

## 8. Positioning `p_eyes` / `p_ears` (`jzFT3uryGuI`)

Full recipe, the same for both props:
1. Import any component from the ped — **only as a skeleton reference**.
2. Skeleton → Edit Mode → **X-Ray** → select the **rear sphere** of the **`IK_Head`** bone
   that runs through the middle of the head. (Blender sometimes calls it "facial root"; that does not matter.)
3. `Shift+S` → **Cursor to Selected**.
4. Object Mode → select the prop mesh → right click → Set Origin → **Origin to 3D Cursor**.
5. In Object Properties, **Location X/Y/Z = 0, 0, 0**.
6. Rotate **180° on the Z axis**, then **90° on the Y axis**.
7. `Ctrl+A` → Apply All Transforms (habit; makes debugging easier).

Because this works relative to the `SCALE_Head` bone, it holds **on every ped**.

## 9. Adding ped props (`p_head` / `p_eyes`) to a non-streamed ped (`Jm3Ps157z3s`)

- Prop texture naming is **DIFFERENT from components**: no suffix, only the letter →
  `..._a`, `..._b`, `..._c` inside `<ped>_p.ytd`.
- In practice props carry **only HIGH LOD**; no medium/low to worry about.
- Give a prop without a normal map an **8×8 blank normal**.
- YMT Editor → activate the matching category (`p_head`, `p_eyes`), add the A/B textures.
- ⛔ **`Render Flags` (prop properties) MUST MATCH the shader in Blender.**
  If you use `ped_alpha` / `ped_decal` / `ped_cutout`, pick the counterpart in the YMT.
  **Unimportant on MP freemode, effectively required on ALL other peds** — skipping it on things
  like a glass visor or glasses lenses leads to a silent failure.
- The **`MH_hair_scale`** bone is mostly **freemode-specific**; most Rockstar
  peds do not have it. The hair shrinking when a hat is worn happens through this bone.
- ⚠️ **Creature Metadata is only needed if something on the ped IS SCALED** —
  heel height (feet) or hair scaling (p_head). If neither, do not touch it.
  If it is needed: YMT Editor → **File → Generate Creature Metadata**.
- FiveM `peds.meta`: write the name of the prop `.ydd` in the **`propsName`** line —
  it is the only thing that activates the props.
- Final file set: `.ydd` · `.yft` · `.ymt` · `.ytd` · `_p.ydd` · `_p.ytd`


## Community warning (Sollumz Discord)

- ⛔ **On a ped prop, `Render Flags` must match the Blender shader**
  (`ped_alpha`/`ped_decal`/`ped_cutout`). Unimportant on MP freemode,
  **effectively required on all other peds**.
