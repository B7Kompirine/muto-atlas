---
description: Objenin üstünde canlı, tıklanabilir HTML ekran — DUI panel + raycast/UV etkileşim zinciri
argument-hint: <model adı veya "ne yapmak istediğin">
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

Bir dünya objesine **gerçek HTML/JS çalışan, etkileşimli bir ekran** koyar:
ATM tuş takımı, kasa terminali, kamera monitörü, laptop, keypad, arcade.

## ÖNCE OKU

Tam reçete, ölçülmüş değerler ve 13 maddelik tuzak kataloğu:
`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/3dnui-dui-panel.md`

## ADIM 1 — Hangi render yolu (tahmin etme, sorgula)

```bash
powershell -NoProfile -ExecutionPolicy Bypass \
  -File "${CLAUDE_PLUGIN_ROOT}/scripts/screentex.ps1" -Model <model> -All
```

- **`emissive*` shader + adı `screen`/`scr`/`rt` içeren doku var** →
  `AddReplaceTexture` yolu. `origTxd` neredeyse her zaman **model adının
  kendisidir** (doku modele gömülü), `origTxn` çıktıdaki `txn='...'`.
- **Ekran dokusu yok** (keypad, CCTV, çoğu prop) → **dünya quad'ı** yolu
  (`CreatePanel`). Zorlama, ReplaceTexture'ın uygulanacağı materyal yok.
- **O modelden sahnede birden fazla örnek var** → yine dünya quad'ı.
  `AddReplaceTexture` materyal bazında ve **global**dir; o modeli kullanan
  bütün objeler aynı sayfayı gösterir.

ytyp'deki `textureDict` alanına bakıp `origTxd` yazma — **o alan ekran
sözlüğü değildir** (ölçüldü: `prop_monitor_01a`).

## ADIM 2 — Konum ve yönelim

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" show  <model>   # bbox -> yüz nerede
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" where <model>   # dünyadaki gerçek konumlar
```

Koordinat **uydurulmaz**, indeksten alınır.

## ADIM 3 — Panel kurulumu

```lua
local id = exports['cr-3dnui']:CreatePanel({
  url    = ('nui://%s/html/index.html?res=%s'):format(res, res),
  pos    = <yüzey noktası>,
  normal = <yüzey normali>,
  up     = <normale DİK hale getirilmiş up>,   -- roll için şart
  width = <m>, height = <m>,
  resW = 1024, resH = 512,                     -- oran panel oranıyla AYNI
  faceCamera = false, frontOnly = true,        -- sabit ekran
  zOffset = 0.002,
})
```

- `up` verilmezse roll yok; `up` normale paralelse basis sessizce bozulur.
- `faceCamera=false` **ve** `up` birlikte verilmezse basis önbelleği açılmaz
  (her kare yeniden hesap).
- URL dosyası tüketici kaynağın `fxmanifest.lua` `files { }` listesinde
  olmak **zorunda**.

## ADIM 4 — Etkileşim modu

| İhtiyaç | Mod |
|---|---|
| Duvarda büyük panel, bakarak tıkla | `uv` — `RaycastPanel` + `SendMouseMove/Down/Up` |
| Laptop/terminal, imleç ekranda gezsin | `key2dui` — `GetDisabledControlNormal(0,1/2)` deltası |
| Klavye girişi (oyun) | `BeginFocus` + `SetFocusKeymap` (yalnız **basma** var) |
| Metin girişi | `DisplayOnscreenKeyboard` — DUI'ye metin enjekte eden native yok |

`key2dui`'de imleci **HUD'a değil DUI'nin içine** çizdir (`SendMessage`),
yoksa çift/kaymış imleç olur. İmleç mesajını 0.002 UV / 33 ms ile kıs.

## ADIM 5 — Sunucu otoritesi

DUI **client-only** ve **senkronize değildir**. Durum sunucuda tutulur,
`TriggerClientEvent` ile yayılır, her istemci kendi DUI'sine `SendMessage`
ile yansıtır. **Şifre/kod karşılaştırması sayfada değil sunucuda yapılır.**

## ADIM 6 — Temizlik

`onResourceStop`: `DestroyPanel` / `DestroyReplaceTexture` / `EndFocus` +
ekran klavyesi akışı varsa `FreezeEntityPosition(ped, false)`.

## GÖRSEL GEREKİRSE

Ekran arka planı, ikon, logo, doku — **üretme.** Fikri anlat, kullanıcıya
hazır bir prompt ver ve fotoğrafı **kullanıcının** üretmesini iste. Prompt
panelin `resW:resH` oranını içersin. Görsel gelene kadar düzeni CSS ile kur,
doğru ölçüde boş kutu bırak.

## TEST

Sadece Lua/HTML değiştiyse `restart` yeter. **Stream dosyası (asset)
değiştiyse sunucudan ÇIKIP YENİDEN BAĞLAN** — FiveM stream dosyalarını
cache'ler, restart yetmez.
