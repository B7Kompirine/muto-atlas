# muto-atlas'a katkı

Yardımın için teşekkürler. Katkılar **Türkçe ya da İngilizce** olabilir —
issue, pull request ve bulgu fark etmez. [English guide →](../CONTRIBUTING.md)

## Tek kural: ölç, varsayma

Bu depodaki her şey bir ölçüme dayanır; katkının da dayanması gerekir.
Tekrar üretilemeyen bir iddia, ne kadar makul görünürse görünsün birleştirilmez.

Her iddia için şunları yaz:

- **neyle bulundu** — komut, dosya ya da okuduğun kaynak
  (`assetdb.py door v_ilev_gb_teldr`, `lighting_common.fxh`, Sollumz kaynağındaki bir satır)
- **kaç örnekte** — "her zaman" değil, "118 vanilla MLO / 18.799 entity"
- **ne zaman, neyle** — tarih, oyun sürümü (Legacy / Enhanced), araç sürümleri

"Bende bir kere çalıştı" bir bulgu değil, bir rapordur. Onu issue olarak aç —
o da işe yarar.

## Nasıl katkı verilir

| Elinde ne var | Ne yap |
|---|---|
| Yanlış bir cevap ya da sessiz bir hata | **Bug / silent failure** issue'su aç |
| Belgelerde olmayan ya da yanlış yazılmış, ölçülmüş bir bilgi | **Finding · Bulgu** issue'su aç ya da pull request gönder |
| Bir betik düzeltmesi | Pull request gönder |
| Bir soru | Boş bir issue aç |

Nereden başlayacağını bilmiyorsan
[`good first issue`](https://github.com/B7Kompirine/muto-atlas/labels/good%20first%20issue)
ve [`help wanted`](https://github.com/B7Kompirine/muto-atlas/labels/help%20wanted)
etiketlerine bak. Açık soruların çoğu yalnızca oyunu olan birinin bir akşamını
istiyor.

## Neler nerede

| Yol | Oraya ne girer |
|---|---|
| `skills/fivem-assets/SKILL.md` + `trunk/` | Gövde: **her** dalda geçerli kurallar — motor değişmezleri, araç tuzakları, doğrulama merdiveni, bayraklar, kemik tag'i |
| `skills/fivem-assets/branches/<branch>/_branch.md` | Bir dal: kategorinin geniş kuralları ve yaprak tablosu |
| `skills/fivem-assets/branches/<branch>/<leaf>.md` | Tek bir görev. Yeni yaprak dalının `_branch.md` tablosuna yazılmalı, yoksa onu hiçbir şey okumaz |
| `skills/fivem-assets/sources/` | Dış araçlar ve topluluk kaynakları hakkında notlar — kaynak, kural değil |
| `skills/fivem-natives/` | Native'ler, framework API ve Lua tuzakları |
| `commands/*.md` | Slash komutları; her biri ayrı dosya, başında `description:` satırı |
| `scripts/` | Python ve PowerShell araçları |
| `data/*.tsv` | Depoda yalnız elle yazılmış üç tablo durur. `data/` içindeki geri kalan her şey yerelde üretilir ve gitignore'dadır |

Bir bulgu **bir kez**, geçerli olduğu en geniş yere yazılır: her dalda geçerliyse
gövdeye; tek kategoriye aitse o `_branch.md`'ye; tek göreve özgüyse yaprağa.

## Asla commit'leme

- **Oyun verisi.** RPF'ten çıkarılmış dosya, üretilmiş katman (`*.tsv.gz`,
  `entities.db`), Rockstar asset'lerinin XML dökümü olmaz.
  Bkz. [NOTICE.md](../NOTICE.md).
- **Başkasının kodu ya da asset'i.** Bağlantı ver, kaynak göster; yapıştırma.
  Proje bağımsız bir uygulamadır.
- **Kişisel yollar.** Araç konumları `data/config.json`'a (gitignore'da) aittir,
  `assetdb.py path` ile ayarlanır.

## Betik üzerinde çalışırken

- **Çıkış kodu sözleşmesini koru.** `0` bulundu · `1` otoritede yok ·
  `2` katman kurulu değil, yani hiçbir şey iddia edilemez · `3` iç hata.
  `2`'yi `1` diye okumak, bu eklentinin önlemek için var olduğu hatanın ta kendisidir.
- **Her yazdığını geri oku.** Komutun hata vermemesi, bir şeyin yazıldığını kanıtlamaz.
- **Hatayı asla yutma.** Çıplak `except:` ya da `catch {}` olmaz; ilk hatayı
  yazdır. Sessizce patlayan bir `foreach` bir keresinde 86.690 dosyayı
  kaybettirdi, tek belirti "0 tarandı" satırıydı.
- **Yeni kullanıcı mesajları `scripts/i18n.py` üzerinden** hem `en` hem `tr`
  karşılığıyla eklenir. Eksik anahtar kendisini yazdırır, böylece boşluk
  görünür kalır.
- **PowerShell betikleri Windows PowerShell 5.1'de çalışmalı.** UTF-8 *BOM'lu*
  kaydet, yoksa 5.1 ASCII dışı karakterleri yanlış okur.

## Değişikliğini yerelde test etmek

1. Depoyu fork'la ve kendi fork'unu klonla.
2. Claude Code'u, yayımlanmış eklenti yerine kendi kopyanla başlat:

   ```bash
   claude --plugin-dir yol/senin/muto-atlas
   ```

3. Katmanları bir kez kur (`/asset-setup`) ve değiştirdiğin komutu çalıştır.
   Çıktısını, çıkış kodu dahil, pull request'e yapıştır.
4. Eklentinin kendi denetimini çalıştır. `0` ile çıkmalı:

   ```bash
   python scripts/audit_plugin.py
   ```

   Hiç hata vermeyen kusurları yakalar: kırık bağlantı, dal tablosunda olmayan
   yaprak, kaymış sayaç, BOM'suz `.ps1`.
5. Bilgi ağacını değiştirdiysen veritabanını çevrimdışı yeniden üret ve snippet'ini bul:

   ```bash
   python scripts/build_atlas_db.py --tagger rules
   python scripts/build_atlas_db.py --search "değişikliğindeki bir kelime"
   ```

Bunun dışında otomatik test paketi yok. Pull request'teki ölçüm, testin kendisidir.

## Pull request

- Pull request başına tek konu. Yeni bir bulgu ile bir betik düzenlemesi iki ayrı PR'dır.
- Kapattığı issue varsa yaz (`Closes #12`).
- Commit mesajları, mevcut geçmiş gibi, neyin değiştiğini söyleyen düz
  cümlelerdir; Türkçe ya da İngilizce olabilir:
  *"Read lights from drawables that have no skeleton"*.
- Pull request göndererek katkının [MIT lisansı](../LICENSE) altında
  lisanslanmasını kabul etmiş olursun.

## Davranış

Nazik ol, somut ol. Bkz. [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md).
