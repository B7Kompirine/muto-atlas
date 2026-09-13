---
description: Query prop/object/door archetype data (ytyp truth: is it a door, where is the pivot)
argument-hint: <model name or search term> | door <model name>
allowed-tools: Bash(python:*), Read
---

User query: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

This command gives the **ytyp truth**: `specialAttribute`, `flags`, `assetType`,
bounding box (pivot/hinge position), physics and texture dictionary. These are things
you cannot learn by trying natives.

## How to use

1. If the query is a model name (`v_ilev_gb_teldr`, `prop_gate_prison_01`):

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" show <name>
   ```

   The output contains the raw fields **and an interpretation**: does the door system move this object,
   is the pivot on the edge (does rotating it with heading look right).

2. If the question is specifically "does this door open":

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" door <name>
   ```

3. If the exact name is not known, search first:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" search <part>
   python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" prop <part>     # spawnable props
   ```

4. If the model is not found: the index may be old. Suggest that the user runs
   `/asset-build` — **do not invent**.

## When presenting the result

- Write the `specialAttribute` value and what it means **explicitly**.
- If the door system does not work (e.g. `0`), say so clearly and give the alternative;
  do not say "try AddDoorToSystem".
- Use the pivot information to say whether the `SetEntityHeading` approach will look
  right.
- If the archetype comes from a `custom` source, say which resource it came from.
