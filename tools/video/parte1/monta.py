import json
import math
import os
import subprocess
import sys
import wave

import numpy as np
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.dirname(HERE))
OUT = os.path.join(HERE, 'out')
W, H, FPS = 1080, 1920, 30
SAFE_L, SAFE_R, SAFE_T, SAFE_B = 90, 990, 150, 1670
CX = W // 2
REPO = 'github.com/auri-intelligence/auri-3310'

BLUE = (11, 26, 58)
BLUE2 = (24, 52, 104)
LCD_BG = (157, 200, 106)
LCD_FG = (28, 43, 20)
GREEN = (170, 232, 92)
WHITE = (245, 248, 240)

FONT_BIG = r'C:\Windows\Fonts\impact.ttf'
FONT_BOLD = r'C:\Windows\Fonts\seguibl.ttf'
FONT_MONO = r'C:\Windows\Fonts\consolab.ttf'
_fonts = {}


def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]


def ease(x):
    x = min(1, max(0, x))
    return 1 - (1 - x) ** 3


def back_ease(x):
    x = min(1, max(0, x))
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


# ---------- tempi parola per parola ----------
raw = json.load(open(os.path.join(OUT, 'parole.json'), encoding='utf-8'))
WORDS = []
# correzioni degli errori di trascrizione, riallineati al copione
FIX = {'Intra': 'Entra', 'Ci': 'Ce', 'davvero.': 'davvero?', 'Open': 'open', 'Source,': 'source,'}
i = 0
while i < len(raw):
    w, a, b = raw[i]
    if w == "'occhio":
        WORDS.append(['Nokia', a, raw[i + 1][2]])
        i += 2
        continue
    if w == 'Covertasti,':
        m = (a + b) / 2
        WORDS += [['Cover,', a, m], ['tasti,', m, b]]
    elif w == 'Sigui':
        WORDS.append(['Seguimi', a, raw[i + 1][2]])
        i += 2
        continue
    elif w.startswith("'") and WORDS:
        WORDS[-1][0] += w
        WORDS[-1][2] = b
    else:
        WORDS.append([FIX.get(w, w), a, b])
    i += 1
for k in range(1, len(WORDS)):
    if WORDS[k][0] == 'tu' and WORDS[k - 1][0] == 'E':
        WORDS[k][0] = 'tu?'
    if WORDS[k][0] == '3310' and WORDS[k - 1][0] == 'Nokia':
        WORDS[k][0] = '3310...'


def T(word, nth=0):
    norm = lambda x: x[0].lower().strip('.,?!')
    hits = [x for x in WORDS if norm(x) == word.lower()] or [x for x in WORDS if norm(x).startswith(word.lower())]
    return hits[nth][1]


wf = wave.open(os.path.join(OUT, 'voce_Fenrir.wav'))
SR = wf.getframerate()
VOICE = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
DUR = len(VOICE) / SR
OUTRO = DUR + 0.1
DUR_V = DUR + 3.8
NF = int(round(DUR_V * FPS))

# frasi per le didascalie: si spezza su punteggiatura o ogni 3 parole
LINES = []
cur = []
for w in WORDS:
    cur.append(w)
    if w[0][-1] in '.,?!' or len(cur) >= 3:
        LINES.append(cur)
        cur = []
if cur:
    LINES.append(cur)

# ---------- materiale ----------
Image.MAX_IMAGE_PIXELS = None
comp = Image.open(os.path.join(ROOT, 'docs', 'photos', '15_componenti_fronte.jpg')).convert('RGB')
comp_retro = Image.open(os.path.join(ROOT, 'docs', 'photos', '16_componenti_retro.jpg')).convert('RGB')
pano = Image.open(os.path.join(ROOT, 'docs', 'photos', '13_panoramica_smontaggio.jpg')).convert('RGB')
pcb_scan = Image.open(os.path.join(ROOT, 'docs', 'scans', 'pcb_fronte_600dpi.png')).convert('RGB')
cover = Image.open(os.path.join(ROOT, 'firmware', 'web', 'cover.webp')).convert('RGBA')
PIECES = {
    'back': comp.crop((0, 0, 285, 676)),
    'front': comp.crop((290, 0, 598, 676)),
    'keys': comp.crop((612, 25, 842, 305)),
    'batt': comp.crop((612, 310, 835, 620)),
    'pcb': comp.crop((845, 30, 1085, 676)),
    'ui': comp.crop((1085, 40, 1322, 655)),
    'chassis': comp.crop((1325, 20, 1600, 676)),
}
# finestra LCD della cover: 15.24% / 26.01% / 68.46% x 21.01% dell'immagine
SCREEN = (round(0.1524 * cover.width), round(0.2601 * cover.height),
          round((0.1524 + 0.6846) * cover.width), round((0.2601 + 0.2101) * cover.height))
LCD = np.load(os.path.join(OUT, 'lcd.npz'))
LCD = {k: LCD[k] for k in LCD.files}


def lcd_img(bits, scale, gap=True, on=1.0):
    h, w = bits.shape
    bg = np.array(LCD_BG, np.float32) * (0.55 + 0.45 * on)
    fg = np.array(LCD_FG, np.float32)
    px = np.where(bits[..., None], fg, bg).astype(np.uint8)
    big = px.repeat(scale, 0).repeat(scale, 1)
    if gap and scale >= 4:
        big[scale - 1::scale, :, :] = (big[scale - 1::scale, :, :] * 0.85 + bg * 0.15).astype(np.uint8)
        big[:, scale - 1::scale, :] = (big[:, scale - 1::scale, :] * 0.85 + bg * 0.15).astype(np.uint8)
    return Image.fromarray(big)


def lcd_frame(name, i):
    a = LCD[name]
    return a[int(i) % len(a)]


def phone(bits, on=1.0, glow=0.0):
    im = cover.copy()
    x0, y0, x1, y1 = SCREEN
    ww, hh = x1 - x0, y1 - y0
    bg = tuple(int(v * (0.55 + 0.45 * on)) for v in LCD_BG) if bits is not None else (120, 130, 110)
    panel = Image.new('RGB', (ww, hh), bg)
    if bits is not None:
        l = lcd_img(bits, 10, on=on)
        s = min((ww - 20) / l.width, (hh - 20) / l.height)
        l = l.resize((int(l.width * s), int(l.height * s)), Image.NEAREST)
        panel.paste(l, ((ww - l.width) // 2, (hh - l.height) // 2))
    mask = Image.new('L', (ww, hh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, ww - 1, hh - 1), int(ww * 0.05), fill=255)
    im.paste(panel, (x0, y0), mask)
    if glow > 0:
        d = ImageDraw.Draw(im)
        cx, cy, r = 590, 1450, int(80 + 60 * glow)
        ov = Image.new('RGBA', im.size)
        ImageDraw.Draw(ov).ellipse((cx - r, cy - r // 2, cx + r, cy + r // 2), fill=GREEN + (int(160 * glow),))
        im = Image.alpha_composite(im, ov.filter(ImageFilter.GaussianBlur(25)))
    return im


# ---------- disegno ----------
BG_CACHE = {}


def background(t, tint=BLUE):
    key = tint
    if key not in BG_CACHE:
        y = np.linspace(0, 1, H)[:, None, None]
        base = np.array(tint, np.float32) * (1.15 - 0.5 * y) + np.array(BLUE2, np.float32) * 0.35 * (1 - y)
        img = np.broadcast_to(base, (H, W, 3)).copy()
        img[::24, :, :] += 10
        img[:, ::24, :] += 10
        BG_CACHE[key] = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return BG_CACHE[key].copy()


def paste_scaled(canvas, img, cx, cy, scale, rot=0, alpha=1.0, shadow=True):
    w, h = max(1, int(img.width * scale)), max(1, int(img.height * scale))
    im = img.resize((w, h), Image.BILINEAR).convert('RGBA')
    if rot:
        im = im.rotate(rot, Image.BILINEAR, expand=True)
    if alpha < 1:
        a = im.getchannel('A').point(lambda v: int(v * alpha))
        im.putalpha(a)
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel('A').point(lambda v: int(v * 0.55)))
        canvas.paste(sh.filter(ImageFilter.GaussianBlur(14)), (x + 18, y + 26), sh.filter(ImageFilter.GaussianBlur(14)))
    canvas.paste(im, (x, y), im)


def text_w(txt, f):
    b = f.getbbox(txt)
    return b[2] - b[0]


def auri_spans(txt):
    """Spezza il testo isolando AurI: 'ur' va resa piu' piccola."""
    out = []
    i = 0
    while i < len(txt):
        j = txt.find('AurI', i)
        if j < 0:
            out.append((txt[i:], False))
            break
        if j > i:
            out.append((txt[i:j], False))
        out += [('A', 'hi'), ('ur', True), ('I', 'hi')]
        i = j + 4
    return out


def span_fill(kind, fill):
    if kind == 'hi':
        return GREEN if fill != GREEN else WHITE
    if kind is True:
        return tuple(int(v * 0.6) for v in fill[:3])
    return fill


def draw_text(canvas, txt, cx, y, size, fill=WHITE, path=FONT_BIG, stroke=0, stroke_fill=(0, 0, 0), scale=1.0, maxw=SAFE_R - SAFE_L):
    size = int(size * scale)
    f = font(path, size)
    fs = font(path, int(size * 0.72))
    spans = auri_spans(txt)
    tw = sum(text_w(s, fs if small is True else f) for s, small in spans)
    if tw > maxw:
        return draw_text(canvas, txt, cx, y, size * maxw / tw, fill, path, stroke, stroke_fill, 1.0, maxw)
    d = ImageDraw.Draw(canvas)
    x = cx - tw / 2
    asc = f.getmetrics()[0]
    for s, small in spans:
        ff = fs if small is True else f
        off = asc - ff.getmetrics()[0]
        d.text((x, y + off), s, font=ff, fill=span_fill(small, fill), stroke_width=stroke, stroke_fill=stroke_fill)
        x += text_w(s, ff)
    return size


def pop_text(canvas, txt, cx, y, size, t0, t, fill=WHITE, path=FONT_BIG):
    k = t - t0
    if k < 0:
        return
    s = 0.4 + 0.6 * back_ease(k / 0.18)
    layer = Image.new('RGBA', (W, H))
    draw_text(layer, txt, cx, y, size, fill=fill, path=path, stroke=8, stroke_fill=(5, 12, 28))
    if abs(s - 1) > 0.01:
        layer = layer.resize((int(W * s), int(H * s)), Image.BILINEAR)
        ox, oy = int(cx - cx * s), int((y + size / 2) - (y + size / 2) * s)
        tmp = Image.new('RGBA', (W, H))
        tmp.paste(layer, (ox, oy))
        layer = tmp
    canvas.paste(layer, (0, 0), layer)


def pixelate(img, amt):
    if amt <= 0:
        return img
    f = max(2, int(4 + 60 * amt))
    return img.resize((W // f, H // f), Image.BILINEAR).resize((W, H), Image.NEAREST)


def glitch(img, amt, seed):
    if amt <= 0:
        return img
    rng = np.random.default_rng(seed)
    a = np.array(img)
    sh = int(18 * amt)
    a[:, :, 0] = np.roll(a[:, :, 0], sh, 1)
    a[:, :, 2] = np.roll(a[:, :, 2], -sh, 1)
    for _ in range(int(10 * amt)):
        y = rng.integers(0, H - 80)
        h = rng.integers(8, 80)
        a[y:y + h] = np.roll(a[y:y + h], int(rng.integers(-120, 120) * amt), 1)
    return Image.fromarray(a)


def camera(img, zoom=1.0, dx=0, dy=0, rot=0):
    if zoom == 1 and dx == 0 and dy == 0 and rot == 0:
        return img
    if rot:
        img = img.rotate(rot, Image.BILINEAR, center=(W / 2, H / 2))
    w, h = W / zoom, H / zoom
    x0, y0 = (W - w) / 2 - dx, (H - h) / 2 - dy
    return img.transform((W, H), Image.EXTENT, (x0, y0, x0 + w, y0 + h), Image.BILINEAR)


def scan_beam(canvas, y, x0=0, x1=W):
    ov = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(ov)
    for i in range(60):
        d.line((x0, y - i, x1, y - i), fill=GREEN + (int(90 * (1 - i / 60) ** 2),))
    d.rectangle((x0, y - 3, x1, y + 3), fill=(230, 255, 200, 255))
    ov = ov.filter(ImageFilter.GaussianBlur(2))
    canvas.paste(ov, (0, 0), ov)


def git_icon(canvas, cx, cy, s, col=GREEN):
    d = ImageDraw.Draw(canvas)
    r = int(26 * s)
    lw = int(14 * s)
    a = (cx - int(70 * s), cy - int(110 * s))
    b = (cx - int(70 * s), cy + int(110 * s))
    c = (cx + int(80 * s), cy - int(40 * s))
    d.line((a, b), fill=col, width=lw)
    d.line(((a[0], cy + int(30 * s)), (c[0], c[1] + int(20 * s))), fill=col, width=lw)
    d.line(((c[0], c[1] + int(20 * s)), c), fill=col, width=lw)
    for p in (a, b, c):
        d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=BLUE, outline=col, width=lw)
    d.rounded_rectangle((cx - int(200 * s), cy - int(200 * s), cx + int(200 * s), cy + int(200 * s)),
                        radius=int(60 * s), outline=col, width=int(10 * s))


def esp_chip(scale=1.0):
    im = Image.new('RGBA', (520, 760), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, 510, 750), 22, fill=(18, 22, 30), outline=GREEN, width=6)
    for i in range(6):
        x = 60 + i * 70
        d.line((x, 40, x, 150), fill=GREEN, width=12)
        if i < 5:
            d.line((x, 40 if i % 2 else 150, x + 70, 40 if i % 2 else 150), fill=GREEN, width=12)
    d.rounded_rectangle((60, 220, 460, 640), 16, fill=(160, 168, 178), outline=(220, 225, 230), width=6)
    for y in range(240, 640, 26):
        d.line((70, y, 450, y), fill=(150, 158, 168), width=2)
    for side in (0, 1):
        for k in range(16):
            y = 200 + k * 34
            x = 0 if side == 0 else 495
            d.rectangle((x, y, x + 25, y + 16), fill=(212, 175, 55))
    f = font(FONT_MONO, 64)
    d.text((260, 400), 'ESP32-S3', font=f, fill=(25, 35, 45), anchor='mm')
    d.text((260, 480), 'dual core 240MHz', font=font(FONT_MONO, 30), fill=(40, 50, 60), anchor='mm')
    return im


CHIP = esp_chip()
CODE = open(os.path.join(ROOT, 'firmware', 'apps', 'assistente.py'), encoding='utf-8').read().splitlines()


# ---------- scene ----------
from cervello import brain_bits

# fascia libera per il telefono: titoli sopra (170-520), didascalie sotto (da 1520)
PH_TOP, PH_BOT = 545, 1490


def phone_top(ph):
    """Solo la meta' alta del telefono (display e tasti di navigazione), sfumata in basso."""
    h = int(ph.height * 0.6)
    im = ph.crop((0, 0, ph.width, h))
    a = np.array(im.getchannel('A'), np.float32)
    f = int(h * 0.15)
    a[h - f:] *= np.linspace(1, 0, f)[:, None]
    im.putalpha(Image.fromarray(a.astype(np.uint8)))
    return im


def place_phone(c, ph, grow=0.0, top=PH_TOP, bot=PH_BOT):
    s = (bot - top) / ph.height * (1 + grow)
    paste_scaled(c, ph, CX, (top + bot) / 2, s)


def sc_hook(t):
    c = background(t)
    on = 1.0 if t > 0.15 else (0.3 if int(t * 40) % 2 else 1.0)
    place_phone(c, phone(brain_bits(t), on=on), 0.02 * ease(t / 2.5))
    pop_text(c, 'AI', CX, 160, 240, 0.0, t, fill=GREEN)
    pop_text(c, 'su un Nokia 3310?', CX, 420, 95, T('su'), t)
    return c, 1.0, 0, 0


def sc_lui(t):
    c = background(t)
    k = t - T('Sì')
    bits = lcd_frame('home', int(k * 30))
    l = lcd_img(bits, 10)
    paste_scaled(c, l, CX, 900, 0.95 + 0.1 * k, shadow=True)
    pop_text(c, 'SÌ.', CX, 260, 220, T('Sì'), t, fill=GREEN)
    pop_text(c, 'PROPRIO LUI.', CX, 1250, 140, T('proprio'), t)
    return c, 1.0 + 0.05 * k, 0, 0


def sc_smonta(t):
    c = background(t)
    k = t - T('smontato')
    order = ['back', 'front', 'keys', 'pcb', 'ui', 'chassis']
    spread = ease(k / 1.6)
    for i, n in enumerate(order):
        off = (i - 2.5) * 300 * spread - 200 * ease((k - 1.2) / 1.2)
        rot = (i - 2.5) * 6 * (1 - spread)
        paste_scaled(c, PIECES[n], CX + off, 900 + (i % 2) * 60 * spread, 1.25, rot=rot)
    pop_text(c, 'PEZZO', CX, 240, 160, T('pezzo'), t, fill=GREEN)
    pop_text(c, 'PER PEZZO', CX, 1240, 150, T('per'), t)
    return c, 1.05 + 0.08 * k, 0, 0


def sc_scan(t):
    c = background(t, (8, 20, 44))
    k = t - T('e', 0) if t < T('600') else t - T('e', 0)
    sc = 1.9
    img = comp
    x = CX + 900 - 1300 * ease(k / 3.3)
    paste_scaled(c, img, x, 900, sc, shadow=False)
    by = int(450 + ((k * 520) % 900))
    scan_beam(c, by)
    d = ImageDraw.Draw(c)
    if t >= T('600'):
        kk = t - T('600')
        box = Image.new('RGBA', (W, H))
        draw_text(box, '600 DPI', CX, 1170, 230, fill=GREEN, stroke=10, stroke_fill=(5, 12, 28))
        s = 1.8 - 0.8 * ease(kk / 0.15)
        box = camera(box, s)
        c.paste(box, (0, 0), box)
    else:
        pop_text(c, 'SCANSIONE', CX, 230, 150, T('scansionato'), t, fill=GREEN)
    return c, 1.0, 0, 0


def sc_list(t):
    seq = [('Cover', 'back', 'COVER'), ('tasti', 'keys', 'TASTI'), ('scheda', 'pcb', 'SCHEDA'), ('display', 'ui', 'DISPLAY')]
    c = background(t)
    if t >= T('tutto', 0) and t < T('Perché'):
        k = t - T('tutto', 0)
        paste_scaled(c, comp_retro, CX, 900, 1.3 - 0.4 * ease(k / 0.5))
        pop_text(c, 'TUTTO.', CX, 1170, 220, T('tutto', 0), t, fill=GREEN)
        return c, 1.0, 0, 0
    cur = seq[0]
    for s in seq:
        if t >= T(s[0]):
            cur = s
    k = t - T(cur[0])
    if cur[1] == 'ui':
        bits = lcd_frame('menu', int(k * 30) + 20)
        paste_scaled(c, lcd_img(bits, 10), CX, 900, 1.0 + 0.2 * k)
    else:
        im = PIECES[cur[1]]
        paste_scaled(c, im, CX, 900, (1000 / im.height) * (1.0 + 0.25 * k), rot=4 - 8 * ease(k / 0.3))
    pop_text(c, cur[2], CX, 230, 190, T(cur[0]), t, fill=GREEN)
    return c, 1.0, 0, 0


def sc_mm(t):
    c = background(t, (6, 18, 40))
    k = t - T('Perché')
    d = ImageDraw.Draw(c)
    for gx in range(0, W, 40):
        d.line((gx, 0, gx, H), fill=(40, 90, 70) if gx % 200 else (70, 150, 100), width=1)
    for gy in range(0, H, 40):
        d.line((0, gy, W, gy), fill=(40, 90, 70) if gy % 200 else (70, 150, 100), width=1)
    ph = phone(LCD['home'][0])
    s = 0.33
    PX = CX
    paste_scaled(c, ph, PX, 980, s * (1 + 0.04 * k), shadow=False)
    ph_h, ph_w = ph.height * s, ph.width * s
    top, bot = 980 - ph_h / 2, 980 + ph_h / 2
    left, right = PX - ph_w / 2, PX + ph_w / 2
    p = ease((t - T('precisa')) / 0.6)
    if p > 0:
        xx = left - 50
        yb = top + (bot - top) * p
        d.line((xx, top, xx, yb), fill=GREEN, width=6)
        d.line((xx - 20, top, xx + 20, top), fill=GREEN, width=6)
        if p >= 1:
            d.line((xx - 20, bot, xx + 20, bot), fill=GREEN, width=6)
            draw_text(c, '113 mm', xx - 100, 960, 50, fill=GREEN, path=FONT_MONO, maxw=190)
    p2 = ease((t - T('millimetro')) / 0.5)
    if p2 > 0:
        yy = top - 30
        d.line((left, yy, left + (right - left) * p2, yy), fill=GREEN, width=6)
        if p2 >= 1:
            draw_text(c, '48 mm', PX, yy - 75, 56, fill=GREEN, path=FONT_MONO)
    pop_text(c, 'AL MILLIMETRO', CX, 200, 150, T('millimetro'), t, fill=WHITE)
    if t < T('millimetro'):
        pop_text(c, 'PRECISA', CX, 200, 160, T('precisa'), t, fill=GREEN)
    return c, 1.0 + 0.03 * k, 0, 0


def sc_vero(t):
    c = background(t)
    k = t - T('partendo')
    paste_scaled(c, pano, CX - 60 + 120 * k / 1.8, 900, 1.1 + 0.15 * k)
    pop_text(c, 'UN TELEFONO VERO', CX, 1290, 130, T('telefono'), t, fill=GREEN)
    return c, 1.0, 0, 0


def sc_idea(t):
    c = background(t)
    k = t - T("L'idea")
    if t < T('tenere'):
        place_phone(c, phone(lcd_frame('home', int(k * 30))), 0.02 * k)
        pop_text(c, "L'IDEA È", CX, 170, 140, T("L'idea"), t)
        pop_text(c, 'SEMPLICE', CX, 340, 160, T('semplice'), t, fill=GREEN)
        return c, 1.0, 0, 0
    k = t - T('tenere')
    bits = lcd_frame('snake', int(k * 30))
    paste_scaled(c, lcd_img(bits, 10), CX, 860, 0.98 + 0.06 * k)
    pop_text(c, 'TUTTO CIÒ', CX, 260, 140, T('tenere'), t)
    if t >= T('2000'):
        pop_text(c, 'DEL 2000', CX, 1200, 190, T('2000'), t, fill=GREEN)
    else:
        pop_text(c, 'CHE AMIAMO', CX, 1250, 140, T('amiamo'), t, fill=GREEN)
    return c, 1.0, 0, 0


def sc_keep(t):
    seq = [('scocca', 'back', 'SCOCCA'), ('schermo', None, 'SCHERMO'), ('tastiera', 'keys', 'TASTIERA')]
    c = background(t)
    cur = seq[0]
    for s in seq:
        if t >= T(s[0]):
            cur = s
    k = t - T(cur[0])
    if cur[1] is None:
        paste_scaled(c, lcd_img(lcd_frame('home', 5), 10), CX, 900, 1.0 + 0.15 * k)
    else:
        im = PIECES[cur[1]]
        paste_scaled(c, im, CX, 900, (980 / im.height) * (1.0 + 0.2 * k))
    pop_text(c, cur[2], CX, 230, 170, T(cur[0]), t, fill=GREEN)
    d = ImageDraw.Draw(c)
    draw_text(c, 'RESTA', CX, 1300, 120, fill=WHITE)
    return c, 1.0, 0, 0


def sc_brain(t):
    c = background(t, (14, 22, 50))
    k = t - T('cambiare')
    out = ease(k / 0.8)
    paste_scaled(c, PIECES['pcb'], CX - 700 * out, 900 + 200 * out, 1.4, rot=-25 * out, alpha=1 - 0.6 * out)
    t_in = T('cambiare') + 0.45
    inn = back_ease((t - t_in) / 0.45)
    if t >= t_in:
        paste_scaled(c, CHIP, CX + 700 * (1 - inn), 820, 0.95)
    pop_text(c, 'SOLO IL', CX, 220, 140, T('solo'), t)
    pop_text(c, 'CERVELLO', CX, 1220, 180, T('cervello'), t, fill=GREEN)
    return c, 1.0 + 0.05 * k, 0, 0


def sc_voice(t):
    c = background(t)
    k = t - T('Tieni')
    listen = LCD['assist'][35:75]
    wait = LCD['assist'][78:95]
    if t < T('e', 2):
        bits = listen[int(k * 30) % len(listen)]
    elif t < T('risponde'):
        bits = wait[min(len(wait) - 1, int((t - T('e', 2)) * 30))]
    else:
        bits = LCD['assist'][-1]
    held = T('Tieni') <= t < T('e', 2)
    ph = phone(bits, glow=0.6 + 0.4 * math.sin(k * 12) if held else 0)
    place_phone(c, phone_top(ph), 0.03 * ease((t - T('gli')) / 0.4))
    if T('parli') <= t < T('risponde'):
        d = ImageDraw.Draw(c)
        for i in range(3):
            r = 370 + ((k * 200 + i * 45) % 135)
            col = tuple(int(v * (1 - (r - 370) / 135)) for v in GREEN)
            d.arc((CX - r, 1120 - r, CX + r, 1120 + r), 150, 210, fill=col, width=10)
            d.arc((CX - r, 1120 - r, CX + r, 1120 + r), 330, 30, fill=col, width=10)
    if t < T('gli'):
        pop_text(c, 'TIENI PREMUTO', CX, 230, 140, T('Tieni'), t, fill=GREEN)
    elif t < T('e', 2):
        pop_text(c, 'GLI PARLI', CX, 230, 160, T('gli'), t, fill=GREEN)
    else:
        pop_text(c, 'TI RISPONDE', CX, 230, 160, T('risponde'), t, fill=GREEN)
    return c, 1.0, 0, 0


def sc_best(t):
    c = background(t, (4, 10, 24))
    k = t - T('E', 0) if False else t - WORDS[[w[0] for w in WORDS].index('E')][1]
    pop_text(c, 'LA PARTE', CX, 560, 170, WORDS[[w[0] for w in WORDS].index('E')][1], t)
    pop_text(c, 'MIGLIORE?', CX, 760, 220, T('migliore'), t, fill=GREEN)
    return c, 1.0 + 0.1 * k, 0, 0


def sc_open(t):
    c = background(t, (4, 14, 20))
    k = t - T('open')
    d = ImageDraw.Draw(c)
    f = font(FONT_MONO, 30)
    off = int(k * 140)
    for i in range(48):
        line = CODE[(i + off // 40) % len(CODE)]
        d.text((SAFE_L, 160 + i * 40 - off % 40), line[:48], font=f, fill=(50, 110, 60))
    ov = Image.new('RGBA', (W, H), (4, 14, 20, 150))
    c.paste(ov, (0, 0), ov)
    if t < T('Lo'):
        pop_text(c, 'OPEN', CX, 520, 300, T('open'), t, fill=GREEN)
        pop_text(c, 'SOURCE', CX, 840, 250, T('source'), t)
    else:
        draw_text(c, 'AurI OS', CX, 360, 120, fill=GREEN)
        pop_text(c, 'COSTRUISCILO', CX, 640, 150, T('costruire'), t)
        pop_text(c, 'ANCHE TU', CX, 850, 200, T('anche'), t, fill=GREEN)
    return c, 1.0 + 0.04 * k, 0, 0


def sc_git(t):
    c = background(t)
    k = t - T('Entra')
    s = back_ease(k / 0.35)
    git_icon(c, CX, 620, 1.1 * s)
    pop_text(c, 'github.com/', CX, 960, 80, T('GitHub'), t, path=FONT_BOLD)
    pop_text(c, 'auri-intelligence/', CX, 1060, 90, T('GitHub'), t, fill=GREEN, path=FONT_BOLD)
    pop_text(c, 'auri-3310', CX, 1165, 100, T('GitHub'), t, fill=GREEN, path=FONT_BOLD)
    if t >= T('costruiamolo'):
        pop_text(c, 'COSTRUIAMOLO INSIEME', CX, 1330, 90, T('costruiamolo'), t)
    return c, 1.0 + 0.03 * k, 0, 0


def heart(canvas, cx, cy, r, col):
    d = ImageDraw.Draw(canvas)
    d.ellipse((cx - r, cy - r * 0.8, cx, cy + r * 0.2), fill=col)
    d.ellipse((cx, cy - r * 0.8, cx + r, cy + r * 0.2), fill=col)
    d.polygon([(cx - r * 0.97, cy - 0.1 * r), (cx + r * 0.97, cy - 0.1 * r), (cx, cy + r)], fill=col)


T_E2 = [w[1] for w in WORDS if w[0] == 'E'][1]


def sc_comment(t):
    c = background(t, (10, 22, 52))
    t0 = T_E2
    k = t - t0
    pop_text(c, 'E TU?', CX, 190, 230, t0, t, fill=GREEN)
    d = ImageDraw.Draw(c)
    if t >= T('scrivimi'):
        s = back_ease((t - T('scrivimi')) / 0.3)
        x0, y0, x1, y1 = CX - 380 * s, 560 - 40 * s, CX + 380 * s, 900 + 40 * s
        d.rounded_rectangle((x0, y0, x1, y1), 50, fill=WHITE)
        d.polygon([(CX - 200, y1 - 2), (CX - 120, y1 - 2), (CX - 230, y1 + 90)], fill=WHITE)
        if s > 0.9:
            if t < T('aggiungeresti'):
                for j in range(3):
                    on = int(k * 6 + j) % 3 == 0
                    d.ellipse((CX - 110 + j * 90, 700, CX - 50 + j * 90, 760), fill=BLUE if on else (150, 165, 190))
            else:
                draw_text(c, 'Cosa aggiungeresti', CX, 610, 70, fill=BLUE, path=FONT_BOLD, maxw=700)
                draw_text(c, 'al tuo Nokia 3310?', CX, 720, 70, fill=BLUE, path=FONT_BOLD, maxw=700)
                n = min(4, int((t - T('aggiungeresti')) * 4))
                draw_text(c, '...' [:max(0, n - 1)] or ' ', CX, 800, 60, fill=(80, 100, 140), path=FONT_BOLD)
    if t >= T('like'):
        kk = t - T('like')
        s = back_ease(kk / 0.3)
        r = int(150 * s * (1 + 0.08 * math.sin(kk * 10)))
        heart(c, CX, 1120, r, (255, 70, 110))
        for j in range(8):
            a = j * math.pi / 4 + kk
            rr = 200 + 140 * ease(kk / 0.6)
            heart(c, CX + rr * math.cos(a), 1100 + rr * math.sin(a) * 0.7, int(30 * (1 - ease(kk / 1.2))), GREEN)
        pop_text(c, 'LASCIA UN LIKE', CX, 1300, 110, T('like'), t)
    elif t >= T('scrivimi'):
        pop_text(c, 'SCRIVIMI NEI COMMENTI', CX, 1060, 90, T('commenti'), t)
    return c, 1.0 + 0.03 * k, 0, 0


def logo_pixels():
    f = font(FONT_BIG, 60)
    im = Image.new('L', (200, 80), 0)
    d = ImageDraw.Draw(im)
    fs = font(FONT_BIG, 40)
    x = 10
    cells = []
    for s, ff, kind in [('A', f, 'hi'), ('ur', fs, 'lo'), ('I', f, 'hi')]:
        tmp = Image.new('L', (200, 80), 0)
        ImageDraw.Draw(tmp).text((x, 70 - ff.getmetrics()[0]), s, font=ff, fill=255)
        a = np.array(tmp) > 127
        ys, xs = np.nonzero(a)
        cells += [(xx, yy, kind) for xx, yy in zip(xs, ys)]
        x += text_w(s, ff) + 4
    xs = np.array([p[0] for p in cells])
    ys = np.array([p[1] for p in cells])
    return cells, (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2


LOGO, LOGO_CX, LOGO_CY = logo_pixels()
_rng = np.random.default_rng(7)
LOGO_START = [(_rng.uniform(0, W), _rng.uniform(150, 1600), _rng.uniform(0, 0.5)) for _ in LOGO]


def sc_outro(t):
    c = background(t, (6, 12, 30))
    k = t - OUTRO
    d = ImageDraw.Draw(c)
    px = 9
    for (x, y, kind), (sx, sy, dl) in zip(LOGO, LOGO_START):
        e = ease((k - dl) / 0.8)
        tx = CX + (x - LOGO_CX) * px
        ty = 640 + (y - LOGO_CY) * px
        X, Y = sx + (tx - sx) * e, sy + (ty - sy) * e
        col = GREEN if kind == 'hi' else (90, 130, 70)
        d.rectangle((X, Y, X + px - 1, Y + px - 1), fill=col)
    if k > 1.4:
        a = ease((k - 1.4) / 0.4)
        draw_text(c, 'github.com/auri-intelligence/auri-3310', CX, 1000 + 30 * (1 - a), 56, fill=WHITE, path=FONT_BOLD)
    if k > 1.9:
        s = back_ease((k - 1.9) / 0.35)
        w2, h2 = 380 * s, 70 * s
        d.rounded_rectangle((CX - w2, 1180 - h2, CX + w2, 1180 + h2), int(40 * s), fill=GREEN)
        if s > 0.8:
            draw_text(c, 'PARTE 2 IN ARRIVO', CX, 1145, 66, fill=BLUE, path=FONT_BOLD)
            draw_text(c, '+ segui', CX, 1290, 60, fill=GREEN, path=FONT_BOLD)
    return c, 1.0, 0, 0


def sc_end(t):
    c = background(t, (6, 12, 30))
    k = t - T('Seguimi')
    blink = (int(k * 4) % 2) == 0
    bits = np.zeros((48, 84), bool)
    if t >= T('Ce'):
        g = LCD['assist'][80]
        bits = g.copy()
        bits[12:] = False
        if blink:
            bits[18:40, 36:48] = QMARK
    else:
        bits = LCD['home'][0]
    ph = phone(bits, on=1.0 if blink or t < T('Ce') else 0.6)
    place_phone(c, phone_top(ph), 0.0, PH_TOP, 1270)
    if t < T('come'):
        pop_text(c, 'SEGUIMI', CX, 220, 190, T('Seguimi'), t, fill=GREEN)
    elif t < T('Ce'):
        pop_text(c, 'COME VA', CX, 170, 140, T('come'), t)
        pop_text(c, 'A FINIRE?', CX, 330, 150, T('finire'), t, fill=GREEN)
    else:
        pop_text(c, 'CE LA FARÀ', CX, 170, 140, T('Ce'), t)
        pop_text(c, 'A PARLARE DAVVERO?', CX, 340, 100, T('parlare'), t, fill=GREEN)
        if t > T('davvero') + 0.15:
            d = ImageDraw.Draw(c)
            d.rounded_rectangle((CX - 360, 1300, CX + 360, 1420), 30, fill=GREEN)
            draw_text(c, 'SEGUI PER LA PARTE 2', CX, 1318, 64, fill=BLUE, path=FONT_BOLD)
    return c, 1.0, 0, 0


QMARK = np.array([[c == '#' for c in r] for r in [
    '..######....', '.##....##...', '.##....##...', '.......##...', '......##....', '.....##.....',
    '....##......', '....##......', '....##......', '....##......', '............', '............',
    '....##......', '....##......', '............', '............', '............', '............',
    '............', '............', '............', '............']])

SCENES = [
    (0.0, sc_hook), (T('Sì') - 0.1, sc_lui), (T('L'), sc_smonta), (T('e', 0), sc_scan),
    (T('Cover'), sc_list), (T('Perché'), sc_mm), (T('partendo'), sc_vero), (T("L'idea"), sc_idea),
    (T('scocca'), sc_keep), (T('e', 1), sc_brain), (T('Tieni'), sc_voice),
    (WORDS[[w[0] for w in WORDS].index('E')][1] - 0.2, sc_best), (T('open'), sc_open),
    (T('Entra'), sc_git), (T_E2 - 0.1, sc_comment), (T('Seguimi'), sc_end), (OUTRO, sc_outro),
]
CUTS = [s[0] for s in SCENES[1:]]
HITS = [T(w) for w in ['Sì', '600', 'tutto', 'millimetro', 'cervello', 'risponde', 'open', 'GitHub', 'like', 'davvero']]
HITS += [T('3310'), T('tu', 1)]


def scene_at(t):
    cur = SCENES[0]
    for s in SCENES:
        if t >= s[0]:
            cur = s
    return cur


def cap_word(d, x, y, w, f, fill, stroke):
    fs = font(f.path, int(f.size * 0.72))
    asc = f.getmetrics()[0]
    for s, kind in auri_spans(w):
        ff = fs if kind is True else f
        col = (GREEN if fill != BLUE else (255, 255, 255)) if kind == 'hi' else span_fill(kind, fill)
        d.text((x, y + asc - ff.getmetrics()[0]), s, font=ff, fill=col, stroke_width=stroke, stroke_fill=(5, 12, 28))
        x += text_w(s, ff)


def captions(c, t):
    line = None
    for ln in LINES:
        if ln[0][1] - 0.05 <= t <= ln[-1][2] + 0.35:
            line = ln
    if not line:
        return
    f = font(FONT_BOLD, 66)
    words = [w[0] for w in line]
    widths = [text_w(w, f) for w in words]
    sp = 22
    total = sum(widths) + sp * (len(words) - 1)
    size = 66
    if total > SAFE_R - SAFE_L - 40:
        size = int(66 * (SAFE_R - SAFE_L - 40) / total)
        f = font(FONT_BOLD, size)
        widths = [text_w(w, f) for w in words]
        total = sum(widths) + sp * (len(words) - 1)
    y = 1525
    x = CX - total / 2
    d = ImageDraw.Draw(c)
    for (w, a, b), wd in zip(line, widths):
        nxt = [w2[1] for w2 in WORDS if w2[1] > a]
        on = a <= t < (nxt[0] if nxt else b + 0.5)
        if on:
            k = ease((t - a) / 0.1)
            d.rounded_rectangle((x - 12, y - 6 - 6 * k, x + wd + 12, y + size * 1.25 + 4), 14, fill=GREEN)
            cap_word(d, x, y - 6 * k, w, f, BLUE, 0)
        else:
            col = WHITE if t >= a else (150, 160, 175)
            cap_word(d, x, y, w, f, col, 5)
        x += wd + sp


def render(i):
    t = i / FPS
    start, fn = scene_at(t)
    c, z, dx, dy = fn(t)
    c = c.convert('RGB')
    hit = min([t - h for h in HITS if t >= h] or [9])
    shake = max(0, 1 - hit / 0.25)
    if shake > 0:
        rng = np.random.default_rng(i)
        dx += rng.uniform(-18, 18) * shake
        dy += rng.uniform(-18, 18) * shake
        z *= 1 + 0.05 * shake
    c = camera(c, z, dx, dy)
    since_cut = min([t - x for x in CUTS if t >= x] or [9])
    if since_cut < 0.1:
        c = pixelate(c, 1 - since_cut / 0.1)
    if since_cut < 0.2 or (shake > 0.6):
        c = glitch(c, max(1 - since_cut / 0.2, shake * 0.6), i)
    if hit < 0.08:
        c = Image.blend(c, Image.new('RGB', (W, H), (230, 255, 210)), 0.6 * (1 - hit / 0.08))
    a = np.array(c)
    a[::4] = (a[::4] * 0.9).astype(np.uint8)
    c = Image.fromarray(a)
    captions(c, t)
    d = ImageDraw.Draw(c)
    d.rectangle((0, 1672, W, 1680), fill=(30, 45, 80))
    d.rectangle((0, 1672, int(W * t / DUR_V), 1680), fill=GREEN)
    return c


# ---------- audio ----------
def music():
    n = int(DUR_V * SR)
    voice = np.pad(VOICE, (0, n - len(VOICE)))
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    bpm = 132
    step = 60 / bpm / 2
    prog = [(57, [0, 3, 7, 12]), (53, [0, 4, 7, 12]), (48, [0, 4, 7, 12]), (55, [0, 4, 7, 11])]
    nsteps = int((OUTRO + 0.8) / step)
    for s in range(nsteps):
        root, arp = prog[(s // 16) % 4]
        note = root + 12 + arp[s % 4]
        f = 440 * 2 ** ((note - 69) / 12)
        a, b = int(s * step * SR), int((s + 0.8) * step * SR)
        b = min(b, n)
        if a >= n:
            break
        tt = np.arange(b - a) / SR
        env = np.exp(-tt * 9)
        out[a:b] += 0.22 * np.sign(np.sin(2 * np.pi * f * tt)) * env
        if s % 4 == 0:
            fb = 440 * 2 ** ((root - 12 - 69) / 12)
            out[a:b] += 0.25 * (2 * ((tt * fb) % 1) - 1) * np.exp(-tt * 4) * (np.abs(2 * ((tt * fb) % 1) - 1) < 2)
        if s % 2 == 0:
            m = min(b, a + int(0.03 * SR))
            out[a:m] += 0.12 * np.random.default_rng(s).uniform(-1, 1, m - a) * np.linspace(1, 0, m - a)
    a = int(nsteps * step * SR)
    tt = np.arange(n - a) / SR
    fade = np.clip(1 - tt / (n / SR - a / SR), 0, 1) ** 1.5
    for note in (45, 57, 61, 64, 69):
        fq = 440 * 2 ** ((note - 69) / 12)
        out[a:] += 0.13 * np.sign(np.sin(2 * np.pi * fq * tt)) * np.exp(-tt * 0.6) * fade
    for h in HITS + CUTS:
        a = int(h * SR)
        m = min(n, a + int(0.12 * SR))
        tt = np.arange(m - a) / SR
        out[a:m] += 0.35 * np.sign(np.sin(2 * np.pi * (1760 - 6000 * tt) * tt)) * np.exp(-tt * 30)
    env = np.abs(voice)
    k = int(0.15 * SR)
    env = np.convolve(env, np.ones(k) / k, 'same')
    duck = 1 - 0.55 * np.clip(env * 12, 0, 1)
    return out * duck * 0.16


def main():
    only = [float(x) for x in sys.argv[1:]]
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    if only:
        os.makedirs(os.path.join(OUT, 'prova'), exist_ok=True)
        for s in only:
            render(int(s * FPS)).save(os.path.join(OUT, 'prova', '%05.2f.png' % s))
        return
    mix = np.pad(VOICE, (0, int(DUR_V * SR) - len(VOICE))) + music()
    mix = mix / max(1.0, np.abs(mix).max() / 0.98)
    wav = os.path.join(OUT, 'mix.wav')
    with wave.open(wav, 'wb') as o:
        o.setnchannels(1)
        o.setsampwidth(2)
        o.setframerate(SR)
        o.writeframes((mix * 32767).astype(np.int16).tobytes())
    dst = os.path.join(OUT, 'auri_tiktok_v3.mp4')
    p = subprocess.Popen([ff, '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS),
                          '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                          '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                          '-t', '%.3f' % DUR_V, '-movflags', '+faststart', dst], stdin=subprocess.PIPE)
    for i in range(NF):
        p.stdin.write(render(i).tobytes())
        if i % 150 == 0:
            print(i, '/', NF, flush=True)
    p.stdin.close()
    p.wait()
    print('ok', dst, DUR_V)


if __name__ == '__main__':
    main()
