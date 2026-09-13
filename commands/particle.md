---
description: Particle branch - find/attach vanilla effects, build .ypt from scratch, family catalogues, layered effects, deploy and measure in game
argument-hint: <ne olacak — "kırılınca toz çıksın" / "kendi kıvılcımım" / "patlama katmanlı olsun" / "efekt görünmüyor">
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep, AskUserQuestion
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `scripts/assetdb.py`'yi içeren muto-atlas klasörü).

## Bu bir DAL komutudur

1. **Önce dalı oku:** `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/branches/particle/_branch.md`
   — `fxName` ≠ `.ypt` adı, `FxcFileHash`, keyframe yuvaları, ölçekler (yüzde vs 1.0), sayfa/`C4`, havuz 400.
2. Argümandan **tek yaprağı** seç: hazır efekt · sıfırdan `.ypt` · katalog · katmanlı · dağıtım/ölçüm.
3. Kod yazmadan sorgula: `assetdb.py fx <ad> --exact` · `ptfx <prop|efekt>` · `ptfx --type 4`.
4. Üretim sonrası geri oku (`ypt_xml_to_bin.ps1` exit 0), oyunda **tezgâh** ile ölç — "handle dolu" kanıt değildir.

## Sonucu sunarken
- `fxName`'in `.ypt`'de bulunduğunu ve `ent_` önekini açıkça yaz.
- Yeni `.ypt` stream'e girdiyse: ayrı kaynak, küçük harf ad, **sunucudan çık, yeniden bağlan**.
