#!/usr/bin/env python3
"""doctor_common.py — shared primitives of the doctor checks.

It is a separate file because of a circular import: doctor.py calls the
checks, and the checks need the severity levels and Report. With
the shared parts here, both sides import this module instead of each other.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n import get_lang  # noqa: E402

# --- SEVERITY LEVELS ----------------------------------------------------------
# FATAL  : the game crashes or the WHOLE resource dies (no command registers)
# SILENT : does not work and gives no error -- the most expensive class, the one that eats rounds
# WARN   : suspicious, may be deliberate
FATAL, SILENT, WARN = "FATAL", "SILENT", "WARN"
SEVERITY_ORDER = {FATAL: 0, SILENT: 1, WARN: 2}

# NOTE: the supported binary extensions (RES_EXT) are defined in res_xml.py --
# in the module that does the conversion. Keeping two copies meant that when an
# extension was added to one, the other silently stayed stale.


def _localize(d):
    """Pick the text for the active language from a message dict.

    The dict holds an "en" text; a text for another language (for example "tr")
    may sit next to it. A missing language falls back to "en".
    """
    return d.get(get_lang(), d.get("en", next(iter(d.values()))))


class Finding:
    __slots__ = ("level", "code", "path", "message", "hint")

    def __init__(self, level, code, path, message, hint=""):
        self.level, self.code, self.path = level, code, path
        self.message, self.hint = message, hint


class Report:
    """The doctor report: findings, files that were not inspected, and the inspected count."""

    def __init__(self):
        self.findings = []
        self.skipped = []      # (path, reason) -- NOT INSPECTED
        self.inspected = 0

    def add(self, level, code, path, message, hint=""):
        self.findings.append(Finding(level, code, path, message, hint))

    def skip(self, path, reason):
        self.skipped.append((path, reason))


EMPTY_HASHES = {"", "0", "hash_0", "hash_00000000"}

# GTA clips are 30 fps. MEASURED (vanilla mp_safehousewine@ + move_m@brave and
# our own compiled output): the animation's Duration field is the time of the
# LAST FRAME,
#     Duration == (FrameCount - 1) / 30
# and in vanilla a clip's EndTime NEVER exceeds its animation's Duration (the
# largest measured difference is -1 frame, 0 violations in 37 pairs). A clip
# that exceeds Duration asks for a frame the animation does not have.
FRAME_SECONDS = 1.0 / 30.0  # one frame in seconds


def _attr_float(el, attr="value"):
    """Float value of attribute `attr` of element `el`, or None."""
    if el is None:
        return None
    try:
        return float(el.get(attr))
    except (TypeError, ValueError):
        return None


def _hash_empty(value):
    """True when a hash field is empty or hash 0."""
    return (value or "").strip().lower() in EMPTY_HASHES
