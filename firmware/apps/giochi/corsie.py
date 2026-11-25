from auri import keys
from auri.gfx import W, H
from apps.giochi.base import Game, PHONE, TOP, sin

LANES = (16, 42, 68)
PY = 36
CRATE = ('#########', '##.....##', '#.#...#.#', '#..#.#..#', '#.#...#.#', '##.....##', '#########')


class Corsie(Game):
    key = 'corsie'

    def setup(self):
        self.lane = 1
        self.x = float(LANES[1])
        self.obs = []   # [lane, y, kind]  kind: 0 crate, 1 coin, 2 battery
        self.speed = 1.7
        self.scroll = 0
        self.jump = 0
        self.gap = 0

    def control(self, k):
        if k in ('4', keys.UP) and self.lane > 0:
            self.lane -= 1
            self.beep(700, 10)
        elif k in ('6', keys.DOWN) and self.lane < 2:
            self.lane += 1
            self.beep(700, 10)
        elif k in ('2', '5', keys.NAVI) and not self.jump:
            self.jump = 14
            self.beep(1100, 20)

    def update(self):
        self.scroll += self.speed
        self.speed = min(4.0, 1.7 + self.frame / 400)
        if self.frame % 10 == 0:
            self.add(1)
        tx = LANES[self.lane]
        self.x += (tx - self.x) / 2
        if self.jump:
            self.jump -= 1
        self.gap -= self.speed
        if self.gap <= 0:
            self.gap = max(9, 14 - self.frame // 400) + self.r(9)
            free = self.r(3)
            for ln in range(3):
                if ln != free and self.r(3) == 0:
                    self.obs.append([ln, TOP - 7.0, 0])
            k = 2 if self.r(12) == 0 else 1
            if self.r(2):
                self.obs.append([free, TOP - 7.0, k])
        for o in self.obs:
            o[1] += self.speed
            if o[1] > H + 2 or self.lane != o[0] or abs(self.x - LANES[o[0]]) > 6:
                continue
            if PY - 6 < o[1] < PY + 7:
                if o[2] == 1:
                    o[1] = H + 9
                    self.add(5, self.x, PY - 10)
                    self.beep(1900, 15)
                elif o[2] == 2:
                    o[1] = H + 9
                    self.charge(self.x, PY - 10)
                elif not self.jump:
                    # the crate explodes, the 3310 keeps running
                    o[1] = H + 9
                    self.burst(int(self.x), PY, 10, 2)
                    if not self.hurt(int(self.x), PY):
                        return
        self.obs = [o for o in self.obs if o[1] < H + 3]

    def render(self, g):
        s = int(self.scroll)
        for bx in (29, 55):
            for y in range(TOP + (s % 8) - 8, H, 8):
                g.vline(bx, y, 4)
        g.vline(2, TOP, H - TOP)
        g.vline(W - 3, TOP, H - TOP)
        for y in range(TOP + (s % 4), H, 4):
            g.pixel(0, y)
            g.pixel(W - 1, y)
        for ln, y, k in self.obs:
            x, y = LANES[ln], int(y)
            if k == 0:
                g.fill_rect(x - 5, y, 11, 7, 0)
                g.icon(CRATE, x - 4, y)
            elif k == 1:
                g.fill_rect(x - 1, y + 1, 3, 3)
                g.pixel(x, y)
                g.pixel(x, y + 4)
            else:
                g.rect(x - 2, y, 5, 7)
                g.pixel(x, y - 1)
                if (self.frame // 3) % 2:
                    g.fill_rect(x - 1, y + 2, 3, 4)
        x = int(self.x) - 2
        lift = int(5 * sin(3.1416 * self.jump / 14)) if self.jump else 0
        if lift:
            g.dither(x, PY + 9, 5, 1, 2)
        g.fill_rect(x - 1, PY - lift - 1, 7, 10, 0)
        g.icon(PHONE, x, PY - lift)
        if self.frame % 2:
            g.pixel(x + 1, PY - lift + 9)
            g.pixel(x + 3, PY - lift + 10)

    def art(self, g, el):
        for bx in (29, 55):
            for y in range(12 + (el // 30) % 8 - 8, 40, 8):
                g.vline(bx, y, 4)
        ln = (el // 700) % 3
        g.icon(PHONE, LANES[ln] - 2, 28)
        cy = 12 + (el // 30) % 28
        g.icon(CRATE, LANES[(ln + 1) % 3] - 4, cy)
