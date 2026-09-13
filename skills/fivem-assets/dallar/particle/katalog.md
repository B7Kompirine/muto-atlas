# Partikül kataloğu / aile üretimi — donörden aile, kalite kapısı, referans döngüsü

**Ne zaman okunur:** çok sayıda efekt aileyi tek hattan üreteceksin (56 aile); donör seçimi, `C4`, KFP min/max, katalog denetimi, kullanıcı görseli → kod.
**When to read:** producing a family of effects from a donor, the quality gate, colour and envelope auditing.
**Kaynak:** `ptfx-flipbook-uretimi.md` §9-12, §14-15 (2026-09) · **Ölçüm:** 56 aile; `PtFxAssetStore` 400 havuzu; donör alan anlamları vanilla'dan okundu
**Önce:** `dallar/particle/_dal.md` · gövde › `govde/arac-tuzaklari.md` §3 CodeWalker (`FxcFileHash`, `VFT`, `ResourcePointerArray64`) · betikler `ptfx_katalog_kur.py`, `ptfx_kalite_kapisi.py`, `ptfx_donor_ara.py`, `ptfx_birlestir.py`

---

## 9. Üretilen 15 aile — ⛔ AÇIK İŞ VAR, ÖNCE BUNU OKU

`duman · ates · alev_topu · toz · buhar · kivilcim · sicrama · kor · sis ·
kabarcik · parca · halka · elektrik · kan · yaprak`

Dağıtım: `resources/[script]/muto_ptfx/stream/` (33 `.ypt`; 15'i aile,
gerisi teşhis izi). Tezgâh ayrı kaynakta: `muto_ptfx_test`.

### ⛔ BU BÖLÜMÜN ESKİ HÂLİ YANLIŞTI

Eskiden "hepsi 49 kare (7×7) @ 1024, `C4 = 48`" yazıyordu. Bu **§1e'deki
4×4 bulgusundan ÖNCEKİ** durumdu ve güncellenmemişti. Dağıtılmış dosyalar
geri okunarak ölçüldü (`res_to_xml.ps1` → `AnimateTexture/UnknownC4`):

| dosya | `C4` | doku | değerlendirme |
|---|---:|---:|---|
| `muto_n4` (kontrol, 4×4) | **15** | 1024 | doğru |
| `muto_n7` (kontrol, 7×7) | **48** | 1024 | doğru (eski hâl) |
| **15 ailenin HEPSİ** | **0** | **512** | ⛔ |

### ⛔ AÇIK KUSUR: ailelerin `C4`'ü 0

§1'e göre `C4` **oynatılacak son kare indeksidir**. `C4 = 0` demek
**yalnızca 0. kare oynar** — yani flipbook hiç dönmez, efekt donuk kalır.
4×4 sayfa için **15** olmalı.

İki bağımsız kaynak aynı şeyi söylüyor: kuralın kendisi (§1e "`UnknownC4`
**15** yazılır") ve kontrol varlığı `muto_n4` (C4=15). Aileler 19:32'de
yeniden üretilirken bu adım yazılmamış.

Doku çözünürlüğü de 512 (§1e'nin 4×4 ızgarası 512'yi 128 px hücreye tam
böler, yani ızgara tutarlı — sorun yalnızca `C4`).

⚠ **BURASI AÇIK SORUYA BAĞLI — ÖNCE §1e-BIS OKU.** Ailelerin `C4=0`
olması bir kusur mu, yoksa doğru üretim yolu mu, **dilimlemenin çalışıp
çalışmadığına bağlı** ve bu 2026-09-02 itibariyle çözülmedi:
§1b (`t1`) çalıştığını, §1e çalışmadığını söylüyor; ikisi de temiz
ölçümle kapatılmadı.

- dilimleme ÇALIŞIYORSA → `C4 = kare − 1` (4×4 sayfa → **15**) yazılmalı,
  `C4=0` gerçek kusurdur
- ÇALIŞMIYORSA → `C4=0` zaten doğru, dokunma

⛔ **Bu ikisinden birini seçmeden aileleri yeniden üretme.** Önce
§1e-BIS'teki ayrım testini temiz çalıştır.


## 10. Katalog üretim hattı — donörden aile üretmek ve DENETLEMEK

Katalogdaki bir efekt ailesi sıfırdan yazılmaz; vanilla bir donörden
transplant edilir (§1b) ve sonra **ölçülerek** denetlenir. İki betik:

```
python ptfx_katalog_kur.py    --grup <grup>   # üretir
python ptfx_kalite_kapisi.py  --grup <grup>   # vanilla'ya karşı denetler
```

**İlke: donörün kendi değerleri KORUNUR.** Vanilla o efekti zaten
dengelemiş. Yalnız ailenin gerçekten farklı olması gereken alanı override
edilir ve her override'ın **gerekçesi spec'te yazılır**. Gerekçesiz
override "gereksiz fazla / gereksiz az efekt" üretmenin en hızlı yoludur.

### ⛔ Aralığı tek sayıya ÇÖKTÜRME — ölçüldü

`--oran` / `--omur` bir zamanlar R ve G yuvalarına **aynı sayıyı** yazıyordu.
Bu, parçacıkların rastgeleliğini kaldırır: hepsi tam aynı süre yaşar ve
**aynı anda ölür**, göz bunu "mekanik" okur. Ölçüm (n=1989 emitter):

| alan | aralık veren | medyan maks/min |
|---|---|---|
| `m_particleLifeKFP` | **%90,3** | 1.45 |
| `m_spawnRateOverTimeKFP` | %56,7 | 1.40 |

Yani düz sayı yazmak **çoğunluk vakada vanilla'dan sapmaktır.** Doğrusu:
donörün kendi yayılma oranını koru, aralığı istenen **ortalamaya** taşı
(`mn·d/ort`, `mx·d/ort`). Donörde aralık yoksa düz kalır — o da donörün
kendi tercihidir.

### Kapının ölçtüğü iki şey

1. **Donör sapması (kesin referans).** Spec'te override *yazılmayan* bir
   alan değişmişse bu kazadır → ihlal. Override yazılıp değer
   değişmemişse de ihlal (etkisiz override).
2. **Vanilla bandı (popülasyon referansı).** Eş zamanlı yük
   `ort(oran) × ort(ömür)` bütün vanilla emitterlerin dağılımına konur:
   **p05 = 1 · medyan = 18 · p95 = 225**. Altı "gereksiz az", üstü
   "gereksiz fazla".

Ayrıca sessiz kıranlar: `UnknownC4 ≠ 0`, `RGB_*` teknik (alfayı yok sayar),
yanlış doku adı.

### ⛔ Emitter adı efekt adıyla AYNI DEĞİLDİR

`fire_extinguish` efektinin emitteri bu yüzden bulunamadı ve kapı
"donör emitteri yok" dedi. Bağ **`<EmitterRule>ad</EmitterRule>`**
alanındadır. Ada göre tahmin etme, bağı oku.

### ⛔ KFP kanal anlamı: `Red` = MIN, `Green` = MAX

Tek bir sayı okumak (ilk kanal) aralığın üst ucunu görmezden gelir; seyrek
görünen bir emitter aslında birkaç kat yoğun olabilir.

### ⛔ Donörün kendi değerini "hata" diye raporlama

Kapı önce `sizeScalar ≤ 1.5` gördüğü her yerde uyarıyordu ve
`ent_amb_fbi_cinder`'ın **0.4437**'sini ihlal saydı. O değer donörün kendi
vanilla değeridir ve vanilla `sizeScalar`'ın **%2'si** 1.5'in altındadır
(n=1901; p05 = 5.22, medyan = 65.5). Kural yalnız **biz** o alanı
yazdığımızda çalışmalı — yoksa yanlış alarm üretir. (Aynı ders §2'nin
kardeşi: aracın bir şeyi işaretlemesi o şeyin bozuk olduğunu göstermez.)

### ⛔ Yaprak/çöp efektleri SPRITE DEĞİL

`ent_amb_falling_leaves_*` MESH parçacıklardır (`ParticleBehaviourModel`),
dokuları yoktur ve transplant *"particle rule'da `<TextureName>` yok"* ile
düşer. Savrulma/uçuşma için sprite tabanlı donör gerekir —
`ent_amb_fbi_falling_debris` çalıştı.


## 11. Animasyon zarfı — tek kare sprite'ın hareketi BURADAN gelir

Sayfa dilimlemesi çalışmadığı için (§1e) sprite statiktir. Geriye kalan tek
hareket kaynağı **ömür boyunca alfa/boyut/renk eğrileri**dir. Eğri düzse
parçacık canlı değil, yapıştırma görünür.

Eğri `ptxu_Colour:m_rgbaMinKFP` / `m_rgbaMaxKFP` içindedir.
`InterpolationInterval` = 0..1 normalize ömür, `AlphaChannelColour` = o
andaki alfa. ⛔ **`KeyFrameMultiplier` uydurulmaz:** ölçüldü,
`1 / (t[i] − t[i−1])`, ilk karede 0.

**Ölçüm (n = 1735 vanilla particle rule):**

| | oran |
|---|---|
| `t=1`'de alfa 0 (fade-out) | **%88,2** |
| `t=0`'da alfa 0 (fade-in) | %44,7 |
| keyframe sayısı medyanı | 3 (%9,3'ü tek kare = sabit) |
| tepe alfa | p05 0.1 · medyan 0.7 · p95 1 |

Yani **fade-out neredeyse zorunlu, fade-in değil** — kıvılcım ani belirmeli.
Onarırken donörün ani belirme tercihini koru, yalnız sondaki pop'u gider.

### ⛔ HAREKETİ DOKUDAN ALAN DONÖR, STATİK SPRITE'LA ÖLÜR

En pahalı madde. `ent_amb_dry_ice_vent`'in alfa zarfı **tek keyframe**
(sabit 0.5) — ama dokusu `ptfx_smoke_wispy_anim`, yani animasyonlu sayfa.
Hareketi doku sağlıyordu. Biz dokuyu tek kare sprite ile değiştirince o
efektte **değişen hiçbir şey kalmadı**: parçacık tam alfayla belirip tam
alfayla yok oluyor. Vanilla'da doğru olan bir değer, bizim hattımızda
kusurdur.

231 uygun donörün **20'si** sabit alfa, **14'ü** sonda alfa > 0 ile
popluyor — toplam **%14,7**. Üretici (`ptfx_katalog_kur.py: zarf_onar`)
bozuk zarfı vanilla şeklinde yeniden yazar ve ne yaptığını raporlar.

### ⛔ MIN ve MAX zarflarının İKİSİNE birden bak

Bir tur boyunca yalnız `min` denetlendi; `kagit_savrulma` ile
`moloz_yagmuru`nun **`max` zarfı 0.8'de bitip popladığı halde** kapıdan
"geçti" aldı. İki zarf ayrı ayrı bozulabiliyor.

### ⛔ `<ParticleRule>` EMITTER'da değil EFEKT blogundadır

Emitter blogunda hiç `*Rule` etiketi yok (ölçüldü: boş küme). Yanlış yerde
aramak **her donörü** *"MESH parçacık, doku yok"* diye raporladı — oysa aynı
donörden dokulu bir efekt üretilmişti. (§2'nin aynısı.)

### ⛔ Katalogun ad referansları donör DEĞİLDİR

Yıkım için yazılan 18 referansın (`bang_concrete`, `bul_glass`,
`scrape_metal` …) **hiçbiri** kullanılamadı: hepsi çok emitterli. Sebep
yapısal — bir çarpma efekti doğası gereği toz + kıymık + püf'tür, yani 3-6
emitter. Transplant edilebilir efekt **231 / 964**. Seçim **davranışa**
göre yapılır, ad benzerliğine göre değil: `ptfx_donor_ara.py --ara <terim>`
ve dokuya göre gruplama.

### ⛔ Bandı donöre karşı muaf tut

Vanilla'nın kendi efektlerinin %5'i tanım gereği p95'in üstündedir.
Donörün değerini koruyup bandı ihlal etmek "vanilla gibi" olmanın ta
kendisidir (`cokme_tozu` yük 244). Band yalnızca **bizim** yükü donörden
uzağa taşıyıp taşımadığımızı ölçmeli.

### ⛔ Build çıktısını GREP'LEYEREK okuma

`for n in zn:` döngüsü dıştaki sayaç `n`'i ezdi, build ilk onarımdan sonra
`TypeError` ile çöktü ve **kalan 8 dosya hiç yeniden üretilmedi**. Çıktı
`grep -E "zarf|kurulan"` ile okunduğu için traceback görünmedi; kapı da
bayat dosyaları ölçüp *"11/11 geçti"* dedi. İki tur bu yanılgıyla geçti.
Üretim betiğinin çıktısını **filtrelemeden** oku, ya da `set -o pipefail`
kullan ve çıkış kodunu kontrol et. ("Komut hata vermedi" dağıtım kanıtı
değildir — §7'nin kardeşi.)


## 12. ⛔ `PtFxAssetStore Pool Full, Size == 400` — havuz DOSYA sayar

Belirti: oyun açılışta `INIT_SESSION` sırasında çöker
(`CExtraContentWrapper`, `c0000005`). Sunucu tarafında hiçbir iz yoktur;
hata istemcinin kendi kutusundadır ve sebebini açıkça yazar.

**Havuz efekt kuralını değil DOSYAYI sayar.** Kanıt kesin: `core.ypt` tek
dosyada **964 efekt kuralı** taşır, havuz ise 400 — kural sayılsaydı
vanilla kendi başına havuzu patlatırdı. `RequestNamedPtfxAsset` de dosya
adını alır.

Sonuç: **"efekt başına bir dosya" savurganlıktır.** 35 aile 35 slot yerine
**1** slot harcayabilir. Ölçüldü: 35 dosya → tek `muto_efektler.ypt`
(1.49 MB), doğrulama 35/35 zincir ve zarf sağlam.

Araç: `ptfx_birlestir.py --ad muto_efektler --klasor <dizin>`

### Birleştirmenin dört bağı

- **`TextureDictionary` HASH SIRALI olmak zorunda** (RAGE ikili arama
  yapar). Ölçüldü: vanilla `core.ypt`in 107 dokusu Jenkins hash'ine göre
  sıralı; öte yandan **üç kural sözlüğü sıralı DEĞİL** (ne alfabetik ne
  hash). Yalnız dokuları sırala, ötekilere dokunma. Hash fonksiyonunu
  doğrulamanın yolu: vanilla doku sırasının senin hash'inle sıralı çıkması.
- **Dokular XML'e GÖMÜLÜ DEĞİL** — `<FileName>x.dds</FileName>` ile
  dışarıdan okunur. Birleştirilmiş XML'in yanında bütün `.dds` dosyaları
  bulunmalı, yoksa derleme sessizce dokusuz çıkar.
- **Birleştirmeden sonra VARLIK adı ≠ EFEKT adı.** Artık
  `RequestNamedPtfxAsset('muto_efektler')` +
  `UseParticleFxAssetNextCall('muto_efektler')` +
  `StartParticleFx*('muto_duman', …)`.
- ⛔ **Varlık adına göre tutulan her kayıt SESSİZCE BOZULUR.** Harness
  handle'ları `acik[varlik]` ile saklıyordu; birleşmeden sonra bütün
  efektlerin varlığı aynı olduğu için her yeni efekt öncekinin handle'ını
  ezdi — `/ptfxdur` 19 efekti açık bırakacaktı. Anahtar **efekt adı**
  olmalı. Bu tür kayıtları birleştirmeden önce tara.

### Bunu ilk elemede yakala

Sunucudaki özel `.ypt` sayısını **kaynak bazında** say
(`find resources -name '*.ypt'`). `_kaynak/` gibi `stream/` dışındaki
klasörler yüklenmez, sayma. Emekli test kaynaklarını
`fxmanifest.lua.KAPALI` ile kapat — sunucunun kendi geleneği, tek
adlandırmayla geri gelir.

### ⛔ `res_to_xml.ps1` klasörü `-Path` ile almaz

`-Path <klasor>` *"Access to the path is denied"* der ve **0 başarılı**
raporlar; doğrusu `-Dir <klasor> -Filter "*.ypt"`. Hata mesajı izin
sorunuymuş gibi görünüyor, oysa parametre yanlış.


## 14. Katalog tamamlandı — 56 aile, ölçülmüş dört yeni tuzak

Sekiz grup, **56 / 56** kapıdan geçti; 15 üretim sprite'ıyla birlikte
**71 efekt tek `.ypt`de** (`muto_efektler.ypt`, 2.94 MB, 1 havuz slotu).
İkiliden geri okundu: 71/71 zincir, doku ve zarf sağlam.

Katalogun 58 ailesinden **ikisi bilerek dışarıda**, ikisi de katalogun
kendi ifadesiyle partikül işi değil:
`kalkan_kubbesi` (mesh + shader) ve `isi_dalgalanmasi` (kırılma shader'ı,
`ptfx_heathaze_n` bir normal-map dokusudur). Partikülle taklidi kötü sonuç
verir; gerekçe spec'te yazılı.

### ⛔ ÇOK DOKULU donör kullanma

`liquid_splash_petrol` **iki** doku ister: `ptfx_gloop_n` (NORMAL MAP) +
`ptfx_gloop` (renk). Transplant tek sprite'ı **ikisine birden** yazar ve
shader yanlış ışıklanır. Kapı bunu *"doku adı ['muto_roket','muto_roket']"*
diye yakaladı. Ölçüldü: 231 uygun donörün **6'sı** çok dokulu; çoğunun tek
dokulu bir ikizi var (`petrol → liquid_splash_water`, aynı ömür bandı).
`ptfx_donor_ara.py` artık bunları eliyor.

### ⛔ `ptxu_Acceleration`ın İKİ varyantı var

`m_xyzMinKFP`/`m_xyzMaxKFP` (1392 kural) **ve** `m_strengthKFP` (24 kural,
skaler). `ent_amb_fly_swarm` ikincisini kullanır; xyz yazmaya çalışmak
sessizce başarısız olur. Alan adını tek varyant sanma.

### ⛔ MAX alfa zarfı TAMAMEN SIFIR olabilir — bu geçerlidir

Ölçüldü: 1733 kuralın **87'si (%5,0)** böyle, `ent_amb_tnl_bubbles_lge`
gibi oyunda çalışan efektler dahil. Max sıfırsa aralık yok demektir, min
geçerlidir. Kapı bunu *"görünmez / animasyonsuz"* diye raporlıyordu — yanlış
alarm; artık muaf. (Min zarfı için aynı muafiyet **yoktur**.)

### Donör artık İSKELET

Hareketi biz yazdığımız için donörün kendi hareketi ölçüt değil. Seçim
ölçütü üç şey: tek emitterli · **tek dokulu** · gereken davranış birimlerini
taşıyor. Üç birimi (Acceleration + Dampening + Rotation) birden taşıyan
**115 / 231**. Ömür bandı ailenin istediğine yakın olan seçilir; gerisi
yazılır.

Bir birim gerçekten yoksa ve istenen değer **no-op** ise (ivme = 0)
anahtarı **kaldır** — taşımadığı bir şeyi istemek yerine. `elec_crackle` ve
`fbi_live_wires`ta hiç hareket birimi yok ve bu doğru: elektrik arkı uçmaz,
yerinde çakar.

### ⛔ Birleştirmeye eski birleşik çıktıyı sokma

`muto_katalog.ypt.xml` (önceki turun 20'lik birleşiği) girdi klasöründe
kalmıştı ve yeniden birleştirmeye karıştı; içindeki **hareket yazılmadan
önceki** sürümler dedup'ta yalnız alfabetik sıra sayesinde elendi. Şansa
bırakılacak şey değil — birleştirmeden önce klasörü temizle ve
`kaynak dosya` sayısının beklenen aileyle **birebir** tuttuğunu doğrula.

### Test düzeni

`/ptfxkat` 56 efekti 4 m aralıkla dizerse 224 m eder ve hiçbir kameraya
sığmaz. Izgara: 8 sütun × 7 satır (28 × 30 m). `/ptfxkat <n>` 16'şarlık
sayfa gösterir, yakından bakmak için.


## 15. Referans döngüsü — kullanıcı görseli üretir, biz karakteri koda taşırız

Kullanıcı kararı (bu hattın kuralı): **ChatGPT görselleri doğrudan sprite
olarak KULLANILMAZ** — referanstır. Tek istisna kullanıcının açıkça
beğendiği parça (mor rune çemberi). Görseller
yerel bir klasörde (depoda yok).

Döngü: ChatGPT'ye 2×2 atlas ürettir (tam siyah zemin, yazı yok) → yan yana
karşılaştır (`ref_vs_biz`) → farkı üç-dört somut karaktere indir → üreticiyi
o karakterlere göre yeniden yaz → tekrar karşılaştır.

Ölçülen/yaşanan tuzaklar:

- ⛔ **ChatGPT'ye çok satırlı mesaj `type` ile gönderilemez** — ilk satır
  sonunda mesaj gider, kalan tarif hiç ulaşmaz ve model konuları uydurur
  (ilk atlas dört generic patlama çıktı). Prompt TEK satır olmalı.
- ⛔ **Sayfa yüklenmeden `type` başlarsa metnin çoğu kaybolur** — kutuda
  `--` kalıntısı görüldü. Önce ekran görüntüsüyle kutunun geldiğini doğrula.
- Görsel URL'leri gizlenir (auth token) — indirme düğmesi kullanılır,
  `Downloads/ChatGPT Image *.png`.
- Siyah zeminden alfa: `a = max(R,G,B)`, sonra **unpremultiply**
  (`rgb/max(a,eps)`); yoksa kenarlar kararır. Kesit `atlas_isle.py`.
- ⛔ **Dalgalı yarıçap cam üretmez, ÇİÇEK üretir** (yaşandı). Köşeli parça
  = rastgele yönlü 5-6 **yarı düzlemin kesişimi**; kenar = sınıra uzaklık.
- ⛔ İnce çizgiler bulanıklıkta yok olur: 0.01 radyan diken ≈ 1 piksel
  (EMP halkasında yaşandı). Çizgi kalınlığını piksel cinsinden düşün.
- Ateş karakteri: beyaz sıcak çekirdek + açıya bağlı FİLAMENT modülasyonu
  + enerjiden renk rampası (`R=0.55+0.9e · G=1.55e−0.08 · B=2.6e−1.55`).
  Düz radyal falloff "turuncu disk" verir.
- Elektrik karakteri: cos^n dikeni değil **gerçek zikzak çizgi geometrisi**
  (segmentli polyline + yan dallar).
- Kan karakteri: yuvarlak benek değil — hareket yönünde **uzamış damla** +
  merkezden damlaya viskoz iplik (kısa ömürlü).
- Kıvılcım yağmuru: benek değil **ince parlak çizgi** (motion blur hissi),
  uçlarda dallanma.

Temel 15'in spriteı değişince `ptfx_hepsi/muto_<ad>.dds` de tazelenmeli —
katalog kurucusu onları üretmez, birleştirici hazır DDS'i alır.
