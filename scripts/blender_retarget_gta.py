"""blender_retarget_gta.py — yabanci iskeletli animasyonu GTA V ped rig'ine aktar.

Blender'in Text Editor'unde ac ve Run Script. Ya da:
    blender --background --python blender_retarget_gta.py

NE YAPAR
========
Sketchfab / Mixamo / Rigify / Daz / UE gibi BASKA bir iskelete yapilmis
animasyonu GTA V ped iskeletine (mp_m_freemode_01, 128 kemik) tasir ve
FiveM'e uygun hale getirir:

  1. Kemik adi eslemesi (coklu rig konvansiyonu otomatik taninir)
  2. REFERANS POZ ofseti ile delta transfer  <-- matematigin dogru kismi
  3. Root motion'u hips'ten cikarip MOVER track'ine tasima
  4. 30 fps'e zorlama
  5. Dogrulama raporu (ayak kaymasi, dongusellik, yasakli kanallar)

OLCULMUS GERCEKLER (bu araci sekillendiren, references/ dosyasinda ayrintili)
============================================================================
* GTA kemiginin uzunluk ekseni LOCAL +X. Parent-space child yonu tam (1,0,0).
  Blender ayni kemikleri +Y'de gosterir (Sollumz eksen donusumu yapar).
* GTA rest pose'u T-POSE DEGIL: ust kol yataydan 57 derece asagida (A-pose).
  Mixamo T-pose'dur. Bu fark goz ardi edilirse kollar 144 dereceye kadar sapar.
* Dunya-yonelimi eslemesi YANLIS sonuc verir: olcumde her kemikte rig'in roll
  konvansiyonu farki kadar (deneyde tam 30 derece), kollarda 144 derece hata.
  Referans-poz ofsetli delta transfer ise gidis-donuste 0.000 derece verdi.
* GTA lokomosyonu YERINDE uretilir: kosu klibinde ayak anim-uzayi suruklenmesi
  0.000 m, tum yol (3.656 m / 1.73 s) MOVER track'inde. Mixamo'da yol hips'e
  gomuludur -> tasinmazsa ped yerinde kayar ya da iki kat hareket eder.
* Klipler 30 fps. Blender sahnesi varsayilan 24'te kalir -> %25 zamanlama hatasi.
* SKEL_Pelvis ve SKEL_Spine_Root rest'te +-90 Y cevirici; 84 klip olcumunde
  sapmalari 0.0 derece. ASLA keyframe'lenmez -> kalca donusu SKEL_ROOT'a gider.
* Klipler uzuvlara translation ve scale YAZMAZ (sadece rotasyon).
"""

import bpy
import math
from mathutils import Matrix, Vector

# ---------------------------------------------------------------- AYARLAR
GTA_ARMATURE = ""     # bos -> otomatik bul (SKEL_ROOT iceren armature)
SRC_ARMATURE = ""     # bos -> otomatik bul (digeri)
BAKE_FINGERS = True
BAKE_MOVER = True     # hips yatay yolunu mover'a tasi + kemigi yerinde birak
FPS = 30
# "align" = kaynak kemik yonu hedefe otomatik dondurulur (T-pose/A-pose farkini
# kapatir, deterministik). "rest" = duz rest ofseti. "pose" = kaynagin o anki pozu.
OFFSET_MODE = "align"

# ------------------------------------------------- KEMIK ESLEMESI
# GTA adi -> yabanci rig aday adlari (prefix'ler otomatik soyulur).
# Parmak eslemesi rest offset'lerinden dogrulandi: hand'a en yakin zincir
# (0.026 m) basparmak; Finger10..40 elin -Y yonunde ilerler = index..pinky.
BONE_MAP = {
    # kalca donusu SKEL_ROOT'a gider: Pelvis ve Spine_Root donmez (olculdu 0.0 derece)
    "SKEL_ROOT":        ["Hips", "pelvis", "Bip01_Pelvis", "root", "Armature_Hips"],
    "SKEL_Spine0":      ["Spine", "spine_01", "Bip01_Spine"],
    "SKEL_Spine1":      ["Spine1", "spine_02", "Bip01_Spine1"],
    "SKEL_Spine2":      ["Spine2", "spine_03", "Bip01_Spine2"],
    "SKEL_Spine3":      ["Spine3", "spine_04", "chest", "Bip01_Spine3"],
    "SKEL_Neck_1":      ["Neck", "neck_01", "Bip01_Neck"],
    "SKEL_Head":        ["Head", "head", "Bip01_Head"],

    "SKEL_L_Clavicle":  ["LeftShoulder", "clavicle_l", "Bip01_L_Clavicle", "shoulder.L"],
    "SKEL_L_UpperArm":  ["LeftArm", "upperarm_l", "Bip01_L_UpperArm", "upper_arm.L"],
    "SKEL_L_Forearm":   ["LeftForeArm", "lowerarm_l", "Bip01_L_Forearm", "forearm.L"],
    "SKEL_L_Hand":      ["LeftHand", "hand_l", "Bip01_L_Hand", "hand.L"],
    "SKEL_R_Clavicle":  ["RightShoulder", "clavicle_r", "Bip01_R_Clavicle", "shoulder.R"],
    "SKEL_R_UpperArm":  ["RightArm", "upperarm_r", "Bip01_R_UpperArm", "upper_arm.R"],
    "SKEL_R_Forearm":   ["RightForeArm", "lowerarm_r", "Bip01_R_Forearm", "forearm.R"],
    "SKEL_R_Hand":      ["RightHand", "hand_r", "Bip01_R_Hand", "hand.R"],

    "SKEL_L_Thigh":     ["LeftUpLeg", "thigh_l", "Bip01_L_Thigh", "thigh.L"],
    "SKEL_L_Calf":      ["LeftLeg", "calf_l", "Bip01_L_Calf", "shin.L"],
    "SKEL_L_Foot":      ["LeftFoot", "foot_l", "Bip01_L_Foot", "foot.L"],
    "SKEL_L_Toe0":      ["LeftToeBase", "ball_l", "Bip01_L_Toe0", "toe.L"],
    "SKEL_R_Thigh":     ["RightUpLeg", "thigh_r", "Bip01_R_Thigh", "thigh.R"],
    "SKEL_R_Calf":      ["RightLeg", "calf_r", "Bip01_R_Calf", "shin.R"],
    "SKEL_R_Foot":      ["RightFoot", "foot_r", "Bip01_R_Foot", "foot.R"],
    "SKEL_R_Toe0":      ["RightToeBase", "ball_r", "Bip01_R_Toe0", "toe.R"],
}
FINGER_MAP = {}
for _s, _S in (("L", "Left"), ("R", "Right")):
    for _gi, _digit in ((0, "Thumb"), (1, "Index"), (2, "Middle"), (3, "Ring"), (4, "Pinky")):
        for _j in (0, 1, 2):
            FINGER_MAP[f"SKEL_{_s}_Finger{_gi}{_j}"] = [
                f"{_S}Hand{_digit}{_j+1}",
                f"{_digit.lower()}_{_gi and '0' or '0'}{_j+1}_{_s.lower()}",
                f"f_{_digit.lower()}.0{_j+1}.{_s}",
            ]

# GTA'da bulunan ama klibe ASLA yazilmamasi gerekenler (expression surer)
EXPRESSION_DRIVEN_PREFIX = ("MH_", "RB_", "SM_", "EO_", "SPR_", "FB_", "FACIAL_")
NEVER_KEY = ("SKEL_Pelvis", "SKEL_Spine_Root")


# ---------------------------------------------------------------- yardimci
def log(*a):
    print("[retarget]", *a)


def find_armatures():
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    gta = src = None
    if GTA_ARMATURE:
        gta = bpy.data.objects.get(GTA_ARMATURE)
    if SRC_ARMATURE:
        src = bpy.data.objects.get(SRC_ARMATURE)
    if gta is None:
        for a in arms:
            if "SKEL_ROOT" in a.data.bones:
                gta = a
                break
    if src is None:
        for a in arms:
            if a is not gta:
                src = a
                break
    return gta, src


def strip(name):
    """mixamorig:LeftArm -> LeftArm ; Armature|Hips -> Hips"""
    for sep in (":", "|"):
        if sep in name:
            name = name.rsplit(sep, 1)[-1]
    return name


def build_pairs(gta, src):
    """GTA kemigi -> kaynak kemigi. Once tam ad, sonra prefix'siz, sonra kucuk harf."""
    full = dict(BONE_MAP)
    if BAKE_FINGERS:
        full.update(FINGER_MAP)
    by_exact = {b.name: b.name for b in src.data.bones}
    by_strip = {}
    by_lower = {}
    for b in src.data.bones:
        by_strip.setdefault(strip(b.name), b.name)
        by_lower.setdefault(strip(b.name).lower(), b.name)
    pairs, missing = {}, []
    for gname, cands in full.items():
        if gname not in gta.data.bones:
            continue
        hit = None
        for c in cands:
            hit = by_exact.get(c) or by_strip.get(c) or by_lower.get(c.lower())
            if hit:
                break
        if hit:
            pairs[gname] = hit
        else:
            missing.append(gname)
    return pairs, missing


def rest3(obj, name):
    return obj.data.bones[name].matrix_local.to_3x3()


def bone_dir(obj, name):
    """Kemigin ANATOMIK rest yonu = kendi head'inden COCUGUNUN head'ine.

    DIKKAT — olculmus tuzak: Sollumz'un import ettigi GTA ped armature'unda
    HER kemik 0.05 m sabit uzunlukta, use_connect=False ve yonu anatomik
    DEGIL (bone.vector hepsinde ~ +-Y cikar, bone.length hepsinde 0.05).
    Kemik KONUMLARI dogru, yon/uzunluk/roll dogru DEGIL. Bu yuzden
    bone.vector / bone.length / matrix_local'in Y ekseni buradaki anatomi
    icin KULLANILAMAZ; head->cocugun head'i kullanilir.
    Ornek: SKEL_L_UpperArm -> bone.vector 1.2 derece derken gercek anatomik
    yon 57 derece (A-pose).

    OLCULMUS IKI TUZAK — ikisi de sessizce bozuk poz uretir:

    1) "en uzak cocuk" HELPER kemige dusebilir. Olculdu (mp_m_freemode_01):
       SKEL_L_UpperArm -> MH_L_Elbow 0.2750 m, SKEL_L_Forearm 0.2742 m.
       Helper 0.8 mm farkla kazaniyor ve anatomi YARDIMCI kemikten hesaplaniyor.
       SKEL_Head daha beter: cocuklari MH_Hair_Scale / MH_Hair_Crown (0.0931 m,
       SACA dogru YUKARI) -> kafa retarget'ta geriye atiliyordu.
    2) Yaprak kemikte `b.vector`'e dusmek. Sollumz rig'inde bone.vector
       anatomik DEGIL (kolda 56 derece sapma), FBX yapraginda ise tamamen
       uydurma. Uydurma yon, yon YOKLUGUNDAN daha kotudur.

    Cozum iki kademeli:
      1. helper/twist elenmis GERCEK anatomik cocuk
      2. yoksa EBEVEYNDEN GELEN yon (uzuv devam eder: parmak ucu parmagi,
         kafa boynu, ayak parmagi ayagi surdurur)
      3. o da yoksa None -> cagiran taraf align'i UYGULAMAZ (duz rest ofseti)

    Olculen kazanc: SKEL_Head 113.6 -> 37.0 derece, SKEL_L_Toe0 85.9 -> 73.7
    (vanilla bant 79'u artik asmiyor), yaprak kemiklerde eklem acisi farki 0.00.
    """
    HELPER_GTA = ("MH_", "RB_", "SM_", "EO_", "SPR_", "FB_", "IK_", "PH_", "FACIAL_")
    HELPER_SRC = ("ik_",)
    SKIP_SRC = ("_twist_",)

    bones = obj.data.bones
    is_gta = "SKEL_ROOT" in bones
    helpers = HELPER_GTA if is_gta else HELPER_SRC
    skips = () if is_gta else SKIP_SRC

    b = bones[name]
    kids = [c for c in b.children
            if not c.name.startswith(helpers) and not any(s in c.name for s in skips)]
    if kids:
        c = max(kids, key=lambda k: (k.head_local - b.head_local).length)
        d = c.head_local - b.head_local
        if d.length > 1e-6:
            return d.normalized()

    if b.parent:
        d = b.head_local - b.parent.head_local
        if d.length > 1e-6:
            return d.normalized()

    return None


def compute_offsets(gta, src, pairs, mode="align"):
    """Q_off = (kaynak REFERANS yonelimi)^-1 @ (hedef REST yonelimi)

    mode:
      "align" (VARSAYILAN, deterministik) — kaynak kemigin REST YONU hedefin
          REST YONUNE dondurulur, sonra ofset rest'ten hesaplanir. Boylece
          T-pose/A-pose farki (GTA'da 57 derece) otomatik kapanir ve sonuc
          kaynagin o anki karesine BAGLI DEGILDIR.
      "rest"  — duz rest ofseti. Iki rig'in rest'i zaten benziyorsa dogru;
          T-pose kaynakta kollari 57 derece asagi biaslar.
      "pose"  — kaynagin O ANKI pozu referans. Kaynagi ELLE hedefin rest
          pozuna benzettiysen kullan. Dikkat: hangi karede oldugun sonucu
          degistirir, o yuzden varsayilan degil.

    OLCULMUS DAVRANIS (test edildi, 53 kemik):
      "rest" ve "pose" -> kaynak kendi rest'indeyken hedef de kendi rest'ine
          oturur (hata 0.000 derece). Yani rig'in rest biasi KORUNUR: T-pose
          kaynakta GTA kolu 57 derece asagi biaslanir, animasyonun gosterdigi
          kol yonu bozulur.
      "align" -> bu invaryanti KASITLI olarak 57 derece bozar; cunku amaci
          kaynagin MUTLAK uzuv yonunu korumaktir (animasyonun icerigi budur).
          Roll konvansiyonu farki yine rest ofsetiyle temizlenir.
    Retarget'ta dogru olan "align"dir: icerik korunur, roll kirlenmez.
    """
    offs = {}
    skipped = []
    for g, s in pairs.items():
        tgt = rest3(gta, g)
        if mode == "pose":
            ref = src.pose.bones[s].matrix.to_3x3()
        else:
            ref = rest3(src, s)
            if mode == "align":
                ds, dt = bone_dir(src, s), bone_dir(gta, g)
                # bone_dir None dondurebilir (ne gecerli cocuk ne ebeveyn var).
                # O durumda align UYGULANMAZ: uydurma bir yonle hizalamak,
                # hizalamamaktan daha kotudur. Duz rest ofsetine duseriz.
                if ds is None or dt is None:
                    skipped.append(g)
                else:
                    dot = max(-1.0, min(1.0, ds.dot(dt)))
                    if dot < 0.999999:
                        axis = ds.cross(dt)
                        if axis.length > 1e-8:
                            ref = Matrix.Rotation(math.acos(dot), 3, axis.normalized()) @ ref
        offs[g] = ref.inverted() @ tgt
    if skipped:
        log(f"align atlandi ({len(skipped)} kemik, duz rest ofseti): {skipped}")
    return offs


def bake(gta, src, pairs, offs, f0, f1, action_name):
    """Delta transfer + keyframe. Kok->yaprak sirasi ZORUNLU: parent ayarlanmadan
    child'in dunya matrisi yanlis okunur."""
    for pb in gta.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    gta.animation_data_create()
    act = bpy.data.actions.new(action_name)
    gta.animation_data.action = act
    # Blender 4.4+: action ATAMASI YETMEZ, SLOT da baglanmali
    try:
        gta.animation_data.action_slot = act.slots[0]
    except Exception:
        pass

    order = sorted(pairs, key=lambda n: len(gta.data.bones[n].parent_recursive))
    sc = bpy.context.scene
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        want = {g: src.pose.bones[s].matrix.to_3x3() @ offs[g]
                for g, s in pairs.items()}
        for g in order:
            pb = gta.pose.bones[g]
            loc = pb.matrix.translation.copy()
            m = want[g].to_4x4()
            m.translation = loc
            pb.matrix = m
            bpy.context.view_layer.update()
        for g in order:
            gta.pose.bones[g].keyframe_insert('rotation_quaternion', frame=f)
    try:
        gta.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    return act


def transfer_mover(gta, src, pairs, f0, f1):
    """Kaynagin hips YATAY yolunu MOVER track'ine tasi, kemik animasyonunu
    yerinde birak. GTA lokomosyonu boyle uretilir (olculdu: kosu klibinde
    ayak suruklenmesi 0.000 m, yol 3.656 m mover'da).

    ONEMLI: mover'in isaret/uzay konvansiyonu bu araçta DOGRULANMADI.
    Asagidaki dogrulama raporundaki `stance_slide` degerini iki isaretle
    de olcup kucugu sec (README'de anlatildi).
    """
    src_hips = pairs.get("SKEL_ROOT")
    if not src_hips:
        log("UYARI: hips eslesmedi, mover tasinmadi")
        return None
    root = gta.pose.bones.get("SKEL_ROOT")
    if root is None or not hasattr(root, "animation_tracks_mover_location"):
        log("UYARI: mover ozelligi yok (Sollumz surumu?), atlandi")
        return None
    sc = bpy.context.scene

    # ⛔ OLCEK ORANI ZORUNLU. pose.bones[].matrix ARMATURE uzayindadir, objenin
    # dunya olcegini ICERMEZ. FBX'ten gelen UE rig'i tipik olarak 0.01 olcekli
    # (santimetre) gelir; ham degerleri metre sanip GTA rig'ine (olcek 1.0)
    # yazmak yolu 100 KAT buyutur. Olculdu: ped kare 13'te z = -26.978 m'ye
    # gomuldu, "kemikler etrafa dagiliyor" sikayeti bundandi. Duzeltince
    # kok z araligi -0.271 .. +0.067 m.
    ratio = src.matrix_world.to_scale()[0] / max(gta.matrix_world.to_scale()[0], 1e-12)
    if abs(ratio - 1.0) > 1e-6:
        log(f"mover olcek orani: {ratio:.6g} (kaynak/hedef dunya olcegi)")

    sc.frame_set(f0)
    base = src.pose.bones[src_hips].matrix.translation.copy()
    n = 0
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        p = src.pose.bones[src_hips].matrix.translation
        dx, dy, dz = (p.x - base.x) * ratio, (p.y - base.y) * ratio, (p.z - base.z) * ratio
        root.animation_tracks_mover_location = (dx, dy, 1.0)
        root.keyframe_insert('animation_tracks_mover_location', frame=f)
        # kemigi yerinde birak: yatay bileseni sifirla, dikey kalsin
        root.location = (0.0, 0.0, dz)
        root.keyframe_insert('location', frame=f)
        n += 1
    return n


# ---------------------------------------------------------------- dogrulama
def validate(gta, act, f0, f1):
    sc = bpy.context.scene
    rep = {}
    rep["fps"] = sc.render.fps
    rep["frames"] = (f0, f1)
    rep["duration_s"] = round((f1 - f0 + 1) / max(sc.render.fps, 1), 3)

    def curves(a):
        out = []
        for lay in a.layers:
            for st in lay.strips:
                for cb in st.channelbags:
                    out += list(cb.fcurves)
        return out

    bad_scale, bad_loc, bad_expr, bad_never = [], [], [], []
    for fc in curves(act):
        dp = fc.data_path
        if 'pose.bones[' not in dp:
            continue
        bone = dp.split('"')[1]
        prop = dp.rsplit('.', 1)[-1]
        if prop == 'scale':
            bad_scale.append(bone)
        if prop == 'location' and bone not in ("SKEL_ROOT",) and not bone.startswith(("IK_", "PH_")):
            bad_loc.append(bone)
        if bone.startswith(EXPRESSION_DRIVEN_PREFIX):
            bad_expr.append(bone)
        if bone in NEVER_KEY:
            bad_never.append(bone)
    rep["scale_yazilmis"] = sorted(set(bad_scale))
    rep["uzuvda_translation"] = sorted(set(bad_loc))
    rep["expression_kemigine_yazilmis"] = sorted(set(bad_expr))
    rep["donmemesi_gereken_kemik"] = sorted(set(bad_never))

    # dongusellik: ilk ve son kare ayni mi (loop icin sart)
    def pose_of(f):
        sc.frame_set(f)
        return {b.name: gta.pose.bones[b.name].matrix.to_3x3().to_quaternion().copy()
                for b in gta.data.bones if b.name.startswith("SKEL_")}
    a0, a1 = pose_of(f0), pose_of(f1)
    worst = 0.0
    wb = None
    for k in a0:
        d = math.degrees(a0[k].rotation_difference(a1[k]).angle)
        if d > 180:
            d = 360 - d
        if d > worst:
            worst, wb = d, k
    rep["loop_uyusmazligi_derece"] = (round(worst, 2), wb)

    # ayak yerinde mi (in-place kontrolu)
    def foot_drift(name):
        sc.frame_set(f0)
        p0 = (gta.matrix_world @ gta.pose.bones[name].matrix).translation.copy()
        sc.frame_set(f1)
        p1 = (gta.matrix_world @ gta.pose.bones[name].matrix).translation.copy()
        return round((Vector((p1.x - p0.x, p1.y - p0.y, 0))).length, 4)
    rep["ayak_anim_suruklenmesi_m"] = {"L": foot_drift("SKEL_L_Foot"),
                                      "R": foot_drift("SKEL_R_Foot")}
    return rep


# ---------------------------------------------------------------- main
def main():
    sc = bpy.context.scene
    gta, src = find_armatures()
    if gta is None or src is None:
        log("HATA: iki armature gerekli (GTA rig + kaynak rig).")
        return
    log(f"GTA rig  : {gta.name} ({len(gta.data.bones)} kemik)")
    log(f"Kaynak   : {src.name} ({len(src.data.bones)} kemik)")

    if sc.render.fps != FPS:
        log(f"fps {sc.render.fps} -> {FPS} (GTA klipleri 30 fps; 24'te kalirsa "
            f"zamanlama %25 kayar)")
        sc.render.fps = FPS

    pairs, missing = build_pairs(gta, src)
    log(f"eslesen kemik: {len(pairs)}")
    if missing:
        log(f"eslesmeyen  : {missing}")

    # rest pose farki raporu — A-pose/T-pose tuzagi
    def arm_angle(o):
        try:
            a = o.data.bones[[k for k in ("SKEL_L_UpperArm", pairs.get("SKEL_L_UpperArm", ""))
                              if k in o.data.bones][0]]
            b = o.data.bones[[k for k in ("SKEL_L_Forearm", pairs.get("SKEL_L_Forearm", ""))
                              if k in o.data.bones][0]]
            d = (b.matrix_local.translation - a.matrix_local.translation).normalized()
            return round(math.degrees(math.asin(max(-1, min(1, -d.z)))), 1)
        except Exception:
            return None
    ag, as_ = arm_angle(gta), arm_angle(src)
    log(f"ust kol yataydan asagi:  GTA={ag} derece  kaynak={as_} derece")
    if ag is not None and as_ is not None and abs(ag - as_) > 10:
        log(f"  !! REST POZ FARKI {abs(ag-as_):.0f} derece (GTA A-pose vs kaynak).")
        if OFFSET_MODE == "align":
            log("     OFFSET_MODE='align' bunu otomatik kapatiyor — devam.")
        else:
            log(f"     OFFSET_MODE='{OFFSET_MODE}' bu farki KAPATMAZ: kollar")
            log("     57 dereceye kadar biaslanir. OFFSET_MODE='align' kullan.")

    src_act = src.animation_data.action if src.animation_data else None
    if src_act is None:
        log("HATA: kaynak rig'de action yok.")
        return
    f0, f1 = int(src_act.frame_range[0]), int(src_act.frame_range[1])
    sc.frame_start, sc.frame_end = f0, f1

    offs = compute_offsets(gta, src, pairs, OFFSET_MODE)
    log(f"ofset modu: {OFFSET_MODE}")

    act = bake(gta, src, pairs, offs, f0, f1, f"GTA_{src_act.name}")
    log(f"baked: {act.name}  ({f1-f0+1} kare)")

    if BAKE_MOVER:
        n = transfer_mover(gta, src, pairs, f0, f1)
        if n:
            log(f"mover: {n} kare tasindi (hips yatay yolu -> mover track)")

    rep = validate(gta, act, f0, f1)
    log("--- DOGRULAMA ---")
    for k, v in rep.items():
        log(f"  {k}: {v}")
    log("Disa aktarim: Sollumz ile .ycd export -> XML uretir ->")
    log("  powershell -File scripts/xml_to_ycd.ps1 -XmlPath <...>.ycd.xml -ClipName @('klip_adi')")


if __name__ == "__main__":
    main()
