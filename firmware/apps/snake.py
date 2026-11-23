from auri import keys
from auri.ui import App, header
from auri.gfx import W
from auri.i18n import t

CELL = 3
COLS = W // CELL
ROWS = 13
TOP = 9
DIRS = {'2': (0, -1), '8': (0, 1), '4': (-1, 0), '6': (1, 0), keys.UP: (0, -1), keys.DOWN: (0, 1)}


class Snake(App):
    def __init__(self, sys):
        super().__init__(sys)
        self.best = sys.hal.load('snake', {'best': 0})['best']
        self.reset()

    def reset(self):
        self.body = [(6, 6), (5, 6), (4, 6)]
        self.dir = (1, 0)
        self.next_dir = self.dir
        self.score = 0
        self.dead = False
        self.speed = 160
        self.last = 0
        self.food = self._place()

    def _place(self):
        r = self.sys.hal.random
        while True:
            p = (r(COLS), r(ROWS))
            if p not in self.body:
                return p

    def on_key(self, k):
        if self.dead:
            if k == keys.NAVI:
                self.reset()
            elif k == keys.C:
                self.sys.pop()
            return
        if k in DIRS:
            d = DIRS[k]
            if (d[0] + self.dir[0], d[1] + self.dir[1]) != (0, 0):
                self.next_dir = d
        elif k == keys.C:
            self.sys.pop()

    def tick(self, now):
        if self.dead or now - self.last < self.speed:
            return False
        self.last = now
        self.dir = self.next_dir
        hx, hy = self.body[0]
        head = ((hx + self.dir[0]) % COLS, (hy + self.dir[1]) % ROWS)
        if head in self.body[:-1]:
            self.dead = True
            self.sys.hal.vibrate(300)
            if self.score > self.best:
                self.best = self.score
                self.sys.hal.save('snake', {'best': self.best})
            return True
        self.body.insert(0, head)
        if head == self.food:
            self.score += 1
            self.speed = max(60, self.speed - 4)
            self.food = self._place()
            self.sys.hal.beep(1800, 30)
        else:
            self.body.pop()
        return True

    def draw(self, g):
        if self.dead:
            header(g, t('game_over'))
            g.text_center('%s: %d' % (t('points'), self.score), 14)
            g.text_center('%s: %d' % (t('record'), self.best), 24)
            g.text_center(t('again'), 40)
            return
        g.text('%04d' % self.score, 0, 0)
        g.text('R%d' % self.best, W - 6 * len('R%d' % self.best), 0)
        g.hline(0, TOP - 1, W)
        for x, y in self.body:
            g.fill_rect(x * CELL, TOP + y * CELL, CELL, CELL)
        fx, fy = self.food
        g.rect(fx * CELL, TOP + fy * CELL, CELL, CELL)
        g.pixel(fx * CELL + 1, TOP + fy * CELL + 1, 0)
