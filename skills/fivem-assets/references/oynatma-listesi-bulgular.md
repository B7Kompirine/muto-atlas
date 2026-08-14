# Stumpy Mason oynatma listesi — tam bulgu dökümü

**Kaynak:** `PLa_ue93jrQjMhbeY3nFqr2PkGMNII11WD` (25 video, 6 sa 41 dk)
+ "create basic decal" (Lamont Cranston, 61 sn, listede değil)

**Yöntem:** 25 videonun **altyazısının tamamı** okundu; **26 videonun hepsinden
kare çıkarıldı ve izlendi** (bilgi yoğun panellerde 1600px'e kadar
büyütülerek). Decal videosunun altyazısı yoktu — yalnız kareden okundu.

**Bu belge üç soruyu ayırır:** ne *geliştirdik* (koda girdi), ne *keşfettik*
(bilgi olarak doğru ama henüz koda girmedi), ne *işe yaramaz* (bilerek dışarıda
bırakıldı). Doğrulama durumu her maddede yazılı.

---

## 1. NE GELİŞTİRDİK — koda/veriye girmiş olanlar

### 1.1 Yeni veri katmanları

| İndeks | Üretici | Boyut | Doğrulama |
|---|---|---|---|
| `ytyp_extensions.tsv.gz` | `build_extensions.ps1` | 64.209 extension | 0 hata; `prop_pallet_01a` videodaki XML'le birebir |
| `ymap_lod.tsv.gz` | `build_ymap_lod.ps1` | 3.145.882 entity | 0 hata; zincir uçtan uca yürütüldü |
| `procedural.tsv` | `build_procedural.ps1` | 255 ID | videodan okunan 2 değerle sınandı, ikisi de tuttu |
| `collision_materials.tsv` | (Sollumz kaynağı) | 185 materyal | `ANIMAL_DEFAULT=171` bizim eski ölçümümüzle aynı |
| `shaders.tsv` | `build_shaders.py` | 249 shader | ⚠ **tek kaynak, çapraz doğrulanmadı** |

### 1.2 Yeni sorgular (`assetdb.py`)

`ptfx` · `ext` · `lod` · `lodchain` · `lodaudit` · `proc` · `mat` · `shader` ·
`flags`

### 1.3 Düzeltilen yanlışlar

- **`SPECIAL` tablosu** — 21 değerin resmi motor adları eklendi; `9` ve `32`
  bizde hiç yoktu. Eski etiketler (gözlemden) korundu, çünkü ikisi farklı
  katman: motor adı *neden*, gözlem *neyin* öyle etiketlendiğini söylüyor.
- **`.ycd` / `NATIVE` notu 7 dosyada** — "Sollumz NATIVE istense de XML yazar"
  genelleştirmesi yanlıştı. Doğrusu: `.ycd` **format sisteminin dışında**;
  diğer 8 uzantıda `NATIVE` gerçekten binary yazar (`pymateria` kuruluysa).
- **CLAUDE.md §4** — `1572872` / `18350080` artık bit açılımıyla.
- **CLAUDE.md §9** — kemik `Tag` alanının **elle yazılabildiği** eklendi;
  "Sollumz'un tag formülü yanlış" sorununun çözümü buymuş.
- **Kütüphane davranışı** — `SKILL.md` + `CLAUDE.md §5` yönlendirme tabloları:
  konu geçince komut beklemeden sorgulanıyor.

### 1.4 Kendi kaynaklarımızda bulunan gerçek kusur

```
'LOD in Parented YMAP' bitli ama parentIndex = -1
   VANILLA :     0 / 3.072.951   %0,00
   BIZIM   : 3.575 /    72.931   %4,90
```
Rockstar 3M entity'de bir kez bile yapmamış. `la_trees.ymap` (788),
`CityCentral.ymap` (477), `highway.ymap` (381). `assetdb.py lodaudit` yakalıyor.

---

## 2. NE KEŞFETTİK — doğru ama henüz koda girmedi

### 2.1 Sollumz `Import RAGE Assets` seçenekleri (#14, ekrandan)

Dosya tarayıcısının sağ panelinde:
- **Import Asset**: `Import To Asset Library`
- **Fragment**: `Split Mesh by Vertex Group` · `Import Window Shattermaps`
- **Drawable Dictionary**: `Import External Skeleton`
- **Ymap**: `Hide Missing Entities` · `Exclude Entities` · `Instance Entities`
  · `Exclude Box Occluders` · `Exclude Model Occluders` · `Exclude Car Generators`

`Instance Entities` kritik: ymap'i içe aktarırken entity'leri **dünya
koordinatına açar** — kumaş world-bound işi (#15) bunsuz yapılamıyor.

### 2.2 Sollumz klip paneli (#23, ekrandan)

```
Sollumz Type   Clip
Hash           sm_logo_text_test_1
Name           sm_logo_text_test_1.clip
Duration       0 s
[Apply Clip to NLA]
Linked Animations
  ▾ sm_logo_text_test_1.002
      Animation     sm_logo_text_test_1.002
      Frame Range   Start 1   End 60
  > Tags     > Properties
```
`Tags` ve `Properties` bölümleri bizim `movement-clipset-uretimi.md`'nin
konusu — arayüz karşılığı burada.

### 2.3 Bound oluşturma paneli (#12, #15, #20)

`Convert to Composite` · `Create Bound` (**`Bound Plane (for cloth only)`**
dahil) · `Create Poly Bound` · **`Create Box From Selection`** (+ parent alanı:
"If not set, the parent of the active object is used") · `Create Collision
Material` · **`Flag Presets`**

`Flag Presets` düğmesi hiçbir videoda kullanılmadı ama hazır bayrak setleri
sunuyor olmalı — **incelenmedi.**

### 2.4 ymap grass batch düğümü (#7, ekrandan)

Grass batch ymap XML'inde `<GrassInstanceBatches><Item><archetypeName>` yapısı
var. Bizim `ymap_lod.tsv.gz` yalnız `CEntityDefs`'i okuyor — **grass batch'ler
indekste yok.**

### 2.5 Doğrulanmış ama indekslenmemiş

- **`Shaders.xml` `Flags` alanı**: `IS_TERRAIN` (17), `IS_CLOTH` (6),
  `IS_PED_CLOTH` (6), `IS_TERRAIN IS_TERRAIN_MASK_ONLY` (4). Terrain/cloth
  shader'ını programatik ayırt etmeye yarar; `shaders.tsv`'ye yazıldı ama
  sorgu bunu kullanmıyor.
- ~~**CodeWalker vs Sollumz ad çelişkisi**~~ ✅ **KAPANDI — ölçüldü.**
  Bit 16 (65536) = **`Underwater`**, CodeWalker haklı, Sollumz'un
  "Unused"'ı yanlış. 3.145.882 entity'de **14 kez** kurulu ve hepsi
  `prop_dock_bouy_*` + `prop_rub_wheel_01`, liman/nehir ymap'lerinde —
  yani kullanım anlamla birebir örtüşüyor. `assetdb.py flags --entity`
  artık `Underwater` yazıyor.

---

## 3. NE İŞE YARAMAZ — bilerek dışarıda bırakılanlar

### 3.1 Prosedür anlatımları (veri değil, adım listesi)

Videoların büyük kısmı "şuraya tıkla" anlatımı. Bunlar plugin'e **veri olarak
giremez**, çünkü sorgulanacak bir şey yok:
- #10 dönen logo, #8 yürüyen küp — armature + keyframe temel anlatımı
- #14, #19 asset library kurulumu — Blender iş akışı, GTA verisi değil
- #24 prop taşıma/silme — CodeWalker `T` menüsü, üç adım
- #4 "chains" — **şaka videosu**, içerik yok (23 sn, "don't make chains")

Bunlardan çıkan tek kalıcı bilgi zaten §1'e girdi (bake zorunluluğu, BB kutusu,
ytyp bayrak setleri).

### 3.2 Tekrarlanamaz / riskli yöntemler

- **#7 grass batch hack'i**: kendi collision'ına çim boyayabilmek için base
  game RPF'ine collision enjekte ediliyor, GTA bütünlük kontrolü bozuluyor,
  sonra "verify game files" ile 211 MB indirilerek onarılıyor. **Plugin'e
  reçete olarak giremez.** Ama *neden* çalışmadığı (grass batch yalnız base
  game collision'ına boyar) bilinmesi gereken bir sınır — referansa yazıldı.
- **#13 Sketchfab retarget**: kaynağın kendi iskeletini taşıyor. Prop için
  çalışır, **ped için çalışmaz** (CLAUDE.md §10, custom iskelet yasak).
  Çelişki değil, kapsam farkı — ama tavsiye olarak alınamaz.

### 3.3 Bize özgü olmayan içerik

- #25 bayrak prop'u: vanilla `prop_flag_japan`'ı yeniden adlandırma hattı.
  Yöntem doğru ama tek bir prop'a özgü; genel bir kural çıkmıyor
  (çıkan tek şey: ymap bayrağı `1572865` = Allow full rotation + gölgeler).
- #17 LOD texture swap: LOD seviyelerinin **ayrı YTD**'lerde olduğu bilgisi
  değerli (§1'e girdi), gerisi Photoshop işi.

---

## 4. DOĞRULANMAMIŞ — açık kalanlar

### ✅ KAPANDI — `build_usage.ps1` ile ikinci kaynak üretildi

12.000 `.ydr` + 12.000 `.yft` + 12.000 `.ybn` tarandı (12 hata; gerçekten bozuk
dosyalar). Çıktı: `shader_usage.tsv`, `collision_usage.tsv`.
Denetim: `python scripts/dogrula_tablolar.py`

| Eski madde | Denetim | Sonuç |
|---|---|---|
| 1 · `shaders.tsv` tek kaynak | vanilla'da 177 farklı shader kullanılıyor; **tabloda olmayan: 0** | ✅ tablo eksiksiz |
| 2 · `collision_materials.tsv` | 151 farklı indeks kullanılmış, hepsi 0-183 aralığında; **aralık dışı: 0** | ✅ |
| 9 · `procedural.tsv` | 73 farklı `proceduralId` kullanılmış, hepsi 0-254'te; **aralık dışı: 0** | ✅ |
| 10 · decal render bucket | 5.482 decal kullanımının **%92,3'ü bucket 2**, Opaque yalnız **1** | ✅ ölçüldü |

Materyal tablosu ayrıca **anlamsal** olarak da tutuyor — en çok kullanılanlar
`DEFAULT` (98.222) · `CONCRETE` (48.210) · `SAND_UNDERWATER` (32.127) ·
`GRASS_SHORT` (30.736) · `ROCK` (29.422) · `DIRT_TRACK` (28.310) ·
`TREE_BARK` (20.407). Bir harita için beklenecek dağılım tam olarak bu.

**Genel render bucket dağılımı** (75k kullanım): Opaque %77,73 · Alpha %11,10
· Decal %6,78 · Cutout %4,27 · NoSplash %0,06 · NoWater %0,03 · Water %0,02
· DisplacementAlpha %0,01.

### ✅ Ölçümle kapanan üç madde daha

| Eski madde | Ölçüm | Sonuç |
|---|---|---|
| 6 · bit **65536** | 3.145.882 entity'de **14 kez** kurulu; hepsi `prop_dock_bouy_1/2/3` + `prop_rub_wheel_01`, liman/nehir ymap'lerinde | **CodeWalker haklı: "Underwater".** Sollumz'un "Unused"'ı yanlış |
| 4 · `specialAttribute` **17** | İki örnek de **`v_traffic_lights.ytyp`** içinde | **Sollumz haklı: demiryolu geçidi lambası.** Bizim "yol korkuluğu" etiketimiz yanlıştı |
| 3 · `specialAttribute` **6** | 630 arketipin yalnız **%15,7**'sinde `slod` geçiyor; kalanı `cs1_`/`ch1_` kırsal harita parçası, `lodDist` medyanı 80 | Çelişki **duruyor** ama benim "hepsi slod" iddiam **çürüdü** — 6 satırlık örnekten genellemeydi |

### ⚠ Kendi belgemizde bulunan hata

Bu tur sırasında §3'teki **ENTITY bayrak tablosunun 128'den sonrasının bir
satır kaydığı** ortaya çıktı — elle kopyalarken yapılmış. `assetdb.py`'daki
kod hep doğruydu (`1572872` baştan beri doğru çözülüyordu), hatalı olan
**belgeydi**. Tablo artık koddan üretiliyor.

Ders: aynı bilgiyi iki yerde elle tutma. Belge koddan üretilmeli, tersi değil.

### 7 ve 8 — kod yolu doğrulandı (bayt düzeyi hâlâ test edilmedi)

`NativeProvider.save_asset` gerçekten **yazıyor**, sadece okumuyor:

```python
pm.Bound.export_rsc(...)              # .ybn
pm.ClothDictionary.export_rsc(...)    # .yld
pm.gen8.MapTypes.export_rsc(...)      # .ytyp
pm.MapData.export_rsc(...)            # .ymap
```

`export_rsc` = **export RESOURCE**, yani binary. Ayrıca `provider_gen8.py` ve
`provider_gen9.py` **ayrı** `save_drawable_to_native_g8/_g9`,
`save_fragment_to_native_g8/_g9`, `save_txd_to_native_g8/_g9` fonksiyonları
taşıyor — Gen8/Gen9 ayrımı gerçek, kozmetik değil.

`pymateria 0.2.0` bu makinede kurulu. Yani `NATIVE` seçmek gerçekten binary
üretir. **Kalan tek belirsizlik:** çıkan baytların geçerli `RSC7` olup olmadığı
— bunun için gerçek bir export gerekir, yapılmadı.

### ✅ 7, 8, 11 — CANLI BLENDER TESTİYLE KAPANDI

Blender 5.2.0 LTS + Sollumz 2.8.0, gerçek export yapıldı (test objesi sonradan
silindi, kullanıcının `.blend` dosyası kaydedilmedi).

**Sağlayıcılar:** `is_provider_available` dördü de `True` —
`NATIVE/GEN8`, `NATIVE/GEN9`, `CWXML/GEN8`, `CWXML/GEN9`.

**7 · `NATIVE` gerçekten binary yazıyor — ilk 4 bayt okundu:**

| Ayar | Çıktı | Boyut | İlk 4 bayt |
|---|---|---:|---|
| `NATIVE` + `GEN8` | `muto_export_testi.ydr` | 451 | `52534337` = **`RSC7`** |
| `CWXML` + `GEN8` | `muto_export_testi.ydr.xml` | 2.699 | `3c3f786d` = `<?xm` |

**8 · Gen8+Gen9 birlikte seçilince alt klasör — doğrulandı:**

```
gen8/muto_export_testi.ydr   451 bayt  RSC7
gen9/muto_export_testi.ydr   558 bayt  RSC7
```

İki sürüm **farklı boyutta** (451 vs 558) — yani Gen9 kozmetik bir etiket
değil, gerçekten başka bir dosya. Tek sürüm seçiliyse alt klasör oluşmuyor,
dosya doğrudan hedefe yazılıyor.

**İki format birden** (`NATIVE`+`CWXML`, tek sürüm) → aynı klasöre **ikisi de**:
`muto_export_testi.ydr` (RSC7) + `muto_export_testi.ydr.xml`.

→ Böylece `.ycd` iddiası da dolaylı olarak pekişti: aynı ayarla `.ydr` binary
çıkarken `.ycd`'nin XML kalması, `.ycd`'nin bu sistemin dışında olmasındandır.

**11 · `Flag Presets` — açıldı, içeriği çıkarıldı**

Sollumz **27 hazır preset JSON'u** taşıyor (`*/gta5/presets/`): bayraklar,
collision materyalleri, arketip, ve her extension tipi için ayrı dosya.
`ybn/gta5/presets/flag_presets.json` **7 composite ön ayarı** içeriyor:

| Ön ayar | Type | Include |
|---|---:|---:|
| **General (Default)** | 5 | 17 |
| General 2 | 4 | 17 |
| Water surface | 1 | 5 |
| Leaves - Bush | 1 | 16 |
| Stair plane | 1 | 6 |
| Stair mesh | 6 | 17 |
| Deep surface | 2 | 3 |

`General (Default)` = sıradan harita objesi için doğru set:
type `map_weapon + map_dynamic + map_animal + map_cover + map_vehicle`,
include 17 bayrak. Tabloya alındı: `data/collision_flag_presets.tsv`,
`assetdb.py mat` çıktısında görünüyor.

⚠ Diğer 26 preset dosyası (partikül, grass batch, arketip, MLO oda/portal,
ışık, shader…) **henüz okunmadı** — hazır bir bilgi kaynağı olarak duruyor.

### Hâlâ açık

| # | Konu | Durum |
|---|---|---|
| 5 | LOD zinciri **%6,1** | İki hipotez denendi, **ikisi de çürüdü** — aşağıya bak |

### 5 · LOD %6,1 — iki hipotez elendi

1. **ymap adı çakışması** → `rpfPath` eklendi. Gerçek bir kusurdu (53k sahte
   kopukluk üretiyordu) ama kalan %6,1'i açıklamadı.
2. **ymap iç adı ≠ dosya adı** → `mapName` sütunu eklendi. Ölçüldü: 3000
   ymap'in **177'sinde (%5,9)** gerçekten farklı (`dt1_02_grass_0.ymap` →
   `dt1_02`). Doğru olan iç adla eşleştirmek, ama sonuç **hiç değişmedi**:
   %93,5 çözüldü / %6,1 kopuk. Uyumsuz ymap'ler çim ymap'leriymiş, zincire
   katılmıyorlar.

Kalan somut vaka: `dt1_rd1.ymap`'in **643 entity'si** `parentIndex` 0..77
taşıyor, ama parent'ı `dt1_lod`'un **dört kopyasında da 42 entity** var
(`CEntityDefs` = `AllEntities` = 42, MLO instance yok). 42-77 arası indeksler
hiçbir yerde yok.

Kalan hipotezler (**sınanmadı**): `parentIndex` aynı LOD seviyesindeki birden
çok ymap'in birleşik listesine bakıyor olabilir; ya da `.imap`/grup dosyaları
devrede olabilir.

---

## 4b. ⛔ CodeWalker.Core tuzağı — `ResourcePointerArray64<T>` üzerinde `foreach` KULLANMA

`ShaderGroup.Shaders`, `BoundComposite.Children` gibi alanların tipi
`ResourcePointerArray64<T>`. Bu tip `IEnumerable` **uyguluyor görünür**
(PowerShell'de `-is [IEnumerable]` → `True`, C# derleyicisi `foreach`'e
izin verir) ama `GetEnumerator()` **`NotImplementedException` fırlatır.**

Sonuç sessiz felakettir: `try/catch` içindeki her dosya hataya düşer,
derleyici uyarmaz, çıktı boş olur. Ölçüldü: `build_usage.ps1`'in ilk
sürümünde **86.690 `.ydr`'nin tamamı** böyle kayboldu ve tek belirti
`ydr tarandi: 0` satırıydı.

**Doğrusu `.data_items` dizisidir:**
```csharp
var arr = sg.Shaders.data_items;          // foreach DEGIL
for (int i = 0; i < arr.Length; i++) { ... }
```

İki yan ders:
- **`catch { }` ile hatayı yutma.** İlk sürümde hata mesajı yoktu; eklenince
  sebep tek denemede çıktı. Toplu tarayıcılarda **ilk hatayı mutlaka yazdır.**
- **Limit sayacını BAŞARILI değil DENENEN üzerinden say.** `if (nD >= limit)`
  yazmıştım; hepsi hata verince `nD` hiç artmadı, `-Limit 4000` devreye
  girmedi ve betik 86 bin dosyayı taramaya başladı.

Ayrıca: `File.WriteAllText(..., Encoding.UTF8)` **BOM yazar**; okuyan taraf
ilk sütun adını `﻿shader` görür ve `KeyError` alır. `new UTF8Encoding(false)`
kullan.

## 4c. Sollumz export tuzağı — gömülü doku sessizce atlanır

`.ydr` **476 bayt** çıktıysa doku gömülmemiştir (gömülüyken 18.975 bayt).
Doğru operatör **`bpy.ops.sollumz.setallembedded()`** ve **nesne seçili
olmalı**. Yanlış operatör adını `try/except` içine koyduğumda hata sessizce
yutuldu, export "Successfully exported" dedi ve **dosya üretildi** — yalnız
16 kat küçük. Boyut kontrolü tek güvenilir belirti.

İlgili: `bpy.ops.sollumz.deleteytyp()` **3B viewport bağlamı ister**
(`context.space_data.show_gizmo`); MCP üzerinden çağrılınca `AttributeError`
verir. Koleksiyondan doğrudan `sc.ytyps.remove(i)` aynı işi yapar.

## 5. Yöntem notu — bu turda öğrenilen iki şey

**Videodan öğrenmek, kaynaktan doğrulamaya göre ikincildir.** Enum'ların,
bayrakların ve tabloların tamamı Sollumz'un kendi Python kaynağında ve
CodeWalker DLL'inde yazılı. 6,7 saatlik video izleyerek çıkarılan bilginin
büyük kısmı oradan dakikalar içinde ve **daha eksiksiz** alındı (örnek: video
11 extension tipi gösteriyordu, kaynakta 14 tane var).

**Videonun asıl değeri başka:** *hangi soruyu sormak gerektiğini* öğretiyor.
`Procedural ID`'nin varlığını, decal'ın ayrı bir render bucket istediğini,
LOD zincirinin ymap dosyalarını aştığını video olmadan aramazdık.

**Kendi ölçümüne de şüpheyle bak.** Bu turda bir kez "53.102 kopuk LOD zinciri"
raporladım; sebep vanilla değil, ymap adlarının 4751'inin birden çok RPF'te
olması ve indeksimin kopyaları üst üste bindirmesiydi. `rpfPath` eklenince
gerçek sayı ortaya çıktı. **Şüphelenmeseydim yanlış sayı belgeye girecekti.**

**Sonraki tur (2026-08-12) bunu üçüncü kez doğruladı.** Video yolu bir kez
daha denendi: sprite sheet mekanizması için "GTAV Particle Effects In Depth
Tutorial" izlendi — 38 dakika, konuya **hiç girmiyor**, transkriptte "sheet"
kelimesi bir kez bile geçmiyor. Cevap yine ölçümden çıktı: vanilla dosyayla
bizimkini **nesne düzeyinde alan alan karşılaştırmak**. O tur bulunan dört
kusurun (`FxcFileHash`, blok VFT'leri, `FileVFT`, ShaderVar VFT'leri)
dördü de bu yöntemden çıktı, hiçbiri aramayla bulunmadı.

---

## 6. Bu belgenin kapsamı

Burası **oynatma listesinden ne çıktığının** kaydıdır. Sonraki turlarda
yapılan ölçümler konularına göre ayrı referanslarda:

| Konu | Dosya |
|---|---|
| `.ypt` üretimi, VFT/hash tabloları, sprite sheet, decal, collision, LOD | `ytyp-ymap-bayraklari.md` |
| Movement clipset (`.ycd`) | `movement-clipset-uretimi.md` |
| Ped rig / retarget / weight paint | `ped-retarget-weightpaint.md` · `ped-kemik-yuz-rigging.md` |
| Yetenek matrisi, güven oranları, yol haritası | `../../../YETENEK-DURUMU.md` |
