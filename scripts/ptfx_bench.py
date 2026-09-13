#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_bench.py — drives the in-game particle test FROM OUTSIDE and MEASURES it.

WHY: particle verification was stuck for five rounds in the loop "put the
user in the game, ask for a screenshot, interpret the screenshot". The
interpretation layer led to a wrong diagnosis three times (see the former
flipbook production note (2.5.0), §1c). This script removes that layer: a job
file is written, the server takes a screenshot from the client with a FIXED
CAMERA, and the image is judged by pixel measurement.

⛔ LIMIT: the screenshot is the CLIENT's render. A player must be connected;
   there is NO way that takes the game out completely -- what is tested is
   GTA's own render.

⛔ If a stream (.ypt/.ydr) file CHANGED the player must RECONNECT; `restart`
   is not enough, FiveM caches stream files. This script only measures assets
   that are ALREADY deployed.

Usage:
  python ptfx_bench.py diagnose          # numbered diagnostic sheets
  python ptfx_bench.py all               # 15 production effects
  python ptfx_bench.py --measure <jpg>   # measure a single image
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

import numpy as np
from PIL import Image

def _server_resources():
    """The server's resources folder: MUTO_ATLAS_SERVER or `assetdb.py path server`.

    The path is NOT WRITTEN into the code -- it is the user's own server, in their own registry.
    """
    env = os.environ.get("MUTO_ATLAS_SERVER")
    if env:
        return env
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import paths
        r = paths.resolve("server")
        p = r[0] if isinstance(r, tuple) else r
        return p or None
    except Exception:
        return None


_RES = _server_resources()
# The bench resource (`my_ptfx_test`) must be installed on the server separately; it is not in the repository.
RESOURCE = os.path.join(_RES, "[script]", "my_ptfx_test") if _RES else ""
# ⛔ Do not rename: the in-game resource reads is/istek.json (request) and writes is/sonuc.json (result).
REQUEST = os.path.join(RESOURCE, "is", "istek.json")
RESULT = os.path.join(RESOURCE, "is", "sonuc.json")
# How the server resolves the `fileName` path is not known in advance; the result
# JSON gives the real name, and it is also searched in these roots (parents of resources).
ROOTS = [os.path.dirname(_RES), os.path.dirname(os.path.dirname(_RES)),
         os.path.dirname(os.path.dirname(os.path.dirname(_RES)))] if _RES else []

# Effect families deployed as `my_<family>`.
PRODUCTION = ["smoke", "fire", "fireball", "dust", "steam", "spark", "splash",
              "ember", "fog", "bubble", "debris", "ring", "electric", "blood", "leaf"]

# old Turkish mode names still accepted on the command line
MODE_ALIASES = {"tani": "diagnose", "hepsi": "all", "izgara": "grid"}


# ------------------------------------------------------------- job driving
# JSON keys exchanged with the in-game resource stay Turkish because the resource reads them:
#   request: "adimlar" (steps), per step "ad" (name), "varlik" (asset), "efekt" (effect),
#            "olcek" (scale), "mesafe" (distance)
#   result:  "adimlar", "hata" (error), per step "ad", "dosya" (file), "taban" (base frame)
def send_job(steps, timeout=180):
    """Writes is/istek.json, waits for is/sonuc.json."""
    if not RESOURCE:
        raise SystemExit("server path is not registered: assetdb.py path server <resources path> "
                         "(or MUTO_ATLAS_SERVER)")
    os.makedirs(os.path.dirname(REQUEST), exist_ok=True)
    if os.path.exists(RESULT):
        os.remove(RESULT)
    io.open(REQUEST, "w", encoding="utf-8").write(
        json.dumps({"adimlar": steps}, ensure_ascii=False))
    print("job sent: %d steps -- waiting for the server" % len(steps))
    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists(RESULT):
            raw = io.open(RESULT, encoding="utf-8", errors="replace").read()
            if raw.strip():
                try:
                    return json.loads(raw)
                except ValueError:
                    pass
        time.sleep(1.0)
    raise TimeoutError(
        "the server did not answer within %d s.\n"
        "  · are you connected in game?\n"
        "  · did `ensure my_ptfx_test` run (server.lua is new)?\n"
        "  · does the console show '[my_ptfx] is alindi' (the resource's 'job received' line)?"
        % timeout)


def decode_b64(rel_path):
    """Converts the .b64 file the server wrote into a JPEG, returns the path."""
    import base64
    full = os.path.join(RESOURCE, rel_path.replace("/", os.sep))
    if not os.path.exists(full):
        return None
    raw = io.open(full, encoding="ascii", errors="ignore").read().strip()
    if not raw:
        return None
    jpg = full[:-4] + ".jpg"
    io.open(jpg, "wb").write(base64.b64decode(raw + "=" * (-len(raw) % 4)))
    return jpg


def find_file(name):
    """Finds the screenshot the server wrote on disk."""
    if name and name.endswith(".b64"):
        return decode_b64(name)
    if name and os.path.isabs(name) and os.path.exists(name):
        return name
    for root in ROOTS:
        y = os.path.join(root, name or "")
        if name and os.path.exists(y):
            return y
    # last resort: search by name
    target = os.path.basename(name or "")
    for root in ROOTS:
        for folder, _, files in os.walk(root):
            if target and target in files:
                return os.path.join(folder, target)
        break
    return None


# ------------------------------------------------------------- measurement
def _components(mask):
    """Connected component count (4-neighbourhood, stack based)."""
    h, w = mask.shape
    seen = np.zeros((h, w), bool)
    n, sizes = 0, []
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not seen[y, x]:
                n += 1
                stack = [(y, x)]
                seen[y, x] = True
                count = 0
                while stack:
                    cy, cx = stack.pop()
                    count += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
                sizes.append(count)
    return n, sizes


def measure(path, downscale=3, threshold_pct=97.0, min_size=4):
    """Counts the WHITE digits in the image (for the numbered diagnostic sheet).

    If slicing WORKS a single digit is visible; if it DOES NOT, the whole sheet
    is drawn and dozens of digits are visible at once. The criterion is the
    component count.

    ⛔ DO NOT USE AN ABSOLUTE BRIGHTNESS THRESHOLD. The first version said
    `bright > 205` and counted ZERO on a night frame where the digits were
    clearly visible. Scene lighting changes from frame to frame; the threshold
    is taken RELATIVE TO THE SCENE.
    """
    im = Image.open(path).convert("RGB")
    k = im.resize((im.size[0] // downscale, im.size[1] // downscale), Image.LANCZOS)
    a = np.asarray(k, np.float32)
    grey = a.mean(axis=2)
    saturation = a.max(axis=2) - a.min(axis=2)
    # top percentile of the scene + no colour: a white digit satisfies both
    t = float(np.percentile(grey, threshold_pct))
    m = (grey >= t) & (saturation < 55)
    n, sizes = _components(m)
    large = [x for x in sizes if x >= min_size]
    return {
        "file": os.path.basename(path),
        "size": im.size,
        "threshold": round(t, 1),
        "bright_ratio": float(m.mean()),
        "components": n,
        "large_components": len(large),
        "largest": max(sizes) if sizes else 0,
    }

def measure_diff(effect_path, base_path, downscale=3, threshold=26, min_size=6):
    """Compares the effect frame with the BASE frame and measures only the effect.

    ⛔ An absolute threshold counted the scene as well (1027 components on the
    reference frame, unrelated to the digits). The base difference takes the
    scene out of the equation completely.
    """
    a = np.asarray(Image.open(effect_path).convert("RGB"), np.float32)
    b = np.asarray(Image.open(base_path).convert("RGB"), np.float32)
    if a.shape != b.shape:
        return None
    d = np.abs(a - b).mean(axis=2)
    k = Image.fromarray(d.astype(np.uint8)).resize(
        (d.shape[1] // downscale, d.shape[0] // downscale), Image.LANCZOS)
    m = np.asarray(k, np.float32) >= threshold
    n, sizes = _components(m)
    large = [x for x in sizes if x >= min_size]
    return {
        "components": n,
        "large_components": len(large),
        "largest": max(sizes) if sizes else 0,
        "changed_ratio": float(m.mean()),
    }


def report(result):
    print()
    print("%-22s %8s %10s %9s" % ("step", "compon.", "large", "bright%"))
    for a in result.get("adimlar", []):
        if a.get("hata"):
            print("%-22s  ERROR: %s" % (a["ad"], a["hata"]))
            continue
        y = find_file(a.get("dosya"))
        if not y:
            print("%-22s  image not found: %s" % (a["ad"], a.get("dosya")))
            continue
        tb = find_file(a.get("taban")) if a.get("taban") else None
        if tb:
            o = measure_diff(y, tb)
            if o:
                print("%-22s %8d %10d %8.2f%%   %s"
                      % (a["ad"], o["components"], o["large_components"],
                         o["changed_ratio"] * 100, os.path.basename(y)))
                continue
        o = measure(y)
        print("%-22s %8d %10d %8.2f%%   (no base) %s"
              % (a["ad"], o["components"], o["large_components"],
                 o["bright_ratio"] * 100, os.path.basename(y)))


DIAGNOSE = [
    {"ad": "reference", "varlik": "core", "efekt": "exp_grd_grenade_smoke",
     "olcek": 1.0, "mesafe": 3.5},
    {"ad": "diag_2x2", "varlik": "my_no2", "olcek": 1.0, "mesafe": 3.5},
    {"ad": "diag_7x7", "varlik": "my_no7", "olcek": 1.0, "mesafe": 3.5},
]

# Grid x resolution multiplier. Between the working (2x2@256) and the broken
# (7x7@1024) case there were TWO variables; the four corners separate them.
GRID = [
    {"ad": "gA_2x2_256",  "varlik": "my_g1", "olcek": 1.0, "mesafe": 3.5},
    {"ad": "gB_2x2_1024", "varlik": "my_g2", "olcek": 1.0, "mesafe": 3.5},
    {"ad": "gC_7x7_256",  "varlik": "my_g3", "olcek": 1.0, "mesafe": 3.5},
    {"ad": "gD_7x7_1024", "varlik": "my_g4", "olcek": 1.0, "mesafe": 3.5},
    # The last two cells that separate the donor from the grid:
    #   g5  = our copy (C4=48) + VANILLA's own 7x7 texture
    #   ref7= the game's OWN 7x7 effect, we send no file
    {"ad": "g5_7x7_vanilla_texture", "varlik": "my_g5", "olcek": 1.0, "mesafe": 3.5},
    {"ad": "ref7_game_own", "varlik": "core", "efekt": "veh_respray_smoke",
     "olcek": 1.0, "mesafe": 3.5},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", default="diagnose", choices=["diagnose", "all", "grid"],
                    type=lambda v: MODE_ALIASES.get(v, v))
    ap.add_argument("--measure", "--olc", dest="measure", help="measure a single image and exit")
    a = ap.parse_args()
    if a.measure:
        print(json.dumps(measure(a.measure), ensure_ascii=False, indent=2))
        return 0
    if a.mode == "grid":
        steps = GRID
    else:
        steps = DIAGNOSE if a.mode == "diagnose" else [
            {"ad": x, "varlik": "my_" + x, "olcek": 1.0, "mesafe": 4.0} for x in PRODUCTION]
    s = send_job(steps)
    if s.get("hata"):
        print("SERVER ERROR: %s" % s["hata"])
        return 1
    report(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
