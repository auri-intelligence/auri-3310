from auri import keys
from auri.gfx import W, H
from apps.giochi.base import Game, PHONE_BIG, sin

BW, BH = 11, 4
BCOLS, BROWS = 7, 4
BY = 11
PW = 16
PY = H - 3
BALL = ('###', '#.#', '###', '#.#')
LEFT = ('4', keys.UP)
RIGHT = ('6', keys.DOWN)


class Rompimuro(Game):
    key = 'rompimuro'

    def setup(self):
        self.level = 0
        self.px = W / 2 - PW / 2
        self.dir = 0
        self.drops = []
        self._level()

    def _level(self):
        self.level += 1
        # each level has its own pattern; 2 = tough brick that takes two hits
        L = self.level
        self.bricks = bytearray(BCOLS * BROWS)
        for i in range(len(self.bricks)):
            r, c = i // BCOLS, i % BCOLS
            if L % 3 == 2 and (r + c) % 2:
                continue
            if L % 3 == 0 and abs(c - 3) + r > 4:
                continue
            self.bricks[i] = 2 if (L > 1 and r == 0) else 1
        self.bx, self.by = W / 2, PY - 6.0
        sp = min(2.2, 1.3 + L * 0.15)
        self.vx, self.vy = sp * (0.6 if self.r(2) else -0.6), -sp
        self.stuck = 20

    def control(self, k):
        if k in LEFT:
            self.dir = -1
        elif k in RIGHT:
            self.dir = 1
        elif k in ('5', keys.NAVI):
            self.stuck = 0

    def release(self, k):
        if k in LEFT + RIGHT:
            self.dir = 0

    def update(self):
        self.px = max(0, min(W - PW, self.px + self.dir * 3))
        if self.stuck:
            self.stuck -= 1
            self.bx = self.px + PW / 2
            return
        self.bx += self.vx
        self.by += self.vy
        if self.bx < 1 or self.bx > W - 3:
            self.vx = -self.vx
            self.bx = max(1, min(W - 3, self.bx))
        if self.by < 10:
            self.vy = abs(self.vy)
        if self.vy > 0 and PY - 4 <= self.by <= PY - 2 and self.px - 2 <= self.bx <= self.px + PW:
            # where it lands on the bar sets the angle
            off = (self.bx + 1 - self.px - PW / 2) / (PW / 2)
            sp = (self.vx * self.vx + self.vy * self.vy) ** 0.5
            self.vx = sp * off * 0.8
            self.vy = -(abs(sp * sp - self.vx * self.vx) ** 0.5)
            self.beep(600, 12)
        if self.by > H - 4:
            self.vy = -abs(self.vy)
            self.by = H - 4
            if not self.hurt(int(self.bx), H - 4):
                return
        c = int((self.bx + 1) // (BW + 1))
        r = int((self.by + 2 - BY) // (BH + 1))
        if 0 <= r < BROWS and 0 <= c < BCOLS and self.bricks[r * BCOLS + c]:
            i = r * BCOLS + c
            self.bricks[i] -= 1
            self.vy = -self.vy
            x, y = c * (BW + 1) + BW // 2, BY + r * (BH + 1)
            if self.bricks[i] == 0:
                self.add(5 * self.level, x, y)
                self.burst(x, y, 6)
                self.beep(1500 + r * 200, 15)
                if self.r(8) == 0:
                    self.drops.append([x, float(y)])
            else:
                self.beep(900, 15)
        for d in self.drops:
            d[1] += 0.8
            if PY - 4 <= d[1] <= PY + 1 and self.px - 2 <= d[0] <= self.px + PW + 2:
                d[1] = H + 5
                self.charge(d[0], PY - 12)
        self.drops = [d for d in self.drops if d[1] < H]
        if not any(self.bricks):
            self.add(50, W // 2, 24)
            self.sys.play('c6:16 e6:16 g6:16 c7:8', 200)
            self.flash = 2
            self._level()

    def render(self, g):
        for i in range(BCOLS * BROWS):
            v = self.bricks[i]
            if v:
                x, y = (i % BCOLS) * (BW + 1), BY + (i // BCOLS) * (BH + 1)
                g.fill_rect(x, y, BW, BH)
                if v == 1:
                    g.hline(x + 1, y + 1, BW - 2, 0)
                    g.hline(x + 1, y + 2, BW - 2, 0)
                    g.dither(x + 1, y + 1, BW - 2, 2, 2)
        for x, y in self.drops:
            g.rect(int(x) - 1, int(y), 4, 5)
            g.pixel(int(x), int(y) - 1)
        px = int(self.px)
        g.fill_rect(px + 1, PY, PW - 2, 3)
        g.hline(px, PY + 1, PW)
        g.hline(px + 3, PY + 1, PW - 6, 0)
        g.icon(BALL, int(self.bx), int(self.by))
        for i in range(0, W, 4):
            g.pixel(i + (self.frame % 4), H - 1)

    def art(self, g, el):
        for c in range(BCOLS):
            if (c + el // 300) % 3:
                g.fill_rect(c * 12, 12, 11, 4)
        x = 40 + int(30 * sin(el / 400))
        y = 30 - int(abs(12 * sin(el / 300)))
        g.icon2(PHONE_BIG, x - 4, y - 6, 1, 1)
        g.fill_rect(x - 8, 37, 16, 2)
