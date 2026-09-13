---
name: fivem-natives
description: FiveM/GTA V native verification and lookup database (7191 natives, offline). ALWAYS use it when writing, editing or reviewing FiveM Lua/JS code involves a native name, signature, parameter order or client/server side — even if the user does not ask. Do not write a native name from memory; verify it first. Triggers - FiveM, Cfx, GTA V native, QBCore, QBX, ESX, ox_lib, client.lua/server.lua, fxmanifest, "does this native exist", "which native", "does it work on the server", "what is the signature", resmon/performance review, Lua lint.
license: MIT
compatibility: Python 3.10+. The native index is built once by scripts/build_index.py --fetch (network). The scripts live at the muto-atlas repository root, outside this folder - outside Claude Code install with scripts/install_skills.py or use scripts/mcp_server.py.
---

# FiveM Native Database

Writing FiveM natives from memory is the most common mistake: a name that does not exist
(`GetPlayerMoney`), the wrong side (`DrawMarker` on the server) or the wrong parameter
order gets written and the script breaks silently. This skill makes that measurable.

**Rule: do not write a native name from memory. Run `check` first for every native you are
not sure of.**


## ⛔ IF DATA IS MISSING, DO NOT GUESS — gate first

Every answer of this skill rests on the layers under `data/`. If a layer is missing, the
query returns **exit 2**. At that point the only thing to do is **stop**:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --plan     # writes nothing, shows the state
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py"            # installs the missing layers
```

The `--plan` output says "N/M layers installed" and lists the missing one by name
(M is not fixed, `setup.py` computes it — do not write a number here).
Setup builds from the user's **own GTA V install**; the command is `/asset-setup`.

⛔ **Do not produce an answer without data.** When you see exit 2, tell the user which layer is
missing and the one-line install command. Falling back to a guess defeats the reason this
tool exists — a wrong `fxName`, a wrong flag or a prop name that does not exist is accepted
**silently** and costs a round.

ℹ️ **Why the data does not ship in the repository:** `entities.db` alone is 214 MB (GitHub
file limit 100 MB) and the content belongs to Rockstar — redistributing it is a copyright
problem. Side benefit: each layer comes from everyone's **own game version**.
With one central copy everyone would be stuck on one version (measured:
this install has 1271 `m26_*` archetypes, the ready-made dump has 0).
## Data

An offline, merged index in `data/`:

| set | count |
|---|---|
| total natives | 7191 |
| client-only | 6830 |
| shared (client + server) | 232 |
| server-only | 129 |

Sources: `runtime.fivem.net/doc/natives.json` (GTA V) +
`natives_cfx.json` (Cfx) + the server handler registrations in the `citizenfx/fivem` source.
For checksums and dates: `python scripts/nativedb.py stats`.

> The GTA V native list carries no `apiset` upstream — docs.fivem.net assumes they are
> client. Server availability is derived from the Cfx declaration set and the
> `RegisterNativeHandler` registrations in `ServerGameState_Scripting.cpp`;
> if both sides support a native it is marked `shared`.

## Commands

`$P` = plugin root: `${CLAUDE_PLUGIN_ROOT}` (if not found, the muto-atlas folder that contains `scripts/nativedb.py`).

```bash
# Does it exist? Which side? — BEFORE writing code
python "$P/scripts/nativedb.py" check GetEntityCoords DrawMarker GetPlayerMoney

# Full signature, parameter descriptions, docs link, Lua example
python "$P/scripts/nativedb.py" show GetVehicleNumberPlateText

# Find the right native (when you do not remember the name)
python "$P/scripts/nativedb.py" search vehicle fuel --apiset server

# The natives of a namespace callable from the server
python "$P/scripts/nativedb.py" ns VEHICLE --apiset server

# Lint the Lua you wrote
python "$P/scripts/lint_lua.py" resources/<resource-name>
```

If `check` finds a native that does not exist it returns **exit 1** and suggests close names.

## Required flow

1. **Before writing code** — verify the natives you will use in one `check` call.
   The `[client] / [server] / [shared]` tag in the output decides which file they go in.
2. **Take the signature from `show`**, not from memory. Parameter order and types are there.
3. **After writing/editing code** — run `lint_lua.py` on the resource you touched.
   Do not consider the work done while an E00x error remains.
4. **When suggesting a native to the user**, give the docs link (the `docs` line in the
   `show` output) with it.

If `check` cannot find a native and has no close suggestion either: **that native does not exist.**
Do not invent one. What you are looking for is probably a framework function (QBCore/ox_lib
exports) — not a native. Tell the user so plainly.

## Side discipline

| file | may call |
|---|---|
| `client.lua` | `client` + `shared` |
| `server.lua` | `server` + `shared` |
| `shared.lua` / config | `shared` only |

Common mistakes that do **not work** on the server: `DrawMarker`, `DrawText3D`,
`GetClockHours`, `RequestModel`, `TaskGoToCoord`, `PlaySoundFrontend`,
`SetNuiFocus`, the entire `HUD`/`GRAPHICS`/`CAM`/`STREAMING` namespaces.

If you need to do entity work on the server, search with `--apiset server`: entity natives
marked `shared` (`GetEntityCoords`, `SetEntityCoords`, `DeleteEntity`,
`CreateVehicle`, `GetPlayerPed`) are valid on the server side too.

`Wait`, `CreateThread`, `RegisterNetEvent`, `TriggerClientEvent`,
`PerformHttpRequest`, `GetPlayers` are not natives — they are Citizen runtime functions,
they are not looked up in the database, and they exist on both sides.

## Lint rules

| rule | meaning |
|---|---|
| `E001` | native does not exist (typo or invented) |
| `E002` | wrong side — client-only native in a server file |
| `E003` | extra argument — more parameters than the signature |
| `W101` | `RequestModel`/`RequestAnimDict` called every frame |
| `W102` | `GetGamePool`/`GetActivePlayers` in a `Wait(0)` loop |
| `W103` | distance computed every frame, result not cached |
| `W104` | missing argument — legal, but verify it is intentional |

E00x are errors, fix them. W1xx are warnings; common idioms such as `GetEntityCoords(ped)`
produce W104 and are usually fine — look and move on.

The linter does not count table/method calls such as `Bridge.HasItem()` or local functions
defined in the scanned files as natives. If you still see a false positive, make sure the
definition is in a file inside the lint scope.

## Performance and depth

Per-frame cost, entity caching and resmon targets:
`references/performance.md`. Commonly confused native pairs and their correct counterparts:
`references/pitfalls.md`.

## Framework calls — not natives, but just as silent

`lint_lua.py` verifies only **GTA natives**. Most bugs in a QBCore/Qbox/ESX/ox
resource are not in a native but **in a framework call**, and
none of them throws: a non-existent event is triggered (not even a log), a non-existent export
is called (`nil value` only when that line runs), `lib.showTextUi` is written in lowercase
(no module, silent).

```bash
python "$P/scripts/assetdb.py" framework <name>
python "$P/scripts/assetdb.py" framework --check
```

⛔ **The authority is the installed server, not upstream GitHub.**
Full layer: `references/framework-api.md`

## Updating

When Cfx adds new natives:

```bash
python "$P/scripts/build_index.py" --fetch
```

Downloads upstream again and rebuilds the index.
