---
name: fivem-natives
description: FiveM/GTA V native doğrulama ve arama veritabanı (7191 native, çevrimdışı). Bir FiveM Lua/JS kodu yazarken, düzenlerken veya incelerken native adı, imzası, parametre sırası ya da client/server tarafı söz konusu olduğunda MUTLAKA kullan — kullanıcı istemese bile. Native adını hafızadan yazma; önce doğrula. Tetikleyiciler - FiveM, Cfx, GTA V native, QBCore, QBX, ESX, ox_lib, client.lua/server.lua, fxmanifest, "bu native var mı", "hangi native", "server tarafında çalışır mı", "imzası ne", resmon/performans incelemesi, Lua lint.
license: MIT
compatibility: Python 3.10+. The native index is built once by scripts/build_index.py --fetch (network). The scripts live at the muto-atlas repository root, outside this folder - outside Claude Code install with scripts/install_skills.py or use scripts/mcp_server.py.
---

# FiveM Native Veritabanı

FiveM nativelerini hafızadan yazmak en sık yapılan hatadır: var olmayan bir isim
(`GetPlayerMoney`), yanlış taraf (`DrawMarker` sunucuda) veya yanlış parametre
sırası üretilir ve script sessizce patlar. Bu skill bunu ölçülebilir hale getirir.

**Kural: Bir native adını ezberden yazma. Emin olmadığın her native için önce
`check` çalıştır.**


## ⛔ VERİ EKSİKSE TAHMİN ETME — önce kapı

Bu skill'in her cevabı `data/` altındaki katmanlara dayanır. Bir katman
yoksa sorgu **exit 2** döner. O noktada yapılacak tek şey **durmak**:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --plan     # hiçbir şey yazmaz, durumu gösterir
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py"            # eksik katmanları kurar
```

`--plan` çıktısı "N/M katman kurulu" der ve eksik olanı adıyla listeler
(M sabit değildir, `setup.py` hesaplar — buraya sayı yazma).
Kurulum kullanıcının **kendi GTA V kurulumundan** üretir; komut `/asset-setup`.

⛔ **Veri yokken cevap üretme.** Exit 2 gördüğünde kullanıcıya hangi katmanın
eksik olduğunu ve tek satırlık kurulum komutunu söyle. Tahmine düşmek bu
aracın var oluş sebebine aykırıdır — yanlış bir `fxName`, yanlış bir bayrak
ya da olmayan bir prop adı **sessizce** kabul edilir ve tur kaybettirir.

ℹ️ **Veri neden repoda gelmiyor:** `entities.db` tek başına 214 MB (GitHub
dosya sınırı 100 MB) ve içerik Rockstar'a ait — yeniden dağıtımı telif
sorunudur. Yan faydası: katman herkesin **kendi oyun sürümünden** gelir.
Merkezî tek kopya dağıtılsaydı herkes tek sürüme mahkûm olurdu (ölçüldü:
bu kurulumda 1271 `m26_*` arketip var, hazır dump'ta 0).
## Veri

`data/` içinde çevrimdışı, birleştirilmiş indeks:

| küme | adet |
|---|---|
| toplam native | 7191 |
| client-only | 6830 |
| shared (client + server) | 232 |
| server-only | 129 |

Kaynaklar: `runtime.fivem.net/doc/natives.json` (GTA V) +
`natives_cfx.json` (Cfx) + `citizenfx/fivem` kaynağındaki sunucu handler kayıtları.
Sağlama ve tarih için `python scripts/nativedb.py stats`.

> GTA V native listesi upstream'de `apiset` taşımaz — docs.fivem.net onları
> client varsayar. Sunucu erişilebilirliği Cfx bildirim setinden ve
> `ServerGameState_Scripting.cpp` içindeki `RegisterNativeHandler` kayıtlarından
> türetilir; iki taraf da destekliyorsa `shared` olarak işaretlenir.

## Komutlar

`$P` = plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `scripts/nativedb.py`'yi içeren muto-atlas klasörü).

```bash
# Var mı? Hangi tarafta? — kod yazmadan ÖNCE
python "$P/scripts/nativedb.py" check GetEntityCoords DrawMarker GetPlayerMoney

# Tam imza, parametre açıklamaları, docs linki, Lua örneği
python "$P/scripts/nativedb.py" show GetVehicleNumberPlateText

# Doğru nativei bul (ad hatırlanmıyorsa)
python "$P/scripts/nativedb.py" search vehicle fuel --apiset server

# Bir namespace'te sunucudan çağrılabilenler
python "$P/scripts/nativedb.py" ns VEHICLE --apiset server

# Yazdığın Lua'yı denetle
python "$P/scripts/lint_lua.py" resources/<kaynak-adi>
```

`check` var olmayan native bulursa **exit 1** döner ve yakın isimleri önerir.

## Zorunlu akış

1. **Kod yazmadan önce** — kullanacağın nativeleri tek `check` çağrısında doğrula.
   Çıktıdaki `[client] / [server] / [shared]` etiketi hangi dosyaya yazacağını belirler.
2. **İmzayı `show`'dan al**, hafızadan değil. Parametre sırası ve tipleri oradadır.
3. **Kod yazdıktan/düzenledikten sonra** — dokunduğun kaynağa `lint_lua.py` çalıştır.
   E00x hatası kalmadan işi bitmiş sayma.
4. **Kullanıcıya native önerirken** docs linkini (`show` çıktısındaki `docs` satırı)
   birlikte ver.

`check` bir nativei bulamıyor ve yakın öneri de yoksa: **o native yoktur.** Uydurma.
Muhtemelen aradığın şey bir framework fonksiyonudur (QBCore/ox_lib exports) —
native değil. Bunu kullanıcıya açıkça söyle.

## Taraf disiplini

| dosya | çağırabileceği |
|---|---|
| `client.lua` | `client` + `shared` |
| `server.lua` | `server` + `shared` |
| `shared.lua` / config | yalnız `shared` |

Sunucuda **çalışmayan** yaygın yanlışlar: `DrawMarker`, `DrawText3D`,
`GetClockHours`, `RequestModel`, `TaskGoToCoord`, `PlaySoundFrontend`,
`SetNuiFocus`, tüm `HUD`/`GRAPHICS`/`CAM`/`STREAMING` namespace'i.

Sunucuda entity işi yapman gerekiyorsa `--apiset server` ile ara: `shared` işaretli
entity nativeleri (`GetEntityCoords`, `SetEntityCoords`, `DeleteEntity`,
`CreateVehicle`, `GetPlayerPed`) sunucu tarafında da geçerlidir.

`Wait`, `CreateThread`, `RegisterNetEvent`, `TriggerClientEvent`,
`PerformHttpRequest`, `GetPlayers` native değildir — Citizen runtime fonksiyonlarıdır,
veritabanında aranmazlar ve iki tarafta da vardır.

## Lint kuralları

| kural | anlamı |
|---|---|
| `E001` | native yok (yazım hatası veya uydurma) |
| `E002` | yanlış taraf — client-only native sunucu dosyasında |
| `E003` | fazla argüman — imzadan çok parametre verilmiş |
| `W101` | `RequestModel`/`RequestAnimDict` her karede çağrılıyor |
| `W102` | `GetGamePool`/`GetActivePlayers` `Wait(0)` döngüsünde |
| `W103` | mesafe hesabı her karede, sonuç önbelleklenmiyor |
| `W104` | eksik argüman — yasal ama kasıtlı olduğunu doğrula |

E00x hatadır, düzelt. W1xx uyarıdır; `GetEntityCoords(ped)` gibi yaygın deyimler
W104 üretir ve genelde sorun değildir — bakıp geç.

Linter `Bridge.HasItem()` gibi tablo/metot çağrılarını ve taranan dosyalarda
tanımlı yerel fonksiyonları native saymaz. Yine de bir yanlış pozitif görürsen
tanımın lint kapsamındaki dosyalarda olduğundan emin ol.

## Performans ve derinlik

Per-frame maliyet, entity önbellekleme ve resmon hedefleri için
`references/performance.md`. Sık karıştırılan native çiftleri ve doğru karşılıkları
için `references/pitfalls.md`.

## Framework çağrıları — native değil ama aynı şekilde sessiz

`lint_lua.py` yalnız **GTA native**'lerini doğrular. Bir QBCore/Qbox/ESX/ox
kaynağındaki hataların çoğu native'de değil **framework çağrısındadır** ve
hiçbiri hata fırlatmaz: olmayan event tetiklenir (log bile yok), olmayan export
çağrılır (`nil value` ancak o satır çalışınca), `lib.showTextUi` küçük harfle
yazılır (modül yok, sessiz).

```bash
python "$P/scripts/assetdb.py" framework <ad>
python "$P/scripts/assetdb.py" framework --check
```

⛔ **Otorite kurulu sunucudur, upstream GitHub değil.**
Tam katman: `references/framework-api.md`

## Güncelleme

Cfx yeni native eklediğinde:

```bash
python "$P/scripts/build_index.py" --fetch
```

Upstream'i yeniden indirir ve indeksi yeniden üretir.
