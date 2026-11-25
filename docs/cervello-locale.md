# Il cervello di AurI, gratis e in casa propria

AurI è l'assistente del telefono: tieni premuto Navi, parli, lei risponde a voce e sul display.
Fino a ieri dietro c'era un servizio a pagamento con una chiave (Gemini) e, nel simulatore online,
non c'era proprio niente. Adesso il cervello è **nostro**: un modello di linguaggio piccolo che gira
dentro il dispositivo o dentro casa. Zero chiavi, zero abbonamenti, zero dati che escono.

Il cervello può stare in tre posti. Sono gli stessi tre in ogni versione del telefono, e si sceglie
in **Impostazioni › Cervello** (o dal menu `#` dentro l'assistente): *Auto*, *Locale*, *Casa*.

| Dove | Cosa gira | Quando |
|---|---|---|
| **Locale** | nel browser (simulatore) o nella microSD (telefono vero) | sempre, anche senza rete |
| **Casa** | sul PC o sul Raspberry, con llama.cpp | in rete di casa: risposte migliori, voce, domotica |
| **Niente** | — | il telefono lo dice sul display invece di inventare |

---

## 1. Nel simulatore online (è questa la novità che si vede)

Apri il simulatore, accendi il telefono (tasto in alto o `P`), Menu → **AurI**.

- La prima volta il cervello è spento: il display dice `Cervello OFF`, il modello e quanto pesa.
  Premi Navi: parte lo scaricamento, con la percentuale sullo schermo del 3310.
- Finito, `tieni premuto Navi e parla` (il browser trascrive), oppure premi Navi breve e **scrivi col
  T9** come nel 2000.
- La risposta compare una parola per volta sul display e viene letta ad alta voce.
- `#` apre le opzioni: modello, motore, voce, nuova conversazione.

Nel pannello a destra c'è la stessa cosa in grande (modello, barra di scaricamento, voce on/off).
Per sapere se il tuo telefono o il tuo PC ce la fa, c'è una pagina apposta:
[`firmware/web/prova-cervello.html`](../firmware/web/prova-cervello.html) — dice se c'è WebGPU, se la
scheda grafica ha `shader-f16`, se il browser sa ascoltare e leggere, e prova una domanda vera.

### I modelli (tutti Apache 2.0, scaricati una volta sola e poi tenuti nella cache del browser)

| Nome sul telefono | Modello | Scarica | Memoria video |
|---|---|---|---|
| Mini 360M | SmolLM2 360M Instruct | ~207 MB | ~380 MB |
| **Base 0.5B** (predefinito) | Qwen2.5 0.5B Instruct | ~290 MB | ~945 MB |
| Pensa 0.6B | Qwen3 0.6B (ragionamento spento) | ~352 MB | ~1,4 GB |
| Grande 1.5B | Qwen2.5 1.5B Instruct | ~880 MB | ~1,6 GB |

Gira con [WebLLM](https://github.com/mlc-ai/web-llm) (Apache 2.0), che usa **WebGPU**: serve Chrome o
Edge aggiornati, su PC o su Android recente. Su un telefono conviene *Mini* o *Base*: i modelli grandi
chiedono più memoria di quella che un browser mobile concede. Dove WebGPU non c'è, AurI lo dice e
rimanda alle altre funzioni.

Un modello da mezzo miliardo di numeri non è Claude: risponde in italiano, tiene il filo di due o tre
battute, e ogni tanto si inventa le cose. Per un 3310 del 2000 che pensa da solo dentro una pagina web,
va benissimo.

---

## Dal telefono (e qui casca l'asino)

Il 99% delle persone apre il simulatore dallo smartphone, quindi conta solo quello che funziona li'.

**Serve https.** Fuori da una connessione sicura il browser **nasconde WebGPU e il microfono**: chi apre
`http://192.168.1.x:8000` dal telefono non vedra' mai il cervello ne' la voce, per quanto il telefono sia
nuovo. Il sito pubblico e' su https e quindi va; per provare dalla rete di casa serve un certificato
(oppure si prova dal PC su `localhost`, che il browser considera sicuro). Il pannello e il display lo
dicono con parole semplici invece di dare un errore muto.

**Dove c'e' WebGPU**: Chrome su Android 12 o piu' nuovo (dalla versione 121, GPU Qualcomm e ARM) e Safari
su iOS 26. Firefox per Android non ce l'ha ancora. Dove manca, l'assistente lo dice e resta il bridge.

**Cosa cambia sul telefono**, in automatico:

- modello **Mini (SmolLM2 360M, 207 MB)** invece di Base: sui browser mobili la memoria della GPU e'
  limitata a buffer da 128 MB ed e' l'unico che gira davvero;
- finestra di contesto a 1024 pezzi invece di 2048, per stare dentro quel limite;
- se sei sotto rete mobile (o hai il risparmio dati acceso) il pannello avvisa prima di scaricare;
- il tasto **Navi si tiene premuto col dito** per parlare: funziona col tocco come col mouse.

**Il permesso del microfono va chiesto dentro un tocco**, se no su iPhone l'ascolto parte e muore subito:
per questo nel pannello c'e' il pulsante **Prova il microfono**, che chiede il permesso nel momento giusto
e dice come e' andata. Se il permesso manca, sul display compare "Microfono no" e si scrive col T9.

## La risposta comincia prima che il modello abbia finito

Un modello piccolo scrive piano: aspettare la risposta intera in silenzio fa sembrare il telefono rotto.
Allora, come fanno gli assistenti vocali:

1. appena mandi la domanda AurI dice subito una parola ("Vediamo...");
2. mentre il modello scrive, il testo compare sul display pezzo per pezzo;
3. **ogni frase finita viene letta ad alta voce subito**, senza aspettare le altre: si taglia al primo
   `.`, `!`, `?`, `:` o `;` (o dopo 110 caratteri se il modello non mette punteggiatura) e si mette in
   coda alla voce del browser, che le legge una dietro l'altra.

Cosi' il tempo prima di sentire qualcosa passa dalla risposta intera alla prima frase. E' la tecnica
consigliata un po' da tutti per mettere insieme un modello di linguaggio e una voce
(vedi le fonti in fondo).

## 2. In casa: il bridge con llama.cpp

Sul PC (o sul Raspberry) il cervello è [llama.cpp](https://github.com/ggml-org/llama.cpp) con un modello
Qwen3 in formato GGUF. Si installa tutto dentro la cartella del progetto:

```powershell
cd bridge
.\setup_llm.ps1              # llama.cpp (circa 25 MB) + Qwen3 1.7B Q4_K_M (circa 1,1 GB)
.\setup_llm.ps1 -Modello piccolo   # Qwen3 0.6B, per PC lenti
.\run.ps1                    # il bridge, come sempre
```

(su Linux e Raspberry: `./setup_llm.sh`, `./setup_llm.sh piccolo`.)

Il bridge avvia `llama-server` da solo alla prima domanda e parla con lui in formato OpenAI
(`/v1/chat/completions`). In `config.json`:

```json
"assist_engine": "auto",            // auto | local | gemini
"llm_url": "http://127.0.0.1:8080",
"llm_model": "models/llm/Qwen3-1.7B-Q4_K_M.gguf",
"llm_autostart": true
```

`auto` sceglie il cervello locale se c'è, altrimenti Gemini (se hai la chiave), altrimenti lo dice.
Tutto il resto del bridge non cambia: la voce resta Whisper + Piper in locale, la console Claude resta
Claude, la domotica resta Home Assistant.

**Domotica con un modello piccolo.** I modelli da 1-2 miliardi di numeri sbagliano spesso le chiamate a
funzione, quindi il bridge usa un trucco più semplice: nel prompt chiede di finire la frase con
`[CASA on light.soggiorno]`, e poi esegue e cancella quel pezzo dalla risposta. Funziona anche su
Qwen3 0.6B.

Per cancellare tutto: `bridge/models/llm/` (binari e pesi stanno solo lì, dentro Z:).

---

## 3. Sul Nokia vero

Il telefono con l'ESP32-S3 può far girare un modello piccolissimo preso dalla **microSD** (racconti, non
risposte: è un giocattolo bellissimo da vedere) e, per le risposte vere, chiede al bridge di casa via
Wi-Fi. Tutti i dettagli, i pin, il modulo C e i numeri veri:
[`hardware/cervello/README.md`](../hardware/cervello/README.md).

---

## Com'è fatto dentro

```
firmware/auri/cervello.py       un solo cervello per tutti: sceglie il motore, pulisce il testo per il display
firmware/apps/assistente.py     l'app: accensione, ascolto, T9, risposta a pezzi, lettura ad alta voce
firmware/hal/web.py             ponte verso il browser (ai_*, hear_*, speak)
firmware/hal/esp32.py           ponte verso la microSD e il modulo C auri_llm
firmware/web/auri-llm.js        WebLLM nel browser + voce del browser + pannello
firmware/web/auri-llm-worker.js il modello gira qui, in un worker, per non bloccare il telefono
bridge/auri_bridge.py           motore 'local' (llama.cpp) accanto a Gemini e Claude
hardware/cervello/              il cervello del telefono vero (modulo C, microSD, prova sul PC)
```

L'app non sa che motore ha sotto: chiede, aspetta, mostra. Per questo la stessa schermata funziona nel
browser, nella finestra del PC e sul telefono.

Prove: `py tools/test_cervello.py` (assistente e motori, immagini in `tmp/lcd/cervello/`),
`py tools/test_bridge_cervello.py` (il bridge con un llama.cpp finto: risposta, memoria, comandi casa)
e `py tools/test_llm_esp32.py` (formato dei pesi del telefono vero).

## Quanto va veloce (misurato il 25/11/2026)

| Dove | Modello | Prima accensione | Velocita' |
|---|---|---|---|
| Browser, grafica integrata Intel (questo PC) | Qwen2.5 0.5B | 290 MB scaricati in ~36 s, accensione ~43 s | ~1 pezzo/s: si guarda, non si usa |
| Browser, scheda grafica dedicata | Qwen2.5 0.5B | come sopra | molto piu' veloce (non misurato qui) |
| Bridge di casa, solo CPU | Qwen3 1.7B Q4_K_M | llama-server pronto in ~9 s | **~8 pezzi/s**, prima frase in 2-4 s |

Il modello si scarica **una volta sola** e resta nella cache del browser: alla seconda visita il
cervello si accende in pochi secondi e funziona anche senza rete.

Per questo il pannello del simulatore adesso **dice che scheda grafica sta usando** (e avvisa prima di
scaricare 290 MB se WebGPU gira in software, come su macchine virtuali e desktop remoti). Sorpresa
onesta: su questo PC la scheda c'e' (integrata Intel) ma il modello va comunque a circa un pezzo al
secondo, otto volte piu' lento del bridge sulla stessa macchina - llama.cpp sulla CPU e' scritto
apposta e vince. Il cervello nel browser serve a far provare AurI a chi apre il simulatore senza
installare niente; per usarlo davvero, il bridge di casa.

Una nota onesta sui modelli piccoli: a 0,5 miliardi di parametri l'italiano e' approssimativo e se non
gli si dice bene chi e' si inventa di chiamarsi come gli assistenti famosi. Per questo il messaggio di
sistema dice il nome per primo ("Ti chiami AurI... non hai altri nomi") e gli si mette davanti un botta
e risposta di esempio: con quello risponde "Sono AurI". Col modello del bridge (1,7 miliardi) non
serve nemmeno l'esempio.

## Privacy e costi

- Il modello nel browser **non manda niente a nessuno**: scarica i pesi una volta da HuggingFace e poi
  lavora in locale. Le domande non escono dal dispositivo.
- L'**ascolto** nel browser usa il riconoscimento vocale di Chrome, che manda l'audio ai server di
  Google: è scritto nel pannello e nella nota sulla privacy del simulatore. Chi non lo vuole scrive
  col T9, che è tutto in locale.
- Il bridge di casa non manda niente fuori: llama.cpp, Whisper e Piper girano sul PC.
- Costo totale: zero. Nessuna chiave, nessun account, nessun limite giornaliero.

## Fonti

- WebLLM: <https://github.com/mlc-ai/web-llm> (Apache 2.0) — modelli preparati da MLC-AI.
- Qwen2.5 / Qwen3 (Apache 2.0): <https://huggingface.co/Qwen>; SmolLM2 (Apache 2.0): HuggingFaceTB.
- llama.cpp: <https://github.com/ggml-org/llama.cpp> (MIT), build ufficiali per Windows e Linux.
- GGUF Qwen3 di unsloth (Apache 2.0): <https://huggingface.co/unsloth/Qwen3-1.7B-GGUF>.
- Web Speech API (ascolto e lettura del browser): <https://developer.mozilla.org/docs/Web/API/Web_Speech_API>.
- WebGPU nei browser e sui telefoni: <https://web.dev/blog/webgpu-supported-major-browsers>,
  <https://github.com/gpuweb/gpuweb/wiki/Implementation-Status>, <https://caniuse.com/webgpu>
- Riconoscimento vocale sul telefono (limiti e ripieghi): <https://caniuse.com/speech-recognition>,
  <https://webreflection.medium.com/taming-the-web-speech-api-ef64f5a245e1>
- Leggere la risposta frase per frase mentre il modello scrive:
  <https://docs.inworld.ai/tts/best-practices/latency>,
  <https://aws.amazon.com/blogs/machine-learning/stream-low-latency-speech-from-ai-agents-using-kokoro-tts-on-amazon-sagemaker-ai/>
