# GTA V temelleri — motorun kendi kuralları

**Gövde dosyası.** Burada motorun **her dalda ve her yaprakta** geçerli olan
temel kuralları var: veri modeli, dosya tipleri, ad/hash sistemi, koordinat,
**doku ve DDS**, streaming, kaynak formatı, istemci/sunucu ayrımı. Bunlar
"bizim yöntemimiz" değil, **oyunun kendi sözleşmesidir** — dal onları değiştiremez,
yalnız üstüne kendi kuralını koyar.

Buradaki her sayı ölçümdür; kaynağı satırında yazılı. Çalışma disiplini ve
araç davranışı ayrı: `SKILL.md` ve `trunk/tool-pitfalls.md`.

---

## 1. Veri modeli — üç ayrı şey, karıştırma

GTA'da "bir obje" tek şey değildir. Üç katman vardır ve her biri **ayrı dosyada**:

| katman | dosya | ne söyler | değiştirirsen |
|---|---|---|---|
| **archetype** | `.ytyp` | objenin **ne olduğu**: model adı, bbox, `lodDist`, bayraklar, `specialAttribute`, physics/texture sözlüğü, extension'lar | o modeli kullanan **her yer** etkilenir |
| **entity** | `.ymap` (ya da MLO'nun kendi listesi) | objenin **nerede olduğu**: konum, rotasyon, `lodLevel`, `parentIndex`, entity bayrakları | yalnız o yerleştirme |
| **drawable** | `.ydr` / `.ydd` / `.yft` | objenin **nasıl göründüğü ve fiziği**: mesh, materyal, gömülü doku, iskelet, bound, ışık | görsel + fizik |

Sonuçları:

- Bir prop'un "kapı olması" drawable'da değil **archetype**tedir (`specialAttribute`).
  Modeli değiştirmek kapı yapmaz; ytyp düzeltilir.
- Bir objeyi haritadan kaldırmak **entity** işidir, archetype'a dokunulmaz.
- Aynı archetype haritada N yerde olabilir (`assetdb.py where`); ytyp'yi
  düzeltmek N yeri birden etkiler — etki alanını **önce ölç**.
- **MLO iç mekânı ayrıdır:** entity listesi ymap'te değil **ytyp'nin içindedir**;
  dışarıdan ymap ile prop koymak oda/portal sistemi tarafından elenir.
- Archetype adı `.ytyp` içinde, entity `archetypeName` ile ona **hash üzerinden**
  bağlanır (§3). Ad tutmazsa entity sessizce hiç oluşmaz.

## 2. Dosya tipleri — hangi uzantı ne taşır

| uzantı | ne | binary yazan | not |
|---|---|---|---|
| `.ydr` | drawable — mesh + materyal + gömülü doku + ışık + bound | Sollumz `NATIVE` | tek model |
| `.ydd` | drawable **dictionary** — birden çok drawable | Sollumz | ped bileşenleri, LOD çocukları |
| `.yft` | fragment — iskelet + `PhysicsLODGroup` (kırılabilir / per-bone collision) | Sollumz | ⛔ ped `.yft`'i **fiziksiz** gönderilir |
| `.ybn` | ayrı collision (bound) | Sollumz | harita collision'ı burada |
| `.ytd` | doku sözlüğü | `dds_to_ytd.ps1` | §5 |
| `.ycd` | klip (animasyon) sözlüğü | ⛔ **Sollumz XML yazar** → ayrıca binary'ye derlenir | format sisteminin dışında |
| `.yed` | expression sözlüğü — kural tabanlı kemik hareketi | ⛔ Sollumz yazamaz; CodeWalker **okur, yazamaz** | |
| `.ytyp` | archetype tanımları (+ MLO odaları/portalları, `compositeEntityTypes`) | `meta_xml_to_bin.ps1` (`MetaFormat.RSC`) | ⛔ `YtypFile.Save()` composite'i düşürür |
| `.ymap` | entity yerleştirmeleri (+ grass batch, car generator) | aynı | |
| `.ypt` | partikül efekti | `ypt_xml_to_bin.ps1` | ⛔ CodeWalker XML turu `FxcFileHash`/`VFT` yazmaz |
| `.yld` | Sollumz destekliyor — **bizde ölçüm yok** | — | iddia etme, ölç |

Sollumz'un **8 uzantıda** binary yazdığı ölçüldü (`.ybn .ydr .ydd .yft .yld
.ytyp .ymap .ytd`, `pymateria` kuruluysa); `.ycd` bu sistemin dışındadır.
Ayrıntı `trunk/tool-pitfalls.md` Ayrıntı B.

## 3. Ad ve hash — her şey joaat ile bağlanır

- Motor adları **joaat (Jenkins one-at-a-time)** ile hash'ler; dosyalarda
  çoğu yerde ad değil **hash** durur. Bağ ada göre değil hash'e göre kurulur.
- **CodeWalker bilmediği adı `hash_XXXXXXXX` yazar** — bu "bozuk" değil,
  *çözülmemiş* addır. Stream dosya adlarının / bilinen adların joaat'ini
  hesaplayıp eşle; yeni adı **düz metin** yaz, derleyici hash'ler.
- ⛔ **Varlık adında büyük harf olmaz.**
- ⛔ **Ad çakışması sessizdir:** aynı adlı üç `.ytyp`'den yalnız biri yüklendi;
  aynı adlı iki doku farklı sözlükte farklı içerik taşır (175 kopyadan 22'si).
  Kendi ürettiğin her ytyp/doku/klip adı **benzersiz** olmalı.
- `.ycd` klibi **`<Hash>` ile bulunur**, adla değil: alan boşsa klibin adı yok
  demektir, `TaskPlayAnim` bulamaz ve hata da vermez. Motorun sözleşmesi budur;
  hangi aracın bu alanı doldurup doldurmadığı → `trunk/tool-pitfalls.md` §1.

## 4. Koordinat, birim, yön

- **1 birim = 1 metre**, dünya **Z-up**, sağ el düzeni.
- **Ped −Y yönüne bakar** (rest pozunda); **klip uzayında ileri +Y**.
  Model ters bakıyorsa mesh 180° Z çevrilir — doğrulamalar geçer, ped oyunda
  geri geri yürür.
- **Kemik uzayı ≠ model uzayı.** Işığın `Position/Direction/Tangent`'ı, ped'e
  bağlanan prop'un ofseti, fragment bound'u — hepsi **kemik uzayındadır**.
- **Takılı obje objenin ORIGIN'inden konumlandırılır**, iskeletinden değil →
  hizalama modele pişirilir.
- **`CreateObject` collision-bound TABANINA, `CreateObjectNoOffset` ORİGİN'e** koyar.
- Blender tarafı ayrı bir uzaydır: Sollumz kemiklerinde local Y = head→tail;
  FBX armature'u 90° X + 0.01 ölçek taşır → karşılaştırma **dünya uzayında**
  (`matrix_world`) yapılır.

## 5. Doku ve DDS — motorun sert kuralları

**Bu bölüm her dalda geçerlidir**: harita, prop, silah, ped, kıyafet, partikül,
decal, ışık projeksiyonu. Ölçüm: 400+ vanilla malzeme `.ytd` / 1.135 doku,
ayrıca `core.ypt`'nin 107 gömülü partikül dokusu.

### Format
- ⛔ **DDS zorunlu. PNG/JPEG kabul edilmez.** Sollumz'a PNG paketli veri
  verilirse *"packed data is not in DDS format"* der ve dokuyu **atlar** —
  `.ytd` ~300 bayt (boş) çıkar, export hata vermez.
- ⛔ **Sollumz gömülü dokuyu DİSKTEKİ DDS'ten paketler.** Blender içinde
  yükleyip `scale()`/`save()`/`pack()` yapmak yetmez: `.ydr`'ye **16×16 taslak**
  gömüldü, hata çıkmadı, kusur ancak geri okumada göründü. Piksel işini
  Blender dışında yap (Pillow `pixel_format='DXT5'`).
- **Gömülü doku adı DOSYA ADINDAN gelir**; `img.name` ataması yok sayılır.

### Boyut
- ⛔ **Her iki kenar da ikinin kuvveti olmalı** (2/4/…/1024/2048/4096).
  Değilse doku **titrer**. Dikdörtgen serbesttir — `4096×256` çalışır.
- Ölçülen medyan: diffuse/normal/spec **üçünde de 512**, maksimum 2048.
- **Kare gereken yerler ayrıca vardır:** ped `_r` (skintone) spec maskesi
  kare olmak zorunda — `1024×512` UV'yi gerer ve ten rengini bozar.
- Bake çıktısı açıklığın oranına göre üretildiyse (`1024×442` gibi) **yeniden
  ölçeklenir**; kare render + dikdörtgen açıklık siyah kenarı içeri gerer.

### Sıkıştırma ve mip (ölçüldü)
| harita | vanilla dağılımı | kural |
|---|---|---|
| normal | DXT1 278 · DXT5 18 · ATI2 6 | **DXT1** (%92) |
| spec | DXT1 98 · DXT5 1 | **DXT1** (%99) |
| diffuse | DXT1 570 · DXT5 161 | alfa yoksa **DXT1**, varsa DXT5 |
| partikül | DXT5 75 · DXT1 32 — **107/107 DXT** | sıkıştırılmamış/tek mip örnek **yok** |

- **Mip zinciri şart:** `log2(kısa kenar) − 1`, 4×4'te biter (832/921 = %90,3).
  Tek mip'li doku vanilla'da yok.
- ⛔ **DXT1 alfa taşımaz.** Delikli/cutout doku DXT1 yazılırsa **delikler
  kapanır** — dosya geçerli, doku geçerli, hata yok. Alfa gerekiyorsa DXT5
  ya da `A8R8G8B8`.
- **Normal ve spec haritaları `Non-Color`**; sRGB okunursa kabartma yönü ve
  parlaklık sessizce yanlış çıkar.

### Sözlük (`.ytd`) ve gömülü doku
- ⛔ **`.ytd` XML şeması:** `<TextureDictionary>` altında **doğrudan `<Item>`**;
  `<Textures>` sarmalayıcısı **yoktur**. Yanlış sarmalayıcı hata vermez,
  **57 baytlık boş sözlük** üretir — tek belirti dosya boyutudur.
- **Gömülü mü sözlükte mi, dala göre değişir:** vanilla harita modellerinde
  gömülü doku **yoktur** (dış sözlük + `gtxd.meta` zinciri); freemode giysisinde
  spec+bump gömülür, **diffuse gömülmez** (oyunda değişebilsin diye);
  non-streamed ped'de **hiç gömülü doku olmaz**. Akıtılan kendi ped'inde de bu düzen çalışır: çizimde gömülü doku yok, örnekleyici
  adları kurala uygun (`uppr_diff_000_a_uni`, `uppr_normal_000`, `uppr_spec_000`), dokular `<ped>.ytd`'de.
  Ölçüm: 2026-09-11, 1 oyun testi — `a_m_y_beach_01` yerine akıtılan ped (DXT1 diffuse + düz normal/spec): doku doğru renklerle göründü, F8 hatası yok.
- Arketip `textureDictionary`'yi referans etmiyorsa oyun o sözlüğü **hiç
  yüklemez** — ışık "çalışır" görünür, projeksiyon deseni olmaz.

### Araçlar
`make_dds.py` (DXT5 + mip; partikül sprite'ı için alfa dayatır) ·
`bake_to_gta.py` (PBR → GTA; malzeme haritaları opak, alfa dayatmaz) ·
`dds_to_ytd.ps1` (klasör → `.ytd`, **geri okur**) · `ytd_index.ps1` / `ytd_find.ps1`
(vanilla doku sözlüğü indeksi).
- **Pillow'un DXT kodlayıcısı kalite tavanı değil.** Blok başına temel eksen aralık uydurma + bir en küçük kareler turu (saf numpy,
  Blender Python'unda da çalışır — orada Pillow yok) her örnekte daha iyi çıktı. Ölçüm: 2026-09-11, Pillow 12.3, Pillow ile çözüp PSNR —
  vanilla `a_m_y_beach_01` diffuse 512² ×3: Pillow DXT1 42.9–44.6 dB, numpy 45.3–46.7; spec DXT5 alfa 45.8 → 69.8; 1024² mip'li 0.6–0.8 s.
  Sollumz 2.9 DXT DDS'i `.ytd`'ye olduğu gibi paketler (geri okumada çıkarılan yük bayt bayt aynı).
- ⛔ **DXT1'de `c0 <= c1` çözücüyü 3 renk kipine sokar: indeks 3 = şeffaf siyah** (BC1 biçim tanımı). Tek renkli blokta iki uç
  eşit çıkar → uçları sırala (büyük olan `c0`), eşitse bütün indeksleri 0 yaz. Kendi kodlayıcını düz renkle sına: 2026-09-11 ölçümünde
  32² 0.5 gri → Pillow çözümünde en büyük sapma 4 (565 nicemlemesi, iki kodlayıcıda da 37.3 dB), siyah piksel 0.

## 6. Streaming ve kaynak

- `stream/` içindeki dosyalar **otomatik** akar; ytyp/ymap/meta ise
  `fxmanifest.lua`'da **`data_file`** ile bildirilmelidir
  (`DLC_ITYP_REQUEST`, `TIMECYCLEMOD_FILE`, `WEAPONINFO_FILE`, …).
  Kaydedilmeyen dosyayı oyun **hiç aramaz**.
- ⛔ **Asset değişti → sunucudan çık, yeniden bağlan.** Stream cache'lenir,
  `restart` yetmez.
- ⛔ **Bozuk bir stream varlığı kaynağın TAMAMINI sessizce düşürür**:
  sunucu "Started resource" yazar, istemcide hiçbir komut kaydolmaz, F8'de
  hata yoktur. Komutlar birden yok olduysa Lua'ya değil `stream/`e bak.
- ⛔ **Aynı dosya iki klasördeyse FiveM birini sessizce yok sayar** →
  "görünmüyor" denince ilk bakılacak yer **sunucu logudur**.
- **Vanilla dosyanın birden fazla sürümü vardır** (base + `patchdayNNng` +
  DLC). Hangisinin yükleneceği DLC sırasına bağlıdır ve **dosyalardan
  okunamaz** — çakışma gizlenmez, **raporlanır**. `hei_` (mpheist) ikizleri
  bunun en sık hâlidir: gerçekte yüklenen odur.
- Escrow'lu (`.fxap`) bir kaynağın stream dosyası **şifrelidir**; kopyalarsan
  istemci çöker.

### Pool taşması — crash'in bir numaralı sebebi

- ⛔ **Sert tavan: sunucudaki toplam stream dosyası 65535.** Aşınca
  `ERR_STR_FAILURE: trying to add more assets to pgRawStreamer` ile **fatal**.
  Bu sayı **hiçbir ayarla artırılamaz**; çare asset birleştirmedir.
  İstemci konsolunda (F8) `assetscount` ile ölçülür — **sunucu komutu değildir.**
- **Pool büyütme `server.cfg`'de `increase_pool_size` ile yapılır.** Eski
  "gameconfig.xml fix" kaynakları **artık yanlış cevap**: FiveM kendi
  `gameconfig.xml`'ini ship edip doğruluyor ve elle düzenleneni geri yazıyor.
- ⛔ **Satırlar dosyanın EN ÜSTÜNDE, ilk `ensure`/`start`'tan önce olmalı.**
  Kaynaklar bir kez başlatıldıktan sonra pool değiştirilemez; aşağı kayarsa
  satır **sessizce etkisiz** kalır.
- ⭐ **Geçerli ölçüt dokümantasyon değil, sunucunun kendisidir.** Sınır aşılırsa
  konsola `Requested pool size increase is invalid: ... exceeds allowed limit of N`
  yazar ve o satır düşer, diğerleri işler. **Ölçüm (2026-09, build 3258):**
  docs `Building` için 20000 diyor, **sunucu 500 dedi**. Değeri yazdıktan sonra
  konsolda `pool` ara; uyarı yoksa kabul edilmiştir.
- ⚠️ Pool satırı değişince oyuncu **reconnect değil, oyunu tamamen kapatıp
  açmak** zorunda (`sv_enforceGameBuild` gibi davranır).
- ⚠️ `FragmentStore` artışı şu an **uygulanmıyor** (Cfx açık bug #3812).
- Ölçülen kabul edilen değerler (aynı kurulum): `TxdStore` 26000 ·
  `EntityDescPool` 20480 · `AnimStore` 20480 · `StaticBounds` 5000 ·
  `Object` 2000 · `fragInstGta` 2000 · `InteriorProxy` 450 · `Building` 500.

### Crash'i teşhis etmek

- Crash penceresi **iki kelimeli imza** (`ekim-michigan-lityum` gibi) + sıkça
  `modül.dll+offset` verir. Aynı crash **her zaman aynı imzayı** üretir.
  İmzayı insan diline çeviren resmî tablo:
  <https://github.com/citizenfx/fivem/blob/master/data/client/citizen/crash-data.json>.
- Dump'lar `%localappdata%\FiveM\FiveM.app\crashes\`. Tam dump için
  `CitizenFX.ini`'ye `EnableFullMemoryDump=1` (1-10 GB; işin bitince **sil**).
- **Hangi asset çökertti sorusunun otomatik cevabı yoktur.** Yöntem ikiye
  bölerek eleme (`stream` kaynaklarının yarısını kaldır, tekrarla).
- Sert crash yapanlar: **geçersiz TXD referansı**, **bozuk cloth verisi**,
  bozuk `.ytyp` (unmount sırasında `CDLCItypFileMounter`). Buna karşılık
  eksik collision, `.ytd`'de olmayan doku, kayıtsız archetype **sessiz
  görünmezliktir** — crash değil. İkisini karıştırma.
- Script'le 500 prop dizmek yerine **`.ymap` kullan**: ymap entity'si `Object`
  pool'unu değil `Building`/`EntityDescPool`'u yer ve ağ senkronu istemez.
- `SET_ENTITY_DISTANCE_CULLING_RADIUS` ve kardeşleri **resmî olarak
  deprecated**, "known, unfixable issues" deniyor — kullanma.

**Ölçüm:** bir test sunucusu, 2026-09-08, FXServer build 3258, 2.1 GB / 2140 stream
dosyası / 78 kaynak. Kaynaklar: `docs.fivem.net/docs/server-manual/server-commands`,
`citizenfx/fivem` issue #3812 · #3384, forum 5385215.

## 7. Kaynak formatı (RSC7)

- Binary `.y*` dosyaları **RSC7** kabuğudur ve **zlib sıkıştırmalıdır**.
- ⛔ **Dosya boyutu geçerlilik ölçütü DEĞİLDİR** — 32.768 baytlık açılmış
  `.ypt` kaydedince 3.077 bayt oldu; 15.056 → 15.904 bayt aynı içeriktir.
  **Tek geçerli ölçüt geri okumadır.**
- Yeniden dışa aktarım dosyayı %20–30 büyütebilir; bu bir kusur değildir.
- Yeni bir kaynak tipine başlarken ilk iş: **vanilla bir dosyayı XML'e döküp
  geri okumak ve ikili ile XML turunu alan alan karşılaştırmak** — aracın
  hangi alanları sessizce düşürdüğü ancak böyle görülür.

## 8. İstemci / sunucu

- **Harita objeleri networked DEĞİLDİR.** Durum sunucuda tutulur, her istemci
  kendi kopyasına uygular; yoksa yalnız sende hareket eder.
- Bir entity'yi oynatmadan önce **sahiplik**: `SetEntityAsMissionEntity` +
  `NetworkRequestControlOfEntity`; alınmazsa `Freeze`/`SetCoords`/`SetHeading`
  **sessizce yok sayılır**.
- **DUI/NUI istemci tarafıdır ve senkron değildir**; sayfanın JS'i okunabilir,
  mesajı taklit edilebilir → şifre/kod/fiyat karşılaştırması **sunucuda**.
- Partikül, decal, Euphoria tepkisi **görseldir ve istemci başınadır**;
  sonucu (hasar, ölüm, kilit) sunucu belirler.
- Native'in tarafı tahmin edilmez, sorgulanır (`fivem-natives` skill'i).

## 9. Render kovası ve vertex biçimi

- **Bir `.sps` iki şey seçer: shader PROGRAMI ve RENDER KOVASI.** Kova ayrı bir
  alandır ve **yazılabilir** — `.sps` ön ayarının getirdiğine mahkûm değilsin.
  Kovalar: `OPAQUE / ALPHA / DECAL / CUTOUT / NO_SPLASH / NO_WATER / WATER /
  DISPLACEMENT_ALPHA`. ⛔ **Opak kova alfayı hiç okumaz** (`emissive_clip.sps`
  OPAQUE'tir → delikler kapanır). Haritaya gömülü decal **bucket 2**.
- ⛔ **`.ydr`'ye yazılan ad `.sps` dosya adı değil, PROGRAM adıdır**
  (`emissive_alpha.sps` → `emissive`). Hash'i dosya adıyla karşılaştırmak
  yanlış teşhistir.
- Vertex biçimi `GTAV1`: Position, BlendWeights, BlendIndices, Normal,
  Colour0, TexCoord0, Tangent. **Geometri sayısı = materyal sayısı.**
- **`Color 1` vertex renk katmanı şart** (OBJ'den gelen mesh'te hiç yoktur):
  motor doğal/yapay ambient'i `.r`/`.g` ile kapatır, `decal.sps` harman
  katsayısını **alfasından** okur. Blender'da `.color` gamma çözer →
  **`.color_srgb`**. Vertex color karartması yalnız **bucket 0** geometriye
  uygulanır.
- **UV katmanının adı `UVMap 0`** — başka ad sessizce düşer. Arazi karışımı
  ayrıca `UVMap 1` ister; ped giysisinde `UVMap 1` **kan haritasıdır**, dokunma.

---

## Bu dosyaya ne girer, ne girmez

**Girer:** motorun her dalda geçerli sözleşmesi — veri modeli, dosya/ad/hash,
koordinat, doku, streaming, kaynak formatı, istemci/sunucu, kova.

**Girmez:** tek bir aracın davranışı (`tool-pitfalls.md`), bizim çalışma
disiplinimiz (`SKILL.md`), bir kategoriye özgü kural (`branches/<branch>/_branch.md`),
tek göreve özgü reçete (yaprak). Bir madde "yalnız X dalında geçerli" diye
okunuyorsa buraya değil, o dala aittir.
