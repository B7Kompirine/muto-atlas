# Kırılabilir / kemikli prop — fragment (.yft) üretimi

**Ne zaman okunur:** prop mermiyle parçalansın, ya da collision'ın kemik animasyonuyla hareket etmesi için zincirin 1. adımı (fragment kurmak).
**When to read:** a breakable or boned prop — building the fragment (`.yft`), per-bone collision, `physicsDictionary`, cloth world bounds.
**Kaynak:** eski SKILL 'FRAGMENT ÜRETİMİ' (2026-07) · **Ölçüm:** Sollumz kaynağı (`get_child_of_bone`), vanilla `Groups`, Fleeca kapıları oyunda
**Önce:** `_branch.md` · gövde › `trunk/flags.md` (`specialAttribute`), `trunk/tool-pitfalls.md` §1

---

## FRAGMENT ÜRETİMİ (zincirin 1. adımı)

Bir prop'un çarpışması kemik animasyonuyla birlikte hareket etsin istiyorsan
tek yol **fragment**tir. Denenip elenen yollar:

- `ASSET_TYPE_DRAWABLE`: tek statik bound, entity transform'una bağlı.
  Kemik animasyonu sadece görseli oynatır, çarpışma yerinde kalır.
- **YED / expression**: ÇALIŞAN YOL BUDUR (tam reçete public sürümde yok).

  > ⚠️ Bu satırda önceden **"YED ile collision animasyonu diye bir şey yok"**
  > yazıyordu. YANLIŞTI ve saatlerce yanlış yöne gidilmesine sebep oldu.
  > Hatanın kaynağı: CodeWalker ile `.yed` açılıp `ExprMap.Count == 0`
  > görülmesi ve "dosya boş" sanılması. Gerçek şu ki **CodeWalker
  > expression bytecode'unu (Streams) YAZAMAZ, sadece okuyabilir** — ve bu
  > kullanımda `Streams` zaten boştur, iş `Tracks` tarafında döner.
  > Yani ölçülen şey aracın sınırıydı, dosyanın içeriği değil.
  > **Bir aracın bir şeyi göstermemesi, o şeyin yok olduğu anlamına gelmez.**

### Sollumz'da fragment kurma — bound'u kemiğe bağlayan şey

`parent_bone` **DEĞİL**, isim eşleşmesi de **DEĞİL**. Sollumz bağı
`COPY_TRANSFORMS` constraint'inden okur (`tools/blenderhelper.py`,
`get_child_of_bone`). Constraint yoksa `does_bone_have_collision` false
döner, kemik sessizce atlanır ve export **uyarı bile vermeden**
`PhysicsLODGroup`'u boş bırakır — dosya üretilir ama işe yaramaz.

Her collision objesi için:

```python
c = col_obj.constraints.new("COPY_TRANSFORMS")
c.target = frag_armature_obj
c.subtarget = "KemikAdi"
c.mix_mode = "BEFORE_FULL"   # set_child_of_constraint_space ile aynı
c.target_space = "POSE"
c.owner_space = "LOCAL"
```

Ayrıca:
- `bone.sollumz_use_physics = True` **sadece** collision'ı olan kemikte.
- `col_obj.child_properties.mass` varsayılan 0; 0 bırakılırsa archetype
  kütlesi de 0 olur. Bound hacmine göre dağıt.
- Kırılmasın istiyorsan `bone.group_properties.strength = -1`.
- Bound composite fragment armature'ının **doğrudan** çocuğu olmalı,
  drawable'ın altında değil.
- Kemik başına birden fazla bound serbesttir (`child_cols` kemik adına göre
  gruplanır).

### EN ÇOK VAKIT KAYBETTİREN TUZAK: kök grup

`parentIdx = 255` olan grup **entity gövdesidir**. Onun çarpışması entity
transformuna kaynaklıdır ve **kemiği takip etmez**. Tek gruplu bir fragment
üretirsen o grup zorunlu olarak kök olur; export kusursuz görünür,
`PhysicsLODGroup` dolu çıkar, ama oyunda animasyon oynar ve collision
yerinde kalır — yani hiçbir şey kazanmamış olursun.

**En az iki grup gerekir:**

```
grup[0]  kök kemik (tag 0)   parentIdx=255   -> SABIT taban/menteşe
grup[1]  hareketli kemik      parentIdx=0     -> DÖNEN parça (kanat, kapak)
```

Hareket eden parça **çocuk** grupta olmalı. Kök gruba da mutlaka bir
collision ver (yoksa Sollumz o kemiği atlar ve tek gruba düşersin) —
dönme ekseni üzerindeki küçük parçalar bu iş için idealdir, döndüklerinde
konumları zaten değişmez.

Doğrulama: `Groups` listesinde parentIdx=255 olanın boneTag'i **0**
olmalı; hareketli kemiğin tag'i çocuk grupta görünmeli.

### physicsDictionary asla 0 bırakılmaz

Collision `.ydr`/`.yft` içine gömülü olsa bile oyun onu **archetype'ın
physicsDictionary'sinden** bulur. 0 verirsen model görünür ama içinden
geçilir. Vanilla arşivinde tek bir kapı prop'unda bile 0 yoktur
(`v_ilev_gb_teldr` → 2110158618, `prop_ld_garaged_01` → 427433450).

Kendi prop'umuzda doğrusu **kendi ad hash'i**: `-PhysicsDictSelf`.
`textureDictionary` ise dokular gömülüyse 0 kalabilir.

### ytyp tarafı

`assetType` bir **property**dir (alan değil), tipi
`rage__fwArchetypeDef__eAssetType`. Fragment için:

- `assetType = ASSET_TYPE_FRAGMENT` — drawable kalırsa oyun per-bone
  collision kurmaz, tüm emek boşa gider.
- `physicsDictionary = kendi ad hash'i` (0 değil).
- `textureDictionary = 0` — Sollumz dokuları .yft'ye gömer.
- `specialAttribute = 0` — animasyonu script oynatıyorsa bu bir kapı
  sistemi kapısı değildir.

`make_ytyp_override.ps1 -AssetType ASSET_TYPE_FRAGMENT -ClearDicts
-PhysicsDictSelf` bunu üretir.

### Doğrulama

Export "FINISHED" demesi yeterli değil. `cw_to_xml` ile .yft'yi döküp bak:
`<Physics><LOD1>` altında `<Groups>` dolu mu, `<Children>` sayısı bound
sayısına eşit mi, hepsinin `<BoneTag>`'i doğru kemiğin tag'i mi. Çalışan bir
referans fragment varsa aynı alanları yan yana karşılaştır.


---

## Cloth duvarın içine giriyor — fragment `worldbound`

Duvara asılı cloth rüzgârda **duvarın içine geçiyorsa** çözüm fragment'ın
**World Bounds** alanıdır (script değil, collision değil).

1. Binayı **ve** ymap'ini Blender'a al (dünya koordinatı için), kendi ymap'ini
   **Instance Entities** açık import et.
2. **Bound Composite** oluştur, adı `<obje>_worldbound`.
3. İçine **Bound Plane** ekle (Sollumz'da *"cloth only"* yazar).
4. ⭐ **Bound plane her yöne sonsuz uzanır ve YALNIZ bağlandığı `.yft`'yi
   etkiler** — yanındaki objeye dokunmaz. Kutunun tek bir yüzü gibi düşün.
5. **Face Orientation overlay'ini aç** — normal doğru tarafa bakmalı
   (örnekte duvara göre 70° döndürüldü).
6. Fragment → Object Properties → **World Bounds** → bound composite'i seç.
7. Bound plane'e **varsayılan materyal**, **hiç bayrak yok**.
8. **Yalnız `.yft` export edilir**; bound ayrıca export edilmez.

- ⚠️ **Cloth'u sonradan taşırsan world bounds'u yeniden yapman gerekir.**

**Ölçüm:** Stumpy Mason 9 dk (`NDYv0EnWvhg`), `notlar/07` §3, 2026-09.
