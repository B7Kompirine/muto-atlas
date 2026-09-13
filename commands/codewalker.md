---
description: Where CodeWalker.Core.dll is - show it, or set a new path
argument-hint: [path]  ·  omit to just show it
allowed-tools: Bash(python:*), Read
---

User query: `$ARGUMENTS`

```bash
# where is it?
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path codewalker

# set it
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path codewalker "$ARGUMENTS"
```

If `$ARGUMENTS` is empty, **show** the path; if a path was given, **set** it.

`CodeWalker.Core.dll` is the plugin's most critical external dependency: **30 scripts**
depend on it (`.ydr/.yft/.ycd` decoding, RPF extraction, XML round trip, light editor).
They all read the same registry (`data/config.json`) — if it cannot be found, the fix is to
set it here, not to edit the scripts.

## When presenting the result

- The path is **verified on disk**; a path that does not exist is not accepted.
- "written in the config but not on disk" and "never set" are **different**
  states and are reported separately.
- If it was not found, also show where it looked, then suggest setting it.
- The version matters: the plugin was measured with `CodeWalker30_dev46`. If a different version
  is given, the API signatures may have changed — if a script blows up, that is the first suspect.
