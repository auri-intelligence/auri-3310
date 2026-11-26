# Fotocamera su 84x48: ricerca e confronto

Ricerca di novembre 2026. Domanda: chi ha già fatto fotocamere su display piccoli a 1 bit, e cosa possiamo migliorare nella nostra catena (ritaglio 7:4, contrasto 1%-99%, Atkinson/Bayer/soglia).

## 1. Cosa esiste

### Fotocamere su display minuscoli
- **Game Boy Camera** (128x112, 4 grigi). Il sensore M64282FP fa da solo **edge enhancement** (orizzontale, verticale o 2D, con intensità regolabile), poi guadagno e livelli; il dithering usa una **matrice 4x4 di soglie programmabili** (3 soglie per cella, per 4 grigi). È ordered dithering: stabile nel tempo, niente sfarfallio. [Pan Docs](https://gbdev.io/pandocs/Gameboy_Camera), [sorgente MAME](https://git.redump.net/mame/plain/src/devices/bus/gameboy/camera.cpp).
- **PD-Camera per Playdate** (1 bit, 320x240): OV7670 su Teensy, che fa il dithering prima di mandare l'immagine. [github.com/t0mg/pd-camera](https://github.com/t0mg/pd-camera). Anche l'articolo di Aras P. sul dither stabile su Playdate: [aras-p.info](https://aras-p.info/blog/2025/02/09/Surface-Stable-Fractal-Dither-on-Playdate/).
- **Progetti MIT Fab Academy** con ESP32 e OLED: QQVGA in GRAYSCALE, buffer in PSRAM, `CAMERA_GRAB_LATEST`, riduzione e Floyd-Steinberg su un buffer float. [camera_60sec.ino](https://fab.cba.mit.edu/classes/863.25/people/SaleemAldajani/finalproject/camera/camera_60sec.ino), [view_camera_oled.ino](https://fab.cba.mit.edu/classes/863.25/people/SaleemAldajani/week11/code/view_camera_oled.ino), [fotocamera compatta](https://fab.cba.mit.edu/classes/863.25/people/CharlesLu/pages/w06.html).
- **Georg Lukas**: ESP32 con dithering a palette ridotta. [op-co.de](https://op-co.de/blog/posts/esp32-ega16-tga/).
- **Webcam con Atkinson in tempo reale**: Evil Mad Scientist (Processing) [evilmadscientist.com](https://www.evilmadscientist.com/2012/dithering/); tool da terminale [dith](https://github.com/nishantjoshi00/dith).

Non ho trovato nessun progetto pubblicato di fotocamera su Nokia 5110/PCD8544 che riporti gli fps: siamo in territorio poco battuto.

### Dithering e stabilità nel tempo
- **Obra Dinn (Lucas Pope)**: Bayer 8x8 per oggetti e blue noise 128x128 per gli ambienti; lo sfarfallio quando la camera si muove era il problema principale. [Hackaday](https://hackaday.com/2022/07/04/dithering-makes-everything-cooler-now-even-animated), [discussione MetaFilter](https://www.Metafilter.com/170872/man-this-dithering-is-stable-as-shit-total-magic-going-on-here).
- **Blue noise spazio-temporale** (NVIDIA, EA SEED): se cambi maschera blue noise in modo indipendente a ogni fotogramma, nel tempo hai rumore bianco, cioè sfarfallio. [arXiv 2112.09629](https://arxiv.org/pdf/2112.09629), [EA SEED EGSR 2022](https://www.ea.com/seed/news/egsr-2022-blue-noise).
- **Halftoning video**: la diffusione d'errore "frame-dependent" (che tiene conto del fotogramma prima) sfarfalla meno di Floyd-Steinberg fotogramma per fotogramma. [EURASIP 2010](https://jivp-eurasipjournals.springeropen.com/articles/10.1155/2010/625191/figures/15), [demo UT Austin](https://users.ece.utexas.edu/~bevans/papers/2011/video/halftones/index.html), [NASA SPIE '93, diffusione temporale](https://webarchive.library.unt.edu/eot2008/20080923033628/http://vision.arc.nasa.gov/publications/spie93.pdf).
- **Gamma**: con soglia a 128 su valori sRGB la luminosità percepita risulta sbagliata, perché 128 vale circa il 22% della luce. [Nigel Tao](https://nigeltao.github.io/blog/2022/gamma-aware-ordered-dithering.html), [Nayuki](https://nayuki.io/page/gamma-aware-image-dithering).

### Prestazioni
- **ESP32-S3 + esp32-camera**: il frame rate dipende da formato, risoluzione, XCLK; Espressif consiglia `fb_count >= 2`. [Espressif DVP](https://docs.espressif.com/projects/esp-techpedia/en/latest/esp-friends/solution-introduction/camera/dvp-camera-solution.html), [FAQ](https://docs.espressif.com/projects/esp-faq/en/latest/application-solution/camera-application.html). Il driver MicroPython che usiamo: [micropython-camera-API](https://github.com/cnadler86/micropython-camera-API).
- **Finestra/scaler hardware dell'OV2640** (`set_res_raw`): il DSP può ritagliare e ridurre già nel sensore, ma ci sono bug segnalati sulla dimensione del buffer. [issue #433](https://github.com/espressif/esp32-camera/issues/433), [registri](https://esp32.com/viewtopic.php?p=150517), [datasheet](https://dl.espressif.com/dl/schematics/Camera_OV2640.pdf).
- **MicroPython viper**: molto più veloce per interi e bit, con `ptr8`/`ptr16`; al massimo 4 argomenti, niente valori predefiniti. [docs speed_python](https://docs.micropython.org/en/v1.13/reference/speed_python.html). Adafruit lo usa per elaborare i fotogrammi della camera: [fruit jam eyeballs](https://learn.adafruit.com/fruit-jam-motion-tracking-eyeballs?view=all).
- **Browser/WebGL**: dithering ordered come shader sulla texture video. [Codrops 2025](https://tympanus.net/codrops/2025/06/04/building-a-real-time-dithering-shader/), [Codrops Efecto 2026](https://tympanus.net/codrops/2026/01/04/efecto-building-real-time-ascii-and-dithering-effects-with-webgl-shaders), [dithered-camera](https://gh.r-mj.com/imkisi/dithered-camera). Floyd-Steinberg su MediaStreamTrackProcessor: [gist](https://gist.github.com/rplacd/1ed41216a177c61bff3f6d83cc07126c). La diffusione d'errore non entra bene in un solo passaggio di shader (è sequenziale).

## 2. Confronto con la nostra implementazione

| Aspetto | Noi | Stato dell'arte | Giudizio |
|---|---|---|---|
| Ritaglio 7:4 centrale | sì | uguale | ok |
| Riduzione (ESP32) | media a blocchi ma campiona solo ~2x2 punti per cella (passo `(x1-x0)//2`) | box filter pieno, o scaler del sensore | quasi ok (da 160x91 a 84x48 i blocchi sono ~1,9 px, quindi poca perdita) |
| Riduzione (browser) | un solo `drawImage` da 320x240 a 84x48 | riduzione a più passi o `imageSmoothingQuality='high'` | rischio di aliasing e moiré |
| Contrasto | stretch 1%-99%, span minimo 24 | uguale (simile al "level control" della Game Boy Camera) | ok, ma cambia a ogni fotogramma, quindi pompa |
| Nitidezza | nessuna | Game Boy Camera: edge enhancement nel sensore | **manca: è la differenza più visibile a 84x48** |
| Gamma/curva | lineare su sRGB, soglia 128 | gamma-aware, o almeno una curva regolabile | da valutare (su LCD riflettente l'sRGB "puro" spesso viene troppo scuro) |
| Atkinson | sì, a scansione normale, errore `>>3` (perde 1/4, quindi più contrasto) | uguale; la serpentina riduce le "scie" | ok |
| Bayer 4x4 | sì | 4x4 (GB Cam) o 8x8 (Obra Dinn) | ok, è il più stabile |
| Stabilità nel tempo | Atkinson ricalcolato da zero a ogni fotogramma, quindi sfarfalla | ordered o blue noise fisso, isteresi | **migliorabile** |
| Velocità ESP32 | Python puro, 3 cicli annidati per pixel più l'array `h` | viper / modulo C | **collo di bottiglia probabile** (stima: centinaia di ms per fotogramma) |
| Browser loop | `requestVideoFrameCallback` con ripiego su rAF, canvas `willReadFrequently` | uguale | ok; worker/OffscreenCanvas inutili a 84x48 |

## 3. Raccomandazioni (ordinate per impatto)

### A. Prestazioni ESP32: portare la catena in viper (impatto alto)
Tutto `dither.py` è codice per pixel in Python puro. Con viper e `ptr8` il guadagno tipico per cicli su interi è di un ordine di grandezza. Prima di tutto bisogna **misurare** `time.ticks_ms()` di `capture()` e di `da_grigi()` separatamente. Esempio di riduzione 160x120 a 84x48 (ritaglio 160x91, offset y 14):

```python
import micropython

@micropython.viper
def riduci_v(src: ptr8, dst: ptr8, oy: int):
    # 160x120 -> 84x48, ritaglio verticale 91 righe; media 2x2 in punto fisso
    for y in range(48):
        sy = oy + (y * 91) // 48
        r0 = sy * 160
        r1 = r0 + 160
        for x in range(84):
            sx = (x * 160) // 84
            s = src[r0 + sx] + src[r0 + sx + 1] + src[r1 + sx] + src[r1 + sx + 1]
            dst[y * 84 + x] = s >> 2
```

Per Atkinson in viper conviene un buffer di errori a 16 bit (`ptr16` con offset +32768, oppure due righe di errore `int` invece di modificare l'immagine), perché viper non ha array firmati comodi. In alternativa, nel nostro modulo C (abbiamo già grafica in C) aggiungere `dither_atkinson(src, buf)`, che resta sotto 1 ms.

### B. Nitidezza prima del dithering (impatto alto sulla qualità)
A 84x48 i contorni sono tutto. Va fatta una unsharp mask leggera (oppure un "edge enhancement" alla Game Boy Camera) **dopo** la riduzione e **prima** del contrasto:

```js
// g: Int16Array 84x48; k ~ 0.5..1.0
for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
  const i = y * W + x;
  const blur = (g[i-1] + g[i+1] + g[i-W] + g[i+W]) >> 2;
  out[i] = g[i] + ((g[i] - blur) * k);
}
```
In alternativa a costo zero sull'OV2640 si possono usare `sensor.set_sharpness()` (dove supportato) e `set_contrast(2)`.

### C. Stabilità nel tempo (impatto alto per la "vista dal vivo")
1. **Contrasto con memoria**: invece di usare lo, hi nuovi a ogni fotogramma, fare una media mobile: `lo = lo*0.8 + lo_nuovo*0.2` (in interi: `lo += (n - lo) >> 2`). Toglie il "pompaggio".
2. **Isteresi sul pixel**: un pixel cambia stato solo se supera la soglia di un margine (per esempio ±12) rispetto allo stato precedente. Funziona benissimo con soglia e Bayer, e riduce lo sfarfallio dell'Atkinson sulle zone piatte:
   ```python
   on = v < t - 12 if prev_on else v < t + 12
   ```
3. **Proposta di default**: usare Bayer (o una maschera blue noise 8x8/16x16 **fissa**, mai cambiata tra i fotogrammi) per l'anteprima dal vivo, e Atkinson solo per lo scatto. È quello che fanno GB Camera e Obra Dinn.

### D. Riduzione di qualità nel browser (impatto medio)
Un `drawImage` diretto 320 a 84 campiona male. Due opzioni:
- `cx.imageSmoothingQuality = 'high'` (Chrome usa un filtro migliore);
- riduzione a due passi: prima a 168x96 su un canvas intermedio, poi a 84x48 (equivale a una media 2x2).
Anche la conversione in grigio va fatta **prima** della riduzione, se si vuole essere identici all'ESP32 (che riceve già grigio): differenza minima, solo per coerenza.

### E. Curva di gamma / luminosità (impatto medio, da provare a occhio)
Su un LCD riflettente senza retroilluminazione forte, il dithering "matematicamente corretto" in luce lineare tende a dare immagini troppo chiare o troppo scure. Meglio una **LUT a 256 voci** con gamma regolabile (0,8-1,4) applicata insieme allo stretch del contrasto: costa zero, perché lo stretch è già una LUT.
```python
lut = bytes(min(255, int(255 * ((i / 255) ** gamma))) for i in range(256))
```

### F. Atkinson serpentino (impatto basso-medio)
Scansione alternata sinistra-destra e destra-sinistra sulle righe: meno scie diagonali. È un cambiamento piccolo (invertire i vicini x+1, x+2, x-1 sulle righe dispari).

### G. Sensore e driver (impatto medio, rischio medio)
- Tenere GRAYSCALE QQVGA (niente JPEG: decodificare costa più di tutto il resto). `fb_count=2` va bene; verificare `grab_mode=LATEST` per avere sempre l'ultimo fotogramma e non uno vecchio.
- Possibile ma rischioso: finestra hardware OV2640 (`set_res_raw`) per far uscire già ~168x96 dal sensore, ma ci sono bug noti sul buffer (issue #433). Da provare solo dopo A.
- Abbassare `xclk_freq` non serve; semmai provare `set_gainceiling`/AEC per evitare rumore al buio, che il dithering amplifica.

### H. Browser: cosa NON serve
Worker, OffscreenCanvas e WebGL non portano vantaggi a 84x48 (4032 pixel, meno di 1 ms in JS). WebGL avrebbe senso solo per anteprime grandi, e comunque solo con dithering ordered.

## 4. Ordine di lavoro suggerito
1. Misurare i tempi sull'ESP32, poi viper/C per la riduzione e il dithering (A).
2. Media mobile del contrasto e isteresi (C1, C2): poche righe, effetto grande.
3. Unsharp mask leggera (B), con lo stesso codice in JS e in Python.
4. Bayer come default in anteprima, Atkinson allo scatto (C3).
5. LUT gamma e riduzione browser a due passi (D, E); poi serpentina (F).
