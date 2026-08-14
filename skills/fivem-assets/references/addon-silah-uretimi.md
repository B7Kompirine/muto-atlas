# Add-on silah üretimi — Blender/Sollumz → vWeaponsToolkit → FiveM

Kendi 3D silah modelini GTA V / FiveM'e **add-on weapon** olarak sokmanın
uçtan uca hattı: iskelet eşleme, vertex group, shader, doku sözlüğü, meta
üretimi, kaynak yapısı ve mag hizalama düzeltmesi.

## KAYNAK VE GÜVENİLİRLİK — hangi bilgi nereden

Bu belgede iki tür bilgi var, karıştırma:

| İşaret | Kaynak | Güven |
|---|---|---|
| **[ölçüm]** | `data/skeletons.tsv.gz` — 868 `w_*` model üzerinden sayıldı | kesin |
| **[video]** | tek bir üreticinin çalışan iş akışı (ooknumber13 tutorial) | çalıştığı gösterildi, tek örnek |

`[video]` işaretli adımlar **denenmiş ve oyunda çalışmış** bir hattır ama tek
bir kişinin alışkanlıklarını da içerir; alternatifleri varsa belirtildi.
`[ölçüm]` işaretli sayılar tahmin değildir, sorgulanabilir.

## 0. ÖNCE REFERANS SİLAHI SEÇ VE İSKELETİNİ SORGULA

Kod/Blender açmadan önce hangi vanilla silaha bineceğine karar ver ve
**iskeletini gerçekten oku**. Kemik adı ve tag'i tahmin edilmez:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" bones w_ar_assaultrifle
```

Seçim ölçütü: silahının **sınıfı** (assault rifle, SMG, pistol...) ve
gereken **bileşen yuvaları** (şarjör, susturucu, dürbün, el feneri). Vanilla
silah hangi `WAP*` kemiklerini taşıyorsa senin silahın da o eklentileri
alabilir — taşımadığını sonradan ekleyemezsin.

## 1. İSKELET — ne birebir korunur, ne serbesttir

Add-on silah **vanilla iskeletin üzerine** kurulur. Serbest olan tek şey
kemiklerin **konumu**; ad ve tag korunur.

### Silah modelleri ikiye ayrılır [ölçüm]

868 benzersiz `w_*` `.ydr` modelinin:

- **408'i ana silah** (`boneCount > 1`) — `Gun_*` + `WAP*` iskeleti taşır
- **460'ı tek kemikli bileşen** (`boneCount == 1`) — kökü `AAP*` olan
  eklenti modelleri
- **201'i `_hi` ile biten** yüksek detay varyantı (ayrı model değil, aynı
  silahın LOD'u — sınıflandırmada iki kez sayma)

> ⚠️ `skeletons.tsv.gz`'de her satır **4 kez** tekrarlar (aynı model birden
> fazla RPF/DLC kopyasından indekslenir). Satır sayarak model sınıflandırma
> yapma — `boneCount` alanını kullan ya da `(index, ad, tag)` üçlüsüyle
> deduplike et. Bu tuzağa düşülürse 458 bileşen modeli "çok kemikli ana
> silah" sayılır ve tablo tamamen kayar.
>
> `assetdb.py bones` bu deduplikasyonu **artık kendisi yapıyor** — komutun
> çıktısında her kemik bir kez görünür. Uyarı `.tsv.gz`'yi kendin okuduğunda
> geçerli. İki ek ölçüm: kopyalar dosyada **ardışık bloklar** hâlinde durur
> (her blok indeks 0'dan başlar, uzunluğu kendi `boneCount`'una eşit —
> 72.364 blokta ihlal 0), ve **289 modelde kopyalar gerçekten farklıdır**
> (base vs DLC iskeleti). Fark her zaman `boneCount`'a yansımaz:
> `w_lr_grenadelauncher` 14 ↔ 15 kemik (`WAPScop_2` eklenmiş, sonraki tüm
> indeksler kayar), `adder` ise **iki kez 63 kemik** — aynı kadro, farklı
> indeks sırası. Bu yüzden düz satır kümesiyle deduplike etmek yetmez;
> **blok blok** ayır, yoksa 63 kemikli modelden 76 kemik çıkarırsın.
> Sonuç kuralı: **indekse değil TAG'e bağlan.**

### Ana silahta kemik yaygınlığı [ölçüm — n=410, deduplike]

| Kemik | Kaç silahta | Ne işe yarar |
|---|---|---|
| `Gun_Main_Bone` | 340 (%83) | gövde — mesh'in çoğu buraya bağlanır |
| `Gun_GripR` | 327 (%80) | sağ el kavrama noktası |
| `Gun_Root` | 325 (%79) | kök |
| `Gun_Muzzle` | 242 (%59) | namlu ağzı — flash/VFX çıkışı |
| `Gun_Trigger_Pr` | 218 (%53) | tetik (ateşte oynar) |
| `Gun_VFX_Eject` | 195 (%48) | kovan atma noktası |
| `WAPClip` | 187 (%46) | şarjör **takma noktası** |
| `Gun_Cock1` | 184 (%45) | sürgü / kurma kolu (ateşte oynar) |
| `Gun_GripL` | 163 (%40) | sol el kavrama |
| `WAPFlshLasr` | 163 (%40) | el feneri / lazer yuvası |
| `WAPSupp` | 151 (%37) | susturucu yuvası |
| `NM_Butt_Marker` | 144 (%35) | dipçik (NaturalMotion çarpma) |
| `WAPScop` | 115 (%28) | dürbün yuvası |
| `WAPGrip` | 80 (%20) | ön tutamak yuvası |
| `Gun_Safety` | 78 (%19) | emniyet |
| `WAPScop_2` | 69 (%17) | ikincil dürbün yuvası |
| `Gun_Hammer` | 67 (%16) | horoz (tabanca) |

### Bileşen modellerinin kök kemikleri [ölçüm — n=460]


**`AAPClip` ana silah iskeletinde hiç geçmez** — yalnızca tek kemikli
bileşen modellerinin köküdür. Aşağıdaki ayrım bu ölçümün doğrudan sonucudur.

### Kemik tag'leri sabittir [ölçüm]

868 modelde ad→tag eşlemesi **tek istisna dışında** birebir aynı:

```
Gun_Root 0 · Gun_GripR 18308 · Gun_GripL 18302 · Gun_Main_Bone 3360
Gun_Trigger_Pr 56099 · Gun_Cock1 39439 · Gun_Safety 53712 · Gun_Hammer 24730
Gun_Muzzle 17833 · Gun_VFX_Eject 28405 · NM_Butt_Marker 26613
WAPClip 1477 · WAPSupp 4230 · WAPScop 64805 · WAPScop_2 3634
WAPFlshLasr 4396 · WAPGrip 19397 · WAPCover 27459
AAPClip 0 · AAPCamo 0 · AAPSupp 0
```

**Tek istisna: kök kemiğin tag'i her zaman 0'dır.** `Gun_GripR` normalde
18308'dir ama kendi modelinin kökü olduğu 2 modelde 0 görünür; `Gun_Main_Bone`
da öyle. Bu bir tutarsızlık değil, kural: *root ⇒ tag 0*.

### ⛔ `AAPClip` ile `WAPClip` AYNI ŞEY DEĞİLDİR

En kolay yapılan adlandırma hatası budur ve sessizce yanlış sonuç verir:

- **`WAPClip` (tag 1477)** — **silahın** `.ydr`'sinde bulunan **takma
  noktası**. Şarjörün nereye oturacağını söyler.
- **`AAPClip` (tag 0)** — **şarjör modelinin** (`*_mag1.ydr`) **kök kemiği**.
  Bileşen modelinin kendi iskeletidir.

[ölçüm] `w_ar_assaultrifle_mag1`, `_mag2`, `_boxmag` — hepsi **tek kemikli**
ve o kemik `AAPClip`, tag **0**. Şarjör drawable'ında vertex group adı
`AAPClip` olacak; `WAPClip` yazarsan şarjör hiç bağlanmaz.

Aynı kalıp bütün eklentilerde geçerli — **modelin kökü `AAP*`, silahtaki
yuva `WAP*`**: `AAPSupp`↔`WAPSupp` (susturucu), `AAPScop`↔`WAPScop`
(dürbün), `AAPGrip`↔`WAPGrip` (tutamak), `AAPCamo` (kaplama, yuvasız).

### ⛔ AMA `weaponcomponents.meta`'ya `AAP*` YAZILIR, `WAP*` DEĞİL

Yukarıdaki ayrım iskelet tarafı içindir. Meta tarafında **iki isimden
yalnız biri kullanılır** ve bu sezgiye aykırıdır.

[ölçüm] 4 vanilla `weaponcomponents.meta` (common.rpf + update.rpf +
mpgunrunning + mpchristmas2017) çıkarılıp bütün `<AttachBone>` alanları
sayıldı:

```
toplam 318 girdi  →  AAP* ile başlayan: 318   ·   WAP* ile başlayan: 0
AAPCamo 133 · AAPClip 102 · AAPCamo2 22 · AAPScop 18 · AAPSupp 17
AAPBarrel 16 · AAPFlsh 7 · AAPGrip 2 · AAPCover 1
```

Yani `<AttachBone>` **silahtaki yuvayı değil, bileşen modelinin kendi kök
kemiğini** gösterir. Vanilla örneği:

```xml
<Item type="CWeaponComponentClipInfo">
  <Name>COMPONENT_PISTOL_CLIP_01</Name>
  <Model>w_pi_pistol_mag1</Model>       <!-- bileşen modeli -->
  <AttachBone>AAPClip</AttachBone>      <!-- O MODELİN kök kemiği -->
  <ClipSize value="12" />
  <ReloadData ref="RELOAD_DEFAULT_WITH_EMPTIES" />
</Item>
```

`WAPClip` yazarsan **vanilla'da hiç görülmeyen** bir değer üretmiş olursun.
Özet kural:

| Nerede | Hangi ad |
|---|---|
| Silahın `.ydr` iskeletindeki yuva kemiği | `WAP*` |
| Bileşen modelinin kök kemiği + vertex group | `AAP*` |
| `weaponcomponents.meta` → `<AttachBone>` | **`AAP*`** |
| `weapons.meta` → `<AttachPoints>` → `<AttachBone>` | **`WAP*`** |

### ⛔ `<AttachBone>` İKİ AYRI DOSYADA GEÇER VE DEĞERLERİ FARKLIDIR

Aynı etiket adı, farklı anlam — karıştırılırsa bileşen ya hiç görünmez ya
yanlış yere takılır. [ölçüm: vanilla `weapons.meta`, `WEAPON_PUMPSHOTGUN`]

```xml
<!-- weapons.meta — silahin YUVASI -->
<AttachPoints>
  <Item>
    <AttachBone>WAPClip</AttachBone>          <!-- WAP* -->
    <Components>
      <Item><Name>COMPONENT_PUMPSHOTGUN_CLIP_01</Name><Default value="true" /></Item>
    </Components>
  </Item>
</AttachPoints>
```
```xml
<!-- weaponcomponents.meta — BILESEN MODELININ kok kemigi -->
<Item type="CWeaponComponentClipInfo">
  <Model>w_ar_carbinerifle_mag1</Model>
  <AttachBone>AAPClip</AttachBone>            <!-- AAP* -->
</Item>
```

Ayrıca **`<WeaponComponents>` diye bir etiket vanilla'da yoktur** — bazı
anlatımlarda geçiyor ama `weapons.meta`'nın gerçek şeması `<AttachPoints>`
kullanır ve `CWeaponInfo` içinde `NmShotTuningSet` ile `GunFeedBone` arasında
durur (ölçüm: 160/182). Yanlış etiket sessizce yok sayılır, bileşen hiç
görünmez.

**`<Default value>` çıkarılabilirliği belirlemez.** Bileşen `<AttachPoints>`
listesinde olduğu sürece her iki durumda da takılıp çıkarılabilir; `Default`
yalnızca silahın hangi hâlde **doğduğunu** söyler. `false` verilirse silah o
parça olmadan spawn olur ve modelde boşluk görünür — "model bozuk" sanılan
şey çoğu zaman budur.

## 2. BLENDER HATTI [video]

### 2.1 Vanilla referansı içeri al — ⛔ BASE **VE** HI, ikisi birden

CodeWalker'dan referans silahın **iki modelini de** çıkar:

| Dosya | İçeriği |
|---|---|
| `w_xx_silah.ydr` | **base** — collision burada |
| `w_xx_silah_hi.ydr` | **hi** — yüksek poligonlu görsel |

Ayrıca şarjörü (`*_mag1.ydr`). Hepsini Blender'a import et; en güncel
patch'ten al.

İkisi de gerekir çünkü oyun mesafeye göre ikisini de kullanır ve **ikisinin
iskeleti ayrıdır**. Kemik taşırsan **her ikisinde de aynı yere taşımak
zorundasın** (§7) — biri kayarsa silah mesafe değiştikçe zıplar.

`General → View → Toggle Collisions` ile collision'ları göster.

### 2.2 Kendi mesh'ini vanilla'ya hizala

Kendi modelini vanilla silahın üstüne **mümkün olduğunca yakın** getir.
Kusursuz olması gerekmez ama yakınlık doğrudan sonuç kalitesidir:

- Yandan **ve arkadan** bak — nişangâh hattı yana kaçmasın.
- Bitince **`Ctrl+A` → All Transforms** uygula. Bu adım atlanırsa ölçek/
  dönme export'a taşınır.

### 2.3 Vanilla vertex group'larını SİLMEDEN ÖNCE incele

Vanilla silahın `Object Data Properties → Vertex Groups` listesi sana
animasyonun nasıl çalıştığını gösterir. Edit mode'da bir grubu seçip
`Select` dediğinde o kemiğin hangi mesh parçasını sürdüğünü görürsün:

- `Gun_Trigger_Pr` → tetik parçası
- `Gun_Cock1` → ateş edince geri gelen sürgü

Bunu görmeden kendi gruplarını kurma; hangi parçanın hangi kemiğe gideceğini
oradan öğrenirsin.

### 2.4 Kendi drawable'ını kur

1. Vanilla mesh'i sil, kendi mesh'ini göster.
2. Seç → **`V` → Convert to Drawable**.
3. Oluşan hiyerarşiyi aç, mesh'i **shift+sürükle** ile unparent et, artık
   boş kalan drawable objesini sil, mesh'i yeniden adlandır.
4. Mesh'i **skeleton/armature'a parent** et.

### 2.5 ⛔ SİLAHTA WEIGHT PAINTING YOKTUR — rijit atama vardır

Ped'deki "4 kemiğe dağıt, yumuşak geçiş" mantığı **silahta geçerli değil.**
Vanilla `w_ar_assaultrifle.ydr` çözülüp bütün vertex'leri sayıldı:

| Ölçüm | Sonuç |
|---|---|
| Toplam vertex | 2556 |
| **1 kemik etkiliyor** | **2556 (%100)** |
| 2+ kemik etkiliyor | **0** |
| Ağırlık toplamı = 255 (1.0) | 2556 / 2556, sapma **0** |
| Ağırlıksız vertex | **0** |

Yani silah mesh'i **katı parçalar** bütünüdür: tetik döner, sürgü geri gelir,
gövde durur. Metal esnemediği için geçiş bölgesi de yoktur. Blender'da
`Assign` butonu **Weight = 1.000** ile kullanılır; slider 1.0 değilse
ağırlık 255'in altına düşer ve vanilla'nın hiçbir yerinde görülmeyen bir
durum üretirsin.

Ölçülen dağılım (aynı model):

```
Gun_Main_Bone    2382 vertex  (%93)
Gun_Safety         71
Gun_Cock1          62
Gun_Trigger_Pr     41
```

Not: vanilla bu silahta **dört** grup kullanıyor — `Gun_Safety` (emniyet
kolu) de ayrı. Video üç grupla yetiniyor; emniyeti olan bir silah
yapıyorsan dördüncüyü de ayır, yoksa emniyet gövdeye kaynar ve hiç oynamaz.

Format ped ile aynıdır (4 slot, byte ağırlık, toplam 255) — fark
**kullanımdadır**: ped 4 slotu da harmanlar, silah yalnız birini doldurur.

### 2.5b Vertex group'ları oluştur ve ata

En az üç grup — **adlar kemik adlarıyla birebir aynı olmalı**, büyük/küçük
harf dahil:

```
Gun_Main_Bone      → geri kalan tüm mesh
Gun_Trigger_Pr     → tetik
Gun_Cock1          → sürgü / kurma kolu
```

Atama sırası pratik olarak şöyle işler: tetiği ve sürgüyü `L` (linked
select) ile seçip kendi gruplarına `Assign`, sonra **tüm mesh'i seç →
`Gun_Cock1` ve `Gun_Trigger_Pr` gruplarında `Deselect` → kalanı
`Gun_Main_Bone`'a `Assign`**.

Bu "seç → çıkar → kalanı ata" adımı zarafet değil, **iki kuralı birden
garantiye alan şeydir** (§2.5'teki ölçüm):

- **ağırlıksız vertex kalmaz** — kalan her şey `Gun_Main_Bone`'a gider
- **çift atama olmaz** — hareketli parçalar önce çıkarıldığı için hiçbir
  vertex iki gruba birden 1.0 ile giremez

Atlanırsa iki arıza da **sessizdir**: ağırlıksız vertex'ler origin'e
çöker, çift atanmış parça iki kemik arasında gerilir. Export uyarı vermez.

Ardından mesh'e **Armature modifier** ekle ve hedefini **silahın**
armature'ı yap — şarjörünki değil. Base ve hi mesh'lerinin her biri kendi
armature'ına bağlanır.

### ⛔ EKSİK GRUP BOŞ BIRAKILIR, SİLİNMEZ

Referans silahta kaç vertex group varsa **senin modelinde de o kadar
olmalı** — karşılığı olmayanı bile **boş olarak yarat**. Kendi modelinde
kullanılmayan bir parça varsa (ör. emniyet kolun yok) grubu yine de aç,
içine vertex atama.

Fazladan grup da bırakma: kaynak modelden gelen kendi eski grupların
(`Cube.001` vb.) silinmeli. Ölçüt basit — **grup sayısı referansla aynı,
adlar referansla aynı.**

### 2.6 Sollumz LOD alanı

`Object Data Properties → Sollumz` sekmesinde **High LOD** için doğru mesh
adının yazılı olduğundan emin ol. Yanlışsa export bozulur.

### 2.7 Şarjör ayrı bir drawable'dır

Şarjör silahın parçası değil, ayrı bir model + ayrı bileşendir:

1. Vanilla mag'e hizala → `Ctrl+A` All Transforms.
2. `V` → Convert to Drawable, unparent, yeniden adlandır.
3. **Tek** vertex group: `AAPClip` — tüm mesh'i ona ata.
4. Armature modifier → **mag'in** armature'ı.

Collision'ın mag ile birebir aynı boyda olması **gerekmez**; var olması
yeterli. Yine de kabaca oturtmak isabetli.

## 3. SHADER VE DOKU SÖZLÜĞÜ [video]

### Shader seçimi

Sollumz shader'ı zorunlu. Silahta yaygın seçenek `normal_spec`; doku
sırası:

```
Base Color   → diffuse
"Roughness"  → specular   (alan adı yanıltıcı, içine specular doku girer)
Normal       → normal map
```

**Weapon tint / skin kullanacaksan `normal_spec` yanlış tercihtir** —
tint destekleyen shader'a geç. Tint derdin yoksa `normal_spec` yeterli.

### Doku sözlüğü (.ytd) üretimi — embed/unembed hilesi

Sollumz `.ytd` üretemez. Video'daki pratik yol:

1. `Drawable Tools → Shader Tools → Set All Materials Embedded`
   (hem silah hem mag için).
2. Export et → Blender doku dosyalarını XML'in yanına yazar.
3. `Set All Materials Unembedded` → **tekrar** export et.
4. Çıkan doku klasörlerini **folders2ytd** aracına sürükle → `.ytd` üretir
   (gerekiyorsa DDS'e de çevirir).

Amaç sadece dokuları export klasörüne düşürmek. Dokuların zaten DDS ve
düzenli olduğu bir hattın varsa bu adımı atlayabilirsin.

Sonra `.ydr` + `.ytd` dosyalarını CodeWalker'a sürükleyip doğrula.

## 4. META ÜRETİMİ — vWeaponsToolkit

### ⛔ SÜRÜM: 1.0.3 kullan

[video] Sonraki build'ler bozuk ve düzgün çalışmıyor. GitHub release
sekmesinde aşağı inip **1.0.3**'ü al.

Araç dört sekmeli: `Create Add-on Weapon` · `Configuration` ·
`Components` · `Export`.

### 4.1 Create Add-on Weapon

`Browse` ile `.ydr`/`.ytd` dosyalarının bulunduğu klasörü seç, sonra:

| Alan | Örnek | Anlamı |
|---|---|---|
| Select Weapon Template | `WEAPON_ASSAULTRIFLE` | taban silah tanımı |
| Weapon Name | `AK19` | çıktı klasörü adı — kritik değil |
| **Weapon ID** | `WEAPON_AK19` | **oyunda spawn edilen ad** |
| Weapon Model | `W_AR_AK19` | `.ydr` dosya adı |

Sol taraftaki `Files Found` listesi eşleşen dosyaları **yeşile çevirir** —
yeşil değilse ad tutmuyor demektir, ilerleme.

Şablon listesi eksiktir; istediğin silah yoksa en yakınını seçip meta'yı
elle düzeltmek gerekir.

### 4.2 Configuration

Video'daki varsayılanlar (assault rifle şablonu):

```
Select Audio Item          AUDIO_ITEM_ASSAULTRIFLE
Fire Rate Modifier         1.0
Weapon Damage              30.0
Damage Type                BULLET
Weapon Range               120.0
Headshot Damage Modifier   18.0
Ammo Type                  AMMO_RIFLE
LOD                        500.0
Reload Speed Modifier      1.0
```

### 4.3 Components — şarjör

`Add` → `Select Component Template` → `COMPONENT_ASSAULTRIFLE_CLIP_01`,
sonra:

| Alan | Değer |
|---|---|
| Component Name | `COMPONENT_AK19_CLIP_01` |
| Model Name | `w_ar_ak19_mag1` |
| Model LODs | `300` |
| Clip Size | `30` |
| Ammo Info | `Default Ammo` |
| **Component Enabled** | ☑ işaretli |

`Component Enabled` işaretliyse silah spawn edildiğinde şarjör **varsayılan
olarak takılı** gelir. İşaretlenmezse silah şarjörsüz doğar.

### 4.4 Export

Export sekmesi her asset'i hangi tanımın kullandığını gösterir; **hepsi
yeşil olmalı**:

```
w_ar_ak19.ydr        → WEAPON_AK19
w_ar_ak19.ytd        → WEAPON_AK19
w_ar_ak19_mag1.ydr   → COMPONENT_AK19_CLIP_01
w_ar_ak19_mag1.ytd   → COMPONENT_AK19_CLIP_01
```

`Browse` ile çıktı klasörü seç → `Export`. Araç hazır bir **resource
klasörü** üretir; onu doğrudan sunucunun `resources/` dizinine kopyala.

## 5. KAYNAK YAPISI — ölçülmüş `data_file` listesi

Oyun konsolunda yüklenirken görülen gerçek dosya listesi [video, konsol
çıktısından okundu] — add-on silah kaynağının bildirmesi gereken beş
data_file:

| data_file türü | Yol |
|---|---|
| `WEAPONINFO_FILE` | `meta/weapons.meta` |
| `WEAPON_METADATA_FILE` | `meta/weaponarchetypes.meta` |
| `WEAPON_ANIMATIONS_FILE` | `meta/weaponanimations.meta` |
| `PED_PERSONALITY_FILE` | `meta/pedpersonality.meta` |
| `WEAPONCOMPONENTSINFO_FILE` | `meta/components/<COMPONENT_ADI>/weaponcomponents.meta` |

Dikkat: **her bileşen kendi klasöründe kendi `weaponcomponents.meta`'sını
taşır** — bileşen başına bir `data_file` satırı gerekir. `.ydr`/`.ytd`
dosyaları `stream/` altındadır ve otomatik streamlenir.

Kaynak doğru yüklendiyse konsolda her satır için
`loading … / done loading … in data file mounter 0x…` çifti görürsün.
Bu çift yoksa o meta hiç yüklenmemiştir.

## 6. TEST DÖNGÜSÜ

### Hızlı yol (denemeye değer)

```
restart <KAYNAK_ADI>
str_requestFlush
```

`str_requestFlush` **istemci konsolunda** (F8) çalıştırılır ve streaming
cache'ini boşaltır. [video] Bunun için **canary / latest unstable** build
gerekiyor.

⚠️ **Silahı önce elinden bırak.** Oyuncunun üzerinde duran silah
yenilenmez; `Remove All Weapons` yapıp sonra tekrar spawn et.

### Güvenilir yol

`str_requestFlush` tutmazsa **sunucudan çıkıp yeniden bağlan.** FiveM
stream dosyalarını cache'ler ve `restart` tek başına yetmez. Şüphedeysen
bu yolu kullan — bayat asset test etmek yanlış teşhis üretir ve saat
kaybettirir.

Spawn: menüden `Spawn Weapon By Name` → `WEAPON_AK19`, ya da
`GiveWeaponToPed`.

## 7. ŞARJÖR YANLIŞ YERDE / ATEŞTE TİTRİYOR

Belirti: silah çalışıyor ama şarjör kaymış duruyor, ateş ederken zıplıyor.
Sebep: `WAPClip` kemiğinin **konumu** yanlış — mag doğru bağlanmış ama
yanlış yere.

Teşhis yöntemi (Blender'daki görüntüyü oyundakiyle eşitle):

1. Silahta **Edit Mode** → `WAPClip` kemiğini seç.
2. **Set Origin to Selected** (3D cursor'ı kemiğe taşı).
3. Mag'i seç → **Snap to Cursor**.

Artık Blender'da gördüğün, oyunda göreceğinle **aynıdır**. Kayma buradan
ölçülür.

Düzeltme:

1. Armature'da **Edit Mode** → `WAPClip` kemiğini doğru yere taşı.
   ⛔ **Aynı kemiği `_hi` armature'ında da aynı yere taşı** — ikisi
   hizalanmazsa silah LOD değişiminde zıplar. Pratik yol: iki armature'ı
   birden seçip tek seferde Edit Mode'a girmek.
2. **Pose Mode** → taşıdığın kemiği seç → `Bone Properties` → **tüm
   Bone Flags'ı sil**. ⛔ Sadece **taşıdığın kemiklerde** yap.
3. Yerine **tam iki flag** ekle (`New` ile), adları birebir:
   ```
   LimitRotation
   LimitTranslation
   ```
   [ölçüm — karede doğrulandı: `Gun_Muzzle`, `BoneTag 17833`, Flags
   listesinde tam bu iki satır] `Drawable Tools → Bone Tools → Limit`
   düğmesi de aynı iki flag'i ekler; elle yazmakla eşdeğerdir.
4. Taşıdığın **her** kemik için 2-3'ü tekrarla — base ve hi ayrı ayrı.
5. Yeniden export et, `.ydr`'leri `stream/` içinde değiştir, §6'daki test
   döngüsünü uygula.

**Namlu ateşi (muzzle flash) yanlış yerden çıkıyorsa** sebebi aynıdır:
`Gun_Muzzle` (tag 17833) kemiği yanlış konumda. Test yöntemi — **gece,
birinci şahıs, ateş et**; flash'ın çıktığı nokta kemiğin yeridir.

## 8. TUZAK KATALOĞU

- **⛔ `AAPClip` ≠ `WAPClip`.** Şarjör modelinin kök kemiği `AAPClip`
  (tag 0); silahtaki takma noktası `WAPClip` (tag 1477). Karıştırılırsa
  şarjör bağlanmaz.
- **⛔ `weaponcomponents.meta` → `<AttachBone>` alanına `AAP*` yazılır.**
  [ölçüm: 318/318 vanilla girdi `AAP*`, `WAP*` sıfır] Sezgiye aykırıdır;
  "takma noktası WAPClip'ti" diye oraya `WAP*` yazma.
- **⛔ Base ve hi modelin ikisi de gerekir** ve kemik taşıma **ikisinde de**
  yapılır. Yalnız birini düzeltirsen silah LOD değişiminde zıplar.
- **Eksik vertex group boş bırakılır, silinmez** — grup sayısı ve adları
  referans silahla birebir aynı olmalı.
- **Taşınan kemiğin flag'leri** tam iki tane olmalı: `LimitRotation` +
  `LimitTranslation`. Eski flag'ler silinmezse kemik konumu tutmaz.
- **⛔ vWeaponsToolkit 1.0.3'ten sonraki sürümler bozuk.**
- **Vertex group adı = kemik adı, birebir.** Büyük/küçük harf dahil.
  Tutmazsa o parça hiç sürülmez, hata da alınmaz.
- **`Ctrl+A` All Transforms atlanırsa** ölçek/dönme export'a sızar.
- **Armature modifier yanlış hedefe bağlanır** — silah mesh'i mag'in
  armature'ına bağlanırsa oyunda saçma davranır. Her ikisini de kontrol et.
- **Sollumz High LOD mesh adı yanlışsa export bozulur.**
- **Bone flag silme tek kemiğe uygulanır**; tümüne uygularsan iskeletin
  davranışını bozarsın.
- **`Component Enabled` işaretsizse** silah şarjörsüz spawn olur ve bu
  "model bozuk" sanılır.
- **`Files Found` yeşil değilse ilerleme** — ad uyuşmazlığı meta'ya
  taşınır ve oyunda model hiç yüklenmez.
- **Bileşen başına ayrı `weaponcomponents.meta` + ayrı `data_file`
  satırı** gerekir; tek satır bırakmak diğer bileşenleri sessizce düşürür.
- **Silah elde tutulurken yenilenmez** — flush/restart öncesi silahı bırak.
- **Kemik tag'i uydurma.** `assetdb.py bones <model>` ile sorgula;
  868 modelde ad→tag eşlemesi sabittir, tek istisna kök kemiğin 0 olmasıdır.
- **Taşımayan yuvayı sonradan ekleyemezsin** — referans silahta `WAPScop`
  yoksa dürbün takılamaz. Şablonu buna göre seç.

## NE ZAMAN YETMEZ

- **Silah animasyonları** (reload, ateş, tutuş) — `weaponanimations.meta`
  vanilla klipleri işaret eder; kendi klibini üretmek ayrı bir hattır
  (`references/ped-animasyon-davranis-ve-uretim.md`).
- **Weapon tint / camo** — farklı shader ve `AAPCamo` bileşeni gerekir.
- **Fizik/fragment davranışı** (yere düşen silah) — `.yft` tarafıdır.
