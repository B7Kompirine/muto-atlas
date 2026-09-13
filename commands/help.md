---
description: List every muto-atlas command with what it does, plus data-layer status - the map of the whole plugin
argument-hint: [boş = tüm liste] | [arama kelimesi — "ışık", "animasyon", "decal"]
allowed-tools: Bash(python:*), Read
---

Argüman: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `scripts/assetdb.py`'yi içeren muto-atlas klasörü).

## Yap

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/list_commands.py" $ARGUMENTS
```

Bu betik listeyi **`commands/*.md` frontmatter'ından okur** — elle yazılmış bir
liste değildir, dolayısıyla eskimez. Yeni komut eklenince kendiliğinden görünür.

Argüman verilmişse arama olarak geçer (ada ve açıklamaya bakar).

## Sonra — veri durumunu da göster

Bu plugin'in her cevabı `data/` altındaki katmanlara dayanır. Eksik katman,
modelin **tahmine düşmesi** demektir. O yüzden komut listesiyle birlikte durumu
da bildir:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" --plan
```

Çıktının **"N/M katman kurulu"** satırını olduğu gibi aktar — sayıyı sabit
yazma, `setup.py` onu `len(KATMANLAR)`'dan hesaplar. Eksik varsa kurulum
komutunu ver: `python scripts/setup.py` ya da `/asset-setup`.

## Sunarken

- Ham çıktıyı olduğu gibi bas — betik zaten okunur biçimde gruplu.
- Kullanıcı belirli bir iş tarif ediyorsa ("ışık ayarlayacağım", "kapı
  açılmıyor") listeyi dökmek yerine **doğru komutu söyle** ve neden onun
  olduğunu bir cümleyle açıkla.
- Komutlar `/muto-atlas:<ad>` ile çağrılır; başka bir plugin'de aynı ad yoksa
  kısa hâli `/<ad>` de çalışır.

## Listede olmayan ama işe yarayan üç şey

| iş | komut |
|---|---|
| veri katmanı durumu | `python scripts/setup.py --plan` |
| plugin bütünlük denetimi (kırık atıf, yetim referans, BOM) | `python scripts/audit_plugin.py` |
| tek satırlık komut listesi (script/dokümantasyon için) | `python scripts/list_commands.py --duz` |
