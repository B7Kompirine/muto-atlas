#!/usr/bin/env python3
"""ptfx_sheet.py — ANIMATED sprite sheet (flipbook) for a GTA particle.

WHY IT EXISTS: `build_custom_ptfx.py` already writes the `AnimateTexture`
behaviour (`--sheet FRAMES`, `--anim-speed`) but there was no SHEET to feed it;
the generated effects used a single-frame (`--sheet 1`) static sprite.

⛔ VANILLA MEASUREMENT (core.ypt, 1736 particle rules): **45%** of the rules
carry `ParticleBehaviourAnimateTexture`. The texture names say so too:
`ptfx_smoke_billow_anim_rgba` 1024x1024, `_explosion_fireball_rgba`
2048x1024, `ptfx_fire_v2` 1024x2048, `ptfx_cig_smoke_sheet` 256x256.
So the secret of a "good looking" particle is not resolution but a texture
that CHANGES over the particle's life. A single-frame sprite shows the same
dull smudge for its whole life.

⛔ THE GRID MUST BE SQUARE: columns = rows = sqrt(frames). `build_custom_ptfx.py`
writes FRAME COUNT - 1 into the `UnknownC4` field. Valid frame counts:
4 (2x2), 16 (4x4), 36 (6x6), 64 (8x8). Frames run left to right, top to
bottom.

Usage:
  python ptfx_sheet.py smoke out.png --frames 36 --resolution 1024
  python ptfx_sheet.py --list
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np

try:
    from PIL import Image
except ImportError:
    print("PIL required: pip install pillow", file=sys.stderr)
    raise


# ------------------------------------------------------------- helpers

def _rng(seed):
    return np.random.default_rng(seed)


def _blur(a, r):
    """Separable box blur, 3 passes (gaussian approximation).

    ⛔ The output shape stays the SAME as the input; NO fix with `np.resize`
    (that is data repetition, not spatial resizing).
    """
    if r < 1:
        return a
    out = a.astype(np.float32)
    k = 2 * int(r) + 1
    for _ in range(3):
        for axis in (0, 1):
            pad = [(0, 0), (0, 0)]
            pad[axis] = (int(r), int(r))
            p = np.pad(out, pad, mode='edge')
            c = np.cumsum(p, axis=axis, dtype=np.float32)
            zero = np.zeros_like(np.take(c, [0], axis=axis))
            c = np.concatenate([zero, c], axis=axis)
            upper = np.take(c, np.arange(k, k + out.shape[axis]), axis=axis)
            lower = np.take(c, np.arange(0, out.shape[axis]), axis=axis)
            out = (upper - lower) / float(k)
    return out


def _value_noise(n, cell, rng):
    """Single-octave value noise: coarse grid + bilinear upscaling."""
    g = max(2, int(cell))
    coarse = rng.random((g + 1, g + 1)).astype(np.float32)
    yi = np.linspace(0, g, n, endpoint=False)
    xi = np.linspace(0, g, n, endpoint=False)
    y0 = np.floor(yi).astype(np.int32); x0 = np.floor(xi).astype(np.int32)
    fy = (yi - y0)[:, None]; fx = (xi - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)   # smoothstep
    a = coarse[y0][:, x0]; b = coarse[y0][:, x0 + 1]
    c = coarse[y0 + 1][:, x0]; d = coarse[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def _fbm(n, octaves, cell, rng, persistence=0.55):
    """Multi-octave value noise (0..1)."""
    acc = np.zeros((n, n), np.float32)
    amplitude = 1.0
    total = 0.0
    for o in range(octaves):
        acc += amplitude * _value_noise(n, cell * (2 ** o), rng)
        total += amplitude
        amplitude *= persistence
    return acc / max(total, 1e-6)


def _radial(n, center=(0.5, 0.5)):
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    return np.sqrt(((x / n) - center[0]) ** 2 + ((y / n) - center[1]) ** 2) * 2.0


def _rescale(a, new):
    """Area-averaged resize."""
    n = a.shape[0]
    if n == new:
        return a
    yi = (np.arange(new) + 0.5) * (n / float(new)) - 0.5
    i0 = np.clip(np.floor(yi).astype(np.int32), 0, n - 1)
    i1 = np.clip(i0 + 1, 0, n - 1)
    f = np.clip(yi - i0, 0, 1)
    mid = a[i0] * (1 - f[:, None]) + a[i1] * f[:, None]
    return mid[:, i0] * (1 - f[None, :]) + mid[:, i1] * f[None, :]


# ------------------------------------------------------------- frame generators
# Every generator: (frame_index, frame_count, resolution, rng) -> (rgb, alpha)
# t = 0..1 progress over the particle's life.

def k_smoke(i, n, c, rng, hot=False):
    """A smoke puff that curls as it grows and disperses.

    ⛔ DO NOT RAISE DENSITY BY CRUSHING THE NOISE. In the first fix the
    multiplier became `0.86 + 0.34*billow`; since the range was almost constant,
    coverage went up but the STRUCTURE went flat -- composited over grey it
    looked like "a blurry ball" next to vanilla's fine curling smoke.
    Density comes from the MASK and the threshold, the noise amplitude stays full.

    ⛔ ONE OCTAVE GIVES NO CURLS. Vanilla smoke has two scales:
    coarse billows + fine filaments. Without a second, high-frequency layer
    the smoke does not read as "smoke".
    """
    t = i / max(n - 1, 1)
    d1 = _fbm(c, 4, 3, _rng(1000 + i * 7), 0.58)      # coarse billow
    d2 = _fbm(c, 3, 9, _rng(1500 + i * 7), 0.50)      # fine curl
    d = 0.66 * d1 + 0.34 * d2
    # ⛔ THE SILHOUETTE MUST NOT BE A CIRCLE. When the mask is a plain radial disc
    # and a constant base remains in the multiplier (`0.10 + ...`), a faint DISC
    # shows even where the noise is empty -- composited over grey the circle
    # edge reads bare. Vanilla smoke has an irregular silhouette. Fix: distort
    # the radius with noise and remove the base completely.
    r = _radial(c) - 0.13 * (d1 - 0.5)           # silhouette distorted by noise
    edge = 0.50 + 0.44 * t                       # puff radius
    softness = 0.20 + 0.30 * t                   # edge softness
    mask = np.clip((edge - r) / max(softness, 1e-3), 0.0, 1.0)
    # ⛔ THE EROSION THRESHOLD RISES OVER TIME, IT DOES NOT FALL. The first
    # version had `threshold = 0.44 - 0.24*t`: in late frames the threshold
    # dropped so far that ALL of the noise passed, the modulation ended and
    # what remained was the bare radial mask -- i.e. a flat DISC.
    # Composited over grey the last two frames read as a clear circle.
    # Real smoke BREAKS UP as it disperses: the threshold must rise.
    threshold = 0.34 + 0.26 * t
    billow = np.clip((d - threshold) / 0.24, 0.0, 1.0)
    alpha = mask * np.clip(1.35 * billow - 0.03, 0.0, 1.0)
    alpha *= (1.0 - t) ** 0.40                   # fade over life
    alpha = _blur(alpha, 1 + int(c * 0.004))
    if hot:
        inner = np.clip((0.30 * (1 - t) - r) / 0.22, 0.0, 1.0)
        rgb = np.dstack([np.clip(0.35 + 1.4 * inner, 0, 1),
                         np.clip(0.28 + 0.9 * inner, 0, 1),
                         np.clip(0.24 + 0.35 * inner, 0, 1)]).astype(np.float32)
    else:
        # Dark body + bright tops: the sense of volume comes from here.
        v = 0.30 + 0.58 * billow
        rgb = np.dstack([v, v, v * 1.02]).astype(np.float32)
    return rgb, alpha

def k_fire(i, n, c, rng):
    """Fire tongues licking upward.

    ⛔ THE FIRST VERSION called `k_smoke(hot=True)`: it gave a radial hot smudge
    that looked NOTHING like fire. Fire is NOT coloured smoke - what defines
    smoke is dispersal, what defines fire is tongues RISING UPWARD.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    u = xx / c
    v = 1.0 - yy / c                       # 0 = base, 1 = top

    d = _fbm(c, 4, 5, _rng(2500), 0.55)    # 3 -> 5 cells: finer tongues
    shift = int((0.55 * t) * c) % max(c, 1)
    d = np.roll(d, -shift, axis=0)         # the flame climbs

    # ⛔ THE FIRST VERSION DID NOT FIT THE CELL: width 0.42 and a constant 0.2
    # envelope at the base made it touch the frame edge at 0.44 alpha (measured;
    # `smoke`/`spark` were clean at 0.00). If a flipbook frame touches the edge,
    # in game a HARD CUT shows at the sprite quad boundary. The width was
    # narrowed and a soft start was put at the base.
    width = 0.32 * (1.0 - 0.70 * v)
    centre = 0.5 + 0.05 * np.sin(v * 7.0 + t * 5.0)
    cone = np.clip(1.0 - np.abs(u - centre) / np.maximum(width, 1e-3), 0, 1)

    height = 0.26 + 0.58 * min(t * 1.8, 1.0)
    base = np.clip((v - 0.06) / 0.10, 0, 1)
    envelope = np.clip((height - v) / 0.24, 0, 1) * base

    breakup = np.clip((d - (0.30 + 0.42 * v)) / 0.20, 0, 1)
    alpha = cone * envelope * (0.35 + 0.65 * breakup)
    alpha *= (1.0 - t) ** 0.45
    alpha = _blur(alpha, 1)

    heat = np.clip(1.0 - v / max(height, 1e-3), 0, 1) ** 0.8
    rgb = np.dstack([np.clip(0.55 + 0.85 * heat, 0, 1),
                     np.clip(0.16 + 0.78 * heat ** 1.5, 0, 1),
                     np.clip(0.05 + 0.55 * heat ** 4, 0, 1)]).astype(np.float32)
    return rgb, alpha


def _old_k_fireball(i, n, c, rng):
    """Explosion: bright core -> billowing fire -> darkening smoke.

    ⛔ THE FIRST VERSION HAD NO STRUCTURE: one radial mask + one noise layer,
    the result was a "fading red smudge". In the table of 15 families it was the
    weakest by eye. What makes an explosion an explosion is BILLOWING: separate
    lobes growing at different speeds. Three lobes were added and the colour
    SHIFTS over time from white core -> orange -> dark smoke.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    u, v = xx / c - 0.5, yy / c - 0.5
    radius = 0.10 + 0.34 * (t ** 0.55)

    alpha = np.zeros((c, c), np.float32)
    for k in range(3):
        r2 = _rng(2600 + k * 7)
        angle = r2.random() * math.tau
        offset = (0.05 + 0.10 * r2.random()) * t
        lx, ly = math.cos(angle) * offset, math.sin(angle) * offset
        lr = radius * (0.62 + 0.30 * r2.random())
        dist = np.sqrt((u - lx) ** 2 + (v - ly) ** 2)
        alpha = np.maximum(alpha, np.clip((lr - dist) / (0.06 + 0.16 * t), 0, 1))

    d = _fbm(c, 4, 4, _rng(2650), 0.62)
    d = np.roll(d, -int(0.25 * t * c) % max(c, 1), axis=0)
    billow = np.clip((d - (0.56 - 0.32 * t)) / 0.24, 0, 1)
    alpha = alpha * (0.34 + 0.66 * billow) * (1.0 - t) ** 0.7
    alpha = _blur(alpha, 1 + int(c * 0.006))

    # ⛔ DO NOT BUILD THE COLOUR CHANNEL BY CHANNEL. In the first two tries R/G/B
    # were written with separate formulas; as the channels faded at different
    # speeds the core came out first dull orange, then GREENISH (verified by
    # eye). Channel crossover silently invents colours like this. The right way
    # is to build one TEMPERATURE field and interpolate between three fixed
    # colours: smoke -> fire -> white core. Monotonicity is guaranteed that way.
    dist0 = np.sqrt(u * u + v * v)
    core = np.clip((radius * 0.68 - dist0) / 0.09, 0, 1)
    heat = np.clip(core * (1.0 - t) ** 0.9 * 1.25
                   + (1.0 - t) ** 2.0 * 0.42, 0.0, 1.0)

    SMOKE = np.array([0.13, 0.120, 0.115], np.float32)
    FIRE = np.array([1.00, 0.42, 0.09], np.float32)
    WHITE = np.array([1.00, 0.94, 0.74], np.float32)
    a1 = np.clip(heat / 0.55, 0, 1)[..., None]
    a2 = np.clip((heat - 0.55) / 0.45, 0, 1)[..., None]
    base = SMOKE + (FIRE - SMOKE) * a1
    rgb = (base + (WHITE - base) * a2).astype(np.float32)

    # ⛔ THE RIGHT COLOUR ALONE IS NOT ENOUGH - ALPHA MUST BE IN THE CORE TOO.
    # Even AFTER the colour was fixed to smoke->fire->white the core still looked
    # GREY: the alpha there was ~0.34 and the background showed through; at the
    # edge the lobes overlapped so alpha was high -> "grey centre, orange ring".
    # The centre of an explosion is its most OPAQUE part.
    alpha = np.clip(alpha + core * (1.0 - t) ** 1.1 * 0.85, 0, 1)
    return rgb, alpha


def k_electric(i, n, c, rng):
    """Forking electric arc."""
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    rr = _rng(11000 + i * 17)
    stack = [(0.5, 0.5, rr.random() * math.tau, 0.30, c * 0.010, 1)]
    while stack:
        x0, y0, angle, length, thick, depth = stack.pop()
        px, py = x0, y0
        for _k in range(7):
            angle += (rr.random() - 0.5) * 1.1
            nx = px + math.cos(angle) * length / 7.0
            ny = py + math.sin(angle) * length / 7.0
            # ⛔ The arc walks freely and forks; unconstrained it hits the frame
            # edge at 0.98 alpha. It is KEPT inside the cell.
            nx = min(max(nx, 0.12), 0.88)
            ny = min(max(ny, 0.12), 0.88)
            dx, dy = (nx - px) * c, (ny - py) * c
            L = max(math.hypot(dx, dy), 1e-6)
            sN = np.clip(((xx - px * c) * dx + (yy - py * c) * dy) / (L * L), 0, 1)
            mx = px * c + sN * dx
            my = py * c + sN * dy
            dist = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2)
            alpha = np.maximum(alpha, np.clip(1.0 - dist / max(thick, 1e-6), 0, 1))
            px, py = nx, ny
            if depth > 0 and rr.random() < 0.4:
                stack.append((px, py, angle + (rr.random() - 0.5) * 2.0,
                              length * 0.45, thick * 0.6, depth - 1))
    halo = _blur(alpha, max(1, int(c * 0.018))) * 0.55
    alpha = np.clip(alpha + halo, 0, 1) * (0.35 + 0.65 * abs(math.sin(t * math.pi * 3)))
    rgb = np.dstack([np.full((c, c), 0.72, np.float32),
                     np.full((c, c), 0.86, np.float32),
                     np.full((c, c), 1.0, np.float32)])
    return rgb.astype(np.float32), alpha


def k_blood(i, n, c, rng):
    """Blood mist / splash."""
    t = i / max(n - 1, 1)
    rr = _rng(12000)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for _k in range(40):
        angle = rr.random() * math.tau
        speed = 0.10 + 0.34 * rr.random() ** 1.6
        x = 0.5 + math.cos(angle) * speed * t
        y = 0.5 + math.sin(angle) * speed * t * 0.6 + 0.30 * t * t
        rad = c * (0.010 + 0.030 * rr.random()) * (1.0 - 0.3 * t)
        dist = np.sqrt((xx - x * c) ** 2 + (yy - y * c) ** 2)
        alpha = np.maximum(alpha, np.clip(1.0 - dist / max(rad, 1e-6), 0, 1))
    alpha *= (1.0 - t) ** 0.5
    alpha = _blur(alpha, 1)
    v = np.full((c, c), 1.0, np.float32)
    return np.dstack([v * 0.55, v * 0.06, v * 0.05]).astype(np.float32), alpha


def k_leaf(i, n, c, rng):
    """Scattering leaves: flat, spinning, green-brown."""
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    tone = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(9):
        r2 = _rng(13000 + k)
        angle0 = r2.random() * math.tau
        speed = 0.12 + 0.26 * r2.random()
        x = (0.5 + math.cos(angle0) * speed * t) * c
        y = (0.5 + math.sin(angle0) * speed * t * 0.5 + 0.30 * t) * c
        spin = angle0 + t * (3.0 + 5.0 * r2.random())
        a2 = c * (0.030 + 0.022 * r2.random())
        b2 = a2 * (0.30 + 0.35 * abs(math.cos(spin * 1.7)))
        dx = (xx - x) * math.cos(spin) + (yy - y) * math.sin(spin)
        dy = -(xx - x) * math.sin(spin) + (yy - y) * math.cos(spin)
        e = np.clip(1.0 - ((dx / a2) ** 2 + (dy / max(b2, 1e-6)) ** 2), 0, 1)
        alpha = np.maximum(alpha, (e > 0).astype(np.float32))
        tone = np.maximum(tone, e * r2.random())
    alpha *= (1.0 - t) ** 0.3
    alpha = _blur(alpha, 1)
    rgb = np.dstack([0.35 + 0.42 * tone, 0.42 + 0.24 * tone,
                     0.14 + 0.12 * tone]).astype(np.float32)
    return rgb, alpha


def k_dust(i, n, c, rng):
    """Fine-grained dust cloud — more broken up and faster dispersing than smoke."""
    t = i / max(n - 1, 1)
    d = _fbm(c, 5, 5, _rng(2000 + i * 11), 0.62)
    r = _radial(c)
    mask = np.clip((0.34 + 0.60 * t - r) / (0.22 + 0.30 * t), 0.0, 1.0)
    billow = np.clip((d - (0.68 - 0.34 * t)) / 0.22, 0.0, 1.0)
    alpha = mask * billow * (1.0 - t) ** 1.3
    alpha = _blur(alpha, 1)
    v = 0.62 + 0.30 * billow
    return np.dstack([v, v * 0.94, v * 0.84]).astype(np.float32), alpha


def k_steam(i, n, c, rng):
    """A wisp of steam creeping upward.

    ⛔ THE FIRST VERSION WAS TOO FAINT: one soft smudge, heavy blur and a 0.75
    multiplier made it almost invisible in game. What makes steam visible is
    not opacity but STRUCTURE: wisps stretching up and separating from each
    other. The horizontal noise scale was narrowed (wisp), the vertical
    stretched, the blur halved.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    v = 1.0 - yy / c

    # vertically stretched noise = wisp
    d = _fbm(c, 4, 6, _rng(3000), 0.58)
    d = _blur(d, max(1, int(c * 0.010)))
    shift = int(0.70 * t * c) % max(c, 1)
    d = np.roll(d, -shift, axis=0)

    width = 0.30 + 0.34 * v + 0.22 * t
    cone = np.clip(1.0 - np.abs(xx / c - 0.5) / width, 0, 1)
    height = 0.42 + 0.56 * min(t * 1.6, 1.0)
    envelope = np.clip((height - v) / 0.30, 0, 1) * np.clip(v / 0.05 + 0.15, 0, 1)

    wisp = np.clip((d - (0.40 + 0.16 * v)) / 0.24, 0, 1)
    alpha = cone * envelope * (0.30 + 0.70 * wisp)
    alpha *= (1.0 - t) ** 0.9
    alpha = _blur(alpha, 1 + int(c * 0.006))
    v2 = np.full((c, c), 0.93, np.float32)
    return np.dstack([v2, v2, v2 * 0.98]).astype(np.float32), alpha

def k_spark(i, n, c, rng):
    """Bright lines shooting out from the centre and shortening."""
    t = i / max(n - 1, 1)
    rr = _rng(4000)
    count = 26
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(count):
        angle = rr.random() * math.tau
        speed = 0.20 + 0.34 * rr.random()
        length = speed * t
        start = 0.5 + np.array([math.cos(angle), math.sin(angle)]) * max(length - 0.06, 0.0)
        end = 0.5 + np.array([math.cos(angle), math.sin(angle)]) * length
        px = np.array([start[0], end[0]]) * c
        py = np.array([start[1], end[1]]) * c
        dx, dy = px[1] - px[0], py[1] - py[0]
        seg_len = max(math.hypot(dx, dy), 1e-6)
        # distance of the point to the line segment
        s = np.clip(((xx - px[0]) * dx + (yy - py[0]) * dy) / (seg_len * seg_len), 0, 1)
        mx = px[0] + s * dx; my = py[0] + s * dy
        dist = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2)
        thick = c * (0.010 + 0.008 * (1 - t))
        alpha = np.maximum(alpha, np.clip(1.0 - dist / thick, 0, 1))
    alpha *= (1.0 - t) ** 0.6
    alpha = _blur(alpha, 1)
    rgb = np.dstack([np.full((c, c), 1.0, np.float32),
                     np.full((c, c), 0.78 - 0.30 * t, np.float32),
                     np.full((c, c), 0.35 - 0.28 * t, np.float32)])
    return rgb.astype(np.float32), alpha


def k_splash(i, n, c, rng):
    """Water splash: drops going outward and down."""
    t = i / max(n - 1, 1)
    rr = _rng(5000)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(34):
        angle = rr.random() * math.tau
        speed = 0.16 + 0.30 * rr.random()
        x = 0.5 + math.cos(angle) * speed * t
        y = 0.5 + math.sin(angle) * speed * t * 0.55 + 0.34 * t * t   # gravity
        rad = c * (0.020 + 0.026 * rr.random()) * (1.0 - 0.4 * t)
        dist = np.sqrt((xx - x * c) ** 2 + (yy - y * c) ** 2)
        alpha = np.maximum(alpha, np.clip(1.0 - dist / max(rad, 1e-6), 0, 1))
    alpha *= (1.0 - t) ** 0.5
    alpha = _blur(alpha, 1)
    v = np.full((c, c), 0.86, np.float32)
    return np.dstack([v * 0.88, v * 0.94, v]).astype(np.float32), alpha


def k_ember(i, n, c, rng):
    """Ember grains drifting upward + motion trail.

    ⛔ THE FIRST VERSION WAS TOO SPARSE (coverage 1%): the grains were like dots.

    ⛔ THE SECOND VERSION WENT THE OTHER WAY: 30 grains + a 0.030*c halo each,
    the grains stuck together into one orange MASS - in the table it read like
    "leaf". What makes an ember effect an ember is bright points that can be
    picked out ONE BY ONE. Went down to 14 grains, radius narrowed, halo
    halved, and the grains are scattered at the start (not all from the centre).
    """
    t = i / max(n - 1, 1)
    rr = _rng(6000 + i * 3)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(14):
        r2 = _rng(6100 + k)
        # initial spread: not all start from the same point
        bx = 0.5 + (r2.random() - 0.5) * 0.34
        by = 0.66 + (r2.random() - 0.5) * 0.20
        angle = r2.random() * math.tau
        speed = 0.05 + 0.13 * r2.random()
        rise = 0.16 + 0.16 * r2.random()

        def position(tt):
            return (bx + math.cos(angle) * speed * tt,
                    by + math.sin(angle) * speed * tt * 0.5 - rise * tt)

        x, y = position(t)
        xg, yg = position(max(t - 0.10, 0.0))
        dx, dy = (x - xg) * c, (y - yg) * c
        L = max(math.hypot(dx, dy), 1e-6)
        sN = np.clip(((xx - xg * c) * dx + (yy - yg * c) * dy) / (L * L), 0, 1)
        dist = np.sqrt((xx - (xg * c + sN * dx)) ** 2 + (yy - (yg * c + sN * dy)) ** 2)
        flicker = 0.55 + 0.45 * rr.random()
        rad = c * 0.016 * flicker
        alpha = np.maximum(alpha, np.clip(1.0 - dist / rad, 0, 1) ** 0.6 * flicker)
    halo = _blur(alpha, max(1, int(c * 0.016))) * 0.38
    alpha = np.clip(alpha + halo, 0, 1) * (1.0 - t) ** 0.7
    rgb = np.dstack([np.full((c, c), 1.0, np.float32),
                     np.full((c, c), 0.50 + 0.32 * (1 - t), np.float32),
                     np.full((c, c), 0.12, np.float32)])
    return rgb.astype(np.float32), alpha

def k_fog(i, n, c, rng):
    """Fog layers creeping along the ground.

    ⛔ THE FIRST VERSION was almost THE SAME as `steam` (both a soft smudge).
    Horizontal layering was added.

    ⛔ THE SECOND VERSION WAS ONLY TWO BANDS: at this scale `sin(y * 9)` fit only
    ~2 visible bands in the cell and the result read like "two smudges stacked"
    - it did not look like fog. Fog must be WIDE and LOW: it fills the cell
    horizontally, gathers in the lower half vertically, and fine wisps drift
    side by side inside it.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    u, v = xx / c, yy / c

    d = _fbm(c, 5, 3, _rng(4000), 0.62)
    d = np.roll(d, int(0.35 * t * c) % max(c, 1), axis=1)     # horizontal drift
    fine = _fbm(c, 3, 9, _rng(4100), 0.50)
    fine = np.roll(fine, int(0.6 * t * c) % max(c, 1), axis=1)

    # wide horizontally, gathered in the lower half vertically
    horizontal = np.clip(1.0 - np.abs(u - 0.5) / 0.52, 0, 1) ** 0.6
    vertical = np.clip((v - 0.24) / 0.22, 0, 1) * np.clip((0.96 - v) / 0.14, 0, 1)

    wisp = np.clip((0.55 * d + 0.45 * fine - 0.34) / 0.30, 0, 1)
    alpha = horizontal * vertical * (0.22 + 0.62 * wisp)
    alpha *= (1.0 - abs(2 * t - 1) * 0.72)
    alpha = _blur(alpha, 2 + int(c * 0.016))
    g = np.full((c, c), 0.82, np.float32)
    return np.dstack([g * 0.97, g * 0.99, g]).astype(np.float32), alpha

def k_bubble(i, n, c, rng):
    """Rising stream of bubbles.

    ⛔ THE FIRST VERSION WAS CROWDED: 9 bubbles overlapped into an unreadable
    tangle. Went down to 3 big bubbles.

    ⛔ THE SECOND VERSION PILED UP: each bubble's phase was NORMALISED with
    `tk = (t - delay) / (1 - delay)`, so even though they started late they ALL
    ARRIVED AT THE SAME TIME. Result: in the last frames the three bubbles sat
    side by side at the same height - it read like "three rings", not "rising
    bubbles". The automatic stillness gate flagged this as 20 still frames, and
    it was verified by eye too.

    The right way is a CONTINUOUS FLOW: each bubble wraps its own phase with
    `% 1.0`, the phases have fixed offsets; in every frame the three bubbles are
    at DIFFERENT heights and the sheet loops seamlessly by itself.

    ⛔ THE RADIUS IS A CELL RATIO. When I wrote 0.085 the bubble stayed only
    8% of the cell - in game it looks like a dot.
    """
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    bright = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(3):
        r2 = _rng(8000 + k)
        x = 0.28 + 0.22 * k + 0.04 * (r2.random() - 0.5)
        tk = (t + k / 3.0) % 1.0                  # continuous flow, fixed phase
        # ⛔ THE RANGE MUST ACCOUNT FOR THE RADIUS: even if the grain's CENTRE
        # stays inside the cell, it spills out by its radius and makes a hard
        # cut at the frame edge. The edge mask softens this but clips the content.
        rad = c * (0.15 + 0.04 * r2.random()) * (0.62 + 0.38 * tk)
        y = 0.76 - 0.52 * tk
        dist = np.sqrt((xx - x * c) ** 2 + (yy - y * c) ** 2)
        ring = np.clip(1.0 - np.abs(dist - rad) / (rad * 0.22), 0, 1)
        inner = np.clip(1.0 - dist / rad, 0, 1) * 0.16
        pdist = np.sqrt((xx - (x - 0.050) * c) ** 2 + (yy - (y - 0.050) * c) ** 2)
        p = np.clip(1.0 - pdist / (rad * 0.30), 0, 1)
        # soft birth and death: no jump in the loop
        fade = np.clip(tk / 0.12, 0, 1) * np.clip((1.0 - tk) / 0.18, 0, 1)
        fade = float(fade) * 0.85 + 0.15
        alpha = np.maximum(alpha, np.maximum(ring * 0.85, np.maximum(inner, p)) * fade)
        bright = np.maximum(bright, p * fade)
    alpha = _blur(alpha, 1)
    v = 0.70 + 0.30 * bright
    return np.dstack([v * 0.88, v * 0.95, v]).astype(np.float32), alpha

def k_debris(i, n, c, rng):
    """Solid fragments scattering while spinning (rubble/leaf)."""
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(11):
        r2 = _rng(9000 + k)
        angle0 = r2.random() * math.tau
        # ⛔ THE RANGE MUST ACCOUNT FOR THE RADIUS: even if the grain's CENTRE
        # stays inside the cell, it spills out by its radius and makes a hard
        # cut at the frame edge. The edge mask softens this but clips the
        # content - the fix is to narrow the range at the source.
        speed = 0.10 + 0.20 * r2.random()
        x = (0.5 + math.cos(angle0) * speed * t) * c
        y = (0.5 + math.sin(angle0) * speed * t + 0.14 * t * t) * c
        spin = angle0 + t * (4.0 + 6.0 * r2.random())
        half = c * (0.022 + 0.020 * r2.random())
        dx = (xx - x) * math.cos(spin) + (yy - y) * math.sin(spin)
        dy = -(xx - x) * math.sin(spin) + (yy - y) * math.cos(spin)
        piece = ((np.abs(dx) < half) & (np.abs(dy) < half * 0.42)).astype(np.float32)
        alpha = np.maximum(alpha, piece)
    alpha *= (1.0 - t) ** 0.35
    alpha = _blur(alpha, 1)
    v = np.full((c, c), 0.45, np.float32)
    return np.dstack([v, v * 0.86, v * 0.70]).astype(np.float32), alpha


def k_ring(i, n, c, rng):
    """Shock wave ring opening outward."""
    t = i / max(n - 1, 1)
    r = _radial(c)
    radius = 0.06 + 0.86 * t
    thick = 0.10 + 0.16 * t
    alpha = np.clip(1.0 - np.abs(r - radius) / thick, 0, 1) ** 1.6
    alpha *= (1.0 - t) ** 1.1
    alpha = _blur(alpha, 1 + int(c * 0.006))
    v = np.full((c, c), 0.95, np.float32)
    return np.dstack([v, v * 0.95, v * 0.90]).astype(np.float32), alpha


# --------------------------------------------------- FAMILIES WITH A DISTINCT SILHOUETTE
# ⛔ These families exist so they are NOT "the same thing with a different colour".
#    Criterion: composited over grey and placed side by side, which one it is
#    must be clear FROM THE SHAPE. Colour comes from the tint, so RGB is kept neutral here.

def _old_k_star(i, n, c, rng):
    """Sharp radial flare -- electric arc / magic impact.

    ⛔ It MUST differ from the SOFT DISC of `fireball`: an arc impact is not a
       soft ball but a star with long thin SPIKES.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    dx = (xx / c - 0.5) * 2.0
    dy = (yy / c - 0.5) * 2.0
    r = np.sqrt(dx * dx + dy * dy) + 1e-6
    angle = np.arctan2(dy, dx)
    # 6 main + 6 secondary spikes; the secondary spikes are short
    spike = np.abs(np.cos(6.0 * angle)) ** 14.0 + 0.35 * np.abs(np.cos(6.0 * angle + 0.5236)) ** 22.0
    length = 0.30 + 0.62 * t
    ray = np.clip(1.0 - r / length, 0, 1) ** 2.2 * spike
    core = np.clip(1.0 - r / (0.11 * (1.0 - 0.55 * t)), 0, 1) ** 1.4
    alpha = np.clip(ray * 1.5 + core, 0, 1)
    alpha *= (1.0 - t) ** 1.5
    alpha = _blur(alpha, 1)
    v = np.clip(0.72 + 0.28 * core, 0, 1).astype(np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def k_fly(i, n, c, rng):
    """Small DARK dots -- fly/insect swarm. NO glow."""
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(16):
        r2 = _rng(31000 + k)
        angle = r2.random() * math.tau
        orbit = 0.10 + 0.22 * r2.random()
        # irregular wandering: oscillation at two different frequencies
        phase = t * (5.0 + 7.0 * r2.random())
        x = (0.5 + math.cos(angle + phase * 0.6) * orbit) * c
        y = (0.5 + math.sin(angle + phase) * orbit * 0.7) * c
        rr = c * (0.008 + 0.006 * r2.random())
        d = ((xx - x) ** 2 + ((yy - y) * 1.6) ** 2) / (rr * rr)
        alpha = np.maximum(alpha, np.clip(1.0 - d, 0, 1) ** 0.7)
    alpha = _blur(alpha, 1)
    v = np.full((c, c), 0.22, np.float32)          # DARK: a fly does not emit light
    return np.dstack([v, v, v]).astype(np.float32), alpha


def _old_k_glass(i, n, c, rng):
    """Glass shard -- sharp triangular pieces with a bright EDGE and a hollow inside."""
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(9):
        r2 = _rng(32000 + k)
        angle0 = r2.random() * math.tau
        speed = 0.12 + 0.24 * r2.random()
        x = (0.5 + math.cos(angle0) * speed * t) * c
        y = (0.5 + math.sin(angle0) * speed * t + 0.20 * t * t) * c
        spin = angle0 + t * (3.0 + 5.0 * r2.random())
        L = c * (0.030 + 0.026 * r2.random())
        u = (xx - x) * math.cos(spin) + (yy - y) * math.sin(spin)
        v2 = -(xx - x) * math.sin(spin) + (yy - y) * math.cos(spin)
        # sharp triangle: width narrows with length
        inside = (u > -L) & (u < L) & (np.abs(v2) < 0.42 * (L - u) + 1e-3)
        # ⛔ What shows in glass is the EDGE; a filled triangle looks like plastic.
        d = np.minimum(np.abs(np.abs(v2) - (0.42 * (L - u))), np.abs(u - L))
        edge = np.clip(1.0 - d / (c * 0.006), 0, 1)
        alpha = np.maximum(alpha, np.where(inside, np.maximum(edge, 0.16), 0.0))
    alpha *= (1.0 - t) ** 0.30
    alpha = _blur(alpha, 1)
    v = np.full((c, c), 0.90, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def k_wood(i, n, c, rng):
    """Long thin splinter -- wood. Aspect ratio 8:1, clearly separate from `debris`."""
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(10):
        r2 = _rng(33000 + k)
        angle0 = r2.random() * math.tau
        speed = 0.10 + 0.22 * r2.random()
        x = (0.5 + math.cos(angle0) * speed * t) * c
        y = (0.5 + math.sin(angle0) * speed * t + 0.16 * t * t) * c
        spin = angle0 + t * (2.5 + 4.0 * r2.random())
        L = c * (0.055 + 0.035 * r2.random())
        # ⛔ 9:1 read like a "scratch" on the contact sheet; 5:1 is still clearly
        #    separate from the 2.4:1 block of `debris` but VISIBLE.
        W = L * 0.20                                   # 5:1
        u = (xx - x) * math.cos(spin) + (yy - y) * math.sin(spin)
        v2 = -(xx - x) * math.sin(spin) + (yy - y) * math.cos(spin)
        # pointed ends
        width = W * np.clip(1.0 - (np.abs(u) / L) ** 3.0, 0, 1)
        alpha = np.maximum(alpha, ((np.abs(u) < L) & (np.abs(v2) < width)).astype(np.float32))
    alpha *= (1.0 - t) ** 0.30
    alpha = _blur(alpha, 1)
    v = np.full((c, c), 0.80, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def k_concrete(i, n, c, rng):
    """Angular CHUNKY block -- concrete/rubble. Bigger than `debris` and angular."""
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(7):
        r2 = _rng(34000 + k)
        angle0 = r2.random() * math.tau
        # ⛔ When the blocks spawned in the centre and dispersed slowly they
        #    overlapped at t=0.4 into ONE lump. They must be spread at the start too.
        speed = 0.16 + 0.26 * r2.random()
        spread = 0.13 + 0.10 * r2.random()          # initial spread
        x = (0.5 + math.cos(angle0) * (spread + speed * t)) * c
        y = (0.5 + math.sin(angle0) * (spread + speed * t) + 0.22 * t * t) * c
        spin = angle0 + t * (1.5 + 3.0 * r2.random())
        R = c * (0.032 + 0.022 * r2.random())
        u = (xx - x) * math.cos(spin) + (yy - y) * math.sin(spin)
        v2 = -(xx - x) * math.sin(spin) + (yy - y) * math.cos(spin)
        # irregular pentagon: the radius undulates with the angle
        a2 = np.arctan2(v2, u)
        rr = np.sqrt(u * u + v2 * v2)
        wave = 1.0 + 0.26 * np.cos(5.0 * a2 + r2.random() * 6.0)
        alpha = np.maximum(alpha, (rr < R * wave).astype(np.float32))
    alpha *= (1.0 - t) ** 0.28
    alpha = _blur(alpha, 1)
    v = np.full((c, c), 0.70, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def k_paper(i, n, c, rng):
    """Flat rectangular paper -- a fold in the middle (two-tone)."""
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    tone = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(7):
        r2 = _rng(35000 + k)
        angle0 = r2.random() * math.tau
        speed = 0.12 + 0.24 * r2.random()
        x = (0.5 + math.cos(angle0) * speed * t) * c
        y = (0.5 + math.sin(angle0) * speed * t + 0.10 * t * t) * c
        spin = angle0 + t * (2.0 + 3.0 * r2.random())
        L = c * (0.050 + 0.028 * r2.random())
        W = L * (0.62 + 0.24 * r2.random())
        u = (xx - x) * math.cos(spin) + (yy - y) * math.sin(spin)
        v2 = -(xx - x) * math.sin(spin) + (yy - y) * math.cos(spin)
        inside = (np.abs(u) < L) & (np.abs(v2) < W)
        alpha = np.maximum(alpha, inside.astype(np.float32))
        # fold line: one half darker -- the paper reads as folded
        tone = np.where(inside & (v2 > 0), 0.62, tone)
        tone = np.where(inside & (v2 <= 0), 0.95, tone)
    alpha *= (1.0 - t) ** 0.22
    alpha = _blur(alpha, 1)
    v = np.where(tone > 0, tone, 0.85).astype(np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def k_ash(i, n, c, rng):
    """Very small irregular ash flecks -- fallout. Dense and fine."""
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    # ⛔ In the first two versions 34 flecks x 0.004-0.017c radius: on the contact
    #    sheet the frame looked EMPTY. The reason is not the count but the SIZE --
    #    every particle draws the WHOLE sprite, 34 micro dots vanish when the
    #    scale drops. Few and large is right.
    for k in range(7):
        r2 = _rng(36000 + k)
        x = r2.random() * c
        y = (r2.random() * 0.8 + 0.35 * t) % 1.0 * c
        # ⛔ In the first version rr=0.004c and the multiplier was 0.5: on the contact
        #    sheet the frame looked COMPLETELY EMPTY. Ash must be fine but VISIBLE.
        rr = c * (0.022 + 0.020 * r2.random())
        d = ((xx - x) ** 2 + (yy - y) ** 2 * (1.0 + 0.8 * r2.random())) / (rr * rr)
        alpha = np.maximum(alpha, np.clip(1.0 - d, 0, 1) ** 0.5 * (0.75 + 0.25 * r2.random()))
    alpha = _blur(alpha, 1)
    v = np.full((c, c), 0.58, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def k_drop(i, n, c, rng):
    """Teardrop-shaped drop -- pointed top, round bottom."""
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(3):
        r2 = _rng(37000 + k)
        x = (0.18 + 0.64 * r2.random()) * c
        y = (0.12 + 0.62 * r2.random() + 0.24 * t) * c
        R = c * (0.032 + 0.020 * r2.random())
        u = (xx - x) / R
        v2 = (yy - y) / R
        # drop: circle below, narrowing tail above
        width = np.where(v2 < 0, np.clip(1.0 + v2 * 0.85, 0, 1) ** 1.8, 1.0)
        d = u * u / np.maximum(width * width, 1e-4) + v2 * v2
        alpha = np.maximum(alpha, np.clip(1.4 - d, 0, 1) ** 0.55)
    alpha = _blur(alpha, 1)
    v = np.full((c, c), 0.86, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def k_flare(i, n, c, rng):
    """Structureless soft glow -- neutral so the tint gives the colour ENTIRELY."""
    t = i / max(n - 1, 1)
    r = _radial(c)
    radius = 0.32 + 0.34 * t
    alpha = np.clip(1.0 - r / radius, 0, 1) ** 2.4
    alpha *= (1.0 - t) ** 0.85
    alpha = _blur(alpha, 1 + int(c * 0.008))
    core = np.clip(1.0 - r / (radius * 0.35), 0, 1)
    v = np.clip(0.66 + 0.34 * core, 0, 1).astype(np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def k_arc_straight(i, n, c, rng):
    """A SINGLE zigzag line -- a straight arc without forks. Clearly separate from `electric`."""
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    r2 = _rng(38000 + int(t * 97))
    # zigzag from top centre to bottom centre
    N = 9
    px = [0.5 * c]
    py = [0.06 * c]
    for s in range(1, N + 1):
        px.append((0.5 + (r2.random() - 0.5) * 0.34) * c)
        py.append((0.06 + 0.88 * s / N) * c)
    for s in range(N):
        x0, y0, x1, y1 = px[s], py[s], px[s + 1], py[s + 1]
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy + 1e-6
        h = np.clip(((xx - x0) * vx + (yy - y0) * vy) / L2, 0, 1)
        d = np.sqrt((xx - x0 - h * vx) ** 2 + (yy - y0 - h * vy) ** 2)
        alpha = np.maximum(alpha, np.clip(1.0 - d / (c * 0.010), 0, 1) ** 1.3)
    alpha *= (1.0 - t) ** 1.8
    alpha = _blur(alpha, 1)
    v = np.full((c, c), 0.94, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def k_ring_organic(i, n, c, rng):
    """Rough ORGANIC ring -- infection wave.

    Reference: the infection ring the user had ChatGPT generate
    (ptfx_referans_gorseller/, the reference image folder). Not a clean circle:
    the radius is distorted by noise and fog fibres spill outward from the edge.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    dx = (xx / c - 0.5) * 2.0
    dy = (yy / c - 0.5) * 2.0
    r = np.sqrt(dx * dx + dy * dy) + 1e-6
    angle = np.arctan2(dy, dx)
    radius = 0.10 + 0.80 * t
    # the radius undulates with the angle: organic roughness
    rough = (0.10 * np.sin(7.0 * angle + 1.7) + 0.06 * np.sin(13.0 * angle)
             + 0.05 * np.sin(23.0 * angle + 4.0))
    thick = 0.10 + 0.13 * t
    d = np.abs(r - radius * (1.0 + rough))
    alpha = np.clip(1.0 - d / thick, 0, 1) ** 1.3
    # fog fibres outward from the edge
    fibre = np.clip(1.0 - (r - radius) / (thick * 2.6), 0, 1) * (r > radius)
    texture = _fbm(c, 3, 8, _rng(41000), 0.5)
    alpha = np.clip(alpha + 0.45 * fibre * np.clip(texture - 0.45, 0, 1) * 2.0, 0, 1)
    alpha *= (1.0 - t) ** 1.0
    alpha = _blur(alpha, 1 + int(c * 0.004))
    v = np.full((c, c), 0.85, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def k_ring_arc(i, n, c, rng):
    """Sharp ring with ARC spikes bursting from its edge -- EMP/shock.

    Reference: the ChatGPT EMP ring. Thin bright circle + radial zigzag
    spikes; the exact opposite character of the organic ring.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    dx = (xx / c - 0.5) * 2.0
    dy = (yy / c - 0.5) * 2.0
    r = np.sqrt(dx * dx + dy * dy) + 1e-6
    angle = np.arctan2(dy, dx)
    radius = 0.12 + 0.78 * t
    thick = 0.05 + 0.05 * t
    alpha = np.clip(1.0 - np.abs(r - radius) / thick, 0, 1) ** 1.1
    # radial arc spikes: lines reaching outward in narrow angle windows
    spike = np.zeros_like(alpha)
    r2 = _rng(42000)
    for k in range(14):
        a0 = r2.random() * math.tau
        # ⛔ 0.01 radian ~ 1 pixel: the spikes vanished in the blur (seen).
        spread = 0.05 + 0.06 * r2.random()
        length = 0.14 + 0.22 * r2.random()
        diff = np.abs(((angle - a0 + math.pi) % math.tau) - math.pi)
        window = np.clip(1.0 - diff / spread, 0, 1)
        reach = np.clip(1.0 - (r - radius) / length, 0, 1) * (r > radius * 0.98)
        # zigzag: small angle deviation along the radius
        zig = 0.5 + 0.5 * np.sin(40.0 * r + k * 2.3)
        spike = np.maximum(spike, window * reach ** 1.2 * (0.6 + 0.4 * zig))
    alpha = np.clip(alpha + spike, 0, 1)
    alpha *= (1.0 - t) ** 1.4
    alpha = _blur(alpha, 1)
    inner = np.clip(1.0 - np.abs(r - radius) / (thick * 0.5), 0, 1)
    v = np.clip(0.72 + 0.28 * inner, 0, 1).astype(np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def _polar(c):
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    dx = (xx / c - 0.5) * 2.0
    dy = (yy / c - 0.5) * 2.0
    r = np.sqrt(dx * dx + dy * dy) + 1e-6
    return r, np.arctan2(dy, dx), dx, dy


def k_fireball(i, n, c, rng):
    """Explosion core with radial flame filaments.

    Three traits taken from the reference: (1) centre WHITE hot, (2) THIN FLAME
    FILAMENTS outward (not a plain radial falloff), (3) colour ramp
    white->yellow->orange->crimson, not one flat orange.
    """
    t = i / max(n - 1, 1)
    r, angle, dx, dy = _polar(c)
    size = 0.60 + 0.30 * t
    # filament: angle-dependent high-frequency noise, phase flowing with the radius
    g1 = _fbm(c, 4, 6, _rng(51000), 0.55)
    g2 = _fbm(c, 3, 12, _rng(51500), 0.5)
    fil = np.abs(np.cos(14.0 * angle + 9.0 * (g1 - 0.5) + 3.5 * r)) ** 1.6
    fil = 0.35 + 0.65 * fil * (0.5 + 0.9 * g2)
    body = np.clip(1.0 - r / size, 0, 1) ** 1.15
    core = np.clip(1.0 - r / (0.30 * size), 0, 1) ** 1.15
    energy = np.clip(body * fil + core * 1.2, 0, 1)
    # break the edge up with noise -- no plain circle edge left
    edge_break = np.clip((g1 - 0.08 - 0.42 * (r / size)) * 4.0, 0, 1)
    alpha = np.clip(energy * (0.55 + 0.45 * edge_break), 0, 1)
    alpha *= (1.0 - t) ** 0.8
    alpha = _blur(alpha, 1)
    # colour ramp: from energy
    e = np.clip(energy, 0, 1)
    R = np.clip(0.55 + 0.45 * e * 2.0, 0, 1)
    G = np.clip(1.55 * e - 0.08, 0, 1)
    B = np.clip(2.6 * e - 1.55, 0, 1)
    return np.dstack([R, G, B]).astype(np.float32), alpha


def k_star(i, n, c, rng):
    """Branching electric star -- moment of impact.

    Reference character: 8-10 SHARP ZIGZAG rays outward from the centre, side
    branches on each, a very bright centre. Not a plain cos^n spike but REAL
    line geometry.
    """
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)

    def line(x0, y0, x1, y1, thick):
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy + 1e-6
        h = np.clip(((xx - x0) * vx + (yy - y0) * vy) / L2, 0, 1)
        d = np.sqrt((xx - x0 - h * vx) ** 2 + (yy - y0 - h * vy) ** 2)
        return np.clip(1.0 - d / thick, 0, 1) ** 1.4

    r2 = _rng(52000)
    M = c * 0.5
    N = 9
    for k in range(N):
        a0 = k * math.tau / N + (r2.random() - 0.5) * 0.5
        length = c * (0.26 + 0.30 * r2.random()) * (0.6 + 0.7 * (1.0 - t))
        seg = 4
        px, py = M, M
        heading = a0
        for s2 in range(seg):
            step = length / seg
            nx = px + math.cos(heading) * step
            ny = py + math.sin(heading) * step
            thick = c * 0.014 * (1.0 - 0.55 * s2 / seg) + 1.0
            alpha = np.maximum(alpha, line(px, py, nx, ny, thick)
                               * (1.0 - 0.5 * s2 / seg))
            # side branch
            if s2 >= 1 and r2.random() < 0.55:
                da = heading + (0.5 + 0.5 * r2.random()) * (1 if r2.random() < 0.5 else -1)
                bx = nx + math.cos(da) * step * 0.9
                by = ny + math.sin(da) * step * 0.9
                alpha = np.maximum(alpha, line(nx, ny, bx, by, thick * 0.6) * 0.55)
            px, py = nx, ny
            heading += (r2.random() - 0.5) * 0.55
    r, angle, _, _ = _polar(c)
    core = np.clip(1.0 - r / 0.16, 0, 1) ** 1.2
    alpha = np.clip(alpha + core * 1.3, 0, 1)
    alpha *= (1.0 - t) ** 1.5
    alpha = _blur(alpha, 1)
    v = np.clip(0.62 + 0.38 * np.clip(core * 2.0 + alpha * 0.3, 0, 1), 0, 1)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def k_glass(i, n, c, rng):
    """Large faceted glass shards.

    ⛔ The first v2 used an undulating radius and the pieces came out like FLOWERS
       (petal silhouette -- seen). Glass is angular: a convex polygon, built as
       the intersection of 5-6 randomly oriented HALF-PLANES.
    """
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(4):
        r2 = _rng(53000 + k)
        angle0 = r2.random() * math.tau
        speed = 0.10 + 0.18 * r2.random()
        mx = (0.5 + math.cos(angle0) * (0.24 + speed * t)) * c
        my = (0.5 + math.sin(angle0) * (0.24 + speed * t) + 0.10 * t * t) * c
        R = c * (0.058 + 0.040 * r2.random())
        u = xx - mx
        v2 = yy - my
        corners = 5 + int(r2.random() * 2)
        # every half-plane: n·p <= distance ; distance to boundary = min(distance - n·p)
        d_in = np.full((c, c), 1e9, np.float32)
        inside = np.ones((c, c), bool)
        for e in range(corners):
            ea = e * math.tau / corners + (r2.random() - 0.5) * 0.9
            em = R * (0.55 + 0.60 * r2.random())
            proj = u * math.cos(ea) + v2 * math.sin(ea)
            inside &= proj < em
            d_in = np.minimum(d_in, em - proj)
        d_in = np.where(inside, d_in, 0.0)
        edge = np.clip(1.0 - np.abs(d_in - 0.0) / (c * 0.006), 0, 1)
        edge = np.where(inside & (d_in < c * 0.006), 1.0 - d_in / (c * 0.006), 0.0)
        facet_a = r2.random() * math.pi
        facet = np.clip(1.0 - np.abs(u * math.cos(facet_a) + v2 * math.sin(facet_a)) /
                        (c * 0.0035), 0, 1) * inside
        piece = np.maximum(edge, np.maximum(facet * 0.75, inside * 0.16))
        alpha = np.maximum(alpha, piece.astype(np.float32))
    alpha *= (1.0 - t) ** 0.30
    alpha = _blur(alpha, 1)
    v = np.full((c, c), 0.92, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alpha


def k_blood_v2(i, n, c, rng):
    """Viscous blood splash -- reference: atlas4 top right.

    Character: drops of all sizes SCATTERING outward from the centre, THIN
    THREADS (viscosity) between them, the tips of the drops pointed in the
    direction of motion. The old k_blood was only a cluster of round specks.
    """
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    M = c * 0.5
    r2 = _rng(61000)
    for k in range(22):
        a0 = r2.random() * math.tau
        speed = 0.08 + 0.30 * r2.random()
        distance = (0.06 + speed * (0.35 + 0.65 * t)) * c
        x = M + math.cos(a0) * distance
        y = M + math.sin(a0) * distance + 0.08 * t * t * c
        R = c * (0.006 + 0.020 * r2.random() * (1.0 - 0.4 * speed))
        # drop: ellipse stretched in the direction of motion
        u = (xx - x) * math.cos(a0) + (yy - y) * math.sin(a0)
        v2 = -(xx - x) * math.sin(a0) + (yy - y) * math.cos(a0)
        d = (u / (R * (1.6 + 2.0 * speed))) ** 2 + (v2 / R) ** 2
        alpha = np.maximum(alpha, np.clip(1.2 - d, 0, 1) ** 0.6)
        # viscous thread: thin line from the centre to the drop (short-lived)
        if r2.random() < 0.5 and t < 0.6:
            L2 = distance * distance + 1e-6
            h = np.clip(((xx - M) * (x - M) + (yy - M) * (y - M)) / L2, 0, 1)
            dd = np.sqrt((xx - M - h * (x - M)) ** 2 + (yy - M - h * (y - M)) ** 2)
            alpha = np.maximum(alpha, np.clip(1.0 - dd / (c * 0.0035), 0, 1)
                               * 0.7 * (1.0 - t))
    core = np.clip(1.0 - (np.sqrt((xx - M) ** 2 + (yy - M) ** 2) / (c * 0.10)), 0, 1)
    alpha = np.clip(alpha + core ** 1.5 * 0.9 * (1.0 - 0.8 * t), 0, 1)
    alpha *= (1.0 - t) ** 0.45
    alpha = _blur(alpha, 1)
    # dark red body + wet bright top
    v = np.clip(0.35 + 0.45 * alpha, 0, 1)
    return np.dstack([v, v * 0.10, v * 0.08]).astype(np.float32), alpha


def k_spark_v2(i, n, c, rng):
    """Pouring spark shower -- reference: atlas4 bottom left.

    Character: THIN BRIGHT LINES from top to bottom (motion blur feel),
    branching at the tips; lines, not specks.
    """
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    r2 = _rng(62000)

    def line(x0, y0, x1, y1, thick, strength):
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy + 1e-6
        h = np.clip(((xx - x0) * vx + (yy - y0) * vy) / L2, 0, 1)
        d = np.sqrt((xx - x0 - h * vx) ** 2 + (yy - y0 - h * vy) ** 2)
        return np.clip(1.0 - d / thick, 0, 1) ** 1.5 * strength

    for k in range(26):
        x0 = (0.34 + 0.32 * r2.random()) * c
        y0 = 0.04 * c + r2.random() * 0.10 * c
        side = (r2.random() - 0.5) * 0.55
        length = (0.25 + 0.55 * r2.random()) * c * (0.4 + 0.6 * t)
        x1 = x0 + side * length
        y1 = y0 + length
        thick = c * (0.0016 + 0.0022 * r2.random())
        alpha = np.maximum(alpha, line(x0, y0, x1, y1, thick, 0.75 + 0.25 * r2.random()))
        if r2.random() < 0.4:
            dx2 = (r2.random() - 0.5) * 0.3 * length
            alpha = np.maximum(alpha, line(x1, y1, x1 + dx2, y1 + 0.22 * length,
                                           thick * 0.7, 0.5))
    alpha *= (1.0 - t) ** 0.9
    alpha = _blur(alpha, 1)
    v = np.clip(0.75 + 0.25 * alpha, 0, 1)
    return np.dstack([v, v * 0.72, v * 0.38]).astype(np.float32), alpha


def k_fire_v2(i, n, c, rng):
    """Vertical FLAME TONGUES -- reference: atlas4 top left.

    Character: tongues licking up from the base, thinning and breaking off at
    the tip; white-hot base, yellow body, orange-crimson tip. NOT a plain radial
    smudge: vertical flow + a silhouette that narrows with HEIGHT, not with angle.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    u = xx / c                      # 0..1 horizontal
    h = 1.0 - yy / c                # 0 = base, 1 = top

    # vertically flowing noise: slides up over the frames (the flame climbs)
    g = _fbm(c, 4, 4, _rng(71000), 0.58)
    shift = int((0.45 + 0.55 * t) * c) % max(c, 1)
    g = np.roll(g, -shift, axis=0)
    g2 = _fbm(c, 3, 9, _rng(71500), 0.5)
    g2 = np.roll(g2, -int(shift * 1.6) % max(c, 1), axis=0)

    # silhouette: wide at the base, narrow at the top; the edge is licked by noise
    height = 0.55 + 0.40 * t
    width = 0.34 * np.clip(1.0 - (h / height) ** 1.5, 0, 1)
    # tongue: horizontal position twisted by noise -> licking feel
    twist = (g - 0.5) * 0.30 * np.clip(h / max(height, 1e-3), 0, 1)
    d = np.abs((u - 0.5) + twist)
    body = np.clip(1.0 - d / np.maximum(width, 1e-4), 0, 1)

    # break-off at the top: the threshold rises with height -> tongues separate
    threshold = 0.22 + 0.42 * np.clip(h / max(height, 1e-3), 0, 1)
    tongue = np.clip((0.55 * g + 0.45 * g2 - threshold) / 0.22, 0, 1)
    alpha = np.clip(body ** 0.85 * (0.35 + 0.85 * tongue), 0, 1)
    alpha *= np.clip(h / 0.06, 0, 1)          # cut the base
    alpha *= (1.0 - t) ** 0.45
    alpha = _blur(alpha, 1)

    # colour: by height and density white -> yellow -> orange -> crimson
    heat = np.clip(body * (1.0 - h / max(height, 1e-3)) * 1.6, 0, 1)
    R = np.clip(0.70 + 0.30 * heat * 2.0, 0, 1)
    G = np.clip(0.18 + 1.05 * heat, 0, 1)
    B = np.clip(1.9 * heat - 1.05, 0, 1)
    return np.dstack([R, G, B]).astype(np.float32), alpha


def k_concrete_v2(i, n, c, rng):
    """Angular CHUNKY concrete blocks.

    ⛔ The old version used an undulating radius `1 + 0.26*cos(5a)` and gave a
       FLOWER silhouette (seen on the contact sheet -- the same bug fixed in
       glass). Convex polygon = intersection of 5-6 randomly oriented half-planes.
    """
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    tone = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(5):
        r2 = _rng(72000 + k)
        angle0 = r2.random() * math.tau
        spread = 0.22 + 0.12 * r2.random()
        speed = 0.14 + 0.24 * r2.random()
        mx = (0.5 + math.cos(angle0) * (spread + speed * t)) * c
        my = (0.5 + math.sin(angle0) * (spread + speed * t) + 0.20 * t * t) * c
        R = c * (0.034 + 0.026 * r2.random())
        u = xx - mx
        v2 = yy - my
        corners = 5 + int(r2.random() * 2)
        inside = np.ones((c, c), bool)
        d_in = np.full((c, c), 1e9, np.float32)
        for e in range(corners):
            ea = e * math.tau / corners + (r2.random() - 0.5) * 0.8
            em = R * (0.60 + 0.55 * r2.random())
            proj = u * math.cos(ea) + v2 * math.sin(ea)
            inside &= proj < em
            d_in = np.minimum(d_in, em - proj)
        block = inside.astype(np.float32)
        alpha = np.maximum(alpha, block)
        # lit face / shaded face: sense of volume
        light = np.clip(0.55 + 0.45 * np.cos(np.arctan2(v2, u) - 0.9), 0, 1)
        tone = np.where(inside, light, tone)
    alpha *= (1.0 - t) ** 0.28
    alpha = _blur(alpha, 1)
    v = np.where(tone > 0, 0.42 + 0.52 * tone, 0.60).astype(np.float32)
    return np.dstack([v, v * 0.98, v * 0.95]).astype(np.float32), alpha


def k_spark_burst(i, n, c, rng):
    """Sparks spraying OUTWARD from the centre -- friction / metal tearing.

    Deliberately different from `k_spark_v2` (shower): there the lines pour
    down, here they fly out RADIALLY from the CENTRE and curl down with gravity.
    """
    t = i / max(n - 1, 1)
    alpha = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    M = c * 0.5
    r2 = _rng(73000)

    def line(x0, y0, x1, y1, thick, strength):
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy + 1e-6
        h = np.clip(((xx - x0) * vx + (yy - y0) * vy) / L2, 0, 1)
        d = np.sqrt((xx - x0 - h * vx) ** 2 + (yy - y0 - h * vy) ** 2)
        return np.clip(1.0 - d / thick, 0, 1) ** 1.5 * strength

    for k in range(24):
        a0 = r2.random() * math.tau
        speed = (0.10 + 0.26 * r2.random())
        # trail: from the start to the current position; curls down with gravity
        t0 = max(0.0, t - 0.16)
        def position(tt):
            x = M + math.cos(a0) * speed * tt * c * 2.0
            y = M + math.sin(a0) * speed * tt * c * 2.0 + 0.55 * tt * tt * c
            return x, y
        x0, y0 = position(t0)
        x1, y1 = position(t)
        thick = c * (0.0018 + 0.0022 * r2.random())
        alpha = np.maximum(alpha, line(x0, y0, x1, y1, thick,
                                       0.7 + 0.3 * r2.random()))
    core = np.clip(1.0 - np.sqrt((xx - M) ** 2 + (yy - M) ** 2) / (c * 0.06), 0, 1)
    alpha = np.clip(alpha + core ** 1.4 * (1.0 - t) * 0.9, 0, 1)
    alpha *= (1.0 - t) ** 0.8
    alpha = _blur(alpha, 1)
    v = np.clip(0.72 + 0.28 * alpha, 0, 1)
    return np.dstack([v, v * 0.70, v * 0.34]).astype(np.float32), alpha


def single_object(rgba, margin=0.06):
    """Keeps the LARGEST object, crops tightly, fills the frame.

    ⛔ TWO MEASURED RULES:

    1) ONE OBJECT PER SPRITE. Vanilla's debris atlases have **1 object** per
       cell (measured: multi_sheet_002/003/004 and fine_debris_sheet 1,
       glass_dots 2). Ours had 3-6 (concrete 5, rubble 6, glass 4). Because
       every particle draws the WHOLE sprite, 15 particles = a tangle of 75
       pieces -- a crowd, not "debris".

    2) TIGHT CROP. "Alpha coverage of a particle sprite is one of the most
       underestimated sources of performance" (VFXDoc): an empty margin is both
       wasted fill and makes the particle look small. The object must fill the
       frame, with only a margin for the edge fade around it.
    """
    a = rgba[..., 3]
    m = a > 0.12
    if not m.any():
        return rgba
    # ---- find the largest connected component (labelling, no recursion) ----
    H, W = m.shape
    labels = np.zeros((H, W), np.int32)
    n = 0
    best, best_size = 0, 0
    for y0 in range(H):
        row = m[y0]
        for x0 in range(W):
            if not row[x0] or labels[y0, x0]:
                continue
            n += 1
            stack = [(y0, x0)]
            labels[y0, x0] = n
            size = 0
            while stack:
                cy, cx = stack.pop()
                size += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < H and 0 <= nx < W and m[ny, nx] and not labels[ny, nx]:
                        labels[ny, nx] = n
                        stack.append((ny, nx))
            if size > best_size:
                best_size, best = size, n
    if best == 0:
        return rgba
    keep = (labels == best)
    out = rgba.copy()
    out[..., 3] = np.where(keep, a, 0.0)

    # ---- tight crop + scale up to the frame ----
    ys, xs = np.where(keep)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    kh, kw = y1 - y0, x1 - x0
    k = max(kh, kw)
    k = int(k * (1.0 + 2.0 * margin))
    cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
    ty0, tx0 = cy - k // 2, cx - k // 2
    square = np.zeros((k, k, 4), np.float32)
    sy0, sx0 = max(0, ty0), max(0, tx0)
    sy1, sx1 = min(H, ty0 + k), min(W, tx0 + k)
    square[sy0 - ty0:sy1 - ty0, sx0 - tx0:sx1 - tx0] = out[sy0:sy1, sx0:sx1]
    # scale back to the original resolution
    yi = (np.arange(H) + 0.5) * (k / float(H)) - 0.5
    i0 = np.clip(np.floor(yi).astype(np.int32), 0, k - 1)
    i1 = np.clip(i0 + 1, 0, k - 1)
    f = np.clip(yi - i0, 0, 1)[:, None, None]
    mid = square[i0] * (1 - f) + square[i1] * f
    f2 = np.clip(yi - i0, 0, 1)[None, :, None]
    result = mid[:, i0] * (1 - f2) + mid[:, i1] * f2
    result = result.astype(np.float32)
    # ⛔ SCALING UP ALSO SCALES UP THE BLUR. A 1-2 pixel blur applied to a small
    #    object becomes a spread-out smudge when scaled up 4-6 times
    #    (seen: concrete SINGLE_OBJECT came out mushy). Pass alpha through a
    #    steep curve to regain edge sharpness.
    scale_factor = k / float(H)
    if scale_factor > 1.6:
        a2 = result[..., 3]
        mid_point = 0.42
        steep = 1.0 + 1.6 * min(scale_factor / 4.0, 1.0)
        result[..., 3] = np.clip((a2 - mid_point) * (1.0 + 2.4 * steep) + mid_point, 0, 1)
    result[..., 3] *= _edge_mask(H, margin=0.04)
    return np.clip(result, 0, 1)


# ⛔ These families must have ONE OBJECT PER SPRITE (vanilla measurement: 1 object
#    per cell in debris atlases). Drawing a cluster produces a tangle of 75 pieces
#    with 15 particles.
# ⚠ `fly` and `ember` are NOT IN THE LIST: both are by nature SMALL and many;
#   scaling up a single grain gives a shapeless smudge (seen).
SINGLE_OBJECT = {"debris", "concrete", "glass", "wood", "paper", "ash", "drop",
                 "leaf", "splash", "bubble"}

FAMILIES = {
    "smoke": k_smoke, "fire": k_fire_v2, "fireball": k_fireball,
    "dust": k_dust, "steam": k_steam, "spark": k_spark_v2,
    "splash": k_splash, "ember": k_ember, "fog": k_fog,
    "bubble": k_bubble, "debris": k_debris, "ring": k_ring,
    "electric": k_electric, "blood": k_blood_v2, "leaf": k_leaf,
    "ring_organic": k_ring_organic, "ring_arc": k_ring_arc,
    "star": k_star, "fly": k_fly, "glass": k_glass, "wood": k_wood,
    "concrete": k_concrete_v2, "spark_burst": k_spark_burst, "paper": k_paper, "ash": k_ash, "drop": k_drop,
    "flare": k_flare, "arc_straight": k_arc_straight,
}

# old Turkish family names still accepted (command line and library callers)
FAMILY_ALIASES = {
    "duman": "smoke", "ates": "fire", "alev_topu": "fireball", "toz": "dust",
    "buhar": "steam", "kivilcim": "spark", "sicrama": "splash", "kor": "ember",
    "sis": "fog", "kabarcik": "bubble", "parca": "debris", "halka": "ring",
    "elektrik": "electric", "kan": "blood", "yaprak": "leaf",
    "halka_organik": "ring_organic", "halka_ark": "ring_arc", "yildiz": "star",
    "sinek": "fly", "cam": "glass", "tahta": "wood", "beton": "concrete",
    "kivilcim_patlama": "spark_burst", "kagit": "paper", "kul": "ash",
    "damla": "drop", "parlama": "flare", "ark_duz": "arc_straight",
}


# ----------------------------------------------------------------- driver

# ALPHA PEAK target per family.
#
# ⛔ OUR SHEETS NEVER REACHED OPACITY. Measured: the alpha peak of our 15 families
# was between 0.30-0.47, that of vanilla smoke sheets 0.59-0.97.
# The symptom in game: "the effect is not as dense as the reference" -- the effect
# is not wrong, it is just not opaque enough anywhere. The cause is not in one
# place: edge mask, blur and the life-fade multiplier stack up and crush the
# peak. Instead of fiddling with each family, the peak is scaled to the target
# AFTER the sheet is generated.
#
# Targets taken from the vanilla counterpart (alpha peak):
#   ptfx_smoke_new_plumes 0.93 · billow 0.97 · wispy 0.74
#   ptfx_smoke_thin 0.71 · ptfx_steam 0.59
ALPHA_PEAK = {
    "smoke": 0.93, "fire": 0.95, "fireball": 0.97, "dust": 0.85,
    "steam": 0.62, "spark": 1.00, "splash": 0.95, "ember": 1.00,
    "fog": 0.58, "bubble": 0.90, "debris": 1.00, "ring": 0.92,
    "electric": 1.00, "blood": 0.95, "leaf": 1.00,
    "ring_organic": 0.92, "ring_arc": 1.00,
    "star": 1.00, "fly": 0.90, "glass": 1.00, "wood": 1.00,
    "concrete": 1.00, "spark_burst": 1.00, "paper": 1.00, "ash": 0.80, "drop": 0.95,
    "flare": 0.92, "arc_straight": 1.00,
}


def _visible(alpha):
    """VISIBLE coverage ratio of the frame (0..1).

    ⛔ THE MEASUREMENT IS MADE ON THE DATA THAT IS SENT. If alpha is measured as
    a float, 0.0201 counts as "filled"; but `write_png()` rounds to uint8
    (0.0201 -> 5 -> 0.0196) and the frame that is sent drops BELOW the threshold.
    Measured: `smoke` frame 63 and `fog` frame 0 passed the gate as "filled"
    and came out completely empty in the PNG - two rounds were wasted. Look at
    the quantised value, not the float.
    """
    q = np.floor(np.clip(alpha, 0, 1) * 255.0 + 0.5) / 255.0
    return float((q > 0.02).mean())


def _edge_mask(cell, margin=0.045):
    """Soft fade mask at the cell edge.

    ⛔ If a flipbook frame touches the cell edge, in game a HARD CUT shows at
    the sprite quad boundary - in all vanilla sheets the frames sit inside a
    transparent border. Measured: `fire` touched the edge at 0.44 alpha,
    `smoke`/`spark` were clean at 0.00.
    """
    p = max(2, int(cell * margin))
    d = np.minimum(np.arange(cell), np.arange(cell)[::-1]).astype(np.float32)
    q = np.clip(d / p, 0.0, 1.0)
    q = q * q * (3.0 - 2.0 * q)          # smoothstep
    return np.minimum(q[:, None], q[None, :])


def sheet(family, frames=36, resolution=1024, seed=0):
    """Generates a square-grid flipbook -> RGBA numpy (resolution, resolution, 4), 0..1.

    ⛔ `frames` must be a PERFECT SQUARE (4/16/36/64); the engine splits the grid with sqrt.
    """
    family = FAMILY_ALIASES.get(family, family)
    k = int(round(math.sqrt(frames)))
    if k * k != frames:
        raise ValueError("frame count must be a perfect square (4, 16, 25, 36, 49): %d" % frames)
    # ⛔ THE VANILLA CEILING FOR THE FRAME COUNT IS 49. 781 AnimateTexture were
    # measured in core.ypt: `Unknown_C4h` max 49 (50 frames), zero rules with
    # C4 > 63. 64 frames were tried; the engine did NOT apply the grid AT ALL and
    # every sprite drew the whole sheet in a single frame (verified in game).
    if frames > 49:
        raise ValueError(
            "frame count %d is outside the vanilla band (measured max 50). "
            "The engine does not apply the grid, it draws the whole sheet. "
            "Use 36 (6x6) or 49 (7x7)." % frames)
    if family not in FAMILIES:
        raise KeyError("no family '%s'. Valid: %s" % (family, ", ".join(sorted(FAMILIES))))
    cell = resolution // k
    fn = FAMILIES[family]
    edge = _edge_mask(cell)

    def generate(t0, t1):
        """Spreads the frames over the t range [t0, t1].

        The family functions compute `t = i / (n - 1)`; we cannot pass t directly.
        The same result comes from `n` and an `offset` shift:
            (n - 1) = (frames - 1) / (t1 - t0)      and      offset = t0 * (n - 1)
        `offset` is rounded to an INTEGER: some families also use `i` in the
        random seed (`_rng(2600 + i * 3)`), a fractional index is meaningless there.

        ⛔ THE rng MUST BE ONE PER PASS, not per frame. Creating a new
        `_rng(seed)` per frame gives every frame THE SAME random sequence and the
        frames come out identical (a still sprite).
        """
        n1 = (frames - 1) / max(t1 - t0, 1e-3)
        offset = int(round(t0 * n1))
        rng = _rng(seed)
        kk, spill = [], 0.0
        for i in range(frames):
            rgb, alpha = fn(i + offset, n1 + 1.0, cell, rng)
            alpha = np.clip(alpha, 0, 1)
            spill = max(spill, float(max(alpha[:, :2].max(), alpha[:, -2:].max(),
                                         alpha[:2].max(), alpha[-2:].max())))
            kk.append((rgb, alpha * edge))
        return kk, spill

    # Pass 1: t range [0, (frames-1)/frames]. THE UPPER END CANNOT BE 1.0 - the
    # `(1 - t) ** k` fade multiplier in every family gives exactly ZERO at t = 1
    # and the last frame comes out COMPLETELY EMPTY. `Unknown_C4h = frames - 1`
    # makes the engine draw that frame too, so the effect "blinks" one frame
    # every loop. Measured: frame 63 was empty in 15 of 15 families.
    upper = (frames - 1) / float(frames)
    kk, spill = generate(0.0, upper)

    # Pass 2: if there are empty head/tail frames the t range is NARROWED.
    # Even after the fade multiplier was fixed empty frames remained, and the
    # cause was not the multiplier but the family's OWN envelope: `ring` leaves
    # the frame, `fog` peaks at t=0.5 and fades to both sides (7 empty frames at
    # the head), `bubble` starts its first bubble with a delay. An empty frame is
    # both waste and makes the effect vanish for a moment. The range is rebuilt
    # from the measured first/last filled frame - not a guess, a correction that
    # measures its own output.
    #
    # ⛔ ONE PASS DOES NOT CONVERGE. Narrowing the range from the first
    # measurement can drop the new boundary frames to zero again - measured:
    # `ring` went from 1 empty frame to 1 empty frame in one pass, `fog` went from
    # 7 to 2 but not to zero. The range is pushed inward UNTIL NO EMPTY FRAME REMAINS.
    t0, t1 = 0.0, upper
    for _round in range(6):
        filled = [_visible(a) for _, a in kk]
        present = [n for n, d in enumerate(filled) if d > 0.002]
        if not present:
            break
        if present[0] == 0 and present[-1] == frames - 1:
            break                                   # no empty frame
        step = (t1 - t0) / max(frames - 1, 1)
        y0 = t0 + present[0] * step
        y1 = t0 + present[-1] * step
        # push one step INWARD: the boundary frame must not sit on the exact zero point
        pad = (y1 - y0) * 0.02
        y0, y1 = y0 + pad, y1 - pad
        if y1 - y0 < 0.05:
            break
        t0, t1 = y0, y1
        kk, spill = generate(t0, t1)

    # Last gate: frames still empty AFTER fitting are filled from their neighbours.
    #
    # Range narrowing closes empty ends but does not always converge and never
    # touches a gap in the MIDDLE. Measured, three separate causes: `smoke` at the
    # tail (its own envelope goes to zero), `fog` at the head (symmetric envelope
    # peaking at t=0.5), `dust` in the MIDDLE at frame 11 - its neighbours 2.4%
    # and 5.4% while itself 0%. A gap in the middle is not a fitting problem but
    # the generator dropping a frame, and in game it is a visible flicker. The
    # patch is visual, it does not hide the cause: how many frames were filled is reported.
    threshold = 0.0005
    filled = [_visible(a) for _, a in kk]
    present = [n for n, d in enumerate(filled) if d > threshold]
    patched = 0
    if present:
        for n in range(frames):
            if filled[n] > threshold:
                continue
            prev = max((v for v in present if v < n), default=None)
            nxt = min((v for v in present if v > n), default=None)
            if prev is None and nxt is None:
                continue
            if prev is None:
                kk[n] = (kk[nxt][0].copy(), kk[nxt][1].copy())
            elif nxt is None:
                kk[n] = (kk[prev][0].copy(), kk[prev][1].copy())
            else:
                w = (n - prev) / float(nxt - prev)
                r0, a0 = kk[prev]
                r1, a1 = kk[nxt]
                kk[n] = (r0 * (1 - w) + r1 * w, a0 * (1 - w) + a1 * w)
            patched += 1
    if patched:
        print("NOTE: %s %d empty frames filled from their neighbours"
              % (family, patched), file=sys.stderr)

    # ⛔ THE GRID DOES NOT HAVE TO DIVIDE THE TEXTURE EXACTLY. That requirement WAS
    # WRONG and was the reason for moving to 64 frames: vanilla `ptfx_smoke_wispy_anim`
    # is 7x7 on 1024x1024 (1024/7 = 146.29). The engine samples in UV space in
    # 1/k steps, it does not look for pixel alignment. Cell content is generated
    # at `cell` size, corners are rounded to the FRACTIONAL boundary; the remaining
    # sub-pixel margin is already transparent thanks to the edge mask.
    # Scale the alpha peak to the family target. The criterion is not the MAXIMUM
    # but the 99.7th percentile: a single outlier pixel would fade the whole sheet.
    target = ALPHA_PEAK.get(family)
    if target:
        pool = np.concatenate([a.ravel() for _, a in kk])
        peak = float(np.percentile(pool, 99.7))
        if peak > 1e-4:
            scale = target / peak
            kk = [(rgb, np.clip(a * scale, 0.0, 1.0)) for rgb, a in kk]

    out = np.zeros((resolution, resolution, 4), np.float32)
    for i, (rgb, alpha) in enumerate(kk):
        sy = int(round((i // k) * resolution / float(k)))
        sx = int(round((i % k) * resolution / float(k)))
        out[sy:sy + cell, sx:sx + cell, :3] = rgb
        out[sy:sy + cell, sx:sx + cell, 3] = alpha
    if spill > 0.35:
        # The mask softens the spill but does not hide it: content spilling this
        # much DOES NOT FIT the cell and must be shrunk at its source.
        print("WARNING: %s touches the cell edge with alpha %.2f (shrink the source)"
              % (family, spill), file=sys.stderr)
    return out

def neutralize(rgba):
    """Reduces RGB to brightness, keeps alpha -- so the TINT takes.

    ⛔ The engine applies colour as a MULTIPLICATION (`ptxu_Colour` RGB). Multiplying
       an orange sprite by blue does not give blue: the sprite's blue channel is
       0.09, the multiplication cannot bring it back. Measured (alpha-weighted
       average x tint):

         cherenkov      ember sprite, blue tint     -> hue drift **118°**
         magic_gather   ember,        blue          -> **165°**
         magic_bolt     ember,        blue          -> **156°**
         teleport       ember,        lavender      -> **129°**
         magic_impact   fireball,     lavender      -> **109°**
         healing_aura   ember,        mint green    -> **91°**
         arc_impact     fireball,     white         -> **177°**
         hot_spot       ember,        yellow-green  -> **33°**

       On a neutral (grey) sprite the hue comes ENTIRELY from the tint, drift is 0.
       Shape and density are kept in the brightness.

    Coefficients are Rec.709 luma; they keep perceived brightness, a channel
    average would suppress green.
    """
    y = (0.2126 * rgba[..., 0] + 0.7152 * rgba[..., 1] + 0.0722 * rgba[..., 2])
    out = rgba.copy()
    out[..., 0] = y
    out[..., 1] = y
    out[..., 2] = y
    return out


def single_frame(family, resolution=512, t=0.45, seed=0, neutral=False, single=False):
    """Generates a SINGLE frame -- NO flipbook.

    ⛔ SHEET SLICING DOES NOT WORK IN A CUSTOM `.ypt`. Measured in game with the
    numbered diagnostic sheet: at 4x4 ALL of 1..16, at 7x7 ALL of 1..49 are seen
    at once in a single particle. The grid size makes no difference; 2x2
    "appearing to work" was an illusion (4 puffs at a small scale read as
    smoke). Vanilla uses 7x7 in its own `core.ypt` and it works, but the same
    structure does not work in a streamed file -- the cause was not solved.

    Fix: drop the sheet. 955 of vanilla's 1736 particle rules already do NOT
    CARRY `AnimateTexture`; motion comes from size/colour/speed curves. This
    function generates the frame at moment `t` of the family's life on its own,
    at full resolution.
    """
    family = FAMILY_ALIASES.get(family, family)
    if family not in FAMILIES:
        raise KeyError("no family '%s'" % family)
    fn = FAMILIES[family]
    rng = _rng(seed)
    # to pass t directly: fn computes `t = i/(n-1)` -> i=1, n=1+1/t
    n1 = 1.0 + 1.0 / max(t, 1e-3)
    rgb, alpha = fn(1, n1, resolution, rng)
    alpha = np.clip(alpha, 0, 1) * _edge_mask(resolution, margin=0.03)
    target = ALPHA_PEAK.get(family)
    if target:
        peak = float(np.percentile(alpha, 99.7))
        if peak > 1e-4:
            alpha = np.clip(alpha * (target / peak), 0.0, 1.0)
    out = np.zeros((resolution, resolution, 4), np.float32)
    out[..., :3] = rgb
    out[..., 3] = alpha
    if single:
        out = single_object(out)
    if neutral:
        out = neutralize(out)
    return out


def write_png(rgba, path):
    a = (np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(a, "RGBA").save(path)
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("family", nargs="?", help="effect family",
                    type=lambda v: FAMILY_ALIASES.get(v, v))
    ap.add_argument("out", nargs="?", help="PNG output path")
    ap.add_argument("--frames", "--kare", dest="frames", type=int, default=36,
                    help="frame count, must be a PERFECT SQUARE (4/16/36/64)")
    ap.add_argument("--resolution", "--coz", dest="resolution", type=int, default=1024,
                    help="sheet resolution")
    ap.add_argument("--seed", "--tohum", dest="seed", type=int, default=0)
    ap.add_argument("--single", "--tek", dest="single", type=float, default=None, metavar="T",
                    help="generate a single frame INSTEAD of a flipbook (moment T of the life, 0..1)")
    ap.add_argument("--neutral", "--notr", dest="neutral", action="store_true",
                    help="reduce RGB to brightness -- let the engine's tint give the colour")
    ap.add_argument("--list", "--liste", dest="list", action="store_true")
    a = ap.parse_args()
    if a.list or not a.family:
        print("families: " + ", ".join(sorted(FAMILIES)))
        return 0
    if not a.out:
        print("output path required", file=sys.stderr)
        return 2
    if a.single is not None:
        r = single_frame(a.family, a.resolution, a.single, a.seed, a.neutral)
    else:
        r = sheet(a.family, a.frames, a.resolution, a.seed)
    write_png(r, a.out)
    filled = float((r[..., 3] > 0.02).mean())
    print("%s -> %s  %dx%d  %d frames  filled=%.1f%%"
          % (a.family, a.out, a.resolution, a.resolution, a.frames, filled * 100))
    if filled < 0.005:
        print("WARNING: sheet almost empty", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
