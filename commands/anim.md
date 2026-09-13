---
description: Search animations (duration + bones), prop skeletons, expressions and scenarios
argument-hint: <arama terimi> | <dict> --dict | bones <model> | expr <terim>
allowed-tools: Bash(python:*), Read
---

Kullanıcının sorgusu: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

312.748 klip `.ycd`'den çıkarıldı — **gerçek süre ve kemik sayısı** ile.
**Animasyon adı asla uydurulmaz**; burada yoksa yoktur.

## Nasıl kullan

```bash
# dict + clip içinde ara (süre ve kemik sayısıyla)
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" anim <terim>

# bir dictionary'nin içini SÜREYE GÖRE GRUPLU dök -> ped+prop çiftini gösterir
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" anim <dict adı> --dict

# sadece dictionary adlarında ara
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" anim <terim> --dict-only

# prop/ped iskeleti: kemik adı + tag
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" bones <model>

# expression (.yed): prosedürel / yay / çarpışma tepkisi
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" expr <terim>

# ped senaryosu (dünya animasyonu)
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" scenario <terim>
```

Türkçe sorguyu İngilizce terime çevirerek ara: `oturma` → `sit`, `sigara` →
`smoking`, `kaynak` → `weld`, `kelepçe` → `cuff`, `taşıma` → `carry`,
`çanta` → `bag`, `para` → `cash`.

## Sonucu sunarken

- **Hem dictionary hem clip** adını ver; biri eksikse animasyon oynamaz.
- **Süreyi çıktıdan al**, tahmin etme. `Wait()` / progress süresi oradan gelir.
- Kullanım kalıbı: `RequestAnimDict` → `HasAnimDictLoaded` bekle → `TaskPlayAnim`.
- **Prop'lu sahne isteniyorsa** `--dict` çıktısındaki
  *"ayni sure, FARKLI iskelet: ped + prop cifti"* işaretine bak; ped ve prop
  kliplerini senkron sahneyle birlikte oynat.
- Prop'un iskeleti yoksa `PlayEntityAnim` çalışmaz — `bones` ile önce doğrula.
- Sonuç çıkmadıysa terimi değiştirerek 2-3 kez dene; hâlâ yoksa
  "bu isimde animasyon indekste yok" de, **benzerini uydurma**.
