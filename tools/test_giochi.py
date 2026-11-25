"""Test of the AurI games on the PC: python tools/test_giochi.py  (images in tmp/lcd/giochi/)"""
import os
import sys
import time
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, 'firmware')
sys.path.insert(0, FW)
os.chdir(FW)
OUT = os.path.join(ROOT, 'tmp', 'lcd', 'giochi')
os.makedirs(OUT, exist_ok=True)

from hal.pc import PCHal
from auri.core import System
from auri import keys
from apps.home import Home
from apps.giochi import GAMES
from apps.giochi import classifica as cl


class TestHal(PCHal):
    def __init__(self):
        super().__init__((2026, 11, 25, 12, 0, 0, 2, 329))
        self.now = 0
        self.mem = {}
        self.sent = []

    def ticks_ms(self):
        return self.now

    def beep(self, f, ms, vol=3):
        pass

    def load(self, k, d=None):
        return self.mem.get(k, d)

    def save(self, k, v):
        import json
        self.mem[k] = json.loads(json.dumps(v))

    def request(self, method, url, body=None, token=None):
        self.sent.append((method, url, body))
        return {'top': [['ANNA', 120], [body['nome'] if body else 'X', body['punti'] if body else 5]]}


def mk(cfg=None):
    hal = TestHal()
    s = System(hal, cfg or {'bridge_url': ''})
    s.push(Home(s))
    s.step()
    return hal, s


def run(hal, s, ms):
    for _ in range(ms // 20):
        hal.now += 20
        s.step()


def key(hal, s, k, hold=60):
    hal.press(k)
    run(hal, s, hold)
    hal.release(k)
    run(hal, s, 20)


def bot(g, name, hal, s):
    # a crude player per game, enough to score points
    f = g.frame
    if name == 'volo':
        ws = [w for w in g.walls if w[0] + 6 >= 14]
        target = (ws[0][1] + ws[0][2] / 2 - 4) if ws else 24
        if g.y > target and g.vy >= 0:
            return keys.NAVI
    elif name == 'corsie':
        if f % 15 == 0:
            return random.choice(('4', '6', '5'))
    elif name == 'incastro':
        return random.choice(('4', '6', '2', '5', '8')) if f % 4 == 0 else None
    elif name == 'rompimuro':
        if g.stuck:
            return '5'
        hal.release('4'); hal.release('6')
        return '4' if g.bx < g.px + 6 else '6'
    elif name == 'trefila':
        for i in range(len(g.b)):
            for d, j in (('6', i + 1), ('8', i + 7)):
                if j < len(g.b) and (d == '8' or i % 7 < 6):
                    g._swap(i, j); ok = g._matches(); g._swap(i, j)
                    if ok and not g.clear:
                        g.cx, g.cy, g.sel = i % 7, i // 7, True
                        return d
        return None
    elif name == 'salisali':
        p = min(g.plats, key=lambda p: abs(p[1] - g.y - 12) + abs(p[0] + p[2] / 2 - g.x))
        hal.release('4'); hal.release('6')
        return '4' if g.x > p[0] + p[2] / 2 + 2 else '6' if g.x < p[0] + p[2] / 2 - 4 else None
    elif name == 'catapulta':
        if not g.ball and f % 6 == 0:
            g.pow = 40 + random.randrange(45)
            return '5'
    return None


def shot(hal, path):
    hal.save_png(os.path.join(OUT, path), scale=3)


def test_game(mod, cls):
    hal, s = mk()
    random.seed(1)
    m = __import__('apps.giochi.' + mod, None, None, (cls,))
    g = getattr(m, cls)(s)
    s.push(g)
    run(hal, s, 700)
    shot(hal, mod + '_1intro.png')
    key(hal, s, '5')
    assert g.state == 'play', g.state
    for _ in range(1200):
        k = bot(g, mod, hal, s)
        if k:
            hal.press(k)
            if mod not in ('rompimuro', 'salisali'):
                hal.now += 20; s.step()
                hal.release(k)
        hal.now += 20
        s.step()
        if g.state != 'play':
            break
        if _ == 300:
            shot(hal, mod + '_2gioco.png')
    pts = g.score
    assert pts > 0, (mod, 'nessun punto')
    # force a loss: battery empty, then impacts until luck runs out
    ok = 0
    for _ in range(1000):
        g.state, g.energy = 'play', 0
        ok += g.hurt(40, 20)
    held = ok / 10
    g.state, g.energy = 'play', 0
    g.reset(); g.state = 'play'; g.score = g.best + 5
    n = 0
    while g.state == 'play' and n < 200:
        g.hurt(40, 20)
        n += 1
    assert g.state == 'dying', (mod, g.state)
    run(hal, s, 1300)
    run(hal, s, 600)
    shot(hal, mod + '_3fine.png')
    assert g.state == 'over'
    saved = hal.mem['g_' + mod]
    assert saved['best'] == g.score and g.newbest, saved
    key(hal, s, keys.NAVI)
    assert g.state == 'play' and g.score == 0
    # local ranking (no service configured)
    g.lose(); run(hal, s, 1100)
    key(hal, s, '8')
    assert type(s.top).__name__ == 'Classifica'
    run(hal, s, 100)
    shot(hal, mod + '_4classifica.png')
    key(hal, s, keys.C)
    key(hal, s, keys.NAVI)
    # 2000 random steps, timing step + draw
    ks = ['2', '4', '5', '6', '8', keys.UP, keys.DOWN, keys.NAVI, '1', '3', '0']
    tt, deaths = 0.0, 0
    for i in range(2000):
        if random.random() < 0.3:
            hal.press(random.choice(ks))
        if random.random() < 0.3:
            for k in ks:
                hal.release(k)
        if g.state == 'over':
            deaths += 1
            hal.press(keys.NAVI)
        if s.top is not g:
            s.push(g)
        hal.now += 50
        s.dirty = True
        t0 = time.perf_counter()
        s.step()
        tt += time.perf_counter() - t0
    # same, but drawing only when the game asked for it (as on the device)
    return pts, held, deaths, tt / 2000 * 1000


def test_menu_and_snake():
    hal, s = mk()
    key(hal, s, keys.NAVI, 20)
    run(hal, s, 300)
    names = [it[0] for it in s.top.items]
    assert 'Giochi' in names and 'Snake' not in names, names
    s.top.sel = names.index('Giochi')
    key(hal, s, keys.NAVI)
    run(hal, s, 300)
    shot(hal, '0_menu_giochi.png')
    gm = s.top
    assert gm.kind == 'giochi' and gm.items[-1][0] == 'Snake'
    gm.sel = len(gm.items) - 1
    key(hal, s, keys.NAVI)
    assert type(s.top).__name__ == 'Snake'
    key(hal, s, '5')
    run(hal, s, 2000)
    key(hal, s, keys.C)
    for i in range(len(GAMES)):
        assert s.top is gm
        gm.sel = i
        key(hal, s, keys.NAVI)
        assert type(s.top).__name__ == GAMES[i][1]
        key(hal, s, keys.C)


def test_online():
    assert cl.is_bad('Cazz0') and cl.is_bad('FUUCK') and cl.is_bad('5tr0nz0') and cl.is_bad('sh1t') and cl.is_bad('m3rda') and cl.is_bad('@sshole')
    assert not cl.is_bad('Luigi') and not cl.is_bad('Claudio') and not cl.is_bad('Marco')
    assert not cl.valid('ab') and not cl.valid('abcdefghijk') and cl.valid('Pippo')
    hal, s = mk({'bridge_url': '', 'scores_url': 'https://example.invalid/score', 'scores_key': 'k'})
    from apps.giochi.volo import Volo
    g = Volo(s)
    s.push(g)
    key(hal, s, '5')
    g.score = 42
    g.lose()
    run(hal, s, 1100)
    key(hal, s, '8')
    run(hal, s, 60)
    assert type(s.top).__name__ == 'NomeInput'
    for k in '2' * 1:
        key(hal, s, k)
    key(hal, s, keys.NAVI)          # too short
    assert type(s.top).__name__ == 'NomeInput' and s.top.err
    s.top.mt.text = ''
    for k in ('3', '3', '3', '5', '5', '5', '2', '2', '2'):   # "fkc" style: test spelling of a clean name instead
        pass
    s.top.mt.text = 'Merd4'
    key(hal, s, keys.NAVI)
    assert type(s.top).__name__ == 'NomeInput' and s.top.err
    s.top.mt.text = 'LUIGI'
    shot(hal, '5_nome.png')
    key(hal, s, keys.NAVI)
    run(hal, s, 200)
    assert type(s.top).__name__ == 'Classifica' and s.top.world, s.top.msg
    m, u, b = hal.sent[0]
    assert m == 'POST' and b['nome'] == 'LUIGI' and b['punti'] == 42 and b['firma'] == cl.sign('volo', 'LUIGI', 42, 'k')
    shot(hal, '6_mondo.png')


def sheet():
    from PIL import Image
    fs = sorted(f for f in os.listdir(OUT) if f.endswith('.png') and f != 'foglio.png')
    ims = [Image.open(os.path.join(OUT, f)) for f in fs]
    w, h = ims[0].size
    cols = 4
    rows = (len(ims) + cols - 1) // cols
    out = Image.new('RGB', (cols * (w + 6), rows * (h + 6)), (40, 40, 40))
    for i, im in enumerate(ims):
        out.paste(im, ((i % cols) * (w + 6), (i // cols) * (h + 6)))
    out.save(os.path.join(OUT, 'foglio.png'))


if __name__ == '__main__':
    test_menu_and_snake()
    print('menu + snake ok')
    test_online()
    print('classifica online (finta) + filtro ok')
    for mod, cls, _ic in GAMES:
        pts, held, deaths, ms = test_game(mod, cls)
        print('%-10s punti bot %5d | impatti retti a batteria vuota %5.1f%% | partite perse in 2000 passi casuali %d | passo+disegno %.2f ms'
              % (mod, pts, held, deaths, ms))
    sheet()
    print('foglio:', os.path.join(OUT, 'foglio.png'))
