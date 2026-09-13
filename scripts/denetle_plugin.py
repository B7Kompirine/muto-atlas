"""denetle_plugin.py -- muto-atlas plugin butunluk denetimi.

NEDEN: plugin buyudukce atiflar sessizce kirilir. Bir komut olmayan referansa
isaret eder, bir referans hicbir yerden cagrilmaz, bir .ps1 BOM'suz kalir ve
PowerShell 5.1 onu bozuk okur -- hicbiri hata vermez.

Denetlenenler:
  1. plugin.json / marketplace.json ayrisiyor mu, ad uyusuyor mu
  2. komut frontmatter'i tam mi; description INGILIZCE, govde TURKCE mi
  3. atif verilen her references/*.md var mi (IKI skill klasoru birden --
     tek klasore bakan bir denetleyici yanlis pozitif uretir, yasandi)
  4. hicbir yerden cagrilmayan YETIM referans var mi
  5. atif verilen her scripts/* var mi ("henuz yazilmadi" isaretliler haric)
  6. .ps1 dosyalarinda ASCII disi karakter varsa BOM var mi
  7. SKILL.md frontmatter'i klasor adiyla uyusuyor mu
 11. Sayac tutarliligi (katman/dal/yaprak/komut) + yetim betik
 10. Ortusme: tekrarlanan baslik / birebir kopya blok
  9. Yaprakta govde kurali tekrari (kisa madde) -> NOT
  8. AGAC: dallar/<dal>/_dal.md var mi, yaprak tablosu <-> disk, yetim yaprak,
     SKILL.md her dali aniyor mu, _dal.md/SKILL.md satir tavani, tasima kaydi

Cikis kodu: sorun varsa 1, temizse 0.

Kullanim:  python scripts/denetle_plugin.py [--lang en|tr]
           Rapor dili diger betiklerle ayni secilir: --lang > MUTO_ATLAS_LANG > config > en.
"""
import argparse, io, os, re, json, sys

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
    """Rapor satiri iki dilde yazilir; hangisinin basilacagi i18n ile ayni kurala uyar."""
    return en if EN else tr


problems, notes = [], []

def read(p):
    return io.open(p, encoding='utf-8', errors='replace').read()

# ---------- 1. JSON ----------
for rel in (r".claude-plugin\plugin.json", r".claude-plugin\marketplace.json"):
    p = os.path.join(A, rel)
    try:
        json.load(io.open(p, encoding='utf-8'))
        notes.append(f"JSON ok: {rel}")
    except Exception as e:
        problems.append(L(f"JSON BOZUK: {rel} -> {e}", f"BROKEN JSON: {rel} -> {e}"))

pj = json.load(io.open(os.path.join(A, r".claude-plugin\plugin.json"), encoding='utf-8'))
mj = json.load(io.open(os.path.join(A, r".claude-plugin\marketplace.json"), encoding='utf-8'))
if pj["name"] != mj["plugins"][0]["name"]:
    problems.append(L(f"plugin adi uyusmuyor: {pj['name']} vs {mj['plugins'][0]['name']}",
                      f"plugin name mismatch: {pj['name']} vs {mj['plugins'][0]['name']}"))

# ---------- 2. commands frontmatter ----------
cmd_dir = os.path.join(A, "commands")
cmds = sorted(f for f in os.listdir(cmd_dir) if f.endswith(".md"))
TR = set("çğıöşüÇĞİÖŞÜ")
for f in cmds:
    txt = read(os.path.join(cmd_dir, f))
    if not txt.startswith("---"):
        problems.append(L(f"komut frontmatter YOK: {f}", f"command has NO frontmatter: {f}"))
        continue
    fm = txt.split("---", 2)[1]
    for key in ("description",):
        if not re.search(rf"^{key}:", fm, re.M):
            problems.append(L(f"komut '{f}': '{key}' alani eksik", f"command '{f}': '{key}' field missing"))
    for key in ("argument-hint", "allowed-tools"):
        if not re.search(rf"^{key}:", fm, re.M):
            notes.append(L(f"komut '{f}': '{key}' yok (istege bagli)", f"command '{f}': no '{key}' (optional)"))
    m = re.search(r"^description:\s*(.+)$", fm, re.M)
    if m and (set(m.group(1)) & TR):
        problems.append(L(f"komut '{f}': description TURKCE karakter iceriyor "
                          f"(konvansiyon: frontmatter Ingilizce)",
                          f"command '{f}': description contains TURKISH characters "
                          f"(convention: frontmatter in English)"))
    body = txt.split("---", 2)[2]
    if not (set(body) & TR):
        notes.append(L(f"komut '{f}': govdede Turkce karakter yok (konvansiyon: govde Turkce)",
                       f"command '{f}': no Turkish characters in the body (convention: body in Turkish)"))

# ---------- 3. referanslar: var mi / yetim mi ----------
ref_dirs = [os.path.join(A, "skills", s_, "references")
            for s_ in ("fivem-assets", "fivem-natives")]
refs_on_disk = set()
for d_ in ref_dirs:
    if os.path.isdir(d_):
        refs_on_disk |= {f for f in os.listdir(d_) if f.endswith(".md")}

md_files = []
for root, _, files in os.walk(A):
    if ".git" in root or os.sep + "_arsiv" in root:
        continue
    for f in files:
        if f.endswith((".md", ".ps1", ".py")):
            md_files.append(os.path.join(root, f))

mentioned = set()
for p in md_files:
    for m in re.finditer(r"references/([A-Za-z0-9._-]+\.md)", read(p)):
        mentioned.add(m.group(1))

for r in sorted(mentioned - refs_on_disk):
    problems.append(L(f"ATIF VAR DOSYA YOK: references/{r}", f"REFERENCED FILE MISSING: references/{r}"))
for r in sorted(refs_on_disk - mentioned):
    problems.append(L(f"YETIM REFERANS (hicbir yerden atif yok): references/{r}",
                      f"ORPHAN REFERENCE (nothing links to it): references/{r}"))

# ---------- 3b. AGAC: govde/ + dallar/<dal>/ + _arsiv/ ----------
# NEDEN: bilgi govde/dal/yaprak agacina tasindi. Yaprak dosyasi _dal.md
# tablosunda yoksa ulasilamaz (yetim); tabloda olup diskte yoksa kirik bag.
# _arsiv/ gunluktur, taranmaz. Buyuyen _dal.md ve SKILL.md uyari alir.
FA = os.path.join(A, "skills", "fivem-assets")
govde_dir = os.path.join(FA, "govde")
dallar_dir = os.path.join(FA, "dallar")
skill_txt = read(os.path.join(FA, "SKILL.md"))

tree_on_disk = set()
kaynaklar_dir = os.path.join(FA, "kaynaklar")
for base in (govde_dir, dallar_dir, kaynaklar_dir):
    if os.path.isdir(base):
        for root, _, files in os.walk(base):
            for f in files:
                if f.endswith(".md"):
                    rel = os.path.relpath(os.path.join(root, f), FA).replace("\\", "/")
                    tree_on_disk.add(rel)

tree_mentioned = set()
for p_ in md_files:
    if os.sep + "_arsiv" + os.sep in p_:
        continue
    for m in re.finditer(r"(?:govde|dallar|kaynaklar)/[A-Za-z0-9._/-]+?\.md", read(p_)):
        tree_mentioned.add(m.group(0))
# planli (tasinacak) yapraklari topla: onlara atif sorun degil, not
planli_tum = set()
if os.path.isdir(dallar_dir):
    for dal_ in os.listdir(dallar_dir):
        dm_ = os.path.join(dallar_dir, dal_, "_dal.md")
        if os.path.exists(dm_):
            for row_ in re.finditer(r"^\|[^|\n]*\|\s*([A-Za-z0-9._-]+\.md)\s*\|([^\n]*)$", read(dm_), re.M):
                if "taşınacak" in row_.group(2) or "tasinacak" in row_.group(2):
                    planli_tum.add(f"dallar/{dal_}/{row_.group(1)}")
for r in sorted(tree_mentioned - tree_on_disk):
    if r in planli_tum:
        notes.append(L(f"planli yapraga atif (henuz yazilmadi): {r}", f"link to a planned leaf (not written yet): {r}"))
    else:
        problems.append(L(f"ATIF VAR DOSYA YOK: {r}", f"REFERENCED FILE MISSING: {r}"))

if os.path.isdir(dallar_dir):
    for dal in sorted(os.listdir(dallar_dir)):
        dp = os.path.join(dallar_dir, dal)
        if not os.path.isdir(dp):
            continue
        dal_md = os.path.join(dp, "_dal.md")
        if not os.path.exists(dal_md):
            problems.append(L(f"DAL DOSYASI YOK: dallar/{dal}/_dal.md", f"BRANCH FILE MISSING: dallar/{dal}/_dal.md"))
            continue
        dt = read(dal_md)
        # yaprak tablosu: | istenen | dosya.md | durum — kaynak |
        listed, planned = set(), set()
        for row in re.finditer(r"^\|[^|\n]*\|\s*([A-Za-z0-9._-]+\.md)\s*\|([^\n]*)$", dt, re.M):
            f, rest = row.group(1), row.group(2)
            if f == "_dal.md":
                continue
            (planned if "taşınacak" in rest or "tasinacak" in rest else listed).add(f)
        on_disk = {f for f in os.listdir(dp) if f.endswith(".md") and f != "_dal.md"}
        for f in sorted(listed - on_disk):
            problems.append(L(f"dallar/{dal}/_dal.md yaprak listeliyor, dosya yok: {f}",
                              f"dallar/{dal}/_dal.md lists a leaf that does not exist: {f}"))
        for f in sorted(on_disk - listed - planned):
            problems.append(L(f"YETIM YAPRAK (dal tablosunda yok): dallar/{dal}/{f}",
                              f"ORPHAN LEAF (not in the branch table): dallar/{dal}/{f}"))
        for f in sorted(planned & on_disk):
            problems.append(L(f"dallar/{dal}/{f} yazilmis ama tabloda hala 'tasinacak': durumu guncelle",
                              f"dallar/{dal}/{f} exists but its table row still says 'tasinacak' (to be moved): update it"))
        if planned - on_disk:
            notes.append(L(f"dallar/{dal}: {len(planned - on_disk)} yaprak henuz tasinmadi",
                           f"dallar/{dal}: {len(planned - on_disk)} leaves not moved yet"))
        n = dt.count("\n")
        if n > 150:
            notes.append(L(f"dallar/{dal}/_dal.md {n} satir (>150) -> fazlasi yapraga insin",
                           f"dallar/{dal}/_dal.md is {n} lines (>150) -> move the extra into leaves"))
        if f"dallar/{dal}/" not in skill_txt:
            problems.append(L(f"SKILL.md 'dallar/{dal}/' dalini anmiyor", f"SKILL.md does not mention the 'dallar/{dal}/' branch"))
        # tasima kaydi: yapragin Kaynak satirindaki eski dosya hala references/ altindaysa
        for f in sorted(on_disk):
            lt = read(os.path.join(dp, f))
            m = re.search(r"\*\*Kaynak:\*\*\s*(.+)", lt)
            if m:
                for old in re.findall(r"([A-Za-z0-9._-]+\.md)", m.group(1)):
                    if old in refs_on_disk:
                        notes.append(L(f"dallar/{dal}/{f}: kaynak references/{old} hala duruyor (tasima bitmemis)",
                                       f"dallar/{dal}/{f}: its source references/{old} still exists (move not finished)"))

# govde olcutu: govde dosyasi en az 4 dalda anilmali (her dalda gecerli mi)
_dal_sayisi = len([d for d in os.listdir(dallar_dir) if os.path.isdir(os.path.join(dallar_dir, d))])
for gf_ in sorted(f for f in os.listdir(govde_dir) if f.endswith(".md")):
    kac_ = sum(1 for dal_ in os.listdir(dallar_dir)
               if os.path.isdir(os.path.join(dallar_dir, dal_))
               and gf_ in read(os.path.join(dallar_dir, dal_, "_dal.md")))
    if kac_ < 4 and gf_ != "gta-temel.md":
        notes.append(L(f"govde/{gf_}: yalniz {kac_}/{_dal_sayisi} dalda aniliyor -> her dalda gecerli mi, yoksa kaynaklar/ mi?",
                       f"govde/{gf_}: mentioned in only {kac_}/{_dal_sayisi} branches -> does it hold for every branch, or belong in kaynaklar/?"))

n = skill_txt.count("\n")
if n > 250:
    notes.append(L(f"fivem-assets/SKILL.md {n} satir (>250) -> govde/ altina in",
                   f"fivem-assets/SKILL.md is {n} lines (>250) -> move content into govde/"))

# ---------- 3c. YAPRAKTA GOVDE KURALI TEKRARI (not) ----------
# NEDEN: agacin amaci ortak kurali BIR kez, govde/_dal'da tutmak. Bir yaprakta
# yalniz govde kuralini tasiyan kisa (<=3 satir) madde gorulurse bayatlama
# riskidir; isaretci ver ("-> govde/arac-tuzaklari.md"), tekrar yazma.
GOVDE_KURAL = [
    ("yeniden baglan", r"yeniden bağlan|restart yetmez"),
    ("LiteralPath", r"-literalpath"),
    ("xml_to_ycd", r"xml_to_ycd\.ps1|format sisteminin dışında"),
    ("Hash yazmaz", r"<hash>.{0,30}yazmaz|fix_ycd_xml"),
    ("24 fps", r"24 fps"), ("Mesh Domain", r"mesh domain"), ("$null", r"\$null\.length"),
    ("boyut olcut degil", r"boyut.{0,30}ölçüt"), ("ekran goruntusu", r"ekran görüntüsü.{0,20}ölçüm değil"),
    ("gostermemesi", r"aracın (bir şeyi )?göstermemesi"), ("use_custom_settings", r"use_custom_settings"),
    ("sz_lods", r"sz_lods\.high\.mesh"), ("hide_select", r"hide_select"), ("target_id", r"target_id.{0,40}(data|armature)"),
    ("-File dizi", r"-file.{0,40}(tek string|virgül)"), ("pymateria", r"pymateria"), ("PYTHONIOENCODING", r"pythonioencoding"),
]
_OZGUL = re.compile(r"ölçüldü|ölçüm|\d{3,}|bu (turda|projede|işte|oturumda)|yaşandı|örnek|→ ?`?(govde|dallar)/", re.I)
_BUL = re.compile(r"^(\s*)([-*]|\d+[a-z]?\.)\s+")
tekrar = 0
if os.path.isdir(dallar_dir):
    for dal_ in sorted(os.listdir(dallar_dir)):
        dp_ = os.path.join(dallar_dir, dal_)
        if not os.path.isdir(dp_): continue
        for f_ in sorted(os.listdir(dp_)):
            if not f_.endswith(".md") or f_ == "_dal.md": continue
            ls_ = read(os.path.join(dp_, f_)).split("\n"); i_ = 0
            while i_ < len(ls_):
                m_ = _BUL.match(ls_[i_])
                if not m_: i_ += 1; continue
                ind_ = len(m_.group(1)); j_ = i_ + 1
                while j_ < len(ls_) and ls_[j_].strip() and (len(ls_[j_]) - len(ls_[j_].lstrip())) > ind_ and not _BUL.match(ls_[j_]): j_ += 1
                blk_ = "\n".join(ls_[i_:j_])
                if (j_ - i_) <= 3 and not _OZGUL.search(blk_):
                    hit_ = [e for e, rx in GOVDE_KURAL if re.search(rx, blk_.lower())]
                    if hit_:
                        tekrar += 1
                        notes.append(L(f"yaprakta govde kurali tekrari ({hit_[0]}): dallar/{dal_}/{f_}: {ls_[i_].strip()[:70]}",
                                       f"trunk rule repeated in a leaf ({hit_[0]}): dallar/{dal_}/{f_}: {ls_[i_].strip()[:70]}"))
                i_ = j_
if tekrar == 0:
    notes.append(L("yaprak/govde tekrari: 0 (kisa madde olcutuyle)", "leaf/trunk repeats: 0 (short-item check)"))

# ---------- 3d. ORTUSME: tekrarlanan baslik + birebir kopyalanmis blok ----------
# NEDEN: agacin sozu "bir kez, en genis yerde". Ayni dosyada ayni baslik iki kez
# gecerse ya blok kopyalanmistir (bilgi ikiye ayrilir, biri bayatlar) ya da iki
# ayri sey ayni adi tasiyor (arama yanlis yere goturur). Iki dosyada birebir ayni
# uzun blok da ayni kusurdur. _arsiv/ gunluktur, taranmaz.
_canli = []
for _r, _d, _fs in os.walk(FA):
    if ".git" in _r or os.sep + "_arsiv" in _r:
        continue
    for _f in _fs:
        if _f.endswith(".md"):
            _canli.append(os.path.join(_r, _f))

_ortusme = 0
_bas = re.compile(r"^#{2,4}\s+(.+?)\s*$", re.M)
for _p in sorted(_canli):
    _c = {}
    for _m in _bas.finditer(read(_p)):
        _k = _m.group(1)
        _c[_k] = _c.get(_k, 0) + 1
    for _k, _v in _c.items():
        # kisa/genel altbaslik (Olcum, Sirayla, Dogrulama...) bir dosyada birden
        # cok bolumde gecebilir; kopya belirtisi degildir.
        if _v > 1 and len(_k) >= 14:
            _ortusme += 1
            _rel = os.path.relpath(_p, A).replace("\\", "/")
            problems.append(L("TEKRARLANAN BASLIK: %s icinde '%s' %d kez — blok kopyalanmis ya da iki ayri sey ayni adi tasiyor"
                              % (_rel, _k[:60], _v),
                              "REPEATED HEADING: '%s' appears %d times in %s — a block was copied, or two different things share one name"
                              % (_k[:60], _v, _rel)))

# birebir kopya blok: >=6 anlamli ardisik satir, iki ayri yerde
def _anlamli(_ls):
    _o = []
    for _i, _s in enumerate(_ls):
        _x = _s.strip()
        if len(_x) >= 30 and not _x.startswith(("|---", "---", "```", "#")):
            _o.append((_i, _x))
    return _o
_pen = {}
for _p in sorted(_canli):
    _ls = read(_p).split("\n")
    _an = _anlamli(_ls)
    for _j in range(len(_an) - 5):
        _win = tuple(_x for _, _x in _an[_j:_j + 6])
        if _an[_j + 5][0] - _an[_j][0] > 12:   # arada cok bosluk varsa blok degil
            continue
        _pen.setdefault(_win, []).append((os.path.relpath(_p, A).replace("\\", "/"), _an[_j][0] + 1))
_gorulen = set()
for _win, _yer in _pen.items():
    if len(_yer) < 2:
        continue
    _imza = tuple(sorted(set(_y[0] for _y in _yer)))
    if _imza in _gorulen:
        continue
    _gorulen.add(_imza)
    _ortusme += 1
    _yerler = " · ".join("%s:%d" % _y for _y in _yer[:3])
    problems.append(L("BIREBIR KOPYA BLOK (>=6 satir): " + _yerler + " — bilgi bir kez, en genis yerde yazilir",
                      "IDENTICAL BLOCK (>=6 lines): " + _yerler + " — write knowledge once, in the widest place"))
if not _ortusme:
    notes.append(L("ortusme: tekrarlanan baslik 0, birebir kopya blok 0 (%d canli md)" % len(_canli),
                   "overlap: repeated headings 0, identical blocks 0 (%d live md files)" % len(_canli)))

# ---------- 4. scripts: atif var mi ----------
script_dir = os.path.join(A, "scripts")
scripts_on_disk = {f for f in os.listdir(script_dir)
                   if f.endswith((".py", ".ps1")) and not f.startswith("_")}
script_mentioned = set()
for p in md_files:
    for m in re.finditer(r"scripts/([A-Za-z0-9._-]+\.(?:py|ps1))", read(p)):
        script_mentioned.add(m.group(1))
all_text = chr(10).join(read(p_) for p_ in md_files)
for s_ in sorted(script_mentioned - scripts_on_disk):
    ctx = re.search("scripts/" + re.escape(s_) + "[^" + chr(10) + "]*", all_text)
    line = ctx.group(0) if ctx else ""
    if "yazilmadi" in line or "yazılmadı" in line or "TODO" in line:
        notes.append(L(f"scripts/{s_}: atif var, dosya yok — ama belgede "
                       f"'henuz yazilmadi' diye ISARETLI (bilinen acik is)",
                       f"scripts/{s_}: referenced but missing — MARKED 'not written yet' "
                       f"in the docs (known open work)"))
    else:
        problems.append(L(f"ATIF VAR BETIK YOK: scripts/{s_}", f"REFERENCED SCRIPT MISSING: scripts/{s_}"))

# ---------- 5. slash komut atiflari ----------
cmd_names = {f[:-3] for f in cmds}
referred_cmds = set()
for p in md_files:
    for m in re.finditer(r"komut:\s*`?/([a-z0-9-]+)`?|`/([a-z0-9-]+)`", read(p)):
        referred_cmds.add(m.group(1) or m.group(2))
# OYUN ICI / DIS komutlar: bunlar FiveM sunucusunda ya da baska bir aracta
# calisir, plugin komutu DEGILDIR. Beyaz listede olmayan bir eksik komut
# GERCEK kirik atiftir (bir plugin komutu kaldirildi ama atif kaldi) -> SORUN.
KNOWN_EXTERNAL = {
    # olcum/test icin sunucuya kurulmus kendi oyun ici komutlarimiz
    "pxm", "pxmturn", "pxmdel", "pxmprobe", "dev", "obje", "panel",
    "lapnext", "latest",
    "ptfx", "ptfxdur", "ptfxkat", "ptfxsira", "ptfxt1", "spor",
    # Claude Code'un kendi komutlari
    "timecycle", "loop", "schedule", "help",
}
eksik_komut = sorted(referred_cmds - cmd_names - KNOWN_EXTERNAL)
for c in eksik_komut:
    problems.append(L(f"KIRIK KOMUT ATIFI: '/{c}' aniliyor ama commands/{c}.md yok "
                      f"(plugin komutu kaldirildiysa atiflari da guncelle; oyun ici "
                      f"komutsa KNOWN_EXTERNAL'a ekle)",
                      f"BROKEN COMMAND LINK: '/{c}' is mentioned but commands/{c}.md does not exist "
                      f"(if the plugin command was removed, update the links; if it is an "
                      f"in-game command, add it to KNOWN_EXTERNAL)"))
if not eksik_komut:
    notes.append(L(f"komut atiflari: {len(referred_cmds & cmd_names)} gecerli, kirik 0",
                   f"command links: {len(referred_cmds & cmd_names)} valid, 0 broken"))

# ---------- 6. ps1 BOM ----------
for f in sorted(os.listdir(script_dir)):
    if not f.endswith(".ps1"):
        continue
    p = os.path.join(script_dir, f)
    raw = open(p, "rb").read()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        raw.decode("ascii")
        non_ascii = False
    except UnicodeDecodeError:
        non_ascii = True
    if non_ascii and not has_bom:
        problems.append(L(f"BOM EKSIK ve ASCII disi karakter var: scripts/{f} "
                          f"(PowerShell 5.1 bozuk okur)",
                          f"MISSING BOM with non-ASCII characters: scripts/{f} "
                          f"(PowerShell 5.1 misreads it)"))
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

# ---------- 8. SAYAC TUTARLILIGI + YETIM BETIK ----------
# NEDEN: belgeye elle yazilan sayi kayar. Olculdu: veri katmani icin ayni anda
# uc farkli sayi yaziyordu (README 28 / README.tr 24 / help.md 24) ama gercek
# setup.py'nin len(KATMANLAR)'i = 27 idi. Sayiyi diskten uret, belgeyle karsilastir.
_belge = {}
for _f in ("README.md", os.path.join("docs", "README.tr.md")):
    if os.path.exists(os.path.join(A, _f)):
        _belge[_f] = read(os.path.join(A, _f))
_hepsi = "\n".join(_belge.values())

# 8a. veri katmani sayisi: kaynak setup.py'nin KENDI listesi (tahmin degil, import)
_katman = None
try:
    import importlib.util as _ilu
    _sp_yol = os.path.join(A, "scripts", "setup.py")
    _spec = _ilu.spec_from_file_location("_atlas_setup", _sp_yol)
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    _katman = len(_mod.KATMANLAR)
except Exception as _e:
    notes.append(L("katman sayisi okunamadi (setup.py import): %s" % _e,
                   "could not read the layer count (setup.py import): %s" % _e))
if _katman:
    # "2 veri katmani kurulu degil" gibi cikis-kodu satirlari iddia degildir
    _iddia = re.findall(r"(\d+)\s*(?:offline data layers|çevrimdışı veri katmanı|veri katmanı|data layers)(?!\s*(?:kurulu|not installed))", _hepsi)
    for _yaz in sorted(set(_iddia)):
        if int(_yaz) != _katman:
            problems.append(L("SAYAC KAYMASI: belgede '%s veri katmani' yaziyor, setup.py'de %d katman var" % (_yaz, _katman),
                              "COUNTER DRIFT: the docs say '%s data layers', setup.py has %d" % (_yaz, _katman)))
    for _f, _t in _belge.items():
        for _yaz in set(re.findall(r"N/(\d+)\s*katman", _t)):
            problems.append(L("SABIT KATMAN SAYISI: %s icinde 'N/%s' — sayiyi yazma, setup.py hesaplar" % (_f, _yaz),
                              "HARD-CODED LAYER COUNT: 'N/%s' in %s — do not write the number, setup.py computes it" % (_yaz, _f)))

# 8b. dal / yaprak / komut / betik sayaci
_disk = {
    "dal":    len([d for d in os.listdir(dallar_dir) if os.path.isdir(os.path.join(dallar_dir, d))]) if os.path.isdir(dallar_dir) else 0,
    "yaprak": sum(len([f for f in os.listdir(os.path.join(dallar_dir, d))
                       if f.endswith(".md") and f != "_dal.md"])
                  for d in os.listdir(dallar_dir) if os.path.isdir(os.path.join(dallar_dir, d))) if os.path.isdir(dallar_dir) else 0,
    "komut":  len([f for f in os.listdir(os.path.join(A, "commands")) if f.endswith(".md")]),
}
_ETIKET = {"dal": r"(\d+)\s*dal\b", "yaprak": r"(\d+)\s*yaprak\b", "komut": r"(\d+)\s*komut\b"}
_AD_EN = {"dal": "branches", "yaprak": "leaves", "komut": "commands"}
for _k, _rx in _ETIKET.items():
    for _yaz in set(re.findall(_rx, _hepsi)):
        if int(_yaz) != _disk[_k]:
            problems.append(L("SAYAC KAYMASI: belgede '%s %s' yaziyor, diskte %d var" % (_yaz, _k, _disk[_k]),
                              "COUNTER DRIFT: the docs say '%s %s', %d on disk" % (_yaz, _AD_EN[_k], _disk[_k])))

# 8c. yetim betik: belgede anilmiyor VE baska betikten cagrilmiyor
_sdir = os.path.join(A, "scripts")
_betikler = sorted(f for f in os.listdir(_sdir) if f.endswith((".py", ".ps1")))
_metin = _hepsi
for _r, _d, _fs in os.walk(FA):
    if ".git" in _r or os.sep + "_arsiv" in _r:
        continue
    for _f in _fs:
        if _f.endswith(".md"):
            _metin += read(os.path.join(_r, _f))
for _f in os.listdir(os.path.join(A, "commands")):
    _metin += read(os.path.join(A, "commands", _f))
_kod = {_s: read(os.path.join(_sdir, _s)) for _s in _betikler}
def _anilir(_s):
    _tab, _uz = os.path.splitext(_s)
    if _s in _metin or _tab in _metin:
        return True
    _parca = _tab.split("_")
    return any("_" + "_".join(_parca[_k:]) + _uz in _metin for _k in range(1, len(_parca)))
_yetim = []
for _s in _betikler:
    if _anilir(_s):
        continue
    _tab = os.path.splitext(_s)[0]
    if any(_o != _s and _tab in _c for _o, _c in _kod.items()):
        continue          # baska betikten cagriliyor -> ic yardimci, sorun degil
    _yetim.append(_s)
if _yetim:
    for _s in _yetim:
        notes.append(L("yetim betik: scripts/%s hicbir belgede anilmiyor ve hicbir betikten cagrilmiyor" % _s,
                       "orphan script: scripts/%s is not mentioned in any doc and not called by any script" % _s))
else:
    notes.append(L("yetim betik: 0 (%d betik tarandi)" % len(_betikler),
                   "orphan scripts: 0 (%d scripts scanned)" % len(_betikler)))

# ---------- rapor ----------
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
