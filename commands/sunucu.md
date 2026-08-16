---
description: FiveM sunucusunun resources klasörü nerede — göster ya da yeni yolu ayarla
argument-hint: [yol]  ·  boş bırak = nerede olduğunu söyle
allowed-tools: Bash(python:*), Read
---

Kullanıcının sorgusu: `$ARGUMENTS`

```bash
# nerede?
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" yol sunucu

# ayarla
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" yol sunucu "$ARGUMENTS"
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
