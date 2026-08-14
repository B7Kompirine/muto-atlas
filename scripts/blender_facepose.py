"""blender_facepose.py — GTA ped yuzunu OLCEREK pozla (tahminle degil).

Blender'in Text Editor'unde ac ve Run Script; ya da:
    exec(open(r"...blender_facepose.py").read())
Sonra:
    fp = FacePose()                 # sahnedeki kafayi + armature'i bulur
    fp.measure()                    # Jacobian olcumu (bir kez)
    fp.apply(stretch=.14, lift=.0075, sep=.0008, jaw=.0034)
    fp.report()                     # agiz genisligi / dikey acikligi / kirpilma

NEDEN BU ARAC
=============
Yuz kemiklerine elle deger vermek CALISMAZ. GTA ped riginde kemiklerin
yerel eksenleri anatomik degildir, kaldirac kollari kemikten kemige 6 kat
degisir ve komsu kemikler farkli deger alinca mesh YIRTILIR.

Calisan yontem uc olcume dayanir:

 1. JACOBIAN — her kemik icin d(dunya)/d(local) 3x3 matrisi olculur.
    Sonra `local = J^-1 * istenen_dunya`. Boylece "hangi eksen ne yapiyor"
    tahmini tamamen ortadan kalkar.

 2. YUZEY TAKIBI — agiz kosesi duz yana cekilirse siluetin disina tasar,
    cunku yuz yanlara dogru GERIYE kivrilir. Agiz hizasindaki on yuzey
    profili mesh'ten olculur ve kose o egriye oturtulur.

 3. ROL TABLOSU — her kemige (yanal, dikey, dudak-ayrimi) paylari verilir.
    Komsu kemikler benzer deger aldigi icin gecis pürüzsüz olur.

OLCULMUS TUZAKLAR (hepsi bilfiil yasandi)
=========================================
 * Kok kemiklerin (UpperLipRoot/LowerLipRoot) KENDI derisi yoktur; naif
   olcum onlari atlar ve dudak "butun olarak" hareket etmez, sadece
   koseler kipirdar. Etki alani = kendi vertex'leri + TUM alt kemiklerinki.
 * Sahnede disler (teef) kafadan BUYUK olabilir (4517 > 1514 vertex);
   `max(len(vertices))` ile kafa secmek YANLIS mesh'i secer. Dudak vertex
   grubu olan mesh'i ara.
 * Armature'a atanmis bir action varken elle poz vermek ISE YARAMAZ;
   action her `view_layer.update()` cagrisinda pozu geri ezer.
 * Kirpilma (cap'e dayanma) alani bozar ve sivri uc yaratir -> `report()`
   icindeki `kirpilan` DAIMA 0 olmali.
 * Workbench cavity gölgelemesi kirisiklari abartir; "bozuk mu" karari
   vermeden once cavity'yi kapatip bak.

SINIR (mp_m_freemode_01 kafasi, olculdu)
=======================================
 kafa toplam 1514 vertex, ortalama kenar 11.2 mm (agiz cevresi 6.7 mm),
 kose cevresi 5 mm'de 23 / 10 mm'de 60 vertex.
 -> yanal gerilme ~%14'un otesinde katlanma baslar. Ote tarafi mesh
    duzenleme (edge loop) isidir, animasyon degil.
"""

import json
import math
import os

import bpy
from mathutils import Matrix, Vector


class FacePose:
    PROBE = 0.01          # Jacobian sondasi (m)
    WEIGHT_MIN = 0.08     # etki alanina girme esigi

    # (yanal_pay, dikey_pay, dudak_ayrimi_pay)
    # NOT: kok kemikler SART; onlarsiz dudak butun olarak hareket etmez.
    ROLE_FB = {
        "FB_L_Lip_Corner": (1.00, 1.00,  0.00),
        "FB_R_Lip_Corner": (1.00, 1.00,  0.00),
        "FB_L_Lip_Top":    (0.85, 0.70, +0.10),
        "FB_R_Lip_Top":    (0.85, 0.70, +0.10),
        "FB_L_Lip_Bot":    (0.85, 0.45, -1.00),
        "FB_R_Lip_Bot":    (0.85, 0.45, -1.00),
        "FB_UpperLip":     (0.60, 0.45, +0.15),
        "FB_LowerLip":     (0.60, 0.25, -1.15),
        "FB_UpperLipRoot": (0.50, 0.40, +0.10),
        "FB_LowerLipRoot": (0.50, 0.20, -0.95),
        "FB_L_CheekBone":  (0.15, 0.85,  0.00),
        "FB_R_CheekBone":  (0.15, 0.85,  0.00),
    }

    def __init__(self, armature=None, head=None):
        self.arm = armature or self._find_arm()
        self.head = head or self._find_head()
        self.J = {}
        self.suffix = self._detect_suffix()
        for pb in self.arm.pose.bones:
            pb.rotation_mode = 'XYZ'
        self.clear_action()
        self.reset()

    # ------------------------------------------------------------ bulma
    @staticmethod
    def _find_arm():
        for o in bpy.data.objects:
            if o.type == 'ARMATURE' and any(
                    b.name.startswith(("FB_", "FACIAL_")) for b in o.data.bones):
                return o
        raise RuntimeError("Yuz kemigi olan armature bulunamadi.")

    @staticmethod
    def _find_head():
        """DIKKAT: disler (teef) kafadan BUYUK olabilir -> vertex sayisina
        gore secmek yanlis mesh'i secer. Dudak grubu olani ara."""
        for o in bpy.data.objects:
            if o.type != 'MESH':
                continue
            names = {g.name for g in o.vertex_groups}
            if any(n.startswith(("FB_L_Lip_Corner", "FACIAL_L_lipCorner")) for n in names):
                return o
        raise RuntimeError("Dudak vertex grubu olan kafa mesh'i bulunamadi.")

    def _detect_suffix(self):
        """FB_ kemikleri ped'e gore _000.._006 ya da _045 son eki tasir."""
        for b in self.arm.data.bones:
            if b.name.startswith("FB_L_Lip_Corner"):
                return b.name[len("FB_L_Lip_Corner"):]
        return ""

    def bone(self, base):
        return base + self.suffix if base.startswith("FB_") else base

    # ------------------------------------------------------------ temel
    def clear_action(self):
        """Atanmis action elle pozu EZER — once temizle."""
        if self.arm.animation_data:
            self.arm.animation_data.action = None

    def reset(self):
        for pb in self.arm.pose.bones:
            pb.rotation_euler = (0, 0, 0)
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)
        bpy.context.view_layer.update()

    def _groups(self):
        return {g.name: g.index for g in self.head.vertex_groups}

    def _influence(self, name, gi, own):
        """Etki alani = kendi vertex'leri + TUM alt kemiklerininki.
        Kok kemiklerin kendi derisi olmadigi icin bu sart."""
        b = self.arm.data.bones.get(name)
        if b is None:
            return []
        acc = {}
        for n in [name] + [c.name for c in b.children_recursive]:
            for i, w in own.get(gi.get(n, -1), []):
                acc[i] = max(acc.get(i, 0.0), w)
        return list(acc.items())

    def _wcentroid(self, lst):
        if not lst:
            return None
        dg = bpy.context.evaluated_depsgraph_get()
        ev = self.head.evaluated_get(dg)
        me = ev.to_mesh()
        mw = self.head.matrix_world
        c = Vector((0, 0, 0))
        tot = 0.0
        for i, w in lst:
            c += (mw @ me.vertices[i].co) * w
            tot += w
        ev.to_mesh_clear()
        return c / tot if tot else None

    # ------------------------------------------------------------ olcum
    def measure(self, prefixes=("FB_", "FACIAL_", "MUTO_")):
        """Her yuz kemigi icin Jacobian (local -> dunya) olc."""
        import collections
        self.clear_action()
        self.reset()
        gi = self._groups()
        own = collections.defaultdict(list)
        for v in self.head.data.vertices:
            for g in v.groups:
                if g.weight >= self.WEIGHT_MIN:
                    own[g.group].append((v.index, g.weight))
        data = {}
        for b in self.arm.data.bones:
            n = b.name
            if not n.startswith(prefixes):
                continue
            lst = self._influence(n, gi, own)
            if len(lst) < 3:
                continue
            base = self._wcentroid(lst)
            cols = []
            for ax in range(3):
                self.reset()
                t = [0, 0, 0]
                t[ax] = self.PROBE
                self.arm.pose.bones[n].location = t
                bpy.context.view_layer.update()
                c = self._wcentroid(lst)
                if c is None:
                    cols = None
                    break
                cols.append((c - base) / self.PROBE)
            self.reset()
            if not cols:
                continue
            M = Matrix(((cols[0].x, cols[1].x, cols[2].x),
                        (cols[0].y, cols[1].y, cols[2].y),
                        (cols[0].z, cols[1].z, cols[2].z)))
            if abs(M.determinant()) < 1e-12:
                continue
            data[n] = {"pos": [base.x, base.y, base.z],
                       "J": [list(M[0]), list(M[1]), list(M[2])],
                       "gain": sum(c.length for c in cols) / 3.0,
                       "verts": len(lst)}
        self.J = data
        self._setup_frame()
        return len(data)

    def _setup_frame(self):
        P = {k: Vector(v["pos"]) for k, v in self.J.items()}
        lc = self.bone("FB_L_Lip_Corner")
        rc = self.bone("FB_R_Lip_Corner")
        up = self.bone("FB_UpperLip")
        lo = self.bone("FB_LowerLip")
        if lc not in P:                      # FACIAL_ rigi
            lc, rc = "FACIAL_L_lipCornerAnalog", "FACIAL_R_lipCornerAnalog"
            up, lo = "FACIAL_lipUpperAnalog", "FACIAL_lipLowerAnalog"
        self.Lc, self.Rc = P[lc], P[rc]
        self.M = (P[lc] + P[rc] + P[up] + P[lo]) / 4.0
        self.xr = abs(self.Lc.x - self.Rc.x) / 2.0
        self._key = (lc, rc, up, lo)
        # agiz hizasindaki ON yuzey profili
        mw = self.head.matrix_world
        prof = {}
        for v in self.head.data.vertices:
            p = mw @ v.co
            if abs(p.z - self.M.z) > 0.010:
                continue
            k = round(p.x * 200) / 200.0
            if k not in prof or p.y < prof[k]:
                prof[k] = p.y
        self._prof = prof
        self._pk = sorted(prof)

    def surf_y(self, x):
        """Agiz hizasinda yuzun ON yuzeyi. Kose buna oturmazsa silueti asar."""
        k = self._pk
        x = max(k[0], min(k[-1], x))
        for i in range(len(k) - 1):
            a, b = k[i], k[i + 1]
            if a <= x <= b:
                t = (x - a) / (b - a) if b > a else 0
                return self._prof[a] * (1 - t) + self._prof[b] * t
        return self._prof[k[-1]]

    # ------------------------------------------------------------ poz
    def apply(self, stretch=0.0, lift=0.0, sep=0.0, jaw=0.0, role=None, cap=0.20):
        """Agiz deformasyonunu uygula.
        stretch: yanal gerilme orani  |  lift: kose kaldirma (m)
        sep: dudak ayrimi (m)         |  jaw: cene acilmasi (m)
        """
        if not self.J:
            raise RuntimeError("Once measure() calistir.")
        role = role or {self.bone(k): v for k, v in self.ROLE_FB.items()}
        self.clear_action()
        self.reset()
        out, clipped = {}, 0
        jn = self.bone("FB_Jaw")
        jd, jb = self.J.get(jn), self.arm.pose.bones.get(jn)
        if jd and jb and abs(jaw) > 1e-9:
            M = Matrix(tuple(tuple(r) for r in jd["J"]))
            loc = M.inverted() @ Vector((0, 0, -jaw))
            jb.location = loc
            out[jn] = tuple(loc)
        for name, (kx, kz, ks) in role.items():
            d, pb = self.J.get(name), self.arm.pose.bones.get(name)
            if d is None or pb is None:
                continue
            p = Vector(d["pos"])
            r = min(abs(p.x) / self.xr, 1.35) if self.xr > 1e-6 else 0.0
            tx = p.x * (1.0 + stretch * kx)
            ty = self.surf_y(tx) + (p.y - self.surf_y(p.x))
            tz = (p.z + lift * kz * (0.40 + 0.60 * r * r)
                  + sep * ks * (1.0 - 0.45 * r * r))
            if ks < 0:
                tz -= jaw * 0.60 * (1.0 - 0.35 * r * r)
            want = Vector((tx, ty, tz)) - p
            if want.length < 1e-7:
                continue
            M = Matrix(tuple(tuple(row) for row in d["J"]))
            loc = M.inverted() @ want
            if loc.length > cap:
                loc = loc.normalized() * cap
                clipped += 1
            pb.location = loc
            out[name] = tuple(loc)
        bpy.context.view_layer.update()
        self.last = {"pose": out, "clipped": clipped}
        return out, clipped

    # ------------------------------------------------------------ rapor
    def report(self):
        import collections
        gi = self._groups()
        own = collections.defaultdict(list)
        for v in self.head.data.vertices:
            for g in v.groups:
                if g.weight >= 0.3:
                    own[g.group].append(v.index)

        def cen(n):
            idx = own.get(gi.get(n, -1), [])
            if not idx:
                return None
            dg = bpy.context.evaluated_depsgraph_get()
            ev = self.head.evaluated_get(dg)
            me = ev.to_mesh()
            mw = self.head.matrix_world
            c = Vector((0, 0, 0))
            for i in idx:
                c += mw @ me.vertices[i].co
            c /= len(idx)
            ev.to_mesh_clear()
            return c
        lc, rc, up, lo = self._key
        L, R, U, D = cen(lc), cen(rc), cen(up), cen(lo)
        rep = {"surulen_kemik": len(getattr(self, "last", {}).get("pose", {})),
               "kirpilan": getattr(self, "last", {}).get("clipped", 0)}
        if L and R:
            rep["agiz_genisligi_mm"] = round(abs(L.x - R.x) * 1000, 1)
        if U and D:
            rep["dikey_acik_mm"] = round((U.z - D.z) * 1000, 1)
        if rep["kirpilan"]:
            rep["UYARI"] = ("kirpilan kemik var -> alan bozulur, sivri uc olusur. "
                            "cap'i yukselt ya da genligi dusur.")
        return rep

    def topology(self):
        """Mesh'in gerilmeye ne kadar dayanabilecegini gosteren olcum."""
        mw = self.head.matrix_world
        n = len(self.head.data.vertices)
        near = {f"{int(r*1000)}mm": sum(
            1 for v in self.head.data.vertices if (mw @ v.co - self.Lc).length < r)
            for r in (0.005, 0.010, 0.020)}
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(self.head.data)
        avg = sum(e.calc_length() for e in bm.edges) / max(len(bm.edges), 1)
        bm.free()
        return {"kafa_vertex": n, "ortalama_kenar_mm": round(avg * 1000, 2),
                "kose_cevresi_vertex": near,
                "not": "vertex az + kenar buyukse yanal gerilme sinirlidir; "
                       "otesinde katlanma modelleme isidir."}


if __name__ == "__main__":
    fp = FacePose()
    print("[facepose] armature:", fp.arm.name, "| kafa:", fp.head.name,
          "| son ek:", repr(fp.suffix))
    print("[facepose] olculen kemik:", fp.measure())
    print("[facepose] topoloji:", fp.topology())
    fp.apply(stretch=0.14, lift=0.0075, sep=0.0008, jaw=0.0034)
    print("[facepose] rapor:", fp.report())
