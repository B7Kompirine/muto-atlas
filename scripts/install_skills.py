#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""install_skills.py — installs the muto-atlas skills into tools OTHER than Claude Code.

WHY: the Agent Skills open standard (agentskills.io) makes Codex, the ChatGPT
desktop app, Gemini CLI, VS Code/Copilot, Cursor and others read a SKILL.md
folder the same way. But these skills run scripts from scripts/ at the
repository root and write that path with Claude Code's ${CLAUDE_PLUGIN_ROOT}
variable, which no other tool knows. The installer COPIES each skill folder to
the target and replaces the variable with the absolute path of this clone.
There is one source; the copies are never edited by hand, they are generated
again.

Usage:
  python scripts/install_skills.py                     # ~/.agents/skills
  python scripts/install_skills.py --tool cursor       # ~/.cursor/skills
  python scripts/install_skills.py --tool copilot --project <repo>   # <repo>/.github/skills
  python scripts/install_skills.py --dest <folder>     # any skills folder
  python scripts/install_skills.py --check             # only check against the standard, writes nothing
  python scripts/install_skills.py --uninstall [--tool/--project/--dest]

Exit: 0 done | 1 a SKILL.md does not meet the standard (nothing was written) |
      2 the target holds a folder this installer did not install, or the read-back did not match
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILLS = os.path.join(ROOT, "skills")
sys.path.insert(0, HERE)
from i18n import add_lang_arg, set_lang, t  # noqa: E402

VAR = "${CLAUDE_PLUGIN_ROOT}"
MARKER = ".muto-atlas-install.json"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Which tool reads which folder -- from the 2026-09 documentation:
#   ~/.agents/skills : Codex CLI/IDE, ChatGPT desktop, Gemini CLI (alias), VS Code/Copilot
#   ~/.gemini/skills : Gemini CLI      ~/.copilot/skills : Copilot
#   ~/.cursor/skills : Cursor           ~/.claude/skills  : Claude Code (without the plugin)
USER_DIRS = {
    "agents": "~/.agents/skills", "codex": "~/.agents/skills", "gemini": "~/.gemini/skills",
    "copilot": "~/.copilot/skills", "cursor": "~/.cursor/skills", "claude": "~/.claude/skills",
}
PROJECT_DIRS = {
    "agents": ".agents/skills", "codex": ".agents/skills", "gemini": ".gemini/skills",
    "copilot": ".github/skills", "cursor": ".cursor/skills", "claude": ".claude/skills",
}


def frontmatter(path):
    txt = io.open(path, encoding="utf-8").read()
    if not txt.startswith("---"):
        return None
    end = txt.find("\n---", 3)
    if end < 0:
        return None
    fm = {}
    for line in txt[3:end].splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def validate(skill_dir):
    """None if the SKILL.md meets the Agent Skills spec, else the reason."""
    folder = os.path.basename(os.path.normpath(skill_dir))
    fm = frontmatter(os.path.join(skill_dir, "SKILL.md"))
    if fm is None:
        return "frontmatter missing"
    name, desc = fm.get("name", ""), fm.get("description", "")
    if not (1 <= len(name) <= 64 and NAME_RE.match(name)):
        return f"name '{name}' breaks the naming rule (a-z, 0-9, single hyphens, max 64)"
    if name != folder:
        return f"name '{name}' does not match folder '{folder}'"
    if not (1 <= len(desc) <= 1024):
        return f"description is {len(desc)} characters (allowed 1-1024)"
    comp = fm.get("compatibility")
    if comp is not None and not (1 <= len(comp) <= 500):
        return f"compatibility is {len(comp)} characters (allowed 1-500)"
    return None


def skill_dirs():
    return sorted(os.path.join(SKILLS, d) for d in os.listdir(SKILLS)
                  if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))


def files_of(d):
    out = []
    for dp, dn, fn in os.walk(d):
        dn[:] = [x for x in dn if x != "__pycache__"]
        for f in fn:
            if f != MARKER:
                out.append(os.path.relpath(os.path.join(dp, f), d).replace(os.sep, "/"))
    return sorted(out)


def install_one(src, dest_root, root_posix):
    name = os.path.basename(src)
    dest = os.path.join(dest_root, name)
    if os.path.exists(dest):
        if not os.path.isfile(os.path.join(dest, MARKER)):
            print(t("sk_conflict", path=dest))
            return 2
        shutil.rmtree(dest)
    rels = files_of(src)
    for rel in rels:
        s, d = os.path.join(src, rel), os.path.join(dest, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if rel.endswith(".md"):
            with io.open(s, encoding="utf-8", newline="") as fh:
                text = fh.read()
            with io.open(d, "w", encoding="utf-8", newline="") as fh:
                fh.write(text.replace(VAR, root_posix))
        else:
            shutil.copy2(s, d)
    with io.open(os.path.join(dest, MARKER), "w", encoding="utf-8") as fh:
        json.dump({"source": root_posix, "skill": name, "installed": time.strftime("%Y-%m-%d %H:%M:%S")}, fh, indent=2)

    # read back: file set, leftover variable, frontmatter
    got = files_of(dest)
    if got != rels:
        print(t("sk_readback_fail", path=dest, why=f"{len(got)} files, expected {len(rels)}"))
        return 2
    left = [r for r in got if r.endswith(".md") and VAR in io.open(os.path.join(dest, r), encoding="utf-8").read()]
    if left:
        print(t("sk_readback_fail", path=dest, why=f"{VAR} still in {left[:3]}"))
        return 2
    why = validate(dest)
    if why:
        print(t("sk_readback_fail", path=dest, why=why))
        return 2
    print(t("sk_installed", skill=name, path=dest, n=len(got)))
    return 0


def main():
    p = argparse.ArgumentParser(description="Install the muto-atlas skills into another agent's skills folder.")
    p.add_argument("--tool", choices=sorted(USER_DIRS), default="agents",
                   help="target tool (default: agents = ~/.agents/skills)")
    p.add_argument("--project", metavar="DIR", help="install into this project instead of your home folder")
    p.add_argument("--dest", metavar="DIR", help="install into this exact skills folder")
    p.add_argument("--check", action="store_true", help="only validate SKILL.md files against the spec")
    p.add_argument("--uninstall", action="store_true", help="remove skills this tool installed")
    add_lang_arg(p)
    a = p.parse_args()
    if getattr(a, "lang", None):
        set_lang(a.lang)

    sources = skill_dirs()
    failed = False
    for s in sources:
        why = validate(s)
        if why:
            failed = True
            print(t("sk_invalid", skill=os.path.basename(s), why=why))
        else:
            fm = frontmatter(os.path.join(s, "SKILL.md"))
            print(t("sk_valid", skill=os.path.basename(s), name=len(fm["name"]), desc=len(fm["description"])))
    if failed:
        return 1
    if a.check:
        return 0

    if a.dest:
        dest_root = os.path.abspath(os.path.expanduser(a.dest))
    elif a.project:
        dest_root = os.path.abspath(os.path.join(os.path.expanduser(a.project), PROJECT_DIRS[a.tool]))
    else:
        dest_root = os.path.expanduser(USER_DIRS[a.tool])

    if a.uninstall:
        for s in sources:
            dest = os.path.join(dest_root, os.path.basename(s))
            if os.path.isfile(os.path.join(dest, MARKER)):
                shutil.rmtree(dest)
                print(t("sk_removed", path=dest))
            else:
                print(t("sk_nothing", path=dest))
        return 0

    os.makedirs(dest_root, exist_ok=True)
    root_posix = ROOT.replace(os.sep, "/")
    worst = max(install_one(s, dest_root, root_posix) for s in sources)
    print(t("sk_rerun"))
    return worst


if __name__ == "__main__":
    sys.exit(main())
