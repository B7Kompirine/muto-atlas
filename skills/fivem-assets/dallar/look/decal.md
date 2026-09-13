# Decal — script (`AddDecal`), haritaya gömülü (`decal.sps`), Blender'da yüzeye projeksiyon; kaynak paketler

**Ne zaman okunur:** "duvara graffiti / yere kan / merdivene leke"; hangi sistem; decal görünmüyor/beyaz/yeşil; Void Tools; ücretsiz doku paketleri ve lisansları.
**When to read:** a runtime mark (`AddDecal`), a decal baked into the map (`decal.sps`), or projecting geometry onto a surface in Blender; "the decal looks white".
**Kaynak:** `decal.md` §0-3, §7-8, §10, beyaz/parlaklık · `govde/bayraklar.md` §8.5b-8.6 · eski `/look` · `decal-kaynak/KAYNAKLAR.md` (2026-08) · **Ölçüm:** 194 decal tipi; 4096 ışın merdivende; A oyunda çalıştı; 2.989 doku envanteri
**Önce:** `_dal.md` · gövde › `govde/arac-tuzaklari.md` §1-2

---



Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `scripts/assetdb.py`'yi içeren muto-atlas klasörü).

aşağısı

Sayıların hepsi ölçümdür. Projeksiyon aracının kendisi bu depoda değil; bu belge
o tür bir aracın sözleşmesidir, araç değişse de ölçüt burada kalır.

---

## ADIM 0 — HANGİ SİSTEM? Kod yazmadan seç

"Şuraya leke/graffiti/kan koyalım" **üç ayrı iştir** ve hiçbiri diğerinin
yerine geçmez:

| istenen | sistem |
|---|---|
| çalışma anında iz — kan, lastik, mermi deliği, sızıntı, ayak izi | `AddDecal` (script) |
| haritaya **kalıcı gömülü** — graffiti, logo, tabela, yol çizgisi | `decal.sps` shader + render bucket **2** |
| bir modelin yüzeyine **geometri yansıtma** (Blender'da üretim) | projeksiyon decal (Blender eklentisi) |

Belirsizse `AskUserQuestion` ile netleştir:
- İz **kalıcı mı** (haritanın parçası) yoksa oyun sırasında mı oluşacak?
- **Herkes aynı anda mı** görecek? → `AddDecal` istemci başınadır.
- Yüzey **düz mü**, kıvrık mı, ince boru/ızgara mı? → sonuncusunda projeksiyon
  çalışmaz, orası boyama işidir.

---

## 1. ÇALIŞMA ANINDA İZ — `AddDecal`

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" decal kan
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" decal <mermi|ayak|yanık|yağ|benzin>
```

194 tipli tablo. Tipi **tahmin etme**, tablodan seç.

## 2. HARİTAYA GÖMÜLÜ DECAL — shader tarafı

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" shader decal
```

Render bucket **2**. `decal.sps` harman katsayısı olarak **`Color 1`'in
alfasını** okur — vertex rengi yanlışsa decal ya hiç görünmez ya da yarı
saydam kalır.

## 3. YÜZEYE GEOMETRİ YANSITMA — üç yöntem, üç sert sınır

| yöntem | ne zaman | sınırı (ölçüldü) |
|---|---|---|
| ışın ızgarası | düz, ışına dik yüzey | **ışına paralel yüzeye asla vuramaz** — merdivende 4096 ışının 2732'si, iç köşede 1344'ü boşa gitti |
| kutu (triplanar) | sarma gereken yüzey | silindirde 39 normal bandı verir (ışın 2) ama desen **köşede yeniden başlar** |
| tek eksenli kırpma | tek yöne bakan düz yüzey | ekseni **her yüz için `max()` ile seçme** — yüzey normalleri eksenle hizalı değilse sonuç boş çıkar |

⛔ **`bmesh.ops.bisect_plane` açık geometride kırpmaz, YÜZ SİLER** — altı
çağrı boyunca yüz sayısı 637'de sabit kalırken alan 3.553 → 0.941 m² düştü.
Boolean INTERSECT de güvenilmez (aynı duvarda biri hiç kırpmadı).
**Doğrusu Sutherland–Hodgman**: çözücüsü yok, başarısızlık modu yok.

İnce boru / ızgara / karmaşık kıvrım → **hiçbiri çalışmaz**. Orada yol
yüzey kopyası + elle alfa boyamadır (Surface Painter).

---

## DECAL GÖRÜNMÜYORSA — sırayla, hepsi sessiz

1. **UV katmanının ADI** materyalinkiyle aynı mı — `"UVMap 0"`.
2. Hedefin **eski UV katmanı** silindi mi (geometri kopyalanırken gelir).
3. **`Color 1` alfası 1.0 mı** — kopyalanan geometri hedefinkini miras alır,
   ölçülen vakada 0.498 çıktı ve decal yarı saydam kaldı.
4. **Alfa haritasında satır 0 görüntünün ALTIDIR** — ters okunursa maske
   baş aşağı uygulanır.
5. Alfa elemesi fazla agresif mi — tamamen şeffaf olmayan pikseller de
   eleniyorsa desen delinir.

## BLENDER API TUZAKLARI — bu işte yakalananlar

- ⛔ **`object.dimensions` DÖNÜŞÜ İÇERMEZ** (yerel bbox × ölçek). Döndürmek
  onu değiştirmez → "en uzun ekseni yatır" mantığı sessizce hiçbir şey yapmaz.
  Dünya bbox'ı kullan.
- ⛔ **Gizli objede `select_set()` sessizce çalışmaz** — export
  "successfully" der, dosya **0 bayt** çıkar (yedi objeden beşi böyle yazıldı).
- `scene.ray_cast` **viewport'u** kullanır; bakış ışını gerçek göz konumundan
  atılır ve tam dik yüzün dot'u **0.000**'dır.
- Edit Mode'a girince **önceki seçim geri gelir**.

## SONUCU SUNARKEN

- ⛔ **"Obje oluştu, sayılar makul" ÇALIŞIYOR DEMEK DEĞİLDİR.** Bu alandaki
  sessiz hataların hepsi bu kalıptaydı: yüz sayısı yüzlerce, alan makul,
  hata yok, **ekranda hiçbir şey yok.**
- ⛔ **Ekran görüntüsü ölçüm değildir.** Bir şeyin bozuk olduğunu söylemeden
  önce **oku** — pikseli, dosyayı, geri okumayı.
- **Tek sentetik noktada çalışması yeterli değildir** — düzeltmeyi
  kullanıcının gerçek geometrisinde dene, sonra "oldu" de.


---

## DECAL — üç ayrı sistem, karıştırma (`/look`)

"Şuraya kan/graffiti/leke/logo koyalım" üç ayrı işten biridir ve hiçbiri
diğerinin yerine geçmez:

| istenen | yol |
|---|---|
| çalışma anında iz (kan, lastik, mermi, sızıntı) | `AddDecal` → `assetdb.py decal <tür>` (194 tipli tablo) |
| haritaya **kalıcı gömülü** (graffiti, logo, tabela) | `decal.sps` shader + render bucket **2** → `assetdb.py shader decal` |
| Blender'da yüzeye **geometri yansıtma** | aşağısı |

Yansıtmanın üç yöntemi ölçüldü, üçünün de sert sınırı var:

- **Işın ızgarası ışına paralel yüzeye ASLA vuramaz** — merdivende 4096
  ışının 2732'si, odanın iç köşesinde 1344'ü boşa gitti.
- **Kutu yöntemi** sarar (silindirde 39 normal bandı, ışında 2) ama desen
  köşede yeniden başlar. İnce boru/ızgarada **hiçbiri çalışmaz** — orası
  boyama işidir (Surface Painter).

Decal görünmüyorsa **sırayla** şuna bak (hepsi sessiz):
UV katmanının adı materyalinkiyle aynı mı (`"UVMap 0"`) · hedefin eski UV
katmanı silindi mi · `Color 1` alfası 1.0 mı (kopyalanan geometri hedefinkini
getirir, ölçülen vakada 0.498) · alfa haritasında **satır 0 görüntünün ALTIDIR**.

⛔ **`object.dimensions` DÖNÜŞÜ İÇERMEZ** (yerel bbox × ölçek) — "en uzun
ekseni yatır" mantığını bununla kurmak sessizce hiçbir şey yapmaz.
⛔ **Gizli objede `select_set()` sessizce çalışmaz**: export "successfully"
der, dosya **0 bayt** çıkar (yedi objeden beşi böyle yazıldı).

Blender aracı bu depoda değil. Bu belge o tür bir aracın ölçülmüş
sözleşmesidir; araç değişirse belge ölçüt olarak kalır.


---

## Decal — iki ayrı sistem (ytyp-ymap ölçümü)

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


---

## 0. BU OTURUMUN EN PAHALI DERSİ

Bir decal aracını **altı tur** boyunca "düzelttim" diye teslim ettim, altısında
da kullanıcının elinde çalışmadı. Sebep tek bir hata değildi; **her turda
başka bir sessiz hata** vardı ve ben bir öncekini düzeltince ortaya çıkanı
görmeden "hazır" dedim.

⛔ **KURAL: bir düzeltmeyi teslim etmeden önce kullanıcının GERÇEK durumunda
test et.** Tek bir sentetik noktada çalışması yeterli değil. Bu oturumda
"düz duvarda çalıştı" deyip teslim ettim, kullanıcı silindirde/merdivende
denedi ve kırıldı — üst üste.

⛔ **"Obje oluştu, sayılar makul" ÇALIŞIYOR DEMEK DEĞİLDİR.** Bu oturumdaki
sessiz hataların hepsi bu kalıptaydı: yüz sayısı yüzlerce, alan makul,
hata yok, **ekranda hiçbir şey yok.**

---

## 1. PROJEKSİYON DECAL — ÜÇ YÖNTEM, ÜÇ SERT SINIR

Bir yüzeye decal koymanın üç yolu var. Hiçbiri diğerinin yerine geçmez.

| Yöntem | Nasıl | Sert sınırı |
|---|---|---|
| **Işın izgarası** | Düzgün ızgara kurup yüzeye ışın atar | **Işına paralel yüzeye asla vuramaz** |
| **Geometri kopyala** | Hedefin üçgenlerini kopyalar | UV tek eksenden gelir → dik yüzde doku **esner** |
| **Kutu (triplanar)** | Kopyalar ama UV'yi yüzün kendi eksenine verir | Desen köşede **yeniden başlar** (dikiş) |

### Işın yönteminin sınırı ölçüldü

Odanın iç köşesinde 64×64 ızgara: **4096 hücrenin 1344'ü hiçbir yüzey
bulamadı.** Merdivende **4096'nın 2732'si**. Sebep geometrik: merdiven
rungları ~2 cm boru, aralarında hava; ışınlar teğet geçiyor.
**Hiçbir açı/eşik ayarı bunu çözmez.**

Silindirde ölçüm: ışın yöntemi 288 yüz / **2 farklı normal bandı** (düz
kalıyor), kutu yöntemi 89 yüz / **39 normal bandı** (sarıyor), alan 3.5 katı.

### Karar tablosu

- Düz/geniş yüzey (duvar, kapak, masa üstü) → **ışın** (sürekli, ucuz)
- Silindir, köşe, dönüş yüzeyi → **kutu**
- İnce boru/ızgara (merdiven, cam kayıtları) → **hiçbiri**; Surface Painter
  ya da dokuya bake

---

## 2. DECAL ARACINDA BULUNAN SESSİZ HATALAR

Hepsi ölçümle bulundu, hiçbiri hata mesajı üretmedi.

### 2a. UV katmanının ADI materyalle eşleşmeli
GTA/Sollumz materyali **`"UVMap 0"`** arar. `"UVMap"` yazarsan eşleşme
kurulmaz, UV `(0,0)`'a düşer, atlasın saydam köşesi örneklenir.
**Ölçüm:** 505 yüzlü, doğru konumlu, %97'si dolu alfaya denk gelen decal
tek başına render edildiğinde **tamamen boş** çıktı.

### 2b. Geometri kopyalarken hedefin UV'si de gelir
`.new()` ile ikinci katman açılınca materyal **hâlâ birinciyi** — yani
duvarın fayans UV'sini — okur. **Ölçüm:** UV aralığı `u 0.078..4.628`,
`v -1.750..18.440`; atlas gözü ise `0.75..1.00 / 0.50..0.75`. Doku
defalarca tekrar ediyordu → "her kareye parça parça yerleştiriyor".
→ Yeni katmandan **önce mevcut UV katmanlarını sil.**

### 2c. Vertex rengi de hedeften miras alınır
Materyal alfayı `doku_alfası × Color1_alfası` diye çarpıyor. Kopyalanan
geometri hedefin `Color 1`'ini getirir. **Ölçüm:** `v_2_bds_over_shadow`
üzerine düşen decal'in Color1 alfası **0.498** → decal yarı saydam.
→ `Color 1` / `Color 2`'yi **her zaman** (1,1,1,1) yaz; "yoksa oluştur" yetmez.

### 2d. Alfa haritasında satır 0 görüntünün ALTIDIR
`bpy.types.Image.pixels` alttan üste dizilir: `v=0 → satır 0`.
`1-v` yazmak elemeyi dikeyde ters çevirir → **dokunun boş olduğu hücrelerde
üçgen üretilir, dolu olanlar atılır.** Düzeltmeden sonra üretilen hücrelerin
**%97'sinde alfa > 0.5** (önce %1).

### 2e. "Cursor çevresindeki baskın normal" YANLIŞ ÖLÇÜTTÜR
Masada cursor üstteyken 0.8 m kürenin içinde tablanın **alt** yüzeyleri daha
geniş alan kapladığı için normal `(0,0,-1)` seçildi; decal **masanın altına**
yapıştı (decal z −8.86..−8.71, masa üstü −8.67). Kullanıcı hiçbir şey görmedi.
→ Doğru ölçüt **bakış**: kameradan cursor'a ışın, ilk çarpılan yüzün normali.
Aynı noktada eski `(0,0,-1)`, yeni `(0.03,0.01,1.0)`.

### 2f. Bakış ışını GERÇEK göz konumundan atılır
Cursor'un 30 m gerisinden başlatmak kapalı mekânda binanın **dışında** kalır;
ışın duvarın **dış** yüzüne çarpar, normal ters döner, ızgara hiçbir yere
vurmaz → *"Yüzey bulunamadı"*. Asansörün içinde tam bu oldu.

### 2g. Tam dik yüzün dot'u 0.000'dır
Arka yüz elemesini `dot <= 0` yazmak **köşe dönüş yüzlerini** arka yüz sayıp
eler. Odanın iç köşesinde 48 hücre bu yüzden düştü, gri şerit kaldı.
→ Eşik `-0.05` gibi küçük bir negatif olmalı.

### 2h. ⛔ `bmesh.ops.bisect_plane` BU GEOMETRİDE KIRPMIYOR, YÜZ SİLİYOR
**Ölçüm (en net kanıt):** altı bisect çağrısı boyunca **yüz sayısı 637'de
sabit** kalırken alan `3.553 → 2.552 → 1.401 → 0.941 m²`'ye düştü. Yani
büyük yüzler kesilip içerideki parçası tutulmadı, **komple gitti.**
Sonuç: dolap kapakları kaldı, aralarındaki geniş panel yok oldu, decal
kapak kenarında **dümdüz kesildi**.

### 2i. Boolean INTERSECT açık/ince mesh'te GÜVENİLMEZ
Aynı duvarda dört decal: biri **hiç kırpılmadı** (3.706 m², kutu 2.56),
biri neredeyse **boş** kaldı (0.025 m²).

### 2j. ÇÖZÜM: Sutherland–Hodgman
Her üçgeni altı yarım uzaya sırayla kırp, kesişim noktalarını tam hesapla.
**Çözücüsü yok → başarısızlık modu yok.** Beş test (düz duvar ×3, silindir,
köşe): **hiçbiri kutu alanını aşmadı**, UV hepsinde atlas gözünün içinde.

### 2k. Kutu yönteminde ekseni HER YÜZ için `max()` ile seçme
Duvar 0.3 m²'lik panellerden oluşuyor ve normalleri birbirinden biraz farklı;
`max()` komşu panellerde **farklı eksen** seçiyor, her panel bağımsız UV
alıyor. **Ölçüm:** cursor çevresindeki 10 yüzün 4'ü `n`, 6'sı `u` seçti.
→ Ana eksen **decal'in kendi yönüdür**; bir yüz ancak **70°'den fazla**
sapmışsa yan eksene geçer.

### 2l. "Seçili obje" ölçütü kullanıcıyı yakar
Bir duvar tek obje değildir: dolap bankı, kabuk, süpürgelik, çerçeve,
borular **ayrı objelerdir**. **Ölçüm:** aynı kutuda yalnız `bodydrawers`
**0.656 m²**, tüm görünür objeler **6.318 m²** (10 kat).
→ Varsayılan **"görünür her şey"** olmalı.

### 2m. Ama "görünür her şey" KENDİ DEKORUNU DA KAPSAR
Filtresiz halde 2×2 m kutuda **20.5 m²** yüzey toplandı — çünkü
`my_mlo_veins`, önceki decal'ler ve collision kutuları da "görünür mesh".
Decal'in üstüne decal atmak olur. Kendi koleksiyonları elenince **3.88 m²**
(kutu 4.00) — tek tutarlı katman.

### 2n. Kutuya giren her yüz GÖRÜNÜR DEĞİLDİR (occlusion)
Dolap kapaklarının arkasında düz bir sırt paneli var; derinlik 0.40 ile ikisi
de kutuya giriyor. Kopyalama yöntemi ikisini birden alıyor, büyük düz arka
panel öne geçip decal'i **havada duran levha** gibi gösteriyor.
→ Yüz merkezinden projektöre ışın at; önünde başka yüz varsa **at**.
(Işın yönteminde bu sorun yok — o zaten ilk çarpmayı alır.)

### 2o. Kutu yönteminde alfa elemesi de olmalı
Işın yönteminde vardı, kutuda yoktu. **Ölçüm:** düz duvarda 487 yüz üretildi,
alan olarak yalnızca **%1'i** dolu dokuya denk geliyordu. Atlas gözlerinin
doluluk oranı **%6.8 – %32** arasında.

---

## 3. BLENDER API TUZAKLARI (bu oturumda yakalananlar)

### 3a. ⛔ `object.dimensions` DÖNÜŞÜ İÇERMEZ
Yerel bbox × ölçek verir. Objeyi döndürmek `dimensions`'ı **değiştirmez**.
"En uzun ekseni X'e getir" mantığını bununla kurmak sessizce hiçbir şey
yapmaz. → Dünya bbox'ı kullan: `matrix_world @ v for v in bound_box`.

### 3b. ⛔ GİZLİ OBJEDE `select_set()` SESSİZCE ÇALIŞMAZ
Export "File exported successfully" der, dosya **0 bayt** çıkar.
**Ölçüm:** 7 objeden 5'i böyle boş yazıldı. → Export öncesi `hide_set(False)`,
sonra **dosya boyutunu kontrol et**.

### 3c. `scene.ray_cast` VIEWPORT'U kullanır
Render'da görünüp viewport'ta gizli bir obje ışın testinde **atlanır**.
Macenta objeyi ararken bu yüzden yanlış objeyi buldum.

### 3d. Edit Mode'a girince ÖNCEKİ SEÇİM geri gelir
`bpy.ops.object.mode_set(mode='EDIT')` sonrası eski yüz seçimi canlanır.
Void Decal Tool bu yüzden **4089 decal** üretti. → Edit Mode'da önce
`for f in bm.faces: f.select_set(False)`.

### 3e. Blender 5.x compositor
- `scene.node_tree` ve `scene.use_nodes` **kaldırıldı** → `scene.compositing_node_group`
  (bağımsız `CompositorNodeTree` datablock, sen yaratıp sen sileceksin)
- `CompositorNodeComposite` düğümü **silindi** → yerine grubun `NodeGroupOutput`'u
  (+ ağacın arayüzüne Image soketi eklemek gerekiyor)
- Düğüm ayarları RNA'dan **giriş soketlerine** taşındı:
  `Blur.filter_type/size_x/size_y` → `Type` (menü) + `Size` (2B vektör),
  `Denoise.use_hdr` → `HDR` (bool soket)

---

## 7. SATIN ALINAN MODEL PAKETLERİ

- **`.mtl` çoğu zaman zip'e konmaz.** Dört pakette de yoktu → hiçbir OBJ'de
  materyal ataması yok, dokular elle eşleştirilir.
- **Ölçek paket İÇİNDE bile tutarsız.** Ölçüm: aynı 675-vertexlik parça bir
  gövdede **1.07 m**, başkasında **0.15 m**. Tek çarpanla ölçeklemek yanlış.
- **Bir `.obj` = bir sahne dökümü.** Tek dosyada onlarca ceset olabilir
  (biri 196 bağlı bileşen).
- **⛔ SERPİNTİ KÜMELEMEYİ ZİNCİRLER.** `model_12`'nin 608 bileşeninin
  yalnız **4'ü** gerçek parça, kalanı et kırıntısı; hepsi kümelemeye
  sokulunca kırıntılar gövdeler arasında köprü kurdu ve **608 bileşen tek
  kümeye düştü** — hiçbir şey ayrılmadı, hata da vermedi.
  → Önce yalnız büyük parçaları kümele, kırıntıları sonra en yakın kümeye ata.
- **UV'siz parça dokulanamaz.** Bir pakette 4 model UV'siz çıktı.

---

## 8. VOID TOOLS (seto3d) — ÖĞRENİLENLER

Kurulum: extension zip, `seto.*` operatör ad alanı, `Void Tools` N-panel sekmesi.
Güvenlik taraması: 155 dosya / 36.930 satır, `eval`/`exec`/`subprocess` yok;
ağ erişimi yalnız kendi GitHub sürüm kontrolü.

### Mimari ders — en değerlisi
Zor problemi **çözmek yerine ortadan kaldırmış**:
- *Decal Tool* → yüzeyin normal+tangent'ından baz kurup **tek quad**. Projeksiyon
  yok, kopyalama yok → hiç kırılmıyor (ama düz).
- *Surface Painter* → yüzeyin **kopyasını** çıkarıp alfasını **elle boyatıyor**.
  Projeksiyon problemi hiç doğmuyor → silindirde ve merdivende çalışır.
- *Edge Dirt / Wear / AO* → kenardan şerit.

### Aktarılabilir teknikler
- **`decal.sps`, `Color 1`'in ALFASINI harman katsayısı olarak okur** (Sollumz'un
  kendi node bağlantısı). Alfa boyamak = görünürlük boyamak.
- **Normal ters-transpoze matristen, tangent düz lineer kısımdan geçer.**
  Karıştırırsan üniform ölçekte fark görünmez, üniform olmayan ölçekte
  her decal sessizce yüzeyden eğilir.
- **Kendi projeksiyon UV'sini kurar, duvarınkini miras almaz** — duvarın
  unwrap'i 0-1'de üst üste binen adalardan oluşabilir, decal ada başına bir
  kez çizilir. (Bizim §2b hatamızın doğru kurulmuş hâli.)
- **Kayıpsız düzenleme:** UV'nin bozulmamış kopyası + strokelar tam güçte ayrı
  tutulur, böylece slider'lar veri kaybettirmez.
- **Export'a yalnız GTA'nın okuduğu veri gider:** `Color 1` + `UVMap 0`.

### Vertex Color Bake oda kabuğu için YANLIŞ ARAÇ
Vertex color'ın çözünürlüğü **mesh'in vertex yoğunluğudur**. Az poligonlu oda
kabuğunda AO leke leke çıkıyor. Yoğun mesh'li **prop'lar** için doğru.
Ayrıca **mesh'e YAZAN tek araçtır**; vanilla `Color 1` dolu olabilir
(ölçüm: `bsnt_shell` B kanalı 1.000) ve üzerine yazar.
⛔ `.npy` yedeği bu oturumda **işe yaramadı**; kurtarma kaynak `.ydr`'yi
yeniden içe alıp `Color 1`'i kopyalamakla oldu. → Bu araçtan önce
**`.blend`'i tarihli kopyala.**

### Shadow Map Baker
GTA iç mekânlarının kendi tekniği: ışığı dokuya bake edip `decal_dirt` decal
olarak geri koyar. Çözünürlük vertex'ten bağımsız → oda için **doğru araç**.
Ölçüm: AO 2048²/128 örnek, 2.4 sn. Oda ortalama parlaklığı
`62.98 → 59.24` (post-process çökmüşken), yamadan sonra **57.97** (%7.96).

---

## 10. DOĞRULAMA ALIŞKANLIKLARI (bu oturumda kendini kanıtlayanlar)

- **Her yazmadan sonra geri oku.** ytyp derlendikten sonra geri okunup
  `timecycleName` hash'i `joaat()` ile karşılaştırıldı — eşleşti.
- **Dağıtımdan sonra md5 karşılaştır.** "Komut hata vermedi" dağıtım kanıtı
  değildir.
- **Ekran görüntüsü ölçüm değildir** — ama tersi de doğru: **sayı da tek
  başına yeterli değil.** Bu oturumda "UV tam gözün içinde" ölçümü doğruydu
  ve decal yine görünmüyordu (katman adı yanlıştı). İkisi birden gerekli.
- **Kullanıcı "olmadı" dediğinde önce ÖLÇ, savunma yapma.** Bu oturumdaki
  her "olmadı" gerçek bir hataya karşılık geldi.

## ⛔ "Decal beyaz gözüküyor" = dokunun ALFASI yok, adı değil

Ölçüldü (`my_zem_kan.ydr`): 13 kan decal'inin **8'i** alfası her yerde
**255** olan **16×16** bir dokuya bakıyordu. Alfa yoksa kesim de yoktur →
motor quad'ın **tamamını opak çizer**. Zeminde açık renk dikdörtgenler
çıkar ve bu "decaller beyaz" diye okunur.

**Kaynak dosyalar bozuktu ve bunu hiçbir araç söylemedi.** `cd_blood_01..09_dec.dds`
başlığı `512×512 DXT5 mip=10` diyor, o boyut **349.552 bayt** veri ister,
dosyalarda **174.660–259.884** bayt var. Hiçbir geçerli (genişlik, yükseklik,
mip) üçlüsüne oturmuyor. Zinciri şöyle kırdı:

| katman | ne yaptı |
|---|---|
| Blender | başlığı okudu, `img.size` **512×512** gösterdi, `packed=True` |
| Sollumz | pikselleri çözemedi, **16×16 A8B8G8R8 yer tutucu** yazdı |
| export | **"0 uyarı"** |
| DOKU_KAPISI | **GEÇTİ** — ad çözülüyordu, sorun içerikteydi |
| CodeWalker | `GetTexture()` başlığı okur ve 512×512 döner; **`GetPixels()` patlar** |

⛔ **"Doku çözülüyor" ile "doku KULLANILABİLİR" aynı şey değildir.** İlkine
`DOKU_KAPISI`, ikincisine `ALFA_KAPISI` bakar. Adın çözülmesi içeriğin
sağlam olduğunu göstermez — §2'nin aynısı: aracın göstermemesi yok olduğu
anlamına gelmez, tersi de doğru.

**Ölçüt alfasızlık DEĞİL, "alfasız + küçük + DÜZ DEĞİL".** Vanilla'da
`mh_v_solidwhite_d`, `mh_v_solidblack_d`, `v_glass_d`, `gz_v_white256`
gerçekten 4×4 **düz dolgu** ve alfasızdır; bu normaldir, shader onları düz
renk kaynağı olarak kullanır. Sadece alfasızlığa bakan bir kapı bu dördünü
yanlışla işaretler ve her dağıtımı bloklar (ölçüldü). Bozuk olan, **pikselleri
değişen ama alfasını kaybetmiş** gerçek bir görüntüdür.

Kapı: dağıtımdan önce çalışan bir alfa denetim adımı (betiği depoda yok). Negatif
testle doğrulandı; 228 modelin 84 alfalı dokusunda yanlış alarm **0**.

**Elenen hipotezler (ölçülerek):** vertex color kanal sırası — vanilla'nın
kendisi de bayt0'ı **0** yazıyor, dört modelde bizim değerler vanilla ile
örtüştü; `v_2_shadowmap1/2/3` ve `v_2_bds_over_decal`'in DXT1 alfasızlığı —
vanilla orijinalleriyle **birebir aynı**, gerileme değil.

## ⛔ Decal parlaklığı MUTLAK değil, zemine GÖRE ölçülür

Zemin karartılmış bir haritada, normal parlaklıkta yazılmış bir decal
"beyaz leke" olarak okunur. Kusur decal'de değil, **oranda**.

**Ölçüt vanilla'dan türetilir.** Vanilla `decal_dirt` kaplaması
`mh_v_cor_flooroverlay_a` = **75**, altındaki vanilla zemin
`mh_v_floortiles02_d` = **175** → oran **0.43**.

Morg ölçümü: zemin 55–101 (ort ~78) → decal hedefi **~34**. Bulunan değer
`my_duvar_atlas_0` **109.7**, `_1` **94.8** — zeminden *parlak*. Kir
zemini koyultmalı, aydınlatmamalı. Kat sayısı ölçümden çıkar (0.311 /
0.364), alfaya **dokunulmaz** (şekil orada).

### İki ayrı kalıp, ikisi de aynı belirtiyi verir

**1. Maske dokusunu haritaya gömmek.** `fxdecal_blood_pool2` saf **gri**
(R=G=B=175): şekil alfada, RGB yalnızca maske. Vanilla'da bunu *script*
decal sistemi (`AddDecal`) kullanır ve **renklendirir**. Haritaya `decal_dirt`
ile gömülünce ham beyaz havuz çizilir. Ölçüt basit: **R=G=B ise o doku renk
değil maskedir** — gömmeden önce renklendir. Aynı modeldeki doğru kan
dokuları R≈38 G≈10 B≈10 idi; hedef oradan alındı.

**2. Alfa taşıyan atlası `decal_dirt`'e vermek.** Vanilla `decal_dirt`
dokularının **hepsi** DXT1, gri tonlamalı, alfa 255, **%0 şeffaf**
(`mh_v_cor_flooroverlay_a` · `mh_v_shadowsquare_a` · `mh_v_cor_numbers_a`).
Maske RGB'dedir, alfada değil. Bizim atlas DXT5 + %70-90 şeffaftı; şekil
yine çıkıyor ama RGB doğrudan çizildiği için parlaklık kritik hale geliyor.

### Elenen hipotezler (hepsi ölçülerek)

| hipotez | ölçüm | sonuç |
|---|---|---|
| doku çözülmüyor | `DOKU_KAPISI`: 228 dosya, **0 eksik** | elendi |
| shader yanlış | hash/bucket/param **vanilla ile birebir** (3645727493, bucket 2) | elendi |
| vertex color kanalı yanlış sıfırlanıyor | vanilla'nın kendisi de bayt0'ı **0** yazıyor, 4 modelde örtüştü | elendi |
| shadowmap/over_decal alfası düşmüş | vanilla orijinalleriyle **birebir aynı** DXT1/alfa 255 | elendi |
| atlas beyaz | görünür piksellerde 205 üstü **0 piksel**, ortalama 51 | elendi |

⛔ **"Ortalama RGB koyu" bir kanıt değildir.** Atlasın %70'i şeffaf olduğu
için genel ortalama 43 çıkıyordu; **alfası dolu bölgenin** ortalaması
109.7 idi. Doğru soru "doku koyu mu" değil, **"çizilen yer koyu mu"**.

## Kaplama karartırken NORMAL MAP'e dokunma

Decal bucket taramasında `mh_v_cor_normaldetails01_n` **169.6** parlaklıkla
en üst sıralarda çıkar — ama `_n` bir **normal map**'tir; düz normal zaten
(128,128,255) yani parlak olmak zorundadır. Karartmak yüzey normallerini
bozar. Parlaklık listesinden körlemesine karartma: **önce dokunun ROLÜNE
bak** (`_n` normal · `_s` spec · `_h` height · `_d`/`_a` albedo/alfa).

Aynı taramada dokunulmayanlar ve sebepleri: `gz_v_white256` (4×4 düz renk
kaynağı), `mh_v_scresbolts01` (prop cıvatası, zemin değil),
`prop_ng_fruit_logo` (monitör logosu). Karartılanlar yalnız zemine binen
büyük kaplamalardı: `gz_v_co_shadowmap1/2/3` + `shadhandle`, aynı vanilla
oranıyla (`78/175 = 0.446`), **formatı koruyarak** (DXT1 kaynak DXT1 kalır).


---

## Ücretsiz decal doku kaynakları ve lisansları (2026-08-31)


Hepsi **ücretsiz ve ticari kullanıma açık**. Buradaki dosyalar **ham PNG/JPG**;
FiveM'e girmeden önce `.ytd` sözlüğüne derlenmeleri gerekir (bkz. en alt).

| Klasör | İçerik | Adet | Format | Kaynak | Lisans |
|---|---|---:|---|---|---|
| `kan/png` | kan sıçraması, damla, birikinti, sürtme | 132 | PNG **RGBA** — medyan 2764 px, max 4984 | Resource Boy — Blood Textures | RB lisansı: kişisel+ticari serbest, atıf gerekmez |
| `kir/drip_png` | akıntı / damlama / sızıntı izi | 106 | PNG **RGBA** — medyan 1493 px | Resource Boy — Drip Textures | aynı |
| `kir/grunge_jpg` | kir, yıpranma, derin çatlak | 250 | **JPG, alfa YOK** — medyan 4000 px | Resource Boy — Grunge Textures | aynı |
| `hasar/rust_jpg` | pas, korozyon, metal yıpranma | 50 | **JPG, alfa YOK** — medyan 6425 px | Resource Boy — Rust Textures | aynı |
| `kirik/cam_jpg` | kırık cam / çatlamış vitrin | 251 | **JPG, alfa YOK** — medyan 5376 px | Resource Boy — Broken Glass | aynı |
| `acg-sizinti/png` | duvar sızıntısı / su-kir akıntısı | 39 asset | PNG 1K | ambientCG "Leaking" | **CC0** — tamamen serbest |

### 2. dalga — graffiti + apokaliptik (hepsi Resource Boy, aynı lisans)

| Klasör | İçerik | Adet | Alfa | Medyan kenar |
|---|---|---:|:--:|---:|
| `graffiti/sprey` | sprey boya izleri, tag'ler | 200 | ✅ | 4836 px |
| `graffiti/karalama` | karalama / el yazısı / çizik yazı | 501 | ✅ | 3889 px |
| `graffiti/firca` | fırça darbesi, boya sürtme | 100 | ✅ | 4980 px |
| `graffiti/duvar` | 8K graffiti duvar (tam kaplama) | 300 | ⛔ JPG | 7680 px |
| `apoc/orumcek_agi` | örümcek ağı — terk edilmiş mekân | 400 | 200'ü ✅ | 5001 px |
| `apoc/el_izi` | el / parmak izi (kanlı el izi için) | 115 | ✅ | 1049 px |
| `apoc/yirtik_kagit` | yırtık afiş / kâğıt | 106 | ✅ | 4779 px |
| `apoc/sicrama` | genel sıçrama | 104 | ✅ | 3934 px |
| `apoc/leke` | kahve/sıvı lekesi | 100 | ✅ | 3057 px |
| `apoc/murekkep` | mürekkep akıntısı | 100 | ✅ | 4097 px |
| `apoc/ayak_izi` | ayak izi (kanlı iz için) | 60 | ✅ | 4867 px |
| `apoc/dikenli_tel` | dikenli tel | 60 | ✅ | 7680 px |

**Genel toplam: 2989 doku — 1884'ü alfalı (decal'e hazır), 1105'i alfasız JPG.**
Sayısal envanter: `envanter.json`. Ham `.zip`'ler klasörlerde duruyor —
açıldıkları için artık gereksiz, silinince ~9 GB geri gelir.

### Bulunup alınmayanlar (elle indirmen gerekir)

- **3DTexel** — 280+ CC0 decal, graffiti dahil, alfalı. https://3dtexel.com/decals/
  Fiyat 0 € ama WooCommerce **checkout**'tan geçmek gerekiyor (form + sipariş),
  otomatik indirilemedi. En temiz lisanslı graffiti kaynağı; satılacak asset için bu.
- **Sketchfab — karlwirbelwind "[CC0] Decal – Graffiti Textures"** — Albedo + Opacity
  PNG, 2K/4K. İndirme Sketchfab hesabı ister.
- ambientCG'de graffiti/kir/çatlak **decal'i yok** (ölçüldü: `q=graffiti` → 0 sonuç;
  decal kataloğu yalnız Leaking / RoadLines / ManholeCover). `dirt` sonuçları
  tileable zemin materyali, decal değil.

### ambientCG serisi ikiye ayrılıyor (ölçüldü)

- **Leaking001–011 (15 adet):** `_Color.png` **RGB** + ayrı `_Opacity.png` →
  hazır decal, alfayı opacity dosyasından al.
- **Leaking012–019 (24 adet):** `_Color.png` **grayscale**, opacity dosyası **yok**
  → bunlar renk değil **maske**; ya çarpan (kirletme) olarak ya da doğrudan
  alfa kanalı olarak kullanılır.

## Lisans uyarısı (önemli)

**Resource Boy paketleri CC0 DEĞİL.** Lisans metni (`License.txt`, paketlerin içinde):

- ✅ İstediğin kadar kişisel ve ticari projede kullanabilirsin, atıf gerekmez.
- ⛔ **Dosyaları tek başına yeniden dağıtamaz, satamaz, alt-lisanslayamazsın** —
  "kendi başına ya da işinden ayrı bir ek olarak" dağıtmak yasak.

Pratik karşılığı: **sunucuda `.ytd` içine gömülü olarak kullanmak sorun değil**
(son ürünün parçası). Ama bu dokuları **"decal paketi" diye Tebex'te satmak ya da
ham PNG olarak paylaşmak lisansı ihlal eder.** Satılacak bir asset'e girecekse
`acg-sizinti` (CC0) tarafını kullan, ya da kendi dokunu üret.

## FiveM'e sokmadan önce

1. **Alfa şart.** Grunge / Rust / Kırık cam **JPG**'dir, alfası yoktur — decal olarak
   kullanılırsa **opak dikdörtgen** çizilir. Bunlar Photoshop'ta "screen/multiply"
   ile bindirmek için üretilmiş. Decal'e çevirmek için luminance → alpha maskesi
   üretilmeli (kırık camda parlaklık = cam çatlağı, koyu = boşluk; kir/pasta tersi).
   Kan ve akıntı PNG'leri zaten RGBA, dönüştürme gerekmez.
2. **Güç 2 çözünürlük.** 421×1402 gibi ölçüler motorda ölçeklenir; 512/1024/2048'e
   yeniden boyutlandır.
3. **DXT5** (alfalı) / DXT1 (alfasız) + mip zinciri ile `.ytd`'ye derle.
4. Arketipin `textureDictionary` alanına `.ytd` adını yaz — boş kalırsa motor
   dokuyu modelin kendi sözlüğünde arar, bulamaz ve **hata vermeden dokusuz çizer**.

## Kaynak bağlantıları

- Resource Boy — Blood: https://resourceboy.com/textures/blood-textures/
- Resource Boy — Drip: https://resourceboy.com/textures/drip-textures/
- Resource Boy — Rust: https://resourceboy.com/textures/rust-textures/
- Resource Boy — Grunge: https://resourceboy.com/textures/grunge-textures/
- Resource Boy — Broken Glass: https://resourceboy.com/textures/broken-glass-textures/
- ambientCG (CC0): https://ambientcg.com/list?type=Decal
