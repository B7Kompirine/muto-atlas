# Map — branch rules

Command: `/map`
**Keywords:** ymap, ytyp, MLO, interior, vanilla part replacement, road, bridge, building, tower, wall, destruction, breaking, make it break, collapse, break apart, explosion of a structure, debris, RayFire, des_, composite, LOD, lodDist, SLOD, disappears at distance, ghost copy, extent, hei_, patchday, overlay, decal layer, ybn, collision, grass, fur grass, @ma, grass batch, terrain, procedural, interior measurements, chamfer, bevel, shadow mesh
**What belongs here:** Everything that sits **FIXED in the world** — ymap/ytyp/MLO, interiors, road · building · bridge · wall, grass, LOD, and their **destruction/collapse**. Boundary: a portable object that can be picked up on its own → `/prop`.

> The keywords above are **accelerators, not an exhaustive list.** If a word is not in the list,
> routing does not stop — check this definition. *“roller shutter”* is not in the list, but it is a door object.


## Rules that hold for every leaf in this branch

Every item was measured in game (Fleeca MLO, hw1_27 crane, dt1_rd1 freeway, des_stilthouse/crane/bridge,
v_coroner/abattoir). A project name is a source note, not a rule.

### Two questions first
- **Inside the MLO or outside?** **A prop cannot be placed inside with a ymap** (the room/portal system culls it, the object never appears);
  the only way is the MLO's own entity list. Outside, a ymap works. Do not let a reference resource that uses a ymap
  mislead you — first check whether the coordinate is inside the MLO (`assetdb.py where`).
- **An object spawned by script is not a map object**: the door system cannot find it, fragment
  collision does not follow the animation, and it is a separate load on every client.

### MLO
- The same interior can have **more than one MLO version** (Fleeca: `v_genbank` + `hei_generic_bank_dlc`,
  same local frame, different entity lists) — **patch all of them**.
- MLO entity flag **18350080**; given the ymap value `1572872` the object is silently not created
  (bit 8 says "LOD in parent map"; with no parent map the entity is dropped). Decode: `assetdb.py flags <n> --entity`.
- A new entity **is attached to a room** (`AttachedObjects`); forget it and it is invisible, and the MLO can break. `lodDist -1`.
- A vanilla file replacement **does not get** `DLC_ITYP_REQUEST`; your own new ytyp does.
- Patches stack: every script continues from the **output folder**, not from the vanilla RPF.
- Your own drawable renders **pitch black with `trees_normal.sps`** inside an interior → `normal.sps`.

### When touching a vanilla part
- **Do not delete, move it down** (`z -= 600`); deleting shifts indices and `parentIndex` values point at the wrong entity.
  Deleting an object from inside a `.ydd` also breaks the properties of the other objects.
- ⛔ **Do not touch the extent** — enlarging the streaming volume removed collision across the whole map.
- **The whole LOD chain** (`X_strm_N` → `X` → `X_lod`) **and the `hei_` twins** — with mpheist active the `hei_`
  copy is what loads; patching the base gives "clean up close, still there from afar".
  SLOD2 often cannot be hidden (15 children) → model surgery.
- **Count every entity in the footprint**: road = `_rd_NN` surface + `_ovly_NN` overlay + `_rd_NN_ov` decal;
  the decal stays in the same plane → Z-fighting; if `_ovly` is not removed, the lines hang in the air.
  ⛔ **The `_ovly` number may not match the road number** — the overlay of `hw1_rd_02_25` is `hw1_rd_02_00_ovly`
  (same position, bbox 100%); `hw1_rd_02_25_ovly` is 185 m away, 0% overlap. Match a decal **by entity position +
  bbox intersection, not by name**. A region decal (`X_glue*`) also climbs the walls of neighbouring buildings;
  if those buildings are gone it looks like a wire cage in the air. (measured: hw1 6 parts / 12 candidate decals, 2026-09-10)
- **Textures are not in the model** — external dictionary + `gtxd.meta` parent chain; the same texture name carries
  different content in different dictionaries (22 of 175 copies) → do not pick by size; pick in GTA's resolution order.
- ⛔ **The same ymap is in more than one RPF, and the versions differ.** `-Flatten` silently leaves the wrong version;
  the right source is usually `patchday27ng` / `update.rpf/dlc_patch/mpheist`. If other resources stream the same
  ymap, which one wins is undefined — list the conflict first.
- Collision is in a separate `.ybn` (`physicsDict 0`); find the file that covers the target with `BoxMin/BoxMax`.

### When writing your own ymap
- The extent is computed **from the union of the entities**; an entity left outside is silently invisible.
  The archetype box also covers **the whole** animation. `guid` is deterministic with Jenkins.
- There are two ways to write a ymap, and which one is lossless depends on the file; do not call `CalcFlags()`,
  do not use `CalcExtents()`, do not write `CEntityDefs` directly (`trunk/tool-pitfalls.md` §3).
- HD entity flag `1572872` = LOD in parent map + shadows; parent index is **0-based**, `-1` ends the chain;
  each level's `childLodDist` is the `lodDist` of the level before it. The benchmark is vanilla: `lodaudit`.

### Destruction (RayFire)
- `des_X` is a **director**, not an archetype: `StartImapFile` turns off → the engine creates the `AnimatedModel` →
  clip → `EndImapFile` turns on. What you see is **three separate assets**. The animated drawable is in no ymap.
- **NO collision during the animation**; collision belongs to the state. Script tricks backfire here too.
- **Clip name = model name = archetype name** (the "must differ" rule of the `.yed` chain does not carry over here).
- **Permanent geometry goes in the placer ymap**, only the collapsing slice in `start`; otherwise the whole area becomes a hole.
- Bone flags: root `4215`, the others `119`; the `.ycd` covers the whole skeleton, root included, three tracks.

### Grass / collision
- **Grass is four separate systems** (flat texture · grass prop · fur grass · `@ma` procedural · grass batch) — **ask** which one.
- `@ma` procedural is only added to **existing** collision; the polygon must be **big** enough.
- "Grass does not show" → first the **Grass Quality** setting (Ultra).

## Leaves

| wanted | file | status — source |
|---|---|---|
| Replace a vanilla part with my own model (road, prop, structure) | vanilla-part-replacement.md | measured — former vanilla part replacement reference |
| Destruction / collapse / choreographed scene — single leaf | destruction.md | measured — former RayFire reference (2.5.0) |
| Swap an MLO object (entity swap) | mlo-object-swap.md | measured — former MLO object swap reference · old SKILL |
| Put your own prop / drawable into an MLO | mlo-props.md | measured — former MLO prop pipeline · MLO drawable export notes |
| LOD chain — flickers / disappears at distance | lod.md | measured+video — former ytyp/ymap reference §9 · former video notes 08 §8 |
| Vanilla interior measurements | vanilla-interiors.md | measured — former vanilla interior measurement notes |
| Grass / procedural ground / terrain | grass-procedural.md | video+data — former video notes 08 §1-7 |

## Trunk files to read
- `trunk/flags.md` — entity/archetype flags, `specialAttribute`, extensions
- `trunk/tool-pitfalls.md` §3 CodeWalker (writing ymaps, `MetaHash`, `BoxMin`), §4 PowerShell (`-Flatten`, `[script]`)
- `trunk/verification-ladder.md` — checking ymap/ytyp without entering the game
- `scripts/mlo_local_to_world.ps1` — converts an MLO-local coordinate to **every** world placement (Fleeca 6 branches; same math as `build_entities.ps1`)
- Lights/timecycle/parallax: `branches/look/_branch.md`
- Looking for a ready template / tool (LOD templates + `nametables.rpf`, Arbolito, VichoTools, `str_enableFlush`, interior reference libraries, `Procedural_IDs.txt`) → `sources/community-resources.md` §6, §10, §12 — **source note, not a rule.**
