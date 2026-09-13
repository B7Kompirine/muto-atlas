#!/usr/bin/env python3
"""build_custom_ptfx.py — builds a custom particle effect (.ypt) FROM SCRATCH.

It does not copy and modify a vanilla effect: it writes the effect/emitter/particle
rules and the texture FROM SCRATCH. None of GTA's effect names, textures or curves
are used.

⚠ HONESTLY: `.ypt` is a binary resource format and its schema has fields whose
meaning is unresolved (`Unknown*`). Their VALUES are required by the format --
they were measured from vanilla files and taken as safe constants. The VISUAL
itself (texture, color, size, lifetime, speed, spawn curve) is entirely ours.

PIPELINE:
  1) make your own sprite with make_dds.py
  2) this script writes the .ypt.xml
  3) CodeWalker XmlYpt.GetYpt(xml, folder) -> binary .ypt
     (the DDS file must be IN THE SAME FOLDER AS THE XML, otherwise it
      crashes with "Texture file not found")

Usage:
  python build_custom_ptfx.py --name my_spore --texture my_ptfx_soft \\
      --folder <output> --color 0.2 0.9 0.35 --lifetime 2.5 --size 0.35 --rate 25
"""
from __future__ import annotations

import argparse
import os
import sys

# --- format constants: measured from vanilla core.ypt, meaning unresolved ---
# These are not "magic numbers", they are required fields of the schema. Do not change them.
#
# ⛔ NEVER WRITE 0 INTO AN UNKNOWN FIELD -- write vanilla's MOST COMMON value.
#    Measured over the 964 effect rules in core.ypt. For most fields zero NEVER
#    occurs in vanilla (such as UnknownA4/A8/AC/B0); these look like distance/
#    LOD bands and if they are zeroed the effect may not draw at any
#    distance. "I don't know, I'll leave it 0" produces a silent failure.
EFFECT_CONSTANTS = """   <Unknown50 value="0xFFFFFFFF" />
   <Unknown54 value="0x1000000" />
   <Unknown70 value="0" />
   <Unknown74 value="0.25" />
   <PlaybackDelay value="2" />
   <PlaybackDelayModifier value="2" />
   <PlaybackSpeedScale value="1" />
   <PlaybackSpeedScaleModifier value="1" />
   <Unknown88 value="0x1010100" />
   <Unknown8C value="0x10004" />
   <CullRadius value="0" />
   <CullDistance value="0" />
   <Unknown98 value="0" />
   <UnknownA0 value="0" />
   <UnknownA4 value="50" />
   <UnknownA8 value="60" />
   <UnknownAC value="10" />
   <UnknownB0 value="30" />
   <UnknownB4 value="0" />
   <UnknownB8 value="0" />
   <UnknownBC value="0x0" />
   <Unknown3A0 value="0x0" />"""

# ⛔ UsageFlags CHANGE WITH THE TEXTURE SIZE -- do not hard-code them.
#    Measured per size over the 107 textures in core.ypt. Writing the wrong flag
#    makes the texture sample wrongly and is SILENT.
TEXTURE_FLAGS = {
    (32, 32):     "X16, UNK24",
    (64, 64):     "X64, X128, UNK24",
    (128, 128):   "X8, X32, X64, X128, UNK24",
    (256, 256):   "X64, Y64, X256, UNK24",
    (512, 512):   "X64, Y64, X256, Y512, UNK24",
    (1024, 1024): "X64, Y64, X256, Y512, Y1024, UNK24",
    (2048, 2048): "X32, X64, X128, X512, X1024, X2048, UNK24",
}

EFFECT_KFP = [
    ("ptxEffectRule:m_colourTintMinKFP", 63744),
    ("ptxEffectRule:m_colourTintMaxKFP", 64000),
    ("ptxEffectRule:m_zoomScalarKFP", 64256),
    ("ptxEffectRule:m_dataSphereKFP", 64512),
    ("ptxEffectRule:m_dataCapsuleKFP", 64768),
]

EMITTER_KFP = [
    ("ptxEmitterRule:m_spawnRateOverTimeKFP", 54272),
    ("ptxEmitterRule:m_spawnRateOverDistKFP", 54528),
    ("ptxEmitterRule:m_particleLifeKFP", 54784),
    ("ptxEmitterRule:m_playbackRateScalarKFP", 55040),
    ("ptxEmitterRule:m_speedScalarKFP", 55296),
    ("ptxEmitterRule:m_sizeScalarKFP", 55552),
    ("ptxEmitterRule:m_accnScalarKFP", 55808),
    ("ptxEmitterRule:m_dampeningScalarKFP", 56064),
    ("ptxEmitterRule:m_matrixWeightScalarKFP", 56320),
    ("ptxEmitterRule:m_inheritVelocityKFP", 56576),
]

DOMAIN_KFP = [
    ("m_positionKFP", 12800), ("m_rotationKFP", 13056),
    ("m_sizeOuterKFP", 13312), ("m_sizeInnerKFP", 13568),
]


def kf(interval=0.0, mult=0.0, r=0.0, g=0.0, b=0.0, a=0.0, indent=7):
    """One keyframe. The R/G/B/A names are MISLEADING: these are four generic channels.
    Their meaning changes with the <Name> field they sit in --
    inside spawn rate 'Red' = rate, inside xyz 'Red' = X."""
    i = " " * indent
    return (f"{i}<Item>\n"
            f"{i} <InterpolationInterval value=\"{interval:g}\" />\n"
            f"{i} <KeyFrameMultiplier value=\"{mult:g}\" />\n"
            f"{i} <RedChannelColour value=\"{r:g}\" />\n"
            f"{i} <GreenChannelColour value=\"{g:g}\" />\n"
            f"{i} <BlueChannelColour value=\"{b:g}\" />\n"
            f"{i} <AlphaChannelColour value=\"{a:g}\" />\n"
            f"{i}</Item>\n")


def kfp(name, unk, frames, indent=4, tag="Item"):
    i = " " * indent
    inner = "".join(frames)
    kf_block = f"{i} <Keyframes>\n{inner}{i} </Keyframes>\n" if inner else f"{i} <Keyframes />\n"
    return (f"{i}<{tag}>\n"
            f"{i} <Name>{name}</Name>\n"
            f"{i} <Unknown6C value=\"{unk}\" />\n"
            f"{kf_block}"
            f"{i}</{tag}>\n")


def domain(tag, class_name, base_unk, radius, pos_z=0.0, indent=3):
    """A domain block.

    ⛔ WHAT MOVES THE PARTICLE IS NOT THE `Velocity` BEHAVIOUR,
       IT IS THE POSITION OF THE TARGET DOMAIN. (Velocity has 0 keyframe slots.)
       Measured: in 89.2% of vanilla emitters the Z of `Domain2:m_positionKFP`
       is non-zero, median +0.400. Rising smoke/spores are made with this
       offset; if both domains share the same centre there is no net direction
       and the effect stays in place.
    """
    i = " " * indent
    p = ""
    for k, (name, unk) in enumerate(DOMAIN_KFP):
        frames = []
        if name == "m_sizeOuterKFP":
            # open the sphere at this radius: the volume the particles spawn in
            frames = [kf(r=radius, g=radius, b=radius, indent=indent + 4)]
        elif name == "m_positionKFP" and pos_z:
            frames = [kf(b=pos_z, indent=indent + 4)]
        p += kfp(f"{class_name}:{name}", base_unk + k * 256, frames,
                 indent=indent + 1, tag=f"KeyframeProperty{k}")
    return (f"{i}<{tag}>\n"
            f"{i} <Type value=\"Sphere\" />\n"
            f"{i} <Unknown10 value=\"0x0\" />\n"
            f"{i} <Unknown258 value=\"{radius:g}\" />\n"
            f"{p}"
            f"{i}</{tag}>\n")


def build_xml(name, texture, color, lifetime, size, rate, speed, radius,
              tex_w=128, tex_h=128, tex_mips=4, tex_fmt="D3DFMT_DXT5",
              rise=0.4, alpha=1.0, sheet_frames=1, anim_speed=0.0,
              tex_flags="X64, Y64, X256, Y512, UNK24", color2=None,
              accel=0.0, spin=0.0, noise=0.0, bounce=0.0,
              light=0.0, light_range=3.0, emissive=0.0,
              anim_c8=1, anim_cc="0x1010100"):
    r, g, b = color
    # ⛔ COLOR CHANGE OVER THE LIFETIME. The Colour behaviour's keyframes
    #    are interpolated over the particle's LIFETIME: the first key is birth,
    #    the last key is death. Giving two different colors produces the 'born
    #    orange, turns green' acid look in a single effect -- there is no need to
    #    stack two separate effects.
    r2, g2, b2 = color2 if color2 else (r, g, b)
    effect_name, emit, part = name, f"{name}_em", f"{name}_pr"

    # --- EFFECT RULE ---
    effect_kfps = "".join(kfp(n, u, [], indent=4) for n, u in EFFECT_KFP)
    effect = (f"  <Item>\n"
              f"   <Name>{effect_name}</Name>\n{EFFECT_CONSTANTS}\n"
              f"   <EventEmitters>\n"
              f"    <Item>\n"
              f"     <EmitterRule>{emit}</EmitterRule>\n"
              f"     <ParticleRule>{part}</ParticleRule>\n"
              f"     <Unknown10 value=\"0\" />\n"
              f"     <Unknown14 value=\"1\" />\n"
              f"     <MoveSpeedScale value=\"1\" />\n"
              f"     <MoveSpeedScaleModifier value=\"1\" />\n"
              f"     <ParticleScale value=\"1\" />\n"
              f"     <ParticleScaleModifier value=\"1\" />\n"
              f"     <Colour1 value=\"0xFFFFFFFF\" />\n"
              f"     <Colour2 value=\"0xFFFFFFFF\" />\n"
              # ⛔ UnknownData IS A REQUIRED BLOCK. Without it the XML parses fine,
              #    the rule dictionaries read back full, but Save() crashes on a
              #    NULL reference in ResourceSystemBlock.set_FilePosition.
              #    Its content may be empty; it MUST EXIST.
              f"     <UnknownData>\n"
              f"      <EventEmitterFlags />\n"
              f"      <Unknown10 />\n"
              f"     </UnknownData>\n"
              f"    </Item>\n"
              f"   </EventEmitters>\n"
              f"   <KeyframeProperties>\n{effect_kfps}   </KeyframeProperties>\n"
              f"  </Item>\n")

    # --- EMITTER RULE: spawn rate, lifetime and speed are ours ---
    emitter_values = {
        "ptxEmitterRule:m_spawnRateOverTimeKFP": [kf(r=rate, g=rate, indent=8)],
        "ptxEmitterRule:m_particleLifeKFP":      [kf(r=lifetime, g=lifetime, indent=8)],
        "ptxEmitterRule:m_speedScalarKFP":       [kf(r=speed,  g=speed,  indent=8)],
        # ⛔ sizeScalar IS ON A PERCENT SCALE, NOT a fraction.
        #    Measured (2,097 keyframes): 5%=1.0 · median=57.6 · 75%=125 · 95%=297.
        #    Writing 1.0 puts it in the bottom 5% -> ~1% of the particle size ->
        #    NOTHING SHOWS IN THE GAME. 100 = neutral.
        #    The same percent scale applies to accn/dampening/matrixWeight
        #    (medians 98.4 / 98.6 / 93.8); speed and life are on a ~1.0 scale.
        "ptxEmitterRule:m_sizeScalarKFP":        [kf(r=100.0, g=100.0, indent=8)],
    }
    emitter_kfps = "".join(kfp(n, u, emitter_values.get(n, []), indent=5) for n, u in EMITTER_KFP)
    emitter = (f"  <Item>\n"
               f"   <Name>{emit}</Name>\n"
               f"   <Unknown10 value=\"2\" />\n"      # 1674/1993
               f"   <Unknown628 value=\"0\" />\n"     # 1116/1993
               f"{domain('Domain1', 'ptxCreationDomain', 12800, radius)}"
               f"{domain('Domain2', 'ptxTargetDomain', 13824, radius, rise)}"
               f"   <KeyframeProperties>\n{emitter_kfps}   </KeyframeProperties>\n"
               f"  </Item>\n")

    # --- PARTICLE RULE: color and size are ours ---
    # The values are the MOST COMMON value over the 1,736 particle rules in core.ypt
    # (share in brackets). The fields written as 0 are 0 in vanilla too.
    rule_constants = "".join(f"   <Unknown{k} value=\"{v}\" />\n" for k, v in (
        ("10", "2"),        # 1341/1736
        ("100", "2"),       # 1098/1736
        ("104", "0"),       # 1545/1736
        ("108", "2"),       # 1347/1736
        ("10C", "0x10100"), # 1638/1736  -- 94%, almost constant
        ("118", "0"),       # 1121/1736
        ("11C", "0"),       # 398/1736 (neck and neck with 3)
        ("1D0", "5"),       # 890/1736
        ("1E0", "0"),       # 1398/1736
        ("1E4", "0"),       # 1732/1736
        ("1E8", "0x101"),   # 1044/1736
        ("1EC", "0"),       # 1722/1736
        ("220", "0x2")))    # 736/1736
    spawner = ("   <Spawner{n}>\n"
               "    <EffectRule />\n"
               "    <Unknown18 value=\"0\" />\n"
               "    <Unknown1C value=\"0\" />\n"
               "    <Unknown20 value=\"0x0\" />\n"
               "    <Unknown24 value=\"0\" />\n"
               "    <Unknown28 value=\"0\" />\n"
               "    <Unknown38 value=\"0\" />\n"
               "    <Unknown3C value=\"0\" />\n"
               "    <Unknown40 value=\"0x0\" />\n"
               "    <Unknown44 value=\"0\" />\n"
               "    <Unknown48 value=\"0\" />\n"
               "    <Unknown68 value=\"0\" />\n"
               "    <Unknown6C value=\"0x0\" />\n"
               "   </Spawner{n}>\n")

    # --- BEHAVIOURS ---
    # ⛔ EVERY BEHAVIOUR TYPE HAS A FIXED SLOT COUNT AND ALL SLOTS MUST BE WRITTEN.
    #    An unwritten slot leaves a null block; the XML parses fine, the dictionaries
    #    read back full, but Save() crashes with a NullReferenceException inside
    #    ResourceBuilder.AssignPositions. The error message does NOT SAY which
    #    slot it was -- that is why the table is below, not guessed.
    #
    #    Measured over the 15,430 behaviours in core.ypt; every type shows ONE
    #    slot count, no exceptions:
    #      Age 0 · Velocity 0 · Sprite 0 · MatrixWeight 1 · AnimateTexture 1
    #      Wind 1 · Trail 1 · Attractor 1 · Acceleration 2 · Dampening 2
    #      Collision 2 · ZCull 2 · Decal 2 · Colour 3 · Size 4 · Rotation 4
    #      Noise 4 · FogVolume 7 · Light 9
    #    The <Name> values are constant 1736/1736 (real schema). <Unknown6C>, however,
    #    is the position inside the file and steps by 256; it is not constant.
    #
    #    Velocity having 0 slots is no surprise: particle speed is defined not
    #    in a behaviour but in the EMITTER rule's speedScalar and in the
    #    creation/target domains.
    def behaviour(kind, slots=(), fields=(), base=30208):
        g = "".join(f"     <Unknown{k} value=\"{v}\" />\n" for k, v in fields)
        p = ""
        for i, (slot_name, frames) in enumerate(slots):
            inner = "".join(frames)
            kb = f"      <Keyframes>\n{inner}      </Keyframes>\n" if inner else "      <Keyframes />\n"
            p += (f"     <KeyframeProperty{i}>\n"
                  f"      <Name>{slot_name}</Name>\n"
                  f"      <Unknown6C value=\"{base + i * 256}\" />\n"
                  f"{kb}"
                  f"     </KeyframeProperty{i}>\n")
        return f"    <Item>\n     <Type value=\"{kind}\" />\n{g}{p}    </Item>\n"

    # ⛔ BEHAVIOUR ORDER IS NOT ARBITRARY. Measured in core.ypt by mean normalised
    #    position (15,430 behaviours) -- canonical order:
    #      Age · Acceleration · Attractor · Velocity · Rotation · Noise ·
    #      Size · Dampening · MatrixWeight · Wind · ZCull · Collision ·
    #      AnimateTexture · Light · Colour · Sprite/Model/Trail (always last)
    #    AnimateTexture comes before Sprite in 781/781 rules.
    behaviours = (
        behaviour("Age")
        # ⛔ Acceleration xyz in METRES/S^2. Z positive for rising smoke/mist.
        + (behaviour("Acceleration",
                     (("ptxu_Acceleration:m_xyzMinKFP",
                       [kf(b=accel * 0.6, indent=8)]),
                      ("ptxu_Acceleration:m_xyzMaxKFP",
                       [kf(b=accel, indent=8)])),
                     (("158", "0"), ("15C", "0")), base=11776)
           if accel else "")
        + behaviour("Velocity")
        # ⛔ Rotation: the first two slots are the INITIAL angle (randomness), the
        #    last two slots are the SPIN SPEED. In degrees. Without an initial angle
        #    all particles face the same way and the repetition is visible.
        + (behaviour("Rotation",
                     (("ptxu_Rotation:m_initialAngleMinKFP", [kf(r=0.0, indent=8)]),
                      ("ptxu_Rotation:m_initialAngleMaxKFP", [kf(r=360.0, indent=8)]),
                      ("ptxu_Rotation:m_angleMinKFP", [kf(r=-spin, indent=8)]),
                      ("ptxu_Rotation:m_angleMaxKFP", [kf(r=spin, indent=8)])),
                     (("270", "0"), ("274", "0"), ("278", "0x1"), ("27C", "0")),
                     base=18944)
           if spin else "")
        # ⛔ Noise = TURBULENCE. Position noise shifts the particle, velocity
        #    noise disturbs its direction. Without both, smoke travels straight.
        + (behaviour("Noise",
                     (("ptxu_Noise:m_posNoiseMinKFP",
                       [kf(r=-noise, g=-noise, b=-noise * .5, indent=8)]),
                      ("ptxu_Noise:m_posNoiseMaxKFP",
                       [kf(r=noise, g=noise, b=noise * .5, indent=8)]),
                      ("ptxu_Noise:m_velNoiseMinKFP",
                       [kf(r=-noise * .8, g=-noise * .8, b=0.0, indent=8)]),
                      ("ptxu_Noise:m_velNoiseMaxKFP",
                       [kf(r=noise * .8, g=noise * .8, b=0.0, indent=8)])),
                     (("270", "0"), ("274", "1")), base=12544)
           if noise else "")
        + behaviour("Size",
                    # whd = width/height/depth. In vanilla the B (depth) median is 0.000 --
                    # depth is not written because the sprite is a flat quad.
                    (("ptxu_Size:m_whdMinKFP",
                      [kf(r=size * .6, g=size * .6, indent=8),
                       kf(interval=1.0, r=size * 1.4, g=size * 1.4, indent=8)]),
                     ("ptxu_Size:m_whdMaxKFP",
                      [kf(r=size, g=size, indent=8),
                       kf(interval=1.0, r=size * 2.0, g=size * 2.0, indent=8)]),
                     # ⛔ tblrScalar CANNOT BE LEFT EMPTY. In vanilla 1727/1736 are filled
                     #    (99.5%) and the value is almost always 1.0 -- i.e. a neutral
                     #    multiplier. Leaving it empty makes the multiplier 0 and the sprite
                     #    is drawn at zero size: the effect "works", nothing shows.
                     ("ptxu_Size:m_tblrScalarKFP",
                      [kf(r=1.0, g=1.0, b=1.0, indent=8)]),
                     # tblrVelScalar is empty in 83.6% of vanilla -- leaving it empty is normal.
                     ("ptxu_Size:m_tblrVelScalarKFP", [])),
                    (("270", "0"), ("274", "1")), base=35840)
        # ⛔ Collision: the particle hits the world. bounciness 0=sticks,
        #    1=full bounce. bounceDirVar is the direction variance -- left at 0,
        #    they all bounce at the same angle and it looks mechanical.
        + (behaviour("Collision",
                     (("ptxu_Collision:m_bouncinessKFP", [kf(r=bounce, indent=8)]),
                      ("ptxu_Collision:m_bounceDirVarKFP", [kf(r=0.35, indent=8)])),
                     (("150", "0.1"), ("154", "0"), ("158", "100"), ("15C", "0")),
                     base=14336)
           if bounce else "")
        # ⛔ SPRITE SHEET ANIMATION = the `AnimateTexture` behaviour.
        #    Measured by counting two independent vanilla sheets BY EYE:
        #      ptfx_smoke_billow_anim_rgba  1024x1024  6x6 = 36 frames  -> C4 = 35
        #      ptfx_water_splashes_sheet     512x512   2x2 =  4 frames  -> C4 =  3
        #    So `UnknownC4` = FRAME COUNT - 1 (the index of the last frame).
        #    Square grid: columns = rows = sqrt(frames). Frames run left to right,
        #    top to bottom.
        #    UnknownCC 0x1000100 is the combination the 6x6 sheets use.
        #    If m_animRateKFP is left empty the engine plays at its default speed;
        #    if a value is given, the flap speed is set from there.
        + (behaviour("AnimateTexture",
                     (("ptxu_AnimateTexture:m_animRateKFP",
                       [kf(r=anim_speed, g=anim_speed, indent=8)] if anim_speed else []),),
                     (("C0", "0"), ("C4", str(max(0, sheet_frames - 1))),
                      ("C8", str(anim_c8)), ("CC", anim_cc)), base=31488)
           if sheet_frames > 1 else "")
        # ⛔ Light: the particle emits REAL LIGHT -- it lights the ground and the
        #    surroundings. This is what breaks the "flat color lying on the ground" feel.
        #    ALL 9 slots must be written; the corona slots may stay empty.
        + (behaviour("Light",
                     (("ptxu_Light:m_rgbMinKFP", [kf(r=r, g=g, b=b, indent=8)]),
                      ("ptxu_Light:m_rgbMaxKFP", [kf(r=r2, g=g2, b=b2, indent=8)]),
                      ("ptxu_Light:m_intensityKFP",
                       [kf(r=light, g=light, indent=8),
                        kf(interval=1.0, r=0.0, g=0.0, indent=8)]),
                      ("ptxu_Light:m_rangeKFP",
                       [kf(r=light_range, g=light_range, indent=8)]),
                      ("ptxu_Light:m_coronaRgbMinKFP", []),
                      ("ptxu_Light:m_coronaRgbMaxKFP", []),
                      ("ptxu_Light:m_coronaIntensityKFP", []),
                      ("ptxu_Light:m_coronaSizeKFP", []),
                      ("ptxu_Light:m_coronaFlareKFP", [])),
                     (("540", "0"), ("544", "0x101"), ("548", "0x0"), ("54C", "0")),
                     base=40448)
           if light else "")
        + behaviour("Colour",
                    (("ptxu_Colour:m_rgbaMinKFP",
                      [kf(r=r, g=g, b=b, a=alpha, indent=8),
                       kf(interval=1.0, r=r2, g=g2, b=b2, a=0.0, indent=8)]),
                     ("ptxu_Colour:m_rgbaMaxKFP",
                      [kf(r=r, g=g, b=b, a=alpha, indent=8),
                       kf(interval=1.0, r=r2, g=g2, b=b2, a=0.0, indent=8)]),
                     # Self-lit glow. Empty in 71.7% of vanilla
                     # -- but the secret of glowing liquid/fire is here.
                     ("ptxu_Colour:m_emissiveIntensityKFP",
                      [kf(r=emissive, g=emissive, indent=8)] if emissive else [])),
                    (("1E0", "0"), ("1E4", "0x101")), base=31744)
        + behaviour("Sprite", (), (
            ("30", "0"), ("34", "0"), ("38", "0"), ("40", "0"), ("44", "0"),
            ("48", "0"), ("4C", "0"), ("50", "0"), ("54", "0"), ("58", "0"),
            ("5C", "0x100"), ("60", "0x0")))
    )

    # ⛔ THE TEXTURE BINDING IS NOT INSIDE <Behaviours>, IT IS INSIDE <ShaderVars>.
    #    Measured (cut_arena + core): Behaviours carry only these 10 types --
    #    Age Acceleration Velocity Rotation Size Dampening MatrixWeight
    #    Wind Colour Sprite. Texture NEVER APPEARS THERE.
    # ⛔ <Name> is not the texture name, it is the SHADER SAMPLER SLOT (diffusetex2 /
    #    normalspecmap / refractionmap); the real name is in <TextureName>.
    #    If they are swapped the XML parses, no error appears, the texture is NOT BOUND.
    shadervars = (f"    <Item>\n     <Type value=\"Texture\" />\n"
                  f"     <Name>diffusetex2</Name>\n"
                  f"     <Unknown18 value=\"4\" />\n     <Unknown3C value=\"0\" />\n"
                  f"     <TextureName>{texture}</TextureName>\n    </Item>\n")

    particle = (f"  <Item>\n"
                f"   <Name>{part}</Name>\n"
                # ⛔ FxcTechnique IS NOT FREE TEXT. In vanilla's 1,736
                #    particle rules only these 6 values occur:
                #      RGBA_lit_soft (904) · RGBA_lit (425) · RGB_lit_soft (136)
                #      RGB_lit (75) · RGB_soft (70) · RGBA_soft (30)
                #    'default' NEVER OCCURS -- if it is written the shader does not
                #    resolve and the effect silently does not draw. RGBA = texture with
                #    alpha (ours), _soft = depth fade (soft edge).
                f"   <FxcFile>ptfx_sprite</FxcFile>\n"
                f"   <FxcTechnique>RGBA_lit_soft</FxcTechnique>\n"
                f"{rule_constants}"
                f"{spawner.replace('{n}', '1')}{spawner.replace('{n}', '2')}"
                f"   <Behaviours>\n{behaviours}   </Behaviours>\n"
                f"   <ShaderVars>\n{shadervars}   </ShaderVars>\n"
                f"  </Item>\n")

    return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<ParticleEffectsList>\n"
            f" <Name>{name}</Name>\n"
            f" <EffectRuleDictionary>\n{effect} </EffectRuleDictionary>\n"
            f" <EmitterRuleDictionary>\n{emitter} </EmitterRuleDictionary>\n"
            f" <ParticleRuleDictionary>\n{particle} </ParticleRuleDictionary>\n"
            " <DrawableDictionary />\n"
            " <TextureDictionary>\n"
            # Width/Height/MipLevels/Format are REQUIRED.
            # ⛔ The values are read FROM THE DDS HEADER, not hard-coded. A wrongly
            #    declared mip count/format silently produces a broken texture.
            #    All 107 particle textures in vanilla are DXT (DXT5 75 /
            #    DXT1 32), mips 4-9; there is NO uncompressed EXAMPLE.
            f"  <Item>\n   <Name>{texture}</Name>\n"
            f"   <Unk32 value=\"32\" />\n   <Usage>DIFFUSE</Usage>\n"
            f"   <UsageFlags>X8, X16, X64, X128, UNK24</UsageFlags>\n"
            f"   <ExtraFlags value=\"0\" />\n"
            f"   <Width value=\"{tex_w}\" />\n   <Height value=\"{tex_h}\" />\n"
            f"   <MipLevels value=\"{tex_mips}\" />\n   <Format>{tex_fmt}</Format>\n"
            f"   <FileName>{texture}.dds</FileName>\n  </Item>\n"
            " </TextureDictionary>\n"
            "</ParticleEffectsList>\n")


def main() -> int:
    # Help and messages carry non-ASCII marks; a console with a legacy code page cannot encode
    # them and argparse would crash. Replace what the console cannot show.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", "--ad", dest="name", required=True,
                    help="effect/asset name, e.g. my_spore")
    ap.add_argument("--texture", "--doku", dest="texture", required=True,
                    help="DDS file name (without extension)")
    ap.add_argument("--folder", "--klasor", dest="folder", required=True,
                    help="folder where the XML and the DDS sit together")
    ap.add_argument("--color", "--renk", dest="color", nargs=3, type=float,
                    default=[0.2, 0.9, 0.35], metavar=("R", "G", "B"))
    ap.add_argument("--lifetime", "--omur", dest="lifetime", type=float, default=2.5,
                    help="particle lifetime (s)")
    ap.add_argument("--size", "--boyut", dest="size", type=float, default=0.35,
                    help="particle size (m)")
    ap.add_argument("--rate", "--oran", dest="rate", type=float, default=8.0,
                    help="spawn rate (per s). Vanilla median 5, 75th percentile 16.")
    ap.add_argument("--speed", "--hiz", dest="speed", type=float, default=1.2,
                    help="speedScalar: speed multiplier towards the target domain "
                         "(vanilla median 0.85). Not the direction, the SPEED.")
    ap.add_argument("--radius", "--yaricap", dest="radius", type=float, default=0.45,
                    help="spawn sphere radius (m) -- if it is too narrow the "
                         "particles pile up and look like one opaque ball")
    # ⛔ The rise comes from the target domain position, NOT from the Velocity behaviour.
    #    In 89.2% of vanilla emitters Domain2 Z != 0, median +0.400.
    ap.add_argument("--rise", "--yukselme", dest="rise", type=float, default=0.4,
                    help="target domain Z offset (m) -- pulls the particles upwards")
    ap.add_argument("--color2", "--renk2", dest="color2", nargs=3, type=float, default=None,
                    metavar=("R", "G", "B"),
                    help="color at death; if omitted --color stays constant")
    # --- behaviours that bring the look to life (0 = off) ---
    ap.add_argument("--accel", "--ivme", dest="accel", type=float, default=0.0,
                    help="Z acceleration m/s^2; positive for rising smoke")
    ap.add_argument("--spin", "--donme", dest="spin", type=float, default=0.0,
                    help="spin speed (degrees/s); brings a static blob to life")
    ap.add_argument("--noise", "--gurultu", dest="noise", type=float, default=0.0,
                    help="turbulence; smoke curls instead of going straight")
    ap.add_argument("--bounce", "--sekme", dest="bounce", type=float, default=0.0,
                    help="Collision: 0=sticks 1=full bounce")
    ap.add_argument("--light", "--isik", dest="light", type=float, default=0.0,
                    help="the particle emits REAL light (intensity)")
    ap.add_argument("--light-range", "--isik-menzil", dest="light_range", type=float,
                    default=3.0, help="light range (m)")
    ap.add_argument("--emissive", "--parlama", dest="emissive", type=float, default=0.0,
                    help="emissive: self-lit glow")
    ap.add_argument("--alpha", "--alfa", dest="alpha", type=float, default=1.0,
                    help="peak opacity 0..1; lower it for a dense effect")
    # ⛔ The frame count must match the TEXTURE: a square grid (sqrt) is assumed.
    ap.add_argument("--sheet", type=int, default=1, metavar="FRAMES",
                    help="sprite sheet frame count (16 = 4x4). 1 = no animation")
    ap.add_argument("--anim-speed", "--animhiz", dest="anim_speed", type=float, default=0.0,
                    help="flap speed; 0 = engine default")
    # Two fields of AnimateTexture whose meaning is unresolved. Vanilla distribution:
    #   C8: 1 x476 · 0 x251 · 2 x5 · 4 x1        (in rules with C4>0)
    #   CC: 0x01010100 x367 dominant; 0x01000100 / 0x01000000 / 0x01010000
    # Both vary for the SAME texture, so they do not encode the grid --
    # but by default the DOMINANT combination is written.
    ap.add_argument("--animc8", type=int, default=1, help="AnimateTexture C8")
    ap.add_argument("--animcc", default="0x1010100", help="AnimateTexture CC")
    args = ap.parse_args()

    dds = os.path.join(args.folder, args.texture + ".dds")
    if not os.path.exists(dds):
        sys.exit(f"ERROR: {dds} not found.\n"
                 f"  Make it first: python make_dds.py \"{dds}\" --pattern soft")

    # ⛔ Size/mip/format are read FROM THE DDS HEADER, not guessed.
    #    If the value declared in the XML does not match the file, the texture silently breaks.
    import struct
    with open(dds, "rb") as fh:
        header = fh.read(128)
    _, _, tex_h, tex_w, _, _, tex_mips = struct.unpack("<7I", header[4:32])
    tex_mips = max(1, tex_mips)
    fourcc = header[84:88]
    tex_fmt = {b"DXT1": "D3DFMT_DXT1", b"DXT3": "D3DFMT_DXT3",
               b"DXT5": "D3DFMT_DXT5"}.get(fourcc, "D3DFMT_A8R8G8B8")
    if tex_fmt == "D3DFMT_A8R8G8B8":
        print("[!] WARNING: the texture is uncompressed. All 107 particle "
              "textures in vanilla are DXT -- it may be rejected in the game.")
    if args.sheet > 1:
        import math as _m
        k = _m.isqrt(args.sheet)
        if k * k != args.sheet:
            sys.exit(f"ERROR: --sheet {args.sheet} is not a perfect square. The grid must "
                     f"be square (4/9/16/25/36...).")
        # ⛔ THE GRID DOES NOT HAVE TO DIVIDE THE TEXTURE EXACTLY - this requirement WAS
        #    WRONG and broke the whole chain. Vanilla `ptfx_smoke_wispy_anim`
        #    is 7x7 on 1024x1024: 1024/7 = 146.29. The engine samples in UV space
        #    in 1/k steps, it does not look for pixel alignment. Because of this wrong
        #    requirement 36 frames were rejected and we moved to 64 frames (8x8) -> see below.
        if tex_w % k or tex_h % k:
            print(f"[i] note: a {k}x{k} grid does not divide a {tex_w}x{tex_h} texture exactly "
                  f"(cell {tex_w/k:.2f}px). Vanilla does this too -- not a problem.")

        # ⛔ THE FRAME COUNT MUST NOT GO BEYOND THE VANILLA BAND. 781 AnimateTexture
        #    behaviours were measured in core.ypt: `Unknown_C4h` **max 49**,
        #    i.e. at most 50 frames; there are ZERO rules with C4 > 63. 64 frames (C4=63)
        #    were tried and in the game the engine did NOT apply the grid AT ALL -- every
        #    sprite drew the WHOLE 8x8 sheet in one frame. The symptom is not "animation
        #    slow/frozen" but "a grid made of small images".
        #    The safe ceiling is the measured vanilla band: 36 (6x6) or 49 (7x7).
        if args.sheet > 49:
            sys.exit(f"ERROR: --sheet {args.sheet} is outside the vanilla band "
                     f"(measured max 50 frames / C4=49). The engine does not apply "
                     f"the grid and draws the whole sheet in one frame. "
                     f"Use 36 (6x6) or 49 (7x7).")
        print(f"[i] sheet: {k}x{k} = {args.sheet} frames, cell {tex_w/k:.1f}x{tex_h/k:.1f}px "
              f"-> UnknownC4={args.sheet-1}")
    tex_flags = TEXTURE_FLAGS.get((tex_w, tex_h))
    if tex_flags is None:
        tex_flags = TEXTURE_FLAGS[(512, 512)]
        print(f"[!] WARNING: no measured UsageFlags for {tex_w}x{tex_h}, "
              f"used the 512x512 ones -- not verified.")
    print(f"[i] texture: {tex_w}x{tex_h} {tex_fmt} mip={tex_mips}  flags={tex_flags}")
    xml = build_xml(args.name, args.texture, args.color, args.lifetime, args.size,
                    args.rate, args.speed, args.radius, tex_w, tex_h, tex_mips, tex_fmt,
                    args.rise, args.alpha, args.sheet, args.anim_speed, tex_flags,
                    args.color2, args.accel, args.spin, args.noise, args.bounce,
                    args.light, args.light_range, args.emissive,
                    anim_c8=args.animc8, anim_cc=args.animcc)

    # READ BACK YOUR OWN OUTPUT: XML that does not parse silently fails to load in the game
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(xml)
    except ET.ParseError as e:
        sys.exit(f"ERROR: the generated XML does not parse: {e}")

    path = os.path.join(args.folder, f"{args.name}.ypt.xml")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(xml)
    print(f"[+] {path}  ({len(xml)} characters)")
    print(f"[+] effect={args.name}  texture={args.texture}  color={args.color}  "
          f"lifetime={args.lifetime}s size={args.size}m rate={args.rate}/s")
    print("\nNext: convert to binary with CodeWalker "
          "(XmlYpt.GetYpt + Save) -- the DDS must be in the same folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
