# Verifying an asset without entering the game — the CodeWalker ladder

**Trunk file.** The ladder for verifying an asset without taking it into the game; every branch uses it. Moved: `trunk/verification-ladder.md` (2026-09-05).

**Goal:** stop connecting to the server for every small change. Because FiveM caches stream
files, an asset test needs a **full exit + reconnect** (a restart is not enough) — so even the
cheapest in-game round takes minutes. The upper steps of the ladder below take seconds.

**Rule: do not carry a bug that one step can catch down to a lower step.**
The game is the last resort; go down there only for things the three steps above *structurally*
cannot see.

---

## Step 0 — The production tool's own check (seconds)

On the Blender/Sollumz side, **before** export. Measure, do not eyeball.
Concrete examples that were skipped once and cost hours:

- Unweighted vertex count, influence count (>4), weight sum (=1.0).
  In bmesh, if `index_update()` is not called, `vert.index` is **−1** and
  the weights are written to no vertex; export silently produces an unweighted mesh.
- Measurement after deform: real world coordinates with `evaluated_get(depsgraph)`.
  Posing it and saying "done" is not enough.
- **Do not measure on a single axis and pick a vertex with `max()`.** Measured case:
  the three rings had equal radii, so `max(x)` picked a vertex from the bottom ring;
  that ring did not bend, so a working rig was reported as "tilt 0". **Pin the measurement to
  the subset you care about** (index range), not the whole mesh.

## Step 1 — Read back the compiled file (seconds)

**Tools: `assetdb.py doctor` and `assetdb.py diff`** — both dump the binary to XML with
`res_to_xml.ps1` and read it; you do not have to do it by hand.

```bash
assetdb.py doctor stream/ -r          # scan for silent failures
assetdb.py diff yours.yft vanilla.yft
```

`doctor` looks for known silent failure patterns: an empty `<Hash>` in a `.ycd`
(the clip has no name, `TaskPlayAnim` cannot find it), an unresolved `AnimationHash`,
an animation with 0 bone channels, a ymap flag on an MLO entity, an entity not assigned
to a room/portal, a degenerate bounding box, a light with `TimeFlags` but no hours.
A file that cannot be audited is **never counted as clean** — it is reported in a separate
section and the exit code becomes 2.

`diff` does not compare field values but **which nodes are missing entirely**,
and reports the boundary where the difference *starts* (if a whole subtree is missing it does
not make a separate row for every descendant).

**Correction about the ped `.yft` crash (measured):** at this step do NOT SEARCH for the
`ArticulatedBody` node — CodeWalker's XML writer never produces that string, it does not appear
in the XML of vanilla `mp_m_freemode_01.yft` either, so it "looking missing" means nothing.
The real measured sign is this: **a vanilla ped `.yft` has no `<Physics>` node at all.**
So if `Physics` shows up on the "IN YOURS, NOT IN VANILLA" side of the `diff` output, remove it;
what you are looking for is not a missing child node but an extra parent node.

Caught at this step: shader name/bucket, bone tags and hierarchy, geometry count, whether
`<Hash>` is filled, clip count (in a multi-clip dictionary, clips overwriting each other shows up here).

## Step 2 — clip curve evaluation

The tool and recipe for this step are not in the public release.

## Step 3 — Visual preview (half a minute)

The number says "right" but **the user cannot see it**. A headless check does not replace what a
human has to confirm by eye.

The most practical way: run the pose library frame by frame in Blender and render a PNG
sequence, turn it into mp4/gif with `ffmpeg`, and **send it to the user as a file**.
Do not tell the user "look in this folder", deliver the file.

```powershell
ffmpeg -y -framerate 30 -i "f%04d.png" -c:v libx264 -pix_fmt yuv420p out.mp4
```

Blender preview pitfalls:
- **Sollumz export materials render black in EEVEE.** For the preview give a temporary
  `Principled BSDF` material, then revert it.
- **Opaque glass hides the liquid completely.** For transparency do not use `Transmission`
  (EEVEE does not show what is behind it) — use `Alpha` + in Blender 4.2+
  `material.surface_render_method = 'BLENDED'`.
- In Blender 5.x the render engine is `'BLENDER_EEVEE'` (no `_NEXT` suffix).

### NUI page (HUD) preview

Substitute `vh/vw` with 1080p pixels + inject a sample message + **headless Edge**
screenshot (`--user-data-dir` required, otherwise no file is written). The Browser
pane's `file://` snapshot misleads on scale.

## Step 4 — CodeWalker GUI (minutes, by hand)

`ModelForm` really can play a clip on a model:
`ClipDictComboBox` + `ClipComboBox` + `LoadClipDict()` + `SelectClip()` +
`InitAnimation()`. The yellow ring/coloured arrow gizmos are `SetWidgetMode` /
`SetWidgetTransform`.

**Limit:** `LoadClipDict(string)` resolves the dictionary **by name from the loaded game
data**. A loose `.ycd` in a FiveM resource folder does not appear in the dropdown
list; it has to be in a location CodeWalker scans.
`ModelForm` has no "Open" dialog of its own either — it is opened from RPF Explorer.

**Automation note:** if CodeWalker is a portable `.exe`, computer-use
`request_access` cannot find it (it looks at the Start menu index; creating a shortcut
afterwards did not help immediately either). So the agent cannot drive the GUI;
this is the step the user does with their own hands. The agent gives
**step-by-step directions** here and does not try to be the driver.

## Step 5 — The game (minutes, the most expensive)

Only for what cannot be seen **structurally** above:

- Everything tied to script: `PlayEntityAnim`, phase scanning with
  `SetEntityAnimCurrentTime`, the door system, export/event flow
- Physics: ragdoll, fragment breaking, collision response, `specialAttribute`
  behaviour
- The real RAGE look — CodeWalker has its own DX11 renderer and Blender is
  something else entirely; `glass_env`/`emissive` look exactly right in neither
- Streaming/cache, resource load order, ytyp registration with `DLC_ITYP_REQUEST`,
  MLO room/portal culling
- Performance (resmon)

**Before going into the game, remind the user: they must fully LEAVE the server and
reconnect, a restart is not enough** — otherwise a stale asset is tested
and the result is wrong.

---

## Verifying the table itself — `verify_tables.py`

The steps above verify an **asset**. This script verifies the **table**:
`shaders.tsv` and `collision_materials.tsv` were both extracted from the Sollumz source,
so they have **a single source**. The script sets a second source against them (usage data
built from the game's own files, `build_usage.ps1`) and asks three questions: is there a shader
that appears in usage but is **not** in the table · are the collision material indices in use
inside the table range · with which `RenderBucket` are decal shaders used (Sollumz default
`Opaque(0)`; only measurement tells the right one).

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/verify_tables.py"
```

If a number you took from a table looks unexpected, **run this first** —
it may be the table to blame, not the asset.

## Summary decision table

| What to verify | Highest sufficient step |
|---|---|
| weights, deform, pivot, dimensions | 0 (Blender measurement) |
| shader/bucket, bone tag, hierarchy, `<Hash>`, clip count | 1 (`doctor` / `diff`) |
| a light's hours, cone, range; why an interior is dark | 1 (`light` / `timecycle --mlo`) |
| "does it look right" | 3 (render + send to the user) |
| inspecting a vanilla asset, world placement, MLO layout | 4 (CodeWalker GUI, by hand) |
| script, physics, real look, streaming, performance | 5 (game) |
