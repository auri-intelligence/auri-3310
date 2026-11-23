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
    # Light header: title on the left, a dotted rule underneath instead of a solid black bar.
    g.text(title[:13], 2, 0)
    for x in range(0, W, 2):
        g.pixel(x, 9)


def softkey(g, label):
    if label:
        g.text_center(label, H - 8)


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
        elif k in keys.DIGITS and k != '0' and int(k) <= n:
            self.sel = int(k) - 1
            self.items[self.sel][1]()
        else:
            super().on_key(k)
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + VISIBLE - 1:
            self.top = self.sel - VISIBLE + 2

    def draw(self, g):
        header(g, self.title)
        for i in range(VISIBLE - 1):
            j = self.top + i
            if j >= len(self.items):
                break
            y = 11 + i * 10
            sel = j == self.sel
            if sel:
                g.round_fill(0, y - 1, W - 3, 10, 1)
            g.text(self.items[j][0][:13], 2, y, 0 if sel else 1)
        if len(self.items) > VISIBLE - 1:
            for yy in range(11, 39, 3):
                g.pixel(W - 1, yy)
            h = max(4, 28 * (VISIBLE - 1) // len(self.items))
            y = 11 + (28 - h) * self.sel // max(1, len(self.items) - 1)
            g.vline(W - 1, y, h)
        softkey(g, self.soft)


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
        g.round_fill(0, H - 9, 20, 9, 1)
        g.text('OK', 4, H - 8, 0)
        no = 'C ' + t('no')
        g.rect(W - len(no) * 6 - 4, H - 9, len(no) * 6 + 4, 9)
        g.text(no, W - len(no) * 6 - 1, H - 8)
