#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_motion.py — writes the particle's MOTION (does not inherit it).

⛔ WHY IT EXISTS: inheriting the donor's motion as-is is nothing more than
   dressing that effect in a new colour. What the eye reads is the motion.
   Three measured cases:

     · `collapse_dust`  <- env_dust_devil_rural_lrg  : the donor has a
       `ptxAttractorDomain` (outer 20.6 / inner 6.8). The attractor spirals
       particles inward and up; in game a TORNADO was seen. Because the donor
       is itself a dust devil.
     · `infection_wave` <- fire_extinguish : `ptxTargetDomain` aims 3.5 m up
       -- a fire extinguisher jet. With a ring sprite it sprayed rings.
     · `concrete_break` <- ent_ray_fam3_dust_motes : spawn volume is a
       **5x5x1 m** box. Splinters spawn scattered over a 5 metre area, not
       from the impact point.

Measured meanings (n=231 suitable donors):
   `ptxCreationDomain:m_sizeOuterKFP`  -> the volume particles SPAWN in
   `ptxTargetDomain:m_positionKFP`     -> direction x distance (speed)
   `ptxu_Acceleration:m_xyzMin/MaxKFP` -> gravity / rise
   `ptxu_Dampening:m_xyzMin/MaxKFP`    -> damping
Examples: drop target [0,0,-4] accel [0,0,-20] · ground fog target [0,0.3,0.01]
accel [0,0,0] · ember target [0,0,0.1] · falling debris target [0,0,-8].

Domain types: CreationDomain and TargetDomain present in **100%**; Attractor
only in **6%** (14/231) -- the tornado risk comes from there, it is removed.
"""
from __future__ import annotations

import re

# ALPHA keyframe: RGB + alpha together. `KEYFRAME_RGB` writes RGB only
# (for motion fields); writing an envelope needs alpha as well.
KEYFRAME_RGBA = ("       <Item>\n"
                 "        <InterpolationInterval value=\"%g\" />\n"
                 "        <KeyFrameMultiplier value=\"%g\" />\n"
                 "        <RedChannelColour value=\"%g\" />\n"
                 "        <GreenChannelColour value=\"%g\" />\n"
                 "        <BlueChannelColour value=\"%g\" />\n"
                 "        <AlphaChannelColour value=\"%g\" />\n"
                 "       </Item>\n")

KEYFRAME_RGB = ("       <Item>\n"
                "        <InterpolationInterval value=\"0\" />\n"
                "        <KeyFrameMultiplier value=\"0\" />\n"
                "        <RedChannelColour value=\"%g\" />\n"
                "        <GreenChannelColour value=\"%g\" />\n"
                "        <BlueChannelColour value=\"%g\" />\n"
                "        <AlphaChannelColour value=\"0\" />\n"
                "       </Item>\n")


def write_kfp(block, full_name, xyz):
    """Sets the first keyframe of a KFP to `xyz`. (text, was_written)

    ⛔ The field can be EMPTY (`<Keyframes />`, self-closing). Then the
       `</Keyframes>` pattern being searched for does not exist; missing this
       once made it read a NEIGHBOURING field's value for a whole round. The
       empty case is filled here too -- otherwise the motion cannot be written.
    """
    i = block.find("<Name>%s</Name>" % full_name)
    if i < 0:
        return block, False
    j = block.find("<Name>", i + 6)
    end = j if j > 0 else len(block)
    section = block[i:end]
    new_kf = "<Keyframes>\n" + (KEYFRAME_RGB % tuple(xyz)) + "      </Keyframes>"
    if "<Keyframes />" in section:
        section2 = section.replace("<Keyframes />", new_kf, 1)
    elif "<Keyframes>" in section:
        section2 = re.sub(r"<Keyframes>.*?</Keyframes>", new_kf, section,
                          count=1, flags=re.S)
    else:
        return block, False
    return block[:i] + section2 + block[end:], True


def write_domain_type(block, index, shape):
    """Changes the `<DomainN><Type value="X" />` field."""
    d = "<Domain%d>" % index
    i = block.find(d)
    if i < 0:
        return block, False
    section = block[i:i + 200]
    new = re.sub(r"<Type value=\"\w+\" />", "<Type value=\"%s\" />" % shape,
                 section, count=1)
    return block[:i] + new + block[i + 200:], new != section


def remove_attractor(block):
    """Neutralises the attractor domain -- the tornado/spiral comes from it.

    ⛔ Do NOT DELETE the node: the `<DomainN>` slots are positional, removing
       one shifts the indices of the rest. Zeroing the radius is both safe
       and enough (the pull field disappears).
    """
    n = 0
    for name in ("ptxAttractorDomain:m_sizeOuterKFP",
                 "ptxAttractorDomain:m_sizeInnerKFP"):
        block, ok = write_kfp(block, name, (0.0, 0.0, 0.0))
        n += 1 if ok else 0
    return block, n


# motion dict key -> (which block, full KFP name)
#   "em" = emitter rule body, "pr" = particle rule body
# ⛔ SIZE MUST BE WRITTEN TOO. Motion was written but size was left from the
#    donor, and the donors turned out mutually incompatible: measured, **38**
#    of 56 families stayed under 0.2 m (five exactly 0.000) -- nothing was
#    visible in game; on the other hand `blood_haze` at 9.7 m covered the
#    screen. Vanilla band: whdMin p50=1.0 p95=7.0 · whdMax p50=1.6 p95=9.9;
#    rules with a zero whdMin are only **68 / 1724 (3.9%)**.
#
# ⚠ `m_sizeScalarKFP` IS A PERCENTAGE (neutral 100). Write the size with whd and
#   pin the scalar to 100; otherwise the donor's scalar (0.44 to 949)
#   distorts the whd we wrote.
MOTION_FIELDS = {
    "size":        ("pr", "ptxu_Size:m_whdMinKFP"),
    "size_max":    ("pr", "ptxu_Size:m_whdMaxKFP"),
    "spawn":       ("em", "ptxCreationDomain:m_sizeOuterKFP"),
    "spawn_inner": ("em", "ptxCreationDomain:m_sizeInnerKFP"),
    "target":      ("em", "ptxTargetDomain:m_positionKFP"),
    "target_size": ("em", "ptxTargetDomain:m_sizeOuterKFP"),
    "accel":       ("pr", "ptxu_Acceleration:m_xyzMinKFP"),
    "accel_max":   ("pr", "ptxu_Acceleration:m_xyzMaxKFP"),
    "damping":     ("pr", "ptxu_Dampening:m_xyzMinKFP"),
    "damping_max": ("pr", "ptxu_Dampening:m_xyzMaxKFP"),
}


def _region(s, dictionary):
    """The (start, end) range of a dictionary in the document."""
    i = s.find("<%s>" % dictionary)
    j = s.find("</%s>" % dictionary)
    return (i, j) if i >= 0 and j > i else (0, len(s))


def _write_in_region(s, dictionary, full_name, xyz):
    """Searches for and writes the KFP ONLY inside that dictionary.

    ⛔ DO NOT SEARCH THE WHOLE DOCUMENT. `ptxEmitterRule:m_sizeScalarKFP`
       appears in TWO places: in the EffectRule's
       `EventEmitters/UnknownData/Unknown10` override list and in the real
       EmitterRule. Writing to the first hit changes the override list and the
       real value stays UNTOUCHED -- the build says "sizeScalar -> 100" but the
       file keeps the donor's 6.41 and the particle comes out 0.003 m and
       invisible. Lock to the region.
    """
    i, j = _region(s, dictionary)
    section, ok = write_kfp(s[i:j], full_name, xyz)
    return s[:i] + section + s[j:], ok


def apply_to_document(s, motion):
    """Writes the motion into a `.ypt.xml` document with a SINGLE emitter/particle.

    (Do NOT use this on a multi-emitter document.)
    """
    notes = []
    if motion.get("remove_attractor"):
        _i, _j = _region(s, "EmitterRuleDictionary")
        _k, n = remove_attractor(s[_i:_j])
        s = s[:_i] + _k + s[_j:]
        if n:
            notes.append("attractor zeroed")
    if "envelope" in motion:
        # ⛔ THE ALPHA ENVELOPE MUST BE WRITABLE TOO. `repair_envelope` only fixes
        #    a BROKEN envelope (single keyframe / pop at the end); it does not
        #    touch the donor's valid envelope that does NOT FIT our family.
        #    Measured: spark donor `water_splash_veh_out` drops alpha to 0.06 at
        #    0.75 s -- right for a water splash, too early for a spark. A spark
        #    should stay BRIGHT for most of its life and fade at the end.
        points = motion["envelope"]          # [(t, alpha), ...]
        for name in ("ptxu_Colour:m_rgbaMinKFP", "ptxu_Colour:m_rgbaMaxKFP"):
            i0, j0 = _region(s, "ParticleRuleDictionary")
            section = s[i0:j0]
            i = section.find("<Name>%s</Name>" % name)
            if i < 0:
                continue
            j = section.find("<Name>", i + 6)
            sub = section[i:j if j > 0 else len(section)]
            m = re.search(r"<RedChannelColour value=\"([-0-9.eE]+)\" />\s*"
                          r"<GreenChannelColour value=\"([-0-9.eE]+)\" />\s*"
                          r"<BlueChannelColour value=\"([-0-9.eE]+)\" />", sub)
            r, g, b = (float(x) for x in m.groups()) if m else (1.0, 1.0, 1.0)
            frames = ""
            for n2, (t, a2) in enumerate(points):
                mult = 0.0 if n2 == 0 else 1.0 / max(t - points[n2 - 1][0], 1e-4)
                frames += (KEYFRAME_RGBA % (t, mult, r, g, b, a2))
            new_sub = re.sub(r"<Keyframes\s*/>|<Keyframes>.*?</Keyframes>",
                             "<Keyframes>\n" + frames + "      </Keyframes>",
                             sub, count=1, flags=re.S)
            section = section[:i] + new_sub + section[(j if j > 0 else len(section)):]
            s = s[:i0] + section + s[j0:]
        notes.append("envelope written: %d keyframes, peak %.2f"
                     % (len(points), max(a2 for _, a2 in points)))

    if "one_shot" in motion:
        # ⛔ CONTINUOUS or ONE SHOT -- `Unknown628` on the emitter.
        #    Measured (n=964): **48/48** of the `bul_*` bullet impacts and
        #    **80%** of the `exp_*` explosions are 1; whereas `fire_*`
        #    0/38, `wheel_*` 0/58, `env_*` 0/27. So 1 = one shot/burst,
        #    0 = continuous. An impact effect left at 0 sprays forever.
        i0, j0 = _region(s, "EmitterRuleDictionary")
        section = s[i0:j0]
        new_section, n = re.subn(r"<Unknown628 value=\"[-0-9.]+\" />",
                                 '<Unknown628 value="%d" />'
                                 % (1 if motion["one_shot"] else 0), section)
        s = s[:i0] + new_section + s[j0:]
        notes.append("one_shot=%s (%d emitters)"
                     % (bool(motion["one_shot"]), n))
    if "shape" in motion:
        s, ok = write_domain_type(s, 1, motion["shape"])
        if ok:
            notes.append("spawn shape -> %s" % motion["shape"])
    if "size" in motion:
        # pull the scalar to neutral so whd is real metres
        s, ok = _write_in_region(s, "EmitterRuleDictionary",
                                 "ptxEmitterRule:m_sizeScalarKFP",
                                 (100.0, 100.0, 0.0))
        if ok:
            notes.append("sizeScalar -> 100 (neutral)")
        else:
            # ⛔ Some donors have NO `m_sizeScalarKFP` (measured: fly_swarm,
            #    moths_swarm). Then the scalar stays whatever it is in the donor
            #    and the whd we write is MULTIPLIED by it -- `fly_cloud` came
            #    out 0.003 m, invisible. Compensation: scale whd by 100/scalar.
            import re as _re
            g = None
            i = s.find("<Name>ptxEmitterRule:m_sizeScalarKFP</Name>")
            if i >= 0:
                j = s.find("<Name>", i + 6)
                k2 = _re.search(r"<RedChannelColour value=\"([-0-9.eE]+)\"",
                                s[i:j if j > 0 else len(s)])
                if k2:
                    g = float(k2.group(1))
            if g and g > 1e-6:
                factor = 100.0 / g
                motion = dict(motion)
                motion["size"] = tuple(x * factor for x in motion["size"])
                notes.append("sizeScalar could not be written (%.3g) -> size x%.1f compensation"
                             % (g, factor))
            else:
                notes.append("sizeScalar could not be written ⛔")
    DICTS = {"em": "EmitterRuleDictionary", "pr": "ParticleRuleDictionary"}
    for key, (where, full) in MOTION_FIELDS.items():
        if key not in motion:
            continue
        v = motion[key]
        s, ok = _write_in_region(s, DICTS[where], full, v)
        notes.append("%s=[%g,%g,%g]%s"
                     % (key, v[0], v[1], v[2], "" if ok else " ⛔NOT WRITTEN"))
        twin = key + "_max"
        if not key.endswith("_max") and twin in MOTION_FIELDS and twin not in motion:
            # ⚠ In vanilla whdMax / whdMin is ~1.6 (p50 1.0 / 1.6). Writing the
            #   same value makes every particle the same size -- it looks mechanical.
            factor = 1.6 if key == "size" else 1.0
            s, _ = _write_in_region(s, DICTS[MOTION_FIELDS[twin][0]], MOTION_FIELDS[twin][1],
                                    tuple(x * factor for x in v))
    return s, notes


def apply(emitter, particle, motion):
    """Writes the motion spec into the emitter+particle blocks.

    motion: {"spawn": (x,y,z), "target": (x,y,z), "accel": (x,y,z),
             "damping": (x,y,z), "shape": "Sphere", "remove_attractor": True}
    Returns: (emitter, particle, notes)
    """
    notes = []
    if motion.get("remove_attractor"):
        emitter, n = remove_attractor(emitter)
        if n:
            notes.append("attractor zeroed (%d fields)" % n)
    if "shape" in motion:
        emitter, ok = write_domain_type(emitter, 1, motion["shape"])
        if ok:
            notes.append("spawn volume shape -> %s" % motion["shape"])

    for key, (where, full) in MOTION_FIELDS.items():
        if key not in motion:
            continue
        v = motion[key]
        if where == "em":
            emitter, ok = write_kfp(emitter, full, v)
        else:
            particle, ok = write_kfp(particle, full, v)
        notes.append("%s = [%g, %g, %g]%s"
                     % (key, v[0], v[1], v[2], "" if ok else "  ⛔ NOT WRITTEN"))
        # ⚠ accel/damping are a min-max PAIR; writing only min leaves the range
        #    with the donor's old max. If max is not given explicitly, match it.
        twin = key + "_max"
        if where == "pr" and not key.endswith("_max") and twin not in motion \
                and twin in MOTION_FIELDS:
            particle, _ = write_kfp(particle, MOTION_FIELDS[twin][1], v)
    return emitter, particle, notes
