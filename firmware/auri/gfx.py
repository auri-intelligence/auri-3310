from auri import font

W = 84
H = 48


class Canvas:
    # Buffer layout matches PCD8544 RAM: 6 banks of 84 bytes, bit 0 = top pixel of the bank.
    def __init__(self):
        self.buf = bytearray(W * H // 8)

    def clear(self):
        for i in range(len(self.buf)):
            self.buf[i] = 0

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
        if o < 32 or o > 126:
            o = 63
        base = (o - 32) * font.W
        for col in range(font.W):
            bits = font.FONT[base + col]
            for row in range(font.H):
                if bits & (1 << row):
                    if s == 1:
                        self.pixel(x + col, y + row, c)
                    else:
                        self.fill_rect(x + col * s, y + row * s, s, s, c)

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
