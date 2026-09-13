#!/usr/bin/env python3
"""list_commands.py -- lists ALL commands of the plugin with their descriptions.

WHY: a hand-written command list goes stale. This script READS the
`commands/*.md` frontmatter, so the list always shows the real state.
Nothing needs to change here when a new command is added.

Usage:
  python scripts/list_commands.py                 # full grouped list
  python scripts/list_commands.py --flat          # one line per command: name + description
  python scripts/list_commands.py <search>        # filter by name/description
"""
from __future__ import annotations

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMANDS_DIR = os.path.join(ROOT, "commands")

# Group the commands by kind of work. If a name is deleted here the command
# falls into the "Other" group -- the list still stays complete.
GROUPS = [
    ("Getting started", ["help", "asset-setup", "paths"]),
    ("Data queries", ["asset", "where", "anim", "native", "native-lint"]),
    ("Branches (rules + leaves)", ["map", "prop", "clothing", "particle", "look", "vehicle"]),
    ("Setup and tool paths", ["asset-build", "blender", "codewalker", "gta", "server"]),
]

# --flat is the English flag; --duz is the old Turkish spelling, still accepted.
FLAT_FLAGS = ("--flat", "--duz")


def frontmatter(path: str) -> dict:
    """Extracts simple key: value pairs from the --- ... --- block."""
    text = io.open(path, encoding="utf-8", errors="replace").read()
    if not text.startswith("---"):
        return {}
    try:
        block = text.split("---", 2)[1]
    except IndexError:
        return {}
    out = {}
    for line in block.splitlines():
        m = re.match(r"^([a-zA-Z-]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def read_commands() -> dict:
    if not os.path.isdir(COMMANDS_DIR):
        sys.exit(f"commands/ not found: {COMMANDS_DIR}")
    registry = {}
    for f in sorted(os.listdir(COMMANDS_DIR)):
        if not f.endswith(".md"):
            continue
        name = f[:-3]
        fm = frontmatter(os.path.join(COMMANDS_DIR, f))
        registry[name] = {
            "description": fm.get("description", "(no description)"),
            "hint": fm.get("argument-hint", ""),
        }
    return registry


def wrap(text: str, width: int, indent: str) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return ("\n" + indent).join(lines)


def main() -> int:
    args = [a for a in sys.argv[1:]]
    flat = any(f in args for f in FLAT_FLAGS)
    args = [a for a in args if not a.startswith("--")]
    search = args[0].lower() if args else None

    registry = read_commands()
    if search:
        registry = {k: v for k, v in registry.items()
                    if search in k.lower() or search in v["description"].lower()}
        if not registry:
            print(f"No command matches '{search}'.")
            return 1

    if flat:
        for name, v in sorted(registry.items()):
            print(f"/muto-atlas:{name}  --  {v['description']}")
        return 0

    print("=" * 74)
    print(f"  muto-atlas -- {len(registry)} commands")
    print("=" * 74)
    print("  Invoke:  /muto-atlas:<name>   or  /<name>  (when there is no clash)")
    print()

    placed = set()
    for title, names in GROUPS:
        # A command may appear in more than one group; it is shown in the FIRST one.
        members = [n for n in names if n in registry and n not in placed]
        if not members:
            continue
        print(f"-- {title} " + "-" * (70 - len(title)))
        for name in members:
            placed.add(name)
            v = registry[name]
            print(f"  /{name}")
            print(f"      {wrap(v['description'], 62, '      ')}")
            if v["hint"]:
                print(f"      argument: {v['hint']}")
        print()

    rest = sorted(set(registry) - placed)
    if rest:
        print("-- Other " + "-" * 64)
        for name in rest:
            print(f"  /{name}")
            print(f"      {wrap(registry[name]['description'], 62, '      ')}")
        print()

    print("-" * 74)
    print("  Data layer status   :  python scripts/setup.py --plan")
    print("  Plugin integrity    :  python scripts/audit_plugin.py")
    print("  One-line list       :  python scripts/list_commands.py --flat")
    print("  Search              :  python scripts/list_commands.py <word>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
