# Ped iskeleti, yüz animasyonu ve rigging — ölçülmüş referans

Kaynak: `mp_m_freemode_01.yft` / `mp_f_freemode_01.yft` / `player_zero|one|two.yft`,
`ambient.yed`, `multiplayer.yed`, `default.yed`, `p_m_zero.yed`,
154 adet `facials@*.ycd`, 8 gövde `.ycd` (84 klip). Ölçüm Blender 5.2 +
Sollumz + CodeWalker.Core ile kare kare yapıldı. **Tahmin yok — her sayı
ölçümdür.** Ölçümün nasıl tekrarlanacağı en sonda.

---

## 0. ÜÇ CÜMLEDE ÖZET

1. **Yüz animasyonu FB_ kemiklerini doğrudan sürmez.** `.ycd` soyut *float
   kanalları* oynatır (Track 22 / Track 25); bu kanalları kemik dönüşüne
   çeviren şey **`.yed` expression**'dır. Klip → kemik diye düşünmek en
   büyük hata kaynağıdır.
2. **128 kemiğin sadece 65'i klip tarafından keyframe'lenir.** Kalan 63'ü
   (MH_/RB_/EO_/SPR_/FB_ ve helper'lar) expression'dan veya hiç gelmez.
3. **Gövde klipleri scale yazmaz, uzuvlarda translation da yazmaz.** Ölçek
   (uzama/kısalma) yalnızca yüz expression'ının işidir.

---

## 1. İSKELET — 128 kemik, önek anlambilimi

`mp_m_freemode_01` ve `mp_f_freemode_01`: **128 kemik** (birebir aynı ağaç).
Hikâye karakterleri daha zengin: `player_zero` 354, `player_one` 317,
`player_two` 282 kemik (kıyafet/saç/cloth kemikleri dahil).

Önek dağılımı (`pedrig.py groups mp_m_freemode_01` — toplam tam 128):

| Önek | Sayı | Ne işe yarar | Klip keyframe'ler mi |
|---|---|---|---|
| `SKEL_` | **55** | Gerçek deforme eden iskelet. Mesh bunlara skinlenir. Bunun **30'u parmaktır** (5 parmak × 3 eklem × 2 el; `Finger0*`=başparmak → `Finger4*`=serçe). | ✅ evet |
| `FB_` | 21 | **Facial Bone** — yüzü deforme eden kemikler. | ❌ expression |
| `MH_` | 20 | **Muscle Helper** — dirsek/diz şişmesi, parmak yumrusu, saç. | ❌ expression |
| `SM_` | 8 | **Skirt/Soft Mesh** — etek panelleri. | ❌ expression |
| `RB_` | 7 | **Roll Bone** — önkol/kol/uyluk/boyun burulma dağıtımı. | ❌ expression |
| `IK_` | 6 | IK hedefi (Hand, Foot, Head, Root). Ayak/el sabitleme. | ✅ kısmen |
| `PH_` | 4 | **Physics/attach** noktası (el, ayak). Prop takma burada. | ✅ evet |
| `EO_` | 4 | Ayakkabı/topuk override (`EO_L_Foot`, `EO_L_Toe`). | ❌ expression |
| `SPR_` | 2 | **Spring** — `SPR_L/R_Breast`, yay fiziği. | ❌ expression |
| `FACIAL_` | 1 | `FACIAL_facialRoot` — tüm yüz alt ağacının kökü. | ❌ expression |

### Ağaç (kısaltılmış)

```
SKEL_ROOT (tag 0)
├── SKEL_Pelvis (11816)                    ← rest'te 90° Y, ASLA döndürülmez
│   ├── SKEL_L_Thigh (58271) → L_Calf (63931) → L_Foot (14201) → L_Toe0 (2108)
│   │                                        ├── IK_L_Foot / PH_L_Foot / EO_L_Foot
│   ├── SKEL_R_Thigh (51826) → ... (ayna)
│   ├── RB_L/R_ThighRoll, SM_*SkirtRoll
├── SKEL_Spine_Root (57597)                ← rest'te -90° Y, ASLA döndürülmez
│   └── Spine0 (23553) → Spine1 (24816) → Spine2 (24817) → Spine3 (24818)
│       ├── SKEL_L_Clavicle (64729) → L_UpperArm (45509) → L_Forearm (61163)
│       │   └── L_Hand (18905) → 5×Finger + PH_L_Hand (60309) + IK_L_Hand (36029)
│       ├── SKEL_R_Clavicle (10706) → ... (ayna)
│       ├── SKEL_Neck_1 (39317) → SKEL_Head (31086)
│       │   ├── IK_Head, MH_Hair_Scale (50788), MH_Hair_Crown (5749)
│       │   └── FACIAL_facialRoot (65068) → 21 × FB_*
│       └── SPR_L_Breast (64654), SPR_R_Breast (34911)
└── IK_Root (56604)
```

Tam ağaç + tag'ler:
`python scripts/pedrig.py tree mp_m_freemode_01`

---

## 2. REST POSE — rigging'in üç temel kuralı

Ölçüm: `cw_skeleton_dump` ile `mp_m_freemode_01.yft`'ten okundu; Blender'ın
import ettiği armature'ın `matrix_local`'ı ile **birebir doğrulandı**
(Pelvis `w=.7071,y=.7071`, Spine3 `w=.9994,z=.0333`, Head `w=.9928,z=-.1197`).

**Kural 1 — kemiğin uzunluk ekseni LOCAL +X'tir.**
Her uzuv kemiğinin `translation`'ı `[uzunluk, 0, 0]` biçimindedir:

| Kemik | translation | = uzunluk |
|---|---|---|
| `SKEL_L_Calf` | `[0.406518, 0, 0]` | 40.7 cm (uyluk) |
| `SKEL_L_Foot` | `[0.412970, 0, 0]` | 41.3 cm (baldır) |
| `SKEL_L_Forearm` | `[0.274172, 0, 0]` | 27.4 cm (üst kol) |
| `SKEL_L_Hand` | `[0.259194, 0, 0]` | 25.9 cm (önkol) |
| `SKEL_Head` | `[0.113076, 0, 0]` | 11.3 cm (boyun) |

Blender'da kemik uzatmak/kısaltmak = **local X translation**. Y/Z'yi
oynatmak eklemi yerinden çıkarır. Bir kemiği "uzatmak" istiyorsan
child'ın X translation'ını değiştirirsin, scale'i değil.

**Kural 2 — `SKEL_Pelvis` ve `SKEL_Spine_Root` koordinat çevirici, eklem değil.**
İkisi de rest'te ±90° Y döndürülmüştür (Z-up dünya → X-along-bone iskelet).
84 klip ölçümünde ikisinin rest'ten sapması **0.0°**. Bunlara keyframe
koymak tüm hiyerarşiyi 90° yatırır — en sık yapılan rigging hatası.

**Kural 3 — ayna simetrisi Z işaretidir, X/Y aynıdır.**
`SKEL_L_Thigh` = `[0.073508, -0.000226, -0.096118]`,
`SKEL_R_Thigh` = `[0.073508, -0.000226, +0.096118]`.
Rotasyonda ise x,y bileşenleri işaret değiştirir:
L `[-0.0203, 0.0390, -0.0200, 0.9988]` ↔ R `[+0.0203, -0.0390, -0.0200, 0.9988]`.

---

## 3. HANGİ KEMİK KLİPLE, HANGİSİ EXPRESSION'LA SÜRÜLÜR

8 dict / 84 klip ölçümü (`move_m@generic`, `move_f@generic`,
`random@homelandsecurity`, `random@kidnap_girl`, `random@security_van`,
`dead`, `anim@mp_player_intcelebrationmale@dj|bro_love`):

**Klip tarafından keyframe'lenen: 65 kemik.** Kalan 63 kemiğe hiçbir klip
dokunmuyor → onlar expression (`ambient.yed`, `multiplayer.yed`) veya
runtime IK ürünüdür.

**Kanal kullanımı (ölçüm):**

| Kanal | Hangi kemikler | Not |
|---|---|---|
| rotation | 63 kemik | Ped animasyonunun neredeyse tamamı **sadece rotasyon**dur |
| location | `SKEL_ROOT`, `IK_L/R_Hand`, `PH_L/R_Hand`, `IK_L/R_Foot`, `SM_M_*SkirtRoll`, `SKEL_L_Finger22` | Uzuv kemiklerinde translation YOK |
| scale | **hiçbiri** | Gövde klipleri scale yazmaz |

Pratik sonuç: **kendi ped animasyonunu yazarken uzuvlara sadece rotasyon
keyframe'i koy.** Translation koyduğun an mesh ayrılır; oyun bunu
düzeltmez.

### Ölçülen hareket aralıkları (rest'ten maksimum sapma)

Metrik: `2·acos(|dot(q_klip, q_rest)|)` — kemiğin rest'ten en fazla ne kadar
döndüğü. Bir üst-sınır gözlemidir, anatomik limit değil.

| Kemik | maxΔ° | Kemik | maxΔ° |
|---|---|---|---|
| `SKEL_ROOT` | 180.0 | `SKEL_Neck_1` | 82.8 |
| `PH_R_Hand` | 179.2 | `SKEL_L_Toe0` | 79.1 |
| `IK_L_Hand` | 172.4 | `SKEL_R_Foot` | 78.7 |
| `SKEL_L_Forearm` | **154.5** (dirsek) | `SKEL_L_Foot` | 75.0 |
| `SKEL_L_Calf` | **153.9** (diz) | `SKEL_L_Clavicle` | 73.0 |
| `SKEL_R_Calf` | 149.1 | `SKEL_R_Clavicle` | 65.8 |
| `SKEL_R_Forearm` | 147.3 | `SKEL_Head` | **62.0** |
| `SKEL_R_UpperArm` | 144.9 | `SKEL_Spine0` | 43.1 |
| `SKEL_L_Hand` | 142.5 (bilek) | `SKEL_Spine2` | 38.7 |
| `SKEL_L_Thigh` | **129.9** (kalça) | `SKEL_Spine3` | 31.7 |
| `SKEL_L_UpperArm` | 126.8 | `SKEL_Spine1` | 27.8 |
| parmaklar | 38–179 | `IK_Head` | 0.5 |
| — | — | `SKEL_Pelvis` / `SKEL_Spine_Root` | **0.0** |

Okunacak şey: **omurga sert** (her segment 28–43°, toplam ~140° eğilme
4 kemiğe bölünür), **boyun+kafa esnek** (83°+62°), dirsek/diz ~150°.
`SKEL_ROOT` 180° = karakterin dünya yönü (mover), eklem değil.
Parmakların 180'e yaklaşan değerleri kuaterniyon çift-örtü etkisi
içerebilir; parmak için gerçek bükülme ~90–110° bandındadır.

---

## 4. YÜZ SİSTEMİ — asıl zincir

```
facials@<ped>@variations@<mood>.ycd
        │  Track 22 (float)  ve  Track 25 (vector3) kanalları
        │  — bunlar KEMİK DEĞİL, soyut expression girişleridir
        ▼
ambient.yed  →  "facial" expression   (genel ped)
multiplayer.yed → "mp_freemode"       (freemode ped, gövde+yüz birleşik)
p_m_zero.yed → "faceinit"             (Michael, 203 track)
        │  Track 0 (pos) / Track 1 (rot) / Track 2 (scale)
        ▼
FB_* kemikleri  →  mesh deformasyonu
```

**Doğru expression'ı seçmek kritiktir.** `facials@gen_male@*` klipleri
`ambient.yed → facial` için yazılmıştır: 34 kanalın **33'ü** track
tipiyle birebir uyuşur. Aynı klipleri `mp_freemode` ile eşlemeye
çalışmak 34'te 27 uyum verir — 6 kanal (`10274, 15406, 17867, 33683,
40256, 59855`) `mp_freemode`'da Track25, klipte Track22'dir. Yanlış
expression'la eşleme sessizce yanlış yüz üretir.

### Track tablosu (Sollumz `Track` enum'undan doğrulandı)

| Track | Ad | Format | Rol |
|---|---|---|---|
| 0 | BonePosition | Vector3 | kemik konumu |
| 1 | BoneRotation | Quaternion | kemik dönüşü |
| 2 | BoneScale | Vector3 | **kemik ölçeği — "uzama" budur** |
| 5 / 6 | MoverPosition / Rotation | Vec3 / Quat | kök hareketi |
| 22 | *(Float22)* | **Float** | yüz giriş kanalı (skaler) |
| 25 | *(Vector25)* | **Vector3** | yüz giriş kanalı (2–3 bileşenli) |
| 134,137–140 | *(Unk)* | — | klip başına 5 kanal, BoneId 0 (meta/blend) |

### Klip yapısı — mood klipleri `AnimationList`'tir

`facials@gen_male@variations@happy.ycd`:

```
CLIP mood_happy_1  type=AnimationList  dur=8.333  → [hash_52F77E02, hash_E641A4A0]
CLIP mood_happy_2  type=AnimationList  dur=8.333  → aynı iki animasyon
CLIP mood_happy_3  type=AnimationList  dur=8.333  → aynı iki animasyon

ANIM hash_E641A4A0  frames=379  dur=25.2  → 34 kanal (Track22 ×22, Track25 ×12)
ANIM hash_52F77E02  frames=754  dur=25.1  → 5 kanal (Track 134/137/138/139/140)
```

Üç varyant **tek uzun animasyonun dilimleridir** — klipler `StartTime`/
`EndTime` ile keser (`_1` 0–8.33 s, `_3` 8.37–16.7 s, `_2` 16.73–25.07 s).
İki animasyonun **frame rate'i farklıdır**: 379/25.2 ≈ 15 fps (yüz
kanalları), 754/25.1 ≈ 30 fps (meta kanallar). Süreyi frame sayısından
hesaplamaya çalışmak yanlış sonuç verir — `Duration` alanını kullan.

### Yüz kanalı haritası (`ambient.yed → facial`, 35 giriş)

Sürdüğü kemikler statik dataflow ile (yığın simülasyonu, %100 dengeli),
işlev ise 14 mood'un kare kare ölçülmüş genliğinden çıkarıldı.
`R:`=rotation, `P:`=position, `S:`=scale.

| ID | Track | Sürdüğü kemikler | En yüksek mood | İşlev |
|---|---|---|---|---|
| **447** | V25 | `FB_L_Eye` R | stressed 2.00 | **sol göz küresi bakış yönü** |
| **64876** | V25 | `FB_R_Eye` R | (447 ile r=1.00) | **sağ göz küresi bakış yönü** |
| **19205** | F22 | `FB_L_Lid_Upper` P+R, `L_CheekBone` R | her mood'da aktif, normal 1.76 | **sol üst göz kapağı — GÖZ KIRPMA** |
| **25778** | F22 | `FB_R_Lid_Upper` P+R, `R_CheekBone` R | (19205 ile r=0.99) | **sağ üst göz kapağı — göz kırpma** |
| **33683** | F22 | `FB_L_CheekBone` R, `L_Lip_Corner` P+R | happy 1.57, excited 1.57, **aiming 0.00** | **SOL GÜLÜMSEME** (ağız köşesi + elmacık) |
| **40256** | F22 | `FB_R_CheekBone` R, `R_Lip_Corner` P+R | (33683 ile r=1.00) | **SAĞ GÜLÜMSEME** |
| **19497** | V25 | `FB_Brow_Centre` R, `L_Brow_Out` R | injured 1.02, stressed 0.89 | **sol kaş (endişe/acı)** |
| **7689** | V25 | `FB_Brow_Centre` R, `R_Brow_Out` R | — | **sağ kaş** |
| **31528** | V25 | `FB_Brow_Centre` R | happy 1.94 | **kaş ortası kaldırma** |
| **15406** | F22 | `LowerLip`+`LowerLipRoot`+iki `Lip_Bot`/`Lip_Corner` R | **angry 1.02**, frustrated 0.80 | **alt dudak — SOMURTMA/HOMURDANMA** |
| **17867** | F22 | `UpperLip`+`UpperLipRoot`+iki `Lip_Top`/`Lip_Corner` R | **stressed 0.89** | **üst dudak — dudak büzme/istifleme** |
| **59855** | F22 | tüm `Lip_Top`/`Lip_Bot` P+R+S, iki köşe | happy 0.86, talking 0.72, frustrated 0.00 | **AĞIZ AÇMA** (dudak ayrılması) |
| **4187** | V25 | `L_CheekBone` R + sol dudaklar | happy 1.69 | sol ağız/yanak şekli |
| **10760** | V25 | `R_CheekBone` R + sağ dudaklar | (4187 ile r=0.93) | sağ ağız/yanak şekli |
| **10274** | F22 | `FB_Tongue` P+R | **yalnız reactions 0.99** | **dil** |
| **51288** | V25 | `FB_Tongue` R | ~ölü | dil (ikincil) |
| **57296** | V25 | **17 yüz kemiğinin TAMAMI — sadece `S:` (scale)** | — | **GLOBAL YÜZ ÖLÇEĞİ** |
| 840, 1574, 1608, 21981, 34077, 51201 | F22 | `Jaw` dahil tüm ağız (25 çıkış) | **mood'larda 0.00** | **viseme / fonem — konuşma (lipsync)** |
| 18040, 58445, 58471 | F22 | kaş + dudak birleşik | mood'larda 0.00 | kaş+dudak kombosu |
| 4626, 22140, 23631, 28113, 41298, 52693, 60518, 64382 | karışık | ağız şekilleri | değişken | ağız şekil kanalları |

**Bu tablodan çıkan üç önemli sonuç:**

1. **Gülümseme = 33683 + 40256.** İkisi `Lip_Corner` ve `CheekBone`'u
   birlikte sürer; `aiming` mood'unda tam sıfırdır (nişan alırken
   gülümsenmez). "Smile bone" diye tek bir kemik yok — gülümseme *ağız
   köşesi + elmacık kemiği* çiftinin ortak hareketidir.
2. **`57296` tüm yüz kemiklerinin scale'ini sürer** — kullanıcının sorduğu
   "uzama" tam olarak budur. Yüz deformasyonu sadece rotasyon değil,
   **kemik ölçeklemesi** de kullanır (`Lip_Top`, `Lip_Bot`, `Lid_Upper`,
   `CheekBone`, `Brow`, `Jaw`, `Tongue` hepsinde `:Scale` çıkışı var).
3. **Konuşma kanalları mood kanallarından ayrıdır.** 840/1574/1608/21981/
   34077/51201 tüm mood varyasyonlarında sıfırdır; onları lipsync sürer.
   Yani duygu ve konuşma **aynı anda, çakışmadan** oynatılabilir.

### L/R çiftleri (happy klibi üzerinde Pearson korelasyonu)

```
r=1.0000   447   ↔ 64876    (göz küreleri)
r=1.0000   33683 ↔ 40256    (gülümseme)
r=0.9874   19205 ↔ 25778    (göz kapakları)
r=0.9700   19497 ↔ 31528    (kaş)
r=0.9348   4187  ↔ 10760    (ağız/yanak şekli)
```

---

## 5. YÜZ KLİP KATALOĞU

`facials@gen_male@base` — **64 tekil klip**, tüm yüz durumları:

| Grup | Klipler |
|---|---|
| `mood_*` animasyonlu (28) | `normal` `happy` `angry` `injured` `stressed` `excited` `frustrated` `talking` `aiming` `smug` `sulk` `drunk` `sleeping` `skydive` `drivefast` `knockout` `dancing_high/low/medium/trance_*` |
| `pose_*` **tek kare statik** (8) | `pose_normal_1` `pose_happy_1` `pose_angry_1` `pose_smug_1` `pose_sulk_1` `pose_stressed_1` `pose_injured_1` `pose_aiming_1` — hepsi `dur=0.033` |
| `pain_*` (6) | `pain_1..6` |
| tepki | `effort_1..3` `melee_effort_1..3` `shocked_1..2` `electrocuted_1` `burning_1` `coughing_1` |
| eylem | `smoking_inhale/exhale/hold_1` `drinking_1` `eating_1` |
| ölüm | `die_1..2` `dead_1..2` (`dur=0.033`) |

`facials@gen_male@variations@<mood>` — mood başına 3 varyant
(`mood_<x>_1/2/3`). Mevcut mood'lar: `normal happy angry injured stressed
excited frustrated talking aiming reactions dancinghigh dancinglow
dancingmed dancingtrance`.

**Süreler (ölçüm, `Duration` alanından):** happy 8.333 s · angry 2.0 s ·
normal 3.333–8.333 s · stressed 5.333 s · injured 2.2–8.333 s ·
excited/frustrated/talking 6.667 s · aiming 4.0–8.333 s.

**"Sad" adında bir mood YOKTUR.** Üzgün ifade için `mood_sulk_1` /
`pose_sulk_1` (somurtma) veya `mood_injured_1` kullanılır. Kullanıcı "sad"
derse bu ikisini öner; `facials@...@variations@sad` uydurmak sessizce
çalışmayan koda yol açar.

**Ped ailesi başına ayrı dict:** `gen_male`, `gen_female`, `p_m_zero`
(Michael), `p_m_one` (Franklin), `p_m_two` (Trevor), `mime`, `drf`,
`u_m_y_zombie_01`, `creatures@<hayvan>@bark`. Toplam 74 dict.
Michael/Franklin/Trevor'a özel: `elkcall`, `electrocuted`.

### FiveM kullanımı (native adları doğrulandı)

```lua
-- Anlık yüz ifadesi (bir kez oynar)
RequestAnimDict('facials@gen_male@variations@happy')
while not HasAnimDictLoaded('facials@gen_male@variations@happy') do Wait(0) end
PlayFacialAnim(ped, 'mood_happy_1', 'facials@gen_male@variations@happy')

-- KALICI ifade (idle olarak kilitlenir) — RP için doğru olan bu
SetFacialIdleAnimOverride(ped, 'mood_angry_1', 'facials@gen_male@variations@angry')
ClearFacialIdleAnimOverride(ped)

-- Tüm yüz clipset'ini değiştir (ped'in varsayılan yüz ailesi)
_SetFacialClipsetOverride(ped, 'facials@gen_male@variations@stressed')
_ClearFacialClipsetOverride(ped)
```

`PlayFacialAnim` tek seferliktir ve idle geri gelir; kalıcı ifade isteniyorsa
**`SetFacialIdleAnimOverride`** kullanılır. En sık hata: `PlayFacialAnim`
ile kalıcı ifade beklemek.

---

## 6. EXPRESSION (.yed) — yığın tabanlı VM

`.yed` = Expression Dictionary. İçinde her expression için:
`Tracks[]` (G/Ç imzası), `Streams[]` (bytecode), `DefineSpring` (yay),
`LookAt` (bakış kısıtı).

**CodeWalker bu bytecode'u OKUR ama YAZAMAZ.** Bir `.yed`'i CodeWalker ile
kaydedersen `Streams` boşalır ve tüm prosedürel hareket + yüz ölür.
Düzenleme gerekiyorsa `muto` Blender eklentisinin `build_yed` yolu
kullanılır. (Ayrıca: bir `.yed`'i açıp `ExprMap.Count == 0` görmek
"dosya boş" demek DEĞİLDİR — aracın sınırıdır.)

### Instruction seti (4 dosya, 49.795 instruction)

```
Yığına iten (0→1):  Push0 Push1 PushFloat PushVector PushTime PushDeltaTime
                    GetVariable TrackGet TrackGetComp TrackGetOffsetComp
                    TrackGetBoneTransform TrackValid
Yığından alan (1→0): Pop SetVariable TrackSet TrackSetComp TrackSetOffset
                    TrackSetBoneTransform
Tekli (1→1):        VectorNeg VectorNeg3 VectorRcp VectorSaturate
                    VectorRad2Deg VectorDeg2Rad FromEuler ToEuler
İkili (2→1):        VectorAdd Sub Mul Min Max LessThan LessEqual
                    GreaterThan GreaterEqual NotEqual QuatMul VectorTransform
Üçlü (3→1):         ToVector VectorMad VectorClamp VectorLerp QuatSlerp LookAt
Özel:               BlendVector / BlendQuaternion  → operandları YIĞINDAN
                    DEĞİL kendi <Sources> listesinden alır; her Source bir
                    <TrackIndex> taşır ve bu Tracks[] dizisine indekstir.
                    DefineSpring → tüm parametreler instruction içinde.
Kontrol akışı:      Jump JumpIfTrue JumpIfFalse (hedef = KENDİ indeksi + offset)
```

**Doğrulanmış semantik (4 kombinasyon ölçülerek seçildi):**
`JumpIf*` koşulu **pop etmez** — her iki dalın başında ayrı bir `Pop`
vardır. Ölçüm: peek + `i+off` → 184 akışın **179'u yığın-dengeli**;
en yakın alternatif (pop-on-taken + `i+1+off`) → 180 temiz ama toplam
dengesizlik 275'e karşı 105.

**Bilinen sınır — dürüst olmak gerekirse:** 5 akış tam dengelenmiyor:
`default.yed`'in prosedürel düzeltmeleri (`upperbody_fixup`,
`upperbody_shadow`, `independent_mover`, `rootheight_fixup`) ve
`p_m_zero/faceinit`. Bu beşinde `drives`/`channels` çıkışı **yaklaşıktır**.
Bu iş için kritik olanlar tamamen dengeli: `multiplayer.yed` 1/1,
`ambient.yed` **19/19** — yani yukarıdaki yüz kanalı haritası kesindir.
Muhtemel neden: `InstructionOffset`'in bayt tabanlı olması.

### Ped'le ilgili expression envanteri

| Dosya → expression | Track | Spring | Rol |
|---|---|---|---|
| `ambient.yed → facial` | 88 | 0 | **genel ped yüzü** (asıl tüketici) |
| `multiplayer.yed → mp_freemode` | 139 | 2 | freemode ped: gövde + yüz + göğüs yayı |
| `default.yed → male_std` / `female_std` | 22 / 26 | 0 / 2 | gövde roll/muscle helper |
| `default.yed → male_std_facial` | 46 | 0 | eski/standart yüz |
| `default.yed → female_std_facial` | 64 | 0 | dişi yüz |
| `p_m_zero|one|two.yed → faceinit` | 203 | 0 | hikâye karakteri yüz init |
| `ambient.yed → breasts` | 4 | **2** | göğüs yay fiziği |
| `ambient.yed → heels / hiheels / mp_heels` | 12–14 | 0 | topuk → `EO_*Foot` düzeltmesi |
| `ambient.yed → skirt` / `shorts` / `shortslong` | 6–11 | 0 | `SM_*` etek panelleri |
| `ambient.yed → male_body` / `female_body` | 20 / 22 | 0 | gövde şekil |
| `ambient.yed → hairscale` | 6 | 0 | `MH_Hair_Scale` / `MH_Hair_Crown` |
| `ambient.yed → wrinklemaps` / `wrinkletest` | 14 / 119 | 0/2 | kırışık haritası |
| `default.yed → ballistics` | 20 | 2 | zırh/yelek |
| `default.yed → firstpersoncam` | 11 | 0 | FPS kamera düzeltmesi |
| `default.yed → upperbody_fixup` / `_shadow` | 38 / 13 | 0 | üst gövde düzeltme |

**Kıyafet expression'ları:** 234 `.yed` dosyasında toplam ~2000 expression
var ve ezici çoğunluğu **giysi drawable'ına özeldir**:
`uppr_XXX_u` (422), `lowr_XXX_u` (414), `hand_XXX_r` (217), `head_XXX_r`
(207), `hair_XXX` (195), `accs_XXX` (191), `teef_XXX` (126),
`decl_XXX` (103), `task_XXX` (88), `jbib_XXX` (82), `feet_XXX` (71),
`berd_XXX` (29), `clothsim_*` (17).

Yani **her kıyafet parçası kendi kemik düzeltmesini getirir** —
yüksek topuk ayak kemiğini döndürür, kalın mont kolu şişirir. Bir
drawable'ı değiştirince ilgili expression da değişir; kemik pozunun
kıyafete göre farklı görünmesi bug değil, tasarımdır.

---

## 7. TUZAK KATALOĞU — bu iş sırasında bilfiil yaşananlar

1. **Sollumz binary `.ycd`/`.yed` OKUYAMAZ.** Import denenince
   `"Binary resource format '.ycd' is not supported yet"` uyarısı verip
   `Imported in 0.0 seconds` der — **hata fırlatmaz**, sahneye hiçbir şey
   gelmez. Önce `res_to_xml.ps1` ile XML'e çevir.
2. **Sollumz'un otomatik kemik tag formülü vanilla tag'leri ÜRETMEZ.**
   `calc_tag_hash('SKEL_Head')` = 21030, gerçek tag = **31086**. Vanilla
   kemiklerde `use_manual_tag = True` ve tag dosyadan okunur. Hesaplanan
   tag'e asla güvenme; `bone_properties.tag`'i oku.
3. **Bunun sonucu:** Sollumz `.ycd` import'unda kemikleri eşleyemez ve
   kanalları `pose.bones["#31086"]` gibi `#<tag>` adıyla bırakır.
   Analiz yaparken tag→ad eşlemesini kendin kurmalısın.
4. **`.ycd` fcurve değerleri MUTLAK kemik-yerel yönelimdir, rest'e göre
   delta DEĞİL.** Kanıt: `SKEL_Pelvis` tüm klip boyunca sabit
   `w=0.7071, y=0.7071` — yani tam rest değeri. Gerçek eklem açısı için
   `2·acos(|dot(q_klip, q_rest)|)` hesaplanır. Bunu atlarsan Pelvis'i
   "90° dönüyor" sanırsın.
5. **Yanlış expression eşlemesi.** `facials@gen_male@*` klipleri
   `ambient.yed → facial` içindir (33/34 uyum), `mp_freemode` değil
   (27/34). Yanlış eşleme sessizce yanlış yüz üretir.
6. **Yüz kanalı ID'leri kemik tag'i DEĞİLDİR.** 840, 1574, 15406... hiçbir
   ped iskeletinde karşılığı yok. `skeletons.tsv.gz`'de arayınca prop
   kemikleriyle (cam kırığı, tekerlek) rastgele çakışırlar — bu çakışmaya
   kanıp "bu kanal tekerleği sürüyor" demek kolay bir hata.
7. **Kanal adını hash'ten geri çözmeye çalışma.** Bilinen formül vanilla
   tag'leri üretmediği için (bkz. 2) her "eşleşme" anlamsız çakışmadır.
   Ben 144.900 aday deneyip 31 "eşleşme" buldum; kontrol testleri
   başarısız olduğu için hepsini attım. Kanalları **ölçülen mood
   imzasıyla** adlandır.
8. **Mood klipleri `AnimationList`'tir**, tek animasyon değil. `bones=5,34`
   gösterimi "2 animasyon: 5 kanallı + 34 kanallı" demektir.
9. **Aynı `.ycd` içinde iki farklı frame rate olabilir** (15 fps yüz
   kanalı + 30 fps meta). Süreyi `FrameCount / fps` diye hesaplama;
   `Duration` alanını oku.
10. **`SKEL_Pelvis` / `SKEL_Spine_Root`'a keyframe koymak** tüm hiyerarşiyi
    90° yatırır. Ölçümde ikisinin sapması 0.0°.
11. **Uzuv kemiğine translation keyframe'i koymak** mesh'i ayırır. Gövde
    kliplerinde translation yalnız `SKEL_ROOT` + `IK_*` + `PH_*`'te var.
12. **Gövde animasyonuna scale koymak** oyunda beklendiği gibi çalışmaz;
    ölçümde hiçbir gövde klibi scale yazmıyor. Scale yüz expression'ının
    alanıdır.
13. **`PlayFacialAnim` kalıcı DEĞİLDİR.** Kalıcı ifade için
    `SetFacialIdleAnimOverride`.
14. **`sad` mood'u yok** — `sulk` veya `injured` kullan.
15. **CodeWalker ile `.yed` kaydetmek `Streams`'i boşaltır** → yüz ve tüm
    prosedürel hareket ölür.
16. **`ExprMap.Count == 0` görmek dosyanın boş olduğunu göstermez** —
    aracın bytecode'u okuma/yazma sınırıdır.
17. **PowerShell'e `-File` ile virgüllü liste geçmek** tek string olur ve
    sessizce hiçbir şey bulunmaz. Bu iş sırasında bilfiil yaşandı:
    10 dosya istendi, `0 dosya cikarildi` döndü. Çözüm:
    `-Command "& script.ps1 -Names @('a','b')"`.
18. **Asset değiştikten sonra sunucudan çıkıp yeniden bağlan** — FiveM
    stream dosyalarını cache'ler, restart yetmez.
19. **`GetPedBoneIndex(ped, boneId)` TAG alır, indeks değil.** Ad ile
    çalışacaksan `GetEntityBoneIndexByName(ped, 'SKEL_Head')` kullan.
    İkisini karıştırmak -1 döndürür.
20. **Hikâye karakteri ≠ freemode ped.** `player_zero` 354 kemik,
    `mp_m_freemode_01` 128. Michael için yazılmış kemik indeksi freemode
    ped'de başka kemiğe denk gelir; tag ile çalış, indeksle değil.

---

## 8. ÖLÇÜMÜ TEKRARLAMA (araç zinciri)

```bash
P="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/fivem-natives}"

# 1) asset çıkar  — DİZİ İÇİN @() ŞART
powershell -NoProfile -ExecutionPolicy Bypass -Command \
  "& '$P/scripts/extract_asset.ps1' -Names @('mp_m_freemode_01.yft','ambient.yed') -Out <klasör>"
powershell -NoProfile -ExecutionPolicy Bypass -File \
  "$P/scripts/extract_asset.ps1" -Pattern "facials@*" -Out <klasör>

# 2) binary -> XML (Sollumz binary ycd/yed okuyamaz)
powershell -NoProfile -ExecutionPolicy Bypass -File \
  "$P/scripts/res_to_xml.ps1" -Dir <klasör> -Filter "*.ycd" -OutDir <klasör>/xml

# 3) iskelet + rest pose
python $P/scripts/pedrig.py tree   mp_m_freemode_01
python $P/scripts/pedrig.py rest   mp_m_freemode_01 --bone SKEL_L_Calf
python $P/scripts/pedrig.py facial mp_m_freemode_01

# 4) expression çözümle
python $P/scripts/yed_expr.py list     ambient.yed.xml
python $P/scripts/yed_expr.py verify   ambient.yed.xml          # yığın dengesi
python $P/scripts/yed_expr.py io       ambient.yed.xml --expr facial
python $P/scripts/yed_expr.py channels ambient.yed.xml --expr facial --model mp_m_freemode_01
python $P/scripts/yed_expr.py drives   ambient.yed.xml --expr facial --model mp_m_freemode_01
python $P/scripts/yed_expr.py springs  ambient.yed.xml
```

**Blender'da kare kare ölçüm** (bu dokümandaki sayılar böyle üretildi):

1. `.yft`'i Sollumz ile içe al → 128 kemikli armature.
2. `.ycd.xml`'i armature seçili durumda içe al → Blender action.
3. Action eğrilerini `layers → strips → channelbags → fcurves` üzerinden
   oku (Blender 4.4+ katmanlı Action API; `action.fcurves` **yoktur**).
4. Kanal adı `pose.bones["#<tag>"].<prop>` — tag→ad eşlemesini
   `skeletons.tsv.gz`'den kur.
5. Rest kuaterniyonunu armature'dan al
   (`parent.matrix_local.inverted() @ bone.matrix_local`), `.yft` ile
   birebir uyuşur.
6. Eklem açısı = `2·acos(|dot(q_klip, q_rest)|)`.

---

## 9. HIZLI KARAR TABLOSU

| İstek | Doğru yol |
|---|---|
| Kalıcı öfkeli/mutlu yüz | `SetFacialIdleAnimOverride(ped,'mood_angry_1','facials@gen_male@variations@angry')` |
| Tek seferlik acı ifadesi | `PlayFacialAnim(ped,'pain_1','facials@gen_male@base')` |
| Üzgün yüz | `mood_sulk_1` veya `mood_injured_1` (`sad` yok) |
| Donuk tek kare ifade | `pose_*_1` klipleri (`dur=0.033`) |
| Kemik konumu al | `GetPedBoneCoords(ped, <TAG>, 0,0,0)` |
| Ada göre kemik indeksi | `GetEntityBoneIndexByName(ped,'SKEL_Head')` |
| Prop'u ele takmak | `PH_R_Hand` (tag 28422) / `PH_L_Hand` (60309) |
| Kendi ped animasyonu | Sadece **rotasyon** keyframe'i; `Pelvis`/`Spine_Root`'a dokunma; scale yok |
| Kemiği uzatmak | Child'ın **local X translation**'ı (scale değil) |
| Yüz kemiğini elle sürmek | Mümkün değil — expression üzerine yazar. Klip/override kullan |
