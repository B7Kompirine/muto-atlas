---
description: List every muto-atlas command with what it does, plus data-layer status - the map of the whole plugin
argument-hint: [empty = full list] | [search word — "light", "animation", "decal"]
allowed-tools: Bash(python:*), Read
---

Argument: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

## Do

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/list_commands.py" $ARGUMENTS
```

This script **reads the list from the `commands/*.md` frontmatter** — it is not a hand-written
list, so it does not go stale. A new command shows up by itself once it is added.

If an argument is given, it is passed on as a search (it checks the name and the description).

## Then — show the data status too

Every answer of this plugin rests on the layers under `data/`. A missing layer means
the model **falls back to guessing**. So report the status together with the
command list:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --plan
```

Pass on the **"N/M layers installed"** line of the output as it is — do not hard-code the
number; `setup.py` computes it from the length of its layer list. If something is missing, give the setup
command: `python scripts/setup.py` or `/asset-setup`.

## When presenting

- Print the raw output as it is — the script already groups it readably.
- If the user describes a specific job ("I'm going to adjust lights", "the door
  won't open"), **name the right command** instead of dumping the list, and explain in one sentence why
  it is that one.
- Commands are called with `/muto-atlas:<name>`; if no other plugin has the same name,
  the short form `/<name>` works too.

## Three useful things that are not in the list

| job | command |
|---|---|
| data layer status | `python scripts/setup.py --plan` |
| plugin integrity audit (broken links, orphan references, BOM) | `python scripts/audit_plugin.py` |
| one-line command list (for scripts/docs) | `python scripts/list_commands.py --flat` |
