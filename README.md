<img src="assets/logo.png" alt="muto-atlas" width="128" align="right">

# muto-atlas

**Ground truth for FiveM / GTA V development.** A Claude Code plugin that answers
questions about the game's actual data instead of guessing.

[Türkçe dokümantasyon →](docs/README.tr.md) · [![checks](https://github.com/B7Kompirine/muto-atlas/actions/workflows/checks.yml/badge.svg)](https://github.com/B7Kompirine/muto-atlas/actions/workflows/checks.yml)

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
| timecycle modifiers | 1,087 | why an interior is dark — ambient multipliers, exposure, fog |
| weather cycles | 17 | the base layer under the modifier — ambient + sun at any hour |
| embedded lights | 72,539 | every light in every `.ydr`/`.yft`/`.ydd` — hours, cone, falloff, flags |
| weapons + parts | 184 + 634 | components, liveries, attach bones |
| …plus | | shaders, collision materials, decals, procedural, scenarios |

Plus a **Lua linter** that catches invented natives, client-only natives called on the
server, wrong argument counts, and per-frame performance mistakes.

### Measured build rules, not folklore — organised as a tree

Some answers are not a row in a table — they are a number you only get by measuring
vanilla and your own output side by side. Those live in the `fivem-assets` skill as a
**trunk / branch / leaf** tree, so a task loads one branch and one leaf, not 30 files:

- **Trunk** (`SKILL.md` + `trunk/`) — rules that hold everywhere: engine invariants,
  the tool-trap catalogue (Sollumz, Blender, CodeWalker, PowerShell, FiveM runtime),
  the verification ladder, flag tables, bone-tag rules.
- **Branches** (`branches/<branch>/_branch.md`, one slash command each) — category-wide rules:
  `map` · `prop` · `clothing` · `particle` · `look` · `vehicle`.
- **Leaves** (`branches/<branch>/<leaf>.md`, 31 of them) — one task each, named by what is
  wanted, never by the project it came from. "Road collapse", "bridge collapse" and
  "explosion" are one leaf: destruction.

Every leaf states what it measured, on what, and what it never checked. Two examples:

- **Parallax (`*_pxm`)** — which of the 16 variants vanilla actually uses (571 uses;
  `normal_spec_pxm` 218, `normal_pxm` only 3, so the obvious pick is the wrong one),
  the parameter bands read field by field off a shipped MLO and cross-checked against
  Sollumz's own `Shaders.xml`, and the one test that tells parallax apart from real
  geometry: **a real recess looks deepest head-on, parallax looks flattest**.
  Command: `/look`.
- **Vanilla interior measurements** — corner bevels cluster at **17 mm** with chamfered
  edges outnumbering hard 90° ones **11 : 1**; shadows come from a **separate low-poly
  mesh**, not from lights; dirt and blood are **separate overlay meshes**; the widely
  repeated "green at the bottom, blue at the top" vertex-colour rule **does not
  reproduce** in `v_coroner`. Measured, with the sample size and the limits stated.

Both say plainly what was measured, what was inferred, and what was never checked.

The plugin also checks **itself**:

```bash
python scripts/audit_plugin.py     # exit 1 if anything is broken
python scripts/check_repo.py       # scripts, data tables, public text, links
```

It catches the failures that never raise an error: a command pointing at a
reference that does not exist, a reference nothing links to, a `.ps1` with
non-ASCII text but no BOM (PowerShell 5.1 misreads it), a command whose
frontmatter drifted from the convention.

## Install

**Step 1 — install the plugin** (two commands, no cloning):

```bash
claude plugin marketplace add B7Kompirine/muto-atlas
claude plugin install muto-atlas@muto-atlas
```

Restart Claude Code. You now have **19 commands** and **2 skills**
(`fivem-natives`, `fivem-assets`).

| | |
|---|---|
| **Ask the data** | `/asset` `/native` `/where` `/anim` |
| **Branches** (rules + leaves) | `/map` `/prop` `/clothing` `/particle` `/look` `/vehicle` |
| **Check & build** | `/asset-setup` `/asset-build` `/native-lint` `/help` |
| **Tool paths** | `/paths` `/codewalker` `/gta` `/server` `/blender` |

> The skills are part of the plugin — you do **not** install them separately.
> They trigger automatically when you work on FiveM props, maps, materials,
> particles or natives, even if you never type a command.

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
Your server's framework index and `data/config.json` (your paths) never leave your
machine.

## Knowledge database — projects, snippets, tags

`scripts/build_atlas_db.py` turns the knowledge tree into one SQLite file, `data/atlas.db`.
It is generated locally and never committed.

- **Projects come from folder names.** Each branch folder (`map`, `prop`, `look`, …), the trunk
  (`trunk`), the sources (`sources`) and `fivem-natives` is a project. Add your own notes with
  `--source path/to/notes`; every subfolder of it becomes a project.
- **Every file is split into snippets:** one per heading, with code blocks as separate snippets.
  Long sections are split at blank lines, never cut mid-line.
- **Claude tags every snippet** from a fixed vocabulary (`claude-opus-5` by default; `--model` and
  `--effort` to change). Tags are cached by content hash: a rebuild — or a rerun after an
  interrupted one — only sends snippets that have no tags yet. Requests to `claude-opus-5` enable
  server-side refusal fallbacks (`fallbacks: "default"`). Without the `anthropic` package or
  credentials the build says so and uses offline keyword rules.
- **Full-text search** (SQLite FTS5) from the command line, or through the MCP server's
  `snippet_search`, `snippet_read` and `snippet_tags` tools.
- **Exit codes:** 0 found / written · 1 no hit · 2 database missing, or Claude requested but not
  available (nothing written) · 3 database unreadable or verification failed (the old file is kept).

```bash
python scripts/build_atlas_db.py                         # auto: Claude when available, else rules
python scripts/build_atlas_db.py --tagger claude         # python -m pip install anthropic + credentials
python scripts/build_atlas_db.py --source path/to/notes  # your folders become projects
python scripts/build_atlas_db.py --search "TimeFlags" --project look
python scripts/build_atlas_db.py --stats
```

## Other AI tools

muto-atlas is not tied to Claude Code. There are two routes; use either or both.

### Agent Skills — Codex, ChatGPT desktop, Cursor, GitHub Copilot, Gemini CLI

The two skills follow the open [Agent Skills](https://agentskills.io/specification) format.
Clone the repository, build the data layers once (Step 2 above), then install the skills into
your tool's skills folder:

```bash
python scripts/install_skills.py                  # ~/.agents/skills (Codex, ChatGPT desktop, Gemini CLI, VS Code Copilot, Cursor)
python scripts/install_skills.py --tool cursor    # ~/.cursor/skills
python scripts/install_skills.py --tool copilot --project path/to/your/repo   # .github/skills
python scripts/install_skills.py --check          # validate only, write nothing
```

The installer copies each skill, rewrites the Claude Code path variable to the absolute path of
your clone, and reads the copy back. Re-run it after `git pull`; the copies do not update
themselves. The slash commands stay Claude Code only.

### MCP server — Cursor, VS Code, Claude Desktop, Codex, Gemini CLI, ChatGPT

`scripts/mcp_server.py` exposes the same queries as MCP tools: asset and door lookups, animation
and particle names, flag decoding, native checks, the knowledge tree, and — locally only —
`doctor`, structural diff, light decoding and the Lua linter. Every result starts with its exit
code and what that code means. It needs the `mcp` Python package, version 1.x (tested with 1.28
and 1.30; mcp 2.x renamed the server API and is not supported yet):
`python -m pip install "mcp>=1.28,<2"`.

Claude Desktop (`claude_desktop_config.json`), Cursor (`~/.cursor/mcp.json`) and Gemini CLI
(`~/.gemini/settings.json`) use this shape; VS Code (`.vscode/mcp.json`) takes the same entry
under `"servers"` instead of `"mcpServers"`:

```json
{
  "mcpServers": {
    "muto-atlas": {
      "command": "python",
      "args": ["C:/path/to/muto-atlas/scripts/mcp_server.py"]
    }
  }
}
```

Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.muto-atlas]
command = "python"
args = ["C:/path/to/muto-atlas/scripts/mcp_server.py"]
```

**ChatGPT** connects only to remote servers (streamable HTTP or SSE), through Developer mode
(Plus, Pro, Business, Enterprise, Education — Settings → Security and login → Developer mode).
Run the server in HTTP mode and put an HTTPS tunnel in front of it:

```bash
python scripts/mcp_server.py --http --port 8765 --allow-host your-tunnel.example.com
```

Then create a developer-mode app in ChatGPT with `https://your-tunnel.example.com/mcp`.
⚠️ In HTTP mode the tools that read your own files or your own server's map (`doctor`,
`structural_diff`, `light_read`, `lua_lint`, `framework_api`, `lodaudit`) are not registered,
because a tunnel puts the server on the internet with no authentication. If you built the data
layers with your server folder, your custom archetype names can still be queried. Every tool is
marked read-only (`readOnlyHint`). Close the tunnel when you are done.

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
locally from your own GTA V install and never redistributed. No code, assets, UI,
names or branding from any third-party editing tool are included.

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
assetdb.py timecycle --search hospital        # find modifiers by name
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

## Contributing

Corrections, new measurements and bug reports are welcome — in **English or
Turkish**. Start with [CONTRIBUTING.md](CONTRIBUTING.md)
([Türkçe](docs/CONTRIBUTING.tr.md)). Issues labelled
[`good first issue`](https://github.com/B7Kompirine/muto-atlas/labels/good%20first%20issue)
are a good place to begin.

## License

MIT — see [LICENSE](LICENSE). Code only; [NOTICE.md](NOTICE.md) explains how game data is handled.

No GTA V data is distributed here. GTA V and its assets are property of Rockstar Games.
This project is not affiliated with Rockstar Games, Take-Two Interactive, or Cfx.re.

Built by **muto**.
