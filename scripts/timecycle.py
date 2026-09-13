#!/usr/bin/env python3
"""timecycle.py — timecycle modifier sorgusu.

NEDEN VAR
=========
Ic mekanda bir prop'un koyu gorunmesinin sebebi cogu zaman prop'ta ya da
isikta DEGIL, odanin timecycle modifier'indadir. MLO odasi `timecycleName`
ile bir modifier'a baglanir; o modifier ortam isigini, pozlamayi, sisi ezer.
Isigi dogru kurup hala "karanlik" goruyorsan once buraya bakilir.

En cok ise yarayan parametreler (olculdu, 1087 modifier icinde kac kez
tanimlandiklari ile):
    postfx_intensity_bloom                1634
    postfx_bright_pass_thresh             1581
    artificial_int_ambient_multiplier     1393   <- ic mekan yapay ortam isigi
    natural_ambient_multiplier            1368   <- dogal ortam isigi
    light_artificial_int_down_intensity   1291
    light_artificial_int_up_intensity     1274

AYNI AD BIRDEN COK DLC'DE
=========================
1087 modifier'in 691'i birden cok kaynakta tanimli. Hangisinin kazandigi DLC
yukleme sirasina baglidir ve bu dosyadan OKUNAMAZ. Bu yuzden catisma
GIZLENMEZ: `--kaynak` ile hepsi gosterilir ve varsayilan ciktida uyarilir.

KULLANIM
========
    python assetdb.py timecycle <ad>
    python assetdb.py timecycle --ara hospital
    python assetdb.py timecycle <ad> --param ambient
    python assetdb.py timecycle <ad> --kaynak
"""
from __future__ import annotations

import collections
import gzip
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
TSV = os.path.join(DATA, "timecycle.tsv.gz")

# "Neden karanlik" sorusunun dogrudan cevabi olan parametreler one cikarilir.
ONEMLI = (
    "artificial_int_ambient_multiplier",
    "natural_ambient_multiplier",
    "light_artificial_int_down_intensity",
    "light_artificial_int_up_intensity",
    "light_ambient_multiplier",
    "postfx_exposure",
)


def satirlar():
    if not os.path.exists(TSV):
        return None
    with gzip.open(TSV, "rt", encoding="utf-8", errors="replace") as fh:
        fh.readline()
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            p = line.split("\t")
            if len(p) >= 6:
                yield {"modifier": p[0], "param": p[1], "v1": p[2], "v2": p[3],
                       "numMods": p[4], "source": p[5]}


def _kisa_kaynak(s):
    """Kaynagi AYIRT EDICI sekilde kisalt.

    Son iki parcayi almak yetmez: butun DLC'ler ayni sonu tasir
    ('.../dlc.rpf/timecycle_mods_1.xml'), dolayisiyla dort ayri DLC ekranda
    ayni satir olarak gorunur ve catisma raporu ise yaramaz hale gelir.
    Ayirt edici parca 'dlcpacks/<ad>' segmentidir.
    """
    s = s.replace("\\", "/")
    parca = [x for x in s.split("/") if x]
    dlc = ""
    for i, p in enumerate(parca):
        if p.lower() == "dlcpacks" and i + 1 < len(parca):
            dlc = parca[i + 1] + ":"
            break
    return dlc + "/".join(parca[-2:]) if len(parca) >= 2 else s


def cmd_ara(desen, limit):
    d = desen.lower()
    bulunan = collections.Counter()
    for r in satirlar():
        if d in r["modifier"].lower():
            bulunan[r["modifier"]] += 1
    if not bulunan:
        print(f"'{desen}' ile eslesen modifier yok.")
        return 1
    print(f"{len(bulunan)} modifier eslesti:\n")
    for ad, n in bulunan.most_common(limit):
        print(f"  {ad:<44} {n} parametre")
    if len(bulunan) > limit:
        print(f"\n  ... {len(bulunan) - limit} tane daha (--limit ile artir)")
    return 0


def cmd_goster(ad, param_filtre, kaynak_goster, limit):
    hedef = ad.lower()
    kayit = collections.defaultdict(list)   # kaynak -> [satir]
    for r in satirlar():
        if r["modifier"].lower() == hedef:
            kayit[r["source"]].append(r)

    if not kayit:
        # yakin ad onerisi
        yakin = sorted({r["modifier"] for r in satirlar()
                        if hedef in r["modifier"].lower()})[:6]
        print(f"'{ad}' diye bir timecycle modifier YOK.")
        if yakin:
            print("  benzer: " + ", ".join(yakin))
        return 1

    kaynaklar = list(kayit)
    print(f"modifier: {ad}")
    print(f"kaynak  : {len(kaynaklar)} dosyada tanimli")
    if len(kaynaklar) > 1:
        print("  ! Ayni modifier birden cok DLC'de tanimli. Hangisinin kazandigi "
              "DLC yukleme sirasina baglidir ve bu veriden OKUNAMAZ.")
        for k in kaynaklar:
            print(f"    - {_kisa_kaynak(k)}  ({len(kayit[k])} parametre)")

    # Varsayilan: ilk kaynagi goster (hepsini istersen --kaynak)
    gosterilecek = kaynaklar if kaynak_goster else kaynaklar[:1]

    for k in gosterilecek:
        if len(gosterilecek) > 1:
            print(f"\n--- {_kisa_kaynak(k)} ---")
        rows = kayit[k]
        onemli = [r for r in rows if r["param"] in ONEMLI]
        digeri = [r for r in rows if r["param"] not in ONEMLI]
        if param_filtre:
            f = param_filtre.lower()
            onemli = [r for r in onemli if f in r["param"].lower()]
            digeri = [r for r in digeri if f in r["param"].lower()]

        if onemli:
            print("\n  ISIK / ORTAM (once bunlara bak):")
            for r in onemli:
                print(f"    {r['param']:<40} {r['v1']:>10}  {r['v2']:>10}")
        if digeri:
            print(f"\n  diger ({len(digeri)}):")
            for r in digeri[:limit]:
                print(f"    {r['param']:<40} {r['v1']:>10}  {r['v2']:>10}")
            if len(digeri) > limit:
                print(f"    ... {len(digeri) - limit} tane daha (--limit ile artir)")
        if not onemli and not digeri:
            print("  (filtreyle eslesen parametre yok)")
    return 0


def joaat(s):
    h = 0
    for c in s.lower():
        h = (h + ord(c)) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    h = (h + (h << 15)) & 0xFFFFFFFF
    return h


def _ambient_haritasi():
    """{modifier: {param: value1}} — yalnizca ONEMLI parametreler + hash->ad.

    MLO odasinin `timecycleName` alani CodeWalker'da COZULMEMIS bir JOAAT
    hash'i olarak durur (`hash_CDE50982`). 1087 modifier adini hash'leyip
    geri eslemek onu okunur hale getirir -- dogrulandi: CDE50982 ->
    int_extlight_small, 55C419A1 -> gen_bank, BD2EC26B -> NEW_abattoir.
    """
    deger = collections.defaultdict(dict)
    for r in satirlar():
        if r["param"] in ONEMLI:
            deger[r["modifier"]].setdefault(r["param"], r["v1"])
    hash_ad = {joaat(a): a for a in deger}
    return deger, hash_ad


def cmd_mlo(yol):
    """Bir MLO ytyp'inin odalarini timecycle'lariyla birlikte listeler."""
    from res_xml import kok_oku

    kok, hata = kok_oku(yol)
    if hata:
        print(f"ERROR: {yol}: {hata}", file=sys.stderr)
        return 2

    deger, hash_ad = _ambient_haritasi()

    def coz(ham):
        ham = (ham or "").strip()
        if not ham:
            return None
        if ham.lower().startswith("hash_"):
            try:
                return hash_ad.get(int(ham[5:], 16))
            except ValueError:
                return None
        return ham

    mlolar = [a for a in kok.findall("./archetypes/Item")
              if a.get("type") == "CMloArchetypeDef"]
    if not mlolar:
        print(f"{os.path.basename(yol)}: MLO archetype yok.")
        return 1

    print(f"{os.path.basename(yol)}: {len(mlolar)} MLO")
    karanlik = 0
    for a in mlolar:
        odalar = a.findall("./rooms/Item")
        print(f"\n  {a.findtext('name')}  ({len(odalar)} oda)")
        for o in odalar:
            oda = (o.findtext("name") or "?").strip()
            ham = (o.findtext("timecycleName") or "").strip()
            ad = coz(ham)
            if not ham:
                print(f"    {oda:<26} (timecycle yok)")
                continue
            if ad is None:
                print(f"    {oda:<26} {ham}  <- COZULEMEDI (bu ad timecycle "
                      f"katmaninda yok)")
                continue
            p = deger.get(ad, {})
            dogal = p.get("natural_ambient_multiplier")
            yapay = p.get("artificial_int_ambient_multiplier")
            ek = ""
            try:
                if dogal is not None and yapay is not None \
                        and float(dogal) == 0 and float(yapay) == 0:
                    ek = "   <- HER IKI AMBIENT 0: dogrudan aydinlatilmayan her sey SIYAH"
                    karanlik += 1
            except ValueError:
                pass
            amb = ""
            if dogal is not None or yapay is not None:
                amb = f"  ambient dogal={dogal or '-'} yapay={yapay or '-'}"
            print(f"    {oda:<26} {ad}{amb}{ek}")

    if karanlik:
        print(f"\n  {karanlik} odada ortam isigi tamamen sifir. Bu odalarda bir "
              f"prop'un gorunmesi icin ONU AYDINLATAN bir isik olmak zorunda; "
              f"prop'un kendi rengi/dokusu yetmez.")
    return 0


def calistir(args):
    from doctor_common import _tr

    if not os.path.exists(TSV):
        print(f"ERROR: {TSV} yok.", file=sys.stderr)
        print("  " + _tr({
            "tr": "Katman kurulu degil: powershell -File build_timecycle.ps1",
            "en": "Layer not installed: powershell -File build_timecycle.ps1"}),
            file=sys.stderr)
        return 2

    if args.mlo:
        return cmd_mlo(args.mlo)
    if args.ara:
        return cmd_ara(args.ara, args.limit)
    if not args.name:
        # ozet
        mods = collections.Counter()
        params = collections.Counter()
        for r in satirlar():
            mods[r["modifier"]] += 1
            params[r["param"]] += 1
        print(f"timecycle katmani: {len(mods)} modifier, {len(params)} farkli "
              f"parametre, {sum(mods.values())} satir")
        print("\nen sik tanimlanan parametreler:")
        for p, n in params.most_common(8):
            yildiz = " *" if p in ONEMLI else ""
            print(f"  {p:<40} {n}{yildiz}")
        print("\n  * = 'neden karanlik' sorusunun dogrudan cevabi")
        print("\nbir modifier icin: assetdb.py timecycle <ad>")
        return 0
    return cmd_goster(args.name, args.param, args.kaynak, args.limit)
