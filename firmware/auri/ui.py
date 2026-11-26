from auri import keys
from auri.gfx import W, H, wrap
from auri.i18n import t

ROW = 8
VISIBLE = 4


class App:
    title = ''

    def __init__(self, sys):
        self.sys = sys

    def on_key(self, k):
        if k == keys.C:
            self.sys.pop()

    def on_long(self, k):
        if k == keys.C:
            self.sys.home()

    def tick(self, now):
        return False

    def draw(self, g):
        pass


def header(g, title):
    # Title on the left as on the 3310; underneath a solid rule under the title fading into dots.
    title = title[:13]
    end = len(title) * 6 + 3
    g.text(title, 2, 0)
    g.hline(0, 9, end)
    g.pixel(end + 1, 9)
    for x in range(end + 4, W, 2):
        g.pixel(x, 9)


def softkey(g, label):
    # Centred label as on the 3310, framed by two short tapered rules.
    if not label:
        return
    w = len(label) * 6 - 1
    x0 = (W - w) // 2
    g.text(label, x0, H - 8)
    g.hline(max(0, x0 - 9), H - 4, 5)
    g.hline(x0 + w + 4, H - 4, 5)
    g.pixel(max(0, x0 - 11), H - 4)
    g.pixel(x0 + w + 10, H - 4)


class Menu(App):
    def __init__(self, sys, title, items):
        super().__init__(sys)
        self.soft = t('select')
        self.title = title
        self.items = items
        self.sel = 0
        self.top = 0

    def on_key(self, k):
        n = len(self.items)
        if k == keys.UP:
            self.sel = (self.sel - 1) % n
        elif k == keys.DOWN:
            self.sel = (self.sel + 1) % n
        elif k == keys.NAVI:
            self.items[self.sel][1]()
        elif k in keys.DIGITS and (int(k) or 10) <= n:
            self.sel = (int(k) or 10) - 1          # 0 = la decima voce, come sulla tastiera
            self.items[self.sel][1]()
        else:
            super().on_key(k)
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + VISIBLE - 1:
            self.top = self.sel - VISIBLE + 2

    def tick(self, now):
        target = 11 + (self.sel - self.top) * 10
        moving = getattr(self, 'hy', target) != target
        long_label = len(self.items[self.sel][0]) > 13
        return moving or long_label

    def draw(self, g):
        header(g, self.title)
        now = self.sys.hal.ticks_ms()
        # the highlight glides towards the selected row instead of jumping
        target = 11 + (self.sel - self.top) * 10
        hy = getattr(self, 'hy', target)
        hy = target if abs(target - hy) <= 1 else hy + (target - hy) // 2
        self.hy = hy
        g.round_fill(0, hy - 1, W - 4, 10, 1)
        g.dither(1, hy + 9, W - 5, 1, 1)
        for i in range(VISIBLE - 1):
            j = self.top + i
            if j >= len(self.items):
                break
            y = 11 + i * 10
            label = self.items[j][0]
            inv = abs(y - hy) < 5
            if j == self.sel and len(label) > 13:
                # marquee for labels longer than the screen
                span = len(label) - 13
                k = (now // 300) % (span + 6)
                label = label[max(0, min(span, k - 3)):]
            g.text(label[:13], 2, y, 0 if inv else 1)
        n = len(self.items)
        if n > VISIBLE - 1:
            for yy in range(11, 39, 2):
                g.pixel(W - 2, yy)
            h = max(5, 28 * (VISIBLE - 1) // n)
            y = 11 + (28 - h) * self.sel // max(1, n - 1)
            g.fill_rect(W - 3, y, 3, h)
            g.pixel(W - 3, y, 0)
            g.pixel(W - 3, y + h - 1, 0)
        softkey(g, self.soft)


class IconMenu(App):
    """3310-style main menu: one entry per page with a big icon, sliding sideways, page dots at the bottom."""

    SLIDE_MS = 160

    def __init__(self, sys, items):
        super().__init__(sys)
        self.items = items  # (title, icon rows, action)
        self.sel = 0
        self.prev = 0
        self.t0 = -10000
        self.dir = 1

    def _go(self, d):
        self.prev = self.sel
        self.sel = (self.sel + d) % len(self.items)
        self.dir = d
        self.t0 = self.sys.hal.ticks_ms()

    def on_key(self, k):
        if k == keys.DOWN:
            self._go(1)
        elif k == keys.UP:
            self._go(-1)
        elif k == keys.NAVI:
            self.items[self.sel][2]()
        elif k in keys.DIGITS and k != '0' and int(k) <= len(self.items):
            self.sel = int(k) - 1
            self.items[self.sel][2]()
        else:
            super().on_key(k)

    def tick(self, now):
        return now - self.t0 < self.SLIDE_MS + 40

    def _page(self, g, i, dx):
        title, ico, _ = self.items[i]
        g.text(title[:12], 2 + dx, 0)
        if callable(ico):
            ico(g, dx, 11)   # full-width scene, 84x25
        else:
            g.icon2(ico, (W - 24) // 2 + dx, 11)

    def draw(self, g):
        p = min(1, (self.sys.hal.ticks_ms() - self.t0) / self.SLIDE_MS)
        p = 1 - (1 - p) * (1 - p)
        off = int((1 - p) * W) * self.dir
        if p < 1:
            self._page(g, self.prev, -W * self.dir + off)
        self._page(g, self.sel, off)
        num = '%d' % (self.sel + 1)
        g.fill_rect(W - 6 * len(num) - 2, 0, 6 * len(num) + 2, 8, 0)
        g.text(num, W - 6 * len(num), 0)
        for x in range(0, W, 2):
            g.pixel(x, 9)
        n = len(self.items)
        x0 = (W - n * 4) // 2
        for i in range(n):
            if i == self.sel:
                g.fill_rect(x0 + i * 4, 37, 3, 3)
            else:
                g.pixel(x0 + i * 4 + 1, 38)
        softkey(g, self.soft if hasattr(self, 'soft') else t('select'))


class TextView(App):
    def __init__(self, sys, title, text, soft=None):
        super().__init__(sys)
        self.title = title
        self.lines = wrap(text)
        self.pos = 0
        self.soft = soft or t('back')

    def on_key(self, k):
        if k == keys.UP:
            self.pos = max(0, self.pos - 1)
        elif k == keys.DOWN:
            self.pos = min(max(0, len(self.lines) - 3), self.pos + 1)
        elif k in (keys.NAVI, keys.C):
            self.sys.pop()

    def draw(self, g):
        header(g, self.title)
        for i, line in enumerate(self.lines[self.pos:self.pos + 3]):
            g.text(line, 0, 11 + i * 9)
        if len(self.lines) > 3:
            g.vline(W - 1, 11 + 27 * self.pos // len(self.lines), max(4, 27 * 3 // len(self.lines)))
        softkey(g, self.soft)


class Confirm(App):
    # Navi confirms, C cancels: the 3310 has no green/red call keys.
    def __init__(self, sys, text, on_done):
        super().__init__(sys)
        self.lines = wrap(text)
        self.on_done = on_done

    def on_key(self, k):
        if k == keys.NAVI:
            self.sys.pop()
            self.on_done(True)
        elif k == keys.C:
            self.sys.pop()
            self.on_done(False)

    def draw(self, g):
        header(g, t('confirm_q'))
        for i, line in enumerate(self.lines[:3]):
            g.text(line, 0, 11 + i * 9)
        g.round_fill(0, H - 9, 22, 9, 1)
        g.text('OK', 5, H - 8, 0)
        no = 'C ' + t('no')
        x = W - len(no) * 6 - 5
        g.panel(x, H - 9, len(no) * 6 + 4, 9)
        g.text(no, x + 2, H - 8)


def snake_load(g, now, cy=24, label=None):
    """Caricamento in stile 3310: uno snake a blocchi che gira intorno a un riquadro e cerca la mela.
    Non blocca niente: basta ridisegnarlo a ogni giro (tick che ritorna True)."""
    x0, y0, w, h = 22, cy - 8, 40, 14          # percorso (perimetro del riquadro), passo di 3 px
    per = []
    for x in range(0, w, 3):
        per.append((x0 + x, y0))
    for y in range(0, h, 3):
        per.append((x0 + w, y0 + y))
    for x in range(w, 0, -3):
        per.append((x0 + x, y0 + h))
    for y in range(h, 0, -3):
        per.append((x0, y0 + y))
    n = len(per)
    head = (now // 70) % n
    for i in range(7):                      # 7 blocchi, la testa e' piena e un po' piu' grande
        x, y = per[(head - i) % n]
        if i == 0:
            g.fill_rect(x - 1, y - 1, 4, 4)
            g.pixel(x + 1, y, 0)            # occhio
        else:
            g.fill_rect(x, y, 2, 2)
    ax, ay = per[(head + n // 2) % n]       # la mela, sempre davanti
    g.pixel(ax, ay)
    g.pixel(ax + 1, ay + 1)
    g.pixel(ax - 1, ay + 1)
    g.pixel(ax, ay + 2)
    if label:
        g.text_center(label, cy + 10)


def onoff(v):
    """'si'/'no' tradotto: usato da tutti i menu di impostazioni."""
    return t('on') if v else t('off')


# Wi-Fi a ventaglio: punto + 3 archi (dal piccolo al grande). Archi accesi = segnale, spenti = tratteggiati.
_WIFI = ((('....#....',), 0),
         (('...###...', '..#...#..'), 4),
         (('..#####..', '.#.....#.'), 2),
         (('.#######.', '#.......#'), 0))


def _wifi(g, livello):
    # livello 0..4 (4 = pieno), -1 = Wi-Fi spento (solo una crocetta piccola)
    if livello < 0:
        g.icon(('#.#', '.#.', '#.#'), 3, 3)
        return
    for k, (righe, y) in enumerate(_WIFI):
        if k == 0:
            g.icon(righe, 0, 6)
        elif k < livello:
            g.icon(righe, 0, y)
        else:
            for dy, r in enumerate(righe):
                for x, ch in enumerate(r):
                    if ch == '#' and x % 2 == 0:
                        g.pixel(x, y + dy)


def stato(g, sys, f=0):
    """Barra di stato in alto (rete, Bluetooth, posizione, batteria): uguale in Home e nell'assistente,
    cosi' le icone non spariscono mai. f = fotogramma per l'animazione della carica."""
    hal = sys.hal
    st = sys.settings
    rssi = 0 if st['aereo'] or not st['wifi'] else hal.wifi_level()
    if st['aereo']:
        g.icon(('..#..', '..#..', '.###.', '#####', '..#..', '..#..', '.###.'), 2, 1)
    if not st['aereo']:
        _wifi(g, rssi if st['wifi'] else -1)
    if st['bt'] and not st['aereo']:
        g.icon(('.#.', '.##', '##.', '.#.', '##.', '.##', '.#.'), 14, 1)
    if st['gps'] and not st['aereo']:
        g.icon(('.#.', '#.#', '#.#', '.#.', '.#.'), 19, 2)
    pct, chg = sys.battery
    g.rect(W - 13, 1, 11, 7)
    g.vline(W - 2, 3, 3)
    fill = pct * 9 // 100
    if chg and pct < 100:
        fill = max(fill, (f % 4) * 3)
    g.fill_rect(W - 12, 2, fill, 5)
