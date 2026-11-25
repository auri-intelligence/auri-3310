from auri import keys
from auri.ui import App
from auri.gfx import W, H
from auri.i18n import t

# 12x12 original sprites, drawn at 2x
EGG = ('....####....', '...######...', '..##.#####..', '.##########.', '.####.#####.', '############',
       '#####.######', '############', '.##.#######.', '.##########.', '..########..', '....####....')
BABY = ('............', '............', '....####....', '..########..', '.##########.', '.#.##..##.#.',
        '.##########.', '.####..####.', '.##########.', '..########..', '..##....##..', '............')
ADULT = ('...#....#...', '..##....##..', '..########..', '.##########.', '.#.##..##.#.', '############',
         '############', '#####..#####', '.##########.', '.##########.', '..##....##..', '.###....###.')
EYES = {'baby': (5, 4, 7), 'adult': (4, 2, 7)}  # row, left eye x, right eye x (2 px wide holes)
FOOD = ('.#.', '###', '###')
HEART = ('#.#', '###', '.#.')
BOLT = ('.##', '##.', '.#.')
POOP = ('.#.', '###')

ACTIONS = ('pet_feed', 'pet_play', 'pet_sleep', 'pet_clean')


def minutes(tm):
    return ((((tm[0] - 2020) * 12 + tm[1]) * 31 + tm[2]) * 24 + tm[3]) * 60 + tm[4]


class Pet(App):
    def __init__(self, sys):
        super().__init__(sys)
        self.now_min = minutes(sys.hal.localtime())
        self.s = sys.hal.load('pet', None) or self._new()
        self._catch_up()
        self.act = 0
        self.anim = None   # (kind, start ms)
        self.t0 = sys.hal.ticks_ms()
        self.x = 30

    def _new(self):
        return {'stage': 'egg', 'born': self.now_min, 'last': self.now_min,
                'food': 3, 'joy': 3, 'energy': 4, 'poop': 0, 'sleep': False, 'neglect': 0}

    def _save(self):
        self.sys.hal.save('pet', self.s)

    def _catch_up(self):
        # Real time passes even with the phone off: apply every elapsed minute (capped at a week).
        s = self.s
        el = max(0, min(10080, self.now_min - s['last']))
        for m in range(s['last'] + 1, s['last'] + el + 1):
            if s['stage'] in ('egg', 'gone'):
                break
            if m % 15 == 0:
                s['food'] = max(0, s['food'] - 1)
            if m % 20 == 0:
                s['joy'] = max(0, s['joy'] - 1)
            if m % 25 == 0:
                s['energy'] = min(4, s['energy'] + 1) if s['sleep'] else max(0, s['energy'] - 1)
            if m % 45 == 0 and not s['sleep']:
                s['poop'] = min(3, s['poop'] + 1)
            if s['food'] == 0 and s['joy'] == 0:
                s['neglect'] += 1
                if s['neglect'] > 720:
                    s['stage'] = 'gone'
            else:
                s['neglect'] = 0
        age = self.now_min - s['born']
        if s['stage'] == 'egg' and age >= 1:
            s['stage'] = 'hatch'
        if s['stage'] == 'baby' and age >= 1440:
            s['stage'] = 'adult'
        s['last'] = self.now_min
        self._save()

    def on_key(self, k):
        s = self.s
        if s['stage'] == 'gone':
            if k == keys.NAVI:
                self.s = self._new()
                self._save()
            elif k == keys.C:
                self.sys.pop()
            return
        if k in (keys.UP, keys.DOWN):
            self.act = (self.act + (1 if k == keys.DOWN else -1)) % len(ACTIONS)
        elif k in '1234':
            self.act = int(k) - 1
            self._do()
        elif k == keys.NAVI:
            self._do()
        else:
            super().on_key(k)

    def _do(self):
        s = self.s
        if s['stage'] in ('egg', 'hatch') or self.anim:
            return
        a = ACTIONS[self.act]
        if s['sleep'] and a != 'pet_sleep':
            return
        if a == 'pet_feed':
            s['food'] = min(4, s['food'] + 1)
            self.sys.play('c6:16 e6:16', 200)
        elif a == 'pet_play':
            s['joy'] = min(4, s['joy'] + 1)
            s['energy'] = max(0, s['energy'] - 1)
            self.sys.play('e6:16 g6:16 c7:16', 200)
        elif a == 'pet_sleep':
            s['sleep'] = not s['sleep']
        elif a == 'pet_clean':
            s['poop'] = 0
            self.sys.play('g6:32 c7:32', 220)
        self.anim = (a, self.sys.hal.ticks_ms())
        self.sys.track('aurIpet/' + a[4:])
        self._save()

    def tick(self, now):
        m = minutes(self.sys.hal.localtime())
        if m != self.now_min:
            self.now_min = m
            self._catch_up()
        if self.anim and now - self.anim[1] > 1400:
            self.anim = None
        if self.s['stage'] == 'hatch' and now - self.t0 > 2200:
            self.s['stage'] = 'baby'
            self.sys.vibrate(150)
            self.sys.play('c6:16 e6:16 g6:16 c7:8', 180)
            self._save()
        return True

    # --- drawing ---
    def _sprite(self, g, rows, x, y, eyes=None, mood='ok', blink=False):
        g.icon2(rows, x, y)
        if not eyes:
            return
        r, lx, rx = eyes
        for ex in (lx, rx):
            if blink or mood == 'sleep':
                g.fill_rect(x + ex * 2, y + r * 2 + 1, 4, 1, 0)
                g.fill_rect(x + ex * 2, y + r * 2, 4, 1, 1)
            elif mood == 'happy':
                g.pixel(x + ex * 2 + 1, y + r * 2, 0)
                g.pixel(x + ex * 2 + 2, y + r * 2, 0)
        mouth_y = y + (r + 3) * 2
        if mood == 'sad':
            g.hline(x + 10, mouth_y + 1, 4, 0)
        elif mood in ('happy', 'eat'):
            g.fill_rect(x + 10, mouth_y, 4, 2 if mood == 'eat' else 1, 0)

    def _bar(self, g, icon, v, x):
        g.icon(icon, x, 1)
        for i in range(4):
            if i < v:
                g.fill_rect(x + 5 + i * 3, 2, 2, 3)
            else:
                g.pixel(x + 5 + i * 3, 4)

    def draw(self, g):
        s = self.s
        now = self.sys.hal.ticks_ms()
        if s['stage'] == 'gone':
            g.text_center('AurIpet', 0)
            for i, line in enumerate(_wrap(t('pet_gone'))[:3]):
                g.text_center(line, 12 + i * 9)
            return
        self._bar(g, FOOD, s['food'], 0)
        self._bar(g, HEART, s['joy'], 28)
        self._bar(g, BOLT, s['energy'], 56)
        for x in range(0, W, 2):
            g.pixel(x, 8)
        f = now // 400
        if s['stage'] in ('egg', 'hatch'):
            wob = (1 if f % 2 else -1) if s['stage'] == 'hatch' or f % 6 == 0 else 0
            self._sprite(g, EGG, 30 + wob, 12)
            if s['stage'] == 'hatch':
                g.vline(40, 14, 6, 0)
                g.pixel(39, 18, 0)
                g.pixel(41, 16, 0)
            g.text_center(t('pet_egg'), 40)
            return
        rows = BABY if s['stage'] == 'baby' else ADULT
        eyes = EYES[s['stage']]
        a = self.anim[0] if self.anim else None
        el = now - self.anim[1] if self.anim else 0
        mood = 'sleep' if s['sleep'] else 'happy' if a in ('pet_feed', 'pet_play') else \
            'sad' if min(s['food'], s['joy']) <= 1 else 'ok'
        if a == 'pet_feed' and (el // 200) % 2:
            mood = 'eat'
        # idle walk and bounce
        if not s['sleep'] and not a:
            self.x += (1 if (now // 3000) % 2 else -1) if f % 2 else 0
            self.x = max(4, min(W - 28, self.x))
        y = 13 - (3 if a == 'pet_play' and (el // 150) % 2 else 0) - (1 if f % 2 and not s['sleep'] else 0)
        self._sprite(g, rows, self.x, y, eyes, mood, blink=(f % 9 == 0))
        for i in range(s['poop']):
            g.icon(POOP, 70 - i * 6, 34)
            if f % 2:
                g.pixel(71 - i * 6, 31)
        if a == 'pet_feed' and el < 600:
            g.icon2(FOOD, self.x + 30, 12 + el // 40, 1, 2)
        if a in ('pet_feed', 'pet_play'):
            g.icon(HEART, self.x + 24, 12 - el // 120)
        if a == 'pet_play':
            bx = self.x + 30 + (el // 30) % 20
            g.fill_rect(bx, 34 - abs((el // 30) % 12 - 6), 3, 3)
        if a == 'pet_clean':
            g.vline(W - (el * W // 900), 10, 28)
        if s['sleep']:
            z = (now // 500) % 3
            g.text('z', self.x + 26, 12 - z * 2)
            if z > 0:
                g.text('Z', self.x + 30, 8 - z)
        msg = self._need()
        if msg and (now // 1500) % 2 and not a:
            g.text_center(msg, 40)
        else:
            name = t(ACTIONS[self.act])
            g.text_center('< %s >' % name, 40)

    def _need(self):
        s = self.s
        if s['sleep']:
            return None
        if s['food'] <= 1:
            return t('pet_hungry')
        if s['poop'] >= 2:
            return t('pet_dirty')
        if s['energy'] <= 1:
            return t('pet_tired')
        if s['joy'] <= 1:
            return t('pet_bored')
        return None


def _wrap(text):
    from auri.gfx import wrap
    return wrap(text)
