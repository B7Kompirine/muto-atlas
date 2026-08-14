# Oyuna girmeden asset doğrulama — CodeWalker merdiveni

**Amaç:** her küçük değişiklik için sunucuya bağlanmayı bırakmak. FiveM
stream dosyalarını cache'lediği için asset testi **tam çıkış + yeniden
bağlanma** gerektiriyor (restart yetmez) — yani en ucuz oyun-içi tur bile
dakikalar sürüyor. Aşağıdaki merdivenin üst basamakları saniyeler sürüyor.

**Kural: bir basamakta yakalanabilecek hatayı alt basamağa taşıma.**
Oyun en son çare; oraya yalnızca üstteki üç basamağın *yapısal olarak*
göremeyeceği şeyler için inilir.

---

## Basamak 0 — Üretim aracının kendi denetimi (saniyeler)

Blender/Sollumz tarafında, export'tan **önce**. Ölçüm yapılır, göze
bakılmaz. Bir kez atlanıp saatler kaybedilen somut örnekler:

- Ağırlıksız vertex sayısı, etki sayısı (>4), ağırlık toplamı (=1.0).
  bmesh'te `index_update()` çağrılmazsa `vert.index` **−1**'dir ve
  ağırlıklar hiçbir vertex'e yazılmaz; export sessizce ağırlıksız mesh üretir.
- Deform sonrası ölçüm: `evaluated_get(depsgraph)` ile gerçek dünya
  koordinatları. Poz verip "oldu" demek yetmez.
- **Ölçümü tek eksende yapma ve `max()` ile vertex seçme.** Ölçülen vaka:
  üç halkanın yarıçapı eşit olduğu için `max(x)` alt halkadan vertex seçti,
  o halka eğilmediği için çalışan bir rig "eğim 0" diye raporlandı. Ölçümü
  ilgilendiğin **alt kümeye sabitle** (indeks aralığı), tüm mesh'e değil.

## Basamak 1 — Derlenmiş dosyayı geri oku (saniyeler)

**Araçlar: `assetdb.py doctor` ve `assetdb.py diff`** — ikisi de binary'yi
`res_to_xml.ps1` ile XML'e döküp okur, elle yapmana gerek yok.

```bash
assetdb.py doctor stream/ -r          # sessiz hataları tara
assetdb.py diff seninki.yft vanilla.yft
```

`doctor` bilinen sessiz hata kalıplarını arar: `.ycd`'de boş `<Hash>`
(klibin adı yoktur, `TaskPlayAnim` bulamaz), çözülmeyen `AnimationHash`,
0 kemik kanallı animasyon, MLO entity'sinde ymap bayrağı, odaya/portala
atanmamış entity, dejenere sınır kutusu, `TimeFlags`'i saatsiz ışık.
Denetlenemeyen dosya **asla temiz sayılmaz** — ayrı bölümde bildirilir ve
çıkış kodu 2 olur.

`diff` alan değerlerini değil **hangi düğümlerin hiç olmadığını**
karşılaştırır ve farkın *başladığı* sınırı raporlar (bir alt ağaç komple
eksikse her torununu ayrı satır yapmaz).

**Ped `.yft` çökmesi hakkında düzeltme (ölçüldü):** bu basamakta
`ArticulatedBody` düğümünü ARAMA — CodeWalker'ın XML yazıcısı o dizeyi
hiç üretmez, vanilla `mp_m_freemode_01.yft`'in XML'inde de geçmez, yani
"eksik" görünmesi anlamsızdır. Ölçülen gerçek işaret şudur: **vanilla ped
`.yft`'inde `<Physics>` düğümü hiç yoktur.** Yani `diff` çıktısında
`Physics` "SENDE VAR, VANILLA'DA YOK" tarafında görünüyorsa onu çıkar;
aranacak şey eksik bir alt düğüm değil, fazladan bir üst düğümdür.

Bu basamakta yakalananlar: shader adı/bucket, kemik tag'leri ve
hiyerarşi, geometri sayısı, `<Hash>` dolu mu, klip sayısı (çok klipli
sözlükte kliplerin birbirini ezmesi burada görünür).

## Basamak 2 — CodeWalker.Core ile headless değerlendirme (saniyeler)

**Araç: `scripts/cw_anim_check.ps1`**

CodeWalker bir GUI uygulaması ama `CodeWalker.Core.dll` bir kütüphanedir;
Model Viewer'ın animasyon değerlendirme kodu doğrudan çağrılabilir. Yani
klibin *hangi kemiğe, hangi fazda, hangi değeri yazdığı* oyuna girmeden
sayıyla okunur.

```powershell
# dizi parametresi -Command ile gecilmeli; -File ile TEK STRING olur
powershell -Command "& cw_anim_check.ps1 -Ycd <x.ycd> -Clip level -Tags @(63316)"
```

Kullanılan API:
`RpfFile.GetResourceFile<YcdFile>(byte[])` → `ycd.ClipMapEntries` →
`ClipAnimation.Animation` → `FindBoneIndex(tag, track)` →
`GetFramePosition(t)` → `EvaluateVector4/EvaluateQuaternion`.

Bu basamakta yakalananlar: faz→değer eğrisi doğrusal mı, genlik doğru mu,
kanal gerçekten yazılmış mı, **klibin ölü kuyruğu var mı**. Ölçülen vaka:
3 sn'lik bir çalkalanma klibinin hareketi faz 0.55'te bitiyordu — son
**1.35 saniye tamamen ölüydü** ve Lua o boşluğu bekliyordu. Oyunda gözle
fark edilmesi çok zor; sayıyla bir bakışta çıktı.

### Ardışık klipler: BİRLEŞME NOKTASINI ölç

Klipler **mutlak** kemik dönüşümü yazar, delta değil. Arka arkaya oynatılan
iki klip birleşme noktasında **her kanalda** eşleşmezse motor tek karede
sıçratır. Bu iki kez yaşandı, ikisi de kullanıcı tarafından fark edildi:

- **Seviye uyuşmazlığı:** dolum klibi %100'e çıkıyordu, çalkalanma klibi
  %72'ye gömülüydü → sıvı tepeden ortaya *zıpladı*. Aynı tutarsızlık Lua'da
  da vardı (`Settle()` çağrısı bardağı 0.72'ye çekiyordu).
- **Eğim uyuşmazlığı:** dolum **0.00°** ile düz bitiyordu, çalkalanma
  **9.00°** ile başlıyordu → tek karede 9 derece, gözle *"frame skip"*
  gibi görünüyor.

Kural: **her klip düz/nötr başlar ve düz/nötr biter**; genlik sıfırdan
yükseltilir (`min(1, z/0.12)`) ve sona doğru sıfıra indirilir
(`min(1, (1-t)/0.12)`). Ortak durum (dolum hedefi gibi) **tek bir sabitten**
gelir; klip üreticisi, önizleme render'ı ve Lua üçü de aynı sabiti okur.

Denetimi `cw_anim_check.ps1` ile yap: A klibinin son fazları ile B klibinin
ilk fazlarını yan yana bas, hem `pos` hem `aci` sütunu sürekli olmalı.

**Üçüncü uyuşmazlık: HAREKETİN FİZİĞİ.** Konum ve açı birleşme noktasında
tutsa bile, iki klip aynı hareketi farklı sabitlerle üretiyorsa göz bunu
*hız değişimi* olarak okur. Yaşandı: dolum kuyruğu `exp(-2.6·z)` ile
sönüyordu, çalkalanma `exp(-2.0·z)` ile; tepe genlikler 5.5° ve 9.0° idi.
Kullanıcının tarifi: *"dalgalanma sönerken bir anda darbe alıp
hızlanıyormuş gibi"*. **Algılanan hız genliğe bağlıdır** — büyük genlikte
yüzeyin tepe noktası daha geniş yol süpürür ve daha hızlı görünür, yani
farklı genlik = farklı hız demektir.

Kural: salınım frekansı, tepe genliği ve sönüm katsayısı **tek yerde
tanımlanır**, bütün klipler oradan okur. Denetim: iki klibi *sönüm
başlangıcına göre hizalayıp* aynı geçen sürelerde ölç — sayılar
örtüşmeli (ölçülen: 0.3 s → 3.72°/3.72°, 0.8 s → 1.94°/1.95°,
1.3 s → 1.01°/1.02°).

**Ayrıca: ayrı olayları önizlemede arka arkaya ekleme.** `settle` bir
*darbe* klibidir; dolumun hemen ardına eklenirse dalgalanma sönüp yeniden
büyür ve kullanıcı bunu hata sanır. Önizlemede olayları ayrı göster.

### Önizleme videosu asset'ten SAPMAMALI

Önizleme render'ı ile gerçek klip ayrı ayrı yazılırsa birbirinden sapar ve
kullanıcıya var olmayan bir davranış gösterilir (ya da gerçek bir hata
gizlenir). Kare fonksiyonlarını **tek bir modüle** koy; hem klip üreticisi
hem render oradan okusun.

### CodeWalker.Core tuzakları (üçü de yaşandı)

- **`ClipBase.Name` OKUMA** → StackOverflow. Süreç exit 253 ile ölür,
  hata mesajı bile çıkmaz. Klip adı `ClipMapEntry.Hash`'tedir.
- **`Add-Type`'a `netstandard` referansı ekle.** Yoksa generic çağrıda
  "The type 'System.Object' is defined in an assembly that is not
  referenced" der.
- **`Animation.BoneIds` dizi değil**, `ResourceSimpleList64_s<>` →
  `.data_items`. `.Length` doğrudan çalışmaz.
- StackOverflow buffer'ı boşaltmaz: adım adım teşhis gerekiyorsa her adımı
  **diske** yaz (`File.AppendAllText`), stdout'a değil.

## Basamak 3 — Görsel önizleme (yarım dakika)

Sayı "doğru" der ama **kullanıcı göremez**. Headless denetim, insanın
gözle onaylaması gereken şeyin yerine geçmez.

En pratik yol: Blender'da poz kütüphanesini kare kare çalıştırıp PNG
dizisi render etmek, `ffmpeg` ile mp4/gif'e çevirmek ve kullanıcıya
**dosya olarak göndermek**. Kullanıcıya "şu klasöre bak" deme, dosyayı ilet.

```powershell
ffmpeg -y -framerate 30 -i "f%04d.png" -c:v libx264 -pix_fmt yuv420p out.mp4
```

Blender önizleme tuzakları:
- **Sollumz export materyalleri EEVEE'de siyah render olur.** Önizleme
  için geçici `Principled BSDF` materyali ver, sonra geri al.
- **Opak cam sıvıyı tamamen gizler.** Saydamlık için `Transmission`
  kullanma (EEVEE arkasındakini göstermez) — `Alpha` + Blender 4.2+'ta
  `material.surface_render_method = 'BLENDED'` kullan.
- Blender 5.x'te render motoru `'BLENDER_EEVEE'` (`_NEXT` eki yok).

## Basamak 4 — CodeWalker GUI (dakikalar, elle)

`ModelForm` gerçekten model üzerinde klip oynatabiliyor:
`ClipDictComboBox` + `ClipComboBox` + `LoadClipDict()` + `SelectClip()` +
`InitAnimation()`. Sarı halka/renkli ok gizmoları `SetWidgetMode` /
`SetWidgetTransform`.

**Sınır:** `LoadClipDict(string)` sözlüğü **ada göre yüklü oyun
verisinden** çözer. Bir FiveM resource klasöründeki serbest `.ycd` açılır
listede çıkmaz; CodeWalker'ın taradığı bir konumda olması gerekir.
`ModelForm`'un kendi "Aç" diyaloğu da yoktur — RPF Explorer'dan açılır.

**Otomasyon notu:** CodeWalker taşınabilir bir `.exe` ise computer-use
`request_access` onu bulamaz (Start menüsü indeksine bakar; sonradan
kısayol oluşturmak da anında işe yaramadı). Yani GUI'yi ajan sürükleyemez;
bu basamak kullanıcının kendi eliyle yaptığı basamaktır. Ajan buraya
**adım adım tarif** verir, sürücü olmaya çalışmaz.

## Basamak 5 — Oyun (dakikalar, en pahalı)

Yalnızca üstte **yapısal olarak** görülemeyenler için:

- Script'e bağlı her şey: `PlayEntityAnim`, `SetEntityAnimCurrentTime` ile
  faz tarama, kapı sistemi, export/event akışı
- Fizik: ragdoll, fragment kırılması, çarpışma tepkisi, `specialAttribute`
  davranışı
- Gerçek RAGE görünümü — CodeWalker kendi DX11 renderer'ı, Blender ise
  büsbütün başka; `glass_env`/`emissive` hiçbirinde birebir görünmez
- Streaming/cache, resource yükleme sırası, `DLC_ITYP_REQUEST` ile ytyp
  kaydı, MLO oda/portal elemesi
- Performans (resmon)

**Oyuna girmeden önce kullanıcıya hatırlat: sunucudan tamamen ÇIKIP
yeniden bağlanmak gerekiyor, restart yetmez** — yoksa bayat asset test
edilir ve yanlış sonuç çıkar.

---

## Özet karar tablosu

| Ne doğrulanacak | En üst yeterli basamak |
|---|---|
| ağırlık, deform, pivot, ölçü | 0 (Blender ölçümü) |
| shader/bucket, kemik tag, hiyerarşi, `<Hash>`, klip sayısı | 1 (`doctor` / `diff`) |
| ışığın saati, konisi, menzili; iç mekân neden karanlık | 1 (`light` / `timecycle --mlo`) |
| klip eğrisi, faz→değer, genlik, ölü kuyruk | 2 (`cw_anim_check.ps1`) |
| "gözle doğru duruyor mu" | 3 (render + kullanıcıya gönder) |
| vanilla asset'i incelemek, dünya yerleşimi, MLO düzeni | 4 (CodeWalker GUI, elle) |
| script, fizik, gerçek görünüm, streaming, performans | 5 (oyun) |
