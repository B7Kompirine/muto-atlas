---
description: Setup - asks for your paths, builds all data layers from your own install
argument-hint: "[sunucu resources klasörü]"
allowed-tools: Bash(python:*), Bash(powershell.exe:*), Read, Glob, AskUserQuestion
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `scripts/assetdb.py`'yi içeren muto-atlas klasörü).

## ADIM 1 — Durumu gör

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --plan
```

Çıktının başındaki üç satıra bak: `GTA V`, `CodeWalker`, `sunucu`.
Üçü de doluysa ADIM 3'e geç.

## ADIM 2 — Eksik yolu KULLANICIYA SOR

⛔ **Tahmin etme, arama yapıp durma, "muhtemelen şuradadır" deme.**
Bu aracı kullanan herkeste GTA V ve CodeWalker vardır; eksik olan veri değil
**yol bilgisidir.** `AskUserQuestion` ile sor:

- **GTA V klasörü** — `x64a.rpf`, `common.rpf` gibi dosyaların olduğu yer.
  Yaygın: `C:\Program Files\Epic Games\GTAV`,
  `C:\Program Files\Rockstar Games\Grand Theft Auto V`,
  `...\Steam\steamapps\common\Grand Theft Auto V`
- **CodeWalker.Core.dll** — CodeWalker'ı açtığın klasörde, `CodeWalker.exe`'nin
  yanında durur. Sürüm klasörü olabilir (`CodeWalker30_dev46`).
- **FiveM sunucu `resources` klasörü** *(isteğe bağlı ama çok değerli)* —
  framework indeksi buradan üretilir; kurulu olmayan kaynağa giden
  export/event çağrılarını yakalar.

## ADIM 3 — Kur

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --save \
  --gta "<GTA V klasörü>" \
  --codewalker "<yol>\CodeWalker.Core.dll" \
  --resources "<sunucu>/resources"
```

`--save` yolları `data/config.json`'a yazar; bir daha sorulmaz.
(`data/` `.gitignore`'da — kişisel yol bilgisi repoya girmez.)

Ağır katmanlar **varsayılan olarak** kurulur. Birkaç dakika sürer
(klipler ~3 dk, iskeletler daha uzun). Atlamak için `--hafif-only`.

## ADIM 4 — Doğrula

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" stats
```

Her katmanın VAR/YOK durumunu, boyutunu ve dump sürümünü basar.
`stats` **asla** EXIT 2 dönmez — eksik katman varken de çalışır, çünkü
"ne kurulu?" sorusunun cevabı odur.

## ⛔ Kurulum sonrası kullanıcıya söyle

Eksik kalan katman varsa **hangi sorguların çalışmayacağını** söyle.
Çıkış kodları:

| kod | anlam |
|---:|---|
| 0 | bulundu |
| 1 | ad otoritede yok |
| 2 | katman kurulu değil — sonuç hakkında hiçbir şey iddia edilemez |
| 3 | iç hata (bozuk dosya) |

`2`'yi `1` sanmak, veri eksikliğini varlık yokluğu sanmaktır — bu plugin
tam olarak onu önlemek için var.
