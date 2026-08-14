---
description: Archetype/animasyon indekslerini yeniden kur (yeni MLO/prop eklediysen)
argument-hint: [sunucu resources yolu]
allowed-tools: Bash(powershell.exe:*), Bash(python:*), Read
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

Ne zaman gerekir: sunucuya **yeni MLO / custom prop / ytyp** eklendiğinde, ya da
GTA V güncellendiğinde. Vanilla veri değişmediği sürece tekrar kurmaya gerek yok.

## 1. Archetype indeksi (ytyp → prop/kapı gerçeği)

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/build_archetypes.ps1" -ExtraFolders "<sunucu resources yolu>"
```

- GTA V klasörünü ve CodeWalker.Core.dll'i kendi bulur; bulamazsa
  `-GtaFolder` / `-CodeWalker` ile verilir.
- `-ExtraFolders` verilmezse sadece vanilla indekslenir.
- Süre ~20 sn, çıktı `data/archetypes.tsv.gz`.

**Ön koşul:** CodeWalker (CodeWalker.Core.dll) ve GTA V kurulu olmalı. Yoksa
kullanıcıya söyle; bu adım atlanırsa custom prop'lar sorgulanamaz.

## 2. Dünya konumu indeksi (ymap + MLO iç mekân)

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/build_entities.ps1"
python "${CLAUDE_PLUGIN_ROOT}/scripts/build_entities_db.py"
```

- İlk adım ~50 sn, `entities.tsv.gz` (~40 MB) üretir.
- İkinci adım ~20 sn, `entities.db` (~214 MB, indeksli) üretir.
  `--drop-tsv` ile ara dosya silinir.
- `-All` verilmezse LOD/arazi parçaları atlanır; script yazarken lazım olan
  proplar korunur. Her şey isteniyorsa `-All` ekle (indeks ~10x büyür).

## 3. Animasyon detayı, iskelet ve expression

```bash
# klipler: gerçek süre + iz + kemik sayısı (.ycd), ~3 dk
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/build_clips.ps1"

# iskelet (.ydr/.yft) + expression (.yed) — en uzun adım
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/build_rigs.ps1"
```

## 4. Animasyon / prop / senaryo isim listesi

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/build_anims.py"
```

İnternet ister (DurtyFree/gta-v-data-dumps). Daha önce indirilmişse
`--offline` ile önbellekten kurar.

## 5. Doğrula

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" stats
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" where v_ilev_gb_teldr
```

Beklenen: ~316k archetype, ~269k anim klip, ~3.05M dünya yerleşimi ve
`v_ilev_gb_teldr` için 6 Fleeca konumu. Kullanıcıya custom archetype sayısını
söyle — 0 ise `-ExtraFolders` yolu yanlıştır.
