# Sollumz Discord `#tutorials` — topluluk bilgisi

**Kaynak:** Sollumz sunucusu `#tutorials` kanalının tamamı
(75 mesaj, 28.12.2021 → 13.07.2026), 57 video transkripti + 7 video kare kare.
**Çıkarım tarihi:** 21.08.2026
**Ham veri:** `C:\Users\musti\Desktop\FiveM\sollumz-tutorials\`
(`metin/` transkriptler · `notlar/` konu damıtımları · `index.tsv` tam liste)

> **Bu dosyanın statüsü:** buradakiler **ölçüm değil, topluluk uygulamasıdır.**
> Atlasın geri kalanı kendi ölçümlerimize dayanır ve **çakışma hâlinde ölçüm
> kazanır.** Buranın değeri: (a) Sollumz arayüzünde işi yapan doğru düğmeler,
> (b) bizim ölçmediğimiz alanlar, (c) bağımsız doğrulama.

---

## 1. ⛔ `.yed` zinciri TEK YOL DEĞİL — ikinci reçete ölçüldü

`yed-collision-animasyon.md` ve `CLAUDE.md §1` *"Kendi çözümünü arama, varyasyon
deneme"* diyor. Bu, **collision'ı script ile kovalamaya** karşı doğru bir uyarı;
ama expression'sız, **motorun kendi fragment yolu** üzerinden çalışan geçerli
bir ikinci reçete var (`dfO1eQf8WE0`, ook_3D).

### Reçete B — fragment physics bones + constraint + ytyp bayrağı
1. Mesh'i **hareketli** ve **sabit** parçalara ayır.
2. Convert to Drawable → **Create Fragment** → **Create Physic Bones**.
3. Skeleton Edit Mode'da hareketli kemiği taban kemiğine **parent** et.
4. Pose Mode → Drawables → Bone Tools → **"rotation and translation"**
   ← *bu, atlasın "Sollumz `Flags` yazmaz" uyarısının Sollumz içindeki çözümü.*
5. Fragment Physics (her iki kemik): **Strength = −1**, altındaki iki değer **0**,
   tüm **scale** değerleri **0**.
6. Collision: Bound Composite → **Bound Box** (⚠️ Bound *Poly* Box değil) +
   materyal.
7. Her collision kutusuna **`Child Of`** constraint → target fragment,
   bone = hareketli kemik → **Set Inverse**.
8. Clip dict **`anim@<fragment_adı>`**; **animation adı = clip adı = fragment
   objesinin adı**; animation Target = fragment skeleton.
9. Clip **Duration = kare ÷ 30**.
10. ytyp flags: **`HAS_ANIM` + `AUTOSTART_ANIM`**.
11. Kütle: collision kutuları → Fragments → **Set Mass → Calculate**.
12. Collision'ı olmayan taban kemiğinde **fragment physics kutusunu KAPAT**.
13. ⚠️ **CodeWalker collision animasyonunu göstermez** — oyunda çalışır.

### Hangi reçete ne zaman — henüz ÖLÇÜLMEDİ
| istenen | aday yol |
|---|---|
| tek prop'un parçası dönsün/açılsın, collision gelsin | `.yed` zinciri **ya da** Reçete B |
| bina/kule çöksün, sağlam → enkaz | RayFire (`rayfire-des-uretim.md`) |
| kırılabilir prop (mermiyle parçalansın) | fragment, **`Copy Transforms`** + ytyp `DYNAMIC` |

⛔ **İki constraint farklıdır, karıştırma** (ikisi de aynı yazardan, farklı işler):
- **animasyonlu prop** (klip oynayacak) → **`Child Of`** + Set Inverse
- **kırılabilir fragment** (parçalanma/fizik) → **`Copy Transforms`** + correct space

**Yapılacak ölçüm:** iki reçetenin ürettiği `.yft`/`.ycd` yapısal diff'i; hangi
durumda hangisinin collision'ı gerçekten sürdüğü. O ölçüm yapılana kadar
kullanıcıya **iki yol da anlatılmalı**, "tek yol var" denmemeli.

---

## 2. `.yed` yazabilmek — bizde olan, toplulukta olmayan yetenek

`yCy6hVJai3Y` (NcProductions) videosunda açıkça:

> *"`.yed` dosyalarını düzenleyebilecek bir araç henüz yok. `.yed` desteği
> **add-on ped'lerin yeni neslini** mümkün kılardı — aynı ped'in hem `IG_` hem
> `CS_` sürümünü yapma zorunluluğu ortadan kalkardı."*

`muto` Blender eklentisindeki **`build_yed`** tam olarak bu boşluğu dolduruyor.

### ⚠️ 2026-02: "CodeWalker `.yed` desteği ekledi" iddiası — ÖLÇÜLDÜ, YARIM DOĞRU
`bxmVJfL8KcA` (aynı yazarın Part 2'si) *"6 Şubat'ta Dexyfex CodeWalker'a YED/XML
dönüşümü ekledi"* diyor ve `.yed` düzenleyerek gerçek sonuçlar gösteriyor.

**Kurulu `CodeWalker30_dev46` üzerinde tur testi yapıldı** (vanilla `ambient.yed`,
41.562 bayt):

| yön | tip | sonuç |
|---|---|---|
| `.yed` → XML | `YedXml.GetXml` | ✅ **ÇALIŞIYOR** — 3 MB XML, **19 `<Streams>` + 23 `<Instructions>` bloğu dahil** |
| XML → `.yed` | `XmlYed.GetYed` | ⛔ **`NotImplementedException`** — tip var, gövdesi yok |

**Sonuç: atlas §2 bu derlemede GEÇERLİ** — okuma tarafı bytecode'u da veriyor,
**yazma tarafı yok**. `build_yed` hâlâ gerekli.

⛔ **Ders (§2 ve §9'un aynısı):** bir tipin/metodun **var olması** o işi yaptığı
anlamına gelmez. `$asm.GetTypes()` listesinde `XmlYed` görüp "destek eklenmiş"
demek yanlış teşhistir — **tur testi yapılmadan karar verme.**

**Açık kalan:** video daha yeni bir CodeWalker sürümünden bahsediyor olabilir
(ook_3D'nin 2025 kurulum videosunda `30dev48` geçiyor, bizde `dev46`).
Yeni sürümde `XmlYed.GetYed` gövdelenmiş mi — **tur testi tekrarlanmalı.**

### `.yed`'in ne yaptığına dair oyun tarafı gözlemi
`.yed` **hangi kemiklerin aktif olduğunu** belirler:
- Franklin'in `.yed`'ini kullanan kadın ped → **göğüs kemikleri ölü**, statik kalır
  (Franklin'de o kemikler yok).
- `csb_stripper_02.yed`'e geçince göğüs çalışır ama **konuşma kemikleri kaybolur**
  → ağız açılmaz.

`ped-kemik-yuz-rigging.md` §6'daki *"kanalı kemik dönüşüne çeviren şey `.yed`
expression'dır"* ölçümünün oyun içi karşılığı budur.

### `IG_` / `CS_` ayrımı ve protagonist ped'i
Michael/Franklin/Trevor dışında her karakterin **iki modeli** vardır:

| | `IG_` | `CS_` |
|---|---|---|
| ne zaman | oyun içi | ara sahne |
| iskelet | basit, az yüz kemiği | **çok daha fazla yüz kemiği** |
| yapı | genelde **compact** (tek `.ydd`/`.ytd`) | genelde **streamed** (ayrı dosyalar) |
| kusuru | ara sahnede ifadesiz yüz | oyun içinde ifadesiz yüz |

`CS_` ped'i oyun içinde çalıştırmak için ped metadata'sında:
- **`ExpressionDictionaryName` + `ExpressionName`** → `p_m_zero` (Michael) /
  `p_m_one` (Franklin) / `p_m_two` (Trevor).
  **Konuşurken ağzın açılmasını bu sağlar.**
- **`FacialClipsetGroupName`** → `facial_clipset_group_p_m_zero/one/two`
- **`IsStreamedGfx`** → streamed'de `true`, compact'ta `false`

⚠️ Her `CS_` ped uyumlu değil; uyumsuzluk ped bileşenleri ile `.yed`'in beklediği
bileşenler arasındaki farktan gelir.

---

## 3. Bağımsız doğrulanan ölçümlerimiz

| atlas maddesi | doğrulayan |
|---|---|
| §7 vertex başına **max 4 kemik**, toplam **tam 1.0** | `IbZ4xSCZt6I` — Blender karşılığı: Weights → **Normalize All** + **Limit Total 4** + **Smooth** |
| §8 ambient **98** ↔ freemode **128** kemik | `IbZ4xSCZt6I` — farkı `MH_hair_scale` + ön/arka etek roll'ları olarak sayıyor |
| §10 `COPY_TRANSFORMS`/`BEFORE_FULL`/`POSE`/`LOCAL` | `Ql7U5CyRx6E` ped cloth kapsülü — birebir aynı dört ayar |
| §1.5 bbox animasyonun tamamını kapsamalı | `ahPJhRZPiZQ` — ytyp'i animasyonun BB min/max'ini saran kutuyla export ediyor |
| §5 decal = render bucket **2** | `seto_decal.mp4` — Material Properties'te `Decal (2)` |
| §9 `sz_lods.high.mesh` atanmazsa drawable atlanır | `0lSk_4pWP0U` — "high LOD mesh'i doğru ayarla, yoksa export bozulur" |
| §9 Gen8/Gen9 ayrı eksen | `ahPJhRZPiZQ` — "Gen 8 XML olarak export et" |
| §4 oda ataması unutulursa sessizce bozulur | `6MbS33jvYU0` (light proxy **limbo'ya değil odaya**) · `GxalDgXGv1g` · `j9tCYnWJsZo` |
| §2 aracın göstermemesi ≠ yok | CodeWalker **parallax'ı**, **cloth'u** ve **animasyonlu collision'ı** hiç göstermiyor (üç ayrı video) |

**Tek çelişki:** `f4G1DpHyEHc` T-pose için kolu **−45°** çeviriyor;
`ped-retarget-weightpaint.md` ölçümü **57°**. **Ölçüm kazanır**, videoya göre
düzeltme yapma.

---

## 4. Bizde kayıtlı olmayan sessiz hatalar

- ⛔ **Export → Drawable → `Mesh Domain` = `Face Corner`.**
  `Vertex` yalnız **MP freemode kafaları** içindir (vertex sırası önemli).
  Yanlış seçim sessizce bozuk ped üretir.
- ⛔ **Rokoko `Auto Scale` açıkken root motion TAMAMEN silinir.**
  Videonun yazarı bunu aylarca teşhis edememiş.
- ⛔ **Retarget'ta tüm `FB_` yüz kemiği keyframe'leri silinmeli.** Yoksa hikâye
  ped'lerinde (Michael/Franklin/Trevor) yumruk atarken **yüz içe çöküyor**.
  (§6: yüz kemikleri expression ile sürülür, klip yazmamalı.)
- ⛔ **Ped cloth physics mesh'i en fazla 255 vertex** — motor sınırı.
- ⛔ **Arazi karışımı `UVMap 1` olmadan hiç çalışmaz** (lookup sampler onu kullanır);
  ayrıca **`Colour 1`'in ALFASI siyah** olmalı (beyaz = lookup kapalı).
- ⛔ **Vanilla `.ydd` içinden obje SİLME, dünyanın altına taşı.** Silmek sözlükteki
  diğer bağlı objelerin özelliklerini bozuyor ve bölgenin dokusunu bulanıklaştırıyor.
  (`vanilla-parca-degistirme.md`'ye ek.)
- ⛔ **`_r` (skintone) giysilerde üç sessiz hata:**
  1. ten rengi UV'sini **kaydırma** (erkek bacak sol altta, kadın ayak alt yarıda) —
     gerçek ten dokusu `mp_fm_skin` setinden gelir, giysinin `.ytd`'sinden değil
  2. gömülü doku adı **`<bileşen>_spec_<NN>`** olmalı, rastgele isim ten rengini
     sessizce kapatır
  3. maske **specular'ın ALFA kanalıdır**; doku **KARE** olmalı, 1024×512 gerer
- ⛔ **Ped prop'unda `Render Flags` Blender shader'ıyla eşleşmeli**
  (`ped_alpha`/`ped_decal`/`ped_cutout`). MP freemode'da önemsiz,
  **diğer tüm ped'lerde fiilen zorunlu**.
- ⛔ **UV animasyonunda kare 120 = kare 0.** İkisi de bırakılırsa döngü başında
  gözle görülür takılma olur; animasyon **119'da bitmeli**.
- ⛔ **`.rel` / ses XML'lerinde isim uyuşmazlığı sessizce her şeyi bozar.**
- ⚠️ **Sollumz `Fill Animation Data` düğmesi bozuk** — frame count'u elle yaz.
- ⚠️ **Shadowmap: iki ayrı yöntem, karıştırma.** Eski yöntem Blender'ın
  **Shadow *render pass*'ini** kullanır ve o kaldırıldığı için **Blender 3.3**
  gerektirir; yeni yöntem **bake type = Shadow** kullandığı için güncel Blender'da
  çalışır.

---

## 5. ⛔ İki UV uzayı — yön hatasının gerçek sebebi

Kare kare, etiketli test ızgarasıyla (`uv_test_pattern.dds`) doğrulandı:

- **Blender UV editöründe** `0,0` **SOL ALT**, `0,1` sol üst → **V yukarı artar**
- **GTA doku uzayında** orijin **SOL ÜST** → **V aşağı artar**

**Sonucu:** Blender'da `+Y` (V) yönünde bir translate, oyunda dokuyu **ters yöne**
kaydırır. Yön tutmuyorsa keyframe'leri kurcalama, önce buraya bak.
Kendi etiketli test dokunu üretmek en hızlı doğrulama.

### Dönen UV — numara keyframe'de değil DOKUDA
Rotate ve Scale **UV `0,0` etrafında** çalışır, şeklin merkezi etrafında değil.
Adayı 0,0'a taşımak bozuyor. Doğrusu: **şekli dört parçaya kesip dokunun dört
köşesine yerleştirmek** (sonra vertex bevel + merge). Kareden görsel doğrulama:
`sollumz_circle.dds` tam olarak böyle çizilmiş. **Sonradan UV oynatarak
düzeltilemez — doku baştan öyle üretilir.**

### UV animasyonunun Sollumz'daki yeri
**Material Properties → `UV Transformations`** + altındaki
**`Create Sollumz Shader UV Animation`** düğmesi.
Animation Target ID **materyaldir** (iskelet animasyonundaki gibi armature değil).
Clip **Name = hash + `.clip`** olmalı.
ytyp flags: **`UV_ANIM` (= 1024)** + `AUTOSTART_ANIM`; iskelet animasyonuyla
birlikteyse `HAS_ANIM` + `UV_ANIM` ve autostart gerekmiyor.
✅ **Kapı: CodeWalker'da oynamıyorsa oyunda da oynamaz.**

---

## 6. Sollumz'da var olduğunu bilmediğimiz araçlar

- **`Cable Tools`** (Drawables altında) — kablo **Catenary** eklentisiyle gerçek
  zincir eğrisi olarak üretilir, sonra **vertex başına**
  `Radius` (ör. 0.02 m) · `Diffuse Factor` · `Micromovements Scale` ·
  `Phase Offset` (+ **`Randomize`**) · `Material Index` yazılır.
  Kabloyu elle mesh yapmak bu yüzden tutmuyor.
- **ytyp arketip tipi `Time`** + **24 saatlik onay kutusu ızgarası** ve
  `Select from … to …` aralık seçici. `ytyp-ymap-bayraklari.md`'deki `TimeFlags`
  sihirli sayısını elle yazmaya gerek yok.
- **Cloth Tools → Diagnostics → Refresh** — ped cloth için **gerçek bir doğrulama
  kapısı**: binding ve materyal hatalarını sayar, hedef **sıfır**.
- **LOD Tools → Generate LODs** (referans mesh + Medium/Low, decimation 0.6).
- **Light Presets** (`+`) — kendi ışık ön ayarını kaydeder.
- **Bone Tools → Limit** — tek kemiğin bayraklarını sıfırlayıp sınırlamak için
  (silah şarjörü hizalamasında kullanılıyor).

### Dış eklentiler (topluluk standardı)
`Rokoko` (retarget) · `Catenary` (kablo) · `DeepBump` (diffuse'tan normal map) ·
`Vertex Color Master` (kanal bazlı vertex boyama + data transfer) ·
`Sushi Cleanups` (boş vertex grubu temizleme) · `Collider Tools` ·
`Vicho Tools` (animasyon) · `Folders to YTD` · `V Weapons Toolkit 1.0.3`
(sonraki sürümler bozuk) · `Audio Occlusion Tool` · `MLOScaleformTools`

---

## 7. Konu → ayrıntı haritası

Tam adım adım yordamlar `C:\Users\musti\Desktop\FiveM\sollumz-tutorials\notlar\`:

| konu | dosya |
|---|---|
| animasyonlu prop+collision, fragment, prop/ped cloth, ped animasyonu, retarget | `01-animasyon-fragment-cloth.md` |
| UV animasyonu, MLO ışığı, shadowmap, yansıma proxy, vertex AO, materyal, YBN hizalama, doortuning | `02-uv-animasyon-isik-golge-dunya.md` |
| `.yed`/IG_/CS_, ağırlık boyama, skintone `_r`, freemode giysi, ped ölçekleme, `p_eyes`/`p_ears`, ped prop, silah | `03-ped-giysi-prop-silah.md` |
| araç kurulumu, MLO üretimi, iç mekân LOD, arazi karışımı, parallax, timecycle, audio occlusion, ses emitter, radyo | `04-mlo-harita-ses-arac-gerec.md` |
| grafiti/decal (Substance → DDS → render bucket 2 → ymap) | `05-decal-grafiti.md` |
| time bound prop, Cable Tools, arazi/bina değiştirme | `06-altyazisiz-videolar-kare-turu.md` |

### Erişilemeyen kaynaklar (tekrar denendi)
- `ttKh1iOorIU` Shadowmap (YamK Mods) — **video gizli yapılmış**
- `IIrBh13-lG4` One room MLO (gta5 modder) — **video kaldırılmış**

İkisinin de konusu başka videolarla kapanıyor.
