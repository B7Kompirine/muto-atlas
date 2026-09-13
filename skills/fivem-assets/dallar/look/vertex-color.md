# Vertex color — iç mekân ambient, kanalların ölçülmüş anlamı, "boyanmamış beyaz", bucket kuralı

**Ne zaman okunur:** kendi modelin iç mekânda parlıyor/aydınlık; `Color 1` kanalları ne; R/G hedef değerleri; decal'da yeşillik.
**When to read:** interior ambient shading through vertex colours; the measured meaning of each channel; fake bounce light.
**Kaynak:** `isik.md` vertex color bölümleri + 'iç mekân kuralı' (morg_vanilla ölçümü, 2026-08) · **Ölçüm:** facility 66 dosya, vault, v_coroner kabuğu; 105 dosya geri okumayla
**Önce:** `_dal.md` · gövde › `govde/arac-tuzaklari.md` §1-2 · vanilla iç mekân bantları `dallar/map/vanilla-ic-mekan.md` §4

---

### ⛔ İÇ MEKÂN KURALI: vanilla `R = 0` yazar — Blender turu bunu BOZAR

Bu, ölçülmüş ve bir kez çok pahalıya mal olmuş bir kuraldır.

**Vanilla iç mekân (MLO) yüzeylerinde vertex color 0'ın R kanalı TAM 0'dır.**
MLO'yu dış dünyadan yalıtan şey budur: R=0 → gökyüzü/doğal ortam katmanı
kapalı → iç mekân dışarıdaki hava, güneş ve gökyüzü yansımasından etkilenmez.

Blender import/export turu bu sıfırı korumaz. Ölçüldü (v_coroner morgu,
214 model):

| | vanilla | Blender turundan sonra |
|---|---|---|
| `v_med_cor_offglass` | **0** / 153.6 / 38 | **118.4** / 135.8 / 109 |
| `v_ilev_cor_doorglassa` | **0** / 90.7 / 121.2 | **53.2** / 107 / 134.4 |
| `v_2_ala_mesh_delta` | **0** / 120 / 152 | **120.1** / 124.8 / 154.6 |

**Belirti — ve teşhisi en zor yanı bu:** kullanıcı "harita aşırı ıslak, her
yer deli gibi yansıyor" der. Işıklandırma ayarı gibi görünür, ama değildir.
Doğal ortam katmanı açıldığı için iç mekân dışarının ışığını ve gökyüzü
yansımasını alır.

⛔ **Bu belirtiyi kovalarken şunların HEPSİ yanlış adrestir** (hepsi ayrı ayrı
ölçüldü ve hepsi vanilla bandında çıktı — turlarca kaybettirdi):
spec dokusu parlaklığı · spec dokusundaki parlak benek oranı · normal
haritası gücü · `specularintensitymult` / `specularfalloffmult` /
`specularfresnel` / `bumpiness` / `reflectivepower` · `environmentsampler`
bağı · spec kanalına diffuse bağlanması (vanilla bunu bizden ÇOK yapar) ·
üretilmiş kirli dokular · oda/portal bayrakları · hava döngüsü (yağmur).

**Doğru ölçüm ve düzeltme:** modelin vertex color 0 R ortalamasını vanilla
karşılığıyla kıyasla; vanilla'da `< 5` ise bizde de `0` olmalı.

```powershell
# offset'i sabit varsayma - deklarasyondan al
$ofs = $vd.Info.GetComponentOffset([CodeWalker.GameFiles.VertexComponentType]::Colour0)
for($i=0; $i -lt $vd.VertexCount; $i++){ $vd.VertexBytes[$i*$vd.VertexStride+$ofs] = [byte]0 }
```

Düzeltmeden sonra ölçüt: vertex renk ortalaması vanilla ile eşleşmeli
(ölçülen vaka: 64.5 → **61.7**, vanilla 60.8).

⚠️ **G kanalını körlemesine sıfırlama** — o yapay iç mekân katmanını kapatır
ve odayı zifiri karanlık yapar. Yalnız R.

#### Bu kural KAPIYA çevrilmelidir, hatırlamaya bırakılmaz

Bu bozulma **her Blender export'unda yeniden oluşur**. Elle hatırlamaya
bırakılırsa her turda kullanıcı oyuna girip "yine ıslak" demek zorunda kalır —
bu yaşandı, defalarca. Doğrusu dağıtımı tek bir kapılı betiğe bağlamaktır:

```
<dagitim_betigi> -Kaynak <klasor> [-Deneme]      (ornek hat; betik depoda yok)
  1) vertex color R -> 0   (otomatik düzeltir, hatırlamaya gerek yok)
  2) doku kapısı           (referans edilen her doku çözülüyor mu)
  3) collision kapısı      (vanilla'da bound varsa bizde de var mı)
  4) yapısal kapı          (physics + geometri + R son kontrol)
  → biri kalırsa stream/'e HİÇ DOKUNMAZ
```

⛔ **Kapıyı yazmak yetmez, NEGATİF TESTİNİ de yap.** Bir modelin R'sini bilerek
128 yapıp betiğin düzelttiğini gör. Kanıtlanmamış kapı, kapı değildir —
"0 dosya denetledim, geçti" diyen bir kapı bu projede bir kez yaşandı.

⛔ Dosya filtresinde `Get-ChildItem -Include *.ydr,*.yft -Recurse` KULLANMA:
`.ycd/.ytd/.ytyp`'yi de yakalar ve "geometri yok" diye yanlış alarm verir.
`-File | Where-Object { $_.Extension -in '.ydr','.yft' }` kullan.

## Vertex color kanalları — ÖLÇÜLDÜ ve önceki notum YANLIŞTI

⛔ **Bu dosyada daha önce "vertex color 0'ın .r ve .g kanallarıyla kapılır
(natural/artificial)" yazıyordu. YANLIŞ.** Sollumz'un kendi dokümanı
(`docs.sollumz.org/2.6/tutorials/creating-interiors/texturing`) ve vanilla
ölçümü şunu söylüyor — `Color 1` (= `Colour0`, CORNER domain, BYTE_COLOR):

| kanal | ne yapar | vanilla kullanımı |
|---|---|---|
| **R** | **gece ambient occlusion.** Yükseldikçe gece KARARIR. | gece lambası olmayan yüzeylerde çoğunlukla **255**'e dayanır |
| **G** | **yapay ışık.** 255 = kendinden ışıklı etki. | lamba/ışık kaynağı yakınındaki yüzeylerde yükseltilir |
| **B** | **ay ışığı yansıması.** Yükseldikçe dış ışığı daha çok alır. | R* bunu sık kullanır ki mekân tamamen kararmasın |

**Yükseklik kuralı (kullanıcıdan, vanilla'da doğrulandı):** kabuk alt yarısı
yeşil→koyu yeşil, üst yarısı mavi→koyu mavi; dışarıya açılan pencere/kapı
çevrelerinde ve güneşin vuracağı yerlerde kırmızı-sarı. İki katlı iç mekânda
birinci kat ağırlıklı yeşil, ikinci kat ağırlıklı mavi.

Ölçüm — `v_57_franklin_int` (vanilla, tek kat), `Colour0` offset 24, RGBA:

| z bandı | R | G | **B** |
|---|---|---|---|
| −1.50…−1.11 (zemin) | 49 | 116 | **4** |
| −1.11…−0.72 | 174 | 132 | **0** |
| −0.32…0.07 | 82 | 108 | **41** |
| 0.07…0.46 | 220 | 89 | **255** |
| 1.25…1.64 (tavan) | 94 | 76 | **255** |

Mavi zeminde ~0, tavanda 255 — gradyan gerçek.

⚠️ **Vanilla iç mekân "karanlık" demek değildir.** `v_coroner` morgu ölçüldü:
R ≈ 0–29 (gece AO neredeyse yok), B ≈ 234–255 (ay ışığını sonuna kadar alır).
Yani o iç mekân **aydınlık** olacak şekilde boyanmış. Karanlık/horror tema
isteniyorsa timecycle tek başına yetmez; **vertex color'ı da değiştirmek
gerekir** (R yukarı, B aşağı).

### ⛔ CodeWalker'da renk offset'ini BULMANIN doğru yolu

Bu bir turda ÜÇ KEZ yanlış offset okundu. Sebepleri sırayla:

1. `[CodeWalker.GameFiles.VertexComponentType]::Colour0` **diye bir üye YOK**
   (gerçek üyeler: `Nothing, Half2, Float, Half4, FloatUnk, Float2, Float3,
   Float4, UByte4, Colour, Dec3N, Unk1..Unk5`). PowerShell olmayan statik
   üyede **hata vermez, `$null` döner**; `GetComponentOffset($null)` → **0**,
   yani POZİSYON okunur. (§ "aracın göstermemesi yok olduğu anlamına gelmez")
2. `GetComponentOffset(Colour)` **36** verdi — o **Tangent0**'ın offset'i.
   Bu fonksiyon semantik yuvayı değil veri tipini arıyor.
3. Renk bileşeni olmayan mesh'te de bir sayı döner (stride'a eşit) — "yok"
   durumunu ayırt etmez.

**Doğrusu bildirimden hesaplamaktır.** `Info.Flags` hangi semantik yuvaların
var olduğunu bit bit söyler, `Info.Types` yuva başına 4 bit tip verir:

```
yuva sirasi: Position BlendWeights BlendIndices Normal Colour0 Colour1
             TexCoord0..7 Tangent0 Tangent1 Binormal0 Binormal1
tip boyutu : Nothing 0 · Half2/Float/UByte4/Colour/Dec3N 4 · Half4/Float2 8
             Float3 12 · Float4 16
```

**Ölçüt: hesaplanan toplam = `VertexStride`.** Tutmuyorsa çözüm yanlıştır.
`DefaultEx` (Flags=16473) için: Position 0 · Normal 12 · **Colour0 24** ·
TexCoord0 28 · Tangent0 36, toplam 52 = stride ✓

**Bayt sırası RGBA** (Blender'ın Sollumz çözümüyle çapraz doğrulandı:
ikili `[12,56,255,240]` ↔ Blender `R=12 G=56 B=255 A=240`).

En güvenli yol: mümkünse ölçümü **Blender'da** `color_attributes["Color 1"]`
üzerinden yap — Sollumz zaten doğru çözüyor ve boyama da orada yapılacak.

### Vertex color — ÖLÇÜLMÜŞ HEDEF DEĞERLER (vanilla iç mekânlar)

⚠️ **Sollumz dokümanının R açıklaması yanıltıcı.** "R gece AO'sudur, çoğunlukla
255'e dayanır ki çok kararsın" diyor; ölçüm bunun tersini gösteriyor:

| iç mekân | R | G |
|---|---|---|
| `v_55_shell` (işkence odası, **çok karanlık**) | 0–20 | 1–22 |
| `v_44_shell` (Michael'ın evi, **aydınlık**) | 71–132 | 58–167 |
| `v_57_franklin_int` (aydınlık ev) | 49–220 | 76–132 |
| `v_2_*` (morg, vanilla) | 0–29 | 0–92 |

**Yüksek R/G = daha aydınlık.** Karanlık/horror tema istiyorsan R ve G düşük
kalmalı (0–25 bandı).

**MAVİ dikey gradyanı evrenseldir** — normalize yükseklikte (0%=zemin, 100%=tavan):

| model | 10% | 20% | 40% | 50% | 60% | 70% | 90% | 100% |
|---|---|---|---|---|---|---|---|---|
| `v_55` karanlık | 0 | 0 | 0 | 0 | 66 | 184 | 255 | 208 |
| `v_44` aydınlık | 5 | 0 | 22 | 2 | 63 | 255 | 255 | 255 |
| `v_57` franklin | 4 | 0 | 43 | 17 | 255 | 206 | 255 | 255 |

**Kural: alt %50 → B ≈ 0–40 · geçiş %50–60 · üst %40 → B ≈ 200–255.**
Vertex paint görünümündeki "alt yeşil / üst mavi" tam olarak budur:
altta B=0 + G>0 yeşil okunur, üstte B=255 mavi okunur.

Diğer ölçülmüş bağlar:

- **`Colour1` (Sollumz "Color 2") iç mekân kabuklarında HİÇ kullanılmıyor**
  (`v_55`, `v_44`, `v_57`, morg — dördünde de 0 geometri). Yalnız `Color 1`.
- **Alfa kabuklarda 255.** 255'ten küçük alfa yalnız decal/overlay mesh'lerinde
  görülür (harman katsayısı): morg `over_decal` 76, `bsnt_shell` yer yer 127.
- **Vertex color'ı okumayan shader YOK.** 60 vanilla iç mekân dosyasında,
  250+ geometride, her shader'ın her geometrisinde `Colour0` bildirimi var —
  tek istisna yok. Bildirimde `Colour0` varsa shader onu okuyor demektir;
  ayrıca "bu shader boyamayı yok sayar mı" diye sormaya gerek yok.
- Morg tarafı: 994 geometrinin **tamamında** `Colour0` var, hepsi boyanabilir.

---

## Vertex color: "boyanmamış beyaz" tespiti ve kanalların ölçülmüş anlamı

**Ölçüm hattı** (1.626 geometri / 4 iç mekân, bu turda kuruldu):
`extract_asset.ps1 -Pattern '*.ydr' -PathFilter '<iç mekân>.rpf'` → CodeWalker
`YdrFile` → `VertexBuffer.Info.GetComponentOffset(4)`.

### Beş sessiz tuzak — beşi de bu turda yaşandı

1. ⛔ **`GetComponentOffset` SLOT İNDEKSİ alır, tip enum'u değil.**
   `Colour0` = **slot 4**. `VertexComponentType.Colour` (=9) bir *tip*tir;
   onu indeks sanıp geçirmek slot 9'u okur ve **offset 36** (Tangent0) döner.
   Slot sırası: 0 Position · 1 BlendWeights · 2 BlendIndices · 3 Normal ·
   **4 Colour0** · 5 Colour1 · 6-13 TexCoord0-7 · 14-15 Tangent0-1.
   Doğrulama: `DefaultEx` (Flags=16473) → Colour0 offset **24**, stride 52.
   Varlık denetimi `Flags & 16` (Colour0), `Flags & 32` (Colour1).
2. ⛔ **`VertexBuffer.Data1` byte[] DEĞİL, bir `VertexData` nesnesidir.**
   Baytlar `Data1.VertexBytes` içindedir. `$data.Length` `$null` döner,
   `$p+3 -ge $null` karşılaştırması `break` eder ve **döngü sessizce boşalır**:
   0 satır, 0 hata. `Data1` ve `Data2` **aynı nesnedir** (ReferenceEquals
   True) — birini yamalamak yeter.
3. ⛔ **Shader parametresinin `Data`'sı `System.Numerics.Vector4` DEĞİLDİR.**
   `-is [System.Numerics.Vector4]` her parametreyi sessizce eler ve tablo
   boş çıkar. Tip adına bakma, alana bak: `$dv.PSObject.Properties['X']`.
   (Teşhis çıktısında `Data=Vector4` görmek yanıltıcıdır — o `ToString()`
   değil, `GetType().Name`'i yazan ELSE dalıdır.)
4. ⛔ **Python'un Windows'ta yazdığı liste dosyası CRLF taşır**; bash
   `while read` ile okunan ada `\r` yapışır ve PowerShell
   *"Illegal characters in path"* der. `tr -d '\r'`.
5. ⛔ **`| tee x | head -N` boruyu erken kapatır**, log dosyası yarıda kalır
   ve "8 dosya işlendi" gibi **yanlış bir başarı sayısı** okursun. Dosya
   gerçekten yamalandı mı, **yeniden ölçerek** doğrula.

### Kanalların anlamı — ölçüm, doktrin değil

| iç mekân | R | G | B | "boyanmamış beyaz" (R=G>200) |
|---|---:|---:|---:|---:|
| `xm_x17dlc_int_facility` (loş, tamamen gömülü) | **0.0** | 109.7 | 187.6 | **%0.0** |
| `ch_dlc_int_09_ch` (kasa — kapalı **ama parlak**) | 186.2 | 205.3 | 135.5 | **%69.9** |
| `v_coroner` bodrum kabuğu (vanilla) | 12.7 | 33.8 | — | — |

⚠️ **"Kapalı iç mekânda R sıfır olmalı" diye bir kural YOKTUR** — vault bunu
çürütür: yeraltında, penceresiz, ve geometrisinin %70'i R=G=255. Fark
aydınlatma yönüdür, kapalılık değil. R **loş** mekânlarda sıfırlanır:
facility'nin **66 dosyasının, dört alt grubunun (shell/detail/blend/diğer)
istisnasız hepsinde R = 0.0**; G ise 37-153 arasında serbestçe değişir.
Yani **R yön kararıdır, G sanatsal değerdir** — G'yi tek sayıya çakma.

**`R == G` ve ikisi de >200 ⇒ mesh hiç boyanmamış** (Blender/Sollumz
varsayılan beyazı). Ayırt edici olan eşitliktir: gerçekten boyanmış bir
mesh'te R ve G bağımsızdır. Kendi eklediğin modelleri bu testle tara —
ölçüldü: kendi `muto_*` modellerimizin **9'undan 8'i** R=G=225-255'te
duruyordu, oysa üstünde durdukları kabuk R=12.7 idi. Kusur "R yüksek"
değil, **modelin konulduğu haritayla uyuşmaması**.

**Hedef seçimi:** zemin dekalı **altında yattığı mesh'in** değerini alır
(burada `v_2_bsnt_shell` → R=12 G=47). Obje/prop için G'ye **dokunma**,
yalnız R'yi kabuk seviyesine çek — okunabilirlik korunur. Sonuç ölçüldü:
R 83.0 → 16.3, boyanmamış oran %19.7 → **%0.0**, G 102.4 → 94.9 (neredeyse
sabit), B hiç değişmedi.

### Specular tarafı: bakmadan "kısayım" deme

Aynı ölçümde medyanlar — **bizimki zaten en karanlık vanilla referansın
çok altındaydı**, oradan alınacak kazanç yoktu:

| param | vault | facility | bizim |
|---|---:|---:|---:|
| `specularintensitymult` | 1.000 | 0.800 | **0.071** |
| `specularfresnel` | 0.920 | 0.950 | 0.750 |
| `bumpiness` | 1.000 | 0.800 | 0.700 |
| `wetnessmultiplier` | 1.000 | 1.000 | **0.000** |
| `emissivemultiplier` | 8.000 | 6.000 | 0.900 |
| yansıtıcı shader (vertex payı) | %1.7 | %7.8 | %7.7 |

Yansıtıcı shader oranımız facility ile birebir aynı (%7.7 / %7.8) — yani
"çok fazla yansıtıcı materyal var" teşhisi de ölçüme dayanmıyordu.

### MLO'ya eklediğin YÜZEY, prop bayrağı almamalı

⛔ **`Dont Render In Reflections` (bit24, 16777216) prop için normaldir,
yüzey için kusurdur.** Ölçüldü (`v_coroner`): 583 vanilla entity'nin
**%61,6'sı `18350080`** taşıyor — yani Rockstar'ın bu MLO'daki prop
standardı budur, anormal değil. **Ama kabuklarını ayırıyor:**
`v_2_bsnt_shell` / `v_2_strs_shell` / `v_2_tpoff_shell` → **`1572864`**
(Cast Static + Cast Dynamic, yansımada **görünür**).

Ayrımı `limbo` odasının `AttachedObjects`'i gösteriyor: vanilla oraya
yalnız 3 kabuk + 3 `v_2_shadowmap*` koymuş. Shadowmap proxy'leri
`22544384` = kabuk bayrağı + **`Disable shadow`** + `Dont Render In
Reflections` — yani sadece gölge üretmek için var olan görünmez yardımcılar.

**Sonuç:** MLO'ya kendi tavanını/zeminini/kabuğunu eklerken bayrağı
komşu **prop'tan değil, komşu KABUKTAN** kopyala. Yanlışının iki ayrı
belirtisi var ve ikisi de "yansıma bozuk" diye okunur:

- tavan yansımada yoksa → zemin **boşluğu/gökyüzünü** yansıtır;
- zemin kaplaman yansımada yoksa → doğrudan bakışta kirli zemin,
  **yansımada tertemiz vanilla fayans** görünür.

Aynı hatanın üçüncü yüzü daha önce ölçülmüştü: `18350080` taşıyan
kabuk **hiç yüklenmemişti** (arketipin `textureDictionary`'si de 0'dı).
Bir kez bulup **yalnız o objede** düzeltmek yetmez — `limbo`'ya ve kendi
eklediğin tüm entity'lere **süpürme** yap.

Denetim (tek satır): `limbo`'nun `AttachedObjects`'ini dök, senin
eklediklerinin bayrağı vanilla kabuklarınkiyle aynı mı bak.

### ⛔ Vertex color karartmasi YALNIZ bucket 0'a uygulanir

Onceki bolumdeki `R == G > 200 => boyanmamis` sezgisi **yalniz
`RenderBucket == 0`** (opak, isikli yuzey) icin gecerlidir. Orada RGB uc
ayri **isik maskesidir** ve asimetri normaldir (vanilla kabuk 12/32/42,
facility 0/110/188).

**Opak olmayan bucket'ta (1 cam / 2 decal / 3 / 7) RGB carpan gibi davranir**
ve R'yi dusurup G'yi birakmak **hue kaydirir**. Olculdu: zemin dekali
227/227 -> 12/47 yapilinca oran 1:1'den **1:3,9**'a cikti ve zemin yesile
dondu. Diger tum yesil kaynagi elendi: atlas dokusu rust (R=54 G=12 B=8,
10x10 izgarada yesil baskin hucre **0**), haritadaki **217 isigin hepsi**
sicak kirmizi-turuncu (255,76,46).

⚠️ "Decal'da G=R olmalidir" da **evrensel degil**: bu haritanin
vanilla'sinda oyle (`decal_dirt` 31/31, `decal_normal_only` 158/158,
`normal_decal` 222/222 -- ucunde de `G-R = 0,0`), ama facility'de bucket
2'de `|G-R| = 144` ve G=R orani **%0**. Olcut daima **haritanin kendi
vanilla'si**, baska bir DLC degil.

Yanlislikla dokunduysan **geometri bazinda** geri al, dosya bazinda degil --
opak kisimdaki kazanc korunmali. Yedekle canli dosyanin geometri sirasi
ayni kalir (yalniz vertex baytlari degistiyse), `RenderBucket != 0` olan
geometrilerin Colour0 R/G/B baytlarini kopyalamak yeterlidir.

⛔ Ayrica: **PowerShell degiskenleri buyuk/kucuk harf duyarsizdir.** Izgara
boyutu `$N` ile dongu sayaci `$n` ayni degiskendir; ikinci dosyada `$N`
sifirlandi ve "0 yesil hucre" diye **yanlis bir olcum** uretti.
