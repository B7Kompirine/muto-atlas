# Sık yapılan native hataları

Bu dosyadaki her iddia `data/natives.merged.json` üzerinden doğrulanmıştır.
Şüphelendiğinde `nativedb.py check` ile teyit et.

## 1. Namespace'e göre taraf

Sunucudan **hiçbir** nativei çağrılamayan namespace'ler (34 adet):

```
APP AUDIO BRAIN CAM CLOCK CUTSCENE DATAFILE DECORATOR DLC EVENT FILES FIRE
GRAPHICS INTERIOR ITEMSET LOADINGSCREEN LOCALIZATION MOBILE MONEY NETSHOPPING
PAD PATHFIND PHYSICS RECORDING REPLAY SAVEMIGRATION SCRIPT SHAPETEST SOCIALCLUB
STATS STREAMING SYSTEM WATER ZONE
```

Bu namespace'lerden bir native `server.lua` içinde görürsen bu bir hatadır.
`CLOCK` özellikle tuzaktır: `GetClockHours()` sunucuda yoktur, `os.date` kullan.

Sunucudan kısmen çağrılabilenler:

| namespace | toplam | sunucudan |
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

Yani `VEHICLE` nativelerinin yalnızca %6'sı sunucudan çağrılabilir. "Entity nativesi
sunucuda çalışır" genellemesi yanlıştır — tek tek `check` et.

## 2. Baştaki alt çizgi

Cfx'te adı belgelenmemiş nativeler alt çizgiyle başlar ve Lua'da da alt çizgiyle
çağrılır. Alt çizgiyi düşürmek `E001` üretir:

| yanlış | doğru |
|---|---|
| `AddTextComponentString(...)` | `AddTextComponentSubstringPlayerName(...)` veya `_AddTextComponentString(...)` |
| `GetWeatherTypeTransition(...)` | `_GetWeatherTypeTransition(...)` |

`check` her iki yazımı da tanır ve kanonik adı gösterir.

## 3. Var olmayan ama çok yazılan isimler

Bunlar native değildir — framework fonksiyonu ararken native sanılırlar:

| yazılan | gerçekte |
|---|---|
| `GetPlayerMoney` | QBCore: `Player.PlayerData.money`, ESX: `xPlayer.getMoney()` |
| `TriggerServerCallback` | QBCore: `QBCore.Functions.TriggerCallback`, ox_lib: `lib.callback` |
| `GetWeaponName` | native yok; `WEAPON` hash → locale/config eşlemesi yap |
| `HasEntityBeenDamagedByAnyWeapon` | `HasEntityBeenDamagedByWeapon(entity, weaponHash, weaponType)` |
| `GetVehicleFuel` | `GetVehicleFuelLevel(vehicle)` (Cfx, client) |

Kullanıcı "şu nativei kullan" derse ve `check` bulamıyorsa, bunun bir native
olmadığını ve hangi framework API'sinin karşılık geldiğini söyle.

## 4. Argüman sayısı

FiveM Lua'da eksik argüman hata vermez, `nil`/`0` olur. Bu yüzden yanlış parametre
sayısı sessizce yanlış davranışa döner:

```lua
-- GetEntityCoords(Entity entity, BOOL alive) — yaygın ve zararsız
local c = GetEntityCoords(ped)

-- HATA: fazla argüman, imza tek parametre alır
local plate = GetVehicleNumberPlateText(veh, 5)
```

Fazla argüman `E003` (hata), eksik argüman `W104` (uyarı) üretir.

## 5. Metot çağrısı native değildir

`Bridge.HasItem(...)`, `QBCore:GetCoreObject()`, `Player.Functions.AddItem(...)`
noktalı/iki noktalı çağrılardır; linter bunları atlar. Sen de bunları native diye
`check` etme — veritabanında yoktur.
