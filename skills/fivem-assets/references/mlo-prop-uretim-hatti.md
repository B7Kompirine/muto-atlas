# MLO İÇİNE KENDİ PROP'UNU ÜRETME HATTI

Fleeca kasa odasına 20 animasyonlu emanet kutusu ve iki özel kapı koyarken
uçtan uca kurulan hat. Her madde oyun içi ölçümle doğrulandı.

**Sırayla oku. Adım atlarsan sessizce başarısız olur — bu iş hata vermez,
sadece "hiçbir şey olmaz".**

---

## 0. ÖNCE BUNU BELİRLE

**Obje MLO iç mekânında mı, dışında mı?** Her şey buna bağlı.

| | MLO **dışı** | MLO **içi** |
|---|---|---|
| kendi ymap'in | ✅ | ❌ oda/portal eler, obje hiç gelmez |
| MLO entity listesi | — | ✅ tek yol |
| script spawn | ⚠️ harita objesi değil | ⚠️ aynı + her istemcide yük |

**Aynı iç mekânın birden fazla MLO sürümü olabilir.** Fleeca'da iki tane:
`v_genbank` (`v_int_10.ytyp`) ve `hei_generic_bank_dlc`
(`hei_dlc_generic_bank.ytyp`). İkisi **aynı MLO-yerel çerçeveyi** paylaşıyor
(aynı prop ikisinde de aynı yerel koordinatta) ama entity listeleri farklı.
Birine yamayıp diğerini atlarsan test ettiğin şubede hiçbir şey görünmez —
bu bir kez yaşandı ve uzun süre yanlış yerde arandı.

---

## 1. MEVCUT OBJEYİ DEĞİŞTİRME (model adı swap)

En güvenli işlem: dosya boyutu değişmez, MLO yapısına dokunulmaz.

```
patch_vanilla_ytyp.ps1 -YtypName v_int_10.ytyp `
  -SwapEntity @('v_ilev_gb_teldr=muto_teldr','v_ilev_gb_vauldr=muto_vauldr') `
  -OutDir <...>\stream
```

- `-Command` kullan, `-File` değil → `-File` ile virgüllü dizi TEK STRING
  olur ve sessizce `muto_teldr,v_ilev_gb_vauldr=muto_vauldr` gibi uydurma
  bir ada dönüşür.
- `data_file 'DLC_ITYP_REQUEST'` **EKLENMEZ** (vanilla dosya değişimi).

## 2. YENİ ENTITY EKLEME

```
add_mlo_entities.ps1 -YtypName v_int_10.ytyp -Mlo v_genbank `
  -Part v_10_gen_country_bank -Model muto_depobox `
  -CellsJson <...>.json -Count 20 -Room bankvault -OutDir <...>\stream
```

Üç şey aynı anda doğru olmalı, biri eksikse obje **görünmez**:

| alan | doğru | yanlış olursa |
|---|---|---|
| `flags` | **18350080** (vanilla MLO entity'sinden ölçüldü) | ymap değeri `1572872` → obje hiç oluşmaz |
| `lodDist` | **-1** | — |
| **oda** | `AttachedObjects`'e indeks eklenmeli | **eklenmezse obje hiç oluşmaz, MLO bozulabilir** |

Oda ataması en kolay atlanan adım: entity `entities` dizisinde görünür,
ytyp sorunsuz yüklenir, oyunda hiçbir şey çıkmaz.

**Koordinat MLO-YEREL olmalı.** Parça yerel verisi varsa zincir:
`panelLocal → (parça pos/rot) → mloLocal`. Referans parça hedef MLO'da
yoksa diğer MLO'larda aranır (ikisi aynı çerçeveyi paylaşıyor).

## 3. YAMALAR ÜST ÜSTE BİNMELİ

Her script vanilla RPF'ten okursa öncekini **ezer**. Gerçek vaka: kapı
değişimi yapıldı, sonra aynı ytyp'ye kutu eklenince kapılar vanilla'ya
döndü. Her iki script de artık çıktı klasöründe dosya varsa **ondan**
devam ediyor.

---

## 4. FRAGMENT ÜRETİMİ

Detay: `yed-collision-animasyon.md`. Buradaki tek kritik hatırlatma:

**`parentIdx = 255` olan grup entity gövdesidir ve kemiği TAKİP ETMEZ.**
En az iki grup gerekir:

```
grup[0]  sabit kemik   parentIdx=255   → gövde / menteşe
grup[1]  hareketli     parentIdx=0     → dönen parça
```

Bound'u kemiğe bağlayan şey **COPY_TRANSFORMS constraint**'i —
`parent_bone` değil, isim eşleşmesi değil.

### Statik bit

Duvara monte fragment `flags`'ine **32** eklenmezse oyuncu dokununca
**düşer**. `537526784` (animasyonlu fragment) + `32` = **537526816**.

---

## 5. KENDİ .ycd'NİN

Sollumz `.ycd`'yi **XML** olarak yazar ("Successfully exported" der ama
klasörde `.ycd` yoktur). Binary'ye çevirmeden önce XML'e **elle** üç şey
eklenir — Sollumz hiçbirini yazmaz:

```xml
<Clips><Item>
  <Hash>muto_depobox_open</Hash>            ← klip hash'i
  <Name>pack:/muto_depobox_open</Name>       ← pack:/ NORMAL, dokunma
  <Tags /> <Properties />
  <AnimationHash>muto_depobox_open</AnimationHash>
</Item></Clips>
<Animations><Item>
  <Hash>muto_depobox_open</Hash>            ← ANIMASYON hash'i
  <Unknown1C>hash_22E95D79</Unknown1C>      ← Sollumz hash_00000001 yazar
</Item></Animations>
```

Sonra:
```powershell
[CodeWalker.GameFiles.XmlMeta]::GetYcdData($doc)   # GUI'nin kullandigi yol
```

**`XmlYcd.GetYcd($doc).Save()` KULLANMA** — nesne modeline girer,
`ClipDictionary.Clips` üzerinde gezinmek `NotImplementedException` fırlatır.

### Doğrulama (bunu görmeden "oldu" deme)

```
ClipMap = <joaat(klip)>     AnimMap = <joaat(klip)>
```

İkisi de sıfırdan farklı olmalı. `AnimMap = 0` ise `PlayEntityAnim` **true
döner ama kemikler kımıldamaz** — en kafa karıştırıcı belirti.

**Sollumz'un çıktısı her export'ta aynı değil.** Bir seferinde Animations
bloğuna `<Hash>hash_00000000</Hash>` yazdı, bir seferinde elementi **hiç
yazmadı**. Körlemesine `replace` yetmez; her seferinde geri okuyup
`AnimMap`'i doğrula.

---

## 6. YTYP + EXPRESSION EXTENSION

Nesne modeliyle (`Archetype.Extensions`) yazmak **serileşmiyor**.
Tutan yol XML:

```powershell
[CodeWalker.GameFiles.XmlMeta]::GetData($doc, [MetaFormat]::RSC, "")
```

`MetaFormat`'ta **`ytyp` yok** — ytyp bir RSC meta'sıdır.

Doğrulama: `ext: MCExtensionDefExpression dict=<hash> name=<hash>`

---

## 7. ANİMASYON SEÇİMİ — ped mi prop mu?

**Kemik sayısı söyler:**

| kemik | ne |
|---|---|
| 44+32 (çok-izli) | **ped** klibi (gövde + mimik) |
| 72 | genelde **prop** izi (çanta, alet) |
| 4-24 (tek-iz) | prop izi |

Gerçek hata: kutu soyma sekansında ped'e `reward_p_m_bag_var22_arm_s_f`
(72 kemik) oynattım — o **çantanın** izi. Karakter hiç kımıldamadı.
Doğru ped klipleri çok-izli olanlardı: `enter` / `action` / `reward` /
`no_reward` / `rest_exit`.

Süreleri tahmin etme, `assetdb.py anim <dict> --dict-only` ile oku.

### Hazır sekanslar

- **Kilitli kutu delme:** `anim@scripted@cbr5@ig3_drill_box@pattern_01@lockbox_01@male@`
  `enter 3.8 · action 8.0 · reward 4.57 · no_reward 4.10 · rest_exit 3.23`
  Matkap prop'u: `ch_prop_vault_drill_01a`. **Boş çıkma varyantı hazır.**
- **Kasa/tezgâh soyma:** `oddjobs@shop_robbery@rob_till` (enter/loop/exit)

### Prop'u ele tutturma

`PH_R_Hand` (60309) her ped'de çözülmeyebilir; `GetPedBoneIndex` **-1**
dönünce attach kök kemiğe düşer ve prop **gövdenin yanında havada** kalır.
Yedek: `SKEL_R_Hand` (28422).

Klip zaten aleti çantadan çıkarıyorsa prop'u **klipten sonra** tuttur —
yoksa iki alet görünür.

### Senkron sahne klipleri konum ister

Bu klipler ped'in objeye göre **konumu** sabit olacak şekilde yapılmış.
Sadece `TaskTurnPedToFaceCoord` yetmez; ped'i objenin önüne ofsetle koy.

**Objenin ÖNÜ entity'nin ARKASI olabilir** — modelin ön yüzü yerel `-Y`'de
ise (GTA entity ileri yönü `+Y`), `+ileri` kullanmak oyuncuyu 90-180°
yanlış yere koyar.

---

## 8. TEKRARLANMAMASI GEREKEN HATALAR

Hepsi bu oturumda yaşandı ve zaman kaybettirdi.

### Asset / yerleştirme
1. **Script'le spawn edilen obje harita objesi değildir.** Kapı sistemi
   bulamaz (kapı zeminden düştü), fragment collision'ı animasyonu takip
   etmez. Ve 60 kişilik sunucuda her istemcide ayrı yük.
2. **MLO içine ymap ile prop konmaz.** Referansın ymap kullanması
   yanıltmasın — önce onun prop'unun MLO içinde mi dışında mı olduğuna bak.
3. **Entity'yi odaya bağlamayı unutma.** Sessizce görünmez.
4. **MLO entity'sine ymap bayrağı verme.** Sessizce görünmez.
5. **Aynı iç mekânın ikinci MLO sürümünü atlama.**
6. **Vanilla prop ytyp'sinde `specialAttribute` düzeltmek tutmadı** —
   dosya doğru üretildi ama oyun içi fizik yüklenmedi. MLO entity swap
   çalıştı.

### Araç davranışı
7. **CodeWalker `.yed`'i tam okuyamaz.** `ExprMap.Count == 0` görmek
   "dosya boş" DEMEK DEĞİLDİR — expression bytecode'unu yazamıyor, sadece
   okuyabiliyor. Bu yüzden "`.yed` işe yaramıyor" diye saatler kaybedildi.
   **Bir aracın bir şeyi göstermemesi, o şeyin yok olduğu anlamına gelmez.**
8. **Sollumz `.ycd`/`.yed`/`.ymap` binary üretemez** ve `.ycd`'yi XML
   yazarken "Successfully exported" der.
9. **PowerShell `-File` ile dizi geçme** → tek string olur, sessizce bozar.
10. **`Test-Path` yolda `[script]` görünce joker sanar** → `-LiteralPath`.
11. **Lua dosyasını Python ile yazarken kaçışlar bozulabilir.**
    `\n` gerçek satır sonuna dönüşüp Lua stringini bölmüştü; dosya parse
    edilemedi ve **hiçbir komut kayıtlı olmadı**. `lua_check` sözdizimini
    temiz gösterir, çalışma zamanı hatasını yakalamaz.
    → Bu tür satırları doğrudan `Edit` ile yaz.

### Mantık
12. **Durumu önbellekleme, sürekli doğrula.** Aynı hata iki yerde yapıldı:
    `doorRegistered[hash]` önbelleği ve "entity handle değişti mi"
    karşılaştırması. FiveM handle'ı yeniden kullanabilir; animasyon bir kez
    başarısız olursa bir daha denenmez. Doğrusu: `IsEntityPlayingAnim` gibi
    **gerçeğe** sor.
13. **Model adını değiştirince onu arayan her config'i güncelle.**
    `config/heists/fleeca.lua` hâlâ `v_ilev_gb_teldr` arıyordu; kapı modülü
    kapıyı tanıyamayınca kilit mantığı yanlış tarafa düştü.
14. **"Düzelttim, şimdi hiç açılmıyor" sahte regresyon olabilir.**
    Config doğru adı gösterince o güne kadar hiç çalışmamış kilit ilk kez
    devreye girer. Kapı tasarım gereği kilitlidir.
15. **Tek otorite kuralı.** Aynı objeye iki modül durum yazarsa son yazan
    kazanır. Kilit hem kapı sistemiyle hem `FreezeEntityPosition` ile
    uygulanıyordu; donmuş entity kapı sisteminden etkilenmez, bu yüzden
    `durum=0` göründüğü halde kapı açılmıyordu.
16. **Referansı kopyalarken neyin işe yaradığını ölç.** Referansın kendi
    `.ycd`'si olması "custom ycd şart" demek değildi; eksik parça `.yed` +
    Expression extension'dı. O yerine oturunca vanilla klip zaten çalıştı.

### Test disiplini
17. **Asset değiştikten sonra sunucudan çıkıp yeniden bağlan.** Restart
    yetmez, FiveM stream dosyalarını cache'ler.
18. **Bir seferde tek değişken değiştir.** Bir şey çalışmıyorsa zinciri
    parçalara ayır (`.yed`'i çıkar / vanilla klip dene) — iki bambaşka
    düzeltmeyi tek testle ayırt eden A/B testi kur.
19. **Zincirin tamamı bitmeden test isteme.** Yarım zincirde çıkan sonuç
    yanlış yöne götürür.
