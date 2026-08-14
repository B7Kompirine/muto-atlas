"""blender_izgara_bake.py -- sanayi bar-grating BAKE KAYNAGI uretir.

Bu betik PROP'u degil, propun DOKUSUNU uretecek 1x1 m'lik gercek geometriyi
kurar. Cikti akisi:
    blender_bake_sahnesi.kur(alfa=True)   -> tiling bake sahnesi
    izgara_kur()                          -> bu betik (cubuklar + malzeme)
    blender_bake_sahnesi.aov_bagla()
    blender_bake_sahnesi.render_et(klasor)
    bake_to_gta.py <klasor> --cutout      -> GTA dokulari
    dds_to_ytd.ps1                        -> .ytd

Alfa, bosluklarin GERCEKTEN BOS olmasindan gelir (film_transparent).
Delik cizmiyoruz; delik zaten yok olan geometridir.
"""
import bmesh
import bpy
from mathutils import Vector

ADI = "mtk_izgara_01"


def izgara_kur(tekrar=8, bar_en=0.026, bar_yuk=0.045,
               rod_en=0.013, rod_cok=0.006, koleksiyon="bake_texture"):
    """1 m'lik bar-grating parcasi. tekrar TAM SAYI olmali (tiling sarti)."""
    if tekrar != int(tekrar):
        raise ValueError("tekrar tam sayi olmali -- kesirli deger tiling'i bozar")

    eski = bpy.data.objects.get(ADI)
    if eski:
        bpy.data.objects.remove(eski, do_unlink=True)

    adim = 1.0 / tekrar
    merkez = [-0.5 + adim * (i + 0.5) for i in range(tekrar)]
    bm = bmesh.new()

    def kutu(c, s):
        t = bmesh.new()
        bmesh.ops.create_cube(t, size=1.0)
        bmesh.ops.scale(t, vec=s, verts=t.verts)
        bmesh.ops.translate(t, vec=c, verts=t.verts)
        me = bpy.data.meshes.new("_tmp")
        t.to_mesh(me); t.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)

    # tasiyici cubuklar: Y boyunca SUREKLI -> Y ekseninde tiling kendiliginden
    for cx in merkez:
        kutu((cx, 0.0, -bar_yuk / 2), (bar_en, 1.0, bar_yuk))
    # capraz miller: X boyunca surekli, bar ustunden rod_cok kadar asagida
    for cy in merkez:
        kutu((0.0, cy, -rod_cok - rod_en / 2), (1.0, rod_en, rod_en))

    me = bpy.data.meshes.new(ADI)
    bm.to_mesh(me); bm.free()
    obj = bpy.data.objects.new(ADI, me)
    bpy.data.collections[koleksiyon].objects.link(obj)
    obj.data.materials.append(metal_malzeme())

    acik = 1 - (bar_en + rod_en) / adim + (bar_en * rod_en) / adim ** 2
    print(f"[izgara] {tekrar} cubuk + {tekrar} mil | {len(me.vertices)} vertex | "
          f"adim {adim * 1000:.0f} mm | teorik acik alan %{acik * 100:.1f}")
    return obj


def metal_malzeme(ad="mtk_izgara_metal"):
    m = bpy.data.materials.get(ad) or bpy.data.materials.new(ad)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    yeni = lambda t, x, y: (lambda n: (n.location.__setattr__("x", x),
                                       n.location.__setattr__("y", y), n)[-1])(
        nt.nodes.new(t))

    cikti = yeni("ShaderNodeOutputMaterial", 700, 0)
    bsdf = yeni("ShaderNodeBsdfPrincipled", 380, 0)
    nt.links.new(bsdf.outputs["BSDF"], cikti.inputs["Surface"])

    # !! TEXTURE COORDINATE 'Object' OLMALI. Tiler malzemeyi KOLEKSIYON
    #    KOPYASI olarak 8 komsuya tasir; Object uzayi her kopyada aynidir,
    #    desen birebir tekrarlar. Dunya/global uzay kullanirsan her kopyada
    #    farkli gurultu cikar ve kenarda GORUNUR DIKIS olusur.
    koord = yeni("ShaderNodeTexCoord", -800, 0)
    gur = yeni("ShaderNodeTexNoise", -600, 100)
    gur.inputs["Scale"].default_value = 6.0
    gur.inputs["Detail"].default_value = 8.0
    gur.inputs["Roughness"].default_value = 0.65
    nt.links.new(koord.outputs["Object"], gur.inputs["Vector"])

    pas = yeni("ShaderNodeValToRGB", -380, 100)
    pas.color_ramp.elements[0].position = 0.48
    pas.color_ramp.elements[1].position = 0.62
    nt.links.new(gur.outputs["Fac"], pas.inputs["Fac"])

    renk = yeni("ShaderNodeMixRGB", -120, 160)
    renk.inputs["Color1"].default_value = (0.34, 0.355, 0.375, 1)   # galvaniz
    renk.inputs["Color2"].default_value = (0.16, 0.065, 0.028, 1)   # pas
    nt.links.new(pas.outputs["Color"], renk.inputs["Fac"])
    nt.links.new(renk.outputs["Color"], bsdf.inputs["Base Color"])

    prz = yeni("ShaderNodeMapRange", -120, -140)
    prz.inputs["To Min"].default_value = 0.28
    prz.inputs["To Max"].default_value = 0.85
    nt.links.new(pas.outputs["Color"], prz.inputs["Value"])
    nt.links.new(prz.outputs["Result"], bsdf.inputs["Roughness"])

    # !! METALLIC 0 BIRAKILIYOR, bilerek. Base color duz beyaz dunya isigi
    #    altinda render ediliyor; metallic=1 olsaydi yuzeyin diffuse'u olmaz,
    #    ortami yansitir ve base color duz beyaza cikardi. GTA'da zaten
    #    metallic sampler YOK (249 shader'da 0) -- metal hissi spec
    #    haritasi + shader skalerlerinden gelir.
    bsdf.inputs["Metallic"].default_value = 0.0
    return m


if __name__ == "__main__":
    izgara_kur()
