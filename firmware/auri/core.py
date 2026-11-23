from auri import keys
from auri.gfx import Canvas

VERSION = '0.1.0'


class System:
    def __init__(self, hal, config):
        self.hal = hal
        self.config = config
        from auri import i18n
        i18n.set_lang(hal.load('settings', {}).get('lang', config.get('lang', 'it')))
        self.g = Canvas()
        self.stack = []
        self.dirty = True
        self._held = {}

    def push(self, app):
        self.stack.append(app)
        self.dirty = True

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()
        self.dirty = True

    def assistant(self, trigger):
        from apps.assistente import Assistente
        self.push(Assistente(self, trigger))

    def home(self):
        del self.stack[1:]
        self.dirty = True

    @property
    def top(self):
        return self.stack[-1]

    def step(self):
        now = self.hal.ticks_ms()
        for kind, k in self.hal.events():
            if kind == 'down':
                self._held[k] = now
                self.hal.light(1)
                self.top.on_key(k)
                self.dirty = True
            elif kind == 'up':
                self._held.pop(k, None)
                if hasattr(self.top, 'on_up'):
                    self.top.on_up(k)
                    self.dirty = True
        for k, t in list(self._held.items()):
            if t is not None and now - t >= keys.LONG_MS:
                self._held[k] = None
                if k == keys.POWER and type(self.top).__name__ != 'Assistente':
                    self.assistant(k)
                else:
                    self.top.on_long(k)
                self.dirty = True
        if self.top.tick(now):
            self.dirty = True
        # A blocking tick (network call) must not turn a key still held into a long press.
        after = self.hal.ticks_ms()
        if after - now > 200:
            for k in self._held:
                if self._held[k] is not None:
                    self._held[k] = after
        if self.dirty:
            self.g.clear()
            self.top.draw(self.g)
            self.hal.show(self.g.buf)
            self.dirty = False

    def run(self):
        while self.hal.running():
            self.step()
            self.hal.sleep_ms(20)
