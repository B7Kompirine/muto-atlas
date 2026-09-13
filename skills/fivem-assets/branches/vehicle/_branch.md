# Vehicle — branch rules

Command: `/vehicle`
**Keywords:** vehicle, car, automobile, car door, car bone, handling, handlingId, handling.meta, modkit, SetVehicleModKit, extra, SetVehicleExtra, vehicle class, seat, vehicle bone, door_dside_f, door bone, window, hood, siren, exhaust, wheel, livery, debadger, tint
**What belongs here:** **A vehicle** — its bones, handling, modkit/extras, spec sheet. Boundary: the vehicle's texture or paint → `/look`.

> The keywords above are **accelerators, not a complete list.** If a word is not on the list,
> routing does not stop — this definition is used. *“roller shutter”* is not on the list, but it is still a door object.


## Valid for every leaf in this branch

⚠️ **Thin branch.** Vehicle modelling/setup videos were **removed from the Sollumz extraction on request**; the atlas has two measured things for vehicles:
bone names and the vehicle spec sheet. If a vehicle build is done, its measurements go here.

- **On vehicle bones the NAME is fixed, 100% tag-stable** (193 names: door/window/hood/wheel/light/engine/exhaust/seat/mod/extra/siren) —
  copy the name exactly, find it with `GetEntityBoneIndexByName`. Weapons and peds can be the opposite → `trunk/bone-tags.md` §1 decision rule.
- **The spec sheet is queried, not guessed:** `assetdb.py vehicle <name>` → `handlingId`, modkit, extra, class, seats (921 vehicles).
- If an external tool brought a number or table (Five Toolkit debadger, tint), it is **a claim** → `sources/external-tools.md` label system.
- For vehicle texture/shader (`vehicle_paint*`, livery) the texture rules are in `branches/look/_branch.md`; vehicle collision flags in `trunk/flags.md` §8.

## Leaves

| wanted | file | status — source |
|---|---|---|
| Bone / mod / extra / handling query | bones-and-mods.md | measured — trunk/bone-tags §2 · assetdb vehicle |
| External tool — debadger, removed vehicle videos | external-tools.md | external source — sources/external-tools §1k · sollumz-discord (removed) |

## Trunk files to read
- `trunk/bone-tags.md` §2 (full table), §6 (unstable names) · `trunk/flags.md` §8 collision · `sources/external-tools.md` §1k
- `trunk/verification-ladder.md` — skeleton/spec sheet read back
