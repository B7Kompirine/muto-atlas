---
description: Clothing branch - freemode clothing, moving clothes to 98-bone peds, ped props (hats, glasses), texture variants and skintone (_r)
argument-hint: <what should happen — "add a jacket to freemode" / "hat prop" / "skin tone not working" / "texture variant">
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep, AskUserQuestion
---

Argument: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

## This is a BRANCH command

1. **Read the branch first:** `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/branches/clothing/_branch.md`
   — two UV maps, `Colour 0/1`, Mesh Domain, the embedded texture rule, texture naming, the `_r` mask, Render Flags.
2. Pick **one leaf** from the argument: freemode clothing · ped prop · texture variant.
3. ⚠️ This branch is **video-sourced, not measured** — tell the user; when you give a number, verify it with `assetdb.py`.
4. Extracting from the RPF → `extract_asset.ps1 -PathFilter '<ped>'`.

## When presenting the result
- If a `textures/` folder appeared after export, something is still embedded — say so.
- Asset changed → leave the server and reconnect.
