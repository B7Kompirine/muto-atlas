<img src="../assets/logo.png" alt="muto-atlas" width="128" align="right">

# muto-atlas

**FiveM / GTA V geliştirmesinde yer gerçeği.** Oyunun kendi verisine bakıp cevap
veren, tahmin etmeyen bir Claude Code plugin'i.

[← English README](../README.md)

---

## Neden var

Bir kapıyı açtırmak istiyorsun. `AddDoorToSystem` denersin, olmaz.
`FreezeEntityPosition` denersin, olmaz. `SetEntityDynamic`,
`NetworkRequestControlOfEntity`… yarım saat gider.

Cevap oyunun kendi `.ytyp`'sinde tek satırdı:

```
specialAttribute = 0   → bu obje KAPI DEĞİL, kapı sisteminde menteşesi yok
```

Tek sorgu, ilk satır kodu yazmadan önce bunu söylerdi:

```bash
assetdb.py door v_ilev_gb_teldr
```

Bütün fikir bu: **önce veriye bak, sonra kod yaz.**

## Kurulum

### 1. Plugin'i kur — iki komut, klonlama yok

```bash
claude plugin marketplace add B7Kompirine/muto-atlas
claude plugin install muto-atlas@muto-atlas
```

Claude Code'u yeniden başlat. Artık **19 komutun** ve **2 skill'in**
(`fivem-natives`, `fivem-assets`) var.

| | |
|---|---|
| **Veriyi sorgula** | `/asset` `/native` `/where` `/anim` |
| **Dallar** (kurallar + yapraklar) | `/map` `/prop` `/clothing` `/particle` `/look` `/vehicle` |
| **Denetle & kur** | `/asset-setup` `/asset-build` `/native-lint` `/help` |
| **Araç yolları** | `/paths` `/codewalker` `/gta` `/server` `/blender` |

> **Skill'ler plugin'in içinde gelir — ayrıca kurulmaz.** FiveM prop'u, harita,
> görünüm, partikül ya da native işi yaptığında, sen hiç komut yazmasan bile
> kendiliğinden devreye girerler.

### 2. Veri katmanlarını üret

Plugin **hiç oyun verisi taşımaz**; bu adımı yapana kadar komutların cevaplayacak
bir şeyi olmaz. **GTA V ve CodeWalker gerekir** — bu işi yapan herkeste ikisi de
zaten vardır; eksik olan veri değil, **yol bilgisidir.**

En kolay yol, Claude Code içinde:

```
/asset-setup
```

Ne bulabiliyorsa bulur, eksik yolu **sana sorar**, kalanı kurar. Elle de olur:

```bash
python scripts/setup.py --save \
  --gta        "C:\Program Files\Epic Games\GTAV" \
  --codewalker "C:\...\CodeWalker\CodeWalker.Core.dll" \
  --resources  "C:\...\sunucun\resources"
```

`--save` yolları `data/config.json`'a yazar; bir daha sorulmaz.
`scripts/` kurulu plugin klasöründedir (`${CLAUDE_PLUGIN_ROOT}`, tipik olarak
`~/.claude/plugins/cache/muto-atlas/muto-atlas/<sürüm>`).

Doğrulama:

```bash
python scripts/assetdb.py stats
```

### Neden veri repoda yok

İki sebep, ikisi de ölçüldü:

1. `entities.db` tek başına **214 MB**; GitHub'ın dosya sınırı 100 MB. Push
   teknik olarak reddedilir.
2. Rockstar'ın verisi. Yeniden dağıtımı telif sorunudur.

Yan faydası: herkesin katmanı **kendi oyun sürümünden** gelir. Merkezî bir kopya
dağıtılsaydı herkes tek bir sürüme mahkûm olurdu.

## Bilgi veritabanı — proje, snippet, etiket

`scripts/build_atlas_db.py` bilgi ağacını tek bir SQLite dosyasına döker: `data/atlas.db`.
Dosya yerelde üretilir, depoya girmez.

- **Proje adı klasör adından gelir.** Her dal klasörü (`map`, `prop`, `look`, …), gövde (`govde`),
  kaynaklar (`kaynaklar`) ve `fivem-natives` birer projedir. Kendi notlarını `--source notlarim/`
  ile ekle; o klasörün her alt klasörü bir proje olur.
- **Her dosya snippet'lere bölünür:** her başlık bir snippet, kod blokları ayrı snippet. Uzun
  bölümler boş satırdan bölünür, satır ortasından kesilmez.
- **Her snippet'i Claude etiketler**, sabit bir sözlükten seçerek (varsayılan `claude-opus-5`;
  `--model` ve `--effort` ile değişir). Etiketler içerik özetiyle önbelleğe alınır: yeniden
  üretim — yarıda kesilmiş bir üretimin tekrarı da — yalnız henüz etiketi olmayan snippet'leri
  gönderir. `claude-opus-5` isteklerinde sunucu tarafı reddetme yedeği (`fallbacks: "default"`)
  açıktır. `anthropic` paketi ya da kimlik bilgisi yoksa betik bunu söyler ve çevrimdışı anahtar
  kelime kurallarına geçer.
- **Tam metin arama** (SQLite FTS5): komut satırından ya da MCP sunucusunun `snippet_search`,
  `snippet_read` ve `snippet_tags` araçlarıyla.
- **Çıkış kodları:** 0 bulundu / yazıldı · 1 sonuç yok · 2 veritabanı yok ya da Claude istendi ama
  kullanılamıyor (hiçbir şey yazılmaz) · 3 veritabanı okunamadı ya da doğrulama tutmadı (eski dosya korunur).

```bash
python scripts/build_atlas_db.py                         # auto: Claude varsa Claude, yoksa kurallar
python scripts/build_atlas_db.py --tagger claude         # python -m pip install anthropic + kimlik bilgisi
python scripts/build_atlas_db.py --source notlarim/      # klasörlerin proje olur
python scripts/build_atlas_db.py --search "TimeFlags" --project look
python scripts/build_atlas_db.py --stats
```

## Diğer yapay zekâ araçları

muto-atlas Claude Code'a bağlı değil. İki yol var; biri ya da ikisi birden kullanılabilir.

### Agent Skills — Codex, ChatGPT masaüstü, Cursor, GitHub Copilot, Gemini CLI

İki skill açık [Agent Skills](https://agentskills.io/specification) biçimindedir. Depoyu klonla,
veri katmanlarını bir kez kur (yukarıdaki 2. adım), sonra skill'leri aracının klasörüne kur:

```bash
python scripts/install_skills.py                  # ~/.agents/skills (Codex, ChatGPT masaüstü, Gemini CLI, VS Code Copilot, Cursor)
python scripts/install_skills.py --tool cursor    # ~/.cursor/skills
python scripts/install_skills.py --tool copilot --project proje/yolu   # .github/skills
python scripts/install_skills.py --check          # yalnız denetle, yazma
```

Kurucu her skill'i kopyalar, Claude Code'un yol değişkenini klonunun mutlak yoluyla değiştirir
ve kopyayı geri okur. `git pull`'dan sonra yeniden çalıştır; kopyalar kendiliğinden
güncellenmez. Slash komutları yalnız Claude Code'dadır.

### MCP sunucusu — Cursor, VS Code, Claude Desktop, Codex, Gemini CLI, ChatGPT

`scripts/mcp_server.py` aynı sorguları MCP aracı olarak sunar: asset ve kapı sorgusu, animasyon
ve partikül adları, bayrak çözme, native doğrulama, bilgi ağacı ve — yalnız yerelde — `doctor`,
yapısal diff, ışık çözme ve Lua linter. Her sonuç çıkış koduyla ve o kodun anlamıyla başlar.
`mcp` Python paketi gerekir (1.28 ile denendi): `python -m pip install "mcp>=1.28"`.

Claude Desktop (`claude_desktop_config.json`), Cursor (`~/.cursor/mcp.json`) ve Gemini CLI
(`~/.gemini/settings.json`) şu biçimi kullanır; VS Code (`.vscode/mcp.json`) aynı girdiyi
`"mcpServers"` yerine `"servers"` altında ister:

```json
{
  "mcpServers": {
    "muto-atlas": {
      "command": "python",
      "args": ["C:/klonun/yolu/muto-atlas/scripts/mcp_server.py"]
    }
  }
}
```

Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.muto-atlas]
command = "python"
args = ["C:/klonun/yolu/muto-atlas/scripts/mcp_server.py"]
```

**ChatGPT** yalnız uzaktaki sunuculara (streamable HTTP ya da SSE) Developer mode üzerinden
bağlanır (Plus, Pro, Business, Enterprise, Education — Settings → Security and login →
Developer mode). Sunucuyu HTTP modunda çalıştır ve önüne bir HTTPS tüneli koy:

```bash
python scripts/mcp_server.py --http --port 8765 --allow-host tunel-alan-adin.example.com
```

Sonra ChatGPT'de `https://tunel-alan-adin.example.com/mcp` adresiyle bir developer-mode
uygulaması oluştur. ⚠️ HTTP modunda kendi dosyalarını ya da kendi sunucunun haritasını okuyan
araçlar (`doctor`, `structural_diff`, `light_read`, `lua_lint`, `framework_api`, `lodaudit`)
kaydedilmez, çünkü tünel sunucuyu kimlik doğrulaması olmadan internete açar. Veri katmanlarını
sunucu klasörünle kurduysan özel arketip adların yine sorgulanabilir. Bütün araçlar salt okunur
(`readOnlyHint`) işaretlidir. İşin bitince tüneli kapat.

## Ne veriyor

24 çevrimdışı veri katmanı:

| katman | satır | neyi cevaplar |
|---|---:|---|
| arketip | 316.975 | kapı mı, pivot nerede, fiziği var mı |
| dünya yerleşimi | 3.054.420 | bu model dünyada nerede duruyor |
| ymap LOD zinciri | 3.145.882 | uzakta neden titriyor / kayboluyor |
| animasyon klibi | 315.964 | süre, iz sayısı, hangi iskelet |
| animasyon adı | 269.414 | `TaskPlayAnim` için sözlük + klip |
| iskelet kemiği | 478.055 | kemik adı ↔ tag ↔ parent |
| dünya nesnesi | 33.912 | **etiketli** ATM, kamera, bank… **rotasyonla** |
| prop | 21.631 | `CREATE_OBJECT` ile spawn edilebilir |
| framework API | 12.713 | sunucunun gerçekten tanımladığı export/event |
| native | 7.191 | imza, apiset (client/server/shared), hash |
| ytyp extension | 64.209 | partikül, merdiven, ışık, expression |
| partikül efekti | 2.549 | `StartParticleFx*` için geçerli `fxName` |
| expression | 2.338 | prosedürel kemik hareketi, yay |
| ped | 1.109 | klip sözlüğü, expression seti, movement clipset |
| araç | 921 | handling id, mod kit, extra |
| IPL | 895 | sınır kutusu, `RequestIpl` / `RemoveIpl` |
| MLO iç mekân | 853 | her iç mekânın her dünya yerleşimi |
| silah + parça | 184 + 634 | bileşen, livery, takılma kemiği |
| …ayrıca | | shader, collision materyali, decal, procedural, senaryo |

Artı bir **Lua linteri**: uydurma native, sunucuda çağrılan client-only native,
yanlış argüman sayısı, per-frame performans hataları.

## Kullanım

```bash
assetdb.py door    v_ilev_gb_teldr        # kapı sistemi bunu oynatır mı
assetdb.py show    prop_atm_01            # tam künye + yorum
assetdb.py where   prop_atm_01            # dünyadaki tüm yerleşimleri
assetdb.py world   --near 147,-1035,29 --radius 50   # bu noktanın çevresinde ne var
assetdb.py pedmeta a_c_rottweiler         # klip sözlüğü, expression, clipset
assetdb.py weapon  WEAPON_CARBINERIFLE --parts       # bileşenler + takılma kemikleri
assetdb.py vehicle adder                  # handling id, mod kit, extra
assetdb.py mlo     v_genbank              # iç mekân + tüm dünya konumları
assetdb.py anim    weld                   # sözlük + klip + süre
assetdb.py fx      <ad> --exact           # bu gerçek bir partikül efekti mi
assetdb.py framework --check              # çalışma anında patlayacak export/event
assetdb.py stats                          # ne kurulu, ne eksik
```

### Kendi dosyalarını denetlemek — oyuna girmeden

Yukarıdaki komutlar *vanilla* hakkında soru cevaplar. Aşağıdakiler **senin**
dosyalarına bakar: bozuk bir asset sana bir tur değil, bir denetim maliyetine
gelsin diye.

```bash
assetdb.py doctor  stream/ -r            # sessiz hata kapısı: hata vermeden ne çalışmayacak
assetdb.py diff    seninki.yft vanilla.yft   # hangi DÜĞÜMLER farklı (değer değil)
assetdb.py light   prop_lamp.ydr         # gömülü ışıklar: saat, koni, menzil, bayrak
assetdb.py light   --table               # ölçülmüş vanilla ışık referansı
assetdb.py timecycle --mlo ic_mekan.ytyp # oda → modifier → ambient
```

`doctor` üç seviye raporlar: **FATAL** (oyun çöker / kaynağın tamamı düşer),
**SILENT** (hiç hata vermeden çalışmaz — en pahalı sınıf), **WARN** (olağandışı).
Denetleyemediği dosyalar ayrı bölümde listelenir ve **asla temiz sayılmaz**.

`diff` alan değerlerini değil düğüm *varlığını* karşılaştırır. Bir Sollumz
export'u "0 uyarı" verip yine de oyunu çökertebilir, çünkü sorun yanlış bir
değer değil komple eksik bir düğümdür; değer karşılaştıran hiçbir denetim
bunu bulmaz, düğüm kümesi karşılaştıran bulur.

### İç mekân neden karanlık

Cevap genelde prop'ta da ışıkta da değil, odanın **timecycle modifier**'ında.
Oda kendi modifier'ını çözülmemiş bir JOAAT hash olarak tutar
(`hash_CDE50982`); `--mlo` bilinen 1087 modifier adını hash'leyip geri çözer
ve aydınlatılmamış bir yüzeyin görünüp görünmeyeceğini belirleyen iki çarpanı
gösterir. İkisi de `0.000` ise doğrudan aydınlatılmayan hiçbir şey çizilmez —
prop ayarıyla telafi edilemez.

Aynı modifier adı çoğu zaman birden fazla DLC'de tanımlıdır (1087'nin 691'i).
Hangisinin kazandığı DLC yükleme sırasına bağlıdır ve dosyalardan **okunamaz**,
o yüzden çakışma gizlenmez, raporlanır.

Her kural dayandığı ölçümle birlikte kaynakta yazılıdır. Ölçüm soruyu
**çözmüyorsa** araç bunu da söyler: `TimeFlags 0` değeri 72.539 vanilla ışığın
yalnızca 8'inde geçer, ama o 8'i iç mekân lamba prop'udur — yani "hiç yanmaz"
ile "saat kısıtı yok" okumalarının ikisi de veriyle uyumludur. O denetim
*kusur* değil, *şüpheli, oyunda doğrula* diye raporlanır.

## Çıkış kodları

```
0  bulundu
1  sorgu çalıştı; ad otoritede yok
2  veri katmanı kurulu değil — sonuç hakkında HİÇBİR ŞEY iddia edilemez
3  iç hata (bozuk dosya)
```

`2`'yi `1` sanmak, **veri eksikliğini varlık yokluğu sanmak** ve sonra tahmin
etmektir. Bu plugin tam olarak onu önlemek için var. `stats` asla `2` dönmez —
neyin eksik olduğunu söyleyen komut odur.

## Dil

Çıktı varsayılan olarak İngilizce. Türkçe için:

```bash
assetdb.py --lang tr ...                    # tek çağrı
export MUTO_ATLAS_LANG=tr                   # oturum boyu
python scripts/setup.py --lang tr --save    # kalıcı
```

## Tasarım kuralları

Bunlar üslup tercihi değil; her biri sessiz bir hatadan öğrenildi.

- **Ölç, varsayma.** Belgedeki her sayının onu üreten bir komutu var.
- **Aracın bir şey göstermemesi, o şeyin olmadığının kanıtı değildir.** Satır
  yokluğu asset yokluğu değildir; olmayan bir property `None` döner ve
  `None.length` **`0`**'dır.
- **Adlar kaynaktaki hâliyle saklanır, join daima küçük harf üzerinden kurulur.**
  Dump adları `MixedCase`, plugin katmanları küçük harf — birebir join her ailede
  sessizce sıfır döndürür.
- **Her yazma geri okunur.** "Komut hata vermedi" yazıldığının kanıtı değildir.
- **Eksik çeviri anahtarın kendisini basar**, boş string değil — boşluk fark
  edilmezdi.

---

## specialAttribute — kapı tablosu

Adlar **Sollumz 2.9 kaynağından** (`ytyp/properties/ytyp.py:53`), kapı yeteneği
316k archetype üzerinde **ölçülerek** doğrulandı: `Enable Door Physics` bayrağı
(bit 26) kurulu 1176 archetype'ın `specialAttribute` dağılımı.

| değer | Sollumz adı | door physics'li adet | kapı sistemi |
|---|---|---:|---|
| 7 | Normal Door | 646 | ✅ |
| 5 | Garage Door | 77 | ✅ |
| 8 | Sliding Door | 71 | ✅ |
| 10 | Sliding Vertical Door | 7 | ✅ |
| 12 | Rail Crossing Barrier Door | 2 | ✅ |
| 9 | Barrier Door | **0** | ❌ |
| 14 | Single Axis Rotation | **0** | ❌ prosedürel dönüş (çatı fanı) |
| 0 | None | **379** | ⚠ bayrağa bak |

⚠ **`specialAttribute` tek başına yetmez:** 379 archetype `=0` olduğu hâlde
door physics taşıyor. `assetdb.py door` artık bayrağı da raporluyor.

Tam tablo (21 değer) + entity/archetype bit tabloları + extension tipleri:
`skills/fivem-assets/govde/bayraklar.md`

## Bayrak çözme

```bash
python scripts/assetdb.py flags 549584896            # archetype (ytyp)
python scripts/assetdb.py flags 1572872 --entity     # entity (ymap)
```

```
1572872  (0x180008)  ->  ENTITY (ymap) bayragi
              8  bit3   LOD in Parented YMAP
         524288  bit19  Cast Static Shadows
        1048576  bit20  Cast Dynamic Shadows
```

## İndeksi kurma

```bash
# archetype — CodeWalker.Core.dll + GTA V kurulumu gerekir, ~20 sn
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_archetypes.ps1 `
    -ExtraFolders "<sunucu resources yolu>"

# dünya konumları — ~50 sn + ~20 sn, entities.db ~214 MB
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_entities.ps1
python scripts/build_entities_db.py    # --drop-tsv ile ara dosyayı sil

# animasyon klipleri (.ycd) — süre + kemik, ~3 dk
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_clips.ps1

# iskelet (.ydr/.yft) + expression (.yed) — uzun sürer
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_rigs.ps1

# animasyon adı / prop / senaryo listesi — internet gerekir
python scripts/build_anims.py          # --offline ile önbellekten
```

`build_entities.ps1` varsayılan olarak LOD/arazi parçalarını atlar; `-All` ile
hepsi indekslenir (indeks ~10x büyür).

`build_archetypes.ps1` CodeWalker ve GTA V yollarını kendi bulur; bulamazsa
`-CodeWalker` / `-GtaFolder` ile verilir.

## Klip → model eşleştirme (`clipfit`)

Bir klibin hangi modelde oynatılmak üzere yapıldığını **kemik tag'leriyle**
bulur. Kemik sayısı yanıltıcıdır (aynı kemiğin konum/rotasyon izleri ayrı
sayılır); tag seti ise modeli tek başına belirler.

```
$ assetdb.py clipfit anim@heists@fleeca_bank@bank_vault_door bank_vault_door_opens
  hedefledigi kemik tag'leri (3): [0, 10596, 50607]
  TAM ESLESME (1 model):
    hei_prop_heist_sec_door    3 kemik  [ydr]
```

72.364 kemikli model içinde tek aday. bbox'ı haritadaki `v_ilev_gb_vauldr`
ile birebir aynı → animasyonlu ikizi. **Prop swap** deseninin kaynağı budur.

## ytyp override üretimi

Archetype yanlış tanımlıysa (kapı olması gereken obje `specialAttribute=0`):

```bash
powershell -File scripts/make_ytyp_override.ps1 `
    -Models v_ilev_gb_teldr -SpecialAttribute 7 `
    -YtypName my_fleeca_doors -OutFile "<resource>\stream\my_fleeca_doors.ytyp"
```

Kaynağı RPF'ten okur, tüm alanları birebir kopyalar, tek değeri değiştirir.
Çıktı `data_file 'DLC_ITYP_REQUEST'` ile bildirilerek yüklenir.

## Sınırlar

Kapsamayanlar:

- fragment iç yapısı / bone listesi (.yft)
- animasyon süresi ve eventleri (.ycd)
- sunucunun kendi MLO'larının iç yerleşimi (archetype'ları gelir, iç entity
  genişletmesi vanilla ymap'lere bağlıdır)

Bunlar için CodeWalker'da bakmak ya da oyun içi ölçüm gerekir.

## Dünya konumu doğrulaması

MLO iç mekân matematiği (`world = mloPos + rotate(localPos, mloRot)`, ham
quaternion) bağımsız ölçümle doğrulandı:

| kaynak | v_ilev_gb_teldr @ Legion Square |
|---|---|
| indeks | `(145.4186, -1041.8130, 29.6426)` |
| oyun içi ölçüm | `(145.4186, -1041.8125, 29.6426)` |

## Katkı

Düzeltme, yeni ölçüm ve hata bildirimi **Türkçe ya da İngilizce** kabul edilir.
Önce [katkı rehberini](CONTRIBUTING.tr.md) oku. `good first issue` etiketli
maddeler başlamak için uygundur:
https://github.com/B7Kompirine/muto-atlas/labels/good%20first%20issue

## Lisans

MIT — bkz. [LICENSE](../LICENSE). Yalnız kod içindir; oyun verisinin nasıl
ele alındığı [NOTICE.md](../NOTICE.md)'de yazılı. Bu depoda GTA V verisi dağıtılmaz.
