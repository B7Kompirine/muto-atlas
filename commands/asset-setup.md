---
description: Setup - asks for your paths, builds all data layers from your own install
argument-hint: "[server resources folder]"
allowed-tools: Bash(python:*), Bash(powershell.exe:*), Read, Glob, AskUserQuestion
---

Argument: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

## STEP 1 — See the state

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --plan
```

Look at the three lines at the top of the output: `GTA V`, `CodeWalker`, `server`.
If all three are filled in, go to STEP 3.

## STEP 2 — ASK THE USER for the missing path

⛔ **Do not guess, do not keep searching, do not say "it is probably there".**
Everyone who uses this tool has GTA V and CodeWalker; what is missing is not data but
**path information.** Ask with `AskUserQuestion`:

- **GTA V folder** — where files such as `x64a.rpf` and `common.rpf` are.
  Common: `C:\Program Files\Epic Games\GTAV`,
  `C:\Program Files\Rockstar Games\Grand Theft Auto V`,
  `...\Steam\steamapps\common\Grand Theft Auto V`
- **CodeWalker.Core.dll** — in the folder you open CodeWalker from, next to `CodeWalker.exe`.
  It can be a version folder (`CodeWalker30_dev46`).
- **FiveM server `resources` folder** *(optional but very valuable)* —
  the framework index is built from it; it catches export/event calls to
  resources that are not installed.

## STEP 3 — Build

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --save \
  --gta "<GTA V folder>" \
  --codewalker "<path>\CodeWalker.Core.dll" \
  --resources "<server>/resources"
```

`--save` writes the paths to `data/config.json`; they are not asked again.
(`data/` is in `.gitignore` — personal path information never enters the repo.)

The heavy layers are built **by default**. It takes a few minutes
(clips ~3 min, skeletons longer). To skip them, `--light-only`.

## STEP 4 — Verify

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" stats
```

It prints each layer's present/missing status, its size and the dump version.
`stats` **never** returns EXIT 2 — it works even with missing layers, because it is
the answer to "what is installed?".

## ⛔ After setup, tell the user

If a layer is still missing, say **which queries will not work**.
Exit codes:

| code | meaning |
|---:|---|
| 0 | found |
| 1 | name not in the authority |
| 2 | layer not installed — nothing can be claimed about the result |
| 3 | internal error (broken file) |

Mistaking `2` for `1` is mistaking missing data for a missing asset — this plugin
exists exactly to prevent that.
