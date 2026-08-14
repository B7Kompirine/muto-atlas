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

24 offline data layers, built from **your own** GTA V install and FiveM server:

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

Restart Claude Code. You now have **14 commands** (`/asset`, `/native`, `/where`,
`/anim`, `/ped`, `/yed`, `/clipset`, `/3dnui`, `/weapon`, …) and **2 skills**
(`fivem-natives`, `fivem-assets`).

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
