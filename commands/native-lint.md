---
description: Lint Lua files for native mistakes (invented natives, wrong side, wrong arity)
argument-hint: [file or folder path — current directory if empty]
allowed-tools: Bash(python:*), Read, Edit, Grep, Glob
---

Target: `$ARGUMENTS` (the current working directory if empty)

1. Run the linter:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/lint_lua.py" <target>
   ```

2. Handle the findings:

   - **E001** (native does not exist) — find the right name with `nativedb.py check`. If the suggested
     name is right, fix it. If there is no suggestion, consider that it may be a framework
     function; if it is not a native, tell the user — do not replace it with an invented name.
   - **E002** (wrong side) — a client-only native in a server file. Either move the logic
     to the client and trigger it with an event, or look for an equivalent native with `--apiset server`.
     Do not delete it silently; explain which fix you chose.
   - **E003** (too many arguments) — get the signature with `show` and make the call match it.
   - **W101/W102/W103** — per-frame cost. Apply the patterns in `references/performance.md`
     (dynamic `sleep`, moving work out of the loop, caching).
   - **W104** (missing argument) — usually a harmless idiom. Fix it only if it
     affects behaviour; do not "fix" these in bulk.

3. After applying the fixes, **run the linter again** and show that no E00x
   remain.

4. Summarise: how many files were scanned, how many errors were fixed, which warnings were deliberately
   left and why.

Do not just skip a finding you believe is a false positive — first verify the cause
(is the definition outside the lint scope, is it a method call), then write down the reasoning.
