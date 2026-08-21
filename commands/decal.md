---
description: Decal work - runtime marks (AddDecal), map-embedded decal shader, or projecting decal geometry onto a surface in Blender
argument-hint: [ne olacak — "duvara graffiti" / "yere kan izi" / "merdivene leke"]
allowed-tools: Bash(python:*), Bash(powershell:*), Read, Edit, Write, Glob, Grep, AskUserQuestion
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

## ÖNCE OKU

`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/decal-isik-timecycle-bulgulari.md`

Sayıların hepsi ölçümdür. Aracın kendisi bu depoda değil — **MutoLab**
Blender eklentisinde (`ops/decal`, `panels/decal.py`, `props/decal.py`).
Bu belge o aracın sözleşmesidir; araç değişse de ölçüt burada kalır.

---

## ADIM 0 — HANGİ SİSTEM? Kod yazmadan seç

"Şuraya leke/graffiti/kan koyalım" **üç ayrı iştir** ve hiçbiri diğerinin
yerine geçmez:

| istenen | sistem |
|---|---|
| çalışma anında iz — kan, lastik, mermi deliği, sızıntı, ayak izi | `AddDecal` (script) |
| haritaya **kalıcı gömülü** — graffiti, logo, tabela, yol çizgisi | `decal.sps` shader + render bucket **2** |
| bir modelin yüzeyine **geometri yansıtma** (Blender'da üretim) | projeksiyon decal — MutoLab |

Belirsizse `AskUserQuestion` ile netleştir:
- İz **kalıcı mı** (haritanın parçası) yoksa oyun sırasında mı oluşacak?
- **Herkes aynı anda mı** görecek? → `AddDecal` istemci başınadır.
- Yüzey **düz mü**, kıvrık mı, ince boru/ızgara mı? → sonuncusunda projeksiyon
  çalışmaz, orası boyama işidir.

---

## 1. ÇALIŞMA ANINDA İZ — `AddDecal`

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" decal kan
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" decal <mermi|ayak|yanık|yağ|benzin>
```

194 tipli tablo. Tipi **tahmin etme**, tablodan seç.

## 2. HARİTAYA GÖMÜLÜ DECAL — shader tarafı

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" shader decal
```

Render bucket **2**. `decal.sps` harman katsayısı olarak **`Color 1`'in
alfasını** okur — vertex rengi yanlışsa decal ya hiç görünmez ya da yarı
saydam kalır.

## 3. YÜZEYE GEOMETRİ YANSITMA — üç yöntem, üç sert sınır

| yöntem | ne zaman | sınırı (ölçüldü) |
|---|---|---|
| ışın ızgarası | düz, ışına dik yüzey | **ışına paralel yüzeye asla vuramaz** — merdivende 4096 ışının 2732'si, iç köşede 1344'ü boşa gitti |
| kutu (triplanar) | sarma gereken yüzey | silindirde 39 normal bandı verir (ışın 2) ama desen **köşede yeniden başlar** |
| tek eksenli kırpma | tek yöne bakan düz yüzey | ekseni **her yüz için `max()` ile seçme** — yüzey normalleri eksenle hizalı değilse sonuç boş çıkar |

⛔ **`bmesh.ops.bisect_plane` açık geometride kırpmaz, YÜZ SİLER** — altı
çağrı boyunca yüz sayısı 637'de sabit kalırken alan 3.553 → 0.941 m² düştü.
Boolean INTERSECT de güvenilmez (aynı duvarda biri hiç kırpmadı).
**Doğrusu Sutherland–Hodgman**: çözücüsü yok, başarısızlık modu yok.

İnce boru / ızgara / karmaşık kıvrım → **hiçbiri çalışmaz**. Orada yol
yüzey kopyası + elle alfa boyamadır (Surface Painter).

---

## DECAL GÖRÜNMÜYORSA — sırayla, hepsi sessiz

1. **UV katmanının ADI** materyalinkiyle aynı mı — `"UVMap 0"`.
2. Hedefin **eski UV katmanı** silindi mi (geometri kopyalanırken gelir).
3. **`Color 1` alfası 1.0 mı** — kopyalanan geometri hedefinkini miras alır,
   ölçülen vakada 0.498 çıktı ve decal yarı saydam kaldı.
4. **Alfa haritasında satır 0 görüntünün ALTIDIR** — ters okunursa maske
   baş aşağı uygulanır.
5. Alfa elemesi fazla agresif mi — tamamen şeffaf olmayan pikseller de
   eleniyorsa desen delinir.

## BLENDER API TUZAKLARI — bu işte yakalananlar

- ⛔ **`object.dimensions` DÖNÜŞÜ İÇERMEZ** (yerel bbox × ölçek). Döndürmek
  onu değiştirmez → "en uzun ekseni yatır" mantığı sessizce hiçbir şey yapmaz.
  Dünya bbox'ı kullan.
- ⛔ **Gizli objede `select_set()` sessizce çalışmaz** — export
  "successfully" der, dosya **0 bayt** çıkar (yedi objeden beşi böyle yazıldı).
- `scene.ray_cast` **viewport'u** kullanır; bakış ışını gerçek göz konumundan
  atılır ve tam dik yüzün dot'u **0.000**'dır.
- Edit Mode'a girince **önceki seçim geri gelir**.

## SONUCU SUNARKEN

- ⛔ **"Obje oluştu, sayılar makul" ÇALIŞIYOR DEMEK DEĞİLDİR.** Bu alandaki
  sessiz hataların hepsi bu kalıptaydı: yüz sayısı yüzlerce, alan makul,
  hata yok, **ekranda hiçbir şey yok.**
- ⛔ **Ekran görüntüsü ölçüm değildir.** Bir şeyin bozuk olduğunu söylemeden
  önce **oku** — pikseli, dosyayı, geri okumayı.
- **Tek sentetik noktada çalışması yeterli değildir** — düzeltmeyi
  kullanıcının gerçek geometrisinde dene, sonra "oldu" de.
- Asset değişti → sunucudan **çıkıp yeniden bağlan**; restart yetmez.
