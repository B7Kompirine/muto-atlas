# Shader seçimi — program + render kovası, doku sampler'ları, "dokusu yok"

**Ne zaman okunur:** hangi `.sps`, alfa/cutout neden çalışmıyor, `RenderBucket`, ydr'deki shader adı, PBR haritalarını GTA'ya çevirme, "bu yüzeyin dokusu yok".
**When to read:** choosing the shader program and render bucket; texture samplers; "the texture is there but nothing shows".
**Kaynak:** `kaynaklar/dis-arac.md` §2 shader bölümü (Sollumz 2.9 ölçümü) · `isik.md` 'dokusu yok' · `bake_to_gta.py` docstring (249 shader, 1135 doku) · `kaynaklar/dis-arac.md` §1e · **Ölçüm:** 249 shader tablosu (`shaders.tsv`), 24.000 model kullanım sayımı, 400+ vanilla `.ytd`
**Önce:** `_dal.md` · gövde › `govde/arac-tuzaklari.md` §1-2

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" shader <tür>     # cam/emissive/terrain/kumaş/araç/su/decal/pxm — doku + parametre
```

## Shader seçimi iki eksenlidir: program **ve** render kovası

⛔ **Bir `.sps` seçmek shader'ı seçmez, iki şeyi birden seçer:** GTA shader
**programı** ve **render kovası**. İkisi Sollumz'da ayrı alanlardır ve kova
**yazılabilir** — `.sps` ön ayarının getirdiği kovaya mahkûm değilsiniz.

Ölçüldü (Sollumz 2.9.0):

| `.sps` | program | kova | emissive |
|---|---|---|---|
| `cutout.sps` | `default` | CUTOUT | yok |
| `emissive_alpha.sps` | `emissive` | ALPHA | var |
| `emissive_clip.sps` | `emissive_clip` | **OPAQUE** | var |

**Opak kova alfayı hiç okumaz.** Adında "clip"/"alpha" geçen bir `.sps`
seçmek alfanın çalışacağını garanti etmez: `emissive_clip.sps` ile delikli
bir prop üretildiğinde oyunda **bütün delikler kapandı**, doku saydam
olduğu hâlde katı bir kutu çizildi.

Kova değerleri: `OPAQUE / ALPHA / DECAL / CUTOUT / NO_SPLASH / NO_WATER /
WATER / DISPLACEMENT_ALPHA`. Alfa + emissive birlikte isteniyorsa program
emissive bırakılır, kova elle `CUTOUT`'a çekilir:

```python
m = create_shader("emissive_clip.sps")
m.shader_properties.renderbucket = "CUTOUT"   # ydr'ye RenderBucket 3 yazar
```

⚠️ **ydr'ye yazılan ad `.sps` DOSYA ADI DEĞİL, PROGRAM adıdır.**
`emissive_alpha.sps` ydr'de `emissive` diye görünür. Hash'i
`emissive_alpha` sanıp "yanlış shader yazılmış" demek yanlış teşhistir.
Doğrulama yaparken `JenkHash.GenHash(<program adı>)` ile karşılaştırın.

**İki tarafı da ölçün:** `shader_properties.name` (program),
`shader_properties.renderbucket` (kova). Sonra ydr'den geri okuyup
`Shaders.data_items[i].Name` ve `.RenderBucket` ile doğrulayın.


---

## PBR → GTA: hangi harita nereye (ölçüldü)

GTA PBR değildir: 249 shader'da roughness/gloss/metallic/AO sampler'ı **0**; var olan `SpecSampler` (130). Roughness ters çevrilip **spec**'e, AO **diffuse'un içine**, metallic shader **skalerlerine** gider. Hat: `scripts/bake_to_gta.py`.


## "Bu yüzeyin dokusu yok" ≠ doku eksik

Ölçüldü: JS kapağının dokusu (`my_js_kapi_d`) **vardı ve doğruydu** —
256×256, gerçek bir morg çekmecesi atlası (kapak yüzeyi + kilit/kulp).
Kapının UV'si de doğru bölgeyi örnekliyordu. Kusur **kontrasttaydı**:

| | ortalama | std |
|---|---|---|
| kapı sütunu (önce) | **181** | **5.0** |
| zemin (karşılaştırma) | 55–101 | — |
| kapı sütunu (sonra) | 93 | 13.2 |

Ortalama 181 ve std 5 = zemine göre bembeyaz, dümdüz bir panel. Kullanıcı
bunu **"doku yok"** diye okur. Karartma + kontrast açma yeter; yeni doku
aramaya gerek yok.

⛔ **Sıra önemli: ÖNCE kontrast, SONRA ölçekleme.** Ters sırada ölçekleme
std'yi de böldüğü için kontrast artışı boşa gider — ölçüldü: std 5.0 → 5.8,
yani hiçbir şey değişmedi. Doğru sırada 5.0 → 20.1 (DXT1'den sonra 13.2).

---
