---
description: Query prop/object/door archetype data (ytyp truth: is it a door, where is the pivot)
argument-hint: <model adı veya arama terimi> | door <model adı>
allowed-tools: Bash(python:*), Read
---

Kullanıcının sorgusu: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

Bu komut **ytyp gerçeğini** verir: `specialAttribute`, `flags`, `assetType`,
bounding box (pivot/menteşe konumu), fizik ve doku sözlüğü. Native denemekle
öğrenilemeyecek şeyler bunlar.

## Nasıl kullan

1. Sorgu bir model adıysa (`v_ilev_gb_teldr`, `prop_gate_prison_01`):

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" show <ad>
   ```

   Çıktı ham alanları **ve yorumu** içerir: kapı sistemi bu objeyi oynatır mı,
   pivot kenarda mı (heading ile döndürmek doğru görünür mü).

2. Soru özellikle "bu kapı açılır mı" ise:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" door <ad>
   ```

3. Tam ad bilinmiyorsa önce ara:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" search <parça>
   python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" prop <parça>     # spawn edilebilir proplar
   ```

4. Model bulunamazsa: indeks eski olabilir. Kullanıcıya
   `/asset-build` çalıştırmasını öner — **uydurma**.

## Sonucu sunarken

- `specialAttribute` değerini ve ne anlama geldiğini **açıkça** yaz.
- Kapı sistemi çalışmıyorsa (`0` gibi) bunu net söyle ve alternatifi ver;
  "AddDoorToSystem dene" deme.
- Pivot bilgisini kullanarak `SetEntityHeading` yaklaşımının doğru görünüp
  görünmeyeceğini söyle.
- `custom` kaynaklı bir archetype ise hangi resource'tan geldiğini belirt.
