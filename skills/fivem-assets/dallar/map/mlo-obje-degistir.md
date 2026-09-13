# MLO içindeki objeyi kendi modelimle değiştir (entity swap)

**Ne zaman okunur:** iç mekândaki kapı/obje yanlış tanımlı (`specialAttribute=0`), animasyon oynuyor ama çarpışma kalıyor, ya da modelin kendisi değişecek.
**When to read:** replacing an object that is already inside an MLO with your own model (entity swap).
**Kaynak:** `mlo-obje-degistirme.md` (tamamı) · eski SKILL 'HARİTADAKİ BİR OBJEYİ DÜZELTMEK' (2026-07/08) · **Ölçüm:** Fleeca vezne + kasa kapısı oyunda; elenen 4 yol oyunda çöktü
**Önce:** `dallar/map/_dal.md` · gövde › `govde/bayraklar.md`, `govde/arac-tuzaklari.md`

---


Fleeca vezne kapısı (`v_ilev_gb_teldr`) ve kasa kapısı (`v_ilev_gb_vauldr`)
bu yolla çalışır hale getirildi. Aşağıdaki her madde oyun içi ölçümle
doğrulandı; "muhtemelen" yok.

---

## 1. BU REÇETE NE ZAMAN KULLANILIR

Haritada duran bir obje istediğin gibi davranmıyorsa:

- kapı olması gerekiyor ama itilmiyor (`specialAttribute = 0`)
- animasyon oynuyor ama çarpışma yerinde kalıyor (drawable, fragment değil)
- modelin kendisi yanlış / eksik ve kendi modelini koymak istiyorsun

---

## 2. ÖNCE BUNU BELİRLE — HER ŞEY BUNA BAĞLI

**Obje MLO iç mekânında mı, dışında mı?**

Bu tek soru hangi yolun çalışacağını belirler ve atlanırsa günler kaybedilir.

| | MLO **dışı** (sokak, açık alan) | MLO **içi** (banka, ev, dükkân) |
|---|---|---|
| Kendi ymap'inle yerleştirme | ✅ çalışır | ❌ **oda/portal sistemi eler, obje hiç gelmez** |
| MLO entity listesini değiştirme | — | ✅ **tek çalışan yol** |

Başka bir resource'un ymap kullanıyor olması seni yanıltmasın. Önce onun
prop'unun koordinatına bak: MLO'nun dışındaysa senin durumuna uymuyordur.

---

## 3. ELENEN YOLLAR (tekrar deneme)

Hepsi denendi ve oyun içi ölçümle çöktü:

1. **`CreateObject` ile kendi kopyanı spawn edip vanilla'yı gizlemek**
   Script'le üretilen obje **harita objesi değildir**.
   - Kapı sistemi kapıyı model+konum ile *haritada* arar, bulamaz →
     geriye serbest bir fizik prop'u kalır → **kapıya dokununca zeminin
     içinden düştü.**
   - Fragment'in per-bone çarpışması animasyonu **takip etmedi**.
   - `FreezeEntityPosition` ile düşmeyi durdurursan bu sefer kapı sistemi
     itemez.

2. **Kendi ymap'inle yerleştirme (MLO içinde)**
   Entity elenir. Vanilla da gizlendiği için ortada **boşluk** kalır.

3. **Vanilla prop ytyp'sinde `specialAttribute` düzeltmek**
   (`int_lev_des.ytyp` → `v_ilev_gb_teldr` 0→7). Dosya kusursuz üretildi
   (348/348 archetype birebir) ama oyun içinde fizik yine yüklenmedi.

4. **Vanilla adıyla yeni bir ytyp eklemek**
   Oyun ilk tanımı zaten kaydetmiştir; çakışır.

---

## 4. ÇALIŞAN REÇETE — ADIM ADIM

### Adım 1 — Objeyi ve archetype'ını tanı

```
assetdb.py near <model_adi>
```

Not al: `specialAttribute`, `assetType`, `physicsDict`, `bbMin/bbMax`.
`bbMin.x` / `bbMax.x` kapı için kritik: **pivot menteşede olmalı**
(bbox ya `-W → 0` ya da `0 → +W` olmalı, menteşe X=0'da).

### Adım 2 — Modeli RPF'ten çıkar

```
extract_asset.ps1 -Names <model>.ydr -Out <klasör>
```

Script RSC7 başlığını geri ekler ve deflate uygular — bunlar olmadan
Sollumz "Unsupported file format" / "DECOMPRESS_FAILED" der.

### Adım 3 — Blender'da KENDİ ADIMIZLA yeniden kur

Sollumz ile import → adı `my_xxx` yap → export.

- **Normal kapı** istiyorsan: drawable yeterli. Pivotun menteşede
  olduğunu doğrula. Collision (BoundComposite) mesh'in içinde kalmalı.
- **Çarpışması animasyonu takip etsin** istiyorsan: FRAGMENT üret.
  Detay için SKILL.md → "COLLISION'IN ANIMASYONU TAKİP ETMESİ".
  Özet, iki kural:
  - Bound'u kemiğe bağlayan şey `COPY_TRANSFORMS` constraint'idir
    (`parent_bone` değil, isim eşleşmesi değil).
  - **En az iki grup gerekir.** `parentIdx=255` olan grup entity
    gövdesidir ve kemiği TAKİP ETMEZ. Hareket eden parça çocuk grupta
    olmalı:
    ```
    grup[0] kök kemik (tag 0)  parentIdx=255  -> SABİT menteşe
    grup[1] hareketli kemik    parentIdx=0    -> DÖNEN kanat
    ```
  - Kemik tag'lerini **değiştirme** — vanilla klibin oynaması buna bağlı.

### Adım 4 — Kendi archetype'ını üret

```
make_ytyp_override.ps1 -Models <vanilla> -RenameTo <bizim> `
  -SpecialAttribute <7|0> -AssetType <ASSET_TYPE_DRAWABLE|ASSET_TYPE_FRAGMENT> `
  -ClearDicts -PhysicsDictSelf -Flags <...> -LodDist <...> `
  -YtypName <bizim> -OutFile <...>\stream\<bizim>.ytyp
```

| | itilebilir kapı | animasyonlu fragment |
|---|---|---|
| `assetType` | `ASSET_TYPE_DRAWABLE` | `ASSET_TYPE_FRAGMENT` |
| `specialAttribute` | **7** (menteşeli) | **0** (animasyonu script oynatır) |

- **`physicsDictionary` ASLA 0 bırakılmaz** → `-PhysicsDictSelf`.
  0 verirsen model görünür ama **içinden geçilir**. Vanilla arşivinde tek
  bir kapı prop'unda bile 0 yoktur.
- `textureDictionary` 0 kalabilir (dokular dosyaya gömülüyse).

fxmanifest:
```lua
files { 'stream/<bizim>.ytyp' }
data_file 'DLC_ITYP_REQUEST' 'stream/<bizim>.ytyp'
```

### Adım 5 — Objeyi hangi MLO tutuyor, bul

Tüm ytyp'leri tarayıp `MloArchetype.entities` içinde model hash'ini ara.
Fleeca için sonuç:

```
v_int_10.ytyp            -> MLO v_genbank            (vezne + kasa)
hei_dlc_generic_bank.ytyp -> MLO hei_generic_bank_dlc (vezne)
```

Aynı obje birden fazla MLO'da olabilir — **hepsini** değiştir.

### Adım 6 — MLO entity listesinde adı değiştir

```
powershell -Command "& patch_vanilla_ytyp.ps1 -YtypName 'v_int_10.ytyp' `
  -SwapEntity @('v_ilev_gb_teldr=my_teldr','v_ilev_gb_vauldr=my_vauldr') `
  -OutDir '<...>\stream'"
```

- Bu dosyaya **`DLC_ITYP_REQUEST` EKLENMEZ** — vanilla dosya değişimidir.
  `stream/` içindekiler zaten otomatik streamlenir.
- Script yazdıktan sonra dosyayı geri okur; imza (`arch / mlo / rooms /
  portals / entities`) kaynakla aynı değilse veya eski model kalmışsa
  dosyayı **siler**. Bozuk ytyp streamlemek MLO'yu komple bozar.

Beklenen çıktı:
```
[*] imza  : arch=51 mlo=2 rooms=7 portals=7 entities=427
[+] MLO v_genbank: entity v_ilev_gb_teldr -> my_teldr
[*] yazilan imza: arch=51 mlo=2 rooms=7 portals=7 entities=427
    dogrulama: yeni model 2 entity'de, eski model 0 entity'de kaldi
```

### Adım 7 — Runtime

Artık vanilla obje **hiç yerleştirilmiyor**. `CreateModelHide`,
`RemoveModelHide`, spawn, ymap — hiçbiri gerekmez.

**İtilebilir kapı:**
```lua
AddDoorToSystem(h, model, x, y, z, false, false, false)
-- FİZİĞİN YÜKLENMESİNİ BEKLE, yoksa sonraki çağrı sessizce düşer
while not DoorSystemGetIsPhysicsLoaded(h) and GetGameTimer()-t < 3000 do Wait(50) end
DoorSystemSetDoorState(h, 0, true, true)   -- 0 = kilitsiz
```

**Animasyonlu fragment:**
```lua
PlayEntityAnim(obj, clip, dict, 1000.0, false, true, false, 0.0, 0)
-- DONDURMA. Kök grup gövdeyi taşıdığı için devrilmez.
```

### Adım 8 — STREAMING: durumu bir kere uygulamak YETMEZ

Oyuncu uzaklaşınca MLO boşalır; geri dönünce **entity yeniden yaratılır**.
O anda:

- kapı sistemi durumu **varsayılana (kilitli) döner**
- fragment'te oynayan animasyon **kaybolur**

Belirti: "kapı bir süre sonra kendi kendine geri kilitleniyor". İlk
sürümde `doorRegistered[hash] = true` diye önbellek tutup durumu bir daha
uygulamamıştım — hata tam buydu. **Önbellek tutma, durumu periyodik olarak
DOĞRULA:**

```lua
CreateThread(function()
  while true do
    local wait = 1500
    if nearest(DOOR) then
      -- kayit yoksa ekle (idempotent)
      if not IsDoorRegisteredWithSystem(h) then AddDoorToSystem(h, model, x,y,z, false,false,false) end
      -- fizik hazir degilse dokunma, sonraki turda tekrar bak
      if DoorSystemGetIsPhysicsLoaded(h) and DoorSystemGetDoorState(h) ~= 0 then
        DoorSystemSetDoorState(h, 0, true, true)
      end
      wait = 2000
    end
    Wait(wait)
  end
end)
```

Fragment tarafında: **entity handle'ını sakla**. Handle değiştiyse iç mekân
yeniden yüklenmiş demektir; istenen durumu geri uygula. Animasyonu
`delta = 1.0` ile (klibin sonundan) başlat, yoksa oyuncu her dönüşünde
kapının baştan açılmasını izler.

### Adım 9 — ESKİ MODEL ADINI ARAYAN HER YERİ GÜNCELLE

Model adını değiştirdiğin an, o adı arayan **tüm** kod ve config kırılır —
ama sessizce. Objeyi bulamaz, hiçbir hata vermez.

```
grep -rn "<eski_model>" --include=*.lua config/ data/ modules/ core/
```

Gerçek örnek: `config/heists/fleeca.lua` hâlâ `v_ilev_gb_teldr` arıyordu.
Sonuç: kapı modülü kapıyı tanıyamadı, kilit mantığı yanlış tarafa düştü ve
oyuncu 60 m'ye her girdiğinde kapı yeniden kilitlendi.

### Kilit/durum çakışması — tek otorite kuralı

Aynı objeye **iki modül** durum yazıyorsa son yazan kazanır ve davranış
rastgele görünür. Belirti: teşhis `durum=0` (kilitsiz) diyor ama kapı
açılmıyor.

Sebebi genelde şu: kilit sadece kapı sistemiyle değil, **entity
dondurularak** uygulanır —
`FreezeEntityPosition(obj, isLocked and not isOpen)`. Donmuş entity kapı
sisteminden etkilenmez, bu yüzden `DoorSystemGetDoorState` yanıltıcı olur.

Kural: **kilidi tek bir modül yönetsin.** Yeni modülün onunla yarışmasın;
onun config'ini yeni model adına yönlendir, yeter.

### "Düzelttim, şimdi hiç açılmıyor" — sahte regresyon

Config'i doğru model adına çevirdiğin an, o güne kadar **hiç çalışmamış**
olan kilit mantığı ilk kez devreye girer. Kapı kilitli gelir ve bu bozulma
gibi görünür — halbuki tasarım öyle (`Config.Doors.Types.teller.locked =
true`, kapı bir soygun hedefi).

Öncesinde kapı "çalışıyor" görünüyorduysa sebebi, kilit modülünün objeyi
hiç bulamamasıdır. Yani seçim: kilit hiç çalışmasın, ya da çalışsın ve kapı
kapalı dursun.

Fiziksel testi mümkün kılmak için **açık bir override komutu** koy —
sessizce sürekli ezen bir döngü değil:

```lua
-- Kilit IKI katmanli: kapi sistemi durumu + entity dondurma.
-- Sadece state 0 yazmak YETMEZ; donmus entity kimildamaz.
FreezeEntityPosition(door, false)
if DoorSystemGetDoorState(h) ~= 0 then DoorSystemSetDoorState(h, 0, true, true) end
```

Override açıkken kısa aralıkla (~0.5 sn) tekrar uygula: oyuncu menzile
girince kilit modülü kilidi geri koyar. Kapatınca otorite ona döner.

---

## 5. GENEL TUZAKLAR (bu işte yakalananlar)

- `SetEntityCollision(mapObj, false, false)` harita objesinde **güvenilir
  değil** — obje görünmez olur, çarpışma yerinde kalır. Gizlemek
  gerekiyorsa `CreateModelHide(x,y,z,r,hash,true)`.
- Sadece kök kemiği (tag 0) oynatan klip, objenin **kendisini** taşır.
  `FreezeEntityPosition(true)` bunu tamamen engeller: klip oynar,
  `PlayEntityAnim` true döner, ekranda hiçbir şey olmaz.
- Bir prop'un iç parçasını oynatan klip **var mı** diye önce bak:
  modelin kemik tag'lerini `skeletons.tsv.gz`'den al, `clips.tsv.gz`'nin
  `bones` kolonunda ara. (Örnek: `hei_prop_heist_deposit_box`'ın
  çekmecelerine dokunan klip 312.748 klip içinde YOK.)
- `.yed` (expression) ile "collision animasyonu" diye bir şey **yok**.
  Referans dosyada `.yed` açıldı: içinde **0 expression** var, 166 baytlık
  boş kabuk, fxmanifest'te kaydı bile yok. İşi yapan fragment yapısıydı.

---

## 6. BANA NE SÖYLEMEN GEREKİYOR

Benzer bir iş için şu üçünü söylersen doğrudan bu reçeteye girerim:

1. **Hangi obje** — model adı (`v_ilev_gb_teldr`) veya "oyunda ölçeyim"
2. **Ne yapmasını istiyorsun** —
   - "normal kapı gibi itilsin"
   - "animasyonla açılsın ve çarpışması da onunla hareket etsin"
   - "sadece modeli değişsin"
3. **Nerede** — "Fleeca'nın içinde" gibi. İç mekân mı dışarısı mı,
   ilk belirlenmesi gereken şey bu.

Kısa hali, kopyalayıp kullanabilirsin:

> `<model_adı>` objesini kendi modelimizle değiştirmek istiyorum.
> `<MLO adı / mekân>` içinde. `<itilebilir kapı | animasyonlu + çarpışma
> takipli | sadece model>` olsun.
> `skills/fivem-assets/mlo-obje-degistir.md` reçetesini uygula.


---

## Eski gövde özeti — elenen yollar ve çalışan yol

## HARİTADAKİ BİR OBJEYİ DÜZELTMEK (spawn etme — ytyp'yi değiştir)

Haritada duran bir prop yanlış tanımlıysa (kapı olması gereken obje
`specialAttribute=0`), **onu gizleyip yerine kendi kopyanı spawn etme.**
Bu yol test edildi ve çöktü:

- Script'le üretilen obje **harita objesi değildir**. Kapı sistemi kapıyı
  model+konum ile haritada arar, script objesini bulamaz.
- Geriye serbest bir fizik prop'u kalır: oyun içinde kapıya dokununca
  zeminin içinden düştü.
- `FreezeEntityPosition` ile düşmesini durdurursan bu sefer kapı sistemi
  onu itemez — kazandığın bir şey olmaz.

Denenip **elenen** diğer yollar (hepsi oyun içi ölçümle):

- **Kendi ymap'inle yerleştirmek** — MLO İÇ MEKÂNINDA ÇALIŞMAZ. Oda/portal
  sistemi dışarıdan konan entity'yi eler; obje hiç gelmez. Sadece MLO
  dışındaki (sokak, açık alan) proplar için geçerlidir. Referans bir
  resource'un ymap kullanması seni yanıltmasın — **önce o prop'un
  koordinatı MLO içinde mi dışında mı ona bak.**
- **Vanilla prop ytyp'sinde `specialAttribute` düzeltmek**
  (`int_lev_des.ytyp` gibi) — dosya doğru üretildi (348/348 archetype
  birebir) ama oyun içinde kapı fiziği yine yüklenmedi.
- **Vanilla adıyla YENİ bir ytyp eklemek** — oyun ilk tanımı zaten
  kaydettiği için çakışır, tutmaz.

**ÇALIŞAN YOL: MLO'nun kendi entity listesinde model adını değiştirmek.**

Objeyi MLO'nun KENDİSİ yerleştirir: doğru odada, doğru konumda, gizleme /
ymap / spawn olmadan, o MLO haritada kaç yerde varsa hepsinde birden.

```
patch_vanilla_ytyp.ps1 -YtypName v_int_10.ytyp `
  -SwapEntity @('v_ilev_gb_teldr=my_teldr','v_ilev_gb_vauldr=my_vauldr') `
  -OutDir <...>\stream
```

- `data_file 'DLC_ITYP_REQUEST'` **EKLENMEZ** — bu bir dosya değişimidir,
  yeni ityp kaydı değil. `stream/` zaten otomatik streamlenir.
  (Kendi yeni ytyp'in için EKLENİR.)
- Script yazdıktan sonra dosyayı geri okuyup imzayı (archetype / oda /
  portal / entity sayıları) kaynakla karşılaştırır ve yeni modelin kaç
  entity'de olduğunu sayar; tutmazsa dosyayı siler. Bozuk ytyp streamlemek
  MLO'yu komple bozar.

Tam adım adım reçete: yukarısı

### Harita objesinin çarpışmasını kaldırma

`SetEntityCollision(mapObj, false, false)` **güvenilir değil** — obje
görünmez olur ama çarpışma yerinde kalır. Belirti: takas ettiğin kapı
açılmış görünür, yine de geçemezsin. Doğrusu `CreateModelHide(x,y,z,r,
hash, true)`; geri almak için `RemoveModelHide` (unutulursa harita objesi
bir daha gelmez). Hide çağrısı handle'ı geçersizleştirir, çarpışmayı
**önce** kapat.
