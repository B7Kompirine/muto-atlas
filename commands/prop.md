---
description: Prop branch - doors and movement, fragments, live screens on objects (DUI), attaching props to a hand
argument-hint: <what should happen — "the door won't open" / "a screen on the ATM" / "breakable prop" / "attach to hand">
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep, AskUserQuestion
---

Argument: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

## This is a BRANCH command

1. **Read the branch first:** `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/branches/prop/_branch.md`
   — `specialAttribute`, the four layers of movement, pivot/bbox/physicsDictionary, `CreateObject` vs `NoOffset`, the three screen paths.
2. Pick **one leaf** from the argument: door/movement · fragment · DUI screen · attaching to a hand.
3. Query before writing code: `assetdb.py show <name>` · `door <name>` · `where <name>` · `bones <name>` · `screentex.ps1 -Model <name>`.
4. If the object is **inside an MLO**, the fix is not in this branch: `branches/map/mlo-object-swap.md`.

## When presenting the result
- State the `specialAttribute` value and its meaning; if it is 0, do not suggest the door system at all.
- Asset changed → leave the server and reconnect. For screen work, say that `AddReplaceTexture` is global.
