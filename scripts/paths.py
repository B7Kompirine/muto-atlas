#!/usr/bin/env python3
"""paths.py — the single source of external tool and folder paths.

WHY
===
Paths used to be scattered across scripts: **29** separate hard-coded guesses
for `CodeWalker.Core.dll` and **23** for the GTA folder. The results:

* When a user installed CodeWalker somewhere else, 20+ files had to be fixed by hand.
* `data/config.json` already existed but the scripts **did not read it**; ytd_find.ps1
  tried to and wrote `gta` instead of `gtaFolder` -> PowerShell returns `$null` for a
  missing property without an error, so the configuration was **silently** ignored
  and the hard-coded guesses won.
* Personal paths kept leaking into the repository (cleaned once, came back).

There is one registry: `data/config.json`. `data/` is in .gitignore, so a personal
path **never enters the repository**.

THE KNOWN NAMES ARE **NOT A CLOSED LIST**
========================================
`REGISTERED` defines the common ones (search order + validation rule), but any
name can be stored:

    assetdb.py path gizmo "C:\\Tools\\Gizmo.exe"
    assetdb.py path gizmo            -> tells you where it is

so a new tool needs no code change.

USAGE
=====
    assetdb.py path                       # show all (found / missing)
    assetdb.py path codewalker            # show one
    assetdb.py path codewalker "C:\\...\\CodeWalker.Core.dll"   # set
    assetdb.py path codewalker --remove   # drop the entry

    import paths
    paths.resolve("codewalker")   # -> (path, source) or (None, reason)
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
CONFIG = os.path.join(DATA, "config.json")


def _home(*parts):
    return os.path.join(os.path.expanduser("~"), *parts)


# name -> (config key, description, kind, candidate paths)
# kind: "file" | "folder". Candidates are tried IN ORDER; the first that exists wins.
REGISTERED = {
    "codewalker": (
        "codeWalker", "CodeWalker.Core.dll - decodes .ydr/.yft/.ycd", "file",
        [_home("Desktop", "CodeWalker", "CodeWalker.Core.dll")],
    ),
    "gta": (
        "gtaFolder", "GTA V install folder - source of every data layer", "folder",
        [r"C:\Program Files\Rockstar Games\Grand Theft Auto V",
         r"C:\Program Files\Epic Games\GTAV",
         r"C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V",
         r"C:\SteamLibrary\steamapps\common\Grand Theft Auto V",
         r"D:\SteamLibrary\steamapps\common\Grand Theft Auto V",
         r"E:\Grand Theft Auto V"],
    ),
    "server": (
        "resources", "your FiveM server resources folder - framework index",
        "folder", [],
    ),
    "blender": (
        "blender", "blender.exe - to run scripts headless", "file",
        [r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
         r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"],
    ),
}

# Names that are not registered are stored too, under this prefix so they cannot collide.
FREE_PREFIX = "path_"
# Older versions stored them under this prefix; it is still read and cleaned up on write.
LEGACY_PREFIX = "yol_"

# Old Turkish names stay as aliases so older command lines keep working.
ALIASES = {"sunucu": "server", "yol": "path"}


def read_config():
    if os.path.exists(CONFIG):
        try:
            with open(CONFIG, encoding="utf-8-sig") as fh:
                return json.load(fh)
        except (ValueError, OSError):
            return {}
    return {}


def write_config(data):
    os.makedirs(DATA, exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def _canonical(name):
    return ALIASES.get(name.lower(), name.lower())


def _config_keys(name):
    """Config keys for a name: the current key first, then the legacy one for free names."""
    name = _canonical(name)
    entry = REGISTERED.get(name)
    if entry:
        return [entry[0]]
    return [FREE_PREFIX + name, LEGACY_PREFIX + name]


def _exists(path, kind):
    if not path:
        return False
    return os.path.isdir(path) if kind == "folder" else os.path.isfile(path)


def resolve(name):
    """Return (path, source), or (None, reason) when it cannot be found.

    Order: config.json -> known candidates. A path that is SET in config.json but
    MISSING on disk is reported as such -- "I set it but it doesn't work" is the
    most common case.
    """
    name = _canonical(name)
    entry = REGISTERED.get(name)
    kind = entry[2] if entry else "file"
    cfg = read_config()
    stored = next((cfg[k] for k in _config_keys(name) if cfg.get(k)), None)
    if stored:
        if _exists(stored, kind):
            return stored, "config.json"
        return None, "set in config.json but MISSING on disk: %s" % stored
    for candidate in (entry[3] if entry else []):
        if _exists(candidate, kind):
            return candidate, "found automatically"
    return None, "not set, and not found automatically"


def set_path(name, value):
    """REFUSES a path that does not exist: better to say so now than to leave a
    silently broken entry behind."""
    name = _canonical(name)
    entry = REGISTERED.get(name)
    kind = entry[2] if entry else None
    value = os.path.abspath(os.path.expanduser(value))
    if kind is None:
        kind = "folder" if os.path.isdir(value) else "file"
    if not _exists(value, kind):
        raise ValueError("no such %s: %s" % (kind, value))
    cfg = read_config()
    keys = _config_keys(name)
    for legacy in keys[1:]:
        cfg.pop(legacy, None)
    cfg[keys[0]] = value
    write_config(cfg)
    return value


def remove(name):
    cfg = read_config()
    found = [k for k in _config_keys(name) if k in cfg]
    if not found:
        return False
    for key in found:
        del cfg[key]
    write_config(cfg)
    return True


def all_paths():
    """[(name, path, source, description)] — the registered names plus user-defined ones."""
    out = []
    for name, entry in REGISTERED.items():
        path, source = resolve(name)
        out.append((name, path, source, entry[1]))
    cfg = read_config()
    seen = set()
    for key in sorted(cfg):
        for prefix in (FREE_PREFIX, LEGACY_PREFIX):
            if key.startswith(prefix) and key[len(prefix):] not in seen:
                name = key[len(prefix):]
                seen.add(name)
                path, source = resolve(name)
                out.append((name, path, source, "(user-defined)"))
    return out


# --------------------------------------------------------------------- CLI

def run(args):
    name = getattr(args, "name", None)
    value = getattr(args, "value", None)

    if name and getattr(args, "remove", False):
        print("removed: %s" % name if remove(name) else "not stored anyway: %s" % name)
        return 0

    if name and value:
        try:
            path = set_path(name, value)
        except ValueError as e:
            print("ERROR: %s" % e, file=sys.stderr)
            return 2
        print("%-12s -> %s" % (name, path))
        print("  saved to: %s" % CONFIG)
        return 0

    if name:
        path, source = resolve(name)
        if path:
            print("%s\n  %s  (%s)" % (name, path, source))
            return 0
        print("%s\n  MISSING - %s" % (name, source), file=sys.stderr)
        entry = REGISTERED.get(_canonical(name))
        if entry and entry[3]:
            print("  looked in:", file=sys.stderr)
            for candidate in entry[3]:
                print("    %s" % candidate, file=sys.stderr)
        print('\n  set it with: assetdb.py path %s "<path>"' % name, file=sys.stderr)
        return 1

    missing = 0
    print("registry: %s\n" % CONFIG)
    for name, path, source, description in all_paths():
        if path:
            print("  [+] %-11s %s" % (name, path))
            print("      %-11s %s | %s" % ("", source, description))
        else:
            missing += 1
            print("  [!] %-11s MISSING - %s" % (name, source))
            print("      %-11s %s" % ("", description))
    print('\n  set:  assetdb.py path <name> "<path>"   |   drop: --remove')
    print("  any name works too: assetdb.py path gizmo \"C:\\...\\Gizmo.exe\"")
    return 1 if missing else 0


if __name__ == "__main__":
    class Args:
        name = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None
        value = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
        remove = "--remove" in sys.argv or "--sil" in sys.argv
    sys.exit(run(Args))
