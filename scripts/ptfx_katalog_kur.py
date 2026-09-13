#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ptfx_katalog_kur.py — katalogdaki bir efekt ailesini uretir ve DENETLER.

ILKE: donorun kendi degerleri KORUNUR. Vanilla o efekti zaten dengelemis;
uzerine yazmak "gereksiz fazla / gereksiz az efekt" uretmenin en hizli yolu.
Yalnizca ailenin gercekten farkli olmasi gereken alani override edilir ve
her override'in GEREKCESI spec'te yazilir.

⛔ Donor TEK EMITTERLI olmali (`ypt_transplant.py` boyle calisiyor).
   251 tek emitterli efekt var; cok emitterli olan reddedilir.
⛔ Sayfa dilimlemesi custom `.ypt`'de calismiyor -> `UnknownC4 = 0`.
⛔ Alfali dokuda `RGB_*` teknik alfayi yok sayar -> `RGBA_*`e cevrilir.

Kullanim:
  python ptfx_katalog_kur.py --grup virus_ambiyans
  python ptfx_katalog_kur.py --grup virus_ambiyans --denetle-sadece
"""
from __future__ import annotations

import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import zlib

import ptfx_hareket
import ptfx_sayfa

BETIK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BETIK)
import tempfile  # noqa: E402
_TMP = tempfile.gettempdir()
VANILLA = os.path.join(_TMP, "vanilla_ptfx", "core.ypt.xml")
SPRITE = os.path.join(_TMP, "ptfx_uret")
CIKTI = os.path.join(_TMP, "ptfx_katalog")

# ⛔ TEK KARE SPRITE ICIN 512 FAZLA. Olculdu: vanilla core.ypt'nin en
#    yaygin doku boyutu **256x256** (107 dokunun 33'u); 512 kullandigi
#    yerler 16-49 KARELIK SAYFALAR, yani kare basina ~73 piksel.
#    Bizimkiler tek kare oldugu halde 512'ydi -> 71 doku = 23.7 MB,
#    `.ypt` 6.56 MB ve `RequestNamedPtfxAsset` oyunu KILITLEDI
#    (`/ptfxt1` tek basina dondurdu; efekt ve etiket masumdu).
COZ = 256

# aile: (donor, sprite, renk, override, neden, HAREKET)
#
# ⛔ HAREKET DEVRALINMAZ, YAZILIR. Donorun hareketini oldugu gibi birakmak
#    o efekti yeni renk giydirmekten baska bir sey degildir ve oyunda
#    DONORUN KENDISI gorunur. Uc olculmus vaka referans §13'te.
#    Anlamlar: dogus = parcaciklarin dogdugu hacim (m),
#              hedef = yon x mesafe (hiz), ivme = yercekimi/yukselis.
GRUPLAR = {
 "virus_ambiyans": [
  ("spor_bulutu", "ent_amb_dust_motes", "toz", (0.62, 0.70, 0.52), {},
   "Donor zaten seyrek ve yavas asili tane; sporun istedigi tam bu.",
   # ⚠ `ent_amb_dust_motes`ta `ptxu_Acceleration` birimi YOK. Spor icin
   #    ivme zaten kritik degil: hedef (0,0,0.15) yavas yukselisi veriyor
   #    ve donorun asili-kalma davranisi tam istedigimiz sey. Anahtari
   #    kaldirmak, tasimadigi bir sey istemektense dogru olan.
   {"boy": (0.09, 0.09, 0.09), "tip": "Sphere", "dogus": (1.5, 1.5, 1.5), "hedef": (0, 0, 0.15),
    "surtunme": (0.4, 0.4, 0.4)}),
  ("kan_sisi", "blood_mist", "kan", (0.55, 0.06, 0.05), {},
   "blood_mist bizzat kan sisi; oran/omur donorden.",
   {"boy": (0.35, 0.35, 0.35), "tip": "Sphere", "dogus": (0.3, 0.3, 0.3), "hedef": (0, 0, 0.25),
    "ivme": (0, 0, -0.6), "surtunme": (0.5, 0.5, 0.5)}),
  ("cozunme_sivisi", "ent_amb_fbi_fire_drip", "damla", (0.30, 0.26, 0.18),
   {"omur": 3.0, "oran": 1.5},
   "Donor yangin damlasi: 3/sn cok sik. Morg damlamasi SEYREK olmali.",
   {"boy": (0.1, 0.1, 0.1), "tip": "Box", "dogus": (0.4, 0.4, 0.02), "hedef": (0, 0, -2.0),
    "ivme": (0, 0, -9.8)}),
  ("kimyasal_buhar", "ent_amb_dry_ice_vent", "buhar", (0.92, 0.94, 0.95), {},
   "Kuru buz venti; hareket YAZILDI: dar agizdan yukari cikan buhar.",
   {"boy": (0.6, 0.6, 0.6), "tip": "Cylinder", "dogus": (0.2, 0.05, 0.2), "hedef": (0, 0, 1.2),
    "ivme": (0, 0, 0.6), "surtunme": (0.3, 0.3, 0.1)}),
  # ⛔ Donor `fire_extinguish` -- YANGIN SONDURUCU JETI. TargetDomain'i
  #    3.5 m yukariyi hedefliyordu; oyunda halka fiskirtti. Bulasma
  #    dalgasi ZEMINDE yayilir: hedef neredeyse duz, attractor sifir.
  ("bulasma_dalgasi", "fire_extinguish", "halka_organik", (0.45, 0.72, 0.35),
   {"oran": 2.0, "omur": 1.2},
   "Jet hareketi silindi; zeminde yatay yayilan dalga yazildi.",
   {"boy": (1.3, 1.3, 1.3), "tip": "Cylinder", "dogus": (0.3, 0.05, 0.3), "hedef": (0, 0, 0.05),
    "hedef_boy": (1.6, 0.05, 1.6), "ivme": (0, 0, 0),
    "surtunme": (0.8, 0.8, 0.9), "attractor_sil": True}),
  ("zemin_sisi", "ent_amb_dry_ice_area", "sis", (0.72, 0.74, 0.76),
   {"oran": 6.0, "omur": 8.0},
   "Zemin sisi surekli ve DURGUN: genis yassi hacim, neredeyse sifir hiz.",
   {"boy": (1.6, 1.6, 1.6), "tip": "Box", "dogus": (3.0, 3.0, 0.05), "hedef": (0, 0.2, 0.02),
    "ivme": (0, 0, 0), "surtunme": (0.9, 0.9, 0.95)}),
  ("toz_zerreleri", "ent_amb_dust_motes", "toz", (0.80, 0.78, 0.72),
   {"oran": 5.0},
   "Isik huzmesindeki zerre: dikey sutun icinde neredeyse hareketsiz.",
   {"boy": (0.05, 0.05, 0.05), "tip": "Box", "dogus": (1.5, 1.5, 2.0), "hedef": (0.1, 0, 0.05),
    "surtunme": (0.9, 0.9, 0.9)}),
  ("tavan_damlamasi", "ent_amb_water_roof_drips", "damla", (0.70, 0.78, 0.84),
   {"oran": 2.5},
   "Tavandan tek tek damla: genis yassi dogus, dogrudan asagi, yercekimi.",
   {"boy": (0.09, 0.09, 0.09), "tip": "Box", "dogus": (1.5, 1.5, 0.02), "hedef": (0, 0, -3.0),
    "ivme": (0, 0, -15.0)}),
  ("buhar_bacasi", "ent_amb_steam_prison", "buhar", (0.90, 0.92, 0.94), {},
   "Baca: dar agiz, guclu dikey cikis.",
   {"boy": (0.7, 0.7, 0.7), "tip": "Cylinder", "dogus": (0.25, 0.05, 0.25), "hedef": (0, 0, 2.5),
    "ivme": (0, 0, 1.2), "surtunme": (0.2, 0.2, 0.05)}),
  # ⛔ `ent_amb_falling_leaves_*` KULLANILAMAZ: GTA'da yaprak SPRITE
  #    degil MESH'tir, dokusu yoktur ve transplant duser.
  ("kagit_savrulma", "ent_amb_falling_cherry_bloss", "kagit", (0.86, 0.84, 0.78),
   {"oran": 6.0},
   "Savrulan kagit: genis hacimde dogar, yana suruklenir, yavas duser.",
   {"boy": (0.22, 0.22, 0.22), "tip": "Box", "dogus": (3.0, 3.0, 2.0), "hedef": (1.5, 0.5, -0.3),
    "ivme": (0.2, 0.1, -0.8), "surtunme": (0.7, 0.7, 0.8)}),
  ("ucusan_kor", "ent_amb_fbi_cinder", "kor", (1.00, 0.58, 0.16), {},
   "Ucusan kor: dar kaynaktan yukari suzulur, hafifce savrulur.",
   {"boy": (0.06, 0.06, 0.06), "tip": "Cylinder", "dogus": (0.3, 0.1, 0.3), "hedef": (0, 0, 0.8),
    "ivme": (0.15, 0.1, 0.25)}),
 ],

 # ⛔ Katalogun yikim icin yazdigi 18 referansin HICBIRI kullanilamadi:
 #    hepsi cok emitterli. Bir carpma efekti dogasi geregi toz + kiymik +
 #    puf'tur. Tek emitterli 231 donor ISKELET olarak alindi, HAREKET
 #    ailenin kendi fiziginden yazildi.
 "yikim": [
  ("duvar_cokme", "ent_amb_fbi_smoke_land_hvy", "duman", (0.42, 0.39, 0.35), {},
   "Duvar yuzeyi boyunca dogan, yavas kabaran toz perdesi.",
   {"boy": (1.8, 1.8, 1.8), "tip": "Box", "dogus": (3.0, 0.3, 2.0), "hedef": (0, 0, 0.5),
    "ivme": (0, 0, 0.15), "surtunme": (0.7, 0.7, 0.8)}),
  # ⛔ Donorun dogus hacmi 5x5x1 m KUTU idi -- kiymik carpma noktasindan
  #    degil, 5 metrelik alana sacilarak doguyordu. Kucuk kureye cevrildi.
  ("beton_kirilma", "ent_ray_fam3_dust_motes", "beton", (0.58, 0.57, 0.55),
   {"omur": 1.2},
   "Carpma NOKTASINDAN patlayan kiymik; agir, hizla duser.",
   {"boy": (0.16, 0.16, 0.16), "tip": "Sphere", "dogus": (0.15, 0.15, 0.15), "hedef": (0, 0, 1.2),
    "ivme": (0, 0, -14.0), "surtunme": (0.2, 0.2, 0.1)}),
  ("tahta_kirilma", "ent_ray_fam3_dust_motes", "tahta", (0.55, 0.38, 0.20),
   {"omur": 1.6},
   "Tahta kiymigi betondan hafif: daha uzaga firlar, daha yavas duser.",
   {"boy": (0.2, 0.2, 0.2), "tip": "Sphere", "dogus": (0.2, 0.2, 0.2), "hedef": (0, 0, 1.5),
    "ivme": (0, 0, -9.0), "surtunme": (0.35, 0.35, 0.25)}),
  ("cam_kirilma", "ent_amb_falling_cherry_bloss", "cam", (0.82, 0.90, 0.94),
   {"omur": 1.4, "oran": 10.0},
   "Pencere DUZLEMINDEN dokulen cam; en agir dusus, kisa mesafe.",
   {"boy": (0.13, 0.13, 0.13), "tip": "Box", "dogus": (1.0, 0.05, 1.0), "hedef": (0, 0, -2.0),
    "ivme": (0, 0, -18.0), "surtunme": (0.1, 0.1, 0.05)}),
  ("metal_burulma", "ent_amb_fbi_cinder", "kivilcim", (1.00, 0.78, 0.42),
   {"omur": 0.9},
   "Yirtilma noktasindan firlayan kivilcim, yay cizerek duser.",
   {"boy": (0.09, 0.09, 0.09), "tip": "Sphere", "dogus": (0.1, 0.1, 0.1), "hedef": (0, 0, 0.6),
    "ivme": (0, 0, -6.0)}),
  ("siva_dokulme", "ent_amb_fbi_smoke_creep", "toz", (0.90, 0.89, 0.86), {},
   "Tavandan suzulen ince siva tozu: hafif, yavas iner.",
   {"boy": (0.35, 0.35, 0.35), "tip": "Box", "dogus": (1.0, 1.0, 0.05), "hedef": (0, 0, -1.5),
    "ivme": (0, 0, -6.0), "surtunme": (0.6, 0.6, 0.7)}),
  ("moloz_yagmuru", "ent_amb_falling_cherry_bloss", "beton", (0.48, 0.44, 0.40),
   {"oran": 4.0},
   "Tavan alanindan dusen enkaz: genis yassi dogus, uzun dusus.",
   {"boy": (0.26, 0.26, 0.26), "tip": "Box", "dogus": (4.0, 4.0, 0.2), "hedef": (0, 0, -8.0),
    "ivme": (0, 0, -16.0), "surtunme": (0.15, 0.15, 0.1)}),
  # ⛔ Donor `env_dust_devil_rural_lrg` -- TOZ SEYTANI. `ptxAttractorDomain`i
  #    (dis 20.6 / ic 6.8) parcaciklari iceri-yukari sarmaliyordu; oyunda
  #    HORTUM goruldu. Attractor sifirlanir, hedef zemine yatirilir.
  ("cokme_tozu", "env_dust_devil_rural_lrg", "duman", (0.66, 0.60, 0.50), {},
   "Hortum silindi; yerden ILERI yayilan agir toz duvari yazildi.",
   {"boy": (2.6, 2.6, 2.6), "tip": "Cylinder", "dogus": (2.0, 0.3, 2.0), "hedef": (0, 0, 0.4),
    "hedef_boy": (4.0, 0.3, 4.0), "ivme": (0, 0, 0.05),
    "surtunme": (0.85, 0.85, 0.9), "attractor_sil": True}),
  ("surtunme_kivilcimi", "ent_amb_fbi_cinder", "kivilcim", (1.00, 0.86, 0.55),
   {"oran": 14.0, "omur": 0.55},
   "metal_burulma ile ayni donor ama YON farkli: surtunme kivilcimi tek "
   "yone akar (hedef x=1.5), burulma dagilir.",
   {"boy": (0.07, 0.07, 0.07), "tip": "Sphere", "dogus": (0.06, 0.06, 0.06), "hedef": (1.5, 0, 0.3),
    "ivme": (0, 0, -8.0)}),
 ],
 # ⛔ Butun `exp_*` patlama efektleri COK EMITTERLI (cekirdek + halka + duman
 #    + parca). Tek emitterle patlamanin TAMAMI yapilamaz; her aile
 #    patlamanin EN OKUNUR parcasini temsil eder. Iskelet omur bandina gore
 #    secildi, hareket yazildi.
 "patlama": [
  ("el_bombasi", "weap_veh_turbulance_dirt", "alev_topu", (1.00, 0.72, 0.30), {},
   "Noktadan disa patlayan cekirdek; cok kisa omurlu iskelet (0.2-0.4 sn).",
   {"boy": (1.2, 1.2, 1.2), "tip": "Sphere", "dogus": (0.2, 0.2, 0.2), "hedef": (0, 0, 2.5),
    "ivme": (0, 0, 1.5), "surtunme": (0.6, 0.6, 0.6)}),
  ("roket", "liquid_splash_water", "alev_topu", (1.00, 0.66, 0.24),
   {"oran": 5.0},
   "RPG YONLUDUR: hedef x ekseninde 3 m -- cekirdek one uzar. "
   "Iskelet `liquid_splash_water`: petrol ikizi DEGIL -- petrol IKI "
   "doku ister (`ptfx_gloop_n` normal map + `ptfx_gloop` renk) ve "
   "tek sprite ikisine birden yazilinca shader yanlis isiklanir. "
   "Oran petrolun 5/sn degerinde tutuldu.",
   {"boy": (0.9, 0.9, 0.9), "tip": "Sphere", "dogus": (0.15, 0.15, 0.15), "hedef": (3.0, 0, 0.4),
    "ivme": (0, 0, -1.0), "surtunme": (0.5, 0.5, 0.5)}),
  ("yakit_varili", "bang_plastic", "ates", (1.00, 0.52, 0.14), {"oran": 30.0},
   "Varil: cekirdek degil SUREKLI yangin. Genis agiz, guclu yukselis.",
   {"boy": (1.6, 1.6, 1.6), "tip": "Cylinder", "dogus": (0.6, 0.1, 0.6), "hedef": (0, 0, 3.0),
    "ivme": (0, 0, 2.2), "surtunme": (0.4, 0.4, 0.3)}),
  ("arac_patlamasi", "weap_veh_turbulance_dirt", "beton", (0.45, 0.42, 0.40),
   {"omur": 1.6},
   "Arac patlamasi PARCALIDIR: metal/cam firlar, yay cizip duser.",
   {"boy": (0.24, 0.24, 0.24), "tip": "Sphere", "dogus": (0.5, 0.5, 0.5), "hedef": (0, 0, 4.0),
    "ivme": (0, 0, -8.0), "surtunme": (0.3, 0.3, 0.2)}),
  ("molotof", "bang_plastic", "ates", (1.00, 0.60, 0.18), {"oran": 22.0},
   "Molotof patlamaz, YAYILIR: genis yassi zemin alani, dusuk yukselis.",
   {"boy": (1.1, 1.1, 1.1), "tip": "Cylinder", "dogus": (1.5, 0.1, 1.5), "hedef": (0, 0, 0.8),
    "ivme": (0, 0, 1.0), "surtunme": (0.7, 0.7, 0.6)}),
  ("sok_dalgasi", "liquid_splash_water", "halka_ark", (0.96, 0.97, 1.00),
   {"oran": 12.0},
   "Flashbang ATESSIZ: beyaz, zeminde hizla genisleyen halka. hedef_boy "
   "genis, hedef neredeyse duz.",
   {"boy": (1.4, 1.4, 1.4), "tip": "Cylinder", "dogus": (0.2, 0.05, 0.2), "hedef": (0, 0, 0.05),
    "hedef_boy": (5.0, 0.05, 5.0), "ivme": (0, 0, 0),
    "surtunme": (0.9, 0.9, 0.9)}),
  ("hava_patlamasi", "ent_amb_fbi_smoke_linger_lt", "duman", (0.34, 0.32, 0.30),
   {},
   "Havada patlama: yerle temas yok, duman ASAGI sarkar (hedef z negatif).",
   {"boy": (1.6, 1.6, 1.6), "tip": "Sphere", "dogus": (1.0, 1.0, 1.0), "hedef": (0, 0, -0.6),
    "ivme": (0, 0, -0.3), "surtunme": (0.8, 0.8, 0.85)}),
  ("su_patlamasi", "ent_amb_bubble_stream", "kabarcik", (0.78, 0.88, 0.94),
   {"oran": 40.0, "omur": 2.5},
   "Su alti: kabarcik kubbesi yuzeye dogru sutun halinde cikar.",
   {"boy": (0.45, 0.45, 0.45), "tip": "Sphere", "dogus": (0.8, 0.8, 0.4), "hedef": (0, 0, 3.0),
    "ivme": (0, 0, 1.8), "surtunme": (0.5, 0.5, 0.4)}),
 ],

 # ⛔ `kalkan_kubbesi` BU PAKETTE YOK. Katalogun kendi ifadesiyle
 #    "partikulden cok yuzey isi -- mesh + shader gerekir". Partikulle
 #    taklidi kotu bir kubbe verir; dogru yol ayri bir mesh.
 "buyu": [
  ("buyu_toplanma", "ent_amb_elec_crackle", "parlama", (0.55, 0.72, 1.00),
   {"oran": 25.0},
   "ICE AKIS: genis hacimde dogar, hedef_boy KUCUK oldugu icin hepsi tek "
   "noktaya yonelir -- toplanma hissi boyle kurulur.",
   {"boy": (0.35, 0.35, 0.35), "tip": "Sphere", "dogus": (1.2, 1.2, 1.2), "hedef": (0, 0, 0),
    "hedef_boy": (0.05, 0.05, 0.05)}),
   # ⚠ `ent_amb_elec_crackle`ta Acceleration/Dampening/Rotation YOK.
   #    Elektrik/enerji cakmasi zaten ucmaz, yerinde parlar.
  ("rune_cemberi", "ent_amb_fbi_smoke_linger_lt", "notr_halka", (0.70, 0.55, 1.00),
   {"oran": 4.0, "omur": 3.0},
   "Yerde duran cember: yassi silindir, neredeyse sifir hiz, yuksek surtunme.",
   {"boy": (1.6, 1.6, 1.6), "tip": "Cylinder", "dogus": (1.5, 0.02, 1.5), "hedef": (0, 0, 0.02),
    "ivme": (0, 0, 0), "surtunme": (0.95, 0.95, 0.95)}),
  ("buyu_mermisi", "liquid_splash_water", "notr_kor", (0.60, 0.80, 1.00),
   {"oran": 35.0},  # omur override YOK: donor zaten 0.4-0.5 (ort 0.45)
   "Merminin IZI: cok kisa omur + dar dogus = arkada kalan cizgi.",
   {"boy": (0.12, 0.12, 0.12), "tip": "Sphere", "dogus": (0.08, 0.08, 0.08), "hedef": (0, 0, 0.1),
    "ivme": (0, 0, 0), "surtunme": (0.8, 0.8, 0.8)}),
  ("buyu_carpma", "weap_veh_turbulance_dirt", "yildiz", (0.72, 0.62, 1.00),
   {},
   "Carpma ani: noktadan yukari patlayan parlama, sonra dagilir.",
   {"boy": (0.9, 0.9, 0.9), "tip": "Sphere", "dogus": (0.15, 0.15, 0.15), "hedef": (0, 0, 1.8),
    "ivme": (0, 0, -2.0), "surtunme": (0.6, 0.6, 0.6)}),
  ("sifa_aurasi", "ent_amb_bubble_stream", "parlama", (0.65, 1.00, 0.85),
   {"oran": 9.0},
   "Karakteri saran YUKARI akis: dikey silindir, yumusak hiz.",
   {"boy": (0.3, 0.3, 0.3), "tip": "Cylinder", "dogus": (0.6, 1.0, 0.6), "hedef": (0, 0, 1.5),
    "ivme": (0, 0, 0.4), "surtunme": (0.6, 0.6, 0.5)}),
  ("isinlanma", "liquid_splash_water", "parlama", (0.85, 0.75, 1.00),
   {"oran": 60.0},
   "buyu_toplanma ile ayni ice-cokme mekanigi ama COK daha hizli ve genis "
   "-- kayboluş ani.",
   {"boy": (0.55, 0.55, 0.55), "tip": "Sphere", "dogus": (1.5, 1.5, 1.5), "hedef": (0, 0, 0),
    "hedef_boy": (0.03, 0.03, 0.03), "ivme": (0, 0, 0),
    "surtunme": (0.3, 0.3, 0.3)}),
  ("lanet_sisi", "ent_amb_fbi_smoke_linger_lt", "sis", (0.32, 0.20, 0.40),
   {"oran": 5.0},
   "Karakteri saran koyu agir sis: dar dikey silindir, neredeyse durgun.",
   {"boy": (1.1, 1.1, 1.1), "tip": "Cylinder", "dogus": (0.8, 1.2, 0.8), "hedef": (0, 0, 0.1),
    "ivme": (0, 0, 0), "surtunme": (0.9, 0.9, 0.92)}),
 ],

 "radyasyon": [
  ("radyoaktif_sis", "_fog_foundry", "sis", (0.55, 0.72, 0.45), {"oran": 5.0},
   "Yere coken agir hava: genis yassi kutu, neredeyse sifir hiz.",
   {"boy": (1.8, 1.8, 1.8), "tip": "Box", "dogus": (4.0, 4.0, 0.15), "hedef": (0, 0.2, 0.02),
    "ivme": (0, 0, 0), "surtunme": (0.95, 0.95, 0.95)}),
  ("varil_sizintisi", "liquid_splash_water", "damla", (0.62, 0.78, 0.30),
   {"oran": 3.0},
   "Devrilmis varilden akan sivi: dar agiz, dogrudan asagi, yercekimi.",
   {"boy": (0.1, 0.1, 0.1), "tip": "Box", "dogus": (0.15, 0.15, 0.02), "hedef": (0, 0, -0.8),
    "ivme": (0, 0, -9.8), "surtunme": (0.2, 0.2, 0.1)}),
  ("sicak_nokta", "ent_amb_elec_crackle", "yildiz", (0.75, 1.00, 0.45), {},
   "KESIKLI parlama: iskeletin kendi oran araligi 0.1-15 zaten duzensiz -- "
   "sayac sesiyle eslesen aralikliligi bu veriyor, oran override EDILMEDI.",
   {"boy": (0.1, 0.1, 0.1), "tip": "Sphere", "dogus": (0.1, 0.1, 0.1), "hedef": (0, 0, 0.2)}),
  ("serpinti", "ent_amb_falling_cherry_bloss", "kul", (0.62, 0.60, 0.58),
   {"oran": 8.0},
   "Kul yagisi: COK genis alan, yavas inis, hafif yanal suruklenme.",
   {"boy": (0.07, 0.07, 0.07), "tip": "Box", "dogus": (8.0, 8.0, 0.3), "hedef": (0.3, 0.2, -2.0),
    "ivme": (0, 0, -0.4), "surtunme": (0.85, 0.85, 0.9)}),
  ("cerenkov", "ent_amb_tnl_bubbles_lge", "parlama", (0.30, 0.70, 1.00),
   {"oran": 6.0},
   "Su alti mavi parlama: durgun, genis, cok yavas yukselen.",
   {"boy": (0.5, 0.5, 0.5), "tip": "Sphere", "dogus": (1.0, 1.0, 1.0), "hedef": (0, 0, 0.4),
    "ivme": (0, 0, 0.1), "surtunme": (0.9, 0.9, 0.9)}),
  ("bulasik_iz", "liquid_splash_water", "toz", (0.60, 0.75, 0.42),
   {"oran": 8.0},
   "Ayak izi tozu: kucuk, kisa omurlu, neredeyse hareketsiz.",
   {"boy": (0.14, 0.14, 0.14), "tip": "Sphere", "dogus": (0.12, 0.12, 0.12), "hedef": (0, 0, 0.15),
    "ivme": (0, 0, 0), "surtunme": (0.9, 0.9, 0.9)}),
 ],

 # ⛔ `isi_dalgalanmasi` BU PAKETTE YOK: katalog "partikul degil KIRILMA
 #    shader'i" diyor ve vanilla `ptfx_heathaze_n` bir normal-map dokusudur.
 #    Kendi sprite'imizla taklidi bulanik bir leke verir.
 # ⛔ `leke_yayilma`nin ASIL isi DECAL'dir; burada yalniz uzerindeki ince
 #    buhar var. Decal ayri hatta uretilir.
 "virus_ek": [
  ("sinek_bulutu", "ent_amb_fly_swarm", "sinek", (0.55, 0.52, 0.46),
   {"oran": 12.0, "omur": 5.0},
   "Ceset cevresinde donen kucuk koyu tane. Iskelet zaten sinek suru "
   "davranisinda; dogus hacmi cesedi saracak kadar kucultuldu.",
   {"boy": (0.05, 0.05, 0.05), "tip": "Sphere", # ⚠ Acceleration burada `m_strengthKFP` (skaler) varyanti; xyz
    #    yazilamaz. Dampening var, o yaziliyor.
    "dogus": (0.5, 0.5, 0.4), "hedef": (0, 0, 0.05),
    "surtunme": (0.6, 0.6, 0.6)}),
  ("leke_yayilma", "ent_amb_exhaust_thin", "buhar", (0.50, 0.55, 0.42),
   {"oran": 1.5, "omur": 6.0},
   "Zemindeki lekenin uzerinden yukselen COK ince buhar; leke decal ile.",
   {"boy": (0.4, 0.4, 0.4), "tip": "Box", "dogus": (0.8, 0.8, 0.02), "hedef": (0, 0, 0.15),
    "ivme": (0, 0, 0), "surtunme": (0.95, 0.95, 0.95)}),
  ("bocek_surusu", "ent_amb_moths_swarm", "sinek", (0.62, 0.56, 0.48),
   {"oran": 10.0},
   "Lamba alti/coplukte donen bulut; sinek_bulutundan daha genis ve seyrek.",
   {"boy": (0.06, 0.06, 0.06), "tip": "Sphere", "dogus": (0.7, 0.7, 0.6), "hedef": (0, 0, 0.1),
    "ivme": (0, 0, 0), "surtunme": (0.6, 0.6, 0.6)}),
 ],

 "elektrik": [
  ("duz_ark", "ent_amb_elec_crackle", "ark_duz", (0.70, 0.85, 1.00), {},
   "Iki nokta arasi kisa cizgi: cok dar dogus, iskeletin duzensiz orani "
   "yanip sonmeyi zaten veriyor.",
   {"boy": (0.55, 0.55, 0.55), "tip": "Sphere", "dogus": (0.05, 0.05, 0.05), "hedef": (0, 0, 0.1)}),
  ("catalli_yildirim", "ent_amb_fbi_live_wires", "elektrik",
   (0.75, 0.82, 1.00), {"oran": 8.0},
   "Duz arktan farki KAPSAMA: dogus hacmi 6 kat genis, dallanma hissi "
   "boyle kuruluyor.",
   {"boy": (0.9, 0.9, 0.9), "tip": "Sphere", "dogus": (0.3, 0.3, 0.3), "hedef": (0, 0, 0.3)}),
  ("ark_carpmasi", "bul_stungun", "yildiz", (0.92, 0.96, 1.00),
   {"oran": 20.0, "omur": 0.5},
   "Arkin hedefe vurdugu an: keskin beyaz parlama, hizli soner.",
   {"boy": (0.6, 0.6, 0.6), "tip": "Sphere", "dogus": (0.12, 0.12, 0.12), "hedef": (0, 0, 0.8),
    "ivme": (0, 0, -3.0), "surtunme": (0.5, 0.5, 0.5)}),
  ("kivilcim_yagmuru", "liquid_splash_water", "kivilcim", (1.00, 0.80, 0.40),
   {"oran": 18.0, "omur": 1.0},
   "Kopmus kablodan DOKULEN kivilcim: yassi dogus, guclu yercekimi.",
   {"boy": (0.08, 0.08, 0.08), "tip": "Box", "dogus": (0.4, 0.4, 0.05), "hedef": (0, 0, -2.5),
    "ivme": (0, 0, -12.0), "surtunme": (0.25, 0.25, 0.15)}),
  ("kisa_devre", "ent_amb_elec_crackle", "elektrik", (0.65, 0.78, 1.00),
   {"oran": 6.0},
   "Panel kisa devresi: duz arktan genis, catalli yildirimdan dar; "
   "aralikli.",
   {"boy": (0.45, 0.45, 0.45), "tip": "Sphere", "dogus": (0.15, 0.15, 0.15), "hedef": (0, 0, 0.25)}),
  ("emp_dalgasi", "liquid_splash_water", "halka_ark", (0.40, 0.70, 1.00),
   {"oran": 15.0},
   "Hizla genisleyen mavi halka: sok_dalgasi ile ayni mekanik, daha genis "
   "hedef_boy (6 m) ve mavi.",
   {"boy": (1.6, 1.6, 1.6), "tip": "Cylinder", "dogus": (0.15, 0.05, 0.15), "hedef": (0, 0, 0.03),
    "hedef_boy": (6.0, 0.05, 6.0), "ivme": (0, 0, 0),
    "surtunme": (0.9, 0.9, 0.9)}),
  ("tesla_kubbe", "ent_amb_elec_crackle", "elektrik", (0.60, 0.80, 1.00),
   {"oran": 20.0},
   "Merkezden CEVREYE atlayan arklar: dar dogus ama GENIS hedef_boy -- "
   "her parcacik baska yone gider.",
   {"boy": (0.7, 0.7, 0.7), "tip": "Sphere", "dogus": (0.1, 0.1, 0.1), "hedef": (0, 0, 0.6),
    "hedef_boy": (1.5, 1.5, 1.5)}),
 ],

 "ortak": [
  ("carpma_tozu", "weap_veh_turbulance_dirt", "toz", (0.68, 0.64, 0.58),
   {"omur": 0.9},
   "Herhangi bir seyin yuzeye vurmasi: noktadan yukari puskurup coker.",
   {"boy": (0.55, 0.55, 0.55), "tip": "Sphere", "dogus": (0.2, 0.2, 0.2), "hedef": (0, 0, 1.0),
    "ivme": (0, 0, -3.0), "surtunme": (0.6, 0.6, 0.6)}),
  ("ayak_tozu", "liquid_splash_water", "toz", (0.72, 0.68, 0.62),
   {"oran": 4.0},
   "⚠ Ayak tozu ZAYIF olmali; yoksa ped duman cikarir. Oran ve hedef "
   "kasten dusuk.",
   {"boy": (0.3, 0.3, 0.3), "tip": "Sphere", "dogus": (0.15, 0.15, 0.1), "hedef": (0, 0, 0.35),
    "ivme": (0, 0, -1.0), "surtunme": (0.8, 0.8, 0.8)}),
  ("su_sicramasi", "ent_amb_drain_splash", "sicrama", (0.80, 0.88, 0.92),
   {"oran": 25.0},
   "Tac seklinde sicrama: dar halka agzindan yukari, sonra yercekimiyle "
   "geri duser.",
   {"boy": (0.3, 0.3, 0.3), "tip": "Cylinder", "dogus": (0.25, 0.05, 0.25), "hedef": (0, 0, 1.6),
    "ivme": (0, 0, -12.0), "surtunme": (0.3, 0.3, 0.2)}),
  ("namlu_alevi", "weap_veh_turbulance_dirt", "ates", (1.00, 0.82, 0.45),
   {"oran": 40.0},
   "Namlu alevi COK kisa ve YONLU: hedef x ekseninde, dogus cok dar.",
   {"boy": (0.3, 0.3, 0.3), "tip": "Sphere", "dogus": (0.06, 0.06, 0.06), "hedef": (0.8, 0, 0),
    "ivme": (0, 0, 0), "surtunme": (0.5, 0.5, 0.5)}),
  ("egzoz_dumani", "ent_amb_exhaust_thin", "duman", (0.55, 0.55, 0.56), {},
   "Surekli ince egzoz: dar agiz, hafif yukselis.",
   {"boy": (0.45, 0.45, 0.45), "tip": "Cylinder", "dogus": (0.1, 0.05, 0.1), "hedef": (0, 0, 0.6),
    "ivme": (0, 0, 0.25), "surtunme": (0.7, 0.7, 0.7)}),
 ],

 # ⛔ YILDIRIM BUYUSU -- uc asamali tek senaryo (firlatma / temas / son aksiyon).
 #    "Hizadan hedefe gitme" kismi PARTIKUL DEGIL: partikul tek noktada
 #    dogar. Yol alan ark, isin boyunca sirayla serpilen kisa omurlu
 #    segmentlerle cizilir (script tarafi). Bu yuzden `yildirim_kolu`
 #    0.10-0.16 sn omurlu -- serpildigi yerde cakip soner.
 "yildirim": [
  ("yildirim_kolu", "ent_amb_elec_crackle", "elektrik", (0.62, 0.80, 1.00),
   {"oran": 90.0, "omur": 0.13},
   "Isin boyunca serpilen catalli ark segmenti. COK kisa omurlu: segment "
   "cakip sonmeli, yoksa isin boyunca kalici bir cizgi kalir. Donorun "
   "duzensiz orani (0.1-15) cakma hissini zaten veriyor.",
   {"tip": "Sphere", "boy": (1.15, 1.15, 1.15), "dogus": (0.18, 0.18, 0.18),
    "hedef": (0, 0, 0.05), "tek_atim": True,
    "zarf": [(0.0, 0.9), (0.4, 1.0), (1.0, 0.0)]}),

  ("yildirim_parlama", "bul_stungun", "yildiz", (0.88, 0.94, 1.00),
   {"oran": 120.0, "omur": 0.28},
   "Carpma anindaki beyaz cakma. Kisa ve parlak; kivilcimdan ONCE biter "
   "ki goz once vurusu, sonra sacilmayi okusun.",
   {"tip": "Sphere", "boy": (1.30, 1.30, 1.30), "dogus": (0.10, 0.10, 0.10),
    "hedef": (0, 0, 0.25), "ivme": (0, 0, -1.0), "surtunme": (0.6, 0.6, 0.6),
    "tek_atim": True, "zarf": [(0.0, 1.0), (0.25, 1.0), (1.0, 0.0)]}),

  # ⛔ Donor `water_splash_veh_out`: omur 1.1-1.6 sn ve Acceleration +
  #    Dampening + Rotation + Size birimlerinin DORDU de var. Kisa omurlu
  #    kivilcim donorlerinde (0.2-0.4 sn) kivilcim havada yay cizmeye
  #    firsat bulamiyor.
  ("yildirim_kivilcim", "water_splash_veh_out", "kivilcim", (1.00, 0.82, 0.45),
   {"oran": 260.0, "omur": 1.45},
   "Carpma noktasindan CEVREYE sacilip yercekimiyle inen kivilcim. "
   "`hedef_boy` genis -> her parcacik baska yone firlar; `ivme` -9 -> yay "
   "cizerek duser; surtunme dusuk -> hizini korur.",
   # ⚠ Ilk degerler COK YAVASTI: hedef 1.1 m / 1.45 sn = 0.76 m/s, yanal
   #   +-1.1 m/s. Kivilcim havada yay cizemedi, carpma noktasinda kumelendi.
   #   Gercek kivilcim 5-15 m/s firlar; hedef ve hedef_boy buyutuldu.
   {"tip": "Sphere", "boy": (0.075, 0.075, 0.075), "dogus": (0.10, 0.10, 0.10),
    # ⚠ 14 m'lik yayilim kivilcimlari 7 m oteye firlatti ve kadraji
    #   tamamen terk ettiler. Carpma kivilcimi 2-3 m'de kalmali.
    "hedef": (0, 0, 2.2), "hedef_boy": (6.5, 6.5, 3.5),
    # ⚠ Yercekimi -9 ile 1.45 sn'de 9 m dusuyorlardi (zeminin cok altina).
    #   -4.5 ile ~2.7 m -- carpma yuksekliginden zemine makul bir yay.
    "ivme": (0, 0, -4.5), "surtunme": (0.18, 0.18, 0.12), "tek_atim": True,
    # kivilcim omrunun cogunda PARLAK kalir, sonda soner
    "zarf": [(0.0, 1.0), (0.55, 0.95), (0.85, 0.55), (1.0, 0.0)]}),
 ],
}


def ps(*a):
    return subprocess.run(list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


# ⛔ ANIMASYON ZARFI ONARIMI -- bu adim atlanirsa parcacik "yapistirma" gorunur.
#
# Sayfa dilimlemesi custom `.ypt`de calismadigi icin (referans §1e) tek kare
# sprite kullaniyoruz. Vanilla donorlerin bir kismi hareketini DOKUDAN
# aliyordu: `ent_amb_dry_ice_vent` alfa zarfi tek keyframe (sabit 0.5) ama
# dokusu `ptfx_smoke_wispy_anim`, yani animasyonlu sayfa. Dokuyu statikle
# degistirince o efektte degisen HICBIR SEY kalmiyor -- parcacik tam alfayla
# beliriyor ve tam alfayla yok oluyor.
#
# Olculdu: 231 uygun donorun 20'si sabit alfa, 14'u sonda alfa>0 ile
# "poplayarak" bitiyor -- toplam %14,7. Vanilla particle rule'larin
# **%88,2**'si t=1'de alfayi 0'a indirir; olcut budur.
#
# `KeyFrameMultiplier` alani olculdu: `1 / (t[i] - t[i-1])`, ilk karede 0.
KFP_ZARF = ("ptxu_Colour:m_rgbaMinKFP", "ptxu_Colour:m_rgbaMaxKFP")


def _kare(t, mult, r, g, b, al):
    return ("       <Item>\n"
            "        <InterpolationInterval value=\"%g\" />\n"
            "        <KeyFrameMultiplier value=\"%g\" />\n"
            "        <RedChannelColour value=\"%g\" />\n"
            "        <GreenChannelColour value=\"%g\" />\n"
            "        <BlueChannelColour value=\"%g\" />\n"
            "        <AlphaChannelColour value=\"%g\" />\n"
            "       </Item>\n" % (t, mult, r, g, b, al))


def zarf_onar(s):
    """Bozuk alfa zarfini vanilla seklinde yeniden yazar. (metin, notlar)"""
    notlar = []

    def duzelt(m):
        bas, govde, son = m.group(1), m.group(2), m.group(3)
        kf = re.findall(
            r"<InterpolationInterval value=\"([-0-9.eE]+)\" />\s*"
            r"<KeyFrameMultiplier value=\"[-0-9.eE]+\" />\s*"
            r"<RedChannelColour value=\"([-0-9.eE]+)\" />\s*"
            r"<GreenChannelColour value=\"([-0-9.eE]+)\" />\s*"
            r"<BlueChannelColour value=\"([-0-9.eE]+)\" />\s*"
            r"<AlphaChannelColour value=\"([-0-9.eE]+)\" />", govde)
        if not kf:
            return m.group(0)
        alfa = [float(x[4]) for x in kf]
        tepe = max(alfa)
        bozuk = len(kf) < 2 or alfa[-1] > 0.02
        if not bozuk or tepe <= 0:
            return m.group(0)
        r, g, b = (float(kf[0][1]), float(kf[0][2]), float(kf[0][3]))
        # ⚠ Donorun ANI BELIRME tercihini koru: vanilla'nin yalniz %44,7'si
        #   alfayi 0'dan baslatir; kivilcim/kor ani belirmeli. Yalnizca
        #   sondaki pop giderilir.
        if alfa[0] <= 0.02:
            nok = [(0.0, 0.0), (0.1, tepe), (0.8, tepe), (1.0, 0.0)]
        else:
            nok = [(0.0, tepe), (0.75, tepe), (1.0, 0.0)]
        yeni = ""
        for i, (t, al) in enumerate(nok):
            mult = 0.0 if i == 0 else 1.0 / (t - nok[i - 1][0])
            yeni += _kare(t, mult, r, g, b, al)
        notlar.append("zarf onarildi: %d kare -> %d, tepe %.3g"
                      % (len(kf), len(nok), tepe))
        return bas + "\n" + yeni + "      " + son

    for ad in KFP_ZARF:
        s = re.sub(r"(<Name>%s</Name>.*?<Keyframes>)(.*?)(</Keyframes>)"
                   % re.escape(ad), duzelt, s, count=1, flags=re.S)
    return s, notlar


def kur(aile, donor, sprite, renk, ovr, neden, hareket, dizin):
    ad = "my_" + aile
    # ⛔ SPRITE'I PAYLASMA -- HER AILEYE KENDI TOHUMU.
    #    Onceki surum `my_<sprite>.dds`yi kopyaliyordu: `duman`,
    #    `cokme_tozu`, `duvar_cokme`, `egzoz_dumani`, `hava_patlamasi`
    #    PIKSEL PIKSEL ayni cikti. Ayni ureticiyi farkli tohum ve farkli
    #    omur ani (`t`) ile cagirmak, ayni MALZEMEYI koruyup deseni
    #    ayirir: duman duman kalir ama iki puf ayni olmaz.
    # ⛔ KENNEY CC0 DOKULARI EN YUKSEK ONCELIK. Sektorun kendi tavsiyesi
    #    (realtimevfx.com): once HAZIR PAKET, sonra photo-bashing, en son
    #    prosedurel. Kenney gri tonlamali + saydam + sprite basina tek
    #    nesne -- bizim olctugumuz uc kuralin ucunu birden sagliyor.
    #    Lisans CC0: ticari kullanim serbest, atif zorunlu degil.
    KEN = {
        'arac_patlamasi': 'explosion07',
        'ark_carpmasi': 'star_07',
        'ayak_tozu': 'whitePuff01',
        'bocek_surusu': 'dirt_02',
        'buhar_bacasi': 'whitePuff18',
        'bulasik_iz': 'smoke_02',
        'bulasma_dalgasi': 'twirl_02',
        'buyu_carpma': 'star_08',
        'buyu_mermisi': 'trace_04',
        'buyu_toplanma': 'magic_02',
        'carpma_tozu': 'whitePuff15',
        'catalli_yildirim': 'spark_02',
        'cerenkov': 'light_03',
        'cokme_tozu': 'blackSmoke20',
        'cozunme_sivisi': 'scorch_03',
        'duvar_cokme': 'blackSmoke09',
        'duz_ark': 'spark_05',
        'egzoz_dumani': 'smoke_04',
        'el_bombasi': 'explosion04',
        'emp_dalgasi': 'circle_03',
        'hava_patlamasi': 'blackSmoke14',
        'isinlanma': 'flash04',
        'kagit_savrulma': 'scratch_01',
        'kan_sisi': 'scorch_02',
        'kimyasal_buhar': 'whitePuff12',
        'kisa_devre': 'spark_03',
        'kivilcim_yagmuru': 'spark_06',
        'lanet_sisi': 'blackSmoke04',
        'leke_yayilma': 'whitePuff08',
        'metal_burulma': 'spark_01',
        'molotof': 'flame_04',
        'namlu_alevi': 'muzzle_01',
        'radyoaktif_sis': 'smoke_10',
        'roket': 'muzzle_03',
        'rune_cemberi': 'magic_03',
        'serpinti': 'dirt_03',
        'sicak_nokta': 'star_06',
        'sifa_aurasi': 'light_02',
        'sinek_bulutu': 'dirt_01',
        'siva_dokulme': 'whitePuff03',
        'sok_dalgasi': 'circle_02',
        'spor_bulutu': 'whitePuff05',
        'su_patlamasi': 'whitePuff21',
        'su_sicramasi': 'whitePuff23',
        'surtunme_kivilcimi': 'spark_07',
        'tavan_damlamasi': 'circle_05',
        'tesla_kubbe': 'spark_04',
        'toz_zerreleri': 'whitePuff02',
        'ucusan_kor': 'star_04',
        'varil_sizintisi': 'scorch_01',
        'yakit_varili': 'fire_01',
        'yildirim_kivilcim': 'spark_07',
        'yildirim_kolu': 'spark_02',
        'yildirim_parlama': 'star_08',
        'zemin_sisi': 'smoke_09',
    }
    if aile in KEN:
        png = os.path.join(dizin, ad + ".png")
        dds = os.path.join(dizin, ad + ".dds")
        rk = ps(sys.executable, os.path.join(BETIK, "ptfx_kenney.py"),
                "--ad", KEN[aile], "--cikti", png, "--coz", str(COZ))
        if os.path.exists(png):
            ps(sys.executable, os.path.join(BETIK, "make_dds.py"), dds,
               "--kaynak", png, "--format", "DXT5")
            if os.path.exists(dds):
                return _kur_devam(aile, donor, renk, ovr, neden, hareket, dizin, ad)
        return "kenney doku alinamadi: %s" % (rk.stdout + rk.stderr).strip()[-160:]

    # BLENDER ENERJI/SIVI: parlama ve sivi de render'dan gelir.
    #    ⛔ Enerjide okunan sey GEOMETRI DEGIL ISIK: emissive + bloom.
    #       Sivida yuzey gerilimi metaball ile kurulur. Numpy ile ikisi de
    #       "cizilmis leke" gibi duruyordu.
    BE = {
        "halka": "halka", "notr_halka": "halka", "halka_organik": "halka",
        "halka_ark": "emp", "yildiz": "yildiz", "parlama": "kure",
        "kor": "kure", "ark_duz": "ark", "elektrik": "ark",
        "damla": "damla", "sicrama": "sicrama", "kabarcik": "tac",
        "kan": "kan", "alev_topu": "kure",
    }
    if sprite in BE:
        png = os.path.join(dizin, ad + ".png")
        dds = os.path.join(dizin, ad + ".dds")
        tohum_bl = zlib.crc32(aile.encode("utf-8")) % 9973
        rb = ps(sys.executable, os.path.join(BETIK, "ptfx_blender_enerji.py"),
                "--tur", BE[sprite], "--cikti", png,
                "--coz", str(COZ), "--tohum", str(tohum_bl))
        if os.path.exists(png):
            ps(sys.executable, os.path.join(BETIK, "make_dds.py"), dds,
               "--kaynak", png, "--format", "DXT5")
            if os.path.exists(dds):
                return _kur_devam(aile, donor, renk, ovr, neden, hareket, dizin, ad)
        return "blender enerji render olmadi: %s" % (rb.stdout + rb.stderr).strip()[-160:]

    # BLENDER RENDER: kati parcalar numpy ile degil 3B render'la uretilir.
    #    ⛔ Olculdu/arastirildi: vanilla'nin enkaz atlaslari 3B/fotograf
    #       kaynakli; hesaplanan siluet profesyonel durmuyor. Isikli,
    #       fasetli, golgeli parca ancak render'dan cikar.
    BL = {"beton": "beton", "cam": "cam", "tahta": "tahta", "kagit": "kagit",
          "parca": "beton"}
    if sprite in BL:
        png = os.path.join(dizin, ad + ".png")
        dds = os.path.join(dizin, ad + ".dds")
        tohum_bl = zlib.crc32(aile.encode("utf-8")) % 9973
        rb = ps(sys.executable, os.path.join(BETIK, "ptfx_blender_render.py"),
                "--malzeme", BL[sprite], "--cikti", png,
                "--coz", str(COZ), "--tohum", str(tohum_bl))
        if os.path.exists(png):
            r0 = ps(sys.executable, os.path.join(BETIK, "make_dds.py"), dds,
                    "--kaynak", png, "--format", "DXT5")
            if os.path.exists(dds):
                return _kur_devam(aile, donor, renk, ovr, neden, hareket, dizin, ad)
        return "blender render olmadi: %s" % (rb.stdout + rb.stderr).strip()[-160:]

    # DIS GORSEL: kullanicinin ChatGPT'ye urettirdigi sprite'lar oncelikli.
    #    Proseduerel uretim yalniz dis gorseli OLMAYAN aileler icin.
    #    (Kural §12: gorsel uretimini modele birakma -- kullanici uretti.)
    dis = os.path.join(SPRITE, "gpt_%s.png" % aile)
    if os.path.exists(dis):
        dds = os.path.join(dizin, ad + ".dds")
        r0 = ps(sys.executable, os.path.join(BETIK, "make_dds.py"), dds,
                "--kaynak", dis, "--format", "DXT5")
        if not os.path.exists(dds):
            return "dis gorsel dds olmadi: %s" % (r0.stdout + r0.stderr).strip()[-160:]
        return _kur_devam(aile, donor, renk, ovr, neden, hareket, dizin, ad)
    tohum = zlib.crc32(aile.encode("utf-8")) & 0x7FFFFFFF
    t = 0.30 + 0.32 * (((tohum >> 7) % 1000) / 1000.0)
    notr = sprite.startswith("notr_")
    uretici = sprite[5:] if notr else sprite
    if uretici not in ptfx_sayfa.AILE:
        return "sprite uretici yok: %s" % uretici
    png = os.path.join(dizin, ad + ".png")
    dds = os.path.join(dizin, ad + ".dds")
    try:
        tekil = uretici in getattr(ptfx_sayfa, 'TEKIL', set())
        ptfx_sayfa.yaz(
            ptfx_sayfa.tek_kare(uretici, COZ, t, tohum, notr, tekil), png)
    except Exception as e:
        return "sprite uretilemedi: %s" % e
    r0 = ps(sys.executable, os.path.join(BETIK, "make_dds.py"), dds,
            "--kaynak", png, "--format", "DXT5")
    if not os.path.exists(dds):
        return "dds uretilemedi: %s" % (r0.stdout + r0.stderr).strip()[-160:]
    return _kur_devam(aile, donor, renk, ovr, neden, hareket, dizin, ad)


def _kur_devam(aile, donor, renk, ovr, neden, hareket, dizin, ad):
    cmd = [sys.executable, os.path.join(BETIK, "ypt_transplant.py"), VANILLA,
           "--efekt", donor, "--yeni-ad", ad, "--doku", ad, "--klasor", dizin,
           "--renk", str(renk[0]), str(renk[1]), str(renk[2])]
    for k, bayrak in (("omur", "--omur"), ("oran", "--oran"),
                      ("boyut", "--boyut-olcek"), ("carpan", "--boyut-carpan")):
        if k in ovr:
            cmd += [bayrak, str(ovr[k])]
    r = ps(*cmd)
    xml = os.path.join(dizin, ad + ".ypt.xml")
    if not os.path.exists(xml):
        return (r.stdout + r.stderr).strip().splitlines()[-1:] or ["transplant basarisiz"]

    s = io.open(xml, encoding="utf-8").read()
    s = re.sub(r'(<Type value="AnimateTexture" />\s*<UnknownC0 value="\d+" />\s*'
               r'<UnknownC4 value=")\d+(")', r"\g<1>0\g<2>", s, count=1)
    s = re.sub(r"<FxcTechnique>RGB_(\w+)</FxcTechnique>",
               r"<FxcTechnique>RGBA_\1</FxcTechnique>", s)
    s, zn = zarf_onar(s)
    if hareket:
        s, hn = ptfx_hareket.uygula_belge(s, hareket)
        zn += hn
        # ⛔ YAZILAMAYAN HAREKET = HATA. Donorun particle rule'unda o
        #    davranis birimi yoksa (olculdu: Acceleration ve Dampening
        #    donorlerin yalniz %77'sinde, ucu birden %50'sinde var) alan
        #    sessizce yazilmaz ve efekt donorun hareketiyle kalir --
        #    duzeltmek istedigimiz kusurun ta kendisi. Uyari degil, hata.
        eksik = [x for x in hn if "YAZILAMADI" in x]
        if eksik:
            return "donor bu hareketi tasimiyor: " + "; ".join(eksik)
    ET.fromstring(s)
    io.open(xml, "w", encoding="utf-8").write(s)
    ps("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
       os.path.join(BETIK, "ypt_xml_to_bin.ps1"), "-Xml", xml)
    if not os.path.exists(os.path.join(dizin, ad + ".ypt")):
        return "derlenmedi"
    return ("", zn) if zn else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grup", default="virus_ambiyans")
    a = ap.parse_args()
    if a.grup not in GRUPLAR:
        raise SystemExit("grup yok: %s (%s)" % (a.grup, ", ".join(GRUPLAR)))
    os.makedirs(CIKTI, exist_ok=True)
    n, hata = 0, []
    for aile, donor, sprite, renk, ovr, neden, hareket in GRUPLAR[a.grup]:
        h = kur(aile, donor, sprite, renk, ovr, neden, hareket, CIKTI)
        zn = []
        if isinstance(h, tuple):
            h, zn = h
        if h:
            hata.append((aile, h))
            print("  HATA  %-18s %s" % (aile, h))
        else:
            n += 1
            ek = ("  [%s]" % ", ".join("%s=%s" % kv for kv in ovr.items())) if ovr else ""
            print("  kuruldu %-18s <- %-28s%s" % (aile, donor, ek))
            # ⛔ Dongu degiskenini `n` yapma -- disaridaki basari sayaci `n`
            #    eziliyor ve build ilk onarimdan sonra `n += 1` ile coker.
            for msj in zn:
                print("           ! %s" % msj)
    print("\nkurulan: %d / %d" % (n, len(GRUPLAR[a.grup])))
    return 0 if not hata else 1


if __name__ == "__main__":
    raise SystemExit(main())
