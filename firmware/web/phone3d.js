import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { SSAOPass } from 'three/addons/postprocessing/SSAOPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

// Coordinate in mm: origine al centro della cover 2D, x a destra, y in alto, z verso il fronte (retro a z=0, fronte a z=18).
const KEYS = [
  ['1', 'e', 180, 1320, 85, 55, -8], ['2', 'e', 410, 1345, 85, 52, 0], ['3', 'e', 650, 1320, 85, 55, 8],
  ['4', 'e', 185, 1445, 85, 55, -8], ['5', 'e', 410, 1480, 85, 52, 0], ['6', 'e', 640, 1445, 85, 55, 8],
  ['7', 'e', 190, 1600, 85, 55, -8], ['8', 'e', 410, 1620, 85, 52, 0], ['9', 'e', 635, 1600, 85, 55, 8],
  ['*', 'e', 205, 1730, 85, 55, -8], ['0', 'e', 410, 1760, 85, 52, 0], ['#', 'e', 625, 1730, 85, 55, 8],
  ['navi', 'e', 420, 1058, 160, 48, 0],
  ['c', 'p', 'M140,1090 L185,1048 L292,1110 L238,1190 Z'],
  ['up', 'p', 'M585,1110 L640,1072 L700,1085 L690,1140 L615,1175 Z'],
  ['down', 'p', 'M470,1150 L585,1110 L615,1175 L560,1210 L490,1245 Z'],
];
// masse stimate dei pezzi in grammi (batteria e chassis i piu' pesanti)
const MASS = { 'Coperchio': 14, 'Batteria': 30, 'Chassis': 25, 'Viti Torx': 1.5, 'Scheda (PCB)': 15, 'Display': 9, 'Tastierino': 5, 'Cover frontale': 16 };
const CW = 49.8, CH = 116.8, FACE = 18, FOV = 20;
// mediana dei pixel blu delle scansioni (faccia #161f37, retro #1c253d): pareti e facce devono combaciare
const BLUE = 0x1a2239;

const hitCtx = document.createElement('canvas').getContext('2d');
const keyAt = (x, y) => {
  for (const [k, kind, ...v] of KEYS) {
    if (kind === 'e') {
      const a = -v[4] * Math.PI / 180, dx = x - v[0], dy = y - v[1];
      const rx = dx * Math.cos(a) - dy * Math.sin(a), ry = dx * Math.sin(a) + dy * Math.cos(a);
      if ((rx / v[2]) ** 2 + (ry / v[3]) ** 2 <= 1) return k;
    } else if (hitCtx.isPointInPath(new Path2D(v[0]), x, y)) return k;
  }
  return null;
};

const toPath = (pts, sx = 1, sy = 1, cx = 0, cy = 0, P = THREE.Shape) => {
  const s = new P();
  for (let i = 0; i < pts.length; i += 2) s[i ? 'lineTo' : 'moveTo'](cx + (pts[i] - cx) * sx, cy + (pts[i + 1] - cy) * sy);
  return s;
};
const bbox = pts => {
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  for (let i = 0; i < pts.length; i += 2) { x0 = Math.min(x0, pts[i]); x1 = Math.max(x1, pts[i]); y0 = Math.min(y0, pts[i + 1]); y1 = Math.max(y1, pts[i + 1]); }
  return { x0, x1, y0, y1, cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, w: x1 - x0, h: y1 - y0 };
};
// I contorni scansionati hanno scalini di pochi decimi: ricampionati a passo costante e mediati diventano lisci.
const smooth = (pts, n = 240, win = 4, passes = 3) => {
  const P = [];
  for (let i = 0; i < pts.length; i += 2) P.push([pts[i], pts[i + 1]]);
  const L = [0];
  for (let i = 1; i <= P.length; i++) { const a = P[i - 1], b = P[i % P.length]; L.push(L[i - 1] + Math.hypot(b[0] - a[0], b[1] - a[1])); }
  let R = [], j = 0;
  for (let k = 0; k < n; k++) {
    const s = L[L.length - 1] * k / n;
    while (L[j + 1] < s) j++;
    const a = P[j], b = P[(j + 1) % P.length], t = (s - L[j]) / (L[j + 1] - L[j] || 1);
    R.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
  }
  for (let p = 0; p < passes; p++) R = R.map((_, i) => { let x = 0, y = 0; for (let d = -win; d <= win; d++) { const q = R[(i + d + n) % n]; x += q[0]; y += q[1]; } return [x / (2 * win + 1), y / (2 * win + 1)]; });
  return R.flat();
};
// contorno rimpicciolito di d mm per lato (abbastanza preciso per profili convessi)
const inset = (pts, d, P) => { const b = bbox(pts); return toPath(pts, (b.w - 2 * d) / b.w, (b.h - 2 * d) / b.h, b.cx, b.cy, P); };

export function createPhone3D(container, { press, release }) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(2, devicePixelRatio));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  // ombre morbide (skill threejs-lighting): PCFSoft e' ancora valido nella 0.160
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  // near/far stretti sulla scena in mm: piu' precisione di profondita' per l'occlusione ambientale
  const camera = new THREE.PerspectiveCamera(FOV, 1, 20, 3000);
  const controls = new OrbitControls(camera, renderer.domElement);
  const TARGET = new THREE.Vector3(0, 0, FACE / 2);
  controls.target.copy(TARGET);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  // niente spostamento del centro: con due dita si fa solo zoom e rotazione, il telefono resta al centro
  controls.enablePan = false;
  controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_ROTATE };
  controls.rotateSpeed = 0.9;
  // giro lento da vetrina quando nessuno tocca
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.7;

  // luci da studio: chiave con ombra, controluce freddo per staccare i bordi, riempimento basso
  scene.add(new THREE.HemisphereLight(0xffffff, 0x30343c, 0.6));
  const key = new THREE.DirectionalLight(0xfff4e8, 2.2);
  key.position.set(90, 160, 260);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, { left: -140, right: 140, top: 140, bottom: -140, near: 50, far: 900 });
  key.shadow.radius = 4;
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.4;
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xbfd4ff, 1.6); rim.position.set(-200, 80, -220); scene.add(rim);
  const fill = new THREE.DirectionalLight(0xffffff, 0.5); fill.position.set(-120, -160, 120); scene.add(fill);

  // post-produzione (skill threejs-postprocessing): RenderPass, SSAO nelle fessure, SMAA, OutputPass
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const ssao = new SSAOPass(scene, camera, 256, 256);
  ssao.kernelRadius = 6;
  ssao.minDistance = 0.0004;
  ssao.maxDistance = 0.012;
  composer.addPass(ssao);
  composer.addPass(new SMAAPass(256, 256));
  composer.addPass(new OutputPass());

  let explode = 0, explodeTarget = 0, needs = true, visible = false, lastLcd = 0, anim = null, dist = 400;
  const invalidate = () => { needs = true; };
  const loader = new THREE.TextureLoader();
  let pending = 0;
  const tex = (name, W, H, flip = false, srgb = true) => {
    pending++;
    const t = loader.load('tex/' + name, () => { pending--; invalidate(); }, undefined, () => { pending--; });
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    t.repeat.set((flip ? -1 : 1) / W, 1 / H); t.offset.set(0.5, 0.5);
    return t;
  };
  const mat = o => new THREE.MeshStandardMaterial({ roughness: 0.6, metalness: 0, envMapIntensity: 0.35, ...o });
  // plastica satinata del 3310: base ruvida con un velo lucido leggero (skill threejs-materials)
  const blue = new THREE.MeshPhysicalMaterial({ color: BLUE, roughness: 0.62, clearcoat: 0.25, clearcoatRoughness: 0.45, envMapIntensity: 0.35 });

  const layers = [];
  const layer = (z, spread, name) => { const g = new THREE.Group(); g.userData = { z, spread, name, off: new THREE.Vector3(), vel: new THREE.Vector3(), mass: MASS[name] || 10 }; g.position.z = z; scene.add(g); layers.push(g); return g; };
  const meshes = [];
  const add = (g, m) => { m.castShadow = true; m.receiveShadow = true; g.add(m); meshes.push(m); return m; };

  // Pezzo piatto: bordo estruso dal contorno reale, facce con le scansioni dei due lati.
  function slab(g, P, name, depth, edge, opts = {}) {
    const bev = Math.min(0.3, depth / 4);
    const side = new THREE.ExtrudeGeometry(inset(P.outline, bev), { depth: depth - 2 * bev, bevelEnabled: true, bevelThickness: bev, bevelSize: bev, bevelSegments: 3, curveSegments: 1 });
    side.translate(0, 0, bev);
    add(g, new THREE.Mesh(side, mat({ color: edge, roughness: 0.7 })));
    // facce appena dentro il bordo smussato, cosi' il contorno lo disegna la geometria e non l'alpha della scansione
    const f = new THREE.ShapeGeometry(inset(P.outline, bev));
    const front = new THREE.Mesh(f, mat({ map: tex(name + '_front.webp', P.w, P.h), alphaTest: 0.1, polygonOffset: true, polygonOffsetFactor: -2, ...opts }));
    front.position.z = depth + 0.01; add(g, front);
    const back = new THREE.Mesh(f, mat({ map: tex(name + '_back.webp', P.w, P.h, true), alphaTest: 0.1, polygonOffset: true, polygonOffsetFactor: -2, side: THREE.BackSide, ...opts }));
    back.position.z = -0.01; add(g, back);
  }

  let power, lcdTex, coverFace;
  const keyMeshes = [];
  const ready = fetch('tex/parts.json').then(r => r.json()).then(build);

  // Anello (parete di un contenitore) dal contorno: spessore wall, bordi arrotondati di bev.
  function ring(pts, wall, z0, z1, bev, P) {
    const s = inset(pts, bev);
    s.holes.push(inset(pts, wall - bev, THREE.Path));
    for (const h of P || []) s.holes.push(h);
    const g = new THREE.ExtrudeGeometry(s, { depth: z1 - z0 - 2 * bev, bevelEnabled: bev > 0, steps: 1, bevelThickness: bev, bevelSize: bev, bevelSegments: 4, curveSegments: 2 });
    g.translate(0, 0, z0 + bev);
    return g;
  }
  // Piega i gusci come nel video: f(nx, ny) restituisce la nuova z di un vertice, con nx, ny in -1..1 sul contorno.
  function bend(g, b, f) {
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) p.setZ(i, f((p.getX(i) - b.cx) / (b.w / 2), (p.getY(i) - b.cy) / (b.h / 2), p.getZ(i)));
    g.computeVertexNormals();
    return g;
  }
  const sstep = (a, b, v) => { const t = Math.min(1, Math.max(0, (v - a) / (b - a))); return t * t * (3 - 2 * t); };
  // retro: bordi laterali arrotondati, estremita' che risalgono, piu' sottile in alto
  // curvatura solo nella fascia esterna, dove dietro c'e' solo la parete: lo chassis resta dentro
  const backZ = (nx, ny, z) => { const zb = Math.min(4, 3 * sstep(0.86, 1.02, Math.abs(nx)) + 1.6 * sstep(0.95, 1.03, Math.abs(ny))); return zb + z * (9 - zb) / 9; };
  // tiene solo i triangoli di una griglia che cadono dentro il contorno pts
  const inside = (pts, x, y) => { let c = false; for (let i = 0, j = pts.length - 2; i < pts.length; j = i, i += 2) { const xi = pts[i], yi = pts[i + 1], xj = pts[j], yj = pts[j + 1]; if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) c = !c; } return c; };
  const clip = (g, pts) => {
    const p = g.attributes.position, idx = g.index.array, keep = [];
    for (let i = 0; i < idx.length; i += 3) {
      const a = idx[i], b = idx[i + 1], c = idx[i + 2];
      if (inside(pts, (p.getX(a) + p.getX(b) + p.getX(c)) / 3, (p.getY(a) + p.getY(b) + p.getY(c)) / 3)) keep.push(a, b, c);
    }
    g.setIndex(keep); return g;
  };
  const insetPts = (pts, d) => { const b = bbox(pts), sx = (b.w - 2 * d) / b.w, sy = (b.h - 2 * d) / b.h; return pts.map((v, i) => i % 2 ? b.cy + (v - b.cy) * sy : b.cx + (v - b.cx) * sx); };
  // fronte: faccia che scende verso i fianchi e verso le due estremita'
  const frontZ = (nx, ny, z) => { const d = 2.2 * nx ** 6 + 2.2 * sstep(0.68, 1, Math.abs(ny)); return z <= 9 ? z : 9 + (z - 9) * (9 - d) / 9; };
  // pareti laterali della cover: scavate di 3,5 mm lungo i fianchi della tastiera (dal video)
  // giunzione tra le cover (foto laterali del telefono chiuso): nella meta' alta il coperchio forma quasi tutto
  // il fianco (16 mm), dalla tastiera in giu' la cover frontale scende fino a 6 mm dal retro
  const seamZ = (nx, ny) => 6 + 8 * sstep(-0.12, 0.06, ny);
  const backWallZ = (nx, ny, z) => { const b = backZ(nx, ny, z), s = seamZ(nx, ny); return z > 8 ? b + (s - 9) * (z - 8) : b; };
  const wallZ = (nx, ny, z) => {
    const top = frontZ(nx, ny, FACE);
    const base = seamZ(nx, ny);
    return base + (Math.max(9, z) - 9) * (top - base) / 9;
  };
  // griglia con uv = posizione in mm, come le ShapeGeometry su cui sono tarate le texture
  const grid = (b, nx = 100, ny = 240) => {
    const g = new THREE.PlaneGeometry(b.w, b.h, nx, ny).translate(b.cx, b.cy, 0), p = g.attributes.position, uv = g.attributes.uv;
    for (let i = 0; i < p.count; i++) uv.setXY(i, p.getX(i), p.getY(i));
    return g;
  };
  const shift = (pts, dx, dy) => pts.map((v, i) => v + (i % 2 ? dy : dx));
  const grow = (pts, d, P = THREE.Path) => { const b = bbox(pts); return toPath(pts, (b.w + 2 * d) / b.w, (b.h + 2 * d) / b.h, b.cx, b.cy, P); };

  // Pila reale (mm, z dal retro): coperchio 0-9 (pareti e fondo 1), chassis 1-15 con vano batteria
  // 1-7 sul retro e vano PCB 13-15 sul fronte, display 15-17, tappetino 16-17, tasti 17-19, cover 9-18.
  function build(P) {
    for (const k in P) P[k].outline = smooth(P[k].outline);
    const C = P.cover, cb = bbox(C.outline);
    const off = (part, dy = 0) => { const b = bbox(part.outline); return [cb.cx - b.cx, cb.cy - b.cy + dy]; };
    const center = (g, part, dy = 0) => { const [x, y] = off(part, dy); g.position.x = x; g.position.y = y; };
    const local = (part, of, dy = 0) => { const [ax, ay] = off(of, dy), [bx, by] = off(part); return shift(of.outline, ax - bx, ay - by); };

    // Coperchio posteriore: scatola profonda 9 mm, pareti e fondo da 1 mm, aperta verso il fronte.
    const back = layer(0, -60, 'Coperchio'), bg = new THREE.Group(); back.add(bg);
    const BP = P.back_cover;
    const bb = bbox(BP.outline);
    add(bg, new THREE.Mesh(bend(ring(BP.outline, 1, 0, 9, 0.45), bb, backWallZ), blue));
    // fondo curvo: griglia fitta piegata, il contorno lo ritaglia l'alpha della scansione sotto la parete
    // superfici ritagliate dal contorno liscio (dentro lo spessore della parete), non dall'alpha della scansione
    const bOut = new THREE.Mesh(bend(clip(grid(bb), insetPts(BP.outline, 0.5)), bb, (x, y) => backZ(x, y, 0)), mat({ map: tex('back_cover_back.webp', BP.w, BP.h, true), roughness: 0.6, side: THREE.BackSide }));
    add(bg, bOut);
    const bIn = new THREE.Mesh(bend(clip(grid(bb), insetPts(BP.outline, 0.9)), bb, (x, y) => backZ(x, y, 1)), mat({ map: tex('back_cover_front.webp', BP.w, BP.h), roughness: 0.8 }));
    add(bg, bIn);
    // ganci: due in alto e uno a L in basso, che entrano nella cover frontale
    const hook = (x, y, w, up) => {
      const g = new THREE.Group();
      const a = new THREE.Mesh(new THREE.BoxGeometry(w, 1, 3.2), blue); a.position.z = 10.4; g.add(a);
      const b = new THREE.Mesh(new THREE.BoxGeometry(w, 1.6, 0.9), blue); b.position.set(0, up ? -0.8 : 0.8, 11.6); g.add(b);
      g.position.set(x, y, 0); bg.add(g);
    };
    hook(-9, bb.y1 - 1.6, 4, true); hook(9, bb.y1 - 1.6, 4, true); hook(0, bb.y0 + 1.6, 10, false);
    // dentro il coperchio, misure stimate dalle riprese: ganci laterali, rilievo in alto, molla metallica in basso
    for (const sx of [-1, 1]) for (const y of [15, -5]) {
      const t = new THREE.Mesh(new THREE.BoxGeometry(1.2, 3.5, 2.4), blue);
      t.position.set(sx > 0 ? bb.x1 - 1.4 : bb.x0 + 1.4, bb.cy + y, 9.6); bg.add(t);
    }
    const boss = new THREE.Mesh(new THREE.BoxGeometry(11, 5, 1.6), blue); boss.position.set(bb.cx, bb.y1 - 11, 1.8); bg.add(boss);
    const steel = mat({ color: 0xc9ccd0, metalness: 0.9, roughness: 0.3 });
    const spring = new THREE.Mesh(new THREE.BoxGeometry(13, 11, 0.4), steel); spring.position.set(bb.cx, bb.y0 + 10, 1.3); bg.add(spring);
    for (const sx of [-1, 1]) { const o = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.6, 0.5, 24).rotateX(Math.PI / 2), mat({ color: 0x2a2d33 })); o.position.set(bb.cx + sx * 3.2, bb.y0 + 12, 1.4); bg.add(o); }
    center(bg, BP);

    // Batteria BLC-1: 6 mm, appoggiata sul fondo del coperchio dentro il vano dello chassis.
    // nel video la batteria sta in alto, infilata sotto il bordo superiore dello chassis
    const BAT_DY = 6;
    const bat = layer(1, -40, 'Batteria'), batg = new THREE.Group(); bat.add(batg);
    slab(batg, P.battery, 'battery', 6, 0x3a3a3a, { roughness: 0.75 });
    center(batg, P.battery, BAT_DY);

    // Chassis bianco 14 mm: anello posteriore col vano batteria, piano centrale, anello frontale col vano PCB.
    const ch = layer(1, -22, 'Chassis'), chg = new THREE.Group(); ch.add(chg);
    const CP = P.chassis, white = mat({ color: 0xbfc2c5, roughness: 0.6 });
    const batHole = grow(local(CP, P.battery, BAT_DY), 0.3);
    // le facce degli anelli portano le scansioni dello chassis (uv delle ExtrudeGeometry = posizione in mm)
    const chBack = mat({ map: tex('chassis_back.webp', CP.w, CP.h, true), roughness: 0.6 });
    const chFront = mat({ map: tex('chassis_front.webp', CP.w, CP.h), roughness: 0.6 });
    const rear = toPath(CP.outline); rear.holes.push(batHole);
    add(chg, new THREE.Mesh(new THREE.ExtrudeGeometry(rear, { depth: 6, bevelEnabled: false, curveSegments: 2 }), [chBack, white]));
    const mid = new THREE.Group(); mid.position.z = 6; chg.add(mid);
    slab(mid, CP, 'chassis', 6, 0xbfc2c5, { roughness: 0.6 });
    // il contorno del PCB sfiora quello dello chassis: il vano usa una parete fissa da 0,8 mm
    add(chg, new THREE.Mesh(ring(CP.outline, 0.8, 12, 14, 0), [chFront, white]));
    // linguette laterali dello chassis che si incastrano nelle pareti delle cover
    const cpb = bbox(CP.outline);
    // posizioni stimate dalle riprese del retro dello chassis
    for (const [sx, y] of [[-1, 12], [-1, -8], [1, 20], [1, -15]]) {
      const lug = new THREE.Mesh(new THREE.BoxGeometry(1.2, 4, 2.2), white);
      lug.position.set(sx > 0 ? cpb.x1 + 0.2 : cpb.x0 - 0.2, cpb.cy + y, 8); chg.add(lug);
    }
    center(chg, CP);

    // Viti Torx T6 lunghe 7 mm, dal retro dello chassis: da smontato escono dai loro fori.
    const sw = layer(1, -31, 'Viti Torx');
    const screwMat = mat({ color: 0xa8aaae, metalness: 0.9, roughness: 0.28 });
    const head = new THREE.CylinderGeometry(1.25, 1.1, 0.9, 32).rotateX(Math.PI / 2);
    const shank = new THREE.CylinderGeometry(0.7, 0.7, 6.1, 24).rotateX(Math.PI / 2);
    const thread = new THREE.TorusGeometry(0.72, 0.08, 6, 24);
    const star = new THREE.MeshBasicMaterial({ color: 0x18181a, side: THREE.DoubleSide });
    for (const [x, y] of [[-17.5, 47], [17.5, 47], [-18, -24], [18, -24], [-15, -50], [15, -50]]) {
      const s = new THREE.Group(); s.position.set(x, y, -0.45);
      add(s, new THREE.Mesh(head, screwMat));
      const sh = new THREE.Mesh(shank, screwMat); sh.position.z = 0.45 + 3.05; s.add(sh);
      for (let t = 0; t < 14; t++) { const r = new THREE.Mesh(thread, screwMat); r.position.z = 1.4 + t * 0.4; s.add(r); }
      for (let a = 0; a < 3; a++) { const b = new THREE.Mesh(new THREE.PlaneGeometry(1.3, 0.28), star); b.rotation.z = a * Math.PI / 3; b.position.z = -0.46; s.add(b); }
      sw.add(s);
    }

    // PCB verde 2 mm, a filo nel vano frontale dello chassis.
    const pcb = layer(13, 6, 'Scheda (PCB)'), pg = new THREE.Group(); pcb.add(pg);
    slab(pg, P.pcb, 'pcb', 2, 0x2c4a2e, { roughness: 0.45, metalness: 0.15 });
    center(pg, P.pcb);

    // Display 2 mm: telaio UI che lo regge e modulo LCD vivo.
    const ui = layer(15, 17, 'Display'), ug = new THREE.Group(); ui.add(ug);
    slab(ug, P.ui_frame, 'ui_frame', 1, 0xe8e8e8, { roughness: 0.55 });
    center(ug, P.ui_frame);
    lcdTex = new THREE.CanvasTexture(document.getElementById('lcd'));
    lcdTex.colorSpace = THREE.SRGBColorSpace;
    const lw = CW * 0.6846, lh = CH * 0.2101, lx = -CW / 2 + CW * (0.1524 + 0.6846 / 2), ly = CH / 2 - CH * (0.2601 + 0.2101 / 2);
    // modulo LCD tutto sotto la faccia della cover (che sta a 17): cornice scura e vetro a 16,6
    const metal = mat({ color: 0xb8bcc2, metalness: 0.7, roughness: 0.4 }), dark = mat({ color: 0x0c0d0f, roughness: 0.9 });
    const lcdBox = new THREE.Mesh(new THREE.BoxGeometry(lw + 0.8, lh + 0.8, 1.5), [metal, metal, metal, metal, dark, dark]);
    lcdBox.position.set(lx, ly, 0.85); ui.add(lcdBox);
    // fondo nero attorno al vetro: negli angoli della finestra non deve vedersi il telaio bianco
    const surround = new THREE.Mesh(new THREE.PlaneGeometry(lw + 8, lh + 10), dark);
    surround.position.set(lx, ly - 1, 1.3); ui.add(surround);
    // vetro 0,2 mm sopra il fondo del modulo: a 0,01 mm i due piani si contendevano i pixel (diagonale chiaro/scuro)
    const lcd = new THREE.Mesh(new THREE.PlaneGeometry(lw, lh), new THREE.MeshBasicMaterial({ map: lcdTex, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 }));
    lcd.position.set(lx, ly, 1.8); ui.add(lcd);

    // Tappetino in gomma 1 mm e tasti rialzati di 2 mm che escono di 1 mm dai fori della cover.
    const km = layer(16, 28, 'Tastierino');
    // pellicola azzurra trasparente sotto tutti i tasti: costruita attorno ai fori, cosi' i tasti ci stanno sempre sopra
    const hb = C.holes.reduce((a, h) => { const b = bbox(h); return { x0: Math.min(a.x0, b.x0), x1: Math.max(a.x1, b.x1), y0: Math.min(a.y0, b.y0), y1: Math.max(a.y1, b.y1) }; }, { x0: 1e9, x1: -1e9, y0: 1e9, y1: -1e9 });
    const mx0 = hb.x0 - 1.8, mx1 = hb.x1 + 1.8, my0 = hb.y0 - 1.8, my1 = hb.y1 + 1.8, mr = 5, film = new THREE.Shape();
    film.moveTo(mx0 + mr, my0); film.lineTo(mx1 - mr, my0); film.quadraticCurveTo(mx1, my0, mx1, my0 + mr); film.lineTo(mx1, my1 - mr); film.quadraticCurveTo(mx1, my1, mx1 - mr, my1);
    film.lineTo(mx0 + mr, my1); film.quadraticCurveTo(mx0, my1, mx0, my1 - mr); film.lineTo(mx0, my0 + mr); film.quadraticCurveTo(mx0, my0, mx0 + mr, my0);
    add(km, new THREE.Mesh(new THREE.ExtrudeGeometry(film, { depth: 1, bevelEnabled: false, curveSegments: 8 }), mat({ color: 0x9fc6ee, transparent: true, opacity: 0.55, roughness: 0.25, depthWrite: false })));
    const faceTex = tex('front_cover_front.webp', CW, CH);
    const keyMat = mat({ color: 0xbfc4cb, roughness: 0.32, metalness: 0.55 });
    // scritte dei tasti ridisegnate pulite (la scansione le aveva tagliate dai bordi dei fori)
    const LABELS = { '1': ['1', 'oo'], '2': ['2', 'abc'], '3': ['3', 'def'], '4': ['4', 'ghi'], '5': ['5', 'jkl'], '6': ['6', 'mno'], '7': ['7', 'pqrs'], '8': ['8', 'tuv'], '9': ['9', 'wxyz'], '*': ['*', '+'], '0': ['0', '_'], '#': ['#', ''], c: ['C', ''], up: ['▲', ''], down: ['▼', ''] };
    const labelTex = (k, w, h) => {
      const cv = document.createElement('canvas'), s = 64; cv.width = Math.round(w * s); cv.height = Math.round(h * s);
      const x = cv.getContext('2d'); x.fillStyle = '#16181c'; x.textBaseline = 'middle';
      if (k === 'navi') { x.fillStyle = '#3fb7d8'; x.beginPath(); x.ellipse(cv.width / 2, cv.height * 0.55, cv.width * 0.3, cv.height * 0.09, 0, 0, 7); x.fill(); }
      else if (k === 'updown') { x.textAlign = 'center'; x.font = `bold ${cv.height * 0.32}px Arial`; x.fillText('▲', cv.width * 0.62, cv.height * 0.32); x.fillText('▼', cv.width * 0.42, cv.height * 0.7); }
      else { const [a, b] = LABELS[k] || ['', '']; x.textAlign = 'right'; x.font = `bold ${cv.height * 0.8}px Arial`; x.fillText(a, cv.width * (b ? 0.5 : 0.62), cv.height * 0.52); x.textAlign = 'left'; x.font = `bold ${cv.height * 0.4}px Arial`; x.fillText(b, cv.width * 0.53, cv.height * 0.62); }
      const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = renderer.capabilities.getMaxAnisotropy(); return t;
    };
    // tasti: contorno liscio, bordo molto arrotondato e cupola di 0,5 mm come i tasti veri
    for (const h of C.holes) {
      const sh = smooth(h, 96, 2, 2), b = bbox(sh), d = 0.35, r = 0.8;
      let k = keyAt((b.cx / CW + 0.5) * 853, (0.5 - b.cy / CH) * 1999);
      if (k === 'up' || k === 'down') k = 'updown';
      const g = new THREE.ExtrudeGeometry(toPath(sh, (b.w - 2 * (d + r)) / b.w, (b.h - 2 * (d + r)) / b.h, b.cx, b.cy), { depth: 2 - 2 * r, bevelEnabled: true, bevelThickness: r, bevelSize: r, bevelSegments: 8, curveSegments: 3 });
      g.translate(0, 0, 1 + r);
      const p = g.attributes.position;
      for (let i = 0; i < p.count; i++) {
        const z = p.getZ(i);
        if (z > 2) { const u = (p.getX(i) - b.cx) / (b.w / 2), v = (p.getY(i) - b.cy) / (b.h / 2); p.setZ(i, z + 0.5 * Math.max(0, 1 - u * u - v * v) * (z - 2)); }
      }
      g.computeVertexNormals();
      keyMeshes.push(add(km, new THREE.Mesh(g, keyMat)));
      // etichetta sulla sommita' della cupola (al centro la cupola e' piatta entro 0,1 mm)
      // etichetta piegata sulla stessa cupola, 0,03 mm sopra
      const lw2 = b.w * 0.7, lh2 = b.h * 0.7, lg = new THREE.PlaneGeometry(lw2, lh2, 12, 12), lp = lg.attributes.position;
      for (let i = 0; i < lp.count; i++) { const u = lp.getX(i) / (b.w / 2), v = lp.getY(i) / (b.h / 2); lp.setZ(i, 3.03 + 0.5 * Math.max(0, 1 - u * u - v * v)); }
      const lab = new THREE.Mesh(lg, new THREE.MeshBasicMaterial({ map: labelTex(k, lw2, lh2), transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4 }));
      lab.position.set(b.cx, b.cy, 0); km.add(lab);
    }

    // Cover frontale: scatola da 9 mm con fori dei tasti, finestra LCD e targhetta AurI, tasto Power in alto.
    const front = layer(0, 48, 'Cover frontale');
    const faceShape = toPath(C.outline);
    for (const h of C.holes) faceShape.holes.push(toPath(h, 1, 1, 0, 0, THREE.Path));
    const wx0 = lx - lw / 2, wy0 = ly - lh / 2, r = 1.2, win = new THREE.Path();
    win.moveTo(wx0 + r, wy0); win.lineTo(wx0 + lw - r, wy0); win.quadraticCurveTo(wx0 + lw, wy0, wx0 + lw, wy0 + r); win.lineTo(wx0 + lw, wy0 + lh - r); win.quadraticCurveTo(wx0 + lw, wy0 + lh, wx0 + lw - r, wy0 + lh);
    win.lineTo(wx0 + r, wy0 + lh); win.quadraticCurveTo(wx0, wy0 + lh, wx0, wy0 + lh - r); win.lineTo(wx0, wy0 + r); win.quadraticCurveTo(wx0, wy0, wx0 + r, wy0);
    faceShape.holes.push(win);
    const T = 1;
    // faccia curva: griglia fitta piegata, fori e finestra li ritaglia l'alpha della scansione
    const fb = { ...cb, w: CW, h: CH, cx: 0, cy: 0 };
    const rmTex = tex('front_cover_rm.webp', CW, CH, false, false);
    const faceMat = mat({ map: faceTex, roughnessMap: rmTex, metalnessMap: rmTex, roughness: 1, metalness: 1, alphaTest: 0.5, envMapIntensity: 0.5 });
    coverFace = add(front, new THREE.Mesh(bend(grid(fb), cb, (x, y) => frontZ(x, y, FACE)), faceMat));
    // interno scuro con gli stessi fori: la scansione interna ha macchie di luce passata dai fori
    const cin = new THREE.Mesh(bend(grid(fb), cb, (x, y) => frontZ(x, y, FACE - T)), mat({ map: faceTex, color: 0x2a2f3a, alphaTest: 0.5, roughness: 0.85, side: THREE.BackSide }));
    add(front, cin);
    add(front, new THREE.Mesh(bend(ring(C.outline, 1, 9, FACE, 0.45), cb, wallZ), blue));
    // spessore di 1 mm sui bordi di fori e finestra
    for (const h of [...C.holes, win.getPoints(4).flatMap(p => [p.x, p.y])]) {
      const s = grow(h, 0.35, THREE.Shape); s.holes.push(toPath(h, 1, 1, 0, 0, THREE.Path));
      const g = new THREE.ExtrudeGeometry(s, { depth: T, bevelEnabled: false, curveSegments: 3 }); g.translate(0, 0, FACE - T);
      add(front, new THREE.Mesh(bend(g, cb, frontZ), blue));
    }
    // sui fianchi della cover: incavo ovale chiaro e sotto tre feritoie orizzontali (dalle foto laterali)
    const edgeX = y => { let m = 0; for (let i = 0; i < C.outline.length; i += 2) if (Math.abs(C.outline[i + 1] - y) < 2) m = Math.max(m, Math.abs(C.outline[i])); return m; };
    const slotMat = mat({ color: 0x0b0d12, roughness: 0.9 }), gripMat = mat({ color: 0x141b2e, roughness: 0.8, envMapIntensity: 0.15 });
    // dietro i fori della faccia (es. microfono in basso) non deve vedersi il telaio bianco
    const bk = { x0: cb.x0, x1: cb.x1, y0: cb.y0, y1: cb.y0 + 12 };
    Object.assign(bk, { w: bk.x1 - bk.x0, h: bk.y1 - bk.y0, cx: (bk.x0 + bk.x1) / 2, cy: (bk.y0 + bk.y1) / 2 });
    const backing = new THREE.Mesh(bend(clip(grid(bk, 60, 20), insetPts(C.outline, 1.2)), cb, (x, y) => frontZ(x, y, FACE - T) - 0.12), mat({ color: 0x07080b, roughness: 1, side: THREE.DoubleSide }));
    front.add(backing);
    for (const sx of [-1, 1]) {
      const gy = cb.cy - 0.26 * cb.h / 2;
      const grip = new THREE.Mesh(new THREE.CircleGeometry(1, 40).scale(2.6, 7, 1).rotateY(sx * Math.PI / 2), gripMat);
      grip.position.set(sx * (edgeX(gy) + 0.05), gy, 10.5); front.add(grip);
      for (let i = 0; i < 3; i++) {
        const y = -36.5 - i * 1.7;
        const slot = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.55, 3), slotMat);
        slot.position.set(sx * (edgeX(y) + 0.05), y, 8.6); front.add(slot);
      }
    }
    const glass = new THREE.Mesh(new THREE.PlaneGeometry(lw, lh), new THREE.MeshPhysicalMaterial({ color: 0xffffff, transparent: true, opacity: 0.08, roughness: 0.05, envMapIntensity: 1.2, depthWrite: false }));
    glass.position.set(lx, ly, FACE - 0.5); front.add(glass);
    // Power: ovale scuro centrato sullo spessore, come nella foto dall'alto
    power = new THREE.Mesh(new THREE.CapsuleGeometry(2.6, 9, 6, 24).rotateZ(Math.PI / 2).scale(1, 0.45, 1), mat({ color: 0x2a2c31, roughness: 0.7 }));
    // sta nel bordo alto del coperchio (dalla foto dall'alto), non nella cover frontale
    power.position.set(back.children[0].worldToLocal(new THREE.Vector3(0, 0, 0)).x * 0, cb.y1 - 0.4, 9.5);
    power.position.sub(back.children[0].position); add(back.children[0], power);
    applyExplode(); invalidate();
  }

  // posizione = livello nella pila + smontaggio + spostamento a mano del singolo pezzo
  const applyExplode = () => { for (const g of layers) g.position.set(0, 0, g.userData.z + g.userData.spread * explode).add(g.userData.off); };

  // Il canvas riempie lo stage, centrato come #phone: a Smonta 0 la faccia frontale coincide col box 2D.
  const phoneEl = document.getElementById('phone'), stageEl = document.getElementById('stage');
  let placed = false;
  function resize() {
    const r = phoneEl.getBoundingClientRect(), s = stageEl.getBoundingClientRect();
    if (!r.width || !s.width) return;
    const w = s.width, h = s.height;
    renderer.setSize(w, h);
    composer.setPixelRatio(renderer.getPixelRatio());
    composer.setSize(w, h);
    camera.aspect = w / h;
    // distanza perche' CH mm sul piano z=FACE valgano r.height px
    dist = (h * CH / r.height) / 2 / Math.tan(FOV * Math.PI / 360) + FACE - TARGET.z;
    camera.updateProjectionMatrix();
    if (!placed) { camera.position.set(0, 0, TARGET.z + dist); camera.up.set(0, 1, 0); placed = true; }
    else camera.position.sub(TARGET).setLength(dist).add(TARGET);
    controls.minDistance = dist * 0.15; controls.maxDistance = dist * 5;
    invalidate();
  }
  addEventListener('resize', resize);
  new ResizeObserver(resize).observe(stageEl);
  controls.addEventListener('change', invalidate);

  function loop(now) {
    requestAnimationFrame(loop);
    if (!visible) return;
    if (anim) {
      const t = Math.min(1, (now - anim.t0) / 650), e = t * t * (3 - 2 * t);
      camera.quaternion.slerpQuaternions(anim.q0, anim.q1, e);
      camera.position.set(0, 0, 1).applyQuaternion(camera.quaternion).multiplyScalar(dist).add(TARGET);
      camera.up.set(0, 1, 0).applyQuaternion(camera.quaternion);
      if (t === 1) { anim = null; controls.enabled = true; controls.update(); }
      needs = true;
    } else if (controls.update()) needs = true;
    if (physics(now)) needs = true;
    if (homing.size) {
      for (const [g, h] of homing) {
        const t = Math.min(1, (now - h.t0) / 550), e = 1 - (1 - t) ** 3;
        g.userData.off.copy(h.off).multiplyScalar(1 - e);
        g.quaternion.slerpQuaternions(h.q, Q0, e);
        if (t === 1) homing.delete(g);
      }
      applyExplode(); needs = true;
    }
    // il pezzo preso si solleva leggermente: unico segnale visivo, niente riquadri
    for (const g of layers) {
      const want = grab && grab.g === g && grab.mode === 'move' ? 1.04 : 1;
      if (Math.abs(g.scale.x - want) > 1e-3) { g.scale.setScalar(g.scale.x + (want - g.scale.x) * 0.25); needs = true; }
    }
    if (explode !== explodeTarget) {
      explode = Math.abs(explodeTarget - explode) < 1e-3 ? explodeTarget : explode + (explodeTarget - explode) * 0.15;
      applyExplode(); needs = true;
    }
    if (lcdTex && now - lastLcd > 66) { lastLcd = now; lcdTex.needsUpdate = true; needs = true; }
    if (needs) { needs = false; composer.render(); }
  }
  requestAnimationFrame(loop);

  // direzione della camera e vettore "su" per ogni vista
  const VIEWS = { fronte: [[0, 0, 1], [0, 1, 0]], retro: [[0, 0, -1], [0, 1, 0]], destra: [[1, 0, 0], [0, 1, 0]], sinistra: [[-1, 0, 0], [0, 1, 0]], alto: [[0, 1, 0], [0, 0, -1]], sotto: [[0, -1, 0], [0, 0, 1]] };
  function view(name) {
    const [dir, up] = VIEWS[name];
    const m = new THREE.Matrix4().lookAt(new THREE.Vector3(...dir), new THREE.Vector3(), new THREE.Vector3(...up));
    controls.target.copy(TARGET);
    controls.enabled = false;
    anim = { t0: performance.now(), q0: camera.quaternion.clone(), q1: new THREE.Quaternion().setFromRotationMatrix(m) };
  }

  const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
  let downKey = null;
  const pick = e => {
    const r = renderer.domElement.getBoundingClientRect();
    ptr.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
    ray.setFromCamera(ptr, camera);
    const hit = ray.intersectObjects(meshes, false)[0];
    if (!hit) return null;
    if (hit.object === power) return 'power';
    if (hit.object === coverFace || keyMeshes.includes(hit.object)) {
      const p = hit.object.worldToLocal(hit.point.clone());
      return keyAt((p.x / CW + 0.5) * 853, (0.5 - p.y / CH) * 1999);
    }
    return null;
  };
  // Interazione a gesti (skill threejs-interaction: un solo set di pointer event per mouse e dita).
  // Trascina lo sfondo = gira la vista; tieni premuto un pezzo = lo stacchi e lo sposti;
  // trascina un pezzo gia' staccato = lo ruoti; doppio tocco su un pezzo = torna a posto;
  // doppio tocco sullo sfondo = smonta / ricomponi tutto.
  const partOf = o => { while (o && !layers.includes(o)) o = o.parent; return o; };
  const setPtr = e => { const r = renderer.domElement.getBoundingClientRect(); ptr.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1); ray.setFromCamera(ptr, camera); };
  const hitPart = e => {
    setPtr(e);
    for (const h of ray.intersectObjects(meshes, false)) { const g = partOf(h.object); if (g && g.visible) return { g, point: h.point }; }
    return null;
  };
  const Q0 = new THREE.Quaternion();
  const displaced = g => g.userData.off.lengthSq() > 0.01 || !g.quaternion.equals(Q0);
  const keysLive = () => explode < 0.01 && !layers.some(displaced);
  const homing = new Map(); // pezzo -> {t0, off, q}
  const sendHome = g => (g.userData.vel.set(0, 0, 0), homing.set(g, { t0: performance.now(), off: g.userData.off.clone(), q: g.quaternion.clone() }));

  // --- Fisica degli urti -------------------------------------------------------------------
  // Ogni pezzo ha massa m e velocita' v (mm/s). Urto lungo l'asse di minima compenetrazione dei
  // box: conservazione della quantita' di moto con coefficiente di restituzione e,
  //   v1' = (m1 v1 + m2 v2 + m2 e (v2 - v1)) / (m1 + m2),  v2' = (m1 v1 + m2 v2 + m1 e (v1 - v2)) / (m1 + m2)
  // Il pezzo tenuto in mano ha massa infinita: v2' = v1 + e (v1 - v2). Attrito viscoso: v *= exp(-k dt).
  // Le coppie che si compenetrano gia' a riposo (pezzi incastrati) si ignorano finche' non si separano.
  const E = 0.35, K = 3.2, VMIN = 2, STEP = 0.8;
  const boxes = []; // creati al primo uso: i pezzi arrivano dopo, quando il modello e' caricato
  // Box di ogni pezzo nella sua posa di riposo (senza spostamenti ne' rotazioni): due pezzi che a
  // riposo si compenetrano sono incastrati per costruzione (es. PCB nel vano dello chassis) e non si urtano.
  const localBox = new Map();
  const restBox = g => {
    if (!localBox.has(g)) {
      const p = g.position.clone(), q = g.quaternion.clone(), sc = g.scale.clone();
      g.position.set(0, 0, 0); g.quaternion.identity(); g.scale.setScalar(1); g.updateMatrixWorld(true);
      localBox.set(g, new THREE.Box3().setFromObject(g).expandByScalar(-0.3));
      g.position.copy(p); g.quaternion.copy(q); g.scale.copy(sc); g.updateMatrixWorld(true);
    }
    return localBox.get(g).clone().translate(new THREE.Vector3(0, 0, g.userData.z + g.userData.spread * explode));
  };
  const nested = (A, B) => restBox(A).intersectsBox(restBox(B));
  let lastPhys = 0;
  const resetPairs = () => {};
  let unsettled = false;
  // risolutore iterativo: ripete finche' nessuna coppia si compenetra (o 10 giri), cosi' le catene A->B->C si chiudono
  function collide(held) {
    for (let it = 0; it < 10; it++) if (!collideOnce(held)) { unsettled = false; return; }
    unsettled = true;
  }
  function collideOnce(held) {
    let hit = false;
    applyExplode();
    layers.forEach((g, i) => (boxes[i] ||= new THREE.Box3()).setFromObject(g));
    for (let i = 0; i < layers.length; i++) for (let j = i + 1; j < layers.length; j++) {
      const A = layers[i], B = layers[j];
      if (!A.visible || !B.visible || homing.has(A) || homing.has(B)) continue;
      const a = boxes[i], b = boxes[j];
      if (!a.intersectsBox(b) || nested(A, B)) continue;
      // asse e profondita' di compenetrazione minima
      const ov = [Math.min(a.max.x, b.max.x) - Math.max(a.min.x, b.min.x),
                  Math.min(a.max.y, b.max.y) - Math.max(a.min.y, b.min.y),
                  Math.min(a.max.z, b.max.z) - Math.max(a.min.z, b.min.z)];
      const ax = ov.indexOf(Math.min(...ov)), depth = ov[ax];
      if (depth < 0.05) continue;
      hit = true;
      const ca = a.getCenter(new THREE.Vector3()), cb = b.getCenter(new THREE.Vector3());
      const n = new THREE.Vector3().setComponent(ax, Math.sign(cb.getComponent(ax) - ca.getComponent(ax)) || 1);
      const ua = A.userData, ub = B.userData;
      const kinA = A === held, kinB = B === held;
      const ma = kinA ? Infinity : ua.mass, mb = kinB ? Infinity : ub.mass;
      // separazione proporzionale alle masse inverse
      const ia = kinA ? 0 : 1 / ma, ib = kinB ? 0 : 1 / mb;
      ua.off.addScaledVector(n, -depth * ia / (ia + ib));
      ub.off.addScaledVector(n, depth * ib / (ia + ib));
      const va = ua.vel.dot(n), vb = ub.vel.dot(n);
      if (va - vb <= 0) continue; // si stanno gia' allontanando
      let na, nb;
      if (kinA) { na = va; nb = va + E * (va - vb); }
      else if (kinB) { nb = vb; na = vb + E * (vb - va); }
      else { na = (ma * va + mb * vb + mb * E * (vb - va)) / (ma + mb); nb = (ma * va + mb * vb + ma * E * (va - vb)) / (ma + mb); }
      if (!kinA) ua.vel.addScaledVector(n, na - va);
      if (!kinB) ub.vel.addScaledVector(n, nb - vb);
      if (navigator.vibrate && Math.abs(na - va) + Math.abs(nb - vb) > 120) navigator.vibrate(8);
    }
    applyExplode();
    return hit;
  }
  function physics(now) {
    const dt = Math.min(0.05, (now - (lastPhys || now)) / 1000);
    lastPhys = now;
    const held = grab && grab.mode === 'move' ? grab.g : null;
    // mano ferma: il pezzo tenuto non spinge e non verra' lanciato
    if (held && now - grab.lt > 80) held.userData.vel.set(0, 0, 0);
    const moving = layers.some(g => g.userData.vel.lengthSq() > VMIN * VMIN) || held;
    if (!moving && unsettled) { collide(null); applyExplode(); return true; }
    if (!moving || !dt) return false;
    // passi da massimo STEP mm, cosi' un pezzo veloce non attraversa quelli sottili (effetto tunnel)
    let vmax = 0;
    for (const g of layers) if (g !== held) vmax = Math.max(vmax, g.userData.vel.length());
    const n = Math.min(40, Math.max(1, Math.ceil(vmax * dt / STEP)));
    for (let k = 0; k < n; k++) {
      for (const g of layers) {
        if (g === held || homing.has(g)) continue;
        g.userData.off.addScaledVector(g.userData.vel, dt / n);
      }
      collide(held);
    }
    for (const g of layers) {
      const v = g.userData.vel;
      if (g === held) continue;
      v.multiplyScalar(Math.exp(-K * dt));
      if (v.lengthSq() < VMIN * VMIN) v.set(0, 0, 0);
    }
    applyExplode();
    return true;
  }
  function reassemble() { resetPairs(); for (const g of layers) if (displaced(g)) sendHome(g); explodeTarget = 0; invalidate(); }
  let grab = null, lastTap = { t: 0, g: undefined }, idleTimer = 0;
  const plane = new THREE.Plane(), hitP = new THREE.Vector3();
  const pause = () => { controls.autoRotate = false; clearTimeout(idleTimer); idleTimer = setTimeout(() => { controls.autoRotate = true; }, 9000); };
  controls.addEventListener('start', pause);

  function startMove(gr) {
    gr.mode = 'move';
    controls.enabled = false;
    plane.setFromNormalAndCoplanarPoint(camera.getWorldDirection(new THREE.Vector3()), gr.point);
    gr.last = gr.point.clone();
    gr.lt = performance.now();
    gr.g.userData.vel.set(0, 0, 0);
    homing.delete(gr.g);
    if (navigator.vibrate) navigator.vibrate(12);
    window.auriTrack?.('3d/stacca/' + gr.g.userData.name);
    invalidate();
  }

  renderer.domElement.addEventListener('pointerdown', e => {
    pause();
    if (!e.isPrimary) { if (grab) { clearTimeout(grab.timer); grab = null; controls.enabled = true; } return; }
    if (keysLive()) {
      const k = pick(e);
      if (k) {
        e.stopImmediatePropagation(); e.preventDefault();
        controls.enabled = false; downKey = k;
        renderer.domElement.setPointerCapture(e.pointerId);
        if (k === 'power') power.position.y -= 0.6;
        invalidate(); press(k);
        return;
      }
    }
    const h = hitPart(e);
    grab = { x: e.clientX, y: e.clientY, t: performance.now(), g: h && h.g, point: h && h.point, mode: null, moved: false };
    if (!h) return;
    const free = explode > 0.01 || displaced(h.g);
    if (free) {
      // pezzo staccato: il trascinamento gira il pezzo, non la vista
      e.stopImmediatePropagation();
      renderer.domElement.setPointerCapture(e.pointerId);
      grab.freeze = true;
    }
    const gr = grab;
    gr.timer = setTimeout(() => { if (grab === gr && !gr.moved) startMove(gr); }, 320);
  }, { capture: true });

  const end = e => {
    if (downKey) {
      release(downKey); if (downKey === 'power') power.position.y += 0.6;
      downKey = null; controls.enabled = true; invalidate();
      return;
    }
    if (!grab) return;
    clearTimeout(grab.timer);
    const g = grab.g, wasTap = !grab.moved && !grab.mode && performance.now() - grab.t < 300;
    controls.enabled = true;
    grab = null;
    if (!wasTap) return;
    const now = performance.now();
    if (now - lastTap.t < 320 && lastTap.g === (g || null)) {
      if (g && displaced(g)) sendHome(g);
      else if (layers.some(displaced) || explode > 0.01) { reassemble(); window.auriTrack?.('3d/ricomponi'); }
      else { resetPairs(); explodeTarget = 1; window.auriTrack?.('3d/smonta'); }
      lastTap = { t: 0, g: undefined };
    } else lastTap = { t: now, g: g || null };
    invalidate();
  };
  renderer.domElement.addEventListener('pointerup', end);
  renderer.domElement.addEventListener('pointercancel', end);
  renderer.domElement.addEventListener('pointermove', e => {
    if (downKey || !grab || !e.isPrimary) return;
    const dx = e.clientX - grab.x, dy = e.clientY - grab.y;
    if (!grab.mode && Math.hypot(dx, dy) > 6) {
      grab.moved = true;
      clearTimeout(grab.timer);
      if (grab.freeze) { grab.mode = 'rotate'; controls.enabled = false; homing.delete(grab.g); window.auriTrack?.('3d/ruota/' + grab.g.userData.name); }
    }
    if (grab.mode === 'move') {
      setPtr(e);
      if (ray.ray.intersectPlane(plane, hitP)) {
        const d = hitP.clone().sub(grab.last), t = performance.now(), dt = Math.max(8, t - grab.lt) / 1000;
        // velocita' della mano (media mobile): serve agli urti e al lancio quando si lascia il pezzo
        grab.g.userData.vel.lerp(d.clone().divideScalar(dt), 0.5);
        grab.lt = t;
        const n = Math.min(60, Math.max(1, Math.ceil(d.length() / STEP)));
        for (let k = 0; k < n; k++) { grab.g.userData.off.addScaledVector(d, 1 / n); collide(grab.g); }
        grab.last.copy(hitP); applyExplode(); invalidate();
      }
    } else if (grab.mode === 'rotate') {
      const up = new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion), right = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion);
      grab.g.rotateOnWorldAxis(up, dx * 0.012);
      grab.g.rotateOnWorldAxis(right, dy * 0.012);
      grab.x = e.clientX; grab.y = e.clientY;
      // anche girando un pezzo, se urta gli altri li sposta
      collide(grab.g);
      invalidate();
    }
  });
  renderer.domElement.addEventListener('pointerover', e => { if (e.pointerType === 'mouse') renderer.domElement.style.cursor = 'grab'; });

  return {
    show(on) { visible = on; if (on) { resize(); invalidate(); } },
    view,
    setExplode(v) { resetPairs(); explodeTarget = v; },
    get explodeTarget() { return explodeTarget; },
    // per i test: posizione sullo schermo del centro di un pezzo, distanza e centro della camera
    where(name) {
      const g = layers.find(l => l.userData.name === name); if (!g) return null;
      const c = new THREE.Box3().setFromObject(g).getCenter(new THREE.Vector3()).project(camera);
      const r = renderer.domElement.getBoundingClientRect();
      return { x: r.left + (c.x + 1) / 2 * r.width, y: r.top + (1 - c.y) / 2 * r.height };
    },
    camera: () => ({ dist: camera.position.distanceTo(controls.target), target: controls.target.toArray().map(v => +v.toFixed(2)), pos: camera.position.toArray().map(v => +v.toFixed(1)) }),
    displacedNames: () => layers.filter(displaced).map(g => g.userData.name),
    // per i test: coppie di pezzi non incastrati che si compenetrano oltre 0,5 mm
    penetrations() {
      layers.forEach((g, i) => (boxes[i] ||= new THREE.Box3()).setFromObject(g));
      const out = [];
      for (let i = 0; i < layers.length; i++) for (let j = i + 1; j < layers.length; j++) {
        const a = boxes[i], b = boxes[j];
        if (!layers[i].visible || !layers[j].visible || nested(layers[i], layers[j]) || !a.intersectsBox(b)) continue;
        const d = Math.min(Math.min(a.max.x, b.max.x) - Math.max(a.min.x, b.min.x), Math.min(a.max.y, b.max.y) - Math.max(a.min.y, b.min.y), Math.min(a.max.z, b.max.z) - Math.max(a.min.z, b.min.z));
        if (d > 0.5) out.push(layers[i].userData.name + ' / ' + layers[j].userData.name + ' ' + d.toFixed(1));
      }
      return out;
    },
    reassemble,
    get loading() { return pending > 0; },
    ready,
  };
}
