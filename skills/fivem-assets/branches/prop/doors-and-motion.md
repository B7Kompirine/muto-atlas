# Kapı açılmıyor / obje kımıldamıyor / kilit / koordinat

**Ne zaman okunur:** harita objesi hareket etmiyor, `AddDoorToSystem` tutmuyor, obje donuyor, kapı yanlış tanımlı, konumu config'e yazacaksın.
**When to read:** the door won't open, the object won't move, locking, coordinates, `specialAttribute` door table.
**Kaynak:** eski SKILL 'specialAttribute — KAPI TABLOSU', 'OBJE HAREKET ETTİRMENİN KATMANLARI', 'ARCHETYPE YANLIŞ TANIMLIYSA', 'Kök-kemik klipleri', 'KOORDİNAT' (2026-07) · **Ölçüm:** 316.975 arketip dağılımı; Fleeca oyunda
**Önce:** `_branch.md` · gövde › `trunk/flags.md` (`specialAttribute`), `trunk/tool-pitfalls.md` §1 · MLO içindeyse çözüm `branches/map/mlo-object-swap.md`

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" door  <ad>   # kapı gibi açılır mı
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" show  <ad>   # pivot, bbox, fizik, ytyp
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" where <ad>   # haritada kaç yerde
```

## specialAttribute — KAPI TABLOSU

316k archetype'ın dağılımından doğrulandı, tahmin değil:

| Değer | Anlam | Kapı sistemi çalışır mı |
|---|---|---|
| **7** | menteşeli kapı | ✅ evet — `AddDoorToSystem` + `DoorSystemSetDoorState` |
| **8** | sürgülü kapı | ✅ evet |
| **5** | garaj / rulo kapı | ✅ evet |
| **10** | kepenk / asansör kapısı | ✅ evet |
| **12** | demiryolu bariyeri | ✅ evet |
| **0** | kapı DEĞİL | ❌ hayır — kayıt olsa bile obje kımıldamaz |
| diğer | bitki, mobilya, trafik, SLOD... | ❌ hayır |

`specialAttribute = 0` ise:
1. Kapı sistemi **hiçbir şey yapmaz** — denemeye değmez.
2. Tek script-içi yol: `SetEntityHeading` ile transform'u yeniden yazmak.
   Doğru görünmesi için pivot'un kenarda olması gerekir → `show` çıktısındaki
   bbox yorumu bunu söyler.
3. Kalıcı doğru çözüm: ytyp override ile `specialAttribute = 7` vermek.

## OBJE HAREKET ETTİRMENİN KATMANLARI

Bir dünya objesini oynatmak isterken sırayla doğrula:

1. **Sahiplik** — `SetEntityAsMissionEntity` + `NetworkRequestControlOfEntity`.
   Kontrol alınmadan `FreezeEntityPosition` / `SetEntityCoords` /
   `SetEntityHeading` **sessizce yok sayılır**. En sık atlanan adım budur.
2. **Fizik** — `FreezeEntityPosition(false)` tek başına yetmez; obje
   "hareketsiz" işaretliyse `SetEntityDynamic(true)` + `ActivatePhysics()` gerekir.
3. **Menteşe** — kapı sistemi ancak `specialAttribute` uygunsa devreye girer.
4. **Senkron** — harita objeleri networked DEĞİLDİR. Durum server'da tutulup
   her client kendi kopyasına uygular; yoksa sadece sende hareket eder.

## ARCHETYPE YANLIŞ TANIMLIYSA — ytyp override

Bir obje ytyp'te yanlış tanımlıysa (kapı olması gereken şey
`specialAttribute=0`) doğru çözüm script değil, ytyp düzeltmesidir:

```bash
powershell -File "${CLAUDE_PLUGIN_ROOT}/scripts/make_ytyp_override.ps1" `
    -Models v_ilev_gb_teldr -SpecialAttribute 7 `
    -YtypName <benzersiz_ad> -OutFile "<resource>\stream\<ad>.ytyp"
```

Kaynak archetype'ı RPF'ten okur, **bütün alanları birebir kopyalar**, sadece
istenen değeri değiştirir — uydurma alan olmaz. Çıktı `stream/` klasörüne
konur ve fxmanifest'te `data_file 'DLC_ITYP_REQUEST'` ile bildirilir.

Uyarı: aynı archetype'ı kullanan **her yer** etkilenir (Fleeca örneğinde 6
şube). Etki alanını `assetdb.py where <model>` ile önceden gör.

## Kök-kemik klipleri donmuş objede çalışmaz

Bir klip sadece tag 0'ı oynatıyorsa objenin **kendisini** taşır, iç
parçasını değil. `FreezeEntityPosition(obj, true)` bunu tamamen engeller:
klip oynar, `PlayEntityAnim` true döner, ekranda hiçbir şey olmaz.
Kök hareketli klip oynatmadan önce dondurmayı kaldır.



## KOORDİNAT — config'e sabit yazmadan önce

Bir prop/kapı için koordinat gerekiyorsa **oyuncudan isteme, indeksten al**:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" where v_ilev_gb_teldr
# -> 6 benzersiz konum (6 Fleeca şubesi)
```

İki şeye dikkat:

1. **Aynı prop haritada birden fazla yerde olabilir.** Fleeca vezne kapısı 6
   şubede var. Config'i tek koordinata göre kurma; ya hepsini yaz ya da
   oyuncunun etrafında ara.
2. **`[mlo]` işaretli konumlar bir iç mekâna aittir** — o prop ancak o MLO
   yüklüyken vardır. `near` çıktısındaki köşeli parantez hangi MLO olduğunu
   söyler.

## Harita objesinin çarpışmasını kaldırma

`SetEntityCollision(mapObj, false, false)` **güvenilir değil** — obje görünmez olur ama çarpışma yerinde kalır. Doğrusu `CreateModelHide(x,y,z,r,hash,true)`; geri almak `RemoveModelHide` (unutulursa obje bir daha gelmez). Hide çağrısı handle'ı geçersizleştirir, çarpışmayı **önce** kapat.
