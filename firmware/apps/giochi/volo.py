from auri import keys
from auri.gfx import W, H
from apps.giochi.base import Game, PHONE, PHONE_BIG, TOP, sin

PX = 16
WALL_W = 6


class Volo(Game):
    key = 'volo'

    def setup(self):
        self.y = 24.0
        self.vy = 0.0
        self.walls = []   # [x, gap_top, gap_h, broken_from, broken_to, passed, batt]
        self.dist = 0
        self.speed = 1.5

    def control(self, k):
        if k in (keys.NAVI, keys.UP, '2', '5', '8', keys.DOWN, '4', '6'):
            self.vy = -2.4
            self.beep(900 + self.r(200), 12)
            self.sparks.append([PX, self.y + 8, -0.5, 0.8, 3])

    def update(self):
        self.vy = min(3.0, self.vy + 0.32)
        self.y += self.vy
        if self.y < TOP:
            self.y, self.vy = TOP, 0.5
        if self.y > H - 8:
            # the floor cannot hurt a 3310: it just bounces back
            self.y, self.vy = H - 8, -2.8
            self.burst(PX + 2, H - 1, 4, 2)
            self.beep(300, 15)
        self.dist += 1
        self.speed = min(3.2, 1.5 + self.dist / 500)
        if not self.walls or self.walls[-1][0] < W - 30:
            gap = max(11, 17 - self.dist // 250)
            gt = TOP + 2 + self.r(H - TOP - gap - 4)
            self.walls.append([W + 2.0, gt, gap, 0, 0, False, self.r(8) == 0])
        y = int(self.y)
        for w in self.walls:
            w[0] -= self.speed
            x = int(w[0])
            if not w[5] and x + WALL_W < PX:
                w[5] = True
                self.add(1)
                self.beep(1600, 20)
            if w[6] and x <= PX + 4 and x + WALL_W >= PX and w[1] <= y + 4 <= w[1] + w[2]:
                w[6] = False
                self.charge(PX, y - 8)
            if x <= PX + 4 and x + WALL_W >= PX and not (w[1] <= y and y + 8 <= w[1] + w[2]):
                lo, hi = y - 2, y + 10
                if w[4]:
                    w[3], w[4] = min(w[3], lo), max(w[4], hi)
                else:
                    # crash: smash a hole in the wall instead of stopping (one hit per wall)
                    w[3], w[4] = lo, hi
                    self.vy = -1.0
                    if not self.hurt(x, y + 4):
                        return
                    self.sys.play('c4:32 g3:32', 240)
        self.walls = [w for w in self.walls if w[0] > -WALL_W - 2]

    def render(self, g):
        for i in range(0, W, 6):
            g.pixel((i - self.dist) % W, H - 1)
        for w in self.walls:
            x, gt, gh = int(w[0]), w[1], w[2]
            for (a, b) in ((TOP, gt), (gt + gh, H)):
                if b <= a:
                    continue
                g.fill_rect(x, a, WALL_W, b - a)
                g.dither(x + 1, a + 1, WALL_W - 2, b - a - 2, 1)
                for yy in range(a + 3, b, 5):
                    g.hline(x, yy, WALL_W, 0)
            if w[4]:
                g.fill_rect(x, max(TOP, w[3]), WALL_W, w[4] - max(TOP, w[3]), 0)
                for yy in range(max(TOP, w[3]), w[4], 3):
                    g.pixel(x + (yy % 2), yy)
                    g.pixel(x + WALL_W - 1 - (yy % 2), yy)
            if w[6]:
                by = gt + gh // 2 - 2
                g.rect(x + 1, by, 4, 6)
                g.hline(x + 2, by - 1, 2)
                if (self.frame // 3) % 2:
                    g.fill_rect(x + 2, by + 2, 2, 3)
        g.icon(PHONE, PX, int(self.y))
        if self.vy < 0:
            g.pixel(PX - 2, int(self.y) + 2)
            g.pixel(PX - 3, int(self.y) + 5)

    def art(self, g, el):
        x = (el // 30) % (W + 30) - 20
        y = 22 + int(8 * sin(el / 250))
        for k in range(3):
            wx = (60 + k * 30 - el // 25) % (W + 10) - 5
            g.fill_rect(wx, 12, 5, 8)
            g.fill_rect(wx, 30, 5, 8)
        g.icon2(PHONE_BIG, x, y - 6, 1, 1)
        g.pixel(x - 2, y)
        g.pixel(x - 4, y + 3)
