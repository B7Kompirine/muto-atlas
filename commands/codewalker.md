---
description: Where CodeWalker.Core.dll is - show it, or set a new path
argument-hint: [path]  ·  omit to just show it
allowed-tools: Bash(python:*), Read
---

Kullanıcının sorgusu: `$ARGUMENTS`

```bash
# nerede?
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path codewalker

# ayarla
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path codewalker "$ARGUMENTS"
```

`$ARGUMENTS` boşsa **göster**, bir yol verilmişse **ayarla**.

`CodeWalker.Core.dll` plugin'in en kritik dış bağımlılığıdır: **30 betik**
buna bağlı (`.ydr/.yft/.ycd` çözümü, RPF çıkarma, XML turu, ışık editörü).
Hepsi aynı kütüğü (`data/config.json`) okur — bulunamıyorsa çözüm burayı
ayarlamaktır, betikleri düzenlemek değil.

## Sonucu sunarken

- Yol **diskte doğrulanır**; olmayan yol kabul edilmez.
- "config'de yazılı ama diskte yok" ile "hiç ayarlı değil" **farklı**
  durumlardır, ayrı raporlanır.
- Bulunamadıysa nerelere bakıldığını da göster, sonra ayarlamayı öner.
- Sürüm önemli: plugin `CodeWalker30_dev46` ile ölçüldü. Farklı bir sürüm
  veriliyorsa API imzaları değişmiş olabilir — bir betik patlarsa ilk şüpheli budur.
