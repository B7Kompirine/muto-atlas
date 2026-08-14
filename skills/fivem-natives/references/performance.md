# Native maliyeti ve resmon

Hedef: boştaki bir resource **0.01ms**, aktif kullanımda **0.10ms** altında.
Bu hedefi aşan tek sebep genellikle her karede çalışan bir döngüdür.

## Wait(0) döngüsü kuralı

`Wait(0)` = saniyede ~60 iterasyon. İçine konan her native 60× çalışır.

```lua
-- KÖTÜ: her karede pool taraması + model isteği
CreateThread(function()
    while true do
        Wait(0)
        local peds = GetGamePool('CPed')          -- W102
        RequestModel(model)                        -- W101
        local d = GetDistanceBetweenCoords(...)    -- W103
    end
end)

-- İYİ: pahalı iş döngü dışında, döngü uyku süresine göre ayarlanmış
local model = `adder`
RequestModel(model)
while not HasModelLoaded(model) do Wait(0) end

CreateThread(function()
    while true do
        local sleep = 1000
        local coords = GetEntityCoords(cache.ped)
        if #(coords - target) < 20.0 then
            sleep = 0            -- yalnız yakınken her kare
            DrawMarker(...)
        end
        Wait(sleep)
    end
end)
```

Anahtar kalıp: **dinamik `sleep`**. Oyuncu ilgili alanda değilken döngü 500–1000ms
uyumalı; `Wait(0)` yalnız çizim gerektiğinde kullanılmalı.

## Pahalı nativeler

Her karede çağrılmaması gerekenler — linter bunları `Wait(0)` gövdesinde yakalar:

| native | maliyet | yerine |
|---|---|---|
| `GetGamePool('CPed'/'CVehicle'/'CObject')` | tüm dünyayı tarar | periyodik tara, sonucu önbellekle |
| `GetActivePlayers` | oyuncu listesi kopyalar | 1–5sn'de bir yenile |
| `GetClosestVehicle` / `GetClosestPed` | shapetest + tarama | önbelleklenmiş pool üzerinden hesapla |
| `GetDistanceBetweenCoords` | native sınırı geçer | `#(vec1 - vec2)` kullan (saf Lua, çok daha ucuz) |
| `RequestModel` / `RequestAnimDict` | streaming isteği | bir kez yükle, `HasModelLoaded` ile bekle |

`#(v1 - v2)` vektör farkı GTA nativei çağırmaz; mesafe karşılaştırmalarında
`GetDistanceBetweenCoords` yerine bunu tercih et.

## Önbellekleme

Her karede değişmeyen değerleri döngü dışına al:

```lua
-- KÖTÜ
while true do
    Wait(0)
    local ped = PlayerPedId()
    local veh = GetVehiclePedIsIn(ped, false)
end

-- İYİ: ox_lib cache veya kendi değişkenin
local ped = cache.ped        -- ox_lib
local veh = cache.vehicle
```

`PlayerPedId()` ucuzdur ama ped değişimini olay üzerinden takip etmek daha ucuzdur.
ox_lib kullanılıyorsa `cache.ped` / `cache.vehicle` / `cache.seat` zaten olay
tabanlı günceller.

## Sunucu tarafı

Sunucuda per-frame döngü yoktur ama eşdeğer hatalar vardır:

- Oyuncu döngüsü içinde tekil DB sorgusu → N+1. Tek sorguda topla.
- `TriggerClientEvent` ile tüm oyunculara (`-1`) sık yayın → bant genişliği.
  Mesafe/ilgi filtresi uygula.
- Her olay tetiklenişinde DB yazımı → toplu yaz (batch) veya debounce et.

## Ölçüm

Kod tahmininle yetinme:

```
resmon 1          # F8 konsolunda, resource CPU süresi
profiler record 500
profiler view
```

Değişiklik öncesi ve sonrası resmon değerini karşılaştır; iddiayı ölçümle destekle.
