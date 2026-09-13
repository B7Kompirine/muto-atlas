# Native cost and resmon

Target: an idle resource under **0.01ms**, under **0.10ms** in active use.
The one thing that usually breaks this target is a loop that runs every frame.

## The Wait(0) loop rule

`Wait(0)` = ~60 iterations per second. Every native inside it runs 60×.

```lua
-- BAD: pool scan + model request every frame
CreateThread(function()
    while true do
        Wait(0)
        local peds = GetGamePool('CPed')          -- W102
        RequestModel(model)                        -- W101
        local d = GetDistanceBetweenCoords(...)    -- W103
    end
end)

-- GOOD: expensive work outside the loop, loop tuned by sleep time
local model = `adder`
RequestModel(model)
while not HasModelLoaded(model) do Wait(0) end

CreateThread(function()
    while true do
        local sleep = 1000
        local coords = GetEntityCoords(cache.ped)
        if #(coords - target) < 20.0 then
            sleep = 0            -- every frame only when close
            DrawMarker(...)
        end
        Wait(sleep)
    end
end)
```

Key pattern: **dynamic `sleep`**. While the player is not in the relevant area the loop should sleep
500–1000ms; use `Wait(0)` only when something must be drawn.

## Expensive natives

Do not call these every frame — the linter catches them inside a `Wait(0)` body:

| native | cost | instead |
|---|---|---|
| `GetGamePool('CPed'/'CVehicle'/'CObject')` | scans the whole world | scan periodically, cache the result |
| `GetActivePlayers` | copies the player list | refresh every 1–5s |
| `GetClosestVehicle` / `GetClosestPed` | shapetest + scan | compute from the cached pool |
| `GetDistanceBetweenCoords` | crosses the native boundary | use `#(vec1 - vec2)` (pure Lua, much cheaper) |
| `RequestModel` / `RequestAnimDict` | streaming request | load once, wait with `HasModelLoaded` |

The `#(v1 - v2)` vector difference calls no GTA native; prefer it over
`GetDistanceBetweenCoords` for distance comparisons.

## Caching

Move values that do not change every frame out of the loop:

```lua
-- BAD
while true do
    Wait(0)
    local ped = PlayerPedId()
    local veh = GetVehiclePedIsIn(ped, false)
end

-- GOOD: ox_lib cache or your own variable
local ped = cache.ped        -- ox_lib
local veh = cache.vehicle
```

`PlayerPedId()` is cheap, but tracking ped changes through an event is cheaper.
With ox_lib, `cache.ped` / `cache.vehicle` / `cache.seat` already update from events.

## Server side

The server has no per-frame loop, but it has equivalent mistakes:

- One DB query per iteration inside a player loop → N+1. Gather it into one query.
- Frequent broadcasts to all players (`-1`) with `TriggerClientEvent` → bandwidth.
  Apply a distance/interest filter.
- A DB write on every event trigger → write in batches or debounce.

## Measurement

Do not settle for a guess from the code:

```
resmon 1          # in the F8 console, resource CPU time
profiler record 500
profiler view
```

Compare the resmon value before and after the change; back the claim with a measurement.
