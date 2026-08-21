"""des_* klip sozlugunu VANILLA sozlesmesine getirir.

OLCUM TABANI: 5 vanilla des sozlugu / 27 klip
  des_farmhouse (10), des_stilthouse (8), des_vaultdoor (7),
  des_protree (1), des_tvsmash (1)
Asagidaki bes alanda ISTISNA YOK (27/27):

  1. Animation <Hash>   = klip adiyla AYNI
     fix_ycd_xml.py bunu 'anim_<klip>' diye turetiyor. Gerekcesi cakisma
     korkusu ama ClipMap ve AnimMap AYRI haritalar; vanilla 5/5 ayni adi
     kullaniyor. Onemli: compositeEntityTypes'taki <AnimName> bu anahtarla
     aranir -- uyusmazsa motor animasyonu BULAMAZ ve sessizce hicbir sey
     oynamaz (durum makinesi yine de fazi ilerletir).
  2. Clip <Name>        = 'pack:/<klip>.clip'   (27/27 '.clip' ile biter)
  3. Clip <Unknown30>   = 1                      (27/27)
  4. Animation <Unknown10> = 1                   (27/27)
  5. Clip <Properties>  = tek oge:
       NameHash hash_BF6A5D60  (27/27 sabit)
       UnkHash  hash_996C3B27 + Int 32   ya da   hash_B7BC80C9 + Int 0
       Dagilim: 32 baskin; des_stilthouse'un 8 klibinin 8'i de 32.

BILINCLI OLARAK DOKUNULMAYAN: <Unknown1C>. Vanilla'da animasyon basina
farkli (farmhouse 3+, stilthouse 3+ ayri deger) ve turetme kurali
cikarilamadi -- deger uydurmak yerine oldugu gibi birakiliyor.
"""
import sys, xml.etree.ElementTree as ET

NAME_HASH = "hash_BF6A5D60"
UNK_HASH  = "hash_996C3B27"
PROP_DEG  = "32"


def klip_adi(item):
    h = item.find("Hash")
    if h is not None and h.text:
        return h.text.strip()
    n = item.find("Name")
    if n is not None and n.text:
        return n.text.strip().replace("pack:/", "").replace(".clip", "")
    return None


def alan_kur(ebeveyn, etiket, deger, oncesi=None):
    e = ebeveyn.find(etiket)
    if e is None:
        e = ET.Element(etiket)
        if oncesi is not None:
            hedef = ebeveyn.find(oncesi)
            idx = list(ebeveyn).index(hedef) if hedef is not None else len(ebeveyn)
            ebeveyn.insert(idx, e)
        else:
            ebeveyn.append(e)
    if etiket in ("Unknown30", "Unknown10"):
        e.set("value", deger)
        e.text = None
    else:
        e.text = deger
    return e


def yama(yol):
    tree = ET.parse(yol)
    kok = tree.getroot()
    clips = kok.findall("./Clips/Item")
    anims = kok.findall("./Animations/Item")
    rapor = {"klip": len(clips), "anim": len(anims), "degisiklik": []}

    adlar = []
    for it in clips:
        ad = klip_adi(it)
        adlar.append(ad)

        # 2) Name -> pack:/<ad>.clip
        n = it.find("Name")
        istenen = f"pack:/{ad}.clip"
        if n is None or (n.text or "").strip() != istenen:
            alan_kur(it, "Name", istenen)
            rapor["degisiklik"].append(f"Name -> {istenen}")

        # 3) Unknown30 = 1
        u30 = it.find("Unknown30")
        if u30 is None or u30.get("value") != "1":
            alan_kur(it, "Unknown30", "1")
            rapor["degisiklik"].append("Unknown30 -> 1")

        # 1/6) AnimationHash = klip adi
        ah = it.find("AnimationHash")
        if ah is None or (ah.text or "").strip() != ad:
            alan_kur(it, "AnimationHash", ad)
            rapor["degisiklik"].append(f"AnimationHash -> {ad}")

        # 5) Properties
        props = it.find("Properties")
        if props is None:
            props = ET.SubElement(it, "Properties")
        if not props.findall("Item"):
            oge = ET.SubElement(props, "Item")
            ET.SubElement(oge, "NameHash").text = NAME_HASH
            ET.SubElement(oge, "UnkHash").text = UNK_HASH
            attrs = ET.SubElement(oge, "Attributes")
            a = ET.SubElement(attrs, "Item")
            ET.SubElement(a, "NameHash").text = NAME_HASH
            ET.SubElement(a, "Type").set("value", "Int")
            ET.SubElement(a, "Value").set("value", PROP_DEG)
            rapor["degisiklik"].append(f"Properties -> {NAME_HASH}/{UNK_HASH}/Int {PROP_DEG}")

    for i, it in enumerate(anims):
        # 1) Animation Hash = klip adi ('anim_' oneki DEGIL)
        ad = adlar[i] if i < len(adlar) else None
        if ad:
            h = it.find("Hash")
            if h is None or (h.text or "").strip() != ad:
                eski = h.text if h is not None else "(yok)"
                alan_kur(it, "Hash", ad, oncesi="Unknown10")
                rapor["degisiklik"].append(f"Animation Hash {eski} -> {ad}")
        # 4) Unknown10 = 1
        u10 = it.find("Unknown10")
        if u10 is None or u10.get("value") != "1":
            alan_kur(it, "Unknown10", "1")
            rapor["degisiklik"].append("Unknown10 -> 1")

    ET.indent(tree, space=" ")
    tree.write(yol, encoding="UTF-8", xml_declaration=True)
    return rapor


if __name__ == "__main__":
    r = yama(sys.argv[1])
    print(f"[+] {r['klip']} klip / {r['anim']} animasyon")
    for d in r["degisiklik"]:
        print(f"    {d}")
