from auri import keys
from auri.ui import App
from auri.gfx import W, H
from auri.i18n import t

CELL = 3
COLS = W // CELL
ROWS = 12
TOP = 10
DIRS = {'2': (0, -1), '8': (0, 1), '4': (-1, 0), '6': (1, 0), keys.UP: (0, -1), keys.DOWN: (0, 1)}


class Snake(App):
    def __init__(self, sys):
        super().__init__(sys)
        self.best = sys.hal.load('snake', {'best': 0})['best']
        self.state = 'intro'
        self.t0 = sys.hal.ticks_ms()
        self.reset()

    def reset(self):
        self.body = [(6, 6), (5, 6), (4, 6)]
        self.dir = (1, 0)
        self.next_dir = self.dir
        self.score = 0
        self.shown = 0
        self.speed = 160
        self.last = 0
        self.sparks = []  # (x, y, vx, vy, life)
        self.pops = []    # (x, y, born)
        self.food = self._place()
        self.newbest = False

    def _place(self):
        r = self.sys.hal.random
        while True:
            p = (r(COLS), r(ROWS))
            if p not in self.body:
                return p

    def on_key(self, k):
        if self.state == 'intro':
            if k == keys.C:
                self.sys.pop()
            else:
                self.state = 'play'
            return
        if self.state in ('dying', 'over'):
            if k == keys.NAVI and self.state == 'over':
                self.reset()
                self.state = 'play'
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
        if self.state == 'intro':
            return True
        if self.state == 'dying':
            if now - self.t0 > 1100:
                self.state = 'over'
                self.t0 = now
            return True
        if self.state == 'over':
            return self.shown < self.score or now - self.t0 < 3000
        moved = False
        if now - self.last >= self.speed:
            self.last = now
            moved = self._step(now)
        self.sparks = [(x + vx, y + vy, vx, vy + 0.15, l - 1) for x, y, vx, vy, l in self.sparks if l > 0]
        self.pops = [p for p in self.pops if now - p[2] < 600]
        return moved or bool(self.sparks) or bool(self.pops) or True

    def _step(self, now):
        self.dir = self.next_dir
        hx, hy = self.body[0]
        head = ((hx + self.dir[0]) % COLS, (hy + self.dir[1]) % ROWS)
        if head in self.body[:-1]:
            self.state = 'dying'
            self.t0 = now
            sc = self.score
            self.sys.track('snake/punti_' + ('0' if sc == 0 else '1-4' if sc < 5 else '5-14' if sc < 15 else '15-29' if sc < 30 else '30+'))
            self.sys.vibrate(300)
            self.sys.play('c6:16 g5:16 e5:16 c5:4', 200)
            if self.score > self.best:
                self.best = self.score
                self.newbest = True
                self.sys.hal.save('snake', {'best': self.best})
            return True
        self.body.insert(0, head)
        if head == self.food:
            self.score += 1
            self.speed = max(60, self.speed - 4)
            cx, cy = head[0] * CELL + 1, TOP + head[1] * CELL + 1
            r = self.sys.hal.random
            for i in range(10):
                self.sparks.append((cx, cy, (r(9) - 4) / 3, (r(9) - 6) / 3, 6 + r(5)))
            self.pops.append((cx, cy - 3, now))
            self.food = self._place()
            if self.sys.settings['volume']:
                self.sys.hal.beep(1800, 30, self.sys.settings['volume'])
        else:
            self.body.pop()
        return True

    # --- drawing ---
    def _intro(self, g, now):
        el = now - self.t0
        g.text_center('SNAKE', 2, 1, 2)
        # a snake slithering along a sine wave under the title
        n = 14
        for i in range(n):
            x = (el // 40 - i * 3) % (W + 40) - 20
            y = 27 + int(4 * _sin((x + el // 20) / 9))
            g.fill_rect(x, y, 3, 3)
        hx = (el // 40) % (W + 40) - 20
        g.pixel(hx + 2, 27 + int(4 * _sin((hx + el // 20) / 9)), 0)
        if (el // 500) % 2:
            g.text_center(t('press_key'), 38)
        g.text('R%d' % self.best, 0, 40)

    def _head(self, g, x, y):
        g.fill_rect(x, y, CELL, CELL)
        dx, dy = self.dir
        ex, ey = x + 1 + dx, y + 1 + dy
        g.pixel(min(x + 2, max(x, ex)), min(y + 2, max(y, ey)), 0)

    def draw(self, g):
        now = self.sys.hal.ticks_ms()
        if self.state == 'intro':
            self._intro(g, now)
            return
        if self.state == 'over':
            if self.shown < self.score:
                self.shown += 1
            g.text_center(t('game_over'), 0)
            g.text_center('%d' % self.shown, 11, 1, 2)
            if self.newbest and (now // 300) % 2:
                g.text_center(t('new_record'), 29)
            else:
                g.text_center('%s %d' % (t('record'), self.best), 29)
            g.text_center(t('again'), 40)
            return
        g.text('%04d' % self.score, 0, 0)
        g.text('R%d' % self.best, W - 6 * len('R%d' % self.best), 0)
        g.hline(0, TOP - 2, W)
        if self.state == 'dying':
            # the body blinks, then crumbles away from the tail
            el = now - self.t0
            keep = len(self.body) - int(len(self.body) * max(0, el - 400) / 700)
            if el < 400 and (el // 100) % 2:
                return
            for x, y in self.body[:max(0, keep)]:
                g.fill_rect(x * CELL, TOP + y * CELL, CELL, CELL)
            return
        for i, (x, y) in enumerate(self.body):
            if i == 0:
                self._head(g, x * CELL, TOP + y * CELL)
            else:
                g.fill_rect(x * CELL, TOP + y * CELL, CELL, CELL)
                if i % 2:
                    g.pixel(x * CELL + 1, TOP + y * CELL + 1, 0)
        fx, fy = self.food
        if (now // 250) % 3:
            g.fill_rect(fx * CELL, TOP + fy * CELL, CELL, CELL)
            g.pixel(fx * CELL + 1, TOP + fy * CELL + 1, 0)
        else:
            g.pixel(fx * CELL + 1, TOP + fy * CELL + 1)
        for x, y, _vx, _vy, _l in self.sparks:
            g.pixel(int(x), int(y), 2)
        for x, y, born in self.pops:
            g.text('+1', x - 5, y - (now - born) // 60 - 6, 2)


def _sin(x):
    # small sine approximation (no float math module needed on every port)
    x = x % 6.2832
    if x > 3.1416:
        return -_sin(x - 3.1416)
    return 4 * x * (3.1416 - x) / (49.348 - x * (3.1416 - x))
