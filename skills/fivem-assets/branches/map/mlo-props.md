# MLO'ya kendi prop'unu / drawable'ını koy (yeni entity)

**Ne zaman okunur:** iç mekâna yeni obje ekleyeceksin (kutu, kapı, animasyonlu emanet kasası), kendi mesh'in MLO'da siyah/görünmez, oda ataması, iki MLO sürümü.
**When to read:** adding your own prop or drawable into an MLO as a new entity.
**Kaynak:** `mlo-prop-uretim-hatti.md` + `mlo-drawable-export-bulgulari.md` (tamamı, 2026-07/08) · **Ölçüm:** Fleeca kasa odası 20 emanet kutusu + 2 kapı; `trees_normal.sps` A/B; v_coroner asansör kabini
**Önce:** `branches/map/_branch.md` · gövde › `trunk/flags.md`, `trunk/tool-pitfalls.md`

---


Fleeca kasa odasına 20 animasyonlu emanet kutusu ve iki özel kapı koyarken
uçtan uca kurulan hat. Her madde oyun içi ölçümle doğrulandı.

**Sırayla oku. Adım atlarsan sessizce başarısız olur — bu iş hata vermez,
sadece "hiçbir şey olmaz".**

---

## 0. ÖNCE BUNU BELİRLE

**Obje MLO iç mekânında mı, dışında mı?** Her şey buna bağlı.

| | MLO **dışı** | MLO **içi** |
|---|---|---|
| kendi ymap'in | ✅ | ❌ oda/portal eler, obje hiç gelmez |
| MLO entity listesi | — | ✅ tek yol |
| script spawn | ⚠️ harita objesi değil | ⚠️ aynı + her istemcide yük |

**Aynı iç mekânın birden fazla MLO sürümü olabilir.** Fleeca'da iki tane:
`v_genbank` (`v_int_10.ytyp`) ve `hei_generic_bank_dlc`
(`hei_dlc_generic_bank.ytyp`). İkisi **aynı MLO-yerel çerçeveyi** paylaşıyor
(aynı prop ikisinde de aynı yerel koordinatta) ama entity listeleri farklı.
Birine yamayıp diğerini atlarsan test ettiğin şubede hiçbir şey görünmez —
bu bir kez yaşandı ve uzun süre yanlış yerde arandı.

---

## 1. MEVCUT OBJEYİ DEĞİŞTİRME (model adı swap)

En güvenli işlem: dosya boyutu değişmez, MLO yapısına dokunulmaz.

```
patch_vanilla_ytyp.ps1 -YtypName v_int_10.ytyp `
  -SwapEntity @('v_ilev_gb_teldr=my_teldr','v_ilev_gb_vauldr=my_vauldr') `
  -OutDir <...>\stream
```

- `data_file 'DLC_ITYP_REQUEST'` **EKLENMEZ** (vanilla dosya değişimi).

## 2. YENİ ENTITY EKLEME

```
add_mlo_entities.ps1 -YtypName v_int_10.ytyp -Mlo v_genbank `
  -Part v_10_gen_country_bank -Model my_depobox `
  -CellsJson <...>.json -Count 20 -Room bankvault -OutDir <...>\stream
```

Üç şey aynı anda doğru olmalı, biri eksikse obje **görünmez**:

| alan | doğru | yanlış olursa |
|---|---|---|
| `flags` | **18350080** (vanilla MLO entity'sinden ölçüldü) | ymap değeri `1572872` → obje hiç oluşmaz |
| `lodDist` | **-1** | — |
| **oda** | `AttachedObjects`'e indeks eklenmeli | **eklenmezse obje hiç oluşmaz, MLO bozulabilir** |

Oda ataması en kolay atlanan adım: entity `entities` dizisinde görünür,
ytyp sorunsuz yüklenir, oyunda hiçbir şey çıkmaz.

**Koordinat MLO-YEREL olmalı.** Parça yerel verisi varsa zincir:
`panelLocal → (parça pos/rot) → mloLocal`. Referans parça hedef MLO'da
yoksa diğer MLO'larda aranır (ikisi aynı çerçeveyi paylaşıyor).

## 3. YAMALAR ÜST ÜSTE BİNMELİ

Her script vanilla RPF'ten okursa öncekini **ezer**. Gerçek vaka: kapı
değişimi yapıldı, sonra aynı ytyp'ye kutu eklenince kapılar vanilla'ya
döndü. Her iki script de artık çıktı klasöründe dosya varsa **ondan**
devam ediyor.

---

## 4. FRAGMENT ÜRETİMİ

Buradaki tek kritik hatırlatma:

**`parentIdx = 255` olan grup entity gövdesidir ve kemiği TAKİP ETMEZ.**
En az iki grup gerekir:

```
grup[0]  sabit kemik   parentIdx=255   → gövde / menteşe
grup[1]  hareketli     parentIdx=0     → dönen parça
```

Bound'u kemiğe bağlayan şey **COPY_TRANSFORMS constraint**'i —
`parent_bone` değil, isim eşleşmesi değil.

### Statik bit

Duvara monte fragment `flags`'ine **32** eklenmezse oyuncu dokununca
**düşer**. `537526784` (animasyonlu fragment) + `32` = **537526816**.

---

## 5. KENDİ .ycd'NİN

Sollumz `.ycd`'yi **XML** olarak yazar ("Successfully exported" der ama
klasörde `.ycd` yoktur). Binary'ye çevirmeden önce XML'e **elle** üç şey
eklenir — Sollumz hiçbirini yazmaz:

```xml
<Clips><Item>
  <Hash>my_depobox_open</Hash>            ← klip hash'i
  <Name>pack:/my_depobox_open</Name>       ← pack:/ NORMAL, dokunma
  <Tags /> <Properties />
  <AnimationHash>my_depobox_open</AnimationHash>
</Item></Clips>
<Animations><Item>
  <Hash>my_depobox_open</Hash>            ← ANIMASYON hash'i
  <Unknown1C>hash_22E95D79</Unknown1C>      ← Sollumz hash_00000001 yazar
</Item></Animations>
```

Sonra:
```powershell
[CodeWalker.GameFiles.XmlMeta]::GetYcdData($doc)   # GUI'nin kullandigi yol
```

**`XmlYcd.GetYcd($doc).Save()` KULLANMA** — nesne modeline girer,
`ClipDictionary.Clips` üzerinde gezinmek `NotImplementedException` fırlatır.

### Doğrulama (bunu görmeden "oldu" deme)

```
ClipMap = <joaat(klip)>     AnimMap = <joaat(klip)>
```

İkisi de sıfırdan farklı olmalı. `AnimMap = 0` ise `PlayEntityAnim` **true
döner ama kemikler kımıldamaz** — en kafa karıştırıcı belirti.

**Sollumz'un çıktısı her export'ta aynı değil.** Bir seferinde Animations
bloğuna `<Hash>hash_00000000</Hash>` yazdı, bir seferinde elementi **hiç
yazmadı**. Körlemesine `replace` yetmez; her seferinde geri okuyup
`AnimMap`'i doğrula.

---

## 6. YTYP + EXPRESSION EXTENSION

Nesne modeliyle (`Archetype.Extensions`) yazmak **serileşmiyor**.
Tutan yol XML:

```powershell
[CodeWalker.GameFiles.XmlMeta]::GetData($doc, [MetaFormat]::RSC, "")
```

`MetaFormat`'ta **`ytyp` yok** — ytyp bir RSC meta'sıdır.

Doğrulama: `ext: MCExtensionDefExpression dict=<hash> name=<hash>`

---

## 7. ANİMASYON SEÇİMİ — ped mi prop mu?

**Kemik sayısı söyler:**

| kemik | ne |
|---|---|
| 44+32 (çok-izli) | **ped** klibi (gövde + mimik) |
| 72 | genelde **prop** izi (çanta, alet) |
| 4-24 (tek-iz) | prop izi |

Gerçek hata: kutu soyma sekansında ped'e `reward_p_m_bag_var22_arm_s_f`
(72 kemik) oynattım — o **çantanın** izi. Karakter hiç kımıldamadı.
Doğru ped klipleri çok-izli olanlardı: `enter` / `action` / `reward` /
`no_reward` / `rest_exit`.

Süreleri tahmin etme, `assetdb.py anim <dict> --dict-only` ile oku.

### Hazır sekanslar

- **Kilitli kutu delme:** `anim@scripted@cbr5@ig3_drill_box@pattern_01@lockbox_01@male@`
  `enter 3.8 · action 8.0 · reward 4.57 · no_reward 4.10 · rest_exit 3.23`
  Matkap prop'u: `ch_prop_vault_drill_01a`. **Boş çıkma varyantı hazır.**
- **Kasa/tezgâh soyma:** `oddjobs@shop_robbery@rob_till` (enter/loop/exit)

### Prop'u ele tutturma

`PH_R_Hand` (28422) her ped'de çözülmeyebilir; `GetPedBoneIndex` **-1**
dönünce attach kök kemiğe düşer ve prop **gövdenin yanında havada** kalır.
Yedek: `SKEL_R_Hand` (57005). Ofset ve `rotationOrder` → `branches/prop/hand-attach.md`.

Klip zaten aleti çantadan çıkarıyorsa prop'u **klipten sonra** tuttur —
yoksa iki alet görünür.

### Senkron sahne klipleri konum ister

Bu klipler ped'in objeye göre **konumu** sabit olacak şekilde yapılmış.
Sadece `TaskTurnPedToFaceCoord` yetmez; ped'i objenin önüne ofsetle koy.

**Objenin ÖNÜ entity'nin ARKASI olabilir** — modelin ön yüzü yerel `-Y`'de
ise (GTA entity ileri yönü `+Y`), `+ileri` kullanmak oyuncuyu 90-180°
yanlış yere koyar.

---

## 8. TEKRARLANMAMASI GEREKEN HATALAR

Hepsi bu oturumda yaşandı ve zaman kaybettirdi.

### Asset / yerleştirme
1. **Script'le spawn edilen obje harita objesi değildir.** Kapı sistemi
   bulamaz (kapı zeminden düştü), fragment collision'ı animasyonu takip
   etmez. Ve 60 kişilik sunucuda her istemcide ayrı yük.
2. **MLO içine ymap ile prop konmaz.** Referansın ymap kullanması
   yanıltmasın — önce onun prop'unun MLO içinde mi dışında mı olduğuna bak.
3. **Entity'yi odaya bağlamayı unutma.** Sessizce görünmez.
4. **MLO entity'sine ymap bayrağı verme.** Sessizce görünmez.
5. **Aynı iç mekânın ikinci MLO sürümünü atlama.**
6. **Vanilla prop ytyp'sinde `specialAttribute` düzeltmek tutmadı** —
   dosya doğru üretildi ama oyun içi fizik yüklenmedi. MLO entity swap
   çalıştı.

### Araç davranışı
7. **CodeWalker `.yed`'i tam okuyamaz.** `ExprMap.Count == 0` görmek
   "dosya boş" DEMEK DEĞİLDİR — expression bytecode'unu yazamıyor, sadece
   okuyabiliyor. Bu yüzden "`.yed` işe yaramıyor" diye saatler kaybedildi.
   **Bir aracın bir şeyi göstermemesi, o şeyin yok olduğu anlamına gelmez.**
8. **Sollumz `.ycd`/`.yed`/`.ymap` binary üretemez** ve `.ycd`'yi XML
   yazarken "Successfully exported" der.
11. **Lua dosyasını Python ile yazarken kaçışlar bozulabilir.**
    `\n` gerçek satır sonuna dönüşüp Lua stringini bölmüştü; dosya parse
    edilemedi ve **hiçbir komut kayıtlı olmadı**. `lua_check` sözdizimini
    temiz gösterir, çalışma zamanı hatasını yakalamaz.
    → Bu tür satırları doğrudan `Edit` ile yaz.

### Mantık
12. **Durumu önbellekleme, sürekli doğrula.** Aynı hata iki yerde yapıldı:
    `doorRegistered[hash]` önbelleği ve "entity handle değişti mi"
    karşılaştırması. FiveM handle'ı yeniden kullanabilir; animasyon bir kez
    başarısız olursa bir daha denenmez. Doğrusu: `IsEntityPlayingAnim` gibi
    **gerçeğe** sor.
13. **Model adını değiştirince onu arayan her config'i güncelle.**
    `config/heists/fleeca.lua` hâlâ `v_ilev_gb_teldr` arıyordu; kapı modülü
    kapıyı tanıyamayınca kilit mantığı yanlış tarafa düştü.
14. **"Düzelttim, şimdi hiç açılmıyor" sahte regresyon olabilir.**
    Config doğru adı gösterince o güne kadar hiç çalışmamış kilit ilk kez
    devreye girer. Kapı tasarım gereği kilitlidir.
15. **Tek otorite kuralı.** Aynı objeye iki modül durum yazarsa son yazan
    kazanır. Kilit hem kapı sistemiyle hem `FreezeEntityPosition` ile
    uygulanıyordu; donmuş entity kapı sisteminden etkilenmez, bu yüzden
    `durum=0` göründüğü halde kapı açılmıyordu.
16. **Referansı kopyalarken neyin işe yaradığını ölç.** Referansın kendi
    `.ycd`'si olması "custom ycd şart" demek değildi; eksik parça `.yed` +
    Expression extension'dı. O yerine oturunca vanilla klip zaten çalıştı.

### Test disiplini
18. **Bir seferde tek değişken değiştir.** Bir şey çalışmıyorsa zinciri
    parçalara ayır (`.yed`'i çıkar / vanilla klip dene) — iki bambaşka
    düzeltmeyi tek testle ayırt eden A/B testi kur.
19. **Zincirin tamamı bitmeden test isteme.** Yarım zincirde çıkan sonuç
    yanlış yöne götürür.


---

# MLO'ya kendi drawable'ını koyma — ölçülmüş bulgular


`v_coroner` BodyStorage asansör sahnesi üretilirken ölçüldü. Hepsi **sessiz**
hatadır: hata mesajı yok, "successfully exported" yazar, dosya oluşur, oyunda
yanlış sonuç çıkar.

Kardeş dosyalar: `mlo-prop-uretim-hatti.md` (entity/oda hattı) ·
`trunk/flags.md` (bayraklar) · `branches/look/lights.md` (ışık).

---

## 1. ⛔ `trees_normal.sps` İÇ MEKÂNDA SİMSİYAH ÇİZER

En pahalı bulgu. Bir MLO odasına `trees_normal` (ya da başka bir **foliage**)
shader'ı ile geometri koyarsan model **tamamen siyah** çıkar.

**Sebep:** foliage shader'ları aydınlatmayı **doğal/güneş** yolundan alır. MLO
içinde doğal ambient sıfıra yakındır (`morgue_dark` 0.154, ondan türetilmiş
`my_mlo_dark` **0.045**), yapay ambient (0.300) ise foliage tarafından
okunmaz → ışık yok → siyah.

**Çözüm:** iç mekân geometrisi için `normal.sps` / `normal_spec.sps`
(render bucket 0). `trees_normal`ı yalnızca dış mekânda kullan.

**BEDELİ — bunu bilerek öde:** `trees_normal`ın vertex rüzgârı
(`WindGlobalParams`, `Color 2`.B maskesi) da gider. **İç mekânda “ağ/lif
rüzgârla sallansın” diye bedava bir yol YOKTUR.** Hareket isteniyorsa
`.yed` expression zinciri ya da RayFire gerekir.

### Sebep bulunmadan önce elenenler (hepsi doğruydu, hiçbiri sebep değildi)

Aynı yolu tekrar yürüme — bu altısı ölçüldü ve temiz çıktı:

| kontrol | ölçülen |
|---|---|
| gömülü doku var mı | 2 doku, 1024 DXT1 ✓ |
| `DiffuseSampler` bağlı mı | doğru ada bağlı, sözlükte var ✓ |
| vertex rengi | `Colour0 = 255,255,255,255` ✓ |
| normaller | gerçek yüzey normalleri ✓ |
| `UseTreeNormals` | zaten **0** (ilk teoriydi, çürüdü) ✓ |
| UV / tangent | var ✓ |

### Teşhis yöntemi: aynı odada A/B

Tek bir katmanın shader'ını değiştir, diğerini **kontrol grubu olarak
`trees_normal`da bırak**, aynı karede bak. Bizde bizim katmanlar renklendi,
kontrol siyah kaldı → sebep kesinleşti. Tek değişkenli test kurulmadan
"shader yüzünden" demek tahmindir.

---

## 2. ⛔ KAYNAK İKİ YERDEYSE FiveM BİRİNİ SESSİZCE YOK SAYAR

Aynı adlı kaynak iki klasörde varsa yalnız biri yüklenir, diğerine yapılan
her şey **çöpe gider**. Uyarı yalnızca **sunucu logundadır**, oyunda hiçbir
belirti yoktur:

```
Warning: my-resource exists in more than one place
([harita]\my-resource is used, the duplicate is [script]\my-resource)
```

**Kural: “oyunda görünmüyor” dendiğinde İLK BAKILACAK YER SUNUCU LOGUDUR**,
`txData/default/logs/fxserver.log`. Teşhis betiği yazmadan, asset kurcalamadan
önce oraya bak. Bu bir tur kaybettirdi.

Aynı logdan çıkan ikinci uyarı da gerçek bir risktir:

```
Asset X.ydr uses 64.0 MiB of physical memory. Oversized assets can and
WILL lead to streaming issues (such as models not loading/rendering).
```

4096 DXT5 doku bunu tetikler. 2048'e indirmek 4 kat düşürür
(ölçüldü: `.ydr` 5.35 MB → 1.85 MB, 64 MiB → ~16 MiB).

---

## 3. Sollumz export tuzakları

### ⛔ `use_custom_settings=False` VERİLEN ARGÜMANLARI YOK SAYAR

`bpy.ops.sollumz.export_assets(...)` çağrısında bu bayrak **varsayılan False**
ve o hâlde operatör senin geçtiğin argümanları **kullanmaz**, sahnenin kendi
export ayarlarını kullanır. Ölçülen sonuç: `limit_to_selected=True` geçildiği
hâlde **bütün sahne** (170+ drawable, 19 sn) ihraç edildi ve
`target_versions={'GEN8'}` yok sayılıp çıktı `gen8/` + `gen9/` **alt
klasörlerine** dağıldı. `use_custom_settings=True` ile 5 dosya, 1.2 sn.

### ⛔ Doku `embedded` bayrağı + PNG gömülemez

Sollumz doku düğümünde `n.texture_properties.embedded` **False** ise doku
`.ydr`'ye **hiç yazılmaz**; export uyarmaz. Belirti: geri okumada
`TextureDictionary` boş, oyunda model dokusuz.

Bayrağı açtığında ikinci kapı gelir:
`WARNING: Embedded texture '...' is not in DDS format.` — **PNG gömülemez.**
`texconv -f DXT1 -m 0` ile DDS'e çevir (mip zinciri şart).
Doku adı **dosya adından** türer, o yüzden dosya adını koru.

### ⛔ `hide_select` `select_set()`'i SESSİZCE düşürür

Obje ya da koleksiyon `hide_select=True` ise `select_set(True)` hata vermez,
seçim **boş kalır** ve export `No Sollumz objects selected!` der. Obje
görünürdür — gözle ayırt edilemez. `hide_viewport` / `hide_get()` temiz
görünürken `hide_select` açık olabilir; üçünü de kontrol et.

### ⛔ `sz_lods.high.mesh` atanmazsa drawable KOMPLE atlanır

Betikle üretilen mesh objelerinde bu alan `None` kalır ve export
"has no Sollumz materials!" der — materyal aslında oradadır.
`ob.sz_lods.high.mesh = ob.data`.

### ⛔ Her drawable'da `Color 1` olmalı

Motor doğal/yapay ambient'i vertex renginin `.r`/`.g` kanallarıyla kapıyor,
`decal.sps` de harman katsayısını alfasından okuyor. OBJ'den gelen mesh'te bu
katman **hiç olmaz**. `(1,1,1,1)` yaz — ve `.color` değil **`.color_srgb`**
kullan (`.color` gamma çözer).

---

## 4. ⛔ Transformu SIFIRLAMA, VERİYE PİŞİR

Geometriyi MLO-yerel dünya koordinatında üretiyorsan katmanların transformu
zaten identity'dir. Ama **yerleştirilmiş** bir obje (konum + dönüş taşıyan)
körlemesine `matrix_basis = Identity` yapılırsa **orijine ışınlanır**.

Ölçüldü: ceset bbMin `(15.94, 36.55, −9.28)` iken sıfırlanınca
`(−0.408, −0.083, −0.506)` oldu — 40 m ötede, oyunda görünmez.

```python
if c.matrix_world != Matrix.Identity(4):
    c.data.transform(c.matrix_world)     # veriye PİŞİR
c.matrix_basis = Matrix.Identity(4)
```

⛔ `bpy.ops.object.transform_apply` operatörüne güvenme — sessizce hiçbir şey
yapmayabilir.

---

## 5. ⛔ `matrix_world` okumadan önce `view_layer.update()`

Parent atadıktan / obje oluşturduktan sonra depsgraph güncellenmeden
`matrix_world` okunursa **bayat değer** döner. Bu oturumda iki kez yanlış
teşhise yol açtı: ışıklar `(0,0,0)` göründü, ceset `(27, 75, −18)` göründü —
ikisi de aslında doğru yerdeydi.

---

## 6. ⛔ KOORDİNAT UYDURMA — veritabanında duruyor

Dünya koordinatı gerekiyorsa tahmin etme:

```
assetdb.py where <model>      # dünya konumu (MLO içindekiler dahil)
assetdb.py near <x> <y> <z>   # çevresinde ne var
```

Ölçüldü: asansör `v_2_bds_mesh_lift` → `vec3(286.05, −1350.90, 24.94)`.
Elle uydurulan değer 55 m ötedeydi ve "yanlış yere mi bakıyorum" sorusunu
gereksiz yere açtı.

---

## 7. ytyp OVERRIDE deseni ve doğrulaması

MLO'nun kendi ytyp'sini değiştirmek için **aynı adla** `stream/` içine koy.
⛔ `data_file 'DLC_ITYP_REQUEST'` **EKLENMEZ** — çift kayıt yapar.
(Yeni bir ytyp üretiyorsan ekle; override'da ekleme.)

### Yamalar üst üste binmeli

Her üretim vanilla'dan değil **önceki çıktıdan** okumalı. Bu oturumda canlı
ytyp (88 arketip / 585 entity / `attachedObjects` 20) çözülüp doğrulandı,
sonra üstüne binildi (93 / 590 / 25). Boyut farkı (25.758 vs 25.901 bayt)
**içerik farkı değil**, PSO paketleme varyansıdır — boyuta bakıp "farklı
dosya" deme.

### `.ytyp` okuma/yazma

`xml_to_res.ps1` **`.ytyp` desteklemez** ("desteklenmeyen uzantı") ve
CodeWalker.Core'da `XmlYtyp` tipi **yoktur**. Doğru yol `build_ytyp.ps1`
(genel `XmlMeta` içe aktarıcısı). Geri okuma:

```powershell
$y = New-Object CodeWalker.GameFiles.YtypFile
$y.Load($bytes)        # TEK argümanlı overload — RpfFileEntry İSTEMEZ
```

⛔ `Load($bytes, $rpfEntry)` ile çağırmak `.ytyp`'de **patlar** ve dosya bozuk
sanılır. `.ypt` için tersi geçerlidir (o `RpfFileEntry` ister) — ikisini
karıştırma.

---

## 8. ⛔ YANLIŞ TEST "YOK" SONUCU ÜRETİR — üç kez yaşandı

Doğrulama yazarken aracın/formatın sınırını hesaba katmazsan "eksik" sanırsın:

| yazılan test | dönen | gerçek |
|---|---|---|
| `.//Texture/Name` XPath | boş | doku adı `Item/Name` altında, **3 doku vardı** |
| ikili dosyada string arama | bulunamadı | ytyp `timecycleName`'i **hash** tutar |
| `YtypFile.Load($d, $null)` | "Value cannot be null" | yanlış overload, dosya sağlamdı |

**Kural (kataloğun genel kuralı):** *bir aracın bir şeyi göstermemesi, o şeyin
yok olduğu anlamına gelmez.* Ölçüm aracını da denetle.

Ek: **Blender yolu `//x.dds` şeklinde görelidir**; Windows'ta
`os.path.basename('//x.dds')` bunu UNC kökü sanıp **boş string** döndürür.
`bpy.path.abspath()` ile çöz.

---

## 9. Ölçülmüş asansör kabini (v_coroner BodyStorage)

MLO-yerel koordinat, ışın ızgarasıyla ölçüldü:

| yüzey | konum |
|---|---|
| sol / sağ duvar | x = 14.485 / 18.212 |
| tel kafes (arka) | y = **35.196** — `ah_meshfence1`, tek düzlem, 2 yüz |
| dolu duvar | y = 35.12 → kafesle arasında **7.6 cm** var |
| ön (açık ağız) | y ≈ 38.10 |
| zemin / tavan | z = −9.707 / −6.920 |
| oda ağzının dışı | tavan −6.51 · zemin −9.70 · duvar x 13.44 / 25.86 |

⛔ **Asansörün kendi ışığı YOKTUR:** `v_2_bds_mesh_lift.ydr`'de `<Lights>`
düğümü **var ama boş**. Kabine menzili yeten vanilla ışık sayısı ölçüldü:
**0**. Aydınlatma tamamen senin koyduğun ışıklardan gelir.
