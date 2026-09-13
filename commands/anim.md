---
description: Search animations (duration + bones), prop skeletons, expressions and scenarios
argument-hint: <search term> | <dict> --dict | bones <model> | expr <term>
allowed-tools: Bash(python:*), Read
---

User query: `$ARGUMENTS`

Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if it cannot be found, the muto-atlas folder that contains `scripts/assetdb.py`).

312,748 clips were extracted from `.ycd` files — with **real duration and bone count**.
**An animation name is never invented**; if it is not here, it does not exist.

## How to use

```bash
# search in dict + clip names (with duration and bone count)
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" anim <term>

# dump a dictionary's contents GROUPED BY DURATION -> shows the ped+prop pair
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" anim <dict name> --dict

# search dictionary names only
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" anim <term> --dict-only

# prop/ped skeleton: bone name + tag
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" bones <model>

# expression (.yed): procedural / spring / collision response
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" expr <term>

# ped scenario (world animation)
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" scenario <term>
```

Search with English terms; translate a Turkish query first: `oturma` → `sit`, `sigara` →
`smoking`, `kaynak` → `weld`, `kelepçe` → `cuff`, `taşıma` → `carry`,
`çanta` → `bag`, `para` → `cash`.

## When presenting the result

- Give **both the dictionary and the clip** name; if one is missing, the animation does not play.
- **Take the duration from the output**; do not guess it. The `Wait()` / progress duration comes from there.
- Usage pattern: `RequestAnimDict` → wait for `HasAnimDictLoaded` → `TaskPlayAnim`.
- **If a scene with a prop is wanted**, look for the
  *"same duration, DIFFERENT skeleton: ped + prop pair"* marker in the `--dict` output; play the ped and prop
  clips together as a synchronised scene.
- If the prop has no skeleton, `PlayEntityAnim` does not work — verify with `bones` first.
- If nothing comes up, try 2-3 times with a different term; if there is still nothing,
  say "no animation with this name in the index" and **do not invent a similar one**.
