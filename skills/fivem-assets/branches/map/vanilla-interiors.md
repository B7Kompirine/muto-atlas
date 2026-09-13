# Vanilla iç mekân ölçüsü — pah, bütçe, shader envanteri, gölge/kir mesh'i

**Ne zaman okunur:** kendi MLO/iç mekânını vanilla kalitesinde kuracaksın: köşe pahı kaç mm, poligon bütçesi, hangi shader, vertex color, gölgenin nereden geldiği.
**When to read:** measuring a vanilla interior — scale, budget, shader inventory, how Rockstar handles shadows.
**Kaynak:** `vanilla-ic-mekan-olcumu.md` (tamamı, 2026-08) · **Ölçüm:** v_coroner + v_abattoir alan alan
**Önce:** `branches/map/_branch.md` · gövde › `trunk/flags.md`, `trunk/tool-pitfalls.md`

---


Kaynak: `Interior_References.7z` / `_V2.7z` (39 vanilla iç mekân, Sollumz ile
Blender'a aktarılmış). Ölçülen ikisi: **`v_coroner`** (penceresiz bodrum morg)
ve **`v_abattoir`** (gün ışığı alan mezbaha).
Yöntem: Blender 5.2, `--background`, iki geçiş. Vertex color **`.color_srgb`**
ile okundu (BYTE_COLOR'da `.color` gamma çözer ve maskeyi sessizce koyultur).

⚠ Bu iki dosya 2013 launch iç mekânıdır; sonraki DLC'ler farklı olabilir.

---

## 1. BÜTÇE

| | `v_coroner` | `v_abattoir` |
|---|---|---|
| obje / mesh | 5.413 / 3.952 | 3.232 / 2.352 |
| **ışık** | **249** | **120** |
| materyal / doku | 1.667 / 755 | 1.094 / 471 |
| **üçgen** | **613.730** | **548.147** |

Karşılaştırma: satılık modern bir MLO **537 obje / 183.574 üçgen**. R\*'ın morgu
onun **3,3 katı üçgen, 10 katı obje**.

**Kural:** poligonda kendini gereksiz sıkma — ama R\* atmosferi **249 ışıktan**
alıyor, poligondan değil.

---

## 2. PAH / BEVEL — köşe yumuşatma ölçüsü

Yöntem: GTA drawable'ı **üçgenlenmiş** gelir → önce
`bmesh.ops.dissolve_limit(angle_limit=radians(2), delimit={'NORMAL'})`, sonra
ince şerit n-gon araması (min kenar < 20 cm · max/min > 2,5 · ≥2 kenarda >12°).

| | pah şerit | sert 90° | oran | **medyan** | p25 | p75 |
|---|---|---|---|---|---|---|
| **coroner kabuk** | 2.769 | 250 | **11,1 : 1** | **17,2 mm** | 11,1 | 23,9 |
| coroner prop | 18.298 | 2.143 | 8,5 : 1 | 9,3 mm | 5,9 | 19,0 |
| abattoir kabuk | 3.695 | 1.835 | 2,0 : 1 | 23,3 mm | 15,6 | 32,5 |
| abattoir prop | 24.727 | 7.021 | 3,5 : 1 | 20,2 mm | 12,0 | 41,2 |

**Kural: mimari köşeleri ~1,5–2 cm pahla.** 1 mm de değil, 10 cm de değil.
Prop'larda daha ince (~9 mm). R\* neredeyse hiçbir köşeyi keskin bırakmıyor.

⚠ **Ölçümün sınırı:** "iki açılı yüz arası ince şerit" tanımı **silindir
tesselasyonuna da uyar** (boru, direk, korkuluk). Ayırt edici gösterge
**dönüş açısı medyanı**: coroner kabuk **60,1°** (gerçek köşe pahı, iki ~30°
adım), abattoir kabuk **119,7°** (silindir → o satır şişkin).
Güvenilecek satır **coroner kabuk**.

---

## 3. SHADER ENVANTERİ (üçgene göre)

**v_coroner:** `default` 139.983 · `default_spec` 118.042 · `normal_spec` 83.789 ·
`spec` 72.061 · `normal` 54.521 · `normal_spec_reflect_alpha` 22.296 ·
`normal_spec_detail` 16.786 · `glass_env` 8.360 · `emissive` 7.196

**v_abattoir:** `spec` 184.864 · `normal_spec` 114.816 · `default` 56.718 ·
`default_spec` 29.608 · `normal_spec_tnt` 20.768 · `cutout` 9.276 ·
`emissivenight` 3.114

⛔ **İki iç mekânda da tek bir `*_pxm` shader YOK.** 4 katmanlı terrain shader
de üst sıralarda yok. R\* bu iç mekânları **en düz shader'larla** kuruyor.

→ **`normal_pxm` numarası modern modder tekniğidir, R\* imzası değil.**
R\* derinliği **geometri + doku + vertex color + ışık**tan alıyor.
(Parallax ailesi ağırlıkla dış mekân/terrain ve sonraki DLC'lerde — bkz.
`branches/look/parallax.md` §4.)

---

## 4. VERTEX COLOR — "alt yeşil / üst mavi" iddiası KISMEN YANLIŞ

`Color 1` (= GTA `Colour0`), kabuk objesi Z ekseninde 4 banda bölünerek okundu.

### v_coroner — penceresiz bodrum

| obje | alt | → | → | üst |
|---|---|---|---|---|
| `v_2_bsnt_shell` | R.047 G.307 **B1.000** | G.157 B1.000 | G.111 B1.000 | G.197 B1.000 |
| `v_2_strs_shell` | R.000 G.103 **B1.000** | G.142 B1.000 | G.178 B1.000 | R.075 G.165 B1.000 |
| `v_2_tpoff_shell` | R.103 G.260 **B1.000** | G.224 B1.000 | G.287 B1.000 | G.344 B1.000 |

**Mavi kanal tepeden tırnağa 1.000'e sabit.** Kırmızı düşük ve neredeyse sabit.
Değişen tek kanal yeşil ve değişimi yükseklikle **monoton bile değil**.
→ "alt yeşil / üst mavi" tarifi burada **çıkmıyor**.

### v_abattoir — gün ışığı alan

`v_11_abattoirshell`: yeşil tabanda **0,225** → tavanda **0,101**; kırmızı ve
mavi yükseldikçe artıyor. → Yön doğru, **harfiyen değil**.

**Kural:** bu kanallar bir boyama paleti değil, **ortam ışığı kapısıdır**
(natural / artificial ambient gate). Değeri ezberden değil, **mekânın ışık
durumundan** türet: penceresiz mekânda doğal katman kapalıdır.

**Katman envanteri:** yalnız **`Color 1`** var (coroner 922 mesh, abattoir 479).
**`Color 2` hiç yok.** Yanında sadece tint prop'larının `TintColor (…_pal.dds)`
katmanları.

---

## 5. YAPISAL DESENLER — kopyalanabilir

### 5.1 Gölge ayrı geometridir

`v_2_shadowmap1/2/3.model` — kabukla **aynı bbox**, daha düşük poligon
(1.208–1.468 vs kabuk 1.979–4.165), vertex color **tam siyah (0,0,0)**.
abattoir karşılıkları: `v_11_abattoirshadprox` (168 poly), `v_11_abbcorrishad`,
`v_11_abbmnrmshad1`.

→ İç mekân gölgesi ışıktan değil, **ayrı bir düşük-poli mesh'ten** geliyor.
Işık sayısını artırmadan önce bu deseni düşün.

### 5.2 Kir ve kan ayrı overlay mesh'idir

`v_11_abbnardirt`, `v_11_ab_dirty` (554 poly) ve **`v_11_coolblood001`
(15,8 × 87 × 7,1 m)**. Dokuya gömülmemiş, kabuğun üstüne **ayrı ince mesh**
olarak konmuş. coroner'da benzeri: `v_2_tpo_over_normal` ("over" = overlay).

### 5.3 Kabuk parçalıdır

coroner'da tek dev kabuk yok, **oda grubu başına ayrı kabuk**:
`v_2_bsnt_shell` (42,8 × 54,0 × 4,2 m) · `v_2_strs_shell` (29,5 × 27,9 × 21,4) ·
`v_2_tpoff_shell` (35,6 × 19,7 × 4,3).

---

## 6. DOĞRUDAN UYGULANABİLİR ÇIKARIMLAR

1. Köşeleri **~1,5–2 cm** pahla (§2).
2. Kabuğu **oda grubuna böl**, tek parça yapma (§5.3).
3. Gölge için **ayrı düşük-poli mesh** düşün, ışık sayısını artırmadan (§5.1).
4. Kir/kan/leke **ayrı overlay mesh** olarak, dokuya gömmeden (§5.2).
5. Vertex color'ı **palet ezberiyle değil**, mekânın ışık durumuna göre yaz (§4).
6. İç mekânda parallax R\* deseni değil — derinliği geometri ve ışıktan al (§3).

---

## 7. ÖLÇÜM BETİKLERİ

`scripts/` altında değil, oturum scratchpad'inde üretildi; taşınmak isteniyorsa:

- envanter + shader envanteri + vertex color Z-profili + ışık dökümü
- `dissolve_limit` sonrası pah şeridi ölçümü, kabuk/prop ayrımı

**Ölçülmemiş, açık:** `v_genbank`, `v_hospital`, `v_janitor`, `v_fib01`,
`v_policehub` ve 34 iç mekân daha.
