from auri import keys
from auri.gfx import W, H
from apps.giochi.base import Game, PHONE, PHONE_BIG, TOP, sin

LEFT = ('4', keys.UP, '1')
RIGHT = ('6', keys.DOWN, '3')


class SaliSali(Game):
    key = 'salisali'

    def setup(self):
        self.x, self.y = 40.0, 30.0
        self.vx, self.vy = 0.0, -3.0
        self.dir = 0
        self.height = 0
        self.plats = [[34, 42.0, 16, 0, False]]   # x, y, w, kind (0 normal, 1 spring, 2 crumbles), battery
        self.top_y = 42.0
        self._more()

    def _more(self):
        while self.top_y > TOP - 10:
            h = int(self.height)
            gap = 7 + min(9, h // 250) + self.r(4)
            self.top_y -= gap
            w = max(8, 16 - h // 300)
            k = 1 if self.r(9) == 0 else (2 if self.r(6) == 0 and h > 150 else 0)
            self.plats.append([self.r(W - w), self.top_y, w, k, self.r(14) == 0])

    def control(self, k):
        if k in LEFT:
            self.dir = -1
        elif k in RIGHT:
            self.dir = 1

    def release(self, k):
        if k in LEFT + RIGHT:
            self.dir = 0

    def update(self):
        self.vx = self.vx * 0.6 + self.dir * 1.0
        self.x = (self.x + self.vx) % W
        self.vy = min(3.5, self.vy + 0.22)
        oy = self.y
        self.y += self.vy
        if self.vy > 0:
            for p in self.plats:
                if oy + 8 <= p[1] <= self.y + 8 and p[0] - 4 <= self.x <= p[0] + p[2]:
                    self.y = p[1] - 8
                    self.vy = -5.6 if p[3] == 1 else -3.6
                    self.beep(1500 if p[3] == 1 else 800, 15)
                    if p[3] == 1:
                        self.burst(int(self.x) + 2, int(p[1]), 6, 3)
                    if p[3] == 2:
                        p[1] = H + 20
                        self.burst(p[0] + p[2] // 2, int(self.y) + 8, 5)
                    if p[4]:
                        p[4] = False
                        self.charge(int(self.x), int(self.y) - 6)
                    break
        if self.y < 20:
            d = 20 - self.y
            self.y = 20.0
            for p in self.plats:
                p[1] += d
            self.top_y += d
            self.height += d
            self.score = int(self.height // 4)
            self.plats = [p for p in self.plats if p[1] < H + 2]
            self._more()
        if self.y > H:
            # fell off: the 3310 hits bottom and is launched back up
            self.y = H - 2.0
            self.vy = -7.0
            self.shake = 4
            if not self.hurt(int(self.x), H - 4):
                return
            self.plats.append([int(self.x) - 8, H - 6.0, 18, 0, False])

    def render(self, g):
        for x, y, w, k, b in self.plats:
            y = int(y)
            if k == 2:
                for i in range(0, w, 2):
                    g.pixel(x + i, y)
                    g.pixel(x + i + 1, y + 1)
            else:
                g.hline(x, y, w)
                g.hline(x + 1, y + 1, w - 2)
            if k == 1:
                g.icon(('#.#', '.#.', '#.#', '###'), x + w // 2 - 1, y - 4)
            if b:
                g.rect(x + w // 2 - 2, y - 7, 4, 6)
                g.pixel(x + w // 2 - 1, y - 8)
        x, y = int(self.x), int(self.y)
        g.icon(PHONE, x, y)
        if x > W - 5:
            g.icon(PHONE, x - W, y)
        if self.vy < -4:
            g.pixel(x + 1, y + 10)
            g.pixel(x + 3, y + 11)

    def art(self, g, el):
        for i in range(5):
            y = (12 + i * 8 + el // 40) % 36 + 10
            g.hline(8 + (i * 29) % 60, y, 14)
        y = 30 - int(abs(14 * sin(el / 350)))
        g.icon2(PHONE_BIG, 37, y - 6, 1, 1)
