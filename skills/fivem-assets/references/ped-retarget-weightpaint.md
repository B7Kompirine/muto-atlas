# Yabancı iskeletten GTA ped'ine animasyon aktarma + weight painting

Sketchfab / Mixamo / Rigify / Daz / UE animasyonlarını GTA V ped iskeletine
(`mp_m_freemode_01`, 128 kemik) taşıma ve FiveM'e uygun hale getirme.

Kaynak: gerçek `.yft` / `.ydd` / `.ycd` verisi üzerinde Blender 5.2 + Sollumz
ile yapılan ölçümler. **Her sayı ölçümdür.** Kardeş doküman:
`ped-kemik-yuz-rigging.md` (iskelet + yüz sistemi).

> **Topluluk tarafı:** `sollumz-discord-tutorials.md` §3-§4.
> Oradan gelen üç sessiz hata bu dosyaya ek olarak geçerlidir:
> - ⛔ **Rokoko `Auto Scale` açıkken root motion TAMAMEN silinir.**
> - ⛔ **Retarget'ta tüm `FB_` yüz keyframe'leri silinmeli** — yoksa hikâye
>   ped'lerinde yumruk atarken yüz içe çöküyor.
> - ⛔ **Export → Drawable → `Mesh Domain` = `Face Corner`** (`Vertex` yalnız
>   MP freemode kafaları için; yanlışı sessizce bozuk ped üretir).
>
> ⚠️ **Çelişki:** bir topluluk videosu T-pose için kolu **−45°** çeviriyor.
> Bu dosyadaki **57°** ÖLÇÜMDÜR ve kazanır. Videoya göre düzeltme yapma.

Araç: `scripts/blender_retarget_gta.py` — bu dokümandaki matematiği uygular,
53 kemik üzerinde test edildi.

---

## 0. DÖRT CÜMLEDE ÖZET

1. **GTA rest pose'u T-pose DEĞİL, A-pose**: üst kol yataydan **57° aşağı**.
   Mixamo T-pose'dur. Bu fark kapatılmazsa kollar **144°'ye kadar** sapar.
2. **GTA lokomosyonu yerinde (in-place) üretilir.** Koşu klibinde ayak
   animasyon-uzayı sürüklenmesi **0.000 m**; tüm yol (3.656 m / 1.73 s) ayrı
   **mover track**'inde. Mixamo'da yol hips kemiğine gömülüdür → taşınmazsa
   ped yerinde kayar ya da iki kat hareket eder.
3. **Sollumz'un import ettiği GTA armature'unda kemik yönleri anatomik
   DEĞİL** — hepsi 0.05 m, `use_connect=False`. `bone.vector` / `bone.length`
   kullanan her retarget/IK yanlış çalışır.
4. **Weight paint kuralı sert**: vertex başına **en fazla 4 kemik**, ağırlık
   toplamı **tam 1.0**, ağırlıksız vertex **yok**, ağırlıklar **1/255 adımlı**.

---

## 1. RETARGET MATEMATİĞİ — ölçülmüş üç yöntem

Hedef kemik `t`, kaynak kemik `s`. Her kare için:

```
W_t  =  W_s  ·  Q_off          (W = armature uzayında 3x3 yönelim)
```

`Q_off` sabittir, kare başına değişmez. Nasıl hesaplandığı her şeyi belirler:

| Yöntem | `Q_off` | Ölçülen sonuç |
|---|---|---|
| **naive dünya eşleme** | `I` (birim) | **Her kemikte rig'in roll farkı kadar hata — deneyde tam 30.00°; kollarda 144°.** Kullanma. |
| **rest ofseti (delta)** | `rest_s⁻¹ · rest_t` | Gidiş-dönüşte **0.000°** (55 kemik × 5 kare). Roll farkını temizler ✅ ama rest biasını korur: T-pose kaynakta GTA kolu **57° aşağı** biaslanır ❌ |
| **`align` (doğru olan)** | `(R_align · rest_s)⁻¹ · rest_t` | Roll farkını temizler ✅ **ve** kaynağın mutlak uzuv yönünü korur ✅ |

`R_align` = kaynak kemiğin **anatomik rest yönünü** hedefin anatomik rest
yönüne döndüren rotasyon.

**Doğrulama ölçümü** (kaynak T-pose, hedef A-pose, kollar 57° farklı):

```
align öncesi:  GTA kol 57° aşağı   |  kaynak kol  0° (yatay)
align sonrası: GTA kol  0°  ← kaynağın yönüne oturdu
               GTA uyluk 85° → 85° ← rest'ler zaten aynıydı, DOKUNMADI
```

Yani `align` yalnızca rest'lerin ayrıştığı yerde düzeltir. Doğru davranış bu.

**Neden "rest → rest" invaryantı burada istenmez:** `rest` modu "kaynak kendi
rest'indeyse hedef de kendi rest'inde" garantisini verir (ölçüm: 0.000°).
Kulağa doğru gelir ama animasyonun *içeriği* mutlak uzuv yönüdür: kaynakta kol
40° aşağıdaysa GTA'da da 40° aşağı olmalı — GTA'nın rest'i 57° olduğu için
kanal değeri −17° delta olur. `align` bunu yapar, `rest` yapmaz.

### Kemik sırası zorunlu

Bake sırasında **kök → yaprak** sırayla ilerle ve her kemikten sonra
`view_layer.update()` çağır. Parent ayarlanmadan child'ın dünya matrisi eski
parent'a göre okunur ve zincir bozulur. Sıralama:
`sorted(pairs, key=lambda n: len(bones[n].parent_recursive))`.

---

## 2. KEMİK ADI EŞLEMESİ

GTA ↔ Mixamo (`mixamorig:` öneki soyulur). Rigify / UE / Daz / 3ds Biped
adları da araçta var.

| GTA | Mixamo | Not |
|---|---|---|
| `SKEL_ROOT` | `Hips` | **Kalça dönüşü buraya gider.** `SKEL_Pelvis` ve `SKEL_Spine_Root` rest'te ±90° çeviricidir ve 84 klip ölçümünde sapmaları **0.0°** — onlara keyframe koymak tüm hiyerarşiyi yatırır. |
| `SKEL_Spine0/1/2/3` | `Spine`, `Spine1`, `Spine2`, — | **3 → 4 uyuşmazlığı.** Mixamo'da 3 omurga, GTA'da 4. `Spine3` karşılıksız kalır; rest'te bırak ya da `Spine2`'nin bir kısmını dağıt. |
| `SKEL_Neck_1` / `SKEL_Head` | `Neck` / `Head` | |
| `SKEL_L_Clavicle` | `LeftShoulder` | |
| `SKEL_L_UpperArm` / `_Forearm` / `_Hand` | `LeftArm` / `LeftForeArm` / `LeftHand` | |
| `SKEL_L_Thigh` / `_Calf` / `_Foot` / `_Toe0` | `LeftUpLeg` / `LeftLeg` / `LeftFoot` / `LeftToeBase` | |
| `SKEL_L_Finger00/01/02` | `LeftHandThumb1/2/3` | **başparmak** |
| `SKEL_L_Finger10/11/12` | `LeftHandIndex1/2/3` | işaret |
| `SKEL_L_Finger20/21/22` | `LeftHandMiddle1/2/3` | orta |
| `SKEL_L_Finger30/31/32` | `LeftHandRing1/2/3` | yüzük |
| `SKEL_L_Finger40/41/42` | `LeftHandPinky1/2/3` | serçe |

Parmak eşlemesi **rest offset'lerinden doğrulandı**, folklor değil:
`Finger00` elin merkezine 0.026 m (diğerleri ~0.10 m) → başparmak.
`Finger10 → Finger40` elin −Y yönünde ilerler (+0.029 → −0.034) →
işaret'ten serçeye.

**Eşlenmeyecekler** — bunlara ASLA keyframe yazma; expression sürer:
`MH_` (20), `RB_` (7), `SM_` (8), `EO_` (4), `SPR_` (2), `FB_` (21),
`FACIAL_` (1). Toplam 63 kemik. Klipler zaten sadece 65 kemiğe dokunur.

---

## 3. ROOT MOTION / MOVER — en çok atlanan adım

GTA animasyonu iki ayrı yerde yol taşır:

| Kanal | Nerede | Ne |
|---|---|---|
| Track 5 `MoverPosition` | `pose.bones["SKEL_ROOT"].animation_tracks_mover_location` | Ped'in dünyada aldığı yol |
| Track 6 `MoverRotation` | `...animation_tracks_mover_rotation` | Ped'in dönüşü (kuaterniyon) |

**Ölçüm:**

| Klip | Süre | Mover yolu | Ayak anim-uzayı sürüklenmesi | Hız |
|---|---|---|---|---|
| koşu `B6B72381` | 1.73 s | **3.656 m** | **0.000 m** | 2.11 m/s |
| sprint `21FAE774` | 0.90 s | **7.530 m** | 0.002 m | 8.4 m/s |
| geçiş `CDADD93E` | 3.17 s | 2.949 m | 0.322 m | 0.93 m/s |

İlk ikisi **tam döngüsel ve yerinde**: kemik animasyonu başladığı yere döner,
yolun %100'ü mover'da. Üçüncüsü bir başlama/durma geçişi (0.32 m sürüklenme).

**Mixamo'dan gelen animasyonda yol `Hips`'e gömülüdür.** Yapılacak:

1. Kaynağın `Hips` **yatay** yer değiştirmesini oku.
2. `SKEL_ROOT.animation_tracks_mover_location`'a yaz.
3. `SKEL_ROOT.location`'ın yatay bileşenini **sıfırla** (dikey kalsın —
   zıplama/çökme dikeyde yaşar).

Yapılmazsa: mover boşsa ped yerinde kayar; hem hips hem mover doluysa iki kat
hızlı gider.

`mover_location[2]` yer düzlemi lokomosyonunda sabit **1.0**; sadece dikey yer
değiştiren kliplerde değişir (bir klipte 5.33 → 2.74 ölçüldü).

> **Dürüst sınır:** mover'ın kemik uzayına göre **işaret konvansiyonunu
> kesinleştiremedim**. Ayak kayması metriğim iki işaretle de temiz sıfır
> vermedi (yürüyüşte 59 mm/kare ve 112 mm/kare). Pratik çözüm: iki işaretle de
> bake et, stance fazında ayak kaymasını ölç, küçüğünü seç. Araç bu ölçümü
> raporluyor.

---

## 4. FPS — sessiz %25 hatası

GTA klipleri **30 fps**'tir (ölçüm: 754 kare / 25.1 s = 30.04).
**Blender sahnesi Sollumz import'undan sonra varsayılan 24 fps'te kalır.**
24'te animasyon yapıp export edersen tüm zamanlama %25 yavaşlar ve kimse
nedenini bulamaz.

```python
bpy.context.scene.render.fps = 30
```

Süreyi `Duration` alanından al; `FrameCount / fps` ile hesaplama — aynı `.ycd`
içinde iki farklı frame rate olabilir (yüz kliplerinde 15 fps + 30 fps birlikte).

---

## 5. SOLLUMZ ARMATURE GEOMETRİSİ — büyük tuzak

Sollumz `.yft` import ettiğinde:

```
her kemik:  length = 0.05 m   (HEPSİ aynı)
            use_connect = False
            bone.vector ≈ ±Y   (anatomik değil)
```

Kemik **konumları (head) doğru**, yön / uzunluk / roll **doğru değil**.

Somut fark: `SKEL_L_UpperArm` için `bone.vector` **1.2°** derken gerçek
anatomik yön **57°**. Aralarında 56° fark var.

**Anatomik yön = kemiğin head'inden çocuğunun head'ine.** Helper kemikler
çok yakın durduğu için "en uzak çocuk" seçilir:

```python
kids = bone.children
c = max(kids, key=lambda k: (k.head_local - bone.head_local).length)
direction = (c.head_local - bone.head_local).normalized()
```

`bone.vector`, `bone.length`, ya da kemiğin Y eksenine dayanan her IK /
retarget / "bone stretch" işlemi bu rig'de yanlış çalışır.

---

## 6. DOĞALLIK — ölçülebilir kontrol listesi

Sketchfab animasyonları GTA'da "kayıyor / plastik duruyor" diye şikâyet
edilmesinin ölçülebilir nedenleri:

**1. Ayak teması (foot contact).** Stance fazında ayağın **dünya**
konumu sabit kalmalı. Anim uzayı + mover = dünya. Kontrol: stance karelerinde
`|Δayak_dünya|` küçük olmalı; büyükse ya mover yanlış ya klip in-place değil.

**2. Döngü kapanışı.** Loop'lanacak klipte ilk ve son kare pozu aynı olmalı.
Araç bunu `loop_uyusmazligi_derece` olarak raporlar. Testte 31 karelik bir
kesitte `SKEL_L_Toe0` 71° uyuşmazlık verdi — o kesit tam bir çevrim değildi.
Tam çevrim seç, yoksa ayak her döngüde zıplar.

**3. Omurga sertliği.** GTA omurgası **sert**: ölçülen maksimum sapmalar
`Spine0` 43°, `Spine1` 28°, `Spine2` 39°, `Spine3` 32°. Mixamo'nun 3 omurgalı
esnek eğrisini 4 kemiğe dağıtırken bu bandı aşarsan karakter lastik gibi olur.
Boyun 83°, kafa 62° — orada bol pay var.

**4. Helper kemikler ölü kalır.** `MH_` (dirsek/diz şişmesi), `RB_` (önkol
burulma dağıtımı) kemikleri **mesh'e skinlenmiş ama animasyonla
sürülmez** — expression sürer. Retarget edilmiş bir animasyonda expression
yoksa dirsek/diz şişmesi ve önkol burulması **kaybolur**; kol büküldüğünde
mesh sıkışır. Bu "doğal durmuyor" hissinin somut kaynağıdır.
Ölçülen skin ağırlıkları: `MH_L_HandSide` 448 vertex, `RB_L_ForeArmRoll` 383,
`MH_L_FingerBulge00` 328, `RB_L_ThighRoll` 148, `MH_L_Knee` 48, `RB_Neck_1` 117.

**5. Parmaklar.** GTA'da 30 parmak kemiği var ve vanilla klipler bunları
gerçekten kullanıyor (ölçülen sapmalar 38-179°). Mixamo animasyonlarının
çoğunda parmak yoktur → eller donuk kalır. Elle poz ver ya da bir vanilla
klipten parmak kanallarını kopyala.

**6. Ayak/parmak ucu.** `SKEL_L_Toe0` ölçülen sapma 79°. Yürüyüşte parmak
ucu bükülmesi olmadan basış sahte görünür.

**7. Yasaklı kanallar.** Uzuvlara **translation** yazma (mesh ayrılır),
hiçbir yere **scale** yazma (ölçümde hiçbir vanilla gövde klibi scale
yazmıyor). Translation yalnız `SKEL_ROOT`, `IK_*`, `PH_*`'te meşrudur.

---

## 7. WEIGHT PAINTING — ölçülmüş kurallar

4 gerçek freemode drawable'ında ölçüldü:

| Drawable | Vertex | Grup | Etki dağılımı (1/2/3/4 kemik) | Toplam≠1 | Ağırlıksız | min ağırlık |
|---|---|---|---|---|---|---|
| `head_000_r` | 1514 | 23 | 587 / 250 / 261 / 416 | **0** | **0** | 0.003922 |
| `uppr_000_u` | 4416 | 46 | 910 / 1440 / 1236 / 830 | **0** | **0** | 0.003922 |
| `lowr_000_u` | 1075 | 11 | 317 / 134 / 578 / 46 | **0** | **0** | 0.003922 |
| `feet_000_u` | 536 | 6 | 209 / 327 / 0 / 0 | **0** | **0** | 0.047059 |

**Kurallar — hepsi dört dosyada da tutarlı:**

1. **Vertex başına en fazla 4 kemik.** Hiçbir vertex 4'ü aşmıyor.
   Blender'da: `Weights → Limit Total → 4`.
2. **Ağırlık toplamı tam 1.0.** 7541 vertex'te tek istisna yok.
   Blender'da: `Weights → Normalize All` (Lock Active kapalı).
3. **Ağırlıksız vertex yasak.** Dördünde de 0 tane. Ağırlıksız vertex oyunda
   origin'e fırlar.
4. **Ağırlıklar 1/255 adımlı.** Minimum gözlenen 0.003922 = 1/255;
   `feet` minimumu 0.047059 = 12/255. GTA ağırlıkları **8-bit** saklıyor →
   0.002 gibi bir ağırlık yazmak anlamsız, kuantizasyonda kaybolur.
   0.004'ün altındaki ağırlıkları temizle (`Clean` ile threshold 0.004).
5. **Helper kemikler skinlenir.** `MH_`, `RB_` kemiklerine ağırlık **verilir**
   (yukarıdaki vertex sayıları), ama onlara animasyon **yazılmaz**. Kendi
   kıyafetini modellerken vanilla drawable'ın ağırlık dağılımını taklit et.
6. **`SKEL_Pelvis` skinlenir ama dönmez** (`lowr`'da 554 vertex). Dönüşü
   `SKEL_ROOT`'tan gelir.

### Yüz skinlemesi

`head_000_r` 23 gruba skinli: `SKEL_Head` (1140 vertex, baskın),
19 × `FB_*`, `SKEL_Neck_1` (117), `RB_Neck_1` (117), `SKEL_Spine3` (101).
En çok ağırlık alan yüz kemikleri: `FB_Jaw` 304, `FB_R_Lip_Top` 167,
`FB_L_Lip_Top` 165, `FB_R_Lip_Corner` 153, `FB_L_Lip_Corner` 145,
`FB_L_Eye` 139, `FB_R_Eye` 129. En azı `FB_Tongue` 12.

### ⚠ `_000` / `_045` ad tuzağı — sessizce yüzü ölü bırakır

`.ydd`'nin gömülü iskeletinde yüz kemikleri **`FB_Jaw_000`**, `.yft`
iskeletinde ise **`FB_Jaw_045`** adını taşır. **21 yüz kemiğinin tamamı aynı
tag'e sahip ama farklı isimde** (128 tag'in hepsi ortak, sadece bu 21 adı
farklı).

- Oyunda skinleme **tag** ile bağlanır → sorun yok.
- Blender'da armature modifier **isim** ile bağlar → `_000` skinli bir kafa
  mesh'ini `_045` armature'a verirsen **yüz hiç deforme olmaz**, hata da
  vermez.

Çözüm: kafayı `.ydd`'nin kendi iskeletiyle içe al (`import_ext_skeleton`
kullanma) ya da vertex grup adlarını armature'a uyacak şekilde yeniden adlandır.

---

## 8. YÜZ KEMİĞİ EKSEN ANLAMLARI — elle poz vermek için

Ölçüm: her `FB_` kemiği +15° döndürülüp baskın vertex'lerin ağırlık merkezi
kaymasına bakıldı (dünya uzayı: **Z yukarı, −Y yüzün baktığı yön**).

**Evrensel kalıp:**
- **`rotX` (kemik boyu ekseni) neredeyse etkisiz** — 19 kemikte 0.1-2.0 mm.
  "+X uzunluk ekseni" kuralının bağımsız doğrulaması.
- **`rotY+` → AŞAĞI** (her kemikte). `rotY−` → yukarı. Ana sürücü budur.
- **`rotZ` → yan / ileri-geri**, ve **L ile R'de işaret ters**.

| Kemik | +15° rotY etkisi | Kaldıraç |
|---|---|---|
| `FB_Jaw` | aşağı+geri (ağız açılır) | 15.8 mm |
| `FB_Brow_Centre` | aşağı (kaş çatma) | 11.5 mm |
| `FB_L/R_Brow_Out` | aşağı | 9.7 mm |
| `FB_L/R_Lip_Corner` | aşağı+geri | 7.4 mm |
| `FB_LowerLip` / `FB_UpperLip` | aşağı / geri | 3.5 mm |
| `FB_L/R_Eye`, `Lid_Upper` | aşağı | 2.5-3.3 mm |
| `FB_L/R_Lip_Top/Bot` | aşağı | 2.1 mm |

### Görsel doğrulanmış ifade değerleri

Gerçek `head_000_r` mesh'inde render edilip gözle onaylandı:

```python
# GÜLÜMSEME  (rotZ işaretleri L/R'de TERS — genişleme için)
FB_L_Lip_Corner: rotY=-14, rotZ=+8    FB_R_Lip_Corner: rotY=-14, rotZ=-8
FB_L/R_CheekBone: rotY=-12
FB_L/R_Lid_Upper: rotY=+6             FB_Jaw: rotY=+4

# SİNİRLİ
FB_Brow_Centre: rotY=+20              FB_L/R_Brow_Out: rotY=+15
FB_L/R_Lip_Corner: rotY=+11           FB_UpperLip: rotY=-14
FB_LowerLip: rotY=+9                  FB_L/R_Lid_Upper: rotY=+9

# ÜZGÜN  (iç kaş yukarı + dış kaş aşağı = klasik üzgün kaş)
FB_Brow_Centre: rotY=-16              FB_L/R_Brow_Out: rotY=+9
FB_L/R_Lip_Corner: rotY=+16           FB_L/R_Lid_Upper: rotY=+11
FB_Jaw: rotY=+4

# AĞIZ AÇIK
FB_Jaw: rotY=+26                      FB_LowerLip: rotY=+8
```

**Doğal sınır:** `Lip_Corner`'da **22° kırılıyor** (üst dudak yırtılıyor),
**14° doğal**, 10° hafif. Kaşlar 15-20°'yi rahat kaldırıyor. Kaldıraç
büyüdükçe tolerans düşer.

> Not: bu değerler kemiği **doğrudan** sürer. Oyun içinde yüz kemikleri
> expression tarafından her karede üzerine yazılır — bu tablo Blender'da
> yüz animasyonu **üretmek** için, runtime'da kemik zorlamak için değil.

---

## 9. İŞ AKIŞI

```bash
P="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/fivem-natives}"

# 1) GTA rig'i çıkar
powershell -NoProfile -ExecutionPolicy Bypass -Command \
  "& '$P/scripts/extract_asset.ps1' -Names @('mp_m_freemode_01.yft') -Out <klasör>"

# ped bileşeni (kafa/gövde) — AYNI ADI TAŞIDIKLARI İÇİN yol filtresi ŞART
powershell -NoProfile -ExecutionPolicy Bypass -Command \
  "& '$P/scripts/extract_asset.ps1' -Pattern 'head_000_r.ydd' -PathFilter 'mp_m_freemode_01' -Out <k>"
```

**Blender'da:**

1. `.yft`'i Sollumz ile içe al → 128 kemikli GTA rig.
2. Sketchfab kaynağını içe al (FBX / glTF). Ölçeğini GTA'ya uydur
   (ped kemik açıklığı ayak parmağından tepeye **~1.69 m**).
3. `bpy.context.scene.render.fps = 30`.
4. `scripts/blender_retarget_gta.py`'yi çalıştır. Rapor:
   eşleşen kemik sayısı, rest poz farkı uyarısı, yasaklı kanal denetimi,
   döngü uyuşmazlığı, ayak sürüklenmesi.
5. Raporu düzelt: döngüyü kapat, parmakları elle ver, omurga bandını aşma.
6. Sollumz ile `.ycd` export → **XML üretir** ("Successfully exported" der ama
   klasörde `.ycd.xml` vardır, `.ycd` yoktur).
7. Binary'ye çevir:

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File \
  "$P/scripts/xml_to_ycd.ps1" -XmlPath <...>.ycd.xml -ClipName @('klip_adi')
```

8. Sunucuya koy, **sunucudan çıkıp yeniden bağlan** (restart yetmez, FiveM
   stream dosyalarını cache'ler).

---

## 10. TUZAK KATALOĞU

1. **Naive dünya-yönelimi eşleme** → her kemikte roll farkı kadar hata
   (deneyde tam 30°), kollarda 144°. `align` kullan.
2. **Düz rest ofseti (delta)** → roll temiz ama T-pose kaynakta kollar 57°
   aşağı biaslanır.
3. **Rest poz farkını hiç kontrol etmemek.** GTA A-pose (57°), Mixamo T-pose
   (0°). Araç bunu raporluyor; uyarıyı görmezden gelme.
4. **`bone.vector` / `bone.length` kullanmak.** Sollumz rig'inde hepsi 0.05 m
   ve yön anatomik değil (kolda 56° fark). head→çocuk-head kullan.
5. **Kemik sırasını gözetmemek.** Kök→yaprak gitmezsen ve her adımda
   depsgraph güncellemezsen zincir bozulur.
6. **Kalça dönüşünü `SKEL_Pelvis`'e yazmak.** Pelvis ve `SKEL_Spine_Root`
   ±90° çeviricidir, ölçülen sapmaları 0.0° — hiyerarşiyi yatırır.
   Kalça dönüşü `SKEL_ROOT`'a gider.
7. **Root motion'u hips'te bırakmak.** Ped yerinde kayar. Mover'a taşı ve
   hips'in yatayını sıfırla.
8. **Hem hips'te hem mover'da yol bırakmak.** Ped iki kat hızlı gider.
9. **24 fps'te bırakmak.** Sessiz %25 zamanlama hatası.
10. **`MH_` / `RB_` kemiklerine keyframe yazmak** — expression alanı, çakışır.
11. **Bunları hiç düşünmemek** — dirsek/diz şişmesi ve önkol burulması
    kaybolur, kol büküldüğünde mesh sıkışır.
12. **Uzuvlara translation, herhangi bir yere scale yazmak.**
13. **Vertex başına 4'ten fazla kemik.** Fazlası sessizce atılır.
14. **Ağırlık toplamını 1.0'a normalize etmemek.**
15. **Ağırlıksız vertex bırakmak** → origin'e fırlar.
16. **0.004'ten küçük ağırlık yazmak** — 8-bit kuantizasyonda kaybolur.
17. **`_000` / `_045` yüz kemiği ad farkı** → Blender'da yüz hiç deforme
    olmaz, hata da vermez. Oyunda tag ile bağlandığı için sorun görünmez.
18. **Sollumz binary `.ycd` / `.yed` okuyamaz** → "Imported in 0.0 seconds"
    der, sahne boş kalır. Önce `res_to_xml.ps1`.
19. **`.ycd` format sisteminin dışında** → `target_formats` ne olursa olsun
    XML çıkar, `xml_to_ycd.ps1` şart. (Diğer 8 uzantıda `NATIVE` gerçekten
    binary yazar — `ytyp-ymap-bayraklari.md` §7.)
20. **Sollumz'un otomatik kemik tag formülü vanilla tag'leri üretmez**
    (`SKEL_Head` → hesap 21030, gerçek 31086) → `.ycd` import'unda kanallar
    `pose.bones["#31086"]` diye eşlenmemiş kalır; tag→ad eşlemesini kendin kur.
21. **Blender 4.4+ katmanlı Action**: `action.fcurves` yok
    (`layers→strips→channelbags→fcurves`) ve **action atamak yetmez, SLOT da
    bağlanmalı** (`animation_data.action_slot = act.slots[0]`) — yoksa
    fcurve'ler doğru olsa bile poz hiç değişmez.
22. **Action'ın keyframe'lemediği kemik son pozunda kalır.** Ölçüm/karşılaştırma
    öncesi pozu sıfırla, yoksa önceki denemenin kirliliğini ölçersin.
23. **Ped bileşenleri her ped'de aynı adı taşır** (`head_000_r.ydd`).
    Filtresiz çıkarmada onlarca ped aynı dosyaya yazar, sonuncusu kazanır →
    `-PathFilter 'mp_m_freemode_01'` şart.
24. **PowerShell'e `-File` ile virgüllü liste** → tek string olur, sessizce
    hiçbir şey bulunmaz. `-Command "& script.ps1 -Names @('a','b')"` kullan.
25. **`Add-Type` C# 5 derler** — `?.` null-conditional çalışmaz.

---

## 11. İNSAN DIŞI YARATIK RIG'İ — gerçek GTA iskeletiyle

### 11.0 Değişmez kural

**Custom iskelet TAMAMEN YASAKTIR.** GTA V motoru yalnızca kendi ped
iskeletini kabul eder. Sketchfab'den gelen bir yaratığın kendi armature'ı
FiveM'e taşınamaz — kemik adları, tag'leri, hiyerarşisi motorun beklediğiyle
uyuşmadığı için ped hiç yüklenmez.

| Değiştirilebilir | Değiştirilemez |
|---|---|
| Kemiğin **konumu** (head/tail) | Kemik **adı** |
| Kemiğin **boyu** | Kemik **tag**'i |
| — | Kemiğin **parent**'ı |
| — | Kemik **sayısı** (128) |

Yöntem: **doğru ped'i seç** → gerçek `.yft` iskeletini içe al → kemikleri
yaratığın anatomisine **taşı** → kullanılmayanları **kısalt** (silme) →
ağırlıklandır → imzayı doğrula.

Araç: `scripts/blender_creature_rig.py`

### 11.0.1 ÖNCE PED SEÇ — insan pedi çoğu yaratık için yanlış tercih

GTA V'te **43 kayıtlı `a_c_*` model** var (`peds.json` 1109 kayıt / `PedList.ini`),
**40'ı `Pedtype=Animal`**; `A_C_Chimp`, `A_C_Chimp_02`, `A_C_Rhesus` `civmale`
olarak kayıtlıdır ve insan rig'i taşır. Her birinin kendi iskeleti *ve kendi
animasyon seti* var. Dört ayaklı bir yaratığa `mp_m_freemode_01` giydirmek
teknik olarak çalışır ama oyunda **insan yürüyüşü** oynar. Doğru soru
"hangi hayvana benziyor" değil: **hangi iskelet yeterli uzuv zinciri veriyor,
kaç hazır klibi var ve model KAYITLI mı.**

> ⚠️ `pedrig.py animals` listesi `skeletons.tsv.gz` model adlarından üretilir,
> yani **`.yft`'i olan her şeyi** listeler — "spawn edilebilir ped" listesi
> değildir. Kayıtlılığın otoritesi `pedmodelinfo` (`peds.json` / `PedList.ini`).
> Fark ölçüldü: plugin 44, kayıtlı 43, fazlalık **`a_c_whalegrey`**.

```bash
python scripts/pedrig.py animals                 # klip sayisina gore sirali
python scripts/pedrig.py animals a_c_rottweiler  # zincir dokumu
```

Ölçülmüş sonuç — `creatures@<aile>@`. ⚠ **`Kayıt` ham satırdır, `Klip`
benzersizdir — ikisi aynı şey değildir** (bu belgenin E5 kuralı). `Kayıtlı`
kolonu `peds.json`/`PedList.ini`'dendir.

| Ped | Kemik | Zincirler | Kayıt | **Klip** | Sözlük | Kayıtlı | Pedtype |
|---|---|---|---:|---:|---:|---|---|
| **`a_c_rottweiler`** | 82 | 6·6·5·5·5·3 | 382 | **228** | 27 | evet | Animal |
| `a_c_retriever` | 77 | 6·6·5·5·5·3 | 113 | **80** | 15 | evet | Animal |
| `a_c_coyote` | 74 | 6·6·5·5·5·3 | 106 | **64** | 16 | evet | Animal |
| `a_c_mtlion` / `panther` | 72 | 6·6·5·5·5·3 | 80 | — | — | evet | Animal |
| `a_c_killerwhale` | 20 | **7** (tek zincir, `Tail0..4`) | 32 | **15** | 2 | evet | Animal |
| `a_c_humpback` | 18 | **10** (`Tail0..4` + `L_TailFin_00..01`) | 13 | **13** | 1 | evet | Animal |
| `a_c_sharktiger` | 19 | 7 (tek zincir) | 26 | **25** | — | evet | Animal |
| `a_c_rhesus` / `chimp` | 92-94 | **7·7**·4·4 | 2 | 2 | — | evet | **civmale** |
| ~~`a_c_whalegrey`~~ | 22 | 10 (tek zincir) | **0** | **0** | 0 | **HAYIR** | — |

**Klip sayısı 0 = uyarı işareti.** `a_c_whalegrey`'in iskeleti gerçekten en uzun
tek seriye sahip (`SKEL_Spine_Root → SKEL_Pelvis → SKEL_Tail_00..07` = 10 kemik)
ama modelin `pedmodelinfo` girdisi yok. İki kayıt listesinde de olmaması +
0 klip **güçlü karinedir**: kullanma. (`CreatePed` ile denenmedi — G12.)
Model doğru, **kullanılabilirlik şüpheli** — bu ayrımı her ped seçiminde
ayrıca sor.

- **Dört ayaklıların HEPSİ aynı kalıpta**: 2 ön bacak (6 kemik), 2 arka bacak
  (5), kuyruk (5), boyun (3). Aralarındaki fark kemik sayısı değil, **klip
  sayısı** — o yüzden dört ayaklı bir yaratıkta `a_c_rottweiler` neredeyse
  her zaman doğru seçimdir (382 klip, ikincisinin 3 katı).
- **Uzun tek zincir gerekiyorsa** (yılan, yılanbalığı, solucan):
  `a_c_killerwhale` **7** kemiklik kuyruk serisi + **15 klip** (32 kayıt) verir;
  `a_c_humpback` aynı zincir şeklini **10** kemikle ve 13 klip ile verir
  (ikisi de kayıtlı); üçüncü seçenek `a_c_sharktiger` (7 / 25 klip).
  Dört ayaklıların kuyruğu yalnızca 5. **`a_c_whalegrey`'e uzanma** — 10'luk
  seri onda ama model iki kayıt listesinde de yok ve 0 klipli
  (yukarıdaki tablo).
- **Uzun kol gerekiyorsa**: `a_c_rhesus`/`chimp` 7 kemiklik kol verir, ama
  hazır klip yok denecek kadar az (2) ve bu üç model `Pedtype=civmale`'dir,
  yani **insan rig'i** taşır — hayvan animasyon setine erişemezler.
- `_02` varyantları (`a_c_chop`, `a_c_rottweiler_02`) 1-2 kemik farklı ve
  **isimleri de tag'leri de farklı** (`SPR_Gonads_ROOT`/49118 vs
  `SPR_GonadsROOT`/56895) — birbirinin yerine geçmez.

**`skeletons.tsv.gz` sayım tuzağı:** satır saymak kemik saymak değildir.
Bazı ped'ler hem `.yft` hem `.ydd` kaynağından gelir, **ayrıca aynı kaynakta
kemikler iki kez yazılmış olabilir** (model birden fazla RPF'te). Ölçüldü:
`a_c_mtlion_02` → 144 satır, 72 benzersiz `boneIndex`, `boneCount` alanı da
72 diyor. Tekilleştirmeyen kod "bu ped iki kat zengin" der ve yanlış iskelet
seçtirir. (`assetdb.py bones` bunu kendisi tekilleştirir; uyarı `.tsv.gz`'yi
doğrudan okuyan kod için geçerli.)

### 11.0.2 Ped −Y yönüne bakar — yön uyuşmazlığı ped'i geri geri yürütür

Ölçüldü (`a_c_rottweiler` rest pose): `SKEL_Head` y = **−0.286**,
`SKEL_Tail_05` y = **+0.509**. Yani GTA ped konvansiyonunda **baş −Y, kuyruk
+Y, üst +Z**.

Sketchfab'den gelen model bunun tersine bakıyor olabilir. Düzeltme mesh
tarafında yapılır (iskelette değil):

```python
M = Matrix.Rotation(math.pi, 4, 'Z') @ obj.matrix_world
obj.data.transform(M)                 # veriye uygula
obj.matrix_world = Matrix.Identity(4) # dunya matrisi birim kalsin
```

Bu adım atlanırsa rig kusursuz görünür, doğrulamalar geçer, ped oyunda
**yürüme yönünün tersine** hareket eder.

```python
exec(open(r"<PLUGIN>/scripts/blender_creature_rig.py").read())
cr = CreatureRig("gta_rig", "GladeMonster")
cr.snapshot()                                    # ad -> (tag, parent)
cr.place_chain(KUYRUK_ZINCIRI, kuyruk_noktalari) # N kemik -> N+1 nokta
cr.place_chain(ON_BACAK_L,     sol_on_noktalari)
cr.park()                                        # kalanlari ~12 mm'ye indir
cr.skin()                                        # bilesen tabanli agirlik
cr.verify(pose=TEST_POZU)                        # IMZA_AYNI true olmali
```

### 11.1 Uzuv eşlemesi topolojiktir, anatomik değil

"Yaratığın 6 bacağı var ama köpeğin 4" diye durma. Önemli olan **seri
uzunluğu** ve zincirin **kaç bükümü temsil edebildiği**: N kemiklik zincir
N−1 büküm taşır.

Bükümü ölç, tahmin etme — `yol / kuş uçuşu` oranı:

```python
yol = np.linalg.norm(np.diff(H, axis=0), axis=1).sum()
oran = yol / np.linalg.norm(H[-1] - H[0])       # 1.0 = düz
```

Gerçek ölçüm (6 bacaklı akrep yaratık, `a_c_rottweiler` iskeleti):

| Uzuv | Eğrilik | Verilen zincir |
|---|---|---|
| Ön bacaklar | **2.11-2.44×** (en bükümlü) | `Clavicle→UpperArm→Forearm→Hand→Finger00→01` (6) |
| Arka bacaklar | 1.92-2.00× | `Thigh→Calf→Foot→Toe0→Toe1` (5) |
| Orta bacaklar | **1.55-1.69×** (en düz, tek büküm) | `MH_L/R_ShoulderBladeRoot→ShoulderBlade` (2) |
| Kuyruk | 5.91 m yay | `Tail_01..05` (5) |
| Gövde | — | `Spine_Root→Spine0..3` + `PelvisRoot→Pelvis1→Pelvis` (8) |
| Kafa | — | `Neck_1→Neck_2→Head` (3) |

82 kemiğin **42**'si uzuvlara, **29**'u kafa bloğuna gitti, 11'i uç/park.

**Fazladan uzuv nereye asılır:** serbest 2 kemiklik zincir
`MH_L/R_ShoulderBladeRoot → MH_L/R_ShoulderBlade`'tir. Bunlar
`SKEL_L/R_Clavicle`'ın çocuklarıdır, yani **ön bacak hareketini miras alır**.

> ⚠️ **Bu zincir yalnız KÖPEK iskeletlerinde var** — 43 hayvan pedinin 5'i:
> `A_C_Chop`, `A_C_Chop_02`, `A_C_Rottweiler`, `A_C_Rottweiler_02`,
> `A_C_shepherd`. `a_c_mtlion` / `coyote` / `deer` / `cow` / `pig`
> iskeletlerinde **yoktur**; oralarda fazladan uzva verilecek serbest zincir
> aramak gerekir. Tag'ler: sol `34577 → 20143`, sağ `14858 → 21679`.
> Yukarıdaki akrep ölçümü `a_c_rottweiler` üzerinde yapıldı — o yüzden geçerli.
> **Başka ped seçtiysen `pedrig.py <ped>` ile kemiğin varlığını doğrula.**

`a_c_rottweiler.yed` ölçümü bunu doğruluyor — expression **girişleri** arasında
`SKEL_L_Clavicle` ve `SKEL_R_Clavicle [BoneRotation]`, **çıkışları** arasında
`34577 MH_L_ShoulderBladeRoot [BoneRotation]`, `20143 MH_L_ShoulderBlade
[BonePosition]` var. Yani omuz küreği klavikulanın dönüşünden **prosedürel
olarak** sürülüyor.

İki yapılandırma mümkün, ikisi de geçerli:

- **Expression bağlı kalırsa** → orta bacaklar ön bacaklar adım attıkça
  kendiliğinden hareket eder, ek animasyon yazmaya gerek yok. Ama `MH_`
  kemiklerine **keyframe yazamazsın** — expression her karede üzerine yazar.
- **Expression bağlanmazsa** → `MH_` kemikleri serbest kalır, kendi
  kliplerinde orta bacakları istediğin gibi sürersin. Vanilla köpek klipleri
  onlara dokunmaz, klavikulayla birlikte hareket ederler. Yay kemikleri
  (`SPR_` kulak/gonad) da ölür — yaratıkta karşılığı yoksa kayıp değil.

Kendi animasyonunu yazacaksan ikincisi doğru seçim.

### 11.2 Zincir yerleştirme — N kemik, N+1 nokta

Bir zincirin son kemiğine ayrı bir nokta kalmazsa o kemik güdükte kalır.
Ölçüldü: 7 kemik 7 noktayla yerleştirildi → `SKEL_Head` **0.02 m** boyunda
kaldı ve **0 vertex** sürdü, kuyruğun ucu poz verirken hiç oynamadı.
`verify()` bunu `olu_kemik` listesinde raporlar; liste boş olmalı.

`place_chain()` eğriyi yay uzunluğuna göre yeniden örnekler, yani ham merkez
hattını kaç noktayla çıkardığın önemli değil.

### 11.3 Merkez hattı — üç yöntem, ikisi belirli durumlarda çöker

| Yöntem | Nerede çalışır | Nerede çöker |
|---|---|---|
| BFS / geodezik | bütün mesh | **parçalı mesh** — 1.89 m bacak **0.15 m** çıktı |
| PCA dilimleme (`centerline()`) | düz, tek eksenli uzuv | kıvrılan uzuv |
| **3B yürüyüş (`march()`)** | kıvrılan / ters-V uzuv, kuyruk | — |

**Örümcek bacağı ve kıvrık kuyruk tek eksene göre dilimlenemez.** Bacak
gövdeden yukarı çıkıp ayağa iner (ters V); çıkan ve inen kısım **aynı dilime
düşer**, ortalamaları alınır ve hat bozulur. Ölçüldü: ayak z=0.43 iken
XY dilimlemesi z profilini `1.28 → 1.69 → 1.39 → 1.31 → 1.16 → 1.42 → 1.08`
diye zigzag verdi ve **hat hiç ayağa ulaşmadı**; aynı bacak `march()` ile
`0.43 → 0.62 → 0.78 → 0.98 → 1.26 → 1.65 → 1.88 → 2.09 → ... → 2.37`
şeklinde tek yönlü çıktı.

`march()` her adımda ilerideki kürenin **ileri yarısının** ortalamasını alır
ve yönü günceller, böylece kıvrımı takip eder. **Ayaktan gövdeye doğru
başlat** — ayak konumu kesin, gövde bağlantısı tahminidir. Yürüyüş uzvun
gövdeye bağlandığı yerde kendiliğinden durur (vertex kalmaz); bu bitiş
noktası eklem konumudur.

### 11.4 Kullanılmayan kemikleri sil değil, park et

Silmek imzayı bozar. Doğrusu ebeveynin başına indirip ~12 mm'ye çekmek.
Ağırlıklandırma uzunluk filtresi kullandığı için park edilmiş kemik hiç
vertex almaz → mesh'i etkilemez, oyuna tam kemik sayısıyla gider.

**`IK_*` / `PH_*` kemiklerini park etme, uzuv ucuna koy.** `IK_L_Foot`
motorun ayak yerleştirmesinde kullandığı hedef, `PH_R_Hand` prop takma
noktasıdır. Ebeveynin başında bırakılırsa ayak IK'sı yanlış yere çalışır.

**Eşik `> 0.05` YAZMA — float32 tuzağı.** Blender kemik uzunluğunu float32
tutar; float32'deki 0.05 (0.050000000745…) Python'un double 0.05'inden
**büyüktür**. Sollumz tüm kemikleri tam 0.05'e sabitlediği için `length > 0.05`
karşılaştırması **hepsini geçirir**. Ölçüldü: 82 kemikli rig'de ağırlık alan
kemik 43 yerine **77** çıktı, kafanın 29 kemiği de dahil oldu ve kafa
ağırlığını çaldı. Doğrusu `MIN_LEN = 0.06` ya da açık kemik listesi
(`skin(bones=[...])`).

Ölçüm: 42 uzuv + 29 kafa bloğu kullanıldı, **11 park/uç**, `IMZA_AYNI: true`.

### 11.4.1 Kafa: zincir değil, KATI BLOK

Kafanın iç yapısı (25 `FB_` yüz kemiği + 2 `SPR_` kulak + `IK_Head`)
korunmak zorundaysa kafa zincir olarak yerleştirilemez — **saf ötelemeyle**
blok halinde taşınır (`move_block()`). Öteleme kemikler arası tüm göreli
konumları ve tüm kemik boylarını aynen bırakır. Ölçüldü: iç yapı sapması
**3e-8 m**, kemik boyu sapması **1.15e-7 m** — pratikte sıfır.

Sonuç: kafa kemiği kısa kalır (0.05 m) ve mesafe modelinde **hiçbir vertex
kazanamaz**. Kafa geometrisini ona bağlamanın yolu ağırlık maskesidir:

```python
cr.skin(bones=UZUVLAR, force={"SKEL_Head": lambda P:
        np.clip((-1.30 - P[:,1]) / 0.28, 0, 1) * (np.abs(P[:,0]) < 1.15)})
```

**Bileşen bazlı zorlama burada işe yaramaz** — kafa çoğu modelde gövdeyle
aynı bağlı bileşenin parçasıdır, bileşen merkezi gövdenin ortasına düşer ve
hiçbir bileşen kafa bölgesinde çıkmaz (ölçüldü: `kafa_bileseni: 0`). Maske
**vertex bazlı** olmalı ve boyunda **yumuşak geçmeli**, yoksa boyunda kırılma
olur.

### 11.5 Parçalı mesh'te ağırlıklandırma — asıl zorluk

Mekanik/zırhlı yaratıklar tek bir kabuk değil, **binlerce ayrı katı
parçadır**. Ölçüldü (Glade Monster, 223.069 vertex): **10.021 bağlı bileşen**,
sadece **1** tanesi 5000 vertex'ten büyük, **9.935**'i 500'ün altında.

Bunun iki sonucu var:

1. **Blender'ın otomatik ağırlıklandırması çalışmaz.** `parent_set(
   type='ARMATURE_AUTO')` → *"Bone Heat Weighting: failed to find solution
   for one or more bones"* ve tüm vertex'ler ağırlıksız kalır. Sebep kopuk
   parçalardır, kemik yerleşimi değil — kemikleri düzeltmekle geçmez.
2. **Düz mesafe ağırlığı parçaları yırtar.** Bir plakanın vertexleri 4 farklı
   kemiğe dağılırsa poz verildiğinde plaka gerilir.

Ölçülmüş karşılaştırma (531.010 kenar):

| Yöntem | Ort. gerilme | %99 | 2 katı aşan kenar |
|---|---|---|---|
| Düz mesafe (inverse-cube, top-4) | 1.2585 | 5.042 | **%5.94** |
| + bileşen çapı < 0.40 m katı bağlama | 1.1989 | — | %4.78 |
| + eşik **0.80 m** + Laplacian düzeltme | 1.0656 | 2.177 | %1.19 |
| **doğru ped + anatomik zincir eşlemesi** | **1.0011** | 1.08 | **%0.094** |

Son satır ayrı bir yöntem değil: aynı ağırlıklandırma, ama iskelet yaratığın
anatomisine **oturduğu** için kemikler mesh'i zorlamıyor. İnsan iskeletiyle
%1.19 olan gerilme, dört ayaklı iskeletle **%0.094**'e düştü. En büyük
kazanç algoritmadan değil, **doğru ped seçiminden** geldi.

**Kural:** çapı eşiğin altındaki her bileşen, ortalama ağırlığı en yüksek
**tek kemiğe %100** bağlanır. Katı cisim dönüşümü kenar uzunluğunu korur,
yani o parçada gerilme matematiksel olarak imkânsızdır. Kalan büyük
bileşenlerde 4 kemikli yumuşak ağırlık kurulur, komşu ortalamasıyla **6 adım
Laplacian düzeltme** uygulanır, sonra yeniden top-4 + normalize edilir.

**Eşiği düşük tutma.** 0.40 m ile denendiğinde 0.42–0.55 m'lik tekrar eden
mekanik parçalar yumuşak tarafta kaldı ve kenarlarının **%50-67'si** yırtıldı;
kötü kenarların yarısı bu 9 parçadan geliyordu. 0.80 m'ye çıkarınca sorun
kayboldu. Ana gövde (3.52 m, 26.620 vertex) yumuşak tarafta kaldı ve orada
kötü kenar oranı zaten **%6** ile sınırlıydı.

GTA kuralları (4 etki / toplam 1.0 / 1/255) **düzeltmeden sonra** uygulanır;
önce uygulanırsa Laplacian adımı toplamı tekrar bozar.

### 11.5.1 "Kemikler birleşik değil" — bu GTA'da HATA DEĞİL

Ölçüm (vanilla `a_c_rottweiler` vs bu yöntemle kurulan rig):

| | Kurulan rig | **Vanilla `a_c_rottweiler`** |
|---|---|---|
| `use_connect = True` kemik | 0 | **0** |
| Ebeveyn ucuna değen kemik (<1 mm) | 33 | **0** |
| Eklem mesafesi ort. / rig boyu | %8.1 | %9.3 |
| Eklem mesafesi maks / rig boyu | %29.8 | %25.9 |

**Vanilla GTA rig'inde tek bir kemik bile ebeveyninin ucuna değmiyor.** Sebep:
`.yft`'te gerçek veri kemiğin **head konumu + hiyerarşi**dir; Sollumz her
kemiğe 0.05 m'lik sentetik bir tail uydurur. Blender'da "kopuk" görünmek
normaldir, oyunda hiçbir şeye yol açmaz. Oranlar da vanilla ile aynı bantta.

Gerçekten hata olan şey ayrı: **kemiğin sürdüğü geometrinin dışında kalması.**

### 11.5.2 Bölgenin ağırlık merkezi BOŞ UZAYA düşebilir

Bu, imza/ağırlık/gerilme denetimlerinin **hiçbirinin** yakalamadığı bir kusur.

Ölçülen vaka: yaratığın "kafa" diye ayrılan ön bölgesinin (y < −1.45) x
histogramı **`[0, 958, 462, 0, 2, 0, 1461, 0, 0]`** çıktı — kütle iki yanda,
**merkez şerit boş** (2 vertex). Orası kafa değil, iki yandan sarkan
**çenelerdi**. Bölgenin ağırlık merkezi ikisinin ortasına, yani boşluğa düştü;
`SKEL_Head` mesh'e **0.499 m** uzakta asılı kaldı. Gerçek yüz gövdenin ön
yüzünde, **z ≈ 1.76**'daydı.

Sonuç: `IMZA_AYNI` true, ağırlık kuralları temiz, gerilme %0.09 — her şey
"geçti", ama kafa yanlış eksen etrafında dönüyordu.

**Kural:** bir bölgeyi kemiğe atamadan önce eksen histogramına bak. Ortası boş
çıkarsa o bölge tek bir organ değil, **iki ayrı kütledir**; kemiği ortalamaya
değil, gerçek yoğun kütleye koy.

Düzeltme sonrası `SKEL_Head` mesh mesafesi **0.499 m → 0.012 m**.

### 11.6 Doğrulama — dört şey birden

`verify()` dördünü de raporlar, hepsi geçmeden iş bitmiş sayılmaz:

1. **`IMZA_AYNI: true`** — ad+tag+parent haritası başlangıçtakiyle birebir.
   Kemik eklemek/yeniden adlandırmak Blender'da hiçbir uyarı üretmez;
   hata oyunda ped hiç yüklenmeyerek ortaya çıkar.
2. **GTA ağırlık kuralları** — `4ten_fazla: 0`, `agirliksiz: 0`,
   `toplam_sapma: 0`.
3. **Gerilme testi** — bir test poz verilip kenar uzunluğu oranı ölçülür.
   `2x_asan_%` %1-2 bandında olmalı; %5 üstü parça bağlama eşiğinin düşük
   olduğunu gösterir.
4. **`GEOMETRI_DISI`** — her kemiğin sürdüğü mesh'e uzaklığı. Listede
   çıkması beklenenler: `SKEL_ROOT` (zeminde olmalı, vanilla'da da öyle) ve
   gövde içi omurga kemikleri (kabuk kalınlığı kadar ölçülür). **Bir uzuv ya
   da kafa kemiği listeye düşerse kusurdur** — §11.5.2.

Ayrıca `olu_kemik` listesi boş olmalı. **Bu testi kemik uzunluğuna bağlama:**
blok taşınan kafa kemiği kısadır (0.05 m) ama `force` maskesiyle ağırlık alır;
uzunluk testi onu yanlış yere "ölü" der. Tek doğru ölçüt vertex grubunda
sıfırdan büyük ağırlık olup olmadığıdır.

### 11.7 Ek tuzaklar

- **`bpy.ops.render.opengl(view_context=False)` armature ÇİZMEZ.** Kemikleri
  görmek için ya viewport screenshot al ya da kemikleri geçici mesh'e çevir.
  `show_in_front=True` bu render yolunda hiçbir şey değiştirmez.
- **Mesh viewport'ta gizliyse (`hide_get() == True`) OpenGL render'a girmez**
  ve boş kare üretir; `hide_render` False olsa bile. Render öncesi
  `obj.hide_set(False)`.
- **Kamerayı yerel koordinatla kurma.** `to_mesh()` yerel uzayda vertex verir;
  import edilmiş mesh'in `matrix_world`'ünde −90° X dönüşü olabilir →
  kamera tamamen boşluğa bakar. Sınırları dünyaya çevirdikten sonra çerçevele.
- **`.yft` import'u `SKEL_ROOT` adlı bir MESH ve ped gövdesini de sahneye
  bırakır**; yaratıkla birlikte render'a girip kadrajı bozar → `hide_render`.
  Hayvan `.yft`'i ayrıca onlarca `<kemik>.col` collision mesh'i getirir ve
  *"No bone exists for the physics group ...physicsbody"* uyarıları basar —
  uyarılar zararsız, `.col` objeleri silinebilir.
- **PowerShell 7'de `Add-Type` çöker.** .NET 8+ altında `HashSet<>`,
  `Console`, `Regex` gibi tipler netstandard'dan *forward* edilmiştir;
  `-ReferencedAssemblies` listesine `System.Collections`, `System.Runtime`,
  `System.Console` eklenmezse *CS1069: type has been forwarded* /
  *CS0103: Console does not exist* hatası verir. Windows PowerShell 5.1'de
  sorun çıkmaz, PS7'de her seferinde çıkar. Plugin'deki 14 script düzeltildi.

### 11.8 FiveM bunu nasıl tanır — dağıtım yolu

Rig bitince ortada hâlâ bir `.blend` var; oyunun tanıması için ped **dosya
kimliği** kazanmalı. İki yol var ve zorluğu çok farklı.

**A) Vanilla ped'i DEĞİŞTİR (basit, önerilen ilk adım)**

Dosyaları taban aldığın ped'in adıyla üret ve stream'e koy:

```
resource/
  fxmanifest.lua        -> stream/ otomatik yuklenir, ek bildirim yok
  stream/
    a_c_rottweiler_02.yft  <- iskelet + fizik
    a_c_rottweiler_02.ydd  <- drawable (+ GOMULU dokular)
```

**Doku gömülüyse `.ytd` GEREKMEZ** — ayrıntı §12.3. Hangi ped'i hedef
alacağını da veriye bakarak seç: vanilla `a_c_rottweiler` (baz) `.ydd`
içermez, tam set yalnız **`a_c_rottweiler_02`**'de vardır.

Hiçbir metadata gerekmez. Oyun bu ped'i zaten tanıdığı için:

- `creatures@rottweiler@` altındaki **382 klibin hepsi** çalışır,
- `GetHashKey('a_c_rottweiler')` ile spawn edilir,
- ped'in `.yed` expression'ı, ses seti, davranışı hazır gelir.

Bedeli: **dünyadaki tüm rottweiler'lar** bu yaratık olur. Test ve tek-yaratıklı
senaryolar için sorun değil; köpek de lazımsa değil.

**B) Addon ped ekle**

`peds.meta` + `pedpersonality.meta` yazıp `fxmanifest.lua`'da `data_file`
ile bildirmek gerekir. Bu dosyaların **tam anahtar adları bu plugin'in
verisinde doğrulanmadı** — yazmadan önce çalışan bir addon ped kaynağından
teyit et, ezberden yazma. Yanlış anahtar sessizce yüklenmez.

**Her iki yolda da geçerli:**

- **Asset değişince sunucudan çıkıp yeniden bağlan** — `restart` yetmez,
  FiveM stream dosyalarını cache'ler.
- `.yft` yalnız iskeleti değil **fragment physics**'i de taşır. Yaratık
  vanilla ped'den çok büyükse (ölçüldü: 6.4 m'ye karşı köpekte ~1 m)
  çarpışma kapsülü ve fizik sınırları da yeniden üretilmelidir; iskelet
  doğru olsa bile bu yapılmazsa ped dünyayla yanlış çarpışır. Nasıl
  üretileceği: **§12.5-12.7**.
- Ped ölçeğini `SetPedScale`/model ölçeğiyle "düzeltmeye" çalışma; boyut
  iskelette ve fizikte tanımlıdır.

---

## 12. YARATIĞI FiveM'E ÇIKARMA — ölçülmüş export hattı

Rig bittikten sonra `.ydd` + `.yft` üretme adımları. Her sayı gerçek bir
export'tan alındı.

### 12.1 Poligon bütçesi — vanilla referansı

`a_c_rottweiler_02.ydd` (gerçek oyun dosyası): **11.303 üçgen / 9.273 vertex**,
5 drawable model, shader `ped.sps` / `ped_fur.sps` / `ped_hair_cutout_alpha.sps`.

Sketchfab yaratığı ham haliyle **321.562 üçgen / 222.999 vertex** — **28 katı**.
Bu haliyle çıkarılmaz. İki aşamada indirildi:

| Aşama | Üçgen | Vertex | Bileşen |
|---|---|---|---|
| ham | 321.562 | 222.999 | 10.021 |
| çapı < 5 cm parçaları at | 273.928 | 174.731 | 4.840 |
| decimate (collapse) | **20.000** | **28.042** | 4.840 |

- **Küçük parçaları önce at.** Bileşenlerin **medyan çapı 4.7 cm**; 6.4 m'lik
  bir yaratıkta 5 cm altı oyunda görünmez. 5.181 parça atıldı = vertexlerin
  **%21,6**'sı. Bu yapılmazsa vertex sayısı dibe vurmaz: her bileşen en az
  3-4 vertex ister, 10.021 bileşen yaklaşık **30.000 vertex tabanı** demektir
  (ölçüldü: %3.5 decimate'te bile 33.469 vertex).
- **Decimate hiçbir bileşeni yok etmez** (collapse en az bir üçgen bırakır).
  Asıl kayıp küçük parçaları elle atarken olur ve orası kontrollüdür.

### 12.2 Decimate GTA ağırlık kuralını BOZAR

Vertex birleştirme etkileri toplar. Ölçüldü: decimate sonrası **750 vertex**
4'ten fazla kemik etkisi aldı (8'e kadar). Export bunu şikâyet etmez; hata
oyunda bozuk deformasyon olarak çıkar.

**Decimate'ten sonra kuralları yeniden uygula:** en büyük 4 etkiyi tut,
normalize et, 1/255 altını ele, tekrar normalize et. Sonrası ölçüm:
dağılım `{1: 25297, 2: 496, 3: 256, 4: 1993}`, 4'ten fazla **0**,
ağırlıksız **0**, sapma **0**.

### 12.3 Materyal ve doku

- Shader `ped.sps` kullan. En güvenlisi vanilla bir ped'in materyalini
  **kopyalamak** — round-trip'te `Name=ped / FileName=hash_203B2307` çıktı,
  vanilla ile birebir aynı.
- **Ped shader'ı `UVMap 0` + `UVMap 1` ve `Color 1` + `Color 2` bekler.**
  Yoksa export "missing UV maps / color attributes ... rendering issues
  in-game" uyarısı verir. Sketchfab mesh'inde tek `UVMap` gelir → yeniden
  adlandır, ikinciyi kopyala, renk katmanlarını beyaz ekle.
- **Dokular GÖMÜLÜ olursa ayrı `.ytd` GEREKMEZ.** Her `TEX_IMAGE` node'unda
  `texture_properties.embedded = True` ve dosyalar **DDS** olmalı.
  Ölçüldü: 3 doku (512+128+128) gömülü, `.ydd` 1.5 MB, `.ytd` yok.
- **Sollumz `.ytd` ÜRETEMEZ** — `sollum_type` listesinde texture dictionary
  yok. Gömmezsen `.ytd`'yi CodeWalker ile elle yapman gerekir.
- **Blender DDS YAZAMAZ.** Sıkıştırmasız A8R8G8B8 başlığı elle yazılabilir:
  4 bayt "DDS " + **tam 124 bayt** header (7x4 + 44 reserved + 32
  pixelformat + 4 caps + 16 kuyruk), toplam **128 bayt**, sonra BGRA piksel.
  Blender pikselleri **alttan üste**, DDS **üstten alta** — dikey çevirmezsen
  doku ters çıkar.

### 12.4 `.yft` küçük olmalı — görsel `.ydd`'den gelir

İlk denemede drawable olduğu gibi fragment'a da kondu: `.yft` **1.518.235**
bayt çıktı (vanilla 17.947). Ped'de `.yft` yalnız **iskelet + fizik** taşır.

Çözüm: export sırasında drawable model'in **mesh verisini geçici olarak
8 vertexlik yer tutucuyla değiştir** (nesne/armature bağı korunur, iskelet
çözümlenir), dokuların `embedded`'ını kapat, export et, geri al.
Sonuç: **23.700 bayt**.

Yer tutucuyu boş bir Empty yapma — fragment export'u `drawable.skeleton`
arar ve `AttributeError: 'NoneType' object has no attribute 'skeleton'`
ile çöker.

### 12.5 Fragment fiziği — kapsül üretimi

Vanilla `a_c_rottweiler`: `Physics/LOD1` → Archetype + **20 Group / 20 Child**
+ Composite içinde **20 Capsule**. Üretilen yaratıkta 6 bacak + kuyruk olduğu
için **32 kapsül**.

**Kapsül parametreleri mesh'ten DEĞİL, `sz_bound_shape`'ten gelir:**

```python
o.sollum_type = "sollumz_bound_capsule"
o.sz_bound_shape.capsule_radius = r
o.sz_bound_shape.capsule_length = cyl     # SILINDIR kismi, kaplar haric
```

**Mesh'i kendin üretme.** Sollumz `depsgraph_update_post` handler'ıyla kapsül
geometrisini bu iki değerden yeniden kurar. Kendi mesh'ini atarsan Sollumz
parametreleri senin mesh'inin bbox'ından geri okur ve değerlerin silinir —
ölçüldü: 32 kapsülün hepsi küreye döndü (`capsule_length` 0). Doğru sırayla
yazınca vertex 482 → 660 olur ve bbox `r x (cyl+2r) x r` çıkar.

**GTA kuralı: toplam boy > çap.** Silindir kısmı 0 olan (küre) kapsül
export'ta reddedilir:
`RuntimeError: [BOUND_CAPSULE_LENGTH_INVALID] Capsule length must be greater
than the diameter (received 1.0978317, expected >1.0978318)`.
Gövde gibi tıknaz yerlerde `cyl` doğal olarak 0 çıkar → tabana **>= 0.03 m**
koy. Ölçüldü: 32 kapsülün 6'sı bu yüzden düzeltildi.

**Kapsül ölçüsünü kemik boyundan değil, kemiğin SÜRDÜĞÜ vertex bulutundan
türet:** eksen = kemik yönü, uzunluk = izdüşümün %3-%97 aralığı, yarıçap =
dik mesafenin yüzdeliği. Uzuvlarda yarıçapı `0.42 x uzunluk` ile sınırla;
yoksa eklemdeki geniş plakalar yüzünden kapsül küreye döner (ölçüldü:
`R_Hand` yarıçap 0.75 / uzunluk 0.52).

### 12.5.1 ⛔ Sollumz'un yazdigi ped fizigi OYUNU COKERTIR

**Bu bolumdeki kapsul uretimi teknik olarak dogru calisir ama sonuc oyunda
CRASH verir.** Olculdu, tahmin degil.

Belirti: ped modeli oyuncuya uygulandiktan ~4 saniye sonra oyun kapanir.

```
[103297] MainThrd/ [glade] model giyildi (a_c_chop_02)
[107281] DumpServer/ Process crash captured.
         GTA5_b3258.exe+1691021
         Legacy crash hash: september-ceiling-network
```

Stack tamamen motorun icinde, script tarafinda degil.

**Sebep:** uretilen `.yft` ile vanilla `.yft` arasindaki TAM yapisal fark:

| `Physics/LOD1` alt dugumu | Sollumz ciktisi | Vanilla |
|---|---|---|
| `Archetype`, `Transforms`, `Groups`, `Children`, damping'ler | var | var |
| **`ArticulatedBody`** | **YOK** | var |
| **`UnknownData1` / `UnknownData2`** | **YOK** | var |

Kapsullerin kendisi kusursuz: `Inertia`, `CompositeTransform`, `MaterialIndex`,
`BoneTag`, `Mass` alanlarinin hepsi vanilla ile ayni yapida ve dolu. Sorun
tek tek bound'larda degil, **eklem/ragdoll tanimininin hic olmamasinda**.

`ArticulatedBody` ped'in ragdoll artikulasyonudur. Fizik gruplari VARDIR ama
onlari birbirine baglayan eklem yapisi YOKTUR; motor ped'i fiziklestirirken
bu yapiyi kurmaya calisir ve coker.

**`ArticulatedBody` dizesi Sollumz'un TAMAMINDA gecmiyor** — ne eklentide ne
`szio` kutuphanesinde:

```bash
grep -rn "ArticulatedBody\|articulated_body" <sollumz_kok> --include=*.py   # 0 sonuc
```

Yani bu bir ayar hatasi degil, **Sollumz ped fragment fizigini eksik yaziyor**.
`bone.sollumz_use_physics` + bound composite + `COPY_TRANSFORMS` bagi hepsi
dogru kurulsa, export "0 uyari" verse bile sonuc coker.

**Yapilacak:** ped `.yft`'ini **fiziksiz** gonder. Physics dugumunu XML'den
cikarip yeniden derle:

```python
t = ET.parse("<ped>.yft.xml"); r = t.getroot()
r.remove(r.find("Physics"))
t.write("nophys.yft.xml", encoding="utf-8", xml_declaration=True)
```

```bash
powershell -File scripts/xml_to_res.ps1 -XmlPath nophys.yft.xml -OutPath nophys.yft
```

Sonuc: 23.700 -> **16.343 bayt**; round-trip'te 82 kemik / 82 tag korunur,
`Drawable` + `BoneTransforms` yerinde, `Physics: YOK`.

**Bedeli:** ragdoll ve mermi carpismasi calismaz. Ped yuklenir, gorunur,
animasyon oynar, yurur. Gercek fizik isteniyorsa `ArticulatedBody`'yi
CodeWalker ile elle eklemek ya da vanilla bir `.yft`'in Physics blogunu
grafting yapmak gerekir — Sollumz bu isi yapamaz.

**Genel ders:** export'un "0 uyari" vermesi dosyanin dogru oldugunu
GOSTERMEZ. Vanilla muadiliyle **yapisal diff** al; sadece alan degerlerini
degil, **hangi dugumlerin hic olmadigini** karsilastir.

### 12.6 Bound → kemik bağı: COPY_TRANSFORMS constraint

Kapsülü `<kemik>.col` diye adlandırmak **yetmez**. Sollumz bağı constraint'ten
okur (`get_child_of_bone`) ve fonksiyonun adı `child_of` olsa da aradığı tip
**`COPY_TRANSFORMS`**'tur:

```python
con = obj.constraints.new("COPY_TRANSFORMS")
con.target = armature; con.subtarget = kemik_adi
con.mix_mode = "BEFORE_FULL"; con.target_space = "POSE"; con.owner_space = "LOCAL"
```

`owner_space="LOCAL"` + `mix_mode="BEFORE_FULL"` kemik parenting'i taklit
eder: objenin **yerel** transformu kemik uzayındaki ofset olarak korunur.
Kapsülü armature uzayında konumlayıp kemik uzayına çevir:

```python
obj.matrix_basis = bone.matrix_local.inverted() @ istenen_dunya_matrisi
```

Ölçüldü: dünya sapması **7e-7**. Bağ kurulmazsa export şunu yazar ve o kemik
fiziksiz kalır: "Bone 'X' has physics enabled, but no associated collision!"

Ayrıca her kemikte `bone.sollumz_use_physics = True` ve her bound'da bir
**collision materyali** şart ("has no collision materials"). Yaratık için
doğru olan `ANIMAL_DEFAULT` = indeks **171**
(`ybn.collision_materials.create_collision_material_from_index`).

**Not:** vanilla `.yft`'lerde fizik grubu adları `skel_headphysicsbody`
biçimindedir, kemik adları değil — Sollumz import'ta bunları kemiğe
bağlayamaz ("No bone exists for the physics group ...") ve constraint
oluşturmaz. Yani vanilla bir ped'i içe alıp fiziğini olduğu gibi yeniden
export edemezsin; bağları elle kurman gerekir.

### 12.7 Kütle

`Mass` arayüzde yok; **kapsül başına** `obj.child_properties.mass` toplanır.
Sıfır bırakılırsa fragment kütlesiz kalır (vanilla köpek 74.19 kg).
Kapsül hacmiyle orantılı dağıt:

```python
v = pi*r*r*cyl + (4/3)*pi*r**3
obj.child_properties.mass = HEDEF_TOPLAM * v / toplam_v
```

Üretilen yaratık: 9.8 m3 kapsül hacmi → **900 kg**. Round-trip'te
`Archetype/Mass = 900`, grup başına `Mass` / `PristineMass` dolu ve
`BoneTag` kemikle eşleşiyor.

### 12.8 Round-trip doğrulama — atlanmaz

`res_to_xml.ps1` ile geri oku ve şunları gör:

| Kontrol | Beklenen |
|---|---|
| `.yft` kemik / benzersiz tag | 82 / 82, tag'ler vanilla ile aynı |
| `.yft` öteleme ölçeği | yaratık ölçeğinde (m), köpeğin cm'si değil |
| `Physics/LOD1` Groups / Children | kapsül sayısına eşit |
| `Bounds` type / children | `Composite` / hepsi `Capsule` |
| `MaterialIndex` | 171 (ANIMAL_DEFAULT) |
| `Archetype/Mass` | 0 DEĞİL |
| `.ydd` vertex layout | `GTAV1` + `BlendWeights` + `BlendIndices` |
| `.ydd` shader | vanilla ile aynı (`ped` / `hash_203B2307`) |
| gömülü doku | `.ytd` göndermeyeceksen dolu olmalı |

XML okurken etiket adını doğrula: grup kütlesi `Mass`'tır, `TotalMass` değil;
`Tag` bir `value` özniteliğidir, metin değil. Yanlış etiket "0" ya da "1
benzersiz tag" gibi sahte alarm üretir.

### 12.9 Paket

```
glade_monster/
  fxmanifest.lua          -- stream/ otomatik yuklenir, ek bildirim yok
  stream/
    a_c_rottweiler_02.ydd (1.50 MB, dokular gomulu)
    a_c_rottweiler_02.yft (23.7 KB, iskelet + fizik)
```

`.ymt` göndermeye gerek yok — ped metadata'sı değişmediği için oyunun kendi
dosyası kullanılır. Vanilla `a_c_rottweiler` (baz) `.ydd` içermez; tam set
(`ydd`+`yft`+`ymt`+`ytd`) yalnız `_02` varyantındadır, o yüzden değiştirme
hedefi olarak **`a_c_rottweiler_02`** seçildi.
