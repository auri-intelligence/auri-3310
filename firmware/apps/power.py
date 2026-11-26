from auri import keys
from auri.ui import App, Menu
from auri.gfx import Canvas, W, H
from auri.i18n import t
from auri.settings import PROFILES
from auri.sound import BOOT, SHUTDOWN


def _logo_pixels():
    # The "AurI" logo at 3x, as a list of blocks: the boot animation assembles it pixel by pixel.
    c = Canvas()
    c.logo(0, 0)
    out = []
    for y in range(8):
        for x in range(18):
            if c.get(x, y):
                out.append((x, y))
    return out


def _order(i):
    # fixed pseudo-random order, the same on every boot
    return (i * 37 + 11) % 97


def draw_logo(g, frac, y0=6):
    px = _logo_pixels()
    n = int(len(px) * frac)
    ranked = sorted(range(len(px)), key=_order)[:n]
    x0 = (W - 18 * 3) // 2
    for i in ranked:
        x, y = px[i]
        g.fill_rect(x0 + x * 3, y0 + y * 3, 3, 3)


# spunta = ok, croce = problema vero (es. batteria scarica), trattino = parte che qui non c'e'
SPUNTA = ('....#', '...#.', '#.#..', '.#...')
CROCE = ('#...#', '.#.#.', '..#..', '.#.#.', '#...#')
TRATTO = ('.....', '.....', '.###.')


class Avvio(App):
    """Accensione vera: controlla una per una le parti del telefono (hardware, memoria, rete, cervello...)
    e le spunta in una lista che scorre, con la barra di avanzamento; poi la schermata principale."""

    STEP_MS = 150

    def __init__(self, sys):
        super().__init__(sys)
        self.t0 = sys.hal.ticks_ms()
        self.anim = sys.settings['boot_anim']
        self.logo_ms = 1300 if self.anim else 0
        self.checks = []
        self.todo = [self._display, self._keys, self._ram, self._memory, self._battery, self._audio,
                     self._vibra, self._sensors, self._network, self._bt, self._gps, self._clock,
                     self._camera, self._brain, self._games]
        self.total = len(self.todo)
        sys.hal.light(1)
        sys.vibrate(120)
        if self.anim:
            sys.play(BOOT, 170)

    # ogni controllo: (nome, valore, ok)
    def _display(self):
        return t('ck_display'), '84x48', True

    def _keys(self):
        return t('ck_keys'), '19', True

    def _ram(self):
        try:
            import gc
            gc.collect()
            kb = gc.mem_free() // 1024
            return 'RAM', ('%dK' % kb) if kb < 10000 else '%dM' % (kb // 1024), True
        except Exception:
            return 'RAM', 'OK', True

    def _memory(self):
        st = self.sys.hal.load('settings', None)
        return t('ck_data'), 'OK' if st is not None else t('new'), True

    def _battery(self):
        pct, chg = self.sys.hal.battery()
        self.sys.battery = (pct, chg)
        return t('ck_batt'), '%d%%%s' % (pct, '+' if chg else ''), pct > 10 or chg

    def _audio(self):
        return t('ck_audio'), 'OK' if self.sys.settings['volume'] else t('off'), True

    def _vibra(self):
        return t('ck_vibra'), 'OK' if self.sys.settings['vibra'] else t('off'), True

    def _sensors(self):
        try:
            n = len(self.sys.hal.sensors())
        except Exception:
            n = 0
        return t('ck_sens'), '%d' % n if n else '--', True if n else None

    def _network(self):
        ok = bool(self.sys.hal.wifi_level()) and not self.sys.settings['aereo']
        return t('network'), 'OK' if ok else '--', True if ok else None

    def _bt(self):
        f = getattr(self.sys.hal, 'net_info', None)
        try:
            ok = bool(f and f().get('bt'))
        except Exception:
            ok = False
        return 'BT', 'OK' if ok else '--', True if ok else None

    def _gps(self):
        ok = hasattr(self.sys.hal, 'loc_start')
        return 'GPS', 'OK' if ok else '--', True if ok else None

    def _clock(self):
        ok = self.sys.hal.localtime()[0] >= 2024
        return t('ck_ora'), 'OK' if ok else '--', ok

    def _camera(self):
        f = getattr(self.sys.hal, 'cam_ok', None)
        try:
            ok = bool(f and f())
        except Exception:
            ok = False
        return 'Camera', 'OK' if ok else '--', True if ok else None

    def _brain(self):
        locale = False
        f = getattr(self.sys.hal, 'ai_ok', None)
        try:
            locale = bool(f and f())
        except Exception:
            pass
        if locale:
            return 'AurI AI', t('ck_local'), True
        if self.sys.config.get('bridge_url'):
            return 'AurI AI', t('ck_home'), True
        return 'AurI AI', '--', None

    def _games(self):
        return t('games'), '8', True

    def on_key(self, k):
        pass

    def on_long(self, k):
        pass

    def tick(self, now):
        el = now - self.t0
        if el >= self.logo_ms:
            due = (el - self.logo_ms) // self.STEP_MS + 1
            while self.todo and len(self.checks) < due:
                fn = self.todo.pop(0)
                try:
                    self.checks.append(fn())
                except Exception:
                    self.checks.append((fn.__name__[1:9], '--', False))
        if not self.todo and el >= self.logo_ms + self.STEP_MS * (self.total + 1) + 900:
            from apps.home import Home
            self.sys.stack = [Home(self.sys)]
        return True

    def draw(self, g):
        el = self.sys.hal.ticks_ms() - self.t0
        if el < self.logo_ms:
            draw_logo(g, min(1, el / (self.logo_ms * 0.8)))
            if el > self.logo_ms * 0.85:
                g.text_center('3310', 36)
            return
        if not self.todo and el >= self.logo_ms + self.STEP_MS * (self.total + 1):
            draw_logo(g, 1, 4)
            g.text_center(self.sys.settings['welcome'] or t('welcome'), 34)
            return
        g.logo_center(0)
        for i, (name, val, ok) in enumerate(self.checks[-4:]):
            y = 10 + i * 8
            g.icon(SPUNTA if ok else TRATTO if ok is None else CROCE, 0, y + 1)
            g.text(name[:7], 7, y)
            g.text(val[:5], W - len(val[:5]) * 6, y)
        # barra di avanzamento: quanti controlli fatti sul totale
        g.rect(0, 43, W, 5)
        g.fill_rect(1, 44, (W - 2) * len(self.checks) // self.total, 3)


class Spegnimento(App):
    MS = 1400

    def __init__(self, sys):
        super().__init__(sys)
        self.t0 = sys.hal.ticks_ms()
        sys.play(SHUTDOWN, 170)
        sys.vibrate(120)

    def on_key(self, k):
        pass

    def on_long(self, k):
        pass

    def tick(self, now):
        if now - self.t0 >= self.MS and not self.sys.sound.busy():
            self.sys.shut()
        return True

    def draw(self, g):
        el = self.sys.hal.ticks_ms() - self.t0
        draw_logo(g, max(0, 1 - el / (self.MS * 0.7)), 4)
        g.text_center(t('goodbye'), 34)


class Spento(App):
    """Phone off: screen dark, only a long Power press does something. Shows the charge level if plugged in."""

    dark = True

    def __init__(self, sys):
        super().__init__(sys)
        self._f = 0

    def on_key(self, k):
        pass

    def on_long(self, k):
        pass

    def tick(self, now):
        f = now // 500
        if self.sys.battery[1] and f != self._f:
            self._f = f
            return True
        return False

    def draw(self, g):
        pct, chg = self.sys.battery
        if not chg:
            return
        x, y = W // 2 - 12, 14
        g.rect(x, y, 22, 12)
        g.fill_rect(x + 22, y + 3, 2, 6)
        full = pct * 18 // 100
        anim = (self._f % 5) * 18 // 4
        g.fill_rect(x + 2, y + 2, max(full, anim) if pct < 100 else 18, 8)
        g.text_center('%d%%' % pct, 32)


def Profili(sys):
    def pick(name):
        def run():
            sys.settings.profile(name)
            sys.pop()
            sys.toast(t('prof_' + name))
        return run

    cur = sys.settings['profile']
    items = [(('>' if n == cur else ' ') + t('prof_' + n), pick(n)) for n, _v, _b, _k in PROFILES]
    items.append((' ' + t('power_off'), sys.power_off))
    m = Menu(sys, t('profiles'), items)
    m.kind = 'profiles'
    m.sel = [n for n, _v, _b, _k in PROFILES].index(cur) if cur in [p[0] for p in PROFILES] else 0
    return m
