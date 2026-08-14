#!/usr/bin/env python3
"""doctor_kontroller.py — format basina denetimler (.ycd, .ytyp / MLO).

Her denetim GERCEK dosya uzerinde olculmus bir kurala dayanir; olcumun ne
oldugu ilgili kuralin yaninda yazilidir. Olcumsuz kural EKLENMEZ -- yanlis
pozitif ureten bir kapi, kapisiz olmaktan kotudur.
"""
from __future__ import annotations

from doctor_ortak import (FATAL, SILENT, WARN, KARE, Rapor, _hash_bos,  # noqa: F401
                          _oznitelik, _tr)

# =============================================================================
# .ycd  — klip sozlugu
# =============================================================================
# Yapi (vanilla mp_safehousewine@.ycd / move_m@brave.ycd uzerinde dogrulandi):
#   ClipDictionary
#     Clips/Item      : Hash, Name, Type(value=Animation|AnimationList),
#                       AnimationHash          (Type=Animation)
#                       Animations/Item/AnimationHash  (Type=AnimationList)
#     Animations/Item : Hash, Unknown10, FrameCount, BoneIds, Sequences

def _klip_anim_hashleri(klip):
    """Bir klibin refere ettigi TUM animasyon hash'leri (iki tip de)."""
    tek = klip.findtext("AnimationHash")
    if tek and tek.strip():
        yield tek.strip()
    liste = klip.find("Animations")
    if liste is not None:
        for it in liste:
            h = it.findtext("AnimationHash")
            if h and h.strip():
                yield h.strip()


def denetle_ycd(kok, yol, rap, derlenmis=False):
    klipler = kok.findall("./Clips/Item")
    animler = kok.findall("./Animations/Item")

    if not klipler:
        rap.ekle(SILENT, "YCD000", yol, _tr({
            "tr": "Sozlukte hic klip yok.",
            "en": "Dictionary contains no clips."}))
        return

    anim_hashleri = set()
    anim_sure = {}
    gorulen_anim = {}
    for i, a in enumerate(animler):
        h = (a.findtext("Hash") or "").strip()
        if _hash_bos(h):
            rap.ekle(SILENT, "YCD002", yol, _tr({
                "tr": f"Animasyon #{i} <Hash> bos -> hash 0. Ayni anahtara "
                      f"dusen animasyonlar birbirini EZER.",
                "en": f"Animation #{i} has empty <Hash> -> hash 0. Animations "
                      f"colliding on one key OVERWRITE each other."}), "fix_ycd_xml.py")
            continue
        if h in gorulen_anim:
            rap.ekle(SILENT, "YCD004", yol, _tr({
                "tr": f"Animasyon hash tekrari: {h} (#{gorulen_anim[h]} ve #{i}). "
                      f"Sonuncusu oncekini ezer.",
                "en": f"Duplicate animation hash: {h} (#{gorulen_anim[h]} and #{i}). "
                      f"The last one overwrites the earlier."}))
        gorulen_anim[h] = i
        anim_hashleri.add(h)
        anim_sure[h] = _oznitelik(a.find("Duration"))

        # 0 kanal tuzagi: Sollumz'a Object verilirse dosya olusur, kare/sure
        # dogrudur, KEMIK VERISI YOKTUR (724 bayt vs 59 KB).
        kemik = a.find("BoneIds")
        diziler = a.find("Sequences")
        if kemik is not None and len(kemik) == 0:
            rap.ekle(SILENT, "YCD006", yol, _tr({
                "tr": f"Animasyon {h}: BoneIds BOS -> 0 kemik kanali. Dosya "
                      f"olusur, sure dogrudur, poz hic degismez.",
                "en": f"Animation {h}: BoneIds is EMPTY -> 0 bone channels. The "
                      f"file builds, duration looks right, the pose never moves."}),
                _tr({"tr": "Sollumz Animation.target_id ARMATURE DATA olmali (arm.data), Object degil.",
                     "en": "Sollumz Animation.target_id must be the ARMATURE DATA-BLOCK (arm.data), not the Object."}))
        elif diziler is not None and len(diziler) == 0:
            rap.ekle(SILENT, "YCD006", yol, _tr({
                "tr": f"Animasyon {h}: Sequences BOS -> veri yok.",
                "en": f"Animation {h}: Sequences is EMPTY -> no data."}))

        fc = a.find("FrameCount")
        if fc is not None and (fc.get("value") or "0").strip() in ("0", "0.0"):
            rap.ekle(SILENT, "YCD007", yol, _tr({
                "tr": f"Animasyon {h}: FrameCount 0.",
                "en": f"Animation {h}: FrameCount is 0."}))

    gorulen_klip = {}
    kullanilan = set()
    cozulmeyen = []   # (klip, cozulmeyen_anim_hash)
    tasma = []        # (klip, saniye cinsinden asim)
    refsiz = 0        # AnimationHash tasimayan klip sayisi
    for i, c in enumerate(klipler):
        h = (c.findtext("Hash") or "").strip()
        ad = (c.findtext("Name") or "").strip()
        etiket = h or ad or f"#{i}"

        if _hash_bos(h):
            rap.ekle(SILENT, "YCD001", yol, _tr({
                "tr": f"Klip '{ad or i}' <Hash> bos -> klibin ADI YOK. "
                      f"TaskPlayAnim/PlayEntityAnim onu BULAMAZ. Cok klipli "
                      f"sozlukte klipler ayrica birbirini ezer.",
                "en": f"Clip '{ad or i}' has empty <Hash> -> the clip HAS NO NAME. "
                      f"TaskPlayAnim/PlayEntityAnim CANNOT find it. In a multi-clip "
                      f"dictionary the clips also overwrite each other."}), "fix_ycd_xml.py")
        else:
            if h in gorulen_klip:
                rap.ekle(SILENT, "YCD003", yol, _tr({
                    "tr": f"Klip hash tekrari: {h} (#{gorulen_klip[h]} ve #{i}).",
                    "en": f"Duplicate clip hash: {h} (#{gorulen_klip[h]} and #{i})."}))
            gorulen_klip[h] = i

        refler = list(_klip_anim_hashleri(c))
        if not refler:
            refsiz += 1
            continue
        for r in refler:
            kullanilan.add(r)
            if anim_hashleri and r not in anim_hashleri:
                cozulmeyen.append((etiket, r))
                continue
            son = _oznitelik(c.find("EndTime"))
            if son is None:
                son = _oznitelik(c.find("Duration"))
            sure = anim_sure.get(r)
            if son is not None and sure:
                fazla = son - sure
                if fazla > 1e-4:
                    tasma.append((etiket, fazla))

    # --- cozulmeyen referans: klip oynar, hicbir sey hareket etmez ---
    for etiket, r in cozulmeyen[:8]:
        rap.ekle(SILENT, "YCD005", yol, _tr({
            "tr": f"Klip '{etiket}' -> {r} animasyonu sozlukte YOK. "
                  f"Klip oynar, hicbir sey hareket etmez.",
            "en": f"Clip '{etiket}' -> animation {r} is NOT in the dictionary. "
                  f"The clip plays, nothing moves."}))
    if len(cozulmeyen) > 8:
        rap.ekle(SILENT, "YCD005", yol, _tr({
            "tr": f"...ve {len(cozulmeyen) - 8} klip daha cozulmeyen referans tasiyor.",
            "en": f"...and {len(cozulmeyen) - 8} more clips carry unresolved references."}))

    # --- konumsal eslesme (Sollumz formu) ---
    # Sollumz Type=Animation klibine AnimationHash YAZMAZ; derleyici klip[i] ile
    # animasyon[i]'yi konumsal eslestirir. Kendi basina hata degildir -- ama
    # Sollumz kliplerle animasyonlari OBJE ADINA GORE ALFABETIK dizer, olusturma
    # sirasina gore degil. Sayilar tutmuyorsa eslesme kesinlikle yanlistir.
    if refsiz:
        if derlenmis:
            # DERLENMIS dosyada bag artik cozulmus olmali. Bos AnimationHash
            # burada hash 0 demektir: klip calisir, hicbir animasyon bulunmaz.
            # (Olculdu: ayni sozlugun 2 Agustos derlemesinde 63/63 hash dolu,
            #  3 Agustos derlemesinde 63/63 BOS -- ayni donusturucu, ayni okuyucu.)
            rap.ekle(SILENT, "YCD009", yol, _tr({
                "tr": f"DERLENMIS dosyada {refsiz}/{len(klipler)} klibin AnimationHash'i "
                      f"BOS -> hash 0. Klip cagrilir, hicbir animasyon bulunmaz. "
                      f"Kaynak XML'de konumsal eslesme normaldir; derlenmis dosyada "
                      f"bagin COZULMUS olmasi gerekir.",
                "en": f"In this COMPILED file {refsiz}/{len(klipler)} clips have an EMPTY "
                      f"AnimationHash -> hash 0. The clip is invoked, no animation is "
                      f"found. Positional matching is normal in the source XML; in a "
                      f"compiled file the link must already be RESOLVED."}),
                "res_to_xml.ps1 + fix_ycd_xml.py")
        elif refsiz == len(klipler) and len(klipler) == len(animler):
            rap.ekle(WARN, "YCD009", yol, _tr({
                "tr": f"Hicbir klip AnimationHash tasimiyor ({refsiz} klip) -> eslesme "
                      f"KONUMSAL. Sayilar tutuyor ({len(klipler)}={len(animler)}), ama "
                      f"Sollumz alfabetik dizer: hangi klibin hangi animasyona "
                      f"dustugunu FrameCount ile dogrula.",
                "en": f"No clip carries an AnimationHash ({refsiz} clips) -> matching is "
                      f"POSITIONAL. Counts agree ({len(klipler)}={len(animler)}), but "
                      f"Sollumz sorts alphabetically: verify which clip landed on which "
                      f"animation via FrameCount."}))
        else:
            rap.ekle(SILENT, "YCD009", yol, _tr({
                "tr": f"{refsiz} klip AnimationHash tasimiyor ve sayilar tutmuyor "
                      f"(klip={len(klipler)}, animasyon={len(animler)}) -> konumsal "
                      f"eslesme YANLIS baglanir.",
                "en": f"{refsiz} clips carry no AnimationHash and the counts disagree "
                      f"(clips={len(klipler)}, animations={len(animler)}) -> positional "
                      f"matching WILL bind the wrong pairs."}))

    # --- klip penceresi animasyonu asiyor ---
    if tasma:
        enfazla = max(f for _, f in tasma)
        kare = enfazla / KARE
        seviye = WARN if kare <= 1.5 else SILENT
        rap.ekle(seviye, "YCD010", yol, _tr({
            "tr": f"{len(tasma)} klibin EndTime'i bagli animasyonun Duration'ini asiyor "
                  f"(en fazla {enfazla:.4f} s = {kare:.2f} kare). Vanilla'da bu fark hic "
                  f"pozitif olmaz; klip animasyonda OLMAYAN bir kareyi istiyor."
                  + ("" if seviye == WARN else " 1 kareyi astigi icin eslesme de supheli."),
            "en": f"{len(tasma)} clip(s) have an EndTime beyond the linked animation's "
                  f"Duration (worst {enfazla:.4f} s = {kare:.2f} frames). In vanilla this "
                  f"difference is never positive; the clip asks for a frame the animation "
                  f"DOES NOT have."
                  + ("" if seviye == WARN else " Beyond one frame, the pairing is suspect too.")}),
            f"Duration == (FrameCount-1)/30")

    # Konumsal formda hicbir klip referans tasimaz -> sahipsizlik anlamsiz.
    if not refsiz:
        sahipsiz = sorted(anim_hashleri - kullanilan)
        for h in sahipsiz[:5]:
            rap.ekle(WARN, "YCD008", yol, _tr({
                "tr": f"Animasyon {h} sahipsiz: hicbir klip kullanmiyor.",
                "en": f"Animation {h} is orphaned: no clip references it."}))
        if len(sahipsiz) > 5:
            rap.ekle(WARN, "YCD008", yol, _tr({
                "tr": f"...ve {len(sahipsiz) - 5} sahipsiz animasyon daha.",
                "en": f"...and {len(sahipsiz) - 5} more orphaned animations."}))


# =============================================================================
# .ytyp — archetype tanimlari
# =============================================================================
# Yapi (muto_spear_props.ytyp.xml uzerinde dogrulandi):
#   CMapTypes/archetypes/Item[@type=CBaseArchetypeDef|CTimeArchetypeDef|
#                             CMloArchetypeDef]
#     lodDist, flags, bbMin, bbMax, name, assetName, extensions
#     (MLO) entities/Item[@type=CEntityDef]/flags, rooms/Item/attachedObjects

# MLO entity bayragi. ymap degeri (1572872) MLO icinde kullanilirsa obje
# SESSIZCE hic olusmaz: bit 8 = "LOD in Parented YMAP", ust harita yok.
YMAP_BAYRAK = 1572872
BIT_LOD_UST_HARITA = 8

# OLCULDU: 79 vanilla interior ytyp'i -> 118 MLO, 18.799 entity.
#   * 1572872                : 0 kez
#   * 8. biti set eden HERHANGI bir bayrak : 0 kez  (tek bir entity bile yok)
#   * ayni degerin bitsiz hali 1572864     : 2272 kez (cok yaygin)
#   * en yaygin degerler: 18350082 (7578), 18350080 (3860), 1572864 (2272)
# Bu yuzden denetim tek bir sayiya degil BITE bakar: vanilla MLO icinde 8. bit
# hic kullanilmaz, dolayisiyla biti set eden her deger olagandisidir.
# Tek bir "dogru sayi" YOKTUR -> yaygin deger referans olarak verilir, recete
# olarak degil.
MLO_BAYRAK_YAYGIN = 18350082


def denetle_ytyp(kok, yol, rap, derlenmis=False):
    arketipler = kok.findall("./archetypes/Item")
    if not arketipler:
        rap.ekle(SILENT, "YTY000", yol, _tr({
            "tr": "ytyp'de hic archetype yok.",
            "en": "The ytyp contains no archetypes."}))
        return

    ad_farki, adsiz, lodsuz, dejenere = [], [], [], []
    for a in arketipler:
        tip = a.get("type") or "?"
        ad = (a.findtext("name") or "").strip()
        etiket = ad or "<adsiz>"

        if not ad:
            adsiz.append(tip)

        lod = a.find("lodDist")
        if lod is None or (_oznitelik(lod) or 0) <= 0:
            lodsuz.append(etiket)

        # MLO archetype'in bbox'i vanilla'da 0,0,0'dir (olculdu: v_int_10'un
        # her iki MLO'su da). Ic mekanin siniri odalardan gelir, archetype
        # kutusundan degil -> dejenere kutu denetimi MLO'ya UYGULANMAZ.
        bmin, bmax = a.find("bbMin"), a.find("bbMax")
        if tip != "CMloArchetypeDef" and bmin is not None and bmax is not None:
            try:
                mn = [float(bmin.get(k) or 0) for k in "xyz"]
                mx = [float(bmax.get(k) or 0) for k in "xyz"]
                if mn == mx:
                    dejenere.append(etiket)
            except ValueError:
                pass

        varlik = (a.findtext("assetName") or "").strip()
        if ad and varlik and ad != varlik and tip == "CBaseArchetypeDef":
            ad_farki.append(etiket)

        _denetle_extensions(a, etiket, yol, rap)

        if tip == "CMloArchetypeDef":
            _denetle_mlo(a, etiket, yol, rap)

    n = len(arketipler)
    if adsiz:
        rap.ekle(SILENT, "YTY006", yol, _tr({
            "tr": f"{len(adsiz)}/{n} archetype'in <name> alani bos -> adreslenemez.",
            "en": f"{len(adsiz)}/{n} archetype(s) have an empty <name> -> unaddressable."}))
    if lodsuz:
        rap.ekle(SILENT, "YTY004", yol, _tr({
            "tr": f"{len(lodsuz)}/{n} archetype'ta lodDist 0/eksik -> obje hicbir "
                  f"mesafede cizilmez. {', '.join(lodsuz[:4])}"
                  + (f" ve {len(lodsuz) - 4} tane daha." if len(lodsuz) > 4 else ""),
            "en": f"{len(lodsuz)}/{n} archetype(s) have lodDist 0/missing -> the object "
                  f"never draws. {', '.join(lodsuz[:4])}"
                  + (f" and {len(lodsuz) - 4} more." if len(lodsuz) > 4 else "")}),
            "assetdb.py lod")
    if dejenere:
        rap.ekle(SILENT, "YTY003", yol, _tr({
            "tr": f"{len(dejenere)}/{n} archetype'ta bbMin == bbMax (dejenere sinir "
                  f"kutusu) -> obje uzakta titrer ve kaybolur. "
                  f"{', '.join(dejenere[:4])}"
                  + (f" ve {len(dejenere) - 4} tane daha." if len(dejenere) > 4 else ""),
            "en": f"{len(dejenere)}/{n} archetype(s) have bbMin == bbMax (degenerate "
                  f"bounding box) -> the object flickers at distance and vanishes. "
                  f"{', '.join(dejenere[:4])}"
                  + (f" and {len(dejenere) - 4} more." if len(dejenere) > 4 else "")}))

    # name != assetName: YASAK DEGIL (bir archetype baska bir drawable'i
    # gosterebilir) ama OLAGANDISI -- olculdu: vanilla v_int_10 + v_int_47,
    # 89 CBaseArchetypeDef'in 89'unda ikisi AYNI (%0 sapma). Bu yuzden WARN,
    # ve dosya basina TEK satir: arketip basina yazmak 300+ satir uretiyordu.
    if ad_farki:
        rap.ekle(WARN, "YTY005", yol, _tr({
            "tr": f"{len(ad_farki)} archetype'ta assetName, name'den farkli "
                  f"(vanilla olcumu: 89/89 ayni). Kasitliysa sorun yok; degilse "
                  f"archetype var olmayan bir drawable'i gosteriyor olabilir.",
            "en": f"{len(ad_farki)} archetype(s) have assetName differing from name "
                  f"(vanilla measurement: 89/89 identical). Fine if deliberate; "
                  f"otherwise the archetype may point at a drawable that does not exist."}))


def _denetle_extensions(arketip, etiket, yol, rap):
    ext = arketip.find("extensions")
    if ext is None:
        return
    for it in ext:
        etip = it.get("type") or ""
        if "Expression" in etip:
            deger = (it.findtext("expressionDictionaryName") or "") + " " + \
                    (it.findtext("expressionName") or "")
            if "pack:/" in deger or ".expr" in deger:
                rap.ekle(SILENT, "YTY002", yol, _tr({
                    "tr": f"{etiket}: Expression extension 'pack:/...' formunda. "
                          f"CIPLAK AD yazilmali, yoksa expression baglanmaz ve "
                          f"collision animasyonu takip etmez.",
                    "en": f"{etiket}: Expression extension uses the 'pack:/...' form. "
                          f"It must be the BARE NAME, otherwise the expression never "
                          f"binds and collision will not follow the animation."}), "/yed")


def _denetle_mlo(arketip, etiket, yol, rap):
    varliklar = arketip.findall("./entities/Item")
    odalar = arketip.findall("./rooms/Item")

    # Entity'yi sahiplenen iki liste vardir: ODALAR *ve* PORTALLAR.
    # Portallari saymamak yanlis pozitif uretir -- olculdu: vanilla v_int_10'un
    # iki MLO'sunda da tam 2 entity portala baglidir, odaya degil. Sadece
    # odalara bakinca "hicbir odada yok" diye rapor edilirler ve dogru dosya
    # bozuk gorunur.
    sahipli = set()
    for kap in list(odalar) + arketip.findall("./portals/Item"):
        ham = (kap.findtext("attachedObjects") or "").replace(",", " ").split()
        for s in ham:
            try:
                sahipli.add(int(s))
            except ValueError:
                pass

    sahipsiz = []
    ymap_bayrakli = []
    for i, e in enumerate(varliklar):
        bayrak = e.find("flags")
        if bayrak is not None:
            try:
                v = int(float(bayrak.get("value") or 0))
            except ValueError:
                v = 0
            if v & BIT_LOD_UST_HARITA:
                ymap_bayrakli.append((i, v))

        if sahipli and i not in sahipli:
            sahipsiz.append((i, (e.findtext("archetypeName") or "?").strip()))

    if ymap_bayrakli:
        degerler = sorted({v for _, v in ymap_bayrakli})
        ilk = ", ".join(f"#{i}" for i, _ in ymap_bayrakli[:6])
        kalan = len(ymap_bayrakli) - 6
        rap.ekle(SILENT, "YTY001", yol, _tr({
            "tr": f"{etiket}: {len(ymap_bayrakli)}/{len(varliklar)} entity 8. biti "
                  f"('LOD ust haritada') set eden bir bayrak tasiyor: "
                  f"{', '.join(str(d) for d in degerler)}. OLCULDU: 118 vanilla MLO / "
                  f"18.799 entity icinde bu bit HIC kullanilmaz (0 kez); bitsiz hali "
                  f"1572864 ise 2272 kez gecer. Ust harita olmadigi icin entity "
                  f"SESSIZCE dusurulur. Yaygin MLO degeri {MLO_BAYRAK_YAYGIN} -- "
                  f"sayiyi kopyalama, coz. {ilk}"
                  + (f" ve {kalan} tane daha." if kalan > 0 else ""),
            "en": f"{etiket}: {len(ymap_bayrakli)}/{len(varliklar)} entities carry a flag "
                  f"with bit 8 ('LOD in parented ymap') set: "
                  f"{', '.join(str(d) for d in degerler)}. MEASURED: across 118 vanilla "
                  f"MLOs / 18,799 entities this bit is NEVER used (0 occurrences), while "
                  f"the same value without it (1572864) appears 2272 times. With no "
                  f"parent map the entity is SILENTLY dropped. Common MLO value is "
                  f"{MLO_BAYRAK_YAYGIN} -- decode it, do not copy it. {ilk}"
                  + (f" and {kalan} more." if kalan > 0 else "")}),
            f"assetdb.py flags {degerler[0]} --entity")

    if sahipsiz:
        ornek = ", ".join(f"#{i} ({ad})" for i, ad in sahipsiz[:4])
        kalan = len(sahipsiz) - 4
        rap.ekle(SILENT, "YTY007", yol, _tr({
            "tr": f"{etiket}: {len(sahipsiz)}/{len(varliklar)} entity hicbir odanin ya "
                  f"da portalin attachedObjects listesinde YOK -> oyun onlari HIC "
                  f"OLUSTURMAZ, hata da vermez. {ornek}"
                  + (f" ve {kalan} tane daha." if kalan > 0 else ""),
            "en": f"{etiket}: {len(sahipsiz)}/{len(varliklar)} entities are in NO room's "
                  f"or portal's attachedObjects list -> the game NEVER creates them and "
                  f"reports no error. {ornek}"
                  + (f" and {kalan} more." if kalan > 0 else "")}))



# =============================================================================
# Drawable / Fragment — gomulu isiklar
# =============================================================================
# Isiklar <kok>/Lights altindadir; hem .ydr (Drawable) hem .yft (Fragment)
# kokunde ayni yerde (olculdu: prop_worklight_01a.yft -> Fragment/Lights=1,
# Fragment/Drawable/Lights YOK). Buradaki her kusur SESSIZDIR: dosya derlenir,
# oyun hata vermez, isik sadece yanmaz.


def denetle_drawable(kok, yol, rap, derlenmis=False):
    import light as _light

    isiklar = _light.isiklari_oku(kok)
    if not isiklar:
        return  # isik yok -> bu modul icin denetlenecek bir sey de yok

    yanmaz, sifir, menzilsiz, koni = [], [], [], []
    for idx, i in enumerate(isiklar):
        if not _light.aktif_saatler(i["TimeFlags"]):
            yanmaz.append(idx)
        if i["Intensity"] is not None and i["Intensity"] <= 0:
            sifir.append(idx)
        if i["Falloff"] is not None and i["Falloff"] <= 0:
            menzilsiz.append(idx)
        if i["Type"] == "Spot":
            ic, dis = i["ConeInnerAngle"], i["ConeOuterAngle"]
            if dis is not None and dis <= 0:
                koni.append(f"#{idx} disaci 0")
            elif ic is not None and dis is not None and ic > dis:
                koni.append(f"#{idx} ic{ic:g}>dis{dis:g}")

    if yanmaz:
        # SEVIYE WARN, SILENT DEGIL -- ve bu bilincli bir geri adim.
        # Ilk surumde "isik HIC YANMAZ" diye SILENT raporlaniyordu; dayanak
        # 53 isiklik bir orneklemde TimeFlags 0'in hic gorulmemesiydi. Tam
        # korpus olculunce (72.539 isik) 0 degeri 8 kez cikti ve ciktigi
        # yerler ic mekan lamba prop'lariydi. Yani "0 = hic yanmaz" ile
        # "0 = saat kisiti yok" okumalarinin IKISI DE veriyle uyumlu.
        # Veriden cozulemeyen bir seyi kesinmis gibi raporlamak, aracin
        # onlemeye calistigi hatanin ta kendisi olurdu.
        rap.ekle(WARN, "LGT001", yol, _tr({
            "tr": f"{len(yanmaz)}/{len(isiklar)} isikta TimeFlags 0 (hicbir saat biti). "
                  f"Vanilla'da cok nadir: 72539 isikta 8 kez (%0.011). '0 = hic "
                  f"yanmaz' mi '0 = saat kisiti yok' mu oldugu bu veriden "
                  f"COZULEMEZ -- oyunda gece ve gunduz test et. Isik #{yanmaz[:5]}",
            "en": f"{len(yanmaz)}/{len(isiklar)} light(s) have TimeFlags 0 (no hour bit). "
                  f"Very rare in vanilla: 8 out of 72539 lights (0.011%). Whether 0 "
                  f"means 'never lights' or 'no time restriction' CANNOT be resolved "
                  f"from this data -- test in game at night and at noon. "
                  f"Light #{yanmaz[:5]}"}),
            "assetdb.py light --tablo")
    if sifir:
        rap.ekle(SILENT, "LGT002", yol, _tr({
            "tr": f"{len(sifir)}/{len(isiklar)} isikta Intensity 0 -> isik yayilmaz. "
                  f"Isik #{sifir[:5]}",
            "en": f"{len(sifir)}/{len(isiklar)} light(s) have Intensity 0 -> no light is "
                  f"emitted. Light #{sifir[:5]}"}))
    if menzilsiz:
        rap.ekle(SILENT, "LGT003", yol, _tr({
            "tr": f"{len(menzilsiz)}/{len(isiklar)} isikta Falloff 0 -> menzil yok, isik "
                  f"hicbir yuzeye ulasmaz. Isik #{menzilsiz[:5]}",
            "en": f"{len(menzilsiz)}/{len(isiklar)} light(s) have Falloff 0 -> no range, "
                  f"the light reaches no surface. Light #{menzilsiz[:5]}"}))
    if koni:
        rap.ekle(SILENT, "LGT004", yol, _tr({
            "tr": f"{len(koni)} spot isikta koni gecersiz: {', '.join(koni[:4])}",
            "en": f"{len(koni)} spot light(s) have an invalid cone: {', '.join(koni[:4])}"}))


DENETCI = {
    "Drawable": denetle_drawable,
    "Fragment": denetle_drawable,
    "ClipDictionary": denetle_ycd,
    "CMapTypes": denetle_ytyp,
}

# XML yorumu icinde iki tire dosyayi ayristirilamaz yapar. Oyun HATA VERMEZ,
