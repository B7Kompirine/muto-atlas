---
description: Multi-object scene - object list, .ycd clip decoding and ymap placement
argument-hint: --add <model.ydr> [--anim <ycd>:<clip>] [--ymap out.ymap]
allowed-tools: Bash(python:*), Bash(powershell:*), Read, Edit
---

Kullanıcının sorgusu: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

Birden fazla objeyi bir sahnede toplar, `.ycd` klibini çözüp doğrular ve
yerleşimi `.ymap` olarak yazar.

## Sırayla

```bash
# sahne kur (kalıcı: --file ile kaydedilir)
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" sahne --file sahnem.json \
    --add prop_a.ydr --add prop_b.yft

# son eklenen objeye animasyon bağla
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" sahne --file sahnem.json \
    --anim "kapi.ycd:kapi_ac"

# sahnenin ozeti: ucgen/kemik/light sayilari + klip dogrulamasi
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" sahne --file sahnem.json

# yerleşimi haritaya çıkar
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" sahne --file sahnem.json \
    --ymap muto_sahne.ymap --name muto_sahne
```

Obje silme: `--remove <indeks>`. Klip adı verilmezse sözlüğün ilk klibi seçilir
ve özet çıktısında kare/süre/kemik kanalı sayısı raporlanır.

## Ölçülmüş, tahmin edilmemiş

- **Animasyon oynatılacaksa geometri PİŞİRİLMEZ.** Pişirilmiş vertex'e
  animasyon uygulanırsa kemik dönüşümü **iki kez** girer ve model dağılır.
  Doğrulandı: bind pozunda skinning, pişirilmiş sonuca **0.000e+00 m** farkla eşit.
- **Kanal kemiğe TAG ile bağlanır**, isimle değil. Tag tutmazsa kanal sessizce
  düşer — hata çıkmaz, o kemik kımıldamaz.
- **Prop animasyonlarında hareket çoğu zaman MOVER'dadır** (track 5/6), kemik
  kanallarında değil: obje dünyada yol alır. Kemik kanalları sabit görünüyor
  diye "animasyon yok" deme, track 5/6'ya bak.
- **`bidx` slot 0 boş olabilir.** Ölçüldü: bir kapının 330 vertexinin
  **%100'ünde** slot 0'ın ağırlığı sıfır, gerçek kemik 2. slotta. Slot 0'ı
  körlemesine almak bbox'ı 1.096 m kaydırır — ve bbox **ymap extent'ini** besler.
- **ymap extent entity'lerin BİRLEŞİMİNDEN** hesaplanır; extent dışında kalan
  entity sessizce hiç görünmez. Yazıldıktan sonra **geri okunup** doğrulanır.

## Sonucu sunarken

- Animasyon **statik** olabilir (kanallar sabit) — klip oynar ama bir şey
  kımıldamaz. Bu hata değil; klibin kendisi öyle. Söyle, kullanıcı klip
  aramakla vakit kaybetmesin.
- Obje ya da `.ycd` yüklenemezse **hangi obje** ve **neden** olduğu raporlanır;
  sahne yine açılır, eksik obje atlanır.
- ymap yazdıktan sonra hatırlat: asset değişti → sunucudan **çıkıp yeniden
  bağlan**, restart yetmez.
- Işık işi tek dosyaysa `/light` daha doğrudan; `/scene` çoklu obje içindir.
- **Animasyon oynatan bir görsel önizleme bu pakette yoktur.** Klip çözülür,
  doğrulanır ve raporlanır; "gözle izle" isteniyorsa Blender/oyun gerekir.

Işık matematiği ve önizlemenin sınırları:
`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/light-matematigi-ve-onizleme.md`
