<img src="assets/logo.png" alt="muto-atlas" width="128" align="right">

# muto-atlas

**Ground truth for FiveM / GTA V development.** A Claude Code plugin that answers
questions about the game's actual data instead of guessing.

[Türkçe dokümantasyon →](docs/README.tr.md)

---

## The problem

You want a door to open. You try `AddDoorToSystem` — nothing. `FreezeEntityPosition` —
nothing. `SetEntityDynamic`, `NetworkRequestControlOfEntity`... half an hour gone.

The answer was one line in the game's own `.ytyp`:

```
specialAttribute = 0   → this object is NOT a door. It has no hinge in the door system.
```

One query would have said so before the first line of code:

```bash
assetdb.py door v_ilev_gb_teldr
```

That is the whole idea. **Look at the data first, then write the code.**

## What it gives you

25 offline data layers, built from **your own** GTA V install and FiveM server:

| layer | rows | what it answers |
|---|---:|---|
| archetypes | 316,975 | is it a door, where is the pivot, does it have physics |
| world entities | 3,054,420 | where in the world is this model placed |
| ymap LOD chains | 3,145,882 | why does it flicker / disappear at distance |
| animation clips | 315,964 | duration, track count, which skeleton |
| animation names | 269,414 | dictionary + clip for `TaskPlayAnim` |
| skeleton bones | 478,055 | bone name ↔ tag ↔ parent |
| world objects | 33,912 | **labelled** ATMs, CCTVs, benches… with **rotation** |
| props | 21,631 | spawnable with `CREATE_OBJECT` |
| framework API | 12,713 | every export/event/command your server actually defines |
| natives | 7,191 | signature, apiset (client/server/shared), hash |
| ytyp extensions | 64,209 | particle, ladder, light, expression extensions |
| particle effects | 2,549 | valid `fxName` for `StartParticleFx*` |
| expressions | 2,338 | procedural bone motion, springs |
| peds | 1,109 | clip dictionary, expression set, movement clipset |
| vehicles | 921 | handling id, mod kits, extras |
| IPLs | 895 | bounds, for `RequestIpl` / `RemoveIpl` |
| MLO interiors | 853 | every world placement of every interior |
| timecycle modifiers | 1,087 | why an interior is dark — ambient multipliers, exposure, fog |
| weather cycles | 17 | the base layer under the modifier — ambient + sun at any hour |
| embedded lights | 72,539 | every light in every `.ydr`/`.yft`/`.ydd` — hours, cone, falloff, flags |
| weapons + parts | 184 + 634 | components, liveries, attach bones |
| …plus | | shaders, collision materials, decals, procedural, scenarios |

Plus a **Lua linter** that catches invented natives, client-only natives called on the
server, wrong argument counts, and per-frame performance mistakes.

## Install

**Step 1 — install the plugin** (two commands, no cloning):

```bash
claude plugin marketplace add B7Kompirine/muto-atlas
claude plugin install muto-atlas@muto-atlas
```

Restart Claude Code. You now have **22 commands** and **2 skills**
(`fivem-natives`, `fivem-assets`).

| | |
|---|---|
| **Ask the data** | `/asset` `/native` `/where` `/anim` |
| **Author assets** | `/ped` `/retarget` `/clipset` `/yed` `/weapon` `/weaponfx` `/3dnui` `/rayfire` |
| **Light & scene** | `/light` `/scene` |
| **Check & build** | `/asset-setup` `/asset-build` `/native-lint` |
| **Tool paths** | `/paths` `/codewalker` `/gta` `/server` `/blender` |

> The skills are part of the plugin — you do **not** install them separately.
> They trigger automatically when you work on FiveM assets, natives, rigging or
> animation, even if you never type a command.

**Step 2 — build the data layers.** The plugin ships with no game data, so the
commands have nothing to answer with until you do this. **You need GTA V and
CodeWalker** — you almost certainly already have both; what's missing is only the
*paths*:

```bash
python scripts/setup.py --save \
  --gta        "C:\Program Files\Epic Games\GTAV" \
  --codewalker "C:\...\CodeWalker\CodeWalker.Core.dll" \
  --resources  "C:\...\your-server\resources"
```

`--save` writes the paths to `data/config.json`; you are never asked again.

Inside Claude Code just run **`/asset-setup`** — it detects what it can, asks you
for whatever is missing, and builds everything. That is the easiest route.

Verify with `/asset-setup` or:

```bash
python scripts/assetdb.py stats
```

`scripts/` lives in the installed plugin directory, which Claude Code reports as
`${CLAUDE_PLUGIN_ROOT}` (typically `~/.claude/plugins/cache/muto-atlas/muto-atlas/<version>`).

**Why no data ships with the repo:** `entities.db` alone is 214 MB — over GitHub's
100 MB file limit — and it is Rockstar's data. It is built locally instead. A useful
side effect: everyone's layers come from *their* game version, not from a frozen copy.

## Usage

```bash
assetdb.py door    v_ilev_gb_teldr        # will the door system move this?
assetdb.py show    prop_atm_01            # full record + verdict
assetdb.py where   prop_atm_01            # every world placement
assetdb.py world   --near 147,-1035,29 --radius 50   # what's around this point
assetdb.py pedmeta a_c_rottweiler         # clip dict, expression, movement clipset
assetdb.py weapon  WEAPON_CARBINERIFLE --parts       # components + attach bones
assetdb.py vehicle adder                  # handling id, mod kits, extras
assetdb.py mlo     v_genbank              # interior + all its world locations
assetdb.py anim    weld                   # dictionary + clip + duration
assetdb.py fx      <name> --exact         # is this a real particle effect?
assetdb.py framework --check              # exports/events that will fail at runtime
assetdb.py stats                          # what is installed, what is missing
```

### Where do my tools live?

Every external path lives in one registry (`data/config.json`, which is
gitignored — personal paths never reach the repo). Ask it, or set it:

```bash
assetdb.py path                       # show all, marked found / missing
assetdb.py path codewalker            # where is CodeWalker.Core.dll?
assetdb.py path gta "D:\Games\GTAV"   # set it
assetdb.py path gizmo "C:\Tools\Gizmo.exe"   # any name you like
```

Slash commands: `/paths`, `/codewalker`, `/gta`, `/server`, `/blender` — with no
argument they report the location, with a path they set it.

This used to be **29 copies** of a guessed CodeWalker path and **23** of a
guessed GTA folder, one per script; installing a tool somewhere unusual meant
editing twenty files. They now all read the one registry. A path that is not on
disk is rejected at set time, and "written in config but missing on disk" is
reported as its own case — it is the most common cause of "I set it and it
still doesn't work".

### Scenes: several objects, clip decoding, and a ymap placement

```bash
assetdb.py scene --file scene.json --add a.ydr --add b.yft
assetdb.py scene --file scene.json --anim "door.ycd:door_open"
assetdb.py scene --file scene.json                 # summary + clip check
assetdb.py scene --file scene.json --ymap out.ymap # write the placement
```

The `.ycd` is decoded into per-frame bone channels, so a clip's real frame
count, duration and which bones it actually drives are known without launching
the game. Six channel types are handled, including `CachedQuaternion` — which is
a *pointer*, not a channel: it names the dropped component, and the missing one
is rebuilt as `sqrt(1-Σ)` with the sign taken from the type name. Verified
across 47,499 rotation frames: zero non-unit quaternions, max deviation
1.72e-08.

The ymap is written with extents computed from the union of the entities and is
**read back** to confirm the entity count before it is accepted; an entity
outside the extents renders nothing at all, with no error.

### Checking your own files, before the game sees them

The commands above answer questions about *vanilla*. These three inspect **your**
files — so a broken asset costs you a check, not a full reconnect cycle.

```bash
assetdb.py doctor  stream/ -r            # silent-failure gate: what will fail without an error
assetdb.py diff    mine.yft vanilla.yft  # which NODES differ (not which values)
assetdb.py light   prop_lamp.ydr         # decode embedded lights: hours, cone, falloff, flags
assetdb.py light   --table               # measured vanilla light reference
```

### Editing a prop light

```bash
assetdb.py light prop_lamp.ydr                          # decode it
assetdb.py light prop_lamp.ydr --table                  # measured vanilla band
assetdb.py light prop_lamp.ydr --apply edit.json       # write back, verified
assetdb.py light prop_lamp.ydr --set 0.Intensity=8 --set 0.ConeOuterAngle=35
assetdb.py light prop_lamp.ydr --add | --remove 1         # add / remove a light
```

Values are judged against the **measured vanilla distribution** — p05, median
and p95 per field across the embedded lights in your own install (72,539 lights
in 4,476 files here), computed live from the layer. If the layer is not built,
no range is offered at all; an invented one would be worse than none.

Three things it gets right that cost real time when they are wrong:

- **The light hangs off a bone, not the model origin.** In `prop_worklight_01a`
  the light sits on `BoneId 41615`, 1.737 m up the chain; skip the bone chain and
  it renders on the floor. `Position`/`Direction` are in **bone space**.
- **`TimeFlags` is a set of hours, not a number.** `14680095` means 21:00–05:00,
  so at 20:00 the light is off. When someone says "my light doesn't work", this
  is the first thing to check — usually the light is fine and the hour is not.
- **File size proves nothing** (RSC7 is zlib — identical content went 15,056 →
  15,904 bytes). Every write is verified by **reading the file back**; if the
  light count does not match, the file is left untouched and the original is
  kept as `.yedek`.

**Provenance.** This is an independent implementation. The lighting formulas are
derived from the game's own shader files (`lighting_common.fxh`, `common.fxh`,
`postfx.fx`) and verified against measurements; the reference bands are computed
locally from your own GTA V install and never redistributed (`data/` is
gitignored). No code, assets, UI, names or branding from any third-party editing
tool are included.

### Why is my interior dark?

Darkness has three layers, and the answer is usually not the third:

```bash
assetdb.py cycle w_clear --hour 20            # 1. base weather cycle at that hour
assetdb.py timecycle int_hospital_dark        # 2. the room's modifier
assetdb.py light prop_lamp.ydr                # 3. the prop's own light
```

`cycle` evaluates the weather timecycle itself. Its keyframes are **not** hours:
there are 13 of them and their times live in `time.xml` — where one sample is
named `09:00` but carries `hour="10"`, so trusting the name shifts everything
after it by an hour.


Usually the answer is not in your prop and not in your light — it is the room's
**timecycle modifier**, which overrides ambient light, exposure and fog.

```bash
assetdb.py timecycle --mlo my_interior.ytyp   # each room → its modifier → ambient values
assetdb.py timecycle int_hospital_dark        # what that modifier actually changes
assetdb.py timecycle --ara hospital           # find modifiers by name
```

The room stores its modifier as an unresolved JOAAT hash (`hash_CDE50982`);
`--mlo` hashes the 1,087 known modifier names and resolves it back to
`int_extlight_small`, then shows the two multipliers that decide whether an
unlit surface is visible at all. When both are `0.000`, nothing that isn't
directly lit will render — no prop setting can compensate for that.

Same modifier name is often defined in several DLCs (691 of 1,087 are). Which
one wins depends on DLC load order and **cannot** be read from the files, so
the conflict is reported rather than hidden.

`doctor` reads `.ycd`, `.ytyp` (incl. MLO rooms/portals), `.ydr` and `.yft`, and
reports three severities: **FATAL** (game crashes / the whole resource dies),
**SILENT** (fails with no error at all — the expensive class), **WARN** (unusual).
Files it could not inspect are listed separately and are **never** counted as clean.

`diff` compares node *presence*, not field values. A Sollumz export can pass with
"0 warnings" and still crash the game because a node is missing entirely; no
value-by-value check finds that, a node-set comparison does.

Every rule is backed by a measurement recorded next to it in the source — e.g.
the MLO entity-flag check rests on 118 vanilla MLOs / 18,799 entities, in which
bit 8 is never set even once.

Where the measurement does **not** settle the question, the tool says so instead
of guessing. `TimeFlags 0` appears in only 8 of 72,539 vanilla lights — but those
8 are interior lamp props, so "never lights" and "no time restriction" are both
consistent with the data. That check is reported as *suspicious, verify in game*,
not as a defect.

Two skills (`fivem-natives`, `fivem-assets`) trigger automatically on relevant work —
you don't have to call the commands by hand.

## Exit codes matter

```
0  found
1  the query ran; the name is not in the authority
2  the data layer is not installed — NOTHING can be claimed about the result
3  internal error (corrupt file)
```

Reading `2` as `1` means mistaking *missing data* for *a missing asset*, and then
guessing. That is exactly the failure this plugin exists to prevent. `stats` never
returns `2` — it is the command that tells you what's missing.

`doctor`, `diff` and `light` inspect files rather than query a layer, so their
codes read slightly differently — but `2` keeps the same meaning:

```
doctor   0 clean   1 findings        2 at least one file COULD NOT be inspected
diff     0 same    1 structural diff 2 a file could not be read
light    0 lights  1 no lights       2 the file could not be read
```

## Language

Output is English by default. Turkish is available:

```bash
assetdb.py --lang tr ...          # per call
export MUTO_ATLAS_LANG=tr         # per shell
python scripts/setup.py --lang tr --save   # persistent
```

## Design rules

These are not style preferences; each one was learned from a silent failure.

- **Measure, don't assume.** Every number in the docs has a command that produced it.
- **A tool showing nothing is not proof that nothing is there.** Missing rows ≠ missing
  asset; a missing property on a foreign object returns `None`, and `None.length` is `0`.
- **Names are stored as the source writes them; joins are always case-folded.** Dump
  names are `MixedCase`, plugin layers are lowercase — a literal join silently returns
  zero on every family.
- **Every write is read back.** "The command didn't error" is not proof that anything
  was written.
- **Missing translations print the key**, never an empty string, so gaps stay visible.

## License

MIT — see [LICENSE](LICENSE). Code only.

No GTA V data is distributed here. GTA V and its assets are property of Rockstar Games.
This project is not affiliated with Rockstar Games, Take-Two Interactive, or Cfx.re.

Built by **muto**.
