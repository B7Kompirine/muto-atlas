# Grass / procedural ground / terrain

**When to read:** "let's make grass" — which system; your own terrain; `@ma` procedural collision; grass batch; fur grass; "grass does not show"; terrain material and the procedural IDs that spawn it.
**Source:** former video notes 08 §1-7 (Stumpy Mason videos, [video]) · SKILL proc/mat queries · **Measured:** video steps; the data side `procedural.tsv` (255) and `collision_materials.tsv` (185) measured
**Read first:** `branches/map/_branch.md` · trunk › `trunk/flags.md`, `trunk/tool-pitfalls.md`

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" proc [<name>|--id N]   # procedural table (collision 'Procedural ID')
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" mat  [<name>|--index N] # collision material + flags
```

⚠️ The steps below are **a video walkthrough** (one author, shown working); verify the numbers with `assetdb.py`.

## 1. Grass in GTA is FOUR separate systems

When a "let's make grass" request comes in, **ask which one** — all four
are built completely differently:

| system | what | how |
|---|---|---|
| **flat texture** | the ground's own texture | `terrain_cb_*` shader + vertex color blend |
| **grass models** | grass placed as props | ymap entity |
| **fur grass** | fur-like volumetric grass | separate drawable with `grass_fur` / `grass_fur_mask` shader |
| **`@ma` procedural** | weeds/bushes the engine scatters by itself | through the **collision material** |
| **ymap grass batch** | instances painted with a brush | inside a ymap in CodeWalker |

### ⛔ Fur grass is INVISIBLE in CodeWalker
When you open drawables starting with `fur_` you **see no geometry at all** —
not even in wireframe. Only the material shows. This is not a defect, it is normal.
(trunk: a tool not showing it ≠ it does not exist.)

---

## 2. Anatomy of a vanilla terrain model (decoded)

When a vanilla ground tile is opened:
- **Three UV maps** — one per texture layer
- **Two color attributes:**
  - **`Colour 1`** = lighting zones. In the measured sample:
    **blue** = ground under a bridge / lit by moonlight · **pink** = the rest ·
    **red** = hilltops that see the sun
  - **`Colour 2`** = **which texture layer shows where**
    (e.g. green area → sandy soil)

So the layer blend is in `Colour 2`, lighting in `Colour 1`.


---

## 3. Building your own terrain — measured steps

1. **Circle** (72 vertices, ~25 m) → Edit Mode → select the face → **Grid Fill**
   → triangulate with `Ctrl+T`.
2. **Proportional Editing on, falloff `Random`** → move only in Z →
   natural hills/hollows.
3. Flatten the outer ring: in edge select, double-click the outer ring →
   **`S Z 0`** → snap to the reference plane you placed at 0, then delete the plane.
4. **Sculpt Mode → Smooth** brush, **low strength** — take off sharp corners.
   (The author left strength high and ruined it, then lowered it.)
5. Shader: the **`terrain_cb_4lyr_pxm`** family (type `4lyr` in the search box).
6. UV: select all → unwrap → **Cube Projection**,
   ⭐ **cube size = 2** — *"texture density for grass is two."*
7. `Colour 1`: **magenta** everywhere (R=1, G=0, B=1). Leave no white spots.

### ⭐ Sollumz Vertex Painter — `Shift+T`
Opens the `Shift+T` panel in the viewport. It has:
- **RGBA channel isolation**
- palette
- **multi-object vertex paint**
- ⭐ **Terrain Paint** — the `texture 1/2/3/4` buttons paint the layer blend
  straight into `Colour 2`

Brush size on right click, strength is adjustable. Switch between layers to
break up the "tiled" look. **The denser the geometry, the better the control.**

⚠️ The **camera icon** next to a color attribute = **"set render color"**:
it picks which layer you **paint**; the eye next to it picks which layer you **see**.
They are separate — mix them up and you paint the wrong layer.

---

## 4. Terrain collision

- Duplicate the drawable → name it `.col` → convert to **Composite**
- Collision materials: **grass (short)**, **gravel small**
- Edit Mode → view from the top → **circle select**, face mode → select the faces where
  soil shows → assign **gravel** → invert with **`Ctrl+I`** → assign **grass**
- ⭐ **DELETE the texture, UV maps and color attributes from the collision** — not needed.
- Result in game: **footprints** in the soil, **grass footstep sounds** on the grass.

---

## 5. Building fur grass

1. Select a part of the terrain mesh → `Shift+D` → `P` → **Separate by Selection**
   → `Alt+P` → **Clear Parent, Keep Transform** (so it stays in place).
2. Delete the UV maps and the texture.
3. Shader: **`grass_fur_mask`** (the `SM_26` variant in the example — this one has the mask).
4. Cube projection, again **texture density 2**.
5. In `UVMap 1`, move the islands **inside the small islands of the mask**.
6. Edit Mode → raise everything **+0.01 in Z**.
7. Add **Subdivision Surface** and **apply it right away**.
8. In vertex select, pull some vertices outward to add irregularity.

In game: layered dot arrays (stipple + height samplers) → looks
**more volumetric** than normal grass, alpha based. Suits places like a front lawn.
The edge needs a grass→soil transition, otherwise it looks cut off.

---

## 6. ymap **Grass Batch** — procedural scatter with a brush

CodeWalker Project → new ymap → **YMAP → New Grass Batch**.

Fields: **LOD distance · fade distance · orient to terrain · optimize batch ·
name** (e.g. `proc_grasses01`).

**Brush** tab: radius · density · **color (RGB wheel)** · ambient occlusion ·
scale (can be **random**) · padding · brush mode.

- **Hold `Ctrl` + left-click drag** = paints instances
- radius = circle size · density = how many inside the circle
- ⭐ **color = the color in game** — paint red and it comes out red in game
- **Optimize Batch** splits a large number of instances into small groups
- Model names are found in **Pleb Masters: Forge** with the `procedural` filter
  (e.g. `prop_brittle_bush_01`); all procedural models are in **`v_proc1.rpf`**
- Save + **generate manifest**

### ⛔ Grass batch does NOT paint onto your own collision — and the fix breaks GTA
Grass batch paints **only on top of base game collision**. If you try to paint
on a model in your own project, the brush paints **under the model**.

The fix in the video (in the author's own words *"we're hacking the system"*):
1. Export the area's **base game `.ybn`** as XML, bring it into Blender.
2. Free your own collision poly mesh with `Alt+P`, paste its **world
   coordinates** into the Collision → object location/rotation fields,
   drag it into the base game YBN's **BVH**.
3. Export and **write it back into the base game RPF** (CodeWalker
   warns *"you are editing base game files directly"*).
4. Restart CodeWalker → now you can paint onto your own collision.
5. ⛔ **The game fails its integrity check, GTA does not start.**
6. **Fix:** Rockstar Launcher / Steam → **verify game files**
   (downloads ~211 MB). Writing the file leaves the folders it sits in
   **decrypted**; verification encrypts them again.

> **Assessment:** it works, but it writes to a base game file and the undo
> step is mandatory. When suggesting it to the user, **state this cost**; placing grass
> props as entities in your own ymap may be enough in most cases.

### ⛔⛔ "Grass does not show" = check the GRAPHICS SETTING first
After doing everything right, the author **saw no grass at all** in game.
Cause: **Settings → Graphics → `Grass Quality`** was on **Normal**.
Setting it to **Ultra** and restarting brought the grass in.

> This is a variant of the atlas lesson *"a screenshot is not a measurement"*:
> **if the output does not show, rule out the player/settings side first.**

---

## 7. `@ma` procedural collision — very fragile

`@ma` collisions are bound meshes on which the engine scatters weeds/bushes
by itself, depending on the material index.

- An `@ma` collision has several materials, and **going down the list the
  material index goes up by one** (top = 1).
- Adding your own type: add a new material at the highest index in the list + 1
  and give it the procedural name (e.g. `proc_high_flowers`).
- **Join the geometry with `Ctrl+J`** into the bound poly mesh of the `@ma` collision
  (`Alt+P` → clear parent keep transform first).
- ⛔ **The only way the author found: ADD to an EXISTING `@ma` collision.**
  They did not manage to build an `@ma` collision from scratch.

### Corrected in the next video (`A8ueX5UgmGE`)
- Some grass types did not show at all. The cause was not the name, as assumed:
  ⭐ **the collision polygon must be BIG enough.** With the squares enlarged,
  **all** the types that had not worked before worked.
- Not every triangle gets grass — for performance.
- ⚠️ **Very fragile, use sparingly.** There are underwater types too (not tested).
- Verified type names: `city_weeds_01` · `mountain_side_dry` ·
  `mountain_side_lush` · `hill_side_lush` · `green_meadow_01` ·
  `city_weeds_sparse` · `city_weeds_litter` ·
  `AD_City_Industrial_Weeds_Lodo_01_Dense`

> `assetdb.py proc` and `assetdb.py mat` — we have the **data**. What was missing was the production side: **polygon size** and
> the requirement to **add to an existing one**.

---


## Community warning — terrain blend

⛔ **Terrain blending does not work at all without `UVMap 1`** (the lookup sampler uses it); also the **ALPHA of `Colour 1` must be black** (white = lookup off). (Sollumz Discord.)
