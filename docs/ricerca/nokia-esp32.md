# AurI-3310: prestazioni di MicroPython su ESP32-S3, cosa esiste e cosa conviene fare

Ricerca di novembre 2026. Ho confrontato il nostro codice (`firmware/main.py`, `hal/esp32.py`, `auri/net.py`, `auri/core.py`) con documentazione, forum e progetti pubblici. Il codice non è stato toccato.

## 1. Cosa dicono le fonti

**Velocità di MicroPython**
- La guida ufficiale "Maximising MicroPython speed" spiega `@micropython.native` (circa 2 volte il bytecode), `@micropython.viper` (molto più veloce sui calcoli con interi e bit), `const()`, la preallocazione dei buffer, `memoryview` e la cache dei metodi in variabili locali: https://docs.micropython.org/en/latest/reference/speed_python.html
- Il benchmark di Miguel Grinberg (MicroPython 1.25) mostra che l'ESP32-S3 a volte batte il Pico 2W e a volte perde. Il risultato dipende molto dal tipo di codice: https://blog.miguelgrinberg.com/post/benchmarking-micropython
- Su RP2040 Adafruit ha misurato Viper a circa 20 volte il bytecode su Mandelbrot: https://learn.adafruit.com/circuitpython-turbo/measured-speed
- Gli esperimenti di glenn20 su ESP32 (PSRAM, velocità, memoria): https://github.com/glenn20/upy-esp32-experiments
- Per la PSRAM octal (il nostro N8R8) serve il firmware variante SPIRAM_OCT: https://micropython.org/download/ESP32_GENERIC_S3/ . Non ho trovato numeri affidabili che confrontino octal e quad. Un utente segnala rallentamenti quando i buffer grandi finiscono in PSRAM: https://esp32.com/viewtopic.php?p=150127 . In pratica i buffer piccoli e "caldi" (lo schermo da 504 byte) conviene allocarli all'avvio, quando la RAM interna è ancora libera.
- Ottimizzazione lato ESP-IDF (cache, flash QIO/OPI, 240 MHz): https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/performance/speed.html

**Moduli nativi e codice congelato**
- I moduli nativi dinamici sono file `.mpy` che contengono codice C compilato e si caricano con `import`, senza ricompilare il firmware. L'S3 è xtensawin, che è supportato: https://docs.micropython.org/en/latest/develop/natmod.html
- Con i moduli congelati (manifest.py) il bytecode resta in flash e non occupa RAM. Si caricano più in fretta di un `.mpy` messo sul filesystem: https://docs.micropython.org/en/latest/reference/manifest.html

**Display PCD8544**
- Il driver di mcauser (MIT) usa framebuf MONO_VLSB in indirizzamento orizzontale, come noi: https://github.com/mcauser/micropython-pcd8544
- Esiste anche il driver CircuitPython di Adafruit: https://docs.circuitpython.org/projects/pcd8544/en/latest/api.html
- Il PCD8544 regge circa 4 MHz di SPI. 504 byte a 4 MHz sono circa 1 ms per frame, quindi lo schermo non è il collo di bottiglia. Spedire solo i banchi cambiati (6 righe da 84 byte) fa risparmiare poco tempo, ma serve a ridurre consumi e lavoro del bus.

**Thread, GIL e socket**
- Doc `_thread`: https://docs.micropython.org/en/latest/library/_thread.html
- Sull'ESP32 tutti i thread MicroPython girano sullo stesso core e condividono il GIL: https://forum.micropython.org/viewtopic.php?p=48667
- La lettura di una socket rilascia il GIL solo se dovrebbe davvero bloccarsi (commit esp32/modsocket). `connect`, la risoluzione DNS e TLS possono invece tenere fermo l'interprete per un po'.
- La PR #15476 corregge l'ingiustizia nel GIL, cioè un thread che lo riprende subito e affama gli altri. Serve un MicroPython recente: https://github.com/micropython/micropython/pull/15476
- Espressif consiglia asyncio streams o socket non bloccanti per la rete: https://docs.espressif.com/projects/esp-vision/en/latest/esp32p4/api-reference/micropython.html

**Energia**
- Guida low-power ESP32 (fork tve): a 80 MHz con il power management si scende a circa 12 mA da fermo e a circa 115 mA con la radio accesa. `lightsleep` sospende Wi-Fi e I/O: https://micropython-tve.readthedocs.io/en/tve/library/esp32-lowpower.html
- Power management in ESP-IDF: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/power_management.html

**Progetti simili** (esempi di architettura, non li ho misurati)
- Thumby (RP2040, schermo 72x40 monocromatico, giochi in MicroPython con framebuf): è il caso più vicino al nostro.
- Badger 2040 (e-ink, sleep tra un aggiornamento e l'altro), PicoSystem, M5Stack Cardputer (ESP32-S3, firmware MicroPython/UIFlow), Tildagon di EMF (ESP32-S3, app MicroPython con asyncio e un ciclo update/draw).
- Il modello comune è un ciclo a tempo fisso (update + draw), il disegno con framebuf o in C e la rete in asyncio o fuori dal ciclo dei frame.

## 2. Confronto con il nostro codice

| Punto | Noi | Pratica consigliata |
|---|---|---|
| Ciclo principale | `s.step(); hal.sleep_ms(20)` fisso (main.py) | dormire solo il tempo che resta del passo |
| Invio schermo | `cmd()` crea `bytes(c)` a ogni chiamata, `show` manda sempre 504 byte | comandi preallocati, invio solo se il buffer è cambiato |
| Tastiera | `set()` nuovi e list comprehension a ogni scan | bitmask intera, nessuna allocazione |
| Rete | `Richiesta.poll` sull'ESP32 fa la richiesta bloccante (thread nell'ultimo commit) | thread o asyncio, timeout corti, mai DNS o TLS nel ciclo dei frame |
| GC | automatico | `gc.collect()` nei momenti morti e `gc.threshold` |
| CPU/energia | 240 MHz sempre | 80 o 160 MHz nei menu, `lightsleep` quando lo schermo è fermo |
| Codice | .mpy su filesystem | moduli congelati, viper per le funzioni di pixel |

## 3. Raccomandazioni, dalla più utile alla meno utile

### 1. Ciclo a passo costante, senza deriva
Adesso il ciclo dura 20 ms più la durata dello step, quindi la velocità dei giochi cambia con il carico.
```python
import time
PASSO = const(50)  # 20 passi/s
prossimo = time.ticks_ms()
while True:
    s.step()
    prossimo = time.ticks_add(prossimo, PASSO)
    attesa = time.ticks_diff(prossimo, time.ticks_ms())
    if attesa > 0:
        time.sleep_ms(attesa)        # piu' avanti: lightsleep quando la radio e' spenta
    else:
        prossimo = time.ticks_ms()   # in ritardo: si riparte da adesso, senza recuperare
```

### 2. Togliere le allocazioni dal percorso di ogni frame
```python
_GOTO = bytearray(b'\x80\x40')
def show(self, buf):
    if buf == self._ultimo:          # confronto veloce tra bytearray
        return
    self._ultimo[:] = buf
    self.dc(0); self.ce(0); self.spi.write(_GOTO)
    self.dc(1); self.spi.write(buf); self.ce(1)
```
Tastiera con bitmask:
```python
def scan(self):
    m = 0; i = 0
    for rp in self.rows:
        rp(0)
        for cp in self.cols:
            if not cp(): m |= 1 << i
            i += 1
        rp(1)
    cambiati = m ^ self.prima
    self.prima = m
    return m, cambiati   # down = cambiati & m, up = cambiati & ~m
```
Il polling a 20 Hz basta come debounce (50 ms tra due letture). Gli interrupt sulla matrice servono solo per svegliarsi dal sonno.

### 3. Rete: niente blocchi lunghi dentro l'interprete
- Il thread va bene per `recv`, perché lì il GIL si rilascia. `getaddrinfo`, `connect` e soprattutto l'handshake TLS però possono fermare i frame per centinaia di ms. Conviene il bridge di casa in HTTP semplice sulla LAN, l'IP risolto una volta sola e salvato, `settimeout` corti.
- Un'alternativa più pulita è asyncio con `asyncio.open_connection` e i passi del gioco come task. Il sistema diventa uno solo, senza GIL conteso. Costa un refactor del ciclo, quindi va fatto solo se il thread dà problemi.
- Usare un MicroPython recente, che include la correzione dell'equità del GIL (PR #15476).

### 4. Viper nelle funzioni di pixel che girano in Python puro
```python
@micropython.viper
def inverti(buf: ptr8, n: int):
    for i in range(n):
        buf[i] = buf[i] ^ 0xFF
```
Funziona bene per i fallback di `gfx.py`, il dithering e il retino, cioè tutto quello che framebuf non fa già in C. `@micropython.native` sulla logica dei giochi dà circa il doppio. Va misurato sul dispositivo vero con `time.ticks_us()`, perché il banco da 400k giri/s è solo una stima.

### 5. Moduli congelati nel firmware
Si compila un firmware ESP32_GENERIC_S3 variante SPIRAM_OCT con un `manifest.py` (`include("$(PORT_DIR)/boards/manifest.py")` più `package("auri")`, `package("apps")`, `package("hal")`). Si risparmia RAM, si avvia più in fretta e il filesystem si usura meno. Il .mpy attuale resta il piano B per gli aggiornamenti rapidi.

### 6. GC sotto controllo
```python
import gc
gc.collect()
gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())  # raccolte piu' frequenti ma corte
```
Chiamare `gc.collect()` al cambio schermata o a fine partita. I buffer grandi (modello, camera) si allocano subito all'avvio. Con 8 MB di PSRAM un singolo collect può durare decine di ms, e questo è un motivo in più per evitare le allocazioni nei frame.

### 7. Energia
- `machine.freq(80_000_000)` in menu e orologio, `240_000_000` solo nei giochi o con la camera. Va verificato che SPI e PWM reggano il cambio, e conviene reinizializzarli se serve.
- Con il Wi-Fi spento e lo schermo fermo: `machine.lightsleep(ms)` con risveglio da GPIO sui tasti (`esp32.wake_on_ext1` oppure `Pin.irq(..., wake=machine.SLEEP)`). Lo spegnimento con `deepsleep` lo abbiamo già.
- Wi-Fi: `wlan.config(pm=network.WLAN.PM_POWERSAVE)` quando è inattivo, spento del tutto se non serve.

### 8. Audio non bloccante
Il PWM con fine programmata in `events()` va già bene. Per le melodie conviene una coda di note avanzata da `events()`. Usare I2S (`machine.I2S` con `irq`) solo se servono campioni veri, perché sul piezo non vale la pena.

### 9. Watchdog, flash e OTA
- `wdt = machine.WDT(timeout=8000)` e `wdt.feed()` in `step()`, da attivare solo dopo la fase di prova.
- Flash: scrivere impostazioni e classifiche solo quando cambiano, mai a ogni frame. LittleFS (quello predefinito) distribuisce già l'usura.
- OTA: con `esp32.Partition` si scrive la partizione OTA successiva (`get_next_update()`, `writeblocks`, `set_boot`), poi si chiama `Partition.mark_app_valid_cancel_rollback()` dopo un avvio riuscito. Per aggiornare solo il codice Python basta scaricare i `.mpy` dal bridge.

### 10. Modulo C nativo (.mpy natmod), solo se serve
Se dopo i punti 1-4 un gioco è ancora lento (blit di sprite grandi, scroll), si può scrivere un natmod in C con `py/dynruntime.h` e compilarlo per `ARCH=xtensawin`. È più veloce di viper, ma la toolchain è più complicata.

## 4. Cosa non serve
- DMA o invio parziale per lo schermo come misura di velocità: 1 ms per frame su 50 è già trascurabile.
- La differenza tra PSRAM octal e quad: il codice caldo e i buffer piccoli stanno in RAM interna.
