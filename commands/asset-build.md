---
description: Rebuild the archetype/animation indexes (after adding a new MLO or prop)
argument-hint: [server resources path]
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read
---

Argument: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

When it is needed: when a **new MLO / custom prop / ytyp** is added to the server, or
when GTA V is updated. As long as the vanilla data does not change, there is no need to rebuild.

## 1. Archetype index (ytyp → prop/door truth)

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/build_archetypes.ps1" -ExtraFolders "<server resources path>"
```

- It finds the GTA V folder and CodeWalker.Core.dll by itself; if it cannot, pass them with
  `-GtaFolder` / `-CodeWalker`.
- Without `-ExtraFolders` only vanilla is indexed.
- Takes ~20 s, output `data/archetypes.tsv.gz`.

**Prerequisite:** CodeWalker (CodeWalker.Core.dll) and GTA V must be installed. If they are not,
tell the user; if this step is skipped, custom props cannot be queried.

## 2. World position index (ymap + MLO interior)

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/build_entities.ps1"
python "${CLAUDE_PLUGIN_ROOT}/scripts/build_entities_db.py"
```

- The first step takes ~50 s and produces `entities.tsv.gz` (~40 MB).
- The second step takes ~20 s and produces `entities.db` (~214 MB, indexed).
  `--drop-tsv` deletes the intermediate file.
- Without `-All`, LOD/terrain pieces are skipped; the props you need when writing a script
  are kept. If you want everything, add `-All` (the index grows ~10x).

## 3. Animation detail, skeleton and expression

```bash
# clips: real duration + tracks + bone count (.ycd), ~3 min
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/build_clips.ps1"

# skeleton (.ydr/.yft) + expression (.yed) — the longest step
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/build_rigs.ps1"
```

## 4. Animation / prop / scenario name list

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/build_anims.py"
```

Needs internet (DurtyFree/gta-v-data-dumps). If the files were downloaded before,
`--offline` builds from the cache.

## 5. Light + timecycle

```bash
# timecycle modifiers (~1 s) — "why is the interior dark"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/build_timecycle.ps1"

# embedded lights — ALL of GTA's .ydr/.yft/.ydd files are scanned, takes a LONG time
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/build_lights.ps1"
```

`build_lights.ps1` scans 171k files and **can take an hour**, depending on the machine.
To measure the duration first, run it with `-Sample 600`: sample mode prints an estimate
and **writes no file** (so that partial data does not persist).

Both are optional. If they are not installed, `light --table` and `timecycle`
return no invented values; they exit with code **2**.

## 6. Verify

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" stats
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" where v_ilev_gb_teldr
```

Expected: ~316k archetypes, ~269k anim clips, ~3.05M world placements and
6 Fleeca locations for `v_ilev_gb_teldr`. Tell the user the custom archetype count
— if it is 0, the `-ExtraFolders` path is wrong.
