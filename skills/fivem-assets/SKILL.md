---
name: fivem-assets
description: GTA V / FiveM asset verisi ve ölçülmüş üretim kuralları — prop, obje, kapı, ytyp/ymap/MLO, LOD, çim, bayraklar, partikül (.ypt), shader/doku/ışık/timecycle/decal/parallax, kıyafet, araç; vanilla animasyon adı ve kemik tag sorgusu. Prop, kapı, harita, efekt ya da görünüm işinde KOD YAZMADAN ÖNCE gerçek veriye bakmak için kullan, kullanıcı istemese bile. Tetikleyiciler — model adı (prop_*, v_ilev_*, des_*), kapı açılmıyor, obje kımıldamıyor, AddDoorToSystem, TaskPlayAnim, anim dict, bone tag, specialAttribute, bayrak sayısı (1572872), LOD, uzakta kayboluyor, fxName, StartParticleFx, ışık yanmıyor, TimeFlags, karanlık iç mekân, timecycle, decal, parallax, DUI ekran, fragment, RayFire yıkım, freemode kıyafet, handling, modkit, Sollumz, CodeWalker. Use for GTA V / FiveM props, doors, maps, particles, materials, lights and clothing.
license: MIT
compatibility: Python 3.10+. Windows PowerShell 5.1 runs the .ps1 build scripts. Data layers are built from your own GTA V install with CodeWalker.Core (scripts/setup.py). The scripts live at the muto-atlas repository root, outside this folder - outside Claude Code install with scripts/install_skills.py or use scripts/mcp_server.py.
---

# FiveM Asset Verisi — gövde

Bu dosya **gövde**dir: her dalda geçerli olan kurallar ve ağacın haritası.
Ayrıntı dal ve yaprak dosyalarındadır; buradan yalnız **yönlendirilir**.
Bir bilgi bir kez yazılır, geçerli olduğu en geniş yere.

## AĞAÇ — gövde / dal / yaprak

- **Gövde** — bu dosya + `trunk/`: **GTA V'in kendi kuralları** (veri modeli, dosya
  tipleri, hash, koordinat, **doku/DDS**, streaming, kaynak formatı, istemci/sunucu),
  bizim çalışma disiplinimiz, araç tuzakları, doğrulama merdiveni, bayraklar, kemik tag'i.
  **Ölçüt:** bir madde her dalda ve her yaprakta geçerli değilse gövdeye girmez.
- **Dal** — `branches/<branch>/_branch.md`: o kategorinin geniş kuralları + yaprak listesi.
- **Yaprak** — `branches/<branch>/<leaf>.md`: yalnız o göreve özgü olan.
  Yaprak *istenen şeyle* tanımlanır; "yol yıkımı / köprü yıkımı / patlama" tek yapraktır.

**Kullanım:** konu geçince önce dalı aç (`_branch.md`), sonra tek yaprağı.
Bütün dosyaları tarama; keyword → dal → yaprak.

| dal | komut | dosya | anahtar kelimeler |
|---|---|---|---|
| Harita | `/map` | `branches/map/_branch.md` | ymap, ytyp, MLO, vanilla parça, yıkım, RayFire, LOD, extent, çim |
| Prop | `/prop` | `branches/prop/_branch.md` | prop, kapı, kımıldamıyor, fragment, ham paket, DUI, NUI HUD, ox_target |
| Kıyafet | `/clothing` | `branches/clothing/_branch.md` | giysi, freemode component, skintone, ped prop, şapka |
| Partikül | `/particle` | `branches/particle/_branch.md` | ptfx, .ypt, efekt, duman, flipbook, emitter, katalog |
| Görünüm | `/look` | `branches/look/_branch.md` | shader, doku, parallax, ışık, TimeFlags, decal, timecycle, emissive, bake |
| Araç | `/vehicle` | `branches/vehicle/_branch.md` | araç kemiği, handling, modkit, siren |

Tam anahtar kelime listesi her `_branch.md`'nin başında.

### ⛔ Yönlendirme KELİMEYLE değil SINIFLA yapılır

Anahtar kelimeler **hızlandırıcıdır, sözlük değildir.** Kelime kümesi sonsuz
(*kepenk · tabela · çeşme*), sınıf kümesi kapalı: **6 dal.**

1. Kelime tutuyorsa → dal belli, aç.
2. Tutmuyorsa **dur değil**: `branches/<branch>/_branch.md` başındaki
   **`Bu dala ne düşer:`** tanımına bak, cümleyi **sınıflandır**.
   *"Kepenk açılsın"* → kepenk bir kapı nesnesidir → `/prop`.
3. Listeye kelime eklemek **istisnadır**: yalnız sık geçen ve tanımdan da
   anlaşılmayan terim için. Her kelimeyi ekleme — liste şişer.

Sınıf tanımından da çıkmıyorsa → **sor.**

## GÖVDE DOSYALARI

| dosya | ne zaman |
|---|---|
| `trunk/gta-fundamentals.md` | **motorun kendi sözleşmesi** — archetype/entity/drawable ayrımı, dosya tipleri, joaat, koordinat/birim, **doku ve DDS kuralları**, streaming, RSC7, istemci/sunucu, render kovası |
| `trunk/tool-pitfalls.md` | Sollumz · Blender · CodeWalker · PowerShell · Python/Lua · FiveM çalışma zamanı — bir araç beklenmedik davranınca **önce buraya** |
| `trunk/verification-ladder.md` | bir asset'i oyuna sokmadan doğrulama: Blender ölç → geri oku → CodeWalker headless → render → GUI → oyun |
| `trunk/flags.md` | ytyp/ymap/collision bayrakları, `specialAttribute` 21 değer, 14 extension tipi, nametable |
| `trunk/bone-tags.md` | araç / silah / ped kemiklerinde **ad mı sabit, tag mi sabit** |
| `sources/external-tools.md` | *(kural değil, kaynak notu)* dış araçların ölçülebilen kısmı; [doğrulandı]/[çürütüldü] etiketleri; alet envanteri |
| `sources/community-resources.md` | *(kural degil, kaynak notu)* Sollumz Discord `#resources` tam dokumu — hazir sablon/rig/arac indeksi, `bloodfx.dat` alanlari |

## ⛔ VERİ EKSİKSE TAHMİN ETME

Her cevap `data/` katmanlarına dayanır. Katman yoksa sorgu **exit 2** döner;
o noktada yapılacak tek şey **durmak**:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --plan   # durumu gösterir, yazmaz
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py"          # eksik katmanları kurar (/asset-setup)
```

Çıkış kodları: `0` bulundu · `1` sorgu çalıştı, **ad otoritede yok** · `2` **katman
kurulu değil** — sonuç hakkında hiçbir şey denemez · `3` iç hata, "yok" değil.
`2` ile `1`'i karıştırmak, eksik katmandan çıkan "0 sonuç"u "oyunda yok" diye
okumaktır.

## TEMEL KURAL — önce veri, sonra kod

Bir obje/prop/kapı/animasyon hakkında kod yazmadan önce o asset'in verisine
bakılır. Gerçek vaka: Fleeca vezne kapısı `v_ilev_gb_teldr` için dört native
sırayla denendi; cevap ytyp'nin tek satırındaydı — `specialAttribute = 0`,
yani kapı değil. `assetdb.py door v_ilev_gb_teldr` bunu baştan söylerdi.

## ÇALIŞMA DİSİPLİNİ — her dalda, her araçta

1. **Ölçüm > tahmin.** Bir sayı (tag, bayrak, süre, lodDist, `fxName`) tahmin
   edilmez, sorgulanır. Dış araçtan gelen sayı **iddiadır**, `[doğrulandı]`
   etiketi yoksa önce ölç (`sources/external-tools.md`).
2. **Aracın göstermemesi, o şeyin yok olduğu anlamına gelmez.** CodeWalker
   `.yed` bytecode'unu yazamaz, PowerShell olmayan property'de `$null.Length=0`
   döner, Sollumz binary'yi "0.0 saniyede" içe alır — üçü de "yok" sanıldı.
3. **Aracın hata vermemesi, işin doğru olduğu anlamına gelmez.** Bu depodaki
   hataların neredeyse hepsi sessizdir: dosya oluşur, "success" yazar, oyunda
   hiçbir şey olmaz. Hepsi `trunk/tool-pitfalls.md`'de.
4. **Ekran görüntüsü ölçüm değildir.** Bir şeyin bozuk olduğunu söylemeden önce
   oku: pikseli, dosyayı, geri okumayı. (Bir turda üç kez görüntüye bakıp yanlış
   teşhis kondu.)
5. **"Obje oluştu, sayılar makul" çalışıyor demek değildir.** Sayı ve ekran
   ikisi birden gerekli; tek sentetik noktada çalışması yetmez, düzeltme
   **kullanıcının gerçek durumunda** denenmeden teslim edilmez.
6. **Yazdığını geri oku.** Dosya boyutu geçerlilik ölçütü değildir (RSC7 zlib);
   tek ölçüt geri okumadır. Betik ortada çökerse sonraki `Write` çalışmaz —
   "yazıldı" demeden `cat`/`grep`. Kopyadan sonra boyut/hash karşılaştır.
7. **İşlem sırası ölçümün parçasıdır.** Tek sayıya değil, **iki bağımsız
   sayının birbirini tutmasına** bak (`ulaşılan` vs `hedef`). Bir sayı doğruyken
   *ne zaman* ölçüldüğü yanlış olabilir.
8. **Referansın kendisi bozuk olabilir.** İki bağımsız çözücü aynı yanlışı
   paylaşabilir; vanilla'yla karşılaştırmadan "ölçtüm" deme.
9. **Bir seferde tek değişken.** Bir şey çalışmıyorsa zinciri parçalara ayır,
   A/B kur; zincir bitmeden test isteme; belirtiden hipoteze atlayıp tek tek deneme.
10. **Izgara yanlış soruyu sorabilir** — "100/100 nokta dolu" demek örneklenmeyen
    yerin var olmadığı anlamına gelmez. Ölçüm doğru, soru yanlış olabilir.
11. **Bir aracın sabiti kendi ölçeğine ayarlıdır** — sabiti değil, neye göre
    normalize edildiğini kopyala (gölge bias'ı 0.15 m prop için doğru, 660 m
    sahnede zeminin %72'sini gölgeledi).
12. **Bir alanın anlamını dağılımdan tahmin etmeden önce aracın o alanı nasıl
    adlandırdığına bak** (`bl_rna.properties[...].enum_items`). `Flashiness`
    için üç tahmin de yanlıştı; Sollumz isimli enum veriyordu.
13. **`Unknown*` alanına 0 yazma** — dağılımına bak, en sık değeri al.
14. **Reçete seç, sonuna kadar uygula; iki reçeteyi MELEZLEME.** Her ikisi de
    tek başına doğru olan iki yolun melezi hiç çalışmadı. Tarif belirsizse
    `AskUserQuestion` ile netleştir.

## MOTOR DEĞİŞMEZLERİ — dal fark etmez

- **Asset değişti → sunucudan çık, yeniden bağlan.** Stream cache'lenir, restart
  yetmez; atlanırsa bayat asset test edilir. Test istemeden önce hatırlat.
- **Bozuk stream varlığı kaynağın tamamını sessizce düşürür** — istemcide
  hiçbir komut kaydolmaz, hata yok. Komutlar birden yok olduysa Lua'ya değil
  `stream/`e bak. Kaynak **iki klasördeyse** biri yok sayılır → sunucu logu.
- **Sihirli sayı kopyalanmaz, çözülür:** `assetdb.py flags <sayı> [--entity]`.
  `1572872` = LOD in Parented YMAP + Cast Static/Dynamic → ymap için; `18350080`
  = Dont Render In Reflections + iki gölge biti → MLO entity için. Karıştırmak
  objeyi sessizce yok eder. → `trunk/flags.md`
- **Kemik: ad mı sabit, tag mi?** Script tarafı (`GetEntityBoneIndexByName`)
  **adı**, dosya tarafı (`.ycd`/`.yed`/`specialAttribute`) **tag'i** kullanır.
  `GetPedBoneIndex` TAG alır. → `trunk/bone-tags.md`
- **bbox animasyonun tamamını kapsamalı — iki ayrı yerde:** `.ydr`'nin kendi
  `BoundingBox`/`Sphere`'i **ve** ytyp arketip kutusu. Biri düzeltilince öbürü
  rest kalırsa obje uzakta titrer ve kaybolur.
- **`physicsDictionary` asla 0** — model görünür, içinden geçilir.
- **Script'le spawn edilen obje harita objesi değildir**; MLO içine ymap ile
  prop konmaz; harita objesinde `SetEntityCollision(false)` güvenilmez.
- **`CreateObject` collision-bound TABANINA, `CreateObjectNoOffset` ORİGİN'e koyar** — bayat bound objeyi havaya kaldırır,
  bound görselden yeniden üretilir. Takılı obje **origin**'inden konumlandırılır; prop'a kemik eklemek hizalama vermez,
  hizalama modele pişirilir.
- **Collision script'le kovalanmaz** — `SetEntityCollision` / `Freeze` /
  `SetEntityHeading` / `DoorSystemSetOpenRatio` animasyon zincirini bozar.
- **Custom ped iskeleti yasak**; motor yalnız kendi iskeletini kabul eder.
- **DUI/NUI istemci tarafıdır** — şifre/kod/fiyat karşılaştırması sunucuda.
- **Doku: DDS zorunlu, her iki kenar ikinin kuvveti, DXT + mip zinciri.** PNG sessizce
  atlanır, ikinin kuvveti olmayan doku titrer, DXT1 alfa taşımaz (delikler kapanır).
  → `trunk/gta-fundamentals.md` §5
- **Archetype (ne) ≠ entity (nerede) ≠ drawable (nasıl görünür)** — üçü ayrı dosyada;
  ytyp'yi düzeltmek o modeli kullanan **her yeri** etkiler. → `trunk/gta-fundamentals.md` §1
- **Klip adı = prop model adı** (eşya animasyonu tespiti). Süre tahmin edilmez,
  indeksten alınır.

## SORGU TABLOSU — kullanıcı komut vermez, sen bakarsın

Konu geçtiği anda, kod yazmadan önce:

| konu | çalıştır |
|---|---|
| prop / obje / kapı adı · "kapı açılmıyor" | `assetdb.py show <ad>` · `door <ad>` |
| dünyada nerede · yakınımda ne var | `where <ad>` · `near x y z --radius 10` |
| animasyon / klip · prop animasyonu · hangi model oynatır | `anim <ara>` · `propanim <prop>` · `clipfit <dict> <clip>` |
| kemik / tag / iskelet | `bones <model>` |
| ped kimliği (klip sözlüğü, expression, clipset) | `pedmeta <ped>` |
| expression / `.yed` / yay-sarkma | `expr <ara>` · `ext <ad>` |
| partikül · "şu efekt var mı" · `fxName` | `ptfx <prop\|efekt>` · `fx <ad> --exact` · `ptfx --type 4` |
| bayrak sayısı · ytyp extension | `flags <sayı> [--entity]` · `ext <ad>` |
| LOD · "uzakta kayboluyor" · haritamda sorun var mı | `lod` · `lodchain <ad>` · `lodaudit` |
| çim / zemin / `Procedural ID` | `proc [<ad>\|--id N]` |
| collision materyali | `mat [<ad>\|--index N]` |
| decal script'le · gömülü decal shader · shader türü | `decal <tür>` · `shader decal` · `shader <tür>` |
| ışık · hava · oda timecycle | `light <ydr>` · `cycle w_clear --hour 20` · `timecycle <ad>` |
| silah · araç · MLO · IPL | `weapon <ad> --parcalar` · `vehicle <ad>` · `mlo <ad>` · `ipl <ad>` |
| loot/spawn noktası, ATM/CCTV konumu | `world --near x,y,z --mesafe 50` · `--family <aile>` |
| modelin ekranı var mı (`AddReplaceTexture`) | `screentex.ps1 -Model <ad> -All` |
| native adı / imzası / tarafı | `fivem-natives` skill'i (`/native`, `/native-lint`) |

Hepsi `python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" <alt komut>`. Sonucu
bir iki cümleyle özetle, sonra koda geç. İndeks vanilla RPF + sunucunun kendi
ytyp'lerinden üretilir; yeniden kurmak `/asset-build`.

## DOĞRULAMA MERDİVENİ — oyun en son çare

**Bir basamakta yakalanabilecek hatayı alt basamağa taşıma.**
Tam reçete `trunk/verification-ladder.md`.

| ne doğrulanacak | basamak |
|---|---|
| ağırlık, deform, pivot, ölçü | Blender'da **ölç** (`evaluated_get`) |
| shader/bucket, kemik tag, hiyerarşi, `<Hash>`, klip sayısı | `res_to_xml.ps1` + vanilla ile yapısal diff |
| "gözle doğru duruyor mu" | Blender render → kullanıcıya **dosya** gönder |
| vanilla asset, dünya yerleşimi, MLO düzeni | CodeWalker GUI (elle, kullanıcı sürer) |
| script, fizik, gerçek görünüm, streaming, resmon | **oyun** — partikül için tezgâh `scripts/ptfx_bench.py` |

## GÖRSEL GEREKTİĞİNDE — üretme, öner ve prompt ver

Ekran arka planı, ikon, logo, doku: **yer tutucu uydurma.** Fikri anlat (ne,
nerede, hangi mesafeden, ton) → kullanıcıya en-boy oranı ve çözünürlük içeren
**hazır prompt** ver → görsel gelene kadar düzeni kodla kur, doğru ölçüde boş
kutu bırak. Uydurulmuş görsel tona oturmaz, iki kez iş olur.

## NE ZAMAN YETMEZ

Fragment iç yapısı → `.yft` incelenir · animasyon süresi/eventleri → `.ycd` ·
sunucunun kendi MLO'larının iç yerleşimi → `/asset-build -ExtraFolders`
arketipleri getirir, iç entity genişletmesi vanilla ymap'lere bağlıdır.
Bu durumlarda tahmin yürütme; CodeWalker'da neye bakılacağını söyle ya da
oyun içi ölçüm iste.
