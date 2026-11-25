from auri import keys
from auri.gfx import W, H
from apps.giochi.base import Game, PHONE, PHONE_BIG, sin

C = 3
COLS = 10
ROWS = 12
X0 = 2
Y0 = 11
# our own set: from a single cell up to the plus, mixed sizes
PIECES = (
    ((0, 0),), ((0, 0), (1, 0)), ((0, 0), (1, 0), (2, 0)), ((0, 0), (1, 0), (0, 1)),
    ((0, 0), (1, 0), (0, 1), (1, 1)), ((0, 0), (1, 0), (2, 0), (1, 1)), ((0, 0), (1, 0), (2, 0), (0, 1)),
    ((1, 0), (0, 1), (1, 1), (2, 1), (1, 2)), ((0, 0), (1, 0), (1, 1), (2, 1)),
)
SCORES = (0, 10, 30, 60, 100, 150)
HERO = ((0, 0), (0, 1), (0, 2))   # the 3310 piece, never rotates


class Incastro(Game):
    key = 'incastro'

    def setup(self):
        self.grid = bytearray(COLS * ROWS)
        self.lines = 0
        self.next = self.r(len(PIECES))
        self.hero = False
        self.clearing = []
        self.fall = 0
        self._spawn()

    def _spawn(self):
        self.hero = self.next < 0
        self.cells = HERO if self.hero else PIECES[self.next]
        self.next = -1 if self.r(7) == 0 else self.r(len(PIECES))
        self.px, self.py = COLS // 2 - 1, 0
        if not self._fits(self.cells, self.px, self.py):
            if not self.hurt(X0 + COLS * C // 2, Y0 + 4):
                return
            # the 3310 drops in and blasts the top half of the stack
            for i in range(COLS * ROWS // 2):
                self.grid[i] = 0
            for x in range(0, COLS, 2):
                self.burst(X0 + x * C, Y0 + 6, 3)
            self.sys.play('c4:32 c5:32 c6:16', 220)

    def _fits(self, cells, px, py):
        for x, y in cells:
            x, y = px + x, py + y
            if x < 0 or x >= COLS or y >= ROWS or (y >= 0 and self.grid[y * COLS + x]):
                return False
        return True

    def _rot(self):
        if self.hero:
            return
        c = [(-y, x) for x, y in self.cells]
        mx, my = min(x for x, _ in c), min(y for _, y in c)
        c = tuple((x - mx, y - my) for x, y in c)
        for dx in (0, -1, 1, -2):
            if self._fits(c, self.px + dx, self.py):
                self.cells, self.px = c, self.px + dx
                self.beep(1200, 8)
                return

    def _move(self, dx):
        if self._fits(self.cells, self.px + dx, self.py):
            self.px += dx
            self.beep(800, 6)

    def _drop(self):
        while self._fits(self.cells, self.px, self.py + 1):
            self.py += 1
            self.score += 1
        self.shake = 2
        self._lock()

    def control(self, k):
        if self.clearing:
            return
        if k == '4':
            self._move(-1)
        elif k == '6':
            self._move(1)
        elif k in ('2', keys.UP):
            self._rot()
        elif k in ('8', keys.DOWN):
            if self._fits(self.cells, self.px, self.py + 1):
                self.py += 1
            else:
                self._lock()
        elif k in ('5', keys.NAVI):
            self._drop()

    def held(self, k):
        if k in ('8', keys.DOWN) and not self.clearing:
            self._drop()

    def _smash(self):
        # the 3310 does not stack: it drills straight through everything below it
        x, n = self.px, 0
        for y in range(self.py, ROWS):
            if self.grid[y * COLS + x]:
                self.grid[y * COLS + x] = 0
                n += 1
            self.burst(X0 + x * C + 1, Y0 + y * C + 1, 2)
        self.add(10 + 15 * n, X0 + x * C, Y0 + self.py * C)
        self.shake = 6
        self.sys.vibrate(120)
        self.sys.play('c4:32 g4:32 c5:32 c6:16', 240)
        self._spawn()

    def _phone(self, g, x, y):
        g.fill_rect(x, y, C, 3 * C)
        g.pixel(x + 1, y + 1, 0)
        g.pixel(x + 1, y + 2, 0)
        g.pixel(x + 1, y + 5, 0)
        g.pixel(x + 1, y + 7, 0)

    def _lock(self):
        if self.hero:
            self._smash()
            return
        for x, y in self.cells:
            if y + self.py >= 0:
                self.grid[(self.py + y) * COLS + self.px + x] = 1
        self.beep(400, 10)
        full = [y for y in range(ROWS) if all(self.grid[y * COLS:(y + 1) * COLS])]
        if full:
            self.clearing = [full, 6]
            n = len(full)
            self.add(SCORES[min(n, 5)], X0 + COLS * C // 2, Y0 + full[0] * C)
            self.lines += n
            self.flash = 1
            self.sys.play(('e6:32 g6:32', 'e6:32 g6:32 c7:16', 'c6:32 e6:32 g6:32 c7:8')[min(n, 3) - 1], 240)
            for y in full:
                for x in range(0, COLS, 2):
                    self.burst(X0 + x * C + 1, Y0 + y * C, 2)
        else:
            self._spawn()

    def update(self):
        if self.clearing:
            self.clearing[1] -= 1
            if self.clearing[1] <= 0:
                for y in self.clearing[0]:
                    self.grid[COLS:(y + 1) * COLS] = self.grid[0:y * COLS]
                    self.grid[0:COLS] = bytes(COLS)
                self.clearing = []
                self._spawn()
            return
        self.fall += 1
        if self.fall >= max(2, 12 - self.lines // 4):
            self.fall = 0
            if self._fits(self.cells, self.px, self.py + 1):
                self.py += 1
            else:
                self._lock()

    def _cell(self, g, x, y):
        g.fill_rect(x, y, C, C)
        g.pixel(x + 1, y + 1, 0)

    def render(self, g):
        g.rect(X0 - 1, Y0 - 1, COLS * C + 2, ROWS * C + 2)
        blink = self.clearing and self.clearing[1] % 2
        for y in range(ROWS):
            if blink and y in self.clearing[0]:
                continue
            for x in range(COLS):
                if self.grid[y * COLS + x]:
                    self._cell(g, X0 + x * C, Y0 + y * C)
        if not self.clearing and self.state == 'play':
            gy = self.py
            while self._fits(self.cells, self.px, gy + 1):
                gy += 1
            if self.hero:
                # drill target: the whole column below lights up
                for y in range(self.py + 3, ROWS, 2):
                    g.pixel(X0 + self.px * C + 1, Y0 + y * C + 1, 2)
                self._phone(g, X0 + self.px * C, Y0 + self.py * C)
            else:
                for x, y in self.cells:
                    g.pixel(X0 + (self.px + x) * C + 1, Y0 + (gy + y) * C + 1)
                    if y + self.py >= 0:
                        g.fill_rect(X0 + (self.px + x) * C, Y0 + (self.py + y) * C, C, C)
        bx = X0 + COLS * C + 6
        g.text('%d' % self.lines, bx, 11)
        g.rect(bx, 21, 16, 16)
        if self.next < 0:
            self._phone(g, bx + 6, 24)
        else:
            for x, y in PIECES[self.next]:
                self._cell(g, bx + 3 + x * C, 24 + y * C)
        g.icon(PHONE, W - 7, 39 - int(2 * abs(sin(self.frame / 4))))

    def art(self, g, el):
        n = el // 120
        for i in range(8):
            x = 6 + (i * 37) % 70
            y = 12 + (n * (1 + i % 3) + i * 7) % 26
            g.fill_rect(x, y, 6, 3)
            g.fill_rect(x + 3, y + 3, 3, 3)
        g.fill_rect(30, 32, 26, 6, 0)
        g.icon2(PHONE_BIG, 37, 24, 1, 1)
