# muto-atlas — yetenek durumu ve yol haritası

Son güncelleme: 2026-08-15 · Plugin v2.2.0 (muto) · 35 sorgu · 24 veri katmanı · 63 script

Bu belge üç soruyu ayırır: **ne yapabiliyoruz**, **ne kadar güvenilir**,
**ne eksik**. Güven oranları keyfi değil; aşağıdaki ölçekten geliyor.

## Güven ölçeği

| Bant | Anlamı |
|---|---|
| **%95+** | İki **bağımsız** kaynak kesişti *ve* büyük veri üzerinde çapraz doğrulandı |
| **%85–94** | Tek güçlü kaynak (motor dosyası / oyun verisi) + kısmi çapraz kontrol |
| **%70–84** | Tek kaynak, iç tutarlı, aykırı örnek bulunamadı |
| **%50–69** | Yapı doğrulandı ama ayrıntılar (alan adları, değerler) doğrulanmadı |
| **<%50** | İddia var, ölçüm yok |

⚠ Oran, **verinin doğruluğu** içindir; "bu işi yapabilir miyiz" değil.
Veri %95 doğru olsa da iş akışı test edilmemiş olabilir — ayrıca yazılı.

---

# 1. NE YAPABİLİYORUZ

## 1.1 Prop / obje / kapı — **%95**

```bash
assetdb.py show <ad>      # tam künye + yorum
assetdb.py door <ad>      # "kapı gibi açılır mı" kararı
assetdb.py search <parça> # ada göre arama
assetdb.py prop <parça>   # spawn edilebilir prop
```

**Dayanak:** 316.975 arketip (CodeWalker.Core ile GTA V'ten çıkarıldı) +
`specialAttribute` adları Sollumz 2.9 kaynağından + kapı yeteneği
`Enable Door Physics` bayrağının 1176 arketipteki dağılımından **ölçüldü**.

**Ne söyleyebiliriz:** objenin kapı olup olmadığını, hangi tür kapı olduğunu,
pivotunun nerede olduğunu, fragment mı olduğunu, hangi ytyp'te durduğunu,
`lodDist`/`bbox`/`physicsDict` değerlerini.

**Sınır:** `specialAttribute=6`'nın anlamı çelişkili (§4.2). 379 arketip
`specialAttribute=0` olduğu hâlde door physics taşıyor — tek başına
`specialAttribute`'a bakmak yetmez, araç ikisini birden raporluyor.

## 1.2 Bayrak çözme — **%97**

```bash
assetdb.py flags 1572872 --entity
assetdb.py flags 549584896
```

**Dayanak:** Sollumz `ytyp/properties/flags.py` (32 archetype + 32 entity
bayrağı) **ve** 316.975 arketip üzerinde çapraz doğrulama:
`clipDictionary` dolu 1308 arketibin 470'i `Has Anim`, 838'i `UV anims`
bitli, **açıklanamayan 0**; ters yönde yanlış pozitif de **0**.

**Ölçülmüş özel bulgu:** bit 65536 = **Underwater** (CodeWalker haklı,
Sollumz'un "Unused"'ı yanlış) — 3.145.882 entity'de 14 kez kurulu, hepsi
`prop_dock_bouy_*` ve `prop_rub_wheel_01`, liman/nehir ymap'lerinde.

Sihirli sayılar çözülü: `1572872` = LOD in Parented YMAP + Cast Static +
Cast Dynamic · `18350080` = Dont Render In Reflections + iki gölge biti.

## 1.3 Dünyada konum — **%90**

```bash
assetdb.py where <ad>                      # hangi ymap / hangi MLO
assetdb.py near <x> <y> <z> --radius 10
```

**Dayanak:** 3.054.420 entity (MLO iç mekânları dünya koordinatına açılmış),
`entities.db` 214 MB. CodeWalker'dan mekanik çıkarım.

**Sınır:** bağımsız çapraz doğrulama yapılmadı; MLO dönüşüm kuantiyonu
bilinen bir koordinatla bir kez sınanmıştı, sistematik değil.

## 1.4 Animasyon / klip — **%85**

```bash
assetdb.py anim <ara>          # dict + clip + süre + kemik
assetdb.py propanim <prop>     # bir prop'un gerçek animasyonları
assetdb.py clipfit <dict> <clip>  # bu klibi hangi model oynatabilir
assetdb.py bones <model>       # iskelet: kemik adı + tag
assetdb.py expr <ara>          # expression (.yed)
```

**Dayanak:** 269.413 animasyon, 315.964 klip, 478.055 iskelet satırı,
2.338 expression. Önceki turların ölçümleri (30 fps, kemik tag'leri,
`AnimationList` kuralı) sağlam.

**Sınır:** klip↔model uyumu kemik tag kesişimiyle tahmin ediliyor; oyunda
doğrulanmış örnek sayısı sınırlı.

## 1.5 ytyp extension'ları — **%95**

```bash
assetdb.py ext <archetype>     # 14 tipin tamamı
assetdb.py ptfx <prop|efekt>   # partikül kullanımı
assetdb.py ptfx --type 4       # fxType'a göre (Destroy)
```

**Dayanak:** 64.209 extension, 2.765 vanilla + 52 custom ytyp'ten, **0 hata**.
`prop_pallet_01a`'nın çıktısı videodan okunan XML ile **birebir** aynı.

**Kapsam:** Particle 57.221 · Ladder 3.266 · AudioCollisionSettings 1.649 ·
LightShaft 845 · SpawnPoint 615 · AudioEmitter 183 · ExplosionEffect 145 ·
WindDisturbance 131 · ProcObject 13 · Buoyancy 12 · Expression 10.

## 1.6 Partikül efekt kataloğu — **%92**

```bash
assetdb.py fx <ad> --exact     # "bu efekt var mı, hangi ypt'de"
assetdb.py fx steam            # arama
```

**Dayanak:** 1.240 `.ypt` tarandı (0 hata) → **2.549 benzersiz efekt**,
368 dosyada. `core.ypt` tek başına 895 efekt.

**Ölçülmüş kritik bulgu:** ytyp'teki `fxName` ile `.ypt`'deki efekt adı
**aynı değil** — 406 `fxName`'in yalnız **3'ü** aynen var, **265'i (%65,3)**
`ent_` öneki gerektiriyor, **138'i (%34)** hiç bulunamıyor.

**Çözüldü (bu tur):** `core.ypt` XML'e açıldı, `EffectRuleDictionary`'deki
**895 efektin 895'i** indekste — kaçan **0**. İndeks eksik değil. Adların
%68,2'si çözülüyor (%0,7 aynen · %65,3 `ent_` öneki · %2,2 önek+sonek);
kalan **%31,8 vanilla'nın kendi ölü referansları**.

**Neden %92, %98 değil:** ölü referansların *neden* öyle olduğu (sürüm
geçişi mi, DLC mi) kanıtlanmadı; ayrıca custom `.ypt`'ler taranmıyor.

## 1.7 Shader seçimi — **%90**

```bash
assetdb.py shader decal        # iş türüne göre: cam/emissive/terrain/kumaş/araç/su/çim
assetdb.py shader decal_dirt --exact
assetdb.py shader --buckets
```

**Dayanak:** 249 shader (Sollumz `Shaders.xml`) **+ ikinci kaynak**:
12.000 `.ydr` + 12.000 `.yft` tarandı, 177 farklı shader kullanımda görüldü,
**tabloda olmayan 0**.

**Render bucket ölçüldü:** decal shader'larının **%92,3'ü bucket 2**,
Opaque 5.482 kullanımda yalnız **1** kez. Sollumz varsayılanı Opaque —
değiştirilmezse neredeyse kesin yanlış. İstisna: `vehicle_decal` bucket 1.

## 1.8 Collision — **%90**

```bash
assetdb.py mat <ad|--index N>  # 185 materyal + 3 bayrak katmanı + ön ayarlar
```

**Dayanak:** 185 materyal (Sollumz kaynağı) + 12.000 `.ybn` taraması:
151 farklı indeks kullanılmış, **hepsi 0-183 aralığında, aralık dışı 0**.
`ANIMAL_DEFAULT = 171` bizim aylar önceki bağımsız ölçümümüzle **birebir**.

Üç bayrak katmanı ayrıştırıldı: materyal (16) · composite Type+Include (31) ·
arketip (32). Ayrıca Sollumz'un 7 hazır composite ön ayarı çıkarıldı.

## 1.9 LOD — **%85**

```bash
assetdb.py lod --size 8        # vanilla lodDist referansı
assetdb.py lodchain <ad>       # gerçek zinciri yürü
assetdb.py lodaudit            # kendi haritanı vanilla ile kıyasla
```

**Dayanak:** 3.145.882 entity (19.387 vanilla + 204 custom ymap), 0 hata.

**Ölçülmüş:** seviye zinciri düz merdiven **değil** (`SLOD1 → LOD` geçişi
hiç yok, SLOD1 SLOD2'nin yan dalı) · 7 seviye var, 5 değil · `ORPHANHD` en
yaygın · `childLodDist == çocuğun lodDist`'i %86 tutuyor, %14 tutmuyor.

**`lodaudit` gerçek kusur buldu:** `LOD in Parented YMAP` bitli ama
`parentIndex=-1` — vanilla'da **0/3.072.951**, bizde **3.575/72.931 (%4,90)**.

**Neden %85:** zincirin **%6,1'i çözülemiyor** ve sebebi bulunamadı (§4.1).

## 1.10 Çim / zemin — **%80**

```bash
assetdb.py proc <ad|--id N>
```

**Dayanak:** 255 Procedural ID (`procedural.meta`'nın `procTagTable`'ı),
113'ü dolu. Videodan okunan iki değerle sınandı (`15 = Green_Meadow_Flowers`,
`38 = MOUNTAINSIDE_DRY`), ikisi de tuttu. 12.000 `.ybn`'de 73 farklı
`proceduralId` kullanılmış, **aralık dışı 0**.

**Neden %80:** oyunda hiç test edilmedi; @ma sisteminin çok hassas olduğu
(üçgen boyutu, Grass Quality ayarı) biliniyor ama ölçülmedi.

## 1.11 Export formatı — **%98**

**Canlı test yapıldı** (Blender 5.2 + Sollumz 2.8, gerçek export, baytlar okundu):

| Ayar | Çıktı | İlk 4 bayt |
|---|---|---|
| `NATIVE`+`GEN8` | `x.ydr` 451 B | `52534337` = **RSC7** |
| `CWXML`+`GEN8` | `x.ydr.xml` 2.699 B | `3c3f786d` = `<?xm` |
| `NATIVE`+**ikisi** | `gen8/` **ve** `gen9/` | 451 / **558** B, ikisi RSC7 |

`.ycd` **format sisteminin dışında** — `ycdexport.py:574` doğrudan
`write_xml()` çağırıyor, `target_formats`'a hiç bakmıyor.

## 1.13 Decal — **A: %90 · B: %85**

**İKİ AYRI SİSTEM.** Karıştırmak en sık hata.

```bash
assetdb.py decal kan          # A: script'le (AddDecal)
assetdb.py decal --id 1010
assetdb.py shader decal       # B: haritaya gömülü (.ydr)
```

**A · Çalışma anı (%90):** `decalType` tablosu oyunun kendi
`common.rpf\data\effects\decals.dat`'ından çıkarıldı — **194 tip**,
ID 1010-10031, kategorileriyle. FiveM belgesindeki enum eksik; bu tam.
Her tipin varyant sayısı, `washable` ve `underwater` davranışı yazılı.
`PatchDecalDiffuseMap` ile kendi dokunu giydirmek mümkün.
**Neden %90:** tablo ayrıştırıldı ama **oyunda tek bir ID denenmedi**.

**B · Haritaya gömülü (%85):** reçete + 35 decal shader'ı + render bucket
ölçümü (%92,3 → bucket 2). **Neden %85:** uçtan uca hiç denenmedi.

## 1.14 Özel partikül üretimi — **%90 · OYUNDA DOĞRULANDI**

> Uçtan uca çalışıyor ve **tek komuta indirildi**. Sıfırdan yazılan `.ypt`
> + kendi ürettiğimiz DXT5 doku, FiveM'de `stream/` üzerinden yükleniyor
> ve oyunda çiziliyor. GTA'nın hiçbir efekti/dokusu/kuralı kullanılmadı.

```powershell
scripts\ptfx_yap.ps1 -Ad muto_spor -Renk 0.2,0.9,0.35 -Hedef <stream klasoru>
scripts\ptfx_yap.ps1 -Ad muto_x -Gorsel kendi.png -Boyut 0.4 -Yukselme 0.8 -Hedef <k>
```

Doku → XML → ikili → CodeWalker'ın atladığı alanlar → doğrulama → dağıtım.

**Oyunda doğrulanan:** kendi doku · renk · boyut · ömür · doğum oranı ·
yayılım · yukarı süzülme · opaklık · `.ypt`'nin FiveM'de streaming'i.

**Yol boyunca bulunan ve düzeltilen — hepsi sessiz hataydı:**

| Kusur | Belirti |
|---|---|
| `FxcFileHash` yazılmıyor | dosya geçerli, handle dolu, **hiçbir şey çizilmiyor** |
| Blok `VFT`'leri yazılmıyor | sınıf kimliği sıfır |
| `FileVFT` yazılmıyor | kök tip sıfır |
| `ShaderVar` VFT'leri yazılmıyor | doku bağını kuran nesne kimliksiz |
| Doku DXT değil (A8R8G8B8) | **kaynağın tamamı** istemcide düşüyor, Lua bile yüklenmiyor |
| `FxcTechnique='default'` | kapalı liste, shader çözülmüyor |
| Boş `m_tblrScalarKFP` | çarpan 0, sprite sıfır boyutta |
| Eksik keyframe yuvası | `Save()` NRE ile çöküyor, hangi yuva olduğunu söylemiyor |
| `Unknown*` alanına 0 | vanilla'da hiç geçmeyen değerler, mesafe bandı sıfırlanıyor |

Beşi de `ypt_xml_to_bin.ps1` içinde denetleniyor; sıfır kalırsa **exit 1**.

**Kalan %10 — tek eksik: sprite sheet animasyonu.** Gömülü dokuda kare
kare animasyon (kanat çırpma, alev dalgalanması) çalışmıyor. Ölçüldü:
aynı doku `core.ypt`'ten referansla dilimleniyor, bizim dosyaya gömülünce
dilimlenmiyor. Dört ölçümle daraltıldı, sebebi bulunamadı — tam tablo ve
sıradaki yön referans §7d'de. Tek karelik doku ile her şey çalışıyor.

## 1.12 Native denetimi — **%90**

```bash
python scripts/lint_lua.py <dosya>
```

7.191 native, apiset çözümü, uydurma-native tespiti.
**Bilinen yanlış negatif:** alt çizgili adlar (`GetGroundZFor_3dCoord`)
"native değil" diye işaretleniyor.

---

# 2. NE YAPAMIYORUZ

| İstek | Neden |
|---|---|
| Oyunda test | Sunucuya bağlanma/otomasyon yok; her doğrulama dosya düzeyinde |
| `.ycd` binary üretimi | Sollumz XML yazıyor → `xml_to_ycd.ps1` şart, tek yönlü |
| `.yed` binary üretimi | Sollumz yazamıyor; `muto` eklentisi gerekiyor |
| `.ytd` üretimi | Sollumz üretemiyor, Blender DDS yazamıyor |
| Ped fiziği (`.yft` Physics) | Sollumz'un yazdığı ped fiziği **oyunu çökertiyor** — fiziksiz gönderilmeli |
| Custom iskelet | Motor yalnız kendi ped iskeletini kabul ediyor |
| Grass batch indeksi | ymap `<GrassInstanceBatches>` düğümü indekslenmedi |
| Timecycle / ses / navmesh | Hiç dokunulmadı |

---

# 3. VERİ ENVANTERİ

| Katman | Satır | Kaynak | Güven |
|---|---:|---|---:|
| `archetypes.tsv.gz` | 316.975 | CodeWalker → GTA V | %95 |
| `entities.tsv.gz` + `entities.db` | 3.054.420 | CodeWalker | %90 |
| `ymap_lod.tsv.gz` | 3.145.882 | CodeWalker | %90 |
| `clips.tsv.gz` | 315.964 | CodeWalker | %85 |
| `anims.tsv.gz` | 269.413 | CodeWalker | %85 |
| `skeletons.tsv.gz` | 478.055 | CodeWalker | %90 |
| `ytyp_extensions.tsv.gz` | 64.209 | CodeWalker | %95 |
| `props.tsv.gz` | 21.630 | CodeWalker | %85 |
| `natives.index.tsv` | 7.191 | Cfx + GTA5 native db | %90 |
| `ptfx_effects.tsv.gz` | 2.549 | CodeWalker `.ypt` | %85 |
| `expressions.tsv.gz` | 2.338 | CodeWalker | %85 |
| `ptfx_files.tsv` | 368 | CodeWalker | %95 |
| `procedural.tsv` | 255 | `procedural.meta` | %80 |
| `shaders.tsv` | 249 | Sollumz + kullanım kontrolü | %90 |
| `collision_materials.tsv` | 185 | Sollumz + kullanım kontrolü | %90 |
| `shader_usage.tsv` | 177 | 24.000 model | %95 |
| `collision_usage.tsv` | 151 | 12.000 `.ybn` | %95 |
| `scenarios.tsv.gz` | 246 | CodeWalker | %80 |
| `collision_flag_presets.tsv` | 7 | Sollumz | %95 |
| `light_presets.tsv` | 6 | Sollumz | %95 |

---

# 4. AÇIK MADDELER — sırayla

## 4.1 LOD zincirinde %6,1 çözülemeyen — **öncelik: orta**

`parentIndex ≥ 0` olan 1.548.159 entity'nin 95.143'ü parent'ında bulunamıyor.
Somut vaka: `dt1_rd1.ymap`'in 643 entity'si `parentIndex` 0..77 istiyor,
`dt1_lod`'un **dört kopyasında da 42 entity** var.

**Elenen hipotezler:** ymap adı çakışması (`rpfPath` eklendi — 53k sahte
kopukluğu düzeltti ama bunu açıklamadı) · ymap iç adı ≠ dosya adı
(`mapName` eklendi — 3000 ymap'in 177'sinde gerçekten farklı, sonuç değişmedi).

**Sınanmamış:** `parentIndex` aynı seviyedeki birden çok ymap'in birleşik
listesine bakıyor olabilir · `.imap` grup dosyaları devrede olabilir.

## 4.2 `specialAttribute = 6` çelişkisi — **öncelik: düşük**

Motor adı `MLO_WATER_LEVEL` ("Defines water level for a MLO") ama 630
kullanıcının **%84'ü** SLOD değil, sıradan kırsal harita parçası
(`cs1_`/`ch1_` önekli, 20 ytyp, `lodDist` medyanı 80).

**Sınanabilir:** bu arketiplerin `where` ile su yakınında olup olmadığına bak.

## 4.3 ✅ `.ypt` alan adları — KAPANDI

`core.ypt` XML'e açıldı (45,5 MB) ve gerçek şema okundu: 10 emitter keyframe
özelliği (`ptxEmitterRule:m_spawnRateOverTimeKFP` …), 27 particle behaviour
tipi, renk alanları (`ptxu_Colour:m_rgbaMinKFP` / `Max` / `emissiveIntensity`).

**Bonus tuzak:** keyframe değerleri `RedChannelColour` / `Green` / `Blue` /
`Alpha` diye adlandırılmış ama **renkle ilgisi yok** — genel dört kanal.
`m_spawnRateOverTimeKFP` içinde `RedChannelColour=4` "spawn oranı 4" demek;
`m_xyzMinKFP` içinde X/Y/Z demek. Anlam **hangi `<Name>` altında olduğuna** bağlı.

**Kalan tek boşluk:** rengi script'e açan bayrağın hangi alan olduğu
(`Colour` behaviour'unun `Unknown*` alanlarından biri). Partikül üretimi
%55 → **%85**.

## 4.4 ✅ Çözülemeyen `fxName`'ler — KAPANDI

İndeks eksik değil: `core.ypt` XML'iyle karşılaştırıldı, **895/895**.
Ad çözümü %68,2 (aynen / `ent_` öneki / önek+sonek). Kalan **%31,8 (129 ad)
vanilla'nın kendi ölü referansları** — `amb_water_roof_drips_short` 5.621 kez
kullanılıyor ve hiçbir ypt'de yok.

**Kalan soru (düşük öncelik):** bu ölü referanslar sürüm geçişinden mi kaldı,
yoksa yüklenmeyen bir DLC ypt'sinde mi — kanıtlanmadı.

## 4.5 Custom kaynaklarımızdaki 3.575 bayrak kusuru — **öncelik: orta**

`la_trees.ymap` (788) · `CityCentral.ymap` (477) · `highway.ymap` (381) …
`LOD in Parented YMAP` bitli ama zincirsiz. Vanilla'da bu kombinasyon **hiç
yok**. Zararlı olup olmadığı **test edilmedi** — `lodLevel` hepsinde
`ORPHANHD`, motor biti muhtemelen yok sayıyor.

**Nasıl kapanır:** tek bir ymap'te biti temizleyip oyunda karşılaştır.

## 4.6 Test edilmemiş iş akışları — **öncelik: değişken**

| İş | Durum |
|---|---|
| Decal üretimi | Reçete yazıldı, bucket ölçüldü, **oyunda denenmedi** |
| `.ypt` özel efekt | **Binary üretildi ve geri okundu**; oyunda görsel test bekliyor (`/spor`) |
| Grass batch | Yalnız video anlatımı; base-game hack'i gerektiriyor |
| @ma çim | Prosedürel ID tablosu var, **oyunda denenmedi** |
| Gen9 (Enhanced) | Export doğrulandı, **oyunda yüklenmedi** |

---

# 5. ARAŞTIRILMASI GEREKENLER — hiç dokunulmadı

| Konu | Neden önemli |
|---|---|
| `.ypt` alan şeması | Partikül üretiminin tek eksik parçası |
| ymap `<GrassInstanceBatches>` | Çim yerleşimi indekste yok |
| `.ymt` / clip_sets | Movement clipset tarafı yalnız referans dokümanında |
| Timecycle modifiers | MLO oda atmosferi |
| Audio (`.awc`, audio occlusion) | Hiç bakılmadı |
| Navmesh (`.ynv`) | Ped yol bulma; MLO'da kritik |
| `.ycd` içi tag/property şeması | Referansta var, indekste yok |
| Vehicle handling / `.meta` aileleri | Hiç bakılmadı |

---

# 6. YÖNTEM DERSLERİ — kendi hatalarımızdan

1. **Tek kaynak yetmez.** Güçlü doğrulamaların hepsi iki bağımsız kaynağın
   kesişmesinden geldi. `shaders.tsv` ve `collision_materials.tsv` tek
   kaynaklıydı; ikinci kaynak (`build_usage.ps1`) üretilince ikisi de doğrulandı.
2. **Küçük örneklemden genelleme yapma.** `specialAttribute=6` için "630
   örneğin hepsi slod" dedim — 6 satırlık örneklemdi, tam sayımda %15,7 çıktı.
3. **Aynı bilgiyi iki yerde elle tutma.** Entity bayrak tablosu belgede bir
   satır kaymıştı; kod doğruydu. Tablolar artık koddan üretiliyor.
4. **`catch {}` ile hata yutma.** `ResourcePointerArray64<T>` üzerinde
   `foreach` sessizce patlıyor — 86.690 dosya böyle kayboldu, tek belirti
   "0 tarandı" satırıydı. İlk hatayı **her zaman yazdır**.
5. **Limit sayacını denenen üzerinden say**, başarılı üzerinden değil.
6. **Kendi ölçümüne de şüphe duy.** "53.102 kopuk zincir" raporladım; sebep
   vanilla değil benim indeksimdi.

---

# 7. ÖNERİLEN SIRA

1. ~~`.ypt` alan şeması~~ ✅ **kapandı** — partikül %55 → %85
2. ~~138 `fxName`~~ ✅ **kapandı** — katalog %85 → %92
3. ~~Decal'ı oyunda dene~~ ✅ **kapandı** — A çalıştı; doku **gri maskedir**,
   rengi `AddDecal`'ın `rCoef/gCoef/bCoef` çarpanı verir
4. ~~`.ypt` XML→binary~~ ✅ **kapandı** — engel araçta değil, benim yanlış
   property adı okumamdaymış; sıfırdan efekt üretildi ve geri okundu
5. ~~Özel partikülü oyunda dene~~ ✅ **kapandı** — çiziliyor; yol boyunca
   CodeWalker'ın 4 sessiz eksiği bulundu ve derleyicide denetime bağlandı
6. ~~Üretimi tek komuta indir~~ ✅ **kapandı** — `scripts/ptfx_yap.ps1`
7. **Sprite sheet dilimlemesi** — gömülü dokuda çalışmıyor; 4 ölçümle
   daraltıldı, tek somut yön dokuyu `core.ypt`'ye eklemek (§7d) ·
   **sıradaki**, partikülü %90 → %98
8. **Renk bayrağı** — `SetParticleFxColour`'ı çalıştıran alan
9. **`<GrassInstanceBatches>` indeksi** — çim tarafındaki tek yapısal boşluk
10. **LOD %6,1** (4.1) — zor, getirisi düşük; en sona
