#!/usr/bin/env python3
"""build_anims.py — animasyon / prop / senaryo indekslerini uretir.

Kaynak: DurtyFree/gta-v-data-dumps (acik veri deposu, oyun dosyalarindan
uretilmis dokumler). Archetype verisinin aksine bunlar isim listeleridir;
oyunun kendi RPF'lerinden isim cikarmak mumkun ama gereksiz yere pahali.

Kullanim:
  python build_anims.py             # indir + indeksle
  python build_anims.py --offline   # daha once indirilmis ham dosyalari kullan

Cikti:
  data/anims.tsv.gz       dict <TAB> clip
  data/props.tsv.gz       prop adi (CREATE_OBJECT ile kullanilabilir)
  data/scenarios.tsv.gz   senaryo adi
  data/anims.meta.json
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
RAW = os.path.join(DATA, "_raw")

BASE = "https://raw.githubusercontent.com/DurtyFree/gta-v-data-dumps/master/"
SOURCES = {
    "animDictsCompact.json": "anims",
    "ObjectList.ini":        "props",
    "scenariosCompact.json": "scenarios",
}


def fetch(name: str, offline: bool) -> bytes:
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, name)
    if offline or os.path.exists(path):
        if os.path.exists(path):
            print(f"  [cache] {name}")
            with open(path, "rb") as fh:
                return fh.read()
        sys.exit(f"HATA: --offline verildi ama {path} yok.")
    print(f"  [indir] {BASE}{name}")
    req = urllib.request.Request(BASE + name, headers={"User-Agent": "fivem-assets-indexer"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    with open(path, "wb") as fh:
        fh.write(data)
    return data


def write_gz(path: str, lines) -> int:
    n = 0
    buf = io.StringIO()
    for line in lines:
        buf.write(line)
        buf.write("\n")
        n += 1
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as fh:
        fh.write(buf.getvalue())
    return n


def parse_anims(raw: bytes):
    """animDictsCompact.json -> (dict, clip) ciftleri.

    Ust yapinin dict mi list mi oldugu surume gore degisebiliyor; ikisini de
    kaldiriyoruz ki depo formati degisince sessizce bos indeks uretmeyelim.
    """
    obj = json.loads(raw.decode("utf-8-sig"))
    pairs = []

    if isinstance(obj, dict):
        for dct, clips in obj.items():
            if isinstance(clips, dict):
                clips = list(clips.keys())
            if isinstance(clips, list):
                for c in clips:
                    pairs.append((str(dct), str(c)))
    elif isinstance(obj, list):
        for item in obj:
            if not isinstance(item, dict):
                continue
            dct = item.get("Name") or item.get("name") or item.get("DictionaryName")
            clips = item.get("Animations") or item.get("animations") or item.get("Clips") or []
            if isinstance(clips, dict):
                clips = list(clips.keys())
            for c in clips:
                if isinstance(c, dict):
                    c = c.get("Name") or c.get("name")
                if c:
                    pairs.append((str(dct), str(c)))

    if not pairs:
        sys.exit("HATA: animDictsCompact.json'dan hic cift cikmadi — format degismis olabilir.")
    return pairs


def parse_props(raw: bytes):
    """ObjectList.ini -> prop adlari (satir basina bir ad)."""
    out = []
    for line in raw.decode("utf-8-sig", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith((";", "#", "[")):
            continue
        out.append(s)
    return out


def parse_scenarios(raw: bytes):
    obj = json.loads(raw.decode("utf-8-sig"))
    if isinstance(obj, dict):
        return [str(k) for k in obj.keys()]
    if isinstance(obj, list):
        out = []
        for it in obj:
            if isinstance(it, str):
                out.append(it)
            elif isinstance(it, dict):
                n = it.get("Name") or it.get("name")
                if n:
                    out.append(str(n))
        return out
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="sadece onbellekteki ham dosyalari kullan")
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)
    meta = {"generatedAtUtc": datetime.now(timezone.utc).isoformat(), "source": BASE}

    print("Kaynaklar:")
    raws = {name: fetch(name, args.offline) for name in SOURCES}

    pairs = parse_anims(raws["animDictsCompact.json"])
    dicts = {d for d, _ in pairs}
    n = write_gz(os.path.join(DATA, "anims.tsv.gz"),
                 (f"{d}\t{c}" for d, c in sorted(pairs)))
    print(f"[+] anims.tsv.gz      {n} clip / {len(dicts)} dictionary")
    meta["animClips"], meta["animDicts"] = n, len(dicts)

    props = sorted(set(parse_props(raws["ObjectList.ini"])))
    n = write_gz(os.path.join(DATA, "props.tsv.gz"), props)
    print(f"[+] props.tsv.gz      {n} prop")
    meta["props"] = n

    scen = sorted(set(parse_scenarios(raws["scenariosCompact.json"])))
    n = write_gz(os.path.join(DATA, "scenarios.tsv.gz"), scen)
    print(f"[+] scenarios.tsv.gz  {n} senaryo")
    meta["scenarios"] = n

    with open(os.path.join(DATA, "anims.meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
    print("[+] anims.meta.json")


if __name__ == "__main__":
    main()
