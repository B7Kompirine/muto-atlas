#!/usr/bin/env python3
"""build_dumps.py — DurtyFree GTA V data dump'larindan plugin veri katmanlari uretir.

  python scripts/build_dumps.py --dump <gta-v-data-dumps klasoru>

Uretilen katmanlar (data/ altina):
  peds_meta.tsv.gz       ped kimligi + ANIMASYON/EXPRESSION baglantilari
  weapons.tsv.gz         silah kunyesi
  weapon_parts.tsv.gz    bilesen + livery (kind kolonu ile AYNI tabloda)
  vehicles.tsv.gz        arac kunyesi
  mlo_interiors.tsv.gz   MLO ic mekanlari, KONUM BASINA bir satir
  ipls.tsv.gz            IPL adlari + sinir kutulari
  world_objects.tsv.gz   dunya nesneleri: aile etiketi + konum + ROTASYON
  dumps.meta.json        kaynak, tarih, satir sayilari

TASARIM KURALLARI (olculerek konuldu, degistirmeden once oku):

1. AD KOLONU KAYNAKTAKI HALIYLE yazilir, JOIN daima .lower() uzerinden kurulur.
   Dump adlari MixedCase (W_AR_ASSAULTRIFLE), plugin katmanlari kucuk harf.
   Birebir join her ailede 0 dondurur ve bu SESSIZDIR - tablo dolu gorunur,
   eslesme bos cikar, cagiran taraf "bu model yok" der.

2. weapon_parts'ta component VE livery ayni tabloda, ayirt eden `kind` kolonu.
   155 livery adi da gecerli bir COMPONENT_* adidir (GiveWeaponComponentToPed
   onlari kabul eder). Ayri tablo yapmak, livery'leri "gecersiz bilesen" diye
   isaretleyen bir kapiya yol acar.

3. Her katmanda `dlc` kolonu ZORUNLU. Sunucu sv_enforceGameBuild ile bir yapiya
   sabitlenir; dump'ta VAR ama sunucunun yapisinda YOK olan ad, "gecerli" diye
   raporlanir ve oyunda RequestModel hic yuklenmez, F8'de hata da olmaz.

4. mlo_interiors KONUM BASINA satirdir (385 MLO, 844 konum). Ayni ic mekan
   birden fazla yere yerlestirilir; MLO basina tek satir yazmak konumlarin
   %54'unu atar.

5. Bos degerler bos string yazilir, "None"/"null" DIZESI yazilmaz. Kaynakta
   732 pedin ExpressionDictionaryName alani literal 'null' dizesidir - bu
   dizeyi gercek bir sozluk adi sanan sorgu sessizce yanlis cevap verir.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import gzip
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")

# Kaynakta gercek yoklugu temsil eden degerler. 'null'/'None' DIZE olarak gelir.
BOS = {None, "", "null", "NULL", "None", "none"}


def s(v):
    """Hucre degeri: yoklugu bos string yapar, sekme/satir sonunu temizler.

    Tip testleri SIRAYLA onemli: `v in BOS` hashlenemeyen tipte (list/dict)
    TypeError atar, o yuzden once koleksiyonlar ayiklanir. Tints ve Flags
    liste; TranslatedLabel dict.
    """
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (list, tuple)):
        parts = []
        for x in v:
            if isinstance(x, dict):
                x = x.get("Name") or x.get("English") or ""
            if x not in BOS:
                parts.append(str(x))
        return ",".join(parts)
    if isinstance(v, dict):
        return s(v.get("Name") or v.get("English") or "")
    if v in BOS:
        return ""
    return str(v).replace("\t", " ").replace("\n", " ").replace("\r", "")


def xyz(p, nd=4):
    """{'X':..,'Y':..,'Z':..} -> uc ayri hucre. Yoksa uc bos hucre."""
    if not isinstance(p, dict):
        return ["", "", ""]
    return [f"{float(p.get(k, 0) or 0):.{nd}f}" for k in ("X", "Y", "Z")]


def label(t):
    """TranslatedLabel dict'inden Ingilizce etiket."""
    return s(t.get("English")) if isinstance(t, dict) else ""


def load(dump, name):
    p = os.path.join(dump, name)
    if not os.path.exists(p):
        print(f"  [!] {name} yok, bu katman atlandi", file=sys.stderr)
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def write(fname, cols, rows):
    """Gzip TSV yazar (BASLIKLI). Yazdiktan sonra GERI OKUYUP dogrular."""
    path = os.path.join(DATA, fname)
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    # Geri okuma: "komut hata vermedi" yazma kaniti degildir.
    with gzip.open(tmp, "rt", encoding="utf-8") as fh:
        head = fh.readline().rstrip("\n").split("\t")
        n = sum(1 for _ in fh)
    if head != cols:
        os.remove(tmp)
        sys.exit(f"HATA: {fname} basligi geri okumada uyusmadi: {head}")
    if n != len(rows):
        os.remove(tmp)
        sys.exit(f"HATA: {fname} {len(rows)} satir yazildi, {n} okundu")
    os.replace(tmp, path)
    kb = os.path.getsize(path) / 1024
    print(f"  {fname:<24} {n:>7} satir  {kb:>8.1f} KB")
    return n


# --- katmanlar ---------------------------------------------------------------

PED_COLS = ["name", "hash", "dlc", "pedtype", "propsName", "clipDict", "blendShape",
            "exprSet", "exprDict", "exprName", "movementClipSet", "strafeClipSet",
            "gestureClipSet", "facialClipsetGroup", "visemeClipSet", "getupSet",
            "creatureMetadata", "capsule", "voiceGroup", "isStreamedGfx",
            "isHeadBlend", "boneCount"]


def build_peds(dump):
    d = load(dump, "peds.json")
    if d is None:
        return 0
    rows = []
    for p in d:
        rows.append([
            s(p.get("Name")), s(p.get("Hash")), s(p.get("DlcName")), s(p.get("Pedtype")),
            s(p.get("PropsName")), s(p.get("ClipDictionaryName")), s(p.get("BlendShapeFileName")),
            s(p.get("ExpressionSetName")), s(p.get("ExpressionDictionaryName")),
            s(p.get("ExpressionName")), s(p.get("MovementClipSet")), s(p.get("StrafeClipSet")),
            s(p.get("DefaultGestureClipSet")), s(p.get("FacialClipsetGroupName")),
            s(p.get("DefaultVisemeClipSet")), s(p.get("GetupSetHash")),
            s(p.get("CreatureMetadataName")), s(p.get("PedCapsuleName")),
            s(p.get("PedVoiceGroup")), s(p.get("IsStreamedGfx")), s(p.get("IsHeadBlendPed")),
            s(len(p.get("Bones") or [])),
        ])
    return write("peds_meta.tsv.gz", PED_COLS, rows)


WPN_COLS = ["name", "label", "hash", "dlc", "category", "model", "ammoType", "ammoModel",
            "damageType", "isVehicleWeapon", "tints", "maxAmmoSp", "maxAmmoMp",
            "componentCount", "liveryCount", "flags"]
PART_COLS = ["weapon", "kind", "name", "label", "hash", "dlc", "attachBone", "type", "isDefault"]


def build_weapons(dump):
    d = load(dump, "weapons.json")
    if d is None:
        return 0, 0
    wrows, prows = [], []
    for w in d:
        comps = w.get("Components") or []
        livs = w.get("Liveries") or []
        wrows.append([
            s(w.get("Name")), label(w.get("TranslatedLabel")), s(w.get("Hash")),
            s(w.get("DlcName")), s(w.get("Category")), s(w.get("ModelName")),
            s(w.get("AmmoType")), s(w.get("AmmoModelName")), s(w.get("DamageType")),
            s(w.get("IsVehicleWeapon")), s(w.get("Tints")),
            s(w.get("DefaultMaxAmmoSp")), s(w.get("DefaultMaxAmmoMp")),
            s(len(comps)), s(len(livs)), s(w.get("Flags")),
        ])
        for c in comps:
            prows.append([
                s(w.get("Name")), "component", s(c.get("Name")), label(c.get("TranslatedLabel")),
                s(c.get("Hash")), s(c.get("DlcName")), s(c.get("AttachBone")),
                s(c.get("Type")), s(c.get("IsDefault")),
            ])
        for l in livs:
            prows.append([
                s(w.get("Name")), "livery", s(l.get("Name")), label(l.get("TranslatedLabel")),
                s(l.get("Hash")), s(l.get("DlcName")), "", "", "",
            ])
    return (write("weapons.tsv.gz", WPN_COLS, wrows),
            write("weapon_parts.tsv.gz", PART_COLS, prows))


VEH_COLS = ["name", "displayName", "hash", "dlc", "handlingId", "layoutId", "manufacturer",
            "class", "type", "seats", "price", "wheelsCount", "hasSirens", "hasConvertible",
            "modKits", "extras", "maxSpeed", "acceleration", "flags"]


def build_vehicles(dump):
    d = load(dump, "vehicles.json")
    if d is None:
        return 0
    rows = []
    for v in d:
        rows.append([
            s(v.get("Name")), s(v.get("DisplayName")), s(v.get("Hash")), s(v.get("DlcName")),
            s(v.get("HandlingId")), s(v.get("LayoutId")), s(v.get("Manufacturer")),
            s(v.get("Class")), s(v.get("Type")), s(v.get("Seats")), s(v.get("Price")),
            s(v.get("WheelsCount")), s(v.get("HasSirens")), s(v.get("HasConvertibleRoof")),
            s(v.get("ModKits")), s(v.get("Extras")),
            s(v.get("MaxSpeed")), s(v.get("Acceleration")), s(v.get("Flags")),
        ])
    return write("vehicles.tsv.gz", VEH_COLS, rows)


MLO_COLS = ["name", "dlc", "locDlc", "x", "y", "z", "flags", "entityCount", "ytypPath", "ymapPath"]


def build_mlo(dump):
    d = load(dump, "mloInteriors.json")
    if d is None:
        return 0
    rows = []
    for m in d:
        locs = m.get("Locations") or []
        if not locs:
            # Konumu bilinmeyen MLO da yazilir; "yok" ile "yerlestirilmemis" farkli.
            rows.append([s(m.get("Name")), s(m.get("DlcName")), "", "", "", "", "",
                         s(m.get("TotalEntitiesCount")), s(m.get("FilePath")), ""])
            continue
        for lo in locs:
            x, y, z = xyz(lo.get("Position"))
            rows.append([
                s(m.get("Name")), s(m.get("DlcName")), s(lo.get("DlcName")), x, y, z,
                s(lo.get("Flags")), s(m.get("TotalEntitiesCount")),
                s(m.get("FilePath")), s(lo.get("FilePath")),
            ])
    return write("mlo_interiors.tsv.gz", MLO_COLS, rows)


IPL_COLS = ["name", "dlc", "x", "y", "z", "minX", "minY", "minZ", "maxX", "maxY", "maxZ",
            "contentFlags", "group", "category"]


def build_ipls(dump):
    d = load(dump, "ipls.json")
    if d is None:
        return 0
    rows = []
    for i in d:
        ex = i.get("ExtraData") or {}
        rows.append([s(i.get("Name")), s(i.get("DlcName"))]
                    + xyz(i.get("Position")) + xyz(i.get("DimensionMin")) + xyz(i.get("DimensionMax"))
                    + [s(i.get("ContentFlags")), s(ex.get("GroupName")), s(ex.get("Category"))])
    return write("ipls.tsv.gz", IPL_COLS, rows)


WORLD_COLS = ["family", "model", "x", "y", "z", "rx", "ry", "rz"]


def build_world(dump):
    """objectslocations/*.json -> tek tablo. Aile etiketi dosya adindan gelir.

    NEDEN DEGERLI: entities.tsv.gz 3M satirla "nerede ne var" der ama SEMANTIK
    etiket tasimaz - "bu bir ATM'dir" diyemez, ROTASYON da tutmaz. Loot/spawn
    noktasi, anti-cheat beyaz listesi, prop degistirme icin gereken ikisi de bu.
    """
    dirp = os.path.join(dump, "objectslocations")
    if not os.path.isdir(dirp):
        print("  [!] objectslocations/ yok, atlandi", file=sys.stderr)
        return 0
    rows, bos = [], []
    for f in sorted(glob.glob(os.path.join(dirp, "*.json"))):
        fam = os.path.basename(f)[:-5]
        if fam.startswith("world"):
            fam = fam[5:]
        fam = fam[0].lower() + fam[1:] if fam else fam
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        if not d:
            bos.append(fam)
            continue
        for o in d:
            rows.append([fam, s(o.get("Name"))] + xyz(o.get("Position")) + xyz(o.get("Rotation")))
    if bos:
        print(f"  (bos dosya, satir uretmedi: {', '.join(bos)})")
    return write("world_objects.tsv.gz", WORLD_COLS, rows)


RAW = "https://raw.githubusercontent.com/DurtyFree/gta-v-data-dumps/master/"

# --fetch ile indirilecek dosyalar. objectslocations/ ayri ele alinir.
GEREKLI = ["README.md", "peds.json", "weapons.json", "vehicles.json",
           "mloInteriors.json", "ipls.json",
           "animDictsCompact.json", "ObjectList.ini", "scenariosCompact.json"]
DUNYA = ["worldAirMasts", "worldAntennas", "worldAtms", "worldBinsDumpsters",
         "worldBusStopSigns", "worldBusStops", "worldCctvs", "worldContainerCabins",
         "worldDartDiscs", "worldElectricityBoxes", "worldExtraPhones",
         "worldFireHydrantDriser", "worldFoodStands", "worldFruitStands",
         "worldGasPumps", "worldHarvestFields", "worldJukeboxes", "worldLetterBoxes",
         "worldMobileMasts", "worldNewsPaperDispensers", "worldOilJacks",
         "worldParknmeters", "worldPostBoxes", "worldPublicPhones", "worldRadioTowers",
         "worldRecycleBins", "worldSatDishes", "worldSeats", "worldStreetLights",
         "worldTelescopes", "worldTrafficLights", "worldVendingMachines",
         "worldWreckedBikes", "worldWreckedCars"]


def indir(hedef, force=False):
    """Dump dosyalarini upstream'den ceker. Klasor yoksa olusturur.

    ⛔ VAR OLANI ATLAR. Sebebi olculdu: "klasor bos degilse indirme" mantigi,
    kaynak listesine sonradan dosya EKLENDIGINDE sessizce basarisiz olur —
    klasor dolu gorunur, yeni dosyalar hic inmez, o katmanlar "atlandi" der
    ve kullanici sebebini bilmez. Dosya bazinda kontrol bunu kokten keser.
    """
    import urllib.request
    os.makedirs(os.path.join(hedef, "objectslocations"), exist_ok=True)
    isler = [(RAW + f, os.path.join(hedef, f)) for f in GEREKLI]
    isler += [(RAW + "objectslocations/" + f + ".json",
               os.path.join(hedef, "objectslocations", f + ".json")) for f in DUNYA]
    hata = atlandi = 0
    for i, (url, dest) in enumerate(isler, 1):
        if not force and os.path.exists(dest) and os.path.getsize(dest) > 0:
            atlandi += 1
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fivem-natives-plugin"})
            with urllib.request.urlopen(req, timeout=120) as r:
                veri = r.read()
            with open(dest, "wb") as fh:
                fh.write(veri)
            print(f"  [{i:>2}/{len(isler)}] {os.path.basename(dest):<34} {len(veri)/1024:>8.0f} KB")
        except Exception as e:
            hata += 1
            print(f"  [{i:>2}/{len(isler)}] {os.path.basename(dest):<34} HATA: {e}", file=sys.stderr)
    if atlandi:
        print(f"  ({atlandi} dosya zaten vardi, atlandi)")
    if hata:
        print(f"\n  {hata} dosya inemedi. Eksik dosyanin katmani atlanir.", file=sys.stderr)
    return hata


def yaz_basliksiz(fname, satirlar):
    """BASLIKSIZ gzip TSV. anims/props/scenarios tarihsel olarak basliksizdir;
    baslik eklemek assetdb.py'in gz_lines(header=False) okumasini bozar ve
    ilk kayit sessizce 'baslik' sanilip dusurulur."""
    path = os.path.join(DATA, fname)
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8", newline="\n") as fh:
        for s_ in satirlar:
            fh.write(s_ + "\n")
    with gzip.open(tmp, "rt", encoding="utf-8") as fh:
        n = sum(1 for _ in fh)
    if n != len(satirlar):
        os.remove(tmp)
        sys.exit(f"HATA: {fname} {len(satirlar)} yazildi, {n} okundu")
    os.replace(tmp, path)
    print(f"  {fname:<24} {n:>7} satir  {os.path.getsize(path)/1024:>8.1f} KB")
    return n


def build_anim(dump):
    """animDictsCompact.json -> anims.tsv.gz  (dict<TAB>clip, basliksiz)

    NOT: 408 sozluk SIFIR animasyonlu (hepsi '-N' sonekli ara sahne dilimi) ve
    satir uretmez. README 20179 dict der, dosyaya 19771 girer - fark budur,
    kayip degil.
    """
    d = load(dump, "animDictsCompact.json")
    if d is None:
        return 0
    satir = []
    for e in d:
        dn = e.get("DictionaryName") or ""
        for c in (e.get("Animations") or []):
            satir.append(f"{dn}\t{c}")
    return yaz_basliksiz("anims.tsv.gz", satir)


def build_props(dump):
    """ObjectList.ini -> props.tsv.gz (satir basina bir ad)"""
    p = os.path.join(dump, "ObjectList.ini")
    if not os.path.exists(p):
        print("  [!] ObjectList.ini yok, props atlandi", file=sys.stderr)
        return 0
    adlar = [l.strip() for l in open(p, encoding="utf-8", errors="replace") if l.strip()]
    return yaz_basliksiz("props.tsv.gz", adlar)


def build_scenarios(dump):
    d = load(dump, "scenariosCompact.json")
    if d is None:
        return 0
    return yaz_basliksiz("scenarios.tsv.gz", [str(x) for x in d if x])


def main():
    ap = argparse.ArgumentParser(description="GTA V data dump -> plugin veri katmanlari")
    ap.add_argument("--dump", required=True, help="gta-v-data-dumps klasoru")
    ap.add_argument("--fetch", action="store_true",
                    help="eksik kaynak dosyalari indir (var olani atlar)")
    ap.add_argument("--force-fetch", action="store_true",
                    help="var olan dosyalari da yeniden indir")
    ap.add_argument("--only", nargs="*", help="yalniz bu katmanlar (peds weapons vehicles mlo ipls world anim props scenarios)")
    a = ap.parse_args()

    if a.fetch or a.force_fetch:
        print(f"Indiriliyor -> {a.dump}\n")
        os.makedirs(a.dump, exist_ok=True)
        indir(a.dump, force=a.force_fetch)
        print()
    if not os.path.isdir(a.dump):
        sys.exit(f"HATA: dump klasoru yok: {a.dump}\n"
                 f"  Indirmek icin: --fetch ekle")
    os.makedirs(DATA, exist_ok=True)

    # Dump surumu README'nin ilk 'update:' satirindan okunur (elle yazilmaz).
    surum = ""
    rp = os.path.join(a.dump, "README.md")
    if os.path.exists(rp):
        for line in open(rp, encoding="utf-8"):
            if "up2date as of GTA V update" in line:
                surum = line.strip().replace("*", "").split("update:")[-1].strip()
                break

    print(f"Dump : {a.dump}")
    print(f"Surum: {surum or '(README okunamadi)'}")
    print(f"Hedef: {DATA}\n")

    sec = set(a.only) if a.only else None
    say = {}

    def istendi(k):
        return sec is None or k in sec

    if istendi("peds"):
        say["peds_meta"] = build_peds(a.dump)
    if istendi("weapons"):
        say["weapons"], say["weapon_parts"] = build_weapons(a.dump)
    if istendi("vehicles"):
        say["vehicles"] = build_vehicles(a.dump)
    if istendi("mlo"):
        say["mlo_interiors"] = build_mlo(a.dump)
    if istendi("ipls"):
        say["ipls"] = build_ipls(a.dump)
    if istendi("world"):
        say["world_objects"] = build_world(a.dump)
    if istendi("anim"):
        say["anims"] = build_anim(a.dump)
    if istendi("props"):
        say["props"] = build_props(a.dump)
    if istendi("scenarios"):
        say["scenarios"] = build_scenarios(a.dump)

    meta_p = os.path.join(DATA, "dumps.meta.json")
    eski = {}
    if os.path.exists(meta_p):
        try:
            eski = json.load(open(meta_p, encoding="utf-8")).get("rows", {})
        except Exception:
            eski = {}
    eski.update(say)
    with open(meta_p, "w", encoding="utf-8") as fh:
        json.dump({
            "generatedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source": "https://github.com/DurtyFree/gta-v-data-dumps",
            "dumpPath": a.dump,
            "gameVersion": surum,
            "rows": eski,
        }, fh, indent=2, ensure_ascii=False)

    print(f"\n{sum(say.values())} satir uretildi, {len(say)} katman.")
    print(f"meta: {meta_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
