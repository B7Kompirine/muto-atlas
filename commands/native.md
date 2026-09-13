---
description: Search a FiveM native, verify it exists, show its signature
argument-hint: <native name or search term> [--apiset server|client|shared]
allowed-tools: Bash(python:*), Read
---

User query: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

Handle the query like this:

1. If the query looks like a native name (`GetEntityCoords`, `GET_ENTITY_COORDS`,
   `0x3FEF770D40960D5A`), verify it first:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/nativedb.py" check <name>
   ```

   If it exists, fetch the full signature, parameter descriptions, docs link and Lua
   example with `show`. If it does not, offer the user the suggested close names and **do not invent**.

2. If the query is free text (`vehicle fuel`, `reading the plate`, `player identifier`), search:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/nativedb.py" search <terms> [--apiset ...]
   ```

   The search runs on the English descriptions; translate a Turkish query into English terms
   before searching (`yakıt` → `fuel`, `plaka` → `plate`, `kimlik` → `identifier`).

3. When presenting the result, **always** state:
   - the `client` / `server` / `shared` label and which file it goes into
   - the full signature (parameter types and order)
   - the docs.fivem.net link

If there are several candidates, list them all, then recommend the one that best fits the job
the user described, with the reason.
