# Texture / colour variants / skintone (`_r`) garments

**When to read:** a-z texture variants of the same garment, a garment that shows skin tone (`_r`), "skin tone is not working", texture naming.
**Source:** `notes/03` §3, §4 naming (2026-08) · **Measured:** video; the three silent failures of `_r` independently confirmed on the Sollumz Discord
**Read first:** `branches/clothing/_branch.md` · trunk › `trunk/tool-pitfalls.md` §1

---

**The texture naming rule** holds for the whole branch → `branches/clothing/_branch.md`.

## 3. `_r` (skintone) garments — three silent failures (`sJO_Fd__2nw`)

**The skin tone texture is NOT in the garment's own `.ytd`.** The game
reads it from the `mp_fm_skin...` set in `streamedpeds_mp / MP overlay TXD`.
So the leg/foot area in the garment's texture **can be left empty**.

1. ⛔ **Do NOT MOVE the skin tone UV.** Male legs always sit in the **bottom-left corner** of the texture,
   female feet always in the **bottom half**. If you move them, tattoos and blood mapping
   break. Use the space **around** them for your own texture.
   If you are making something that covers the leg completely, like trousers, you can use that area,
   but the UV of the visible part (e.g. the ankles) **must stay in place**.
2. ⛔ **Embedded texture names must follow Rockstar's rule**:
   `<component>_spec_<NN>` → `feet_spec_000`, `lower_spec_000`, `upper_spec_000`.
   A random name → **skin tone silently does not work**.
3. ⛔ **The skin tone mask is the ALPHA channel of the specular texture.**
   Alpha says "use skin tone here"; **white = normal fabric** (no skin tone).
   You need a program that can edit the RGB channels and the alpha.
   Best starting point: **base game (not DLC)** female `lower_15` spec,
   male `lower_14` spec — the ones that show the most leg.
4. ⛔ **The texture must be SQUARE** (1024×1024, 512×512…). A ratio such as 1024×512 stretches the UV
   and breaks the skin tone again.
