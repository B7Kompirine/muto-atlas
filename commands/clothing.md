---
description: Clothing branch - freemode clothing, moving clothes to 98-bone peds, ped props (hats, glasses), texture variants and skintone (_r)
argument-hint: <ne olacak — "freemode'a ceket ekle" / "şapka prop'u" / "ten rengi çalışmıyor" / "doku varyantı">
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read, Edit, Write, Glob, Grep, AskUserQuestion
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

## Bu bir DAL komutudur

1. **Önce dalı oku:** `${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/dallar/clothing/_dal.md`
   — iki UV map, `Colour 0/1`, Mesh Domain, gömülü doku kuralı, doku adlandırması, `_r` maskesi, Render Flags.
2. Argümandan **tek yaprağı** seç: freemode kıyafet · ped prop · doku varyantı.
3. ⚠️ Bu dal **video kaynaklı, ölçülmedi** — kullanıcıya bunu söyle; sayı verirken `assetdb.py` ile doğrula.
4. RPF'ten çıkarma → `extract_asset.ps1 -PathFilter '<ped>'`.

## Sonucu sunarken
- Export'tan sonra `textures/` klasörü oluştuysa embed kalmıştır — söyle.
- Asset değişti → sunucudan çık, yeniden bağlan.
