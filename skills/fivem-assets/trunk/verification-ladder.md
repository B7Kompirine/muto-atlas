# Oyuna girmeden asset doğrulama — CodeWalker merdiveni

**Gövde dosyası.** Bir asset'i oyuna sokmadan doğrulamanın merdiveni; her dal bunu kullanır. Taşındı: `trunk/verification-ladder.md` (2026-09-05).

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

## Basamak 2 — klip eğrisi değerlendirmesi

Bu basamağın aracı ve reçetesi public sürümde yok.

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

### NUI sayfası (HUD) önizlemesi

`vh/vw` → 1080p piksel yerine koyma + örnek mesaj enjekte + **headless Edge**
ekran görüntüsü (`--user-data-dir` şart, yoksa dosya yazılmaz). Browser
pane'in `file://` snapshot'ı ölçekte yanıltır.

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

## Tablonun kendisini doğrulama — `verify_tables.py`

Yukarıdaki basamaklar bir **asset'i** doğrular. Bu betik **tabloyu** doğrular:
`shaders.tsv` ve `collision_materials.tsv` ikisi de Sollumz kaynağından
çıkarıldı, yani **tek kaynak**. Betik karşısına ikinci kaynağı (oyunun kendi
dosyalarından üretilen kullanım verisi, `build_usage.ps1`) koyar ve üç soruyu
sorar: kullanımda görünüp tabloda **olmayan** shader var mı · kullanılan
collision materyal indeksleri tablo aralığında mı · decal shader'ları hangi
`RenderBucket` ile kullanılıyor (Sollumz varsayılanı `Opaque(0)`; doğrusunu
ancak ölçüm söyler).

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/verify_tables.py"
```

Bir tablodan aldığın sayı beklenmedik geldiyse **önce bunu çalıştır** —
asset'i değil tabloyu suçlamak gerekebilir.

## Özet karar tablosu

| Ne doğrulanacak | En üst yeterli basamak |
|---|---|
| ağırlık, deform, pivot, ölçü | 0 (Blender ölçümü) |
| shader/bucket, kemik tag, hiyerarşi, `<Hash>`, klip sayısı | 1 (`doctor` / `diff`) |
| ışığın saati, konisi, menzili; iç mekân neden karanlık | 1 (`light` / `timecycle --mlo`) |
| "gözle doğru duruyor mu" | 3 (render + kullanıcıya gönder) |
| vanilla asset'i incelemek, dünya yerleşimi, MLO düzeni | 4 (CodeWalker GUI, elle) |
| script, fizik, gerçek görünüm, streaming, performans | 5 (oyun) |
