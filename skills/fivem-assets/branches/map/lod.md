# LOD chain — flickers / disappears at distance / ghost copy

**When to read:** a prop disappears and comes back at distance, shows twice, a ghost copy remains; choosing `lodDist`; LOD levels in your own ymap; building the LOD chain and its parenting; `lodaudit` output.
**Source:** `trunk/flags.md` §9 (3.07M entities) · former video notes 08 §8 (Stumpy Mason, video) · **Measured:** 3,145,882 ymap entities, with `rpfPath`; video steps [video]
**Read first:** `branches/map/_branch.md` · trunk › `trunk/flags.md`, `trunk/tool-pitfalls.md`

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" lod [--size <m>]     # vanilla lodDist reference
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" lodchain <name>    # the real chain
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" lodaudit           # your own ymaps vs vanilla
```

## LOD chain — MEASURED on 3.07M vanilla entities

CodeWalker entity tabs: `General` · **`LOD Hierarchy`** · `Extensions` · `Pivot`.
`LOD Hierarchy` carries only two fields: **`ParentIndex`** and **`NumChildren`**.

Index: `data/ymap_lod.tsv.gz` (`build_ymap_lod.ps1`) — vanilla 19,387 ymaps +
custom 204 ymaps = **3,145,882 entities**, of which **1,556,743 are in a LOD
chain**. Query: `assetdb.py lodchain`.

### ⛔ A ymap NAME IS NOT UNIQUE — without `rpfPath` the measurement is wrong

**4751 of 8252 ymap names exist in more than one RPF** (base + DLC patches; some
names have 5 copies). Index by file name alone and the copies overlap,
entity indices get mixed up and the chain looks falsely "broken". My first measurement
did exactly that: reading by name produced **53,102 false breaks** and a wrong
missing-entity count. That is why the index carries an `rpfPath` column; when resolving
a parent, look **in the same RPF layer first**.

### Chain integrity — measured

**1,548,159** entities with `parentIndex ≥ 0`:

| Result | Count | Share |
|---|---:|---:|
| parent resolved | 1,447,833 | 93.5% |
| ymap declares no parent | 5,183 | 0.3% |
| **parent index not found** | **95,143** | **6.1%** |

⚠ **This 6.1% is an OPEN QUESTION, not "vanilla is broken".** Measured sample:
`dt1_rd1.ymap[83]` asks for `dt1_lod[69]` as parent; **all four copies of
`dt1_lod.ymap` have only 42 entities** (`CEntityDefs` = `AllEntities`
= 42, no MLO instance). So the index really does not exist. Possible explanations
not tested: `parentIndex` may point into the combined list of the ymaps at the same LOD
level, or `imap` group files may be involved. **If you see 6% breaks in your own
map, use this as the reference: vanilla itself measures "broken" at this rate.**

### ⛔ `ParentIndex` alone means nothing

It is **an ordinal**; which file's ordinal is given by **`CMapData.parent`**
in the ymap header. Without indexing that field the chain cannot be walked.

**Do not trust the file-name pattern.** The `X.ymap → X_lod.ymap` pattern is real but
not a rule: only 456 of 8143 ymaps carry a `*_lod`/`*_slod` name, and in **79%**
of the 7285 ymaps that declare a parent the child name starts with the parent name —
so one in five does not match.

### Measured real level transitions (parent → child)

| Transition | Count |
|---|---:|
| `LOD` → `HD` | 693,260 |
| `SLOD2` → `LOD` | 55,817 |
| `SLOD3` → `LOD` | 40,250 |
| `SLOD2` → `SLOD1` | 13,628 |
| `SLOD4` → `LOD` | 1,719 |

⚠ **The chain is NOT a straight ladder.** The
`HD→LOD→SLOD1→SLOD2→SLOD3` order taught in tutorials does not exist in vanilla: **there is no
`SLOD1 → LOD` transition at all.** `SLOD1` is not a step between `LOD` and `SLOD2`,
it is a separate side branch of `SLOD2`. And there are **7 levels**, not 5:
`ORPHANHD · HD · LOD · SLOD1 · SLOD2 · SLOD3 · SLOD4`.

### `lodLevel` distribution

| Level | Count |
|---|---:|
| `LODTYPES_DEPTH_ORPHANHD` | 1,527,999 |
| `LODTYPES_DEPTH_HD` | 1,234,368 |
| `LODTYPES_DEPTH_LOD` | 279,955 |
| `LODTYPES_DEPTH_SLOD1` | 27,423 |
| `LODTYPES_DEPTH_SLOD2` | 2,407 |
| `LODTYPES_DEPTH_SLOD3` | 722 |
| `LODTYPES_DEPTH_SLOD4` | 77 |

**`ORPHANHD` is the most common level** — so even in vanilla most entities are not in a chain.
The LOD chain is the exception, not the rule.

### `childLodDist` — convention, not rule

`parent.childLodDist == child.lodDist` **holds 86%, fails 14%**
(692,525 equal / 112,149 different). Example: `plg_01_chopped_field` has `lodDist=220`
while its parent has `childLodDist=210`. `lodDist=-1` also occurs (means use the archetype
default).

### Other measurements

- `-1` = end of chain. On an intermediate level the `LOD Adopt Me` (16) bit is set.
- `priorityLevel`: `PRI_REQUIRED` 2,584,698 · `PRI_OPTIONAL_MEDIUM` 182,663 ·
  `PRI_OPTIONAL_HIGH` 158,164 · `PRI_OPTIONAL_LOW` 147,426
- **Delete one link from the chain and the whole chain breaks**: all levels load
  at once, flicker, ghost copies appear. (Measured: one model deleted,
  six models disappeared at once.)
- Even vanilla has breaks: of 859,352 entities with `parentIndex ≥ 0`,
  52,614 have a parent index that does not exist in that file.

### ⭐ Auditing your own map: the benchmark is vanilla

`assetdb.py lodaudit` — an absolute count says nothing; **the comparison with the vanilla
rate** does. Our server's 195 loose ymaps (72,931 entities) compared with vanilla's
3,072,951 entities:

| Inconsistency | Vanilla | Ours |
|---|---:|---:|
| **`LOD in Parented YMAP` bit set but `parentIndex = -1`** | **0** (0.00%) | **3,575** (4.90%) |
| `parentIndex` set but the ymap declares no parent | 3,351 (0.11%) | 1,832 (2.51%) |
| `LOD Adopt Me` bit set but no children | 519 (0.02%) | 0 |

**The first is a definite defect:** Rockstar never once ended up in that state across
3 million entities. Our 3,575 cases are the trace of copying `flags=1572872` from a tutorial
without building a chain — `lodLevel` is `ORPHANHD` in all of them. The densest files:
`la_trees.ymap` (788), `CityCentral.ymap` (477), `highway.ymap` (381).

The third row shows the reverse: vanilla itself is inconsistent at 0.02%,
so **not every non-zero deviation is a defect**. The benchmark is the rate.

### Verified real chain

```
0. plg_01_chopped_field        HD    prologue01.ymap[4]
   lodDist=220  childLodDist=0  children=0
   flags=1572872 -> LOD in Parented YMAP | Cast Static | Cast Dynamic
   parentIndex=84 -> prologue01_lod
1. plg_01_chopped_field_lod    LOD   prologue01_lod.ymap[84]
   lodDist=750  childLodDist=210  children=1
   flags=1572864 -> Cast Static | Cast Dynamic
```

The HD entity's flag is **exactly `1572872`** — the number carried in the notes for years
without its reason written down, now in real vanilla data and decoded.
- Entity `General` fields: `Position` `Rotation` `Archetype(+hash)` `GUID`
  `Flags` `ScaleXY` `ScaleZ` `LodDist` `ChildLodDist` `LodLevel`
  (`LODTYPES_DEPTH_HD` …) `PriorityLevel` (`PRI_REQUIRED` …) `AOMultiplier`
  `ArtificialAO` `TintValue`.
- To see an entity with an orphan LOD, set CodeWalker `Max LOD` = **`ORPHANHD`**.

---



---

## Two mechanisms — embedded LOD and ymap parenting [video]

### A) Embedded (orphan) LOD — inside one drawable
- Build four versions: high / medium / low / verylow.
  Reduce polygons **and halve the textures each step**: `512 → 256 → 128 → 64 → 32`.
- In the Sollumz drawable hierarchy, **high/medium/low/verylow distances**
  (**50 / 100 / 150** in the example, the last one left as is).
- Link each mesh to its slot: from the drawable's **data (small triangle)** tab pick
  the medium/low/verylow meshes.
- ytyp → autocreate.
- ⭐ On the ymap entity **`LODTYPES_DEPTH_ORPHANHD`** —
  > *"the single most important thing for this."*
- In game: medium at 50, very low at 150, then the **ymap bounds** kick in and
  the object disappears.

### B) YMAP parenting — multi-level chain
Four separate ymaps: `test` (HD) → `test_lod` → `test_slod` → `test_slod3`

- **The HD entity's flag is `1572872`** =
  *"LOD in parent map + cast static + cast dynamic shadows"*
  ⭐ **Exactly the decode in Atlas §4** — independent confirmation.
  > Atlas §4 says this flag silently drops the object when used **inside an MLO**;
  > the reason shows here: the flag says *"my LOD is in the PARENT map"*,
  > **correct when a parent map exists**, and in an MLO there is none, so the entity is dropped. The two facts do not conflict,
  > they complete each other.
- **Parent Index = the index of the entity in the next ymap, 0-BASED.**
  `-1` = end of the chain. The author stresses it separately: *"it starts from zero,
  this is very important."*
- The **"LOD adopt me"** flag on the LOD entity → it is adopted by the entry
  one level up.
- Distance hand-over: **each level's `Child LOD Distance` is the `lodDist` of the level
  before it**. Example: HD lodDist 50 → LOD child 50 / lodDist 100 → SLOD2 child 100 …
  SLOD3 child 200 / lodDist 250.
- `Num Children` must be counted correctly.
- ⚠️ **Close and reopen the CodeWalker project** — only then does the LOD transition
  show.
- Refine the distances afterwards; the benchmark is **what vanilla does**.

---
