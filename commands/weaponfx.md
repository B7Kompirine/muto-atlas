---
description: Weapon visuals - glow (emissive), wireframe, charms, and UV-animated skins
argument-hint: <glow|wireframe|zincir|charm|uvanim> [silah modeli]
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

Çalışan bir add-on silahın **üstüne** görsel katman ekler. Temel hat bu
değil — silahın kendisi için `/weapon`.

## ÖNCE OKU

`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/silah-gorsel-ve-uv-animasyon.md`

Temel silah hattı (iskelet, vertex group, meta, test):
`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/addon-silah-uretimi.md`

## ZORLUK SIRASI — hangisi ne gerektiriyor

| Teknik | Oyun tarafı |
|---|---|
| zincir / charm | **yok** — sadece mesh, `Ctrl+J` ile silaha kaynar |
| wireframe | yok — modifier + shader |
| glow | shader + `.ytd`'ye doku ekleme |
| **uvanim** | **`.ycd` + `.ytyp` + `.ymap` + ayrı bileşen** |

İlk üçü `.ydr` içinde kalır. `uvanim` ayrı model + dört dosya demektir.

## GLOW — kısa hat

Shader **`normal_spec_emissive`**. Value Parameters (doğrulanmış):
`bumpiness 0.40 · specularFalloffMult 250.00 · specularFresnel 0.96 ·
emissiveMultiplier 1.10 · specMapIntMask 1/0/0 · HardAlphaBlend 1.00`.
Ana doku = parlamanın rengi; normal + spec **Embedded**.

⛔ İki sessiz tuzak — bunlar yüzünden çalışan kurulum bozuk sanılıyor:
- **Ana glow dokusu `.ytd`'ye eklenmezse bölge beyaz kalır.**
- **OpenIV'de parlamaz, gündüz parlamaz** → oyun içinde **gece** test et.

## WIREFRAME

Mesh'i çoğalt, kopyaya **Wireframe modifier**:
`Thickness 0.001 · Offset 0 · Replace Original ☑`. Export öncesi apply et.

## ZİNCİR / CHARM

Saf modelleme. Zincir: Archimedean spiral + torus halka + **Array** +
**Curve** modifier → apply → spiral sil → `Ctrl+J`.
Charm: Sollumz shader'ı **şart** (Principled BSDF çalışmaz),
`V → Convert to Drawable`, **Rotation X = 90**, sonra `Ctrl+J`.
Birleştikten sonra tek drawable'dır — bileşen/meta gerektirmez.

## UV ANİMASYONLU SKIN — kritik dört nokta

1. Skin **ayrı model, ayrı ad**: `<silah>_skin_01`.
2. ⛔ **`Target ID` = MATERYAL**, armature değil (ped alışkanlığı en sık
   hata). UV keyframe: kare 0 → `0,0`, 30 → `0.5,0.5`, 60 → `0,0`.
3. ⛔ Klip **`Name` = `<hash>.clip`** — `.clip` eki yoksa animasyon
   sessizce hiç oynamaz. `Duration = kare / 30`. Sözlük adı `clip@<ad>`.
4. ⛔ Archetype `Flags = 525312` = **1024 (UV anims)** + **524288
   (Auto Start Anim)**. `Has Anim (YCD)` **başka bir bayraktır**, onu
   işaretleme.

Bileşen tarafı: `COMPONENT_..._SKIN01`, `<AttachBone>` **`AAP*`**
(ölçüm: 318/318 vanilla girdi `AAP*`, `WAP*` sıfır).

**İlk kontrol noktası CodeWalker**: skin orada animasyonlu görünmüyorsa
oyunda da görünmez — oyuna kadar gitme.

## BİLİNEN SINIRLAR

- UV animasyonu **yalnız dokuyu kaydırır**, geometriyi oynatmaz. Parça
  hareketi `Gun_Cock1` / `Gun_Trigger_Pr` kemikleriyle olur.
- `.ymap` gerekliliği ve LOD 99999 **doğrulanmadı** — kaynak üretici de
  emin değil. Referansta `[video?]` ile işaretli; kendi testinde çıkarıp
  dene.
- **Weapon tint / camo** (oyunun kendi renk sistemi) kapsam dışı;
  `AAPCamo` bileşeni + tint destekli shader ister.
