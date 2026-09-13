#!/usr/bin/env python3
"""structural_diff.py — compares two resources by WHICH NODES EXIST.

WHY STRUCTURE, NOT VALUES
=========================
An export reporting "0 warnings" does NOT SHOW that the file is correct.
Measured case: a ped .yft written by Sollumz crashed the game in ~4 seconds;
the export had not given a single warning. The cause was not a WRONG VALUE in
a field but a node that DID NOT EXIST AT ALL. No check that compares values
field by field catches that; a "which nodes exist, which do not" comparison
does.

Measurement (made while this tool was written): vanilla mp_m_freemode_01.yft
has NO `<Physics>` node at all. So the advice "ship the ped .yft without
physics" is what vanilla already does -- and an extra `Physics` node shows up
in this diff as "IN YOURS, NOT IN VANILLA".

THE BOUNDARY IS REPORTED
========================
When a whole subtree is missing, printing each descendant separately is noise
(if `Physics` is missing, the 200 paths under it are missing too). So only
paths whose PARENT EXISTS ON BOTH SIDES are reported: the boundary where the
difference starts.

USAGE
=====
    python assetdb.py diff <yours> <vanilla>
    python assetdb.py diff mine.yft vanilla.yft --limit 40
"""
from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_xml import read_root  # noqa: E402

# The same path exists on both sides but the counts are very different.
# The threshold is not a measured constant, it is a noise filter: a difference
# of 2x or more signals "a different structure", not "the same structure
# filled differently".
COUNT_RATIO = 2.0


def path_counter(root):
    """{node path without indices: count}. Indices are dropped so that Item[3]
    and Item[7] count as the same path -- what is compared is structure, not
    content."""
    counter = collections.Counter({root.tag: 1})
    stack = [(root, root.tag)]
    while stack:
        el, path = stack.pop()
        for c in el:
            p = f"{path}/{c.tag}"
            counter[p] += 1
            stack.append((c, p))
    return counter


def _parent(path):
    return path.rsplit("/", 1)[0] if "/" in path else None


def boundary_paths(missing, common):
    """The paths where the difference STARTS: those whose parent exists on both sides."""
    return [p for p in missing if _parent(p) is None or _parent(p) in common]


def compare(a_counter, b_counter):
    """a=yours, b=vanilla. Returns (missing_in_yours, extra_in_yours, count_diff)."""
    a, b = set(a_counter), set(b_counter)
    common = a & b
    missing_in_yours = sorted(boundary_paths(b - a, common))
    extra_in_yours = sorted(boundary_paths(a - b, common))

    # The BOUNDARY is reported for count differences too. If a node differs
    # 3 to 1, all its children differ 3 to 1 as well; all 12 lines come from a
    # single cause. Only paths whose PARENT's counts are equal are reported:
    # where the difference starts. (Measured: custom prop vs vanilla broom ->
    # 12 lines dropped to 2, with no loss of information.)
    count_diff = []
    for p in sorted(common):
        na, nb = a_counter[p], b_counter[p]
        if na == nb:
            continue
        larger, smaller = max(na, nb), min(na, nb)
        if smaller != 0 and larger / smaller < COUNT_RATIO:
            continue
        parent = _parent(p)
        if parent and parent in common and a_counter[parent] != b_counter[parent]:
            continue  # the difference starts higher up, do not repeat it here
        count_diff.append((p, na, nb))
    return missing_in_yours, extra_in_yours, count_diff


def _print_section(title, lines, limit, explanation=""):
    if not lines:
        return
    print(f"\n=== {title} ({len(lines)}) ===")
    if explanation:
        print(f"  {explanation}")
    for s in lines[:limit]:
        print(f"  {s}")
    if len(lines) > limit:
        print(f"  ... and {len(lines) - limit} more (raise with --limit)")


def run(args):
    """Runs the diff and returns the exit code (assetdb.py calls it)."""
    from doctor_common import _localize

    root_a, error_a = read_root(args.mine)
    if error_a:
        print(f"ERROR: {args.mine}: {error_a}", file=sys.stderr)
        print("  " + _localize({
            "tr": "Karsilastirma YAPILMADI - sonuc hakkinda hicbir sey iddia edilemez.",
            "en": "Comparison NOT performed - nothing can be claimed about the result."}),
            file=sys.stderr)
        return 2
    root_b, error_b = read_root(args.vanilla)
    if error_b:
        print(f"ERROR: {args.vanilla}: {error_b}", file=sys.stderr)
        print("  " + _localize({
            "tr": "Karsilastirma YAPILMADI - sonuc hakkinda hicbir sey iddia edilemez.",
            "en": "Comparison NOT performed - nothing can be claimed about the result."}),
            file=sys.stderr)
        return 2

    if root_a.tag != root_b.tag:
        print(f"WARNING: the root nodes differ ({root_a.tag} vs {root_b.tag}) - "
              f"probably different resource types are being compared.")

    ca, cb = path_counter(root_a), path_counter(root_b)
    missing_in_yours, extra_in_yours, count_diff = compare(ca, cb)

    print(f"YOURS   : {os.path.basename(args.mine)}   ({root_a.tag}, "
          f"{len(ca)} distinct paths)")
    print(f"VANILLA : {os.path.basename(args.vanilla)}   ({root_b.tag}, "
          f"{len(cb)} distinct paths)")

    _print_section("IN VANILLA, NOT IN YOURS", missing_in_yours, args.limit,
                   "The most dangerous direction: a structure the engine expects may be missing.")
    _print_section("IN YOURS, NOT IN VANILLA", extra_in_yours, args.limit,
                   "Extra structure. If 'Physics' shows up here for a ped .yft, remove it.")
    if count_diff:
        print(f"\n=== COUNT DIFFERENCE ({len(count_diff)}) ===")
        print(f"  The same path exists on both sides but the count differs {COUNT_RATIO:g}x+.")
        for p, na, nb in count_diff[:args.limit]:
            print(f"  {p}   yours={na}  vanilla={nb}")
        if len(count_diff) > args.limit:
            print(f"  ... and {len(count_diff) - args.limit} more")

    total = len(missing_in_yours) + len(extra_in_yours) + len(count_diff)
    print()
    if total == 0:
        print("NO STRUCTURAL DIFFERENCE - both files have the same node set.")
        return 0
    print(f"{len(missing_in_yours)} missing | {len(extra_in_yours)} extra | "
          f"{len(count_diff)} count differences")
    return 1
