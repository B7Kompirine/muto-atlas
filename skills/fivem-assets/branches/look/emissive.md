# Emissive panel — fluorescent ceiling light, individual control, broken panel

**When to read:** a glowing ceiling light / fluorescent panel that should look broken or flicker; its brightness; individually controlled lamps; "the emissive gives no light".
**Source:** `decal.md` §6 (2026-08) · **Measured:** in game, in the morgue MLO
**Read first:** `_branch.md` · trunk › `trunk/tool-pitfalls.md` §1-2 · shader/bucket `shader.md` (emissive + CUTOUT)

---

## 6. EMISSIVE PANELS (fluorescent ceiling light)

The brightness of the `emissive.sps` shader is in the **`emissiveMultiplier`** parameter
(`x=3` on the morgue panel).

⛔ **The panels have NO light** — only emissive geometry. The room's 3 large
panels shared one `Geometry` (6 triangles) and one shader; changing
one changes all three.

### Split the geometry for individual control
1. Copy the shader; in the copy `emissiveMultiplier` = 0 (dead panel)
2. Split the `Geometry` by vertex position, renumber the indices **from 0
   in each geometry**
3. Bind the dead panels to the new shader, the live one to the old one

Vertex/index format (CodeWalker XML, `Layout type="GTAV1"`):
```
Position(3)  Normal(3)  Colour0(4)  TexCoord0(2)
indices: 0 1 2  2 3 0   (per quad)
```

### Emissive geometry CANNOT FLICKER
Flicker is a **light** property. The panel's own glow stays constant;
put a light with Flashiness under the panel and **the light falling on the room** flickers,
which reads as the panel flickering.

---


**An emissive panel has no light**, its brightness is in `emissiveMultiplier`, and the panels in a room share one geometry — to break one you must split the geometry. Emissive geometry **cannot flicker**; flicker is a light property, so put a light with `Flashiness` under the panel (`lights.md`).
