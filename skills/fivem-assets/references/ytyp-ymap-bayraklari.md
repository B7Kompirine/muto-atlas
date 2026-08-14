# ytyp / ymap yer gerçeği — bayraklar, enum'lar, extension'lar

Bu dosyadaki her tablo **Sollumz 2.9.0 kaynağından** (`szio 1.3.0.dev9`) birebir
çıkarıldı ve mümkün olan yerde **316.975 vanilla arketip** üzerinde çapraz
doğrulandı. Tahmin yok; doğrulanmamış kalan tek tük madde `[DOĞRULANMADI]`
etiketli.

Kaynak yolu (kurulu olduğu makinede):
`%APPDATA%\Blender Foundation\Blender\<sürüm>\extensions\user_default\sollumz\`

---

## 1. ⛔ Bayrak numaralandırması: `flagN` bit `N-1`'dir

Sollumz özellikleri `flag1 … flag32` diye adlandırır ama **`flag1` en düşük
bittir**, yani değeri `1`. Formül:

```
deger(flagN) = 2^(N-1)
```

Doğrudan `1 << N` yazmak tüm tabloyu **bir bit kaydırır** ve sessizce yanlış
isim üretir. Denetim: `flag16 = LOD Use Alt Fade → 2^15 = 32768`, CodeWalker'ın
onay listesindeki değerle birebir aynı.

---

## 2. ARCHETYPE bayrakları (`CBaseArchetypeDef.flags`)

| Değer | Bit | Ad |
|---:|---:|---|
| 1 | 0 | *(adsız)* |
| 2 | 1 | Wet Road Reflection |
| 4 | 2 | Dont Fade |
| 8 | 3 | Draw Last |
| 16 | 4 | Climbable By AI |
| 32 | 5 | Suppress HD TXDs |
| 64 | 6 | Static |
| 128 | 7 | Disable alpha sorting |
| 256 | 8 | Tough For Bullets |
| **512** | 9 | **Has Anim (YCD)** |
| **1024** | 10 | **UV anims (YCD)** |
| 2048 | 11 | Shadow Only |
| 4096 | 12 | Damage Model |
| 8192 | 13 | Dont Cast Shadows |
| 16384 | 14 | Cast Texture Shadows |
| 32768 | 15 | Dont Collide With Flyer |
| 65536 | 16 | Double-sided rendering |
| **131072** | 17 | **Dynamic** |
| 262144 | 18 | Override Physics Bounds |
| **524288** | 19 | **Auto Start Anim** |
| 1048576 | 20 | Has Pre Reflected Water Proxy |
| 2097152 | 21 | Has Drawable Proxy For Water Reflections |
| 4194304 | 22 | Does Not Provide AI Cover |
| 8388608 | 23 | Does Not Provide Player Cover |
| 16777216 | 24 | Is Ladder Deprecated |
| 33554432 | 25 | Has Cloth |
| **67108864** | 26 | **Enable Door Physics** |
| 134217728 | 27 | Is Fixed For Navigation |
| 268435456 | 28 | Dont Avoid By Peds |
| 536870912 | 29 | Use Ambient Scale |
| 1073741824 | 30 | Is Debug |
| 2147483648 | 31 | Has Alpha Shadow |

### Çapraz doğrulama (316.975 arketip)

`clipDictionary` alanı dolu olan **1308** arketip:

| Alt küme | Adet |
|---|---:|
| `Has Anim (YCD)` biti kurulu | 470 |
| yalnız `UV anims (YCD)` biti kurulu | 838 |
| **hiçbir anim biti kurulu olmayan** | **0** |

Ve `Has Anim` biti kurulu olup `clipDictionary`'si boş olan **0** arketip var.
Yani eşleme tam örtüşüyor — bit tablosu doğru.

Örnek çözüm — vanilla `prop_pallet_01a`, `flags="549584896"`:
```
549584896 = Dynamic | Does Not Provide AI Cover
          | Does Not Provide Player Cover | Use Ambient Scale
```
(Kırılabilir bir palet için: dinamik, siper vermez, ambient ölçekli. Tutarlı.)

### Videolarda kullanılan bayrak setleri

- Animasyonlu prop → `Dynamic` + `Has Anim (YCD)` + `Auto Start Anim`
- UV/spritesheet animasyonu → `UV anims (YCD)`
- Kapı → `Dynamic` + `Enable Door Physics`

---

## 3. ENTITY bayrakları (`CEntityDef.flags`, ymap)

> ⚠ Bu tablo `assetdb.py::ENTITY_FLAGS`'ten **üretildi**, elle yazılmadı.
> Önceki sürümünde 128'den sonrası bir satır kaymıştı (elle kopyalama hatası);
> kod hep doğruydu, hatalı olan belgeydi. Değiştirirsen koddan yeniden üret.

| Değer | Bit | Ad |
|---:|---:|---|
| 1 | 0 | Allow full rotation |
| 2 | 1 | Stream Low Priority |
| 4 | 2 | Disable embedded collisions |
| **8** | 3 | **LOD in Parented YMAP** |
| **16** | 4 | **LOD Adopt Me** |
| 32 | 5 | Static entity |
| 64 | 6 | Interior LOD |
| 128 … 16384 | 7-14 | Unknown 8 … Unknown 15 |
| 32768 | 15 | LOD Use Alt Fade |
| **65536** | 16 | **Underwater** |
| 131072 | 17 | Does Not Touch Water |
| 262144 | 18 | Does Not Spawn Peds |
| **524288** | 19 | **Cast Static Shadows** |
| **1048576** | 20 | **Cast Dynamic Shadows** |
| 2097152 | 21 | Ignore Day Night Settings |
| 4194304 | 22 | Disable shadow for entity |
| 8388608 | 23 | Disable entity, shadow casted |
| **16777216** | 24 | **Dont Render In Reflections** |
| 33554432 | 25 | Only Render In Reflections |
| 67108864 | 26 | Dont Render In Water Reflections |
| 134217728 | 27 | Only Render In Water Reflections |
| 268435456 | 28 | Dont Render In Mirror Reflections |
| 536870912 | 29 | Only Render In Mirror Reflections |
| 1073741824 | 30 | Unknown 31 |
| 2147483648 | 31 | Unknown 32 |

### `65536` = Underwater — ölçüldü

Sollumz kaynağı bu biti **"Unused"** diye adlandırıyor, CodeWalker
**"Underwater"** diyor. 3.145.882 entity tarandı: bit **yalnız 14 kez** kurulu
ve hepsi su prop'u — `prop_dock_bouy_1/2/3` (iskele şamandırası) ve
`prop_rub_wheel_01`, liman/nehir ymap'lerinde (`po1_09_long_0`,
`vb_rv_strm_1`). **CodeWalker haklı.**

### ⭐ Elimizdeki sihirli sayılar artık çözülüyor

```
1572872  = LOD in Parented YMAP | Cast Static Shadows | Cast Dynamic Shadows
1572865  = Allow full rotation  | Cast Static Shadows | Cast Dynamic Shadows
18350080 = Dont Render In Reflections | Cast Static Shadows | Cast Dynamic Shadows
```

- **`1572872` LOD zincirindeki HD entity'nin değeridir.** 8. bit motora
  "benim LOD'um ÜST haritada" der. Üst harita yoksa entity **sessizce düşer**.
  CLAUDE.md §4'teki "ymap değeri verilirse obje oluşmaz" uyarısının sebebi budur
  — değer bozuk değil, **bir zincirin ortasına ait**.
- **`1572865` ile arasındaki tek fark 1. bittir**: `LOD in Parented YMAP` yerine
  `Allow full rotation`. Bayrak/flama prop'u bunu kullanır (rüzgârda dönebilsin).
- **`18350080` MLO entity'sidir**: iç mekân objesi yansımalarda çizilmez.

---

## 4. `specialAttribute` — 21 değerin tamamı

Sollumz enum adı = **motorun semantiği**; "vanilla kullanımı" sütunu = bizim
316k arketip üzerinden ölçtüğümüz **gerçek kullanım**. İkisi farklı katman ve
ikisi de gerekli.

| Değer | Sollumz adı | Vanilla adet | Gerçek kullanım / örnek |
|---:|---|---:|---|
| 0 | None | 314.116 | kapı değil |
| 1 | Deprecated - Unused | 41 | *"Does nothing"* — `sm_boat_clutter2` |
| 2 | Deprecated - Ladder | 233 | ~~vinç~~ → merdiven; `prop_towercrane_02a..e` |
| 3 | Traffic Light | 80 | trafik lambası |
| 4 | Unknown 4 | 17 | Sollumz de bilmiyor; `*_hedgedtl_*` (çit detayı) |
| 5 | Garage Door | 81 | garaj/rulo kapı |
| 6 | MLO Water Level | 630 | ⚠ örnekler `ch1_roadsb_slod*` — çelişki, §4.1 |
| 7 | Normal Door | 661 | menteşeli kapı |
| 8 | Sliding Door | 74 | sürgülü kapı |
| **9** | **Barrier Door** | **1** | `m26_1_prop_m61_sewer_gate` |
| 10 | Sliding Vertical Door | 8 | kepenk / asansör kapısı |
| 11 | Bush *(içeride `NOISY_BUSH`)* | 39 | çalı |
| 12 | Rail Crossing Barrier Door | 2 | `prop_railway_barrier_01/02` |
| 13 | Deformable Bush | 226 | ezilebilen çalı |
| 14 | Single Axis Rotation | 2 | *"procedural animation"*; `prop_roofvent_06a/14a` |
| 15 | Dynamic Cover Bound | 81 | siper verir; `v_ret_fh_dinetable`, `prop_aircon_m_10` |
| 16 | Rumble On Vehicle Collision | 207 | `prop_barrier_work01a..d`, `prop_pallet_01a` |
| 17 | Rail Crossing Light | 2 | ⚠ örnekler `prop_traffic_rail_*` — çelişki, §4.1 |
| 30 | Clock | 11 | *"animated clock hands"*; `prop_big_clock_01` |
| 31 | Deprecated - Tree | 463 | *"double-sided rendering ile aynı"* |
| **32** | **Street Light** | **0** | vanilla'da hiç kullanılmıyor |

### 4.1 İki ad çelişkisi — biri çözüldü, biri daraldı

**17 → Sollumz haklı, ben yanılmışım.** İki örnek `prop_traffic_rail_1a` ve
`prop_traffic_rail_2`, ikisi de **`v_traffic_lights.ytyp`** içinde — yani
trafik *lambası* ytyp'i. Adındaki "rail" yol korkuluğu değil, demiryolu geçidi.
Eski etiketimiz ("trafik korkuluğu") **yanlıştı**, düzeltildi.

**6 → çelişki duruyor ama şekli değişti.** Önce "630 örneğin hepsi `*_slod*`"
demiştim; bu **6 satırlık bir örneklemden** çıkarılmış yanlış bir genellemeydi.
Tam ölçüm:

- 630 arketipin **yalnız 99'unda (%15,7)** adında `slod` geçiyor
- Kalanı sıradan kırsal harita parçası: `cs1_15b_barn`, `cs1_15b_bridge_det1`,
  `cs1_15b_chimneydet1` …
- Ad önekleri: `cs1_` (474) · `ch1_` (37) · `cs2_` (21) · `cs6_` (18)
- 20 farklı ytyp'e dağılmış, en yoğunu `country_01_metadata_010_strm.ytyp` (363)
- `lodDist` medyanı **80** — SLOD'a ait olmayacak kadar küçük

Yani ne "hepsi SLOD" doğru, ne de "MLO Water Level" adı kullanımla örtüşüyor.
**Ölçmeden yeniden adlandırma; ikisini de bil.**

⚠ Ders: 6 satırlık örnekten genelleme yapmıştım ve yanlış çıktı. Bu tablodaki
her iddia tam sayımdan gelmeli.

### 4.2 Kapı sistemi hangi tipleri gerçekten oynatır

**Ölçüm:** `Enable Door Physics` biti (67108864) kurulu **1176** arketipin
`specialAttribute` dağılımı:

| specialAttribute | Adet |
|---:|---:|
| 7 Normal Door | 646 |
| **0 None** | **379** |
| 5 Garage Door | 77 |
| 8 Sliding Door | 71 |
| 10 Sliding Vertical | 7 |
| 12 Rail Crossing Barrier | 2 |
| 4 Unknown 4 | 1 |
| **9 Barrier Door** | **0** |
| **14 Single Axis Rotation** | **0** |

→ `DOOR_CAPABLE = {5, 7, 8, 10, 12}` **doğrudur**. `9` ve `14` enum'da var ama
vanilla onlara door physics vermiyor: `14` bir **prosedürel dönüş**tür (çatı
fanı), kapı değil. Bir eğitim videosunda `14` ile kapı yapılıp "açıldı"
görülmesi door sistemini değil bu prosedürel dönüşü gösterir.
→ Ayrıca **379 arketip `specialAttribute=0` olduğu hâlde door physics taşıyor**:
kapı olup olmadığını yalnız `specialAttribute`'a bakarak söylemek eksiktir,
bayrağa da bakılmalı.

---

## 5. ytyp EXTENSION tipleri (14)

`ytyp/properties/extensions.py:29`. **Sollumz arayüzü bunlardan yalnız 11'ini
gösterir**; `DOOR`, `SPAWN_POINT_OVERRIDE`, `LIGHT_EFFECT` listede yoktur ama
içe aktarma yolunda desteklenir.

| Sollumz sabiti | XML sınıfı | Arayüzde |
|---|---|:--:|
| `DOOR` | `CExtensionDefDoor` | — |
| `PARTICLE` | `CExtensionDefParticleEffect` | ✓ |
| `AUDIO_COLLISION` | `CExtensionDefAudioCollisionSettings` | ✓ |
| `AUDIO_EMITTER` | `CExtensionDefAudioEmitter` | ✓ |
| `EXPLOSION_EFFECT` | `CExtensionDefExplosionEffect` | ✓ |
| `LADDER` | `CExtensionDefLadder` | ✓ |
| `BUOYANCY` | `CExtensionDefBuoyancy` | ✓ |
| `LIGHT_SHAFT` | `CExtensionDefLightShaft` | ✓ |
| `SPAWN_POINT` | `CExtensionDefSpawnPoint` | ✓ |
| `SPAWN_POINT_OVERRIDE` | `CExtensionDefSpawnPointOverride` | — |
| `WIND_DISTURBANCE` | `CExtensionDefWindDisturbance` | ✓ |
| `PROC_OBJECT` | `CExtensionDefProcObject` | ✓ |
| **`EXPRESSION`** | **`CExtensionDefExpression`** | ✓ |
| `LIGHT_EFFECT` | `CExtensionDefLightEffect` | — |

⚠ **`EXPRESSION` bizim `.yed` zincirimizin ytyp ayağıdır** (CLAUDE.md §1).
Orada "ytyp'e Expression extension ekle, **çıplak ad** yaz" diyoruz — bunun
Sollumz'da hazır bir arayüzü var, XML'i elle yazmak gerekmiyor.
`PROC_OBJECT` ise @ma prosedürel çim sisteminin ytyp ayağı.

---

## 6. Partikül extension'ı (`CExtensionDefParticleEffect`)

```xml
<Item type="CExtensionDefParticleEffect">
  <name>prop_pallet_01a</name>
  <offsetPosition x="0" y="0" z="0" />
  <offsetRotation x="0" y="0" z="0" w="1" />
  <fxName>dst_wood_structures</fxName>
  <fxType value="4" />          <!-- Destroy -->
  <boneTag value="-1" />        <!-- -1 = TÜM kemikler -->
  <scale value="1.4" />
  <probability value="100" />
  <flags value="0" />
  <color value="0xFFFFFFFF" />
</Item>
```

### `fxType` enum'u

| Değer | Ad | Not |
|---:|---|---|
| 0 | Ambient | sürekli/ortam; `amb_*` aileleri |
| 1 | Collision | çarpma anında |
| 2 | Shot | vurulunca |
| 3 | Break | kırılınca |
| 4 | Destroy | yok olunca (`dst_*`) |
| 5 | Animation (Unused) | kullanılmıyor |
| 6 | RayFire | *"Valid FX names are defined in the `ENTITYFX_RAYFIRE_PTFX` block"* |
| 7 | In Water | su altında |

### Bayraklar
`Ignore Damaged Model` · `Play on Parent` · `Only on Damaged Model` ·
`Allow Rubber Bullet Shot`

### ⛔ ytyp'teki `fxName` ile `.ypt`'deki efekt adı AYNI DEĞİL

**Ölçüldü** (406 benzersiz `fxName` × 2.549 efekt kataloğu):

| Durum | Adet | Oran |
|---|---:|---:|
| katalogda **aynen** var | 3 | %0,7 |
| **`ent_` öneki** eklenince var | 265 | %65,3 |
| `ent_` öneki **+ sonek** ile var | 9 | %2,2 |
| **hiçbir akrabası yok** | 129 | %31,8 |

Yani ytyp'e `amb_steam_vent_round` yazarsın, `.ypt` içindeki gerçek ad
**`ent_amb_steam_vent_round`**'dur. Bazen sonek de eklenir:
`amb_butterflys` → **`ent_amb_butterflys_swarm`** ·
`amb_moths` → `ent_amb_moths_swarm` / `ent_amb_moths_cupboard` ·
`ray_shipwreck_splash` → `..._s` / `..._l`.

**Toplam çözülebilirlik: %68,2.**

### ⚠ Kalan %31,8 vanilla'nın kendi boşta referansları

**İndeks eksik değil — kanıtlandı:** `core.ypt` CodeWalker ile XML'e açıldı
(45,5 MB) ve `EffectRuleDictionary`'deki **895 efektin 895'i** indekste çıktı,
kaçan **0**. Yani bu adlar oyunun dosyalarında gerçekten yok.

En çarpıcıları: `amb_water_roof_drips_short` **5.621 kullanım** ·
`amb_wind_dust_swirl` 783 · `amb_wind_sand_dune` 547 · `amb_wind_dust` 475 ·
`amb_water_roof_pour_short` 374 · `dst_shop_plastic_cont` 256.

`amb_water_roof_drips` ve `..._thin` var ama `_short` yok — yani bunlar
sürüm geçişlerinde silinmiş/yeniden adlandırılmış efektlere kalan ölü
referanslar. **Bir vanilla ytyp'i kopyalayıp efektini devraldıysan, o efekt
zaten çalışmıyor olabilir.**

Pratik sonuç: bir vanilla prop'un ytyp'ini kopyalayıp efektini devraldıysan,
o efekt zaten çalışmıyor olabilir. **Kopyalamadan önce doğrula:**

```bash
assetdb.py fx <fxName> --exact
```

### Efekt kataloğu

`data/ptfx_effects.tsv.gz` — **2.549 benzersiz efekt**, 368 `.ypt` içinde
(1.240 dosya tarandı, 0 hata). `core.ypt` tek başına 895 efekt taşıyor.
Üretici: `build_ptfx.ps1`.

### Ölçülmüş tuzaklar
- **Yazım hatası sessizdir.** Yanlış `fxName` hiçbir hata üretmez, efekt
  görünmez. Extension kopyalanınca hata da kopyalanır.
- `boneTag = -1` → tüm kemikler (parça hangi sırayla kopar farketmez).
- `probability` gerçekten olasılıktır (%20 → 5 objeden ~1'i).
- **Rotasyon önemli**: ters kurulan kıvılcım yukarı saçar.
- `veh_` `ped_` `proj_` `wheel_` önekli efektler ytype'tan çalışmaz, script ister.
- Bazıları koşulludur: `_nighttime` yalnız gece, deniz efektleri su altında.

---

## 7. Export formatı — `NATIVE` gerçekten binary yazar mı?

**Evet, ama koşullu — ve `.ycd` bu sistemin tamamen dışındadır.**

```python
# szio/gta5/native/__init__.py:7
IS_BACKEND_AVAILABLE = importlib.util.find_spec("pymateria") is not None
```

```python
# sollumz_preferences.py:377-378
if not self.target_formats or (not is_provider_available(AssetFormat.NATIVE)
                               and "CWXML" not in self.target_formats):
    self.target_formats = {"CWXML"}       # ← SESSİZ geri düşüş
```

- `pymateria` paketi kurulu değilse `NATIVE` sağlayıcısı **hiç kaydolmaz** ve
  ayar **sessizce `CWXML`'e düşer**. Hata yok, uyarı yok.
- Bu makinede `pymateria 0.2.0` kurulu → `NATIVE` çalışır durumda.

### ✅ Canlı testle doğrulandı (Blender 5.2 + Sollumz 2.8)

Gerçek export yapıldı, çıkan dosyaların **ilk 4 baytı okundu**:

| Ayar | Çıktı | Boyut | İlk 4 bayt |
|---|---|---:|---|
| `NATIVE` + `GEN8` | `x.ydr` | 451 | `52534337` = **`RSC7`** (binary) |
| `CWXML` + `GEN8` | `x.ydr.xml` | 2.699 | `3c3f786d` = `<?xm` |
| `NATIVE` + `GEN8`+`GEN9` | `gen8/x.ydr` **ve** `gen9/x.ydr` | 451 / **558** | ikisi de `RSC7` |
| `NATIVE`+`CWXML`, tek sürüm | `x.ydr` **ve** `x.ydr.xml` | — | aynı klasöre ikisi |

`is_provider_available` dördü de `True`: `NATIVE/GEN8`, `NATIVE/GEN9`,
`CWXML/GEN8`, `CWXML/GEN9`.

**Gen8 ile Gen9 çıktısı farklı boyutta** (451 vs 558) — Gen9 kozmetik bir
etiket değil, gerçekten başka bir dosya. Tek sürüm seçiliyse alt klasör
oluşmaz, dosya doğrudan hedefe yazılır.

### Her iki sağlayıcının desteklediği uzantılar **aynı 8 tanedir**

`.ybn .ydr .ydd .yft .yld .ytyp .ymap .ytd`

### ⛔ `.ycd` bu listede YOK

`.ycd` export'u sağlayıcı sistemine hiç uğramaz:

```python
# ycd/ycdexport.py:574
clip_dict.write_xml(filepath)          # sabit kodlanmış XML
```

→ **Bizim eski notumuz doğruydu ama sebebi yanlış yerdeydi.** "Sollumz NATIVE
istense de XML yazar" *genel* bir kusur değil; **`.ycd` format sisteminin
dışında olduğu için** `target_formats` ona hiç ulaşmaz. Diğer 8 uzantı için
`NATIVE` gerçekten binary üretir (pymateria varsa).
→ Dolayısıyla `xml_to_ycd.ps1` hâlâ **zorunlu**, ama `xml_to_res.ps1`'i
`.ydr/.yft/.ybn` için atlayabiliriz.

### Gen8 / Gen9

```python
# iecontext.py:99-100
gen8_directory = directory / "gen8"
gen9_directory = directory / "gen9"
```

- `("GEN9", "Gen9", "GTAV Enhanced", 2)` — Gen9 = **GTA V Enhanced**.
- İki sürüm birden seçilirse çıktı **`gen8/` ve `gen9/` alt klasörlerine**
  ayrılır. Tek sürüm seçiliyse dosyalar doğrudan hedef klasöre yazılır.
- ⚠ Hattımız tek çıktı yolu varsayıyor: `extract_asset.ps1` / `xml_to_res.ps1`
  çağıran her betik, iki sürüm açıkken dosyayı **beklediği yerde bulamaz**.
- Gen9'un ayrı shader varsayılanları var (`ShadersG9ParamsDefaults.json`,
  `ShadersG9TextureNameMapping.json`) ve ayrı adaptörleri
  (`drawable_gen9.py`, `fragment_gen9.py`, `texture_gen9.py`).

---

## 7c. SIFIRDAN PARTİKÜL EFEKTİ ÜRETME (`.ypt`)

Kaynak: JulioNIB, *"Creating and editing a new particle effect based on an
existing one"* (35 dk). Yapı iddiaları CodeWalker tipleriyle **doğrulandı**.

### `.ypt` yapısı — beş sözlük

`ParticleEffectsList` (kök) şunları taşır, ve **özel efekt üretirken beşi de
yeni dosyaya taşınır**:

| Sözlük | İçerik |
|---|---|
| `EffectRuleDictionary` | efektin kendisi; her biri **event emitter** listesi |
| `EmitterRuleDictionary` | emitter kuralları — **spawn rate** keyframe'leri |
| `ParticleRuleDictionary` | particle kuralları — **renk/boyut/hız** keyframe'leri |
| `DrawableDictionary` | efektin kullandığı modeller (çoğu efekt kullanmaz) |
| `TextureDictionary` | efektin kullandığı dokular |

Bir efekt birden çok **event emitter** taşıyabilir (ölçüldü: `bang_carmetal`
6 tane). **Her event emitter için** hem emitter rule hem particle rule ayrı
ayrı kopyalanmalı.

### Hat

1. Efektin bulunduğu `.ypt`'yi bul → `assetdb.py fx <ad> --exact` söyler.
2. CodeWalker ile **XML'e export** et.
3. **Yeni bir dosya aç** — vanilla `.ypt`'yi düzenleme; başka modları bozar.
   Uzantı `.<ad>.ypt.xml` biçiminde olmalı (XML'den önce asset uzantısı).
4. Beş sözlüğün **açılış/kapanış etiketlerini** yeni dosyaya kopyala.
5. Efekt tanımını, sonra **her event emitter'ın** emitter+particle rule'unu bul
   ve ilgili sözlüğe yapıştır.
6. Kullanılan **drawable ve texture** girdilerini de kendi sözlüklerine kopyala.
7. Dosyanın tepesindeki **asset adını** ve efekt adını değiştir — oyunda
   çağıracağın ad budur.
8. ⛔ **Dosyayla aynı adda bir KLASÖR oluştur ve doku dosyalarını içine koy.**
   Yoksa import "texture bulunamadı" ile başarısız olur. (Videoda bu adım
   unutuldu ve iki kez hata verdi.)
9. CodeWalker ile geri import et.

### ✅ GERÇEK XML ŞEMASI — `core.ypt` açılıp okundu (45,5 MB)

Kök **birebir beş sözlük** (video doğru):
```xml
<ParticleEffectsList>
  <Name>core</Name>
  <EffectRuleDictionary>   <EmitterRuleDictionary>
  <ParticleRuleDictionary> <DrawableDictionary>  <TextureDictionary>
```

**Efekt → emitter bağı ADLA kurulur**, indeksle değil:
```xml
<EffectRuleDictionary><Item>
  <Name>_fog_foundry</Name>
  <PlaybackDelay value="2"/> <PlaybackSpeedScale value="1"/>
  <CullRadius value="2"/>    <CullDistance value="-4"/>
  <EventEmitters><Item>
    <EmitterRule>_fog_foundry_core</EmitterRule>
    <ParticleRule>_fog_foundry_core</ParticleRule>
    <MoveSpeedScale value="1"/> <ParticleScale value="1"/>
  </Item></EventEmitters>
</Item></EffectRuleDictionary>
```

### EMITTER RULE — 10 keyframe özelliği (gerçek adlar)

Alanlar: `Name` · `Domain1` · `Domain2` · `KeyframeProperties`

| Ne için | `<Name>` değeri |
|---|---|
| **daha çok/az partikül (zamana göre)** | `ptxEmitterRule:m_spawnRateOverTimeKFP` |
| daha çok/az partikül (mesafeye göre) | `ptxEmitterRule:m_spawnRateOverDistKFP` |
| **ekranda kalma süresi** | `ptxEmitterRule:m_particleLifeKFP` |
| oynatma hızı | `ptxEmitterRule:m_playbackRateScalarKFP` |
| **ne kadar uzağa gitsin** | `ptxEmitterRule:m_speedScalarKFP` |
| boyut | `ptxEmitterRule:m_sizeScalarKFP` |
| ivme | `ptxEmitterRule:m_accnScalarKFP` |
| sönümleme | `ptxEmitterRule:m_dampeningScalarKFP` |
| matris ağırlığı | `ptxEmitterRule:m_matrixWeightScalarKFP` |
| hız devralma | `ptxEmitterRule:m_inheritVelocityKFP` |

### ⛔ Keyframe alan adları YANILTICI

```xml
<Keyframes><Item>
  <InterpolationInterval value="0"/>
  <KeyFrameMultiplier value="0"/>
  <RedChannelColour value="4"/>    <GreenChannelColour value="7"/>
  <BlueChannelColour value="0"/>   <AlphaChannelColour value="0"/>
</Item></Keyframes>
```

`*ChannelColour` adları **genel amaçlı dört kanaldır**, renkle ilgisi yoktur.
`m_spawnRateOverTimeKFP` içinde `RedChannelColour=4` demek "spawn oranı 4"
demektir. `m_xyzMinKFP` içinde Red/Green/Blue = **X/Y/Z**'dir.
Bu isimlendirme CodeWalker'ın kendi seçimi; alanın anlamı **hangi
`<Name>` altında olduğuna** bağlıdır.

### PARTICLE RULE — davranış listesi

Alanlar: `Name` · `FxcFile` · `FxcTechnique` · `Spawner1/2` · **`Behaviours`** ·
`ShaderVars`

`Behaviours` içindeki `<Type value="…"/>` değerleri (`core.ypt` sayımı):

| Type | Adet | Type | Adet |
|---|---:|---|---:|
| Age | 1596 | AnimateTexture | 721 |
| Velocity | 1596 | Collision | 253 |
| **Size** | 1596 | Wind | 245 |
| **Colour** | 1596 | Noise | 119 |
| Sprite | 1444 | Model | 114 |
| Acceleration | 1289 | ZCull | 103 |
| Dampening | 1144 | Light | 65 |
| MatrixWeight | 1110 | Trail · Attractor · Decal · | |
| Rotation | 1109 | DecalPool · FogVolume · Liquid · River | tek haneli |

### RENK — gerçek alan adları

```
ptxu_Colour:m_rgbaMinKFP            (1596 particle rule'un hepsinde)
ptxu_Colour:m_rgbaMaxKFP
ptxu_Colour:m_emissiveIntensityKFP
```

Burada `RedChannelColour`/`Green`/`Blue`/`Alpha` **gerçekten** renktir.
Diğer sık kullanılan özellikler: `ptxu_Size:m_whdMinKFP` / `m_whdMaxKFP`
(genişlik-yükseklik-derinlik) · `ptxu_Rotation:m_angleMinKFP` / `Max` ·
`ptxu_Acceleration:m_xyzMinKFP` / `Max` · `ptxu_Light:m_rgbMinKFP` / `Max`.

⚠ **Hâlâ [DOĞRULANMADI]:** rengi script'ten değiştirilebilir yapan bayrağın
hangi alan olduğu. Video "bir değişken"den bahsediyor ama adını söylemiyor;
`Colour` behaviour'unun `Unknown*` alanlarından biri olması muhtemel.
`SetParticleFxColour` çalışmıyorsa sebep budur.

## 7d. `.ypt` ÜRETİMİ — CodeWalker.Core YAZAR, zincir uçtan uca çalışıyor

**Sürüm: CodeWalker 30_dev46, `CodeWalker.Core.dll` 2023-12-13.**
Bu sürümle sıfırdan `.ypt` üretildi, oyun formatında kaydedildi ve geri
okunarak doğrulandı. Daha yeni sürüme, .NET SDK'ya ya da GUI'ye **gerek yok**.

Doğrulanmış hat:

```
make_dds.py          -> 128x128 A8R8G8B8 sprite (kendi urettigimiz)
build_custom_ptfx.py -> .ypt.xml (efekt/emitter/particle kurallari sifirdan)
XmlYpt.GetYpt()      -> nesne agaci
YptFile.Save()       -> 7.865 bayt RSC7
YptFile.Load()       -> geri okuma: butun adlar + doku yerinde
```

### ⛔ ÖNCE BU: "ölçtüm, yok" demeden ÖNCE property adını doğrula

Bu bölümün önceki hâli **"CodeWalker `.ypt` YAZAMAZ"** diyordu. Yanlıştı, ve
tek sebebi vardı: **var olmayan property adları okundu.**

| Okuduğum | Gerçek | Sonuç |
|---|---|---|
| `EffectRuleDictionary.Effects` | `.EffectRules` | `$null.Length` → **0** |
| `PtfxList.EffectRuleDict` | `.EffectRuleDictionary` | `$null` |
| `AllEffects` | yalnız `Load()` doldurur, `GetYpt()` doldurmaz | 0 |

PowerShell olmayan bir property'ye erişince **hata vermez, `$null` döner**;
`$null.Length` de `0`'dır. Yani ölçüm aleti sıfır gösterdi ve ben bunu verinin
sıfır olduğu sanıp saatlerce yanlış yönde ilerledim, hatta belgeye
"imkânsız" diye yazdım. (Bu, CLAUDE.md §2'nin aynısı: **aracın bir şeyi
göstermemesi o şeyin yok olduğu anlamına gelmez.**)

Refleks olsun: yabancı bir DLL'i sorgularken önce
`$obj.GetType().GetProperties() | % Name` yaz, ya da guard kullan —

```powershell
function P($o,$ad){
  if(-not $o.PSObject.Properties[$ad]){ throw "PROPERTY YOK: $($o.GetType().Name).$ad" }
  $o.$ad }
```

### ⛔ Sessiz çöküşün gerçek sebebi: EKSİK BIRAKILAN KEYFRAME YUVASI

`Save()` içindeki `NullReferenceException`
(`ResourceBuilder.AssignPositions` → `ResourceSystemBlock.set_FilePosition`)
neredeyse her zaman **eksik yazılmış bir `KeyframeProperty` yuvasıdır.**

Her davranış tipinin yuva sayısı **sabittir ve hepsi yazılmalıdır**.
Yazılmayan yuva null blok bırakır; XML sorunsuz ayrışır, sözlükler dolu
okunur, hata bir adım sonra `Save()`'de gelir ve **hangi yuva olduğunu
söylemez.**

`core.ypt`'teki **15.430 davranışta** ölçüldü — her tip TEK bir yuva sayısı
gösteriyor, istisna yok:

| KFP | Davranış tipleri |
|---:|---|
| 0 | `Age` · `Velocity` · `Sprite` · `DecalPool` · `Liquid` · `Model` · `River` |
| 1 | `MatrixWeight` · `AnimateTexture` · `Wind` · `Trail` · `Attractor` |
| 2 | `Acceleration` · `Dampening` · `Collision` · `ZCull` · `Decal` |
| 3 | `Colour` |
| 4 | `Size` · `Rotation` · `Noise` |
| 7 | `FogVolume` |
| 9 | `Light` |

Yuva `<Name>`'leri gerçek şemadır (1736/1736 sabit):

- `Size` → `m_whdMinKFP` · `m_whdMaxKFP` · `m_tblrScalarKFP` · `m_tblrVelScalarKFP`
- `Colour` → `m_rgbaMinKFP` · `m_rgbaMaxKFP` · `m_emissiveIntensityKFP`
- `Rotation` → `m_initialAngleMinKFP` · `m_initialAngleMaxKFP` · `m_angleMinKFP` · `m_angleMaxKFP`

`<Unknown6C>` ise **sabit değil**: dosya içi konumdur, yuva başına 256 artar
(Size KFP0 için 331 farklı değer ölçüldü). İstediğin tabandan başlat.

**`Velocity`'nin 0 yuvası olması hata değil.** Parçacık hızı davranışta
değil, **emitter** kuralının `speedScalar`'ında ve creation/target
domain'lerinde tanımlanır. Velocity'ye keyframe yazmaya çalışmak `Save()`'i
çökerten en kolay yoldur.

### ⛔ Diğer iki zorunlu blok

- **`EventEmitters/Item/UnknownData`** — içeriği boş olabilir, ama **var
  olmalı**: `<UnknownData><EventEmitterFlags /><Unknown10 /></UnknownData>`.
  Yoksa aynı `Save()` çöküşü.
- **`Sprite`** davranışı 0 keyframe alır ama `Unknown30 34 38 40 44 48 4C
  50 54 58 5C 60` alanlarının hepsini ister (`5C` = `0x100`).

### Üretim hattı — hangi betik ne yapar

**Normal üretim tek komuttur**, ara adımları elle çalıştırma:

```powershell
scripts\ptfx_yap.ps1 -Ad muto_spor -Renk 0.2,0.9,0.35 -Hedef <stream klasoru>
scripts\ptfx_yap.ps1 -Ad muto_x -Gorsel kendi.png -Boyut 0.4 -Yukselme 0.8 -Hedef <k>
```

Doku → XML → ikili → eksik alanları tamamla → doğrula → dağıt.

| Betik | İş |
|---|---|
| `ptfx_yap.ps1` | **giriş noktası** — hattın tamamı |
| `make_dds.py` | DXT5/DXT1 + mip zincirli DDS (`--kaynak` ile hazır PNG'den) |
| `build_custom_ptfx.py` | sıfırdan efekt/emitter/particle kuralı XML'i |
| `ypt_xml_to_bin.ps1` | XML→ikili + **CodeWalker'ın atladığı alanlar** + doğrulama + dağıtım |
| `ypt_transplant.py` | **teşhis**: çalışan vanilla efekti kopyalayıp tek değişken değiştirir |
| `make_test_sheet.py` | **teşhis**: hücreleri farklı şekilli test sheet'i |
| `make_butterfly_sheet.py` | kanat çırpma sprite sheet'i (prosedürel, tutarlı kareler) |
| `ptfx_onizleme.py` | derlenmiş `.ypt`'nin verisinden animasyonlu önizleme (motor çıktısı DEĞİL) |
| `build_ptfx.ps1` | vanilla efekt kataloğunu indeksler (`assetdb.py ptfx/fx`) |

⛔ `XmlYpt.GetYpt` + `Save()`'i **elle çağırma** — `ypt_xml_to_bin.ps1`
olmadan dosya shader'sız ve VFT'siz çıkar, oyunda sessizce bozulur.

### ⛔⛔ CodeWalker XML okuyucusu `VFT` de YAZMAZ — sınıf kimliği sıfır kalır

`FxcFileHash` ile aynı sınıf hata, ama daha geniş: XML'den üretilen bir
`.ypt`'de **hiçbir bloğun `VFT`'si yazılmaz**, hepsi `0` çıkar. `VFT`
nesnenin sınıf kimliğidir (vtable); sıfırsa motor bloğun türünü çözemez.

Ölçüldü — `core.ypt`'te her tip **tek** değer taşıyor, sıfır sapma:

| Blok | Örnek | VFT |
|---|---:|---|
| Texture | 107/107 | `1080137320` |
| EffectRule | 964/964 | `1080081688` |
| EmitterRule | 1993/1993 | `1080083608` |
| ParticleRule | 1736/1736 | `1080085192` |
| EventEmitter | 2543/2543 | `1080100952` |
| KeyframeProp | 4820/4820 | `1080085392` |
| EffectRuleDict / EmitterRuleDict / ParticleRuleDict | 1 | `1080048016` / `1080048056` / `1080048096` |

Davranışlar tip başına tek değer: `Age 1080067288 · Velocity 1080075080 ·
Size 1080074648 · Colour 1080070168 · Sprite 1080076760 · AnimateTexture
1080068072 · Acceleration 1080066920 · Rotation 1080073832 · Dampening
1080070840 · MatrixWeight 1080071352 · Noise 1080072136 · Wind 1080075768 ·
Model 1080077240 · Trail 1080078056 · Collision 1080069256 · Attractor
1080068456 · ZCull 1080175704 · Decal 1080170408 · DecalPool 1080170920 ·
FogVolume 1080172152 · Light 1080174040 · Liquid 1080174872 · River
1080175208`

Domain'ler şekil başına: `Sphere 1080088936 · Box 1080088880 ·
Cylinder 1080088992 · Attractor 1080089048`

**`ShaderVars` girdilerinin de kendi VFT'si var** — ve doku bağını kuran
nesne budur (`Type=Texture`). Atlanması kolay, çünkü davranış listesinde
değil ayrı bir listede:

| ShaderVar tipi | Örnek | VFT |
|---|---:|---|
| `Texture` | 5108/5108 | `1080097544` |
| `Vector2` | 18846/18846 | `1080097368` |
| `Vector4` | 1686/1686 | `1080097368` |
| `Keyframe` | 10216/10216 | `1080097256` |

`Vector4` ile `Vector2` aynı VFT'yi paylaşır.

`scripts/ypt_xml_to_bin.ps1` hepsini yazar ve sıfır kalırsa **exit 1**.

### Parçacığı HAREKET ettiren şey: target domain'in konumu

⛔ `Velocity` davranışının **0 keyframe yuvası** vardır — oraya hız
yazılmaz. Yükselen duman/spor **`Domain2` (target domain) konumuyla**
yapılır: parçacık creation domain'de doğar, target domain'e doğru gider.

Ölçüldü: vanilla emitter'ların **%89,2**'sinde
`ptxTargetDomain:m_positionKFP`'nin Z'si sıfırdan farklı, **medyan +0.400**.
İki domain de aynı merkezdeyse net yön oluşmaz ve efekt yerinde durur.

`m_speedScalarKFP` yönü değil **hızı** verir (vanilla medyanı 0.85).

### ⛔ `m_zoomScalarKFP` efektin TÜM uzamsal ölçeğini sürer

Sadece parçacık boyutunu değil; yayılım, mesafe, boyut hepsi birden.
Oyunda ölçüldü: 338 olan değeri boşaltınca efekt her boyutta çöktü ve
`whd` keyframe'lerini **50×** çarpmak bunu telafi etmedi.

Vanilla'da değer efektin büyüklüğüyle ölçekleniyor: minik hapşırık
efekti `0.75`, dev gaz sütunu `1200`, **medyan 51.8**, %77,2'si dolu.
Boşaltmak meşrudur (%22,8'i boş) ama efekti küçültür.

### ⛔ AÇIK SORUN: GÖMÜLÜ dokuda sprite sheet DİLİMLENMİYOR

Bu **çözülmedi.** Bir sonraki oturum sıfırdan aramasın diye ölçümler burada.

Oyunda ölçülen tablo — hepsi **aynı particle rule**, tek değişken doku:

| Test | Doku | Sonuç |
|---|---|---|
| `vs2` | vanilla sheet, `core.ypt`'ten **isimle** | **tek hücre** ✅ |
| `dict` | vanilla sheet isimle + dosyada gömülü sözlük de var (kullanılmıyor) | **tek hücre** ✅ |
| `van` | **aynı vanilla dokunun ham verisi**, bizim dosyaya gömülü | dört hücre ❌ |
| `test3` | bizim ürettiğimiz DDS, gömülü | dört hücre ❌ |

Okunuşu:

- Motor **gerçekten dilimliyor** — `ptfx_grass_blades` (sheet olmayan, şekli
  tartışılmaz vanilla doku) doğru çizildiği için dış doku çözümünün
  çalıştığı da kanıtlandı; yani `vs2`'nin tek hücresi yedek doku değil.
- **Bizim DDS kodlamamız masum** — `van` vanilla'nın ham verisini taşıyor
  ve o da başarısız.
- **Gömülü sözlüğün varlığı masum** — `dict` sözlük dosyada dururken
  sorunsuz dilimliyor.
- Kusur, kuralın **gömülü bir dokuya bağlanması** durumunda ortaya çıkıyor.

Denenip **elenen** düzeltmeler (hepsi gerçek eksikti, düzeltildi, ama
belirtiyi çözmedi): `FxcFileHash` · blok `VFT`'leri · `FileVFT` ·
`ShaderVar` VFT'leri · `UsageFlags` · DXT1/DXT5 · mip derinliği.
Doku nesnesi vanilla ile **alan alan aynı** (`UsageData` dahil), doku
sözlüğünün hash tablosu tutarlı.

**Sıradaki tek somut yön:** dokuyu kendi `.ypt`'mize gömmek yerine
`core.ypt`'nin doku sözlüğüne eklemek ve kuraldan isimle çağırmak —
`vs2`/`dict` bunun çalıştığını gösteriyor. GTA'daki özel partikül
modlarının mevcut `.ypt` dosyalarını düzenlemesinin sebebi bu olabilir.

⚠ Bu sınır **yalnız sprite sheet animasyonunu** etkiliyor. Tek karelik
özel doku, renk, boyut, ömür, doğum oranı, yayılım ve yükselme gömülü
dokuyla sorunsuz çalışıyor (oyunda doğrulandı).

### ⛔ `m_sizeScalarKFP` BOYUTUN ASIL KOLUDUR — `whd` değil

Oyunda ölçüldü: aynı efektin `whd` keyframe'leri **200×** çarpıldığında
parçacık gözle fark edilir kadar büyümedi; yalnızca `m_sizeScalarKFP`
`0.4437 → 100` yapıldığında **dev boyuta** çıktı.

Yani parçacığı büyütmek isterken `whd`'yi çarpmak boşa kürek. Alanın
matematiksel ölçeği hâlâ çözülmedi (vanilla dağılımı medyan 57.6 ile
yüzde gibi duruyor ama donör 0.4437 ile görünür parçacık üretiyor) —
ama **hangi kolun boyutu sürdüğü** artık deneyle biliniyor.

### ⛔⛔ EN ÖNEMLİSİ: CodeWalker `FxcFileHash`'i YAZMAZ — shader'sız `.ypt`

**Bu bir CodeWalker hatasıdır, senin XML'inin kusuru değil.** XML'den
üretilen **her** `.ypt` shader hash'i sıfır çıkar. Bozulmamış bir vanilla
dosyayla ölçüldü:

| | `FxcFileHash` |
|---|---|
| `cut_arena.ypt` ikili okuma | `246470498` |
| **aynı dosya**, XML turundan | **`0`** |

`FxcFile` **metni** doğru görünür (`ptfx_sprite`), hash sıfırdır ve motorun
baktığı şey hash'tir. Belirti tam olarak şudur ve başka hiçbir denetim
yakalamaz:

- dosya geçerli, `Save()` çöker değil
- `YptFile.Load()` geri okuma turu geçer
- `RequestNamedPtfxAsset` başarılı
- `StartParticleFx*` **sıfırdan farklı handle** döndürür
- **ekranda hiçbir şey olmaz**

Düzeltme JenkHash ile: `GenHash('ptfx_sprite') = 246470498` — vanilla ikili
değerle birebir. `FxcTechniqueHash` vanilla'da da `0`, **ona dokunma**.

```powershell
foreach ($pr in $ypt.PtfxList.ParticleRuleDictionary.ParticleRules.data_items) {
    $pr.FxcFileHash = [CodeWalker.GameFiles.JenkHash]::GenHash([string]$pr.FxcFile)
}
```

Hazır betik: `scripts/ypt_xml_to_bin.ps1` — GetYpt → hash yaz → Save →
geri oku → `FxcFileHash` sıfırsa **çıkış kodu 1**. `.ypt` üretirken
`XmlYpt.GetYpt` + `Save()`'i elle çağırma, bu betiği kullan.

⚠ Aynı sınıftan başka alanlar olabilir: **CodeWalker'ın XML'e yazdığı her
alanı geri okuduğunda aynı değerde bulmasını bekleme.** Yeni bir kaynak
tipinde üretim yaparken ilk iş vanilla bir dosyayı XML'e çıkarıp geri okumak
ve **ikili ile XML turunu alan alan karşılaştırmaktır** — aracın hangi
alanları düşürdüğü ancak böyle görülür.

### ⛔ BİLİNMEYEN ALANA 0 YAZMA

`Unknown*` alanlarına "bilmiyorum, 0 bırakayım" demek sessiz hata üretir.
Ölçüldü — bu değerlerin çoğunda 0 vanilla'da **hiç geçmiyor**:

| EffectRule | En sık | Pay |
|---|---|---|
| `Unknown50` | `0xFFFFFFFF` | 537/964 |
| `Unknown88` | `0x1010100` | 283/964 |
| `Unknown8C` | `0x10004` | 422/964 |
| `UnknownA4` | `50` | 144/964 |
| `UnknownA8` | `60` | 176/964 |
| `UnknownAC` | `10` | 176/964 |
| `UnknownB0` | `30` | 224/964 |

`UnknownA0/A4/A8/AC/B0` mesafe/LOD bandı görünümündedir (0/50/60/10/30) ve
sıfırlanırsa efekt hiçbir mesafede çizilmeyebilir.

| ParticleRule | En sık | Pay |
|---|---|---|
| `Unknown10` | `2` | 1341/1736 |
| `Unknown100` | `2` | 1098/1736 |
| `Unknown108` | `2` | 1347/1736 |
| `Unknown10C` | `0x10100` | **1638/1736 (%94)** |
| `Unknown1D0` | `5` | 890/1736 |
| `Unknown1E8` | `0x101` | 1044/1736 |
| `Unknown220` | `0x2` | 736/1736 |

Kural: bir `Unknown` alanına değer yazmadan önce
`assetdb.py`/`core.ypt` üzerinde **dağılımına bak**; en sık değeri al.

### ⛔ Dosya geçerli ama OYUNDA HİÇBİR ŞEY GÖRÜNMÜYOR — üç sebep daha

Bu üçü `Save()`'i çökertmez, geri okuma turunu geçer, `StartParticleFx*`
**sıfırdan farklı handle** döndürür (yani motor efekti buldu) ve yine de
ekranda hiçbir şey olmaz. Handle'ın dolu gelmesi "çalışıyor" demek değildir;
yalnız **adın bulunduğu** anlamına gelir.

**1. `FxcTechnique` serbest metin değil, kapalı bir listedir.**
`core.ypt`'teki 1.736 particle rule'da yalnız altı değer geçer:

| Teknik | Adet |
|---|---:|
| `RGBA_lit_soft` | 904 |
| `RGBA_lit` | 425 |
| `RGB_lit_soft` | 136 |
| `RGB_lit` | 75 |
| `RGB_soft` | 70 |
| `RGBA_soft` | 30 |

`default` **hiç geçmez.** Yazılırsa shader çözülmez, efekt sessizce
çizilmez. `RGBA` = alfalı doku, `_soft` = derinlik geçişli yumuşak kenar.
`FxcFile` ise yalnız `ptfx_sprite` (1.686) ya da `ptfx_trail` (50).

**2. `m_sizeScalarKFP` YÜZDE ölçeğindedir, kesir değil.**
2.097 keyframe'de ölçüldü: `%5 = 1.0` · **medyan 57.6** · `%75 = 125` ·
`%95 = 297` · max 1000. Yani `1.0` yazmak en alt %5'e düşmektir —
parçacık boyutunun ~%1'i, gözle görülmez. **100 = nötr.**

Aynı yüzde ölçeği `m_accnScalarKFP` (medyan 98.4), `m_dampeningScalarKFP`
(98.6), `m_matrixWeightScalarKFP` (93.8) için de geçerli.
**Ama hepsi değil:** `m_speedScalarKFP` (medyan 0.85),
`m_particleLifeKFP` (1.40) ve `m_playbackRateScalarKFP` (1.20) ~1.0
ölçeğindedir. Alan adına bakıp ölçek varsayma — **ölç**.

**3. Boş bırakılan keyframe yuvası çarpanı SIFIRLAR.**
Yuvanın var olması yetmez, bazılarının dolu olması da gerekir. Hangisinin
boş bırakılabileceği ölçülür:

| Yuva | Vanilla'da boş | Boş bırakılır mı |
|---|---:|---|
| `Size:m_tblrScalarKFP` | %0,5 | ⛔ **HAYIR** — boş = çarpan 0 = sıfır boyut |
| `Size:m_whdMin/MaxKFP` | %0,7 / %0,8 | ⛔ hayır |
| `Colour:m_rgbaMin/MaxKFP` | %0,1 / %0,2 | ⛔ hayır |
| `Size:m_tblrVelScalarKFP` | %83,6 | ✅ evet |
| `Colour:m_emissiveIntensityKFP` | %71,7 | ✅ evet |
| `Emitter:m_matrixWeightScalarKFP` | %99,1 | ✅ evet |
| `Emitter:m_dampeningScalarKFP` | %95,8 | ✅ evet |
| `Emitter:m_particleLifeKFP` | %0,6 | ⛔ hayır |
| `Emitter:m_spawnRateOverTimeKFP` | %3,6 | ⛔ hayır |

Kural: **vanilla'da %5'ten az boş olan yuva zorunludur.**

`CullRadius` / `CullDistance` `0` olması normaldir (869/964 ve 836/964) —
oraya bakma. `Unknown74` **964/964 `0.25`**, sabittir.

### Teşhis yöntemi: BÖLEREK DARALT, blok ağacında gezme

`GetReferences()`/`GetParts()` ağacında null aramak **işe yaramaz** —
`ResourcePointerArray64<T>` foreach'te `NotImplementedException` atar
(CLAUDE.md §9) ve yürüyüş sessizce yanlış sonuç verir.

Çalışan yöntem: vanilla bir `.ypt`'yi XML'e çıkar (bu XML `Save()` turunu
geçer), sonra **tek tek** kendi bloklarınla değiştirip hangisinde çöktüğüne
bak. Sözlük seviyesinde 4 test, sonra bölüm seviyesinde 4 test — sekiz
çalıştırmada kusur bulunur.

### Kaydedilen dosyanın boyutu KÜÇÜK olması hata değil

`Save()` çıktısı RSC7'dir ve **zlib sıkıştırılmıştır**. `cut_arena.ypt`
32.768 bayt açılmış → `Save()` **3.077 bayt**. Daha önce bu farka bakıp
"dosya bozuldu" sonucuna vardım; ölçüt boyut değil, **geri okumadır**:

```powershell
$d=[IO.File]::ReadAllBytes($yol)
$e=[CodeWalker.GameFiles.RpfFile]::CreateResourceFileEntry([ref]$d,0)
$d=[CodeWalker.GameFiles.ResourceBuilder]::Decompress($d)
$y=New-Object CodeWalker.GameFiles.YptFile; $y.Load($d,$e)
```

`YptFile.Load()` **`RpfFileEntry` ister**; `null` geçilirse patlar ve bu da
"dosya bozuk" sanılır.

Geri okumada `Behaviours` **0 görünür — bu kayıp değildir.** İkili yükleme
`BehaviourList1..5`'i doldurur; `Behaviours` XML tarafının toplayıcısıdır.
Vanilla `cut_arena` da aynı şekilde okunur.

### Şema: doku bağı

⛔ **Doku bağı `<Behaviours>` içinde DEĞİL, `<ShaderVars>` içindedir.**
Ölçüldü: `Behaviours` yalnız şu tipleri taşır — `Age Acceleration Velocity
Rotation Size Dampening MatrixWeight Wind Colour Sprite` (+ tablo yukarıda).
`Texture` orada **hiç geçmez**.

⛔ `Texture` girdisinde `<Name>` **doku adı değil, SAMPLER YUVASIDIR**
(`refractionmap` / `normalspecmap` / `diffusetex2`); gerçek doku adı ayrı
bir `<TextureName>` alanındadır. Ters yazılırsa XML ayrışır, **hata çıkmaz,
doku bağlanmaz**:

```xml
<ShaderVars>
  <Item>
    <Type value="Texture" />
    <Name>diffusetex2</Name>       <!-- SAMPLER YUVASI -->
    <Unknown18 value="4" />
    <Unknown3C value="0" />
    <TextureName>muto_ptfx_soft</TextureName>   <!-- GERCEK doku adi -->
  </Item>
</ShaderVars>
```

`TextureDictionary` girdisi şunları **zorunlu** ister:
`Name` · `Unk32` · `Usage` (**`DIFFUSE`**, `DEFAULT` değil) · `UsageFlags` ·
`ExtraFlags` · **`Width`** · **`Height`** · **`MipLevels`** · **`Format`** ·
`FileName`. Bunlar eksikse doku sessizce boş kalır.

⚠ DDS dosyaları **XML ile aynı klasörde** olmalı; yoksa
`Texture file not found` ile çöker. (Videodaki "aynı adda klasör aç"
uyarısının gerçek sebebi budur.)

### Partikül SPRITE SHEET animasyonu — `AnimateTexture`

Kanat çırpan böcek, alev, sıçrayan su gibi **kare kare değişen** partiküller
mesh animasyonuyla değil, tek dokuya dizilmiş karelerin UV ile oynatılmasıyla
yapılır. Vanilla'da 781 particle rule bunu kullanıyor.

**`UnknownC4` = kare sayısı − 1** (son karenin indeksi). Çıkarımla değil,
iki bağımsız vanilla dokusu **çıkarılıp gözle sayılarak** doğrulandı:

| Doku | Boyut | Izgara | Kare | `C4` |
|---|---|---|---:|---:|
| `ptfx_smoke_billow_anim_rgba` | 1024×1024 | 6×6 | 36 | **35** |
| `ptfx_water_splashes_sheet` | 512×512 | 2×2 | 4 | **3** |

Izgara **kare**: sütun = satır = √(kare sayısı). Kareler soldan sağa,
yukarıdan aşağıya. `UnknownCC` = `0x1000100` (6×6 sheet'lerin değeri),
`C0` = 0, `C8` = 0. `m_animRateKFP` boş bırakılırsa motor varsayılan hızda
oynatır.

İkisi de **siyah zemin üzerine gri maske** — renk motordan gelir.

⚠ Kare sayısı dokuyla tutarlı olmalı; `build_custom_ptfx.py --sheet N`
tam kare olup olmadığını ve dokunun ızgaraya tam bölündüğünü denetler.

### Partikül 3B MODEL olabilir — `Model` davranışı

Partikül illa sprite olmak zorunda değil. 133 particle rule katı bir mesh
çiziyor; model `.ypt`'nin kendi `DrawableDictionary`'sine gömülü
(`core.ypt`'te **46 model**: mermi kovanı, kar tanesi, yaprak, cam kırığı).
Bağ kuralın içindeki `<Drawables>` bloğunda **isimle** kuruluyor:

```xml
<Type value="Model" />
<Drawables>
  <Name>ptfx_model_pistol_casing/ptfx_model_pistol_casing</Name>
</Drawables>
```

**Sınırı:** model partikülü katıdır — konumlanır, döner, ölçeklenir ama
**iskelet animasyonu oynatmaz.** Kanat çırpma, alev dalgalanması gibi
şekil değiştiren şeyler için `AnimateTexture` yolu kullanılır.

### FiveM özel `.ypt` streaming'i — DOĞRULANDI

Oyunda ölçüldü: `stream/` içine konan özel `.ypt`, dosya adıyla named ptfx
asset olarak kaydoluyor.

```
[ptvarlik] muto_spore   yuklendi=1
[ptcal]    handle=29442   0.6 sn sonra yasiyor = 1
```

`data_file` satırı **gerekmiyor**. Doku `.ypt`'ye gömülü, ayrı `.ytd` yok.

⛔ Ama doku **DXT olmalı**: ilk sürüm `A8R8G8B8` (tek mip) idi ve istemci
kaynağın tamamını düşürüyordu — Lua bile yüklenmiyordu. Ölçüm:
`core.ypt`'teki 107 partikül dokusunun tamamı DXT (DXT5 75 · DXT1 32),
mip 4-9; sıkıştırılmamış örnek yok.

⛔ **Bozuk bir stream varlığı kaynağın TAMAMINI düşürür ve sessizdir.**
Sunucu `Started resource X` yazar; istemcide hiçbir komut kaydolmaz,
hiçbir print çıkmaz, F8'de hata da yoktur. Lua'ya hiç sıra gelmez.
Teşhis: `stream/` klasörü **olmayan** ikinci bir kaynak kur — onun komutu
çalışıyorsa kusur stream varlığındadır.

⛔ Stream dosyası ekleyip çıkardıktan sonra **o kaynağı `restart` et**.
Sunucu dosya listesini kaynak başlarken tarar; restart edilmezse istemciye
artık var olmayan bir dosya vaat edilir ve mount yine düşer. (Bu tam olarak
yaşandı: dosya silindi, kaynak restart edilmedi, belirti değişmedi.)

### Oyunda kullanım — iki ayrı ad

**VARLIK adı = `.ypt` DOSYA adı** (`RequestNamedPtfxAsset`),
**EFEKT adı = `EffectRule`'un `<Name>`'i** (`StartParticleFx*`).
Aynı olmak zorunda değiller ve genelde değildirler.

`.ypt` için `data_file` satırı **gerekmez** — `stream/` içindeki dosya adıyla
kendiliğinden named ptfx asset olarak kaydolur.

⛔ `UseParticleFxAssetNextCall` **her** `Start` çağrısından önce tekrarlanır;
adı üstünde, yalnız bir sonraki çağrı için geçerlidir. Bir kez çağırıp
döngüye girmek sessizce vanilla varlığına düşer.

## 8. Collision — ÜÇ AYRI BAYRAK KATMANI

Sık karıştırılır. Üçü farklı yerde yaşar ve farklı iş yapar.

### 8.1 Materyalin kendi bayrakları (16)

```
STAIRS          NOT COVER         NO DECAL        NO PTFX
NOT CLIMBABLE   WALKABLE PATH     NO NAVMESH      TOO STEEP FOR PLAYER
SEE THROUGH     NO CAM COLLISION  NO RAGDOLL      NO NETWORK SPAWN
SHOOT THROUGH   SHOOT THROUGH FX  VEHICLE WHEEL   NO CAM COLLISION ALLOW CLIPPING
```

Aynı panelde: `Procedural ID` · `Ped Density` · `Room ID` · `Material Color Index`.

### 8.2 Bound COMPOSITE bayrakları (31, İKİ ayrı küme)

`ybn/properties.py::BoundFlags`. Obje **iki** küme taşır:
`composite_flags1` = **Type Flags** (bu bound *nedir*),
`composite_flags2` = **Include Flags** (bu bound *neyle çarpışır*).

```
UNKNOWN          MAP WEAPON       MAP DYNAMIC      MAP ANIMAL
MAP COVER        MAP VEHICLE      VEHICLE NOT BVH  VEHICLE BVH
PED              RAGDOLL          ANIMAL           ANIMAL RAGDOLL
OBJECT           OBJECT_ENV_CLOTH PLANT            PROJECTILE
EXPLOSION        PICKUP           FOLIAGE          FORKLIFT FORKS
TEST WEAPON      TEST CAMERA      TEST AI          TEST SCRIPT
TEST VEHICLE WHEEL  GLASS         MAP RIVER        SMOKE
UNSMASHED        MAP STAIRS       MAP DEEP SURFACE
```

Ölçülmüş örnek (havuz/su): Type = `MAP WEAPON` + `MAP DYNAMIC` + `MAP ANIMAL`
+ `MAP COVER` + `MAP RIVER`; materyal `WATER`, materyal bayrakları
`SEE THROUGH` + `SHOOT THROUGH` + `NO CAM COLLISION`.

### 8.3 Arketip bayrakları

§2'deki tablo (`Dynamic`, `Enable Door Physics`, `Has Cloth` …). Bunlar
collision'ın değil **arketipin** bayrakları.

### 8.4 Materyal tablosu (185)

`data/collision_materials.tsv` · sorgu: `assetdb.py mat [<ad>|--index N]`
Kaynak: Sollumz `ybn/collision_materials.py`; liste sırası = oyunun materyal
indeksi. **Çapraz doğrulandı:** `ANIMAL_DEFAULT = 171` — bizim yaratık rig'i
çalışmasında bağımsız olarak ölçülen değerle birebir aynı (CLAUDE.md §10).

Uçlar: en hafif `Fibreglass Hollow` (126.0), `Polystyrene` (157.5),
`Foam` (175.0); en ağır `Metal Solid Large` / `Metal Garage Door` /
`Metal Manhole` (31500.0). Sık kullanılanlar: `CONCRETE` 1 · `GRAVEL_SMALL` 31
· `GRASS_SHORT` 48 · `METAL_GARAGE_DOOR` 67 · `WOOD_SOLID_MEDIUM` 70 ·
`GLASS_SHOOT_THROUGH` 112 · `CAR_METAL` 116 · `WATER` 125 · `ANIMAL_DEFAULT` 171.

### 8.5 Ölçülmüş davranış

**`mesh` collision + `Dynamic` arketip bayrağı = obje dünya collision'ıyla
etkileşmez, yerin içine düşer.** Dinamik obje istiyorsan collision
**primitive** (bound box / cylinder) olmalı. Kapı standardı: `NOT COVER` +
`NOT CLIMBABLE`.

---

## 8.5b DECAL — İKİ AYRI SİSTEM VAR, KARIŞTIRMA

| | **A · Çalışma anı** | **B · Haritaya gömülü** |
|---|---|---|
| Nasıl | `AddDecal()` native'i | `.ydr` + ymap |
| Üretim | script, Blender yok | Blender + Sollumz |
| Ömür | `timeout` ile silinir, yıkanır | kalıcı |
| Maliyet | her istemcide çizim | sıfıra yakın |
| Ne zaman | olay bazlı: kan, lastik izi, sızıntı | kalıcı: graffiti, logo, yol çizgisi |

### A · Çalışma anı decal'ları

```lua
AddDecal(decalType, x,y,z, dirX,dirY,dirZ, sideX,sideY,sideZ,
         width, height, r,g,b, opacity, timeout, isLongRange, isDynamic, useComplexColn)
```

`dir` = yüzeyin normali (zemin için `0,0,-1`), `side` = decal'ın yatay ekseni.
`timeout` negatifse kalıcı. Dönen tamsayı `RemoveDecal` / `IsDecalAlive` /
`GetDecalWashLevel` ile kullanılır.

**Hazır yardımcılar:** `AddPetrolDecal` (benzin — **tutuşabilir**) ·
`_AddOilDecal` · `StartPetrolTrailDecals` + `AddPetrolTrailDecalInfo` +
`EndPetrolTrailDecals` (araç arkası iz) · `ApplyPedDamageDecal` (ped üstü yara)

**Toplu işlemler:** `RemoveDecalsInRange` · `FadeDecalsInRange` ·
`WashDecalsInRange` · `RemoveDecalsFromVehicle` / `FromObject` ·
`SetDisableDecalRenderingThisFrame`

**⭐ Kendi dokunu giydirmek:** `PatchDecalDiffuseMap(decalType, txd, texture)`
— var olan bir tipin dokusunu değiştirir; **yeni asset üretmeden** özel
kan/graffiti yapmanın yolu. `UnpatchDecalDiffuseMap` geri alır.

### ⛔ DECAL DOKULARI GRİ MASKEDİR — RENGİ SEN VERİRSİN

**Ölçüldü:** `fxdecal_blood_pool2.dds` (256×256 DXT5) içinden örneklenen
**800 renk çiftinin tamamı R=G=B**. Doku renk taşımıyor, yalnız şekil + alfa.

Belirti: *"decal'lar çalışıyor ama renkleri yok"* — gri/beyaz lekeler.

Renk **iki ayrı yerden** gelir, hangi sistemi kullandığına göre:

| Sistem | Renk nereden |
|---|---|
| **A · `AddDecal`** | `rCoef, gCoef, bCoef` parametreleri. `1,1,1` = nötr = **gri** |
| **B · model decal** | **vertex color** (`Color 1`). `decal.sps`'in renk parametresi **yok** |

Başlangıç değerleri (ayarlanacak): kan `0.35, 0.02, 0.02` · kanlı iz
`0.30, 0.03, 0.03` · yağ/benzin `0.10, 0.09, 0.06` · mermi izi `0.55` nötr gri.

⚠ B tarafı **[DOĞRULANMADI]**: `decal.sps` parametre listesinde renk alanı
olmadığı için vertex color olduğu çıkarımı yapıldı; oyunda teyit edilmedi.

### `decalType` tablosu — 194 tip

`data/decal_types.tsv` · sorgu: `assetdb.py decal <iş>` veya `--id <sayı>`

**Kaynak: oyunun kendi `common.rpf\data\effects\decals.dat`'ı** (131 KB).
FiveM belgesindeki enum **eksiktir**; bu tablo tam. ID aralığı 1010–10031.

| Kategori | Tip | Örnek ID |
|---|---:|---|
| VEHICLE BADGES | 32 | — |
| BANGS (mermi izi, `materialfx.dat`'tan referanslı) | 18 | 4010 metal · 4020 beton · 4050 ahşap |
| MUD / SCRAPES | 7 + 7 | — |
| BLOOD | 4 (+11 ilgili) | **1010** sıçrama · 1015 yönlü · 1017 sis · **9001** birikinti |
| BURN SCORTCH MARKS | 4 | — |
| WATER / OIL / PETROL | 4+4+4 | — |
| *TRANSFER* (kan/yağ/benzin/çamur/su taşınması) | 3'er | 2040 kanlı ayak izi · 3100 kanlı lastik |
| FOOTPRINTS (çamur/kum) | 2+2 | — |

⚠ **Aynı ID birden çok varyant taşır** ve motor **rastgele seçer** — `1010`'un
3 varyantı var. Aynı yere iki kez basmak aynı görseli vermez.

⚠ `washable` ve `underwater` sütunları davranışı belirler: `washable=1` ise
yağmur/`WashDecalsInRange` siler; `underwater=1` ise su altında da oluşur.

## 8.6 B · Haritaya gömülü decal — yüzeye yapışan leke/iz/yazı

Kaynak: "create basic decal" (Lamont Cranston, 61 sn, altyazısız — kare kare
izlendi) + Sollumz shader tablosu. Sorgu: `assetdb.py shader decal`.

### Reçete (Blender 5.0 / Sollumz 2.8)

1. **`Add → Mesh → Plane`** — `Size 2m`, **`Generate UVs` ✓**, `Align: World`,
   konum `0,0,0`. Decal düz bir dörtgendir; başka geometri gerekmez.
2. Yeniden adlandır (`decal_example`).
3. **Sollumz → Drawables → `Convert to Drawable`** → hiyerarşi:
   `decal_example` (drawable) → `decal_example.model` → `Plane.001` (mesh).
4. **Shader Tools** → arama kutusuna **`decal`** yaz → listeden seç →
   **`Create Shader Material`**.
5. Materyalin `Texture Parameters → DiffuseSampler`'ına DDS yükle,
   **`Embedded` ✓** işaretle, `Color Space: sRGB`.
6. **Render Bucket'a elle dokunma — doğru shader'ı seçersen Sollumz halleder.**
   Canlı ölçüldü (Blender 5.2 + Sollumz 2.8, materyal oluşturup okundu):

   | Shader | Otomatik bucket |
   |---|---|
   | `default.sps` | OPAQUE |
   | `decal.sps` · `decal_dirt` · `normal_decal` · `water_decal` | **DECAL** |
   | `cutout.sps` | CUTOUT |
   | `alpha.sps` · `glass.sps` · **`vehicle_decal.sps`** | ALPHA |

   `vehicle_decal → ALPHA` bizim vanilla ölçümümüzle **birebir** (395/395
   kullanım bucket 1). Sollumz'un shader başına varsayılanları Rockstar'ın
   gerçekte gönderdiğiyle uyuşuyor.

   ⚠ **Düzeltme:** bu belgenin önceki sürümü "bucket'ı elle 2 yap" diyordu.
   **Yanlıştı.** Videodaki `Opaque (0)`'ın sebebi bucket'ı unutmak değil —
   adam `decal` aramasını yapmış ama **`default` shader'ını bırakmış**
   (durum çubuğu "Added a **default.sps**" diyor, materyal adı `default`).

7. ⛔ **ASIL TUZAK: decal yapıp `default` shader'ında kalmak.** O zaman bucket
   `OPAQUE` olur, alfa çalışmaz, decal opak bir kare olarak çıkar — ve
   **hata verilmez.**

   12.000 `.ydr` + 12.000 `.yft` tarandı; decal shader'larının **5.482
   kullanımı** şöyle dağılıyor:

   | Bucket | Adet | Oran |
   |---|---:|---:|
   | **2 Decal** | **5.062** | **%92,3** |
   | 1 Alpha | 419 | %7,6 (neredeyse tamamı `vehicle_decal`) |
   | 0 Opaque | **1** | %0,0 |

   Yani Rockstar 5.482 kullanımda **bir kez** Opaque bırakmış. Sollumz'un
   varsayılanı `OPAQUE` (`ydr/properties.py:160`); değiştirilmezse decal opak
   çizilir, alfa çalışmaz, **hata da vermez.**
   ⚠ İstisna: **`vehicle_decal` bucket 1 (Alpha)** kullanıyor (395/395).

### Render Bucket — shader'dan AYRI bir alan

`szio.gta5.drawables.RenderBucket`:

| Değer | Ad | Anlamı |
|---:|---|---|
| 0 | Opaque | alfasız |
| 1 | Alpha | alfalı ama **gölgesiz** — genelde cam |
| **2** | **Decal** | alfalı decal, gölge yok |
| 3 | Cutout | alfalı **ve gölgeli** — çit/kafes |
| 4 | No Splash | yalnız `vehicle_nosplash` ile |
| 5 | No Water | yalnız `vehicle_nowater` ile |
| 6 | Water | su shader'ları |
| 7 | Displacement Alpha | en son çizilir; yalnız `glass_displacement` ile |

Sorgu: `assetdb.py shader --buckets`

### Decal shader'ları (35 tane)

`assetdb.py shader decal` tam listeyi verir. En sık kullanılanlar ve
**zorunlu dokuları**:

| Shader | Doku | Ne zaman |
|---|---|---|
| `decal` | `DiffuseSampler` | en yalın; sadece renk + alfa |
| `decal_dirt` | `DiffuseSampler` | kir/toz; `DirtDecalMask` parametresi var |
| `normal_decal` | + `BumpSampler` | yüzeyde kabartma istiyorsan |
| `normal_spec_decal` | + `BumpSampler`, `SpecSampler` | parlaklık da gerekiyorsa |
| `decal_glue` | `DiffuseSampler` | poster/etiket gibi yapıştırılmış |
| `decal_emissive_only` | — | yanan yazı/işaret |
| `decal_tnt` | + `TintPaletteSampler` | renk paletiyle tonlanan |
| `vehicle_decal` | + `DamageSampler`, `SpecSampler` | araç üstü |
| `mirror_decal` · `reflect_decal` · `spec_reflect_decal` | | yansımalı |

`decal`'ın parametreleri: `useTessellation=0` · `wetnessMultiplier=1` ·
`specularIntensityMult=0` · `specularFalloffMult=100` · `specularFresnel=0.97`

### Doku

Vanilla decal dokuları `decals_stains` gibi texture dictionary'lerde:
`decal_house_stain_03_a.dds`, `conc_stain1.dds`, `dirt_grime_01_*.dds`,
`dc_parking_splats_01*.dds`. **Hepsi alfa kanallı DDS** — decal'ın kenarı
alfa ile erir, geometriyle değil.

### Bilinen tuzaklar

- **Decal zemine gömülmez, ÜSTÜNE konur.** Z-fighting'i önlemek için
  ~1-2 cm yukarı al (video #7'de fur grass için de aynı yöntem: `0.01` kaydır).
- Yanlış shader **sessiz hatadır**: `default` shader'la yapılan decal opak bir
  kare olarak çıkar, alfa çalışmaz. Hata mesajı yoktur.
- Doku **embedded** değilse ayrı bir `.ytd` gerekir; tek bir decal için gömmek
  daha basit.

## 9. LOD zinciri — 3.07M vanilla entity üzerinde ÖLÇÜLDÜ

CodeWalker entity sekmeleri: `General` · **`LOD Hierarchy`** · `Extensions` · `Pivot`.
`LOD Hierarchy` yalnız iki alan taşır: **`ParentIndex`** ve **`NumChildren`**.

İndeks: `data/ymap_lod.tsv.gz` (`build_ymap_lod.ps1`) — vanilla 19.387 ymap +
custom 204 ymap = **3.145.882 entity**, bunların **1.556.743'ü bir LOD
zincirinde**. Sorgu: `assetdb.py lodchain`.

### ⛔ ymap ADI TEKİL DEĞİL — `rpfPath` olmadan ölçüm yanlış çıkar

**8252 ymap adının 4751'i birden çok RPF'te var** (base + DLC yamaları; bazı
adlarda 5 kopya). Sadece dosya adıyla indekslersen kopyalar üst üste biner,
entity indeksleri karışır ve zincir sahte "kopuk" görünür. İlk ölçümümde tam
olarak bu oldu: ad bazlı okuma **53.102 sahte kopukluk** ve eksik entity sayısı
üretti. İndeks bu yüzden `rpfPath` sütunu taşıyor; parent çözerken **önce aynı
RPF katmanına** bakılır.

### Zincir bütünlüğü — ölçülen

`parentIndex ≥ 0` olan **1.548.159** entity:

| Sonuç | Adet | Oran |
|---|---:|---:|
| parent çözüldü | 1.447.833 | %93,5 |
| ymap parent bildirmiyor | 5.183 | %0,3 |
| **parent indeksi bulunamadı** | **95.143** | **%6,1** |

⚠ **Bu %6,1 AÇIK BİR SORU, "vanilla bozuk" demek değil.** Ölçülen örnek:
`dt1_rd1.ymap[83]` parent olarak `dt1_lod[69]` istiyor; `dt1_lod.ymap`'in
**dört kopyasının da yalnız 42 entity'si var** (`CEntityDefs` = `AllEntities`
= 42, MLO instance yok). Yani indeks gerçekten yok. Olası açıklamalar
sınanmadı: `parentIndex` aynı LOD seviyesindeki ymap'lerin birleşik listesine
bakıyor olabilir, ya da `imap` grup dosyaları devrede olabilir. **Kendi
haritanda %6 kopukluk görürsen bunu referans al: vanilla'nın kendisi de bu
oranda "kopuk" ölçülüyor.**

### ⛔ `ParentIndex` tek başına anlamsızdır

Bir **sıra numarasıdır**; hangi dosyanın sırası olduğunu ymap başlığındaki
**`CMapData.parent`** söyler. Bu alan indekslenmeden zincir yürünemez.

**Dosya adı kalıbına güvenme.** `X.ymap → X_lod.ymap` kalıbı gerçek ama
kural değil: 8143 ymap'in yalnız 456'sı `*_lod`/`*_slod` adını taşıyor, ve
parent bildiren 7285 ymap'in **%79'unda** çocuk adı parent adıyla başlıyor —
yani her beşte biri tutmuyor.

### Ölçülen gerçek seviye geçişleri (parent → çocuk)

| Geçiş | Adet |
|---|---:|
| `LOD` → `HD` | 693.260 |
| `SLOD2` → `LOD` | 55.817 |
| `SLOD3` → `LOD` | 40.250 |
| `SLOD2` → `SLOD1` | 13.628 |
| `SLOD4` → `LOD` | 1.719 |

⚠ **Zincir düz bir merdiven DEĞİL.** Öğreticilerde anlatılan
`HD→LOD→SLOD1→SLOD2→SLOD3` sırası vanilla'da yok: **`SLOD1 → LOD` diye bir
geçiş hiç yok.** `SLOD1`, `LOD` ile `SLOD2` arasında bir basamak değil,
`SLOD2`'nin ayrı bir yan dalı. Ve **7 seviye** var, 5 değil:
`ORPHANHD · HD · LOD · SLOD1 · SLOD2 · SLOD3 · SLOD4`.

### `lodLevel` dağılımı

| Seviye | Adet |
|---|---:|
| `LODTYPES_DEPTH_ORPHANHD` | 1.527.999 |
| `LODTYPES_DEPTH_HD` | 1.234.368 |
| `LODTYPES_DEPTH_LOD` | 279.955 |
| `LODTYPES_DEPTH_SLOD1` | 27.423 |
| `LODTYPES_DEPTH_SLOD2` | 2.407 |
| `LODTYPES_DEPTH_SLOD3` | 722 |
| `LODTYPES_DEPTH_SLOD4` | 77 |

**`ORPHANHD` en yaygın seviyedir** — yani vanilla'da bile çoğu entity zincirsiz.
LOD zinciri istisnadır, kural değil.

### `childLodDist` — kural değil, gelenek

`parent.childLodDist == çocuk.lodDist` eşitliği **%86 tutuyor, %14 tutmuyor**
(692.525 eşit / 112.149 farklı). Örnek: `plg_01_chopped_field` `lodDist=220`
iken parent'ının `childLodDist=210`. `lodDist=-1` de görülür (arketip
varsayılanını kullan demek).

### Diğer ölçülenler

- `-1` = zincir sonu. Ara seviyede `LOD Adopt Me` (16) biti kurulur.
- `priorityLevel`: `PRI_REQUIRED` 2.584.698 · `PRI_OPTIONAL_MEDIUM` 182.663 ·
  `PRI_OPTIONAL_HIGH` 158.164 · `PRI_OPTIONAL_LOW` 147.426
- **Zincirden bir halka silinirse tüm zincir bozulur**: bütün seviyeler aynı
  anda yüklenir, titreşir, hayalet kopyalar çıkar. (Ölçüldü: tek model silindi,
  altı model birden kayboldu.)
- Vanilla'da bile kopukluk var: `parentIndex ≥ 0` olan 859.352 entity'nin
  52.614'ünde parent indeksi o dosyada yok.

### ⭐ Kendi haritanı denetlemek: ölçüt vanilla'dır

`assetdb.py lodaudit` — mutlak sayı bir şey söylemez, **vanilla oranıyla
karşılaştırma** söyler. Sunucumuzun 195 loose ymap'i (72.931 entity) vanilla'nın
3.072.951 entity'siyle karşılaştırıldığında:

| Tutarsızlık | Vanilla | Bizim |
|---|---:|---:|
| **`LOD in Parented YMAP` bitli ama `parentIndex = -1`** | **0** (%0,00) | **3.575** (%4,90) |
| `parentIndex` var ama ymap parent bildirmiyor | 3.351 (%0,11) | 1.832 (%2,51) |
| `LOD Adopt Me` bitli ama çocuğu yok | 519 (%0,02) | 0 |

**Birincisi kesin kusurdur:** Rockstar 3 milyon entity boyunca bir kez bile o
hâle düşmemiş. Bizdeki 3.575 örnek `flags=1572872`'yi bir öğreticiden kopyalayıp
zincir kurmamanın izi — `lodLevel` hepsinde `ORPHANHD`. En yoğun dosyalar:
`la_trees.ymap` (788), `CityCentral.ymap` (477), `highway.ymap` (381).

Üçüncü satır tersini gösteriyor: vanilla'nın kendisi de %0,02 oranında tutarsız,
yani **sıfır olmayan her sapma kusur değildir**. Ölçüt orandır.

### Doğrulanmış gerçek zincir

```
0. plg_01_chopped_field        HD    prologue01.ymap[4]
   lodDist=220  childLodDist=0  çocuk=0
   flags=1572872 -> LOD in Parented YMAP | Cast Static | Cast Dynamic
   parentIndex=84 -> prologue01_lod
1. plg_01_chopped_field_lod    LOD   prologue01_lod.ymap[84]
   lodDist=750  childLodDist=210  çocuk=1
   flags=1572864 -> Cast Static | Cast Dynamic
```

HD entity'nin bayrağı **birebir `1572872`** — CLAUDE.md'de yıllardır sebebi
yazılmadan taşınan sayı, gerçek vanilla verisinde ve artık çözülmüş hâlde.
- Entity `General` alanları: `Position` `Rotation` `Archetype(+hash)` `GUID`
  `Flags` `ScaleXY` `ScaleZ` `LodDist` `ChildLodDist` `LodLevel`
  (`LODTYPES_DEPTH_HD` …) `PriorityLevel` (`PRI_REQUIRED` …) `AOMultiplier`
  `ArtificialAO` `TintValue`.
- Orphan LOD'lu entity'yi görmek için CodeWalker `Max LOD` = **`ORPHANHD`**.

---

## 10. Animasyon — ölçülmüş iki zorunluluk

### Bake şart
Aynı model, aynı keyframe'ler, biri bake edilmiş biri edilmemiş: **bake
edilmeyen oyunda dönerken ölçekleniyor.** CodeWalker'da ikisi de doğru görünür —
kusur yalnız oyunda çıkar. Reçete: `Pose → Animation → Bake Action` (seçili
kemikler) → **scale kanallarını sil** → **root/tag 0 kemiğinin tüm
keyframe'lerini sil**.

### BB min/max kutusu
ytyp export'undan **önce** animasyonun tüm hacmini kapsayan geçici bir kutu
eklenir, export edilir, kutu silinir. Kutu yoksa arketipin bounding box'ı
yalnız model kadar olur → obje hareket ederken kutunun dışına taşar,
**titrer ve kaybolur**.

### Kemik özellikleri (Bone Properties → Sollumz)
```
Tag    56606                    ← ELLE YAZILABİLİR
Flags  RotX RotY RotZ
       TransX TransY TransZ
       ScaleX ScaleY ScaleZ     ← 9 ayrı eksen bayrağı
☑ Fragment Physics              ← kemik başına
```
⚠ CLAUDE.md §9'daki "Sollumz'un otomatik tag formülü vanilla tag'leri üretmez
(`SKEL_Head` → 21030, gerçek 31086)" sorununun çözümü burada: **hesaplanan
tag'i kabul etmek zorunda değiliz**, alan doğrudan düzenlenebilir.

---

## 11. Nametables — hash → isim

Blender `Preferences → Sollumz → Name Tables → +` ile bir klasör eklenir,
Blender yeniden başlatılır; içe aktarılan modellerde `hash_...` yerine gerçek
adlar görünür. Tablolar Sollumz Discord `#resources` kanalında (Oohk),
`nametables.rpf` (~13,6 MB) olarak dağıtılıyor; RPF Explorer'a atılıp içindeki
`.nametable` dosyaları klasöre çıkarılır.

Faydası kozmetik değil: nametable olmadan bir ymap'te iki entity `hash_60F...`
diye gelir ve hangisinin `arch_lod`, hangisinin `lod_canopy` olduğu ancak
CodeWalker'ın hash hesaplayıcısıyla tek tek denenerek bulunur.
