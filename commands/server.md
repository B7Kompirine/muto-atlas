---
description: Where your FiveM server resources folder is - show it, or set a new path
argument-hint: [path]  ·  omit to just show it
allowed-tools: Bash(python:*), Read
---

User query: `$ARGUMENTS`

```bash
# where is it?
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path server

# set it
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path server "$ARGUMENTS"
```

If `$ARGUMENTS` is empty, **show** the path; if a path was given, **set** it.

The framework index (QBCore/Qbox/ESX/ox exports and events) is built from this folder
— that is how missing exports and calls to non-existent events are caught.
The path looks like `.../txData/<server>.base/resources`.

## When presenting the result

- The folder is **verified on disk**.
- If the server path changed, the framework index is stale: refresh it with `build_framework.py`,
  otherwise the "this export does not exist" warnings come out wrong.
- There is no automatic candidate — the server folder is in a different place on every install,
  so it is given by hand once.
