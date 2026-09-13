#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mcp_server.py — muto-atlas'i MCP sunucusu olarak sunar (stdio ya da HTTP).

NEDEN: skill'ler "once veriye bak" kuralini anlatir, ama sorguyu calistiran
sey Claude Code'un kabuguydu. MCP ile ayni sorgular Cursor, VS Code (Copilot),
Codex, Gemini CLI, Claude Desktop ve -- HTTPS tuneliyle -- ChatGPT'den
cagrilir. Araclar mevcut betikleri calistirir; hicbir kural burada TEKRAR
yazilmaz, hicbir cikti yeniden yorumlanmaz.

Kullanim:
  python scripts/mcp_server.py                          # stdio: yerel istemciler
  python scripts/mcp_server.py --http --port 8765       # streamable HTTP, 127.0.0.1
  python scripts/mcp_server.py --http --allow-host <tunel-alan-adi>
  python scripts/mcp_server.py --list-tools [--http]    # kayitli araclari yaz, cik

GUVENLIK (--http):
  Kullanicinin KENDI dosyalarini okuyan araclar (doctor, structural_diff,
  light_read, lua_lint) ve KENDI sunucusunun haritasi (framework_api,
  lodaudit) HTTP modunda KAYDEDILMEZ. Tunel bu sunucuyu internete acar ve
  kimlik dogrulamasi yoktur. Katmanlar sunucu klasoruyle kurulduysa ozel
  arketip adlari da sorgulanabilir -- tuneli yalniz kullandigin surece ac.
  Yazan hicbir alt komut (light --apply/--set/--add/--remove, path) hicbir
  modda sunulmaz.

Her sonucun ilk satiri cikis kodunun anlamidir. exit 2 = katman kurulu degil:
sonuc hakkinda HICBIR SEY iddia edilemez.
"""
import argparse
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILLS = os.path.join(ROOT, "skills")
MAX_OUT = 60000
TIMEOUT = 300

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations
except ImportError:
    sys.stderr.write('mcp paketi yok / mcp package missing: python -m pip install "mcp>=1.28"\n')
    sys.exit(3)

INSTRUCTIONS = (
    "muto-atlas answers GTA V / FiveM questions from the game's own data instead of guessing.\n"
    "1. Before writing code that touches a prop, door, animation, flag, particle effect or native, query it "
    "(asset_show, asset_door, anim_search, flags_decode, particle_fx, native_check).\n"
    "2. Read the first line of every result. 'exit 2' means the data layer is not installed: say so and point "
    "to scripts/setup.py - never fill the gap with a guess.\n"
    "3. Decode magic numbers with flags_decode instead of copying them.\n"
    "4. For build rules (Sollumz, ytyp/ymap, LOD, lights, particles, clothing) call atlas_map, read the branch "
    "_branch.md with atlas_read, then ONE leaf. Do not read every file.\n"
    "5. Take native signatures from native_show, not from memory.\n"
    "6. To find what the knowledge base already says about a topic, call snippet_search (data/atlas.db) and "
    "snippet_read before reading whole files."
)

ASSETDB_EXIT = {
    0: "ok - found",
    1: "the query ran; the name is not in the authority",
    2: "data layer NOT installed - NOTHING can be claimed about this result; tell the user to run scripts/setup.py",
    3: "internal error (corrupt file) - this is NOT the same as 'does not exist'",
}
FILE_EXIT = {
    0: "ok - clean / no structural difference / lights found",
    1: "findings / structural difference / no lights",
    2: "at least one file could NOT be read or inspected - it must not be reported as clean",
    3: "internal error",
}
NATIVE_EXIT = {
    0: "ok",
    1: "a name was not found, or the native index is missing (see stderr) - do not invent names",
}

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


def _run(script, args, meaning=None, timeout=TIMEOUT):
    cmd = [sys.executable, os.path.join(HERE, script)] + [str(a) for a in args]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    # stdin=DEVNULL ZORUNLU: stdio modunda sunucunun stdin'i istemcinin borusudur ve bir is
    # parcacigi onu okurken bekler. Windows'ta bu boruyu miras alan alt surec acilista ayni
    # tutamakta bloke olur -> her cagri zaman asimina kadar asili kalir (olculdu, 2026-09-13:
    # data_status ve flags_decode 300 sn'de dustu).
    try:
        r = subprocess.run(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"exit timeout: {script} did not finish in {timeout}s - no result"
    what = (meaning or {}).get(r.returncode, "see the output below")
    out = (r.stdout or "").rstrip()
    if (r.stderr or "").strip():
        out += "\n[stderr]\n" + r.stderr.rstrip()
    if len(out) > MAX_OUT:
        out = out[:MAX_OUT] + f"\n... [{len(out) - MAX_OUT} characters truncated - narrow the query]"
    return f"exit {r.returncode}: {what}\n\n{out}"


def _opt(flag, value):
    """Option as `--flag=value` so a value starting with '-' is never read as an option."""
    if value is None or value is False:
        return []
    if value is True:
        return [flag]
    return [f"{flag}={value}"]


def _pos(values):
    """Positionals after `--` for the same reason."""
    return ["--"] + [str(v) for v in values]


# ---------------------------------------------------------------- vanilla data
def asset_show(names: list[str], raw: bool = False) -> str:
    """Full archetype record and verdict for props, objects and doors: door type, pivot, bbox, physics, lodDist. Query this before writing any code that touches a model."""
    return _run("assetdb.py", ["show", *_opt("--raw", raw), *_pos(names)], ASSETDB_EXIT)


def asset_door(names: list[str]) -> str:
    """Will the door system move this model? Decided from specialAttribute and the door-physics flag. specialAttribute 0 means it is NOT a door, whatever the natives say."""
    return _run("assetdb.py", ["door", *_pos(names)], ASSETDB_EXIT)


def asset_search(query: str, limit: int = 25) -> str:
    """Search archetype (model) names by substring."""
    return _run("assetdb.py", ["search", *_opt("--limit", limit), *_pos([query])], ASSETDB_EXIT)


def asset_where(names: list[str], limit: int = 25) -> str:
    """Every world placement of a model, including MLO interiors. One prop is often placed in several places; do not hard-code a single coordinate."""
    return _run("assetdb.py", ["where", *_opt("--limit", limit), *_pos(names)], ASSETDB_EXIT)


def asset_near(x: float, y: float, z: float, radius: float = 10.0, name_filter: str | None = None, limit: int = 25) -> str:
    """Models placed near a world coordinate. name_filter narrows by model name substring."""
    return _run("assetdb.py", ["near", *_opt("--radius", radius), *_opt("--filter", name_filter),
                               *_opt("--limit", limit), *_pos([x, y, z])], ASSETDB_EXIT)


def anim_search(query: str, dictionary: bool = False, dict_only: bool = False, limit: int = 25) -> str:
    """Vanilla animation dictionaries and clips with real duration and bone count. dictionary=True lists one dictionary grouped by duration, which exposes ped + prop clip pairs. Never invent an animation name that is not listed."""
    return _run("assetdb.py", ["anim", *_opt("--dict", dictionary), *_opt("--dict-only", dict_only),
                               *_opt("--limit", limit), *_pos([query])], ASSETDB_EXIT)


def bones(names: list[str], limit: int = 200) -> str:
    """Skeleton of a model: bone names and tags. A model without a skeleton cannot play PlayEntityAnim or take bone-index attachments."""
    return _run("assetdb.py", ["bones", *_opt("--limit", limit), *_pos(names)], ASSETDB_EXIT)


def clipfit(dictionary: str, clip: str, limit: int = 25) -> str:
    """Which models a vanilla clip can play on, matched by the bone tags it drives."""
    return _run("assetdb.py", ["clipfit", *_opt("--limit", limit), *_pos([dictionary, clip])], ASSETDB_EXIT)


def flags_decode(value: str, entity: bool = False) -> str:
    """Decode a flag integer (e.g. 1572872 or 0x180008) into flag names. entity=True for ymap entity flags, otherwise archetype (ytyp) flags. Magic numbers are decoded, never copied."""
    return _run("assetdb.py", ["flags", *_opt("--entity", entity), *_pos([value])], ASSETDB_EXIT)


def particle_fx(query: str, exact: bool = False, limit: int = 25) -> str:
    """Is this a real particle effect name (fxName) and which asset holds it. exact=True for a strict yes/no check. A misspelled fxName shows nothing and raises no error."""
    return _run("assetdb.py", ["fx", *_opt("--exact", exact), *_opt("--limit", limit), *_pos([query])], ASSETDB_EXIT)


def world_objects(family: str | None = None, model: str | None = None, near: str | None = None,
                  radius: float | None = None, list_families: bool = False, limit: int = 25) -> str:
    """Labelled world objects (ATMs, CCTV cameras, benches, bins...) with rotation. near is 'x,y,z'. list_families=True lists the families."""
    return _run("assetdb.py", ["world", *_opt("--families", list_families), *_opt("--family", family),
                               *_opt("--model", model), *_opt("--near", near), *_opt("--radius", radius),
                               *_opt("--limit", limit)], ASSETDB_EXIT)


def data_status() -> str:
    """Which data layers are installed and which are missing. Run this whenever a query returns exit 2."""
    return _run("assetdb.py", ["stats"], ASSETDB_EXIT)


# ---------------------------------------------------------------- natives
def native_check(names: list[str], apiset: str | None = None) -> str:
    """Does a FiveM / GTA V native exist, and on which side (client, server, shared)? Check every native name before using it."""
    return _run("nativedb.py", ["check", *_opt("--apiset", apiset), *_pos(names)], NATIVE_EXIT)


def native_show(names: list[str]) -> str:
    """Full native signature, parameters, docs link and example. Take the parameter order from here, not from memory."""
    return _run("nativedb.py", ["show", *_pos(names)], NATIVE_EXIT)


def native_search(query: str, apiset: str | None = None, namespace: str | None = None, limit: int = 25) -> str:
    """Find a native by keyword, optionally only those callable on one side (apiset: client, server or shared) or in one namespace."""
    return _run("nativedb.py", ["search", *_opt("--apiset", apiset), *_opt("--ns", namespace),
                                *_opt("--limit", limit), *_pos([query])], NATIVE_EXIT)


# ---------------------------------------------------------------- knowledge tree
def _md_files():
    for dp, dn, fn in os.walk(SKILLS):
        dn[:] = sorted(d for d in dn if not d.startswith((".", "_")))
        for f in sorted(fn):
            if f.endswith(".md"):
                yield os.path.join(dp, f)


def _rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def atlas_map() -> str:
    """Map of the knowledge tree: trunk files, branches and leaves with their titles. Start here, then read the branch _branch.md, then ONE leaf."""
    lines = ["Routing: open the branch _branch.md first, then one leaf. Do not read every file.", ""]
    for p in _md_files():
        title = ""
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        lines.append(f"{_rel(p)}  -  {title}")
    return "\n".join(lines)


def atlas_read(path: str, start_line: int = 1, max_lines: int = 400) -> str:
    """Read one knowledge file by the path atlas_map or atlas_search returned. Long files are paged with start_line."""
    base = os.path.normcase(os.path.realpath(SKILLS))
    target = None
    for cand in (os.path.join(ROOT, path), os.path.join(SKILLS, path)):
        real = os.path.realpath(cand)
        if os.path.normcase(real).startswith(base + os.sep) and real.endswith(".md") and os.path.isfile(real):
            target = real
            break
    if target is None:
        return f"refused: '{path}' is not a knowledge file under skills/"
    with io.open(target, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    s = max(1, int(start_line))
    e = min(len(lines), s + max(1, min(int(max_lines), 1000)) - 1)
    body = "\n".join(f"{i}: {lines[i - 1]}" for i in range(s, e + 1))
    more = f"\n... {len(lines) - e} more lines (start_line={e + 1})" if e < len(lines) else ""
    return f"{_rel(target)} lines {s}-{e} of {len(lines)}\n\n{body}{more}"


def atlas_search(query: str, limit: int = 30) -> str:
    """Case-insensitive text search across the knowledge tree. Returns path:line: text."""
    q = query.lower().strip()
    if not q:
        return "empty query"
    hits = []
    for p in _md_files():
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                if q in line.lower():
                    hits.append(f"{_rel(p)}:{i}: {line.strip()[:200]}")
                    if len(hits) >= limit:
                        return "\n".join(hits) + f"\n... limit {limit} reached"
    return "\n".join(hits) if hits else f"no match for '{query}'"


# ---------------------------------------------------------------- snippet database (data/atlas.db)
def _adb():
    import build_atlas_db
    return build_atlas_db


def _db_trouble(adb, code, detail):
    if code == adb.EXIT_UNAVAILABLE:
        return "exit 2: data/atlas.db is not built - run: python scripts/build_atlas_db.py"
    if code == adb.EXIT_INTERNAL:
        return f"exit 3: data/atlas.db could not be read ({detail}) - rebuild it: python scripts/build_atlas_db.py"
    return None


def snippet_search(query: str, project: str | None = None, tag: str | None = None, limit: int = 20) -> str:
    """Full-text search over the knowledge snippets in data/atlas.db. project is a folder name such as look, map, prop, particle or govde; tag is a name from snippet_tags. Use snippet_read for the full text of a hit."""
    adb = _adb()
    code, rows = adb.search_rows(adb.DEFAULT_DB, query, project, tag, max(1, min(int(limit), 100)))
    trouble = _db_trouble(adb, code, rows)
    if trouble:
        return trouble
    if not rows:
        return f"exit 1: no snippet matches '{query}'"
    out = [f"exit 0: {len(rows)} snippets", ""]
    for r in rows:
        out.append(f"#{r['id']} [{r['project']}] {r['path']}:{r['start_line']}  {r['heading_path']}")
        out.append(f"   tags: {r['tags'] or '-'} ({r['tag_source'] or '-'})")
        out.append(f"   {r['snip']}")
    return "\n".join(out)


def snippet_read(snippet_id: int) -> str:
    """Full text of one snippet returned by snippet_search, with its file, line range and tags."""
    adb = _adb()
    code, row = adb.read_snippet(adb.DEFAULT_DB, int(snippet_id))
    trouble = _db_trouble(adb, code, row)
    if trouble:
        return trouble
    if row is None:
        return f"exit 1: no snippet #{snippet_id}"
    return (f"exit 0: #{row['id']} [{row['project']}] {row['path']} lines {row['start_line']}-{row['end_line']}\n"
            f"heading: {row['heading_path']}\ntags: {row['tags'] or '-'} ({row['tag_source'] or '-'})\n\n{row['content']}")


def snippet_tags(project: str | None = None, limit: int = 60) -> str:
    """Projects (folder names) and tag counts in data/atlas.db, optionally for one project. Use a tag name with snippet_search."""
    adb = _adb()
    code, data = adb.tag_counts(adb.DEFAULT_DB, project, max(1, min(int(limit), 500)))
    trouble = _db_trouble(adb, code, data)
    if trouble:
        return trouble
    meta = data["meta"]
    out = [f"exit 0: tagger {meta.get('tagger', '?')}, built {meta.get('built_at', '?')}", "", "projects:"]
    out += [f"  {name}: {nfiles} files, {nsnips} snippets" for name, nfiles, nsnips in data["projects"]]
    out += ["", "tags" + (f" in {project}" if project else "") + ":"]
    out += [f"  {name}: {n} (claude {from_claude})" for name, n, from_claude in data["tags"]]
    return "\n".join(out)


# ---------------------------------------------------------------- local files (stdio only)
def doctor(paths: list[str], recursive: bool = False, level: str | None = None) -> str:
    """Silent-failure gate for YOUR asset files (.ytyp incl. MLO rooms and portals, .ydr, .yft, .ycd): FATAL / SILENT / WARN. Use absolute paths. level: fatal, silent or warn."""
    return _run("assetdb.py", ["doctor", *_opt("-r", recursive), *_opt("--level", level), *_pos(paths)], FILE_EXIT)


def structural_diff(mine: str, vanilla: str, limit: int = 50) -> str:
    """Compare two resource files by which nodes exist, not by values. A missing node is what crashes an export that reported 0 warnings. Use absolute paths."""
    return _run("assetdb.py", ["diff", *_opt("--limit", limit), *_pos([mine, vanilla])], FILE_EXIT)


def light_read(path: str, vanilla_table: bool = False, raw: bool = False) -> str:
    """Decode the lights embedded in a .ydr/.yft: hours (TimeFlags), cone, falloff, flags and the bone they hang from. vanilla_table=True adds the measured vanilla band. Read-only: editing is not exposed."""
    return _run("assetdb.py", ["light", *_opt("--tablo", vanilla_table), *_opt("--ham", raw), *_pos([path])], FILE_EXIT)


def lua_lint(paths: list[str], side: str = "auto") -> str:
    """Lint FiveM Lua for invented natives, natives on the wrong side, wrong argument counts and per-frame mistakes. side: auto, client, server or shared. Use absolute paths."""
    return _run("lint_lua.py", [*_opt("--side", side), *_pos(paths)])


def framework_api(query: str | None = None, kind: str | None = None, definitions_only: bool = False,
                  check: bool = False, limit: int = 25) -> str:
    """Exports, events, callbacks and commands YOUR server actually defines (QBCore / Qbox / ESX / ox). check=True lists calls that will fail at runtime."""
    args = ["framework", *_opt("--kind", kind), *_opt("--defs", definitions_only), *_opt("--check", check), *_opt("--limit", limit)]
    if query:
        args += _pos([query])
    return _run("assetdb.py", args, ASSETDB_EXIT)


# ---------------------------------------------------------------- generic query
SAFE_SUBCOMMANDS = {"show", "door", "search", "where", "near", "anim", "bones", "clipfit", "expr", "prop", "scenario",
                    "propanim", "ptfx", "fx", "ext", "lod", "proc", "decal", "shader", "mat", "lodchain", "flags",
                    "pedmeta", "weapon", "vehicle", "mlo", "ipl", "world", "timecycle", "cycle", "stats"}
LOCAL_SUBCOMMANDS = {"doctor", "diff", "light", "framework", "lodaudit"}
WRITE_FLAGS = {"--apply", "--set", "--add", "--remove"}


def make_assetdb_query(http):
    allowed = SAFE_SUBCOMMANDS | (set() if http else LOCAL_SUBCOMMANDS)

    def assetdb_query(subcommand: str, args: list[str] | None = None) -> str:
        sub = (subcommand or "").strip().lower()
        if sub not in allowed:
            return f"refused: '{subcommand}' is not available here. Allowed: {', '.join(sorted(allowed))}"
        a = [str(x) for x in (args or [])]
        writes = [x for x in a if x.split("=", 1)[0] in WRITE_FLAGS]
        if writes:
            return f"refused: write options are not exposed over MCP: {writes}"
        if http and sub == "timecycle" and any(x.split("=", 1)[0] == "--mlo" for x in a):
            return "refused: timecycle --mlo reads a local file and is not available over HTTP"
        return _run("assetdb.py", [sub, *a], FILE_EXIT if sub in ("doctor", "diff", "light") else ASSETDB_EXIT)

    desc = ("Run a read-only assetdb subcommand that has no dedicated tool, with arguments exactly as on the command "
            "line, e.g. subcommand='weapon', args=['--parts', 'WEAPON_CARBINERIFLE']; subcommand='timecycle', "
            "args=['int_hospital_dark']; subcommand='ptfx', args=['--type=4']. Available: " + ", ".join(sorted(allowed)) + ".")
    return assetdb_query, desc


SAFE_TOOLS = [asset_show, asset_door, asset_search, asset_where, asset_near, anim_search, bones, clipfit,
              flags_decode, particle_fx, world_objects, data_status, native_check, native_show, native_search,
              atlas_map, atlas_read, atlas_search, snippet_search, snippet_read, snippet_tags]
LOCAL_TOOLS = [doctor, structural_diff, light_read, lua_lint, framework_api]


def build(http=False, host="127.0.0.1", port=8765, allow_hosts=(), allow_origins=()):
    kw = {"instructions": INSTRUCTIONS}
    if http:
        from mcp.server.transport_security import TransportSecuritySettings
        hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
        for h in allow_hosts:
            hosts += [h, f"{h}:*"]
        kw.update(host=host, port=port, transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True, allowed_hosts=hosts, allowed_origins=list(allow_origins)))
    server = FastMCP("muto-atlas", **kw)
    for fn in SAFE_TOOLS + ([] if http else LOCAL_TOOLS):
        server.add_tool(fn, annotations=READ_ONLY)
    query_fn, query_desc = make_assetdb_query(http)
    server.add_tool(query_fn, name="assetdb_query", description=query_desc, annotations=READ_ONLY)
    return server


def main():
    p = argparse.ArgumentParser(description="muto-atlas MCP server (stdio by default)")
    p.add_argument("--http", action="store_true", help="serve streamable HTTP at /mcp instead of stdio")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--allow-host", action="append", default=[], metavar="HOST",
                   help="extra Host header to accept in --http mode (e.g. your tunnel domain); repeatable")
    p.add_argument("--allow-origin", action="append", default=[], metavar="ORIGIN",
                   help="extra Origin header to accept in --http mode; repeatable")
    p.add_argument("--lang", choices=("tr", "en"), help="output language of the underlying tools")
    p.add_argument("--list-tools", action="store_true", help="print the registered tool names and exit")
    a = p.parse_args()
    if a.lang:
        os.environ["MUTO_ATLAS_LANG"] = a.lang
    server = build(a.http, a.host, a.port, a.allow_host, a.allow_origin)
    if a.list_tools:
        import anyio
        tools = anyio.run(server.list_tools)
        print("\n".join(sorted(tool.name for tool in tools)))
        return 0
    if a.http:
        sys.stderr.write(f"muto-atlas MCP (streamable HTTP) on http://{a.host}:{a.port}/mcp - "
                         "local-file and own-server tools are NOT registered in this mode\n")
        server.run(transport="streamable-http")
    else:
        server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
