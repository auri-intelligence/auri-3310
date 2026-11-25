// Registro "parlante" del simulatore: frasi chiare su cosa succede, salvate a ogni secondo nel browser
// cosi' sopravvivono anche a un crash della scheda. Alla riapertura dice se l'ultima volta si e' chiuso
// di colpo e cosa stava facendo. Si legge nel pannello (Registro) o con auriLogText() dalla console.
// Resta solo in questo browser: niente viene mandato a nessun server.
(() => {
  const KEY = 'auri.registro', BEAT = 'auri.battito', MAX = 300;
  const t0 = performance.now();
  let righe = [];
  try { righe = JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) { righe = []; }
  let sporco = false;

  const ora = () => {
    const d = new Date();
    return d.toTimeString().slice(0, 8) + '.' + String(d.getMilliseconds()).padStart(3, '0');
  };
  let log = function (livello, area, testo) {
    const r = { t: ora(), l: livello, a: area, m: String(testo).slice(0, 400) };
    righe.push(r);
    if (righe.length > MAX) righe.splice(0, righe.length - MAX);
    sporco = true;
    (livello === 'ERR' ? console.error : livello === 'ATT' ? console.warn : console.log)(`[AurI ${area}] ${r.m}`);
    if (livello !== 'INFO') salva();      // errori e avvisi subito: potrebbe essere l'ultima cosa prima del crash
    if (window.auriLogUi) window.auriLogUi();
  };
  function salva() {
    if (!sporco) return;
    sporco = false;
    try { localStorage.setItem(KEY, JSON.stringify(righe)); } catch (e) {}
  }
  window.auriLog = (area, testo) => log('INFO', area, testo);
  window.auriWarn = (area, testo) => log('ATT', area, testo);
  window.auriErr = (area, testo) => log('ERR', area, testo);
  window.auriLogRows = () => righe;
  window.auriLogText = () => righe.map(r => `${r.t} ${r.l.padEnd(4)} ${r.a.padEnd(8)} ${r.m}`).join('\n');
  window.auriLogClear = () => { righe = []; sporco = true; salva(); if (window.auriLogUi) window.auriLogUi(); };

  // --- crash: battito ogni secondo; se alla riapertura il battito e' fermo e non c'e' stata una
  // chiusura pulita, la scheda e' morta (memoria finita, GPU, browser che l'ha uccisa) ---
  let prima = null;
  try { prima = JSON.parse(localStorage.getItem(BEAT) || 'null'); } catch (e) {}
  if (prima && !prima.pulito) {
    const fa = Math.round((Date.now() - prima.ts) / 1000);
    log('ERR', 'crash', `L'ultima volta il simulatore si e' chiuso di colpo (${fa} s fa) mentre era in "${prima.app || '?'}"` +
        (prima.fase ? `, cervello: ${prima.fase}` : '') + (prima.mem ? `, memoria JS ${prima.mem} MB` : '') +
        '. Probabile: il telefono ha finito la memoria o la GPU.');
  }
  log('INFO', 'avvio', `Pagina aperta: ${navigator.userAgent.replace(/\s+/g, ' ').slice(0, 160)}`);
  const mem = () => (performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : 0);
  function battito(pulito) {
    let fase = '';
    try { fase = JSON.parse(window.auriAiInfo ? window.auriAiInfo() : '{}').phase || ''; } catch (e) {}
    try {
      localStorage.setItem(BEAT, JSON.stringify({ ts: Date.now(), pulito, app: window.auriTop || '', fase, mem: mem() }));
    } catch (e) {}
  }
  setInterval(() => { battito(false); salva(); }, 1000);
  addEventListener('pagehide', () => { log('INFO', 'avvio', 'Pagina chiusa normalmente'); salva(); battito(true); });
  document.addEventListener('visibilitychange', () => log('INFO', 'pagina', document.hidden ? 'Scheda in secondo piano' : 'Scheda di nuovo visibile'));

  // --- errori JS e promesse rifiutate ---
  addEventListener('error', e => log('ERR', 'js', `${e.message} (${(e.filename || '').split('/').pop()}:${e.lineno || '?'})`));
  addEventListener('unhandledrejection', e => log('ERR', 'js', 'Promessa fallita: ' + ((e.reason && (e.reason.message || e.reason)) || '?')));

  // --- UI bloccata: un timer da 250 ms che arriva tardi vuol dire che il thread principale era fermo ---
  // (in secondo piano il browser rallenta i timer apposta: quei ritardi non sono blocchi veri)
  let atteso = performance.now() + 250, visibileDa = performance.now();
  document.addEventListener('visibilitychange', () => { visibileDa = performance.now(); });
  setInterval(() => {
    const ritardo = performance.now() - atteso;
    if (ritardo > 700 && !document.hidden && document.hasFocus() && performance.now() - visibileDa > ritardo + 500)
      log('ATT', 'blocco', `Interfaccia ferma per ${(ritardo / 1000).toFixed(1)} s (app "${window.auriTop || '?'}", memoria ${mem()} MB)`);
    atteso = performance.now() + 250;
  }, 250);

  // --- memoria: avvisa quando sale molto ---
  let ultimaMem = 0;
  setInterval(() => {
    const m = mem();
    if (m && m - ultimaMem >= 100) { log('INFO', 'memoria', `Memoria JS: ${m} MB`); ultimaMem = m; }
  }, 5000);
  // --- invio automatico: solo dal sito pubblico e solo quando qualcosa va storto (crash, errore, blocco).
  // Va nel foglio Google del progetto (lo stesso indirizzo della classifica, file classifica.txt).
  // Massimo 6 invii a sessione, uno ogni 8 s, ultime 50 righe accorciate. Nessun dato personale.
  const LOCALE = /^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(location.hostname);
  const sessione = Math.random().toString(36).slice(2, 10);
  let urlReg = null, invii = 0, inAttesa = null, ultimo = 0;
  const pronto = LOCALE ? Promise.resolve(null) :
    fetch('classifica.txt', { cache: 'no-store' }).then(r => r.ok ? r.text() : '').then(t => { t = t.trim(); urlReg = t.startsWith('https://') ? t : null; }).catch(() => {});
  function manda(motivo) {
    if (LOCALE || invii >= 6) return;
    if (inAttesa) return;
    const attesa = Math.max(0, 8000 - (Date.now() - ultimo));
    inAttesa = setTimeout(async () => {
      inAttesa = null;
      await pronto;
      if (!urlReg) return;
      invii++; ultimo = Date.now();
      const testo = righe.slice(-50).map(r => `${r.t} ${r.l} ${r.a}: ${r.m.slice(0, 160)}`).join(' | ').slice(-5000);
      const q = 'registro=' + encodeURIComponent(testo) + '&sessione=' + sessione + '&motivo=' + encodeURIComponent(motivo.slice(0, 100));
      try { await fetch(urlReg + (urlReg.includes('?') ? '&' : '?') + q, { mode: 'no-cors' }); } catch (e) {}
    }, attesa);
  }
  window.auriLogSend = manda;
  // ogni errore o avviso fa partire un invio (raggruppato), il crash al riavvio subito
  const logOrig = log;
  log = function (livello, area, testo) {
    logOrig(livello, area, testo);
    if (livello === 'ERR' || (livello === 'ATT' && area !== 'memoria')) manda(`${area}: ${String(testo).slice(0, 80)}`);
  };
  if (righe.some(r => r.a === 'crash' && r === righe[righe.length - 2])) manda('crash');
  window.auriLogUptime = () => Math.round((performance.now() - t0) / 1000);
})();
