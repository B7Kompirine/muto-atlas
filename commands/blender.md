---
description: Where blender.exe is - show it, or set a new path
argument-hint: [path]  ·  omit to just show it
allowed-tools: Bash(python:*), Read
---

Kullanıcının sorgusu: `$ARGUMENTS`

```bash
# nerede?
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path blender

# ayarla
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" path blender "$ARGUMENTS"
```

`$ARGUMENTS` boşsa **göster**, bir yol verilmişse **ayarla**.

`blender_*.py` betikleri (ışık önizlemesi) Blender'ın içinde
çalışır. Bu yol kayıtlıysa betikler başsız
(`--background`) çalıştırılabilir.

**Otomatik arama Steam kurulumunu bulamaz** — ölçüldü: Blender
`steamapps\common\Blender\blender.exe` altına kurulabiliyor ve varsayılan
aday listesinde yok. Böyle bir kurulumda yol bir kez elle verilir.

## Sonucu sunarken

- **Işığı okumak/yazmak için Blender GEREKMEZ** — `/look` dosya üzerinden
  çalışır. Kullanıcı ışık değeri ayarlıyorsa Blender önerme.
- Blender sürümü önemli: 5.x'te `GPUShader(vs, fs)` kaldırıldı ve
  `GPUStorageBuf` yok; 4.4+ Action API katmanlı. Sürüm farkı betik
  hatalarının ilk şüphelisidir.

## Kurulu eklentiler — kod yazmadan önce buna bak

Bir iş için sıfırdan `bpy` kodu yazmadan önce **zaten kurulu bir eklenti onu
yapıyor mu** diye bak. Kullanıcının kendi yazdıkları (`muto_*`, `MutoLab`)
GTA hattına göre kurulmuştur; genel bir eklentiden daha uygundur.

### Kullanıcının kendi eklentileri

| eklenti | ne yapar |
|---|---|
| **`muto_decal`** | atlas UV seçimiyle yüz decal'leri, toplu arşiv ve birleştirme |
| **`muto_edge_decals`** | mesh kenarları boyunca decal geometrisi — katman + UV |
| **`muto_kablo`** | GTA V için çapraz düzlemli kablo/zincir — eğri **tüpe değil, alfa kesimli kartlara** dönüşür |
| **`muto_panel_merge`** | dağınık N-panel sekmelerini tek sekmede toplar |
| **`muto_helper`** | hangi araç nerede + node araçları için `D` tuşu pie menüsü — **hangi aracı arayacağını bilmiyorsan buradan başla** |
| **`MutoLab`** | fizik ve **fracture** simülasyon araçları (yıkım/kırılma işlerinde) |
| `decal_gen` · `ornament_generator` · `GeoCables` | kenar decal üretimi · ornament · geometry-nodes kablo |

⚠️ Bunların ürettiği geometri **Sollumz'a girmeden önce** normal kurallara tabidir:
transform pişer, `Ctrl+A` şart, doku ikinin kuvveti
(`skills/fivem-assets/govde/arac-tuzaklari.md` §2, `govde/gta-temel.md` §5).

### İşe yarayan üçüncü taraf eklentiler (kurulu)

`sollumz` · `sollumz_rdr_dev` ·
`cell_fracture` · `ZenUV` / `mio3_uv` / `flat_uv_mapper` / `propgon_uv_trim` ·
`SimpleBake` / `sanctus_bake` / `beyond_channel_packer` · `lazy_decals` ·
`smart_remesh` · `qol_clean_slice_booleans` · `auto_mirror` · `pro_particles` ·
`RayPilot` · `stair_generator_addon` · `Organic_Addon` · `luman_tools` ·
`unreal_viewport_navigation`.

Kanalda paylaşılan, **kurulu olmayan** araçlar (Vertex Color Master, geonodes
decal/terrain, `blender_rayfirev`, FakeBones) →
`skills/fivem-assets/kaynaklar/topluluk-kaynak.md`.

**Ölçüm:** `AppData\Roaming\Blender Foundation\Blender\*\extensions\` ve
`\scripts\addons\` taraması, 2026-09-06.
