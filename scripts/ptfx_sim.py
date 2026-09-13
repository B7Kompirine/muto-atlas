#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_sim.py — SIMULATES a `.ypt` effect and writes an animated GIF.

⛔ BE CLEAR ABOUT WHAT THIS IS: it is NOT the engine itself, it is a MODEL
   that plays back the documented meaning of the engine's fields. A strong
   proxy, not hard proof -- the game has the last word.

   But it catches what a file-level check cannot: while the check said
   "71/71 chains intact", 38 effects were invisible in the game. This
   simulation would have shown that failure on screen.

Fields it plays back (all measured in this session):
  ptxCreationDomain:m_sizeOuterKFP  -> volume the particles spawn in (m)
  ptxTargetDomain:m_positionKFP     -> direction x distance (path travelled over the lifetime)
  ptxu_Acceleration:m_xyzMinKFP     -> acceleration (m/s^2)
  ptxu_Dampening:m_xyzMinKFP        -> damping (0..1, fraction kept per second)
  ptxu_Size:m_whdMinKFP x sizeScalar -> particle size (m)
  ptxu_Colour:m_rgbaMinKFP          -> color + ALPHA ENVELOPE (over the lifetime)
  m_spawnRateOverTimeKFP / m_particleLifeKFP -> rate and lifetime

Usage:
  python ptfx_sim.py <ypt.xml> <effect_name> --out out.gif
"""
from __future__ import annotations

import argparse
import io
import math
import os
import random
import re
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptfx_quality_gate import iter_blocks, kfp, kfp_body, kfp_envelope  # noqa: E402


def v3(block, name, default=(0.0, 0.0, 0.0)):
    body = kfp_body(block, name)
    if body is None:
        return list(default)
    v = re.findall(r"<(?:Red|Green|Blue)ChannelColour value=\"([-0-9.eE]+)\"", body)
    return [float(x) for x in v[:3]] if len(v) >= 3 else list(default)


def color_rgb(block):
    body = kfp_body(block, "ptxu_Colour:m_rgbaMinKFP")
    if body is None:
        return (1.0, 1.0, 1.0)
    v = re.findall(r"<RedChannelColour value=\"([-0-9.eE]+)\" />\s*"
                   r"<GreenChannelColour value=\"([-0-9.eE]+)\" />\s*"
                   r"<BlueChannelColour value=\"([-0-9.eE]+)\" />", body)
    return tuple(float(x) for x in v[0]) if v else (1.0, 1.0, 1.0)


def curve_value(envelope, t):
    """Linear interpolation of the value at time t from a (time, value) list."""
    if not envelope:
        return 1.0
    if t <= envelope[0][0]:
        return envelope[0][1]
    for i in range(1, len(envelope)):
        if t <= envelope[i][0]:
            t0, v0 = envelope[i - 1]
            t1, v1 = envelope[i]
            f = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
            return v0 + (v1 - v0) * f
    return envelope[-1][1]


class Layer:
    """One emitter+particle pair. A multi-emitter effect is made of these."""

    def __init__(self, emb, prb, xml_path, delay=0.0, scale=1.0):
        self.em, self.pr = emb, prb
        self.delay, self.layer_scale = delay, scale

        r = kfp(self.em, "m_spawnRateOverTimeKFP") or (10.0, 10.0)
        l = kfp(self.em, "m_particleLifeKFP") or (2.0, 2.0)
        sc = kfp(self.em, "m_sizeScalarKFP") or (100.0, 100.0)
        self.rate = (r[0] + r[1]) / 2.0
        self.lifetime = (l[0], l[1])
        self.spawn = v3(self.em, "ptxCreationDomain:m_sizeOuterKFP", (0.2,) * 3)
        self.target = v3(self.em, "ptxTargetDomain:m_positionKFP", (0, 0, 0.5))
        self.target_size = v3(self.em, "ptxTargetDomain:m_sizeOuterKFP", (0, 0, 0))
        self.accel = v3(self.pr, "ptxu_Acceleration:m_xyzMinKFP", (0, 0, 0))
        self.damping = v3(self.pr, "ptxu_Dampening:m_xyzMinKFP", (0, 0, 0))
        w = v3(self.pr, "ptxu_Size:m_whdMinKFP", (0.3,) * 3)
        self.size = max(w) * max(sc[1], 1.0) / 100.0 * self.layer_scale
        # ⛔ ONE SHOT: `Unknown628` on the emitter. 1 means it emits once,
        #    0 means it keeps emitting. Without modelling it an impact effect sprays forever.
        import re as _re
        m628 = _re.search(r"<Unknown628 value=\"([-0-9.]+)\" />", self.em)
        self.one_shot = bool(m628 and float(m628.group(1)) >= 1.0)
        self.envelope = kfp_envelope(self.pr, "ptxu_Colour:m_rgbaMinKFP") or [(0, 1), (1, 0)]
        self.color = color_rgb(self.pr)

        # texture: <FileName> or <Name>.dds, next to the XML
        d = re.search(r"<TextureName>([^<]+)</TextureName>", self.pr)
        tex_name = d.group(1) if d else None
        self.sprite = None
        if tex_name:
            for candidate in (tex_name + ".dds", tex_name + ".png"):
                p = os.path.join(os.path.dirname(xml_path), candidate)
                if os.path.exists(p):
                    self.sprite = Image.open(p).convert("RGBA")
                    break


class Effect:
    """An effect = one or more LAYERS.

    ⛔ 74% of vanilla has several emitters; the layer delay comes from the
       `Unknown10` field, the layer size multiplier from `ParticleScale`.
    """

    def __init__(self, xml_path, name):
        s = io.open(xml_path, encoding="utf-8", errors="replace").read()
        block = None
        for a, b in iter_blocks(s, "EffectRuleDictionary"):
            if a == name:
                block = b
                break
        if block is None:
            raise KeyError("no such effect: %s" % name)
        em = dict(iter_blocks(s, "EmitterRuleDictionary"))
        pr = dict(iter_blocks(s, "ParticleRuleDictionary"))
        i, j = block.find("<EventEmitters>"), block.find("</EventEmitters>")
        g = block[i:j] if i >= 0 else block
        pairs = re.findall(
            r"<EmitterRule>([^<]*)</EmitterRule>\s*"
            r"<ParticleRule>([^<]*)</ParticleRule>\s*"
            r"<Unknown10 value=\"([-0-9.eE]+)\" />.*?"
            r"<ParticleScale value=\"([-0-9.eE]+)\"", g, re.S)
        self.name = name
        self.layers = []
        for e, p, delay, scale in pairs:
            if e in em and p in pr:
                self.layers.append(
                    Layer(em[e], pr[p], xml_path, float(delay), float(scale)))
        if not self.layers:
            raise KeyError("%s: no layer could be resolved" % name)

    def sim(self, duration=3.0, fps=20, seed=1):
        merged = []
        for n, k in enumerate(self.layers):
            layer_frames = k.sim(duration, fps, seed + n * 17)
            delay_frames = int(k.delay * fps)
            for i in range(len(layer_frames)):
                while len(merged) <= i:
                    merged.append([])
            for i, frame in enumerate(layer_frames):
                target = i + delay_frames
                if target < len(merged):
                    merged[target].extend((q, k) for q in frame)
        return merged

    @property
    def sprite(self):
        return self.layers[0].sprite

    @property
    def color(self):
        return self.layers[0].color

    @property
    def size(self):
        return max(k.size for k in self.layers)

    @property
    def envelope(self):
        return self.layers[0].envelope


def _layer_sim(self, duration=3.0, fps=20, seed=1):
        """Produces frames: each frame [(x, y, z, size, alpha)]."""
        rng = random.Random(seed)
        dt = 1.0 / fps
        particles = []
        frames = []
        accumulator = 0.0
        n = int(duration * fps)
        for k in range(n):
            # in one-shot mode emission only lasts the first 0.08 s
            # ⚠ The one-shot window is a MODEL: 0.25 s. The engine's real
            #   semantics were not measured (`StartParticleFxNonLooped`
            #   plays the effect once; the engine knows how long).
            if not self.one_shot or k * dt < 0.25:
                accumulator += self.rate * dt
            while accumulator >= 1.0:
                accumulator -= 1.0
                p = [rng.uniform(-1, 1) * self.spawn[0] * 0.5,
                     rng.uniform(-1, 1) * self.spawn[1] * 0.5,
                     rng.uniform(-1, 1) * self.spawn[2] * 0.5]
                life = rng.uniform(self.lifetime[0], self.lifetime[1]) or 1.0
                # target = path to travel over the lifetime -> initial velocity
                offset = [rng.uniform(-1, 1) * self.target_size[i] * 0.5 for i in range(3)]
                velocity = [(self.target[i] + offset[i]) / life for i in range(3)]
                particles.append({"p": p, "v": velocity, "t": 0.0, "life": life,
                                  "d": rng.uniform(0, math.tau)})
            frame = []
            for pt in particles:
                pt["t"] += dt
                for i in range(3):
                    pt["v"][i] += self.accel[i] * dt
                    if self.damping[i] > 0:
                        pt["v"][i] *= max(0.0, 1.0 - self.damping[i] * dt)
                    pt["p"][i] += pt["v"][i] * dt
                f = pt["t"] / pt["life"]
                if f <= 1.0:
                    frame.append((pt["p"][0], pt["p"][1], pt["p"][2],
                                  self.size, curve_value(self.envelope, f), pt["d"]))
            particles = [q for q in particles if q["t"] < q["life"]]
            frames.append(frame)
        return frames



# ⛔ Do NOT put the binding at the END OF THE FILE: `main()` runs first through
#    `raise SystemExit(main())` and at that moment `Layer.sim` is still undefined
#    (AttributeError). Bind it right after the definition.
Layer.sim = _layer_sim

def draw(frames, effect, resolution=384, view_m=4.0):
    """Draws the frames as a side-on orthographic image.

    ⚠ Every particle uses the sprite and color of ITS OWN LAYER; in a
      multi-emitter effect the layers carry different textures.
    """
    px_per_m = resolution / view_m          # pixels / metre
    ims = []
    ground = int(resolution * 0.78)
    for frame in frames:
        im = Image.new("RGB", (resolution, resolution), (26, 27, 30))
        d = np.asarray(im).copy()
        d[ground:ground + 1, :] = (70, 72, 78)
        im = Image.fromarray(d)
        # back to front: sort by y so the overlap is right
        for (q, layer) in sorted(frame, key=lambda t: -t[0][1]):
            x, y, z, size, alpha, angle = q
            if alpha <= 0.01 or layer.sprite is None:
                continue
            px = int(resolution * 0.5 + x * px_per_m)
            py = int(ground - z * px_per_m)
            sprite_px = max(2, int(size * px_per_m))
            if sprite_px > resolution * 3 or px < -sprite_px or px > resolution + sprite_px:
                continue
            s2 = layer.sprite.resize((sprite_px, sprite_px), Image.LANCZOS)
            if angle:
                s2 = s2.rotate(math.degrees(angle), expand=False)
            a = np.asarray(s2).astype(np.float32) / 255.0
            a[..., 0] *= layer.color[0]
            a[..., 1] *= layer.color[1]
            a[..., 2] *= layer.color[2]
            a[..., 3] *= alpha
            tinted = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGBA")
            im.paste(tinted, (px - sprite_px // 2, py - sprite_px // 2), tinted)
        ims.append(im)
    return ims


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xml")
    ap.add_argument("effect", nargs="?")
    ap.add_argument("--out", "--cikti", dest="out", default=None)
    ap.add_argument("--duration", "--sure", dest="duration", type=float, default=3.0)
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--resolution", "--coz", dest="resolution", type=int, default=384)
    ap.add_argument("--view-width", "--kamera", dest="view_width", type=float, default=4.0,
                    help="view width (m)")
    args = ap.parse_args()

    e = Effect(args.xml, args.effect)
    frames = e.sim(args.duration, args.fps)
    total = sum(len(k) for k in frames)
    peak = max(len(k) for k in frames) if frames else 0
    ims = draw(frames, e, args.resolution, args.view_width)
    out = args.out or (e.name + ".gif")
    ims[0].save(out, save_all=True, append_images=ims[1:],
                duration=int(1000 / args.fps), loop=0, optimize=True)
    print("%-26s %d layers  particle peak %3d  size %.2f m  -> %s"
          % (e.name, len(e.layers), peak, e.size, os.path.basename(out)))
    if peak == 0:
        print("   ⛔ NO PARTICLES AT ALL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
