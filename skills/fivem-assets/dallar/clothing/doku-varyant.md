# Doku / renk varyantı / skintone (`_r`) giysiler

**Ne zaman okunur:** aynı giysiye a-z doku varyantı, ten rengi gösteren (`_r`) giysi, "ten rengi çalışmıyor", doku adlandırması.
**When to read:** a-z texture variants of one garment, a skin-tone (`_r`) garment, "skin tone is not working", texture naming.
**Kaynak:** `notlar/03` §3, §4 adlandırma (2026-08) · **Ölçüm:** video; `_r` üç sessiz hatası Sollumz Discord'da bağımsız teyitli
**Önce:** `dallar/clothing/_dal.md` · gövde › `govde/arac-tuzaklari.md` §1

---

**Doku adlandırma kuralı** dalın tamamında geçerlidir → `dallar/clothing/_dal.md`.

## 3. `_r` (skintone) giysiler — üç sessiz hata (`sJO_Fd__2nw`)

**Ten rengi dokusu giysinin kendi `.ytd`'sinde DEĞİLDİR.** Oyun
`streamedpeds_mp / MP overlay TXD` içindeki `mp_fm_skin...` setinden okur.
Bu yüzden giysinin dokusundaki bacak/ayak alanı **boş bırakılabilir**.

1. ⛔ **Ten rengi UV'sini KAYDIRMA.** Erkek bacakları dokuda hep **sol alt köşede**,
   kadın ayakları hep **alt yarıda** durur. Oynatırsan dövme ve kan haritalaması
   bozulur. Kendi dokun için **çevresindeki** boşluğu kullan.
   Pantolon gibi bacağı tamamen kapatan bir şey yapıyorsan o alanı kullanabilirsin,
   ama görünen kısmın (ör. bilekler) UV'si **yerinde kalmalı**.
2. ⛔ **Gömülü doku adları Rockstar'ın kuralına uymalı**:
   `<bileşen>_spec_<NN>` → `feet_spec_000`, `lower_spec_000`, `upper_spec_000`.
   Rastgele isim → **ten rengi sessizce çalışmaz**.
3. ⛔ **Ten rengi maskesi specular dokusunun ALFA kanalıdır.**
   Alfa "burada ten rengi kullan" der; **beyaz = normal kumaş** (ten rengi yok).
   RGB kanallarını ve alfayı düzenleyebilen bir program şart.
   En iyi başlangıç: **base game (DLC değil)** kadın `lower_15` spec,
   erkek `lower_14` spec — en çok bacak gösterenler.
4. ⛔ **Doku KARE olmalı** (1024×1024, 512×512…). 1024×512 gibi bir oran UV'yi
   gerer ve ten rengini yine bozar.
