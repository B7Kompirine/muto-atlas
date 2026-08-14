# Framework API — QBCore / Qbox / ESX / ox

Sorgu: `assetdb.py framework <ad>` · Denetim: `assetdb.py framework --denetle`
Üretim: `python scripts/build_framework.py --resources <sunucu resources>`

## Neden ayrı bir katman

`lint_lua.py` yalnız **GTA native**'lerini doğrular. Ama bir QBCore/ox
kaynağındaki hataların çoğu native'de değil, **framework çağrısındadır** — ve
hiçbiri hata fırlatmaz:

| hata | belirti |
|---|---|
| olmayan event tetiklenir | tetikleme hiçbir yere gitmez, log yok |
| olmayan export çağrılır | `nil value` **ancak o satır çalışınca** — belki ayda bir |
| `lib.showTextUi` (küçük i) | modül yok, nil, sessiz |

## ⛔ Otorite kurulu sunucudur, upstream GitHub DEĞİL

İndeks `github.com/qbcore-framework` ya da `overextended` master'ından değil,
**sunucuda kurulu kaynaklardan** üretilir. Sebep: bir export upstream'de eklenmiş
ama senin `qb-core`'unda yoksa, "geçerli" demek yanıltır. `fxmanifest`'teki
`version` alanı da her satıra yazılır.

Ölçüm (musti'nin sunucusu, 2026-08): **173 kaynak, 12.713 satır** —
2.569 event tanımı · 1.002 export · 501 komut · 321 callback · 115 ox_lib modülü.

## Ekosistem — hangisi neyin yerine geçiyor

| framework | çekirdek | durum |
|---|---|---|
| **QBCore** | `qb-core` | `exports['qb-core']:GetCoreObject()` |
| **Qbox** | `qbx_core` | QBCore forku; kod kalitesi/güvenlik/performans için yeniden yazıldı, ox kaynaklarıyla tümleşik |
| **ESX** | `es_extended` | ayrı ekosistem; `esx:playerLoaded` gibi kendi olayları |
| **ox_core** | `ox_core` | Overextended'in kendi çekirdeği |

**Qbox'ta `GetCoreObject` yerel olarak yoktur** — köprü katmanı QBCore biçimli
çağrıyı uyumluluk için kabul eder. Qbox belgesi der ki: doğrudan veritabanı
tablosuna dokunan, `qb-core`'un belgelenmemiş içine giren ya da geçersiz
kullanım yapan kaynaklar dışında çoğu QBCore scripti değişmeden çalışır.

Bu yüzden doğru kalıp tek çekirdeğe sabitlemek değil, **köprü**:

```lua
local core = exports['qb-core'] and exports['qb-core']:GetCoreObject()
          or exports.qbx_core and exports.qbx_core:GetCoreObject()
```

## Kurulu olmayan kaynağa çağrı — en yüksek sinyal

`framework --denetle` çıktısının **A** bölümü. Ölçüldü: **345 çağrı / 58 kaynak**
sunucuda kurulu olmayan bir kaynağa gidiyor — `ox_inventory` 57, `qbx_core` 44,
`es_extended` 27. Hepsi çalışma anında sessizce başarısız olur.

## ox_lib — ölçülmüş iki tuzak

**1. Modül listesini `imports/` klasöründen çıkarma.** `imports/` 59 klasör verir
ama gerçek API yüzeyi **115**'tir; `lib.notify` `resource/interface/client/notify.lua`
altında tanımlıdır. Yalnız `imports/`'a bakan ilk sürüm 2.216 `lib.*` çağrısının
**%46,8'ini** "olmayan modül" diye işaretledi — `lib.notify` tek başına 380 kez
kullanılıyor. Düzeltince yanlış pozitif **%0,8**'e düştü.

**2. Belge listesi kurulu sürümü göstermez.** `overextended.dev` modül listesi ile
dosya sistemi aynı değildir. Dosya sistemi otoritedir.

## Dinamik export döngüsü — literal ad aramak yetmez

`ox_target` export'larını şöyle verir:

```lua
for index, value in pairs(api) do exports(index, value) end
```

Yani `addBoxZone`, `addLocalEntity`, `removeZone` gibi **30+ gerçek export**
kaynakta tırnak içinde hiç geçmez; yalnız `function api.X(` olarak tanımlıdır.
Bu kalıbı tanımayan bir denetim onları "tanımsız export" sayar. Tanıyınca yazım
hatası adayı **69 → 29** çağrıya düştü.

## Bu denetim neden ERROR değil UYARI

Kalan 29 adayın çoğu **JS/C# ile yazılmış kaynakların export'ları** —
`screenshot-basic:requestScreenshotUpload`, `oxmysql:execute`. Lua taramasında
görünmezler. Aynı şekilde `chat:addMessage` (79 kullanım) FXServer'ın yerleşik
`chat` kaynağındandır ve sunucunun `resources/` ağacında klasörü yoktur.

Bir linter her şeye kızarsa kullanılmaz hale gelir ve **gerçek hataları da
kaçırırsın**. Bu yüzden A bölümü güçlü sinyal, B/C/D uyarıdır.

## ⛔ Satır yokluğu kaynak yokluğu değildir

İlk sürümde "kurulu kaynak" kümesi üretilen satırlardan türetildi. Hiç export/event
tanımlamayan bir kaynak sıfır satır üretir ve **"kurulu değil" görünür** — bu
yaşandı (`muto-ai`). Çözüm: her taranan kaynak için ayrı bir `kind=resource`
satırı yazılır. Kurulu küme oradan okunur.

## Sorgular

```bash
assetdb.py framework GetCoreObject              # kim nerede çağırıyor
assetdb.py framework qb-core --tanim            # qb-core'un SAĞLADIKLARI
assetdb.py framework --kind lib_module          # ox_lib'in 115 modülü
assetdb.py framework --kind command             # kayıtlı 501 komut
assetdb.py framework --denetle                  # A/B/C/D çapraz denetim
```

## Kaynaklar

`docs.fivem.net/natives` · `docs.qbcore.org` · `docs.qbox.re` ·
`docs.esx-framework.org` · `overextended.dev/docs/ox_lib` ·
`github.com/{overextended,qbcore-framework,qbox-project,esx-framework}`

Not: `docs.qbcore.org` üzerindeki JetBrains sayfası sponsor bilgisidir, API değil.
