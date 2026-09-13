# Partikül — dal kuralları

Komut: `/particle` · Klasör: `dallar/particle/`
Anahtar kelimeler: partikül, particle, ptfx, .ypt, efekt, duman, smoke, ateş, fire, kıvılcım, spark, buhar, toz, dust, damla, sinek, kar, yaprak, fxName, StartParticleFx, amb_, dst_, brk_, core.ypt, fxType, CExtensionDefParticleEffect, flipbook, sprite sheet, sayfa, C4, emitter, keyframe, KFP, donör, transplant, katalog, aile, PtFxAssetStore, tezgâh, rcon
**Bu dala ne düşer:** **Görsel efekt** — duman · ateş · kıvılcım · toz · sıvı; `.ypt` üretimi, ytyp partikül extension'ı. Sınır: ışık → `/look` · kırılma fiziğinin kendisi → `/prop`.

> Yukarıdaki anahtar kelimeler **hızlandırıcıdır, kapsayıcı değildir.** Bir kelime listede yoksa
> yönlendirme durmaz — bu tanıma bakılır. *“kepenk”* listede olmasa da bir kapı nesnesidir.

**What belongs here:** **A visual effect** — smoke · fire · sparks · dust · liquid; `.ypt` authoring, ytyp particle extension. Boundary: light → `/look` · the breaking physics itself → `/prop`.
**Keywords (EN):** particle, ptfx, .ypt, smoke, fire, sparks, dust, steam, explosion effect, flipbook, sprite page, effect catalogue, fxName, StartParticleFx, CExtensionDefParticleEffect, fxType, emitter, keyframe, evolution, donor effect, PtFxAssetStore, blood effect, bloodfx


## Bu dalda her yaprakta geçerli olan

Ölçüm kaynakları: `core.ypt` (45,5 MB) alan alan; 2.549 vanilla efekt / 368 `.ypt`; 64.209 ytyp extension;
15 + 56 aile oyunda tezgâhla ölçüldü.

### Adlandırma ve bağ
- **ytyp `fxName` ile `.ypt`'deki efekt adı AYNI DEĞİL** — motor `ent_` öneki ekler (%65,3). Bir `fxName` yazmadan
  önce `assetdb.py fx <ad> --exact`. Yanlış ad **sessizce** hiç çıkmaz.
- **Emitter adı efekt adıyla aynı değildir**; `<ParticleRule>` emitter'da değil **efekt** bloğundadır.
- Oyunda kullanım **iki ayrı ad** taşır (varlık adı + efekt adı); varlık adında **büyük harf olmaz**.

### `.ypt` üretimi — sessiz çöküşlerin dördü
- ⛔ **CodeWalker XML okuyucusu `FxcFileHash`'i ve `VFT`'yi YAZMAZ** → shader'sız `.ypt`, hiçbir şey çizilmez →
  `scripts/ypt_xml_to_bin.ps1` (hash'i yazar, geri okur, sıfırsa exit 1).
- ⛔ **Her davranış tipinin keyframe yuva sayısı sabittir ve hepsi yazılır** (`Age`/`Velocity`/`Sprite` 0 · `Colour` 3 ·
  `Size`/`Rotation` 4); eksik yuva `Save()`'i `AssignPositions`'ta çökertir ve hangi yuva olduğunu söylemez.
- ⛔ **Alan adına bakıp ölçek varsayma:** `m_sizeScalarKFP` **yüzde** (nötr 100, medyan 57.6; `1.0` yazmak boyutu %1'e
  düşürür); `speed`/`life`/`playbackRate` ~1.0. `m_tblrScalarKFP` boşsa çarpan 0 → sıfır boyut. `FxcTechnique`
  kapalı listedir (`RGBA_lit_soft`), `default` yok. `m_zoomScalarKFP` efektin tüm uzamsal ölçeğini sürer.
- ⛔ **`Unknown*` alanına 0 yazma** — dağılımına bak (`UnknownA4..B0` mesafe bandı, `Unknown10C` `0x10100`).
- **Partikül dokusu DXT + mip zinciri** (107/107 vanilla); sıkıştırılmamış/tek mip örnek yok. `make_dds.py` varsayılanı.
- ⛔ **Sıfırdan yazılan kural ızgarayı uygulatmıyor — üretim yolu TRANSPLANT** (`ypt_transplant.py`); donörün tekniği
  kendi dokusuna göre seçilmiştir, çok dokulu donör kullanma.

### Sayfa (flipbook) — ölçülmüş
- **`C4` ızgara değil, oynatılacak SON KARE indeksidir.** Sayfa dilimlenir ama **flipbook yoktur** — parçacık doğduğu
  hücreye kilitlenir. Kare geçişi isteniyorsa **N emitter + `Unknown10` gecikmesi** (`katmanli.md`).
- Son kare boş çıkar (15 ailenin 15'inde) → üç kademeli kapı; kare hücre kenarına değmemeli; rng geçiş başına tek.
- **Hareket devralınmaz, yazılır** — hareketi dokudan alan donör statik sprite'la ölür; MIN ve MAX zarflarının ikisine bak.

### Çalışma zamanı
- **`PtFxAssetStore Pool Full, Size == 400` dosya sayar**; **tek büyük `.ypt` oyunu dondurur** (ölçülmüş eşik) → böl,
  ad haritası şart. Stream ve komutlar **ayrı kaynakta**.
- **Handle'ın sıfırdan farklı gelmesi yalnız adın bulunduğunu gösterir**; "geri okuma geçti" motorun kabul ettiği
  anlamına gelmez; **beyaz zemine bindirilmiş partikül yanıltır**; ekran görüntüsü ölçüm değildir → **tezgâh** (etiketi ekrana
  yaz, vanilla efekti referans çağır, kafesi say).
- ⛔ **Türkçe kesme işareti Lua string'ini kapatır, `lua_check` kaçırır**; `Wait()` command callback'te çağrılamaz.

## Yapraklar

| istenen | dosya | durum — kaynak |
|---|---|---|
| Var olan efekti kullan / prop'a bağla | hazir-efekt.md | ölçüldü — ytyp-ymap §6 · SKILL sorgu |
| Sıfırdan `.ypt` üret (sayfa, yuvalar, transplant, hareket) | sifirdan-ypt.md | ölçüldü — ptfx-flipbook §1-6, §8, §13 · ytyp-ymap §7c-7d |
| Doku sayfası — kare, `C4`, ızgara, yoğunluk, transplant | sayfa-doku.md | ölçüldü — ptfx-flipbook §1-5 |
| Katalog / aile üretimi ve kalite kapısı | katalog.md | ölçüldü — ptfx-flipbook §9-12, §14-15 |
| Katmanlı (çok emitterli) efekt | katmanli.md | ölçüldü — ptfx-flipbook §1e-BIS · ptfx_kompoze |
| Dağıtım ve oyunda ölçüm (tezgâh, rcon, havuz) | dagitim-olcum.md | ölçüldü — ptfx-flipbook §1c, §7, §16-18 |

## Betikler (hepsi `scripts/`)
`ptfx_sayfa.py` (sayfa) · `make_dds.py` (DXT5+mip) · `build_custom_ptfx.py` / `ypt_transplant.py` (üretim) ·
`ypt_xml_to_bin.ps1` (hash + geri okuma) · `ptfx_katalog_kur.py` · `ptfx_kalite_kapisi.py` · `ptfx_donor_ara.py` ·
`ptfx_birlestir.py` · `ptfx_hareket.py` · `ptfx_kompoze.py` (katman) · `ptfx_sim.py` (GIF simülasyon — model, motor değil) ·
`ptfx_blender_render.py` / `_enerji.py` / `_duman.py` (sprite render: katı / enerji-sıvı / hacim) · `ptfx_kenney.py` ·
`ptfx_tezgah.py` (oyunda ölçüm)

## Gövdeye bakılacaklar
- `govde/bayraklar.md` §6 partikül extension bayrakları · `govde/arac-tuzaklari.md` §3 (`YptFile.Load`, boyut ölçüt değil,
- `govde/dogrulama-merdiveni.md` — `.ypt` geri okuma kapısı; oyunda ölçüm en son basamak (tezgâh)
  `ResourcePointerArray64`), §4 (`while read` stdin), §6 FiveM (stream'e dosya eklemek üç adım, hayalet oturum)
- Oyunda canlı efekt önizleme (`eco_effect`, `echo effect`), `.ypt` keyframe property dokümantasyonu ve `bloodfx.dat` alan anlamları → `kaynaklar/topluluk-kaynak.md` §11 — **kaynak notu, kural değil.**
