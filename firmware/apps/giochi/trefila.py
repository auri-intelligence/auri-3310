from auri import keys
from auri.gfx import W, H
from apps.giochi.base import Game, PHONE_BIG, sin

CS = 9
COLS, ROWS = 7, 4
Y0 = 11
TIME = 1200      # steps of 50 ms: one minute
GEMS = (
    ('...#...', '..#.#..', '.#.#.#.', '#.#.#.#', '...#...', '...#...', '..###..'),   # antenna
    ('#######', '##...##', '#.#.#.#', '#..#..#', '#.....#', '#.....#', '#######'),   # envelope
    ('.##.##.', '#######', '#######', '#######', '.#####.', '..###..', '...#...'),   # heart
    ('...#...', '...#...', '#######', '.#####.', '..###..', '.##.##.', '#.....#'),   # star
    ('..####.', '.#....#', '#.##..#', '#.##..#', '#.....#', '#..##.#', '#######'),   # sim card
)
PHONE = 5
PHONE_GEM = ('.#####.', '#.....#', '#.###.#', '#.....#', '#.#.#.#', '#.....#', '.#####.')
DIRS = {'2': (0, -1), '8': (0, 1), '4': (-1, 0), '6': (1, 0), keys.UP: (0, -1), keys.DOWN: (0, 1)}


class TreFila(Game):
    key = 'trefila'
    ROLL = False

    def setup(self):
        self.cx, self.cy = 3, 1
        self.sel = False
        self.time = TIME
        self.clear = None   # (set of cells, steps left)
        self.combo = 0
        self.undo = None
        self.b = bytearray(COLS * ROWS)
        self._fill_all()

    def _fill_all(self):
        while True:
            for i in range(len(self.b)):
                self.b[i] = self.r(len(GEMS))
            if not self._matches() and self._has_move():
                return

    def _matches(self):
        m = set()
        b = self.b
        for y in range(ROWS):
            for x in range(COLS - 2):
                i = y * COLS + x
                if b[i] == b[i + 1] == b[i + 2]:
                    m.update((i, i + 1, i + 2))
        for y in range(ROWS - 2):
            for x in range(COLS):
                i = y * COLS + x
                if b[i] == b[i + COLS] == b[i + 2 * COLS]:
                    m.update((i, i + COLS, i + 2 * COLS))
        return m

    def _swap(self, i, j):
        self.b[i], self.b[j] = self.b[j], self.b[i]

    def _has_move(self):
        for i in range(len(self.b)):
            for j in (i + 1, i + COLS):
                if j < len(self.b) and (j != i + 1 or i % COLS < COLS - 1):
                    self._swap(i, j)
                    ok = bool(self._matches())
                    self._swap(i, j)
                    if ok:
                        return True
        return False

    def control(self, k):
        if self.clear:
            return
        if k in ('5', keys.NAVI):
            self.sel = not self.sel
            self.beep(1000 if self.sel else 700, 10)
            return
        if k not in DIRS:
            return
        dx, dy = DIRS[k]
        nx, ny = self.cx + dx, self.cy + dy
        if not (0 <= nx < COLS and 0 <= ny < ROWS):
            return
        if self.sel:
            i, j = self.cy * COLS + self.cx, ny * COLS + nx
            self._swap(i, j)
            self.sel = False
            if PHONE in (self.b[i], self.b[j]):
                self._blast(j if self.b[j] == PHONE else i)
                self.cx, self.cy = nx, ny
                return
            if self._matches():
                self.combo = 0
                self.cx, self.cy = nx, ny
                self._resolve()
            else:
                self._swap(i, j)
                self.shake = 2
                self.beep(200, 30)
        else:
            self.cx, self.cy = nx, ny

    def _blast(self, p):
        # the 3310 explodes: its whole row and column are cleared
        x, y = p % COLS, p // COLS
        m = set(y * COLS + c for c in range(COLS)) | set(r * COLS + x for r in range(ROWS))
        self.combo = 1
        self.add(15 * len(m), x * CS + 4, Y0 + y * CS)
        self.clear = [m, 7]
        self.flash = 2
        self.shake = 4
        self.sys.vibrate(120)
        self.sys.play('c5:32 g5:32 c6:32 g6:16', 240)
        for c in m:
            self.burst((c % COLS) * CS + 4, Y0 + (c // COLS) * CS + 4, 2)

    def _gem(self):
        return PHONE if self.r(25) == 0 else self.r(len(GEMS))

    def _resolve(self):
        m = self._matches()
        if not m:
            if not self._has_move():
                self._fill_all()
                self.flash = 1
            return
        self.combo += 1
        n = len(m)
        pts = 10 * n * self.combo
        i = min(m)
        self.add(pts, (i % COLS) * CS + 4, Y0 + (i // COLS) * CS)
        if n >= 4:
            self.time = min(TIME, self.time + 60)
        self.clear = [m, 5]
        self.beep(1200 + 200 * min(self.combo, 6), 25)
        for c in m:
            self.burst((c % COLS) * CS + 4, Y0 + (c // COLS) * CS + 4, 2)

    def update(self):
        if self.clear:
            self.clear[1] -= 1
            if self.clear[1] <= 0:
                for c in self.clear[0]:
                    self.b[c] = 255
                for x in range(COLS):
                    col = [self.b[y * COLS + x] for y in range(ROWS) if self.b[y * COLS + x] != 255]
                    col = [self._gem() for _ in range(ROWS - len(col))] + col
                    for y in range(ROWS):
                        self.b[y * COLS + x] = col[y]
                self.clear = None
                self._resolve()
            return
        self.time -= 1
        if self.time <= 0:
            # out of time: a spare battery buys 20 more seconds
            if self.hurt(W - 10, 20):
                self.time = 400

    def render(self, g):
        blink = self.clear and self.clear[1] % 2
        for i in range(COLS * ROWS):
            x, y = (i % COLS) * CS + 1, Y0 + (i // COLS) * CS + 1
            if blink and i in self.clear[0]:
                g.fill_rect(x + 2, y + 2, 3, 3)
                continue
            v = self.b[i]
            g.icon(PHONE_GEM if v == PHONE else GEMS[v % len(GEMS)], x, y)
        x, y = self.cx * CS, Y0 + self.cy * CS
        if self.sel:
            g.rect(x - 1, y - 1, CS + 2, CS + 2)
            g.rect(x, y, CS, CS)
        elif (self.frame // 4) % 2:
            g.rect(x, y, CS, CS)
        bx = COLS * CS + 3
        h = 34 * self.time // TIME
        g.rect(bx, Y0, 6, 36)
        g.fill_rect(bx + 1, Y0 + 35 - h, 4, h)
        if self.combo > 1 and self.clear:
            g.text('x%d' % self.combo, bx + 7, 20)
        g.icon(GEMS[(self.frame // 20) % len(GEMS)], W - 8, 38)

    def art(self, g, el):
        for i in range(9):
            x, y = 2 + i * 9, 16 + int(5 * sin(el / 200 + i))
            g.icon(GEMS[(i + el // 600) % len(GEMS)], x, y)
        g.icon2(PHONE_BIG, 37, 25, 1, 1)
