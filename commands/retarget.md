---
description: Retarget a foreign-rig animation (Sketchfab/Mixamo) onto the GTA ped rig + weight painting
argument-hint: <kaynak dosya/rig> | weights | mover | fps | axis | creature
allowed-tools: Bash(python:*), Bash(powershell.exe:*), Read, Edit, Write, Glob, Grep
---

Kullanıcının isteği: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

## ÖNCE OKU

`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/ped-retarget-weightpaint.md`
— retarget matematiği, kemik eşleme tablosu, mover, doğallık kontrol listesi,
ölçülmüş weight paint kuralları, 25 maddelik tuzak kataloğu.

İskelet/yüz tarafı: `.../ped-kemik-yuz-rigging.md` (komut: `/ped`).

## ARAÇ

```bash
# Blender'da çalıştır (Text Editor > Run Script)
${CLAUDE_PLUGIN_ROOT}/scripts/blender_retarget_gta.py
```

Otomatik yapar: iki rig'i bulur, kemikleri eşler (Mixamo/Rigify/UE/Daz/Biped
adları), rest poz farkını raporlar, `align` ofsetiyle bake eder, root motion'u
mover'a taşır, 30 fps'e zorlar, yasaklı kanalları denetler.

`OFFSET_MODE` = `align` (varsayılan, doğru olan) · `rest` · `pose`.

## ⛔ CUSTOM İSKELET TAMAMEN YASAK

GTA V motoru **yalnızca kendi ped iskeletini** kabul eder. Kaynak modelin
(Sketchfab yaratığı, Mixamo karakteri) kendi armature'ı FiveM'e taşınamaz.
Değiştirilebilen tek şey her kemiğin **konumu ve boyu**; **ad, tag, parent ve
sayı (128)** birebir korunur. İhlal Blender'da hiçbir uyarı üretmez — hata
oyunda ped hiç yüklenmeyerek ortaya çıkar.

İnsan dışı bir yaratığı rig'lemek gerekiyorsa (kuyruk, 6 bacak, pençe):
referansın **§11**'i + `scripts/blender_creature_rig.py`.

### ÖNCE PED SEÇ — insan pedi çoğu yaratık için yanlış

Oyunda 44 hayvan pedi var, her birinin kendi iskeleti **ve animasyon seti**.
Dört ayaklıya `mp_m_freemode_01` giydirmek çalışır ama oyunda **insan
yürüyüşü** oynar.

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/pedrig.py" animals            # klip sirali
python "${CLAUDE_PLUGIN_ROOT}/scripts/pedrig.py" animals a_c_rottweiler
```

- Dört ayaklıların **hepsi** aynı kalıpta (6·6·5·5·5·3); fark **klip sayısı**
  → `a_c_rottweiler` **382 klip** ile açık ara önde (retriever 113, cougar 80).
- Uzun tek zincir (yılan): `a_c_whalegrey` 10 kemik. Uzun kol: `a_c_rhesus` 7.
- Ölçüldü: aynı ağırlıklandırma, insan iskeletinde gerilme %1.19 →
  dört ayaklı iskelette **%0.094**. Kazanç ped seçiminden geliyor.

```python
exec(open(r"${CLAUDE_PLUGIN_ROOT}/scripts/blender_creature_rig.py").read())
cr = CreatureRig("rott_rig", "Yaratik")
cr.snapshot()                                     # ad -> (tag, parent) imzasi
cr.place_chain(["SKEL_Tail_01","SKEL_Tail_02","SKEL_Tail_03",
                "SKEL_Tail_04","SKEL_Tail_05"], kuyruk_noktalari)
cr.move_block("SKEL_Head", kafa_konumu)           # kafa OLCEKLENMEZ, otelenir
cr.park()                                         # kalanlari kisalt (SILME)
cr.skin(bones=UZUVLAR, force={"SKEL_Head": kafa_maskesi})
cr.verify(pose=TEST_POZU)                         # IMZA_AYNI true olmali
```

**Ped −Y'ye bakar** (`SKEL_Head` y=−0.286, `SKEL_Tail_05` y=+0.509). Model
ters bakıyorsa mesh 180° Z çevrilir; atlanırsa tüm doğrulamalar geçer ve ped
oyunda **geri geri yürür**.

**N kemiklik zincir N+1 nokta ister** — eksik verilirse son kemik güdükte
kalır ve 0 vertex sürer (`verify()` bunu `olu_kemik` diye raporlar).

**Merkez hattını `march()` ile çıkar.** Örümcek bacağı ters V'dir; dilimleme
çıkan ve inen kısmı aynı dilimde ortalar, hat ayağa hiç ulaşmaz (ölçüldü).

**Ağırlık eşiğine `> 0.05` yazma** — Blender float32 tutar, float32'deki 0.05
double 0.05'ten büyüktür; Sollumz'un 0.05'lik tüm kemikleri filtreyi geçer
(ölçüldü: 43 yerine 77 kemik). `MIN_LEN=0.06` ya da açık liste.

### Export (`.ydd` + `.yft`) — referansın §12'si

- **Bütçe:** vanilla `a_c_rottweiler_02.ydd` = 11.303 üçgen. Sketchfab modeli
  321.562'ydi. Önce çapı **5 cm altı parçaları at**, sonra decimate.
- **Decimate 4-etki kuralını bozar** (750 vertex 5-8 etki aldı, export
  şikâyet etmedi) → ağırlıkları yeniden oturt.
- **`.yft` sadece iskelet + fizik**; mesh'i geçici yer tutucuyla değiştir
  (1.5 MB → 23.7 KB). Görsel `.ydd`'den gelir.
- **Doku gömülü + DDS ise `.ytd` gerekmez** (Sollumz `.ytd` üretemez).
- **⛔ Ped `.yft`'ini FİZİKSİZ gönder.** Sollumz `ArticulatedBody`'yi hiç
  yazmıyor; fizik gruplu ped **oyunu çökertiyor** (ölçüldü: model uygulandıktan
  4 sn sonra crash, export 0 uyarı vermişti). XML'den `<Physics>` çıkar,
  `scripts/xml_to_res.ps1` ile derle. Ragdoll gider, ped çalışır.
- **Kapsül** (elle fizik yapılacaksa): `sz_bound_shape.capsule_radius/length`
  yaz, **mesh'i kendin üretme**. Silindir kısmı **0 olamaz** →
  `BOUND_CAPSULE_LENGTH_INVALID`.
- **Kemik bağı `COPY_TRANSFORMS` constraint'tir**, isim yetmez
  (`BEFORE_FULL` / `POSE` / `LOCAL`). Collision materyali de şart
  (yaratık = `ANIMAL_DEFAULT`, 171). Kütle kapsül başına verilir.
- Bitince **`res_to_xml.ps1` ile geri oku**: tag'ler, Groups/Children,
  `Archetype/Mass` ≠ 0, `BlendWeights` layout, shader adı.

**Parçalı yaratıkta düz mesafe ağırlığı yırtar.** Ölçüldü (10.021 bileşen):
düz mesafe → kenarların **%5.9**'u 2 katı aşıyor; çapı **0.80 m** altındaki
her bileşeni tek kemiğe katı bağlayıp kalanına Laplacian düzeltme uygulayınca
**%1.2**. Blender'ın `ARMATURE_AUTO`'su bu mesh'te *"Bone Heat Weighting:
failed"* verip tüm vertex'leri ağırlıksız bırakır.

## DÖRT TEMEL GERÇEK — bunlar bilinmeden yapılan retarget sessizce bozuk olur

1. **GTA rest pose'u T-pose DEĞİL, A-pose**: üst kol yataydan **57° aşağı**;
   Mixamo 0°. Kapatılmazsa kollar **144°'ye kadar** sapar.
2. **GTA lokomosyonu yerinde üretilir.** Koşuda ayak anim-uzayı sürüklenmesi
   **0.000 m**, tüm yol (3.656 m / 1.73 s) **mover track**'inde. Mixamo'da yol
   hips'e gömülü → taşınmazsa ped yerinde kayar ya da iki kat hareket eder.
3. **Sollumz rig'inde kemik yönleri anatomik DEĞİL** — hepsi 0.05 m,
   `use_connect=False`, kolda `bone.vector` ile gerçek yön arası **56° fark**.
   Yön için `head → çocuğun head'i` kullan.
4. **Weight paint sert kurallı**: vertex başına **en fazla 4 kemik**, toplam
   **tam 1.0**, ağırlıksız vertex **yok**, ağırlıklar **1/255 adımlı**
   (0.004'ün altı kaybolur).

## RETARGET YÖNTEMİ SEÇİMİ (ölçüldü)

| Yöntem | Ölçülen hata | Karar |
|---|---|---|
| naive dünya eşleme | roll farkı kadar (deneyde **30°**), kollarda **144°** | ❌ |
| düz rest ofseti (delta) | gidiş-dönüş **0.000°** ama T-pose'da kollar 57° biaslı | ⚠ |
| **`align`** | roll temiz **+** mutlak uzuv yönü korunur | ✅ |

## DOĞALLIK — şikâyet gelirse buraya bak

- **Ayak kayması**: stance fazında ayağın *dünya* konumu sabit olmalı
  (anim + mover). Mover işareti yanlışsa kayar.
- **Döngü kapanmıyor**: ilk/son kare pozu aynı olmalı; tam çevrim seç.
- **Lastik gibi**: omurga bandını aşmışsın. Ölçülen maks: `Spine0` 43°,
  `Spine1` 28°, `Spine2` 39°, `Spine3` 32°. Boyun 83°, kafa 62°.
- **Dirsek/diz şişmesi yok, kol büküldüğünde mesh sıkışıyor**: `MH_` / `RB_`
  helper kemikleri mesh'e **skinli ama animasyonla sürülmez** — expression
  sürer. Retarget'ta bu katman yok.
- **Eller donuk**: GTA'da 30 parmak kemiği var ve vanilla klipler kullanıyor
  (38-179° sapma). Mixamo'da genelde parmak yok → elle ver.
- **Basış sahte**: `SKEL_L_Toe0` ölçülen sapma 79°; parmak ucu bükülmesi şart.

## YASAK

- `MH_ RB_ SM_ EO_ SPR_ FB_ FACIAL_` (63 kemik) → keyframe **yazma**,
  expression alanı.
- `SKEL_Pelvis` / `SKEL_Spine_Root` → ±90° çevirici, ölçülen sapma **0.0°**.
  Kalça dönüşü **`SKEL_ROOT`**'a gider.
- Uzuvlara **translation**, herhangi bir yere **scale** yazma.

## EXPORT

Sollumz `.ycd` export **XML üretir** ("Successfully exported" der ama klasörde
`.ycd` yoktur):

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File \
  "${CLAUDE_PLUGIN_ROOT}/scripts/xml_to_ycd.ps1" -XmlPath <...>.ycd.xml -ClipName @('klip_adi')
```

Sonra **sunucudan çıkıp yeniden bağlan** — restart yetmez.

## SONUCU SUNARKEN

- Sayıları dokümandan/ölçümden ver, tahmin etme.
- Aracın doğrulama raporunu (yasaklı kanal, döngü, ayak sürüklenmesi)
  kullanıcıya aktar; temiz değilse "bitti" deme.
- Mover işaret konvansiyonu **kesinleşmedi**: iki işaretle bake edip ayak
  kaymasını ölçüp küçüğünü seçmesi gerektiğini söyle.
