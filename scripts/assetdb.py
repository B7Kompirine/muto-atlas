#!/usr/bin/env python3
"""assetdb.py — GTA V / FiveM archetype (prop, obje, kapi) veritabani sorgulama.

  assetdb.py show   <ad> [...]     archetype detayi + YORUM (kapi mi, pivot nerede)
  assetdb.py search <parca>        ada gore arama
  assetdb.py door   <ad> [...]     "bu obje kapi gibi acilir mi" karari
  assetdb.py stats                 indeks ozeti

Veri: data/archetypes.tsv.gz  (build_archetypes.ps1 uretir)

NEDEN VAR: bir prop/kapi ile ilgili kod yazmadan ONCE objenin ne oldugunu
bilmek gerekir. specialAttribute ve bbox, "kapi sistemi bu objeyi oynatir mi"
sorusunun tek dogru kaynagidir; native denemekle bulunmaz.
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import itertools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n import add_lang_arg, get_lang, set_lang, t  # noqa: E402

# Windows konsolu cp1252; UTF-8'e zorla yoksa ASCII disi karakterde cokuyor.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- CIKIS KODLARI -----------------------------------------------------------
# Tek bir "1" hem "aradigin ad yok" hem "veri dosyasi kurulu degil" hem de
# Python istisnasi anlamina geliyordu. Bir kapi (lint / CI) bu ucunu ayirt
# edemeyince VERI hatasi VARLIK hatasi diye raporlanir: katman eksik oldugu
# icin "0 sonuc" cikar, cagiran taraf "bu asset oyunda YOK" der ve tahmin
# uretir. Ev kurali: "aracin gostermemesi, o seyin yok oldugu anlamina gelmez."
EXIT_OK = 0        # bulundu
EXIT_NOTFOUND = 1  # sorgu calisti, ad otoritede yok
EXIT_NOLAYER = 2   # veri katmani kurulu degil -> sonuc HAKKINDA HICBIR SEY denemez
EXIT_INTERNAL = 3  # ic hata (istisna, harici arac coktu)


def die_layer(msg):
    """Katman kurulu degil -> EXIT_NOLAYER. 'Sonuc yok' ile karistirilmamali."""
    print(f"ERROR: {msg}", file=sys.stderr)
    print(f"  {t('layer_missing_hint')}", file=sys.stderr)
    sys.exit(EXIT_NOLAYER)


def die_internal(msg):
    """Harici arac/ortam hatasi -> EXIT_INTERNAL."""
    print(f"HATA: {msg}", file=sys.stderr)
    sys.exit(EXIT_INTERNAL)


HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
TSV = os.path.join(DATA, "archetypes.tsv.gz")
META = os.path.join(DATA, "assets.meta.json")
ENTDB = os.path.join(DATA, "entities.db")
ANIMS = os.path.join(DATA, "anims.tsv.gz")
CLIPS = os.path.join(DATA, "clips.tsv.gz")
PROPS = os.path.join(DATA, "props.tsv.gz")
SCENARIOS = os.path.join(DATA, "scenarios.tsv.gz")
SKELS = os.path.join(DATA, "skeletons.tsv.gz")
EXPRS = os.path.join(DATA, "expressions.tsv.gz")

# specialAttribute -> anlam.
#
# Iki katman var ve ikisi de gerekli:
#   * ETIKET  = Sollumz 2.9 kaynagindaki resmi motor adi
#               (ytyp/properties/ytyp.py:53, SpecialAttribute IntEnum)
#   * ACIKLAMA = 316k vanilla archetype uzerinde OLCULEN gercek kullanim
# Ornek: 2 motorda "Deprecated - Ladder" ama kullanan proplarin hepsi kule
# vinci -- vincin merdiveni. 15 motorda "Dynamic Cover Bound" ama proplar
# masa; masa siper verdigi icin. Motor adi NEDEN oyle davrandigini,
# olculen kullanim NEYIN oyle etiketlendigini soyler.
#
# Tam tablo + capraz dogrulama:
#   skills/fivem-assets/references/ytyp-ymap-bayraklari.md
SPECIAL = {
    0:  ("None", "Duz obje. Oyunun KAPI SISTEMI bu objeyi tanimaz."),
    1:  ("Deprecated - Unused", "Motorda hicbir sey yapmaz; eski dosyalarla "
         "uyumluluk icin duruyor. Kullananlar clutter/detay objeleri."),
    2:  ("Deprecated - Ladder", "Merdiven; artik Ladder extension kullanilir. "
         "Vanilla'da kullananlarin hepsi kule vinci (prop_towercrane_*)."),
    3:  ("Traffic Light", "Trafik isigi / lamba rigi."),
    4:  ("Unknown 4", "Sollumz de bilmiyor. Ornekler cit/kenar detayi."),
    5:  ("Garage Door", "Motor destekli buyuk kapi. Kapi sistemi calisir."),
    6:  ("MLO Water Level", "Motor adi bu ama 630 kullanicinin cogu sira disi: "
         "%84'u SLOD DEGIL, siradan kirsal harita parcasi (cs1_/ch1_/cs2_ "
         "onekli, 20 ytyp'e dagilmis, lodDist medyani 80). Ad ile kullanim "
         "ortusmuyor; ikisini de bil, tek basina karar verme."),
    7:  ("Normal Door", "Standart swing kapi. Kapi sistemi tam calisir."),
    8:  ("Sliding Door", "Yana kayar. Kapi sistemi calisir."),
    9:  ("Barrier Door", "Bariyer kapisi. Vanilla'da tek ornek "
         "(m26_1_prop_m61_sewer_gate) ve door physics bayragi YOK."),
    10: ("Sliding Vertical Door", "Dikey kepenk / asansor kapisi."),
    11: ("Bush", "Cali (motor icinde NOISY_BUSH)."),
    12: ("Rail Crossing Barrier Door", "Demiryolu bariyer kolu."),
    13: ("Deformable Bush", "Ezilebilen cali/ot."),
    14: ("Single Axis Rotation", "Tek eksende PROSEDUREL DONUS -- kapi DEGIL. "
         "Vanilla ornekleri cati fani (prop_roofvent_*)."),
    15: ("Dynamic Cover Bound", "Dinamik siper verir. Ornekler masa/klima."),
    16: ("Rumble On Vehicle Collision", "Arac carpinca sarsilir. Ornekler "
         "insaat bariyeri, palet."),
    17: ("Rail Crossing Light", "Demiryolu gecidi lambasi. Iki ornek "
         "(prop_traffic_rail_1a/_2) 'v_traffic_lights.ytyp' icinde -- yani "
         "trafik LAMBASI ytyp'i. Adi 'rail' diye yol korkulugu sanma."),
    30: ("Clock", "Akrepli saat -- motor kollari animasyonlu surer."),
    31: ("Deprecated - Tree", "Cift tarafli render bayragiyla ayni sey; "
         "artik o bayrak kullanilir. Ornekler sarmasik/yaprak."),
    32: ("Street Light", "Sokak lambasi. Vanilla'da HIC kullanilmiyor (0 adet)."),
}

# Kapi sisteminin (AddDoorToSystem) gercekten oynattigi tipler.
#
# OLCULDU, tahmin degil: 'Enable Door Physics' bayragi (ARCH_FLAG bit 26,
# deger 67108864) kurulu 1176 archetype'in specialAttribute dagilimi
#   7 -> 646   0 -> 379   5 -> 77   8 -> 71   10 -> 7   12 -> 2   4 -> 1
# 9 (Barrier Door) ve 14 (Single Axis Rotation) icin bu sayi SIFIR.
# 14 zaten kapi degil, prosedurel donus.
DOOR_CAPABLE = {5, 7, 8, 10, 12}

# UYARI: 379 archetype specialAttribute=0 oldugu halde door physics tasiyor.
# "Kapi mi" sorusu specialAttribute TEK BASINA cevaplanamaz; bayraga da bak.
ARCH_FLAG_DOOR_PHYSICS = 1 << 26


# ---------------------------------------------------------------------------
# BAYRAK TABLOLARI
# ---------------------------------------------------------------------------
# Kaynak: Sollumz 2.9 ytyp/properties/flags.py (ArchetypeFlags / EntityFlags).
#
# !! Sollumz ozellikleri flag1..flag32 diye adlandirir ama flag1 EN DUSUK
#    bittir: deger(flagN) = 2**(N-1). Dogrudan 1<<N yazmak tum tabloyu bir
#    bit kaydirir ve sessizce yanlis isim uretir.
#
# Capraz dogrulama (316.975 vanilla archetype): clipDictionary'si dolu 1308
# archetype'in 470'i 'Has Anim (YCD)', 838'i 'UV anims (YCD)' bitli;
# hicbir anim biti olmayan 0. Ters yonde de yanlis pozitif yok.
ARCH_FLAGS = [
    None, "Wet Road Reflection", "Dont Fade", "Draw Last", "Climbable By AI",
    "Suppress HD TXDs", "Static", "Disable alpha sorting", "Tough For Bullets",
    "Is Generic", "Has Anim (YCD)", "UV anims (YCD)", "Shadow Only",
    "Damage Model", "Dont Cast Shadows", "Cast Texture Shadows",
    "Dont Collide With Flyer", "Double-sided rendering", "Dynamic",
    "Override Physics Bounds", "Auto Start Anim",
    "Has Pre Reflected Water Proxy", "Has Drawable Proxy For Water Reflections",
    "Does Not Provide AI Cover", "Does Not Provide Player Cover",
    "Is Ladder Deprecated", "Has Cloth", "Enable Door Physics",
    "Is Fixed For Navigation", "Dont Avoid By Peds", "Use Ambient Scale",
    "Is Debug", "Has Alpha Shadow",
]

ENTITY_FLAGS = [
    None, "Allow full rotation", "Stream Low Priority",
    "Disable embedded collisions", "LOD in Parented YMAP", "LOD Adopt Me",
    "Static entity", "Interior LOD", "Unknown 8", "Unknown 9", "Unknown 10",
    "Unknown 11", "Unknown 12", "Unknown 13", "Unknown 14", "Unknown 15",
    # bit16 (65536): Sollumz "Unused" diyor, CodeWalker "Underwater".
    # OLCULDU -> CodeWalker hakli: 3.145.882 entity'de yalniz 14 kez kurulu
    # ve hepsi su prop'u (prop_dock_bouy_1/2/3, prop_rub_wheel_01), liman ve
    # nehir ymap'lerinde (po1_09_long_0, vb_rv_strm_1).
    "LOD Use Alt Fade", "Underwater", "Does Not Touch Water", "Does Not Spawn Peds",
    "Cast Static Shadows", "Cast Dynamic Shadows", "Ignore Day Night Settings",
    "Disable shadow for entity", "Disable entity, shadow casted",
    "Dont Render In Reflections", "Only Render In Reflections",
    "Dont Render In Water Reflections", "Only Render In Water Reflections",
    "Dont Render In Mirror Reflections", "Only Render In Mirror Reflections",
    "Unknown 31", "Unknown 32",
]


def decode_flags(value, table):
    """Bayrak tamsayisini isim listesine cevirir. flagN -> bit N-1."""
    try:
        value = int(value or 0)
    except (TypeError, ValueError):
        return []
    out = []
    for n in range(1, len(table)):
        if table[n] and value & (1 << (n - 1)):
            out.append(table[n])
    kalan = value & ~sum(1 << (n - 1) for n in range(1, len(table)) if table[n])
    if kalan:
        out.append(f"(cozulmeyen bit: {kalan})")
    return out

COLS = ["name", "hash", "src", "ytyp", "kind", "assetType", "specialAttribute",
        "flags", "lodDist", "bbMin", "bbMax", "bsRadius", "physicsDict",
        "textureDict", "clipDict"]


def rows():
    """TSV satirlarini dict olarak akitir."""
    if not os.path.exists(TSV):
        die_layer(f"{TSV} yok. Once build_archetypes.ps1 calistir.")
    with gzip.open(TSV, "rt", encoding="utf-8", errors="replace") as fh:
        header = fh.readline()  # baslik
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == len(COLS):
                yield dict(zip(COLS, parts))


def find(names):
    """Verilen adlari (kucuk harf) tek gecise bulur."""
    want = {n.lower() for n in names}
    hits = {}
    for r in rows():
        nl = r["name"].lower()
        if nl in want:
            hits.setdefault(nl, []).append(r)
            if len(hits) == len(want) and all(len(v) >= 1 for v in hits.values()):
                pass  # ayni ad birden fazla ytyp'te olabilir; taramaya devam
    return hits


def vec(s):
    try:
        return [float(x) for x in s.split(",")]
    except Exception:
        return [0.0, 0.0, 0.0]


def pivot_note(r):
    """bbox'tan mentese/pivot konumunu cikarir.

    Kapi modellerinde orijin genelde kapinin KENARINDADIR (mentese).
    Oyle ise SetEntityHeading ile dondurmek dogru gorunur; degilse obje
    kendi ortasinda doner ve yanlis gorunur.
    """
    mn, mx = vec(r["bbMin"]), vec(r["bbMax"])
    out = []
    for i, ax in enumerate("XYZ"):
        lo, hi, span = mn[i], mx[i], mx[i] - mn[i]
        if span < 0.05:
            continue
        # orijin bir kenara span'in %10'undan yakinsa: mentese orada
        if abs(lo) < span * 0.10:
            out.append(t("v_pivot_low", ax=ax, span=span))
        elif abs(hi) < span * 0.10:
            out.append(t("v_pivot_high", ax=ax, span=span))
    return out


def verdict(r):
    """Bu objeyi 'kapi gibi' actirmanin hangi yolla mumkun oldugunu soyler."""
    sa = int(r["specialAttribute"] or 0)
    frag = "FRAGMENT" in r["assetType"].upper()
    has_phys = bool(r["physicsDict"].strip())
    lines = []

    label, desc = SPECIAL.get(sa, (t("v_unknown", sa=sa), t("v_undef")))
    # specialAttribute aciklamasinin cevirisi varsa onu kullan; yoksa tablo.
    ceviri = t(f"sa_{sa}")
    if ceviri != f"sa_{sa}":
        desc = ceviri
    lines.append(f"specialAttribute={sa} -> {label}. {desc}")

    try:
        arch_flags = int(r["flags"] or 0)
    except (TypeError, ValueError):
        arch_flags = 0
    door_phys = bool(arch_flags & ARCH_FLAG_DOOR_PHYSICS)
    lines.append(f"{t('v_flag')}: {t('v_yes') if door_phys else t('v_no')}")

    if sa in DOOR_CAPABLE:
        lines.append(t("v_route_door"))
        if not door_phys:
            lines.append(t("v_warn_noflag"))
    elif door_phys:
        lines.append(t("v_route_flagonly"))
    else:
        lines.append(t("v_route_none"))
        piv = pivot_note(r)
        if piv:
            lines.append(t("v_pivot_edge"))
            lines.extend("       " + p for p in piv)
        else:
            lines.append(t("v_pivot_center"))
        lines.append(t("v_only_fix"))

    if not has_phys:
        lines.append(t("v_no_physics"))
    if frag:
        lines.append(t("v_fragment"))
    return lines


def fmt(r, with_verdict=True):
    out = [
        f"  {r['name']}   [{r['src']}]",
        f"    ytyp            {r['ytyp']}",
        f"    hash            {r['hash']}",
        f"    kind/assetType  {r['kind']} / {r['assetType']}",
        f"    specialAttr     {r['specialAttribute']}",
        f"    flags           {r['flags']}",
    ]
    bayraklar = decode_flags(r["flags"], ARCH_FLAGS)
    if bayraklar:
        out.append(f"                    -> {' | '.join(bayraklar)}")
    out += [
        f"    lodDist         {r['lodDist']}",
        f"    bbMin / bbMax   {r['bbMin']}  /  {r['bbMax']}",
        f"    physicsDict     {r['physicsDict'] or '(yok)'}",
        f"    textureDict     {r['textureDict'] or '(yok)'}",
        f"    clipDict        {r['clipDict'] or '(yok)'}",
    ]
    if with_verdict:
        out.append("    -- yorum --")
        out.extend("    " + l for l in verdict(r))
    return "\n".join(out)


def cmd_show(args):
    hits = find(args.names)
    eksik = 0
    for n in args.names:
        rs = hits.get(n.lower())
        if not rs:
            print(f"\n[{n}] BULUNAMADI. `assetdb.py search {n}` dene.")
            eksik += 1
            continue
        print(f"\n=== {n} ===")
        for r in rs:
            print(fmt(r, with_verdict=not args.raw))
    return EXIT_NOTFOUND if eksik else EXIT_OK


def cmd_door(args):
    hits = find(args.names)
    eksik = 0
    for n in args.names:
        rs = hits.get(n.lower())
        if not rs:
            print(f"{n}: BULUNAMADI")
            eksik += 1
            continue
        r = rs[0]
        sa = int(r["specialAttribute"] or 0)
        ok = t("door_yes") if sa in DOOR_CAPABLE else t("door_no")
        print(f"\n{n}  ->  {t('door_q')}: {ok}")
        for l in verdict(r):
            print("   " + l)
    return EXIT_NOTFOUND if eksik else EXIT_OK


def cmd_search(args):
    q = args.query.lower()
    seen, n = set(), 0
    for r in rows():
        if q in r["name"].lower():
            key = (r["name"], r["ytyp"])
            if key in seen:
                continue
            seen.add(key)
            n += 1
            if n <= args.limit:
                print(f"  {r['name']:<40} specialAttr={r['specialAttribute']:<3} "
                      f"{r['assetType']:<22} [{r['src']}] {r['ytyp']}")
    extra = n - args.limit
    print("\n" + t("results", n=n)
          + (t("hidden", n=extra) if extra > 0 else ""))
    return EXIT_NOTFOUND if n == 0 else EXIT_OK


def ent_con():
    """Dunya konumu veritabanina baglanir."""
    import sqlite3
    if not os.path.exists(ENTDB):
        die_layer("entities.db yok. Once:\n"
                  "  powershell -File build_entities.ps1\n"
                  "  python build_entities_db.py")
    return sqlite3.connect(f"file:{ENTDB}?mode=ro", uri=True)


def cmd_where(args):
    """Bir archetype'in dunyadaki tum yerlesimleri.

    'root' = ymap'e dogrudan yerlestirilmis. 'mlo' = bir ic mekanin (MLO)
    parcasi; konum MLO'nun dunya yerlesimiyle hesaplandi.
    """
    con = ent_con()
    eksik = 0
    for name in args.names:
        print(f"\n=== {name} ===")

        # Once ad -> id (names kucuk tablo). Sonra ent'i nid indeksiyle sorgula;
        # ent uzerinde COLLATE NOCASE ile join yapmak 3M satiri taratiyor.
        row = con.execute("SELECT id FROM names WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
        if not row:
            print("  dunyada yerlesimi yok (sadece archetype olarak tanimli,"
                  " ya da LOD filtresine takildi).")
            eksik += 1
            continue

        rows_ = con.execute(
            "SELECT e.x, e.y, e.z, e.kind, ny.name, ni.name "
            "FROM ent e JOIN names ny ON ny.id = e.ymid "
            "LEFT JOIN names ni ON ni.id = e.iid "
            "WHERE e.nid = ?", (row[0],)).fetchall()

        # Ayni konum birden fazla ymap'te gorunur (DLC varyantlari ayni ic
        # mekani yeniden yerlestirir). Konuma gore tekille, kaynaklari say.
        groups = {}
        for x, y, z, kind, ymap, interior in rows_:
            key = (round(x, 2), round(y, 2), round(z, 2))
            g = groups.setdefault(key, {"kind": kind, "interior": interior, "ymaps": set()})
            g["ymaps"].add(ymap)

        for (x, y, z), g in sorted(groups.items())[:args.limit]:
            k = "mlo " if g["kind"] == 1 else "root"
            loc = f"  ic mekan: {g['interior']}" if g["interior"] else ""
            dup = f"  ({len(g['ymaps'])} ymap)" if len(g["ymaps"]) > 1 else ""
            print(f"  [{k}] vec3({x:.4f}, {y:.4f}, {z:.4f}){loc}{dup}")

        extra = len(groups) - args.limit
        print(f"  -> {len(groups)} benzersiz konum ({len(rows_)} kayit)"
              + (f", {extra} gosterilmedi" if extra > 0 else ""))
        if not groups:
            eksik += 1
    con.close()
    return EXIT_NOTFOUND if eksik else EXIT_OK


def cmd_near(args):
    """Bir noktanin cevresindeki entity'ler. Koordinat elde varken ne var diye bakmak icin."""
    con = ent_con()
    x, y, z, r = args.x, args.y, args.z, args.radius
    sql = ("SELECT n.name, e.x, e.y, e.z, e.kind, ni.name "
           "FROM ent e JOIN names n ON n.id = e.nid "
           "LEFT JOIN names ni ON ni.id = e.iid "
           "WHERE e.x BETWEEN ? AND ? AND e.y BETWEEN ? AND ? AND e.z BETWEEN ? AND ?")
    params = [x - r, x + r, y - r, y + r, z - r, z + r]
    if args.filter:
        sql += " AND n.name LIKE ?"
        params.append(f"%{args.filter}%")

    # Ayni obje birden fazla ymap'te (DLC varyanti) gorunur; ad+konuma gore tekille.
    seen = {}
    for nm, ex, ey, ez, kind, interior in con.execute(sql, params):
        d = ((ex - x) ** 2 + (ey - y) ** 2 + (ez - z) ** 2) ** 0.5
        if d > r:
            continue
        key = (nm.lower(), round(ex, 2), round(ey, 2), round(ez, 2))
        if key not in seen:
            seen[key] = (d, nm, ex, ey, ez, kind, interior)
    con.close()

    hits = sorted(seen.values(), key=lambda t: t[0])
    for d, nm, ex, ey, ez, kind, interior in hits[:args.limit]:
        k = "mlo " if kind == 1 else "root"
        loc = f"  [{interior}]" if interior else ""
        print(f"  {d:6.2f}m  [{k}] {nm:<38} vec3({ex:.4f}, {ey:.4f}, {ez:.4f}){loc}")
    extra = len(hits) - args.limit
    print(f"\n{len(hits)} entity {r}m icinde" + (f" ({extra} gosterilmedi)" if extra > 0 else ""))


def gz_lines(path, what, header=False):
    """Gzip TSV satirlarini akitir. header=True ise ilk satiri (baslik) atlar.

    clips/skeletons/expressions basliklidir; anims/props/scenarios degildir.
    Baslik atlanmazsa sorgu sonuclarina 'dict  clip  type...' diye sahte bir
    satir karisiyor.
    """
    if not os.path.exists(path):
        die_layer(f"{path} yok. Once ilgili build betigini calistir ({what}).")
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        if header:
            fh.readline()
        for line in fh:
            line = line.rstrip("\n")
            if line:
                yield line


CLIP_COLS = ["dict", "clip", "type", "animCount", "duration", "rootMotion", "bones"]


def clip_rows():
    """clips.tsv.gz satirlari (ycd'den cikarilmis: sure + iz sayisi ile)."""
    for line in gz_lines(CLIPS, "klipler", header=True):
        p = line.split("\t")
        if len(p) == len(CLIP_COLS):
            yield dict(zip(CLIP_COLS, p))


def clip_line(r, width=40):
    dur = float(r["duration"] or 0)
    kind = "cok-izli" if r["type"] == "animlist" else "tek-iz "
    rm = " root-motion" if r["rootMotion"] == "1" else ""
    bones = r.get("bones") or "?"
    return f"  {r['clip']:<{width}} {dur:7.3f}s  {kind} iz={r['animCount']} {t('ped_bones')}={bones}{rm}"


def anim_yedek(q, dict_only, limit):
    """clips.tsv.gz (AGIR katman) yoksa anims.tsv.gz'ye dus.

    ⛔ Kullanicinin verisi VARKEN "katman yok" demek, aracin en buyuk kusuru
    olur: GTA V kurulumu olmayan biri 269.414 animasyon adina sahiptir ama
    sure/kemik bilgisine sahip degildir. Tamamen reddetmek yerine ELDEKINI
    ver ve neyin eksik oldugunu SOYLE.
    """
    n = 0
    for line in gz_lines(ANIMS, "animasyon adlari"):
        p_ = line.split("\t")
        if len(p_) != 2:
            continue
        d, c = p_
        hay = d.lower() if dict_only else f"{d}\t{c}".lower()
        if q not in hay:
            continue
        n += 1
        if n <= limit:
            print(f"  {d:<46} {c}")
    extra = n - limit
    print("\n" + t("results", n=n)
          + (t("hidden", n=extra) if extra > 0 else ""))
    print(f"{t('note')}: {t('anim_no_clips')}")
    print("       powershell -File scripts/build_clips.ps1")
    return EXIT_NOTFOUND if not n else EXIT_OK


def cmd_anim(args):
    """Animasyon arama. Sure ve iz sayisi .ycd'den gelir.

    FiveM'de bir animasyon oynatmak icin HEM dictionary HEM clip adi gerekir
    (RequestAnimDict + TaskPlayAnim).
    """
    q = args.query.lower()

    # Agir katman yoksa hafif katmana dus (bkz. anim_yedek).
    if not os.path.exists(CLIPS):
        if args.dict:
            print("clips.tsv.gz kurulu degil; --dict sure gruplamasi yapilamaz.")
            print("Ad aramasi icin --dict olmadan calistir.")
            return EXIT_NOLAYER
        return anim_yedek(q, args.dict_only, args.limit)

    # --dict: tek bir sozlugun icini dok ve SURELERE GORE GRUPLA.
    # Ayni sozlukte ayni sureye sahip klipler senkron oynatilmak uzere
    # yazilmistir: biri ped, digeri prop. Prop animasyonu ararken bakilacak yer.
    if args.dict:
        rows_ = [r for r in clip_rows() if r["dict"].lower() == q]
        if not rows_:
            print(f"'{args.query}' adinda dictionary yok. `anim {args.query} --dict-only` ile ara.")
            return EXIT_NOTFOUND
        groups = {}
        for r in rows_:
            groups.setdefault(round(float(r["duration"] or 0), 3), []).append(r)

        print(f"=== {args.query} ===  {len(rows_)} klip")
        for dur, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            # Ayni sure + FARKLI iskelet = ped ve prop ayni sahnede.
            # Sadece ayni sure yeterli degil: _female/_suit varyantlari da
            # ayni suredir ama hepsi ayni iskelet (ped).
            skels = {r.get("bones", "") for r in rs}
            pair = len(rs) > 1 and len(skels) > 1 and dur > 0
            tag = "  <-- ayni sure, FARKLI iskelet: ped + prop cifti" if pair else ""
            print(f"\n  [{dur:.3f}s]{tag}")
            for r in sorted(rs, key=lambda x: x["clip"])[:args.limit]:
                print("  " + clip_line(r))
        print("\nSenkron oynatma: NetworkCreateSynchronisedScene + TaskSynchronizedScene (ped)")
        print("                 + PlaySynchronizedEntityAnim / NetworkAddEntityToSynchronisedScene (prop)")
        return

    n = 0
    for r in clip_rows():
        hay = r["dict"].lower() if args.dict_only else f"{r['dict']}\t{r['clip']}".lower()
        if q not in hay:
            continue
        n += 1
        if n <= args.limit:
            print(f"  {r['dict']:<42}{clip_line(r, width=34)}")
    extra = n - args.limit
    print("\n" + t("results", n=n)
          + (t("hidden", n=extra) if extra > 0 else ""))
    if not n:
        return EXIT_NOTFOUND
    if n:
        print("Kullanim: RequestAnimDict('<dict>') -> HasAnimDictLoaded -> TaskPlayAnim(ped,'<dict>','<clip>',...)")
        print("Ipucu:    bir sozlugun icini sure gruplariyla gormek icin  anim <dict> --dict")


SKEL_COLS = ["model", "src", "boneCount", "boneIndex", "boneName", "boneTag", "parentIndex"]


def cmd_bones(args):
    """Bir modelin iskeleti: kemik adi + TAG.

    Prop'u animasyonla oynatmak, bir seye takmak veya kemigine offset vermek
    icin kemik ADI (GetEntityBoneIndexByName) ya da TAG'i gerekir. Iskeleti
    olmayan prop'ta bunlarin hicbiri calismaz — bu komut once onu soyler.
    """
    q = {n.lower() for n in args.names}

    # skeletons.tsv.gz ayni modeli birden fazla RPF/DLC KOPYASINDAN indeksler;
    # her kopya kendi kemiklerini indeks 0'dan itibaren sirayla yazar. Yani
    # satirlar tekrar eder (olculdu: w_ar_assaultrifle 64 satir, 16 kemik,
    # tam 4 kopya) — tekillestirilmezse liste cogalir ve --limit tasmasi
    # yanlis hesaplanir.
    #
    # Kopyayi indeks sifirlanmasindan ayirmak sart: 289 modelde kopyalar
    # GERCEKTEN farklidir (base vs DLC iskeleti). Ustelik fark her zaman
    # boneCount'a yansimaz — 'adder' iki ayri 63 kemikli iskelete sahiptir
    # (birinde fazladan 'extra_1' var, sonraki tum indeksler kayar). Satir
    # kumesi olarak birlestirilirse 63 kemik basligi altinda 76 kemik basilir.
    # Butun dosyada dogrulandi: 72.364 kopya, hepsinin uzunlugu kendi
    # boneCount'una esit ve indeksleri 0..n-1 kesintisiz.
    found, cur, prev = {}, None, -1
    for line in gz_lines(SKELS, "iskeletler", header=True):
        p = line.split("\t")
        if len(p) != len(SKEL_COLS):
            continue
        r = dict(zip(SKEL_COLS, p))
        key, idx = r["model"].lower(), int(r["boneIndex"])
        if key != cur or idx <= prev:      # yeni kopya basladi
            cur = key
            if key in q:
                found.setdefault(key, []).append([])
        prev = idx
        if key in q:
            found[key][-1].append(r)

    eksik = 0
    for n in args.names:
        copies = found.get(n.lower())
        print(f"\n=== {n} ===")
        if not copies:
            print(t("bones_none"))
            print(t("bones_none_hint"))
            eksik += 1
            continue

        # Ayni iskeletin kopyalarini ele, gercekten farkli surumleri tut.
        seen, variants = set(), []
        for c in copies:
            sig = tuple((r["boneIndex"], r["boneName"], r["boneTag"]) for r in c)
            if sig in seen:
                continue
            seen.add(sig)
            variants.append(c)
        variants.sort(key=len, reverse=True)   # zengin (yeni/DLC) surum once

        if len(variants) > 1:
            counts = " / ".join(t("bones_n", n=len(v)) for v in variants)
            print(f"  DIKKAT: bu model {len(variants)} farkli iskelet surumuyle")
            print(f"  indekslenmis ({counts}) — kemik INDEKSLERI surumler")
            print("  arasinda kayar, TAG'ler kaymaz. Indeks yerine tag ile baglan.")
            # Ayrisma noktasini soyle: kemik sayilari esit olabiliyor
            # ('adder' iki kez 63, ayni kemikler farkli indeks sirasiyla) ve
            # ilk kemikler ayni oldugu icin surumler ekranda sebepsiz tekrar
            # gibi gorunur.
            key = lambda r: (r["boneName"], r["boneTag"])
            sets = [{key(r) for r in v} for v in variants]
            at = min(
                next((i for i in range(min(len(variants[0]), len(o)))
                      if key(variants[0][i]) != key(o[i])), min(len(variants[0]), len(o)))
                for o in variants[1:])
            excl = [s.difference(*(sets[:i] + sets[i + 1:])) for i, s in enumerate(sets)]
            if any(excl):
                which = "; ".join(
                    f"surum {i + 1}: {', '.join(sorted(n for n, _ in e))}"
                    for i, e in enumerate(excl) if e)
                print(f"  Ilk ayrisma: #{at} — sadece o surumde olan kemikler -> {which}")
            else:
                print(f"  Ilk ayrisma: #{at} — kemik kadrosu AYNI, degisen sadece indeks sirasi.")

        for v in variants:
            head = f"  {v[0]['src']} · " + t("bones_n", n=len(v))
            print(head if len(variants) == 1 else head + "  (surum)")
            for r in v[:args.limit]:
                par = r["parentIndex"]
                par = "-" if par == "-1" else par
                print(f"    #{r['boneIndex']:<4} {r['boneName']:<32} tag={r['boneTag']:<6} parent={par}")
            extra = len(v) - args.limit
            if extra > 0:
                print("    " + t("bones_more", n=extra))
    return EXIT_NOTFOUND if eksik else EXIT_OK


def cmd_clipfit(args):
    """Bir klibi HANGI MODEL oynatabilir — kemik tag eslesmesiyle.

    Klip kac kemik animasyonluyor bilmek yetmez; hangi kemik TAG'lerini
    hedefledigi gerekir. O tag seti modeli tek basina belirler.
    Ornek: bank_vault_door_opens -> tag {0,10596,50607} -> tek model:
    hei_prop_heist_sec_door (haritadaki kasa kapisinin animasyonlu ikizi).
    """
    import subprocess

    ps = os.path.join(HERE, "clip_bones.ps1")
    if not os.path.exists(ps):
        die_internal(f"{ps} yok.")

    try:
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", ps, "-Dict", args.dict, "-Clip", args.clip, "-Json"],
            capture_output=True, text=True, timeout=900).stdout
    except Exception as e:
        die_internal(f"clip_bones.ps1 calistirilamadi: {e}")

    line = next((l for l in out.splitlines() if l.strip().startswith("{")), None)
    if not line:
        die_internal(f"kemik tag'i cikarilamadi.\n{out.strip()[:400]}")
    data = json.loads(line)
    if "error" in data:
        print(f"BULUNAMADI: {args.dict} / {args.clip}", file=sys.stderr)
        sys.exit(EXIT_NOTFOUND)

    want = set(data["tags"])
    print(f"=== {args.dict} / {args.clip} ===")
    print(f"  hedefledigi kemik tag'leri ({len(want)}): {sorted(want)}\n")

    # Sadece kok kemik (tag 0) hedefleniyorsa klip objeyi TEK PARCA olarak
    # oynatiyor demektir. Bu durumda tag seti model belirlemez — her prop
    # oynatabilir. 52k modeli listelemek yerine bunu soylemek gerekir.
    if want == {0}:
        print("  Bu klip SADECE kok kemigi (tag 0) hareket ettiriyor.")
        print("  Yani objeyi tek parca olarak tasiyor/donduruyor; ic parcasi oynamiyor.")
        print("  SONUC: model tag'lerden belirlenemez — kok kemigi olan HER prop")
        print("  bu klibi oynatabilir. Dogru prop'u ad ve sure eslesmesinden bul:")
        print(f"    assetdb.py anim {args.dict} --dict")
        return

    # Not: SKELS ayni modeli birden fazla kopyadan indeksler (bkz. cmd_bones).
    # Tag'ler SET'e girdigi icin tekrar eden satirlar skoru sismez; ama
    # boneCount kopyalar arasinda farkli olabilir (base vs DLC) — dosya
    # sirasina gore degil, zengin surume gore sabitle.
    mtags, mcount, msrc = {}, {}, {}
    for line_ in gz_lines(SKELS, "iskeletler", header=True):
        p = line_.split("\t")
        if len(p) != len(SKEL_COLS):
            continue
        mtags.setdefault(p[0], set()).add(int(p[5]))
        mcount[p[0]] = max(int(p[2]), mcount.get(p[0], 0))
        msrc[p[0]] = p[1]

    scored = []
    for m, tags in mtags.items():
        hit = len(want & tags)
        if hit:
            scored.append((hit, -mcount[m], m))
    scored.sort(reverse=True)

    full = [s for s in scored if s[0] == len(want)]
    if full:
        # Cok fazla tam eslesme = tag seti ayirt edici degil (genelde
        # yaygin/paylasilan kemik tag'leri). Liste dokmek yaniltir.
        if len(full) > 50:
            print(f"  {len(full)} model tam esliyor -> bu tag seti AYIRT EDICI DEGIL.")
            print("  (yaygin/paylasilan kemik tag'leri; model bundan belirlenemez)")
            print(f"  Ad ve sure eslesmesine bak:  assetdb.py anim {args.dict} --dict")
            return

        print(f"  TAM ESLESME ({len(full)} model):")
        for hit, _, m in full[:args.limit]:
            print(f"    {m:<44} {mcount[m]} kemik  [{msrc[m]}]")
        if len(full) == 1:
            print("\n  Tek aday -> klip bu modelde oynatilmak uzere yapilmis.")
            print(f"  Kullanim: PlayEntityAnim(obj, '{args.clip}', '{args.dict}', ...)")
    else:
        print("  Tam eslesen model YOK. En yakinlar:")
        for hit, _, m in scored[:args.limit]:
            print(f"    {m:<44} {hit}/{len(want)} tag  {mcount[m]} kemik")
        print("\n  Not: klip ped iskeletini hedefliyor olabilir (ped animasyonu),")
        print("  ya da modeli bu indekste olmayan bir DLC/custom asset olabilir.")
        return EXIT_NOTFOUND


def cmd_expr(args):
    """Expression (.yed) arama — prosedurel kemik hareketi / yay / carpisma tepkisi."""
    q = args.query.lower()
    n = 0
    for line in gz_lines(EXPRS, "expression'lar", header=True):
        p = line.split("\t")
        if len(p) != 6:
            continue
        yed, name, h, streams, tracks, springs = p
        if q not in f"{yed}\t{name}".lower():
            continue
        n += 1
        if n <= args.limit:
            sp = f"  yay={springs}" if springs != "0" else ""
            print(f"  {yed:<34} {name:<34} iz={tracks:<4} stream={streams}{sp}")
    extra = n - args.limit
    print("\n" + t("results", n=n)
          + (t("hidden", n=extra) if extra > 0 else ""))
    if n:
        print("Not: yay (spring) sayisi > 0 olan expression'lar fiziksel tepki uretir")
        print("     (carpisma/hareketle sallanan kemikler). SetEntityAnimSpeed vb. ile")
        print("     degil, modelin expression'i uzerinden calisir.")
    return EXIT_NOTFOUND if n == 0 else EXIT_OK


def cmd_prop(args):
    q = args.query.lower()
    n = 0
    for name in gz_lines(PROPS, "proplar"):
        if q in name.lower():
            n += 1
            if n <= args.limit:
                print(f"  {name}")
    extra = n - args.limit
    print("\n" + t("results", n=n)
          + (t("hidden", n=extra) if extra > 0 else ""))
    if n:
        print("Not: bu liste CREATE_OBJECT ile spawn edilebilen proplar.")
        print("     Objenin kapi/fizik ozelligi icin: assetdb.py show <ad>")
    return EXIT_NOTFOUND if n == 0 else EXIT_OK


def cmd_scenario(args):
    q = args.query.lower()
    hits = [s for s in gz_lines(SCENARIOS, "senaryolar") if q in s.lower()]
    for s in hits[:args.limit]:
        print(f"  {s}")
    print("\n" + t("results", n=len(hits)))
    return EXIT_NOTFOUND if not hits else EXIT_OK


def cmd_propanim(args):
    """Bir PROP'un GERCEK animasyonlarini bul.

    NEDEN BU YOL: "ayni sure + farkli kemik sayisi" sezgisi ped+prop ciftini
    tahmin eder; kesin degildir. Olculdu: senkron sahne kliplerinde KLIP ADI
    dogrudan PROP MODEL ADIdir (`prop_cs_walking_stick-3`, `v_ilev_store_door-0`
    -> `-N` sahne dilimi eki). 312.748 klip prop veritabaniyla eslendiginde
    1407 prop / 53.181 gercek prop animasyonu cikti.
    """
    import collections
    q = args.query.lower()
    props = set()
    for name in gz_lines(PROPS, "proplar"):
        props.add(name.lower())

    want = {p for p in props if q in p} if q else props
    if not want:
        print(f"[!] '{args.query}' prop veritabaninda yok. "
              f"Once: assetdb.py prop {args.query}")
        return EXIT_NOTFOUND

    hits = collections.defaultdict(list)
    with gzip.open(CLIPS, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 7:
                continue
            c = f[1].lower()
            base = c.rsplit("-", 1)[0] if ("-" in c and c.rsplit("-", 1)[1].isdigit()) else c
            if base in want:
                hits[base].append((f[0], f[1], f[4], f[6]))

    if not hits:
        print(f"[=] '{args.query}' ile eslesen prop bulundu ama HIC animasyonu yok.")
        print("    Prop'un kemigi/animasyonu yoksa PlayEntityAnim calismaz.")
        return EXIT_NOTFOUND

    for p in sorted(hits, key=lambda k: -len(hits[k]))[:args.limit]:
        v = hits[p]
        print(f"\n=== {p}   ({len(v)} klip)")
        seen = set()
        for d, c, dur, b in v:
            if d in seen:
                continue
            seen.add(d)
            print(f"    {d:<46} {c:<30} {dur:>9}s  kanal={b}")
            if len(seen) >= args.dicts:
                rest = len({x[0] for x in v}) - len(seen)
                if rest > 0:
                    print(f"    ... {rest} dict daha")
                break
    print(f"\n{len(hits)} prop, {sum(len(v) for v in hits.values())} klip")
    print("Kullanim: ped klibi ve prop klibi AYNI dict icinde, AYNI sure ile")
    print("          senkron oynatilir (bkz. SKILL.md senkron sahne bolumu).")


FXTYPE = {
    0: "Ambient",  1: "Collision", 2: "Shot",    3: "Break",
    4: "Destroy",  5: "Animation (Unused)", 6: "RayFire", 7: "In Water",
}

EXT_TSV = os.path.join(DATA, "ytyp_extensions.tsv.gz")

EXT_COLS = ["archetype", "src", "ytyp", "extType", "extName", "offsetPos",
            "fxName", "fxType", "boneTag", "scale", "probability",
            "extFlags", "detay"]


def ext_rows():
    """ytyp extension satirlarini dolasir. Indeks yoksa anlamli hata verir."""
    if not os.path.exists(EXT_TSV):
        die_layer(
            f"{EXT_TSV} yok.\n"
            "  Uret: powershell -NoProfile -ExecutionPolicy Bypass "
            "-File scripts/build_extensions.ps1"
        )
    with gzip.open(EXT_TSV, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()  # baslik
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == len(EXT_COLS):
                yield dict(zip(EXT_COLS, parts))


PTFXTSV = os.path.join(DATA, "ptfx_effects.tsv.gz")


def ptfx_katalog():
    """Gercek efekt katalogu (.ypt dosyalarindan). ad -> (emitter, ypt listesi).

    2549 benzersiz efekt / 368 ypt. Bu olmadan 'fxName dogru mu' sorusu
    cevaplanamaz -- ve yanlis fxName SESSIZ hatadir: efekt hic cikmaz,
    uyari da verilmez.
    """
    if not os.path.exists(PTFXTSV):
        return {}
    out = {}
    with gzip.open(PTFXTSV, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) == 3:
                out[p[0].lower()] = (p[0], p[1], p[2])
    return out


def cmd_fx(args):
    """Partikul efekt katalogu: 'boyle bir efekt var mi, hangi ypt icinde'."""
    kat = ptfx_katalog()
    if not kat:
        die_layer(f"{PTFXTSV} yok.\n  Uret: powershell -NoProfile "
                  "-ExecutionPolicy Bypass -File scripts/build_ptfx.ps1")

    q = (args.query or "").lower()
    if args.exact:
        # ytyp'teki fxName ile .ypt'deki efekt adi AYNI DEGIL: olculdu,
        # 406 fxName'in yalniz 3'u aynen var, 265'i (%65,3) 'ent_' oneki
        # gerektiriyor. Once oldugu gibi, sonra onekli dene.
        r = kat.get(q) or kat.get("ent_" + q)
        if r and not kat.get(q):
            print(f"\n  NOT: ytyp'te '{args.query}' yaziliyor ama .ypt'deki "
                  f"gercek ad '{r[0]}'.")
            print("       Motor 'ent_' onekini kendisi ekliyor "
                  "(406 fxName'in %65,3'unde boyle).")
        if not r:
            # 'ent_<ad>' ILE BASLAYAN varsa ad sonek de almis demektir.
            # Olculdu: 406 fxName'in 9'u boyle (orn. amb_butterflys ->
            # ent_amb_butterflys_swarm).
            onekli = "ent_" + q
            sonekli = sorted(v[0] for k, v in kat.items() if k.startswith(onekli))
            if sonekli:
                print(f"\n'{args.query}' aynen yok ama SONEK almis hali var:")
                for y in sonekli[:6]:
                    print(f"    {y}")
                print("\n  ytyp adi ile .ypt adi arasinda hem onek hem sonek farki")
                print("  olabiliyor. Hangisini istediginden emin ol.")
                return 1

            print(f"\n'{args.query}' diye bir efekt YOK ({len(kat)} efekt tarandi;")
            print("  'ent_' oneki ve sonekli halleri de denendi).")
            yakin = [v[0] for k, v in kat.items() if q[:6] and q[:6] in k][:8]
            if yakin:
                print("  bunu mu demek istedin:")
                for y in yakin:
                    print(f"    {y}")
            print("\n  !! Yanlis fxName SESSIZ hatadir: efekt hic cikmaz, uyari yok.")
            print("  !! AMA 'yok' demek her zaman senin hatan demek DEGIL.")
            print("     OLCULDU: 406 vanilla fxName'in 129'unun (%31,8) hicbir")
            print("     .ypt'de akrabasi bile yok -- orn. 'amb_water_roof_drips_short'")
            print("     5621 kez kullanildigi halde. Indeks eksik DEGIL: core.ypt'nin")
            print("     XML'i ile karsilastirildi, 895/895 efekt yakalanmis.")
            print("     Yani bunlar vanilla'nin kendi BOSTA REFERANSLARI.")
            print("     Bir vanilla ytyp'i kopyalayip efektini devraldiysan,")
            print("     o efekt zaten calismiyor olabilir.")
            return 1
        ad, em, ypts = r
        print(f"\n=== {ad} ===")
        print(f"  event emitter : {em}")
        print(f"  bulundugu ypt : {ypts.replace(';', ', ')}")
        kul = [x for x in ext_rows()
               if x["extType"] == "Particle" and x["fxName"].lower() == q]
        print(f"  ytyp kullanimi: {len(kul)} prop")
        for x in kul[:6]:
            print(f"     {x['archetype']:<34} fxType={x['fxType']} scale={x['scale']}")
        return 0

    bulunan = [v for k, v in kat.items() if not q or q in k]
    if not bulunan:
        print(f"'{args.query}' ile eslesen efekt yok.")
        return 1
    bulunan.sort(key=lambda v: v[0])
    print(f"\n{len(bulunan)} efekt" + (f" ('{args.query}' iceren)" if q else
                                       f" / {len(kat)} toplam") + "\n")
    for ad, em, ypts in bulunan[: args.limit]:
        ilk = ypts.split(";")[0]
        print(f"  {ad:<40} emitter={em:<3} {ilk}")
    if len(bulunan) > args.limit:
        print(f"\n  ... {len(bulunan)-args.limit} tane daha (--limit)")
    print("\n  Tek efektin ayrintisi: assetdb.py fx <tam_ad> --exact")
    return 0


def cmd_ptfx(args):
    """Partikul extension'i arar: prop adina, efekt adina veya fxType'a gore.

    Partikul YTYP'te yasar, script'te degil. 'Bu prop kirilinca toz cikarsin'
    isteginin cevabi bir native degil, archetype'a eklenen
    CExtensionDefParticleEffect'tir.
    """
    q = (args.query or "").lower()
    tip = args.type
    bulunan, gorulen_fx = [], collections.Counter()

    for row in ext_rows():
        if row["extType"] != "Particle":
            continue
        if tip is not None and (row["fxType"] or "0") != str(tip):
            continue
        if q and q not in row["archetype"].lower() and q not in row["fxName"].lower():
            continue
        bulunan.append(row)
        gorulen_fx[row["fxName"]] += 1

    if not bulunan:
        print("eslesen partikul yok.")
        return 1

    print(f"\n{len(bulunan)} partikul extension, {len(gorulen_fx)} farkli efekt\n")
    for row in bulunan[: args.limit]:
        ft = int(row["fxType"] or 0)
        bone = int(row["boneTag"] or 0)
        bone_s = "TUM kemikler" if bone == -1 else f"tag {bone}"
        print(f"  {row['archetype']:<38} {row['fxName']}")
        print(f"      fxType={ft} ({FXTYPE.get(ft, '?')})  {bone_s}  "
              f"scale={row['scale']}  olasilik=%{row['probability']}")
        if row["offsetPos"] not in ("", "0,0,0"):
            print(f"      offset {row['offsetPos']}")
    if len(bulunan) > args.limit:
        print(f"\n  ... {len(bulunan) - args.limit} satir daha (--limit ile arttir)")

    if len(gorulen_fx) > 1:
        print("\n  en sik efektler:")
        for ad, n in gorulen_fx.most_common(8):
            print(f"    {ad:<34} {n}")
    return 0


def cmd_ext(args):
    """Bir archetype'in TUM extension'lari (14 tip)."""
    ad = args.name.lower()
    satirlar = [r for r in ext_rows() if ad in r["archetype"].lower()]
    if not satirlar:
        print(f"'{args.name}' icin extension yok.")
        print("  NOT: archetype'larin cogunda hic extension olmaz -- bu normal.")
        return 1

    for arch, grup in itertools.groupby(
            sorted(satirlar, key=lambda r: r["archetype"]), key=lambda r: r["archetype"]):
        grup = list(grup)
        print(f"\n{arch}   [{grup[0]['src']}]  {grup[0]['ytyp']}")
        for r in grup:
            t = r["extType"]
            if t == "Particle":
                ft = int(r["fxType"] or 0)
                print(f"   Particle       {r['fxName']}  fxType={ft} ({FXTYPE.get(ft,'?')})"
                      f"  scale={r['scale']} %{r['probability']}")
            elif t == "Expression":
                print(f"   Expression     {r['detay']}")
                print("                  -> .yed zinciri: exprDict CIPLAK ADdir "
                      "(pack:/x.expr DEGIL)")
            elif t == "ProcObject":
                print(f"   ProcObject     {r['detay']}")
            else:
                print(f"   {t:<14} {r['extName']}")
    return 0


def cmd_lod(args):
    """lodDist icin vanilla referansi: 'bu boyutta obje ne mesafe alir'.

    lodDist tahmin edilmez, olculur. Asagidaki tablo 316k vanilla archetype'in
    bbox uzun kenari ile lodDist'inin birlikte dagilimidir.
    """
    kovalar = [(0, 1, "<1m"), (1, 3, "1-3m"), (3, 10, "3-10m"),
               (10, 30, "10-30m"), (30, 100, "30-100m"), (100, float("inf"), ">100m")]
    veri = collections.defaultdict(list)

    for row in rows():
        try:
            lo = [float(v) for v in row["bbMin"].split(",")]
            hi = [float(v) for v in row["bbMax"].split(",")]
            uzun = max(hi[i] - lo[i] for i in range(3))
            ld = float(row["lodDist"])
        except (ValueError, IndexError, KeyError):
            continue
        if ld <= 0:
            continue
        for a, b, ad in kovalar:
            if a <= uzun < b:
                veri[ad].append(ld)
                break

    print("\nVANILLA lodDist DAGILIMI (bbox uzun kenarina gore)\n")
    print(f"  {'boyut':<10}{'adet':>8}{'medyan':>9}{'p25':>8}{'p75':>8}")
    for _, _, ad in kovalar:
        v = sorted(veri[ad])
        if not v:
            continue
        med = v[len(v) // 2]
        p25 = v[len(v) // 4]
        p75 = v[min(len(v) - 1, 3 * len(v) // 4)]
        print(f"  {ad:<10}{len(v):>8}{med:>9.0f}{p25:>8.0f}{p75:>8.0f}")

    if args.size is not None:
        for a, b, ad in kovalar:
            if a <= args.size < b:
                v = sorted(veri[ad])
                med = v[len(v) // 2]
                print(f"\n  {args.size} m -> '{ad}' kovasi, ONERI lodDist = {med:.0f}")
                break

    print("""
  LOD ZINCIRI -- 3.07M vanilla entity uzerinde OLCULDU
    * ParentIndex bir SIRA numarasidir; hangi dosyanin sirasi oldugunu ymap
      basligindaki CMapData.parent soyler. DOSYA ADI KALIBINA GUVENME:
      cocuk adi parent adiyla baslayanlar yalnizca %79.
    * -1 = zincir sonu. Ara seviyede entity bayragi 'LOD Adopt Me' (16).
    * HD entity bayragi 1572872 = LOD in Parented YMAP | Cast Static | Cast Dynamic
    * parent.childLodDist == cocuk.lodDist  ->  %86 dogru, %14 DEGIL.
      Kural degil, guclu gelenek.
    * SEVIYE ZINCIRI DUZ DEGIL. Olculen gercek gecisler (parent -> cocuk):
        LOD   -> HD     693.260      SLOD2 -> SLOD1   13.628
        SLOD2 -> LOD     55.817      SLOD4 -> LOD      1.719
        SLOD3 -> LOD     40.250
      'SLOD1 -> LOD' diye bir gecis YOK: SLOD1 zincirin arasinda degil,
      SLOD2'nin yan dalidir. 7 seviye var (ORPHANHD HD LOD SLOD1..SLOD4).
    * ORPHANHD EN YAYGIN seviyedir (1.53M) -- yani cogu entity zincirsizdir.
    * ZINCIRDEN BIR HALKA SILINIRSE TUM ZINCIR BOZULUR: butun seviyeler ayni
      anda yuklenir, titresir, hayalet kopyalar cikar.

  Gercek bir zinciri yurumek icin:  assetdb.py lodchain <archetype>""")
    return 0


LODTSV = os.path.join(DATA, "ymap_lod.tsv.gz")

# rpfPath SART: 8252 ymap adinin 4751'i birden cok RPF'te var (base + DLC).
# Ad bazli okuma kopyalari ust uste bindirir ve sahte kopukluk uretir.
# mapName: ymap'in IC adi. CMapData.parent dosya adina degil buna isaret
# eder; olculdu, 3000 ymap'in 177'sinde ikisi farkli.
LOD_COLS = ["ymap", "mapName", "rpfPath", "parentYmap", "idx", "archetype",
            "flags", "parentIndex", "numChildren", "lodDist", "childLodDist",
            "lodLevel", "priority"]


def lod_rows():
    if not os.path.exists(LODTSV):
        die_layer(f"{LODTSV} yok.\n"
                  "  Uret: powershell -NoProfile -ExecutionPolicy Bypass "
                  "-File scripts/build_ymap_lod.ps1")
    with gzip.open(LODTSV, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == len(LOD_COLS):
                yield dict(zip(LOD_COLS, parts))


DECALTSV = os.path.join(DATA, "decal_types.tsv")

# Turkce is -> decals.dat kategorisi. "kan izi istiyorum" diyen kisi
# 'BLOOD' yazmak zorunda kalmasin.
DECAL_ISI = {
    "kan": "BLOOD", "blood": "BLOOD",
    "mermi": "BANGS", "kursun": "BANGS", "bullet": "BANGS", "impact": "BANGS",
    "ayak": "FOOTPRINT", "iz": "FOOTPRINT", "footprint": "FOOTPRINT",
    "yanik": "BURN", "burn": "BURN",
    "yag": "OIL", "oil": "OIL",
    "benzin": "PETROL", "petrol": "PETROL",
    "camur": "MUD", "mud": "MUD",
    "su": "WATER", "water": "WATER",
    "arac": "VEHICLE", "vehicle": "VEHICLE", "rozet": "VEHICLE BADGES",
    "sicrama": "SPLATTER", "splatter": "SPLATTER",
    "cizik": "SCRAPE", "scrape": "SCRAPE",
}


def cmd_decal(args):
    """decalType tablosu -- AddDecal()'in ilk argumani.

    KAYNAK: oyunun kendi common.rpf\\data\\effects\\decals.dat dosyasi.
    FiveM belgesindeki enum EKSIKTIR; bu tablo tam.

    AYNI ID BIRDEN COK VARYANT tasiyabilir: motor rastgele secer.
    """
    if not os.path.exists(DECALTSV):
        die_layer(f"{DECALTSV} yok.\n  Uret: python scripts/build_decals.py")

    with open(DECALTSV, encoding="utf-8") as fh:
        bas = fh.readline().rstrip("\n").split("\t")
        kayit = [dict(zip(bas, l.rstrip("\n").split("\t"))) for l in fh if l.strip()]

    if args.id is not None:
        r = next((k for k in kayit if int(k["id"]) == args.id), None)
        if r is None:
            print(f"decalType {args.id} tabloda yok.")
            yakin = sorted(kayit, key=lambda k: abs(int(k["id"]) - args.id))[:5]
            print("  en yakin ID'ler:")
            for y in yakin:
                print(f"    {y['id']:<7} {y['kategori']}")
            return 1
        print(f"\ndecalType {r['id']}   [{r['kategori']}]")
        print(f"  varyant     {r['varyant']}   (motor rastgele secer)")
        print(f"  yikanabilir {r['washable']}   su altinda olusur: {r['underwater']}")
        print(f"  dokular     {r['dokular'].replace(';', ', ')}")
        print("\n  Kullanim:")
        print(f"    AddDecal({r['id']}, x,y,z, 0,0,-1, 1,0,0, gen,yuk,"
              " 1.0,1.0,1.0, opaklik, sure, false, false, false)")
        print("    yon (0,0,-1) = asagi bakan yuzey (zemin). sure=-1 kalici.")
        return 0

    q = (args.query or "").lower().strip()
    if q in DECAL_ISI:
        q = DECAL_ISI[q].lower()
    bulunan = [k for k in kayit
               if not q or q in k["kategori"].lower() or q in k["dokular"].lower()]
    if not bulunan:
        print(f"'{args.query}' ile eslesme yok.")
        print("  is turleri: " + ", ".join(sorted(set(DECAL_ISI))))
        return 1

    print(f"\n{len(bulunan)} decalType" + (f" ('{args.query}')" if q else
                                           f" / {len(kayit)} toplam") + "\n")
    for r in bulunan[: args.limit]:
        print(f"  {r['id']:<7} {r['kategori'][:34]:<36} varyant={r['varyant']:<3} "
              f"{r['dokular'][:34]}")
    if len(bulunan) > args.limit:
        print(f"\n  ... {len(bulunan)-args.limit} tane daha (--limit)")
    print("\n  Tek tipin ayrintisi: assetdb.py decal --id <sayi>")
    print("  Kendi dokunu giydirmek: PatchDecalDiffuseMap(id, txd, texture)")
    return 0


SHADERTSV = os.path.join(DATA, "shaders.tsv")

# RENDER BUCKET -- materyal basina, shader'dan AYRI bir alan.
# Kaynak: szio.gta5.drawables.RenderBucket + Sollumz ydr/render_bucket.py
# aciklamalari. Sollumz VARSAYILANI 'Opaque (0)' birakir; decal/cam icin
# elle degistirilmezse yuzey YANLIS cizilir ve hata verilmez.
RENDER_BUCKET = {
    0: ("Opaque", "Alfasiz, opak yuzey."),
    1: ("Alpha", "Alfali ama GOLGESIZ. Genelde cam."),
    2: ("Decal", "Alfali decal, golge yok."),
    3: ("Cutout", "Alfali VE golgeli. Cit/kafes gibi."),
    4: ("No Splash", "Yalniz 'vehicle_nosplash' shader'i ile."),
    5: ("No Water", "Yalniz 'vehicle_nowater' shader'i ile."),
    6: ("Water", "Su shader'lari."),
    7: ("Displacement Alpha", "En son cizilir, sahnedeki her seye displacement "
        "uygular. Yalniz 'glass_displacement' ile."),
}

# Yuzey turu -> shader ailesi. "Bu ne yapayim" sorusunun kisayolu.
SHADER_ISI = {
    "decal":    ("decal", "Yuzeye yapisan leke/iz/yazi. DUZ BIR PLANE uzerine "
                 "konur, zemine 1-2 cm yukarida durur."),
    "cam":      ("glass", "Saydam yuzey."),
    "glass":    ("glass", "Saydam yuzey."),
    "emissive": ("emissive", "Kendi isigi olan yuzey (tabela, ekran, LED)."),
    "terrain":  ("terrain", "Vertex color ile harmanlanan cok katmanli zemin."),
    "kumas":    ("cloth", "Ruzgarda dalgalanan kumas."),
    "cloth":    ("cloth", "Ruzgarda dalgalanan kumas."),
    "arac":     ("vehicle", "Arac govdesi/parcasi."),
    "su":       ("water", "Su yuzeyi."),
    "water":    ("water", "Su yuzeyi."),
    "ped":      ("ped", "Karakter derisi/kiyafeti."),
    "cim":      ("grass", "Cim / bitki ortusu."),
    "grass":    ("grass", "Cim / bitki ortusu."),
}


SHADERUSE = os.path.join(DATA, "shader_usage.tsv")


def shader_usage():
    """Vanilla dosyalarindan olculen shader kullanimi.

    OLCULDU (12.000 ydr + 12.000 yft): decal shader'larinin %92,3'u render
    bucket 2 (Decal) ile kullaniliyor; bucket 0 (Opaque) 5482 kullanimda
    yalniz 1 kez gorulmus. Sollumz'un varsayilani Opaque'tir -- yani
    degistirilmezse neredeyse kesin YANLIS.
    """
    if not os.path.exists(SHADERUSE):
        return {}
    out = {}
    with open(SHADERUSE, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            b = {}
            for parca in (r.get("buckets") or "").split(";"):
                if ":" in parca:
                    k, v = parca.split(":")
                    b[int(k)] = int(v)
            out[r["shader"]] = {"total": int(r["total"]), "buckets": b}
    return out


def cmd_shader(args):
    """GTA V shader tablosu: hangi shader, hangi doku ve parametreleri ister.

    Yanlis shader SESSIZ hatadir: model yuklenir ama yanlis cizilir --
    decal opak cikar, cam saydam olmaz, emissive yanmaz.
    """
    if not os.path.exists(SHADERTSV):
        die_layer(f"{SHADERTSV} yok.\n  Uret: python scripts/build_shaders.py")

    with open(SHADERTSV, encoding="utf-8") as fh:
        bas = fh.readline().rstrip("\n").split("\t")
        kayit = [dict(zip(bas, l.rstrip("\n").split("\t"))) for l in fh if l.strip()]

    q = (args.query or "").lower().strip()
    ipucu = None
    if q in SHADER_ISI:
        q, ipucu = SHADER_ISI[q]

    if args.exact:
        bulunan = [k for k in kayit if k["name"] == args.query]
    else:
        bulunan = [k for k in kayit if not q or q in k["name"].lower()]

    if not bulunan:
        print(f"'{args.query}' ile eslesen shader yok ({len(kayit)} shader var).")
        return 1

    if ipucu:
        print(f"\n  [{args.query}] -> '{q}' ailesi. {ipucu}")

    if args.buckets or q in ("decal", "glass", "water", "cutout"):
        print("\n  RENDER BUCKET (materyal basina, shader'dan AYRI alan):")
        for v, (ad, aciklama) in RENDER_BUCKET.items():
            print(f"    {v}  {ad:<20} {aciklama}")
        print("  Sollumz bucket'i SHADER'A GORE kendisi ayarlar -- CANLI OLCULDU:")
        print("    default.sps -> OPAQUE   decal/decal_dirt/normal_decal/water_decal -> DECAL")
        print("    cutout.sps  -> CUTOUT   alpha/glass/vehicle_decal -> ALPHA")
        print("  Yani DOGRU SHADER'I secersen bucket'a elle dokunman gerekmez.")
        print("  !! ASIL TUZAK: decal yapip 'default' shader'ini birakmak. O zaman")
        print("     bucket OPAQUE kalir, alfa CALISMAZ ve hata da verilmez.")

    kullanim = shader_usage()

    # tek sonuc ya da --exact: tam doku
    if len(bulunan) == 1 or args.exact:
        for r in bulunan:
            print(f"\n=== {r['name']} ===")
            if r["flags"]:
                print(f"  bayraklar : {r['flags']}")
            u = kullanim.get(r["name"])
            if u:
                print(f"  VANILLA KULLANIMI: {u['total']} kez")
                for b, n in sorted(u["buckets"].items(), key=lambda x: -x[1]):
                    ad = RENDER_BUCKET.get(b, ("?", ""))[0]
                    print(f"    render bucket {b} ({ad}): {n}")
            elif kullanim:
                print("  VANILLA KULLANIMI: taranan ornekte gorulmedi")
            print(f"  DOKULAR ({r['texCount']}):")
            for t in (r["textures"].split(";") if r["textures"] else []):
                print(f"    {t}")
            print(f"  PARAMETRELER ({r['valCount']}):")
            for p in (r["params"].split(";") if r["params"] else []):
                print(f"    {p}")
        return 0

    print(f"\n{len(bulunan)} shader" + (f" ('{q}' iceren)" if q else "") + "\n")
    for r in bulunan[: args.limit]:
        print(f"  {r['name']:<38} doku={r['texCount']:<3} param={r['valCount']:<3} "
              f"{r['textures'][:46]}")
    if len(bulunan) > args.limit:
        print(f"\n  ... {len(bulunan)-args.limit} tane daha (--limit)")
    print("\n  Tam parametre listesi icin: assetdb.py shader <tam_ad> --exact")
    return 0


MATTSV = os.path.join(DATA, "collision_materials.tsv")

# Collision materyal BAYRAKLARI (Sollumz arayuzunde 4x4 izgara).
# Materyalin kendi bayraklaridir; bound composite bayraklarindan AYRIDIR.
COLL_FLAGS = [
    "STAIRS", "NOT COVER", "NO DECAL", "NO PTFX",
    "NOT CLIMBABLE", "WALKABLE PATH", "NO NAVMESH", "TOO STEEP FOR PLAYER",
    "SEE THROUGH", "NO CAM COLLISION", "NO RAGDOLL", "NO NETWORK SPAWN",
    "SHOOT THROUGH", "SHOOT THROUGH FX", "VEHICLE WHEEL",
    "NO CAM COLLISION ALLOW CLIPPING",
]

# Bound COMPOSITE bayraklari -- materyal bayraklarindan TAMAMEN AYRI katman.
# Sollumz ybn/properties.py::BoundFlags, 31 bayrak. Obje IKI kume tasir:
#   composite_flags1 = "Type Flags"    (bu bound NEDIR)
#   composite_flags2 = "Include Flags" (bu bound NEYLE carpisir)
COMPOSITE_FLAGS = [
    "UNKNOWN", "MAP WEAPON", "MAP DYNAMIC", "MAP ANIMAL", "MAP COVER",
    "MAP VEHICLE", "VEHICLE NOT BVH", "VEHICLE BVH", "PED", "RAGDOLL",
    "ANIMAL", "ANIMAL RAGDOLL", "OBJECT", "OBJECT_ENV_CLOTH", "PLANT",
    "PROJECTILE", "EXPLOSION", "PICKUP", "FOLIAGE", "FORKLIFT FORKS",
    "TEST WEAPON", "TEST CAMERA", "TEST AI", "TEST SCRIPT",
    "TEST VEHICLE WHEEL", "GLASS", "MAP RIVER", "SMOKE", "UNSMASHED",
    "MAP STAIRS", "MAP DEEP SURFACE",
]


def cmd_mat(args):
    """Collision materyal tablosu: indeks, ad, renk, yogunluk.

    Kaynak: Sollumz 2.9 ybn/collision_materials.py (185 materyal, liste sirasi
    = oyunun materyal indeksi). Capraz dogrulandi: ANIMAL_DEFAULT = 171, bizim
    yaratik rig'i calismasindan bagimsiz olarak olculen degerle ayni.
    """
    if not os.path.exists(MATTSV):
        die_layer(f"{MATTSV} yok.")

    with open(MATTSV, encoding="utf-8") as fh:
        bas = fh.readline().rstrip("\n").split("\t")
        kayit = [dict(zip(bas, l.rstrip("\n").split("\t"))) for l in fh if l.strip()]

    if args.index is not None:
        r = next((k for k in kayit if int(k["index"]) == args.index), None)
        if r is None:
            print(f"materyal indeksi {args.index} yok (0-{len(kayit)-1}).")
            return 1
        print(f"\n[{r['index']}] {r['name']}   \"{r['ui_name']}\"")
        print(f"  renk      rgb({r['r']}, {r['g']}, {r['b']})")
        print(f"  yogunluk  {r['density']}")
        return 0

    q = (args.query or "").lower()
    bulunan = [k for k in kayit
               if not q or q in k["name"].lower() or q in k["ui_name"].lower()]
    if not bulunan:
        print("eslesme yok.")
        return 1

    print(f"\n{len(bulunan)} materyal" + (f" (filtre: {args.query})" if q else
                                          f" / {len(kayit)} toplam") + "\n")
    for r in bulunan[: args.limit]:
        print(f"  {r['index']:>4}  {r['name']:<30} {r['ui_name']:<28} "
              f"yogunluk={r['density']}")
    if len(bulunan) > args.limit:
        print(f"\n  ... {len(bulunan)-args.limit} satir daha (--limit)")

    print("\n  MATERYAL BAYRAKLARI (materyalin kendi bayraklari, composite'ten AYRI):")
    for i in range(0, len(COLL_FLAGS), 4):
        print("    " + "  ".join(f"{f:<32}" for f in COLL_FLAGS[i:i+4]).rstrip())
    print("\n  COMPOSITE BAYRAKLARI -- AYRI BIR KATMAN (31 bayrak, IKI kume:")
    print("  'Type Flags' = composite_flags1, 'Include Flags' = composite_flags2):")
    for i in range(0, len(COMPOSITE_FLAGS), 4):
        print("    " + "  ".join(f"{f:<22}" for f in COMPOSITE_FLAGS[i:i+4]).rstrip())
    print("\n  Havuz/su olcumu (vanilla): MAP WEAPON + MAP DYNAMIC + MAP ANIMAL")
    print("  + MAP COVER + MAP RIVER; materyal WATER, bayraklari SEE THROUGH +")
    print("  SHOOT THROUGH + NO CAM COLLISION.")

    onayar = os.path.join(DATA, "collision_flag_presets.tsv")
    if os.path.exists(onayar):
        with open(onayar, encoding="utf-8") as fh:
            bas = fh.readline().rstrip("\n").split("\t")
            ps = [dict(zip(bas, l.rstrip("\n").split("\t"))) for l in fh if l.strip()]
        print("\n  HAZIR COMPOSITE ON AYARLARI (Sollumz 'Flag Presets' dugmesi):")
        for p in ps:
            t = p["typeFlags"].split(";") if p["typeFlags"] else []
            i = p["includeFlags"].split(";") if p["includeFlags"] else []
            print(f"    {p['name']:<20} type={len(t):>2} include={len(i):>2}")
        gen = next((p for p in ps if p["name"].startswith("General (Default)")), None)
        if gen:
            print("    -> 'General (Default)' siradan harita objesi icin dogru set:")
            print(f"       type   : {gen['typeFlags'].replace(';', ' + ')}")
            print(f"       include: {gen['includeFlags'].replace(';', ' + ')}")

    print("\n  Kapi standardi: NOT COVER + NOT CLIMBABLE")
    print("  DIKKAT: mesh collision + 'Dynamic' arketip bayragi = obje dunya")
    print("  collision'iyla ETKILESMEZ, yerin icine duser. Dinamik objede")
    print("  collision PRIMITIVE olmali (bound box / cylinder).")
    return 0


def cmd_lodaudit(args):
    """Kendi ymap'lerimizi vanilla'nin davranisiyla karsilastirir.

    Mutlak sayi bir sey ifade etmez; OLCUT vanilla'dir. Rockstar'in 3.07M
    entity'sinde hic gorulmeyen bir kombinasyon bizde varsa, o bir kusurdur.
    """
    LOD_PARENT = 1 << 3          # 'LOD in Parented YMAP'
    ADOPT_ME = 1 << 4            # 'LOD Adopt Me'

    say = {"v_n": 0, "c_n": 0}
    kusur = collections.defaultdict(lambda: {"v": 0, "c": 0})
    nerede = collections.Counter()

    for r in lod_rows():
        vanilla = ".rpf" in r["rpfPath"].lower()
        say["v_n" if vanilla else "c_n"] += 1
        try:
            f = int(r["flags"])
            pi = int(r["parentIndex"])
            nc = int(r["numChildren"])
        except ValueError:
            continue

        bulgular = []
        if (f & LOD_PARENT) and pi < 0:
            bulgular.append("'LOD in Parented YMAP' bitli ama parentIndex=-1")
        if (f & ADOPT_ME) and nc == 0:
            bulgular.append("'LOD Adopt Me' bitli ama cocugu yok")
        if pi >= 0 and not r["parentYmap"]:
            bulgular.append("parentIndex var ama ymap parent BILDIRMIYOR")

        for b in bulgular:
            kusur[b]["v" if vanilla else "c"] += 1
            if not vanilla:
                nerede[(b, r["ymap"])] += 1

    print(f"\nVANILLA {say['v_n']} entity  |  BIZIM {say['c_n']} entity\n")
    if not kusur:
        print("  hicbir tutarsizlik yok.")
        return 0

    for b, d in sorted(kusur.items(), key=lambda x: -x[1]["c"]):
        vo = 100 * d["v"] / max(say["v_n"], 1)
        co = 100 * d["c"] / max(say["c_n"], 1)
        damga = "  <-- VANILLA'DA HIC YOK" if d["v"] == 0 and d["c"] else ""
        print(f"  {b}")
        print(f"     vanilla {d['v']:>8} (%{vo:.2f})   bizim {d['c']:>6} (%{co:.2f}){damga}")
        en = [(ym, n) for (bb, ym), n in nerede.items() if bb == b]
        for ym, n in sorted(en, key=lambda x: -x[1])[:5]:
            print(f"       {ym:<40} {n}")
        print()

    print("  Yorum: vanilla oraninin ustundeki her sey SENIN haritanin kusurudur.")
    print("  Vanilla'da SIFIR olan bir kombinasyon kesinlikle yanlistir --")
    print("  Rockstar 3M entity boyunca bir kez bile o hale dusmemis.")
    return 0


def cmd_lodchain(args):
    """Bir archetype'in GERCEK LOD zincirini vanilla'dan yurur.

    Zincirin nasil kurulmasi gerektigini tarif etmek yerine calisan bir
    ornegi gosterir: hangi ymap, hangi indeks, hangi mesafe, hangi bayrak.
    """
    hedef = args.name.lower()
    ent = collections.defaultdict(dict)
    par = {}
    baslangic = []

    for r in lod_rows():
        ent[r["ymap"]][int(r["idx"])] = r
        if r["parentYmap"]:
            par[r["ymap"]] = r["parentYmap"]
        if hedef in r["archetype"].lower() and not baslangic:
            baslangic.append((r["ymap"], int(r["idx"])))

    if not baslangic:
        print(f"'{args.name}' hicbir ymap'te bulunamadi.")
        return 1

    def coz(ad):
        n = ad if ad.endswith(".ymap") else ad + ".ymap"
        return n if n in ent else None

    ym, i = baslangic[0]
    print(f"\nLOD ZINCIRI  <- {ent[ym][i]['archetype']}\n")
    for adim in range(12):
        r = ent[ym][i]
        bayrak = decode_flags(r["flags"], ENTITY_FLAGS)
        print(f"  {adim}. {r['archetype']}")
        print(f"     {r['lodLevel']}   ymap={r['ymap']} idx={i}")
        print(f"     lodDist={r['lodDist']}  childLodDist={r['childLodDist']}  "
              f"cocuk={r['numChildren']}  priority={r['priority']}")
        if bayrak:
            print(f"     flags={r['flags']} -> {' | '.join(bayrak)}")
        pi = int(r["parentIndex"])
        if pi < 0:
            print("     parentIndex=-1  ->  ZINCIR SONU")
            break
        pym = par.get(ym)
        if not pym:
            print(f"     parentIndex={pi} ama bu ymap parent BILDIRMIYOR -> izlenemiyor")
            break
        pn = coz(pym)
        if not pn or pi not in ent[pn]:
            print(f"     parentIndex={pi} -> {pym}  (o indekste entity YOK: kopuk zincir)")
            break
        print(f"     parentIndex={pi}  ->  {pym}")
        print()
        ym, i = pn, pi
    return 0


PROCTSV = os.path.join(DATA, "procedural.tsv")


def cmd_proc(args):
    """Prosedurel bitki/obje tablosu -- collision materyalindeki 'Procedural ID'.

    Bir zemin collision'ina yazdigin sayinin orada NE bitirecegini soyleyen
    tek kaynak. ID = procedural.meta icindeki <procTagTable> INDEKSIDIR
    (procObjInfos degil; ikisi ayri liste).
    """
    if not os.path.exists(PROCTSV):
        die_layer(f"{PROCTSV} yok.\n"
                  "  Uret: powershell -NoProfile -ExecutionPolicy Bypass "
                  "-File scripts/build_procedural.ps1")

    with open(PROCTSV, encoding="utf-8") as fh:
        basliklar = fh.readline().rstrip("\n").split("\t")
        kayit = [dict(zip(basliklar, l.rstrip("\n").split("\t")))
                 for l in fh if l.strip()]

    if args.id is not None:
        r = next((k for k in kayit if int(k["id"]) == args.id), None)
        if r is None:
            print(f"Procedural ID {args.id} tablo disinda (0-{len(kayit)-1}).")
            return 1
        print(f"\nProcedural ID {r['id']}  ->  {r['name']}")
        print(f"  tur        {r['kind']}")
        if r["procObjTag"]:
            print(f"  procObjTag {r['procObjTag']}   (kati obje: tas/cop/cali modeli)")
        if r["plantTag"]:
            print(f"  plantTag   {r['plantTag']}   (cim/bitki, shader ile cizilir)")
        if r["models"]:
            print(f"  modeller   {r['models']}")
        if r["kind"] == "bos":
            print("  !! Bu indeks KULLANILMIYOR -- zemine yazarsan hicbir sey bitmez.")
        return 0

    q = (args.query or "").lower()
    bulunan = [k for k in kayit
               if k["kind"] != "bos"
               and (not q or q in k["name"].lower() or q in k["models"].lower())]
    if not bulunan:
        print("eslesme yok.")
        return 1

    print(f"\n{len(bulunan)} dolu procedural ID"
          f"{' (filtre: ' + args.query + ')' if q else f' / {len(kayit)} toplam'}\n")
    for r in bulunan[: args.limit]:
        satir = f"  {r['id']:>4}  {r['name']:<34} {r['kind']}"
        if r["models"]:
            satir += f"  [{r['models'][:52]}]"
        print(satir)
    if len(bulunan) > args.limit:
        print(f"\n  ... {len(bulunan) - args.limit} satir daha (--limit)")
    print("\n  Kullanim: collision materyalinin 'Procedural ID' alanina bu sayi yazilir.")
    print("  @ma cim sistemi cok hassastir: ucgenler kucukse hic cikmaz, ve")
    print("  oyun ayarindaki 'Grass Quality' dusukse HIC gorunmez.")
    return 0


def cmd_flags(args):
    """Bayrak tamsayisini isimlere cozer.

    Kaynak tablolar Sollumz 2.9 ytyp/properties/flags.py'den birebir alindi;
    bit eslemesi flagN -> 2**(N-1) (bkz. ARCH_FLAGS uzerindeki not).
    """
    ham = args.value.strip()
    try:
        deger = int(ham, 0)
    except ValueError:
        print(f"gecersiz sayi: {ham}")
        return 1

    tablo, tur = (ENTITY_FLAGS, "ENTITY (ymap)") if args.entity else (ARCH_FLAGS, "ARCHETYPE (ytyp)")
    isimler = decode_flags(deger, tablo)

    print(f"\n{deger}  ({deger:#x})  ->  {tur} bayragi")
    if not isimler:
        print("   (hicbir bit kurulu degil)")
        return 0
    for ad in isimler:
        if ad.startswith("(cozulmeyen"):
            print(f"   {ad}")
            continue
        bit = tablo.index(ad)
        print(f"   {1 << (bit - 1):>12}  bit{bit - 1:<2}  {ad}")

    if not args.entity and deger & ARCH_FLAG_DOOR_PHYSICS:
        print("\n   NOT: 'Enable Door Physics' kurulu -> kapi sistemi bu objede")
        print("        specialAttribute kapi tipi olmasa bile calisabilir.")
    return 0


FRAMEWORK = os.path.join(DATA, "framework_api.tsv.gz")


def cmd_framework(args):
    """Framework API: export / event / callback / komut / ox_lib modulu.

    NEDEN: lint yalniz GTA NATIVE'ini dogrular. Ama QBCore/ox kaynagindaki
    hatalarin cogu framework cagrisindadir ve HICBIRI hata firlatmaz:
    olmayan event tetiklenirse hicbir yere gitmez; olmayan export ancak
    o satir CALISINCA 'nil value' verir - belki ayda bir.

    Otorite SUNUCUDA KURULU kaynaklardir, upstream GitHub degil.
    """
    rows = list(dump_rows(FRAMEWORK, "framework API"))
    kurulu = {r["name"].lower() for r in rows if r["kind"] == "resource"}

    if args.denetle:
        tanim_ex = {(r["resource"].lower(), r["name"].lower())
                    for r in rows if r["kind"] == "export"}
        tanim_ev = {r["name"].lower() for r in rows if r["kind"] == "event"}
        modul = {r["name"].lower() for r in rows if r["kind"] == "lib_module"}
        yok, yazim, ev, lib = collections.Counter(), collections.Counter(), \
            collections.Counter(), collections.Counter()
        for r in rows:
            if r["kind"] == "export_use":
                res, _, ad = r["name"].partition(":")
                if res.lower() not in kurulu:
                    yok[res.lower()] += 1
                elif (res.lower(), ad.lower()) not in tanim_ex:
                    yazim[r["name"]] += 1
            elif r["kind"] == "event_use" and r["name"].lower() not in tanim_ev:
                ev[r["name"]] += 1
            elif r["kind"] == "lib_use" and r["name"].lower() not in modul:
                lib[r["name"]] += 1
        print(t("fw_a"))
        for k, n in yok.most_common(args.limit):
            print(f"   {n:>4}x  {k}")
        print("   " + t("fw_calls", n=sum(yok.values()), u=len(yok),
                        unit="resources" if get_lang() == "en" else "kaynak") + "\n")
        print(t("fw_b"))
        for k, n in yazim.most_common(args.limit):
            print(f"   {n:>4}x  {k}")
        print("   " + t("fw_calls", n=sum(yazim.values()), u=len(yazim), unit="unique" if get_lang() == "en" else "benzersiz"))
        print(f"   {t('note')}: {t('fw_b_note')}\n")
        print(t("fw_c"))
        for k, n in ev.most_common(args.limit):
            print(f"   {n:>4}x  {k}")
        print("   " + t("fw_calls", n=sum(ev.values()), u=len(ev), unit="unique" if get_lang() == "en" else "benzersiz"))
        print(f"   {t('note')}: {t('fw_c_note')}\n")
        print(t("fw_d"))
        for k, n in lib.most_common(args.limit):
            print(f"   {n:>4}x  {k}")
        print("   " + t("fw_calls", n=sum(lib.values()), u=len(lib), unit="unique" if get_lang() == "en" else "benzersiz"))
        return EXIT_OK

    q = args.query.lower() if args.query else ""
    hits = [r for r in rows if r["kind"] != "resource"
            and (not q or q in r["name"].lower() or q in r["resource"].lower())]
    if args.kind:
        hits = [r for r in hits if r["kind"] == args.kind]
    if args.tanim:
        hits = [r for r in hits if not r["kind"].endswith("_use")]
    for r in hits[:args.limit]:
        v = f" v{r['version']}" if r["version"] else ""
        print(f"  {r['kind']:<13} {r['name']:<48} [{r['resource']}{v}] "
              f"{r['side']:<7} {r['file']}:{r['line']}")
    extra = len(hits) - args.limit
    print("\n" + t("results", n=len(hits))
          + (t("hidden", n=extra) if extra > 0 else "")
          + "   |  " + t("fw_scanned", n=len(kurulu)))
    return EXIT_NOTFOUND if not hits else EXIT_OK


def katman_envanteri():
    """Her veri katmaninin VAR/YOK durumu + boyutu.

    NEDEN: eksik katman sessizce "0 sonuc" uretir ve cagiran taraf bunu
    "asset yok" diye okur. Envanter olmadan "hicbir sey denetlenmedi" ile
    "her sey temiz" ayni ekrana benzer.
    """
    katmanlar = [
        ("archetypes.tsv.gz", TSV), ("entities.db", ENTDB), ("ymap_lod.tsv.gz", LODTSV),
        ("clips.tsv.gz", CLIPS), ("anims.tsv.gz", ANIMS), ("props.tsv.gz", PROPS),
        ("scenarios.tsv.gz", SCENARIOS), ("expressions.tsv.gz", EXPRS),
        ("ytyp_extensions.tsv.gz", EXT_TSV), ("ptfx_effects.tsv.gz", PTFXTSV),
        ("shaders.tsv", SHADERTSV), ("collision_materials.tsv", MATTSV),
        ("decal_types.tsv", DECALTSV), ("procedural.tsv", PROCTSV),
        # --- dump katmanlari ---
        ("peds_meta.tsv.gz", PEDMETA), ("weapons.tsv.gz", WEAPONS),
        ("weapon_parts.tsv.gz", WPNPARTS), ("vehicles.tsv.gz", VEHICLES),
        ("mlo_interiors.tsv.gz", MLOS), ("ipls.tsv.gz", IPLS),
        ("world_objects.tsv.gz", WORLDOBJ),
        ("framework_api.tsv.gz", FRAMEWORK),
        # --- isik / timecycle ---
        ("lights.tsv.gz", os.path.join(DATA, "lights.tsv.gz")),
        ("timecycle.tsv.gz", os.path.join(DATA, "timecycle.tsv.gz")),
    ]
    print(t("inventory"))
    eksik = 0
    for ad, yol in katmanlar:
        if os.path.exists(yol):
            mb = os.path.getsize(yol) / (1024 * 1024)
            print(f"  [{t('inv_present')}] {ad:<26} {mb:>8.2f} MB")
        else:
            eksik += 1
            print(f"  [{t('inv_missing')}] {ad:<26}        - {t('inv_missing_note')}")
    dm = os.path.join(DATA, "dumps.meta.json")
    if os.path.exists(dm):
        try:
            with open(dm, encoding="utf-8-sig") as fh:
                d = json.load(fh)
            print(f"\n  {t('dump_version'):<12}: {d.get('gameVersion') or '?'}")
            print(f"  {t('built_at'):<12}: {d.get('generatedAtUtc') or '?'}")
        except Exception:
            pass
    print("\n  " + t("inv_installed", n=len(katmanlar) - eksik, t=len(katmanlar))
          + (t("inv_missing_count", n=eksik) if eksik else ""))
    return eksik


def cmd_stats(args):
    """Katman envanteri + archetype dagilimi.

    ⛔ stats ASLA EXIT 2 DONMEZ. Bu komut "ne kurulu?" sorusunun cevabidir;
    eksik katman yuzunden calismamasi, yangin alarminin yangin yuzunden
    calismamasi gibidir. Yeni kullanici ilk bunu calistirir - burada hata
    alirsa neyin eksik oldugunu ogrenecegi yeri kaybeder.
    """
    eksik = katman_envanteri()
    print()
    if os.path.exists(META):
        with open(META, encoding="utf-8-sig") as fh:
            print(json.dumps(json.load(fh), indent=2, ensure_ascii=False))
    if not os.path.exists(TSV):
        print("\nArchetype dagilimi: archetypes.tsv.gz kurulu degil (AGIR katman).")
        print("  Uret: powershell -File scripts/build_archetypes.ps1  (GTA V + CodeWalker gerekir)")
        return EXIT_OK
    dist, total = {}, 0
    for r in rows():
        total += 1
        dist[r["specialAttribute"]] = dist.get(r["specialAttribute"], 0) + 1
    print(f"\nToplam archetype: {total}")
    print("specialAttribute dagilimi:")
    for k, v in sorted(dist.items(), key=lambda kv: -kv[1]):
        label = SPECIAL.get(int(k), ("?", ""))[0]
        print(f"  {k:>4} : {v:>7}   {label}")
    return EXIT_OK


# ============================================================================
# DUMP KATMANLARI (build_dumps.py uretir) - ped meta, silah, arac, MLO, IPL,
# dunya nesneleri. Kaynak: DurtyFree/gta-v-data-dumps.
#
# JOIN KURALI: bu katmanlarin ad kolonlari KAYNAKTAKI harf duzeniyle yazilir
# (W_AR_ASSAULTRIFLE), plugin'in kendi katmanlari kucuk harftir. Karsilastirma
# DAIMA .lower() uzerinden yapilir. Birebir join her ailede 0 dondurur ve bu
# SESSIZDIR: tablo dolu gorunur, eslesme bos cikar, "bu model yok" denir.
# ============================================================================
PEDMETA = os.path.join(DATA, "peds_meta.tsv.gz")
WEAPONS = os.path.join(DATA, "weapons.tsv.gz")
WPNPARTS = os.path.join(DATA, "weapon_parts.tsv.gz")
VEHICLES = os.path.join(DATA, "vehicles.tsv.gz")
MLOS = os.path.join(DATA, "mlo_interiors.tsv.gz")
IPLS = os.path.join(DATA, "ipls.tsv.gz")
WORLDOBJ = os.path.join(DATA, "world_objects.tsv.gz")


def dump_rows(path, what):
    """Baslikli gzip TSV -> dict akisi. Kolon adlarini baslik satirindan alir,
    boylece build_dumps.py kolon eklediginde burasi degismek zorunda kalmaz."""
    if not os.path.exists(path):
        die_layer(f"{os.path.basename(path)} yok ({what}).\n"
                  "  Uret: python scripts/build_dumps.py --dump <gta-v-data-dumps klasoru>")
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        cols = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == len(cols):
                yield dict(zip(cols, parts))


def cmd_pedmeta(args):
    """Ped kunyesi: hangi klip sozlugu, hangi expression, hangi movement clipset.

    NEDEN: ped animasyonu/yuz isinde "bu ped hangi expression'i tuketiyor"
    sorusu tahmin edilir ve yanlis eslesme SESSIZCE yanlis yuz uretir.
    """
    q = args.query.lower()
    hits = [r for r in dump_rows(PEDMETA, "ped meta") if q in r["name"].lower()]
    for r in hits[:args.limit]:
        print(f"\n=== {r['name']} ===  [{r['pedtype'] or '?'}]  dlc={r['dlc'] or '-'}"
              f"  {t('ped_bones')}={r['boneCount']}")
        print(f"  {t('ped_clipdict'):<17}: {r['clipDict'] or '-'}")
        print(f"  expression       : set={r['exprSet'] or '-'}  "
              f"dict={r['exprDict'] or '-'}  ad={r['exprName'] or '-'}")
        print(f"  {t('ped_movement'):<17}: {r['movementClipSet'] or '-'}")
        print(f"  {t('ped_strafe'):<17}: {r['strafeClipSet'] or '-'} / {r['gestureClipSet'] or '-'}")
        print(f"  {t('ped_face'):<17}: {r['visemeClipSet'] or '-'} / {r['facialClipsetGroup'] or '-'}")
        if r.get("propsName"):
            print(f"  {t('ped_props'):<17}: {r['propsName']}")
        if r.get("voiceGroup"):
            print(f"  {t('ped_voice'):<17}: {r['voiceGroup']}")
    extra = len(hits) - args.limit
    print("\n" + t("results", n=len(hits))
          + (t("hidden", n=extra) if extra > 0 else ""))
    if hits:
        print(f"{t('note')}: {t('ped_clipset_note')}")
    return EXIT_NOTFOUND if not hits else EXIT_OK


def cmd_weapon(args):
    """Silah kunyesi + bilesenler. Bilesen ve livery AYNI tabloda (kind kolonu)."""
    q = args.query.lower()
    hits = [r for r in dump_rows(WEAPONS, "silahlar")
            if q in r["name"].lower() or q in (r["model"] or "").lower()
            or q in (r["label"] or "").lower()]
    parts = {}
    if hits:
        adlar = {r["name"].lower() for r in hits}
        for pr in dump_rows(WPNPARTS, "silah parcalari"):
            if pr["weapon"].lower() in adlar:
                parts.setdefault(pr["weapon"].lower(), []).append(pr)
    for r in hits[:args.limit]:
        print(f"\n=== {r['name']} ===  {r['label']}")
        print(f"  {t('wpn_category'):<15}: {r['category']}  /  {r['damageType']}")
        print(f"  {t('wpn_model'):<15}: {r['model'] or t('wpn_no_model')}")
        print(f"  mermi          : {r['ammoType']}  model={r['ammoModel'] or '-'}"
              f"  sp={r['maxAmmoSp']} mp={r['maxAmmoMp']}")
        print(f"  {t('wpn_dlc_tint'):<15}: {r['dlc']}  /  {r['tints'] or '-'}")
        ps = parts.get(r["name"].lower(), [])
        comp = [x for x in ps if x["kind"] == "component"]
        liv = [x for x in ps if x["kind"] == "livery"]
        print(f"  bilesen={len(comp)}  livery={len(liv)}")
        if args.parcalar:
            for x in comp:
                d = "  [varsayilan]" if x["isDefault"] == "1" else ""
                print(f"    C {x['name']:<44} {t('ped_bones')}={x['attachBone'] or '-':<16}{d}")
            for x in liv:
                print(f"    L {x['name']:<44} {x['label']}")
    extra = len(hits) - args.limit
    print("\n" + t("results", n=len(hits))
          + (t("hidden", n=extra) if extra > 0 else ""))
    if hits and not args.parcalar:
        print(f"{t('tip')}: {t('wpn_parts_tip')}")
        print(f"{t('note')}: {t('wpn_livery_note')}")
    return EXIT_NOTFOUND if not hits else EXIT_OK


def cmd_vehicle(args):
    """Arac kunyesi. handlingId ile handling.meta override'i eslesir."""
    q = args.query.lower()
    hits = [r for r in dump_rows(VEHICLES, "araclar")
            if q in r["name"].lower() or q in (r["displayName"] or "").lower()
            or q in (r["manufacturer"] or "").lower()]
    for r in hits[:args.limit]:
        print(f"\n=== {r['name']} ===  {r['displayName']}  ({r['manufacturer'] or '?'})")
        print(f"  sinif/tip   : {r['class']} / {r['type']}   koltuk={r['seats']}"
              f"  teker={r['wheelsCount']}")
        print(f"  handlingId  : {r['handlingId']}     layout={r['layoutId']}")
        print(f"  {t('veh_dlc_price'):<12}: {r['dlc']}  /  {r['price']}")
        if r.get("modKits"):
            print(f"  modKit      : {r['modKits']}")
        if r.get("extras"):
            print(f"  extra       : {r['extras']}")
    extra = len(hits) - args.limit
    print("\n" + t("results", n=len(hits))
          + (t("hidden", n=extra) if extra > 0 else ""))
    return EXIT_NOTFOUND if not hits else EXIT_OK


def cmd_mlo(args):
    """MLO ic mekanlari. KONUM BASINA satir: ayni ic mekan birden fazla yerde."""
    q = args.query.lower()
    hits = [r for r in dump_rows(MLOS, "MLO ic mekanlari") if q in r["name"].lower()]
    gruplar = {}
    for r in hits:
        gruplar.setdefault(r["name"], []).append(r)
    for ad, rs in list(gruplar.items())[:args.limit]:
        r0 = rs[0]
        konum = [r for r in rs if r["x"]]
        print(f"\n=== {ad} ===  dlc={r0['dlc'] or '-'}  entity={r0['entityCount']}")
        print(f"  ytyp: {r0['ytypPath'] or '-'}")
        if not konum:
            print(f"  {t('mlo_unplaced')}")
        for r in konum[:args.konum]:
            print(f"  vec3({r['x']}, {r['y']}, {r['z']})  bayrak={r['flags'] or '-'}")
        if len(konum) > args.konum:
            print("  " + t("mlo_more", n=len(konum) - args.konum))
        print("  -> " + t("mlo_locations", n=len(konum)))
    extra = len(gruplar) - args.limit
    print(f"\n{len(gruplar)} ic mekan" + (f" ({extra} gosterilmedi)" if extra > 0 else ""))
    if len(gruplar) > 1:
        print(f"{t('note')}: {t('mlo_variant_note')}")
    return EXIT_NOTFOUND if not gruplar else EXIT_OK


def cmd_ipl(args):
    """IPL adi + sinir kutusu. RequestIpl/RemoveIpl icin ad dogrulamasi."""
    q = args.query.lower()
    hits = [r for r in dump_rows(IPLS, "IPL'ler")
            if q in r["name"].lower() or q in (r["group"] or "").lower()
            or q in (r["category"] or "").lower()]
    for r in hits[:args.limit]:
        yer = f"vec3({r['x']}, {r['y']}, {r['z']})" if r["x"] else "(konumsuz)"
        print(f"  {r['name']:<40} {yer}  [{r['group'] or '-'} / {r['category'] or '-'}]")
    extra = len(hits) - args.limit
    print("\n" + t("results", n=len(hits))
          + (t("hidden", n=extra) if extra > 0 else ""))
    if hits:
        print(f"{t('usage')}: {t('ipl_usage')}")
    return EXIT_NOTFOUND if not hits else EXIT_OK


def cmd_world(args):
    """Dunya nesneleri: aile etiketi + konum + ROTASYON.

    entities.tsv.gz 3M satirla "nerede ne var" der ama "bu bir ATM'dir"
    diyemez ve rotasyon tutmaz. Loot/spawn noktasi ve prop degistirme icin
    gereken ikisi de burada.
    """
    rows = list(dump_rows(WORLDOBJ, "dunya nesneleri"))
    if args.aileler:
        say = collections.Counter(r["family"] for r in rows)
        model = collections.defaultdict(set)
        for r in rows:
            model[r["family"]].add(r["model"])
        for fam, n in say.most_common():
            print(f"  {fam:<26} {n:>6} nesne  {len(model[fam]):>3} model")
        print("\n" + t("world_families", f=len(say), n=len(rows)))
        return EXIT_OK

    hits = rows
    if args.family:
        f = args.family.lower()
        hits = [r for r in hits if f in r["family"].lower()]
    if args.model:
        m = args.model.lower()
        hits = [r for r in hits if m in r["model"].lower()]
    if args.near:
        try:
            cx, cy, cz = [float(v) for v in args.near.split(",")]
        except ValueError:
            print(t("world_near_fmt"), file=sys.stderr)
            return EXIT_INTERNAL
        r2 = args.mesafe * args.mesafe
        yakin = []
        for r in hits:
            dx = float(r["x"]) - cx
            dy = float(r["y"]) - cy
            dz = float(r["z"]) - cz
            d2 = dx * dx + dy * dy + dz * dz
            if d2 <= r2:
                yakin.append((d2 ** 0.5, r))
        yakin.sort(key=lambda t: t[0])
        for d, r in yakin[:args.limit]:
            print(f"  {d:6.1f}m  {r['family']:<20} {r['model']:<34} "
                  f"vec3({r['x']}, {r['y']}, {r['z']})  rotZ={r['rz']}")
        print("\n" + t("world_within", n=len(yakin), r=args.mesafe))
        return EXIT_NOTFOUND if not yakin else EXIT_OK

    for r in hits[:args.limit]:
        print(f"  {r['family']:<20} {r['model']:<34} vec3({r['x']}, {r['y']}, {r['z']})"
              f"  rot({r['rx']}, {r['ry']}, {r['rz']})")
    extra = len(hits) - args.limit
    print("\n" + t("results", n=len(hits))
          + (t("hidden", n=extra) if extra > 0 else ""))
    return EXIT_NOTFOUND if not hits else EXIT_OK


def cmd_doctor(args):
    """Sessiz hata kapisi. Kendi cikis kodlarini dondurur (bkz. doctor.py):

        0 temiz | 1 bulgu var | 2 EN AZ BIR DOSYA DENETLENEMEDI

    2, EXIT_NOLAYER ile ayni sayidir ve bu KASITLIDIR: denetlenemeyen dosya
    "temiz" degildir, tipki kurulu olmayan katmanin "sonuc yok" olmamasi gibi.
    """
    import doctor  # tembel: diger komutlar subprocess/tempfile yuku odemesin
    return doctor.calistir(args)


def cmd_timecycle(args):
    """Timecycle modifier sorgusu. 0 bulundu | 1 yok | 2 katman kurulu degil."""
    import timecycle
    return timecycle.calistir(args)


def cmd_light(args):
    """Gomulu isiklari coz. 0 isik bulundu | 1 isik yok | 2 dosya okunamadi."""
    import light
    return light.calistir(args)


def cmd_diff(args):
    """Yapisal diff. 0 fark yok | 1 fark var | 2 dosya okunamadi."""
    import yapisal_diff
    return yapisal_diff.calistir(args)


def main():
    p = argparse.ArgumentParser(
        description="muto-atlas — GTA V / FiveM ground-truth asset database")
    add_lang_arg(p)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="archetype detayi + yorum")
    s.add_argument("names", nargs="+")
    s.add_argument("--raw", action="store_true", help="yorumsuz, sadece ham alanlar")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("door", help="kapi gibi acilir mi karari")
    s.add_argument("names", nargs="+")
    s.set_defaults(func=cmd_door)

    s = sub.add_parser("search", help="ada gore arama")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("where", help="archetype dunyada nerede (ymap + MLO ic mekan)")
    s.add_argument("names", nargs="+")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_where)

    s = sub.add_parser("near", help="bir koordinatin cevresinde ne var")
    s.add_argument("x", type=float)
    s.add_argument("y", type=float)
    s.add_argument("z", type=float)
    s.add_argument("--radius", type=float, default=10.0)
    s.add_argument("--filter", help="isimde gecmesi gereken parca (or. door)")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_near)

    s = sub.add_parser("anim", help="animasyon dict/clip arama")
    s.add_argument("query")
    s.add_argument("--dict", action="store_true", help="sorguyu TAM dictionary adi say, klipleri listele")
    s.add_argument("--dict-only", action="store_true", help="sadece dictionary adlarinda ara")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_anim)

    s = sub.add_parser("bones", help="modelin iskeleti: kemik adi + tag")
    s.add_argument("names", nargs="+")
    s.add_argument("--limit", type=int, default=60)
    s.set_defaults(func=cmd_bones)

    s = sub.add_parser("clipfit", help="bu klibi hangi model oynatabilir (kemik tag eslesmesi)")
    s.add_argument("dict")
    s.add_argument("clip")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_clipfit)

    s = sub.add_parser("expr", help="expression (.yed) arama - prosedurel/yay hareketi")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_expr)

    s = sub.add_parser("prop", help="spawn edilebilir prop arama")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_prop)

    s = sub.add_parser("scenario", help="ped senaryo arama")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_scenario)

    s = sub.add_parser("propanim", help="bir PROP'un gercek animasyonlari (klip adi = prop model adi)")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=6, help="kac prop gosterilsin")
    s.add_argument("--dicts", type=int, default=8, help="prop basina kac dict")
    s.set_defaults(func=cmd_propanim)

    s = sub.add_parser("ptfx", help="partikul extension arama (prop adi / efekt adi / fxType)")
    s.add_argument("query", nargs="?", default="", help="prop adi ya da efekt adi parcasi")
    s.add_argument("--type", type=int, choices=range(8), metavar="0-7",
                   help="fxType: 0=Ambient 1=Collision 2=Shot 3=Break 4=Destroy "
                        "5=Anim(kullanilmiyor) 6=RayFire 7=InWater")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_ptfx)

    s = sub.add_parser("fx", help="partikul EFEKT katalogu (.ypt): efekt var mi, hangi ypt'de")
    s.add_argument("query", nargs="?", default="", help="efekt adi ya da parcasi")
    s.add_argument("--exact", action="store_true", help="tam ad; yoksa 'YOK' der ve benzer onerir")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_fx)

    s = sub.add_parser("ext", help="bir archetype'in TUM ytyp extension'lari")
    s.add_argument("name", help="archetype adi (parca da olur)")
    s.set_defaults(func=cmd_ext)

    s = sub.add_parser("lod", help="vanilla lodDist referansi + LOD zinciri kurallari")
    s.add_argument("--size", type=float, metavar="M",
                   help="objenin uzun kenari (m) -> oneri lodDist")
    s.set_defaults(func=cmd_lod)

    s = sub.add_parser("proc", help="prosedurel cim/obje tablosu (collision 'Procedural ID')")
    s.add_argument("query", nargs="?", default="", help="ad ya da model parcasi")
    s.add_argument("--id", type=int, help="tek bir Procedural ID'yi coz")
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(func=cmd_proc)

    s = sub.add_parser("decal", help="decalType tablosu (194) -- AddDecal()'in ilk argumani")
    s.add_argument("query", nargs="?", default="",
                   help="is turu: kan/mermi/ayak/yanik/yag/benzin/camur/su/arac")
    s.add_argument("--id", type=int, help="tek bir decalType'i coz")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_decal)

    s = sub.add_parser("shader", help="GTA V shader tablosu (249): doku + parametre")
    s.add_argument("query", nargs="?", default="",
                   help="ad parcasi ya da is turu: decal/cam/emissive/terrain/kumas/arac/su/cim")
    s.add_argument("--exact", action="store_true", help="tam ad, butun parametreleri dok")
    s.add_argument("--buckets", action="store_true", help="render bucket tablosunu da yaz")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_shader)

    s = sub.add_parser("mat", help="collision materyal tablosu (185 materyal + bayraklar)")
    s.add_argument("query", nargs="?", default="", help="ad parcasi, orn. 'metal' / 'glass'")
    s.add_argument("--index", type=int, help="tek bir materyal indeksini coz")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_mat)

    s = sub.add_parser("lodaudit", help="kendi ymap'lerini vanilla davranisiyla karsilastirir")
    s.set_defaults(func=cmd_lodaudit)

    s = sub.add_parser("lodchain", help="bir archetype'in GERCEK LOD zincirini vanilla'dan yurur")
    s.add_argument("name", help="archetype adi (parca da olur)")
    s.set_defaults(func=cmd_lodchain)

    s = sub.add_parser("flags", help="bayrak tamsayisini isimlere cozer (archetype/entity)")
    s.add_argument("value", help="bayrak degeri, orn. 1572872 veya 0x180008")
    s.add_argument("--entity", action="store_true",
                   help="ymap ENTITY bayragi olarak coz (varsayilan: archetype)")
    s.set_defaults(func=cmd_flags)

    s = sub.add_parser("pedmeta", help="ped kunyesi: klip sozlugu, expression, movement clipset")
    s.add_argument("query", help="ped adi (parca da olur)")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_pedmeta)

    s = sub.add_parser("weapon", help="silah kunyesi + bilesen/livery adlari")
    s.add_argument("query", help="silah adi, model adi ya da etiket")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--parts", "--parcalar", dest="parcalar", action="store_true",
                   help="list component and livery names / bilesen ve livery adlari")
    s.set_defaults(func=cmd_weapon)

    s = sub.add_parser("vehicle", help="arac kunyesi (handlingId, modkit, extra)")
    s.add_argument("query", help="arac adi, gorunen ad ya da uretici")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_vehicle)

    s = sub.add_parser("mlo", help="MLO ic mekanlari ve dunya konumlari")
    s.add_argument("query", help="ic mekan adi (parca da olur)")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--locations", "--konum", dest="konum", type=int, default=5,
                   help="locations shown per interior / ic mekan basina konum")
    s.set_defaults(func=cmd_mlo)

    s = sub.add_parser("ipl", help="IPL adi + sinir kutusu (RequestIpl dogrulamasi)")
    s.add_argument("query", help="ipl adi, grup ya da kategori")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_ipl)

    s = sub.add_parser("world", help="dunya nesneleri: aile + konum + ROTASYON")
    s.add_argument("--families", "--aileler", dest="aileler", action="store_true",
                   help="list families and counts / aile listesi ve sayilar")
    s.add_argument("--family", help="aile filtresi (atms, cctvs, seats ...)")
    s.add_argument("--model", help="model adi filtresi")
    s.add_argument("--near", help="x,y,z - bu noktanin yakinindakiler")
    s.add_argument("--radius", "--mesafe", dest="mesafe", type=float, default=50.0,
                   help="--near radius in metres / --near yaricapi (m)")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_world)

    s = sub.add_parser("framework", help="QBCore/ox/ESX export-event-callback indeksi")
    s.add_argument("query", nargs="?", help="ad ya da kaynak (bos: hepsi)")
    s.add_argument("--kind", choices=["export", "export_use", "event", "event_use",
                                      "callback", "callback_use", "command",
                                      "lib_module", "lib_use", "resource"])
    s.add_argument("--defs", "--tanim", dest="tanim", action="store_true",
                   help="definitions only (the authority) / yalniz TANIMLAR")
    s.add_argument("--check", "--denetle", dest="denetle", action="store_true",
                   help="cross-check usage against definitions (A/B/C/D report)")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_framework)

    s = sub.add_parser("doctor", help="sessiz hata kapisi: asseti oyuna sokmadan denetle")
    s.add_argument("paths", nargs="+",
                   help="dosya ya da klasor (.ycd .ytyp .ymap ... ya da .xml)")
    s.add_argument("-r", "--recursive", action="store_true",
                   help="klasorleri alt klasorlerle birlikte gez")
    s.add_argument("--level", choices=["fatal", "silent", "warn"], default="warn",
                   help="en dusuk bildirilecek siddet (varsayilan: warn = hepsi)")
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("timecycle", help="timecycle modifier: ic mekan neden karanlik")
    s.add_argument("name", nargs="?", help="modifier adi (bos: ozet)")
    s.add_argument("--ara", "--search", dest="ara", help="ada gore arama")
    s.add_argument("--mlo", help="bir MLO ytyp'inin odalari -> timecycle + ambient")
    s.add_argument("--param", help="parametre adi filtresi")
    s.add_argument("--kaynak", "--sources", dest="kaynak", action="store_true",
                   help="ayni adi tanimlayan TUM kaynaklari goster")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_timecycle)

    s = sub.add_parser("light", help="bir .ydr/.yft icindeki gomulu isiklari coz")
    s.add_argument("path", nargs="?", help=".ydr / .yft / .xml")
    s.add_argument("--tablo", "--table", dest="tablo", action="store_true",
                   help="olculen vanilla isik referansini yazdir")
    s.add_argument("--ham", "--raw", dest="ham", action="store_true",
                   help="cozumsuz, ham alanlar")
    s.set_defaults(func=cmd_light)

    s = sub.add_parser("diff", help="iki kaynagi DUGUM VARLIGI uzerinden karsilastir")
    s.add_argument("mine", help="senin dosyan (.yft .ydr .ycd ... ya da .xml)")
    s.add_argument("vanilla", help="vanilla muadili")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_diff)

    s = sub.add_parser("stats", help="indeks ozeti")
    s.set_defaults(func=cmd_stats)

    a = p.parse_args()
    set_lang(getattr(a, "lang", None))
    return a.func(a) or EXIT_OK


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BrokenPipeError:
        sys.exit(EXIT_OK)
    except Exception as exc:  # ic hata asla "sonuc yok" gibi gorunmesin
        print(f"IC HATA: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(EXIT_INTERNAL)
