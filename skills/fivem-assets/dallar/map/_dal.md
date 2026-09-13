# Harita — dal kuralları

Komut: `/map` · Klasör: `dallar/map/`
Anahtar kelimeler: ymap, ytyp, MLO, iç mekân, interior, vanilla parça değiştirme, yol, köprü, bina, kule, duvar, yıkım, kırılma, kırılsın, çökme, parçalanma, patlama, enkaz, RayFire, des_, composite, LOD, lodDist, SLOD, uzakta kayboluyor, hayalet, extent, hei_, patchday, overlay, decal katmanı, ybn, collision, çim, grass, fur grass, @ma, grass batch, arazi, terrain, iç mekân ölçüsü, pah, bevel, gölge mesh
**Bu dala ne düşer:** Dünyaya **SABİT** duran her şey — ymap/ytyp/MLO, iç mekân, yol · bina · köprü · duvar, çim, LOD ve bunların **yıkımı/çökmesi**. Sınır: tek başına alınabilen taşınabilir nesne → `/prop`.

> Yukarıdaki anahtar kelimeler **hızlandırıcıdır, kapsayıcı değildir.** Bir kelime listede yoksa
> yönlendirme durmaz — bu tanıma bakılır. *“kepenk”* listede olmasa da bir kapı nesnesidir.

**What belongs here:** Everything that sits **FIXED in the world** — ymap/ytyp/MLO, interiors, road · building · bridge · wall, grass, LOD, and their **destruction/collapse**. Boundary: a standalone portable object → `/prop`.
**Keywords (EN):** ymap, ytyp, MLO, interior, vanilla part replacement, road, bridge, building, tower, wall, destruction, collapse, break apart, explosion of a structure, debris, RayFire, des_, composite, LOD, lodDist, SLOD, disappears at distance, ghost copy, extent, patchday, overlay, grass, terrain, procedural


## Bu dalda her yaprakta geçerli olan

Her madde oyunda ölçüldü (Fleeca MLO, hw1_27 vinç, dt1_rd1 otoyol, des_stilthouse/crane/kopru,
v_coroner/abattoir). Proje adı kural değil, kaynak notudur.

### Önce iki soru
- **MLO içi mi, dışı mı?** İçine **ymap ile prop konmaz** (oda/portal eler, obje hiç gelmez);
  tek yol MLO'nun kendi entity listesi. Dışına ymap olur. Referans kaynağın ymap kullanması
  yanıltmasın — önce koordinatın MLO içinde mi olduğuna bak (`assetdb.py where`).
- **Script'le spawn edilen obje harita objesi değildir**: kapı sistemi bulamaz, fragment
  collision'ı animasyonu takip etmez, her istemcide ayrı yük.

### MLO
- Aynı iç mekânın **birden fazla MLO sürümü** olabilir (Fleeca: `v_genbank` + `hei_generic_bank_dlc`,
  aynı yerel çerçeve, farklı entity listesi) — **hepsini yamala**.
- MLO entity bayrağı **18350080**; ymap değeri `1572872` verilirse obje sessizce oluşmaz
  (bit 8 "LOD in parent map" der, üst harita yoksa entity düşer). Çöz: `assetdb.py flags <n> --entity`.
- Yeni entity **odaya bağlanır** (`AttachedObjects`); unutulursa görünmez, MLO bozulabilir. `lodDist -1`.
- Vanilla dosya değişimine `DLC_ITYP_REQUEST` **eklenmez**; kendi yeni ytyp'ine eklenir.
- Yamalar üst üste biner: her betik vanilla RPF'ten değil **çıktı klasöründen** devam eder.
- Kendi drawable'ın iç mekânda **`trees_normal.sps` ile simsiyah** çizer → `normal.sps`.

### Vanilla parçaya dokunurken
- **Silme, aşağı taşı** (`z -= 600`); silmek indeksleri kaydırır, `parentIndex`'ler yanlış entity'yi gösterir.
  `.ydd` içinden obje silmek diğer objelerin özelliklerini de bozar.
- ⛔ **Extent'e dokunma** — streaming hacmini büyütmek haritanın tamamında collision'ı yok etti.
- **LOD zincirinin tamamı** (`X_strm_N` → `X` → `X_lod`) **ve `hei_` ikizleri** — mpheist aktifken
  yüklenen `hei_` kopyasıdır; base'i yamalamak "yakından temiz, uzaktan duruyor" verir.
  SLOD2 çoğu zaman gizlenemez (15 çocuk) → model cerrahisi.
- **Ayak izindeki her entity'yi say**: yol = `_rd_NN` yüzey + `_ovly_NN` kaplama + `_rd_NN_ov` decal;
  decal aynı düzlemde kalır → Z-fighting, `_ovly` kaldırılmazsa çizgiler havada asılı kalır.
  ⛔ **`_ovly` numarası yol numarasıyla eşleşmeyebilir** — `hw1_rd_02_25`'in kaplaması `hw1_rd_02_00_ovly`
  (aynı konum, bbox %100); `hw1_rd_02_25_ovly` 185 m ötede, çakışma %0. Decal'i **addan değil,
  entity konumu + bbox kesişiminden** eşle. Bölge decal'i (`X_glue*`) komşu binaların duvarına da
  tırmanır; o binalar yoksa havada tel kafes gibi görünür. (ölçüm: hw1 6 parça / 12 aday decal, 2026-09-10)
- **Dokular modelde değil** — dış sözlük + `gtxd.meta` ebeveyn zinciri; aynı doku adı farklı sözlükte
  farklı içerik taşır (175 kopyadan 22'si) → boyuta göre seç, GTA'nın çözüm sırasıyla.
- ⛔ **Aynı ymap birden fazla RPF'te, sürümler farklı.** `-Flatten` sessizce yanlış sürümü bırakır;
  doğru kaynak genelde `patchday27ng` / `update.rpf/dlc_patch/mpheist`. Başka kaynaklar aynı ymap'i
  stream ediyorsa hangisinin kazandığı belirsiz — önce çakışmayı listele.
- Collision ayrı `.ybn`'de (`physicsDict 0`); hedefi kapsayan dosyayı `BoxMin/BoxMax` ile bul.

### Kendi ymap'ini yazarken
- Extent **entity'lerin birleşiminden** hesaplanır; dışta kalan entity sessizce görünmez.
  Arketip kutusu da animasyonun **tamamını** kapsar. `guid` Jenkins ile deterministik.
- ymap yazmanın iki yolu var ve hangisinin kayıpsız olduğu dosyaya göre değişir; `CalcFlags()`
  çağırma, `CalcExtents()` kullanma, `CEntityDefs`'i doğrudan yazma (`govde/arac-tuzaklari.md` §3).
- HD entity bayrağı `1572872` = LOD in parent map + gölgeler; parent index **0 tabanlı**, `-1` zincir sonu;
  her seviyenin `childLodDist`'i bir öncekinin `lodDist`'i. Ölçüt vanilla: `lodaudit`.

### Yıkım (RayFire)
- `des_X` bir **yönetmendir**, arketip değil: `StartImapFile` kapanır → motor `AnimatedModel`'i yaratır →
  klip → `EndImapFile` açılır. Görünen **üç ayrı varlık**. Animasyonlu drawable hiçbir ymap'te yoktur.
- **Animasyon sırasında collision YOK**; collision duruma aittir. Script hilesi burada da ters teper.
- **Klip adı = model adı = arketip adı** (`.yed` zincirinin "farklı olmalı" kuralı buraya taşınmaz).
- **Kalıcı geometri placer ymap'ine**, `start`'a yalnız çöken dilim; yoksa bölgenin tamamı boşluk olur.
- Kemik bayrakları: kök `4215`, diğerleri `119`; `.ycd` iskeletin tamamı, kök dahil, üç track.

### Çim / collision
- **Çim dört ayrı sistemdir** (düz doku · çim prop · fur grass · `@ma` prosedürel · grass batch) — hangisi olduğu **sorulur**.
- `@ma` prosedürel yalnız **var olan** collision'a eklenir; poligon yeterince **büyük** olmalı.
- "Çim görünmüyor" → önce **Grass Quality** ayarı (Ultra).

## Yapraklar

| istenen | dosya | durum — kaynak |
|---|---|---|
| Vanilla parçayı kendi modelimle değiştir (yol, prop, yapı) | vanilla-parca-degistirme.md | ölçüldü — vanilla-parca-degistirme · yol-yikim OLCUMLER |
| Yıkım / çökme / koreografili sahne — tek yaprak | yikim.md | ölçüldü — rayfire-des-uretim |
| MLO objesini değiştir (entity swap) | mlo-obje-degistir.md | ölçüldü — mlo-obje-degistirme · eski SKILL |
| MLO'ya kendi prop'unu / drawable'ını koy | mlo-prop.md | ölçüldü — mlo-prop-uretim-hatti · mlo-drawable-export |
| LOD zinciri — uzakta titriyor / kayboluyor | lod.md | ölçüldü+video — ytyp-ymap §9 · notlar/08 §8 |
| Vanilla iç mekân ölçüsü | vanilla-ic-mekan.md | ölçüldü — vanilla-ic-mekan-olcumu |
| Çim / prosedürel zemin / arazi | cim-prosedurel.md | video+veri — notlar/08 §1-7 |

## Gövdeye bakılacaklar
- `govde/bayraklar.md` — entity/archetype bayrakları, `specialAttribute`, extension'lar
- `govde/arac-tuzaklari.md` §3 CodeWalker (ymap yazma, `MetaHash`, `BoxMin`), §4 PowerShell (`-Flatten`, `[script]`)
- `govde/dogrulama-merdiveni.md` — oyuna girmeden ymap/ytyp denetimi
- `scripts/mlo_local_to_world.ps1` — MLO yerel koordinatını **tüm** dünya yerleşimlerine çevirir (Fleeca 6 şube; `build_entities.ps1` ile aynı matematik)
- Işık/timecycle/parallax: `dallar/look/_dal.md`
- Hazır şablon / araç arıyorsan (LOD şablonları + `nametables.rpf`, Arbolito, VichoTools, `str_enableFlush`, iç mekân referans kütüphaneleri, `Procedural_IDs.txt`) → `kaynaklar/topluluk-kaynak.md` §6, §10, §12 — **kaynak notu, kural değil.**
