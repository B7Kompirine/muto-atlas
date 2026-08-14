# Silah görselleri: glow, wireframe, süsleme ve UV animasyonlu skin

Add-on silah **çalıştıktan sonra** üstüne binen katman: parlayan bölgeler,
tel kafes görünüm, zincir/charm süslemesi ve **UV animasyonlu skin**.

Temel hat burada değil — önce `addon-silah-uretimi.md` (komut: `/weapon`).
Bu belge o hattın çıktısını süsler.

## KAYNAK VE GÜVENİLİRLİK

| İşaret | Kaynak |
|---|---|
| **[ölçüm]** | vanilla `.meta` / `.ydr` çözülüp sayıldı — kesin |
| **[kare]** | tutorial videosunda ekrandan okundu — o kurulumda çalışıyor |
| **[video]** | anlatımdan; üreticinin kendisi de emin değil (aşağıda işaretli) |

## 1. ZORLUK SIRASI — nereden başlanır

| Teknik | Zorluk | Oyun tarafı gerektirir mi |
|---|---|---|
| Zincir / charm süsleme | düşük | **hayır** — sadece mesh |
| Wireframe | düşük | hayır — modifier + shader |
| Glow (emissive) | orta | hayır — shader + `.ytd` |
| **UV animasyonlu skin** | **yüksek** | **evet** — `.ycd` + `.ytyp` + `.ymap` + bileşen |

İlk üçü silahın `.ydr`'sinin içinde kalır. Sonuncusu ayrı bir model, ayrı
bir bileşen ve dört ek dosya demektir — onu en sona bırak.

## 2. GLOW — parlayan silah

Shader: **`normal_spec_emissive`**.

### Adımlar

1. Edit Mode → yüz seçimi (`3` ile face mode; `L` bağlı parça, `B` kutu).
   Materials sekmesinde `Select` ile mevcut materyalin hangi yüzleri
   kapsadığını görebilirsin — parlayacak bölge zaten ayrı materyaldeyse
   iş biter.
2. `N` → Sollumz → `Drawables → Shader Tools` → arama kutusuna
   `normal spec emissive` → **Create Shader Material**.
3. Materyali yeniden adlandır → `Sollumz → Texture Parameters`:
   - **ana doku = parlamanın rengi**
   - normal ve spec dokularını ekle ve **ikisini Embedded işaretle**
4. Value Parameters — [kare] ile okunan çalışan değerler:

```
HardAlphaBlend         1.00
useTessellation        ☐ (kapalı)
bumpiness              0.40
specMapIntMask         1.000 / 0.000 / 0.000
specularIntensity…     1.00
specularFalloffMult    250.00
specularFresnel        0.96
emissiveMultiplier     1.10      ← parlaklık burası
```

5. Seçili yüzler dururken shader'ı **Assign** et. Görmek için viewport
   **Material Preview** modunda olmalı (sağ üstteki üçüncü küre ikonu).
6. Export → XML'i CodeWalker'a sürükle → `.ydr`.

### ⛔ EN SIK ATLANAN ADIM: ana doku `.ytd`'ye eklenmeli

Export sonrası parlayan bölgeler **beyaz** görünür. Sebep: ana glow
dokusu texture dictionary'de yok. `.ytd`'yi aç ve dokuyu ekle.

Ayrıca: **OpenIV'de parlamaz.** Parlama oyun içinde ve **gece** görünür.
"Çalışmadı" diye geri dönmeden önce gece test et — bu iki madde
yüzünden çalışan bir kurulum defalarca bozuk sanılıyor.

## 3. WIREFRAME — tel kafes görünüm

En ucuz efekt; tamamen modifier işidir.

1. Mesh'i **çoğalt** (kopya `.001` ekiyle gelir) ve **kopya üzerinde
   çalış** — orijinal altta kalsın.
2. Kopyaya **Wireframe modifier** ekle. [kare] ile okunan ayarlar:
   ```
   Thickness        0.001  (veya daha ince)
   Offset           0.0000
   Boundary         ☐
   Replace Original ☑
   Even / Relative  ☐ ☐
   Crease Edges     ☐  (1.0)
   Material Offset  0
   ```
3. Wireframe'e kendi shader'ını ver (parlasın istiyorsan §2'deki
   `normal_spec_emissive`).

`Thickness` modelin ölçeğine bağlıdır: GTA silahı ~0.5 m olduğu için
0.001 makul; kalın gelirse düşür. Modifier **apply edilmeden export
edilmez**.

## 4. ZİNCİR SARMA — spiral + array + curve

Saf Blender modelleme; oyun tarafı hiç yok.

1. `Shift+A → Curve → Spirals → Archimedean` (Sollumz'un değil, Blender'ın
   `Add Curve: Extra Objects` eklentisi). Ayarları sol alt kutudan gir,
   sonra spirali gizle.
2. Zincir halkası: üstten görünüm (`Z`) → `Shift+A → Mesh → Torus` →
   X-ray aç → torusun yarısını seç → `E`, `Z` ile sağa extrude → halka
   şekli. `Shade Smooth`.
3. Halkayı Y'de 90° döndür → `Shift+D` ile çoğalt → `G`,`Z` ile yukarı →
   ikinciyi Z'de 90° döndür → aralarında biraz boşluk bırak → ikisini
   seçip `Ctrl+J`. **Tüm rotation değerlerini 0'la.**
4. **Array modifier** → Count ~87 → `Factor X`'i (shift+sürükle) zincir
   birleşene kadar küçült.
5. Spirali göster, zinciri ölçekle, spiralin başına hizala →
   **`Ctrl+A` → Rotation & Scale**.
6. **Curve modifier** → Curve Object = spiral (damlalık ikonu).
7. Silahı import et, spiral+zinciri birlikte ölçekle/döndür/taşı
   (`Ctrl` basılı döndürme 5°'de kilitler). Namluya sar.
8. İnce ayar: **yalnız spirali** seç → Edit Mode → vertex'leri tek tek
   oynatarak zinciri silaha oturt.
9. Array count'u fazlaysa düşür → **array ve curve modifier'larını apply
   et** → spiral curve'ü sil → zincir + silah `Ctrl+J`.

## 5. CHARM / 3B SÜSLEME

1. Sketchfab'den `.obj` (veya `.fbx`) indir, klasördeki **iç zip'leri de**
   aç. `File → Import → Wavefront OBJ`.
2. Ölçekle (`S`) ve silahın yanına taşı. Parçalıysa `B` ile seçip
   `Ctrl+J` ile birleştir.
3. Materyaller **Sollumz shader'ı olmak zorunda.** Orijinal materyalin
   hex rengini al → o renkte düz bir görüntü üret → **DDS'e çevir** →
   Sollumz shader'ının ilk doku yuvasına koy, **Embedded** işaretle.
   Parlak metal için `reflect`, mat yüzey için `normal_spec`.
4. Doğrulama: eski materyali sil → Edit Mode → yeni materyalde `Select` →
   **turuncu parlıyorsa tuttu**, parlamıyorsa atama olmamış.
5. `V → Convert to Drawable` → Object Properties'te **Rotation X = 90**.
6. Konumlandır → charm'ı seç, `Shift` ile silahı seç, `Ctrl+J`.
   Sahne listesinde kalan boş charm objesini silmek modeli silmez.

## 6. UV ANİMASYONLU SKIN — akan/kayan doku

Silahın üstünde **hareket eden** bir kaplama. Ayrı bir model, ayrı bir
bileşen ve dört ek dosya gerektirir.

> ⚠️ Bu bölümün kaynağı olan üretici tekniği **"gimmicky"** diye niteliyor
> ve birkaç adımın neden gerektiğinden emin olmadığını açıkça söylüyor
> (`.ymap` gerekliliği, LOD mesafesi). O maddeler `[video?]` ile
> işaretlendi — çalıştığı gösterildi, **nedeni doğrulanmadı**.

### 6.1 Skin ayrı bir model olmalı

Animasyonlu bölge ana silahtan **ayrılır** ve **farklı ad** alır:

```
w_ar_carbinerifle_m31            ← ana silah
w_ar_carbinerifle_m31_skin_01    ← animasyonlu kaplama
```

### 6.2 UV keyframe (materyal üzerinde)

Materyal node'unda → **Animation Tracks** → `+`. Temel keyframe:

| Kare | UV offset | Sonuç |
|---|---|---|
| 0 | 0.0 , 0.0 | başlangıç |
| 30 | 0.5 , 0.5 | orta |
| 60 | 0.0 , 0.0 | **ileri-geri döngü** |

Tek yöne sürekli akış isteniyorsa: kare 0 → `0.0`, kare 60 → `1.0`.

### 6.3 Sollumz klip zinciri

`N` → Sollumz → `Animations`:

1. **Create Clip Dictionary Template** → `Create Animation` → `Create Clip`
2. **Animation** nesnesinde:
   - `Hash` — serbest ad (ör. `carbinerifle_m31`), **çakışmasın**
   - `Action` — doğru action seçilmeli
   - ⛔ **`Target ID` = MATERYAL** (ped animasyonundaki gibi armature
     DEĞİL). [kare] Açılır liste materyalleri listeler; animasyonlu
     kaplamanın materyalini seç.
3. **Clip** nesnesinde [kare ile okundu]:
   ```
   Sollumz Type : Clip
   Hash         : carbinerifle_m31
   Name         : carbinerifle_m31.clip     ← ⛔ ".clip" EKİ ŞART
   Duration     : kare sayısı / 30          (60 kare → 2.0 s)
   ```
   `Linked Animations` → `New` → animasyonu seç.
4. Clip Dictionary nesnesini yeniden adlandır: **`clip@<ad>`**
   (ör. `clip@carbinerifle_m31`).

`.clip` eki unutulursa animasyon **hiç oynamaz** ve hata da vermez.

### 6.4 Archetype (ytyp)

`Archetype Definition` → YTYPS `+` → Archetypes `+` →
**Auto-Create From Selected** (skin modeli seçiliyken):

```
Archetype adı      w_ar_carbinerifle_m31_skin_01
Texture Dictionary = archetype adının aynısı
Clip Dictionary    = clip@carbinerifle_m31
Flags              525312
```

[ölçüm — karedeki `Flags: 525312` değeri bit ayrıştırmasıyla doğrulandı]

```
   1024  UV anims (YCD)        ☑
+524288  Auto Start Anim       ☑
────────
 525312
```

⚠️ **`Has Anim (YCD)` ile `UV anims (YCD)` ayrı bayraklardır.** UV
animasyonunda işaretlenen **`UV anims`**'tir; `Has Anim` değil.

### 6.5 Export ve bileşen

Export sonrası CodeWalker'da **dört dosya** olmalı: `.ytyp`, `.ycd`,
ana silah `.ydr`, skin `.ydr`. Skin'e çift tıkla — **CodeWalker'da
animasyonlu görünmüyorsa oyunda da görünmez**, geri dön ve hatayı bul.
(Bazen CodeWalker'ı yeniden başlatmak gerekir.)

vWeaponsToolkit'te skin bir **bileşendir**:

```
Component Name  COMPONENT_RIFLE_SKIN01
Model           w_ar_carbinerifle_m31_skin_01
Component Enabled ☑
```

`weaponcomponents.meta` tarafında:

```xml
<Name>COMPONENT_RIFLE_SKIN01</Name>   <!-- weapons.meta ile birebir aynı -->
<Model>w_ar_carbinerifle_m31_skin_01</Model>
<AttachBone>AAPGrip</AttachBone>
```

⛔ `<AttachBone>` **`AAP*`** ailesindendir — bkz. `addon-silah-uretimi.md`
§1 [ölçüm: 318/318 vanilla girdi `AAP*`]. `LocName`/`LocDesc` kozmetiktir.

### 6.6 `[video?]` — doğrulanmamış adımlar

Üreticinin "emin değilim" dediği, ama onun kurulumunda gerekli çıkan
adımlar. Kendi testinde birer birer çıkarıp doğrula:

- **`.ymap` üretmek**: yeni proje → YMAP → New Entity → adı skin modeli
  (`..._skin_01`), `Calculate Extents` + `Calculate Flags`, `stream/`
  içine kaydet. Gerekçe olarak "UV map objeyi instance ediyor olabilir"
  deniyor — **mekanizma doğrulanmadı**.
- **LOD distance 99999** — üretici "gerekli mi bilmiyorum" diyor.
- **`_manifest.ymf`** üretmek: bu genel bir `stream/` kuralıdır, YMAP
  eklediysen gereklidir.

## 7. TUZAK KATALOĞU

- **⛔ Glow, OpenIV'de görünmez ve gündüz görünmez** — gece, oyun içinde
  test et.
- **⛔ Glow'un ana dokusu `.ytd`'ye eklenmezse bölge beyaz kalır.**
- **⛔ Klip adı `<hash>.clip` olmalı** — ek unutulursa UV animasyonu
  sessizce hiç oynamaz.
- **⛔ UV animasyonunda `Target ID` materyaldir**, armature değil.
  Ped animasyonu alışkanlığıyla armature seçmek en kolay hatadır.
- **⛔ `UV anims (YCD)` ≠ `Has Anim (YCD)`** — yanlış bayrak sessizce
  çalışmaz. Doğru toplam `525312` (1024 + 524288).
- **CodeWalker'da oynamayan skin oyunda da oynamaz** — ilk kontrol noktası
  orasıdır, oyuna kadar gitme.
- **Wireframe/array/curve modifier'ları apply edilmeden export edilmez.**
- **Charm/zincir birleştirildikten (`Ctrl+J`) sonra tek drawable olur** —
  ayrı bileşen değildir, `weaponcomponents.meta` gerektirmez.
- **Charm'da `Rotation X = 90`** ayarı atlanırsa süsleme oyunda yan yatar.
- **Sollumz shader'ı olmayan materyal oyunda çalışmaz** — Principled BSDF
  bırakma; atamanın tuttuğunu `Select` → turuncu testiyle doğrula.
- **Skin ana silahla aynı adı taşıyamaz** — `_skin_01` gibi ayrı ad şart.

## NE ZAMAN YETMEZ

- **Weapon tint / camo sistemi** (oyunun kendi renk kanalları) — bu belge
  onu kapsamaz; `AAPCamo` bileşeni ve tint destekli shader gerekir.
- **Mesh deformasyonlu animasyon** (parça hareketi) — UV animasyonu
  yalnız dokuyu kaydırır, geometriyi oynatmaz. Parça hareketi için
  `Gun_Cock1` / `Gun_Trigger_Pr` kemikleri ve vanilla silah animasyonları
  kullanılır.
