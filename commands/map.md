---
description: Map branch - replace vanilla parts, destruction (RayFire), MLO props and swaps, LOD chains, vanilla interior measurements, grass/procedural
argument-hint: <ne olacak — "köprü çöksün" / "yolu değiştir" / "bankaya kasa koy" / "uzakta kayboluyor" / "çim">
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep, AskUserQuestion
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `scripts/assetdb.py`'yi içeren muto-atlas klasörü).

## Bu bir DAL komutudur

1. **Önce dalı oku:** `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/dallar/map/_dal.md`
   — MLO içi/dışı, extent, LOD zinciri + `hei_`, ymap sürümleri, RayFire'ın üç varlığı, çimin dört sistemi.
2. Argümandan **tek yaprağı** seç: vanilla parça · yıkım · MLO swap · MLO'ya prop · LOD · iç mekân ölçüsü · çim.
   Tarif belirsizse (*"duvar kırılsın"*, *"kapı patlasın"*) `AskUserQuestion`: harita parçası mı script prop'u mu ·
   kalıcı enkaz kalacak mı · herkes aynı anda mı görecek · yıkım sırasında üstünde yürünecek mi.
3. Kod yazmadan sorgula: `assetdb.py where <ad>` · `mlo <ad>` · `lodchain <ad>` · `flags <n> --entity` · `near x y z`.
4. Asset değişti → **sunucudan çık, yeniden bağlan.**

## Sonucu sunarken
- Sihirli sayıyı (`1572872`, `18350080`) çözerek söyle, kopyalama.
- Extent'e dokunulmadığını, `hei_` ikizinin yamalandığını, oda atamasının yapıldığını açıkça yaz.
