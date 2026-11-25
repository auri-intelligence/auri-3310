from auri import keys
from auri.gfx import Canvas, W, wrap
from auri.settings import Settings
from auri.sound import Player, NOTIFY, WARN, KEY_TONE

VERSION = '0.2.0'


class System:
    def __init__(self, hal, config):
        self.hal = hal
        self.config = config
        self.settings = Settings(hal)
        from auri import i18n
        i18n.set_lang(self.settings['lang'] or config.get('lang', 'it'))
        self.g = Canvas()
        self.sound = Player(hal)
        self.stack = []
        self.dirty = True
        self._held = {}
        self._toast = None
        self._toast_until = 0
        self._toast_t0 = 0
        self._last = None      # (top app, stack depth) of the last drawn frame
        self._prev = bytearray(W * 48 // 8)
        self._trans = None     # (start ms, direction): +1 push, -1 pop
        self.battery = (100, False)
        self._batt_t = -10000
        self._batt_seen = False
        self._low_warned = False
        self._full_told = False

    # --- stack ---
    def track(self, name):
        t = getattr(self.hal, 'track', None)
        if t:
            t(name)

    def push(self, app):
        n = type(app).__name__
        self.track('app/' + (getattr(app, 'kind', '') or (app.title if n == 'Menu' else n)).replace(' ', '_'))
        self.stack.append(app)
        self.dirty = True

    def pop(self):
        if len(self.stack) > 1:
            self._chiudi(self.stack.pop())
        self.dirty = True

    def home(self):
        while len(self.stack) > 1:
            self._chiudi(self.stack.pop())
        self.dirty = True

    @staticmethod
    def _chiudi(app):
        # le app che tengono acceso qualcosa (es. la fotocamera) lo spengono qui
        f = getattr(app, 'close', None)
        if f:
            try:
                f()
            except Exception:
                pass

    @property
    def top(self):
        return self.stack[-1]

    @property
    def off(self):
        return bool(self.stack) and getattr(self.top, 'dark', False)

    def bridge_missing(self, title):
        # True (and an explanation on screen) when this build has no bridge, e.g. the public web simulator
        if self.config.get('bridge_url'):
            return False
        self.track('non_disponibile/' + title.replace(' ', '_'))
        from auri.ui import TextView
        from auri.i18n import t
        self.push(TextView(self, title, t('need_bridge_web') if self.config.get('online') else t('need_bridge')))
        return True

    def assistant(self, trigger=None):
        # Il cervello puo' essere nel dispositivo (browser o microSD) o sul bridge di casa:
        # l'assistente si apre sempre e dentro spiega cosa manca.
        from apps.assistente import Assistente
        self.push(Assistente(self, trigger))

    # --- power ---
    def power_on(self):
        self.track('accensione')
        from apps.power import Avvio
        self.stack = [Avvio(self)]
        self.dirty = True

    def power_off(self):
        self.track('spegnimento')
        from apps.power import Spegnimento
        self.stack = [Spegnimento(self)]
        self.dirty = True

    def shut(self):
        # Called at the end of the shutdown animation: on the ESP32 this does not return (deep sleep).
        from apps.power import Spento
        self.stack = [Spento(self)]
        self.sound.stop()
        self.hal.light(0)
        self.dirty = True
        self.hal.power_off()

    # --- feedback that follows the settings ---
    def light(self):
        s = self.settings['light_s']
        self.hal.light(1, s * 1000 if s else -1)

    def vibrate(self, ms):
        if self.settings['vibra']:
            self.hal.vibrate(ms)

    def play(self, song, bpm=140):
        self.sound.play(song, self.settings['volume'], bpm)

    def toast(self, text, ms=1800):
        self._toast = text
        self._toast_until = self.hal.ticks_ms() + ms
        self._toast_t0 = self.hal.ticks_ms()
        self.dirty = True

    def _check_battery(self, now):
        if now - self._batt_t < 1000:
            return
        self._batt_t = now
        pct, chg = self.hal.battery()
        old = self.battery
        self.battery = (pct, chg)
        if old != self.battery:
            self.dirty = True
        if not self._batt_seen:
            self._batt_seen = True
            return
        from auri.i18n import t
        if chg != old[1] and not self.off:
            self.toast(t('charger_on') if chg else t('charger_off'))
            self.play(NOTIFY, 180)
            self.vibrate(80)
        if chg and pct >= 100 and not self._full_told and not self.off:
            self._full_told = True
            self.toast(t('battery_full'))
        if not chg:
            self._full_told = False
        if not chg and pct <= 10 and not self._low_warned and not self.off:
            self._low_warned = True
            self.toast(t('battery_low'))
            self.play(WARN, 160)
        if pct > 15 or chg:
            self._low_warned = False
        if not chg and pct <= 0 and not self.off and type(self.top).__name__ != 'Spegnimento':
            self.power_off()

    # --- main loop ---
    def step(self):
        now = self.hal.ticks_ms()
        for kind, k in self.hal.events():
            if kind == 'down':
                self._held[k] = now
                if not self.off:
                    self.light()
                    if self.settings['keytones'] and self.settings['volume'] and k != keys.POWER:
                        self.hal.beep(KEY_TONE[0], KEY_TONE[1], self.settings["volume"])
                    self.top.on_key(k)
                self.dirty = True
            elif kind == 'up':
                t0 = self._held.pop(k, None)
                if k == keys.POWER:
                    # short press: profiles, as on the original 3310
                    if t0 is not None and not self.off and getattr(self.top, 'kind', '') != 'profiles' and type(self.top).__name__ not in ('Avvio', 'Spegnimento', 'Assistente'):
                        from apps.power import Profili
                        self.push(Profili(self))
                elif hasattr(self.top, 'on_up') and not self.off:
                    self.top.on_up(k)
                self.dirty = True
        for k, t in list(self._held.items()):
            if t is None:
                continue
            if k == keys.POWER:
                if now - t >= keys.POWER_MS:
                    self._held[k] = None
                    name = type(self.top).__name__
                    if self.off:
                        self.power_on()
                    elif name not in ('Avvio', 'Spegnimento'):
                        self.power_off()
            elif now - t >= keys.LONG_MS:
                self._held[k] = None
                if not self.off:
                    self.top.on_long(k)
                self.dirty = True
        self._check_battery(now)
        self.sound.tick(now)
        if self.top.tick(now):
            self.dirty = True
        if self._toast and now >= self._toast_until:
            self._toast = None
            self.dirty = True
        # A blocking tick (network call) must not turn a key still held into a long press.
        after = self.hal.ticks_ms()
        if after - now > 200:
            for k in self._held:
                if self._held[k] is not None:
                    self._held[k] = after
        cur = (self.top, len(self.stack))
        if self._last and cur[0] is not self._last[0]:
            name = type(self.top).__name__
            if not self.off and name not in ('Avvio', 'Spegnimento', 'Home') or (name == 'Home' and self._last[1] > 1):
                self._trans = (now, 1 if cur[1] > self._last[1] else -1)
                self._prev[:] = self.g.buf
        self._last = cur
        if self._trans and now - self._trans[0] >= self.TRANS_MS:
            self._trans = None
            self.dirty = True
        if self._toast and now - self._toast_t0 < 150:
            self.dirty = True
        if self.dirty or self._trans:
            self.g.clear()
            self.top.draw(self.g)
            if self._toast and not self.off:
                self._draw_toast(self.g, now)
            if self._trans:
                self.hal.show(self._slide(now))
            else:
                self.hal.show(self.g.buf)
            self.dirty = False

    TRANS_MS = 150

    def _slide(self, now):
        # Push: the old screen leaves to the left and the new one enters from the right; pop is the mirror.
        p = (now - self._trans[0]) / self.TRANS_MS
        p = 1 - (1 - p) * (1 - p)
        sft = int(W * p)
        new, old, out = self.g.buf, self._prev, bytearray(len(self.g.buf))
        for b in range(6):
            o = b * W
            if self._trans[1] > 0:
                out[o:o + W - sft] = old[o + sft:o + W]
                out[o + W - sft:o + W] = new[o:o + sft]
            else:
                out[o:o + sft] = new[o + W - sft:o + W]
                out[o + sft:o + W] = old[o:o + W - sft]
        return out

    def _draw_toast(self, g, now):
        lines = wrap(self._toast, 12)[:2]
        h = 6 + 9 * len(lines)
        # pops in: grows from the centre during the first 120 ms
        p = min(1, (now - self._toast_t0) / 120)
        w = max(8, int((W - 8) * p))
        hh = max(4, int(h * p))
        x, y = (W - w) // 2, (48 - hh) // 2
        g.panel(x, y, w, hh)
        if p >= 1:
            for i, line in enumerate(lines):
                g.text_center(line, y + 3 + 9 * i)

    def run(self):
        while self.hal.running():
            self.step()
            self.hal.sleep_ms(20)
