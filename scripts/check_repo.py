#!/usr/bin/env python3
"""check_repo.py — the checks every pull request must pass, runnable on your own machine.

WHY: audit_plugin.py checks the knowledge tree. This script checks what a contributor can break
without noticing anywhere else: a script that no longer compiles or crashes on --help, a PowerShell
script that no longer parses, a hand-written data table with a wrong column or value, a personal path
or a secret pasted into a file, a relative link that points nowhere. GitHub Actions runs the same
script on every pull request (.github/workflows/checks.yml).

Sections (all of them run by default):
  scripts   every scripts/*.py compiles; every script with a CLI answers --help without writing
            files; every scripts/*.ps1 parses
  data      every tracked data/*.tsv matches its schema: columns, types, ranges, unique keys
  public    no personal user folders, private e-mail addresses or secrets in tracked text files
  links     every relative Markdown link points at a file that exists

Usage:
  python scripts/check_repo.py
  python scripts/check_repo.py --only data public
  python scripts/check_repo.py --strict      # a missing Python package or PowerShell counts as a problem (CI)

A line that must show something the public check would flag can carry the marker
"check-repo: allow" to skip that one line.

Exit: 0 clean | 1 at least one problem
"""
import argparse
import ast
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from i18n import add_lang_arg, get_lang, set_lang  # noqa: E402

IN_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"
SECTIONS = ("scripts", "data", "public", "links")
TEXT_EXT = (".md", ".py", ".ps1", ".yml", ".yaml", ".json", ".txt", ".toml", ".cfg", ".lua", ".tsv", ".gitignore")
ALLOW_MARKER = "check-repo: allow"

problems, notes, summary = [], [], []


def L(tr, en):
    """One line in both languages; which one prints follows the i18n rule (--lang > env > config > en)."""
    return en if get_lang() == "en" else tr


def problem(section, message, path=None, line=None):
    problems.append((section, message, path, line))


def note(section, message):
    notes.append((section, message))


def tracked_files():
    """Tracked files from git; outside a git checkout, every file except .git, __pycache__ and data/."""
    try:
        r = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, timeout=60)
        if r.returncode == 0:
            return sorted(p for p in r.stdout.decode("utf-8").split("\0") if p)
    except (OSError, subprocess.TimeoutExpired):
        pass
    out = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__", "data")]
        out += [os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/") for f in fn]
    return sorted(out) + [f"data/{name}" for name in sorted(SCHEMAS_BY_NAME) if os.path.isfile(os.path.join(ROOT, "data", name))]


def read_text(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        raw = fh.read()
    if b"\0" in raw[:8000]:
        return None
    return raw.decode("utf-8", errors="replace").lstrip("﻿")


# ---------------------------------------------------------------- scripts
BLENDER_MODULES = {"bpy", "gpu", "gpu_extras", "mathutils"}
PS_PARSE = r"""
$bad = 0
foreach ($f in $args) {
    $tokens = $null; $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$tokens, [ref]$errors)
    foreach ($e in $errors) { "{0}`t{1}`t{2}" -f $f, $e.Extent.StartLineNumber, $e.Message; $bad++ }
}
exit $bad
"""


def top_level_imports(tree):
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return names


def check_scripts(files, strict):
    pys = [f for f in files if f.startswith("scripts/") and f.endswith(".py")]
    helped = 0
    # no PYTHONIOENCODING / PYTHONUTF8: on a Windows code page this catches help text the console cannot encode
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    for rel in pys:
        path = os.path.join(ROOT, rel)
        source = read_text(rel) or ""
        try:
            tree = ast.parse(source, filename=rel)
            compile(source, rel, "exec")
        except SyntaxError as e:
            problem("scripts", L(f"derlenmiyor: {e.msg}", f"does not compile: {e.msg}"), rel, e.lineno)
            continue
        has_cli = "__main__" in source and ("argparse" in source or '"--help"' in source)
        if not has_cli:
            continue
        if top_level_imports(tree) & BLENDER_MODULES:
            note("scripts", L(f"{rel}: yalniz Blender icinde calisir, --help atlandi",
                              f"{rel}: runs inside Blender only, --help skipped"))
            continue
        with tempfile.TemporaryDirectory() as tmp:
            try:
                r = subprocess.run([sys.executable, path, "--help"], cwd=tmp, env=env, stdin=subprocess.DEVNULL,
                                   capture_output=True, timeout=120)
            except subprocess.TimeoutExpired:
                problem("scripts", L("--help 120 sn icinde bitmedi", "--help did not finish in 120 s"), rel)
                continue
            left_behind = sorted(os.listdir(tmp))
        err = r.stderr.decode("utf-8", errors="replace")
        if r.returncode == 0:
            helped += 1
            if left_behind:
                problem("scripts", L(f"--help dosya yazdi: {left_behind[:3]}", f"--help wrote files: {left_behind[:3]}"), rel)
            continue
        missing = re.search(r"ModuleNotFoundError: No module named '([^']+)'", err)
        if missing and not strict:
            note("scripts", L(f"{rel}: --help atlandi, '{missing.group(1)}' paketi kurulu degil "
                              f"(python -m pip install -r requirements-dev.txt)",
                              f"{rel}: --help skipped, the Python package '{missing.group(1)}' is not installed "
                              f"(python -m pip install -r requirements-dev.txt)"))
            continue
        last = (err or r.stdout.decode("utf-8", errors="replace")).strip().splitlines()[-1:] or [""]
        problem("scripts", L(f"--help {r.returncode} ile cikti: {last[0][:160]}",
                             f"--help exited with {r.returncode}: {last[0][:160]}"), rel)

    ps1 = [f for f in files if f.startswith("scripts/") and f.endswith(".ps1")]
    parsed = 0
    exe = shutil.which("powershell") or shutil.which("pwsh")
    if ps1 and not exe:
        (problem if strict else note)("scripts", L("PowerShell bulunamadi: .ps1 dosyalari ayristirilmadi",
                                                   "PowerShell not found: the .ps1 files were not parsed"))
    elif ps1:
        with tempfile.TemporaryDirectory() as tmp:
            runner = os.path.join(tmp, "parse.ps1")
            with open(runner, "w", encoding="ascii") as fh:
                fh.write(PS_PARSE)
            r = subprocess.run([exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", runner]
                               + [os.path.join(ROOT, f) for f in ps1],
                               capture_output=True, stdin=subprocess.DEVNULL, timeout=300)
        out = r.stdout.decode("utf-8", errors="replace")
        for line in out.splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3:
                rel = os.path.relpath(parts[0], ROOT).replace(os.sep, "/")
                problem("scripts", L(f"PowerShell ayristiramiyor: {parts[2]}", f"PowerShell cannot parse it: {parts[2]}"),
                        rel, int(parts[1]) if parts[1].isdigit() else None)
        if r.returncode != 0 and not out.strip():
            problem("scripts", L(f"PowerShell ayristirma calismadi (cikis {r.returncode})",
                                 f"the PowerShell parse run failed (exit {r.returncode})"))
        parsed = len(ps1)
    summary.append(("scripts", L(f"{len(pys)} Python betigi derlendi · {helped} --help calisti · {parsed} PowerShell ayristirildi",
                                 f"{len(pys)} Python scripts compiled · {helped} answered --help · {parsed} PowerShell scripts parsed")))


# ---------------------------------------------------------------- data
# The 31 Sollumz BoundFlags (ybn/properties.py), written in trunk/flags.md §8.2.
BOUND_FLAGS = {
    "unknown", "map_weapon", "map_dynamic", "map_animal", "map_cover", "map_vehicle", "vehicle_not_bvh", "vehicle_bvh",
    "ped", "ragdoll", "animal", "animal_ragdoll", "object", "object_env_cloth", "plant", "projectile", "explosion",
    "pickup", "foliage", "forklift_forks", "test_weapon", "test_camera", "test_ai", "test_script",
    "test_vehicle_wheel", "glass", "map_river", "smoke", "unsmashed", "map_stairs", "map_deep_surface",
}


def integer(lo=None, hi=None):
    def check(value):
        if not re.fullmatch(r"-?\d+", value):
            return L("tam sayi olmali", "must be an integer")
        n = int(value)
        if (lo is not None and n < lo) or (hi is not None and n > hi):
            return L(f"{lo}..{hi} araliginda olmali", f"must be in {lo}..{hi}")
        return None
    return check


def number(lo=None, hi=None, above=None):
    def check(value):
        try:
            n = float(value)
        except ValueError:
            return L("sayi olmali", "must be a number")
        if not math.isfinite(n):
            return L("sonlu bir sayi olmali", "must be a finite number")
        if (lo is not None and n < lo) or (hi is not None and n > hi):
            return L(f"{lo}..{hi} araliginda olmali", f"must be in {lo}..{hi}")
        if above is not None and n <= above:
            return L(f"{above} degerinden buyuk olmali", f"must be greater than {above}")
        return None
    return check


def pattern(regex, text):
    compiled = re.compile(regex)

    def check(value):
        return None if compiled.fullmatch(value) else text
    return check


def rgb01(value):
    parts = value.split(",")
    if len(parts) != 3:
        return L("'r,g,b' biciminde uc sayi olmali", "must be three numbers as 'r,g,b'")
    for part in parts:
        if number(0, 1)(part):
            return L("her kanal 0..1 araliginda bir sayi olmali", "every channel must be a number in 0..1")
    return None


def flag_list(value):
    tokens = value.split(";") if value else []
    unknown = sorted(t for t in tokens if t not in BOUND_FLAGS)
    if unknown:
        return L(f"bilinmeyen bound flag: {', '.join(unknown)}", f"unknown bound flag: {', '.join(unknown)}")
    if len(set(tokens)) != len(tokens):
        return L("ayni flag iki kez yazilmis", "the same flag is listed twice")
    return None


NONEMPTY = pattern(r"\S(?:.*\S)?", L("bos olamaz, basinda ya da sonunda bosluk olamaz",
                                     "must not be empty or start or end with a space"))

SCHEMAS_BY_NAME = {
    "collision_materials.tsv": {
        "columns": ["index", "name", "ui_name", "r", "g", "b", "density"],
        "unique": ["index", "name", "ui_name"],
        "sequential": "index",
        "checks": {"index": integer(0), "name": pattern(r"[A-Z0-9_]+", L("BUYUK_HARF_ALT_CIZGI olmali", "must be UPPER_CASE_WITH_UNDERSCORES")),
                   "ui_name": NONEMPTY, "r": integer(0, 255), "g": integer(0, 255), "b": integer(0, 255),
                   "density": number(above=0)},
    },
    "collision_flag_presets.tsv": {
        "columns": ["name", "typeFlags", "includeFlags"],
        "unique": ["name"],
        "checks": {"name": NONEMPTY, "typeFlags": flag_list, "includeFlags": flag_list},
    },
    "light_presets.tsv": {
        "columns": ["name", "timeFlags", "lightFlags", "energy", "cutoff_distance", "color", "spot_size", "spot_blend",
                    "shadow_soft_size", "volume_factor", "flashiness", "corona_size", "corona_intensity",
                    "shadow_fade_distance", "specular_fade_distance", "volume_size_scale", "culling_plane_offset"],
        "unique": ["name"],
        "checks": {"name": NONEMPTY, "timeFlags": integer(0, 2 ** 32 - 1), "lightFlags": integer(0, 2 ** 32 - 1),
                   "energy": number(0), "cutoff_distance": number(0), "color": rgb01, "spot_size": number(0, math.pi),
                   "spot_blend": number(0, 1), "shadow_soft_size": number(0), "volume_factor": number(0),
                   "flashiness": pattern(r"[A-Z][A-Z0-9_]*", L("BUYUK_HARF bir ad olmali", "must be an UPPER_CASE name")),
                   "corona_size": number(0), "corona_intensity": number(0), "shadow_fade_distance": number(0),
                   "specular_fade_distance": number(0), "volume_size_scale": number(0), "culling_plane_offset": number()},
    },
}


def check_data(files):
    tables = [f for f in files if f.startswith("data/") and f.endswith(".tsv")]
    rows_total = 0
    for rel in tables:
        schema = SCHEMAS_BY_NAME.get(os.path.basename(rel))
        if schema is None:
            problem("data", L("bu tablonun semasi yok: scripts/check_repo.py icindeki SCHEMAS_BY_NAME'e ekle",
                              "this table has no schema: add one to SCHEMAS_BY_NAME in scripts/check_repo.py"), rel, 1)
            continue
        with open(os.path.join(ROOT, rel), "rb") as fh:
            raw = fh.read()
        if raw.startswith(b"\xef\xbb\xbf"):
            problem("data", L("UTF-8 BOM var: ilk sutun adini bozar", "has a UTF-8 BOM: it corrupts the first column name"), rel, 1)
        try:
            lines = raw.decode("utf-8").lstrip("﻿").splitlines()
        except UnicodeDecodeError as e:
            problem("data", L(f"UTF-8 degil: {e}", f"is not UTF-8: {e}"), rel)
            continue
        if not lines or lines[0].split("\t") != schema["columns"]:
            problem("data", L(f"sutunlar beklenen gibi degil: {schema['columns']}", f"columns are not as expected: {schema['columns']}"), rel, 1)
            continue
        seen = {key: {} for key in schema["unique"]}
        expected_index = 0
        for n, line in enumerate(lines[1:], start=2):
            if not line.strip():
                problem("data", L("bos satir", "empty line"), rel, n)
                continue
            cells = line.split("\t")
            if len(cells) != len(schema["columns"]):
                problem("data", L(f"{len(cells)} hucre var, {len(schema['columns'])} olmali",
                                  f"has {len(cells)} cells, expected {len(schema['columns'])}"), rel, n)
                continue
            rows_total += 1
            row = dict(zip(schema["columns"], cells))
            for column, check in schema["checks"].items():
                why = check(row[column])
                if why:
                    problem("data", f"{column} = {row[column]!r}: {why}", rel, n)
            for key in schema["unique"]:
                if row[key] in seen[key]:
                    problem("data", L(f"{key} tekrar ediyor: {row[key]!r} (ilk kez {seen[key][row[key]]}. satirda)",
                                      f"duplicate {key}: {row[key]!r} (first on line {seen[key][row[key]]})"), rel, n)
                else:
                    seen[key][row[key]] = n
            if schema.get("sequential") and re.fullmatch(r"\d+", row[schema["sequential"]]):
                if int(row[schema["sequential"]]) != expected_index:
                    problem("data", L(f"{schema['sequential']} {expected_index} olmali (sirali ve bosluksuz)",
                                      f"{schema['sequential']} should be {expected_index} (in order, no gaps)"), rel, n)
                expected_index = int(row[schema["sequential"]]) + 1
    summary.append(("data", L(f"{len(tables)} tablo · {rows_total} satir", f"{len(tables)} tables · {rows_total} rows")))


# ---------------------------------------------------------------- public
USER_FOLDER = re.compile(
    r"(?i)(?<![a-z])[a-z]:[\\/]+(?:users|documents and settings)[\\/]+"
    r"(?![<{%$*]|\.\.\.|public[\\/]|default[\\/]|all users[\\/]|you[\\/]|user[\\/]|username[\\/])[^\\/\s`'\"<>|]+")
HOME_FOLDER = re.compile(r"(?<![\w.~])/(?:home|Users)/(?![<{$*]|\.\.\.|user/|runner/|you/|username/)[A-Za-z0-9_.-]+/")
SHORT_NAME = re.compile(r"[\\/][A-Z0-9]{1,6}~[1-9][\\/]")
EMAIL = re.compile(r"(?<![\w.+-])[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:com|net|org|io|dev|me|co|app|ai|edu|gov|tr|de|uk|fr|ru)\b")
EMAIL_OK = re.compile(r"(?i)(@users\.noreply\.github\.com|@anthropic\.com|@example\.(?:com|org|net))$|^noreply@|^git@github\.com$")
SECRETS = [
    ("Anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
]


def check_public(files):
    scanned = 0
    for rel in files:
        if not rel.endswith(TEXT_EXT) and os.path.basename(rel) not in (".gitignore", ".gitattributes"):
            continue
        text = read_text(rel)
        if text is None:
            continue
        scanned += 1
        for n, line in enumerate(text.splitlines(), start=1):
            if ALLOW_MARKER in line:
                continue
            for regex, what in ((USER_FOLDER, L("kisisel kullanici klasoru", "personal user folder")),
                                (HOME_FOLDER, L("kisisel ev klasoru", "personal home folder")),
                                (SHORT_NAME, L("8.3 kisa ad iceren yol (kisisel klasor olabilir)", "path with an 8.3 short name (can be a personal folder)"))):
                m = regex.search(line)
                if m:
                    problem("public", L(f"{what}: {m.group(0)} — yerine <ad> gibi bir yer tutucu yaz",
                                        f"{what}: {m.group(0)} — write a placeholder such as <name> instead"), rel, n)
            for m in EMAIL.finditer(line):
                if not EMAIL_OK.search(m.group(0)):
                    problem("public", L(f"e-posta adresi: {m.group(0)}", f"e-mail address: {m.group(0)}"), rel, n)
            for name, regex in SECRETS:
                if regex.search(line):
                    problem("public", L(f"{name} gibi gorunuyor — anahtari iptal et ve dosyadan cikar",
                                        f"looks like a {name} — revoke the key and remove it from the file"), rel, n)
    summary.append(("public", L(f"{scanned} metin dosyasi tarandi", f"{scanned} text files scanned")))


# ---------------------------------------------------------------- links
LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")


def check_links(files):
    count = 0
    for rel in files:
        if not rel.endswith(".md"):
            continue
        text = read_text(rel)
        if text is None:
            continue
        in_fence = None
        for n, line in enumerate(text.splitlines(), start=1):
            fence = re.match(r"^\s*(`{3,}|~{3,})", line)
            if fence:
                if in_fence is None:
                    in_fence = fence.group(1)[0]
                elif fence.group(1)[0] == in_fence:
                    in_fence = None
                continue
            if in_fence:
                continue
            for m in LINK.finditer(re.sub(r"`[^`]*`", "", line)):
                target = m.group(1)
                if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                    continue
                path = target.split("#", 1)[0].split("?", 1)[0]
                if not path:
                    continue
                count += 1
                resolved = os.path.normpath(os.path.join(ROOT, os.path.dirname(rel), path.replace("%20", " ")))
                if not os.path.exists(resolved):
                    problem("links", L(f"baglanti bos bir yere gidiyor: {target}", f"link points nowhere: {target}"), rel, n)
    summary.append(("links", L(f"{count} goreli baglanti", f"{count} relative links")))


# ---------------------------------------------------------------- report
def main():
    ap = argparse.ArgumentParser(description="The checks every pull request must pass: scripts, data tables, "
                                             "public text, links (exit 1 on a problem).")
    ap.add_argument("--only", nargs="+", choices=SECTIONS, metavar="SECTION",
                    help="run only these sections: " + ", ".join(SECTIONS))
    ap.add_argument("--strict", action="store_true",
                    help="a missing Python package or PowerShell is a problem, not a note (used in CI)")
    add_lang_arg(ap)
    args = ap.parse_args()
    if args.lang:
        set_lang(args.lang)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass

    files = tracked_files()
    wanted = args.only or SECTIONS
    if "scripts" in wanted:
        check_scripts(files, args.strict)
    if "data" in wanted:
        check_data(files)
    if "public" in wanted:
        check_public(files)
    if "links" in wanted:
        check_links(files)

    print("=" * 62)
    print(L("muto-atlas depo kontrolleri", "muto-atlas repository checks"))
    for section, text in summary:
        print(f"  {section:8} {text}")
    print("=" * 62)
    if problems:
        print(L(f"\n!! {len(problems)} SORUN\n", f"\n!! {len(problems)} PROBLEMS\n"))
        for section, message, path, line in problems:
            where = f"{path}:{line}" if path and line else (path or "")
            print(f"  X [{section}] {where}  {message}".rstrip())
            if IN_ACTIONS and path:
                clean = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                print(f"::error file={path}{f',line={line}' if line else ''},title=check_repo {section}::{clean}")
    else:
        print(L("\nSORUN YOK\n", "\nNO PROBLEMS\n"))
    if notes:
        print(L(f"-- {len(notes)} not --", f"-- {len(notes)} notes --"))
        for section, message in notes:
            print(f"  . [{section}] {message}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
