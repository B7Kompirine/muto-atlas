# COLLISION'IN ANİMASYONU TAKİP ETMESİ — Expression (.yed) YÖNTEMİ

Bir fragment prop'a animasyon oynattığında **çarpışmanın da animasyonla
birlikte hareket etmesini** sağlayan zincir. Çalışan yöntem budur.

> Bu reçete kullanıcı tarafından verildi ve daha önce bizzat çalıştırıldı.
> Tahmin değil. Varyasyon deneme — **birebir uygula.**

---

## ZİNCİR (5 parça, hepsi gerekli)

### 1) YFT — Blender / Sollumz

- Animasyonlu kemiğe bir **tag** ver (örn. `64893`)
- O kemikte **Fragment Physics AÇIK** olmalı
- Collision bound'u o kemiğe bağlı olmalı
  → Sollumz bunu **COPY_TRANSFORMS constraint**'i ile yapar
  (`parent_bone` değil, isim eşleşmesi değil — bkz. SKILL.md fragment bölümü)

### 2) .yed — Expression Dictionary

```
Tracks:     BoneId = <kemik tag>,  Track = 1,  Format = 1,  UnkFlag = False
Streams:    BOŞ
Signature:  3140693525
Unk7C:      3
Dosya adı:  <model_adi>.yed
```

### 3) YTYP arketip

```
Extensions -> Add Extension -> Type = Expression
    Expression Dictionary = <model_adi>      (ÇIPLAK ad)
    Expression Name       = <model_adi>      (ÇIPLAK ad)
Clip Dictionary = <ycd_adi>
Flags = Has Anim (YCD) + Dynamic + Use Ambient Scale
```

Flags sayısal karşılığı: vanilla animasyonlu fragment'ler (`prop_aircon_l_01`,
`prop_roofvent_06a` …) **537526784** kullanıyor — clipDict'i dolu olan
fragment arketiplerinden doğrulandı.

### 4) YCD

Klip adı model adıyla **AYNI OLMAMALI**.
`<model_adi>_open` / `<model_adi>_close` gibi ayır.

### 5) Lua — tick yok, collision'a dokunma

```lua
RequestAnimDict('<ycd_adi>')
while not HasAnimDictLoaded('<ycd_adi>') do Wait(0) end
PlayEntityAnim(prop, '<klip_adi>', '<ycd_adi>', 1000.0, false, true, false, 0.0, 0)
```

`SetEntityCollision`, `FreezeEntityPosition`, `SetEntityHeading`,
`DoorSystemSetOpenRatio` — **hiçbiri kullanılmaz.** Collision'ı script ile
kovalamaya çalışmak bu yöntemin tamamını bozar.

---

## KRİTİK TUZAKLAR (hepsi bizzat yaşandı)

**YTYP Expression alanlarına `pack:/model.expr` YAZMA.**
Oyun `pack:/` ve `.expr` kısmını atıp sadece dosya adını joaat'lar. Çıplak ad
yaz: `mairon_kapili_box`. Yanlış yazarsan expression hiç yüklenmez **ama mesh
animasyonu çalışmaya devam eder** — bu yüzden hatayı fark etmek çok zor.

- `Signature = 0` yapma → **3140693525** kullan.
- Dummy track (`BoneId = 0`) **EKLEME**.
- Klip adı model adıyla aynı olursa `PlayEntityAnim` **false** döner.
- **Asset değiştirdikten sonra sunucudan ÇIKIP YENİDEN BAĞLAN.**
  FiveM stream dosyalarını cache'ler; **restart yetmez.** Bu adım atlanırsa
  bayat asset test edilir ve yanlış sonuç çıkarılır.

---

## ARAÇLAR

Sollumz `.yed` / `.ycd` / `.ymap` **binary üretemiyor.**

### .yed → `muto` Blender eklentisi

Saf Python, harici bağımlılık yok:
`~/AppData/Roaming/Blender Foundation/Blender/5.2/scripts/addons/muto.py`

Panelden (`MUTO_PT_yed`) ya da doğrudan:

```python
import importlib.util
spec = importlib.util.spec_from_file_location("muto", r"...\muto.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

data = m.build_yed("muto_vauldr",
                   [(50607, 1, 1, False)],          # (bone_id, track, format, unk_flag)
                   signature=m.DEFAULT_SIGNATURE,   # 3140693525
                   unk7c=m.DEFAULT_UNK7C)           # 3
open(r"...\stream\muto_vauldr.yed", "wb").write(data)
```

### .ycd — Sollumz XML üretir, binary'ye çevrilmeli

`.ycd` her zaman **`.ycd.xml`** çıkar; `target_formats` bunu değiştirmez,
çünkü `.ycd` Sollumz'un format sağlayıcı sisteminin **dışındadır**
(`ycd/ycdexport.py` doğrudan `write_xml()` çağırır). "Successfully exported"
der, klasörde `.ycd` yoktur — sessiz tuzak.

```
powershell -File scripts/xml_to_ycd.ps1 -XmlPath <...>\muto_vauldr_anim.ycd.xml
```

CodeWalker API'si:
```csharp
[CodeWalker.GameFiles.XmlYcd]::GetYcd($xmlDoc).Save()
[CodeWalker.GameFiles.XmlMeta]::GetData($xmlDoc, $format, $klasor)
```

### PowerShell yol tuzağı

Yol içinde `[script]` gibi köşe parantez varsa `Test-Path` onu **joker**
sanar ve dosyayı bulamaz → **`-LiteralPath` şart.**

---

## BİLİNEN SINIRLAR

- Sadece `Track = 1` (rotasyon) test edildi.
- Tek kemikli prop test edildi.
- `Signature`'ın nasıl hesaplandığı bilinmiyor; çalışan değer kopyalanıyor.
- CodeWalker expression bytecode'unu (`Streams`) **yazamıyor, sadece
  okuyabiliyor.** Bu yüzden CodeWalker ile bir `.yed` açıp
  `ExprMap.Count == 0` görmek "dosya boş" demek DEĞİLDİR.

---

## DOĞRULANDI — bu zincir ÇALIŞIYOR

Fleeca kasa kapısında oyun içi doğrulandı: animasyon oynuyor **ve çarpışma
onu takip ediyor.**

### Kendi .ycd'ne GEREK YOK

Referans resource'un kendi `.ycd`'sini kullanıyor olması yanıltmasın —
eksik parça o değil, **`.yed` + ytyp Expression extension**'dır. O yerine
oturduğunda prop'un **vanilla klibi** zaten çalışır.

Gerçek vaka: kasa kapısı için `muto_vauldr_anim.ycd` üretildi (hash doğru,
eğriler dolu, `PlayEntityAnim` true döndü) ama kapı kımıldamadı. Aynı objeye
vanilla `bank_vault_door_opens` oynatılınca hem açıldı hem çarpışma takip
etti. Yani custom ycd üretmek **gereksiz bir yan yoldu.**

**Sıra:** önce `.yed` + extension'ı kur, prop'un vanilla klibiyle test et.
Ancak uygun vanilla klip YOKSA kendi ycd'ni üret.

### STREAMING — açık kalması garantilenmeli

Oyuncu uzaklaşınca MLO boşalır; dönünce **entity yeniden yaratılır ve
animasyon gider**. Kapı kendiliğinden kapalı görünür. Oyun içi risk: soygun
sırasında uzaktan gelen NPC/polis kapıyı kapalı görürse akış bozulur.

**"Handle değişti mi" diye bakma — iki şekilde patlar:**
1. FiveM handle'ı yeniden kullanabilir → değişim görülmez, uygulanmaz
2. Animasyon bir kez başarısız olursa (iç mekân henüz yüklenmemiş) handle
   kaydedildiği için bir daha denenmez

**Doğrusu: olaya değil gerçeğe sor.**
```lua
if not wantOpen then return end
local o = nearest(MODEL); if not o then return end
if IsEntityPlayingAnim(o, DICT, CLIP, 3) then return end   -- zaten oynuyor
if not loadDict(DICT) then return end
PlayEntityAnim(o, CLIP, DICT, 1000.0, false, true, false, 1.0, 0)  -- delta=1.0
```
`delta = 1.0` klibin sonundan başlatır; yoksa oyuncu her dönüşünde kapının
baştan açılmasını izler. `stayInAnim = true` olduğu için klip bitince de
"oynuyor" sayılır ve kapı açık kalır.

Aynı hata kilit tarafında da yapıldı (`doorRegistered[hash] = true` önbelleği).
Genel kural: **durumu önbellekleme, sürekli doğrula.**

### A/B testi — "true dönüyor ama kımıldamıyor"

`PlayEntityAnim` true döndüğü halde hiçbir şey olmuyorsa aynı objeye
**vanilla klip** oynat:
- kapı hareket ederse → senin ycd'n bozuk
- yine durursa → sorun klipte değil, yft/ytyp/obje tarafında

Bu tek test iki bambaşka düzeltmeyi ayırır; tahmin yürütme.

## ytyp'ye Expression extension yazma — ÇÖZÜLDÜ

Nesne modeliyle (`Archetype.Extensions`) yazmak **serileşmiyor** —
`CBaseArchetypeDef.extensions` ham `Array_StructurePointer` ve `Save()` onu
nesne modelinden doldurmuyor.

**Tutan yol: ytyp'yi XML'den üretmek.**
`scripts/make_expression_ytyp.ps1` bunu yapar:
```
[CodeWalker.GameFiles.XmlMeta]::GetData($doc, [MetaFormat]::RSC, "")
```
DİKKAT: `MetaFormat`'ta **`ytyp` yok** — ytyp bir RSC meta'sıdır.

**Doğrulama kriteri** (bunu görmeden "oldu" deme):
```
ext: MCExtensionDefExpression  dict=<hash>  name=<hash>
```

Geçici çözüm: ytyp'yi CodeWalker GUI'de aç →
Extensions → Add Extension → Expression → alanlara **çıplak** model adını yaz.

---

## KULLANICI BU İŞİ İSTEDİĞİNDE

> `<model_adi>` prop'unun collision'ı animasyonu takip etsin istiyorum.
> Animasyonlu kemik tag'i `<tag>`. `references/yed-collision-animasyon.md`
> reçetesini uygula.

Uygularken: varyasyon deneme, adımları atlama, "şunu da deneyelim" deme.
Zincirin beş parçası da tamamlanmadan test isteme.
