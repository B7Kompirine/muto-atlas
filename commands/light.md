---
description: Read prop lights, decode the magic numbers and write them back into the .ydr/.yft
argument-hint: <file.ydr|.yft> [--set 0.Intensity=8] [--apply edit.json] [--add] [--remove N]
allowed-tools: Bash(python:*), Bash(powershell:*), Read, Edit
---

Kullanıcının sorgusu: `$ARGUMENTS`

Plugin kökü: `${CLAUDE_PLUGIN_ROOT}` (bulunamazsa `~/.claude/muto-atlas`).

Işıkla ilgili **her** iş bu komuttan geçer: "lambam çok sönük", "ışık
yanmıyor", "koni çok geniş", "prop'uma ışık ekle", "bu ışık hangi saatte
yanar". Kullanıcı `/light` yazmasa bile ışık konusu geçtiğinde bunu kullan.

## Sırayla

**1. Önce OKU — sihirli sayıyı kopyalama, çöz.**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya>
```

`TimeFlags 14680095` bir sayı değil "21:00–05:00 arası yanar" demektir.
Çıktıyı kullanıcıya bir iki cümleyle özetle: kaç ışık, tipi, hangi saatler,
uyarı var mı.

**2. Değeri ÖLÇÜLMÜŞ ARALIĞA göre öner.**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light --table
```

72.539 vanilla ışıktan hesaplanan `p05 / medyan / p95` bandı. Bir değer
önerirken "bence 20 olsun" deme — o alanın vanilla medyanını ve bandını
söyle, önerin bandın neresine düşüyor belirt. Katman kurulu değilse
**aralık uydurma**, referans veremediğini söyle.

**3. Geri yaz ve DOĞRULA.**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya> --apply duzenleme.json
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya> --set 0.Intensity=8 --set 0.ConeOuterAngle=35
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya> --add
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya> --remove 1
```

Her yazma orijinali `<ad>.yedek` olarak saklar ve sonucu **geri okuyarak**
doğrular. Doğrulama geçmezse dosya değişmez.

## Karanlık şikâyeti üç katmanlıdır — sırayla bak

Cevap çoğu zaman prop'un ışığında değil:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" cycle w_clear --hour 20   # 1. taban hava
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" timecycle --mlo <ytyp>    # 2. odanın modifier'ı
python "${CLAUDE_PLUGIN_ROOT}/scripts/assetdb.py" light <dosya>             # 3. prop'un ışığı
```

## Sonucu sunarken

- **Her sihirli sayıyı çöz.** `TimeFlags`, `Flags` — sayıyı tekrarlama,
  ne anlama geldiğini söyle (`assetdb.py flags <sayı>`).
- **Işık kemiğe bağlıdır.** `BoneId` sıfırdan farklıysa ışık modelin
  orijininde değil, o kemiktedir; konumu ona göre anlat.
- **Saat uyuşmazlığını söyle.** Kullanıcı "yanmıyor" diyorsa önce
  `TimeFlags`'e bak — çoğu vakada ışık sağlamdır, saat yanlıştır.
- **Yazmadan sonra hatırlat:** asset değişti → sunucudan **çıkıp yeniden
  bağlan**; restart yetmez.
- `cycle` katmanı kurulu değilse `build_cycle.ps1`'i öner — **uydurma**.

Tam matematik, üç katmanlı timecycle ve sessiz hata kataloğu:
`${CLAUDE_PLUGIN_ROOT}/skills/fivem-assets/references/light-matematigi-ve-onizleme.md`
