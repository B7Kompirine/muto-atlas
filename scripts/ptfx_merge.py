#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_merge.py — merges many `.ypt` files into ONE `.ypt`.

⛔ WHY IT IS NEEDED: `PtFxAssetStore Pool Full, Size == 400`.

The pool counts FILES, not EFFECT RULES. The evidence is conclusive: `core.ypt`
carries **964 effect rules** in one file while the pool is 400 -- if rules were
counted, vanilla would overflow the pool on its own. `RequestNamedPtfxAsset` also
takes a file name. So "one file per effect" is wasteful: 35 families can use
**1** slot instead of 35.

Merging = merging the `<Item>`s of four dictionaries:
  EffectRuleDictionary · EmitterRuleDictionary · ParticleRuleDictionary
  · TextureDictionary

⛔ `TextureDictionary` MUST BE SORTED BY HASH (RAGE does a binary search).
   Measured: the 107 textures of vanilla `core.ypt` are sorted by Jenkins hash;
   the three rule dictionaries, on the other hand, are NOT sorted (neither
   alphabetically nor by hash). So sort only the textures, leave the others alone.

⛔ Textures are NOT EMBEDDED in the XML: they are read from outside through
   `<FileName>x.dds</FileName>`. Every `.dds` file must sit next to the merged XML.

Usage:
  python ptfx_merge.py --name my_effects --folder <dir>
  python ptfx_merge.py --name my_effects --folder <dir> --exclude my_x
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DICTIONARIES = ("EffectRuleDictionary", "EmitterRuleDictionary",
                "ParticleRuleDictionary", "TextureDictionary")


def jenkins(s):
    """RAGE's name hash. Verified against the vanilla texture order."""
    h = 0
    for c in s.lower().encode("utf-8"):
        h = (h + c) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    h = (h + (h << 15)) & 0xFFFFFFFF
    return h


def dictionary_items(xml, dictionary):
    """Returns the top-level <Item> bodies of a dictionary as (name, text)."""
    i = xml.find("<%s>" % dictionary)
    if i < 0:
        return []
    j = xml.find("</%s>" % dictionary)
    body = xml[i + len(dictionary) + 2:j]
    # ⛔ Splitting top-level <Item>s with a regex trips over nested <Item>s.
    #    Every rule starts with exactly `\n   <Name>`; split at those anchor points.
    anchors = [m.start() for m in re.finditer(r"\n   <Name>[^<]+</Name>", body)]
    if not anchors:
        return []
    result = []
    for n, s in enumerate(anchors):
        e = anchors[n + 1] if n + 1 < len(anchors) else len(body)
        chunk = body[s:e]
        name = re.search(r"<Name>([^<]+)</Name>", chunk).group(1)
        # put the opening <Item> back: the anchor point starts at <Name>
        result.append((name, "  <Item>" + chunk.rstrip().rsplit("</Item>", 1)[0]
                       + "</Item>\n"))
    return result


def main():
    # Help and messages carry non-ASCII marks; a console with a legacy code page cannot encode
    # them and argparse would crash. Replace what the console cannot show.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", "--ad", dest="name", required=True,
                    help="name of the merged asset")
    ap.add_argument("--folder", "--klasor", dest="folder", required=True)
    ap.add_argument("--exclude", "--disla", dest="exclude", action="append", default=[],
                    help="skip files that start with this prefix")
    ap.add_argument("--xml-only", "--derleme", dest="xml_only", action="store_true",
                    help="write the XML only")
    ap.add_argument("--allow-duplicates", "--tekille", dest="allow_duplicates",
                    action="store_true",
                    help="do NOT fail when the same name comes from more than one file, "
                         "keep one copy. ⚠ Use ONLY for DELIBERATE sharing: "
                         "a composed effect and its source layers "
                         "SHARE the same emitter/particle rules. The default is an "
                         "ERROR so that a stale-file accident is not hidden.")
    args = ap.parse_args()

    sources = sorted(f for f in os.listdir(args.folder)
                     if f.endswith(".ypt.xml")
                     and not f.startswith(args.name + ".")
                     and not any(f.startswith(d) for d in args.exclude))
    if not sources:
        raise SystemExit("no .ypt.xml to merge: %s" % args.folder)

    collected = {d: [] for d in DICTIONARIES}
    seen = {d: set() for d in DICTIONARIES}
    clashes, origin = {}, {}
    for f in sources:
        s = io.open(os.path.join(args.folder, f), encoding="utf-8",
                    errors="replace").read()
        for d in DICTIONARIES:
            for name, text in dictionary_items(s, d):
                # ⛔ NEVER WRITE THE SAME NAME TWICE. If two families were made
                #    from the same donor their textures differ but the rule names
                #    are unique; still, keep one entry per name for safety -- a
                #    duplicate entry breaks the dictionary and raises no error.
                if name in seen[d]:
                    # ⛔ DO NOT DROP SILENTLY. The previous version kept the first
                    #    entry it saw and threw the other away; an OLD merged file
                    #    left in the input folder (`my_catalog.ypt.xml`)
                    #    got mixed in that way, and whether the right version won
                    #    was left to ALPHABETICAL ORDER alone. It must be an error, not luck.
                    clashes.setdefault((d, name), []).append(f)
                    continue
                seen[d].add(name)
                origin[(d, name)] = f
                collected[d].append((name, text))

    if clashes and args.allow_duplicates:
        print("ⓘ %d names in more than one file -- one copy kept (--allow-duplicates)"
              % len(clashes))
        clashes = {}
    if clashes:
        print("⛔ THE SAME NAME CAME FROM MORE THAN ONE FILE -- merge stopped.")
        for (d, name), fs in sorted(clashes.items())[:12]:
            print("   %-24s %-28s first: %s | also: %s"
                  % (d, name, origin.get((d, name), "?"), ", ".join(fs)))
        print("   An old merged file may have been left in the input folder.")
        return 1

    # ⛔ Only the textures are sorted by hash. The rule dictionaries are not
    #    sorted in vanilla either; sorting them is unnecessary and makes verification harder.
    collected["TextureDictionary"].sort(key=lambda t: jenkins(t[0]))

    parts = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n",
             "<ParticleEffectsList>\n",
             " <Name>%s</Name>\n" % args.name]
    for d in ("EffectRuleDictionary", "EmitterRuleDictionary",
              "ParticleRuleDictionary"):
        parts.append(" <%s>\n" % d)
        parts += [m for _, m in collected[d]]
        parts.append(" </%s>\n" % d)
    parts.append(" <DrawableDictionary />\n")
    parts.append(" <TextureDictionary>\n")
    parts += [m for _, m in collected["TextureDictionary"]]
    parts.append(" </TextureDictionary>\n")
    parts.append("</ParticleEffectsList>\n")
    text = "".join(parts)

    ET.fromstring(text)  # do not take broken XML to the compiler
    xml = os.path.join(args.folder, args.name + ".ypt.xml")
    io.open(xml, "w", encoding="utf-8").write(text)
    print("source files: %d" % len(sources))
    for d in DICTIONARIES:
        print("  %-24s %d items" % (d, len(collected[d])))

    # are the texture files next to it?
    missing = [name + ".dds" for name, _ in collected["TextureDictionary"]
               if not os.path.exists(os.path.join(args.folder, name + ".dds"))]
    if missing:
        print("⛔ MISSING .dds (%d): %s" % (len(missing), ", ".join(missing[:6])))
        return 1

    if args.xml_only:
        return 0
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", os.path.join(SCRIPT_DIR, "ypt_xml_to_bin.ps1"),
                    "-Xml", xml], check=False)
    ypt = os.path.join(args.folder, args.name + ".ypt")
    if not os.path.exists(ypt):
        print("⛔ not compiled")
        return 1
    print("\n%s.ypt  %d bytes" % (args.name, os.path.getsize(ypt)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
