# Dağıtım ve oyunda ölçüm — tezgâh, rcon, `PtFxAssetStore`, "bozuk görünüyor"

**Ne zaman okunur:** `.ypt`'yi sunucuya koyacaksın, oyunda test edeceksin, "efekt bozuk/görünmüyor" diyorsun, oyun donuyor.
**When to read:** shipping a `.ypt` and measuring it in game — test bench, rcon, `PtFxAssetStore` pool, "it looks wrong" is not a measurement.
**Kaynak:** `ptfx-flipbook-uretimi.md` §1c, §7, §16-18 (2026-09) · **Ölçüm:** tezgâh piksel ölçümü; `PtFxAssetStore` 400; tek büyük `.ypt` donma eşiği
**Önce:** `dallar/particle/_dal.md` · gövde › `govde/arac-tuzaklari.md` §3 CodeWalker (`FxcFileHash`, `VFT`, `ResourcePointerArray64`) · araçlar `ptfx_tezgah.py`, `ptfx_sim.py` (motor değil, model)

---

## 1c. Teşhis yöntemi — bu turda pahalıya öğrenilenler

### ⛔ REFERANSSIZ GÖRÜNTÜDEN TEŞHİS KONMAZ

Beş tur boyunca ekranda neyin **normal** olduğunu bilmeden "bozuk" denildi.
Karşılaştırma noktası olmadan bir partikülün doğru mu yanlış mı çizildiği
gözle ayırt edilemez — özellikle gece, saydam ve büyük ölçekte. Teste
**oyunun kendi efektini** aynı karede referans olarak koy:

```lua
UseParticleFxAssetNextCall('core')
StartParticleFxLoopedAtCoord('exp_grd_grenade_smoke', ...)
```

Yan yana: referans · bizim dosya + vanilla doku · bizim dosya + bizim doku.
Tek değişken doku kaynağı olur.

Ek okunabilirlik şartları (hepsi ihlal edildi): gündüz (`NetworkOverrideClockTime`),
küçük ölçek (`--boyut-carpan 0.30`), aralarında ≥4 m, konumu değil **rengi**
etiket yap.

### ✅ TEZGÂH — testi kullanıcıdan al, ölçüme bağla

Beş tur "kullanıcıyı oyuna sok → ekran görüntüsü iste → görüntüyü yorumla"
döngüsünde kayboldu ve yorum katmanı üç kez yanlış teşhis üretti. Kalıcı
çözüm o katmanı kaldırmaktır.

`screenshot-basic` çoğu sunucuda zaten kuruludur ve **sunucudan**
sürülebilir:

```lua
exports['screenshot-basic']:requestClientScreenshot(src,
    { fileName = 'cache/my_ptfx/x.jpg', encoding = 'jpg', quality = 0.85 },
    function(err, dosya) ... end)
```

Kurulum: kaynak `is/istek.json` dosyasını 1 sn'de bir yoklar; dışarıdan
yazılan iş için istemciyi kurar (efekt + **sabit kamera**), bekler, ekran
görüntüsü alır, `is/sonuc.json` yazar. Sürücü ve ölçüm:
`scripts/ptfx_tezgah.py`.

- **Kamera her adımda aynı noktaya, aynı yönle kurulur.** Elle çekilen
  karelerde mesafe/açı değiştiği için iki efekt kıyaslanamıyordu.
- Sahne koşulları sabitlenir: `NetworkOverrideClockTime(12,0,0)`,
  `SetWeatherTypeNowPersist('EXTRASUNNY')`, ped dondurulur.

**Ölçüt numaralı tanı sayfasıdır**: her hücreye kocaman numarası yazılır.
Bağlantılı bileşen sayısı iki durumu kesin ayırır (ölçüldü):
sayfanın tamamı → **89 bileşen**, tek hücre → **1 bileşen**.

⛔ **`screenshot-basic`'e `fileName` VERME.** Dosyaya yazmaya çalışırsa
FiveM'in dosya kapısına takılır: *"Access to this API has been restricted.
Use --allow-fs-write"*. `fileName`'siz çağrıda base64 veri URI'si döner;
onu kendi kaynağımıza `SaveResourceFile` ile yazarız — o bir native,
node'un fs kapısına tabi değil.

⛔ **`StopParticleFxLooped(h, false)` EFEKTİ HEMEN KALDIRMAZ.** Emisyonu
durdurur ama yaşayan parçacıklar ömürleri bitene kadar ekranda kalır ve
**bir sonraki ölçüme bulaşır** (ölçüldü: 4 sn ömürlü adımın numaraları
sonraki karede okundu, yanlış teşhis kondu). `true` ver, üstüne
`RemoveParticleFx(h, true)` çağır, ve adımlar arasında bekle.

⛔ **Kamerayı sabit bir dünya yönüne koyma.** Efekt oyuncunun ileri
vektörü boyunca duruyorsa, kamerayı `hedef.y - 3.2` gibi sabit bir eksene
koymak onu **pedin içinde** bırakır; karede yalnız sırt çantası görünür.
Kamera oyuncunun göz hizasından hedefe bakmalı.

⛔ **Çerçeveleme efekti KÜÇÜLTEREK yapılmaz, kamerayı GERİ ÇEKEREK yapılır.**
Efekt küçültülünce tamamen görünmez oldu (değişen piksel %0,6).

⛔ **Sınır:** ekran görüntüsü istemcinin render'ıdır; oyuncunun bağlı
olması şarttır. Ve stream dosyası değiştiyse **yeniden bağlanmak**
gerekir — `restart` yetmez. Tezgâh yalnız zaten dağıtılmış varlığı ölçer.

### ⛔ ETİKETİ EKRANA YAZ — konum da renk de güvenilmez

Kutuları önce **konumdan**, sonra **renkten** eşleştirmeye çalışıldı; ikisi
de yanlış okumaya yol açtı. Renk turunda dosyalara doğru RGB'nin yazıldığı
ölçümle doğrulandı (dördü de birebir istenen değerde) ama ekran
görüntüsünde "mavi kutu" hiç bulunamadı — yani doğru veriyle bile
eşleştirme yapılamadı.

Çözüm: her efektin üstüne `DrawText3D` ile **adını yaz**. Ekran
görüntüsünün kendisi hangi kutunun ne olduğunu söylemeli; yorum payı
bırakma. `SetDrawOrigin(x,y,z,0)` + `DrawText(0,0)` + `ClearDrawOrigin()`.

### ⛔ VANILLA EFEKTİ REFERANS OLARAK ÇAĞIRMAK BEDAVA

`UseParticleFxAssetNextCall('core')` + oyunun kendi efekt adı — dosya
göndermeden, garantili doğru bir karşılaştırma noktası. Her görsel teste
bunu koy.

### ⛔ TESTİN KENDİSİNİ DE DENETLE — ölçek iki kez uygulandı

Referanslı test kurulduktan sonra bile sonuç yanıltıcı çıktı: denekler
referanstan çok daha küçük göründü ve "noktalar kümesi" gibi okundu.
Sebep bulguda değil **testin tasarımındaydı** — küçültme iki kez
uygulanmıştı: dosyaya `--boyut-carpan 0.30` pişirildi, üstüne Lua'da
`StartParticleFxLoopedAtCoord(..., 0.35)` verildi. Referans yalnız
0.35 aldı, denekler 0.30 × 0.35. Yani denekler referansın **0.3 katıydı**
ve 0.3 katına inmiş bir duman bulutu doğal olarak küçük noktalar gibi görünür.

**Kural: karşılaştırmalı testte her yol aynı dönüşümlerden geçmeli.**
Deneği hazırlarken uygulanan her ölçek/renk değişikliği referansa da
uygulanmalı, ya da hiçbirine uygulanmamalı. Test öncesi bunu **ölçerek**
doğrula: kural bloğunu vanilla ile metin düzeyinde karşılaştır —
`Size`/`Colour`/`AnimateTexture`/`Velocity` blokları bayt bayt eşit olmalı,
tüm dosyadaki tek fark isimler kadar (bu vakada 27 bayt) kalmalı.

### ⛔ "Bozuk görünüyor" bir ölçüm değildir — kafesi SAY

Ekran görüntüsünden şüphelenilen bir örüntü FFT / otokorelasyon ile ölçülür.
Ölçüldü: bloğun içinde ~7 tekrar (bizim ızgaramız 7×7), periyot 20 px.
Ama hücreler **birbiriyle korelasyonsuz** (+0.002) çıktı; bizim sayfamızın
hücreleri ise birbirine benziyor (+0.791). Yani gördüğümüz şey ne
"sayfanın tamamı" ne de "tek hücrenin tekrarı"ydı — gözle konan iki teşhis
de yanlıştı.

### Elenen alanlar — ham bayt düzeyinde

`AnimateTexture` bloğu (208 bayt) vanilla ile **birebir aynı**: 208 baytın
yalnız 7'si farklı ve ikisi de işaretçidir (0x10 ve 0xA0, keyframe
adresleri). CodeWalker hiçbir baytı gizlemiyor — XML turu yalnız VFT
işaretçilerini değiştiriyor, davranışların tek bir alanı bile kaymıyor.
Doku metadata'sı da aynı (`UsageFlags`, `UsageData`, `Unknown_32h`).

**Sonuç: dosyanın içinde aranacak yer kalmadı.**

### ✅ KAPANDI — custom `.ypt` MOTORDA VANİLLA GİBİ İŞLENİYOR

Referanslı, eşit ölçekli, gündüz kurulan testte oyunun kendi efekti ile
bizim `.ypt`'miz (aynı kural, vanilla doku) ve bizim `.ypt`+bizim sayfamız
**ayırt edilemedi**. Yani stream yolu, kural kopyalama, doku gömme ve sayfa
animasyonu sağlam.

⚠ Bu, önceki turlarda konulan "dosya bozuk / motor ızgarayı uygulamıyor"
teşhislerini **geçersiz kılar**; o testlerin hepsi karıştırılmıştı
(çift ölçek, referanssız okuma, gece, etiketsiz kutular).

### ⛔ `rm my_t*` DENEK SİLERKEN ÜRETİMİ DE SİLER

`my_t1..t5` deneklerini temizleyen glob `my_toz.ypt`'yi de yakaladı ve
dosya sessizce kayboldu. Dağıtımdan sonra **Lua'nın andığı her varlık adını
stream içeriğiyle karşılaştır** — bu kapı olmasa oyunda "bir efekt eksik"
diye tur kaybedilecekti.

---

## 7. Dağıtım — stream ve komutlar AYRI kaynakta

⛔ **Bozuk bir stream varlığı kaynağın TAMAMINI sessizce düşürür**:
sunucu `Started resource X` yazar, istemcide hiçbir komut kaydolmaz,
hiçbir print çıkmaz, F8'de hata yoktur.

Bu yüzden `.ypt` dosyaları `my_ptfx/stream/` içinde (Lua yok), test
komutları `my_ptfx_test/` içinde (stream yok). Komut çalışıp efekt
gelmiyorsa kusur stream'dedir; komut hiç yoksa kusur Lua'dadır.

`ensure [script]` klasörün tamamını başlatır — cfg'ye satır eklemek
gerekmez.

Kopyadan sonra **hash karşılaştır**; "komut hata vermedi" dağıtım kanıtı
değildir.

### Lua tarafı
- `RequestNamedPtfxAsset(ad)` + `HasNamedPtfxAssetLoaded(ad)` beklenir
  (zaman aşımı koy).
- `UseParticleFxAssetNextCall(ad)` **her** `StartParticleFx...` çağrısından
  önce yenilenir.
- Handle 0 dönerse **varlık yüklendi ama efekt kuralı adı bulunamadı**
  demektir — ikisini ayrı raporla.
- ⛔ `GetEntityRightVector` **standart bir native değildir**;
  `GetEntityMatrix` sarmalayıcısında dönüş sırası belirsizdir. Sağ vektörü
  ileriden türet: `sag = (ileri.y, -ileri.x)`.

### ⛔ VARLIK ADINDA BÜYÜK HARF OLMAZ

`my_gA` adıyla üretilen varlık **yükleniyor** ama
`StartParticleFxLoopedAtCoord` **handle 0** döndürüyor: "efekt kuralı
bulunamadı". GTA ad hash'lerini küçük harfe çevirerek hesaplar;
`RequestNamedPtfxAsset` geçer, içerideki efekt kuralının hash'i tutmaz.
Belirti yanıltıcı — varlık yüklü görünür, efekt yoktur.
**Tüm varlık/efekt/doku adları küçük harf.**

### ⛔ STREAM'E YENİ DOSYA EKLEMEK ÜÇ ADIMDIR

1. dosyayı `stream/` içine kopyala
2. **`restart <kaynak>`** — sunucu stream listesini yeniden kurar
3. istemciyi yeniden **bağla**

2. adım atlanınca istemci varlığı hiç bulamaz (`varlik YUKLENMEDI`) ve
ekranda hiçbir şey çıkmaz. Hata yalnız **istemci** günlüğünde görünür;
sunucu konsolunda iz yoktur. Var olan dosyayı *değiştirmek* manifesti
değiştirmez, ama dosya *eklemek* değiştirir.

### ⛔ İSTEMCİYİ ÖLDÜRMEK HAYALET OTURUM BIRAKIR

Süreci zorla kapatınca sunucu oyuncuyu hâlâ bağlı sayar ve yeniden
bağlanma **"Duplicate Rockstar License Found"** ile reddedilir.
RCON'da `clientkick` de `drop` da **yoktur** ("No such command"); oturum
kendi zaman aşımıyla düşer. Çözüm: öldürdükten sonra ~25 sn bekle.

### ⛔ `while read` DÖNGÜSÜNDE powershell STDIN'İ YUTAR

Döngü gövdesinde `powershell`/`python` çağırmak kalan satırları tüketir ve
döngü satır atlar. Ölçüldü: 15 aileden 5'i yanlış değerlerle kuruldu ve
sebebi ancak geri okumayla görüldü. Ayrı dosya tanıtıcısı kullan:
`while read ... <&3; do ... </dev/null; done 3< dosya.txt`

### ⛔ FiveM PROTOKOLÜ KABUKTAN ÇAĞRILIR

`FiveM.exe fivem://connect/...` doğrudan başlatılırsa
*"This application should be launched directly from the shell or a web
browser"* ile çöker. Çağrı kabuktan gelmeli:
`Start-Process 'explorer.exe' -ArgumentList 'fivem://connect/<ip>'`

### ⛔ Asset değişince sunucudan ÇIKIP YENİDEN BAĞLAN
FiveM stream dosyalarını cache'ler; `restart` yetmez.

---

## 16. ⛔ TÜRKÇE KESME İŞARETİ LUA STRING'İNİ KAPATIR — `lua_check` KAÇIRIR

Yazılan satır:

```lua
print('^2[x]^7 hazir - /ptfxkat <n> (8'er)  /ptfxall')
```

`8'er`'deki kesme string'i kapatıyor. FiveM'in verdiği hata
`')' expected near 'er'` ve sonucu şu: **kaynağın TAMAMI yüklenmiyor.**
Hiçbir komut kaydolmuyor. Oyunda belirti "Lua hatası" gibi değil,
*"komut yok"* gibi görünüyor — kullanıcı `/ptfx` yazınca yalnızca
başka bir kaynağın komutu çıktı.

⛔ **`lua_check` (lua-language-server) bunu "No diagnostics" dedi.**
   Tek denetim olarak ona güvenme. Doğrulanmış ikinci kapı:
   `python lua_sozdizim.py <dosya.lua>` — Lua'nın string/yorum
   kurallarını gerçekten izler (`'`/`"`, `\` kaçışı, `--` satır yorumu,
   `[[ ]]` ve `[==[ ]==]` uzun blok). Hatalı satırı yakaladığı, doğrusunu
   geçirdiği ölçülerek doğrulandı.

**Kural:** Türkçe metinde kesme varsa **çift tırnak** kullan
(`"8'er"`), ya da kesmeyi hiç yazma.

Kapsam notu: bu betik string/yorum dengesine bakar. `<eof> expected
near 'end'` gibi YAPISAL hataları (fazla/eksik `end`) yakalamaz — onun
için `lua_check` hâlâ gerekli. İkisi birbirini tamamlar, biri ötekinin
yerine geçmez.

## 17. `/ptfxkat` donması — veri değil OVERDRAW

Belirti: `Window Watchdog: FiveM has stopped responding`, crash dump'ta
`Is Out of memory : No`. Logda **tek bir ptfx hatası yok**, varlık
`Mounted my_ptfx` ile sorunsuz yükleniyor.

Ölçüldü: 56 efekti birden açmak **1784 eş zamanlı parçacık** demek.
Üstüne Kenney dokularının alfa kaplaması **%40-70** (eski prosedürel
dokular %2-30'du) — yani parçacık sayısı aynı kalsa bile doldurma
maliyeti birkaç kat arttı. VFXDoc'un *"alpha coverage is one of the most
underestimated sources of performance"* uyarısı tam olarak bu.

En ağır beş aile: `cokme_tozu` 244 · `duvar_cokme` 215 ·
`su_patlamasi` 100 · `radyoaktif_sis` 88 · `yakit_varili` 72.

**Ders:** toplu gösterim komutu varsayılan olarak SAYFA açmalı.
`/ptfxkat` 8'erlik sayfa, `/ptfxsira` tek tek gezinme; hepsini birden
açan yol (`/ptfxkat hep`) uyarı basar.


## 18. ⛔ TEK BÜYÜK `.ypt` OYUNU DONDURUR — ölçülmüş eşik

§12 "havuz dosya sayar, hepsini tek dosyada birleştir" diyordu. **Bu tek
başına yanlış yönlendirir:** birleştirmenin bir ÜST sınırı var.

Ölçüldü (ikiye bölerek, oyunda):

| dosya | efekt | boyut | sonuç |
|---|---|---|---|
| `my_mini2` | 2 | 0.06 MB | **yüklendi** |
| `my_mini16` | 16 | 0.39 MB | **yüklendi** |
| `my_efektler` | 71 | 1.88 MB | **DONDURDU** |

Eşik 16 ile 71 arasında. Üretim 18'erlik dört parçaya bölündü.

### Teşhis nasıl yapıldı — her adımı yanlış çıkan üç tahmin

1. **"Boyut"** → 6.56 MB'ı 256×256 dokularla 1.88 MB'a indirdim, **aynı
   şekilde dondu**. Boyut değil, ÖĞE SAYISI.
2. **"`Wait` komut callback'inde"** → doğru bir kusurdu (aşağıda) ama
   düzeltince de dondu. Tek sebep o değildi.
3. **"3B etiket çizimi"** → kapatıldı, yine dondu.

Kesin cevabı ancak **harness'ı kanıt üretecek hale getirince** aldım:
bloklamayan yükleme + her adımda log. Log şunu gösterdi —

```
[t1] baslangic ✓  su an yuklu mu: false ✓  varlik isteniyor ✓
[t1] komut bitti (beklemedi) ✓     <- Lua sonuna kadar çalıştı
                                    <- 46 sn sonra
Window Watchdog: FiveM has stopped responding
```

`varlik HAZIR` hiç basılmadı → donma `RequestNamedPtfxAsset` **sonrası**,
GTA varlığı stream ederken. Lua tamamen aklandı.

⛔ **Ders: "donuyor" demekle "nerede donuyor" arasındaki farkı kod
üretmeli.** Üç turu adım logu olmadan tahminle harcadım.

### ⛔ `Wait()` COMMAND CALLBACK'İNDE ÇAĞRILAMAZ

`RegisterCommand` geri çağrısı coroutine içinde çalışmaz; içinden
`Wait(0)` çağırmak ana iş parçacığını kilitler. Belirti çok yanıltıcı:
**tek satır print bile basılmaz**, komut hiç çalışmamış gibi görünür.

Bu kusur baştan beri koddaydı ama hiç tetiklenmemişti: varlık zaten
yüklüyken `HasNamedPtfxAssetLoaded` erken dönüyor, döngüye girilmiyor,
`Wait` hiç çağrılmıyordu. Tek büyük varlığa geçince ilk kez tetiklendi.

Çözüm: gövdeyi `CreateThread` içine alan bir kaydedici
(`komut(ad, fn)`), ve daha iyisi — **bloklayan beklemeyi tamamen
kaldırmak**: istek bir kez gönderilir, kalıcı gözcü thread durumu izler,
hazır olunca bekleyen iş çalışır.

### Bölünmüş varlıkta ad haritası ŞART

`UseParticleFxAssetNextCall` efektin **bulunduğu** varlığı ister; yanlış
varlık verilirse `handle 0` döner ve hiçbir hata çıkmaz. Efekt adı →
varlık adı haritası üretilip Lua'ya gömülür.

### Doku çözünürlüğü (bu turda yine de kazanç)

Vanilla `core.ypt`in en yaygın doku boyutu **256×256** (107 dokunun 33'ü).
512 kullandığı yerler **16-49 karelik sayfalar** — kare başına ~73 piksel.
Tek kare sprite için 512 fazladır: 71 doku 23.7 MB'dan **5.9 MB**'a indi.
