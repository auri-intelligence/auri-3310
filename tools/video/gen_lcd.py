import os
import sys
import numpy as np

FW = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'firmware')
sys.path.insert(0, os.path.abspath(FW))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'lcd.npz')
os.chdir(os.path.abspath(FW))

from hal.pc import PCHal, W, H
from auri.core import System
from auri import keys
from apps.home import Home
import sim

DT = 1000 / 30


class VideoHal(PCHal):
    def __init__(self):
        super().__init__((2026, 11, 23, 20, 0, 0, 0, 327))
        self.mem = {}
        self.polls = 0

    def beep(self, f, ms):
        pass

    def load(self, k, d=None):
        return self.mem.get(k, d)

    def save(self, k, v):
        self.mem[k] = v

    def voice_start(self):
        return True

    def voice_stop(self, url, params, token):
        self.polls = 0

    def voice_poll(self):
        self.polls += 1
        if self.polls < 18:
            return None
        return {'transcript': 'Ciao AurI, ci sei?', 'reply': 'Ci sono! Nuovo cervello, stesso cuore del 2000.'}


class Rec:
    def __init__(self):
        self.hal = VideoHal()
        cfg = sim.load_config()
        cfg['bridge_url'] = 'http://x'
        self.s = System(self.hal, cfg)
        self.s.push(Home(self.s))
        self.s.step()
        self.frames = []

    def tick(self, n=1, rec=True):
        for _ in range(n):
            self.hal._t0 -= DT / 1000
            self.s.step()
            if rec:
                self.frames.append(np.array([[self.hal.pixel(x, y) for x in range(W)] for y in range(H)], bool))

    def tap(self, k, hold=2):
        self.hal.press(k)
        self.tick(hold)
        self.hal.release(k)
        self.tick(4)

    def take(self):
        f, self.frames = np.array(self.frames), []
        return f


r = Rec()
r.tick(30)
home = r.take()
r.tap(keys.NAVI)
r.tick(8)
for _ in range(2):
    r.tap(keys.DOWN)
    r.tick(5)
menu = r.take()
r.tap(keys.NAVI)
r.tick(10)
for k in [keys.UP, None, keys.RIGHT if hasattr(keys, 'RIGHT') else '6', None, '8', None, '4', None]:
    if k:
        r.tap(k, 1)
    r.tick(8)
snake = r.take()
r.tap(keys.C)
r.tap(keys.C)
r.tap(keys.C)
r.tick(5, rec=False)
r.hal.press(keys.NAVI)
r.tick(75)
r.hal.release(keys.NAVI)
r.tick(90)
assist = r.take()
np.savez_compressed(OUT,
                    home=home, menu=menu, snake=snake, assist=assist)
print(home.shape, menu.shape, snake.shape, assist.shape)
