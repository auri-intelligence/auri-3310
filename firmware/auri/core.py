from auri import keys
from auri.gfx import Canvas

VERSION = '0.1.0'


class System:
    def __init__(self, hal, config):
        self.hal = hal
        self.config = config
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
        for k, t in list(self._held.items()):
            if t is not None and now - t >= keys.LONG_MS:
                self._held[k] = None
                self.top.on_long(k)
                self.dirty = True
        if self.top.tick(now):
            self.dirty = True
        if self.dirty:
            self.g.clear()
            self.top.draw(self.g)
            self.hal.show(self.g.buf)
            self.dirty = False

    def run(self):
        while self.hal.running():
            self.step()
            self.hal.sleep_ms(20)
