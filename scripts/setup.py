#!/usr/bin/env python3
"""setup.py — setup. Builds all 28 layers from the USER'S OWN data.

  python scripts/setup.py --save --gta "<GTA V>" --codewalker "<...\\CodeWalker.Core.dll>" \\
                          --resources "<server>/resources"
  python scripts/setup.py                # run again with the saved paths
  python scripts/setup.py --plan         # write nothing, only show the state

DESIGN PRINCIPLE
----------------
EVERYONE who uses this tool has GTA V and CodeWalker — it is a GTA modding
tool. So what is missing is not data but **path information.** Setup asks for
it once, writes it to `data/config.json` and never asks again.

That is why the heavy layers are NOT OPTIONAL, THEY ARE THE DEFAULT. If the
path is known they are built. Not using the real data the user already has
goes against the reason the tool exists: without data a query returns EXIT 2
and the model falls back to GUESSING.

WHAT IS DISTRIBUTED, WHAT IS NOT
--------------------------------
This public release does NOT DISTRIBUTE game data: every layer is built
locally from the user's own GTA V install and their own server. The repository
only holds three small hand-written tables (collision_materials,
collision_flag_presets, light_presets).

Three things that are never distributed:
  1. `entities.db` (214 MB) — DERIVED; built locally during setup.
  2. `framework_api.tsv.gz` — the USER'S OWN SERVER. Every net event and
     every export, with file path and line number. Publishing it is not a
     privacy problem but a SECURITY problem. Everyone builds it from their
     own server.
  3. `config.json` / `assets.meta.json` / `dumps.meta.json` — contain local
     paths and the user name.

⚠ VERSION: layers are tied to the game version they were built from (measured:
one install has 1271 `m26_*` archetypes, an old dump has 0). When the game
updates, run `/asset-build`.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n import add_lang_arg, get_lang, set_lang  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
PY = sys.executable or "python"

# The candidate list lives in ONE PLACE: paths.py. A second copy kept here gets
# updated while the other is forgotten -- there were 29 copies for CodeWalker
# and 23 for GTA.
from paths import REGISTERED as _REGISTERED_PATHS  # noqa: E402

GTA_CANDIDATES = _REGISTERED_PATHS["gta"][3]

# (file, tier, description, build command)
# tier: "light" = downloaded / small, "heavy" = built from the user's GTA V install.
# audit_plugin.py reads this list as LAYERS (it only counts it).
LAYERS = [
    ("natives.index.tsv", "light", "7191 natives + apiset + signature",
     "python scripts/build_index.py --fetch"),
    ("peds_meta.tsv.gz", "light", "1109 peds: clip dictionary, expression, clipset", "DUMP"),
    ("weapons.tsv.gz", "light", "184 weapons", "DUMP"),
    ("weapon_parts.tsv.gz", "light", "634 components + liveries", "DUMP"),
    ("vehicles.tsv.gz", "light", "921 vehicles: handlingId, modkit", "DUMP"),
    ("mlo_interiors.tsv.gz", "light", "853 MLO locations", "DUMP"),
    ("ipls.tsv.gz", "light", "895 IPLs + bounding box", "DUMP"),
    ("world_objects.tsv.gz", "light", "33912 world objects + rotation", "DUMP"),
    ("framework_api.tsv.gz", "light", "QBCore/ox export-event index", "FRAMEWORK"),
    ("archetypes.tsv.gz", "heavy", "316k archetypes (door, pivot, physics)",
     "powershell -File scripts/build_archetypes.ps1"),
    # entities.tsv.gz comes with the repository; the .db is built from it. If
    # the tsv is missing (or the user wants it from their own version) it is
    # first extracted with CodeWalker.
    ("entities.db", "heavy", "3M world placements (built from entities.tsv.gz)",
     "powershell -File scripts/build_entities.ps1 && python scripts/build_entities_db.py"),
    ("ymap_lod.tsv.gz", "heavy", "3.1M ymap LOD chain",
     "powershell -File scripts/build_ymap_lod.ps1"),
    ("clips.tsv.gz", "heavy", "316k clips: duration + bones",
     "powershell -File scripts/build_clips.ps1"),
    ("skeletons.tsv.gz", "heavy", "478k bone records",
     "powershell -File scripts/build_rigs.ps1"),
    ("expressions.tsv.gz", "heavy", "2338 expressions (.yed)",
     "powershell -File scripts/build_rigs.ps1"),
    ("ytyp_extensions.tsv.gz", "heavy", "64k ytyp extensions",
     "powershell -File scripts/build_extensions.ps1"),
    ("ptfx_effects.tsv.gz", "heavy", "2549 particle effects",
     "powershell -File scripts/build_ptfx.ps1"),
    ("shaders.tsv", "heavy", "249 shaders", "python scripts/build_shaders.py"),
    ("collision_materials.tsv", "heavy", "185 collision materials", "(manual)"),
    ("decal_types.tsv", "heavy", "194 decal types", "python scripts/build_decals.py"),
    ("procedural.tsv", "heavy", "255 procedural records",
     "powershell -File scripts/build_procedural.ps1"),
    ("anims.tsv.gz", "light", "269k animation names", "DUMP"),
    ("props.tsv.gz", "light", "21631 spawnable props", "DUMP"),
    ("scenarios.tsv.gz", "light", "247 scenarios", "DUMP"),
]


def have(f):
    return os.path.exists(os.path.join(DATA, f))


def run_step(title, cmd, plan):
    print(f"\n>>> {title}")
    print(f"    {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if plan:
        print("    (--plan: not run)")
        return None
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1800)
        output = (r.stdout or "").strip().split("\n")
        for l in output[-6:]:
            if l.strip():
                print(f"    {l}")
        if r.returncode != 0:
            errors = (r.stderr or "").strip().split("\n")
            for l in errors[-4:]:
                if l.strip():
                    print(f"    ! {l}")
        return r.returncode
    except Exception as e:
        print(f"    ! COULD NOT RUN: {e}")
        return 1


CONFIG = os.path.join(DATA, "config.json")


def read_config():
    if os.path.exists(CONFIG):
        try:
            return json.load(open(CONFIG, encoding="utf-8-sig"))
        except Exception:
            return {}
    return {}


def write_config(gta, cw, resources, lang=None):
    """Saves the paths so they are not asked for again.

    data/ is in .gitignore, so this file never enters the repository - personal
    path information is not shared.
    """
    d = read_config()
    if gta:
        d["gtaFolder"] = gta
    if cw:
        d["codeWalker"] = cw
    if resources:
        d["resources"] = resources
    if lang:
        d["lang"] = lang
    os.makedirs(DATA, exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=2, ensure_ascii=False)
    print(f"\n  Paths saved -> {CONFIG}")
    print("  They will not be asked for on the next run.")


def find_gta(given):
    if given:
        return given if os.path.isdir(given) else None
    import paths
    c, _ = paths.resolve("gta")          # config.json + known candidates, single source
    if c:
        return c
    meta = os.path.join(DATA, "assets.meta.json")
    if os.path.exists(meta):
        try:
            g = json.load(open(meta, encoding="utf-8-sig")).get("gtaFolder")
            if g and os.path.isdir(g):
                return g
        except Exception:
            pass
    for p in GTA_CANDIDATES:
        if os.path.isdir(p):
            return p
    return None


def find_codewalker(given):
    if given:
        return given if os.path.exists(given) else None
    import paths
    c, _ = paths.resolve("codewalker")   # config.json + known candidates, single source
    if c:
        return c
    meta = os.path.join(DATA, "assets.meta.json")
    if os.path.exists(meta):
        try:
            c = json.load(open(meta, encoding="utf-8-sig")).get("codeWalker")
            if c and os.path.exists(c):
                return c
        except Exception:
            pass
    for base in (os.path.expanduser("~/Desktop"), os.path.expanduser("~")):
        if not os.path.isdir(base):
            continue
        for dirp, dirs, files in os.walk(base):
            if dirp.count(os.sep) - base.count(os.sep) > 3:
                dirs[:] = []
                continue
            if "CodeWalker.Core.dll" in files:
                return os.path.join(dirp, "CodeWalker.Core.dll")
    return None


def main():
    ap = argparse.ArgumentParser(description="fivem-natives tiered setup")
    ap.add_argument("--resources", help="the FiveM server's resources folder (for the framework index)")
    ap.add_argument("--dump", help="gta-v-data-dumps folder (downloaded if missing)")
    ap.add_argument("--gta", help="GTA V install folder")
    ap.add_argument("--codewalker", help="path to CodeWalker.Core.dll")
    ap.add_argument("--plan", action="store_true", help="write nothing, only report")
    ap.add_argument("--light-only", "--hafif-only", dest="light_only", action="store_true",
                    help="skip the heavy layers built from GTA V")
    add_lang_arg(ap)
    ap.add_argument("--save", action="store_true",
                    help="save the given paths to data/config.json (not asked again)")
    a = ap.parse_args()
    set_lang(getattr(a, "lang", None))

    os.makedirs(DATA, exist_ok=True)
    dump = a.dump or os.path.join(ROOT, "data", "_raw", "dumps")
    gta = find_gta(a.gta)
    cw = find_codewalker(a.codewalker)
    saved = read_config()
    resources = a.resources or saved.get("resources")
    if a.save and not a.plan:
        write_config(gta, cw, resources, getattr(a, "lang", None))

    print("=" * 68)
    print("fivem-natives — setup")
    print("=" * 68)
    print(f"  plugin      : {ROOT}")
    print(f"  GTA V       : {gta or 'NOT FOUND'}")
    print(f"  CodeWalker  : {cw or 'NOT FOUND'}")
    print(f"  server      : {resources or '(not given)'}")
    print(f"  dump        : {dump}")
    missing0 = [f for f, k, *_ in LAYERS if not have(f)]
    print(f"  state       : {len(LAYERS) - len(missing0)}/{len(LAYERS)} layers installed")

    # --- LIGHT TIER ---
    print("\n" + "-" * 68)
    print("1) LAYERS DOWNLOADED FROM THE INTERNET")
    print("-" * 68)

    if not have("natives.index.tsv"):
        run_step("Native database (internet)",
                 [PY, "scripts/build_index.py", "--fetch"], a.plan)
    else:
        print("\n>>> Native database  [already installed]")

    dump_missing = [f for f, k, _d, c in LAYERS if c == "DUMP" and not have(f)]
    if dump_missing:
        # --fetch is ALWAYS passed: it skips files that exist and downloads the
        # MISSING ones. An "if the folder is full, do not download" rule silently
        # left files missing whenever a file was added to the source list.
        cmd = [PY, "scripts/build_dumps.py", "--dump", dump, "--fetch"]
        run_step(f"Dump layers ({len(dump_missing)} missing)", cmd, a.plan)
    else:
        print("\n>>> Dump layers  [already installed]")

    if resources:
        if os.path.isdir(resources):
            run_step("Framework index (your server)",
                     [PY, "scripts/build_framework.py", "--resources", resources], a.plan)
        else:
            print(f"\n>>> Framework index  SKIPPED: folder does not exist -> {resources}")
    else:
        print("\n>>> Framework index  SKIPPED")
        print("    Reason : --resources was not given")
        print("    Install: python scripts/setup.py --resources <server>/resources")
        print("    Gain   : export/event calls to a resource that is not installed are caught")

    # --- HEAVY TIER ---
    print("\n" + "-" * 68)
    # --- FAST PATH: build entities.db from the tsv that ships with the repository ---
    # This is the first gap a user who clones meets; CodeWalker is not needed at
    # all because the source tsv is already in the repository.
    if have("entities.tsv.gz") and not have("entities.db"):
        run_step("entities.db — building from entities.tsv.gz (no CodeWalker needed)",
                 "python scripts/build_entities_db.py", a.plan)

    print("2) LAYERS BUILT FROM YOUR OWN GAME  (default)")
    print("-" * 68)
    if not gta or not cw:
        missing = []
        if not gta:
            missing.append("GTA V install")
        if not cw:
            missing.append("CodeWalker.Core.dll")
        print(f"\n  ⛔ PATH NEEDED — not found: {', '.join(missing)}")
        print()
        print("  Most vanilla layers COME with the repository; the ones below are")
        print("  needed if you want them built from your game version or they are")
        print("  not in the repository. Everyone who uses this tool already has")
        print("  GTA V and CodeWalker; what is missing is not data but PATH information.")
        print()
        print("  Give the paths (once; --save stores them and they are not asked again):")
        print()
        print("    python scripts/setup.py --save \\")
        print('      --gta "C:\\Program Files\\Epic Games\\GTAV" \\')
        print('      --codewalker "C:\\...\\CodeWalker\\CodeWalker.Core.dll"')
        print()
        print("  CodeWalker.Core.dll: in the folder you downloaded CodeWalker to, next to the exe.")
    elif a.light_only:
        heavy_missing = [f for f, k, *_ in LAYERS if k == "heavy" and not have(f)]
        print(f"\n  --light-only given, {len(heavy_missing)} heavy layers skipped.")
    else:
        # THE HEAVY TIER IS NOW THE DEFAULT. If the path is known it is built;
        # making it "opt-in" wasted the real data the user already has.
        heavy_missing = [(f, d, c) for f, k, d, c in LAYERS
                         if k == "heavy" and not have(f) and c != "(manual)"]
        if not heavy_missing:
            print("\n  All heavy layers are installed.")
        else:
            print(f"\n  {len(heavy_missing)} heavy layers will be built (GTA V: {gta})")
            print("  This takes a few minutes (clips ~3 min, skeletons longer).")
            for f, d, c in heavy_missing:
                run_step(f"{f} — {d}", c, a.plan)

    # --- REPORT ---
    print("\n" + "=" * 68)
    print("STATE")
    print("=" * 68)
    installed = missing = 0
    for f, k, d, c in LAYERS:
        if have(f):
            installed += 1
            print(f"  [OK]  {f:<26} {d}")
        else:
            missing += 1
            print(f"  [--]  {f:<26} {d}")
            print(f"        -> {c}")
    print(f"\n  {installed}/{installed + missing} layers installed")
    if missing:
        print("\n  ⚠ A query that uses a missing layer returns EXIT 2 and claims NOTHING.")
        print("    Do not read that as 'asset not found' — 1 (no such name) and 2 (no layer) differ.")
    print("\n  Verify: python scripts/assetdb.py stats")
    return 0 if installed else 2


if __name__ == "__main__":
    sys.exit(main())
