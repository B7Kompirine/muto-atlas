#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_quality_gate.py — audits the generated `.ypt` against VANILLA.

Question: is there "needlessly too much / needlessly too little effect"? This
cannot be judged by eye, it is measured. Two separate criteria are used:

  1. DONOR DRIFT (exact reference). The generated effect is compared field by
     field with its own donor. If a field for which NO override is written in
     the spec has changed, it is an ACCIDENT -> VIOLATION. A written change is expected.

  2. VANILLA BAND (population reference). The concurrent particle load
     `load = avg(spawnRate) x avg(particleLife)` is placed in the distribution
     of all vanilla emitters. Below p05 means "needlessly too little", above
     p95 "needlessly too much".

⛔ KFP channel meaning measured: `RedChannelColour` = MIN, `GreenChannelColour`
   = MAX. Reading a single number (the first channel) ignores the top of the
   range; an emitter that looks sparse may actually be 3x denser.
⛔ `m_sizeScalarKFP` IS A PERCENTAGE (neutral 100). Writing 1.0 drops the size to
   1%; the gate warns when it sees a sizeScalar around 1.0.

Usage:
  python ptfx_quality_gate.py --group virus_ambient
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptfx_build_catalog import GROUPS, VANILLA, OUT_DIR, GROUP_ALIASES  # noqa: E402
from ptfx_motion import MOTION_FIELDS  # noqa: E402

# emitter fields to measure -> (spec override key, human name)
FIELDS = {
    "m_spawnRateOverTimeKFP": ("rate", "spawn rate /s"),
    "m_particleLifeKFP": ("lifetime", "particle life s"),
    "m_sizeScalarKFP": ("size_scale", "size scale %"),
}


def kfp_body(block, full_name):
    """Returns ONLY the KFP's OWN <Keyframes> body.

    ⛔ DO NOT WRITE `<Name>X</Name>(.*?)</Keyframes>`. If the field is empty the XML
       has `<Keyframes />` (self-closing); the `</Keyframes>` pattern being
       searched for does NOT EXIST there and the regex captures the NEXT field's
       body. Measured: the `ptxTargetDomain:m_positionKFP` field of
       `ent_amb_fbi_smoke_land_hvy` is empty, the read slid to `m_rotationKFP`
       and gave **[90, -30, 0]** as the position -- degrees, not a position.
       A silent and completely convincing misread.

    The right way: first cut the field's OWN boundary (up to the next <Name>),
    then search for <Keyframes> inside it.
    """
    i = block.find("<Name>%s</Name>" % full_name)
    if i < 0:
        return None
    j = block.find("<Name>", i + 6)
    section = block[i:j if j > 0 else len(block)]
    m = re.search(r"<Keyframes>(.*?)</Keyframes>", section, re.S)
    return m.group(1) if m else None


def kfp(block, name):
    """Extracts the (min, max) value of a KFP from an emitter block."""
    g = kfp_body(block, "ptxEmitterRule:%s" % name)
    if g is None:
        return None
    k = re.findall(r"<(?:Red|Green)ChannelColour value=\"([-0-9.eE]+)\"", g)
    if len(k) < 2:
        return None
    return (float(k[0]), float(k[1]))


def iter_blocks(xml, dictionary):
    """Yields every rule inside a dictionary as (name, block)."""
    i = xml.find("<%s>" % dictionary)
    j = xml.find("</%s>" % dictionary)
    if i < 0:
        return
    body = xml[i:j]
    # ⛔ Splitting on the top-level <Item> boundary with a regex trips on nested
    #    <Item>s. Split on the emitter's own top <Name> lines: every emitter
    #    starts with a full name and lasts until the next one.
    tops = [m.start() for m in re.finditer(r"\n   <Name>[^<]+</Name>", body)]
    for n, s in enumerate(tops):
        e = tops[n + 1] if n + 1 < len(tops) else len(body)
        block = body[s:e]
        name = re.search(r"<Name>([^<]+)</Name>", block).group(1)
        yield name, block


def kfp_envelope(block, name):
    """Returns the (time, alpha) envelope of a KFP. time 0..1 = particle life.

    ⛔ In a `.ypt` this IS the "animation". Because sheet slicing does not work
       (see reference §1e) we use a single-frame sprite; the sense of motion
       comes ENTIRELY from these curves and from rotation. If the curve is
       flat the particle does not look alive, it looks pasted on.
    """
    g = kfp_body(block, name)
    if g is None:
        return None
    it = re.findall(r"<InterpolationInterval value=\"([-0-9.eE]+)\" />.*?"
                    r"<AlphaChannelColour value=\"([-0-9.eE]+)\" />", g, re.S)
    return [(float(a), float(b)) for a, b in it]


def load_estimate(rate, life):
    """Concurrent particle count ~ avg(rate) x avg(life)."""
    if not rate or not life:
        return None
    return ((rate[0] + rate[1]) / 2.0) * ((life[0] + life[1]) / 2.0)


def percentile(values, p):
    d = sorted(values)
    if not d:
        return 0.0
    k = (len(d) - 1) * p / 100.0
    a, b = int(k), min(int(k) + 1, len(d) - 1)
    return d[a] + (d[b] - d[a]) * (k - a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", "--grup", dest="group", default="virus_ambient",
                    type=lambda v: GROUP_ALIASES.get(v, v))
    a = ap.parse_args()

    print("reading vanilla...")
    van = io.open(VANILLA, encoding="utf-8", errors="replace").read()
    vem = {}
    loads = []
    for name, block in iter_blocks(van, "EmitterRuleDictionary"):
        vem[name] = block
        y = load_estimate(kfp(block, "m_spawnRateOverTimeKFP"), kfp(block, "m_particleLifeKFP"))
        if y and y > 0:
            loads.append(y)
    veffect = {}
    for name, block in iter_blocks(van, "EffectRuleDictionary"):
        e = re.findall(r"<EmitterRule>([^<]*)</EmitterRule>", block)
        if len(e) == 1:
            veffect[name] = e[0]
    p05, p50, p95 = percentile(loads, 5), percentile(loads, 50), percentile(loads, 95)
    print("vanilla emitters: %d | concurrent load p05=%.0f  median=%.0f  p95=%.0f\n"
          % (len(vem), p05, p50, p95))

    passed, violations = 0, 0
    for entry in GROUPS[a.group]:
        effect, donor, sprite, color, ovr, reason = entry[:6]
        motion = entry[6] if len(entry) > 6 else {}
        name = "my_" + effect
        path = os.path.join(OUT_DIR, name + ".ypt.xml")
        if not os.path.exists(path):
            print("  NO FILE  %-18s" % effect)
            violations += 1
            continue
        s = io.open(path, encoding="utf-8", errors="replace").read()
        blocks = list(iter_blocks(s, "EmitterRuleDictionary"))
        if len(blocks) != 1:
            print("  FAIL   %-18s emitter count %d (must be 1)" % (effect, len(blocks)))
            violations += 1
            continue
        ours = blocks[0][1]

        # ⛔ The emitter name is NOT THE SAME as the effect name (that is why
        #    `fire_extinguish` was not found). The link is in the
        #    `<EmitterRule>name</EmitterRule>` field -- read the link instead of
        #    guessing from the name.
        dblock = vem.get(veffect.get(donor)) if donor in veffect else None

        notes, bad = [], False

        # --- 1. donor drift ---------------------------------------------------
        if dblock:
            for field, (key, human) in FIELDS.items():
                ou, dn = kfp(ours, field), kfp(dblock, field)
                if not ou or not dn:
                    continue
                differs = abs(ou[0] - dn[0]) > 1e-4 or abs(ou[1] - dn[1]) > 1e-4
                # ⚠ If `size` is in the motion spec, `sizeScalar` is DELIBERATELY
                #   pulled to 100 (the percentage scale must be neutral so whd is
                #   real metres). This is a declared change, not an accident.
                if key == "size_scale" and "size" in (motion or {}):
                    continue
                if differs and key not in ovr:
                    notes.append("ACCIDENT %s: %.4g-%.4g -> %.4g-%.4g (no override)"
                                 % (human, dn[0], dn[1], ou[0], ou[1]))
                    bad = True
                elif not differs and key in ovr:
                    notes.append("NO EFFECT %s: override written, value unchanged" % human)
                    bad = True
                elif differs:
                    # so it can be checked by eye whether the direction matches the reason
                    notes.append("%s: %.4g-%.4g -> %.4g-%.4g"
                                 % (human, dn[0], dn[1], ou[0], ou[1]))
        else:
            notes.append("donor emitter not found -- drift could not be measured")
            bad = True

        # --- 2. vanilla band --------------------------------------------------
        r, l = kfp(ours, "m_spawnRateOverTimeKFP"), kfp(ours, "m_particleLifeKFP")
        y = load_estimate(r, l)
        if y is None:
            notes.append("rate/lifetime could not be read")
            bad = True
        else:
            # ⛔ Do NOT apply the band UNCONDITIONALLY. By definition 5% of
            #    vanilla's own effects are above p95; keeping the donor's value
            #    and breaking the band is exactly what "like vanilla" means.
            #    The band should only measure whether WE moved the load away
            #    from the donor.
            dy = load_estimate(kfp(dblock, "m_spawnRateOverTimeKFP"),
                               kfp(dblock, "m_particleLifeKFP")) if dblock else None
            near_donor = dy and abs(y - dy) <= 0.02 * max(dy, 1.0)
            if near_donor:
                pass
            elif y > p95:
                notes.append("TOO MUCH: load %.0f > p95 %.0f (donor %.0f)"
                             % (y, p95, dy or 0))
                bad = True
            elif y < p05:
                notes.append("TOO LITTLE: load %.2f < p05 %.2f (donor %.0f)"
                             % (y, p05, dy or 0))
                bad = True

        # --- 3. silent breakers -----------------------------------------------
        c4 = re.findall(r"<UnknownC4 value=\"(\d+)\"", s)
        if any(x != "0" for x in c4):
            notes.append("UnknownC4=%s (sheet slicing does not work in a custom ypt)"
                         % ",".join(c4))
            bad = True
        tech = re.findall(r"<FxcTechnique>(\w+)</FxcTechnique>", s)
        if any(not t.startswith("RGBA") for t in tech):
            notes.append("technique %s ignores alpha" % ",".join(tech))
            bad = True
        tex = re.findall(r"<TextureName>([^<]+)</TextureName>", s)
        if tex != [name]:
            notes.append("texture name %s (expected %s)" % (tex, name))
            bad = True
        # ⛔ This rule only applies if WE wrote the size. The donor's own value
        #    is vanilla-correct by definition: `ent_amb_fbi_cinder` carries
        #    0.4437 and 2% of vanilla sizeScalars are below 1.5 (n=1901).
        #    Reporting the donor value as an "error" is a false alarm.
        sz = kfp(ours, "m_sizeScalarKFP")
        if "size_scale" in ovr and sz and 0 < sz[1] <= 1.5:
            notes.append("sizeScalar %.4g -- a PERCENTAGE scale, neutral 100" % sz[1])
            bad = True

        # --- 4. ANIMATION ENVELOPE --------------------------------------------
        # Measured (n=1735 vanilla particle rules):
        #   alpha down to 0 at t=1            -> 88.2%  (those that do not POP: vanish abruptly)
        #   alpha starting from 0 at t=0      -> 44.7%  (so an instant appearance is NORMAL)
        #   keyframe count median 3; 9.3% have a single keyframe = constant alpha
        # ⛔ Check BOTH the MIN and the MAX envelope. For one round only min was
        #    checked, and `paper_scatter` and `rubble_rain` "passed" the gate
        #    although their MAX envelope ended at 0.8 and popped.
        prb = s[s.find("<ParticleRuleDictionary>"):]
        for kfpname, label in (("ptxu_Colour:m_rgbaMinKFP", "min"),
                               ("ptxu_Colour:m_rgbaMaxKFP", "max")):
            e = kfp_envelope(prb, kfpname)
            if not e:
                notes.append("alpha envelope (%s) could not be read" % label)
                bad = True
                continue
            # ⛔ The MAX envelope can be ENTIRELY ZERO and that is a VALID pattern
            #    in vanilla: measured, **87 of 1733 rules (5.0%)** are like this --
            #    including effects that work in game such as
            #    `ent_amb_tnl_bubbles_lge`. A zero max means no range, min applies.
            #    Reporting it as "invisible/no animation" is a false alarm.
            if label == "max" and max(a for _, a in e) <= 1e-6:
                continue
            if len(e) < 2:
                notes.append("NO ANIMATION (%s): alpha has a single keyframe (constant) -- "
                             "90.7%% of vanilla carry at least 2" % label)
                bad = True
            elif e[-1][1] > 0.02:
                notes.append("POP (%s): alpha %.3g at t=1 -- the particle vanishes "
                             "abruptly; 88.2%% of vanilla go down to 0"
                             % (label, e[-1][1]))
                bad = True
            tp = max(a for _, a in e)
            if tp < 0.05:
                notes.append("INVISIBLE (%s): peak alpha %.3g (vanilla p05 = 0.1)"
                             % (label, tp))
                bad = True

        # --- 5. MOTION READ BACK ----------------------------------------------
        # ⛔ "I wrote it" is not enough; READ it BACK from the file. Motion was the
        #    most expensive failure in this pipeline (inheriting the donor's
        #    motion = publishing the donor in a new colour) and can silently return.
        for key, value in (motion or {}).items():
            if key not in MOTION_FIELDS:
                continue
            g = kfp_body(s, MOTION_FIELDS[key][1])
            if g is None:
                notes.append("NO MOTION: field %s not found in the file" % key)
                bad = True
                continue
            v = re.findall(r"<(?:Red|Green|Blue)ChannelColour value=\"([-0-9.eE]+)\"", g)
            if len(v) < 3:
                notes.append("MOTION could not be read: %s" % key)
                bad = True
                continue
            read = tuple(float(x) for x in v[:3])
            if any(abs(read[i] - value[i]) > 1e-3 for i in range(3)):
                notes.append("MOTION DRIFT %s: written %s, in file %s"
                             % (key, tuple(value), read))
                bad = True
        if motion.get("remove_attractor"):
            g = kfp_body(s, "ptxAttractorDomain:m_sizeOuterKFP")
            if g and any(abs(float(x)) > 1e-6 for x in
                         re.findall(r"<(?:Red|Green|Blue)ChannelColour value=\"([-0-9.eE]+)\"", g)):
                notes.append("ATTRACTOR STILL PRESENT -- the tornado risk remains")
                bad = True

        if bad:
            violations += 1
        else:
            passed += 1
        head = "FAIL  " if bad else "pass  "
        if r and l:
            print("  %s %-18s load %6.0f   rate %.4g-%.4g /s   life %.4g-%.4g s"
                  % (head, effect, y or 0, r[0], r[1], l[0], l[1]))
        else:
            print("  %s %-18s (rate/lifetime could not be read)" % (head, effect))
        for n in notes:
            print("           - %s" % n)

    print("\npassed: %d / %d" % (passed, len(GROUPS[a.group])))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
