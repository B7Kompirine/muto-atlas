# AGENTS.md — working on muto-atlas

Instructions for coding agents (Codex, Cursor, GitHub Copilot, Gemini CLI, Claude Code, …)
working **inside this repository**. Human contributors: [CONTRIBUTING.md](CONTRIBUTING.md).

## What this repository is

A knowledge base and toolset that answers GTA V / FiveM questions from the game's own
data instead of guessing. It ships three ways: as a Claude Code plugin, as portable
[Agent Skills](https://agentskills.io/specification), and as an MCP server.

| path | what it is |
|---|---|
| `skills/fivem-assets/SKILL.md` + `trunk/` | the trunk: rules that hold in every branch |
| `skills/fivem-assets/branches/<branch>/_branch.md` | one branch: its rules and the table of its leaves |
| `skills/fivem-assets/branches/<branch>/<leaf>.md` | one task |
| `skills/fivem-assets/sources/` | notes on outside tools — sources, not rules |
| `skills/fivem-natives/` | the native database skill |
| `commands/*.md` | Claude Code slash commands |
| `scripts/` | Python and PowerShell tools: `assetdb.py`, `nativedb.py`, `lint_lua.py`, `setup.py`, … |
| `scripts/install_skills.py` | installs the skills into other agents' skill folders |
| `scripts/mcp_server.py` | the same queries as MCP tools |
| `scripts/build_atlas_db.py` | builds `data/atlas.db`: snippets per project (folder name), Claude tags, FTS5 search |
| `data/` | generated locally and gitignored, except three hand-written tables |

## Rules that are not negotiable

1. **Measure, don't assume.** Every number written into the docs says what produced it,
   on how many samples, and when.
2. **Exit codes are a contract:** `0` found · `1` not in the authority · `2` data layer not
   installed, so nothing can be claimed · `3` internal error. Never collapse `2` into `1`.
3. **Read every write back.** A command that raised no error has not proven anything.
4. **Never commit game data, generated layers or personal paths.** Tool locations come from
   the path registry (`assetdb.py path`), never from a hard-coded path.
5. **A finding is written once, in the widest place where it holds:** trunk, branch
   `_branch.md`, or leaf. A new leaf must be listed in its branch's leaf table.
6. **User-facing script messages** go through `scripts/i18n.py` with `en` and `tr` entries.
7. **PowerShell scripts run on Windows PowerShell 5.1:** save them as UTF-8 with BOM when
   they contain non-ASCII characters.
8. **Language:** the knowledge tree is written in Turkish; the `description:` front matter of
   commands is English.

## Keeping the skills portable

`SKILL.md` files follow the Agent Skills specification: `name` equals the folder name
(lowercase letters, digits, single hyphens, at most 64 characters), `description` is at most
1024 characters, `compatibility` at most 500.

Inside a skill, refer to scripts as `${CLAUDE_PLUGIN_ROOT}/scripts/…`. Claude Code fills the
variable in; `install_skills.py` rewrites it to an absolute path for every other tool. Do not
add other tool-specific syntax to skill bodies.

## Before you finish

```bash
python scripts/audit_plugin.py        # must exit 0
python scripts/check_repo.py          # must exit 0 (the pull-request checks)
python scripts/install_skills.py --check
python scripts/mcp_server.py --list-tools
python scripts/build_atlas_db.py --tagger rules   # if you touched the knowledge tree
```
