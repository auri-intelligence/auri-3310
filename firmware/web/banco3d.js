// AurI-3310 · banco ESP32: il prototipo da banco in 3D, misure in millimetri (1 unita = 1 mm).
// Fonti delle misure:
//  - ESP32-S3-DevKitC-1 v1.1, pinout J1/J3 e posizione dei pin:
//    https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html
//    (header 2x22 passo 2,54 mm, file distanti 22,86 mm; scheda ~63 x 25,4 mm dal disegno quotato Espressif, arrotondata)
//  - Modulo ESP32-S3-WROOM-1 18 x 25,5 x 3,1 mm, PSRAM ottale su GPIO 33-37 (N8R8):
//    https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf
//  - Breadboard 830 punti: 165,1 x 54,6 x 8,5 mm, 63 colonne x 10 file + 4 barre da 50 fori (valori tipici del formato)
//  - PCD8544 (controller 84x48): https://www.sparkfun.com/datasheets/LCD/Monochrome/Nokia5110.pdf ; breakout ~43,6 x 43,1 mm
//  - INMP441: https://invensense.tdk.com/products/digital/inmp441/ ; MAX98357A: https://www.analog.com/en/products/max98357a.html
//  - TP4056: https://dlnmh9ip6v2uc.cloudfront.net/datasheets/Prototyping/TP4056.pdf ; 1N4148: https://www.vishay.com/docs/81857/1n4148.pdf
//  - NPN 2N2222A (TO-92): https://www.onsemi.com/pdf/datasheet/p2n2222a-d.pdf
// Pin dei collegamenti: firmware/hal/board.py (LCD 8-12, BL 7, VIBRA 6, righe 15-18, colonne 4/5/13/14,
// I2C 1/2, POWER 0, BAT_ADC 3, CHG 21, SPEAKER 47, SD 38/39/40/41).
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const P = 2.54;                         // passo
const BB = { L: 165.1, W: 54.6, H: 8.5 };
const TABLE = -BB.H;                    // piano del tavolo: le breadboard ci appoggiano sopra
const Z1 = 25.4, Z2 = -25.4;            // centro delle file a-j delle due breadboard (davanti, dietro)
const colX = c => (c - 32) * P;
const rowP = r => { const i = 'abcdefghij'.indexOf(r); return i < 5 ? i : i + 2; };
const holeZ = (b, r) => (b === 1 ? Z1 : Z2) + (5.5 - rowP(r)) * P;
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const hole = (b, c, r) => V(colX(c), 0, holeZ(b, r));
const railOk = c => c >= 3 && c <= 61 && (c - 3) % 6 !== 5;
const railCol = c => { while (!railOk(c)) c += c < 3 ? 1 : (c > 61 ? -1 : 1); return c; };
// barra rossa (+) interna, blu (-) esterna; breadboard 1 davanti, 2 dietro
const railZ = (b, s) => b === 1 ? Z1 + (s > 0 ? 19.5 : 22.04) : Z2 - (s > 0 ? 19.5 : 22.04);
const rail = (b, s, c) => V(colX(railCol(c)), 0, railZ(b, s));

// ---------- scena ----------
const box = document.getElementById('scena');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
box.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0f1115);
const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.5, 4000);
camera.position.set(-20, 260, 260);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0);
controls.enableDamping = true;
controls.minDistance = 6;
controls.maxDistance = 900;
controls.maxPolarAngle = Math.PI * 0.49;
scene.add(new THREE.HemisphereLight(0xffffff, 0x334, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-120, 300, 200); scene.add(sun);
const ANISO = renderer.capabilities.getMaxAnisotropy();

const tavolo = new THREE.Mesh(new THREE.PlaneGeometry(600, 500), new THREE.MeshStandardMaterial({ color: 0x1d4a3a, roughness: 1 }));
tavolo.rotation.x = -Math.PI / 2; tavolo.position.y = TABLE - 0.05; scene.add(tavolo);
const grid = new THREE.GridHelper(600, 60, 0x2c6a52, 0x245a46); grid.position.y = TABLE; scene.add(grid);

const mats = {};
const mat = (c, o = {}) => { const k = c + JSON.stringify(o); return mats[k] || (mats[k] = new THREE.MeshStandardMaterial({ color: c, roughness: 0.6, ...o })); };
function bx(w, h, d, c, x, y, z, parent) {   // box con la base a y
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), typeof c === 'object' ? c : mat(c));
  m.position.set(x, y + h / 2, z); parent.add(m); return m;
}
function cyl(r, h, c, x, y, z, parent, seg = 24) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, seg), typeof c === 'object' ? c : mat(c));
  m.position.set(x, y + h / 2, z); parent.add(m); return m;
}
// piano con texture disegnata su canvas; (0,0) del disegno = angolo dietro-sinistra (xmin, zmin), unita mm
function texPlane(w, d, s, draw, cx, y, cz, parent) {
  const cv = document.createElement('canvas');
  cv.width = Math.round(w * s); cv.height = Math.round(d * s);
  const g = cv.getContext('2d'); g.scale(s, s); draw(g, w, d);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = ANISO;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshStandardMaterial({ map: t, roughness: 0.8 }));
  m.rotation.x = -Math.PI / 2; m.position.set(cx, y, cz); parent.add(m); return m;
}
function txt(g, s, x, y, size, color, rot = 0, align = 'center', bold = true) {
  g.save(); g.translate(x, y); g.rotate(rot); g.fillStyle = color;
  g.font = (bold ? '700 ' : '400 ') + size + 'px system-ui, sans-serif'; g.textAlign = align; g.textBaseline = 'middle';
  g.fillText(s, 0, 0); g.restore();
}

// ---------- componenti ----------
const groups = {};      // id -> THREE.Group
const INFO = {
  devkit: ['ESP32-S3-DevKitC-1 (N8R8)', '~63 x 25,4 mm, header 2x22 passo 2,54 mm (file a 22,86 mm)', 'logica 3,3 V; alimentazione USB 5 V', 'https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html', 'Flash 8 MB, PSRAM ottale 8 MB (GPIO 33-37 occupati). Due USB: UART e USB nativo.'],
  bb: ['Breadboard 830 punti (x2)', '165,1 x 54,6 x 8,5 mm, 63 colonne, file a-j, 4 barre', '-', 'https://it.wikipedia.org/wiki/Breadboard', 'Il DevKit e largo: una breadboard per fila di pin. La barra interna di ciascuna e staccata, le due tavole sono a ~18 mm.'],
  lcd: ['Display 84x48 PCD8544 (breakout stile 5110)', '~43,6 x 43,1 mm, 8 pin passo 2,54', '2,7-3,3 V (logica e alimentazione)', 'https://www.sparkfun.com/datasheets/LCD/Monochrome/Nokia5110.pdf', 'Bus SPI2. BL: alcuni moduli accendono la luce a GND, altri a 3V3; qui comanda GPIO 7 (PWM).'],
  sd: ['Modulo microSD SPI (3,3 V)', '~24 x 32 mm (approssimato), 6 pin', '3,3 V', 'https://www.sdcard.org/downloads/pls/', 'Bus SPI3 separato dal display. I moduli con regolatore AMS1117 vogliono 5 V su VCC: qui si usa un modulo da 3,3 V.'],
  keypad: ['Tastiera a matrice 4x4 a membrana', '~69 x 77 x 0,8 mm, coda ~86 mm, connettore 8 pin', 'passiva (pull-up interni dell\'ESP32)', 'https://it.wikipedia.org/wiki/Tastiera_a_matrice', 'Pin 1-4 righe, 5-8 colonne (verificare col tester: l\'ordine cambia tra produttori).'],
  mic: ['Microfono I2S INMP441 (breakout)', 'scheda tonda ~14 mm (approssimato), capsula 4,72 x 3,76 x 1 mm', '1,8-3,3 V', 'https://invensense.tdk.com/products/digital/inmp441/', 'L/R a GND = canale sinistro. Pin dati I2S da fissare in board.py.'],
  amp: ['Amplificatore I2S MAX98357A + altoparlante', 'breakout ~17,8 x 19,3 mm (approssimato); altoparlante 28 mm 8 ohm', '2,5-5,5 V (qui 3,3 V)', 'https://www.analog.com/en/products/max98357a.html', 'Arriva dopo il piezo. Pin I2S da fissare in board.py.'],
  vibra: ['Vibrazione: motorino + NPN + diodo', 'motorino 10 x 2,7 mm; NPN TO-92 4,6 x 3,6 mm; R 1 kohm; 1N4148 DO-35', '3 V, ~70 mA (troppi per un GPIO: serve il transistor)', 'https://www.onsemi.com/pdf/datasheet/p2n2222a-d.pdf', 'GPIO 6 -> 1 kohm -> base. Emettitore a GND, collettore al meno del motore, diodo in antiparallelo (fascia verso il +).'],
  piezo: ['Cicalino piezo passivo', 'diametro 12 mm, alto 9,5 mm, piedini a 7,6 mm', '3-5 V', 'https://en.wikipedia.org/wiki/Piezoelectric_speaker', 'GPIO 47 (SPEAKER) fa i toni con il PWM.'],
  power: ['Tasto Power (6x6 mm)', '6 x 6 x 5 mm', '-', 'https://en.wikipedia.org/wiki/Push-button', 'In parallelo al BOOT del DevKit su GPIO 0: chiude a GND, sveglia dal deep sleep.'],
  bat: ['Carica: TP4056 + LiPo', 'TP4056 ~26 x 17 mm; LiPo 503035 35 x 30 x 5 mm, 3,7 V 500 mAh', 'ingresso USB 5 V, batteria 4,2 V max', 'https://dlnmh9ip6v2uc.cloudfront.net/datasheets/Prototyping/TP4056.pdf', 'CHRG (open drain, basso in carica) -> GPIO 21. OUT+ -> partitore -> GPIO 3. OUT- a massa comune.'],
  div: ['Partitore batteria 1:2', '2 resistenze 100 kohm 1/4 W (corpo 6,3 x 2,4 mm)', 'max 4,2 V in, 2,1 V sul GPIO 3', 'https://it.wikipedia.org/wiki/Partitore_di_tensione', 'BAT_DIVIDER = 2.0 in board.py.'],
};
function grp(id) { const g = new THREE.Group(); g.userData.comp = id; scene.add(g); groups[id] = g; return g; }

// breadboard: strip di file a-j + barre su un lato
function breadboard(b, g) {
  const inner = 16.5, outer = 27.3;
  const zmin = b === 1 ? Z1 - inner : Z2 - outer, zmax = b === 1 ? Z1 + outer : Z2 + inner;
  const d = zmax - zmin, cz = (zmin + zmax) / 2;
  bx(BB.L, BB.H, d, 0xeeece4, 0, -BB.H, cz, g);
  texPlane(BB.L, d, 14, (c) => {
    c.fillStyle = '#f1efe7'; c.fillRect(0, 0, BB.L, d);
    const X = x => x + BB.L / 2, Z = z => z - zmin;
    c.fillStyle = '#d9d6cb'; c.fillRect(0, Z((b === 1 ? Z1 : Z2) - 1.27 * 1.0) , BB.L, 2.54);  // canale centrale
    for (let col = 1; col <= 63; col++) for (const r of 'abcdefghij') {
      const x = X(colX(col)), z = Z(holeZ(b, r));
      c.fillStyle = '#9a978d'; c.fillRect(x - 0.7, z - 0.7, 1.4, 1.4);
      c.fillStyle = '#222'; c.fillRect(x - 0.5, z - 0.5, 1, 1);
    }
    for (let col = 1; col <= 63; col++) if (col === 1 || col % 5 === 0) {
      txt(c, String(col), X(colX(col)), Z(holeZ(b, 'a')) + 2.3, 1.5, '#555');
      txt(c, String(col), X(colX(col)), Z(holeZ(b, 'j')) - 2.3, 1.5, '#555');
    }
    for (const r of 'abcdefghij') {
      txt(c, r, X(colX(-0.2)), Z(holeZ(b, r)), 1.6, '#555');
      txt(c, r, X(colX(64.2)), Z(holeZ(b, r)), 1.6, '#555');
    }
    for (const s of [1, -1]) {
      const z = Z(railZ(b, s));
      for (let col = 3; col <= 61; col++) if (railOk(col)) {
        const x = X(colX(col)); c.fillStyle = '#9a978d'; c.fillRect(x - 0.7, z - 0.7, 1.4, 1.4); c.fillStyle = '#222'; c.fillRect(x - 0.5, z - 0.5, 1, 1);
      }
      const lz = z + (s > 0 ? -1 : 1) * 1.6 * (b === 1 ? 1 : -1);
      c.fillStyle = s > 0 ? '#d22' : '#25c'; c.fillRect(X(colX(2)), lz - 0.25, X(colX(62)) - X(colX(2)), 0.5);
      txt(c, s > 0 ? '+' : '−', X(colX(1)), z, 2.4, s > 0 ? '#d22' : '#25c');
      txt(c, s > 0 ? '+' : '−', X(colX(63)), z, 2.4, s > 0 ? '#d22' : '#25c');
    }
    txt(c, b === 1 ? 'BREADBOARD 1 (davanti, J1)' : 'BREADBOARD 2 (dietro, J3)', X(colX(52)), b === 1 ? d - 1.4 : 1.4, 1.5, '#888');
  }, 0, 0.02, cz, g);
}
const gbb = grp('bb'); breadboard(1, gbb); breadboard(2, gbb);

// ---------- DevKitC-1 ----------
const J1 = ['3V3', '3V3', 'RST', '4', '5', '6', '7', '15', '16', '17', '18', '8', '3', '46', '9', '10', '11', '12', '13', '14', '5V', 'G'];
const J3 = ['G', 'TX', 'RX', '1', '2', '42', '41', '40', '39', '38', '37', '36', '35', '0', '45', '48', '47', '21', '20', '19', 'G', 'G'];
const pinCol = n => 25 - n;             // pin 1 in colonna 24, pin 22 in colonna 3
const jz1 = holeZ(1, 'j'), jz3 = holeZ(2, 'a');   // +11,43 / -11,43
function espPin(name) {          // 'GPIO12' / '3V3' / 'G' -> {hdr, n, col}
  const k = name.replace('GPIO', '');
  let n = J1.indexOf(k); if (n >= 0) return { hdr: 'J1', n: n + 1, col: pinCol(n + 1) };
  n = J3.indexOf(k); return { hdr: 'J3', n: n + 1, col: pinCol(n + 1) };
}
{
  const g = grp('devkit');
  const x0 = -77.5, x1 = -14.5, W = x1 - x0, D = 25.4, y = 2.5;
  for (const z of [jz1, jz3]) {
    bx(22 * P, 2.5, P, 0x111111, (colX(3) + colX(24)) / 2, 0, z, g);
  }
  bx(W, 1.6, D, 0x16181c, (x0 + x1) / 2, y, 0, g);
  texPlane(W, D, 22, (c) => {
    c.fillStyle = '#16181c'; c.fillRect(0, 0, W, D);
    const X = x => x - x0, Z = z => z + D / 2;
    for (let n = 1; n <= 22; n++) {
      const x = X(colX(pinCol(n)));
      for (const [z, lab, dir] of [[jz1, J1[n - 1], -1], [jz3, J3[n - 1], 1]]) {
        c.fillStyle = '#c9a33a'; c.beginPath(); c.arc(x, Z(z), 0.85, 0, 7); c.fill();
        c.fillStyle = '#333'; c.beginPath(); c.arc(x, Z(z), 0.4, 0, 7); c.fill();
        const bad = ['35', '36', '37'].includes(lab);
        txt(c, lab, x, Z(z) + dir * 2.6, 1.25, bad ? '#ff7a6a' : '#fff', -Math.PI / 2);
      }
    }
    txt(c, 'J1', X(colX(25.3)), Z(jz1), 1.4, '#9fe06a'); txt(c, 'J3', X(colX(25.3)), Z(jz3), 1.4, '#9fe06a');
    txt(c, 'ESP32-S3-DevKitC-1  N8R8', X(-58), Z(0), 1.9, '#ddd');
    txt(c, 'BOOT = GPIO0', X(-70.5), Z(-4.2), 1.2, '#bbb'); txt(c, 'RST', X(-70.5), Z(4.2), 1.2, '#bbb');
    txt(c, 'RGB LED = GPIO38', X(-50), Z(4), 1.2, '#bbb');
  }, (x0 + x1) / 2, y + 1.61, 0, g);
  // modulo WROOM-1 (18 x 25,5 x 3,1) con schermo metallico, antenna oltre il bordo dei pin 1
  bx(25.5, 0.8, 18, 0x1b2b20, x1 - 12.75, y + 1.6, 0, g);
  bx(17.6, 2.3, 15.8, 0xb8bcc2, x1 - 17.6 / 2 - 7, y + 2.4, 0, g);
  bx(6, 0.05, 15, 0x7a6a30, x1 - 3.6, y + 2.4, 0, g);
  // due USB (UART, USB) all'estremita dei pin 22, tasti BOOT/RST, LED
  for (const z of [-5.5, 5.5]) bx(7.4, 3.2, 9, 0xaeb2b8, x0 + 2.8, y + 1.6, z, g);
  bx(3.5, 1.2, 3, 0x333, x0 + 7, y + 1.6, -4.2, g); cyl(0.9, 1.6, 0x222, x0 + 7, y + 2.8, -4.2, g);
  bx(3.5, 1.2, 3, 0x333, x0 + 7, y + 1.6, 4.2, g); cyl(0.9, 1.6, 0x222, x0 + 7, y + 2.8, 4.2, g);
  bx(5, 1.5, 5, 0xf4f4f0, -50, y + 1.6, 7, g);
}

// ---------- moduli generici su tavolo ----------
// pin in fila lungo x locale, a z locale pz; ritorna funzione pin(nome) -> punta del pin nel mondo
function modulo(id, o) {
  const g = o.group || grp(id);
  const sub = new THREE.Group(); sub.userData.comp = id; g.add(sub);
  sub.position.set(o.x, TABLE, o.z); sub.rotation.y = o.rot || 0;
  const yb = 1.0, t = 1.6;
  bx(o.w, t, o.d, o.color, 0, yb, 0, sub);
  for (const [fx, fz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) cyl(0.8, yb, 0x444, fx * (o.w / 2 - 2), 0, fz * (o.d / 2 - 2), sub, 8);
  const n = o.pins.length, px = i => (i - (n - 1) / 2) * P;
  texPlane(o.w, o.d, 20, (c, w, d) => {
    c.fillStyle = o.css; c.fillRect(0, 0, w, d);
    for (let i = 0; i < n; i++) {
      const x = px(i) + w / 2, z = o.pz + d / 2;
      c.fillStyle = '#c9a33a'; c.beginPath(); c.arc(x, z, 0.85, 0, 7); c.fill();
      txt(c, o.pins[i], x, z + 1.6, 1.15, '#fff', -Math.PI / 2, 'right');
    }
    if (o.draw) o.draw(c, w, d);
  }, 0, yb + t + 0.01, 0, sub);
  const top = yb + t;
  bx(n * P, 2.5, P, 0x111, 0, top, o.pz, sub);
  for (let i = 0; i < n; i++) bx(0.64, 6, 0.64, 0xd4b24a, px(i), top + 2.5, o.pz, sub);
  sub.updateMatrixWorld(true);
  const tip = top + 2.5 + 6;
  return name => { const i = o.pins.indexOf(name); return sub.localToWorld(V(px(i), tip, o.pz)); };
}

const lcdPin = modulo('lcd', {
  x: -78, z: 100, w: 43.6, d: 43.1, color: 0x8a1f1f, css: '#8a1f1f', pz: -43.1 / 2 + 2.2,
  pins: ['RST', 'CE', 'DC', 'DIN', 'CLK', 'VCC', 'BL', 'GND'],
  draw: (c, w, d) => {
    c.fillStyle = '#c8ccc0'; c.fillRect(2, 7, w - 4, d - 11);
    c.fillStyle = '#9fb59a'; c.fillRect(7, 12, w - 14, d - 22);
    txt(c, 'AurI-3310', w / 2, d / 2 + 1, 4.2, '#1d2a1b'); txt(c, '84x48 PCD8544', w / 2, d / 2 + 7, 2, '#3a4a38', 0, 'center', false);
  },
});
// metallo e vetro sopra il display
{ const s = groups.lcd.children[0]; bx(40, 3.2, 32, 0xb8bcc2, 0, 2.6, 1.5, s); texPlane(34, 22, 16, (c, w, d) => { c.fillStyle = '#9fb59a'; c.fillRect(0, 0, w, d); txt(c, 'AurI-3310', w / 2, d / 2 - 2, 4.4, '#1d2a1b'); txt(c, 'banco ESP32', w / 2, d / 2 + 4, 2.2, '#2d3a2b', 0, 'center', false); }, 0, 5.82, 1.5, s); }

const sdPin = modulo('sd', {
  x: -40, z: -95, rot: Math.PI, w: 24, d: 32, color: 0x123a7a, css: '#123a7a', pz: -32 / 2 + 2.2,
  pins: ['3V3', 'CS', 'MOSI', 'SCK', 'MISO', 'GND'],
  draw: (c, w, d) => { c.fillStyle = '#ccc'; c.fillRect(3, 12, w - 6, 16); c.fillStyle = '#333'; c.fillRect(5, 14, w - 10, 12); txt(c, 'microSD', w / 2, 20, 2, '#ddd'); },
});
{ const s = groups.sd.children[0]; bx(15, 1.6, 15, 0xc8ccd2, 0, 2.6, 6, s); bx(11, 0.7, 11, 0x222, 0, 4.2, 9, s); }

const micPin = modulo('mic', {
  x: 38, z: -88, rot: Math.PI, w: 16, d: 14, color: 0x1a1a6a, css: '#1a1a6a', pz: -14 / 2 + 2,
  pins: ['SD', 'VDD', 'GND', 'L/R', 'WS', 'SCK'],
  draw: (c, w, d) => txt(c, 'INMP441', w / 2, d - 3, 1.6, '#ddd'),
});
{ const s = groups.mic.children[0]; bx(4.72, 1, 3.76, 0xaaaaaa, 0, 2.6, 3, s); }

const ampPin = modulo('amp', {
  x: 78, z: -88, rot: Math.PI, w: 17.8, d: 19.3, color: 0x1a1a1a, css: '#262626', pz: -19.3 / 2 + 2,
  pins: ['LRC', 'BCLK', 'DIN', 'GAIN', 'SD', 'GND', 'Vin'],
  draw: (c, w, d) => { txt(c, 'MAX98357A', w / 2, d / 2, 1.6, '#ddd'); txt(c, '+   −', w / 2, d - 2, 1.6, '#ddd'); },
});
{ const s = groups.amp.children[0]; bx(3, 0.9, 3, 0x111, 0, 2.6, 0, s); bx(7.6, 6, 5, 0x2a7ad4, 0, 2.6, 19.3 / 2 - 3, s); }
// altoparlante 28 mm
{ const g = groups.amp; cyl(14, 4, 0x2b2b2b, 78, TABLE, -135, g, 40); cyl(10, 4.3, 0x111, 78, TABLE, -135, g, 40); }
const spkA = V(78 - 5, TABLE + 4, -135 + 10), spkB = V(78 + 5, TABLE + 4, -135 + 10);
const ampOut = s => groups.amp.children[0].localToWorld(V(s * 1.8, 2.6 + 6, 19.3 / 2 - 3));

// tastiera 4x4: membrana + coda + connettore con strip maschio
const keyPin = (() => {
  const g = grp('keypad'), cx = 0, cz = 182;
  bx(69, 0.8, 77, 0x1c1c1c, cx, TABLE, cz, g);
  texPlane(69, 77, 10, (c, w, d) => {
    c.fillStyle = '#222'; c.fillRect(0, 0, w, d);
    const L = [['1', '2', '3', 'A'], ['4', '5', '6', 'B'], ['7', '8', '9', 'C'], ['*', '0', '#', 'D']];
    const cols = ['#3a6fd8', '#3a6fd8', '#3a6fd8', '#d83a3a'];
    for (let r = 0; r < 4; r++) for (let k = 0; k < 4; k++) {
      const x = 5 + k * 15.5, z = 6 + r * 17.8;
      c.fillStyle = k === 3 ? cols[3] : (L[r][k] === '*' || L[r][k] === '#' ? '#888' : cols[0]);
      c.fillRect(x, z, 12, 14); txt(c, L[r][k], x + 6, z + 7, 7, '#fff');
    }
  }, cx, TABLE + 0.81, cz, g);
  bx(20, 0.4, 86, 0x8a8a7a, cx, TABLE, cz - 77 / 2 - 43 + 0.5, g);
  const pz = cz - 77 / 2 - 86 + 1;
  bx(8 * P, 2.6, 2.6, 0x111, cx, TABLE, pz, g);
  for (let i = 0; i < 8; i++) bx(0.64, 9, 0.64, 0xd4b24a, cx + (i - 3.5) * P, TABLE + 2.6, pz - 1, g);
  texPlane(8 * P, 6, 30, (c, w) => { for (let i = 0; i < 8; i++) txt(c, ['R1', 'R2', 'R3', 'R4', 'C1', 'C2', 'C3', 'C4'][i], (i + 0.5) * P, 3, 1.2, '#fff', -Math.PI / 2); }, cx, TABLE + 0.45, pz + 5, g);
  return i => V(cx + (i - 3.5) * P, TABLE + 11.6, pz - 1);
})();

// TP4056 + LiPo a destra
const tpPin = modulo('bat', {
  x: 112, z: 32, rot: -Math.PI / 2, w: 26, d: 17, color: 0x1d3f8a, css: '#1d3f8a', pz: 17 / 2 - 2.2,
  pins: ['OUT−', 'OUT+', 'CHRG'],
  draw: (c, w, d) => { txt(c, 'TP4056', w / 2, d / 2, 2.2, '#ddd'); txt(c, 'B+  B−', w - 6, 3, 1.6, '#ddd'); txt(c, 'CHRG = filo saldato al LED rosso', w / 2, d / 2 + 3, 1.1, '#ffd28a', 0, 'center', false); },
});
{ const s = groups.bat.children[0]; bx(9, 3.2, 7.4, 0xaeb2b8, -26 / 2 + 3.5, 2.6, 0, s); bx(2.9, 1.2, 3, 0x111, 0, 2.6, 0, s); bx(1.6, 0.8, 0.8, 0xff3030, 4, 2.6, -4, s); bx(1.6, 0.8, 0.8, 0x30a0ff, 6, 2.6, -4, s); }
{ const g = groups.bat; bx(30, 5, 35, 0xc0c4c8, 140, TABLE, 70, g); texPlane(28, 33, 10, (c, w, d) => { c.fillStyle = '#c0c4c8'; c.fillRect(0, 0, w, d); txt(c, 'LiPo 3,7 V', w / 2, d / 2 - 3, 3, '#333'); txt(c, '500 mAh 503035', w / 2, d / 2 + 2, 2.2, '#333', 0, 'center', false); }, 140, TABLE + 5.01, 70, g); }
const tpB = s => groups.bat.children[0].localToWorld(V(26 / 2 - 4 + (s > 0 ? -2 : 1.5), 2.7, -17 / 2 + 3));

// ---------- pezzi sulla breadboard ----------
const onTop = (p, dy) => V(p.x, p.y + dy, p.z);
function leg(a, b, g, c = 0xbbbbbb) {   // filo rigido tra due punti
  const d = b.clone().sub(a), m = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, d.length(), 6), mat(c));
  m.position.copy(a).addScaledVector(d, 0.5); m.quaternion.setFromUnitVectors(V(0, 1, 0), d.clone().normalize()); g.add(m); return m;
}
function resistor(g, a, b, bands) {
  const h = 2.4, A = onTop(a, h), B = onTop(b, h);
  leg(a, A, g); leg(b, B, g); leg(A, B, g);
  const mid = A.clone().add(B).multiplyScalar(0.5), dir = B.clone().sub(A).normalize();
  const body = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.2, 6.3, 16), mat(0xd9c49a));
  body.position.copy(mid); body.quaternion.setFromUnitVectors(V(0, 1, 0), dir); g.add(body);
  bands.forEach((c, i) => { const r = new THREE.Mesh(new THREE.CylinderGeometry(1.25, 1.25, 0.6, 16), mat(c)); r.position.copy(mid).addScaledVector(dir, -2.2 + i * 1.3 + (i === 3 ? 0.6 : 0)); r.quaternion.copy(body.quaternion); g.add(r); });
}
{ // vibrazione: R 1k (36b-40b), NPN E39 B40 C41 fila d, diodo 41c-44c, motore -41a +44a
  const g = grp('vibra');
  resistor(g, hole(1, 36, 'b'), hole(1, 40, 'b'), [0x7a4a1a, 0x111111, 0xcc2222, 0xc9a33a]);
  for (const c of [39, 40, 41]) leg(hole(1, c, 'd'), onTop(hole(1, c, 'd'), 4), g);
  const q = new THREE.Mesh(new THREE.CylinderGeometry(2.3, 2.3, 4.6, 20, 1, false, -Math.PI / 2, Math.PI), mat(0x1a1a1a));
  q.position.copy(onTop(hole(1, 40, 'd'), 6.3)); g.add(q);
  bx(4.6, 4.6, 0.1, 0x1a1a1a, colX(40), 4, holeZ(1, 'd'), g);
  texPlane(4.4, 4.4, 40, (c) => { c.fillStyle = '#1a1a1a'; c.fillRect(0, 0, 4.4, 4.4); txt(c, 'NPN', 2.2, 1.4, 1.1, '#ddd'); txt(c, 'E B C', 2.2, 3, 0.9, '#ddd'); }, colX(40), 8.61, holeZ(1, 'd') + 0.1, g).rotation.set(0, 0, 0);
  // diodo DO-35, fascia (catodo) verso 44
  { const A = onTop(hole(1, 41, 'c'), 1.8), B = onTop(hole(1, 44, 'c'), 1.8); leg(hole(1, 41, 'c'), A, g); leg(hole(1, 44, 'c'), B, g); leg(A, B, g);
    const d = new THREE.Mesh(new THREE.CylinderGeometry(0.93, 0.93, 3.9, 14), mat(0xe07a30, { transparent: true, opacity: 0.85 })); d.position.copy(A.clone().add(B).multiplyScalar(0.5)); d.rotation.z = Math.PI / 2; g.add(d);
    const k = cyl(0.97, 0.6, 0x111, 0, 0, 0, g); k.position.copy(d.position).add(V(1.4, 0, 0)); k.rotation.z = Math.PI / 2; }
  // motorino a moneta sul tavolo
  cyl(5, 2.7, 0xb8bcc2, 62, TABLE, 72, g, 30);
}
{ const g = grp('piezo'); cyl(6, 9.5, 0x151515, (colX(48) + colX(51)) / 2, 0, holeZ(2, 'h'), g, 30); cyl(1, 0.2, 0x555, (colX(48) + colX(51)) / 2, 9.5, holeZ(2, 'h'), g); }
{ const g = grp('power'); const x = (colX(30) + colX(32)) / 2, z = (holeZ(2, 'e') + holeZ(2, 'f')) / 2;
  bx(6, 3.5, 6, 0x222, x, 0, z, g); cyl(1.75, 1.5, 0x111, x, 3.5, z, g);
  for (const c of [30, 32]) for (const r of 'ef') leg(hole(2, c, r), V(colX(c), 1, holeZ(2, r)), g); }
{ const g = grp('div');
  resistor(g, hole(1, 52, 'c'), hole(1, 55, 'c'), [0x7a4a1a, 0x111111, 0xe8d020, 0xc9a33a]);
  resistor(g, hole(1, 55, 'b'), hole(1, 58, 'b'), [0x7a4a1a, 0x111111, 0xe8d020, 0xc9a33a]); }

// ---------- fili ----------
const COL = { r: 0xe02020, k: 0x151515, y: 0xf0d020, b: 0x2060e0, g: 0x20a040, o: 0xf08020, w: 0xf0f0f0, p: 0x9040c0, pk: 0xf080b0, br: 0x8a5a2a, gr: 0x8a8a8a, c: 0x30c0d0 };
const conns = [];
const wires = [];
function wire(a, b, color, h, meta) {
  const up = Math.max(a.y, b.y) + h;
  const pts = [a, onTop(a, 3), V(a.x + (b.x - a.x) * 0.25, up, a.z + (b.z - a.z) * 0.25), V(a.x + (b.x - a.x) * 0.75, up, a.z + (b.z - a.z) * 0.75), onTop(b, 3), b];
  const curve = new THREE.CatmullRomCurve3(pts, false, 'centripetal');
  const m = new THREE.MeshStandardMaterial({ color, roughness: 0.5, transparent: true, opacity: 1 });
  const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 80, 0.7, 8), m);
  mesh.userData.wire = conns.length;
  scene.add(mesh);
  for (const p of [a, b]) { const k = new THREE.Mesh(new THREE.BoxGeometry(2.5, 6, 2.5), mat(0x111)); k.position.copy(onTop(p, p.y > 0.5 ? -2 : 3)); mesh.add(k); }
  const c = { ...meta, color, mesh, mid: curve.getPoint(0.5) };
  conns.push(c); wires.push(mesh); return c;
}
const espHole = (name, r) => { const p = espPin(name); return p.hdr === 'J1' ? hole(1, p.col, r || 'h') : hole(2, p.col, r || 'c'); };
const lab = name => { const p = espPin(name); return `${name} (${p.hdr}-${p.n})`; };
let hh = 8;
const H = () => (hh += 1.3);
// alimentazione
wire(espHole('3V3', 'g'), rail(1, 1, 24), COL.r, 3, { esp: lab('3V3'), comp: 'bb', to: 'barra + davanti', note: '3,3 V' });
wire(espHole('G', 'g'), rail(1, -1, 3), COL.k, 3, { esp: 'G (J1-22)', comp: 'bb', to: 'barra − davanti', note: 'massa' });
{ const p = hole(2, pinCol(1), 'd'); wire(p, rail(2, -1, 24), COL.k, 3, { esp: 'G (J3-1)', comp: 'bb', to: 'barra − dietro', note: 'massa' }); }
wire(rail(1, 1, 61), rail(2, 1, 61), COL.r, 12, { esp: '-', comp: 'bb', to: 'barra + dietro', note: 'ponte 3,3 V tra le breadboard' });
wire(rail(1, -1, 63), rail(2, -1, 63), COL.k, 14, { esp: '-', comp: 'bb', to: 'barra − dietro', note: 'ponte massa' });
// display (SPI2)
const LCD = [['GPIO8', 'RST', COL.p, 'LCD_RES'], ['GPIO10', 'CE', COL.o, 'LCD_SCE'], ['GPIO9', 'DC', COL.w, 'LCD_DC'], ['GPIO11', 'DIN', COL.b, 'LCD_SDIN (MOSI)'], ['GPIO12', 'CLK', COL.y, 'LCD_SCLK'], ['GPIO7', 'BL', COL.pk, 'BACKLIGHT (PWM)']];
for (const [e, p, c, n] of LCD) wire(espHole(e), lcdPin(p), c, H(), { esp: lab(e), comp: 'lcd', to: 'Display ' + p, note: n });
wire(rail(1, 1, 22), lcdPin('VCC'), COL.r, 10, { esp: '3V3', comp: 'lcd', to: 'Display VCC', note: 'dalla barra +' });
wire(rail(1, -1, 15), lcdPin('GND'), COL.k, 9, { esp: 'GND', comp: 'lcd', to: 'Display GND', note: 'dalla barra −' });
// tastiera
[15, 16, 17, 18].forEach((gp, i) => wire(espHole('GPIO' + gp), keyPin(i), COL.br, H(), { esp: lab('GPIO' + gp), comp: 'keypad', to: 'Tastiera R' + (i + 1), note: 'KEY_ROWS[' + i + ']' }));
[4, 5, 13, 14].forEach((gp, i) => wire(espHole('GPIO' + gp), keyPin(4 + i), COL.gr, H(), { esp: lab('GPIO' + gp), comp: 'keypad', to: 'Tastiera C' + (i + 1), note: 'KEY_COLS[' + i + ']' }));
// vibrazione
wire(espHole('GPIO6'), hole(1, 36, 'e'), COL.c, H(), { esp: lab('GPIO6'), comp: 'vibra', to: 'R 1 kohm -> base NPN', note: 'VIBRA' });
wire(hole(1, 39, 'a'), rail(1, -1, 39), COL.k, 2, { esp: '-', comp: 'vibra', to: 'emettitore NPN', note: 'a massa' });
wire(hole(1, 44, 'b'), rail(1, 1, 45), COL.r, 2, { esp: '-', comp: 'vibra', to: 'motore + / catodo diodo', note: '3,3 V' });
wire(hole(1, 41, 'a'), V(60, TABLE + 2.7, 68), 0x3060ff, 4, { esp: '-', comp: 'vibra', to: 'motorino −', note: 'filo del motore, al collettore' });
wire(hole(1, 44, 'a'), V(64, TABLE + 2.7, 68), COL.r, 5, { esp: '-', comp: 'vibra', to: 'motorino +', note: 'filo del motore' });
// piezo, tasto power, carica, batteria
wire(espHole('GPIO47'), hole(2, 48, 'f'), COL.g, H(), { esp: lab('GPIO47'), comp: 'piezo', to: 'Piezo +', note: 'SPEAKER (toni PWM)' });
wire(hole(2, 51, 'j'), rail(2, -1, 51), COL.k, 2, { esp: '-', comp: 'piezo', to: 'Piezo −', note: 'a massa' });
wire(espHole('GPIO0'), hole(2, 30, 'c'), COL.o, H(), { esp: lab('GPIO0'), comp: 'power', to: 'Tasto Power', note: 'POWER_KEY, attivo basso (come BOOT)' });
wire(hole(2, 30, 'j'), rail(2, -1, 30), COL.k, 2, { esp: '-', comp: 'power', to: 'Tasto Power, altro lato', note: 'a massa' });
wire(espHole('GPIO3'), hole(1, 55, 'e'), COL.w, H(), { esp: lab('GPIO3'), comp: 'div', to: 'centro partitore', note: 'BAT_ADC (1:2)' });
wire(hole(1, 58, 'a'), rail(1, -1, 57), COL.k, 2, { esp: '-', comp: 'div', to: 'partitore, lato basso', note: 'a massa' });
wire(tpPin('OUT+'), hole(1, 52, 'e'), COL.r, 8, { esp: '-', comp: 'bat', to: 'TP4056 OUT+ -> partitore', note: 'tensione batteria, max 4,2 V' });
wire(tpPin('OUT−'), rail(1, -1, 55), COL.k, 7, { esp: '-', comp: 'bat', to: 'TP4056 OUT−', note: 'massa comune' });
wire(espHole('GPIO21'), tpPin('CHRG'), COL.y, 22, { esp: lab('GPIO21'), comp: 'bat', to: 'TP4056 CHRG', note: 'CHG_DET, basso in carica' });
wire(tpB(1), V(130, TABLE + 3, 56), COL.r, 4, { esp: '-', comp: 'bat', to: 'LiPo +  (B+)', note: '' });
wire(tpB(-1), V(134, TABLE + 3, 56), COL.k, 4, { esp: '-', comp: 'bat', to: 'LiPo −  (B−)', note: '' });
// microSD (SPI3)
const SD = [['GPIO41', 'CS', COL.o, 'SD_CS'], ['GPIO38', 'MOSI', COL.b, 'SD_MOSI'], ['GPIO39', 'SCK', COL.y, 'SD_SCK'], ['GPIO40', 'MISO', COL.g, 'SD_MISO']];
for (const [e, p, c, n] of SD) wire(espHole(e), sdPin(p), c, H(), { esp: lab(e), comp: 'sd', to: 'microSD ' + p, note: n + ' (SPI3)' });
wire(rail(2, 1, 33), sdPin('3V3'), COL.r, 8, { esp: '3V3', comp: 'sd', to: 'microSD 3V3', note: 'dalla barra + dietro' });
wire(rail(2, -1, 27), sdPin('GND'), COL.k, 7, { esp: 'GND', comp: 'sd', to: 'microSD GND', note: '' });
// microfono e amplificatore: solo alimentazione (pin I2S non ancora in board.py)
wire(rail(2, 1, 39), micPin('VDD'), COL.r, 8, { esp: '3V3', comp: 'mic', to: 'INMP441 VDD', note: 'dati I2S da fissare' });
wire(rail(2, -1, 45), micPin('GND'), COL.k, 7, { esp: 'GND', comp: 'mic', to: 'INMP441 GND', note: '' });
wire(micPin('GND'), micPin('L/R'), COL.k, 4, { esp: '-', comp: 'mic', to: 'INMP441 L/R a GND', note: 'canale sinistro' });
wire(rail(2, 1, 55), ampPin('Vin'), COL.r, 8, { esp: '3V3', comp: 'amp', to: 'MAX98357A Vin', note: 'dati I2S da fissare' });
wire(rail(2, -1, 57), ampPin('GND'), COL.k, 7, { esp: 'GND', comp: 'amp', to: 'MAX98357A GND', note: '' });
wire(ampOut(1), spkA, COL.r, 6, { esp: '-', comp: 'amp', to: 'altoparlante +', note: '' });
wire(ampOut(-1), spkB, COL.k, 6, { esp: '-', comp: 'amp', to: 'altoparlante −', note: '' });
// riga informativa: I2C libero
conns.push({ esp: 'GPIO1 / GPIO2 (J3-4/5)', comp: 'devkit', to: 'I2C SDA / SCL', note: 'libero: nessun modulo del banco', color: 0x666666, mid: espHole('GPIO1', 'c') });

// ---------- pannello ----------
const hex = c => '#' + c.toString(16).padStart(6, '0');
const tab = document.getElementById('conns');
tab.innerHTML = '<tr><td><b>ESP32</b></td><td><b>va a</b></td><td><b>note</b></td></tr>' +
  conns.map((c, i) => `<tr class="c" data-i="${i}"><td><span class="sw" style="background:${hex(c.color)}"></span>${c.esp}</td><td>${c.to}</td><td>${c.note}</td></tr>`).join('');
let sel = -1;
function select(i, fly = true) {
  sel = i;
  tab.querySelectorAll('tr.c').forEach(r => r.classList.toggle('sel', +r.dataset.i === i));
  wires.forEach(w => { const on = i < 0 || w.userData.wire === i; w.material.opacity = on ? 1 : 0.18; w.material.emissive.setHex(w.userData.wire === i ? 0x335522 : 0); });
  if (i >= 0 && fly) { flyTo(conns[i].mid, 70); showInfo(conns[i].comp); }
}
tab.addEventListener('click', e => { const r = e.target.closest('tr.c'); if (r) select(+r.dataset.i === sel ? -1 : +r.dataset.i); });
function showInfo(id) {
  const k = INFO[id], el = document.getElementById('info'); if (!k) return;
  el.style.display = 'block';
  el.innerHTML = `<b>${k[0]}</b><p>Misure: ${k[1]}</p><p>Tensione: ${k[2]}</p><p>${k[4]}</p><p><a href="${k[3]}" target="_blank" rel="noopener">datasheet / riferimento</a></p>`;
}
const NOMI = { devkit: 'DevKit', bb: 'Breadboard', lcd: 'Display', sd: 'microSD', keypad: 'Tastiera', mic: 'INMP441', amp: 'MAX98357A', vibra: 'Vibrazione', piezo: 'Piezo', power: 'Power', div: 'Partitore', bat: 'TP4056+LiPo' };
document.getElementById('toggles').innerHTML = Object.keys(NOMI).map(k => `<label><input type="checkbox" data-k="${k}" checked> ${NOMI[k]}</label>`).join('');
document.getElementById('toggles').addEventListener('change', e => {
  const k = e.target.dataset.k, on = e.target.checked; groups[k].visible = on;
  conns.forEach(c => { if (c.mesh && c.comp === k) c.mesh.visible = on; });
});
document.getElementById('apri').onclick = () => document.body.classList.toggle('closed');
if (innerWidth < 760) document.body.classList.add('closed');

// ---------- camera e picking ----------
let fly = null;
function flyTo(p, dist) {
  const dir = camera.position.clone().sub(controls.target).normalize();
  fly = { t0: performance.now(), a: controls.target.clone(), b: p.clone(), ca: camera.position.clone(), cb: p.clone().addScaledVector(dir, dist) };
}
const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
let down = null;
renderer.domElement.addEventListener('pointerdown', e => { down = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', e => {
  if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 6) return;
  const r = renderer.domElement.getBoundingClientRect();
  ptr.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
  ray.setFromCamera(ptr, camera);
  const hit = ray.intersectObjects([...wires, ...Object.values(groups)], true).find(h => h.object.visible && h.object.material.opacity !== 0.18);
  if (!hit) { select(-1, false); return; }
  let o = hit.object;
  while (o && o.userData.wire === undefined && !o.userData.comp) o = o.parent;
  if (!o) return;
  if (o.userData.wire !== undefined) { select(o.userData.wire); tab.querySelector(`tr[data-i="${o.userData.wire}"]`)?.scrollIntoView({ block: 'nearest' }); }
  else { showInfo(o.userData.comp); if (innerWidth < 760) document.body.classList.remove('closed'); }
});
addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
renderer.setAnimationLoop(() => {
  if (fly) {
    const k = Math.min(1, (performance.now() - fly.t0) / 700), s = k * k * (3 - 2 * k);
    controls.target.lerpVectors(fly.a, fly.b, s); camera.position.lerpVectors(fly.ca, fly.cb, s);
    if (k >= 1) fly = null;
  }
  controls.update(); renderer.render(scene, camera);
});
window.banco = { conns, groups, select, flyTo, camera, controls, pronto: true };
