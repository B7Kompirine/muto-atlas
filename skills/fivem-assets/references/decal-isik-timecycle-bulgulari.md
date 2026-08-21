# DECAL · IŞIK · TIMECYCLE — ÖLÇÜLMÜŞ BULGULAR

> Kaynak: 21.08.2026 morg (v_coroner / BodyStorage) oturumu.
> Buradaki her sayı **ölçüldü**. Tahmin yok. Yanlış çıkan teşhisler de
> yazılı — çünkü tekrar edilmemesi gereken asıl şey onlar.

---

## 0. BU OTURUMUN EN PAHALI DERSİ

Bir decal aracını **altı tur** boyunca "düzelttim" diye teslim ettim, altısında
da kullanıcının elinde çalışmadı. Sebep tek bir hata değildi; **her turda
başka bir sessiz hata** vardı ve ben bir öncekini düzeltince ortaya çıkanı
görmeden "hazır" dedim.

⛔ **KURAL: bir düzeltmeyi teslim etmeden önce kullanıcının GERÇEK durumunda
test et.** Tek bir sentetik noktada çalışması yeterli değil. Bu oturumda
"düz duvarda çalıştı" deyip teslim ettim, kullanıcı silindirde/merdivende
denedi ve kırıldı — üst üste.

⛔ **"Obje oluştu, sayılar makul" ÇALIŞIYOR DEMEK DEĞİLDİR.** Bu oturumdaki
sessiz hataların hepsi bu kalıptaydı: yüz sayısı yüzlerce, alan makul,
hata yok, **ekranda hiçbir şey yok.**

---

## 1. PROJEKSİYON DECAL — ÜÇ YÖNTEM, ÜÇ SERT SINIR

Bir yüzeye decal koymanın üç yolu var. Hiçbiri diğerinin yerine geçmez.

| Yöntem | Nasıl | Sert sınırı |
|---|---|---|
| **Işın izgarası** | Düzgün ızgara kurup yüzeye ışın atar | **Işına paralel yüzeye asla vuramaz** |
| **Geometri kopyala** | Hedefin üçgenlerini kopyalar | UV tek eksenden gelir → dik yüzde doku **esner** |
| **Kutu (triplanar)** | Kopyalar ama UV'yi yüzün kendi eksenine verir | Desen köşede **yeniden başlar** (dikiş) |

### Işın yönteminin sınırı ölçüldü

Odanın iç köşesinde 64×64 ızgara: **4096 hücrenin 1344'ü hiçbir yüzey
bulamadı.** Merdivende **4096'nın 2732'si**. Sebep geometrik: merdiven
rungları ~2 cm boru, aralarında hava; ışınlar teğet geçiyor.
**Hiçbir açı/eşik ayarı bunu çözmez.**

Silindirde ölçüm: ışın yöntemi 288 yüz / **2 farklı normal bandı** (düz
kalıyor), kutu yöntemi 89 yüz / **39 normal bandı** (sarıyor), alan 3.5 katı.

### Karar tablosu

- Düz/geniş yüzey (duvar, kapak, masa üstü) → **ışın** (sürekli, ucuz)
- Silindir, köşe, dönüş yüzeyi → **kutu**
- İnce boru/ızgara (merdiven, cam kayıtları) → **hiçbiri**; Surface Painter
  ya da dokuya bake

---

## 2. DECAL ARACINDA BULUNAN SESSİZ HATALAR

Hepsi ölçümle bulundu, hiçbiri hata mesajı üretmedi.

### 2a. UV katmanının ADI materyalle eşleşmeli
GTA/Sollumz materyali **`"UVMap 0"`** arar. `"UVMap"` yazarsan eşleşme
kurulmaz, UV `(0,0)`'a düşer, atlasın saydam köşesi örneklenir.
**Ölçüm:** 505 yüzlü, doğru konumlu, %97'si dolu alfaya denk gelen decal
tek başına render edildiğinde **tamamen boş** çıktı.

### 2b. Geometri kopyalarken hedefin UV'si de gelir
`.new()` ile ikinci katman açılınca materyal **hâlâ birinciyi** — yani
duvarın fayans UV'sini — okur. **Ölçüm:** UV aralığı `u 0.078..4.628`,
`v -1.750..18.440`; atlas gözü ise `0.75..1.00 / 0.50..0.75`. Doku
defalarca tekrar ediyordu → "her kareye parça parça yerleştiriyor".
→ Yeni katmandan **önce mevcut UV katmanlarını sil.**

### 2c. Vertex rengi de hedeften miras alınır
Materyal alfayı `doku_alfası × Color1_alfası` diye çarpıyor. Kopyalanan
geometri hedefin `Color 1`'ini getirir. **Ölçüm:** `v_2_bds_over_shadow`
üzerine düşen decal'in Color1 alfası **0.498** → decal yarı saydam.
→ `Color 1` / `Color 2`'yi **her zaman** (1,1,1,1) yaz; "yoksa oluştur" yetmez.

### 2d. Alfa haritasında satır 0 görüntünün ALTIDIR
`bpy.types.Image.pixels` alttan üste dizilir: `v=0 → satır 0`.
`1-v` yazmak elemeyi dikeyde ters çevirir → **dokunun boş olduğu hücrelerde
üçgen üretilir, dolu olanlar atılır.** Düzeltmeden sonra üretilen hücrelerin
**%97'sinde alfa > 0.5** (önce %1).

### 2e. "Cursor çevresindeki baskın normal" YANLIŞ ÖLÇÜTTÜR
Masada cursor üstteyken 0.8 m kürenin içinde tablanın **alt** yüzeyleri daha
geniş alan kapladığı için normal `(0,0,-1)` seçildi; decal **masanın altına**
yapıştı (decal z −8.86..−8.71, masa üstü −8.67). Kullanıcı hiçbir şey görmedi.
→ Doğru ölçüt **bakış**: kameradan cursor'a ışın, ilk çarpılan yüzün normali.
Aynı noktada eski `(0,0,-1)`, yeni `(0.03,0.01,1.0)`.

### 2f. Bakış ışını GERÇEK göz konumundan atılır
Cursor'un 30 m gerisinden başlatmak kapalı mekânda binanın **dışında** kalır;
ışın duvarın **dış** yüzüne çarpar, normal ters döner, ızgara hiçbir yere
vurmaz → *"Yüzey bulunamadı"*. Asansörün içinde tam bu oldu.

### 2g. Tam dik yüzün dot'u 0.000'dır
Arka yüz elemesini `dot <= 0` yazmak **köşe dönüş yüzlerini** arka yüz sayıp
eler. Odanın iç köşesinde 48 hücre bu yüzden düştü, gri şerit kaldı.
→ Eşik `-0.05` gibi küçük bir negatif olmalı.

### 2h. ⛔ `bmesh.ops.bisect_plane` BU GEOMETRİDE KIRPMIYOR, YÜZ SİLİYOR
**Ölçüm (en net kanıt):** altı bisect çağrısı boyunca **yüz sayısı 637'de
sabit** kalırken alan `3.553 → 2.552 → 1.401 → 0.941 m²`'ye düştü. Yani
büyük yüzler kesilip içerideki parçası tutulmadı, **komple gitti.**
Sonuç: dolap kapakları kaldı, aralarındaki geniş panel yok oldu, decal
kapak kenarında **dümdüz kesildi**.

### 2i. Boolean INTERSECT açık/ince mesh'te GÜVENİLMEZ
Aynı duvarda dört decal: biri **hiç kırpılmadı** (3.706 m², kutu 2.56),
biri neredeyse **boş** kaldı (0.025 m²).

### 2j. ÇÖZÜM: Sutherland–Hodgman
Her üçgeni altı yarım uzaya sırayla kırp, kesişim noktalarını tam hesapla.
**Çözücüsü yok → başarısızlık modu yok.** Beş test (düz duvar ×3, silindir,
köşe): **hiçbiri kutu alanını aşmadı**, UV hepsinde atlas gözünün içinde.

### 2k. Kutu yönteminde ekseni HER YÜZ için `max()` ile seçme
Duvar 0.3 m²'lik panellerden oluşuyor ve normalleri birbirinden biraz farklı;
`max()` komşu panellerde **farklı eksen** seçiyor, her panel bağımsız UV
alıyor. **Ölçüm:** cursor çevresindeki 10 yüzün 4'ü `n`, 6'sı `u` seçti.
→ Ana eksen **decal'in kendi yönüdür**; bir yüz ancak **70°'den fazla**
sapmışsa yan eksene geçer.

### 2l. "Seçili obje" ölçütü kullanıcıyı yakar
Bir duvar tek obje değildir: dolap bankı, kabuk, süpürgelik, çerçeve,
borular **ayrı objelerdir**. **Ölçüm:** aynı kutuda yalnız `bodydrawers`
**0.656 m²**, tüm görünür objeler **6.318 m²** (10 kat).
→ Varsayılan **"görünür her şey"** olmalı.

### 2m. Ama "görünür her şey" KENDİ DEKORUNU DA KAPSAR
Filtresiz halde 2×2 m kutuda **20.5 m²** yüzey toplandı — çünkü
`muto_bds_veins`, önceki decal'ler ve collision kutuları da "görünür mesh".
Decal'in üstüne decal atmak olur. Kendi koleksiyonları elenince **3.88 m²**
(kutu 4.00) — tek tutarlı katman.

### 2n. Kutuya giren her yüz GÖRÜNÜR DEĞİLDİR (occlusion)
Dolap kapaklarının arkasında düz bir sırt paneli var; derinlik 0.40 ile ikisi
de kutuya giriyor. Kopyalama yöntemi ikisini birden alıyor, büyük düz arka
panel öne geçip decal'i **havada duran levha** gibi gösteriyor.
→ Yüz merkezinden projektöre ışın at; önünde başka yüz varsa **at**.
(Işın yönteminde bu sorun yok — o zaten ilk çarpmayı alır.)

### 2o. Kutu yönteminde alfa elemesi de olmalı
Işın yönteminde vardı, kutuda yoktu. **Ölçüm:** düz duvarda 487 yüz üretildi,
alan olarak yalnızca **%1'i** dolu dokuya denk geliyordu. Atlas gözlerinin
doluluk oranı **%6.8 – %32** arasında.

---

## 3. BLENDER API TUZAKLARI (bu oturumda yakalananlar)

### 3a. ⛔ `object.dimensions` DÖNÜŞÜ İÇERMEZ
Yerel bbox × ölçek verir. Objeyi döndürmek `dimensions`'ı **değiştirmez**.
"En uzun ekseni X'e getir" mantığını bununla kurmak sessizce hiçbir şey
yapmaz. → Dünya bbox'ı kullan: `matrix_world @ v for v in bound_box`.

### 3b. ⛔ GİZLİ OBJEDE `select_set()` SESSİZCE ÇALIŞMAZ
Export "File exported successfully" der, dosya **0 bayt** çıkar.
**Ölçüm:** 7 objeden 5'i böyle boş yazıldı. → Export öncesi `hide_set(False)`,
sonra **dosya boyutunu kontrol et**.

### 3c. `scene.ray_cast` VIEWPORT'U kullanır
Render'da görünüp viewport'ta gizli bir obje ışın testinde **atlanır**.
Macenta objeyi ararken bu yüzden yanlış objeyi buldum.

### 3d. Edit Mode'a girince ÖNCEKİ SEÇİM geri gelir
`bpy.ops.object.mode_set(mode='EDIT')` sonrası eski yüz seçimi canlanır.
Void Decal Tool bu yüzden **4089 decal** üretti. → Edit Mode'da önce
`for f in bm.faces: f.select_set(False)`.

### 3e. Blender 5.x compositor
- `scene.node_tree` ve `scene.use_nodes` **kaldırıldı** → `scene.compositing_node_group`
  (bağımsız `CompositorNodeTree` datablock, sen yaratıp sen sileceksin)
- `CompositorNodeComposite` düğümü **silindi** → yerine grubun `NodeGroupOutput`'u
  (+ ağacın arayüzüne Image soketi eklemek gerekiyor)
- Düğüm ayarları RNA'dan **giriş soketlerine** taşındı:
  `Blur.filter_type/size_x/size_y` → `Type` (menü) + `Size` (2B vektör),
  `Denoise.use_hdr` → `HDR` (bool soket)

---

## 4. IŞIK DÜZENLEME

Işıklar script'te değil **`.ydr`'nin kendi ışık dizisinde**. Modeli düzenleyip
`stream/` içine aynı adla koymak = override.

### İlk bakılacak yer: TimeFlags
`16777215` = 24/24 (her saat). Vanilla'da en sık ikinci değer `14680191`
= 21:00–07:00. **"Işık yanmıyor" şikâyetinin en sık sebebi saat penceresidir**,
ışığın kendisi değil.

### Flashiness — anlamı hiçbir yerde yazmıyor, dağılımdan okundu
72.539 vanilla ışık tarandı, **68.036'sı = 0** (sabit). Sıfır olmayanlar ve
onları kullanan modeller:

| Değer | Adet | Kullanan modeller (ipucu) |
|---|---|---|
| 15 | 1096 | `v_med_cor_alarmlight`, `xm_prop_x17_sub_alarm_lamp` — kırmızı 255,5,0 **alarm** |
| 17 | 693 | `cs2_30_tunnel_det_*` — tünel lambaları |
| 11/12/13 | ~1400 | kumarhane oyun salonu, sinema — döngüler |
| 9 | 344 | `prop_ld_alarm_alert`, `v_48_emerg_light_a` — **acil durum** |
| 19 | 172 | `gr_prop_damship_01a` (**hasarlı gemi**) |
| 20 | 39 | `ba_prop_battle_lights_fx_rige` — strobe |
| 14 | 22 | `v_73_elev_sec*` — asansör |

⚠️ **`h4_int_club_broken_light` ("kırık ışık") flashiness = 0.** Yani GTA
"kırık" görüntüsünü flashiness ile değil **modelle** yapıyor.

### Vanilla bandı (72.539 ışık)
`Intensity` p05 0.25 · medyan 6 · p95 32 — bandın dışı hata değil, **nadir** demek.

### Işık kemiğe bağlıdır
`Position` **kemik uzayındadır**, model orijininde değil. `BoneId=0` ise
objenin kendi uzayı (statik prop'ların çoğu böyle).

---

## 5. TIMECYCLE

Karanlık **üç katmanlıdır**, sırayla bakılır:
**hava cycle'ı → odanın modifier'ı → prop ışıkları.** Cevap çoğu zaman
üçüncüde değildir.

### Paylaşılan modifier'a DOKUNMA
`morgue_dark` **6 DLC dosyasında** tanımlı ve tüm morg onu paylaşıyor.
Hangisinin kazandığı DLC yükleme sırasına bağlı ve **veriden okunamaz.**
→ Kendi modifier'ını yaz, odanın `timecycleName`'ini ytyp'de değiştir.

### Şema (vanilla'dan kopyalandı, uydurulmadı)
```xml
<timecycle_modifier_data version="1.000000">
  <modifier name="muto_bds_dark" numMods="44" userFlags="0">
    <natural_ambient_multiplier>0.045 0.000</natural_ambient_multiplier>
    ...
  </modifier>
</timecycle_modifier_data>
```
Eleman metni `"deger1 deger2"`. `numMods` gerçek eleman sayısıyla tutmalı.

### FiveM kaydı ŞART
```lua
files { 'data/timecycle_mods_muto.xml' }
data_file 'TIMECYCLEMOD_FILE' 'data/timecycle_mods_muto.xml'
```
Kaydedilmezse oyun modifier'ı **aramaz**, oda vanilla'da kalır.

### Mood için en etkili dört parametre (ölçülen etki)
| Parametre | vanilla morgue_dark | koyu |
|---|---|---|
| `natural_ambient_multiplier` | 0.154 | 0.045 |
| `artificial_int_ambient_multiplier` | 0.632 | 0.300 |
| `ssao_inten` | 6.300 | 9.500 |
| `postfx_vignetting_intensity` | 0.000 | **0.550** ← en görünür fark |

`fog_start` **düşürme** (73 → 4 denendi, beğenilmedi — iç mekânda sis
istenmiyorsa vanilla 73'te bırak).

---

## 6. EMISSIVE PANELLER (fosforlu tavan lambası)

`emissive.sps` shader'ının parlaklığı **`emissiveMultiplier`** parametresinde
(morg panelinde `x=3`).

⛔ **Panellerin ışığı YOKTUR** — sadece emissive geometri. Odanın 3 büyük
paneli tek `Geometry` (6 üçgen) ve tek shader paylaşıyordu; birini
değiştirmek üçünü birden değiştiriyor.

### Tek tek kontrol için geometri bölünür
1. Shader'ı kopyala, kopyada `emissiveMultiplier` = 0 (ölü panel)
2. `Geometry`'yi vertex konumuna göre böl, indeksleri **her geometride
   0'dan** yeniden numaralandır
3. Ölü panelleri yeni shader'a, canlıyı eskisine bağla

Vertex/indeks biçimi (CodeWalker XML, `Layout type="GTAV1"`):
```
Position(3)  Normal(3)  Colour0(4)  TexCoord0(2)
indeksler: 0 1 2  2 3 0   (quad basina)
```

### Emissive geometri TİTREYEMEZ
Flicker bir **ışık** özelliğidir. Panelin kendi parıltısı sabit kalır;
panelin altına Flashiness'li bir ışık koyarsan **odaya vuran ışık** titrer
ve panel titriyormuş gibi okunur.

---

## 7. SATIN ALINAN MODEL PAKETLERİ

- **`.mtl` çoğu zaman zip'e konmaz.** Dört pakette de yoktu → hiçbir OBJ'de
  materyal ataması yok, dokular elle eşleştirilir.
- **Ölçek paket İÇİNDE bile tutarsız.** Ölçüm: aynı 675-vertexlik parça bir
  gövdede **1.07 m**, başkasında **0.15 m**. Tek çarpanla ölçeklemek yanlış.
- **Bir `.obj` = bir sahne dökümü.** Tek dosyada onlarca ceset olabilir
  (biri 196 bağlı bileşen).
- **⛔ SERPİNTİ KÜMELEMEYİ ZİNCİRLER.** `model_12`'nin 608 bileşeninin
  yalnız **4'ü** gerçek parça, kalanı et kırıntısı; hepsi kümelemeye
  sokulunca kırıntılar gövdeler arasında köprü kurdu ve **608 bileşen tek
  kümeye düştü** — hiçbir şey ayrılmadı, hata da vermedi.
  → Önce yalnız büyük parçaları kümele, kırıntıları sonra en yakın kümeye ata.
- **UV'siz parça dokulanamaz.** Bir pakette 4 model UV'siz çıktı.

---

## 8. VOID TOOLS (seto3d) — ÖĞRENİLENLER

Kurulum: extension zip, `seto.*` operatör ad alanı, `Void Tools` N-panel sekmesi.
Güvenlik taraması: 155 dosya / 36.930 satır, `eval`/`exec`/`subprocess` yok;
ağ erişimi yalnız kendi GitHub sürüm kontrolü.

### Mimari ders — en değerlisi
Zor problemi **çözmek yerine ortadan kaldırmış**:
- *Decal Tool* → yüzeyin normal+tangent'ından baz kurup **tek quad**. Projeksiyon
  yok, kopyalama yok → hiç kırılmıyor (ama düz).
- *Surface Painter* → yüzeyin **kopyasını** çıkarıp alfasını **elle boyatıyor**.
  Projeksiyon problemi hiç doğmuyor → silindirde ve merdivende çalışır.
- *Edge Dirt / Wear / AO* → kenardan şerit.

### Aktarılabilir teknikler
- **`decal.sps`, `Color 1`'in ALFASINI harman katsayısı olarak okur** (Sollumz'un
  kendi node bağlantısı). Alfa boyamak = görünürlük boyamak.
- **Normal ters-transpoze matristen, tangent düz lineer kısımdan geçer.**
  Karıştırırsan üniform ölçekte fark görünmez, üniform olmayan ölçekte
  her decal sessizce yüzeyden eğilir.
- **Kendi projeksiyon UV'sini kurar, duvarınkini miras almaz** — duvarın
  unwrap'i 0-1'de üst üste binen adalardan oluşabilir, decal ada başına bir
  kez çizilir. (Bizim §2b hatamızın doğru kurulmuş hâli.)
- **Kayıpsız düzenleme:** UV'nin bozulmamış kopyası + strokelar tam güçte ayrı
  tutulur, böylece slider'lar veri kaybettirmez.
- **Export'a yalnız GTA'nın okuduğu veri gider:** `Color 1` + `UVMap 0`.

### Vertex Color Bake oda kabuğu için YANLIŞ ARAÇ
Vertex color'ın çözünürlüğü **mesh'in vertex yoğunluğudur**. Az poligonlu oda
kabuğunda AO leke leke çıkıyor. Yoğun mesh'li **prop'lar** için doğru.
Ayrıca **mesh'e YAZAN tek araçtır**; vanilla `Color 1` dolu olabilir
(ölçüm: `bsnt_shell` B kanalı 1.000) ve üzerine yazar.
⛔ `.npy` yedeği bu oturumda **işe yaramadı**; kurtarma kaynak `.ydr`'yi
yeniden içe alıp `Color 1`'i kopyalamakla oldu. → Bu araçtan önce
**`.blend`'i tarihli kopyala.**

### Shadow Map Baker
GTA iç mekânlarının kendi tekniği: ışığı dokuya bake edip `decal_dirt` decal
olarak geri koyar. Çözünürlük vertex'ten bağımsız → oda için **doğru araç**.
Ölçüm: AO 2048²/128 örnek, 2.4 sn. Oda ortalama parlaklığı
`62.98 → 59.24` (post-process çökmüşken), yamadan sonra **57.97** (%7.96).

---

## 9. ARAÇ HATALARI — DÜZELTİLDİ

### `light_sahne.oku` iskeletsiz drawable'da çöküyordu
`bones is None` durumunda `return [], {}` dönüyordu ama çağıranlar
`kmap["tag"]` / `kmap["idx"]` bekliyor → `KeyError: 'idx'`, ve hata
*"IC HATA"* diye çıkıp sebebini gizliyordu. **Statik prop'ların çoğunda
iskelet yoktur** — yani ışık düzenleme o dosyalarda hiç çalışmıyordu.
→ `return [], {"tag": {}, "idx": {}}`

### Void Tools Shadow Map, Blender 5.x'te post-process yapamıyordu
Üç ayrı API kırılması (bkz. §3e), hepsi tek `try/except`'e düşüp tek satır
uyarıyla yutuluyordu; kullanıcı **ham bake** alıyordu.
→ `_make_compositor_tree`, `_link_compositor_output`, `_set_node_option`
yardımcıları eklendi; 4.x ve 5.x'te birden çalışır.

---

## 10. DOĞRULAMA ALIŞKANLIKLARI (bu oturumda kendini kanıtlayanlar)

- **Her yazmadan sonra geri oku.** ytyp derlendikten sonra geri okunup
  `timecycleName` hash'i `joaat()` ile karşılaştırıldı — eşleşti.
- **Dağıtımdan sonra md5 karşılaştır.** "Komut hata vermedi" dağıtım kanıtı
  değildir.
- **Ekran görüntüsü ölçüm değildir** — ama tersi de doğru: **sayı da tek
  başına yeterli değil.** Bu oturumda "UV tam gözün içinde" ölçümü doğruydu
  ve decal yine görünmüyordu (katman adı yanlıştı). İkisi birden gerekli.
- **Kullanıcı "olmadı" dediğinde önce ÖLÇ, savunma yapma.** Bu oturumdaki
  her "olmadı" gerçek bir hataya karşılık geldi.
