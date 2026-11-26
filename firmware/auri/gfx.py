from auri import font

W = 84
H = 48


_ZERO = bytes(W * H // 8)


class Canvas:
    # Buffer layout matches PCD8544 RAM: 6 banks of 84 bytes, bit 0 = top pixel of the bank.
    def __init__(self):
        self.buf = bytearray(W * H // 8)

    def clear(self):
        self.buf[:] = _ZERO

    def pixel(self, x, y, c=1):
        if 0 <= x < W and 0 <= y < H:
            i = (y >> 3) * W + x
            m = 1 << (y & 7)
            if c == 2:
                self.buf[i] ^= m
            elif c:
                self.buf[i] |= m
            else:
                self.buf[i] &= ~m & 0xFF

    def get(self, x, y):
        return (self.buf[(y >> 3) * W + x] >> (y & 7)) & 1

    def hline(self, x, y, w, c=1):
        for i in range(w):
            self.pixel(x + i, y, c)

    def vline(self, x, y, h, c=1):
        for i in range(h):
            self.pixel(x, y + i, c)

    def rect(self, x, y, w, h, c=1):
        self.hline(x, y, w, c)
        self.hline(x, y + h - 1, w, c)
        self.vline(x, y, h, c)
        self.vline(x + w - 1, y, h, c)

    def fill_rect(self, x, y, w, h, c=1):
        for j in range(h):
            self.hline(x, y + j, w, c)

    def char(self, ch, x, y, c=1, s=1):
        o = ord(ch)
        if o == 0xB7:
            self.fill_rect(x + 2 * s, y + 3 * s, s, s, c)
            return
        if o > 126:
            o = ord(FOLD.get(ch, '?'))
        elif o < 32:
            o = 63
        base = (o - 32) * font.W
        if s == 2:
            self._char2x(base, x, y, c)
            return
        for col in range(font.W):
            bits = font.FONT[base + col]
            for row in range(font.H):
                if bits & (1 << row):
                    if s == 1:
                        self.pixel(x + col, y + row, c)
                    else:
                        self.fill_rect(x + col * s, y + row * s, s, s, c)

    def _char2x(self, base, x, y, c):
        # Scale2x: doubles the glyph but rounds diagonal steps, so big digits look smooth instead of blocky.
        F = font.FONT

        def px(i, j):
            if 0 <= i < font.W and 0 <= j < font.H:
                return (F[base + i] >> j) & 1
            return 0
        for i in range(font.W):
            for j in range(font.H):
                p = px(i, j)
                a, b, d, e = px(i, j - 1), px(i + 1, j), px(i - 1, j), px(i, j + 1)
                if b != d and a != e:
                    q = (d if a == d else p, b if a == b else p, d if d == e else p, b if e == b else p)
                else:
                    q = (p, p, p, p)
                for k in range(4):
                    if q[k]:
                        self.pixel(x + i * 2 + (k & 1), y + j * 2 + (k >> 1), c)

    def round_fill(self, x, y, w, h, c=1):
        self.fill_rect(x, y, w, h, c)
        bg = 0 if c else 1
        for cx, cy in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
            self.pixel(cx, cy, bg)

    def text(self, s, x, y, c=1, scale=1):
        for ch in s:
            self.char(ch, x, y, c, scale)
            x += font.ADV * scale
        return x

    def text_center(self, s, y, c=1, scale=1):
        self.text(s, (W - text_width(s, scale)) // 2, y, c, scale)

    def icon(self, rows, x, y, c=1):
        # rows: list of strings, '#' = pixel on
        for j, r in enumerate(rows):
            for i, ch in enumerate(r):
                if ch == '#':
                    self.pixel(x + i, y + j, c)


    def dither(self, x, y, w, h, level=2):
        # fake grey on a 1-bit LCD: 1 = 25%, 2 = 50%, 3 = 75% of the pixels on
        # cicli a passo 2: si toccano solo i pixel accesi, niente controlli pixel per pixel
        pix = self.pixel
        if level == 3:
            for py in range(y, y + h):
                if py & 1:
                    self.hline(x, py, w)
                else:
                    for px in range(x + 1 - (x & 1), x + w, 2):
                        pix(px, py)
            return
        for py in range(y, y + h):
            if level == 1 and py & 1:
                continue
            start = x + ((x + py) & 1) if level == 2 else x + (x & 1)
            for px in range(start, x + w, 2):
                pix(px, py)

    def panel(self, x, y, w, h):
        # rounded box with a dithered drop shadow: the "modern" container of popups
        self.dither(x + 2, y + h, w - 1, 1, 2)
        self.dither(x + w, y + 2, 1, h - 1, 2)
        self.fill_rect(x, y, w, h, 0)
        self.hline(x + 1, y, w - 2)
        self.hline(x + 1, y + h - 1, w - 2)
        self.vline(x, y + 1, h - 2)
        self.vline(x + w - 1, y + 1, h - 2)

    def blit(self, src, y0, y1):
        # copy rows y0..y1-1 from another canvas (used to clip rolling digits)
        for y in range(y0, y1):
            for x in range(W):
                self.pixel(x, y, src.get(x, y))

    def icon2(self, rows, x, y, c=1, s=2):
        # pixel art scaled up, clipped by pixel() at the screen edges (used while sliding)
        for j, r in enumerate(rows):
            for i, ch in enumerate(r):
                if ch == '#':
                    self.fill_rect(x + i * s, y + j * s, s, s, c)

    def logo(self, x, y, c=1):
        # "AurI": full-size A and I, a smaller "ur" sitting on the same baseline.
        self.char('A', x, y, c)
        self.icon(('#.#', '#.#', '#.#', '.##'), x + 6, y + 3, c)
        self.icon(('#.##', '##..', '#...', '#...'), x + 10, y + 3, c)
        self.char('I', x + 13, y, c)

    def logo_center(self, y, c=1):
        self.logo((W - 18) // 2, y, c)


# Accented letters fold to their base letter: the 5x8 font is ASCII only.
FOLD = {}
for _base, _acc in (('a', 'àáâãäå'), ('e', 'èéêë'), ('i', 'ìíîï'), ('o', 'òóôõö'), ('u', 'ùúûü'),
                    ('A', 'ÀÁÂÃÄÅ'), ('E', 'ÈÉÊË'), ('I', 'ÌÍÎÏ'), ('O', 'ÒÓÔÕÖ'), ('U', 'ÙÚÛÜ'),
                    ('c', 'ç'), ('C', 'Ç'), ('n', 'ñ'), ('N', 'Ñ'), ('s', 'ß'), ("'", '’‘'), ('"', '“”'),
                    ('-', '–—'), ('o', '°')):
    for _ch in _acc:
        FOLD[_ch] = _base


def text_width(s, scale=1):
    return (len(s) * font.ADV - 1) * scale if s else 0


def wrap(text, cols=14):
    lines = []
    for para in text.split('\n'):
        line = ''
        for word in para.split(' '):
            while len(word) > cols:
                if line:
                    lines.append(line)
                    line = ''
                lines.append(word[:cols])
                word = word[cols:]
            if not line:
                line = word
            elif len(line) + 1 + len(word) <= cols:
                line += ' ' + word
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


# --- framebuf (MicroPython, scritto in C): stesso formato del display (MONO_VLSB), quindi le
# operazioni piu' usate passano a lui. Sul PC (CPython) non c'e' e resta il disegno in Python.
try:
    import framebuf as _fb
except ImportError:
    _fb = None

if _fb is not None:
    _GLYPHS = {}
    _PAL0 = _fb.FrameBuffer(bytearray(1), 2, 1, _fb.MONO_HLSB)   # colore 1 -> 0 (testo "spento")
    _PAL0.pixel(0, 0, 1)
    _PAL0.pixel(1, 0, 0)
    _py_init = Canvas.__init__
    _py_pixel = Canvas.pixel
    _py_char = Canvas.char

    def _init(self):
        _py_init(self)
        self.fb = _fb.FrameBuffer(self.buf, W, H, _fb.MONO_VLSB)

    def _pixel(self, x, y, c=1):
        if c == 2:
            _py_pixel(self, x, y, 2)
        elif 0 <= x < W and 0 <= y < H:
            self.fb.pixel(x, y, 1 if c else 0)

    def _hline(self, x, y, w, c=1):
        if c == 2:
            for i in range(w):
                _py_pixel(self, x + i, y, 2)
        else:
            self.fb.hline(x, y, w, 1 if c else 0)

    def _vline(self, x, y, h, c=1):
        if c == 2:
            for i in range(h):
                _py_pixel(self, x, y + i, 2)
        else:
            self.fb.vline(x, y, h, 1 if c else 0)

    def _fill_rect(self, x, y, w, h, c=1):
        if c == 2:
            for j in range(h):
                _hline(self, x, y + j, w, 2)
        else:
            self.fb.fill_rect(x, y, w, h, 1 if c else 0)

    def _char(self, ch, x, y, c=1, s=1):
        if s != 1 or c == 2:
            return _py_char(self, ch, x, y, c, s)
        o = ord(ch)
        if o == 0xB7:
            return _py_char(self, ch, x, y, c, s)
        if o > 126:
            o = ord(FOLD.get(ch, '?'))
        elif o < 32:
            o = 63
        g = _GLYPHS.get(o)
        if g is None:
            base = (o - 32) * font.W
            g = _GLYPHS[o] = _fb.FrameBuffer(bytearray(font.FONT[base:base + font.W]), font.W, 8, _fb.MONO_VLSB)
        if c:
            self.fb.blit(g, x, y, 0)
        else:
            self.fb.blit(g, x, y, 0, _PAL0)

    Canvas.__init__ = _init
    Canvas.pixel = _pixel
    Canvas.hline = _hline
    Canvas.vline = _vline
    Canvas.fill_rect = _fill_rect
    Canvas.char = _char
