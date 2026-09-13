# Araç tuzakları — tek katalog

**Gövde dosyası.** Her dalda geçerli olan, araca (Sollumz, Blender,
CodeWalker.Core, PowerShell, Python/Lua, FiveM çalışma zamanı) ait
tuzaklar burada **bir kez** yazılır. Dal ve yaprak dosyaları buraya bağ
verir, tekrar yazmaz. Göreve özgü tuzak buraya **girmez**; o yapraktadır.

Her madde bir satır: **belirti → sebep → çözüm**. Ölçülmüş olanlar
"ölçüldü" taşır; ayrıntısı olan maddede `→` ile yer verilir. Ayrıntı için
doğal bir yaprak yoksa bu dosyanın sonundaki **Ayrıntı** bölümündedir.

İki gövde kuralı bu kataloğun tamamını özetler:
- **Aracın göstermemesi, o şeyin yok olduğu anlamına gelmez.** (CodeWalker
  `ExprMap.Count == 0`, PowerShell `$null.Length == 0`, Sollumz "Imported in
  0.0 seconds" — üçü de bir gün yaktı.)
- **Aracın hata vermemesi, işin doğru olduğu anlamına gelmez.** Bu
  katalogdaki maddelerin neredeyse hepsi *sessizdir*: dosya oluşur, "success"
  yazar, oyunda hiçbir şey olmaz.

---

## 1. Sollumz — export / import

### Ayarlar ve format
- ⛔ **`use_custom_settings=False` verilen argümanları yok sayar.** Operatör
  senin geçtiğin ayarları değil kullanıcı tercihlerini okur; anahtarlar geçerli
  olduğu için `TypeError` çıkmaz. Ölçüldü: `limit_to_selected=True` verildi,
  170 drawable / 19 sn bütün sahne çıktı. → Ayrıntı A
- ⛔ **`.ycd` Sollumz'un format sisteminin DIŞINDADIR.** `target_formats` ne
  olursa olsun XML çıkar, "Successfully exported" der → binary'ye ayrıca derlenmeli. Diğer
  8 uzantıda (`.ybn .ydr .ydd .yft .yld .ytyp .ymap .ytd`) `NATIVE` gerçekten
  binary yazar. → Ayrıntı B
- **`NATIVE` yalnız `pymateria` kuruluysa çalışır**; yoksa ayar **sessizce
  `CWXML`'e düşer**. → Ayrıntı B
- **Gen8 + Gen9 birlikte seçiliyse çıktı `gen8/` ve `gen9/` alt klasörlerine
  gider**; tek sürümde doğrudan hedefe. Sabit yol okuyan betik 36 dosya varken
  0 sayar — yolu ara, sabitleme. → Ayrıntı B
- **Export klasörü yoksa** `ios_base::failbit` + Blender kapanışta asılı kalır
  → önce `os.makedirs`.
- **`Fill Animation Data` düğmesi bozuk** — kare sayısını elle yaz.

### Klip (`.ycd`) yazımı
- ⚠️ **`<Hash>` — 2026-09-06'da YENİDEN ÖLÇÜLDÜ; eski kural ("Sollumz yazmaz")
  YANLIŞTI.** Sollumz **yazar**: `ycd/ycdexport.py:510` `xml_clip.hash =
  clip_properties.hash`, `:352` `animation.hash = animation_properties.hash`.
  Ama alan **elle doldurulur** — `ClipProperties.hash` varsayılanı `""`
  (`ycd/properties.py:127`, `:161`) ve yeni klip açınca doldurulmaz
  (`create_anim_obj` hash set etmez), addan da türetilmez. Doldurulmayan klip
  **boş** `<Hash></Hash>` ile çıkar; boşlar aynı anahtara düşüp birbirini ezer.
  Eski "5 klip → 1" ölçümünün sebebi buydu: araç değil, **Clip panelindeki Hash
  alanı boş bırakılmıştı**. Belirti gerçekti, teşhis yanlıştı.
  → ⛔ **Klip üretirken Clip panelinde `Hash` alanını doldur** (yerleşik olan:
  klip adının kendisi). Boş bırakırsan hata çıkmaz, klip oyunda **bulunmaz**.
  → ⛔ Hâlâ hesaplanmayan tek şey **Sequence** hash'i:
  `sequence.hash = "hash_00000000"  # TODO: calculate signature` (`:367`) —
  `<Sequences>` içindeki sıfır **normaldir**, düzeltilmez.
  → **Kapı değişmedi:** `res_to_xml.ps1` ile geri oku, `<Hash>` dolu mu bak.
  Bu kuralın yanlış olduğunu ortaya çıkaran da o kapıydı.
  **Ölçüm (2026-09-06):** Sollumz **2.8.3** kaynağı + 3 klipli bir ham export —
  üçünün de `<Hash>` alanı dolu ve benzersiz çıktı.
- ⛔ **`Animation.target_id` ARMATURE DATA-BLOCK olmalı** (`arm.data`). Object
  verilirse **0 kemik kanalı** yazar: dosya oluşur, süre doğrudur, veri yoktur
  (724 bayt vs 59 KB).
- ⛔ **UV animasyonunda `Target ID` MATERYALDİR**, armature değil. Ped
  alışkanlığıyla armature seçmek en sık hata.
- ⛔ **Kemik bayraklarını (`Flags`) yazmaz, sıfır bırakır.** Sıfır bayraklı kemik
  hiçbir dönüşüm kabul etmez: `PlayEntityAnim` 1 döner, `animTime` ilerler,
  hata yok, mesh rest pozunda. Kök **4215**, diğerleri **119**; scale süren
  klipte bu yetmez → `dallar/map/yikim.md`.
- **Klipleri ve animasyonları obje adına göre ALFABETİK dizer**, oluşturma
  sırasına göre değil → bağı `<AnimationHash>` ile açıkça yaz.
- **RayFire `.ycd`'sinde altı sapma** (çift `pack:/`, `Unknown30`, `Tags`/
  `Properties` yok, Track 2 yok, bbox rest) → `dallar/map/yikim.md`
- **`.ycd` fcurve değerleri MUTLAK kemik-yerel yönelimdir**, rest'e göre delta
  değil → gerçek açı `2·acos(|dot(q_klip, q_rest)|)`.

### Mesh / materyal / doku
- ⛔ **Fragment bound → kemik bağı `COPY_TRANSFORMS` constraint'tir** (`BEFORE_FULL`/`POSE`/`LOCAL`), `parent_bone` ya da ad eşleşmesi
  değil; constraint yoksa `does_bone_have_collision` false, kemik sessizce atlanır, `PhysicsLODGroup` boş çıkar. Animasyonlu prop'ta
  `Child Of` + Set Inverse, kırılabilir fragment'te `Copy Transforms` — iki constraint farklıdır. → `dallar/prop/fragment.md`
- ⛔ **`sz_lods.high.mesh` atanmamışsa export "has no Sollumz materials!" der
  ve drawable'ı KOMPLE atlar.** Materyal oradadır; betikle yaratılan mesh
  objelerinde alan `None` kalır → `ob.sz_lods.high.mesh = ob.data`.
- ⛔ **`bpy.data.objects.new` ile kurulan obje `sollum_type` taşımaz** → export
  onu Sollumz objesi saymaz, **dosya hiç yazılmaz, hata da vermez**. Çalışan bir
  `.ydr`'nin mesh OBJESİNİ kopyala, `.data`'yı değiştir.
- ⛔ **`hide_select` `select_set()`'i SESSİZCE düşürür.** Obje görünürdür,
  `hide_viewport`/`hide_get()` temizdir, `selected_objects` boş kalır, export
  "No Sollumz objects selected!" der. Hem objede hem koleksiyonda olabilir —
  üçünü de kontrol et, seçimden sonra `selected_objects`'i **say**.
- ⛔ **Gizli objede `select_set()` sessizce çalışmaz** → export "successfully"
  der, dosya **0 bayt** çıkar (7 objeden 5'i böyle yazıldı) → `hide_set(False)`
  + dosya boyutunu kontrol et.
- ⛔ **Sollumz'un ymap'i sessizce boş çıkabilir:** "Successfully exported" der, `<entities />` boş, extent sentinel (3.4e38).
  İki ymap sistemi var (eski `sollumz_ymap`, yeni `sz_maps_container`); karışınca "context is incorrect". ytyp/ymap XML'ini elle yaz.
- ⛔ **Sollumz operatörleri viewport bağlamı ister** — betik/MCP'de `context.selected_objects`/`active_object` yok → `temp_override`.
- **`converttodrawable` obje adına `.model` ekler**; düz adla arama sessizce boş döner. **`.001` soneki ad eşlemesini bozar** →
  `re.sub(r"\.\d+$", "", ad)`. Aynı sahnede iki kez drawable kurmak `.001` çiftleri üretir.
  Export ise drawable adındaki `.001`'i **atar**: çıktı adı doğru çıkar, Blender tarafında ada göre arama yine bozulur.
  Ölçüm: 2026-09-11, Sollumz 2.9, 1 `.ydd` — nesne `head_000_r.001` → geri okumada `<Name>head_000_r</Name>`.
- **Doku `embedded=False` ise `.ydr`'ye hiç yazılmaz**, uyarı yok; açınca ikinci
  kapı: **PNG gömülemez** → `texconv -f DXT1 -m 0` (mip zinciri şart), doku adı
  dosya adından türer.
- ⛔ **Şablon materyalde diffuse'u değiştirip normal'i bırakma** → miras
  `plants_normal` prop'ta siyah çizgi çizer. İki image düğümü de değişir.
- **Her drawable'da `Color 1` olmalı** (OBJ'den gelen mesh'te hiç yok) →
  `(1,1,1,1)` yaz, **`.color_srgb`** ile (bkz. Blender §2).
- ⛔ **Sollumz `Create Shader Material` eksik `Color 2`'yi DOLDURMADAN açar; Blender yeni `BYTE_COLOR` katmanını BEYAZ (1,1,1,1)
  başlatır.** Aynı adım mevcut köşe rengini sırayla `Color 1`e yeniden adlandırır (Unreal ripinde `PSKVTXCOL_0` → `Color 1`). Ped'de
  `Color 2` = rüzgâr (RGB) + ter/ıslaklık (alfa): beyaz kalınca oyunda **titreme**, export uyarı vermez. Vanilla ped'de `Color 2` hep 0 →
  shader ekledikten sonra `Color 2`'yi 0'a çek (her köşede aynı değerse boyanmamıştır, boyanmışsa dokunma).
  **Ölçüm:** Sollumz 2.9.0 + Blender 5.2.1, 2026-09-13; iskeletli ped'e ped.sps ve ped_default.sps → `Color 2` köşelerin %100'ü beyaz,
  export edilen head/uppr/lowr'da da beyaz; `color_attributes.new` ve `attributes.new` ikisi de 1,1,1,1 başlatır. 0'a çekince `.ydd` geri
  okumada 3 çizimde Colour1 RGBA min = max = 0.
- **Export → Drawable → `Mesh Domain` = `Face Corner`**; `Vertex` yalnız MP
  freemode kafaları içindir. Yanlış seçim sessizce bozuk ped üretir.
- **Geometri başına 65.535 vertex sınırını (16 bit indeks) Sollumz kendisi böler** — elle bölme gerekmez. Ama **UV'siz mesh'te köşe
  paylaşımı olmaz**: vertex = 3 × üçgen, dosya ~4× şişer, uyarı yok (muhtemel sebep: UV yokken teğet köşe başına farklı; ölçülmedi) → önce UV aç.
  Ölçüm: 2026-09-11, Sollumz 2.9, deri bağlı ped — 232.849 vertex'lik UV'siz mesh → 22 geometri, hepsinde max indeks < vertex, toplam
  1.396.224 vertex (= 3 × üçgen), `.ydd` 31 MB; UV'li 12.520 üçgenlik export'ta üçgen başına 0.68 vertex.
- **Sollumz shader'ı olmayan materyal oyunda çalışmaz** — Principled BSDF
  bırakma; `Select` → turuncu testiyle doğrula.
- ⛔ **Sollumz gömülü dokuyu DİSKTEKİ DDS'ten paketler.** Blender içinde PNG yükleyip `img.scale()` + piksel düzenleme +
  `save()` + `pack()` yetmedi: `.ydr`'ye **16×16 taslak** gömüldü, hata yok, kusur geri okumada göründü → piksel işi Pillow'da
  (`im.save(..., pixel_format='DXT5')`). Gömülü doku adı **dosya adından** gelir, `img.name` yok sayılır.
- **Silah `.ydr`'si içe alınırken bir de "Bound Box" MESH'i yaratılır** — ilk MESH'i almak onu seçer, "UV taşımıyor" der;
  ölçüt `sollum_type == 'sollumz_drawable_model'`.
- **`.yed`/`.ymap`/`.ytyp` binary yazamaz** → meta için `meta_xml_to_bin.ps1`
  (CodeWalker.Core, `MetaFormat.RSC`); `.yed` için public bir yol yok.
- **`.ytd` YAZAR (2.9)** — eski "`.ytd` üretemez" notu geçersiz. Sahne TXD'si:
  `scene.sz_txds.new_texture_dictionary(ad)` + `txd.new_texture(image)`, sonra
  `export_assets(..., export_ytds=True, export_ytds_include="ALL")`. ⛔ `export_ytds` varsayılan
  kapalı → "CANCELLED", dosya yok; `sz_export_types` sınıf niteliğidir, parametre değil.
  Doku adı image **dosya adından** gelir.
  Ölçüm: 2026-09-11, Sollumz 2.9 + Blender 5.2, 1 örnek — 64² A8R8G8B8 DDS → 411 B `.ytd`;
  geri okumada ad, 64×64, 7 mip, format ve çıkarılan DDS (21.972 B) girdiyle aynı.

### Import / iskelet
- ⛔ **Binary `.ycd`/`.yed` OKUYAMAZ**: uyarı verip "Imported in 0.0 seconds"
  der, hata fırlatmaz, sahne boş kalır → önce `res_to_xml.ps1`.
- ⛔ **Otomatik kemik tag formülü vanilla tag'leri üretmez** (`SKEL_Head` →
  21030, gerçek **31086**) → `.ycd` import'unda kanallar `pose.bones["#31086"]`
  diye kalır. `Bone Properties → Sollumz → Tag` alanı **elle yazılır**.
- ⛔ **Kemiklerde local Y = head→tail yönüdür**, dünya eksenleri değil. Poz
  formülü `basis = L.inverted() @ M @ L` (`M` dünya rijit dönüşümü, `L =
  bone.matrix_local`); `L⁻¹ @ M` yazmak kare 0'da bile geometriyi bozar.
- **Armature'da kemik yönleri anatomik DEĞİL**: hepsi 0.05 m, `use_connect=
  False`, `bone.vector` ~±Y, kolda gerçek yönle **56°** fark → yön için
  `head → çocuğun head'i`; `bone.vector`/`bone.length` kullanan IK yanlış çalışır.
- **Kemik `tail`'i efektör olarak kullanılmaz** — tail'ler 0.05 m sentetik →
  hedef/yön için çocuk kemiğin `head`'i.
- **Import'tan sonra sahne 24 fps'te kalır**, GTA 30 → sessiz %25 zamanlama
  hatası. `scene.render.fps = 30`.
- **`.yft` import'u `SKEL_ROOT` adlı bir MESH de yaratır** ve render'da her şeyi
  kapatır. Ped origin'i kalçadadır, ayaklar z≈−0.94.
- **Koni açıları RADYANDIR** (`subtype=ANGLE`, 0–π/2); dereceyle yazmak koniyi
  tamamen açar. Property'nin `subtype`'ına bak.
- ⛔ **Sollumz'un yazdığı ped fiziği OYUNU ÇÖKERTİR** (`ArticulatedBody`
  yazmıyor) → ped `.yft` fiziksiz gönderilir.
- **`bpy.ops.object.select_all(action='DESELECT')` MCP bağlamında seçimi
  sessizce bozar** → `bpy.context.temp_override(...)`.
- **Işık export'u üç bağ:** gizli ışık düşmez, konumu bozulur ·
  `light_properties.intensity` saklanan alan değil, `energy` proxy'si · kemiğe
  bağlı ışığın konumu KEMİK uzayında · `Tangent` projeksiyonun **yukarı**
  ekseni, `Direction` değil. → `dallar/look/isik.md`

---

## 2. Blender — API ve veri

### Transform
- ⛔ **OBJE TRANSFORMU EXPORT'A PİŞER.** `matrix_basis` identity değilse
  geometriye yazılır (ölçüldü: drawable **394 m** ötede çizildi). `matrix_basis`
  **ve** `matrix_parent_inverse` sıfırla, **aynı çağrıda doğrula**.
  Armature'a bağlı ped modelinde de, `apply_transforms=False` iken bile pişer → FBX'in uygulanmamış ölçek/dönüşü ped'i bozmaz.
  Ölçüm: 2026-09-11, Sollumz 2.9, 1 `.ydd` (3 çizim) — ölçek 0.01 + X 90°, mesh verisi telafili: normal export'la metin farkı 0,
  sınır kutuları 1e-7 m, en büyük sayısal fark 0.005 (teğet bileşeni).
- ⚠️ **AMA KÖRLEMESİNE SIFIRLAMA.** Yerleştirilmiş objede (konum taşıyan)
  sıfırlamak onu orijine ışınlar (ceset 40 m öteye gitti). Doğrusu **pişir,
  sonra sıfırla**: `o.data.transform(o.matrix_world)` → identity.
- ⛔ **`bpy.ops.object.transform_apply` sessizce hiçbir şey yapmayabilir**
  (mesh 124 m kaydı, hata yok) → `ob.data.transform(ob.matrix_world)`.
- **`bound_box` BAYAT olabilir** — `mesh.transform()` sonrası eski değeri döndürür.
  Kutuyu **vertex'lerden** hesapla.
- ⛔ **`object.dimensions` DÖNÜŞÜ İÇERMEZ** (yerel bbox × ölçek) → "en uzun
  ekseni yatır" sessizce hiçbir şey yapmaz; dünya bbox'ı kullan.
- ⛔ **`matrix_world` okumadan önce `view_layer.update()`** — en çok **yeni
  append/link edilen** objede ısırır: depsgraph güncellenene kadar identity
  döner, `data.transform(matrix_world)` hiçbir şey yapmaz, ardından basis
  sıfırlanınca rotasyon/ölçek **pişmeden silinir**. Hata yok. **Ölçüm:**
  Blender 5.2.1 headless, `ExamplePed` (rot 90°, ölçek 0.01) yatık çıktı, yalnız
  önizleme render'ında görüldü; `update()` eklenince pişirme öncesi/sonrası
  dünya kutusu farkı 0.0, 2026-09-11.
- **`Ctrl+A` All Transforms atlanırsa** ölçek/dönme export'a sızar.

### Geometri
- ⛔ **`bmesh.ops.bisect_plane` açık geometride kırpmaz, YÜZ SİLER** (altı
  çağrıda yüz 637 sabit, alan 3.553 → 0.941 m²). Boolean INTERSECT de
  güvenilmez → **Sutherland–Hodgman**. → `dallar/look/decal.md`
- **Elle bmesh birleştirme UV ve renk katmanlarını düşürür** (`bm.faces.new()`
  loop verisi taşımaz) → `mesh.transform()` + `bpy.ops.object.join()`.
- ⛔ **`holes_fill` UV (0,0) örnekler** — doku köşesi yama olur → açık kenar
  oranı >%5 ise `solidify`; ölçek en **büyük** eksene göre.
- ⛔ **Decimate 4-etki kuralını bozar** → LOD'dan sonra rijit parçalarda
  ağırlığı tek gruba %100 geri çek.
- ⛔ **Vertex grubunu SİLMEK ağırlığı da siler**; ağırlıklar grup **indeksiyle**
  durur, listeyi yeniden yaratmak adları indekslere yanlış oturtur.
- **Armature modifier'ı bozuk olabilir** (500+ m saçılma) — `pose @
  matrix_local⁻¹` elle doğruysa dosya sağlamdır, viewport'a değil hesaba güven.
- **`scene.ray_cast` VIEWPORT'U kullanır** — render'da görünüp viewport'ta gizli
  obje ışın testinde atlanır.
- **Edit Mode'a girince ÖNCEKİ SEÇİM geri gelir** → önce `f.select_set(False)`
  (bir aracın 4089 decal üretmesinin sebebi).

### Renk / katman
- ⛔ **`BYTE_COLOR` katmanında `.color` GAMMA ÇÖZER**, `.color_srgb` ham
  bayt/255 verir. GTA vertex color'ı maske/çarpan olarak kullanır → `.color`
  her maskeyi sessizce koyultur. Sollumz bunu `"Color 1"`, CORNER domain'de tutar.
- **UV katmanının adı `UVMap 0`** — başka ad sessizce düşer; kopyalanan
  geometri hedefin eski UV'sini ve `Color 1` alfasını miras alır.

### Animasyon / poz
- **Blender 4.4+ Action API katmanlı**: `action.fcurves` yok →
  `layers → strips → channelbags → fcurves`; ve **action atamak yetmez, SLOT
  da bağlanmalı** (`animation_data.action_slot = act.slots[0]`).
- **Keyframe'lenmeyen kemik son pozunda kalır** → ölçüm öncesi pozu sıfırla;
  elle poz vermeden `animation_data.action = None` (atanmış action her
  `view_layer.update()`'te pozu ezer).
- **Blender 5.0'da seçim `Bone`'dan `PoseBone`'a taşındı.**
- **Bezier interpolasyon** UV/klip animasyonunu hızlandırıp yavaşlatır → Linear.

### Sahne / collection
- **Obje sahnede görünüyor ama Edit Mode'a girmiyor, Sollumz tipi
  `sollumz_none`** → obje aslında **EMPTY + `instance_type='COLLECTION'`**
  (asset library'den gelen collection sahneye örnek olarak girmiş; asıl
  objeler sahneye bağlı olmayan collection'da). Çözüm: seç → **Object ▸ Apply
  (`Ctrl+A`) ▸ Make Instances Real**, alt-sol panelde **Keep Hierarchy**
  işaretle (varsayılan **kapalı**; armature→mesh parent'ı buna bağlı). Sonra
  geri oku: mesh'lerin Armature modifier hedefi **yeni** armature mı, isimlerde
  `.00N` eki var mı (orijinaller silinmediği için kopyalar ek alır).
  **Ölçüm:** Blender 5.2.1, StalkerAssetLibrary kaynaklı 3 empty
  (`red_forest_bridge_01_dynamic`: 1 armature + 11 mesh, hepsi Armature
  modifier'lı), 2026-09-11; menü yolu `VIEW3D_MT_object_apply` kaynağından,
  varsayılanlar operatör RNA'sından okundu.

### Sürüm / ortam
- ⛔ **Blender 5.x: `GPUShader(vertexcode, fragcode)` KALDIRILDI** →
  `gpu.shader.create_from_info`; **`GPUStorageBuf` yok** → dizi veri UBO'dan.
- **Kendi geçişini çizen draw handler solid geçişle aynı derinlikte** çizerse
  sahne z-fight eder → önce `gpu.state.active_framebuffer_get().clear(depth=1.0)`.
- **Blender 5.x compositor**: `scene.node_tree`/`use_nodes` kaldırıldı →
  `scene.compositing_node_group`; `CompositorNodeComposite` silindi → grubun
  `NodeGroupOutput`'u; düğüm ayarları giriş soketlerine taşındı.
- ⛔ **Blender 5.x: GN modifier'ında `mod["Input_3"]` KALDIRILDI**
  (`TypeError: this type doesn't support IDProperties`) → yol
  `mod.properties.inputs`, okuma/yazma **soketin kendisinden**:
  `getattr(mod.properties.inputs, ident).value`. `inputs[ident] = 12.0` float
  sokette `Cannot assign a 'float' value to the existing Group IDProperty`
  verir; **bool'da hata VERMEZ ama değeri bozar** — sessiz. `ident` node
  grubunun `interface.items_tree`'sinden gelir (`Input_3`, `Socket_11`);
  `inputs["Resolution"]` **KeyError** — ada göre erişim yok, ad→ident
  eşlemesini kendin kur. Yazdıktan sonra `obj.update_tag()` +
  `view_layer.update()`, sonra **geri oku** — bu tuzak yalnız geri okumayla
  görülür. **Ölçüm:** Blender 5.2.1, ORGANIC addon GN ağacı, 2026-09-09;
  dört erişim yolu ayrı ayrı denendi.
- **Koleksiyonu silmek objeleri silmez** (bake ışıkları öksüz kalıp sonraki render'ları aydınlattı). **Modül düzeyinde Image/Material
  önbelleği** dosya değişiminden sağ kalır → `StructRNA … removed`; her çağrıda `bpy.data`'dan bak. Blender alt modülleri önbellekler.
- **Yarıda kalan mutasyondan sonra "baştan çalıştır" güvenli değil** — mesh'ler taşınmış, ışıkta çökmüş; tekrar aynı ötelemeyi
  uyguladı. İşlem idempotent olmalı ya da durum önce okunmalı; tip filtresi baştan.
- **Render sonrası `Image.pixels` okumak güvenilir değil** (istisna → sessiz fallback) → ölçüm PIL ile dışarıda. **`dither_intensity`**
  8-bit yazımda gürültü ekler, üs alınınca benek olur → 0. **`read_homefile(use_empty=True)` sahne özelliklerini de siler** → ayarlar
  `AddonPreferences`'ta.
- **`execute_blender_code` her çağrıda YENİ namespace** — yardımcı fonksiyonu
  aynı çağrıda tanımla.
- **`read_factory_settings` eklentiyi kaldırır** (headless'ta Sollumz kaybolur).
  Aynısını **`--factory-startup`** yapar: hiçbir eklenti yüklenmez.
- ⛔ **Headless testte eklentiyi `sys.path` ile İKİNCİ kez register etmek ÇIKIŞTA sahte traceback basar.** Kullanıcı tercihleriyle
  açılan `-b`'de eklenti extension olarak (`bl_ext.user_default.<id>`) zaten kayıtlıdır; test aynı sınıfları yeniden kaydedince Blender
  "registered before, unregistering previous" der, kapanışta extension kopyasının `unregister`'ı
  `unregister_class(...): missing bl_rna … (may not be registered)` atar — eklenti hatası DEĞİL. Ayırt etmek için aynı testi
  `--factory-startup` ile koş (tek kopya: register → unregister → register temiz). Aşağıdaki "kapanırken unregister hatası"nın bir
  kaynağı olabilir; kilitlenmeyle ilişkisi ölçülmedi. Açık oturumda yeni kodu yüklemek: `addon_utils.disable(ad)` → `sys.modules`'tan
  `ad` ve alt modüllerini sil → `addon_utils.enable(ad, default_set=True)`; Scene `PointerProperty` değerleri korunur.
  **Ölçüm:** Blender 5.2.1, muto_ped_rig 0.2.0, 2026-09-12; headless iki koşu (tercihli: traceback, factory: temiz) + canlı oturumda
  yeniden yükleme (14 modül silindi, etiketler yeni, 5 sahne ayarı aynı).
- ⛔ **Kaydedilmemiş sahnede `render.filepath` GÖRELİ yolu sürücü köküne çözülür, cwd'ye DEĞİL.** Aynı betikte Python `open()` göreli
  yolu kabuğun cwd'sinden (proje) okur; `render.filepath = "out/video/frames_ws/0000.png"` ise `C:\out\video\frames_ws\0000.png`'ye
  yazar ve klasörü kendisi açar. Log `Saved: …` der, çıkış kodu 0, proje klasörü BOŞ — sessiz. Yola `os.path.abspath` uygula ve
  yazdıktan sonra kareleri HEDEF klasörde say. **Ölçüm:** Blender 5.2.1 `-b --factory-startup --python`, kabuk cwd = proje,
  2026-09-13; 2 × 585 kare `C:\out` altına yazıldı.
- ⛔ **`.blend` yayımlamak kişisel yolları da yayımlar.** Dosya, kaydedildiği makinelerin dosya tarayıcısı / asset kütüphanesi /
  preset yollarını düz metin taşır (dosyayı daha önce açıp kaydeden BAŞKA bilgisayarın kullanıcı adı dahil). `rg` ikili dosyayı ATLAR;
  Blender 5 `.blend`'i ZSTD sıkıştırılmış olabilir → ham bayt taraması da görmez: Blender'ın Python'undaki `zstandard` ile aç
  (`ZstdDecompressor().stream_reader(..., read_across_frames=True)`), sonra ara. `save_as_mainfile(copy=True)` kopyası izleri TAŞIDI.
  Temizlik: gereken datablock'ları `bpy.data.libraries.write(yol, {obj}, compress=True)` ile kişisel ad içermeyen bir klasöre yaz ve
  eşitliği doğrula. Blender 5'te eklenti özellikleri (ör. Sollumz `bone_properties`) `bone.get()` ile görünmez → karşılaştırmayı
  eklenti YÜKLÜ oturumda yap. **Ölçüm:** Blender 5.2.1, 2026-09-12; 1 şablon `.blend`: kaynak 14 iz (`C:\Users\<ad>\Desktop…`,
  `…\AppData\Roaming…\presets`, ikinci kullanıcı `…\OneDrive\…`), `save_as_mainfile` kopyası iz taşıdı, `libraries.write` kopyası 0 iz;
  128 kemik matris + Sollumz tag/bayrak eşit.
- **Eklenti kurulumunu kullanıcının Blender'ına DOKUNMADAN test et:** `BLENDER_USER_RESOURCES=<geçici klasör>` → önce
  `bpy.utils.resource_path('USER')` o klasörü mü veriyor bak, vermiyorsa DUR. Sonra `--online-mode --command extension repo-add <id>
  --url <index.json>` → `sync` → `list` → `install <paket> --enable`; ayrı `-b` açılışta `addon_utils.check('bl_ext.<id>.<paket>')`.
  Statik uzak depo: `extension server-generate --repo-dir <klasör> --html` (`index.json` + sürükle-bırak bağlantılı `index.html`,
  `archive_url` göreli) → GitHub Pages'e `gh-pages` dalı + `.nojekyll`; Pages'i açma `gh api -X PUT repos/<o>/<r>/pages` gövdesi
  stdin'den JSON (`/` içeren argüman Git Bash'te yola çevrilir). **Ölçüm:** Blender 5.2.1 + gh 2.100.0, 2026-09-12; Pages ~70 s'de
  canlı, zip `application/x-zip-compressed` ile 200; izole kurulum etkin, gerçek `extensions` klasörü ve `userpref.blend` hash'i değişmedi
  (1 eklenti).
- ⛔ **Sollumz'un modül ADI kurulum yoluna göre değişir; sabit adla import başka makinede boşa düşer.** Eski addon kurulumunda
  ad klasör adıdır (`Sollumz`, GitHub kaynak zip'inde `Sollumz-main`), eklenti kurulumunda `bl_ext.<depo>.sollumz`
  (`user_default`, `blender_org` ya da kullanıcının depo adı). Sabit adları `try/except ImportError` ile denemek iki kötülük yapar:
  ad tutmazsa `create_shader` hiç bulunmaz (sessiz yolda materyaller doku düğümsüz, bake **simsiyah**, render **bomboş gri**) ve
  Sollumz'un İÇİNDEKİ bir ImportError (ör. `No module named 'szio'`) da "bulunamadı" diye yutulur. **Yol:**
  `bpy.context.preferences.addons.keys()` içinde son ad parçası `sollumz` / `sollumz-…` / `sollumz_…` olanı bul, sürümü
  `addon_utils.module_bl_info(sys.modules[ad])["version"]`, sonra `importlib.import_module(ad + ".ydr.shader_materials")`;
  yakalanan istisnayı mesaja yaz. Sürüm gerçekleri (GitHub etiketleri): `create_shader` v2.3.0–v2.9.0 hep `ydr/shader_materials.py`'de;
  `Scene.sz_txds` ve `export_ytds_include` YALNIZ 2.9.0'da; `blender_manifest.toml` v2.5.0'dan beri. Sollumz 2.9 bağımlılığı `szio`
  eklenti klasöründe değil `<USER>/config/sollumz/data/lib/python3.x/site-packages`'tadır — izole testte o klasörü de kopyala.
  **Ölçüt:** `create_shader` sonrası malzemede `ShaderNodeTexImage` düğümü VAR olmalı. **Ölçüm:** 2026-09-12; uzak kullanıcı Blender
  5.1 + Sollumz 2.9.0: "Sollumz not found (create_shader)"; yerelde `Sollumz-main` adıyla kurulu 2.9.0 (izole `BLENDER_USER_RESOURCES`):
  eski iki ad ImportError → aynı mesaj, ad-bağımsız arama → bulundu, `ped.sps` 5 doku düğümü; normal `Sollumz` kurulumu da çalıştı.
- **Blender 5.2 bu makinede kapanırken kilitleniyor** — işi bitirip `.blend`'i
  kaydeder, unregister'da eklenti hata atar, süreç kapanmaz. Headless hatlar
  zaman aşımıyla sonlandırılır.
- ⛔ **`.blend`'i her export'tan sonra KAYDET** ve doğrulanmış çıktıyı tarihli
  klasöre kopyala. Hafızadaki ara veri (`bpy._X`) kalıcı değil; bir günlük iş
  yalnız export'larda kaldı, hareket tabloları gitti.
- **Ölçüt operatörün `{'FINISHED'}` demesi değil, KEYFRAME SAYISIDIR** — modal
  operatör `-b` modunda hiç çalışmadan başarılı görünür.
- ⛔ **`blender -b --python <yol>` 260 karakteri aşan yolda betiği HİÇ
  çalıştırmaz, çıkış kodu yine 0.** Log'da tek satır `OSError: Python file "…"
  could not be opened: No such file or directory`, gerisi normal açılış ve
  "Blender quit". Sebep yol **uzunluğu**; 8.3 kısa ad (`SUPERU~1`) değil.
  Claude'un scratchpad yolu tek başına bu sınırı aşar → betiği kısa yola koy
  (`%TEMP%\claude\<iş>\`). Ölçüt exit kodu değil, **betiğin yazdığı çıktı
  dosyasının varlığı**. **Ölçüm:** Blender 5.2.1, 272 karakterlik yol FAIL,
  aynı betik kısa yolda OK, 8.3 adlı kısa yol OK, 2026-09-11.
- ⛔ **Bu makinede yeni eklentinin N sekmesi "yok" görünür: kullanıcı addon'u
  `muto_plugins` her VIEW_3D/UI üst panelini `Plugins` sekmesine taşır ve
  `poll`'unu sarmalar.** Tablosunda adı geçmeyen sekme `Tools` grubuna düşer;
  Plugins'te o grup seçili değilse panel çizilmez. Eklenti etkin, panel kayıtlı,
  hata yok — sessiz. **Yalnız `bl_category`'yi geri yazmak YETMEZ:** sarmalayıcı
  poll sınıfta kalır, sekme yine çıkmaz. Kalıcı yol: `muto_plugins.py` içindeki
  `DOKUNMA`'ya sekme adı; açık oturumda timer içinde
  `muto_plugins._geri_al(cls)`. Ölçüt: `cls.bl_category` VE
  `cls.__dict__.get("poll")` modülü `muto_plugins` değil. **Ölçüm:** Blender
  5.2.1, `muto_ped_rig` `MPR_PT_main`, 2026-09-12; kategori geri yazıldı →
  kullanıcı yine göremedi; `_geri_al` + DOKUNMA → poll yok, kategori Muto Rig.
- ⛔ **`bpy.ops.object.mode_set` çağıranın BAĞLAM objesine uygulanır.** İçinde `view_layer.objects.active = arm` yapıp EDIT → OBJECT
  geçen fonksiyon dışarıdan `temp_override(object=mesh, active_object=mesh)` altında çağrılınca iskelet **EDIT'te kalır** — hata yok,
  ama EDIT'teki iskeletin pozu mesh'i **hiç deforme etmez**. Yalnız override'ı iskelete çevirmek de yetmedi (aktif obje başkayken EDIT'ten
  çıkmadı); `objects.active = arm` **ve** `temp_override(object=arm, active_object=arm, selected_objects=[arm])` birlikte çıkarır.
  Çıkışta `arm.mode` geri oku. Ölçüt: `evaluated_get` mesh'i ile orijinal vertex farkı > 0. **Ölçüm:** Blender 5.2.1, 2026-09-12;
  headless tekrar üretildi (eski EDIT, sabitlenmiş OBJECT, rest hatası 0,0 mm); canlı oturumda poz farkı 0 → 805 mm.
- ⛔ **Shape key'li mesh'te `mesh.vertices.co` yazmak görüntüye ve export'a YANSIMAZ** — değerlendirilmiş mesh basis key'den gelir;
  hata yok, mesh "değişmemiş" kalır (yeniden pozlama, rest'e çevirme gibi vertex taşıyan her işlem sessizce etkisiz). Yol: işlemden önce
  shape key'leri kaldır (`obj.shape_key_clear()`; yüz mimikleri gider) ya da işlemi durdur. `key_blocks[i].data`'ya yazmak ölçülmedi.
  Ölçüt: `evaluated_get(depsgraph)` mesh'inde konum farkı. Hazır karakterler shape key'le gelir (Ready Player Me glTF: 10 mesh'te 15 key).
  **Ölçüm:** Blender 5.2.1, 2026-09-12; shape key'li küpte `vertices.co` +1,0 yazıldı, değerlendirilmiş fark 0,0 (1 küp, test betiği).

---

## 3. CodeWalker.Core

- ⛔ **`.yed` bytecode'unu (`Streams`) okur ama YAZAMAZ.** `ExprMap.Count == 0`
  görmek "dosya boş" demek değildir; **kaydetmek `Streams`'i boşaltır**, yüz ve
  tüm prosedürel hareket ölür.
- ⛔ **XML okuyucu `.ypt`'de `FxcFileHash`'i ve `VFT`'yi YAZMAZ** → XML'den
  üretilen her `.ypt` shader'sız çıkar, hiçbir şey çizilmez (vanilla ikili
  `246470498`, XML turu `0`) → `scripts/ypt_xml_to_bin.ps1` hash'i yazar, geri
  okur, sıfırsa exit 1. **Genel ders:** yeni kaynak tipinde ilk iş vanilla
  dosyayı XML'e çıkarıp geri okumak ve alan alan karşılaştırmak.
  → `dallar/particle/sifirdan-ypt.md`
- ⛔ **`YtypFile.Save()` `compositeEntityTypes` bloğunu SESSİZCE DÜŞÜRÜR**
  (925 → 836 bayt). XML yolu düşürmez. → `dallar/map/yikim.md`
- **`.ytyp`/`.ymap` ikisi de `MetaFormat.RSC`** üzerinden yazılır — enum'da
  `ytyp`/`ymap` üyesi ARAMA (bulamayınca "yazamıyor" denip yanlış yola geçildi).
- **`YptFile.Load()` `RpfFileEntry` ister**; `null` geçilirse patlar → 
  `RpfFile::CreateResourceFileEntry([ref]$d,0)` + `ResourceBuilder::Decompress`.
- ⛔ **`ResourcePointerArray64<T>` üzerinde `foreach` → `NotImplementedException`**,
  yürüyüş sessizce yanlış sonuç verir → blok ağacında gezme, **bölerek daralt**.
- **`ClipBase.Name` OKUMA** → StackOverflow, exit 253, mesaj yok.
- **`Add-Type`'a `netstandard` referansı şart**; `Animation.BoneIds` dizi değil
  → `.data_items`.
- **GUI'de `LoadClipDict(string)` sözlüğü ada göre OYUN verisinden çözer** —
  resource klasöründeki serbest `.ycd` listede çıkmaz.
- ⛔ **`.ytd` XML şeması: `<TextureDictionary>` altında DOĞRUDAN `<Item>`**, `<Textures>` sarmalayıcısı yok; yanlış sarmalayıcı hata
  vermez, **57 baytlık boş sözlük** üretir. `XmlMeta.GetXMLFormat` **dosya adını** ister (`x.ytyp.xml`), kök etiketi verilince
  genel `XML` döner, `GetData` boş döner. ytyp/ymap için `XmlYtyp`/`XmlYmap` sınıfı yoktur.
- ⛔ **`RpfFile.ScanStructure()` anahtarsız çöker** (`GTA5Keys.LoadFromPath` önce); `try/catch` yutarsa tarama sessizce boş biter
  ve "doku GTA'da yok" sanılır (19/19 vardı). `RpfManager.Init` örnek metodu. **Kaç dosya okuduğunu daima yazdır**; sıfırsa arıza.
- ⛔ **`MetaHash` ≠ `UInt32`.** `archetypeName` bir `MetaHash`; `UInt32` anahtarlı
  hashtable'da `ContainsKey` hiç eşleşmez ve "kalıntı 0" okunur →
  `[uint32]$en._CEntityDef.archetypeName`.
- ⛔ **Kaynak dosya boyutu geçerlilik ölçütü DEĞİLDİR** (RSC7 zlib): 32.768 bayt
  açılmış `.ypt` → `Save()` 3.077 bayt aynı içeriktir. Tek ölçüt **geri okuma**.
- **Geri okumada çıkarılan DDS girdiyle BAYT BAYT aynı değildir** — başlığı CodeWalker kendisi yazar (flags'e `DDSD_PITCH`,
  pitch = satır baytı `4·w`, depth 1); piksel yükü aynıdır. Hash "farklı" der → **128. bayttan sonrasını** karşılaştır.
  Ölçüm: 2026-09-11, Sollumz 2.9 `.ytd` → `res_to_xml.ps1`, 9 doku A8R8G8B8 (8² ve 256²): yük 9/9 aynı, başlıkta 4 bayt farklı.
- ⛔ **`Unknown*` alanına "bilmiyorum, 0" yazma** — `UnknownA4..B0` mesafe
  bandıdır, 0 vanilla'da hiç geçmez; `Unknown10C` 1638/1736'da `0x10100`.
  **Dağılımına bak**, en sık değeri al.
- **CodeWalker XML'i bilmediği adı `hash_XXXXXXXX` yazar** (ytyp adı, doku, shader) → stream dosya adlarının / bilinen adların
  joaat'ini (büyük hex) tabloya koy, eşle; yeni adı **düz metin** yaz, derleyici hash'ler. Şablonla aynı hash kusur değildir
  (`hash_38DD00DF` = `normal_spec.sps`).
- **`.ycd` kanalında `StaticVector3`/`StaticFloat` = o kemik/eksen hiç kıpırdamıyor** — kanal var diye hareket var sanma;
  bir kemikte kanal tipleri **karışık** olabilir (X/Z `QuantizeFloat`, Y `StaticFloat`); hepsini liste beklersen hareketi kaçırırsın.
- **XML'e çevirirken nicemlemeyi ZATEN çözer** (`<Values>` düz float) — kendi
  çözücünü yazma; `CachedQuaternion` kanal değil işaretçi; `.//Animations`
  yanlış düğüm; iki klip tipi (`Animation`/`AnimationList`).
- **ymap yazarken `CalcFlags()` çağırma** (contentFlags 65→1), `CalcExtents()`
  kullanma (sıfır kutu), `CEntityDefs`'i doğrudan yazma (0 entity).
- **ymap adı tekil değil** — `rpfPath` olmadan LOD ölçümü yanlış çıkar.
  → `dallar/map/lod.md`
- **Property adları — yanlış ad `$null` döner, hata vermez** (bkz. §4): Bound `BoxMin`/`BoxMax`
  (`BoundingBoxMin/Max` değil), Drawable `DrawableModels`/`AllModels` (`DrawableModelsHigh` değil);
  `ShaderGroup.Shaders` foreach'te `NotImplementedException` → `.data_items`. Ölçüldü: yol-yikim, 2026-09-01.
- **CodeWalker taşınabilir `.exe` ise computer-use onu bulamaz** → GUI
  basamağını ajan süremez, kullanıcıya tarif verir.

---

## 4. PowerShell 5.1

- ⛔ **Betikler `powershell` (5.1) ile çağrılır, `pwsh` ile değil.** Ternary
  (`? :`) ve `??` yok; `[single](if (...) {...} else {...})` ayrışmaz ve hata
  *"'if' is not recognized"* diye gelir — ara değişken kullan.
- ⛔ **`[script]` gibi köşe parantezli yolda `Test-Path`/`Copy-Item`/`Remove-Item`
  jokerle çalışır** → **`-LiteralPath`**. `Copy-Item`'da SESSİZDİR: kopya hiç
  olmaz, hata çıkmaz; `stream/` eski sürümde kaldı, turlarca eski asset test
  edildi. Kopyadan sonra boyut/hash karşılaştır.
- **`-LiteralPath` joker GENİŞLETMEZ** — `"$dir\*"` hiçbir şey kopyalamaz. Joker
  gerekiyorsa `-Path`, köşe parantez varsa `-LiteralPath`.
- **`Split-Path -LiteralPath $p -Parent` 5.1'de `AmbiguousParameterSet` verir** → sonuç `$null`, ardından `Test-Path -LiteralPath $null`
  de hata basar; hedef klasör zaten varsa kopya yine olur, hata zararsız sanılır → `[IO.Path]::GetDirectoryName($p)`.
  Ölçüm: 2026-09-11, Windows PowerShell 5.1, `[script]` altına 13 dosyalık kopya döngüsü: dosya başına iki hata, kopyalar hash eşit.
- ⛔ **`-replace` büyük/küçük harf DUYARSIZDIR** — `'ABC'→'x'` kuralı `abc_modul`'ü
  de bozar → kod/ad değiştiriyorsan **`-creplace`**, sonra kalıntı taraması.
- ⛔ **`-File` ile virgüllü liste TEK STRING olur** ve sessizce bozulur (10 dosya
  istendi, "0 dosya çıkarıldı") → `-Command "& script.ps1 -Names @('a','b')"`.
- ⛔ **OLMAYAN property hata vermez, `$null` döner — ve `$null.Length` `0`'dır.**
  Yanlış yazılmış ad "ölçtüm, veri yok" dedirtir (`EffectRules` yerine `Effects`
  okundu, belgeye "CodeWalker `.ypt` yazamaz" yazıldı — araç çalışıyordu).
  Yabancı DLL'de önce `$o.GetType().GetProperties() | % Name`, ya da guard:
  `if(-not $o.PSObject.Properties[$ad]){ throw "PROPERTY YOK: $ad" }`.
- **`Add-Type` C# 5 derler**: `?.` çalışmaz.
- **Değişkenler büyük/küçük harf DUYARSIZ** — döngüdeki `$y` yedek yolu `$Y`'yi
  ezdi. Kısa ad + döngü = bu hata.
- **`"$S\$n.ymap"` yanlış yol üretir** (`$n.ymap` property sanılır) →
  `"$($n).ymap"` ya da `Join-Path`.
- **`@(@(x,y))` tek elemanlıysa DÜZLEŞİR** → `$k[0]`/`$k[1]` saçmalar, eşleşme
  sessizce kaçar ("0 silindi", çöp kutusu 1.1 m ötedeydi).
- **ASCII dışı karakter içeren `.ps1` BOM'suzsa 5.1 bozuk okur** →
  `denetle_plugin.py` bunu denetler.
- **`while read` döngüsünde `powershell` STDIN'i yutar** → `< /dev/null`.
- **İki CodeWalker betiği aynı PowerShell oturumunda `&` ile ard arda** (ölçülen çift: `.ycd` derleyicisi + `res_to_xml.ps1`) → AssemblyResolve işleyicileri
  birbirini çağırır, **StackOverflowException**, süreç sessizce ölür → her aracı ayrı `powershell -File` ile.
- **`res_to_xml.ps1 -Path` `[script]` yolunda çöker** ve klasörü `-Path` ile
  almaz → parantezsiz klasöre kopyala, `-Dir` + `-Filter`.

---

## 5. Python · Lua · kabuk

- ⛔ **Python `glob` içinde `[script]` karakter sınıfıdır** → hiç eşleşmez, hata
  vermez → `os.listdir`.
- **`argparse` help metnindeki `%` kaçışlanmalı (`%%`)**, yoksa `--help` `TypeError`.
- **Konsol Türkçe karakterde patlarsa `PYTHONIOENCODING=utf-8`.**
- ⛔ **Lua dosyasını Python ile yazarken kaçışlar bozulur** — `\n` gerçek satır
  sonuna dönüşüp string'i böldü, **hiçbir komut kayıtlı olmadı**; `lua_check`
  sözdizimi temiz gösterir. Bu satırları doğrudan `Edit` ile yaz.
- ⛔ **Türkçe kesme işareti (`'`) Lua string'ini KAPATIR — `lua_check` kaçırır.**
  Görünen metni locale dosyasına al.
- **`Wait()` command callback'inde çağrılamaz.**
- **Git Bash'ten çağrılan Windows `ffmpeg` `/c/...` yolunu açamaz** → `C:/...`.
- ⛔ **Git Bash `/` ile başlayan argümanı Windows yoluna ÇEVİRİR:** `gh api /licenses/gpl-3.0` → `C:/Program Files/Git/licenses/gpl-3.0`
  ("invalid API endpoint"). `> dosya` yönlendirmesi komuttan önce **boş dosyayı yine oluşturur**. Yol: baştaki `/`'ı at
  (`gh api licenses/gpl-3.0`). **Ölçüm:** gh 2.100.0, Git Bash, 2026-09-12; aynı uç nokta `/`'sız çalıştı (1 deneme).
- ⛔ **`np.argsort` varsayılanı (quicksort) EŞİT değerlerin sırasını numpy sürümüne göre değiştirir.** Eşitliğe duyarlı seçim (tam sayı
  mesafe/sayaçla sıralayıp "ilk gelen kazanır") Blender'ın numpy'si ile sistem Python'unun numpy'sinde FARKLI sonuç verir → Blender dışında
  koşan testler eklentinin Blender'daki davranışını ölçmez; hata vermez. Yol: seçimde `kind="stable"` (ya da açık ikincil anahtar,
  `np.lexsort`); `argpartition`'ın kararlı seçeneği yok. Ölçüt: aynı girdiyi iki ortamda koşup çıktı imzasını karşılaştır.
  **Ölçüm:** Blender 5.2.1 numpy 2.3.4 ↔ sistem Python numpy 2.5.1, 2026-09-12; 3 mesh girdisi: varsayılan sırayla 3,37 ↔ 3,26 cm ve
  bir vakada başarı ↔ hata; `kind="stable"` ile iki ortam 6 haneye kadar aynı.
- **`"stream$f.ydr"` tek parça gider**, dosya bulunamaz → yolu değişkenle ayrı kur.
- **`rm muto_t*` denek silerken üretimi de siler** — joker aralığını önce `ls`.
- **İndirilen ses tepe −25…−29 dB olabilir** → `volumedetect` ölç, normalize et.

---

## 6. FiveM çalışma zamanı

- ⛔ **Asset değiştikten sonra sunucudan ÇIKIP YENİDEN BAĞLANILIR.** Stream
  cache'lenir; **restart yetmez**. Bu atlanırsa bayat asset test edilir.
  Silahta ek: `str_requestFlush` (canary) ve **silahı önce elden bırak**.
- ⛔ **BOZUK STREAM VARLIĞI KAYNAĞIN TAMAMINI SESSİZCE DÜŞÜRÜR.** Sunucu
  "Started resource" yazar, istemcide hiçbir komut kaydolmaz, print yok, F8'de
  hata yok. Teşhis: `stream/` klasörü **olmayan** ikinci kaynak kur; onun komutu
  çalışıyorsa kusur stream'dedir. Lua'yı kurcalama.
- ⛔ **Kaynak iki klasördeyse FiveM birini sessizce yok sayar** → "görünmüyor"
  denince ilk bakılacak yer **sunucu logu**.
- **Varlık adında büyük harf olmaz.** Stream'e yeni dosya eklemek üç adımdır
  (dosya + manifest/`data_file` + çık/bağlan).
- ⛔ **Escrow (`.fxap`) kaynağın stream dosyası şifrelidir** — kopyalarsan
  istemci çöker ("Couldn't find asset key"). Çökme teşhisi: CitizenFX log `Error:`.
- **İstemciyi öldürmek hayalet oturum bırakır.**
- **`PtFxAssetStore Pool Full, Size == 400`** — havuz DOSYA sayar; **tek büyük
  `.ypt` oyunu dondurur** (ölçülmüş eşik). → `dallar/particle/dagitim-olcum.md`
- **`LoadResourceFile` ile istemcide JSON okuma çalışmadı** → Lua tablosu.
- **Harita objesinde `SetEntityCollision(false)` güvenilir değil** — görünmez
  olur, çarpışma kalır → `CreateModelHide`; **kontrol alınmadan
  `FreezeEntityPosition`/`SetEntityCoords` yok sayılır**; **donmuş objede
  kök-kemik klibi oynamaz**. → `dallar/prop/kapi-ve-hareket.md`
- **Handle önbellekleme** (`doorRegistered[hash]`, "handle değişti mi") —
  FiveM handle'ı yeniden kullanır → `IsEntityPlayingAnim` gibi **gerçeğe** sor.
- **`GetPedBoneIndex` / `GetPedBoneCoords` TAG alır, indeks değil.**
  → `govde/kemik-tag.md`
- ⛔ **`set` FiveM'in yerleşik convar komutudur** — `RegisterCommand('set')` sessizce ezilmez ama yerleşik olan çalışır ve
  *"Argument count mismatch"* verir. Test komutlarına önek ver. **`os._exit(0)` stdout tamponunu boşaltmaz** → önce `flush()`.
- **`.rel` / ses XML'lerinde isim uyuşmazlığı sessizce her şeyi bozar** (topluluk).
- **`DrawSpritePoly` kanonik ad değil** — `DrawTexturedPoly`; `/native-lint`
  uydurma sayar.

---

## 7. Dış araçlar (topluluk)

- **Rokoko `Auto Scale` açıkken root motion TAMAMEN silinir.**
- **Void Tools Vertex Color Bake mesh'e yazan tek araçtır** → öncesinde
  `.blend`'i tarihli kopyala. → `dallar/look/decal.md`
- **Five Toolkit silah kemik tag tablosu yanlış** → `kaynaklar/dis-arac.md` §1a
- **Sketchfab glb indirmeleri: "rigged" etiketine, ölçeğe ve yöne güvenme.**
  - **Kemik adları:** düğüm adlarına `_<sayı>` soneki eklenir (`hand_l_026`, `Thumb1.L_91`) → eşleme tam adla yapılır.
  - **Etiket:** "rigged" etiketli model iskeletsiz çıkabilir (skin 0); iskelet glb JSON'undaki `skins` alanından doğrulanır.
  - **Boy ve yön:** boy 51 m (düğüm ölçeği 0,807) ya da −90° X ile yatık gelebilir.
  - **Aksesuar:** ayrı iskelete bağlı aksesuar (balta) mesh'e karışır.
  - **İndirme zinciri:** `sketchfab.com/i/models/<uid>/download` (giriş gerekir) format ve boyut JSON'u verir →
    `/i/archives/latest?archiveType=glb&model=<uid>&textureMaxResolution=1024` imzalı S3 bağlantısı JSON'u verir → bağlantı tarayıcıda açılınca dosya iner.
  - Ölçüm: 6 model, 2026-09-12 (1 iskeletsiz, 1 51 m, 1 yatık + balta).

---

## Ayrıntı

### A. Sollumz `use_custom_settings` — kaynak

`sollumz_operators.py:415` ve `:132`:

```python
prefs_export_settings = self if self.use_custom_settings else get_export_settings()
```

Bayrak kapalıyken operatör kendi özelliklerini bırakıp **kullanıcı
tercihlerini** okur. `directory` ve `direct_export` ayar grubunun dışındadır,
bayraktan bağımsız çalışırlar — dosyalar doğru klasöre gittiği için kusur
gizlenir. Sessizce miras alınanlar: `apply_transforms` (True ise transform
**geometriye pişer**), `limit_to_selected` (False ise **tüm sahne**),
`target_formats` (CWXML ise XML), `target_versions`, `export_ytyps/ymaps/ytds`.

Doğrulama: tercihleri **kasten boz**, aktar, çıktının etkilenmediğini gör,
tercihleri geri yükle.

### B. Sollumz export formatı — `NATIVE` gerçekten binary yazar mı?

**Evet, ama koşullu — ve `.ycd` bu sistemin tamamen dışındadır.**

```python
# szio/gta5/native/__init__.py:7
IS_BACKEND_AVAILABLE = importlib.util.find_spec("pymateria") is not None
```

```python
# sollumz_preferences.py:377-378
if not self.target_formats or (not is_provider_available(AssetFormat.NATIVE)
                               and "CWXML" not in self.target_formats):
    self.target_formats = {"CWXML"}       # ← SESSİZ geri düşüş
```

Canlı testle doğrulandı (Blender 5.2 + Sollumz 2.8), çıkan dosyaların ilk 4
baytı okundu:

| Ayar | Çıktı | Boyut | İlk 4 bayt |
|---|---|---:|---|
| `NATIVE` + `GEN8` | `x.ydr` | 451 | `52534337` = **`RSC7`** (binary) |
| `CWXML` + `GEN8` | `x.ydr.xml` | 2.699 | `3c3f786d` = `<?xm` |
| `NATIVE` + `GEN8`+`GEN9` | `gen8/x.ydr` **ve** `gen9/x.ydr` | 451 / **558** | ikisi de `RSC7` |
| `NATIVE`+`CWXML`, tek sürüm | `x.ydr` **ve** `x.ydr.xml` | — | aynı klasöre ikisi |

Gen8 ile Gen9 çıktısı farklı boyutta — Gen9 kozmetik bir etiket değil, gerçekten başka bir dosya.

#### Gen8 / Gen9 — ölçülmüş ayrıntı

```python
# iecontext.py:99-100
gen8_directory = directory / "gen8"
gen9_directory = directory / "gen9"
```

- `("GEN9", "Gen9", "GTAV Enhanced", 2)` — Gen9 = **GTA V Enhanced**.
- İki sürüm birden seçilirse çıktı **`gen8/` ve `gen9/` alt klasörlerine**
  ayrılır. Tek sürüm seçiliyse dosyalar doğrudan hedef klasöre yazılır.
- ⚠ Hattımız tek çıktı yolu varsayıyor: `extract_asset.ps1` / `xml_to_res.ps1`
  çağıran her betik, iki sürüm açıkken dosyayı **beklediği yerde bulamaz**.
- Gen9'un ayrı shader varsayılanları var (`ShadersG9ParamsDefaults.json`,
  `ShadersG9TextureNameMapping.json`) ve ayrı adaptörleri
  (`drawable_gen9.py`, `fragment_gen9.py`, `texture_gen9.py`).

Her iki sağlayıcının desteklediği uzantılar aynı 8 tanedir:
`.ybn .ydr .ydd .yft .yld .ytyp .ymap .ytd`. `.ycd` bu listede yok:

```python
# ycd/ycdexport.py:574
clip_dict.write_xml(filepath)          # sabit kodlanmış XML
```

→ `.ycd` için ayrı derleme hâlâ **zorunlu**; `xml_to_res.ps1`'i `.ydr/.yft/.ybn` için
`NATIVE` çalışıyorsa atlayabilirsin. Ölçüm: `govde/bayraklar.md` §7'den
taşındı (2026-08).
