# GTA V movement clipset üretimi — ölçülmüş reçete ve hata kataloğu

Kapsam: Blender/Sollumz ile üretilip FiveM `stream/` üzerinden vanilla bir
movement clipset sözlüğünün (`move_m@brave` gibi) yerine konan `.ycd`.

Bu belgedeki her sayı **ölçümdür**. Kaynak korpus: 12+ vanilla movement clipset
sözlüğü, 686 klip / 247 animasyon, artı çalışan bir topluluk modu
(FiveMCombatOverhaul, 138 animasyon). Doğrulanmış bulgu sayısı 79.

---

## 0. Önce şunu bil: belirti → sebep tablosu

Bu iş boyunca gözlenen **her** belirti ve gerçek sebebi:

| Belirti | Gerçek sebep |
|---|---|
| Ped aralıklarla **bind/T-poza** düşüyor, klip oynamıyor | Klibin kemik kapsamı eksik (Sollumz tek animasyona yalnız gövde kanallarını yazar, 32 parmak/ayakbaşparmağı kanalını hiç yazmaz → kapsanmayan kemik önceki pozunda kalır). Çözüm: `AnimationList` + 2 animasyon ile **aynı adlı vanilla klibinin** kemik sayısına tamamla (`clips.tsv.gz`'den oku — sözlük başına sabit sayı yoktur) |
| Klip oynuyor ama ped **yerinde sayıyor** | Mover yönü ters (`−Track5` + birim `Track6` = "geri yürü") |
| Yalnızca **maksimum yürüme hızında** takılıyor | Eşik değil: minimal clipset'te `wstart_*`/`sprint` yok, ped sadece MBR 1.0'da senin verine kalır |
| Ayaklar yerden **birkaç cm yukarıda**, parmak ucunda duruyor | `IK_L_Foot`/`IK_R_Foot` `Track 0` kanalları yok + kök yüksekliği kalibre değil |
| Gövde ilerleme yönüne **tam hizalanmıyor** (±15°) | `SKEL_Pelvis` / `SKEL_Spine_Root` `Track 1` pimlemesi yok |
| Koşarken ayaklar **kayıyor / hiç basmıyor** | Klip kadansı ile mover hızı uyumsuz (adım mesafesi yanlış) |
| Her döngüde **tek karelik takılma** | Döngü kapanış karesi klip penceresinin İÇİNDE |
| Animasyon **hiç oynamıyor**, hata da yok | Klip `<Hash>` boş ya da klip→animasyon bağı yanlış |
| **Hızlanırken/yavaşlarken** poz kayboluyor, sonra geri geliyor | `wstart_*`/`wstop_*` senin clipset'inde yok, fallback'ten (vanilla) geliyor |
| Bir kez ileri tuşuna basınca **ped durmadan yürüyor** | `SetPedMinMoveBlendRatio(ped, 1.0)` — MBR pozu değil HAREKETİ de zorlar |
| Ped sabit birkaç cm **havada** duruyor | Zemin referansı kemik alınmış; gerçek zemin ayakkabı mesh'inin en alçak vertex'i |
| Bir bacak diğerinden **daha düz açılıyor**, diz "pat" ediyor | Retarget hiperekstansiyonu; diz aralığı diğer bacağa sıkıştırılmalı |
| Diz düzeltmesinden sonra **bacaklar birbirine dolanıyor** | Menteşe ekseni `u×v` ile her karede hesaplanmış; diz düzken çarpım dejenere |

---

## 1. DOĞRU YOL — uçtan uca üretim hattı

### 1.1 Blender tarafı

```
CS_idle / CS_walk / CS_run   (tek döngü, 30 fps)
   ↓ döşe (tile)             → animasyon penceresinden UZUN olmalı
   ↓ mover yaz               → Track 5 = +Y doğrusal rampa, Track 6 = birim
   ↓ zemin kalibrasyonu      → en alçak ayak = rest pozunun en alçak ayağı
```

**Döşeme kuralı.** Klip penceresi tam sayı döngü olmalı, animasyon pencereden
uzun. Vanilla `move_m@brave`: idle 7.37 s, walk 6.37 s, run 4.07 s.

**Mover.** Kümülatif konum, doğrusal rampa yeterli:

| klip | mover hızı (ölçülen vanilla) |
|---|---|
| `idle` / `idle_intro` | 0.00 m/s |
| `walk` | **+1.736 m/s** |
| `run` | **+5.128 m/s** |
| `sprint` | +7.059 m/s (`move_m@generic`) |

`z` bileşeni sabit **1.0**. `Track 6` birim quaternion.

**Kadans ↔ mover eşleşmesi.** Adım mesafesi = mover hızı ÷ adım frekansı.
Vanilla: walk ~1.74/2.0 = 0.87 m, run ~5.13/3.44 = **1.50 m**. Klibinin kadansı
uymuyorsa animasyonu **zamanda yeniden örnekle** (aşağıda §2.7).

**Zemin kalibrasyonu.** Rest pozundaki en alçak ayak noktası zemin düzlemidir.
Her klipte en alçak `SKEL_L/R_Toe0`/`Foot` bu değere gelene kadar
`SKEL_ROOT.location.z`'yi kaydır.

### 1.1b Clipset TANIMI — sözlüğe klip eklemek YETMEZ

**Ölçüldü ve iki kez yanlış varsayıldı.** `clip_sets.ymt` içinde her clipset
şöyle tanımlı:

```
move_m@brave            dict=move_m@brave   fallbackId=move_m@brave@fallback
                        clipItems: run, idle, idle_intro, walk        ← 4 klip
move_m@brave@fallback   dict=...@fallback   fallbackId=move_m@generic
move_m@generic          dict=move_m@generic clipItems: BOŞ
```

`clipItems` **gerçek listedir**, yalnızca metadata değil. Listede olmayan bir
klip senin sözlüğünde **aranmaz**; motor doğrudan `fallbackId` zincirine gider.
Bu yüzden `wstart_l_0`'ı `.ycd`'ye eklemek hiçbir şey değiştirmedi.

Çözüm — kendi clipset tanımını kaydet:

```lua
-- fxmanifest.lua
files { 'clip_sets.xml' }
data_file 'CLIP_SETS_FILE' 'clip_sets.xml'
```

```xml
<fwClipSetManager>
  <clipSets>
    <Item type="fwClipSet" key="move_m@brave">
      <fallbackId>move_m@brave@fallback</fallbackId>
      <clipDictionaryName>move_m@brave</clipDictionaryName>
      <clipItems>
        <Item type="fwClipItemWithProps" key="wstart_l_0">
          <flags>APF_ISBLENDAUTOREMOVE</flags>
          <priority>AP_MEDIUM</priority>
          <boneMask />
        </Item>
        <!-- sağlamak istediğin HER klip burada bildirilmeli -->
      </clipItems>
      <moveNetworkFlags />
    </Item>
  </clipSets>
</fwClipSetManager>
```

`fallbackId` korunursa bildirmediklerin vanilla'dan gelmeye devam eder.

**Üst gövde katmanlaması bunun yerini TUTMAZ.** Ölçüldü: duruş klibi bayrak 49
(`LOOPING+UPPERBODY+SECONDARY`) ile oynatıldığında `IsEntityPlayingAnim` true
döndü ama geçiş bandında el↔kalça yine 0.78'den 0.37'ye düştü — movement
clipset ikincil üst gövde katmanını eziyor.

### 1.1c Fallback zincirindeki 66 klip

`move_m@generic` envanteri — kendi clipset'ini eksiksiz yapmak istiyorsan
sağlaman gerekenler:

| kategori | adet | örnek |
|---|---|---|
| başlama | 12 | `wstart_l_0`, `wstart_r_180`, `rstart_*` |
| durma | 16 | `wstop_l_0`, `wstop_quick_r_0`, `rstop_*` |
| dönüş | 20 | `idle_turn_l_-90`, `walk_turn_l3`, `run_turn_180_r` |
| eğim/merdiven | 8 | `walk_up`, `run_down_slope`, `walk_up_slope` |
| geçiş | 5 | `walktorun_left`, `runtowalk_right`, `idle_transition` |
| temel | 5 | `idle`, `idle_intro`, `walk`, `run`, `sprint` |

Her birinin kendi **mover profili** var: `wstart` hızlanan, `wstop` yavaşlayan,
dönüşler `Track 6`'da açı taşır. Sabit walk mover'ı kopyalamak yanlış sonuç verir.

### 1.2 XML hattı — SIRA ÖNEMLİ

```bash
Sollumz export (.ycd her zaman XML — format sisteminin dışında)
  → fix_ycd_xml.py       # <Hash> + klip→animasyon bağı
  → fix_clip_window.py   # Sollumz'un bir kare kayması
  → inject_channels.py   # eksik 20 vanilla kanalı
  → make_animlist.py     # AnimationList + parmak ayrımı + Unknown10/1C
  → xml_to_ycd.ps1       # binary
  → dogrula_clipset.py   # değişmez denetimi (BU ADIM ATLANMAZ)
```

Hepsi `C:\Users\musti\Desktop\FiveM\retarget\` altında.

### 1.3 Vanilla değişmezleri — `dogrula_clipset.py` bunları denetler

1. **Toplam kemik kapsamı AYNI ADLI vanilla klibiyle eşit.** **Asıl değişmez
   budur** — ama *sözlük* başına sabit bir sayı değil, *klip* başına vanilla'nın
   kendi değeri. Ölçüldü: `move_m@generic`'in 66 klibi **yedi farklı toplam**
   taşıyor (76×27, 71×13, 89×10, 88×10, 75×2, 101×2, 77×2); `idle` 71,
   `walk` 76, `run` 76. Sabit sayı yazan kapı ailenin %59'unu reddeder.
   Ambalaj: klip tipi `AnimationList` + **2** animasyon — 557 `move*` sözlüğün
   2646 klibinde **%86,7** (2294/2646). Üretirken bu yolu kullan (denetlenebilir
   tek yol), ama vanilla'yı denetlerken **kanun sayma**: 352 klip tek
   animasyonlu, `move_m@generic|walk` dahil (`anim`, animCount 1, 76 kemik).
   "Tam 2" da mutlak değil: **26 klipte 3** (baston/prop katmanı,
   `move_characters@lester@std_caneup` 23'ü).
2. İki animasyon kullanılıyorsa kemik kümeleri **ayrık** (kesişim 0)
3. İkinci animasyon **tipik olarak 32 kemik**: 30 parmak + 2 ayak başparmağı,
   hepsi `Track 1`, `Unknown10=0`. Oran ölçüldü: iki animasyonlu 2268 klibin
   **1862'si (%82,1)** 32; kalanlar 30·200, 68·40, 15·38, 62·20, 66·20.
   "8 vanilla dosyada frozenset eşitliği" kendi korpusunda doğru,
   **oyun geneline genellenemez** — doğrulayıcı 32'yi zorunlu tutarsa
   vanilla'nın %18'ini yanlışlıkla reddeder.
4. `(Unknown10 & 16) != 0` ⟺ `Track 5/6` var (247/247, ihlal 0)
5. `R(Track6) · Δ(Track5)` dünya yönü **daima ileri**
6. Klip penceresi animasyon süresini aşmaz
7. Döngü klibinde `(Duration − maks EndTime) × 30 = 1 kare`
8. `Unknown1C` = kemik kümesinin imzası; farklı küme farklı değer

---

## 2. HATA KATALOĞU — yapılan yanlışlar ve neden yanlış oldukları

### 2.1 `Type=Animation` klip yazmak — asıl kusur TİP DEĞİL, KAPSAM
Sollumz varsayılanı `Type=Animation`'dır ve o klibe yalnız **gövde kanallarını**
yazar. Movement clipset'te ped aralıklarla bind poza düşer — sebebi tipin adı
değil, yazılmayan **32 parmak/ayakbaşparmağı kanalıdır**; kapsanmayan kemik
"önceki pozunda kalır" (§ sürülmeyen kemik kuralı).

**Yanlış genelleme uyarısı — iki yönlü:**
- "vanilla'da hep AnimationList" **doğru değil**: 557 `move*` sözlüğün 2646
  klibinin **352'si (%13,3)** tek animasyonlu; içlerinde çözüm zincirinin son
  halkası `move_m@generic`'in **`walk`** klibi var (76 kemik, tek animasyon).
  Ayrıca `move_female_2h` sözlüğünün **tamamı** (idle/run/walk, 53 kemik) tek
  animasyonlu.
- Ama bu "istediğin gibi yaz" demek değil: tek animasyon yazacaksan **aynı adlı
  vanilla klibinin kemiklerinin hepsini** yazmak zorundasın (sayıyı
  `clips.tsv.gz`'den oku — `move_m@generic` içinde bile klipten klibe değişir:
  idle 71, walk 76, sprint 76, en yüksek 101). Pratikte bunu Blender/Sollumz
  hattında garanti etmenin yolu `make_animlist.py` ile 2'ye bölmektir →
  **üretirken `AnimationList` kullan, denetlerken kapsama bak.**

### 2.2 Mover yönünü yarım düzeltmek
İki geçerli üslup vardır ve **karıştırılamaz**:
- `(+Track5, birim Track6)` — `move_m@brave` üslubu
- `(−Track5, 180° Track6)` — `move_m@generic` üslubu

`−Track5` + birim `Track6` = "geri yürü". Motor klipten −1.72 m/s çıkarır,
görev +1.7 ister, net ≈ 0: **ped yerinde sayar, poz oynamaya devam eder.**

### 2.3 Mover hızını klip sınırının üstünden ölçmek ⚠️ EN SİNSİ HATA
Vanilla master animasyonu dört çekimi tek zaman çizgisinde tutar ve mover
**her klip başında sıfırlanır** (`move_m@brave` kare 488→489, −11.03 m).
Pencereyi sıfırlanmanın üstünden geçirirsen hız **yarıya** düşer.

Bu hataya düşüldü: vanilla run 2.39 m/s ölçüldü, gerçeği **5.128**. Yanlış sayı
doğrudan dosyaya yazıldı ve bir tur kaybettirdi.

**Kural:** ölçmeden önce `|Δy| > 0.3 m` sıçrama taraması yap, pencereyi böl.
Daha sağlamı: sıfırlanmayı eşikle değil **klip başlangıç karesiyle** bul.

### 2.4 `Unknown10` bayrağını mirasla taşımak
Animasyonu ikiye bölerken mover'sız yarı da `16` alırsa motora "kök hareketim
var" denip veri bulduramazsın. Kural: `16` ancak ve ancak `Track 5/6` varsa.

### 2.5 Animasyonu konumsal ortadan bölmek
`BoneIds` listesi tag sıralı olduğu için ayrım anatomik olarak anlamsız bir
yerden geçer. Doğrusu sabit 32'lik parmak kümesidir (§1.3-3).

### 2.6 Sollumz'un sıralamasına güvenmek
Sollumz hem klipleri hem animasyonları **Blender obje adına göre alfabetik**
dizer, oluşturma sırasına göre değil. "Önce walk yarattım" walk'ın `[1]` olduğu
anlamına gelmez. Bir kez `walk` klibi koşu mover'ına bağlandı.
**Kural:** sırayı mover imzasından doğrula, bağı `<AnimationHash>` ile açıkça yaz.

### 2.7 Keyframe'leri zamanda ölçekleyip kesirli kare bırakmak
Kadansı düzeltmek için keyframe pozisyonlarını çarpmak kesirli kare üretir
(39.458 keyframe'in 31.392'si). Sollumz `FrameCount`'u yanlış yazar
(`FrameCount=181` / `Duration=3.6` gibi tutarsızlık).
**Doğrusu:** kaynağı `frame_set(tam, subframe=...)` ile kesirli konumlarda
örnekleyip **tam sayı** hedef karelere yeniden pişirmek.

### 2.8 Yeniden pişirirken kaynakta olmayan kanal yazmak
Tüm kemiklere `location` keyframe'i atmak kanal sayısını 43 → 94 yapar.
Önce kaynağın hangi (kemik, özellik) çiftlerine sahip olduğunu çıkar, sadece
onları yaz.

### 2.9 Eksik kanalları "sıfır/birim" ile doldurmak
- `PH_R_Hand` `Track 0`'a `(0,0,0)` yazmak prop takma noktasını **5.4 cm** kaydırır
  (mızrak tam o kemiğe bağlı)
- `SKEL_Pelvis`/`SKEL_Spine_Root`'a birim quaternion yazmak ±90° Y çeviriciyi
  siler, hiyerarşiyi yatırır

**Doğru değerler** (vanilla'dan okundu, `pedrig.py` rest transformlarıyla
mikron mertebesinde doğrulandı) → `inject_channels.py` içinde.

### 2.10 `SKEL_Spine3`'ü sabit kanalla doldurmak
Vanilla'da **%98,5 animasyonlu**. Kimlik quaternion yazmak göğsü dondurur.
Blender tarafında keyframe üretilmeli — hâlâ açık iş.

### 2.10b Zemin referansını KEMİKTEN almak ⚠️ "ölçüm doğru, referans yanlış"
Rest pozunda en alçak **kemik** z = −0.9577, en alçak **vertex** (ayakkabı
tabanı, `ayak_feet` mesh'i) z = −1.0024 → aradaki **4.48 cm** gerçek zemindir.
Kemiğe hizalarsan ölçüm "hata 0.00 cm" der ama ped gözle 4.5 cm havada durur.
Ölçüm aracına da aynı sabit girmeli, yoksa "hâlâ havada" diye yanlış düzeltme
yapılır (yapıldı).

### 2.10c Zemin ölçütü olarak "en alçak mutlak nokta"
Yanlış ölçüt. Yürüyüşün en alçak karesi **parmak-kalkış** karesidir; oraya
hizalarsan ped parmak ucunda yürür. Doğru ölçüt **düz-taban karesi**: ayak
eğiminin rest değerine (−18.1°) en yakın olduğu kare. Walk'ta bu iki kare
farklıdır (düz faz 2.9 cm yukarıda, parmak-ucu karesi yerde).

### 2.10d Ayak eğimi düzeltmesinde işareti tahmin etmek
Sollumz rig'inde kemik eksenleri anatomik değil; yerel eksen etrafında
`+delta` mı `−delta` mı gerektiği **denenerek** bulunur. Bir kez `+` seçildi ve
ayak −36.6°'den −55.2°'ye, yani ters yöne gitti.

### 2.10e Diz menteşe eksenini her karede `u×v` ile hesaplamak
Diz düzken (177°) `u` ve `v` neredeyse zıt yönlüdür; `|u×v| = sin(177°) ≈ 0.05`
— tam da düzeltilmek istenen karelerde eksen **sayısal olarak kararsız**.
Sonuç: bacak bükülmek yerine yana savrulur, **ayaklar birbirine dolanır**.
Menteşe ekseni kemiğin yerel çerçevesinde **sabittir**; en bükük kareden
(çarpım en iyi koşullanmış) bir kez hesaplanıp tüm karelerde kullanılır.
Doğrulama: sol/sağ ayak yanal ayrımı hiçbir karede işaret değiştirmemeli.

### 2.10f `pb.matrix` setter'ıyla kare kare döndürmek
`pb.matrix = R @ pb.matrix` + `keyframe_insert` döngüsü, sonraki `frame_set`
kendi yazdığın keyframe'i yeniden okuduğu için **hata biriktirir** (ölçüldü:
bilek 1 metre havaya çıktı). Doğrusu saf quaternion aritmetiği: fcurve
keyframe'lerini oku, sabit bir delta ile çarp, geri yaz — poz hiç okunmadan.

### 2.10g Kadans düzeltirken keyframe pozisyonlarını çarpmak
Kesirli kare üretir (39.458 keyframe'in 31.392'si) ve Sollumz `FrameCount`'u
tutarsız yazar (`FrameCount=181` / `Duration=3.6`). Doğrusu
`frame_set(tam, subframe=…)` ile kesirli konumlarda örnekleyip **tam sayı**
karelere yeniden pişirmek. Pişirirken **yalnızca kaynakta var olan** kanalları
yaz; hepsine `location` atmak kanal sayısını 43'ten 94'e çıkarır.

### 2.10h `SetPedMinMoveBlendRatio`'yu poz sabitlemek için kullanmak
Bu native pozu değil **hareketi** zorlar: taban 1.0'da kalınca oyuncu tuşu
bıraksa da ped yürümeye devam eder. Ayrıca MBR hem pozu hem hızı sürdüğü için
"şu hızda poz tamamlansın ama hız değişmesin" MBR ile **yapılamaz** — 0.9'da
MBR'yi 1.0'a çekmek ped'i 1.736 m/s'ye hızlandırır.

Poz erken tamamlansın isteniyorsa çözüm klip tarafındadır: duruş klibinin üst
gövdesi yürüyüşünkine taşınır. Matematiği şu: motor idle↔walk pozunu MBR ile
**doğrusal** harmanlar ve 0.8 m/s ≈ MBR 0.46, yani harman %46 tamamlanır.
`0.77 = idle + 0.46×(0.778 − idle)` → `idle = 0.763`. Görünür bir "kalkma"
bırakıp aynı anda 0.8'de tamamlanması **mümkün değil**.

### 2.10i Geçiş klibinin mover rampasını pencereden uzun yaymak
`wstart` animasyonu 3 sn, klip penceresi 2 sn iken rampayı 3 sn'ye yaymak
pencere sonunda hızı 1.157 m/s'de bırakır → "aşırı yavaş hızlanıyorum".
Rampa **pencere içinde** tamamlanmalı: `pos(t) = v·t²/(2·T)` ile `T = pencere`,
sonrası sabit hızda devam.

### 2.11 Aracın göstermediğine "yok" demek
CodeWalker geri-derlerken bazı alanları yazmaz (`<AnimationHash>` boş görünür).
Kaynak XML'de düğüm hiç yoktur ama klipler çalışır — derleyici bağı ad/sırayla
kurar. **Bir aracın göstermemesi yokluk değildir.**

### 2.12 Ölçüm aracının kendi sınırını unutmak
`dogrula_clipset.py` vanilla'yı "hatalı" gösterir: master animasyon çok çekimli
ve `Track 6` `CachedQuaternion` kodlamasında. Araç **bizim** çıktımızı
denetlemek için doğrudur, vanilla'yı yargılamak için değil.

### 2.13 Belirtiden hipoteze atlayıp tek tek denemek
Bu iş boyunca en pahalı hata. Çürütülen hipotezler: ambient idle, clipset'in
düşmesi, sözlüğün bellekten atılması, döngü sarma noktası, `Track 134-140`
eksikliği, `.yed` expression eksikliği, klip sonunun veri bitişine denk gelmesi.
Her biri bir tur yedi.

**İşe yarayan yöntem:** vanilla korpusunu tarayıp **istisnasız kuralları**
çıkarmak, sonra kendi dosyanı o kurallara göre denetlemek.

---

### 2.14 Native adını veritabanından almak
`GetGroundZFor3dCoord` veritabanında böyle geçiyor ama **çalışma zamanındaki ad
alt çizgilidir**: `GetGroundZFor_3dCoord`. Yanlışıyla çağırınca
`attempt to call a nil value` verir. Doğrulama yolu: sunucudaki mevcut
kullanımları ara (qb-core 20+ yerde alt çizgili kullanıyor). Linter bu adı
"native değil" diye reddeder — yanlış negatif, kodu değiştirme.

Ayrıca: FiveM'de `vector3`'ün **`:dot()` metodu yoktur**, elle hesaplanır.
Çıktı parametreleri (`groundZ` gibi) Lua'da argüman değil **dönüş değeridir**;
linter C imzasını sayıp W104 verir, o da yanlış pozitif.

### 2.15 Kemik tag'lerini tahmin etmek
`pedrig.py` ile doğrula. Bir kez `SKEL_L_Calf`/`SKEL_R_Calf` ters yazıldı ve
`SKEL_*_Foot` yerine `IK_*_Foot` tag'leri kullanıldı. Doğru değerler:
`L_Thigh 58271 · R_Thigh 51826 · L_Calf 63931 · R_Calf 36864 · L_Foot 14201 ·
R_Foot 52301 · L_Toe0 2108 · R_Toe0 20781 · R_Hand 57005 · L_Hand 18905`

### 2.16 Ölçüm aracının kendi referansını doğrulamamak
Ayağın "yerden yüksekliği" `GetEntityCoords(ped).z`'ye göre ölçülmüştü — o
ped'in **orijinidir**, zemin değil. Gerçek zemin `GetGroundZFor_3dCoord`.
Araç yanlış referansla ölçerse yanlış düzeltmeye yol açar; bu iş boyunca
üç ayrı referans hatası çıktı (zemin=kemik, zemin=origin, native adı).

## 3. Ölçüm araçları

| araç | ne yapar |
|---|---|
| `res_to_xml.ps1` | binary `.ycd` → XML |
| `extract_asset.ps1` | GTA RPF'ten vanilla dosya çıkarır |
| `dogrula_clipset.py` | 8 değişmezi denetler, çıktıyı kapıda tutar |
| `clips.tsv.gz` | sözlük/klip envanteri — **sözlük adları, clipset adları değil** |
| `pedrig.py` | kemik tag → ad, rest transform |

`clips.tsv` tuzağı: `move_ballistic` bir sözlük adıdır, `RequestAnimSet` ile
yüklenmez. Clipset adı ≠ sözlük adı.

---

## 3.5 Mover çözücüsü — `ycd_mover.py` (ÇALIŞIYOR, 66 klip üretildi)

Vanilla `Track 5/6`'yı okumak için. Doğrulaması iki bağımsız testtir ve
**ikisi de geçmeden klip üretme** — yanlış çözüm 60 klibi yanlış açıyla üretir:

| test | dosya | beklenen | sonuç |
|---|---|---|---|
| dönüş açısı | `move_m@brave@fallback` `idle_turn_*` | tam ±90 / ±180 / 0 | **6/6 tam** |
| hız | `move_m@brave` | idle 0, walk 1.736, run 5.128 | **4/4** |

Dört ayrı hata vardı, hepsi **varsayım**tı:

- **`CachedQuaternion` bir kanal değil, İŞARETÇİDİR.** Değeri yoktur; yalnız
  `<Type>` + `<QuatIndex>` taşır. Track dört kanaldan oluşmak zorunda değil:
  ölçülen iki dizilim var ve ayırmadan okumak yaw'ı **180° kaydırır**.
  - **3 değer kanalı** → `QuatIndex` **düşürülmüş** bileşendir; saklananlar
    *kalan* yuvalara sırayla girer (`move_m@brave`)
  - **4 değer kanalı** → hepsi `x,y,z,w`'ye girer, `QuatIndex`'teki yeniden
    hesaplanır (`move_m@brave@fallback`)
  - eksik bileşen: `sqrt(max(0, 1 − diğerlerinin kareleri))`,
    işaret `CachedQuaternion1` → `+`, `2` → `−`
- **`IndirectQuantizeFloat`'ta `<Frames>` kare listesi DEĞİL**, `<Values>`'a
  **indeks tablosudur** (`len(Frames) == FrameCount`). Düz okunursa dizi kare
  sayısından kısa kalır ve profil sessizce bozulur.
- **Dünya yer değiştirmesi KARE KARE döndürülür**: `Σ R(yaw_i)·(p_i − p_{i−1})`.
  Toplam farkı tek bir başlangıç yaw'ı ile döndürmek yanlış — kodlama pencere
  ortasında değişebiliyor (`walk`'ta kare 416'da yaw 180→0 atlıyor) ve **işaret
  ters** çıkıyor.
- **Track 6 da sıfırlanır** — hem take hem sequence sınırında. Tek karede 90°'yi
  aşan yaw adımı gerçek dönüş değil, kodlama süreksizliğidir; atlanır. Gerçek
  dönüşler kademelidir (180°'lik klip ~35 karede döner ≈ 5°/kare).

**q ile −q aynı dönüştür** ama ardışık kareler zıt yarımkürede kalırsa kümülatif
yaw sahte dönüş sayar (ölçüldü: 180°'lik klip 328 çıktı). Her kareyi bir
öncekiyle aynı yarımküreye çek.

### Dönen klibin hızı ölçülürken: KİRİŞ, yay değil

Bir dönüş klibinde ped daire yayı çizer; çözücü **net yer değiştirmeyi**, yani
kirişi ölçer. Beklenen değer `v · |sin(θ/2)/(θ/2)|`:

| θ | oran | walk 1.736 → beklenen | ölçülen |
|---|---|---|---|
| 90° | 0.900 | 1.563 | 1.563 |
| 180° | 0.637 | 1.105 | **1.105** |
| 483° | 0.209 | (run) 1.070 | 1.041 |

Bu düzeltme yapılmazsa **24 doğru klip yanlış raporlanır** — bir tur boyunca
olmayan bir hatayı kovaladım. Hızlanan + 180° dönen kliplerde ölçülen ~%18
yüksek çıkar: yolun çoğu dönüş bittikten sonra alınır, kiriş uzar. Beklenen.

## 3.6 66 klibin üretimi — `uret_66.py`

Tek veri tablosu: `(klip, içerik, v0, v1, dönüş°, pencere_kare, çift)`.
Hedefler `klip_profilleri.json`'dan, yani **vanilla ölçümünden** gelir.

- **Klip başına AYRI animasyon.** Mover kümülatiftir; bir animasyonda birden
  fazla klip penceresi olursa önceki pencerenin biriktirdiği yaw sonrakinin yer
  değiştirmesini **dünya uzayında döndürür** ve klip yana yürür. Vanilla bunu
  take sınırında sıfırlayarak çözüyor; biz pencere başına ayrı animasyonla.
- **`l`/`r` varyantları da ayrı animasyon.** İçerik yarım çevrim kaydırılır
  (`wstart_r` penceresi kare 16'da başlar), çünkü **mover rampası pencere
  başından başlamak zorunda** — yoksa `r` varyantı yarım hızla başlar.
- Döngü uzunlukları: idle 100, walk 30, run 18 kare. Döngü klibinin kare sayısı
  `n·çevrim + 1` olmalı, yoksa kapanmaz.
- **Sollumz `Type=Animation` klibine animasyon referansı YAZMAZ** — eşleşme
  konumsaldır (klip[i] ↔ animasyon[i]). Her ikisi de obje adına göre alfabetik
  sıralanır; `clip_<ad>` / `an_<ad>` kullanılırsa sıra birebir tutar.
  **Varsayma, doğrula:** animasyonun `FrameCount`'unu beklenen kare sayısıyla
  karşılaştır (66/66 tuttu).
- Boyut korkusu yersiz: 22.4 MB XML → **206 KB `.ycd`**.
- `clip_sets.xml` **üretilir** (`yaz_clipsets.py`), elle yazılmaz. Listedeki tek
  yazım hatası o klibi sessizce vanilla'ya düşürür.

## 3.7 Tags, Properties ve sürülmeyen kemik

### Tag yapısı (`move_m@brave` walk/run'dan birebir okundu)

| ne | NameHash / UnkHash | Attributes | faz |
|---|---|---|---|
| **Foot** | `hash_B82E430B` / `hash_7E0050C6` | `hash_2BC03824` Bool 1 + **`right`** Bool 0\|1 | `StartPhase == EndPhase` (anlık) |
| **MoveEvent** | `hash_7EA9DFC4` / `hash_774E6BC1` | `hash_7EA9DFC4` HashString `hash_70ABE2B4` | **`EndPhase` = ayak fazı**, başı 0.07 s önce |

MoveEvent penceresi **ayak temasında biter** — ölçüldü: MoveEvent
`[0.0009, 0.012]` → Foot `0.012`; `[0.0879, 0.099]` → Foot `0.099`. Fark 12/12
tagda sabit 0.0111 faz = **0.07 saniye**. Genişlik faz değil saniye cinsinden
sabittir, yani klip süresine bölünerek yazılır.

**Fazlar vanilla'dan KOPYALANMAZ** — kadans farklıdır, ses ayak yere değmeden
çalar. Kendi klibinin topuk vuruşundan ölçülür: ayak kemiğinin dünya Z'si
çevrimin minimumuna 1 cm yaklaştığı **ilk** kare (`olc_topuk.py`). Ölçülen:
walk L=29 R=15 (çevrim 30), run L=2 R=11 (çevrim 18) — ikisi de tam yarım
çevrim aralıklı, ölçümün doğruluğunun işareti.

**Klibin içeriğini adından tahmin etme.** `runtowalk_*` **walk** içeriği,
`walktorun_*` **run** içeriği kullanır; "r ile başlıyorsa koşudur" kuralı bu
ikisini ters işaretler. İçerik üretim tablosundan okunur.

### Properties

- `hash_69497CB4` / `hash_571B7C5F`, Int **−958235956** → `move_m@generic`'te
  **66/66** klipte var, hepsine yazılır.
- `hash_421AE770` / `hash_A5E1493A`, Float **1.12** → yalnız `move_m@brave`'in
  `run` klibinde; generic'te **hiç yok**. Sadece `run`'a yazılır.
- `hash_320B8B63` / `hash_443D96E7` → generic'te yalnız `idle`/`idle_intro`'da.

### Sürülmeyen kemik = ESKİ POZDA KALIR

Vanilla movement klipleri omurganın **beşini de** sürer (`SpineRoot` 57597,
`Spine0` 23553, `Spine1` 24816, `Spine2` 24817, **`Spine3` 24818**). Retarget
`Spine3`'e keyframe yazmamıştı → klip o kemiği **sahiplenmiyordu**. Sürülmeyen
kemik rest'e dönmez, **önceki animasyonun bıraktığı pozda kalır**: bir saldırı
klibinden sonra göğsün üstü burulmuş hâlde kalıp ped öyle yürüyebilir.

Çözüm kanalı **açmak**: birim quaternion (yerel rest, "ebeveynini takip et")
ile iki keyframe. Duruşu zaten `Spine0/1/2` taşıdığı için görünüm değişmez;
değişen şey kemiğin artık klip tarafından sahiplenilmesidir.

## 3.71 Mover sözleşmesini vanilla ile hizala — KAYIPSIZ dönüşüm

Vanilla mover'ı iki üslupla saklar ve bunu **sistematik** yapar: `+t5/birim`
(36 klip) ve `−t5/180°` (21 klip). `rstop_l` `+`, `rstop_r` `−`;
`walktorun_left` `−`, `right` `+`. `l`/`r` aynı anda çalmadığı için vanilla'da
sorun değil.

Bizim kliplerimizin hepsi `+t5/birim` yazıyordu. Bizim klipten vanilla klibine
geçerken motor mover **dönüşünü de harmanlıyor**; birim ile 180° arası
harmanlama **90°'den geçer** → ped yana gider. Belirti: *"sola yürümeye
başlayınca ters yönde zorla hareket ediyorum."*

**Düzeltme gövdeye hiç dokunmaz.** Dünya hareketi `R(t6)·Δt5`'tir:

```
R(180°) · (−dx, −dy, dz) = (+dx, +dy, dz)
```

`Track 5`'in **yalnız x ve y**'sini negatifle (z yükseklik, dönmez),
`Track 6`'yı `(w,x,y,z) = (0,0,0,1)` yap. Dünya hareketi **birebir aynı**
kalır; süreye, kadansa, içeriğe dokunulmaz. Değişen tek şey temsildir — ve
harmanlama temsil üzerinden yapıldığı için düzelen de budur.

**Denetim şart:** dönüşümden sonra her klibin dünya hızı öncekiyle **aynı**
olmalı. Değiştiyse dönüşüm yanlış uygulanmıştır. (8 klipte uygulandı, 8'inde
de hız değişmedi.)

**Gerçek dönüş taşıyan klibe dokunma.** `Track 6` açısı kare kare değişiyorsa
(> 5° oynama) o bir üslup değil, animasyonun kendisidir.

**Doğru ölçüt `move_m@generic` değil, çözüm zinciridir** (`brave` → `@fallback`
→ `generic`). Vanilla'nın kendisi de `run`'ı brave'den, `wstop`'u generic'ten
çözer; yalnız generic'e bakan denetim `run`'ı yanlış raporlar.

### `temas_fazlari.json` build'e özeldir

Bu dosya üretici ile `inject_tags` arasındaki **arayüzdür** ve her build kendi
fazlarını üretmek zorundadır — sabit çevrimli build `temas_sabit_cevrim.py`,
derleyici build'i `derle_clipset.py`. Yanlış build'in JSON'unu kullanmak adım
seslerini kaydırır ve **hiçbir denetim yakalamaz**: dosya geçerlidir, sadece
yanlıştır.

## 3.72 ⛔ Üretilen `clip_sets.xml` bozuk çıkabilir — ve oyun susar

XML yorumunun içinde **iki tire yan yana yasaktır**. Üretici şablonuna başlık
altı çizgisi (`--------`) koymak dosyayı ayrıştırılamaz yapar. Sonuç:

- oyun **hiçbir hata vermez**
- `data_file 'CLIP_SETS_FILE'` sessizce devre dışı kalır
- clipset **vanilla tanımıyla** kalır (`move_m@brave` = 4 klip)
- `.ycd` yüklenmeye devam eder, yani `idle`/`idle_intro`/`walk`/`run` bizden
  gelir, **geri kalan her şey vanilla'dan**

Bu bir kez oldu ve **iki turluk yanlış teşhise** yol açtı: aslında hiç
çalışmayan bir yapılandırmanın belirtilerine bakıp önce dönüş klibi içeriğini,
sonra mover formülünü suçladım. Her ikisi de gerçek kusurdu ama **o anki
belirtilerin sebebi değildi.**

Kural: **üretici kendi çıktısını ayrıştırmadan yazmasın.**

```python
try:
    ET.fromstring(xml)
except ET.ParseError as e:
    raise SystemExit(f'[X] uretilen XML BOZUK, yazilmadi: {e}')
```

### Test öncesi kapı — DAĞITILMIŞ dosyada

`on_test_denetimi.py`, üretim klasörünü değil **sunucudaki** dosyaları okur:
`.ycd`'yi geri okur, `clip_sets.xml` ile karşılaştırır ve şunları sınar —
bildirilen her ad sözlükte birebir var mı, **her klibin toplam kemik kapsamı
AYNI ADLI vanilla klibiyle eşit mi** (sayı `clips.tsv.gz`'den ad ile çekilir;
sözlük başına sabit değer **yoktur**), `<Hash>`'ler dolu mu, `Properties` var
mı, `SKEL_Spine3` sürülüyor mu, `Unknown10` bit 16 ↔ Track 5/6 değişmezi
tutuyor mu. Kapı `AnimationList` **üretmeni bekler** (bizim hattımız öyle
üretir) ve üretim tarafında `AnimationList` + 2 animasyon şartı **HATA**
kalır; yalnız **vanilla'yı denetlerken** bilgiye düşer — aksi hâlde
vanilla'nın %13,3'ü "bozuk" raporlanır.

**Savepoint'lerdeki kopyaları da düzelt** — bozuk dosya orada kalırsa geri
yükleme onu geri getirir. (Bu da oldu: iki savepoint bozuk XML taşıyordu.)

## 3.75 DERLEYİCİ — mover'ı vanilla'dan kopyala, gövdeyi mover'a uydur

> Bu bölüm §3.6'daki formül tabanlı üretimin **yerini alır.** Formül yaklaşımı
> ölçülebilir şekilde yanlıştı; aşağıdaki sayılar o yanlışın maliyetidir.

**İlke tek cümle: gövde mover'ı takip eder.** Her karede vanilla'nın mover
eğrisinden anlık hız okunur, gövde o hıza göre `idle↔walk↔run` harmanlanır,
adım fazı hızdan **integre** edilir. Zamanlama uydurulmaz.

Girdi: gövde içeriği (`CS_idle_x`/`walk_x`/`run_x`) + `referans_mover.json`
Çıktı: 66 animasyon + 66 klip + `derleme_raporu.txt` + `temas_fazlari.json`

| adım | araç |
|---|---|
| referans çıkar (çözüm sırasıyla) | `cikar_mover.py out.json brave.xml fallback.xml generic.xml` |
| derle | `derle_clipset.py` (Blender headless) |
| hat | `fix_ycd_xml` → `fix_clip_window` → `inject_channels` → `make_animlist` → `inject_tags` |
| denetle | `fark_vanilla.py bizim.xml vanilla.xml` |

### Formülle üretmenin ölçülmüş bedeli

| eksen | formül | vanilla | belirti |
|---|---|---|---|
| durma profili | yolun %75'i pencerenin %50'sinde | %13-20'sinde | *"aşırı uzun süre yavaşlıyorum"* |
| `wstop_l_0` | 2.0 s'de 1.74 m | 3.80 s'de 1.1 m | fazla yol + uzun kayma |
| `rstop` süresi | 1.80 s | 3.73 s | — |
| sözleşme | 66/66 `+t5/birim` | 36 `+`, 21 `−t5/180`, 9 ara açı | *"ters yönde zorla hareket"* |

**Sözleşme en kritik olanı.** Vanilla iki üslubu **sistematik** karıştırır —
`rstop_l` `+`, `rstop_r` `−`; `walktorun_left` `−`, `right` `+`. Hepsine tek
üslup yazınca, bizim klipten vanilla klibine geçerken motor mover **dönüşünü
de harmanlar**; birim ile 180° arası 90°'den geçer, yani **yan taraf**.
`l`/`r` aynı anda çalmadığı için vanilla'nın karıştırması sorun değildir —
bizim tek üsluba sabitlememiz sorundur.

Derleyici sonrası ölçüm: profil şekli sapması **sıfır klip**, sözleşme dağılımı
`+t5:35 / −t5:23` (vanilla `36 / 21`), süreler eşleşti.

### Türetilmiş şeyler de derleyiciden çıkar

**Tag fazları sabit çevrimden alınamaz.** Kadans hızdan integre edildiği için
hızlanan/yavaşlayan klipte adımlar eşit aralıklı **değildir**. "walk = her 30
karede bir adım" demek `wstart`/`wstop`'ta sesi ayağın gerçekte yere değdiği
andan kaydırır. Derleyici faz birikimini zaten hesapladığı için temas anlarını
da o üretir (`temas_fazlari.json`).

### Eskiyen denetim

`dogrula_clipset.py`'ın "mover ileri olmalı" kuralı artık **yanlış alarm**
veriyor: vanilla'nın `−t5/180` kliplerini kopyaladığımız için dünya yer
değiştirmesi o kliplerde negatif okunuyor — büyüklük vanilla ile birebir aynı
(`rstop_l` ±1.022). Doğru denetim `fark_vanilla.py`'dır: referansla karşılaştır,
mutlak yön varsayma.

### ⛔ DERLEYİCİNİN AÇIK KUSURU — dağıtılmadı

**Farklı kadanslı iki gaiti aynı fazda harmanlamak GEÇERSİZ.** `walk`'ın sol
topuk fazı 0.967, `run`'ınki 0.111. Ara hızda (%31 walk + %69 run) iki gaitin
ayak kaldırmaları birbirini götürür ve **ayak neredeyse hiç kalkmaz**.

Ölçüldü — derleyici çıktısı vs bir önceki çalışan sürüm:

| ölçüt | derleyici | çalışan sürüm | doğrusu |
|---|---|---|---|
| `walk` temas sayısı (7.4 s) | **5** | 16 (8 s) | ~14 |
| `walk` sağ ayak kayması | 0.162 m | 0.095 m | — |
| `wstart_l_0` sol | 0.158 m | 0.047 m | — |
| `run` ayak Z hareketi | **0** | 0 | > 0 |

Mover tarafı doğru (profil sapması 0, sözleşme örtüşüyor); **gövde harmanlaması
hatalı**. Çözüm yönü: fazda harmanlamak yerine **faza göre hizalamak** — hedef
gaitin temas fazını kaynak gaitin temas fazına oturtup öyle harmanlamak, ya da
ara hızlar için harman yerine tek gaiti zaman ölçekleyerek kullanmak.

**Ders:** dosya seviyesinde her eksende vanilla'ya oturan bir çıktı, gövde
seviyesinde bozuk olabilir. Mover doğruluğu gait doğruluğunu göstermez; ayak
kaymasını ve **temas sayısını** ayrıca ölç (`olc_kayma.py`). Ölçüm de
kendi kendine yetmeli — mover'ı referans JSON'dan değil **action'ın kendi
fcurve'lerinden** oku, yoksa iki sürüm kıyaslanamaz.

Ayrıca: ayak kaymasının **mutlak** değeri geçme/kalma ölçütü değildir —
oyunda "mükemmel" denen sürüm de 7-15 cm ölçüyor. Karşılaştırmalı bak.

### Yeni animasyon eklerken

Kaynak action'ı `KAYNAK`'a ekle, gerekiyorsa `HIZ`/`ADIM` eşiklerini genişlet.
Klip adı referansta yoksa derleyici onu atlar ve raporda söyler.

## 3.76 ⛔ Mover NİCEMLEMESİ — "karakter tekliyor"un kök sebebi

**Belirti:** ped yürürken hız `0.69 / 1.37 / 2.06` m/s arasında zıplıyor ve
zaman zaman **0'a düşüyor** — oyuncu "tekliyor / anlık donuyor" diyor.

Sayılar ele veriyor: hepsi **0.686'nın katları**, ve 0.686 tam olarak
`wstart_l_0` klibinin **kuantumu × 30 fps**. Salınım değil, **nicemleme**.

| kanal | aralık | kuantum | m/s adımı |
|---|---|---|---|
| bizim `wstart_l_0` | 3.73 m | 0.02286 | **0.686** |
| bizim `walk` | 14.76 m | 0.05787 | 1.736 |
| bizim `run` | 21.02 m | 0.17093 | 5.128 |
| **vanilla** `walk` | 20.86 m | **0.00003** | **0.001** |

Bizimki 8 bit (aralık ÷ kuantum = 255), vanilla ~20 bit (695.000 seviye).

**Neden:** synthesize edilen mover kusursuz **doğrusal** bir rampadır —
ardışık kareler arası fark hep aynı. Kodlayıcı kuantumu en küçük farka
eşitlediği için kuantum **tam bir karelik adıma** eşit olur ve geriye
alt-kare çözünürlüğü kalmaz. Oyun 30 fps'ten farklı hızda çizince kimi kare
0, kimi kare 2 kuantum alır. Vanilla'nın verisi gerçek yakalanmış harekettir;
kare farkları eşit olmadığı için en küçük fark çok küçük çıkar.

**Denendi, OLMADI:** XML'deki `<Quantum>` alanını elle yazmak. Derleyici
(CodeWalker) onu okumuyor, **veriden yeniden hesaplıyor** — 168 kanal
değiştirildi, derlemeden sonra hiçbiri incelmedi.

### ÇÖZÜM — nicemleme tohumu

Vanilla'nın kuantumu neden ince: master animasyonu `idle` gibi neredeyse
duran bölümler içerir, yani kanalda çok küçük kare farkları vardır.

Aynısını kasten üret: klip penceresinin **çok ötesine**, oyunun okumayacağı
yere, **3e-5 m adımlı** birkaç kare koy. Kanalın tamamı o inceliği alır.
0.03 mm — görünmez.

```python
kok = son + adim * (hedef - f1)
for j in range(1, 6):
    fc.keyframe_points.insert(hedef + j, kok + 3.0e-5 * j)
```

Ölçülen sonuç — **tüm klipler vanilla seviyesinde**:

| klip | önce | sonra |
|---|---|---|
| `walk` | 0.05787 (1.736 m/s) | **0.00003** (0.001) |
| `run` | 0.17093 (5.128) | **0.00003** |
| `sprint` | 0.23530 (7.059) | **0.00003** |
| `wstart_l_0` | 0.02286 (0.686) | **0.00003** |

**Tohumu mover'ı yeniden yazan HER adıma koy.** `durma_hizlandir.py`
`kuyruk_ekle.py`'den sonra çalışıp kanalı yeniden yazdığı için tohumu
siliyordu; ölçüldü: diğerleri 0.00003'e inerken `wstop_l_0` 0.00868'de kaldı.

**Ölçüm kuralı:** kuantumu XML'den okuma, **derlenmiş dosyadan** oku
(`olc_nicemleme.py`).

## 3.77 Animasyonu klip penceresinde bitirme — KUYRUK bırak

**Belirti:** ped yürümeye başlarken ~1.90 s'de ~0.3 s **tam duruyor**, sonra
devam ediyor. İki bağımsız koşuda milisaniyesi tuttu:

```
1.80s hiz 1.68 | 1.91s hiz 0.01 | 2.02s hiz 0.03 | 2.13s 0.27 | 2.24s 1.94
```

`wstart_r_0` klibinin süresi **1.87 s** — donma tam klibin bittiği anda.
`MoveBlendRatio` bu süre boyunca **1.00 sabit**, yani niyet tam; eksik olan
**mover**.

**Sebep:** klip başına ayrı animasyon üretince animasyon pencereyle *tam aynı
yerde* bitiyor. Vanilla'da bir animasyon onlarca klibi barındırır; motor
blend-out sırasında pencereyi aşıp okuduğunda mover verisi hâlâ vardır.
Bizde aşınca veri kalmıyor → hız sıfıra düşüyor, sonraki klip devralınca
geri geliyor.

**Çözüm** (`kuyruk_ekle.py`) — pencereden sonra ~15 kare (0.5 s) uzat:

| kanal | kuyrukta |
|---|---|
| gövde | içerik döngüsü devam eder |
| `Track 5` | son karedeki hızla **doğrusal** sürer (durmaz) |
| `Track 6` | son quaternion **sabit** (fazladan açı üretmesin) |

Klip penceresi **değişmez** — yalnız arkasında veri olur. Denetim: her klip
için `animasyon süresi − pencere sonu ≥ 0.30 s`.

### Teşhis aracı için iki kural

- **`IsEntityPlayingAnim` movement clipset klibini GÖRMEZ.** MoVE ağı üzerinden
  çalar, anim task değildir; native hepsine `false` döner. İlk sürüm 66 klibi
  tek tek sordu ve her satırda `klip=(yok)` yazdı — sütun baştan boştu ve
  "hiçbir şey çalmıyor" sanılabilirdi. Ölçümü klip **adına** değil
  **davranışa** dayandır.
- **Hızlanmayı hızdan değil NİYETTEN başlat** (`GetPedDesiredMoveBlendRatio`).
  Kronometreyi hız eşiğinden başlatan sürüm "1.0'a 0.08 sn'de çıktı" diyordu;
  oysa ped zaten hareketliydi ve şikâyet edilen gecikme ondan **önceki**
  aralıktaydı. Ayrım: MBR hızlı yükselip hız geride kalıyorsa kusur bizim
  mover'da; MBR'nin kendisi yavaşsa kusur hareket görevinde.

## 3.78 Dönen klip: gövde bizim, MOVER vanilla'dan birebir

§3.8'de "dönüş klibi üretilemez" deniyor — doğru ama **eksik**. Klibi dışarıda
bırakmanın bedeli daha ağır çıktı: bildirilmeyen klip devreye girdiği anda
motor vanilla'ya düşüyor ve vanilla'nın kol pozu prop tutmuyor.
Belirti: *"sola dönerek yürümeye başlayınca eller aşağı iniyor."*

Doğru çözüm ikisinin arası: **gövde bizde kalır, mover vanilla'dan birebir
gelir** (`mover_vanilla_uygula.py`):

- kare sayısı → vanilla'nın kare sayısı (içerik döngüsü uzatılır/kırpılır)
- `Track 5` / `Track 6` → vanilla'nın eğrisi, kare kare
- klip penceresi → animasyonun tamamı
- tag fazları → **yeni kare sayısına göre tazelenir** (unutulursa kayar)

Dönüş hızı, açısı ve sözleşmesi böylece **tanım gereği** doğru olur — formül
yok. Ölçüm: 34 klipte dünya hızları vanilla ile birebir, net açılar **33/34**
uyumlu.

**Kalan sınır kozmetiktir:** gövde dönüşe yatmaz, ayaklar çapraz basmaz.
Ped doğru yere gider, dönüş jesti düz yürüyüştür. "Eller aşağı"dan iyidir.

Tek sapan `wstart_l_-90` (bizde 90°, vanilla ham verisi 180°). Simetriye göre
**90 doğru olan**: `wstart_r_90` → −90, `wstop_l_-90` → +90,
`idle_turn_l_-90` → +90. Vanilla'nın o tek okuması baştan beri aykırıydı.

## 3.8 Dönüş klibi ÜRETİLEMEZ — dönüş içeriğin içindedir

Oyun içi belirti: *"A/D'ye basınca ya da kamerayı çevirince kayıyorum, kendi
kendine 180° dönüyor."*

Sebep: vanilla'nın dönüş klibinde **dönüşün kendisi animasyonun içindedir** —
gövde dönüşe yatar, ayaklar çapraz basar. Düz yürüyüş içeriğine `Track 6`
rotasyonu **cıvatalamak** çalışmaz: ped döner ama bacaklar dönüş yürüyüşü
yapmaz (→ kayma), ve klibe gömülü tam açı ne ise oyunca döner.

**Kural: `Track 6`'sı birim olmayan klip üretme.** Dönüş gerekiyorsa dönüş
içeriği de üretilmeli. Aksi hâlde o klipler `clipItems`'tan çıkarılıp vanilla
fallback'ine bırakılır — sözlükte kalmaları zararsızdır, bildirilmeyen klip
aranmaz. Bu proje 66 klibin 32'sini bildirip 34'ünü vanilla'ya bıraktı.

### Bir turu boşa harcayan yanlış teşhis

Önce "çözücü bu kliplerde fazla biriktirmiş, `run_turn_l3` 419°/s imkânsız"
dedim. **Yanlıştı.** Kare başı adımlar birebir düzgün çıktı (`run_turn_l2` her
karede tam +4.0°, atlanan kare 0) — 419°/s gerçek vanilla değeri. Açı doğruydu,
sorun **içerikteydi**.

Ders: "bu sayı bana mantıksız geliyor" bir ölçüm değildir. Toplam şüpheliyse
**kare başına dağılıma bak** — düzgün mü, sıçramalı mı. Düzgünse toplam doğrudur.

## 3.79 ⛔ SIRADAKİ İŞ — tek master animasyon (klipler arası mover sürekliliği)

**Belirti:** ped **her dönüşte** (fare ya da klavye, yön fark etmez) anlık
duruyor; hız 0.02–0.16'ya düşüp geri geliyor.

**Eleme ile bulundu.** Sırayla çözülüp belirtinin devam ettiği görüldü:
kuyruk (§3.77), nicemleme (§3.76), sözleşme (§3.71), dönüş mover'ı (§3.78),
döngü kısaltma (aşağıda). Nicemleme düzeltmesi sonrası hızlar sürekli hâle
geldi (0.42/0.92/1.21… ve sabit yürüyüş tam 1.74) ama donma aynen kaldı.

**KESİN İMZA — donma sonrası sıçrama.** Ölçüldü:

```
1.78s 1.74 | 1.90s 0.00 | 2.00s 0.03 | 2.11s 32.11 | 2.21s 1.06
```

**32 m/s.** Bu bir yavaşlama değil, **biriktirip boşaltma**: motor harmanlama
boyunca sıfır fark çıkarıyor (ped duruyor), harman bitince konum bir anda
yerine oturuyor ve tek karede devasa fark okunuyor. Konum süreksizliğinin
imzası budur; başka hiçbir sebep hem sıfırı hem 32'yi aynı anda üretmez.

Sorun mesafenin BÜYÜKLÜĞÜ değil, **sıfırdan başlaması**. Bu yüzden döngü
kısaltma (genliği 3.4 kat düşürdü) mekanizmayı ortadan kaldırmadı.

**Kalan tek sebep:** bizde her klibin mover'ı **kendi sıfırından** başlayan
bir konum rampası. `walk` 6 m'ye ulaşmışken dönüş klibi 0'dan başlıyor; motor
harmanlarken konumları da harmanlıyor, çıkan fark negatife düşüyor ve hız
sıfırlanıyor. Dönmek = klip geçişi, o yüzden **her dönüşte** oluyor.

Vanilla'da imkânsız: 66 klibin hepsi **tek master animasyonu** paylaşır ve
mover konumu klipler arasında **kesintisiz** akar.

### ✅ HİPOTEZ SINANDI — mutlak konum ÖNEMLİ

Tek master planı "motor harmanlarken mover konumlarını da harmanlıyor"
varsayımına dayanıyordu. Yanlışsa (motor pencere başına normalize ediyorsa)
koca yeniden yapı hiçbir şey değiştirmezdi.

**Sınav:** `walk` klibinin `Track 5.Y` tabanına **+100 m** ekle, başka hiçbir
şeye dokunma. Deltalar, aralık (4.34 m), kuantum (0.00003), süre — hepsi aynı
kalır. Değişen tek şey mutlak konum.

| | ofsetsiz | +100 m |
|---|---|---|
| dip derinliği | **0.02** | **0.83** |
| dipten çıkış | 0.04 → 0.80 → 1.47 | 1.11 → 1.55 |
| 1.736'ya ulaşma | 0.57 sn | **1.00 sn** |
| başlangıç rampası | 0.42 → 0.82 → 1.19 | 0.69 → 0.71 → 0.78 |

Normalize etseydi **hiçbiri değişmezdi**. Her eksende değişti →
**mutlak konum önemli, tek master doğru yol.**

**İşaret de yön veriyor:** `walk`'ı İLERİ taşımak dipi **sığlaştırdı**. Şu an
`wstart` 3.4 m'de biterken `walk` 0'dan başlıyor — harmanda konum **geriye**
çekiliyor ve hız sıfırlanıyor. Tek master'da `walk` doğal olarak `wstart`'ın
bittiği yerden devam edecek, yani +100 testinin faydalı yönüyle aynı tarafta.

(Sınav geri alındı: dip sığlaştı ama hızlanma 0.57 → 1.00 sn'ye çıktı.)

### Denendi, ÇÜRÜDÜ — klip penceresini kuyruğa uzatmak

Hipotez: dip, motor pencere sonunda son kareyi tekrar ettiği için o klibin
mover farkının **sıfır** olmasından geliyor; pencereyi kuyruğa uzatırsak mover
harman boyunca akar.

44 döngüsüz klibin penceresi 0.5 sn uzatıldı. **Sonuç: donma kaybolmadı, yer
değiştirdi** — 1.90 sn'den 2.25 sn'ye, yani uzatma kadar ötelendi.

Bu, dipin pencerenin **sonuna bağlı** olduğunu kanıtlar (hipotezin yeri
doğruydu) ama çözümü çürütür: uzatmak yeni bir son yaratır, sorun oraya taşınır.
Klibin bir sonu olduğu sürece böyledir. **Geri alındı** (tek etkisi durma
klibini 1.07 → 1.57 sn uzatmaktı).

**Ders:** bir belirtinin nerede olduğunu bulmak, onu nasıl kaldıracağını
bulmak değildir. Belirti bir sınıra bağlıysa, sınırı taşımak değil **sınırın
davranışını** değiştirmek gerekir.

### Ara adım (yapıldı) — döngü kliplerini vanilla uzunluğuna çek

Hatanın büyüklüğü iki klibin o andaki **konum farkıyla** orantılıdır. Döngü
kliplerimiz vanilla'dan çok daha uzundu ve çok daha fazla konum biriktiriyordu:

| klip | bizim | vanilla | biriken konum |
|---|---|---|---|
| `walk` | 7.97 sn | 2.10 sn | 14.76 → **4.34 m** |
| `run` | 3.57 sn | 1.33 sn | 21.02 → **8.72 m** |
| `sprint` | 3.57 sn | 1.07 sn | 28.94 → **12.00 m** |
| `idle` | 9.97 sn | 6.67 sn | — |

Kısaltma döngü klibinde güvenlidir (içerik zaten çevrimsel; tam sayıda çevrim
bırakılırsa kapanır) ve zaten vanilla ile hizalıyor. **Tam çözüm değil**,
hatanın genliğini ~3.4 kat düşürür.

**Kırpma nicemleme tohumunu da siler** — tohumu kırpmadan sonra yeniden koy,
yoksa kuantum tekrar kabalaşır (§3.76).

### Yapılacak (asıl çözüm)

66 klibi tek bir uzun animasyona ardışık diz, mover konumunu klipten klibe
**kümülatif** yaz, her klibi o animasyonun bir zaman penceresi olarak tanımla.

**Hat da değişmeli:** `make_animlist.py` klip↔animasyon eşlemesini KONUMSAL
yapıyor (klip[i] ↔ animasyon[i]). Tek animasyonda hepsi `animasyon[0]`'a
düşmeli — `--map` ile açıkça verilmeli, yoksa 66 klip 66 ayrı animasyon arar
ve sessizce yanlış eşleşir.

**Dikkat — bu yüzden ayrı animasyona geçilmişti:** aynı animasyondaki ikinci
pencere, birincinin biriktirdiği `Track 6` yaw'ı yüzünden **yana yürür**.
Çözüm: `Track 6`'yı kümülatif bırakma; her pencerenin başında o pencerenin
kendi başlangıç yönüne dön — yani yaw'ı pencere içinde göreli tut, konumu
(`Track 5`) kümülatif tut. Vanilla take sınırında sıfırlıyor; hangi sınırların
sıfırlama noktası olduğu `ycd_mover.py`'nin sıçrama taramasıyla ölçülebilir.

## 4. Hâlâ açık tek iş

**`SKEL_ROOT` `Track 0` yanal salınım.** Vanilla walk penceresinde ölçüldü:
`x` genlik 0.0763 (orta +0.0022), `y` genlik 0.0754 (orta −0.0253); run
`x` 0.0555, `y` 0.0836. Bizde x/y genliği **0**, z 0.0369 var.

Yapılmadı çünkü **fazı güvenilir çıkmadı**: `y` tepeleri her ayak temasına
oturuyor (faz farkı ≤0.005, temiz) ama `x` 12 adımda **7 düzensiz** tepe
veriyor. Kemik yerel eksenlerinin dünya eksenleriyle hizası doğrulanmadan
yazmak ayakların yere basmasını bozma riski taşıyor — o davranış çok turda
kazanıldı. Yapılacaksa oyun içi A/B testiyle, **tek başına** yapılmalı.

## 5. Savepoint'ler

| klasör | durum |
|---|---|
| `_yedek\2026-08-04_calisan-yuruyus\` | 6 klip bizim, kalan 60 vanilla |
| `_yedek\2026-08-04_66klip\` | **66 klibin tamamı bizim** + Tags/Properties/Spine3 |

İkisinde de `GERI-YUKLEME.md` içinde tek bloklu geri dönüş komutları var.
