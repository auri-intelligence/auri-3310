"""AurI OS sull'ESP32 finto: il codice del Nokia vero (hal/esp32.py) gira su CPython con machine, network,
time (ticks_*), esp32, requests e _thread simulati. La tastiera e' simulata a livello elettrico (matrice
righe/colonne di hal/board.py), il display a livello SPI (comandi e dati del PCD8544 decodificati).

  py tools/test_esp32_finto.py        (immagini del display in tmp/lcd/esp32/)

Trova i crash del codice che il simulatore web non esegue mai (hal/esp32.py) prima di avere l'hardware.
"""
import json
import os
import random
import shutil
import sys
import time as _t
import types
import warnings  # noqa: F401  (prima dei moduli finti)
import threading
try:
    from PIL import Image, PngImagePlugin  # noqa: F401
except ImportError:
    Image = None
if Image:
    Image.init()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, 'firmware')
OUT = os.path.join(ROOT, 'tmp', 'lcd', 'esp32')
DATA = os.path.join(ROOT, 'tmp', 'esp32_data')
os.makedirs(OUT, exist_ok=True)
shutil.rmtree(DATA, ignore_errors=True)
os.makedirs(DATA, exist_ok=True)
sys.path.insert(0, FW)

# --- orologio virtuale e modulo time di MicroPython ---
CLK = [0]
tm = types.ModuleType('time')
tm.ticks_ms = lambda: CLK[0]
tm.ticks_us = lambda: CLK[0] * 1000
tm.ticks_add = lambda a, b: a + b
tm.ticks_diff = lambda a, b: a - b
tm.sleep_ms = lambda ms: CLK.__setitem__(0, CLK[0] + int(ms))
tm.sleep = lambda s: CLK.__setitem__(0, CLK[0] + int(s * 1000))
tm.time = lambda: 1795600000 + CLK[0] // 1000
tm.localtime = lambda s=None: _t.localtime(s if s is not None else tm.time())[:8]
tm.mktime = _t.mktime
sys.modules['utime'] = tm

# --- machine: pin, SPI, PWM, ADC, I2C ---
PINS = {}
PREMUTI = set()          # (riga, colonna) premuti
POWER = [False]
POWER_FINO = [10 ** 12]     # il dito si stacca da solo a quest'ora (serve allo spegnimento)
SPI_LOG = []
STATO = {'dc': 0, 'vib': 0, 'pwm': {}}
import hal.board as board  # noqa: E402


class Pin:
    OUT, IN, PULL_UP, OPEN_DRAIN = 1, 2, 3, 7

    def __init__(self, n, mode=None, pull=None, value=None):
        self.n = n
        self.v = value if value is not None else 1
        PINS[n] = self

    def __call__(self, v=None):
        if v is None:
            return self.value()
        self.v = v
        if self.n == board.LCD_DC:
            STATO['dc'] = v
        if self.n == board.VIBRA:
            STATO['vib'] = v

    def value(self, v=None):
        if v is not None:
            return self(v)
        if self.n in board.KEY_COLS:
            c = board.KEY_COLS.index(self.n)
            for r, rp in enumerate(board.KEY_ROWS):
                if PINS[rp].v == 0 and (r, c) in PREMUTI:
                    return 0
            return 1
        if self.n == board.POWER_KEY:
            return 0 if POWER[0] and CLK[0] < POWER_FINO[0] else 1
        if self.n == board.CHG_DET:
            return 1
        return self.v


class SPI:
    def __init__(self, *a, **k):
        pass

    def write(self, b):
        SPI_LOG.append((STATO['dc'], bytes(b)))


class PWM:
    def __init__(self, pin, freq=1000, duty_u16=0):
        self.pin = pin

    def freq(self, f=None):
        pass

    def duty_u16(self, d=None):
        STATO['pwm'][self.pin.n] = d


class ADC:
    ATTN_11DB = 3

    def __init__(self, pin):
        pass

    def atten(self, a):
        pass

    def read_uv(self):
        return 1950000        # 3,9 V con il partitore 1:2


class I2C:
    def __init__(self, *a, **k):
        pass

    def scan(self):
        return []


machine = types.ModuleType('machine')
machine.Pin, machine.SPI, machine.PWM, machine.ADC, machine.I2C = Pin, SPI, PWM, ADC, I2C
machine.deepsleep = lambda *a: (_ for _ in ()).throw(SystemExit('deepsleep'))
machine.SDCard = lambda **k: (_ for _ in ()).throw(OSError('niente microSD'))
sys.modules['machine'] = machine


class WLAN:
    def __init__(self, *a):
        self._on = True

    def active(self, v=None):
        if v is None:
            return self._on
        self._on = v

    def isconnected(self):
        return False

    def status(self, k=None):
        return -70

    def config(self, k):
        return ''

    def connect(self, *a):
        pass


network = types.ModuleType('network')
network.WLAN, network.STA_IF = WLAN, 0
sys.modules['network'] = network
esp32m = types.ModuleType('esp32')
esp32m.wake_on_ext0 = lambda *a: None
esp32m.WAKEUP_ALL_LOW = 0
sys.modules['esp32'] = esp32m
req = types.ModuleType('requests')


def _request(method, url, data=None, headers=None, timeout=None):
    raise OSError('rete assente (prova)')


req.request = _request
sys.modules['requests'] = req
th = types.ModuleType('_thread')
th.start_new_thread = lambda f, a: f(*a)      # niente thread veri: si esegue subito (come prova logica)
sys.modules['_thread'] = th

# file in /data -> tmp/esp32_data
_open = open


def _open_data(p, *a, **k):
    if isinstance(p, str) and p.startswith('/data'):
        p = DATA + p[5:]
    return _open(p, *a, **k)


import builtins  # noqa: E402
builtins.open = _open_data
_mkdir = os.mkdir
os.mkdir = lambda p, *a: _mkdir(DATA + p[5:] if p.startswith('/data') else p, *a)

# il modulo time di MicroPython deve essere quello finto anche per hal/esp32.py e auri/*
sys.modules['time'] = tm
from hal.esp32 import ESP32Hal  # noqa: E402
from auri.core import System  # noqa: E402
from auri import keys  # noqa: E402


def lcd_attuale():
    """Ricostruisce la RAM del PCD8544 dagli ultimi 504 byte di dati scritti via SPI."""
    for dc, b in reversed(SPI_LOG):
        if dc == 1 and len(b) == 504:
            return b
    return bytes(504)


def png(nome):
    if Image is None:
        return
    b = lcd_attuale()
    im = Image.new('RGB', (84, 48), (157, 200, 106))
    for i, v in enumerate(b):
        x, bank = i % 84, i // 84
        for k in range(8):
            if v >> k & 1:
                im.putpixel((x, bank * 8 + k), (28, 43, 20))
    im.resize((84 * 5, 48 * 5), Image.NEAREST).save(os.path.join(OUT, nome + '.png'))


DOVE = {k: (r, c) for r, row in enumerate(board.KEYMAP) for c, k in enumerate(row) if k}


def gira(s, ms):
    fine = CLK[0] + ms
    while CLK[0] < fine:
        s.step()
        tm.sleep_ms(20)


def premi(s, k, ms=80):
    if k == 'power':
        POWER[0] = True
        gira(s, ms)
        POWER[0] = False
    else:
        PREMUTI.add(DOVE[k])
        gira(s, ms)
        PREMUTI.discard(DOVE[k])
    gira(s, 120)


def app(s):
    return type(s.top).__name__


LENTO = {'attivo': False}


def bridge_lento(s, hal):
    """Bridge che risponde dopo 2 s (thread veri): il telefono deve continuare a disegnare e leggere i tasti."""
    def risposta(method, url, data=None, headers=None, timeout=None):
        _t.sleep(2.0)
        class R:
            def json(self):
                if url.endswith('/v1/home'):
                    return {'entities': [{'id': 'light.sala', 'name': 'Luce sala', 'state': 'off'}]}
                if url.endswith('/v1/info'):
                    return {'version': '9.9', 'plan': 'Max', 'cwd': '~'}
                return {'reply': 'Risposta dal bridge lento', 'session': 'x'}

            def close(self):
                pass
        return R()
    req.request = risposta
    th.start_new_thread = lambda f, a: threading.Thread(target=f, args=a, daemon=True).start()

    def segui(nome, fine, max_s=6):
        frame0 = sum(1 for dc, b in SPI_LOG if dc == 1)
        t0 = _t.time()
        passi = 0
        while _t.time() - t0 < max_s:
            a = _t.time()
            s.step()
            tm.sleep_ms(20)
            passi += 1
            assert _t.time() - a < 0.5, "%s: un passo e' durato %.1f s (bloccato dalla rete?)" % (nome, _t.time() - a)
            if fine():
                break
            _t.sleep(0.01)
        frame = sum(1 for dc, b in SPI_LOG if dc == 1) - frame0
        assert fine(), "%s: non e' finito in %d s (app %s)" % (nome, max_s, app(s))
        print("ok  %-9s col bridge lento: %d passi e %d fotogrammi durante l'attesa, nessun blocco" % (nome, passi, frame))

    # AurI (motore bridge)
    s.home(); gira(s, 200)
    s.settings.set(brain='bridge')
    s.assistant(); gira(s, 300)
    a = s.top
    a._send('che ore sono')
    segui('AurI', lambda: a.brain.done and 'lento' in (a.brain.text or ''))
    png('04_auri_bridge_lento')
    # Casa
    s.home(); gira(s, 200)
    from apps.casa import Casa
    s.push(Casa(s))
    segui('Casa', lambda: app(s) == 'Menu')
    png('05_casa_bridge_lento')
    # Claude: info all'apertura e una domanda
    s.home(); gira(s, 200)
    from apps.claude import Claude
    c = Claude(s)
    s.push(c)
    segui('Claude', lambda: c.info.get('plan') == 'Max')
    c.state = 'chat'
    c._ask('/v1/chat', {'text': 'ciao'})
    segui('Claude 2', lambda: c.state == 'chat' and any('lento' in x for _w, x in c.log))
    th.start_new_thread = lambda f, a: f(*a)
    req.request = _request


def main():
    cfg = {'bridge_url': 'http://192.168.1.2:8787', 'token': '', 'scores_url': 'https://script.example/exec'}
    hal = ESP32Hal()
    s = System(hal, cfg)
    s.power_on()
    gira(s, 6000)
    assert app(s) == 'Home', app(s)
    png('01_home')
    print('ok  accensione fino alla Home con la HAL vera')

    # tutte le voci del menu principale, con tasti a raffica
    rnd = random.Random(7)
    from apps.home import main_menu
    voci = len(main_menu(s).items)
    for i in range(voci):
        s.home()
        gira(s, 300)
        premi(s, 'navi')
        for _ in range(i):
            premi(s, 'down')
        premi(s, 'navi')
        gira(s, 500)
        nome = app(s)
        png('02_menu_%d_%s' % (i, nome))
        for _ in range(40):
            premi(s, rnd.choice(['navi', 'up', 'down', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '*', '#']), rnd.randint(30, 200))
        print('ok  menu %d %-12s + 40 tasti a raffica (finito in %s)' % (i, nome, app(s)))
        hal.keys.state = set()
        PREMUTI.clear()
        premi(s, 'c', 1200)

    # ogni gioco fino al game over, poi la classifica (rete assente: non deve bloccare ne' rompersi)
    hal.save('g_nome', {'nome': 'BANCO'})
    giochi = (('volo', 'Volo'), ('corsie', 'Corsie'), ('incastro', 'Incastro'), ('rompimuro', 'Rompimuro'),
              ('trefila', 'TreFila'), ('salisali', 'SaliSali'), ('catapulta', 'Catapulta'))
    for mod, cls in giochi:
        s.home()
        gira(s, 200)
        m = __import__('apps.giochi.' + mod, None, None, (cls,))
        s.push(getattr(m, cls)(s))
        premi(s, '5')
        for _ in range(250):
            premi(s, rnd.choice(['2', '4', '5', '6', '8', 'navi']), rnd.randint(30, 150))
            if app(s) == 'Classifica':
                break
        gira(s, 2000)
        png('03_gioco_%s' % mod)
        assert STATO['vib'] == 0, 'il motorino deve spegnersi da solo'
        print('ok  gioco %-10s finito in %s (vibrazione spenta, niente blocchi)' % (mod, app(s)))

    bridge_lento(s, hal)

    # spegnimento: deve arrivare al deep sleep senza errori
    s.home()
    gira(s, 300)
    POWER[0] = True
    POWER_FINO[0] = CLK[0] + 2500
    try:
        gira(s, 3000)
        POWER[0] = False
        gira(s, 3000)
    except SystemExit as e:
        print('ok  spegnimento fino al %s' % e)
    print('\ntutti i test passati. Immagini in', OUT)


if __name__ == '__main__':
    main()
