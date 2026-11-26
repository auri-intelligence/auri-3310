from auri import font

W = 84
H = 48


_ZERO = bytes(W * H // 8)
_PUNTI = {}


_P2X = {}


def _punti2x(base):
    p = _P2X.get(base)
    if p is None:
        F = font.FONT

        def px(i, j):
            if 0 <= i < font.W and 0 <= j < font.H:
                return (F[base + i] >> j) & 1
            return 0
        out = []
        for i in range(font.W):
            for j in range(font.H):
                q0 = px(i, j)
                a, b, d, e = px(i, j - 1), px(i + 1, j), px(i - 1, j), px(i, j + 1)
                if b != d and a != e:
                    q = (d if a == d else q0, b if a == b else q0, d if d == e else q0, b if e == b else q0)
                else:
                    q = (q0, q0, q0, q0)
                for k in range(4):
                    if q[k]:
                        out.append((i * 2 + (k & 1), j * 2 + (k >> 1)))
        p = _P2X[base] = tuple(out)
    return p


def _punti(rows):
    k = rows if isinstance(rows, tuple) else id(rows)
    p = _PUNTI.get(k)
    if p is None:
        p = _PUNTI[k] = tuple((i, j) for j, r in enumerate(rows) for i, ch in enumerate(r) if ch == '#')
    return p


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
        # Scale2x calcolato una volta per carattere (prima a ogni fotogramma: era il peso della Home)
        pix = self.pixel
        for i, j in _punti2x(base):
            pix(x + i, y + j, c)

    def _char2x_calcolo(self, base, x, y, c):
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
        # rows: list of strings, '#' = pixel on. Converted once (list of lit pixels), not re-read per frame.
        pts = _punti(rows)
        pix = self.pixel
        for i, j in pts:
            pix(x + i, y + j, c)


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
        # copy rows y0..y1-1 from another canvas (used to clip rolling digits): a byte at a time with a
        # row mask per 8-row bank (prima 1344 chiamate pixel/get a ogni fotogramma della Home)
        y0, y1 = max(0, y0), min(H, y1)
        d, s = self.buf, src.buf
        for bank in range(y0 >> 3, ((y1 - 1) >> 3) + 1):
            lo = max(y0, bank * 8) - bank * 8
            hi = min(y1, bank * 8 + 8) - bank * 8
            m = ((1 << hi) - 1) & ~((1 << lo) - 1) & 0xFF
            nm = ~m & 0xFF
            for i in range(bank * W, bank * W + W):
                d[i] = (d[i] & nm) | (s[i] & m)

    def icon2(self, rows, x, y, c=1, s=2):
        # pixel art scaled up, clipped by pixel() at the screen edges (used while sliding)
        fr = self.fill_rect
        for i, j in _punti(rows):
            fr(x + i * s, y + j * s, s, s, c)

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
            self.fb.blit(g, x, y, 1, _PAL0)   # chiave dopo la palette: 1 = sfondo trasparente

    _ICONE = {}

    def _icon(self, rows, x, y, c=1):
        if c == 2:
            return _py_icon(self, rows, x, y, c)
        k = rows if isinstance(rows, tuple) else id(rows)
        fb = _ICONE.get(k)
        if fb is None:
            w = max(len(r) for r in rows) if rows else 0
            h = len(rows)
            if not w or not h:
                return
            fb = _fb.FrameBuffer(bytearray(((w + 7) // 8) * h), w, h, _fb.MONO_HLSB)
            for i, j in _punti(rows):
                fb.pixel(i, j, 1)
            _ICONE[k] = fb
        if c:
            self.fb.blit(fb, x, y, 0)
        else:
            self.fb.blit(fb, x, y, 1, _PAL0)   # chiave dopo la palette: 1 = sfondo trasparente

    _GRANDI = {}
    _py_c2x = Canvas._char2x

    def _char2x_fb(self, base, x, y, c):
        if c == 2:
            return _py_c2x(self, base, x, y, c)
        fb = _GRANDI.get(base)
        if fb is None:
            fb = _fb.FrameBuffer(bytearray(2 * 16), 10, 16, _fb.MONO_HLSB)
            for i, j in _punti2x(base):
                fb.pixel(i, j, 1)
            _GRANDI[base] = fb
        if c:
            self.fb.blit(fb, x, y, 0)
        else:
            self.fb.blit(fb, x, y, 1, _PAL0)   # chiave dopo la palette: 1 = sfondo trasparente


    _GRANDI2 = {}
    _py_icon2 = Canvas.icon2

    def _icon2(self, rows, x, y, c=1, s=2):
        if c == 2:
            return _py_icon2(self, rows, x, y, c, s)
        k = (rows if isinstance(rows, tuple) else id(rows), s)
        fb = _GRANDI2.get(k)
        if fb is None:
            w = max(len(r) for r in rows) * s
            h = len(rows) * s
            fb = _fb.FrameBuffer(bytearray(((w + 7) // 8) * h), w, h, _fb.MONO_HLSB)
            for i, j in _punti(rows):
                fb.fill_rect(i * s, j * s, s, s, 1)
            _GRANDI2[k] = fb
        if c:
            self.fb.blit(fb, x, y, 0)
        else:
            self.fb.blit(fb, x, y, 1, _PAL0)   # chiave dopo la palette: 1 = sfondo trasparente

    def _blit(self, src, y0, y1):
        # stesse righe y0..y1-1 copiate dall'altra tela, tutto in C: si pulisce fuori zona nella sorgente
        # (e' una tela di lavoro) e dentro zona nella destinazione, poi blit con lo 0 trasparente
        y0, y1 = max(0, y0), min(H, y1)
        if y1 <= y0:
            return
        if y0:
            src.fb.fill_rect(0, 0, W, y0, 0)
        if y1 < H:
            src.fb.fill_rect(0, y1, W, H - y1, 0)
        self.fb.fill_rect(0, y0, W, y1 - y0, 0)
        self.fb.blit(src.fb, 0, 0, 0)

    _py_icon = Canvas.icon

    class _CanvasFB(Canvas):
        """La tela del Nokia (e del browser): le operazioni piu' usate fatte in C da framebuf. I metodi in
        Python di Canvas restano per i casi che framebuf non fa (xor, scale diverse) e per il PC."""
        __init__ = _init
        pixel = _pixel
        hline = _hline
        vline = _vline
        fill_rect = _fill_rect
        char = _char
        _char2x = _char2x_fb
        icon = _icon
        icon2 = _icon2
        blit = _blit

    Canvas = _CanvasFB
