# Objenin üstünde canlı, tıklanabilir ekran (DUI)

**Ne zaman okunur:** ATM tuş takımı, kasa terminali, kamera monitörü, laptop, keypad, tabela — objede gerçek HTML/JS çalışsın, tıklansın.
**When to read:** a live, clickable screen on an object (DUI) — ATM, keypad, monitor; raycast to UV; jitter when attached.
**Kaynak:** `dui-ekran.md` (tamamı) + eski SKILL özeti (2026-07) · **Ölçüm:** 5 model RPF'ten; cr-3dnui v2.6 kaynağı okundu; kemiğe bağlı panel titremesi ölçüldü
**Önce:** `_dal.md` · gövde › `govde/bayraklar.md` (`specialAttribute`), `govde/arac-tuzaklari.md` §1

---

## Kod yazmadan bilinmesi gereken beş şey

**`dui-ekran.md`** · komut: `/prop`

Kod yazmadan bilinmesi gereken beş şey:

- **Üç render yolu vardır ve seçimi veri belirler.** Modelin gerçek ekran
  dokusu varsa `AddReplaceTexture` (en gerçekçi), yoksa dünya uzayında quad
  (`CreatePanel`), hareketli entity'de `AttachPanelToEntity`. Hangisi
  olduğunu **sor, deneme**: `screentex.ps1 -Model <model>`.
- **`AddReplaceTexture` materyal bazında ve GLOBAL'dir.** O istemcide o
  dokuyu kullanan bütün objeler değişir. Bankada 3 ATM varsa üçü de aynı
  sayfayı gösterir → farklı içerik gerekiyorsa bu yol yanlıştır.
- **Ekran = `emissive*` shader ve doku neredeyse her zaman modele GÖMÜLÜDÜR**
  → `origTxd` = **model adının kendisi**. Ölçüldü: `prop_atm_01` →
  `prop_cashpoint_screen`, `prop_laptop_lester` → `prop_lester_screen`,
  `prop_tv_flat_01` → `script_rt_tvscreen`. **ytyp'deki `textureDict` alanı
  ekran sözlüğü DEĞİLDİR** — oraya bakıp `origTxd` yazma.
- **Keypad'lerin ve CCTV kameralarının ekran dokusu YOKTUR** (üç keypad
  prop'unda ölçüldü; `hei_prop_hei_keypad_01`'de gömülü doku sayısı 0).
  Keypad UI'si ancak dünya quad'ı ile yapılır.
- **DUI client-only ve senkronize DEĞİLDİR.** Panel bir dünya objesi değil;
  her istemci kendi panelini kurar. Durum sunucuda tutulur, `SendMessage` ile
  yansıtılır. **Şifre/kod karşılaştırması sayfada değil sunucuda yapılır** —
  sayfanın JS'i okunabilir, mesajı taklit edilebilir.

Panel kurarken: `faceCamera=false` + `frontOnly=true` + normale **dik hale
getirilmiş** `up` (ikisi birden verilmezse basis önbelleği açılmaz ve roll
desteklenmez), `resW:resH` panel oranıyla aynı, URL dosyası tüketici kaynağın
`files { }` listesinde.




---


Bir objenin üstünde **gerçek HTML/JS çalışan, tıklanabilen bir ekran** olsun
isteniyorsa yol bellidir: DUI (Direct UI) → runtime texture → dünya uzayında
çizim ya da materyal değiştirme, üstüne kamera ışını ile UV hesabı.

Kaynak: `cr-3dnui` (codyraves) v2.6 — kütüphane + 4 demo satır satır okundu.
Buradaki her madde ya o koddan ya da bu plugindeki asset/native verisinden
**ölçüldü**. Tahmin edilen bir şey varsa açıkça öyle yazılmıştır.

---

## 0. ÖNCE KARAR: üç render yolundan hangisi

| Yol | Nasıl çalışır | Ne zaman |
|---|---|---|
| **A. Dünya quad'ı** (`CreatePanel`) | `DrawTexturedPoly` ile 2 üçgen, serbest konum + normal | Modelin ekranı **yoksa**; duvar, keypad yüzü, tahta, hava boşluğu |
| **B. Entity'ye bağlı quad** (`AttachPanelToEntity` / `...ToBone`) | Aynı quad, her kare entity uzayından tazelenir | Araç, ped, taşınan prop |
| **C. Materyal değiştirme** (`AddReplaceTexture`) | Modelin kendi ekran dokusunun yerine DUI konur | Modelin **gerçek ekran dokusu varsa**: TV, laptop, monitör, ATM |

C yolu en gerçekçi görünendir (ekran modelin içinde, açıyla doğru eğilir,
ışık alır) **ama iki sert kısıtı vardır**:

1. Modelin ekran dokusu olmak zorunda. Yoksa uygulanacak bir şey yok.
2. `AddReplaceTexture` **materyal bazında ve GLOBAL'dir** — o istemcide o
   dokuyu kullanan **bütün** objeler değişir. Bankada 3 ATM varsa üçünde de
   aynı sayfa görünür. Tek tek farklı içerik isteniyorsa C yolu yanlıştır.

> Ekranı olmayan bir modele C yolunu denemek en sık yapılan hatadır.
> Modelde ekran var mı — **sorulur, denenmez** (§6).

---

## 1. DUI ZİNCİRİ — beş adım, hepsi gerekli

```lua
local dui = CreateDui(url, resW, resH)          -- CEF sayfası aç
local handle = GetDuiHandle(dui)                -- NUI window handle
local txd = CreateRuntimeTxd('my_txd')          -- runtime sözlük
CreateRuntimeTextureFromDuiHandle(txd, 'my_tex', handle)
-- artık 'my_txd' / 'my_tex' çizim natives'lerinde kullanılabilir
DestroyDui(dui)                                 -- temizlik ŞART
```

Doğrulanmış imzalar (plugin native indeksi):

| Native | İmza | Not |
|---|---|---|
| `CreateDui` | `(char* url, int w, int h) -> long` | 0x23EAF899 |
| `GetDuiHandle` | `(long dui) -> char*` | 0x1655D41D |
| `IsDuiAvailable` | `(long dui) -> BOOL` | 0x7AAC3B4C — **kullanılmıyor, kullanılmalı** (§9.3) |
| `SetDuiUrl` | `(long dui, char* url)` | 0xF761D9F3 — sayfa değiştirmek için DUI'yi yeniden yaratmaya gerek yok |
| `SendDuiMessage` | `(long dui, char* json)` | 0xCD380DA9 |
| `SendDuiMouseMove` | `(long dui, int x, int y)` | **PİKSEL**, UV değil |
| `SendDuiMouseDown/Up` | `(long dui, char* button)` | `'left'` / `'middle'` / `'right'` |
| `SendDuiMouseWheel` | `(long dui, int deltaY, int deltaX)` | **iki delta alır** (§9.4) |
| `AddReplaceTexture` | `(origTxd, origTxn, newTxd, newTxn)` | docs: "Experimental" |

### URL kuralı

`nui://<resource_adi>/<yol>/index.html` — ve o dosya **o kaynağın
`fxmanifest.lua`'sındaki `files { }` listesinde olmak zorundadır.** Değilse
DUI boş/siyah kalır, hata da vermez.

`GetParentResourceName()` DUI sayfası içinde **bulunmayabilir**. Sayfanın
`fetch("https://<resource>/callback")` yapması gerekiyorsa kaynak adını
query string ile geçir:

```lua
('nui://%s/html/index.html?res=%s'):format(res, res)
```

(whiteboard demosu bunu yapıyor; `RegisterNUICallback` DUI'den gelen fetch'i
normal NUI gibi yakalıyor — yani **DUI → Lua geri yolu vardır**, tek yön
değildir.)

---

## 2. QUAD ÇİZİMİ — mirror, roll ve z-fighting

Panel dört köşeden çizilir; iki `DrawTexturedPoly` çağrısı.

```
v1 = c - r*hw + u*hh      v2 = c + r*hw + u*hh
v4 = c - r*hw - u*hh      v3 = c + r*hw - u*hh
```

- `right = cross(normal, up)`, `up = cross(right, normal)` — **sağ el**
  düzeni. Ters kurulursa backface culling paneli görünmez yapar; "panel
  oluştu ama ekranda yok" şikâyetinin birinci sebebi budur.
- `up` verilmezse dünya-up (0,0,1) kullanılır → **roll desteklenmez**.
  Yatık monitör, eğik dashboard, yan yatmış tabela için `up` **verilmelidir**.
  `up` normal ile paralelse çapraz çarpım sıfırlanır → kütüphane (0,1,0)'a
  düşer; yani sessizce yanlış bir yönelim üretir. Kendi `up`'ını verirken
  **önce normale dik hale getir** (Gram-Schmidt):
  `up_ortho = normalize(up - normal * dot(normal, up))`
- **UV, U ekseninde çevrilerek** verilir (v1→(0,1), v2→(1,1), v3→(1,0)).
  Bu olmadan yazı ayna görüntüsü çıkar. Kendi çizimini yazarsan bunu atlama.
- `zOffset` = panelin yüzeyden dışarı itilmesi. Varsayılan **0.002 m**,
  `depthCompensation='screen'` verilirse **0.004 m** + eğime bağlı ek
  (`min(0.35, |normal.z|) * 0.002`). Küçük tutulursa z-fighting (titreşen
  ekran), büyük tutulursa panel yüzeyden ayrık durur.

### `faceCamera` tuzağı

`faceCamera=true` her karede normali kameraya doğru çevirir. Sonuç:
- panel her yerden okunur ✅
- ama **ön/arka kavramı yok olur** — arkasından bakınca da UI görünür,
  raycast arkadan da tutar ❌
- ve panel artık "dinamik" sayılır, **basis önbelleği devre dışı kalır**

Sabit bir ekran (monitör, ATM, keypad) için doğrusu:
`faceCamera = false` + `frontOnly = true` (+ istersen `frontDotMin`).
Serbest duran bilgi tabelası için `faceCamera = true` mantıklıdır.

### Önbellek şartı (perf)

Kütüphane şunu yapar:
```
isDynamic = (faceCamera and not frontOnly) or (orientationLock and not up)
```
`isDynamic` **false** olmadan köşe noktaları her karede yeniden hesaplanır.
Yani **statik panelde hem `faceCamera=false` hem de `up` verilmelidir**;
sadece birini vermek önbelleği açmaz.

---

## 3. RAYCAST → UV — düzlem kesişimi

```
denom = dot(dir, normal)              -- |denom| < 0.0001 -> ışın düzleme paralel
t     = dot(center - camPos, normal) / denom
hit   = camPos + dir * t
rel   = hit - center
x     = dot(rel, right) / halfW       -- |x| > 1 -> panelin dışında
y     = dot(rel, up)    / halfH
u = (x+1)/2 ;  v = (y+1)/2            -- 0..1
px = u * resW ;  py = v * resH        -- DUI'ye giden PİKSEL
```

Buradan iki sonuç çıkar:

1. **Bu bir shape test değildir.** Işın sonsuz düzlemle kesişir; panelin
   önünde duvar olsa bile isabet sayılır. Arada engel olup olmadığını
   önemsiyorsan ayrıca `StartShapeTestRay` at ve mesafeleri karşılaştır.
2. **`resW`/`resH` hem netliği hem tıklama hassasiyetini belirler.** Panel
   1.0 m genişse ve `resW=512` ise bir pikselin dünyadaki karşılığı ~2 mm.
   Küçük butonlu bir UI'de tıklama "kademeli" hissettirir. Panel oranı ile
   DUI oranı **eşleşmelidir** — geniş panele kare DUI verilirse UI gerilir
   ve isabet noktası kayar.

Önerilen başlangıç: geniş panel `1024×512`, kare panel `1024×1024`. Yoğun
metin varsa `2048×1024`.

---

## 4. HAREKETLİ ENTITY'YE BAĞLAMA — jitter'ın gerçek sebebi

`AttachPanelToEntity` her tetiklemede:
```
pos    = GetOffsetFromEntityInWorldCoords(ent, off.x, off.y, off.z)
normal = entity matrisi ile localNormal'ın döndürülmüşü
```
ve bunu **tek bir merkezî thread** yapar (`updateInterval`, `nextUpdate`).
Her tüketici kendi 0-tick döngüsünü açarsa güncelleme kadansı tutarsız olur
ve panel araca göre "basamaklanır". Kendi loop'unu **yazma**, kütüphanenin
sürücüsünü kullan.

- `updateInterval = 0` → her karede (en pürüzsüz, en pahalı)
- `updateMaxDistance` → uzaktayken transform güncellemesini atlar
  (çizim zaten `renderDistance` ile ayrı kısıtlı)

### Ölçülmüş bulgu: kemiğe bağlı prop + prop'a bağlı panel = titrer

cardemo üç mod deniyor ve sonuç net:

| Mod | Panel neye bağlı | Sonuç |
|---|---|---|
| `roof` | doğrudan araca | titremez |
| `dashprop` | bone-attached prop'a | **titrer** (referans mod olarak bırakılmış) |
| `dashstable` | prop'un pozu araç uzayına **pişirilip** araca | titremez |

Sebep: bone transform'u ile entity transform'u aynı karede aynı anda
tazelenmiyor; iki kademeli zincir faz farkı üretiyor. Çözüm zinciri kısaltmak:

1. Prop'u kemiğe bağla (yalnız **görsel** için).
2. Panelin prop-yerel pozunu dünya uzayına, oradan **araç-yerel** uzaya çevir
   (`GetOffsetFromEntityGivenWorldCoords` + matris izdüşümleri).
3. Paneli **araca** bağla, prop'a değil.

Bu, "araç ROT çözüldü" denen şeyin tamamıdır. Ped'e/prop'a bağlı panellerde
de aynı kural geçerlidir: **panel, hiyerarşide mümkün olan en üst kararlı
entity'ye bağlanır.**

---

## 5. ETKİLEŞİM — üç giriş modeli

| Mod | İmleç nerede | Ne zaman |
|---|---|---|
| `uv` | ekran ortası (crosshair) — kamera ışını | Duvara asılı büyük panel, oyuncu bakarak tıklar |
| `native_mouse` | gerçek NUI imleci (`GetNuiCursorPosition` → `GetWorldCoordFromScreenCoord`) | NUI focus zaten açıkken |
| `key2dui` | panele kilitli sanal imleç, fare deltasıyla sürülür | Laptop/terminal — kamera sabit, imleç ekranda gezer |

### key2dui — ölçülmüş detaylar

```lua
DisableControlAction(0, 1, true)   -- LOOK_LR   (deltayı kendimize alıyoruz)
DisableControlAction(0, 2, true)   -- LOOK_UD
DisableControlAction(0, 24, true)  -- ATTACK    (ateş etmesin)
DisableControlAction(0, 25, true)  -- AIM
DisableControlAction(0, 257, true) -- ATTACK2
local dx = GetDisabledControlNormal(0, 1)
local dy = GetDisabledControlNormal(0, 2)
u = clamp01(u + dx * speed)        -- speed: 0.010 (whiteboard) … 0.030 (laptop)
v = clamp01(v + dy * speed)
```

- **İmleci HUD'a çizme, DUI'nin İÇİNE çizdir.** whiteboard demosu HUD imlecini
  bilerek kapatıyor: dünya uzayındaki quad ile ekran uzayındaki sprite
  perspektifte örtüşmez, "çift imleç" ve kayma hissi verir. Doğrusu
  `SendMessage(panelId, {type='cursor', u=…, v=…})` ile imleci sayfanın
  kendisine çizdirmek.
- İmleç mesajını her karede gönderme: whiteboard demosu **0.002 UV hareket
  veya 33 ms** eşiğiyle kısıyor. Kısılmazsa saniyede ~60 JSON mesajı gider.
- Fare tuşu bırakmayı **kaçırma**: mod değişimi, panelden çıkma, kaynak
  durması — hepsinde `SendMouseUp` çağrılmalı, yoksa sayfa "basılı" kalır
  (whiteboard'da bu, fırçanın takılı kalması demek).

### Klavye — gerçek klavye yok

DUI'ye **key event enjekte eden bir native yok.** cr-3dnui'nin yaptığı şey
`IsDisabledControlJustPressed` ile kontrolü okuyup DUI'ye **mesaj** atmak:

```json
{ "type": "key", "key": "W", "code": 32 }
```

Bunun anlamı:
- yalnız **basma** var; key-up, auto-repeat, modifier yok
- **metin girişi yok** → metin gerekiyorsa `DisplayOnscreenKeyboard`
  (whiteboard demosu böyle yapıyor: oyuncuyu dondur → klavye aç →
  `UpdateOnscreenKeyboard()` döngüsü → sonucu DUI'ye mesajla gönder)
- `SetFocusKeymap` ile hangi kontrolün hangi harf olduğunu **sen** yazarsın

`BeginFocus(panelId, opts)` seçenekleri (ölçülmüş varsayılanlar):
`maxDist=7.0` · `strict` → `DisableAllControlActions(0)` ·
`autoExitOnMiss` + `missGraceMs=250` (küçük ıskalarda anında çıkmasın) ·
`exitControls={200,177}` (ESC/BACKSPACE) · `allowLook` (kamera serbest) ·
`sendFocusMessages` → sayfaya `{type='focus', state=true/false}`.

> README `focus_on` / `focus_off` yazıyor, **kod `{type='focus', state=…}`
> gönderiyor.** Sayfayı README'ye göre yazarsan focus mesajı hiç yakalanmaz.
> Kaynak doğruyu söyler, README değil.

---

## 6. MODELDE EKRAN VAR MI — sorgula, deneme

`AddReplaceTexture(origTxd, origTxn, …)` iki ad ister ve **ikisi de tahmin
edilemez**: prop adı ile txd adı çoğu zaman farklıdır, bir propta 5-10 doku
vardır ve hangisinin ekran olduğu isimden anlaşılmaz. cr-3dnui'nin laptop
demosu bu yüzden 10 adaylık liste tutup `/lapnext` ile tek tek çeviriyor.
Bu tahmindir. Bizde sorgu var:

```bash
powershell -NoProfile -ExecutionPolicy Bypass \
  -File "${CLAUDE_PLUGIN_ROOT}/scripts/screentex.ps1" -Model <model> -All
```

### Ölçülen sonuçlar (5 model, doğrudan RPF'ten)

| Model | Ekran dokusu | Shader | Sözlük |
|---|---|---|---|
| `prop_atm_01` | `prop_cashpoint_screen` | `emissive` | gömülü → **origTxd = `prop_atm_01`** |
| `prop_laptop_lester` | `prop_lester_screen` | `emissive_speclum` | gömülü → origTxd = `prop_laptop_lester` |
| `prop_monitor_01a` | `prop_moniter_desktop_01` | `emissive` | gömülü → origTxd = `prop_monitor_01a` |
| `prop_tv_flat_01` | `script_rt_tvscreen` | `normal_spec_emissive` | gömülü → origTxd = `prop_tv_flat_01` |
| `hei_prop_hei_keypad_01` | **YOK** (`Prop_Hei_LED_1` sadece LED şeridi) | — | gömülü doku sayısı **0** |
| `ch_prop_casino_keypad_01` | **YOK** (emissive shader hiç yok) | — | — |
| `prop_cctv_cam_01a` | **YOK** (tek shader) | — | — |

Buradan çıkan kurallar:

1. **Ekran = `emissive*` shader.** Dördünde de öyle çıktı. Ama tek başına
   yetmez: `prop_tv_flat_01`'de emissive shader **iki tane** var, ikincisi
   (`prop_base_blue_03`) ekran değil **stand-by LED'i**. Doğru seçim
   emissive shader'lar arasından adı `screen`/`scr`/`rt` içeren dokudur.
2. **`script_rt_*` adı özeldir** — o doku zaten oyunun named render target
   sistemi için ayrılmıştır (`prop_tv_flat_01` → `script_rt_tvscreen`).
   Böyle bir doku varsa hedef odur.
3. **Ekran dokusu neredeyse her zaman modele GÖMÜLÜDÜR** → `origTxd` =
   **model adı**. 4/4 böyle çıktı. Harici sözlük araması (`-Deep`) dakikalar
   sürer ve genelde gereksizdir.
4. **ytyp'deki `textureDict` alanı ekran sözlüğü DEĞİLDİR.**
   `prop_monitor_01a`: ytyp `textureDict = 3126464848 → prop_desk_monitor.ytd`,
   ama ekran dokusu modelin içinde. `assetdb.py show` çıktısındaki bu alana
   bakıp `origTxd` yazma.
5. **Keypad'lerin ekranı yoktur.** Üç ayrı keypad prop'unda da ekran dokusu
   çıkmadı; `hei_prop_hei_keypad_01`'de gömülü doku sayısı sıfır. Yani
   **keypad UI'si C yolu ile yapılamaz** — A yolu (dünya quad'ı, keypad'in ön
   yüzüne hizalı) tek seçenektir. Aynısı CCTV kamerası için de geçerli.

---

## 7. PERFORMANS — kütüphanenin ölçekleme yapısı

Kaynaktaki kadanslar (`CR3D.CONFIG`):

| Ayar | Değer | Ne yapar |
|---|---|---|
| `renderDistance` | 50.0 m | bu mesafeden uzaktaki panel çizilmez |
| `idleWait` | 100 ms | yakında panel yoksa render loop uyur |
| `activeWait` | 0 ms | çizim varsa her kare |
| `renderCheckInterval` | 500 ms | oyuncu konumu önbelleği |
| `candidateScanInterval` | 250 ms | aday listesi taraması (varsayılan **kapalı**) |
| `focusIdleWait` | 100 ms | focus kapalıyken |
| `ATTACH_MAX_WAIT` | 250 ms | bağlı panel yokken attach sürücüsü uyur |

Kendi tüketicimizi yazarken uyulacaklar:

- Panel çizimi zaten 0-tick. **İkinci bir 0-tick döngüsü açma**; ihtiyacın
  olan şey `RaycastPanel` ise onu da kıs. whiteboard demosu çizmiyorken
  raycast'i **50 ms**'e kısıp aradaki karelerde son sonucu yeniden kullanıyor.
- Panel sayısı arttıkça `RaycastPanels()` hepsini gezer. Kendi listeni mesafe
  ile önceden filtrele (demoda `nearbyBoards`, 250 ms'de bir yenilenir).
- `enableCandidateScan` ve `enableCamForwardCull` varsayılan **kapalı**
  (davranış değişmesin diye). Çok panelli sahnede ikisini de aç.
- Her DUI ayrı bir tarayıcı yüzeyi + runtime texture'dır. **Sayı ve
  çözünürlük doğrudan VRAM'dir.** Kullanılmayan paneli `DestroyPanel` et;
  `SetPanelEnabled(false)` çizimi durdurur ama DUI'yi ve dokuyu **tutmaya
  devam eder**.

---

## 8. SUNUCU OTORİTESİ — DUI tamamen istemci tarafıdır

Bu bölüm muto-* scriptleri için bağlayıcıdır.

- `CreateDui` ve tüm cr-3dnui export'ları **client-only**. Panel bir dünya
  objesi değildir; **hiç senkronize edilmez**. Başka oyuncu senin panelini
  görmez, sen açmadıkça sende de yoktur.
- Bir keypad ekranını herkesin görmesi isteniyorsa **her istemci kendi
  panelini kendisi kurar**; ortak olan şey sunucudaki *durum*tur.
  Kalıp: sunucu durumu tutar → `TriggerClientEvent` ile yayar → her istemci
  kendi DUI'sine `SendMessage` ile yansıtır.
- **Şifre/kod kontrolü asla sayfada yapılmaz.** DUI sayfası istemcidedir,
  içindeki JS okunabilir ve `SendMessage` taklit edilebilir. Sayfa yalnız
  girilen değeri Lua'ya taşır; **karşılaştırma sunucuda** yapılır ve sonucu
  sunucu söyler.
- `AddReplaceTexture` istemci genelindedir ve **kaynak durdurulduğunda geri
  alınmazsa doku bozuk kalır**. `RemoveReplaceTexture` + `DestroyDui`
  `onResourceStop`'ta çağrılmak zorunda (cr-3dnui bunu yapıyor; kendi
  sarmalayıcımız da yapmalı).

---

## 9. TUZAK KATALOĞU — tekrar yaşanmasın

1. **Panel oluştu, ekranda yok.** Sırayla bak: (a) `up` normale paralel mi
   (basis çöker), (b) sağ-el düzeni bozuk mu → arka yüz culling, (c) URL
   `files{}`'ta değil, (d) `renderDistance` dışındasın.
2. **Yazı ayna görüntüsü.** U ekseni çevrilmemiş. Kütüphane bunu yapıyor;
   kendi çizimini yazarsan atlama.
3. **İlk kare siyah.** DUI ilk boyamasını yapana kadar runtime texture boş.
   laptop demosu 200 ms sabit bekliyor — **bu tahmindir**. Doğrusu
   `IsDuiAvailable(dui)`'yi bekleyip öyle göstermek.
4. **`SendMouseWheel` yarım.** Native `SendDuiMouseWheel(dui, deltaY, deltaX)`
   iki delta alır; cr-3dnui yalnız birini geçiyor. Yatay kaydırma
   kullanacaksan ikincisini kendin ver.
5. **`SetPanelUrl` DUI'yi yeniden yaratır.** Sadece sayfa değişiyorsa
   `SetDuiUrl` yeter — CEF örneğini ve runtime texture'ı yeniden kurmak
   gereksiz maliyettir. Yeniden yaratma **yalnız çözünürlük değişince** gerekir.
6. **README ile kod çelişiyor** (focus mesajı, §5). Entegrasyonda kaynak esas
   alınır.
7. **`DrawSpritePoly` indekste yok.** Kanonik ad `DrawTexturedPoly`
   (`0x29280002282F1928`, alias `_DRAW_SPRITE_POLY`). cr-3dnui eski adı
   kullanıyor ve çalışıyor, ama **kendi kodumuzda kanonik adı yaz** — yoksa
   `/native-lint` uydurma native olarak işaretler.
8. **Panel önünde duvar varsa yine tıklanır** (§3.1). Gerekiyorsa ayrıca
   shape test at.
9. **`faceCamera=true` + `frontOnly=true` birlikte anlamsızdır** — kütüphane
   `frontOnly` varken kamera çevirmesini zaten atlar. İkisini birlikte yazmak
   "iki koruma" değil, bir tanesinin sessizce yok sayılmasıdır.
10. **Native `<select>` DUI'de çalışmaz.** Açılır liste gerekiyorsa kendi
    div'inle yaz (whiteboard demosunda örneği var).
11. **Fare tuşu asılı kalması** (§5). Her çıkış yolunda `SendMouseUp`.
12. **Oyuncu dondurulup bırakılmazsa oyun kilitlenir.** Ekran klavyesi açan
    akışta `FreezeEntityPosition(ped, false)` `onResourceStop`'ta da çağrılmalı.
13. **Panel sayısı = DUI sayısı = tarayıcı sayısı.** Aynı sayfayı 10 objede
    göstermek 10 CEF örneği demektir. Aynı içerik yeterliyse tek panel + tek
    DUI, farklı konumlarda **çizim** düşünülmeli (kütüphane bunu desteklemiyor;
    gerekirse eklenir).

---

---

## 9b. cr-3dnui v2.6'nın KENDİ KUSURLARI (kaynak okunarak bulundu)

Kullanmadan önce bilinmezse saatler kaybettirir. Üçü de aynı export'ta:
`AttachPanelToBone`.

**1. `AttachPanelToBone` bağlanmayı ilk tick'te sessizce iptal eder.**
Panel sözlüğü **string** anahtarlıdır (`PANELS[tostring(id)]`), ama bu export
attachment'ı **sayı** anahtarla yazar:

```lua
ATTACHMENTS[panelId] = { ... }        -- AttachPanelToBone  (sayı)
ATTACHMENTS[tostring(panelId)] = {…}  -- AttachPanelToEntity (string) ✅
```

Güncelleme döngüsü `PANELS[key]` bakar; sayı anahtarla panel bulunamaz ve
`ATTACHMENTS[key] = nil` ile kaydı **siler**. Sonuç: panel oluşur, görünür,
ama kemiği hiç takip etmez. Hata da vermez.

**2. Kemik bağlama zaten uygulanmamış.** `getBoneWorldPos` / `getBoneWorldRot`
yardımcıları tanımlı ama güncelleme döngüsü **hiç çağırmıyor**; döngü yalnız
`GetOffsetFromEntityInWorldCoords(a.entity, …)` kullanıyor, yani `a.boneIndex`
tamamen yok sayılıyor. 1. madde düzeltilse bile panel kemiği değil **entity
kökünü** takip eder.

**3. Sahip (owner) yanlış yazılıyor.** `AttachPanelToBone` içinde
`createPanelInternal(opts, GetCurrentResourceName())` çağrılıyor — bu
**`cr-3dnui`'nin kendisidir**, çağıran kaynak değil. Diğer export'lar
`GetInvokingResource()` kullanıyor. Sonuç: tüketici kaynak durdurulduğunda
`onResourceStop` temizliği o paneli **sahiplenmez**, panel ekranda asılı kalır.

> Sonuç: **kemiğe panel bağlamak için bu export'a güvenme.** Ya
> `AttachPanelToEntity` + pozu entity uzayına pişirme yolunu kullan (§4 —
> zaten titremeyen yol odur), ya da bu üç satırı düzeltip forkla.

## 10. GÖRSEL GEREKTİĞİNDE — üretme, öner ve prompt ver

Bir DUI sayfası, ikon, ekran arka planı, logo, doku ya da herhangi bir
görsel gerektiğinde:

**Rastgele bir şey üretme ya da yer tutucu uydurma.** Sırayla:

1. **Fikri anlat**: ne göstereceği, hangi objede duracağı, hangi mesafeden
   okunacağı, hangi ton/renk (ekranlar `emissive` shader üstünde durur —
   koyu zemin + parlak yazı gerçekçi görünür).
2. **Kullanıcıya hazır bir prompt ver** ve fotoğrafı **kullanıcının**
   üretmesini iste. Prompt'ta şunlar bulunsun: içerik, stil, en-boy oranı
   (panelin `resW:resH` oranıyla **aynı**), çözünürlük, arka plan (ekran
   dokusu için genelde tam kanama, kenar boşluğu yok).
3. Görsel gelene kadar **düzeni CSS ile kur**, görsel yerine ölçüsü doğru
   boş bir kutu bırak. Böylece görsel gelince tek dosya değişir.

Gerekçe: ekran içeriği projenin görünen yüzüdür; uydurulmuş bir görsel hem
tona oturmaz hem de sonradan tamamen değiştirilir — iki kez iş olur.

---

## 11. HIZLI REÇETE — muto-* scriptlerinde yeni bir etkileşimli ekran

1. `screentex.ps1 -Model <model>` → ekran dokusu **var mı**?
   - Varsa ve o modelden sahnede **tek** örnek varsa → C yolu (ReplaceTexture)
   - Yoksa ya da birden çok örnek varsa → A yolu (dünya quad'ı)
2. Konum/normal: `assetdb.py show <model>` (bbox → yüzün nerede olduğu) +
   `assetdb.py where <model>` (dünyadaki gerçek konumlar). Koordinat
   **uydurma**.
3. Paneli kur: `faceCamera=false`, `frontOnly=true`, `up` ver (dik hale
   getirilmiş), `resW:resH` panel oranıyla eşleşsin.
4. Etkileşim modunu seç (§5). Terminal/laptop → `key2dui`; duvar paneli → `uv`.
5. Durumu **sunucuda** tut, `SendMessage` ile yansıt (§8).
6. `onResourceStop` → `DestroyPanel` / `DestroyReplaceTexture` / `EndFocus` /
   ped dondurma iptali.
