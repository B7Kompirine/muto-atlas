# muto-atlas marka animasyonu

Videolar için giriş (intro, 5 s) ve kapanış (outro, 6 s). Animasyon **kod olarak** yazıldı:
`scene.js` her kareyi zamanın saf fonksiyonu olarak Canvas'a çizer, `render.mjs` kareleri
tek tek çekip ffmpeg ile MP4'e çevirir. Video modeli yok; metin, süre, renk değiştirmek
bir satır değiştirmek demek.

| dosya | ne yapar |
|---|---|
| `scene.js` | sahneler, renkler (`RENK`), metinler (`METIN`), süreler (`SURE`), ses ipuçları (`IPUCLARI`) |
| `index.html` | tarayıcıda önizleme: sahne / dil / oran seçimi, zaman kaydırıcı |
| `ses.mjs` | ses tasarımı: `IPUCLARI` tablosundan sentezlenir (örnek dosya yok, telif yok) |
| `render.mjs` | kare kare render + ses → `cikti/*.mp4` |
| `fonts/` | Space Grotesk ve JetBrains Mono (SIL OFL 1.1, lisanslar yanında) |

## Önizleme

ES modülü olduğu için `file://` ile açılmaz; bir yerel sunucu gerekir:

```bash
cd brand/motion && npx serve .      # ya da: python -m http.server
```

## Render

Gerekenler: Node 18+, Playwright (Chromium), ffmpeg.

```bash
cd brand/motion
node render.mjs --sahne intro --dil tr                 # 1920x1080, 60 fps, sesli
node render.mjs --sahne outro --dil en --w 1080 --h 1920
node render.mjs --hepsi                                # intro/outro × tr/en × 16:9/9:16
node render.mjs --sahne intro --sessiz                 # sessiz
```

ffmpeg PATH'te değilse `--ffmpeg <yol>` ya da `FFMPEG` ortam değişkeni. Çıktı:
`cikti/muto-atlas_<sahne>_<dil>_<oran>.mp4` (git'e girmez).

Çıktı biçimi: H.264 yuv420p, CRF 16, BT.709, AAC 256k 48 kHz; ses tepe -1 dBFS'e
normalize edilir.

## Zaman çizelgesi

**Giriş (5.0 s):** 0.0 ping noktası → 0.35 topografik harita merkezden taranarak açılır →
0.55 altıgen çerçeve tepeden iki yöne çizilir → 1.3 kollar ve düğümler, 1.45 pin düşer
(1.95'te oturur) → 2.05 logo sola kayar, kelime markası harf harf gelir → 2.75 slogan
daktiloyla yazılır → 4.05 logonun merkezinden altıgen perde, zemin rengiyle biter.

**Kapanış (6.0 s):** 0.0 amber kenarlı altıgen delik açılır → 0.35 logo kurulur →
1.55 "Önce veriye bak. / Sonra kodu yaz." → 2.75 GitHub adresi → 4.85 her şey pine
çöker → 5.45 son vuruş, siyaha iner.

Giriş zemin rengiyle biter, kapanış zemin rengiyle başlar: montajda düz kesmeyle
bağlanırlar.
