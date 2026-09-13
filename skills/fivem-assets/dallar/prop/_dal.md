# Prop — dal kuralları

Komut: `/prop` · Klasör: ``
Anahtar kelimeler: prop, obje, kapı, kapı açılmıyor, kilit, kımıldamıyor, freeze, AddDoorToSystem, specialAttribute, pivot, bbox, physicsDictionary, fragment, kırılabilir, yft, ytyp adı, hash_, CreateObject, yuva yüksekliği, DUI, objede ekran, ATM, keypad, monitör, ele tutturma, PH_R_Hand
**Bu dala ne düşer:** **Tek bir taşınabilir / etkileşilebilir nesne** — kapısı, fiziği, kırılması, üstündeki ekran, ele tutturulması. Sınır: nesnenin **hareket etmesi** (animasyon) bu dalın dışındadır · dünyaya toplu yerleşimi → `/map`.

> Yukarıdaki anahtar kelimeler **hızlandırıcıdır, kapsayıcı değildir.** Bir kelime listede yoksa
> yönlendirme durmaz — bu tanıma bakılır. *“kepenk”* listede olmasa da bir kapı nesnesidir.

**What belongs here:** **A single portable / interactable object** — its door, physics, breaking, the screen on it, attaching it to a hand. Boundary: the object **moving** (animation) is outside this branch · placing it in the world → `/map`.
**Keywords (EN):** prop, object, door, door won't open, lock, won't move, freeze, AddDoorToSystem, specialAttribute, pivot, bbox, physicsDictionary, fragment, breakable, yft, ytyp name, CreateObject, DUI, screen on object, ATM, keypad, monitor, attach to hand, PH_R_Hand


## Bu dalda her yaprakta geçerli olan

Ölçüm kaynakları: 316.975 arketip, Fleeca MLO kapıları, 5 ekranlı model RPF'ten.

### Önce sorgula — kod yok
- **`assetdb.py show <ad>` / `door <ad>` / `where <ad>`.** Kapı mı, pivot nerede, fizik var mı, kaç yerde var.
  Fleeca vezne kapısı için dört native sırayla denendi; cevap tek satırdı: `specialAttribute = 0` → kapı değil.
- **`specialAttribute` kapı tablosu:** 7 menteşeli · 8 sürgülü · 5 garaj · 10 kepenk · 12 bariyer → kapı sistemi
  çalışır; **0 = kapı DEĞİL**, kayıt olsa bile kımıldamaz. Tam 21 değer `govde/bayraklar.md`.
- **Hareket dört katmandır, sırayla:** sahiplik (`NetworkRequestControlOfEntity` yoksa `Freeze/SetCoords`
  sessizce yok sayılır) → fizik (`SetEntityDynamic` + `ActivatePhysics`) → menteşe (`specialAttribute`) →
  senkron (harita objesi networked değil; durum sunucuda).
- **Prop iskeleti yoksa** `PlayEntityAnim` ve bone-index işlemleri o modelde çalışmaz (`assetdb.py bones`).

### Üretirken
- **Pivot X/Y merkez, Z taban** (`bbMin.z = 0`); uzun parça `yatik` + 90°. **`physicsDictionary` asla 0**
  (model görünür, içinden geçilir) — kendi prop'unda kendi ad hash'i.
- **bbox animasyonun tamamını kapsar, iki yerde** (`.ydr` + ytyp); yoksa uzakta titrer/kaybolur.
- **ytyp'nin kendi `<name>`'i benzersiz** (aynı adlı üç ytyp'den yalnız biri yüklendi); CodeWalker XML'de
  `hash_XXXXXXXX` → stream dosya adlarının joaat'iyle çöz.
- Sollumz: `bpy.data.objects.new` ile obje `sollum_type` taşımaz → dosya hiç yazılmaz; `sz_lods.high.mesh`;
  `holes_fill` UV (0,0) örnekler; ölçek en **büyük** eksene → `govde/arac-tuzaklari.md` §1-2.
- **Fragment kök grup tuzağı:** `parentIdx=255` grup entity gövdesidir, kemiği takip etmez → en az iki grup,
  hareketli parça çocuk grupta. Bound→kemik bağı **`COPY_TRANSFORMS` constraint**'tir, ad eşleşmesi değil.

### Oyun içi yerleşim
- **`CreateObject` bound tabanına, `CreateObjectNoOffset` origin'e koyar**; bayat bound objeyi havaya kaldırır —
  bound'u görselden yeniden üret.
- **Yuva/raf yüksekliği tahmin edilmez, ölçülür** — modelin en geniş yatay yüzeyi (+Z normalli yüz alanı z'ye göre).
- **Ele tutturma:** `PH_R_Hand` 28422 · `PH_L_Hand` 60309 · `SKEL_L_Hand` 18905; burger klibi **sol** elle yer.
  Ofset tablosu `rotationOrder`'ıyla taşınır (dpemotes 1 · ox_lib/qb 0) → `ele-tutturma.md`.
- ⛔ **Prop'a kemik eklemek hizalama vermez** — GTA takılı objeyi ORIGIN'inden konumlandırır. Tutma hizalaması **modele pişirilir**:
  ORIGIN = tutma noktası, ileri +Y, attach `(0,0,0)`; ölçek de pişirilir (prop çalışma zamanında ölçeklenemez).
- **Yetim süpürücü sergi/teşhis objelerini de siler** → beyaz liste; "modeller kayboluyor" teşhisinde önce kendi kodun.
- Harita objesinde `SetEntityCollision(false)` güvenilir değil → `CreateModelHide`. Donmuş objede kök-kemik klibi oynamaz.
- **Script'le spawn edilen obje harita objesi değildir**; MLO içine ymap ile prop konmaz → `dallar/map/_dal.md`.

### Ekran / etkileşim
- **Üç render yolu, seçimi veri belirler:** gerçek ekran dokusu varsa `AddReplaceTexture` (materyal bazlı ve **GLOBAL** —
  3 ATM aynı sayfayı gösterir), yoksa dünya quad'ı, hareketli entity'de `AttachPanelToEntity`. Sor: `screentex.ps1 -Model <ad>`.
  Ekran = `emissive*` shader, doku modele gömülü → `origTxd` = model adı; ytyp `textureDict` ekran sözlüğü **değil**.
  Keypad ve CCTV'nin ekran dokusu **yok**.
- **DUI/NUI istemci tarafıdır, senkronize değil** — şifre/kod karşılaştırması sunucuda.

## Yapraklar

| istenen | dosya | durum — kaynak |
|---|---|---|
| Kapı açılmıyor / obje kımıldamıyor / kilit / koordinat | kapi-ve-hareket.md | ölçüldü — eski SKILL kapı/hareket/override/koordinat |
| Kırılabilir / kemikli prop (fragment) | fragment.md | ölçüldü — eski SKILL fragment üretimi |
| Objenin üstünde canlı ekran (DUI) | dui-ekran.md | ölçüldü — 3dnui-dui-panel |
| Prop'u kemiğe tutturma — ofset tablosu taşıma, rotationOrder, canlı ofset editörü | ele-tutturma.md | okundu + sayısal — pg_attachproptoplayereditor, dpemotes, ox_lib, qb progressbar |

## Gövdeye bakılacaklar
- `govde/bayraklar.md` — `specialAttribute` 21 değer, archetype bayrakları, extension tipleri (partikül, ladder, buoyancy)
- `govde/dogrulama-merdiveni.md` — prop'u oyuna sokmadan: export boyutu, bound, ytyp geri okuma
- `govde/arac-tuzaklari.md` §1 Sollumz, §2 Blender (transform pişir), §6 FiveM (`CreateModelHide`, handle önbelleği)
- Prop'un ışığı → `dallar/look/isik.md`
- Hazır örnek / araç arıyorsan (3 parçaya ayrılan `yft.blend`, `blender_rayfirev`, drawable import temizliği, ⛔ boş `.col` = anında crash) → `kaynaklar/topluluk-kaynak.md` §5, §8 — **kaynak notu, kural değil.**
