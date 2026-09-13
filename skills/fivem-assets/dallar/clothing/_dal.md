# Kıyafet — dal kuralları

Komut: `/clothing` · Klasör: `dallar/clothing/`
Anahtar kelimeler: kıyafet, giysi, freemode, component, bileşen, .ydd, head_000_r, uppr, lowr, jbib, feet, accs, skintone, _r, _uni, ped prop, şapka, gözlük, p_head, p_eyes, p_ears, propsName, YMT, doku varyantı, renk varyantı, Colour 0, Colour 1, UVMap 1, kan haritası, Mesh Domain, ped ölçekleme, MH_hair_scale, cloth physics, pelerin, etek, duvak, .yld, ped cloth, ayakkabı, topuklu, topuk, boy ayarı, boy artsın, MP_HEELS, CreatureMetadataName, jiggle, spring
**Bu dala ne düşer:** Ped'in **ÜZERİNE giyilen/takılan bileşen** — giysi, saç, şapka/gözlük, ten varyantı, ped boyu/ölçeği. Sınır: ped'in kendi iskeleti ve animasyonu bu dalın dışındadır.

> Yukarıdaki anahtar kelimeler **hızlandırıcıdır, kapsayıcı değildir.** Bir kelime listede yoksa
> yönlendirme durmaz — bu tanıma bakılır. *“kepenk”* listede olmasa da bir kapı nesnesidir.

**What belongs here:** **A component worn or attached ON a ped** — garment, hair, hat/glasses, skin-tone variant, ped height and scale. Boundary: the ped's own skeleton and animation are outside this branch.
**Keywords (EN):** clothing, garment, outfit, freemode, component, .ydd, head_000_r, uppr, lowr, jbib, feet, accs, skintone, _r suffix, _uni, ped prop, hat, glasses, p_head, p_eyes, p_ears, propsName, YMT, texture variant, colour variant, Colour 0, Colour 1, UVMap 1, blood map, Mesh Domain, ped scaling, MH_hair_scale, cloth physics, cape, skirt, veil, .yld, ped cloth, shoes, heels, height offset, MP_HEELS, CreatureMetadataName, jiggle, spring bone


## Bu dalda her yaprakta geçerli olan

⚠️ **Bu dal henüz ölçülmedi.** Kaynağın tamamı topluluk videoları (`notlar/03`); ağırlık kuralları
ve iskelet sayıları bizim ölçümlerimizle tutuyor, geri kalanı `[video]`. Bir üretim yapıldığında
ölçüm buraya yazılır ve `durum` sütunu değişir.

⚠️ **[video] — topluluk anlatımı, bizim ölçümümüz değil.** Sayı verdiği yerde `assetdb.py` ile doğrula; çakışırsa ölçüm kazanır.
  Bu dalın kaynaklarının çoğu topluluk videosudur; **her yaprakta geçerli**.

### Dosya ve iskelet
- **Bileşen dosya adları her ped'de aynıdır** (`head_000_r.ydd`, `uppr_000_u.ydd`) → RPF'ten çıkarırken
  `extract_asset.ps1 -PathFilter '<ped>'` şart; filtresiz onlarca ped aynı dosyaya yazar, sonuncusu kazanır.
- **`.ydd` yüz kemikleri `FB_*_000`, `.yft` `FB_*_045`** — aynı tag, farklı ad (21 kemik); Blender adla bağlar,
  yanlış eşleşirse yüz deforme olmaz, hata da vermez.
- **Freemode 128 kemik, tipik ped 98**; fark `MH_hair_scale` + etek roll'ları (`SM_*SkirtRoll`) + yüz kemikleri.
  Freemode giysisini 98'e taşımak = ağırlık transferi (**Source Layers = By Name**) ya da eksik kemikleri silip
  **Normalize All**.
- **Ağırlık:** vertex başına ≤ 4 kemik (fazlası sessizce kesilir), toplam tam 1.0, 1/255 adımlı.
- **Ped cloth sim mesh'i ≤ 254 vertex** (Sollumz `CLOTH_CHAR_MAX_VERTICES`, vanilla `csb_bride.yld` tam 254). Hareketle dalgalanan kumaş → `ped-cloth.md`; prop env cloth ped hareketini görmez.
- **Ped `.yft` fiziksiz** (Sollumz ped fiziği oyunu çökertir).

### Mesh ve doku

**Doku adlandırma kuralı** (ezberlenir, her yaprakta aynı):

```
<bileşen>_diff_<NNN>_<harf>_<sonek>     jbib_diff_000_a_uni
<bileşen>_normal_<NNN>                  jbib_normal_000
<bileşen>_spec_<NNN>                    jbib_spec_000
```
- `<bileşen>`: `jbib` `uppr` `lowr` `feet` `hand` `teef` `accs` `task` `berd` `hair`
- `<NNN>`: YMT'deki bileşen indeksi
- `<harf>`: doku varyasyonu, **`a`–`z` arası 25 varyasyona kadar**
- `<sonek>`: `uni` (evrensel) ya da ten varyantı (`r`, `lat` …)

- **İki UV map zorunlu:** `UVMap 0` doku, **`UVMap 1` kan haritası** (dokunma).
- **Vertex renkleri:** `Colour 0` = `FF8000` (aydınlatma; yoksa güneşte koyu gölgelenir), `Colour 1` = `000000`
  alfa 0 (rüzgâr + ter; alfa > 0 giysi sallanır/parlar). Emissive parça beyaz vertex rengi + `ped_emissive`.
- ⛔ **Export → Drawable → `Mesh Domain` = `Face Corner`**; `Vertex` yalnız MP freemode **kafaları** için.
- **Freemode:** spec + bump gömülür, **diffuse gömülmez** (oyunda doku değişimi). **Non-streamed ped'de hiç gömülü
  doku olmaz** — export klasöründe `textures/` çıktıysa bir yerde embed kalmış.
- **Bileşen export'unda `Exclude Skeleton` KAPALI, ped prop export'unda AÇIK.**
- **Doku adı Rockstar kuralına uyar:** `<bileşen>_diff_<NNN>_<harf>_<sonek>` · `_normal_<NNN>` · `_spec_<NNN>`;
  prop'ta yalnız harf (`_a`, `_b`). Rastgele ad → ten rengi sessizce kapanır. **Doku kare.**
- **`_r` (skintone):** ten dokusu giysinin `.ytd`'sinde değil (`mp_fm_skin`); ten UV'si **kaydırılmaz**; maske
  specular'ın **alfa** kanalı (beyaz = kumaş).
- **Ped prop `Render Flags` Blender shader'ıyla eşleşir** (`ped_alpha`/`ped_decal`/`ped_cutout`) — MP freemode'da
  önemsiz, diğer tüm ped'lerde fiilen zorunlu. `peds.meta` `propsName` prop'ları aktive eden tek şey.
- LOD: Sollumz **LOD Tools → Generate LODs** (decimation 0.6); prop'lar yalnız HIGH LOD.

## Yapraklar

| istenen | dosya | durum — kaynak |
|---|---|---|
| Freemode kıyafet ekleme / 98'e taşıma / ölçekleme | freemode-kiyafet.md | video — notlar/03 §2, §4-7 |
| Ped prop — şapka, gözlük, kulaklık | ped-prop.md | video — notlar/03 §8-9 · sollumz-discord §4 |
| Doku / renk varyantı / skintone | doku-varyant.md | video — notlar/03 §3-4 |
| Pelerin / etek / duvak — karakterle süzülen kumaş (`.yld`) | ped-cloth.md | Sollumz kaynağı + vanilla csb_bride dökümü (2026-09) |

## Gövdeye bakılacaklar
- `govde/arac-tuzaklari.md` §1 (Mesh Domain, gömülü doku, `hide_select`), §4 (`-PathFilter`, `-LiteralPath`)
- `govde/dogrulama-merdiveni.md` — `.ydd` export boyutu ve gömülü doku kontrolü
- `govde/kemik-tag.md` §4 ped kemikleri
- Kıyafet dokusu renk/detay yordamı ve ped DLC şablonu (`customped.zip`) → `kaynaklar/topluluk-kaynak.md` §9, §12 — **kaynak notu, kural değil.**
