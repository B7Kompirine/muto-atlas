# Araç kemikleri, mod, extra, handling — sorgu ve kemik adları

**Ne zaman okunur:** araca script'le kapı/cam/kaput/ışık/egzoz/siren/mod kemiğiyle iş yapacaksın; `handlingId`, modkit, extra, sınıf soracaksın.
**When to read:** vehicle bone names, mods, extras and handling — querying the spec sheet instead of guessing.
**Kaynak:** `govde/kemik-tag.md` §2 (193 ad, %100 tag-kararlı) · `assetdb.py vehicle` (921 araç) · **Ölçüm:** 478.055 iskelet satırı
**Önce:** `dallar/vehicle/_dal.md`

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" vehicle <ad>        # handlingId, modkit, extra, sınıf, koltuk
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" bones <model>       # aracın gerçek iskeleti (ad + tag)
```

## Araç kemiklerinde AD sabittir — adı birebir kopyala

Tam katalog ve tuzaklar `govde/kemik-tag.md` §2 ve §6'da; özet burada.

### Kategoriler

Gövde/kök · tekerlek/süspansiyon · kapı/cam/kaput · ışıklar · motor/egzoz/şanzıman · iç mekân/koltuk · mod/extra/misc · uçak/motosiklet/tekne — adlar ve tag'ler `govde/kemik-tag.md` §2.1-2.8 (tek kopya).
