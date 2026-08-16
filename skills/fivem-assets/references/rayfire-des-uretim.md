# RayFire / `des_*` yıkım sistemi — üretim hattı

**Ne zaman:** bir bina, kule, ağaç, iskele ya da herhangi bir harita
yapısının **koreografili** yıkılması istendiğinde. Fragment kırılması
(`prop_*` cam/tahta parçalanması) DEĞİL — o başka sistem. Buradaki sistem
"sağlam hal → oynatılan çöküş animasyonu → enkaz hali" üçlüsüdür.

Kaynak: vanilla `des_stilthouse` **alan alan** açıldı (ytyp, ycd, 8 ydr,
3 ymap, 6 ybn, yerleştirici ymap) ve birebir kopyası (`des_mutotest`)
üretilip oyunda çalıştığı doğrulandı. Buradaki sayıların hiçbiri tahmin
değildir. Çapraz kontrol: `des_protree`, `des_apartmentblock`,
`des_tvsmash`, `des_farmhouse`.

Sorgu: `assetdb.py show des_*` · `res_to_xml.ps1` · `cw_anim_check.ps1`

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

---

## 5. Sessiz kıran ÜÇ BAĞ

Üçü de hata vermez. Dosya derlenir, doğrulama "1 klip" der, oyunda
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

**Bağ C — bbox animasyonun TAMAMINI kapsamalı.**
Sollumz rest pozunun kutusunu yazar. Vanilla `des_stilthouse_root` kutusu
(−16.96, −5.76, −7.68)…(22.92, 26.67, 11.20) — evin kendisinden çok daha
geniş, çünkü çöküş oraya kadar gidiyor. Rest kutusu bırakılırsa obje uzakta
titrer ve kaybolur. Bütün karelerde min/max ölçüp `.ydr` XML'ini yamala.

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

Betik: `scratchpad/yama_ycd_A.py` kalıbı (klip alanlarını vanilla sırasıyla
yeniden kurar, Track 2 bloklarını `SequenceData`'ya ekler).

### Diğer Sollumz tuzakları (hepsi yaşandı)

- **`sz_lods.high.mesh` atanmamışsa export "has no Sollumz materials!" der
  ve drawable'ı komple atlar.** Materyal aslında oradadır; Sollumz
  materyalleri `child.sz_lods.get_lod(...)` üzerinden okur. Yeni oluşturulan
  mesh objelerinde bu alan **None** kalır → `ob.sz_lods.high.mesh = ob.data`.
- `.ycd` Sollumz'un format sisteminin **dışındadır** → `target_formats` ne
  olursa olsun XML çıkar → `xml_to_ycd.ps1`.
- `Animation.target_id` **armature DATA-BLOCK** olmalı (`arm.data`), Object
  değil; Object verilirse 0 kemik kanalı yazılır.
- `bpy.ops.object.select_all(DESELECT)` MCP bağlamında seçimi sessizce
  bozar → `bpy.context.temp_override(...)` kullan.
- Blender sahnesi Sollumz import'undan sonra 24 fps'te kalır → `fps = 30`.
- `pose_bone.matrix_basis`'i doğrudan hesaplarken kemik ekseni tuzağı:
  Sollumz kemiklerinde local Y = head→tail yönüdür, dünya eksenleri değil.
  Doğru formül: `basis = L.inverted() @ M @ L` — `M` istenen **dünya** rijit
  dönüşümü, `L = bone.matrix_local`. `basis = L.inverted() @ M` yazmak
  kemik başında bir dönüşe dönüşür ve kare 0'da bile geometriyi bozar.

### `.ytyp` / `.ymap` binary üretimi

Sollumz bunları binary yazamaz, `xml_to_res.ps1` de desteklemez. Kullan:
`XmlMeta::GetData(doc, MetaFormat.RSC, folder)` (bkz. `meta_xml_to_bin.ps1`).

---

## 9. Oyuna girmeden ne test edilir

Merdivenin tamamı: `oyuna-girmeden-dogrulama.md`. Bu sisteme özgü kesişim:

**Test edilebilir (saniyeler):**
- Klibin kemikleri gerçekten sürdüğü — `cw_anim_check.ps1 -Ycd x.ycd
  -Clip <ad> -Tags @(tag,…)` derlenmiş `.ycd`'yi CodeWalker.Core ile
  değerlendirir, faz başına konum/açı basar. Bağ A'yı ve ölü kuyruğu yakalar.
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
   mesh'i + `muto_vauldr`'ın fragment ambalajı olmuştu; her iki reçete de
   tek başına doğruydu, melez çalışmadı. **Bir reçete seç ve sonuna kadar
   onu uygula.**

---

## 11. Kalıcı geometri ile durum geometrisini AYIR

Bir `des_*` işinde çoğu zaman üç ayrı şey vardır:

| ne | nereye | neden |
|---|---|---|
| sağlam hâl | `StartImapFile` | durum makinesi kapatır |
| enkaz | `EndImapFile` | durum makinesi açar |
| **kalıcı zemin / çevre** | **placer ymap'i** (composite'in yanına) | hiçbir duruma ait değil |

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
