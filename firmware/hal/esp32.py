# Hardware layer for MicroPython on ESP32-S3. Untested until the bench prototype (phase H0).
import json
import time
import machine
import network
import random

from hal import board

REQ_TIMEOUT_S = 25

W, H = 84, 48


class PCD8544:
    def __init__(self):
        self.spi = machine.SPI(1, baudrate=4_000_000, sck=machine.Pin(board.LCD_SCLK), mosi=machine.Pin(board.LCD_SDIN))
        self.dc = machine.Pin(board.LCD_DC, machine.Pin.OUT)
        self.ce = machine.Pin(board.LCD_SCE, machine.Pin.OUT, value=1)
        self.rst = machine.Pin(board.LCD_RES, machine.Pin.OUT, value=1)
        self.rst(0)
        time.sleep_ms(10)
        self.rst(1)
        self.cmd(0x21, 0x80 | board.LCD_VOP, 0x04, 0x14, 0x20, 0x0C)

    _HOME = bytes((0x80, 0x40))   # cursore a 0,0: comando di ogni fotogramma, senza allocare

    def cmd(self, *c):
        self.dc(0)
        self.ce(0)
        self.spi.write(bytes(c))
        self.ce(1)

    def show(self, buf):
        self.dc(0)
        self.ce(0)
        self.spi.write(self._HOME)
        self.ce(1)
        self.dc(1)
        self.ce(0)
        self.spi.write(buf)
        self.ce(1)


class Keypad:
    def __init__(self):
        # open-drain: due tasti della stessa colonna non mettono in corto due uscite (prima: tasti fantasma)
        self.rows = [machine.Pin(p, machine.Pin.OPEN_DRAIN, value=1) for p in board.KEY_ROWS]
        self.cols = [machine.Pin(p, machine.Pin.IN, machine.Pin.PULL_UP) for p in board.KEY_COLS]
        self.state = set()

    def scan(self):
        now = set()
        for r, rp in enumerate(self.rows):
            rp(0)
            for c, cp in enumerate(self.cols):
                if not cp():
                    k = board.KEYMAP[r][c]
                    if k:
                        now.add(k)
            rp(1)
        ev = [('down', k) for k in now - self.state] + [('up', k) for k in self.state - now]
        self.state = now
        return ev


class SHT40:
    ADDR = 0x44

    def __init__(self, i2c):
        self.i2c = i2c

    def read(self):
        self.i2c.writeto(self.ADDR, b'\xfd')
        time.sleep_ms(10)
        d = self.i2c.readfrom(self.ADDR, 6)
        t = -45 + 175 * ((d[0] << 8) | d[1]) / 65535
        h = -6 + 125 * ((d[3] << 8) | d[4]) / 65535
        return round(t, 1), round(max(0, min(100, h)))


class ESP32Hal:
    def __init__(self):
        self.lcd = PCD8544()
        self.keys = Keypad()
        self.pwr = machine.Pin(board.POWER_KEY, machine.Pin.IN, machine.Pin.PULL_UP)
        self.pwr_down = False
        self.adc = machine.ADC(machine.Pin(board.BAT_ADC))
        self.adc.atten(machine.ADC.ATTN_11DB)
        self.chg = machine.Pin(board.CHG_DET, machine.Pin.IN, machine.Pin.PULL_UP)
        self.spk = machine.PWM(machine.Pin(board.SPEAKER), freq=1000, duty_u16=0)
        self.tone_until = 0
        self.bl = machine.PWM(machine.Pin(board.BACKLIGHT), freq=1000, duty_u16=0)
        self.vib = machine.Pin(board.VIBRA, machine.Pin.OUT, value=0)
        self.vib_until = 0
        self._req = {}             # richieste di rete in corso in un thread: id -> risultato
        self._req_n = 0
        self.lit_until = 0
        self.wlan = network.WLAN(network.STA_IF)
        self.i2c = machine.I2C(0, scl=machine.Pin(board.I2C_SCL), sda=machine.Pin(board.I2C_SDA), freq=400000)
        found = self.i2c.scan()
        self.sht = SHT40(self.i2c) if SHT40.ADDR in found else None
        self.sd = False
        self._llm = None          # modulo auri_llm, quando c'e'
        self._llm_state = 'off'   # off | load | ready | gen
        self._llm_file = None
        self._llm_got = 0
        self._llm_size = 0
        self._llm_name = ''
        self._llm_text = ''

    def ticks_ms(self):
        # time.ticks_ms() ricomincia da zero ogni ~12,4 giorni: qui un contatore che cresce sempre,
        # cosi' tutto AurI OS puo' sottrarre i tempi senza time.ticks_diff
        t = time.ticks_ms()
        self._mono = getattr(self, '_mono', 0) + time.ticks_diff(t, getattr(self, '_mono_t', t))
        self._mono_t = t
        return self._mono

    def localtime(self):
        return time.localtime(time.time() + board.TZ_OFFSET)

    def events(self):
        if self.lit_until and time.ticks_diff(time.ticks_ms(), self.lit_until) > 0:
            self.bl.duty_u16(0)
            self.lit_until = 0
        if self.tone_until and time.ticks_diff(time.ticks_ms(), self.tone_until) > 0:
            self.spk.duty_u16(0)
            self.tone_until = 0
        if self.vib_until and time.ticks_diff(time.ticks_ms(), self.vib_until) > 0:
            self.vib(0)
            self.vib_until = 0
        ev = self.keys.scan()
        down = not self.pwr()
        if down != self.pwr_down:
            self.pwr_down = down
            ev.append(('down' if down else 'up', 'power'))
        return ev

    def show(self, buf):
        self.lcd.show(buf)

    def light(self, on, ms=15000):
        # ms < 0: always on
        self.bl.duty_u16(40000 if on else 0)
        self.lit_until = time.ticks_add(time.ticks_ms(), ms) if on and ms >= 0 else 0

    def vibrate(self, ms):
        # non bloccante come il bip: events() spegne il motorino quando e' ora (prima sleep_ms fermava
        # tutto il telefono fino a 300 ms, a fine partita il gioco si congelava)
        self.vib(1)
        self.vib_until = time.ticks_add(time.ticks_ms(), ms)

    def beep(self, freq, ms, vol=3):
        # non-blocking: events() switches the tone off when its time is up
        if not vol:
            return
        self.spk.freq(freq)
        self.spk.duty_u16(vol * 6000)
        self.tone_until = time.ticks_add(time.ticks_ms(), ms)

    def wifi_level(self):
        if not self.wlan.isconnected():
            return 0
        rssi = self.wlan.status('rssi')
        return 4 if rssi > -55 else 3 if rssi > -65 else 2 if rssi > -75 else 1

    def net_info(self):
        ok = self.wlan.active() and self.wlan.isconnected()
        try:
            ssid = self.wlan.config('ssid') if ok else ''
        except Exception:
            ssid = ''
        try:
            import bluetooth   # noqa: F401
            bt = 1
        except ImportError:
            bt = 0
        return {'online': ok, 'tipo': 'wifi' if ok else '', 'eff': '', 'bars': self.wifi_level(),
                'down': 0, 'bt': bt, 'ssid': ssid}

    def wifi_set(self, on):
        self.wlan.active(bool(on))

    def bt_set(self, on):
        try:
            import bluetooth
            bluetooth.BLE().active(bool(on))
        except Exception:
            pass

    # niente loc_*: il Nokia vero non ha un GPS (l'app lo dice)

    def battery(self):
        if not getattr(board, 'BATTERIA', True):
            return 100, False            # a rete: mai 0% (spegnerebbe tutto), mai carica fantasma
        mv = sum(self.adc.read_uv() for _ in range(8)) // 8000 * board.BAT_DIVIDER
        # niente batteria (banco a USB o col caricatore): sotto 2,5 V una cella al litio non esiste,
        # la sua protezione la stacca prima. Si dice "piena, a rete" invece di 0% (che spegnerebbe tutto)
        if mv < 2500:
            return 100, False
        pct = (mv - board.BAT_EMPTY_MV) * 100 // (board.BAT_FULL_MV - board.BAT_EMPTY_MV)
        return int(max(0, min(100, pct))), not self.chg()

    def battery_level(self):
        return min(4, (self.battery()[0] + 12) // 25)

    def track(self, name):
        # anonymous usage counters exist only in the public web simulator
        pass

    def power_off(self):
        # LCD in power-down, everything off, then deep sleep until Power is pressed again.
        import esp32
        self.lcd.cmd(0x24)
        self.bl.duty_u16(0)
        self.spk.duty_u16(0)
        self.wlan.active(False)
        while not self.pwr():
            time.sleep_ms(10)
        esp32.wake_on_ext0(self.pwr, esp32.WAKEUP_ALL_LOW)
        machine.deepsleep()

    def sensors(self):
        out = {}
        if self.sht:
            out['temperature'], out['humidity'] = self.sht.read()
        return out

    def voice_start(self):
        return False

    def voice_stop(self, url, params, token):
        pass

    def voice_poll(self):
        return {'error': 'Microfono non ancora collegato'}

    # --- microSD -------------------------------------------------------
    def sd_mount(self):
        """Monta la microSD su /sd. Ci stanno i pesi del cervello e, volendo, tutto AurI OS."""
        if self.sd:
            return True
        # senza scheda non si riprova a ogni chiamata: l'inizializzazione della SD costa tempo
        if getattr(self, '_sd_fallita', None) is not None and time.ticks_diff(time.ticks_ms(), self._sd_fallita) < 30000:
            return False
        try:
            import os
            sd = machine.SDCard(slot=3, sck=machine.Pin(board.SD_SCK), mosi=machine.Pin(board.SD_MOSI),
                                miso=machine.Pin(board.SD_MISO), cs=machine.Pin(board.SD_CS))
            os.mount(sd, '/sd')
            self.sd = True
        except Exception as e:
            print('microSD:', e)
            self._sd_fallita = time.ticks_ms()
        return self.sd

    def _llm_files(self):
        """(modello, tokenizer) sulla microSD, oppure None. Ricordato: prima si leggeva la SD 3-4 volte a fotogramma."""
        c = getattr(self, '_llm_f', 0)
        if c != 0:
            return c
        self._llm_f = f = self._llm_files_sd()
        return f

    def _llm_files_sd(self):
        if not self.sd_mount():
            return None
        import os
        try:
            nomi = os.listdir(board.SD_DIR)
        except OSError:
            return None
        modello = next((n for n in nomi if n.endswith('.bin') and 'tok' not in n), None)
        tok = next((n for n in nomi if n.endswith('.bin') and 'tok' in n), None)
        if not modello or not tok:
            return None
        return (board.SD_DIR + '/' + modello, board.SD_DIR + '/' + tok)

    # --- cervello locale (modulo C auri_llm + pesi dalla microSD) --------
    # --- fotocamera del Nokia (OV2640 sulla porta DVP, modulo micropython-camera-API) ---
    # Il sensore da' gia' la scala di grigi a 160x120: qui si riduce a 84x48 e si fa il dithering.
    def cam_ok(self):
        if getattr(self, '_cam_ok', None) is None:
            try:
                import camera   # noqa: F401
                self._cam_ok = hasattr(board, 'CAM_PINS')
            except ImportError:
                self._cam_ok = False
        return self._cam_ok

    def cam_start(self):
        self._cam_err, self._cam_modo, self._cam_buf = '', 0, bytearray(504)
        try:
            from camera import Camera, PixelFormat, FrameSize
            p = board.CAM_PINS
            self._cam = Camera(data_pins=p['data'], vsync_pin=p['vsync'], href_pin=p['href'],
                               sda_pin=p['sda'], scl_pin=p['scl'], pclk_pin=p['pclk'], xclk_pin=p['xclk'],
                               xclk_freq=20_000_000, pixel_format=PixelFormat.GRAYSCALE,
                               frame_size=FrameSize.QQVGA, fb_count=2)
        except Exception:
            self._cam, self._cam_err = None, 'no_cam'

    def cam_stop(self):
        if getattr(self, '_cam', None):
            try:
                self._cam.deinit()
            except Exception:
                pass
        self._cam = None

    def cam_switch(self):
        pass        # una sola fotocamera

    def cam_mode(self, m):
        self._cam_modo = m

    def cam_poll(self):
        cam = getattr(self, '_cam', None)
        if not cam:
            return {'on': False, 'busy': False, 'err': getattr(self, '_cam_err', 'no_cam'), 'facing': 'environment', 'frame': None}
        from auri.dither import da_grigi
        img = cam.capture()
        f = da_grigi(img, 160, 120, self._cam_modo, False, self._cam_buf) if img else None
        return {'on': True, 'busy': False, 'err': '', 'facing': 'environment', 'frame': f}

    def ai_ok(self):
        if self._llm is None:
            try:
                import auri_llm
                self._llm = auri_llm
            except ImportError:
                self._llm = False     # firmware senza il modulo: si usa il bridge
        return bool(self._llm) and self._llm_files() is not None

    def ai_models(self):
        f = self._llm_files()
        if not f:
            return []
        import os
        kb = os.stat(f[0])[6] // 1024
        nome = f[0].split('/')[-1].replace('.bin', '')
        return [[nome, nome[:12], max(1, kb // 1024)]]

    def ai_start(self, model=''):
        """Carica i pesi dalla microSD alla PSRAM, un pezzo per giro: il telefono resta vivo."""
        f = self._llm_files()
        if not f or not self._llm:
            return
        import os
        import gc
        try:
            self._llm_name = f[0].split('/')[-1].replace('.bin', '')[:12]
            self._llm_size = os.stat(f[0])[6]
            gc.collect()
            if self._llm_size > gc.mem_free() - 512 * 1024:      # non ci sta: errore chiaro, mai un blocco
                raise MemoryError('modello troppo grande')
            self._llm.tokenizer(open(f[1], 'rb').read())
            self._llm.begin(self._llm_size)
            self._llm_file = open(f[0], 'rb')
            self._llm_got = 0
            self._llm_state = 'load'
        except Exception as e:
            print('cervello:', e)
            self._llm_f = 0                   # la SD si rilegge al prossimo tentativo
            self._llm_state = 'err'
            self._llm_text = str(e)

    def _llm_feed(self):
        buf = getattr(self, '_llm_buf', None)
        if buf is None:
            buf = self._llm_buf = bytearray(16384)     # uno solo, riusato: niente GC a ogni pezzo
        n = self._llm_file.readinto(buf)
        if not n:
            self._llm_file.close()
            self._llm_file = None
            try:
                self._llm.end()
                self._llm_state = 'ready'
            except Exception as e:
                print('cervello:', e)
                self._llm_state = 'off'
            return
        self._llm.feed(buf if n == len(buf) else memoryview(buf)[:n])
        self._llm_got += n

    def ai_info(self):
        if self._llm_state == 'load' and self._llm_file:
            self._llm_feed()
        pct = 100 * self._llm_got // self._llm_size if self._llm_size else 0
        return {'phase': self._llm_state, 'pct': pct, 'name': self._llm_name or 'microSD',
                'mb': max(1, self._llm_size // 1048576),
                'error': self._llm_text if self._llm_state == 'err' else ''}

    def ai_ask(self, messages, opts=None):
        if self._llm_state not in ('ready', 'gen'):
            return 'cervello non pronto'
        testo = ''
        for m in messages:
            if m.get('role') == 'user':
                testo = m.get('content', '')
        try:
            self._llm.start(testo, 0.9, 0.9, int((opts or {}).get('max_tokens', 120)), time.ticks_ms())
        except Exception as e:
            return str(e)
        self._llm_text = ''
        self._llm_state = 'gen'
        return ''

    def ai_poll(self):
        """Un pezzo di testo per giro (ognuno ~100 ms sull'ESP32): con due il passo superava i 200 ms e
        le pressioni lunghe (spegnimento, C) non scattavano piu' durante la risposta."""
        if self._llm_state == 'gen':
            for _ in range(1):
                p = self._llm.next()
                if p is None:
                    self._llm_state = 'ready'
                    break
                self._llm_text += p
        return {'text': self._llm_text, 'done': 0 if self._llm_state == 'gen' else 1, 'error': ''}

    def ai_stop(self):
        if self._llm:
            self._llm.stop()
        if self._llm_state == 'gen':
            self._llm_state = 'ready'

    def random(self, n):
        return random.getrandbits(16) % n

    def sleep_ms(self, ms):
        time.sleep_ms(ms)

    def running(self):
        return True

    def request(self, method, url, body=None, token=None):
        import requests
        h = {'Content-Type': 'application/json'}
        if token:
            h['Authorization'] = 'Bearer ' + token
        # timeout: se il bridge tarda (modello che si carica) il telefono non resta bloccato per minuti;
        # l'eccezione arriva all'app, che mostra "bridge non raggiungibile"
        try:
            r = requests.request(method, url, data=json.dumps(body) if body is not None else None,
                                 headers=h, timeout=REQ_TIMEOUT_S)
        except TypeError:       # requests vecchio, senza timeout
            r = requests.request(method, url, data=json.dumps(body) if body is not None else None, headers=h)
        try:
            return r.json()
        finally:
            r.close()

    # Richieste che non bloccano (classifica, ecc.): partono in un thread, il ciclo principale continua a
    # disegnare e a leggere i tasti. auri/net.py le usa da sole quando la HAL le ha.
    def request_start(self, method, url, body=None, token=None):
        import _thread
        if sum(1 for v in self._req.values() if v is None) >= 2:
            raise OSError('rete occupata')      # ogni thread con TLS costa ~40 KB: non piu' di 2 insieme
        if len(self._req) > 8:                  # risultati mai ritirati (app chiusa prima): si buttano
            for k in [k for k, v in self._req.items() if v is not None]:
                del self._req[k]
        self._req_n += 1
        rid = self._req_n
        self._req[rid] = None

        def lavora():
            try:
                self._req[rid] = (self.request(method, url, body, token), '')
            except Exception as e:
                self._req[rid] = (None, str(e) or 'rete')
        try:
            _thread.stack_size(16 * 1024)       # TLS (mbedtls) + json non stanno nei ~5 KB di default
        except Exception:
            pass
        try:
            _thread.start_new_thread(lavora, ())
        except Exception:
            lavora()              # niente thread: almeno funziona (bloccando)
        return rid

    def request_poll(self, rid):
        r = self._req.get(rid)
        if r is not None:
            del self._req[rid]
        return r

    def load(self, name, default):
        try:
            with open('/data/' + name + '.json') as f:
                return json.load(f)
        except (OSError, ValueError):
            return default

    def save(self, name, obj):
        try:
            import os
            os.mkdir('/data')
        except OSError:
            pass
        with open('/data/' + name + '.json', 'w') as f:
            json.dump(obj, f)
