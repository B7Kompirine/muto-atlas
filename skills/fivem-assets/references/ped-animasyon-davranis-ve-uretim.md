# Ped animasyon davranış veritabanı + sıfırdan animasyon üretimi

Oyundaki **1070 humanoid ped iskeletinin tamamı** üzerinde yapılan ölçümler,
eşya etkileşim animasyonlarının gerçek yapısı, ve GTA V'te **olmayan** iki
animasyon stilinin (mızrak, kademeli korkutucu gülüş) sıfırdan üretilip
`.ycd`'ye derlenerek doğrulanması.

Kardeş dokümanlar: `ped-kemik-yuz-rigging.md` (iskelet + yüz sistemi),
`ped-retarget-weightpaint.md` (retarget + skinning).

---

## 0. BEŞ CÜMLEDE ÖZET

1. **1070 humanoid ped, 158 farklı rig ailesi.** 98 kemikli ambient rig,
   128 kemikli freemode rig'in **tam alt kümesi**; fazlalık 30 kemiğin
   tamamı expression-güdümlü helper. Ters yönde tek kemik yok.
2. **GTA V'te İKİ ayrı yüz rig sistemi var.** Ambient/freemode ped'ler
   21 kemikli `FB_` rigini, hikâye karakterleri **156 kemikli `FACIAL_`**
   rigini kullanır. İkisi ayrı dünya.
3. **`_045` yüz kemiği son ekini tüm oyunda yalnızca `mp_m_freemode_01`
   kullanır** — ve o FiveM'in en çok kullanılan ped'i.
4. **Eşya animasyonu tespiti tahmin işi değil: klip adı = prop model adı.**
   1407 prop, 53.181 gerçek prop animasyonu.
5. Yeni animasyon üretmek çalışıyor: mızrak seti (55 kanal) ve kademeli
   gülüş (39 kanal) üretilip binary `.ycd`'ye derlendi, gidiş-dönüş birebir
   doğrulandı.

---

## 1. RİG AİLELERİ VE ANİMASYON UYUMLULUĞU

Ölçüm: `skeletons.tsv.gz`'deki tüm iskeletler, hayvanlar (`a_c_*`) ve
parmaksızlar çıkarılarak kemik-tag kümesine göre kümelendi.
Araç: `pedrig.py families` / `pedrig.py compat <ped>`

**1070 humanoid ped → 158 rig ailesi.** En büyük dördü:

| İmza | Kemik | Ped | Örnek |
|---|---|---|---|
| `30c1119e8f` | **98** | 362 | `a_m_m_beach_01` (ambient erkek) |
| `63198251d5` | **128** | 154 | `a_m_m_bankrobber_01`, **`mp_m_freemode_01`** |
| `71211e8ac3` | 100 | 75 | `a_f_m_beach_01` (ambient kadın) |
| `72b6df069e` | 128 | 49 | `a_f_m_genbiker_01`, `mp_f_freemode_01` |

### Kapsama katmanları (ölçüldü)

| Hedeflenen aile | Kapsanan ped | Ortak kemik |
|---|---|---|
| ilk 1 | 362 (33.8%) | 98 |
| ilk 4 | 640 (59.8%) | **98** |
| ilk 8 | 761 (71.1%) | 77 |
| ilk 20 | 864 (80.7%) | 63 |
| ilk 40 | 924 (86.4%) | 61 |
| tümü (158) | 1070 (100%) | **23** |

**Evrensel çekirdek — 23 kemik**, her humanoid ped'de var:
`SKEL_ROOT, SKEL_Pelvis, SKEL_Spine_Root, SKEL_Spine0..3, SKEL_Neck_1,
SKEL_Head, SKEL_L/R_Clavicle, SKEL_L/R_UpperArm, SKEL_L/R_Forearm,
SKEL_L/R_Hand, SKEL_L/R_Thigh, SKEL_L/R_Calf, SKEL_L/R_Foot`

Dikkat: **parmak ve ayak parmağı evrensel çekirdekte YOK.** Yine de
1070 ped'in **1070'inde parmak var** (30 parmak kemiği: 1070 ped; 4 kemik:
24 ped; hiç: 2 ped) — yani pratikte %97 güvenli, ama garanti değil.

### 98 ⊂ 128: fark tam olarak helper kemikler

98 kemikli ambient rig, 128 kemikli freemode rig'in **tam alt kümesidir**
(`98 ⊂ 128` → doğru; ters yönde **0** kemik). Fazlalık 30 kemik:

```
EO_  (4) : EO_L/R_Foot, EO_L/R_Toe            -> ayakkabı override
MH_ (16) : Hair_Crown, Hair_Scale, L/R_CalfBack, L/R_ThighBack,
           L/R_Finger00, L/R_Finger10, L/R_FingerBulge00,
           L/R_FingerTop00, L/R_HandSide       -> muscle helper
SM_  (8) : L/R_Skirt, M/L/R_BackSkirtRoll, M/L/R_FrontSkirtRoll
SPR_ (2) : SPR_L/R_Breast
```

Hepsi **expression-güdümlü** — yani klip zaten dokunmaz.

### Pratik karar

| Hedef | Sonuç (ölçüldü — payda 1066 humanoid ped, `a_c_*` hariç, kemik TAG'i üzerinden) |
|---|---|
| `mp_m_freemode_01` için yazılan animasyon | yalnız **154 ped** (%14,4) sorunsuz |
| 98-kemik ambient set için yazılan | **822 ped** (%77,1) sorunsuz + freemode'da da çalışır |

> Önceki sürümde bu satır **692 (%64,7)** yazıyordu. Aynı payda ve yöntemle
> freemode sayısı birebir yeniden üretildi (154/1066 = %14,4), ambient set
> **822** verdi. 692'yi üreten yöntem dört varyantla arandı, bulunamadı
> (tag/`peds.json` 822 · tag/`skeletons.tsv.gz` 822 · tag/ilk blok 822 ·
> **ad** tabanlı 592). Karıştırmayın: `ExpressionSetName` `expr_set_ambient*`
> ile başlayan ped sayısı **717/1109 = %64,7**'dir — yüzde tesadüfen aynı,
> ölçtüğü şey farklı.

→ **Maksimum erişim için 98-kemik ambient sete yaz.** Bir klip yalnızca
hedefte var olan kemikleri sürer; eksik kemik sessizce rest'te kalır.
Küçük sete yazılan animasyon büyük rig'de çalışır, tersi çalışmaz.

---

## 2. İKİ AYRI YÜZ RİG SİSTEMİ

Bu, dokümanın en önemli bulgusu olabilir.

| | `FB_` rigi | `FACIAL_` rigi |
|---|---|---|
| Kemik | **21** + `FACIAL_facialRoot` | **156** |
| Kullanan | ambient + freemode (838 ped) | `player_zero/one/two` |
| Sürücü | `ambient.yed → facial` | `<ped>.yed → faceinit` (203 track) |
| Adlandırma | `FB_Jaw_045`, `FB_L_Lip_Corner_000` | `FACIAL_jaw`, `FACIAL_L_lipCornerAnalog` |
| Kanal | rot + scale (kaldıraç kısa) | translasyon (kaldıraç ~47 cm) |

### `player_zero` (Michael) `FACIAL_` rig envanteri — 156 kemik

| Bölge | Sayı | Örnekler |
|---|---|---|
| göz | 40 | `L_eyeball`, `L_eyelidUpper/Lower`, `L_eyelidUpperInnerAnalog`, `L_eyelashUpperInner`, `L_eyesackUpperInnerBulge/Furrow` |
| **dudak** | **32** | `L_lipCornerAnalog`, `L_lipCornerThicknessUpper/Lower`, `lipUpperAnalog`, `L_lipUpperThicknessH/V`, `lipLowerAnalog` |
| çene(chin) | 15 | `L_chinSkinTop/Mid/Bottom`, `L_chinSide`, `L_underChin` |
| dil | 15 | `tongueA..E`, `L/R_tongueA..E` |
| yanak | 12 | `L_cheekInner/Lower/Outer/OuterSkin`, `L_cheekLowerBulge1/2` |
| alın | 12 | `L_foreheadInner/Outer/UpperInner/UpperOuter`, `L_foreheadInnerBulge` |
| burun | 9 + 4 | `noseTip`, `noseBridge`, `L_noseUpper`, `L_nostril`, `L_nostrilThickness` |
| diğer | 8 | `L_masseter` (çene kası), `L_nasolabialBulge/Furrow`, `skull`, `L_jawRecess` |
| kulak/şakak | 6 | `L_ear`, `L_earLower`, `L_temple` |

**`Analog` / `SDK` deseni:** `Analog` = doğrudan kontrol kemiği,
`SDK` = set-driven-key ile sürülen. `.ydd`'nin gömülü iskeletinde
genelde yalnız `Analog` bulunur.

**`Thickness` kemikleri kritik:** `lipUpperThicknessV`, `lipLowerThicknessV`,
`lipCornerThicknessUpper/Lower` — dudağı **geri kıvırıp dişleri açığa
çıkaran** mekanizma budur. `FB_` riginde karşılığı yok.

### Yüz kemiği adı son eki — ped bazında ölçüm

| Son ek | Ped |
|---|---|
| `_000` | 634 |
| `_001` | 183 |
| `_002` | 29 |
| `_003` | 10 |
| `_004` | 7 |
| `_005` | 2 |
| `_006` | 1 (`hc_gunman`) |
| **`_045`** | **1 — yalnızca `mp_m_freemode_01`** |
| FB_ yok | 235 |

**21 FB_ tag'inin her birinin 8 ad varyantı var** (aynı tag, farklı isim).
`mp_f_freemode_01` `_000` kullanır — yani erkek/kadın freemode arasında bile
ad farkı vardır. Oyunda bağlama **tag** ile olduğu için sorun çıkmaz;
Blender'da armature modifier **isim** ile bağladığı için yanlış eşleşen yüz
**sessizce hiç deforme olmaz.**

### `teef` drawable = sadece diş değil

`teef_000_u.ydd` (Michael): 1893 vertex, vertex grupları
`FACIAL_jaw`, `FACIAL_tongueA..E`, `FACIAL_L/R_eyeball`,
`FACIAL_L/R_eyelidUpper/Lower`, `FACIAL_L/R_eyelash*`.
Yani **diş + dil + göz küresi + kirpik** hepsi bu tek drawable'da.
Ağız içi görünecek bir animasyon yapıyorsan bu component şart.

---

## 3. EŞYA ETKİLEŞİM ANİMASYONLARI

### Tespit: klip adı = prop model adı

Senkron sahne kliplerinde klip adı doğrudan prop modelinin adıdır
(`-N` soneki sahne dilimidir):

```
ah_1_ext_t6-3 dict'i:
  player_zero_dual-3          171 kanal   <- ped
  player_one_dual-3           170 kanal   <- ped
  cs_lestercrest_dual-3       167 kanal   <- ped
  exportcamera-3               13 kanal   <- kamera
  prop_cs_walking_stick-3       4 kanal   <- PROP
  prop_phone_cs_frank-3         4 kanal   <- PROP
  v_ilev_store_door02-3         4 kanal   <- kapı
```

312.748 klip prop veritabanıyla eşlendi → **1407 prop, 53.181 klip.**
Araç: `assetdb.py propanim <prop>`

En çok animasyonu olan proplar:
`prop_npc_phone` 1743 · `w_pi_pistol` 1173 · `prop_cs_walking_stick` 868 ·
`p_v_med_p_sofa_s` 720 · `prop_phone_overlay_anim` 697 ·
`v_ilev_fib_door1_s` 668 · `p_cs_lighter_01` 518 · `p_cs_joint_01` 341

Prop klibi kanal sayısı dağılımı: **4 kanal 30.682 klip** (baskın), sonra
10, 12, 18, 8, 26. Yani tipik prop tek kemikli, pos+rot ile sürülür.

**Silahlar da prop olarak animasyonlanır** (`w_pi_pistol` 1173 klip) —
yeni bir silah/alet animasyonu yaparken izlenecek kalıp budur.

### Melee/dövüş klipleri = gövde + yüz TEK klipte

`melee@large_wpn@streamed_core` (136 klip) ölçümü: neredeyse tüm klipler
`AnimationList`, **2 animasyon: 44 gövde kanalı + 32 yüz kanalı.**

Adlandırma kuralı yönlüdür:
`low_attack_-90`, `low_attack_0`, `ground_attack_-90`,
`melee_damage_front/back/left/right`, `dodge_generic_l`,
`plyr_rear_takedown_bat_r_facehit`, `hit_counter_attack_knife_r`

Hayvan melee dict'lerinde ayrıca **eşli `_facial` klibi** vardır
(`growling` + `growling_facial`, 20 kanal). Yani Rockstar bir dövüş
animasyonu yaparken yüz eşliğini de üretir — kendi setini yaparken aynı
yapıyı kur.

---

## 4. SIFIRDAN ANİMASYON ÜRETİMİ — çalışan hat

### Poz kurmanın doğru yolu: `aim` + `ik2`

Sollumz rig'inde kemik yönü/roll'u anatomik değildir (hepsi 0.05 m stub,
`use_connect=False`), bu yüzden **Euler değeri vermek öngörülemez.** İki
deterministik araç gerekir:

**`aim(bone, child, world_dir)`** — kemiğin anatomik yönünü (head → çocuğun
head'i) dünya uzayında verilen yöne döndürür. Ölçüm: hedef `(0,-1,0)`
verildiğinde ulaşılan yön `(0,-1,0)`, **hata 0.0000°**.

**`ik2(upper, mid, end, target, pole)`** — 2 kemikli analitik IK; ucu dünya
uzayındaki bir **konuma** götürür, dirseği `pole` yönüne açar. Yön yerine
konum vermek poz kurmayı öngörülebilir yapar (el/ayak nereye gitsin
diye düşünürsün, hangi açı diye değil).

Kosinüs teoremi: `a = (l1²−l2²+d²)/2d`, `h = √(l1²−a²)`,
dirsek `E = S + d̂·a + perp·h`.

Ped yönelimi (freemode + ambient): **ileri = −Y, sol = +X, yukarı = +Z.**
Ped origin'i **kalçadadır** — ayaklar z ≈ −0.94'te, yani armature'ı
`+0.94` yukarı almazsan alt gövde zemin düzleminin altında kalır.

### Sollumz `.ycd` export — üç tuzak

**1. `target_id` ARMATURE DATA-BLOCK olmalı, Object DEĞİL.**
Sollumz `ycdexport.py` içinde:
`target_is_armature = isinstance(target_id, bpy.types.Armature)`
Object verirsen bone_map `None` olur ve export **sessizce 0 kemik kanalı**
yazar: dosya oluşur, kare sayısı ve süre doğrudur, veri yoktur.
Ölçüm: yanlış → **724 bayt**, doğru (`ap.target_id = arm.data`) → **59.286 bayt**.

**2. `target_formats` enum'u `{'NATIVE','CWXML'}`** — `'YCD'` diye bir
değer yok (`ValueError` verir). Ve **`.ycd` için ikisi de fark etmez**:
"Successfully exported" der, klasörde `.ycd` yerine `.ycd.xml` bulunur.

Sebep ölçüldü (Sollumz 2.9 kaynağı): `.ycd` **format sağlayıcı sisteminin
dışındadır**. `szio.gta5` sağlayıcıları yalnız `.ybn .ydr .ydd .yft .yld
.ytyp .ymap .ytd` tanır; clip dictionary export'u `ycd/ycdexport.py` içinde
doğrudan `clip_dict.write_xml(filepath)` çağırır ve `target_formats`'a **hiç
bakmaz**. Diğer 8 uzantı için `NATIVE` gerçekten binary üretir — ama yalnız
`pymateria` paketi kuruluysa; değilse Sollumz ayarı sessizce `{'CWXML'}`'e
düşürür (`sollumz_preferences.py:377`). Ayrıntı:
`references/ytyp-ymap-bayraklari.md` §7.

**3. ÇOK KLİPLİ SÖZLÜKTE KLİPLER BİRBİRİNİ EZER — en sinsi hata.**
Sollumz clip ve animation ögelerine `<Name>` yazar ama **`<Hash>` YAZMAZ.**
CodeWalker'ın `ClipMap`/`AnimMap`'i **hash ile anahtarlanır**; hash yoksa
hepsi 0 olur ve aynı anahtara yazılanlar birbirini ezer.

Ölçüm — 5 klipli bir sözlük:

| Aşama | Klip | Animasyon |
|---|---|---|
| Sollumz export XML | **5** | **5** |
| binary `.ycd` (düzeltmesiz) | **1** ✗ | **1** ✗ |
| binary `.ycd` (`fix_ycd_xml.py` sonrası) | **5** ✓ | **5** ✓ |

Düzeltmesiz halde yalnızca **sonuncu** klip hayatta kalır.

**TEK KLİPLİ SÖZLÜKTE DE ZARARLIDIR — ve orada daha sinsidir.** Klip
ezilmez ama **hash 0 kalır**, yani klibin ADI yoktur:

```
duzeltmesiz : <Hash></Hash>              -> TaskPlayAnim(... ,'spear_thrust') BULAMAZ
fix sonrasi : <Hash>spear_thrust</Hash>  -> calisir
```

Dosya derlenir, `klip=1` der, geri okuma "1 klip" doğrular — her şey yolunda
görünür. Ama oyun klibi **isim/hash ile** aradığı için animasyon hiç
oynamaz. Bu oturumda mızrak `.ycd`'si tam bu şekilde bozuk üretildi ve
ancak son doğrulamada yakalandı.

→ **Klip sayısı kaç olursa olsun `fix_ycd_xml.py` çalıştır**, sonra
derlenmiş dosyayı geri okuyup `<Hash>` alanının dolu olduğunu doğrula.

Çözüm: derlemeden önce eksik `<Hash>` alanlarını enjekte et:

```bash
python "$P/scripts/fix_ycd_xml.py" <dosya>.ycd.xml -o <dosya>_fixed.ycd.xml
powershell -File "$P/scripts/xml_to_ycd.ps1" -XmlPath <dosya>_fixed.ycd.xml
```

`xml_to_ycd.ps1` çıktısındaki `[*] klip=N animasyon=N` satırını **oku**;
beklediğin sayı değilse ezilme olmuştur.

**4. `xml_to_ycd.ps1 -ClipName` tek-animasyonlu klipte ÇÖKER.**
Klip tipi `Animation` (AnimationList değil) olduğunda
`ClipDictionary.Clips` üzerinde `Hash` set etmek `NotImplementedException`
→ korumasızsa `StackOverflowException`. Ama o durumda Sollumz
`<Name>pack:/klip</Name>` alanını **zaten yazar**, yani elle hash atamaya
gerek yoktur → **`-ClipName` vermeden çalıştır.** (Script artık bu bloğu
korumaya alıyor ve uyarı basıp devam ediyor.)

### Tam hat

```bash
P="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/fivem-natives}"
# 1) rig
powershell -Command "& '$P/scripts/extract_asset.ps1' -Names @('mp_m_freemode_01.yft') -Out <k>"
# 2) Blender: yft import -> aim/ik2 ile poz -> keyframe (SADECE rotasyon)
# 3) Sollumz: create_clip_dictionary -> create_animation (target_id = arm.DATA!)
#            -> create_clip -> clip_new_animation -> export NATIVE
# 4) XML -> binary
powershell -File "$P/scripts/xml_to_ycd.ps1" -XmlPath <...>.ycd.xml
# 5) doğrula (gidiş-dönüş)
powershell -File "$P/scripts/res_to_xml.ps1" -Path <...>.ycd -OutDir <k>/rt
```

---

## 5. DENEY 1 — MIZRAK (GTA V'te yok)

GTA V'te mızrak/cirit propu **yoktur** (`spear`, `javelin` → 0 sonuç).
En yakın uzun saplı prop: `w_me_poolcue`, `prop_pool_cue`.
İki elle uzun sap tutan en iyi vanilla referans:
`timetable@gardener@clean_pool@` (`base_skimmer`, havuz süzgeci).

**Üretilen:** `muto_spear@core` / `spear_thrust`
26 kare, **0.867 s**, 30 fps, **55 kanal (hepsi Track 1 = rotasyon)**,
55 kemiğin tamamı doğru tag ile tanındı, bilinmeyen tag 0.

Anahtar pozlar (kare → poz): `0 guard` → `7 wind` → `14 thrust` → `25 recover`

El/ayak hedefleri (dünya, m; ayaklar z≈0.10):

| Poz | sağ el | sol el | sol ayak | sağ ayak |
|---|---|---|---|---|
| guard | (−0.14, −0.02, 1.16) | (−0.02, −0.52, 1.22) | (0.12, −0.34, 0.10) | (−0.16, 0.30, 0.08) |
| wind | (−0.20, +0.26, 1.14) | (−0.06, −0.24, 1.26) | (0.12, −0.26, 0.10) | (−0.18, 0.42, 0.08) |
| thrust | (−0.10, −0.44, 1.18) | (−0.02, −0.84, 1.20) | (0.14, −0.62, 0.10) | (−0.18, 0.34, 0.08) |

Mızrak yerleşimi: iki elli kavramanın geometrik kısıtı **mızrak ekseni =
(sol el − sağ el)** doğrultusudur; kavrama sapın arka üçte birindedir.

**Doğrulama:** binary derleme öncesi/sonrası birebir aynı —
klip adı, 26 kare, 0.8333 s, 55 kanal, 88 veri kanalı.

Yalnız `SKEL_*` kemikleri keyframe'lendi → 98-kemik ambient sete uyumlu,
`MH_/RB_/SM_/SPR_/EO_` ve `FB_` kemiklerine dokunulmadı.

---

## 6. DENEY 2 — KADEMELİ KORKUTUCU GENİŞ GÜLÜŞ (GTA V'te yok)

`FB_` riginin 21 kemiği bu iş için yetersiz; **Michael'ın 156 kemikli
`FACIAL_` rigi** kullanıldı (`player_zero` + `head_000_r.ydd` +
`teef_000_u.ydd`).

### Kanal seçimi ölçümle belirlendi

`FACIAL_` deri kemiklerinin dönme merkezi deriden **~47 cm** uzakta:
10° rotasyon → **100–120 mm** deri hareketi. Yani **rotasyon kullanılamaz.**
Translasyon temiz ve doğrusal: 10 mm local → **7.2 mm** deri
(ağırlık ortalamasıyla ölçekli).

→ **`FACIAL_` rigi TRANSLASYONLA sürülür.** (`FB_` rigi ise rotasyonla —
ikisi ters çalışır, karıştırma.)

### Ölçülmüş eksen haritası (+10 mm local → derinin gittiği yön)

| Kemik grubu | locX | locY | locZ |
|---|---|---|---|
| `jaw`, `L/R_lipCornerAnalog`, `lipUpperAnalog`, `lipLowerAnalog`, `L_foreheadInner` | **−X** | **ileri** | **yukarı** |
| `L/R_lipUpperThicknessH`, `lipLowerThicknessH` | **−X (yatay dudak gerilmesi)** | yukarı/aşağı | geri/ileri |
| `L_lipUpperThicknessV`, `L_lipCornerThicknessUpper` | −X | **yukarı** | geri |
| `L_lipLowerThicknessV`, `L_lipCornerThicknessLower` | −X | **aşağı** | ileri |
| `L_cheekOuter`, `L_cheekOuterSkin` | aşağı+−X | ileri | yukarı+−X |
| `L_eyelidUpper` | −X | aşağı+ileri | yukarı+ileri |
| `L_masseter` | aşağı | ileri | −X |

### ⚠ İŞARET TUZAĞI — bir kez yanlış yapıldı, ölçümle düzeltildi

**Ped'in SOLU +X'tir** (`FACIAL_L_ear` deri merkezi x = +0.0894,
`R_ear` x = −0.0835 — mesh tabanlı ölçüm).
Ama **`locX+` deriyi −X'e götürür**, yani ped'in SAĞINA.
Sonuç: `L_*` kemiğine `+X` vermek ağzı **daraltır**.

Doğrulama (ağız köşeleri arası mesafe, rest 63.5 mm):

| Ne verildi | Sonuç |
|---|---|
| `L=+X, R=−X` | **35.6 mm** → büzülme ✗ |
| `L=−X, R=+X` | **91.5 mm** → gerilme ✓ |

→ Ağzı **genişletmek** için `L` kemiklerine **negatif X**, `R` kemiklerine
**pozitif X**. `L/R` kemikleri ayna DEĞİLDİR; ikisi de `locX+` ile aynı
yöne (−X) gider.

İlk denemede bu ters kuruldu ve dudaklar dışa gerilmek yerine içe büzüldü.
Ölçmeden gözle karar vermek burada işe yaramaz.

### YÜZ DEFORMASYONUNUN DOĞRU YÖNTEMİ — Jacobian + yüzey alanı

**Kemik kemik değer tahmin etmek çalışmaz.** İlk üç denemem bozuk çıktı:
dudaklar yüzden koptu, köşeler sivri uç halinde dışarı taştı, yandan gaga
gibi durdu. Sebep: tek bir kemiği 20-30 mm çekmek, o kemiğe bağlı vertex'leri
komşularından koparır.

Çalışan yöntem üç ölçüme dayanır:

**1. Her kemiğin Jacobian'ı (local → dünya, 3×3).**
Kemiğin ağırlıklı vertex merkezini al, her local eksende 10 mm sonda uygula,
dünya kaymasını ölç. 109 kemiğin tamamı tersinir çıktı; kazanç 0.16–0.91
(yani 10 mm local, kemiğe göre 1.6–9.1 mm deri hareketi).
Sonra: `local = J⁻¹ · istenen_dünya_kayması`. Artık kanal/eksen tahmini yok.

**2. Pürüzsüz deformasyon alanı.**
Her kemiğe ayrı değer vermek yerine, konuma bağlı sürekli bir alan tanımla:
```
w = exp(-((z-z_ağız)/σz)² - ((y-y_ağız)/σy)²)     # ağız çevresinde sönümleme
hedef_x = x · (1 + gerilme·w)                      # yanal uzama
hedef_z = z + kaldırma·w·r²                        # r=|x|/yarı_genişlik → hilal
```
Komşu kemikler benzer değer aldığı için **yırtılma oluşmaz**.

**3. Yüzeyi takip etme — siluetin bozulmasını bu engeller.**
Köşeyi düz yana çekmek yüzü balonlaştırır, çünkü yüz yanlara doğru geriye
kıvrılır. Ağız hizasında mesh'in ön yüzey profilini ölç ve köşeyi ona oturt:

| x (merkeze göre) | yüzey ne kadar geride |
|---|---|
| ±30 mm | 9 mm |
| ±50 mm | 23 mm |
| ±60 mm | 37 mm |
| ±70 mm | 55 mm |

```
hedef_y = surf_y(hedef_x) + (y - surf_y(x))   # yüzeye göre derinlik korunur
```

**4. Dudak ayrımı köşede sıfırlanmalı.** Dişleri göstermek için üst dudak +z,
alt dudak −z; ama çarpan `(1 − r²)` ile köşede 0'a inmeli — yoksa köşe
açılıp yırtılır. Gerçek sırıtışta köşeler kapalıdır.

**Hariç tutulacaklar:** `eyeball, eyelash, eyelid, eyesack, forehead, temple,
ear, skull, tongue, noseBridge, noseTip, brow, nostril`. Ağız alanına
dahil edilirlerse gözler ve alın bozulur.

### `FB_` RİGİNDE AĞIZ — hangi kemikler ŞART

Ölçüm: bir gülümsemede yalnız ağız köşelerini sürmek yetmez. `FB_` riginin
ağız bölgesinde **13 kemik** vardır ve üçü kritiktir:

| Kemik | Rol | Atlanırsa |
|---|---|---|
| `FB_UpperLipRoot` / `FB_LowerLipRoot` | dudakların **EBEVEYNİ** | dudak bütün olarak hareket etmez, sadece köşeler kıpırdar |
| `FB_UpperLip` / `FB_LowerLip` | dudak **ORTASI** | ağzın ortası donuk kalır |
| `FB_L/R_CheekBone` | yanak desteği | köşe yırtılır |

**Kök kemiklerin kendi derisi yoktur** → ağırlıklı vertex sayıları 0'dır ve
naif Jacobian ölçümü onları **atlar**. Çözüm: etki alanını
*kendi vertex'leri + TÜM alt kemiklerinin vertex'leri* olarak al:

```python
names = [bone] + [c.name for c in arm.data.bones[bone].children_recursive]
```

Bu düzeltilmeden üretilen ilk freemode klibi yalnız **9 kemik** sürüyordu ve
dudaklar hiç kıpırdamıyordu.

### ARAÇ: `blender_facepose.py`

Yukarıdaki yöntemin tamamı tekrar kullanılabilir hale getirildi:

```python
import os
P = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.expanduser("~/.claude/muto-atlas")
exec(open(P + "/scripts/blender_facepose.py").read())
fp = FacePose()          # armature + kafa mesh'i otomatik bulur, son eki tespit eder
fp.measure()             # Jacobian olcumu (kok kemikler dahil)
fp.topology()            # mesh gerilmeye ne kadar dayanir
fp.apply(stretch=.14, lift=.0075, sep=.0008, jaw=.0034)
fp.report()              # genislik / dikey aciklik / KIRPILAN
```

`report()` çıktısındaki **`kirpilan` daima 0 olmalı**. Sıfır değilse alan
bozulmuş, sivri uç oluşmuş demektir.

### ⚠ KAFA MESH'İNİ VERTEX SAYISIYLA SEÇME

`max(len(o.data.vertices))` ile kafayı seçmek **yanlış mesh'i** seçer:

```
TEETH (teef_000_u)  4517 vertex   <- daha BUYUK
head  (head_000_r)  1514 vertex   <- asil kafa
```

Bu yüzden bir Jacobian ölçümü sessizce **0 kemik** döndürdü (dişlerde dudak
vertex grubu yok). Doğrusu: **dudak vertex grubu olan** mesh'i ara.

### `FB_` RİGİNİN YAPISAL SINIRI — filtrum

Burun ile üst dudak arasındaki deri **%75 `SKEL_Head`**'e bağlıdır — ifade
sırasında hiç kıpırdamayan bir kemik. Üst dudak kayınca orası yerinde kalır
ve yüzey buruşur.

Üstelik `FB_` riginde **nazolabial / burun / filtrum kemiği YOKTUR**
(Michael'ın 156 kemikli riginde `nasolabialFurrow`, `nasolabialBulge`,
`nostril`, `chinSkin*` var; freemode'da yok). Ağız köşesinin dışındaki
deriyi taşıyacak hiçbir kemik bulunmadığı için yanal gerilme
**%14'ün** ötesinde katlanma üretir.

Denenen ve **işe yaramayan**: filtrum ağırlığını `SKEL_Head`'den dudak
kemiklerine aktarmak (%75 → %25, GTA kurallarına uyarak). Filtrum düzeldi
ama etki alanı genişleyince ağzın tamamı bozuldu. Otomatik bir ağırlık
geçişiyle çözülmüyor.

**Doğrulama notu:** buruşmanın gerçek geometri hasarı mı yoksa Workbench
cavity gölgelemesinin abartması mı olduğu, cavity kapatılarak sınandı —
gerçek hasar çıktı. Gölgeleme ayarını sorgulamadan "bozuk" ya da "temiz"
demek yanıltır.

### ASIL TAVAN TOPOLOJİDİR — sayılarla

`mp_m_freemode_01` kafası (`head_000_r.ydd`):

| Ölçüm | Değer |
|---|---|
| **Kafanın TOPLAM vertex sayısı** | **1514** |
| Ortalama kenar uzunluğu | **11.2 mm** (ağız çevresi 6.7 mm) |
| Ağız köşesinden 5 mm içinde vertex | 21 |
| Ağız köşesinden 10 mm içinde vertex | 60 |
| Ağız köşesinden 20 mm içinde vertex | 143 |

Ağız köşesini 30 mm yana çekmek, 6.7 mm aralıklı vertex'leri **4-5 kenar
boyu** ötelemek demektir. Araya girecek geometri olmadığı için yüzey
katlanmak zorundadır. Yüksek çözünürlüklü bir horror sculpt'ı (50-500 bin
vertex) ile karşılaştırmak yanıltıcıdır — orada ağız **öyle modellenmiştir**,
gerilmemiştir.

`fp.topology()` bu ölçümü verir. Bir hedef görsele bakıp "olur mu" demeden
**önce bunu çalıştır**.

### KEMİK EKLEMEK ÇÖZMEDİ (denendi)

Eksik bölgeler için 5 yeni kemik eklendi (`MUTO_L/R_Nasolabial`,
`MUTO_L/R_CornerCheek`, `MUTO_Philtrum`; tag 40000-40004, çakışmasız) ve
`SKEL_Head` ağırlığı onlara aktarıldı (GTA kuralları korunarak).

Sonuç: **kırık kaybolmadı.** `CornerCheek` kemikleri o bölgede yalnızca
**2 vertex** bulabildi — orada zaten vertex yok. **Kemik eklemek, olmayan
geometriyi var etmez.**

### DİKEY AÇILMA, YANAL GERİLMEDEN DAHA ÇOK YIRTAR

Ayrı ayrı ölçüldü (freemode kafası, kırpılma 0):

| Deformasyon | Ağız genişliği |
|---|---|
| saf yatay gerilme %30 | 85.6 mm |
| saf yatay gerilme %50 | 106.0 mm |
| saf yatay gerilme %70 | 126.4 mm |
| yatay + dikey açılma | %14'te katlanma başlar |

Yani **ince ve geniş** bir sırıtış, dikeyde açılan bir ağızdan çok daha az
hasar üretir. Saf yatay gerilme 126 mm'ye kadar kırpılmasız gidiyor;
şekli oradan kurmak, dikey açıklıkla zorlamaktan iyidir.

### ÖLÇÜLEN SINIR — %30 gerilme (FACIAL_ rigi)

| Gerilme | Sonuç |
|---|---|
| 0.30 | **temiz** — yırtık yok, kırpılan kemik 0 |
| 0.40 | sağ köşede ayrılma başlar |
| 0.45 / 0.60 | köşeler belirgin şekilde kopar |

Weight yumuşatma (dudak köşesi ağırlıklarını yanağa yayma, GTA'nın
4-etki/toplam-1.0 kuralına uyarak) denendi — **yırtılmayı çözmedi.**
Sınır ağırlıkta değil **topolojide**: dudak köşesinde o gerilmeyi taşıyacak
edge loop yok. Referanstaki Joker tipi kulaklara ulaşan sırıtış için
mesh'i düzenlemek (edge loop ekleme / sculpt) gerekir; bu animasyon değil
modelleme işidir.

### 5 KADEMELİ GÜLÜMSEME — nihai (Jacobian + alan yöntemi)

`muto_facial@smile` — 5 ayrı klip, 46 kare / 1.5 s, **49 kemik**, Track 0.

| # | Klip | gerilme | kaldırma | ayrım | ağız genişliği | açıklık |
|---|---|---|---|---|---|---|
| 1 | `smile_stage_1_neutral` | 0.00 | 0.000 | 0.0000 | 63.5 mm | 1.2 mm |
| 2 | `smile_stage_2_tension` | 0.09 | 0.003 | 0.0000 | 71.0 | 1.0 |
| 3 | `smile_stage_3_stretch` | 0.17 | 0.006 | 0.0012 | 77.5 | 4.9 |
| 4 | `smile_stage_4_grow` | 0.24 | 0.009 | 0.0020 | 83.3 | 7.5 |
| 5 | `smile_stage_5_max` | 0.30 | 0.011 | 0.0027 | **88.3** | 9.7 |

Beş kademede de **kırpılan kemik 0**. Binary gidiş-dönüşte 5 klibin hepsi
korundu, 49 kemiğin hepsi `player_zero` iskeletinde tanınıyor.

### ⚠ POZ ÖLÇERKEN ACTION'I TEMİZLE

Armature'a atanmış bir action varken `pose_bone.location` yazıp
`view_layer.update()` çağırmak **hiçbir işe yaramaz**: action her
güncellemede pozu geri ezer. Bu oturumda saatlerce "gözler neden bozuk"
diye arandı — sebep buydu, `smile_stage_5_max` atalı kalmıştı.

```python
if arm.animation_data: arm.animation_data.action = None
```
Elle poz vermeden ÖNCE bunu yap; yoksa ölçtüğün şey senin pozun değildir.

### Alternatif deney: çene düşüren kahkaha (39 kemik, metre)

Hedef: **çene KAPALI, ağız YATAY olarak kulaklara doğru gerilen** ince bir
yarık (Joker/Glasgow tipi). İlk denemem çeneyi düşürüp dikey açılan bir ağız
üretti — **yanlış kanal seçimi**. Doğrusu: `jaw` neredeyse sabit, iş
`lipCornerAnalog` + `ThicknessH` (yatay) + yanak kaldırma ile yapılır.

Yanal çekiş **tek kemiğe yüklenmez**; `lipCorner` + `lipUpperThicknessH` +
`lipLowerThicknessH` + `lipCornerThickness*` + `cheek*` + `chinSide`
arasında dağıtılır. Tek kemiğe 30 mm vermek dudağı yırtar; dağıtınca
108 mm genişlik yırtılmadan elde edilir.

`muto_facial@smile` — **5 ayrı klip**, her biri 46 kare / 1.5 s,
47 kemik (Track 0 = pozisyon), nötr(0) → hedef(15) → tut(45).

| # | Klip | wide | up | curl_u | curl_l | jaw | cheek | naso | squint |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `smile_stage_1_neutral` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | `smile_stage_2_tension` | .005 | .003 | 0 | 0 | 0 | .003 | .002 | .001 |
| 3 | `smile_stage_3_stretch` | .013 | .010 | .0015 | .0010 | .0005 | .007 | .005 | .003 |
| 4 | `smile_stage_4_grow` | .021 | .018 | .0035 | .0022 | .0010 | .011 | .009 | .006 |
| 5 | `smile_stage_5_max` | .029 | .026 | .0055 | .0035 | .0015 | .015 | .013 | .010 |

Ölçülen sonuç (deri üzerinden, mm):

| Kademe | ağız genişliği | köşe yüksekliği | dikey açıklık |
|---|---|---|---|
| 1 | 63.5 | −3.5 | 1.2 |
| 2 | 71.2 | −2.9 | 1.5 |
| 3 | 83.5 | −2.1 | 4.0 |
| 4 | 95.9 | −1.4 | 6.9 |
| 5 | **108.2** | **−0.7** | 9.9 |

Genişlik **%70 artar**, köşe yüksekliği −3.5'ten −0.7'ye çıkarak hilal
oluşturur, dikey açıklık 10 mm'de kalır (ince yarık). `curl` değerlerini
büyütmek ağzı dikeyde açar ve referanstan uzaklaştırır — küçük tut.

**Kademe 2'de `curl_u = curl_l = jaw = 0`** olmalı: referansta "hafif
gerilim" aşamasında dudaklar KAPALIDIR, diş görünmez.

### Alternatif deney: çene düşüren kahkaha (39 kemik, metre)

| Kademe | köşe dışa | köşe yukarı | çene açık | üst kıvrım | alt kıvrım | yanak | göz |
|---|---|---|---|---|---|---|---|
| L1 smirk | 0.004 | 0.004 | 0.000 | 0.001 | 0.000 | 0.002 | 0.001 |
| L2 smile | 0.009 | 0.008 | 0.004 | 0.003 | 0.001 | 0.005 | 0.003 |
| L3 grin | 0.014 | 0.011 | 0.011 | 0.006 | 0.004 | 0.008 | 0.005 |
| L4 laugh | 0.019 | 0.013 | 0.020 | 0.009 | 0.007 | 0.011 | 0.008 |
| L5 scary | **0.030** | 0.014 | **0.032** | 0.015 | 0.012 | 0.014 | **−0.004** |

L5'te göz kısma **negatife** çevrilir (gözler kısılmaz, faltaşı gibi
açılır) ve kaş aşağı iner — "gülüyor ama gözleri gülmüyor" etkisi
rahatsızlığın kaynağıdır.

### Ölçülen sınır

- **L2** temiz doğal gülümseme (yırtık yok).
- **L4** üst + alt diş tam görünür, dudak geri kıvrılmış, nazolabial derin —
  **rig'in kullanışlı üst sınırı.**
- **L5** dudak köşeleri **yırtılıyor**: 30 mm köşe çekişi deri
  ağırlıklarının taşıyabileceğini aşıyor. Horror estetiği için işe yarar,
  ama bu bir bug değil **rig'in tasarım sınırının aşılması**.

**Üretilen:** `muto_facial@laugh` / `laugh_staged`
61 kare, **2.033 s**, **39 kanal (hepsi Track 0 = pozisyon)**.
Gidiş-dönüş birebir doğrulandı (117 veri kanalı).

### DÜRÜST SINIR — runtime'da ne olur

176 vanilla yüz animasyonunun **hiçbiri** `FB_`/`FACIAL_` kemiklerini
doğrudan sürmez; hepsi expression kanallarından geçer. Yani doğrudan kemik
yazan bir yüz `.ycd`'si oyunda **expression tarafından üzerine yazılabilir.**

Bu animasyon şurada güvenle çalışır:
- cutscene / machinima / video üretimi,
- expression'ı olmayan özel ped,
- Blender içinde yüz animasyonu **üretme** aşaması.

Runtime'da desteklenen yol hâlâ: yüz kanalı (`Track 22/25`) + expression,
ve yeni expression bytecode'u yazmak `muto` eklentisinin `build_yed`
yolunu gerektirir (CodeWalker `Streams` yazamaz).

---

## 7. TUZAK KATALOĞU (bu oturumda bilfiil yaşananlar)

1. **Sollumz `Animation.target_id` Object verilirse export sessizce boş** —
   724 bayt vs 59.286 bayt. `arm.data` ver.
2. **`target_formats={'YCD'}` yok** → `{'NATIVE'}` veya `{'CWXML'}`.
   `.ycd` format sisteminin dışında olduğu için ikisi de XML yazar.
3. **`xml_to_ycd.ps1 -ClipName` tek-animasyonlu klipte çöker** →
   `-ClipName` vermeden çalıştır.
4. **`.yft` import'u `SKEL_ROOT` adlı bir MESH de yaratır** ve render'da
   her şeyi kapatır (zemin gibi görünür). Poz incelerken gizle.
5. **Ped origin'i kalçadadır**, ayaklar z ≈ −0.94 → armature'ı +0.94
   yukarı almazsan alt gövde zeminin altında kalır.
6. **Bir action'ın keyframe'lemediği kemik son pozunda kalır.** Ölçüm
   öncesi pozu sıfırla; yoksa önceki denemenin kirliliğini ölçersin
   (bu oturumda ayak "hiç kımıldamıyor" sanıldı, sebebi buydu).
7. **`execute_blender_code` her çağrıda YENİ namespace** — yardımcı
   fonksiyonlar bir sonraki çağrıda yok. Aynı çağrıda tanımla.
8. **`bone.matrix_local.translation` bu ydd armature'larında güvenilmez**
   (kafa x=−0.47 çıktı, mesh x≈0). Yönelim tespitini **mesh bbox +
   simetrik kemik çiftleri** ile yap, kemik konumuyla değil.
9. **Rig yönelimi rig'e göre değişir.** `mp_m_freemode_01` ileri = −Y;
   Michael'ın ydd armature'ında ilk okuma +Y sandırdı, doğrusu −Y çıktı.
   **Her rig için ölçerek doğrula** (nötr render en hızlı yol).
10. **`FACIAL_` rigi translasyon, `FB_` rigi rotasyon ister.** Karıştırmak
    `FACIAL_`'da 10°'de 100 mm sıçrama demek.
11. **L/R yüz kemikleri ayna DEĞİL** — ikisi de `locX+` ile aynı yöne (−X)
    gider. Ped'in solu **+X** ama `locX+` deriyi **−X**'e götürür → ağzı
    genişletmek için `L` negatif, `R` pozitif X. Ters kurulursa ağız
    büzülür (ölçüm: 63.5 → 35.6 mm). **Gözle karar verme, mesafeyi ölç.**
12. **Çok klipli sözlükte klipler birbirini EZER** — Sollumz `<Hash>`
    yazmaz, hepsi 0 olur, `ClipMap` tek anahtara düşer, sadece sonuncusu
    kalır (5 klip → 1). `fix_ycd_xml.py` ile hash enjekte et ve
    `xml_to_ycd.ps1` çıktısındaki `klip=N` sayısını doğrula.
13. **Yatay ağız gerilmesi `ThicknessH` kemikleridir** (`lipUpperThicknessH`,
    `lipLowerThicknessH`) — `ThicknessV` dikey kıvrımdır. Geniş sırıtış için
    `H`, diş göstermek için `V`. Karıştırmak ağzı dikeyde açar.
14a. **Kafa mesh'ini vertex sayısıyla seçme** — dişler (`teef`, 4517 vertex)
    kafadan (1514) BÜYÜKTÜR. `max(len(vertices))` yanlış mesh'i seçer ve
    ölçüm sessizce **0 kemik** döndürür. Dudak vertex grubu olanı ara.
14b. **Hedef görsele bakıp söz vermeden önce `fp.topology()` çalıştır.**
    1514 vertex / 11.2 mm kenar bir kafada aşırı ağız deformasyonu kemik
    pozlayarak elde EDİLEMEZ. Kemik eklemek de çözmez (denendi).
14. **Yüz deformasyonunda kemik kemik değer TAHMİN ETME.** Jacobian ölç
    (`local = J⁻¹·istenen_dünya`), pürüzsüz alan tanımla, köşeyi ölçülmüş
    yüzey profiline oturt. Tahminle üç deneme de yırtık/gaga çıktı.
15. **Elle poz vermeden önce `animation_data.action = None`.** Atanmış
    action her `view_layer.update()`'te pozu ezer; ölçtüğün şey senin pozun
    olmaz. Bu oturumda "gözler neden bozuk" sorusunun cevabı buydu.
16. **Köşeyi düz yana çekme** — yüz yanlara geriye kıvrılır, düz çekiş
    silueti balonlaştırır. Ağız hizasında yüzey profilini ölç
    (±50 mm'de 23 mm geri) ve `hedef_y = surf_y(hedef_x) + derinlik_offset`.
17. **Dudak ayrımını köşede sıfırla** (`×(1−r²)`) — köşe açık kalırsa yırtılır.
18. **Bu mesh'in gerilme sınırı %30.** %40'ta ayrılma başlar. Weight
    yumuşatma çözmez; sınır topolojidedir. Daha aşırısı için mesh
    düzenlemek (edge loop) gerekir — animasyon değil modelleme.
19. **Ambient rig (98) hedefle**, freemode (128) değil: **%77,1**'e karşı
    %14,4 (822 / 154 ped, payda 1066 humanoid).
20. **`spear`/`javelin` propu yok** — uzun saplı iş için `w_me_poolcue`
    yedek, gerçek mızrak custom model gerektirir.
21. **`_045` yalnızca `mp_m_freemode_01`'de**; `mp_f_freemode_01` bile
    `_000` kullanır.
