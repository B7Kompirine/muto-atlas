# Yıkım / çökme / koreografili sahne — RayFire `des_*`

**Ne zaman okunur:** bir bina, köprü, yol, kule, iskele çöksün; "sağlam → animasyonlu çöküş → enkaz"; patlama sonrası kalıcı enkaz; collision'ın koreografiyle hareket etmesi.
**When to read:** destruction, collapse or a choreographed scene — RayFire `des_*` composites, road/bridge/building coming down.
**Kaynak:** `rayfire-des-uretim.md` (tamamı, 2026-08/09) · **Ölçüm:** vanilla `des_stilthouse` alan alan; `des_mytest`, `des_crane`, `des_kopru` oyunda
**Önce:** `dallar/map/_dal.md` · gövde › `govde/bayraklar.md`, `govde/arac-tuzaklari.md`

---

⛔ **Yol seçimi önce:** bu yaprak bina/kule/yol/köprü çöküşü içindir. Tek prop'un kapağı/kolu ya da motor sürücüsü (saat, bariyer) başka reçetedir ve bu sürümde yok. İki reçetenin melezi hiç çalışmadı.


**Ne zaman:** bir bina, kule, ağaç, iskele ya da herhangi bir harita
yapısının **koreografili** yıkılması istendiğinde. Fragment kırılması
(`prop_*` cam/tahta parçalanması) DEĞİL — o başka sistem. Buradaki sistem
"sağlam hal → oynatılan çöküş animasyonu → enkaz hali" üçlüsüdür.

Kaynak: vanilla `des_stilthouse` **alan alan** açıldı (ytyp, ycd, 8 ydr,
3 ymap, 6 ybn, yerleştirici ymap) ve birebir kopyası (`des_mytest`)
üretilip oyunda çalıştığı doğrulandı. Buradaki sayıların hiçbiri tahmin
değildir. Çapraz kontrol: `des_protree`, `des_apartmentblock`,
`des_tvsmash`, `des_farmhouse`.

Sorgu: `assetdb.py show des_*` · `res_to_xml.ps1`

---

## 1. Zihinsel model: composite bir OBJE değil, bir YÖNETMEN

`des_X` diye bir arketip **yoktur**. Var olan şey `.ytyp` içindeki ikinci
bir blok — `compositeEntityTypes` — ve o blok motora şunu söyler:

| alan | anlamı |
|---|---|
| `StartImapFile` | sağlam halin bulunduğu ymap |
| `EndImapFile` | enkaz halinin bulunduğu ymap |
| `Animations[i].AnimatedModel` | çöküş sırasında **motorun yaratacağı** drawable |
| `Animations[i].AnimDict` / `AnimName` | o drawable'da oynatılacak klip |
| `punchInPhase` / `punchOutPhase` | klibin hangi faz aralığında oynatılacağı (vanilla 0 → 1) |

Tetiklendiğinde motorun sırası:

1. `StartImapFile` kapanır → sağlam bina kaybolur
2. `AnimatedModel`'deki drawable **motor tarafından yaratılır**
3. Klip `punchIn`→`punchOut` arası oynatılır
4. Klip biter, drawable silinir, `EndImapFile` açılır → enkaz belirir

**Sonuç: görünen üç ayrı varlıktır, tek arketip değil.** Sağlam hal ayrı
bir prop, enkaz ayrı bir prop, aradaki hareket üçüncü bir drawable.
"Tek objeyi hem animasyonlu hem collision'lı yapmak" bu sistemde yanlış
sorudur ve saatler yakar.

### ⛔ Animasyonlu drawable HİÇBİR ymap'te yer almaz

Ölçüldü: `des_stilthouse`'un 8 `rootN` arketipi `imapstart`, `imapend` ve
`rebuild` ymap'lerinin **hiçbirinde** entity olarak geçmez. Onları composite
yaratır. `CreateObject` / `rfspawn` ile elle çağırmak sistemin dışına
çıkmaktır ve gördüğün şey artık RayFire değildir.

### Composite'in KENDİSİ sıradan bir entity olarak konur

Yerleştirici, normal bir ymap'teki normal bir `CEntityDef`'tir ve
`archetypeName` = `joaat(composite adı)`'dır. Bu entity yoksa
`GetRayfireMapObject` hiçbir şey bulamaz.

Vanilla (`ch2_09b_strm_1.ymap`, contentFlags 65):
```
archetypeName = des_stilthouse   flags 1572864   parentIndex -1
lodLevel LODTYPES_DEPTH_ORPHANHD   lodDist 100   priorityLevel PRI_REQUIRED
```

### İki desen var — karıştırma

- **A · imap takası** (`des_stilthouse`, `des_protree`, `des_apartmentblock`):
  `StartModel`/`EndModel` **boş**, `StartImapFile`/`EndImapFile` dolu.
  Bina/yapı yıkımı bunu kullanır.
- **B · model takası** (`des_tvsmash`): `StartModel`/`EndModel` dolu.
  Tek prop'un yerine enkaz prop'u geçer. İç mekân ufaklıkları içindir.

---

## 2. `.ytyp` — ölçülmüş alanlar

### Animasyonlu kök arketip (`des_X_root`)

```
assetType          ASSET_TYPE_DRAWABLE      <- .ydr, FRAGMENT DEĞİL
flags              536871424                = Has Anim(512) + Use Ambient Scale
lodDist            100
hdTextureDist      5
clipDictionary     <ytyp adı>               (= composite adı)
textureDictionary  <txd adı>
drawableDictionary BOŞ
physicsDictionary  BOŞ                      <- animasyonda collision yok
specialAttribute   0
extensions         CExtensionDefParticleEffect (fxType 6) — toz/moloz, opsiyonel
```

`des_stilthouse`'un 8 kök arketipinin **tamamı** bu kalıbın birebir aynısıdır;
tek fark ad, kutu ve partikül sayısı.

### `compositeEntityTypes` (tek Item)

```
flags              536870912
lodDist            -1
specialAttribute   0
bsRadius           yapının küresel yarıçapı (stilthouse 44.66)
StartModel/EndModel  BOŞ  (desen A)
StartImapFile      des_X_imapstart
EndImapFile        des_X_imapend
PtFxAssetName      <.ypt adı>  — partikül yoksa BOŞ
Animations[N]:
   AnimDict        = ytyp adı
   AnimName        = AnimatedModel = arketip adı   <- ÜÇÜ AYNI
   punchInPhase    0
   punchOutPhase   1
   effectsData     partikül tetik listesi (0..19 arası, opsiyonel)
```

Çok parçalı yıkımlarda `Animations` birden fazla olur (stilthouse 8) — her
biri kendi drawable'ını kendi klibiyle sürer, hepsi eşzamanlı oynar.

---

## 3. `.ydr` — mesh nasıl kımıldıyor

**Rijit skinning.** Tek `DrawableModel`, `HasSkin=1`, `BoneIndex=0`,
vertex başına tek kemik:

```
Layout (GTAV1): Position, BlendWeights, BlendIndices, Normal, Colour0, TexCoord0
BlendWeights    0 0 255 0      <- tek kemiğe %100
BlendIndices    0 0 20 0       <- Geometry/BoneIDs paletindeki indeks
Unknown1        = kemik sayısı
Bounds          YOK            <- animasyon sırasında collision yoktur
LodDistHigh     9998
FlagsHigh       15
```

### Kemik hiyerarşisi DÜZDÜR

Ölçüldü: `des_stilthouse_root` 102 kemik, **101'inin de parent'ı 0**. Zincir
yok. Kemik[0] = `DES_StiltHouse_ROOT_bone`, `parent -1`, flags'inde `Unk0`
var. Her parça kendi kemiğine kilitlidir; kemik nereye giderse parça oraya
gider. Bu yüzden ağırlık boyama, yumuşak geçiş, Laplacian düzeltme vs.
**gerekmez** — istenmez de.

### `Tag`'ler keyfidir

`des_stilthouse` tag'leri 0, 743, 3793, 4289, 16689, 17738… — ne sıralı
ne formülle üretilmiş. Önemli olan tek şey `.ycd`'nin aynı sayıları
kullanmasıdır (§5 Bağ A).

---

## 4. `.ycd` — ölçülmüş sözleşme

```
Klip:
  Hash            = arketip adı            (des_stilthouse_root)
  Name            = pack:/<ad>.clip        (TEK pack:/ öneki)
  Type            Animation
  Unknown30       1
  Tags            boş ama VAR
  Properties      1 Item: NameHash hash_BF6A5D60 / UnkHash hash_996C3B27
                  Attributes: hash_BF6A5D60, Int, 32
  AnimationHash   = Hash
  StartTime 0 · EndTime (kare-1)/30 · Rate 1

Animasyon:
  Hash            = klip Hash ile aynı
  Unknown10       1
  FrameCount      579   (stilthouse)
  Duration        (kare-1)/30 = 19.266666
  BoneIds         kemik x 3  — Track 0 (ötelem), 1 (dönüş), 2 (ölçek), HEPSİ
  SequenceFrameLimit 303 -> 579 kare 2 sequence'e bölünür (304 + 276)
```

- **Track 2 boş bırakılmaz.** Vanilla ölçek kanalını `StaticVector3(1,1,1)`
  ile açık yazar. Sürülmeyen kanal rest'e dönmez, **önceki animasyonun
  pozunda kalır**.
- **Sequence bölünmesi 1 kare bindirmelidir**: `seq0 = limit+1`,
  `seq1 = toplam - limit`, toplam = kare+1. 121 karelik bir klipte
  bölünme gerekmez (Sollumz'un `kare+30` limiti zaten böler değil).
- ⛔ **KÖK KEMİK (tag 0) DAHİL, İSKELETİN TAMAMI yazılır.** Sollumz köke
  kanal yazmaz. Ölçüm: `des_crane.ycd` 51 kemiğin 51'ini de yazıyor, kök
  her track grubunun **başında** (indeks 0, 51, 102). Kök kanalları rest
  değerleridir: Track 0 `StaticVector3`(kökün rest konumu), Track 1
  `StaticQuaternion`(rest dönüşü), Track 2 `StaticVector3(1,1,1)`.
- ⛔ **`BoneIds` sayısının ölçütü dosyanın kendi tutarlılığı DEĞİLDİR.**
  Ölçüt `iskelet kemik sayısı × 3`. Bu yaşandı: `330 = 110×3` kendi içinde
  tutarlı olduğu için "doğrulandı" sanıldı, oysa iskelette **111** kemik
  vardı ve kök eksikti. Doğrulama daima `.ydr`'nin kemik sayısına ve
  **çalışan bir referans dosyaya** karşı yapılır.

### Üretim hattı — Sollumz çıktısı DOĞRUDAN kullanılmaz

> Bu public sürümde aşağıdaki `.ycd` yama betikleri **yoktur**; hat yalnız sözleşmeyi anlatır.

```
Sollumz .ycd export (XML cikar)
  -> fix_ycd_xml.py          bos <Hash> kalmissa doldurur (ag; doluysa 0 ekler)
  -> ycd_track2_ekle.py      Track 2 (olcek) grubu eksik
  -> ycd_kok_kemik_ekle.py   tag 0, uc track'in de BASINA
  -> yama_ycd.py             bes alanlik vanilla sozlesmesi (asagida)
  -> xml_to_ycd.ps1          binary
  -> GERI OKU ve calisan referansla alan alan karsilastir
```

Yama adımının ölçtüğü beş alan (5 vanilla sözlük / 27 klip, **istisna
yok**): `anim.Hash` = klip adı · `clip.Name` = `pack:/<ad>.clip` ·
`clip.Unknown30` = 1 · `anim.Unknown10` = 1 · `clip.Properties` = tek öge.
⛔ Bu adım hattın parçasıdır; "elle hizalarım" deyip atlanınca
`clip.Properties` eksik kaldı ve bir tur kaybedildi.

`Unknown1C` **türetilmez** — crane'de `anim.Hash+1`, stilthouse'ta ilgisiz.
Kural çıkarılamadı, olduğu gibi bırakılır.

---

## 5. Sessiz kıran DÖRT BAĞ

Dördü de hata vermez. Dosya derlenir, doğrulama "1 klip" der, oyunda
**hiçbir şey olmaz**.

**Bağ A — `.ycd` `BoneId` = iskelet `Tag`.**
Eşleşmezse kanal sessizce düşürülür, kemik rest'te kalır. Sollumz'un
otomatik tag formülü vanilla tag'leri üretmez → kemiğin
`Bone Properties → Sollumz → Tag` alanını **elle yaz**
(`use_manual_tag = True` + `manual_tag`).

**Bağ B — klip adı = model adı = arketip adı.**
RayFire'da üçü **aynıdır**. `.yed`/expression reçetesindeki *"klip adı model
adıyla AYNI OLMAMALI"* kuralı **buraya ait değildir** — o kural fragment +
expression yoluna aittir. Bu iki kuralı karıştırmak bir kez tur boyu yanlış
teşhise yol açtı.

**Bağ C — bbox animasyonun TAMAMINI kapsamalı. İKİ AYRI YERDE.**
Sollumz rest pozunun kutusunu yazar. Vanilla `des_stilthouse_root` kutusu
(−16.96, −5.76, −7.68)…(22.92, 26.67, 11.20) — evin kendisinden çok daha
geniş, çünkü çöküş oraya kadar gidiyor. Rest kutusu bırakılırsa obje uzakta
titrer ve kaybolur.

⛔ **Kutu iki ayrı yerde durur ve İKİSİ de düzeltilir:**
```
.ydr  Drawable/BoundingBoxMin,Max + BoundingSphereCenter,Radius   <- Sollumz rest yazar
.ytyp arketip bbMin,bbMax + bsCentre,bsRadius                     <- ayri alan
```
Bu yaşandı: köprüde yalnız `ytyp` düzeltildi, drawable'ınki rest kaldı
(`x` −44.75 iken animasyon −53.38'e gidiyordu) ve kusur sürdü. Crane
hattında ikisi de yazılmış. Uzanım Blender'da kare taranarak ölçülür,
üstüne ~0.6 m pay konur.

**Bağ D — ⛔ KEMİK BAYRAKLARI. Sollumz `Flags` alanını YAZMAZ, sıfır bırakır.**
Bayrağı sıfır olan kemik **hiçbir dönüşüm kabul etmez**; klip oynar, kemik
kımıldamaz.

| dosya | dağılım |
|---|---|
| vanilla `des_stilthouse_root` | `119`×55, `1911`×42, `7`×4, kök `4215` |
| `des_crane_root` (çalışıyor) | `119`×50, kök `4215` |
| **Sollumz çıktısı (bozuk)** | **`0`×N, kök `4096`** |

### ⛔ `119` BİR SABİT DEĞİL, BİR İZİN KÜMESİDİR — klibin sürdüğü track'e göre seçilir

Bit tablosu (Sollumz `flags_enum`'dan okundu, tahmin değil):

| bit | 1 | 2 | 4 | 16 | 32 | 64 | 256 | 512 | 1024 | 4096 |
|---|---|---|---|---|---|---|---|---|---|---|
| ad | RotX | RotY | RotZ | TransX | TransY | TransZ | ScaleX | ScaleY | ScaleZ | Unk0 |

- `119` = `Rot*|Trans*` → **Scale biti YOK**
- `1911` = `119 | Scale*` → üçü de serbest
- `4215` = `119 | Unk0`, `6007` = `1911 | Unk0` → kök kemiğe `Unk0` eklenir

Klip track'i ile bayrak eşleşmek zorundadır: **Track 0 = translation,
Track 1 = rotation, Track 2 = scale.** Bayrağın izin vermediği track
**sessizce atılır** — dosya sağlam, klip oynuyor, hata yok, o kemik durur.

⛔ **BU MADDE BİR TUR YAKTI, SEBEBİ TAM OLARAK BU ÖZETİN KENDİSİYDİ.**
Yukarıdaki tabloda vanilla `des_stilthouse_root`'un **`1911`×42** taşıdığı
yazılıydı; buna rağmen "kök 4215, diğerleri 119" özeti okundu ve bir
jumpscare drawable'ına 119 yazıldı. O klibin tamamı **bone scale** ile
sürülüyordu (84 sarmaşık kemiği 0.001→1). Sonuç: kapılar (rotasyon)
oynadı, sarmaşıklar (scale) **hiç** oynamadı, konsolda hata çıkmadı.
Otomatik düzeltme aracı da 119 yazdığı için kendisi
kusurun **kaynağı** oldu.

**Kural: bayrağı klipten türet, tablodan kopyalama.** Klip hangi
track'leri kullanıyorsa o bitler açık olmalı; emin değilsen `1911`
(kök `6007`) yaz — fazladan izin zararsızdır, eksik izin sessizdir.

**Kapı:** bir denetim adımı (betiği public sürümde yok)
`.ycd`'nin kullandığı her track'i iskelet bayrağına karşı denetler ve
"N kemikte scale kanalı var ama BAYRAK İZİN VERMİYOR" der. Negatif testle
doğrulandı.

**Bu, katalogdaki en yanıltıcı belirtidir** ve bir günü yakmıştır:
```
PlayEntityAnim        -> 1          klip BULUNDU
animTime              0 -> 0.994    klip OYNUYOR
GetRayfireMapObjectAnimPhase ilerliyor
mesh                  REST POZUNDA  hicbir kemik kimildamiyor
konsolda hata         YOK
```
Oyunda görünen şey: sağlam hâl → (hiçbir şey) → enkaz. "Animasyon
oynamıyor" diye okunur ama klip kusursuz çalışmaktadır.

**Kural: her animasyonlu `.ydr` export'undan sonra bayrak denetlenir.**
Denetim ve otomatik düzeltme betiği public sürümde yok.

---

## 5b. Oyunda teşhis merdiveni — "animasyon oynamıyor" dendiğinde

Sırayla, ve **her basamağı atlamadan**. Bu merdiven olmadan alan alan diff
çekmek turlarca kaybettirir (yaşandı: sekiz tur).

**1. Çalışan bir referansı tetikle** (`rfyik crane` / `rfyik stilthouse`).
Oynuyorsa composite yolu, ytyp kaydı, imap takası, sunucu tarafı **sağlam**;
kusur senin `.ydr`/`.ycd` ikilindedir. Oynamıyorsa asset'i kurcalama, ortama
bak. — ⛔ *Dosyaların diskte durması çalıştığı anlamına gelmez; "referans"
diye kullanacağın asset'in oyunda oynadığı **doğrulanmış** olmalı.*

**2. `rfmanuel <hedef>`** — composite'i devre dışı bırakıp modeli spawn eder,
klibi `PlayEntityAnim` ile oynatır. Çıktıyı şöyle oku:

| `animTime` | mesh | teşhis |
|---|---|---|
| 0.000'da çakılı | — | klip BULUNAMADI → Bağ A/B, dict adı, `.ycd` hash'leri |
| ilerliyor | **kımıldamıyor** | **Bağ D (kemik bayrağı) ya da Bağ C (bbox)** |
| ilerliyor | kımıldıyor | ikili sağlam → kusur composite/ytyp/imap tarafında |

**3. ⛔ İki sayıya teşhis dayandırma.**
`GetRayfireMapObjectAnimPhase` **bir sayaçtır** — klip yüklü olmasa bile
ilerler. `animTime` ilerlemesi de yalnız klibin *bulunduğunu* söyler,
kemikleri sürdüğünü **söylemez**. Bu iki yanlış çıkarımın ikisi de yapıldı.

**4. Durum makinesi basamak atlatmaz.** Durum `3` iken doğrudan `6` yazmak
**reddedilir** (okunan `3`'te kalır, faz 0.000). Doğrusu: `4` yaz →
durumun **oturmasını bekle** (sabit 100 ms değil, değişimi gözle) → `6`.
Motor `7`'ye alır. Tetiklemeden önce `RequestAnimDict` şart; sözlük yüklü
değilse model rest pozunda kalır ve belirti Bağ D ile birebir aynı görünür.

---

## 6. Collision — durum tabanlıdır, animasyonu TAKİP ETMEZ

- Animasyonlu `.ydr`'de `Bounds` düğümü **yoktur**. Düşerken çarpışma yoktur.
- Collision **duruma** aittir: sağlam halin kendi bound'u, enkazın kendi
  bound'u. Vanilla bunu ymap başına dünya-uzayı `.ybn` ile taşır
  (`imapstart_1.ybn`, `imapend_1.ybn` — Composite/GeometryBVH).
- Custom üretimde daha az kırılgan eşdeğer yol: durum `.ydr`'lerine
  **gömülü** Bound Composite (Sollumz'da composite'i drawable'ın çocuğu yap)
  + arketipte `physicsDictionary = model adı`. Doğrulandı.

**Bu yüzden `SetEntityCollision` / `FreezeEntityPosition` /
`DoorSystemSetOpenRatio` gibi script hileleri burada hep ters teper:**
sistem zaten durum tabanlıdır, script'in kovalayacağı bir çarpışma yoktur.

### Gömülü bound üretimi — ölçülmüş sınırlar ve sıra

Sollumz'da kurulum: `sollumz_bound_composite` (EMPTY, drawable'ın çocuğu)
→ altına `sollumz_bound_geometry` (MESH). Mesh'i görsel mesh'in kopyası
yapmak yeterli; ayrı collision modellemeye gerek yok.

⛔ **`sollumz_bound_geometrybvh` KULLANMA.** Sollumz o tipte mesh'i okumuyor,
export `Bound GeometryBVH 'x' has no geometry!` deyip çöküyor. Çalışan tip
`sollumz_bound_geometry`.

⛔ **Sert vertex tavanları** (ikisi de export'ta hata olarak çıkar):
```
sollumz_bound_geometry (non-BVH)   max 16.383 vertex
BVH bound                          max 32.767 vertex
```
Ve dönüşüm oranı sezgisel değil: **bound vertex ≈ mesh vertex × 1.52**
(ölçüldü: 11.396 mesh → 17.283 bound). 1.42 diye tahmin edip iki tur
başarısız export aldım. Hedefi mesh tarafında **~9.500 vertex**'e kurmak
güvenli bant veriyor (→ ~14.400 bound).
Aşıyorsa `DECIMATE` modifier ile seyrelt — collision'da bu kayıp görünmez.

Materyal: `bpy.ops.sollumz.createcollisionmaterial()` bir `DEFAULT`
materyali üretir (**seçili obje ister**, yoksa "No objects selected" deyip
hiçbir şey yapmaz). Sonra `mat.collision_properties.collision_index` ile
gerçek materyali seç (beton = **1**, tablo `collision_materials.tsv`).
Tüm yüzleri tek collision materyaline indirmek yeterli.

⛔ **`physicsDictionary` boş kalırsa gömülü bound motora HİÇ bağlanmaz.**
Arketipte model adının kendisi yazılır. Bound taşımayan arketipte ise boş
bırakılır — var olmayan bir sözlüğü işaret etmek yeni bir hata kaynağıdır.

### ⛔ SIRA: önce KENDİ collision'ını koy, sonra vanilla'yı kes

Vanilla collision `physicsDict = 0` olan arketiplerde **dünya uzayı `.ybn`**
içindedir; entity'yi ymap'ten silmek görüntüyü kaldırır ama **çarpışmayı
bırakır** — çöküşten sonra havada yürünür. Kesmek gerekir, ama vanilla'yı
önce kesersen sağlam hâl de delik olur ve içinden düşülür.

Ölçülmüş dağılım (köprü dilimi, üçgen merkezi dilim içinde):
```
hw1_rd_10.ybn   546 poligon  z 78..84   kopru tablasi + yol yuzeyi
hw1_rd_9.ybn     44 poligon  z 80..84   dilimin kenari
hw1_10_0.ybn     75 poligon  z >= 70    ayaklar/govde
hw1_10_0.ybn    260 poligon  z 56..70   CUKUR ZEMINI -- DOKUNULMAZ
```
Not: `.ybn` içinde poligon ararken **üçgenin üç köşesi de** bölge içinde
şartı koyma — tablanın büyük üçgenleri sınırı aşar ve sayım "deck collision
yok" der. **Üçgen merkezini** kullan.

---

## 7. ymap'ler

```
des_X_imapstart : ymap flags 1  contentFlags 577 (HD 1 + Physics 64 + Critical 512)
des_X_imapend   : ymap flags 1  contentFlags 65  (HD + Physics)
yerleştirici    : ymap flags 0  contentFlags 65

entity kalıbı (üçünde de):
  flags 1572864 · parentIndex -1 · LODTYPES_DEPTH_ORPHANHD · PRI_REQUIRED
  lodDist -1 (arketipinkini kullan)  — yerleştiricide 100
```

`des_stilthouse`'ta üçüncü bir ymap daha var: `_rebuild` (85 entity) —
onarılmış hal. Zorunlu değildir.

`.ytyp` **kayıt edilmek zorundadır**, stream'e koymak yetmez:
```lua
files { 'stream/des_X.ytyp' }
data_file 'DLC_ITYP_REQUEST' 'stream/des_X.ytyp'
```
Kaydolmazsa hem ymap entity'leri hem `compositeEntityTypes` **sessizce**
hiç oluşmaz.

---

## 8. Sollumz sapmaları ve yama listesi

Sollumz 2.9 ile ölçüldü. Export'tan sonra bunların hepsi düzeltilmelidir:

| # | Sollumz yazıyor | olması gereken |
|---|---|---|
| 1 | `pack:/pack:/x.clip` (çift önek) | `pack:/x.clip` |
| 2 | `Unknown30 = 0` | `1` |
| 3 | `Tags` / `Properties` blokları **hiç yok** | `Properties` 1 Item (Int 32) |
| 4 | `Unknown10 = 0` | `1` |
| 5 | `BoneIds` yalnız Track 0+1 | Track 2 de (`StaticVector3 1,1,1`) |
| 6 | bbox = rest pozu | animasyonun tam uzanımı |

Düzeltme adımları: klip alanları vanilla sırasıyla yeniden kurulur · Track 2
blokları `SequenceData`'ya eklenir · kök kemiğin (tag 0) üç kanalı her track
grubunun başına yazılır. Betikler public sürümde yok.

### Diğer Sollumz tuzakları (hepsi yaşandı)

- **`sz_lods.high.mesh` atanmamışsa export "has no Sollumz materials!" der
  ve drawable'ı komple atlar.** Materyal aslında oradadır; Sollumz
  materyalleri `child.sz_lods.get_lod(...)` üzerinden okur. Yeni oluşturulan
  mesh objelerinde bu alan **None** kalır → `ob.sz_lods.high.mesh = ob.data`.
- `bpy.ops.object.select_all(DESELECT)` MCP bağlamında seçimi sessizce
  bozar → `bpy.context.temp_override(...)` kullan.
- `pose_bone.matrix_basis`'i doğrudan hesaplarken kemik ekseni tuzağı:
  Sollumz kemiklerinde local Y = head→tail yönüdür, dünya eksenleri değil.
  Doğru formül: `basis = L.inverted() @ M @ L` — `M` istenen **dünya** rijit
  dönüşümü, `L = bone.matrix_local`. `basis = L.inverted() @ M` yazmak
  kemik başında bir dönüşe dönüşür ve kare 0'da bile geometriyi bozar.

### `.ytyp` / `.ymap` XML'ini ELLE YAZMA — üretici betik kullan

Bir `des_*` seti **bir ytyp + üç ymap** ister ve dördü birbirine guid/ad/
extent üzerinden bağlıdır; elle yazınca bağlardan biri sessizce kopar.
Depoda iki çalışan üretici var, ikisi de **desen A** (imap takası) içindir:

| betik | ne üretir |
|---|---|
| `scripts/uret_crane.py <klasör>` | `des_crane` — alanları `des_stilthouse`'tan ölçülmüş referans üretici |
| `scripts/uret_kopru_meta.py <klasör>` | `des_kopru` — §11'deki **kalıcı geometri ayrımı** uygulanmış hâli (`_kalan` placer'da) |

Yeni bir `des_X` için bunlardan birini kopyala; konum, ad ve entity listesi
dışında hiçbir alanı **değiştirme**. Çıktı XML'dir → `meta_xml_to_bin.ps1`.

### `.ytyp` / `.ymap` binary üretimi

Sollumz bunları binary yazamaz, `xml_to_res.ps1` de desteklemez. Kullan:
`XmlMeta::GetData(doc, MetaFormat.RSC, folder)` (bkz. `meta_xml_to_bin.ps1`).

⛔ **İkisi de `MetaFormat.**RSC**` üzerinden yazılır — enum'da `ytyp`/`ymap`
diye bir üye ARAMA.** Bu yaşandı: enum'da bulamayınca "CodeWalker bu yolu
yazamıyor" sonucuna varıldı, composite terk edildi ve script tabanlı
(`CreateObject` + `PlayEntityAnim`) yanlış yola geçilerek turlar kaybedildi.
Araç zaten çalışıyordu.

⛔ **`YtypFile.Save()` `compositeEntityTypes` bloğunu SESSİZCE DÜŞÜRÜR**
(ölçüldü: 925 → 836 bayt, composite 0). XML yolu düşürmez. Bir ytyp'i
`Load` + `Save` ile "dokunmadan" yeniden yazmak composite'i yok eder.

---

## 9. Oyuna girmeden ne test edilir

Merdivenin tamamı: `govde/dogrulama-merdiveni.md`. Bu sisteme özgü kesişim:

**Test edilebilir (saniyeler):**
- Klibin kemikleri gerçekten sürdüğü — derlenmiş `.ycd`'yi CodeWalker.Core ile
  faz başına değerlendirmek Bağ A'yı ve ölü kuyruğu yakalar (araç public sürümde yok).
- Bağ A/B/C'nin üçü de dağıtılmış dosyalar üzerinde XML geri okumasıyla
  denetlenir (tag kümesi eşitliği, klip Hash'i, bbox ⊇ animasyon kutusu).
- Hareketin estetiği — Blender zaman çizelgesi / viewport render.

**Test EDİLEMEZ (oyun şart):**
- Composite durum makinesi, imap takası, `punchIn/Out` zamanlaması
- Streaming, `DLC_ITYP_REQUEST` ile ytyp kaydı
- Collision davranışı

**Asset değiştikten sonra sunucudan tamamen ÇIKIP yeniden bağlan** —
restart yetmez, yoksa bayat asset test edilir.

---

## 10. Hata kataloğu — yaşananlar

1. **Fragment (`.yft`) ile denemek.** RayFire kökü `.ydr`'dir. `.yft`'te
   `PlayEntityAnim` `animTime`'ı 0.000'da bırakır.
2. **`compositeEntityTypes` bloğunu hiç yazmamak** → arketipler kaydolur,
   composite yoktur, `GetRayfireMapObject` 0 döner.
3. **`.yed` + Expression extension eklemek.** RayFire'da yoktur; o zincir
   fragment/expression yolunun parçasıdır. Eklemek zarar verir.
4. **Klip adını model adından farklı yapmak** (Bağ B'nin tersi).
5. **`physicsDictionary`'yi doldurmak** — vanilla kökte boştur.
6. **`rootN`'i ymap'e koymak / elle spawn etmek** → artık RayFire değil.
7. **Reçeteleri karıştırmak.** Bir turda asset `des_stilthouse`'un skinned
   mesh'i + `my_vauldr`'ın fragment ambalajı olmuştu; her iki reçete de
   tek başına doğruydu, melez çalışmadı. **Bir reçete seç ve sonuna kadar
   onu uygula.**

---

## 10b. Vanilla'yı kaldırma — gizleme DEĞİL, silme ya da taşıma

Kendi yıkımını vanilla bir yapının yerine koyuyorsan vanilla entity
kalkmalı; yoksa ikisi üst üste biner ve yıkım "hiç olmamış" görünür.
**Bütün LOD katmanları + `hei_` ikizleri** yamalanır (`X_strm_N`, `X_long_N`,
`X` içindeki `_lod`).

⛔ **Entity bayrağıyla gizleme (`bit22 Disable shadow` + `bit23 Disable
entity`) KULLANILMAZ.** Ölçüldü: HD entity gizlenince motor onun **LOD
kabuğunu** çizmeye başlar — ekranda dokusuz, düz, tek renk üçgen yüzeyler
belirir ve bu "modelimiz bozuk" diye okunur. Kabuk zaten kaba geometridir.

İki doğru yol var:

| yol | ne yapar | ne zaman |
|---|---|---|
| **sil** | entity'yi `entities`'ten çıkar, **`parentIndex`** kaydır ve ebeveynin **`numChildren`**'ını düşür | kalıcı temizlik |
| **taşı** | entity'yi 600 m aşağı al | indeksleri hiç bozmaz, geri alınabilir |

### ⛔ SİLMEDEN ÖNCE İKİ SORU — üçü de yaşandı, üçü de dünyada delik açtı

**1. Entity'nin kapsamı senin modelinin AYAK İZİNİN içinde mi?**
*"Bu vanilla objeyi modelimize birleştirdik"* demek *"tamamını kapsıyoruz"*
demek **değildir** — birleştirme sırasında yalnız kesişen kısım alınmış olur.
Ölçüt tek satır: `pozisyon + arketip bbMin/bbMax` senin kapsamının içinde mi.

Ölçülmüş vaka (köprü, kapsam `x 664…869, y −113…41`):
```
fwy_04_splita03   y −322 … −143   DISARI   -> silinince otoyol yok oldu
fwy_04_splita02   y  +60 … +178   DISARI
fwy_04_splita     y  −50 …  +85   DISARI
hw1_rd_02_17      x 664 …  784    icinde   -> silinmesi guvenli
```
Dışarı taşan **yapısal** geometri silinmez; ya bırakılır ya da vanilla'nın
kalan kısmı kendi drawable'ın olarak üretilir (crane'deki "yol eksi çöken
dilim" yöntemi).

**2. Bu entity yapı mı taşıyor, yoksa yalnızca decal mi?**
`_ovly` / decal entity'leri **her durumda silinebilir** — eksikliği delik
değil, yalnız leke/çizgi eksikliğidir. Ölçüldü: 4 `fwy_04_rd_*_ovly` hepsi
`parentIndex = −1` (öksüz, LOD ebeveyni yok) ve `lodDist` 62–89.
Ama dikkat: aynı decal **yol çizgilerini de** taşıyabilir
(`im_roadmarkings*`, `im_roadblends*`) — silince yol yamalı görünür.

**3. Çocuğu kalmayan LOD'u yerinde bırakma.**
HD entity silinince ebeveyni `numChildren = 0` kalır ve o LOD **her mesafede
çizilmeye başlar**. Belirti: "yol/zemin hâlâ duruyor" ya da dokusuz düz
yüzeyler. Ölçülmüş: `fwy_04[53,56,58,68]`, `hw1_rd[237,238]`,
`hw1_10[3,4]` — hepsi `LODTYPES_DEPTH_LOD`, `lodDist` 350–500.
Ve ayrı bir tuzak: `hw1_10_land03_a` gibi `_a` sonekli **orta mesafe**
varyantlar zeminin **pişmiş kir dokusunu** taşır; "zemin" diye etiketleyip
geçme, ne çizdiğine bak.

### ⛔ ymap YAZMANIN İKİ YOLU VAR VE HANGİSİNİN KAYIPSIZ OLDUĞU DOSYAYA GÖRE DEĞİŞİR

| yol | ne zaman |
|---|---|
| `XmlMeta.GetData` (XML turu) | çoğu ymap'te kayıpsız, **ama hepsinde değil** |
| `YmapFile.RemoveEntity` + `YmapFile.Save()` | binary üzerinde, ölçülen vakada kayıpsız |

Ölçüldü — `hw1_rd_critical_1.ymap`, **dosyaya hiç dokunmadan** yapılan XML
turu: **457 entity → 128**. Aynı dosyada `Save()` turu: **457 → 457**.
Dağıtılsaydı bölgedeki **325 obje** (ağaç, tabela, trafik ışığı, çöp kutusu)
sessizce yok olurdu; araç hata vermiyor, "başarılı" diyor.

**Kural: her ymap yazımından sonra kaynak entity sayısıyla karşılaştır.**
`meta_xml_to_bin.ps1` artık bunu kendisi yapıyor ve tutmazsa çıktıyı siler.

### ⛔ Vanilla prop'u kendi modeline GÖMME

Sokak lambası, çöp kutusu gibi vanilla prop'ları `.ydr`'ine katmak dokuyu
bozar: dokuları kendi `.ytd`'lerindedir (`prop_streetlight_01.ytd`), modele
gömerken o sözlük gelmez ve materyaller yanlış dokulara düşer — ölçülen
vakada lamba kırmızı-beyaz çizgili çıktı. Prop'a ihtiyacın varsa
**vanilla entity'yi olduğu yerde bırak** ya da **ymap'ten sil**; geometrisini
kopyalama.

Silerken indeks onarımı zorunludur: üst ymap'ten bir entity çıkınca çocuk
ymap'lerdeki `parentIndex` değerleri **bir kayar** ve sessizce yanlış
entity'yi gösterir. Ölçülmüş örnek (`hw1_10`):
```
hw1_10.ymap[9]  = hw1_10_bridge01_lod   silindi
                  -> ebeveyn[0].numChildren 6 -> 5
hw1_10_strm_0   parentIndex > 9 olan 3 entity  -> -1
hw1_10_long_0   parentIndex > 9 olan 1 entity  -> -1
```
Doğrulama: her ymap'te entity sayısı korunmalı (silinen hariç) ve hedef
arketip hash'i **0 kez** geçmeli.

⛔ **Extent'e dokunma** (§1.6): entity çıkarmak extent'i değiştirmez.

---

## 10c. ⛔ ÖLÇÜM TUZAKLARI — hepsi bu sistemde yaşandı, hepsi SESSİZ

Bu bölümdeki her madde bir turu, bazıları bir günü yaktı. Ortak yanları:
araç hata vermiyor, makul görünen **yanlış bir sayı** dönüyor.

**`MetaHash` ≠ `UInt32`.** `entity._CEntityDef.archetypeName` bir `MetaHash`'tir;
`UInt32` anahtarlı bir hashtable'da `ContainsKey($archetypeName)` **hiçbir zaman
eşleşmez** ve "kalıntı 0" diye okunur. Açık çevrim şart:
`[uint32]$en._CEntityDef.archetypeName`. Bir doğrulama turunu bu yüzden
tamamen boşa harcadım — "temiz" dediğim dosyalar ölçülmemişti.

**PowerShell değişkenleri büyük/küçük harf DUYARSIZ.** Döngüde kullanılan
`$y` (YmapFile), yedek klasörü değişkeni `$Y`'yi ezdi ve yedek yanlış yola
yazılmaya çalışıldı. Kısa değişken adı + döngü = bu hata.

**`"$S\$n.ymap"` yanlış yol üretir** — PowerShell `$n.ymap`'i property erişimi
sanar, boş döner. `"$($n).ymap"` ya da `Join-Path` kullan.

**`@(@(x,y))` tek elemanlıysa DÜZLEŞİR.** Tek koordinatlık liste `@(x,y)`'ye
dönüşür, `$k[0]`/`$k[1]` saçmalar ve eşleşme sessizce kaçar. Ölçülen vakada
silinecek çöp kutusu 1.1 m ötede duruyordu, "0 silindi" dendi.

**`bpy` `bound_box` BAYAT olabilir.** `mesh.transform()` sonrası
`ob.bound_box` eski değeri döndürür; dönüşüm uygulanmış olsa bile
"uygulanmamış" gibi görünür. Kutuyu **vertex'lerden** hesapla.

**Izgara örneklemesi yanlış soruyu sorabilir.** "Zemin var mı" diye 20 m
adımlı ızgara attım, 100/100 nokta doldu ve "boşluk yok" dedim — oysa ızgara
noktalarının hepsi yol/köprü yüzeyine denk gelmişti, zeminin olmadığı yerler
hiç örneklenmemişti. Ölçüm doğruydu, **soru yanlıştı**.

**⛔ Ve en pahalısı: EKRAN GÖRÜNTÜSÜ ÖLÇÜM DEĞİLDİR.** Bu oturumda üç kez
karelere bakıp yanlış teşhis koydum (bir kez "boşluk var" dedim, yoktu; bir
kez "boşluk yok" dedim, vardı). Bir şeyin bozuk olduğunu söylemeden önce
**oku**: dosyayı, entity sayısını, geri okumayı.

---

## 11. Kalıcı geometri ile durum geometrisini AYIR

Bir `des_*` işinde çoğu zaman üç ayrı şey vardır:

| ne | nereye | neden |
|---|---|---|
| sağlam hâl | `StartImapFile` | durum makinesi kapatır |
| enkaz | `EndImapFile` | durum makinesi açar |
| **kalıcı zemin / çevre** | **placer ymap'i** (composite'in yanına) | hiçbir duruma ait değil |

⛔ **`start` imap'ine SADECE çöken dilim konur, tüm yapı değil.**
İkinci kez yaşandı, bu sefer daha büyük ölçekte: `start`'a 205 × 154 m'lik
**köprünün tamamı** konmuştu, `end`'de ise yalnız 82 × 69 m'lik enkaz vardı.
Tetiklenince `start` kapanıyor ve o 205 metrenin **hepsi** yok oluyor; geri
gelen sadece enkaz. Belirtiler tek tek şikâyet olarak geldi ve hiçbiri
birbirine benzemiyordu:
```
korkuluklar kayboldu · yolda delik acildi · decal'lar havada kaldi
```
Hepsinin tek sebebi buydu. Doğru bölme:
```
placer (HEP ACIK)   composite  +  <ad>_kalan     yikilmayan her sey
start  (kapanir)    <ad>_saglam                  cöken dilimin saglam hali
end    (acilir)     <ad>_enkaz                   enkaz
```
`_saglam` = animasyonun **kare 0'ının statik export'u** (crane'de de öyle).
`_kalan` = birleştirilmiş modelin, çöken dilim **çıkarılmış** hâli.

⛔ **Kalıcı geometriyi durum imap'lerine koyma.** Yolun yıkılmayan kalanını
`start` ve `end`'in ikisine birden koymuştum; `start` kapanıp `end` henüz
açılmadığı anda **ortada yol kalmıyor**, altından gökyüzü görünüyor.
Belirti: bölgenin tamamı boşluk. Doğru yeri her zaman açık olan placer.

```
des_crane_start    ['des_crane_saglam']
des_crane_end      ['des_crane_enkaz']
des_crane_placer   ['des_crane', 'des_crane_yol', 'des_crane_ov']   <- kalici
```

### ⛔ imap EXTENT'İNİ HESAPLA

Kendi ürettiğin ymap'te extent elle yazılmış bir kutudan gelmemeli;
**entity'lerin birleşiminden** hesaplanmalı. Extent içinde kalmayan entity
**sessizce hiç görünmez**, hata da vermez.

Ölçüldü:
```
des_crane_start  beyan z 28.6..43.8   gercek z 28.6..108.9  -> saglam vincin 65 m'si DISARIDA
des_crane_end    beyan z 28.6..43.8   gercek z 28.6.. 48.8  -> enkazin 5 m'si DISARIDA
```

Aynı şey arketip kutusu için de geçerli: `des_X_root`'un kutusu
**animasyonun tamamını** kapsamalı (tüm karelerde tüm parçaların birleşimi),
yalnız rest hâlini değil.

### guid deterministik olsun

`abs(hash(ad))` kullanma — Python'un string hash'i süreç başına rastgele
tohumlanır, her üretimde başka guid yazar. Jenkins kullan.

---

## 12. Bind pozu ve iskelet bağı — kurtarma reçetesi

### Bind pozu = dünya rest − ORIGIN

Animasyonlu `.ydr`'nin içindeki vertex'ler **sağlam hâlin** koordinatlarıdır
(drawable uzayında). Hareketi oyunda `.ycd` sürer. Yani:

- `des_X_saglam` ve `des_X_root` **aynı geometriyi** taşır
- `des_X_enkaz` = aynı geometri, parça başına son kare dönüşümü uygulanmış

### ⛔ Parça hareketini `pose_bone.matrix`'ten TÜRETME

Sollumz kemiklerinde yerel Y = head→tail'dir; poz matrisinin **dönüşü
parçanın dünya dönüşü değildir**. Ölçüldü: `Translation(ORIGIN) @ pose.matrix`
parçanın **konumunu doğru**, **oryantasyonunu 90° yanlış** verir. Oyunda
direk yatay, kol dikey çıktı.

⛔ **bbox kapısı bu hatayı YAKALAMAZ** — parçalar kendi merkezleri etrafında
döndüğü için birleşim kutusu makul görünür. Kapıyı **oryantasyona** kur:
bilinen bir parçanın bilinen bir kenarının yönünü ölç, ya da §12'deki
kemik-merkezi karşılaştırmasını yap.

### Blender'ın armature modifier'ı bozuk olabilir — dosya bozuk demek değil

Ölçüldü: aynı sahnede `pose @ bone.matrix_local⁻¹` elle uygulandığında
bind ve çökmüş kutuların **ikisi de birebir** çıkıyor, ama armature
modifier'ının çıktısı 500+ m saçılıyor. Oyunda çalışan `.ycd` sağlamdı.

**Ders:** viewport'a değil, **elle hesaba ve dağıtılmış dosyaya** güven.
Elle dönüşüm doğru sonucu veriyorsa asset üretilebilir; modifier'ı düzeltmeye
uğraşmak gereksiz.

### Doğru grup→kemik eşlemesini ÇALIŞAN `.ydr`'den kurtar

Ağırlıklar mesh'te grup **indeksiyle** saklanır; objenin grup listesi
yeniden yaratılırsa isimler indekslere yanlış oturur ve parçalar birbirinin
hareketini alır. Kurtarma:

1. Çalışan `.ydr`'yi XML'e dök; `BlendIndices` + `Position` oku.
2. Kemik indeksi başına **vertex merkezi** çıkar (iskelet sırası = indeks).
3. Blender'da her grubun vertex merkezini hesapla, en yakın kemikle eşle.
4. İki aşamalı yeniden adlandır (önce `__t_` öneki, sonra gerçek ad).

Ölçüm: eşleşme medyanı **0.093 m**, 50/50 grup 0.5 m altında.

**Kapı:** yeni `.ydr` ile çalışan `.ydr`'nin kemik başına vertex merkezlerini
karşılaştır. Vinç kemiklerinde sapma medyan **0.040 m** çıktı; geometrisini
bilerek değiştirdiğim plakalarda sapma büyük olması normaldir.

### ⛔ Vertex grubunu silmek ağırlığı siler

`km.data = yeni_mesh` sonrası `vertex_groups.remove(...)` yaparsan mesh'in
ağırlık verisi gider. Export "42586 vertex hiçbir gruba ağırlıklı değil"
uyarısı verir. Mesh'i ata, grupları **silme**.

---

## 13. İş disiplini — bu turda en pahalı iki ders

### ⛔ BLEND'İ KAYDET

Bir günlük Blender çalışması yalnızca export edilmiş `.ydr`'lerde vardı;
`.blend` diskte **26 saat eskiydi**. Blender kapanınca hafızadaki hareket
tabloları (`_hedef`, `_sim_M0`) da gitti ve iş baştan kuruldu — üstelik
yanlış kuruldu (§12). Her export'tan sonra `bpy.ops.wm.save_mainfile()`.

Hafızada tutulan ara veri (`bpy._X`) kalıcı değildir. Kalıcı olması
gerekenler ya `.blend`'e ya diske yazılır.

### Son çalışan çıktıyı SAKLA

`cikti2/` klasöründeki dün akşamki `.ydr`'ler yüzünden bozuk dağıtımdan
tek komutla dönülebildi. Her doğrulanmış sürümü tarihli bir klasöre kopyala;
geri dönüş yolu olmadan üretim yapma.

### Ekran görüntüsü teşhis değildir

Bu turda üç kez ekrandaki desene bakıp yanlış teşhis kondu (çakışan
plakalar sanıldı → aslında dönük eksen hizalı kutuların doğal örtüşmesiydi;
çözülemeyen doku sanıldı → aslında `cpv_only`; materyal sanıldı → aslında
normal). Belirti nereye bakılacağını söyler, **sebebi ölçüm söyler**.

## 14. Parçalama — yıkımın "yıkım gibi" görünmesini belirleyen üç ölçü

Bir yapıyı hücrelere bölüp her hücreye rijit dönüşüm vermek doğru yöntem,
ama **hücre boyutu ve katman ayrımı sonucu belirler.** Üçü de ölçüldü
(115 × 72 m'lik bir köprü bölgesi, 20 bin yüz).

### a. Zeminden kaldırma kelepçesi çöküşü İPTAL EDER

Parçalara "yere batmasın" diye `if zmin < TABAN: yukarı taşı` kelepçesi
konulduğunda ve bir parça hem **güverteyi hem ayağı** içeriyorsa, ayağın
tabanı zaten zemine yakın olduğu için kelepçe parçanın tamamını geri
kaldırır. Ölçülen sonuç: üst yüzey düşüşü **medyan 4.1 m**, 24 parçanın
17'si 8 m'den az düştü, ikisi **yükseldi**. Gözle "köprü yıkılmıyor".

**Doğrusu yatay bir düzlemle katmanlara ayırmaktır** (burada z=77):
güverte katmanı serbestçe **18-20 m** düşer, altyapı katmanı **düşmez,
devrilir** (25-60° eğim, 2-8 m). Ayak batmaz — ayak *devrilir*.
Ölçüm: medyan düşüş 4.1 → **18.9 m**, en az düşen parça 12.1 m.

### b. Görünen "yırtılma"nın ölçütü kenar uzunluğudur, üçgen oranı değil

Gerilmiş üçgen **oranına** bakmak yanıltır: vanilla köprünün kendisi de
%14 çıkar, "sorun yok" denir. Rijit parçada gerilme matematiksel olarak
zaten imkânsızdır; gözle görülen şey **parçanın kendi içindeki uzun
kenarın dönerken süpürdüğü alandır**.

| ızgara | parça çapı (medyan) | en uzun kenar | >30 m parça |
|---|---|---|---|
| 23 m hücre (44 parça) | 30.7 m | 16.2 m (maks 25.5) | 23/44 |
| **11 m hücre (88 parça)** | **21.8 m** | **7.3 m** (maks 19.2) | **2/88** |

Hedef: en uzun kenar **medyan < 8 m**. Hücre sınırlarında `bisect_plane`
ile kesmek şart — yüzleri sadece merkezine göre hücreye atamak, hücreyi
aşan yüzü olduğu gibi bırakır ve tek üçgen 60 m'ye uzanır.

### c. Küçük hücreyi silme, komşuya kat

25 yüzden az hücreler ayrı parça yapılırsa iskelet gereksiz şişer ve
sliver parçalar uçuşur. Aynı katmandaki en yakın büyük hücreye eklenir.
88 parça + el + kök = **90 kemik** sorunsuz export edildi.

### d. Yeniden kurarken sıra sabittir

Parça listesi değişince **her şey** yeniden üretilir ve hiçbiri
atlanamaz: enkaz (boolean) → armature → root mesh + ağırlıklar →
animasyon → **klip sözlüğü** → export → `.ycd` yaması → ytyp kutuları →
dağıtım. Klip sözlüğü eski armature data-block'una bakmaya devam ederse
export `AssertionError: The armature bone-map is required at this point`
verir — hiyerarşiyi silip `create_clip_dictionary` ile **sıfırdan** kur;
`target_id`'yi elle düzeltmek yetmez.

## 15. Kesilmiş yüzey — geometri kapanır, UV ve materyal de düzeltilir

Bir vanilla parçasını kesip enkaza çevirirken üç ayrı kusur çıkar ve
**üçü de ayrı ölçütle** yakalanır. Ölçüldü (115 × 72 m köprü, 78 bin üçgen).

### a. Sıra: temizle → KES → kalınlaştır → parçala → delik kapat

`remove_doubles` / `dissolve_degenerate` **hücre kesiklerini geri eritir**.
Temizliği kesimden sonra yaparsan en uzun kenar 19.3 m'den **88.6 m**'ye
fırlar ve tek üçgen sahneyi boydan boya süpürür. Sıra bozulunca hiçbir
denetim uyarmaz; kenar uzunluğunu her adımdan sonra ölç.

Vanilla yol/zemin **tek yüzlü kabuktur**: parçalara ayrılınca açık kenar
oranı **%51,1**. Devrilen levhanın arkası görünür — bu "yırtılma" diye
raporlanır. `SOLIDIFY` (0.6 m, `offset=-1`) + parça başına `holes_fill`
ile kesik yüzeyleri kapanır: **%51,1 → %3,8**.

Bağsız vertex ölçümü kirletir: `bmesh.ops.delete(context='FACES')` yüze
bağlı olmayan vertexleri bırakır, parça çapı **22.5 m yerine 106.9 m**
okunur. Ölçmeden önce `context='VERTS'` ile temizle.

### b. UV: alan oranı YETMEZ, anizotropi ölç — ve n-gon'u üçgenle

`uv_alan / dünya_alan` **alan koruyan gerilmeyi göremez**: u ekseninde 10×
uzayıp v'de 10× daralan üçgenin oranı değişmez. Bu ölçütle "düzeldi"
denildi, ekranda sürtme izleri sürdü. Doğru ölçüt **Jacobian'ın tekil
değer oranıdır** (`s0/s1`).

Ayrıca ölçüm yüzün **ilk üç loop'unu** alıyorsa `holes_fill`'in ürettiği
n-gon'ların geri kalanı hiç ölçülmez. Önce `triangulate`, sonra ölç.
Ölçüldü: n-gon'lu ölçüm "medyan 1.13, >3x %0.0" derken üçgenlenmiş ölçüm
aynı meshte **>3x %11,4** buldu.

### c. UV ölçeği MATERYAL BAŞINA alınır, tek küresel medyan olmaz

Yeniden yansıtırken tüm yüzlere tek `uv/m` vermek yol dokusunu araziye,
araziyi yola giydirir. Hedef ölçek **dokunulmamış vanilla parçasının**
aynı materyaldeki iyi (anizotropi < 2) yüzlerinin medyanından alınır.
Ölçülen vanilla değerleri birbirinden kat kat farklı:
`im_road_001` **0.172 uv/m** (5.8 m'de tekrar) · `rn_tf_canyonrock_009`
**0.087** (11.5 m). Tek sayı kullanmak ikisinden birini bozar.

### d. Kesik yüzeyi kaynağın materyalini MİRAS ALIR — beton ver

Solidify yan duvarı ve delik kapatma yüzü, kesildiği yüzün materyalini
taşır: dik bir duvarda **yol çizgisi** ya da **çim** dokusu belirir.
Ölçüt basit ve ölçülebilir: `|n.z| < 0.55` **ve** materyal adı
yol/zemin ailesinden → yapının kendi betonu (`hw10_bridge1_rn_rk_main`),
zeminse kaya (`rn_tf_canyonrock_009`). Ölçüldü: %10,1 üçgen → %0,00.

### e. ⛔ İki render'ı farklı mesafeden karşılaştırma

"Vanilla'da damalar sık, bizde çubuk" diye UV bozuk sanıldı; iki çekim
farklı mesafedeydi. Ölçüm ikisinin de aynı bantta olduğunu söylüyordu:
uv/m vanilla **0.216** · bizim **0.178**; anizotropi >3x vanilla **%7,5**,
bizim **%0,3**. Kontrol çekimi **aynı hedef, aynı mesafe, aynı lens**
olmadan kontrol değildir. (§13'ün aynısı: ekran görüntüsü ölçüm değildir.)
