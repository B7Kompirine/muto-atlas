---
description: Bir prop/obje dünyada nerede (ymap + MLO iç mekân) veya bir koordinatın çevresinde ne var
argument-hint: <model adı> | near <x> <y> <z> [--radius N] [--filter parça]
allowed-tools: Bash(python:*), Read
---

Kullanıcının sorgusu: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

3.05 milyon dünya yerleşimi indekste. İç mekân (MLO) proplarının konumu
`mloPos + rotate(localPos, mloRot)` ile hesaplanır — yani Fleeca'nın içindeki
kapı da bulunur, sadece dış dünya değil.

## Nasıl kullan

```bash
# bir archetype'in tüm yerleşimleri
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" where <model adı>

# bir noktanın çevresinde ne var
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" near <x> <y> <z> --radius 10
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" near <x> <y> <z> --radius 15 --filter door
```

## Sonucu sunarken

- Konumu doğrudan `vec3(x, y, z)` biçiminde ver — config'e yapıştırılabilsin.
- `[mlo]` işaretliyse hangi iç mekânın parçası olduğunu söyle; o prop ancak
  o MLO yüklüyken vardır.
- "6 benzersiz konum" gibi bir sonuç, o propun haritada kaç yerde
  tekrarlandığını gösterir (örn. 6 Fleeca şubesi) — config'i buna göre kur,
  tek koordinat varsayma.
- Sonuç yoksa: prop dünyaya yerleştirilmemiş olabilir (sadece script ile
  spawn edilir) ya da LOD filtresine takılmıştır. `/asset <ad>` ile
  archetype olarak var mı diye bak.
- `entities.db` yoksa kullanıcıya `/asset-build` öner — **uydurma**.
