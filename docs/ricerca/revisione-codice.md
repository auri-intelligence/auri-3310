# Revisione del codice di AurI-3310 (26/11/2026)

Ho controllato ogni problema leggendo il codice. Non ho modificato niente. I numeri di riga si riferiscono al commit `f8532d6`.
Ordine: **CRITICO**, poi **ALTO**, **MEDIO** e **BASSO** (manutenibilità e pulizia).

---

## CRITICO

### 1. Il bridge parte senza token, ascolta tutta la rete e il telefono sceglie i permessi di Claude
- `bridge/config.example.json`: `"host": "0.0.0.0"`, `"token": ""`
- `bridge/auri_bridge.py:616-618`: con il token vuoto `_authorized()` restituisce sempre True
- `bridge/auri_bridge.py:129`: `permission_mode=r.get('permission_mode') or 'default'` arriva **dalla richiesta**
- `bridge/auri_bridge.py:657-659`: se manca `config.json` il bridge usa da solo `config.example.json`

**Perché è grave.** Chiunque sia sulla stessa rete (Wi-Fi ospiti, rete del bar, VPN) può mandare
`POST /v1/chat {"text":"...","permission_mode":"bypassPermissions"}`. Claude allora esegue comandi Bash e
scrive file nella cartella `cwd` (di base `~`, cioè tutta la home) senza chiedere conferma. In pratica è
un'esecuzione di codice da remoto sul PC. Anche con `default` chi attacca può rispondere da solo a
`/v1/confirm` con `ok: true`. Il CORS `*` (riga 607) permette poi a **qualsiasi sito web** aperto nel browser
di chiamare `http://<ip-del-pc>:8310` (le richieste JSON fanno il preflight, ma il bridge risponde
`Allow-Origin: *` anche a quello).

**Correzione.**
```python
# load_config
c.setdefault('host', '127.0.0.1')
if not c.get('token') or len(c['token']) < 24:
    raise SystemExit('Imposta un "token" lungo in bridge/config.json (es. python -c "import secrets;print(secrets.token_urlsafe(32))")')

# main(): niente ripiego silenzioso su config.example.json
if not os.path.exists(a.config):
    raise SystemExit('Manca ' + a.config + ': copia config.example.json e imposta il token')

# Run.go(): solo i modi che si possono scegliere dal telefono
ALLOWED_MODES = {'default', 'acceptEdits', 'plan'}
mode = r.get('permission_mode')
permission_mode = mode if mode in ALLOWED_MODES else 'default'

# _authorized(): confronto a tempo costante
import hmac
return hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + cfg['token'])
```
Togli anche `Access-Control-Allow-Origin: *`, oppure limitalo a un elenco `cors_origins` nel config
(il Nokia vero non ha bisogno del CORS). `cwd` predefinito: una cartella dedicata, non `~`.

### 2. `serve.py` pubblica su tutta la rete la cartella firmware, compreso `config.json` con token e password Wi-Fi
- `firmware/serve.py:23`: `ThreadingHTTPServer(('0.0.0.0', port), ...)` con `directory=firmware/`
- `firmware/web/index.html:541`: la pagina legge `../config.json` (token del bridge, `wifi_ssid`, `wifi_password`)

Chiunque sulla LAN può aprire `http://<pc>:8000/config.json` e anche `/.simdata/`. Con il token del punto 1 in mano
può comandare Claude e Home Assistant.

**Correzione.**
```python
class NoCache(http.server.SimpleHTTPRequestHandler):
    BLOCCATI = ('/config.json', '/.simdata', '/.git')
    def send_head(self):
        if self.path.split('?')[0].startswith(self.BLOCCATI) and self.client_address[0] not in ('127.0.0.1', '::1'):
            self.send_error(404); return None
        return super().send_head()
```
In alternativa: `host` predefinito `127.0.0.1` e opzione `--lan` esplicita per il telefono.

---

## ALTO

### 3. `/v1/sensors` permette di scrivere stati qualsiasi in Home Assistant
`bridge/auri_bridge.py:247-257`: `'state': req[key]` non viene controllato (testo lungo, oggetti, ecc.) e
`sensor.auri_3310_*` viene creato con il token di HA, che ha i pieni poteri. È un problema minore del punto 1, ma resta anche con il token
(il telefono può essere compromesso o perso).
```python
try:
    val = round(float(req[key]), 1)
except (TypeError, ValueError):
    continue
```
Consiglio: un **token HA dedicato** (utente HA non amministratore) e scritto nel README.

### 4. Formula injection e spam nel foglio Google (Apps Script)
- `tools/classifica/apps_script.gs:38`: `appendRow([new Date(), sessione, motivo, testo])` con testo libero preso dalla URL.
  Un valore che inizia con `=`, `+`, `-` o `@` diventa una **formula** (`=IMPORTXML(...)`, `=HYPERLINK(...)`), che si esegue quando
  apri il foglio e può far uscire dati verso un sito esterno.
- Nessun limite di frequenza: chiunque conosca l'URL (è pubblico in `firmware/web/classifica.txt`) può riempire il
  Registro (2000 righe che ruotano, quindi può cancellare i registri veri) o la classifica con punteggi
  finti fino a `99999`.
- Riga 47: la chiave del registro viene fissata dal **primo** che chiama `?leggi=` con 20 caratteri o più. Se la proprietà non
  è ancora impostata, la può prendere chiunque.

```js
function cella(s) { s = String(s); return /^[=+\-@\t\r]/.test(s) ? "'" + s : s; }
f.appendRow([new Date(), cella(sessione), cella(motivo), cella(testo)]);

// limite semplice per IP non disponibile: si usa un contatore per minuto
const c = CacheService.getScriptCache();
const k = 'n' + Math.floor(Date.now() / 60000);
const n = Number(c.get(k) || 0); if (n > 30) return risposta({ ok: false, errore: 'troppi' });
c.put(k, String(n + 1), 120);

// la chiave si imposta solo a mano dall'editor (Proprietà dello script), mai dalla prima richiesta
if (!chiave || p.leggi !== chiave) return risposta({ errore: 'chiave' });
```
Per la classifica: valida anche `punti` come intero (`/^\d+$/`), usa `cella(nome)` (oggi la regex permette
`-` iniziale: `-123` diventa un numero) e valuta un controllo di plausibilità per gioco (punteggio massimo realistico).
Il filtro `BAD` contiene `bob`, `nig` e `sex`, che bloccano nomi innocui (`Bobby`, `Nigel`, `Essex`).

### 5. La storia git contiene il nome utente Windows (percorso personale)
Ho cercato chiavi Google (`AIza…`), token Anthropic/GitHub/AWS, JWT, email, `"token"/"password"` pieni nei JSON e percorsi `C:\Users\…`:
- **Nessuna chiave o token trovati** in nessun commit.
- **Percorso personale `C:\Users\<nome>\…`**: `contesti/2026-11-25.md` nei commit `7c843bf` e `840685e`
  (nell'ultima versione non c'è più, ma **resta nella storia**). È contro la regola "niente percorsi del PC".
- `firmware/web/classifica.txt` (commit `e9ef428`): URL pubblico dell'Apps Script. È voluto, ma rende possibile l'abuso del punto 4.

**Correzione.** Se il repo è già pubblico: riscrivere la storia di quel file
(`git filter-repo --replace-text` con una regola `C:\Users\NOME==>C:\Users\<utente>`), poi fare un push forzato,
ma **solo dopo conferma**. Per il futuro aggiungi un controllo prima del commit:
```sh
git diff --cached | grep -nE 'C:\\\\Users\\\\[^<]|AIza[0-9A-Za-z_-]{20}|sk-ant-' && { echo "dato personale"; exit 1; }
```

### 6. Il bridge non ha limiti di memoria (DoS) e fa vedere `cwd`
- `auri_bridge.py:636`: legge `Content-Length` senza un massimo (un POST da 2 GB riempie la RAM del Raspberry).
- `runs` (riga 85), `llm_sessions` (269) e `gemini_sessions` non vengono **mai svuotati**: ogni chat resta in memoria per sempre.
- `/v1/info` (riga 626) restituisce `cfg['cwd']`, cioè il percorso completo della home con il nome utente.
- `voice()` riga 580: il ciclo sul picco audio scorre tutto il PCM ricevuto, senza limite di durata.
```python
MAX_BODY = 4 * 1024 * 1024
n = int(self.headers.get('Content-Length', 0))
if n > MAX_BODY:
    return self._send(413, {'error': msg(None, 'server')})

# pulizia: dopo ogni start_chat
with lock:
    for k in [k for k, r in runs.items() if r.done and time.time() - r.t0 > 600]:
        del runs[k]
# sessioni: OrderedDict con al massimo 50 voci (popitem(last=False))
```
`/v1/info`: restituisci solo `os.path.basename(cfg['cwd'])`.

---

## MEDIO

### 7. Doppia conferma: `set_result` su un future già risolto
`auri_bridge.py:115-118` e `193-196`: dopo `await self.answer` il future non torna a `None`. Un secondo `/v1/confirm`
con lo stesso id (doppio tasto, nuova richiesta dopo un timeout di rete) chiama `set_result` su un future finito:
`InvalidStateError` dentro il loop, e il telefono riceve la risposta "in attesa".
```python
ok = await self.answer
self.answer = None          # in can_use_tool
...
if not run or not run.answer or run.answer.done():   # in confirm
```

### 8. `msg` usata sia come funzione sia come variabile del ciclo
`auri_bridge.py:139`: `async for msg in query(...)` copre la funzione globale `msg`. Per questo esiste l'alias
`msg_text = msg` (riga 68), che è un trucco poco chiaro. Basta rinominare la variabile del ciclo in `m` e togliere `msg_text`.

### 9. `push_telemetry` blocca la schermata Home
`firmware/apps/sensori.py:45`: `sys.hal.request(...)` è **bloccante** (fino a `REQ_TIMEOUT_S` sull'ESP32 e 60 s sul PC,
`hal/pc.py:130`). Viene chiamata da `apps/home.py:43` ogni pochi minuti: se il bridge è spento il telefono si
blocca e l'eccezione viene ignorata in silenzio (`except Exception: pass`). Esiste già `auri.net.Richiesta`:
```python
from auri.net import Richiesta
_tel = None
def push_telemetry(sys):
    global _tel
    if _tel and not _tel.poll():
        return                      # quella prima e' ancora in corso
    ...
    _tel = Richiesta(sys.hal, 'POST', cfg['bridge_url'] + '/v1/sensors', data, cfg.get('token'))
```

### 10. Richieste in thread sull'ESP32 senza un numero massimo
`hal/esp32.py:417-436`: ogni `request_start` apre un nuovo `_thread`. Ogni thread ha il suo stack e il socket TLS
usa circa 40 KB. Con tante richieste di fila (classifica, casa, telemetria) si esaurisce la RAM. Se il thread
non parte, si ripiega su una chiamata bloccante. Inoltre, se l'app viene chiusa prima del `poll`, il risultato
resta per sempre in `self._req`.
```python
if sum(1 for v in self._req.values() if v is None) >= 2:
    raise OSError('rete occupata')
```
Aggiungi anche `request_cancel(rid)`, da chiamare in `close()` delle app.

### 11. Errori interni mandati al client
`auri_bridge.py:146` (`self.error = str(e)`), `417`, `530`: il testo dell'eccezione (che può contenere percorsi,
URL del server LLM o dettagli dell'SDK) arriva sul display e nel registro web, che poi **viene mandato al foglio Google**
(`auri-log.js:100`). Meglio scrivere `str(e)` solo nel log del bridge e mandare al telefono `msg(req, 'error')`.

### 12. `raise last` con un elenco di modelli vuoto
`auri_bridge.py:499`: se `gemini_models` è `[]`, `last` resta `None` e `raise None` dà `TypeError`. Correzione:
`raise last or RuntimeError('nessun modello Gemini')`.

### 13. Patch "monkey" di `Canvas` in `auri/gfx.py:260-401`
Quando c'è `framebuf`, il modulo sostituisce al volo 11 metodi della classe (`Canvas.__init__`, `pixel`, `char`,
`icon`, `icon2`, `blit`, `_char2x`, …) e tiene gli originali in `_py_*`. Funziona, ma:
- chi legge `class Canvas` non vede il codice che gira davvero sul Nokia;
- l'ordine conta (`_py_icon2` alla riga 360 va letto prima della riga 392, `_py_icon` alla 394);
- i test su PC (CPython, senza framebuf) non provano mai il ramo C (c'è solo `tools/confronta_framebuf.py`).

**Correzione.** Una sottoclasse, scelta una sola volta:
```python
class _CanvasFB(Canvas):
    def __init__(self):
        super().__init__()
        self.fb = _fb.FrameBuffer(self.buf, W, H, _fb.MONO_VLSB)
    def pixel(self, x, y, c=1): ...
    # ecc.

Canvas = _CanvasFB if _fb is not None else Canvas
```
Con MicroPython la chiamata `super()` costa poco, e il comportamento non cambia per chi fa `from auri.gfx import Canvas`.

### 14. XSS possibile in `prova-cervello.html:49` e in parte di `auri-io.js:22`
`li.innerHTML = \`<b>${nome}</b><span ...>${nota}</span>\``: `nota` contiene anche messaggi d'errore dal worker o dal modello
(testo che non controlliamo). Oggi la pagina è solo di prova, ma è pubblicata su Pages. Usa `textContent`:
```js
const b = document.createElement('b'); b.textContent = nome;
const s = document.createElement('span'); s.className = ...; s.textContent = nota;
li.append(b, s);
```
`auri-io.js:22` usa solo costanti locali (`NAMES`, valori numerici), quindi oggi è sicuro. Il resto di `innerHTML`
(`index.html:241,275,335`, `auri-llm.js:498-543`) usa solo stringhe fisse: va bene. Il registro (`auri-log.js`) salva
in `localStorage` e invia con `encodeURIComponent`, senza HTML: va bene.

### 15. `localStorage` del simulatore conserva il token
`index.html:354-355`: `auriSave` salva le impostazioni dell'app in `localStorage` (`auri.*`). Il token arriva da
`config.json` e non sembra salvato, ma ogni `save()` fatto da Python finisce in chiaro nel browser. Per sicurezza conviene una lista di
chiavi vietate (`token`, `wifi_password`) dentro `WebHal.save`.

---

## BASSO (manutenibilità, duplicazione, codice morto)

### 16. `onoff()` e il menu che si ricostruisce, copiati in più file
- `apps/connessioni.py:8` e `apps/impostazioni.py:10`: stessa funzione `onoff(v)`.
- `m.rebuild = lambda: setattr(m, 'items', build())`: in `impostazioni.py:18`, `impostazioni.py:83`, `connessioni.py:141`,
  e il richiamo `if hasattr(m, 'rebuild'): m.rebuild()` in `impostazioni.py:25` e `connessioni.py:120`.

Spostali in `auri/ui.py`:
```python
def onoff(v):
    return t('on') if v else t('off')

class Menu(App):
    def __init__(self, sys, title, items, build=None):
        self.build = build
        ...
    def rebuild(self):
        if self.build:
            self.items = self.build()
```

### 17. URL del bridge e token ripetuti 8 volte
`cfg['bridge_url'] + '/v1/...', ..., cfg.get('token')` in `apps/casa.py:16`, `apps/claude.py:46,95,136`,
`apps/sensori.py:45`, `auri/cervello.py:224,315`. Basta un aiutante in `auri/net.py`:
```python
def bridge(sys, method, path, body=None):
    c = sys.config
    return Richiesta(sys.hal, method, c['bridge_url'].rstrip('/') + path, body, c.get('token'))
```
Così basta un solo posto per aggiungere `rstrip('/')`, il controllo di `bridge_url` vuoto o un timeout diverso.

### 18. Le tre HAL ripetono `request`, `load` e `save`
`hal/pc.py:124-141`, `hal/esp32.py:399-455` e `hal/web.py:196-230` hanno la stessa firma, ma costruiscono le intestazioni ognuna a modo suo
(Content-Type e Bearer ripetuti), e i timeout sono diversi: 60 s sul PC, `REQ_TIMEOUT_S` sull'ESP32, nessuno nel web (`auriRequest`).
Proposta: una classe base `hal/board.py` con
```python
def _headers(self, token):
    h = {'Content-Type': 'application/json'}
    if token: h['Authorization'] = 'Bearer ' + token
    return h
REQ_TIMEOUT_S = 20
```
e i metodi "vuoti" (`speak`, `cam_ok`, `ai_ok` che restituiscono False) messi lì, così le app smettono di usare
`getattr(sys.hal, 'net_info', None)` e `hasattr(hal, 'request_start')` (`connessioni.py:13`, `impostazioni.py:133`, `net.py:14`).

### 19. Eccezioni ignorate in silenzio
`except Exception: pass` in `auri/core.py:62` (chiusura app), `apps/assistente.py:68`, `apps/sensori.py:46`,
`hal/web.py:178,184`, `hal/esp32.py:178,284,453` e altri. Sul telefono vero un errore in `close()` (per esempio la
fotocamera che non si spegne) non lascia nessuna traccia. Basta un `log` minimo:
```python
except Exception as e:
    sys.print_exception(e) if hasattr(sys, 'print_exception') else print('close:', e)
```
(`hal/web.py` ha già `auriLog` lato JS: si può usare quello.)

### 20. Stringhe i18n non usate
In `auri/i18n.py` (191 chiavi) queste chiavi non sono usate da nessuna parte (né Python né JS, e nemmeno con un prefisso dinamico):
`effort_word` (r.105), `memory` (r.191, il testo "memory" che compare in giro non è una chiamata a `t()`), `navi_ask` (153),
`navi_on` (147), `navi_send` (155), `pet_age` (128), `pet_happy` (125), `points` (90), `with` (104).
Ogni chiave sono 6 stringhe in RAM sull'ESP32: toglile o usale.
Non mancano chiavi (tutte le `t('...')` esistono). Le chiavi con prefisso dinamico (`cam_`, `loc_`, `g_`, `g_h_`, `prof_`)
sono usate. Nel bridge alcuni testi sono **solo in italiano** e non passano da `MSG`: `describe_tool` ("Eseguo:", "Modifico", "Uso",
righe 173-178) e `'Audio vuoto o muto'` (riga 584): per un utente con il telefono in inglese le conferme appaiono in italiano.

### 21. Altre piccole cose
- `auri_bridge.py:582`: `int(req.get('rate', 16000))` è calcolato due volte (righe 578 e 582). Usa `rate`.
- `auri_bridge.py:199-207`: `claude_version()` avvia un processo `claude --version` (fino a 20 s) a **ogni** `/v1/info`.
  Basta calcolarlo una volta sola (`functools.lru_cache`).
- `index.html:201-204`: `document.write` con `Date.now()` per evitare la cache. È deprecato e blocca il caricamento: meglio
  `<script src="auri-io.js" defer>`, visto che `serve.py` manda già `no-store`.
- `apps/giochi/base.py:33-51`: tanti metodi vuoti (`pass`) come segnaposto. Va bene, ma un breve commento
  "da sovrascrivere" eviterebbe di pensare che sia codice morto.
- Import pesanti: in firmware non ne ho trovati (`requests` e `_thread` sono già caricati dentro le funzioni; `faster_whisper` e
  `piper` nel bridge sono caricati solo quando servono). Nel bridge `claude_agent_sdk` viene importato all'avvio anche se si
  usa solo l'assistente locale: si può spostare l'import dentro `Run.go`.

---

## Riepilogo delle priorità
1. Token obbligatorio, host `127.0.0.1` predefinito e `permission_mode` limitato nel bridge (punto 1).
2. `serve.py`: non pubblicare `config.json` sulla LAN (punto 2).
3. Apps Script: `cella()` contro le formule, limite di frequenza, chiave fissata a mano (punto 4).
4. Pulire il percorso `C:\Users\…` dalla storia di `contesti/2026-11-25.md` se il repo è pubblico (punto 5).
5. Limiti di memoria nel bridge, poi le pulizie (helper `bridge()`, `onoff`/`Menu.rebuild`, sottoclasse per framebuf).
