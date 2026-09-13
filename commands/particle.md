---
description: Particle branch - find/attach vanilla effects, build .ypt from scratch, family catalogues, layered effects, deploy and measure in game
argument-hint: <what should happen — "dust when it breaks" / "my own spark" / "a layered explosion" / "the effect is not visible">
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep, AskUserQuestion
---

Argument: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

## This is a BRANCH command

1. **Read the branch first:** `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/branches/particle/_branch.md`
   — `fxName` ≠ `.ypt` name, `FxcFileHash`, keyframe slots, scales (percent vs 1.0), sheet/`C4`, pool 400.
2. Pick **one leaf** from the argument: ready-made effect · `.ypt` from scratch · catalogue · layered · deployment/measurement.
3. Query before writing code: `assetdb.py fx <name> --exact` · `ptfx <prop|effect>` · `ptfx --type 4`.
4. After building, read back (`ypt_xml_to_bin.ps1` exit 0) and measure in game with the **test bench** — "the handle is set" is not proof.

## When presenting the result
- State explicitly that the `fxName` was found in the `.ypt`, and mention the `ent_` prefix.
- If a new `.ypt` went into stream: a separate resource, a lower-case name, **leave the server and reconnect**.
