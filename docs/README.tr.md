# fivem-natives

FiveM geliştirme veri katmanı — Claude Code plugin'i. İki bölüm:

1. **Native veritabanı + Lua linteri** — native uydurmasını, yanlış tarafa
   yazmasını ve yanlış imza kullanmasını engeller.
2. **Asset veritabanı** — prop / kapı / obje / animasyon gerçeği. `ytyp`'ten
   üretilir; "bu kapı açılır mı" sorusunu tahminle değil veriyle cevaplar.

Tüm veri çevrimdışıdır; sorgu için ağ gerekmez.

## Kurulum

```bash
git clone https://github.com/<kullanici>/fivem-natives
claude plugin marketplace add ./fivem-natives
claude plugin install fivem-natives@fivem-natives
```

Sonra veri katmanlarını kur — **tek komut**:

```bash
python scripts/setup.py --resources "<FiveM sunucun>/resources"
```

Etkileşimli oturumda `/asset-setup` de aynı işi yapar.

### İki kademe

Repo **kod taşır, veri taşımaz**. Katmanlar kurulumda üretilir.

| kademe | ne gerekir | ne gelir |
|---|---|---|
| **HAFİF** (12 katman) | internet + (isteğe bağlı) bir FiveM sunucu klasörü | 7191 native · 269k animasyon adı · 21631 prop · 247 senaryo · 1109 ped künyesi · 184 silah + 634 bileşen · 921 araç · 853 MLO konumu · 895 IPL · 33912 dünya nesnesi · framework indeksi |
| **AĞIR** (12 katman) | GTA V kurulumu + `CodeWalker.Core.dll` | 316k arketip · 3M dünya yerleşimi · 3.1M LOD zinciri · 316k klip (süre+kemik) · 478k kemik · expression · ytyp extension · ptfx · shader · collision · decal |

Ağır katmanlar **dağıtılmaz**: Rockstar'ın verisi ve ~300 MB. Kullanıcının
kendi oyun kurulumundan üretilir:

```bash
python scripts/setup.py --agir --gta "<GTA V>" --codewalker "<yol>\CodeWalker.Core.dll"
```

GTA V olmadan da plugin **çalışır** — hafif kademe tek başına araç, silah, ped,
MLO, IPL, dünya nesnesi ve framework sorgularını cevaplar. Ağır katman isteyen
bir sorgu çalıştırıldığında araç **tahmin etmez**, `EXIT 2` döner ve o katmanı
kuracak komutu yazar.

```bash
python scripts/setup.py --plan     # hicbir sey yazma, sadece durumu goster
python scripts/assetdb.py stats    # her katmanin VAR/YOK durumu
```

## Kullanım

```bash
/native GetVehicleNumberPlateText     # imza, taraf, docs linki
/native araç yakıtı --apiset server   # serbest metin arama
/native-lint resources/muto-lumber    # Lua denetimi

/asset v_ilev_gb_teldr                # ytyp gerçeği + yorum
/asset door prop_gate_prison_01       # "kapı sistemi çalışır mı"
/anim weld                            # animasyon dict + clip
/asset-build <resources yolu>         # indeksleri yeniden kur

/where v_ilev_gb_teldr                # dunyada nerede (ymap + MLO ic mekan)

python scripts/assetdb.py pedmeta a_c_rottweiler     # klip sozlugu + expression + clipset
python scripts/assetdb.py weapon WEAPON_CARBINERIFLE --parcalar   # 11 bilesen + AttachBone
python scripts/assetdb.py vehicle adder              # handlingId, modkit, extra
python scripts/assetdb.py mlo v_genbank              # 6 dunya konumu
python scripts/assetdb.py ipl finbank                # RequestIpl adi dogrulama
python scripts/assetdb.py world --near 147,-1035,29 --mesafe 60   # yakindaki ATM/CCTV/bank
python scripts/assetdb.py world --aileler            # 34 nesne ailesi
/yed muto_vauldr 50607                # collision animasyonu TAKIP ETSIN (.yed zinciri)
/3dnui prop_atm_01                    # obje ustunde canli/tiklanabilir HTML ekran (DUI)
```

`/3dnui` — bir objenin üstüne **gerçek HTML/JS çalışan, tıklanabilir bir
ekran** koyar (ATM tuş takımı, kasa terminali, kamera monitörü, laptop).
Önce `screentex.ps1` ile modelin ekran dokusu olup olmadığı **sorulur**,
sonra üç render yolundan doğrusu seçilir: `AddReplaceTexture` (modelin kendi
ekranı) / dünya quad'ı (`CreatePanel`) / entity'ye bağlı quad. Ölçülmüş
değerler ve 13 maddelik tuzak kataloğu:
`skills/fivem-assets/references/3dnui-dui-panel.md`

`/yed` — bir fragment prop'a animasyon oynatildiginda **carpismanin da
animasyonla birlikte hareket etmesini** saglayan bes parcali zinciri kurar:
`.yft` (kemik tag + fragment physics + COPY_TRANSFORMS) -> `.yed` (expression) ->
`ytyp` (Expression extension + clip dict) -> `.ycd` -> Lua. Tuzaklariyla birlikte
tam recete: `skills/fivem-assets/references/yed-collision-animasyon.md`

İki skill (`fivem-natives`, `fivem-assets`) ilgili işlerde otomatik devreye girer;
komutları elle çağırmak gerekmez.

## Doğrudan CLI

```bash
python scripts/nativedb.py check GetEntityCoords DrawMarker
python scripts/nativedb.py show  GetVehicleNumberPlateText
python scripts/nativedb.py search vehicle fuel --apiset server
python scripts/nativedb.py ns    VEHICLE --apiset server
python scripts/nativedb.py stats

python scripts/lint_lua.py <klasör> [--side client|server] [--json]
```

`check` bilinmeyen native için exit 1 döner — CI'da kullanılabilir.

## Veri

| küme | adet |
|---|---:|
| toplam | 7191 |
| client-only | 6830 |
| shared | 232 |
| server-only | 129 |

Kaynaklar:

- `https://runtime.fivem.net/doc/natives.json` — GTA V nativeleri
- `https://runtime.fivem.net/doc/natives_cfx.json` — Cfx nativeleri (`apiset` taşır)
- `citizenfx/fivem` → `ServerGameState_Scripting.cpp` — sunucu handler kayıtları

GTA V listesi upstream'de `apiset` taşımadığı için sunucu erişilebilirliği son iki
kaynaktan türetilir. Bir native hem GTA V client setinde hem Cfx sunucu bildiriminde
geçiyorsa `shared` işaretlenir.

Güncelleme:

```bash
python scripts/build_index.py --fetch
```

## Lint kuralları

| kural | seviye | anlamı |
|---|---|---|
| E001 | hata | native yok (yazım hatası / uydurma) |
| E002 | hata | client-only native sunucu dosyasında |
| E003 | hata | imzadan fazla argüman |
| W101 | uyarı | `RequestModel`/`RequestAnimDict` per-frame |
| W102 | uyarı | `GetGamePool`/`GetActivePlayers` `Wait(0)` içinde |
| W103 | uyarı | mesafe hesabı per-frame, önbelleklenmemiş |
| W104 | uyarı | imzadan eksik argüman |

Linter tablo/metot çağrılarını (`Bridge.HasItem`) ve taranan dosyalarda tanımlı
fonksiyonları native saymaz. Taraf tespiti dosya adından ve `fxmanifest.lua`
içindeki `client_scripts`/`server_scripts` bloklarından yapılır; `--side` ile
geçersiz kılınabilir.

---

# Asset veritabanı

## Neden var

Fleeca vezne kapısı `v_ilev_gb_teldr` bir türlü açılmadı. `AddDoorToSystem`,
`FreezeEntityPosition`, `SetEntityDynamic`, `NetworkRequestControlOfEntity`
sırayla denendi. Cevap `int_lev_des.ytyp`'nin tek satırındaydı:

```
specialAttribute = 0   → bu obje kapı DEĞİL, menteşesi yok
```

Bu katman o satırı kod yazılmadan önce sorgulanabilir yapar.

## Veri

| küme | adet | kaynak |
|---|---:|---|
| archetype (vanilla) | 315.699 | GTA V RPF → 2744 ytyp, CodeWalker.Core ile |
| archetype (custom) | 656 | sunucunun kendi `.ytyp` dosyaları |
| dünya yerleşimi | 3.054.420 | 19.366 ymap + MLO iç mekân genişletmesi |
| animasyon klibi (detaylı) | 312.748 | 24.692 `.ycd` — süre + iz + kemik sayısı |
| çok izli klip (ped+prop) | 88.011 | aynı |
| iskeletli model | 72.364 | 144.798 `.ydr`/`.yft` taraması |
| kemik kaydı | 478.055 | ad + tag + parent |
| expression | 2.338 | 242 `.yed` (100'ü yay/spring içerir) |
| animasyon klibi (isim) | 269.414 | DurtyFree/gta-v-data-dumps |
| animasyon dictionary | 19.771 | aynı |
| spawn edilebilir prop | 21.631 | aynı |
| ped senaryosu | 247 | aynı |
| **ped künyesi** | **1.109** | **dump — klip sözlüğü, expression, movement clipset** |
| **silah** | **184** | **dump — kategori, model, mermi, tint** |
| **silah parçası** | **634** | **dump — 479 bileşen + 155 livery, `AttachBone` ile** |
| **araç** | **921** | **dump — handlingId, modkit, extra, sınıf** |
| **MLO iç mekânı** | **853** | **dump — 385 iç mekân, KONUM başına satır (844 konum)** |
| **IPL** | **895** | **dump — sınır kutusu + grup/kategori** |
| **dünya nesnesi** | **33.912** | **dump — 34 aile, ROTASYON ile (`entities` rotasyon tutmaz)** |

Son yedi küme `scripts/build_dumps.py` ile üretilir:

```bash
python scripts/build_dumps.py --dump <gta-v-data-dumps klasoru>
```

Kaynak sürümü `data/dumps.meta.json`'a yazılır (`v3717.0 / mp2025_02_g9ec`).

**⛔ Join kuralı:** dump katmanlarının ad kolonları kaynaktaki harf düzeniyle
yazılır (`W_AR_ASSAULTRIFLE`), plugin'in kendi katmanları küçük harftir.
Karşılaştırma **daima `.lower()` üzerinden** kurulur. Birebir join her ailede
0 döndürür ve bu **sessizdir** — tablo dolu görünür, eşleşme boş çıkar.
Ölçülmüş örnek: `A_C_Rottweiler` klip sözlüğünü `creatures@rottweiler@move`
diye yazar, `A_C_Rottweiler_02` aynı sözlüğü `CREATURES@ROTTWEILER@MOVE`
diye yazar.

**Her dump katmanında `dlc` kolonu vardır ve gereklidir.** Sunucu
`sv_enforceGameBuild` ile bir yapıya sabitlenir; dump'ta **var** ama sunucunun
yapısında **yok** olan bir ad "geçerli" diye raporlanır, oyunda `RequestModel`
hiç yüklenmez ve F8'de hata da çıkmaz.

## Çıkış kodları

`assetdb.py` dört ayrı kod döndürür — hepsini `!= 0` diye okumak yanlıştır:

| kod | anlam |
|---:|---|
| 0 | bulundu |
| 1 | sorgu çalıştı, **ad otoritede yok** |
| 2 | **veri katmanı kurulu değil** — sonuç hakkında hiçbir şey denemez |
| 3 | iç hata (bozuk dosya, istisna) |

`2`'yi `1` sanmak, katman eksik olduğu için çıkan "0 sonuç"u "bu asset oyunda
yok" diye okumaktır. `assetdb.py stats` her katmanın VAR/YOK durumunu basar.

Archetype başına: `specialAttribute`, `flags`, `assetType`, `lodDist`,
bbMin/bbMax (pivot/menteşe tespiti), `bsRadius`, fizik/doku/clip sözlükleri,
hangi ytyp'ten geldiği ve vanilla mı custom mu.

## CLI

```bash
python scripts/assetdb.py show   v_ilev_gb_teldr     # detay + yorum
python scripts/assetdb.py door   prop_gate_prison_01 # kapı kararı
python scripts/assetdb.py search fleeca              # archetype arama
python scripts/assetdb.py prop   prop_cctv           # spawn edilebilir proplar
python scripts/assetdb.py where  v_ilev_gb_teldr     # dünyada nerede (6 Fleeca)
python scripts/assetdb.py near   145.42 -1041.81 29.64 --radius 10 --filter door
python scripts/assetdb.py anim   weld                # dict + clip + süre + kemik
python scripts/assetdb.py anim   anim@heists@ornate_bank@grab_cash --dict
python scripts/assetdb.py bones  prop_cs_cardbox_01  # iskelet: kemik adı + tag
python scripts/assetdb.py clipfit anim@heists@fleeca_bank@bank_vault_door bank_vault_door_opens
python scripts/assetdb.py expr   spring              # expression (.yed)
python scripts/assetdb.py scenario welding
python scripts/assetdb.py stats

# modelin ekranı var mı — shader/doku eşlemesi (AddReplaceTexture için)
powershell -File scripts/screentex.ps1 -Model prop_atm_01 -All
```

`screentex.ps1` modelin `.ydr/.yft/.ydd`'sini RPF'ten okuyup her shader'ın
doku parametrelerini yazar. `AddReplaceTexture(origTxd, origTxn, …)` için
gereken iki ad tahmin edilemez; bu sorgu doğrudan verir. Ölçüldü: ekran
**`emissive*` shader**'dadır ve doku neredeyse her zaman **modele gömülüdür**
(→ `origTxd` = model adı). Keypad ve CCTV prop'larının ekran dokusu yoktur.

### Prop + karakter animasyonu

`anim <dict> --dict` klipleri **süreye göre gruplar**. Aynı sürede *farklı
kemik sayısı* varsa o bir ped+prop çiftidir:

```
[47.967s]  <-- ayni sure, FARKLI iskelet: ped + prop cifti
  bag_grab              47.967s  kemik=72    <- ped
  cart_cash_dissapear   47.967s  kemik=96    <- prop (para arabası)
```

Sadece aynı süre yetmez — `_female`/`_suit` varyantları da aynı süredir ama
hepsi ped'dir. Ayırt eden kemik sayısının farklı olması.

Prop tarafında kemik adları da elimizde:

```
$ assetdb.py bones ch_prop_cash_low_trolly_01a
  ydr · 47 kemik
    #0  Prop_Cash_low_Trolly_01a_Root   tag=0       parent=-
    #1  Prop_Cash_low_Trolly_01a_Main   tag=56965   parent=0
    #2  P_M_CashTrolly_S_1_Stack001     tag=29611   parent=1
    #3  P_M_CashTrolly_S_1_Stack002     tag=29612   parent=1
```

Her para destesi ayrı kemik — "para dolduruyor" animasyonu bu kemikleri
oynatarak/gizleyerek çalışıyor. `GetEntityBoneIndexByName` bu adları alır.

## specialAttribute — kapı tablosu

Adlar **Sollumz 2.9 kaynağından** (`ytyp/properties/ytyp.py:53`), kapı yeteneği
316k archetype üzerinde **ölçülerek** doğrulandı: `Enable Door Physics` bayrağı
(bit 26) kurulu 1176 archetype'ın `specialAttribute` dağılımı.

| değer | Sollumz adı | door physics'li adet | kapı sistemi |
|---|---|---:|---|
| 7 | Normal Door | 646 | ✅ |
| 5 | Garage Door | 77 | ✅ |
| 8 | Sliding Door | 71 | ✅ |
| 10 | Sliding Vertical Door | 7 | ✅ |
| 12 | Rail Crossing Barrier Door | 2 | ✅ |
| 9 | Barrier Door | **0** | ❌ |
| 14 | Single Axis Rotation | **0** | ❌ prosedürel dönüş (çatı fanı) |
| 0 | None | **379** | ⚠ bayrağa bak |

⚠ **`specialAttribute` tek başına yetmez:** 379 archetype `=0` olduğu hâlde
door physics taşıyor. `assetdb.py door` artık bayrağı da raporluyor.

Tam tablo (21 değer) + entity/archetype bit tabloları + extension tipleri:
`skills/fivem-assets/references/ytyp-ymap-bayraklari.md`

## Bayrak çözme

```bash
python scripts/assetdb.py flags 549584896            # archetype (ytyp)
python scripts/assetdb.py flags 1572872 --entity     # entity (ymap)
```

```
1572872  (0x180008)  ->  ENTITY (ymap) bayragi
              8  bit3   LOD in Parented YMAP
         524288  bit19  Cast Static Shadows
        1048576  bit20  Cast Dynamic Shadows
```

## İndeksi kurma

```bash
# archetype — CodeWalker.Core.dll + GTA V kurulumu gerekir, ~20 sn
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_archetypes.ps1 `
    -ExtraFolders "<sunucu resources yolu>"

# dünya konumları — ~50 sn + ~20 sn, entities.db ~214 MB
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_entities.ps1
python scripts/build_entities_db.py    # --drop-tsv ile ara dosyayı sil

# animasyon klipleri (.ycd) — süre + kemik, ~3 dk
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_clips.ps1

# iskelet (.ydr/.yft) + expression (.yed) — uzun sürer
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_rigs.ps1

# animasyon adı / prop / senaryo listesi — internet gerekir
python scripts/build_anims.py          # --offline ile önbellekten
```

`build_entities.ps1` varsayılan olarak LOD/arazi parçalarını atlar; `-All` ile
hepsi indekslenir (indeks ~10x büyür).

`build_archetypes.ps1` CodeWalker ve GTA V yollarını kendi bulur; bulamazsa
`-CodeWalker` / `-GtaFolder` ile verilir.

## Klip → model eşleştirme (`clipfit`)

Bir klibin hangi modelde oynatılmak üzere yapıldığını **kemik tag'leriyle**
bulur. Kemik sayısı yanıltıcıdır (aynı kemiğin konum/rotasyon izleri ayrı
sayılır); tag seti ise modeli tek başına belirler.

```
$ assetdb.py clipfit anim@heists@fleeca_bank@bank_vault_door bank_vault_door_opens
  hedefledigi kemik tag'leri (3): [0, 10596, 50607]
  TAM ESLESME (1 model):
    hei_prop_heist_sec_door    3 kemik  [ydr]
```

72.364 kemikli model içinde tek aday. bbox'ı haritadaki `v_ilev_gb_vauldr`
ile birebir aynı → animasyonlu ikizi. **Prop swap** deseninin kaynağı budur.

## ytyp override üretimi

Archetype yanlış tanımlıysa (kapı olması gereken obje `specialAttribute=0`):

```bash
powershell -File scripts/make_ytyp_override.ps1 `
    -Models v_ilev_gb_teldr -SpecialAttribute 7 `
    -YtypName muto_fleeca_doors -OutFile "<resource>\stream\muto_fleeca_doors.ytyp"
```

Kaynağı RPF'ten okur, tüm alanları birebir kopyalar, tek değeri değiştirir.
Çıktı `data_file 'DLC_ITYP_REQUEST'` ile bildirilerek yüklenir.

## Sınırlar

Kapsamayanlar:

- fragment iç yapısı / bone listesi (.yft)
- animasyon süresi ve eventleri (.ycd)
- sunucunun kendi MLO'larının iç yerleşimi (archetype'ları gelir, iç entity
  genişletmesi vanilla ymap'lere bağlıdır)

Bunlar için CodeWalker'da bakmak ya da oyun içi ölçüm gerekir.

## Dünya konumu doğrulaması

MLO iç mekân matematiği (`world = mloPos + rotate(localPos, mloRot)`, ham
quaternion) bağımsız ölçümle doğrulandı:

| kaynak | v_ilev_gb_teldr @ Legion Square |
|---|---|
| indeks | `(145.4186, -1041.8130, 29.6426)` |
| oyun içi ölçüm | `(145.4186, -1041.8125, 29.6426)` |
