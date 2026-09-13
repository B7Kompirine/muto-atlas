# Timecycle — oda karanlık/loş, hava cycle'ı, ıslak harita, MLO'ya güneş sızması

**Ne zaman okunur:** "neden karanlık", "iç mekân aydınlık kalıyor", "zemin ıslak gibi parlıyor", mood için modifier, `TIMECYCLEMOD_FILE`.
**When to read:** the room is dark or washed out, a weather cycle, a wet map, applying a timecycle modifier to an MLO.
**Kaynak:** `isik.md` 'Timecycle katmanı', 'ıslak', 'MLO odası' · `decal.md` §5 · morg_vanilla notları (2026-08) · **Ölçüm:** 1.087 modifier + 17 hava cycle'ı (`timecycle.tsv.gz`); v_coroner oda bayrakları; casino vault / facility 111
**Önce:** `_dal.md` · gövde › `govde/arac-tuzaklari.md` §1-2

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" cycle w_clear --hour 20   # 1. taban hava cycle'ı
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" timecycle <modifier>     # 2. odanın modifier'ı
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya>           # 3. prop'un ışığı
```

Karanlık şikâyeti **üç katmanlıdır** ve sırayla bakılır: taban hava cycle'ı → odanın modifier'ı → prop'un ışığı. Cevap çoğu zaman üçüncüde değildir.

## Timecycle katmanı

Bir sahnenin görünümü üç katmandır ve sırası şudur:
**taban hava cycle'ı → odanın modifier'ı → prop'un kendi ışığı.**
"Işığı doğru kurdum ama hâlâ yanlış" diyorsan ilk ikisine bak.

Ölçülmüş, tahmin edilmemesi gerekenler:

- Bir cycle dosyası `cycle > region > <değişken>metin</değişken>` yapısındadır
  ve metin **keyframe başına** bir değer taşır. **13 keyframe vardır, 24 saat
  değil.** "saat = indeks" varsayımı her şeyi kaydırır.
- Saat çizelgesi ayrı dosyadadır ve **iki tane `time.xml` vardır**. Doğrusu
  `common.rpf\data\levels\gta5\time.xml` (13 sample);
  `common.rpf\data\time.xml` 4 sample'lik bambaşka bir dosyadır.
  Saatler: `0 5 6 7 10 12 16 17 18 19 20 21 22`
- ⛔ Bir sample `name="09:00"` yazar ama `hour="10"` taşır. **Ad yalan söyler,
  `hour` niteliği esastır.** Ada bakan sonraki tüm keyframe'leri bir saat kaydırır.
- Renkler zaten 0–1'dir (ölçülen maks 1.002), hiçbir yerde /255 yoktur
- `light_dir_mult` HDR'dir, **54'e** kadar çıkar — kırpma opsiyonel değildir
- Bölge katmanı vardır: `GLOBAL` ve `URBAN`
- Modifier bir **değiştirme değil harmandır**: `taban + (mod − taban) × güç`,
  ve param bazındadır (bir modifier natural'ı sıfırlarken artificial'a
  dokunmayabilir). Modifier tablosunda param başına iki değer bulunur;
  geçerli olan **birincisidir**.

> **Kırpma tavanları kalibrasyondur, motor sabiti değil.** `cycle.py` içindeki
> `TAVAN_ORTAM` / `TAVAN_GUNES` parametredir; vanilla görüntüyle
> karşılaştırarak doğrula, gömülü sabit gibi davranma.

---

## 5. TIMECYCLE

Karanlık **üç katmanlıdır**, sırayla bakılır:
**hava cycle'ı → odanın modifier'ı → prop ışıkları.** Cevap çoğu zaman
üçüncüde değildir.

### Paylaşılan modifier'a DOKUNMA
`morgue_dark` **6 DLC dosyasında** tanımlı ve tüm morg onu paylaşıyor.
Hangisinin kazandığı DLC yükleme sırasına bağlı ve **veriden okunamaz.**
→ Kendi modifier'ını yaz, odanın `timecycleName`'ini ytyp'de değiştir.

### Şema (vanilla'dan kopyalandı, uydurulmadı)
```xml
<timecycle_modifier_data version="1.000000">
  <modifier name="muto_bds_dark" numMods="44" userFlags="0">
    <natural_ambient_multiplier>0.045 0.000</natural_ambient_multiplier>
    ...
  </modifier>
</timecycle_modifier_data>
```
Eleman metni `"deger1 deger2"`. `numMods` gerçek eleman sayısıyla tutmalı.

### FiveM kaydı ŞART
```lua
files { 'data/timecycle_mods_muto.xml' }
data_file 'TIMECYCLEMOD_FILE' 'data/timecycle_mods_muto.xml'
```
Kaydedilmezse oyun modifier'ı **aramaz**, oda vanilla'da kalır.

### Mood için en etkili dört parametre (ölçülen etki)
| Parametre | vanilla morgue_dark | koyu |
|---|---|---|
| `natural_ambient_multiplier` | 0.154 | 0.045 |
| `artificial_int_ambient_multiplier` | 0.632 | 0.300 |
| `ssao_inten` | 6.300 | 9.500 |
| `postfx_vignetting_intensity` | 0.000 | **0.550** ← en görünür fark |

`fog_start` **düşürme** (73 → 4 denendi, beğenilmedi — iç mekânda sis
istenmiyorsa vanilla 73'te bırak).

---

### ⛔ "Harita ıslak" ŞİKÂYETİNİN İKİ AYRI YOLU VAR — biri diğerini kapatmaz

Yukarıdaki vertex `R = 0` kuralı **doğal ambient sızmasını** kapatır. Yüzey
ıslaklığı **ayrı bir global yoldur** ve R onu kapatmaz. İkisini birbirinin
yerine koymak bir turu yakar: R'yi 228/228 modelde 0 yaptıktan sonra harita
hâlâ ıslanıyordu, çünkü sebep hiç orada değildi.

**Belirti zamana bağlıysa varlık tarafına bakma.** "İçeride 15 dakika
çalışınca gene ıslak" — dosya değişmediğine göre kaynak çalışma anındadır.

### `SetRainLevel` ıslaklığı KALDIRMAZ

`_SET_RAIN_LEVEL` (lua: `_SetRainLevel`, alias `SetRainLevel`,
`0x643E26EA6E024D92`) yağmurun **yoğunluğudur**. Yüzey ıslaklığını **hava
tipinin kendisi** sürer. Tip `RAIN` kaldığı sürece yağmur seviyesini
sıfırlamak hiçbir şey değiştirmez.

⚠️ Bir tur "bu native yok" diye yanlış teşhis kondu. İndekste lua adı
`_SetRainLevel`, lua-defs'te `SetRainLevel` — **ikisi de FiveM'de vardır**.
`GET_RAIN_LEVEL` ise `GetRainLevel`.

### qb-weathersync ile YARIŞ KAZANILMAZ — döngüsü durdurulur

Ölçüldü (`qb-weathersync/client.lua`): ana döngü **`Wait(100)`** ile koşar ve
**her turda** şunları yeniden yazar:

```
ClearOverrideWeather / ClearWeatherTypePersist
SetWeatherTypePersist(lastWeather) / SetWeatherTypeNow / SetWeatherTypeNowPersist
RAIN -> SetRainLevel(0.3)   THUNDER -> SetRainLevel(0.5)
```

500 ms'lik bir bastırma döngüsü buna **5'e 1 kaybeder**. Her karede yazmak da
çözüm değil: qb'nin yazdığı karede tip yine `RAIN` olur.

**Doğrusu qb'yi durdurmaktır:**

```lua
TriggerEvent('qb-weathersync:client:DisableSync')   -- disable = true
-- cikarken:
TriggerEvent('qb-weathersync:client:EnableSync')    -- sunucudan durum ister
```

`RegisterNetEvent` ile kayıtlı olduğu için `TriggerEvent` yerelde çalışır.

⛔ **`DisableSync` SAATİ 18:00'E SABİTLER** (`client.lua:25`,
`NetworkOverrideClockTime(18,0,0)`). Tutturulmuş karanlık iç mekân tonu
saatten beslendiği için bu tonu kaydırır. **Girmeden önce saati oku, sonra
geri koy:**

```lua
local h,m,sn = GetClockHours(), GetClockMinutes(), GetClockSeconds()
TriggerEvent('qb-weathersync:client:DisableSync')
NetworkOverrideClockTime(h, m, sn)
```

⛔ **Kaynak durursa oyuncu "hava senkronu kapalı" kalır** — `onResourceStop`
içinde `EnableSync` çağır.

Mekanizma: `Config.DynamicWeather = true` → hava 10 dakikada bir değişir →
döngü düzenli olarak `RAIN`/`THUNDER`'a girer. "15 dakikada bir geri geliyor"
şikâyetinin süresi tam olarak budur. Uygulama: `muto-morg/kuru_morg.lua`.


## MLO odasına dışarıdan ışık girmesi = ODA BAYRAĞI, geometri değil

⛔ **Karanlık bir iç mekâna güneş sızıyorsa ilk bakılacak yer kabuk/küp
değil, odanın kendi `flags` alanıdır.** Directional light (güneş/ay) GTA'da
geometriyle engellenmez; **oda bayrağıyla** kapatılır. Kabuk koymak yalnızca
*gölge* yaratır, gölge haritasının çözünürlüğü de kenarda yetmez → kenar
boyunca dizilmiş parlak noktalar (shadow acne) çıkar. Belirti "yırtılma"
gibi görünür ve kişiyi geometriyi düzeltmeye iter; sebep orada değildir.

**Oda bayrağı bitleri — Sollumz `RoomFlags` enum'u (tahmin DEĞİL):**

| bit | değer | ad | bit | değer | ad |
|---:|---:|---|---:|---:|---|
| 0 | 1 | Freeze Vehicles | 5 | 32 | Reduce Cars |
| 1 | 2 | Freeze Peds | 6 | 64 | Reduce Peds |
| **2** | **4** | **No Directional Light** | 7 | 128 | Force Directional Light On |
| **3** | **8** | **No Exterior Lights** | 8 | 256 | Dont Render Exterior |
| 4 | 16 | Force Freeze | 9 | 512 | Mirror Potentially Visible |

Kaynak: `sollumz/ytyp/properties/flags.py` → `class RoomFlags`.
Portal tablosu aynı dosyada `class PortalFlags` (1 One Way · 2 Link Interiors
Together · 4 Mirror · 8 Disable Timecycle Modifier · 16 Mirror Using
Expensive Shaders · 32 Low LOD Only · …).

⛔ **`assetdb.py flags <n>` bu iş için YANLIŞ CEVAP VERİR** — o araç yalnız
**archetype/entity** tablosunu bilir, oda/portal tablosu ayrıdır ve `--room`
seçeneği yoktur. 111'i "Wet Road Reflection | Dont Fade | Draw Last |
Climbable By AI | Static | Disable alpha sorting" diye çözer; hepsi
alâkasızdır. Bu §2'nin bir başka yüzü: **araç sessizce başka bir tablodan
cevap verebilir.** Bir alanın anlamını sormadan önce aracın o alanı
hangi tabloyla eşlediğine bak.

**Ölçülmüş vanilla ölçütü** (bu turda dört MLO açıldı):

| MLO | oda | bayrak |
|---|---|---|
| `ch_dlc_int_09_ch` (casino vault, zifiri) | 5 | **5/5 → 111** |
| `xm_x17dlc_int_facility` (tamamen gömülü) | 18 | **18/18 → 111** |
| `dt1_02_carpark` (yeraltı otoparkı) | 2 | 108 · 104 |
| `v_int_2` (v_coroner, **vanilla**) | 14 | 111 ağırlıklı, **ama** `MainStairs` 99 · `CorridorTop` 107 · `topoff_*` 99/99/**0** |

**111 = Freeze×2 + Reduce×2 + No Directional Light + No Exterior Lights.**
Karanlık iç mekânın imzası budur. Dikkat: hiçbiri **256 `Dont Render
Exterior` KURMAZ** — o bit karanlık için gerekli değil, kurma.

**Rockstar'ın kendi mantığı:** yeraltı odaları 111, yer üstü odaları 99/107/0.
Yani vanilla `v_coroner`'da merdiven boşluğuna (`MainStairs`, z uzanımı
**18.6 m**) güneş **kasıtlı** giriyor. Apokaliptik/karanlık bir sürüm
yapıyorsan bunlar tek tek 111'e çekilir; kusur senin değişikliğinde değil
**vanilla'nın kendisindedir**, bu yüzden "vanilla ile diff al" denetimi bunu
ASLA yakalamaz. Ölçüt vanilla'nın aynı dosyası değil, **aynı işi yapan başka
bir vanilla MLO** olmalı.

Ped/araç popülasyon bitlerine karışma: yalnız `flags |= 4|8` uygula.
`limbo` odasına dokunma (vanilla'da her zaman 96).

**Yazma hattı:** `ytyp_to_xml.ps1` → XML'de `flags` yaması →
`meta_xml_to_bin.ps1` (`.ytyp`/`.ymap` için; `xml_to_res.ps1` bu ikisini
TANIMAZ) → geri oku. Tur kayıpsızlığı **düğüm bazında** doğrulanır:
ölçüldü, 14.257 düğümde kaybolan 0 / eklenen 0 / değişen tam 5.

---
