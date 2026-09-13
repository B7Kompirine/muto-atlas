# Vanilla parçayı kendi modelimle değiştir (yol, prop, yapı)

**Ne zaman okunur:** haritadaki bir yol dilimini, prop'u, yapı parçasını gizleyip yerine kendi modelini koyacaksın; "yakından temiz uzaktan duruyor", Z-fighting, beyaz yüzey, harita collision'ı gitti.
**When to read:** replacing a vanilla road, prop or structure with your own model; recovering its textures; custom split normals.
**Kaynak:** `vanilla-parca-degistirme.md` (tamamı, 2026-08) · bir yol yıkımı çalışması (2026-09-01) · **Ölçüm:** hw1_27 vinç + fwy_01/dt1_rd1 otoyol; entities.db ile doğrulanmış LOD zinciri ve `hei_` ikizleri
**Önce:** `dallar/map/_dal.md` · gövde › `govde/bayraklar.md`, `govde/arac-tuzaklari.md`

---


Bir yol dilimini, bir prop'u ya da bir yapı parçasını **kendi modelinle
değiştirmek** iki ayrı iştir ve ikisi de sessiz hatalarla doludur:

> ⭐ **Topluluk teyidi (`govde/arac-tuzaklari.md` §7 / Sollumz Discord):** bir `.ydd` sözlüğünün
> içindeki objeyi **SİLME, dünyanın altına taşı.** Silmek sözlükteki **diğer bağlı
> objelerin özelliklerini de bozuyor** ve o bölgenin dokusu bulanık/düşük kaliteli
> görünmeye başlıyor. Aşağıdaki §1 ile aynı kural, bağımsız kaynaktan.
> Ayrıca: tek bir `.ydd` değiştirmek için **ytyp/ymap gerekmez.**

1. vanilla olanı **görünmez yapmak** (silmeden — §1)
2. kendi modelini **vanilla'nın kendi verisinden üretmek** (§3) ve
   **dokularını geri bağlamak** (§4)

Buradaki her sayı hw1_27 vinç + fwy_01/dt1_rd1 otoyol işinde ölçüldü.

---

## 1. Vanilla entity'yi gizleme

### Silme, AŞAĞI TAŞI

Child LOD'u olan bir entity silinirse dizideki indeksler kayar ve başka
ymap'lerin `parentIndex` değerleri sessizce yanlış entity'yi gösterir.
Doğrusu `position.z -= 600`. İndeksler ve sayılar korunur, geri alınabilir.

### ⛔ EXTENT'LERE DOKUNMA

Entity'yi 600 m aşağı taşıyınca "extent dışında kaldı" diye
`entitiesExtentsMin` / `streamingExtentsMin` değerlerini büyütme.
**Ölçüldü: bir ymap'in streaming hacmini derinleştirmek o bölgenin akışını
ve fizik ızgarasını çökertiyor — haritanın tamamında collision kayboldu.**

| dosya | orijinal ent/str z | benim yazdığım | sonuç |
|---|---|---|---|
| hw1_27_strm_0 | 31.0 / −111.1 | −650 / −650 | harita geneli collision gitti |
| dt1_rd1_strm_2 | 28.3 / −111.4 | −650 / −650 | aynı |

Entity zaten extent **dışına** çıkınca hiç akmıyor; gizlemek için o yeterli.
Extent'e dokunmak gerekli değil, zararlı.

### LOD ZİNCİRİNİN TAMAMINI yamalamak gerekir

Tek bir görsel nesne haritada **üç ayrı katmanda** durur:

```
X_strm_N.ymap   HD          (yakın)
X.ymap          LOD + SLOD1 (orta)
X_lod.ymap      SLOD2       (uzak, birden fazla bloğu tek modele kaynatır)
```

`parent` alanı zinciri verir: `hw1_27_strm_0 → hw1_27 → hw1_lod`.
Sadece HD'yi gizlersen yakında temiz, **uzaktan hayalet** görürsün.

**SLOD2 genelde gizlenemez**: `hw1_lod_22_23_26_27` adlı SLOD2'nin
**15 çocuğu** var; gizlemek 15 başka yapının uzak görüntüsünü de götürür.
Çözümü ymap değil **model cerrahisi** (o drawable'dan ilgili kısmı kesmek).

### ⛔ `hei_` İKİZLERİNİ UNUTMA — bu bir tur kaybettirdi

mpheist DLC aktifken haritanın çoğu ymap'inin `hei_` önekli bir kopyası
vardır ve **gerçekte yüklenen odur**. Base sürümü yamalayıp `hei_`'yi
atlamak "yakından temiz, uzaktan duruyor" belirtisini verir.

```
hw1_27_strm_0      +  hei_hw1_27_strm_0        (HD)
hw1_27             +  hei_hw1_27               (LOD/SLOD1)
fwy_01             +  hei_fwy_01
dt1_rd1            +  hei_dt1_rd1
```

Her yamada ikisini birden ara: `extract_asset.ps1 -Pattern 'hei_X*.ymap'`.

### Ayak izindeki HER ŞEYİ önce say

Tahminle entity aramak yerine veritabanını sorgula — bir ayak izi içindeki
her entity'yi ymap'iyle birlikte listele (`data/entities.tsv.gz`):

```python
# (x,y) -> (s,u) yerel çerçeveye çevir, z bandıyla birlikte süz
if -52<=s<=3 and -26<=u<=24 and 36<=z<=46: bul.append(...)
```

Bu tarama olmadan **`fwy_01_rd_09_ov`** atlandı ve iki tur Z-fighting
kovalandı (§5).

---

## 2. Ne gizlemek gerektiğini belirleme: overlay ve decal

Yol yüzeyi tek model değildir. En az üç katman vardır:

| sonek | ne | atlanırsa |
|---|---|---|
| `X_rd_NN` | asıl yol yüzeyi | yol yok olur |
| `X_ovly_NN` | yol kaplaması | — |
| `X_rd_NN_ov` | **decal** (shader adı birebir `decal`) | senin yüzeyinle **aynı düzlemde** kalır → Z-fighting |

`fwy_01_rd_09_ov` ölçümü: çöken dilimin ayak izinde **3.417 vertex**,
bunların 2.128'i z>40, medyan z **42.47** — bizim plakaların üst yüzeyi
41.6–42.6. Yani birebir aynı düzlem.

**Kapı:** kendi modelini koyduğun ayak izindeki her vanilla entity için
"yüzeyi benimkiyle çakışıyor mu" diye geometriyi oku — ekranda görünen
üçgen deseni Z-fighting'in kesin işaretidir ama sebebini söylemez.

---

## 3. Kendi modelini vanilla'dan kesme

### Kesim tümleyen olmalı

Ayak izi içi + dışı = orijinalin tamamı. Yüz merkezine göre kesim bunu
matematiksel olarak garanti eder ve ölçüyle doğrulanır:

```
kaynak toplam 14.956 yuz = disarida 13.058 + iceride 1.898
```

Boşluk da yok, çakışma da yok. İki farklı ölçüte göre iki kez kesme
(bir yerde yüz merkezi, başka yerde `bisect_plane`) tümleyenliği bozar.

### ⛔ MATERYAL İNDEKSİNİ TAHMİN ETME

Bir kesim/birleştirme adımı materyal indekslerini sıfırlayabiliyor
(`farkli indeks = 1` görürsen tam olarak bu olmuştur). Kaybolan atamayı
"en yakın vanilla poligonundan" geri türetmek **çalışmaz**: ölçülen medyan
hata 0.7 m ve sonuç gözle bozuk (asfaltın yerine bariyer atlası çizildi).

Doğrusu: atamayı türetme, **orijinalden yeniden kes**. Yüzler vanilla'nın
kendisi olduğu için materyal ve UV tanım gereği doğru olur.

Denetim: kesimden sonra poligon sayıları orijinalle birebir tutmalı
(9235 / 316 / 2636 / 871 gibi) ve `farkli indeks` sayısı slot sayısına
yakın olmalı.

### Blender tuzakları (hepsi yaşandı, hepsi sessiz)

- **`bpy.ops.object.transform_apply` hiçbir şey yapmayabilir** → mesh 124 m
  kaydı, hata çıkmadı. Operatöre güvenme, dönüşümü veriye pişir:
  `d.data.transform(d.matrix_world)` + `d.matrix_world = Identity`.
- **Elle bmesh birleştirme UV ve renk katmanlarını düşürür.** `bm.faces.new()`
  loop verisini taşımaz. `mesh.transform()` + `bpy.ops.object.join()` kullan;
  join katmanları ada göre birleştirir.
- **Vertex grubunu SİLMEK ağırlığı da siler.** Mesh'i atadıktan sonra
  grupları temizlersen ağırlık verisi gider ve export "hiçbir vertex
  ağırlıklı değil" der. Mesh'i ata, grupları **silme**.

---

## 4. Doku kurtarma — vanilla modelin dokuları modelde DEĞİLDİR

### Ölçüm

```
dt1_rd1_r1_06        shader=21  gomulu doku=0   istenen doku=61
fwy_01_rd_01         shader=22  gomulu doku=0   istenen doku=51
prop_towercrane_02a  shader= 9  gomulu doku=0   istenen doku=15
```

**Yedi kaynak modelin hiçbirinde gömülü doku yok.** Hepsi dış sözlük
kullanıyor. Arketipin `textureDictionary` alanı ilk halkadır, gerisi
**ebeveyn zinciridir**.

### Zinciri izleme

1. `assetdb.py show <model>` → `textureDict` hash'i.
2. Hash'i isme çöz (jenkins). Çıkmazsa oyundaki tüm `.ytd` adlarını tarat.
3. `gtxd.meta` ebeveynleri verir (`GlobalRoads`, `DowntownRD`, `CityEastRD`…).
4. Paylaşılan ebeveyn sözlükler burada: **`x64g.rpf/levels/gta5/generic/gtxd.rpf`**
   (771 ytd). Prop dokuları için ayrıca modelin `+hi` / `+hidr` ikizleri.
5. Detay dokuları (`env_*`) **`x64a.rpf/mapdetail.ytd`** içindedir.

### Doku adı indeksi çıkar, tahmin etme

`scripts/ytd_index.ps1` — bir klasördeki tüm `.ytd`'lerin doku **adlarını**
listeler (DDS yazmadan). 948 sözlük / 13.003 doku indekslendi; istenen 131
dokunun 116'sı 9 sözlükte bulundu.

### ⛔ AYNI AD, FARKLI İÇERİK

175 doku birden fazla sözlükte var; **22'sinin içeriği gerçekten farklı**
(md5 ile ölçüldü). Kopyalar arasından **boyuta göre seçme** — 174.888 bayt
512×512 DXT1 + mip zincirinin standart boyutu, yani boyut hiçbir şey
söylemez. Seçim GTA'nın kendi çözüm sırasına göre yapılır:

```
modelin KENDI sozlugu  ->  ebeveynleri  ->  yabancilar (en son)
fwy_01, dt1_rd1_1 …    ->  freewayrd, globalroads …  ->  paletoroadtemp …
```

### Sollumz'un uydurduğu adlar

- `ABAB_a` biçimli **birleşik adlar**: Sollumz materyali diffuse+alpha
  adını birleştirerek adlandırır. Bunların bir kısmı GTA'da gerçekten
  vardır (vanilla `.ydr` de aynı adı kullanır), bir kısmı yoktur.
- `<model>_pal`: bağlanamayan palet örnekleyicisine model adından türetilmiş
  ad. **Oyunda böyle bir doku yoktur**, aramaya değmez.

Ayrım: vanilla `.ydr`'yi XML'e dök ve doku parametre adlarına bak. Vanilla
da o adı kullanıyorsa ad gerçektir, yoksa Sollumz uydurmuştur.

### `.ytd` üretimi

`scripts/dds_to_ytd.ps1` — üretimden sonra dosyayı **geri okur** ve doku
sayısı/adı/formatını doğrular. Boyut geçerlilik ölçütü değildir.
Ölçüm: 129 doku → 12 MB `.ytd`, geri okumada 114/114 md5 birebir.

**Arketipin `textureDictionary`'si var olmayan bir adı gösterirse hiçbir
doku çözülmez.** Tüm arketipleri tek kendi sözlüğüne bağla.

---

## 5. `cpv_only` ve decal katmanı — beyaz yüzeylerin gerçek sebebi

`cpv_only` **dokusu olmayan** bir shader'dır; yalnızca vertex renginden
çizilir. Yolun **taban katmanıdır** ve vanilla'da üstünü decal örter.

Ölçüm (25 plaka): `cpv_only` 3.412 m² kaplıyor; üstteki 128 yüzün **113'ü
başka yüzeylerin altında gömülü**, 15'i açıkta.

Decal'i ayak izinden kaldırırsan bu çıplak taban ortaya çıkar ve **büyük
beyaz üçgenler** olarak görünür. Materyal uydurmak yanlış çözümdür.

**Doğrusu:** decal'i de aynı hücrelere böl ve parçalara **kat** — yol
kırılınca kaplaması da onunla kırılsın (2.280 yüz).

---

## 6. Normaller — kalınlaştırmanın sessiz bedeli

### Ölçüm

Vanilla harita mesh'leri **custom split normal** taşır:
`has_custom_normals=True`, sharp kenar **0**, flat yüz **0**. Tüm
gölgelendirme baked normalden gelir.

Kalınlaştırma (solidify) yüzeyi katı bloğa çevirir; **üst yüzey ile dikey
kenar aynı vertex'leri paylaşır**, smooth gölgelendirmede 90°'lik köşede
normaller ortalanır ve yan yüz kısmen yukarı bakan normal alır — güneşi
üst yüzey gibi yansıtır, patlamış beyaz görünür.

### Ölçüt

Vertex normalinin z bileşenine göre dağılım; "ARA" = `0.2 ≤ |nz| ≤ 0.85`:

```
VANILLA fwy_01_rd_01     ARA=22%
VANILLA dt1_rd1_r1_06    ARA=14%
VANILLA towercrane_02d   ARA=21%
BIZIM  (bozuk)           ARA=38%
BIZIM  (duzeltilmis)     ARA=20%
```

**Bu ölçüt yalnızca devrilmemiş geometride anlamlıdır** — enkaz hâlinde
parçalar eğik olduğu için ARA doğal olarak %46'ya çıkar, kusur değildir.

### Düzeltme

Toptan "normalleri yeniden hesapla" **yapma**: vanilla'nın baked normalleri
yüz normalinden medyan 0.7° sapıyor ama **%10'u 24°'den fazla** sapıyor,
silmek yolun gölgelendirmesini değiştirir.

```python
# UST yuzlerin baked normalini KORU, kalinlastirmadan gelen
# yeni yuzlere DUZ (yuz normali) yaz.
nv=[Vector(me.corner_normals[i].vector) for i in range(len(me.loops))]
for p in me.polygons:
    if p.normal.z > 0.5: continue      # UST: dokunma
    for li in p.loop_indices: nv[li]=p.normal.copy()
me.normals_split_custom_set(nv)
```

Ayrıca kalınlaştırmayı **yalnızca aşağı** yap (`offset=-1`): üst yüzey
vanilla kotunda kalır, yukarı taşıp decal'lerle yarışmaz. Ölçüm: üst yüzey
yükseklik farkı medyan **0.000 m**.

Alt ve yan yüzlere gerçek doku ver (alt = `freeway_ubderbelly_new_01`,
kenar = `mh_bridgebase03`), UV'yi düzlemsel projeksiyonla üret ve ölçeği
**üst yüzeylerden ölç** (bu işte 0.167–0.197 UV/m, yani 1 tekrar ≈ 5–6 m).

---

## 7. LOD — orijinal prop ne yapıyorsa o

Ölçüm:

```
prop_towercrane_02a  ucgen H=3455 M= 706  M/H=0.20  lodDist 70
prop_towercrane_02b  H=1544 M= 338        M/H=0.22  lodDist 70
prop_towercrane_02c  H= 740 M= 326        M/H=0.44  lodDist 70
prop_towercrane_02d  H=8006 M=5924        M/H=0.74  lodDist 75
fwy_01_rd_01         LOD YOK (High tek)   lodDist 9998
dt1_rd1_r1_06        LOD YOK              lodDist 9998
```

- **Prop'ta Medium LOD vardır**, oran ~%20–44.
- **Yol modellerinde LOD yoktur** — yolun uzak görüntüsü ayrı `_lod`
  arketiplerinden gelir. Kendi yol drawable'ına LOD ekleme.

Sollumz'da: `obj.sz_lods.medium.mesh` + `drawable.drawable_properties
.lod_dist_high / _med / _low / _vlow`.

⛔ **Decimate 4-etki kuralını bozar.** Vertex birleşince ağırlık birden
fazla gruba dağılır. Rijit parçalarda LOD üretiminden sonra tek gruba %100
geri çek ve **çok-gruplu vertex = 0** olduğunu doğrula.

---

## 8. Kapı listesi (oyuna girmeden)

| ne | nasıl | eşik |
|---|---|---|
| extent bozulmamış | yamalı ymap'i orijinaliyle karşılaştır | birebir aynı |
| tüm LOD katmanları gizli | base **ve** `hei_` sürümlerde say | HD+LOD+SLOD1 |
| kesim tümleyen | iç + dış = orijinal yüz sayısı | birebir |
| materyal taşınmış | `farkli indeks` sayısı | slot sayısına yakın |
| UV/renk katmanı | `me.uv_layers`, `me.color_attributes` | `UVMap 0`, `Color 1` |
| obje transformu | export'tan **hemen önce** matrix_world | identity |
| doku çözülüyor | `.ydr` doku parametreleri ∩ `.ytd` indeksi | eksik ≈ 0 |
| normaller | ARA oranı | vanilla bandı %14–22 |
| LOD ağırlıkları | çok-gruplu / ağırlıksız vertex | 0 / 0 |


---

## Çalışılmış örnek — 10 m'lik yol yarığı (`dt1_rd1_r1_28`, 2026-09-01)

Bir vanilla yol parçasını değiştirirken **önce çıkarılması gereken** taban verinin tamamı; aynı sırayı kendi hedefin için tekrarla.

### Hedef (kullanıcı kararı)

| olcu | deger |
|---|---|
| uzunluk | 10 m |
| genislik | ort. 2 m (bir uc genis, uzakta incelir) |
| derinlik | 3 m |
| dip | gorunur moloz + kaya (oyuncu duser, dipte durur) |
| hat | genis baslar, uzaga dogru catlaga incelir |

### Hedef asset

| alan | deger |
|---|---|
| HD arketip | `dt1_rd1_r1_28` hash **700810582** |
| ytyp | `downtown_01_metadata_002_strm.ytyp` |
| konum | 252.06, -946.04, 25.78 |
| bbox | -51.6977,-81.9242,-2.6449 / 51.6876,83.4316,2.6808 |
| lodDist | 148 |
| flags | 8192 = Dont Cast Shadows |
| textureDict | **`dt1_rd1_1`** (hash 1203152392 — jenkins ile DOGRULANDI) |
| physicsDict | 0 -> collision ayri .ybn'de |

Overlay (yol cizgileri, ayri entity):

| alan | deger |
|---|---|
| ad | `dt1_rd1_r1_ovly_38` hash 1433796416 |
| konum | 251.91, -946.21, 25.77 (HD'ye 0.23 m) |
| lodDist | 93 |
| bbox | +-49.02 x +-67.48 x +-2.64 |
| textureDict | `dt1_rd1_1` (ayni) |

⛔ v1 bu overlay'i HIC saymadi. Kaldirilmazsa yarigin ustunde **havada asili
yol cizgileri** kalir.

### LOD zinciri (assetdb.py lodchain — dogrulandi)

| # | ad | ymap | idx | lodDist |
|---|---|---|---|---|
| 0 | `dt1_rd1_r1_28` | `dt1_rd1_strm_6.ymap` | 66 | 148 |
| 1 | `3700422285` | `dt1_rd1.ymap` | 225 | 400 |
| 2 | `dt1_lod_12_13_22_23` | `dt1_lod.ymap` | 33 | 1500 |

SLOD2 (#2) **dokunulmuyor** — 10 m'lik yarik 1500 m'den gorunmez.

LOD ebeveyni `3700422285` cozuldu (kullanicinin verdigi 4 deger buydu):

| alan | deger |
|---|---|
| ytyp | `downtown_01_metadata_001.ytyp` |
| assetType | ASSET_TYPE_DRAWABLEDICTIONARY |
| assetName | `dt1_rd1_r5h_slod1_children` (.ydd) |
| textureDict | `dt1_rd1_lod` (hash 2280611059 — DOGRULANDI) |
| lodDist | 400, flags 8192 |

### Dokunulacak 4 ymap + DOGRU base surumler

⛔ Ayni ymap birden fazla RPF'te var ve **surumler farkli**. `-Flatten $true`
ile cikarmak sessizce yanlis surumu birakir (sonuncusu kazanir).

| ymap | DOGRU kaynak | md5(12) |
|---|---|---|
| `dt1_rd1_strm_6.ymap` | **patchday27ng** | 4d16ad79331d |
| `dt1_rd1.ymap` | **patchday27ng** | dfe50afe6540 |
| `hei_dt1_rd1_strm_6.ymap` | **update.rpf/dlc_patch/mpheist** | 3d2d93bdd35b |
| `hei_dt1_rd1.ymap` | **update.rpf/dlc_patch/mpheist** | a8f3e2f171da |

Dordunde de patchday27ng / dlc_patch surumu digerlerinden FARKLI.
Dogru kopyalar: `vanilla/dogru/`.

`hei_` ikizi **VAR** — v1'in `VANILLA_KALDIR.md` dosyasindaki
"hei_ ikizi YOK (olculdu)" satiri YANLISTI (entities.db ile dogrulandi).

### Collision

`dt1_rd1` collision'i 12 .ybn'e bolunmus. Hedefi kapsayan **TEK** dosya:

**`dt1_rd1_4.ybn`** — BoxMin 88.6,-981.9,23.1 / BoxMax 304.3,-768.4,53.0

Yarik 10 m oldugu icin komsu ybn'lere tasmiyor. (Komsu `dt1_rd1_3` y=-969.6'da
bitiyor, bizim hedef -946.)

### Vanilla yol geometrisi

| olcu | deger |
|---|---|
| model | 1 |
| geometry | 28 |
| ucgen | 5660 |
| LodDistHigh/Med/Low/Vlow | 9998 (hepsi) |
| gomulu Skeleton | YOK |
| gomulu Bound | YOK |

Shader'lar (2 tur, jenkins ile cozuldu):
- `normal_spec_detail` (3620052489) — asfalt govdesi, 22 geometry
- `normal_spec_decal` (471606640) — kaplama/cizgi katmani, 6 geometry

### Cakisma (COZULMEDI — karar bekliyor)

Uc kaynak ayni vanilla ymap'lerin **farkli duzenlenmis** surumlerini
stream ediyor. FiveM'de biri kazanir, hangisi belirsiz.

| ymap | cakisan kaynak |
|---|---|
| `dt1_rd1.ymap`, `hei_dt1_rd1.ymap` | `[harita]/my-test-map` |
| `hei_dt1_rd1_strm_6.ymap` | `[script]/crux_bennysautos/crux_crucialfix` |

### CodeWalker.Core — dogru property adlari (bu oturumda olculdu)

⛔ Yanlis ad **hata vermez, $null doner** (§5). Olculmus dogru adlar:

| nesne | YANLIS | DOGRU |
|---|---|---|
| Bound | `BoundingBoxMin/Max` | **`BoxMin`** / **`BoxMax`** |
| Drawable | `DrawableModelsHigh` | **`DrawableModels`** / **`AllModels`** |

⛔ `ShaderGroup.Shaders` foreach'te **NotImplementedException** atar
(`ResourcePointerArray64<T>`). Cozum: `.data_items` uzerinden gez.
