# Vehicle bones, mods, extras, handling — queries and bone names

**When to read:** you will script a vehicle's door/window/hood/light/exhaust/siren/mod bone; you need `handlingId`, modkit, extras or class — query the spec sheet instead of guessing.
**Source:** `trunk/bone-tags.md` §2 (193 names, 100% tag-stable) · `assetdb.py vehicle` (921 vehicles) · **Measured:** 478,055 skeleton rows
**Read first:** `branches/vehicle/_branch.md`

---

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" vehicle <name>      # handlingId, modkit, extra, class, seats
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" bones <model>       # the vehicle's real skeleton (name + tag)
```

## On vehicle bones the NAME is fixed — copy the name exactly

The full catalogue and the pitfalls are in `trunk/bone-tags.md` §2 and §6; summary here.

### Categories

Body/root · wheel/suspension · door/window/hood · lights · engine/exhaust/transmission · interior/seat · mod/extra/misc · aircraft/motorbike/boat — names and tags in `trunk/bone-tags.md` §2.1-2.8 (single copy).
