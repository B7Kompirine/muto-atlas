#!/usr/bin/env python3
"""res_xml.py — has a binary RSC7 resource dumped to XML temporarily and reads it.

WHY A SEPARATE MODULE: doctor, diff and light all start the same way -- there
is a binary .ycd/.ytyp/.yft at hand, and what has to be inspected is its XML
counterpart. A separate copy for each of the three meant a bug fixed in one
stayed in the others.

MOST IMPORTANT CONTRACT: if the converter cannot be run, this is returned as an
ERROR, NOT silently as "no content". The caller has to see the difference;
otherwise "CodeWalker is not installed" gets reported as "the file is empty".
    "The tool not showing a thing does not mean the thing is not there."
"""
from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
RES_TO_XML = os.path.join(HERE, "res_to_xml.ps1")

# The extensions res_to_xml.ps1 can REALLY convert (one to one with the switch in
# that file). If this is kept wider, every file that cannot be converted is reported
# as "produced no XML" and the reason is lost -- measured: because `.ymap` was in
# the list, 204 files were skipped this way, while the converter DOES NOT ACCEPT `.ymap`.
# The list must stay in sync with res_to_xml.ps1; the `case` lines there are the authority.
# (doctor.py imports RES_EXT.)
RES_EXT = {".ycd", ".yed", ".yft", ".ydd", ".ydr", ".ybn", ".ytyp", ".ypt"}

# Known resources this pipeline cannot convert: the reason is stated OPENLY,
# not hidden behind a vague message such as "produced no XML".
UNCONVERTIBLE = {
    ".ymap": "res_to_xml.ps1 does not convert .ymap (use the CodeWalker GUI or "
             "build_ymap_lod.ps1)",
}

TIMEOUT = 180


def binary_to_xml(path, tmp):
    """Dumps the binary resource into the tmp folder as XML. Returns (xml_path, error)."""
    if not os.path.exists(RES_TO_XML):
        return None, f"res_to_xml.ps1 not found: {RES_TO_XML}"
    shell = shutil.which("powershell") or shutil.which("pwsh")
    if shell is None:
        return None, "powershell not found"
    try:
        p = subprocess.run(
            [shell, "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", RES_TO_XML, "-Path", path, "-OutDir", tmp],
            capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"res_to_xml.ps1 could not be run: {exc}"
    if p.returncode != 0:
        lines = (p.stderr or p.stdout or "").strip().splitlines()
        return None, f"res_to_xml.ps1 error: {lines[-1] if lines else p.returncode}"
    produced = [os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith(".xml")]
    if not produced:
        return None, "res_to_xml.ps1 produced no XML"
    return max(produced, key=os.path.getmtime), None


@contextlib.contextmanager
def open_xml(path):
    """`with open_xml(p) as (xml_path, error):` — gives an XML file directly, a
    binary through a temporary conversion that is cleaned up on exit. When error
    is set, xml_path is None."""
    if not os.path.exists(path):
        yield None, "file not found"
        return
    if path.lower().endswith(".xml"):
        yield path, None
        return
    ext = os.path.splitext(path)[1].lower()
    if ext not in RES_EXT:
        yield None, UNCONVERTIBLE.get(ext, f"unsupported extension ({ext})")
        return
    tmp = tempfile.mkdtemp(prefix="mutoxml_")
    try:
        yield binary_to_xml(path, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _shell():
    return shutil.which("powershell") or shutil.which("pwsh")


def _batch_convert(paths, tmp):
    """Converts several files with a single PowerShell call. Returns {source: xml}.

    WHY: one PowerShell + CodeWalker.Core load per file is ~0.6 s.
    For a stream folder of 957 files that meant 10 minutes; with a batch call a
    single load is enough. A gate that takes 10 minutes does not get used, so
    speed matters here as much as correctness.
    """
    shell = _shell()
    if shell is None:
        return {}, "powershell not found"
    array = ",".join("'" + y.replace("'", "''") + "'" for y in paths)
    command = (f"& '{RES_TO_XML.replace(chr(39), chr(39) * 2)}' "
               f"-Path @({array}) -OutDir '{tmp.replace(chr(39), chr(39) * 2)}'")
    try:
        p = subprocess.run([shell, "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-Command", command],
                           capture_output=True, text=True,
                           timeout=TIMEOUT * 4)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {}, f"batch conversion could not be run: {exc}"
    if p.returncode != 0:
        lines = (p.stderr or p.stdout or "").strip().splitlines()
        return {}, f"batch conversion error: {lines[-1] if lines else p.returncode}"

    produced = {f: os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith(".xml")}
    mapping = {}
    for y in paths:
        name = os.path.basename(y) + ".xml"
        if name in produced:
            mapping[y] = produced[name]
    return mapping, None


def _unique_groups(paths, limit=60):
    """Two sources that carry the same file name are NOT put in the SAME group.

    The output is matched by file name, so two inputs with the same name overwrite
    each other and one silently gets the other's XML -- with ped components
    (head_000_r has the same name in every ped) this is a real pitfall.
    """
    group, names = [], set()
    for y in paths:
        name = os.path.basename(y).lower()
        if name in names or len(group) >= limit:
            yield group
            group, names = [], set()
        group.append(y)
        names.add(name)
    if group:
        yield group


# doctor.py imports read_roots_batch.
def read_roots_batch(paths):
    """Yields (path, root, error). Binaries are converted in batches, XML files are read directly."""
    binary = []
    for y in paths:
        if not os.path.exists(y):
            yield y, None, "file not found"
        elif y.lower().endswith(".xml"):
            yield (y,) + _parse(y)
        elif os.path.splitext(y)[1].lower() in RES_EXT:
            binary.append(y)
        else:
            ext = os.path.splitext(y)[1].lower()
            yield y, None, UNCONVERTIBLE.get(ext, f"unsupported extension ({ext})")

    for group in _unique_groups(binary):
        tmp = tempfile.mkdtemp(prefix="mutoxml_")
        try:
            mapping, error = _batch_convert(group, tmp)
            for y in group:
                if error:
                    yield y, None, error
                elif y not in mapping:
                    yield y, None, "res_to_xml.ps1 produced no XML for this file"
                else:
                    yield (y,) + _parse(mapping[y])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# doctor.py recognises the "XML could not be parsed" prefix (PARSE_ERROR_PREFIXES) and
# then reports the cause; keep the prefix when editing these messages.
def _parse(xml_path):
    try:
        return ET.parse(xml_path).getroot(), None
    except ET.ParseError as exc:
        return None, f"XML could not be parsed: {exc}"
    except OSError as exc:
        return None, f"could not be read: {exc}"


# light.py, light_scene.py, timecycle.py and structural_diff.py import read_root.
def read_root(path):
    """(ElementTree root, error). A parse failure is returned as an ERROR too."""
    with open_xml(path) as (xml_path, error):
        if error:
            return None, error
        try:
            return ET.parse(xml_path).getroot(), None
        except ET.ParseError as exc:
            return None, f"XML could not be parsed: {exc}"
        except OSError as exc:
            return None, f"could not be read: {exc}"
