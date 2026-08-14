#!/usr/bin/env python3
"""build_framework.py — FiveM framework API indeksi (export / event / fonksiyon).

  python scripts/build_framework.py --resources <sunucu resources klasoru>

NEDEN VAR
---------
lint_lua.py bugun yalniz GTA NATIVE'lerini dogruluyor. Ama bir QBCore/ox
kaynaginda hatalarin cogu native'de degil, FRAMEWORK cagrisinda olur:

    exports['qb-core']:GetCoreObj()          -- yazim hatasi, nil doner
    TriggerServerEvent('qb-inventory:server:closeInv')  -- olmayan event, sessiz
    lib.showTextUI(...)                       -- ox_lib modulu yanlis yazilmis

Bunlarin hicbiri hata FIRLATMAZ. Event yoksa tetikleme sessizce hicbir yere
gitmez; export yoksa `nil value` ancak o satir CALISINCA patlar - ve o satir
oyunda belki ayda bir calisir.

OTORITE SECIMI (onemli)
-----------------------
Bu indeks upstream GitHub'dan degil, SUNUCUDA KURULU kaynaklardan uretilir.
Sebep: upstream master ile kurulu surum ayni degildir. Bir export upstream'de
eklenmis ama senin qb-core'unda yoksa, "gecerli" demek yaniltir. Kurulu surum
tek gecerli otoritedir. fxmanifest'teki `version` alani da kaydedilir.

TANIMLI ile KULLANILAN AYRIMI
-----------------------------
`kind` kolonu iki sinifi ayirir:
  export/event/function  -> TANIM (bu kaynak saglar)  = OTORITE
  export_use/event_use   -> KULLANIM (bu kaynak cagirir) = ADAY
Bir kullanim hicbir tanimla eslesmiyorsa suphelidir. Ama otomatik "hata" deme:
tanim baska bir kaynakta, baska bir dilde (JS/C#) ya da runtime'da uretilmis
olabilir. Bu yuzden lint tarafi UYARI uretir, HATA degil.
"""
from __future__ import annotations

import argparse
import datetime
import gzip
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
OUT = os.path.join(DATA, "framework_api.tsv.gz")

COLS = ["resource", "kind", "name", "side", "file", "line", "version"]

# --- desenler ---------------------------------------------------------------
# Lua'da tirnak tek ya da cift olabilir; ikisini de yakala.
Q = r"""['"]([^'"]+)['"]"""

TANIM = [
    ("export", re.compile(r"\bexports\(\s*" + Q)),                 # exports('ad', fn)
    ("event", re.compile(r"\bRegisterNetEvent\(\s*" + Q)),
    ("event", re.compile(r"\bAddEventHandler\(\s*" + Q)),
    ("command", re.compile(r"\bRegisterCommand\(\s*" + Q)),
    ("command", re.compile(r"\blib\.addCommand\(\s*" + Q)),
    ("callback", re.compile(r"\blib\.callback\.register\(\s*" + Q)),
    ("callback", re.compile(r"CreateCallback\(\s*" + Q)),          # QBCore.Functions.CreateCallback
]

KULLANIM = [
    ("event_use", re.compile(r"\bTriggerServerEvent\(\s*" + Q)),
    ("event_use", re.compile(r"\bTriggerClientEvent\(\s*" + Q)),
    ("event_use", re.compile(r"\bTriggerEvent\(\s*" + Q)),
    ("callback_use", re.compile(r"\blib\.callback\(\s*" + Q)),
    ("callback_use", re.compile(r"TriggerCallback\(\s*" + Q)),
]

# exports.<kaynak>:<ad>(   ve   exports['<kaynak>']:<ad>(
EXP_USE = re.compile(r"\bexports(?:\.(\w+)|\[\s*['\"]([\w-]+)['\"]\s*\])\s*:\s*(\w+)")
# lib.<modul>  (ox_lib)
LIB_USE = re.compile(r"\blib\.(\w+)")

YORUM = re.compile(r"^\s*--")


def manifest_bilgisi(kok):
    """fxmanifest'ten surum + hangi dosya hangi tarafta.

    Taraf tespiti dosya adindan DEGIL manifest'ten yapilir: 'main.lua' hem
    client hem server olabilir ve ad tahmini sessizce yanlis taraf atar.
    """
    surum, taraf = "", {}
    for ad in ("fxmanifest.lua", "__resource.lua"):
        p = os.path.join(kok, ad)
        if not os.path.exists(p):
            continue
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        m = re.search(r"^\s*version\s+['\"]([^'\"]+)['\"]", t, re.M)
        if m:
            surum = m.group(1)
        for blok, yan in (("client_scripts?", "client"), ("server_scripts?", "server"),
                          ("shared_scripts?", "shared")):
            for mb in re.finditer(blok + r"\s*\{(.*?)\}", t, re.S):
                for f in re.findall(Q, mb.group(1)):
                    taraf[f.replace("\\", "/").lower()] = yan
            for mb in re.finditer(blok + r"\s+" + Q, t):
                taraf[mb.group(1).replace("\\", "/").lower()] = yan
        break
    return surum, taraf


def taraf_bul(rel, taraf_map):
    """Manifest eslesmesi; glob (*) desenleri de kabaca karsilanir."""
    r = rel.replace("\\", "/").lower()
    if r in taraf_map:
        return taraf_map[r]
    for kalip, yan in taraf_map.items():
        if "*" in kalip:
            rx = re.escape(kalip).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
            if re.fullmatch(rx, r):
                return yan
    # Manifest sessizse ad ipucuna DUS, ama bunu 'shared' diye isaretle:
    # yanlis taraf atamasi, taraf bilgisi yoklugundan daha zararlidir.
    if "/server" in r or r.startswith("server"):
        return "server"
    if "/client" in r or r.startswith("client"):
        return "client"
    return "shared"


# exports(index, value) gibi TIRNAKSIZ ilk arguman = dinamik export dongusu.
# ox_target tam olarak boyle yapar:  for index, value in pairs(api) do exports(index, value) end
DINAMIK_EXPORT = re.compile(r"\bexports\(\s*(?!['\"])\w+\s*,")
# function api.addBoxZone(...)  /  function Core.GetPlayer(...)
TABLO_FN = re.compile(r"^\s*function\s+(\w+)\.(\w+)\s*\(")


def tara(kaynak_kok):
    kaynak = os.path.basename(kaynak_kok)
    surum, taraf_map = manifest_bilgisi(kaynak_kok)
    satirlar = []
    # Once dinamik export var mi diye bak: varsa tablo fonksiyonlari da export'tur.
    # ⛔ Bu olculdu: ox_target'in 30+ gercek export'u ('addBoxZone', 'addLocalEntity',
    # 'removeZone'...) literal tirnakla HIC gecmez; yalniz `function api.X(` olarak
    # tanimlanip dongude verilir. Bu kalibi tanimayan bir denetim onlari
    # "tanimsiz export" diye isaretler ve kural kullanilamaz hale gelir.
    dinamik = False
    for dirp, dirs, files in os.walk(kaynak_kok):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "stream", "web")]
        for f in files:
            if f.endswith(".lua"):
                try:
                    if DINAMIK_EXPORT.search(open(os.path.join(dirp, f), encoding="utf-8",
                                                  errors="replace").read()):
                        dinamik = True
                        break
                except Exception:
                    pass
        if dinamik:
            break
    for dirp, dirs, files in os.walk(kaynak_kok):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "stream", "web")]
        for f in files:
            if not f.endswith(".lua"):
                continue
            tam = os.path.join(dirp, f)
            rel = os.path.relpath(tam, kaynak_kok).replace("\\", "/")
            yan = taraf_bul(rel, taraf_map)
            try:
                metin = open(tam, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for i, satir in enumerate(metin.split("\n"), 1):
                if YORUM.match(satir):
                    continue
                for kind, rx in TANIM:
                    for m in rx.finditer(satir):
                        satirlar.append([kaynak, kind, m.group(1), yan, rel, str(i), surum])
                for kind, rx in KULLANIM:
                    for m in rx.finditer(satir):
                        satirlar.append([kaynak, kind, m.group(1), yan, rel, str(i), surum])
                for m in EXP_USE.finditer(satir):
                    hedef = m.group(1) or m.group(2)
                    satirlar.append([kaynak, "export_use", f"{hedef}:{m.group(3)}",
                                     yan, rel, str(i), surum])
                for m in LIB_USE.finditer(satir):
                    satirlar.append([kaynak, "lib_use", m.group(1), yan, rel, str(i), surum])
                if dinamik:
                    m = TABLO_FN.match(satir)
                    if m:
                        satirlar.append([kaynak, "export", m.group(2), yan, rel, str(i), surum])
    return satirlar


LIB_DEF = re.compile(r"(?:function\s+lib\.(\w+)\s*\(|\blib\.(\w+)\s*=)")


def oxlib_modulleri(kok):
    """ox_lib'in GERCEK API yuzeyi.

    ⛔ OLCULMUS TUZAK: yalniz `imports/` alt klasorlerini saymak YANLIS.
    imports/ 59 klasor verir ama gercek fonksiyonlarin buyuk kismi
    `resource/` altinda tanimlidir - `lib.notify` orada
    (resource/interface/client/notify.lua:33). Sadece imports/'a bakan ilk
    surum, 2216 `lib.*` cagrisinin %46,8'ini "olmayan modul" diye isaretledi;
    `lib.notify` tek basina 380 kez kullaniliyor. Bir linter her seye kizarsa
    kullanilmaz hale gelir ve GERCEK hatalari da kacirirsin.

    Dogrusu: tum agacta `function lib.X(` ve `lib.X =` tanimlarini topla,
    imports/ klasorlerini de ekle (ikisinin BIRLESIMI).
    """
    out, gorulen = [], set()
    surum, _ = manifest_bilgisi(kok)

    imp = os.path.join(kok, "imports")
    if os.path.isdir(imp):
        for d in sorted(os.listdir(imp)):
            if os.path.isdir(os.path.join(imp, d)):
                gorulen.add(d.lower())
                out.append(["ox_lib", "lib_module", d, "shared", f"imports/{d}", "0", surum])

    for dirp, dirs, files in os.walk(kok):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "web")]
        for f in files:
            if not f.endswith(".lua"):
                continue
            tam = os.path.join(dirp, f)
            rel = os.path.relpath(tam, kok).replace("\\", "/")
            yan = "server" if "/server" in "/" + rel else ("client" if "/client" in "/" + rel else "shared")
            try:
                metin = open(tam, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for i, satir in enumerate(metin.split("\n"), 1):
                if YORUM.match(satir):
                    continue
                for m in LIB_DEF.finditer(satir):
                    ad = m.group(1) or m.group(2)
                    if not ad or ad.startswith("__") or ad.lower() in gorulen:
                        continue
                    gorulen.add(ad.lower())
                    out.append(["ox_lib", "lib_module", ad, yan, rel, str(i), surum])
    return out


def main():
    ap = argparse.ArgumentParser(description="FiveM framework API indeksi")
    ap.add_argument("--resources", required=True, help="sunucu resources klasoru")
    ap.add_argument("--only", nargs="*", help="yalniz bu kaynaklar")
    a = ap.parse_args()

    if not os.path.isdir(a.resources):
        sys.exit(f"HATA: resources klasoru yok: {a.resources}")

    # Kaynak = icinde fxmanifest olan her klasor ([kategori] klasorleri dahil).
    kokler = []
    for dirp, dirs, files in os.walk(a.resources):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "stream")]
        if "fxmanifest.lua" in files or "__resource.lua" in files:
            kokler.append(dirp)
            dirs[:] = []
    if a.only:
        sec = {x.lower() for x in a.only}
        kokler = [k for k in kokler if os.path.basename(k).lower() in sec]

    print(f"Kaynak taranacak: {len(kokler)}")
    tum = []
    for k in sorted(kokler):
        ad = os.path.basename(k)
        surum, _ = manifest_bilgisi(k)
        # ⛔ KURULU KAYNAK LISTESI AYRICA YAZILIR.
        # Kurulu kumeyi satirlardan turetmek YANLIS: hic export/event tanimlamayan
        # bir kaynak sifir satir uretir ve "kurulu degil" gorunur. Bu tam olarak
        # yasandi. Satir yoklugu, kaynak yoklugu DEGILDIR.
        tum.append([ad, "resource", ad, "shared", os.path.relpath(k, a.resources).replace("\\", "/"),
                    "0", surum])
        r = tara(k)
        if ad == "ox_lib":
            r += oxlib_modulleri(k)
        tum += r

    tmp = OUT + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(COLS) + "\n")
        for r in tum:
            fh.write("\t".join(x.replace("\t", " ") for x in r) + "\n")
    with gzip.open(tmp, "rt", encoding="utf-8") as fh:
        head = fh.readline().rstrip("\n").split("\t")
        n = sum(1 for _ in fh)
    if head != COLS or n != len(tum):
        os.remove(tmp)
        sys.exit(f"HATA: geri okuma tutmadi ({n} vs {len(tum)})")
    os.replace(tmp, OUT)

    say = {}
    for r in tum:
        say[r[1]] = say.get(r[1], 0) + 1
    print(f"\n  framework_api.tsv.gz  {n} satir  {os.path.getsize(OUT)/1024:.1f} KB")
    for k in sorted(say, key=lambda x: -say[x]):
        print(f"    {k:<14} {say[k]:>6}")

    meta_p = os.path.join(DATA, "dumps.meta.json")
    meta = {}
    if os.path.exists(meta_p):
        try:
            meta = json.load(open(meta_p, encoding="utf-8"))
        except Exception:
            meta = {}
    meta.setdefault("rows", {})["framework_api"] = n
    meta["frameworkScannedAtUtc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    meta["frameworkSource"] = a.resources
    meta["frameworkResources"] = len(kokler)
    with open(meta_p, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
