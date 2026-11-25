import math
from auri import keys
from auri.gfx import W, H
from apps.giochi.base import Game, PHONE, PHONE_BIG, sin

GY = H - 2
SX, SY = 8, GY - 10
CB = 5   # crate size


class Catapulta(Game):
    key = 'catapulta'
    ROLL = False

    def setup(self):
        self.level = 0
        self.ang = 45
        self.pow = 60
        self._level()

    def _level(self):
        self.level += 1
        self.shots = 3
        self.ball = None
        self.crates = []
        cols = min(5, 2 + self.level // 2)
        x0 = W - 4 - cols * CB - self.r(10)
        for c in range(cols):
            for h in range(1 + self.r(min(4, 1 + self.level // 2) + 1)):
                self.crates.append([x0 + c * CB, GY - (h + 1) * CB])
        self.wind = 0 if self.level < 3 else (self.r(5) - 2) * 0.01

    def control(self, k):
        if self.ball:
            return
        if k in ('2', keys.UP):
            self.ang = min(80, self.ang + 3)
        elif k in ('8', keys.DOWN):
            self.ang = max(10, self.ang - 3)
        elif k == '6':
            self.pow = min(100, self.pow + 5)
        elif k == '4':
            self.pow = max(20, self.pow - 5)
        elif k in ('5', keys.NAVI):
            self._fire()

    def held(self, k):
        for _ in range(3):
            self.control(k)

    def _v(self):
        a = self.ang * 3.1416 / 180
        v = 1.2 + self.pow * 0.018
        return v * math.cos(a), -v * math.sin(a)

    def _fire(self):
        vx, vy = self._v()
        self.ball = [float(SX), float(SY), vx, vy, 0, 0]   # x, y, vx, vy, bounces, steps
        self.shots -= 1
        self.sys.play('g5:32 c6:32', 240)
        self.sys.vibrate(30)

    def update(self):
        b = self.ball
        if not b:
            return
        for _ in range(2):
            b[0] += b[2]
            b[1] += b[3]
            b[3] += 0.09
            b[2] += self.wind
            b[5] += 1
            hit = None
            for c in self.crates:
                if c[0] - 4 <= b[0] <= c[0] + CB and c[1] - 7 <= b[1] <= c[1] + CB:
                    hit = c
                    break
            if hit:
                # the 3310 goes straight through: the crate breaks, the phone loses a little speed
                self.crates.remove(hit)
                self.add(10 * self.level, hit[0] + 2, hit[1] - 4)
                self.burst(hit[0] + 2, hit[1] + 2, 8)
                self.shake = 2
                self.beep(300 + self.r(200), 25)
                b[2] *= 0.85
                b[3] *= 0.85
                for c in self.crates:
                    if c[0] == hit[0] and c[1] < hit[1]:
                        c[1] += CB
            if b[1] > GY - 8:
                b[1] = GY - 8
                b[3] = -abs(b[3]) * 0.5
                b[2] *= 0.7
                b[4] += 1
                self.burst(int(b[0]) + 2, GY, 3, 2)
                self.beep(200, 15)
        if b[0] > W + 4 or b[0] < -8 or b[4] > 3 or b[5] > 400:
            self.ball = None
            if not self.crates:
                self.add(30 * self.level + 20 * self.shots, W // 2, 20)
                self.sys.play('c6:16 e6:16 g6:16 c7:8', 200)
                self.flash = 2
                self._level()
            elif self.shots == 0:
                # out of shots: a battery bar buys three more
                if self.hurt(W // 2, 20):
                    self.shots = 3

    def render(self, g):
        g.hline(0, GY, W)
        for x in range(0, W, 3):
            g.pixel(x, GY + 1)
        for x, y in self.crates:
            g.rect(x, y, CB, CB)
            g.pixel(x + 2, y + 2)
        g.vline(SX + 2, SY + 8, GY - SY - 8)
        g.icon(('#...#', '.#.#.', '..#..'), SX, SY + 7)
        if not self.ball:
            vx, vy = self._v()
            x, y = SX + 2.0, SY + 4.0
            for i in range(26):
                x += vx
                y += vy
                vy += 0.09
                vx += self.wind
                if i % 3 == 2 and i < 18:
                    g.pixel(int(x), int(y))
            g.icon(PHONE, SX, SY)
        else:
            g.icon(PHONE, int(self.ball[0]), int(self.ball[1]))
        for i in range(self.shots):
            g.fill_rect(i * 4, 10, 3, 3)
        g.text('%d' % self.ang, 0, 14)
        g.hline(0, 23, self.pow // 5)
        if self.wind:
            g.text('>' if self.wind > 0 else '<', 40, 10)

    def art(self, g, el):
        p = (el % 1600) / 1600
        x = 8 + int(60 * p)
        y = 34 - int(22 * sin(p * 3.1416))
        for c in range(3):
            for h in range(2):
                if not (p > 0.9 and c == 1):
                    g.rect(62 + c * 6, 32 - h * 6, 6, 6)
        g.icon2(PHONE_BIG, x - 4, y - 6, 1, 1)
        g.hline(0, 38, W)
