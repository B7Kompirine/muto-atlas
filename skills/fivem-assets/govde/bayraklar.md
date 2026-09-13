# Bayraklar — ytyp / ymap / collision / specialAttribute / extension

**Gövde dosyası.** Sihirli bir sayı görünce kopyalanmaz, çözülür:
`python scripts/assetdb.py flags <sayı> [--entity]`. Bit tabloları ve
`specialAttribute`'un 21 değeri burada; ölçüm 316.975 arketip + 3.145.882
entity üzerinde. Kaynak: `govde/bayraklar.md` §1-6, §8, §11
(2026-09-05'te gövdeye taşındı; §7 export formatı → `govde/arac-tuzaklari.md`
Ayrıntı B, §7c-7d partikül → Partikül dalı, §8.5b-8.6 decal → Görünüm dalı,
§9 LOD → Harita dalı, §10 animasyon → Animasyon dalı).

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

### Pratikte hangi bayrak kombinasyonu — topluluk uygulaması
Kaynak: `kaynaklar/dis-arac.md` §2. Bunlar ölçüm değil, çalıştığı görülmüş
kombinasyonlardır — ama üçü de birden fazla videoda tekrarlanıyor.

| iş | bayraklar |
|---|---|
| animasyonlu prop (klip kendiliğinden oynasın) | **`Has Anim` (512) + `Auto Start Anim` (524288)** |
| UV animasyonlu prop / silah kaplaması | **`UV anims` (1024) + `Auto Start Anim`** |
| iskelet + UV animasyonu **birlikte** | **`Has Anim` + `UV anims`** — bu durumda `Auto Start Anim` **gerekmiyor** |
| kırılabilir fragment | **`Dynamic` (131072)**; ops. `Does Not Provide AI/Player Cover` |
| prop cloth | **`Has Cloth` (33554432) + `Dynamic` + `Double-sided rendering` (65536) + `Use Ambient Scale` (536870912)** |
| bake edilmiş shadowmap düzlemi | **`Dont Cast Shadows` (8192)** |
| yansıma proxy'si | archetype flags **0**; iş entity bayraklarında (`only render in reflections` + cast static/dynamic shadow) |

### ⭐ `Time` arketipi — `TimeFlags`'i elle yazmaya gerek yok
Sollumz'da arketip **`Type` alanı `Base` yerine `Time`** seçilirse panelde
**24 saatlik onay kutusu ızgarası** (`12:00 AM–1:00 AM` … `11:00 PM–12:00 AM`)
ve **`Select from … to …`** aralık seçici açılıyor. Bu dosyadaki `TimeFlags`
sihirli sayısı (ör. `14680095` = 21:00–05:00) oradan üretiliyor.

Saate bağlı prop için tipik alanlar: `HD Texture Distance` **60**,
`Lod Distance` **60**, ymap **Content Flags `HD (1)` + `Physics (64)` = `65`**.
Doğrulama: CodeWalker → Lighting → **`Time of day`** kaydırıcısıyla saati değiştir,
prop aralık içinde görünüp dışında kaybolmalı.

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

### ⭐ 2.1 GERÇEK kullanım dağılımı — 316.975 arketip, tam sayım

Yukarıdaki bit tablosu "hangi bit ne demek"i söyler; bu tablo **vanilla'nın
gerçekten ne yazdığını**. Bayrak seçerken önce buraya bak: listede olmayan bir
kombinasyon kuruyorsan, sebebini bilerek kuruyor ol.

**224 benzersiz bayrak değeri var, ama üç tanesi %90,5'i kaplıyor.**

| değer | adet | % | kümülatif | çözümü |
|---:|---:|---:|---:|---|
| `536870912` | 137.663 | 43,4 | 43,4 | Use Ambient Scale |
| `0` | 108.104 | 34,1 | 77,5 | *(hiçbiri)* |
| `8192` | 41.210 | 13,0 | **90,5** | Dont Cast Shadows |
| `537001984` | 5.122 | 1,6 | 92,2 | Dynamic \| Ambient |
| `33685504` | 4.049 | 1,3 | 93,4 | Dynamic \| Has Cloth |
| `537002016` | 2.787 | 0,9 | 94,3 | Static \| Dynamic \| Ambient |
| `8196` | 2.486 | 0,8 | 95,1 | Draw Last \| Dont Cast Shadows |
| `549584896` | 1.723 | 0,5 | 95,6 | Dynamic \| No AI Cover \| No Player Cover \| Ambient |
| `32` | 1.287 | 0,4 | 96,0 | Static |
| `2097152` | 1.035 | 0,3 | 96,4 | Drawable Proxy Water Refl |
| `604110848` | 860 | 0,3 | 96,6 | Dynamic \| **Enable Door Physics** \| Ambient |
| `2048` | 849 | 0,3 | 96,9 | Shadow Only |
| `4` | 839 | 0,3 | 97,2 | Draw Last |
| `12582912` | 810 | 0,3 | 97,4 | No AI Cover \| No Player Cover |
| `549453824` | 593 | 0,2 | 97,6 | No AI/Player Cover \| Ambient |
| `536870944` | 550 | 0,2 | 97,8 | Static \| Ambient |
| `131072` | 425 | 0,1 | 97,9 | Dynamic |
| `1024` | 363 | 0,1 | 98,4 | UV anims |
| `536936448` | 232 | 0,1 | 98,6 | Double-sided \| Ambient *(bitki)* |
| `570556416` | 177 | 0,1 | 98,7 | Dynamic \| Has Cloth \| Ambient *(bayrak/flama)* |
| `537264128` | 170 | 0,1 | 98,8 | Dynamic \| Override Physics Bounds \| Ambient |
| `67239936` | 158 | 0,0 | 98,8 | Dynamic \| Enable Door Physics *(ambient'siz)* |
| `536871424` | 149 | 0,0 | 98,9 | **Has Anim** \| Ambient *(RayFire kökleri: `des_*_root`)* |

Okunacak dört şey:

- **`Use Ambient Scale` neredeyse serbest bir varsayılandır** (tek başına
  %43,4). Emin değilsen kurmak vanilla davranışıdır.
- **`Static` nadirdir** (tek başına %0,4). "Static + Dynamic birlikte" ise
  vanilla'da gerçekten var (`537002016`, 2.787 arketip) — çelişki değil.
- **Kapı bayrağı iki sürümlüdür**: `604110848` (860, ambient'li) ve
  `67239936` (158, ambient'siz). Beşte dördü ambient'li.
- **`536871424` = Has Anim + Ambient**, `Auto Start Anim` **yok** — ve
  taşıyıcıları `des_*_root` yani RayFire kökleri. RayFire klibini motor
  başlattığı için auto-start gerekmiyor. Kendi RayFire kökünde
  `Auto Start Anim` kurmak vanilla kalıbı **değildir**.

⚠ **ENTITY (ymap) tarafının aynı dağılımı ÖLÇÜLEMEDİ** — `entities.tsv.gz`
ve `entities.db` şemasında `flags` kolonu yok (`name,x,y,z,kind,ymap,interior`).
Aşağıdaki §3 bit tablosu ve çözülmüş sihirli sayılar geçerli, ama "vanilla en
çok hangi entity bayrağını yazıyor" sorusunun cevabı **elimizde yok**. Gerekirse
ymap dump'ına `flags` kolonu eklenmeli.

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

### `assetType` — alan değil PROPERTY (`rage__fwArchetypeDef__eAssetType`)

`ASSET_TYPE_DRAWABLE` (`.ydr`) · `ASSET_TYPE_FRAGMENT` (`.yft`, per-bone collision **yalnız** bununla) · `ASSET_TYPE_DRAWABLEDICTIONARY`
(`.ydd`, LOD ebeveynleri) · `ASSET_TYPE_ASSETLESS`. Fragment üretip `assetType` drawable bırakmak tüm emeği boşa çıkarır
(`dallar/prop/fragment.md`); RayFire kökü **drawable**dır, fragment değil (`dallar/map/yikim.md`).

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
| 30 | Clock | 11 | *"animated clock hands"*; `prop_big_clock_01` (kemik tag 0/419/418, klip YOK) |
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


> §6 partikül extension → `dallar/particle/hazir-efekt.md` (2026-09-05).

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


## 11. Nametables — hash → isim

Blender `Preferences → Sollumz → Name Tables → +` ile bir klasör eklenir,
Blender yeniden başlatılır; içe aktarılan modellerde `hash_...` yerine gerçek
adlar görünür. Tablolar Sollumz Discord `#resources` kanalında (Oohk),
`nametables.rpf` (~13,6 MB) olarak dağıtılıyor; RPF Explorer'a atılıp içindeki
`.nametable` dosyaları klasöre çıkarılır.

Faydası kozmetik değil: nametable olmadan bir ymap'te iki entity `hash_60F...`
diye gelir ve hangisinin `arch_lod`, hangisinin `lod_canopy` olduğu ancak
CodeWalker'ın hash hesaplayıcısıyla tek tek denenerek bulunur.
