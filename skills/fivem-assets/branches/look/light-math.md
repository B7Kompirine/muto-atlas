# Işık matematiği ve Blender önizlemesi — motorun dört formülü, gölge bias, sessiz hata kataloğu

**Ne zaman okunur:** Blender'da başka oyunda başka görünüyor; kendi ışık önizlemeni kuracaksın; düşüş/koni/ambient/tone mapping formülü.
**When to read:** what the engine's light formulas actually do, and previewing a light in Blender before it goes in game.
**Kaynak:** `lights.md` §1-8, 'Blender önizlemesi', 'Sessiz hata kataloğu', 'Veri kurulumu' (2026-08) · **Ölçüm:** motorun shader kaynağı (`lighting_common.fxh`) port edildi; `pow()` sapması %17,3
**Önce:** `_branch.md` · gövde › `trunk/tool-pitfalls.md` §1-2 · araç `scripts/blender_light_preview.py`

---


Bir prop'un ışığının Blender'da bir türlü, oyunda başka türlü görünmesinin
sebebi neredeyse hiç "ayarı tutturamadım" değildir. Motorun kullandığı dört
formül, Blender'ın (ve çoğu önizleme aracının) kullandığından **yapısal olarak
farklıdır**. Bu dosya o dördünü ve etrafındaki sessiz hataları toplar.

Sorgular:
```
python assetdb.py light <ydr|yft>          # gömülü ışıkları çöz
python assetdb.py cycle w_clear --hour 20  # hava cycle'ı: ortam + güneş
python assetdb.py timecycle <modifier>     # odanın ezmesi
```

---

## 1. Düşüş eğrisi `pow()` DEĞİLDİR

Motor rasyonel bir yaklaşım kullanır:

```
powApprox(a, b) = a / ((1 - b) * a + b)
```

0 ve 1'de tamdır, arada `pow(a,b)`'ye **yaklaşır**. Aynı eğriyi `pow()` ile
çizmenin ölçülen bedeli: **%17.3 sapma** (falloff 90 m, üs 8).

İki ek ayrıntı, ikisi de atlanınca sessizce yanlış eğri verir:

- Fonksiyon **kare mesafe** üzerinde çalışır: `distanceFalloff(d², 1/max², üs)`
- Işığın yarıçapında **kesilir** — ters kare değil, sınırlı bir eğri

## 2. Spot konisi açıda değil, KOSİNÜSTE lineerdir

```
cosDış = cos(dışAçı);  cosİç = cos(içAçı)
ölçek  = 1 / max(cosİç - cosDış, 1e-4)
sonuç  = saturate(cosAçı * ölçek - cosDış * ölçek)
```

Açıda lineer bir geçiş (Blender'ın `spot_blend`'i dahil) kenarı yanlış yerde
yumuşatır. Koni açıları Sollumz'da **radyan** tutulur (`subtype=ANGLE`,
0–π/2) — dereceyle yazmak koniyi tamamen açar.

## 3. Capsule ışık = doğru parçasına en yakın nokta

Uzantı `yön * (extent.x * 0.5)` ile ±ekseni verir; ışığa uzaklık o parçaya
olan en kısa mesafedir, merkeze değil. Sonrası nokta ışıkla aynıdır.

## 4. Ortam ışığı yarım küre lerp'i DEĞİLDİR

```
downMult = max(0, (n.z + wrap) / (1 + wrap))
ortam    = ÜstRenk * downMult + AltRenk
```

`wrap` = `light_amb_down_wrap`, timecycle'dan gelir (**varsayılanı 1.0**).
İç mekânların "düz" görünmesinin sebebi çoğu zaman bunun yerine hemisphere
lerp kullanılmasıdır.

Ayrıca ortam **iki ayrı katmandır** ve ikisi farklı maskelerle kapılır:

| katman | kaynak | kapı |
|---|---|---|
| natural (gökyüzü) | `light_natural_amb_*` | vertex color 0 **.r** |
| artificial (iç mekân) | `light_artificial_ext_*` | vertex color 0 **.g** |

Bunlar **bake edilmiş maskelerdir**. Sollumz onları `"Color 1"` adıyla,
CORNER domain'de, BYTE_COLOR olarak taşır.

> ⛔ **Blender BYTE_COLOR tuzağı:** `.color` gamma çözer, `.color_srgb` ham
> bayt/255 verir. Motor ham değeri çarpan olarak kullanır — `.color` okumak
> her maskeyi sessizce koyultur, hata da vermez.

## 5. Tone mapping: Hable filmic

```
A=0.22 B=0.30 C=0.10 D=0.20 E=0.01 F=0.30,  beyaz nokta 11.2
f(x) = ((x(Ax+CB)+DE) / (x(Ax+B)+DF)) - E/F
sonuç = saturate(f(renk) / f(11.2))
```

Kendi uydurduğun highlight rolloff'u gündüzü beyaza kırpar. Bu eğri kırpmaz.

## 6. Specular — üç ayrı sessiz hata

- **Spec map'i olmayan materyal mat değildir.** Motor sabit **0.1** besler.
  Sıfırlamak her yüzeyi matlaştırır; "specular tutmuyor" şikâyetinin en sık
  sebebi budur.
- **Kanallar ayrı okunur, dot'lanmaz:** `x` = yoğunluk, `y` = üs.
- **Fresnel MAP'ten değil MATERYALDEN gelir** (`specularFresnel`, preset
  vermezse 0.97). Mavi kanaldan almak, spec map'i olan her materyalde fresnel
  kontrolünü işlevsiz bırakır.
- Üs yeniden eşlenir: `0..500 → 0..1500`, `501..512 → 1500..8192`
  → `(ham - taşan) * 3 + taşan * 558`

## 7. Detail map iki iş birden yapar

Tek doku hem normali büker (XY) hem diffuse'u karartır (X). Fade **spec
map'in alpha kanalından** gelir. PC'de tile ikinci kez **3.17×** ölçekte
örneklenip ortalanır — o tuhaf oran tiling'in ızgara gibi okunmasını
engeller.

## 8. Diğer sabitler

- Renk CPU'da önçarpılır: `rgb * (2 * yoğunluk / 255)` — baştaki **2** atlanır
- UV dönüşümü **bir kez** uygulanır, tüm sampler'lar sonucu kullanır; ayrılırsa
  kayan tabelanın normal map'i diffuse'unun altından kayar
- Canlı çalışan bayrak bitleri: **6** cast shadows · **13** no specular ·
  **23** don't light alpha (alpha geometriyi tamamen atlar)
- Projeksiyon dokusu oyunda **aynı adlı bir `.ytd` içinde** gitmek zorundadır
- Işıklar `.ydr`/`.yft` içine RSC7 / gen8 olarak yazılır

---

## Blender önizlemesi

Blender'ın kendi ışıkları bu matematiği **ifade edemez** (ters kare + açıda
lineer koni). O yüzden önizleme kendi geçişini çizer, Sollumz ışıklarını
doğrudan okuyarak.

```python
import sys; sys.path.append(r"${CLAUDE_PLUGIN_ROOT}/scripts")
import blender_light_preview as lp
lp.enable()
lp.load_timecycle("w_clear", hour=19)
lp.cfg(albedo=0.35, exposure=1.6)      # gerçek asfalt ~0.2-0.35
lp.load_timecycle("w_clear", 2, modifier="v_dark", strength=1.0)
lp.cfg(mode=3)                          # gölge faktörü görselleştirme
lp.report(); lp.disable()
```

Modlar: `0` lit · `1` sadece ışık · `2` normal · `3` gölge faktörü.

**Blender 5.x notları:** `GPUShader(vs, fs)` kaldırıldı, `create_from_info`
zorunlu. `GPUStorageBuf` yok — ışıklar UBO'dan geçer (64 tavanı buradan gelir).
Overlay Blender'ın solid geçişiyle aynı derinlikte çizerse tüm sahne z-fight
eder; kendi geçişinden önce depth buffer temizlenir.

### Gölge bias'ı texel biriminde olmalı

⛔ Bir aracın gölge bias sabitini kopyalama. Sabit metre cinsinden bias sadece
ayarlandığı ölçekte doğrudur: prop için doğru olan 0.15 m, 660 m'lik bir
sahnede (texel 0.44 m) düz zeminin **%72'sini** gölgeli işaretledi. Bias texel
boyutuyla ölçeklenir ve normal-offset ile birlikte kullanılır.

**Akne ile gerçek gölgeyi oran değil derinlik dağılımı ayırır.** Akne bias'ın
hemen üstünde toplanır. Ölçülen düzeltilmiş durumda: 1 m altında kapanma
**%0**, medyan derinlik **7.3 m** → bunlar gerçek gölgedir.

---

## Sessiz hata kataloğu

| belirti | gerçek sebep |
|---|---|
| düşüş eğrisi oyunla tutmuyor | `pow()` kullanılmış, rasyonel yaklaşım değil |
| koni kenarı yanlış yerde yumuşuyor | açıda lerp; kosinüste olmalı |
| koni tamamen açık | açı dereceyle yazılmış, radyan olmalı |
| iç mekân düz görünüyor | hemisphere lerp; `downMult` formülü olmalı |
| maskeler koyu | `.color` okunmuş, `.color_srgb` olmalı |
| her yüzey mat | spec map yok diye 0 beslenmiş, 0.1 olmalı |
| fresnel kontrolü hiçbir şey yapmıyor | fresnel map'ten okunmuş, materyalden olmalı |
| gündüz beyaza patlıyor | filmic yerine ad-hoc rolloff |
| timecycle bir saat kaymış | `time.xml`'de `name` okunmuş, `hour` olmalı |
| yanlış timecycle yüklenmiş | 4 sample'lik `data/time.xml` alınmış |
| düz zemin gölgeli | gölge bias'ı sahne ölçeğine göre normalize edilmemiş |
| projeksiyon dokusu oyunda yok | aynı adlı `.ytd` ile gönderilmemiş |
| ışık günün hiçbir saatinde yanmıyor | `time_flags.total = 0` |
| projeksiyon yan yatmış | `Tangent` = *up*; Sollumz oraya yerel X yazıyor |
| eğim/koni ayarı oyunda hiçbir şeyi değiştirmiyor | ışığın transformu mesh sıfırlamasıyla birlikte silinmiş |
| yuvarlak pencere sivri, sivri pencere yuvarlak düşüyor | gobo kareye sıkıştırılmış, en-boy oranı kaybolmuş |
| yer lekesinin köşeleri sivri | kare dokunun boş köşeleri; vinyet yok |
| lekenin ortasında koyu elips | `static_shadows` açık, pencere kendi ışınını engelliyor |

---

## Veri kurulumu

Hava cycle'ları oyunun arşivindedir ve **katmana gömülmez** — kullanıcının
kendi kurulumundan üretilir:

```
powershell -File build_cycle.ps1
python assetdb.py cycle --liste
```
