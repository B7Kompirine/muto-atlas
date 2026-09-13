#!/usr/bin/env python3
"""build_shaders.py — indexes the GTA V shader table.

WHY: "which shader for this surface?" cannot be answered by guessing. Decal, glass,
emissive, terrain, cloth, vehicle -- each has its own shader and its own REQUIRED
parameter set. Picking the wrong shader is a silent failure: the model loads but
draws wrong (the decal comes out opaque, the glass is not transparent, the emissive does not glow).

SOURCE: Shaders.xml in Sollumz's szio package (249 shaders). The file is derived
from CodeWalker's shader definitions; the parameter names and defaults are the
values the game expects.

Usage:
  python build_shaders.py [--src <path to Shaders.xml>]

If Sollumz is not installed, pass the path by hand with --src. Output: data/shaders.tsv
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")

# Sollumz versions install into different Blender versions; find the newest.
PATTERNS = [
    os.path.expandvars(
        r"%APPDATA%\Blender Foundation\Blender\*\extensions\.user\*\sollumz"
        r"\lib\python*\site-packages\szio\gta5\Shaders.xml"),
    os.path.expandvars(
        r"%APPDATA%\Blender Foundation\Blender\*\extensions\*\sollumz"
        r"\lib\python*\site-packages\szio\gta5\Shaders.xml"),
]


def find_source() -> str | None:
    candidates: list[str] = []
    for d in PATTERNS:
        candidates.extend(glob.glob(d))
    if not candidates:
        return None
    # newest Blender version = highest version number in the path; mtime is good enough
    return max(candidates, key=os.path.getmtime)


def main() -> int:
    ap = argparse.ArgumentParser(description="index the GTA V shader table")
    ap.add_argument("--src", help="path to Shaders.xml (when it is not found automatically)")
    ap.add_argument("--out", default=os.path.join(DATA, "shaders.tsv"))
    args = ap.parse_args()

    src = args.src or find_source()
    if not src or not os.path.exists(src):
        sys.exit(
            "Shaders.xml not found. If Sollumz is not installed, pass it with --src.\n"
            "  Typical path: %APPDATA%\\Blender Foundation\\Blender\\<version>\\"
            "extensions\\.user\\user_default\\sollumz\\lib\\python*\\"
            "site-packages\\szio\\gta5\\Shaders.xml")

    print(f"source: {src}")
    root = ET.parse(src).getroot()

    os.makedirs(DATA, exist_ok=True)
    n = 0
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["name", "flags", "texCount", "valCount",
                    "textures", "params"])
        for it in root:
            name = (it.findtext("Name") or "").strip()
            if not name:
                continue
            flags = (it.findtext("Flags") or "").strip()

            textures, values = [], []
            ps = it.find("Parameters")
            if ps is not None:
                for p in ps:
                    pname = p.get("name", "")
                    ptype = (p.get("type") or "").lower()
                    if ptype == "texture":
                        uv = p.get("uv")
                        textures.append(f"{pname}(uv{uv})" if uv is not None else pname)
                    else:
                        # scalar/vector defaults: x,y,z,w
                        components = [p.get(k) for k in ("x", "y", "z", "w")]
                        components = [b for b in components if b is not None]
                        subtype = p.get("subtype")
                        label = f"{pname}={','.join(components)}" if components else pname
                        if subtype:
                            label += f"[{subtype}]"
                        values.append(label)

            w.writerow([name, flags, len(textures), len(values),
                        ";".join(textures), ";".join(values)])
            n += 1

    print(f"[+] {args.out}  ({n} shaders)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
