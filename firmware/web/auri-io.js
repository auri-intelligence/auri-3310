// Simulated sensors and push-to-talk microphone for the web simulator.
(() => {
  const sens = { temperature: 21.5, humidity: 48, pressure: 1013, light: 120 };
  const NAMES = { temperature: 'Temperatura', humidity: 'Umidita', pressure: 'Pressione', light: 'Luce' };
  const RANGES = { temperature: [-10, 45, 0.1, '°C'], humidity: [0, 100, 1, '%'], pressure: [950, 1060, 1, 'hPa'], light: [0, 2000, 10, 'lx'] };

  window.auriSensors = () => JSON.stringify(sens);

  // Simulated battery: the charger raises the level by 1% every 2 s, like a real charge but faster.
  const bat = { pct: 80, chg: false };
  window.auriBattery = () => `${Math.round(bat.pct)},${bat.chg ? 1 : 0}`;
  let batUi = null;
  setInterval(() => { if (bat.chg && bat.pct < 100) { bat.pct++; batUi?.(); } }, 2000);

  addEventListener('DOMContentLoaded', () => {
    const host = document.querySelector('aside');
    if (!host) return;
    const box = document.createElement('fieldset');
    box.innerHTML = '<legend>Sensori simulati</legend>';
    for (const [k, [min, max, step, unit]] of Object.entries(RANGES)) {
      const row = document.createElement('label');
      row.innerHTML = `${NAMES[k]} <output>${sens[k]} ${unit}</output><input type="range" min="${min}" max="${max}" step="${step}" value="${sens[k]}">`;
      const inp = row.querySelector('input'), out = row.querySelector('output');
      inp.addEventListener('input', () => { sens[k] = parseFloat(inp.value); out.textContent = `${sens[k]} ${unit}`; });
      box.appendChild(row);
    }
    const brow = document.createElement('label');
    brow.innerHTML = 'Batteria <output></output><input type="range" min="0" max="100" step="1">';
    const bin = brow.querySelector('input'), bout = brow.querySelector('output');
    batUi = () => { bin.value = bat.pct; bout.textContent = `${bat.pct} %${bat.chg ? ' +' : ''}`; };
    bin.addEventListener('input', () => { bat.pct = parseInt(bin.value); batUi(); });
    box.appendChild(brow);
    const crow = document.createElement('label');
    crow.style.display = 'flex';
    crow.innerHTML = '<input type="checkbox"> Caricatore collegato';
    crow.querySelector('input').addEventListener('change', e => { bat.chg = e.target.checked; batUi(); });
    box.appendChild(crow);
    batUi();
    const p = document.createElement('p');
    p.textContent = 'Accensione: tieni premuto il tasto in alto sulla cover (o P). Voce: tieni premuto Navi.';
    box.appendChild(p);
    host.appendChild(box);
  });

  let ctx, stream, node, chunks = [], result = '', recording = false;

  // Chrome keeps an AudioContext suspended unless it is created or resumed inside a user gesture,
  // and push-to-talk starts from the simulator loop, so the audio graph is prepared on the first click/key.
  async function prepare() {
    if (!ctx) ctx = new AudioContext();
    if (ctx.state !== 'running') await ctx.resume();
    if (!stream) {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      const src = ctx.createMediaStreamSource(stream);
      node = ctx.createScriptProcessor(4096, 1, 1);
      node.onaudioprocess = e => { if (recording) chunks.push(new Float32Array(e.inputBuffer.getChannelData(0))); };
      src.connect(node); node.connect(ctx.destination);
    }
  }
  const gesture = () => prepare().catch(e => { result = JSON.stringify({ error: 'Microfono: ' + e.message }); });
  addEventListener('pointerdown', gesture, { once: true });
  addEventListener('keydown', gesture, { once: true });

  window.auriVoiceStart = () => {
    chunks = []; result = '';
    recording = true;
    prepare().catch(e => { recording = false; result = JSON.stringify({ error: 'Microfono: ' + e.message }); });
    return true;
  };

  function pcm16k() {
    const rate = ctx ? ctx.sampleRate : 16000;
    const all = new Float32Array(chunks.reduce((n, c) => n + c.length, 0));
    let o = 0; for (const c of chunks) { all.set(c, o); o += c.length; }
    const n = Math.floor(all.length * 16000 / rate), out = new Int16Array(n);
    for (let i = 0; i < n; i++) out[i] = Math.max(-1, Math.min(1, all[Math.floor(i * rate / 16000)])) * 32767;
    let bin = ''; const b = new Uint8Array(out.buffer);
    for (let i = 0; i < b.length; i += 0x8000) bin += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
    return btoa(bin);
  }

  window.auriVoiceStop = (url, params, token) => {
    recording = false;
    if (result) return;
    if (!chunks.length) { result = JSON.stringify({ error: 'Audio vuoto: controlla il microfono' }); return; }
    const body = Object.assign(JSON.parse(params), { audio: pcm16k(), rate: 16000 });
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = 'Bearer ' + token;
    fetch(url, { method: 'POST', headers, body: JSON.stringify(body) })
      .then(r => r.json())
      .then(r => {
        if (r.audio) new Audio('data:audio/wav;base64,' + r.audio).play().catch(() => {});
        delete r.audio;
        result = JSON.stringify(r);
      })
      .catch(e => { result = JSON.stringify({ error: 'Bridge: ' + e.message }); });
  };

  window.auriVoicePoll = () => { const r = result; if (r) result = ''; return r; };
})();
