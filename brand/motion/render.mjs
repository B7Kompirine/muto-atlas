// Animasyonu kare kare çekip MP4'e çevirir (gerçek zamanlı kayıt değil: kare atlamaz).
//   node render.mjs --sahne intro --dil tr [--w 1920 --h 1080 --fps 60] [--sessiz]
//   node render.mjs --hepsi            # intro+outro × tr+en × 16:9+9:16
// Gerekenler: Node 18+, Playwright (Chromium) ve ffmpeg (PATH'te ya da --ffmpeg / FFMPEG).
import { createServer } from 'node:http';
import { readFileSync, mkdirSync, existsSync, rmSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { join, dirname, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { SURE } from './scene.js';
import { sesUret } from './ses.mjs';

const KOK = dirname(fileURLToPath(import.meta.url));

function arg(ad, varsayilan) {
  const i = process.argv.indexOf(`--${ad}`);
  if (i < 0) return varsayilan;
  const v = process.argv[i + 1];
  return v === undefined || v.startsWith('--') ? true : v;
}

// Playwright yerelde ya da global kurulu olabilir
function playwrightYukle() {
  const req = createRequire(import.meta.url);
  const adaylar = ['playwright', 'playwright-core'];
  for (const a of adaylar) { try { return req(a); } catch {} }
  const npmKok = process.env.NODE_PATH || join(dirname(process.execPath), '..', 'lib', 'node_modules');
  for (const a of adaylar) { try { return req(join(npmKok, a)); } catch {} }
  throw new Error('Playwright bulunamadı: npm i -D playwright  (ya da global kurulum)');
}

const TUR = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.ttf': 'font/ttf' };
function sunucuAc() {
  return new Promise(ok => {
    const s = createServer((istek, yanit) => {
      const yol = join(KOK, decodeURIComponent(new URL(istek.url, 'http://x').pathname));
      if (!yol.startsWith(KOK) || !existsSync(yol)) { yanit.writeHead(404); return yanit.end(); }
      yanit.writeHead(200, { 'content-type': TUR[extname(yol)] || 'application/octet-stream' });
      yanit.end(readFileSync(yol));
    });
    s.listen(0, '127.0.0.1', () => ok(s));
  });
}

async function renderle(tarayici, port, { sahne, dil, w, h, fps, ffmpeg, sessiz, cikti }) {
  const sayfa = await tarayici.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  await sayfa.goto(`http://127.0.0.1:${port}/index.html?render=1&sahne=${sahne}&dil=${dil}&w=${w}&h=${h}`);
  await sayfa.waitForFunction(() => window.hazir === true, null, { timeout: 30000 });
  // Yazı tipleri gerçekten yüklendi mi? Yüklenmediyse yedek yazı tipiyle sessizce çizilir.
  const fontlar = await sayfa.evaluate(() => [
    document.fonts.check('700 100px "Space Grotesk"'),
    document.fonts.check('500 20px "JetBrains Mono"'),
  ]);
  if (!fontlar.every(Boolean)) throw new Error(`yazı tipi yüklenemedi (fonts/ klasörü?): ${fontlar}`);

  const kareSayisi = Math.round(SURE[sahne] * fps);
  let wav = null;
  if (!sessiz) {
    wav = join(tmpdir(), `muto-${sahne}-${process.pid}.wav`);
    const { buf } = sesUret(sahne);
    (await import('node:fs')).writeFileSync(wav, buf);
  }
  const argumanlar = [
    '-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
    ...(wav ? ['-i', wav] : []),
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p',
    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
    ...(wav ? ['-c:a', 'aac', '-b:a', '256k', '-shortest'] : []),
    '-movflags', '+faststart', cikti,
  ];
  const ff = spawn(ffmpeg, argumanlar, { stdio: ['pipe', 'inherit', 'inherit'] });
  const bitti = new Promise((ok, red) => ff.on('close', k => (k === 0 ? ok() : red(new Error(`ffmpeg çıkış kodu ${k}`)))));

  for (let i = 0; i < kareSayisi; i++) {
    const t = i / fps;
    const b64 = await sayfa.evaluate(t => {
      window.kareCiz(t);
      return document.getElementById('c').toDataURL('image/png').split(',')[1];
    }, t);
    const png = Buffer.from(b64, 'base64');
    if (!ff.stdin.write(png)) await new Promise(ok => ff.stdin.once('drain', ok));
    if (i % fps === 0) process.stdout.write(`\r  ${cikti}  ${i}/${kareSayisi}`);
  }
  ff.stdin.end();
  await bitti;
  if (wav) rmSync(wav, { force: true });
  await sayfa.close();
  process.stdout.write(`\r  ${cikti}  ${kareSayisi}/${kareSayisi} kare\n`);
  return kareSayisi;
}

const ffmpeg = arg('ffmpeg', process.env.FFMPEG || 'ffmpeg');
const fps = +arg('fps', 60);
const klasor = join(KOK, 'cikti');
mkdirSync(klasor, { recursive: true });

const isler = [];
if (arg('hepsi', false)) {
  for (const sahne of ['intro', 'outro'])
    for (const dil of ['tr', 'en'])
      for (const [w, h, ad] of [[1920, 1080, '16x9'], [1080, 1920, '9x16']])
        isler.push({ sahne, dil, w, h, ad });
} else {
  const w = +arg('w', 1920), h = +arg('h', 1080);
  isler.push({ sahne: arg('sahne', 'intro'), dil: arg('dil', 'tr'), w, h, ad: `${w}x${h}` });
}

const { chromium } = playwrightYukle();
const sunucu = await sunucuAc();
const tarayici = await chromium.launch();
try {
  for (const is of isler) {
    await renderle(tarayici, sunucu.address().port, {
      ...is, fps, ffmpeg, sessiz: !!arg('sessiz', false),
      cikti: join(klasor, `muto-atlas_${is.sahne}_${is.dil}_${is.ad}.mp4`),
    });
  }
} finally {
  await tarayici.close();
  sunucu.close();
}
