# Işık matematiği ve oyun-doğru önizleme

Bir prop'un ışığının Blender'da bir türlü, oyunda başka türlü görünmesinin
sebebi neredeyse hiç "ayarı tutturamadım" değildir. Motorun kullandığı dört
formül, Blender'ın (ve çoğu önizleme aracının) kullandığından **yapısal olarak
farklıdır**. Bu dosya o dördünü ve etrafındaki sessiz hataları toplar.

Sorgular:
```
python assetdb.py light <ydr|yft>          # gömülü ışıkları çöz
python assetdb.py cycle w_clear --saat 20  # hava cycle'ı: ortam + güneş
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

## Timecycle katmanı

Bir sahnenin görünümü üç katmandır ve sırası şudur:
**taban hava cycle'ı → odanın modifier'ı → prop'un kendi ışığı.**
"Işığı doğru kurdum ama hâlâ yanlış" diyorsan ilk ikisine bak.

Ölçülmüş, tahmin edilmemesi gerekenler:

- Bir cycle dosyası `cycle > region > <değişken>metin</değişken>` yapısındadır
  ve metin **keyframe başına** bir değer taşır. **13 keyframe vardır, 24 saat
  değil.** "saat = indeks" varsayımı her şeyi kaydırır.
- Saat çizelgesi ayrı dosyadadır ve **iki tane `time.xml` vardır**. Doğrusu
  `common.rpf\data\levels\gta5\time.xml` (13 sample);
  `common.rpf\data\time.xml` 4 sample'lik bambaşka bir dosyadır.
  Saatler: `0 5 6 7 10 12 16 17 18 19 20 21 22`
- ⛔ Bir sample `name="09:00"` yazar ama `hour="10"` taşır. **Ad yalan söyler,
  `hour` niteliği esastır.** Ada bakan sonraki tüm keyframe'leri bir saat kaydırır.
- Renkler zaten 0–1'dir (ölçülen maks 1.002), hiçbir yerde /255 yoktur
- `light_dir_mult` HDR'dir, **54'e** kadar çıkar — kırpma opsiyonel değildir
- Bölge katmanı vardır: `GLOBAL` ve `URBAN`
- Modifier bir **değiştirme değil harmandır**: `taban + (mod − taban) × güç`,
  ve param bazındadır (bir modifier natural'ı sıfırlarken artificial'a
  dokunmayabilir). Modifier tablosunda param başına iki değer bulunur;
  geçerli olan **birincisidir**.

> **Kırpma tavanları kalibrasyondur, motor sabiti değil.** `cycle.py` içindeki
> `TAVAN_ORTAM` / `TAVAN_GUNES` parametredir; vanilla görüntüyle
> karşılaştırarak doğrula, gömülü sabit gibi davranma.

---

## Işığı okuma ve geri yazma — oyuna girmeden

```bash
assetdb.py light prop_lamp.ydr              # oku + sihirli sayıları çöz
assetdb.py light prop_lamp.ydr --uygula duzenleme.json
assetdb.py light prop_lamp.ydr --set 0.Intensity=8 --ekle --sil 1
```

Hat iki parçadır ve ikisi de ölçüldü:

| parça | ne yapar | dosya |
|---|---|---|
| çözme | `.ydr/.yft` → mesh + kemik dünya matrisleri + 40 alanlı ışıklar | `light_sahne.py` |
| geri yazma | `res_to_xml → XML → xml_to_res`, sonra **geri okuma** | `light_edit.py` |

Ölçülmüş vanilla dağılımı `light.referans()` ile canlı gelir
(`data/lights.tsv.gz`; bu kurulumda 72.539 ışık / 4.476 dosya):
her sayısal alan için `p05 / medyan / p95 / min / maks`. Katman yoksa
**aralık uydurulmaz**, referans hiç sunulmaz.

### Üç sessiz bağ

- **Işık kemiğe bağlıdır.** `prop_worklight_01a` → `BoneId 41615`
  (`Worklight_01A_Bulb`), zincirde **1.737 m** yukarıda; ışığın kendi
  `Position`'ı (0, −0.015, 0.009) bunun **üstüne** biner → dünya
  (0, −0.102, 1.746). Kemik zinciri kurulmazsa ışık yerde durur ve
  "ışığım yanlış yerde" denir. Vertex'ler de `HasSkin=1` ise kemik
  uzayındadır (prop'ta ağırlık tek kemiğe %100, yani rijit).
- **`TimeFlags` bir sayı değil saat kümesidir.** `14680095` = `0xE0001F`
  → bit 0–4 ve 21–23 = **8 saat**, 21:00–05:00. Saat 20'de ışık **yanmaz**.
  Kullanıcı "ışığım yanmıyor" dediğinde ilk bakılacak yer ışığın kendisi
  değil, saattir. Bir önizleme bunu uygulamazsa araçta parlak görünür,
  oyunda karanlık çıkar.
- **Boyut geçerlilik ölçütü DEĞİLDİR.** Aynı içerik 15.056 → 15.904 bayt
  çıktı (RSC7 zlib). Tek ölçüt geri okumadır; `--uygula` yazdıktan sonra
  dosyayı yeniden çözer, ışık sayısı tutmazsa hata verir ve orijinali
  `.yedek` olarak korur.

### Köken

Bağımsız bir uygulamadır. Matematik oyunun kendi shader dosyalarından
(`lighting_common.fxh`, `common.fxh`, `postfx.fx`) türetilmiş ve ölçümle
doğrulanmıştır; referans bantları kullanıcının kendi kurulumundan yerel olarak
hesaplanır ve dağıtılmaz (`data/` gitignore'lu). Herhangi bir üçüncü taraf
düzenleme aracının kodu, varlıkları, arayüzü, adları ya da markası **yoktur**.

### Bir önizleme kurarken — sınırı baştan söyle

Bu matematikle kurulan herhangi bir önizleme bir **render değildir**. Bilerek
dışarıda kalanlar: **doku** (albedo tek sayıdır), **korona sprite'ı**,
**hacimsel ışın**, deferred pass'in **SSAO/yansıması**. Cevapladığı soru
"ışık nereye ne kadar düşüyor"dur; "sahne birebir böyle görünecek" değil.

Gölgede de fark var: oyun sanal güneş konumundan **mesafe** saklar. Derinlik
haritasıyla kuran bir önizleme dersi koruyabilir (normal ofseti ağır işi
yapar, bias texel dünya boyutuna göre ölçeklenir) ama depolaması farklıdır.

Bu matematik bir kez ölçülerek doğrulandı (piksel okunarak, ekran
görüntüsüne bakılarak **değil**): saat 12 → `[107,109,110]`,
17 → `[93,95,96]`, 20 → `[14,19,32]`, 06 → `[20,30,38]` — gün boyunca
fiziksel olarak makul ilerleme.

---

## Blender önizlemesi

Blender'ın kendi ışıkları bu matematiği **ifade edemez** (ters kare + açıda
lineer koni). O yüzden önizleme kendi geçişini çizer, Sollumz ışıklarını
doğrudan okuyarak.

```python
import sys; sys.path.append(r"~/.claude/muto-atlas/scripts")
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

---

## Veri kurulumu

Hava cycle'ları oyunun arşivindedir ve **katmana gömülmez** — kullanıcının
kendi kurulumundan üretilir:

```
powershell -File build_cycle.ps1
python assetdb.py cycle --liste
```
