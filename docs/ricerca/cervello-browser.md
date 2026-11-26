# Cervello nel browser del telefono: cosa esiste e cosa conviene fare

Ricerca di fine novembre 2026. Il codice non è stato toccato: questo file contiene solo dati e consigli.
Quando un dato non è stato verificato in una fonte, lo dico.

## 1. Riassunto per chi ha fretta

- **WebLLM resta una scelta sensata** per AurI: ha i prefill più veloci tra i motori nel browser. Sui telefoni i problemi veri sono tre: la memoria GPU (il limite di 128 MB per binding), i driver (f16) e gli shader da compilare.
- **La qualità dell'italiano conta più della velocità.** Con modelli sotto i 400 MB la differenza la fanno il prompt, i parametri di generazione e risposte corte. Cambiare motore aiuta poco.
- **Da provare subito:** Qwen3-0.6B con il ragionamento spento (`/no_think`) come modello predefinito sui telefoni, contesto a 1024 (o anche 512), `max_tokens` basso e penalità più leggere. SmolLM2 non va usato per l'italiano.
- **Chrome Built-in AI (Gemini Nano)** su Chrome per Android **non c'è ancora**. Si può tenere come ripiego automatico per il PC.
- **La voce:** per l'italiano le API del browser restano la via più pratica. Le alternative tutte locali (Whisper tiny/base e Piper `it_IT`) funzionano, ma pesano e aggiungono latenza.

## 2. Cosa esiste (con link)

| Motore | Come gira | Telefono | Note |
|---|---|---|---|
| **WebLLM** (MLC) | WebGPU, kernel compilati da TVM | sì, con modelli piccoli | Ha il prefill più veloce (kernel fusi). Sono noti i problemi di `maxStorageBufferBindingSize` su Android ([issue #209](https://github.com/mlc-ai/web-llm/issues/209)) e di `mapAsync` ([issue #497](https://github.com/mlc-ai/web-llm/issues/497), ancora aperta). |
| **Transformers.js v3** (Hugging Face) | ONNX Runtime Web, WebGPU o WASM | sì | Ha molti modelli ONNX ([guida WebGPU](https://huggingface.co/docs/transformers.js/guides/webgpu)). Gemma-3-270M in fp16/q4f16 su WebGPU dà **testo spazzatura**, mentre in WASM funziona ([onnxruntime #26732](https://github.com/microsoft/onnxruntime/issues/26732)). |
| **ONNX Runtime Web** | è il motore sotto Transformers.js | sì | Usarlo direttamente conviene solo con un modello ONNX già pronto. |
| **wllama** (llama.cpp in WASM) | CPU, multi-thread | sì, lento ma stabile | Legge i file GGUF. I thread richiedono gli header COOP/COEP ([unpkg README](https://app.unpkg.com/@wllama/wllama@3.6.1/files/README-dev.md)). Qwen3-0.6B Q4_K_M pesa circa 400 MB. |
| **llama.cpp WebGPU ("LlamaWeb")** | WebGPU dentro llama.cpp | sì, 4-17 tok/s nella fascia "bassa" | Paper del maggio 2026 ([arXiv 2605.20706](https://arxiv.org/html/2605.20706)). Rispetto a WebLLM ha un decode più veloce del 54% e usa circa la metà della memoria, ma il prefill è al 49%. Carica i pesi da OPFS a pezzi da 1 MB. |
| **MediaPipe LLM Inference** | WebGPU, modelli `.task` | sì | È in **sola manutenzione** ([guida](https://ai.google.dev/edge/mediapipe/solutions/genai/llm_inference/web_js)). Supporta Gemma 3 1B int4 QAT ([blog Google](https://developers.googleblog.com/es/gemma-3-on-mobile-and-web-with-google-ai-edge)). |
| **LiteRT-LM JS** (`@litert-lm/core`) | WebGPU | anteprima | È il successore di MediaPipe ([doc](https://ai.google.dev/edge/litert-lm/js)). Per ora supporta solo i Gemma 4 E2B/E4B, troppo grandi per un Android 10. |
| **Chrome Prompt API** (Gemini Nano) | modello del browser | **no su Android** | Le [doc ufficiali](https://developer.chrome.com/docs/ai/prompt-api) dicono che Chrome per Android non è supportato. Su Android nativo esiste solo ML Kit GenAI ([blog](https://android-developers.googleblog.com/2025/10/ml-kit-genai-prompt-api-alpha-release.html)), non dal web. |
| **WebNN** | NPU/GPU tramite il sistema | sperimentale | Non è ancora una strada pratica per gli LLM sui telefoni. |

## 3. Confronto con la nostra implementazione

Cosa facciamo già bene, perché coincide con quello che suggeriscono le fonti:
- usiamo modelli piccoli e il **contesto a 1024 sul telefono**. È lo stesso principio dei modelli `-1k` di WebLLM, creati proprio per stare sotto i 128 MB per binding (issue #209);
- usiamo **f32 sui telefoni**. Gli errori dell'f16 sono documentati su Mali, Adreno e Apple (in LlamaWeb serve l'accumulo in f32; Gemma-270M fp16 si rompe in ORT). Anche WebLLM consiglia f32 quando `shader-f16` è dubbio;
- abbiamo il ripiego automatico, il riscaldamento e il worker. I crash da OOM e il "device lost" vanno intercettati: WebLLM lo fa dalla 0.2.36 (PR #402);
- usiamo **IndexedDB** al posto della Cache API. È una scelta ragionevole. OPFS sarebbe meglio per i file grandi (lo usa LlamaWeb), ma WebLLM non lo supporta.

Cosa manca o si può migliorare:
1. Nel cervello, il modello predefinito sui telefoni è Base, cioè Qwen2.5-0.5B. Per l'italiano **Qwen3-0.6B senza ragionamento** di solito è migliore: è addestrato su 119 lingue e pesa solo circa 60 MB in più. Va comunque verificato con un test nostro, perché non ho trovato un benchmark italiano pubblico per i modelli sotto 1B. La classifica [Evalita-LLM](https://arxiv.org/abs/2502.02289) è il posto dove guardare.
2. **SmolLM2-360M è quasi solo inglese.** Che "si ripeta e dica frasi senza senso" in italiano è normale. Come ripiego andrebbe bene solo per comandi molto brevi, oppure andrebbe sostituito.
3. `repetition_penalty 1.15` insieme a `frequency_penalty 0.6` sono **troppo forti** per un modello piccolo. Fanno saltare parole comuni e articoli, e la frase diventa strana. Meglio tenerne una sola, e debole.
4. I 18 s del primo pezzo di risposta sono soprattutto **compilazione degli shader e caricamento dei pesi**. Il codice non può ridurre molto la compilazione, ma può nasconderla (punto 4.3).

## 4. Raccomandazioni ordinate per impatto

### 4.1 Qualità delle risposte (impatto alto)
- Sul telefono usare **Qwen3-0.6B q4f32** con il ragionamento spento, oppure tenere Qwen2.5-0.5B e fare un test A/B con 20 domande italiane fisse.
- Usare un prompt di sistema corto in italiano, con 2-3 esempi di risposte da una o due frasi. Fissare `max_tokens` a 60-80 sul telefono.
- Parametri consigliati:
```js
// Qwen3 senza ragionamento (valori consigliati da Qwen per il "non-thinking")
{ temperature: 0.7, top_p: 0.8, max_tokens: 80,
  repetition_penalty: 1.05, frequency_penalty: 0 ,
  messages: [{role:'system', content:'Sei AurI... Rispondi in italiano, massimo due frasi. /no_think'}, ...] }
```
- Fuori da WebLLM ci sono candidati migliori per l'italiano: **Gemma 3 1B int4** (circa 530 MB, multilingue, con MediaPipe o Transformers.js) e **Llama 3.2 1B**. Pesano il doppio e su un Android 10 rischiano lo stesso crash del 1.5B. Gemma 3 270M è piccolissimo ma in italiano è debole, e in fp16 su WebGPU è rotto.

### 4.2 Stabilità sui telefoni (impatto alto)
- Prima di caricare il modello conviene leggere i limiti della GPU e scegliere di conseguenza:
```js
const a = await navigator.gpu.requestAdapter();
const L = a.limits;
// su molti Android: 128 MB
if (L.maxStorageBufferBindingSize < 256 * 2**20) { chatOpts.context_window_size = 512; }
```
- Per prevenire il "mapAsync unmapped" e il "device lost":
  - un solo motore alla volta, con `engine.unload()` prima di ricaricare;
  - niente rendering WebGPU in parallelo;
  - non generare mentre la pagina è nascosta (`visibilitychange`), perché Android sospende la GPU;
  - ascoltare `device.lost` e ricreare l'engine una volta sola, poi passare al ripiego.
- Valutare `prefill_chunk_size` più piccolo (per esempio 256) nella configurazione del modello, se il crash avviene sul primo messaggio lungo. Il KV cache cresce con `context_window_size`, quindi 1024 → 512 dimezza la sua memoria.
- Tenere l'f32 sui telefoni.

### 4.3 Velocità percepita (impatto medio)
- **Riscaldamento all'avvio della pagina**, non alla prima domanda. Si può già fare mentre l'utente guarda il menu: gli shader compilati restano nella cache di Chrome, quindi le volte dopo l'attesa si accorcia.
- Mandare al TTS la prima frase appena è completa (lo facciamo già) e limitare la prima risposta a una frase.
- Prompt di sistema corto: ogni token del prompt costa prefill. Su WebLLM si può anche riusare la conversazione, senza rimandare tutta la storia ogni volta.
- Mostrare una risposta "di cortesia" pronta (es. "Ci penso...") mentre arriva il primo token.

### 4.4 Cache (impatto basso)
- IndexedDB va bene. Conviene aggiungere `navigator.storage.persist()`, così Android non cancella il modello quando lo spazio scarseggia:
```js
if (navigator.storage && navigator.storage.persist) await navigator.storage.persist();
```

### 4.5 Voce
- **STT:** `SpeechRecognition` in italiano su Chrome Android funziona bene, ma usa i server Google. Per una versione tutta locale c'è Whisper tiny/base con Transformers.js su WebGPU ([whisper-web](https://github.com/xenova/whisper-web)). Base pesa circa 150 MB e aggiunge qualche secondo, quindi su un telefono vecchio non conviene. Per Moonshine non ho trovato un supporto all'italiano confermato.
- **TTS:** `speechSynthesis` resta la via più leggera. La migliore alternativa locale è Piper in WASM ([piper-tts-web](https://github.com/Mintplex-Labs/piper-tts-web)) con una voce `it_IT` (es. paola o riccardo, circa 60 MB). Attenzione a Kokoro: per le lingue diverse dall'inglese alcune versioni web mandano il testo a un servizio di fonemizzazione esterno ([offlinetts](https://offlinetts.com/app/kokoro/)), quindi non sono davvero locali.

## 5. Cosa non ho trovato
- Un benchmark pubblico di WebLLM, Transformers.js e wllama sullo stesso telefono Android con modelli sotto 1B.
- Una issue di WebLLM specifica su Adreno con f16: i problemi f16 sono documentati in altri motori.
- Una data per la Prompt API su Chrome Android.
