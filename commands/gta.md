---
description: Where the GTA V install folder is - show it, or set a new path
argument-hint: [path]  ·  omit to just show it
allowed-tools: Bash(python:*), Read
---

Kullanıcının sorgusu: `$ARGUMENTS`

```bash
# nerede?
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path gta

# ayarla
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path gta "$ARGUMENTS"
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
