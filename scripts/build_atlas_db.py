#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_atlas_db.py — dumps the knowledge tree into one SQLite file: project / file / snippet / tag.

WHY: the Markdown tree is good for reading, but "what do we know about light
hours" means walking 45 files. This script splits the tree into snippets,
links every snippet to a PROJECT named after its folder, tags it with Claude
and makes it searchable with FTS5. The generated file (data/atlas.db) is not
committed; everyone builds it from their own copy.

Project = folder name:
  skills/fivem-assets/branches/<branch>/ -> <branch>
  skills/fivem-assets/trunk/ + SKILL.md  -> trunk
  skills/fivem-assets/sources/           -> sources
  skills/<other-skill>/                  -> <other-skill>
  DIR/<folder>/ added with --source DIR  -> <folder>

Snippet = a section split at headings; code blocks are separate 'code' snippets.
Long sections are split into ~4000-character pieces (split, never cut off).

Tags:
  --tagger claude  Claude chooses (default claude-opus-5). The result is stored
                   in tag_cache under the content hash (sha256); a rebuild sends
                   only changed snippets to the API. An interrupted build
                   (Ctrl+C, crash) stays in .tmp and the next build carries it over.
  --tagger rules   keyword rules: offline, free.
  --tagger auto    (default) claude when the anthropic package and credentials
                   exist, otherwise rules. Which one ran is ALWAYS printed.

Usage:
  python scripts/build_atlas_db.py
  python scripts/build_atlas_db.py --tagger claude [--model claude-opus-5] [--effort low]
  python scripts/build_atlas_db.py --source ../my-notes
  python scripts/build_atlas_db.py --search "TimeFlags" [--project look] [--tag light]
  python scripts/build_atlas_db.py --stats

Exit: 0 done | 1 no search results | 2 no database / Claude requested but
      unavailable | 3 database unreadable / verification failed (the previous database is kept)
"""
import argparse
import functools
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
import time
from contextlib import closing
from urllib.request import pathname2url

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILLS = os.path.join(ROOT, "skills")
DATA = os.path.join(ROOT, "data")
DEFAULT_DB = os.path.join(DATA, "atlas.db")
sys.path.insert(0, HERE)
from i18n import add_lang_arg, set_lang, t  # noqa: E402

EXIT_OK, EXIT_EMPTY, EXIT_UNAVAILABLE, EXIT_INTERNAL = 0, 1, 2, 3
SCHEMA_VERSION = "2"
PROMPT_VERSION = "tags-v2"
MAX_CHARS = 4000
DEFAULT_MODEL = "claude-opus-5"
FALLBACK_MODELS = {"claude-opus-5", "claude-fable-5-1"}   # server-side refusal fallbacks
NO_EFFORT_PREFIXES = ("claude-haiku-",)                   # these models reject the effort parameter
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Tag vocabulary: tag -> patterns the rule tagger looks for (case-insensitive).
# Claude gets the same list and picks its tags from it. The Turkish patterns stay on purpose:
# Turkish notes added with --source are tagged as well.
VOCAB = {
    "ydr": [r"\.ydr\b", r"\bdrawable\b"],
    "yft": [r"\.yft\b"],
    "ydd": [r"\.ydd\b"],
    "ybn": [r"\.ybn\b"],
    "ycd": [r"\.ycd\b", r"\bclip dictionary\b"],
    "yed": [r"\.yed\b", r"\bexpression\b"],
    "ytd": [r"\.ytd\b", r"\btexture dictionary\b"],
    "ypt": [r"\.ypt\b"],
    "ytyp": [r"\.?ytyp\b", r"\barchetype", r"\barketip"],
    "ymap": [r"\.?ymap\b"],
    "mlo": [r"\bmlo\b", r"\binterior\b", r"iç mekân", r"\bportal"],
    "dds": [r"\bdds\b", r"\bdxt[15]\b", r"\bmipmap", r"\bmip\b"],
    "xml": [r"\bxml\b", r"\bcwxml\b"],
    "sollumz": [r"sollumz"],
    "codewalker": [r"codewalker"],
    "blender": [r"\bblender\b", r"\bbpy\b"],
    "powershell": [r"powershell", r"\.ps1\b"],
    "python": [r"\bpython\b", r"\.py\b"],
    "lua": [r"\blua\b", r"fxmanifest"],
    "fivem": [r"\bfivem\b", r"\bcfx\b", r"txadmin"],
    "framework": [r"qbcore", r"\bqbox\b", r"\besx\b", r"ox_lib", r"ox_target"],
    "door": [r"adddoortosystem", r"door ?system", r"kapı sistemi", r"\bdoors?\b"],
    "special-attribute": [r"specialattribute"],
    "pivot-bbox": [r"\bpivot\b", r"\bbbox\b", r"bounding ?box", r"\bbb(?:min|max)\b"],
    "flags": [r"\bflags?\b", r"bayra[kğ]"],
    "extension": [r"\bextensions?\b"],
    "lod": [r"\blod\w*", r"\bslod\b"],
    "collision": [r"collision", r"çarpışma", r"\bbounds?\b"],
    "fragment": [r"\bfragment", r"kırılabilir"],
    "physics": [r"\bphysics\b", r"\bfizi[kğ]"],
    "bones": [r"\bbones?\b", r"\bkemi[kğ]", r"\bskeleton\b", r"\biskelet"],
    "animation": [r"\banimation", r"animasyon", r"taskplayanim", r"playentityanim"],
    "particle": [r"\bparticle", r"partikül", r"\bptfx", r"\bfxname\b"],
    "flipbook": [r"flipbook", r"sprite ?sheet"],
    "shader": [r"\bshaders?\b", r"\.sps\b"],
    "render-bucket": [r"render ?bucket", r"\bkova\b"],
    "texture": [r"\btextures?\b", r"\bdoku\b"],
    "light": [r"\blights?\b", r"ışık", r"\blamba"],
    "time-flags": [r"timeflags", r"flashiness"],
    "gobo": [r"\bgobo", r"projected texture"],
    "timecycle": [r"timecycle", r"\bweather\b"],
    "decal": [r"\bdecal", r"graffiti"],
    "parallax": [r"parallax", r"\bpxm\b"],
    "vertex-color": [r"vertex colou?r", r"vertex paint"],
    "emissive": [r"emissive"],
    "destruction": [r"rayfire", r"\bdestruction\b", r"yıkım", r"\bdes_\w+"],
    "grass-procedural": [r"\bgrass\b", r"\bçim\b", r"procedural"],
    "clothing": [r"clothing", r"kıyafet", r"giysi", r"freemode", r"skintone"],
    "cloth-sim": [r"\bcloth\b", r"\.yld\b"],
    "vehicle": [r"\bvehicles?\b", r"\baraç\b", r"\bhandling", r"\bmodkit"],
    "weapon-data": [r"\bweapon_\w+", r"\bcomponent_\w+", r"\blivery"],
    "dui-nui": [r"\bdui\b", r"\bnui\b", r"createdui", r"addreplacetexture", r"render ?target"],
    "attach": [r"attachentitytoentity", r"\bph_[lr]_hand\b", r"ele tuttur"],
    "native": [r"\bnatives?\b", r"\bapiset\b"],
    "performance": [r"performan", r"\bresmon\b", r"wait\(0\)"],
    "streaming": [r"\bstream\w*", r"yeniden bağlan", r"reconnect"],
    "world-placement": [r"world placement", r"dünya yerleşim", r"\bkoordinat", r"\bcoordinates?\b"],
    "verification": [r"doğrula", r"\bverif", r"geri oku", r"read back", r"\bdoctor\b"],
    "silent-failure": [r"sessiz", r"\bsilent", r"hata vermez", r"no error"],
    "export-import": [r"\bexport\w*", r"içe al"],
    "bake": [r"\bbak(?:e|ing)\b", r"pişir"],
    "measurement": [r"ölçüm", r"ölçüldü", r"\bmeasured\b"],
    "pitfall": [r"tuzak", r"⛔", r"\bpitfall"],
    "vanilla-reference": [r"\bvanilla\b"],
    "prop-swap": [r"prop swap", r"swapentity", r"patch_vanilla_ytyp"],
    "data-layer": [r"assetdb\.py", r"\bkatman", r"\blayers?\b"],
}

SCHEMA_SQL = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, source TEXT NOT NULL);
CREATE TABLE files (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
                    path TEXT NOT NULL UNIQUE, title TEXT NOT NULL, sha256 TEXT NOT NULL, lines INTEGER NOT NULL);
CREATE TABLE snippets (id INTEGER PRIMARY KEY, file_id INTEGER NOT NULL REFERENCES files(id),
                       project_id INTEGER NOT NULL REFERENCES projects(id), ord INTEGER NOT NULL,
                       kind TEXT NOT NULL CHECK (kind IN ('section', 'code')), lang TEXT,
                       heading TEXT NOT NULL, heading_path TEXT NOT NULL,
                       start_line INTEGER NOT NULL, end_line INTEGER NOT NULL,
                       content TEXT NOT NULL, sha256 TEXT NOT NULL);
CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE snippet_tags (snippet_id INTEGER NOT NULL REFERENCES snippets(id),
                           tag_id INTEGER NOT NULL REFERENCES tags(id),
                           source TEXT NOT NULL CHECK (source IN ('claude', 'rule')),
                           PRIMARY KEY (snippet_id, tag_id));
CREATE TABLE tag_cache (sha256 TEXT NOT NULL, tagger TEXT NOT NULL, tags TEXT NOT NULL, created TEXT NOT NULL,
                        PRIMARY KEY (sha256, tagger));
CREATE INDEX idx_snippets_project ON snippets(project_id);
CREATE INDEX idx_snippets_file ON snippets(file_id);
CREATE INDEX idx_snippet_tags_tag ON snippet_tags(tag_id);
CREATE VIRTUAL TABLE snippets_fts USING fts5(heading_path, content, tags, folded, project UNINDEXED,
                                             tokenize = 'unicode61 remove_diacritics 2');
"""


# ---------------------------------------------------------------- splitting
HEADING = re.compile(r"^(#{1,4})\s+(.*\S)\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})\s*([\w+#.-]*)")


# unicode61 does not fold the dotless i (U+0131) to 'i': a search for "carpisma" did not find the word
# written with Turkish letters (946 snippets, 0 hits).
# The query and the 'folded' column go through the same folding; the original text is searched and shown in its own column.
_FOLD = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def fold(text):
    return text.translate(_FOLD)


def _sha(*parts):
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()


def _chunks(entries, limit=MAX_CHARS):
    """[(first_line, last_line, text)] -> [(text, first_line, last_line)].
    Prefers to split at a blank line; blank lines at the start or end of a piece are not part of its line range."""
    out, buf, size = [], [], 0

    def emit():
        while buf and not buf[-1][2].strip():
            buf.pop()
        if buf:
            out.append(("\n".join(x for _, _, x in buf), buf[0][0], buf[-1][1]))

    for a, b, text in entries:
        blank = not text.strip()
        if buf and (size + len(text) + 1 > limit or (blank and size > limit * 0.7)):
            emit()
            buf, size = [], 0
        if blank and not buf:
            continue
        buf.append((a, b, text))
        size += len(text) + 1
    emit()
    return out


def split_markdown(text):
    """Markdown -> snippet dicts (kind, lang, heading, heading_path, start_line, end_line, content, sha256).
    A code block becomes its own 'code' snippet; the section keeps a [lang: N lines] placeholder in its
    place and the section's line range covers the block."""
    lines = text.splitlines()
    first = 0
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                first = j + 1
                break
    out, stack, prose, code = [], [], [], None

    def where():
        return (stack[-1][1] if stack else ""), " > ".join(h for _, h in stack)

    def flush_prose():
        nonlocal prose
        if any(real and x.strip() for _, _, x, real in prose):
            heading, path = where()
            for chunk, a, b in _chunks([(a, b, x) for a, b, x, _ in prose]):
                out.append({"kind": "section", "lang": "", "heading": heading, "heading_path": path,
                            "start_line": a, "end_line": b, "content": chunk.strip()})
        prose = []

    def flush_code(block):
        heading, path = where()
        for chunk, a, b in _chunks(block["lines"]):
            out.append({"kind": "code", "lang": block["lang"], "heading": heading, "heading_path": path,
                        "start_line": a, "end_line": b, "content": chunk})

    for idx in range(first, len(lines)):
        n, line = idx + 1, lines[idx]
        if code is not None:
            if code["close"].match(line):
                flush_code(code)
                prose.append((code["start"], n, f"[{code['lang'] or 'code'}: {len(code['lines'])} line{'s' if len(code['lines']) != 1 else ''}]", False))
                code = None
            else:
                code["lines"].append((n, n, line))
            continue
        m = FENCE.match(line)
        if m:
            fence = m.group(1)
            code = {"lang": m.group(2).lower(), "lines": [], "start": n,
                    "close": re.compile(r"^\s*" + re.escape(fence[0]) + "{%d,}\\s*$" % len(fence))}
            continue
        h = HEADING.match(line)
        if h:
            flush_prose()
            level = len(h.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, h.group(2).strip()))
            continue
        prose.append((n, n, line, True))
    if code is not None:
        flush_code(code)
    flush_prose()
    out.sort(key=lambda s: (s["start_line"], s["kind"] != "section"))
    for s in out:
        s["sha256"] = _sha(s["kind"], s["lang"], s["heading_path"], s["content"])
    return out


def project_of(rel, label):
    parts = rel.split("/")
    if label == "skills":
        if parts[0] == "fivem-assets":
            if len(parts) >= 4 and parts[1] == "branches":
                return parts[2]
            if len(parts) >= 3 and parts[1] in ("trunk", "sources"):
                return parts[1]
            return "trunk"
        return parts[0]
    return parts[0].lower() if len(parts) > 1 else label.lower()


def collect(sources):
    files = []
    for label, base in sources:
        for dp, dn, fn in os.walk(base):
            dn[:] = sorted(d for d in dn if not d.startswith((".", "_")))
            for f in sorted(fn):
                if not f.lower().endswith(".md"):
                    continue
                full = os.path.join(dp, f)
                rel = os.path.relpath(full, base).replace(os.sep, "/")
                with io.open(full, encoding="utf-8-sig", errors="replace") as fh:
                    text = fh.read()
                project = project_of(rel, label)
                snippets = split_markdown(text)
                # the title is the first heading outside a code block (a "# comment" line is not a heading)
                title = next((s["heading_path"].split(" > ")[0] for s in snippets if s["heading_path"]), rel)
                for s in snippets:
                    s["project"] = project
                files.append({"project": project, "source": label, "path": f"{label}/{rel}", "title": title,
                              "sha256": _sha(text), "lines": len(text.splitlines()), "snippets": snippets})
    return files


# ---------------------------------------------------------------- taggers
class RuleTagger:
    key = "rules:v1"

    def __init__(self):
        self.patterns = {tag: [re.compile(p, re.I) for p in pats] for tag, pats in VOCAB.items()}

    def tag(self, snippets):
        out = {}
        for s in snippets:
            text = s["heading_path"] + "\n" + s["content"]
            scored = sorted((-sum(len(p.findall(text)) for p in pats), tag) for tag, pats in self.patterns.items())
            out[s["sha256"]] = [tag for score, tag in scored if score < 0][:6]
        return out


class ClaudeUnavailable(Exception):
    pass


def _hint(pattern):
    s = pattern.replace("(?:", "(")
    s = re.sub(r"\\[bBdsw][*+]?", "", s)
    s = re.sub(r"\[(.)[^\]]*\]", r"\1", s)
    s = re.sub(r"\\(.)", r"\1", s)
    return re.sub(r"[?*+]", "", s).replace("|", "/").strip()


def _schema():
    return {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {
            "type": "object",
            "properties": {"id": {"type": "integer"},
                           "tags": {"type": "array", "items": {"type": "string", "enum": sorted(VOCAB)}},
                           "extra": {"type": "array", "items": {"type": "string"}}},
            "required": ["id", "tags", "extra"], "additionalProperties": False}}},
        "required": ["items"], "additionalProperties": False,
    }


class ClaudeTagger:
    """Tags snippets in batches. One request per batch; the system prompt is static so it caches."""

    def __init__(self, model=DEFAULT_MODEL, effort="low", client=None, batch_chars=24000, batch_max=25):
        self.model, self.effort = model, effort
        self.key = f"claude:{model}:{PROMPT_VERSION}"
        self.batch_chars, self.batch_max = batch_chars, batch_max
        self.usage = {"requests": 0, "input_tokens": 0, "output_tokens": 0,
                      "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
        self.refused = 0
        self.unparsed = 0
        if client is None:
            try:
                import anthropic
            except ImportError as e:
                raise ClaudeUnavailable("anthropic package not installed (python -m pip install anthropic)") from e
            try:
                client = anthropic.Anthropic(max_retries=5)
            except Exception as e:  # credentials are resolved here or on the first request
                raise ClaudeUnavailable(f"{type(e).__name__}: {e}") from e
        self.client = client
        vocab_lines = "\n".join(f"- {tag}: {', '.join(dict.fromkeys(_hint(p) for p in pats))}" for tag, pats in VOCAB.items())
        self.system = (
            "You tag snippets from a GTA V / FiveM modding knowledge base. The prose is English, though notes added "
            "from other folders may be Turkish; file formats, tool names and code are English.\n\n"
            "For every snippet you receive, choose 1 to 6 tags from the vocabulary below that describe what the "
            "snippet is about - its subject, not every word it happens to mention. If no vocabulary tag covers a "
            "central topic, you may add up to 2 extra tags: lowercase ASCII words joined by hyphens, at most 32 "
            "characters.\n"
            "Return exactly one item per snippet id you were given, and no other ids.\n\n"
            "Vocabulary (tag: example terms):\n" + vocab_lines
        )

    def batches(self, snippets):
        batch, size = [], 0
        for s in snippets:
            n = len(s["content"]) + len(s["heading_path"]) + 80
            if batch and (len(batch) >= self.batch_max or size + n > self.batch_chars):
                yield batch
                batch, size = [], 0
            batch.append(s)
            size += n
        if batch:
            yield batch

    def _request(self, batch):
        body = "\n\n".join(
            f'<snippet id="{i}" project="{s["project"]}" kind="{s["kind"]}" heading="{s["heading_path"].replace(chr(34), chr(39))}">\n'
            f'{s["content"].replace("</snippet>", "</ snippet>")}\n</snippet>'
            for i, s in enumerate(batch))
        output_config = {"format": {"type": "json_schema", "schema": _schema()}}
        if not self.model.startswith(NO_EFFORT_PREFIXES):
            output_config["effort"] = self.effort
        kwargs = {
            "model": self.model,
            "max_tokens": 16000,
            "system": [{"type": "text", "text": self.system, "cache_control": {"type": "ephemeral"}}],
            "output_config": output_config,
            "messages": [{"role": "user", "content": "Tag these snippets.\n\n" + body}],
        }
        if self.model in FALLBACK_MODELS:
            return self.client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
        return self.client.messages.create(**kwargs)

    def _add_usage(self, resp):
        self.usage["requests"] += 1
        u = getattr(resp, "usage", None)
        for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            self.usage[k] += int(getattr(u, k, 0) or 0)

    def _tag_batch(self, batch):
        resp = self._request(batch)
        self._add_usage(resp)
        if resp.stop_reason == "refusal":
            self.refused += len(batch)
            return {}
        text = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        if data is None or (resp.stop_reason == "max_tokens" and len(batch) > 1):
            if len(batch) == 1:
                self.unparsed += 1
                return {}
            mid = len(batch) // 2
            result = self._tag_batch(batch[:mid])
            result.update(self._tag_batch(batch[mid:]))
            return result
        result = {}
        for item in data.get("items", []):
            i = item.get("id")
            if not isinstance(i, int) or not 0 <= i < len(batch):
                continue
            tags = [x for x in item.get("tags", []) if x in VOCAB]
            extra = [x for x in item.get("extra", []) if isinstance(x, str) and len(x) <= 32 and SLUG.match(x) and x not in VOCAB][:2]
            chosen = list(dict.fromkeys(tags + extra))[:8]
            if chosen:
                result[batch[i]["sha256"]] = chosen
        return result

    def tag(self, snippets, on_batch):
        for batch in self.batches(snippets):
            on_batch(self._tag_batch(batch))


def _classify(e):
    name = type(e).__name__
    if name in ("AuthenticationError", "PermissionDeniedError") or re.search(r"api[_ ]?key|authenticat|credential", str(e), re.I):
        return "auth"
    if name == "NotFoundError":
        return "model"
    if name in ("RateLimitError", "InternalServerError", "APIConnectionError", "APITimeoutError"):
        return "transient"
    if name in ("BadRequestError", "UnprocessableEntityError"):
        return "request"
    return "other"


# ---------------------------------------------------------------- build
def _ro(path):
    return sqlite3.connect(f"file:{pathname2url(os.path.abspath(path))}?mode=ro", uri=True)


def build(out_path, sources, tagger_choice="auto", model=DEFAULT_MODEL, effort="low", client=None, log=print):
    files = collect(sources)
    unique = {}
    for f in files:
        for s in f["snippets"]:
            unique.setdefault(s["sha256"], s)
    total = sum(len(f["snippets"]) for f in files)
    projects = sorted({f["project"] for f in files})
    log(t("adb_collected", files=len(files), snippets=total, projects=len(projects), names=", ".join(projects)))

    # The tag cache is carried over from the previous database AND from the .tmp of an interrupted
    # build: Ctrl+C or a crash does not lose tags already paid for.
    tmp = out_path + ".tmp"
    carried, unsaved = [], 0          # unsaved: paid tags that exist only in .tmp
    for prev in (out_path, tmp):
        if not os.path.isfile(prev):
            continue
        try:
            with closing(_ro(prev)) as old:   # Windows: a connection left open blocks os.replace
                if old.execute("select 1 from sqlite_master where type='table' and name='tag_cache'").fetchone():
                    rows = old.execute("select sha256, tagger, tags, created from tag_cache").fetchall()
                    carried += rows
                    if prev == tmp:
                        unsaved += sum(1 for r in rows if r[1].startswith("claude:"))
        except sqlite3.DatabaseError as e:
            log(t("adb_cache_unreadable", why=f"{os.path.basename(prev)}: {e}"))
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.executescript(SCHEMA_SQL)
    con.executemany("insert or ignore into tag_cache values (?,?,?,?)", carried)
    con.commit()

    def abort(code):
        con.close()
        if not unsaved:          # a .tmp holding paid tags is left for the next build
            os.remove(tmp)
        return code

    rule_tags = RuleTagger().tag(unique.values())
    claude_tags, used = {}, "rules"
    if tagger_choice in ("auto", "claude"):
        try:
            tagger = ClaudeTagger(model, effort, client=client)
        except ClaudeUnavailable as e:
            if tagger_choice == "claude":
                log(t("adb_claude_required", why=str(e)))
                return abort(EXIT_UNAVAILABLE)
            log(t("adb_auto_rules", why=str(e)))
        else:
            cached = {sha: json.loads(tags) for sha, tags in
                      con.execute("select sha256, tags from tag_cache where tagger = ?", (tagger.key,)) if sha in unique}
            pending = [s for sha, s in unique.items() if sha not in cached]
            log(t("adb_plan", cached=len(cached), pending=len(pending), model=model,
                  requests=sum(1 for _ in tagger.batches(pending))))

            def on_batch(result):
                nonlocal unsaved
                now = time.strftime("%Y-%m-%d %H:%M:%S")
                con.executemany("insert or replace into tag_cache values (?,?,?,?)",
                                [(sha, tagger.key, json.dumps(tags), now) for sha, tags in result.items()])
                con.commit()
                cached.update(result)
                unsaved += len(result)

            try:
                tagger.tag(pending, on_batch)
            except Exception as e:  # classified and reported, never swallowed
                kind, why = _classify(e), f"{type(e).__name__}: {e}"
                if tagger_choice == "claude" and kind in ("auth", "model", "request") and not cached:
                    log(t("adb_claude_required", why=why))
                    return abort(EXIT_UNAVAILABLE)
                log(t("adb_claude_error", kind=kind, why=why, left=sum(1 for sha in unique if sha not in cached)))
            except BaseException:   # Ctrl+C: committed tags stay in .tmp, the next build carries them over
                con.close()
                raise
            if tagger.refused:
                log(t("adb_refused", n=tagger.refused))
            if tagger.unparsed:
                log(t("adb_unparsed", n=tagger.unparsed))
            if tagger.usage["requests"]:
                log(t("adb_usage", **tagger.usage))
            claude_tags = cached
            if claude_tags:
                used = f"claude ({model})"
    if unique:
        con.execute("delete from tag_cache where sha256 not in (%s)" % ",".join("?" * len(unique)), list(unique))
    log(t("adb_tagger", name=used))

    project_ids, tag_ids = {}, {}
    for f in files:
        if f["project"] not in project_ids:
            project_ids[f["project"]] = con.execute("insert into projects(name, source) values (?, ?)",
                                                    (f["project"], f["source"])).lastrowid

    def tag_id(name):
        if name not in tag_ids:
            tag_ids[name] = con.execute("insert into tags(name) values (?)", (name,)).lastrowid
        return tag_ids[name]

    by_source = {"claude": 0, "rule": 0, "none": 0}
    for f in files:
        pid = project_ids[f["project"]]
        fid = con.execute("insert into files(project_id, path, title, sha256, lines) values (?,?,?,?,?)",
                          (pid, f["path"], f["title"], f["sha256"], f["lines"])).lastrowid
        for order, s in enumerate(f["snippets"]):
            sid = con.execute(
                "insert into snippets(file_id, project_id, ord, kind, lang, heading, heading_path, start_line, end_line, content, sha256)"
                " values (?,?,?,?,?,?,?,?,?,?,?)",
                (fid, pid, order, s["kind"], s["lang"] or None, s["heading"], s["heading_path"], s["start_line"],
                 s["end_line"], s["content"], s["sha256"])).lastrowid
            tags, source = claude_tags.get(s["sha256"]), "claude"
            if not tags:
                tags, source = rule_tags.get(s["sha256"], []), "rule"
            by_source[source if tags else "none"] += 1
            con.executemany("insert or ignore into snippet_tags(snippet_id, tag_id, source) values (?,?,?)",
                            [(sid, tag_id(x), source) for x in tags])
            plain = s["heading_path"] + "\n" + s["content"]
            folded = fold(plain)
            con.execute("insert into snippets_fts(rowid, heading_path, content, tags, folded, project) values (?,?,?,?,?,?)",
                        (sid, s["heading_path"], s["content"], " ".join(tags), folded if folded != plain else "", f["project"]))
    meta = {"schema_version": SCHEMA_VERSION, "built_at": time.strftime("%Y-%m-%d %H:%M:%S"), "tagger": used,
            "model": model if used.startswith("claude") else "", "prompt_version": PROMPT_VERSION,
            "sources": json.dumps([label for label, _ in sources]), "files": str(len(files)), "snippets": str(total),
            "tagged_claude": str(by_source["claude"]), "tagged_rule": str(by_source["rule"]),
            "untagged": str(by_source["none"])}
    con.executemany("insert into meta(key, value) values (?, ?)", sorted(meta.items()))
    con.commit()

    # read back: counts, FTS, integrity -- on a mismatch the previous database stays in place
    problems = []
    got = {k: con.execute(f"select count(*) from {k}").fetchone()[0] for k in ("files", "snippets", "projects", "snippets_fts")}
    if got["files"] != len(files):
        problems.append(f"files {got['files']} != {len(files)}")
    if got["snippets"] != total or got["snippets_fts"] != total:
        problems.append(f"snippets {got['snippets']} / fts {got['snippets_fts']} != {total}")
    if got["projects"] != len(projects):
        problems.append(f"projects {got['projects']} != {len(projects)}")
    integrity = con.execute("pragma integrity_check").fetchone()[0]
    if integrity != "ok":
        problems.append(f"integrity_check: {integrity}")
    if problems:
        log(t("adb_verify_fail", why="; ".join(problems)))
        return abort(EXIT_INTERNAL)
    con.close()
    try:
        os.replace(tmp, out_path)
    except OSError as e:
        if not unsaved:
            os.remove(tmp)
        log(t("adb_verify_fail", why=f"could not replace {out_path}: {e}"))
        return EXIT_INTERNAL
    with closing(_ro(out_path)) as ro:
        final = ro.execute("select count(*) from snippets").fetchone()[0]
    if final != total:
        log(t("adb_verify_fail", why=f"read back {final} snippets, expected {total}"))
        return EXIT_INTERNAL
    log(t("adb_written", path=out_path, size=os.path.getsize(out_path) // 1024, claude=by_source["claude"],
          rule=by_source["rule"], none=by_source["none"]))
    return EXIT_OK


# ---------------------------------------------------------------- queries (also used by mcp_server.py)
def _fts_query(text):
    terms = [w for w in fold(text).split() if w.strip()]
    return " ".join('"' + w.replace('"', '""') + '"' for w in terms)


def _guard(fn):
    """No database -> (2, None); sqlite error -> (3, 'Type: message'). The CLI and MCP give the same answer."""
    @functools.wraps(fn)
    def wrapped(db, *args, **kwargs):
        if not os.path.isfile(db):
            return EXIT_UNAVAILABLE, None
        try:
            return fn(db, *args, **kwargs)
        except sqlite3.DatabaseError as e:
            return EXIT_INTERNAL, f"{type(e).__name__}: {e}"
    return wrapped


_TAGS_SQL = ("(select group_concat(t.name, ',') from snippet_tags st join tags t on t.id = st.tag_id where st.snippet_id = s.id)",
             "(select group_concat(distinct st.source) from snippet_tags st where st.snippet_id = s.id)")


@_guard
def search_rows(db, query, project=None, tag=None, limit=20):
    q = _fts_query(query or "")
    if not q:
        return EXIT_EMPTY, []
    sql = ("select s.id, p.name as project, f.path, s.start_line, s.end_line, s.heading_path, s.kind, s.lang, "
           "snippet(snippets_fts, 1, '[', ']', ' ... ', 14) as snip, "
           f"{_TAGS_SQL[0]} as tags, {_TAGS_SQL[1]} as tag_source "
           "from snippets_fts join snippets s on s.id = snippets_fts.rowid "
           "join files f on f.id = s.file_id join projects p on p.id = s.project_id "
           "where snippets_fts match ?")
    params = [q]
    if project:
        sql += " and p.name = ?"
        params.append(project)
    if tag:
        sql += " and exists (select 1 from snippet_tags st join tags tg on tg.id = st.tag_id where st.snippet_id = s.id and tg.name = ?)"
        params.append(tag)
    sql += " order by bm25(snippets_fts) limit ?"
    params.append(int(limit))
    with closing(_ro(db)) as con:
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute(sql, params)]
    return (EXIT_OK if rows else EXIT_EMPTY), rows


@_guard
def read_snippet(db, snippet_id):
    with closing(_ro(db)) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("select s.*, p.name as project, f.path, "
                          f"{_TAGS_SQL[0]} as tags, {_TAGS_SQL[1]} as tag_source "
                          "from snippets s join files f on f.id = s.file_id join projects p on p.id = s.project_id "
                          "where s.id = ?", (snippet_id,)).fetchone()
    return (EXIT_OK, dict(row)) if row else (EXIT_EMPTY, None)


@_guard
def tag_counts(db, project=None, limit=60):
    sql = ("select t.name, count(*), sum(st.source = 'claude') from snippet_tags st join tags t on t.id = st.tag_id "
           "join snippets s on s.id = st.snippet_id join projects p on p.id = s.project_id")
    params = []
    if project:
        sql += " where p.name = ?"
        params.append(project)
    sql += " group by t.id order by count(*) desc, t.name limit ?"
    params.append(int(limit))
    with closing(_ro(db)) as con:
        projects = con.execute("select p.name, count(distinct f.id), count(s.id) from projects p "
                               "left join files f on f.project_id = p.id left join snippets s on s.file_id = f.id "
                               "group by p.id order by p.name").fetchall()
        tags = con.execute(sql, params).fetchall()
        meta = dict(con.execute("select key, value from meta").fetchall())
    return EXIT_OK, {"projects": projects, "tags": tags, "meta": meta}


def _db_problem(code, path, detail):
    print(t("adb_missing", path=path) if code == EXIT_UNAVAILABLE else t("adb_db_error", path=path, why=detail))
    return code


def main():
    p = argparse.ArgumentParser(description="Build data/atlas.db from the knowledge tree: projects, snippets, tags, FTS5.")
    p.add_argument("--out", default=DEFAULT_DB, help="database path (default: data/atlas.db)")
    p.add_argument("--source", action="append", default=[], metavar="DIR",
                   help="extra knowledge folder; each of its subfolders becomes a project (repeatable)")
    p.add_argument("--tagger", choices=("auto", "claude", "rules"), default="auto")
    p.add_argument("--model", default=DEFAULT_MODEL, help="Claude model for tagging (default: claude-opus-5)")
    p.add_argument("--effort", choices=("low", "medium", "high", "xhigh", "max"), default="low")
    p.add_argument("--search", metavar="QUERY", help="full-text search instead of building")
    p.add_argument("--project", help="with --search / --stats: only this project")
    p.add_argument("--tag", help="with --search: only snippets carrying this tag")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--stats", action="store_true", help="projects, tag counts and build metadata")
    add_lang_arg(p)
    a = p.parse_args()
    if getattr(a, "lang", None):
        set_lang(a.lang)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if a.search is not None:
        code, rows = search_rows(a.out, a.search, a.project, a.tag, a.limit)
        if code in (EXIT_UNAVAILABLE, EXIT_INTERNAL):
            return _db_problem(code, a.out, rows)
        if not rows:
            print(t("adb_no_results", query=a.search))
            return EXIT_EMPTY
        for r in rows:
            print(f"#{r['id']} [{r['project']}] {r['path']}:{r['start_line']}  {r['heading_path']}")
            print(f"   tags: {r['tags'] or '-'} ({r['tag_source'] or '-'})")
            print(f"   {r['snip']}")
        return EXIT_OK

    if a.stats:
        code, data = tag_counts(a.out, a.project, a.limit)
        if code in (EXIT_UNAVAILABLE, EXIT_INTERNAL):
            return _db_problem(code, a.out, data)
        for k, v in sorted(data["meta"].items()):
            print(f"  {k:16} {v}")
        print()
        for name, nfiles, nsnips in data["projects"]:
            print(f"  {name:22} {nfiles:4} files {nsnips:5} snippets")
        print()
        for name, n, from_claude in data["tags"]:
            print(f"  {name:22} {n:5}  (claude {from_claude})")
        return EXIT_OK

    sources = [("skills", SKILLS)]
    for d in a.source:
        full = os.path.abspath(os.path.expanduser(d))
        if not os.path.isdir(full):
            print(t("adb_missing", path=full))
            return EXIT_UNAVAILABLE
        base = label = os.path.basename(os.path.normpath(full))
        n = 2
        while any(label == seen for seen, _ in sources):   # two sources with the same name must not collide in file paths
            label, n = f"{base}-{n}", n + 1
        sources.append((label, full))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    return build(a.out, sources, a.tagger, a.model, a.effort)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (sqlite3.Error, OSError) as e:   # contract: an internal error is exit 3, not a traceback
        print(t("adb_internal", why=f"{type(e).__name__}: {e}"))
        sys.exit(EXIT_INTERNAL)
