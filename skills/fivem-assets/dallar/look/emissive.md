# Emissive panel — fosforlu tavan lambası, tek tek kontrol, kırık panel

**Ne zaman okunur:** tavan lambası/floresan paneli kırık görünsün, titresin, parlaklığı; "emissive'in ışığı yok".
**When to read:** a glowing ceiling panel, individually controlled lamps, a broken/flickering panel.
**Kaynak:** `decal.md` §6 (2026-08) · **Ölçüm:** morg MLO'sunda oyunda
**Önce:** `_dal.md` · gövde › `govde/arac-tuzaklari.md` §1-2 · shader/kova `shader.md` (emissive + CUTOUT)

---

## 6. EMISSIVE PANELLER (fosforlu tavan lambası)

`emissive.sps` shader'ının parlaklığı **`emissiveMultiplier`** parametresinde
(morg panelinde `x=3`).

⛔ **Panellerin ışığı YOKTUR** — sadece emissive geometri. Odanın 3 büyük
paneli tek `Geometry` (6 üçgen) ve tek shader paylaşıyordu; birini
değiştirmek üçünü birden değiştiriyor.

### Tek tek kontrol için geometri bölünür
1. Shader'ı kopyala, kopyada `emissiveMultiplier` = 0 (ölü panel)
2. `Geometry`'yi vertex konumuna göre böl, indeksleri **her geometride
   0'dan** yeniden numaralandır
3. Ölü panelleri yeni shader'a, canlıyı eskisine bağla

Vertex/indeks biçimi (CodeWalker XML, `Layout type="GTAV1"`):
```
Position(3)  Normal(3)  Colour0(4)  TexCoord0(2)
indeksler: 0 1 2  2 3 0   (quad basina)
```

### Emissive geometri TİTREYEMEZ
Flicker bir **ışık** özelliğidir. Panelin kendi parıltısı sabit kalır;
panelin altına Flashiness'li bir ışık koyarsan **odaya vuran ışık** titrer
ve panel titriyormuş gibi okunur.

---


**Emissive panelin ışığı yoktur**, parlaklığı `emissiveMultiplier`'dadır ve bir odadaki paneller tek geometriyi paylaşır — birini kırmak için geometriyi bölmek gerekir. Emissive geometri **titreyemez**; flicker ışık özelliğidir, panelin altına `Flashiness`'li ışık konur (`isik.md`).
