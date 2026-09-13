#!/usr/bin/env python3
"""ptfx_sheet.py — GTA partikulu icin ANIMASYONLU sprite sayfasi (flipbook).

NEDEN VAR: `build_custom_ptfx.py` `AnimateTexture` davranisini zaten
yaziyor (`--sheet KARE`, `--animhiz`) ama besleyecek SAYFA yoktu; uretilen
efektler tek kare (`--sheet 1`) statik sprite kullaniyordu.

⛔ VANILLA OLCUMU (core.ypt, 1736 particle rule): kurallarin **%45'i**
`ParticleBehaviourAnimateTexture` tasiyor. Doku adlari da bunu soyluyor:
`ptfx_smoke_billow_anim_rgba` 1024x1024, `_explosion_fireball_rgba`
2048x1024, `ptfx_fire_v2` 1024x2048, `ptfx_cig_smoke_sheet` 256x256.
Yani "guzel duran" partikulun sirri cozunurluk degil, parcacigin omru
boyunca DEGISEN bir doku oynatmasidir. Tek kare sprite omur boyunca ayni
donuk lekeyi gosterir.

⛔ IZGARA KARE OLMALI: sutun = satir = sqrt(kare). `build_custom_ptfx.py`
`UnknownC4` alanina KARE SAYISI - 1 yazar. Gecerli kare sayilari:
4 (2x2), 16 (4x4), 36 (6x6), 64 (8x8). Kareler soldan saga, yukaridan
asagiya dizilir.

Kullanim:
  python ptfx_sheet.py duman cikti.png --kare 36 --coz 1024
  python ptfx_sheet.py --liste
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np

try:
    from PIL import Image
except ImportError:
    print("PIL gerekli: pip install pillow", file=sys.stderr)
    raise


# ------------------------------------------------------------- yardimcilar

def _rng(tohum):
    return np.random.default_rng(tohum)


def _bulanik(a, r):
    """Ayrilabilir kutu bulanikligi, 3 gecis (gauss yaklasimi).

    ⛔ Cikti sekli girdiyle AYNI kalir; `np.resize` ile duzeltme YAPILMAZ
    (o mekansal yeniden boyutlandirma degil, veri tekrari).
    """
    if r < 1:
        return a
    out = a.astype(np.float32)
    k = 2 * int(r) + 1
    for _ in range(3):
        for eks in (0, 1):
            dolgu = [(0, 0), (0, 0)]
            dolgu[eks] = (int(r), int(r))
            p = np.pad(out, dolgu, mode='edge')
            c = np.cumsum(p, axis=eks, dtype=np.float32)
            sifir = np.zeros_like(np.take(c, [0], axis=eks))
            c = np.concatenate([sifir, c], axis=eks)
            ust = np.take(c, np.arange(k, k + out.shape[eks]), axis=eks)
            alt = np.take(c, np.arange(0, out.shape[eks]), axis=eks)
            out = (ust - alt) / float(k)
    return out


def _deger_gurultu(n, hucre, rng):
    """Tek oktav deger gurultusu: kaba izgara + bilineer buyutme."""
    g = max(2, int(hucre))
    kaba = rng.random((g + 1, g + 1)).astype(np.float32)
    yi = np.linspace(0, g, n, endpoint=False)
    xi = np.linspace(0, g, n, endpoint=False)
    y0 = np.floor(yi).astype(np.int32); x0 = np.floor(xi).astype(np.int32)
    fy = (yi - y0)[:, None]; fx = (xi - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)   # smoothstep
    a = kaba[y0][:, x0]; b = kaba[y0][:, x0 + 1]
    c = kaba[y0 + 1][:, x0]; d = kaba[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def _fbm(n, oktav, hucre, rng, kalicilik=0.55):
    """Cok oktavli deger gurultusu (0..1)."""
    top = np.zeros((n, n), np.float32)
    genlik = 1.0
    toplam = 0.0
    for o in range(oktav):
        top += genlik * _deger_gurultu(n, hucre * (2 ** o), rng)
        toplam += genlik
        genlik *= kalicilik
    return top / max(toplam, 1e-6)


def _radyal(n, merkez=(0.5, 0.5)):
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    return np.sqrt(((x / n) - merkez[0]) ** 2 + ((y / n) - merkez[1]) ** 2) * 2.0


def _olcekle(a, yeni):
    """Alan ortalamali yeniden boyutlandirma."""
    n = a.shape[0]
    if n == yeni:
        return a
    yi = (np.arange(yeni) + 0.5) * (n / float(yeni)) - 0.5
    i0 = np.clip(np.floor(yi).astype(np.int32), 0, n - 1)
    i1 = np.clip(i0 + 1, 0, n - 1)
    f = np.clip(yi - i0, 0, 1)
    ara = a[i0] * (1 - f[:, None]) + a[i1] * f[:, None]
    return ara[:, i0] * (1 - f[None, :]) + ara[:, i1] * f[None, :]


# ------------------------------------------------------------- kare uretici
# Her uretici: (kare_indeksi, kare_sayisi, cozunurluk, rng) -> (rgb, alfa)
# t = 0..1 parcacigin omru boyunca ilerleme.

def k_duman(i, n, c, rng, sicak=False):
    """Kivrilarak buyuyen ve dagilan duman pufu.

    ⛔ YOGUNLUGU GURULTUYU EZEREK ARTIRMA. Ilk duzeltmede carpan
    `0.86 + 0.34*kabar` yapildi; aralik neredeyse sabit oldugu icin doluluk
    yukseldi ama YAPI dumduz oldu -- gri zemine bindirilince vanilla'nin
    ince kivrimli dumaninin yaninda "bulanik bir top" gibi duruyordu.
    Yogunluk MASKEDEN ve esikten gelir, gurultunun genligi tam kalir.

    ⛔ TEK OKTAV KIVRIM VERMEZ. Vanilla dumaninda iki olcek vardir:
    kaba kabarcik + ince filament. Ikinci, yuksek frekansli katman
    eklenmeden duman "duman" gibi okunmuyor.
    """
    t = i / max(n - 1, 1)
    d1 = _fbm(c, 4, 3, _rng(1000 + i * 7), 0.58)      # kaba kabarcik
    d2 = _fbm(c, 3, 9, _rng(1500 + i * 7), 0.50)      # ince kivrim
    d = 0.66 * d1 + 0.34 * d2
    # ⛔ SILUET DAIRE OLMAMALI. Maske duz bir radyal disk olunca ve
    # carpanda sabit bir taban kalinca (`0.10 + ...`), gurultunun bos
    # oldugu yerlerde bile soluk bir DISK goruluyor -- gri zemine
    # bindirildiginde daire kenari cikiplak okunuyor. Vanilla dumaninin
    # silueti duzensizdir. Cozum: yaricapi gurultuyle bozmak ve tabani
    # tamamen kaldirmak.
    r = _radyal(c) - 0.13 * (d1 - 0.5)           # siluet gurultuyle bozulur
    kenar = 0.50 + 0.44 * t                      # puf yaricapi
    yumusak = 0.20 + 0.30 * t                    # kenar yumusakligi
    maske = np.clip((kenar - r) / max(yumusak, 1e-3), 0.0, 1.0)
    # ⛔ EROZYON ESIGI ZAMANLA YUKSELIR, DUSMEZ. Ilk surumde
    # `esik = 0.44 - 0.24*t` yaziliydi: gec karelerde esik o kadar
    # dusuyordu ki gurultunun TAMAMI geciyor, modulasyon bitiyor ve
    # geriye ciplak radyal maske -- yani duz bir DISK -- kaliyordu.
    # Gri zemine bindirilince son iki kare belirgin bir daire gibi
    # okunuyordu. Gercek duman dagilirken PARCALANIR: esik yukselmeli.
    esik = 0.34 + 0.26 * t
    kabar = np.clip((d - esik) / 0.24, 0.0, 1.0)
    alfa = maske * np.clip(1.35 * kabar - 0.03, 0.0, 1.0)
    alfa *= (1.0 - t) ** 0.40                    # omur boyunca sonme
    alfa = _bulanik(alfa, 1 + int(c * 0.004))
    if sicak:
        ic = np.clip((0.30 * (1 - t) - r) / 0.22, 0.0, 1.0)
        rgb = np.dstack([np.clip(0.35 + 1.4 * ic, 0, 1),
                         np.clip(0.28 + 0.9 * ic, 0, 1),
                         np.clip(0.24 + 0.35 * ic, 0, 1)]).astype(np.float32)
    else:
        # Koyu govde + parlak tepeler: hacim hissi buradan gelir.
        v = 0.30 + 0.58 * kabar
        rgb = np.dstack([v, v, v * 1.02]).astype(np.float32)
    return rgb, alfa

def k_ates(i, n, c, rng):
    """Yukari yalayan ates dilleri.

    ⛔ ILK SURUM `k_duman(sicak=True)` cagiriyordu: radyal sicak bir leke
    cikti, atese HIC benzemedi. Ates dumanin renkli hali DEGILDIR - dumani
    tanimlayan sey dagilma, atesi tanimlayan sey YUKARI YUKSELEN dillerdir.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    u = xx / c
    v = 1.0 - yy / c                       # 0 = taban, 1 = tepe

    d = _fbm(c, 4, 5, _rng(2500), 0.55)    # 3 -> 5 hucre: daha ince diller
    kay = int((0.55 * t) * c) % max(c, 1)
    d = np.roll(d, -kay, axis=0)           # alev tirmanir

    # ⛔ ILK SURUM HUCREYE SIGMIYORDU: genislik 0.42 ve tabanda 0.2'lik
    # sabit zarf yuzunden kare kenarina 0.44 alfayla degiyordu (olculdu;
    # `duman`/`kivilcim` 0.00 ile temizdi). Flipbook karesi kenara degerse
    # oyunda sprite quad sinirinda SERT KESIK gorunur. Genislik kisildi ve
    # tabana yumusak bir baslangic kondu.
    genis = 0.32 * (1.0 - 0.70 * v)
    orta = 0.5 + 0.05 * np.sin(v * 7.0 + t * 5.0)
    koni = np.clip(1.0 - np.abs(u - orta) / np.maximum(genis, 1e-3), 0, 1)

    boy = 0.26 + 0.58 * min(t * 1.8, 1.0)
    taban = np.clip((v - 0.06) / 0.10, 0, 1)
    zarf = np.clip((boy - v) / 0.24, 0, 1) * taban

    kopma = np.clip((d - (0.30 + 0.42 * v)) / 0.20, 0, 1)
    alfa = koni * zarf * (0.35 + 0.65 * kopma)
    alfa *= (1.0 - t) ** 0.45
    alfa = _bulanik(alfa, 1)

    sic = np.clip(1.0 - v / max(boy, 1e-3), 0, 1) ** 0.8
    rgb = np.dstack([np.clip(0.55 + 0.85 * sic, 0, 1),
                     np.clip(0.16 + 0.78 * sic ** 1.5, 0, 1),
                     np.clip(0.05 + 0.55 * sic ** 4, 0, 1)]).astype(np.float32)
    return rgb, alfa


def _eski_k_alev_topu(i, n, c, rng):
    """Patlama: parlak cekirdek -> kabaran ates -> kararan duman.

    ⛔ ILK SURUM YAPISIZDI: tek radyal maske + tek gurultu katmani,
    sonuc "sonen kirmizi leke"ydi. 15 ailenin tablosunda gozle en zayif
    ucu buydu. Patlamayi patlama yapan sey KABARMADIR: birbirinden ayri,
    farkli hizda buyuyen loblar. Uc lob eklendi ve renk zaman icinde
    beyaz cekirdek -> turuncu -> koyu dumana KAYIYOR.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    u, v = xx / c - 0.5, yy / c - 0.5
    yari = 0.10 + 0.34 * (t ** 0.55)

    alfa = np.zeros((c, c), np.float32)
    for k in range(3):
        r2 = _rng(2600 + k * 7)
        aci = r2.random() * math.tau
        kac = (0.05 + 0.10 * r2.random()) * t
        lx, ly = math.cos(aci) * kac, math.sin(aci) * kac
        lr = yari * (0.62 + 0.30 * r2.random())
        mes = np.sqrt((u - lx) ** 2 + (v - ly) ** 2)
        alfa = np.maximum(alfa, np.clip((lr - mes) / (0.06 + 0.16 * t), 0, 1))

    d = _fbm(c, 4, 4, _rng(2650), 0.62)
    d = np.roll(d, -int(0.25 * t * c) % max(c, 1), axis=0)
    kabar = np.clip((d - (0.56 - 0.32 * t)) / 0.24, 0, 1)
    alfa = alfa * (0.34 + 0.66 * kabar) * (1.0 - t) ** 0.7
    alfa = _bulanik(alfa, 1 + int(c * 0.006))

    # ⛔ RENGI KANAL KANAL KURMA. Ilk iki denemede R/G/B ayri ayri
    # formulle yazildi; kanallar farkli hizlarda soninca cekirdek once
    # sonuk turuncu, sonra YESILIMSI cikti (gozle dogrulandi). Kanal
    # kesismesi boyle sessizce renk uydurur. Dogrusu tek bir SICAKLIK
    # alani kurup uc sabit renk arasinda interpolasyon yapmaktir:
    # duman -> ates -> beyaz cekirdek. Monotonluk boylece garanti.
    mes0 = np.sqrt(u * u + v * v)
    cek = np.clip((yari * 0.68 - mes0) / 0.09, 0, 1)
    sicak = np.clip(cek * (1.0 - t) ** 0.9 * 1.25
                    + (1.0 - t) ** 2.0 * 0.42, 0.0, 1.0)

    DUMAN = np.array([0.13, 0.120, 0.115], np.float32)
    ATES = np.array([1.00, 0.42, 0.09], np.float32)
    BEYAZ = np.array([1.00, 0.94, 0.74], np.float32)
    a1 = np.clip(sicak / 0.55, 0, 1)[..., None]
    a2 = np.clip((sicak - 0.55) / 0.45, 0, 1)[..., None]
    taban = DUMAN + (ATES - DUMAN) * a1
    rgb = (taban + (BEYAZ - taban) * a2).astype(np.float32)

    # ⛔ DOGRU RENK TEK BASINA YETMEZ - ALFA DA CEKIRDEKTE OLMALI.
    # Renk duman->ates->beyaz olarak duzeltildikten SONRA bile cekirdek
    # GRI gorunuyordu: oradaki alfa ~0.34 idi, arka plan icinden geciyordu;
    # kenarda loblar ust uste bindigi icin alfa yuksekti -> "gri merkez,
    # turuncu halka". Patlamanin merkezi en OPAK yeridir.
    alfa = np.clip(alfa + cek * (1.0 - t) ** 1.1 * 0.85, 0, 1)
    return rgb, alfa


def k_elektrik(i, n, c, rng):
    """Catallanan elektrik ark."""
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    rr = _rng(11000 + i * 17)
    yigin = [(0.5, 0.5, rr.random() * math.tau, 0.30, c * 0.010, 1)]
    while yigin:
        x0, y0, aci, uz, kal, derin = yigin.pop()
        px, py = x0, y0
        for _k in range(7):
            aci += (rr.random() - 0.5) * 1.1
            nx = px + math.cos(aci) * uz / 7.0
            ny = py + math.sin(aci) * uz / 7.0
            # ⛔ Ark serbest yurur ve catallanir; sinirlanmazsa kare
            # kenarina 0.98 alfayla dayanir. Hucre icinde TUTULUR.
            nx = min(max(nx, 0.12), 0.88)
            ny = min(max(ny, 0.12), 0.88)
            dx, dy = (nx - px) * c, (ny - py) * c
            L = max(math.hypot(dx, dy), 1e-6)
            sN = np.clip(((xx - px * c) * dx + (yy - py * c) * dy) / (L * L), 0, 1)
            mx = px * c + sN * dx
            my = py * c + sN * dy
            mes = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2)
            alfa = np.maximum(alfa, np.clip(1.0 - mes / max(kal, 1e-6), 0, 1))
            px, py = nx, ny
            if derin > 0 and rr.random() < 0.4:
                yigin.append((px, py, aci + (rr.random() - 0.5) * 2.0,
                              uz * 0.45, kal * 0.6, derin - 1))
    hale = _bulanik(alfa, max(1, int(c * 0.018))) * 0.55
    alfa = np.clip(alfa + hale, 0, 1) * (0.35 + 0.65 * abs(math.sin(t * math.pi * 3)))
    rgb = np.dstack([np.full((c, c), 0.72, np.float32),
                     np.full((c, c), 0.86, np.float32),
                     np.full((c, c), 1.0, np.float32)])
    return rgb.astype(np.float32), alfa


def k_kan(i, n, c, rng):
    """Kan sisi / sicrama."""
    t = i / max(n - 1, 1)
    rr = _rng(12000)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for _k in range(40):
        aci = rr.random() * math.tau
        hiz = 0.10 + 0.34 * rr.random() ** 1.6
        x = 0.5 + math.cos(aci) * hiz * t
        y = 0.5 + math.sin(aci) * hiz * t * 0.6 + 0.30 * t * t
        rad = c * (0.010 + 0.030 * rr.random()) * (1.0 - 0.3 * t)
        mes = np.sqrt((xx - x * c) ** 2 + (yy - y * c) ** 2)
        alfa = np.maximum(alfa, np.clip(1.0 - mes / max(rad, 1e-6), 0, 1))
    alfa *= (1.0 - t) ** 0.5
    alfa = _bulanik(alfa, 1)
    v = np.full((c, c), 1.0, np.float32)
    return np.dstack([v * 0.55, v * 0.06, v * 0.05]).astype(np.float32), alfa


def k_yaprak(i, n, c, rng):
    """Savrulan yapraklar: yassi, donen, yesil-kahve."""
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    renk = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(9):
        r2 = _rng(13000 + k)
        aci0 = r2.random() * math.tau
        hiz = 0.12 + 0.26 * r2.random()
        x = (0.5 + math.cos(aci0) * hiz * t) * c
        y = (0.5 + math.sin(aci0) * hiz * t * 0.5 + 0.30 * t) * c
        don = aci0 + t * (3.0 + 5.0 * r2.random())
        a2 = c * (0.030 + 0.022 * r2.random())
        b2 = a2 * (0.30 + 0.35 * abs(math.cos(don * 1.7)))
        dx = (xx - x) * math.cos(don) + (yy - y) * math.sin(don)
        dy = -(xx - x) * math.sin(don) + (yy - y) * math.cos(don)
        e = np.clip(1.0 - ((dx / a2) ** 2 + (dy / max(b2, 1e-6)) ** 2), 0, 1)
        alfa = np.maximum(alfa, (e > 0).astype(np.float32))
        renk = np.maximum(renk, e * r2.random())
    alfa *= (1.0 - t) ** 0.3
    alfa = _bulanik(alfa, 1)
    rgb = np.dstack([0.35 + 0.42 * renk, 0.42 + 0.24 * renk,
                     0.14 + 0.12 * renk]).astype(np.float32)
    return rgb, alfa


def k_toz(i, n, c, rng):
    """Ince taneli toz bulutu — dumandan daha kirik ve hizli dagilan."""
    t = i / max(n - 1, 1)
    d = _fbm(c, 5, 5, _rng(2000 + i * 11), 0.62)
    r = _radyal(c)
    maske = np.clip((0.34 + 0.60 * t - r) / (0.22 + 0.30 * t), 0.0, 1.0)
    kabar = np.clip((d - (0.68 - 0.34 * t)) / 0.22, 0.0, 1.0)
    alfa = maske * kabar * (1.0 - t) ** 1.3
    alfa = _bulanik(alfa, 1)
    v = 0.62 + 0.30 * kabar
    return np.dstack([v, v * 0.94, v * 0.84]).astype(np.float32), alfa


def k_buhar(i, n, c, rng):
    """Yukari surunen buhar tutami.

    ⛔ ILK SURUM COK SILIKTI: tek yumusak leke, agir bulaniklik ve
    0.75 carpani yuzunden oyunda neredeyse gorunmezdi. Buhari gorunur
    kilan sey opaklik degil YAPI: yukari uzayan, birbirinden ayrilan
    tutamlar. Yatay gurultu olcegi kisildi (tutam), dikey uzatildi,
    bulaniklik yariya indi.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    v = 1.0 - yy / c

    # dikey uzamis gurultu = tutam
    d = _fbm(c, 4, 6, _rng(3000), 0.58)
    d = _bulanik(d, max(1, int(c * 0.010)))
    kay = int(0.70 * t * c) % max(c, 1)
    d = np.roll(d, -kay, axis=0)

    genis = 0.30 + 0.34 * v + 0.22 * t
    koni = np.clip(1.0 - np.abs(xx / c - 0.5) / genis, 0, 1)
    boy = 0.42 + 0.56 * min(t * 1.6, 1.0)
    zarf = np.clip((boy - v) / 0.30, 0, 1) * np.clip(v / 0.05 + 0.15, 0, 1)

    tutam = np.clip((d - (0.40 + 0.16 * v)) / 0.24, 0, 1)
    alfa = koni * zarf * (0.30 + 0.70 * tutam)
    alfa *= (1.0 - t) ** 0.9
    alfa = _bulanik(alfa, 1 + int(c * 0.006))
    v2 = np.full((c, c), 0.93, np.float32)
    return np.dstack([v2, v2, v2 * 0.98]).astype(np.float32), alfa

def k_kivilcim(i, n, c, rng):
    """Merkezden disari firlayan, kisalan parlak cizgiler."""
    t = i / max(n - 1, 1)
    rr = _rng(4000)
    adet = 26
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(adet):
        aci = rr.random() * math.tau
        hiz = 0.20 + 0.34 * rr.random()
        uz = hiz * t
        bas = 0.5 + np.array([math.cos(aci), math.sin(aci)]) * max(uz - 0.06, 0.0)
        son = 0.5 + np.array([math.cos(aci), math.sin(aci)]) * uz
        px = np.array([bas[0], son[0]]) * c
        py = np.array([bas[1], son[1]]) * c
        dx, dy = px[1] - px[0], py[1] - py[0]
        uzn = max(math.hypot(dx, dy), 1e-6)
        # noktanin dogru parcasina uzakligi
        s = np.clip(((xx - px[0]) * dx + (yy - py[0]) * dy) / (uzn * uzn), 0, 1)
        mx = px[0] + s * dx; my = py[0] + s * dy
        mes = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2)
        kal = c * (0.010 + 0.008 * (1 - t))
        alfa = np.maximum(alfa, np.clip(1.0 - mes / kal, 0, 1))
    alfa *= (1.0 - t) ** 0.6
    alfa = _bulanik(alfa, 1)
    rgb = np.dstack([np.full((c, c), 1.0, np.float32),
                     np.full((c, c), 0.78 - 0.30 * t, np.float32),
                     np.full((c, c), 0.35 - 0.28 * t, np.float32)])
    return rgb.astype(np.float32), alfa


def k_sicrama(i, n, c, rng):
    """Su sicramasi: disari ve asagi giden damlalar."""
    t = i / max(n - 1, 1)
    rr = _rng(5000)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(34):
        aci = rr.random() * math.tau
        hiz = 0.16 + 0.30 * rr.random()
        x = 0.5 + math.cos(aci) * hiz * t
        y = 0.5 + math.sin(aci) * hiz * t * 0.55 + 0.34 * t * t   # yercekimi
        rad = c * (0.020 + 0.026 * rr.random()) * (1.0 - 0.4 * t)
        mes = np.sqrt((xx - x * c) ** 2 + (yy - y * c) ** 2)
        alfa = np.maximum(alfa, np.clip(1.0 - mes / max(rad, 1e-6), 0, 1))
    alfa *= (1.0 - t) ** 0.5
    alfa = _bulanik(alfa, 1)
    v = np.full((c, c), 0.86, np.float32)
    return np.dstack([v * 0.88, v * 0.94, v]).astype(np.float32), alfa


def k_kor(i, n, c, rng):
    """Yukari suzulen kor taneleri + hareket kuyrugu.

    ⛔ ILK SURUM COK SEYREKTI (doluluk %1): taneler nokta gibiydi.

    ⛔ IKINCI SURUM TERS TARAFA KACTI: 30 tane + her birine 0.030*c hale
    eklendi, taneler birbirine yapisti ve tek turuncu KUTLE oldu - tabloda
    "yaprak" gibi okunuyordu. Kor efektini kor yapan sey AYRI AYRI SECILEN
    parlak noktalardir. 14 taneye inildi, yaricap kisildi, hale yariya
    dusuruldu ve taneler baslangicta dagitildi (hepsi merkezden cikmiyor).
    """
    t = i / max(n - 1, 1)
    rr = _rng(6000 + i * 3)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(14):
        r2 = _rng(6100 + k)
        # baslangic dagilimi: hepsi ayni noktadan cikmaz
        bx = 0.5 + (r2.random() - 0.5) * 0.34
        by = 0.66 + (r2.random() - 0.5) * 0.20
        aci = r2.random() * math.tau
        hiz = 0.05 + 0.13 * r2.random()
        yuk = 0.16 + 0.16 * r2.random()

        def konum(tt):
            return (bx + math.cos(aci) * hiz * tt,
                    by + math.sin(aci) * hiz * tt * 0.5 - yuk * tt)

        x, y = konum(t)
        xg, yg = konum(max(t - 0.10, 0.0))
        dx, dy = (x - xg) * c, (y - yg) * c
        L = max(math.hypot(dx, dy), 1e-6)
        sN = np.clip(((xx - xg * c) * dx + (yy - yg * c) * dy) / (L * L), 0, 1)
        mes = np.sqrt((xx - (xg * c + sN * dx)) ** 2 + (yy - (yg * c + sN * dy)) ** 2)
        titre = 0.55 + 0.45 * rr.random()
        rad = c * 0.016 * titre
        alfa = np.maximum(alfa, np.clip(1.0 - mes / rad, 0, 1) ** 0.6 * titre)
    hale = _bulanik(alfa, max(1, int(c * 0.016))) * 0.38
    alfa = np.clip(alfa + hale, 0, 1) * (1.0 - t) ** 0.7
    rgb = np.dstack([np.full((c, c), 1.0, np.float32),
                     np.full((c, c), 0.50 + 0.32 * (1 - t), np.float32),
                     np.full((c, c), 0.12, np.float32)])
    return rgb.astype(np.float32), alfa

def k_sis(i, n, c, rng):
    """Yerde surunen sis tabakalari.

    ⛔ ILK SURUM `buhar` ile neredeyse AYNIYDI (ikisi de yumusak leke).
    Yatay tabakalanma eklendi.

    ⛔ IKINCI SURUM IKI BANTTAN IBARETTI: `sin(y * 9)` bu olcekte hucreye
    yalnizca ~2 gorunur bant sigdiriyordu ve sonuc "ust uste iki leke" gibi
    okunuyordu - sise benzemiyordu. Sis GENIS ve ALCAK olmalidir: hucreyi
    yatayda doldurur, dikeyde alt yariya toplanir, icinde ince tutamlar
    yan yana suzulur.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    u, v = xx / c, yy / c

    d = _fbm(c, 5, 3, _rng(4000), 0.62)
    d = np.roll(d, int(0.35 * t * c) % max(c, 1), axis=1)     # yatay suzulme
    ince = _fbm(c, 3, 9, _rng(4100), 0.50)
    ince = np.roll(ince, int(0.6 * t * c) % max(c, 1), axis=1)

    # yatayda genis, dikeyde alt yariya toplanmis
    yatay = np.clip(1.0 - np.abs(u - 0.5) / 0.52, 0, 1) ** 0.6
    dikey = np.clip((v - 0.24) / 0.22, 0, 1) * np.clip((0.96 - v) / 0.14, 0, 1)

    tutam = np.clip((0.55 * d + 0.45 * ince - 0.34) / 0.30, 0, 1)
    alfa = yatay * dikey * (0.22 + 0.62 * tutam)
    alfa *= (1.0 - abs(2 * t - 1) * 0.72)
    alfa = _bulanik(alfa, 2 + int(c * 0.016))
    g = np.full((c, c), 0.82, np.float32)
    return np.dstack([g * 0.97, g * 0.99, g]).astype(np.float32), alfa

def k_kabarcik(i, n, c, rng):
    """Yukselen kabarcik akisi.

    ⛔ ILK SURUM KALABALIKTI: 9 kabarcik ust uste binip okunmaz bir yumak
    yapiyordu. 3 buyuk kabarciga inildi.

    ⛔ IKINCI SURUM YIGILIYORDU: her kabarcigin fazi
    `tk = (t - gecikme) / (1 - gecikme)` ile NORMALIZE ediliyordu, yani
    gecikmeli baslasalar da HEPSI AYNI ANDA variyordu. Sonuc: son karelerde
    uc kabarcik yan yana ayni yukseklikte duruyordu - "yukselen kabarcik"
    degil "uc halka" gibi okunuyordu. Otomatik durgunluk kapisi bunu 20
    durgun kare olarak isaretledi, gozle de dogrulandi.

    Dogrusu SUREKLI AKIS: her kabarcik kendi fazini `% 1.0` ile cevirir,
    fazlar sabit ofsetlidir; her karede uc kabarcik FARKLI yukseklikte olur
    ve sayfa kendiliginden kusursuz donguye girer.

    ⛔ YARICAP HUCRE ORANIDIR. 0.085 yazdigimda kabarcik hucrenin
    yalnizca %8'i kadar kaliyordu - oyunda nokta gibi gorunur.
    """
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    parlak = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(3):
        r2 = _rng(8000 + k)
        x = 0.28 + 0.22 * k + 0.04 * (r2.random() - 0.5)
        tk = (t + k / 3.0) % 1.0                  # surekli akis, sabit faz
        # ⛔ MENZIL YARICAPI HESABA KATMALI: tanenin MERKEZI hucre icinde
        # kalsa bile yaricapi kadari disari tasar ve kare kenarinda sert
        # kesik olur. Kenar maskesi bunu yumusatir ama icerigi kirpar.
        rad = c * (0.15 + 0.04 * r2.random()) * (0.62 + 0.38 * tk)
        y = 0.76 - 0.52 * tk
        mes = np.sqrt((xx - x * c) ** 2 + (yy - y * c) ** 2)
        halka = np.clip(1.0 - np.abs(mes - rad) / (rad * 0.22), 0, 1)
        ic = np.clip(1.0 - mes / rad, 0, 1) * 0.16
        pmes = np.sqrt((xx - (x - 0.050) * c) ** 2 + (yy - (y - 0.050) * c) ** 2)
        p = np.clip(1.0 - pmes / (rad * 0.30), 0, 1)
        # dogus ve olum yumusak: dongude sicrama olmasin
        sonme = np.clip(tk / 0.12, 0, 1) * np.clip((1.0 - tk) / 0.18, 0, 1)
        sonme = float(sonme) * 0.85 + 0.15
        alfa = np.maximum(alfa, np.maximum(halka * 0.85, np.maximum(ic, p)) * sonme)
        parlak = np.maximum(parlak, p * sonme)
    alfa = _bulanik(alfa, 1)
    v = 0.70 + 0.30 * parlak
    return np.dstack([v * 0.88, v * 0.95, v]).astype(np.float32), alfa

def k_parca(i, n, c, rng):
    """Donerek savrulan kati parcalar (moloz/yaprak)."""
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(11):
        r2 = _rng(9000 + k)
        aci0 = r2.random() * math.tau
        # ⛔ MENZIL YARICAPI HESABA KATMALI: tanenin MERKEZI hucre
        # icinde kalsa bile yaricapi kadari disari tasar ve kare
        # kenarinda sert kesik olur. Kenar maskesi bunu yumusatir
        # ama icerigi kirpar - cozum menzili kaynakta kismaktir.
        hiz = 0.10 + 0.20 * r2.random()
        x = (0.5 + math.cos(aci0) * hiz * t) * c
        y = (0.5 + math.sin(aci0) * hiz * t + 0.14 * t * t) * c
        don = aci0 + t * (4.0 + 6.0 * r2.random())
        yari = c * (0.022 + 0.020 * r2.random())
        dx = (xx - x) * math.cos(don) + (yy - y) * math.sin(don)
        dy = -(xx - x) * math.sin(don) + (yy - y) * math.cos(don)
        parc = ((np.abs(dx) < yari) & (np.abs(dy) < yari * 0.42)).astype(np.float32)
        alfa = np.maximum(alfa, parc)
    alfa *= (1.0 - t) ** 0.35
    alfa = _bulanik(alfa, 1)
    v = np.full((c, c), 0.45, np.float32)
    return np.dstack([v, v * 0.86, v * 0.70]).astype(np.float32), alfa


def k_halka(i, n, c, rng):
    """Disari acilan sok dalgasi halkasi."""
    t = i / max(n - 1, 1)
    r = _radyal(c)
    yari = 0.06 + 0.86 * t
    kal = 0.10 + 0.16 * t
    alfa = np.clip(1.0 - np.abs(r - yari) / kal, 0, 1) ** 1.6
    alfa *= (1.0 - t) ** 1.1
    alfa = _bulanik(alfa, 1 + int(c * 0.006))
    v = np.full((c, c), 0.95, np.float32)
    return np.dstack([v, v * 0.95, v * 0.90]).astype(np.float32), alfa


# --------------------------------------------------- AYRI SILUETLI AILELER
# ⛔ Bu aileler "ayni seyin rengi degismis hali" OLMAMAK icin var. Olcut:
#    gri zemine bindirilip yan yana konunca hangisi oldugu SEKILDEN
#    anlasilmali. Renk tint'ten gelir, o yuzden RGB burada notr tutulur.

def _eski_k_yildiz(i, n, c, rng):
    """Keskin isinsal parlama -- elektrik arki / buyu carpmasi.

    ⛔ `alev_topu`nun YUMUSAK DISKINDEN ayrilmasi sart: ark carpmasi
       yumusak bir top degil, ince uzun DIKENLERI olan bir yildizdir.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    dx = (xx / c - 0.5) * 2.0
    dy = (yy / c - 0.5) * 2.0
    r = np.sqrt(dx * dx + dy * dy) + 1e-6
    aci = np.arctan2(dy, dx)
    # 6 ana + 6 ara diken; ara dikenler kisa
    diken = np.abs(np.cos(6.0 * aci)) ** 14.0 + 0.35 * np.abs(np.cos(6.0 * aci + 0.5236)) ** 22.0
    boy = 0.30 + 0.62 * t
    isin = np.clip(1.0 - r / boy, 0, 1) ** 2.2 * diken
    cekirdek = np.clip(1.0 - r / (0.11 * (1.0 - 0.55 * t)), 0, 1) ** 1.4
    alfa = np.clip(isin * 1.5 + cekirdek, 0, 1)
    alfa *= (1.0 - t) ** 1.5
    alfa = _bulanik(alfa, 1)
    v = np.clip(0.72 + 0.28 * cekirdek, 0, 1).astype(np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def k_sinek(i, n, c, rng):
    """Kucuk KOYU noktalar -- sinek/bocek surusu. Parlama YOK."""
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(16):
        r2 = _rng(31000 + k)
        aci = r2.random() * math.tau
        yari_yol = 0.10 + 0.22 * r2.random()
        # duzensiz gezinme: iki farkli frekansta salinim
        faz = t * (5.0 + 7.0 * r2.random())
        x = (0.5 + math.cos(aci + faz * 0.6) * yari_yol) * c
        y = (0.5 + math.sin(aci + faz) * yari_yol * 0.7) * c
        rr = c * (0.008 + 0.006 * r2.random())
        d = ((xx - x) ** 2 + ((yy - y) * 1.6) ** 2) / (rr * rr)
        alfa = np.maximum(alfa, np.clip(1.0 - d, 0, 1) ** 0.7)
    alfa = _bulanik(alfa, 1)
    v = np.full((c, c), 0.22, np.float32)          # KOYU: sinek isik sacmaz
    return np.dstack([v, v, v]).astype(np.float32), alfa


def _eski_k_cam(i, n, c, rng):
    """Cam kirigi -- KENARI parlak, ici bos ucgen sivri parcalar."""
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(9):
        r2 = _rng(32000 + k)
        aci0 = r2.random() * math.tau
        hiz = 0.12 + 0.24 * r2.random()
        x = (0.5 + math.cos(aci0) * hiz * t) * c
        y = (0.5 + math.sin(aci0) * hiz * t + 0.20 * t * t) * c
        don = aci0 + t * (3.0 + 5.0 * r2.random())
        L = c * (0.030 + 0.026 * r2.random())
        u = (xx - x) * math.cos(don) + (yy - y) * math.sin(don)
        v2 = -(xx - x) * math.sin(don) + (yy - y) * math.cos(don)
        # sivri ucgen: genislik uzunlukla daralir
        icinde = (u > -L) & (u < L) & (np.abs(v2) < 0.42 * (L - u) + 1e-3)
        # ⛔ Camda gorunen sey KENARDIR; dolu ucgen plastik gibi durur.
        d = np.minimum(np.abs(np.abs(v2) - (0.42 * (L - u))), np.abs(u - L))
        kenar = np.clip(1.0 - d / (c * 0.006), 0, 1)
        alfa = np.maximum(alfa, np.where(icinde, np.maximum(kenar, 0.16), 0.0))
    alfa *= (1.0 - t) ** 0.30
    alfa = _bulanik(alfa, 1)
    v = np.full((c, c), 0.90, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def k_tahta(i, n, c, rng):
    """Uzun ince kiymik -- tahta. En-boy orani 8:1, `parca`dan bariz ayri."""
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(10):
        r2 = _rng(33000 + k)
        aci0 = r2.random() * math.tau
        hiz = 0.10 + 0.22 * r2.random()
        x = (0.5 + math.cos(aci0) * hiz * t) * c
        y = (0.5 + math.sin(aci0) * hiz * t + 0.16 * t * t) * c
        don = aci0 + t * (2.5 + 4.0 * r2.random())
        L = c * (0.055 + 0.035 * r2.random())
        # ⛔ 9:1 kontakt sayfasinda "cizik" gibi okundu; 5:1 hala
        #    `parca`nin 2.4:1 blogundan bariz ayri ama GORUNUR.
        W = L * 0.20                                   # 5:1
        u = (xx - x) * math.cos(don) + (yy - y) * math.sin(don)
        v2 = -(xx - x) * math.sin(don) + (yy - y) * math.cos(don)
        # uclari sivri
        genis = W * np.clip(1.0 - (np.abs(u) / L) ** 3.0, 0, 1)
        alfa = np.maximum(alfa, ((np.abs(u) < L) & (np.abs(v2) < genis)).astype(np.float32))
    alfa *= (1.0 - t) ** 0.30
    alfa = _bulanik(alfa, 1)
    v = np.full((c, c), 0.80, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def k_beton(i, n, c, rng):
    """Kose kose IRI blok -- beton/moloz. `parca`dan buyuk ve kosegen."""
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(7):
        r2 = _rng(34000 + k)
        aci0 = r2.random() * math.tau
        # ⛔ Bloklar merkezde dogup yavas dagilinca t=0.4te ust uste
        #    binip TEK yumru oldu. Baslangicta da dagilmis olmalilar.
        hiz = 0.16 + 0.26 * r2.random()
        yay = 0.13 + 0.10 * r2.random()          # baslangic dagilimi
        x = (0.5 + math.cos(aci0) * (yay + hiz * t)) * c
        y = (0.5 + math.sin(aci0) * (yay + hiz * t) + 0.22 * t * t) * c
        don = aci0 + t * (1.5 + 3.0 * r2.random())
        R = c * (0.032 + 0.022 * r2.random())
        u = (xx - x) * math.cos(don) + (yy - y) * math.sin(don)
        v2 = -(xx - x) * math.sin(don) + (yy - y) * math.cos(don)
        # duzensiz besgen: yariçap aciya gore dalgalanir
        a2 = np.arctan2(v2, u)
        rr = np.sqrt(u * u + v2 * v2)
        dalga = 1.0 + 0.26 * np.cos(5.0 * a2 + r2.random() * 6.0)
        alfa = np.maximum(alfa, (rr < R * dalga).astype(np.float32))
    alfa *= (1.0 - t) ** 0.28
    alfa = _bulanik(alfa, 1)
    v = np.full((c, c), 0.70, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def k_kagit(i, n, c, rng):
    """Duz dikdortgen kagit -- ortasinda kirik (iki tonlu)."""
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    ton = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(7):
        r2 = _rng(35000 + k)
        aci0 = r2.random() * math.tau
        hiz = 0.12 + 0.24 * r2.random()
        x = (0.5 + math.cos(aci0) * hiz * t) * c
        y = (0.5 + math.sin(aci0) * hiz * t + 0.10 * t * t) * c
        don = aci0 + t * (2.0 + 3.0 * r2.random())
        L = c * (0.050 + 0.028 * r2.random())
        W = L * (0.62 + 0.24 * r2.random())
        u = (xx - x) * math.cos(don) + (yy - y) * math.sin(don)
        v2 = -(xx - x) * math.sin(don) + (yy - y) * math.cos(don)
        icinde = (np.abs(u) < L) & (np.abs(v2) < W)
        alfa = np.maximum(alfa, icinde.astype(np.float32))
        # kirik cizgisi: bir yarisi daha koyu -- kagidin kivrildigi okunur
        ton = np.where(icinde & (v2 > 0), 0.62, ton)
        ton = np.where(icinde & (v2 <= 0), 0.95, ton)
    alfa *= (1.0 - t) ** 0.22
    alfa = _bulanik(alfa, 1)
    v = np.where(ton > 0, ton, 0.85).astype(np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def k_kul(i, n, c, rng):
    """Cok kucuk duzensiz kul zerreleri -- serpinti. Yogun ve ince."""
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    # ⛔ Ilk iki surumde 34 zerre x 0.004-0.017c yaricap: kontakt
    #    sayfasinda kare BOS gorundu. Sebep sayi degil BOYUT --
    #    her parcacik sprite'in TAMAMINI cizer, 34 mikro nokta
    #    olcek dususunde yok oluyor. Az ve iri dogru olan.
    for k in range(7):
        r2 = _rng(36000 + k)
        x = r2.random() * c
        y = (r2.random() * 0.8 + 0.35 * t) % 1.0 * c
        # ⛔ Ilk surumde rr=0.004c ve carpan 0.5 idi: kontakt sayfasinda
        #    kare TAMAMEN BOS gorunuyordu. Kul ince olmali ama GORUNMELI.
        rr = c * (0.022 + 0.020 * r2.random())
        d = ((xx - x) ** 2 + (yy - y) ** 2 * (1.0 + 0.8 * r2.random())) / (rr * rr)
        alfa = np.maximum(alfa, np.clip(1.0 - d, 0, 1) ** 0.5 * (0.75 + 0.25 * r2.random()))
    alfa = _bulanik(alfa, 1)
    v = np.full((c, c), 0.58, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def k_damla(i, n, c, rng):
    """Gozyasi bicimi damla -- ustu sivri, alti yuvarlak."""
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(3):
        r2 = _rng(37000 + k)
        x = (0.18 + 0.64 * r2.random()) * c
        y = (0.12 + 0.62 * r2.random() + 0.24 * t) * c
        R = c * (0.032 + 0.020 * r2.random())
        u = (xx - x) / R
        v2 = (yy - y) / R
        # damla: asagida daire, yukarida daralan kuyruk
        genis = np.where(v2 < 0, np.clip(1.0 + v2 * 0.85, 0, 1) ** 1.8, 1.0)
        d = u * u / np.maximum(genis * genis, 1e-4) + v2 * v2
        alfa = np.maximum(alfa, np.clip(1.4 - d, 0, 1) ** 0.55)
    alfa = _bulanik(alfa, 1)
    v = np.full((c, c), 0.86, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def k_parlama(i, n, c, rng):
    """Yapisiz yumusak parlama -- rengi TAMAMEN tint versin diye notr."""
    t = i / max(n - 1, 1)
    r = _radyal(c)
    yari = 0.32 + 0.34 * t
    alfa = np.clip(1.0 - r / yari, 0, 1) ** 2.4
    alfa *= (1.0 - t) ** 0.85
    alfa = _bulanik(alfa, 1 + int(c * 0.008))
    cek = np.clip(1.0 - r / (yari * 0.35), 0, 1)
    v = np.clip(0.66 + 0.34 * cek, 0, 1).astype(np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def k_ark_duz(i, n, c, rng):
    """TEK zikzak cizgi -- catalsiz duz ark. `elektrik`ten bariz ayri."""
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    r2 = _rng(38000 + int(t * 97))
    # ust ortadan alt ortaya zikzak
    N = 9
    px = [0.5 * c]
    py = [0.06 * c]
    for s in range(1, N + 1):
        px.append((0.5 + (r2.random() - 0.5) * 0.34) * c)
        py.append((0.06 + 0.88 * s / N) * c)
    for s in range(N):
        x0, y0, x1, y1 = px[s], py[s], px[s + 1], py[s + 1]
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy + 1e-6
        h = np.clip(((xx - x0) * vx + (yy - y0) * vy) / L2, 0, 1)
        d = np.sqrt((xx - x0 - h * vx) ** 2 + (yy - y0 - h * vy) ** 2)
        alfa = np.maximum(alfa, np.clip(1.0 - d / (c * 0.010), 0, 1) ** 1.3)
    alfa *= (1.0 - t) ** 1.8
    alfa = _bulanik(alfa, 1)
    v = np.full((c, c), 0.94, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def k_halka_organik(i, n, c, rng):
    """Puruzlu ORGANIK halka -- enfeksiyon dalgasi.

    Referans: kullanicinin ChatGPT'ye urettirdigi enfeksiyon halkasi
    (ptfx_referans_gorseller/). Duz cember degil: yaricap gurultuyle
    bozuk, kenardan disari sis lifleri tasiyor.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    dx = (xx / c - 0.5) * 2.0
    dy = (yy / c - 0.5) * 2.0
    r = np.sqrt(dx * dx + dy * dy) + 1e-6
    aci = np.arctan2(dy, dx)
    yari = 0.10 + 0.80 * t
    # yaricap aciya gore dalgalanir: organik puruz
    puruz = (0.10 * np.sin(7.0 * aci + 1.7) + 0.06 * np.sin(13.0 * aci)
             + 0.05 * np.sin(23.0 * aci + 4.0))
    kal = 0.10 + 0.13 * t
    d = np.abs(r - yari * (1.0 + puruz))
    alfa = np.clip(1.0 - d / kal, 0, 1) ** 1.3
    # kenardan disa sis lifleri
    lif = np.clip(1.0 - (r - yari) / (kal * 2.6), 0, 1) * (r > yari)
    doku = _fbm(c, 3, 8, _rng(41000), 0.5)
    alfa = np.clip(alfa + 0.45 * lif * np.clip(doku - 0.45, 0, 1) * 2.0, 0, 1)
    alfa *= (1.0 - t) ** 1.0
    alfa = _bulanik(alfa, 1 + int(c * 0.004))
    v = np.full((c, c), 0.85, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def k_halka_ark(i, n, c, rng):
    """Kenarindan ARK dikenleri fiskiran keskin halka -- EMP/sok.

    Referans: ChatGPT EMP halkasi. Ince parlak cember + radyal zikzak
    dikenler; organik halkanin tam tersi karakter.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    dx = (xx / c - 0.5) * 2.0
    dy = (yy / c - 0.5) * 2.0
    r = np.sqrt(dx * dx + dy * dy) + 1e-6
    aci = np.arctan2(dy, dx)
    yari = 0.12 + 0.78 * t
    kal = 0.05 + 0.05 * t
    alfa = np.clip(1.0 - np.abs(r - yari) / kal, 0, 1) ** 1.1
    # radyal ark dikenleri: dar aci pencerelerinde disari uzanan cizgiler
    diken = np.zeros_like(alfa)
    r2 = _rng(42000)
    for k in range(14):
        a0 = r2.random() * math.tau
        # ⛔ 0.01 radyan ~ 1 piksel: dikenler bulanikta yok oldu (goruldu).
        gen = 0.05 + 0.06 * r2.random()
        boy = 0.14 + 0.22 * r2.random()
        fark = np.abs(((aci - a0 + math.pi) % math.tau) - math.pi)
        pencere = np.clip(1.0 - fark / gen, 0, 1)
        uzak = np.clip(1.0 - (r - yari) / boy, 0, 1) * (r > yari * 0.98)
        # zikzak: yaricap boyunca kucuk aci sapmasi
        zik = 0.5 + 0.5 * np.sin(40.0 * r + k * 2.3)
        diken = np.maximum(diken, pencere * uzak ** 1.2 * (0.6 + 0.4 * zik))
    alfa = np.clip(alfa + diken, 0, 1)
    alfa *= (1.0 - t) ** 1.4
    alfa = _bulanik(alfa, 1)
    ic = np.clip(1.0 - np.abs(r - yari) / (kal * 0.5), 0, 1)
    v = np.clip(0.72 + 0.28 * ic, 0, 1).astype(np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def _polar(c):
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    dx = (xx / c - 0.5) * 2.0
    dy = (yy / c - 0.5) * 2.0
    r = np.sqrt(dx * dx + dy * dy) + 1e-6
    return r, np.arctan2(dy, dx), dx, dy


def k_alev_topu(i, n, c, rng):
    """Isinsal alev filamentli patlama cekirdegi.

    Referanstan alinan uc karakter: (1) merkez BEYAZ sicak, (2) disari
    dogru INCE ALEV FILAMENTLERI (duz radyal falloff degil), (3) renk
    rampasi beyaz->sari->turuncu->kizil, tek duz turuncu degil.
    """
    t = i / max(n - 1, 1)
    r, aci, dx, dy = _polar(c)
    boy = 0.60 + 0.30 * t
    # filament: aciya bagli yuksek frekansli gurultu, yaricapla akan faz
    g1 = _fbm(c, 4, 6, _rng(51000), 0.55)
    g2 = _fbm(c, 3, 12, _rng(51500), 0.5)
    fil = np.abs(np.cos(14.0 * aci + 9.0 * (g1 - 0.5) + 3.5 * r)) ** 1.6
    fil = 0.35 + 0.65 * fil * (0.5 + 0.9 * g2)
    gov = np.clip(1.0 - r / boy, 0, 1) ** 1.15
    cek = np.clip(1.0 - r / (0.30 * boy), 0, 1) ** 1.15
    enerji = np.clip(gov * fil + cek * 1.2, 0, 1)
    # kenari gurultuyle parcala -- duz daire kenari kalmasin
    kenar_boz = np.clip((g1 - 0.08 - 0.42 * (r / boy)) * 4.0, 0, 1)
    alfa = np.clip(enerji * (0.55 + 0.45 * kenar_boz), 0, 1)
    alfa *= (1.0 - t) ** 0.8
    alfa = _bulanik(alfa, 1)
    # renk rampasi: enerjiden
    e = np.clip(enerji, 0, 1)
    R = np.clip(0.55 + 0.45 * e * 2.0, 0, 1)
    G = np.clip(1.55 * e - 0.08, 0, 1)
    B = np.clip(2.6 * e - 1.55, 0, 1)
    return np.dstack([R, G, B]).astype(np.float32), alfa


def k_yildiz(i, n, c, rng):
    """Dallanan elektrik yildizi -- carpma ani.

    Referans karakteri: merkezden disa 8-10 SIVRI ZIKZAK isin, her
    birinde yan dallar, merkez cok parlak. Duz cos^n dikeni degil,
    GERCEK cizgi geometrisi.
    """
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)

    def cizgi(x0, y0, x1, y1, kal):
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy + 1e-6
        h = np.clip(((xx - x0) * vx + (yy - y0) * vy) / L2, 0, 1)
        d = np.sqrt((xx - x0 - h * vx) ** 2 + (yy - y0 - h * vy) ** 2)
        return np.clip(1.0 - d / kal, 0, 1) ** 1.4

    r2 = _rng(52000)
    M = c * 0.5
    N = 9
    for k in range(N):
        a0 = k * math.tau / N + (r2.random() - 0.5) * 0.5
        boy = c * (0.26 + 0.30 * r2.random()) * (0.6 + 0.7 * (1.0 - t))
        seg = 4
        px, py = M, M
        yon = a0
        for s2 in range(seg):
            adim = boy / seg
            nx = px + math.cos(yon) * adim
            ny = py + math.sin(yon) * adim
            kal = c * 0.014 * (1.0 - 0.55 * s2 / seg) + 1.0
            alfa = np.maximum(alfa, cizgi(px, py, nx, ny, kal)
                              * (1.0 - 0.5 * s2 / seg))
            # yan dal
            if s2 >= 1 and r2.random() < 0.55:
                da = yon + (0.5 + 0.5 * r2.random()) * (1 if r2.random() < 0.5 else -1)
                bx = nx + math.cos(da) * adim * 0.9
                by = ny + math.sin(da) * adim * 0.9
                alfa = np.maximum(alfa, cizgi(nx, ny, bx, by, kal * 0.6) * 0.55)
            px, py = nx, ny
            yon += (r2.random() - 0.5) * 0.55
    r, aci, _, _ = _polar(c)
    cek = np.clip(1.0 - r / 0.16, 0, 1) ** 1.2
    alfa = np.clip(alfa + cek * 1.3, 0, 1)
    alfa *= (1.0 - t) ** 1.5
    alfa = _bulanik(alfa, 1)
    v = np.clip(0.62 + 0.38 * np.clip(cek * 2.0 + alfa * 0.3, 0, 1), 0, 1)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def k_cam(i, n, c, rng):
    """Iri fasetli cam kiriklari.

    ⛔ Ilk v2 dalgali yaricap kullandi ve parcalar CICEK gibi cikti
       (taç yaprakli siluet -- goruldu). Cam koselidir: konveks cokgen,
       rastgele yonlu 5-6 YARI DUZLEMIN kesisimi olarak kurulur.
    """
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(4):
        r2 = _rng(53000 + k)
        aci0 = r2.random() * math.tau
        hiz = 0.10 + 0.18 * r2.random()
        mx = (0.5 + math.cos(aci0) * (0.24 + hiz * t)) * c
        my = (0.5 + math.sin(aci0) * (0.24 + hiz * t) + 0.10 * t * t) * c
        R = c * (0.058 + 0.040 * r2.random())
        u = xx - mx
        v2 = yy - my
        kose = 5 + int(r2.random() * 2)
        # her yari duzlem: n·p <= mesafe ; sinira uzaklik = min(mesafe - n·p)
        d_ic = np.full((c, c), 1e9, np.float32)
        icinde = np.ones((c, c), bool)
        for e in range(kose):
            ea = e * math.tau / kose + (r2.random() - 0.5) * 0.9
            em = R * (0.55 + 0.60 * r2.random())
            proj = u * math.cos(ea) + v2 * math.sin(ea)
            icinde &= proj < em
            d_ic = np.minimum(d_ic, em - proj)
        d_ic = np.where(icinde, d_ic, 0.0)
        kenar = np.clip(1.0 - np.abs(d_ic - 0.0) / (c * 0.006), 0, 1)
        kenar = np.where(icinde & (d_ic < c * 0.006), 1.0 - d_ic / (c * 0.006), 0.0)
        fas_a = r2.random() * math.pi
        fas = np.clip(1.0 - np.abs(u * math.cos(fas_a) + v2 * math.sin(fas_a)) /
                      (c * 0.0035), 0, 1) * icinde
        parca = np.maximum(kenar, np.maximum(fas * 0.75, icinde * 0.16))
        alfa = np.maximum(alfa, parca.astype(np.float32))
    alfa *= (1.0 - t) ** 0.30
    alfa = _bulanik(alfa, 1)
    v = np.full((c, c), 0.92, np.float32)
    return np.dstack([v, v, v]).astype(np.float32), alfa


def k_kan_v2(i, n, c, rng):
    """Viskoz kan sicramasi -- referans: atlas4 sag ust.

    Karakter: merkezden disari SACILAN irili ufakli damla, aralarinda
    INCE IPLIKLER (viskozite), damlalarin ucu hareket yonunde sivri.
    Eski k_kan yalnizca yuvarlak benek kumesiydi.
    """
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    M = c * 0.5
    r2 = _rng(61000)
    for k in range(22):
        a0 = r2.random() * math.tau
        hiz = 0.08 + 0.30 * r2.random()
        mesafe = (0.06 + hiz * (0.35 + 0.65 * t)) * c
        x = M + math.cos(a0) * mesafe
        y = M + math.sin(a0) * mesafe + 0.08 * t * t * c
        R = c * (0.006 + 0.020 * r2.random() * (1.0 - 0.4 * hiz))
        # damla: hareket yonunde uzamis elips
        u = (xx - x) * math.cos(a0) + (yy - y) * math.sin(a0)
        v2 = -(xx - x) * math.sin(a0) + (yy - y) * math.cos(a0)
        d = (u / (R * (1.6 + 2.0 * hiz))) ** 2 + (v2 / R) ** 2
        alfa = np.maximum(alfa, np.clip(1.2 - d, 0, 1) ** 0.6)
        # viskoz iplik: merkezden damlaya ince cizgi (kisa omurlu)
        if r2.random() < 0.5 and t < 0.6:
            L2 = mesafe * mesafe + 1e-6
            h = np.clip(((xx - M) * (x - M) + (yy - M) * (y - M)) / L2, 0, 1)
            dd = np.sqrt((xx - M - h * (x - M)) ** 2 + (yy - M - h * (y - M)) ** 2)
            alfa = np.maximum(alfa, np.clip(1.0 - dd / (c * 0.0035), 0, 1)
                              * 0.7 * (1.0 - t))
    cek = np.clip(1.0 - (np.sqrt((xx - M) ** 2 + (yy - M) ** 2) / (c * 0.10)), 0, 1)
    alfa = np.clip(alfa + cek ** 1.5 * 0.9 * (1.0 - 0.8 * t), 0, 1)
    alfa *= (1.0 - t) ** 0.45
    alfa = _bulanik(alfa, 1)
    # koyu kirmizi govde + islak parlak tepe
    v = np.clip(0.35 + 0.45 * alfa, 0, 1)
    return np.dstack([v, v * 0.10, v * 0.08]).astype(np.float32), alfa


def k_kivilcim_v2(i, n, c, rng):
    """Dokulen kivilcim yagmuru -- referans: atlas4 sol alt.

    Karakter: yukaridan asagi INCE PARLAK CIZGILER (motion blur hissi),
    uclarda dallanma; benek degil cizgi.
    """
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    r2 = _rng(62000)

    def cizgi(x0, y0, x1, y1, kal, guc):
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy + 1e-6
        h = np.clip(((xx - x0) * vx + (yy - y0) * vy) / L2, 0, 1)
        d = np.sqrt((xx - x0 - h * vx) ** 2 + (yy - y0 - h * vy) ** 2)
        return np.clip(1.0 - d / kal, 0, 1) ** 1.5 * guc

    for k in range(26):
        x0 = (0.34 + 0.32 * r2.random()) * c
        y0 = 0.04 * c + r2.random() * 0.10 * c
        yan = (r2.random() - 0.5) * 0.55
        boy = (0.25 + 0.55 * r2.random()) * c * (0.4 + 0.6 * t)
        x1 = x0 + yan * boy
        y1 = y0 + boy
        kal = c * (0.0016 + 0.0022 * r2.random())
        alfa = np.maximum(alfa, cizgi(x0, y0, x1, y1, kal, 0.75 + 0.25 * r2.random()))
        if r2.random() < 0.4:
            dx2 = (r2.random() - 0.5) * 0.3 * boy
            alfa = np.maximum(alfa, cizgi(x1, y1, x1 + dx2, y1 + 0.22 * boy,
                                          kal * 0.7, 0.5))
    alfa *= (1.0 - t) ** 0.9
    alfa = _bulanik(alfa, 1)
    v = np.clip(0.75 + 0.25 * alfa, 0, 1)
    return np.dstack([v, v * 0.72, v * 0.38]).astype(np.float32), alfa


def k_ates_v2(i, n, c, rng):
    """Dikey ALEV DILLERI -- referans: atlas4 sol ust.

    Karakter: tabandan yukari yalayan, ucta incelip kopan diller;
    beyaz-sicak taban, sari govde, turuncu-kizil uc. Duz radyal leke
    DEGIL: dikey akis + aciyla degil YUKSEKLIKLE daralan siluet.
    """
    t = i / max(n - 1, 1)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    u = xx / c                      # 0..1 yatay
    h = 1.0 - yy / c                # 0 = taban, 1 = tepe

    # dikey akan gurultu: kare boyunca yukari kayar (alev tirmanir)
    g = _fbm(c, 4, 4, _rng(71000), 0.58)
    kay = int((0.45 + 0.55 * t) * c) % max(c, 1)
    g = np.roll(g, -kay, axis=0)
    g2 = _fbm(c, 3, 9, _rng(71500), 0.5)
    g2 = np.roll(g2, -int(kay * 1.6) % max(c, 1), axis=0)

    # siluet: tabanda genis, tepede dar; kenar gurultuyle yalanir
    boy = 0.55 + 0.40 * t
    genis = 0.34 * np.clip(1.0 - (h / boy) ** 1.5, 0, 1)
    # dil: yatay konumu gurultuyle burkulur -> yalama hissi
    burk = (g - 0.5) * 0.30 * np.clip(h / max(boy, 1e-3), 0, 1)
    d = np.abs((u - 0.5) + burk)
    govde = np.clip(1.0 - d / np.maximum(genis, 1e-4), 0, 1)

    # ust ucta kopma: yuksekte esik yukselir -> diller ayrilir
    esik = 0.22 + 0.42 * np.clip(h / max(boy, 1e-3), 0, 1)
    dil = np.clip((0.55 * g + 0.45 * g2 - esik) / 0.22, 0, 1)
    alfa = np.clip(govde ** 0.85 * (0.35 + 0.85 * dil), 0, 1)
    alfa *= np.clip(h / 0.06, 0, 1)          # tabani kes
    alfa *= (1.0 - t) ** 0.45
    alfa = _bulanik(alfa, 1)

    # renk: yukseklige ve yogunluga gore beyaz -> sari -> turuncu -> kizil
    sicak = np.clip(govde * (1.0 - h / max(boy, 1e-3)) * 1.6, 0, 1)
    R = np.clip(0.70 + 0.30 * sicak * 2.0, 0, 1)
    G = np.clip(0.18 + 1.05 * sicak, 0, 1)
    B = np.clip(1.9 * sicak - 1.05, 0, 1)
    return np.dstack([R, G, B]).astype(np.float32), alfa


def k_beton_v2(i, n, c, rng):
    """Kose kose IRI beton bloklari.

    ⛔ Eski surum `1 + 0.26*cos(5a)` dalgali yaricap kullaniyordu ve
       CICEK silueti veriyordu (kontakt sayfasinda goruldu -- camda
       duzeltilen hatanin aynisi). Konveks cokgen = rastgele yonlu
       5-6 yari duzlemin kesisimi.
    """
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    ton = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    for k in range(5):
        r2 = _rng(72000 + k)
        aci0 = r2.random() * math.tau
        yay = 0.22 + 0.12 * r2.random()
        hiz = 0.14 + 0.24 * r2.random()
        mx = (0.5 + math.cos(aci0) * (yay + hiz * t)) * c
        my = (0.5 + math.sin(aci0) * (yay + hiz * t) + 0.20 * t * t) * c
        R = c * (0.034 + 0.026 * r2.random())
        u = xx - mx
        v2 = yy - my
        kose = 5 + int(r2.random() * 2)
        icinde = np.ones((c, c), bool)
        d_ic = np.full((c, c), 1e9, np.float32)
        for e in range(kose):
            ea = e * math.tau / kose + (r2.random() - 0.5) * 0.8
            em = R * (0.60 + 0.55 * r2.random())
            proj = u * math.cos(ea) + v2 * math.sin(ea)
            icinde &= proj < em
            d_ic = np.minimum(d_ic, em - proj)
        blok = icinde.astype(np.float32)
        alfa = np.maximum(alfa, blok)
        # aydinlik yuz / golgeli yuz: hacim hissi
        isik = np.clip(0.55 + 0.45 * np.cos(np.arctan2(v2, u) - 0.9), 0, 1)
        ton = np.where(icinde, isik, ton)
    alfa *= (1.0 - t) ** 0.28
    alfa = _bulanik(alfa, 1)
    v = np.where(ton > 0, 0.42 + 0.52 * ton, 0.60).astype(np.float32)
    return np.dstack([v, v * 0.98, v * 0.95]).astype(np.float32), alfa


def k_kivilcim_patlama(i, n, c, rng):
    """Merkezden DISA fiskiran kivilcim -- surtunme / metal burulma.

    `k_kivilcim_v2` (yagmur) ile kasten farkli: orada cizgiler asagi
    doker, burada MERKEZDEN radyal firlar ve yercekimiyle asagi kivrilir.
    """
    t = i / max(n - 1, 1)
    alfa = np.zeros((c, c), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32)
    M = c * 0.5
    r2 = _rng(73000)

    def cizgi(x0, y0, x1, y1, kal, guc):
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy + 1e-6
        h = np.clip(((xx - x0) * vx + (yy - y0) * vy) / L2, 0, 1)
        d = np.sqrt((xx - x0 - h * vx) ** 2 + (yy - y0 - h * vy) ** 2)
        return np.clip(1.0 - d / kal, 0, 1) ** 1.5 * guc

    for k in range(24):
        a0 = r2.random() * math.tau
        hiz = (0.10 + 0.26 * r2.random())
        # iz: baslangictan simdiki konuma; yercekimi ile asagi kivrilir
        t0 = max(0.0, t - 0.16)
        def konum(tt):
            x = M + math.cos(a0) * hiz * tt * c * 2.0
            y = M + math.sin(a0) * hiz * tt * c * 2.0 + 0.55 * tt * tt * c
            return x, y
        x0, y0 = konum(t0)
        x1, y1 = konum(t)
        kal = c * (0.0018 + 0.0022 * r2.random())
        alfa = np.maximum(alfa, cizgi(x0, y0, x1, y1, kal,
                                      0.7 + 0.3 * r2.random()))
    cek = np.clip(1.0 - np.sqrt((xx - M) ** 2 + (yy - M) ** 2) / (c * 0.06), 0, 1)
    alfa = np.clip(alfa + cek ** 1.4 * (1.0 - t) * 0.9, 0, 1)
    alfa *= (1.0 - t) ** 0.8
    alfa = _bulanik(alfa, 1)
    v = np.clip(0.72 + 0.28 * alfa, 0, 1)
    return np.dstack([v, v * 0.70, v * 0.34]).astype(np.float32), alfa


def tek_nesne(rgba, pay=0.06):
    """EN BUYUK nesneyi tutar, sikica kirpar, kareyi doldurur.

    ⛔ IKI OLCULMUS KURAL:

    1) SPRITE BASINA TEK NESNE. Vanilla'nin enkaz atlaslarinda her hucrede
       **1 nesne** var (olculdu: multi_sheet_002/003/004 ve
       fine_debris_sheet 1, glass_dots 2). Bizimkilerde 3-6 vardi
       (beton 5, moloz 6, cam 4). Her parcacik sprite'in TAMAMINI cizdigi
       icin 15 parcacik = 75 parca yumagi -- "enkaz" degil kalabalik.

    2) SIKI KIRPMA. "Alpha coverage of a particle sprite is one of the most
       underestimated sources of performance" (VFXDoc): bos kenar hem
       bosa doldurma hem de parcacigi kucuk gosterir. Nesne kareyi
       doldurmali, cevresinde yalnizca kenar solmasi payi kalmali.
    """
    a = rgba[..., 3]
    m = a > 0.12
    if not m.any():
        return rgba
    # ---- en buyuk birlesik bileseni bul (etiketleme, yiginsiz) ----
    H, W = m.shape
    et = np.zeros((H, W), np.int32)
    n = 0
    en_iyi, en_boy = 0, 0
    for y0 in range(H):
        satir = m[y0]
        for x0 in range(W):
            if not satir[x0] or et[y0, x0]:
                continue
            n += 1
            yig = [(y0, x0)]
            et[y0, x0] = n
            boy = 0
            while yig:
                cy, cx = yig.pop()
                boy += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < H and 0 <= nx < W and m[ny, nx] and not et[ny, nx]:
                        et[ny, nx] = n
                        yig.append((ny, nx))
            if boy > en_boy:
                en_boy, en_iyi = boy, n
    if en_iyi == 0:
        return rgba
    tut = (et == en_iyi)
    out = rgba.copy()
    out[..., 3] = np.where(tut, a, 0.0)

    # ---- siki kirpma + kareye buyutme ----
    ys, xs = np.where(tut)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    kh, kw = y1 - y0, x1 - x0
    k = max(kh, kw)
    k = int(k * (1.0 + 2.0 * pay))
    cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
    ty0, tx0 = cy - k // 2, cx - k // 2
    kare = np.zeros((k, k, 4), np.float32)
    sy0, sx0 = max(0, ty0), max(0, tx0)
    sy1, sx1 = min(H, ty0 + k), min(W, tx0 + k)
    kare[sy0 - ty0:sy1 - ty0, sx0 - tx0:sx1 - tx0] = out[sy0:sy1, sx0:sx1]
    # orijinal cozunurluge geri olcekle
    yi = (np.arange(H) + 0.5) * (k / float(H)) - 0.5
    i0 = np.clip(np.floor(yi).astype(np.int32), 0, k - 1)
    i1 = np.clip(i0 + 1, 0, k - 1)
    f = np.clip(yi - i0, 0, 1)[:, None, None]
    ara = kare[i0] * (1 - f) + kare[i1] * f
    f2 = np.clip(yi - i0, 0, 1)[None, :, None]
    son = ara[:, i0] * (1 - f2) + ara[:, i1] * f2
    son = son.astype(np.float32)
    # ⛔ BUYUTME BULANIKLIGI DA BUYUTUR. Kucuk nesneye uygulanan 1-2
    #    piksellik bulaniklik 4-6 kat buyutulunce yayvan bir leke olur
    #    (goruldu: beton TEKIL yumusacik cikti). Alfayi dik bir egriden
    #    gecirerek kenar keskinligini geri kazan.
    olcek_kat = k / float(H)
    if olcek_kat > 1.6:
        a2 = son[..., 3]
        orta = 0.42
        dik = 1.0 + 1.6 * min(olcek_kat / 4.0, 1.0)
        son[..., 3] = np.clip((a2 - orta) * (1.0 + 2.4 * dik) + orta, 0, 1)
    son[..., 3] *= _kenar_maskesi(H, pay=0.04)
    return np.clip(son, 0, 1)


# ⛔ Bu aileler SPRITE BASINA TEK NESNE olmali (vanilla olcumu: enkaz
#    atlaslarinda hucre basina 1 nesne). Kume cizmek 15 parcacikta
#    75 parca yumagi uretir.
# ⚠ `sinek` ve `kor` LISTEDE YOK: ikisi de dogasi geregi KUCUK ve
#   coktur; tek taneyi buyutmek sekilsiz bir leke veriyor (goruldu).
TEKIL = {"parca", "beton", "cam", "tahta", "kagit", "kul", "damla",
         "yaprak", "sicrama", "kabarcik"}

AILE = {
    "duman": k_duman, "ates": k_ates_v2, "alev_topu": k_alev_topu,
    "toz": k_toz, "buhar": k_buhar, "kivilcim": k_kivilcim_v2,
    "sicrama": k_sicrama, "kor": k_kor, "sis": k_sis,
    "kabarcik": k_kabarcik, "parca": k_parca, "halka": k_halka,
    "elektrik": k_elektrik, "kan": k_kan_v2, "yaprak": k_yaprak,
    "halka_organik": k_halka_organik, "halka_ark": k_halka_ark,
    "yildiz": k_yildiz, "sinek": k_sinek, "cam": k_cam, "tahta": k_tahta,
    "beton": k_beton_v2, "kivilcim_patlama": k_kivilcim_patlama, "kagit": k_kagit, "kul": k_kul, "damla": k_damla,
    "parlama": k_parlama, "ark_duz": k_ark_duz,
}


# ----------------------------------------------------------------- surucu

# Aile basina ALFA TEPE hedefi.
#
# ⛔ SAYFALARIMIZ HIC OPAKLIGA ULASMIYORDU. Olculdu: bizim 15 ailenin
# alfa tepesi 0.30-0.47 arasindaydi, vanilla duman sayfalarininki 0.59-0.97.
# Oyundaki belirti "efekt referans kadar yogun degil" -- efekt yanlis degil,
# yalnizca hicbir yerde yeterince opak degil. Sebep bir tek yerde degil:
# kenar maskesi, bulaniklik ve omur sonmesi carpani ust uste binince tepe
# eziliyor. Tek tek ailelerde ugrasmak yerine sayfa uretildikten SONRA
# tepe hedefe olceklenir.
#
# Hedefler vanilla muadilinden alindi (alfa tepesi):
#   ptfx_smoke_new_plumes 0.93 · billow 0.97 · wispy 0.74
#   ptfx_smoke_thin 0.71 · ptfx_steam 0.59
ALFA_TEPE = {
    "duman": 0.93, "ates": 0.95, "alev_topu": 0.97, "toz": 0.85,
    "buhar": 0.62, "kivilcim": 1.00, "sicrama": 0.95, "kor": 1.00,
    "sis": 0.58, "kabarcik": 0.90, "parca": 1.00, "halka": 0.92,
    "elektrik": 1.00, "kan": 0.95, "yaprak": 1.00,
    "halka_organik": 0.92, "halka_ark": 1.00,
    "yildiz": 1.00, "sinek": 0.90, "cam": 1.00, "tahta": 1.00,
    "beton": 1.00, "kivilcim_patlama": 1.00, "kagit": 1.00, "kul": 0.80, "damla": 0.95,
    "parlama": 0.92, "ark_duz": 1.00,
}


def _gorunur(alfa):
    """Karenin GORUNUR doluluk orani (0..1).

    ⛔ OLCUM, GONDERILEN VERI UZERINDE YAPILIR. Alfa float olarak
    olculurse 0.0201 degeri "dolu" sayilir; ama `yaz()` uint8'e yuvarlar
    (0.0201 -> 5 -> 0.0196) ve gonderilen kare esigin ALTINA duser.
    Olculdu: `duman` kare 63 ve `sis` kare 0 kapidan "dolu" diye gecti,
    PNG'de tamamen bos cikti - iki tur bosa gitti. Float'a degil,
    nicemlenmis degere bak.
    """
    q = np.floor(np.clip(alfa, 0, 1) * 255.0 + 0.5) / 255.0
    return float((q > 0.02).mean())


def _kenar_maskesi(hucre, pay=0.045):
    """Hucre kenarinda yumusak sonum maskesi.

    ⛔ Flipbook karesi hucre kenarina degerse oyunda sprite quad'in
    sinirinda SERT KESIK gorunur - vanilla sayfalarin hepsinde kareler
    saydam bir cerceve icindedir. Olculdu: `ates` kenara 0.44 alfayla
    degiyordu, `duman`/`kivilcim` 0.00 ile temizdi.
    """
    p = max(2, int(hucre * pay))
    d = np.minimum(np.arange(hucre), np.arange(hucre)[::-1]).astype(np.float32)
    q = np.clip(d / p, 0.0, 1.0)
    q = q * q * (3.0 - 2.0 * q)          # smoothstep
    return np.minimum(q[:, None], q[None, :])


def sayfa(aile, kare=36, coz=1024, tohum=0):
    """Kare izgarali flipbook uretir -> RGBA numpy (coz, coz, 4), 0..1.

    ⛔ `kare` TAM KARE olmali (4/16/36/64); motor izgarayi sqrt ile bolur.
    """
    k = int(round(math.sqrt(kare)))
    if k * k != kare:
        raise ValueError("kare sayisi tam kare olmali (4, 16, 25, 36, 49): %d" % kare)
    # ⛔ KARE SAYISININ VANILLA TAVANI 49'DUR. core.ypt'te 781
    # AnimateTexture olculdu: `Unknown_C4h` maks 49 (50 kare), C4 > 63 olan
    # kural sifir. 64 kare denendi; motor izgarayi HIC uygulamadi ve her
    # sprite sayfanin tamamini tek karede cizdi (oyunda dogrulandi).
    if kare > 49:
        raise ValueError(
            "kare sayisi %d vanilla bandinin disinda (olculen maks 50). "
            "Motor izgarayi uygulamaz, sayfanin tamamini cizer. "
            "36 (6x6) ya da 49 (7x7) kullan." % kare)
    if aile not in AILE:
        raise KeyError("aile '%s' yok. Gecerli: %s" % (aile, ", ".join(sorted(AILE))))
    hucre = coz // k
    fn = AILE[aile]
    kenar = _kenar_maskesi(hucre)

    def uret(t0, t1):
        """Kareleri t araligi [t0, t1] uzerine dagitir.

        Aile fonksiyonlari `t = i / (n - 1)` hesaplar; dogrudan t veremeyiz.
        Ayni sonuc `n` ve bir `ofs` kaydirmasiyla elde edilir:
            (n - 1) = (kare - 1) / (t1 - t0)      ve      ofs = t0 * (n - 1)
        `ofs` TAM SAYI yuvarlanir: bazi aileler `i`'yi ayrica rastgelelik
        tohumunda kullanir (`_rng(2600 + i * 3)`), kesirli indeks orada
        anlamsizdir.

        ⛔ rng GECIS BASINA TEK OLMALI, kare basina degil. Kare basina
        yeni bir `_rng(tohum)` yaratmak her kareye AYNI rastgele diziyi
        verir ve kareler birbirinin ayni cikar (durgun sprite).
        """
        n1 = (kare - 1) / max(t1 - t0, 1e-3)
        ofs = int(round(t0 * n1))
        rng = _rng(tohum)
        kk, tasma = [], 0.0
        for i in range(kare):
            rgb, alfa = fn(i + ofs, n1 + 1.0, hucre, rng)
            alfa = np.clip(alfa, 0, 1)
            tasma = max(tasma, float(max(alfa[:, :2].max(), alfa[:, -2:].max(),
                                         alfa[:2].max(), alfa[-2:].max())))
            kk.append((rgb, alfa * kenar))
        return kk, tasma

    # 1. gecis: t araligi [0, (kare-1)/kare]. UST UC 1.0 OLAMAZ - her
    # ailedeki `(1 - t) ** k` sonme carpani t = 1'de tam SIFIR verir ve
    # son kare TAMAMEN BOS cikar. `Unknown_C4h = kare - 1` motora o kareyi
    # de cizdirir, yani efekt her dongude bir kare "yanip soner". Olculdu:
    # 15 ailenin 15'inde kare 63 bostu.
    ust = (kare - 1) / float(kare)
    kk, tasma = uret(0.0, ust)

    # 2. gecis: bos kalan bas/kuyruk kareleri varsa t araligi DARALTILIR.
    # Sonme carpani duzeltildikten sonra bile bos kareler kaldi ve sebep
    # carpan degil ailenin KENDI zarfiydi: `halka` kadraji terk ediyor,
    # `sis` t=0.5'te tepe yapip iki yana soniyor (bas tarafta 7 bos kare),
    # `kabarcik` ilk kabarcigi gecikmeyle basliyor. Bos kare hem israftir
    # hem efekti bir an kaybettirir. Olculen ilk/son dolu kareye gore
    # aralik yeniden kurulur - tahmin degil, kendi ciktisini olcen duzeltme.
    #
    # ⛔ TEK GECIS YAKINSAMAZ. Ilk olcume gore araligi daraltmak yeni
    # sinir karelerini gene sifira dusurebilir - olculdu: `halka` bir
    # gecisle 1 bos kareden 1 bos kareye gitti, `sis` 7'den 2'ye indi ama
    # sifirlanmadi. Aralik BOS KARE KALMAYANA KADAR ice dogru itilir.
    t0, t1 = 0.0, ust
    for _tur in range(6):
        dolu = [_gorunur(a) for _, a in kk]
        var = [n for n, d in enumerate(dolu) if d > 0.002]
        if not var:
            break
        if var[0] == 0 and var[-1] == kare - 1:
            break                                   # bos kare yok
        adim = (t1 - t0) / max(kare - 1, 1)
        y0 = t0 + var[0] * adim
        y1 = t0 + var[-1] * adim
        # bir adim ICE it: sinir karesi tam sifir noktasina oturmasin
        pay = (y1 - y0) * 0.02
        y0, y1 = y0 + pay, y1 - pay
        if y1 - y0 < 0.05:
            break
        t0, t1 = y0, y1
        kk, tasma = uret(t0, t1)

    # Son kapi: oturtmadan SONRA hala bos kalan kare komsularindan doldurulur.
    #
    # Aralik daraltma bos uclari kapatir ama her zaman yakinsamaz ve ORTADAKI
    # bosluga hic dokunmaz. Olculdu, uc ayri sebep: `duman` kuyrukta (kendi
    # zarfi sifira iniyor), `sis` basta (t=0.5'te tepe yapan simetrik zarf),
    # `toz` ORTADA kare 11'de - komsulari %2.4 ve %5.4 iken kendisi %0.
    # Ortadaki bosluk bir oturtma sorunu degil, ureticinin kare dusurmesidir
    # ve oyunda gorunur bir titremedir. Yama gorseldir, sebebi gizlemez:
    # kac kare dolduruldugu bildirilir.
    esik = 0.0005
    dolu = [_gorunur(a) for _, a in kk]
    var = [n for n, d in enumerate(dolu) if d > esik]
    yama = 0
    if var:
        for n in range(kare):
            if dolu[n] > esik:
                continue
            onc = max((v for v in var if v < n), default=None)
            snr = min((v for v in var if v > n), default=None)
            if onc is None and snr is None:
                continue
            if onc is None:
                kk[n] = (kk[snr][0].copy(), kk[snr][1].copy())
            elif snr is None:
                kk[n] = (kk[onc][0].copy(), kk[onc][1].copy())
            else:
                w = (n - onc) / float(snr - onc)
                r0, a0 = kk[onc]
                r1, a1 = kk[snr]
                kk[n] = (r0 * (1 - w) + r1 * w, a0 * (1 - w) + a1 * w)
            yama += 1
    if yama:
        print("NOT: %s %d bos kare komsularindan dolduruldu"
              % (aile, yama), file=sys.stderr)

    # ⛔ IZGARA DOKUYU TAM BOLMEK ZORUNDA DEGIL. Bu sart YANLISTI ve
    # 64 kareye gecmenin sebebiydi: vanilla `ptfx_smoke_wispy_anim`
    # 1024x1024 uzerinde 7x7'dir (1024/7 = 146.29). Motor UV uzayinda 1/k
    # adimlarla ornekler, piksel hizasi aramaz. Hucre icerigi `hucre`
    # boyunda uretilir, kokler KESIRLI sinira yuvarlanir; kalan alt piksel
    # payi kenar maskesi sayesinde zaten saydamdir.
    # Alfa tepesini aile hedefine olcekle. Olcut olarak MAKSIMUM degil
    # 99,7'lik dilim alinir: tek bir aykiri piksel butun sayfayi sondurur.
    hedef = ALFA_TEPE.get(aile)
    if hedef:
        yigin = np.concatenate([a.ravel() for _, a in kk])
        tepe = float(np.percentile(yigin, 99.7))
        if tepe > 1e-4:
            olcek = hedef / tepe
            kk = [(rgb, np.clip(a * olcek, 0.0, 1.0)) for rgb, a in kk]

    out = np.zeros((coz, coz, 4), np.float32)
    for i, (rgb, alfa) in enumerate(kk):
        sy = int(round((i // k) * coz / float(k)))
        sx = int(round((i % k) * coz / float(k)))
        out[sy:sy + hucre, sx:sx + hucre, :3] = rgb
        out[sy:sy + hucre, sx:sx + hucre, 3] = alfa
    if tasma > 0.35:
        # Maske tasmayi yumusatir ama gizlemez: bu kadar tasan bir icerik
        # hucreye SIGMIYORDUR, kaynaginda kucultulmelidir.
        print("UYARI: %s hucre kenarina alfa %.2f ile degiyor (kaynagi kucult)"
              % (aile, tasma), file=sys.stderr)
    return out

def notrlestir(rgba):
    """RGB'yi parlakliga indirger, alfayi korur -- TINT'in tutmasi icin.

    ⛔ Motor rengi CARPIM olarak uygular (`ptxu_Colour` RGB). Turuncu bir
       sprite'i maviyle carpmak mavi vermez: sprite'in mavi kanali 0.09,
       carpim onu geri getiremez. Olculdu (alfa agirlikli ortalama x tint):

         cerenkov      kor sprite'i, mavi tint  -> ton sapmasi **118°**
         buyu_toplanma kor,          mavi       -> **165°**
         buyu_mermisi  kor,          mavi       -> **156°**
         isinlanma     kor,          lavanta    -> **129°**
         buyu_carpma   alev_topu,    lavanta    -> **109°**
         sifa_aurasi   kor,          nane yesili-> **91°**
         ark_carpmasi  alev_topu,    beyaz      -> **177°**
         sicak_nokta   kor,          sari-yesil -> **33°**

       Notr (gri) sprite'ta ton TAMAMEN tint'ten gelir, sapma 0 olur.
       Sekil ve yogunluk parlaklikta korunur.

    Katsayilar Rec.709 luma; algilanan parlakligi korur, kanal ortalamasi
    almak yesili bastirir.
    """
    y = (0.2126 * rgba[..., 0] + 0.7152 * rgba[..., 1] + 0.0722 * rgba[..., 2])
    out = rgba.copy()
    out[..., 0] = y
    out[..., 1] = y
    out[..., 2] = y
    return out


def tek_kare(aile, coz=512, t=0.45, tohum=0, notr=False, tekil=False):
    """TEK kare uretir -- flipbook YOK.

    ⛔ CUSTOM `.ypt`'DE SAYFA DILIMLEMESI CALISMIYOR. Numarali tani
    sayfasiyla oyunda olculdu: 4x4'te 1..16'nin, 7x7'de 1..49'un TAMAMI
    tek parcacikta ayni anda goruluyor. Izgara boyutu fark etmiyor;
    2x2'nin "calisir" gorunmesi yanilsamaydi (4 puf kucuk olcekte duman
    gibi okunuyor). Vanilla kendi `core.ypt`'sinde 7x7 kullanip calistiriyor
    ama stream edilen dosyada ayni yapi calismiyor -- sebebi cozulmedi.

    Cozum: sayfayi birakmak. Vanilla'nin 1736 partikul kuralinin 955'i
    zaten `AnimateTexture` TASIMIYOR; hareket boyut/renk/hiz egrilerinden
    gelir. Bu fonksiyon ailenin omrunun `t` anindaki karesini tek basina,
    tam cozunurlukte uretir.
    """
    if aile not in AILE:
        raise KeyError("aile '%s' yok" % aile)
    fn = AILE[aile]
    rng = _rng(tohum)
    # t'yi dogrudan vermek icin: fn `t = i/(n-1)` hesaplar -> i=1, n=1+1/t
    n1 = 1.0 + 1.0 / max(t, 1e-3)
    rgb, alfa = fn(1, n1, coz, rng)
    alfa = np.clip(alfa, 0, 1) * _kenar_maskesi(coz, pay=0.03)
    hedef = ALFA_TEPE.get(aile)
    if hedef:
        tepe = float(np.percentile(alfa, 99.7))
        if tepe > 1e-4:
            alfa = np.clip(alfa * (hedef / tepe), 0.0, 1.0)
    out = np.zeros((coz, coz, 4), np.float32)
    out[..., :3] = rgb
    out[..., 3] = alfa
    if tekil:
        out = tek_nesne(out)
    if notr:
        out = notrlestir(out)
    return out


def yaz(rgba, yol):
    a = (np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(a, "RGBA").save(yol)
    return yol


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("aile", nargs="?", help="efekt ailesi")
    ap.add_argument("cikti", nargs="?", help="PNG cikti yolu")
    ap.add_argument("--kare", type=int, default=36,
                    help="kare sayisi, TAM KARE olmali (4/16/36/64)")
    ap.add_argument("--coz", type=int, default=1024, help="sayfa cozunurlugu")
    ap.add_argument("--tohum", type=int, default=0)
    ap.add_argument("--tek", type=float, default=None, metavar="T",
                    help="flipbook YERINE tek kare uret (omrun T ani, 0..1)")
    ap.add_argument("--notr", action="store_true",
                    help="RGB'yi parlakliga indir -- rengi motorun tint'i versin")
    ap.add_argument("--liste", action="store_true")
    a = ap.parse_args()
    if a.liste or not a.aile:
        print("aileler: " + ", ".join(sorted(AILE)))
        return 0
    if not a.cikti:
        print("cikti yolu gerekli", file=sys.stderr)
        return 2
    if a.tek is not None:
        r = tek_kare(a.aile, a.coz, a.tek, a.tohum, a.notr)
    else:
        r = sayfa(a.aile, a.kare, a.coz, a.tohum)
    yaz(r, a.cikti)
    dolu = float((r[..., 3] > 0.02).mean())
    print("%s -> %s  %dx%d  %d kare  dolu=%%%.1f"
          % (a.aile, a.cikti, a.coz, a.coz, a.kare, dolu * 100))
    if dolu < 0.005:
        print("UYARI: sayfa neredeyse bos", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
