# Parallax (`*_pxm`) — düz yüzeyde delik, oyuk, kabartma, 4 katmanlı zemin

**Ne zaman okunur:** duvarda delik/hasar, kırık sıva, kabartma, büyük zeminde derinlik; "parallax animasyon yapmıyor", "zeminde sırıtıyor".
**When to read:** a hole, recess or relief on a flat surface (`*_pxm`); layered parallax; when parallax breaks on curved geometry.
**Kaynak:** `parallax.md` (tamamı) + eski SKILL/`/look` özeti (2026-08) · **Ölçüm:** 16 varyant / 571 vanilla kullanım; satılık MLO yaması alan alan; oyunda kalibrasyon tahtası
**Önce:** `_dal.md` · gövde › `govde/arac-tuzaklari.md` §1-2

---

## PARALLAX — düz yüzeyde derinlik (`/look`)



Parallax, yükseklik haritasına göre **diffuse'un UV'sini bakış açısına göre
kaydırır**. Başka hiçbir şey yapmaz.

- ⛔ **İçerik uydurmaz** — deliğin içi diffuse'a **boyalı** olmalı.
  Ölçüt: **parallax kapalıyken doku tek başına delik gibi görünmeli.**
  Görünmüyorsa parallax onu delik değil, **kayan çıkartma** yapar.
- ⛔ **Animasyon değildir** — kendi kendine hareket etmez, yalnız kamera
  açısıyla değişir. "Animasyon yok" şikâyeti **beklenen davranıştır**.
- ⛔ **Silüeti kırmaz, collision sürmez.** Zeminde anında sırıtır, duvarda değil.

Shader seçimi veriden (`assetdb.py shader pxm`): **`normal_spec_pxm` 218
kullanım = varsayılan**; `normal_pxm` yalnız 3 kullanım, refleksle seçme;
alfa şartsa `normal_spec_decal_pxm` (bucket 2, gölge vermez); büyük zemin
**`terrain_cb_w_4lyr_pxm`** (12 doku, yakın terrain'de vanilla oranı %84,
LOD sürümünde parallax **yok**).

Delik/oyuk için `heightBias` **negatif**. Duvarda `heightScale` 0.03–0.05;
zeminde vanilla bandında (≈0.03) kal — zemin sürekli sıyırma açısıyla görülür,
parallax'ın en kötü durumu.

**Teşhis:** dik bakışta düz + eğik bakışta derin → parallax. Gerçek çukurun
derinliği **dik bakışta** en çok görünür, parallax'ta tam tersi.

**UV animasyonu ile birlikte kullanılabilir** (oyunda ölçüldü) — ama
⛔ **`normal_spec_pxm`'de `globalAnimUV` YOKTUR**, animasyon isteyen
`normal_pxm`'e geçmeli. Ve ⛔ **hareket bölgeye özel olamaz**: matris
materyalin tüm UV uzayına uygulanır, tek dokudaki üç top aynı hareketi yapar.
Bağımsız hareket için çok materyal, sprite sheet ya da katmanlı düzlem.

⛔ **Vanilla iç mekânda parallax YOKTUR** (v_coroner ve v_abattoir'da tek bir
`*_pxm` yok). Bu modern modder tekniğidir; R\* derinliği geometri + doku +
vertex color + ışıktan alır. → `dallar/map/vanilla-ic-mekan.md`

---



---


Düz bir yüzeyin delik/oyuk/kabartma gibi görünmesi. Ölçüm kaynakları:
`muto-atlas` shader tablosu (249 shader, vanilla kullanım sayıları), Sollumz
`szio/gta5/Shaders.xml`, bir satılık MLO'nun alan alan okunan materyali ve
**oyun içinde çalıştırılan kendi test tahtamız** (2026-08-23).

---

## 0. MEKANİZMA — üç cümle

Parallax, yükseklik haritasına bakarak **diffuse'un UV'sini bakış açısına göre
kaydırır**. Başka hiçbir şey yapmaz.

- ⛔ **İçerik uydurmaz.** Deliğin içi (tuğla, tahta, karanlık, moloz)
  **diffuse'a boyalı olmak zorundadır.** Boyalı değilse kaydıracak bir şey yok.
- ⛔ **Animasyon DEĞİLDİR.** Kendi kendine hareket etmez; yalnız **kamera
  açısı** değişince değişir. Yerinde duran oyuncu hiçbir şey görmez.
  *(ölçüldü: oyun içi, 2026-08-23)*
- ⛔ **Silüeti kırmaz, collision'ı sürmez.** "Çukurun" kenarı düz kalır ve
  oyuncu düz düzlemde yürür. Duvarda kimse fark etmez, **zeminde sırıtır**.

---

## 1. TEŞHİS — geometri mi, parallax mı, düz doku mu

Aynı yeri **dik** ve **eğik** açıdan karşılaştır:

| dik bakış | eğik bakış | teşhis |
|---|---|---|
| düz | düz | **düz boyalı doku** |
| düz | derin | **parallax** |
| derin | derin (kapanır) | **gerçek geometri** |

Gerçek çukurun derinliği **dik bakışta en çok** görünür. Parallax'ta **tam
tersi**: bakış ışını yükseklik eksenine paralelken UV kayması ≈ 0.

*(ölçüldü iki kez: bir satılık MLO'nun tanıtım videosunda t=0.4 vs t=2.8;
ve kendi tahtamızda kontrol paneli vs `heightScale 0.12` paneli.)*

---

## 2. SHADER SEÇİMİ — vanilla kullanımına göre

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" shader normal_spec_pxm --exact
```

| shader | vanilla | bucket | doku | ne zaman |
|---|---|---|---|---|
| **`normal_spec_pxm`** | **218** | 0 opak | Diffuse+height+Bump+Spec | **varsayılan seçim** |
| `normal_pxm` | 3 | 0 opak | Diffuse+height+Bump | spec gerekmiyorsa |
| `normal_spec_decal_pxm` | 196 | 2 decal | +alfa | alfa şartsa — **gölge vermez** |
| `normal_decal_pxm` | 13 | 2 decal | | " |
| **`terrain_cb_w_4lyr_pxm`** | **74** | 0 opak | **12 doku** | **büyük zemin** |

Oyun genelinde toplam `*_pxm` kullanımı: **571**.

⛔ **`normal_pxm`'i refleksle seçme.** Vanilla'da sadece 3 kullanımı var;
`normal_spec_pxm` aynı işi yapar, 218 kullanımı vardır ve spec kanalı da
gelir. Yeni asset için varsayılan bu olmalı.

⛔ **Opak shader'da alfa YOKTUR.** Deliğin şekli **mesh siluetiyle** verilir:
yama hasarın konturuna kesilir, dikdörtgen quad kullanılmaz.
*(ölçülen örnek: 3 bileşen, 263 vertex / 179 yüz / 430 üçgen, V−E+F = 3 →
üçü de disk topolojisi, yani açık yüzey.)*

---

## 3. PARAMETRELER — ölçülmüş bantlar

### Vanilla varsayılanı (`normal_spec_pxm`)

```
HardAlphaBlend 1 · useTessellation 0 · wetnessMultiplier 1
parallaxSelfShadowAmount 0.95 · heightBias 0.015 · heightScale 0.03
bumpiness 1 · specMapIntMask (1,0,0) · specularIntensityMult 1
specularFalloffMult 35 · specularFresnel 0.75
```

### Bir satılık MLO'nun duvar hasarı yaması (alan alan okundu)

| param | değeri | vanilla | etkisi |
|---|---|---|---|
| `heightScale` | 0.040 | 0.03 | kayma miktarı = görünen derinlik |
| `heightBias` | **−0.200** | +0.015 | **negatif = yüzeyi içeri it** |
| `parallaxSelfShadowAmount` | 1.000 | 0.95 | kovuğun kendi gölgesi |
| `bumpiness` | 0.000 | 1 | 0 = kabartma **sadece** parallax'tan |
| `specularFalloffMult` | 1.000 | 35–100 | 1 = kovuk içi tamamen mat |

**Kural:** delik/oyuk isteniyorsa `heightBias` **negatif**; çıkıntı isteniyorsa
pozitif. Duvarda `heightScale` 0.03–0.05 bandı; **zeminde vanilla bandında
(≈0.03) kal**.

---

## 4. BÜYÜK ZEMİN — ayrı bir shader ailesi var

**R\* yakın mesafe terrain'de parallax'ı varsayılan olarak seçiyor** (ölçüldü):

| | kullanım |
|---|---|
| parallax'lı `terrain_cb_w_4lyr_*` varyantları | **135** |
| parallax'sız | 25 |
| **LOD varyantları — parallax YOK** | 72 |

→ yakın zeminde **%84 parallax**, LOD sürümünde **bilinçli olarak atılmış**.

`terrain_cb_w_4lyr_pxm`: bayrak `IS_TERRAIN`, bucket 0, **12 doku** (4 katmanın
her biri için `TextureSampler_layerN` + `BumpSampler_layerN` +
`heightMapSamplerLayerN`), katman başına ayrı `heightScale0..3 = 0.03` ve
`heightBias0..3 = 0.015`.

Kurulum sırası:
1. Zemini **loop cut'larla böl** — blend maskesini boyayacak vertex yoğunluğu
   gerekir (`Colour1`: layer0 siyah, layer1 mavi, layer2 yeşil).
2. 4 katman × (diffuse + bump + height) = 12 doku.
3. `heightScale ≈ 0.03`, `heightBias ≈ 0.015` — duvardaki gibi agresif değer verme.
4. **LOD sürümünde parallax'sız varyanta düş** (`terrain_cb_w_4lyr_lod`).

---

## 5. BOYUT VE KAVİS

- **Dünya ölçeğinde sınır yoktur.** `heightScale` **teğet/UV uzayı** ölçüsüdür;
  2 m'lik yamada da 200 m'lik zeminde de aynı çalışır, tile'lanabilir.
  *(çıkarım — shader matematiğinden; oyun içinde ölçülmedi)*
- **Gerçek sınırlar üçtür:** ① bakış açısı ② silüet kırılmaz ③ collision sürmez.
- **Zemin en kötü durumdur** çünkü sürekli sıyırma açısıyla görülür; duvar en
  iyisi.
- **Kavis:** teğet uzayında çalıştığı için **yumuşak kavis sorunsuzdur** —
  kanıtı terrain'in kendisi (kavislidir, 74 kullanım). Kırıldığı yerler:
  - kavis yarıçapı yer değiştirme derinliğine yaklaşınca (boru, kolon, ince silindir)
  - UV dikişi
  - ⛔ **aynalanmış UV** — teğet işareti döner, kayma dikişin bir yanında
    **ters yöne** gider
  - az segment (fasetli teğet çerçevesi)
  *Pratik eşik (çıkarım, ölçülmedi): kavis yarıçapı ≥ 10 × (heightScale ×
  dokunun dünya boyutu).*
- ⛔ **Tek düzlemde çalışır.** Köşeye binen yamada parallax iki yönde birden
  kayar ve dağılır. Ölçülen örnekte üç yamanın üçü de düz duvarda, hiçbiri
  köşeye değmiyor.

---

## 6. DOKU — işin asıl yarısı burada

Parallax yalnız boyalı olanı kaydırır. Dolayısıyla **ölçüt şudur:**

> ⛔ **Parallax KAPALIYKEN doku tek başına delik gibi görünmeli.**
> Görünmüyorsa parallax onu delik yapmaz, sadece **kayan bir çıkartma** yapar.

Bu test bir kez yapılmadı ve fikstür çöp çıktı. Somut hatalar (ölçüldü,
oyun içi):

1. ⛔ **Kovuk çevre duvardan AÇIK olmuş.** Gerçek delik çevresinden
   **koyudur**. Açık kalırsa çıkartma gibi durur — tek başına illüzyonu öldürür.
2. ⛔ **Diffuse'a derinlik boyanmamış** — oklüzyon yaratacak öğe (kiriş, moloz,
   kırık kenar) yoksa kayan şey düz desen olarak okunur.
3. ⛔ **Kenar hava fırçası gibi yumuşak** (1024'te ~22 px geçiş). Kırık sıva
   sert ve çentiklidir.
4. ⛔ **Yükseklik profili çanak, olması gereken çukur:** kenarda **dik iniş**,
   sonra **düz taban**. Yayvan rampa parallax'ta bulanık smear verir.

Ek: **ışık.** Beyaz panel + tepe güneşi okunabilirliğin en kötü hâlidir.
Etki karanlık ve yandan ışıklı ortamda okunur.

### Doku seti (`normal_spec_pxm`)

| sampler | içerik | not |
|---|---|---|
| `DiffuseSampler` | deliğin içi **boyalı**, dışı yüzey | DXT1 yeter |
| `heightSampler` | 1 = yüzey, 0 = en derin | DXT5 (alfada da tut → gradyan temiz) |
| `BumpSampler` | normal map | height'tan türetilebilir |
| `SpecSampler` | kovuk mat, yüzey hafif parlak | DXT1 |

---


## 7. BOZULMAYI GİZLEME

Parallax dik bakışta kaybolur, çok yatık bakışta yüzer. Ölçülen satılık asset
deliklerin önüne **demir parmaklık** koymuş: oyuncuyu mesafede tutuyor ve
bozulmanın en görünür olduğu kenarları kırıyor. Parmaklık dekor değil,
**efektin maskesi**. *(çıkarım — ama üç delikte de tutarlı.)*

---

## 8. SOLLUMZ TARAFI

Shader kaydı `cwxml.shader.ShaderManager`'da **değil**:
`…/sollumz/lib/python3.13/site-packages/szio/gta5/Shaders.xml`

```python
from bl_ext.user_default.sollumz.ydr.shader_materials import create_shader
mat = create_shader("normal_spec_pxm.sps")
mat.node_tree.nodes['heightScale'].outputs[0].default_value = 0.04
mat.node_tree.nodes['heightBias'].outputs[0].default_value = -0.20
mat.node_tree.nodes['DiffuseSampler'].image = img   # img.name = ytd'deki doku adı
mat.node_tree.nodes['DiffuseSampler'].texture_properties.embedded = False
```

**Mesh gereksinimi:** layout `Position / Normal / Colour0 / TexCoord0 /
TexCoord1 / TexCoord2 / Tangent` → Blender'da **`UVMap 0` / `1` / `2`** aç,
tangent'ı Sollumz üretir.

⛔ **`ob.sz_lods.high.mesh = ob.data` atanmazsa export drawable'ı KOMPLE atlar.**
Betikle üretilen mesh'lerde bu alan `None` kalır.

⛔ **`target_formats` hem NATIVE hem CWXML ise çıktı `gen8/` ve `gen9/`
ALT KLASÖRLERİNE gider.** FiveM için **gen8**.

---

## 9. DOĞRULAMA — geri okumadan "oldu" deme

```bash
powershell -File "${CLAUDE_PLUGIN_ROOT}/scripts/res_to_xml.ps1" -Path out/gen8/x.ydr
```

XML'de kontrol edilecekler:
- materyal sayısı = beklenen
- `<FileName>` hash'i doğru shader mı — JOAAT ile karşılaştır
  (`normal_spec_pxm.sps` → **`58C733F4`**, `normal_spec.sps` → **`14A780FD`**)
- `heightScale` / `heightBias` değerleri **binary'nin içinde** mi
- `ShaderIndex` her geometriye doğru materyali bağlamış mı

⛔ Export "0 uyarı" verdi diye dosya doğru sanma. Dosya boyutu da ölçüt
değildir (RSC7 zlib sıkıştırılmıştır).

---

## 10. OYUNDA TEST — kalibrasyon tahtası deseni

Tek `.ydr` içinde yan yana N panel, hepsi aynı dokuyu paylaşır, **yalnız
`heightScale` değişir**, artı bir **parallax'sız kontrol paneli**.
Tek yürüyüşle N sorunun cevabı alınır.

Bakma sırası:
1. **Tam karşıdan** — bütün paneller birbirinin aynı olmalı. Değilse
   `heightBias` modeli yanlıştır.
2. **Yana kayarak açılı** — derinlik burada çıkar; hangisi inandırıcı,
   hangisi yüzüyor.
3. **Çok yatık** — bozulmanın başladığı açıyı gör.

⛔ Kontrol paneli **tek başına delik gibi görünmüyorsa test hiçbir şey
ölçmez** (§6).

Asset değişti → sunucudan **çıkıp yeniden bağlan**; restart yetmez.
