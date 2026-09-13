---
description: Look branch - shaders and render buckets, textures, prop lights (TimeFlags/Flashiness/gobo), decals, timecycle, parallax, vertex colour, emissive panels
argument-hint: <ne olacak — "lambam sönük" / "duvara graffiti" / "oda çok aydınlık" / "duvarda delik" / "hangi shader">
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep, AskUserQuestion
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `scripts/assetdb.py`'yi içeren muto-atlas klasörü).

## Bu bir DAL komutudur

1. **Önce dalı oku:** `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/branches/look/_branch.md`
   — shader = program + kova, doku DXT kuralları, ışık kemiğe bağlı / TimeFlags / Flashiness enum / gobo Tangent,
   karanlığın üç katmanı, vertex color bucket 0, decal üç sistem, parallax üç gerçek.
2. Argümandan **tek yaprağı** seç: shader · parallax · ışık · ışık matematiği · timecycle · vertex color · emissive · decal.
3. Kod yazmadan sorgula ve **sihirli sayıyı çöz**: `assetdb.py light <ydr>` (`--table` ile vanilla bandı) · `cycle w_clear --hour 20` ·
   `timecycle <ad>` · `shader <tür>` · `decal <tür>` · `flags <n>`.
4. Değer önerirken ölçülmüş vanilla bandını kullan (`--table`); katman yoksa aralık **uydurma**. Her yazma **geri okunur**.

## Sonucu sunarken
- "Yanmıyor" → önce saat (`TimeFlags`), sonra oda modifier'ı, en son ışık. Sırayı yazdığın cevapta göster.
- Ekran görüntüsüne dayanarak "bozuk" deme; pikseli/dosyayı oku.
- Asset değişti → sunucudan çık, yeniden bağlan.
