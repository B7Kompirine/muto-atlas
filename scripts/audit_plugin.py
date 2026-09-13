"""audit_plugin.py -- muto-atlas plugin integrity audit.

WHY: as the plugin grows, links break silently. A command points at a reference
that no longer exists, a reference is linked from nowhere, a .ps1 loses its BOM
and PowerShell 5.1 misreads it -- none of these raise an error.

What is checked:
  1. plugin.json / marketplace.json parse, and their names match
  2. command frontmatter is complete and its description is in English
  3. every linked references/*.md exists (BOTH skill folders -- an auditor that
     looks at only one folder produces false positives; it happened)
  4. ORPHAN references that nothing links to
  5. every linked scripts/* exists (except ones marked "not written yet")
  6. .ps1 files that contain non-ASCII characters have a BOM
  7. SKILL.md frontmatter matches its folder name
  8. TREE: branches/<branch>/_branch.md exists, leaf table <-> disk, orphan leaves,
     SKILL.md mentions every branch, line limits for _branch.md / SKILL.md, move log
  9. a trunk rule repeated in a leaf (short item) -> NOTE
 10. overlap: repeated headings / identical copied blocks
 11. counter consistency (layers / branches / leaves / commands) + orphan scripts
 12. Turkish characters left in the knowledge or command text -> NOTE

Exit code: 1 when a problem is found, 0 when clean.

Usage:  python scripts/audit_plugin.py [--lang en|tr]
        The report language follows the same rule as the other scripts:
        --lang > MUTO_ATLAS_LANG > config > en.
"""
import argparse
import io
import json
import os
import re
import sys

A = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(A, "scripts"))
from i18n import add_lang_arg, get_lang, set_lang  # noqa: E402

_ap = argparse.ArgumentParser(description="muto-atlas plugin integrity audit (exit 1 when a problem is found)")
add_lang_arg(_ap)
_lang = _ap.parse_args().lang
if _lang:
    set_lang(_lang)
EN = get_lang() == "en"


def L(tr, en):
    """One report line in both languages; which one prints follows the i18n rule."""
    return en if EN else tr


problems, notes = [], []
TR_CHARS = set("çğıöşüÇĞİÖŞÜ")
# leaf table row in _branch.md:  | wanted | file.md | status — source |
LEAF_ROW = re.compile(r"^\|[^|\n]*\|\s*([A-Za-z0-9._-]+\.md)\s*\|([^\n]*)$", re.M)
PLANNED = "to be moved"


def read(path):
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def rel(path):
    return os.path.relpath(path, A).replace("\\", "/")


def skipped(root):
    parts = root.replace("\\", "/").split("/")
    return ".git" in parts or "_archive" in parts or "__pycache__" in parts


# ---------- 1. JSON ----------
plugin_json = os.path.join(A, ".claude-plugin", "plugin.json")
marketplace_json = os.path.join(A, ".claude-plugin", "marketplace.json")
for p in (plugin_json, marketplace_json):
    try:
        json.loads(read(p))
        notes.append(f"JSON ok: {rel(p)}")
    except Exception as e:
        problems.append(L(f"JSON BOZUK: {rel(p)} -> {e}", f"BROKEN JSON: {rel(p)} -> {e}"))

pj = json.loads(read(plugin_json))
mj = json.loads(read(marketplace_json))
if pj["name"] != mj["plugins"][0]["name"]:
    problems.append(L(f"plugin adi uyusmuyor: {pj['name']} vs {mj['plugins'][0]['name']}",
                      f"plugin name mismatch: {pj['name']} vs {mj['plugins'][0]['name']}"))

# ---------- 2. command frontmatter ----------
cmd_dir = os.path.join(A, "commands")
cmds = sorted(f for f in os.listdir(cmd_dir) if f.endswith(".md"))
for f in cmds:
    txt = read(os.path.join(cmd_dir, f))
    if not txt.startswith("---"):
        problems.append(L(f"komut frontmatter YOK: {f}", f"command has NO frontmatter: {f}"))
        continue
    fm = txt.split("---", 2)[1]
    if not re.search(r"^description:", fm, re.M):
        problems.append(L(f"komut '{f}': 'description' alani eksik", f"command '{f}': 'description' field missing"))
    for key in ("argument-hint", "allowed-tools"):
        if not re.search(rf"^{key}:", fm, re.M):
            notes.append(L(f"komut '{f}': '{key}' yok (istege bagli)", f"command '{f}': no '{key}' (optional)"))
    m = re.search(r"^description:\s*(.+)$", fm, re.M)
    if m and (set(m.group(1)) & TR_CHARS):
        problems.append(L(f"komut '{f}': description TURKCE karakter iceriyor (konvansiyon: Ingilizce)",
                          f"command '{f}': description contains TURKISH characters (convention: English)"))

# ---------- 3. references: present / orphan ----------
ref_dirs = [os.path.join(A, "skills", s, "references") for s in ("fivem-assets", "fivem-natives")]
refs_on_disk = set()
for d in ref_dirs:
    if os.path.isdir(d):
        refs_on_disk |= {f for f in os.listdir(d) if f.endswith(".md")}

text_files = []
for root, _, files in os.walk(A):
    if skipped(root):
        continue
    for f in files:
        if f.endswith((".md", ".ps1", ".py", ".yml")):
            text_files.append(os.path.join(root, f))

mentioned = set()
for p in text_files:
    for m in re.finditer(r"references/([A-Za-z0-9._-]+\.md)", read(p)):
        mentioned.add(m.group(1))
for r in sorted(mentioned - refs_on_disk):
    problems.append(L(f"ATIF VAR DOSYA YOK: references/{r}", f"REFERENCED FILE MISSING: references/{r}"))
for r in sorted(refs_on_disk - mentioned):
    problems.append(L(f"YETIM REFERANS (hicbir yerden atif yok): references/{r}",
                      f"ORPHAN REFERENCE (nothing links to it): references/{r}"))

# ---------- 8. TREE: trunk/ + branches/<branch>/ + sources/ ----------
# WHY: the knowledge lives in a trunk / branch / leaf tree. A leaf missing from its
# _branch.md table cannot be reached (orphan); a table row without a file is a broken
# link. A growing _branch.md or SKILL.md gets a note.
FA = os.path.join(A, "skills", "fivem-assets")
trunk_dir = os.path.join(FA, "trunk")
branches_dir = os.path.join(FA, "branches")
sources_dir = os.path.join(FA, "sources")
skill_txt = read(os.path.join(FA, "SKILL.md"))
branches = sorted(d for d in os.listdir(branches_dir)
                  if os.path.isdir(os.path.join(branches_dir, d))) if os.path.isdir(branches_dir) else []


def branch_file(branch):
    return os.path.join(branches_dir, branch, "_branch.md")


tree_on_disk = set()
for base in (trunk_dir, branches_dir, sources_dir):
    if os.path.isdir(base):
        for root, _, files in os.walk(base):
            for f in files:
                if f.endswith(".md"):
                    tree_on_disk.add(os.path.relpath(os.path.join(root, f), FA).replace("\\", "/"))

tree_mentioned = set()
for p in text_files:
    for m in re.finditer(r"(?<![A-Za-z0-9_-])(?:trunk|branches|sources)/[A-Za-z0-9._/-]+?\.md", read(p)):
        tree_mentioned.add(m.group(0))

# planned leaves (to be moved): a link to one is a note, not a problem
planned_all = set()
for b in branches:
    if os.path.exists(branch_file(b)):
        for row in LEAF_ROW.finditer(read(branch_file(b))):
            if PLANNED in row.group(2):
                planned_all.add(f"branches/{b}/{row.group(1)}")
for r in sorted(tree_mentioned - tree_on_disk):
    if r in planned_all:
        notes.append(L(f"planli yapraga atif (henuz yazilmadi): {r}", f"link to a planned leaf (not written yet): {r}"))
    else:
        problems.append(L(f"ATIF VAR DOSYA YOK: {r}", f"REFERENCED FILE MISSING: {r}"))

for b in branches:
    bp = os.path.join(branches_dir, b)
    if not os.path.exists(branch_file(b)):
        problems.append(L(f"DAL DOSYASI YOK: branches/{b}/_branch.md", f"BRANCH FILE MISSING: branches/{b}/_branch.md"))
        continue
    bt = read(branch_file(b))
    listed, planned = set(), set()
    for row in LEAF_ROW.finditer(bt):
        f, status = row.group(1), row.group(2)
        if f == "_branch.md":
            continue
        (planned if PLANNED in status else listed).add(f)
    on_disk = {f for f in os.listdir(bp) if f.endswith(".md") and f != "_branch.md"}
    for f in sorted(listed - on_disk):
        problems.append(L(f"branches/{b}/_branch.md yaprak listeliyor, dosya yok: {f}",
                          f"branches/{b}/_branch.md lists a leaf that does not exist: {f}"))
    for f in sorted(on_disk - listed - planned):
        problems.append(L(f"YETIM YAPRAK (dal tablosunda yok): branches/{b}/{f}",
                          f"ORPHAN LEAF (not in the branch table): branches/{b}/{f}"))
    for f in sorted(planned & on_disk):
        problems.append(L(f"branches/{b}/{f} yazilmis ama tabloda hala '{PLANNED}': durumu guncelle",
                          f"branches/{b}/{f} exists but its table row still says '{PLANNED}': update it"))
    if planned - on_disk:
        notes.append(L(f"branches/{b}: {len(planned - on_disk)} yaprak henuz tasinmadi",
                       f"branches/{b}: {len(planned - on_disk)} leaves not moved yet"))
    n = bt.count("\n")
    if n > 150:
        notes.append(L(f"branches/{b}/_branch.md {n} satir (>150) -> fazlasi yapraga insin",
                       f"branches/{b}/_branch.md is {n} lines (>150) -> move the extra into leaves"))
    if f"branches/{b}/" not in skill_txt:
        problems.append(L(f"SKILL.md 'branches/{b}/' dalini anmiyor", f"SKILL.md does not mention the 'branches/{b}/' branch"))
    # move log: a leaf whose Source line still names a file under references/
    for f in sorted(on_disk):
        m = re.search(r"\*\*Source:\*\*\s*(.+)", read(os.path.join(bp, f)))
        if m:
            for old in re.findall(r"([A-Za-z0-9._-]+\.md)", m.group(1)):
                if old in refs_on_disk:
                    notes.append(L(f"branches/{b}/{f}: kaynak references/{old} hala duruyor (tasima bitmemis)",
                                   f"branches/{b}/{f}: its source references/{old} still exists (move not finished)"))

# trunk criterion: a trunk file should be named in at least 4 branch files (does it hold everywhere?)
if os.path.isdir(trunk_dir):
    for tf in sorted(f for f in os.listdir(trunk_dir) if f.endswith(".md")):
        count = sum(1 for b in branches if os.path.exists(branch_file(b)) and tf in read(branch_file(b)))
        if count < 4 and tf != "gta-fundamentals.md":
            notes.append(L(f"trunk/{tf}: yalniz {count}/{len(branches)} dalda aniliyor -> her dalda gecerli mi, yoksa sources/ mi?",
                           f"trunk/{tf}: mentioned in only {count}/{len(branches)} branches -> does it hold for every branch, or belong in sources/?"))

n = skill_txt.count("\n")
if n > 250:
    notes.append(L(f"fivem-assets/SKILL.md {n} satir (>250) -> trunk/ altina in",
                   f"fivem-assets/SKILL.md is {n} lines (>250) -> move content into trunk/"))

# ---------- 9. A TRUNK RULE REPEATED IN A LEAF (note) ----------
# WHY: the tree keeps a shared rule ONCE, in the trunk or a _branch.md. A short
# (<= 3 lines) item in a leaf that only carries a trunk rule goes stale; point at the
# trunk ("-> trunk/tool-pitfalls.md") instead of repeating it.
TRUNK_RULES = [
    ("reconnect", r"reconnect|restart is not enough"),
    ("LiteralPath", r"-literalpath"),
    ("xml_to_ycd", r"xml_to_ycd\.ps1|outside the format system"),
    ("Hash is not written", r"<hash>.{0,30}(not written|does not write)|fix_ycd_xml"),
    ("24 fps", r"24 fps"), ("Mesh Domain", r"mesh domain"), ("$null", r"\$null\.length"),
    ("size is not a criterion", r"size.{0,30}(is not|not a) (criterion|measure)"),
    ("screenshot", r"screenshot.{0,20}not a measurement"),
    ("the tool not showing it", r"the tool (not showing|does not show)"),
    ("use_custom_settings", r"use_custom_settings"),
    ("sz_lods", r"sz_lods\.high\.mesh"), ("hide_select", r"hide_select"), ("target_id", r"target_id.{0,40}(data|armature)"),
    ("-File array", r"-file.{0,40}(single string|comma)"), ("pymateria", r"pymateria"), ("PYTHONIOENCODING", r"pythonioencoding"),
]
SPECIFIC = re.compile(r"measured|measurement|\d{3,}|this (round|project|task|session)|happened|example|→ ?`?(trunk|branches)/", re.I)
BULLET = re.compile(r"^(\s*)([-*]|\d+[a-z]?\.)\s+")
repeats = 0
for b in branches:
    bp = os.path.join(branches_dir, b)
    for f in sorted(os.listdir(bp)):
        if not f.endswith(".md") or f == "_branch.md":
            continue
        lines = read(os.path.join(bp, f)).split("\n")
        i = 0
        while i < len(lines):
            m = BULLET.match(lines[i])
            if not m:
                i += 1
                continue
            indent, j = len(m.group(1)), i + 1
            while (j < len(lines) and lines[j].strip() and (len(lines[j]) - len(lines[j].lstrip())) > indent
                   and not BULLET.match(lines[j])):
                j += 1
            block = "\n".join(lines[i:j])
            if (j - i) <= 3 and not SPECIFIC.search(block):
                hit = [name for name, rx in TRUNK_RULES if re.search(rx, block.lower())]
                if hit:
                    repeats += 1
                    notes.append(L(f"yaprakta govde kurali tekrari ({hit[0]}): branches/{b}/{f}: {lines[i].strip()[:70]}",
                                   f"trunk rule repeated in a leaf ({hit[0]}): branches/{b}/{f}: {lines[i].strip()[:70]}"))
            i = j
if repeats == 0:
    notes.append(L("yaprak/govde tekrari: 0 (kisa madde olcutuyle)", "leaf/trunk repeats: 0 (short-item check)"))

# ---------- 10. OVERLAP: repeated heading + identical copied block ----------
# WHY: the tree promises "once, in the widest place". A heading that appears twice in
# one file means either a copied block (the knowledge splits and one copy goes stale)
# or two things sharing one name (search leads to the wrong place). A long identical
# block in two files is the same defect.
live = []
for root, _, files in os.walk(FA):
    if skipped(root):
        continue
    live += [os.path.join(root, f) for f in files if f.endswith(".md")]

overlap = 0
HEADING = re.compile(r"^#{2,4}\s+(.+?)\s*$", re.M)
for p in sorted(live):
    counts = {}
    for m in HEADING.finditer(read(p)):
        counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    for heading, times in counts.items():
        # a short, generic sub-heading (Measured, In order, Verification...) can
        # appear in several sections of one file; that is not a copy.
        if times > 1 and len(heading) >= 14:
            overlap += 1
            problems.append(L("TEKRARLANAN BASLIK: %s icinde '%s' %d kez — blok kopyalanmis ya da iki ayri sey ayni adi tasiyor"
                              % (rel(p), heading[:60], times),
                              "REPEATED HEADING: '%s' appears %d times in %s — a block was copied, or two different things share one name"
                              % (heading[:60], times, rel(p))))


def meaningful(lines):
    out = []
    for i, line in enumerate(lines):
        s = line.strip()
        if len(s) >= 30 and not s.startswith(("|---", "---", "```", "#")):
            out.append((i, s))
    return out


windows = {}
for p in sorted(live):
    kept = meaningful(read(p).split("\n"))
    for j in range(len(kept) - 5):
        if kept[j + 5][0] - kept[j][0] > 12:   # too many gaps in between: not a block
            continue
        windows.setdefault(tuple(s for _, s in kept[j:j + 6]), []).append((rel(p), kept[j][0] + 1))
signatures = set()
for places in windows.values():
    if len(places) < 2:
        continue
    signature = tuple(sorted(set(place[0] for place in places)))
    if signature in signatures:
        continue
    signatures.add(signature)
    overlap += 1
    where = " · ".join("%s:%d" % place for place in places[:3])
    problems.append(L("BIREBIR KOPYA BLOK (>=6 satir): " + where + " — bilgi bir kez, en genis yerde yazilir",
                      "IDENTICAL BLOCK (>=6 lines): " + where + " — write knowledge once, in the widest place"))
if not overlap:
    notes.append(L("ortusme: tekrarlanan baslik 0, birebir kopya blok 0 (%d canli md)" % len(live),
                   "overlap: repeated headings 0, identical blocks 0 (%d live md files)" % len(live)))

# ---------- 5. scripts: every linked script exists ----------
script_dir = os.path.join(A, "scripts")
scripts_on_disk = {f for f in os.listdir(script_dir) if f.endswith((".py", ".ps1")) and not f.startswith("_")}
script_mentioned = set()
for p in text_files:
    for m in re.finditer(r"scripts/([A-Za-z0-9._-]+\.(?:py|ps1))", read(p)):
        script_mentioned.add(m.group(1))
all_text = "\n".join(read(p) for p in text_files)
for s in sorted(script_mentioned - scripts_on_disk):
    context = re.search("scripts/" + re.escape(s) + r"[^\n]*", all_text)
    line = context.group(0) if context else ""
    if "not written yet" in line or "TODO" in line:
        notes.append(L(f"scripts/{s}: atif var, dosya yok — ama belgede 'henuz yazilmadi' diye ISARETLI (bilinen acik is)",
                       f"scripts/{s}: referenced but missing — MARKED 'not written yet' in the docs (known open work)"))
    else:
        problems.append(L(f"ATIF VAR BETIK YOK: scripts/{s}", f"REFERENCED SCRIPT MISSING: scripts/{s}"))

# ---------- slash command links ----------
cmd_names = {f[:-3] for f in cmds}
referred_cmds = set()
for p in text_files:
    for m in re.finditer(r"(?i)command:\s*`?/([a-z0-9-]+)`?|`/([a-z0-9-]+)`", read(p)):
        referred_cmds.add((m.group(1) or m.group(2)).lower())
# IN-GAME / EXTERNAL commands run on a FiveM server or in another tool; they are
# NOT plugin commands. A missing command that is not on this list is a REAL broken
# link (a plugin command was removed but a link to it stayed) -> PROBLEM.
KNOWN_EXTERNAL = {
    # our own in-game commands, installed on a test server for measurements
    "pxm", "pxmturn", "pxmdel", "pxmprobe", "dev", "obje", "panel",
    "lapnext", "latest",
    "ptfx", "ptfxdur", "ptfxkat", "ptfxsira", "ptfxt1", "spor",
    # Claude Code's own commands
    "timecycle", "loop", "schedule", "help",
}
missing_cmds = sorted(referred_cmds - cmd_names - KNOWN_EXTERNAL)
for c in missing_cmds:
    problems.append(L(f"KIRIK KOMUT ATIFI: '/{c}' aniliyor ama commands/{c}.md yok "
                      f"(plugin komutu kaldirildiysa atiflari da guncelle; oyun ici komutsa KNOWN_EXTERNAL'a ekle)",
                      f"BROKEN COMMAND LINK: '/{c}' is mentioned but commands/{c}.md does not exist "
                      f"(if the plugin command was removed, update the links; if it is an in-game command, add it to KNOWN_EXTERNAL)"))
if not missing_cmds:
    notes.append(L(f"komut atiflari: {len(referred_cmds & cmd_names)} gecerli, kirik 0",
                   f"command links: {len(referred_cmds & cmd_names)} valid, 0 broken"))

# ---------- 6. ps1 BOM ----------
for f in sorted(os.listdir(script_dir)):
    if not f.endswith(".ps1"):
        continue
    with open(os.path.join(script_dir, f), "rb") as fh:
        raw = fh.read()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    non_ascii = any(byte > 127 for byte in raw[3:] if has_bom) if has_bom else any(byte > 127 for byte in raw)
    if non_ascii and not has_bom:
        problems.append(L(f"BOM EKSIK ve ASCII disi karakter var: scripts/{f} (PowerShell 5.1 bozuk okur)",
                          f"MISSING BOM with non-ASCII characters: scripts/{f} (PowerShell 5.1 misreads it)"))
    elif not non_ascii and not has_bom:
        notes.append(L(f"scripts/{f}: BOM yok ama saf ASCII -> sorun degil",
                       f"scripts/{f}: no BOM but pure ASCII -> fine"))

# ---------- 7. SKILL.md ----------
for skill in ("fivem-assets", "fivem-natives"):
    p = os.path.join(A, "skills", skill, "SKILL.md")
    if not os.path.exists(p):
        problems.append(L(f"SKILL.md yok: {skill}", f"SKILL.md missing: {skill}"))
        continue
    t = read(p)
    if not t.startswith("---"):
        problems.append(L(f"{skill}/SKILL.md frontmatter yok", f"{skill}/SKILL.md has no frontmatter"))
        continue
    fm = t.split("---", 2)[1]
    if not re.search(r"^name:\s*" + re.escape(skill) + r"\s*$", fm, re.M):
        problems.append(L(f"{skill}/SKILL.md: 'name' alani klasor adiyla uyusmuyor",
                          f"{skill}/SKILL.md: 'name' does not match the folder name"))
    if not re.search(r"^description:", fm, re.M):
        problems.append(L(f"{skill}/SKILL.md: description yok", f"{skill}/SKILL.md: no description"))

# ---------- 11. COUNTER CONSISTENCY + ORPHAN SCRIPTS ----------
# WHY: a number written into a document by hand drifts. Measured: the docs once gave
# three different data-layer counts at the same time (README 28 / README.tr 24 /
# help.md 24) while setup.py really had 27. Count from disk, compare with the docs.
docs = {}
for f in ("README.md", os.path.join("docs", "README.tr.md")):
    if os.path.exists(os.path.join(A, f)):
        docs[f] = read(os.path.join(A, f))
all_docs = "\n".join(docs.values())
# the layer count is also written in the plugin manifests and the contributor guides
layer_docs = dict(docs)
for f in (os.path.join(".claude-plugin", "plugin.json"), os.path.join(".claude-plugin", "marketplace.json"),
          "AGENTS.md", "CONTRIBUTING.md", os.path.join("docs", "CONTRIBUTING.tr.md")):
    if os.path.exists(os.path.join(A, f)):
        layer_docs[f] = read(os.path.join(A, f))
layer_text = "\n".join(layer_docs.values())

# 11a. data layers: setup.py's OWN list (imported, not guessed)
layer_count = None
try:
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("_atlas_setup", os.path.join(A, "scripts", "setup.py"))
    module = ilu.module_from_spec(spec)
    spec.loader.exec_module(module)
    layers = getattr(module, "LAYERS", None) or getattr(module, "KATMANLAR", None)
    layer_count = len(layers) if layers is not None else None
    if layer_count is None:
        notes.append(L("setup.py'de katman listesi yok", "setup.py has no layer list"))
except Exception as e:
    notes.append(L("katman sayisi okunamadi (setup.py import): %s" % e, "could not read the layer count (setup.py import): %s" % e))
if layer_count:
    # an exit-code line such as "2 data layers not installed" is not a claim about the total
    claims = re.findall(r"(\d+)\s*(?:offline data layers|çevrimdışı veri katmanı|veri katmanı|data layers)(?!\s*(?:kurulu|not installed))",
                        layer_text)
    for written in sorted(set(claims)):
        if int(written) != layer_count:
            problems.append(L("SAYAC KAYMASI: belgede '%s veri katmani' yaziyor, setup.py'de %d katman var" % (written, layer_count),
                              "COUNTER DRIFT: the docs say '%s data layers', setup.py has %d" % (written, layer_count)))
    # setup.py's own docstring once said "all 28 layers" while its list had 24
    for written in sorted(set(re.findall(r"\ball\s+(\d+)\s+(?:data\s+)?layers\b", read(os.path.join(A, "scripts", "setup.py"))))):
        if int(written) != layer_count:
            problems.append(L("SAYAC KAYMASI: scripts/setup.py 'all %s layers' diyor, kendi listesinde %d katman var" % (written, layer_count),
                              "COUNTER DRIFT: scripts/setup.py says 'all %s layers', its own list has %d" % (written, layer_count)))
    for f, t in layer_docs.items():
        for written in set(re.findall(r"N/(\d+)\s*(?:katman|layers)", t)):
            problems.append(L("SABIT KATMAN SAYISI: %s icinde 'N/%s' — sayiyi yazma, setup.py hesaplar" % (f, written),
                              "HARD-CODED LAYER COUNT: 'N/%s' in %s — do not write the number, setup.py computes it" % (written, f)))

# 11b. branch / leaf / command counters (Turkish patterns read docs/README.tr.md)
on_disk_counts = {
    "branch": len(branches),
    "leaf": sum(len([f for f in os.listdir(os.path.join(branches_dir, b)) if f.endswith(".md") and f != "_branch.md"])
                for b in branches),
    "command": len(cmds),
}
COUNTER_PATTERNS = {
    "branch": (r"(\d+)\s*dal\b", r"(\d+)\s*branches\b"),
    "leaf": (r"(\d+)\s*yaprak\b", r"(\d+)\s*leaves\b"),
    "command": (r"(\d+)\s*komut\b", r"(\d+)\s*commands\b"),
}
COUNTER_NAMES = {"branch": ("dal", "branches"), "leaf": ("yaprak", "leaves"), "command": ("komut", "commands")}
for key, patterns in COUNTER_PATTERNS.items():
    for pattern in patterns:
        for written in set(re.findall(pattern, all_docs)):
            if int(written) != on_disk_counts[key]:
                tr_name, en_name = COUNTER_NAMES[key]
                problems.append(L("SAYAC KAYMASI: belgede '%s %s' yaziyor, diskte %d var" % (written, tr_name, on_disk_counts[key]),
                                  "COUNTER DRIFT: the docs say '%s %s', %d on disk" % (written, en_name, on_disk_counts[key])))

# 11c. orphan script: not named in any document AND not called by another script
all_scripts = sorted(f for f in os.listdir(script_dir) if f.endswith((".py", ".ps1")))
corpus = all_docs
for root, _, files in os.walk(FA):
    if skipped(root):
        continue
    for f in files:
        if f.endswith(".md"):
            corpus += read(os.path.join(root, f))
for f in os.listdir(cmd_dir):
    corpus += read(os.path.join(cmd_dir, f))
code = {s: read(os.path.join(script_dir, s)) for s in all_scripts}


def is_named(script):
    stem, ext = os.path.splitext(script)
    if script in corpus or stem in corpus:
        return True
    parts = stem.split("_")
    return any("_" + "_".join(parts[k:]) + ext in corpus for k in range(1, len(parts)))


orphans = []
for s in all_scripts:
    if is_named(s):
        continue
    stem = os.path.splitext(s)[0]
    if any(other != s and stem in source for other, source in code.items()):
        continue          # called by another script -> an internal helper, fine
    orphans.append(s)
if orphans:
    for s in orphans:
        notes.append(L("yetim betik: scripts/%s hicbir belgede anilmiyor ve hicbir betikten cagrilmiyor" % s,
                       "orphan script: scripts/%s is not mentioned in any doc and not called by any script" % s))
else:
    notes.append(L("yetim betik: 0 (%d betik tarandi)" % len(all_scripts), "orphan scripts: 0 (%d scripts scanned)" % len(all_scripts)))

# ---------- 12. Turkish text left in the English knowledge ----------
# WHY: the public knowledge, skills and commands are English. Turkish text that slips
# back in cannot be read by most people who use the repository.
turkish = []
for base in (os.path.join(A, "skills"), cmd_dir):
    for root, _, files in os.walk(base):
        if skipped(root):
            continue
        for f in sorted(files):
            if f.endswith(".md"):
                hits = [i for i, line in enumerate(read(os.path.join(root, f)).splitlines(), 1) if set(line) & TR_CHARS]
                if hits:
                    turkish.append((rel(os.path.join(root, f)), len(hits), hits[0]))
for path, count, first in turkish[:10]:
    notes.append(L(f"Turkce karakter: {path} ({count} satir, ilki {first}. satir)",
                   f"Turkish characters: {path} ({count} lines, first at line {first})"))
if len(turkish) > 10:
    notes.append(L(f"... ve Turkce karakterli {len(turkish) - 10} dosya daha", f"... and {len(turkish) - 10} more files with Turkish characters"))

# ---------- report ----------
print("=" * 62)
print(L(f"muto-atlas denetimi — v{pj['version']}", f"muto-atlas audit — v{pj['version']}"))
print(L(f"  komut: {len(cmds)} · referans: {len(refs_on_disk)} · agac: {len(tree_on_disk)} · betik: {len(scripts_on_disk)}",
        f"  commands: {len(cmds)} · references: {len(refs_on_disk)} · tree: {len(tree_on_disk)} · scripts: {len(scripts_on_disk)}"))
print("=" * 62)
if problems:
    print(L(f"\n!! {len(problems)} SORUN\n", f"\n!! {len(problems)} PROBLEMS\n"))
    for x in problems:
        print("  X " + x)
else:
    print(L("\nSORUN YOK\n", "\nNO PROBLEMS\n"))
print(L(f"\n-- {len(notes)} not --", f"\n-- {len(notes)} notes --"))
for x in notes:
    print("  . " + x)
sys.exit(1 if problems else 0)
