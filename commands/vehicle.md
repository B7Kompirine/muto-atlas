---
description: Vehicle branch - vehicle bone names (stable), handling/modkit/extra lookup, external vehicle tools
argument-hint: <what should happen — "door bone" / "handlingId" / "modkit">
allowed-tools: Bash(python:*), Read, Glob, Grep
---

Argument: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

## This is a BRANCH command (thin branch)

1. **Read the branch first:** `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/branches/vehicle/_branch.md` — vehicle bone names are stable.
2. Query: `assetdb.py vehicle <name>` · `bones <model>`. A bone name is not guessed; copy it from `trunk/bone-tags.md` §2.
3. Vehicle modelling/setup is not measured — tell the user; the community videos are in the local extraction.
