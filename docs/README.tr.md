<img src="../assets/logo.png" alt="muto-atlas" width="128" align="right">

# muto-atlas

**FiveM / GTA V geliştirmesinde yer gerçeği.** Oyunun kendi verisine bakıp cevap
veren, tahmin etmeyen bir Claude Code plugin'i.

[← English README](../README.md)

---

## Neden var

Bir kapıyı açtırmak istiyorsun. `AddDoorToSystem` denersin, olmaz.
`FreezeEntityPosition` denersin, olmaz. `SetEntityDynamic`,
`NetworkRequestControlOfEntity`… yarım saat gider.

Cevap oyunun kendi `.ytyp`'sinde tek satırdı:

```
specialAttribute = 0   → bu obje KAPI DEĞİL, kapı sisteminde menteşesi yok
```

Tek sorgu, ilk satır kodu yazmadan önce bunu söylerdi:

```bash
assetdb.py door v_ilev_gb_teldr
```

Bütün fikir bu: **önce veriye bak, sonra kod yaz.**

## Kurulum

### 1. Plugin'i kur — iki komut, klonlama yok

```bash
claude plugin marketplace add B7Kompirine/muto-atlas
claude plugin install muto-atlas@muto-atlas
```

Claude Code'u yeniden başlat. Artık **14 komutun** (`/asset`, `/native`, `/where`,
`/anim`, `/ped`, `/yed`, `/clipset`, `/3dnui`, `/weapon`, …) ve **2 skill'in**
(`fivem-natives`, `fivem-assets`) var.

> **Skill'ler plugin'in içinde gelir — ayrıca kurulmaz.** FiveM asset'i, native,
> rigging ya da animasyon işi yaptığında, sen hiç komut yazmasan bile kendiliğinden
> devreye girerler.

### 2. Veri katmanlarını üret

Plugin **hiç oyun verisi taşımaz**; bu adımı yapana kadar komutların cevaplayacak
bir şeyi olmaz. **GTA V ve CodeWalker gerekir** — bu işi yapan herkeste ikisi de
zaten vardır; eksik olan veri değil, **yol bilgisidir.**

En kolay yol, Claude Code içinde:

```
/asset-setup
```

Ne bulabiliyorsa bulur, eksik yolu **sana sorar**, kalanı kurar. Elle de olur:

```bash
python scripts/setup.py --save \
  --gta        "C:\Program Files\Epic Games\GTAV" \
  --codewalker "C:\...\CodeWalker\CodeWalker.Core.dll" \
  --resources  "C:\...\sunucun\resources"
```

`--save` yolları `data/config.json`'a yazar; bir daha sorulmaz.
`scripts/` kurulu plugin klasöründedir (`${CLAUDE_PLUGIN_ROOT}`, tipik olarak
`~/.claude/plugins/cache/muto-atlas/muto-atlas/<sürüm>`).

Doğrulama:

```bash
python scripts/assetdb.py stats
```

### Neden veri repoda yok

İki sebep, ikisi de ölçüldü:

1. `entities.db` tek başına **214 MB**; GitHub'ın dosya sınırı 100 MB. Push
   teknik olarak reddedilir.
2. Rockstar'ın verisi. Yeniden dağıtımı telif sorunudur.

Yan faydası: herkesin katmanı **kendi oyun sürümünden** gelir. Merkezî bir kopya
dağıtılsaydı herkes tek bir sürüme mahkûm olurdu.

## Ne veriyor

24 çevrimdışı veri katmanı:

| katman | satır | neyi cevaplar |
|---|---:|---|
| arketip | 316.975 | kapı mı, pivot nerede, fiziği var mı |
| dünya yerleşimi | 3.054.420 | bu model dünyada nerede duruyor |
| ymap LOD zinciri | 3.145.882 | uzakta neden titriyor / kayboluyor |
| animasyon klibi | 315.964 | süre, iz sayısı, hangi iskelet |
| animasyon adı | 269.414 | `TaskPlayAnim` için sözlük + klip |
| iskelet kemiği | 478.055 | kemik adı ↔ tag ↔ parent |
| dünya nesnesi | 33.912 | **etiketli** ATM, kamera, bank… **rotasyonla** |
| prop | 21.631 | `CREATE_OBJECT` ile spawn edilebilir |
| framework API | 12.713 | sunucunun gerçekten tanımladığı export/event |
| native | 7.191 | imza, apiset (client/server/shared), hash |
| ytyp extension | 64.209 | partikül, merdiven, ışık, expression |
| partikül efekti | 2.549 | `StartParticleFx*` için geçerli `fxName` |
| expression | 2.338 | prosedürel kemik hareketi, yay |
| ped | 1.109 | klip sözlüğü, expression seti, movement clipset |
| araç | 921 | handling id, mod kit, extra |
| IPL | 895 | sınır kutusu, `RequestIpl` / `RemoveIpl` |
| MLO iç mekân | 853 | her iç mekânın her dünya yerleşimi |
| silah + parça | 184 + 634 | bileşen, livery, takılma kemiği |
| …ayrıca | | shader, collision materyali, decal, procedural, senaryo |

Artı bir **Lua linteri**: uydurma native, sunucuda çağrılan client-only native,
yanlış argüman sayısı, per-frame performans hataları.

## Kullanım

```bash
assetdb.py door    v_ilev_gb_teldr        # kapı sistemi bunu oynatır mı
assetdb.py show    prop_atm_01            # tam künye + yorum
assetdb.py where   prop_atm_01            # dünyadaki tüm yerleşimleri
assetdb.py world   --near 147,-1035,29 --radius 50   # bu noktanın çevresinde ne var
assetdb.py pedmeta a_c_rottweiler         # klip sözlüğü, expression, clipset
assetdb.py weapon  WEAPON_CARBINERIFLE --parts       # bileşenler + takılma kemikleri
assetdb.py vehicle adder                  # handling id, mod kit, extra
assetdb.py mlo     v_genbank              # iç mekân + tüm dünya konumları
assetdb.py anim    weld                   # sözlük + klip + süre
assetdb.py fx      <ad> --exact           # bu gerçek bir partikül efekti mi
assetdb.py framework --check              # çalışma anında patlayacak export/event
assetdb.py stats                          # ne kurulu, ne eksik
```

## Çıkış kodları

```
0  bulundu
1  sorgu çalıştı; ad otoritede yok
2  veri katmanı kurulu değil — sonuç hakkında HİÇBİR ŞEY iddia edilemez
3  iç hata (bozuk dosya)
```

`2`'yi `1` sanmak, **veri eksikliğini varlık yokluğu sanmak** ve sonra tahmin
etmektir. Bu plugin tam olarak onu önlemek için var. `stats` asla `2` dönmez —
neyin eksik olduğunu söyleyen komut odur.

## Dil

Çıktı varsayılan olarak İngilizce. Türkçe için:

```bash
assetdb.py --lang tr ...                    # tek çağrı
export MUTO_ATLAS_LANG=tr                   # oturum boyu
python scripts/setup.py --lang tr --save    # kalıcı
```

## Tasarım kuralları

Bunlar üslup tercihi değil; her biri sessiz bir hatadan öğrenildi.

- **Ölç, varsayma.** Belgedeki her sayının onu üreten bir komutu var.
- **Aracın bir şey göstermemesi, o şeyin olmadığının kanıtı değildir.** Satır
  yokluğu asset yokluğu değildir; olmayan bir property `None` döner ve
  `None.length` **`0`**'dır.
- **Adlar kaynaktaki hâliyle saklanır, join daima küçük harf üzerinden kurulur.**
  Dump adları `MixedCase`, plugin katmanları küçük harf — birebir join her ailede
  sessizce sıfır döndürür.
- **Her yazma geri okunur.** "Komut hata vermedi" yazıldığının kanıtı değildir.
- **Eksik çeviri anahtarın kendisini basar**, boş string değil — boşluk fark
  edilmezdi.

---

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
