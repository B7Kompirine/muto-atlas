---
name: fivem-assets
description: GTA V / FiveM asset data and measured production rules — props, objects, doors, ytyp/ymap/MLO, LOD, grass, flags, particles (.ypt), shader/texture/light/timecycle/decal/parallax, clothing, vehicles; vanilla animation name and bone tag lookup. Use it to look at the real data BEFORE WRITING CODE in any prop, door, map, effect or look task, even if the user does not ask. Triggers — model name (prop_*, v_ilev_*, des_*), door does not open, object does not move, AddDoorToSystem, TaskPlayAnim, anim dict, bone tag, specialAttribute, flag number (1572872), LOD, disappears at distance, fxName, StartParticleFx, light does not turn on, TimeFlags, dark interior, timecycle, decal, parallax, DUI screen, fragment, RayFire destruction, freemode clothing, handling, modkit, Sollumz, CodeWalker. Use for GTA V / FiveM props, doors, maps, particles, materials, lights and clothing.
license: MIT
compatibility: Python 3.10+. Windows PowerShell 5.1 runs the .ps1 build scripts. Data layers are built from your own GTA V install with CodeWalker.Core (scripts/setup.py). The scripts live at the muto-atlas repository root, outside this folder - outside Claude Code install with scripts/install_skills.py or use scripts/mcp_server.py.
---

# FiveM Asset Data — trunk

This file is the **trunk**: the rules that hold in every branch, and the map of the tree.
Details are in the branch and leaf files; from here you are only **routed**.
A fact is written once, in the widest place where it holds.

## TREE — trunk / branch / leaf

- **Trunk** — this file + `trunk/`: **GTA V's own rules** (data model, file
  types, hash, coordinates, **texture/DDS**, streaming, resource format, client/server),
  our working discipline, tool pitfalls, verification ladder, flags, bone tags.
  **Criterion:** an item that does not hold in every branch and every leaf does not go in the trunk.
- **Branch** — `branches/<branch>/_branch.md`: the category's broad rules + the leaf list.
- **Leaf** — `branches/<branch>/<leaf>.md`: only what is specific to that task.
  A leaf is defined by *the thing wanted*; "road destruction / bridge destruction / explosion" is one leaf.

**Use:** when a topic comes up, open the branch first (`_branch.md`), then a single leaf.
Do not scan every file; keyword → branch → leaf.

| branch | command | file | keywords |
|---|---|---|---|
| Map | `/map` | `branches/map/_branch.md` | ymap, ytyp, MLO, vanilla part, destruction, RayFire, LOD, extent, grass |
| Prop | `/prop` | `branches/prop/_branch.md` | prop, door, does not move, fragment, raw pack, DUI, NUI HUD, ox_target |
| Clothing | `/clothing` | `branches/clothing/_branch.md` | clothing, freemode component, skintone, ped prop, hat |
| Particle | `/particle` | `branches/particle/_branch.md` | ptfx, .ypt, effect, smoke, flipbook, emitter, catalog |
| Look | `/look` | `branches/look/_branch.md` | shader, texture, parallax, light, TimeFlags, decal, timecycle, emissive, bake |
| Vehicle | `/vehicle` | `branches/vehicle/_branch.md` | vehicle bone, handling, modkit, siren |

The full keyword list is at the top of every `_branch.md`.

### ⛔ Route by CLASS, not by KEYWORD

Keywords are **an accelerator, not a dictionary.** The set of words is infinite
(*roller shutter · sign · fountain*), the set of classes is closed: **6 branches.**

1. If a keyword matches → the branch is known, open it.
2. If none matches, **do not stop**: look at the **`What belongs here:`** definition at the top of
   `branches/<branch>/_branch.md` and **classify** the sentence.
   *"Make the roller shutter open"* → a roller shutter is a door object → `/prop`.
3. Adding a keyword to the list is **the exception**: only for a term that comes up often and
   cannot be inferred from the definition. Do not add every word — the list bloats.

If the class definition does not settle it either → **ask.**

## TRUNK FILES

| file | when |
|---|---|
| `trunk/gta-fundamentals.md` | **the engine's own contract** — archetype/entity/drawable split, file types, joaat, coordinates/units, **texture and DDS rules**, streaming, RSC7, client/server, render bucket |
| `trunk/tool-pitfalls.md` | Sollumz · Blender · CodeWalker · PowerShell · Python/Lua · FiveM runtime — when a tool behaves unexpectedly, **come here first** |
| `trunk/verification-ladder.md` | verifying an asset without taking it into the game: measure in Blender → read back → CodeWalker headless → render → GUI → game |
| `trunk/flags.md` | ytyp/ymap/collision flags, the 21 `specialAttribute` values, 14 extension types, nametables |
| `trunk/bone-tags.md` | vehicle / weapon / ped bones: **is the name fixed or the tag fixed** |
| `sources/external-tools.md` | *(not a rule, source note)* the measurable part of external tools; [verified]/[refuted] labels; tool inventory |
| `sources/community-resources.md` | *(not a rule, source note)* full dump of the Sollumz Discord `#resources` — index of ready-made templates/rigs/tools, `bloodfx.dat` fields |

## ⛔ IF DATA IS MISSING, DO NOT GUESS

Every answer rests on the `data/` layers. If a layer is missing, the query returns **exit 2**;
at that point the only thing to do is **stop**:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --plan   # shows the state, writes nothing
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py"          # installs the missing layers (/asset-setup)
```

Exit codes: `0` found · `1` the query ran, **the name is not in the authority** · `2` **the layer
is not installed** — says nothing about the result · `3` internal error, not "absent".
Confusing `2` with `1` means reading a "0 results" that came from a missing layer as
"does not exist in the game".

## CORE RULE — data first, code second

Before writing code about an object/prop/door/animation, look at that asset's data.
Real case: four natives were tried in turn on the Fleeca teller door `v_ilev_gb_teldr`;
the answer was in one line of the ytyp — `specialAttribute = 0`,
i.e. not a door. `assetdb.py door v_ilev_gb_teldr` would have said so from the start.

## WORKING DISCIPLINE — in every branch, with every tool

1. **Measurement > guess.** A number (tag, flag, duration, lodDist, `fxName`) is not guessed,
   it is queried. A number from an external tool is **a claim**; without a `[verified]`
   label, measure it first (`sources/external-tools.md`).
2. **A tool not showing something does not mean that thing is absent.** CodeWalker cannot
   write `.yed` bytecode, PowerShell returns `$null.Length=0` on a property that does not exist,
   Sollumz imports a binary "in 0.0 seconds" — all three were taken for "absent".
3. **A tool raising no error does not mean the work is right.** Nearly all the bugs in this
   repository are silent: the file is created, it says "success", nothing happens in the game.
   All of them are in `trunk/tool-pitfalls.md`.
4. **A screenshot is not a measurement.** Before saying something is broken,
   read: the pixel, the file, the read-back. (In one round the screenshot was looked at three
   times and the wrong diagnosis was made.)
5. **"The object was created, the numbers look reasonable" does not mean it works.** Numbers and
   screen are both needed; working at one synthetic point is not enough, a fix is not
   delivered before it has been tried **in the user's real situation**.
6. **Read back what you wrote.** File size is not a validity criterion (RSC7 zlib);
   the only criterion is reading back. If a script crashes midway, the next `Write` does not run —
   `cat`/`grep` before saying "written". After a copy, compare size/hash.
7. **The order of operations is part of the measurement.** Do not look at a single number but at
   **two independent numbers agreeing** (`reached` vs `target`). A number can be right while
   *when* it was measured is wrong.
8. **The reference itself can be broken.** Two independent decoders can share the same mistake;
   do not say "I measured" without comparing against vanilla.
9. **One variable at a time.** If something does not work, split the chain into parts,
   set up A/B; do not ask for a test before the chain is complete; do not jump from symptom to
   hypothesis and try things one by one.
10. **A grid can ask the wrong question** — "100/100 points filled" does not mean the place
    that was not sampled does not exist. The measurement can be right and the question wrong.
11. **A tool's constant is tuned to its own scale** — do not copy the constant, copy what it is
    normalised against (shadow bias was right for a 0.15 m prop, in a 660 m
    scene it shadowed 72% of the ground).
12. **Before guessing a field's meaning from its distribution, look at how the tool names that
    field** (`bl_rna.properties[...].enum_items`). All three guesses for `Flashiness`
    were wrong; Sollumz had a named enum.
13. **Do not write 0 into an `Unknown*` field** — look at its distribution, take the most common value.
14. **Pick a recipe and apply it to the end; do NOT HYBRIDISE two recipes.** A hybrid of two paths
    that are each correct on their own never worked. If the recipe is unclear,
    clarify it with `AskUserQuestion`.

## ENGINE INVARIANTS — whatever the branch

- **Asset changed → leave the server and reconnect.** The stream is cached, a restart
  is not enough; skip it and you test a stale asset. Remind the user before asking for a test.
- **A broken stream asset silently drops the whole resource** — no command registers on the
  client, no error. If commands suddenly vanished, look at `stream/`, not at the Lua.
  If a resource is **in two folders**, one is ignored → server log.
- **A magic number is not copied, it is decoded:** `assetdb.py flags <number> [--entity]`.
  `1572872` = LOD in Parented YMAP + Cast Static/Dynamic → for a ymap; `18350080`
  = Dont Render In Reflections + two shadow bits → for an MLO entity. Mixing them up
  silently deletes the object. → `trunk/flags.md`
- **Bone: is the name fixed or the tag?** The script side (`GetEntityBoneIndexByName`) uses
  **the name**, the file side (`.ycd`/`.yed`/`specialAttribute`) uses **the tag**.
  `GetPedBoneIndex` takes a TAG. → `trunk/bone-tags.md`
- **The bbox must cover the whole animation — in two separate places:** the `.ydr`'s own
  `BoundingBox`/`Sphere` **and** the ytyp archetype box. If one is fixed and the other
  stays at rest, the object flickers and disappears at distance.
- **`physicsDictionary` never 0** — the model is visible and you walk through it.
- **An object spawned by script is not a map object**; props are not placed inside an MLO
  with a ymap; `SetEntityCollision(false)` is unreliable on a map object.
- **`CreateObject` places at the collision-bound BASE, `CreateObjectNoOffset` at the ORIGIN** — a stale bound lifts the object into the air,
  the bound is regenerated from the visual. An attached object is positioned from its **origin**; adding a bone to a prop gives no alignment,
  the alignment is baked into the model.
- **Collision is not chased with script** — `SetEntityCollision` / `Freeze` /
  `SetEntityHeading` / `DoorSystemSetOpenRatio` break the animation chain.
- **Custom ped skeletons are forbidden**; the engine accepts only its own skeleton.
- **DUI/NUI is client-side** — password/code/price comparison happens on the server.
- **Texture: DDS required, both edges a power of two, DXT + mip chain.** PNG is skipped
  silently, a texture that is not a power of two flickers, DXT1 carries no alpha (holes close).
  → `trunk/gta-fundamentals.md` §5
- **Archetype (what) ≠ entity (where) ≠ drawable (how it looks)** — three separate files;
  fixing the ytyp affects **every place** that uses that model. → `trunk/gta-fundamentals.md` §1
- **Clip name = prop model name** (detecting an item animation). Duration is not guessed,
  it is taken from the index.

## QUERY TABLE — the user gives no command, you look

The moment the topic comes up, before writing code:

| topic | run |
|---|---|
| prop / object / door name · "door does not open" | `assetdb.py show <name>` · `door <name>` |
| where in the world · what is near me | `where <name>` · `near x y z --radius 10` |
| animation / clip · prop animation · which model plays it | `anim <query>` · `propanim <prop>` · `clipfit <dict> <clip>` |
| bone / tag / skeleton | `bones <model>` |
| ped identity (clip dictionary, expression, clipset) | `pedmeta <ped>` |
| expression / `.yed` / spring-sag | `expr <query>` · `ext <name>` |
| particle · "does this effect exist" · `fxName` | `ptfx <prop\|effect>` · `fx <name> --exact` · `ptfx --type 4` |
| flag number · ytyp extension | `flags <number> [--entity]` · `ext <name>` |
| LOD · "disappears at distance" · is something wrong with my map | `lod` · `lodchain <name>` · `lodaudit` |
| grass / ground / `Procedural ID` | `proc [<name>\|--id N]` |
| collision material | `mat [<name>\|--index N]` |
| decal by script · embedded decal shader · shader type | `decal <type>` · `shader decal` · `shader <type>` |
| light · weather · room timecycle | `light <ydr>` · `cycle w_clear --hour 20` · `timecycle <name>` |
| weapon · vehicle · MLO · IPL | `weapon <name> --parts` · `vehicle <name>` · `mlo <name>` · `ipl <name>` |
| loot/spawn point, ATM/CCTV location | `world --near x,y,z --radius 50` · `--family <family>` |
| does the model have a screen (`AddReplaceTexture`) | `screentex.ps1 -Model <name> -All` |
| native name / signature / side | the `fivem-natives` skill (`/native`, `/native-lint`) |

All of them are `python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" <subcommand>`. Summarise the
result in a sentence or two, then move to the code. The index is built from the vanilla RPFs + the
server's own ytyps; rebuilding it is `/asset-build`.

## VERIFICATION LADDER — the game is the last resort

**Do not carry a bug that one step can catch down to a lower step.**
Full recipe: `trunk/verification-ladder.md`.

| what to verify | step |
|---|---|
| weights, deform, pivot, dimensions | **measure** in Blender (`evaluated_get`) |
| shader/bucket, bone tag, hierarchy, `<Hash>`, clip count | `res_to_xml.ps1` + structural diff against vanilla |
| "does it look right" | Blender render → send the user a **file** |
| vanilla asset, world placement, MLO layout | CodeWalker GUI (by hand, the user drives) |
| script, physics, real look, streaming, resmon | **the game** — for particles the test bench `scripts/ptfx_bench.py` |

## WHEN AN IMAGE IS NEEDED — do not generate it, suggest it and give a prompt

Screen background, icon, logo, texture: **do not invent a placeholder.** Describe the idea (what,
where, from what distance, tone) → give the user a **ready prompt** with the aspect ratio and
resolution → until the image arrives, build the layout in code and leave an empty box of the
right size. An invented image does not fit the tone; the work is done twice.

## WHEN IT IS NOT ENOUGH

Fragment internals → inspect the `.yft` · animation duration/events → `.ycd` ·
internal layout of the server's own MLOs → `/asset-build -ExtraFolders`
brings the archetypes, the internal entity expansion depends on vanilla ymaps.
In these cases do not guess; say what to look at in CodeWalker or ask for an
in-game measurement.
