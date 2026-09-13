# Contributing to muto-atlas

Thanks for helping. Contributions are welcome in **English or Turkish** —
issues, pull requests and findings alike. [Türkçe rehber →](docs/CONTRIBUTING.tr.md)

## The one rule: measure, don't assume

Everything in this repository is backed by a measurement, and a contribution
has to be too. A claim without a way to reproduce it cannot be merged, however
plausible it sounds.

For every claim, write down:

- **what produced it** — the command, the file, or the source you read
  (`assetdb.py door v_ilev_gb_teldr`, `lighting_common.fxh`, a line of Sollumz source)
- **how many samples** — "118 vanilla MLOs / 18,799 entities", not "always"
- **when and with what** — date, game build (Legacy / Enhanced), tool versions

"It worked for me once" is a report, not a finding. Open an issue with it —
that is useful too.

## Ways to contribute

| You have | Do this |
|---|---|
| A wrong answer or a silent failure | Open a **Bug / silent failure** issue |
| A measured fact the docs lack, or one they get wrong | Open a **Finding** issue, or send a pull request |
| A fix for a script | Send a pull request |
| A question | Open a blank issue |

Not sure where to start? Look for
[`good first issue`](https://github.com/B7Kompirine/muto-atlas/labels/good%20first%20issue)
and [`help wanted`](https://github.com/B7Kompirine/muto-atlas/labels/help%20wanted).
Many open questions only need someone with the game and one evening.

## Where things live

| Path | What goes there |
|---|---|
| `skills/fivem-assets/SKILL.md` + `trunk/` | The trunk: rules that hold in **every** branch — engine invariants, tool traps, the verification ladder, flags, bone tags |
| `skills/fivem-assets/branches/<branch>/_branch.md` | One branch: its category-wide rules and the table of its leaves |
| `skills/fivem-assets/branches/<branch>/<leaf>.md` | One task. A new leaf must be listed in its branch's `_branch.md` table, or nothing will ever read it |
| `skills/fivem-assets/sources/` | Notes on outside tools and community resources — sources, not rules |
| `skills/fivem-natives/` | Natives, framework API and Lua pitfalls |
| `commands/*.md` | Slash commands, one file each, with a `description:` front-matter line |
| `scripts/` | Python and PowerShell tools |
| `data/*.tsv` | Only the three hand-written tables are tracked. Everything else in `data/` is generated locally and gitignored |

A finding is written **once**, in the widest place where it holds: true in every
branch → trunk; true for one category → that `_branch.md`; true for one task → the leaf.

## Never commit

- **Game data.** No files extracted from RPFs, no generated layers
  (`*.tsv.gz`, `entities.db`), no XML dumps of Rockstar assets.
  See [NOTICE.md](NOTICE.md).
- **Third-party code or assets.** Link and cite; don't paste. The project is an
  independent implementation.
- **Personal paths.** Tool locations belong in `data/config.json` (gitignored),
  set through `assetdb.py path`.

## Working on scripts

- **Keep the exit-code contract.** `0` found · `1` not in the authority ·
  `2` layer not installed, so nothing can be claimed · `3` internal error.
  Reading `2` as `1` is the exact failure this plugin exists to prevent.
- **Read every write back.** A command that didn't error has not proven that
  anything was written.
- **Never swallow errors.** No bare `except:` or `catch {}`; print the first
  error. A silently failing `foreach` once lost 86,690 files, and the only
  symptom was a "0 scanned" line.
- **New user-facing messages go through `scripts/i18n.py`** with both `en` and
  `tr` entries. A missing key prints the key itself, so gaps stay visible.
- **PowerShell scripts must run on Windows PowerShell 5.1.** Keep them pure
  ASCII or save them as UTF-8 *with BOM*, or 5.1 misreads non-ASCII characters.

## Testing your change locally

1. Fork the repository and clone your fork.
2. Start Claude Code with your checkout loaded instead of the published plugin:

   ```bash
   claude --plugin-dir path/to/your/muto-atlas
   ```

3. Build the layers once (`/asset-setup`) and run the command you changed.
   Paste its output, including the exit code, into the pull request.
4. Run the plugin's own checks. Both must exit `0`:

   ```bash
   python -m pip install -r requirements-dev.txt
   python scripts/audit_plugin.py
   python scripts/check_repo.py
   ```

   `audit_plugin.py` catches what never raises an error in the knowledge tree:
   broken links, a leaf missing from its branch table, drifted counters, a `.ps1`
   without a BOM. `check_repo.py` checks the rest: every script compiles and
   answers `--help`, every `.ps1` parses, the tables in `data/` match their
   schemas, no personal path, e-mail address or secret sits in a file, and every
   relative link resolves.
5. If you changed the knowledge tree, rebuild the database offline and find your snippet:

   ```bash
   python scripts/build_atlas_db.py --tagger rules
   python scripts/build_atlas_db.py --search "a word from your change"
   ```

Every pull request runs the same checks in GitHub Actions
(`.github/workflows/checks.yml`); a failing check names the file and the line.
Beyond that there is no automated test suite. The measurement in your pull
request is the test.

## Pull requests

- One topic per pull request. A new finding and a script refactor are two.
- Say which issue it closes, if any (`Closes #12`).
- Commit messages are plain sentences that say what changes, in English or
  Turkish, like the existing history:
  *"Read lights from drawables that have no skeleton"*.
- By submitting a pull request you agree that your contribution is licensed
  under the [MIT license](LICENSE).

## Conduct

Be kind and be specific. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
