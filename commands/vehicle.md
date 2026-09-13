---
description: Vehicle branch - vehicle bone names (stable), handling/modkit/extra lookup, external vehicle tools
argument-hint: <ne olacak — "kapı kemiği" / "handlingId" / "modkit">
allowed-tools: Bash(python:*), Read, Glob, Grep
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `scripts/assetdb.py`'yi içeren muto-atlas klasörü).

## Bu bir DAL komutudur (ince dal)

1. **Önce dalı oku:** `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/branches/vehicle/_branch.md` — araç kemiklerinde ad sabittir.
2. Sorgula: `assetdb.py vehicle <ad>` · `bones <model>`. Kemik adı tahmin edilmez, `trunk/bone-tags.md` §2'den kopyalanır.
3. Araç modelleme/kurulum ölçülmedi — kullanıcıya söyle; topluluk videoları yerel çıkarımda.
