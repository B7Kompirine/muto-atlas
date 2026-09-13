# gen_crane_meta.py — des_crane icin .ytyp + 3 .ymap XML uretir (RECETE A).
# Alanlar des_stilthouse'tan olculmustur; bkz rayfire-des-uretim.md
import os, sys
import xml.etree.ElementTree as ET

KONUM = (47.20, -460.52, 38.80)          # vincin taban merkezi = drawable origin
CIKTI = sys.argv[1] if len(sys.argv) > 1 else "."

KUTU = {
    "des_crane_root":  ((-17.5, -79.0, -13.2), (107.0, 13.5, 71.6)),  # animasyonun TAMAMI
    "des_crane_enkaz": (( -4.0, -79.0, -11.5), (107.0,  6.5, 10.3)),
    "des_crane_saglam":((-17.2, -79.0,  -1.8), (107.0, 13.2, 70.4)),
    "des_crane_yol":   (( -4.5,-130.9,-10.2), (158.4, 23.6,  5.0)),   # vanilla yol eksi coken dilim
    "des_crane_ov":    ((-16.2,-103.7, -6.7), (157.2,  9.9,  4.1)),   # yol DECAL'i eksi coken dilim
}

def kure(mn, mx):
    c = tuple((mn[k] + mx[k]) / 2 for k in range(3))
    r = sum(((mx[k] - mn[k]) / 2) ** 2 for k in range(3)) ** 0.5
    return c, r

def vek(a, tag, v): ET.SubElement(a, tag, {'x': repr(v[0]), 'y': repr(v[1]), 'z': repr(v[2])})
def deg(a, tag, v): ET.SubElement(a, tag, {'value': str(v)})
def met(a, tag, v=""): ET.SubElement(a, tag).text = v

def arketip(ana, ad, flags, lod, klip):
    mn, mx = KUTU[ad]; c, r = kure(mn, mx)
    it = ET.SubElement(ana, 'Item', {'type': 'CBaseArchetypeDef'})
    deg(it, 'lodDist', lod); deg(it, 'flags', flags); deg(it, 'specialAttribute', 0)
    vek(it, 'bbMin', mn); vek(it, 'bbMax', mx); vek(it, 'bsCentre', c)
    deg(it, 'bsRadius', round(r, 5)); deg(it, 'hdTextureDist', 5)
    met(it, 'name', ad); met(it, 'textureDictionary', 'des_crane')
    met(it, 'clipDictionary', klip)
    met(it, 'drawableDictionary', ''); met(it, 'physicsDictionary', '')
    met(it, 'assetName', ad); met(it, 'assetType', 'ASSET_TYPE_DRAWABLE')
    ET.SubElement(it, 'extensions')

def uret_ytyp():
    r = ET.Element('CMapTypes'); ET.SubElement(r, 'extensions')
    ar = ET.SubElement(r, 'archetypes')
    arketip(ar, 'des_crane_root',  536871424, 400, 'des_crane')   # Has Anim + Use Ambient Scale
    arketip(ar, 'des_crane_enkaz',        32, 400, '')            # statik enkaz
    arketip(ar, 'des_crane_saglam',       32, 400, '')            # statik saglam hal
    arketip(ar, 'des_crane_yol',          32, 700, '')
    arketip(ar, 'des_crane_ov',           32, 700, '')            # vanilla yolun KALANI
    met(r, 'name', 'des_crane')
    ce = ET.SubElement(r, 'compositeEntityTypes'); it = ET.SubElement(ce, 'Item')
    deg(it, 'lodDist', -1); deg(it, 'flags', 536870912); deg(it, 'specialAttribute', 0)
    mn, mx = KUTU['des_crane_root']; c, rad = kure(mn, mx)
    vek(it, 'bbMin', mn); vek(it, 'bbMax', mx); vek(it, 'bsCentre', c)
    deg(it, 'bsRadius', round(rad, 5))
    met(it, 'Name', 'des_crane')
    met(it, 'StartModel', ''); met(it, 'EndModel', '')            # desen A: imap takasi
    met(it, 'StartImapFile', 'des_crane_start')
    met(it, 'EndImapFile', 'des_crane_end')
    met(it, 'PtFxAssetName', '')
    an = ET.SubElement(it, 'Animations'); ai = ET.SubElement(an, 'Item')
    met(ai, 'AnimDict', 'des_crane')
    met(ai, 'AnimName', 'des_crane_root')       # = AnimatedModel = arketip adi
    met(ai, 'AnimatedModel', 'des_crane_root')
    deg(ai, 'punchInPhase', 0); deg(ai, 'punchOutPhase', 1)
    ET.SubElement(ai, 'effectsData')
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
    # Python hash() sureç basina rastgele tohumlanir -> her uretimde baska guid.
    # Jenkins deterministik: ayni ad daima ayni guid.
    deg(it, 'guid', jenkins(ad) % 4000000000)
    vek(it, 'position', KONUM)
    ET.SubElement(it, 'rotation', {'x': '0', 'y': '0', 'z': '0', 'w': '1'})
    deg(it, 'scaleXY', 1); deg(it, 'scaleZ', 1); deg(it, 'parentIndex', -1)
    deg(it, 'lodDist', lod); deg(it, 'childLodDist', 0)
    met(it, 'lodLevel', 'LODTYPES_DEPTH_ORPHANHD'); deg(it, 'numChildren', 0)
    met(it, 'priorityLevel', 'PRI_REQUIRED'); ET.SubElement(it, 'extensions')
    deg(it, 'ambientOcclusionMultiplier', 255); deg(it, 'artificialAmbientOcclusion', 255)
    deg(it, 'tintValue', 0)

def uret_ymap(ad, liste, ymflags, cflags, kutu=None):
    r = ET.Element('CMapData')
    met(r, 'name', ad); met(r, 'parent', '')
    deg(r, 'flags', ymflags); deg(r, 'contentFlags', cflags)
    # ⛔ EXTENT HESAPLA. CodeWalker'daki "calculate flags and extents" adimi.
    # Extent ICINDE kalmayan entity SESSIZCE HIC GORUNMEZ -- hata da vermez.
    # Olculdu: des_crane_start saglam vincin 65 m'sini, _end enkazin 5 m'sini
    # disarida birakiyordu. Kutuyu ELLE yazma; entity'lerin BIRLESIMINDEN cikar.
    mn = [ 1e9] * 3
    mx = [-1e9] * 3
    for a, _lod in liste:
        for k in range(3):
            mn[k] = min(mn[k], KONUM[k] + KUTU[a][0][k])
            mx[k] = max(mx[k], KONUM[k] + KUTU[a][1][k])
    mn = tuple(mn); mx = tuple(mx)
    vek(r, 'streamingExtentsMin', tuple(mn[k] - 200 for k in range(3)))
    vek(r, 'streamingExtentsMax', tuple(mx[k] + 200 for k in range(3)))
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
yaz(uret_ytyp(), os.path.join(CIKTI, 'des_crane.ytyp.xml'))
# ⛔ START IMAP ASLA BOS OLMAZ. 0 entity'li CMapData motoru cokertiyor
# (ACCESS_VIOLATION, null+0x11). Olculdu: calisan des_mytest_start'ta 1 entity var.
yaz(uret_ymap('des_crane_start', [('des_crane_saglam', 400)], 1, 65),
    os.path.join(CIKTI, 'des_crane_start.ymap.xml'))
yaz(uret_ymap('des_crane_end', [('des_crane_enkaz', 400)], 1, 65),
    os.path.join(CIKTI, 'des_crane_end.ymap.xml'))
KUTU['des_crane'] = KUTU['des_crane_root']      # composite entity'nin kutusu = animasyon uzanimi
yaz(uret_ymap('des_crane_placer', [('des_crane', 400), ('des_crane_yol', 700), ('des_crane_ov', 700)], 0, 65),
    os.path.join(CIKTI, 'des_crane_placer.ymap.xml'))
