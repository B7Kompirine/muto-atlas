# GTA V fundamentals — the engine's own rules

**Trunk file.** This holds the engine's core rules that apply **in every branch and every
leaf**: data model, file types, name/hash system, coordinates,
**texture and DDS**, streaming, resource format, client/server split. These are
not "our method", they are **the game's own contract** — a branch cannot change them,
it can only put its own rule on top.

Every number here is a measurement; its source is written on its line. Working discipline and
tool behaviour are separate: `SKILL.md` and `trunk/tool-pitfalls.md`.

---

## 1. Data model — three separate things, do not mix them up

In GTA "an object" is not one thing. There are three layers and each lives **in a separate file**:

| layer | file | what it says | if you change it |
|---|---|---|---|
| **archetype** | `.ytyp` | **what** the object is: model name, bbox, `lodDist`, flags, `specialAttribute`, physics/texture dictionary, extensions | **every place** that uses that model is affected |
| **entity** | `.ymap` (or the MLO's own list) | **where** the object is: position, rotation, `lodLevel`, `parentIndex`, entity flags | only that placement |
| **drawable** | `.ydr` / `.ydd` / `.yft` | **how the object looks and its physics**: mesh, material, embedded texture, skeleton, bound, light | visuals + physics |

Consequences:

- A prop "being a door" is not in the drawable but in the **archetype** (`specialAttribute`).
  Changing the model does not make a door; the ytyp is fixed.
- Removing an object from the map is **entity** work; the archetype is not touched.
- The same archetype can be in N places on the map (`assetdb.py where`); fixing the ytyp
  affects all N places at once — **measure** the scope of effect **first**.
- **An MLO interior is separate:** its entity list is not in a ymap but **inside the ytyp**;
  a prop placed from outside with a ymap is culled by the room/portal system.
- The archetype name is inside the `.ytyp`; an entity binds to it with `archetypeName` **through
  the hash** (§3). If the name does not match, the entity silently never spawns.

## 2. File types — which extension carries what

| extension | what | binary writer | note |
|---|---|---|---|
| `.ydr` | drawable — mesh + material + embedded texture + light + bound | Sollumz `NATIVE` | single model |
| `.ydd` | drawable **dictionary** — several drawables | Sollumz | ped components, LOD children |
| `.yft` | fragment — skeleton + `PhysicsLODGroup` (breakable / per-bone collision) | Sollumz | ⛔ a ped `.yft` ships **without physics** |
| `.ybn` | separate collision (bound) | Sollumz | map collision lives here |
| `.ytd` | texture dictionary | `dds_to_ytd.ps1` | §5 |
| `.ycd` | clip (animation) dictionary | ⛔ **Sollumz writes XML** → compiled to binary separately | outside the format system |
| `.yed` | expression dictionary — rule-based bone motion | ⛔ Sollumz cannot write it; CodeWalker **reads, cannot write** | |
| `.ytyp` | archetype definitions (+ MLO rooms/portals, `compositeEntityTypes`) | `meta_xml_to_bin.ps1` (`MetaFormat.RSC`) | ⛔ `YtypFile.Save()` drops the composite |
| `.ymap` | entity placements (+ grass batch, car generator) | same | |
| `.ypt` | particle effect | `ypt_xml_to_bin.ps1` | ⛔ the CodeWalker XML round trip does not write `FxcFileHash`/`VFT` |
| `.yld` | Sollumz supports it — **we have no measurement** | — | do not claim, measure |

Sollumz was measured to write binary for **8 extensions** (`.ybn .ydr .ydd .yft .yld
.ytyp .ymap .ytd`, when `pymateria` is installed); `.ycd` is outside this system.
Details: `trunk/tool-pitfalls.md` Detail B.

## 3. Name and hash — everything binds through joaat

- The engine hashes names with **joaat (Jenkins one-at-a-time)**; in most places the files
  hold not the name but **the hash**. The binding is made by hash, not by name.
- **CodeWalker writes a name it does not know as `hash_XXXXXXXX`** — this is not "broken", it is
  an *unresolved* name. Compute the joaat of stream file names / known names and
  match them; write a new name as **plain text**, the compiler hashes it.
- ⛔ **Asset names have no uppercase letters.**
- ⛔ **A name collision is silent:** of three `.ytyp` with the same name only one loaded;
  two textures with the same name carry different content in different dictionaries (22 of 175 copies).
  Every ytyp/texture/clip name you produce must be **unique**.
- A `.ycd` clip is **found by `<Hash>`**, not by name: if the field is empty the clip has no
  name, `TaskPlayAnim` cannot find it and raises no error either. That is the engine's contract;
  which tool fills this field and which does not → `trunk/tool-pitfalls.md` §1.

## 4. Coordinates, units, direction

- **1 unit = 1 metre**, the world is **Z-up**, right-handed.
- **A ped faces −Y** (in rest pose); **in clip space forward is +Y**.
  If the model faces backwards the mesh is turned 180° on Z — the checks pass, the ped walks
  backwards in the game.
- **Bone space ≠ model space.** A light's `Position/Direction/Tangent`, the offset of a prop
  attached to a ped, a fragment bound — all of them are **in bone space**.
- **An attached object is positioned from the object's ORIGIN**, not from its skeleton →
  the alignment is baked into the model.
- **`CreateObject` places at the collision-bound BASE, `CreateObjectNoOffset` at the ORIGIN**.
- The Blender side is a separate space: in Sollumz bones local Y = head→tail;
  an FBX armature carries 90° X + 0.01 scale → compare **in world space**
  (`matrix_world`).

## 5. Texture and DDS — the engine's hard rules

**This section holds in every branch**: map, prop, weapon, ped, clothing, particle,
decal, light projection. Measured: 400+ vanilla material `.ytd` / 1,135 textures,
plus the 107 embedded particle textures of `core.ypt`.

### Format
- ⛔ **DDS required. PNG/JPEG are not accepted.** Given PNG packed data, Sollumz says
  *"packed data is not in DDS format"* and **skips** the texture —
  the `.ytd` comes out ~300 bytes (empty), export raises no error.
- ⛔ **Sollumz packs the embedded texture FROM THE DDS ON DISK.** Loading it inside Blender
  and doing `scale()`/`save()`/`pack()` is not enough: a **16×16 placeholder** was embedded
  in the `.ydr`, no error came up, the defect only showed on read-back. Do the pixel work
  outside Blender (Pillow `pixel_format='DXT5'`).
- **The embedded texture name comes FROM THE FILE NAME**; assigning `img.name` is ignored.

### Size
- ⛔ **Both edges must be a power of two** (2/4/…/1024/2048/4096).
  Otherwise the texture **flickers**. Rectangles are free — `4096×256` works.
- Measured median: diffuse/normal/spec **all three at 512**, maximum 2048.
- **There are also places that need a square:** the ped `_r` (skintone) spec mask
  must be square — `1024×512` stretches the UV and breaks the skin colour.
- If a bake output was produced at the aperture's ratio (such as `1024×442`) it is **rescaled**;
  a square render + a rectangular aperture stretches the black border inwards.

### Compression and mips (measured)
| map | vanilla distribution | rule |
|---|---|---|
| normal | DXT1 278 · DXT5 18 · ATI2 6 | **DXT1** (92%) |
| spec | DXT1 98 · DXT5 1 | **DXT1** (99%) |
| diffuse | DXT1 570 · DXT5 161 | **DXT1** without alpha, DXT5 with alpha |
| particle | DXT5 75 · DXT1 32 — **107/107 DXT** | **no** uncompressed/single-mip sample |

- **A mip chain is required:** `log2(short edge) − 1`, ends at 4×4 (832/921 = 90.3%).
  A single-mip texture does not exist in vanilla.
- ⛔ **DXT1 carries no alpha.** If a holed/cutout texture is written as DXT1 **the holes
  close** — valid file, valid texture, no error. If alpha is needed, DXT5
  or `A8R8G8B8`.
- **Normal and spec maps are `Non-Color`**; read as sRGB, the bump direction and
  glossiness come out silently wrong.

### Dictionary (`.ytd`) and embedded texture
- ⛔ **`.ytd` XML schema:** **`<Item>` directly** under `<TextureDictionary>`;
  there is **no** `<Textures>` wrapper. The wrong wrapper raises no error,
  it produces **a 57-byte empty dictionary** — the only symptom is the file size.
- **Embedded or in a dictionary depends on the branch:** vanilla map models have **no**
  embedded texture (external dictionary + `gtxd.meta` chain); in freemode clothing
  spec+bump are embedded, **diffuse is not** (so it can change in game);
  a non-streamed ped has **no embedded texture at all**. The same layout works for your own streamed ped: no embedded texture in the drawable, sampler
  names follow the rule (`uppr_diff_000_a_uni`, `uppr_normal_000`, `uppr_spec_000`), textures in `<ped>.ytd`.
  Measured: 2026-09-11, 1 game test — a ped streamed in place of `a_m_y_beach_01` (DXT1 diffuse + flat normal/spec): the texture showed with the right colours, no F8 error.
- If the archetype does not reference the `textureDictionary`, the game **never loads** that
  dictionary — the light seems to "work", there is no projection pattern.

### Tools
`make_dds.py` (DXT5 + mips; forces alpha for particle sprites) ·
`bake_to_gta.py` (PBR → GTA; material maps are opaque, no forced alpha) ·
`dds_to_ytd.ps1` (folder → `.ytd`, **reads back**) · `ytd_index.ps1` / `ytd_find.ps1`
(vanilla texture dictionary index).
- **Pillow's DXT encoder is not the quality ceiling.** Per-block principal-axis range fitting + one least-squares pass (pure numpy,
  also runs in Blender's Python — Pillow is not there) gave better output in every sample. Measured: 2026-09-11, Pillow 12.3, decoded with Pillow, PSNR —
  vanilla `a_m_y_beach_01` diffuse 512² ×3: Pillow DXT1 42.9–44.6 dB, numpy 45.3–46.7; spec DXT5 alpha 45.8 → 69.8; 1024² with mips 0.6–0.8 s.
  Sollumz 2.9 packs a DXT DDS into the `.ytd` as is (the payload extracted on read-back is byte-for-byte the same).
- ⛔ **In DXT1, `c0 <= c1` puts the decoder into 3-colour mode: index 3 = transparent black** (BC1 format definition). In a single-colour
  block both endpoints come out equal → sort the endpoints (the larger one is `c0`), and if equal write all indices as 0. Test your own encoder with a flat colour: in the 2026-09-11 measurement
  32² 0.5 grey → largest deviation 4 in the Pillow decode (565 quantisation, 37.3 dB for both encoders), black pixels 0.

## 6. Streaming and resources

- Files in `stream/` stream **automatically**; ytyp/ymap/meta must be declared
  in `fxmanifest.lua` with **`data_file`**
  (`DLC_ITYP_REQUEST`, `TIMECYCLEMOD_FILE`, `WEAPONINFO_FILE`, …).
  The game **never looks for** a file that is not registered.
- ⛔ **Asset changed → leave the server and reconnect.** The stream is cached,
  `restart` is not enough.
- ⛔ **A broken stream asset silently drops the WHOLE resource**:
  the server prints "Started resource", no command registers on the client, F8 shows
  no error. If commands suddenly vanished, look at `stream/`, not at the Lua.
- ⛔ **If the same file is in two folders, FiveM silently ignores one** →
  when "it does not show" the first place to look is **the server log**.
- **A vanilla file has more than one version** (base + `patchdayNNng` +
  DLC). Which one loads depends on DLC order and **cannot be read from the
  files** — the conflict is not hidden, it is **reported**. The `hei_` (mpheist) twins
  are the most common case: that one is what actually loads.
- The stream files of an escrowed (`.fxap`) resource are **encrypted**; if you copy them
  the client crashes.

### Pool overflow — the number one cause of crashes

- ⛔ **Hard ceiling: 65535 stream files in total on the server.** Past it,
  `ERR_STR_FAILURE: trying to add more assets to pgRawStreamer` is **fatal**.
  This number **cannot be raised by any setting**; the cure is merging assets.
  It is measured with `assetscount` in the client console (F8) — **it is not a server command.**
- **Pools are enlarged in `server.cfg` with `increase_pool_size`.** The old
  "gameconfig.xml fix" resources are **now the wrong answer**: FiveM ships and verifies its own
  `gameconfig.xml` and writes back a hand-edited one.
- ⛔ **The lines must be at the VERY TOP of the file, before the first `ensure`/`start`.**
  Once resources have started, pools cannot be changed; if the line slips down it
  stays **silently ineffective**.
- ⭐ **The valid criterion is not the documentation but the server itself.** When a limit is
  exceeded the console prints `Requested pool size increase is invalid: ... exceeds allowed limit of N`
  and that line is dropped, the others apply. **Measured (2026-09, build 3258):**
  the docs say 20000 for `Building`, **the server said 500**. After writing the value, search the
  console for `pool`; if there is no warning it was accepted.
- ⚠️ When a pool line changes the player must **fully close and reopen the game, not
  reconnect** (behaves like `sv_enforceGameBuild`).
- ⚠️ Raising `FragmentStore` is currently **not applied** (open Cfx bug #3812).
- Accepted values measured (same install): `TxdStore` 26000 ·
  `EntityDescPool` 20480 · `AnimStore` 20480 · `StaticBounds` 5000 ·
  `Object` 2000 · `fragInstGta` 2000 · `InteriorProxy` 450 · `Building` 500.

### Diagnosing a crash

- The crash window gives a **two-word signature** (such as `october-michigan-lithium`) + often
  `module.dll+offset`. The same crash **always produces the same signature**.
  The official table that turns the signature into plain language:
  <https://github.com/citizenfx/fivem/blob/master/data/client/citizen/crash-data.json>.
- Dumps are in `%localappdata%\FiveM\FiveM.app\crashes\`. For a full dump,
  `EnableFullMemoryDump=1` in `CitizenFX.ini` (1-10 GB; **delete** it when you are done).
- **There is no automatic answer to which asset caused the crash.** The method is elimination
  by halving (remove half of the `stream` resources, repeat).
- Hard crashes come from: **an invalid TXD reference**, **broken cloth data**,
  a broken `.ytyp` (`CDLCItypFileMounter` during unmount). By contrast,
  missing collision, a texture not in the `.ytd`, an unregistered archetype are **silent
  invisibility** — not a crash. Do not confuse the two.
- Instead of lining up 500 props by script, **use a `.ymap`**: a ymap entity uses not the `Object`
  pool but `Building`/`EntityDescPool`, and needs no network sync.
- `SET_ENTITY_DISTANCE_CULLING_RADIUS` and its siblings are **officially
  deprecated**, described as "known, unfixable issues" — do not use them.

**Measured:** one test server, 2026-09-08, FXServer build 3258, 2.1 GB / 2140 stream
files / 78 resources. Sources: `docs.fivem.net/docs/server-manual/server-commands`,
`citizenfx/fivem` issue #3812 · #3384, forum 5385215.

## 7. Resource format (RSC7)

- Binary `.y*` files are an **RSC7** shell and are **zlib-compressed**.
- ⛔ **File size is NOT a validity criterion** — an unpacked 32,768-byte
  `.ypt` became 3,077 bytes when saved; 15,056 → 15,904 bytes is the same content.
  **The only valid criterion is reading back.**
- Re-exporting can grow a file by 20–30%; this is not a defect.
- When starting on a new resource type, the first job: **dump a vanilla file to XML, read it
  back and compare the binary and the XML round trip field by field** — only this way do you see
  which fields the tool drops silently.

## 8. Client / server

- **Map objects are NOT networked.** State is kept on the server and every client applies it
  to its own copy; otherwise it moves only for you.
- Before animating an entity, **ownership**: `SetEntityAsMissionEntity` +
  `NetworkRequestControlOfEntity`; without it `Freeze`/`SetCoords`/`SetHeading`
  are **silently ignored**.
- **DUI/NUI is client-side and not synchronised**; the page's JS is readable,
  its messages can be forged → password/code/price comparison **on the server**.
- Particles, decals and Euphoria reactions are **visual and per client**;
  the server decides the outcome (damage, death, lock).
- A native's side is not guessed, it is queried (the `fivem-natives` skill).

## 9. Render bucket and vertex format

- **A `.sps` selects two things: the shader PROGRAM and the RENDER BUCKET.** The bucket is a
  separate field and **can be written** — you are not stuck with what the `.sps` preset brings.
  Buckets: `OPAQUE / ALPHA / DECAL / CUTOUT / NO_SPLASH / NO_WATER / WATER /
  DISPLACEMENT_ALPHA`. ⛔ **The opaque bucket never reads alpha** (`emissive_clip.sps`
  is OPAQUE → holes close). A decal embedded in the map is **bucket 2**.
- ⛔ **The name written into a `.ydr` is not the `.sps` file name but the PROGRAM name**
  (`emissive_alpha.sps` → `emissive`). Comparing the hash with the file name is a
  wrong diagnosis.
- Vertex format `GTAV1`: Position, BlendWeights, BlendIndices, Normal,
  Colour0, TexCoord0, Tangent. **Geometry count = material count.**
- **A `Color 1` vertex colour layer is required** (a mesh coming from OBJ has none at all):
  the engine masks natural/artificial ambient with `.r`/`.g`, and `decal.sps` reads its blend
  factor **from its alpha**. In Blender `.color` decodes gamma →
  **`.color_srgb`**. Vertex colour darkening applies only to **bucket 0**
  geometry.
- **The UV layer's name is `UVMap 0`** — any other name is silently dropped. Terrain blending
  also wants `UVMap 1`; on ped clothing `UVMap 1` **is the blood map**, do not touch it.

---

## What goes in this file, what does not

**In:** the engine's contract that holds in every branch — data model, file/name/hash,
coordinates, texture, streaming, resource format, client/server, bucket.

**Out:** a single tool's behaviour (`tool-pitfalls.md`), our working
discipline (`SKILL.md`), a rule specific to one category (`branches/<branch>/_branch.md`),
a recipe specific to one task (leaf). If an item reads "holds only in branch X",
it does not belong here but to that branch.
