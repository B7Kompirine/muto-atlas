# Partikül doku sayfası — kare, `C4`, ızgara, yoğunluk, donör transplant

**Ne zaman okunur:** efektin **dokusunu** üreteceksin: kaç kare, hangi çözünürlük, `C4` ne yapar, sayfa bölünüyor mu, yoğunluk/siluet nasıl ölçülür, hangi donörden transplant.
**When to read:** the particle texture page — frame count, `C4`, grid, density, transplanting a donor's page.
**Kaynak:** `ptfx-flipbook-uretimi.md` §1-§5 (2026-08/09) · **Ölçüm:** 15 aile oyunda; sayfa bölünmesi görsel kanıtla; 107/107 vanilla partikül dokusu DXT
**Önce:** `branches/particle/_branch.md` · `ypt-from-scratch.md` (dosyanın kendisi) · gövde › `trunk/gta-fundamentals.md` §5 doku

---

## 1. Kare sayısı ve çözünürlük — ⛔ İKİ KURAL DA YANLIŞ YAZILMIŞTI

İlk sürümde buraya iki kural yazdım, ikisi de yanlıştı ve zincirin tamamını
bozdu. Oyunda belirti şuydu: **her sprite 8×8 sayfanın tamamını tek karede
çiziyordu** — ekranda "küçük görüntülerden oluşan bir ızgara". Yani motor
ızgarayı hiç uygulamıyordu.

### ⛔ Yanlış 1: "ızgara dokuyu tam bölmeli"

Bölmek zorunda **değil**. Vanilla `ptfx_smoke_wispy_anim` 1024×1024 üzerinde
**7×7**'dir: 1024/7 = **146.29**. Motor UV uzayında `1/k` adımlarla örnekler,
piksel hizası aramaz. Bu uydurma şart yüzünden 36 kare reddedildi ve
**64 kareye (8×8) geçildi** — asıl hata buradan doğdu.

### ⛔ Yanlış 2: "63 bandın üstünde ama motor kabul eder"

Kabul etmiyor. "Geri okuma doğruladı" demek yalnızca **dosyanın öyle
yazıldığını** doğrular; motorun onu kullandığını değil. `core.ypt`'teki
**781 `AnimateTexture` davranışı** ölçüldü:

| ölçüm | değer |
|---|---|
| `Unknown_C4h` en büyük | **49** (yani en çok 50 kare) |
| `C4 > 48` olan kural | **1** |
| `C4 > 63` olan kural | **0** |

64 kare vanilla bandının tamamen dışındadır ve motor ızgarayı **hiç**
uygulamaz. Güvenli tavan **49 (7×7)** — hem `ptfx_sheet.py` hem
`build_custom_ptfx.py` artık 49'u aşanı reddediyor.

### ⛔ `C4` ızgara DEĞİL, oynatılacak SON KARE İNDEKSİDİR

Bu ayrımı yapmadan `C4`'ten ızgara çıkarmaya çalışmak yanlış yola sokar.
Aynı `ptfx_smoke_wispy_anim` dokusu (görsel olarak sayıldı: **7×7 = 49
kare**) vanilla'da şu `C4` değerleriyle kullanılıyor:
**21, 35, 37, 38, 40, 42, 43, 44, 47, 48**. Yani kurallar sayfanın bir
**alt aralığını** oynatabiliyor.

Izgara, dokuya göre **baskın** `C4` değerinden okunur (`grid = √(C4+1)`) ve
gözle sayılarak doğrulanmıştır:

| doku | ızgara (sayıldı) | baskın `C4` |
|---|---|---|
| `ptfx_water_splashes_sheet_b` | 2×2 = 4 | 3 |
| `ptfx_bubbles_trail_anim` | **5×5 = 25** | 24 (11/11 kural) |
| `ptfx_flipbook_fire_rgb` | 5×5 = 25 | 24 (25/25) |
| `ptfx_smoke_billow_anim_rgba` | 6×6 = 36 | 35 (13/13) |
| `ptfx_smoke_wispy_anim` | **7×7 = 49** | 48 (342/405) |

**Üretirken alt aralık kullanma** — `C4 = kare − 1` yaz, sayfanın tamamı
oynasın.

### Izgarayı taşımayan alanlar (elenmiş, tekrar aranmasın)

Aşağıdakilerin hiçbiri ızgarayı kodlamaz — **aynı doku için serbestçe
değişiyorlar**, ölçüldü:

- `Unknown_C0h` — 776/781'de 0
- `Unknown_C8h` — {0,1,2,4}; aynı dokuda hem 0 hem 1 geçiyor
- `Unknown_CCh` — {0x01010100, 0x01000000, 0x01000100, 0x01010000};
  wispy dokusunun tek başına dördü de var
- `Unknown_11Ch` — aynı wispy dokusu için 12/14/16/18/20/22/23/33
- `ShaderVars` — 21 değişkenin hiçbirinde 7 ya da 1/7 yok
  (`Unknown_18h` bir shader **register** indeksi; `diffusetex2` register 4)

**Yapı olarak bizim kuralımız vanilla ile eşleşiyordu**: davranış listeleri
(L1 `... AnimateTexture Colour Sprite`, L2/L3 aynısı Sprite'sız, L5 yalnız
`Sprite`), teknik (`RGBA_lit_soft`, vanilla'da 567 kuralda), `Sprite` bloğu
(tek fark `Unknown_44h` 0.5/0). Tek gerçek fark kare sayısıydı.

Vanilla `core.ypt` ölçümü (1736 partikül kuralı):
`ParticleBehaviourAnimateTexture` taşıyan **781 (%45)**.
`Unknown_C4h` dağılımı: 48 ×401 · 35 ×70 · 24 ×49 · 3 ×128 · 15 ×8.
`Unknown_CCh` 0x1010100 ×367 · `C0`=0 ×776 · `C8`=1 ×476.

---

## 1b. ⛔ SIFIRDAN YAZILAN KURAL IZGARAYI UYGULATMIYOR — üretim yolu TRANSPLANT

Sayfa doğru, `C4` doğru, davranış listeleri vanilla ile aynı, teknik aynı,
`FxcFileHash` dolu — ve oyunda her sprite **sayfanın tamamını tek karede**
çiziyor. Renk kodlu beş denekle ölçüldü (`t1..t5`, her biri ayrı renk;
konumdan okumak iki kez yanlış teşhise yol açtı, **renkle etiketle**):

| denek | kural | doku | sonuç |
|---|---|---|---|
| t1 | **vanilla** (2×2 donör) | bizim 2×2 | ✅ **düzgün** |
| t2 | bizim | vanilla wispy 7×7 | ❌ ızgara |
| t3 | bizim | bizim 7×7 | ❌ ızgara |
| t4 | bizim + vanilla'nın 21 shader değişkeni | bizim 7×7 | ❌ ızgara |
| t5 | bizim | bizim 2×2 | ❌ ızgara |

Okunuşu kesin: **doku hattı sağlam** (t1 bizim ürettiğimiz sayfayı
dilimliyor), **kare sayısı ilgisiz** (t5 de 2×2), **shader değişkenleri
ilgisiz** (t4). Değişkenin tamamı **bizim kural bloğumuzda**.

Elenen alanlar (aynı doku için serbestçe değişiyorlar, ızgarayı
kodlamıyorlar): `C0` (773/778'de 0), `C8`, `CC`, `Unknown_11Ch`,
`ShaderVars`, `Sprite.Unknown5C` (vanilla'da da `0x100`).
Hangi alan olduğu **henüz bulunamadı**.

### Üretim yolu: `ypt_transplant.py`

Çalışan bir vanilla kuralı kopyalanır, yalnız doku/renk/boyut değişir.
Donör **tek emitterli** olmalı ve `C4`'ü bizim sayfamızla eşleşmeli.

```bash
python ypt_transplant.py core.ypt.xml --efekt veh_respray_smoke     --yeni-ad my_duman --doku my_duman --klasor .     --renk 0.62 0.60 0.58 --boyut-carpan 1.0
```

`core.ypt`'te **120 tek emitterli animasyonlu donör** var; çoğu `C4=48`
(7×7). Ölçülmüş seçim: duman/toz `veh_respray_smoke` ·
`weap_veh_turbulance_sand` · ateş `fire_map` · kor `fire_ped_smoulder` ·
sis `veh_vent_rc` · buhar `ent_amb_steam_prison` · sıçrama/kan
`blood_mouth` · halka `fire_extinguish`.

⛔ **Donör aramasını `<Name>` etiketiyle bölme.** `<Name>` keyframe
özelliklerinde de geçer; kural sınırı `
  <Item>
   <Name>` dizisidir.
Yanlış bölme "tek emitterli animasyonlu donör **yok**" dedirtti — gerçekte
120 tane vardı ve bir tur kaybettirdi.

### ⛔ DONÖRÜN TEKNİĞİ KENDİ DOKUSUNA GÖRE SEÇİLMİŞTİR

Transplant donörün `FxcTechnique` alanını da aynen taşır — ve o teknik
**donörün kendi dokusuna** göre seçilmiştir. `fire_map` donörünün dokusu
`ptfx_fire_v2` alfasızdır, tekniği `RGB_lit_soft`'tur.

`RGB_*` teknik dokunun **alfa kanalını yok sayar**. Bizim sayfalarımızın
şekli alfadadır (DXT5) → her parçacık hücrenin tamamını **opak bir kare**
olarak çizer. Oyunda belirti ızgaraya çok benzer ve "hâlâ kare kare"
diye okunur, ama sebebi bambaşkadır.

Ölçüldü: 15 transplant çıktısının 13'ü `RGBA_lit_soft`, ikisi
(`ates`, `alev_topu` — ikisi de `fire_map` donörlü) `RGB_lit_soft`.
Düzeltme `RGB_x` → `RGBA_x`; teknik düz bir dize alanıdır.

**Kapı:** transplant sonrası tekniği denetle — alfalı doku + `RGB_*`
teknik birleşimi sessiz bir hatadır.

---

## 1d. Yoğunluk ve yapı — vanilla bandı

Format çalıştıktan sonra kalan şikâyet şuydu: *"referanstaki gibi yoğun
değil"* ve *"1024 daha net göründüğü için sis efekti tam olmuyor"*.
İkisi de içerik sorunudur, ölçülebilir.

### ⛔ SAYFALARIMIZ HİÇ OPAKLIĞA ULAŞMIYORDU

Ölçüldü — 15 ailenin alfa **tepesi** 0.30–0.47, vanilla duman sayfalarında
0.59–0.97. Efekt yanlış değil, hiçbir yerde yeterince opak değil. Sebep tek
bir yerde değil: kenar maskesi + bulanıklık + ömür sönmesi üst üste binince
tepe eziliyor. Aile bazında uğraşmak yerine sayfa üretildikten **sonra**
tepe hedefe ölçeklenir (`ALFA_TEPE` tablosu). Ölçüt **maksimum değil
99,7'lik dilim** — tek aykırı piksel bütün sayfayı söndürür.

### ⛔ KARŞILAŞTIRMA IZGARASI EŞLEŞMELİ

Yoğunluğu vanilla'nın **2×2** sayfasıyla kıyaslamak yanlış hedef verdi.
Vanilla'da ızgara büyüdükçe sayfa **seyrekleşir**:

| vanilla sayfa | ızgara | doluluk | alfa ort | alfa tepe | yapı |
|---|---|---|---|---|---|
| `ptfx_smoke_new_plumes` | 2×2 | %62,2 | 0,228 | 0,932 | 0,0120 |
| `ptfx_smoke_billow_anim_rgba` | 6×6 | %58,3 | 0,350 | 0,965 | 0,0119 |
| `ptfx_smoke_wispy_anim` | **7×7** | **%18,7** | **0,039** | 0,742 | **0,0052** |
| `ptfx_smoke_thin_anim` | 6×6 | %20,3 | 0,044 | 0,709 | 0,0057 |

Bizim 7×7 sayfamızın ölçütü `wispy`'dir, `new_plumes` değil.

### ⛔ YOĞUNLUĞU GÜRÜLTÜYÜ EZEREK ARTIRMA

Doluluğu yükseltmek için çarpan `0.86 + 0.34·kabar` yapıldı; aralık
neredeyse sabit olduğu için doluluk arttı ama **yapı dümdüz oldu** — gri
zemine bindirilince "bulanık bir top" gibi okundu. Yoğunluk **maskeden ve
eşikten** gelir, gürültünün genliği tam kalır.

### ⛔ TEK OKTAV KIVRIM VERMEZ

Vanilla dumanında iki ölçek var: kaba kabarcık + ince filament. İkinci,
yüksek frekanslı katman (`_fbm(c, 3, 9, ...)`) eklenmeden duman "duman"
gibi okunmuyor. Ölçüt **gradyan** (`yapı`): vanilla 7×7 = 0,0052.

### ⛔ EROZYON EŞİĞİ ZAMANLA YÜKSELİR, DÜŞMEZ

`esik = 0.44 − 0.24·t` yazıldığında geç karelerde eşik o kadar düşüyordu ki
gürültünün **tamamı** geçiyor, modülasyon bitiyor ve geriye **çıplak radyal
maske — düz bir disk** kalıyordu. Gerçek duman dağılırken **parçalanır**:
`esik = 0.34 + 0.26·t`.

### ⛔ SİLUET DAİRE OLMAMALI

Maskeye sabit taban (`0.10 + ...`) eklenirse gürültünün boş olduğu yerlerde
bile soluk bir disk kalır ve daire kenarı çıplak okunur. Taban kaldırılır,
yarıçap gürültüyle bozulur (`r − 0.13·(d1 − 0.5)`).

### Yoğunluğu GRİ zeminde ölç

Koyu zemin alfası düşük içeriği affeder; gri zemin affetmez. Yoğunluk
karşılaştırması `(120,122,126)` üzerinde yapılır.

**Sonuç (duman 7×7):** doluluk %20,0 · alfa ort 0,058 · tepe 0,618 ·
yapı 0,0043 — vanilla `wispy` bandında.

---

## 1e-BIS. ✅ SAYFA BÖLÜNÜYOR — GÖRSEL KANIT ALINDI (2026-09-02)

**§1e'nin "sayfa dilimlemesi custom `.ypt`'de hiç çalışmıyor" hükmü
YANLIŞTIR.** §1b'nin `t1` satırı doğruymuş.

### Kanıt — tek yorumu olan deney

2×2 sayfa, dört hücrede **dört farklı şekil**: disk · halka · artı · üçgen.
Oyunda çekilen tek karede **dördü de ayrı ayrı, tam parçacık olarak**
görünüyor: iki halka (ortaları delik), iki üçgen, bir artı, iki dolu disk —
farklı konum, farklı boyut, farklı dönüş.

⏵ Sayfa bölünmeseydi **her parçacık dördünü birden içeren tek bir kare
damga** olurdu ve bütün parçacıklar birbirinin aynı görünürdü.

Görsel: `flipbook_deney/P4_zoom.png` (gece arka planı şekilleri en okunur
yapan koşuldur — gündüz kareleri düşük kontrastta okunmuyordu).

**Sayısal teyit:** 25 kadraj-içi parçacığın **hiçbiri** tüm-sayfa imzasını
taşımıyor. Yer gerçeği: disk/artı/üçgen delik=0.00, halka delik=0.41,
**tüm sayfa delik=0.12**. Ölçülen: hepsi ≤ 0.045, çoğu ≤ 0.02.
⚠ Bu sayım halkaları yakalayamaz (üst üste binen iki halka tek bileşene
düşer ve delikleri kapanır) — "farklı şekiller var" iddiası görselden,
"hiçbir parçacık tüm sayfayı çizmiyor" iddiası sayıdan okunur.

### ⛔ FLİPBOOK YOK — PARÇACIK DOĞDUĞU HÜCREYE KİLİTLENİYOR (ölçüldü)

Bölünme kanıtlandı (yukarıda) ama **animasyon yok**. Film şeridiyle
(tek kurulum, tek koşu, 1 sn aralıklı 8 kare, gece) aynı parçacık
**9. saniyeden 15. saniyeye** izlendi:

| iz | kare | delik oranı dizisi | aralık |
|---|---:|---|---|
| iz0 | 7 | 0.00 0.02 0.02 0.00 0.00 0.00 0.00 | 0.00-0.02 |
| iz1 | 5 | 0.00 0.02 0.03 0.02 0.01 | 0.00-0.03 |

Halka hücresi 0.41 verir. **Hiçbir iz oraya girmiyor.** Görselde de
(`flipbook_deney/AYNI_PARCACIK.png`) parçacık 6 saniye boyunca **üçgen**
kalıyor; büyüyüp soluyor ama şekil değişmiyor. `animRate` donörden
**0.8-2** olarak geldi (sıfır değil), yani 4 karelik döngü 2-5 sn sürmeliydi;
6 saniyede en az bir kez halkadan geçmesi gerekirdi. Geçmedi.

**Sonuç:** sayfa bir **çeşitlilik havuzu** gibi davranıyor — her parçacık
doğarken bir hücre seçiyor ve ömrü boyunca onu çiziyor. Bu şartlarda
"tek hücre göster, sırayla diğerlerine geç" görüntüsü **çok parçacıklı
bir plümde elde EDİLEMEZ**: her an farklı yaştaki parçacıklar farklı
hücreleri gösterir, kare karışık okunur.

**`animRate` SÜRÜLDÜ, DEĞİŞMEDİ (ölçüldü).** Donörün 0.8-2 değeri
elle **12**'ye çekildi (15 kat) — 4 karelik döngü saniyede birkaç kez
dönmeliydi. 6 saniyelik şeritte altı izin **hepsinde** delik aralığı
0.00-0.07; görselde (`d2_kareler.png`) üstteki halka hep halka, soldaki
üçgen hep üçgen, ortadaki artı hep artı kaldı.
**`UnknownC8` = 2** denendi (varsayılan 1) — dört izin hepsinde 0.00-0.04,
yine değişim yok.

⚠ Sınır: tek donör (`ent_amb_cig_smoke_linger`) ile ölçüldü; `UnknownCC`
ve `UnknownC0` denenmedi. Başka `animRate` / `UnknownC8` / `UnknownCC` kombinasyonu farklı
davranabilir — denenmedi.

### Çözüm: N emitter + `Unknown10` gecikmesi → `layered-effects.md`


### ⛔ ESKİ UYARI (geçerli): BÖLÜNME ≠ FLIPBOOK

Kanıtlanan şey **bölünme**: farklı parçacıklar farklı hücre çiziyor.
**Tek bir parçacığın ömrü boyunca hücreler arasında geçtiği
KANITLANMADI.** İki durum çok parçacıklı tek karede birebir aynı görünür:

- **(A)** parçacık doğarken bir hücre seçer, ömrü boyunca onu çizer
- **(B)** parçacık zaman içinde 0→1→2→… ilerler → GERÇEK FLIPBOOK

(A)/(B) ayrımı için **film şeridi** modu eklendi (`server.lua`, `kareler`):
kurulum BİR KEZ, aynı koşu içinde peş peşe kare. Eski `adim()` her karede
efekti baştan başlatıyordu; iki kare iki ayrı koşuya aitti. Bir şeritte
delik oranı 8 sn boyunca ~0.00 kaldı — **(A) yönünde eğilim** ama o koşuda
parçacıklar üst üste bindiği için belirleyici değil. **AÇIK SORU.**

### ⛔ ÖLÇÜM REÇETESİ — buna uymadan tekrar deneme

Bu sonuca varmadan önce altı tur boşa gitti; sebepleri:

1. **Kalibrasyon şart.** Parçacık boyutu `--boyut-olcek` (doku) ile adım
   `olcek`'inin (efekt) ÇARPIMIDIR. Ayrı ayrı tahmin edilirse ya kadrajı
   doldurur ya görünmez. **Önce tek varlık dağıtıp `olcek`'i süpür**
   (0.5/1/2/3) — yeniden derleme gerekmez. Ölçülen: `olcek=2.0` → 8 izole
   parçacık, çap ~130 px, hepsi kadraj içinde. Aranılan bu.
2. **Donör tipi.** `exp_grd_grenade_smoke` bir JET — parçacıklar yukarı
   fırlayıp kadrajdan çıkıyor. Yerinde duranı kullan:
   **`ent_amb_cig_smoke_linger`**.
3. **Kadraj kenarını ele.** `x<=2 || x>=1918` olan bileşen kırpılmış
   parçadır, çapı yanlış okunur (31×110 px "parçacık" çıktı).
4. **Yoğunluk iki kolda eşit olmalı.** Yoğun kol parçacıkları birleştirir
   (620 px bulut), seyrek kol kadrajdan taşar; karşılaştıracak izole
   parçacık kalmaz.
5. **Gece arka planı gündüzden İYİ.** Şekiller koyu zeminde okunuyor.
6. **HUD köşesini maskele** (`m[950:,1450:]=False`) — "Downloading assets"
   bildirimi en yoğun değişen bölge olarak çıkıp kadrajı oraya çekti.

Alternatif ayrım testi (`kanit_sayfa.py`): 2×2'de yalnız tek hücre dolu +
dördü dolu kontrol. Bölünüyorsa izole parçacık **çapı** eşit kalır
(sayı ~1/4'e düşer); bölünmüyorsa çap **yarıya** iner. Ölçülen oran
0.74× ve 1.07× — ikisi de ~1.0, yani bölünme yönünde (örnek sayısı azdı,
görsel kanıt asıl dayanaktır).

⛔ **BU BÖLÜM BİR KEZ FAZLA GÜVENLİ YAZILDI VE GERİ ALINDI.** İlk hâli
"sayfa dilimlemesi çalışıyor, ölçüldü" diyordu. Dayanağı ekran
görüntüleri üzerinden **yorumdu**: farklı parçacıkların farklı şekiller
gösterdiği izlenimi. Tek yorumu olan bir ölçüm **yapılamadı**.
§1e'yi de bu yüzden "geçersiz" ilan etmek erkendi.

**Durum:** §1b'nin `t1` satırı (vanilla kural + bizim 2×2 sayfamız = ✅)
ile §1e'nin "hiç çalışmıyor" hükmü birbirini tutmuyor. Hangisinin doğru
olduğu **hâlâ bilinmiyor**. Üretimde güvenli yol değişmedi: tek kare.

### Ölçülmeye çalışılan İKİ AYRI soru — karıştırma

1. **BÖLÜNME:** motor sayfayı hücrelere ayırıyor mu?
2. **FLIPBOOK:** tek bir parçacık ömrü boyunca hücreler arasında geçiyor mu?

⚠ (1) doğru olsa bile (2) doğru olmayabilir: her parçacık doğarken bir
hücre seçip ömrü boyunca onu çiziyor olabilir. Çok parçacıklı tek karede
iki durum **birebir aynı** görünür. **İkisi için de temiz ölçüm yok.**

### Kurulan alet (çalışıyor, kullanılabilir)

- **Film şeridi modu** (`server.lua`, `kareler` alanı): kurulum BİR KEZ,
  aynı koşu içinde peş peşe kare. Eski `adim()` her karede efekti baştan
  başlatıyordu; iki kare iki ayrı koşuya aitti, aynı parçacık izlenemiyordu.
  (2) sorusu ancak bununla cevaplanır.
- **Saat dondurma** (`SetMillisecondsPerGameMinute`): 15 sn'lik şerit
  boyunca GTA saati ilerleyip sahneyi geceye çevirdi; taban kare gündüz,
  ölçüm kareleri gece olunca fark aydınlatmaya boğuldu ve "en büyük
  bileşen" gökyüzü çıktı. Bir seri tamamen bu yüzden geçersizdi.
- **Ayrım sayfası** (`flipbook_deney/kanit_sayfa.py`): 2×2, yalnız tek
  hücre dolu + dördü dolu kontrol. Tek yorumu olan test bu:
  bölünüyorsa parçacık **boyutu** iki koşulda aynı kalır (sayı ~1/4'e
  düşer); bölünmüyorsa parçacık sayısı aynı kalır ama disk **yarı çapta**
  ve karenin sol-üst çeyreğinde durur.

### ⛔ NEDEN SONUÇ ALINAMADI — tekrar edilmesin

Ayrım testinin iki kolu **eşit yoğunlukta olmalı**. Dört-hücreli kol
(%7,9 parlaklık) parçacıkları birbirine karıştırdı (620 px birleşik bulut),
tek-hücreli kol (%0,49) ise kadrajın sağ kenarına taşıp yalnız kırpılmış
parça bıraktı (31×110 px, x=1904). **İki kolda da izole, tam görünür
parçacık gerekiyor**; önce düşük `--oran` ile yoğunluk eşitlenir, sonra
`--boyut-olcek` ve adım `olcek`'i **birlikte** ayarlanır (bu turda hep ters
yönde ayarlandı: biri büyütürken diğeri kadraj dışına attı).
Ölçüt: **izole parçacık çapı oranı** — ~1,0× bölünüyor, ~2,0× bölünmüyor.

⛔ **AŞAĞIDAKİ §1e GEÇERSİZDİR. Önce burayı oku.** §1e "dilimleme hiç
çalışmıyor, ızgara boyutu fark etmiyor" diyordu ve üretim yolunu tek kare
(`C4=0`) olarak koymuştu. Bu ölçümle çürütüldü. §1b'nin `t1` satırı
(vanilla kural + bizim 2×2 sayfamız = ✅) baştan doğruymuş; §1e onu
açıklamadan üzerine yazmış.

### Ne ölçüldü

Altı denek, transplant yoluyla kuruldu; sayfa **dama tahtası** (hücreler
sırayla dolu disk / ortası delik halka), DXT5 + mip, `RGBA_lit_soft`,
`FxcFileHash` dolu, hepsi geri okunarak denetlendi:

| denek | donör (kendi ızgarası) | yazılan `C4` | sayfa | sonuç |
|---|---|---:|---|---|
| b1 | `exp_grd_grenade_smoke` (2×2) | 3 | 2×2 | ✅ dilimliyor |
| b2 | aynı (2×2) | 15 | 4×4 | ✅ dilimliyor |
| **b3** | **aynı (2×2)** | **48** | **7×7** | **✅ dilimliyor** |
| b4 | `ent_amb_cig_smoke_linger` (7×7) | 48 | 7×7 | ✅ dilimliyor |
| b5 | 7×7 donör | 15 | 4×4 | ✅ dilimliyor |
| b6 | `ent_amb_bubble_stream` (5×5) | 24 | 5×5 | ✅ dilimliyor |

### ⛔ ÖNCE BUNU OKU: "DILIMLEME" ≠ "FLIPBOOK"

Aşağıdaki ölçümler **sayfanın bölündüğünü** kanıtlar: farklı parçacıklar
sayfanın farklı hücrelerini çiziyor. **Tek bir parçacığın ömrü boyunca
hücreler arasında GEÇTİĞİNİ KANITLAMAZ.** İki durum tek karede birebir
aynı görünür:

- **(A)** her parçacık doğarken bir hücre seçer, ömrü boyunca onu çizer
  → animasyon YOK, yalnızca çeşitlilik
- **(B)** her parçacık zaman içinde 0→1→2→... ilerler → GERÇEK FLIPBOOK

Ayrım ancak **tek kosu icinde, ayni parcacigi zaman icinde izleyerek**
yapılır. Tezgaha bunun icin `kareler` (film seridi) modu eklendi:
kurulum BIR KEZ, sonra verilen anlarda pes pese kare (`server.lua`).
⚠ Eski `adim()` her karede efekti BASTAN baslatiyordu; iki kare iki ayri
kosuya aitti ve ayni parcacik izlenemiyordu.

**2026-09-02 itibariyle (A) mi (B) mi oldugu HENUZ OLCULMEDI.** Tek
kullanilabilir serit (`ent_amb_cig_smoke_linger` donoru, 2x2, 8 sn
boyunca) delik oranini **hep ~0.00** gosterdi — parçacık halka hücresinden
geçseydi 0.41 olması gerekirdi, yani **(A) yonünde eğilim var** — ama o
koşuda birden fazla parçacık üst üste bindiği için belirleyici değil.
Tek-parçacık koşuları (`--oran 0.15-0.2`) okunamayacak kadar sönük çıktı.

⛔ **Bir sonraki oturum bu ayrımı çözmeden "flipbook çalışıyor" DEME.**
Gereken: tek parçacık (düşük `--oran`) + **okunacak kadar büyük ve parlak**
(`--boyut-olcek` ve adım `olcek` birlikte ayarlanır) + film şeridi +
donmus saat. Olcut: delik oraninin zaman icinde 0.00 ↔ 0.41 arasinda
SALINMASI.

⛔ **SAATİ DONDUR.** Film şeridi 15 sn sürünce GTA saati ilerleyip sahneyi
geceye çevirdi; taban kare gündüz, ölçüm kareleri gece oldu ve fark
aydınlatmaya boğuldu — "en büyük bileşen" gökyüzü çıktı, bir seri
tamamen bu yüzden geçersizdi. `SetMillisecondsPerGameMinute(2147483647)`
`kur` icine eklendi.

### ✅ SONUÇ (yalnız DILIMLEME icin): IZGARAYI `C4` SÜRÜYOR, DONÖR DEĞİL

`b3` belirleyici: **2×2 dokulu bir donörün `C4`'ü elle 48'e yazıldı ve
motor bizim 7×7 sayfamızı doğru dilimledi.** Yani:

- İzgara boyutunda **kural olarak bir kaynak kısıtı yok**; `C4 = kare − 1`
  yazılır ve sayfa o ızgarada bölünür.
- Donörün kendi dokusunun ızgarası **bağlayıcı değil**. Bu önemli, çünkü
  tek emitterli **4×4 donör YOKTUR**: `C4=15` taşıyan 8 kuralın hepsi
  2-4 emitterli efektlerde (ölçüldü). `C4` yazılabildiği için bu bir engel
  değil.
- Vanilla bandı tavanı hala **49 kare (7×7, `C4=48`)** — `C4>48` olan kural
  1, `C4>63` olan 0. 7×7 üstüne çıkma.

### ✅ ÜRETİM YOLU (§1e'nin "tek kare" reçetesi̇nin YERİNE)

1. Sayfayı üret, **`C4 = kare − 1`** yaz (2×2→3 · 4×4→15 · 5×5→24 · 7×7→48)
2. Donör **tek emitterli** olsun; `C4`'ü bizim sayfamıza göre **override et**
3. `FxcTechnique` **`RGBA_*`** olmalı (`RGB_*` alfayı yok sayar — §1b)
4. Doku **DXT5 + mip**, boyut 2'nin kuvveti; hücre 128-192 px hedefle
5. `ypt_xml_to_bin.ps1` ile derle (hash), geri okuyup `C4`+teknik+boyut denetle

### ⛔ AYAKTA KALAN KISIM: SIFIRDAN YAZILAN KURAL

§1b'nin `t2..t5` satırları hala geçerli: **kendi üretecimizin sıfırdan
yazdığı kural blokları ızgarayı uygulatmıyor** (2×2 dahil). Sorumlu alan
hâlâ bulunmadı. Doğru cümle "flipbook GTA'da çalışmıyor" DEĞİL,
"**sıfırdan kural yazıcımız çalışmıyor, transplant çalışıyor**".

### ⛔ ÖLÇÜM YÖNTEMİ — tezgahta ÜÇ hata düzeltildi, üçü de SESSİZDİ

Bu turda "efekt çıkmıyor" diye iki kez yanlış teşhis kondu. Her seferinde
**referans adımı** (oyunun kendi efekti) da boş çıktığı için kusurun bizim
varlığımızda olmadığı anlaşıldı. **Referans adımı olmadan ölçüm yapma.**

1. `baslat()` verilen varlığı yok sayıp sabit `VARLIK` haritasına bakıyordu;
   harita yalnız 15 aile kataloğunu tanıyor → yeni varlık **hiç doğmadı**.
   Düzeltildi: verilen varlık kullanılır + `RequestNamedPtfxAsset` ile istenir.
2. Hedef sabit dünya ekseninde (`k.y + mesafe`) konuyordu → ped başka yöne
   bakıyorsa efekt kadraj dışına düşüyor. Hedef **ileri vektöründe** olmalı.
3. Kamera pedin arkasındaydı → hedef ileri vektöründe olunca **ped efekti
   kapatıyor**. Kamera efektin **yanına** konur.

⛔ **ADIMLAR ARASI BULAŞMA GERÇEK.** Önceki adımın yaşayan parçacıkları
sonraki karede duruyor; renk bazlı atama da güvenilir değil (ton normalizasyonu
farklı renkleri birbirine katıyor). **Kesin okuma için her denek TEK BAŞINA
çekilir.** b3'ün yukarıdaki hükmü tek-denek karesinden okundu (renk farkı
R−38 G−9 B+63 ile doğrulanarak).

**Okuma ölçütü (her ızgarada çalışır):** dama tahtası sayfa → dilimleme
varsa parçacıkların bir kısmı **deliksiz** (disk), bir kısmı **delikli**
(halka, ~0.41). Dilimleme yoksa HER parçacık halka hücrelerini de içerir →
deliksiz parçacık **olamaz** ve delik oranı sabit ~0.20 çıkar.
⚠ Bu istatistik 7×7'de zayıflar (hücre ekranda küçülür, delik JPEG'de
kaybolur) — orada **görsel okuma** şarttir, ama tek-denek karesinde.

Deney betikleri depoda değil (tek seferlik ölçüm).

---


## 2. ⛔ SON KARE BOŞ ÇIKAR — 15 ailenin 15'inde oldu

Aile üreticileri `t = i / (n - 1)` hesaplar. `n = kare` geçilirse son kare
`t = 1.0` olur ve her ailedeki `(1 - t) ** k` sönme çarpanı **tam sıfır**
verir. `Unknown_C4h = kare − 1` motora o kareyi de çizdirir → efekt her
döngüde bir kare **yanıp söner**.

**Çözüm:** `fn(i, kare + 1, ...)` — son kare `t = 48/49 = 0.980` olur,
sönme tamamlanır ama boşalmaz.

Bu **tek başına yetmez**: sönme çarpanı düzeltildikten sonra bile 4 ailede
boş kare kaldı, sebebi ailenin **kendi zarfıydı**:

| aile | boş kare | sebep |
|---|---|---|
| `halka` | kuyruk | halka kadrajı terk ediyor |
| `sis` | **baş** (7 kare) | zarf `t=0.5`'te tepe, iki yana sönüyor |
| `kabarcik` | kare 0 | ilk kabarcık gecikmeyle başlıyor |
| `toz` | **kare 11 (ortada)** | üreticinin kare düşürmesi |

Yani hem baş hem kuyruk hem **orta** boş olabilir; üçü ayrı sebep.

### Üç kademeli kapı (`sayfa()` içinde, hepsi tek yerde)

1. **`kare + 1`** — sönme çarpanının sıfırlanmasını engeller.
2. **Aralık daraltma, DÖNGÜLÜ.** Ölçülen ilk/son dolu kareye göre `t`
   aralığı `[t0, t1]`'e oturtulur. ⛔ **Tek geçiş yakınsamaz** — daraltma
   yeni sınır karelerini gene sıfıra düşürebilir (ölçüldü: `halka` bir
   geçişle 1 boş kareden 1 boş kareye gitti, `sis` 7'den 2'ye indi ama
   sıfırlanmadı). En fazla 6 tur, her turda %2 içe itilir.
   Aralık kayması `n` ve `ofs` ile kurulur:
   `(n-1) = (kare-1)/(t1-t0)` ve `ofs = t0*(n-1)`; **`ofs` tam sayı
   yuvarlanır** çünkü bazı aileler `i`'yi rastgelelik tohumunda da
   kullanır (`_rng(2600 + i*3)`).
3. **Komşu harmanı.** Kalan her boş kare, en yakın dolu komşularından
   doğrusal harmanla doldurulur. Ortadaki boşluğa dokunan tek kademe budur.
   Kaç kare doldurulduğu **bildirilir** — yama görseldir, sebebi gizlemez.

### ⛔ Ölçüm, GÖNDERİLEN veri üzerinde yapılır

İki tur boşa gitti: kapı alfayı **float** olarak ölçüyordu. 0.0201 değeri
"dolu" sayıldı; ama `yaz()` uint8'e yuvarlıyor (0.0201 → 5 → 0.0196) ve
gönderilen kare eşiğin **altına** düşüyordu. `duman` son kare ve `sis`
kare 0 kapıdan geçti, PNG'de tamamen boş çıktı.

```python
q = np.floor(np.clip(alfa, 0, 1) * 255.0 + 0.5) / 255.0
return float((q > 0.02).mean())
```

Genel kural: **niceleme varsa kapı nicemlenmiş değere bakar.**

---

## 3. ⛔ Kare, hücre kenarına DEĞMEMELİ

Flipbook karesi hücre kenarına değerse oyunda sprite quad'ın sınırında
**sert kesik** görünür; vanilla sayfalarda kareler saydam çerçeve içindedir.

Ölçüldü: `ates` kenara **0.44** alfayla değiyordu, `duman`/`kivilcim`
**0.00** ile temizdi. İlk elle kontrolüm yalnız 3 aileye ve 9 kareye
baktığı için 4 aileyi kaçırdı; otomatik kapı hepsini yakaladı:
`kor` 0.43 · `kabarcik` 0.67 · `parca` 0.42 · `elektrik` **0.98**.

İki katmanlı:
- `sayfa()` her kareye **smoothstep kenar maskesi** uygular (%4.5 pay).
- Maske **gizlemez**: ham taşma 0.35'i aşarsa uyarı basar, çünkü o kadar
  taşan içerik hücreye sığmıyordur ve maske onu **kırpar** (efekt seyrelir).

**Menzil, yarıçapı hesaba katmalı.** Tanenin merkezi hücre içinde kalsa
bile yarıçapı kadarı dışarı taşar. Serbest yürüyen içerik (elektrik arkı)
doğrudan **kelepçelenir** (`0.12..0.88`).

---

## 4. ⛔ rng GEÇİŞ BAŞINA TEK olmalı

Kare başına yeni bir `_rng(tohum)` yaratmak her kareye **aynı** rastgele
diziyi verir; kareler birbirinin aynı çıkar (durgun sprite) ve hata
vermez. Aralık daraltma iki geçişli olduğu için bu tuzağa girmek kolaydır.

---

## 5. Aile tasarımı — ölçülmüş üç ders

### Fazı normalize etme, AKIŞ kur
`kabarcik`'in ilk sürümünde her kabarcığın fazı
`tk = (t - gecikme) / (1 - gecikme)` ile normalize ediliyordu → gecikmeli
başlasalar da **hepsi aynı anda varıyordu**. Son karelerde üç kabarcık yan
yana aynı yükseklikteydi; "yükselen kabarcık" değil "üç halka" gibi
okunuyordu. Doğrusu sürekli akış: `tk = (t + k/N) % 1.0`. Yan kazanç —
sayfa kendiliğinden kusursuz döngüye girer.

### Rengi kanal kanal kurma
`alev_topu`'nda R/G/B ayrı formüllerle yazıldı; kanallar farklı hızlarda
sönünce çekirdek önce sönük turuncu, sonra **yeşilimsi** çıktı. Kanal
kesişmesi sessizce renk uydurur. Doğrusu tek bir **sıcaklık alanı** kurup
sabit renkler arasında interpolasyon: `duman → ateş → beyaz`.

### Doğru renk tek başına yetmez — ALFA da çekirdekte olmalı
Renk düzeltildikten **sonra** bile çekirdek gri görünüyordu: oradaki alfa
~0.34'tü ve arka plan içinden geçiyordu; kenarda loblar üst üste bindiği
için alfa yüksekti → **"gri merkez, turuncu halka"**. Patlamanın merkezi
en opak yeridir.

### Bir efekt başka bir efektin renkli hali DEĞİLDİR
`k_ates` başlangıçta `k_duman(sicak=True)` çağırıyordu ve ateşe hiç
benzemiyordu. Dumanı tanımlayan şey dağılma, ateşi tanımlayan şey **yukarı
yükselen dillerdir**. Aynı şekilde `sis` ilk hâlinde `buhar`ın aynısıydı;
sisi ayıran şey **geniş ve alçak** olması, buharı ayıran şey **yukarı
uzayan tutamlardır**.

---
