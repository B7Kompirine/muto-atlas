#!/usr/bin/env python3
"""bake_to_gta.py -- Blender'da bake edilmis PBR harita setini GTA V dokularina cevirir.

NEDEN: Blender/Substance ciktisi metallic-roughness PBR'dir. GTA V DEGILDIR.
  Olculdu (data/shaders.tsv, 249 shader): Roughness sampler 0, Gloss 0,
  Metallic 0, AO/Occlusion 0. Var olan SpecSampler (130 shader).
  Yani roughness TERS CEVRILIP specular'a, AO diffuse'un ICINE girer,
  metallic ise haritaya degil shader SKALERLERINE gider.

Olculdu (400+ vanilla malzeme .ytd, 1135 doku):
  normal   DXT1 278 / DXT5 18 / ATI2 6      -> DXT1 (%92)
  spec     DXT1  98 / DXT5  1               -> DXT1 (%99)
  diffuse  DXT1 570 / DXT5 161              -> alfa yoksa DXT1
  mip      log2(kisa kenar)-1, 4x4'te biter -> 832/921 (%90.3)
  boyut    diffuse/normal/spec medyani ucunde de 512, maks 2048

!! make_dds.py BU ISE UYMAZ: --kaynak yolu alfa YOKSA cikis veriyor
   (satir 154) cunku partikul sprite'i icin yazilmis. Malzeme haritalari
   opaktir. Bu betik onun dxt_dds() mip mantigini yeniden kullanir, alfa
   dayatmasini kullanmaz.

Kullanim:
  python bake_to_gta.py <bake_klasoru> --ad mtk_kaldirim --cikti <klasor>
  python bake_to_gta.py bake/ --ad mtk_kaldirim --cikti out/ --boyut 1024 --pxm
"""
from __future__ import annotations

import argparse
import math
import re
import struct
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops
except ImportError:
    sys.exit("Pillow gerekli:  pip install Pillow")

from make_dds import (MIN_MIP, DDSD_CAPS, DDSD_HEIGHT, DDSD_WIDTH,
                      DDSD_PIXELFORMAT, DDSD_MIPMAPCOUNT, DDSD_LINEARSIZE,
                      DDPF_FOURCC, DDSCAPS_COMPLEX, DDSCAPS_TEXTURE,
                      DDSCAPS_MIPMAP, dxt_dds, dxt_govde)


def _dds_basligi(gen: int, yuk: int, fourcc: str, seviye: int) -> bytes:
    bpb = 8 if fourcc == "DXT1" else 16
    blok = max(1, (gen + 3) // 4) * max(1, (yuk + 3) // 4) * bpb
    bayrak = (DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT
              | DDSD_LINEARSIZE | DDSD_MIPMAPCOUNT)
    h = struct.pack("<7I", 124, bayrak, yuk, gen, blok, 0, seviye)
    h += b"\x00" * 44
    h += (struct.pack("<2I", 32, DDPF_FOURCC) + fourcc.encode("ascii")
          + struct.pack("<5I", 0, 0, 0, 0, 0))
    h += struct.pack("<5I", DDSCAPS_TEXTURE | DDSCAPS_MIPMAP | DDSCAPS_COMPLEX,
                     0, 0, 0, 0)
    return b"DDS " + h


def dxt_dds_kapsamli(rgb: "Image.Image", alfa: "Image.Image",
                     esik: int = 128) -> tuple[bytes, int, list]:
    """Cutout icin ALFA KAPSAMI KORUYAN mip zinciri uretir.

    !! NEDEN GEREKLI -- OLCULDU: duz kucultmede 512px'de %34.2 olan kapsam
       (alfa>=esik orani) 64px'de %43.8'e ciktiktan sonra 16px'de %0'a
       DUSUYOR. Yani izgara belli mesafeden sonra TAMAMEN KAYBOLUYOR ve
       hicbir hata verilmiyor -- sadece "uzakta gozukmuyor" diye fark edilir.

    Cozum (NVTT'nin alpha-coverage yontemi): her mip'te alfayi oyle bir k
    ile olceklendir ki esik ustunde kalan piksel orani mip 0 ile ayni olsun.
    """
    import numpy as np

    def kapsam(a: "np.ndarray") -> float:
        return float((a >= esik).mean())

    a0 = np.asarray(alfa, dtype=np.float32)
    hedef = kapsam(a0)

    seviyeler, olcumler = [], []
    r_im, a_im = rgb, alfa
    while r_im.width >= MIN_MIP and r_im.height >= MIN_MIP:
        a = np.asarray(a_im, dtype=np.float32)
        if seviyeler and hedef > 0:
            # kapsam(k) k'de monoton artar -> gecis noktasini ikili aramayla bul
            lo, hi = 0.0, 8.0
            for _ in range(28):
                orta = (lo + hi) / 2
                if kapsam(np.clip(a * orta, 0, 255)) < hedef:
                    lo = orta
                else:
                    hi = orta
            # !! GECIS NOKTASINI KORU KORUNE ALMA. Kucuk mip'lerde alfa
            #    neredeyse tekduzedir, kapsam basamak fonksiyonudur ve tek
            #    adimda 0'dan 1'e sicrar. Olculdu: 4x4'te hi tarafi %68.75
            #    (hedef %34.23). Iki tarafi da olcup HEDEFE YAKIN olani sec.
            a_lo = np.clip(a * lo, 0, 255)
            a_hi = np.clip(a * hi, 0, 255)
            k_lo, k_hi = kapsam(a_lo), kapsam(a_hi)
            a = a_lo if abs(k_lo - hedef) <= abs(k_hi - hedef) else a_hi
            # ...ama YOK OLMAYA izin verme: hedefin yarisinin altina duserse
            #    obur tarafi al. Kaybolan izgara, kalin izgaradan daha kotudur.
            if kapsam(a) < hedef * 0.5:
                a = a_hi if kapsam(a_hi) > kapsam(a_lo) else a_lo
        olcumler.append((r_im.width, kapsam(a)))
        birlesik = Image.merge("RGBA", (*r_im.split(),
                                        Image.fromarray(a.astype("uint8"), "L")))
        seviyeler.append(dxt_govde(birlesik, "DXT5"))
        if r_im.width == MIN_MIP or r_im.height == MIN_MIP:
            break
        yeni = (max(MIN_MIP, r_im.width // 2), max(MIN_MIP, r_im.height // 2))
        r_im = r_im.resize(yeni, Image.LANCZOS)
        a_im = a_im.resize(yeni, Image.LANCZOS)

    basl = _dds_basligi(rgb.width, rgb.height, "DXT5", len(seviyeler))
    return basl + b"".join(seviyeler), len(seviyeler), olcumler

# Dosya adindan harita turu tanima. Blender File Output node'unun yazdigi
# adlar ("Base Color", "Roughness"...) ve yaygin Substance/Quixel adlari.
DESENLER = {
    "basecolor":   r"base[\s_-]*color|basecolor|albedo|diffuse|_col\b|_d\b",
    "roughness":   r"rough",
    "normal":      r"normal|_nrm\b|_n\b",
    "height":      r"displace|height|_disp\b|_h\b",
    # !! "\bao\b" YAZMA: alt cizgi kelime karakteridir, "_ao" sinir uretmez ve
    #    dosya SESSIZCE atlanir. Ayirici sinifi acikca yazilir.
    "ao":          r"(^|[_\-. ])(ao|occ)($|[_\-. ])|ambient|occlusion",
    "metallic":    r"metal",
    "alpha":       r"(^|[_\-. ])(alpha|opacity|mask|msk)($|[_\-. ])|transparen",
}

# bul() bu SIRAYLA dener; ilk eslesen kazanir. Sira degistirilmemeli:
# "alpha" basecolor'dan once gelmeli ki "..._BaseColor_Alpha" alfa sayilsin,
# "basecolor" da normal'den once gelmeli ki "normal_stone_basecolor" normal
# sanilmasin.
SIRA = ("ao", "metallic", "roughness", "height", "alpha", "basecolor", "normal")


def bul(klasor: Path) -> tuple[dict[str, Path], list[Path]]:
    """Goruntuleri harita turlerine esler -> (eslesen, ESLESMEYEN).

    !! Eslesmeyenler DONDURULUR ve cagiran tarafta EKRANA YAZILIR. Sessizce
       atlamak, eksik haritayi "yoktu" sanmaya yol acar -- bir kez oldu
       (AO dosyasi "\\bao\\b" desenine takilmadi ve hic uyarilmadi).
    """
    uzanti = {".png", ".tif", ".tiff", ".jpg", ".jpeg", ".exr", ".tga", ".bmp"}
    bulunan: dict[str, Path] = {}
    artan: list[Path] = []
    for p in sorted(klasor.iterdir()):
        if not p.is_file() or p.suffix.lower() not in uzanti:
            continue
        # !! KARE NUMARASINI KIRP. Blender File Output dosya adinin sonuna
        #    daima kare numarasi ekler ("AO0001.png"). Kirpilmazsa "ao"
        #    deseni ("ao" + ayirici) TUTMAZ ve harita atlanir -- olculdu.
        ad = re.sub(r"\d+$", "", p.stem.lower())
        for tur in SIRA:
            if tur in bulunan:
                continue
            if re.search(DESENLER[tur], ad):
                bulunan[tur] = p
                break
        else:
            artan.append(p)
    return bulunan, artan


def yukle(p: Path, mod: str = "RGB") -> Image.Image:
    im = Image.open(p)
    if im.mode == "I;16":
        im = im.point(lambda v: v * (1 / 257)).convert("L")
    return im.convert(mod)


def kare_ve_boyut(im: Image.Image, kenar: int) -> Image.Image:
    if im.width != im.height:
        print(f"    [!] kare degil ({im.width}x{im.height}) -- tiling bozulabilir")
    return im.resize((kenar, kenar), Image.LANCZOS)


def srgb_to_linear(im: Image.Image) -> Image.Image:
    lut = [int(round((((v / 255) / 12.92) if v / 255 <= 0.04045
                      else ((v / 255 + 0.055) / 1.055) ** 2.4) * 255))
           for v in range(256)]
    return im.point(lut * len(im.getbands()))


def normal_saglik(im: Image.Image, maske: Image.Image | None = None):
    """Ortalama R,G,B (0-1) ve ortalama |N| dondurur.

    Dogru bir tangent-space normal haritasinda R~0.5, G~0.5, B yuksek ve
    n = 2v-1 vektorunun boyu ~1.0'dir. |N| 1'den belirgin sapiyorsa dosya
    yanlis renk uzayindadir (sRGB olarak yazilip ham okunmustur).
    """
    import numpy as np
    from PIL import ImageFilter

    N = 256                                     # olcum cozunurlugu
    v = np.asarray(im.resize((N, N), Image.LANCZOS), dtype=np.float32) / 255.0
    n = v * 2.0 - 1.0
    boy = np.sqrt((n ** 2).sum(axis=2))
    if maske is not None:
        # !! MASKEYI TAM COZUNURLUKTE ASINDIR, kucultmeden SONRA degil.
        #    Kenar pikselleri antialiasing yuzunden yuzey normalini arka
        #    planla (0,0,0) harmanlar ve vektoru kisaltir; bunlar olcumden
        #    cikarilmali. Ama 128 px'e kucultup asindirirsan cubuk zaten
        #    ~3 px kalir, asinma her seyi siler, orneklem bosalir ve olcum
        #    sessizce maskesiz haline doner -- yasandi.
        ic = maske.filter(ImageFilter.MinFilter(5)).resize((N, N), Image.NEAREST)
        m = np.asarray(ic) >= 128
        if m.sum() >= 256:
            boy, v = boy[m], v[m]
        else:
            print(f"    [!] asindirilmis maske cok kucuk ({int(m.sum())} px) -- "
                  f"olcum tum goruntude yapiliyor, sonuc yaniltici olabilir")
    return (float(v[..., 0].mean()), float(v[..., 1].mean()),
            float(v[..., 2].mean()), float(boy.mean()))


def normal_duzelt(im: Image.Image, maske: Image.Image | None = None):
    """Ham mi sRGB->linear mi -- |N|'i 1.0'a yaklastirani SECER (olcerek).

    !! OLCUMU KATI BOLGEYLE SINIRLA -- YASANDI: cutout dokusunda goruntunun
       %71'i DELIKTIR ve delikte normal (0,0,0)'dir. Tum goruntu uzerinden
       alinan ortalamayi delikler belirler; olcum "ham"i secti (0.920 vs
       0.301) oysa KATI bolgede dogru olan sRGB->linear idi. Yanlis renk
       uzayi hata vermez, sadece yanlis aydinlatir.
    """
    aday = [("ham", im), ("sRGB->linear", srgb_to_linear(im))]
    puanli = []
    for ad, k in aday:
        *_, boy = normal_saglik(k, maske)
        puanli.append((abs(boy - 1.0), ad, k, boy))
    puanli.sort(key=lambda t: t[0])
    _, ad, secilen, boy = puanli[0]
    diger = [p for p in puanli if p[1] != ad][0]
    print(f"    |N| olcumu: {ad}={boy:.3f}  {diger[1]}={diger[3]:.3f}  -> {ad}")
    if abs(boy - 1.0) > 0.15:
        print(f"    [!] |N|={boy:.3f}, 1.0'dan uzak. Normal haritasi tangent-space "
              f"ve 0-1 aralikta mi kontrol et.")
    return secilen, ad


def yaz(im: Image.Image, hedef: Path, fourcc: str) -> None:
    veri, mip = dxt_dds(im.convert("RGBA"), fourcc)
    hedef.write_bytes(veri)
    beklenen = int(math.log2(min(im.size))) - 1
    isaret = "OK" if mip == beklenen else f"!! beklenen {beklenen}"
    print(f"    -> {hedef.name}  {im.width}x{im.height} {fourcc}  "
          f"mip={mip} ({isaret})  {len(veri):,} bayt")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("girdi", type=Path, help="bake edilmis haritalarin klasoru")
    ap.add_argument("--ad", required=True, help="GTA doku taban adi (orn. mtk_kaldirim)")
    ap.add_argument("--cikti", type=Path, required=True)
    ap.add_argument("--boyut", type=int, default=512,
                    help="cikti kenari (vanilla medyani 512; 1024 da yaygin)")
    ap.add_argument("--pxm", action="store_true",
                    help="height haritasini da yaz (_pxm parallax shader'lari icin)")
    ap.add_argument("--yesil-koru", action="store_true",
                    help="normal'in YESIL kanalini cevirme (asagiya bak: DX/GL notu)")
    ap.add_argument("--ao-gucu", type=float, default=1.0,
                    help="AO'nun diffuse'a karisma orani (0=kapali, 1=tam)")
    ap.add_argument("--cutout", action="store_true",
                    help="alfayi ikililestir (cit/izgara/yaprak -- render bucket 3)")
    ap.add_argument("--esik", type=int, default=128,
                    help="--cutout esigi (varsayilan 128)")
    a = ap.parse_args()

    if a.boyut & (a.boyut - 1):
        sys.exit(f"--boyut 2'nin kuvveti olmali: {a.boyut}")
    if not a.girdi.is_dir():
        sys.exit(f"klasor yok: {a.girdi}")
    a.cikti.mkdir(parents=True, exist_ok=True)

    h, artan = bul(a.girdi)
    if not h:
        sys.exit(f"{a.girdi} icinde taninan harita yok")
    print(f"[bulunan] " + "  ".join(f"{k}={v.name}" for k, v in sorted(h.items())))
    if artan:
        print("[!] ESLESMEYEN dosyalar (kullanilmadi -- adlarini kontrol et):")
        for p in artan:
            print(f"      {p.name}")
    print()

    if "basecolor" not in h:
        sys.exit("base color YOK -- diffuse uretilemez")
    if "metallic" in h:
        print("[!] metallic haritasi bulundu ama GTA'da metallic SAMPLER YOK "
              "(249 shader'da 0 adet).\n"
              "    Metal gorunumu shader skalerlerinden gelir:\n"
              "      specularIntensityMult yukselt (1 -> 2.5+)\n"
              "      specularFalloffMult   yukselt (100 -> 250+, keskin highlight)\n"
              "      specularFresnel       0.95+\n")

    # ---- DIFFUSE = base color (x AO) [+ alfa] ----------------------------
    print("[diffuse]")
    diff = kare_ve_boyut(yukle(h["basecolor"]), a.boyut)
    if "ao" in h and a.ao_gucu > 0:
        ao = kare_ve_boyut(yukle(h["ao"], "L"), a.boyut)
        if a.ao_gucu < 1.0:
            ao = ao.point(lambda v: int(255 - (255 - v) * a.ao_gucu))
        diff = ImageChops.multiply(diff, Image.merge("RGB", (ao, ao, ao)))
        print(f"    AO diffuse'a carpildi (guc={a.ao_gucu}) -- GTA'da AO sampler yok")

    # Alfa ayri dosyadan ya da base color'in kendi alfa kanalindan gelebilir.
    alfa = None
    if "alpha" in h:
        alfa = kare_ve_boyut(yukle(h["alpha"], "L"), a.boyut)
        print(f"    alfa: {h['alpha'].name}")
    else:
        ham = Image.open(h["basecolor"])
        if ham.mode in ("RGBA", "LA") and ham.getchannel("A").getextrema()[0] < 255:
            alfa = kare_ve_boyut(ham.convert("RGBA").getchannel("A").convert("L"), a.boyut)
            print("    alfa: base color'in kendi alfa kanali")

    if alfa is not None:
        import numpy as np
        lo, hi = alfa.getextrema()
        av = np.asarray(alfa.resize((128, 128), Image.LANCZOS))
        orta = float(((av > 24) & (av < 231)).mean() * 100)
        print(f"    alfa araligi {lo}-{hi}, ara ton orani %{orta:.1f}")
        if a.cutout:
            alfa = alfa.point(lambda v: 255 if v >= a.esik else 0)
            print(f"    cutout: alfa {a.esik} esiginden ikililestirildi")
            veri, mip, olcumler = dxt_dds_kapsamli(diff, alfa, a.esik)
            hedef = a.cikti / f"{a.ad}.dds"
            hedef.write_bytes(veri)
            print(f"    -> {hedef.name}  {a.boyut}x{a.boyut} DXT5  mip={mip}  "
                  f"{len(veri):,} bayt")
            print("    kapsam koruyan mip zinciri (duz kucultmede izgara "
                  "uzakta KAYBOLUYOR):")
            t0 = olcumler[0][1]
            for kenar, kap in olcumler:
                print(f"      {kenar:4d}px  %{kap * 100:5.2f}  "
                      f"({(kap - t0) * 100:+.2f} puan)")
            # !! HUKMU EN KUCUK MIP'LERE BAKARAK VERME. 4x4'te 16 piksel
            #    vardir, kapsam ancak 1/16 = 6.25 puan adimlarla ayarlanabilir;
            #    oradaki sapma algoritmanin degil NICEMLEMENIN tabanidir.
            anlamli = [(kenar, k) for kenar, k in olcumler if kenar >= 16]
            sapma = max(abs(k - t0) for _, k in anlamli)
            kuyruk = max((abs(k - t0) for kenar, k in olcumler if kenar < 16),
                         default=0.0)
            print(f"    maks sapma (>=16px) {sapma * 100:.2f} puan "
                  f"{'OK' if sapma < 0.08 else '!! yuksek'}")
            if kuyruk:
                print(f"    son iki seviye {kuyruk * 100:.2f} puan -- 4x4'te "
                      f"nicemleme adimi zaten 6.25 puan, normal")
        else:
            yaz(Image.merge("RGBA", (*diff.split(), alfa)),
                a.cikti / f"{a.ad}.dds", "DXT5")
        print("    !! RENDER BUCKET: Sollumz bucket'i SHADER'a gore secer.\n"
              "       cutout_fence / cutout_fence_normal -> 3 (Cutout) DOGRU.\n"
              "       normal_spec birakirsan bucket 0 (Opaque) kalir, alfa\n"
              "       CALISMAZ ve HATA DA VERMEZ -- elle 3'e cekmen gerekir.")
    else:
        yaz(diff, a.cikti / f"{a.ad}.dds", "DXT1")

    # ---- SPEC = 1 - roughness -------------------------------------------
    if "roughness" in h:
        print("[spec]  roughness TERS CEVRILIYOR (GTA specular is akisi)")
        rough = kare_ve_boyut(yukle(h["roughness"], "L"), a.boyut)
        spec = ImageChops.invert(rough)
        yaz(Image.merge("RGB", (spec, spec, spec)), a.cikti / f"{a.ad}_s.dds", "DXT1")
        print("    not: shader'da specMapIntMask=1,0,0 -> yalniz R kanali okunur")
    else:
        print("[spec]  roughness haritasi yok -- atlandi")

    # ---- NORMAL ----------------------------------------------------------
    if "normal" in h:
        print("[normal]")
        nrm = kare_ve_boyut(yukle(h["normal"]), a.boyut)
        # alfa varsa renk-uzayi olcumu YALNIZ katı bolgede yapilir
        nrm, _ = normal_duzelt(nrm, alfa)
        if not a.yesil_koru:
            r, g, b = nrm.split()
            nrm = Image.merge("RGB", (r, ImageChops.invert(g), b))
            print("    yesil kanal cevrildi (DirectX yonu). Oyunda kabartma TERS "
                  "gorunuyorsa --yesil-koru ile tekrar uret.")
        yaz(nrm, a.cikti / f"{a.ad}_n.dds", "DXT1")
    else:
        print("[normal] yok -- atlandi")

    # ---- HEIGHT (yalniz _pxm shader'lari) --------------------------------
    if a.pxm:
        if "height" in h:
            print("[height]")
            hh = kare_ve_boyut(yukle(h["height"], "L"), a.boyut)
            yaz(Image.merge("RGB", (hh, hh, hh)), a.cikti / f"{a.ad}_h.dds", "DXT1")
            print("    _pxm shader'inda heightScale VARSAYILANI 0.03 = 3 cm.\n"
                  "    Gercek displacement DEGIL. Derin kabartmayi normal'e yukle.")
        else:
            print("[height] --pxm verildi ama displacement/height haritasi yok")
    elif "height" in h:
        print("[height] bulundu ama --pxm verilmedi -- yazilmadi "
              "(duz shader'da height sampler yoktur)")

    print(f"\n[bitti] {a.cikti}")
    print("\nSIRADAKI ADIM -- Sollumz shader slotlari:")
    if a.cutout:
        # cutout_fence_normal'in SpecSampler'i YOKTUR (olculdu: 2 doku).
        print("  shader: cutout_fence_normal   (vanilla 117 kullanim, 117'si bucket 3)")
        print("  Base Color  <- {0}.dds   (RGB + ikili alfa)".format(a.ad))
        print("  Normal      <- {0}_n.dds".format(a.ad))
        if "roughness" in h:
            print("  !! {0}_s.dds URETILDI AMA cutout_fence_normal'da SpecSampler YOK."
                  .format(a.ad))
            print("     Parlaklik skalerlerden gelir: specularIntensityMult=0.4")
            print("     specularFalloffMult=20  specularFresnel=0.9  bumpiness=2")
            print("     Spec haritasi sart ise normal_spec'e gec ve bucket'i")
            print("     ELLE 3 (Cutout) yap -- yoksa alfa sessizce calismaz.")
    else:
        print("  Base Color  <- {0}.dds".format(a.ad))
        print("  'Roughness' <- {0}_s.dds   !! ALAN ADI YANILTICI: specular girer"
              .format(a.ad))
        print("  Normal      <- {0}_n.dds".format(a.ad))
        if a.pxm:
            print("  Height      <- {0}_h.dds  (shader: normal_spec_pxm)".format(a.ad))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
