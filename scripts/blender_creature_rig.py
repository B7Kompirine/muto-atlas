"""
blender_creature_rig.py — insan disi bir mesh'i GERCEK GTA ped iskeletine baglar.

TEMEL KURAL (ihlali FiveM'de dogrudan basarisizlik demektir):
    Custom iskelet YASAK. GTA V motoru yalnizca kendi ped iskeletini kabul eder.
    Kemik ADI, TAG'i, PARENT'i ve SAYISI degistirilemez.
    Serbest olan tek sey: her kemigin KONUMU (head/tail) ve dolayisiyla BOYU.

Bu araci kullanmak icin sahnede sunlar olmali:
    - gercek bir ped .yft'inden Sollumz ile ice alinmis Armature
    - baglanacak mesh

Tipik kullanim:
    exec(open(r"<PLUGIN>/scripts/blender_creature_rig.py").read())
    cr = CreatureRig("gta_rig", "GladeMonster")
    cr.snapshot()                      # imza al (ad+tag+parent) — sonda dogrulanir
    cr.place_chain(["SKEL_Spine_Root","SKEL_Spine0","SKEL_Spine1","SKEL_Spine2",
                    "SKEL_Spine3","SKEL_Neck_1","SKEL_Head"], kuyruk_noktalari)
    cr.place_chain([...], on_bacak_noktalari)
    cr.park()                          # kullanilmayanlari ebeveynin yanina indir
    cr.skin()                          # bilesen tabanli agirlik + duzeltme
    cr.verify()                        # imza + GTA kurallari + gerilme testi
"""

import bpy
import numpy as np
from mathutils import Vector, Euler

# DIKKAT: 0.05 DEGIL. Blender kemik uzunlugunu float32 tutar ve float32'deki
# 0.05 (0.050000000745...) Python'un double 0.05'inden BUYUKTUR. Esik tam 0.05
# verilirse Sollumz'un 0.05'e sabitledigi TUM kemikler (yuz blogu dahil) "yerlesmis"
# sayilir ve agirlik calar. Olculdu: 82 kemikli rig'de 43 yerine 77 kemik gecti.
MIN_LEN = 0.06          # bundan kisa kemik "park edilmis" sayilir, agirlik almaz
PARK_LEN = 0.012        # park edilen kemigin boyu
RIGID_EXT = 0.80        # bu boyuttan kucuk mesh parcasi TEK kemige kati baglanir
SMOOTH_ITERS = 6        # yumusak bolgede agirlik duzeltme adimi
SMOOTH_LAMBDA = 0.55


class CreatureRig:
    def __init__(self, armature, mesh):
        self.arm = bpy.data.objects[armature]
        self.obj = bpy.data.objects[mesh]
        self.sig = None
        self.placed = set()
        self._comp = None

    # ------------------------------------------------------------------ imza
    def snapshot(self):
        """Iskeletin degistirilemez imzasini al: ad -> (tag, parent)."""
        self.sig = {
            b.name: (b.bone_properties.tag, b.parent.name if b.parent else None)
            for b in self.arm.data.bones
        }
        return {"kemik": len(self.sig)}

    # --------------------------------------------------------------- konumlama
    def _edit(self):
        bpy.context.view_layer.objects.active = self.arm
        bpy.ops.object.select_all(action='DESELECT')
        self.arm.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        return self.arm.data.edit_bones

    def place_chain(self, names, points):
        """Bir kemik zincirini verilen egri boyunca yerlestirir.

        names  : hiyerarsi sirasinda GTA kemik adlari (parent -> child)
        points : dunya uzayinda Nx3 nokta dizisi (uzuv merkez hatti)

        N kemik icin N+1 nokta gerekir. Az nokta verilirse egri yeniden
        orneklenir; UC KEMIK ICIN AYRI BIR NOKTA KALMAZSA o kemik gudukte
        kalir ve hicbir vertex'i surmez (olculdu: 0.02 m boy -> 0 vertex).
        """
        pts = np.asarray(points, dtype=np.float64)
        if len(pts) < 2:
            raise ValueError("en az 2 nokta gerekli")
        need = len(names) + 1
        pts = _resample(pts, need)
        eb = self._edit()
        inv = self.arm.matrix_world.inverted()
        for i, nm in enumerate(names):
            b = eb.get(nm)
            if b is None:
                raise KeyError(f"{nm} bu iskelette yok — ad uydurma")
            b.head = inv @ Vector(pts[i])
            b.tail = inv @ Vector(pts[i + 1])
            self.placed.add(nm)
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"yerlestirilen": len(names)}

    def place_single(self, name, head, tail):
        eb = self._edit()
        inv = self.arm.matrix_world.inverted()
        b = eb[name]
        b.head = inv @ Vector(head)
        b.tail = inv @ Vector(tail)
        self.placed.add(name)
        bpy.ops.object.mode_set(mode='OBJECT')

    def move_block(self, root, target):
        """Bir kemigi ve TUM alt agacini olceklemeden, saf oteleme ile tasir.

        Kullanim yeri: kafa. Kafanin ic yapisi (25 `FB_` yuz kemigi + `SPR_` kulak
        + `IK_Head`) korunmak zorundaysa zincir olarak yerlestirilemez — blok
        halinde tasinir. Oteleme kemikler arasi TUM goreli konumlari ve TUM kemik
        boylarini aynen birakir (olculdu: sapma 3e-8 m).
        """
        eb = self._edit()
        kids = {}
        for b in self.arm.data.bones:
            kids.setdefault(b.parent.name if b.parent else None, []).append(b.name)
        blok, st = [root], [root]
        while st:
            for k in kids.get(st.pop(), []):
                blok.append(k)
                st.append(k)
        d = Vector(target) - eb[root].head.copy()
        for nm in blok:
            b = eb[nm]
            b.head = b.head + d
            b.tail = b.tail + d
        bpy.ops.object.mode_set(mode='OBJECT')
        self.placed.update(blok)
        self._block = getattr(self, "_block", set()) | set(blok)
        return {"blok_kemik": len(blok), "oteleme": [round(x, 4) for x in d]}

    def park(self):
        """Kullanilmayan kemikleri ebeveynin basina indirip kisaltir.

        SILMEK YASAK — 128 kemigin hepsi kalmali. Kisaltmak yeterlidir:
        MIN_LEN altindaki kemikler skin() tarafindan agirlik disi birakilir,
        yani mesh'i hic etkilemezler ama iskelet imzasi bozulmaz.
        """
        eb = self._edit()
        n = 0
        for b in eb:
            if b.name in self.placed:
                continue
            base = b.parent.head.copy() if b.parent else Vector((0, 0, 0))
            b.head = base
            b.tail = base + Vector((0, PARK_LEN, 0))
            n += 1
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"park_edilen": n, "kullanilan": len(self.placed)}

    # ------------------------------------------------------------- bilesenler
    def components(self):
        """Mesh'in bagli bilesenleri (union-find). Sonuc onbellege alinir."""
        if self._comp is not None:
            return self._comp
        me = self.obj.data
        n = len(me.vertices)
        ne = len(me.edges)
        ek = np.empty(ne * 2, dtype=np.int32)
        me.edges.foreach_get("vertices", ek)
        E = ek.reshape(ne, 2)
        par = np.arange(n, dtype=np.int32)

        def find(x):
            r = x
            while par[r] != r:
                r = par[r]
            while par[x] != r:
                par[x], x = r, par[x]
            return r

        for a, b in E:
            ra, rb = find(a), find(b)
            if ra != rb:
                par[ra] = rb
        roots = np.array([find(i) for i in range(n)], dtype=np.int32)
        uniq, comp, cnt = np.unique(roots, return_inverse=True, return_counts=True)
        self._comp = (uniq, comp, cnt, E)
        return self._comp

    def _world_verts(self):
        me = self.obj.data
        n = len(me.vertices)
        co = np.empty(n * 3)
        me.vertices.foreach_get("co", co)
        mw = np.array(self.obj.matrix_world)
        return co.reshape(n, 3) @ mw[:3, :3].T + mw[:3, 3]

    # ------------------------------------------------------------------- skin
    def skin(self, rigid_ext=RIGID_EXT, iters=SMOOTH_ITERS, force=None, bones=None):
        """Bilesen tabanli agirliklandirma.

        Neden duz mesafe agirligi YETMEZ: mekanik/parcali bir yaratikta mesh
        binlerce ayri katI parcadir. Bir plakanin vertexleri farkli kemiklere
        dagilirsa plaka poz verildiginde YIRTILIR. Olculdu (223k vertex,
        10.021 bilesen): duz mesafe -> kenarlarin %5.9'u 2 kattan fazla
        gerildi; bilesen tabanli + duzeltme -> %1.2.

        Kural:
          - bilesen capi < rigid_ext  ->  TEK kemige %100 (katI, gerilme
            matematiksel olarak imkansiz)
          - buyuk bilesenler          ->  4 kemikli yumusak agirlik + komsu
            ortalamasiyla Laplacian duzeltme

        force : {kemik_adi: fn(P)->agirlik} — P dunya vertex dizisi (Nx3), donen
            dizi 0..1. Bir bolgeyi belirli bir kemige ZORLAR ve digerlerini o
            oranda kisar. Gerekli oldugu yer: blok halinde tasinan kafa. Kafa
            kemigi kisa oldugu icin mesafe modelinde hicbir vertex kazanamaz ve
            bilesen bazli zorlama da ise yaramaz — kafa cogu modelde govdeyle
            AYNI bagli bilesenin parcasidir. Maske vertex bazli olmali ve boyunda
            yumusak gecmeli, yoksa boyunda kirilma olur.
        bones : agirlik alacak kemiklerin acik listesi (verilmezse MIN_LEN filtresi)
        """
        arm, obj = self.arm, self.obj
        used = list(bones) if bones else [b.name for b in arm.data.bones
                                          if b.length > MIN_LEN]
        for nm in (force or {}):
            if nm not in used:
                used.append(nm)
        if not used:
            raise RuntimeError("hicbir kemik yerlestirilmemis")
        bs = [arm.data.bones[x] for x in used]
        M = len(bs)
        A = np.array([list(arm.matrix_world @ b.head_local) for b in bs])
        B = np.array([list(arm.matrix_world @ b.tail_local) for b in bs])
        P = self._world_verts()
        n = len(P)
        AB = B - A
        L2 = (AB * AB).sum(1)
        L2[L2 < 1e-12] = 1e-12

        # kemik SEGMENTINE uzaklik (nokta degil) — uzun kemikte dogru sonuc verir
        W = np.zeros((n, M), dtype=np.float32)
        for s in range(0, n, 20000):
            e = min(s + 20000, n)
            Q = P[s:e]
            t = np.clip(np.einsum('cmk,mk->cm', Q[:, None, :] - A[None, :, :], AB)
                        / L2[None, :], 0.0, 1.0)
            proj = A[None, :, :] + t[:, :, None] * AB[None, :, :]
            d = np.maximum(np.linalg.norm(Q[:, None, :] - proj, axis=2), 1e-4)
            W[s:e] = (1.0 / d ** 3).astype(np.float32)

        # zorlanan kemikler mesafeyle agirlik KAZANMAZ, sadece maskeyle alir
        masks = {}
        for nm, fn in (force or {}).items():
            masks[used.index(nm)] = np.clip(np.asarray(fn(P), dtype=np.float32), 0, 1)
            W[:, used.index(nm)] = 0.0

        uniq, comp, cnt, E = self.components()
        ext = np.zeros(len(uniq))
        for k in range(len(uniq)):
            Q = P[comp == k]
            ext[k] = np.linalg.norm(Q.max(0) - Q.min(0))

        rigid = np.isin(comp, np.nonzero(ext < rigid_ext)[0])
        acc = np.zeros((len(uniq), M))
        np.add.at(acc, comp, W.astype(np.float64))
        best = acc.argmax(1)

        FIN = np.zeros((n, M), dtype=np.float32)
        FIN[rigid, best[comp[rigid]]] = 1.0

        sm = np.nonzero(~rigid)[0]
        if len(sm):
            w = W[sm].copy()
            w /= w.sum(1, keepdims=True)
            gid = -np.ones(n, dtype=np.int64)
            gid[sm] = np.arange(len(sm))
            msk = (gid[E[:, 0]] >= 0) & (gid[E[:, 1]] >= 0)
            Es = np.stack([gid[E[msk, 0]], gid[E[msk, 1]]], 1)
            deg = np.bincount(Es.ravel(), minlength=len(sm)).astype(np.float32)
            deg[deg == 0] = 1
            for _ in range(iters):
                a2 = np.zeros_like(w)
                np.add.at(a2, Es[:, 0], w[Es[:, 1]])
                np.add.at(a2, Es[:, 1], w[Es[:, 0]])
                w = (1 - SMOOTH_LAMBDA) * w + SMOOTH_LAMBDA * (a2 / deg[:, None])
                w /= np.maximum(w.sum(1, keepdims=True), 1e-9)
            FIN[sm] = w

        # zorlama KATI parcalari da kapsamali: kafa cogu zaman kati bilesenlerden
        # olusur, sadece yumusak tarafa uygulanirsa hic tutmaz
        for j, mk in masks.items():
            FIN *= (1.0 - mk)[:, None]
            FIN[:, j] += mk
        FIN = _gta_clean(FIN)

        self._write_groups(used, FIN)
        return {"kemik": M, "kati_vertex": int(rigid.sum()),
                "yumusak_vertex": int(len(sm)),
                "zorlanan_kemik": [used[j] for j in masks],
                "kati_bilesen": int((ext < rigid_ext).sum()),
                "yumusak_bilesen": int((ext >= rigid_ext).sum())}

    def _write_groups(self, used, FIN):
        obj, arm = self.obj, self.arm
        for m in list(obj.modifiers):
            if m.type == 'ARMATURE':
                obj.modifiers.remove(m)
        for g in list(obj.vertex_groups):
            obj.vertex_groups.remove(g)
        obj.parent = arm
        obj.matrix_parent_inverse = arm.matrix_world.inverted()
        md = obj.modifiers.new("Armature", 'ARMATURE')
        md.object = arm
        for j, nm in enumerate(used):
            g = obj.vertex_groups.new(name=nm)
            col = FIN[:, j]
            for i in np.nonzero(col)[0]:
                g.add([int(i)], float(col[i]), 'REPLACE')

    # ----------------------------------------------------------------- verify
    def verify(self, pose=None):
        """Uc sey dogrulanir: iskelet imzasi, GTA agirlik kurallari, gerilme."""
        out = {}

        if self.sig is not None:
            cur = {b.name: (b.bone_properties.tag,
                            b.parent.name if b.parent else None)
                   for b in self.arm.data.bones}
            fark = [k for k in self.sig if cur.get(k) != self.sig[k]]
            fark += [k for k in cur if k not in self.sig]
            out["IMZA_AYNI"] = not fark
            out["imza_farki"] = fark[:8]
        out["kemik_sayisi"] = len(self.arm.data.bones)

        import collections
        infl = collections.Counter()
        zero = fazla = 0
        sapma = 0.0
        for v in self.obj.data.vertices:
            gs = [x for x in v.groups if x.weight > 0]
            infl[len(gs)] += 1
            if not gs:
                zero += 1
                continue
            if len(gs) > 4:
                fazla += 1
            sapma = max(sapma, abs(sum(x.weight for x in gs) - 1.0))
        out["GTA_KURALLARI"] = {"dagilim": dict(sorted(infl.items())),
                                "4ten_fazla": fazla, "agirliksiz": zero,
                                "toplam_sapma": round(sapma, 6)}

        pb = self.arm.pose.bones
        for p in pb:
            p.rotation_mode = 'XYZ'
            p.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        Vr = _eval_verts(self.obj)
        if pose:
            for nm, r in pose.items():
                if nm in pb:
                    pb[nm].rotation_euler = Euler(r, 'XYZ')
            bpy.context.view_layer.update()
            Vp = _eval_verts(self.obj)
            for p in pb:
                p.rotation_euler = (0, 0, 0)
            bpy.context.view_layer.update()
            _, _, _, E = self.components()
            Lr = np.linalg.norm(Vr[E[:, 0]] - Vr[E[:, 1]], axis=1)
            Lp = np.linalg.norm(Vp[E[:, 0]] - Vp[E[:, 1]], axis=1)
            ok = Lr > 1e-6
            ratio = Lp[ok] / Lr[ok]
            out["GERILME"] = {"ortalama": round(float(ratio.mean()), 4),
                              "yuzde99": round(float(np.percentile(ratio, 99)), 3),
                              "2x_asan_%": round(float((ratio > 2).sum())
                                                 / ok.sum() * 100, 3)}

        # --- kemik surdugu geometrinin ICINDE mi ---
        # NEDEN SART: bir bolgenin AGIRLIK MERKEZI bos uzaya dusebilir. Olculdu:
        # yaratigin "kafa" bolgesi aslinda iki yandan sarkan cene kutlesiydi,
        # x histogrami [0,958,462,0,2,0,1461,0,0] - merkez serit BOS. Kafa kemigi
        # o bosluga kondu, mesh'e 0.499 m uzakta kaldi. Hicbir imza/agirlik/
        # gerilme denetimi bunu yakalamaz; poz verilene kadar da fark edilmez.
        P = self._world_verts()
        cell = 0.15
        grid = {}
        for i, k in enumerate(map(tuple, np.floor(P / cell).astype(np.int64))):
            grid.setdefault(k, []).append(i)

        def yakinlik(pt):
            k = tuple(np.floor(pt / cell).astype(np.int64))
            best = float("inf")
            for d in range(7):
                for dx in range(-d, d + 1):
                    for dy in range(-d, d + 1):
                        for dz in range(-d, d + 1):
                            if max(abs(dx), abs(dy), abs(dz)) != d:
                                continue
                            c = (k[0] + dx, k[1] + dy, k[2] + dz)
                            if c in grid:
                                v = np.linalg.norm(P[grid[c]] - pt, axis=1).min()
                                best = min(best, v)
                if best < cell * max(d, 1):
                    break
            return best

        uzak = []
        for nm in sorted(self.placed):
            b = self.arm.data.bones.get(nm)
            if b is None or b.length <= MIN_LEN:
                continue
            h = np.array(b.head_local)
            t = np.array(b.tail_local)
            d = max(yakinlik(h + (t - h) * f) for f in (0.15, 0.5, 0.85))
            if d > 0.25:
                uzak.append((nm, round(float(d), 3)))
        out["GEOMETRI_DISI"] = sorted(uzak, key=lambda x: -x[1])
        out["geometri_notu"] = ("SKEL_ROOT zeminde olmali (vanilla'da da oyle); "
                                "govde ici kemikler kabuk kalinligi kadar uzak "
                                "olcuulur. Uzuv/kafa kemigi listede cikarsa KUSUR.")

        # olu kemik = mesh'i GERCEKTEN surmeyen kemik.
        # Uzunluga gore karar VERME: blok tasinan kafa kemigi kisadir ama
        # force maskesiyle agirlik alir - uzunluk testi onu yanlis yere "olu"
        # der. Tek dogru olcut: vertex grubunda sifirdan buyuk agirlik var mi.
        agirlikli = set()
        for v in self.obj.data.vertices:
            for g in v.groups:
                if g.weight > 0:
                    agirlikli.add(g.group)
        adlar = {g.index: g.name for g in self.obj.vertex_groups}
        suren = {adlar[i] for i in agirlikli if i in adlar}
        out["olu_kemik"] = sorted(nm for nm in self.placed if nm not in suren)
        return out


# --------------------------------------------------------------------- yardim
def _resample(pts, count):
    """Bir egriyi yay uzunluguna gore esit araliklarla yeniden ornekler."""
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    if s[-1] <= 0:
        return np.repeat(pts[:1], count, axis=0)
    tgt = np.linspace(0, s[-1], count)
    return np.stack([np.interp(tgt, s, pts[:, i]) for i in range(3)], axis=1)


def _gta_clean(w):
    """GTA kurali: vertex basina en fazla 4 etki, toplam tam 1.0,
    agirlik 1/255'e nicemlenir — 1/255 altindaki etkiler zaten sifirlanir."""
    K = 4
    if w.shape[1] > K:
        idx = np.argpartition(-w, K, axis=1)[:, :K]
        mk = np.zeros_like(w, dtype=bool)
        np.put_along_axis(mk, idx, True, axis=1)
        w = np.where(mk, w, 0.0)
    w = w / np.maximum(w.sum(1, keepdims=True), 1e-9)
    w[w < 1.0 / 255.0] = 0.0
    return w / np.maximum(w.sum(1, keepdims=True), 1e-9)


def _eval_verts(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    m = ev.to_mesh()
    c = np.empty(len(m.vertices) * 3)
    m.vertices.foreach_get("co", c)
    r = c.reshape(-1, 3).copy()
    ev.to_mesh_clear()
    return r


def march(P, start, direction, step=0.22, radius=0.34, kmax=45, stop=None):
    """Bir uzvun merkez hattini yay boyunca YURUYEREK cikarir.

    NEDEN DILIMLEME YETMEZ: orumcek/akrep bacagi ve kivrilan kuyruk TERS V'dir —
    govdeden yukari cikip ayaga iner. Tek bir eksene gore dilimleyince cikan ve
    inen kisim AYNI dilime duser, ortalamalari alinir ve z profili zigzag yapar
    (olculdu: ayak z=0.43 iken hat 1.28/1.69/1.39/1.31... diye sekti; hat hic
    ayaga ulasmadi). Yuruyus yonu her adimda guncelledigi icin kivrimi takip eder.

    Ayaktan govdeye dogru baslat: ayak noktasi kesin, govde baglantisi tahminidir.
    """
    pts = [np.array(start, dtype=float)]
    d = np.array(direction, dtype=float)
    d /= np.linalg.norm(d)
    for _ in range(kmax):
        c = pts[-1] + d * step
        m = np.linalg.norm(P - c, axis=1) < radius
        if m.sum() < 20:
            break
        Q = P[m]
        fwd = ((Q - pts[-1]) @ d) > 0          # sadece ILERI yarikure
        if fwd.sum() < 12:
            break
        c2 = Q[fwd].mean(0)
        nd = c2 - pts[-1]
        L = np.linalg.norm(nd)
        if L < 1e-3:
            break
        d = 0.5 * d + 0.5 * (nd / L)
        d /= np.linalg.norm(d)
        pts.append(c2)
        if stop and stop(c2):
            break
    return np.array(pts)


def centerline(obj, axis=2, slices=24, comp_min=0):
    """Bir mesh parcasinin merkez hattini PCA ekseni boyunca dilimleyerek cikarir.

    BFS/geodezik yontem BURADA CALISMAZ: parcali mesh'te uzuv onlarca kopuk
    bilesene ayrilir ve hat cokerek (olculdu: 1.89 m bacak -> 0.15 m) yanlis
    sonuc verir. Dilimleme baglantisiz geometride de dogru calisir.
    """
    n = len(obj.data.vertices)
    co = np.empty(n * 3)
    obj.data.vertices.foreach_get("co", co)
    mw = np.array(obj.matrix_world)
    P = co.reshape(n, 3) @ mw[:3, :3].T + mw[:3, 3]
    C = P - P.mean(0)
    _, _, Vt = np.linalg.svd(C, full_matrices=False)
    d = Vt[0]
    t = C @ d
    edges = np.linspace(t.min(), t.max(), slices + 1)
    out = []
    for i in range(slices):
        m = (t >= edges[i]) & (t < edges[i + 1])
        if m.sum() > comp_min:
            out.append(P[m].mean(0))
    return np.array(out)
