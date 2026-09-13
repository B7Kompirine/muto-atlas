# Prop'u kemiğe tutturma — ofset tablosu, rotationOrder, canlı ayar editörü

**Ne zaman okunur:** prop'u ped kemiğine takacaksın (el · ön kol · sırt), başka bir script'in ofset tablosunu (dpemotes, ox_lib, qb progressbar) taşıyacaksın, ofseti oyunda canlı ayarlayan bir editör yazacaksın; "orada düzgündü, bizde yamuk".
**When to read:** attaching a prop to a ped bone, porting an offset table between scripts (dpemotes, ox_lib, qb progressbar), or writing a live offset editor; "it looked right there, it is crooked here".
**Kaynak:** PERPGamer/pg_attachproptoplayereditor `client.lua` (GPL-3.0, son push 2022-11-03; listelenen 19 fork'ta yeni commit yok) · citizenfx/natives `ATTACH_ENTITY_TO_ENTITY`, `GET_ENTITY_ROTATION` · andristum/dpemotes `Client/Emote.lua:260` + `AnimationList.lua` · overextended/ox_lib `progress.lua:66` · qbcore-framework/progressbar `client.lua:74` (2026-09-10) · **Ölçüm:** kaynak okuma (4 script) + Euler sırası sayısal karşılaştırması (4 açı üçlüsü, 2026-09-10). **Oyun testi yok.**
**Önce:** `_dal.md` (el tag'leri, ORIGIN = kabza sözleşmesi) · gövde › `govde/kemik-tag.md` (tag ≠ indeks)

---

## 1. Çağrı — kuyruğun anlamı

```lua
AttachEntityToEntity(prop, ped, GetPedBoneIndex(ped, tag), x, y, z, rx, ry, rz,
    true,   -- p9: etkisiz
    true,   -- useSoftPinning
    false,  -- collision: false → prop ped'i itmez
    true,   -- isPed: false iken pitch çalışmaz, roll yalnız negatifte
    1,      -- rotationOrder: rx/ry/rz'nin uygulanma SIRASI (0-5)
    true)   -- syncRot: false → entity rotasyonu yok sayılır
```

- Bakılan dört script'te kuyruk `true, true, false, true, N, true` — **yalnız `rotationOrder` değişiyor**.
- Geçersiz bone index → prop entity'nin **merkezine** takılır, hata yok (resmi belge).
  Oyundaki görünümü: gövdenin yanında havada → `dallar/map/mlo-prop.md`.

## 2. ⛔ Ofset tablosu `rotationOrder`'ıyla birlikte taşınır

| kaynak | `rotationOrder` |
|---|---|
| dpemotes `PropPlacement` · pg editörü | **1** (`ROT_YZX`) |
| ox_lib `lib.progressBar` prop | `prop.rotOrder or 0` → varsayılan **0** (`ROT_ZYX`) |
| qb progressbar | **0**, sabit, alan yok |

Hangi açılarda fark eder (iki rotasyon matrisinin en büyük eleman farkı):

| (rx, ry, rz) | 0 ↔ 1 | 0 ↔ 2 |
|---|---|---|
| (−50, 16, 60) | 0,18 **farklı** | 0,18 **farklı** |
| (−50, 0, 60) | 0 | 0 |
| (−50, 16, 0) | 0 | 0,21 **farklı** |
| (0, 16, 60) | 0,24 **farklı** | 0 |

- **0 ↔ 1** yalnız `ry` **ve** `rz` ikisi de ≠ 0 iken ayrışır; **0 ↔ 2** yalnız `rx` **ve** `ry` ≠ 0 iken.
  Tek eksenli açı her sırada aynıdır — "bazı prop'lar doğru, bazıları yamuk" belirtisi budur.
- Somut: ölçülen bir burger ofseti `(0.13, 0.05, 0.02) / (−50, 16, 60)` @ 18905 dpemotes'un
  **birebir** değeridir (sıra 1). `lib.progressBar`'a `rotOrder = 1` verilmeden konursa yön değişir
  (matematik; oyunda bakılmadı). ox_lib'in ayrıca `rotOrder` alanı açması farkın oyunda görüldüğüne işaret, kanıt değil.
- Taşırken: hedefte sıra seçilebiliyorsa kaynağın sırasını ver; seçilemiyorsa (qb) açıyı yeniden ayarla.

## 3. Canlı ofset editörü

pg editörünün çalışan yolu: `/ptpeditor <tag> <model>` → `DisableControlAction` ile tuşları al, her
değişimde `DetachEntity` + aynı `AttachEntityToEntity`. Yardım metnindeki `~INPUT_CELLPHONE_LEFT~` gibi
token, oyuncunun **kendi tuş atamasının** simgesini çizer.

Aynı kodun 2022 kusurları — kendi editörünü yazarken:
1. **Konum ve açı tek adımı paylaşıyor** (0,01): açı 0,01°/kare → 60 fps'te 90° ≈ 150 s; konum ise basılı
   tutunca 60 cm/s. Ayrı adım: ~0,005 m ve ~1°.
2. **Adım kare başına** (`IsDisabledControlPressed` her kare ekler) → hız FPS'e bağlı. `GetFrameTime()` ile çarp.
3. **Adımın alt sınırı yok** → 0'da tuşlar donar, negatifte ters çalışır.
4. **Aç/kapa bayrağı doğrulamadan önce çevriliyor** → geçersiz modelli denemeden sonra ilk geçerli komut
   editörü açmaz, ikincisi açar. Bayrağı başarılı başlangıçta çevir.
5. **Sonuç kayboluyor:** çıkışta obje silinir, sayılar yalnız ekrandaydı. Çıkışta hedef satırı `print` et —
   tag, 6 değer **ve `rotationOrder`**.
6. **Klip oynamıyor:** ofset kemik uzayında pozdan bağımsızdır ama kavrayış ve hangi elin tuttuğu klibe
   bağlıdır (burger klibi **sol** el). Hedef klibi döngüde oynatırken ayarla.
7. **Editör objesi ağda** (`CreateObject(..., true, true, true)`): ayar sırasında herkes görür.
   Ayar aracında `isNetwork = false`.
