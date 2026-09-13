#!/usr/bin/env python3
"""doctor.py — SILENT FAILURE GATE: checks an asset before it goes into the game.

WHY IT EXISTS
=============
Most GTA V asset failures are SILENT. The file compiles, the tool says
"0 warnings", the server prints "Started resource" -- and nothing happens in
the game. The only way to find the cause is a round trip: build -> deploy ->
restart the server -> DISCONNECT -> reconnect -> look -> guess -> start over.

Most of those rounds are spent on failures that could have been caught up
front by looking at the file. This tool catches them WITHOUT a round trip.

THE MOST IMPORTANT DESIGN RULE
==============================
A FILE THAT COULD NOT BE INSPECTED DOES NOT COUNT AS "CLEAN". If a file could
not be opened, has no converter, or a check could not run, that is reported in
a SEPARATE section and the exit code is 2. Otherwise the tool produces "false
confidence" -- that is, it becomes the very failure class it tries to prevent.
    "The tool not showing a thing does not mean the thing is not there."

EXIT CODES
==========
    0  inspected, no findings
    1  findings
    2  at least one file was NOT INSPECTED (tool/layer missing)
    3  internal error

USAGE
=====
    python assetdb.py doctor <file|folder> [...]
    python assetdb.py doctor stream/ --recursive
    python assetdb.py doctor x.ycd --level silent   (hide WARNs)
"""
from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from doctor_common import FATAL, SEVERITY_ORDER, SILENT, WARN, Report, _localize  # noqa: E402
from doctor_checks import CHECKERS  # noqa: E402
from res_xml import RES_EXT, read_roots_batch  # noqa: E402


DOUBLE_HYPHEN = re.compile(r"<!--(?:(?!-->).)*?--(?:(?!>).)", re.S)

# Prefix of the parse-error text that res_xml.py returns. The Turkish prefix is
# the one res_xml.py wrote before the English conversion; both are accepted so
# a double hyphen is still reported as XML002 whichever text res_xml.py uses.
PARSE_ERROR_PREFIXES = ("XML ayristirilamadi", "XML could not be parsed")


def _parse_error(path, error, report):
    """Says WHY parsing failed. A double hyphen in an XML comment makes the
    file unparseable and the game gives NO error in that case -- the
    definition silently never loads. A 'could not be parsed' message that does
    not name the cause costs a round trip."""
    raw = ""
    if path.lower().endswith(".xml"):
        try:
            raw = open(path, "r", encoding="utf-8", errors="replace").read()
        except OSError:
            raw = ""
    if raw and DOUBLE_HYPHEN.search(raw):
        report.add(FATAL, "XML002", path, _localize({
            "tr": "XML yorumunun icinde iki tire (--) var. Dosya ayristirilamaz; "
                  "oyun hata VERMEZ, tanim hic yuklenmez.",
            "en": "An XML comment contains a double hyphen (--). The file is "
                  "unparseable; the game reports NO error, the definition simply "
                  "never loads."}))
    else:
        report.add(FATAL, "XML001", path, _localize({
            "tr": f"XML ayristirilamadi: {error}",
            "en": f"XML could not be parsed: {error}"}))
    report.inspected += 1


def check_root(root, path, report, compiled):
    fn = CHECKERS.get(root.tag)
    if fn is None:
        report.skip(path, _localize({
            "tr": f"'{root.tag}' icin denetim yok (henuz)",
            "en": f"no checks for '{root.tag}' (yet)"}))
        return
    fn(root, path, report, compiled)
    report.inspected += 1


def collect_targets(paths, recursive, unlisted=None):
    """Files to inspect. A folder that cannot be listed goes to `unlisted`, so it is reported, never dropped."""
    unlisted = [] if unlisted is None else unlisted
    for p in paths:
        if os.path.isdir(p):
            try:
                walk = os.walk(p, onerror=unlisted.append) if recursive else [(p, [], os.listdir(p))]
            except OSError as exc:
                unlisted.append(exc)
                continue
            for folder, _, files in walk:
                for f in sorted(files):
                    full = os.path.join(folder, f)
                    # Not os.path.isfile(): on Windows it is False for a path over 260 characters and the file
                    # would silently vanish from the report. A file that cannot be opened is reported as not inspected.
                    if _relevant(full) and not os.path.isdir(full):
                        yield full
        elif os.path.isfile(p):
            yield p
        else:
            yield p  # path that does not exist -> reported below as skipped


def _relevant(path):
    lower = path.lower()
    return lower.endswith(".xml") or os.path.splitext(lower)[1] in RES_EXT


def check_all(paths, report):
    """Binaries are converted IN BULK (opening PowerShell per file took
    ~10 minutes for 957 files). XML source files do NOT count as 'compiled':
    positional matching is normal in the Sollumz form, not in a compiled file."""
    for path, root, error in read_roots_batch(paths):
        if error:
            if error.startswith(PARSE_ERROR_PREFIXES):
                _parse_error(path, error, report)
            else:
                report.skip(path, error)
            continue
        check_root(root, path, report, compiled=not path.lower().endswith(".xml"))


# =============================================================================
# Report
# =============================================================================
HEADINGS = {
    FATAL: {"tr": "OYUN COKER / KAYNAK DUSER", "en": "GAME CRASHES / RESOURCE DIES"},
    SILENT: {"tr": "SESSIZ HATA (hata vermeden calismaz)", "en": "SILENT FAILURE (fails without any error)"},
    WARN: {"tr": "SUPHELI", "en": "SUSPICIOUS"},
}


def _short(path):
    """Parent folder + file name. The base name alone is not enough: the same
    name exists in different folders (for example the Sollumz output and its
    read-back) and the report could no longer say which file it means."""
    parent = os.path.basename(os.path.dirname(path))
    return f"{parent}/{os.path.basename(path)}" if parent else os.path.basename(path)


def print_report(report, threshold):
    allowed = {s for s in (FATAL, SILENT, WARN) if SEVERITY_ORDER[s] <= SEVERITY_ORDER[threshold]}
    shown = [f for f in report.findings if f.level in allowed]

    for level in (FATAL, SILENT, WARN):
        group = [f for f in shown if f.level == level]
        if not group:
            continue
        print(f"\n=== {level}: {_localize(HEADINGS[level])} ({len(group)}) ===")
        for f in group:
            print(f"  [{f.code}] {_short(f.path)}")
            print(f"         {f.message}")
            if f.hint:
                print(f"         -> {f.hint}")

    # Files that could NOT be inspected never pass silently.
    if report.skipped:
        print(f"\n=== {_localize({'tr': 'DENETLENEMEDI', 'en': 'NOT INSPECTED'})} "
              f"({len(report.skipped)}) ===")
        print("  " + _localize({
            "tr": "Bu dosyalar hakkinda HICBIR SEY iddia edilemez -- 'temiz' DEGIL.",
            "en": "NOTHING can be claimed about these files -- they are NOT 'clean'."}))
        for path, reason in report.skipped:
            print(f"  - {path}\n      {reason}")

    print()
    if not shown and not report.skipped:
        print(_localize({"tr": f"TEMIZ - {report.inspected} dosya denetlendi, bulgu yok.", "en": f"CLEAN - {report.inspected} file(s) inspected, no findings."}))
    else:
        print(_localize({
            "tr": f"{report.inspected} dosya denetlendi | {len(shown)} bulgu | "
                  f"{len(report.skipped)} denetlenemedi",
            "en": f"{report.inspected} file(s) inspected | {len(shown)} finding(s) | "
                  f"{len(report.skipped)} not inspected"}))


def run(args):
    report = Report()
    unlisted = []
    check_all(list(collect_targets(args.paths, args.recursive, unlisted)), report)
    for exc in unlisted:
        report.skip(getattr(exc, "filename", None) or "?", _localize({
            "tr": f"klasor listelenemedi: {exc}",
            "en": f"folder could not be listed: {exc}"}))
    if not report.inspected and not report.findings and not report.skipped:
        # "CLEAN - 0 file(s) inspected" would be a false all-clear
        report.skip(", ".join(args.paths), _localize({
            "tr": "denetlenecek .xml ya da kaynak dosyasi bulunamadi",
            "en": "no .xml or resource file found to inspect"}))

    threshold = {"fatal": FATAL, "silent": SILENT, "warn": WARN}[args.level]
    print_report(report, threshold)

    if any(f.level in {s for s in (FATAL, SILENT, WARN) if SEVERITY_ORDER[s] <= SEVERITY_ORDER[threshold]}
           for f in report.findings):
        return 1
    if report.skipped:
        return 2
    return 0
