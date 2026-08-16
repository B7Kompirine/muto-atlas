---
description: GTA V kurulum klasörü nerede — göster ya da yeni yolu ayarla
argument-hint: [yol]  ·  boş bırak = nerede olduğunu söyle
allowed-tools: Bash(python:*), Read
---

Kullanıcının sorgusu: `$ARGUMENTS`

```bash
# nerede?
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" yol gta

# ayarla
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" yol gta "$ARGUMENTS"
```

`$ARGUMENTS` boşsa **göster**, bir yol verilmişse **ayarla**.

Veri katmanlarının tamamı (arketipler, dünya yerleşimleri, klipler,
iskeletler, ışıklar, timecycle) **kullanıcının kendi kurulumundan** üretilir.
Bu klasör yanlışsa `/asset-build` çalışmaz.

Rockstar / Epic / Steam kurulumlarının hepsi farklı yerdedir; otomatik
arama beşini dener, bulamazsa buradan verilir.

## Sonucu sunarken

- Klasör **diskte doğrulanır**; olmayan yol kabul edilmez.
- Yol değiştiyse **üretilmiş katmanlar bayattır** — `/asset-build` ile
  yeniden üretmek gerekir; sessizce eski indeksle devam etme.
- `data/` .gitignore'da: bu yol asla repoya girmez.
