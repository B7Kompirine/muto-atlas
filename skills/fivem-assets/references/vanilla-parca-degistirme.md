# Vanilla haritanın bir parçasını kendi modelinle değiştirme

Bir yol dilimini, bir prop'u ya da bir yapı parçasını **kendi modelinle
değiştirmek** iki ayrı iştir ve ikisi de sessiz hatalarla doludur:

> ⭐ **Topluluk teyidi (`sollumz-discord-tutorials.md` §4):** bir `.ydd` sözlüğünün
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
- ⛔ **Obje transformu export'a PİŞER.** `matrix_basis` identity değilse
  Sollumz onu geometriye yazar. Ölçüldü: drawable 394 m ötede çizildi,
  oyunda animasyon boyunca hiçbir şey görünmedi. `matrix_basis` **ve**
  `matrix_parent_inverse` sıfırla ve **aynı çağrıda doğrula** — bir kez
  sıfırlayıp sonra kontrol etmemek yetmiyor, geri gelebiliyor.

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
