# Il cervello dentro il telefono vero (ESP32-S3 + microSD)

Qui c'è la parte che riguarda il Nokia vero: un modello di linguaggio che gira **dentro** il telefono,
con i pesi su una microSD, più il collegamento Wi-Fi al cervello di casa quando serve qualcosa di serio.

Il resto del cervello (simulatore nel browser e bridge sul PC) è spiegato in
[`docs/cervello-locale.md`](../../docs/cervello-locale.md).

> Stato: **il codice c'è, l'hardware no.** Niente di questa cartella è ancora stato provato su una
> scheda vera: si prova in fase H0, insieme al resto del prototipo. I conti e le velocità qui sotto
> vengono da progetti di altri che hanno già fatto girare llama2.c su ESP32-S3 (link in fondo).

## Cosa può e cosa non può fare un ESP32-S3

L'ESP32-S3 ha 8 MB di PSRAM e 240 MHz. Vuol dire:

| Modello | Pesi | Dove sta | Velocità attesa |
|---|---|---|---|
| stories260K (llama2.c) | ~1 MB | tutto in PSRAM | ~20-25 pezzi al secondo |
| stories260K da flash | ~1 MB | flash, senza PSRAM | ~2 pezzi al secondo |
| stories15M | ~58 MB | non entra: a pezzi dalla microSD | ~0,5 pezzi al secondo |
| Qwen2.5 0.5B (quello del browser) | ~290 MB | **impossibile** | — |

Quindi, detto chiaro: **sul telefono, da solo, non gira un assistente vero.** Gira un modello giocattolo
che inventa frasi e raccontini. È bellissimo da vedere (il 3310 che scrive da solo sul display, senza
rete) ed è onesto chiamarlo "AurI nano". L'assistente che risponde davvero alle domande gira sul PC di
casa (`bridge/`, llama.cpp, Qwen3 1.7B) e il telefono ci parla via Wi-Fi: è gratis uguale, solo che il
cervello grosso sta in salotto invece che in tasca.

## I tre livelli, sul telefono

1. **AurI nano** — modulo C `auri_llm` + pesi dalla microSD. Funziona anche in mezzo a un bosco,
   senza rete. Risponde piano e dice cose semplici.
2. **Bridge di casa** — Wi-Fi verso `bridge/auri_bridge.py` con llama.cpp: risposte vere, voce
   (Whisper + Piper), domotica. Gratis, tutto in casa.
3. **Niente di tutto questo** — il telefono lo dice sul display invece di fingere.

La scelta è in Impostazioni (voce `Cervello`: Auto, Locale, Casa) ed è la stessa del simulatore.

## Il modulo C: `auri_llm`

`auri_llm/auri_llm.c` è un transformer in stile [llama2.c](https://github.com/karpathy/llama2.c)
scritto per MicroPython: legge un checkpoint float32 (il formato di llama2.c) e genera **un pezzo di
testo per chiamata**, così AurI OS continua a disegnare il display e a leggere i tasti mentre pensa.

I pesi non li legge lui dal filesystem: glieli passa Python a pezzi (`begin`, `feed`, `end`). In questo
modo funziona con la microSD montata da MicroPython, con la flash interna o con qualunque altra cosa.

```python
import auri_llm
auri_llm.tokenizer(open('/sd/auri/cervello/tok512.bin', 'rb').read())
auri_llm.begin(os.stat('/sd/auri/cervello/stories260K.bin')[6])
# ... auri_llm.feed(pezzo) per ogni blocco letto dal file ...
auri_llm.end()
auri_llm.start('C era una volta un telefono', 0.9, 0.9, 120)
while True:
    p = auri_llm.next()       # un pezzo di testo, oppure None quando ha finito
    if p is None:
        break
    print(p, end='')
```

In AurI OS tutto questo lo fa già `firmware/hal/esp32.py` (`ai_ok`, `ai_start`, `ai_info`, `ai_ask`,
`ai_poll`): l'app dell'assistente non sa nemmeno che sotto c'è un ESP32.

### Compilarlo dentro MicroPython

Serve l'ambiente ESP-IDF e i sorgenti di MicroPython (nulla di tutto ciò entra nel repo).

```bash
# 1. MicroPython + ESP-IDF, una volta sola
git clone https://github.com/micropython/micropython
cd micropython && make -C mpy-cross
cd ports/esp32

# 2. build con il modulo di AurI e la PSRAM accesa
idf.py -D MICROPY_BOARD=ESP32_GENERIC_S3 \
       -D MICROPY_BOARD_VARIANT=SPIRAM_OCT \
       -D USER_C_MODULES=Z:/Shared/progetti-personali/nokia-auri-3310/hardware/cervello/auri_llm/micropython.cmake \
       build

# 3. sul telefono
idf.py -p COM5 flash
```

La PSRAM **ottale** (`SPIRAM_OCT`) non è un dettaglio: senza, i pesi non ci stanno e il modello va dieci
volte più piano. Verifica con `import esp32; esp32.idf_heap_info(esp32.HEAP_DATA)`.

Per provare il codice senza hardware c'è `prova_llm.py`: stessi conti in Python, sul PC
(`py tools/test_llm_esp32.py` costruisce un mini-modello finto e controlla che i pesi siano al posto giusto).

## La microSD

Lettore SPI collegato così (pin di banco, da confermare in H0; stanno in `firmware/hal/board.py`):

| microSD | ESP32-S3 |
|---|---|
| SCK | GPIO 36 |
| MOSI (DI) | GPIO 35 |
| MISO (DO) | GPIO 37 |
| CS | GPIO 34 |
| VCC | 3V3 |
| GND | GND |

Scheda formattata **FAT32** (una da 1-8 GB va benissimo: i file sono piccoli).

```
/auri/cervello/stories260K.bin     i pesi
/auri/cervello/tok512.bin          il tokenizer
/auri/os/                          (facoltativo) tutto AurI OS, per farlo partire dalla scheda
```

Si prepara dal PC:

```bash
py hardware/cervello/prepara_sd.py E:\ --scarica mini --si      # pesi (1 MB, licenza MIT)
py hardware/cervello/prepara_sd.py E:\ --os                     # ci mette anche AurI OS
```

### Far partire AurI dalla scheda

Con `--os` la scheda contiene anche il codice. Nel `main.py` del telefono basta montare la SD e
aggiungerla al percorso **prima** di importare AurI OS:

```python
import sys, os, machine
from hal import board
try:
    sd = machine.SDCard(slot=2, sck=machine.Pin(board.SD_SCK), mosi=machine.Pin(board.SD_MOSI),
                        miso=machine.Pin(board.SD_MISO), cs=machine.Pin(board.SD_CS))
    os.mount(sd, '/sd')
    sys.path.insert(0, '/sd/auri/os')     # il codice sulla scheda vince su quello in flash
except Exception as e:
    print('microSD:', e)                  # senza scheda si parte lo stesso dalla flash
```

Così si aggiorna il telefono cambiando i file sulla scheda, senza riflashare niente. Se la scheda non
c'è, il telefono parte dalla flash come sempre: la scheda è un di più, non un pezzo obbligatorio.

## Da fare quando arriva l'hardware (H0)

1. Verificare i pin della microSD e del display sul prototipo vero.
2. Compilare MicroPython con `auri_llm` e misurare davvero i pezzi al secondo.
3. Controllare quanto dura la batteria mentre il modello gira (la PSRAM a 80 MHz consuma).
4. Provare il risveglio: dopo il deep sleep i pesi vanno ricaricati dalla scheda (qualche secondo).
5. Valutare i pesi in int8 (la metà della memoria, il doppio della velocità) e la lettura a strati
   dalla microSD per modelli più grandi.

## Fonti (progetti di altri, non copiati qui)

- [karpathy/llama2.c](https://github.com/karpathy/llama2.c) — MIT: il formato dei pesi e l'algoritmo.
- [karpathy/tinyllamas](https://huggingface.co/karpathy/tinyllamas) — MIT: i modelli stories260K e stories15M.
- [DaveBben/esp32-llm](https://github.com/DaveBben/esp32-llm) — llama2.c su ESP32-S3, ~19 pezzi al secondo
  usando i due core e le istruzioni ESP-DSP (nessuna licenza dichiarata: guardato, non copiato).
- [Circuit-Digest/ESP32-Tiny-LLM](https://github.com/Circuit-Digest/ESP32-Tiny-LLM) e il loro
  [confronto fra schede](https://circuitdigest.com/articles/running-260K-tiny-llm-on-esp32): 2,33 pezzi
  al secondo dalla flash contro 22 con la PSRAM ottale.
- [Deconstructing llama2.c on ESP32-S3](https://ajv009.com/blog/0018-decontructing-llama2-c-and-exp32-llm/) —
  un modello da 15M letto a strati dalla microSD: circa 0,5 pezzi al secondo.
