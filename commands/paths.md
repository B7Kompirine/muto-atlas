---
description: Show or set external tool and folder paths (codewalker, gta, server, blender, ...)
argument-hint: [name] [path]  ·  omit both to list all  ·  --remove to drop one
allowed-tools: Bash(python:*), Read
---

User query: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

The **single registry** of all external paths is `data/config.json`. Because `data/` is in .gitignore,
personal path information **never enters the repo**.

```bash
# show all of them (marked present/missing)
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path

# show one
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path codewalker

# set it
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path codewalker "C:\Tools\CodeWalker\CodeWalker.Core.dll"

# remove the entry
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path blender --remove
```

## Known names

| name | what | type |
|---|---|---|
| `codewalker` | `CodeWalker.Core.dll` — 30 scripts depend on it | file |
| `gta` | GTA V install folder — the source of the data layers | folder |
| `server` | the FiveM server's `resources` folder | folder |
| `blender` | `blender.exe` | file |

## The list is not closed — you can store any name you want

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path gizmo "C:\Tools\Gizmo.exe"
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path gizmo
```

A new tool needs no code change.

## When presenting the result

- **A path that does not exist on disk is not accepted.** Setting a path first checks that it exists;
  it says so at once rather than silently keeping a broken entry.
- **"written in the config but not on disk" is a separate state** and is reported as such
  — it is the most common cause of "I set it but it doesn't work"; do not confuse it with
  "never set".
- Exit code: `0` all found · `1` at least one missing · `2` the given path is invalid.
- If a script says "CodeWalker not found", the fix is `/paths codewalker "<path>"` —
  do not edit the script; they all read the same registry.
