# gen_bridge_meta.py -- generates the .ytyp + 3 .ymap XML files for des_bridge (RECIPE A).
#
# ARCHITECTURE (reference §11): permanent geometry is NOT put in a state imap.
#   start   des_bridge_intact        intact state of the slice that breaks   (switched off)
#   end     des_bridge_anim_debris   debris                                  (switched on)
#   placer  des_bridge (composite) + des_bridge_rest                        (ALWAYS ON)
#
# In the previous setup start held the WHOLE 205x154 m bridge; on trigger all
# of it vanished and only the 82x69 m debris came back. Symptom: the railings
# disappear, a hole opens in the road, the decals are left hanging in the air.
import os, sys
import xml.etree.ElementTree as ET

POSITION = (766.66, -35.85, 57.59)
# The only argument is the output folder; an option such as --help must never become a folder name.
if any(a in ("-h", "--help") for a in sys.argv[1:]):
    print("usage: python gen_bridge_meta.py [output folder]")
    sys.exit(0)
if len(sys.argv) > 1 and sys.argv[1].startswith("-"):
    sys.exit("unknown option: %s (usage: python gen_bridge_meta.py [output folder])" % sys.argv[1])
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

# Measured from the vertices in Blender (bound_box can be STALE, do not trust it)
BOXES = {
    # animated: the box covers the WHOLE animation (scanned over 31 frames + 0.6 margin)
    "des_bridge_anim":        ((-53.98, -29.37, -0.60), (29.65, 40.30, 30.98)),
    "des_bridge_anim_debris": ((-53.40, -28.80,  0.00), (29.10, 39.70, 30.40)),
    # z ceiling 33.7: the street lamps (9.3 m) were added to the model
    "des_bridge_intact":      ((-44.75, -28.77,  0.18), (28.38, 37.69, 33.70)),
    "des_bridge_rest":        ((-102.53, -77.19, 3.13), (102.53, 77.19, 32.11)),
}
BOXES["des_bridge"] = ((-102.53, -77.19, -0.60), (102.53, 77.19, 32.11))   # union of all of them

def sphere(mn, mx):
    c = tuple((mn[k] + mx[k]) / 2 for k in range(3))
    r = sum(((mx[k] - mn[k]) / 2) ** 2 for k in range(3)) ** 0.5
    return c, r

def vec(a, tag, v): ET.SubElement(a, tag, {'x': repr(round(v[0],4)), 'y': repr(round(v[1],4)), 'z': repr(round(v[2],4))})
def val(a, tag, v): ET.SubElement(a, tag, {'value': str(v)})
def txt(a, tag, v=""): ET.SubElement(a, tag).text = v

# physicsDictionary: archetypes that carry an embedded Bound Composite get the MODEL NAME here.
# Left empty, the engine never attaches the collision inside the .ydr.
PHYSICS = {'des_bridge_intact', 'des_bridge_anim_debris'}   # the ones carrying an embedded Bound

def archetype(parent, name, flags, lod, clip):
    mn, mx = BOXES[name]; c, r = sphere(mn, mx)
    it = ET.SubElement(parent, 'Item', {'type': 'CBaseArchetypeDef'})
    val(it, 'lodDist', lod); val(it, 'flags', flags); val(it, 'specialAttribute', 0)
    vec(it, 'bbMin', mn); vec(it, 'bbMax', mx); vec(it, 'bsCentre', c)
    val(it, 'bsRadius', round(r, 5)); val(it, 'hdTextureDist', 5)
    txt(it, 'name', name); txt(it, 'textureDictionary', name)
    txt(it, 'clipDictionary', clip)
    txt(it, 'drawableDictionary', '')
    txt(it, 'physicsDictionary', name if name in PHYSICS else '')
    txt(it, 'assetName', name); txt(it, 'assetType', 'ASSET_TYPE_DRAWABLE')
    ET.SubElement(it, 'extensions')

def make_ytyp():
    r = ET.Element('CMapTypes'); ET.SubElement(r, 'extensions')
    ar = ET.SubElement(r, 'archetypes')
    archetype(ar, 'des_bridge_anim',        536871424, 600, 'des_bridge')   # Has Anim + Use Ambient Scale
    archetype(ar, 'des_bridge_anim_debris',        32, 600, '')
    archetype(ar, 'des_bridge_intact',             32, 600, '')
    archetype(ar, 'des_bridge_rest',               32, 900, '')            # permanent, visible from afar too
    txt(r, 'name', 'des_bridge')
    ET.SubElement(r, 'dependencies')
    ce = ET.SubElement(r, 'compositeEntityTypes', {'itemType': 'CCompositeEntityType'})
    it = ET.SubElement(ce, 'Item')
    txt(it, 'Name', 'des_bridge')
    val(it, 'lodDist', -1); val(it, 'flags', 536870912); val(it, 'specialAttribute', 0)
    mn, mx = BOXES['des_bridge']; c, rad = sphere(mn, mx)
    vec(it, 'bbMin', mn); vec(it, 'bbMax', mx); vec(it, 'bsCentre', c)
    val(it, 'bsRadius', round(rad, 5))
    txt(it, 'StartModel', ''); txt(it, 'EndModel', '')       # pattern A: imap swap
    txt(it, 'StartImapFile', 'des_bridge_start')
    txt(it, 'EndImapFile', 'des_bridge_end')
    txt(it, 'PtFxAssetName')
    an = ET.SubElement(it, 'Animations', {'itemType': 'CCompEntityAnims'})
    ai = ET.SubElement(an, 'Item')
    txt(ai, 'AnimDict', 'des_bridge')
    txt(ai, 'AnimName', 'des_bridge_anim')          # = AnimatedModel = archetype name
    txt(ai, 'AnimatedModel', 'des_bridge_anim')
    val(ai, 'punchInPhase', 0); val(ai, 'punchOutPhase', 1)
    ET.SubElement(ai, 'effectsData', {'itemType': 'CCompEntityEffectsData'})
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
    val(it, 'guid', jenkins(name) % 4000000000)          # deterministic
    vec(it, 'position', POSITION)
    ET.SubElement(it, 'rotation', {'x': '0', 'y': '0', 'z': '0', 'w': '1'})
    val(it, 'scaleXY', 1); val(it, 'scaleZ', 1); val(it, 'parentIndex', -1)
    val(it, 'lodDist', lod); val(it, 'childLodDist', 0)
    txt(it, 'lodLevel', 'LODTYPES_DEPTH_ORPHANHD'); val(it, 'numChildren', 0)
    txt(it, 'priorityLevel', 'PRI_REQUIRED'); ET.SubElement(it, 'extensions')
    val(it, 'ambientOcclusionMultiplier', 255); val(it, 'artificialAmbientOcclusion', 255)
    val(it, 'tintValue', 0)

def make_ymap(name, entries, ymflags, cflags):
    r = ET.Element('CMapData')
    txt(r, 'name', name); txt(r, 'parent', '')
    val(r, 'flags', ymflags); val(r, 'contentFlags', cflags)
    # An entity that is not INSIDE the extent SILENTLY never shows -> compute it from the union.
    mn = [1e9]*3; mx = [-1e9]*3
    for a, _lod in entries:
        for k in range(3):
            mn[k] = min(mn[k], POSITION[k] + BOXES[a][0][k])
            mx[k] = max(mx[k], POSITION[k] + BOXES[a][1][k])
    mn = tuple(mn); mx = tuple(mx)
    vec(r, 'streamingExtentsMin', tuple(mn[k]-200 for k in range(3)))
    vec(r, 'streamingExtentsMax', tuple(mx[k]+200 for k in range(3)))
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
write(make_ytyp(), os.path.join(OUT_DIR, 'des_bridge.ytyp.xml'))
# start is NEVER empty (a CMapData with 0 entities crashes the engine: null+0x11)
write(make_ymap('des_bridge_start',  [('des_bridge_intact', -1)], 1, 577),
      os.path.join(OUT_DIR, 'des_bridge_start.ymap.xml'))
write(make_ymap('des_bridge_end',    [('des_bridge_anim_debris', -1)], 1, 65),
      os.path.join(OUT_DIR, 'des_bridge_end.ymap.xml'))
# placer: composite + PERMANENT geometry
write(make_ymap('des_bridge_placer', [('des_bridge', 100), ('des_bridge_rest', 700)], 0, 65),
      os.path.join(OUT_DIR, 'des_bridge_placer.ymap.xml'))
print("POSITION:", POSITION)
