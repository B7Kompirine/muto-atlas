---
description: blender.exe nerede — göster ya da yeni yolu ayarla
argument-hint: [yol]  ·  boş bırak = nerede olduğunu söyle
allowed-tools: Bash(python:*), Read
---

Kullanıcının sorgusu: `$ARGUMENTS`

```bash
# nerede?
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" yol blender

# ayarla
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" yol blender "$ARGUMENTS"
```

`$ARGUMENTS` boşsa **göster**, bir yol verilmişse **ayarla**.

`blender_*.py` betikleri (retarget, creature rig, face pose, bake, ışık
önizlemesi) Blender'ın içinde çalışır. Bu yol kayıtlıysa betikler başsız
(`--background`) çalıştırılabilir.

**Otomatik arama Steam kurulumunu bulamaz** — ölçüldü: Blender
`steamapps\common\Blender\blender.exe` altına kurulabiliyor ve varsayılan
aday listesinde yok. Böyle bir kurulumda yol bir kez elle verilir.

## Sonucu sunarken

- **Işığı okumak/yazmak için Blender GEREKMEZ** — `/isik` dosya üzerinden
  çalışır. Kullanıcı ışık değeri ayarlıyorsa Blender önerme.
- Blender sürümü önemli: 5.x'te `GPUShader(vs, fs)` kaldırıldı ve
  `GPUStorageBuf` yok; 4.4+ Action API katmanlı. Sürüm farkı betik
  hatalarının ilk şüphelisidir.
