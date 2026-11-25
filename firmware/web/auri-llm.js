// Cervello locale di AurI per il simulatore: un modello di linguaggio piccolo che gira dentro il
// browser con WebGPU (WebLLM), piu' la voce del browser (ascolto e lettura). Niente chiavi, niente
// server, niente costi: i pesi arrivano una volta sola da HuggingFace e restano nella cache del browser.
//
// Dalla parte del telefono (MicroPython) si usano solo queste funzioni, tutte non bloccanti:
//   auriAiInfo()             stato del cervello, in JSON
//   auriAiStart(chiave)      scarica e accende il modello scelto
//   auriAiAsk(messaggi)      manda la domanda (JSON: [{role, content}, ...])
//   auriAiPoll()             testo generato finora, in JSON
//   auriAiStop()             ferma la generazione
//   auriHearStart/Stop/Poll  ascolto (push-to-talk) col riconoscimento vocale del browser
//   auriSpeak(testo, lingua) legge la risposta ad alta voce
(() => {
  const WEBLLM = 'https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.88/lib/index.js';

  // Solo modelli con licenza libera (Apache 2.0). "mb" = quanto si scarica, una volta sola.
  // Le versioni f16 chiedono la funzione "shader-f16" della GPU; dove manca si usa la f32, piu' grande.
  const MODELS = {
    mini: { name: 'Mini 360M', mb: 207, f16: 'SmolLM2-360M-Instruct-q4f16_1-MLC', f32: 'SmolLM2-360M-Instruct-q4f32_1-MLC' },
    base: { name: 'Base 0.5B', mb: 290, f16: 'Qwen2.5-0.5B-Instruct-q4f16_1-MLC', f32: 'Qwen2.5-0.5B-Instruct-q4f32_1-MLC' },
    pensa: { name: 'Pensa 0.6B', mb: 352, f16: 'Qwen3-0.6B-q4f16_1-MLC', f32: 'Qwen3-0.6B-q4f32_1-MLC', think: true },
    grande: { name: 'Grande 1.5B', mb: 880, f16: 'Qwen2.5-1.5B-Instruct-q4f16_1-MLC', f32: 'Qwen2.5-1.5B-Instruct-q4f32_1-MLC' },
  };
  // Su smartphone il browser limita la memoria della GPU (buffer da 128 MB): il modello piccolo e'
  // l'unico che gira davvero, e si scarica meno anche sotto rete mobile.
  const MOBILE = (navigator.userAgentData && navigator.userAgentData.mobile)
    || /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || '');
  const DEFAULT = MOBILE ? 'mini' : 'base';

  const st = {
    key: DEFAULT,        // modello scelto
    phase: 'off',        // off | load | ready | gen | err
    pct: 0,
    note: '',
    error: '',
    text: '',            // risposta in arrivo, pezzo per pezzo
    done: true,
    tps: 0,
    speak: true,
  };
  let gpuName = '', gpuSoft = false;
  let engine = null, worker = null, webllm = null, f16 = null, stop = false, gen = 0;

  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} },
  };
  const saved = store.get('auri.cervello.modello', DEFAULT);
  st.key = MODELS[saved] ? saved : DEFAULT;
  st.speak = store.get('auri.cervello.voce', '1') === '1';

  const track = n => { try { window.auriTrack && window.auriTrack(n); } catch {} };
  let ui = null;   // funzione che aggiorna il pannello a destra

  // --- GPU ---------------------------------------------------------------
  async function checkGpu() {
    // Fuori da https (e da localhost) il browser nasconde WebGPU e il microfono: capita a chi apre
    // il simulatore dal telefono con l'indirizzo IP del PC.
    if (!window.isSecureContext) return { ok: false, reason: 'no_https' };
    if (!navigator.gpu) return { ok: false, reason: 'no_webgpu' };
    let a = null;
    // su qualche dispositivo la richiesta non risponde mai: dopo 5 s si rinuncia
    try {
      a = await Promise.race([navigator.gpu.requestAdapter(), new Promise(r => setTimeout(() => r(null), 5000))]);
    } catch (e) { return { ok: false, reason: 'no_webgpu' }; }
    if (!a) return { ok: false, reason: 'no_webgpu' };
    f16 = !!(a.features && a.features.has && a.features.has('shader-f16'));
    // Che scheda grafica stiamo usando? Se e' quella finta (software) il modello va a passo d'uomo:
    // meglio dirlo prima di far scaricare 290 MB.
    try {
      const info = a.info || (a.requestAdapterInfo ? await a.requestAdapterInfo() : null);
      if (info) {
        gpuName = [info.vendor, info.architecture || info.device, info.description]
          .filter(Boolean).join(' ').trim().slice(0, 60);
      }
    } catch (e) {}
    gpuSoft = !!a.isFallbackAdapter || /swiftshader|llvmpipe|software|basic render/i.test(gpuName);
    // Senza "shader-f16" si usa la versione f32: piu' grande da scaricare e parecchio piu' lenta.
    // Se l'utente non ha scelto un modello a mano, si parte dal piu' piccolo.
    if (!f16 && !store.get('auri.cervello.modello', '')) st.key = 'mini';
    return { ok: true, reason: '' };
  }

  window.auriAiGpu = () => JSON.stringify({ name: gpuName, soft: gpuSoft ? 1 : 0, f16: f16 === false ? 0 : 1 });

  function modelId(key) {
    const m = MODELS[key] || MODELS[DEFAULT];
    return f16 === false ? m.f32 : m.f16;
  }

  // --- accensione del cervello -------------------------------------------
  async function start(key) {
    if (st.phase === 'load') return;
    if (key && MODELS[key]) { st.key = key; store.set('auri.cervello.modello', key); }
    const gpu = await checkGpu();
    if (!gpu.ok) {
      st.phase = 'err';
      st.error = gpu.reason;
      if (ui) ui();
      track('cervello/no_webgpu');
      return;
    }
    st.phase = 'load';
    st.pct = 0;
    st.note = '';
    st.error = '';
    if (ui) ui();
    track('cervello/accendi');
    try {
      if (!webllm) webllm = await import(WEBLLM);
      if (!worker) worker = new Worker('auri-llm-worker.js?v=' + Date.now(), { type: 'module' });
      const cb = r => {
        // r.progress va da 0 a 1 durante lo scaricamento e la compilazione
        st.pct = Math.max(0, Math.min(100, Math.round((r.progress || 0) * 100)));
        st.note = String(r.text || '').slice(0, 120);
        if (ui) ui();
      };
      const id = modelId(st.key);
      // Sui browser dei telefoni la memoria della GPU e' limitata (buffer da 128 MB): con una
      // finestra di contesto piu' corta il modello ci sta, con quella piena fallisce e basta.
      const chatOpts = { context_window_size: MOBILE ? 1024 : 2048 };
      if (engine) {
        engine.setInitProgressCallback(cb);
        await engine.reload(id, chatOpts);
      } else {
        engine = await webllm.CreateWebWorkerMLCEngine(worker, id, { initProgressCallback: cb }, chatOpts);
      }
      st.phase = 'ready';
      st.pct = 100;
      st.note = '';
      if (ui) ui();
      track('cervello/pronto');
    } catch (e) {
      st.phase = 'err';
      st.error = String((e && e.message) || e).slice(0, 200);
      if (ui) ui();
      track('cervello/errore');
    }
  }

  // --- domanda e risposta -------------------------------------------------
  // Quanto e' gia' stato letto ad alta voce della risposta in arrivo.
  function pezzoDaLeggere(resto, finita) {
    const m = /^[\s\S]*?[.!?:;\u2026](\s|$)/.exec(resto);   // fino alla fine della prima frase
    if (m) return m[0];
    if (finita) return resto;
    if (resto.length > 110) {                 // frase lunghissima senza punteggiatura: si spezza
      const i = resto.lastIndexOf(' ');
      if (i > 50) return resto.slice(0, i + 1);
    }
    return '';
  }

  async function ask(messages, opts) {
    const mine = ++gen;
    stop = false;
    st.text = '';
    st.done = false;
    st.error = '';
    st.phase = 'gen';
    st.tps = 0;
    if (ui) ui();
    const t0 = performance.now();
    let n = 0;
    // voce in diretta: si legge ogni frase appena e' finita, senza aspettare tutta la risposta
    const vivavoce = !!(opts && opts.speak) && st.speak;
    st.spoken = vivavoce;
    const lingua = (opts && opts.lang) || 'it';
    let letto = 0;
    const leggiAvanti = finita => {
      if (!vivavoce) return;
      const pezzo = pezzoDaLeggere(st.text.slice(letto), finita);
      if (pezzo && pezzo.trim()) {
        letto += pezzo.length;
        window.auriSpeakNext(pezzo.trim(), lingua);
      }
    };
    try {
      const req = {
        messages,
        stream: true,
        temperature: (opts && opts.temperature) || 0.5,
        top_p: 0.9,
        max_tokens: (opts && opts.max_tokens) || 150,
      };
      // Qwen3 di suo "ragiona" ad alta voce: su un display di 14 colonne non serve.
      if ((MODELS[st.key] || {}).think) req.extra_body = { enable_thinking: false };
      const out = await engine.chat.completions.create(req);
      for await (const chunk of out) {
        if (mine !== gen) return;
        if (stop) {
          try { await engine.interruptGenerate(); } catch (e) {}
          break;
        }
        const ch = chunk.choices && chunk.choices[0];
        const d = (ch && ch.delta && ch.delta.content) || '';
        if (d) {
          st.text += d;
          n++;
          leggiAvanti(false);
          if (ui) ui();
        }
      }
      leggiAvanti(true);
      const ms = performance.now() - t0;
      st.tps = n && ms > 0 ? Math.round(n * 1000 / ms * 10) / 10 : 0;
      track('cervello/risposta');
    } catch (e) {
      if (mine === gen) st.error = String((e && e.message) || e).slice(0, 200);
    }
    if (mine !== gen) return;
    st.done = true;
    st.phase = 'ready';
    if (ui) ui();
  }

  // --- interfaccia per il telefono ---------------------------------------
  window.auriAiInfo = () => JSON.stringify({
    phase: st.phase, pct: st.pct, key: st.key, name: (MODELS[st.key] || {}).name || '?',
    mb: (MODELS[st.key] || {}).mb || 0, error: st.error, note: st.note,
    webgpu: !!navigator.gpu, speak: st.speak, tps: st.tps, gpu: gpuName, slow: gpuSoft ? 1 : 0,
    hear: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
  });

  window.auriAiStart = key => { start(key || st.key); return ''; };

  window.auriAiAsk = (messagesJson, optsJson) => {
    if (st.phase !== 'ready') return 'non pronto';
    let msgs;
    let opts = {};
    try { msgs = JSON.parse(messagesJson); } catch (e) { return 'messaggi non validi'; }
    if (optsJson) { try { opts = JSON.parse(optsJson) || {}; } catch (e) {} }
    ask(msgs, opts);
    return '';
  };

  window.auriAiPoll = () => JSON.stringify({ text: st.text, done: st.done ? 1 : 0, error: st.error,
    tps: st.tps, spoken: st.spoken ? 1 : 0 });

  window.auriAiStop = () => {
    stop = true;
    gen++;
    try { if (st.spoken) speechSynthesis.cancel(); } catch (e) {}
    st.done = true;
    if (st.phase === 'gen') st.phase = 'ready';
    if (ui) ui();
    return '';
  };

  window.auriAiModels = () => JSON.stringify(Object.keys(MODELS).map(k => [k, MODELS[k].name, MODELS[k].mb]));

  // --- voce: ascolto (riconoscimento del browser) ------------------------
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const LANGS = { it: 'it-IT', en: 'en-US', es: 'es-ES', fr: 'fr-FR', de: 'de-DE', pt: 'pt-PT' };
  let rec = null, heard = '', hearDone = true, hearErr = '';

  window.auriHearStart = lang => {
    if (!SR) return 0;
    heard = '';
    hearErr = '';
    hearDone = false;
    try {
      rec = new SR();
      rec.lang = LANGS[String(lang || 'it')] || 'it-IT';
      rec.interimResults = true;
      rec.continuous = false;
      rec.maxAlternatives = 1;
      rec.onresult = e => {
        let s = '';
        for (let i = 0; i < e.results.length; i++) s += e.results[i][0].transcript;
        heard = s.trim();
      };
      rec.onerror = e => {
        const c = String(e.error || 'errore');
        // 'not-allowed' vuol dire permesso negato: sul display si dice come si rimedia
        hearErr = (c === 'not-allowed' || c === 'service-not-allowed') ? 'no_mic' : c;
        hearDone = true;
      };
      rec.onend = () => { hearDone = true; };
      rec.start();
      return 1;
    } catch (e) {
      hearErr = String((e && e.message) || e);
      hearDone = true;
      return 0;
    }
  };

  window.auriHearStop = () => { try { if (rec) rec.stop(); } catch (e) {} return ''; };

  // Il permesso del microfono va chiesto dentro un tocco dell'utente, se no su iPhone il
  // riconoscimento parte e muore subito. Il pulsante del pannello serve a questo.
  window.auriMicPermesso = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return 'no_mic';
    try {
      const flusso = await navigator.mediaDevices.getUserMedia({ audio: true });
      flusso.getTracks().forEach(t => t.stop());
      return '';
    } catch (e) {
      return String((e && e.name) || e);
    }
  };

  window.auriHearPoll = () => JSON.stringify({ text: heard, done: hearDone ? 1 : 0, error: hearErr });

  // --- voce: lettura ad alta voce -----------------------------------------
  // Safari e Chrome vogliono un gesto dell'utente prima di parlare: si scalda al primo tocco.
  let warm = false;
  const warmUp = () => {
    if (warm || !window.speechSynthesis) return;
    warm = true;
    try {
      const u = new SpeechSynthesisUtterance(' ');
      u.volume = 0;
      speechSynthesis.speak(u);
    } catch (e) {}
  };
  addEventListener('pointerdown', warmUp, { once: true });
  addEventListener('keydown', warmUp, { once: true });

  function voiceFor(code) {
    const want = (LANGS[String(code || 'it')] || 'it-IT').slice(0, 2).toLowerCase();
    const all = speechSynthesis.getVoices() || [];
    return all.find(v => v.lang && v.lang.toLowerCase().startsWith(want)) || null;
  }

  // Legge un pezzo mettendolo in coda, senza interrompere quello che sta dicendo: serve per
  // parlare frase per frase mentre il modello sta ancora scrivendo il resto.
  window.auriSpeakNext = (text, lang) => {
    if (!st.speak || !window.speechSynthesis || !text) return '';
    try {
      const u = new SpeechSynthesisUtterance(String(text));
      const v = voiceFor(lang);
      if (v) u.voice = v;
      u.lang = (v && v.lang) || 'it-IT';
      u.rate = 1.05;
      speechSynthesis.speak(u);
    } catch (e) {}
    return '';
  };

  window.auriSpeak = (text, lang) => {
    if (!st.speak || !window.speechSynthesis || !text) return '';
    try {
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(String(text));
      const v = voiceFor(lang);
      if (v) u.voice = v;
      u.lang = (v && v.lang) || 'it-IT';
      u.rate = 1.05;
      speechSynthesis.speak(u);
    } catch (e) {}
    return '';
  };

  window.auriSpeakStop = () => { try { speechSynthesis.cancel(); } catch (e) {} return ''; };

  // --- pannello del simulatore -------------------------------------------
  addEventListener('DOMContentLoaded', () => {
    const host = document.querySelector('aside');
    if (!host) return;
    const box = document.createElement('fieldset');
    box.innerHTML = '<legend>Cervello AurI (nel browser, gratis)</legend>';

    const row = document.createElement('label');
    row.style.cssText = 'display:flex;gap:8px';
    row.innerHTML = '<select style="flex:1"></select><button type="button">Accendi</button>';
    const sel = row.querySelector('select'), btn = row.querySelector('button');
    for (const [k, m] of Object.entries(MODELS)) {
      const o = document.createElement('option');
      o.value = k;
      o.textContent = m.name + ' · ' + m.mb + ' MB';
      sel.appendChild(o);
    }
    sel.value = st.key;
    sel.addEventListener('change', () => {
      st.key = sel.value;
      store.set('auri.cervello.modello', st.key);
      upd();
    });
    btn.addEventListener('click', () => start(sel.value));
    box.appendChild(row);

    const bar = document.createElement('div');
    bar.style.cssText = 'height:6px;border-radius:3px;background:rgba(255,255,255,.08);margin:8px 0;overflow:hidden';
    bar.innerHTML = '<div style="height:100%;width:0;background:var(--accent);transition:width .2s"></div>';
    box.appendChild(bar);

    const msg = document.createElement('p');
    msg.style.cssText = 'margin:4px 0;font-size:12px';
    box.appendChild(msg);

    const vrow = document.createElement('label');
    vrow.style.display = 'flex';
    vrow.innerHTML = '<input type="checkbox"> Leggi le risposte a voce';
    const vin = vrow.querySelector('input');
    vin.checked = st.speak;
    vin.addEventListener('change', () => {
      st.speak = vin.checked;
      store.set('auri.cervello.voce', st.speak ? '1' : '0');
    });
    box.appendChild(vrow);

    // Prova del microfono: un tocco vero, cosi' il permesso si puo' chiedere davvero
    const mrow = document.createElement('p');
    mrow.style.cssText = 'margin:8px 0 0;font-size:12px;display:flex;gap:8px;align-items:center';
    mrow.innerHTML = '<button type="button">Prova il microfono</button><span></span>';
    const mbtn = mrow.querySelector('button'), mmsg = mrow.querySelector('span');
    const SRok = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    mbtn.addEventListener('click', async () => {
      mmsg.textContent = 'chiedo il permesso...';
      const err = await window.auriMicPermesso();
      if (!err) {
        mmsg.textContent = SRok ? 'microfono ok: sul telefono tieni premuto Navi e parla'
                                : 'microfono ok, ma questo browser non sa trascrivere: scrivi col T9';
      } else if (err === 'no_mic' || !window.isSecureContext) {
        mmsg.textContent = 'niente microfono qui: serve https (o il sito pubblico)';
      } else {
        mmsg.textContent = 'permesso negato: si scrive col T9';
      }
      track('cervello/microfono');
    });
    box.appendChild(mrow);

    const note = document.createElement('p');
    note.style.cssText = 'margin:6px 0 0;font-size:11px;color:var(--muted)';
    note.textContent = 'Il modello (Qwen o SmolLM2, licenza Apache 2.0) si scarica una volta sola e resta nella cache '
      + 'del browser: da quel momento AurI risponde senza server e senza chiavi. Serve un browser con WebGPU '
      + '(Chrome o Edge aggiornati). Sul telefono: tieni premuto Navi per parlare, premilo breve per scrivere col T9. '
      + 'L ascolto usa il riconoscimento vocale del browser, che su Chrome passa dai server di Google; il modello e la '
      + 'lettura ad alta voce restano sul dispositivo.';
    box.appendChild(note);
    host.appendChild(box);

    function upd() {
      const m = MODELS[st.key] || {};
      if (sel.value !== st.key) sel.value = st.key;   // il menu segue il modello davvero scelto
      const full = st.phase === 'ready' || st.phase === 'gen';
      bar.firstChild.style.width = (st.phase === 'load' ? st.pct : full ? 100 : 0) + '%';
      btn.disabled = st.phase === 'load';
      btn.textContent = full ? 'Ricarica' : 'Accendi';
      if (!window.isSecureContext) {
        msg.textContent = 'Serve una connessione sicura (https): dal telefono apri il sito pubblico, '
          + 'qui il browser non da ne il cervello ne il microfono.';
      } else if (!navigator.gpu) {
        msg.textContent = MOBILE
          ? 'Questo telefono non ha WebGPU: serve Chrome su Android 12+ o Safari su iOS 26.'
          : 'Questo browser non ha WebGPU: prova Chrome o Edge aggiornati.';
      } else if (st.phase === 'off') {
        const rete = navigator.connection || {};
        const cara = rete.saveData || /^(2g|3g|slow-2g)$/.test(rete.effectiveType || '');
        msg.textContent = 'Spento. Premi Accendi: scarica ' + (m.mb || '?') + ' MB una volta sola.'
          + (cara ? ' Attenzione: sei sotto rete mobile, meglio il Wi-Fi.' : '')
          + (gpuSoft ? ' Attenzione: qui WebGPU gira senza scheda grafica, sara molto lento.'
             : f16 === false ? ' La tua scheda non ha shader-f16: il modello gira nella versione pesante'
                               + ' e lenta. Meglio Mini, o il bridge di casa.'
             : gpuName ? ' Scheda grafica: ' + gpuName + '.' : '');
      } else if (st.phase === 'load') {
        msg.textContent = 'Scarico e accendo ' + m.name + ': ' + st.pct + '%' + (st.note ? ' — ' + st.note : '');
      } else if (st.phase === 'gen') {
        msg.textContent = 'AurI sta rispondendo...';
      } else if (st.phase === 'err') {
        msg.textContent = st.error === 'no_webgpu' ? 'WebGPU non disponibile su questo dispositivo.'
          : st.error === 'no_https' ? 'Serve https: dal telefono apri il sito pubblico.'
          : 'Errore: ' + st.error;
      } else {
        msg.textContent = 'Pronto: ' + m.name + ' nel browser' + (st.tps ? ' · ' + st.tps + ' pezzi/s' : '')
          + (gpuSoft ? ' (senza scheda grafica: lento)' : f16 === false ? ' (senza shader-f16: lento)' : '');
      }
    }
    ui = upd;
    upd();
    if (navigator.gpu) checkGpu().then(upd).catch(() => {});
  });
})();
