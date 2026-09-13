# Bone tag catalogue — is the name fixed or the tag fixed?

**Trunk file.** Vehicle / weapon / ped bones: is the name fixed or the tag fixed — serves three branches at once. Moved: `trunk/bone-tags.md` (2026-09-05).

**Measured:** `data/skeletons.tsv.gz` — 478,055 rows, 52,399 models
(41,242 `.yft` + 11,157 `.ydr`), vanilla + all DLC.

This file does not answer *"what is this bone's tag"* but the question that comes before it:
**does the engine find this bone by its NAME or by its TAG?** Investing in the wrong side
produces a silent failure — the file compiles, the game raises no error, the bone is
never driven.

---

## 1. ⭐ Decision rule — apply this first

```
Look at how many DIFFERENT tags a bone name carries and
how many DIFFERENT names a tag carries:

  1 name -> 1 tag , in many models       =>  NAME FIXED    -> copy the name EXACTLY
  many names -> 1 tag (names differ in meaning) =>  TAG FIXED -> choose the name freely
```

Measurement code (repeatable):

```python
import gzip, collections
f = gzip.open('data/skeletons.tsv.gz','rt',encoding='utf-8')
hdr = f.readline().strip().split('\t')
mi, ni, ti = hdr.index('model'), hdr.index('boneName'), hdr.index('boneTag')
nm = collections.defaultdict(set)          # name -> set of models
nt = collections.defaultdict(collections.Counter)  # name -> tag counter
tn = collections.defaultdict(set)          # tag -> set of names
for line in f:
    r = line.rstrip('\n').split('\t')
    n = r[ni].lower()
    nm[n].add(r[mi]); nt[n][r[ti]] += 1; tn[r[ti]].add(n)
```

Measured result: **26,013 unique tags**. Of the names that appear in `>=50` models,
**559 carry a single tag** (name fixed), **30 carry more than one** (§6 pitfalls).
The tag-fixed family is very small and almost entirely **clocks** (§5).

⚠ **The FiveM script side and the file side are different layers.**
`GetEntityBoneIndexByName(veh, "door_dside_f")` uses the **NAME**;
`.ycd` channels, `.yed` outputs and `specialAttribute` drivers use the **TAG**.
What works on one side may not work on the other.

---

## 2. VEHICLE bones — name fixed, 100% stable

Measured on ~1,800 vehicles, every name in the list has **a single** tag (exceptions §6).
In FiveM, all vehicle prop attaching, damage, door, light and mod work comes from here.

### 2.1 Body / root

| name | tag | models |
|---|---:|---:|
| `chassis` | **0** | 1834 |
| `chassis_dummy` | 39433 | 1834 |
| `chassis_lowlod` | 37313 | 1470 |
| `bodyshell` | 60113 | 1816 |
| `stub` | **0** | 731 |

`chassis` and `stub` are tag 0, i.e. **the root** — not `bodyshell`.

### 2.2 Wheels / suspension

| name | tag | | name | tag |
|---|---:|---|---|---:|
| `wheel_lf` | 27922 | | `wheel_rf` | 26418 |
| `wheel_lr` | 27902 | | `wheel_rr` | 26398 |
| `wheel_lm1` | 29921 | | `wheel_rm1` | 5857 |
| `hub_lf` | 35926 | | `hub_rf` | 36022 |
| `hub_lr` | 35938 | | `hub_rr` | 36034 |
| `suspension_lf` | 5577 | | `suspension_rf` | 6505 |
| `suspension_lr` | 5589 | | `suspension_rr` | 6517 |
| `suspension_lm` | 5584 | | `suspension_rm` | 6512 |
| `wheelmesh_lf` | 20247 | | `wheelmesh_lr` | 20227 |
| `wheelmesh_lf_l1` | 11707 | | `wheelmesh_lr_l1` | 27353 |
| `wheelmesh_lf_l2` | 11708 | | `wheelmesh_lr_l2` | 27354 |
| `wheelmesh_lf_ng` | 12049 | | `wheelmesh_lr_ng` | 27695 |

`_l1`/`_l2` are LOD levels, `_ng` the next-gen variant.

### 2.3 Doors / windows / bonnet

| name | tag | | name | tag |
|---|---:|---|---|---:|
| `door_dside_f` | 60963 | | `door_pside_f` | 35346 |
| `door_dside_r` | 61071 | | `door_pside_r` | 35230 |
| `handle_dside_f` | 49152 | | `handle_pside_f` | 23407 |
| `handle_dside_r` | 49132 | | `handle_pside_r` | 23419 |
| `window_lf` | 26734 | | `window_rf` | 28174 |
| `window_lr` | 26746 | | `window_rr` | 28186 |
| `window_lm` | 26741 | | `window_rm` | 28181 |
| `windscreen` | 39561 | | `windscreen_r` | 56413 |
| `bonnet` | 42990 | | `boot` | 31608 |
| `bumper_f` | 22841 | | `bumper_r` | 22821 |
| `wing_lf` | 4218 | | `wing_rf` | 4186 |

`dside` = driver side, `pside` = passenger side. Windows/wheels use
`l`/`r` instead — **the same vehicle has two different naming systems**,
do not mix them up.

### 2.4 Lights

| name | tag | | name | tag |
|---|---:|---|---|---:|
| `headlight_l` | 10804 | | `headlight_r` | 10842 |
| `taillight_l` | 18400 | | `taillight_r` | 18438 |
| `brakelight_l` | 20608 | | `brakelight_r` | 20678 |
| `brakelight_m` | 20609 | | `platelight` | 5558 |
| `indicator_lf` | 41664 | | `indicator_rf` | 40032 |
| `indicator_lr` | 41644 | | `indicator_rr` | 40012 |
| `reversinglight_l` | 34500 | | `reversinglight_r` | 34570 |
| `doorlight_lf` | 11965 | | `doorlight_rf` | 11549 |
| `doorlight_lr` | 11977 | | `doorlight_rr` | 11561 |
| `interiorlight` | 37995 | | `dashglow` | 11869 |
| `extralight_1` | 51309 | | `extralight_2` | 51310 |
| `extralight_3` | 51311 | | | |
| `neon_l` | 49485 | | `neon_r` | 49491 |
| `neon_f` | 49479 | | `neon_b` | 49475 |
| `siren1` | 24999 | | `siren2` | 25000 |
| `siren3` | 25001 | | `siren4` | 25002 |

`siren1..4` are consecutive (24999+n) — if you need a higher one, continue the pattern.

### 2.5 Engine / exhaust / transmission

| name | tag | note |
|---|---:|---|
| `engine` | 30510 | |
| `engineblock` | 24668 | |
| `overheat` | 15850 | smoke emission point |
| `overheat_2` | 65271 | |
| `petroltank` | 23306 | · `_l` 50131 · `_r` 50009 |
| `transmission_f` | 17066 | `_m` 17073 · `_r` 17046 |
| `exhaust` | 4944 | |
| `exhaust_2..9` | 50446–50453 | **consecutive** |
| `exhaust_10..16` | 64213–64219 | **separate block**, jumps after 9 |

⚠ The exhaust numbering **changes block going from 9 to 10**
(50453 → 64213). Do not generate it with a formula, use the table.

### 2.6 Interior / seats

| name | tag | | name | tag |
|---|---:|---|---|---:|
| `seat_dside_f` | 20012 | | `seat_pside_f` | 59562 |
| `seat_dside_r` | 20120 | | `seat_pside_r` | 59446 |
| `seat_dside_r1` | 35183 | | `seat_pside_r1` | 33327 |
| `seat_dside_r2` | 35184 | | `seat_f` | 23191 |
| `steeringwheel` | 20285 | | `dials` | 16572 |
| `handlebars` | 49213 | | `hbgrip_l` | 46652 |
| `hbgrip_r` | 46530 | | | |

### 2.7 Mod / extra / misc

| name | tag |
|---|---:|
| `misc_a` … `misc_z` | 58614 … 58639 (**consecutive from a to z**) |
| `mod_col_1` … `mod_col_9` | 17880 … 17888 (**consecutive**) |
| `mod_col_10` | **24604** ⚠ pattern breaks |
| `extra_1` … `extra_4` | 8874 … 8877 |
| `extra_11` / `extra_12` | 10843 / 10844 ⚠ separate block |
| `extra_ten` | 41970 ⚠ name spelled out |
| `slipstream_l` / `_r` | 33128 / 33134 |
| `weapon_1a`/`1b` | 42814 / 42815 |
| `weapon_2a`/`2b` | 42862 / 42863 |
| `turret_1base` | 65015 |
| `turret_1barrel` | 45666 · `turret_2barrel` 22942 · `turret_3barrel` 52239 |

⚠ **Three pattern breaks measured**: `mod_col_10`, `extra_ten` (a word, not a
digit!), `extra_11/12`. `misc_*` runs a→z without a gap. Do not trust a formula.

### 2.8 Aircraft / motorcycle / boat

| name | tag |
|---|---:|
| `rudder` | 30979 |
| `wing_l` | 33042 |
| `forks_u` / `forks_l` | 25308 / 25427 |
| `swingarm` | 61088 |
| `bikedisc_f` / `_r` | 60125 / 60105 |
| `wheelmeshbk_f` / `_r` | 19998 / 19882 (+ `_l1`,`_l2`,`_ng`) |

---

## 3. WEAPON bones — name fixed

| name | tag | models | role |
|---|---:|---:|---|
| `gun_root` | **0** | 327 | root |
| `gun_main_bone` | 3360 | 342 | main body |
| `gun_muzzle` | 17833 | 243 | muzzle — **ptfx/light goes here** |
| `gun_gripr` / `gun_gripl` | 18308 / 18302 | 329 / 158 | right/left grip |
| `gun_trigger_pr` | 56099 | 217 | trigger (finger) |
| `gun_trigger` | 23712 | 20 | trigger (mechanical) |
| `gun_cock1` / `gun_cock2` | 39439 / 39440 | 187 / 45 | charging handle |
| `gun_vfx_eject` | 28405 | 195 | **shell ejection point** |
| `gun_hammer` | 24730 | 67 | hammer |
| `gun_safety` | 53712 | 78 | safety |
| `gun_breach` | 24367 | 39 | |
| `gun_ammo` | 18561 | 24 | |
| `gun_sumuzzle` | 19851 | 47 | suppressor muzzle |

**Component (attachment) slots** — `wap*` prefix:

| name | tag | role |
|---|---:|---|
| `wapclip` | 1477 | magazine |
| `wapscop` / `wapscop_2` | 64805 / 3634 | scope |
| `wapsupp` / `wapsupp_2` | 4230 / 6180 | suppressor |
| `wapflshlasr` / `_2` | 4396 / 24320 | flashlight / laser |
| `wapgrip` / `wapgrip_2` | 19397 / 44079 | foregrip |

⚠ **Bones with the `aap*` prefix carry tag 0** (`aapclip` 198 models, `aapbarrel` 27,
`aapcamo` 122) — they are the component model's **own root**, not a slot on the main
weapon. `wap*` is the slot, `aap*` is the root of the attached part. Mixing them up
gives "the part attaches but in the wrong place".

---

## 4. PED bones

Critical values confirmed by the measurement (1,115 ped models):

| name | tag | | name | tag |
|---|---:|---|---|---:|
| `SKEL_ROOT` | **0** | | `SKEL_Head` | **31086** |
| `SKEL_Pelvis` | 11816 | | `SKEL_Spine_Root` | 57597 |
| `SKEL_Spine0..3` | 23553 / 24816 / 24817 / **24818** | | `SKEL_Neck_1` | 39317 |
| `SKEL_L_Thigh` | 58271 | | `SKEL_R_Thigh` | 51826 |
| `SKEL_L_Calf` | **63931** | | `SKEL_R_Calf` | **36864** |
| `SKEL_L_Foot` | **14201** | | `SKEL_R_Foot` | **52301** |
| `SKEL_L_UpperArm` | 45509 | | `SKEL_R_UpperArm` | 40269 |
| `SKEL_L_Forearm` | 61163 | | `SKEL_R_Forearm` | 28252 |
| `SKEL_L_Hand` | 18905 | | `SKEL_R_Hand` | 57005 |
| `PH_L_Hand` | 60309 | | `PH_R_Hand` | 28422 |
| `IK_L_Hand` | 36029 | | `IK_R_Hand` | 6286 |
| `FACIAL_facialRoot` | 65068 | | | |

(The Calf/Foot values were once written swapped in older notes — the columns here
are measured from 1,107 models.)

---

## 5. TAG-FIXED family — here the rule flips

The only clean example is **the clock**: tags **417 / 418 / 419** carry 3 / 10 / 8
**different bone names** respectively. The name is completely free, the tag is mandatory.

The other candidate (`traffic_light_0/1` ↔ 16665/16666) is **name fixed**, not tag
fixed — a one-to-one mapping, one name one tag.

In vanilla, **238** of the 26,013 tags carry ≥4 different names; on inspection most of them
fall into two harmless groups:

- **hash collision** — a meaningless coincidence (`des_glass94_frag_003` and
  `ik_l_foot` on the same tag)
- **a deliberately shared connection point** — arena pipe pieces
  (`prop_arena_pipe_*_start` / `_end`) share a tag to snap onto each other;
  31 different names on one tag. This is a *snap* system, not an engine driver.

⚠ So "many names → one tag" is **not enough on its own**; the names must differ *in meaning*
(Hour vs Min vs MH vs HH). Look at the meaning, not the count.

---

## 6. ⛔ Pitfalls — measured unstable names

There are 30 names that appear in `>=50` models and carry **more than one tag**. In each, one
tag has an overwhelming majority, the other is in 1-2 models. **The minority value is a FAULTY file.**

| name | right tag | deviant tag | carried by |
|---|---:|---:|---|
| `SKEL_Head` | **31086** (1338) | 21030 (1) | `a_c_whalegrey` |
| `SKEL_Pelvis` | **11816** | 56200 (1) | `a_c_whalegrey` |
| `SKEL_Spine_Root` | **57597** | 11569 (1) | `a_c_whalegrey` |
| `PH_R_Hand` | **28422** | 7966 (6) | `rifle_grip_mesh`, `a_c_poodle` |
| `MH_R_Elbow` | **2992** | 62460 (2) | `player_zero`, `p_michael_02` |
| `MH_L_Knee` | **46078** | 30464 (2) | `player_zero`, `p_michael_02` |
| `RB_Neck_1` | **35731** (1203) | 14728 (86) | — wide distribution, careful |
| `exhaust_3` | **50447** | 4944 (1) | the exhaust root's tag |
| `gun_main_bone` | **3360** (940) | 0 (29) | written as the root |

### ⭐⭐ The `a_c_whalegrey` finding — joins two notes

An earlier note already said: *"do not reach for `a_c_whalegrey` — it has no entry in `peds.json` /
`PedList.ini` and has **0 clips**."* Now **the reason is measured**:

This model's `SKEL_Head` / `SKEL_Pelvis` / `SKEL_Spine_Root` tags are not canonical
(**21030 / 56200 / 11569**). Because `.ycd` channels bind by tag,
no vanilla ped clip can fit this skeleton. **"0 clips" is not a gap,
it is the result of this tag deviation.**

⚠ And `21030` is exactly the number behind the known pitfall *"Sollumz's automatic tag formula
computes 21030 for `SKEL_Head`, the real one is 31086"*. So we have
**a real shipped asset carrying a formula-generated tag**, and
it does not work in the game. This is the most concrete proof of the "enter the tag by hand" rule.

### Other silent breakers

- **Facial bone name difference `.ydd` ↔ `.yft`**: `FB_*_000` vs `FB_*_045`,
  on 21 bones. Same tag, different name. Blender binds by name, so the face never
  deforms and raises no error either.
- **Counting `skeletons.tsv.gz` rows is not counting bones** — there is `.yft`+`.ydd`
  duplication and repetition. The right field is `boneCount`.
  (`a_c_mtlion_02` → 144 rows, 72 real bones.)
- **Sollumz leaves the `Flags` field at zero**; a bone with zero flags accepts no
  transform. ⛔ But `119` is not a constant, it is **a permission set**
  (`Rot*|Trans*`, NO scale bit). If the clip drives bone **scale**, `1911`
  (root `6007`) is needed; otherwise the scale channel is silently dropped. Derive the flag
  from the clip — see `branches/map/destruction.md` §Link D.

---

## 7. Which question, where to look

| question | place |
|---|---|
| vehicle door/light/prop attaching | §2 — use the **name** |
| weapon component, muzzle ptfx, shell | §3 — `wap*` slot, `aap*` part root |
| ped bone | §4 · `assetdb.py bones <ped>` |
| hour/minute hand, traffic light | §5 |
| a model's own skeleton | `assetdb.py bones <model>` |
| does this clip fit this model | `assetdb.py clipfit` |
| ytyp/ymap flag | `trunk/flags.md` (§2.1 real distribution) |
