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
//  - 1N4148: https://www.vishay.com/docs/81857/1n4148.pdf
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
// telefono (schermo stretto o tocco): interfaccia tipo app, meno pixel e tubi piu' leggeri
const MOB = matchMedia('(max-width: 760px)').matches;
const SEG = MOB ? 40 : 80;
const box = document.getElementById('scena');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, MOB ? 1.5 : 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
box.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0f1115);
const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.5, 4000);
camera.position.set(-20, 260, 260);
if (MOB) camera.position.set(-30, 380, 420);   // sul telefono lo schermo e' stretto: si parte piu' lontani
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
  lcd: ["Display ORIGINALE del 3310 (PCD8544) su basetta adattatrice", "vetro ~38 x 34 mm (da misurare col calibro); basetta millefori ~44 x 43 mm con strip 8 pin", "2,7-3,3 V", "https://www.sparkfun.com/datasheets/LCD/Monochrome/Nokia5110.pdf", "Riuso dal telefono: è lo stesso chip del modulo 5110. Ha contatti a molla, non pin: si appoggia su piazzole della basetta (o fili sottili saldati). Sul banco meglio un modulo 5110 da 3-4 euro, l’originale solo nel telefono finito (se si rompe non si ricompra)."],
  sd: ['Modulo microSD SPI (3,3 V)', '~24 x 32 mm (approssimato), 6 pin', '3,3 V', 'https://www.sdcard.org/downloads/pls/', 'Bus SPI3 separato dal display. I moduli con regolatore AMS1117 vogliono 5 V su VCC: qui si usa un modulo da 3,3 V.'],
  keypad: ["Tastiera ORIGINALE del 3310: gomma + lamina a cupole su millefori", "basetta ~45 x 60 mm (da misurare sul tappetino), piste incrociate sotto ogni cupola, 8 fili", "passiva (pull-up interni dell’ESP32)", "https://it.wikipedia.org/wiki/Tastiera_a_matrice", "Riuso dal telefono: gomma e lamina sono quelle vere, si rifanno solo le piste sotto (due pettini per tasto). Matrice 4x4 come KEYMAP in board.py: righe 1-4, colonne 5-8."],
  mic: ['NUOVO · Microfono I2S INMP441 (breakout)', 'scheda tonda ~14 mm (approssimato), capsula 4,72 x 3,76 x 1 mm', '1,8-3,3 V', 'https://invensense.tdk.com/products/digital/inmp441/', 'L/R a GND = canale sinistro. Pin dati I2S da fissare in board.py.'],
  amp: ['Amplificatore I2S MAX98357A + altoparlante', 'breakout ~17,8 x 19,3 mm (approssimato); altoparlante 28 mm 8 ohm', '2,5-5,5 V (qui 3,3 V)', 'https://www.analog.com/en/products/max98357a.html', 'Arriva dopo il piezo. Pin I2S da fissare in board.py.'],
  vibra: ['Vibrazione: motorino ORIGINALE del 3310 + NPN + diodo', 'motorino 10 x 2,7 mm; NPN TO-92 4,6 x 3,6 mm; R 1 kohm; 1N4148 DO-35', '3 V, ~70 mA (troppi per un GPIO: serve il transistor)', 'https://www.onsemi.com/pdf/datasheet/p2n2222a-d.pdf', 'GPIO 6 -> 1 kohm -> base. Emettitore a GND, collettore al meno del motore, diodo in antiparallelo (fascia verso il +).'],
  piezo: ['Cicalino ORIGINALE del 3310 (o piezo passivo 12 mm)', 'cicalino originale ~13 mm (da misurare); piezo 12 x 9,5 mm', '3-5 V', 'https://en.wikipedia.org/wiki/Piezoelectric_speaker', 'Riuso dal telefono per i bip. GPIO 47 (SPEAKER) fa i toni con il PWM. Per la voce serve comunque il MAX98357A.'],
  power: ['Tasto Power (6x6 mm)', '6 x 6 x 5 mm', '-', 'https://en.wikipedia.org/wiki/Push-button', 'In parallelo al BOOT del DevKit su GPIO 0: chiude a GND, sveglia dal deep sleep.'],
  alim: ["Ingresso alimentazione: USB-C oppure caricatore originale 3310", "breakout USB-C ~18 x 12 mm; presa jack DC ~14 x 9 mm; step-down/buck-boost ~22 x 17 mm (valori tipici)", "USB-C: 5 V sul pin 5V del DevKit (il suo regolatore fa i 3,3 V). Caricatore originale: dopo diodo, fusibile e regolatore, mai diretto", "https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html", "Niente batteria sul banco. USB-C: basta anche il cavo infilato nel DevKit (zero fili). Caricatore originale 3310: e un alimentatore non stabilizzato, a vuoto da molto piu dei 3,7 V scritti sopra: misuralo col multimetro, poi diodo Schottky + fusibile 500 mA + modulo buck-boost regolato a 5 V verso il pin 5V. Sotto carico (Wi-Fi) puo non bastare: per il banco e meglio la USB-C."],
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
  x: -78, z: 100, w: 43.6, d: 43.1, color: 0x2f5a2f, css: '#3b6b35', pz: -43.1 / 2 + 2.2,
  pins: ['RST', 'CE', 'DC', 'DIN', 'CLK', 'VCC', 'BL', 'GND'],
  draw: (c, w, d) => {
    c.fillStyle = '#c8ccc0'; c.fillRect(2, 7, w - 4, d - 11);
    c.fillStyle = '#9fb59a'; c.fillRect(7, 12, w - 14, d - 22);
    txt(c, 'AurI-3310', w / 2, d / 2 + 1, 4.2, '#1d2a1b'); txt(c, 'LCD originale 3310', w / 2, d / 2 + 7, 2, '#3a4a38', 0, 'center', false);
  },
});
// metallo e vetro sopra il display
{ const s = groups.lcd.children[0]; bx(40, 3.2, 32, 0xb8bcc2, 0, 2.6, 1.5, s); texPlane(34, 22, 16, (c, w, d) => { c.fillStyle = '#9fb59a'; c.fillRect(0, 0, w, d); txt(c, 'AurI-3310', w / 2, d / 2 - 2, 4.4, '#1d2a1b'); txt(c, 'LCD originale 3310', w / 2, d / 2 + 4, 2.2, '#2d3a2b', 0, 'center', false); }, 0, 5.82, 1.5, s); }

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
  // basetta millefori con sopra gomma e lamina ORIGINALI del 3310 (disposizione vera dei tasti)
  bx(50, 1.6, 64, 0x3d6b3a, cx, TABLE, cz, g);
  bx(44, 3.2, 58, 0x2a2e33, cx, TABLE + 1.6, cz, g);
  texPlane(44, 58, 10, (c, w, d) => {
    c.fillStyle = '#2a2e33'; c.fillRect(0, 0, w, d);
    const tasto = (x, z, tw, th, t, col) => { c.fillStyle = col || '#c9ced6'; c.beginPath(); c.ellipse(x, z, tw / 2, th / 2, 0, 0, 7); c.fill(); txt(c, t, x, z, 3.2, '#222'); };
    tasto(w / 2, 6, 16, 7, 'Navi', '#9fe06a');
    tasto(7, 7, 9, 6, 'C'); tasto(w - 7, 5, 8, 4.5, '^'); tasto(w - 7, 10, 8, 4.5, 'v');
    const L = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ['*', '0', '#']];
    for (let r = 0; r < 4; r++) for (let k = 0; k < 3; k++) tasto(8 + k * 14, 20 + r * 10, 11, 7.5, L[r][k]);
    txt(c, 'gomma + cupole 3310', w / 2, d - 2.5, 2, '#9aa', 0, 'center', false);
  }, cx, TABLE + 4.81, cz, g);
  bx(20, 0.4, 86, 0xb0b0b0, cx, TABLE, cz - 64 / 2 - 43 + 0.5, g);   // 8 fili in piattina
  const pz = cz - 64 / 2 - 86 + 1;
  bx(8 * P, 2.6, 2.6, 0x111, cx, TABLE, pz, g);
  for (let i = 0; i < 8; i++) bx(0.64, 9, 0.64, 0xd4b24a, cx + (i - 3.5) * P, TABLE + 2.6, pz - 1, g);
  texPlane(8 * P, 6, 30, (c, w) => { for (let i = 0; i < 8; i++) txt(c, ['R1', 'R2', 'R3', 'R4', 'C1', 'C2', 'C3', 'C4'][i], (i + 0.5) * P, 3, 1.2, '#fff', -Math.PI / 2); }, cx, TABLE + 0.45, pz + 5, g);
  return i => V(cx + (i - 3.5) * P, TABLE + 11.6, pz - 1);
})();


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

// ---------- fili ----------
const COL = { r: 0xe02020, k: 0x151515, y: 0xf0d020, b: 0x2060e0, g: 0x20a040, o: 0xf08020, w: 0xf0f0f0, p: 0x9040c0, pk: 0xf080b0, br: 0x8a5a2a, gr: 0x8a8a8a, c: 0x30c0d0 };
const conns = [];
const wires = [];
function curvaFilo(a, b, h) {
  const up = Math.max(a.y, b.y) + h;
  const pts = [a, onTop(a, 3), V(a.x + (b.x - a.x) * 0.25, up, a.z + (b.z - a.z) * 0.25), V(a.x + (b.x - a.x) * 0.75, up, a.z + (b.z - a.z) * 0.75), onTop(b, 3), b];
  return new THREE.CatmullRomCurve3(pts, false, 'centripetal');
}
// filo staccato: parte dal componente e penzola giu' fino al tavolo, accanto al foro di prima
function curvaPenzola(a, b) {
  const lato = V(a.x - b.x, 0, a.z - b.z).normalize().multiplyScalar(14);
  const pts = [b, onTop(b, 3), V(b.x + lato.x * 0.6, b.y + 10, b.z + lato.z * 0.6), V(b.x + lato.x, TABLE + 4, b.z + lato.z), V(b.x + lato.x * 1.4, TABLE + 0.8, b.z + lato.z * 1.4)];
  return new THREE.CatmullRomCurve3(pts, false, 'centripetal');
}
// estremita del filo: il connettore dupont nero
function puntali(mesh, pts) {
  for (const k of [...mesh.children]) mesh.remove(k);
  for (const p of pts) { const k = new THREE.Mesh(new THREE.BoxGeometry(2.5, 6, 2.5), mat(0x111)); k.position.copy(onTop(p, p.y > 0.5 ? -2 : 3)); mesh.add(k); }
}
function wire(a, b, color, h, meta) {
  const curve = curvaFilo(a, b, h);
  const m = new THREE.MeshStandardMaterial({ color, roughness: 0.5, transparent: true, opacity: 1 });
  const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, SEG, 0.7, MOB ? 6 : 8), m);
  mesh.userData.wire = conns.length;
  scene.add(mesh);
  puntali(mesh, [a, b]);
  const c = { ...meta, color, mesh, mid: curve.getPoint(0.5), a, b, h };
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
// piezo, tasto power
wire(espHole('GPIO47'), hole(2, 48, 'f'), COL.g, H(), { esp: lab('GPIO47'), comp: 'piezo', to: 'Piezo +', note: 'SPEAKER (toni PWM)' });
wire(hole(2, 51, 'j'), rail(2, -1, 51), COL.k, 2, { esp: '-', comp: 'piezo', to: 'Piezo −', note: 'a massa' });
wire(espHole('GPIO0'), hole(2, 30, 'c'), COL.o, H(), { esp: lab('GPIO0'), comp: 'power', to: 'Tasto Power', note: 'POWER_KEY, attivo basso (come BOOT)' });
wire(hole(2, 30, 'j'), rail(2, -1, 30), COL.k, 2, { esp: '-', comp: 'power', to: 'Tasto Power, altro lato', note: 'a massa' });
// ---------- alimentazione: niente batteria sul banco ----------
// Due varianti scelte nel pannello: USB-C (breakout -> pin 5V) o caricatore originale 3310
// (spinotto tondo -> presa DC -> diodo + fusibile -> buck-boost regolato a 5 V -> pin 5V).
const ALIM = { usb: grp('alim'), car: new THREE.Group() };
ALIM.car.userData.comp = 'alim'; groups.alim.add(ALIM.car);
const ALIM_USB = new THREE.Group(); ALIM_USB.userData.comp = 'alim'; groups.alim.add(ALIM_USB);
const usbPin = modulo('alim', {
  group: ALIM_USB, x: 100, z: 46, rot: -Math.PI / 2, w: 18, d: 12, color: 0x1a1a1a, css: '#1f2328', pz: 12 / 2 - 2,
  pins: ['GND', 'CC2', 'CC1', 'VBUS'],
  draw: (c, w) => { txt(c, 'USB-C 5 V', w / 2, 3.2, 1.8, '#ddd'); },
});
{ const s0 = ALIM_USB.children[0]; bx(9, 3.2, 7.4, 0xaeb2b8, 0, 2.6, -1.5, s0); }
// caricatore originale: presa DC, cavo con spinotto, modulo buck-boost
const presaDC = V(100, TABLE, 40), bb5 = V(122, TABLE, 70);
{ const g = ALIM.car;
  bx(14, 9, 9, 0x111111, presaDC.x, TABLE, presaDC.z, g); cyl(2.2, 1, 0x666, presaDC.x - 7.2, TABLE + 4.5, presaDC.z, g).rotation.z = Math.PI / 2;
  const cavo = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([V(presaDC.x - 9, TABLE + 4.5, presaDC.z), V(presaDC.x - 20, TABLE + 3, presaDC.z + 6), V(presaDC.x - 30, TABLE + 1, presaDC.z + 30), V(presaDC.x - 34, TABLE + 1, presaDC.z + 70)]), 40, 1.3, 8), mat(0x222222)); g.add(cavo);
  cyl(1.8, 10, 0x333, 0, 0, 0, g).position.set(presaDC.x - 12, TABLE + 4.5, presaDC.z); g.children[g.children.length - 1].rotation.z = Math.PI / 2;
  texPlane(14, 9, 20, (c, w, d) => { c.fillStyle = '#111'; c.fillRect(0, 0, w, d); txt(c, 'DC IN', w / 2, d / 2, 2.2, '#ddd'); }, presaDC.x, TABLE + 9.02, presaDC.z, g);
  bx(22, 1.6, 17, 0x1d3f8a, bb5.x, TABLE + 1, bb5.z, g); bx(7, 5, 7, 0x333, bb5.x - 3, TABLE + 2.6, bb5.z - 2, g); cyl(1.5, 2.5, 0x2a6ad4, bb5.x + 7, TABLE + 2.6, bb5.z - 5, g);
  texPlane(22, 17, 16, (c, w, d) => { c.fillStyle = '#1d3f8a'; c.fillRect(0, 0, w, d); txt(c, 'buck-boost 5 V', w / 2, d - 3, 1.9, '#ddd'); txt(c, 'IN+ IN−        OUT+ OUT−', w / 2, 2.5, 1.4, '#ffd28a', 0, 'center', false); }, bb5.x, TABLE + 2.62, bb5.z, g);
  // diodo Schottky + fusibile in serie sul +
  bx(4, 2, 2, 0x111, presaDC.x + 10, TABLE, presaDC.z + 14, g); bx(6, 3, 3, 0xd8c070, presaDC.x + 16, TABLE, presaDC.z + 20, g);
}
const bbIn = s => V(bb5.x - 9 + (s > 0 ? 0 : 3), TABLE + 2.7, bb5.z - 7), bbOut = s => V(bb5.x + 5 + (s > 0 ? 0 : 3), TABLE + 2.7, bb5.z - 7);
wire(usbPin('VBUS'), espHole('5V', 'i'), COL.r, 14, { esp: '5V (J1-21)', comp: 'alim', to: 'USB-C VBUS', note: '5 V nel regolatore del DevKit (equivale a infilare il cavo nel DevKit)', variante: 'usb' });
wire(usbPin('GND'), rail(1, -1, 60), COL.k, 9, { esp: 'GND', comp: 'alim', to: 'USB-C GND', note: 'massa comune', variante: 'usb' });
wire(V(presaDC.x + 7, TABLE + 4, presaDC.z + 2), bbIn(1), COL.r, 6, { esp: '-', comp: 'alim', to: 'presa DC + -> diodo -> fusibile -> IN+', note: 'tensione del caricatore originale', variante: 'car' });
wire(V(presaDC.x + 7, TABLE + 4, presaDC.z - 2), bbIn(-1), COL.k, 5, { esp: '-', comp: 'alim', to: 'presa DC − -> IN−', note: '', variante: 'car' });
wire(bbOut(1), espHole('5V', 'i'), COL.r, 16, { esp: '5V (J1-21)', comp: 'alim', to: 'buck-boost OUT+ (5,0 V)', note: 'regolato a 5 V col multimetro PRIMA di collegarlo', variante: 'car' });
wire(bbOut(-1), rail(1, -1, 60), COL.k, 10, { esp: 'GND', comp: 'alim', to: 'buck-boost OUT−', note: 'massa comune', variante: 'car' });
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
conns.push({ esp: 'GPIO3 / GPIO21', comp: 'devkit', to: 'BAT_ADC / CHG_DET', note: 'liberi: niente batteria sul banco', color: 0x666666, mid: espHole('GPIO3') });

// ---------- pannello ----------
const hex = c => '#' + c.toString(16).padStart(6, '0');
const tab = document.getElementById('conns');
// la tabella si ridisegna quando cambia l'alimentazione o un filo si guasta
let VARIANTE = 'usb';
const attivo = c => !c.variante || c.variante === VARIANTE;
function tabella() {
  tab.innerHTML = '<tr><td><b>ESP32</b></td><td><b>va a</b></td><td><b>note</b></td></tr>' +
    conns.map((c, i) => attivo(c) ? `<tr class="c${c.guasto ? ' gu' : ''}" data-i="${i}"><td><span class="sw" style="background:${hex(c.color)}"></span>${c.guasto && c.guasto.pin ? '<s>' + c.esp + '</s> ' + c.guasto.pin : c.esp}</td><td>${c.to}</td><td>${c.guasto ? (c.guasto.pin ? 'spostato' : 'STACCATO') : c.note}</td></tr>` : '').join('');
  tab.querySelectorAll('tr.c').forEach(r => r.classList.toggle('sel', +r.dataset.i === sel));
}
let sel = -1;
function select(i, fly = true) {
  sel = i;
  tab.querySelectorAll('tr.c').forEach(r => r.classList.toggle('sel', +r.dataset.i === i));
  wires.forEach(w => { const on = i < 0 || w.userData.wire === i; w.material.opacity = on ? 1 : 0.18; w.material.emissive.setHex(w.userData.wire === i ? 0x335522 : 0); });
  if (i >= 0 && fly) { flyTo(conns[i].mid, MOB ? 170 : 70); showInfo(conns[i].comp); }
  if (i >= 0 && MOB && window.UI) UI.apri('guasti', 'meta');
  aspetto();
  pannelloProva();
}
tab.addEventListener('click', e => { const r = e.target.closest('tr.c'); if (r) select(+r.dataset.i === sel ? -1 : +r.dataset.i); });
function showInfo(id) {
  const k = INFO[id], el = document.getElementById('info'); if (!k) return;
  el.style.display = 'block';
  el.innerHTML = `<b>${k[0]}</b><p>Misure: ${k[1]}</p><p>Tensione: ${k[2]}</p><p>${k[4]}</p><p><a href="${k[3]}" target="_blank" rel="noopener">datasheet / riferimento</a></p>`;
}
const NOMI = { devkit: 'DevKit', bb: 'Breadboard', lcd: 'Display', sd: 'microSD', keypad: 'Tastiera', mic: 'INMP441', amp: 'MAX98357A', vibra: 'Vibrazione', piezo: 'Piezo', power: 'Power', alim: 'Alimentazione' };
document.getElementById('toggles').innerHTML = Object.keys(NOMI).map(k => `<label><input type="checkbox" data-k="${k}" checked> ${NOMI[k]}</label>`).join('');
document.getElementById('toggles').addEventListener('change', e => {
  const k = e.target.dataset.k, on = e.target.checked; groups[k].visible = on;
  conns.forEach(c => { if (c.mesh && c.comp === k) c.mesh.visible = on && attivo(c); });
});
document.getElementById('apri').onclick = () => document.body.classList.toggle('closed');
if (innerWidth < 760) document.body.classList.add('closed');

// ---------- camera e picking ----------
let fly = null;
function flyTo(p, dist, dirForzata) {
  const dir = dirForzata ? dirForzata.clone().normalize() : camera.position.clone().sub(controls.target).normalize();
  fly = { t0: performance.now(), a: controls.target.clone(), b: p.clone(), ca: camera.position.clone(), cb: p.clone().addScaledVector(dir, dist) };
}
const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
let down = null;
renderer.domElement.addEventListener('pointerdown', e => { down = [e.clientX, e.clientY]; });
// filo piu' vicino al punto toccato, in pixel sullo schermo (i fili sono sottili: col dito si sbaglia)
function filoVicino(x, y, soglia) {
  const r = renderer.domElement.getBoundingClientRect(), v = new THREE.Vector3();
  let best = -1, bd = soglia;
  for (const w of wires) {
    if (!w.visible || w.material.opacity === 0.18) continue;
    const path = w.geometry.parameters && w.geometry.parameters.path; if (!path) continue;
    for (let k = 0; k <= 24; k++) {
      v.copy(path.getPoint(k / 24)).project(camera);
      if (v.z > 1) continue;
      const d = Math.hypot((v.x + 1) / 2 * r.width + r.left - x, (1 - v.y) / 2 * r.height + r.top - y);
      if (d < bd) { bd = d; best = w.userData.wire; }
    }
  }
  return best;
}
let ultimoTocco = { t: 0, x: 0, y: 0 };
renderer.domElement.addEventListener('pointerup', e => {
  if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > (MOB ? 12 : 6)) return;
  const r = renderer.domElement.getBoundingClientRect();
  ptr.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
  ray.setFromCamera(ptr, camera);
  // doppio tocco: inquadra il punto toccato
  const ora = performance.now();
  if (ora - ultimoTocco.t < 320 && Math.hypot(e.clientX - ultimoTocco.x, e.clientY - ultimoTocco.y) < 30) {
    const h2 = ray.intersectObjects(scene.children, true).find(h => h.object.visible);
    if (h2) flyTo(h2.point, Math.max(40, camera.position.distanceTo(controls.target) * 0.45));
    ultimoTocco.t = 0; return;
  }
  ultimoTocco = { t: ora, x: e.clientX, y: e.clientY };
  const hit = ray.intersectObjects([...wires, ...Object.values(groups), gSald, gFin], true).find(h => h.object.visible && h.object.material.opacity !== 0.18);
  let o = hit ? hit.object : null;
  while (o && o.userData.wire === undefined && !o.userData.comp && o.userData.sald === undefined && !o.userData.fin) o = o.parent;
  // niente filo preso in pieno: se ce n'e' uno vicino al dito (e non si e' toccato un pezzo preciso) vince il filo
  if (VISTA === 'banco' && (!o || (o.userData.wire === undefined && o.userData.sald === undefined && ['bb', 'devkit'].includes(o.userData.comp)))) {
    const f = filoVicino(e.clientX, e.clientY, MOB ? 26 : 10);
    if (f >= 0) { select(f); tab.querySelector(`tr[data-i="${f}"]`)?.scrollIntoView({ block: 'nearest' }); return; }
  }
  if (!o) { select(-1, false); return; }
  if (o.userData.fin) { infoFin(o.userData.fin); if (MOB) UI.apri('info', 'meta'); else if (innerWidth < 760) document.body.classList.remove('closed'); }
  else if (o.userData.sald !== undefined) { infoSald(o.userData.sald); if (MOB) UI.apri('info', 'meta'); else if (innerWidth < 760) document.body.classList.remove('closed'); }
  else if (o.userData.wire !== undefined) { select(o.userData.wire); tab.querySelector(`tr[data-i="${o.userData.wire}"]`)?.scrollIntoView({ block: 'nearest' }); }
  else { showInfo(o.userData.comp); if (MOB) UI.apri('info', 'meta'); else if (innerWidth < 760) document.body.classList.remove('closed'); }
});
addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
renderer.setAnimationLoop(() => {
  if (fly) {
    const k = Math.min(1, (performance.now() - fly.t0) / 700), s = k * k * (3 - 2 * k);
    controls.target.lerpVectors(fly.a, fly.b, s); camera.position.lerpVectors(fly.ca, fly.cb, s);
    if (k >= 1) fly = null;
  }
  controls.update();
  if (window.UI) UI.frame();
  renderer.render(scene, camera);
});
// ---------- prove guasti: stacca un filo o collegalo al pin sbagliato ----------
// Livelli: 0 = funziona, 1 = funziona a meta, 2 = non parte / schermo morto, 3 = rischio di danni.
const LIV = ['✅ funziona', '⚠️ funziona a metà', '❌ non parte', '🔥 rischio danni'];
const TASTO_FW = k => ({ '▲': 'up', '▼': 'down', C: 'c', Navi: 'navi' }[k] || k);   // nomi dei tasti nel firmware
const KEYMAP = [['1', '2', '3', '▲'], ['4', '5', '6', '▼'], ['7', '8', '9', 'C'], ['*', '0', '#', 'Navi']];
// a cosa serve ogni GPIO secondo board.py (sul banco senza batteria: 3 e 21 restano liberi)
const FUNZ = { 8: 'LCD_RES', 10: 'LCD_SCE', 9: 'LCD_DC', 11: 'LCD_SDIN', 12: 'LCD_SCLK', 7: 'BACKLIGHT', 15: 'KEY_ROWS[0]', 16: 'KEY_ROWS[1]', 17: 'KEY_ROWS[2]', 18: 'KEY_ROWS[3]', 4: 'KEY_COLS[0]', 5: 'KEY_COLS[1]', 13: 'KEY_COLS[2]', 14: 'KEY_COLS[3]', 6: 'VIBRA', 47: 'SPEAKER', 0: 'POWER_KEY', 41: 'SD_CS', 38: 'SD_MOSI', 39: 'SD_SCK', 40: 'SD_MISO' };
const INGRESSI = ['KEY_COLS', 'POWER_KEY', 'SD_MISO'];
const origPin = c => { const m = String(c.esp).match(/^(GPIO\d+|3V3|5V|GND|G)\b/); return m ? (m[1] === 'GND' ? 'G' : m[1]) : null; };
const tipoFilo = c => { const o = origPin(c); return !o ? null : o === '3V3' ? 'v33' : o === 'G' ? 'gnd' : o === '5V' ? 'v5' : 'sig'; };
const nGpio = p => /^GPIO\d+$/.test(p) ? +p.slice(4) : null;
const isRail = c => /^barra|^ponte/.test(c.to) || /^G \(J/.test(c.esp) || c.to === 'barra + davanti';
let DIODO = true;

// effetto di un filo staccato (o del suo segnale perso)
function effetto(c) {
  const n = c.note || '', t = c.to || '';
  const tasti = (i, riga) => (riga ? KEYMAP[i] : KEYMAP.map(r => r[i])).join(' ');
  let m;
  if (c.comp === 'alim') return { l: 2, t: 'Niente corrente al DevKit: tutto spento (a meno che il cavo USB sia infilato direttamente nel DevKit).', tel: 'spento' };
  if (t === 'barra + davanti') return { l: 2, t: 'Il 3,3 V non arriva alle breadboard: display, microSD, microfono e amplificatore restano senza corrente. Il DevKit si accende, lo schermo no.', tel: 'spento' };
  if (/ponte 3,3 V/.test(n)) return { l: 1, t: 'La breadboard dietro resta senza 3,3 V: microSD, microfono e amplificatore spenti.', toast: 'Nessuna microSD' };
  if (/ponte massa/.test(n) || /^G \(J/.test(c.esp)) return { l: 0, t: 'Da solo non cambia niente: la massa arriva anche dall’altro filo G (sono in parallelo apposta). Staccane due e una breadboard resta senza massa.' };
  if ((m = n.match(/LCD_(RES|SCE|DC|SDIN|SCLK)/))) return {
    RES: { l: 2, t: 'Il display non riceve il reset: non si inizializza e resta vuoto (a volte righe a caso).', tel: 'vuoto' },
    SCE: { l: 2, t: 'Chip select staccato: il display non sa che i dati sono per lui e resta fermo o vuoto.', tel: 'vuoto' },
    DC: { l: 2, t: 'Senza DC comandi e dati si confondono: pixel a caso e contrasto sbagliato.', tel: 'caos' },
    SDIN: { l: 2, t: 'Niente dati verso il display: schermo vuoto.', tel: 'vuoto' },
    SCLK: { l: 2, t: 'Niente clock: il display non riceve niente e resta vuoto.', tel: 'vuoto' } }[m[1]];
  if (/BACKLIGHT/.test(n)) return { l: 1, t: 'Niente retroilluminazione: lo schermo funziona ma al buio non si legge.', tel: 'buio' };
  if (/^Display (VCC|GND)/.test(t)) return { l: 2, t: 'Display senza alimentazione: spento, il resto del telefono va.', tel: 'spento' };
  if ((m = n.match(/KEY_ROWS\[(\d)\]/))) return { l: 1, t: `Riga ${+m[1] + 1} staccata: non rispondono i tasti ${tasti(+m[1], true)}.`, nota: `tasti ${tasti(+m[1], true)} non rispondono`, morti: KEYMAP[+m[1]].map(TASTO_FW) };
  if ((m = n.match(/KEY_COLS\[(\d)\]/))) return { l: 1, t: `Colonna ${+m[1] + 1} staccata: non rispondono i tasti ${tasti(+m[1], false)}.`, nota: `tasti ${tasti(+m[1], false)} non rispondono`, morti: KEYMAP.map(r => TASTO_FW(r[+m[1]])) };
  if (c.comp === 'vibra') return { l: 1, t: 'Niente vibrazione: il motorino non riceve corrente dal transistor.', nota: 'niente vibrazione' };
  if (c.comp === 'piezo') return { l: 1, t: 'Niente bip: i toni non arrivano al cicalino.', nota: 'muto (niente bip)' };
  if (c.comp === 'power') return { l: 1, t: 'Il tasto Power non fa niente: non si spegne e, una volta spento, non si riaccende col tasto.', nota: 'tasto Power morto' };
  if (c.comp === 'sd') return { l: 1, t: 'microSD non vista: AurI dice “Nessuna microSD” e il cervello locale non parte (resta quello di casa via Wi-Fi).', toast: 'Nessuna microSD' };
  if (/L\/R/.test(t)) return { l: 1, t: 'L/R flottante: il microfono può uscire sul canale sbagliato o a intermittenza.', nota: 'microfono a intermittenza' };
  if (c.comp === 'mic') return { l: 1, t: 'Microfono senza corrente: muto (quando i dati I2S saranno collegati).', nota: 'microfono muto' };
  if (c.comp === 'amp') return { l: 1, t: 'Altoparlante muto.', nota: 'altoparlante muto' };
  return { l: 0, t: 'Nessun effetto importante.' };
}

// collegato al pin sbagliato: valuta il nuovo pin con le regole dell'ESP32-S3
function valuta(c, pin) {
  const o = origPin(c), k = tipoFilo(c), g = nGpio(pin), base = effetto(c);
  const fz = (FUNZ[nGpio(o)] || '').replace(/\[.*/, '');
  const uscita = k === 'sig' && !INGRESSI.includes(fz);
  const nomeBoard = FUNZ[nGpio(o)] || '';
  if (pin === o) return { l: 0, t: 'È il pin giusto.' };
  if (k === 'v5') {
    if (pin === '3V3') return { l: 3, t: VARIANTE === 'car' ? 'Caricatore originale diretto sul 3V3: la sua tensione (a vuoto molto più dei 3,7 V scritti, e comunque oltre 3,6 V) entra nella linea a 3,3 V: brucia ESP32, display e microSD.' : '5 V direttamente sulla linea a 3,3 V: bruci il modulo ESP32 e tutto quello che è a 3,3 V.', tel: 'spento', fuoco: true };
    if (pin === 'G') return { l: 3, t: 'Alimentazione in corto verso massa: il caricatore o la porta USB si scaldano e si spengono.', tel: 'spento', fuoco: true };
    return { l: 3, t: `5 V su ${pin}: i pin dell’ESP32 reggono al massimo 3,6 V. Rischi di bruciarlo.`, tel: 'spento', fuoco: true };
  }
  if (k === 'v33') {
    const rail = c.to === 'barra + davanti';
    if (pin === '5V') return /MAX98357A/.test(c.to) ? { l: 0, t: 'Va bene: il MAX98357A accetta 2,5-5,5 V, anzi a 5 V suona più forte.' } : { l: 3, t: rail ? 'Tutta la barra rossa a 5 V: display, microSD e microfono sono da 3,3 V e si possono bruciare.' : 'Modulo da 3,3 V alimentato a 5 V: si può bruciare (il display e la microSD non lo reggono).', tel: 'spento', fuoco: true };
    if (pin === 'G') return rail ? { l: 2, t: 'La barra rossa finisce a massa: niente 3,3 V ai moduli, tutto spento (nessun corto, la barra non ha altre alimentazioni).', tel: 'spento' } : { ...base, t: 'Alimentazione del modulo collegata a massa: il modulo resta spento. ' + base.t };
    if (pin === 'RST') return { l: 2, t: 'Il 3,3 V sul pin RST tiene l’ESP32 acceso ma il modulo resta senza corrente. ' + base.t, tel: base.tel };
    return { l: Math.max(1, base.l), t: `Un GPIO non è un’alimentazione: dà pochi mA, il modulo si accende male o per niente. ${base.t}`, tel: base.tel, toast: base.toast, nota: base.nota };
  }
  if (k === 'gnd') {
    const rail = isRail(c);
    if (pin === '5V' || pin === '3V3') return rail ? { l: 3, t: `Corto diretto tra ${pin} e massa (la barra blu è collegata anche agli altri G): la USB si spegne o qualcosa si scalda.`, tel: 'spento', fuoco: true } : { ...base, l: Math.max(1, base.l), t: `La massa del modulo va a ${pin}: il modulo resta spento (VCC e GND alla stessa tensione). ` + base.t };
    if (g !== null) return { ...base, l: Math.max(1, base.l), t: 'Massa su un GPIO: il modulo non ha un riferimento stabile, funziona a caso. ' + base.t };
    return { l: 2, t: 'Massa sul pin RST: l’ESP32 resta in reset, non parte.', tel: 'spento' };
  }
  // segnale
  if (pin === '5V') return { l: 3, t: '5 V entrano nel GPIO del modulo e nel pin dell’ESP32: oltre i 3,6 V massimi, rischi di bruciarli.', tel: 'spento', fuoco: true };
  if (pin === '3V3') return uscita ? { l: 3, t: 'Uscita collegata al 3,3 V: quando l’ESP32 la porta a 0 fa un corto e il pin soffre (corrente massima). ' + base.t, tel: base.tel, fuoco: true } : { ...base, t: 'Ingresso fisso a 1: non vede mai nessun cambio. ' + base.t };
  if (pin === 'G') return uscita ? { l: 3, t: 'Uscita in corto verso massa: quando l’ESP32 la porta a 1 scorre la corrente massima. ' + base.t, tel: base.tel, fuoco: true } : { ...base, t: 'Ingresso fisso a 0: sembra sempre premuto/attivo. ' + base.t };
  if (pin === 'RST') return { l: 2, t: 'Il segnale finisce sul reset: l’ESP32 si riavvia di continuo o resta fermo.', tel: 'spento' };
  if (pin === 'TX' || pin === 'RX') return { ...base, l: Math.max(1, base.l), t: `${pin} è la seriale dei log (GPIO ${pin === 'TX' ? 43 : 44}): perdi i messaggi di debug e il firmware non trova il segnale dove lo cerca (${nomeBoard} in board.py). ` + base.t };
  if (g >= 33 && g <= 37) return { l: 2, t: `GPIO ${g} è della PSRAM ottale della N8R8: appena il modulo lo muove la memoria si corrompe, crash (Guru Meditation) e riavvii continui.`, tel: 'spento' };
  if (g === 45) return { l: 2, t: 'GPIO 45 decide all’accensione la tensione della flash: se il modulo lo tiene alto la scheda non parte.', tel: 'spento' };
  if (g === 0 || g === 46) return { l: 2, t: `GPIO ${g} è un pin di avvio: se il modulo lo tiene basso all’accensione l’ESP32 entra in modalità download e AurI non parte. Inoltre ${nomeBoard} non è più dove board.py lo cerca.`, tel: 'spento' };
  if (g === 19 || g === 20) return { ...base, l: Math.max(1, base.l), t: `GPIO ${g} è la USB nativa (D${g === 19 ? '−' : '+'}): perdi la USB/JTAG del chip. E il firmware cerca ${nomeBoard} altrove. ` + base.t };
  const altro = FUNZ[g];
  if (altro) return { l: Math.max(1, base.l), t: `GPIO ${g} è già usato da ${altro}: i due segnali si disturbano e nessuno dei due funziona bene. ${base.t}`, tel: base.tel || (/LCD/.test(altro) ? 'caos' : null), toast: base.toast, nota: base.nota };
  return { ...base, l: Math.max(1, base.l), t: `Il firmware cerca ${nomeBoard} su ${o} (board.py): sul GPIO ${g} non arriva niente. Per usarlo davvero cambia board.py: ${nomeBoard.replace(/\[.*/, '')} = ${g}. ` + base.t };
}

// stato di tutto il banco: ogni guasto attivo con la sua spiegazione
function guasti() {
  const out = [];
  for (const c of conns) if (attivo(c) && c.guasto) out.push({ c, e: c.guasto.pin ? valuta(c, c.guasto.pin) : effetto(c) });
  // due masse staccate: una breadboard resta senza massa
  const st = re => conns.some(c => c.guasto && !c.guasto.pin && re.test(c.esp + ' ' + c.note));
  const gj1 = st(/G \(J1/), gj3 = st(/G \(J3/), pm = st(/ponte massa/);
  if (gj1 && (gj3 || pm)) out.push({ e: { l: 2, t: 'Breadboard davanti senza massa: display e vibrazione spenti.', tel: 'spento' } });
  if (gj3 && (gj1 || pm)) out.push({ e: { l: 1, t: 'Breadboard dietro senza massa: microSD, microfono, amplificatore, cicalino e tasto Power non vanno.', toast: 'Nessuna microSD' } });
  if (!DIODO) out.push({ e: { l: 3, t: 'Senza il diodo sul motorino: ogni volta che si ferma, la bobina crea un picco di tensione (decine di volt) sul transistor. Col tempo il transistor si rompe e i disturbi possono riavviare l’ESP32.', fuoco: true, nota: 'vibra, ma rischia' } });
  return out;
}

// ---------- anteprima del display del telefono ----------
function statoTel() {
  const gs = guasti(), s = { lv: 0, schermo: 'ok', toast: '', note: [], fuoco: false, morti: [] };
  const pr = { spento: 4, vuoto: 3, caos: 3, buio: 1 };
  for (const { e } of gs) {
    s.lv = Math.max(s.lv, e.l);
    if (e.tel && (pr[e.tel] || 0) > (pr[s.schermo] || 0)) s.schermo = e.tel;
    if (e.toast) s.toast = e.toast;
    if (e.nota && !s.note.includes(e.nota)) s.note.push(e.nota);
    if (e.fuoco) s.fuoco = true;
    if (e.morti) for (const k of e.morti) if (!s.morti.includes(k)) s.morti.push(k);
  }
  return { ...s, gs };
}
// il display e' il SIMULATORE VERO di AurI (index.html#incassato) dentro un iframe: stesso telefono, stessi tasti.
// I guasti del banco gli arrivano come messaggio e agiscono davvero (schermo vuoto, tasti morti, toast...).
const telFrame = document.getElementById('telframe');
let ultimoGuasto = '';
function disegnaTel() {
  const s = statoTel();
  const msg = JSON.stringify({ schermo: s.schermo, morti: s.morti, toast: s.toast });
  if (msg !== ultimoGuasto) { ultimoGuasto = msg; try { telFrame.contentWindow.postMessage({ auriGuasto: JSON.parse(msg) }, '*'); } catch (e) {} }
  document.getElementById('telnota').textContent = s.schermo === 'spento' ? 'spento: nessuna immagine' : s.note.join(' · ');
  document.getElementById('telfuoco').style.display = s.fuoco ? 'block' : 'none';
  const st = document.getElementById('stato');
  st.textContent = (MOB ? '' : 'Telefono: ') + (MOB ? LIV[s.lv].split(' ')[0] + ' ' + ['ok', 'a metà', 'non va', 'pericolo'][s.lv] : LIV[s.lv]); st.className = 'l' + s.lv;
  document.getElementById('telbox').classList.toggle('allarme', s.lv > 0);
  return s;
}
telFrame.addEventListener('load', () => { ultimoGuasto = ''; setTimeout(disegnaTel, 1500); });
setInterval(disegnaTel, 500);

// ---------- aspetto dei fili guasti ----------
const tratt = (() => { const cv = document.createElement('canvas'); cv.width = 32; cv.height = 4; const g = cv.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, 18, 4); const t = new THREE.CanvasTexture(cv); t.wrapS = THREE.RepeatWrapping; t.repeat.set(14, 1); return t; })();
function ridisegna(c) {
  const m = c.mesh;
  let curva, pts;
  if (c.guasto && !c.guasto.pin) { curva = curvaPenzola(c.a, c.b); pts = [c.b, curva.getPoint(1)]; }
  else { const a = c.guasto ? espHole(c.guasto.pin) : c.a; curva = curvaFilo(a, c.b, c.h); pts = [a, c.b]; }
  m.geometry.dispose(); m.geometry = new THREE.TubeGeometry(curva, SEG, 0.7, MOB ? 6 : 8);
  puntali(m, pts);
  c.mid = curva.getPoint(0.5);
  m.material.alphaMap = c.guasto && !c.guasto.pin ? tratt : null; m.material.alphaTest = c.guasto && !c.guasto.pin ? 0.5 : 0; m.material.needsUpdate = true;
}
function aspetto() {
  for (const c of conns) {
    if (!c.mesh) continue;
    c.mesh.visible = attivo(c) && groups[c.comp].visible !== false;
    if (c.guasto) { const e = c.guasto.pin ? valuta(c, c.guasto.pin) : effetto(c); c.mesh.material.emissive.setHex(e.l >= 3 ? 0x991100 : e.l >= 2 ? 0x772200 : e.l >= 1 ? 0x553300 : 0x113311); }
  }
}

// ---------- pannello delle prove ----------
const PIN_ESP = [...new Set([...J1, ...J3].map(p => /^\d+$/.test(p) ? 'GPIO' + p : p))];
function pannelloProva() {
  const box = document.getElementById('prova');
  const c = sel >= 0 ? conns[sel] : null;
  let h = '';
  if (!c) h = '<p>Tocca un filo (nella scena o nella tabella), poi “Stacca” o scegli un pin sbagliato.</p>';
  else {
    const k = tipoFilo(c);
    h = `<p id="pTitolo"><b>${c.esp} → ${c.to}</b></p><p class="bt"><button id="pStacca">${c.guasto && !c.guasto.pin ? '🔗 Riattacca' : '✂️ Stacca'}</button><button id="pVai">🎯 Vai lì</button>`;
    if (k) h += ` <select id="pPin"><option value="">collega a…</option>${PIN_ESP.map(p => `<option${c.guasto && c.guasto.pin === p ? ' selected' : ''}>${p}</option>`).join('')}</select>`;
    h += '</p>';
    if (c.guasto) { const e = c.guasto.pin ? valuta(c, c.guasto.pin) : effetto(c); h += `<div class="eff l${e.l}"><b>Cosa succede: ${LIV[e.l]}</b><br>${e.t}</div>`; }
  }
  const gs = guasti();
  if (gs.length) h += '<p><b>Tutti i guasti attivi</b></p>' + gs.map(({ c: cc, e }) => `<div class="eff l${e.l}">${cc ? '<b>' + cc.to + '</b>: ' : ''}${e.t}</div>`).join('');
  h += `<p class="bt"><button id="pDiodo">${DIODO ? 'Togli il diodo del motorino' : 'Rimetti il diodo'}</button> <button id="pReset">Rimetti tutto a posto</button></p>`;
  box.innerHTML = h;
  const q = id => document.getElementById(id);
  if (q('pVai')) q('pVai').onclick = () => flyTo(c.mid, MOB ? 170 : 70);
  if (q('pStacca')) q('pStacca').onclick = () => { c.guasto = c.guasto && !c.guasto.pin ? null : { stacca: true }; ridisegna(c); aggiorna(); };
  if (q('pPin')) q('pPin').onchange = e => { const p = e.target.value; c.guasto = p && p !== origPin(c) ? { pin: p } : null; ridisegna(c); aggiorna(); };
  q('pDiodo').onclick = () => { DIODO = !DIODO; if (groups.vibra) groups.vibra.children.filter(m => m.userData.diodo).forEach(m => { m.visible = DIODO; }); aggiorna(); };
  q('pReset').onclick = () => { DIODO = true; groups.vibra.children.filter(m => m.userData.diodo).forEach(m => { m.visible = true; }); conns.forEach(cc => { if (cc.guasto) { cc.guasto = null; ridisegna(cc); } }); aggiorna(); };
}
function aggiorna() { tabella(); aspetto(); pannelloProva(); disegnaTel(); }

// ---------- alimentazione: USB-C o caricatore originale ----------
function variante(v) {
  VARIANTE = v;
  ALIM_USB.visible = v === 'usb'; ALIM.car.visible = v === 'car';
  conns.forEach(c => { if (c.variante && c.variante !== v && sel >= 0 && conns[sel] === c) sel = -1; });
  aggiorna();
}
document.querySelectorAll('input[name=alim]').forEach(r => r.addEventListener('change', e => variante(e.target.value)));

// ---------- saldature e alternative senza saldare ----------
const gSald = new THREE.Group(); scene.add(gSald);
const SALD = [
  { dove: micPin('VDD'), cosa: 'INMP441: strip da 6 pin (arriva sfusa)', alt: 'Comprarlo con i pin già saldati (molti venditori li offrono) e infilarlo sulla breadboard.', corto: 'pin già saldati', ok: true },
  { dove: ampPin('DIN'), cosa: 'MAX98357A: strip da 7 pin + morsettiera altoparlante', alt: 'Versione con header già saldato; altoparlante con fili a morsetto a vite o connettore JST precrimpato.', corto: 'pin già saldati', ok: true },
  { dove: lcdPin('DC'), cosa: 'Basetta del display: strip 8 pin', alt: 'Sul banco: modulo 5110 venduto con pin già saldati (3-4 €) al posto della basetta.', corto: 'modulo 5110 già saldato', ok: true },
  { dove: V(-78, TABLE + 8, 108), cosa: 'Display ORIGINALE 3310: contatti a molla verso la basetta', alt: 'Senza saldare solo con un adattatore con pogo-pin a molla (stampato in 3D) e mollette che premono il display: funziona ma è delicato. Onestamente: per il telefono finito qui una saldatura o una piccola scheda stampata è la scelta affidabile.', corto: 'pogo-pin + mollette (delicato)', ok: false },
  { dove: V(0, TABLE + 6, 182), cosa: 'Tastiera ORIGINALE: piste sotto le cupole + 8 fili', alt: 'Piste con nastro di rame adesivo o una basetta PCB stampata con le piazzole; i fili con clip o connettore. Senza stagno si fa, ma il nastro si stacca: per il telefono finito meglio una PCB.', corto: 'nastro di rame / PCB stampata', ok: false },
  { dove: V(62, TABLE + 3, 72), cosa: 'Motorino originale: 2 fili', alt: 'Due morsetti a leva Wago 221 o due clip a coccodrillo tra i fili del motorino e due jumper.', corto: 'Wago 221 / coccodrillo', ok: true },
  { dove: V((colX(48) + colX(51)) / 2, 10, holeZ(2, 'h')), cosa: 'Cicalino originale: 2 piazzole', alt: 'Test hook (mini uncini a molla) sulle piazzole, oppure un piezo nuovo con piedini da breadboard.', corto: 'test hook / piezo con piedini', ok: true },
  { dove: () => VARIANTE === 'usb' ? usbPin('VBUS') : V(bb5.x, TABLE + 4, bb5.z), cosa: 'Alimentazione: strip del breakout USB-C / pin del buck-boost', alt: 'USB-C: cavo infilato direttamente nel DevKit, zero fili. Caricatore originale: presa DC e buck-boost con morsetti a vite.', corto: 'cavo nel DevKit / morsetti a vite', ok: true },
  { dove: () => VARIANTE === 'usb' ? usbPin('GND') : V(presaDC.x, TABLE + 10, presaDC.z), cosa: 'Caricatore originale: fili alla presa DC (con diodo e fusibile)', alt: 'Presa DC femmina con morsetti a vite e diodo/fusibile su morsetti Wago: zero stagno.', corto: 'presa DC a vite + Wago', ok: true, solo: 'car' },
];
let SENZA = false;
const etichetta = (t, col) => {
  const cv = document.createElement('canvas'); cv.width = 512; cv.height = 96; const g = cv.getContext('2d');
  g.fillStyle = 'rgba(15,17,21,.85)'; g.beginPath(); g.roundRect(4, 8, 504, 80, 18); g.fill(); g.strokeStyle = col; g.lineWidth = 5; g.stroke();
  g.fillStyle = col; g.font = '600 34px system-ui, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(t.length > 30 ? t.slice(0, 29) + '…' : t, 256, 50);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), depthTest: false, transparent: true })); s.scale.set(32, 6, 1); s.renderOrder = 10; return s;
};
function costruisciSald() {
  for (const o of [...gSald.children]) gSald.remove(o);
  SALD.forEach((d, i) => {
    if (d.solo && d.solo !== VARIANTE) return;
    const p = typeof d.dove === 'function' ? d.dove() : d.dove;
    const col = SENZA ? (d.ok ? '#9fe06a' : '#ffbe3c') : '#ff8a1e';
    const anello = new THREE.Mesh(new THREE.TorusGeometry(4.2, 0.9, 10, 32), new THREE.MeshBasicMaterial({ color: col, depthTest: false, transparent: true }));
    anello.rotation.x = -Math.PI / 2; anello.position.copy(p).add(V(0, 1.5, 0)); anello.renderOrder = 9; anello.userData.sald = i;
    const lab = etichetta(SENZA ? '✓ ' + d.corto : '◉ saldare: ' + d.cosa.split(':')[0], col); lab.position.copy(p).add(V(0, 12, 0)); lab.userData.sald = i;
    gSald.add(anello, lab);
  });
  const vis = SALD.filter(d => !d.solo || d.solo === VARIANTE), dure = vis.filter(d => !d.ok).length;
  document.getElementById('saldsum').innerHTML = `<b>Saldature necessarie: ${vis.length}</b> → con le alternative: <b>0 obbligatorie</b>${dure ? `, ma ${dure} restano consigliate per il telefono finito (display e tastiera originali: senza stagno funzionano ma si staccano facilmente)` : ''}.`;
  document.getElementById('saldlista').innerHTML = vis.map(d => `<div class="eff ${d.ok ? 'l0' : 'l1'}"><b>${d.cosa}</b><br>Senza saldare: ${d.alt}</div>`).join('');
}
function infoSald(i) {
  const d = SALD[i], el = document.getElementById('info'); el.style.display = 'block';
  el.innerHTML = `<b>Saldatura: ${d.cosa}</b><p>Senza saldare: ${d.alt}</p><p>${d.ok ? '✅ Alternativa affidabile per il banco.' : '⚠️ Alternativa possibile ma delicata: per il telefono finito meglio saldare.'}</p>`;
}
document.getElementById('saldOn').addEventListener('change', e => { gSald.visible = e.target.checked; });
document.getElementById('senzaSald').addEventListener('change', e => { SENZA = e.target.checked; costruisciSald(); });
document.querySelectorAll('input[name=alim]').forEach(r => r.addEventListener('change', () => costruisciSald()));

// diodo: segna le sue parti per poterlo togliere nelle prove
groups.vibra.children.forEach(m => { if (m.material && (m.material.color?.getHex() === 0xe07a30 || (m.geometry?.parameters?.radiusTop === 0.97))) m.userData.diodo = true; });

costruisciSald();
variante('usb');

// ---------- vista "Telefono finito": cover del 3310 esplosa con la scheda su misura ----------
// Misure: cover ~113 x 48 x 22 mm; scheda su misura ~44 x 100 mm (SAGOMA DA MISURARE sul telefono smontato).
// Il telefono e' disteso a faccia in su: display verso -z (in alto), USB-C verso +z (in basso).
const gFin = new THREE.Group(); gFin.visible = false; scene.add(gFin);
const FIN_INFO = {
  retro: ['ORIGINALE · Cover posteriore', '~113 x 48 mm, alta ~12 mm', 'Si riusa quella vera: dentro ci stanno batteria e scheda. Lo sportello resta come prima.'],
  bat: ['ORIGINALE · Batteria BLC-2 (facoltativa)', '~56 x 40 x 5 mm (dalla scansione), 3,7 V', 'Si può togliere: il telefono va anche col caricatore originale o con la USB-C. Se c’è, appoggia sui contatti a molla come prima.'],
  telaio: ['ORIGINALE · Telaio posteriore', '~47 x 113 mm (dalla scansione)', 'Si riusa com’è: tiene la scheda e fa da vano batteria.'],
  ui: ['ORIGINALE · Telaio bianco con il display', '~45 x 107 mm (dalla scansione)', 'Si riusa: tiene il display e l’altoparlante; i fori lasciano passare i tasti.'],
  pcb: ['NUOVO · Scheda AurI (PCB)', '46 x 109 x 1 mm: sagoma presa dalla scansione a 600 dpi della scheda originale', 'Si disegna una volta e la si fa stampare E assemblare (JLCPCB/PCBWay): arriva con tutti i chip gia saldati, a mano non si salda niente.'],
  esp: ['NUOVO · Modulo ESP32-S3-WROOM-1 N8R8', '18 x 25,5 x 3,1 mm', 'Montato dalla fabbrica (assemblaggio PCB). L’antenna va lasciata sul bordo, senza rame sotto, lontana dalle parti metalliche della cover.'],
  sd: ['NUOVO · Slot microSD a molla', '~14 x 15 x 1,8 mm', 'Montato dalla fabbrica. Si raggiunge togliendo la batteria, come la SIM.'],
  mic: ['Microfono INMP441 (solo il chip, senza basetta)', '4,72 x 3,76 x 1 mm', 'Montato dalla fabbrica vicino al foro del microfono originale, in basso.'],
  amp: ['NUOVO · MAX98357A (chip) + altoparlantino 15 mm', 'chip 3 x 3 mm; altoparlante ~15 mm', 'Chip montato dalla fabbrica; l’altoparlante si appoggia su piazzole a molla, dove stava l’auricolare originale.'],
  usb: ['NUOVO · USB-C al posto della presa del caricatore', 'presa ~9 x 3,2 x 7,4 mm', 'In basso, dove c’era la presa tonda: va allargato il foro della cover (lima) o stampato un adattatore.'],
  lcd: ['ORIGINALE · Display 3310', 'vetro ~38 x 34 mm (da misurare)', 'Non si salda: i suoi contatti a molla premono sulle 8 piazzole dorate della scheda, tenuti dal telaio come nell’originale.'],
  pad: ['NUOVO · Piazzole del display', '8 piazzole dorate in fila', 'Stampate sulla scheda con la stessa posizione dell’originale (da copiare dalla scheda vecchia).'],
  piste: ['NUOVO · Piste dei tasti', 'stesse posizioni della scheda originale (copiate dalla scansione)', 'Stampate sulla scheda (dorate, ENIG): la cupola che si schiaccia chiude il contatto. Zero saldature.'],
  cupole: ['ORIGINALE · Lamina a cupole', 'foglio adesivo con le cupole metalliche', 'Si stacca dalla scheda vecchia e si incolla sulla nuova, centrando ogni cupola sulle piste.'],
  gomma: ['ORIGINALE · Tastiera in gomma', 'tappetino dei tasti', 'Si appoggia sopra la lamina, come prima.'],
  vibra: ['ORIGINALE · Motorino', '~10 x 2,7 mm', 'Su piazzole a molla della scheda (o due fili corti). Pilotato da transistor + diodo stampati sulla scheda.'],
  buzz: ['ORIGINALE · Cicalino', '~13 mm', 'Su piazzole a molla, nella stessa posizione dell’originale.'],
  fronte: ['ORIGINALE · Cover frontale', '~113 x 48 mm', 'Si chiude sopra tutto come prima: nessuna modifica, tranne la presa USB-C in basso.'],
};
const FIN = {};   // id -> gruppo dello strato (per esplodere)
function strato(id, baseY, passo) { const g = new THREE.Group(); g.userData.fin = id; g.userData.base = baseY; g.userData.passo = passo; gFin.add(g); FIN[id] = g; g.position.y = baseY; return g; }
const finMat = (c, o) => mat(c, o);
// Strati veri: texture dalle scansioni del telefono smontato (tools/prepara_texture_finito.py -> tex/finito/).
// Ogni strato = faccia sopra + faccia sotto + "fette" scure in mezzo che fanno da bordo (spessore vero).
// Telefono a faccia in su: display verso -z, USB-C verso +z. Misure in mm prese dalle scansioni a 600 dpi.
const TEXL = new THREE.TextureLoader();
const texF = n => { const t = TEXL.load('tex/finito/' + n + '.webp'); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = Math.min(8, ANISO); return t; };
function faccia(g, tex, w, l, y, sotto, o = {}) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, l), new THREE.MeshStandardMaterial({ map: tex, alphaTest: 0.5, roughness: o.r ?? 0.55, metalness: o.m ?? 0, color: o.c ?? 0xffffff }));
  if (sotto) m.rotation.set(Math.PI / 2, 0, Math.PI); else m.rotation.x = -Math.PI / 2;
  m.position.y = y; g.add(m); return m;
}
function lastra(id, base, passo, sopra, sotto, w, l, t, o = {}) {
  const g = strato(id, base, passo), ts = texF(sopra), tb = texF(sotto);
  const pz = new THREE.Group(); pz.position.z = o.z || 0; g.add(pz);
  faccia(pz, ts, o.ws || w, o.ls || l, t, false, o);
  faccia(pz, tb, w, l, 0, true, o);
  const n = MOB ? 3 : Math.max(3, Math.round(t / 0.3));
  for (let i = 1; i < n; i++) faccia(pz, ts, o.ws || w, o.ls || l, t * i / n, false, { ...o, c: 0x3c3c3c, r: 0.9, m: 0 });
  return g;
}
lastra('retro', 0, 0, 'retro_dentro', 'retro_fuori', 50.6, 113, 1.8, { ws: 50.6, ls: 110.7, r: 0.45 });
const gBat = lastra('bat', 1.8, 16, 'bat_dietro', 'bat_etichetta', 40.5, 55.8, 5, { ws: 41.5, ls: 59, z: 10, r: 0.5, m: 0.2 });
lastra('telaio', 4.2, 30, 'telaio_sopra', 'telaio_sotto', 42, 113, 3, { ws: 47.6, ls: 113 });
{ // scheda: sopra il lato tasti (identico all'originale), sotto la NUOVA scheda AurI con i componenti veri
  const g = lastra('pcb', 7.6, 46, 'pcb_tasti', 'pcb_auri', 46, 109.2, 1, { ws: 45.5, ls: 109.7, r: 0.35, m: 0.25 });
  const X = x => -(x - 23), Z = y => y - 54.6;     // mm della serigrafia (lato componenti, visto da sotto) -> mondo
  const metallo = mat(0xc9ced4, { metalness: 0.85, roughness: 0.3 }), nero = mat(0x151515, { roughness: 0.5 });
  const sotto = (m, y) => { m.rotation.set(Math.PI / 2, 0, Math.PI); m.position.y = y; return m; };
  // ESP32-S3-WROOM-1: basetta, schermatura metallica con la scritta, antenna PCB verso il bordo alto
  bx(18, 0.8, 25.5, 0x1d4d2e, X(23.5), -0.8, Z(30), g);
  bx(15.8, 2.3, 17.6, metallo, X(23.5), -3.1, Z(32.5), g);
  sotto(texPlane(15.8, 17.6, 24, (c, w, d) => { c.fillStyle = '#c9ced4'; c.fillRect(0, 0, w, d); txt(c, 'ESP32-S3-WROOM-1', w / 2, d / 2 - 2, 1.5, '#333'); txt(c, 'N8R8', w / 2, d / 2 + 1, 1.4, '#333'); txt(c, 'AurI-3310', w / 2, d / 2 + 4, 1.1, '#555', 0, 'center', false); }, X(23.5), 0, Z(32.5), g), -3.12);
  sotto(texPlane(18, 6, 24, (c, w, d) => { c.fillStyle = '#1d4d2e'; c.fillRect(0, 0, w, d); c.strokeStyle = '#c8a24a'; c.lineWidth = 0.5; c.beginPath(); let x = 2; c.moveTo(x, 1); for (let i = 0; i < 6; i++) { c.lineTo(x, 5); x += 1.2; c.lineTo(x, 5); c.lineTo(x, 1); x += 1.2; c.lineTo(x, 1); } c.stroke(); }, X(23.5), 0, Z(20.2), g), -0.82);
  // slot microSD a molla: lamiera con nervature
  bx(14, 1.8, 15, metallo, X(14), -1.8, Z(61), g);
  for (let i = 0; i < 4; i++) bx(10, 0.15, 0.6, mat(0xa8adb3, { metalness: 0.9, roughness: 0.35 }), X(14), -1.95, Z(61) - 4 + i * 2.4, g);
  // chip: MAX98357A (QFN 3x3), LDO, microfono MEMS (coperchio metallico col foro)
  bx(3, 0.8, 3, nero, X(33), -0.8, Z(58), g);
  bx(3, 1.1, 1.6, nero, X(33), -1.1, Z(66), g);
  bx(4.7, 1, 3.8, metallo, X(33), -1, Z(98), g); cyl(0.4, 0.06, 0x111, X(33), -1.06, Z(98), g, 12);
  // USB-C sul bordo basso (dove c'era la presa del caricatore)
  const usb = new THREE.Mesh(new THREE.CapsuleGeometry(1.6, 5.7, 4, 12), metallo); usb.rotation.z = Math.PI / 2; usb.scale.set(1, 1, 2.3); usb.position.set(X(23.5), -1.7, Z(106.5)); g.add(usb);
  // cicalino e motorino a moneta ORIGINALI
  cyl(6.5, 3.2, nero, X(34), -3.2, Z(76), g, 36); cyl(1.2, 0.06, 0x333, X(34), -3.26, Z(76), g, 16);
  cyl(5, 2.7, metallo, X(12), -2.7, Z(84), g, 36);
  // passivi 0402/0603 vicino ai chip
  const cap = mat(0x8a6a44), res = mat(0x111111);
  for (const [x, y] of [[28, 44], [30, 44], [32, 44], [36, 60], [36, 62], [30, 66], [36, 66], [29, 98], [37, 98], [19, 100], [28, 100], [10, 46], [12, 46], [36, 52], [14, 52]]) bx(1, 0.5, 0.5, (x + y) % 3 ? cap : res, X(x), -0.5, Z(y), g);
  const tag = (id, x, y, z) => { const o = new THREE.Object3D(); o.position.set(x, y, z); o.userData.fin = id; g.add(o); return o; };
  tag('esp', X(23.5), -4, Z(30)); tag('sd', X(14), -2, Z(61)); tag('amp', X(33), -1, Z(58)); tag('mic', X(33), -1, Z(98)); tag('usb', X(23.5), -2, Z(106)); tag('buzz', X(34), -3, Z(76)); tag('vibra', X(12), -3, Z(84)); tag('pad', 0, 1.2, -45); tag('piste', 0, 1.2, 25);
}
{ // lamina a cupole ORIGINALE: foglio trasparente con una cupola d'acciaio su ogni piazzola vera
  const g = strato('cupole', 8.7, 58);
  const f = new THREE.Mesh(new THREE.PlaneGeometry(40, 52), new THREE.MeshStandardMaterial({ color: 0xe8eef5, transparent: true, opacity: 0.28, roughness: 0.2 })); f.rotation.x = -Math.PI / 2; f.position.set(0, 0.05, 27); g.add(f);
  fetch('tex/finito/pezzi.json').then(r => r.json()).then(j => {
    for (const [x, z, r] of j.tasti) { const m = new THREE.Mesh(new THREE.SphereGeometry(Math.min(r, 3.6) * 0.8, 20, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat(0xdfe5ea, { metalness: 0.9, roughness: 0.18 })); m.scale.y = 0.3; m.position.set(x, 0.05, z); g.add(m); }
  }).catch(() => {});
}
{ // telaio bianco con il display ORIGINALE (vetro con la Home di AurI accesa)
  const g = lastra('ui', 8.9, 70, 'telaio_ui_sopra', 'telaio_ui_sotto', 46.1, 114.8, 2.6, { ws: 45, ls: 106.6, r: 0.6 });
  FIN.lcd = g;
  const v = texPlane(30, 18, 12, (c, w, d) => { c.fillStyle = '#a9c29a'; c.fillRect(0, 0, w, d); txt(c, 'AurI', w / 2, 3, 2.6, '#1d2a1b'); txt(c, '12:00', w / 2, d / 2 + 0.5, 6.5, '#1d2a1b'); txt(c, 'Menu', w / 2, d - 2.6, 2.4, '#1d2a1b'); }, 0, 2.63, -21, g);
  v.material.emissive = new THREE.Color(0x2a3624);
}
lastra('gomma', 11.6, 84, 'gomma_sopra', 'gomma_sotto', 47.6, 50.8, 2.4, { ws: 40.9, ls: 42.8, z: 30, r: 0.35, m: 0.35 });
lastra('fronte', 14.2, 100, 'fronte_fuori', 'fronte_dentro', 49, 110.8, 2, { ws: 49.5, ls: 111.9, r: 0.3 });
// luce da sotto: la vista Retro (e la scheda vista da sotto) non resta al buio
{ const l = new THREE.DirectionalLight(0xffffff, 1.1); l.position.set(60, -200, 80); gFin.add(l); gFin.add(new THREE.AmbientLight(0xffffff, 0.35)); }
// batteria: si puo' togliere (il telefono va anche col caricatore originale o la USB-C)
{
  const lab = document.getElementById('eslab');
  if (lab) {
    const b = document.createElement('label'); b.id = 'batlab'; b.innerHTML = '<input type="checkbox" id="batOn" checked> batteria'; lab.after(b);
    b.querySelector('input').addEventListener('change', e => { gBat.visible = e.target.checked; if (P3) P3.setVisible('Batteria', e.target.checked); });
  }
}
// etichette cliccabili sopra ogni pezzo
const LAB_FIN = [['retro', 0, 2, 64], ['bat', -30, 4, 0], ['telaio', 30, 2, -40], ['pcb', 30, 1, 40], ['esp', 22, -4, -24], ['sd', -24, -2, 6], ['amp', -26, -1, 2], ['mic', -26, -1, 44], ['usb', 0, -4, 62], ['buzz', -28, -3, 22], ['vibra', 26, -3, 30], ['pad', 26, 2, -50], ['piste', -28, 2, 30], ['cupole', 28, 1, 26], ['ui', -30, 3, -10], ['lcd', 28, 4, -26], ['gomma', -30, 3, 0], ['fronte', 0, 3, -64]];
const finLabels = [];
for (const [id, x, y, z] of LAB_FIN) {
  const par = ['esp', 'sd', 'amp', 'mic', 'usb', 'buzz', 'vibra', 'pad', 'piste'].includes(id) ? FIN.pcb : FIN[id];
  if (!par) continue;
  const l = etichetta(FIN_INFO[id][0].replace(/ \(.*/g, ''), FIN_INFO[id][0].startsWith('NUOVO') ? '#9fe06a' : '#ffd28a'); l.scale.set(26, 4.9, 1); l.position.set(x, y + 4, z); l.userData.fin = id; par.add(l); finLabels.push(l);
}
function esplodi(e) {
  if (P3) P3.setExplode(e);
  for (const g of Object.values(FIN)) g.position.y = g.userData.base + e * g.userData.passo;
  // telefono chiuso: le etichette dei pezzi nascosti dentro confondono, si vedono solo aprendolo
  if (typeof finLabels !== 'undefined') for (const l of finLabels) l.visible = e > 0.15 || ['fronte', 'retro'].includes(l.userData.fin);
}
function infoFin(id) {
  const k = FIN_INFO[id], el = document.getElementById('info'); if (!k) return; el.style.display = 'block';
  el.innerHTML = `<b>${k[0]}</b><p>Misure: ${k[1]}</p><p>Come si monta: ${k[2]}</p>`;
}
let VISTA = 'banco';
// ---- Telefono finito = lo stesso telefono 3D curato del simulatore (phone3d.js), con la scheda NUOVA di AurI.
// Display: i pixel veri del telefono acceso nell'iframe, ridisegnati nitidi (84x48 -> 504x288).
let P3 = null, p3Load = null;
// tutti i pezzi visibili (dopo "Scheda AurI" che mostra solo la scheda); la batteria segue la casella
const tutti = () => { if (!P3) return; for (const n of ['Coperchio', 'Batteria', 'Chassis', 'Viti Torx', 'Display', 'Tastierino', 'Cover frontale']) P3.setVisible(n, true); P3.setVisible('Batteria', document.getElementById('batOn') ? document.getElementById('batOn').checked : true); };
const finEl = document.createElement('div'); finEl.id = 'fin3d'; document.body.appendChild(finEl);
const lcdCv = document.createElement('canvas'); lcdCv.width = 84 * 6; lcdCv.height = 48 * 6;
const lcdG = lcdCv.getContext('2d');
function lcdAggiorna() {
  let t = null, lit = true;
  try { const w = document.getElementById('telframe').contentWindow; t = w.auriPixel(); lit = w.auriAcceso(); } catch (e) {}
  const bg = lit ? [157, 200, 106] : [126, 140, 110], fg = lit ? [28, 43, 20] : [34, 42, 30];
  const gr = lcdG.createRadialGradient(252, 160, 30, 252, 160, 330);
  gr.addColorStop(0, `rgb(${bg.map(c => Math.min(255, c + 12))})`); gr.addColorStop(1, `rgb(${bg.map(c => c - 18)})`);
  lcdG.fillStyle = gr; lcdG.fillRect(0, 0, 504, 288);
  if (!t) return;
  const sh = document.getElementById('telframe').contentWindow.auriGuasto?.schermo;
  if (sh === 'spento') { lcdG.fillStyle = '#1b2016'; lcdG.fillRect(0, 0, 504, 288); return; }
  if (sh === 'vuoto') return;
  lcdG.fillStyle = 'rgba(0,0,0,0.12)'; lcdG.beginPath();
  for (let i = 0; i < 84 * 48; i++) if (t[i] || (sh === 'caos' && Math.random() < 0.33)) lcdG.rect((i % 84) * 6 + 1.6, ((i / 84) | 0) * 6 + 1.6, 5.2, 5.2);
  lcdG.fill();
  lcdG.fillStyle = `rgb(${fg})`; lcdG.beginPath();
  for (let i = 0; i < 84 * 48; i++) if (t[i] || (sh === 'caos' && Math.random() < 0.33)) lcdG.rect((i % 84) * 6, ((i / 84) | 0) * 6, 5.2, 5.2);
  lcdG.fill();
}
const FIN_NOME = { 'Coperchio': 'retro', 'Batteria': 'bat', 'Chassis': 'telaio', 'Scheda (PCB)': 'pcb', 'Display': 'lcd', 'Tastierino': 'gomma', 'Cover frontale': 'fronte', 'Viti Torx': 'viti' };
FIN_INFO.viti = ['ORIGINALE · Viti Torx T6', '6 viti lunghe ~7 mm', 'Le stesse di prima: tengono la scheda nuova sullo chassis, negli stessi fori.'];
FIN_INFO.ldo = ['NUOVO · Regolatore 3,3 V (LDO)', 'SOT-23-5, 2,9 x 1,6 mm', 'Montato dalla fabbrica: dai 5 V della USB-C (o dal caricatore) fa i 3,3 V per ESP32, display e microSD.'];
async function finito3d(on) {
  finEl.style.display = on ? 'block' : 'none';
  renderer.domElement.style.visibility = on ? 'hidden' : 'visible';
  if (!on) { if (P3) P3.show(false); return; }
  tutti();
  if (!p3Load) p3Load = import('./phone3d.js').then(({ createPhone3D }) => {
    const tw = () => document.getElementById('telframe').contentWindow;
    P3 = createPhone3D(finEl, {
      press: k => { try { tw().auriPress(k); } catch (e) {} }, release: k => { try { tw().auriRelease(k); } catch (e) {} },
      lcdCanvas: lcdCv, noMap: true, auri: true,
      onPick: (nome, info) => { const id = info || FIN_NOME[nome]; if (id) { infoFin(id); if (window.UI) UI.apri('info'); } },
    });
    setInterval(() => { if (VISTA !== 'banco') lcdAggiorna(); }, 80);
    lcdAggiorna();
    return P3;
  });
  await p3Load;
  P3.show(true);
  P3.setExplode(+document.getElementById('esplodi').value);
  P3.setVisible('Batteria', document.getElementById('batOn') ? document.getElementById('batOn').checked : true);
}
function vista(v) {
  VISTA = v;
  const banco = v === 'banco';
  for (const [k, g] of Object.entries(groups)) g.visible = banco && (document.querySelector(`#toggles input[data-k="${k}"]`)?.checked ?? true);
  gSald.visible = banco && document.getElementById('saldOn').checked;
  if (banco) { variante(VARIANTE); } else conns.forEach(c => { if (c.mesh) c.mesh.visible = false; });
  gFin.visible = false;
  finito3d(!banco);
  document.querySelectorAll('#viste button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  document.body.classList.toggle('finito', !banco);
  controls.maxPolarAngle = Math.PI * 0.49;
  if (banco) flyTo(V(0, 0, 0), MOB ? 560 : 370); else esplodi(+document.getElementById('esplodi').value);
  if (window.UI) UI.chips();
}
document.querySelectorAll('#viste button').forEach(b => b.addEventListener('click', () => vista(b.dataset.v)));
document.getElementById('esplodi').addEventListener('input', e => esplodi(+e.target.value));
esplodi(0);

// ---------- interfaccia per il telefono: foglio dal basso, bolla del telefono, chip di inquadratura ----------
const UI = (() => {
  const aside = document.querySelector('aside'), corpo = document.getElementById('corpo');
  const tabsEl = document.getElementById('tabs'), telbox = document.getElementById('telbox');
  let tabAttiva = 'coll', posSheet = 'chiuso';
  const altezze = () => ({ chiuso: 66 + safeB(), meta: Math.round(innerHeight * 0.52), tutto: innerHeight - 56 - safeT() });
  const cssPx = v => { const d = document.createElement('div'); d.style.cssText = 'position:fixed;visibility:hidden;height:' + v; document.body.appendChild(d); const h = d.offsetHeight; d.remove(); return h; };
  const safeB = () => cssPx('env(safe-area-inset-bottom, 0px)'), safeT = () => cssPx('env(safe-area-inset-top, 0px)');
  // la scena 3D si centra nello spazio libero sopra il foglio (non dietro)
  function offset(h) {
    if (!MOB) return;
    camera.setViewOffset(innerWidth, innerHeight, 0, Math.round((h - 40) / 2), innerWidth, innerHeight);
    camera.updateProjectionMatrix();
  }
  function altezza(h, anima = true) {
    aside.classList.toggle('trascino', !anima);
    aside.style.setProperty('--sh', h + 'px');
    offset(h);
  }
  function scheda(t) {
    tabAttiva = t;
    corpo.querySelectorAll('section').forEach(sx => sx.classList.toggle('on', sx.dataset.t === t));
    tabsEl.querySelectorAll('button').forEach(b => b.classList.toggle('on', b.dataset.t === t));
    corpo.scrollTop = 0;
    if (t === 'info' && !document.getElementById('info').innerHTML) showInfo('devkit');
  }
  function apri(t, pos) {
    if (!MOB) { document.body.classList.remove('closed'); return; }
    if (t) scheda(t);
    posSheet = pos || (posSheet === 'chiuso' ? 'meta' : posSheet);
    altezza(altezze()[posSheet]);
  }
  function chiudi() { if (!MOB) return; posSheet = 'chiuso'; altezza(altezze().chiuso); }

  if (MOB) {
    document.body.classList.remove('closed');
    scheda('coll');
    altezza(altezze().chiuso, false);
    tabsEl.addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.t === tabAttiva && posSheet !== 'chiuso') { chiudi(); return; }
      apri(b.dataset.t, posSheet === 'chiuso' ? 'meta' : posSheet);
    });
    // trascinare la maniglia (o la barra delle schede) apre e chiude il foglio
    const man = document.getElementById('maniglia');
    let tr = null;
    const inizio = e => { tr = { y: e.clientY, h: aside.getBoundingClientRect().height, mosso: false, id: e.pointerId }; };
    const muovi = e => {
      if (!tr || e.pointerId !== tr.id) return;
      const dy = tr.y - e.clientY;
      if (Math.abs(dy) > 6) tr.mosso = true;
      if (!tr.mosso) return;
      const a = altezze();
      altezza(Math.max(a.chiuso, Math.min(a.tutto, tr.h + dy)), false);
    };
    const fine = e => {
      if (!tr || e.pointerId !== tr.id) return;
      const a = altezze(), h = aside.getBoundingClientRect().height;
      if (!tr.mosso) { if (e.currentTarget === man) { posSheet === 'chiuso' ? apri(null, 'meta') : chiudi(); } tr = null; return; }
      const v = tr.y - e.clientY;    // verso del gesto: decide in quale posizione fermarsi
      let pos = Object.keys(a).reduce((m, k) => Math.abs(a[k] - h) < Math.abs(a[m] - h) ? k : m, 'chiuso');
      if (Math.abs(v) > 60) pos = v > 0 ? (h > a.meta + 20 ? 'tutto' : 'meta') : (h < a.meta - 20 ? 'chiuso' : 'meta');
      tr = null;
      if (pos === 'chiuso') chiudi(); else apri(null, pos);
    };
    for (const el of [man, tabsEl]) {
      el.addEventListener('pointerdown', e => { inizio(e); if (el === man) man.setPointerCapture(e.pointerId); });
      el.addEventListener('pointermove', muovi);
      el.addEventListener('pointerup', fine);
      el.addEventListener('pointercancel', () => { tr = null; });
    }
    document.getElementById('stato').addEventListener('click', () => apri(VISTA === 'banco' ? 'guasti' : 'info', 'meta'));
    addEventListener('resize', () => altezza(altezze()[posSheet], false));

    // bolla del telefono vero: si trascina dalla barretta, ⤢ la apre a tutto schermo
    const bar = document.getElementById('telbar');
    let tb = null;
    bar.addEventListener('pointerdown', e => {
      if (e.target.closest('button') || telbox.classList.contains('grande')) return;
      const r = telbox.getBoundingClientRect();
      tb = { dx: e.clientX - r.left, dy: e.clientY - r.top, id: e.pointerId }; bar.setPointerCapture(e.pointerId);
    });
    bar.addEventListener('pointermove', e => {
      if (!tb || e.pointerId !== tb.id) return;
      const r = telbox.getBoundingClientRect();
      const x = Math.max(4, Math.min(innerWidth - r.width - 4, e.clientX - tb.dx));
      const y = Math.max(56, Math.min(innerHeight - r.height - 70, e.clientY - tb.dy));
      telbox.style.left = x + 'px'; telbox.style.top = y + 'px'; telbox.style.right = 'auto';
    });
    bar.addEventListener('pointerup', () => { tb = null; });
  }
  function telefono(on) {
    telbox.classList.toggle('grande', on);
    document.getElementById('telgrande').textContent = on ? '✕' : '⤢';
    document.getElementById('telgrande').title = on ? 'Chiudi' : 'Apri grande';
    if (on) { telbox.dataset.st = telbox.getAttribute('style') || ''; telbox.removeAttribute('style'); }
    else if (telbox.dataset.st !== undefined) telbox.setAttribute('style', telbox.dataset.st);
  }
  document.getElementById('telgrande').addEventListener('click', () => telefono(!telbox.classList.contains('grande')));
  document.getElementById('telmin').addEventListener('click', () => telbox.classList.toggle('min'));

  // chip di inquadratura
  const chipsEl = document.getElementById('chips');
  const centro = gs => { const b = new THREE.Box3(); gs.forEach(g => b.expandByObject(g)); const c = b.getCenter(V(0, 0, 0)), z = b.getSize(V(0, 0, 0)); return [c, Math.max(z.x, z.z, 30)]; };
  const vai = gs => { const [c, z] = centro(gs.filter(Boolean)); flyTo(c, z * (MOB ? 2.1 : 1.5)); };
  const CHIP_BANCO = [
    ['Tutto', () => flyTo(V(0, 0, 0), MOB ? 560 : 370)],
    ['ESP32', () => vai([groups.devkit])],
    ['Display', () => vai([groups.lcd])],
    ['Tastiera', () => vai([groups.keypad])],
    ['microSD', () => vai([groups.sd])],
    ['Audio', () => vai([groups.mic, groups.amp, groups.piezo])],
    ['Vibrazione', () => vai([groups.vibra])],
    ['Corrente', () => vai([groups.alim])],
  ];
  const CHIP_FIN = [
    ['Fronte', () => { tutti(); esplodi(0); document.getElementById('esplodi').value = 0; P3 && P3.view('fronte'); }],
    ['Esploso', () => { tutti(); esplodi(1); document.getElementById('esplodi').value = 1; P3 && P3.view('tre4'); }],
    ['Metà', () => { tutti(); esplodi(0.5); document.getElementById('esplodi').value = 0.5; P3 && P3.view('tre4'); }],
    ['Retro', () => { tutti(); esplodi(0); document.getElementById('esplodi').value = 0; P3 && P3.view('retro'); }],
    ['Scheda AurI', () => { if (!P3) return; for (const n of ['Coperchio', 'Batteria', 'Chassis', 'Viti Torx', 'Display', 'Tastierino', 'Cover frontale']) P3.setVisible(n, false); esplodi(0); document.getElementById('esplodi').value = 0; P3.view('dietro34'); }],
    ['Lato tasti', () => { if (!P3) return; for (const n of ['Coperchio', 'Batteria', 'Chassis', 'Viti Torx', 'Display', 'Tastierino', 'Cover frontale']) P3.setVisible(n, false); esplodi(0); document.getElementById('esplodi').value = 0; P3.view('tre4'); }],
  ];
  function chips() {
    const lista = VISTA === 'banco' ? CHIP_BANCO : CHIP_FIN;
    chipsEl.innerHTML = lista.map(([n], i) => `<button data-i="${i}">${n}</button>`).join('');
    chipsEl.onclick = e => { const b = e.target.closest('button'); if (!b) return; lista[+b.dataset.i][1](); chipsEl.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); };
  }
  chips();

  // etichette 3D: sul telefono piccole e solo quando servono (scheda Saldature aperta o da vicino)
  const vv = new THREE.Vector3();
  function frame() {
    if (!MOB) return;
    const vicino = p => camera.position.distanceTo(p.getWorldPosition(vv)) < 150;
    for (const o of gSald.children) if (o.isSprite) { o.visible = (tabAttiva === 'sald' && posSheet !== 'chiuso') || vicino(o); o.scale.set(22, 4.1, 1); }
    for (const l of finLabels) { l.visible = (tabAttiva === 'info' && posSheet !== 'chiuso') || vicino(l) || camera.position.distanceTo(controls.target) < 230; l.scale.set(19, 3.6, 1); }
  }
  return { apri, chiudi, scheda, telefono, chips, frame, stato: () => ({ tab: tabAttiva, pos: posSheet }) };
})();
window.UI = UI;

// per le prove automatiche
const prova = { stacca: i => { conns[i].guasto = { stacca: true }; ridisegna(conns[i]); aggiorna(); }, sposta: (i, p) => { conns[i].guasto = { pin: p }; ridisegna(conns[i]); aggiorna(); }, variante, statoTel, valuta, effetto, vista, esplodi };
window.banco = { conns, groups, select, flyTo, camera, controls, prova, ui: UI, pronto: true, p3: () => P3 };
