# Dış araç gözlemleri — başkasının hattından ölçülebilen şeyler

**Kaynak notu — kural değil.** Dış araçların (Five Toolkit vb.) ölçülebilen kısmı ve [doğrulandı]/[çürütüldü] etiket sistemi. Taşındı: `sources/external-tools.md` (2026-09-05). Ham kopyalar `_dis-kaynak/` yanında.

Bu dosya **atlas'ın ölçüm korpusu değildir.** Buradaki sayıların bir kısmı
üçüncü taraf bir aracın ürün tercihidir; vanilla'dan ölçülmüş değerler
`data/` altındaki tablolarda ve diğer referanslardadır.

| İşaret | Anlamı |
|---|---|
| **[doğrulandı]** | Bizim veriyle karşılaştırıldı, tuttu. Kullanılabilir. |
| **[dış kaynak]** | Aracın kendi verisi. Doğru olabilir, ölçüm değildir. |
| **[çürütüldü]** | Bizim ölçümümüzle çeliştiği doğrulandı. Kullanma. |
| **[alınacak]** | Politika/yaklaşım olarak bizim hattımıza değer. |

⛔ **Genel kural:** dış bir araç bir sayı veriyorsa (tag, bayrak, lodDist,
materyal indeksi) o sayı **kanıt değil iddiadır**. `assetdb.py` ile doğrula.
Doğrulanmamış bir sayıyı bu dosyadan alıp koda ya da asset'e taşıma —
`[doğrulandı]` etiketi taşımıyorsa önce ölç.

---

## 1. FIVE TOOLKIT — `tools.scarfacemlo.com`

**İncelenme:** 2026-09-01 (ana sayfa, `tools.scarfacemlo.com/docs`, 2,09 MB JS bundle, açık API
uçları). Scarface MLO / "3D Academy" ekibinin ücretsiz, Discord girişiyle
kapılı, tarayıcı tabanlı FiveM asset üretim hattı.
Sloganı: *"3D modelden FiveM sunucusuna, Blender yok."*

### 1.0 Erişim ve mimari [dış kaynak]

React + three.js (R3F) + zustand + GSAP, Vite; Caddy + Cloudflare.
**GTA'ya dokunan her şey sunucuda** — tarayıcı yalnız editör.
Giriş `/api/auth/discord/login`; `/api/auth/me` →
`{authEnabled, authenticated, inGuild}`. Araç sayfaları (**/armes**, **/props**, **/optimiseur**, **/shell**)
giriş arkasında; `/api/shaders` ve
`/api/shells/catalog` **açık**.

CSP'de `wasm-unsafe-eval` var (tarayıcı tarafında WASM çalışıyor).
`connect-src`: Sketchfab + `*.amazonaws.com` + `*.cloudfront.net`.
Sketchfab içe aktarma **kullanıcının kendi API token'ıyla**, token yalnız
istemcide saklanıyor. Modellerin saklanmadığı iddia ediliyor.

Araçlar: Weapons Creator (12 adım), Props Creator (6 adım), Resource
Optimizer (3 adım), Tattoo Creator, Vehicle Debadger, Weapon Editor;
geliştirmede Shell Creator, Cloth Creator, Map Conflict Fix.

⚠️ İstemcide **hiçbir kütüphane/plugin atfı yok** (`sollumz`, `codewalker`,
`plugin`, `credit`, `powered by`, `open source` — sıfır eşleşme). Hangi hattı
kullandıkları dışarıdan görülmüyor; anlamak için giriş yapıp bir çıktı üretmek
ve vanilla ile ikili karşılaştırmak gerekir.

### 1a. ⛔ Silah kemik tag tablosu YANLIŞ [çürütüldü]

Özet: `gun_root 0` ve
`gun_gripr 18308` doğru; `gun_muzzle 55863` ve `gun_vfx_eject 5103` yanlış
(doğrusu **17833** / **28405**); `gun_mag` · `gun_slide` · `gun_bolt` ·
`gun_pump` diye kemik **hiç yok** (şarjör yuvası `WAPClip` 1477, kurma kolu
`Gun_Cock1` 39439). Araç bu iskeleti kendi içinde *"prosedürel siluet"* diye
işaretliyor ama arayüzde *"GTA adları ve ID'leri korunur"* yazıyor — yani
kullanıcıya doğruymuş gibi görünüyor.

### 1b. [alınacak] "Byte-for-byte" politikası

Weapon Editor ve Optimizer'ın yazılı kuralları. Başkasının kurulu
resource'una dokunan her işte doğru duruş budur:

- Değiştirilmeyen dosya **bit bit aynı** geri döner.
- Silahın **teknik adı asla değiştirilmez** — resource zaten kurulu, yeniden
  adlandırmak onu referans alan envanter ve script'leri kırar.
- `cl_weaponNames.lua` yoksa **başkasının `fxmanifest.lua`'sına
  `client_script` eklenmez**.
- Vanilla bileşen modelleri (susturucu, dürbün…) **hiç yeniden yazılmaz**,
  kendi dokusunu korur.
- `fxap` (escrow) korumalı dosya **tespit edilir, dokunulmaz**; bozuk/boş
  dosya **yalnız raporlanır**, düzeltilmeye kalkışılmaz.
- Eklenen bileşen mevcutların **üstüne** eklenir, hiçbiri değiştirilmez.
- 3B görünümde **yalnız silah gövdesi** çizilir; zaten kurulu bileşenler ayrı
  model olduğu için gösterilmez — kullanıcı yeni parça yerleştirirken bu
  açıkça söylenir. ("Göstermediğimi söyle" iyi bir desen.)

### 1c. [dış kaynak] Eşikler — ürün tercihi, ölçüm değil

| Eşik | Değer | Bağlam |
|---|---:|---|
| Silah "high poly" rozeti | 60.000 vertex | Sketchfab içe aktarmada uyarı |
| Prop "high poly" rozeti | 37.000 vertex | *"prop, streaming'i silahtan hızlı doldurur"* |
| "Çok yoğun model" | 150.000 üçgen | precise collision hesabı yavaşlar |
| Upload tavanı | 100 MB | model + dokular, ya da tam resource |

Collision sadeleştirmesi: 1e-4 weld → `SimplifyModifier`, oran **[0.02, 1]**
aralığına kırpılıyor. Collision modları: **None / Box / Precise**
(varsayılan `none`, oran `0.5`, materyal `default`).

⚠️ Bu sayılar bizim poligon bütçesi ölçümlerimizin yerini **tutmaz**
(ör. vanilla `a_c_rottweiler_02.ydd` = 11.303 üçgen). Kullanıcıya bütçe
söylerken vanilla'dan ölç, buradan alma.

### 1d. [dış kaynak] Collision materyalleri — 20'lik kısa liste

Arayüzde sundukları `bound material` adları (bizim tam tablomuz **185**
materyal, `assetdb.py mat`):

```
default · concrete · brick · stone · marble · tarmac · sand_loose · grass
wood_solid_medium · wood_hollow_medium · metal_solid_medium
metal_hollow_medium · metal_corrugated_iron · glass_shoot_through
plastic · rubber · cardboard_box · cloth · leather · ceramic
```

Ad biçimi doğru (vanilla `METAL_SOLID_MEDIUM` = indeks 56). "Kullanıcıya 20
seçenek sun, 185'i gösterme" iyi bir ürün kararı — bizim araçlarımızda da
kısa liste + tam listeye kaçış yolu doğru desen.

### 1e. [dış kaynak] `/api/shaders` — 106 shader'lık açık tablo

Kimlik doğrulaması istemiyor. Alanlar: `name`, `sps`, `renderBucket`, vertex
`layout`, `textures[{sampler, required}]`, `params[{name, value}]`.
Kopya: `_dis-kaynak/five_toolkit_shaders.json`.

Bucket dağılımı: 0 → 55 · 1 → 18 · 2 → 26 · 3 → 6 · 7 → 1
(bucket 7'deki tek shader `glass_displacement`).

**Bizde zaten daha iyisi var** (`assetdb.py shader`, 249 shader) ve bizimki
render bucket'ı **kullanım dağılımından** veriyor:

```
normal_spec → bizde:   bucket 0 = 6405 · bucket 3 = 166 · bucket 1 = 75
              onlarda: renderBucket 0 (tek sayı)
```

Fark: `normal_spec` için `specularIntensityMult` bizde vanilla varsayılanı
**1**, onlarda **0.125**. Bu bir tercih; vanilla değeri diye alma. Bizde olan
`specMapIntMask`'i listelemiyorlar, onlarda olan `globalAnimUV0/1`'i biz
varsayılan saymıyoruz.

⛔ **`required` alanı bilgi taşımıyor — ölçüldü.** 106 shader'ın **105'inde**
tek `required` sampler `DiffuseSampler` ve o da **her zaman 0. sırada**;
birden fazla `required` taşıyan shader **yok**; hiç `required` taşımayan tek
shader `cable`. Yani alan "ilk sampler diffuse'tur" demekten ibaret.
`build_shaders.py`'ye eklemeye değmez — önce ölçtüğüm için bu alan
korpusumuza girmedi.

### 1f. [dış kaynak] Shell Creator ızgara sözleşmesi

Kendi shell/housing işimiz olursa hazır ölçü seti
(`_dis-kaynak/five_toolkit_shells_catalog.json`):

```
modül 2.0 m · kat yüksekliği 3.0 m · maks 4 kat · 21×21 grid
karolar: vanilla se_stud_wall_1..16 · se_stud_tile_*
hücre içeriği: tile · ceiling · stairs · walls{} · decor{}
seçenekler: void (boşluk kapatma) · shadowMask
çıktı: tek birleşik prop (.ydr + collision) + .ytd + .ytyp
       + layout.json (housing script'i için spawn offset dahil)
```

### 1g. [dış kaynak] Camo / sticker yaklaşımı

Tint palette shader'ıyla uğraşmıyorlar: camo ve sticker **export'ta tek
dokuya merge ediliyor**, kesilen şarjörün `.ytd`'sine silahın dokusunun
kopyası veriliyor. Vertex color global çarpan olarak sunuluyor
(*"beyaz = etkisiz; başka değer silahı boyar"* — bu doğru, motor vertex
color'ı dokuyla çarpar; varsayılan `[255,255,255,255]`).

Camo dokuları `/camo/<id>.webp`, ızgara 2×2 aynalama + mip zinciriyle
üretiliyor, `hue-rotate` + `saturate` CSS filtresiyle renklendiriliyor.
14 hazır desen: `darkmatter · eclaire · zombie_nuk · diamant · or_emeraude ·
sable · romain · crane · flamme · miami · weed · weed2 · coeur · rose`.

⚠️ Kendi uyarıları da doğru: kesilen şarjör birden fazla materyale yayılırsa
oyunda **tek doku** taşır, kalan yüzler yanlış çıkar.

### 1h. [dış kaynak] Doku yeniden kodlama

*"Değiştirilen dokular DXT5'e yeniden kodlanır; DXT1 olanlar yaklaşık iki
katı ağırlaşır."* Bizim ölçümümüzle tutarlı (`core.ypt` gömülü partikül
dokuları: DXT5 75 · DXT1 32). Kullanıcıya boyut artışını **önceden**
söylemek iyi bir desen.

### 1i. Baz silah kataloğu — 28 sınıf

**Model adları [doğrulandı]:** 28'inin **tamamı** bizim iskelet korpusumuzda
gerçek `.ydr` olarak var (`assetdb.py bones` ile tek tek denendi, hiçbiri
"iskeleti yok" dönmedi). Kemik sayıları bizim ölçümümüz:

| id | model | sınıf | kemik | damage | range | clipSize | tbs (ms) |
|---|---|---|---:|---:|---:|---:|---:|
| pistol | `w_pi_pistol` | pistol | 12 | 26 | 60 | 12 | 250 |
| combatpistol | `w_pi_combatpistol` | pistol | 12 | 27 | 60 | 12 | 240 |
| appistol | `w_pi_appistol` | pistol | 12 | 28 | 55 | 18 | 100 |
| pistol50 | `w_pi_pistol50` | pistol | 11 | 51 | 60 | 9 | 350 |
| stungun | `w_pi_stungun` | pistol | 6 | 1 | 12 | 1 | 1000 |
| microsmg | `w_sb_microsmg` | smg | 15 | 21 | 40 | 16 | 90 |
| smg | `w_sb_smg` | smg | 18 | 22 | 45 | 30 | 90 |
| assaultsmg | `w_sb_assaultsmg` | smg | 14 | 23 | 50 | 30 | 80 |
| machinepistol | `w_sb_compactsmg` | smg | 9 | 27 | **120** | 12 | 118 |
| assaultrifle | `w_ar_assaultrifle` | rifle | 16 | 30 | 90 | 30 | 100 |
| carbinerifle | `w_ar_carbinerifle` | rifle | 17 | 32 | 90 | 30 | 100 |
| advancedrifle | `w_ar_advancedrifle` | rifle | 14 | 34 | 90 | 30 | 95 |
| mg | `w_mg_mg` | rifle | 16/15 | 40 | 100 | 54 | 110 |
| combatmg | `w_mg_combatmg` | rifle | 17 | 45 | 100 | 100 | 100 |
| sniperrifle | `w_sr_sniperrifle` | sniper | 16 | 101 | 1500 | 10 | 1000 |
| heavysniper | `w_sr_heavysniper` | sniper | 12 | 216 | 1500 | 6 | 1200 |
| marksmanrifle | `w_sr_marksmanrifle` | sniper | 18 | 65 | 1000 | 8 | 300 |
| pumpshotgun | `w_sg_pumpshotgun` | shotgun | 12 | 116 | 40 | 8 | 600 |
| assaultshotgun | `w_sg_assaultshotgun` | shotgun | 14 | 108 | 35 | 8 | 300 |
| sawnoffshotgun | `w_sg_sawnoff` | shotgun | 10 | 130 | 25 | 8 | 550 |
| grenadelauncher | `w_lr_grenadelauncher` | **shotgun** | 15/14 | 100 | 120 | 10 | 800 |
| golfclub | `w_me_gclub` | melee | 4 | 10 | 2 | 1 | 500 |
| knife | `w_me_knife_01` | melee | 3 | 15 | 2 | 1 | 500 |
| bat | `w_me_bat` | melee | 3 | 12 | 2 | 1 | 500 |
| crowbar | `w_me_crowbar` | melee | 3 | 12 | 2 | 1 | 500 |
| hammer | `w_me_hammer` | melee | 3 | 12 | 2 | 1 | 500 |
| nightstick | `w_me_nightstick` | melee | 3 | 10 | 2 | 1 | 500 |
| ball | `w_am_baseball` | thrown | 3 | 5 | 40 | 1 | 1000 |

**Stat sütunları [dış kaynak] — doğrulanamadı.** Bizim `weapons.tsv.gz`
kategori/model/mermi/bileşen/livery/flags tutuyor; `Damage`, `WeaponRange`,
`ClipSize`, `TimeBetweenShots` alanları **korpusumuzda yok**. Başlangıç
değeri olarak makul, "vanilla böyle" diye aktarma.

İki şüpheli nokta: `machinepistol` menzili **120** (diğer SMG'ler 40-50) ve
`grenadelauncher`'ın kemik sınıfı olarak **shotgun**'a bağlanması —
ikincisi bilinçli bir sadeleştirme (`gun_pump` yuvası kullanılıyor).

Uygulama varsayılanı (baz seçilmeden): `damage 30 · range 60 · clipSize 12 ·
timeBetweenShots 250`, ad alanı `weapon_`.

### 1j. Tattoo hattı

**Zone adları [doğrulandı]** — gerçek `PedDecorationCollection` bölgeleri:

```
ZONE_HEAD · ZONE_TORSO · ZONE_LEFT_ARM · ZONE_RIGHT_ARM
ZONE_LEFT_LEG · ZONE_RIGHT_LEG
```

Payload: `{collection, tattoos:[{name, zone, gender, uvPos, scale, rotation}]}`
+ dövüş başına PNG. Çıktı: **`PedDecorationCollection` XML + stream `.ytd` +
fxmanifest + README**. Aşamalar: *görselleri oku → DDS → .ytd + XML →
resource paketle*. Her dövmenin **benzersiz ve geçerli bir adı (hash)**
olmak zorunda. Girdi **saydam PNG**; cinsiyet ayrı tutuluyor.

Bu yapı bilinen doğru yapı — kendi tattoo işimizde aynı iskelet kullanılır.

### 1k. Vehicle Debadger

Girdi: tam resource klasörü ya da yalnız `_hi.yft`. Export'ta korunan
uzantılar: `yft · ytd · meta · lua · ycd`. Akış:

1. **Parçalar** — tuning parçaları ve logoları otomatik tespit; hangi
   parçaların araca monte edileceği seçilir. *Parça değiştirmek aracı
   yeniden kurar ve süren debadging'i iptal eder.*
2. **Debadging** — kabartma rozetler silinir. Seçim üç modda: `Parça`
   (bağlı bileşen) · `Yüz` (üçgen üçgen) · **`Materyal`** (aynı dokuyu
   paylaşan her şey — çoğu zaman komple "badges" materyali).
3. **Dokular** — düz boyanmış logolar (direksiyon, ızgara, jant) damga ile
   siliniyor ya da doku komple değiştiriliyor; materyalin UV'si üzerine
   bindirilebiliyor. `.ytd` yoksa bu adım çalışmaz.
4. **Export** — *"YFT'in birebir yeniden yazılır, eksik olan yalnız
   rozetler: collision, deformasyon, kapılar ve camlar el değmemiş."*
   Uzak LOD (`_hi` olmayan `.yft`) **kasıtlı olarak elleniyor**.

⚠️ Bir resource = bir araç. Birden fazla araç tespit edilirse reddediyor.

### 1l. Resource Optimizer

Dosya durumları: `OK · Optimizable · Corrupted · Empty · Protected (fxap) ·
Ignored`. Yalnız **aşırı büyük `.ytd`'ler** küçültülüyor; zip yapısı birebir
korunuyor. Bozuk/boş dosya **düzeltilmiyor, raporlanıyor**. `fxap` hata
değil, "sahibi kilitlemiş" olarak işaretlenip aynen geri veriliyor.
Kabul edilen tek tek dosyalar: `ytd ydr ydd yft ybn ymap ytyp lua meta xml
cfg`. **Klasör yüklenemiyor** — zip şart.

Sonuç başlıkları: `X-Original-Size`, `X-Optimized-Size`, `X-Optimized-Count`.

### 1m. API yüzeyi ve payload şekilleri [dış kaynak]

```
GET  /api/auth/me · /api/auth/logout · /api/auth/recheck · /api/auth/discord/login
GET  /api/shaders                (açık)
GET  /api/shells/catalog         (açık)
POST /api/convert                → {jobId}     (silah — kuyruklu)
GET  /api/convert/status?jobId=  → {state, stage, queue, error}
GET  /api/convert/result?jobId=  → zip
POST /api/props/convert          → zip         (senkron)
POST /api/tattoo/convert         → {jobId}     (status/result ortak)
POST /api/shells/convert
POST /api/optimizer/analyze  ·  POST /api/optimizer/apply?jobId=
POST /api/vehicle/preview    ·  POST /api/vehicle/export
POST /api/import/scan        ·  POST /api/import/export   (Weapon Editor)
```

Durum yoklaması **2 saniyede bir**, kuyruk sırası kullanıcıya gösteriliyor.

**Prop payload'ı** — minimum bir prop hattının neye ihtiyacı olduğunun iyi
bir kontrol listesi:

```json
{ "name": "...", "lodDist": 0,
  "model": {"filename": "...", "sketchfab": {...}|null},
  "collision": {"mode": "none|box|mesh", "ratio": 0.5, "material": "default"},
  "transform": {...},
  "materials": [{"name": "...", "shader": "...", "params": {}, "textures": {}}],
  "vertexColor": [255,255,255,255] }
```

Collision mesh'i ayrı bir parça olarak, **ham float32 position buffer**
(indekssiz üçgen listesi) hâlinde gönderiliyor. Dokular
`tex:<materyalIndeksi>:<samplerAdı>` alan adıyla ekleniyor.

**Silah aşamaları (6):** *model okuma → bake → iskelet + ağırlıklar →
dokular → DDS → .ytd → metas → paketleme.*

### 1n. Adım akışları — ürün tasarımı olarak [alınacak]

**Silah (12):** Upload → Temizlik → Baz silah → **Hizalama** → Kemikler →
Şarjör → Bileşenler → Vertex group → Render → Yapılandırma → Önizleme →
Export. *Zorunlu olan tek adım baz silah seçimi;* basit vakada
`Upload → Baz → Hizalama → Export` yeterli, kalanı varsayılanla geçiliyor.

**Prop (6):** Upload → Temizlik → **Yerleştirme** → Render → Yapılandırma →
Export. Yerleştirmede ölçek referansı olarak hayalet ped var ve **üç pozu**
sunuluyor: *ayakta · oturur (sandalye ölçmek için) · yürür (merdiven basamağı
için)*. Konum ve ölçek export'ta geometriye **pişiriliyor**.

**Optimizer (3):** Upload → Analiz → Export.

Alınmaya değer üç desen:
- **Seçim iki kipli**: `Parça` (tek tıkla bağlı bileşen) ve `Yüz` (üçgen
  üçgen) — "parça gövdeye kaynamışsa Yüz'e geç" diye açıkça yazıyorlar.
- **Her adımda "bu adımı atlayabilirsin" yazılı.** Hangi adımın gerçekten
  zorunlu olduğu belirsiz bırakılmıyor.
- **Önizlemenin yalan söyleyeceği önceden söyleniyor**: *"oyunda RAGE
  shader'ları farklı aydınlatır — yalnız oyun içi test bağlayıcıdır."*
  Bu bizim `⛔ EKRAN GÖRÜNTÜSÜ ÖLÇÜM DEĞİLDİR` kuralımızın ürün hâli.

### 1o. Kabul edilen formatlar [dış kaynak]

| Araç | Format |
|---|---|
| Weapons | **yalnız GLB** (tek parça statik); dokular ayrı PNG/JPG |
| Props | GLB önerilen, GLTF kabul; FBX/OBJ **reddediliyor** |
| Bileşen içe aktarma | GLB · GLTF · FBX · OBJ |
| Optimizer | resource zip ya da tek tek dosya |
| Vehicle | tam resource klasörü ya da `_hi.yft` |
| Tattoo | saydam PNG |

Sketchfab'den gelen modeller için kendi uyarıları doğru: *"bazılarının dokusu
yok ya da GTA ile uyumsuz materyal kullanıyor (prosedürel, çok-UV) — tek
dokulu olanları tercih et."*

### 1p. Alınmayanlar ve sebebi

- **Kemik tag tablosu** — çürütüldü (§1a).
- **Shader `required` alanı** — ölçüldü, bilgi taşımıyor (§1e).
- **Shader varsayılan paramları** — bizim ölçülmüş tablomuz daha geniş ve en
  az bir yerde onlarınki vanilla'dan sapıyor (§1e).
- **Silah statları** — korpusumuzda karşılığı yok, doğrulanamadı; tablo
  `[dış kaynak]` olarak duruyor (§1i).
- **Poligon eşikleri** — ürün tercihi; vanilla bütçesinin yerine geçmez (§1c).
- **Dönüştürme hattının kendisi** — sunucuda, Discord girişi arkasında.
  Hangi kütüphaneyle ürettikleri ölçülemedi; ölçmek isteyen giriş yapıp bir
  prop üretip çıkan `.ydr`/`.ytyp`'ı vanilla ile alan alan karşılaştırsın.

---

## Bu dosyaya yeni bir araç eklerken

1. Önce **ne ölçtüğünü** yaz, sonra ne iddia edildiğini.
2. Her sayıyı `[doğrulandı]` / `[dış kaynak]` / `[çürütüldü]` / `[alınacak]`
   ile işaretle. Etiketsiz sayı bırakma.
3. Bizim ölçümümüzle çelişen bir sayı bulursan **ilgili referansın kendi
   dosyasına** uyarı bloğu koy — bu dosya arşiv, çarpma noktası orası.
4. "Onlarda var bizde yok" demeden **önce ölç**: §1e'deki `required` alanı
   tam olarak böyle elendi.


---

## 2. Sollumz Discord `#tutorials` çıkarımı (2026-08-21) — yerel `notlar/` haritası

75 mesaj, 57 video transkripti; ham veri **depoya girmez**. Damıtılmış maddeler ilgili dal yapraklarına dağıtıldı (ölçüm değil topluluk uygulaması; çakışmada ölçüm kazanır). Konu → yerel dosya:

Tam adım adım yordamlar yerel çıkarım klasörünün `notlar/` dizinindedir
(depoya girmez). Konu → dosya eşlemesi:

| konu | dosya |
|---|---|
| animasyonlu prop+collision, fragment, prop/ped cloth, ped animasyonu, retarget | `01-animasyon-fragment-cloth.md` |
| UV animasyonu, MLO ışığı, shadowmap, yansıma proxy, vertex AO, materyal, YBN hizalama, doortuning | `02-uv-animasyon-isik-golge-dunya.md` |
| `.yed`/IG_/CS_, ağırlık boyama, skintone `_r`, freemode giysi, ped ölçekleme, `p_eyes`/`p_ears`, ped prop, silah | `03-ped-giysi-prop-silah.md` |
| araç kurulumu, MLO üretimi, iç mekân LOD, arazi karışımı, parallax, timecycle, audio occlusion, ses emitter, radyo | `04-mlo-harita-ses-arac-gerec.md` |
| grafiti/decal (Substance → DDS → render bucket 2 → ymap) | `05-decal-grafiti.md` |
| time bound prop, Cable Tools, arazi/bina değiştirme | `06-altyazisiz-videolar-kare-turu.md` |
| Sollumz Discord yeni kanallar turu | `07-yeni-kanallar-turu.md` |
| çim dört sistem, arazi anatomisi, `@ma`, grass batch, LOD iki mekanizma, Sketchfab animasyonlu drawable | `08-cim-prosedurel-lod-zinciri.md` (→ `branches/map/grass-procedural.md`, `lod.md`) |
| araç eklenti envanteri | `09-arac-eklenti-envanteri.md` (→ `branches/vehicle/`) |

### Erişilemeyen kaynaklar (tekrar denendi)
- `ttKh1iOorIU` Shadowmap (YamK Mods) — **video gizli yapılmış**
- `IIrBh13-lG4` One room MLO (gta5 modder) — **video kaldırılmış**

İkisinin de konusu başka videolarla kapanıyor.


---


> Shader = program + render kovası ölçümü → `branches/look/shader.md`.


## 3. Alet envanteri — 178 transkriptin desen taraması (2026-08, topluluk)

Sollumz'un kendi düğmeleri, dış eklentiler, Blender dışı araçlar, FiveM yardımcıları, referans siteleri ve **bizde olup toplulukta olmayanlar**. Sayı = kaç ayrı videoda geçtiği. Kaynak `notlar/09` (depoya girmez).


178 transkriptin **tamamı** desen taramasından geçirildi (okunanlar + henüz
okunmayanlar dahil). Yanındaki sayı **kaç ayrı videoda geçtiği** —
topluluk standardı olup olmadığının ölçüsü.
Ham çıktı: `arac_envanteri.txt`

> ⚠️ Altyazısı olmayan videolardaki araçlar bu taramada **görünmez**
> (`Catenary`, `Substance 3D Painter`, `NVIDIA Texture Tools` gibi bazıları
> yalnız kare turundan biliniyor). Aşağıda ayrıca işaretlendi.

---

## A. Sollumz'un KENDİ araçları — eklenti değil, çoğu bilinmiyor

Bunlar zaten kurulu; ayrı bir şey indirmeye gerek yok. Buradaki asıl kazanç:
elle yapmaya çalıştığımız birkaç işin hazır düğmesi varmış.

| araç | nerede | ne yapar |
|---|---|---|
| ⭐ **Add Bone Constraint** | Drawables → Bone Tools | Collision'ı kemiğe bağlayan constraint'i **kendisi kurar ve uzayını doğru ayarlar**. `Child Of` ↔ `Copy Transforms` karışıklığının sebebi buymuş — kimse elle seçmiyor. |
| ⭐ **Apply Bone Flags: rotation and translation** | Drawables → Bone Tools | Atlas §1.5'teki *"Sollumz `Flags`'i sıfır bırakır"* sorununun Sollumz içindeki çözümü. |
| **Bone Tools → Limit** | aynı panel | Tek kemiğin bayraklarını sıfırlayıp sınırlar (silah şarjörü hizalaması). |
| ⭐ **Vertex Painter (`Shift+T`)** | viewport | RGBA kanal izolasyonu · palet · **multi-object vertex paint** · ⭐ **Terrain Paint** (texture 1-4 katman karışımını doğrudan boyar). |
| ⭐ **Cloth Tools → Diagnostics → Refresh** | Drawables | Ped cloth için **gerçek doğrulama kapısı** — binding ve materyal hatalarını sayar. Hedef sıfır. |
| **Cloth Tools → Pin / mass / pin radius** | Drawables | Cloth sabit noktaları ve vertex kütleleri. |
| ⭐ **Cable Tools** | Drawables | Vertex başına `Radius` · `Diffuse Factor` · `Micromovements` · `Phase Offset` (+`Randomize`) · `Material Index`. |
| **LOD Tools → Generate LODs** | Drawables | Referans mesh + Medium/Low, decimation varsayılan 0.6. |
| **Light Tools + Light Presets (`+`)** | Drawables | Kendi ışık ön ayarını kaydeder. |
| **Shader Tools → Convert to \<shader\>** | Drawables | Normal materyali `ped`, `ped_cloth`, `ped_emissive`, `normal_spec` vb. çevirir. |
| **Order Shaders** | Drawable hiyerarşisi | UV animasyonlu materyali sıraya sokar (Sollumz 2.9 öncesi zorunluydu). |
| **Fragments → Set Mass → Calculate** | Fragments | Collision kutularının kütlesini hesaplar. |
| **Create Physic Bones (at Objects) + "Parent to selected bone"** | Fragments | Fragment kemik zinciri kurar. |
| **Create Box From Selection** | Collisions | Seçili geometriden bound box üretir. |
| **Map Data → Create YMAP / Create Entities** | Sollumz | Blender'dan ymap üretimi. |
| **Archetype Definition → Auto-Create From Selected** | Sollumz | ytyp arketipi üretir; **tip `Base` yerine `Time` seçilirse** 24 saatlik kutu ızgarası açılır. |
| **Extensions sekmesi + `Duplicate Extension`** | ytyp | Partikül/ladder/audio extension'ları. ⛔ `Shift`+sürükle ile çoğaltılmaz, bu düğme şart. |
| **`Fill Animation Data`** | Animations | ⛔ **BOZUK** — frame count'u yanlış yazıyor, elle gir. |

---

## B. Blender eklentileri (dışarıdan kurulan)

| eklenti | kaç videoda | ne için |
|---|---|---|
| **Sushi Cleanups** | 3 | Boş vertex gruplarını temizler (ağırlık transferi sonrası şart). |
| **Vertex Color Master** | 3 | Kanal bazlı vertex boyama + **Data Transfer** (AO'yu `Colour 1`'in R kanalına taşımak). |
| **Vicho Tools** | 2 | Animasyon üretimi için "gereklilik" diye geçiyor; ayrıca **Blender içinden `.ytd` üretimi**. |
| **Rokoko** | 2 | Retarget. ⛔ **`Auto Scale` kapalı olmalı** — açıkken root motion siliniyor. |
| **DeepBump** | 1 | Diffuse'tan normal map üretir. |
| **Collider Tools** | 1 | Collision kutusu üretimini kolaylaştırır. |
| **UV Packmaster** | — | UV paketleme (adı geçti, zorunlu değil). |
| ⚠️ **Catenary** | *(altyazısız videodan)* | Kablo için gerçek zincir eğrisi üretir. Sollumz Cable Tools ile birlikte kullanılıyor. |
| **Quixotic'in ped listesi** | 1 | `R0sGnIgvBq0` — *"My Fave Blender Addons for Ped Editing"*, **henüz okunmadı**. |

---

## C. Dış araçlar (Blender dışı)

| araç | kaç videoda | not |
|---|---|---|
| **YMT Editor** (grzybeek) | **9** | En çok geçen araç. Ped bileşenleri, prop kategorileri, **render flags**, `hash_07AE529D` boy ofseti, **Generate Creature Metadata**. |
| **Folders to YTD** | 5 | Klasörden `.ytd` üretir, gerekirse DDS'e çevirir. |
| **OpenIV** | 5 | Çoğu videoda **eski yöntem** olarak; CodeWalker RPF Explorer tercih ediliyor. |
| **3ds Max** | 5 | GTA IV → GTA V rigleme hattı (wolffiremodz). Sollumz alternatifi değil, farklı bir hat. |
| **Notepad++** | 4 | XML düzenleme; tek `.ycd`'ye çok klip birleştirmenin yolu. |
| **V Weapons Toolkit** | 3 | ⚠️ **Sürüm `1.0.3`** — sonraki sürümler bozuk. |
| **FXDK / Cfx Development Kit** | 2 | Timecycle editörü (`timecycleeditor 1`). ⚠️ Önce **ReShade `dxgi.dll` kaldırılmalı**. |
| **vMenu** | 2 | Timecycle/ışık ayarlarken oyun saatini değiştirmek için. |
| **Audacity** | 2 | Sesi **left/right mono'ya** ayırmak (radyo + statik emitter). |
| **NVIDIA Texture Tools** | 2 *(+kare turu)* | DDS export. Decal için ölçülen ayar: **BC3 · mipmap MAX · Gamma Correct · Premultiplied Alpha**. |
| **Blender 3.3 (taşınabilir)** | 2 | ⚠️ **Yalnız eski shadowmap yöntemi için** — Shadow *render pass* kaldırıldığı için. Yeni yöntem güncel Blender'da çalışıyor. |
| **Audio Occlusion Tool** | 1 | ytyp+ymap XML'den `.dat151` + `.ymt` üretir. |
| **AnimKit** | 1 | 3ds Max tarafı animasyon aracı. |
| ⚠️ **Substance 3D Painter** | *(altyazısız)* | Grafiti/decal dokusu üretimi; `Opacity` kanalı şart. |
| ⚠️ **JPEXS + Adobe Flash CS6** | *(metin rehberi)* | MLOScaleformTools için — MLO içi Scaleform ekranları. |

---

## D. FiveM tarafı yardımcılar

| | ne yapar |
|---|---|
| ⭐ **`echo effect`** | Partikül efektlerini **oyun içinde** kaydırıcılarla arayıp önizletir. Partikül işine girecekse ilk kurulacak şey. |
| **`str_request_flush` benzeri konsol komutu** | Sunucuyu yeniden başlatmadan stream'i tazeler; iki videoda geçiyor, **tam adı kulaktan** — doğrulanmalı. Canary/unstable sürüm isteyebiliyor. |

---

## E. Referans siteleri ve listeler

| kaynak | ne için |
|---|---|
| ⭐ **Pleb Masters: Forge** (3 video) | Prop tarayıcı. **Prop'un partikül efektini**, prosedürel modelleri ve freemode giysi bileşenlerini gösteriyor. Partikül adı aramanın en pratik yolu. |
| **Derek Deck** listesi | Test edilmiş, **çalışan ambient partikül** adları. |
| **Dirty Free** GTA 5 data dump | Tüm partikül adlarının tam listesi. |
| **docs.sollumz.org** | Resmî doküman; Legacy→Enhanced dönüşümü orada. |
| **CodeWalker Discord** | ⚠️ CodeWalker **yalnız buradan** indirilmeli — diğer siteler eski/riskli. |

---

## F. Bizde olup toplulukta olmayanlar

| bizde | toplulukta |
|---|---|
| **`assetdb.py fx --exact`** | Elle liste taraması. Bir video yazım hatası yüzünden **bir test turu** kaybetti. |
| **`assetdb.py flags`** | Bayrak sayıları elle kopyalanıyor. |
| **`assetdb.py light --table`** (72.539 ışık p05/medyan/p95) | *"Vanilla'ya bak ve taklit et"* deniyor, sayı yok. |
| **RayFire (`des_*`) üretim hattı** | Hiçbir videoda geçmiyor. |
