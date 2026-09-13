#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_bench.py — oyundaki partikul testini DISARIDAN sur ve OLC.

NEDEN: partikul dogrulamasi bes tur boyunca "kullaniciyi oyuna sok, ekran
goruntusu iste, goruntuyu yorumla" dongusunde kaldi. Yorum katmani uc kez
yanlis teshise yol açtı (bkz. ptfx-flipbook-uretimi.md §1c). Bu betik o
katmani kaldirir: is dosyasi yazilir, sunucu istemciden SABIT KAMERAYLA
ekran goruntusu alir, goruntu piksel olcumuyle degerlendirilir.

⛔ SINIR: ekran goruntusu ISTEMCININ render'idir. Oyuncunun bagli olmasi
   sarttir; oyunu tamamen devre disi birakan bir yol YOKTUR -- test edilen
   sey zaten GTA'nin kendi render'i.

⛔ Stream (.ypt/.ydr) dosyasi DEGISTIYSE oyuncunun yeniden BAGLANMASI
   gerekir; `restart` yetmez, FiveM stream dosyalarini cache'ler. Bu betik
   yalniz ZATEN dagitilmis varliklari olcer.

Kullanim:
  python ptfx_bench.py tani            # numarali tani sayfalari
  python ptfx_bench.py hepsi           # 15 uretim efekti
  python ptfx_bench.py --olc <jpg>     # tek goruntuyu olc
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

import numpy as np
from PIL import Image

def _sunucu_resources():
    """Sunucunun resources klasoru: MUTO_ATLAS_SERVER ya da `assetdb.py path server`.

    Yol koda YAZILMAZ -- kullanicinin kendi sunucusu, kendi kayit defterinde.
    """
    env = os.environ.get("MUTO_ATLAS_SERVER")
    if env:
        return env
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import paths
        r = paths.resolve("server")
        p = r[0] if isinstance(r, tuple) else r
        return p or None
    except Exception:
        return None


_RES = _sunucu_resources()
# Tezgah kaynagi (`my_ptfx_test`) sunucuda ayrica kurulu olmalidir; depoda yoktur.
KAYNAK = os.path.join(_RES, "[script]", "my_ptfx_test") if _RES else ""
ISTEK = os.path.join(KAYNAK, "is", "istek.json")
SONUC = os.path.join(KAYNAK, "is", "sonuc.json")
# Sunucunun `fileName` yolunu neye gore cozdugu pesinen bilinmez; sonuc
# JSON'u gercek adi verir, ayrica bu koklerde aranir (resources'un ust klasorleri).
KOKLER = [os.path.dirname(_RES), os.path.dirname(os.path.dirname(_RES)),
          os.path.dirname(os.path.dirname(os.path.dirname(_RES)))] if _RES else []

URETIM = ["duman", "ates", "alev_topu", "toz", "buhar", "kivilcim", "sicrama",
          "kor", "sis", "kabarcik", "parca", "halka", "elektrik", "kan", "yaprak"]


# --------------------------------------------------------------- is surme
def is_gonder(adimlar, zaman_asimi=180):
    """is/istek.json yazar, is/sonuc.json'u bekler."""
    if not KAYNAK:
        raise SystemExit("sunucu yolu kayitli degil: assetdb.py path server <resources yolu> "
                         "(ya da MUTO_ATLAS_SERVER)")
    os.makedirs(os.path.dirname(ISTEK), exist_ok=True)
    if os.path.exists(SONUC):
        os.remove(SONUC)
    io.open(ISTEK, "w", encoding="utf-8").write(
        json.dumps({"adimlar": adimlar}, ensure_ascii=False))
    print("is gonderildi: %d adim -- sunucu bekleniyor" % len(adimlar))
    t0 = time.time()
    while time.time() - t0 < zaman_asimi:
        if os.path.exists(SONUC):
            ham = io.open(SONUC, encoding="utf-8", errors="replace").read()
            if ham.strip():
                try:
                    return json.loads(ham)
                except ValueError:
                    pass
        time.sleep(1.0)
    raise TimeoutError(
        "sunucu %d sn icinde cevap vermedi.\n"
        "  · oyunda bagli misin?\n"
        "  · `ensure my_ptfx_test` calisti mi (server.lua yeni)?\n"
        "  · konsolda '[my_ptfx] is alindi' yaziyor mu?" % zaman_asimi)


def b64_coz(yol_bagil):
    """Sunucunun yazdigi .b64 dosyasini JPEG'e cevirir, yolu dondurur."""
    import base64
    tam = os.path.join(KAYNAK, yol_bagil.replace("/", os.sep))
    if not os.path.exists(tam):
        return None
    ham = io.open(tam, encoding="ascii", errors="ignore").read().strip()
    if not ham:
        return None
    jpg = tam[:-4] + ".jpg"
    io.open(jpg, "wb").write(base64.b64decode(ham + "=" * (-len(ham) % 4)))
    return jpg


def dosya_bul(ad):
    """Sunucunun yazdigi ekran goruntusunu diskte bulur."""
    if ad and ad.endswith(".b64"):
        return b64_coz(ad)
    if ad and os.path.isabs(ad) and os.path.exists(ad):
        return ad
    for kok in KOKLER:
        y = os.path.join(kok, ad or "")
        if ad and os.path.exists(y):
            return y
    # son care: adi arayarak
    hedef = os.path.basename(ad or "")
    for kok in KOKLER:
        for dizin, _, dosyalar in os.walk(kok):
            if hedef and hedef in dosyalar:
                return os.path.join(dizin, hedef)
        break
    return None


# ----------------------------------------------------------------- olcum
def _bilesenler(maske):
    """Baglantili bilesen sayisi (4-komsuluk, yigin tabanli)."""
    h, w = maske.shape
    gor = np.zeros((h, w), bool)
    n, boy = 0, []
    for y in range(h):
        for x in range(w):
            if maske[y, x] and not gor[y, x]:
                n += 1
                yig = [(y, x)]
                gor[y, x] = True
                say = 0
                while yig:
                    cy, cx = yig.pop()
                    say += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and maske[ny, nx] and not gor[ny, nx]:
                            gor[ny, nx] = True
                            yig.append((ny, nx))
                boy.append(say)
    return n, boy


def olc(yol, kucult=3, esik_dilim=97.0, en_az=4):
    """Goruntudeki BEYAZ rakamlari sayar (numarali tani sayfasi icin).

    Dilimleme CALISIYORSA tek rakam gorunur; CALISMIYORSA sayfanin tamami
    cizilir ve onlarca rakam ayni anda gorunur. Olcut bilesen sayisidir.

    ⛔ MUTLAK PARLAKLIK ESIGI KULLANMA. Ilk surum `parlak > 205` diyordu
    ve gece cekilen karede rakamlar acikca goruldugu halde SIFIR saydi.
    Sahne aydinlatmasi kareden kareye degisir; esik SAHNEYE GORE alinir.
    """
    im = Image.open(yol).convert("RGB")
    k = im.resize((im.size[0] // kucult, im.size[1] // kucult), Image.LANCZOS)
    a = np.asarray(k, np.float32)
    gri = a.mean(axis=2)
    doygun = a.max(axis=2) - a.min(axis=2)
    # sahneye gore ust dilim + renksizlik: beyaz rakam bu ikisini birden saglar
    t = float(np.percentile(gri, esik_dilim))
    m = (gri >= t) & (doygun < 55)
    n, boy = _bilesenler(m)
    buyuk = [x for x in boy if x >= en_az]
    return {
        "dosya": os.path.basename(yol),
        "boyut": im.size,
        "esik": round(t, 1),
        "parlak_oran": float(m.mean()),
        "bilesen": n,
        "buyuk_bilesen": len(buyuk),
        "en_buyuk": max(boy) if boy else 0,
    }

def olc_fark(dolu_yol, bos_yol, kucult=3, esik=26, en_az=6):
    """Efektli kare ile TABAN kareyi karsilastirip yalniz efekti olcer.

    ⛔ Mutlak esik sahneyi de sayiyordu (referans karesinde 1027 bilesen,
    rakamlarla ilgisiz). Taban farki sahneyi tamamen denklem disi birakir.
    """
    a = np.asarray(Image.open(dolu_yol).convert("RGB"), np.float32)
    b = np.asarray(Image.open(bos_yol).convert("RGB"), np.float32)
    if a.shape != b.shape:
        return None
    d = np.abs(a - b).mean(axis=2)
    k = Image.fromarray(d.astype(np.uint8)).resize(
        (d.shape[1] // kucult, d.shape[0] // kucult), Image.LANCZOS)
    m = np.asarray(k, np.float32) >= esik
    n, boy = _bilesenler(m)
    buyuk = [x for x in boy if x >= en_az]
    return {
        "bilesen": n,
        "buyuk_bilesen": len(buyuk),
        "en_buyuk": max(boy) if boy else 0,
        "degisen_oran": float(m.mean()),
    }


def rapor(sonuc):
    print()
    print("%-22s %8s %10s %9s" % ("adim", "bilesen", "buyuk", "parlak%"))
    for a in sonuc.get("adimlar", []):
        if a.get("hata"):
            print("%-22s  HATA: %s" % (a["ad"], a["hata"]))
            continue
        y = dosya_bul(a.get("dosya"))
        if not y:
            print("%-22s  goruntu bulunamadi: %s" % (a["ad"], a.get("dosya")))
            continue
        tb = dosya_bul(a.get("taban")) if a.get("taban") else None
        if tb:
            o = olc_fark(y, tb)
            if o:
                print("%-22s %8d %10d %8.2f%%   %s"
                      % (a["ad"], o["bilesen"], o["buyuk_bilesen"],
                         o["degisen_oran"] * 100, os.path.basename(y)))
                continue
        o = olc(y)
        print("%-22s %8d %10d %8.2f%%   (taban yok) %s"
              % (a["ad"], o["bilesen"], o["buyuk_bilesen"],
                 o["parlak_oran"] * 100, os.path.basename(y)))


TANI = [
    {"ad": "referans", "varlik": "core", "efekt": "exp_grd_grenade_smoke",
     "olcek": 1.0, "mesafe": 3.5},
    {"ad": "tani_2x2", "varlik": "my_no2", "olcek": 1.0, "mesafe": 3.5},
    {"ad": "tani_7x7", "varlik": "my_no7", "olcek": 1.0, "mesafe": 3.5},
]

# Izgara x cozunurluk carpani. Calisan (2x2@256) ile bozuk (7x7@1024)
# arasinda IKI degisken vardi; dort kose ikisini ayirir.
IZGARA = [
    {"ad": "gA_2x2_256",  "varlik": "my_g1", "olcek": 1.0, "mesafe": 3.5},
    {"ad": "gB_2x2_1024", "varlik": "my_g2", "olcek": 1.0, "mesafe": 3.5},
    {"ad": "gC_7x7_256",  "varlik": "my_g3", "olcek": 1.0, "mesafe": 3.5},
    {"ad": "gD_7x7_1024", "varlik": "my_g4", "olcek": 1.0, "mesafe": 3.5},
    # Donor ile izgarayi ayiran son iki hucre:
    #   g5  = bizim kopyamiz (C4=48) + VANILLA'nin kendi 7x7 dokusu
    #   ref7= oyunun KENDI 7x7 efekti, dosya gondermiyoruz
    {"ad": "g5_7x7_vanilla_doku", "varlik": "my_g5", "olcek": 1.0, "mesafe": 3.5},
    {"ad": "ref7_oyunun_kendi", "varlik": "core", "efekt": "veh_respray_smoke",
     "olcek": 1.0, "mesafe": 3.5},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", nargs="?", default="tani", choices=["tani", "hepsi", "izgara"])
    ap.add_argument("--olc", help="tek goruntuyu olc ve cik")
    a = ap.parse_args()
    if a.olc:
        print(json.dumps(olc(a.olc), ensure_ascii=False, indent=2))
        return 0
    if a.mod == "izgara":
        adimlar = IZGARA
    else:
        adimlar = TANI if a.mod == "tani" else [
            {"ad": x, "varlik": "my_" + x, "olcek": 1.0, "mesafe": 4.0} for x in URETIM]
    s = is_gonder(adimlar)
    if s.get("hata"):
        print("SUNUCU HATASI: %s" % s["hata"])
        return 1
    rapor(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
