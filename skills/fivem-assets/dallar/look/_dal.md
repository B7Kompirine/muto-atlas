# Görünüm — dal kuralları (shader · doku · ışık · decal · timecycle · parallax · vertex color · emissive)

Komut: `/look` · Klasör: ``
Anahtar kelimeler: shader, .sps, render bucket, kova, emissive, cutout, alfa, doku, texture, .ytd, DDS, DXT, mip, UVMap, Color 1, vertex color, ambient, parallax, pxm, delik, oyuk, kabartma, heightScale, ışık, lamba, sönük, yanmıyor, TimeFlags, Flashiness, flicker, titreyen, koni, gobo, projeksiyon, Tangent, decal, graffiti, leke, kan izi, AddDecal, timecycle, karanlık, loş, ıslak, weathersync, emissive panel, floresan, bake, pişirme, PBR, roughness, trim sheet
**Bu dala ne düşer:** Bir şeyin **GÖRÜNÜMÜ** — shader, doku/DDS, ışık, decal, timecycle, parallax, bake, emissive. Sınır: modelin geometrisi değil, **üzerindeki** kaplama ve ışık.

> Yukarıdaki anahtar kelimeler **hızlandırıcıdır, kapsayıcı değildir.** Bir kelime listede yoksa
> yönlendirme durmaz — bu tanıma bakılır. *“kepenk”* listede olmasa da bir kapı nesnesidir.

**What belongs here:** **How something LOOKS** — shader, texture/DDS, light, decal, timecycle, parallax, bake, emissive. Boundary: not the model's geometry, but the coating and light **on** it.
**Keywords (EN):** shader, material, texture, DDS, .ytd, DXT1, DXT5, mipmap, power of two, normal map, spec, gloss, light, TimeFlags, Flashiness, gobo, projected texture, culling plane, decal, decal.sps, AddDecal, timecycle, weather, parallax, pxm, bake, baking, emissive, vertex colour, render bucket, tint


## Bu dalda her yaprakta geçerli olan

Ölçüm kaynakları: 249 shader / 24.000 model kullanım; 72.539 gömülü ışık; 1.087 timecycle modifier; 16 pxm varyantı / 571
kullanım; morg MLO oyunda; motorun shader kaynağı port edildi.

### Shader ve doku
- ⛔ **Bir `.sps` seçmek iki şeyi seçer: program + render kovası.** Kova ayrı ve **yazılabilir** (`renderbucket`); `emissive_clip.sps`
  OPAQUE kovadadır ve opak kova **alfayı hiç okumaz** (delikler kapandı). Adına değil kovasına bak. ydr'ye yazılan ad `.sps` dosya
  adı değil **program** adıdır (`emissive_alpha.sps` → `emissive`).
- **Varsayılan opak shader `normal_spec.sps`** (diffuse + `_n` + `_s`); tint/skin isteniyorsa yanlış tercih. Şablon `.ydr`'nin ilk
  materyali doğru shader olmayabilir (`w_pi_pistol[0]` = `normal_spec_decal`) — materyali sıfırdan kur. `make_dds.py` DXT5+mip,
  `dds_to_ytd.ps1` sözlük; malzeme haritaları için `bake_to_gta.py` (alfa dayatmaz).
- **GTA PBR değildir:** roughness/metallic/AO sampler'ı **yok** (249 shader); roughness ters çevrilip **spec**'e, AO **diffuse'un içine**,
  metallic shader **skalerlerine**. Spec map'i olmayan materyal mat değildir (sabit 0.1). Detail map iki iş yapar.
- **Doku DXT + mip zinciri** (normal/spec DXT1 %92-99; diffuse alfa yoksa DXT1; mip `log2(kısa kenar)−1`, 4×4'te biter); PNG gömülemez;
  **iki nin kuvveti**; kare değilse UV gerer. Normal/spec haritaları **Non-Color**. `dds_dxt1` alfa taşımaz — delikli doku için
  `dds_rgba`/DXT5.
- ⛔ **Sollumz gömülü dokuyu DİSKTEKİ DDS'ten paketler**; Blender içi piksel düzenleme `.ydr`'ye 16×16 taslak gömdü, hata vermedi.
  Gömülü doku adı **dosya adından**. Aynı doku adı farklı sözlükte farklı içerik (175 kopyadan 22'si) → boyuta göre seç.
- `UVMap 0` + `Color 1` şart; `.color` gamma çözer → `.color_srgb`. Materyal Sollumz shader'ı olmalı; düz renk kabul edilmez → palet atlası.
- **Dokular modelde değil** (harita) — dış sözlük + `gtxd.meta`; "bu yüzeyin dokusu yok" ≠ doku eksik (`shader.md`).
- **Prop için `AddReplaceTexture` global** — objeye özel içerik için yanlış yol.

### Işık
- **Işık kemiğe bağlıdır**, `Position/Direction/Tangent` kemik uzayında; `prop_worklight_01a`'da kemik 1.737 m yukarıda.
- **`TimeFlags` saat kümesidir** (`14680095` = 21:00–05:00; 24/24 = `16777215`; 0 = hiç yanmaz). "Yanmıyor"da **ilk bakılacak yer saat**.
- **`Flashiness` isimli enum** (Sollumz `enum_items`): 0 CONSTANT · 9 ALARM · 15 CANDLE · 17 FIRE · 19 ELECTRIC · 20 STROBE; tahmin edilen
  üç değer de yanlıştı. "Flicker çalışmıyor" → önce `Intensity`. Tek Flashiness sahte; kırpışma tip çeşitliliğiyle dağıtılır.
- **Gobo:** `Tangent` = projeksiyonun **yukarı** ekseni (Sollumz yerel X yazar, −90° roll); doku aynı adlı `.ytd`'de gider ve arketip
  `textureDictionary`'yi referans etmeli; renk dokudaysa **ışık beyaz** (motor çarpar, çift renk mora döner); `static_shadows` kendi
  siluetini basar; en-boy oranı korunur, kare dokuya vinyet.
- **Blender'dan export üç bağ:** gizli ışık düşmez konumu bozulur · `intensity` `energy` proxy'si · kemiğe bağlı konum kemik uzayında.
  Mesh transformu sıfırlanırken ışığın transformu silinmesin. Koni açıları **radyan**. **Ölçüt hesap değil, geri okumadır.**
- **Dört formül Blender'dan yapısal farklı:** düşüş `a/((1-b)a+b)` kare mesafede (`pow` %17,3 sapar) · koni kosinüste lineer ·
  ambient `downMult` (hemisphere lerp değil) · Hable filmic (beyaz 11.2). Gölge bias'ı texel biriminde.
- Vanilla dekoratif fenerde gömülü ışık **yoktur**; prop'a ışık koymak bilinçli sapma.

### Timecycle ve vertex color
- **Karanlık üç katman:** hava cycle'ı (13 keyframe, `levels/gta5/time.xml`; `name` yalan söyler, `hour` doğru) → oda modifier'ı
  (param bazlı harman; paylaşılana dokunma, kendi modifier'ını `TIMECYCLEMOD_FILE` ile kaydet) → prop ışığı.
- **Directional light geometriyle engellenmez** — oda `flags |= 4|8` (No Directional / No Exterior); "vanilla ile diff" bunu yakalamaz,
  ölçüt aynı işi yapan başka vanilla MLO (vault/facility 111).
- **"Harita ıslak"ın iki ayrı yolu var**; `SetRainLevel` ıslaklığı kaldırmaz; qb-weathersync ile yarış kazanılmaz, döngüsü durdurulur.
- **Vertex color karartması yalnız `RenderBucket == 0`**; opak olmayan kovada RGB çarpandır, R'yi düşürmek hue kaydırır. `R == G > 200`
  ⇒ boyanmamış (yalnız opak). R yön kararı, G sanatsal değer — G'yi tek sayıya çakma. Kabuk prop bayrağı almamalı.

### Decal ve parallax
- **Decal üç sistemdir:** `AddDecal` (script, 194 tip, doku **gri maske** — rengi `rCoef/gCoef/bCoef` verir) · `decal.sps` + bucket 2
  (haritaya gömülü) · Blender projeksiyon (eklenti depoda yok). Işın ızgarası paralel yüzeye vuramaz; kutu köşede yeniden başlar; ince boru/ızgara
  boyama işi. `bisect_plane` yüz siler → Sutherland–Hodgman.
- **Parallax içerik uydurmaz** (diffuse'a boyalı), animasyon değildir, silüet kırmaz; `normal_spec_pxm` 218 kullanım varsayılan,
  `globalAnimUV` yok; delik için `heightBias` negatif; vanilla iç mekânda parallax **yok**.

### Epistemik (bedeli ödendi)
- **Ekran görüntüsü ölçüm değildir** (0.617 gri "patlamış" sanıldı). **Bir aracın sabiti kendi ölçeğine ayarlıdır.** Toplam bir topluluk
  ölçümüdür, tek üye hakkında konuşamaz. Yeni ölçüm eski çıkarımı yalanladıysa çıkarım ölür.

## Yapraklar

| istenen | dosya | durum — kaynak |
|---|---|---|
| Shader seçimi — program + kova, PBR→GTA, "dokusu yok" | shader.md | ölçüldü — sollumz-discord shader · isik-mat · bake_to_gta |
| Parallax — delik, oyuk, kabartma, 4 katmanlı zemin | parallax.md | ölçüldü — parallax-pxm |
| Işık — oku/düzenle/geri yaz, TimeFlags, Flashiness, gobo | isik.md | ölçüldü — isik-mat · decal-isik §4,9 · HATALAR |
| Işık matematiği ve Blender önizleme | isik-matematigi.md | ölçüldü — isik-mat §1-8 |
| Timecycle — karanlık, ıslak, oda bayrağı | timecycle.md | ölçüldü — isik-mat · decal-isik §5 · morg |
| Vertex color — iç mekân ambient, bucket kuralı | vertex-color.md | ölçüldü — isik-mat vertex color |
| Emissive panel | emissive.md | ölçüldü — decal-isik §6 |
| Decal — üç sistem + kaynak paketleri | decal.md | ölçüldü — decal-isik · ytyp-ymap §8.5b-8.6 · decal-kaynak |

## Gövdeye bakılacaklar
- `govde/arac-tuzaklari.md` §1 (gömülü doku DDS, `use_custom_settings`, koni radyan, ışık export), §2 (`.color_srgb`, bisect, `bound_box`),
- `govde/dogrulama-merdiveni.md` — ışık/doku/decal'i oyuna sokmadan: `.ydr` ışık geri okuma, `.ytd` boyut/format
  §3 (`.ytd` şeması, `GetXMLFormat`, RPF anahtar)
- `govde/bayraklar.md` (Time arketipi, Cast Shadows, Dont Render In Reflections) ·
  iç mekân bütçesi `dallar/map/vanilla-ic-mekan.md`
- Hazır şablon / araç arıyorsan (Substance GTA baker, timecycle birleşimi, lightshaft `flags 99`, vertex color master, R\* iç mekân renk şeması) → `kaynaklar/topluluk-kaynak.md` §1-3, §9 — **kaynak notu, kural değil.**
