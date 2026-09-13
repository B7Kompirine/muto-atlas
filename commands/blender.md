---
description: Where blender.exe is - show it, or set a new path
argument-hint: [path]  ·  omit to just show it
allowed-tools: Bash(python:*), Read
---

User query: `$ARGUMENTS`

```bash
# where is it?
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path blender

# set it
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path blender "$ARGUMENTS"
```

If `$ARGUMENTS` is empty, **show** the path; if a path was given, **set** it.

The `blender_*.py` scripts (light preview) run inside
Blender. If this path is stored, the scripts can be run headless
(`--background`).

**The automatic search cannot find a Steam install** — measured: Blender
can be installed under `steamapps\common\Blender\blender.exe`, which is not in the default
candidate list. For such an install, give the path by hand once.

## When presenting the result

- **Reading/writing lights does NOT NEED Blender** — `/look` works on the file
  directly. If the user is adjusting light values, do not suggest Blender.
- The Blender version matters: in 5.x `GPUShader(vs, fs)` was removed and there is no
  `GPUStorageBuf`; in 4.4+ the Action API is layered. A version difference is the first suspect
  for script errors.

## Add-ons — check this before writing code

Before writing `bpy` code from scratch for a job, ask **whether an add-on the user has installed
already does it**.

⚠️ Geometry produced by add-ons follows the normal rules **before it goes into Sollumz**:
bake the transforms, `Ctrl+A` is required, textures are powers of two
(`skills/fivem-assets/trunk/tool-pitfalls.md` §2, `trunk/gta-fundamentals.md` §5).

### Useful third-party add-ons

`sollumz` · `sollumz_rdr_dev` ·
`cell_fracture` · `ZenUV` / `mio3_uv` / `flat_uv_mapper` / `propgon_uv_trim` ·
`SimpleBake` / `sanctus_bake` / `beyond_channel_packer` · `lazy_decals` ·
`smart_remesh` · `qol_clean_slice_booleans` · `auto_mirror` · `pro_particles` ·
`RayPilot` · `stair_generator_addon` · `Organic_Addon` · `luman_tools` ·
`unreal_viewport_navigation`.

Tools shared in the channel that are **not installed** (Vertex Color Master, geonodes
decal/terrain, `blender_rayfirev`, FakeBones) →
`skills/fivem-assets/sources/community-resources.md`.

**Measured:** scan of `AppData\Roaming\Blender Foundation\Blender\*\extensions\` and
`\scripts\addons\`, 2026-09-06.
