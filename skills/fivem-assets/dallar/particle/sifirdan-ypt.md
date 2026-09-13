# Sıfırdan `.ypt` partikül üretimi — sayfa, keyframe yuvaları, transplant, hareket zarfı

**Ne zaman okunur:** kendi partikülünü yazacaksın (kıvılcım, damla, enerji, duman): doku sayfası, `C4`, keyframe yuvaları, donör transplant, `FxcFileHash`, hareketin nereden geldiği; "handle dolu ama ekranda yok".
**When to read:** authoring a `.ypt` from scratch — page, keyframe slots, transforms, the silent failures.
**Kaynak:** `ptfx-flipbook-uretimi.md` §1-6, §8, §13 · `govde/bayraklar.md` §7c-7d (2026-08/09) · **Ölçüm:** `core.ypt` 45,5 MB açıldı; 107 gömülü doku DXT; 15 aile oyunda; sayfa bölünmesi görsel kanıtla
**Önce:** `dallar/particle/_dal.md` · gövde › `govde/arac-tuzaklari.md` §3 CodeWalker (`FxcFileHash`, `VFT`, `ResourcePointerArray64`) · katalog/aile üretimi `katalog.md` · katmanlı efekt `katmanli.md`

---
## `.ypt` yapısı ve gerçek XML şeması (`core.ypt`'den)

Kaynak: JulioNIB, *"Creating and editing a new particle effect based on an
existing one"* (35 dk). Yapı iddiaları CodeWalker tipleriyle **doğrulandı**.

### `.ypt` yapısı — beş sözlük

`ParticleEffectsList` (kök) şunları taşır, ve **özel efekt üretirken beşi de
yeni dosyaya taşınır**:

| Sözlük | İçerik |
|---|---|
| `EffectRuleDictionary` | efektin kendisi; her biri **event emitter** listesi |
| `EmitterRuleDictionary` | emitter kuralları — **spawn rate** keyframe'leri |
| `ParticleRuleDictionary` | particle kuralları — **renk/boyut/hız** keyframe'leri |
| `DrawableDictionary` | efektin kullandığı modeller (çoğu efekt kullanmaz) |
| `TextureDictionary` | efektin kullandığı dokular |

Bir efekt birden çok **event emitter** taşıyabilir (ölçüldü: `bang_carmetal`
6 tane). **Her event emitter için** hem emitter rule hem particle rule ayrı
ayrı kopyalanmalı.

### Hat

1. Efektin bulunduğu `.ypt`'yi bul → `assetdb.py fx <ad> --exact` söyler.
2. CodeWalker ile **XML'e export** et.
3. **Yeni bir dosya aç** — vanilla `.ypt`'yi düzenleme; başka modları bozar.
   Uzantı `.<ad>.ypt.xml` biçiminde olmalı (XML'den önce asset uzantısı).
4. Beş sözlüğün **açılış/kapanış etiketlerini** yeni dosyaya kopyala.
5. Efekt tanımını, sonra **her event emitter'ın** emitter+particle rule'unu bul
   ve ilgili sözlüğe yapıştır.
6. Kullanılan **drawable ve texture** girdilerini de kendi sözlüklerine kopyala.
7. Dosyanın tepesindeki **asset adını** ve efekt adını değiştir — oyunda
   çağıracağın ad budur.
8. ⛔ **Dosyayla aynı adda bir KLASÖR oluştur ve doku dosyalarını içine koy.**
   Yoksa import "texture bulunamadı" ile başarısız olur. (Videoda bu adım
   unutuldu ve iki kez hata verdi.)
9. CodeWalker ile geri import et.

### ✅ GERÇEK XML ŞEMASI — `core.ypt` açılıp okundu (45,5 MB)

Kök **birebir beş sözlük** (video doğru):
```xml
<ParticleEffectsList>
  <Name>core</Name>
  <EffectRuleDictionary>   <EmitterRuleDictionary>
  <ParticleRuleDictionary> <DrawableDictionary>  <TextureDictionary>
```

**Efekt → emitter bağı ADLA kurulur**, indeksle değil:
```xml
<EffectRuleDictionary><Item>
  <Name>_fog_foundry</Name>
  <PlaybackDelay value="2"/> <PlaybackSpeedScale value="1"/>
  <CullRadius value="2"/>    <CullDistance value="-4"/>
  <EventEmitters><Item>
    <EmitterRule>_fog_foundry_core</EmitterRule>
    <ParticleRule>_fog_foundry_core</ParticleRule>
    <MoveSpeedScale value="1"/> <ParticleScale value="1"/>
  </Item></EventEmitters>
</Item></EffectRuleDictionary>
```

### EMITTER RULE — 10 keyframe özelliği (gerçek adlar)

Alanlar: `Name` · `Domain1` · `Domain2` · `KeyframeProperties`

| Ne için | `<Name>` değeri |
|---|---|
| **daha çok/az partikül (zamana göre)** | `ptxEmitterRule:m_spawnRateOverTimeKFP` |
| daha çok/az partikül (mesafeye göre) | `ptxEmitterRule:m_spawnRateOverDistKFP` |
| **ekranda kalma süresi** | `ptxEmitterRule:m_particleLifeKFP` |
| oynatma hızı | `ptxEmitterRule:m_playbackRateScalarKFP` |
| **ne kadar uzağa gitsin** | `ptxEmitterRule:m_speedScalarKFP` |
| boyut | `ptxEmitterRule:m_sizeScalarKFP` |
| ivme | `ptxEmitterRule:m_accnScalarKFP` |
| sönümleme | `ptxEmitterRule:m_dampeningScalarKFP` |
| matris ağırlığı | `ptxEmitterRule:m_matrixWeightScalarKFP` |
| hız devralma | `ptxEmitterRule:m_inheritVelocityKFP` |

### ⛔ Keyframe alan adları YANILTICI

```xml
<Keyframes><Item>
  <InterpolationInterval value="0"/>
  <KeyFrameMultiplier value="0"/>
  <RedChannelColour value="4"/>    <GreenChannelColour value="7"/>
  <BlueChannelColour value="0"/>   <AlphaChannelColour value="0"/>
</Item></Keyframes>
```

`*ChannelColour` adları **genel amaçlı dört kanaldır**, renkle ilgisi yoktur.
`m_spawnRateOverTimeKFP` içinde `RedChannelColour=4` demek "spawn oranı 4"
demektir. `m_xyzMinKFP` içinde Red/Green/Blue = **X/Y/Z**'dir.
Bu isimlendirme CodeWalker'ın kendi seçimi; alanın anlamı **hangi
`<Name>` altında olduğuna** bağlıdır.

### PARTICLE RULE — davranış listesi

Alanlar: `Name` · `FxcFile` · `FxcTechnique` · `Spawner1/2` · **`Behaviours`** ·
`ShaderVars`

`Behaviours` içindeki `<Type value="…"/>` değerleri (`core.ypt` sayımı):

| Type | Adet | Type | Adet |
|---|---:|---|---:|
| Age | 1596 | AnimateTexture | 721 |
| Velocity | 1596 | Collision | 253 |
| **Size** | 1596 | Wind | 245 |
| **Colour** | 1596 | Noise | 119 |
| Sprite | 1444 | Model | 114 |
| Acceleration | 1289 | ZCull | 103 |
| Dampening | 1144 | Light | 65 |
| MatrixWeight | 1110 | Trail · Attractor · Decal · | |
| Rotation | 1109 | DecalPool · FogVolume · Liquid · River | tek haneli |

### RENK — gerçek alan adları

```
ptxu_Colour:m_rgbaMinKFP            (1596 particle rule'un hepsinde)
ptxu_Colour:m_rgbaMaxKFP
ptxu_Colour:m_emissiveIntensityKFP
```

Burada `RedChannelColour`/`Green`/`Blue`/`Alpha` **gerçekten** renktir.
Diğer sık kullanılan özellikler: `ptxu_Size:m_whdMinKFP` / `m_whdMaxKFP`
(genişlik-yükseklik-derinlik) · `ptxu_Rotation:m_angleMinKFP` / `Max` ·
`ptxu_Acceleration:m_xyzMinKFP` / `Max` · `ptxu_Light:m_rgbMinKFP` / `Max`.

⚠ **Hâlâ [DOĞRULANMADI]:** rengi script'ten değiştirilebilir yapan bayrağın
hangi alan olduğu. Video "bir değişken"den bahsediyor ama adını söylemiyor;
`Colour` behaviour'unun `Unknown*` alanlarından biri olması muhtemel.
`SetParticleFxColour` çalışmıyorsa sebep budur.

## Üretim zinciri — CodeWalker.Core yazar, uçtan uca çalışıyor

**Sürüm: CodeWalker 30_dev46, `CodeWalker.Core.dll` 2023-12-13.**
Bu sürümle sıfırdan `.ypt` üretildi, oyun formatında kaydedildi ve geri
okunarak doğrulandı. Daha yeni sürüme, .NET SDK'ya ya da GUI'ye **gerek yok**.

Doğrulanmış hat:

```
make_dds.py          -> 128x128 A8R8G8B8 sprite (kendi urettigimiz)
build_custom_ptfx.py -> .ypt.xml (efekt/emitter/particle kurallari sifirdan)
XmlYpt.GetYpt()      -> nesne agaci
YptFile.Save()       -> 7.865 bayt RSC7
YptFile.Load()       -> geri okuma: butun adlar + doku yerinde
```

### ⛔ ÖNCE BU: "ölçtüm, yok" demeden ÖNCE property adını doğrula

Bu bölümün önceki hâli **"CodeWalker `.ypt` YAZAMAZ"** diyordu. Yanlıştı, ve
tek sebebi vardı: **var olmayan property adları okundu.**

| Okuduğum | Gerçek | Sonuç |
|---|---|---|
| `EffectRuleDictionary.Effects` | `.EffectRules` | `$null.Length` → **0** |
| `PtfxList.EffectRuleDict` | `.EffectRuleDictionary` | `$null` |
| `AllEffects` | yalnız `Load()` doldurur, `GetYpt()` doldurmaz | 0 |

PowerShell olmayan bir property'ye erişince **hata vermez, `$null` döner**;
`$null.Length` de `0`'dır. Yani ölçüm aleti sıfır gösterdi ve ben bunu verinin
sıfır olduğu sanıp saatlerce yanlış yönde ilerledim, hatta belgeye
"imkânsız" diye yazdım. (Bu, CLAUDE.md §2'nin aynısı: **aracın bir şeyi
göstermemesi o şeyin yok olduğu anlamına gelmez.**)

Refleks olsun: yabancı bir DLL'i sorgularken önce
`$obj.GetType().GetProperties() | % Name` yaz, ya da guard kullan —

```powershell
function P($o,$ad){
  if(-not $o.PSObject.Properties[$ad]){ throw "PROPERTY YOK: $($o.GetType().Name).$ad" }
  $o.$ad }
```

### ⛔ Sessiz çöküşün gerçek sebebi: EKSİK BIRAKILAN KEYFRAME YUVASI

`Save()` içindeki `NullReferenceException`
(`ResourceBuilder.AssignPositions` → `ResourceSystemBlock.set_FilePosition`)
neredeyse her zaman **eksik yazılmış bir `KeyframeProperty` yuvasıdır.**

Her davranış tipinin yuva sayısı **sabittir ve hepsi yazılmalıdır**.
Yazılmayan yuva null blok bırakır; XML sorunsuz ayrışır, sözlükler dolu
okunur, hata bir adım sonra `Save()`'de gelir ve **hangi yuva olduğunu
söylemez.**

`core.ypt`'teki **15.430 davranışta** ölçüldü — her tip TEK bir yuva sayısı
gösteriyor, istisna yok:

| KFP | Davranış tipleri |
|---:|---|
| 0 | `Age` · `Velocity` · `Sprite` · `DecalPool` · `Liquid` · `Model` · `River` |
| 1 | `MatrixWeight` · `AnimateTexture` · `Wind` · `Trail` · `Attractor` |
| 2 | `Acceleration` · `Dampening` · `Collision` · `ZCull` · `Decal` |
| 3 | `Colour` |
| 4 | `Size` · `Rotation` · `Noise` |
| 7 | `FogVolume` |
| 9 | `Light` |

Yuva `<Name>`'leri gerçek şemadır (1736/1736 sabit):

- `Size` → `m_whdMinKFP` · `m_whdMaxKFP` · `m_tblrScalarKFP` · `m_tblrVelScalarKFP`
- `Colour` → `m_rgbaMinKFP` · `m_rgbaMaxKFP` · `m_emissiveIntensityKFP`
- `Rotation` → `m_initialAngleMinKFP` · `m_initialAngleMaxKFP` · `m_angleMinKFP` · `m_angleMaxKFP`

`<Unknown6C>` ise **sabit değil**: dosya içi konumdur, yuva başına 256 artar
(Size KFP0 için 331 farklı değer ölçüldü). İstediğin tabandan başlat.

**`Velocity`'nin 0 yuvası olması hata değil.** Parçacık hızı davranışta
değil, **emitter** kuralının `speedScalar`'ında ve creation/target
domain'lerinde tanımlanır. Velocity'ye keyframe yazmaya çalışmak `Save()`'i
çökerten en kolay yoldur.

### ⛔ Diğer iki zorunlu blok

- **`EventEmitters/Item/UnknownData`** — içeriği boş olabilir, ama **var
  olmalı**: `<UnknownData><EventEmitterFlags /><Unknown10 /></UnknownData>`.
  Yoksa aynı `Save()` çöküşü.
- **`Sprite`** davranışı 0 keyframe alır ama `Unknown30 34 38 40 44 48 4C
  50 54 58 5C 60` alanlarının hepsini ister (`5C` = `0x100`).

### Üretim hattı — hangi betik ne yapar

**Normal üretim tek komuttur**, ara adımları elle çalıştırma:

```powershell
scripts\ptfx_yap.ps1 -Ad my_spor -Renk 0.2,0.9,0.35 -Hedef <stream klasoru>
scripts\ptfx_yap.ps1 -Ad my_x -Gorsel kendi.png -Boyut 0.4 -Yukselme 0.8 -Hedef <k>
```

Doku → XML → ikili → eksik alanları tamamla → doğrula → dağıt.

| Betik | İş |
|---|---|
| `ptfx_yap.ps1` | **giriş noktası** — hattın tamamı |
| `make_dds.py` | DXT5/DXT1 + mip zincirli DDS (`--kaynak` ile hazır PNG'den) |
| `build_custom_ptfx.py` | sıfırdan efekt/emitter/particle kuralı XML'i |
| `ypt_xml_to_bin.ps1` | XML→ikili + **CodeWalker'ın atladığı alanlar** + doğrulama + dağıtım |
| `ypt_transplant.py` | **teşhis**: çalışan vanilla efekti kopyalayıp tek değişken değiştirir |
| `make_test_sheet.py` | **teşhis**: hücreleri farklı şekilli test sheet'i |
| `make_butterfly_sheet.py` | kanat çırpma sprite sheet'i (prosedürel, tutarlı kareler) |
| `ptfx_onizleme.py` | derlenmiş `.ypt`'nin verisinden animasyonlu önizleme (motor çıktısı DEĞİL) |
| `build_ptfx.ps1` | vanilla efekt kataloğunu indeksler (`assetdb.py ptfx/fx`) |

⛔ `XmlYpt.GetYpt` + `Save()`'i **elle çağırma** — `ypt_xml_to_bin.ps1`
olmadan dosya shader'sız ve VFT'siz çıkar, oyunda sessizce bozulur.

### ⛔⛔ CodeWalker XML okuyucusu `VFT` de YAZMAZ — sınıf kimliği sıfır kalır

`FxcFileHash` ile aynı sınıf hata, ama daha geniş: XML'den üretilen bir
`.ypt`'de **hiçbir bloğun `VFT`'si yazılmaz**, hepsi `0` çıkar. `VFT`
nesnenin sınıf kimliğidir (vtable); sıfırsa motor bloğun türünü çözemez.

Ölçüldü — `core.ypt`'te her tip **tek** değer taşıyor, sıfır sapma:

| Blok | Örnek | VFT |
|---|---:|---|
| Texture | 107/107 | `1080137320` |
| EffectRule | 964/964 | `1080081688` |
| EmitterRule | 1993/1993 | `1080083608` |
| ParticleRule | 1736/1736 | `1080085192` |
| EventEmitter | 2543/2543 | `1080100952` |
| KeyframeProp | 4820/4820 | `1080085392` |
| EffectRuleDict / EmitterRuleDict / ParticleRuleDict | 1 | `1080048016` / `1080048056` / `1080048096` |

Davranışlar tip başına tek değer: `Age 1080067288 · Velocity 1080075080 ·
Size 1080074648 · Colour 1080070168 · Sprite 1080076760 · AnimateTexture
1080068072 · Acceleration 1080066920 · Rotation 1080073832 · Dampening
1080070840 · MatrixWeight 1080071352 · Noise 1080072136 · Wind 1080075768 ·
Model 1080077240 · Trail 1080078056 · Collision 1080069256 · Attractor
1080068456 · ZCull 1080175704 · Decal 1080170408 · DecalPool 1080170920 ·
FogVolume 1080172152 · Light 1080174040 · Liquid 1080174872 · River
1080175208`

Domain'ler şekil başına: `Sphere 1080088936 · Box 1080088880 ·
Cylinder 1080088992 · Attractor 1080089048`

**`ShaderVars` girdilerinin de kendi VFT'si var** — ve doku bağını kuran
nesne budur (`Type=Texture`). Atlanması kolay, çünkü davranış listesinde
değil ayrı bir listede:

| ShaderVar tipi | Örnek | VFT |
|---|---:|---|
| `Texture` | 5108/5108 | `1080097544` |
| `Vector2` | 18846/18846 | `1080097368` |
| `Vector4` | 1686/1686 | `1080097368` |
| `Keyframe` | 10216/10216 | `1080097256` |

`Vector4` ile `Vector2` aynı VFT'yi paylaşır.

`scripts/ypt_xml_to_bin.ps1` hepsini yazar ve sıfır kalırsa **exit 1**.

### Parçacığı HAREKET ettiren şey: target domain'in konumu

⛔ `Velocity` davranışının **0 keyframe yuvası** vardır — oraya hız
yazılmaz. Yükselen duman/spor **`Domain2` (target domain) konumuyla**
yapılır: parçacık creation domain'de doğar, target domain'e doğru gider.

Ölçüldü: vanilla emitter'ların **%89,2**'sinde
`ptxTargetDomain:m_positionKFP`'nin Z'si sıfırdan farklı, **medyan +0.400**.
İki domain de aynı merkezdeyse net yön oluşmaz ve efekt yerinde durur.

`m_speedScalarKFP` yönü değil **hızı** verir (vanilla medyanı 0.85).

### ⛔ `m_zoomScalarKFP` efektin TÜM uzamsal ölçeğini sürer

Sadece parçacık boyutunu değil; yayılım, mesafe, boyut hepsi birden.
Oyunda ölçüldü: 338 olan değeri boşaltınca efekt her boyutta çöktü ve
`whd` keyframe'lerini **50×** çarpmak bunu telafi etmedi.

Vanilla'da değer efektin büyüklüğüyle ölçekleniyor: minik hapşırık
efekti `0.75`, dev gaz sütunu `1200`, **medyan 51.8**, %77,2'si dolu.
Boşaltmak meşrudur (%22,8'i boş) ama efekti küçültür.

### ⛔ AÇIK SORUN: GÖMÜLÜ dokuda sprite sheet DİLİMLENMİYOR

Bu **çözülmedi.** Bir sonraki oturum sıfırdan aramasın diye ölçümler burada.

Oyunda ölçülen tablo — hepsi **aynı particle rule**, tek değişken doku:

| Test | Doku | Sonuç |
|---|---|---|
| `vs2` | vanilla sheet, `core.ypt`'ten **isimle** | **tek hücre** ✅ |
| `dict` | vanilla sheet isimle + dosyada gömülü sözlük de var (kullanılmıyor) | **tek hücre** ✅ |
| `van` | **aynı vanilla dokunun ham verisi**, bizim dosyaya gömülü | dört hücre ❌ |
| `test3` | bizim ürettiğimiz DDS, gömülü | dört hücre ❌ |

Okunuşu:

- Motor **gerçekten dilimliyor** — `ptfx_grass_blades` (sheet olmayan, şekli
  tartışılmaz vanilla doku) doğru çizildiği için dış doku çözümünün
  çalıştığı da kanıtlandı; yani `vs2`'nin tek hücresi yedek doku değil.
- **Bizim DDS kodlamamız masum** — `van` vanilla'nın ham verisini taşıyor
  ve o da başarısız.
- **Gömülü sözlüğün varlığı masum** — `dict` sözlük dosyada dururken
  sorunsuz dilimliyor.
- Kusur, kuralın **gömülü bir dokuya bağlanması** durumunda ortaya çıkıyor.

Denenip **elenen** düzeltmeler (hepsi gerçek eksikti, düzeltildi, ama
belirtiyi çözmedi): `FxcFileHash` · blok `VFT`'leri · `FileVFT` ·
`ShaderVar` VFT'leri · `UsageFlags` · DXT1/DXT5 · mip derinliği.
Doku nesnesi vanilla ile **alan alan aynı** (`UsageData` dahil), doku
sözlüğünün hash tablosu tutarlı.

**Sıradaki tek somut yön:** dokuyu kendi `.ypt`'mize gömmek yerine
`core.ypt`'nin doku sözlüğüne eklemek ve kuraldan isimle çağırmak —
`vs2`/`dict` bunun çalıştığını gösteriyor. GTA'daki özel partikül
modlarının mevcut `.ypt` dosyalarını düzenlemesinin sebebi bu olabilir.

⚠ Bu sınır **yalnız sprite sheet animasyonunu** etkiliyor. Tek karelik
özel doku, renk, boyut, ömür, doğum oranı, yayılım ve yükselme gömülü
dokuyla sorunsuz çalışıyor (oyunda doğrulandı).

### ⛔ `m_sizeScalarKFP` BOYUTUN ASIL KOLUDUR — `whd` değil

Oyunda ölçüldü: aynı efektin `whd` keyframe'leri **200×** çarpıldığında
parçacık gözle fark edilir kadar büyümedi; yalnızca `m_sizeScalarKFP`
`0.4437 → 100` yapıldığında **dev boyuta** çıktı.

Yani parçacığı büyütmek isterken `whd`'yi çarpmak boşa kürek. Alanın
matematiksel ölçeği hâlâ çözülmedi (vanilla dağılımı medyan 57.6 ile
yüzde gibi duruyor ama donör 0.4437 ile görünür parçacık üretiyor) —
ama **hangi kolun boyutu sürdüğü** artık deneyle biliniyor.

### ⛔⛔ EN ÖNEMLİSİ: CodeWalker `FxcFileHash`'i YAZMAZ — shader'sız `.ypt`

**Bu bir CodeWalker hatasıdır, senin XML'inin kusuru değil.** XML'den
üretilen **her** `.ypt` shader hash'i sıfır çıkar. Bozulmamış bir vanilla
dosyayla ölçüldü:

| | `FxcFileHash` |
|---|---|
| `cut_arena.ypt` ikili okuma | `246470498` |
| **aynı dosya**, XML turundan | **`0`** |

`FxcFile` **metni** doğru görünür (`ptfx_sprite`), hash sıfırdır ve motorun
baktığı şey hash'tir. Belirti tam olarak şudur ve başka hiçbir denetim
yakalamaz:

- dosya geçerli, `Save()` çöker değil
- `YptFile.Load()` geri okuma turu geçer
- `RequestNamedPtfxAsset` başarılı
- `StartParticleFx*` **sıfırdan farklı handle** döndürür
- **ekranda hiçbir şey olmaz**

Düzeltme JenkHash ile: `GenHash('ptfx_sprite') = 246470498` — vanilla ikili
değerle birebir. `FxcTechniqueHash` vanilla'da da `0`, **ona dokunma**.

```powershell
foreach ($pr in $ypt.PtfxList.ParticleRuleDictionary.ParticleRules.data_items) {
    $pr.FxcFileHash = [CodeWalker.GameFiles.JenkHash]::GenHash([string]$pr.FxcFile)
}
```

Hazır betik: `scripts/ypt_xml_to_bin.ps1` — GetYpt → hash yaz → Save →
geri oku → `FxcFileHash` sıfırsa **çıkış kodu 1**. `.ypt` üretirken
`XmlYpt.GetYpt` + `Save()`'i elle çağırma, bu betiği kullan.

⚠ Aynı sınıftan başka alanlar olabilir: **CodeWalker'ın XML'e yazdığı her
alanı geri okuduğunda aynı değerde bulmasını bekleme.** Yeni bir kaynak
tipinde üretim yaparken ilk iş vanilla bir dosyayı XML'e çıkarıp geri okumak
ve **ikili ile XML turunu alan alan karşılaştırmaktır** — aracın hangi
alanları düşürdüğü ancak böyle görülür.

### ⛔ BİLİNMEYEN ALANA 0 YAZMA

`Unknown*` alanlarına "bilmiyorum, 0 bırakayım" demek sessiz hata üretir.
Ölçüldü — bu değerlerin çoğunda 0 vanilla'da **hiç geçmiyor**:

| EffectRule | En sık | Pay |
|---|---|---|
| `Unknown50` | `0xFFFFFFFF` | 537/964 |
| `Unknown88` | `0x1010100` | 283/964 |
| `Unknown8C` | `0x10004` | 422/964 |
| `UnknownA4` | `50` | 144/964 |
| `UnknownA8` | `60` | 176/964 |
| `UnknownAC` | `10` | 176/964 |
| `UnknownB0` | `30` | 224/964 |

`UnknownA0/A4/A8/AC/B0` mesafe/LOD bandı görünümündedir (0/50/60/10/30) ve
sıfırlanırsa efekt hiçbir mesafede çizilmeyebilir.

| ParticleRule | En sık | Pay |
|---|---|---|
| `Unknown10` | `2` | 1341/1736 |
| `Unknown100` | `2` | 1098/1736 |
| `Unknown108` | `2` | 1347/1736 |
| `Unknown10C` | `0x10100` | **1638/1736 (%94)** |
| `Unknown1D0` | `5` | 890/1736 |
| `Unknown1E8` | `0x101` | 1044/1736 |
| `Unknown220` | `0x2` | 736/1736 |

Kural: bir `Unknown` alanına değer yazmadan önce
`assetdb.py`/`core.ypt` üzerinde **dağılımına bak**; en sık değeri al.

### ⛔ Dosya geçerli ama OYUNDA HİÇBİR ŞEY GÖRÜNMÜYOR — üç sebep daha

Bu üçü `Save()`'i çökertmez, geri okuma turunu geçer, `StartParticleFx*`
**sıfırdan farklı handle** döndürür (yani motor efekti buldu) ve yine de
ekranda hiçbir şey olmaz. Handle'ın dolu gelmesi "çalışıyor" demek değildir;
yalnız **adın bulunduğu** anlamına gelir.

**1. `FxcTechnique` serbest metin değil, kapalı bir listedir.**
`core.ypt`'teki 1.736 particle rule'da yalnız altı değer geçer:

| Teknik | Adet |
|---|---:|
| `RGBA_lit_soft` | 904 |
| `RGBA_lit` | 425 |
| `RGB_lit_soft` | 136 |
| `RGB_lit` | 75 |
| `RGB_soft` | 70 |
| `RGBA_soft` | 30 |

`default` **hiç geçmez.** Yazılırsa shader çözülmez, efekt sessizce
çizilmez. `RGBA` = alfalı doku, `_soft` = derinlik geçişli yumuşak kenar.
`FxcFile` ise yalnız `ptfx_sprite` (1.686) ya da `ptfx_trail` (50).

**2. `m_sizeScalarKFP` YÜZDE ölçeğindedir, kesir değil.**
2.097 keyframe'de ölçüldü: `%5 = 1.0` · **medyan 57.6** · `%75 = 125` ·
`%95 = 297` · max 1000. Yani `1.0` yazmak en alt %5'e düşmektir —
parçacık boyutunun ~%1'i, gözle görülmez. **100 = nötr.**

Aynı yüzde ölçeği `m_accnScalarKFP` (medyan 98.4), `m_dampeningScalarKFP`
(98.6), `m_matrixWeightScalarKFP` (93.8) için de geçerli.
**Ama hepsi değil:** `m_speedScalarKFP` (medyan 0.85),
`m_particleLifeKFP` (1.40) ve `m_playbackRateScalarKFP` (1.20) ~1.0
ölçeğindedir. Alan adına bakıp ölçek varsayma — **ölç**.

**3. Boş bırakılan keyframe yuvası çarpanı SIFIRLAR.**
Yuvanın var olması yetmez, bazılarının dolu olması da gerekir. Hangisinin
boş bırakılabileceği ölçülür:

| Yuva | Vanilla'da boş | Boş bırakılır mı |
|---|---:|---|
| `Size:m_tblrScalarKFP` | %0,5 | ⛔ **HAYIR** — boş = çarpan 0 = sıfır boyut |
| `Size:m_whdMin/MaxKFP` | %0,7 / %0,8 | ⛔ hayır |
| `Colour:m_rgbaMin/MaxKFP` | %0,1 / %0,2 | ⛔ hayır |
| `Size:m_tblrVelScalarKFP` | %83,6 | ✅ evet |
| `Colour:m_emissiveIntensityKFP` | %71,7 | ✅ evet |
| `Emitter:m_matrixWeightScalarKFP` | %99,1 | ✅ evet |
| `Emitter:m_dampeningScalarKFP` | %95,8 | ✅ evet |
| `Emitter:m_particleLifeKFP` | %0,6 | ⛔ hayır |
| `Emitter:m_spawnRateOverTimeKFP` | %3,6 | ⛔ hayır |

Kural: **vanilla'da %5'ten az boş olan yuva zorunludur.**

`CullRadius` / `CullDistance` `0` olması normaldir (869/964 ve 836/964) —
oraya bakma. `Unknown74` **964/964 `0.25`**, sabittir.

### Teşhis yöntemi: BÖLEREK DARALT, blok ağacında gezme

`GetReferences()`/`GetParts()` ağacında null aramak **işe yaramaz** —
`ResourcePointerArray64<T>` foreach'te `NotImplementedException` atar
(CLAUDE.md §9) ve yürüyüş sessizce yanlış sonuç verir.

Çalışan yöntem: vanilla bir `.ypt`'yi XML'e çıkar (bu XML `Save()` turunu
geçer), sonra **tek tek** kendi bloklarınla değiştirip hangisinde çöktüğüne
bak. Sözlük seviyesinde 4 test, sonra bölüm seviyesinde 4 test — sekiz
çalıştırmada kusur bulunur.

### Kaydedilen dosyanın boyutu KÜÇÜK olması hata değil

`Save()` çıktısı RSC7'dir ve **zlib sıkıştırılmıştır**. `cut_arena.ypt`
32.768 bayt açılmış → `Save()` **3.077 bayt**. Daha önce bu farka bakıp
"dosya bozuldu" sonucuna vardım; ölçüt boyut değil, **geri okumadır**:

```powershell
$d=[IO.File]::ReadAllBytes($yol)
$e=[CodeWalker.GameFiles.RpfFile]::CreateResourceFileEntry([ref]$d,0)
$d=[CodeWalker.GameFiles.ResourceBuilder]::Decompress($d)
$y=New-Object CodeWalker.GameFiles.YptFile; $y.Load($d,$e)
```

`YptFile.Load()` **`RpfFileEntry` ister**; `null` geçilirse patlar ve bu da
"dosya bozuk" sanılır.

Geri okumada `Behaviours` **0 görünür — bu kayıp değildir.** İkili yükleme
`BehaviourList1..5`'i doldurur; `Behaviours` XML tarafının toplayıcısıdır.
Vanilla `cut_arena` da aynı şekilde okunur.

### Şema: doku bağı

⛔ **Doku bağı `<Behaviours>` içinde DEĞİL, `<ShaderVars>` içindedir.**
Ölçüldü: `Behaviours` yalnız şu tipleri taşır — `Age Acceleration Velocity
Rotation Size Dampening MatrixWeight Wind Colour Sprite` (+ tablo yukarıda).
`Texture` orada **hiç geçmez**.

⛔ `Texture` girdisinde `<Name>` **doku adı değil, SAMPLER YUVASIDIR**
(`refractionmap` / `normalspecmap` / `diffusetex2`); gerçek doku adı ayrı
bir `<TextureName>` alanındadır. Ters yazılırsa XML ayrışır, **hata çıkmaz,
doku bağlanmaz**:

```xml
<ShaderVars>
  <Item>
    <Type value="Texture" />
    <Name>diffusetex2</Name>       <!-- SAMPLER YUVASI -->
    <Unknown18 value="4" />
    <Unknown3C value="0" />
    <TextureName>my_ptfx_soft</TextureName>   <!-- GERCEK doku adi -->
  </Item>
</ShaderVars>
```

`TextureDictionary` girdisi şunları **zorunlu** ister:
`Name` · `Unk32` · `Usage` (**`DIFFUSE`**, `DEFAULT` değil) · `UsageFlags` ·
`ExtraFlags` · **`Width`** · **`Height`** · **`MipLevels`** · **`Format`** ·
`FileName`. Bunlar eksikse doku sessizce boş kalır.

⚠ DDS dosyaları **XML ile aynı klasörde** olmalı; yoksa
`Texture file not found` ile çöker. (Videodaki "aynı adda klasör aç"
uyarısının gerçek sebebi budur.)

### Partikül SPRITE SHEET animasyonu — `AnimateTexture`

Kanat çırpan böcek, alev, sıçrayan su gibi **kare kare değişen** partiküller
mesh animasyonuyla değil, tek dokuya dizilmiş karelerin UV ile oynatılmasıyla
yapılır. Vanilla'da 781 particle rule bunu kullanıyor.

**`UnknownC4` = kare sayısı − 1** (son karenin indeksi). Çıkarımla değil,
iki bağımsız vanilla dokusu **çıkarılıp gözle sayılarak** doğrulandı:

| Doku | Boyut | Izgara | Kare | `C4` |
|---|---|---|---:|---:|
| `ptfx_smoke_billow_anim_rgba` | 1024×1024 | 6×6 | 36 | **35** |
| `ptfx_water_splashes_sheet` | 512×512 | 2×2 | 4 | **3** |

Izgara **kare**: sütun = satır = √(kare sayısı). Kareler soldan sağa,
yukarıdan aşağıya. `UnknownCC` = `0x1000100` (6×6 sheet'lerin değeri),
`C0` = 0, `C8` = 0. `m_animRateKFP` boş bırakılırsa motor varsayılan hızda
oynatır.

İkisi de **siyah zemin üzerine gri maske** — renk motordan gelir.

⚠ Kare sayısı dokuyla tutarlı olmalı; `build_custom_ptfx.py --sheet N`
tam kare olup olmadığını ve dokunun ızgaraya tam bölündüğünü denetler.

### Partikül 3B MODEL olabilir — `Model` davranışı

Partikül illa sprite olmak zorunda değil. 133 particle rule katı bir mesh
çiziyor; model `.ypt`'nin kendi `DrawableDictionary`'sine gömülü
(`core.ypt`'te **46 model**: mermi kovanı, kar tanesi, yaprak, cam kırığı).
Bağ kuralın içindeki `<Drawables>` bloğunda **isimle** kuruluyor:

```xml
<Type value="Model" />
<Drawables>
  <Name>ptfx_model_pistol_casing/ptfx_model_pistol_casing</Name>
</Drawables>
```

**Sınırı:** model partikülü katıdır — konumlanır, döner, ölçeklenir ama
**iskelet animasyonu oynatmaz.** Kanat çırpma, alev dalgalanması gibi
şekil değiştiren şeyler için `AnimateTexture` yolu kullanılır.

### FiveM özel `.ypt` streaming'i — DOĞRULANDI

Oyunda ölçüldü: `stream/` içine konan özel `.ypt`, dosya adıyla named ptfx
asset olarak kaydoluyor.

```
[ptvarlik] my_spore   yuklendi=1
[ptcal]    handle=29442   0.6 sn sonra yasiyor = 1
```

`data_file` satırı **gerekmiyor**. Doku `.ypt`'ye gömülü, ayrı `.ytd` yok.

⛔ Ama doku **DXT olmalı**: ilk sürüm `A8R8G8B8` (tek mip) idi ve istemci
kaynağın tamamını düşürüyordu — Lua bile yüklenmiyordu. Ölçüm:
`core.ypt`'teki 107 partikül dokusunun tamamı DXT (DXT5 75 · DXT1 32),
mip 4-9; sıkıştırılmamış örnek yok.

⛔ **Bozuk bir stream varlığı kaynağın TAMAMINI düşürür ve sessizdir.**
Sunucu `Started resource X` yazar; istemcide hiçbir komut kaydolmaz,
hiçbir print çıkmaz, F8'de hata da yoktur. Lua'ya hiç sıra gelmez.
Teşhis: `stream/` klasörü **olmayan** ikinci bir kaynak kur — onun komutu
çalışıyorsa kusur stream varlığındadır.

⛔ Stream dosyası ekleyip çıkardıktan sonra **o kaynağı `restart` et**.
Sunucu dosya listesini kaynak başlarken tarar; restart edilmezse istemciye
artık var olmayan bir dosya vaat edilir ve mount yine düşer. (Bu tam olarak
yaşandı: dosya silindi, kaynak restart edilmedi, belirti değişmedi.)

### Oyunda kullanım — iki ayrı ad

**VARLIK adı = `.ypt` DOSYA adı** (`RequestNamedPtfxAsset`),
**EFEKT adı = `EffectRule`'un `<Name>`'i** (`StartParticleFx*`).
Aynı olmak zorunda değiller ve genelde değildirler.

`.ypt` için `data_file` satırı **gerekmez** — `stream/` içindeki dosya adıyla
kendiliğinden named ptfx asset olarak kaydolur.

⛔ `UseParticleFxAssetNextCall` **her** `Start` çağrısından önce tekrarlanır;
adı üstünde, yalnız bir sonraki çağrı için geçerlidir. Bir kez çağırıp
döngüye girmek sessizce vanilla varlığına düşer.



---

## 6. Doğrulama — geri okuma zorunlu

### ⛔ `foreach` ile `ResourcePointerArray64` gezme (yine yaşandı)
`foreach($rule in $pr)` kullanan denetim **15/15 "AnimateTexture YOK"**
raporladı; aynı dosyanın davranış listesi indeks döngüsüyle okununca
`AnimateTexture` oradaydı. `$ErrorActionPreference='SilentlyContinue'`
hatayı yutunca sonuç sessizce yanlış çıkar. **İndeks döngüsü kullan.**

### Yapısal kapı (her `.ypt` için)
- her partikül kuralında `ParticleBehaviourAnimateTexture` var mı
- `Unknown_C4h` == kare − 1
- `EffectRules` ≥ 1, `Textures` ≥ 1
- doku 1024×1024 · `D3DFMT_DXT5` · mip ≥ 5
- **`FxcFileHash` ≠ 0** (CodeWalker XML okuyucusu bunu yazmaz;
  `ypt_xml_to_bin.ps1` düzeltir)

### İçerik kapısı — gömülü dokuyu GERİ ÇÖZ
`Texture.Data.FullData` alınır, 128 baytlık DDS başlığı önüne eklenir,
Pillow ile açılır ve **kaynak PNG ile karşılaştırılır**. DXT5 kaybı normal:
ölçülen **PSNR 36–43 dB**. Gömülü boyut kaynak `.dds`'ten tam **128 bayt**
küçüktür (başlık).

DDS başlığı (DXT5, mip zincirli):
`flags = CAPS|HEIGHT|WIDTH|PIXELFORMAT|MIPMAP|LINEARSIZE`,
`pitch = ceil(w/4)*16`, `pf.flags = DDPF_FOURCC`, `fourcc = "DXT5"`,
`caps = TEXTURE|COMPLEX|MIPMAP`.

### ⛔ Beyaz zemine bindirilmiş partikül YANILTIR
Alfa düşük olduğu için her efekt solgun görünür ve "silik" diye yanlış
teşhis konur. Partikül oyunda koyu/orta tonlu bir dünyanın üzerine çizilir
→ önizlemeyi **koyu zemine** bindir.

### ⛔ "Geri okuma geçti" MOTORUN KABUL ETTİĞİ ANLAMINA GELMEZ

Bu turun en pahalı dersi. 15/15 dosya her yapısal kapıdan geçti — davranış
var, `C4` doğru yazılmış, doku gömülü, hash sıfır değil — ve oyunda
**hiçbiri çalışmadı**. Geri okuma dosyanın *yazıldığını* doğrular;
motorun onu *kullandığını* doğrulayan tek şey oyundur. Bir alana vanilla
bandının dışında değer yazarken "geri okuma doğruladı" cümlesini kanıt
sayma — **dağılıma bak, bandın içinde kal.**

### ⛔ Ekran görüntüsü ölçüm değildir (yine)
Kontakt sayfasına bakıp `ates` "sola kayıp kadraj dışına taşıyor" dedim;
kare başına ağırlık merkezi ölçülünce **cx 0.49–0.54 sabit** çıktı — kayma
yoktu. Ama aynı ölçüm gözün yakaladığı **gerçek** kusuru buldu: kenara
değme. Sayı da ekran da tek başına yetmez; ikisi birden gerekir.

---

## 13. ⛔ HAREKET DEVRALINMAZ, YAZILIR — bu hattın en pahalı hatası

Bir donörden transplant edip **rengi ve dokuyu** değiştirmek efekti bizim
yapmaz. Gözün okuduğu şey **harekettir**; hareket devralınırsa oyunda
görünen şey donörün kendisidir, yeni renkte.

Oyunda görülen ve teşhisi dosyadan doğrulanan üç vaka:

| aile | donör | dosyadaki sebep | oyunda görülen |
|---|---|---|---|
| `cokme_tozu` | `env_dust_devil_rural_lrg` | `ptxAttractorDomain` dış 20.6 / iç 6.8 | **hortum** |
| `bulasma_dalgasi` | `fire_extinguish` | `ptxTargetDomain` 3.5 m yukarı (jet) | halka fışkırtıyor |
| `beton_kirilma` | `ent_ray_fam3_dust_motes` | doğuş hacmi **5×5×1 m kutu** | kıymık 5 m alana saçılıyor |

Üçü de "donör adı ve sayıları uygun görünüyordu" diye seçilmişti; hareketi
hiç ölçmemiştim.

### Ölçülen alan anlamları

| alan | anlamı | örnek |
|---|---|---|
| `ptxCreationDomain:m_sizeOuterKFP` | parçacığın **doğduğu hacim** (m) | damla 1×0.05 düz · toz 5×5×1 |
| `ptxTargetDomain:m_positionKFP` | **yön × mesafe** = hız | damla `[0,0,-4]` · kor `[0,0,0.1]` |
| `ptxu_Acceleration:m_xyzMin/MaxKFP` | yerçekimi / yükseliş | damla `[0,0,-20]` · zemin sisi `[0,0,0]` |
| `ptxu_Dampening` | sürtünme | sis 0.9 · cam 0.05 |
| `<DomainN><Type>` | Box · Sphere · Cylinder · Attractor | **Domain1 = CreationDomain** |

Dağılım (n=231 uygun donör): `CreationDomain` ve `TargetDomain` **%100**,
`Attractor` yalnız **%6** (14 adet) — sarmal/hortum riski oradan gelir.
Davranış birimleri: `Acceleration` %77 · `Dampening` %77 · `Rotation` %62 ·
üçünü birden taşıyan **115 / 231**.

Araç: `ptfx_hareket.py` (`uygula_belge`). Attractor **silinmez, yarıçapı
sıfırlanır** — `<DomainN>` yuvaları konumsaldır, düğüm kaldırmak kalanların
indekslerini kaydırır.

### ⛔ Yazılamayan hareket UYARI değil HATA

Donörün particle rule'unda o davranış birimi yoksa alan sessizce yazılmaz
ve efekt **donörün hareketiyle kalır** — düzeltmek istediğimiz kusurun ta
kendisi. `ent_amb_fbi_falling_debris`'te ne `Acceleration` ne `Dampening`
var; "düşen enkaz"a yerçekimi yazılamıyordu. Üretici artık bunu hata
sayıyor, bu yüzden donör `ent_amb_falling_cherry_bloss` ile değiştirildi
(üç birimi de taşıyor ve zaten süzülerek düşen bir şey).

Bir alan gerçekten gereksizse **anahtarı kaldır** — taşımadığı bir şeyi
istemek yerine. `ent_amb_dust_motes`ta `Acceleration` yok ama spor için
ivme kritik değil; hedef `(0,0,0.15)` yavaş yükselişi zaten veriyor.

### ⛔ `<Name>X</Name>(.*?)</Keyframes>` YAZMA — boş alan komşuyu okutur

Alan boşsa XML'de `<Keyframes />` (kendi kapanan) durur; `</Keyframes>`
deseni orada **yoktur** ve regex bir SONRAKİ alanın gövdesini yakalar.
Ölçüldü: `ent_amb_fbi_smoke_land_hvy`in `ptxTargetDomain:m_positionKFP`
alanı boş, okuma `m_rotationKFP`e kayıp konum diye **[90, −30, 0]** verdi —
konum değil derece. Sessiz ve tamamen inandırıcı bir yanlış okuma.

Doğrusu (`kfp_govde`): önce alanın **kendi sınırını** kes (bir sonraki
`<Name>`e kadar), sonra içinde `<Keyframes>` ara. Bu hata bulunduktan
sonra alfa/yük istatistikleri yeniden ölçüldü ve **değişmedi**
(%88,2 / %44,6 / %9,3; band 1 / 18 / 230) — çünkü o alanlar nadiren boş.
Ama domain ölçümlerinin **tamamı** yanlıştı.

### Dürüst sınır: bunlar "tam custom" değil

Bizim olan: **doku, renk, spawn oranı, ömür, alfa zarfı, ve artık hareket**
(doğuş hacmi, yön, hız, ivme, sürtünme, attractor).
Vanilla'dan gelen: kural iskeleti ve dokunmadığımız alanlar
(`Rotation`, `MatrixWeight`, `ZCull`, shader tekniği, LOD davranışı).
Vanilla efektleri **değiştirilmiyor** (replace değil); bunlar ayrı
asset'ler. Ama sıfırdan yazılmış da değiller — iskelet devralınıyor.


## 8. Küçük tuzaklar

- ⛔ `argparse` help metnindeki `%` kaçışlanmalı (`%%`), yoksa `--help`
  çalıştığında `TypeError` ile patlar ve sebebi görünmez.

---

## Doku sayfası (flipbook) ayrı bir iştir

Kare sayısı, `C4`, ızgara, yoğunluk, transplant ve donör seçimi → `sayfa-doku.md`.
