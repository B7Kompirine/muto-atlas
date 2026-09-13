---
description: Where the GTA V install folder is - show it, or set a new path
argument-hint: [path]  ·  omit to just show it
allowed-tools: Bash(python:*), Read
---

User query: `$ARGUMENTS`

```bash
# where is it?
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path gta

# set it
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path gta "$ARGUMENTS"
```

If `$ARGUMENTS` is empty, **show** the path; if a path was given, **set** it.

All the data layers (archetypes, world placements, clips,
skeletons, lights, timecycle) are built **from the user's own install**.
If this folder is wrong, `/asset-build` does not work.

Rockstar / Epic / Steam installs are all in different places; the automatic
search tries five, and if it finds none, the path is given here.

## When presenting the result

- The folder is **verified on disk**; a path that does not exist is not accepted.
- If the path changed, **the generated layers are stale** — they must be rebuilt with
  `/asset-build`; do not silently carry on with the old index.
- `data/` is in .gitignore: this path never enters the repo.
