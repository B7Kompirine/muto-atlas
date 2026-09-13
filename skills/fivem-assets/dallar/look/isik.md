# Işık — prop ışığını oku/düzenle/geri yaz, TimeFlags, Flashiness, gobo (projeksiyon)

**Ne zaman okunur:** "lambam sönük / yanmıyor / titremiyor", ışık ekle, koni geniş, projeksiyonlu ışık (gobo), Blender'dan ışık export'u.
**When to read:** read, edit or write back a prop's light; TimeFlags, Flashiness, cone angle, corona, culling plane.
**Kaynak:** `isik.md` okuma/gobo/flicker/export bölümleri · `decal.md` §4, §9, Flashiness · eski `/look` (2026-08/09) · **Ölçüm:** 72.539 vanilla gömülü ışık (`lights.tsv.gz`); 36 projeksiyonlu ışıklık bir set oyunda
**Önce:** `_dal.md` · gövde › `govde/arac-tuzaklari.md` §1-2

---



Kullanıcının sorgusu: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `scripts/assetdb.py`'yi içeren muto-atlas klasörü).

Işıkla ilgili **her** iş bu komuttan geçer: "lambam çok sönük", "ışık
yanmıyor", "koni çok geniş", "prop'uma ışık ekle", "bu ışık hangi saatte
yanar". Kullanıcı `/look` yazmasa bile ışık konusu geçtiğinde bunu kullan.

## Sırayla

**1. Önce OKU — sihirli sayıyı kopyalama, çöz.**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya>
```

`TimeFlags 14680095` bir sayı değil "21:00–05:00 arası yanar" demektir.
Çıktıyı kullanıcıya bir iki cümleyle özetle: kaç ışık, tipi, hangi saatler,
uyarı var mı.

**2. Değeri ÖLÇÜLMÜŞ ARALIĞA göre öner.**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light --table
```

72.539 vanilla ışıktan hesaplanan `p05 / medyan / p95` bandı. Bir değer
önerirken "bence 20 olsun" deme — o alanın vanilla medyanını ve bandını
söyle, önerin bandın neresine düşüyor belirt. Katman kurulu değilse
**aralık uydurma**, referans veremediğini söyle.

**3. Geri yaz ve DOĞRULA.**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya> --apply duzenleme.json
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya> --set 0.Intensity=8 --set 0.ConeOuterAngle=35
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya> --add
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya> --remove 1
```

Her yazma orijinali `<ad>.yedek` olarak saklar ve sonucu **geri okuyarak**
doğrular. Doğrulama geçmezse dosya değişmez.

## Karanlık şikâyeti üç katmanlıdır — sırayla bak

Cevap çoğu zaman prop'un ışığında değil:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" cycle w_clear --hour 20   # 1. taban hava
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" timecycle --mlo <ytyp>    # 2. odanın modifier'ı
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya>             # 3. prop'un ışığı
```

## Sonucu sunarken

- **Her sihirli sayıyı çöz.** `TimeFlags`, `Flags` — sayıyı tekrarlama,
  ne anlama geldiğini söyle (`assetdb.py flags <sayı>`).
- **Işık kemiğe bağlıdır.** `BoneId` sıfırdan farklıysa ışık modelin
  orijininde değil, o kemiktedir; konumu ona göre anlat.
- **Saat uyuşmazlığını söyle.** Kullanıcı "yanmıyor" diyorsa önce
  `TimeFlags`'e bak — çoğu vakada ışık sağlamdır, saat yanlıştır.
- `cycle` katmanı kurulu değilse `build_cycle.ps1`'i öner — **uydurma**.

Tam matematik, üç katmanlı timecycle ve sessiz hata kataloğu:
`isik-matematigi.md`


---

## Ölçülmüş, tahmin edilmemiş

Işıkla ilgili **her** iş burada başlar.

```bash
assetdb.py light prop_lamp.ydr              # oku ve ÇÖZ (sihirli sayıları aç)
assetdb.py light prop_lamp.ydr --table      # 72.539 vanilla ışığın ölçülmüş bandı
assetdb.py light prop_lamp.ydr --apply duzenleme.json
assetdb.py light prop_lamp.ydr --set 0.Intensity=8 --set 0.ConeOuterAngle=35
assetdb.py light prop_lamp.ydr --add | --remove 1
assetdb.py cycle w_clear --hour 20          # hava cycle'ının taban katmanı
assetdb.py timecycle int_hospital_dark      # odanın modifier'ı
```

Geri yazma `res_to_xml → XML → xml_to_res` turudur ve her yazma **geri
okunarak** doğrulanır. Değer önerirken `--table`'nun ölçülmüş bandını kullan
(alan başına p05 / medyan / p95); katman kurulu değilse aralık **uydurma**.

Ölçülmüş, tahmin edilmemiş:

- **Işık kemiğe bağlıdır.** `prop_worklight_01a`'da `BoneId 41615` zincirde
  **1.737 m** yukarıdadır; kemik zinciri uygulanmazsa ışık yerde durur.
  `Position/Direction/Tangent` **kemik uzayındadır**, model orijininde değil.
- **`TimeFlags` bir sayı değil saat kümesidir.** `14680095` = 21:00–05:00;
  saat 20'de ışık **yanmaz**. "Yanmıyor" şikâyetinde ilk bakılacak yer budur —
  çoğu vakada ışık sağlamdır, saat yanlıştır.
- **Boyut geçerlilik ölçütü değildir** (RSC7 zlib'dir): 15.056 → 15.904 bayt
  aynı içeriktir. Tek ölçüt **geri okumadır**; `--apply` her zaman geri
  okur ve ışık sayısı tutmuyorsa yazmaz.

- **`Flashiness` (flicker) hiçbir yerde yazmaz**, 72.539 ışığın dağılımından
  okundu: **15** alarm · **17** tünel · **9** acil durum · **19** hasarlı gemi
  (68.036'sı 0). ⚠️ Adı "broken light" olan vanilla prop'un flashiness'i
  **0**'dır — GTA "kırık"ı modelle yapar, titremeyle değil.
- **Emissive panelin ışığı yoktur** — parlaklık `emissiveMultiplier`'dadır ve
  bir odadaki paneller **tek geometriyi paylaşır**; birini kırmak için
  geometriyi bölmek gerekir. Emissive geometri **titreyemez**.
- **Kendi timecycle modifier'ını `data_file 'TIMECYCLEMOD_FILE'` ile KAYDET** —
  kaydedilmezse oyun onu hiç aramaz. Paylaşılan vanilla modifier'a dokunma
  (`morgue_dark` 6 DLC'de tanımlı, hangisinin kazandığı veriden okunamaz).

Tam matematik + timecycle üç katmanı: `isik.md`
Işık/timecycle/emissive alan bulguları: `decal.md`

## Işığı okuma ve geri yazma — oyuna girmeden

```bash
assetdb.py light prop_lamp.ydr              # oku + sihirli sayıları çöz
assetdb.py light prop_lamp.ydr --apply duzenleme.json
assetdb.py light prop_lamp.ydr --set 0.Intensity=8 --add --remove 1
```

Hat iki parçadır ve ikisi de ölçüldü:

| parça | ne yapar | dosya |
|---|---|---|
| çözme | `.ydr/.yft` → mesh + kemik dünya matrisleri + 40 alanlı ışıklar | `light_sahne.py` |
| geri yazma | `res_to_xml → XML → xml_to_res`, sonra **geri okuma** | `light_edit.py` |

Ölçülmüş vanilla dağılımı `light.referans()` ile canlı gelir
(`data/lights.tsv.gz`; bu kurulumda 72.539 ışık / 4.476 dosya):
her sayısal alan için `p05 / medyan / p95 / min / maks`. Katman yoksa
**aralık uydurulmaz**, referans hiç sunulmaz.

### Üç sessiz bağ

- **Işık kemiğe bağlıdır.** `prop_worklight_01a` → `BoneId 41615`
  (`Worklight_01A_Bulb`), zincirde **1.737 m** yukarıda; ışığın kendi
  `Position`'ı (0, −0.015, 0.009) bunun **üstüne** biner → dünya
  (0, −0.102, 1.746). Kemik zinciri kurulmazsa ışık yerde durur ve
  "ışığım yanlış yerde" denir. Vertex'ler de `HasSkin=1` ise kemik
  uzayındadır (prop'ta ağırlık tek kemiğe %100, yani rijit).
- **`TimeFlags` bir sayı değil saat kümesidir.** `14680095` = `0xE0001F`
  → bit 0–4 ve 21–23 = **8 saat**, 21:00–05:00. Saat 20'de ışık **yanmaz**.
  Kullanıcı "ışığım yanmıyor" dediğinde ilk bakılacak yer ışığın kendisi
  değil, saattir. Bir önizleme bunu uygulamazsa araçta parlak görünür,
  oyunda karanlık çıkar.
- **Boyut geçerlilik ölçütü DEĞİLDİR.** Aynı içerik 15.056 → 15.904 bayt
  çıktı (RSC7 zlib). Tek ölçüt geri okumadır; `--apply` yazdıktan sonra
  dosyayı yeniden çözer, ışık sayısı tutmazsa hata verir ve orijinali
  `.yedek` olarak korur.

### Köken

Bağımsız bir uygulamadır. Matematik oyunun kendi shader dosyalarından
(`lighting_common.fxh`, `common.fxh`, `postfx.fx`) türetilmiş ve ölçümle
doğrulanmıştır; referans bantları kullanıcının kendi kurulumundan yerel olarak
hesaplanır ve dağıtılmaz (`data/` gitignore'lu). Herhangi bir üçüncü taraf
düzenleme aracının kodu, varlıkları, arayüzü, adları ya da markası **yoktur**.

### Bir önizleme kurarken — sınırı baştan söyle

Bu matematikle kurulan herhangi bir önizleme bir **render değildir**. Bilerek
dışarıda kalanlar: **doku** (albedo tek sayıdır), **korona sprite'ı**,
**hacimsel ışın**, deferred pass'in **SSAO/yansıması**. Cevapladığı soru
"ışık nereye ne kadar düşüyor"dur; "sahne birebir böyle görünecek" değil.

Gölgede de fark var: oyun sanal güneş konumundan **mesafe** saklar. Derinlik
haritasıyla kuran bir önizleme dersi koruyabilir (normal ofseti ağır işi
yapar, bias texel dünya boyutuna göre ölçeklenir) ama depolaması farklıdır.

Bu matematik bir kez ölçülerek doğrulandı (piksel okunarak, ekran
görüntüsüne bakılarak **değil**): saat 12 → `[107,109,110]`,
17 → `[93,95,96]`, 20 → `[14,19,32]`, 06 → `[20,30,38]` — gün boyunca
fiziksel olarak makul ilerleme.

---

## 4. IŞIK DÜZENLEME

Işıklar script'te değil **`.ydr`'nin kendi ışık dizisinde**. Modeli düzenleyip
`stream/` içine aynı adla koymak = override.

### İlk bakılacak yer: TimeFlags
`16777215` = 24/24 (her saat). Vanilla'da en sık ikinci değer `14680191`
= 21:00–07:00. **"Işık yanmıyor" şikâyetinin en sık sebebi saat penceresidir**,
ışığın kendisi değil.

### Flashiness — anlamı hiçbir yerde yazmıyor, dağılımdan okundu
72.539 vanilla ışık tarandı, **68.036'sı = 0** (sabit). Sıfır olmayanlar ve
onları kullanan modeller:

| Değer | Adet | Kullanan modeller (ipucu) |
|---|---|---|
| 15 | 1096 | `v_med_cor_alarmlight`, `xm_prop_x17_sub_alarm_lamp` — kırmızı 255,5,0 **alarm** |
| 17 | 693 | `cs2_30_tunnel_det_*` — tünel lambaları |
| 11/12/13 | ~1400 | kumarhane oyun salonu, sinema — döngüler |
| 9 | 344 | `prop_ld_alarm_alert`, `v_48_emerg_light_a` — **acil durum** |
| 19 | 172 | `gr_prop_damship_01a` (**hasarlı gemi**) |
| 20 | 39 | `ba_prop_battle_lights_fx_rige` — strobe |
| 14 | 22 | `v_73_elev_sec*` — asansör |

⚠️ **`h4_int_club_broken_light` ("kırık ışık") flashiness = 0.** Yani GTA
"kırık" görüntüsünü flashiness ile değil **modelle** yapıyor.

### Vanilla bandı (72.539 ışık)
`Intensity` p05 0.25 · medyan 6 · p95 32 — bandın dışı hata değil, **nadir** demek.

### Işık kemiğe bağlıdır
`Position` **kemik uzayındadır**, model orijininde değil. `BoneId=0` ise
objenin kendi uzayı (statik prop'ların çoğu böyle).

---

## ⛔ Tek Flashiness = sahte. Kırpışma TİP çeşitliliğiyle dağıtılır

GTA'da kırpışmanın **fazı ayarlanamaz**, yalnız **tipi** seçilir. Bütün
ışıklara aynı değeri vermek (ölçüldü: 232/232 `ELECTRIC`) hepsini aynı
desende yakıp söndürür ve senkron göründüğü için sahte durur.

Çözüm: her ışığa **konumundan türetilmiş deterministik bir hash** ile
havuzdan tip ata — komşu ışıklar farklı tip alır, periyotları farklı
olduğu için zamanla birbirinden ayrışırlar. Morgda kullanılan ağırlıklar:

`ELECTRIC 30` · `RANDOM 20` · `RANDOM_FLASHINESS 12` · **`CONSTANT 12`** ·
`ONCE_PER_SECOND 8` · `TWICE_PER_SECOND 7` · `THRESHOLD 6` · `CYCLE_1 3` ·
`CANDLE 2`

⛔ **Hepsini kırpıştırma.** Bir kısmı `CONSTANT` kalmazsa ortam disko olur;
bozuk tesis hissi çalışan ve bozuk ışıkların **karışımından** gelir.
Alarm lambaları havuza girmez, kendi tipi vardır (`ALARM`).

Betik depoda yok.

**İki PowerShell tuzağı burada da çıktı:**
- `(,19) * 30` ile ağırlıklı havuz kurulmaz — beklenen tekrarı üretmiyor
  (ölçüldü: ELECTRIC %30 yerine %0.9). Açık döngü kullan.
- `-bxor`/`-band` işaretsiz tipleri korumaz; ara sonuç Int64'e düşüp
  negatif olur ve `[uint64]`'e geri atarken patlar. Bit işlemi yerine
  djb2 + modulo.

## ⛔ "Flicker çalışmıyor" — önce `Intensity`'ye bak, `Flashiness`'e değil

Ölçüldü (morg): dağıtılmış **232 ışığın tamamı `Intensity = 0`**. Aynı
modellerin vanilla kopyalarında değerler **0.58 – 32** arasında. Yani
haritadaki bütün ışıklar ölüydü ve görünen aydınlık **tamamen emissive
materyalden** geliyordu.

Bu, `Flashiness`'in neden hiçbir şey yapmadığını tek başına açıklar:
**kırpışacak ışık yok.** Ve emissive geometri titreyemez — flicker bir
ışık özelliğidir. `Flashiness`'i ELECTRIC yapmak, sonra çeşitlendirmek,
ikisi de sonuçsuz kaldı çünkü sorun hiç orada değildi.

**Teşhis sırası şu olmalı:**

1. `Intensity` > 0 mı? Sıfırsa ışık yoktur, gerisi anlamsızdır.
2. `TimeFlags` o saati kapsıyor mu? (`14680095` = 21:00–05:00)
3. `Flashiness` doğru tip mi?
4. Görünen parlaklık ışıktan mı **emissive'den mi** geliyor?

Dördüncüsü sinsi: emissive'li bir tavan paneli ışık olmadan da parlar,
yani "ışıklar yanıyor" görünür. Ayırt etmenin ucuz yolu, aynı modelin
vanilla kopyasıyla `Intensity` karşılaştırmasıdır.

### Karartılmış haritada ışığı geri getirirken

Vanilla yoğunluğunu **birebir** geri koyma — harita bilerek karartıldıysa
vanilla parlaklığına döner. Oran korunarak ölçekle (morgda **0.30×**;
232 ışık, sonuç 0.12–9.6, ort 6.0).

Ve **aynı turda emissive'i kıs**, yoksa toplam parlaklık artar: ışık
eklerken panelin kendi parlaklığı düşürülür, net aydınlık aynı kalır ama
artık gerçek ışık havuzu ve kırpışma vardır. Morgda uygulanan:
`mh_v_downlight01_d` **8 → 3** (tavan spotu) · `my_flo_calisan_d`
**3 → 1.6** (çalışan floresan) · kırık olanlar zaten 0.

## Projeksiyonlu ışık (gobo) — Sollumz ile üretim

Bir desenin yere düşmesi materyalden gelmez; ışığın **projected
texture** alanından gelir. 36 ışıklık bir sette uçtan uca ölçüldü;
altısı da **hata vermeden** yanlış sonuç üretti.

### `Tangent` = projeksiyonun YUKARI ekseni, `Direction` değil

⛔ Motor `Tangent`'ı projeksiyonun *up* ekseni sayar; **Sollumz oraya ışık
objesinin yerel X'ini (SAĞ eksen) yazar.** Arada tam 90° vardır ve doku
ışın ekseni etrafında yan yatar — uzun kemer pencerelerin lekesi zeminde
yana uzar.

Düzeltme: ışığı kendi ışın ekseni etrafında **−90°** döndür. Blender euler'i
XYZ (`Rz@Ry@Rx`) olduğu için bu roll euler ile yazılamaz, matristen türetilir:

```python
lo.rotation_euler = (Matrix.Rotation(radians(-(90 - egim)), 3, 'X')
                     @ Matrix.Rotation(radians(-90.0), 3, 'Z')).to_euler()
```

`+90` da doğru ekseni verir ama **ters işaretle** — desen 180° dönük olur.
Ölçüt: `dot(Direction, Tangent) == 0` **ve** `Tangent.z > 0`.

### Işığın transformu, mesh transformu sıfırlanırken siliniyor

⛔ Drawable üretiminde transform geometriye piştiği için mesh'ler orijine
çekilir. Işık aynı koleksiyondaysa **o da sıfırlanır** ve `.ydr`'ye
`Position (0,0,0)`, `Direction (0,0,-1)` yazılır: ışın pencerenin dibinde
dimdik aşağı bakar. Eğim/koni ayarları Blender'da doğru görünür,
**export'ta yok olur** — yani ayar değiştirmek oyunda hiçbir şeyi
değiştirmez.

Işığı sıfırlama döngüsünün dışında tut, konumunu açıklığa göre yeniden kur.

### Ölçüt hesap değil, GERİ OKUMADIR

Mesafeyi sahneden hesaplamak yanıltır: sahnedeki değer doğru, dosyadaki
yanlış olabilir. `assetdb.py light <ydr>` ile dağıtılmış dosyayı oku.

```
yon        (0.000, 0.000, -1.000)   ← bozuk (dik aşağı)
konum      (0.000, 0.000,  0.000)   ← bozuk (orijinde)
```

### Gobo dokusunun kendisi

- ⛔ **En-boy oranı korunmalı.** İçeriği kareye sıkıştırmak siluetı yok eder:
  uzun kemer bodurlaşıp yuvarlağa benzer, yuvarlak pencere aynı kalır —
  oyunda "yuvarlaklar sivri, sivriler yuvarlak" olarak görülür. Ölçüt:
  gobo'nun en/boy oranı pencerenin oranını izlemeli (gotik ≈ 0.49,
  gül = 1.00). Hepsi 1.00 ise siluet gitmiştir.
- ⛔ **Spot konisi dairesel, doku kare.** Dokunun boş köşeleri projeksiyonda
  sivri çıkıntı olur (gül penceresi zeminde sekizgen düşer). Dairesel vinyet
  şart; ölçüt köşe parlaklığı **0**.
- İçerik koninin **iç dairesine** sığmalı (≈ %80), yoksa kemerin ucu kırpılır.
- Gobo camın keskin kopyası **değildir**: vanilla `os_stainglasswindow1_light.dds`
  ağır bulanık, parlayan, düşük kontrastlı bir glow; kurşun çizgileri yok.
  Keskin mozaik kopyası projekte edilince desen okunmaz.
- Doku **DXT1 + mip** olmalı. PIL yoksa numpy ile DXT1 yazmak 60 satır:
  4×4 blok, ana eksenin uçlarından iki RGB565 endpoint, 2 bitlik indeks.

### Işık görünmüyorsa sırayla bak

1. **`time_flags`** — varsayılan `total = 0`, yani **hiçbir saat açık değil**
   ve ışık günün hiçbir vaktinde yanmaz. 24/24 = **16777215**
   (72.539 vanilla ışığın 45.770'i bu). *Işık yanmıyor şikâyetinde ilk
   bakılacak yer burasıdır, ışığın kendisi değil.*
2. **Arketip `<textureDictionary>`** — projeksiyon dokusu drawable'la aynı
   adlı `.ytd` içinde gider; arketip onu referans etmezse oyun o sözlüğü
   **hiç yüklemez**. Işık "çalışıyor" görünür, desen yoktur. (Bir kez bu
   güç sorunu sanılıp `intensity` 6 → 15 yapıldı; sebep güç değildi.)
3. **Koni açıları RADYAN** — `cone_outer_angle = 45` yazmak 45 radyan
   demektir, π/2'ye kırpılır; `40` ise **0** olur.
4. **`static_shadows`** — ışık camın arkasındaysa ve gölge açıksa
   çerçeve+cam kendi ışınını engeller, lekenin ortasına pencerenin koyu
   silueti düşer. Vanilla'da projeksiyonlu ışıkların %53'ünde gölge bayrağı
   yoktur; kapatmak meşrudur.

### Yerleşim geometrisi

Işın yatay giderse zemine hiç düşmez. Eğim küçüldükçe leke uzaklaşır **ve**
uzar; büyüdükçe yaklaşır ve siluet korunur.

| eğim | leke merkezi | uzunluk | okunurluk |
|---|---|---|---|
| 30° | 4.0 m | ~12 m | siluet dağılır |
| 48° | 2.0 m | 1.9 m | **dengeli** |
| 61° | 1.2 m | 2.3 m | neredeyse dibinde |

Eğim, içeriğin yarı açısından **büyük** olmalı; değilse koninin üst kenarı
yukarı bakar ve o kısım zemine hiç değmez.

---

## Blender'dan ışık export'u — ölçülmüş üç bağ

Kaynak: Sollumz 5.2, `ydr/lights.py`, `ydr/properties.py`. Üçü de sessizdir.

### ⛔ 1. Gizli ışık export'tan DÜŞMEZ, konumu bozulur

`export_lights()` **`parent_obj.children_recursive`** gezer — görünürlüğe hiç
bakmaz. Ama konumu şu satır hesaplar (`lights.py:159`):

```python
mat = root_mat.inverted() @ light_obj.matrix_world
```

Blender bir objenin `hide_viewport`'u `True` ise onu depsgraph'tan çıkarır ve
**`matrix_world` sıfır kalır** — `view_layer.update()` ve
`evaluated_depsgraph_get()` de düzeltmez, çünkü obje hiç değerlendirilmez.
Sıfır girince sonuç her ışık için aynı olur: **`−kök`**.

Belirti bu yüzden "ışık kayboldu" değil, **"bütün ışıklar tek noktada
toplandı"**dır. Ölçüldü: `v_2_cor1_mesh_delta2`'nin 4 ışığı
`(0.056, −11.953, 7.958)`'e çöktü; drawable kökü `(−0.056, 11.953, −7.958)` —
tam negatifi. Bu, teşhisin **imzasıdır**: çökme noktası kökün negatifiyse sebep
kesin olarak budur.

- **Işığı söndürmek için GİZLEME.** `intensity = 0` + `flashiness = OFF` yaz.
- Kapı: bir dosyadaki ışıkların hepsi tek noktadaysa dağıtımı durduran bir
  denetim adımı (betiği depoda yok). Negatif testle doğrulandı.

### ⛔ 2. `light_properties.intensity` saklanan bir alan DEĞİL — `energy` proxy'si

`properties.py:346`:

```python
def get(self): return self.id_data.energy / LIGHT_INTENSITY_SCALE_FACTOR   # 500
def set(self, v):     self.id_data.energy = v * LIGHT_INTENSITY_SCALE_FACTOR
```

Yani `energy = intensity × 500`. Önizleme için `light.data.energy` yazmak
**intensity'yi 500'e böler** ve export o bölünmüş değeri taşır. Bu yaşandı:
232 ışığın yoğunluğu 1.6 → 0.0032 oldu, hiçbir hata çıkmadı.
**Yalnız `intensity` yaz, `energy`'ye elle dokunma.**

### ⛔ 3. Kemiğe bağlı ışığın konumu KEMİK uzayındadır

`lights.py:151-159` — ışıkta bir bone bağı varsa:

```python
root_mat = parent.matrix_world @ bone.matrix_local
bone_id  = bone.bone_properties.tag
```

Konumu drawable uzayında karşılaştırmak kemik ofseti kadar sahte sapma verir.
Ölçüldü: `v_med_cor_alarmlight`'ın dönen `V_Med_Cor_alarmLightSpin` kemiği
(tag **36848**) yerel `(0.0007, 0.0006, −0.0438)`; ışığın drawable uzayındaki
yeri sunucu değerinden tam **4.4 cm** sapık göründü, oysa doğruydu. Sahte
sapmaya bakıp ışığı "düzeltmeye" kalkmak gerçek hatayı üretir.

⚠️ **Bağ `COPY_TRANSFORMS`'tur, `CHILD_OF` DEĞİL.** Sollumz 4.2'den sonra
değiştirdi (`blenderhelper.py:297`, gerekçesi kodda yazılı). `CHILD_OF`
arayan bir tarama "kemik bağı yok" der ve **yanlış negatif** üretir — bu da
yaşandı. Constraint `owner_space=LOCAL` olduğu için ışığın `location` alanı
**zaten kemik uzayındadır**; import da oraya ham `light.position`'ı yazar.

### Doğrulama: dosyaya bakma, export formülünü taklit et

Blender'ın dağıtılmış dosyayı üretip üretmediğini anlamanın tek yolu, o üç
kuralı da uygulayan formülü Blender içinde çalıştırıp `.ydr`'den okunan
değerlerle karşılaştırmaktır. Ölçüt: konum sapması < 1 mm, `bone_id` birebir,
`intensity`/`falloff`/renk/`flashiness`/`time_flags` sapması 0.
(Morg'da 225 ışıkta maksimum sapma **0.00008 m** ölçüldü — kalan tamamen
dökümdeki 4 hane yuvarlamadır.)

### Işığı gizlemenin güvenli yolu — üç ikon, biri güvenli

Işıkları düzenlerken "gerisi görünmesin" istemek doğal. Ama gizleme yöntemi
seçimi §1'deki çökmeyi geri getirebilir. Ölçüldü (kaydet → `revert_mainfile`
→ konumları karşılaştır, 8 örnek, 5'i gizli):

| yöntem | Blender'da | güvenli mi |
|---|---|---|
| `layer_collection.hide_viewport` | koleksiyonun **göz** ikonu | ✅ **evet** — reload sonrası 8/8 ışık konumunu birebir korudu |
| `collection.hide_viewport` | koleksiyonun **monitör** ikonu | ⛔ kullanma — objeyi depsgraph'tan çıkarma sınıfı |
| `layer_collection.exclude` | koleksiyonun **onay kutusu** | ⛔ kullanma — aynı sınıf |
| `object.hide_viewport` | objenin **monitör** ikonu | ⛔ **çökmenin sebebi budur** |

⚠️ **Oturum içi geçiş bu hatayı ÜRETMEZ** — `matrix_world` bir kez
hesaplandıktan sonra önbellekte kalır, ikonu kapatıp açmak onu sıfırlamaz.
Çökme yalnız dosya **gizli ışıkla kaydedilip yeniden açıldığında** doğar
(matris hiç hesaplanmaz). Bu yüzden "denedim, bozulmadı" bir kanıt değildir;
ölçüm **kaydet + reload** turuyla yapılır.

**Koleksiyon taşımak export'u etkilemez.** Sollumz drawable'ı obje
hiyerarşisinden (`children_recursive`) toplar, koleksiyondan değil — ışıkları
kendi kategorine taşımak parent bağını bozmaz (ölçüldü: 140 ışık taşındı,
hiyerarşiden kopan 0). Ama ışık **hiçbir** görünür koleksiyonda kalmazsa
view layer'dan düşer, o zaman §1'e geri dönersin.

---

## 9. ARAÇ HATALARI — DÜZELTİLDİ

### `light_sahne.oku` iskeletsiz drawable'da çöküyordu
`bones is None` durumunda `return [], {}` dönüyordu ama çağıranlar
`kmap["tag"]` / `kmap["idx"]` bekliyor → `KeyError: 'idx'`, ve hata
*"IC HATA"* diye çıkıp sebebini gizliyordu. **Statik prop'ların çoğunda
iskelet yoktur** — yani ışık düzenleme o dosyalarda hiç çalışmıyordu.
→ `return [], {"tag": {}, "idx": {}}`

### Void Tools Shadow Map, Blender 5.x'te post-process yapamıyordu
Üç ayrı API kırılması (bkz. §3e), hepsi tek `try/except`'e düşüp tek satır
uyarıyla yutuluyordu; kullanıcı **ham bake** alıyordu.
→ `_make_compositor_tree`, `_link_compositor_output`, `_set_node_option`
yardımcıları eklendi; 4.x ve 5.x'te birden çalışır.

## Shadowmap (topluluk)

- ⚠️ **Shadowmap: iki ayrı yöntem, karıştırma.** Eski yöntem Blender'ın
  **Shadow *render pass*'ini** kullanır ve o kaldırıldığı için **Blender 3.3**
  gerektirir; yeni yöntem **bake type = Shadow** kullandığı için güncel Blender'da
  çalışır.
