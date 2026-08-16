---
description: Choreographed motion and destruction - the RayFire (des_*) composite system
argument-hint: [ne olacak — "kule çöksün" / "duvar yıkılsın" / "vinç devrilsin"]
allowed-tools: Bash(powershell.exe:*), Bash(pwsh:*), Bash(python:*), Read, Edit, Write, Glob, Grep, AskUserQuestion
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

## ÖNCE OKU

`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/rayfire-des-uretim.md`

Vanilla `des_stilthouse` alan alan açılarak ölçüldü ve birebir kopyası
üretilip oyunda çalıştırıldı. İçindeki hiçbir sayı tahmin değildir.

---

## ADIM 0 — YOLU SEÇ, KOD YAZMA

Bu alanda **üç ayrı sistem** var ve üçü de "obje hareket etsin, collision
da gelsin" diye tarif ediliyor. Yanlışını seçmek turlarca kaybettirir —
bu bir kez yaşandı, asset iki reçetenin melezi oldu ve hiç çalışmadı.

| kullanıcı ne istiyor | doğru yol |
|---|---|
| tek prop'un kapağı/kolu/kepçesi açılsın, **collision onunla gelsin** | `.yed` expression zinciri → `/yed` |
| bina/kule/iskele **çöksün**, sağlam hal → enkaz hali | **RayFire desen A** (imap takası) — bu belge |
| küçük/iç mekân prop'u enkaz prop'una **dönüşsün** | **RayFire desen B** (model takası) — bu belge |
| ped'in yürüyüş/koşu stili | `/clipset` |
| collision'ı `SetEntityCollision` / `FreezeEntityPosition` ile kovalamak | **YASAK** — üç yolun da hepsini bozar |

**Tarif belirsizse SOR.** "Duvar kırılsın", "kapı patlasın", "senaryo
başlasın", "çarpınca yıkılsın" gibi cümleler yukarıdaki satırların
birkaçına birden uyar. `AskUserQuestion` ile netleştir:

- Yıkılan şey **haritanın parçası** mı (bina, duvar, kule), yoksa
  **script'le spawn edilen bir prop** mu? → harita ise RayFire, prop ise `/yed`.
- Yıkımdan sonra **kalıcı bir enkaz** kalacak mı, yoksa parça kaybolacak mı?
  → kalıcı enkaz gerekiyorsa RayFire (durum ymap'i bunun için var).
- **Herkes aynı anda mı** görecek? → RayFire imap takası sunucu tarafından
  senkronlanır; `PlayEntityAnim` istemci başınadır.
- Yıkım sırasında **üstünde yürünebilecek mi**? → hayır. RayFire'da
  animasyon sırasında collision **yoktur**, bu sistemin doğasıdır. Bu
  gerekiyorsa beklentiyi baştan düzelt.

Seçim yapılmadan Blender açma.

---

## ZİHİNSEL MODEL

`des_X` diye bir arketip **yoktur**. `compositeEntityTypes` bir yönetmendir:
`StartImapFile` kapanır → `AnimatedModel` drawable'ını **motor yaratır** →
klip oynar → drawable silinir → `EndImapFile` açılır.

Görünen **üç ayrı varlıktır**: sağlam prop, enkaz prop, aradaki animasyonlu
drawable. Tek objeyi hem animasyonlu hem collision'lı yapmaya çalışma.

---

## KADRO

| dosya | rol |
|---|---|
| `des_X_root.ydr` | animasyonlu skinned mesh — **collision YOK** |
| `des_X_saglam.ydr` + gömülü bound | sağlam hal |
| `des_X_enkaz.ydr` + gömülü bound | enkaz hali |
| `des_X.ycd` | klip adı = model adı = arketip adı |
| `des_X.ytyp` | arketipler + `compositeEntityTypes` |
| `des_X_start/_end/_placer.ymap` | üç durum |

---

## ÜÇ SESSİZ BAĞ — kontrol etmeden "oldu" deme

1. **`.ycd` `BoneId` = iskelet `Tag`.** Eşleşmezse kanal düşer, kemik rest'te
   kalır, hata çıkmaz. Sollumz'un otomatik tag formülü vanilla tag'leri
   üretmez → `use_manual_tag = True` + `manual_tag`.
2. **Klip adı = model adı = arketip adı.** `.yed` reçetesindeki *"aynı
   olmamalı"* kuralı **buraya ait değildir**; onu buraya taşımak bir kez
   tur boyu yanlış teşhise yol açtı.
3. **bbox animasyonun tamamını kapsamalı.** Sollumz rest kutusunu yazar;
   bütün karelerde min/max ölçüp `.ydr` XML'ini yamala. Yoksa obje uzakta
   titrer ve kaybolur.

---

## SOLLUMZ YAMA LİSTESİ — export sonrası altısı da uygulanır

| # | Sollumz | olması gereken |
|---|---|---|
| 1 | `pack:/pack:/x.clip` | `pack:/x.clip` |
| 2 | `Unknown30 = 0` | `1` |
| 3 | `Tags`/`Properties` yok | `Properties` 1 Item (Int 32) |
| 4 | `Unknown10 = 0` | `1` |
| 5 | `BoneIds` Track 0+1 | Track 2 de (`StaticVector3 1,1,1`) |
| 6 | bbox = rest | animasyonun tam uzanımı |

Ayrıca: `ob.sz_lods.high.mesh = ob.data` atanmamışsa export
**"has no Sollumz materials!"** deyip drawable'ı komple atlar — materyal
oradadır, Sollumz onu LOD üzerinden okur.

`.ytyp`/`.ymap` binary'sini `xml_to_res.ps1` yazamaz →
`XmlMeta::GetData(doc, MetaFormat.RSC, folder)`.

---

## KAYIT

```lua
files { 'stream/des_X.ytyp' }
data_file 'DLC_ITYP_REQUEST' 'stream/des_X.ytyp'
```
Kaydolmazsa hem ymap entity'leri hem composite **sessizce** hiç oluşmaz.

---

## DOĞRULAMA — oyuna girmeden

Merdiven: `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/oyuna-girmeden-dogrulama.md`

```powershell
# klip kemikleri gercekten suruyor mu (Bag A + olu kuyruk)
& cw_anim_check.ps1 -Ycd <des_X.ycd> -Clip <des_X_root> -Tags @(<tag>,...)
```

Kapıyı **dağıtılmış** dosyada çalıştır, üretim klasöründe değil.
Bağ A/B/C üçü de XML geri okumasıyla denetlenir.

Oyunsuz görülemeyenler: composite durum makinesi, imap takası,
`punchIn/Out` zamanlaması, streaming, collision davranışı.

**Test öncesi kullanıcıya hatırlat: sunucudan tamamen ÇIKIP yeniden
bağlanmak gerekiyor — restart yetmez.**
