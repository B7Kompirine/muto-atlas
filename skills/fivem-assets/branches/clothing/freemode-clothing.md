# Freemode kıyafet ekleme / 98-kemikli ped'e giysi taşıma / ped ölçekleme

**Ne zaman okunur:** kendi giysini `mp_m/f_freemode_01`'e ekleyeceksin; freemode giysisini yerel ped'e taşıyacaksın; export sessizce bozuk çıkıyor; ped boyunu değiştireceksin; topuklu ayakkabıda boy artsın (§8).
**When to read:** adding your own garment to `mp_m/f_freemode_01`; moving a freemode garment onto a local ped; the export is silently broken; changing ped height; height increase with heels.
**Kaynak:** `notlar/03` §2, §4-7 (Sollumz Discord videoları, 2026-08) · **Ölçüm:** video; ağırlık kuralları (4 kemik / 1.0) bizim ölçümümüzle birebir
**Önce:** `branches/clothing/_branch.md` · gövde › `trunk/tool-pitfalls.md` §1

---

## 2. Ağırlık boyama — GTA'nın sert kuralları (`IbZ4xSCZt6I`)

Atlas §7'deki ölçümlerle **birebir** aynı, bağımsız kaynaktan doğrulanmış:

- **Vertex başına ağırlık toplamı tam `1.0`** olmalı.
- **Vertex başına en fazla 4 kemik.** Fazlası export'ta **sessizce kesilir**.
- Blender karşılıkları (Weight Paint → Weights):
  - **Normalize All** (all groups, *lock active* kapalı) → toplamı 1.0 yapar
  - **Limit Total = 4** (all groups) → 4 kemik kuralını uygular
  - **Smooth** (all groups, 1-2 kez) → kaba geçişleri yumuşatır

### Kemik sayısı gerçeği (atlas §8 ile aynı)
- **`mp_m/f_freemode_01` = 128 kemik**
- **Tipik yerel/hikâye ped'i = 98 kemik**
- Fark: `MH_hair_scale` + ön/arka etek roll'ları (`SM_L/R_Front/BackSkirtRoll`)
  + bir miktar yüz kemiği.

**Freemode giysisini 98 kemikli bir ped'e taşımanın iki yolu:**
1. **Ağırlık transferi (önerilen)** — giysiyi **external skeleton OLMADAN** import et
   → vertex grupları boş gelir → hedef ped'den ağırlık aktar.
   Aktarım yalnız ped'in **gerçekten sahip olduğu** kemikleri kullanır.
2. **Elle silme** — eksik kemikleri (etek roll'ları) sil, sonra **Normalize All** ile
   kalan ağırlığı yeniden dağıt (`thigh_roll` 1.0'a çıkar, geçiş sert olur, düzelt).

### Ağırlık transferi yordamı
1. Hedef ped'in **upper + lower** mesh'lerini çoğalt → `Ctrl+J` ile birleştir.
2. Edit Mode → **Merge by Distance** (birleşmemiş vertex transferi bozar),
   sharp edges aç.
3. **Önce gövdeyi**, sonra `Shift` ile giysiyi seç (gövde koyu turuncu, giysi açık).
4. Weight Paint → Weights → **Transfer Weights**:
   - Vertex Mapping: **Nearest Vertex** (öznel, denenebilir)
   - ⚠️ **Source Layers = `By Name`** (Active Layer DEĞİL)
   - Destination = All Layers
5. Boş vertex gruplarını temizle — **Sushi Cleanups** eklentisi:
   *delete from active object → empty vertex groups*.
6. Yaygın kusur: **omurga kemikleri kola sızar** → kol kalkınca kolun altı gövdeye
   yapışır. Bol kesim giysilerde daha sık. Elle temizle, sonra yeniden normalize et.

## 4. Freemode giysi üretimi 2025 (`uBBHJ4vG4fM`)

**Doku adlandırma kuralı** dalın tamamında geçerlidir → `branches/clothing/_branch.md`.

### Diğer adımlar
- Başlamadan **`Ctrl+A` → Apply All Transforms**.
- Materyal **basit** olmalı (yalnız image node'lar) ya da Sollumz `ped` shader'ını
  sıfırdan kur (yazarın tercihi).
- **spec ve bump gömülür (embed), diffuse GÖMÜLMEZ** — oyunda doku değiştirmek için.
- LOD: Sollumz **LOD Tools → referans mesh seç → Medium + Low → Generate LODs**,
  varsayılan decimation **0.6**. Elle yapılacaksa: çoğalt → Decimate → apply →
  mesh'i anlaşılır bir adla adlandır → orijinalin Medium/Low yuvasına ata.
- Kendi drawable model'ini import edilen **vanilla drawable'ın altına** taşı,
  vanilla mesh'i sil.
- **İki UV map zorunlu**: `UVMap 0` = doku UV'si, **`UVMap 1` = kan haritalaması**
  (ona dokunma).

## 5. Export tuzakları — sessiz kıranlar (`IbZ4xSCZt6I`, `Jm3Ps157z3s`)

- ⛔ **Export → Drawable → `Mesh Domain` = `Face Corner`.**
  `Vertex` seçeneği **yalnız MP freemode kafaları** içindir (vertex sırası önemli).
  Yanlış seçilirse sessizce bozuk çıkar. Yazar bunu ilk çekimde kaçırıp
  videoyu yeniden kaydetmek zorunda kalmış.
- **Non-streamed ped'de hiçbir doku gömülü OLMAMALI** — hepsi ilgili `.ytd`'ye gider.
  Export klasöründe bir `textures/` klasörü oluştuysa bir yerde embed kalmış demektir.
  Doğru çıktı: yalnız `<ped>.ydd.xml`.
- **Bileşen export'unda `Exclude Skeleton` KAPALI** (kafa için gerekli).
  **Ped prop export'unda `Exclude Skeleton` AÇIK.**
- `Alt+P` → **Clear and Keep Transformation** ile giysiyi hiyerarşiden çıkar,
  sonra shift-drag ile hedef `upper_00X`'in altına at.

## 6. Ped vertex renkleri (`uVlBINnNTGA`)

Object Data Properties → **Color Attributes** (İngiliz yazımı: **`Colour`**):

| ad | domain | tip | değer | ne işe yarar |
|---|---|---|---|---|
| **`Colour 0`** | Face Corner | Byte Color | hex **`FF8000`** (turuncu) | **oyun içi aydınlatma**. Yoksa güneşte parça garip koyu gölgelenir. |
| **`Colour 1`** | Face Corner | Byte Color | hex **`000000`**, **Alpha = 0** | **rüzgâr + ter efektleri**. Alfa > 0 ise giysi rüzgârda sallanır / gereksiz parlar. |

- Neredeyse her ped `.ydd`'sinde **iki tane** olur.
- **Emissive giysi**: `Colour 0` → pembe (video `FF00BF` civarı okuyor, tam değeri
  gözle doğrula), `Colour 1` aynı kalır; materyali Shader Tools ile **`ped_emissive`**
  yap; `value parameters` altındaki **emissive multiplier** (varsayılan 1) ile
  parlaklığı artır.
- Bazı yerel ped'ler sarı-yeşil paletli gelir; sorun değil, gerekirse hepsini
  `FF8000` yap. Yüzdeki boyama subsurface-scattering benzeri aydınlatma farkıdır.
- ⚠️ 360 spin videosunda (`ahPJhRZPiZQ`): **emissive alanların vertex rengi BEYAZ
  olmalı**, yoksa emissive çalışmıyor. Bu yüzden emissive parça mesh'ten `Y` ile
  ayrılır — vertex renkleri parça bazında farklı olabilsin diye.

## 7. Ped ölçekleme (`LfyCgqZMr3I`)

1. Zemin hizasına bir **plane** koy → `Shift+S` → **Cursor to Selected**
   → pivot'u **3D Cursor** yap.
2. Pose Mode → `SKEL_ROOT`'un **içindeki** her şeyi seç (pelvis vs.) → ölçekle.
   Ölçek değerini **kopyala**.
3. **Kafa iskeleti ayrı bir armature'dır** — aynı işlemi orada da yap ve
   **aynı ölçek değerini** yapıştır.
4. **Her bileşende ve HER LOD'da** (high/medium/low) **Armature modifier'ı apply et**.
5. İki iskelette de Pose Mode → `A` → `Ctrl+A` → **Apply Pose as Rest Pose**.
6. Export: Select Hierarchy → **Selected Objects AÇIK**, **Exclude Skeleton KAPALI**.
7. Orijinal (değiştirilmemiş) `.yft`'i al; `.ydd.xml`'deki **`<Skeleton>`** bloğunu
   `.yft.xml`'e kopyala.
- ⚠️ **Bilinen kusur:** koşarken sağa-sola **salınım** olur, çünkü `SKEL_ROOT`'un
  kendisi ölçeklenmiyor.
- ⚠️ **Articulate iskeletli hayvan ped'lerinde çalışmıyor** (atlas §10'daki
  dört ayaklı iskelet notlarıyla tutarlı).


---

## 8. Ayakkabıya göre boy + saç ölçekleme (`.ymt` tarafı)

Topuklu ayakkabıda ped'in boyunun artması `.yed`'den **değil**, `.ymt`'den
gelir. `.yed` tarafının ayrıntısı (`MP_HEELS.EXPR`, bileşen sırası, jiggle) bu sürümde
yok; temel adımlar aşağıda.

1. `MP_HEELS.EXPR`'i `AMBIENT.YED`'den kopyala → FEET bileşeni olarak yapıştır
   → **`FEET_000_U`** diye yeniden adlandır (**sıraya dikkat**).
2. `AP_M.XML` → **`CreatureMetadataName` = `mp_creaturemetadata`**.
   Saç ölçeklemeyi **ve** boy ayarını açan değer budur.
3. **YMTEditor** (grzybeek) ile `.ymt`'yi aç → feet bileşeni → *View component
   properties* → **`hash_07AE529D`** satırında **5 sayı** vardır;
   **yalnız en sağdaki** boy ofsetidir. Ped havada kalıyorsa **negatif** ver.
- ⚠️ Boy için yeni feet bileşeni eklerken **`.yed`'i değiştirmeye gerek yok** —
  yalnız `.ymt` değeri.

**Ölçüm:** NcProductions `.yed` Part 2 (`bxmVJfL8KcA`), `notlar/07` §4, 2026-09.
