# Var olan efekti kullan / prop'a bağla — `fxName`, `StartParticleFx`, ytyp extension

**Ne zaman okunur:** vanilla efekt arıyorsun (duman, ateş, kıvılcım, toz), bir prop'a partikül bağlayacaksın, "efekt hiç çıkmıyor".
**When to read:** you are looking for an existing vanilla effect (smoke, fire, sparks, dust), attaching a particle to a prop, or "the effect never appears".
**Kaynak:** `trunk/flags.md` §6 · SKILL sorgu satırları (2026-08) · **Ölçüm:** 64.209 ytyp extension, 2.549 efekt / 368 `.ypt`; `ent_` öneki %65,3
**Önce:** `branches/particle/_branch.md` · gövde › `trunk/tool-pitfalls.md` §3 CodeWalker (`FxcFileHash`, `VFT`, `ResourcePointerArray64`)

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" ptfx <prop|efekt>     # ytyp partikül extension'ı, fxType
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" fx <ad> --exact      # efekt .ypt kataloğunda var mı, hangi dosyada
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" ptfx --type 4        # Destroy (3 Break) — 'kırılınca toz'
```

## ytyp partikül extension'ı (`CExtensionDefParticleEffect`)

```xml
<Item type="CExtensionDefParticleEffect">
  <name>prop_pallet_01a</name>
  <offsetPosition x="0" y="0" z="0" />
  <offsetRotation x="0" y="0" z="0" w="1" />
  <fxName>dst_wood_structures</fxName>
  <fxType value="4" />          <!-- Destroy -->
  <boneTag value="-1" />        <!-- -1 = TÜM kemikler -->
  <scale value="1.4" />
  <probability value="100" />
  <flags value="0" />
  <color value="0xFFFFFFFF" />
</Item>
```

### `fxType` enum'u

| Değer | Ad | Not |
|---:|---|---|
| 0 | Ambient | sürekli/ortam; `amb_*` aileleri |
| 1 | Collision | çarpma anında |
| 2 | Shot | vurulunca |
| 3 | Break | kırılınca |
| 4 | Destroy | yok olunca (`dst_*`) |
| 5 | Animation (Unused) | kullanılmıyor |
| 6 | RayFire | *"Valid FX names are defined in the `ENTITYFX_RAYFIRE_PTFX` block"* |
| 7 | In Water | su altında |

### Bayraklar
`Ignore Damaged Model` · `Play on Parent` · `Only on Damaged Model` ·
`Allow Rubber Bullet Shot`

### ⛔ ytyp'teki `fxName` ile `.ypt`'deki efekt adı AYNI DEĞİL

**Ölçüldü** (406 benzersiz `fxName` × 2.549 efekt kataloğu):

| Durum | Adet | Oran |
|---|---:|---:|
| katalogda **aynen** var | 3 | %0,7 |
| **`ent_` öneki** eklenince var | 265 | %65,3 |
| `ent_` öneki **+ sonek** ile var | 9 | %2,2 |
| **hiçbir akrabası yok** | 129 | %31,8 |

Yani ytyp'e `amb_steam_vent_round` yazarsın, `.ypt` içindeki gerçek ad
**`ent_amb_steam_vent_round`**'dur. Bazen sonek de eklenir:
`amb_butterflys` → **`ent_amb_butterflys_swarm`** ·
`amb_moths` → `ent_amb_moths_swarm` / `ent_amb_moths_cupboard` ·
`ray_shipwreck_splash` → `..._s` / `..._l`.

**Toplam çözülebilirlik: %68,2.**

### ⚠ Kalan %31,8 vanilla'nın kendi boşta referansları

**İndeks eksik değil — kanıtlandı:** `core.ypt` CodeWalker ile XML'e açıldı
(45,5 MB) ve `EffectRuleDictionary`'deki **895 efektin 895'i** indekste çıktı,
kaçan **0**. Yani bu adlar oyunun dosyalarında gerçekten yok.

En çarpıcıları: `amb_water_roof_drips_short` **5.621 kullanım** ·
`amb_wind_dust_swirl` 783 · `amb_wind_sand_dune` 547 · `amb_wind_dust` 475 ·
`amb_water_roof_pour_short` 374 · `dst_shop_plastic_cont` 256.

`amb_water_roof_drips` ve `..._thin` var ama `_short` yok — yani bunlar
sürüm geçişlerinde silinmiş/yeniden adlandırılmış efektlere kalan ölü
referanslar. **Bir vanilla ytyp'i kopyalayıp efektini devraldıysan, o efekt
zaten çalışmıyor olabilir.**

Pratik sonuç: bir vanilla prop'un ytyp'ini kopyalayıp efektini devraldıysan,
o efekt zaten çalışmıyor olabilir. **Kopyalamadan önce doğrula:**

```bash
assetdb.py fx <fxName> --exact
```

### Efekt adını nereden bulacaksın (dört yol)

1. **Vanilla ytyp'ten öğren** — CodeWalker RPF Explorer → ilgili ytyp (ör.
   `v_storage.ytyp`) → `Ctrl+F` prop adı → `extensions` altındaki particle
   bloğu. Kırılan paletin efekti `DST_wood_structure`, **FX type 4**,
   **bone tag −1**.
2. **Pleb Masters: Forge** — prop'a tıkla, altta particle effect yazar
   (tam arama 121 sayfa prop).
3. Hazır listeler: Derek Deck'in test edilmiş ambient listesi · Dirty Free'nin
   GTA 5 data dump'ı.
4. ⭐ **`echo effect`** (FiveM helper resource) — efektleri **oyun içinde**
   kaydırıcılarla arayıp önizletir. Resource klasörüne at + `ensure`.
   Aynı işi yapan ikinci araç: `eco_effect`
   (`sources/community-resources.md` §11).

### Blender tarafı — extension'ı kurmak

ytyp → *autocreate from selected* → **Extensions** sekmesi → `+` → type
**Particle** → FX Name / FX Type / bone tag / scale / probability.
Gizmo'yu görmek için viewport'ta `T` → araç çubuğundaki gizmo düğmesi.
**Gizmo yalnız konumu temsil eder, efekti değil.**

- ⛔ **Extension `Shift`+sürükle ile ÇOĞALTILAMAZ** — hiçbir şey olmaz, hata
  da vermez. **`Duplicate Extension`** düğmesini kullan.
- ⚠️ **Gizmo'yu taşıdıktan sonra viewport'a tıklamadan sayılar işlenmez.**
- ⚠️ **`scale = 1` çoğu efekt için çok büyüktür; tipik değer `0.2`.**
  (Yukarıdaki XML örneğindeki `1.4` o prop için ölçülmüş değerdir, varsayılan
  değil.)

**Oyunda görüldüğü doğrulanmış ambient adları** (`amb_` öneki ytyp
extension'ından doğrudan çalışır): `amb_generator_smoke` · `amb_cockroaches` ·
`amb_fly` · `amb_candle_flame` · `amb_sparking_wires` · `amb_moths_nighttime`
(yalnız gece) · `amb_water_drips_med` · `amb_cherry_blossom` ·
`CO_falling_snow` (collision) · `SHT_rubbish` (shot).

**Ölçüm:** Stumpy Mason 38 dk (`leiAB2aM3w8`), `notlar/07` §2, 2026-09 —
yazım hatası tuzağı tek videoda **üç kez** yaşandı (`sparking_wired`,
`cockroaches` yanlış yazımı); efekt hiç çıkmadı, hata da verilmedi.
`assetdb.py fx <ad> --exact` tam bu iş içindir.

### Efekt kataloğu

`data/ptfx_effects.tsv.gz` — **2.549 benzersiz efekt**, 368 `.ypt` içinde
(1.240 dosya tarandı, 0 hata). `core.ypt` tek başına 895 efekt taşıyor.
Üretici: `build_ptfx.ps1`.

### Ölçülmüş tuzaklar
- **Yazım hatası sessizdir.** Yanlış `fxName` hiçbir hata üretmez, efekt
  görünmez. Extension kopyalanınca hata da kopyalanır.
- `boneTag = -1` → tüm kemikler (parça hangi sırayla kopar farketmez).
- `probability` gerçekten olasılıktır (%20 → 5 objeden ~1'i).
- **Rotasyon önemli**: ters kurulan kıvılcım yukarı saçar.
- `veh_` `ped_` `proj_` `wheel_` önekli efektler ytype'tan çalışmaz, script ister.
- Bazıları koşulludur: `_nighttime` yalnız gece, deniz efektleri su altında.

---
