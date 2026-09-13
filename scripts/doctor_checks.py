#!/usr/bin/env python3
"""doctor_checks.py — per-format checks (.ycd, .ytyp / MLO).

Every check rests on a rule measured on REAL files; what the measurement was is
written next to the rule. A rule without a measurement is NOT ADDED -- a gate
that produces false positives is worse than no gate.
"""
from __future__ import annotations

from doctor_common import (FATAL, SILENT, WARN, FRAME_SECONDS, Report, _hash_empty,  # noqa: F401
                          _attr_float, _localize)

# =============================================================================
# .ycd  — clip dictionary
# =============================================================================
# Structure (verified on vanilla mp_safehousewine@.ycd / move_m@brave.ycd):
#   ClipDictionary
#     Clips/Item      : Hash, Name, Type(value=Animation|AnimationList),
#                       AnimationHash          (Type=Animation)
#                       Animations/Item/AnimationHash  (Type=AnimationList)
#     Animations/Item : Hash, Unknown10, FrameCount, BoneIds, Sequences

def _clip_anim_hashes(clip):
    """ALL animation hashes a clip references (both types)."""
    single = clip.findtext("AnimationHash")
    if single and single.strip():
        yield single.strip()
    anim_list = clip.find("Animations")
    if anim_list is not None:
        for it in anim_list:
            h = it.findtext("AnimationHash")
            if h and h.strip():
                yield h.strip()


def check_ycd(root, path, report, compiled=False):
    clips = root.findall("./Clips/Item")
    anims = root.findall("./Animations/Item")

    if not clips:
        report.add(SILENT, "YCD000", path, _localize({
            "tr": "Sozlukte hic klip yok.",
            "en": "Dictionary contains no clips."}))
        return

    anim_hashes = set()
    anim_duration = {}
    seen_anim = {}
    for i, a in enumerate(anims):
        h = (a.findtext("Hash") or "").strip()
        if _hash_empty(h):
            report.add(SILENT, "YCD002", path, _localize({
                "tr": f"Animasyon #{i} <Hash> bos -> hash 0. Ayni anahtara "
                      f"dusen animasyonlar birbirini EZER.",
                "en": f"Animation #{i} has empty <Hash> -> hash 0. Animations "
                      f"colliding on one key OVERWRITE each other."}), "Sollumz Clip panel -> Hash")
            continue
        if h in seen_anim:
            report.add(SILENT, "YCD004", path, _localize({
                "tr": f"Animasyon hash tekrari: {h} (#{seen_anim[h]} ve #{i}). "
                      f"Sonuncusu oncekini ezer.",
                "en": f"Duplicate animation hash: {h} (#{seen_anim[h]} and #{i}). "
                      f"The last one overwrites the earlier."}))
        seen_anim[h] = i
        anim_hashes.add(h)
        anim_duration[h] = _attr_float(a.find("Duration"))

        # 0-channel pitfall: if Sollumz is given the Object, the file is built,
        # frames/duration are right, there is NO BONE DATA (724 bytes vs 59 KB).
        bone_ids = a.find("BoneIds")
        sequences = a.find("Sequences")
        if bone_ids is not None and len(bone_ids) == 0:
            report.add(SILENT, "YCD006", path, _localize({
                "tr": f"Animasyon {h}: BoneIds BOS -> 0 kemik kanali. Dosya "
                      f"olusur, sure dogrudur, poz hic degismez.",
                "en": f"Animation {h}: BoneIds is EMPTY -> 0 bone channels. The "
                      f"file builds, duration looks right, the pose never moves."}),
                _localize({"tr": "Sollumz Animation.target_id ARMATURE DATA olmali (arm.data), Object degil.", "en": "Sollumz Animation.target_id must be the ARMATURE DATA-BLOCK (arm.data), not the Object."}))
        elif sequences is not None and len(sequences) == 0:
            report.add(SILENT, "YCD006", path, _localize({
                "tr": f"Animasyon {h}: Sequences BOS -> veri yok.",
                "en": f"Animation {h}: Sequences is EMPTY -> no data."}))

        fc = a.find("FrameCount")
        if fc is not None and (fc.get("value") or "0").strip() in ("0", "0.0"):
            report.add(SILENT, "YCD007", path, _localize({
                "tr": f"Animasyon {h}: FrameCount 0.",
                "en": f"Animation {h}: FrameCount is 0."}))

    seen_clip = {}
    used = set()
    unresolved = []   # (clip, unresolved_anim_hash)
    overrun = []      # (clip, overrun in seconds)
    no_ref = 0        # number of clips that carry no AnimationHash
    for i, c in enumerate(clips):
        h = (c.findtext("Hash") or "").strip()
        name = (c.findtext("Name") or "").strip()
        label = h or name or f"#{i}"

        if _hash_empty(h):
            report.add(SILENT, "YCD001", path, _localize({
                "tr": f"Klip '{name or i}' <Hash> bos -> klibin ADI YOK. "
                      f"TaskPlayAnim/PlayEntityAnim onu BULAMAZ. Cok klipli "
                      f"sozlukte klipler ayrica birbirini ezer.",
                "en": f"Clip '{name or i}' has empty <Hash> -> the clip HAS NO NAME. "
                      f"TaskPlayAnim/PlayEntityAnim CANNOT find it. In a multi-clip "
                      f"dictionary the clips also overwrite each other."}), "Sollumz Clip panel -> Hash")
        else:
            if h in seen_clip:
                report.add(SILENT, "YCD003", path, _localize({
                    "tr": f"Klip hash tekrari: {h} (#{seen_clip[h]} ve #{i}).",
                    "en": f"Duplicate clip hash: {h} (#{seen_clip[h]} and #{i})."}))
            seen_clip[h] = i

        refs = list(_clip_anim_hashes(c))
        if not refs:
            no_ref += 1
            continue
        for r in refs:
            used.add(r)
            if anim_hashes and r not in anim_hashes:
                unresolved.append((label, r))
                continue
            end = _attr_float(c.find("EndTime"))
            if end is None:
                end = _attr_float(c.find("Duration"))
            duration = anim_duration.get(r)
            if end is not None and duration:
                excess = end - duration
                if excess > 1e-4:
                    overrun.append((label, excess))

    # --- unresolved reference: the clip plays, nothing moves ---
    for label, r in unresolved[:8]:
        report.add(SILENT, "YCD005", path, _localize({
            "tr": f"Klip '{label}' -> {r} animasyonu sozlukte YOK. "
                  f"Klip oynar, hicbir sey hareket etmez.",
            "en": f"Clip '{label}' -> animation {r} is NOT in the dictionary. "
                  f"The clip plays, nothing moves."}))
    if len(unresolved) > 8:
        report.add(SILENT, "YCD005", path, _localize({
            "tr": f"...ve {len(unresolved) - 8} klip daha cozulmeyen referans tasiyor.",
            "en": f"...and {len(unresolved) - 8} more clips carry unresolved references."}))

    # --- positional matching (Sollumz form) ---
    # Sollumz does NOT WRITE an AnimationHash into a Type=Animation clip; the
    # compiler pairs clip[i] with animation[i] by position. That alone is not an
    # error -- but Sollumz sorts clips and animations ALPHABETICALLY BY OBJECT
    # NAME, not by creation order. If the counts disagree, the pairing is
    # certainly wrong.
    if no_ref:
        if compiled:
            # In a COMPILED file the link must already be resolved. An empty
            # AnimationHash here means hash 0: the clip runs, no animation is found.
            # (Measured: the same dictionary's 2 August build had 63/63 hashes
            #  filled, its 3 August build 63/63 EMPTY -- same converter, same reader.)
            report.add(SILENT, "YCD009", path, _localize({
                "tr": f"DERLENMIS dosyada {no_ref}/{len(clips)} klibin AnimationHash'i "
                      f"BOS -> hash 0. Klip cagrilir, hicbir animasyon bulunmaz. "
                      f"Kaynak XML'de konumsal eslesme normaldir; derlenmis dosyada "
                      f"bagin COZULMUS olmasi gerekir.",
                "en": f"In this COMPILED file {no_ref}/{len(clips)} clips have an EMPTY "
                      f"AnimationHash -> hash 0. The clip is invoked, no animation is "
                      f"found. Positional matching is normal in the source XML; in a "
                      f"compiled file the link must already be RESOLVED."}),
                "res_to_xml.ps1 + Sollumz Clip panel -> Hash")
        elif no_ref == len(clips) and len(clips) == len(anims):
            report.add(WARN, "YCD009", path, _localize({
                "tr": f"Hicbir klip AnimationHash tasimiyor ({no_ref} klip) -> eslesme "
                      f"KONUMSAL. Sayilar tutuyor ({len(clips)}={len(anims)}), ama "
                      f"Sollumz alfabetik dizer: hangi klibin hangi animasyona "
                      f"dustugunu FrameCount ile dogrula.",
                "en": f"No clip carries an AnimationHash ({no_ref} clips) -> matching is "
                      f"POSITIONAL. Counts agree ({len(clips)}={len(anims)}), but "
                      f"Sollumz sorts alphabetically: verify which clip landed on which "
                      f"animation via FrameCount."}))
        else:
            report.add(SILENT, "YCD009", path, _localize({
                "tr": f"{no_ref} klip AnimationHash tasimiyor ve sayilar tutmuyor "
                      f"(klip={len(clips)}, animasyon={len(anims)}) -> konumsal "
                      f"eslesme YANLIS baglanir.",
                "en": f"{no_ref} clips carry no AnimationHash and the counts disagree "
                      f"(clips={len(clips)}, animations={len(anims)}) -> positional "
                      f"matching WILL bind the wrong pairs."}))

    # --- clip window exceeds the animation ---
    if overrun:
        worst = max(f for _, f in overrun)
        frames = worst / FRAME_SECONDS
        level = WARN if frames <= 1.5 else SILENT
        report.add(level, "YCD010", path, _localize({
            "tr": f"{len(overrun)} klibin EndTime'i bagli animasyonun Duration'ini asiyor "
                  f"(en fazla {worst:.4f} s = {frames:.2f} kare). Vanilla'da bu fark hic "
                  f"pozitif olmaz; klip animasyonda OLMAYAN bir kareyi istiyor."
                  + ("" if level == WARN else " 1 kareyi astigi icin eslesme de supheli."),
            "en": f"{len(overrun)} clip(s) have an EndTime beyond the linked animation's "
                  f"Duration (worst {worst:.4f} s = {frames:.2f} frames). In vanilla this "
                  f"difference is never positive; the clip asks for a frame the animation "
                  f"DOES NOT have."
                  + ("" if level == WARN else " Beyond one frame, the pairing is suspect too.")}),
            f"Duration == (FrameCount-1)/30")

    # In the positional form no clip carries a reference -> orphan detection is meaningless.
    if not no_ref:
        orphans = sorted(anim_hashes - used)
        for h in orphans[:5]:
            report.add(WARN, "YCD008", path, _localize({
                "tr": f"Animasyon {h} sahipsiz: hicbir klip kullanmiyor.",
                "en": f"Animation {h} is orphaned: no clip references it."}))
        if len(orphans) > 5:
            report.add(WARN, "YCD008", path, _localize({
                "tr": f"...ve {len(orphans) - 5} sahipsiz animasyon daha.",
                "en": f"...and {len(orphans) - 5} more orphaned animations."}))


# =============================================================================
# .ytyp — archetype definitions
# =============================================================================
# Structure (verified on a custom prop .ytyp.xml):
#   CMapTypes/archetypes/Item[@type=CBaseArchetypeDef|CTimeArchetypeDef|
#                             CMloArchetypeDef]
#     lodDist, flags, bbMin, bbMax, name, assetName, extensions
#     (MLO) entities/Item[@type=CEntityDef]/flags, rooms/Item/attachedObjects

# MLO entity flag. If the ymap value (1572872) is used inside an MLO the object
# SILENTLY never spawns: bit 8 = "LOD in Parented YMAP", there is no parent map.
YMAP_FLAG = 1572872
BIT_LOD_PARENT_MAP = 8

# MEASURED: 79 vanilla interior ytyps -> 118 MLOs, 18,799 entities.
#   * 1572872                               : 0 times
#   * ANY flag that sets bit 8              : 0 times  (not a single entity)
#   * the same value without the bit 1572864: 2272 times (very common)
#   * most common values: 18350082 (7578), 18350080 (3860), 1572864 (2272)
# So the check looks at the BIT, not at one number: inside vanilla MLOs bit 8 is
# never used, so every value that sets it is unusual.
# There is NO single "right number" -> the common value is given as a reference,
# not as a recipe.
MLO_FLAG_COMMON = 18350082


def check_ytyp(root, path, report, compiled=False):
    archetypes = root.findall("./archetypes/Item")
    if not archetypes:
        report.add(SILENT, "YTY000", path, _localize({
            "tr": "ytyp'de hic archetype yok.",
            "en": "The ytyp contains no archetypes."}))
        return

    name_mismatch, unnamed, no_lod, degenerate = [], [], [], []
    for a in archetypes:
        arch_type = a.get("type") or "?"
        name = (a.findtext("name") or "").strip()
        label = name or "<unnamed>"

        if not name:
            unnamed.append(arch_type)

        lod = a.find("lodDist")
        if lod is None or (_attr_float(lod) or 0) <= 0:
            no_lod.append(label)

        # An MLO archetype's bbox is 0,0,0 in vanilla (measured: both MLOs of
        # v_int_10). The interior's bounds come from the rooms, not from the
        # archetype box -> the degenerate box check does NOT APPLY to MLOs.
        bmin, bmax = a.find("bbMin"), a.find("bbMax")
        if arch_type != "CMloArchetypeDef" and bmin is not None and bmax is not None:
            try:
                mn = [float(bmin.get(k) or 0) for k in "xyz"]
                mx = [float(bmax.get(k) or 0) for k in "xyz"]
                if mn == mx:
                    degenerate.append(label)
            except ValueError:
                pass

        asset = (a.findtext("assetName") or "").strip()
        if name and asset and name != asset and arch_type == "CBaseArchetypeDef":
            name_mismatch.append(label)

        _check_extensions(a, label, path, report)

        if arch_type == "CMloArchetypeDef":
            _check_mlo(a, label, path, report)

    n = len(archetypes)
    if unnamed:
        report.add(SILENT, "YTY006", path, _localize({
            "tr": f"{len(unnamed)}/{n} archetype'in <name> alani bos -> adreslenemez.",
            "en": f"{len(unnamed)}/{n} archetype(s) have an empty <name> -> unaddressable."}))
    if no_lod:
        report.add(SILENT, "YTY004", path, _localize({
            "tr": f"{len(no_lod)}/{n} archetype'ta lodDist 0/eksik -> obje hicbir "
                  f"mesafede cizilmez. {', '.join(no_lod[:4])}"
                  + (f" ve {len(no_lod) - 4} tane daha." if len(no_lod) > 4 else ""),
            "en": f"{len(no_lod)}/{n} archetype(s) have lodDist 0/missing -> the object "
                  f"never draws. {', '.join(no_lod[:4])}"
                  + (f" and {len(no_lod) - 4} more." if len(no_lod) > 4 else "")}),
            "assetdb.py lod")
    if degenerate:
        report.add(SILENT, "YTY003", path, _localize({
            "tr": f"{len(degenerate)}/{n} archetype'ta bbMin == bbMax (dejenere sinir "
                  f"kutusu) -> obje uzakta titrer ve kaybolur. "
                  f"{', '.join(degenerate[:4])}"
                  + (f" ve {len(degenerate) - 4} tane daha." if len(degenerate) > 4 else ""),
            "en": f"{len(degenerate)}/{n} archetype(s) have bbMin == bbMax (degenerate "
                  f"bounding box) -> the object flickers at distance and vanishes. "
                  f"{', '.join(degenerate[:4])}"
                  + (f" and {len(degenerate) - 4} more." if len(degenerate) > 4 else "")}))

    # name != assetName: NOT FORBIDDEN (an archetype may show another drawable)
    # but UNUSUAL -- measured: vanilla v_int_10 + v_int_47, in 89 of 89
    # CBaseArchetypeDefs the two are the SAME (0% deviation). Hence WARN, and a
    # SINGLE line per file: one line per archetype produced 300+ lines.
    if name_mismatch:
        report.add(WARN, "YTY005", path, _localize({
            "tr": f"{len(name_mismatch)} archetype'ta assetName, name'den farkli "
                  f"(vanilla olcumu: 89/89 ayni). Kasitliysa sorun yok; degilse "
                  f"archetype var olmayan bir drawable'i gosteriyor olabilir.",
            "en": f"{len(name_mismatch)} archetype(s) have assetName differing from name "
                  f"(vanilla measurement: 89/89 identical). Fine if deliberate; "
                  f"otherwise the archetype may point at a drawable that does not exist."}))


def _check_extensions(archetype, label, path, report):
    ext = archetype.find("extensions")
    if ext is None:
        return
    for it in ext:
        ext_type = it.get("type") or ""
        if "Expression" in ext_type:
            value = (it.findtext("expressionDictionaryName") or "") + " " + \
                    (it.findtext("expressionName") or "")
            if "pack:/" in value or ".expr" in value:
                report.add(SILENT, "YTY002", path, _localize({
                    "tr": f"{label}: Expression extension 'pack:/...' formunda. "
                          f"CIPLAK AD yazilmali, yoksa expression baglanmaz ve "
                          f"collision animasyonu takip etmez.",
                    "en": f"{label}: Expression extension uses the 'pack:/...' form. "
                          f"It must be the BARE NAME, otherwise the expression never "
                          f"binds and collision will not follow the animation."}), "/yed")


def _check_mlo(archetype, label, path, report):
    entities = archetype.findall("./entities/Item")
    rooms = archetype.findall("./rooms/Item")

    # Two lists own an entity: ROOMS *and* PORTALS.
    # Not counting portals produces false positives -- measured: in both MLOs
    # of vanilla v_int_10 exactly 2 entities are attached to a portal, not to a
    # room. Looking only at rooms reports them as "in no room" and a correct
    # file looks broken.
    owned = set()
    for container in list(rooms) + archetype.findall("./portals/Item"):
        raw = (container.findtext("attachedObjects") or "").replace(",", " ").split()
        for s in raw:
            try:
                owned.add(int(s))
            except ValueError:
                pass

    orphans = []
    ymap_flagged = []
    for i, e in enumerate(entities):
        flag = e.find("flags")
        if flag is not None:
            try:
                v = int(float(flag.get("value") or 0))
            except ValueError:
                v = 0
            if v & BIT_LOD_PARENT_MAP:
                ymap_flagged.append((i, v))

        if owned and i not in owned:
            orphans.append((i, (e.findtext("archetypeName") or "?").strip()))

    if ymap_flagged:
        values = sorted({v for _, v in ymap_flagged})
        first = ", ".join(f"#{i}" for i, _ in ymap_flagged[:6])
        rest = len(ymap_flagged) - 6
        report.add(SILENT, "YTY001", path, _localize({
            "tr": f"{label}: {len(ymap_flagged)}/{len(entities)} entity 8. biti "
                  f"('LOD ust haritada') set eden bir bayrak tasiyor: "
                  f"{', '.join(str(d) for d in values)}. OLCULDU: 118 vanilla MLO / "
                  f"18.799 entity icinde bu bit HIC kullanilmaz (0 kez); bitsiz hali "
                  f"1572864 ise 2272 kez gecer. Ust harita olmadigi icin entity "
                  f"SESSIZCE dusurulur. Yaygin MLO degeri {MLO_FLAG_COMMON} -- "
                  f"sayiyi kopyalama, coz. {first}"
                  + (f" ve {rest} tane daha." if rest > 0 else ""),
            "en": f"{label}: {len(ymap_flagged)}/{len(entities)} entities carry a flag "
                  f"with bit 8 ('LOD in parented ymap') set: "
                  f"{', '.join(str(d) for d in values)}. MEASURED: across 118 vanilla "
                  f"MLOs / 18,799 entities this bit is NEVER used (0 occurrences), while "
                  f"the same value without it (1572864) appears 2272 times. With no "
                  f"parent map the entity is SILENTLY dropped. Common MLO value is "
                  f"{MLO_FLAG_COMMON} -- decode it, do not copy it. {first}"
                  + (f" and {rest} more." if rest > 0 else "")}),
            f"assetdb.py flags {values[0]} --entity")

    if orphans:
        sample = ", ".join(f"#{i} ({name})" for i, name in orphans[:4])
        rest = len(orphans) - 4
        report.add(SILENT, "YTY007", path, _localize({
            "tr": f"{label}: {len(orphans)}/{len(entities)} entity hicbir odanin ya "
                  f"da portalin attachedObjects listesinde YOK -> oyun onlari HIC "
                  f"OLUSTURMAZ, hata da vermez. {sample}"
                  + (f" ve {rest} tane daha." if rest > 0 else ""),
            "en": f"{label}: {len(orphans)}/{len(entities)} entities are in NO room's "
                  f"or portal's attachedObjects list -> the game NEVER creates them and "
                  f"reports no error. {sample}"
                  + (f" and {rest} more." if rest > 0 else "")}))



# =============================================================================
# Drawable / Fragment — embedded lights
# =============================================================================
# Lights sit under <root>/Lights; in the same place for both a .ydr (Drawable)
# and a .yft (Fragment) root (measured: prop_worklight_01a.yft ->
# Fragment/Lights=1, Fragment/Drawable/Lights ABSENT). Every defect here is
# SILENT: the file compiles, the game gives no error, the light simply does not
# come on.


def check_drawable(root, path, report, compiled=False):
    import light as _light

    lights = _light.read_lights(root)
    if not lights:
        return  # no lights -> nothing to check for this module either

    never_on, zero, no_range, cone = [], [], [], []
    for idx, i in enumerate(lights):
        if not _light.active_hours(i["TimeFlags"]):
            never_on.append(idx)
        if i["Intensity"] is not None and i["Intensity"] <= 0:
            zero.append(idx)
        if i["Falloff"] is not None and i["Falloff"] <= 0:
            no_range.append(idx)
        if i["Type"] == "Spot":
            inner, outer = i["ConeInnerAngle"], i["ConeOuterAngle"]
            if outer is not None and outer <= 0:
                cone.append(f"#{idx} outer 0")
            elif inner is not None and outer is not None and inner > outer:
                cone.append(f"#{idx} inner{inner:g}>outer{outer:g}")

    if never_on:
        # LEVEL WARN, NOT SILENT -- and this is a deliberate step back.
        # The first version reported "the light NEVER comes on" as SILENT; the
        # basis was that TimeFlags 0 never appeared in a 53-light sample. When
        # the full corpus was measured (72,539 lights) the value 0 appeared
        # 8 times, and where it appeared were interior lamp props. So BOTH
        # readings, "0 = never on" and "0 = no time restriction", fit the data.
        # Reporting something the data cannot resolve as if it were certain
        # would be exactly the failure the tool tries to prevent.
        report.add(WARN, "LGT001", path, _localize({
            "tr": f"{len(never_on)}/{len(lights)} isikta TimeFlags 0 (hicbir saat biti). "
                  f"Vanilla'da cok nadir: 72539 isikta 8 kez (%0.011). '0 = hic "
                  f"yanmaz' mi '0 = saat kisiti yok' mu oldugu bu veriden "
                  f"COZULEMEZ -- oyunda gece ve gunduz test et. Isik #{never_on[:5]}",
            "en": f"{len(never_on)}/{len(lights)} light(s) have TimeFlags 0 (no hour bit). "
                  f"Very rare in vanilla: 8 out of 72539 lights (0.011%). Whether 0 "
                  f"means 'never lights' or 'no time restriction' CANNOT be resolved "
                  f"from this data -- test in game at night and at noon. "
                  f"Light #{never_on[:5]}"}),
            "assetdb.py light --table")
    if zero:
        report.add(SILENT, "LGT002", path, _localize({
            "tr": f"{len(zero)}/{len(lights)} isikta Intensity 0 -> isik yayilmaz. "
                  f"Isik #{zero[:5]}",
            "en": f"{len(zero)}/{len(lights)} light(s) have Intensity 0 -> no light is "
                  f"emitted. Light #{zero[:5]}"}))
    if no_range:
        report.add(SILENT, "LGT003", path, _localize({
            "tr": f"{len(no_range)}/{len(lights)} isikta Falloff 0 -> menzil yok, isik "
                  f"hicbir yuzeye ulasmaz. Isik #{no_range[:5]}",
            "en": f"{len(no_range)}/{len(lights)} light(s) have Falloff 0 -> no range, "
                  f"the light reaches no surface. Light #{no_range[:5]}"}))
    if cone:
        report.add(SILENT, "LGT004", path, _localize({
            "tr": f"{len(cone)} spot isikta koni gecersiz: {', '.join(cone[:4])}",
            "en": f"{len(cone)} spot light(s) have an invalid cone: {', '.join(cone[:4])}"}))


# Root tag -> check function (doctor.py imports it).
CHECKERS = {
    "Drawable": check_drawable,
    "Fragment": check_drawable,
    "ClipDictionary": check_ycd,
    "CMapTypes": check_ytyp,
}

# A double hyphen inside an XML comment makes the file unparseable. The game gives NO ERROR,
