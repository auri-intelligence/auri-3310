// Fotocamera del simulatore: telefono -> fotocamera posteriore, computer -> webcam.
// Ogni fotogramma diventa 84x48 a 1 bit come sul display vero (PCD8544):
// ritaglio "cover", scala di grigi, contrasto automatico, dithering (Atkinson come il Mac del 1984,
// oppure Bayer o soglia), impacchettato in 6 banchi da 84 byte (bit 0 = pixel in alto).
// Stessi conti di auri/dither.py, che fara' lo stesso lavoro sul Nokia vero.
(() => {
  const W = 84, H = 48;
  const mobile = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent) ||
    (navigator.maxTouchPoints > 1 && /Macintosh/.test(navigator.userAgent));
  let stream = null, video = null, err = '', facing = mobile ? 'environment' : 'user';
  let mode = 0, frame = '', seq = 0, busy = false, handle = 0;
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const cx = cv.getContext('2d', { willReadFrequently: true });
  const gray = new Float32Array(W * H);
  const out = new Uint8Array(W * H / 8);
  const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
  const hex = []; for (let i = 0; i < 256; i++) hex.push(i.toString(16).padStart(2, '0'));

  function process() {
    const vw = video.videoWidth, vh = video.videoHeight;
    if (!vw) return false;
    // ritaglio centrale con il rapporto del display (84:48 = 7:4)
    let sw = vw, sh = vw * H / W;
    if (sh > vh) { sh = vh; sw = vh * W / H; }
    const sx = (vw - sw) / 2, sy = (vh - sh) / 2;
    cx.save();
    if (facing === 'user') { cx.translate(W, 0); cx.scale(-1, 1); }   // la webcam fa da specchio
    cx.drawImage(video, sx, sy, sw, sh, 0, 0, W, H);
    cx.restore();
    const px = cx.getImageData(0, 0, W, H).data;
    // grigio + istogramma per il contrasto automatico (scarta l'1% piu' scuro e piu' chiaro)
    const hist = new Uint32Array(256);
    for (let i = 0, j = 0; i < W * H; i++, j += 4) {
      const v = (px[j] * 77 + px[j + 1] * 150 + px[j + 2] * 29) >> 8;
      gray[i] = v; hist[v]++;
    }
    const cut = W * H / 100;
    let lo = 0, hi = 255, acc = 0;
    while (lo < 255 && (acc += hist[lo]) < cut) lo++;
    acc = 0;
    while (hi > 0 && (acc += hist[hi]) < cut) hi--;
    const span = Math.max(24, hi - lo);
    for (let i = 0; i < W * H; i++) gray[i] = Math.min(255, Math.max(0, (gray[i] - lo) * 255 / span));
    out.fill(0);
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const i = y * W + x, v = gray[i];
        let on;
        if (mode === 1) on = v < (BAYER[(y & 3) * 4 + (x & 3)] + 0.5) * 16;
        else if (mode === 2) on = v < 128;
        else {
          on = v < 128;
          const e = (v - (on ? 0 : 255)) / 8;   // Atkinson: 6/8 dell'errore su 6 vicini
          if (x + 1 < W) gray[i + 1] += e;
          if (x + 2 < W) gray[i + 2] += e;
          if (y + 1 < H) {
            if (x > 0) gray[i + W - 1] += e;
            gray[i + W] += e;
            if (x + 1 < W) gray[i + W + 1] += e;
          }
          if (y + 2 < H) gray[i + 2 * W] += e;
        }
        if (on) out[(y >> 3) * W + x] |= 1 << (y & 7);   // 1 = pixel nero, come il display
      }
    }
    let s = '';
    for (let i = 0; i < out.length; i++) s += hex[out[i]];
    frame = s; seq++;
    return true;
  }

  function loop() {
    if (!video) return;
    process();
    handle = video.requestVideoFrameCallback ? video.requestVideoFrameCallback(loop) : requestAnimationFrame(loop);
  }

  async function open() {
    close();
    err = ''; busy = true;
    if (!window.isSecureContext) { err = 'no_https'; busy = false; return; }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { err = 'no_cam'; busy = false; return; }
    try {
      // bassa risoluzione: al display servono 84x48, cosi' consuma poco anche sul telefono
      stream = await navigator.mediaDevices.getUserMedia({
        audio: false, video: { facingMode: { ideal: facing }, width: { ideal: 320 }, height: { ideal: 240 }, frameRate: { ideal: 30 } },
      });
      video = document.createElement('video');
      video.muted = true; video.playsInline = true; video.setAttribute('playsinline', '');
      video.srcObject = stream;
      await video.play();
      loop();
    } catch (e) {
      err = (e && (e.name === 'NotAllowedError' || e.name === 'SecurityError')) ? 'denied' : 'no_cam';
      close();
    }
    busy = false;
  }

  function close() {
    if (stream) stream.getTracks().forEach(t => t.stop());
    stream = null; video = null; frame = '';
  }

  window.auriCamInfo = () => JSON.stringify({ ok: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia), mobile, facing, mode });
  window.auriCamStart = () => { open(); return true; };
  window.auriCamStop = () => close();
  window.auriCamSwitch = () => { facing = facing === 'user' ? 'environment' : 'user'; open(); };
  window.auriCamMode = m => { mode = m | 0; };
  // stato + ultimo fotogramma (esadecimale, 1008 caratteri); seq evita di ridisegnare lo stesso
  let last = -1;
  window.auriCamPoll = () => {
    const nuovo = seq !== last && frame;
    last = seq;
    return JSON.stringify({ on: !!video, busy, err, facing, frame: nuovo ? frame : '' });
  };
})();
