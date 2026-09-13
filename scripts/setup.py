#!/usr/bin/env python3
"""setup.py — kurulum. 28 katmanın tamamını KULLANICININ KENDİ verisinden üretir.

  python scripts/setup.py --save --gta "<GTA V>" --codewalker "<...\\CodeWalker.Core.dll>" \\
                          --resources "<sunucu>/resources"
  python scripts/setup.py                # kayıtlı yollarla tekrar çalıştır
  python scripts/setup.py --plan         # hiçbir şey yazma, sadece durumu göster

TASARIM İLKESİ
--------------
Bu aracı kullanan HERKESTE GTA V ve CodeWalker vardır — bir GTA modlama
aracıdır. O yüzden eksik olan şey veri değil, **yol bilgisidir.** Kurulum
onu bir kez sorar, `data/config.json`'a yazar ve bir daha sormaz.

Ağır katmanlar bu yüzden İSTEĞE BAĞLI DEĞİL, VARSAYILANDIR. Yol biliniyorsa
kurulur. Kullanıcının elindeki gerçek veriyi kullanmamak, aracın var oluş
sebebine aykırıdır: veri yoksa sorgu EXIT 2 döner ve model TAHMİNE düşer.

NE DAĞITILIR, NE DAĞITILMAZ
---------------------------
Bu public sürümde oyun verisi DAĞITILMAZ: bütün katmanlar kullanıcının kendi
GTA V kurulumundan ve kendi sunucusundan yerelde üretilir. Depoda yalnız elle
yazılmış üç küçük tablo durur (collision_materials, collision_flag_presets,
light_presets).

Hiçbir durumda dağıtılmayan üç şey:
  1. `entities.db` (214 MB) — TÜRETİLMİŞ; kurulumda yerelde üretilir.
  2. `framework_api.tsv.gz` — KULLANICININ KENDİ SUNUCUSU. Her net event,
     her export, dosya yolu ve satır numarasıyla. Yayınlanması gizlilik
     değil GÜVENLİK sorunudur. Herkes kendi sunucusundan üretir.
  3. `config.json` / `assets.meta.json` / `dumps.meta.json` — yerel yol
     ve kullanıcı adı içerir.

⚠ SÜRÜM: katmanlar üretildikleri oyun sürümüne bağlıdır (ölçüldü: bir
kurulumda 1271 adet `m26_*` arketip var, eski bir dump'ta 0). Oyun
güncellenince `/asset-build`.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n import add_lang_arg, get_lang, set_lang  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
PY = sys.executable or "python"

# Aday listesi TEK YERDE: yol.py. Burada ikinci bir kopya tutulursa biri
# guncellenip digeri unutulur -- CodeWalker icin 29, GTA icin 23 kopya vardi.
from yol import KAYITLI as _YOL_KAYITLI  # noqa: E402

GTA_ADAYLARI = _YOL_KAYITLI["gta"][3]

# (dosya, kademe, aciklama, uretim komutu)
KATMANLAR = [
    ("natives.index.tsv", "hafif", "7191 native + apiset + imza",
     "python scripts/build_index.py --fetch"),
    ("peds_meta.tsv.gz", "hafif", "1109 ped: klip sozlugu, expression, clipset", "DUMP"),
    ("weapons.tsv.gz", "hafif", "184 silah", "DUMP"),
    ("weapon_parts.tsv.gz", "hafif", "634 bilesen + livery", "DUMP"),
    ("vehicles.tsv.gz", "hafif", "921 arac: handlingId, modkit", "DUMP"),
    ("mlo_interiors.tsv.gz", "hafif", "853 MLO konumu", "DUMP"),
    ("ipls.tsv.gz", "hafif", "895 IPL + sinir kutusu", "DUMP"),
    ("world_objects.tsv.gz", "hafif", "33912 dunya nesnesi + rotasyon", "DUMP"),
    ("framework_api.tsv.gz", "hafif", "QBCore/ox export-event indeksi", "FRAMEWORK"),
    ("archetypes.tsv.gz", "agir", "316k arketip (kapi, pivot, fizik)",
     "powershell -File scripts/build_archetypes.ps1"),
    # entities.tsv.gz depoda gelir; .db ondan uretilir. Tsv yoksa (ya da
    # kullanici kendi surumunden istiyorsa) once CodeWalker ile cikarilir.
    ("entities.db", "agir", "3M dunya yerlesimi (entities.tsv.gz'den kurulur)",
     "powershell -File scripts/build_entities.ps1 && python scripts/build_entities_db.py"),
    ("ymap_lod.tsv.gz", "agir", "3.1M ymap LOD zinciri",
     "powershell -File scripts/build_ymap_lod.ps1"),
    ("clips.tsv.gz", "agir", "316k klip: sure + kemik",
     "powershell -File scripts/build_clips.ps1"),
    ("skeletons.tsv.gz", "agir", "478k kemik kaydi",
     "powershell -File scripts/build_rigs.ps1"),
    ("expressions.tsv.gz", "agir", "2338 expression (.yed)",
     "powershell -File scripts/build_rigs.ps1"),
    ("ytyp_extensions.tsv.gz", "agir", "64k ytyp extension",
     "powershell -File scripts/build_extensions.ps1"),
    ("ptfx_effects.tsv.gz", "agir", "2549 partikul efekti",
     "powershell -File scripts/build_ptfx.ps1"),
    ("shaders.tsv", "agir", "249 shader", "python scripts/build_shaders.py"),
    ("collision_materials.tsv", "agir", "185 collision materyali", "(elle)"),
    ("decal_types.tsv", "agir", "194 decal tipi", "python scripts/build_decals.py"),
    ("procedural.tsv", "agir", "255 procedural kayit",
     "powershell -File scripts/build_procedural.ps1"),
    ("anims.tsv.gz", "hafif", "269k animasyon adi", "DUMP"),
    ("props.tsv.gz", "hafif", "21631 spawn edilebilir prop", "DUMP"),
    ("scenarios.tsv.gz", "hafif", "247 senaryo", "DUMP"),
]


def var(f):
    return os.path.exists(os.path.join(DATA, f))


def calistir(baslik, cmd, plan):
    print(f"\n>>> {baslik}")
    print(f"    {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if plan:
        print("    (--plan: calistirilmadi)")
        return None
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1800)
        cikti = (r.stdout or "").strip().split("\n")
        for l in cikti[-6:]:
            if l.strip():
                print(f"    {l}")
        if r.returncode != 0:
            hata = (r.stderr or "").strip().split("\n")
            for l in hata[-4:]:
                if l.strip():
                    print(f"    ! {l}")
        return r.returncode
    except Exception as e:
        print(f"    ! CALISTIRILAMADI: {e}")
        return 1


CONFIG = os.path.join(DATA, "config.json")


def config_oku():
    if os.path.exists(CONFIG):
        try:
            return json.load(open(CONFIG, encoding="utf-8-sig"))
        except Exception:
            return {}
    return {}


def config_yaz(gta, cw, resources, lang=None):
    """Yollari kaydeder ki bir daha sorulmasin.

    data/ .gitignore'da oldugu icin bu dosya asla repoya girmez - kisisel
    yol bilgisi paylasilmis olmaz.
    """
    d = config_oku()
    if gta:
        d["gtaFolder"] = gta
    if cw:
        d["codeWalker"] = cw
    if resources:
        d["resources"] = resources
    if lang:
        d["lang"] = lang
    os.makedirs(DATA, exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=2, ensure_ascii=False)
    print(f"\n  Yollar kaydedildi -> {CONFIG}")
    print("  Bir dahaki calistirmada sorulmaz.")


def gta_bul(verilen):
    if verilen:
        return verilen if os.path.isdir(verilen) else None
    import yol
    c, _ = yol.coz("gta")          # config.json + bilinen adaylar, tek kaynak
    if c:
        return c
    meta = os.path.join(DATA, "assets.meta.json")
    if os.path.exists(meta):
        try:
            g = json.load(open(meta, encoding="utf-8-sig")).get("gtaFolder")
            if g and os.path.isdir(g):
                return g
        except Exception:
            pass
    for p in GTA_ADAYLARI:
        if os.path.isdir(p):
            return p
    return None


def cw_bul(verilen):
    if verilen:
        return verilen if os.path.exists(verilen) else None
    import yol
    c, _ = yol.coz("codewalker")   # config.json + bilinen adaylar, tek kaynak
    if c:
        return c
    meta = os.path.join(DATA, "assets.meta.json")
    if os.path.exists(meta):
        try:
            c = json.load(open(meta, encoding="utf-8-sig")).get("codeWalker")
            if c and os.path.exists(c):
                return c
        except Exception:
            pass
    for kok in (os.path.expanduser("~/Desktop"), os.path.expanduser("~")):
        if not os.path.isdir(kok):
            continue
        for dirp, dirs, files in os.walk(kok):
            if dirp.count(os.sep) - kok.count(os.sep) > 3:
                dirs[:] = []
                continue
            if "CodeWalker.Core.dll" in files:
                return os.path.join(dirp, "CodeWalker.Core.dll")
    return None


def main():
    ap = argparse.ArgumentParser(description="fivem-natives kademeli kurulum")
    ap.add_argument("--resources", help="FiveM sunucusunun resources klasoru (framework indeksi icin)")
    ap.add_argument("--dump", help="gta-v-data-dumps klasoru (yoksa indirilir)")
    ap.add_argument("--gta", help="GTA V kurulum klasoru")
    ap.add_argument("--codewalker", help="CodeWalker.Core.dll yolu")
    ap.add_argument("--plan", action="store_true", help="hicbir sey yazma, sadece raporla")
    ap.add_argument("--light-only", "--hafif-only", dest="hafif_only", action="store_true",
                    help="skip layers built from GTA V / agir katmanlari kurma")
    add_lang_arg(ap)
    ap.add_argument("--save", action="store_true",
                    help="verilen yollari data/config.json'a kaydet (bir daha sorulmaz)")
    a = ap.parse_args()
    set_lang(getattr(a, "lang", None))

    os.makedirs(DATA, exist_ok=True)
    dump = a.dump or os.path.join(ROOT, "data", "_raw", "dumps")
    gta = gta_bul(a.gta)
    cw = cw_bul(a.codewalker)
    kayitli = config_oku()
    resources = a.resources or kayitli.get("resources")
    if a.save and not a.plan:
        config_yaz(gta, cw, resources, getattr(a, "lang", None))

    print("=" * 68)
    print("fivem-natives — kurulum")
    print("=" * 68)
    print(f"  plugin      : {ROOT}")
    print(f"  GTA V       : {gta or 'BULUNAMADI'}")
    print(f"  CodeWalker  : {cw or 'BULUNAMADI'}")
    print(f"  sunucu      : {resources or '(verilmedi)'}")
    print(f"  dump        : {dump}")
    eksik0 = [f for f, k, *_ in KATMANLAR if not var(f)]
    print(f"  durum       : {len(KATMANLAR) - len(eksik0)}/{len(KATMANLAR)} katman kurulu")

    # --- HAFIF KADEME ---
    print("\n" + "-" * 68)
    print("1) INTERNETTEN INEN KATMANLAR")
    print("-" * 68)

    if not var("natives.index.tsv"):
        calistir("Native veritabani (internet)",
                 [PY, "scripts/build_index.py", "--fetch"], a.plan)
    else:
        print("\n>>> Native veritabani  [zaten kurulu]")

    dump_eksik = [f for f, k, _d, c in KATMANLAR if c == "DUMP" and not var(f)]
    if dump_eksik:
        # --fetch DAIMA verilir: var olan dosyalari atlar, EKSIK olani indirir.
        # "klasor doluysa indirme" mantigi, kaynak listesine dosya eklendiginde
        # sessizce eksik birakiyordu.
        cmd = [PY, "scripts/build_dumps.py", "--dump", dump, "--fetch"]
        calistir(f"Dump katmanlari ({len(dump_eksik)} eksik)", cmd, a.plan)
    else:
        print("\n>>> Dump katmanlari  [zaten kurulu]")

    if resources:
        if os.path.isdir(resources):
            calistir("Framework indeksi (senin sunucun)",
                     [PY, "scripts/build_framework.py", "--resources", resources], a.plan)
        else:
            print(f"\n>>> Framework indeksi  ATLANDI: klasor yok -> {resources}")
    else:
        print("\n>>> Framework indeksi  ATLANDI")
        print("    Sebep : --resources verilmedi")
        print("    Kur   : python scripts/setup.py --resources <sunucu>/resources")
        print("    Kazanc: kurulu olmayan kaynaga giden export/event cagrilari yakalanir")

    # --- AGIR KADEME ---
    print("\n" + "-" * 68)
    # --- HIZLI YOL: depodan gelen tsv'den entities.db kur ---
    # Klonlayan kullanicinin ilk karsilastigi eksik bu; CodeWalker'a hic
    # gerek yok cunku kaynak tsv zaten depoda.
    if var("entities.tsv.gz") and not var("entities.db"):
        calistir("entities.db — entities.tsv.gz'den kuruluyor (CodeWalker gerekmez)",
                 "python scripts/build_entities_db.py", a.plan)

    print("2) KENDI OYUNUNDAN URETILEN KATMANLAR  (varsayilan)")
    print("-" * 68)
    if not gta or not cw:
        eksik = []
        if not gta:
            eksik.append("GTA V kurulumu")
        if not cw:
            eksik.append("CodeWalker.Core.dll")
        print(f"\n  ⛔ YOL GEREKIYOR — bulunamadi: {', '.join(eksik)}")
        print()
        print("  Vanilla katmanlarin cogu depoda GELIR; asagidakiler ise senin")
        print("  oyun surumunden uretilmek istenirse ya da depoda yoksa gerekir.")
        print("  Bu araci kullanan herkeste GTA V ve CodeWalker zaten vardir;")
        print("  eksik olan sey veri degil, YOL bilgisidir.")
        print()
        print("  Yollari ver (bir kez; --save ile kaydedilir ve bir daha sorulmaz):")
        print()
        print("    python scripts/setup.py --save \\")
        print('      --gta "C:\\Program Files\\Epic Games\\GTAV" \\')
        print('      --codewalker "C:\\...\\CodeWalker\\CodeWalker.Core.dll"')
        print()
        print("  CodeWalker.Core.dll: CodeWalker'i indirdigin klasorde, exe'nin yaninda.")
    elif a.hafif_only:
        agir_eksik = [f for f, k, *_ in KATMANLAR if k == "agir" and not var(f)]
        print(f"\n  --hafif-only verildi, {len(agir_eksik)} agir katman atlandi.")
    else:
        # AGIR KADEME ARTIK VARSAYILAN. Yol biliniyorsa kurulur; "opt-in" yapmak
        # kullanicinin elindeki gercek veriyi bosa harcamakti.
        agir_eksik = [(f, d, c) for f, k, d, c in KATMANLAR
                      if k == "agir" and not var(f) and c != "(elle)"]
        if not agir_eksik:
            print("\n  Tum agir katmanlar kurulu.")
        else:
            print(f"\n  {len(agir_eksik)} agir katman uretilecek (GTA V: {gta})")
            print("  Bu islem birkac dakika surer (klipler ~3 dk, iskeletler daha uzun).")
            for f, d, c in agir_eksik:
                calistir(f"{f} — {d}", c, a.plan)

    # --- RAPOR ---
    print("\n" + "=" * 68)
    print("DURUM")
    print("=" * 68)
    kurulu = eksik = 0
    for f, k, d, c in KATMANLAR:
        if var(f):
            kurulu += 1
            print(f"  [VAR] {f:<26} {d}")
        else:
            eksik += 1
            print(f"  [YOK] {f:<26} {d}")
            print(f"        -> {c}")
    print(f"\n  {kurulu}/{kurulu + eksik} katman kurulu")
    if eksik:
        print("\n  ⚠ Eksik katmani kullanan sorgu EXIT 2 doner ve HICBIR SEY iddia etmez.")
        print("    Bunu 'asset yok' diye okuma — 1 (ad yok) ile 2 (katman yok) farklidir.")
    print("\n  Dogrula: python scripts/assetdb.py stats")
    return 0 if kurulu else 2


if __name__ == "__main__":
    sys.exit(main())
