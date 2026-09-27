// Ses tasarımı sentezleyici: scene.js'deki IPUCLARI tablosundan WAV üretir.
// Hiç örnek (sample) dosyası yok; her ses matematikle üretilir, telif sorunu yoktur.
//   node ses.mjs intro cikti/intro.wav
import { writeFileSync } from 'node:fs';
import { IPUCLARI, SURE } from './scene.js';

const HZ = 48000;

// Belirlenimci gürültü (her çalıştırmada aynı ses)
let s = 12345;
const gurultu = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 2147483648 - 1; };

function sesUret(sahne) {
  const sure = SURE[sahne] + 0.4;
  const n = Math.ceil(sure * HZ);
  const L = new Float32Array(n), R = new Float32Array(n);
  const ekle = (i, l, r = l) => { if (i >= 0 && i < n) { L[i] += l; R[i] += r; } };

  const boom = t0 => {
    const b = Math.floor(t0 * HZ);
    let faz = 0;
    for (let i = 0; i < HZ * 1.4; i++) {
      const t = i / HZ;
      const f = 38 + 70 * Math.exp(-t * 9);
      faz += 2 * Math.PI * f / HZ;
      const zarf = Math.min(1, t * 400) * Math.exp(-t * 2.6);
      const v = Math.sin(faz) * zarf * 0.9 + gurultu() * Math.exp(-t * 60) * 0.25;
      ekle(b + i, v);
    }
  };
  const ping = (t0, f) => {
    const b = Math.floor(t0 * HZ);
    for (let i = 0; i < HZ * 1.2; i++) {
      const t = i / HZ;
      const zarf = Math.min(1, t * 2000) * Math.exp(-t * 5.5);
      const v = (Math.sin(2 * Math.PI * f * t) + 0.25 * Math.sin(2 * Math.PI * f * 2.01 * t) * Math.exp(-t * 12)) * zarf * 0.16;
      // hafif stereo: sağ kanal 9 ms gecikmeli
      ekle(b + i, v, 0);
      ekle(b + i + Math.floor(0.009 * HZ), 0, v);
    }
  };
  const tik = (t0, parlak) => {
    const b = Math.floor(t0 * HZ);
    let y = 0;
    const pan = gurultu() * 0.6;
    for (let i = 0; i < HZ * 0.012; i++) {
      const x = gurultu();
      y = x - 0.85 * y; // kaba yüksek geçiren
      const v = y * Math.exp(-i / HZ * 500) * 0.12 * parlak;
      ekle(b + i, v * (1 - pan), v * (1 + pan));
    }
  };
  // Bant geçiren gürültü, frekansı yükselen "süpürme"
  const supurme = (t0, d, f0, f1, guc) => {
    const b = Math.floor(t0 * HZ);
    let y1 = 0, y2 = 0;
    for (let i = 0; i < d * HZ; i++) {
      const k = i / (d * HZ);
      const f = f0 * Math.pow(f1 / f0, k * k);
      const r = 0.985, w = 2 * Math.PI * f / HZ;
      const x = gurultu();
      const y = x * (1 - r) + 2 * r * Math.cos(w) * y1 - r * r * y2;
      y2 = y1; y1 = y;
      const zarf = Math.pow(k, 1.6) * (1 - Math.pow(k, 12));
      const v = y * zarf * guc;
      ekle(b + i, v * (0.8 + 0.2 * Math.sin(k * 20)), v * (0.8 + 0.2 * Math.cos(k * 20)));
    }
  };
  const vurus = t0 => {
    const b = Math.floor(t0 * HZ);
    let faz = 0;
    for (let i = 0; i < HZ * 0.35; i++) {
      const t = i / HZ;
      faz += 2 * Math.PI * (55 + 140 * Math.exp(-t * 30)) / HZ;
      const v = Math.sin(faz) * Math.exp(-t * 11) * 0.8 + Math.sign(Math.sin(2 * Math.PI * 880 * t)) * Math.exp(-t * 60) * 0.05;
      ekle(b + i, v);
    }
  };

  for (const q of IPUCLARI[sahne]) {
    switch (q.tur) {
      case 'boom': boom(q.t); break;
      case 'ping': ping(q.t, q.f); break;
      case 'vurus': vurus(q.t); break;
      case 'tikler': for (let i = 0; i < q.adet; i++) tik(q.t + i * q.aralik, 0.6 + 0.4 * ((i * 7) % 5) / 4); break;
      case 'tarama': supurme(q.t, q.sure, 300, 3200, 0.9); break;
      case 'yukselis': supurme(q.t, q.sure, 200, 6000, 1.4); break;
      case 'kapanis': ping(q.t, 880); ping(q.t + 0.02, 1318); boom(q.t); break;
    }
  }

  // Altta yumuşak bir akor (A add9), yavaş açılıp kapanır
  if (IPUCLARI.pad) {
    const notalar = [110, 164.81, 246.94, 277.18, 329.63];
    const son = SURE[sahne];
    for (let i = 0; i < n; i++) {
      const t = i / HZ;
      const zarf = Math.min(1, t / 1.2) * Math.max(0, Math.min(1, (son + 0.2 - t) / 0.8));
      let l = 0, r = 0;
      notalar.forEach((f, j) => {
        const g = 0.035 / (1 + j * 0.3);
        l += Math.sin(2 * Math.PI * f * 0.998 * t + j) * g;
        r += Math.sin(2 * Math.PI * f * 1.002 * t + j * 2) * g;
      });
      L[i] += l * zarf; R[i] += r * zarf;
    }
  }

  // Basit yankı: iki gecikme hattı, çapraz geri besleme
  const d1 = Math.floor(0.137 * HZ), d2 = Math.floor(0.211 * HZ);
  for (let i = 0; i < n; i++) {
    if (i >= d1) L[i] += R[i - d1] * 0.28;
    if (i >= d2) R[i] += L[i - d2] * 0.28;
  }

  // Tepe -1 dBFS'e normalize + yumuşak sınırlayıcı
  let tepe = 0;
  for (let i = 0; i < n; i++) tepe = Math.max(tepe, Math.abs(L[i]), Math.abs(R[i]));
  const kazanc = 0.89 / (tepe || 1);
  const buf = Buffer.alloc(44 + n * 4);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + n * 4, 4); buf.write('WAVE', 8);
  buf.write('fmt ', 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(2, 22);
  buf.writeUInt32LE(HZ, 24); buf.writeUInt32LE(HZ * 4, 28); buf.writeUInt16LE(4, 32); buf.writeUInt16LE(16, 34);
  buf.write('data', 36); buf.writeUInt32LE(n * 4, 40);
  for (let i = 0; i < n; i++) {
    buf.writeInt16LE(Math.round(Math.tanh(L[i] * kazanc) * 32767), 44 + i * 4);
    buf.writeInt16LE(Math.round(Math.tanh(R[i] * kazanc) * 32767), 46 + i * 4);
  }
  return { buf, tepe, n };
}

if (process.argv[1] && process.argv[1].endsWith('ses.mjs')) {
  const [sahne = 'intro', cikti = `${sahne}.wav`] = process.argv.slice(2);
  const { buf, n } = sesUret(sahne);
  writeFileSync(cikti, buf);
  console.log(`${cikti}: ${(n / HZ).toFixed(2)} s, ${buf.length} bayt`);
}

export { sesUret };
