# Tool pitfalls — one catalogue

**Trunk file.** Pitfalls that belong to a tool (Sollumz, Blender,
CodeWalker.Core, PowerShell, Python/Lua, FiveM runtime) and hold in every branch
are written here **once**. Branch and leaf files link here and do not repeat them.
A task-specific pitfall does **not** go here; it is in the leaf.

Each item is one line: **symptom → cause → fix**. Measured items carry
"measured"; an item with details points to them with `→`. When there is no natural leaf
for the details, they are in the **Details** section at the end of this file.

Two trunk rules sum up this whole catalogue:
- **A tool not showing something does not mean that thing is absent.** (CodeWalker
  `ExprMap.Count == 0`, PowerShell `$null.Length == 0`, Sollumz "Imported in
  0.0 seconds" — each of the three burned us one day.)
- **A tool raising no error does not mean the work is right.** Nearly all the items in
  this catalogue are *silent*: the file is created, it says "success",
  nothing happens in the game.

---

## 1. Sollumz — export / import

### Settings and format
- ⛔ **`use_custom_settings=False` ignores the arguments you pass.** The operator reads the
  user preferences, not the settings you passed; the keys are valid, so no `TypeError`
  comes up. Measured: `limit_to_selected=True` was given,
  the whole scene came out, 170 drawables / 19 s. → Detail A
- ⛔ **`.ycd` is OUTSIDE Sollumz's format system.** Whatever `target_formats`
  is, it writes XML and says "Successfully exported" → it must be compiled to binary separately. For the other
  8 extensions (`.ybn .ydr .ydd .yft .yld .ytyp .ymap .ytd`) `NATIVE` really does
  write binary. → Detail B
- **`NATIVE` works only if `pymateria` is installed**; otherwise the setting **silently
  falls back to `CWXML`**. → Detail B
- **If Gen8 + Gen9 are both selected, the output goes to `gen8/` and `gen9/`
  subfolders**; with a single version, straight to the target. A script that reads a fixed path
  counts 0 while there are 36 files — search for the path, do not hard-code it. → Detail B
- **If the export folder does not exist**: `ios_base::failbit` + Blender hangs on exit
  → `os.makedirs` first.
- **The `Fill Animation Data` button is broken** — type the frame count by hand.

### Clip (`.ycd`) writing
- ⚠️ **`<Hash>` — MEASURED AGAIN on 2026-09-06; the old rule ("Sollumz does not write it")
  WAS WRONG.** Sollumz **does write** it: `ycd/ycdexport.py:510` `xml_clip.hash =
  clip_properties.hash`, `:352` `animation.hash = animation_properties.hash`.
  But the field is **filled by hand** — the `ClipProperties.hash` default is `""`
  (`ycd/properties.py:127`, `:161`) and it is not filled when a new clip is created
  (`create_anim_obj` does not set the hash), nor derived from the name. A clip left unfilled
  comes out with an **empty** `<Hash></Hash>`; the empty ones fall on the same key and overwrite each other.
  That was the reason for the old "5 clips → 1" measurement: not the tool, **the Hash field in the
  Clip panel had been left empty**. The symptom was real, the diagnosis was wrong.
  → ⛔ **When producing a clip, fill the `Hash` field in the Clip panel** (the established value:
  the clip's own name). Leave it empty and no error comes up, the clip is **not found** in the game.
  → ⛔ The only thing still not computed is the **Sequence** hash:
  `sequence.hash = "hash_00000000"  # TODO: calculate signature` (`:367`) —
  the zero inside `<Sequences>` is **normal**, do not fix it.
  → **The gate has not changed:** read back with `res_to_xml.ps1` and check whether `<Hash>` is filled.
  That gate is also what exposed this rule as wrong.
  **Measured (2026-09-06):** Sollumz **2.8.3** source + a raw export with 3 clips —
  all three came out with a filled, unique `<Hash>` field.
- ⛔ **`Animation.target_id` must be the ARMATURE DATA-BLOCK** (`arm.data`). Given the Object
  it writes **0 bone channels**: the file is created, the duration is right, there is no data
  (724 bytes vs 59 KB).
- ⛔ **In a UV animation the `Target ID` is the MATERIAL**, not the armature. Picking the
  armature out of ped habit is the most common mistake.
- ⛔ **It does not write the bone flags (`Flags`), it leaves them at zero.** A bone with zero flags
  accepts no transform: `PlayEntityAnim` returns 1, `animTime` advances,
  no error, the mesh stays in rest pose. Root **4215**, the others **119**; for a clip that
  drives scale this is not enough → `branches/map/destruction.md`.
- **It sorts clips and animations ALPHABETICALLY by object name**, not in creation
  order → write the binding explicitly with `<AnimationHash>`.
- **Six deviations in a RayFire `.ycd`** (double `pack:/`, `Unknown30`, no `Tags`/
  `Properties`, no Track 2, rest bbox) → `branches/map/destruction.md`
- **`.ycd` fcurve values are the ABSOLUTE bone-local orientation**, not a delta from rest
  → the real angle is `2·acos(|dot(q_clip, q_rest)|)`.

### Mesh / material / texture
- ⛔ **The fragment bound → bone binding is a `COPY_TRANSFORMS` constraint** (`BEFORE_FULL`/`POSE`/`LOCAL`), not `parent_bone` or a name match;
  without the constraint `does_bone_have_collision` is false, the bone is silently skipped, `PhysicsLODGroup` comes out empty. On an animated prop
  it is `Child Of` + Set Inverse, on a breakable fragment `Copy Transforms` — the two constraints are different. → `branches/prop/fragment.md`
- ⛔ **If `sz_lods.high.mesh` is not assigned, export says "has no Sollumz materials!"
  and skips the drawable ENTIRELY.** The material is there; on mesh objects created by script
  the field stays `None` → `ob.sz_lods.high.mesh = ob.data`.
- ⛔ **An object built with `bpy.data.objects.new` carries no `sollum_type`** → export
  does not count it as a Sollumz object, **the file is never written, and no error either**. Copy the mesh
  OBJECT of a working `.ydr` and swap its `.data`.
- ⛔ **`hide_select` SILENTLY drops `select_set()`.** The object is visible,
  `hide_viewport`/`hide_get()` are clean, `selected_objects` stays empty, export
  says "No Sollumz objects selected!". It can be on the object and on the collection —
  check all three, **count** `selected_objects` after selecting.
- ⛔ **On a hidden object `select_set()` silently does nothing** → export says
  "successfully", the file comes out **0 bytes** (5 of 7 objects were written like this) → `hide_set(False)`
  + check the file size.
- ⛔ **A Sollumz ymap can come out silently empty:** it says "Successfully exported", `<entities />` is empty, extent sentinel (3.4e38).
  There are two ymap systems (old `sollumz_ymap`, new `sz_maps_container`); mixed up they give "context is incorrect". Write ytyp/ymap XML by hand.
- ⛔ **Sollumz operators want a viewport context** — in a script/MCP there is no `context.selected_objects`/`active_object` → `temp_override`.
- **`converttodrawable` appends `.model` to the object name**; a search by the plain name silently returns empty. **A `.001` suffix breaks name matching** →
  `re.sub(r"\.\d+$", "", name)`. Building a drawable twice in the same scene produces `.001` pairs.
  Export, on the other hand, **drops** the `.001` from the drawable name: the output name comes out right, a search by name on the Blender side still breaks.
  Measured: 2026-09-11, Sollumz 2.9, 1 `.ydd` — object `head_000_r.001` → on read-back `<Name>head_000_r</Name>`.
- **If a texture is `embedded=False` it is never written into the `.ydr`**, no warning; once you turn it on, the second
  gate: **PNG cannot be embedded** → `texconv -f DXT1 -m 0` (mip chain required), the texture name
  derives from the file name.
- ⛔ **Do not change the diffuse on a template material and leave the normal** → the inherited
  `plants_normal` draws black lines on the prop. Both image nodes change.
- **Every drawable must have `Color 1`** (a mesh coming from OBJ has none) →
  write `(1,1,1,1)`, with **`.color_srgb`** (see Blender §2).
- ⛔ **Sollumz `Create Shader Material` adds a missing `Color 2` WITHOUT FILLING IT; Blender initialises a new `BYTE_COLOR` layer as WHITE (1,1,1,1).**
  The same step renames the existing vertex colour to `Color 1` in order (in an Unreal rip `PSKVTXCOL_0` → `Color 1`). On a ped
  `Color 2` = wind (RGB) + sweat/wetness (alpha): left white it gives **flickering** in the game, export gives no warning. On a vanilla ped `Color 2` is always 0 →
  after adding the shader pull `Color 2` to 0 (if it is the same value on every vertex it was never painted; if it was painted, do not touch it).
  **Measured:** Sollumz 2.9.0 + Blender 5.2.1, 2026-09-13; ped.sps and ped_default.sps on a rigged ped → `Color 2` white on 100% of vertices,
  white also in the exported head/uppr/lowr; `color_attributes.new` and `attributes.new` both initialise to 1,1,1,1. After pulling it to 0, the `.ydd` read-back
  shows Colour1 RGBA min = max = 0 in 3 drawables.
- **Export → Drawable → `Mesh Domain` = `Face Corner`**; `Vertex` is only for MP
  freemode heads. The wrong choice silently produces a broken ped.
- **Sollumz splits at the 65,535-vertex-per-geometry limit (16-bit index) by itself** — no manual split needed. But **a mesh without UVs shares no
  vertices**: vertices = 3 × triangles, the file bloats ~4×, no warning (probable cause: without UVs the tangent differs per corner; not measured) → unwrap UVs first.
  Measured: 2026-09-11, Sollumz 2.9, skinned ped — a UV-less mesh of 232,849 vertices → 22 geometries, max index < vertex count in all, total
  1,396,224 vertices (= 3 × triangles), `.ydd` 31 MB; an export with UVs of 12,520 triangles had 0.68 vertices per triangle.
- **A material without a Sollumz shader does not work in the game** — do not leave
  a Principled BSDF; verify with `Select` → the orange test.
- ⛔ **Sollumz packs the embedded texture FROM THE DDS ON DISK.** Loading a PNG in Blender and doing `img.scale()` + pixel edits +
  `save()` + `pack()` was not enough: a **16×16 placeholder** was embedded in the `.ydr`, no error, the defect showed on read-back → do the pixel work in Pillow
  (`im.save(..., pixel_format='DXT5')`). The embedded texture name comes **from the file name**, `img.name` is ignored.
- **Importing a weapon `.ydr` also creates a "Bound Box" MESH** — taking the first MESH picks it and says "carries no UVs";
  the criterion is `sollum_type == 'sollumz_drawable_model'`.
- **It cannot write binary `.yed`/`.ymap`/`.ytyp`** → for meta use `meta_xml_to_bin.ps1`
  (CodeWalker.Core, `MetaFormat.RSC`); for `.yed` there is no public path.
- **It WRITES `.ytd` (2.9)** — the old "cannot produce `.ytd`" note is void. Scene TXD:
  `scene.sz_txds.new_texture_dictionary(name)` + `txd.new_texture(image)`, then
  `export_assets(..., export_ytds=True, export_ytds_include="ALL")`. ⛔ `export_ytds` is off by
  default → "CANCELLED", no file; `sz_export_types` is a class attribute, not a parameter.
  The texture name comes from the image **file name**.
  Measured: 2026-09-11, Sollumz 2.9 + Blender 5.2, 1 sample — 64² A8R8G8B8 DDS → 411 B `.ytd`;
  on read-back the name, 64×64, 7 mips, format and the extracted DDS (21,972 B) matched the input.

### Import / skeleton
- ⛔ **It CANNOT READ binary `.ycd`/`.yed`**: it warns and says "Imported in 0.0 seconds",
  throws no error, the scene stays empty → `res_to_xml.ps1` first.
- ⛔ **The automatic bone tag formula does not produce vanilla tags** (`SKEL_Head` →
  21030, real **31086**) → on `.ycd` import the channels stay as `pose.bones["#31086"]`.
  The `Bone Properties → Sollumz → Tag` field is **typed by hand**.
- ⛔ **In bones local Y is the head→tail direction**, not the world axes. Pose
  formula `basis = L.inverted() @ M @ L` (`M` world rigid transform, `L =
  bone.matrix_local`); writing `L⁻¹ @ M` breaks the geometry even at frame 0.
- **Bone directions in the armature are NOT anatomical**: all 0.05 m, `use_connect=
  False`, `bone.vector` ~±Y, on the arm **56°** off the real direction → for direction use
  `head → child's head`; IK that uses `bone.vector`/`bone.length` works wrong.
- **A bone `tail` is not used as an effector** — tails are a synthetic 0.05 m →
  for target/direction use the child bone's `head`.
- **After import the scene stays at 24 fps**, GTA is 30 → a silent 25% timing
  error. `scene.render.fps = 30`.
- **A `.yft` import also creates a MESH named `SKEL_ROOT`** and it covers everything in the
  render. The ped origin is at the hips, the feet at z≈−0.94.
- **Cone angles are RADIANS** (`subtype=ANGLE`, 0–π/2); writing degrees opens the cone
  completely. Look at the property's `subtype`.
- ⛔ **Ped physics written by Sollumz CRASHES THE GAME** (it does not write
  `ArticulatedBody`) → a ped `.yft` ships without physics.
- **`bpy.ops.object.select_all(action='DESELECT')` silently breaks the selection in an MCP
  context** → `bpy.context.temp_override(...)`.
- **Light export, three links:** a hidden light is not dropped, its position breaks ·
  `light_properties.intensity` is not a stored field but an `energy` proxy · the position of a light
  attached to a bone is in BONE space · `Tangent` is the projection's **up**
  axis, not `Direction`. → `branches/look/lights.md`

---

## 2. Blender — API and data

### Transform
- ⛔ **THE OBJECT TRANSFORM BAKES INTO THE EXPORT.** If `matrix_basis` is not identity it is
  written into the geometry (measured: the drawable was drawn **394 m** away). Reset `matrix_basis`
  **and** `matrix_parent_inverse`, **verify in the same call**.
  It also bakes on a ped model bound to an armature, even with `apply_transforms=False` → an FBX's unapplied scale/rotation does not break the ped.
  Measured: 2026-09-11, Sollumz 2.9, 1 `.ydd` (3 drawables) — scale 0.01 + X 90°, mesh data compensated: text difference from a normal export 0,
  bounding boxes 1e-7 m, largest numeric difference 0.005 (a tangent component).
- ⚠️ **BUT DO NOT RESET BLINDLY.** On a placed object (one that carries a position)
  resetting teleports it to the origin (a corpse went 40 m away). The right way is **bake,
  then reset**: `o.data.transform(o.matrix_world)` → identity.
- ⛔ **`bpy.ops.object.transform_apply` may silently do nothing**
  (the mesh shifted 124 m, no error) → `ob.data.transform(ob.matrix_world)`.
- **`bound_box` can be STALE** — after `mesh.transform()` it returns the old value.
  Compute the box **from the vertices**.
- ⛔ **`object.dimensions` DOES NOT INCLUDE ROTATION** (local bbox × scale) → "lay the longest
  axis down" silently does nothing; use the world bbox.
- ⛔ **`view_layer.update()` before reading `matrix_world`** — it bites most on **newly
  appended/linked** objects: until the depsgraph updates it returns identity,
  `data.transform(matrix_world)` does nothing, then when the basis is
  reset the rotation/scale is **deleted without being baked**. No error. **Measured:**
  Blender 5.2.1 headless, `ExamplePed` (rot 90°, scale 0.01) came out lying down, seen only in the
  preview render; with `update()` added, the world box difference before/after baking
  was 0.0, 2026-09-11.
- **If `Ctrl+A` All Transforms is skipped**, scale/rotation leak into the export.

### Geometry
- ⛔ **`bmesh.ops.bisect_plane` does not clip open geometry, it DELETES FACES** (over six
  calls the face count stayed 637, area 3.553 → 0.941 m²). Boolean INTERSECT is also
  unreliable → **Sutherland–Hodgman**. → `branches/look/decal.md`
- **Merging bmesh by hand drops the UV and colour layers** (`bm.faces.new()`
  carries no loop data) → `mesh.transform()` + `bpy.ops.object.join()`.
- ⛔ **`holes_fill` samples UV (0,0)** — the texture corner becomes a patch → if the open edge
  ratio is >5%, use `solidify`; scale by the **largest** axis.
- ⛔ **Decimate breaks the 4-influence rule** → after LOD, on rigid parts pull the
  weight back 100% to one group.
- ⛔ **DELETING a vertex group also deletes the weights**; weights are stored by group **index**,
  recreating the list lands the names on the wrong indices.
- **The Armature modifier can be broken** (500+ m scatter) — if `pose @
  matrix_local⁻¹` is right by hand, the file is sound; trust the maths, not the viewport.
- **`scene.ray_cast` uses the VIEWPORT** — an object visible in the render but hidden in the viewport
  is skipped by the ray test.
- **Entering Edit Mode brings the PREVIOUS SELECTION back** → `f.select_set(False)` first
  (the reason a tool produced 4089 decals).

### Colour / layers
- ⛔ **On a `BYTE_COLOR` layer `.color` DECODES GAMMA**, `.color_srgb` gives the raw
  byte/255. GTA uses vertex colour as a mask/multiplier → `.color`
  silently darkens every mask. Sollumz keeps it as `"Color 1"`, in the CORNER domain.
- **The UV layer's name is `UVMap 0`** — any other name is silently dropped; copied
  geometry inherits the target's old UV and `Color 1` alpha.

### Animation / pose
- **The Blender 4.4+ Action API is layered**: there is no `action.fcurves` →
  `layers → strips → channelbags → fcurves`; and **assigning the action is not enough, the SLOT
  must be bound too** (`animation_data.action_slot = act.slots[0]`).
- **A bone that is not keyframed stays in its last pose** → reset the pose before measuring;
  before posing by hand set `animation_data.action = None` (an assigned action overwrites the pose on
  every `view_layer.update()`).
- **In Blender 5.0 selection moved from `Bone` to `PoseBone`.**
- **Bezier interpolation** speeds up and slows down UV/clip animation → Linear.

### Scene / collection
- **The object shows in the scene but will not enter Edit Mode, Sollumz type
  `sollumz_none`** → the object is really an **EMPTY + `instance_type='COLLECTION'`**
  (a collection from an asset library entered the scene as an instance; the real
  objects are in a collection not linked to the scene). Fix: select → **Object ▸ Apply
  (`Ctrl+A`) ▸ Make Instances Real**, tick **Keep Hierarchy** in the bottom-left panel
  (off by **default**; the armature→mesh parent depends on it). Then
  read back: is the meshes' Armature modifier target the **new** armature, do the names carry
  a `.00N` suffix (the originals were not deleted, so the copies get a suffix).
  **Measured:** Blender 5.2.1, 3 empties from StalkerAssetLibrary
  (`red_forest_bridge_01_dynamic`: 1 armature + 11 meshes, all with an Armature
  modifier), 2026-09-11; menu path read from the `VIEW3D_MT_object_apply` source,
  defaults from the operator RNA.

### Version / environment
- ⛔ **Blender 5.x: `GPUShader(vertexcode, fragcode)` WAS REMOVED** →
  `gpu.shader.create_from_info`; **there is no `GPUStorageBuf`** → array data from a UBO.
- **A draw handler that draws its own pass at the same depth as the solid pass**
  makes the scene z-fight → first `gpu.state.active_framebuffer_get().clear(depth=1.0)`.
- **Blender 5.x compositor**: `scene.node_tree`/`use_nodes` were removed →
  `scene.compositing_node_group`; `CompositorNodeComposite` was deleted → the group's
  `NodeGroupOutput`; node settings moved to input sockets.
- ⛔ **Blender 5.x: `mod["Input_3"]` on a GN modifier WAS REMOVED**
  (`TypeError: this type doesn't support IDProperties`) → the path is
  `mod.properties.inputs`, read/write **from the socket itself**:
  `getattr(mod.properties.inputs, ident).value`. `inputs[ident] = 12.0` on a float
  socket gives `Cannot assign a 'float' value to the existing Group IDProperty`;
  **on a bool it gives NO error but corrupts the value** — silent. `ident` comes from the node
  group's `interface.items_tree` (`Input_3`, `Socket_11`);
  `inputs["Resolution"]` is a **KeyError** — there is no access by name, build the name→ident
  map yourself. After writing, `obj.update_tag()` +
  `view_layer.update()`, then **read back** — this pitfall only shows up on
  read-back. **Measured:** Blender 5.2.1, ORGANIC addon GN tree, 2026-09-09;
  four access paths tried one by one.
- **Deleting a collection does not delete its objects** (orphaned bake lights lit the following renders). **A module-level Image/Material
  cache** survives a file change → `StructRNA … removed`; look it up from `bpy.data` on every call. Blender caches submodules.
- **"Run it from the start" is not safe after a mutation that stopped halfway** — the meshes had moved, it crashed on the light; it applied the same
  offset again. The operation must be idempotent or the state must be read first; the type filter up front.
- **Reading `Image.pixels` after a render is not reliable** (exception → silent fallback) → measure outside with PIL. **`dither_intensity`**
  adds noise to 8-bit writes, which turns into speckles when exponentiated → 0. **`read_homefile(use_empty=True)` also deletes scene properties** → settings
  go in `AddonPreferences`.
- **`execute_blender_code` uses a NEW namespace on every call** — define helper functions
  in the same call.
- **`read_factory_settings` removes the add-on** (Sollumz disappears headless).
  **`--factory-startup`** does the same: no add-on is loaded.
- ⛔ **In a headless test, registering the add-on a SECOND time via `sys.path` PRINTS A FAKE TRACEBACK ON EXIT.** In a `-b` run opened with user
  preferences the add-on is already registered as an extension (`bl_ext.user_default.<id>`); when the test registers the same classes again Blender
  says "registered before, unregistering previous", and on shutdown the extension copy's `unregister` throws
  `unregister_class(...): missing bl_rna … (may not be registered)` — NOT an add-on bug. To tell them apart, run the same test
  with `--factory-startup` (single copy: register → unregister → register is clean). It may be one source of the "unregister error on
  exit" below; its link to the hang was not measured. To load new code in a live session: `addon_utils.disable(name)` → delete
  `name` and its submodules from `sys.modules` → `addon_utils.enable(name, default_set=True)`; Scene `PointerProperty` values are kept.
  **Measured:** Blender 5.2.1, a rig add-on, 2026-09-12; two headless runs (with preferences: traceback, factory: clean) + a reload in a live
  session (14 modules deleted, labels new, 5 scene settings unchanged).
- ⛔ **In an unsaved scene a RELATIVE `render.filepath` resolves against the drive root, NOT the cwd.** In the same script Python `open()` reads a relative
  path from the shell's cwd (the project); `render.filepath = "out/video/frames_ws/0000.png"`, however, writes to `C:\out\video\frames_ws\0000.png`
  and creates the folder itself. The log says `Saved: …`, exit code 0, the project folder is EMPTY — silent. Apply `os.path.abspath` to the path and
  after writing, count the frames in the TARGET folder. **Measured:** Blender 5.2.1 `-b --factory-startup --python`, shell cwd = project,
  2026-09-13; 2 × 585 frames were written under `C:\out`.
- ⛔ **Publishing a `.blend` also publishes personal paths.** The file carries, as plain text, the file browser / asset library /
  preset paths of the machines it was saved on (including the user name of ANOTHER computer that opened and saved it before). `rg` SKIPS binary files;
  a Blender 5 `.blend` can be ZSTD-compressed → a raw byte scan does not see it either: open it with `zstandard` in Blender's Python
  (`ZstdDecompressor().stream_reader(..., read_across_frames=True)`), then search. A `save_as_mainfile(copy=True)` copy CARRIED the traces.
  Cleanup: write the needed datablocks with `bpy.data.libraries.write(path, {obj}, compress=True)` into a folder with no personal name and
  verify equality. In Blender 5 add-on properties (e.g. Sollumz `bone_properties`) are not visible with `bone.get()` → do the comparison in a session with the add-on
  LOADED. **Measured:** Blender 5.2.1, 2026-09-12; 1 template `.blend`: source 14 traces (`C:\Users\<name>\Desktop…`,
  `…\AppData\Roaming…\presets`, a second user `…\OneDrive\…`), the `save_as_mainfile` copy carried traces, the `libraries.write` copy 0 traces;
  128 bone matrices + Sollumz tags/flags equal.
- **Test an add-on install WITHOUT TOUCHING the user's Blender:** `BLENDER_USER_RESOURCES=<temp folder>` → first check that
  `bpy.utils.resource_path('USER')` returns that folder; if it does not, STOP. Then `--online-mode --command extension repo-add <id>
  --url <index.json>` → `sync` → `list` → `install <package> --enable`; in a separate `-b` launch `addon_utils.check('bl_ext.<id>.<package>')`.
  Static remote repository: `extension server-generate --repo-dir <folder> --html` (`index.json` + `index.html` with drag-and-drop links,
  `archive_url` relative) → GitHub Pages via a `gh-pages` branch + `.nojekyll`; to enable Pages, the `gh api -X PUT repos/<o>/<r>/pages` body
  as JSON from stdin (an argument containing `/` is turned into a path in Git Bash). **Measured:** Blender 5.2.1 + gh 2.100.0, 2026-09-12; Pages live in
  ~70 s, the zip served 200 with `application/x-zip-compressed`; isolated install enabled, the real `extensions` folder and the `userpref.blend` hash unchanged
  (1 add-on).
- ⛔ **Sollumz's module NAME changes with the install path; an import by a fixed name fails on another machine.** In the old add-on install
  the name is the folder name (`Sollumz`, `Sollumz-main` from the GitHub source zip); in an extension install it is `bl_ext.<repo>.sollumz`
  (`user_default`, `blender_org` or the user's repo name). Trying fixed names with `try/except ImportError` does two kinds of harm:
  if the name does not match, `create_shader` is never found (on the silent path materials have no texture nodes, the bake is **pitch black**, the render **blank grey**) and
  an ImportError INSIDE Sollumz (e.g. `No module named 'szio'`) is also swallowed as "not found". **Path:**
  in `bpy.context.preferences.addons.keys()` find the one whose last name part is `sollumz` / `sollumz-…` / `sollumz_…`, the version from
  `addon_utils.module_bl_info(sys.modules[name])["version"]`, then `importlib.import_module(name + ".ydr.shader_materials")`;
  write the caught exception into the message. Version facts (GitHub tags): `create_shader` was always in `ydr/shader_materials.py` from v2.3.0 to v2.9.0;
  `Scene.sz_txds` and `export_ytds_include` ONLY in 2.9.0; `blender_manifest.toml` since v2.5.0. The Sollumz 2.9 dependency `szio`
  is not in the add-on folder but in `<USER>/config/sollumz/data/lib/python3.x/site-packages` — copy that folder too in an isolated test.
  **Criterion:** after `create_shader` the material must HAVE a `ShaderNodeTexImage` node. **Measured:** 2026-09-12; a remote user's Blender
  5.1 + Sollumz 2.9.0: "Sollumz not found (create_shader)"; locally 2.9.0 installed under the name `Sollumz-main` (isolated `BLENDER_USER_RESOURCES`):
  the two old names ImportError → the same message, name-independent search → found, `ped.sps` 5 texture nodes; a normal `Sollumz` install worked too.
- **Blender 5.2 hangs on exit on this machine** — it finishes the job and saves the
  `.blend`, the add-on throws on unregister, the process does not exit. Headless pipelines
  are ended with a timeout.
- ⛔ **SAVE the `.blend` after every export** and copy the verified output to a dated
  folder. In-memory intermediate data (`bpy._X`) is not persistent; a day's work
  survived only in the exports, the motion tables were lost.
- **The criterion is not the operator saying `{'FINISHED'}` but the KEYFRAME COUNT** — a modal
  operator looks successful in `-b` mode without ever running.
- ⛔ **`blender -b --python <path>` NEVER RUNS the script on a path over 260
  characters, and the exit code is still 0.** The log has a single line `OSError: Python file "…"
  could not be opened: No such file or directory`, the rest is a normal start and
  "Blender quit". The cause is the path **length**, not the 8.3 short name (e.g. `KULLAN~1`).
  Claude's scratchpad path alone exceeds this limit → put the script on a short path
  (`%TEMP%\claude\<job>\`). The criterion is not the exit code but **the existence of the output
  file the script writes**. **Measured:** Blender 5.2.1, a 272-character path FAIL,
  the same script on a short path OK, an 8.3 short path OK, 2026-09-11.
- ⛔ **`bpy.ops.object.mode_set` applies to the caller's CONTEXT object.** A function that does `view_layer.objects.active = arm` and switches EDIT → OBJECT,
  when called from outside under `temp_override(object=mesh, active_object=mesh)`, leaves the skeleton **in EDIT** — no error,
  but the pose of a skeleton in EDIT **never deforms** the mesh. Switching only the override to the skeleton was not enough either (with another active object it did not
  leave EDIT); `objects.active = arm` **and** `temp_override(object=arm, active_object=arm, selected_objects=[arm])` together get it out.
  Read back `arm.mode` on exit. Criterion: vertex difference between the `evaluated_get` mesh and the original > 0. **Measured:** Blender 5.2.1, 2026-09-12;
  reproduced headless (old EDIT, fixed OBJECT, rest error 0.0 mm); in a live session pose difference 0 → 805 mm.
- ⛔ **On a mesh with shape keys, writing `mesh.vertices.co` is NOT REFLECTED in the view or the export** — the evaluated mesh comes from the basis key;
  no error, the mesh stays "unchanged" (every vertex-moving operation such as re-posing or converting to rest is silently ineffective). Path: before the operation
  remove the shape keys (`obj.shape_key_clear()`; facial expressions are lost) or stop the operation. Writing to `key_blocks[i].data` was not measured.
  Criterion: position difference in the `evaluated_get(depsgraph)` mesh. Ready-made characters come with shape keys (Ready Player Me glTF: 15 keys on 10 meshes).
  **Measured:** Blender 5.2.1, 2026-09-12; on a cube with shape keys `vertices.co` +1.0 was written, evaluated difference 0.0 (1 cube, test script).

---

## 3. CodeWalker.Core

- ⛔ **It reads `.yed` bytecode (`Streams`) but CANNOT WRITE it.** Seeing `ExprMap.Count == 0`
  does not mean "the file is empty"; **saving empties `Streams`**, the face and
  all procedural motion die.
- ⛔ **The XML reader does NOT WRITE `FxcFileHash` and `VFT` in a `.ypt`** → every `.ypt`
  produced from XML comes out without a shader, nothing is drawn (vanilla binary
  `246470498`, XML round trip `0`) → `scripts/ypt_xml_to_bin.ps1` writes the hash, reads it
  back, exit 1 if zero. **General lesson:** with a new resource type, the first job is to dump a vanilla
  file to XML, read it back and compare field by field.
  → `branches/particle/ypt-from-scratch.md`
- ⛔ **`YtypFile.Save()` SILENTLY DROPS the `compositeEntityTypes` block**
  (925 → 836 bytes). The XML path does not drop it. → `branches/map/destruction.md`
- **`.ytyp`/`.ymap` are both written through `MetaFormat.RSC`** — do NOT LOOK for a
  `ytyp`/`ymap` member in the enum (when it was not found, "it cannot write" was said and the wrong path was taken).
- **`YptFile.Load()` wants an `RpfFileEntry`**; passing `null` blows up → 
  `RpfFile::CreateResourceFileEntry([ref]$d,0)` + `ResourceBuilder::Decompress`.
- ⛔ **`foreach` over `ResourcePointerArray64<T>` → `NotImplementedException`**,
  the walk silently gives a wrong result → do not walk the block tree, **narrow it down by halving**.
- **Do NOT READ `ClipBase.Name`** → StackOverflow, exit 253, no message.
- **`Add-Type` needs a `netstandard` reference**; `Animation.BoneIds` is not an array
  → `.data_items`.
- **In the GUI `LoadClipDict(string)` resolves the dictionary by name from GAME data** —
  a loose `.ycd` in a resource folder does not appear in the list.
- ⛔ **`.ytd` XML schema: `<Item>` DIRECTLY under `<TextureDictionary>`**, no `<Textures>` wrapper; the wrong wrapper raises no
  error, it produces **a 57-byte empty dictionary**. `XmlMeta.GetXMLFormat` wants **the file name** (`x.ytyp.xml`); given the root tag it
  returns generic `XML`, and `GetData` returns empty. There is no `XmlYtyp`/`XmlYmap` class for ytyp/ymap.
- ⛔ **`RpfFile.ScanStructure()` crashes without keys** (`GTA5Keys.LoadFromPath` first); if a `try/catch` swallows it the scan silently ends empty
  and "the texture is not in GTA" is assumed (19/19 were there). `RpfManager.Init` is an instance method. **Always print how many files it read**; zero means a fault.
- ⛔ **`MetaHash` ≠ `UInt32`.** `archetypeName` is a `MetaHash`; in a `UInt32`-keyed
  hashtable `ContainsKey` never matches and "0 leftovers" is read →
  `[uint32]$en._CEntityDef.archetypeName`.
- ⛔ **Resource file size is NOT a validity criterion** (RSC7 zlib): an unpacked 32,768-byte
  `.ypt` → `Save()` 3,077 bytes is the same content. The only criterion is **reading back**.
- **The DDS extracted on read-back is NOT BYTE-FOR-BYTE the same as the input** — CodeWalker writes the header itself (`DDSD_PITCH` in the flags,
  pitch = row bytes `4·w`, depth 1); the pixel payload is the same. The hash says "different" → compare **everything after byte 128**.
  Measured: 2026-09-11, Sollumz 2.9 `.ytd` → `res_to_xml.ps1`, 9 textures A8R8G8B8 (8² and 256²): payload 9/9 the same, 4 bytes different in the header.
- ⛔ **Do not write "I don't know, 0" into an `Unknown*` field** — `UnknownA4..B0` is a distance
  band, 0 never appears in vanilla; `Unknown10C` is `0x10100` in 1638/1736.
  **Look at its distribution**, take the most common value.
- **CodeWalker XML writes a name it does not know as `hash_XXXXXXXX`** (ytyp name, texture, shader) → put the joaat (upper-case hex) of stream file names /
  known names in a table and match them; write a new name as **plain text**, the compiler hashes it. The same hash as the template is not a defect
  (`hash_38DD00DF` = `normal_spec.sps`).
- **`StaticVector3`/`StaticFloat` in a `.ycd` channel = that bone/axis never moves** — do not assume motion just because a channel exists;
  the channel types on one bone can be **mixed** (X/Z `QuantizeFloat`, Y `StaticFloat`); if you expect them all to be lists you miss the motion.
- **It ALREADY decodes the quantisation when converting to XML** (`<Values>` plain float) — do not write
  your own decoder; `CachedQuaternion` is a pointer, not a channel; `.//Animations` is the
  wrong node; two clip types (`Animation`/`AnimationList`).
- **When writing a ymap do not call `CalcFlags()`** (contentFlags 65→1), do not use `CalcExtents()`
  (zero box), do not write `CEntityDefs` directly (0 entities).
- **A ymap name is not unique** — without `rpfPath` the LOD measurement comes out wrong.
  → `branches/map/lod.md`
- **Property names — a wrong name returns `$null`, no error** (see §4): Bound `BoxMin`/`BoxMax`
  (not `BoundingBoxMin/Max`), Drawable `DrawableModels`/`AllModels` (not `DrawableModelsHigh`);
  `ShaderGroup.Shaders` in foreach gives `NotImplementedException` → `.data_items`. Measured: a road destruction project, 2026-09-01.
- **If CodeWalker is a portable `.exe`, computer-use cannot find it** → the agent cannot drive
  the GUI step, it gives the user directions.

---

## 4. PowerShell 5.1

- ⛔ **Scripts are called with `powershell` (5.1), not `pwsh`.** No ternary
  (`? :`) and no `??`; `[single](if (...) {...} else {...})` does not parse and the error
  comes as *"'if' is not recognized"* — use an intermediate variable.
- ⛔ **On a path with square brackets such as `[script]`, `Test-Path`/`Copy-Item`/`Remove-Item`
  treat it as a wildcard** → **`-LiteralPath`**. In `Copy-Item` it is SILENT: the copy never
  happens, no error; `stream/` stayed on the old version, the old asset was tested for
  several rounds. After a copy, compare size/hash.
- **`-LiteralPath` does NOT EXPAND wildcards** — `"$dir\*"` copies nothing. If you need a
  wildcard use `-Path`; if there are square brackets use `-LiteralPath`.
- **`Split-Path -LiteralPath $p -Parent` gives `AmbiguousParameterSet` in 5.1** → the result is `$null`, then `Test-Path -LiteralPath $null`
  also prints an error; if the target folder already exists the copy still happens and the error is taken as harmless → `[IO.Path]::GetDirectoryName($p)`.
  Measured: 2026-09-11, Windows PowerShell 5.1, a 13-file copy loop under `[script]`: two errors per file, copies hash-equal.
- ⛔ **`-replace` is case-INSENSITIVE** — an `'ABC'→'x'` rule also breaks `abc_module`
  → if you are changing code/names use **`-creplace`**, then scan for leftovers.
- ⛔ **With `-File` a comma-separated list becomes ONE STRING** and silently breaks (10 files
  requested, "0 files extracted") → `-Command "& script.ps1 -Names @('a','b')"`.
- ⛔ **A NON-EXISTENT property raises no error, it returns `$null` — and `$null.Length` is `0`.**
  A misspelled name makes you say "I measured, no data" (`Effects` was read instead of `EffectRules`,
  and "CodeWalker cannot write `.ypt`" went into the document — the tool was working).
  In a foreign DLL, first `$o.GetType().GetProperties() | % Name`, or a guard:
  `if(-not $o.PSObject.Properties[$name]){ throw "NO PROPERTY: $name" }`.
- **`Add-Type` compiles C# 5**: `?.` does not work.
- **Variables are case-INSENSITIVE** — a backup path `$y` in a loop overwrote `$Y`.
  Short name + loop = this bug.
- **`"$S\$n.ymap"` produces the wrong path** (`$n.ymap` is taken as a property) →
  `"$($n).ymap"` or `Join-Path`.
- **`@(@(x,y))` FLATTENS when it has a single element** → `$k[0]`/`$k[1]` go wrong, the match
  is silently missed ("0 deleted", the rubbish bin was 1.1 m away).
- **A `.ps1` with non-ASCII characters and no BOM is misread by 5.1** →
  `audit_plugin.py` checks for this.
- **In a `while read` loop `powershell` swallows STDIN** → `< /dev/null`.
- **Two CodeWalker scripts called one after the other with `&` in the same PowerShell session** (the measured pair: the `.ycd` compiler + `res_to_xml.ps1`) → the AssemblyResolve handlers
  call each other, **StackOverflowException**, the process dies silently → run each tool with a separate `powershell -File`.
- **`res_to_xml.ps1 -Path` crashes on a `[script]` path** and does not take a folder with `-Path`
  → copy to a folder without brackets, `-Dir` + `-Filter`.

---

## 5. Python · Lua · shell

- ⛔ **In Python `glob`, `[script]` is a character class** → it never matches, raises no
  error → `os.listdir`.
- **`%` in `argparse` help text must be escaped (`%%`)**, otherwise `--help` gives `TypeError`.
- **If the console breaks on Turkish characters, `PYTHONIOENCODING=utf-8`.**
- ⛔ **Escapes break when a Lua file is written from Python** — `\n` turned into a real line
  break and split the string, **no command was registered**; `lua_check`
  shows the syntax as clean. Write those lines directly with `Edit`.
- ⛔ **A Turkish apostrophe (`'`) CLOSES a Lua string — `lua_check` misses it.**
  Move visible text into the locale file.
- **`Wait()` cannot be called in a command callback.**
- **A Windows `ffmpeg` called from Git Bash cannot open a `/c/...` path** → `C:/...`.
- ⛔ **Git Bash CONVERTS an argument starting with `/` into a Windows path:** `gh api /licenses/gpl-3.0` → `C:/Program Files/Git/licenses/gpl-3.0`
  ("invalid API endpoint"). A `> file` redirection **still creates the empty file** before the command runs. Path: drop the leading `/`
  (`gh api licenses/gpl-3.0`). **Measured:** gh 2.100.0, Git Bash, 2026-09-12; the same endpoint worked without the `/` (1 attempt).
- ⛔ **The `np.argsort` default (quicksort) changes the order of EQUAL values depending on the numpy version.** A tie-sensitive selection (sorting by an integer
  distance/counter and "first one wins") gives DIFFERENT results with Blender's numpy and the system Python's numpy → tests that run outside Blender
  do not measure the add-on's behaviour in Blender; no error. Path: `kind="stable"` in the selection (or an explicit secondary key,
  `np.lexsort`); `argpartition` has no stable option. Criterion: run the same input in both environments and compare the output signature.
  **Measured:** Blender 5.2.1 numpy 2.3.4 ↔ system Python numpy 2.5.1, 2026-09-12; 3 mesh inputs: with the default order 3.37 ↔ 3.26 cm and
  in one case success ↔ error; with `kind="stable"` both environments identical to 6 digits.
- **`"stream$f.ydr"` goes as one piece**, the file is not found → build the path separately with a variable.
- **`rm my_t*` deletes production files along with the test subjects** — `ls` the wildcard range first.
- **Downloaded audio can peak at −25…−29 dB** → measure with `volumedetect`, normalise.

---

## 6. FiveM runtime

- ⛔ **After an asset changes, LEAVE the server and RECONNECT.** The stream is
  cached; **a restart is not enough**. Skip this and a stale asset is tested.
  Extra for weapons: `str_requestFlush` (canary) and **put the weapon away first**.
- ⛔ **A BROKEN STREAM ASSET SILENTLY DROPS THE WHOLE RESOURCE.** The server prints
  "Started resource", no command registers on the client, no print, no error
  in F8. Diagnosis: set up a second resource **without** a `stream/` folder; if its command
  works, the defect is in the stream. Do not tinker with the Lua.
- ⛔ **If a resource is in two folders, FiveM silently ignores one** → when "it does not
  show", the first place to look is **the server log**.
- **Asset names have no uppercase letters.** Adding a new file to the stream takes three steps
  (file + manifest/`data_file` + leave/reconnect).
- ⛔ **The stream files of an escrowed (`.fxap`) resource are encrypted** — copy them and
  the client crashes ("Couldn't find asset key"). Crash diagnosis: CitizenFX log `Error:`.
- **Killing the client leaves a ghost session.**
- **`PtFxAssetStore Pool Full, Size == 400`** — the pool counts FILES; **a single large
  `.ypt` freezes the game** (measured threshold). → `branches/particle/deployment-measurements.md`
- **Reading JSON on the client with `LoadResourceFile` did not work** → Lua table.
- **`SetEntityCollision(false)` on a map object is not reliable** — it becomes invisible,
  the collision stays → `CreateModelHide`; **without taking control,
  `FreezeEntityPosition`/`SetEntityCoords` are ignored**; **a root-bone clip does not play
  on a frozen object**. → `branches/prop/doors-and-motion.md`
- **Handle caching** (`doorRegistered[hash]`, "did the handle change") —
  FiveM reuses handles → ask **the real state**, e.g. `IsEntityPlayingAnim`.
- **`GetPedBoneIndex` / `GetPedBoneCoords` take a TAG, not an index.**
  → `trunk/bone-tags.md`
- ⛔ **`set` is FiveM's built-in convar command** — `RegisterCommand('set')` does not silently override it; the built-in one runs and
  gives *"Argument count mismatch"*. Prefix your test commands. **`os._exit(0)` does not flush the stdout buffer** → `flush()` first.
- **A name mismatch in `.rel` / audio XMLs silently breaks everything** (community).
- **`DrawSpritePoly` is not the canonical name** — `DrawTexturedPoly`; `/native-lint`
  counts it as invented.

---

## 7. External tools (community)

- **With Rokoko `Auto Scale` on, root motion is deleted COMPLETELY.**
- **Void Tools Vertex Color Bake is the only tool that writes to the mesh** → make a dated copy of the
  `.blend` before using it. → `branches/look/decal.md`
- **The Five Toolkit weapon bone tag table is wrong** → `sources/external-tools.md` §1a
- **Sketchfab glb downloads: do not trust the "rigged" label, the scale or the orientation.**
  - **Bone names:** node names get a `_<number>` suffix (`hand_l_026`, `Thumb1.L_91`) → match by the full name.
  - **Label:** a model labelled "rigged" can come without a skeleton (skin 0); verify the skeleton from the `skins` field in the glb JSON.
  - **Height and orientation:** it can arrive 51 m tall (node scale 0.807) or lying down at −90° X.
  - **Accessory:** an accessory bound to a separate skeleton (an axe) gets mixed into the mesh.
  - **Download chain:** `sketchfab.com/i/models/<uid>/download` (login required) returns the format and size JSON →
    `/i/archives/latest?archiveType=glb&model=<uid>&textureMaxResolution=1024` returns the signed S3 link JSON → opening the link in a browser downloads the file.
  - Measured: 6 models, 2026-09-12 (1 without a skeleton, 1 at 51 m, 1 lying down + axe).

---

## Details

### A. Sollumz `use_custom_settings` — source

`sollumz_operators.py:415` and `:132`:

```python
prefs_export_settings = self if self.use_custom_settings else get_export_settings()
```

With the flag off, the operator leaves its own properties and reads the **user
preferences**. `directory` and `direct_export` are outside the settings group and
work independently of the flag — the files go to the right folder, so the defect
stays hidden. Silently inherited: `apply_transforms` (if True the transform
**bakes into the geometry**), `limit_to_selected` (if False **the whole scene**),
`target_formats` (if CWXML then XML), `target_versions`, `export_ytyps/ymaps/ytds`.

Verification: **deliberately break** the preferences, export, see that the output is unaffected,
restore the preferences.

### B. Sollumz export format — does `NATIVE` really write binary?

**Yes, but conditionally — and `.ycd` is entirely outside this system.**

```python
# szio/gta5/native/__init__.py:7
IS_BACKEND_AVAILABLE = importlib.util.find_spec("pymateria") is not None
```

```python
# sollumz_preferences.py:377-378
if not self.target_formats or (not is_provider_available(AssetFormat.NATIVE)
                               and "CWXML" not in self.target_formats):
    self.target_formats = {"CWXML"}       # ← SILENT fallback
```

Verified with a live test (Blender 5.2 + Sollumz 2.8), reading the first 4
bytes of the output files:

| Setting | Output | Size | First 4 bytes |
|---|---|---:|---|
| `NATIVE` + `GEN8` | `x.ydr` | 451 | `52534337` = **`RSC7`** (binary) |
| `CWXML` + `GEN8` | `x.ydr.xml` | 2,699 | `3c3f786d` = `<?xm` |
| `NATIVE` + `GEN8`+`GEN9` | `gen8/x.ydr` **and** `gen9/x.ydr` | 451 / **558** | both `RSC7` |
| `NATIVE`+`CWXML`, single version | `x.ydr` **and** `x.ydr.xml` | — | both in the same folder |

The Gen8 and Gen9 outputs differ in size — Gen9 is not a cosmetic label, it really is a different file.

#### Gen8 / Gen9 — measured detail

```python
# iecontext.py:99-100
gen8_directory = directory / "gen8"
gen9_directory = directory / "gen9"
```

- `("GEN9", "Gen9", "GTAV Enhanced", 2)` — Gen9 = **GTA V Enhanced**.
- If both versions are selected the output is split into **`gen8/` and `gen9/` subfolders**.
  With a single version the files are written straight to the target folder.
- ⚠ Our pipeline assumes a single output path: every script that calls `extract_asset.ps1` /
  `xml_to_res.ps1` will **not find the file where it expects it** while both versions are on.
- Gen9 has its own shader defaults (`ShadersG9ParamsDefaults.json`,
  `ShadersG9TextureNameMapping.json`) and its own adapters
  (`drawable_gen9.py`, `fragment_gen9.py`, `texture_gen9.py`).

The extensions supported by both providers are the same 8:
`.ybn .ydr .ydd .yft .yld .ytyp .ymap .ytd`. `.ycd` is not in this list:

```python
# ycd/ycdexport.py:574
clip_dict.write_xml(filepath)          # hard-coded XML
```

→ a separate compile for `.ycd` is still **mandatory**; for `.ydr/.yft/.ybn` you can skip
`xml_to_res.ps1` if `NATIVE` works. Measured: moved from `trunk/flags.md` §7
(2026-08).
