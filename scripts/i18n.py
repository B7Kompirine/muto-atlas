#!/usr/bin/env python3
"""i18n.py — muto-atlas cikti dili (tr / en).

Dil su sirayla belirlenir (ilk bulunan kazanir):
  1. --lang bayragi          (arac calistirilirken)
  2. MUTO_ATLAS_LANG cevre degiskeni
  3. data/config.json -> "lang"
  4. varsayilan: en

NEDEN VARSAYILAN EN
-------------------
Depo herkese aciktir; ilk calistiranin Turkce bilmesini varsayamayiz.
Turkce isteyen bir kez `--lang tr --save` der ve bir daha ugrasmaz.

KULLANIM
--------
    from i18n import t, set_lang
    print(t("layer_missing", file="archetypes.tsv.gz"))

Anahtar bulunamazsa ANAHTARIN KENDISI dondurulur — cikti bozulmaz, eksik
ceviri de gorunur olur. Sessizce bos string dondurmek, eksik cevirinin
fark edilmemesine yol acardi.
"""
from __future__ import annotations

import json
import os

_LANG = None
_DEFAULT = "en"

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
CONFIG = os.path.join(DATA, "config.json")

MESAJ = {
    # --- cikis kodlari / katman ---
    "layer_missing": {
        "tr": "{file} yok. Uret: {cmd}",
        "en": "{file} not found. Build it with: {cmd}",
    },
    "layer_missing_hint": {
        "tr": "Bu katman kurulu degil - sonuc hakkinda HICBIR SEY iddia edilemez.",
        "en": "This layer is not installed - NOTHING can be claimed about the result.",
    },
    "internal_error": {"tr": "IC HATA", "en": "INTERNAL ERROR"},
    "not_found": {"tr": "BULUNAMADI", "en": "NOT FOUND"},

    # --- ortak cikti ---
    "results": {"tr": "{n} sonuc", "en": "{n} result(s)"},
    "hidden": {"tr": " ({n} gosterilmedi, --limit ile artir)",
               "en": " ({n} hidden, raise --limit)"},
    "note": {"tr": "Not", "en": "Note"},
    "usage": {"tr": "Kullanim", "en": "Usage"},
    "tip": {"tr": "Ipucu", "en": "Tip"},

    # --- envanter ---
    "inventory": {"tr": "KATMAN ENVANTERI", "en": "LAYER INVENTORY"},
    "inv_present": {"tr": "VAR", "en": "OK "},
    "inv_missing": {"tr": "YOK", "en": "-- "},
    "inv_missing_note": {
        "tr": "bu katmani kullanan sorgular EXIT 2 doner",
        "en": "queries using this layer will return EXIT 2",
    },
    "inv_installed": {"tr": "{n}/{t} katman kurulu", "en": "{n}/{t} layers installed"},
    "inv_missing_count": {"tr": ", {n} EKSIK", "en": ", {n} MISSING"},
    "dump_version": {"tr": "dump surumu", "en": "dump version"},
    "built_at": {"tr": "uretim", "en": "built"},

    # --- ped ---
    "ped_clipdict": {"tr": "klip sozlugu", "en": "clip dictionary"},
    "ped_expr": {"tr": "expression", "en": "expression"},
    "ped_movement": {"tr": "movement clipset", "en": "movement clipset"},
    "ped_strafe": {"tr": "strafe / jest", "en": "strafe / gesture"},
    "ped_face": {"tr": "yuz viseme/grup", "en": "face viseme/group"},
    "ped_props": {"tr": "prop seti", "en": "prop set"},
    "ped_voice": {"tr": "ses grubu", "en": "voice group"},
    "ped_bones": {"tr": "kemik", "en": "bones"},
    "ped_clipset_note": {
        "tr": ("movementClipSet bir .ycd SOZLUGU OLMAK ZORUNDA DEGIL - 1109 pedin\n"
               "     100 benzersiz clipset degerinin yalniz 37'si gercek sozluktur."),
        "en": ("movementClipSet is NOT necessarily a .ycd dictionary - of the 100 unique\n"
               "     clipset values across 1109 peds, only 37 are real dictionaries."),
    },

    # --- silah ---
    "wpn_category": {"tr": "kategori/hasar", "en": "category/damage"},
    "wpn_model": {"tr": "model", "en": "model"},
    "wpn_ammo": {"tr": "mermi", "en": "ammo"},
    "wpn_dlc_tint": {"tr": "dlc / tint", "en": "dlc / tint"},
    "wpn_components": {"tr": "bilesen", "en": "components"},
    "wpn_no_model": {"tr": "- (model yok: yumruk vb.)", "en": "- (no model: melee/unarmed)"},
    "wpn_parts_tip": {
        "tr": "bilesen/livery adlari icin --parcalar",
        "en": "use --parts to list component and livery names",
    },
    "wpn_livery_note": {
        "tr": ("livery adlari da COMPONENT_* biciminde ve\n"
               "       GiveWeaponComponentToPed onlari KABUL EDER."),
        "en": ("livery names are also COMPONENT_* and\n"
               "       GiveWeaponComponentToPed ACCEPTS them."),
    },

    # --- arac ---
    "veh_class": {"tr": "sinif/tip", "en": "class/type"},
    "veh_seats": {"tr": "koltuk", "en": "seats"},
    "veh_wheels": {"tr": "teker", "en": "wheels"},
    "veh_dlc_price": {"tr": "dlc / fiyat", "en": "dlc / price"},

    # --- mlo / ipl / dunya ---
    "mlo_unplaced": {
        "tr": "YERLESTIRILMEMIS (tanimli ama hicbir ymap'te konumu yok)",
        "en": "NOT PLACED (defined but has no position in any ymap)",
    },
    "mlo_locations": {"tr": "{n} konum", "en": "{n} location(s)"},
    "mlo_more": {"tr": "... {n} konum daha (--konum ile artir)",
                 "en": "... {n} more location(s) (raise --locations)"},
    "mlo_interiors": {"tr": "{n} ic mekan", "en": "{n} interior(s)"},
    "mlo_variant_note": {
        "tr": ("ayni ic mekanin birden fazla MLO SURUMU olabilir\n"
               "     (Fleeca: v_genbank + hei_generic_bank_dlc). Hepsini yamala."),
        "en": ("the same interior can have MULTIPLE MLO VERSIONS\n"
               "     (Fleeca: v_genbank + hei_generic_bank_dlc). Patch all of them."),
    },
    "ipl_usage": {
        "tr": "RequestIpl('<ad>') / RemoveIpl('<ad>') - ad birebir yazilmali.",
        "en": "RequestIpl('<name>') / RemoveIpl('<name>') - name must match exactly.",
    },
    "world_families": {"tr": "{f} aile, {n} nesne", "en": "{f} families, {n} objects"},
    "world_objects": {"tr": "nesne", "en": "objects"},
    "world_models": {"tr": "model", "en": "models"},
    "world_within": {"tr": "{n} nesne {r}m icinde", "en": "{n} objects within {r}m"},
    "world_near_fmt": {"tr": "HATA: --near x,y,z biciminde olmali",
                       "en": "ERROR: --near must be x,y,z"},

    # --- framework ---
    "fw_a": {
        "tr": "A) KAYNAK KURULU DEGIL - bu cagrilar oyunda sessizce basarisiz olur",
        "en": "A) RESOURCE NOT INSTALLED - these calls fail silently in game",
    },
    "fw_b": {
        "tr": "B) KAYNAK VAR ama export tanimsiz - YAZIM HATASI adayi (UYARI, kesin degil)",
        "en": "B) RESOURCE EXISTS but export undefined - likely TYPO (WARNING, not certain)",
    },
    "fw_b_note": {
        "tr": ("JS/C# ile yazilmis kaynaklarin export'lari Lua taramasinda\n"
               "        gorunmez (screenshot-basic, oxmysql). Bu yuzden HATA degil UYARI."),
        "en": ("exports of JS/C# resources are invisible to a Lua scan\n"
               "        (screenshot-basic, oxmysql). Hence WARNING, not ERROR."),
    },
    "fw_c": {"tr": "C) TANIMSIZ EVENT (yerelde tanimi yok)",
             "en": "C) UNDEFINED EVENT (no local definition)"},
    "fw_c_note": {
        "tr": "chat:addMessage gibi FXServer yerlesikleri burada gorunur.",
        "en": "FXServer built-ins such as chat:addMessage show up here.",
    },
    "fw_d": {"tr": "D) OLMAYAN ox_lib MODULU", "en": "D) NON-EXISTENT ox_lib MODULE"},
    "fw_calls": {"tr": "-> {n} cagri / {u} {unit}", "en": "-> {n} calls / {u} {unit}"},
    "fw_scanned": {"tr": "{n} kurulu kaynak tarandi", "en": "{n} installed resources scanned"},

    # --- anim yedek ---
    "anim_no_clips": {
        "tr": ("clips.tsv.gz kurulu degil -> SURE ve KEMIK sayisi gosterilemiyor.\n"
               "     Bu bilgi .ycd dosyalarindan cikarilir ve GTA V kurulumu gerektirir:"),
        "en": ("clips.tsv.gz is not installed -> DURATION and BONE count unavailable.\n"
               "     That data comes from .ycd files and requires a GTA V install:"),
    },
}


def _config_lang():
    try:
        if os.path.exists(CONFIG):
            return json.load(open(CONFIG, encoding="utf-8-sig")).get("lang")
    except Exception:
        pass
    return None


def get_lang():
    global _LANG
    if _LANG is None:
        _LANG = (os.environ.get("MUTO_ATLAS_LANG") or _config_lang() or _DEFAULT).lower()
        if _LANG not in ("tr", "en"):
            _LANG = _DEFAULT
    return _LANG


def set_lang(lang):
    """--lang bayragi cevre degiskenini ve config'i EZER."""
    global _LANG
    if lang and lang.lower() in ("tr", "en"):
        _LANG = lang.lower()
    return _LANG


def t(key, **kw):
    m = MESAJ.get(key)
    if not m:
        return key  # eksik ceviri GORUNUR kalir, sessizce kaybolmaz
    s = m.get(get_lang()) or m.get(_DEFAULT) or key
    try:
        return s.format(**kw) if kw else s
    except (KeyError, IndexError):
        return s


def add_lang_arg(parser):
    """Her CLI'ya ayni bayragi ekler."""
    parser.add_argument("--lang", choices=["tr", "en"],
                        help="cikti dili / output language (varsayilan: en)")
