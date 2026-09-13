#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lua_sozdizim.py — Lua dosyasinda KAPANMAMIS string/yorum arar.

⛔ NEDEN VAR: `lua_check` (lua-language-server) gercek bir sozdizim
   hatasini KACIRDI ve "No diagnostics" dedi. Hata sudur:

       print('... /ptfxkat <n> (8'er)  ...')
                                    ^ Turkce kesme isareti string'i KAPATIR

   FiveM `')' expected near 'er'` verdi ve **kaynagin tamami yuklenmedi**:
   hicbir komut kaydolmadi, oyunda yalniz baska kaynagin komutu gorundu.
   Belirti "komut yok" -- Lua hatasina benzemiyor bile.

Bu betik Lua'nin string/yorum kurallarini gercekten izler:
  · 'tek' ve "cift" tirnakli string, `\\` kacisi
  · `--` satir yorumu (string ICINDE degilse)
  · `[[ ]]` ve `[==[ ]==]` uzun string/yorum
Sonunda hala bir string/yorum acikta ise hata verir; ayrica satir
sonunda kapanmamis kisa string kalirsa o satiri bildirir.

Kullanim:
  python lua_sozdizim.py <dosya.lua> [...]
"""
from __future__ import annotations

import io
import sys


def denetle(yol):
    """(hata_listesi) dondurur."""
    s = io.open(yol, encoding="utf-8", errors="replace").read()
    hatalar = []
    i, n = 0, len(s)
    satir = 1
    while i < n:
        c = s[i]
        if c == "\n":
            satir += 1
            i += 1
            continue
        # uzun string / uzun yorum: [[ ... ]] veya [==[ ... ]==]
        if c == "[" or (c == "-" and s.startswith("--[", i)):
            j = i + 2 if s.startswith("--", i) else i
            if j < n and s[j] == "[":
                k = j + 1
                esit = 0
                while k < n and s[k] == "=":
                    esit += 1
                    k += 1
                if k < n and s[k] == "[":
                    kapa = "]" + "=" * esit + "]"
                    son = s.find(kapa, k + 1)
                    if son < 0:
                        hatalar.append((satir, "kapanmamis uzun string/yorum"))
                        return hatalar
                    satir += s.count("\n", i, son)
                    i = son + len(kapa)
                    continue
        # satir yorumu
        if s.startswith("--", i):
            son = s.find("\n", i)
            i = n if son < 0 else son
            continue
        # kisa string
        if c in "'\"":
            tirnak = c
            j = i + 1
            while j < n:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == "\n":
                    hatalar.append((satir,
                                    "satir sonunda KAPANMAMIS %s string" % tirnak))
                    break
                if s[j] == tirnak:
                    break
                j += 1
            else:
                hatalar.append((satir, "dosya sonunda kapanmamis string"))
                return hatalar
            i = j + 1
            continue
        i += 1
    return hatalar


def main():
    if len(sys.argv) < 2:
        print("kullanim: lua_sozdizim.py <dosya.lua> [...]")
        return 2
    kotu = 0
    for y in sys.argv[1:]:
        h = denetle(y)
        if h:
            kotu += 1
            print("⛔ %s" % y)
            for satir, msj in h[:10]:
                print("   satir %d: %s" % (satir, msj))
        else:
            print("temiz: %s" % y)
    return 1 if kotu else 0


if __name__ == "__main__":
    raise SystemExit(main())
