#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lua_syntax.py — finds UNCLOSED strings/comments in a Lua file.

⛔ WHY IT EXISTS: `lua_check` (lua-language-server) MISSED a real syntax
   error and said "No diagnostics". The error:

       print('... /ptfxkat <n> (8'er)  ...')
                                    ^ the Turkish suffix apostrophe CLOSES the string

   FiveM reported `')' expected near 'er'` and **the whole resource failed to load**:
   no command was registered, in game only another resource's command showed up.
   The symptom is "the command is missing" -- it does not even look like a Lua error.

This script actually follows Lua's string/comment rules:
  · 'single' and "double" quoted strings, `\\` escape
  · `--` line comment (when NOT inside a string)
  · `[[ ]]` and `[==[ ]==]` long string/comment
If a string/comment is still open at the end it reports an error; it also
reports a line that ends with an unclosed short string.

Usage:
  python lua_syntax.py <file.lua> [...]
"""
from __future__ import annotations

import io
import sys


def check(path):
    """Returns (list of errors)."""
    s = io.open(path, encoding="utf-8", errors="replace").read()
    errors = []
    i, n = 0, len(s)
    line = 1
    while i < n:
        c = s[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        # long string / long comment: [[ ... ]] or [==[ ... ]==]
        if c == "[" or (c == "-" and s.startswith("--[", i)):
            j = i + 2 if s.startswith("--", i) else i
            if j < n and s[j] == "[":
                k = j + 1
                equals = 0
                while k < n and s[k] == "=":
                    equals += 1
                    k += 1
                if k < n and s[k] == "[":
                    closer = "]" + "=" * equals + "]"
                    end = s.find(closer, k + 1)
                    if end < 0:
                        errors.append((line, "unclosed long string/comment"))
                        return errors
                    line += s.count("\n", i, end)
                    i = end + len(closer)
                    continue
        # line comment
        if s.startswith("--", i):
            end = s.find("\n", i)
            i = n if end < 0 else end
            continue
        # short string
        if c in "'\"":
            quote = c
            j = i + 1
            while j < n:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == "\n":
                    errors.append((line,
                                   "UNCLOSED %s string at end of line" % quote))
                    break
                if s[j] == quote:
                    break
                j += 1
            else:
                errors.append((line, "unclosed string at end of file"))
                return errors
            i = j + 1
            continue
        i += 1
    return errors


def main():
    # The docstring and messages carry non-ASCII marks; a console with a legacy code page cannot
    # encode them. Replace what the console cannot show.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__ or "usage: python lua_syntax.py <file.lua> [...]")
        return 0
    if len(sys.argv) < 2:
        print("usage: lua_syntax.py <file.lua> [...]")
        return 2
    bad = 0
    for path in sys.argv[1:]:
        found = check(path)
        if found:
            bad += 1
            print("⛔ %s" % path)
            for line, msg in found[:10]:
                print("   line %d: %s" % (line, msg))
        else:
            print("clean: %s" % path)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
