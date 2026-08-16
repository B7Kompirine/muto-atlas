---
description: Where your FiveM server resources folder is - show it, or set a new path
argument-hint: [path]  ·  omit to just show it
allowed-tools: Bash(python:*), Read
---

Kullanıcının sorgusu: `$ARGUMENTS`

```bash
# nerede?
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path server

# ayarla
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path server "$ARGUMENTS"
```

`$ARGUMENTS` boşsa **göster**, bir yol verilmişse **ayarla**.

Framework indeksi (QBCore/Qbox/ESX/ox export ve event'leri) bu klasörden
üretilir — eksik export ve olmayan event çağrıları böyle yakalanır.
Yol `.../txData/<sunucu>.base/resources` biçimindedir.

## Sonucu sunarken

- Klasör **diskte doğrulanır**.
- Sunucu yolu değiştiyse framework indeksi bayattır: `build_framework.py`
  ile yenile, yoksa "bu export yok" uyarıları yanlış çıkar.
- Otomatik aday yoktur — sunucu klasörü her kurulumda farklı yerdedir,
  bu yüzden bir kez elle verilir.
