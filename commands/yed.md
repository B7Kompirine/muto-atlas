---
description: Prop'un collision'ı animasyonu takip etsin — .yed expression zinciri (yft + yed + ytyp + ycd + Lua)
argument-hint: <model adı> [animasyonlu kemik tag'i]
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

Bir fragment prop'a animasyon oynatıldığında **çarpışmanın da animasyonla
birlikte hareket etmesini** sağlayan zinciri kurar.

> Bu yöntem kullanıcı tarafından verildi ve daha önce bizzat çalıştırıldı.
> **Tahmin değil, varyasyon deneme — birebir uygula.**
> Zincirin beş parçası da tamamlanmadan kullanıcıdan test isteme.

## ÖNCE OKU

Tam reçete ve tuzaklar:
`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/yed-collision-animasyon.md`

Fragment kurma kuralları (zincirin 1. adımı, kök grup tuzağı dahil):
`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/SKILL.md`

## ZİNCİR — beşi de gerekli

### 1) YFT (Blender / Sollumz)
- Animasyonlu kemikte **tag** var
- O kemikte **Fragment Physics AÇIK**
- Collision bound o kemiğe **COPY_TRANSFORMS constraint**'i ile bağlı
  (`parent_bone` DEĞİL, isim eşleşmesi DEĞİL)

### 2) .yed — `muto` Blender eklentisiyle
```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "muto", r"~/AppData/Roaming/Blender Foundation/Blender/5.2/scripts/addons/muto.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

data = m.build_yed("<model_adi>",
                   [(<kemik_tag>, 1, 1, False)],    # (bone_id, track, format, unk_flag)
                   signature=m.DEFAULT_SIGNATURE,   # 3140693525
                   unk7c=m.DEFAULT_UNK7C)           # 3
open(r"<...>\stream\<model_adi>.yed", "wb").write(data)
```
`Streams` BOŞ · dummy track (`BoneId=0`) **EKLEME** · `Signature=0` yapma.

### 3) YTYP
```bash
powershell -File "${CLAUDE_PLUGIN_ROOT}/scripts/make_ytyp_override.ps1" `
  -Models <kaynak_arketip> -RenameTo <model_adi> `
  -AssetType ASSET_TYPE_FRAGMENT -ClearDicts -PhysicsDictSelf `
  -SpecialAttribute 0 -Flags 537526784 -LodDist 200 `
  -ClipDict <ycd_adi> -Expression <model_adi> `
  -YtypName <model_adi> -OutFile "<...>\stream\<model_adi>.ytyp"
```
- `-Expression` **ÇIPLAK AD** ister. `pack:/x.expr` yazma — oyun `pack:/` ve
  `.expr` kısmını kendi ekler. Yanlış yazarsan expression hiç yüklenmez **ama
  mesh animasyonu çalışmaya devam eder**, hatayı fark etmek çok zor olur.
- `Flags = 537526784` = Has Anim (YCD) + Dynamic + Use Ambient Scale.
  Vanilla animasyonlu fragment'lerden (`prop_aircon_l_01`, `prop_roofvent_06a`)
  doğrulandı.

**AÇIK İŞ:** extension şu an ytyp'ye serileşMİYOR (geri okumada `Extensions`
boş çıkıyor). Sebep muhtemelen `Init()`'in üzerine yazması ya da `Save()`'in
`CBaseArchetypeDef.extensions` alanından okuması. Düzeltilene kadar geçici
çözüm: ytyp'yi CodeWalker GUI'de aç → Extensions → Add Extension → Expression.

Doğrulama kriteri — bunu görmeden "oldu" deme:
```
ext: MCExtensionDefExpression  dict=<hash>  name=<hash>
```

### 4) YCD
Klip adı model adıyla **AYNI OLMAMALI** → `<model_adi>_open` / `_close`.
Aynı olursa `PlayEntityAnim` **false** döner.

`.ycd` **her zaman** `.ycd.xml` olarak çıkar; `target_formats` bunu değiştirmez.
Sebep ölçüldü: `ycd/ycdexport.py` doğrudan `clip_dict.write_xml()` çağırır,
`.ycd` Sollumz'un format sağlayıcı sisteminin **dışındadır** (o sistem yalnız
`.ybn .ydr .ydd .yft .yld .ytyp .ymap .ytd` tanır). "Successfully exported"
der ama klasörde `.ycd` yoktur — sessiz tuzak:
```bash
powershell -File "${CLAUDE_PLUGIN_ROOT}/scripts/xml_to_ycd.ps1" -XmlPath <...>.ycd.xml
```

### 5) Lua — tick yok, collision'a dokunma
```lua
RequestAnimDict('<ycd_adi>')
while not HasAnimDictLoaded('<ycd_adi>') do Wait(0) end
PlayEntityAnim(prop, '<klip_adi>', '<ycd_adi>', 1000.0, false, true, false, 0.0, 0)
```
`SetEntityCollision` · `FreezeEntityPosition` · `SetEntityHeading` ·
`DoorSystemSetOpenRatio` — **hiçbiri kullanılmaz.** Collision'ı script ile
kovalamak bu yöntemin tamamını bozar.

## TEST

Asset değiştikten sonra **sunucudan ÇIKIP YENİDEN BAĞLAN.** FiveM stream
dosyalarını cache'ler; **restart yetmez.** Bu adım atlanırsa bayat asset
test edilir ve yanlış sonuç çıkarılır.

## BİLİNEN SINIRLAR

- Sadece `Track = 1` (rotasyon) test edildi
- Tek kemikli prop test edildi
- `Signature`'ın nasıl hesaplandığı bilinmiyor; çalışan değer kopyalanıyor
- CodeWalker expression bytecode'unu (`Streams`) **yazamıyor, sadece
  okuyabiliyor** → CodeWalker'da `ExprMap.Count == 0` görmek "dosya boş"
  DEMEK DEĞİLDİR. Bir aracın bir şeyi göstermemesi, o şeyin yok olduğu
  anlamına gelmez.
