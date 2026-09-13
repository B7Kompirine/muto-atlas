---
description: Map branch - replace vanilla parts, destruction (RayFire), MLO props and swaps, LOD chains, vanilla interior measurements, grass/procedural
argument-hint: <what should happen — "make the bridge collapse" / "change the road" / "put a safe in the bank" / "it disappears at a distance" / "grass">
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep, AskUserQuestion
---

Argument: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

## This is a BRANCH command

1. **Read the branch first:** `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/branches/map/_branch.md`
   — inside/outside an MLO, extent, LOD chain + `hei_`, ymap versions, the three assets of RayFire, the four systems of grass.
2. Pick **one leaf** from the argument: vanilla part · destruction · MLO swap · prop into an MLO · LOD · interior measurements · grass.
   If the description is ambiguous (*"break the wall"*, *"blow the door up"*), `AskUserQuestion`: map part or script prop ·
   will permanent debris remain · will everyone see it at the same time · will people walk on it during the destruction.
3. Query before writing code: `assetdb.py where <name>` · `mlo <name>` · `lodchain <name>` · `flags <n> --entity` · `near x y z`.
4. Asset changed → **leave the server and reconnect.**

## When presenting the result
- Decode a magic number (`1572872`, `18350080`) when you mention it; do not copy it.
- State explicitly that the extent was not touched, the `hei_` twin was patched and the room assignment was done.
