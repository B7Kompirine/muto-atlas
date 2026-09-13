#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_build_catalog.py — builds one effect group of the catalog and AUDITS it.

PRINCIPLE: the donor's own values are KEPT. Vanilla has already balanced that
effect; writing over it is the fastest way to produce "needlessly too much /
needlessly too little effect". Only the field where the effect really has to
differ is overridden, and the REASON for every override is written in the spec.

⛔ The donor must have a SINGLE EMITTER (that is how `ypt_transplant.py` works).
   There are 251 single-emitter effects; a multi-emitter one is rejected.
⛔ Sheet slicing does not work in a custom `.ypt` -> `UnknownC4 = 0`.
⛔ On an alpha texture an `RGB_*` technique ignores alpha -> converted to `RGBA_*`.

Usage:
  python ptfx_build_catalog.py --group virus_ambient
  python ptfx_quality_gate.py --group virus_ambient     # audit only
"""
from __future__ import annotations

import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import zlib

import ptfx_motion
import ptfx_sheet

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import tempfile  # noqa: E402
_TMP = tempfile.gettempdir()
VANILLA = os.path.join(_TMP, "vanilla_ptfx", "core.ypt.xml")
SPRITE = os.path.join(_TMP, "ptfx_sprites")
OUT_DIR = os.path.join(_TMP, "ptfx_catalog")

# ⛔ 512 IS TOO MUCH FOR A SINGLE-FRAME SPRITE. Measured: the most common
#    texture size in vanilla core.ypt is **256x256** (33 of 107 textures);
#    where it uses 512 those are 16-49 FRAME SHEETS, i.e. ~73 pixels per frame.
#    Ours were 512 although single-frame -> 71 textures = 23.7 MB,
#    `.ypt` 6.56 MB, and `RequestNamedPtfxAsset` FROZE the game
#    (`/ptfxt1` alone froze it; the effect and the tag were innocent).
RESOLUTION = 256

# old Turkish group names still accepted on the command line
GROUP_ALIASES = {
    "virus_ambiyans": "virus_ambient", "yikim": "destruction", "patlama": "explosion",
    "buyu": "magic", "radyasyon": "radiation", "virus_ek": "virus_extra",
    "elektrik": "electric", "ortak": "common", "yildirim": "lightning",
}

# effect: (donor, sprite, colour, override, reason, MOTION)
#
# ⛔ MOTION IS NOT INHERITED, IT IS WRITTEN. Leaving the donor's motion as-is
#    is nothing more than dressing that effect in a new colour, and in game
#    THE DONOR ITSELF is seen. Three measured cases are in reference §13.
#    Meanings: spawn = the volume particles spawn in (m),
#              target = direction x distance (speed), accel = gravity/rise.
GROUPS = {
 "virus_ambient": [
  ("spore_cloud", "ent_amb_dust_motes", "dust", (0.62, 0.70, 0.52), {},
   "The donor is already sparse, slowly hanging grains; exactly what a spore needs.",
   # ⚠ `ent_amb_dust_motes` has NO `ptxu_Acceleration` behaviour. For a spore
   #    accel is not critical anyway: target (0,0,0.15) gives the slow rise
   #    and the donor's hang-in-the-air behaviour is exactly what we want.
   #    Removing the key is better than asking for something it does not carry.
   {"size": (0.09, 0.09, 0.09), "shape": "Sphere", "spawn": (1.5, 1.5, 1.5), "target": (0, 0, 0.15),
    "damping": (0.4, 0.4, 0.4)}),
  ("blood_haze", "blood_mist", "blood", (0.55, 0.06, 0.05), {},
   "blood_mist is blood haze itself; rate/lifetime from the donor.",
   {"size": (0.35, 0.35, 0.35), "shape": "Sphere", "spawn": (0.3, 0.3, 0.3), "target": (0, 0, 0.25),
    "accel": (0, 0, -0.6), "damping": (0.5, 0.5, 0.5)}),
  ("decay_fluid", "ent_amb_fbi_fire_drip", "drop", (0.30, 0.26, 0.18),
   {"lifetime": 3.0, "rate": 1.5},
   "Donor is a fire drip: 3/s is too frequent. A morgue drip must be SPARSE.",
   {"size": (0.1, 0.1, 0.1), "shape": "Box", "spawn": (0.4, 0.4, 0.02), "target": (0, 0, -2.0),
    "accel": (0, 0, -9.8)}),
  ("chemical_steam", "ent_amb_dry_ice_vent", "steam", (0.92, 0.94, 0.95), {},
   "Dry ice vent; motion WRITTEN: steam rising up from a narrow mouth.",
   {"size": (0.6, 0.6, 0.6), "shape": "Cylinder", "spawn": (0.2, 0.05, 0.2), "target": (0, 0, 1.2),
    "accel": (0, 0, 0.6), "damping": (0.3, 0.3, 0.1)}),
  # ⛔ Donor `fire_extinguish` -- a FIRE EXTINGUISHER JET. Its TargetDomain
  #    aimed 3.5 m up; in game it sprayed rings. An infection wave spreads
  #    ON THE GROUND: target almost flat, attractor zero.
  ("infection_wave", "fire_extinguish", "ring_organic", (0.45, 0.72, 0.35),
   {"rate": 2.0, "lifetime": 1.2},
   "Jet motion removed; a wave spreading horizontally on the ground was written.",
   {"size": (1.3, 1.3, 1.3), "shape": "Cylinder", "spawn": (0.3, 0.05, 0.3), "target": (0, 0, 0.05),
    "target_size": (1.6, 0.05, 1.6), "accel": (0, 0, 0),
    "damping": (0.8, 0.8, 0.9), "remove_attractor": True}),
  ("ground_fog", "ent_amb_dry_ice_area", "fog", (0.72, 0.74, 0.76),
   {"rate": 6.0, "lifetime": 8.0},
   "Ground fog is continuous and STILL: wide flat volume, almost zero speed.",
   {"size": (1.6, 1.6, 1.6), "shape": "Box", "spawn": (3.0, 3.0, 0.05), "target": (0, 0.2, 0.02),
    "accel": (0, 0, 0), "damping": (0.9, 0.9, 0.95)}),
  ("dust_motes", "ent_amb_dust_motes", "dust", (0.80, 0.78, 0.72),
   {"rate": 5.0},
   "Motes in a light beam: almost motionless inside a vertical column.",
   {"size": (0.05, 0.05, 0.05), "shape": "Box", "spawn": (1.5, 1.5, 2.0), "target": (0.1, 0, 0.05),
    "damping": (0.9, 0.9, 0.9)}),
  ("ceiling_drip", "ent_amb_water_roof_drips", "drop", (0.70, 0.78, 0.84),
   {"rate": 2.5},
   "Single drops from the ceiling: wide flat spawn, straight down, gravity.",
   {"size": (0.09, 0.09, 0.09), "shape": "Box", "spawn": (1.5, 1.5, 0.02), "target": (0, 0, -3.0),
    "accel": (0, 0, -15.0)}),
  ("steam_stack", "ent_amb_steam_prison", "steam", (0.90, 0.92, 0.94), {},
   "Stack: narrow mouth, strong vertical exit.",
   {"size": (0.7, 0.7, 0.7), "shape": "Cylinder", "spawn": (0.25, 0.05, 0.25), "target": (0, 0, 2.5),
    "accel": (0, 0, 1.2), "damping": (0.2, 0.2, 0.05)}),
  # ⛔ `ent_amb_falling_leaves_*` CANNOT BE USED: in GTA a leaf is a MESH, not a
  #    SPRITE; it has no texture and the transplant fails.
  ("paper_scatter", "ent_amb_falling_cherry_bloss", "paper", (0.86, 0.84, 0.78),
   {"rate": 6.0},
   "Scattering paper: spawns in a wide volume, drifts sideways, falls slowly.",
   {"size": (0.22, 0.22, 0.22), "shape": "Box", "spawn": (3.0, 3.0, 2.0), "target": (1.5, 0.5, -0.3),
    "accel": (0.2, 0.1, -0.8), "damping": (0.7, 0.7, 0.8)}),
  ("floating_embers", "ent_amb_fbi_cinder", "ember", (1.00, 0.58, 0.16), {},
   "Floating embers: drift up from a narrow source, sway slightly.",
   {"size": (0.06, 0.06, 0.06), "shape": "Cylinder", "spawn": (0.3, 0.1, 0.3), "target": (0, 0, 0.8),
    "accel": (0.15, 0.1, 0.25)}),
 ],

 # ⛔ NONE of the 18 references the catalog listed for destruction could be
 #    used: all are multi-emitter. An impact effect is by nature dust +
 #    splinters + puff. 231 single-emitter donors were taken as a SKELETON,
 #    the MOTION was written from the family's own physics.
 "destruction": [
  ("wall_collapse", "ent_amb_fbi_smoke_land_hvy", "smoke", (0.42, 0.39, 0.35), {},
   "A dust curtain spawning along the wall surface, billowing slowly.",
   {"size": (1.8, 1.8, 1.8), "shape": "Box", "spawn": (3.0, 0.3, 2.0), "target": (0, 0, 0.5),
    "accel": (0, 0, 0.15), "damping": (0.7, 0.7, 0.8)}),
  # ⛔ The donor's spawn volume was a 5x5x1 m BOX -- splinters spawned scattered
  #    over a 5 metre area, not from the impact point. Changed to a small sphere.
  ("concrete_break", "ent_ray_fam3_dust_motes", "concrete", (0.58, 0.57, 0.55),
   {"lifetime": 1.2},
   "Splinters bursting from the impact POINT; heavy, fall fast.",
   {"size": (0.16, 0.16, 0.16), "shape": "Sphere", "spawn": (0.15, 0.15, 0.15), "target": (0, 0, 1.2),
    "accel": (0, 0, -14.0), "damping": (0.2, 0.2, 0.1)}),
  ("wood_break", "ent_ray_fam3_dust_motes", "wood", (0.55, 0.38, 0.20),
   {"lifetime": 1.6},
   "Wood splinters are lighter than concrete: fly further, fall slower.",
   {"size": (0.2, 0.2, 0.2), "shape": "Sphere", "spawn": (0.2, 0.2, 0.2), "target": (0, 0, 1.5),
    "accel": (0, 0, -9.0), "damping": (0.35, 0.35, 0.25)}),
  ("glass_break", "ent_amb_falling_cherry_bloss", "glass", (0.82, 0.90, 0.94),
   {"lifetime": 1.4, "rate": 10.0},
   "Glass pouring from the window PLANE; heaviest fall, short distance.",
   {"size": (0.13, 0.13, 0.13), "shape": "Box", "spawn": (1.0, 0.05, 1.0), "target": (0, 0, -2.0),
    "accel": (0, 0, -18.0), "damping": (0.1, 0.1, 0.05)}),
  ("metal_tear", "ent_amb_fbi_cinder", "spark", (1.00, 0.78, 0.42),
   {"lifetime": 0.9},
   "Sparks shooting from the tear point, falling in an arc.",
   {"size": (0.09, 0.09, 0.09), "shape": "Sphere", "spawn": (0.1, 0.1, 0.1), "target": (0, 0, 0.6),
    "accel": (0, 0, -6.0)}),
  ("plaster_fall", "ent_amb_fbi_smoke_creep", "dust", (0.90, 0.89, 0.86), {},
   "Fine plaster dust drifting from the ceiling: light, comes down slowly.",
   {"size": (0.35, 0.35, 0.35), "shape": "Box", "spawn": (1.0, 1.0, 0.05), "target": (0, 0, -1.5),
    "accel": (0, 0, -6.0), "damping": (0.6, 0.6, 0.7)}),
  ("rubble_rain", "ent_amb_falling_cherry_bloss", "concrete", (0.48, 0.44, 0.40),
   {"rate": 4.0},
   "Debris falling from the ceiling area: wide flat spawn, long fall.",
   {"size": (0.26, 0.26, 0.26), "shape": "Box", "spawn": (4.0, 4.0, 0.2), "target": (0, 0, -8.0),
    "accel": (0, 0, -16.0), "damping": (0.15, 0.15, 0.1)}),
  # ⛔ Donor `env_dust_devil_rural_lrg` -- a DUST DEVIL. Its `ptxAttractorDomain`
  #    (outer 20.6 / inner 6.8) spiralled particles inward and up; in game a
  #    TORNADO was seen. The attractor is zeroed, the target laid flat on the ground.
  ("collapse_dust", "env_dust_devil_rural_lrg", "smoke", (0.66, 0.60, 0.50), {},
   "Tornado removed; a heavy dust wall spreading FORWARD from the ground was written.",
   {"size": (2.6, 2.6, 2.6), "shape": "Cylinder", "spawn": (2.0, 0.3, 2.0), "target": (0, 0, 0.4),
    "target_size": (4.0, 0.3, 4.0), "accel": (0, 0, 0.05),
    "damping": (0.85, 0.85, 0.9), "remove_attractor": True}),
  ("friction_sparks", "ent_amb_fbi_cinder", "spark", (1.00, 0.86, 0.55),
   {"rate": 14.0, "lifetime": 0.55},
   "Same donor as metal_tear but a different DIRECTION: friction sparks flow "
   "one way (target x=1.5), tearing scatters.",
   {"size": (0.07, 0.07, 0.07), "shape": "Sphere", "spawn": (0.06, 0.06, 0.06), "target": (1.5, 0, 0.3),
    "accel": (0, 0, -8.0)}),
 ],
 # ⛔ All `exp_*` explosion effects are MULTI-EMITTER (core + ring + smoke
 #    + debris). A WHOLE explosion cannot be made with one emitter; each
 #    effect represents the MOST READABLE part of the explosion. The skeleton
 #    was chosen by life band, the motion was written.
 "explosion": [
  ("grenade", "weap_veh_turbulance_dirt", "fireball", (1.00, 0.72, 0.30), {},
   "A core bursting outward from a point; very short-lived skeleton (0.2-0.4 s).",
   {"size": (1.2, 1.2, 1.2), "shape": "Sphere", "spawn": (0.2, 0.2, 0.2), "target": (0, 0, 2.5),
    "accel": (0, 0, 1.5), "damping": (0.6, 0.6, 0.6)}),
  ("rocket", "liquid_splash_water", "fireball", (1.00, 0.66, 0.24),
   {"rate": 5.0},
   "An RPG IS DIRECTIONAL: target 3 m on the x axis -- the core stretches forward. "
   "Skeleton `liquid_splash_water`: NOT the petrol twin -- petrol needs TWO "
   "textures (`ptfx_gloop_n` normal map + `ptfx_gloop` colour) and when the "
   "single sprite is written into both the shader lights it wrong. "
   "Rate kept at petrol's value of 5/s.",
   {"size": (0.9, 0.9, 0.9), "shape": "Sphere", "spawn": (0.15, 0.15, 0.15), "target": (3.0, 0, 0.4),
    "accel": (0, 0, -1.0), "damping": (0.5, 0.5, 0.5)}),
  ("fuel_barrel", "bang_plastic", "fire", (1.00, 0.52, 0.14), {"rate": 30.0},
   "Barrel: not a core but a CONTINUOUS fire. Wide mouth, strong rise.",
   {"size": (1.6, 1.6, 1.6), "shape": "Cylinder", "spawn": (0.6, 0.1, 0.6), "target": (0, 0, 3.0),
    "accel": (0, 0, 2.2), "damping": (0.4, 0.4, 0.3)}),
  ("vehicle_explosion", "weap_veh_turbulance_dirt", "concrete", (0.45, 0.42, 0.40),
   {"lifetime": 1.6},
   "A vehicle explosion is FRAGMENTS: metal/glass flies, falls in an arc.",
   {"size": (0.24, 0.24, 0.24), "shape": "Sphere", "spawn": (0.5, 0.5, 0.5), "target": (0, 0, 4.0),
    "accel": (0, 0, -8.0), "damping": (0.3, 0.3, 0.2)}),
  ("molotov", "bang_plastic", "fire", (1.00, 0.60, 0.18), {"rate": 22.0},
   "A molotov does not explode, it SPREADS: wide flat ground area, low rise.",
   {"size": (1.1, 1.1, 1.1), "shape": "Cylinder", "spawn": (1.5, 0.1, 1.5), "target": (0, 0, 0.8),
    "accel": (0, 0, 1.0), "damping": (0.7, 0.7, 0.6)}),
  ("shock_wave", "liquid_splash_water", "ring_arc", (0.96, 0.97, 1.00),
   {"rate": 12.0},
   "Flashbang is FIRELESS: a white ring expanding fast on the ground. target_size "
   "wide, target almost flat.",
   {"size": (1.4, 1.4, 1.4), "shape": "Cylinder", "spawn": (0.2, 0.05, 0.2), "target": (0, 0, 0.05),
    "target_size": (5.0, 0.05, 5.0), "accel": (0, 0, 0),
    "damping": (0.9, 0.9, 0.9)}),
  ("air_burst", "ent_amb_fbi_smoke_linger_lt", "smoke", (0.34, 0.32, 0.30),
   {},
   "Explosion in the air: no ground contact, smoke hangs DOWN (target z negative).",
   {"size": (1.6, 1.6, 1.6), "shape": "Sphere", "spawn": (1.0, 1.0, 1.0), "target": (0, 0, -0.6),
    "accel": (0, 0, -0.3), "damping": (0.8, 0.8, 0.85)}),
  ("water_explosion", "ent_amb_bubble_stream", "bubble", (0.78, 0.88, 0.94),
   {"rate": 40.0, "lifetime": 2.5},
   "Underwater: a bubble dome rises towards the surface as a column.",
   {"size": (0.45, 0.45, 0.45), "shape": "Sphere", "spawn": (0.8, 0.8, 0.4), "target": (0, 0, 3.0),
    "accel": (0, 0, 1.8), "damping": (0.5, 0.5, 0.4)}),
 ],

 # ⛔ `shield_dome` IS NOT IN THIS PACK. In the catalog's own words
 #    "more a surface effect than a particle -- needs a mesh + shader". A particle
 #    imitation gives a bad dome; the right way is a separate mesh.
 "magic": [
  ("magic_gather", "ent_amb_elec_crackle", "flare", (0.55, 0.72, 1.00),
   {"rate": 25.0},
   "INWARD FLOW: spawns in a wide volume, target_size is SMALL so all head "
   "to one point -- that is how the gathering feel is built.",
   {"size": (0.35, 0.35, 0.35), "shape": "Sphere", "spawn": (1.2, 1.2, 1.2), "target": (0, 0, 0),
    "target_size": (0.05, 0.05, 0.05)}),
   # ⚠ `ent_amb_elec_crackle` has NO Acceleration/Dampening/Rotation.
   #    An electric/energy flash does not fly anyway, it glows in place.
  ("rune_circle", "ent_amb_fbi_smoke_linger_lt", "neutral_ring", (0.70, 0.55, 1.00),
   {"rate": 4.0, "lifetime": 3.0},
   "A circle lying on the ground: flat cylinder, almost zero speed, high damping.",
   {"size": (1.6, 1.6, 1.6), "shape": "Cylinder", "spawn": (1.5, 0.02, 1.5), "target": (0, 0, 0.02),
    "accel": (0, 0, 0), "damping": (0.95, 0.95, 0.95)}),
  ("magic_bolt", "liquid_splash_water", "neutral_ember", (0.60, 0.80, 1.00),
   {"rate": 35.0},  # NO lifetime override: the donor is already 0.4-0.5 (avg 0.45)
   "The bolt's TRAIL: very short life + narrow spawn = a line left behind.",
   {"size": (0.12, 0.12, 0.12), "shape": "Sphere", "spawn": (0.08, 0.08, 0.08), "target": (0, 0, 0.1),
    "accel": (0, 0, 0), "damping": (0.8, 0.8, 0.8)}),
  ("magic_impact", "weap_veh_turbulance_dirt", "star", (0.72, 0.62, 1.00),
   {},
   "Moment of impact: a flare bursting up from a point, then scattering.",
   {"size": (0.9, 0.9, 0.9), "shape": "Sphere", "spawn": (0.15, 0.15, 0.15), "target": (0, 0, 1.8),
    "accel": (0, 0, -2.0), "damping": (0.6, 0.6, 0.6)}),
  ("healing_aura", "ent_amb_bubble_stream", "flare", (0.65, 1.00, 0.85),
   {"rate": 9.0},
   "UPWARD flow wrapping the character: vertical cylinder, gentle speed.",
   {"size": (0.3, 0.3, 0.3), "shape": "Cylinder", "spawn": (0.6, 1.0, 0.6), "target": (0, 0, 1.5),
    "accel": (0, 0, 0.4), "damping": (0.6, 0.6, 0.5)}),
  ("teleport", "liquid_splash_water", "flare", (0.85, 0.75, 1.00),
   {"rate": 60.0},
   "Same inward-collapse mechanic as magic_gather but MUCH faster and wider "
   "-- the moment of vanishing.",
   {"size": (0.55, 0.55, 0.55), "shape": "Sphere", "spawn": (1.5, 1.5, 1.5), "target": (0, 0, 0),
    "target_size": (0.03, 0.03, 0.03), "accel": (0, 0, 0),
    "damping": (0.3, 0.3, 0.3)}),
  ("curse_fog", "ent_amb_fbi_smoke_linger_lt", "fog", (0.32, 0.20, 0.40),
   {"rate": 5.0},
   "Dark heavy fog wrapping the character: narrow vertical cylinder, almost still.",
   {"size": (1.1, 1.1, 1.1), "shape": "Cylinder", "spawn": (0.8, 1.2, 0.8), "target": (0, 0, 0.1),
    "accel": (0, 0, 0), "damping": (0.9, 0.9, 0.92)}),
 ],

 "radiation": [
  ("radioactive_fog", "_fog_foundry", "fog", (0.55, 0.72, 0.45), {"rate": 5.0},
   "Heavy air settling on the ground: wide flat box, almost zero speed.",
   {"size": (1.8, 1.8, 1.8), "shape": "Box", "spawn": (4.0, 4.0, 0.15), "target": (0, 0.2, 0.02),
    "accel": (0, 0, 0), "damping": (0.95, 0.95, 0.95)}),
  ("barrel_leak", "liquid_splash_water", "drop", (0.62, 0.78, 0.30),
   {"rate": 3.0},
   "Liquid flowing from a tipped barrel: narrow mouth, straight down, gravity.",
   {"size": (0.1, 0.1, 0.1), "shape": "Box", "spawn": (0.15, 0.15, 0.02), "target": (0, 0, -0.8),
    "accel": (0, 0, -9.8), "damping": (0.2, 0.2, 0.1)}),
  ("hot_spot", "ent_amb_elec_crackle", "star", (0.75, 1.00, 0.45), {},
   "INTERMITTENT flare: the skeleton's own rate range 0.1-15 is already irregular -- "
   "that gives the intermittency matching the counter sound, rate NOT overridden.",
   {"size": (0.1, 0.1, 0.1), "shape": "Sphere", "spawn": (0.1, 0.1, 0.1), "target": (0, 0, 0.2)}),
  ("fallout", "ent_amb_falling_cherry_bloss", "ash", (0.62, 0.60, 0.58),
   {"rate": 8.0},
   "Ash fall: VERY wide area, slow descent, slight sideways drift.",
   {"size": (0.07, 0.07, 0.07), "shape": "Box", "spawn": (8.0, 8.0, 0.3), "target": (0.3, 0.2, -2.0),
    "accel": (0, 0, -0.4), "damping": (0.85, 0.85, 0.9)}),
  ("cherenkov", "ent_amb_tnl_bubbles_lge", "flare", (0.30, 0.70, 1.00),
   {"rate": 6.0},
   "Underwater blue glow: still, wide, rising very slowly.",
   {"size": (0.5, 0.5, 0.5), "shape": "Sphere", "spawn": (1.0, 1.0, 1.0), "target": (0, 0, 0.4),
    "accel": (0, 0, 0.1), "damping": (0.9, 0.9, 0.9)}),
  ("contaminated_trail", "liquid_splash_water", "dust", (0.60, 0.75, 0.42),
   {"rate": 8.0},
   "Footprint dust: small, short-lived, almost motionless.",
   {"size": (0.14, 0.14, 0.14), "shape": "Sphere", "spawn": (0.12, 0.12, 0.12), "target": (0, 0, 0.15),
    "accel": (0, 0, 0), "damping": (0.9, 0.9, 0.9)}),
 ],

 # ⛔ `heat_haze` IS NOT IN THIS PACK: the catalog says "not a particle but a
 #    REFRACTION shader" and vanilla `ptfx_heathaze_n` is a normal-map texture.
 #    An imitation with our own sprite gives a blurry smudge.
 # ⛔ The REAL job of `stain_spread` is a DECAL; here there is only the thin
 #    steam above it. The decal is built in a separate pipeline.
 "virus_extra": [
  ("fly_cloud", "ent_amb_fly_swarm", "fly", (0.55, 0.52, 0.46),
   {"rate": 12.0, "lifetime": 5.0},
   "Small dark grains circling around a corpse. The skeleton already behaves "
   "like a fly swarm; the spawn volume was shrunk to just wrap the corpse.",
   {"size": (0.05, 0.05, 0.05), "shape": "Sphere", # ⚠ Acceleration here is the `m_strengthKFP` (scalar) variant; xyz
    #    cannot be written. Dampening exists, that is written.
    "spawn": (0.5, 0.5, 0.4), "target": (0, 0, 0.05),
    "damping": (0.6, 0.6, 0.6)}),
  ("stain_spread", "ent_amb_exhaust_thin", "steam", (0.50, 0.55, 0.42),
   {"rate": 1.5, "lifetime": 6.0},
   "VERY thin steam rising from the stain on the ground; the stain is a decal.",
   {"size": (0.4, 0.4, 0.4), "shape": "Box", "spawn": (0.8, 0.8, 0.02), "target": (0, 0, 0.15),
    "accel": (0, 0, 0), "damping": (0.95, 0.95, 0.95)}),
  ("insect_swarm", "ent_amb_moths_swarm", "fly", (0.62, 0.56, 0.48),
   {"rate": 10.0},
   "A cloud circling under a lamp / in rubbish; wider and sparser than fly_cloud.",
   {"size": (0.06, 0.06, 0.06), "shape": "Sphere", "spawn": (0.7, 0.7, 0.6), "target": (0, 0, 0.1),
    "accel": (0, 0, 0), "damping": (0.6, 0.6, 0.6)}),
 ],

 "electric": [
  ("straight_arc", "ent_amb_elec_crackle", "arc_straight", (0.70, 0.85, 1.00), {},
   "A short line between two points: very narrow spawn, the skeleton's irregular rate "
   "already gives the flicker.",
   {"size": (0.55, 0.55, 0.55), "shape": "Sphere", "spawn": (0.05, 0.05, 0.05), "target": (0, 0, 0.1)}),
  ("forked_lightning", "ent_amb_fbi_live_wires", "electric",
   (0.75, 0.82, 1.00), {"rate": 8.0},
   "The difference from the straight arc is COVERAGE: spawn volume 6 times wider, "
   "that is how the branching feel is built.",
   {"size": (0.9, 0.9, 0.9), "shape": "Sphere", "spawn": (0.3, 0.3, 0.3), "target": (0, 0, 0.3)}),
  ("arc_impact", "bul_stungun", "star", (0.92, 0.96, 1.00),
   {"rate": 20.0, "lifetime": 0.5},
   "The moment the arc hits the target: sharp white flare, fades fast.",
   {"size": (0.6, 0.6, 0.6), "shape": "Sphere", "spawn": (0.12, 0.12, 0.12), "target": (0, 0, 0.8),
    "accel": (0, 0, -3.0), "damping": (0.5, 0.5, 0.5)}),
  ("spark_shower", "liquid_splash_water", "spark", (1.00, 0.80, 0.40),
   {"rate": 18.0, "lifetime": 1.0},
   "Sparks POURING from a broken cable: flat spawn, strong gravity.",
   {"size": (0.08, 0.08, 0.08), "shape": "Box", "spawn": (0.4, 0.4, 0.05), "target": (0, 0, -2.5),
    "accel": (0, 0, -12.0), "damping": (0.25, 0.25, 0.15)}),
  ("short_circuit", "ent_amb_elec_crackle", "electric", (0.65, 0.78, 1.00),
   {"rate": 6.0},
   "Panel short circuit: wider than the straight arc, narrower than forked lightning; "
   "intermittent.",
   {"size": (0.45, 0.45, 0.45), "shape": "Sphere", "spawn": (0.15, 0.15, 0.15), "target": (0, 0, 0.25)}),
  ("emp_wave", "liquid_splash_water", "ring_arc", (0.40, 0.70, 1.00),
   {"rate": 15.0},
   "A fast expanding blue ring: same mechanic as shock_wave, wider "
   "target_size (6 m) and blue.",
   {"size": (1.6, 1.6, 1.6), "shape": "Cylinder", "spawn": (0.15, 0.05, 0.15), "target": (0, 0, 0.03),
    "target_size": (6.0, 0.05, 6.0), "accel": (0, 0, 0),
    "damping": (0.9, 0.9, 0.9)}),
  ("tesla_dome", "ent_amb_elec_crackle", "electric", (0.60, 0.80, 1.00),
   {"rate": 20.0},
   "Arcs jumping from the centre OUTWARD: narrow spawn but WIDE target_size -- "
   "every particle goes a different way.",
   {"size": (0.7, 0.7, 0.7), "shape": "Sphere", "spawn": (0.1, 0.1, 0.1), "target": (0, 0, 0.6),
    "target_size": (1.5, 1.5, 1.5)}),
 ],

 "common": [
  ("impact_dust", "weap_veh_turbulance_dirt", "dust", (0.68, 0.64, 0.58),
   {"lifetime": 0.9},
   "Anything hitting a surface: puffs up from a point and settles.",
   {"size": (0.55, 0.55, 0.55), "shape": "Sphere", "spawn": (0.2, 0.2, 0.2), "target": (0, 0, 1.0),
    "accel": (0, 0, -3.0), "damping": (0.6, 0.6, 0.6)}),
  ("footstep_dust", "liquid_splash_water", "dust", (0.72, 0.68, 0.62),
   {"rate": 4.0},
   "⚠ Footstep dust must be WEAK; otherwise the ped emits smoke. Rate and target "
   "deliberately low.",
   {"size": (0.3, 0.3, 0.3), "shape": "Sphere", "spawn": (0.15, 0.15, 0.1), "target": (0, 0, 0.35),
    "accel": (0, 0, -1.0), "damping": (0.8, 0.8, 0.8)}),
  ("water_splash", "ent_amb_drain_splash", "splash", (0.80, 0.88, 0.92),
   {"rate": 25.0},
   "Crown-shaped splash: up from a narrow ring mouth, then falls back "
   "with gravity.",
   {"size": (0.3, 0.3, 0.3), "shape": "Cylinder", "spawn": (0.25, 0.05, 0.25), "target": (0, 0, 1.6),
    "accel": (0, 0, -12.0), "damping": (0.3, 0.3, 0.2)}),
  ("muzzle_flash", "weap_veh_turbulance_dirt", "fire", (1.00, 0.82, 0.45),
   {"rate": 40.0},
   "A muzzle flash is VERY short and DIRECTIONAL: target on the x axis, very narrow spawn.",
   {"size": (0.3, 0.3, 0.3), "shape": "Sphere", "spawn": (0.06, 0.06, 0.06), "target": (0.8, 0, 0),
    "accel": (0, 0, 0), "damping": (0.5, 0.5, 0.5)}),
  ("exhaust_smoke", "ent_amb_exhaust_thin", "smoke", (0.55, 0.55, 0.56), {},
   "Continuous thin exhaust: narrow mouth, slight rise.",
   {"size": (0.45, 0.45, 0.45), "shape": "Cylinder", "spawn": (0.1, 0.05, 0.1), "target": (0, 0, 0.6),
    "accel": (0, 0, 0.25), "damping": (0.7, 0.7, 0.7)}),
 ],

 # ⛔ LIGHTNING SPELL -- a single three-stage scenario (cast / contact / final action).
 #    The "travel from the aim point to the target" part is NOT A PARTICLE: a
 #    particle spawns at a single point. The travelling arc is drawn with short-lived
 #    segments scattered one after another along the ray (script side). That is why
 #    `lightning_branch` lives 0.10-0.16 s -- it flashes and fades where it is scattered.
 "lightning": [
  ("lightning_branch", "ent_amb_elec_crackle", "electric", (0.62, 0.80, 1.00),
   {"rate": 90.0, "lifetime": 0.13},
   "A forked arc segment scattered along the ray. VERY short-lived: the segment "
   "must flash and fade, otherwise a permanent line stays along the ray. The donor's "
   "irregular rate (0.1-15) already gives the flash feel.",
   {"shape": "Sphere", "size": (1.15, 1.15, 1.15), "spawn": (0.18, 0.18, 0.18),
    "target": (0, 0, 0.05), "one_shot": True,
    "envelope": [(0.0, 0.9), (0.4, 1.0), (1.0, 0.0)]}),

  ("lightning_flash", "bul_stungun", "star", (0.88, 0.94, 1.00),
   {"rate": 120.0, "lifetime": 0.28},
   "The white flash at the moment of impact. Short and bright; it ends BEFORE the "
   "sparks so the eye reads the hit first, then the scatter.",
   {"shape": "Sphere", "size": (1.30, 1.30, 1.30), "spawn": (0.10, 0.10, 0.10),
    "target": (0, 0, 0.25), "accel": (0, 0, -1.0), "damping": (0.6, 0.6, 0.6),
    "one_shot": True, "envelope": [(0.0, 1.0), (0.25, 1.0), (1.0, 0.0)]}),

  # ⛔ Donor `water_splash_veh_out`: life 1.1-1.6 s and ALL FOUR of the
  #    Acceleration + Dampening + Rotation + Size behaviours are present. With
  #    short-lived spark donors (0.2-0.4 s) the spark gets no chance to draw an
  #    arc in the air.
  ("lightning_sparks", "water_splash_veh_out", "spark", (1.00, 0.82, 0.45),
   {"rate": 260.0, "lifetime": 1.45},
   "Sparks scattering OUTWARD from the impact point and coming down with gravity. "
   "`target_size` wide -> every particle flies a different way; `accel` -9 -> falls "
   "in an arc; damping low -> keeps its speed.",
   # ⚠ The first values were TOO SLOW: target 1.1 m / 1.45 s = 0.76 m/s, sideways
   #   +-1.1 m/s. The sparks could not arc in the air, they clustered at the impact point.
   #   Real sparks fly at 5-15 m/s; target and target_size were enlarged.
   {"shape": "Sphere", "size": (0.075, 0.075, 0.075), "spawn": (0.10, 0.10, 0.10),
    # ⚠ A 14 m spread threw the sparks 7 m away and they left the frame
    #   completely. Impact sparks must stay within 2-3 m.
    "target": (0, 0, 2.2), "target_size": (6.5, 6.5, 3.5),
    # ⚠ With gravity -9 they fell 9 m in 1.45 s (far below the ground).
    #   With -4.5 ~2.7 m -- a reasonable arc from impact height to the ground.
    "accel": (0, 0, -4.5), "damping": (0.18, 0.18, 0.12), "one_shot": True,
    # the spark stays BRIGHT for most of its life, fades at the end
    "envelope": [(0.0, 1.0), (0.55, 0.95), (0.85, 0.55), (1.0, 0.0)]}),
 ],
}


def ps(*args):
    return subprocess.run(list(args), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


# ⛔ ANIMATION ENVELOPE REPAIR -- if this step is skipped the particle looks "pasted on".
#
# Because sheet slicing does not work in a custom `.ypt` (reference §1e) we use
# a single-frame sprite. Some vanilla donors took their motion FROM THE
# TEXTURE: `ent_amb_dry_ice_vent` has a single-keyframe alpha envelope (constant
# 0.5) but its texture is `ptfx_smoke_wispy_anim`, an animated sheet. Replacing
# the texture with a static one leaves NOTHING changing in that effect -- the
# particle appears at full alpha and disappears at full alpha.
#
# Measured: of 231 suitable donors 20 have constant alpha, 14 end by "popping"
# with alpha>0 at the end -- 14.7% in total. **88.2%** of vanilla particle
# rules bring alpha down to 0 at t=1; that is the criterion.
#
# The `KeyFrameMultiplier` field was measured: `1 / (t[i] - t[i-1])`, 0 on the first keyframe.
KFP_ENVELOPE = ("ptxu_Colour:m_rgbaMinKFP", "ptxu_Colour:m_rgbaMaxKFP")


def _keyframe(t, mult, r, g, b, al):
    return ("       <Item>\n"
            "        <InterpolationInterval value=\"%g\" />\n"
            "        <KeyFrameMultiplier value=\"%g\" />\n"
            "        <RedChannelColour value=\"%g\" />\n"
            "        <GreenChannelColour value=\"%g\" />\n"
            "        <BlueChannelColour value=\"%g\" />\n"
            "        <AlphaChannelColour value=\"%g\" />\n"
            "       </Item>\n" % (t, mult, r, g, b, al))


def repair_envelope(s):
    """Rewrites a broken alpha envelope in vanilla shape. (text, notes)"""
    notes = []

    def fix(m):
        head, body, tail = m.group(1), m.group(2), m.group(3)
        kf = re.findall(
            r"<InterpolationInterval value=\"([-0-9.eE]+)\" />\s*"
            r"<KeyFrameMultiplier value=\"[-0-9.eE]+\" />\s*"
            r"<RedChannelColour value=\"([-0-9.eE]+)\" />\s*"
            r"<GreenChannelColour value=\"([-0-9.eE]+)\" />\s*"
            r"<BlueChannelColour value=\"([-0-9.eE]+)\" />\s*"
            r"<AlphaChannelColour value=\"([-0-9.eE]+)\" />", body)
        if not kf:
            return m.group(0)
        alpha = [float(x[4]) for x in kf]
        peak = max(alpha)
        broken = len(kf) < 2 or alpha[-1] > 0.02
        if not broken or peak <= 0:
            return m.group(0)
        r, g, b = (float(kf[0][1]), float(kf[0][2]), float(kf[0][3]))
        # ⚠ Keep the donor's INSTANT APPEARANCE choice: only 44.7% of vanilla
        #   start alpha from 0; a spark/ember must appear instantly. Only the
        #   pop at the end is removed.
        if alpha[0] <= 0.02:
            points = [(0.0, 0.0), (0.1, peak), (0.8, peak), (1.0, 0.0)]
        else:
            points = [(0.0, peak), (0.75, peak), (1.0, 0.0)]
        new = ""
        for i, (t, al) in enumerate(points):
            mult = 0.0 if i == 0 else 1.0 / (t - points[i - 1][0])
            new += _keyframe(t, mult, r, g, b, al)
        notes.append("envelope repaired: %d keyframes -> %d, peak %.3g"
                     % (len(kf), len(points), peak))
        return head + "\n" + new + "      " + tail

    for name in KFP_ENVELOPE:
        s = re.sub(r"(<Name>%s</Name>.*?<Keyframes>)(.*?)(</Keyframes>)"
                   % re.escape(name), fix, s, count=1, flags=re.S)
    return s, notes


def build(effect, donor, sprite, color, ovr, reason, motion, folder):
    name = "my_" + effect
    # ⛔ DO NOT SHARE THE SPRITE -- EVERY EFFECT GETS ITS OWN SEED.
    #    The previous version copied `my_<sprite>.dds`: `smoke`,
    #    `collapse_dust`, `wall_collapse`, `exhaust_smoke`, `air_burst`
    #    came out PIXEL FOR PIXEL identical. Calling the same generator with a
    #    different seed and a different life moment (`t`) keeps the MATERIAL
    #    and separates the pattern: smoke stays smoke but no two puffs are the same.
    # ⛔ KENNEY CC0 TEXTURES HAVE THE HIGHEST PRIORITY. The industry's own advice
    #    (realtimevfx.com): READY-MADE PACK first, then photo-bashing, procedural
    #    last. Kenney is greyscale + transparent + one object per sprite --
    #    it satisfies all three of the three rules we measured.
    #    Licence CC0: commercial use allowed, attribution not required.
    KENNEY = {
        'air_burst': 'blackSmoke14',
        'arc_impact': 'star_07',
        'barrel_leak': 'scorch_01',
        'blood_haze': 'scorch_02',
        'ceiling_drip': 'circle_05',
        'chemical_steam': 'whitePuff12',
        'cherenkov': 'light_03',
        'collapse_dust': 'blackSmoke20',
        'contaminated_trail': 'smoke_02',
        'curse_fog': 'blackSmoke04',
        'decay_fluid': 'scorch_03',
        'dust_motes': 'whitePuff02',
        'emp_wave': 'circle_03',
        'exhaust_smoke': 'smoke_04',
        'fallout': 'dirt_03',
        'floating_embers': 'star_04',
        'fly_cloud': 'dirt_01',
        'footstep_dust': 'whitePuff01',
        'forked_lightning': 'spark_02',
        'friction_sparks': 'spark_07',
        'fuel_barrel': 'fire_01',
        'grenade': 'explosion04',
        'ground_fog': 'smoke_09',
        'healing_aura': 'light_02',
        'hot_spot': 'star_06',
        'impact_dust': 'whitePuff15',
        'infection_wave': 'twirl_02',
        'insect_swarm': 'dirt_02',
        'lightning_branch': 'spark_02',
        'lightning_flash': 'star_08',
        'lightning_sparks': 'spark_07',
        'magic_bolt': 'trace_04',
        'magic_gather': 'magic_02',
        'magic_impact': 'star_08',
        'metal_tear': 'spark_01',
        'molotov': 'flame_04',
        'muzzle_flash': 'muzzle_01',
        'paper_scatter': 'scratch_01',
        'plaster_fall': 'whitePuff03',
        'radioactive_fog': 'smoke_10',
        'rocket': 'muzzle_03',
        'rune_circle': 'magic_03',
        'shock_wave': 'circle_02',
        'short_circuit': 'spark_03',
        'spark_shower': 'spark_06',
        'spore_cloud': 'whitePuff05',
        'stain_spread': 'whitePuff08',
        'steam_stack': 'whitePuff18',
        'straight_arc': 'spark_05',
        'teleport': 'flash04',
        'tesla_dome': 'spark_04',
        'vehicle_explosion': 'explosion07',
        'wall_collapse': 'blackSmoke09',
        'water_explosion': 'whitePuff21',
        'water_splash': 'whitePuff23',
    }
    if effect in KENNEY:
        png = os.path.join(folder, name + ".png")
        dds = os.path.join(folder, name + ".dds")
        rk = ps(sys.executable, os.path.join(SCRIPT_DIR, "ptfx_kenney.py"),
                "--name", KENNEY[effect], "--out", png, "--resolution", str(RESOLUTION))
        if os.path.exists(png):
            ps(sys.executable, os.path.join(SCRIPT_DIR, "make_dds.py"), dds,
               "--source", png, "--format", "DXT5")
            if os.path.exists(dds):
                return _build_rest(effect, donor, color, ovr, reason, motion, folder, name)
        return "Kenney texture could not be fetched: %s" % (rk.stdout + rk.stderr).strip()[-160:]

    # BLENDER ENERGY/LIQUID: flares and liquids also come from a render.
    #    ⛔ What reads in energy is NOT GEOMETRY BUT LIGHT: emissive + bloom.
    #       In a liquid, surface tension is built with metaballs. With numpy both
    #       looked like a "drawn smudge".
    ENERGY_KINDS = {
        "ring": "ring", "neutral_ring": "ring", "ring_organic": "ring",
        "ring_arc": "emp", "star": "star", "flare": "sphere",
        "ember": "sphere", "arc_straight": "arc", "electric": "arc",
        "drop": "drop", "splash": "splash", "bubble": "crown",
        "blood": "blood", "fireball": "sphere",
    }
    if sprite in ENERGY_KINDS:
        png = os.path.join(folder, name + ".png")
        dds = os.path.join(folder, name + ".dds")
        blender_seed = zlib.crc32(effect.encode("utf-8")) % 9973
        rb = ps(sys.executable, os.path.join(SCRIPT_DIR, "ptfx_blender_energy.py"),
                "--kind", ENERGY_KINDS[sprite], "--out", png,
                "--resolution", str(RESOLUTION), "--seed", str(blender_seed))
        if os.path.exists(png):
            ps(sys.executable, os.path.join(SCRIPT_DIR, "make_dds.py"), dds,
               "--source", png, "--format", "DXT5")
            if os.path.exists(dds):
                return _build_rest(effect, donor, color, ovr, reason, motion, folder, name)
        return "Blender energy render failed: %s" % (rb.stdout + rb.stderr).strip()[-160:]

    # BLENDER RENDER: solid debris is made with a 3D render, not numpy.
    #    ⛔ Measured/researched: vanilla's debris atlases come from 3D/photo
    #       sources; a computed silhouette does not look professional. A lit,
    #       faceted, shaded piece only comes out of a render.
    RENDER_MATERIALS = {"concrete": "concrete", "glass": "glass", "wood": "wood",
                        "paper": "paper", "debris": "concrete"}
    if sprite in RENDER_MATERIALS:
        png = os.path.join(folder, name + ".png")
        dds = os.path.join(folder, name + ".dds")
        blender_seed = zlib.crc32(effect.encode("utf-8")) % 9973
        rb = ps(sys.executable, os.path.join(SCRIPT_DIR, "ptfx_blender_render.py"),
                "--material", RENDER_MATERIALS[sprite], "--out", png,
                "--resolution", str(RESOLUTION), "--seed", str(blender_seed))
        if os.path.exists(png):
            r0 = ps(sys.executable, os.path.join(SCRIPT_DIR, "make_dds.py"), dds,
                    "--source", png, "--format", "DXT5")
            if os.path.exists(dds):
                return _build_rest(effect, donor, color, ovr, reason, motion, folder, name)
        return "Blender render failed: %s" % (rb.stdout + rb.stderr).strip()[-160:]

    # EXTERNAL IMAGE: sprites the user generated with ChatGPT take priority.
    #    Procedural generation only for effects that have NO external image.
    #    (Rule §12: do not leave image generation to the model -- the user made them.)
    external = os.path.join(SPRITE, "gpt_%s.png" % effect)
    if os.path.exists(external):
        dds = os.path.join(folder, name + ".dds")
        r0 = ps(sys.executable, os.path.join(SCRIPT_DIR, "make_dds.py"), dds,
                "--source", external, "--format", "DXT5")
        if not os.path.exists(dds):
            return "external image did not become a DDS: %s" % (r0.stdout + r0.stderr).strip()[-160:]
        return _build_rest(effect, donor, color, ovr, reason, motion, folder, name)
    seed = zlib.crc32(effect.encode("utf-8")) & 0x7FFFFFFF
    t = 0.30 + 0.32 * (((seed >> 7) % 1000) / 1000.0)
    neutral = sprite.startswith("neutral_")
    generator = sprite[len("neutral_"):] if neutral else sprite
    if generator not in ptfx_sheet.FAMILIES:
        return "no sprite generator: %s" % generator
    png = os.path.join(folder, name + ".png")
    dds = os.path.join(folder, name + ".dds")
    try:
        single_object = generator in getattr(ptfx_sheet, 'SINGLE_OBJECT', set())
        ptfx_sheet.write_png(
            ptfx_sheet.single_frame(generator, RESOLUTION, t, seed, neutral, single_object), png)
    except Exception as e:
        return "sprite could not be generated: %s" % e
    r0 = ps(sys.executable, os.path.join(SCRIPT_DIR, "make_dds.py"), dds,
            "--source", png, "--format", "DXT5")
    if not os.path.exists(dds):
        return "DDS could not be generated: %s" % (r0.stdout + r0.stderr).strip()[-160:]
    return _build_rest(effect, donor, color, ovr, reason, motion, folder, name)


def _build_rest(effect, donor, color, ovr, reason, motion, folder, name):
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, "ypt_transplant.py"), VANILLA,
           "--effect", donor, "--new-name", name, "--texture", name, "--folder", folder,
           "--color", str(color[0]), str(color[1]), str(color[2])]
    for k, flag in (("lifetime", "--lifetime"), ("rate", "--rate"),
                    ("size_scale", "--size-scale"), ("size_mult", "--size-mult")):
        if k in ovr:
            cmd += [flag, str(ovr[k])]
    r = ps(*cmd)
    xml = os.path.join(folder, name + ".ypt.xml")
    if not os.path.exists(xml):
        return (r.stdout + r.stderr).strip().splitlines()[-1:] or ["transplant failed"]

    s = io.open(xml, encoding="utf-8").read()
    s = re.sub(r'(<Type value="AnimateTexture" />\s*<UnknownC0 value="\d+" />\s*'
               r'<UnknownC4 value=")\d+(")', r"\g<1>0\g<2>", s, count=1)
    s = re.sub(r"<FxcTechnique>RGB_(\w+)</FxcTechnique>",
               r"<FxcTechnique>RGBA_\1</FxcTechnique>", s)
    s, notes = repair_envelope(s)
    if motion:
        s, motion_notes = ptfx_motion.apply_to_document(s, motion)
        notes += motion_notes
        # ⛔ MOTION THAT CANNOT BE WRITTEN = ERROR. If the donor's particle rule
        #    lacks that behaviour (measured: Acceleration and Dampening exist in
        #    only 77% of donors, all three together in 50%) the field is silently
        #    not written and the effect keeps the donor's motion -- the very flaw
        #    we want to fix. An error, not a warning.
        missing = [x for x in motion_notes if "NOT WRITTEN" in x]
        if missing:
            return "the donor does not carry this motion: " + "; ".join(missing)
    ET.fromstring(s)
    io.open(xml, "w", encoding="utf-8").write(s)
    ps("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
       os.path.join(SCRIPT_DIR, "ypt_xml_to_bin.ps1"), "-Xml", xml)
    if not os.path.exists(os.path.join(folder, name + ".ypt")):
        return "not compiled"
    return ("", notes) if notes else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", "--grup", dest="group", default="virus_ambient",
                    type=lambda v: GROUP_ALIASES.get(v, v))
    a = ap.parse_args()
    if a.group not in GROUPS:
        raise SystemExit("no such group: %s (%s)" % (a.group, ", ".join(GROUPS)))
    os.makedirs(OUT_DIR, exist_ok=True)
    n, errors = 0, []
    for effect, donor, sprite, color, ovr, reason, motion in GROUPS[a.group]:
        h = build(effect, donor, sprite, color, ovr, reason, motion, OUT_DIR)
        notes = []
        if isinstance(h, tuple):
            h, notes = h
        if h:
            errors.append((effect, h))
            print("  ERROR   %-18s %s" % (effect, h))
        else:
            n += 1
            extra = ("  [%s]" % ", ".join("%s=%s" % kv for kv in ovr.items())) if ovr else ""
            print("  built   %-18s <- %-28s%s" % (effect, donor, extra))
            # ⛔ Do not name the loop variable `n` -- it overwrites the outer success
            #    counter `n` and the build crashes at `n += 1` after the first repair.
            for msg in notes:
                print("           ! %s" % msg)
    print("\nbuilt: %d / %d" % (n, len(GROUPS[a.group])))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
