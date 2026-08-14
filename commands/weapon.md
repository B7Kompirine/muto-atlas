---
description: Add-on silah üretimi — Blender/Sollumz iskelet eşleme + vWeaponsToolkit meta + FiveM kaynak
argument-hint: <silah adı> [referans vanilla silah modeli]
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

Kendi 3D modelini GTA V / FiveM'e **add-on weapon** olarak sokar: iskelet
eşleme, vertex group, shader/doku, meta üretimi, kaynak yapısı, test döngüsü.

## ÖNCE OKU

Tam hat, ölçülmüş kemik tabloları ve 14 maddelik tuzak kataloğu:
`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/addon-silah-uretimi.md`

## ADIM 0 — SORGULAMADAN BAŞLAMA

Referans vanilla silahın iskeleti **okunur**, tahmin edilmez:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" bones <referans_model>
```

Bu çıktı iki şeyi belirler ve ikisi de sonradan değiştirilemez:
- silahın hangi **eklenti yuvalarını** (`WAP*`) alabileceği
- hangi parçaların **animasyonlu** olabileceği (`Gun_Trigger_Pr`, `Gun_Cock1`)

Referans silahta olmayan yuva senin silahına da eklenemez.

⚠️ `skeletons.tsv.gz`'de silah satırları tekrarlıdır (aynı model birden
fazla RPF/DLC kopyasından indekslenmiş). `assetdb.py bones` bunu artık
kendisi ayıklıyor — çıktıda her kemik bir kez görünür. Ama `.tsv.gz`'yi
**kendin okursan** deduplike etmek sana kalır; kopyalar ardışık bloklar
hâlindedir ve 289 modelde gerçekten farklıdırlar (base vs DLC iskeleti),
o yüzden düz satır kümesiyle değil **blok blok** ayır. Kural: indekse
değil **TAG'e** bağlan.

## HAT — sırayla

### 1) Blender / Sollumz
- Vanilla `.ydr` **+ şarjör** (`*_mag1.ydr`) import
- Kendi mesh'ini vanilla'ya hizala → **`Ctrl+A` All Transforms**
- Vanilla vertex group'larını **silmeden önce incele** (hangi kemik neyi sürüyor)
- `V` → Convert to Drawable → unparent → yeniden adlandır → armature'a parent
- Vertex group'lar, **adlar kemik adlarıyla birebir**:
  `Gun_Main_Bone` (kalan mesh) · `Gun_Trigger_Pr` (tetik) · `Gun_Cock1` (sürgü)
  · varsa `Gun_Safety` (emniyet)
- **⛔ Weight painting YOK — rijit atama.** [ölçüm: 2556 vertex'in %100'ü
  tam 1 kemik, toplam tam 255] `Assign` **Weight = 1.000** ile.
  Sıra: hareketli parçaları kendi gruplarına ata → **tüm mesh'i seç → o
  grupları `Deselect` → kalanı `Gun_Main_Bone`'a `Assign`**. Bu adım
  ağırlıksız vertex ve çift atamayı birlikte önler; ikisi de sessiz arızadır.
- Armature modifier → **silahın** armature'ı (mag'inki değil)
- Sollumz **High LOD** mesh adını doğrula

### 2) Şarjör — ayrı drawable
- Tek vertex group: **`AAPClip`** (tag 0)
- ⛔ `WAPClip` (tag 1477) silahtaki **takma noktasıdır**, şarjörün kökü değil.
  Karıştırılırsa şarjör hiç bağlanmaz.

### 3) Shader + doku
- `normal_spec` yaygın · sıra: Base Color=diffuse, "Roughness"=specular, Normal
- Tint/skin kullanılacaksa `normal_spec` **yanlış** tercihtir
- `.ytd`: Set All Materials **Embedded** → export → **Unembedded** → export
  → çıkan doku klasörlerini **folders2ytd**'ye ver

### 4) vWeaponsToolkit — ⛔ **sürüm 1.0.3**
Sonraki build'ler bozuk.

| Sekme | Kritik alanlar |
|---|---|
| Create Add-on Weapon | Template · Weapon Name · **Weapon ID** (oyunda spawn adı) · Weapon Model |
| Configuration | damage / range / ammo type / fire rate / LOD |
| Components | Template + Component Name + Model Name + Clip Size + **Component Enabled ☑** |
| Export | **hepsi yeşil olmalı** |

`Files Found` yeşile dönmüyorsa ad tutmuyordur — **ilerleme**.

### 5) Kaynak — beş `data_file` [ölçüm: oyun konsolundan]
```
WEAPONINFO_FILE             meta/weapons.meta
WEAPON_METADATA_FILE        meta/weaponarchetypes.meta
WEAPON_ANIMATIONS_FILE      meta/weaponanimations.meta
PED_PERSONALITY_FILE        meta/pedpersonality.meta
WEAPONCOMPONENTSINFO_FILE   meta/components/<COMPONENT>/weaponcomponents.meta
```
**Her bileşen kendi klasörünü ve kendi `data_file` satırını ister.**

## TEST

```
restart <KAYNAK_ADI>
str_requestFlush          # istemci konsolu (F8), canary build gerekir
```

- **Silahı önce elinden bırak** — üzerinde duran silah yenilenmez.
- `str_requestFlush` tutmazsa **sunucudan çık ve yeniden bağlan.**
  FiveM stream cache'ler, `restart` tek başına yetmez; bayat asset test etmek
  yanlış teşhis üretir.

## ŞARJÖR KAYMIŞ / ATEŞTE TİTRİYOR

`WAPClip` kemiğinin konumu yanlış demektir (bağlantı değil, konum).

1. Teşhis: Edit Mode'da `WAPClip`'i seç → **Set Origin to Selected** →
   mag'i seç → **Snap to Cursor**. Artık Blender'daki görüntü oyundakiyle aynı.
2. Armature Edit Mode'da kemiği taşı.
3. Pose Mode → o kemik → `Bone Properties` → **tüm Bone Flags'ı sil**
   (⛔ sadece o tek kemikte).
4. `Drawable Tools → Bone Tools → Limit`
5. **Sadece silahı** yeniden export et, test döngüsünü tekrarla.

## BİLİNEN SINIRLAR

- Hat tek bir çalışan örnekten (ooknumber13 tutorial) çıkarıldı; kemik
  tabloları ve tag'ler `skeletons.tsv.gz`'den (868 model) doğrulandı.
- Kendi **silah animasyonu** (reload/ateş) bu hattın dışında —
  `weaponanimations.meta` vanilla klipleri işaret eder.
- **Weapon tint / camo** farklı shader + `AAPCamo` bileşeni ister.
- Yere düşen silahın **fizik davranışı** `.yft` tarafıdır, burada ele alınmadı.
