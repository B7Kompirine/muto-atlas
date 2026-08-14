---
description: GTA V movement clipset (.ycd) üretimi — vanilla değişmezleri, üretim hattı ve hata kataloğu
---

# /clipset

Blender/Sollumz ile üretilip FiveM `stream/` üzerinden vanilla bir movement
clipset sözlüğünün yerine konan `.ycd` işi.

**Önce oku:**
`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/movement-clipset-uretimi.md`

Bu belge 12+ vanilla sözlük (686 klip / 247 animasyon) ve çalışan bir topluluk
modu üzerinde yapılmış 79 doğrulanmış ölçüme dayanır. İçinde belirti→sebep
tablosu, uçtan uca hat ve 13 maddelik hata kataloğu var.

## Hızlı hat

```bash
# Blender export sonrası, SIRA ÖNEMLİ:
python fix_ycd_xml.py      <x.ycd.xml>
python fix_clip_window.py  <x.ycd.xml>
python inject_channels.py  <x.ycd.xml>
python make_animlist.py    <x.ycd.xml> --map "idle:0,idle_intro:0,run:1,walk:2"
pwsh    xml_to_ycd.ps1     -XmlPath <x.ycd.xml>
python dogrula_clipset.py  <geri_okunan.ycd.xml>     # ATLAMA
```

Betikler: kullanıcının kendi `retarget/` çalışma klasöründe (yolu `data/config.json` ya da kullanıcıdan sorularak alınır).

## Kod yazmadan bilinmesi gereken beş şey

1. **Movement clipset klipleri `AnimationList` olmak zorunda**, klip başına tam
   2 animasyon, kemik kümeleri ayrık. İkinci animasyon daima aynı 32 kemiktir
   (30 parmak + 2 ayak başparmağı). `Type=Animation` yazarsan ped aralıklarla
   bind poza düşer.

2. **Mover'da `Track 5` işareti ile `Track 6` dönüşü tek bir çifttir.**
   `(+t5, birim t6)` ya da `(−t5, 180° t6)` — karıştırma. Yanlış kombinasyon
   "geri yürü" demektir: klip oynar, ped yerinde sayar.

3. **Vanilla mover'ı klip sınırında SIFIRLANIR.** Hız ölçerken sıçrama taraması
   yapmadan pencere açarsan sonuç yarıya düşer. Bu hataya bir kez düşüldü ve
   yanlış sayı dosyaya yazıldı.

4. **`Unknown10` bit 16, ancak ve ancak `Track 5/6` varsa.** Vanilla'da ihlal
   247/247'de sıfır. Animasyonu bölerken mover'sız yarıya bayrak mirası bırakma.

5. **Sollumz klipleri ve animasyonları obje adına göre ALFABETİK dizer**,
   oluşturma sırasına göre değil. Sırayı mover imzasından doğrula, klip→animasyon
   bağını `<AnimationHash>` ile açıkça yaz.

## Görsel belirtiler

| görülen | bak |
|---|---|
| ayaklar havada / parmak ucunda | `IK_L/R_Foot` `Track 0` + zemin kalibrasyonu |
| gövde ilerleme yönüne tam dönmüyor | `SKEL_Pelvis` / `SKEL_Spine_Root` pimlemesi |
| koşarken ayak kayıyor | kadans ↔ mover adım mesafesi uyumsuz |
| her döngüde tek kare takılma | döngü kapanış karesi pencerenin içinde |
