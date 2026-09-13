---
description: Prop branch - doors and movement, fragments, live screens on objects (DUI), attaching props to a hand
argument-hint: <ne olacak — "kapı açılmıyor" / "ATM'ye ekran" / "kırılabilir prop" / "ele tutturma">
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep, AskUserQuestion
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `scripts/assetdb.py`'yi içeren muto-atlas klasörü).

## Bu bir DAL komutudur

1. **Önce dalı oku:** `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/branches/prop/_branch.md`
   — `specialAttribute`, hareketin dört katmanı, pivot/bbox/physicsDictionary, `CreateObject` vs `NoOffset`, ekranın üç yolu.
2. Argümandan **tek yaprağı** seç: kapı/hareket · fragment · DUI ekran · ele tutturma.
3. Kod yazmadan sorgula: `assetdb.py show <ad>` · `door <ad>` · `where <ad>` · `bones <ad>` · `screentex.ps1 -Model <ad>`.
4. Obje **MLO içindeyse** çözüm bu dalda değil: `branches/map/mlo-object-swap.md`.

## Sonucu sunarken
- `specialAttribute` değerini ve anlamını söyle; 0 ise kapı sistemini hiç önerme.
- Asset değişti → sunucudan çık, yeniden bağlan. Ekran işinde `AddReplaceTexture`'ın global olduğunu söyle.
