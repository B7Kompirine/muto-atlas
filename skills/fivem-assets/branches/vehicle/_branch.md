# Araç — dal kuralları

Komut: `/vehicle` · Klasör: `branches/vehicle/`
Anahtar kelimeler: araç, araba, otomobil, araba kapısı, araba kemiği, vehicle, handling, handlingId, handling.meta, modkit, SetVehicleModKit, extra, SetVehicleExtra, araç sınıfı, koltuk, araç kemiği, door_dside_f, kapı kemiği, cam, kaput, siren, egzoz, wheel, livery, debadger, tint
**Bu dala ne düşer:** **Araç** — kemiği, handling'i, modkit/extra'sı, künyesi. Sınır: aracın dokusu/boyası → `/look`.

> Yukarıdaki anahtar kelimeler **hızlandırıcıdır, kapsayıcı değildir.** Bir kelime listede yoksa
> yönlendirme durmaz — bu tanıma bakılır. *“kepenk”* listede olmasa da bir kapı nesnesidir.

**What belongs here:** **A vehicle** — its bones, handling, modkit/extras, spec sheet. Boundary: the vehicle's texture or paint → `/look`.
**Keywords (EN):** vehicle, car, handling, handlingId, handling.meta, modkit, SetVehicleModKit, extra, SetVehicleExtra, vehicle class, seat, vehicle bone, door_dside_f, door bone, window, hood, siren, exhaust, wheel, livery, debadger, tint


## Bu dalda her yaprakta geçerli olan

⚠️ **İnce dal.** Araç modelleme/kurulum videoları Sollumz çıkarımından **istek üzerine ayıklandı**; atlas'ta araç için ölçülmüş olan
iki şey var: kemik adları ve araç künyesi. Bir araç üretimi yapılırsa ölçümler buraya gelir.

- **Araç kemiklerinde AD sabittir, %100 tag-kararlı** (193 ad: kapı/cam/kaput/tekerlek/ışık/motor/egzoz/koltuk/mod/extra/siren) —
  adı birebir kopyala, `GetEntityBoneIndexByName` ile bul. Silah ve ped'de tersi olabilir → `trunk/bone-tags.md` §1 karar kuralı.
- **Künye sorgulanır, tahmin edilmez:** `assetdb.py vehicle <ad>` → `handlingId`, modkit, extra, sınıf, koltuk (921 araç).
- Dış araç bir sayı/tablo getirdiyse (Five Toolkit debadger, tint) **iddiadır** → `sources/external-tools.md` etiket sistemi.
- Araç dokusu/shader'ı (`vehicle_paint*`, livery) için doku kuralları `branches/look/_branch.md`; araç collision bayrakları `trunk/flags.md` §8.

## Yapraklar

| istenen | dosya | durum — kaynak |
|---|---|---|
| Kemik / mod / extra / handling sorgusu | bones-and-mods.md | ölçüldü — trunk/kemik-tag §2 · assetdb vehicle |
| Dış araç — debadger, ayıklanan araç videoları | external-tools.md | dış kaynak — trunk/dis-arac §1k · sollumz-discord (ayıklandı) |

## Gövdeye bakılacaklar
- `trunk/bone-tags.md` §2 (tam tablo), §6 (kararsız adlar) · `trunk/flags.md` §8 collision · `sources/external-tools.md` §1k
- `trunk/verification-ladder.md` — iskelet/künye geri okuma
