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


class Avvio(App):
    """Real start-up: checks memory, battery, sensors, network and clock, then shows the home screen."""

    STEP_MS = 260

    def __init__(self, sys):
        super().__init__(sys)
        self.t0 = sys.hal.ticks_ms()
        self.anim = sys.settings['boot_anim']
        self.logo_ms = 1300 if self.anim else 0
        self.checks = []
        self.todo = [self._memory, self._battery, self._sensors, self._network, self._clock]
        sys.hal.light(1)
        sys.vibrate(120)
        if self.anim:
            sys.play(BOOT, 170)

    def _memory(self):
        st = self.sys.hal.load('settings', None)
        return t('memory'), 'OK' if st is not None else t('new')

    def _battery(self):
        pct, chg = self.sys.hal.battery()
        self.sys.battery = (pct, chg)
        return t('battery'), '%d%%%s' % (pct, '+' if chg else '')

    def _sensors(self):
        try:
            n = len(self.sys.hal.sensors())
        except Exception:
            n = 0
        return t('sensors'), '%d' % n if n else '--'

    def _network(self):
        return t('network'), 'OK' if self.sys.hal.wifi_level() else '--'

    def _clock(self):
        return t('clock'), 'OK' if self.sys.hal.localtime()[0] >= 2024 else '--'

    def on_key(self, k):
        pass

    def on_long(self, k):
        pass

    def tick(self, now):
        el = now - self.t0
        if el >= self.logo_ms:
            due = (el - self.logo_ms) // self.STEP_MS + 1
            while self.todo and len(self.checks) < due:
                self.checks.append(self.todo.pop(0)())
        if not self.todo and el >= self.logo_ms + self.STEP_MS * 6 + 900:
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
        if not self.todo and el >= self.logo_ms + self.STEP_MS * 6:
            draw_logo(g, 1, 4)
            g.text_center(self.sys.settings['welcome'] or t('welcome'), 34)
            return
        g.logo_center(0)
        for i, (name, val) in enumerate(self.checks[-4:]):
            y = 10 + i * 9
            g.text(name[:9], 0, y)
            g.text(val, W - len(val) * 6, y)


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
