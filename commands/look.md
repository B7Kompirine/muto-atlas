---
description: Look branch - shaders and render buckets, textures, prop lights (TimeFlags/Flashiness/gobo), decals, timecycle, parallax, vertex colour, emissive panels
argument-hint: <what should happen — "my lamp is dim" / "graffiti on the wall" / "the room is too bright" / "a hole in the wall" / "which shader">
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep, AskUserQuestion
---

Argument: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

## This is a BRANCH command

1. **Read the branch first:** `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/branches/look/_branch.md`
   — shader = program + bucket, texture DXT rules, light tied to a bone / TimeFlags / Flashiness enum / gobo Tangent,
   the three layers of darkness, vertex color bucket 0, the three decal systems, the three truths of parallax.
2. Pick **one leaf** from the argument: shader · parallax · light · light maths · timecycle · vertex color · emissive · decal.
3. Query before writing code and **decode the magic number**: `assetdb.py light <ydr>` (`--table` for the vanilla band) · `cycle w_clear --hour 20` ·
   `timecycle <name>` · `shader <kind>` · `decal <kind>` · `flags <n>`.
4. When suggesting a value, use the measured vanilla band (`--table`); if the layer is missing, **do not invent** a range. Every write is **read back**.

## When presenting the result
- "It doesn't light up" → first the hour (`TimeFlags`), then the room modifier, the light last. Show this order in your answer.
- Do not call something "broken" based on a screenshot; read the pixel/file.
- Asset changed → leave the server and reconnect.
