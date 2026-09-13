<!-- English or Turkish is fine. -->

## What changes

<!-- One topic per pull request. Closes #… -->

## Evidence

<!-- What you ran and what it printed, including the exit code. -->

```text

```

## Checklist

<!-- Tick what applies. -->

- [ ] Every new claim says what produced it and how many samples
- [ ] No game data, generated layers or third-party code
- [ ] No personal paths; tool locations stay in `data/config.json`
- [ ] A new leaf is listed in its branch's `_branch.md` table
- [ ] `python scripts/audit_plugin.py` exits 0
- [ ] `python scripts/check_repo.py` exits 0 (the same checks run on every pull request)
- [ ] New messages have `en` and `tr` entries in `scripts/i18n.py`
- [ ] PowerShell scripts are pure ASCII or saved as UTF-8 with BOM
- [ ] I agree to license this contribution under MIT
