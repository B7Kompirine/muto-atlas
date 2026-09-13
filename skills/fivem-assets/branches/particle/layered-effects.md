# Katmanlı (çok emitterli) efekt — patlama, ateş+duman+enkaz üst üste

**Ne zaman okunur:** efekt "düz/tek katman" duruyor; vanilla gibi çekirdek + top + duman + enkaz + şok halkası; sayfa dilimlerini emitter gecikmesiyle bölmek.
**When to read:** a layered multi-emitter effect — explosion with fire, smoke and debris stacked with delays.
**Kaynak:** `ptfx-flipbook-uretimi.md` §1e-BIS 'N emitter + Unknown10' · `scripts/ptfx_compose.py` docstring (2026-09) · **Ölçüm:** vanilla 964 efektin 713'ü (%74) çok emitterli; `exp_grd_grenade` 6, `exp_grd_molotov` 7 katman
**Önce:** `branches/particle/_branch.md` · gövde › `trunk/tool-pitfalls.md` §3 CodeWalker (`FxcFileHash`, `VFT`, `ResourcePointerArray64`)

---

## Neden katman

Ölçüldü: vanilla efektlerinin **%74'ü çok emitterli** (713/964); bizim katalog tamamen tek emitterliydi — "hepsi birbirinin türevi" görüntüsünün sebebi bu. Profesyonel VFX derinliğini katmanlardan alır (beyaz çekirdek + turuncu top + yükselen duman + enkaz + şok halkası **üst üste**). Vanilla'dan okunan katman alanları: `<EmitterRule>`/`<ParticleRule>` katmanın kaynağı, `Unknown10` katmanın **gecikmesi** (saniye). Araç: `scripts/ptfx_compose.py`.

## Sayfa dilimlerini katmanla oynatmak

### N emitter + `Unknown10` GECİKMESİ (çalışıyor, ölçüldü)

Motor kare ilerletmediği için sıra **efektin içine** kurulur: N ayrı
emitter, her birinin kendi **tek-kare** dokusu (`C4=0`) ve kendi
**başlama gecikmesi**. Motor sırayı yürütür; Lua'da sıfır yük, senkron
garantili.

**`Unknown10` = emitter başlama gecikmesi (saniye).** EffectRule'un
`<EventEmitters>` girdisindedir. Vanilla ölçümü: 2543 kaydın **%91,1'i 0**;
sıfırdan farklı 226 tanesi **0.0010-0.7500** aralığında (medyan 0.042).
`exp_grd_grenade` emitterleri 0 / 0.034 / 0.068 / 0 diye kademeli.
⛔ **Tavan 0.75 sn** — aşma.

**Emitter'in SUSMASI şart, yoksa aşamalar BİRİKİR.** İlk denemede
gecikmeler çalıştı ama emitter'lar saçmaya devam ettiği için dört şekil
üst üste yığıldı. Vanilla çözümü `m_spawnRateOverTimeKFP`'ye **patlama
eğrisi** yazmaktır (örnek: `bang_metal_dust`):

| keyframe | `InterpolationInterval` (normalize zaman 0-1) | hız |
|---|---|---|
| 1 | 0 | hız |
| 2 | w | hız |
| 3 | w + 0.02 | **0** ← emitter susar |

Yani `InterpolationInterval` **zaman ekseni**, `Red/Green` o andaki
min/max doğum hızıdır.

**Ölçülen çalışan yapılandırma** (`my_e2`): 4 emitter, gecikmeler
**0 / 0.2 / 0.4 / 0.6 sn**, her emitter `w=0.08`'de saçar `0.10`'da susar,
parçacık ömrü **0.30 sn**, her aşamanın kendi tek-kare dokusu, `C4=0`.

Oyunda ölçülen (tek koşu, film şeridi):

| t (ms) | 80 | 200 | 320 | 440 | 560 | 680 | 800 | 950 |
|---|---|---|---|---|---|---|---|---|
| kırmızı kaplama % | 0.04 | **34.5** | 17.0 | 6.9 | 5.4 | 3.4 | **0.04** | 12.6 |
| görülen | — | disk | halka | artı | — | üçgen | — | baştan |

Kaplama sıfıra düşüp yeniden yükseliyor → dizi tamamlanıp döngü başa
sarıyor. Görsel: `flipbook_deney/serit_e2.png`.

**Üretici:** `flipbook_deney/serit_ypt.py` — tek emitterli transplant
çıktısından N aşamalı efekt üretir (EventEmitters/EmitterRule/
ParticleRule/TextureDictionary hepsini N'e çoğaltır, gecikmeleri yazar,
`C4`'ü 0'a çeker, her aşamaya kendi dokusunu bağlar).

⚠ Efekt **döngüsel** çağrıldığında dizi başa sarıyor (yukarıda t=950).
Tek atımlık patlama için `StartParticleFxNonLooped*` kullanılmalı;
denenmedi.
