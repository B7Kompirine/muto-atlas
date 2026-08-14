"""blender_bake_sahnesi.py -- kusursuz tiling malzeme BAKE sahnesi kurar.

Yontem: malzemeyi shader node'uyla degil GERCEK GEOMETRIYLE kur, ortografik
kamerayla tepeden render et, PBR kanallarini dosyaya yaz. Cikti duz doku
oldugu icin GTA V'e girer (motor node grafigi calistiramaz).

Kurdugu sahne:
  bake_texture/   <- MALZEMEYI BURAYA KOY (tek 1x1 m'lik alan)
  bake_tiler/     <- cevresine 8 kopya; kenardan cikan icerik obur uctan girer
  bake_cam        <- ortografik, Z=+2 m, asagi bakar, ortho scale 1
  compositor      <- File Output: BaseColor / Roughness / Normal / AO [/ Alpha]

!! TILER NEDEN GEOMETRY NODES DEGIL: GN soket ADLARI surumler arasi degisir
   (CollectionInfo ciktisi 3.x'te "Geometry", 4.x'te "Instances"), ve yanlis
   soket sessizce baglanmaz. Collection-instance empty'ler ayni isi yapar,
   API'si yillardir sabittir. Video GN kullaniyor; sonuc birebir aynidir.

!! GTA icin METALLIC ve AO KANALI AYRI YAZILMAZ: 249 shader'da metallic
   sampler 0, AO sampler 0 adet. AO yine de render edilir cunku bake_to_gta.py
   onu DIFFUSE'un icine carpar. Metallic hic uretilmez.

Kullanim (Blender Scripting sekmesi ya da MCP):
    exec(open(r"...\\blender_bake_sahnesi.py").read())
    kur(cozunurluk=4096, alfa=True)     # alfa=True -> cutout (izgara/cit)

Sonra: bake_texture koleksiyonuna malzemeni koy, aov_bagla() calistir,
       render_et(klasor) ile haritalari yaz.
"""
import math
import os

import bpy

ON = "bake_"                     # bu betigin urettigi her seyin ad oneki
KANALLAR = ("BaseColor", "Roughness", "Normal", "AO")


# ----------------------------------------------------------------------
# yardimcilar
# ----------------------------------------------------------------------
def _sok(node, ad, giris=True):
    """Soketi ADIYLA bulur; bulamazsa SESSIZ GECMEZ, hata firlatir."""
    havuz = node.inputs if giris else node.outputs
    for s in havuz:
        if s.name == ad and s.enabled:
            return s
    mevcut = [s.name for s in havuz if s.enabled]
    raise KeyError(f"{node.bl_idname}: '{ad}' soketi yok. Mevcut: {mevcut}")


def _temizle():
    """Onceki kurulumu siler -- betik tekrar tekrar calistirilabilir olsun."""
    for o in [o for o in bpy.data.objects if o.name.startswith(ON)]:
        bpy.data.objects.remove(o, do_unlink=True)
    for c in [c for c in bpy.data.collections if c.name.startswith(ON)]:
        bpy.data.collections.remove(c)


def _yabanci_temizle():
    """Bake rig'ine ait OLMAYAN her mesh'i render disi birakir.

    !! NEDEN VAR -- YASANDI: Blender'in baslangic sahnesindeki varsayilan
       'Cube' 2 m'dir, merkezdedir ve z=[-1,1] arasindadir. Kamera z=+2'den
       asagi bakiyor, ortho scale 1 -> kadraji TAMAMEN kaplar ve izgaranin
       ustunde kalir. Render HATA VERMEZ, dosyalar yazilir, ama haritalar
       kupun haritalaridir: alfa her yerde 1.0, AO duz, roughness 0.
       Belirti "duz/bos harita"dir ve sebebi kolay kolay akla gelmez.
    """
    bizim = set()
    for ad in (ON + "texture", ON + "tiler"):
        c = bpy.data.collections.get(ad)
        if c:
            bizim.update(o.name for o in c.all_objects)

    disarida = []
    for o in bpy.context.scene.objects:
        if o.name in bizim or o.name.startswith(ON):
            continue
        if o.type in {"MESH", "CURVE", "SURFACE", "META", "FONT", "VOLUME"}:
            o.hide_render = True
            o.hide_viewport = True
            disarida.append(o.name)
    return disarida


def _koleksiyon(ad, ebeveyn=None):
    c = bpy.data.collections.new(ad)
    (ebeveyn or bpy.context.scene.collection).children.link(c)
    return c


# ----------------------------------------------------------------------
# 1. sahne iskeleti
# ----------------------------------------------------------------------
def kur(cozunurluk=4096, yuzde=100, alfa=False, ornek=128):
    """Tiling bake sahnesini kurar. alfa=True -> arka plan seffaf (cutout)."""
    _temizle()
    sah = bpy.context.scene

    doku  = _koleksiyon(ON + "texture")
    tiler = _koleksiyon(ON + "tiler")

    # --- 3x3 tiling: merkez HARIC 8 kopya -----------------------------
    # Merkezi olusturmuyoruz; video'da GN ile "0,0,0 noktasini sil" adimi
    # tam olarak bunun karsiligi. Burada hic yaratmayarak ayni sonuca
    # daha az parca ile variyoruz.
    n = 0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            e = bpy.data.objects.new(f"{ON}tile_{dx}_{dy}", None)
            e.instance_type = "COLLECTION"
            e.instance_collection = doku
            e.location = (dx, dy, 0.0)
            e.empty_display_size = 0.15
            e.hide_select = True           # yanlislikla tiklanmasin
            tiler.objects.link(e)
            n += 1

    # --- ortografik kamera --------------------------------------------
    kam_v = bpy.data.cameras.new(ON + "cam")
    kam_v.type = "ORTHO"
    kam_v.ortho_scale = 1.0                # 1 m x 1 m tam kadraj
    kam = bpy.data.objects.new(ON + "cam", kam_v)
    kam.location = (0.0, 0.0, 2.0)         # !! mist icin bu yukseklik onemli
    kam.rotation_euler = (0.0, 0.0, 0.0)   # duz asagi
    sah.collection.objects.link(kam)
    sah.camera = kam

    # --- render ayarlari ----------------------------------------------
    sah.render.resolution_x = cozunurluk
    sah.render.resolution_y = cozunurluk   # KARE olmak zorunda
    sah.render.resolution_percentage = yuzde
    sah.render.film_transparent = bool(alfa)
    sah.frame_start = sah.frame_end = 1    # tek kare
    if sah.render.engine != "CYCLES":
        sah.render.engine = "CYCLES"
    if hasattr(sah, "cycles"):
        sah.cycles.samples = ornek

    # --- renk yonetimi -------------------------------------------------
    # !! VARSAYILAN 'AgX' BAKE ICIN YANLIS. AgX bir gorsel tonlayicidir:
    #    olculdu, 1.0'i ~0.78'e sikistirir. Base color'a uygulanirsa GTA
    #    kendi isiklandirmasini bunun UZERINE bindirir -- cift tonlama.
    #    Bake ciktisi albedo olmali, fotograf degil.
    try:
        sah.view_settings.view_transform = "Standard"
        sah.view_settings.look = "None"
        sah.view_settings.exposure = 0.0
        sah.view_settings.gamma = 1.0
    except TypeError:
        print("[!] view_transform 'Standard' yok -- elle Raw/Standard sec")

    # --- pass'ler ------------------------------------------------------
    vl = bpy.context.view_layer
    vl.use_pass_normal = True
    vl.use_pass_mist = True
    eksik = []
    if hasattr(vl, "use_pass_ambient_occlusion"):
        vl.use_pass_ambient_occlusion = True
    else:
        eksik.append("use_pass_ambient_occlusion")

    # --- 'roughness' Shader AOV ---------------------------------------
    # Roughness bir render pass DEGILDIR; her materyalden AOV Output
    # node'uyla disari verilir (aov_bagla() bunu yapar).
    if not any(a.name == "roughness" for a in vl.aovs):
        a = vl.aovs.add()
        a.name = "roughness"
        a.type = "VALUE"                   # renk degil deger -- veri tasarrufu

    # --- duz beyaz dunya (base color'a isik bake ETME) ----------------
    d = sah.world or bpy.data.worlds.new(ON + "world")
    sah.world = d
    d.use_nodes = True
    bg = next((x for x in d.node_tree.nodes if x.type == "BACKGROUND"), None)
    if bg:
        bg.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
        bg.inputs[1].default_value = 1.0

    yabanci = _yabanci_temizle()

    _compositor(alfa)
    print(f"[kur] tiler kopya={n}  cozunurluk={cozunurluk}x{cozunurluk}@{yuzde}%  "
          f"alfa={'ACIK' if alfa else 'kapali'}")
    if yabanci:
        print(f"[kur] render disi birakildi: {', '.join(yabanci)}")
    if eksik:
        print(f"[!] bu Blender surumunde yok, elle ac: {', '.join(eksik)}")
    print(f"[kur] MALZEMENI '{doku.name}' koleksiyonuna koy, sonra aov_bagla()")
    return doku


# ----------------------------------------------------------------------
# 2. compositor
# ----------------------------------------------------------------------
def _comp_agaci():
    """Compositor agacini dondurur -- Blender 5.x ile 4.x FARKLI yerde tutar.

    OLCULDU (Blender 5.2.0 LTS):
      scene.node_tree                 -> YOK
      scene.compositing_node_group    -> VAR (bpy.data.node_groups icinde)
    """
    sah = bpy.context.scene
    if hasattr(sah, "compositing_node_group"):          # 5.x
        ng = sah.compositing_node_group
        if ng is None:
            ng = bpy.data.node_groups.new(ON + "comp", "CompositorNodeTree")
            sah.compositing_node_group = ng
        return ng
    sah.use_nodes = True                                 # 4.x ve oncesi
    return sah.node_tree


def _slot_ekle(out, ad, tip="RGBA"):
    """File Output'a slot ekler ve ADINI dondurur (nesneyi DEGIL).

    !! KOLEKSIYON REFERANSI SAKLAMA -- YASANDI: file_output_items.new()
       dondurdugu nesne, koleksiyona yeni oge eklendiginde BAYATLAR. Once
       eklenen slot'a sonradan yazilan ayarlar sessizce kaybolur; hata
       verilmez. Olculdu: 5 slot eklendi, sadece SONUNCUSUNA (Alpha)
       yazilan 'save_as_render=False' tuttu, 3. sirdaki Normal'e yazilan
       ayni ayar uygulanmadi ve normal haritasi AgX ile tonlanip bozuldu.
       Cozum: her kullanimda ADIYLA yeniden bak.
    """
    if hasattr(out, "file_output_items"):                # 5.x
        out.file_output_items.new(tip, ad)
    else:                                                # 4.x
        out.file_slots.new(ad)
    return ad


def _slot(out, ad):
    """Slot'u ADIYLA taze getirir."""
    return (out.file_output_items[ad] if hasattr(out, "file_output_items")
            else out.file_slots[ad])


def _slot_bicim(out, ad, **kw):
    slot = _slot(out, ad)
    """Slot'a kendi dosya bicimini verir (dugumunkini EZER).

    !! 5.x'te alan adi TERSINE DONDU: 4.x'te 'use_node_format=False' ile
       ezersin, 5.x'te 'override_node_format=True' ile. Yanlisini yazarsan
       hata CIKMAZ, slot sessizce dugum bicimini kullanir.
    """
    if hasattr(slot, "override_node_format"):            # 5.x
        slot.override_node_format = True
    elif hasattr(slot, "use_node_format"):               # 4.x
        slot.use_node_format = False
    # media_type once ayarlanmali, yoksa file_format enum'u kilitli kalir
    if hasattr(slot.format, "media_type"):
        slot.format.media_type = "IMAGE"
    for k, v in kw.items():
        if k == "save_as_render":
            if hasattr(slot, "save_as_render"):
                slot.save_as_render = v
            if v is False:
                _ham_yap(slot.format)
        elif hasattr(slot.format, k):
            setattr(slot.format, k, v)


def _ham_yap(bicim):
    """Slot'a 'Raw' renk donusumu verir -- veri haritalari icin sart.

    !! save_as_render=False TEK BASINA YETMIYOR: olculdu, normal haritasinin
       katı bolgesinde R,G = 0.735 cikti; oysa duz yuzeyde 0.5 olmali.
       0.735 = sRGB(0.5), yani PNG'ye yine sRGB transferi uygulanmis.
       color_management='OVERRIDE' + view_transform='Raw' bunu kapatir.

    !! ENUM'A GUVENME: view_transform'un enum_items listesi bu surumde
       yalniz ('NONE') doner, ama 'Raw' ATAMASI CALISIR. Listelenmemis
       olmasi yok oldugu anlamina gelmiyor.
    """
    if not hasattr(bicim, "color_management"):
        return
    try:
        bicim.color_management = "OVERRIDE"
        for aday in ("Raw", "Standard"):
            try:
                bicim.view_settings.view_transform = aday
                return
            except TypeError:
                continue
    except Exception as e:
        print(f"[!] ham renk uzayi ayarlanamadi: {e}")


def _cikti_yolu(out, yol):
    """5.x: directory + file_name.  4.x: base_path."""
    if hasattr(out, "directory"):
        out.directory = yol
    else:
        out.base_path = yol


def _compositor(alfa):
    nt = _comp_agaci()
    nt.nodes.clear()

    rl = nt.nodes.new("CompositorNodeRLayers"); rl.location = (-700, 0)
    rl.scene = bpy.context.scene
    out = nt.nodes.new("CompositorNodeOutputFile"); out.location = (400, 0)
    out.name = ON + "out"
    _cikti_yolu(out, "//bake_cikti")
    # Dosya adi onekini bosalt: yoksa cikti "UnsavedBaseColor0001.png" olur
    # (kaydedilmemis blend adi one eklenir) ve asagi akista ad esleme zorlasir.
    if hasattr(out, "file_name"):
        out.file_name = ""
    # !! BLENDER 5.x TUZAGI -- OLCULDU: File Output'un media_type VARSAYILANI
    #    'MULTI_LAYER_IMAGE'. O hâlde file_format enum'u yalniz
    #    ('OPEN_EXR_MULTILAYER') icerir ve dugum, slot basina ayri dosya
    #    yerine TEK bir cok katmanli EXR yazar -- bake_to_gta.py bunu okuyamaz.
    #    'IMAGE'e cekmeden PNG atanamaz (TypeError) .
    if hasattr(out.format, "media_type"):
        out.format.media_type = "IMAGE"
    # PNG 8-bit: bake_to_gta.py'nin bekledigi format. EXR/JPEG DEGIL --
    # EXR'i GTA hatti okumaz, JPEG blok artifakti normal haritayi bozar.
    out.format.file_format = "PNG"
    out.format.color_mode = "RGB"
    out.format.color_depth = "8"
    out.format.compression = 15

    for ad, tip in (("BaseColor", "RGBA"), ("Roughness", "FLOAT"),
                    ("Normal", "RGBA"), ("AO", "FLOAT")):
        _slot_ekle(out, ad, tip)
    if alfa:
        _slot_ekle(out, "Alpha", "FLOAT")

    def rl_cikti(*adaylar):
        """Ilk bulunan soketi dondurur. OLCULDU: AO soketinin adi 5.2'de
        'Ambient Occlusion', eski surumlerde 'AO' -- ikisini de dene."""
        for ad in adaylar:
            for s in rl.outputs:
                if s.name == ad and s.enabled:
                    return s
        return None

    def baglan(slot_ad, *kaynak_adlari):
        k = rl_cikti(*kaynak_adlari)
        if k is None:
            print(f"[!] '{slot_ad}' baglanamadi -- RLayers'ta "
                  f"{kaynak_adlari} soketi yok. Pass acik mi?")
            return False
        nt.links.new(k, out.inputs[slot_ad])
        return True

    baglan("BaseColor", "Image")
    baglan("Roughness", "roughness")
    baglan("AO", "Ambient Occlusion", "AO")

    # --- normal: -1..1 -> 0..1 ------------------------------------------
    # Robin videoda iki MixRGB (add beyaz + multiply 0.5) kullaniyor;
    # VectorMath MULTIPLY_ADD ayni isi TEK dugumle yapar: n*0.5 + 0.5
    nrm = rl_cikti("Normal")
    if nrm is None:
        print("[!] normal baglanamadi -- use_pass_normal kapali olabilir")
    else:
        vm = nt.nodes.new("ShaderNodeVectorMath"); vm.location = (-200, -300)
        try:
            vm.operation = "MULTIPLY_ADD"
            vm.inputs[1].default_value = (0.5, 0.5, 0.5)
            vm.inputs[2].default_value = (0.5, 0.5, 0.5)
            nt.links.new(nrm, vm.inputs[0])
            son = vm.outputs[0]
        except TypeError:
            vm.operation = "MULTIPLY"
            vm.inputs[1].default_value = (0.5, 0.5, 0.5)
            ek = nt.nodes.new("ShaderNodeVectorMath"); ek.location = (0, -300)
            ek.operation = "ADD"
            ek.inputs[1].default_value = (0.5, 0.5, 0.5)
            nt.links.new(nrm, vm.inputs[0])
            nt.links.new(vm.outputs[0], ek.inputs[0])
            son = ek.outputs[0]
        nt.links.new(son, out.inputs["Normal"])

    # !! VERI HARITALARINA VIEW TRANSFORM UYGULANMAMALI.
    #    save_as_render=False ham degeri yazar. Normal/AO/Roughness/Alpha
    #    olcumdur, fotograf degil; tonlanirlarsa sessizce bozulurlar.
    for ad, kip in (("Normal", "RGB"), ("AO", "BW"), ("Roughness", "BW")):
        _slot_bicim(out, ad, file_format="PNG", color_mode=kip,
                    color_depth="8", save_as_render=False)
    if alfa and baglan("Alpha", "Alpha"):
        _slot_bicim(out, "Alpha", file_format="PNG", color_mode="BW",
                    color_depth="8", save_as_render=False)


# ----------------------------------------------------------------------
# 3. her materyale AOV Output ekle
# ----------------------------------------------------------------------
def aov_bagla(aov="roughness"):
    """bake_texture icindeki HER materyale AOV Output baglar.

    !! Bir materyal atlanirsa o yuzey roughness pass'inde SIYAH kalir ve
       hicbir hata cikmaz -- bu yuzden sonunda sayim raporlanir.
    """
    doku = bpy.data.collections.get(ON + "texture")
    if not doku:
        raise RuntimeError(f"'{ON}texture' yok -- once kur() calistir")

    mats, atlanan = set(), []
    for o in doku.all_objects:
        for sl in getattr(o, "material_slots", []):
            if sl.material:
                mats.add(sl.material)

    bagli = 0
    for m in mats:
        if not m.use_nodes:
            atlanan.append(f"{m.name} (use_nodes kapali)"); continue
        nt = m.node_tree
        cikti = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputAOV"
                      and n.name == aov), None)
        if cikti is None:
            cikti = nt.nodes.new("ShaderNodeOutputAOV")
            cikti.name = aov
            cikti.location = (400, -400)
        cikti.aov_name = aov

        bsdf = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
        if bsdf is None:
            atlanan.append(f"{m.name} (Principled BSDF yok)"); continue
        r = bsdf.inputs.get("Roughness")
        # Value soketine baglanir (Color'a DEGIL) -- AOV tipi VALUE.
        hedef = cikti.inputs["Value"]
        if r.is_linked:
            nt.links.new(r.links[0].from_socket, hedef)
        else:
            sab = nt.nodes.new("ShaderNodeValue")
            sab.location = (200, -500)
            sab.outputs[0].default_value = r.default_value
            nt.links.new(sab.outputs[0], hedef)
        bagli += 1

    print(f"[aov] {bagli}/{len(mats)} materyale '{aov}' baglandi")
    for a in atlanan:
        print(f"[!]   ATLANDI: {a}  -> bu yuzey roughness'ta SIYAH cikar")
    return bagli, atlanan


# ----------------------------------------------------------------------
# 4. render + dogrulama
# ----------------------------------------------------------------------
def render_et(klasor):
    out = _comp_agaci().nodes.get(ON + "out")
    if not out:
        raise RuntimeError("File Output node yok -- once kur()")
    _cikti_yolu(out, bpy.path.abspath(klasor))
    bpy.context.scene.frame_start = bpy.context.scene.frame_end = 1
    # !! File Output SADECE animasyon render'inda dosya yazar. F12 (still)
    #    ile hicbir sey yazilmaz ve hata da vermez.
    bpy.ops.render.render(animation=True)
    yol = getattr(out, "directory", None) or getattr(out, "base_path", "?")
    print(f"[render] -> {yol}")
    return yol


def dogrula():
    """Kurulumun sessiz hata ureten noktalarini tek tek denetler."""
    sah = bpy.context.scene
    vl = bpy.context.view_layer
    k = []
    ek = lambda ad, ok, not_="": k.append((ad, bool(ok), not_))

    doku = bpy.data.collections.get(ON + "texture")
    tiler = bpy.data.collections.get(ON + "tiler")
    ek("bake_texture koleksiyonu", doku)
    ek("tiler 8 kopya", tiler and len(tiler.objects) == 8,
       f"bulunan {len(tiler.objects) if tiler else 0}")
    ek("cozunurluk KARE", sah.render.resolution_x == sah.render.resolution_y,
       f"{sah.render.resolution_x}x{sah.render.resolution_y}")
    kam = sah.camera
    ek("kamera ortografik", kam and kam.data.type == "ORTHO")
    ek("ortho scale == 1", kam and abs(kam.data.ortho_scale - 1.0) < 1e-6,
       f"{kam.data.ortho_scale if kam else '-'}")
    ek("kamera duz asagi bakiyor",
       kam and all(abs(r) < 1e-4 for r in kam.rotation_euler),
       f"{[round(math.degrees(r), 2) for r in kam.rotation_euler] if kam else '-'}")
    ek("normal pass acik", vl.use_pass_normal)
    ek("'roughness' AOV tanimli", any(a.name == "roughness" for a in vl.aovs))
    ek("tek kare (start==end==1)", sah.frame_start == sah.frame_end == 1)

    nt = _comp_agaci()
    out = nt.nodes.get(ON + "out")
    ek("File Output node", out)
    if out:
        # son giris 5.x'te bos 'ekleme' soketidir (type CUSTOM) -- sayma
        bagsiz = [s.name for s in out.inputs
                  if not s.is_linked and s.type != "CUSTOM" and s.name]
        ek("tum slotlar bagli", not bagsiz, f"bagsiz: {bagsiz}")
        ek("cikti PNG", out.format.file_format == "PNG", out.format.file_format)
        # veri haritalarina view transform uygulanmis mi
        tonlu = [s.name for s in (_slot(out, x.name) for x in out.inputs
                                  if x.name and x.type != "CUSTOM")
                 if s.name != "BaseColor" and getattr(s, "save_as_render", False)]
        ek("veri haritalari ham (save_as_render kapali)", not tonlu,
           f"tonlanan: {tonlu}")
    ek("view transform tonlayici degil",
       sah.view_settings.view_transform in ("Standard", "Raw"),
       sah.view_settings.view_transform)
    ek("render motoru CYCLES", sah.render.engine == "CYCLES", sah.render.engine)

    # !! KADRAJDA YABANCI MESH VAR MI -- duz/bos harita hatasinin sebebi
    bizim = set()
    for ad in (ON + "texture", ON + "tiler"):
        c = bpy.data.collections.get(ad)
        if c:
            bizim.update(o.name for o in c.all_objects)
    kirli = [o.name for o in sah.objects
             if o.type == "MESH" and not o.hide_render
             and o.name not in bizim and not o.name.startswith(ON)]
    ek("kadrajda yabanci mesh yok", not kirli, f"render edilecek: {kirli}")

    if doku and not any(o.type == "MESH" for o in doku.all_objects):
        print("  [BEKL] bake_texture'da mesh yok")

    if doku:
        mats = {sl.material for o in doku.all_objects
                for sl in getattr(o, "material_slots", []) if sl.material}
        if not mats:
            # !! BOS KUMEYI BASARISIZLIK SAYMA. Malzeme henuz konmadiysa bu
            #    bir hata degil, sadece siradaki adimdir.
            print("  [BEKL] bake_texture bos -- malzemeni koy, sonra aov_bagla()")
        else:
            eksik = [m.name for m in mats
                     if not any(n.bl_idname == "ShaderNodeOutputAOV" for n in
                                (m.node_tree.nodes if m.use_nodes else []))]
            ek("her materyalde AOV Output", not eksik, f"eksik: {eksik}")

    kotu = [x for x in k if not x[1]]
    for ad, ok, not_ in k:
        print(f"  [{'OK ' if ok else 'HATA'}] {ad}" + (f"   ({not_})" if not_ else ""))
    print("TUM DENETIMLER GECTI" if not kotu else f"{len(kotu)} DENETIM BASARISIZ")
    return not kotu


if __name__ == "__main__":
    kur()
