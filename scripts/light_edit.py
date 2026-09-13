#!/usr/bin/env python3
"""light_edit.py — WRITES the lights back into a .ydr/.yft.

WHY IT EXISTS
=============
Reading is not enough. The only way to fix a light was to type it in field by
field in the CodeWalker GUI; there was no way back from the editor into the file.

PIPELINE
========
    binary  --res_to_xml-->  XML  --(this module)-->  XML  --xml_to_res-->  binary

The round trip was MEASURED: on prop_worklight_01a.yft Intensity 2->8 and
ConeOuterAngle 60->35 were written, read back, and came out identical. The file
SIZE changes (RSC7 is zlib) -- **size is not a validity measure, the only
measure is reading back**, so verification after every write is mandatory.

SAFETY
======
The original is always kept as `<name>.yedek` and the size is compared after
the copy: "the command raised no error" is not proof of deployment.

USAGE
=====
    python assetdb.py light prop.ydr --apply edits.json
    python assetdb.py light prop.ydr --set 0.Intensity=8 --set 0.ConeOuterAngle=35
    python assetdb.py light prop.ydr --remove 2
    python assetdb.py light prop.ydr --add          (copies the first light)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import light_scene  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RES_TO_XML = os.path.join(HERE, "res_to_xml.ps1")
XML_TO_RES = os.path.join(HERE, "xml_to_res.ps1")

# Backup suffix. ".yedek" is Turkish for "backup"; .gitignore and the README match
# this suffix, so it stays.
BACKUP_SUFFIX = ".yedek"

VEC3 = ["Position", "Direction", "Tangent", "Extent", "CullingPlaneNormal"]
RGB = ["Colour", "VolumeOuterColour"]
TEXT = ["Type", "ProjectedTextureHash"]

# Vanilla field ORDER (measured from prop_worklight_01a.yft). The order is kept so
# the generated node stays structurally identical to vanilla.
ORDER = [
    "Position", "Colour", "Flashiness", "Intensity", "Flags", "BoneId", "Type",
    "GroupId", "TimeFlags", "Falloff", "FalloffExponent", "CullingPlaneNormal",
    "CullingPlaneOffset", "Unknown45", "Unknown46", "VolumeIntensity",
    "VolumeSizeScale", "VolumeOuterColour", "LightHash", "VolumeOuterIntensity",
    "CoronaSize", "VolumeOuterExponent", "LightFadeDistance", "ShadowBlur",
    "ShadowFadeDistance", "SpecularFadeDistance", "VolumetricFadeDistance",
    "ShadowNearClip", "CoronaIntensity", "CoronaZBias", "Direction", "Tangent",
    "ConeInnerAngle", "ConeOuterAngle", "Extent", "ProjectedTextureHash",
]
INTEGER = set(light_scene.FIELDS_I)


def _ps(script, *args):
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", script] + list(args),
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _num(v):
    """CodeWalker float format: an integer is written without the decimal point."""
    f = float(v)
    return str(int(f)) if f == int(f) and abs(f) < 1e15 else repr(f)


def _write_light(it, l):
    """Rebuilds an <Item> from scratch from the JSON dict."""
    for c in list(it):
        it.remove(c)
    for name in ORDER:
        if name not in l:
            continue
        e = ET.SubElement(it, name)
        v = l[name]
        if name in VEC3:
            for k, x in zip("xyz", v):
                e.set(k, _num(x))
        elif name in RGB:
            for k, x in zip("rgb", v):
                e.set(k, str(int(x)))
        elif name in TEXT:
            if str(v).strip():
                e.text = str(v).strip()
        elif name in INTEGER:
            e.set("value", str(int(v)))
        else:
            e.set("value", _num(v))


def _lights_node(root):
    L = root.find("Lights")
    if L is None:
        L = root.find(".//Lights")
    return L


def apply_lights(path, lights, backup=True):
    """lights: a list of dicts in the form light_scene.read_scene() returns."""
    path = os.path.abspath(path)
    name = os.path.basename(path)
    with tempfile.TemporaryDirectory(prefix="lightedit_") as td:
        work = os.path.join(td, name)
        shutil.copyfile(path, work)

        rc, output = _ps(RES_TO_XML, "-Path", work)
        xml = work + ".xml"
        if rc != 0 or not os.path.isfile(xml):
            # If the converter did not run this is an ERROR, not "no lights".
            raise RuntimeError("could not produce XML (%d): %s" % (rc, output.strip()[:300]))

        tree = ET.parse(xml)
        root = tree.getroot()
        L = _lights_node(root)
        if L is None:
            if not lights:
                raise RuntimeError("the file has no <Lights> and there is nothing to add")
            # In a Fragment, Lights is AT THE ROOT, not Drawable/Lights (measured).
            L = ET.SubElement(root, "Lights")
        for c in list(L):
            L.remove(c)
        for l in lights:
            _write_light(ET.SubElement(L, "Item"), l)
        tree.write(xml, encoding="utf-8", xml_declaration=True)

        rc, output = _ps(XML_TO_RES, "-XmlPath", xml)
        if rc != 0 or not os.path.isfile(work):
            raise RuntimeError("could not compile the binary (%d): %s" % (rc, output.strip()[:300]))

        # VERIFICATION: the only valid measure is reading back (not size).
        try:
            back = light_scene.read_scene(work)
        except (RuntimeError, ValueError) as e:
            raise RuntimeError("compiled but could NOT be read back: %s" % e)
        if len(back["isiklar"]) != len(lights):
            raise RuntimeError("light count mismatch on read-back: %d written, %d read"
                               % (len(lights), len(back["isiklar"])))

        if backup:
            backup_path = path + BACKUP_SUFFIX
            if not os.path.isfile(backup_path):
                shutil.copyfile(path, backup_path)
        shutil.copyfile(work, path)
        # "The command raised no error" is not proof of deployment.
        if os.path.getsize(path) != os.path.getsize(work):
            raise RuntimeError("copy not verified: size mismatch")
        return back


# --------------------------------------------------------------------- CLI

def _apply_sets(lights, rules):
    """'0.Intensity=8' or 'Intensity=8' (all lights)."""
    for k in rules:
        if "=" not in k:
            raise ValueError("--set format: [idx.]Field=value  (got: %s)" % k)
        lhs, value = k.split("=", 1)
        lhs = lhs.strip()
        if "." in lhs:
            idx_s, field = lhs.split(".", 1)
            targets = [int(idx_s)]
        else:
            field, targets = lhs, list(range(len(lights)))
        field = field.strip()
        for i in targets:
            if not 0 <= i < len(lights):
                raise ValueError("no such light index: %d (0..%d)" % (i, len(lights) - 1))
            l = lights[i]
            if field not in l:
                raise ValueError("no such field: %s" % field)
            old = l[field]
            if isinstance(old, list):
                parts = [float(x) for x in value.replace(",", " ").split()]
                if len(parts) != len(old):
                    raise ValueError("%s expects %d values" % (field, len(old)))
                l[field] = [int(x) for x in parts] if field in RGB else parts
            elif isinstance(old, str):
                l[field] = value.strip()
            elif field in INTEGER:
                l[field] = int(float(value))
            else:
                l[field] = float(value)
    return lights


def run(args):
    path = getattr(args, "path", None)
    if not path or not os.path.isfile(path):
        print("ERROR: no such file: %s" % path, file=sys.stderr)
        return 2
    try:
        scene = light_scene.read_scene(path)
    except (RuntimeError, ValueError) as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 2
    lights = [{k: v for k, v in l.items() if not k.startswith("_")}
              for l in scene["isiklar"]]

    source = None
    if getattr(args, "apply", None):
        with open(args.apply, encoding="utf-8") as fh:
            d = json.load(fh)
        # "isiklar" (lights) is the scene key light_scene.py writes; edit files use it too.
        new = d.get("isiklar", d if isinstance(d, list) else None)
        if new is None:
            print("ERROR: no 'isiklar' array in the JSON", file=sys.stderr)
            return 2
        lights = [{k: v for k, v in l.items() if not k.startswith("_")}
                  for l in new]
        source = args.apply

    if getattr(args, "add", False):
        new = json.loads(json.dumps(lights[0])) if lights else None
        if new is None:
            print("ERROR: no light to copy (the file has none).",
                  file=sys.stderr)
            return 2
        lights.append(new)

    for i in sorted(getattr(args, "remove", None) or [], reverse=True):
        if not 0 <= i < len(lights):
            print("ERROR: no such index to remove: %d" % i, file=sys.stderr)
            return 2
        lights.pop(i)

    if getattr(args, "set", None):
        try:
            _apply_sets(lights, args.set)
        except ValueError as e:
            print("ERROR: %s" % e, file=sys.stderr)
            return 2

    if source is None and not any([getattr(args, "set", None),
                                   getattr(args, "remove", None),
                                   getattr(args, "add", False)]):
        print("ERROR: nothing to do (--apply / --set / --add / --remove)",
              file=sys.stderr)
        return 2

    before = len(scene["isiklar"])
    try:
        back = apply_lights(path, lights)
    except RuntimeError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 2

    print("%s: %d light(s) -> %d written and VERIFIED BY READING BACK"
          % (os.path.basename(path), before, len(back["isiklar"])))
    for l in back["isiklar"]:
        print("  #%d %-8s int=%-6s range=%-5s cone=%s/%s"
              % (l["_i"], l["Type"], _num(l["Intensity"]), _num(l["Falloff"]),
                 _num(l["ConeInnerAngle"]), _num(l["ConeOuterAngle"])))
    print("  backup: %s%s" % (os.path.basename(path), BACKUP_SUFFIX))
    print("\n  The asset changed: LEAVE the server and reconnect - a restart is not enough.")
    return 0
