# LOD zinciri — uzakta titriyor / kayboluyor / hayalet kopya

**Ne zaman okunur:** prop uzakta kaybolup geri geliyor, çift görünüyor, `lodDist` seçimi, kendi ymap'inde LOD katmanı, `lodaudit` çıktısı.
**When to read:** it flickers or disappears at distance; a ghost copy remains; building the LOD chain and its parenting.
**Kaynak:** `govde/bayraklar.md` §9 (3.07M entity) · `notlar/08` §8 (Stumpy Mason, video) · **Ölçüm:** 3.145.882 ymap entity, `rpfPath` ile; video adımları [video]
**Önce:** `dallar/map/_dal.md` · gövde › `govde/bayraklar.md`, `govde/arac-tuzaklari.md`

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" lod [--size <m>]     # vanilla lodDist referansı
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" lodchain <ad>      # gerçek zincir
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" lodaudit           # kendi ymap'lerin vs vanilla
```

## LOD zinciri — 3.07M vanilla entity üzerinde ÖLÇÜLDÜ

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



---

## İki mekanizma — gömülü LOD ve ymap parenting [video]

### A) Gömülü (orphan) LOD — tek drawable içinde
- Dört sürüm üret: high / medium / low / verylow.
  Poligon azalt **ve dokuları ikişer kat küçült**: `512 → 256 → 128 → 64 → 32`.
- Sollumz drawable hiyerarşisinde **high/medium/low/verylow mesafeleri**
  (örnekte **50 / 100 / 150**, sonuncusu olduğu gibi).
- Her mesh'i kendi yuvasına bağla: drawable'ın **data (küçük üçgen)** sekmesinden
  medium/low/verylow mesh'lerini seç.
- ytyp → autocreate.
- ⭐ ymap entity'de **`LODTYPES_DEPTH_ORPHANHD`** —
  > *"bunun için en önemli tek şey bu."*
- Oyunda: 50'de medium, 150'de very low, sonra **ymap sınırları** devreye girip
  obje kayboluyor.

### B) YMAP parenting — çok katmanlı zincir
Dört ayrı ymap: `test` (HD) → `test_lod` → `test_slod` → `test_slod3`

- **HD entity'nin bayrağı `1572872`** =
  *"LOD in parent map + cast static + cast dynamic shadows"*
  ⭐ **Atlas §4'teki çözümün birebir aynısı** — bağımsız doğrulama.
  > Atlas §4 bu bayrağın **MLO içinde** kullanılırsa objeyi sessizce düşürdüğünü
  > söylüyor; sebebi de burada görünüyor: bayrak *"LOD'um ÜST haritada"* diyor,
  > **üst harita varsa doğru**, MLO'da yoksa entity düşüyor. İki bilgi çelişmiyor,
  > birbirini tamamlıyor.
- **Parent Index = bir sonraki ymap'teki entity'nin indeksi, 0 TABANLI.**
  `-1` = zincirin sonu. Yazar bunu ayrıca vurguluyor: *"sıfırdan başlıyor,
  bu çok önemli."*
- LOD entity'sinde **"LOD adopt me"** bayrağı → bir üst girdi tarafından
  sahiplenilir.
- Mesafe devri: **her seviyenin `Child LOD Distance`'ı bir öncekinin `lodDist`'i**
  olur. Örnek: HD lodDist 50 → LOD child 50 / lodDist 100 → SLOD2 child 100 …
  SLOD3 child 200 / lodDist 250.
- `Num Children` doğru sayılmalı.
- ⚠️ **CodeWalker projesini kapatıp yeniden aç** — LOD geçişi ancak o zaman
  görünüyor.
- Mesafeleri sonradan rafine et; ölçüt **vanilla'nın ne yaptığı**.

---
