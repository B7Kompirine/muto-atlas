# gen_crane_meta.py — generates the .ytyp + 3 .ymap XML files for des_crane (RECIPE A).
# The fields are measured from des_stilthouse; see the former RayFire reference (2.5.0)
import os, sys
import xml.etree.ElementTree as ET

POSITION = (47.20, -460.52, 38.80)          # centre of the crane base = drawable origin
# The only argument is the output folder; an option such as --help must never become a folder name.
if any(a in ("-h", "--help") for a in sys.argv[1:]):
    print("usage: python gen_crane_meta.py [output folder]")
    sys.exit(0)
if len(sys.argv) > 1 and sys.argv[1].startswith("-"):
    sys.exit("unknown option: %s (usage: python gen_crane_meta.py [output folder])" % sys.argv[1])
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

BOXES = {
    "des_crane_root":   ((-17.5, -79.0, -13.2), (107.0, 13.5, 71.6)),  # the WHOLE animation
    "des_crane_debris": (( -4.0, -79.0, -11.5), (107.0,  6.5, 10.3)),
    "des_crane_intact": ((-17.2, -79.0,  -1.8), (107.0, 13.2, 70.4)),
    "des_crane_road":   (( -4.5,-130.9,-10.2), (158.4, 23.6,  5.0)),   # vanilla road minus the collapsing slice
    "des_crane_ov":     ((-16.2,-103.7, -6.7), (157.2,  9.9,  4.1)),   # road DECAL minus the collapsing slice
}

def sphere(mn, mx):
    c = tuple((mn[k] + mx[k]) / 2 for k in range(3))
    r = sum(((mx[k] - mn[k]) / 2) ** 2 for k in range(3)) ** 0.5
    return c, r

def vec(a, tag, v): ET.SubElement(a, tag, {'x': repr(v[0]), 'y': repr(v[1]), 'z': repr(v[2])})
def val(a, tag, v): ET.SubElement(a, tag, {'value': str(v)})
def txt(a, tag, v=""): ET.SubElement(a, tag).text = v

def archetype(parent, name, flags, lod, clip):
    mn, mx = BOXES[name]; c, r = sphere(mn, mx)
    it = ET.SubElement(parent, 'Item', {'type': 'CBaseArchetypeDef'})
    val(it, 'lodDist', lod); val(it, 'flags', flags); val(it, 'specialAttribute', 0)
    vec(it, 'bbMin', mn); vec(it, 'bbMax', mx); vec(it, 'bsCentre', c)
    val(it, 'bsRadius', round(r, 5)); val(it, 'hdTextureDist', 5)
    txt(it, 'name', name); txt(it, 'textureDictionary', 'des_crane')
    txt(it, 'clipDictionary', clip)
    txt(it, 'drawableDictionary', ''); txt(it, 'physicsDictionary', '')
    txt(it, 'assetName', name); txt(it, 'assetType', 'ASSET_TYPE_DRAWABLE')
    ET.SubElement(it, 'extensions')

def make_ytyp():
    r = ET.Element('CMapTypes'); ET.SubElement(r, 'extensions')
    ar = ET.SubElement(r, 'archetypes')
    archetype(ar, 'des_crane_root',   536871424, 400, 'des_crane')   # Has Anim + Use Ambient Scale
    archetype(ar, 'des_crane_debris',        32, 400, '')            # static debris
    archetype(ar, 'des_crane_intact',        32, 400, '')            # static intact state
    archetype(ar, 'des_crane_road',          32, 700, '')
    archetype(ar, 'des_crane_ov',            32, 700, '')            # the REST of the vanilla road
    txt(r, 'name', 'des_crane')
    ce = ET.SubElement(r, 'compositeEntityTypes'); it = ET.SubElement(ce, 'Item')
    val(it, 'lodDist', -1); val(it, 'flags', 536870912); val(it, 'specialAttribute', 0)
    mn, mx = BOXES['des_crane_root']; c, rad = sphere(mn, mx)
    vec(it, 'bbMin', mn); vec(it, 'bbMax', mx); vec(it, 'bsCentre', c)
    val(it, 'bsRadius', round(rad, 5))
    txt(it, 'Name', 'des_crane')
    txt(it, 'StartModel', ''); txt(it, 'EndModel', '')            # pattern A: imap swap
    txt(it, 'StartImapFile', 'des_crane_start')
    txt(it, 'EndImapFile', 'des_crane_end')
    txt(it, 'PtFxAssetName', '')
    an = ET.SubElement(it, 'Animations'); ai = ET.SubElement(an, 'Item')
    txt(ai, 'AnimDict', 'des_crane')
    txt(ai, 'AnimName', 'des_crane_root')       # = AnimatedModel = archetype name
    txt(ai, 'AnimatedModel', 'des_crane_root')
    val(ai, 'punchInPhase', 0); val(ai, 'punchOutPhase', 1)
    ET.SubElement(ai, 'effectsData')
    return r

def jenkins(k):
    h = 0
    for c in k.lower():
        h = (h + ord(c)) & 0xFFFFFFFF; h = (h + (h << 10)) & 0xFFFFFFFF; h ^= (h >> 6)
    h = (h + (h << 3)) & 0xFFFFFFFF; h ^= (h >> 11); h = (h + (h << 15)) & 0xFFFFFFFF
    return h

def entity(parent, name, lod):
    it = ET.SubElement(parent, 'Item', {'type': 'CEntityDef'})
    txt(it, 'archetypeName', name); val(it, 'flags', 1572864)
    # Python hash() is seeded randomly per process -> a different guid on every run.
    # Jenkins is deterministic: the same name always gives the same guid.
    val(it, 'guid', jenkins(name) % 4000000000)
    vec(it, 'position', POSITION)
    ET.SubElement(it, 'rotation', {'x': '0', 'y': '0', 'z': '0', 'w': '1'})
    val(it, 'scaleXY', 1); val(it, 'scaleZ', 1); val(it, 'parentIndex', -1)
    val(it, 'lodDist', lod); val(it, 'childLodDist', 0)
    txt(it, 'lodLevel', 'LODTYPES_DEPTH_ORPHANHD'); val(it, 'numChildren', 0)
    txt(it, 'priorityLevel', 'PRI_REQUIRED'); ET.SubElement(it, 'extensions')
    val(it, 'ambientOcclusionMultiplier', 255); val(it, 'artificialAmbientOcclusion', 255)
    val(it, 'tintValue', 0)

def make_ymap(name, entries, ymflags, cflags, box=None):
    r = ET.Element('CMapData')
    txt(r, 'name', name); txt(r, 'parent', '')
    val(r, 'flags', ymflags); val(r, 'contentFlags', cflags)
    # ⛔ COMPUTE THE EXTENTS. The "calculate flags and extents" step in CodeWalker.
    # An entity that is not INSIDE the extent SILENTLY NEVER SHOWS -- and raises no error either.
    # Measured: des_crane_start left 65 m of the intact crane outside, _end left 5 m
    # of the debris. Do not write the box BY HAND; derive it from the UNION of the entities.
    mn = [ 1e9] * 3
    mx = [-1e9] * 3
    for a, _lod in entries:
        for k in range(3):
            mn[k] = min(mn[k], POSITION[k] + BOXES[a][0][k])
            mx[k] = max(mx[k], POSITION[k] + BOXES[a][1][k])
    mn = tuple(mn); mx = tuple(mx)
    vec(r, 'streamingExtentsMin', tuple(mn[k] - 200 for k in range(3)))
    vec(r, 'streamingExtentsMax', tuple(mx[k] + 200 for k in range(3)))
    vec(r, 'entitiesExtentsMin', mn); vec(r, 'entitiesExtentsMax', mx)
    en = ET.SubElement(r, 'entities')
    for a, lod in entries: entity(en, a, lod)
    for t in ('containerLods','boxOccluders','occludeModels','physicsDictionaries',
              'instancedData','timeCycleModifiers','carGenerators'):
        ET.SubElement(r, t)
    ET.SubElement(r, 'LODLightsSOA'); ET.SubElement(r, 'DistantLODLightsSOA')
    bl = ET.SubElement(r, 'block')
    val(bl, 'version', 0); val(bl, 'flags', 0)
    txt(bl, 'name', name); txt(bl, 'exportedBy', 'muto'); txt(bl, 'owner', ''); txt(bl, 'time', '')
    return r

def write(el, path):
    ET.indent(el, ' '); ET.ElementTree(el).write(path, encoding='utf-8', xml_declaration=True)
    print("  ->", os.path.basename(path))

os.makedirs(OUT_DIR, exist_ok=True)
write(make_ytyp(), os.path.join(OUT_DIR, 'des_crane.ytyp.xml'))
# ⛔ THE START IMAP IS NEVER EMPTY. A CMapData with 0 entities crashes the engine
# (ACCESS_VIOLATION, null+0x11). Measured: the working des_mytest_start has 1 entity.
write(make_ymap('des_crane_start', [('des_crane_intact', 400)], 1, 65),
      os.path.join(OUT_DIR, 'des_crane_start.ymap.xml'))
write(make_ymap('des_crane_end', [('des_crane_debris', 400)], 1, 65),
      os.path.join(OUT_DIR, 'des_crane_end.ymap.xml'))
BOXES['des_crane'] = BOXES['des_crane_root']      # box of the composite entity = extent of the animation
write(make_ymap('des_crane_placer', [('des_crane', 400), ('des_crane_road', 700), ('des_crane_ov', 700)], 0, 65),
      os.path.join(OUT_DIR, 'des_crane_placer.ymap.xml'))
