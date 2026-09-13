#!/usr/bin/env python3
"""make_dds.py — partikul sprite'i icin DXT5 + mip zincirli DDS uretir.

NEDEN ELLE: Blender DDS YAZAMAZ (128 baytlik baslik elle yazilir; Blender
pikselleri alttan uste, DDS ustten alta tutar).
SURUM NOTU (olculdu 2026-08-23): Sollumz 2.9.0'da .ytd export VAR
(bpy.ops.sollumz.export_ytd); eski 'Sollumz .ytd uretemez' notu eskidi.
DDS uretimi yine buradan gecer.

⛔ SIKISTIRILMAMIS FORMAT KULLANMA. Bu betigin ilk hali A8R8G8B8 (tek mip)
   yaziyordu ve gerekcesi "GTA sikistirilmamisi da kabul eder" VARSAYIMIYDI.
   Sonra olculdu: `core.ypt` icindeki 107 gomulu partikul dokusunun
   TAMAMI DXT sikistirilmis (DXT5 75 · DXT1 32), mip seviyesi 4-9.
   Sikistirilmamis ya da tek mip'li ORNEK YOK. Bu yuzden varsayilan artik
   DXT5 + mip zinciri.

⚠ DDS satirlari USTTEN ALTA yazilir (Blender pikselleri alttan uste verir);
  burada dogrudan urettigimiz icin sorun yok, ama Blender'dan aktarirken
  ters cevirmek gerekir.

Uretilen desenler TEKNIK PRIMITIFTIR (yumusak radyal maske), sanat degil --
gercek gorsel gerektiginde kullanici kendi dokusunu koyar.

Kullanim:
  python make_dds.py cikti.dds --desen yumusak --boyut 128
  python make_dds.py cikti.dds --desen halka  --boyut 128 --ic 0.45
  python make_dds.py cikti.dds --format A8R8G8B8      # eski davranis (onerilmez)
"""
from __future__ import annotations

import argparse
import io
import math
import struct
import sys

from PIL import Image

DDSD_CAPS, DDSD_HEIGHT, DDSD_WIDTH, DDSD_PIXELFORMAT = 0x1, 0x2, 0x4, 0x1000
DDSD_PITCH, DDSD_MIPMAPCOUNT, DDSD_LINEARSIZE = 0x8, 0x20000, 0x80000
DDPF_ALPHAPIXELS, DDPF_FOURCC, DDPF_RGB = 0x1, 0x4, 0x40
DDSCAPS_COMPLEX, DDSCAPS_TEXTURE, DDSCAPS_MIPMAP = 0x8, 0x1000, 0x400

# ⛔ MIP ZINCIRI 4x4'E KADAR INER. DXT blogu 4x4'tur, alti anlamsiz.
#    Olculdu: vanilla partikul dokularinin mip sayisi boyutla tam olarak
#    log2(kenar)-1 gidiyor -- 128x128 -> 6, 256x256 -> 7, 512x512 -> 8,
#    1024x1024 -> 9. Zinciri erken kesmek dokunun uzakta yanlis
#    orneklenmesine yol acar.
MIN_MIP = 4


def maske(gen: int, yuk: int, desen: str, ic: float) -> Image.Image:
    """RGBA: renk BEYAZ, sekil ALFA kanalinda.

    Partikul dokulari gri/beyaz maskedir: rengi motor verir (particle
    rule'un ptxu_Colour keyframe'i). Doku renkli yapilirsa tint uzerine
    biner ve kontrol kaybolur.
    """
    im = Image.new("RGBA", (gen, yuk))
    px = im.load()
    mx, my = (gen - 1) / 2.0, (yuk - 1) / 2.0
    yaricap = min(mx, my)
    for y in range(yuk):
        for x in range(gen):
            d = math.hypot(x - mx, y - my) / yaricap      # 0 merkez, 1 kenar
            if desen == "yumusak":
                a = max(0.0, 1.0 - d)
                a = a * a * (3 - 2 * a)                   # smoothstep
            elif desen == "halka":
                a = max(0.0, 1.0 - abs(d - ic) / max(ic, 1e-6))
                a = a * a
                if d > 1.0:
                    a = 0.0
            elif desen == "sert":
                a = 1.0 if d <= 1.0 else 0.0
            else:
                sys.exit(f"bilinmeyen desen: {desen}")
            px[x, y] = (255, 255, 255, int(round(max(0.0, min(1.0, a)) * 255)))
    return im


def dxt_govde(im: Image.Image, fourcc: str) -> bytes:
    """Tek seviyeyi DXT'ye sikistirir, 128 baytlik DDS basligini atar."""
    b = io.BytesIO()
    im.save(b, format="DDS", pixel_format=fourcc)
    return b.getvalue()[128:]


def dxt_dds(taban: Image.Image, fourcc: str = "DXT5") -> tuple[bytes, int]:
    """Mip zincirli DXT DDS uretir -> (bayt, mip_sayisi).

    ⛔ DXT1 = 8 bayt/blok, DXT5 = 16. Blok boyutu basliktaki
    dwPitchOrLinearSize alanina girer; yanlis yazilirsa mip zinciri
    kayar ve doku bozuk orneklenir."""
    seviyeler, im = [], taban
    while im.width >= MIN_MIP and im.height >= MIN_MIP:
        seviyeler.append(dxt_govde(im, fourcc))
        if im.width == MIN_MIP or im.height == MIN_MIP:
            break
        im = im.resize((max(MIN_MIP, im.width // 2),
                        max(MIN_MIP, im.height // 2)), Image.LANCZOS)

    gen, yuk = taban.width, taban.height
    bpb = 8 if fourcc == "DXT1" else 16
    blok = max(1, (gen + 3) // 4) * max(1, (yuk + 3) // 4) * bpb
    bayrak = (DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT
              | DDSD_LINEARSIZE | DDSD_MIPMAPCOUNT)
    h = struct.pack("<7I", 124, bayrak, yuk, gen, blok, 0, len(seviyeler))
    h += b"\x00" * 44                                              # dwReserved1[11]
    h += (struct.pack("<2I", 32, DDPF_FOURCC) + fourcc.encode("ascii")
          + struct.pack("<5I", 0, 0, 0, 0, 0))
    h += struct.pack("<5I", DDSCAPS_TEXTURE | DDSCAPS_MIPMAP | DDSCAPS_COMPLEX,
                     0, 0, 0, 0)
    return b"DDS " + h + b"".join(seviyeler), len(seviyeler)


def a8r8g8b8_dds(taban: Image.Image) -> tuple[bytes, int]:
    """Sikistirilmamis BGRA, tek mip. Vanilla'da ornegi YOK -- yalniz
    karsilastirma/teshis icin birakildi."""
    gen, yuk = taban.width, taban.height
    bayrak = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_PITCH
    h = struct.pack("<7I", 124, bayrak, yuk, gen, gen * 4, 0, 0)
    h += b"\x00" * 44
    h += struct.pack("<8I", 32, DDPF_ALPHAPIXELS | DDPF_RGB, 0, 32,
                     0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    h += struct.pack("<5I", DDSCAPS_TEXTURE, 0, 0, 0, 0)
    px = taban.load()
    veri = bytearray()
    for y in range(yuk):
        for x in range(gen):
            r, g, b, a = px[x, y]
            veri += bytes((b, g, r, a))
    return b"DDS " + h + bytes(veri), 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cikti")
    ap.add_argument("--desen", default="yumusak", choices=["yumusak", "halka", "sert"])
    ap.add_argument("--boyut", type=int, default=128)
    ap.add_argument("--ic", type=float, default=0.5, help="halka deseni: merkez yaricapi")
    ap.add_argument("--format", default="DXT5", choices=["DXT5", "DXT1", "A8R8G8B8"],
                    help="DXT5 varsayilan; A8R8G8B8'in vanilla'da ORNEGI YOK")
    ap.add_argument("--kaynak", default=None,
                    help="hazir PNG'den uret (desen/boyut yok sayilir). "
                         "Sprite sheet'ler icin bu kullanilir.")
    a = ap.parse_args()

    if a.kaynak:
        # ⛔ Kaynak gorsel GRI MASKE olmali (siyah zemin, beyaz-gri sekil).
        #    Vanilla'daki animasyon sheet'leri de boyle -- olculdu
        #    (ptfx_smoke_billow_anim_rgba, ptfx_water_splashes_sheet).
        taban = Image.open(a.kaynak).convert("RGBA")
        for ad, v in (("genislik", taban.width), ("yukseklik", taban.height)):
            if v & (v - 1):
                sys.exit(f"{ad} 2'nin kuvveti olmali: {v}")
        if taban.getextrema()[3][1] == 0:
            sys.exit("kaynakta alfa yok -- sekil alfa kanalinda olmali")
    else:
        if a.boyut & (a.boyut - 1):
            sys.exit("boyut 2'nin kuvveti olmali (64/128/256...)")
        taban = maske(a.boyut, a.boyut, a.desen, a.ic)
    veri, mip = (a8r8g8b8_dds(taban) if a.format == "A8R8G8B8"
                 else dxt_dds(taban, a.format))
    with open(a.cikti, "wb") as f:
        f.write(veri)
    kaynak_bilgi = a.kaynak if a.kaynak else f"desen={a.desen}"
    print(f"[+] {a.cikti}  {taban.width}x{taban.height} {a.format}  "
          f"mip={mip}  {len(veri):,} bayt  {kaynak_bilgi}")
    if a.format != "DXT5":
        print("[!] UYARI: vanilla'daki 107 partikul dokusunun tamami DXT. "
              "Sikistirilmamis doku oyunda reddedilebilir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
