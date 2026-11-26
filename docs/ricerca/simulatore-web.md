# Ricerca: il simulatore web di AurI-3310

Data: novembre 2026. Ho letto `firmware/web/index.html`, `tools/classifica/apps_script.gs` e `firmware/apps/giochi/classifica.py`, poi l'ho confrontato con quello che si trova online. Il codice del progetto non è stato toccato.

## 1. Cosa esiste già

| Progetto | Cosa fa | Come disegna lo schermo |
|---|---|---|
| [freej2me-web](https://github.com/zb3/freej2me-web) | Emulatore J2ME nel browser, con Java che gira tramite CheerpJ | Canvas. Non funziona senza rete e "può essere un po' lento" |
| [FreeJ2ME-Plus (libretro)](https://docs.libretro.com/library/freej2me_plus/), [hex007/freej2me](https://github.com/hex007/freej2me) | Emulatore desktop, anche dentro RetroArch | Gli shader LCD li aggiunge RetroArch |
| [WIE](https://github.com/Magstic/wie), [j2me.js / PluotSorbet](https://github.com/mozilla/pluotsorbet) | Macchine virtuali J2ME scritte in JS | Canvas 2D |
| [Wokwi Nokia 5110](https://docs.wokwi.com/parts/wokwi-nokia-5110-screen) | Simulatore PCD8544 84x48 con MicroPython e Arduino | Pixel netti, senza effetto scia |
| [PCD8544-designer](https://github.com/jlcvp/PCD8544-designer) | Editor di bitmap per il PCD8544 | Canvas |
| [ESP32 + 5110, nota sulla scia](https://github.com/codingABI/3dRotationESP32Nokia5110) | Hardware vero: la scia dipende dagli fps e fino a circa 25 fps resta accettabile | — |

**In breve:** non ho trovato nessun simulatore web che riproduca la scia dell'LCD come fa il nostro, con il livello di ogni pixel che decade nel tempo (costante TAU). Su questo punto siamo avanti. Gli emulatori J2ME girano su VM pesanti (CheerpJ). Noi usiamo MicroPython WASM, che è [circa 170 KB compressi e parte in meno di 100 ms](https://docs.pyscript.net/2026.2.1/user-guide/what/). Pyodide invece pesa diversi MB. L'interfaccia JS<->Python (FFI) è [la stessa di Pyodide](https://pyscript.net/tech-preview/micropython/about.html), quindi passare dall'uno all'altro è facile, ma non conviene.

## 2. Confronto con il nostro codice e raccomandazioni (dalla più importante)

### A. Sicurezza (da fare subito)

**A1. Il server non controlla la firma.** In `classifica.py` il client calcola `firma` con FNV-1a e una chiave (`scores_key`). `doGet` in `apps_script.gs` però non legge mai `p.firma`, quindi chiunque può fare questo:
`GET <url>?gioco=volo&nome=AAA&punti=99999` → finisce in cima alla classifica.
C'è anche un secondo limite: la chiave sta nel client (che è pubblico su GitHub Pages) e FNV non è una firma crittografica. Anche se il server la controllasse, fermerebbe solo chi non si impegna. È la stessa conclusione di [tutte le fonti sull'anti-cheat](https://crux.supercraft.host/blog/leaderboard-cheating-public-leaderboard-server-validation-2026/): un punteggio calcolato dal browser [non è mai affidabile](https://itch.io/post/15202845). Cosa fare, in ordine di costo:
1. Controllare comunque la firma sul server: costa poco e taglia gli abusi più banali.
2. Aggiungere un **gettone di partita**. Il server lo rilascia all'inizio (`?inizia=volo`) con un orario firmato HMAC usando una chiave nelle Proprietà dello script. All'invio il server rifiuta i punteggi impossibili per la durata della partita (es. più di N punti al secondo) e i gettoni già usati. È il metodo descritto [qui](https://dev.to/raxxostudios/how-i-built-an-anti-cheat-system-for-a-css-game-3hm1).
3. Per i giochi deterministici, mandare **seme + tasti premuti** e far rigiocare la partita al server ([Open Hexagon](https://gigazine.net/gsc_news/en/20211110-open-hexagon-against-cheet), [esempio](https://dev.to/gowtham_r_2002/dont-trust-the-score-building-server-authoritative-validation-for-a-prize-based-mobile-game-246i)). È difficile da fare in Apps Script, più semplice su un Worker.

```js
// Apps Script: gettone di partita firmato con HMAC (la chiave resta solo sul server)
function firmaServer(s) {
  const k = PropertiesService.getScriptProperties().getProperty('SEGRETO');
  return Utilities.base64EncodeWebSafe(Utilities.computeHmacSha256Signature(s, k));
}
// ?inizia=volo  ->  { t: "volo.1732600000000", f: firmaServer("volo.1732600000000") }
// all'invio: firma giusta, gettone mai usato (CacheService, 6 ore), punti <= durata_sec * MAX_PPS[gioco]
```

**A2. Formula injection nel Registro.** `appendRow([new Date(), sessione, motivo, testo])` scrive i testi così come arrivano. In Google Sheets, `appendRow` e `setValues` trattano come formula una stringa che inizia con `=` (ad esempio `=IMPORTXML(...)` o `=HYPERLINK(...)`), e la formula parte quando apri il foglio. Lo spiegano [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection) e [CWE-1236](https://cwe.mitre.org/data/definitions/1236). I nomi della classifica sono già protetti dalla regex `^[A-Za-z0-9 ._-]+$`, tranne il `-` iniziale, che viene letto come numero. Soluzione:

```js
const safe = v => { v = String(v); return /^[=+\-@\t\r|%]/.test(v) ? "'" + v : v; };
f.appendRow([new Date(), safe(sessione), safe(motivo), safe(testo)]);
// e per i nomi: /^[A-Za-z0-9][A-Za-z0-9 ._-]{2,9}$/  (il primo carattere non può essere un simbolo)
```

**A3. Abuso dell'endpoint di log.** Chiunque può mandare `?registro=...` all'infinito. Ogni chiamata scrive 6 KB e può far partire `deleteRows`. Si consumano le quote (30 esecuzioni contemporanee per utente, [tabella quote](https://developers.google.com/apps-script/guides/services/quotas)) e, se il registro si riempie, anche la classifica smette di rispondere ("Too many simultaneous invocations"). Soluzioni: un limite per sessione con `CacheService` (es. 5 invii ogni 10 minuti), la pulizia una volta al giorno con un trigger temporizzato invece che a ogni scrittura, e lato client un solo invio per sessione.

```js
const c = CacheService.getScriptCache(), k = 'r_' + sessione;
const n = +(c.get(k) || 0); if (n >= 5) return risposta({ ok: false }); c.put(k, String(n + 1), 600);
```

**A4. Chi legge per primo prende la chiave.** In `leggiRegistro`, se `REGISTRO_CHIAVE` non è ancora impostata, il primo che chiama `?leggi=<20 caratteri>` diventa il proprietario. Basta impostarla a mano nelle Proprietà dello script e togliere la registrazione automatica. Il registro può contenere informazioni sul browser, quindi è meglio scriverci il meno possibile.

**A5. La classifica rallenta man mano che cresce.** Ogni GET legge l'intero foglio con `getDataRange().getValues()`, anche due volte quando si invia un punteggio. Conviene tenere la top 10 di ogni gioco in `CacheService` (durata 60 s, da aggiornare dopo ogni scrittura). Le risposte diventano molto più veloci: Apps Script di solito risponde in 0,5-2 s, con avvii a freddo anche più lunghi.

### B. Prestazioni su telefono

**B1. Disegnare lo schermo LCD con meno lavoro.** Oggi `draw()` fa 9 percorsi (`beginPath`) e fino a 9 × 4032 `rect()` per fotogramma, con l'antialias del vettoriale. Il modo più comune negli emulatori è scrivere i 4032 pixel in un `ImageData` 84x48 (un solo `Uint8ClampedArray`) e poi ingrandirlo con `drawImage` e `imageSmoothingEnabled=false`. La griglia dei pixel e l'ombra si disegnano una volta sola su un canvas a parte, sopra (o con `globalCompositeOperation='multiply'`). Il risultato è lo stesso, con 2-3 chiamate al canvas per fotogramma invece di migliaia.

```js
const small = new OffscreenCanvas(84, 48), sx = small.getContext('2d'), img = sx.createImageData(84, 48);
function paintLcd(fg, bg) {
  const d = img.data;
  for (let i = 0; i < 4032; i++) {
    const v = level[i], j = i * 4;
    d[j] = bg[0] + (fg[0] - bg[0]) * v; d[j + 1] = bg[1] + (fg[1] - bg[1]) * v; d[j + 2] = bg[2] + (fg[2] - bg[2]) * v; d[j + 3] = 255;
  }
  sx.putImageData(img, 0, 0);
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(small, 0, 0, lcd.width, lcd.height);
  ctx.drawImage(gridOverlay, 0, 0);   // griglia + ombra pre-disegnate quando cambia la dimensione
}
```

Se un giorno servirà ancora più velocità, uno shader WebGL con due texture (precedente e attuale) fa la scia direttamente sulla GPU, ma per uno schermo 84x48 non serve.

**B2. Il limite a 30 fps è giusto.** Corrisponde all'osservazione sull'hardware vero (scia accettabile fino a circa 25 fps). Quando la pagina è nascosta (`document.hidden`) conviene fermare anche i `setInterval` a 300 ms/1 s (oggi `index.html:569, 585, 630` e `auri-log.js`).

**B3. Meno chiamate JS->Python.** Oggi `mp.runPython('js.window.auriTop = ...')` viene chiamato periodicamente: ogni chiamata deve analizzare e compilare il codice. Meglio farlo una volta sola, prendere un riferimento alla funzione (`const stato = mp.globals.get('stato_per_js')`) e chiamarla, oppure fare in modo che Python spinga lo stato verso JS solo quando cambia. In generale: poche chiamate che passano tanti dati (un `bytearray` del framebuffer) invece di tante chiamate piccole.

**B4. Caricamento rapido e uso offline (PWA).** Non c'è un service worker. Con [Workbox precaching](https://developer.chrome.com/docs/workbox/modules/workbox-precaching) o con uno scritto a mano si salvano in cache il wasm di MicroPython, i `.py`/`.mpy` e i JS. Da quel momento la seconda apertura funziona anche senza rete, e si aggiorna solo quello che cambia. I file grandi (modello 3D, modelli LLM) vanno messi in cache solo quando servono, non in anticipo ([consiglio Workbox](https://developer.chrome.com/docs/workbox/service-worker-deployment)). Su GitHub Pages il service worker deve stare nella cartella del sito (lo scope è il percorso del repo).

```js
// sw.js (minimo, senza librerie): cambia VER a ogni rilascio
const VER = 'auri-v1', CORE = ['./', 'index.html', 'auri-io.js', 'auri-log.js', 'phone3d.js' /*, wasm e .mpy */];
self.oninstall = e => e.waitUntil(caches.open(VER).then(c => c.addAll(CORE)));
self.onactivate = e => e.waitUntil(caches.keys().then(k => Promise.all(k.filter(x => x !== VER).map(x => caches.delete(x)))));
self.onfetch = e => {
  if (e.request.method !== 'GET' || new URL(e.request.url).origin !== location.origin) return;  // niente classifica/log in cache
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).then(n => {
    const copia = n.clone(); caches.open(VER).then(c => c.put(e.request, copia)); return n; })));
};
```

Va aggiunto anche un `manifest.webmanifest` (icona, `display: standalone`, `orientation: portrait`) per poterlo installare sulla schermata home.

### C. Usabilità su telefono

**C1. Tocco.** Usare `pointerdown` + `preventDefault` + `setPointerCapture` (`index.html:484`) è la scelta giusta. Ci sono tre aggiunte facili: `touch-action: none` sui tasti (così il browser non aspetta per capire se è uno zoom o uno scroll), `user-select:none; -webkit-touch-callout:none` per evitare la lente e il menu sulla pressione lunga su iOS, e `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">` con `env(safe-area-inset-*)`.

**C2. Vibrazione.** `navigator.vibrate` funziona su Chrome e Firefox per Android, ma **Safari su iOS non lo supporta** ([caniuse](https://caniuse.com/mdn-api_navigator_vibrate), [rapporto W3C](https://w3c.github.io/vibration/reports/implementation.html)). Il nostro codice controlla già `if (navigator.vibrate)`, bene. Su iOS 18 e successivi c'è un trucco: un `<input type="checkbox" switch>` nascosto, attivato dentro un gesto dell'utente, produce un piccolo tocco del motore aptico ([WebHaptics](https://azukiazusa.dev/blog/ios-safari-web-haptics.md)). Non è un'API ufficiale, quindi va trattato come extra e non come base. Come ripiego ci sono già lo scossone visivo (`shake`) e un click audio.

**C3. Audio.** Un oscillatore square monofonico con gain a gradini è il modo giusto per imitare il beeper. Due accorgimenti: sbloccare l'`AudioContext` al primo `pointerdown` (già fatto in `auri-io.js:61`) e usare rampe di 2-3 ms (`setTargetAtTime`) invece di salti netti a zero, così spariscono i "clic". Su iOS l'interruttore silenzioso zittisce il WebAudio, e va detto all'utente.

## 3. Alternative gratuite per la classifica

| Servizio | Piano gratuito | Pro | Contro |
|---|---|---|---|
| **Apps Script + Foglio** (attuale) | 30 esecuzioni contemporanee per utente, quota giornaliera di runtime ([quote](https://developers.google.com/apps-script/guides/services/quotas)) | Zero infrastruttura, il foglio si guarda a occhio | Lento (0,5-2 s), rischio formula injection, scala male |
| **Cloudflare Workers + D1** | 100k richieste al giorno per i Workers; D1 5M righe lette e 100k scritte al giorno, 500 MB per database ([limiti D1](https://developers.cloudflare.com/d1/platform/limits/)) | Veloce (edge), SQL, HMAC con WebCrypto, CORS e POST senza problemi, rate limit facile | Serve un account Cloudflare e `wrangler`. Con il free tier, superati i limiti le query falliscono fino a mezzanotte UTC |
| **Cloudflare KV** | 100k letture e 1k scritture al giorno | Semplicissimo per una top 10 | Le scritture si propagano lentamente (fino a ~60 s) |
| **Supabase** | 500 MB Postgres, il progetto va in pausa dopo 7 giorni senza uso | SQL, RLS, funzioni | La pausa e la chiave anon nel client richiedono RLS e una funzione RPC che controlli i punteggi |
| **Firebase Firestore** | 50k letture e 20k scritture al giorno | SDK maturo, App Check | Le regole non possono verificare un punteggio senza Cloud Functions (che richiedono il piano a pagamento) |
| **Deno Deploy + Deno KV** | Free tier con limiti mensili | TypeScript, KV integrato | Il piano gratuito è cambiato più volte, quindi è un po' meno prevedibile |

**Consiglio:** finché il traffico resta basso, tenere Apps Script con le correzioni A1-A5. Se il gioco prende piede, spostarsi su **Cloudflare Worker + D1**, che risolve latenza, quote e sicurezza in circa 60 righe:

```js
export default { async fetch(req, env) {
  const u = new URL(req.url), g = u.searchParams.get('gioco');
  if (req.method === 'POST') {
    const { nome, punti, gettone, firma } = await req.json();
    if (!await verificaHmac(env.SEGRETO, gettone, firma)) return new Response('no', { status: 403 });
    await env.DB.prepare('INSERT INTO punti(gioco,nome,punti) VALUES(?1,?2,?3) ON CONFLICT(gioco,nome) DO UPDATE SET punti=max(punti,excluded.punti)')
      .bind(g, nome, punti).run();
  }
  const { results } = await env.DB.prepare('SELECT nome,punti FROM punti WHERE gioco=?1 ORDER BY punti DESC LIMIT 10').bind(g).all();
  return Response.json({ top: results }, { headers: { 'Access-Control-Allow-Origin': 'https://<utente>.github.io' } });
} };
```

## 4. Registro degli errori lato client

| Servizio | Gratis | Note |
|---|---|---|
| [Sentry](https://sentry.io/pricing/) | 5.000 errori al mese, 1 utente | Il più completo, l'SDK pesa circa 30 KB compressi (meno con il loader lazy) |
| [GlitchTip](https://betterstack.com/community/comparisons/sentry-vs-glitchtip.md) | 1.000 eventi al mese in hosting, gratis se lo ospiti tu | Compatibile con l'SDK di Sentry |
| [PostHog](https://posthog.com/compare/best-sentry-alternatives.md) | ~100k eccezioni al mese | Include anche le analytics, più pesante |
| [Rollbar](https://rollbar.com/blog/sentry-alternatives-for-error-tracking/) | 5.000 occorrenze al mese | — |
| Apps Script (attuale) | quote di Google | Zero dipendenze, ma non è protetto (vedi A2-A3) |

**Consiglio:** il registro fatto in casa va bene per un progetto così piccolo, purché si aggiungano il prefisso `'`, il limite per sessione e la rimozione dei dati personali (niente URL completi con parametri, niente user agent intero: bastano famiglia del browser e versione principale). Sentry gratis conviene solo se servono raggruppamento e stack trace con source map. Il WASM, comunque, dà stack poco leggibili.

## 5. Cosa fare, in ordine

1. **A1** controllare la firma sul server più il limite di punti al secondo, poi il gettone HMAC (sicurezza, impatto alto).
2. **A2** prefisso `'` su tutto quello che finisce nel foglio, e nomi che non iniziano con un simbolo.
3. **A3/A4** limite per sessione sul log e chiave del registro impostata a mano.
4. **B1** schermo LCD con `ImageData` + `drawImage` (CPU molto più bassa sui telefoni economici).
5. **B4** service worker + manifest (seconda apertura istantanea, uso offline, installabile).
6. **A5** top 10 in `CacheService`.
7. **C1** `touch-action`, `user-select`, safe-area; **C3** rampe audio anti-clic.
8. **B3** meno `runPython` a intervalli; **B2** pausa quando la pagina è nascosta.
9. **C2** trucco aptico per iOS, solo come extra facoltativo.
10. Passare a Cloudflare Worker + D1 solo se il traffico cresce.
