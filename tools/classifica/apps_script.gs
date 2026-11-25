// AurI-3310 world leaderboard: one row per player and game, best score only.
const GIOCHI = ['volo', 'corsie', 'incastro', 'rompimuro', 'trefila', 'salisali', 'catapulta'];
const MAX_PUNTI = 99999;
const BAD = ['cazz', 'mink', 'minchi', 'stronz', 'merd', 'puttan', 'troi', 'figa', 'fica', 'vaffa', 'fanculo',
  'coglion', 'culo', 'froci', 'negr', 'porcodi', 'diocan', 'madon', 'bastard', 'zocol', 'pompin', 'fuck', 'fuk',
  'shit', 'bitch', 'cunt', 'pusi', 'whore', 'slut', 'nig', 'fagot', 'rape', 'nazi', 'hitler', 'porn', 'sex',
  'penis', 'vagina', 'tits', 'bob', 'wank', 'twat', 'ashole'];
const LEET = { '4': 'a', '@': 'a', '3': 'e', '0': 'o', '1': 'i', '!': 'i', '5': 's', '$': 's', '7': 't', '8': 'b',
  '9': 'g', '6': 'g', '2': 'z', 'k': 'c', 'y': 'i', 'j': 'i', 'x': 'cs' };

function norm(s) {
  let out = '';
  for (const c0 of s.toLowerCase()) {
    const c = LEET[c0] || c0;
    if (c[0] >= 'a' && c[0] <= 'z' && (!out || out[out.length - 1] !== c[c.length - 1])) out += c;
  }
  return out;
}

function risposta(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

// --- Registro del simulatore: quando qualcosa va storto la pagina manda le ultime righe (niente dati
// personali: app aperta, modello, browser, errori). Si leggono con ?leggi=<chiave>; la chiave sta nelle
// Proprieta' dello script (REGISTRO_CHIAVE, fissata dalla prima lettura), mai nel codice pubblico.
function foglioRegistro() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  return ss.getSheetByName('Registro') || ss.insertSheet('Registro');
}

function registro(p) {
  const testo = String(p.registro || '').slice(0, 6000);
  const sessione = String(p.sessione || '').slice(0, 16);
  const motivo = String(p.motivo || '').slice(0, 120);
  if (!testo) return risposta({ ok: false });
  const f = foglioRegistro();
  f.appendRow([new Date(), sessione, motivo, testo]);
  if (f.getLastRow() > 2000) f.deleteRows(1, f.getLastRow() - 2000);   // tiene le ultime 2000
  return risposta({ ok: true });
}

function leggiRegistro(p) {
  // la prima lettura (dal PC del progetto) fissa la chiave; da li' in poi serve sempre quella
  const props = PropertiesService.getScriptProperties();
  let chiave = props.getProperty('REGISTRO_CHIAVE');
  if (!chiave && String(p.leggi).length >= 20) { chiave = String(p.leggi); props.setProperty('REGISTRO_CHIAVE', chiave); }
  if (!chiave || p.leggi !== chiave) return risposta({ errore: 'chiave' });
  const f = foglioRegistro();
  const n = Math.min(200, parseInt(p.n || '30', 10) || 30);
  const da = Math.max(1, f.getLastRow() - n + 1);
  const righe = f.getLastRow() ? f.getRange(da, 1, f.getLastRow() - da + 1, 4).getValues() : [];
  return risposta({ righe: righe.map(r => [String(r[0]), r[1], r[2], r[3]]) });
}

function doGet(e) {
  const p = e.parameter || {};
  if (p.registro) return registro(p);
  if (p.leggi) return leggiRegistro(p);
  const gioco = String(p.gioco || '');
  if (GIOCHI.indexOf(gioco) < 0) return risposta({ errore: 'gioco' });
  const foglio = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  const nome = String(p.nome || '').trim();
  const punti = parseInt(p.punti, 10);
  if (nome) {
    const n = norm(nome);
    const ok = nome.length >= 3 && nome.length <= 10 && /^[A-Za-z0-9 ._-]+$/.test(nome) &&
      punti > 0 && punti <= MAX_PUNTI && !BAD.some(w => n.indexOf(norm(w)) >= 0);
    if (ok) {
      const lock = LockService.getScriptLock();
      lock.waitLock(5000);
      try {
        const righe = foglio.getDataRange().getValues();
        let trovata = -1;
        for (let i = 0; i < righe.length; i++) {
          if (righe[i][0] === gioco && String(righe[i][1]).toLowerCase() === nome.toLowerCase()) { trovata = i; break; }
        }
        if (trovata < 0) foglio.appendRow([gioco, nome, punti, new Date()]);
        else if (punti > righe[trovata][2]) foglio.getRange(trovata + 1, 3, 1, 2).setValues([[punti, new Date()]]);
      } finally {
        lock.releaseLock();
      }
    }
  }
  const top = foglio.getDataRange().getValues()
    .filter(r => r[0] === gioco && r[2] > 0)
    .sort((a, b) => b[2] - a[2]).slice(0, 10)
    .map(r => [r[1], r[2]]);
  return risposta({ top: top });
}
