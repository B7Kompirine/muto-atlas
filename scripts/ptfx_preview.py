#!/usr/bin/env python3
"""ptfx_preview.py — animated preview driven by DATA read back from a compiled .ypt.

⚠ BE CLEAR ABOUT WHAT THIS IS: this is NOT ENGINE OUTPUT.
GTA's particle system does not run here. This script takes the keyframes
READ BACK from the binary `.ypt` file (spawn rate, lifetime, size curve,
color/alpha curve) and the EMBEDDED TEXTURE, and draws a preview.

What it proves:         whether the data INSIDE the file describes a visible effect
What it does not prove: whether the game/FiveM accepts this file

The input comes from a .ypt dump (made by a former dump script that is not in
this repository). The input file names and the DOKU line tag are that dump's
format and stay as they are:
  doku_ham.bin   -> raw BGRA pixels (A8R8G8B8)
  ptfx_veri.txt  -> TAG|OWNER|NAME|interval|R|G|B|A lines

Usage:
  python ptfx_preview.py <folder> [--out preview.gif]
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys

from PIL import Image

FPS = 30               # fps
DURATION = 3.0         # gif length (s)
CANVAS = 460           # pixels
PX_PER_METRE = 150.0   # pixels in 1 metre


def read_data(path):
    """ptfx_veri.txt -> {name: [(interval, r, g, b, a), ...]} + texture size."""
    kf, texture = {}, None
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = line.split("|")
            if p[0] == "DOKU":          # texture line of the dump format
                texture = (p[1], int(p[2]), int(p[3]), p[4])
                continue
            if len(p) < 8:          # a BOS (empty) line
                continue
            name = p[2].split(":")[-1]
            kf.setdefault(name, []).append(tuple(float(x) for x in p[3:8]))
    for v in kf.values():
        v.sort(key=lambda x: x[0])
    return kf, texture


def curve(kf, name, channel=0, default=0.0):
    """Linear interpolation over the normalised lifetime (t: 0..1)."""
    d = kf.get(name)
    if not d:
        return lambda t: default
    if len(d) == 1:
        v = d[0][1 + channel]
        return lambda t: v

    def f(t):
        t = max(0.0, min(1.0, t))
        for i in range(len(d) - 1):
            t0, t1 = d[i][0], d[i + 1][0]
            if t0 <= t <= t1:
                o = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                return d[i][1 + channel] * (1 - o) + d[i + 1][1 + channel] * o
        return d[-1][1 + channel]
    return f


def load_sprite(folder, width, height):
    """DDS -> alpha mask (L). The color comes from the engine, not from the texture.

    Pillow opens DXT5; a raw BGRA dump is also supported for old
    uncompressed files."""
    dds = os.path.join(folder, "doku.dds")
    if os.path.exists(dds):
        return Image.open(dds).convert("RGBA").split()[3]
    raw = open(os.path.join(folder, "doku_ham.bin"), "rb").read()
    expected = width * height * 4
    if len(raw) < expected:
        sys.exit(f"texture too short: {len(raw)} < {expected}")
    return Image.frombytes("L", (width, height),
                           bytes(raw[i * 4 + 3] for i in range(width * height)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out", "--cikti", dest="out", default="ptfx_preview.gif")
    ap.add_argument("--texture-png", "--doku-png", dest="texture_png", default=None)
    args = ap.parse_args()

    kf, texture = read_data(os.path.join(args.folder, "ptfx_veri.txt"))
    if not texture:
        sys.exit("no DOKU line")
    _, width, height, _ = texture
    mask = load_sprite(args.folder, width, height)
    if args.texture_png:
        mask.save(args.texture_png)

    # --- values read from the file ---
    rate = kf["m_spawnRateOverTimeKFP"][0][1]
    lifetime = kf["m_particleLifeKFP"][0][1]
    speed = kf["m_speedScalarKFP"][0][1]
    # ⛔ The rise comes from the TARGET DOMAIN's position, NOT from Velocity.
    #    (m_positionKFP: channel order interval|X|Y|Z|W -> Z = index 3)
    rise = kf["m_positionKFP"][0][3] if "m_positionKFP" in kf else 0.0
    spawn_r = kf["m_sizeOuterKFP"][0][1] if "m_sizeOuterKFP" in kf else 0.25
    size_min, size_max = curve(kf, "m_whdMinKFP"), curve(kf, "m_whdMaxKFP")
    color = kf["m_rgbaMinKFP"][0]                       # r,g,b constant
    alpha_curve = curve(kf, "m_rgbaMinKFP", channel=3, default=1.0)
    print(f"[i] rate={rate}/s lifetime={lifetime}s speed={speed} rise={rise}m "
          f"spawn_r={spawn_r}m color=({color[1]:.2f},{color[2]:.2f},{color[3]:.2f}) "
          f"peak_alpha={color[4]:.2f}")

    rng = random.Random(20260812)
    frames, particles, remainder = [], [], 0.0
    dt = 1.0 / FPS
    rgb = (int(color[1] * 255), int(color[2] * 255), int(color[3] * 255))

    # pre-warm for one lifetime so the preview starts full
    for step in range(int((DURATION + lifetime) * FPS)):
        remainder += rate * dt
        while remainder >= 1.0:
            remainder -= 1.0
            # spawn sphere: creation domain radius 0.25 m
            u, v = rng.random(), rng.random()
            th, ph = 2 * math.pi * u, math.acos(2 * v - 1)
            r = spawn_r * rng.random() ** (1 / 3)
            x0 = r * math.sin(ph) * math.cos(th)
            y0 = r * math.cos(ph)
            # target: target domain (centre 0,rise; same radius)
            hr = spawn_r * rng.random() ** (1 / 3)
            ht = 2 * math.pi * rng.random()
            hx = hr * math.cos(ht)
            hy = rise + hr * math.sin(ht) * 0.6
            particles.append({
                "x": x0, "y": y0,
                "vx": (hx - x0) / lifetime * speed,
                "vy": (hy - y0) / lifetime * speed,
                "t": 0.0,
                "k": rng.random(),        # blend between min/max
            })
        for p in particles:
            p["t"] += dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
        particles = [p for p in particles if p["t"] < lifetime]

        if step < lifetime * FPS:            # warm-up frames are not recorded
            continue

        canvas = Image.new("RGB", (CANVAS, CANVAS), (26, 26, 28))
        for p in particles:
            n = p["t"] / lifetime
            size = size_min(n) + (size_max(n) - size_min(n)) * p["k"]
            px = max(2, int(size * PX_PER_METRE))
            al = max(0.0, min(1.0, alpha_curve(n)))
            if al <= 0.004:
                continue
            m = mask.resize((px, px), Image.BILINEAR)
            m = m.point(lambda q, s=al: int(q * s))
            layer = Image.new("RGB", (px, px), rgb)
            X = int(CANVAS / 2 + p["x"] * PX_PER_METRE - px / 2)
            Y = int(CANVAS * 0.72 - p["y"] * PX_PER_METRE - px / 2)
            canvas.paste(layer, (X, Y), m)
        frames.append(canvas)

    if not frames:
        sys.exit("no frames produced")
    frames[0].save(args.out, save_all=True, append_images=frames[1:],
                   duration=int(1000 / FPS), loop=0, optimize=True)
    print(f"[+] {args.out}  {len(frames)} frames  "
          f"{os.path.getsize(args.out):,} bytes")


if __name__ == "__main__":
    main()
