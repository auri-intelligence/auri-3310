// Il cervello di AurI gira qui dentro, in un worker, cosi' il telefono (MicroPython) non si blocca
// mentre il modello pensa. La versione di WebLLM deve essere la stessa di auri-llm.js.
import * as webllm from 'https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.88/lib/index.js';

const handler = new webllm.WebWorkerMLCEngineHandler();
self.onmessage = msg => handler.onmessage(msg);
