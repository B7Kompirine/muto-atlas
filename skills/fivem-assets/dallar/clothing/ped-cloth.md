# Ped cloth — pelerin, etek, duvak: karakterle birlikte süzülen kumaş

**Ne zaman okunur:** ped'in üzerinde **hareketle** dalgalanması gereken kumaş (pelerin, etek, duvak, palto eteği). Prop cloth (`.yft` env cloth) bunu YAPAMAZ: attach edilmiş fragment'ın fizik hızı sıfırdır, sim taşıyıcının hareketini görmez; vanilla `prop_flag_*` bile takılınca öne/yanlara savrulur (ölçüm: 2026-09, 2 model).
**When to read:** cloth on a ped that must react to the ped's motion (cape, skirt, veil). Environment cloth on an attached prop cannot do this.
**Kaynak:** Sollumz kaynağı `ydr/cloth_char.py`, `ydr/vertex_buffer_builder.py`, `ydd/yddexport.py` (main, 2026-09) · vanilla `csb_bride.yld`/`.ydd` dökümü · **Ölçüm:** kaynak okuma + 1 vanilla dosya + **1 kendi export'umuz** (bir pelerin, Blender 5.2 headless, Sollumz 2.9.0, 2026-09: `.ydd` 705 KB + `.yld` 6,5 KB, 221 sim vertex / 13 sabit / 3 kapsül, Diagnostics sıfır uyarı; oyun testi bekliyor).
**Önce:** `dallar/clothing/_dal.md` · gövde › `govde/arac-tuzaklari.md` §1

---

## Dosya sözleşmesi (vanilla)

- Cloth, drawable'ın **yanında ayrı `.yld`** dosyasıdır, adı aynı: `csb_bride.ydd` + `csb_bride.yld`, `uppr_000_u.ydd` + `uppr_000_u.yld`. `.ydd`'nin içinde değil, ped `.yft`'sinde değil.
- `.yld` içinde `Controller Type = 2` (env cloth `.yft`'de `3`), `BridgeSimGfx`, `VerletCloth1`, kemik ağırlıkları (`BoneIDs` + 4'lü `BoneWeightsIndices`) ve **yalnız Capsule** çocuklu bir Bound Composite.
- Kumaş yüzlerinin shader'ı **`ped_cloth.sps`**; gövdenin kalanı `ped.sps` (csb_bride: hash 2AAAA841 / 203B2307).
- `csb_bride`: 254 sim vertex, 24 sabit, 4 kapsül, 7 kemik (Pelvis, Spine0-3, iki Thigh).

## Sollumz iş akışı (kaynaktan)

1. **İki mesh:** görünen giysi mesh'i (DRAWABLE_MODEL, normal ağırlık boyalı) + ayrı, düşük çözünürlüklü **sim mesh'i**. Sim mesh'in `sollum_type = Character Cloth Mesh`, **drawable'ın çocuğu** (drawable da Drawable Dictionary'nin çocuğu). **Materyali olmaz.**
2. ⛔ **Sim mesh ≤ 254 vertex** (`CLOTH_CHAR_MAX_VERTICES = 254`); aşarsa hata basar ve cloth **export edilmez**. Pelerin için 12×18 ızgara = 216 yeter.
3. Sim mesh **her vertex'i kemik vertex grubuyla ağırlıklı** — sadece sabitler değil. Grupsuz vertex root'a düşer, uyarı verir. Pelerin: sabit sıra `SKEL_Spine3` 1.0, gerisi Spine3/Spine2'ye azalan.
4. Edit Mode → sidebar **Sollumz Tools → Cloth Tools**: üst sırayı seç → **Pin**. `Pin Radius → Fill Gradient` sabitlerden uzaklaşan yumuşak bağ verir. `Vertex Weight` (0.00001–1.0) kütle. Öznitelikler `.cloth.pinned`, `.cloth.weight`, `.cloth.pin_radius`, `.cloth.inflation_scale` olarak mesh'e yazılır.
5. **Çarpışma:** sim mesh'in **doğrudan çocuğu** olarak Bound Composite, içinde **yalnız Bound Capsule**; her kapsül `Copy Transforms` constraint'iyle bir kemiğe (Spine, Pelvis, Thigh). Kapsül dışı tip → "Only BOUND_CAPSULE type is supported".
6. **Görünen mesh'i bağla:** kumaşı takip edecek vertex'ler **`CLOTH` adlı vertex grubuna** (ağırlık 1.0). Export bu vertex'leri sim üçgenlerine barycentric bağlar; sim yüzeyine uzaklık **> 0.05 m** ise "Failed to bind N vertices" — görünen mesh sim mesh'in üstüne oturmalı.
7. `CLOTH` grubundaki yüzlerin materyali **`ped_cloth`** shader olmalı; yoksa "using non-cloth material… will not be skinned correctly".
8. Drawable Object Properties → **Character Cloth** paneli: `Weight`, `num_pin_radius_sets`. (`wind_scale`, `pin_radius_scale` runtime'da ezildiği için gizli.)
9. Export: Drawable Dictionary export'u `.ydd` + aynı adlı **`.yld`** verir (`make_bundle(dwd, ("", cld))`). Cloth adı = drawable adı (`.001` soneki atılır).
10. **Doğrulama kapısı:** Cloth Tools → **Diagnostics → Refresh**: "No material or binding errors." dışında her şey düzeltilir. Sonra `res_to_xml.ps1` ile `.yld`'yi dök: `VertexCount`, sabit sayısı, kapsül sayısı beklediğin mi.

## Headless üretim (ölçüldü, 2026-09)

Sollumz API'si Blender'ı açmadan `blender.exe -b --python make_cape.py` ile çalışır; şablon script
`kaynaklar/`'a değil projeye aittir, ama iskelet şu:
`create_armature_parent(ad, try_load_asset(freemode.yft))` → DWD armature · `create_empty_object(DRAWABLE)` →
`create_blender_object(DRAWABLE_MODEL, mesh)` + `sz_lods.high.mesh` + `add_armature_modifier` · sim mesh
`create_blender_object(CHARACTER_CLOTH_MESH)` + `mesh_add_cloth_attribute(PINNED/VERTEX_WEIGHT)` ·
`create_empty_object(BOUND_COMPOSITE)` → `create_blender_object(BOUND_CAPSULE)` + `create_capsule(axis="Y")` +
`rotation_euler Z=-90°` (kapsül Y'si kemik X'ine) + `add_child_of_bone_constraint` · export
`export_context_scope(ExportContext(ad, ExportSettings(targets=(AssetTarget(NATIVE, GEN8),)))) → export_ydd(dwd).save()`.
- ⛔ **Kapsüle collision materyali ver** (`create_collision_material_from_index(0)`), yoksa uyarı basar ve `.yld`'ye **0 kapsül** yazar.
- **Doku adı `image.filepath`'in taban adından** gelir (`image.name` değil). `accs_diff_000_a_uni.dds` diye kopyalayıp `filepath`'i ona çevir.
- Normal + spec `texture_properties.embedded = True` ile `.ydd`'ye gömülür; diffuse gömülmez, `<paket>^accs_diff_000_a_uni.ytd` olarak `dds_to_ytd.ps1` ile ayrı çıkar.
- Freemode `SKEL_Spine3` head = (0, 0.032, 0.283) ped uzayında; pelerin üst kenarı buna `(0, -0.17, +0.09)` ile oturdu.

## Paketleme (freemode addon giysisi)

`stream/`: `<paket>^accs_000_u.ydd` + `.yld` + `<paket>^accs_diff_000_a_uni.ytd` + `<paket>.ymt`
(CPedVariationInfo: `availComp` 12 yuva, accs = yuva 8; drawable'da **`clothData/ownsCloth = true`**, cloth'un
oyunda yüklenmesi buna bağlı). `data_file 'SHOP_PED_APPAREL_META_FILE'` ile ShopPedApparel `.meta`.
`.ymt` XML'den `meta_xml_to_bin.ps1` (2026-09'da `.ymt` eklendi) ile derlenir, `res_to_xml.ps1` ile geri okunur;
`dlcName` geri okumada hash görünür, `joaat(dlcName)` ile karşılaştır.

## Tuzaklar
- Freemode pelerin = `accs` ya da `jbib` bileşeni; `.yld` da aynı klasöre, `.ydd` ile aynı ad.
- Sim mesh drawable'la aynı origin'de, armature uzayında (`parent_matrix = Identity`).
- Ağırlık kuralı burada da geçerli: vertex başına ≤ 4 kemik, toplam 1.0.
- `res_to_xml.ps1` `.yld` ve `.ymt` okur (2026-09'da eklendi); `extract_asset.ps1 -Pattern '*.yld'` filtresiz çalıştırılınca DLC'lere gelmeden StackOverflow ile düşüyor, `-PathFilter` ver. Tek bir `dlc.rpf` için `RpfFile(path).ScanStructure()` + `Children` özyinelemesi yeter; RBF (`mp_creaturemetadata_*.ymt`) dosyasına RSC başlığı EKLEME, bozulur.
