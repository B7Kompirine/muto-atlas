# Sollumz Discord `#resources` — kaynak ve araç kataloğu

**Kaynak notu — kural değil.** Kanalın tamamı: **12.09.2022 → 12.06.2026,
110 mesaj**, 53 ek indirildi. Ham döküm ve dosyalar:
yerel indirme klasörü (`_manifest.tsv` = dosya → CDN linki;
linkler ~24 saatte bayatlar).

⛔ Buradaki hiçbir sayı **ölçüm değildir** — topluluk iddiasıdır. Bir değeri
asset'e ya da koda taşımadan önce `assetdb.py` ile doğrula
(`sources/external-tools.md` giriş kuralı burada da geçerlidir).

Bu dosya bir **indekstir**: "böyle bir araç / şablon / referans var mı?"
sorusunun cevabı. Yöntem dallarda, indeks burada.

---

## Bir işe girmeden önce buraya bakılacak durumlar

| durum | ne var |
|---|---|
| iç mekân / MLO vertex boyama | §3 R\* iç mekân renk şeması |
| decal · kenar geçişi · terrain maskesi | §4 geonodes araçları |
| import edilmiş drawable temizliği | §5 standart temizlik yordamı |
| LOD ymap / YDD düzenleme | §6 şablonlar + `nametables.rpf` |
| ped rest pose · IK rig · araç oturuşu | §7 hazır `.blend` dosyaları |
| ışık · timecycle · lightshaft | §2 |
| bake · spec/gloss · Substance | §9 |
| ymap/ytyp toplu işlem · MLO export · su | §10 |
| partikül önizleme · kan efekti | §11 |
| R\* nasıl yapmış — referans dosyası | §12 iç mekân kütüphaneleri, `LS.zip` |

---

## 1. Shader / materyal

- **4 katmanlı (blend) shader** — `Colour1` vertex color: layer0 siyah,
  layer1 mavi, layer2 yeşil. `texcoord0` ana dokular içindir. Shader'da
  `lookup sampler` varsa maske = **`Colour0`'ın alfa kanalı** + `texcoord1`.
- **Ayna gibi yüzey** — `SpecularFalloff` çok yüksek + `SpecularFresnel` çok
  düşük + `SpecularIntensity` artır.
- **Renkli su** — `water_poolenv` shader'ı, parametre **`FogColor`**
  (RGB/255; alfa = görüş derinliği).
- **İki mesh birleşince doku bozuluyorsa** iki objenin **UV map adları aynı
  olmalı**.
- **Tint shader düzeltmesi** (mevcut projede) — geometry nodes içindeki
  IMAGE_TEXTURE düğümlerinin `interpolation`'ını `Closest` yap
  (snippet ham dökümde).
- **UV katmanlarını toplu yeniden adlandır** (`UVMap 0`, `UVMap 1` …) —
  Vicho snippet'i, ham dökümde.
- Cam tonlama örnekleri → `glass.blend` · ped spec haritası anlamı →
  `ped_spec_meaning_fuller.png`.

> Doku boyutunun ikinin kuvveti olması burada da tekrarlanıyor; kural
> gövdededir (`trunk/gta-fundamentals.md` §5), buradan alınmaz.

## 2. Işık / gölge / timecycle

- **Lightshaft:** `flags = 99` + `Direction Amount = 0` → yalnız güneş
  vurduğunda görünür ve güneş yönünü takip eder.
- **Işık projeksiyon dokusunu Blender'da önizleme:** Cycles + emission +
  Node Wrangler `CTRL+T`; Texture Coordinate bağlantısını **UV → Normal** al,
  image'ı **Repeat → Clip** yap, konumu mapping XYZ, bulanıklık `Radius`.
- **`lodlights` / `distlodlights` ayrımı:** `distlodlights.ymap` = renk/konum ·
  `lodlights.ymap` = yoğunluk, falloff, time flags, koni açısı, korona.
- **R\* iç mekân gölgeleri** `v_66_shadowmap2.ydr`, `v_26_shadowtrash.ydr` —
  *"oyundaki ışıklar bu tür gölgeleri asla üretmez"* (bake edilmiş gölge mesh'i).
- Işık culling plane rehberi (PDF) · Flashiness referans videosu ·
  `timecycle_mods_1..4.xml` birleşimi + 426 hava dosyası ·
  `timecycle-loader.zip` (oyunda `/timecycle <ad>` ile test).

## 3. Vertex color

- ⭐ **R\* iç mekân renk şeması:** kabuğun **alt yarısı yeşil→koyu yeşil**,
  **üst yarısı mavi→koyu mavi**. Dışarı açılan pencere/kapı boşluklarında ve
  güneş vuran her yerde **yoğun kırmızı→sarı** (sahte aydınlanma).
  2 katlıda birinci kat ağırlıklı yeşil, ikinci kat ağırlıklı mavi.
- **Yağmuru engelleme (MLO dışında):** collision mesh/primitive'in vertex
  rengine **`#32383A`**.
- **Sahte kumaş/rüzgâr:** herhangi bir tree shader + iki vertex color kanalı;
  `Colour0` siyah-beyaz (siyah = az hareket, beyaz = çok), `Colour1` normal
  vertex renkleri.
- Araçlar: **Vertex Color Master** (4.x fork'ları dahil) ·
  **Geonodes Paint Blend** `terrain_mask_v0_5.blend` (dört kanal otomatik).

## 4. Decal / geçiş

- **Geonodes Edge Decal Tool** → `decal.blend` + `Decal_tool.gif` — bina, zemin
  veya yol için geçiş mesh'i üretir, Asset Browser'a eklenir.
  Köşe-sarma / duvar hasarı decal işine doğrudan bakan tek hazır araç budur.

## 5. Geometri / mesh hijyeni

- ⭐ **Drawable import sonrası standart temizlik:**
  1. Edit mode → `M` → **Merge by Distance**
  2. Object Data Properties → Geometry Data → **Clear Custom Split Normals Data**
  3. Edit mode `ALT+J` (Tris to Quads): Max Face Angle **90°**, Max Shape Angle
     **90°**, Compare **UVs / Seam / Sharp / Materials** açık, **VCols kapalı**
- **Yüz yönü kontrolü:** Show Face Orientation — mavi doğru, kırmızı ters.
- ⛔ **Boş `.col` drawable = anında crash.** Mod parçasına geçince oyun anında
  çöküyorsa ilk şüpheli budur; sil ve yeniden export et.
- Primitive collision üretimi (Collider Tools) · mesh'ler arası vertex grubu
  aktarımı · weighted normal manipülasyonu (videolar ham dökümde).

## 6. LOD

- `FiveM_LOD_template_2_levels.zip` (2 seviye ymap/model parenting şablonu) ·
  `lod_tuto.zip` + `lod_tutorial.blend` (2025, oyunda denenebilir stream).
- ⛔ **LOD (YDD) düzenlemek için `nametables.rpf` şart** — GTA 5 **ana
  dizinine** konur. İçinde animasyon ve ses adları da var.

## 7. Ped / animasyon / rig

- Rest pose şablonları: `A_pose.blend`, `T_pose.blend`, `FEMALE_A-POSE.blend`,
  modelleme ölçeği `ped_scale.fbx`.
- IK rig'leri: `IK_ForGTA.blend` · `Freemode_F_IK.blend` ·
  `Freemode_M_IK.blend` · **`Freemode_M_IK_Fixed.blend`** ← root dönüklüğü
  hatası giderilmiş sürüm, **bunu kullan**.
- Araç oturuşu referansı: `STANDARD_driving_layout.blend`,
  `LOW_driving_layout.blend`.
- **FakeBones** (armature görselleştirme) · animasyon flag hesaplayıcı
  (`vespura.com/fivem/animations/`).

## 8. Fragment / yıkım / RayFire

- `yft.blend` — 3 parçaya ayrılan örnek fragment.
- **`blender_rayfirev`** — bake edilmiş animasyonlu mesh'i Sollumz 2.1+
  drawable'ına çeviren eklenti (`github.com/ultrahacx/blender_rayfirev`).

## 9. Doku üretimi / bake

- **GTA baker (Substance)** `Gta_baker.sbs`, `GTA_ColorSpec.sbsar`:
  Color → `COO` curvature overlay · `AOMO` AO · `NO` normal/height.
  Spec → `Invert` (GTA **gloss** kullanır, ters çevrilir) · `COO` · `AOMO` ·
  `MMO` metallic çarpanı. *Hiç metallic olmayan siyaha düşmez — biraz spec
  hep gerekir.*
- Prosedürel materyal + bake playlist (Ryan King Art) · seamless doku videosu ·
  kıyafet dokusu renk/detay (Photoshop) · **Folders2YTD** (DDS klasörü → `.ytd`;
  artık Vicho's Tools ile Blender içinde de yapılabiliyor).

## 10. Harita / MLO / FiveM tarafı

- **Arbolito** — YMAP splitter/merger, train tracks mover, YNV→ONV, prop
  replacer (`github.com/Hancapo/Arbolito`).
- **VichoTools** — seçimi metne kaydet, **MLO transformlarını çalışır
  `.xml.ymap` olarak export et**, transform kopyalama, YTD araçları.
- **dolu_tool** · **ht_mlotool** (MLO audio occlusion) ·
  `tiwabs_audio_door_tool` (özel kapı sesi) · `doortuning.zip`.
- **WaterEditor** (Blender'da `water.xml`) · **Water XML Merger** (web).
- Dinamik ymap yükleme/boşaltma (`Dynamic-loaded-map-fivem`).
- **Vanilla iç mekânı düzgün devre dışı bırakma:**
  ```lua
  CreateThread(function()
      local oldinterior = GetInteriorAtCoordsWithType(0.0, 0.0, 0.0, 'int_name')
      DisableInterior(oldinterior, true)
      UnpinInterior(oldinterior)
  end)
  ```
- ⚠️ **`str_requestFlush` artık varsayılan kapalı.** Test ortamında açmak için
  `server.cfg` / `env.cfg` sonuna: `setr str_enableFlush true`
- Stream şablonları: `FiveM_Map_Resource.7z`,
  `FiveM_server_scenarios_example.zip`.

## 11. Partikül / efekt / kan

- **eco_effect** (`github.com/Ekhion76/eco_effect`) — partikül efektlerini
  **oyunda canlı** izleme, arama, ölçek ve seçenek değiştirme.
  (`echo effect` ile aynı işi yapan ikinci araç —
  `branches/particle/ready-made-effects.md`.)
- **`.ypt` keyframe property dokümantasyonu** — `github.com/krzysiula3000/ypt-research`.
- **BloodFX** — `bloodfx.dat` alan anlamları, aşağıda.

### `bloodfx.dat` alanları (Fadilj araştırması, üçüncü taraf)

| alan | anlamı |
|---|---|
| **PROB** | efektin kullanılma olasılığı; `1.0` açık, `0.0` kapalı. Ped damage efektleri için **ayrı** bir PROB var (yalnız mermi deliği girdisi) |
| **SPLAT / SPRAY / MIST DCL ID** | her biri **NORM** ve **SOAK** varyantıyla; kullanılan efekti doğrulayan decal ID'leri |
| **COL_TINT (R G B)** | yerdeki kan sıçramasının rengi |
| **SPRAY DOT_THRESH** | yerde kaç büyük leke/birikinti üretileceği (yüksek = daha çok) |
| **MIST THRESH** | küçük serpinti noktalarının yakınlığı (yüksek = daha yakın) |
| **LOD RANGE (HI/LO)** | efektin görülebildiği mesafe; HI yüksek kaliteli sürüm |
| **NUM PROBES (HI/LO)** | **belirsiz** — yazar değerleri değiştirip fark görememiş |
| **PROBE DISTA** | atış normalinden yüzey aramak için gidilen mesafe; yüzey bulursa **Diffuse A** |
| **PROBE DISTB** | probe A'nın **yarısından aşağı** arar, **yalnız Diffuse A gerçekleşmediyse**; bulursa **Diffuse B** |
| **PROBE VARITN** | kanın ne kadar uzağa / çok / büyük yayılacağı |

⛔ Dosyadaki her sayısal girdinin **hem giriş hem çıkış (entry / exit)**
karşılığı olmak zorundadır. Size ve speed evolution'ları efektin ne kadar
hızlı ve büyük gösterileceğine karşılık gelir.
Tam metin: `sollumz-discord-resources\BloodFX_Documentation.md`.

## 12. Referans kütüphaneleri ve diğer

- `Interior_References.7z` (207 MB) · `Interior_References_V2.7z` (849 MB,
  25 iç mekân) — ⚠️ **V2, V1'in üst kümesi DEĞİL**: `v_bahama` ikisinde de var
  ama V1'de 93 MB, V2'de 19,6 MB — farklı export'lar. **İkisini de tut.**
- `LS.zip` (76 MB) — **konum ve ölçek referansı için tüm Los Santos (SLOD2)**.
- `Procedural_IDs.txt` — collision YBN'lerde çim/çöp/döküntü spawn eden
  materyal ID'leri (256 satır).
- `vmt_types.txt` — 38 adet `VMT_` carcols.meta kozmetik tipi.
- `custom_radios.zip` · `Vehicle-Siren-Meta-Files.zip` · `customped.zip`
  (SP/RageMP ped DLC şablonu) · `asset-browser-guide.pdf`.
- `blender-3.3.7-windows-x64.zip` **indirilmedi** (277 MB) — shadow map render
  pass'i 3.4+ ile seçilemediği için kanalda taşınabilir 3.3.7 tutuluyor.
  Gölge bake'i gerekirse akılda tutulacak tek sebep budur.
