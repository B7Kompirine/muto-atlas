# Kemik tag kataloğu — ad mı sabit, tag mi sabit?

**Gövde dosyası.** Araç / silah / ped kemiklerinde ad mı sabit, tag mi sabit — üç dala birden hizmet eder. Taşındı: `trunk/bone-tags.md` (2026-09-05).

**Ölçüm:** `data/skeletons.tsv.gz` — 478.055 satır, 52.399 model
(41.242 `.yft` + 11.157 `.ydr`), vanilla + tüm DLC.

Bu dosya *"şu kemiğin tag'i kaç"* sorusunu değil, ondan önce gelen soruyu
cevaplar: **motor bu kemiği ADIYLA mı TAG'iyle mi buluyor?** Yanlış tarafa
yatırım yapmak sessiz hata üretir — dosya derlenir, oyun hata vermez, kemik
hiç sürülmez.

---

## 1. ⭐ Karar kuralı — önce bunu uygula

```
Bir kemik adının kaç FARKLI tag taşıdığına ve
bir tag'in kaç FARKLI ad taşıdığına bak:

  1 ad  -> 1 tag , çok modelde       =>  AD SABİTİ    -> adı BİREBİR kopyala
  çok ad -> 1 tag (adlar anlamca farklı) =>  TAG SABİTİ -> adı serbest seç
```

Ölçüm kodu (tekrarlanabilir):

```python
import gzip, collections
f = gzip.open('data/skeletons.tsv.gz','rt',encoding='utf-8')
hdr = f.readline().strip().split('\t')
mi, ni, ti = hdr.index('model'), hdr.index('boneName'), hdr.index('boneTag')
nm = collections.defaultdict(set)          # ad -> model kümesi
nt = collections.defaultdict(collections.Counter)  # ad -> tag sayacı
tn = collections.defaultdict(set)          # tag -> ad kümesi
for line in f:
    r = line.rstrip('\n').split('\t')
    n = r[ni].lower()
    nm[n].add(r[mi]); nt[n][r[ti]] += 1; tn[r[ti]].add(n)
```

Ölçülen sonuç: **26.013 benzersiz tag**. `>=50` modelde geçen adlardan
**559'u tek tag** taşıyor (ad sabiti), **30'u birden fazla** (§6 tuzakları).
Tag sabiti ailesi çok küçüktür ve neredeyse tamamı **saattir** (§5).

⚠ **FiveM script tarafı ile dosya tarafı farklı katmandır.**
`GetEntityBoneIndexByName(veh, "door_dside_f")` **ADI** kullanır;
`.ycd` kanalları, `.yed` çıkışları ve `specialAttribute` sürücüleri **TAG**
kullanır. Bir tarafta çalışan diğerinde çalışmayabilir.

---

## 2. ARAÇ kemikleri — ad sabiti, %100 kararlı

~1.800 araçta ölçüldü, listedeki her adın tag'i **tek** (istisnalar §6).
FiveM'de araç prop takma, hasar, kapı, ışık ve mod işlerinin tamamı buradan.

### 2.1 Gövde / kök

| ad | tag | model |
|---|---:|---:|
| `chassis` | **0** | 1834 |
| `chassis_dummy` | 39433 | 1834 |
| `chassis_lowlod` | 37313 | 1470 |
| `bodyshell` | 60113 | 1816 |
| `stub` | **0** | 731 |

`chassis` ve `stub` tag 0'dır, yani **köktür** — `bodyshell` değil.

### 2.2 Tekerlek / süspansiyon

| ad | tag | | ad | tag |
|---|---:|---|---|---:|
| `wheel_lf` | 27922 | | `wheel_rf` | 26418 |
| `wheel_lr` | 27902 | | `wheel_rr` | 26398 |
| `wheel_lm1` | 29921 | | `wheel_rm1` | 5857 |
| `hub_lf` | 35926 | | `hub_rf` | 36022 |
| `hub_lr` | 35938 | | `hub_rr` | 36034 |
| `suspension_lf` | 5577 | | `suspension_rf` | 6505 |
| `suspension_lr` | 5589 | | `suspension_rr` | 6517 |
| `suspension_lm` | 5584 | | `suspension_rm` | 6512 |
| `wheelmesh_lf` | 20247 | | `wheelmesh_lr` | 20227 |
| `wheelmesh_lf_l1` | 11707 | | `wheelmesh_lr_l1` | 27353 |
| `wheelmesh_lf_l2` | 11708 | | `wheelmesh_lr_l2` | 27354 |
| `wheelmesh_lf_ng` | 12049 | | `wheelmesh_lr_ng` | 27695 |

`_l1`/`_l2` LOD seviyeleri, `_ng` next-gen varyantı.

### 2.3 Kapı / cam / kaput

| ad | tag | | ad | tag |
|---|---:|---|---|---:|
| `door_dside_f` | 60963 | | `door_pside_f` | 35346 |
| `door_dside_r` | 61071 | | `door_pside_r` | 35230 |
| `handle_dside_f` | 49152 | | `handle_pside_f` | 23407 |
| `handle_dside_r` | 49132 | | `handle_pside_r` | 23419 |
| `window_lf` | 26734 | | `window_rf` | 28174 |
| `window_lr` | 26746 | | `window_rr` | 28186 |
| `window_lm` | 26741 | | `window_rm` | 28181 |
| `windscreen` | 39561 | | `windscreen_r` | 56413 |
| `bonnet` | 42990 | | `boot` | 31608 |
| `bumper_f` | 22841 | | `bumper_r` | 22821 |
| `wing_lf` | 4218 | | `wing_rf` | 4186 |

`dside` = sürücü tarafı, `pside` = yolcu tarafı. Cam/tekerlekte ise
`l`/`r` kullanılıyor — **aynı araçta iki farklı adlandırma sistemi var**,
karıştırma.

### 2.4 Işıklar

| ad | tag | | ad | tag |
|---|---:|---|---|---:|
| `headlight_l` | 10804 | | `headlight_r` | 10842 |
| `taillight_l` | 18400 | | `taillight_r` | 18438 |
| `brakelight_l` | 20608 | | `brakelight_r` | 20678 |
| `brakelight_m` | 20609 | | `platelight` | 5558 |
| `indicator_lf` | 41664 | | `indicator_rf` | 40032 |
| `indicator_lr` | 41644 | | `indicator_rr` | 40012 |
| `reversinglight_l` | 34500 | | `reversinglight_r` | 34570 |
| `doorlight_lf` | 11965 | | `doorlight_rf` | 11549 |
| `doorlight_lr` | 11977 | | `doorlight_rr` | 11561 |
| `interiorlight` | 37995 | | `dashglow` | 11869 |
| `extralight_1` | 51309 | | `extralight_2` | 51310 |
| `extralight_3` | 51311 | | | |
| `neon_l` | 49485 | | `neon_r` | 49491 |
| `neon_f` | 49479 | | `neon_b` | 49475 |
| `siren1` | 24999 | | `siren2` | 25000 |
| `siren3` | 25001 | | `siren4` | 25002 |

`siren1..4` ardışıktır (24999+n) — daha yükseği gerekiyorsa deseni sürdür.

### 2.5 Motor / egzoz / şanzıman

| ad | tag | not |
|---|---:|---|
| `engine` | 30510 | |
| `engineblock` | 24668 | |
| `overheat` | 15850 | duman çıkış noktası |
| `overheat_2` | 65271 | |
| `petroltank` | 23306 | · `_l` 50131 · `_r` 50009 |
| `transmission_f` | 17066 | `_m` 17073 · `_r` 17046 |
| `exhaust` | 4944 | |
| `exhaust_2..9` | 50446–50453 | **ardışık** |
| `exhaust_10..16` | 64213–64219 | **ayrı blok**, 9'dan sonra sıçrar |

⚠ Egzoz numaralandırması **9'dan 10'a geçerken bloğu değiştirir**
(50453 → 64213). Formülle üretme, tabloyu kullan.

### 2.6 İç mekân / koltuk

| ad | tag | | ad | tag |
|---|---:|---|---|---:|
| `seat_dside_f` | 20012 | | `seat_pside_f` | 59562 |
| `seat_dside_r` | 20120 | | `seat_pside_r` | 59446 |
| `seat_dside_r1` | 35183 | | `seat_pside_r1` | 33327 |
| `seat_dside_r2` | 35184 | | `seat_f` | 23191 |
| `steeringwheel` | 20285 | | `dials` | 16572 |
| `handlebars` | 49213 | | `hbgrip_l` | 46652 |
| `hbgrip_r` | 46530 | | | |

### 2.7 Mod / extra / misc

| ad | tag |
|---|---:|
| `misc_a` … `misc_z` | 58614 … 58639 (**a'dan z'ye ardışık**) |
| `mod_col_1` … `mod_col_9` | 17880 … 17888 (**ardışık**) |
| `mod_col_10` | **24604** ⚠ desen kırılır |
| `extra_1` … `extra_4` | 8874 … 8877 |
| `extra_11` / `extra_12` | 10843 / 10844 ⚠ ayrı blok |
| `extra_ten` | 41970 ⚠ adı yazıyla |
| `slipstream_l` / `_r` | 33128 / 33134 |
| `weapon_1a`/`1b` | 42814 / 42815 |
| `weapon_2a`/`2b` | 42862 / 42863 |
| `turret_1base` | 65015 |
| `turret_1barrel` | 45666 · `turret_2barrel` 22942 · `turret_3barrel` 52239 |

⚠ **Üç desen kırılması ölçüldü**: `mod_col_10`, `extra_ten` (rakam değil
yazı!), `extra_11/12`. `misc_*` ise a→z kesintisiz. Formüle güvenme.

### 2.8 Uçak / motosiklet / tekne

| ad | tag |
|---|---:|
| `rudder` | 30979 |
| `wing_l` | 33042 |
| `forks_u` / `forks_l` | 25308 / 25427 |
| `swingarm` | 61088 |
| `bikedisc_f` / `_r` | 60125 / 60105 |
| `wheelmeshbk_f` / `_r` | 19998 / 19882 (+ `_l1`,`_l2`,`_ng`) |

---

## 3. SİLAH kemikleri — ad sabiti

| ad | tag | model | rol |
|---|---:|---:|---|
| `gun_root` | **0** | 327 | kök |
| `gun_main_bone` | 3360 | 342 | ana gövde |
| `gun_muzzle` | 17833 | 243 | namlu ağzı — **ptfx/ışık buraya** |
| `gun_gripr` / `gun_gripl` | 18308 / 18302 | 329 / 158 | sağ/sol kavrama |
| `gun_trigger_pr` | 56099 | 217 | tetik (parmak) |
| `gun_trigger` | 23712 | 20 | tetik (mekanik) |
| `gun_cock1` / `gun_cock2` | 39439 / 39440 | 187 / 45 | kurma kolu |
| `gun_vfx_eject` | 28405 | 195 | **kovan atma noktası** |
| `gun_hammer` | 24730 | 67 | horoz |
| `gun_safety` | 53712 | 78 | emniyet |
| `gun_breach` | 24367 | 39 | |
| `gun_ammo` | 18561 | 24 | |
| `gun_sumuzzle` | 19851 | 47 | susturucu ağzı |

**Bileşen (attachment) yuvaları** — `wap*` öneki:

| ad | tag | rol |
|---|---:|---|
| `wapclip` | 1477 | şarjör |
| `wapscop` / `wapscop_2` | 64805 / 3634 | dürbün |
| `wapsupp` / `wapsupp_2` | 4230 / 6180 | susturucu |
| `wapflshlasr` / `_2` | 4396 / 24320 | el feneri / lazer |
| `wapgrip` / `wapgrip_2` | 19397 / 44079 | ön kavrama |

⚠ **`aap*` önekli kemikler tag 0 taşır** (`aapclip` 198 model, `aapbarrel` 27,
`aapcamo` 122) — bunlar bileşen modelinin **kendi kökü**dür, ana silahın
yuvası değil. `wap*` yuvadır, `aap*` takılan parçanın köküdür. Karıştırmak
"parça takılıyor ama yanlış yerde" verir.

---

## 4. PED kemikleri

Ölçümün doğruladığı kritik değerler (1.115 ped modeli):

| ad | tag | | ad | tag |
|---|---:|---|---|---:|
| `SKEL_ROOT` | **0** | | `SKEL_Head` | **31086** |
| `SKEL_Pelvis` | 11816 | | `SKEL_Spine_Root` | 57597 |
| `SKEL_Spine0..3` | 23553 / 24816 / 24817 / **24818** | | `SKEL_Neck_1` | 39317 |
| `SKEL_L_Thigh` | 58271 | | `SKEL_R_Thigh` | 51826 |
| `SKEL_L_Calf` | **63931** | | `SKEL_R_Calf` | **36864** |
| `SKEL_L_Foot` | **14201** | | `SKEL_R_Foot` | **52301** |
| `SKEL_L_UpperArm` | 45509 | | `SKEL_R_UpperArm` | 40269 |
| `SKEL_L_Forearm` | 61163 | | `SKEL_R_Forearm` | 28252 |
| `SKEL_L_Hand` | 18905 | | `SKEL_R_Hand` | 57005 |
| `PH_L_Hand` | 60309 | | `PH_R_Hand` | 28422 |
| `IK_L_Hand` | 36029 | | `IK_R_Hand` | 6286 |
| `FACIAL_facialRoot` | 65068 | | | |

(Calf/Foot değerleri CLAUDE.md §10.5'te bir kez ters yazılmıştı — buradaki
sütunlar 1.107 modelden ölçümdür.)

---

## 5. TAG SABİTİ ailesi — kural burada tersine döner

Tek temiz örnek **saattir**: tag **417 / 418 / 419**, sırasıyla 3 / 10 / 8
**farklı kemik adı** taşır. Ad tamamen serbesttir, tag zorunludur.

Diğer aday (`traffic_light_0/1` ↔ 16665/16666) **ad sabitidir**, tag sabiti
değil — birebir örten eşleme, tek ad tek tag.

Vanilla'da 26.013 tag'in **238'i** ≥4 farklı ad taşıyor; incelendiğinde
çoğu iki zararsız gruptan:

- **hash çakışması** — anlamsız beraberlik (`des_glass94_frag_003` ile
  `ik_l_foot` aynı tag'de)
- **bilerek paylaşılan bağlantı noktası** — arena boru parçaları
  (`prop_arena_pipe_*_start` / `_end`) tag'i paylaşarak birbirine oturur;
  31 farklı ad tek tag'de. Bu bir *snap* sistemidir, motor sürücüsü değil.

⚠ Yani "çok ad → tek tag" **tek başına yetmez**; adların *anlamca* farklı
olması gerekir (Hour vs Min vs MH vs HH). Sayıya değil anlama bak.

---

## 6. ⛔ Tuzaklar — ölçülmüş kararsız adlar

`>=50` modelde geçip **birden fazla tag** taşıyan 30 ad var. Hepsinde bir
tag ezici çoğunlukta, diğeri 1-2 modelde. **Azınlık değer HATALI dosyadır.**

| ad | doğru tag | sapkın tag | sapkını taşıyan |
|---|---:|---:|---|
| `SKEL_Head` | **31086** (1338) | 21030 (1) | `a_c_whalegrey` |
| `SKEL_Pelvis` | **11816** | 56200 (1) | `a_c_whalegrey` |
| `SKEL_Spine_Root` | **57597** | 11569 (1) | `a_c_whalegrey` |
| `PH_R_Hand` | **28422** | 7966 (6) | `rifle_grip_mesh`, `a_c_poodle` |
| `MH_R_Elbow` | **2992** | 62460 (2) | `player_zero`, `p_michael_02` |
| `MH_L_Knee` | **46078** | 30464 (2) | `player_zero`, `p_michael_02` |
| `RB_Neck_1` | **35731** (1203) | 14728 (86) | — dağılım geniş, dikkat |
| `exhaust_3` | **50447** | 4944 (1) | egzoz kökünün tag'i |
| `gun_main_bone` | **3360** (940) | 0 (29) | kök olarak yazılmış |

### ⭐⭐ `a_c_whalegrey` bulgusu — iki notu birleştirir

CLAUDE.md §10 zaten diyor ki: *"`a_c_whalegrey`'e uzanma — `peds.json` /
`PedList.ini`'de girdisi yok ve **0 klibi** var."* Şimdi **sebebi ölçüldü**:

Bu modelin `SKEL_Head` / `SKEL_Pelvis` / `SKEL_Spine_Root` tag'leri kanonik
değil (**21030 / 56200 / 11569**). `.ycd` kanalları tag ile bağlandığı için
hiçbir vanilla ped klibi bu iskelete oturamaz. **"0 klip" bir eksiklik değil,
bu tag sapmasının sonucu.**

⚠ Ve `21030` tam olarak CLAUDE.md §9'un *"Sollumz'un otomatik tag formülü
`SKEL_Head` için 21030 hesaplar, gerçeği 31086"* dediği sayıdır. Yani
**formülle üretilmiş tag taşıyan gerçek bir shipped asset** elimizde var ve
oyunda çalışmıyor. Bu, "tag'i elle gir" kuralının en somut kanıtıdır.

### Diğer sessiz kırıcılar

- **`.ydd` ↔ `.yft` yüz kemiği ad farkı**: `FB_*_000` vs `FB_*_045`,
  21 kemikte. Aynı tag, farklı ad. Blender ada göre bağladığı için yüz hiç
  deforme olmaz ve hata da vermez. (CLAUDE.md §9)
- **`skeletons.tsv.gz` satır saymak kemik saymak değildir** — `.yft`+`.ydd`
  ikizliği ve tekrar var. Doğru alan `boneCount`.
  (`a_c_mtlion_02` → 144 satır, gerçek 72 kemik.)
- **Sollumz `Flags` alanını sıfır bırakır**; sıfır bayraklı kemik hiçbir
  dönüşüm kabul etmez. ⛔ Ama `119` bir sabit değil **izin kümesidir**
  (`Rot*|Trans*`, scale biti YOK). Klip bone **scale** sürüyorsa `1911`
  (kök `6007`) gerekir; yoksa scale kanalı sessizce atılır. Bayrağı
  klipten türet — bkz. `branches/map/destruction.md` §Bağ D. (CLAUDE.md §1.5)

---

## 7. Hangi soruda nereye bakılır

| soru | yer |
|---|---|
| araç kapısı/ışığı/prop takma | §2 — **ad** kullan |
| silah bileşeni, namlu ptfx, kovan | §3 — `wap*` yuva, `aap*` parça kökü |
| ped kemiği | §4 · `assetdb.py bones <ped>` |
| akrep/yelkovan, trafik lambası | §5 |
| bir modelin kendi iskeleti | `assetdb.py bones <model>` |
| bu klip bu modele oturur mu | `assetdb.py clipfit` |
| ytyp/ymap bayrağı | `trunk/flags.md` (§2.1 gerçek dağılım) |
