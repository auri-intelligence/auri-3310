from auri import keys
from auri.ui import App
from auri.gfx import W, H
from auri.i18n import t

STEP = 50
TOP = 9
PHONE = ('.###.', '#...#', '#...#', '#####', '#.#.#', '#####', '#.#.#', '.###.')
# 2x version for intros
PHONE_BIG = ('..#####..', '.#######.', '##.....##', '##.....##', '##.....##', '##.....##', '#########',
             '#.##.##.#', '#########', '#.#.#.#.#', '#########', '#.#.#.#.#', '.#######.')


class Game(App):
    key = 'gioco'
    ENERGY = 3
    ROLL = True       # with an empty battery the 3310 still survives 9 impacts out of 10
    HUD = True

    def __init__(self, sys):
        super().__init__(sys)
        d = sys.hal.load('g_' + self.key, None) or {}
        self.best = d.get('best', 0)
        self.top10 = d.get('top', [])
        self.state = 'intro'
        self.t0 = sys.hal.ticks_ms()
        self.r = sys.hal.random
        self.reset()

    # --- to override ---
    def setup(self):
        pass

    def update(self):
        pass

    def render(self, g):
        pass

    def art(self, g, el):
        pass

    def control(self, k):
        pass

    def release(self, k):
        pass

    def held(self, k):
        pass

    # --- common ---
    def reset(self):
        self.score = 0
        self.shown = 0
        self.energy = self.ENERGY
        self.sparks = []
        self.pops = []
        self.shake = 0
        self.flash = 0
        self.frame = 0
        self.newbest = False
        self.last = self.sys.hal.ticks_ms()
        self.setup()

    def vol(self):
        return self.sys.settings['volume']

    def beep(self, f, ms=25):
        if self.vol():
            self.sys.hal.beep(f, ms, self.vol())

    def burst(self, x, y, n=8, up=0):
        for _ in range(n):
            self.sparks.append([x, y, (self.r(9) - 4) / 3, (self.r(9) - 5 - up) / 3, 5 + self.r(5)])
        if len(self.sparks) > 40:
            del self.sparks[:len(self.sparks) - 40]

    def pop(self, x, y, txt):
        self.pops.append([x, y, txt, 12])

    def add(self, n, x=None, y=None):
        self.score += n
        if x is not None:
            self.pop(x, y, '+%d' % n)

    def charge(self, x, y):
        if self.energy < 5:
            self.energy += 1
        self.pop(x, y, '+' + t('g_batt'))
        self.sys.play('c6:32 e6:32 g6:32 c7:16', 200)

    def hurt(self, x, y, roll=None):
        # True if the 3310 held: first the battery takes the blow, then luck does most of the time
        self.burst(x, y, 12)
        self.shake = 4
        if self.energy > 0:
            self.energy -= 1
            self.flash = 1
            self.sys.vibrate(60)
            self.beep(220, 40)
            self.pop(x, y, 'TOC!')
            return True
        if (self.ROLL if roll is None else roll) and self.r(10) < 9:
            self.flash = 2
            self.sys.vibrate(120)
            self.sys.play('g4:32 c5:32 g5:16', 220)
            self.pops.append([W // 2 - 6 * len(t('g_tough')) // 2, 20, t('g_tough'), 16])
            return True
        self.lose()
        return False

    def lose(self):
        self.state = 'dying'
        self.t0 = self.sys.hal.ticks_ms()
        self.flash = 3
        self.shake = 8
        self.sys.vibrate(300)
        self.sys.play('c6:16 g5:16 e5:16 c5:4', 200)
        self.sys.track('giochi/%s' % self.key)
        if self.score > self.best:
            self.best = self.score
            self.newbest = True
        if self.score > 0:
            from apps.giochi.classifica import player_name
            self.top10.append([self.score, player_name(self.sys) or t('g_you')])
            self.top10.sort(key=lambda e: -e[0])
            del self.top10[10:]
        self.sys.hal.save('g_' + self.key, {'best': self.best, 'top': self.top10})

    def on_key(self, k):
        if self.state == 'intro':
            if k == keys.C:
                self.sys.pop()
            else:
                self.state = 'play'
                self.last = self.sys.hal.ticks_ms()
                self.sys.play('c6:32 g6:32 c7:16', 220)
            return
        if self.state == 'over':
            if k in (keys.NAVI, '5'):
                self.reset()
                self.state = 'play'
            elif k in (keys.DOWN, '8'):
                from apps.giochi.classifica import Classifica
                self.sys.push(Classifica(self.sys, self.key, self.score))
            elif k == keys.C:
                self.sys.pop()
            return
        if self.state == 'dying':
            return
        if k == keys.C:
            self.sys.pop()
        else:
            self.control(k)

    def on_up(self, k):
        if self.state == 'play':
            self.release(k)

    def on_long(self, k):
        if k == keys.C:
            self.sys.pop()
        elif self.state == 'play':
            self.held(k)

    def tick(self, now):
        if self.state == 'intro':
            return True
        if self.state == 'dying':
            self._fx()
            if now - self.t0 > 1000:
                self.state = 'over'
                self.t0 = now
                if self.score > 0 and self.sys.config.get('scores_url'):
                    from apps.giochi.classifica import Classifica
                    self.sys.push(Classifica(self.sys, self.key, self.score))
            return True
        if self.state == 'over':
            return True
        n = 0
        while now - self.last >= STEP and n < 4:
            self.last += STEP
            n += 1
            self.frame += 1
            self.update()
            self._fx()
            if self.state != 'play':
                break
        if now - self.last >= STEP:
            self.last = now
        return n > 0

    def _fx(self):
        s = []
        for p in self.sparks:
            if p[4] > 0:
                p[0] += p[2]
                p[1] += p[3]
                p[3] += 0.2
                p[4] -= 1
                s.append(p)
        self.sparks = s
        for p in self.pops:
            p[1] -= 0.5
            p[3] -= 1
        self.pops = [p for p in self.pops if p[3] > 0]
        if self.shake:
            self.shake -= 1
        if self.flash:
            self.flash -= 1

    def hud(self, g):
        g.text('%d' % self.score, 0, 0)
        # energy as phone battery bars
        x = W - 17
        g.rect(x, 1, 15, 6)
        g.vline(x - 1, 3, 2)
        for i in range(5):
            if i < self.energy:
                g.fill_rect(x + 12 - i * 3 - 1, 2, 2, 4)
        g.hline(0, 8, W)

    def draw(self, g):
        now = self.sys.hal.ticks_ms()
        if self.state == 'intro':
            el = now - self.t0
            self.art(g, el)
            name = t('g_' + self.key)
            g.panel(0, 0, len(name) * 6 + 4, 10)
            g.text(name, 2, 1)
            if (el // 500) % 2:
                g.text_center(t('g_h_' + self.key), 40)
            else:
                g.text_center('%s %d' % (t('record'), self.best), 40)
            return
        if self.state == 'over':
            if self.shown < self.score:
                self.shown += max(1, (self.score - self.shown) // 6)
            g.text_center(t('game_over'), 0)
            g.text_center('%d' % self.shown, 10, 1, 2)
            if self.newbest and (now // 300) % 2:
                g.round_fill(0, 27, W, 10)
                g.text_center(t('new_record'), 28, 0)
            else:
                g.text_center('%s %d' % (t('record'), self.best), 28)
            g.text_center(t('again') if (now // 1500) % 2 == 0 else t('g_rank_hint'), 40)
            return
        self.render(g)
        if self.HUD:
            g.fill_rect(0, 0, W, 8, 0)
            self.hud(g)
        for x, y, _vx, _vy, _l in self.sparks:
            g.pixel(int(x), int(y), 2)
        for x, y, txt, _l in self.pops:
            x = max(0, min(W - 6 * len(txt), int(x) - 3 * len(txt)))
            g.fill_rect(x - 1, int(y) - 1, 6 * len(txt) + 1, 9, 0)
            g.text(txt, x, int(y))
        if self.shake:
            _shift(g.buf, 2 if self.shake % 2 else -2)
        if self.flash and self.flash % 2:
            b = g.buf
            for i in range(W, len(b)):
                b[i] ^= 0xFF


def _shift(b, d):
    for bank in range(6):
        o = bank * W
        row = b[o:o + W]
        if d > 0:
            b[o:o + W] = bytes(d) + row[:W - d]
        else:
            b[o:o + W] = row[-d:] + bytes(-d)


def sin(x):
    x = x % 6.2832
    if x > 3.1416:
        return -sin(x - 3.1416)
    return 4 * x * (3.1416 - x) / (49.348 - x * (3.1416 - x))
