#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_compose.py — composes a MULTI-EMITTER effect (layering).

⛔ WHY: measured, **74% of vanilla effects have several emitters**
   (713/964); `exp_grd_grenade` carries 6 layers, `exp_grd_molotov` 7.
   Our whole catalog was SINGLE-emitter -- the simplest 26% of the format.
   That is the reason for the "they are all variants of each other" look:
   professional VFX gets its depth from layers (white core + orange ball + rising
   smoke + debris + shock ring STACKED ON TOP OF EACH OTHER).

Layer fields read from vanilla:
   `<EmitterRule>` / `<ParticleRule>`  -> the layer's source
   `Unknown10`      -> the layer's DELAY (seconds). In exp_grd_grenade
                       0 / 0.034 / 0.068 -- frames 0, 1, 2 at 30 fps.
   `ParticleScale`  -> per-layer size multiplier (1.2 in molotov)
   `Unknown14`      -> layer lifetime/density multiplier (0.7 - 1.0)

Usage:
  python ptfx_compose.py --name my_explosion --folder <dir> \\
      --layer my_arc_impact:0:1.0 \\
      --layer my_fireball:0.034:1.2 \\
      --layer my_smoke:0.10:1.4
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
sys.path.insert(0, SCRIPT_DIR)
from ptfx_merge import jenkins, dictionary_items  # noqa: E402

DICTIONARIES = ("EmitterRuleDictionary", "ParticleRuleDictionary",
                "TextureDictionary")

# One EventEmitter item. The field order matches vanilla 1:1 -- the CodeWalker
# XML reader cares about the order.
EMITTER_ITEM = """  <Item>
     <EmitterRule>%(em)s</EmitterRule>
     <ParticleRule>%(pr)s</ParticleRule>
     <Unknown10 value="%(delay)g" />
     <Unknown14 value="%(lifetime)g" />
     <MoveSpeedScale value="1" />
     <MoveSpeedScaleModifier value="1" />
     <ParticleScale value="%(scale)g" />
     <ParticleScaleModifier value="1" />
     <Colour1 value="0xFFFFFFFF" />
     <Colour2 value="0xFFFFFFFF" />
     <UnknownData>
      <EventEmitterFlags>
       <Item>LOD</Item>
      </EventEmitterFlags>
      <Unknown10 />
     </UnknownData>
    </Item>
"""


def find_single(s, dictionary):
    """Returns the (name, body) pair of the SINGLE item in the dictionary."""
    o = dictionary_items(s, dictionary)
    return o[0] if o else (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", "--ad", dest="name", required=True)
    ap.add_argument("--folder", "--klasor", dest="folder", required=True,
                    help="folder that holds the layer sources")
    ap.add_argument("--layer", "--katman", dest="layer", action="append", required=True,
                    metavar="EFFECT[:delay[:scale[:lifetime]]]")
    ap.add_argument("--xml-only", "--derleme", dest="xml_only", action="store_true")
    args = ap.parse_args()

    items = []
    collected = {d: [] for d in DICTIONARIES}
    seen = {d: set() for d in DICTIONARIES}
    template = None

    for spec in args.layer:
        parts = spec.split(":")
        effect = parts[0]
        delay = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
        scale = float(parts[2]) if len(parts) > 2 and parts[2] else 1.0
        lifetime = float(parts[3]) if len(parts) > 3 and parts[3] else 1.0

        path = os.path.join(args.folder, effect + ".ypt.xml")
        if not os.path.exists(path):
            raise SystemExit("layer source missing: %s" % path)
        s = io.open(path, encoding="utf-8", errors="replace").read()
        if template is None:
            template = s

        em_name, _ = find_single(s, "EmitterRuleDictionary")
        pr_name, _ = find_single(s, "ParticleRuleDictionary")
        if not em_name or not pr_name:
            raise SystemExit("%s: emitter/particle not found" % effect)

        for d in DICTIONARIES:
            for name, text in dictionary_items(s, d):
                # ⛔ The same name is never written twice. If two layers use
                #    the same sprite, the texture goes in once.
                if name in seen[d]:
                    continue
                seen[d].add(name)
                collected[d].append((name, text))

        items.append(EMITTER_ITEM % {"em": em_name, "pr": pr_name, "delay": delay,
                                     "scale": scale, "lifetime": lifetime})

    # --- take the effect rule from the template, replace EventEmitters ---
    i = template.find("<EffectRuleDictionary>")
    j = template.find("</EffectRuleDictionary>")
    rule = template[i + len("<EffectRuleDictionary>"):j]
    rule = re.sub(r"(\n   <Name>)[^<]+(</Name>)", r"\g<1>%s\g<2>" % args.name,
                  rule, count=1)
    ei = rule.find("<EventEmitters>")
    ej = rule.find("</EventEmitters>")
    if ei < 0:
        raise SystemExit("no <EventEmitters> in the template")
    rule = (rule[:ei] + "<EventEmitters>\n" + "".join(items)
            + "   </EventEmitters>" + rule[ej + len("</EventEmitters>"):])

    collected["TextureDictionary"].sort(key=lambda t: jenkins(t[0]))

    p = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n",
         "<ParticleEffectsList>\n", " <Name>%s</Name>\n" % args.name,
         " <EffectRuleDictionary>", rule, "</EffectRuleDictionary>\n"]
    for d in ("EmitterRuleDictionary", "ParticleRuleDictionary"):
        p.append(" <%s>\n" % d)
        p += [m for _, m in collected[d]]
        p.append(" </%s>\n" % d)
    p.append(" <DrawableDictionary />\n")
    p.append(" <TextureDictionary>\n")
    p += [m for _, m in collected["TextureDictionary"]]
    p.append(" </TextureDictionary>\n")
    p.append("</ParticleEffectsList>\n")
    text = "".join(p)

    ET.fromstring(text)
    xml = os.path.join(args.folder, args.name + ".ypt.xml")
    io.open(xml, "w", encoding="utf-8").write(text)
    print("%s: %d layers | %d emitters, %d particles, %d textures"
          % (args.name, len(items), len(collected["EmitterRuleDictionary"]),
             len(collected["ParticleRuleDictionary"]),
             len(collected["TextureDictionary"])))

    missing = [name + ".dds" for name, _ in collected["TextureDictionary"]
               if not os.path.exists(os.path.join(args.folder, name + ".dds"))]
    if missing:
        print("⛔ MISSING .dds: %s" % ", ".join(missing[:6]))
        return 1
    if args.xml_only:
        return 0
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", os.path.join(SCRIPT_DIR, "ypt_xml_to_bin.ps1"),
                    "-Xml", xml], check=False)
    ypt = os.path.join(args.folder, args.name + ".ypt")
    print("  -> %s (%d bytes)" % (os.path.basename(ypt),
                                  os.path.getsize(ypt)) if os.path.exists(ypt)
          else "  ⛔ not compiled")
    return 0 if os.path.exists(ypt) else 1


if __name__ == "__main__":
    raise SystemExit(main())
