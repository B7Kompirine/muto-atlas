// muto-atlas marka animasyonu: giriş (intro) ve kapanış (outro).
// Her kare yalnızca zamanın fonksiyonudur: ciz(ctx, sahne, t). Aynı t her zaman aynı
// kareyi verir; render.mjs kareleri tek tek çekip videoya bu sayede kayıpsız çevirir.
// Ses de (ses.mjs) buradaki IPUCLARI tablosundan üretilir: zamanlama değişince ses de kayar.

export const RENK = {
  zemin: '#15181D',     // logonun zemini, assets/logo.png'den ölçüldü (21,24,29)
  zeminKoyu: '#0B0D10',
  amber: '#F59F18',     // logonun amberi, ölçüldü (245,159,24)
  amberAcik: '#FFC857',
  hexDolgu: '#2A2419',  // altıgen içi, ölçüldü (~43,37,26)
  murekkep: '#EEF0F3',
  soluk: '#7D838D',
};

export const METIN = {
  en: {
    slogan: 'GROUND TRUTH FOR FIVEM / GTA V',
    satir1: 'Look at the data first.',
    satir2: 'Then write the code.',
    etiket: 'FIVEM · GTA V · CLAUDE CODE',
  },
  tr: {
    slogan: 'FIVEM / GTA V İÇİN TAHMİN DEĞİL, VERİ',
    satir1: 'Önce veriye bak.',
    satir2: 'Sonra kodu yaz.',
    etiket: 'FIVEM · GTA V · CLAUDE CODE',
  },
};

export const ADRES = 'github.com/B7Kompirine/muto-atlas';
export const SURE = { intro: 5.0, outro: 6.0 };

// Ses ipuçları (saniye). tur: boom | ping | tik | yukselis | vuruş | kapanis
export const IPUCLARI = {
  intro: [
    { t: 0.05, tur: 'ping', f: 1318 },
    { t: 0.35, tur: 'boom' },
    { t: 0.60, tur: 'tarama', sure: 0.9 },
    { t: 1.52, tur: 'ping', f: 1760 },
    { t: 1.60, tur: 'ping', f: 2093 },
    { t: 1.68, tur: 'ping', f: 2637 },
    { t: 1.95, tur: 'vurus' },
    { t: 2.25, tur: 'tikler', adet: 10, aralik: 0.035 },
    { t: 2.75, tur: 'tikler', adet: 16, aralik: 0.03 },
    { t: 3.95, tur: 'yukselis', sure: 0.55 },
    { t: 4.50, tur: 'boom' },
  ],
  outro: [
    { t: 0.00, tur: 'yukselis', sure: 0.25 },
    { t: 0.25, tur: 'boom' },
    { t: 0.95, tur: 'ping', f: 1760 },
    { t: 1.02, tur: 'ping', f: 2093 },
    { t: 1.09, tur: 'ping', f: 2637 },
    { t: 1.30, tur: 'vurus' },
    { t: 1.75, tur: 'tikler', adet: 8, aralik: 0.04 },
    { t: 2.35, tur: 'tikler', adet: 8, aralik: 0.04 },
    { t: 2.90, tur: 'ping', f: 1318 },
    { t: 4.85, tur: 'yukselis', sure: 0.6 },
    { t: 5.45, tur: 'kapanis' },
  ],
  pad: true, // alttaki yumuşak akor
};

// ---------------------------------------------------------------- yardımcılar
const sinirla = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ilerleme = (t, a, b) => sinirla((t - a) / (b - a));
const karistir = (a, b, k) => a + (b - a) * k;
const E = {
  cikisKubik: k => 1 - Math.pow(1 - k, 3),
  cikisUstel: k => (k >= 1 ? 1 : 1 - Math.pow(2, -10 * k)),
  girisUstel: k => (k <= 0 ? 0 : Math.pow(2, 10 * k - 10)),
  girisCikisUstel: k => k <= 0 ? 0 : k >= 1 ? 1
    : k < 0.5 ? Math.pow(2, 20 * k - 10) / 2 : (2 - Math.pow(2, -20 * k + 10)) / 2,
  girisCikisKubik: k => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
  cikisGeri: (k, s = 1.9) => 1 + (s + 1) * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2),
  cikisSekme: k => {
    const n = 7.5625, d = 2.75;
    if (k < 1 / d) return n * k * k;
    if (k < 2 / d) return n * (k -= 1.5 / d) * k + 0.75;
    if (k < 2.5 / d) return n * (k -= 2.25 / d) * k + 0.9375;
    return n * (k -= 2.625 / d) * k + 0.984375;
  },
};

// Belirlenimci sözde rastgele (kare kare aynı sonuç için)
function tohum(n) {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

function hexYolu(ctx, cx, cy, r) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const a = -Math.PI / 2 + i * Math.PI / 3; // sivri tepe
    const x = cx + r * Math.cos(a), y = cy + r * Math.sin(a);
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  }
  ctx.closePath();
}

function hexKoseleri(r) {
  const k = [];
  for (let i = 0; i < 6; i++) {
    const a = -Math.PI / 2 + i * Math.PI / 3;
    k.push([r * Math.cos(a), r * Math.sin(a)]);
  }
  return k;
}

// Altıgen çevresinin k kadarını tepe köşesinden iki yöne doğru çizer (k: 0..1)
function hexCizgiIzi(ctx, r, k) {
  if (k <= 0) return;
  const kose = hexKoseleri(r);
  const yari = k * 3; // her yöne 3 kenar
  for (const yon of [1, -1]) {
    ctx.beginPath();
    ctx.moveTo(kose[0][0], kose[0][1]);
    for (let i = 0; i < 3; i++) {
      const kalan = yari - i;
      if (kalan <= 0) break;
      const a = kose[((i * yon) % 6 + 6) % 6];
      const b = kose[(((i + 1) * yon) % 6 + 6) % 6];
      const f = Math.min(1, kalan);
      ctx.lineTo(karistir(a[0], b[0], f), karistir(a[1], b[1], f));
    }
    ctx.stroke();
  }
}

// --------------------------------------------------------- eş yükselti çizgileri
// Pürüzsüz bir yükseklik alanı + marching squares => topografik harita çizgileri.
function alan(x, y, z, tepe) {
  let v = Math.sin(x * 0.0041 + 0.9 * Math.sin(y * 0.0032 + z))
        + Math.cos(y * 0.0049 + 0.8 * Math.sin(x * 0.0026 - z * 0.7))
        + 0.55 * Math.sin((x + y) * 0.0029 + z * 0.45)
        + 0.35 * Math.cos((x - y) * 0.0063 - z * 0.3);
  if (tepe) { // logonun olduğu yerde bir "zirve": çizgiler logonun etrafında halkalanır
    const dx = x - tepe.x, dy = y - tepe.y;
    v += tepe.h * Math.exp(-(dx * dx + dy * dy) / (2 * tepe.s * tepe.s));
  }
  return v;
}

function esYukselti(ctx, x0, y0, w, h, hucre, seviyeler, f) {
  const nx = Math.ceil(w / hucre) + 1, ny = Math.ceil(h / hucre) + 1;
  const d = new Float32Array(nx * ny);
  for (let j = 0; j < ny; j++)
    for (let i = 0; i < nx; i++) d[j * nx + i] = f(x0 + i * hucre, y0 + j * hucre);
  ctx.beginPath();
  for (const s of seviyeler) {
    for (let j = 0; j < ny - 1; j++) {
      for (let i = 0; i < nx - 1; i++) {
        const a = d[j * nx + i], b = d[j * nx + i + 1];
        const c = d[(j + 1) * nx + i + 1], e = d[(j + 1) * nx + i];
        const kod = (a > s) | ((b > s) << 1) | ((c > s) << 2) | ((e > s) << 3);
        if (kod === 0 || kod === 15) continue;
        const px = x0 + i * hucre, py = y0 + j * hucre;
        const U = [px + hucre * (s - a) / (b - a), py];
        const R = [px + hucre, py + hucre * (s - b) / (c - b)];
        const D = [px + hucre * (s - e) / (c - e), py + hucre];
        const L = [px, py + hucre * (s - a) / (e - a)];
        const seg = (p, q) => { ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]); };
        switch (kod) {
          case 1: case 14: seg(L, U); break;
          case 2: case 13: seg(U, R); break;
          case 3: case 12: seg(L, R); break;
          case 4: case 11: seg(R, D); break;
          case 6: case 9: seg(U, D); break;
          case 7: case 8: seg(L, D); break;
          case 5: seg(L, U); seg(R, D); break;
          case 10: seg(U, R); seg(L, D); break;
        }
      }
    }
  }
}

// -------------------------------------------------------------------- logo
// Logo birim koordinatlarda (altıgen çevrel yarıçapı = 1). assets/logo.png'den okunan
// yerleşim: merkez pin, üst / sol-alt / sağ-alt düğümler.
const DUGUMLER = [[0, -0.63], [-0.55, 0.36], [0.55, 0.36]];

// ilerlemeler: { hex, ic, kontur, kol, dugum, pin, detay, parilti }
function logoCiz(ctx, cx, cy, olcek, p, t) {
  const R = olcek;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  // Dış parıltı
  if (p.parilti > 0) {
    const g = ctx.createRadialGradient(0, 0, R * 0.2, 0, 0, R * 1.9);
    g.addColorStop(0, `rgba(245,159,24,${0.16 * p.parilti})`);
    g.addColorStop(1, 'rgba(245,159,24,0)');
    ctx.fillStyle = g;
    ctx.fillRect(-R * 2, -R * 2, R * 4, R * 4);
  }

  // Dolgu
  if (p.ic > 0) {
    ctx.globalAlpha = p.ic;
    hexYolu(ctx, 0, 0, R * 0.965);
    ctx.fillStyle = RENK.hexDolgu;
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  // İç eş yükselti çizgileri (altıgene kırpılmış, merkezden dışa açılır)
  if (p.kontur > 0) {
    ctx.save();
    hexYolu(ctx, 0, 0, R * 0.86);
    ctx.clip();
    ctx.beginPath();
    ctx.arc(0, 0, R * 1.1 * E.cikisKubik(p.kontur), 0, Math.PI * 2);
    ctx.clip();
    const u = R / 170; // 1080p'deki boyuta göre ölçek
    const z = t * 0.35;
    esYukselti(ctx, -R, -R, 2 * R, 2 * R, Math.max(3, 7 * u), [-1.2, -0.7, -0.2, 0.3, 0.8, 1.3, 1.8],
      (x, y) => alan(x / u * 2.6 + 400, y / u * 2.6 + 200, z, null));
    ctx.strokeStyle = 'rgba(245,159,24,0.55)';
    ctx.lineWidth = Math.max(1, 2.4 * u);
    ctx.stroke();
    ctx.restore();
  }

  // Dış ve iç altıgen çerçeve
  ctx.strokeStyle = RENK.amber;
  ctx.shadowColor = 'rgba(245,159,24,0.65)';
  ctx.shadowBlur = R * 0.08;
  ctx.lineWidth = R * 0.068;
  hexCizgiIzi(ctx, R, E.girisCikisKubik(p.hex));
  ctx.lineWidth = R * 0.02;
  hexCizgiIzi(ctx, R * 0.88, E.girisCikisKubik(sinirla(p.hex * 1.15 - 0.15)));

  // Köşe / kenar işaretleri
  if (p.detay > 0) {
    ctx.globalAlpha = p.detay;
    ctx.lineWidth = R * 0.03;
    const u = R * (1.08 + 0.12 * (1 - E.cikisGeri(p.detay)));
    ctx.beginPath();
    ctx.moveTo(0, -u); ctx.lineTo(0, -u - R * 0.1);
    ctx.moveTo(0, u); ctx.lineTo(0, u + R * 0.1);
    const kx = R * Math.cos(Math.PI / 6) + R * 0.1;
    for (const sx of [-1, 1]) {
      ctx.moveTo(sx * kx, -R * 0.22); ctx.lineTo(sx * kx, -R * 0.08);
      ctx.moveTo(sx * kx, R * 0.08); ctx.lineTo(sx * kx, R * 0.22);
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
  ctx.shadowBlur = 0;

  // Merkezden düğümlere kollar
  if (p.kol > 0) {
    ctx.strokeStyle = RENK.amber;
    ctx.lineWidth = R * 0.028;
    DUGUMLER.forEach(([x, y], i) => {
      const k = E.cikisUstel(sinirla(p.kol * 1.3 - i * 0.15));
      if (k <= 0) return;
      const bas = 0.2, son = 1 - 0.1 / Math.hypot(x, y);
      ctx.beginPath();
      ctx.moveTo(x * bas, y * bas);
      ctx.lineTo(x * karistir(bas, son, k) , y * karistir(bas, son, k));
      ctx.stroke();
    });
  }

  // Kesikli rotalar, artılar, noktalar
  if (p.detay > 0) {
    ctx.save();
    ctx.globalAlpha = p.detay * 0.9;
    ctx.strokeStyle = RENK.amber;
    ctx.lineWidth = R * 0.018;
    ctx.setLineDash([R * 0.035, R * 0.04]);
    ctx.lineDashOffset = -t * R * 0.12; // rotalar akar
    ctx.beginPath();
    ctx.moveTo(-0.42 * R, 0.45 * R);
    ctx.bezierCurveTo(-0.3 * R, 0.72 * R, 0.05 * R, 0.5 * R, 0.18 * R, 0.66 * R);
    ctx.moveTo(0.12 * R, -0.62 * R);
    ctx.bezierCurveTo(0.35 * R, -0.62 * R, 0.3 * R, -0.35 * R, 0.5 * R, -0.28 * R);
    ctx.moveTo(0.58 * R, 0.2 * R);
    ctx.bezierCurveTo(0.66 * R, 0.05 * R, 0.62 * R, -0.08 * R, 0.66 * R, -0.16 * R);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.lineWidth = R * 0.016;
    const arti = (x, y, s) => {
      ctx.beginPath();
      ctx.moveTo((x - s) * R, y * R); ctx.lineTo((x + s) * R, y * R);
      ctx.moveTo(x * R, (y - s) * R); ctx.lineTo(x * R, (y + s) * R);
      ctx.stroke();
    };
    arti(0.2, -0.46, 0.04); arti(-0.5, -0.24, 0.04); arti(-0.12, 0.72, 0.035);
    ctx.fillStyle = RENK.amber;
    for (const [x, y] of [[0.5, -0.28], [0.66, -0.16], [-0.66, 0.02], [0.18, 0.66]]) {
      ctx.beginPath(); ctx.arc(x * R, y * R, R * 0.025, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
  }

  // Düğümler (halka + nokta), sırayla "pop"
  DUGUMLER.forEach(([x, y], i) => {
    const k = sinirla(p.dugum * 1.4 - i * 0.2);
    if (k <= 0) return;
    const s = E.cikisGeri(k, 2.4);
    ctx.save();
    ctx.translate(x * R, y * R);
    ctx.scale(s, s);
    ctx.strokeStyle = RENK.amber;
    ctx.fillStyle = RENK.hexDolgu;
    ctx.lineWidth = R * 0.034;
    ctx.beginPath(); ctx.arc(0, 0, R * 0.09, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = RENK.amber;
    ctx.beginPath(); ctx.arc(0, 0, R * 0.038, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
    // halka dalgası
    if (k < 1) {
      ctx.globalAlpha = 1 - k;
      ctx.lineWidth = R * 0.012;
      ctx.beginPath(); ctx.arc(x * R, y * R, R * (0.09 + 0.25 * k), 0, Math.PI * 2); ctx.stroke();
      ctx.globalAlpha = 1;
    }
  });

  // Pin: yukarıdan düşer, zıplar
  if (p.pin > 0) {
    const k = E.cikisSekme(p.pin);
    const dy = (1 - k) * -R * 1.6;
    ctx.save();
    ctx.globalAlpha = sinirla(p.pin * 4);
    ctx.translate(0, dy);
    const r = R * 0.13, cyP = -R * 0.04;
    ctx.beginPath();
    ctx.arc(0, cyP, r, Math.PI * 0.8, Math.PI * 0.2);
    ctx.lineTo(0, cyP + r * 2.05);
    ctx.closePath();
    ctx.fillStyle = RENK.hexDolgu;
    ctx.fill();
    ctx.strokeStyle = RENK.amber;
    ctx.lineWidth = R * 0.04;
    ctx.shadowColor = 'rgba(245,159,24,0.8)';
    ctx.shadowBlur = R * 0.1;
    ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.fillStyle = RENK.amber;
    ctx.beginPath(); ctx.arc(0, cyP, r * 0.46, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  ctx.restore();
}

// ------------------------------------------------------------ arka plan katmanı
function zeminCiz(ctx, W, H) {
  const g = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, Math.hypot(W, H) * 0.6);
  g.addColorStop(0, RENK.zemin);
  g.addColorStop(1, RENK.zeminKoyu);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
}

// Tam ekran topografik çizgiler; merkezden açılan dairesel "tarama" ile görünür olur
function haritaCiz(ctx, W, H, t, merkez, yaricap, yogunluk, u) {
  if (yaricap <= 0 || yogunluk <= 0) return;
  const tepe = { x: merkez.x / u, y: merkez.y / u, h: 2.4, s: 260 };
  const f = (x, y) => alan(x / u, y / u, t * 0.12, tepe);
  const seviyeler = [];
  for (let s = -2.6; s <= 3.6; s += 0.3) seviyeler.push(s);

  ctx.save();
  ctx.beginPath();
  ctx.arc(merkez.x, merkez.y, yaricap, 0, Math.PI * 2);
  ctx.clip();
  esYukselti(ctx, 0, 0, W, H, 14 * u, seviyeler, f);
  ctx.lineWidth = 1.4 * u;
  ctx.strokeStyle = `rgba(245,159,24,${0.16 * yogunluk})`;
  ctx.stroke();
  ctx.restore();

  // Tarama cephesi: halkanın hemen içi parlak
  const bant = 90 * u;
  if (yaricap < Math.hypot(W, H)) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(merkez.x, merkez.y, yaricap, 0, Math.PI * 2);
    ctx.arc(merkez.x, merkez.y, Math.max(0, yaricap - bant), 0, Math.PI * 2, true);
    ctx.clip();
    esYukselti(ctx, 0, 0, W, H, 14 * u, seviyeler, f);
    ctx.lineWidth = 1.8 * u;
    ctx.strokeStyle = `rgba(255,200,87,${0.7 * yogunluk})`;
    ctx.stroke();
    ctx.restore();
    ctx.beginPath();
    ctx.arc(merkez.x, merkez.y, yaricap, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(245,159,24,${0.25 * yogunluk})`;
    ctx.lineWidth = 1.5 * u;
    ctx.stroke();
  }
}

// Kenardan kararma (vinyet) — kenarlar yumuşak dursun
function vinyet(ctx, W, H) {
  const g = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.35, W / 2, H / 2, Math.hypot(W, H) * 0.62);
  g.addColorStop(0, 'rgba(8,9,11,0)');
  g.addColorStop(1, 'rgba(8,9,11,0.75)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
}

// Film greni: ince, belirlenimci
function gren(ctx, W, H, t, u) {
  const kare = Math.floor(t * 30);
  ctx.fillStyle = 'rgba(255,255,255,0.025)';
  for (let i = 0; i < 260; i++) {
    const x = tohum(kare * 997 + i) * W, y = tohum(kare * 131 + i * 7.3) * H;
    ctx.fillRect(x, y, 1.5 * u, 1.5 * u);
  }
}

// Köşe HUD'u: çerçeve köşeleri + GTA V koordinat okuması
function hudCiz(ctx, W, H, t, k, u, metin) {
  if (k <= 0) return;
  const pay = 56 * u, kol = 34 * u * E.cikisUstel(k);
  ctx.save();
  ctx.globalAlpha = sinirla(k * 2) * 0.9;
  ctx.strokeStyle = RENK.soluk;
  ctx.lineWidth = 1.5 * u;
  ctx.beginPath();
  for (const [x, y, sx, sy] of [[pay, pay, 1, 1], [W - pay, pay, -1, 1], [pay, H - pay, 1, -1], [W - pay, H - pay, -1, -1]]) {
    ctx.moveTo(x, y + sy * kol); ctx.lineTo(x, y); ctx.lineTo(x + sx * kol, y);
  }
  ctx.stroke();

  ctx.font = `500 ${15 * u}px "JetBrains Mono", monospace`;
  ctx.letterSpacing = `${2 * u}px`;
  ctx.fillStyle = RENK.soluk;
  ctx.textBaseline = 'middle';
  // koordinatlar önce karışık akar, sonra oturur (Legion Square)
  const hedef = [-215.42, -1037.18, 30.14];
  const oturma = E.cikisKubik(ilerleme(k, 0.2, 1));
  const sayi = (v, i) => {
    const gurultu = (tohum(Math.floor(t * 24) * 13 + i) - 0.5) * 2000 * (1 - oturma);
    return (v + gurultu).toFixed(2).padStart(9, ' ');
  };
  const sag = `X${sayi(hedef[0], 0)}  Y${sayi(hedef[1], 1)}  Z${sayi(hedef[2], 2)}`;
  ctx.textAlign = 'left';
  ctx.fillText('MUTO-ATLAS', pay + 14 * u, pay + 14 * u);
  ctx.textAlign = 'right';
  ctx.fillText(sag, W - pay - 14 * u, pay + 14 * u);
  ctx.textAlign = 'left';
  ctx.fillText(metin.etiket, pay + 14 * u, H - pay - 14 * u);
  ctx.textAlign = 'right';
  const zk = `${String(Math.floor(t)).padStart(2, '0')}:${String(Math.floor((t % 1) * 60)).padStart(2, '0')}`;
  ctx.fillText(`● REC ${zk}`, W - pay - 14 * u, H - pay - 14 * u);
  ctx.restore();
}

// Harf harf maskeden yukarı kayarak gelen yazı. parcalar: [{metin, renk}]
function kelimeCiz(ctx, x, y, boyut, parcalar, k, hiza = 'left') {
  ctx.save();
  ctx.font = `700 ${boyut}px "Space Grotesk", sans-serif`;
  ctx.letterSpacing = `${-boyut * 0.03}px`;
  ctx.textBaseline = 'alphabetic';
  ctx.textAlign = 'left';
  const harfler = [];
  for (const p of parcalar) for (const h of p.metin) harfler.push({ h, renk: p.renk });
  const tumu = parcalar.map(p => p.metin).join('');
  const genislik = ctx.measureText(tumu).width;
  let bx = hiza === 'center' ? x - genislik / 2 : x;
  ctx.beginPath();
  ctx.rect(bx - boyut, y - boyut * 1.05, genislik + boyut * 2, boyut * 1.35);
  ctx.clip();
  let onceki = '';
  harfler.forEach((hr, i) => {
    const hx = bx + ctx.measureText(onceki).width;
    onceki += hr.h;
    const kk = E.cikisUstel(sinirla(k * (1 + harfler.length * 0.08) - i * 0.08));
    ctx.fillStyle = hr.renk;
    ctx.globalAlpha = sinirla(kk * 1.5);
    ctx.fillText(hr.h, hx, y + (1 - kk) * boyut * 1.1);
  });
  ctx.restore();
  return genislik;
}

// Daktilo yazısı + blok imleç
function daktilo(ctx, x, y, boyut, metin, k, t, hiza = 'left', renk = RENK.soluk) {
  if (k <= 0) return;
  ctx.save();
  ctx.font = `500 ${boyut}px "JetBrains Mono", monospace`;
  ctx.letterSpacing = `${boyut * 0.18}px`;
  ctx.textBaseline = 'middle';
  const n = Math.floor(metin.length * sinirla(k));
  const gorunen = metin.slice(0, n);
  const tamG = ctx.measureText(metin).width;
  const bx = hiza === 'center' ? x - tamG / 2 : x;
  ctx.fillStyle = renk;
  ctx.textAlign = 'left';
  ctx.fillText(gorunen, bx, y);
  const w = ctx.measureText(gorunen).width;
  const yanip = k < 1 || Math.floor(t * 3) % 2 === 0;
  if (yanip && k < 1.25) {
    ctx.fillStyle = RENK.amber;
    ctx.fillRect(bx + w + boyut * 0.1, y - boyut * 0.55, boyut * 0.55, boyut * 1.1);
  }
  ctx.restore();
}

// Altıgen perde geçişi: önce amber, arkasından zemin rengi altıgen büyür
function hexPerde(ctx, W, H, cx, cy, k, ters) {
  if (k <= 0 && !ters) return;
  if (k >= 1 && ters) return;
  const Rmax = Math.hypot(Math.max(cx, W - cx), Math.max(cy, H - cy)) / Math.cos(Math.PI / 6) * 1.05;
  const a = E.girisCikisUstel(sinirla(k / 0.8));
  const b = E.girisCikisUstel(sinirla((k - 0.2) / 0.8));
  if (!ters) {
    hexYolu(ctx, cx, cy, Rmax * a); ctx.fillStyle = RENK.amber; ctx.fill();
    hexYolu(ctx, cx, cy, Rmax * b); ctx.fillStyle = RENK.zemin; ctx.fill();
  } else {
    // ters: zemin rengi örtü, ortasında büyüyen altıgen delik; delik kenarı amber
    const r = Rmax * a;
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, W, H);
    hexAlt(ctx, cx, cy, r);
    ctx.fillStyle = RENK.zemin;
    ctx.fill('evenodd');
    const kalinlik = Math.max(0, (1 - a) * 60) * (W / 1920);
    if (kalinlik > 0.5 && r > 0) {
      ctx.beginPath();
      hexAlt(ctx, cx, cy, r);
      ctx.strokeStyle = RENK.amber;
      ctx.lineWidth = kalinlik;
      ctx.stroke();
    }
    ctx.restore();
  }
}
function hexAlt(ctx, cx, cy, r) {
  for (let i = 0; i < 6; i++) {
    const a = -Math.PI / 2 + i * Math.PI / 3;
    const x = cx + r * Math.cos(a), y = cy + r * Math.sin(a);
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  }
  ctx.closePath();
}

// --------------------------------------------------------------------- sahneler
function yerlesim(W, H) {
  const u = Math.min(W / 1920, H / 1080) * (W < H ? 1.55 : 1); // dikeyde öğeler büyür
  return { u, dikey: W < H };
}

function introCiz(ctx, W, H, t, dil) {
  const m = METIN[dil] || METIN.en;
  const { u, dikey } = yerlesim(W, H);
  const merkez = { x: W / 2, y: H / 2 };

  zeminCiz(ctx, W, H);

  // Yerleşim hesabı: logo + kelime markası yan yana (yatay) ya da üst üste (dikey)
  const R0 = 170 * u;
  const kayma = E.girisCikisUstel(ilerleme(t, 2.05, 2.9));
  const olcek = R0 * karistir(1, dikey ? 0.82 : 0.72, kayma);
  const boyut = (dikey ? 132 : 150) * u;
  ctx.font = `700 ${boyut}px "Space Grotesk", sans-serif`;
  ctx.letterSpacing = `${-boyut * 0.03}px`;
  const wmG = ctx.measureText('muto-atlas').width;
  ctx.letterSpacing = '0px';
  let lx, ly, wx, wy, hiza;
  if (dikey) {
    lx = W / 2; ly = karistir(H / 2, H * 0.4, kayma);
    wx = W / 2; wy = H * 0.4 + R0 * 0.82 + boyut * 1.25; hiza = 'center';
  } else {
    const bosluk = 70 * u, grup = 2 * R0 * 0.72 * 0.9 + bosluk + wmG;
    const solX = W / 2 - grup / 2;
    lx = karistir(W / 2, solX + R0 * 0.72 * 0.9, kayma); ly = H / 2;
    wx = solX + 2 * R0 * 0.72 * 0.9 + bosluk; wy = H / 2 + boyut * 0.18; hiza = 'left';
  }

  // Arka plan haritası: merkezden açılır
  const tarama = E.cikisKubik(ilerleme(t, 0.35, 1.8));
  haritaCiz(ctx, W, H, t, { x: lx, y: ly }, tarama * Math.hypot(W, H) * 0.75, 1, u);

  // Başlangıç noktası + ping
  const nk = ilerleme(t, 0, 0.4);
  if (t < 0.9) {
    ctx.save();
    ctx.fillStyle = RENK.amber;
    ctx.globalAlpha = sinirla(nk * 3) * (1 - ilerleme(t, 0.6, 0.9));
    ctx.beginPath(); ctx.arc(merkez.x, merkez.y, 7 * u, 0, Math.PI * 2); ctx.fill();
    const pk = ilerleme(t, 0.05, 0.75);
    ctx.strokeStyle = RENK.amber;
    ctx.lineWidth = 2 * u;
    ctx.globalAlpha = (1 - pk) * 0.9;
    ctx.beginPath(); ctx.arc(merkez.x, merkez.y, 7 * u + 200 * u * E.cikisKubik(pk), 0, Math.PI * 2); ctx.stroke();
    ctx.restore();
  }

  // Artı işareti çizgileri (kısa süreli nişangah)
  const nis = ilerleme(t, 0.2, 0.9), nisS = 1 - ilerleme(t, 1.1, 1.6);
  if (nisS > 0 && nis > 0) {
    ctx.save();
    ctx.strokeStyle = `rgba(245,159,24,${0.35 * nisS})`;
    ctx.lineWidth = 1 * u;
    const e = E.cikisUstel(nis);
    ctx.beginPath();
    ctx.moveTo(merkez.x - W / 2 * e, merkez.y); ctx.lineTo(merkez.x + W / 2 * e, merkez.y);
    ctx.moveTo(merkez.x, merkez.y - H / 2 * e); ctx.lineTo(merkez.x, merkez.y + H / 2 * e);
    ctx.stroke();
    ctx.restore();
  }

  // Logo
  const p = {
    hex: ilerleme(t, 0.55, 1.35),
    ic: E.cikisKubik(ilerleme(t, 0.95, 1.4)),
    kontur: ilerleme(t, 1.05, 1.9),
    kol: ilerleme(t, 1.3, 1.75),
    dugum: ilerleme(t, 1.45, 1.95),
    pin: ilerleme(t, 1.45, 2.05),
    detay: ilerleme(t, 1.7, 2.2),
    parilti: E.cikisKubik(ilerleme(t, 1.9, 2.6)) * (0.8 + 0.2 * Math.sin(t * 4)),
  };
  // Pin oturduğunda küçük bir "vuruş" sarsıntısı
  const vurus = Math.max(0, 1 - Math.abs(t - 1.95) / 0.12);
  logoCiz(ctx, lx, ly, olcek * (1 + 0.03 * vurus), p, t);

  // Kelime markası + slogan
  const wk = ilerleme(t, 2.25, 2.95);
  if (wk > 0) kelimeCiz(ctx, wx, wy, boyut, [
    { metin: 'muto', renk: RENK.murekkep },
    { metin: '-', renk: RENK.soluk },
    { metin: 'atlas', renk: RENK.amber },
  ], wk, hiza);
  // ince ayırıcı çizgi
  const ck = E.cikisUstel(ilerleme(t, 2.6, 3.2));
  if (ck > 0) {
    ctx.save();
    ctx.fillStyle = 'rgba(245,159,24,0.6)';
    const cy = wy + boyut * 0.32;
    if (hiza === 'center') ctx.fillRect(wx - wmG / 2 * ck, cy, wmG * ck, 2 * u);
    else ctx.fillRect(wx, cy, wmG * ck, 2 * u);
    ctx.restore();
  }
  daktilo(ctx, wx + (hiza === 'left' ? 4 * u : 0), wy + boyut * 0.62, (dikey ? 22 : 24) * u,
    m.slogan, ilerleme(t, 2.75, 3.55) * 1.0 + ilerleme(t, 3.55, 4.2) * 0.3, t, hiza);

  hudCiz(ctx, W, H, t, ilerleme(t, 0.8, 1.8) * (1 - ilerleme(t, 4.1, 4.35)), u, m);
  vinyet(ctx, W, H);
  gren(ctx, W, H, t, u);

  // Çıkış: logonun merkezinden altıgen perde
  hexPerde(ctx, W, H, lx, ly, ilerleme(t, 4.05, 4.95), false);
}

function outroCiz(ctx, W, H, t, dil) {
  const m = METIN[dil] || METIN.en;
  const { u, dikey } = yerlesim(W, H);

  zeminCiz(ctx, W, H);
  const kapan = E.girisCikisUstel(ilerleme(t, 4.85, 5.55)); // her şey pine çöker
  const R = (dikey ? 150 : 118) * u;
  const lx = W / 2, ly = dikey ? H * 0.33 : H * 0.3;
  const hedef = { x: lx, y: ly };

  // Harita: açılır, sonunda pine doğru geri çekilir
  const ac = E.cikisKubik(ilerleme(t, 0.05, 1.5));
  haritaCiz(ctx, W, H, t, hedef, Math.hypot(W, H) * 0.75 * ac * (1 - kapan), 1, u);

  const toparla = 1 - kapan;
  const p = {
    hex: ilerleme(t, 0.35, 1.0),
    ic: E.cikisKubik(ilerleme(t, 0.6, 1.0)),
    kontur: ilerleme(t, 0.7, 1.4),
    kol: ilerleme(t, 0.85, 1.2),
    dugum: ilerleme(t, 0.9, 1.3),
    pin: ilerleme(t, 0.8, 1.3),
    detay: ilerleme(t, 1.1, 1.5),
    parilti: E.cikisKubik(ilerleme(t, 1.2, 1.8)) * (0.8 + 0.2 * Math.sin(t * 4)),
  };
  ctx.save();
  ctx.globalAlpha = sinirla(1 - ilerleme(t, 5.35, 5.6));
  logoCiz(ctx, lx, ly, R * karistir(1, 0.35, kapan), p, t);
  ctx.restore();

  // Yazılar: kapanışta pine doğru küçülür ve söner
  ctx.save();
  ctx.globalAlpha = toparla;
  ctx.translate(lx, ly);
  const sc = karistir(1, 0.6, kapan);
  ctx.scale(sc, sc);
  ctx.translate(-lx, -ly);

  const boyut1 = (dikey ? 92 : 84) * u;
  const y1 = ly + R * 1.25 + boyut1 * (dikey ? 1.2 : 1.05);
  const k1 = ilerleme(t, 1.55, 2.2), k2 = ilerleme(t, 2.1, 2.75);
  const satir = (metin, y, k, renk) => kelimeCiz(ctx, W / 2, y, boyut1, [{ metin, renk }], k, 'center');
  if (dikey) {
    satir(m.satir1, y1, k1, RENK.murekkep);
    satir(m.satir2, y1 + boyut1 * 1.15, k2, RENK.amber);
  } else {
    satir(m.satir1, y1, k1, RENK.murekkep);
    satir(m.satir2, y1 + boyut1 * 1.1, k2, RENK.amber);
  }

  // Adres hapı
  const ak = E.cikisGeri(ilerleme(t, 2.75, 3.25), 1.4);
  if (ak > 0) {
    const ay = y1 + boyut1 * (dikey ? 2.3 : 2.15);
    const fs = (dikey ? 26 : 26) * u;
    ctx.font = `600 ${fs}px "JetBrains Mono", monospace`;
    ctx.letterSpacing = `${fs * 0.04}px`;
    const tw = ctx.measureText(ADRES).width;
    const pw = (tw + fs * 3.2) * sinirla(ak, 0, 1.2), ph = fs * 2.3;
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(W / 2 - pw / 2, ay - ph / 2, pw, ph, ph / 2);
    ctx.fillStyle = 'rgba(245,159,24,0.10)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(245,159,24,0.55)';
    ctx.lineWidth = 1.5 * u;
    ctx.stroke();
    ctx.clip();
    const tk = ilerleme(t, 3.0, 3.7);
    const gor = ADRES.slice(0, Math.floor(ADRES.length * tk));
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'left';
    const bx = W / 2 - tw / 2 + fs * 0.7;
    // küçük pin ikonu
    ctx.fillStyle = RENK.amber;
    ctx.beginPath(); ctx.arc(bx - fs * 0.95, ay - fs * 0.12, fs * 0.28, Math.PI * 0.85, Math.PI * 0.15);
    ctx.lineTo(bx - fs * 0.95, ay + fs * 0.42); ctx.closePath(); ctx.fill();
    ctx.fillStyle = RENK.murekkep;
    ctx.fillText(gor, bx, ay + fs * 0.02);
    ctx.restore();
  }
  ctx.restore();

  hudCiz(ctx, W, H, t, ilerleme(t, 0.6, 1.5) * (1 - ilerleme(t, 4.7, 5.0)), u, m);
  vinyet(ctx, W, H);
  gren(ctx, W, H, t, u);

  // Açılış: tam amber ekrandan altıgen delikle açılır
  const acilis = ilerleme(t, 0, 0.75);
  if (acilis < 1) hexPerde(ctx, W, H, lx, ly, acilis, true);

  // Kapanış: pin noktası son bir kez parlar, sonra kararır
  const son = ilerleme(t, 5.45, 6.0);
  if (son > 0) {
    ctx.fillStyle = `rgba(8,9,11,${E.girisCikisKubik(son)})`;
    ctx.fillRect(0, 0, W, H);
  }
}

export function ciz(ctx, sahne, t, dil = 'en') {
  const W = ctx.canvas.width, H = ctx.canvas.height;
  ctx.save();
  ctx.letterSpacing = '0px';
  if (sahne === 'outro') outroCiz(ctx, W, H, t, dil);
  else introCiz(ctx, W, H, t, dil);
  ctx.restore();
}
