---
description: Where a prop/object sits in the world (ymap + MLO interior), or what is near a coordinate
argument-hint: <model name> | near <x> <y> <z> [--radius N] [--filter part]
allowed-tools: Bash(python:*), Read
---

User query: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

3.05 million world placements are in the index. The position of interior (MLO) props is
computed as `mloPos + rotate(localPos, mloRot)` — so the door inside the Fleeca
is found too, not only the outside world.

## How to use

```bash
# all placements of an archetype
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" where <model name>

# what is around a point
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" near <x> <y> <z> --radius 10
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" near <x> <y> <z> --radius 15 --filter door
```

## When presenting the result

- Give the position directly as `vec3(x, y, z)` — so it can be pasted into a config.
- If it is marked `[mlo]`, say which interior it belongs to; that prop only exists
  while that MLO is loaded.
- A result such as "6 unique locations" shows how many places the prop is repeated
  on the map (e.g. 6 Fleeca bank branches) — build the config for that; do not
  assume a single coordinate.
- If there is no result: the prop may not be placed in the world (only spawned
  by script), or it was caught by the LOD filter. Check with `/asset <name>` whether it
  exists as an archetype.
- If `entities.db` does not exist, suggest `/asset-build` to the user — **do not invent**.
