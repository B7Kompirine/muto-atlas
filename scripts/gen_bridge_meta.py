# gen_bridge_meta.py -- des_kopru icin .ytyp + 3 .ymap XML uretir (RECETE A).
#
# MIMARI (referans §11): kalici geometri durum imap'ine KONMAZ.
#   start   des_kopru_saglam        kirilan dilimin saglam hali   (kapanir)
#   end     des_kopru_anim_enkaz    enkaz                          (acilir)
#   placer  des_kopru (composite) + des_kopru_kalan               (HEP ACIK)
#
# Onceki kurulumda start'ta 205x154 m'lik TUM kopru vardi; tetiklenince
# hepsi yok oluyor, geri gelen yalnizca 82x69 m'lik enkazdi. Belirti:
# korkuluklar kaybolur, yolda delik acilir, decal'lar havada kalir.
import os, sys
import xml.etree.ElementTree as ET

KONUM = (766.66, -35.85, 57.59)
CIKTI = sys.argv[1] if len(sys.argv) > 1 else "."

# Blender'da vertex'lerden olculdu (bound_box BAYAT olabiliyor, ona guvenme)
KUTU = {
    # animasyonlu: kutu animasyonun TAMAMINI kapsar (31 karede tarandi + 0.6 pay)
    "des_kopru_anim":       ((-53.98, -29.37, -0.60), (29.65, 40.30, 30.98)),
    "des_kopru_anim_enkaz": ((-53.40, -28.80,  0.00), (29.10, 39.70, 30.40)),
    # z tavani 33.7: sokak lambalari (9.3 m) modele katildi
    "des_kopru_saglam":     ((-44.75, -28.77,  0.18), (28.38, 37.69, 33.70)),
    "des_kopru_kalan":      ((-102.53, -77.19, 3.13), (102.53, 77.19, 32.11)),
}
KUTU["des_kopru"] = ((-102.53, -77.19, -0.60), (102.53, 77.19, 32.11))   # hepsinin birlesimi

def kure(mn, mx):
    c = tuple((mn[k] + mx[k]) / 2 for k in range(3))
    r = sum(((mx[k] - mn[k]) / 2) ** 2 for k in range(3)) ** 0.5
    return c, r

def vek(a, tag, v): ET.SubElement(a, tag, {'x': repr(round(v[0],4)), 'y': repr(round(v[1],4)), 'z': repr(round(v[2],4))})
def deg(a, tag, v): ET.SubElement(a, tag, {'value': str(v)})
def met(a, tag, v=""): ET.SubElement(a, tag).text = v

# physicsDictionary: gomulu Bound Composite tasiyan arketiplerde MODEL ADI yazilir.
# Bos birakilirsa .ydr'deki collision motor tarafindan hic baglanmaz.
FIZIK = {'des_kopru_saglam', 'des_kopru_anim_enkaz'}   # gomulu Bound tasiyanlar

def arketip(ana, ad, flags, lod, klip):
    mn, mx = KUTU[ad]; c, r = kure(mn, mx)
    it = ET.SubElement(ana, 'Item', {'type': 'CBaseArchetypeDef'})
    deg(it, 'lodDist', lod); deg(it, 'flags', flags); deg(it, 'specialAttribute', 0)
    vek(it, 'bbMin', mn); vek(it, 'bbMax', mx); vek(it, 'bsCentre', c)
    deg(it, 'bsRadius', round(r, 5)); deg(it, 'hdTextureDist', 5)
    met(it, 'name', ad); met(it, 'textureDictionary', ad)
    met(it, 'clipDictionary', klip)
    met(it, 'drawableDictionary', '')
    met(it, 'physicsDictionary', ad if ad in FIZIK else '')
    met(it, 'assetName', ad); met(it, 'assetType', 'ASSET_TYPE_DRAWABLE')
    ET.SubElement(it, 'extensions')

def uret_ytyp():
    r = ET.Element('CMapTypes'); ET.SubElement(r, 'extensions')
    ar = ET.SubElement(r, 'archetypes')
    arketip(ar, 'des_kopru_anim',       536871424, 600, 'des_kopru')   # Has Anim + Use Ambient Scale
    arketip(ar, 'des_kopru_anim_enkaz',        32, 600, '')
    arketip(ar, 'des_kopru_saglam',            32, 600, '')
    arketip(ar, 'des_kopru_kalan',             32, 900, '')            # kalici, uzaktan da gorunur
    met(r, 'name', 'des_kopru')
    ET.SubElement(r, 'dependencies')
    ce = ET.SubElement(r, 'compositeEntityTypes', {'itemType': 'CCompositeEntityType'})
    it = ET.SubElement(ce, 'Item')
    met(it, 'Name', 'des_kopru')
    deg(it, 'lodDist', -1); deg(it, 'flags', 536870912); deg(it, 'specialAttribute', 0)
    mn, mx = KUTU['des_kopru']; c, rad = kure(mn, mx)
    vek(it, 'bbMin', mn); vek(it, 'bbMax', mx); vek(it, 'bsCentre', c)
    deg(it, 'bsRadius', round(rad, 5))
    met(it, 'StartModel', ''); met(it, 'EndModel', '')       # desen A: imap takasi
    met(it, 'StartImapFile', 'des_kopru_start')
    met(it, 'EndImapFile', 'des_kopru_end')
    met(it, 'PtFxAssetName')
    an = ET.SubElement(it, 'Animations', {'itemType': 'CCompEntityAnims'})
    ai = ET.SubElement(an, 'Item')
    met(ai, 'AnimDict', 'des_kopru')
    met(ai, 'AnimName', 'des_kopru_anim')          # = AnimatedModel = arketip adi
    met(ai, 'AnimatedModel', 'des_kopru_anim')
    deg(ai, 'punchInPhase', 0); deg(ai, 'punchOutPhase', 1)
    ET.SubElement(ai, 'effectsData', {'itemType': 'CCompEntityEffectsData'})
    return r

def jenkins(k):
    h = 0
    for c in k.lower():
        h = (h + ord(c)) & 0xFFFFFFFF; h = (h + (h << 10)) & 0xFFFFFFFF; h ^= (h >> 6)
    h = (h + (h << 3)) & 0xFFFFFFFF; h ^= (h >> 11); h = (h + (h << 15)) & 0xFFFFFFFF
    return h

def entity(ana, ad, lod):
    it = ET.SubElement(ana, 'Item', {'type': 'CEntityDef'})
    met(it, 'archetypeName', ad); deg(it, 'flags', 1572864)
    deg(it, 'guid', jenkins(ad) % 4000000000)          # deterministik
    vek(it, 'position', KONUM)
    ET.SubElement(it, 'rotation', {'x': '0', 'y': '0', 'z': '0', 'w': '1'})
    deg(it, 'scaleXY', 1); deg(it, 'scaleZ', 1); deg(it, 'parentIndex', -1)
    deg(it, 'lodDist', lod); deg(it, 'childLodDist', 0)
    met(it, 'lodLevel', 'LODTYPES_DEPTH_ORPHANHD'); deg(it, 'numChildren', 0)
    met(it, 'priorityLevel', 'PRI_REQUIRED'); ET.SubElement(it, 'extensions')
    deg(it, 'ambientOcclusionMultiplier', 255); deg(it, 'artificialAmbientOcclusion', 255)
    deg(it, 'tintValue', 0)

def uret_ymap(ad, liste, ymflags, cflags):
    r = ET.Element('CMapData')
    met(r, 'name', ad); met(r, 'parent', '')
    deg(r, 'flags', ymflags); deg(r, 'contentFlags', cflags)
    # Extent ICINDE kalmayan entity SESSIZCE hic gorunmez -> birlesimden hesapla.
    mn = [1e9]*3; mx = [-1e9]*3
    for a, _l in liste:
        for k in range(3):
            mn[k] = min(mn[k], KONUM[k] + KUTU[a][0][k])
            mx[k] = max(mx[k], KONUM[k] + KUTU[a][1][k])
    mn = tuple(mn); mx = tuple(mx)
    vek(r, 'streamingExtentsMin', tuple(mn[k]-200 for k in range(3)))
    vek(r, 'streamingExtentsMax', tuple(mx[k]+200 for k in range(3)))
    vek(r, 'entitiesExtentsMin', mn); vek(r, 'entitiesExtentsMax', mx)
    en = ET.SubElement(r, 'entities')
    for a, lod in liste: entity(en, a, lod)
    for t in ('containerLods','boxOccluders','occludeModels','physicsDictionaries',
              'instancedData','timeCycleModifiers','carGenerators'):
        ET.SubElement(r, t)
    ET.SubElement(r, 'LODLightsSOA'); ET.SubElement(r, 'DistantLODLightsSOA')
    bl = ET.SubElement(r, 'block')
    deg(bl, 'version', 0); deg(bl, 'flags', 0)
    met(bl, 'name', ad); met(bl, 'exportedBy', 'muto'); met(bl, 'owner', ''); met(bl, 'time', '')
    return r

def yaz(el, yol):
    ET.indent(el, ' '); ET.ElementTree(el).write(yol, encoding='utf-8', xml_declaration=True)
    print("  ->", os.path.basename(yol))

os.makedirs(CIKTI, exist_ok=True)
yaz(uret_ytyp(), os.path.join(CIKTI, 'des_kopru.ytyp.xml'))
# start ASLA bos olmaz (0 entity'li CMapData motoru cokertir: null+0x11)
yaz(uret_ymap('des_kopru_start',  [('des_kopru_saglam', -1)], 1, 577),
    os.path.join(CIKTI, 'des_kopru_start.ymap.xml'))
yaz(uret_ymap('des_kopru_end',    [('des_kopru_anim_enkaz', -1)], 1, 65),
    os.path.join(CIKTI, 'des_kopru_end.ymap.xml'))
# placer: composite + KALICI geometri
yaz(uret_ymap('des_kopru_placer', [('des_kopru', 100), ('des_kopru_kalan', 700)], 0, 65),
    os.path.join(CIKTI, 'des_kopru_placer.ymap.xml'))
print("KONUM:", KONUM)
