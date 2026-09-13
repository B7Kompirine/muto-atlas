# Breakable / boned prop — building a fragment (.yft)

**When to read:** a prop should break apart when shot, or you need step 1 of the chain that makes collision move with a bone animation (building the fragment) — per-bone collision, `physicsDictionary`, cloth world bounds.
**Source:** old SKILL 'FRAGMENT BUILDING' (2026-07) · **Measured:** Sollumz source (`get_child_of_bone`), vanilla `Groups`, Fleeca doors in game
**Read first:** `_branch.md` · trunk › `trunk/flags.md` (`specialAttribute`), `trunk/tool-pitfalls.md` §1

---

## FRAGMENT BUILDING (step 1 of the chain)

If you want a prop's collision to move together with its bone animation,
the only way is a **fragment**. Paths that were tried and ruled out:

- `ASSET_TYPE_DRAWABLE`: one static bound, tied to the entity transform.
  The bone animation only moves the visual; the collision stays in place.
- **YED / expression**: THIS IS THE PATH THAT WORKS (the full recipe is not in the public release).

  > ⚠️ This line used to say **"there is no such thing as collision animation with YED"**.
  > THAT WAS WRONG and sent the work in the wrong direction for hours.
  > Where the error came from: the `.yed` was opened in CodeWalker, `ExprMap.Count == 0`
  > was seen and taken to mean "the file is empty". The truth is that **CodeWalker
  > cannot WRITE the expression bytecode (Streams), it can only read it** — and in this
  > use `Streams` is empty anyway; the work happens on the `Tracks` side.
  > So what was measured was the tool's limit, not the file's content.
  > **A tool not showing something does not mean that thing does not exist.**

### Building a fragment in Sollumz — what ties the bound to the bone

It is **NOT** `parent_bone`, and it is **NOT** a name match either. Sollumz reads the link
from a `COPY_TRANSFORMS` constraint (`tools/blenderhelper.py`,
`get_child_of_bone`). Without the constraint `does_bone_have_collision` returns
false, the bone is silently skipped and the export leaves `PhysicsLODGroup`
empty **without even a warning** — the file is produced but does nothing.

For every collision object:

```python
c = col_obj.constraints.new("COPY_TRANSFORMS")
c.target = frag_armature_obj
c.subtarget = "BoneName"
c.mix_mode = "BEFORE_FULL"   # same as set_child_of_constraint_space
c.target_space = "POSE"
c.owner_space = "LOCAL"
```

Also:
- `bone.sollumz_use_physics = True` **only** on a bone that has collision.
- `col_obj.child_properties.mass` defaults to 0; if it is left at 0 the archetype
  mass is 0 too. Distribute it by bound volume.
- If it must not break, `bone.group_properties.strength = -1`.
- The bound composite must be a **direct** child of the fragment armature,
  not under the drawable.
- More than one bound per bone is allowed (`child_cols` is grouped by
  bone name).

### THE PITFALL THAT WASTES THE MOST TIME: the root group

The group with `parentIdx = 255` is the **entity body**. Its collision is welded to the entity
transform and **does not follow the bone**. If you build a single-group fragment,
that group is necessarily the root; the export looks flawless,
`PhysicsLODGroup` comes out filled, but in game the animation plays and the collision
stays in place — you gain nothing.

**At least two groups are needed:**

```
group[0]  root bone (tag 0)   parentIdx=255   -> FIXED base/hinge
group[1]  moving bone         parentIdx=0     -> ROTATING part (door leaf, lid)
```

The moving part must be in the **child** group. Give the root group a
collision too (otherwise Sollumz skips that bone and you drop back to a single group) —
small parts on the rotation axis are ideal for this, because their
position does not change when they rotate.

Verification: in the `Groups` list the boneTag of the group with parentIdx=255 must be **0**;
the moving bone's tag must appear in the child group.

### physicsDictionary is never left at 0

Even if the collision is embedded in the `.ydr`/`.yft`, the game finds it through the
**archetype's physicsDictionary**. If you give 0, the model is visible but you walk
through it. In the vanilla archive not a single door prop has 0
(`v_ilev_gb_teldr` → 2110158618, `prop_ld_garaged_01` → 427433450).

On our own prop the right value is **its own name hash**: `-PhysicsDictSelf`.
`textureDictionary` can stay 0 if the textures are embedded.

### The ytyp side

`assetType` is a **property** (not a field); its type is
`rage__fwArchetypeDef__eAssetType`. For a fragment:

- `assetType = ASSET_TYPE_FRAGMENT` — if it stays drawable the game does not build per-bone
  collision, and all the work is wasted.
- `physicsDictionary = its own name hash` (not 0).
- `textureDictionary = 0` — Sollumz embeds the textures in the .yft.
- `specialAttribute = 0` — if a script plays the animation, this is not a door-system
  door.

`make_ytyp_override.ps1 -AssetType ASSET_TYPE_FRAGMENT -ClearDicts
-PhysicsDictSelf` produces this.

### Verification

The export saying "FINISHED" is not enough. Dump the .yft to XML with `res_to_xml.ps1` and check:
is `<Groups>` filled under `<Physics><LOD1>`, does the `<Children>` count equal the bound
count, is every `<BoneTag>` the tag of the right bone. If you have a working
reference fragment, compare the same fields side by side.


---

## Cloth goes into the wall — fragment `worldbound`

If a cloth hung on a wall **passes into the wall** in the wind, the fix is the fragment's
**World Bounds** field (not a script, not collision).

1. Bring the building **and** its ymap into Blender (for world coordinates); import your own ymap
   with **Instance Entities** on.
2. Create a **Bound Composite** named `<object>_worldbound`.
3. Add a **Bound Plane** inside it (Sollumz labels it *"cloth only"*).
4. ⭐ **A bound plane extends infinitely in every direction and affects ONLY the `.yft` it is linked
   to** — it does not touch the object next to it. Think of it as one face of a box.
5. **Turn on the Face Orientation overlay** — the normal must face the right side
   (in the example it was rotated 70° relative to the wall).
6. Fragment → Object Properties → **World Bounds** → pick the bound composite.
7. Bound plane: **default material**, **no flags at all**.
8. **Export only the `.yft`**; the bound is not exported separately.

- ⚠️ **If you move the cloth later, you have to redo the world bounds.**

**Measured:** Stumpy Mason 9 min (`NDYv0EnWvhg`), `notes/07` §3, 2026-09.
