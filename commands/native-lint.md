---
description: Lua dosyalarını native hatalarına karşı denetle (uydurma native, yanlış taraf, argüman sayısı)
argument-hint: [dosya veya klasör yolu — boşsa mevcut dizin]
allowed-tools: Bash(python:*), Read, Edit, Grep, Glob
---

Hedef: `$ARGUMENTS` (boşsa mevcut çalışma dizini)

1. Linteri çalıştır:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/lint_lua.py" <hedef>
   ```

2. Bulguları ele al:

   - **E001** (native yok) — `nativedb.py check` ile doğru adı bul. Önerilen isim
     doğruysa düzelt. Hiç öneri yoksa bunun bir framework fonksiyonu olabileceğini
     değerlendir; native değilse kullanıcıya söyle, uydurma bir isimle değiştirme.
   - **E002** (yanlış taraf) — client-only native sunucu dosyasında. Ya mantığı
     client'a taşı ve olayla tetikle, ya da `--apiset server` ile eşdeğer bir native
     ara. Sessizce silme; hangi çözümü seçtiğini açıkla.
   - **E003** (fazla argüman) — `show` ile imzayı al, çağrıyı imzaya uydur.
   - **W101/W102/W103** — per-frame maliyet. `references/performance.md` kalıplarını
     uygula (dinamik `sleep`, döngü dışına taşıma, önbellekleme).
   - **W104** (eksik argüman) — genelde zararsız bir deyimdir. Yalnız davranışı
     etkiliyorsa düzelt; toplu olarak "düzeltme" yapma.

3. Düzeltmeleri uyguladıktan sonra linteri **tekrar çalıştır** ve E00x kalmadığını
   göster.

4. Özetle: kaç dosya tarandı, kaç hata düzeltildi, hangi uyarılar bilinçli olarak
   bırakıldı ve neden.

Yanlış pozitif olduğunu düşündüğün bir bulguyu düzeltmeden geçme — önce nedenini
doğrula (tanım lint kapsamı dışında mı, metot çağrısı mı), sonra gerekçesini yaz.
