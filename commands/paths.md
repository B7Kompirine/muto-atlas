---
description: Show or set external tool and folder paths (codewalker, gta, server, blender, ...)
argument-hint: [name] [path]  ·  omit both to list all  ·  --remove to drop one
allowed-tools: Bash(python:*), Read
---

Kullanıcının sorgusu: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `scripts/assetdb.py`'yi içeren muto-atlas klasörü).

Tüm dış yolların **tek kütüğü** `data/config.json`. `data/` .gitignore'da
olduğu için kişisel yol bilgisi **asla repoya girmez**.

```bash
# hepsini göster (var/yok işaretli)
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" yol

# tek birini göster
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path codewalker

# ayarla
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path codewalker "C:\Araclar\CodeWalker\CodeWalker.Core.dll"

# kaydı kaldır
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path blender --remove
```

## Bilinen adlar

| ad | ne | tip |
|---|---|---|
| `codewalker` | `CodeWalker.Core.dll` — 30 betik buna bağlı | dosya |
| `gta` | GTA V kurulum klasörü — veri katmanlarının kaynağı | klasör |
| `sunucu` | FiveM sunucusunun `resources` klasörü | klasör |
| `blender` | `blender.exe` | dosya |

## Liste kapalı değil — istediğin adı kaydedebilirsin

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" yol gizmo "C:\Araclar\Gizmo.exe"
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" yol gizmo
```

Yeni bir araç için kod değiştirmek gerekmez.

## Sonucu sunarken

- **Diskte olmayan yol kabul edilmez.** `ayarla` önce varlığını doğrular;
  bozuk kaydı sessizce tutmaktansa hemen söyler.
- **"config'de yazılı ama diskte yok" ayrı bir durumdur** ve öyle raporlanır
  — "ayarladım ama çalışmıyor"un en sık sebebi budur, "hiç ayarlı değil"
  ile karıştırma.
- Çıkış kodu: `0` hepsi bulundu · `1` en az biri eksik · `2` verilen yol geçersiz.
- Bir betik "CodeWalker bulunamadı" diyorsa çözüm `/paths codewalker "<yol>"` —
  betiği düzenleme, hepsi aynı kütüğü okuyor.
