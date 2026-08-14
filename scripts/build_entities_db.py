#!/usr/bin/env python3
"""build_entities_db.py — entities.tsv.gz -> entities.db (SQLite, indeksli).

3 milyon satirda dogrusal tarama yavas; sorgunun aninda donmesi icin
SQLite'a aliyoruz. Isimler sozluk-kodlu (names tablosu) tutuluyor ki
dosya makul kalsin.

Kullanim:
  python build_entities_db.py [--drop-tsv]
"""
from __future__ import annotations

import argparse
import gzip
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
TSV = os.path.join(DATA, "entities.tsv.gz")
DB = os.path.join(DATA, "entities.db")

KIND = {"root": 0, "mlo": 1}

SCHEMA = """
PRAGMA journal_mode=OFF;
PRAGMA synchronous=OFF;
DROP TABLE IF EXISTS ent;
DROP TABLE IF EXISTS names;
CREATE TABLE names (id INTEGER PRIMARY KEY, name TEXT UNIQUE);
CREATE TABLE ent (
    nid  INTEGER NOT NULL,   -- names.id  (archetype adi)
    x    REAL NOT NULL,
    y    REAL NOT NULL,
    z    REAL NOT NULL,
    kind INTEGER NOT NULL,   -- 0=root ymap, 1=MLO ic mekan
    ymid INTEGER NOT NULL,   -- names.id  (ymap dosya adi)
    iid  INTEGER             -- names.id  (MLO adi) veya NULL
);
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop-tsv", action="store_true", help="import sonrasi entities.tsv.gz sil")
    args = ap.parse_args()

    if not os.path.exists(TSV):
        sys.exit(f"HATA: {TSV} yok. Once build_entities.ps1 calistir.")

    if os.path.exists(DB):
        os.remove(DB)

    t0 = time.time()
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)

    ids: dict[str, int] = {}

    def nid(s: str) -> int:
        i = ids.get(s)
        if i is None:
            i = len(ids) + 1
            ids[s] = i
        return i

    def rows():
        with gzip.open(TSV, "rt", encoding="utf-8", errors="replace") as fh:
            fh.readline()  # baslik
            for line in fh:
                p = line.rstrip("\n").split("\t")
                if len(p) != 7:
                    continue
                name, x, y, z, kind, ymap, interior = p
                try:
                    fx, fy, fz = float(x), float(y), float(z)
                except ValueError:
                    continue
                yield (nid(name), fx, fy, fz, KIND.get(kind, 0), nid(ymap),
                       nid(interior) if interior else None)

    con.executemany("INSERT INTO ent (nid,x,y,z,kind,ymid,iid) VALUES (?,?,?,?,?,?,?)", rows())
    con.executemany("INSERT INTO names (id,name) VALUES (?,?)", ((v, k) for k, v in ids.items()))

    n = con.execute("SELECT COUNT(*) FROM ent").fetchone()[0]
    print(f"[*] {n} entity, {len(ids)} benzersiz isim, {time.time()-t0:.1f} sn")

    print("[*] indeksler kuruluyor...")
    con.execute("CREATE INDEX ix_ent_nid ON ent(nid)")
    con.execute("CREATE INDEX ix_ent_x   ON ent(x)")   # 'near' sorgusu icin on eleme
    con.commit()
    con.execute("VACUUM")
    con.close()

    mb = os.path.getsize(DB) / 1024 / 1024
    print(f"[+] {DB}  ({mb:.0f} MB, {time.time()-t0:.1f} sn)")

    if args.drop_tsv:
        os.remove(TSV)
        print(f"[+] {TSV} silindi")


if __name__ == "__main__":
    main()
