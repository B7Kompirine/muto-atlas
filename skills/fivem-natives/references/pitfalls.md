# Common native mistakes

Every claim in this file is verified against `data/natives.merged.json`.
When in doubt, confirm with `nativedb.py check`.

## 1. Side by namespace

Namespaces with **no** native callable from the server (34 of them):

```
APP AUDIO BRAIN CAM CLOCK CUTSCENE DATAFILE DECORATOR DLC EVENT FILES FIRE
GRAPHICS INTERIOR ITEMSET LOADINGSCREEN LOCALIZATION MOBILE MONEY NETSHOPPING
PAD PATHFIND PHYSICS RECORDING REPLAY SAVEMIGRATION SCRIPT SHAPETEST SOCIALCLUB
STATS STREAMING SYSTEM WATER ZONE
```

A native from one of these namespaces inside `server.lua` is a bug.
`CLOCK` is a pitfall in particular: `GetClockHours()` does not exist on the server, use `os.date`.

Partly callable from the server:

| namespace | total | from server |
|---|---:|---:|
| CFX | 775 | 203 |
| VEHICLE | 745 | 43 |
| PED | 610 | 36 |
| ENTITY | 184 | 24 |
| TASK | 304 | 20 |
| PLAYER | 248 | 13 |
| WEAPON | 116 | 10 |
| HUD | 508 | 6 |
| MISC | 323 | 2 |
| NETWORK | 823 | 2 |

So only 6% of `VEHICLE` natives are callable from the server. The generalisation "entity natives
work on the server" is wrong — `check` them one by one.

## 2. Leading underscore

In Cfx, natives with an undocumented name start with an underscore and are called with the
underscore in Lua too. Dropping the underscore gives `E001`:

| wrong | right |
|---|---|
| `AddTextComponentString(...)` | `AddTextComponentSubstringPlayerName(...)` or `_AddTextComponentString(...)` |
| `GetWeatherTypeTransition(...)` | `_GetWeatherTypeTransition(...)` |

`check` recognises both spellings and shows the canonical name.

## 3. Names that do not exist but are written often

These are not natives — they get mistaken for natives while looking for a framework function:

| written | actually |
|---|---|
| `GetPlayerMoney` | QBCore: `Player.PlayerData.money`, ESX: `xPlayer.getMoney()` |
| `TriggerServerCallback` | QBCore: `QBCore.Functions.TriggerCallback`, ox_lib: `lib.callback` |
| `GetWeaponName` | no native; map the `WEAPON` hash → locale/config |
| `HasEntityBeenDamagedByAnyWeapon` | `HasEntityBeenDamagedByWeapon(entity, weaponHash, weaponType)` |
| `GetVehicleFuel` | `GetVehicleFuelLevel(vehicle)` (Cfx, client) |

If the user says "use this native" and `check` cannot find it, say that it is not a native and
which framework API corresponds to it.

## 4. Argument count

In FiveM Lua a missing argument raises no error, it becomes `nil`/`0`. So a wrong parameter count
silently turns into wrong behaviour:

```lua
-- GetEntityCoords(Entity entity, BOOL alive) — common and harmless
local c = GetEntityCoords(ped)

-- ERROR: extra argument, the signature takes one parameter
local plate = GetVehicleNumberPlateText(veh, 5)
```

An extra argument gives `E003` (error), a missing argument `W104` (warning).

## 5. A method call is not a native

`Bridge.HasItem(...)`, `QBCore:GetCoreObject()`, `Player.Functions.AddItem(...)` are dot/colon
calls; the linter skips them. Do not `check` them as natives either — they are not in the database.
