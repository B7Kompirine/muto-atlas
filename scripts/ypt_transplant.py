#!/usr/bin/env python3
"""ypt_transplant.py — takes a WORKING vanilla effect and swaps its TEXTURE.

WHY: when a rule written from scratch does not work, hunting "which field is
missing" field by field is expensive; vanilla has dozens of `Unknown*` fields
whose meaning is unresolved. Copying a working configuration 1:1 and changing ONE
variable (the texture) splits the fault in two in a single round:

  works         -> the fault is in the fields our generator writes
  does not work -> the fault is not in the rule, it is elsewhere in the pipeline

This is NOT a "use a vanilla effect" method -- it is a diagnostic tool. For
production, build_custom_ptfx.py is used.

Usage:
  python ypt_transplant.py core.ypt.xml --effect ent_amb_fbi_cinder \\
      --new-name my_butterfly2 --texture my_butterfly2 --folder <output>
"""
from __future__ import annotations

import argparse
import os
import re
import struct
import sys

TEXTURE_FLAGS = {
    (32, 32): "X16, UNK24",
    (64, 64): "X64, X128, UNK24",
    (128, 128): "X8, X32, X64, X128, UNK24",
    (256, 256): "X64, Y64, X256, UNK24",
    (512, 512): "X64, Y64, X256, Y512, UNK24",
    (1024, 1024): "X64, Y64, X256, Y512, Y1024, UNK24",
}


def block(s, tag):
    a = s.find(f"<{tag}>")
    b = s.find(f"</{tag}>")
    return s[a:b] if a >= 0 else ""


def find_item(dictionary, name):
    """Returns the top-level <Item> block in the dictionary that carries <Name>name</Name>."""
    m = re.search(r"\n  <Item>\n   <Name>" + re.escape(name) + r"</Name>(.*?)\n  </Item>",
                  dictionary, re.S)
    if not m:
        sys.exit(f"not found: {name}")
    return "  <Item>\n   <Name>" + name + "</Name>" + m.group(1) + "\n  </Item>\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source_xml", help="vanilla .ypt.xml (e.g. core.ypt.xml)")
    ap.add_argument("--effect", "--efekt", dest="effect", required=True,
                    help="name of the vanilla effect to copy")
    ap.add_argument("--new-name", "--yeni-ad", dest="new_name", required=True)
    ap.add_argument("--texture", "--doku", dest="texture",
                    help="new texture name (without extension)")
    # ⛔ DIAGNOSTIC MODE: do not change the texture, keep the donor's VANILLA texture.
    #    That splits the question "is it the rule or our texture" in two:
    #      correct drawing with the vanilla texture -> the fault is in our texture
    #      broken with the vanilla texture too      -> the fault is elsewhere in the pipeline
    #    The vanilla texture lives in core.ypt; NO embedded texture is written.
    ap.add_argument("--keep-texture", "--doku-koru", dest="keep_texture", action="store_true",
                    help="keep the donor's own texture (no embedded texture)")
    # ⛔ CONTROL: bind to ANOTHER VANILLA texture by name, do not embed.
    #    That way "does the vanilla texture really get sliced" can be tested with
    #    a vanilla sheet whose cells are CLEARLY DIFFERENT. Cells that look alike
    #    (such as ember grains) cannot answer this question --
    #    a single sliced cell and the unsliced whole sheet look the same.
    ap.add_argument("--vanilla-texture", "--vanilla-doku", dest="vanilla_texture", default=None,
                    help="bind to an existing vanilla texture name (no embedding)")
    ap.add_argument("--folder", "--klasor", dest="folder", required=True)
    # ⛔ Grow the size with `m_whd*KFP`, not with `m_sizeScalarKFP`.
    #    whd is in METRES and its meaning was measured for certain; the scale of
    #    sizeScalar is UNCLEAR (the distribution looks like a percentage -- median 57.6 --
    #    but in the donor a value of 0.44 gives visible particles). Using an unclear
    #    field as a multiplier muddies the diagnosis.
    ap.add_argument("--size-mult", "--boyut-carpan", dest="size_mult", type=float, default=1.0,
                    help="multiplies the whd keyframes of the Size behaviour (metres)")
    # `m_zoomScalarKFP` seems to scale with distance: in vanilla the value goes with
    # the size of the effect (tiny effect 0.75, huge gas column
    # 1200; median 51.8, 77.2% filled). At a high value the particle reads as if it
    # SHRINKS as you get closer. Emptying it is legitimate: 22.8% of vanilla is empty.
    ap.add_argument("--reset-zoom", "--zoom-sifirla", dest="reset_zoom", action="store_true",
                    help="empties the m_zoomScalarKFP keyframes")
    # The donor's color comes along as well (orange->dark red in the ember effect).
    # When the color is changed the ALPHA CURVE IS KEPT: only RGB is written, the alpha
    # keyframe is left as it is -- otherwise the effect's fade-out behaviour
    # breaks and the particles vanish abruptly.
    ap.add_argument("--color", "--renk", dest="color", nargs=3, type=float,
                    metavar=("R", "G", "B"),
                    help="RGB 0..1; changes the color of the Colour behaviour")
    # UsageFlags is NOT an independent field: in CodeWalker `UsageData` is a single
    # uint, packed with the low 5 bits as Usage and the rest as UsageFlags
    # (Usage = UsageData & 0x1F, UsageFlags = UsageData >> 5). So a wrong
    # flag changes the whole word. This is for passing the donor's value 1:1.
    ap.add_argument("--texture-flags", "--doku-bayrak", dest="texture_flags", default=None,
                    help="write UsageFlags by hand (e.g. 'X32, X64, X128, UNK24')")
    # `m_sizeScalarKFP` IS A PERCENTAGE, neutral value 100. (KFPs.md: "Size Scalar --
    # width/height/depth percentages, max 1000%".) Measured: the donors'
    # distribution runs from 34 to 694 -- `weap_veh_turb_dust` covers the sky
    # at 693.6%, `td_blood_nose` is almost invisible at 34.1%.
    # Taking the donor as it is scales the effect to the donor's scene;
    # for our own effect it has to be fitted into the band.
    ap.add_argument("--size-scale", "--boyut-olcek", dest="size_scale", type=float, default=None,
                    help="m_sizeScalarKFP (PERCENT, neutral=100)")
    ap.add_argument("--rate", "--oran", dest="rate", type=float, default=None,
                    help="m_spawnRateOverTimeKFP (per s)")
    ap.add_argument("--lifetime", "--omur", dest="lifetime", type=float, default=None,
                    help="m_particleLifeKFP (seconds)")
    args = ap.parse_args()

    s = open(args.source_xml, encoding="utf-8", errors="replace").read()
    er, em_d, pr_d = (block(s, "EffectRuleDictionary"),
                      block(s, "EmitterRuleDictionary"),
                      block(s, "ParticleRuleDictionary"))

    effect = find_item(er, args.effect)
    emitter_names = re.findall(r"<EmitterRule>([^<]*)</EmitterRule>", effect)
    particle_names = re.findall(r"<ParticleRule>([^<]*)</ParticleRule>", effect)
    if len(emitter_names) != 1 or len(particle_names) != 1:
        sys.exit(f"this effect has {len(emitter_names)} emitters -- pick a single-emitter one")
    emitter = find_item(em_d, emitter_names[0])
    particle = find_item(pr_d, particle_names[0])

    # --- renaming ---
    new, new_em, new_pr = args.new_name, f"{args.new_name}_em", f"{args.new_name}_pr"
    effect = effect.replace(f"<Name>{args.effect}</Name>", f"<Name>{new}</Name>", 1)
    effect = effect.replace(f"<EmitterRule>{emitter_names[0]}</EmitterRule>",
                            f"<EmitterRule>{new_em}</EmitterRule>")
    effect = effect.replace(f"<ParticleRule>{particle_names[0]}</ParticleRule>",
                            f"<ParticleRule>{new_pr}</ParticleRule>")
    emitter = emitter.replace(f"<Name>{emitter_names[0]}</Name>", f"<Name>{new_em}</Name>", 1)
    particle = particle.replace(f"<Name>{particle_names[0]}</Name>", f"<Name>{new_pr}</Name>", 1)

    # --- TEXTURE SWAP: THIS IS THE ONE VARIABLE ---
    old = re.findall(r"<TextureName>([^<]+)</TextureName>", particle)
    if not old:
        sys.exit("no <TextureName> in the particle rule")
    if args.vanilla_texture:
        for e in set(old):
            if e:
                particle = particle.replace(
                    f"<TextureName>{e}</TextureName>",
                    f"<TextureName>{args.vanilla_texture}</TextureName>")
        print(f"[i] bound to VANILLA texture: {old[0]} -> {args.vanilla_texture}")
    elif not args.keep_texture:
        if not args.texture:
            sys.exit("pass --texture or use --keep-texture")
        for e in set(old):
            if e:
                particle = particle.replace(f"<TextureName>{e}</TextureName>",
                                            f"<TextureName>{args.texture}</TextureName>")

    if args.reset_zoom:
        replaced, n = re.subn(
            r"(<Name>ptxEffectRule:m_zoomScalarKFP</Name>\s*<Unknown6C[^>]*>\s*)"
            r"<Keyframes>.*?</Keyframes>",
            r"\1<Keyframes />", effect, flags=re.S)
        if n:
            effect = replaced
            print("[i] m_zoomScalarKFP emptied")
        else:
            print("[!] WARNING: m_zoomScalarKFP already empty or not found")

    # --- size multiplier: whd keyframes only ---
    if args.size_mult != 1.0:
        def multiply(m):
            body = m.group(2)

            def channel(k):
                return f"<{k.group(1)} value=\"{float(k.group(2)) * args.size_mult:g}\" />"
            body = re.sub(r"<(RedChannelColour|GreenChannelColour|BlueChannelColour)"
                          r" value=\"([-\d.eE+]+)\" />", channel, body)
            return m.group(1) + body + m.group(3)

        before = particle
        particle = re.sub(
            r"(<Name>ptxu_Size:m_whd(?:Min|Max)KFP</Name>.*?<Keyframes>)(.*?)(</Keyframes>)",
            multiply, particle, flags=re.S)
        if particle == before:
            print("[!] WARNING: whd keyframe not found, size NOT CHANGED")

    if args.size_scale is not None:
        v = args.size_scale

        def scale(m):
            body = re.sub(r"<(RedChannelColour|GreenChannelColour) value=\"[-\d.eE+]+\" />",
                          lambda k: f"<{k.group(1)} value=\"{v:g}\" />", m.group(2))
            return m.group(1) + body + m.group(3)

        before = emitter
        emitter = re.sub(
            r"(<Name>ptxEmitterRule:m_sizeScalarKFP</Name>.*?<Keyframes>)(.*?)(</Keyframes>)",
            scale, emitter, flags=re.S)
        print(f"[i] m_sizeScalarKFP = {v:g}" if emitter != before
              else "[!] WARNING: m_sizeScalarKFP not found")

    def write_emitter_kfp(kfp_name, value, label):
        """Scales a KFP in the emitter rule to an AVERAGE of `value`.

        R is the min slot, G the max slot.

        ⛔ DO NOT WRITE BOTH THE SAME -- if the range collapses the randomness goes
           and all particles happen at once; the eye reads that as "mechanical".
           Measured (n=1989): **90.3%** of vanilla emitters give the particle
           lifetime a min-max range, median max/min **1.45**. For the spawn
           rate it is 56.7%. So writing a flat number DEVIATES from vanilla
           in most cases.

        The right way: keep the donor's own spread ratio, move the range to the
        requested average. If the donor has no range (min==max) it stays flat --
        that is the donor's own choice too.
        """
        def rewrite(m):
            body = m.group(2)
            k = re.findall(r"<(?:Red|Green)ChannelColour value=\"([-\d.eE+]+)\" />",
                           body)
            if len(k) >= 2:
                mn, mx = float(k[0]), float(k[1])
                mean = (mn + mx) / 2.0
                if mean > 1e-9:
                    new_range = (mn * value / mean, mx * value / mean)
                else:
                    new_range = (value, value)
            else:
                new_range = (value, value)
            it = iter(new_range)
            body = re.sub(
                r"<(RedChannelColour|GreenChannelColour) value=\"[-\d.eE+]+\" />",
                lambda q: f"<{q.group(1)} value=\"{next(it, value):g}\" />",
                body, count=2)
            return m.group(1) + body + m.group(3)
        return re.sub(r"(<Name>ptxEmitterRule:" + kfp_name + r"</Name>.*?<Keyframes>)"
                      r"(.*?)(</Keyframes>)", rewrite, emitter, flags=re.S), label

    if args.rate is not None:
        before = emitter
        emitter, _ = write_emitter_kfp("m_spawnRateOverTimeKFP", args.rate, "rate")
        print(f"[i] spawn rate = {args.rate:g}/s" if emitter != before
              else "[!] WARNING: m_spawnRateOverTimeKFP not found")
    if args.lifetime is not None:
        before = emitter
        emitter, _ = write_emitter_kfp("m_particleLifeKFP", args.lifetime, "lifetime")
        print(f"[i] particle lifetime = {args.lifetime:g} s" if emitter != before
              else "[!] WARNING: m_particleLifeKFP not found")

    # --- color: only the RGB channels of ptxu_Colour, the alpha curve is kept ---
    if args.color:
        r, g, b = args.color

        def recolor(m):
            def rgb(k):
                return (f"<RedChannelColour value=\"{r:g}\" />\n"
                        f"        <GreenChannelColour value=\"{g:g}\" />\n"
                        f"        <BlueChannelColour value=\"{b:g}\" />")
            body = re.sub(r"<RedChannelColour value=\"[-\d.eE+]+\" />\s*"
                          r"<GreenChannelColour value=\"[-\d.eE+]+\" />\s*"
                          r"<BlueChannelColour value=\"[-\d.eE+]+\" />",
                          rgb, m.group(2))
            return m.group(1) + body + m.group(3)

        before = particle
        particle = re.sub(
            r"(<Name>ptxu_Colour:m_rgba(?:Min|Max)KFP</Name>.*?<Keyframes>)(.*?)(</Keyframes>)",
            recolor, particle, flags=re.S)
        print("[i] color written" if particle != before
              else "[!] WARNING: Colour keyframe not found, color NOT CHANGED")

    if args.keep_texture or args.vanilla_texture:
        print(f"[i] NO EMBEDDED TEXTURE: {old[0]}  (no embedded texture written)")
        path = os.path.join(args.folder, new + ".ypt.xml")
        xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
               "<ParticleEffectsList>\n"
               f" <Name>{new}</Name>\n"
               f" <EffectRuleDictionary>\n{effect} </EffectRuleDictionary>\n"
               f" <EmitterRuleDictionary>\n{emitter} </EmitterRuleDictionary>\n"
               f" <ParticleRuleDictionary>\n{particle} </ParticleRuleDictionary>\n"
               " <DrawableDictionary />\n <TextureDictionary />\n"
               "</ParticleEffectsList>\n")
        import xml.etree.ElementTree as ET
        try:
            ET.fromstring(xml)
        except ET.ParseError as e:
            sys.exit(f"THE GENERATED XML DOES NOT PARSE: {e}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"[+] {path}  ({len(xml):,} characters)")
        print(f"    donor effect: {args.effect}  ->  {new}")
        return 0

    dds = os.path.join(args.folder, args.texture + ".dds")
    if not os.path.exists(dds):
        sys.exit(f"DDS not found: {dds}")
    with open(dds, "rb") as fh:
        header = fh.read(128)
    _, _, height, width, _, _, mips = struct.unpack("<7I", header[4:32])
    mips = max(1, mips)
    fmt = {b"DXT1": "D3DFMT_DXT1", b"DXT5": "D3DFMT_DXT5"}.get(
        header[84:88], "D3DFMT_A8R8G8B8")
    flags = args.texture_flags or TEXTURE_FLAGS.get((width, height), TEXTURE_FLAGS[(512, 512)])

    td = (f"  <Item>\n   <Name>{args.texture}</Name>\n"
          f"   <Unk32 value=\"128\" />\n   <Usage>DIFFUSE</Usage>\n"
          f"   <UsageFlags>{flags}</UsageFlags>\n"
          f"   <ExtraFlags value=\"0\" />\n"
          f"   <Width value=\"{width}\" />\n   <Height value=\"{height}\" />\n"
          f"   <MipLevels value=\"{mips}\" />\n   <Format>{fmt}</Format>\n"
          f"   <FileName>{args.texture}.dds</FileName>\n  </Item>\n")

    xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<ParticleEffectsList>\n"
           f" <Name>{new}</Name>\n"
           f" <EffectRuleDictionary>\n{effect} </EffectRuleDictionary>\n"
           f" <EmitterRuleDictionary>\n{emitter} </EmitterRuleDictionary>\n"
           f" <ParticleRuleDictionary>\n{particle} </ParticleRuleDictionary>\n"
           " <DrawableDictionary />\n"
           f" <TextureDictionary>\n{td} </TextureDictionary>\n"
           "</ParticleEffectsList>\n")

    # the generator reads back its own output
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(xml)
    except ET.ParseError as e:
        sys.exit(f"THE GENERATED XML DOES NOT PARSE: {e}")

    path = os.path.join(args.folder, new + ".ypt.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)
    c4 = re.search(r'<UnknownC4 value="([^"]+)"', particle)
    print(f"[+] {path}  ({len(xml):,} characters)")
    print(f"    donor effect: {args.effect}  ->  {new}")
    print(f"    texture     : {old[0]}  ->  {args.texture}  ({width}x{height} {fmt} mip={mips})")
    if c4:
        n = int(c4.group(1)) + 1
        print(f"    UnknownC4={c4.group(1)}  =>  {n} frames  (taken AS IS from the donor)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
