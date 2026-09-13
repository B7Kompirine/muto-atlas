# Çim / prosedürel zemin / arazi

**Ne zaman okunur:** "çimen yapalım" — hangi sistem; kendi arazin; `@ma` prosedürel collision; grass batch; fur grass; "çim görünmüyor".
**When to read:** grass, procedural ground cover, terrain material and the procedural IDs that spawn it.
**Kaynak:** `notlar/08` §1-7 (Stumpy Mason videoları, [video]) · SKILL proc/mat sorguları · **Ölçüm:** video adımları; veri tarafı `procedural.tsv` (255) ve `collision_materials.tsv` (185) ölçülü
**Önce:** `dallar/map/_dal.md` · gövde › `govde/bayraklar.md`, `govde/arac-tuzaklari.md`

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" proc [<ad>|--id N]   # prosedürel tablo (collision 'Procedural ID')
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" mat  [<ad>|--index N] # collision materyali + bayraklar
```

⚠️ Aşağıdaki adımlar **video anlatımıdır** (tek üretici, çalıştığı gösterildi); sayılar `assetdb.py` ile doğrulanır.

## 1. GTA'da çim DÖRT ayrı sistemdir

Bir "çimen yapalım" isteği geldiğinde **hangisi olduğu sorulmalı** — dördü
tamamen farklı üretiliyor:

| sistem | ne | nasıl |
|---|---|---|
| **düz doku** | zeminin kendi dokusu | `terrain_cb_*` shader + vertex color karışımı |
| **çim modelleri** | prop olarak yerleştirilmiş çim | ymap entity |
| **fur grass** | tüy benzeri hacimli çim | `grass_fur` / `grass_fur_mask` shader'lı ayrı drawable |
| **`@ma` prosedürel** | motorun kendiliğinden serpiştirdiği ot/çalı | **collision materyali** üzerinden |
| **ymap grass batch** | fırçayla boyanan instance'lar | CodeWalker'da ymap içinde |

### ⛔ Fur grass CodeWalker'da GÖRÜNMEZ
`fur_` ile başlayan drawable'ları açtığında **hiçbir geometri göremezsin** —
wireframe'de bile. Sadece materyali görünür. Bu bozukluk değil, normal.
(gövde: aracın göstermemesi ≠ yok.)

---

## 2. Vanilla arazi modelinin anatomisi (çözümlendi)

Bir vanilla zemin karosu açıldığında:
- **Üç UV map** — her doku katmanı için ayrı
- **İki color attribute:**
  - **`Colour 1`** = aydınlatma bölgeleri. Ölçülen örnekte:
    **mavi** = köprü altı / ay ışığı alan toprak · **pembe** = geneli ·
    **kırmızı** = güneş gören tepe kısımları
  - **`Colour 2`** = **hangi doku katmanının nerede görüneceği**
    (ör. yeşil bölge → kumlu toprak)

Yani katman karışımı `Colour 2`'de, aydınlatma `Colour 1`'de.


---

## 3. Kendi arazini üretme — ölçülü adımlar

1. **Circle** (72 vertex, ~25 m) → Edit Mode → yüzü seç → **Grid Fill**
   → `Ctrl+T` ile üçgenle.
2. **Proportional Editing açık, falloff `Random`** → sadece Z'de oynat →
   doğal tepe/çukur.
3. Dış çemberi düzle: edge select ile dış halkayı çift tıkla →
   **`S Z 0`** → 0'a koyduğun referans düzlemine snap'le, sonra düzlemi sil.
4. **Sculpt Mode → Smooth** fırçası, **düşük strength** — sivri köşeleri al.
   (Yazar strength'i yüksek bırakıp bozdu, sonra düşürdü.)
5. Shader: **`terrain_cb_4lyr_pxm`** ailesi (arama kutusuna `4lyr`).
6. UV: select all → unwrap → **Cube Projection**,
   ⭐ **cube size = 2** — *"çim için doku yoğunluğu iki."*
7. `Colour 1`: her yere **magenta** (R=1, G=0, B=1). Beyaz kalan yer olmasın.

### ⭐ Sollumz Vertex Painter — `Shift+T`
Viewport'ta `Shift+T` panelini açar. İçinde:
- **RGBA kanal izolasyonu**
- palet
- **multi-object vertex paint**
- ⭐ **Terrain Paint** — `texture 1/2/3/4` düğmeleriyle katman karışımını
  doğrudan `Colour 2`'ye boyar

Fırça boyutu sağ tık, strength ayarlanabilir. Katmanlar arasında geçiş yaparak
"tiled" görünümü kırarsın. **Geometri ne kadar yoğunsa kontrol o kadar iyi.**

⚠️ Color attribute'un yanındaki **kamera ikonu = "set render color"**:
hangi katmanı **boyadığını** seçer; yandaki göz hangi katmanı **gördüğünü**.
İkisi ayrı — karıştırırsan yanlış katmana boyarsın.

---

## 4. Arazi collision'ı

- Drawable'ı çoğalt → `.col` diye adlandır → **Composite**'e çevir
- Collision materyalleri: **grass (short)**, **gravel small**
- Edit Mode → tepeden bak → **circle select**, face modu → toprak görünen
  yüzleri seç → **gravel** ata → **`Ctrl+I`** ile tersle → **grass** ata
- ⭐ **Collision'dan dokuyu, UV map'leri ve color attribute'ları SİL** — gereksiz.
- Oyunda sonuç: toprakta **ayak izleri**, çimde **çim ayak sesi**.

---

## 5. Fur grass üretimi

1. Arazi mesh'inden bir parçayı seç → `Shift+D` → `P` → **Separate by Selection**
   → `Alt+P` → **Clear Parent, Keep Transform** (yerinde kalsın).
2. UV map'leri ve dokuyu sil.
3. Shader: **`grass_fur_mask`** (örnekte `SM_26` varyantı — maskesi olan bu).
4. Cube projection, yine **doku yoğunluğu 2**.
5. `UVMap 1`'de adaları **maskenin küçük adalarının içine** taşı.
6. Edit Mode → her şeyi **Z'de +0.01** kaldır.
7. **Subdivision Surface** ekle ve **hemen apply et**.
8. Vertex select ile bazı vertex'leri dışarı çekerek düzensizlik ver.

Oyunda: katmanlı nokta dizileri (stipple + height sampler'lar) → normal çimden
**daha hacimli** duruyor, alfa tabanlı. Ev önü çimi gibi yerler için uygun.
Kenarına çim→toprak geçişi koymak gerekiyor, yoksa kesik duruyor.

---

## 6. ymap **Grass Batch** — fırçayla prosedürel serpme

CodeWalker Project → yeni ymap → **YMAP → New Grass Batch**.

Alanlar: **LOD distance · fade distance · orient to terrain · optimize batch ·
ad** (ör. `proc_grasses01`).

**Brush** sekmesi: radius · density · **color (RGB çarkı)** · ambient occlusion ·
scale (**random** olabilir) · padding · brush mode.

- **`Ctrl` basılı tut + sol tık sürükle** = instance boyar
- radius = daire boyutu · density = daire içinde kaç adet
- ⭐ **color = oyundaki rengi** — kırmızı boyarsan oyunda kırmızı çıkar
- **Optimize Batch** çok sayıda instance'ı küçük gruplara böler
- Model adları **Pleb Masters: Forge**'da `procedural` filtresiyle bulunur
  (ör. `prop_brittle_bush_01`); tüm prosedürel modeller **`v_proc1.rpf`** içinde
- Kaydet + **manifest üret**

### ⛔ Grass batch KENDİ collision'ına boyamaz — ve çözümü GTA'yı kırıyor
Grass batch **yalnız base game collision'ının üstüne** boyar. Kendi projendeki
modelin üzerine boyamaya çalışırsan fırça **modelin altına** boyar.

Videodaki çözüm (yazarın kendi deyimiyle *"sistemi hack'liyoruz"*):
1. Bölgenin **base game `.ybn`**'ini XML olarak çıkar, Blender'a al.
2. Kendi collision poly mesh'ini `Alt+P` ile serbest bırak, **dünya
   koordinatlarını** Collision → object location/rotation alanına yapıştır,
   base game YBN'in **BVH'sine** sürükle.
3. Export et ve **base game RPF'ine geri yaz** (CodeWalker
   *"base game dosyalarını doğrudan düzenliyorsun"* uyarısı verir).
4. CodeWalker'ı yeniden başlat → artık kendi collision'ına boyayabiliyorsun.
5. ⛔ **Oyun bütünlük kontrolünden geçmez, GTA açılmaz.**
6. **Düzeltme:** Rockstar Launcher / Steam → **verify game files**
   (~211 MB indirir). Dosyayı yazarken içinde bulunduğu klasörler
   **şifresi çözülmüş** hâle geliyor, doğrulama onları yeniden şifreliyor.

> **Değerlendirme:** çalışıyor ama base game dosyasına yazıyor ve geri alma
> adımı zorunlu. Kullanıcıya önerirken **bu maliyeti söyle**; kendi ymap'inde
> entity olarak çim prop'u koymak çoğu durumda yeterli olabilir.

### ⛔⛔ "Çim görünmüyor" = önce GRAFİK AYARINA bak
Yazar her şeyi doğru yaptıktan sonra oyunda **hiç çim göremedi**.
Sebep: **Ayarlar → Grafik → `Grass Quality`** **Normal**'daydı.
**Ultra** yapıp yeniden başlatınca çim çıktı.

> Bu, atlasın *"ekran görüntüsü ölçüm değildir"* dersinin bir varyantı:
> **çıktı görünmüyorsa önce oynatıcı/ayar tarafını ele.**

---

## 7. `@ma` prosedürel collision — çok kırılgan

`@ma` collision'ları, materyal indeksine bağlı olarak motorun kendiliğinden
ot/çalı serpiştirdiği bound mesh'lerdir.

- Bir `@ma` collision'ında birden çok materyal olur ve **liste aşağı indikçe
  materyal indeksi birer birer artar** (en üst = 1).
- Kendi tipini eklemek: listedeki en yüksek indeks + 1'e yeni bir materyal
  ekle ve prosedürel adını ver (ör. `proc_high_flowers`).
- Geometriyi `@ma` collision'ın bound poly mesh'ine **`Ctrl+J` ile birleştir**
  (`Alt+P` → clear parent keep transform önce).
- ⛔ **Yazarın bulabildiği tek yol: VAR OLAN bir `@ma` collision'ına EKLEMEK.**
  Sıfırdan `@ma` collision üretmeyi başaramamış.

### Sonraki videoda (`A8ueX5UgmGE`) düzeltilen nokta
- Bazı çim tipleri hiç çıkmadı. Sebep sanılanın aksine ad değil:
  ⭐ **collision poligonu yeterince BÜYÜK olmalı.** Kareler büyütülünce
  daha önce çalışmayan tiplerin **hepsi çalıştı**.
- Tüm üçgenlere çim gelmiyor — performans amaçlı.
- ⚠️ **Çok kırılgan, az kullan.** Su altı tipleri de var (test edilmemiş).
- Doğrulanmış tip adları: `city_weeds_01` · `mountain_side_dry` ·
  `mountain_side_lush` · `hill_side_lush` · `green_meadow_01` ·
  `city_weeds_sparse` · `city_weeds_litter` ·
  `AD_City_Industrial_Weeds_Lodo_01_Dense`

> `assetdb.py proc` ve `assetdb.py mat` — **veri** elimizde. Eksik olan üretim tarafıydı: **poligon boyutu** ve
> **var olana ekleme** zorunluluğu.

---


## Topluluk uyarısı — arazi karışımı

⛔ **Arazi karışımı `UVMap 1` olmadan hiç çalışmaz** (lookup sampler onu kullanır); ayrıca **`Colour 1`'in ALFASI siyah** olmalı (beyaz = lookup kapalı). (Sollumz Discord.)
