# Ped cloth — cape, skirt, veil: fabric that flows with the character

**When to read:** fabric on a ped that must ripple **with motion** (cape, skirt, veil, coat tail). Prop cloth (`.yft` env cloth) CANNOT do this: an attached fragment has zero physics velocity, so the sim does not see the carrier's motion; even vanilla `prop_flag_*` is flung forward/sideways when attached (measured: 2026-09, 2 models).
**Source:** Sollumz source `ydr/cloth_char.py`, `ydr/vertex_buffer_builder.py`, `ydd/yddexport.py` (main, 2026-09) · vanilla `csb_bride.yld`/`.ydd` dump · **Measured:** source reading + 1 vanilla file + **1 export of our own** (a cape, Blender 5.2 headless, Sollumz 2.9.0, 2026-09: `.ydd` 705 KB + `.yld` 6.5 KB, 221 sim vertices / 13 pinned / 3 capsules, Diagnostics zero warnings; in-game test pending).
**Read first:** `branches/clothing/_branch.md` · trunk › `trunk/tool-pitfalls.md` §1

---

## File contract (vanilla)

- Cloth is a **separate `.yld`** file **next to** the drawable, with the same name: `csb_bride.ydd` + `csb_bride.yld`, `uppr_000_u.ydd` + `uppr_000_u.yld`. It is not inside the `.ydd` and not in the ped `.yft`.
- Inside the `.yld`: `Controller Type = 2` (env cloth in a `.yft` is `3`), `BridgeSimGfx`, `VerletCloth1`, bone weights (`BoneIDs` + 4-wide `BoneWeightsIndices`) and a Bound Composite with **Capsule-only** children.
- The shader of the fabric faces is **`ped_cloth.sps`**; the rest of the body is `ped.sps` (csb_bride: hash 2AAAA841 / 203B2307).
- `csb_bride`: 254 sim vertices, 24 pinned, 4 capsules, 7 bones (Pelvis, Spine0-3, two Thighs).

## Sollumz workflow (from the source)

1. **Two meshes:** the visible garment mesh (DRAWABLE_MODEL, normally weight-painted) + a separate, low-resolution **sim mesh**. The sim mesh has `sollum_type = Character Cloth Mesh` and is a **child of the drawable** (the drawable is a child of the Drawable Dictionary). **It has no material.**
2. ⛔ **Sim mesh ≤ 254 vertices** (`CLOTH_CHAR_MAX_VERTICES = 254`); above that it prints an error and the cloth is **not exported**. For a cape a 12×18 grid = 216 is enough.
3. **Every vertex** of the sim mesh is weighted to a bone vertex group — not only the pinned ones. A vertex without a group falls to root and gives a warning. Cape: the pinned row `SKEL_Spine3` 1.0, the rest decreasing towards Spine3/Spine2.
4. Edit Mode → sidebar **Sollumz Tools → Cloth Tools**: select the top row → **Pin**. `Pin Radius → Fill Gradient` gives a soft binding that fades away from the pins. `Vertex Weight` (0.00001–1.0) is mass. The attributes are written to the mesh as `.cloth.pinned`, `.cloth.weight`, `.cloth.pin_radius`, `.cloth.inflation_scale`.
5. **Collision:** a Bound Composite as a **direct child** of the sim mesh, with **only Bound Capsules** inside; each capsule tied to a bone (Spine, Pelvis, Thigh) with a `Copy Transforms` constraint. A non-capsule type → "Only BOUND_CAPSULE type is supported".
6. **Bind the visible mesh:** the vertices that should follow the fabric go into a **vertex group named `CLOTH`** (weight 1.0). The export binds these vertices barycentrically to the sim triangles; if the distance to the sim surface is **> 0.05 m** you get "Failed to bind N vertices" — the visible mesh must sit on top of the sim mesh.
7. The material of the faces in the `CLOTH` group must be the **`ped_cloth`** shader; otherwise "using non-cloth material… will not be skinned correctly".
8. Drawable Object Properties → **Character Cloth** panel: `Weight`, `num_pin_radius_sets`. (`wind_scale` and `pin_radius_scale` are hidden because they are overwritten at runtime.)
9. Export: a Drawable Dictionary export gives a `.ydd` + a **`.yld`** with the same name (`make_bundle(dwd, ("", cld))`). Cloth name = drawable name (the `.001` suffix is dropped).
10. **Verification gate:** Cloth Tools → **Diagnostics → Refresh**: fix everything other than "No material or binding errors.". Then dump the `.yld` with `res_to_xml.ps1`: are `VertexCount`, the pinned count and the capsule count what you expect?

## Headless build (measured, 2026-09)

The Sollumz API runs without opening Blender, via `blender.exe -b --python make_cape.py`; the template script
belongs to the project, not to `sources/`, but the skeleton is:
`create_armature_parent(name, try_load_asset(freemode.yft))` → DWD armature · `create_empty_object(DRAWABLE)` →
`create_blender_object(DRAWABLE_MODEL, mesh)` + `sz_lods.high.mesh` + `add_armature_modifier` · sim mesh
`create_blender_object(CHARACTER_CLOTH_MESH)` + `mesh_add_cloth_attribute(PINNED/VERTEX_WEIGHT)` ·
`create_empty_object(BOUND_COMPOSITE)` → `create_blender_object(BOUND_CAPSULE)` + `create_capsule(axis="Y")` +
`rotation_euler Z=-90°` (capsule Y onto bone X) + `add_child_of_bone_constraint` · export
`export_context_scope(ExportContext(name, ExportSettings(targets=(AssetTarget(NATIVE, GEN8),)))) → export_ydd(dwd).save()`.
- ⛔ **Give the capsule a collision material** (`create_collision_material_from_index(0)`), otherwise it prints a warning and writes **0 capsules** to the `.yld`.
- **The texture name comes from the base name of `image.filepath`** (not `image.name`). Copy the file as `accs_diff_000_a_uni.dds` and point `filepath` at it.
- Normal + spec are embedded in the `.ydd` with `texture_properties.embedded = True`; diffuse is not embedded and comes out separately as `<pack>^accs_diff_000_a_uni.ytd` via `dds_to_ytd.ps1`.
- Freemode `SKEL_Spine3` head = (0, 0.032, 0.283) in ped space; the cape's top edge sat on it with `(0, -0.17, +0.09)`.

## Packaging (freemode add-on garment)

`stream/`: `<pack>^accs_000_u.ydd` + `.yld` + `<pack>^accs_diff_000_a_uni.ytd` + `<pack>.ymt`
(CPedVariationInfo: `availComp` 12 slots, accs = slot 8; on the drawable **`clothData/ownsCloth = true`** — the cloth
only loads in game with it). ShopPedApparel `.meta` via `data_file 'SHOP_PED_APPAREL_META_FILE'`.
The `.ymt` is compiled from XML with `meta_xml_to_bin.ps1` (`.ymt` support added 2026-09) and read back with `res_to_xml.ps1`;
`dlcName` shows as a hash in the read-back — compare it with `joaat(dlcName)`.

## Pitfalls
- Freemode cape = the `accs` or `jbib` component; the `.yld` goes in the same folder, with the same name as the `.ydd`.
- The sim mesh is at the same origin as the drawable, in armature space (`parent_matrix = Identity`).
- The weight rule holds here too: ≤ 4 bones per vertex, total 1.0.
- `res_to_xml.ps1` reads `.yld` and `.ymt` (added 2026-09); `extract_asset.ps1 -Pattern '*.yld'` run without a filter falls over with a StackOverflow before it reaches the DLCs — give `-PathFilter`. For a single `dlc.rpf`, `RpfFile(path).ScanStructure()` + recursion over `Children` is enough; do NOT ADD an RSC header to an RBF file (`mp_creaturemetadata_*.ymt`) — it breaks.
