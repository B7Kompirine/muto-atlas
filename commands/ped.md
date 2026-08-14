---
description: Ped iskeleti, kemik rest pose, yüz animasyonu ve expression (rigging referansı)
argument-hint: <kemik adı|tag> | tree <ped> | facial <ped> | mood <duygu> | expr <yed>
allowed-tools: Bash(python:*), Bash(powershell.exe:*), Read, Glob, Grep
---

Kullanıcının sorgusu: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

## ÖNCE OKU — bu iş ölçülmüş, tahmin edilmez

İskelet + yüz sistemi (128 kemik, rest pose, 35 yüz kanalı haritası,
20 maddelik tuzak kataloğu):
`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/ped-kemik-yuz-rigging.md`

Tüm oyun ped'lerinde davranış verisi + **sıfırdan animasyon üretimi**
(rig aileleri, iki yüz rig sistemi, prop animasyonları, Sollumz export
tuzakları, `aim`/`ik2` ile poz kurma):
`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/ped-animasyon-davranis-ve-uretim.md`

Retarget + weight painting: `.../ped-retarget-weightpaint.md` (`/retarget`)

## ÜÇ TEMEL GERÇEK — bunlar bilinmeden yazılan kod sessizce yanlış çalışır

1. **Yüz animasyonu `FB_` kemiklerini DOĞRUDAN sürmez.** `facials@*.ycd`
   soyut float kanalları oynatır (Track 22 = float, Track 25 = vector3);
   bu kanalları kemik dönüşüne çeviren şey **`.yed` expression**'dır.
   "Şu klip şu kemiği döndürüyor" varsayımı en büyük hata kaynağıdır.
2. **128 kemiğin sadece 65'i klip tarafından keyframe'lenir.** Kalan 63'ü
   (`MH_ RB_ SM_ EO_ SPR_ FB_`) expression ürünüdür.
3. **Gövde klipleri scale yazmaz, uzuvlara translation da yazmaz.** Ölçek
   (uzama) yalnızca yüz expression'ının işidir.

## SORGU ARAÇLARI

```bash
P="${CLAUDE_PLUGIN_ROOT}"

# --- iskelet / rest pose ---
python "$P/scripts/pedrig.py" peds                        # hangi ped'ler var
python "$P/scripts/pedrig.py" tree   mp_m_freemode_01     # kemik ağacı + tag
python "$P/scripts/pedrig.py" bone   mp_m_freemode_01 SKEL_L_Calf   # ad ya da tag
python "$P/scripts/pedrig.py" groups mp_m_freemode_01     # önek istatistiği + anlamı
python "$P/scripts/pedrig.py" rest   mp_m_freemode_01 --prefix SKEL_
python "$P/scripts/pedrig.py" facial mp_m_freemode_01     # FB_ alt ağacı
python "$P/scripts/pedrig.py" tag    SKEL_Head 46240      # ad <-> tag
python "$P/scripts/pedrig.py" families                    # 158 rig ailesi + kapsama
python "$P/scripts/pedrig.py" compat mp_m_freemode_01     # bu animasyon kaç ped'de oynar
python "$P/scripts/pedrig.py" animals                     # 44 hayvan pedi, klip sırasıyla
python "$P/scripts/pedrig.py" animals a_c_rottweiler      # uzuv zinciri dökümü

# --- eşya/prop animasyonları (klip adı = prop model adı) ---
python "$P/scripts/assetdb.py" propanim <prop adı>

# --- yeni animasyon ürettikten sonra (KLİP SAYISI KAÇ OLURSA OLSUN ŞART) ---
python "$P/scripts/fix_ycd_xml.py" <dosya>.ycd.xml -o <dosya>_fixed.ycd.xml
```

## YÜZ POZLAMA — `blender_facepose.py`

Yüz deformasyonunda kemik kemik değer **tahmin etme**; ölç. Araç bunu yapar:

```python
exec(open(r"${CLAUDE_PLUGIN_ROOT}/scripts/blender_facepose.py").read())
fp = FacePose()        # armature + kafa mesh'i bulur, FB_ son ekini tespit eder
fp.measure()           # Jacobian: local -> dünya (kök kemikler dahil)
fp.topology()          # mesh gerilmeye ne kadar dayanır — ÖNCE BUNU ÇALIŞTIR
fp.apply(stretch=.14, lift=.0075, sep=.0008, jaw=.0034)
fp.report()            # genişlik / dikey açıklık / KIRPILAN (0 olmalı)

# --- yüz animasyonu klipleri ---
python "$P/scripts/assetdb.py" anim facials@gen_male@base --dict
python "$P/scripts/assetdb.py" anim facials --dict-only    # 74 yüz dict'i

# --- expression çözümleme (önce XML'e çevir) ---
powershell -NoProfile -ExecutionPolicy Bypass -File "$P/scripts/res_to_xml.ps1" -Path <dosya.yed>
python "$P/scripts/yed_expr.py" list     ambient.yed.xml
python "$P/scripts/yed_expr.py" verify   ambient.yed.xml   # yığın dengesi denetimi
python "$P/scripts/yed_expr.py" channels ambient.yed.xml --expr facial --model mp_m_freemode_01
python "$P/scripts/yed_expr.py" drives   ambient.yed.xml --expr facial --model mp_m_freemode_01
python "$P/scripts/yed_expr.py" springs  ambient.yed.xml
```

`pedrig.json` yoksa üret:
`powershell -NoProfile -ExecutionPolicy Bypass -File "$P/scripts/build_pedrig.ps1"`

## YÜZ İFADESİ İSTENDİĞİNDE

| İstek | Doğru cevap |
|---|---|
| Kalıcı ifade (RP) | `SetFacialIdleAnimOverride(ped,'mood_angry_1','facials@gen_male@variations@angry')` |
| Tek seferlik | `PlayFacialAnim(ped,'pain_1','facials@gen_male@base')` |
| Donuk tek kare | `pose_happy_1` / `pose_angry_1` / `pose_sulk_1` ... (`dur=0.033`) |
| Tüm yüz ailesi | `_SetFacialClipsetOverride(ped, dict)` |
| Temizle | `ClearFacialIdleAnimOverride(ped)` |

- **`PlayFacialAnim` KALICI DEĞİLDİR** — idle geri gelir. RP'de kalıcı ifade
  isteniyorsa `SetFacialIdleAnimOverride` kullan.
- **`sad` mood'u YOKTUR.** Üzgün için `mood_sulk_1` veya `mood_injured_1`
  öner. `facials@...@variations@sad` uydurmak sessizce çalışmayan kod verir.
- Mood dict'i ped ailesine göre değişir: `gen_male`, `gen_female`,
  `p_m_zero` (Michael), `p_m_one` (Franklin), `p_m_two` (Trevor).
- Süreyi indeksten al, tahmin etme (happy 8.333 s, angry 2.0 s ...).

## KEMİKLE İŞ YAPILDIĞINDA

- `GetPedBoneCoords(ped, boneId, ...)` ve `GetPedBoneIndex(ped, boneId)`
  **TAG alır, indeks değil**. Ad ile çalışacaksan
  `GetEntityBoneIndexByName(ped,'SKEL_Head')`. Karıştırmak `-1` döndürür.
- Prop takma noktası: `PH_R_Hand` (tag 28422) / `PH_L_Hand` (60309).
- Hikâye karakteri ≠ freemode ped (`player_zero` 354 kemik,
  `mp_m_freemode_01` 128). **Tag ile çalış, indeksle değil.**

## KENDİ PED ANİMASYONU / RIGGING YAPILDIĞINDA

- Kemiğin uzunluk ekseni **local +X**'tir. Uzatmak = child'ın X
  translation'ı; **scale değil**.
- `SKEL_Pelvis` ve `SKEL_Spine_Root` rest'te ±90° Y çeviricidir, eklem
  değil. **Keyframe koymak tüm hiyerarşiyi 90° yatırır** (84 klip
  ölçümünde ikisinin sapması 0.0°).
- Uzuvlara **sadece rotasyon** keyframe'i koy. Ölçümde translation yalnız
  `SKEL_ROOT` + `IK_*` + `PH_*`'te var.
- Gövdeye scale koyma — hiçbir vanilla gövde klibi scale yazmıyor.
- Ölçülen aralıklar: dirsek/diz ~150°, kalça ~130°, omuz ~127-145°,
  boyun 83°, kafa 62°, omurga segmenti 28-43° (omurga serttir).

## ARAÇ TUZAKLARI

- **Sollumz binary `.ycd`/`.yed` OKUYAMAZ** — uyarı verip
  `Imported in 0.0 seconds` der, hata fırlatmaz, sahne boş kalır.
  Önce `res_to_xml.ps1`.
- **Sollumz'un otomatik kemik tag formülü vanilla tag'leri üretmez**
  (`SKEL_Head` → hesap 21030, gerçek 31086). Hesaplanana güvenme.
  Sonucu: `.ycd` import'unda kanallar `pose.bones["#31086"]` diye kalır.
- **`.ycd` fcurve değerleri mutlak kemik-yerel yönelimdir**, rest'e göre
  delta değil. Gerçek eklem açısı `2·acos(|dot(q_klip, q_rest)|)`.
- **CodeWalker `.yed` bytecode'unu okur ama YAZAMAZ** — kaydetmek
  `Streams`'i boşaltır, yüz ve tüm prosedürel hareket ölür.
- **PowerShell'e dizi geçerken** `-Command "& script.ps1 -Names @('a','b')"`
  kullan; `-File` ile virgüllü liste tek string olur ve sessizce hiçbir şey
  bulunmaz.
- Asset değişince **sunucudan çıkıp yeniden bağlan** — restart yetmez.

## SONUCU SUNARKEN

- Kemik adı/tag'i **çıktıdan** ver, uydurma. İndekste yoksa yoktur.
- Yüz ifadesi için hem **dict hem clip** adını ver; biri eksikse oynamaz.
- Yüz kemiğini elle döndürmek istenirse: **mümkün değil** — expression
  her karede üzerine yazar. Klip ya da override kullanılır.
