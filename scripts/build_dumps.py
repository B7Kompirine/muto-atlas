#!/usr/bin/env python3
"""build_dumps.py — builds plugin data layers from DurtyFree's GTA V data dumps.

  python scripts/build_dumps.py --dump <gta-v-data-dumps folder>

Layers produced (under data/):
  peds_meta.tsv.gz       ped identity + ANIMATION/EXPRESSION links
  weapons.tsv.gz         weapon record
  weapon_parts.tsv.gz    components + liveries (in the SAME table, split by the kind column)
  vehicles.tsv.gz        vehicle record
  mlo_interiors.tsv.gz   MLO interiors, one row PER LOCATION
  ipls.tsv.gz            IPL names + bounding boxes
  world_objects.tsv.gz   world objects: family label + position + ROTATION
  dumps.meta.json        source, date, row counts

DESIGN RULES (set by measurement, read before changing):

1. THE NAME COLUMN is written AS IT IS IN THE SOURCE; joins are always built on .lower().
   Dump names are MixedCase (W_AR_ASSAULTRIFLE), the plugin layers are lower case.
   An exact join returns 0 in every family and it is SILENT - the table looks full,
   the match comes out empty, the caller says "this model does not exist".

2. In weapon_parts, components AND liveries share one table, told apart by the `kind` column.
   155 livery names are also valid COMPONENT_* names (GiveWeaponComponentToPed
   accepts them). A separate table leads to a gate that flags liveries as
   "invalid component".

3. The `dlc` column is REQUIRED in every layer. A server is pinned to a build with
   sv_enforceGameBuild; a name that EXISTS in the dump but NOT in the server's build is
   reported as "valid", and in game RequestModel never loads it, with no error in F8 either.

4. mlo_interiors is one row PER LOCATION (385 MLOs, 844 locations). The same interior
   is placed in more than one spot; one row per MLO drops 54% of the locations.

5. Empty values are written as an empty string, never as the STRING "None"/"null". In the
   source the ExpressionDictionaryName field of 732 peds is the literal string 'null' - a
   query that takes that string for a real dictionary name silently answers wrong.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import gzip
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")

# Values that stand for a real absence in the source. 'null'/'None' arrive as STRINGS.
EMPTY = {None, "", "null", "NULL", "None", "none"}


def s(v):
    """Cell value: turns absence into an empty string, strips tabs/line breaks.

    The ORDER of the type tests matters: `v in EMPTY` raises TypeError on an
    unhashable type (list/dict), so collections are handled first. Tints and
    Flags are lists; TranslatedLabel is a dict.
    """
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (list, tuple)):
        parts = []
        for x in v:
            if isinstance(x, dict):
                x = x.get("Name") or x.get("English") or ""
            if x not in EMPTY:
                parts.append(str(x))
        return ",".join(parts)
    if isinstance(v, dict):
        return s(v.get("Name") or v.get("English") or "")
    if v in EMPTY:
        return ""
    return str(v).replace("\t", " ").replace("\n", " ").replace("\r", "")


def xyz(p, nd=4):
    """{'X':..,'Y':..,'Z':..} -> three separate cells. Three empty cells when missing."""
    if not isinstance(p, dict):
        return ["", "", ""]
    return [f"{float(p.get(k, 0) or 0):.{nd}f}" for k in ("X", "Y", "Z")]


def label(t):
    """English label from a TranslatedLabel dict."""
    return s(t.get("English")) if isinstance(t, dict) else ""


def load(dump, name):
    p = os.path.join(dump, name)
    if not os.path.exists(p):
        print(f"  [!] {name} not found, this layer is skipped", file=sys.stderr)
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def write(fname, cols, rows):
    """Writes a gzip TSV (WITH a header). READS IT BACK after writing to verify."""
    path = os.path.join(DATA, fname)
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    # Read back: "the command raised no error" is not proof of a write.
    with gzip.open(tmp, "rt", encoding="utf-8") as fh:
        head = fh.readline().rstrip("\n").split("\t")
        n = sum(1 for _ in fh)
    if head != cols:
        os.remove(tmp)
        sys.exit(f"ERROR: {fname} header did not match on read-back: {head}")
    if n != len(rows):
        os.remove(tmp)
        sys.exit(f"ERROR: {fname} {len(rows)} rows written, {n} read")
    os.replace(tmp, path)
    kb = os.path.getsize(path) / 1024
    print(f"  {fname:<24} {n:>7} rows  {kb:>8.1f} KB")
    return n


# --- layers ------------------------------------------------------------------

PED_COLS = ["name", "hash", "dlc", "pedtype", "propsName", "clipDict", "blendShape",
            "exprSet", "exprDict", "exprName", "movementClipSet", "strafeClipSet",
            "gestureClipSet", "facialClipsetGroup", "visemeClipSet", "getupSet",
            "creatureMetadata", "capsule", "voiceGroup", "isStreamedGfx",
            "isHeadBlend", "boneCount"]


def build_peds(dump):
    d = load(dump, "peds.json")
    if d is None:
        return 0
    rows = []
    for p in d:
        rows.append([
            s(p.get("Name")), s(p.get("Hash")), s(p.get("DlcName")), s(p.get("Pedtype")),
            s(p.get("PropsName")), s(p.get("ClipDictionaryName")), s(p.get("BlendShapeFileName")),
            s(p.get("ExpressionSetName")), s(p.get("ExpressionDictionaryName")),
            s(p.get("ExpressionName")), s(p.get("MovementClipSet")), s(p.get("StrafeClipSet")),
            s(p.get("DefaultGestureClipSet")), s(p.get("FacialClipsetGroupName")),
            s(p.get("DefaultVisemeClipSet")), s(p.get("GetupSetHash")),
            s(p.get("CreatureMetadataName")), s(p.get("PedCapsuleName")),
            s(p.get("PedVoiceGroup")), s(p.get("IsStreamedGfx")), s(p.get("IsHeadBlendPed")),
            s(len(p.get("Bones") or [])),
        ])
    return write("peds_meta.tsv.gz", PED_COLS, rows)


WPN_COLS = ["name", "label", "hash", "dlc", "category", "model", "ammoType", "ammoModel",
            "damageType", "isVehicleWeapon", "tints", "maxAmmoSp", "maxAmmoMp",
            "componentCount", "liveryCount", "flags"]
PART_COLS = ["weapon", "kind", "name", "label", "hash", "dlc", "attachBone", "type", "isDefault"]


def build_weapons(dump):
    d = load(dump, "weapons.json")
    if d is None:
        return 0, 0
    wrows, prows = [], []
    for w in d:
        comps = w.get("Components") or []
        livs = w.get("Liveries") or []
        wrows.append([
            s(w.get("Name")), label(w.get("TranslatedLabel")), s(w.get("Hash")),
            s(w.get("DlcName")), s(w.get("Category")), s(w.get("ModelName")),
            s(w.get("AmmoType")), s(w.get("AmmoModelName")), s(w.get("DamageType")),
            s(w.get("IsVehicleWeapon")), s(w.get("Tints")),
            s(w.get("DefaultMaxAmmoSp")), s(w.get("DefaultMaxAmmoMp")),
            s(len(comps)), s(len(livs)), s(w.get("Flags")),
        ])
        for c in comps:
            prows.append([
                s(w.get("Name")), "component", s(c.get("Name")), label(c.get("TranslatedLabel")),
                s(c.get("Hash")), s(c.get("DlcName")), s(c.get("AttachBone")),
                s(c.get("Type")), s(c.get("IsDefault")),
            ])
        for l in livs:
            prows.append([
                s(w.get("Name")), "livery", s(l.get("Name")), label(l.get("TranslatedLabel")),
                s(l.get("Hash")), s(l.get("DlcName")), "", "", "",
            ])
    return (write("weapons.tsv.gz", WPN_COLS, wrows),
            write("weapon_parts.tsv.gz", PART_COLS, prows))


VEH_COLS = ["name", "displayName", "hash", "dlc", "handlingId", "layoutId", "manufacturer",
            "class", "type", "seats", "price", "wheelsCount", "hasSirens", "hasConvertible",
            "modKits", "extras", "maxSpeed", "acceleration", "flags"]


def build_vehicles(dump):
    d = load(dump, "vehicles.json")
    if d is None:
        return 0
    rows = []
    for v in d:
        rows.append([
            s(v.get("Name")), s(v.get("DisplayName")), s(v.get("Hash")), s(v.get("DlcName")),
            s(v.get("HandlingId")), s(v.get("LayoutId")), s(v.get("Manufacturer")),
            s(v.get("Class")), s(v.get("Type")), s(v.get("Seats")), s(v.get("Price")),
            s(v.get("WheelsCount")), s(v.get("HasSirens")), s(v.get("HasConvertibleRoof")),
            s(v.get("ModKits")), s(v.get("Extras")),
            s(v.get("MaxSpeed")), s(v.get("Acceleration")), s(v.get("Flags")),
        ])
    return write("vehicles.tsv.gz", VEH_COLS, rows)


MLO_COLS = ["name", "dlc", "locDlc", "x", "y", "z", "flags", "entityCount", "ytypPath", "ymapPath"]


def build_mlo(dump):
    d = load(dump, "mloInteriors.json")
    if d is None:
        return 0
    rows = []
    for m in d:
        locs = m.get("Locations") or []
        if not locs:
            # An MLO with no known location is written too; "missing" and "not placed" differ.
            rows.append([s(m.get("Name")), s(m.get("DlcName")), "", "", "", "", "",
                         s(m.get("TotalEntitiesCount")), s(m.get("FilePath")), ""])
            continue
        for lo in locs:
            x, y, z = xyz(lo.get("Position"))
            rows.append([
                s(m.get("Name")), s(m.get("DlcName")), s(lo.get("DlcName")), x, y, z,
                s(lo.get("Flags")), s(m.get("TotalEntitiesCount")),
                s(m.get("FilePath")), s(lo.get("FilePath")),
            ])
    return write("mlo_interiors.tsv.gz", MLO_COLS, rows)


IPL_COLS = ["name", "dlc", "x", "y", "z", "minX", "minY", "minZ", "maxX", "maxY", "maxZ",
            "contentFlags", "group", "category"]


def build_ipls(dump):
    d = load(dump, "ipls.json")
    if d is None:
        return 0
    rows = []
    for i in d:
        ex = i.get("ExtraData") or {}
        rows.append([s(i.get("Name")), s(i.get("DlcName"))]
                    + xyz(i.get("Position")) + xyz(i.get("DimensionMin")) + xyz(i.get("DimensionMax"))
                    + [s(i.get("ContentFlags")), s(ex.get("GroupName")), s(ex.get("Category"))])
    return write("ipls.tsv.gz", IPL_COLS, rows)


WORLD_COLS = ["family", "model", "x", "y", "z", "rx", "ry", "rz"]


def build_world(dump):
    """objectslocations/*.json -> one table. The family label comes from the file name.

    WHY IT IS VALUABLE: entities.tsv.gz says "what is where" in 3M rows but carries
    no SEMANTIC label - it cannot say "this is an ATM", and it does not hold ROTATION
    either. Loot/spawn points, anti-cheat whitelists and prop swaps need both.
    """
    dirp = os.path.join(dump, "objectslocations")
    if not os.path.isdir(dirp):
        print("  [!] objectslocations/ not found, skipped", file=sys.stderr)
        return 0
    rows, empty = [], []
    for f in sorted(glob.glob(os.path.join(dirp, "*.json"))):
        fam = os.path.basename(f)[:-5]
        if fam.startswith("world"):
            fam = fam[5:]
        fam = fam[0].lower() + fam[1:] if fam else fam
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        if not d:
            empty.append(fam)
            continue
        for o in d:
            rows.append([fam, s(o.get("Name"))] + xyz(o.get("Position")) + xyz(o.get("Rotation")))
    if empty:
        print(f"  (empty file, produced no rows: {', '.join(empty)})")
    return write("world_objects.tsv.gz", WORLD_COLS, rows)


RAW = "https://raw.githubusercontent.com/DurtyFree/gta-v-data-dumps/master/"

# Files downloaded with --fetch. objectslocations/ is handled separately.
REQUIRED = ["README.md", "peds.json", "weapons.json", "vehicles.json",
            "mloInteriors.json", "ipls.json",
            "animDictsCompact.json", "ObjectList.ini", "scenariosCompact.json"]
WORLD_FILES = ["worldAirMasts", "worldAntennas", "worldAtms", "worldBinsDumpsters",
               "worldBusStopSigns", "worldBusStops", "worldCctvs", "worldContainerCabins",
               "worldDartDiscs", "worldElectricityBoxes", "worldExtraPhones",
               "worldFireHydrantDriser", "worldFoodStands", "worldFruitStands",
               "worldGasPumps", "worldHarvestFields", "worldJukeboxes", "worldLetterBoxes",
               "worldMobileMasts", "worldNewsPaperDispensers", "worldOilJacks",
               "worldParknmeters", "worldPostBoxes", "worldPublicPhones", "worldRadioTowers",
               "worldRecycleBins", "worldSatDishes", "worldSeats", "worldStreetLights",
               "worldTelescopes", "worldTrafficLights", "worldVendingMachines",
               "worldWreckedBikes", "worldWreckedCars"]


def download(target, force=False):
    """Pulls the dump files from upstream. Creates the folder when it is missing.

    ⛔ SKIPS WHAT EXISTS. The reason was measured: "do not download if the folder is
    not empty" logic fails silently when a file is ADDED to the source list later —
    the folder looks full, the new files never arrive, those layers say "skipped"
    and the user does not know why. Checking per file removes this at the root.
    """
    import urllib.request
    os.makedirs(os.path.join(target, "objectslocations"), exist_ok=True)
    jobs = [(RAW + f, os.path.join(target, f)) for f in REQUIRED]
    jobs += [(RAW + "objectslocations/" + f + ".json",
              os.path.join(target, "objectslocations", f + ".json")) for f in WORLD_FILES]
    failed = skipped = 0
    for i, (url, dest) in enumerate(jobs, 1):
        if not force and os.path.exists(dest) and os.path.getsize(dest) > 0:
            skipped += 1
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fivem-natives-plugin"})
            with urllib.request.urlopen(req, timeout=120) as r:
                payload = r.read()
            with open(dest, "wb") as fh:
                fh.write(payload)
            print(f"  [{i:>2}/{len(jobs)}] {os.path.basename(dest):<34} {len(payload)/1024:>8.0f} KB")
        except Exception as e:
            failed += 1
            print(f"  [{i:>2}/{len(jobs)}] {os.path.basename(dest):<34} ERROR: {e}", file=sys.stderr)
    if skipped:
        print(f"  ({skipped} files already existed, skipped)")
    if failed:
        print(f"\n  {failed} files could not be downloaded. The layer of a missing file is skipped.",
              file=sys.stderr)
    return failed


def write_headerless(fname, lines):
    """HEADERLESS gzip TSV. anims/props/scenarios are headerless for historical reasons;
    adding a header breaks assetdb.py's gz_lines(header=False) read and the first
    record is silently taken for a 'header' and dropped."""
    path = os.path.join(DATA, fname)
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8", newline="\n") as fh:
        for line in lines:
            fh.write(line + "\n")
    with gzip.open(tmp, "rt", encoding="utf-8") as fh:
        n = sum(1 for _ in fh)
    if n != len(lines):
        os.remove(tmp)
        sys.exit(f"ERROR: {fname} {len(lines)} written, {n} read")
    os.replace(tmp, path)
    print(f"  {fname:<24} {n:>7} rows  {os.path.getsize(path)/1024:>8.1f} KB")
    return n


def build_anim(dump):
    """animDictsCompact.json -> anims.tsv.gz  (dict<TAB>clip, headerless)

    NOTE: 408 dictionaries have ZERO animations (all of them cutscene slices with a
    '-N' suffix) and produce no rows. The README says 20179 dicts, 19771 go into the
    file - that is the difference, not a loss.
    """
    d = load(dump, "animDictsCompact.json")
    if d is None:
        return 0
    lines = []
    for e in d:
        dn = e.get("DictionaryName") or ""
        for c in (e.get("Animations") or []):
            lines.append(f"{dn}\t{c}")
    return write_headerless("anims.tsv.gz", lines)


def build_props(dump):
    """ObjectList.ini -> props.tsv.gz (one name per line)"""
    p = os.path.join(dump, "ObjectList.ini")
    if not os.path.exists(p):
        print("  [!] ObjectList.ini not found, props skipped", file=sys.stderr)
        return 0
    names = [l.strip() for l in open(p, encoding="utf-8", errors="replace") if l.strip()]
    return write_headerless("props.tsv.gz", names)


def build_scenarios(dump):
    d = load(dump, "scenariosCompact.json")
    if d is None:
        return 0
    return write_headerless("scenarios.tsv.gz", [str(x) for x in d if x])


def main():
    ap = argparse.ArgumentParser(description="GTA V data dump -> plugin data layers")
    ap.add_argument("--dump", required=True, help="gta-v-data-dumps folder")
    ap.add_argument("--fetch", action="store_true",
                    help="download the missing source files (skips what exists)")
    ap.add_argument("--force-fetch", action="store_true",
                    help="download existing files again as well")
    ap.add_argument("--only", nargs="*", help="only these layers (peds weapons vehicles mlo ipls world anim props scenarios)")
    a = ap.parse_args()

    if a.fetch or a.force_fetch:
        print(f"Downloading -> {a.dump}\n")
        os.makedirs(a.dump, exist_ok=True)
        download(a.dump, force=a.force_fetch)
        print()
    if not os.path.isdir(a.dump):
        sys.exit(f"ERROR: dump folder not found: {a.dump}\n"
                 f"  To download it: add --fetch")
    os.makedirs(DATA, exist_ok=True)

    # The dump version is read from the README's first 'update:' line (never written by hand).
    version = ""
    rp = os.path.join(a.dump, "README.md")
    if os.path.exists(rp):
        for line in open(rp, encoding="utf-8"):
            if "up2date as of GTA V update" in line:
                version = line.strip().replace("*", "").split("update:")[-1].strip()
                break

    print(f"Dump   : {a.dump}")
    print(f"Version: {version or '(README could not be read)'}")
    print(f"Target : {DATA}\n")

    selected = set(a.only) if a.only else None
    counts = {}

    def wanted(k):
        return selected is None or k in selected

    if wanted("peds"):
        counts["peds_meta"] = build_peds(a.dump)
    if wanted("weapons"):
        counts["weapons"], counts["weapon_parts"] = build_weapons(a.dump)
    if wanted("vehicles"):
        counts["vehicles"] = build_vehicles(a.dump)
    if wanted("mlo"):
        counts["mlo_interiors"] = build_mlo(a.dump)
    if wanted("ipls"):
        counts["ipls"] = build_ipls(a.dump)
    if wanted("world"):
        counts["world_objects"] = build_world(a.dump)
    if wanted("anim"):
        counts["anims"] = build_anim(a.dump)
    if wanted("props"):
        counts["props"] = build_props(a.dump)
    if wanted("scenarios"):
        counts["scenarios"] = build_scenarios(a.dump)

    meta_p = os.path.join(DATA, "dumps.meta.json")
    previous = {}
    if os.path.exists(meta_p):
        try:
            previous = json.load(open(meta_p, encoding="utf-8")).get("rows", {})
        except Exception:
            previous = {}
    previous.update(counts)
    with open(meta_p, "w", encoding="utf-8") as fh:
        json.dump({
            "generatedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source": "https://github.com/DurtyFree/gta-v-data-dumps",
            "dumpPath": a.dump,
            "gameVersion": version,
            "rows": previous,
        }, fh, indent=2, ensure_ascii=False)

    print(f"\n{sum(counts.values())} rows produced, {len(counts)} layers.")
    print(f"meta: {meta_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
