# Ped prop — şapka, gözlük, kulaklık (`p_head`, `p_eyes`, `p_ears`)

**Ne zaman okunur:** ped'e takılan prop ekleyeceksin; konumlandırma (`IK_Head`), doku adlandırması, `Render Flags`, `propsName`, Creature Metadata.
**When to read:** hat, glasses or headset (`p_head`, `p_eyes`, `p_ears`); positioning a ped prop; adding one to a non-streamed ped.
**Kaynak:** `notlar/03` §8-9 · `kaynaklar/dis-arac.md` §2 §4 (2026-08) · **Ölçüm:** video
**Önce:** `dallar/clothing/_dal.md` · gövde › `govde/arac-tuzaklari.md` §1

---

## 8. `p_eyes` / `p_ears` konumlandırma (`jzFT3uryGuI`)

Tam reçete, iki prop için de aynı:
1. Ped'den herhangi bir bileşen import et — **sadece iskelet referansı için**.
2. Skeleton → Edit Mode → **X-Ray** → kafanın ortasından geçen **`IK_Head`** kemiğinin
   **arkadaki küresini** seç. (Blender bazen buna "facial root" der, önemli değil.)
3. `Shift+S` → **Cursor to Selected**.
4. Object Mode → prop mesh'i seç → sağ tık → Set Origin → **Origin to 3D Cursor**.
5. Object Properties'te **Location X/Y/Z = 0, 0, 0**.
6. **Z ekseninde 180°**, sonra **Y ekseninde 90°** döndür.
7. `Ctrl+A` → Apply All Transforms (alışkanlık; hata ayıklamayı kolaylaştırır).

Bu, `SCALE_Head` kemiğine referansla çalıştığı için **her ped'de** geçerli.

## 9. Ped prop'ları (`p_head` / `p_eyes`) non-streamed ped'e ekleme (`Jm3Ps157z3s`)

- Prop doku adlandırması **bileşenlerden FARKLI**: sonek yok, sadece harf →
  `<ped>_p.ytd` içinde `..._a`, `..._b`, `..._c`.
- Prop'lar pratikte **sadece HIGH LOD** taşır; medium/low derdi yok.
- Normal map'i olmayan prop'a **8×8 boş normal** koy.
- YMT Editor → ilgili kategoriyi (`p_head`, `p_eyes`) aktive et, A/B dokularını ekle.
- ⛔ **`Render Flags` (prop properties) Blender'daki shader ile EŞLEŞMELİ.**
  `ped_alpha` / `ped_decal` / `ped_cutout` kullanıyorsan YMT'de karşılığını seç.
  **MP freemode'da önemsiz, diğer TÜM ped'lerde fiilen zorunlu** — camlı vizör,
  gözlük camı gibi şeylerde bunu atlamak sessiz hataya yol açıyor.
- **`MH_hair_scale`** kemiği ağırlıklı olarak **freemode'a özgüdür**; çoğu Rockstar
  ped'inde yoktur. Şapka takınca saçın küçülmesi bu kemikle olur.
- ⚠️ **Creature Metadata yalnız ped'de bir şey ÖLÇEKLENİYORSA gerekir** —
  topuk yüksekliği (feet) ya da saç ölçekleme (p_head). İkisi de yoksa dokunma.
  Gerekiyorsa YMT Editor → **File → Generate Creature Metadata**.
- FiveM `peds.meta`: **`propsName`** satırına prop `.ydd`'sinin adını yaz —
  prop'ları aktive eden tek şey bu.
- Son dosya seti: `.ydd` · `.yft` · `.ymt` · `.ytd` · `_p.ydd` · `_p.ytd`


## Topluluk uyarısı (Sollumz Discord)

- ⛔ **Ped prop'unda `Render Flags` Blender shader'ıyla eşleşmeli**
  (`ped_alpha`/`ped_decal`/`ped_cutout`). MP freemode'da önemsiz,
  **diğer tüm ped'lerde fiilen zorunlu**.
