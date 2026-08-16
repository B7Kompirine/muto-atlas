---
description: Search a FiveM native, verify it exists, show its signature
argument-hint: <native adı veya arama terimi> [--apiset server|client|shared]
allowed-tools: Bash(python:*), Read
---

Kullanıcının sorgusu: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

Sorguyu şu şekilde ele al:

1. Sorgu bir native adına benziyorsa (`GetEntityCoords`, `GET_ENTITY_COORDS`,
   `0x3FEF770D40960D5A`) önce doğrula:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/nativedb.py" check <ad>
   ```

   Varsa `show` ile tam imzayı, parametre açıklamalarını, docs linkini ve Lua
   örneğini getir. Yoksa önerilen yakın isimleri kullanıcıya sun ve **uydurma**.

2. Sorgu serbest metinse (`araç yakıtı`, `plaka okuma`, `oyuncu kimliği`) arama yap:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/nativedb.py" search <terimler> [--apiset ...]
   ```

   Arama İngilizce açıklamalar üzerinde çalışır; Türkçe sorguyu İngilizce terime
   çevirerek ara (`yakıt` → `fuel`, `plaka` → `plate`, `kimlik` → `identifier`).

3. Sonucu sunarken **her zaman** şunları belirt:
   - `client` / `server` / `shared` etiketi ve bunun hangi dosyaya yazılacağı
   - tam imza (parametre tipleri ve sırası)
   - docs.fivem.net linki

Birden fazla aday varsa hepsini listele, sonra kullanıcının anlattığı işe en uygun
olanı gerekçesiyle öner.
