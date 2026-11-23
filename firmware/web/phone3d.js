import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

// Coordinate in mm: origine al centro della cover 2D, x a destra, y in alto, z verso il fronte (retro a z=0, fronte a z=22).
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
const CW = 49.8, CH = 116.8, FACE = 22, FOV = 20;
const BLUE = 0x1c253d;

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
// contorno rimpicciolito di d mm per lato (abbastanza preciso per profili convessi)
const inset = (pts, d, P) => { const b = bbox(pts); return toPath(pts, (b.w - 2 * d) / b.w, (b.h - 2 * d) / b.h, b.cx, b.cy, P); };

export function createPhone3D(container, { press, release }) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(2, devicePixelRatio));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  const camera = new THREE.PerspectiveCamera(FOV, 1, 1, 5000);
  const controls = new OrbitControls(camera, renderer.domElement);
  const TARGET = new THREE.Vector3(0, 0, FACE / 2);
  controls.target.copy(TARGET);
  controls.enableDamping = true;
  controls.enablePan = false;

  scene.add(new THREE.HemisphereLight(0xffffff, 0x404050, 1.1));
  const key = new THREE.DirectionalLight(0xffffff, 1.3); key.position.set(60, 120, 220); scene.add(key);
  const fill = new THREE.DirectionalLight(0xdfe6ff, 1.1); fill.position.set(-150, -40, -160); scene.add(fill);

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
  const blue = mat({ color: BLUE, roughness: 0.5 });

  const layers = [];
  const layer = (z, spread) => { const g = new THREE.Group(); g.userData = { z, spread }; g.position.z = z; scene.add(g); layers.push(g); return g; };
  const meshes = [];
  const add = (g, m) => { g.add(m); meshes.push(m); return m; };

  // Pezzo piatto: bordo estruso dal contorno reale, facce con le scansioni dei due lati.
  function slab(g, P, name, depth, edge, opts = {}) {
    const sh = toPath(P.outline);
    const side = new THREE.ExtrudeGeometry(sh, { depth, bevelEnabled: false, curveSegments: 1 });
    add(g, new THREE.Mesh(side, mat({ color: edge, roughness: 0.7 })));
    const f = new THREE.ShapeGeometry(sh);
    const front = new THREE.Mesh(f, mat({ map: tex(name + '_front.webp', P.w, P.h), alphaTest: 0.5, ...opts }));
    front.position.z = depth + 0.01; add(g, front);
    const back = new THREE.Mesh(f, mat({ map: tex(name + '_back.webp', P.w, P.h, true), alphaTest: 0.5, side: THREE.BackSide, ...opts }));
    back.position.z = -0.01; add(g, back);
  }

  let power, lcdTex, coverFace;
  const keyMeshes = [];
  const ready = fetch('tex/parts.json').then(r => r.json()).then(build);

  function build(P) {
    const C = P.cover, cb = bbox(C.outline);
    const center = (g, part, dy = 0) => { const b = bbox(part.outline); g.position.x = cb.cx - b.cx; g.position.y = cb.cy - b.cy + dy; };

    // Coperchio posteriore bombato: retro a z=0 al centro, bordi a z=3.4, bordo superiore a z=9.6.
    const back = layer(0, -70), bg = new THREE.Group(); back.add(bg);
    const BP = P.back_cover, Z1 = 9.6, bev = 1.4;
    const bgeo = new THREE.ExtrudeGeometry(inset(BP.outline, bev), { depth: Z1 - 2 * bev, bevelEnabled: true, bevelThickness: bev, bevelSize: bev, bevelSegments: 4, curveSegments: 2 });
    bgeo.translate(0, 0, bev);
    const bb = bbox(BP.outline), pos = bgeo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const nx = (pos.getX(i) - bb.cx) / (bb.w / 2), ny = (pos.getY(i) - bb.cy) / (bb.h / 2), z = pos.getZ(i);
      const zb = 3.4 * (1 - Math.max(0, 1 - nx * nx) * Math.max(0, 1 - ny ** 8));
      pos.setZ(i, zb + z * (Z1 - zb) / Z1);
    }
    bgeo.computeVertexNormals();
    add(bg, new THREE.Mesh(bgeo, [mat({ map: tex('back_cover_back.webp', BP.w, BP.h, true), roughness: 0.55 }), blue]));
    const inner = new THREE.Mesh(new THREE.ShapeGeometry(inset(BP.outline, 0.6)), mat({ map: tex('back_cover_front.webp', BP.w, BP.h), alphaTest: 0.5 }));
    inner.position.z = Z1 + 0.02; add(bg, inner);
    center(bg, BP);

    // Batteria BLC-1 nel vano.
    const bat = layer(3.8, -48), batg = new THREE.Group(); bat.add(batg);
    slab(batg, P.battery, 'battery', 5.6, 0x3a3a3a, { roughness: 0.75 });
    center(batg, P.battery, -20);

    // Chassis interno.
    const ch = layer(9.6, -28), chg = new THREE.Group(); ch.add(chg);
    slab(chg, P.chassis, 'chassis', 5.2, 0x9a9da2, { roughness: 0.45, metalness: 0.3 });
    center(chg, P.chassis);

    // PCB con le 6 viti Torx T6.
    const pcb = layer(14.8, -10), pg = new THREE.Group(); pcb.add(pg);
    slab(pg, P.pcb, 'pcb', 1.0, 0x2c4a2e, { roughness: 0.45, metalness: 0.15 });
    center(pg, P.pcb);
    const screwMat = mat({ color: 0x9a9ca0, metalness: 0.85, roughness: 0.35 });
    const head = new THREE.CylinderGeometry(1.25, 1.25, 0.9, 20).rotateX(Math.PI / 2);
    const shaft = new THREE.CylinderGeometry(0.75, 0.75, 6, 12).rotateX(Math.PI / 2);
    const star = new THREE.MeshBasicMaterial({ color: 0x202022, side: THREE.DoubleSide });
    for (const [x, y] of [[-18.5, 47], [18.5, 47], [-19.8, 2], [19.8, 2], [-18, -45], [18, -45]]) {
      const s = new THREE.Group(); s.position.set(x, y, -0.45);
      s.add(new THREE.Mesh(head, screwMat));
      const sh = new THREE.Mesh(shaft, screwMat); sh.position.z = 3; s.add(sh);
      for (let a = 0; a < 3; a++) { const b = new THREE.Mesh(new THREE.PlaneGeometry(1.3, 0.28), star); b.rotation.z = a * Math.PI / 3; b.position.z = -0.46; s.add(b); }
      pcb.add(s);
    }

    // Telaio UI con LCD vivo.
    const ui = layer(16.0, 10), ug = new THREE.Group(); ui.add(ug);
    slab(ug, P.ui_frame, 'ui_frame', 3.4, 0xe8e8e8, { roughness: 0.55 });
    center(ug, P.ui_frame);
    lcdTex = new THREE.CanvasTexture(document.getElementById('lcd'));
    lcdTex.colorSpace = THREE.SRGBColorSpace;
    const lw = CW * 0.6846, lh = CH * 0.2101, lx = -CW / 2 + CW * (0.1524 + 0.6846 / 2), ly = CH / 2 - CH * (0.2601 + 0.2101 / 2);
    const lcd = new THREE.Mesh(new THREE.PlaneGeometry(lw, lh), new THREE.MeshBasicMaterial({ map: lcdTex }));
    lcd.position.set(lx, ly, 20.4 - 16.0); ui.add(lcd);
    const lcdBox = new THREE.Mesh(new THREE.BoxGeometry(lw + 1, lh + 1, 1), mat({ color: 0x1a1a1a }));
    lcdBox.position.set(lx, ly, 20.4 - 16.0 - 0.52); ui.add(lcdBox);

    // Tappetino in gomma: base sottile e tasti in rilievo che escono dai fori della cover.
    const km = layer(19.9, 26), kg = new THREE.Group(); km.add(kg);
    slab(kg, P.keymat, 'keymat', 0.6, 0x9a9ea6, { roughness: 0.85 });
    const hb = C.holes.reduce((a, h) => { const b = bbox(h); return { y0: Math.min(a.y0, b.y0), y1: Math.max(a.y1, b.y1) }; }, { y0: 1e9, y1: -1e9 });
    const kb = bbox(P.keymat.outline);
    kg.position.set(cb.cx - kb.cx, (hb.y0 + hb.y1) / 2 - kb.cy - 1, 0);
    const faceTex = tex('front_cover_front.webp', CW, CH);
    const rubber = mat({ map: tex('front_cover_keys.webp', CW, CH), roughness: 0.75 });
    const keySide = mat({ color: 0xb0b4ba, roughness: 0.8 });
    for (const h of C.holes) {
      const b = bbox(h), d = 0.35, r = 0.35;
      const g = new THREE.ExtrudeGeometry(toPath(h, (b.w - 2 * (d + r)) / b.w, (b.h - 2 * (d + r)) / b.h, b.cx, b.cy), { depth: 2.1 - 2 * r, bevelEnabled: true, bevelThickness: r, bevelSize: r, bevelSegments: 3, curveSegments: 2 });
      g.translate(0, 0, 0.6 + r);
      keyMeshes.push(add(km, new THREE.Mesh(g, [rubber, keySide])));
    }

    // Cover frontale: faccia con fori reali e targhetta AurI, fianchi arrotondati, tasto Power in alto.
    const front = layer(0, 48);
    const faceShape = toPath(C.outline);
    for (const h of C.holes) faceShape.holes.push(toPath(h, 1, 1, 0, 0, THREE.Path));
    const wx0 = lx - lw / 2, wy0 = ly - lh / 2, r = 1.2, win = new THREE.Path();
    win.moveTo(wx0 + r, wy0); win.lineTo(wx0 + lw - r, wy0); win.quadraticCurveTo(wx0 + lw, wy0, wx0 + lw, wy0 + r); win.lineTo(wx0 + lw, wy0 + lh - r); win.quadraticCurveTo(wx0 + lw, wy0 + lh, wx0 + lw - r, wy0 + lh);
    win.lineTo(wx0 + r, wy0 + lh); win.quadraticCurveTo(wx0, wy0 + lh, wx0, wy0 + lh - r); win.lineTo(wx0, wy0 + r); win.quadraticCurveTo(wx0, wy0, wx0 + r, wy0);
    faceShape.holes.push(win);
    const T = 1.2;
    const fgeo = new THREE.ExtrudeGeometry(faceShape, { depth: T, bevelEnabled: false, curveSegments: 4 });
    fgeo.translate(0, 0, FACE - T);
    const rmTex = tex('front_cover_rm.webp', CW, CH, false, false);
    const faceMat = mat({ map: faceTex, roughnessMap: rmTex, metalnessMap: rmTex, roughness: 1, metalness: 1, alphaTest: 0.5, envMapIntensity: 0.5 });
    coverFace = add(front, new THREE.Mesh(fgeo, [faceMat, blue]));
    const FP = P.front_cover, fb = bbox(FP.outline);
    const cin = new THREE.Mesh(new THREE.ShapeGeometry(toPath(FP.outline)), mat({ map: tex('front_cover_back.webp', FP.w, FP.h, true), alphaTest: 0.5, side: THREE.BackSide }));
    cin.position.set(cb.cx - fb.cx, cb.cy - fb.cy, FACE - T - 0.02); add(front, cin);
    const wall = inset(C.outline, 0.9); wall.holes.push(inset(C.outline, 2.2, THREE.Path));
    const wgeo = new THREE.ExtrudeGeometry(wall, { depth: FACE - T - 9 - 1.8, bevelEnabled: true, bevelThickness: 0.9, bevelSize: 0.9, bevelSegments: 4, curveSegments: 2 });
    wgeo.translate(0, 0, 9 + 0.9);
    add(front, new THREE.Mesh(wgeo, blue));
    const glass = new THREE.Mesh(new THREE.PlaneGeometry(lw, lh), new THREE.MeshPhysicalMaterial({ color: 0xffffff, transparent: true, opacity: 0.08, roughness: 0.05, envMapIntensity: 1.2, depthWrite: false }));
    glass.position.set(lx, ly, FACE - 0.3); front.add(glass);
    power = new THREE.Mesh(new THREE.BoxGeometry(9, 2, 4.5), mat({ color: 0x15161b, roughness: 0.8 }));
    power.position.set(0, cb.y1 + 0.2, 16.5); add(front, power);
    applyExplode(); invalidate();
  }

  const applyExplode = () => { for (const g of layers) g.position.z = g.userData.z + g.userData.spread * explode; };

  // Il canvas si sovrappone alla vista 2D: a Smonta 0 la faccia frontale coincide col box di #phone.
  const phoneEl = document.getElementById('phone');
  let placed = false;
  function resize() {
    const r = phoneEl.getBoundingClientRect();
    if (!r.width) return;
    const cx = r.left + scrollX + r.width / 2, cy = r.top + scrollY + r.height / 2;
    const half = Math.min(r.width * 1.3, cx - 4, document.documentElement.clientWidth - cx - 4);
    const w = Math.max(r.width, 2 * half), h = r.height * 1.3;
    Object.assign(container.style, { left: cx - w / 2 + 'px', top: cy - h / 2 + 'px', width: w + 'px', height: h + 'px' });
    renderer.setSize(w, h);
    camera.aspect = w / h;
    // distanza perche' CH mm sul piano z=FACE valgano r.height px
    dist = (h * CH / r.height) / 2 / Math.tan(FOV * Math.PI / 360) + FACE - TARGET.z;
    camera.updateProjectionMatrix();
    if (!placed) { camera.position.set(0, 0, TARGET.z + dist); camera.up.set(0, 1, 0); placed = true; }
    else camera.position.sub(TARGET).setLength(dist).add(TARGET);
    controls.minDistance = dist * 0.4; controls.maxDistance = dist * 2.5;
    invalidate();
  }
  addEventListener('resize', resize);
  new ResizeObserver(resize).observe(document.body);
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
    if (explode !== explodeTarget) {
      explode = Math.abs(explodeTarget - explode) < 1e-3 ? explodeTarget : explode + (explodeTarget - explode) * 0.15;
      applyExplode(); needs = true;
    }
    if (lcdTex && now - lastLcd > 66) { lastLcd = now; lcdTex.needsUpdate = true; needs = true; }
    if (needs) { needs = false; renderer.render(scene, camera); }
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
  renderer.domElement.addEventListener('pointerdown', e => {
    const k = pick(e);
    if (!k) return;
    e.stopImmediatePropagation(); e.preventDefault();
    controls.enabled = false; downKey = k;
    renderer.domElement.setPointerCapture(e.pointerId);
    if (k === 'power') power.position.y -= 0.6;
    invalidate(); press(k);
  }, { capture: true });
  const up = () => {
    if (!downKey) return;
    release(downKey); if (downKey === 'power') power.position.y += 0.6;
    downKey = null; controls.enabled = true; invalidate();
  };
  renderer.domElement.addEventListener('pointerup', up);
  renderer.domElement.addEventListener('pointercancel', up);
  renderer.domElement.addEventListener('pointermove', e => {
    if (downKey) return;
    renderer.domElement.style.cursor = pick(e) ? 'pointer' : 'grab';
  });

  return {
    show(on) { visible = on; if (on) { resize(); invalidate(); } },
    view,
    setExplode(v) { explodeTarget = v; },
    get loading() { return pending > 0; },
    ready,
  };
}
