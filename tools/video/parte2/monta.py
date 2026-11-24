import importlib.util
import json
import math
import os
import subprocess
import sys
import wave

import numpy as np
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
sys.path.insert(0, os.path.dirname(HERE))

# grafica, LCD, effetti e outro sono quelli della Parte 1
_spec = importlib.util.spec_from_file_location('p1', os.path.join(HERE, '..', 'parte1', 'monta.py'))
p1 = importlib.util.module_from_spec(_spec)
_argv, sys.argv = sys.argv, sys.argv[:1]
_spec.loader.exec_module(p1)
sys.argv = _argv
from cervello import brain_bits

W, H, FPS, CX = p1.W, p1.H, p1.FPS, p1.CX
BLUE, GREEN, WHITE, LCD_BG, LCD_FG = p1.BLUE, p1.GREEN, p1.WHITE, p1.LCD_BG, p1.LCD_FG
RED = (255, 70, 90)
FONT_BIG, FONT_BOLD, FONT_MONO = p1.FONT_BIG, p1.FONT_BOLD, p1.FONT_MONO
ease, back_ease, pop_text, draw_text = p1.ease, p1.back_ease, p1.pop_text, p1.draw_text
paste_scaled, background, camera, phone, lcd_img = p1.paste_scaled, p1.background, p1.camera, p1.phone, p1.lcd_img
LCD = p1.LCD

# ---------- tempi parola per parola ----------
raw = json.load(open(os.path.join(OUT, 'parole.json'), encoding='utf-8'))
FIX = {"'occhia": 'Nokia', 'Club': 'Claude', 'continuati': 'continuate', 'dimmi,': 'dimmi:', '3310.': '3310?',
       'commenti.': 'commenti.', 'può?': 'può.', 'cuore,': 'cuore.', 'TV.': 'TV?'}
WORDS = [[FIX.get(w, w), a, b] for w, a, b in raw]
for k in range(1, len(WORDS)):
    if WORDS[k][0] == 'a' and WORDS[k - 1][0] == 'smartphone':
        WORDS[k][0] = 'ha'
    if WORDS[k][0] == 'ha' and WORDS[k - 1][0] == 'scanner':
        WORDS[k - 1][0], WORDS[k][0] = 'scanner,', 'a'
    if WORDS[k][0] == '3310?' and WORDS[k][1] > 10:
        WORDS[k][0] = '3310.'
    if WORDS[k][0] == 'commenti.' and WORDS[k - 1][0] == 'vostri':
        WORDS[k][0] = 'commenti?'


def T(word, nth=0):
    norm = lambda x: x[0].lower().strip('.,?!:')
    hits = [x for x in WORDS if norm(x) == word.lower().strip('.,?!:')]
    return hits[nth][1]


wf = wave.open(os.path.join(OUT, 'voce_Fenrir.wav'))
SR = wf.getframerate()
VOICE = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
DUR = len(VOICE) / SR
OUTRO = DUR + 0.1
DUR_V = DUR + 3.8
NF = int(round(DUR_V * FPS))

LINES, cur = [], []
for w in WORDS:
    cur.append(w)
    if w[0][-1] in '.,?!:' or len(cur) >= 3:
        LINES.append(cur)
        cur = []
if cur:
    LINES.append(cur)

# ---------- riprese reali ----------
CLIP_DIR = os.path.join(OUT, 'clip')
_clip_cache = {}
MONITOR_BOX = (360, 570, 300, 80)
STATIC = {'tavolo': [(950, 1020, 130, 160), (700, 990, 200, 90)]}


def blur_box(im, box, pad=0.6):
    x, y, w, h = box
    x0, y0 = int(x - w * pad / 2), int(y - h * pad / 2)
    x1, y1 = int(x + w * (1 + pad / 2)), int(y + h * (1 + pad / 2))
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return
    reg = im.crop((x0, y0, x1, y1))
    reg = reg.resize((max(1, reg.width // 18), max(1, reg.height // 18)), Image.BILINEAR)
    reg = reg.resize((x1 - x0, y1 - y0), Image.NEAREST).filter(ImageFilter.GaussianBlur(6))
    im.paste(reg, (x0, y0))


def clip(name, k):
    """Frame of clip `name` at k seconds from its start, with logos blurred."""
    if name not in _clip_cache:
        d = os.path.join(CLIP_DIR, name)
        files = sorted(f for f in os.listdir(d) if f.endswith('.jpg'))
        js = os.path.join(CLIP_DIR, name + '.json')
        _clip_cache[name] = ([os.path.join(d, f) for f in files], json.load(open(js)) if os.path.exists(js) else [])
    files, boxes = _clip_cache[name]
    i = min(len(files) - 1, max(0, int(k * FPS)))
    im = Image.open(files[i]).convert('RGB')
    if name not in ('scanner', 'coperchio'):
        blur_box(im, MONITOR_BOX, 0.2)
    for b in boxes:
        blur_box(im, b[i], 1.0)
    for b in STATIC.get(name, []):
        blur_box(im, b, 0.3)
    return im


def real(name, k, zoom=1.0, grade=True):
    im = clip(name, k)
    if zoom != 1.0:
        im = camera(im, zoom)
    if grade:
        im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.25)).enhance(1.12)
    return im.convert('RGBA')


def vignette_bands(c, top=0.55, bot=0.6):
    """Scurisce alto e basso per leggere titoli e didascalie sopra il girato."""
    a = np.zeros((H, 1), np.float32)
    a[:600, 0] = np.linspace(top, 0, 600)
    a[1350:, 0] = np.linspace(0, bot, H - 1350)
    ov = Image.fromarray((np.broadcast_to(a, (H, W)) * 255).astype(np.uint8))
    c.paste(Image.new('RGBA', (W, H), (4, 10, 26, 255)), (0, 0), ov)


def hud(c, t, label):
    """Cornice da registrazione: REC, timecode, angoli verdi."""
    d = ImageDraw.Draw(c)
    L = 70
    for (x, y, sx, sy) in [(60, 170, 1, 1), (W - 60, 170, -1, 1), (60, 1480, 1, -1), (W - 60, 1480, -1, -1)]:
        d.line((x, y, x + L * sx, y), fill=GREEN, width=6)
        d.line((x, y, x, y + L * sy), fill=GREEN, width=6)
    if int(t * 2) % 2 == 0:
        d.ellipse((100, 1405, 128, 1433), fill=RED)
    d.text((140, 1400), 'REC  %s' % label, font=p1.font(FONT_MONO, 34), fill=WHITE)


# ---------- grafiche nostre ----------
def load_card(n):
    files = sorted(os.listdir(os.path.join(HERE, 'commenti')))
    im = Image.open(os.path.join(HERE, 'commenti', [f for f in files if f.startswith(str(n) + '_')][0])).convert('RGB')
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 80, 2))
    pad = 26
    card = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    m = Image.new('L', card.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, card.width - 1, card.height - 1), 34, fill=255)
    bg = Image.new('RGBA', card.size, (20, 20, 22, 255))
    card.paste(bg, (0, 0), m)
    card.paste(im, (pad, pad))
    ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), 34, outline=GREEN, width=4)
    return card


CARDS = {n: load_card(n) for n in range(1, 7)}


def card_in(c, n, t0, t, cy, scale=1.0):
    k = t - t0
    if k < 0:
        return
    s = back_ease(k / 0.3) * scale
    rot = 6 * (1 - ease(k / 0.3))
    paste_scaled(c, CARDS[n], CX, cy, s, rot=rot)


def stamp(c, txt, t0, t, cx, cy, col=GREEN, size=120, rot=-10):
    k = t - t0
    if k < 0:
        return
    s = 2.2 - 1.2 * ease(k / 0.12)
    layer = Image.new('RGBA', (900, 300))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((20, 20, 880, 280), 30, outline=col, width=14)
    draw_text(layer, txt, 450, 150 - size * 0.62, size, fill=col, maxw=800)
    paste_scaled(c, layer, cx, cy, s * 0.8, rot=rot, shadow=False)


def icon_sensor(kind, s=1.0):
    im = Image.new('RGBA', (260, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 6, 254, 254), 40, fill=(12, 30, 60, 235), outline=GREEN, width=6)
    g = GREEN
    if kind == 'temp':
        d.rounded_rectangle((110, 40, 150, 170), 20, outline=g, width=10)
        d.ellipse((88, 150, 172, 234), fill=g)
        d.rectangle((122, 90, 138, 170), fill=g)
    elif kind == 'umid':
        d.polygon([(130, 36), (70, 140), (190, 140)], fill=g)
        d.ellipse((70, 100, 190, 220), fill=g)
    elif kind == 'press':
        d.arc((40, 50, 220, 230), 150, 390, fill=g, width=14)
        d.line((130, 140, 185, 90), fill=g, width=12)
        d.ellipse((115, 125, 145, 155), fill=g)
    else:
        d.ellipse((85, 85, 175, 175), fill=g)
        for j in range(8):
            a = j * math.pi / 4
            d.line((130 + 68 * math.cos(a), 130 + 68 * math.sin(a), 130 + 100 * math.cos(a), 130 + 100 * math.sin(a)),
                   fill=g, width=12)
    return im


SENS = {k: icon_sensor(k) for k in ('temp', 'umid', 'press', 'luce')}


def tv_icon():
    im = Image.new('RGBA', (420, 330), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, 410, 270), 26, fill=(14, 20, 34), outline=GREEN, width=10)
    d.rectangle((40, 40, 380, 240), fill=(30, 60, 100))
    d.line((170, 275, 140, 320), fill=GREEN, width=10)
    d.line((250, 275, 280, 320), fill=GREEN, width=10)
    return im


TV = tv_icon()


def text_lcd(lines):
    """Testo pixel art 84x48 per il display (font bitmap ridotto)."""
    im = Image.new('L', (84, 48), 0)
    d = ImageDraw.Draw(im)
    f = p1.font(FONT_MONO, 11)
    for i, s in enumerate(lines):
        w = p1.text_w(s, f)
        d.text(((84 - w) / 2, 2 + i * 15), s, font=f, fill=255)
    return np.array(im) > 110


LANGS = [text_lcd(x) for x in (['CIAO', 'Italiano'], ['HELLO', 'English'], ['HOLA', 'Espanol'],
                                ['BONJOUR', 'Francais'], ['HALLO', 'Deutsch'], ['OLA', 'Portugues'])]


def phone_falling(t, t0):
    """Il 3310 cade, rimbalza e resta intero: il pavimento si crepa, lui no."""
    k = t - t0
    floor = 1330
    g = 5200
    y0 = 300
    tf = math.sqrt(2 * (floor - y0) / g)
    if k < tf:
        y = y0 + 0.5 * g * k * k
        rot = 200 * k
        crack = 0
    else:
        kk = k - tf
        v = g * tf * 0.42
        y = floor - max(0, v * kk - 0.5 * g * kk * kk)
        if v * kk - 0.5 * g * kk * kk < 0:
            y = floor
        rot = 200 * tf + 30 * math.sin(kk * 10) * math.exp(-kk * 3)
        crack = ease(kk / 0.15)
    return y, rot, crack, k >= tf


CRACK = []
_r = np.random.default_rng(3)
for j in range(9):
    a = -math.pi + j * math.pi / 8 + _r.uniform(-0.1, 0.1)
    pts = [(0, 0)]
    for s in range(5):
        r = 60 * (s + 1) + _r.uniform(-15, 15)
        pts.append((r * math.cos(a + _r.uniform(-0.2, 0.2)), r * 0.35 * math.sin(a + _r.uniform(-0.2, 0.2))))
    CRACK.append(pts)


# ---------- scene ----------
def make_cracks(seed, cx, cy, n=14, reach=900):
    rng = np.random.default_rng(seed)
    segs = []
    for j in range(n):
        a = j * 2 * math.pi / n + rng.uniform(-0.2, 0.2)
        x, y, r = cx, cy, 0
        while r < reach:
            st = rng.uniform(50, 110)
            a += rng.uniform(-0.35, 0.35)
            nx, ny = x + st * math.cos(a), y + st * math.sin(a)
            r += st
            segs.append((r, (x, y, nx, ny)))
            if rng.random() < 0.18:
                b = a + rng.choice([-1, 1]) * rng.uniform(0.6, 1.1)
                segs.append((r + 60, (nx, ny, nx + 90 * math.cos(b), ny + 90 * math.sin(b))))
            x, y = nx, ny
    for k in range(1, 5):
        rr = 90 * k + rng.uniform(-20, 20)
        pts = [(cx + rr * math.cos(q * 2 * math.pi / n), cy + rr * math.sin(q * 2 * math.pi / n)) for q in range(n + 1)]
        for q in range(n):
            if rng.random() < 0.7:
                segs.append((rr + 40, pts[q] + pts[q + 1]))
    return segs


CRACKS = [make_cracks(5, 620, 820), make_cracks(9, 430, 1150)]


def draw_cracks(c, segs, grow):
    ov = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(ov)
    lim = 1100 * grow
    for r, seg in segs:
        if r <= lim:
            d.line(seg, fill=(0, 0, 0, 170), width=9)
            d.line(seg, fill=(235, 245, 255, 235), width=3)
    c.alpha_composite(ov)


_sp = np.random.default_rng(11)
SPARKS = [(_sp.uniform(0, 2 * math.pi), _sp.uniform(700, 1900), _sp.uniform(0.3, 1.0)) for _ in range(90)]
FLY = [(n, _sp.uniform(0, 2 * math.pi), _sp.uniform(500, 1100), _sp.uniform(-400, 400)) for n in
       ['back', 'front', 'keys', 'batt', 'pcb', 'ui', 'chassis']]


def sparks(c, k, cx, cy):
    d = ImageDraw.Draw(c)
    for a, v, life in SPARKS:
        if k > life:
            continue
        r0, r1 = v * k, v * k + 60
        g = 600 * k * k
        col = (255, int(220 - 150 * k / life), 80)
        d.line((cx + r0 * math.cos(a), cy + r0 * math.sin(a) + g, cx + r1 * math.cos(a), cy + r1 * math.sin(a) + g),
               fill=col, width=6)


def hook_title(c, t):
    draw_text(c, 'HO DISTRUTTO', CX, 175, 150, fill=WHITE, stroke=9, stroke_fill=(5, 12, 28))
    draw_text(c, 'UN 3310!', CX, 335, 190, fill=RED if int(t * 6) % 2 else GREEN, stroke=10, stroke_fill=(5, 12, 28))


T_BOOM = 0.75


def sc_hook(t):
    if t < T_BOOM:
        # girato vero, il vetro si crepa gia' dal primo fotogramma
        c = real('pcb_hook', t, zoom=1.3 + 0.2 * t)
        c = Image.blend(c, Image.new('RGBA', (W, H), (120, 0, 10, 255)), 0.18)
        draw_cracks(c, CRACKS[0], 0.45 + ease(t / 0.5))
    elif t < 1.55:
        # esplosione: il 3310 vola in pezzi
        k = t - T_BOOM
        c = background(t, (40, 6, 12)).convert('RGBA')
        glow = Image.new('RGBA', (W, H))
        r = int(200 + 900 * ease(k / 0.4))
        ImageDraw.Draw(glow).ellipse((CX - r, 950 - r, CX + r, 950 + r), fill=(255, 140, 40, int(200 * (1 - ease(k / 0.7)))))
        c.alpha_composite(glow.filter(ImageFilter.GaussianBlur(80)))
        for n, a, v, spin in FLY:
            e = ease(k / 0.8)
            x = CX + v * e * math.cos(a)
            y = 950 + v * e * math.sin(a) + 500 * k * k
            paste_scaled(c, p1.PIECES[n], x, y, 0.9 + 0.5 * e, rot=spin * k)
        sparks(c, k, CX, 950)
    else:
        k = t - 1.55
        c = real('tavolo', 0.35 + k, zoom=1.15 + 0.12 * k)
        c = ImageEnhance.Color(c).enhance(0.6)
        draw_cracks(c, CRACKS[1], 1.0)
        draw_cracks(c, CRACKS[0], 1.0)
    vignette_bands(c, 0.75, 0.5)
    hook_title(c, t)
    return c, 1.0, 0, 0


def sc_trapianto(t):
    c = background(t, (10, 14, 36))
    k = t - T('solo')
    pcb = real('scheda', 2.0)
    pcb = ImageEnhance.Brightness(pcb).enhance(0.35)
    c.paste(pcb, (0, 0))
    p1.place_phone(c, phone(brain_bits(t)), 0.03 * ease(k / 2))
    # cervello che vola dentro il display
    if t < T('cervello.'):
        kk = ease((t - T('trapianto')) / 0.5)
        b = lcd_img(brain_bits(t), 6)
        paste_scaled(c, b, CX + 420 * (1 - kk), 300 + 600 * kk, 0.4 + 0.6 * (1 - kk), rot=30 * (1 - kk))
    pop_text(c, 'SOLO PER UN', CX, 170, 120, T('solo'), t)
    if t >= T('trapianto'):
        pop_text(c, 'TRAPIANTO', CX, 290, 150, T('trapianto'), t, fill=GREEN)
    if t >= T('cervello.'):
        pop_text(c, 'DI CERVELLO', CX, 440, 120, T('cervello.'), t)
    return c, 1.0 + 0.04 * k, 0, 0


def sc_domanda(t):
    c = background(t, (8, 18, 46))
    y, rot, crack, landed = phone_falling(t, T('ma'))
    d = ImageDraw.Draw(c)
    d.rectangle((0, 1420, W, 1500), fill=(20, 34, 62))
    if crack > 0:
        for pts in CRACK:
            n = max(2, int(len(pts) * crack))
            d.line([(CX + x, 1425 + yy) for x, yy in pts[:n]], fill=(190, 210, 240), width=6)
    ph = phone(LCD['home'][0] if t < T('caduta') else brain_bits(t))
    paste_scaled(c, ph, CX, y - 40, 0.36, rot=rot)
    if landed and t > T('caduta'):
        stamp(c, 'ZERO GRAFFI', T('brutale?') + 0.3, t, CX, 1180, size=110)
    if t < T('anche'):
        pop_text(c, 'MA PRIMA', CX, 190, 150, T('ma'), t)
        pop_text(c, 'DIMMI...', CX, 360, 150, T('dimmi:'), t, fill=GREEN)
    elif t < T('che'):
        pop_text(c, 'AVEVI', CX, 170, 150, T('anche'), t)
        pop_text(c, 'UN 3310?', CX, 330, 190, T('avevi'), t, fill=GREEN)
    elif t < T('e'):
        pop_text(c, 'CHE FINE', CX, 170, 160, T('che'), t)
        pop_text(c, 'HA FATTO?', CX, 340, 170, T('fine'), t, fill=GREEN)
    elif t < T('scrivilo'):
        pop_text(c, 'LA CADUTA', CX, 170, 140, T('caduta'), t)
        pop_text(c, 'PIÙ BRUTALE?', CX, 320, 160, T('brutale?'), t, fill=RED)
    else:
        pop_text(c, 'SCRIVILO', CX, 170, 150, T('scrivilo'), t, fill=GREEN)
        pop_text(c, 'NEI COMMENTI 👇'.replace(' 👇', ''), CX, 330, 130, T('commenti.'), t)
        arrow(c, t, 900, 1300)
    return c, 1.0, 0, 0


def arrow(c, t, x, y):
    d = ImageDraw.Draw(c)
    o = 20 * math.sin(t * 12)
    d.polygon([(x - 50, y + o), (x + 50, y + o), (x, y + 70 + o)], fill=GREEN)
    d.rectangle((x - 18, y - 80 + o, x + 18, y + o), fill=GREEN)


def sc_cover(t):
    k = t - T('via')
    c = real('cover', 0.3 + k * 0.9, zoom=1.3)
    vignette_bands(c)
    hud(c, t, 'SMONTAGGIO 1/4')
    pop_text(c, 'VIA LA COVER', CX, 190, 150, T('via'), t, fill=GREEN)
    return c, 1.05 + 0.05 * k, 0, 0


def sc_batt(t):
    k = t - T('via', 1)
    c = real('batteria', k * 1.1, zoom=1.3)
    vignette_bands(c)
    hud(c, t, 'SMONTAGGIO 2/4')
    pop_text(c, 'VIA LA BATTERIA', CX, 190, 140, T('via', 1), t, fill=GREEN)
    return c, 1.05 + 0.05 * k, 0, 0


def sc_viti(t):
    k = t - T('vite')
    c = real('viti', k * 0.95, zoom=1.35)
    vignette_bands(c)
    hud(c, t, 'SMONTAGGIO 3/4  x74')
    n = min(6, 1 + int(k / (T('fino') - T('vite')) * 6))
    pop_text(c, 'VITE DOPO VITE', CX, 190, 140, T('vite'), t, fill=GREEN)
    draw_text(c, 'TORX T6  %d/6' % n, CX, 1330, 80, fill=WHITE, path=FONT_MONO, stroke=6, stroke_fill=(5, 12, 28))
    return c, 1.0, 0, 0


def sc_scheda(t):
    k = t - T('fino')
    c = real('scheda', k * 0.95 + 0.1, zoom=1.2 + 0.08 * k)
    vignette_bands(c)
    hud(c, t, 'SMONTAGGIO 4/4')
    if t < T('la', 3):
        pop_text(c, 'FINO AL CUORE', CX, 190, 150, T('fino'), t, fill=RED)
    else:
        pop_text(c, 'SCHEDA MADRE', CX, 170, 140, T('la', 3), t, fill=GREEN)
        pop_text(c, 'ORIGINALE', CX, 320, 110, T('originale'), t)
    if t >= T('2000.'):
        stamp(c, 'ANNO 2000', T('2000.'), t, CX, 1250, col=GREEN, size=120)
    return c, 1.0, 0, 0


def sc_scanner(t):
    k = t - T('poi')
    if t < T('600'):
        c = real('scanner', k * 1.0, zoom=1.15)
        vignette_bands(c)
        hud(c, t, 'SCANNER')
        pop_text(c, 'SULLO SCANNER', CX, 190, 140, T('poi'), t, fill=GREEN)
        return c, 1.0, 0, 0
    kk = t - T('600')
    if kk < 0.45:
        c = real('coperchio', 0.6 + kk * 1.2, zoom=1.15)
        c = Image.blend(c.convert('RGB'), Image.new('RGB', (W, H), (230, 255, 210)), 0.5 * ease(kk / 0.45)).convert('RGBA')
    else:
        c = background(t, (8, 20, 44))
        paste_scaled(c, p1.comp, CX + 500 - 700 * ease((kk - 0.45) / 1.2), 900, 1.9, shadow=False)
        p1.scan_beam(c, int(450 + ((kk * 600) % 900)))
    box = Image.new('RGBA', (W, H))
    draw_text(box, '600 DPI', CX, 1120, 230, fill=GREEN, stroke=10, stroke_fill=(5, 12, 28))
    box = camera(box, 1.8 - 0.8 * ease(kk / 0.15))
    c.paste(box, (0, 0), box)
    return c, 1.0, 0, 0


ZOOMS = [('tasto,', p1.PIECES['keys'], 'OGNI TASTO'),
         ('pista,', p1.pcb_scan.crop((260, 300, 860, 900)), 'OGNI PISTA'),
         ('molla.', p1.PIECES['ui'].crop((20, 0, 237, 240)), 'OGNI MOLLA')]


def sc_ogni(t):
    c = background(t, (8, 20, 44))
    cur = ZOOMS[0]
    for z in ZOOMS:
        if t >= T(z[0]) - 0.25:
            cur = z
    k = t - T(cur[0]) + 0.25
    im = cur[1]
    paste_scaled(c, im, CX, 880, (900 / max(im.width, im.height)) * (1.0 + 0.25 * k))
    p1.scan_beam(c, int(450 + ((k * 900) % 900)))
    pop_text(c, cur[2], CX, 200, 160, T(cur[0]) - 0.25, t, fill=GREEN)
    return c, 1.0, 0, 0


def sc_wall(t):
    c = background(t, (10, 22, 52))
    k = t - T('e', 1)
    pos = [(-1, 600), (1, 820), (-1, 1040), (1, 1260), (-1, 1480), (1, 380)]
    for i, n in enumerate([2, 3, 4, 5, 1, 6]):
        kk = ease((k - i * 0.12) / 0.35)
        side, y = pos[i]
        x = CX + side * 1100 * (1 - kk) + side * 40
        paste_scaled(c, CARDS[n], x, y - 120 * k, 0.85, rot=side * 3)
    ov = Image.new('RGBA', (W, H), (4, 10, 26, 110))
    c.paste(ov, (0, 0), ov)
    if t < T('idee'):
        pop_text(c, 'I VOSTRI', CX, 640, 160, T('e', 1), t)
        pop_text(c, 'COMMENTI?', CX, 820, 190, T('vostri'), t, fill=GREEN)
    else:
        pop_text(c, 'IDEE', CX, 600, 230, T('idee'), t)
        pop_text(c, 'PAZZESCHE!', CX, 840, 210, T('pazzesche!'), t, fill=GREEN)
    return c, 1.0 + 0.05 * k, 0, 0


def sc_sensori(t):
    c = background(t)
    card_in(c, 3, T('sensori?') - 0.1, t, 330, 0.95)
    keys = [('temperatura,', 'temp', 'TEMPERATURA'), ('umidità,', 'umid', 'UMIDITÀ'),
            ('pressione', 'press', 'PRESSIONE'), ('luce', 'luce', 'LUCE')]
    if t < T('ma', 1):
        if t >= T('nessuno'):
            pop_text(c, 'NESSUNO SMARTPHONE', CX, 560, 90, T('nessuno'), t, fill=RED)
        for i, (w, ic, lab) in enumerate(keys):
            if t >= T(w):
                kk = back_ease((t - T(w)) / 0.3)
                x = CX + (i % 2 * 2 - 1) * 230
                y = 860 + (i // 2) * 360
                paste_scaled(c, SENS[ic], x, y, 1.0 * kk)
                draw_text(c, lab, x, y + 150, 46, fill=WHITE, path=FONT_BOLD, maxw=420)
    else:
        k = t - T('ma', 1)
        p1.place_phone(c, phone(LCD['home'][0]), 0.0, 560, 1460)
        for i, ic in enumerate(SENS):
            a = k * 2.5 + i * math.pi / 2
            paste_scaled(c, SENS[ic], CX + 380 * math.cos(a), 1000 + 300 * math.sin(a), 0.6)
        pop_text(c, 'IL 3310 PUÒ.', CX, 560, 120, T('può.'), t, fill=GREEN)
    return c, 1.0, 0, 0


def sc_claude(t):
    c = background(t, (12, 16, 40))
    card_in(c, 2, T('claude') - 0.1, t, 330, 0.95)
    k = t - T('claude')
    ph = phone(LCD['assist'][min(len(LCD['assist']) - 1, 40 + int(k * 20))])
    p1.place_phone(c, p1.phone_top(ph), 0.0, 620, 1460)
    if t < T('il', 1):
        pop_text(c, 'NON È NEMMENO', CX, 560, 90, T('non'), t)
        if t >= T('smartphone.', 1):
            stamp(c, 'SMARTPHONE?', T('smartphone.', 1), t, CX, 1250, col=RED, size=110)
    else:
        pop_text(c, 'PIÙ DI UNO', CX, 540, 110, T('il', 1), t, fill=GREEN)
        pop_text(c, 'SMARTPHONE', CX, 1240, 150, T('smartphone.', 2), t, fill=GREEN)
    return c, 1.0 + 0.03 * k, 0, 0


def sc_snake(t):
    c = background(t)
    card_in(c, 4, T('più', 2) - 0.1, t, 330, 0.95)
    k = t - T('più', 2)
    if t < T('e', 2):
        bits = LANGS[int(k * 5) % len(LANGS)]
        paste_scaled(c, lcd_img(bits, 10), CX, 950, 1.0)
        pop_text(c, 'PIÙ LINGUE? CERTO.', CX, 1310, 100, T('certo.'), t, fill=GREEN)
    else:
        kk = t - T('e', 2)
        bits = p1.lcd_frame('snake', int(kk * 30))
        paste_scaled(c, lcd_img(bits, 10), CX, 950, 1.0 + 0.08 * kk)
        if t < T('il', 2):
            pop_text(c, 'SNAKE?', CX, 1290, 190, T('snake'), t, fill=GREEN)
        elif t < T('ma', 2):
            pop_text(c, 'ANCHE', CX, 1230, 120, T('anche', 1), t)
            pop_text(c, 'SU MARTE', CX, 1360, 150, T('marte'), t, fill=RED)
        else:
            pop_text(c, 'SENZA SNAKE', CX, 1250, 130, T('senza'), t, fill=RED)
            pop_text(c, 'NON È UN 3310', CX, 1390, 100, T('non', 1), t)
    return c, 1.0, 0, 0


def sc_tv(t):
    c = background(t)
    card_in(c, 5, T('telecomando') - 0.1, t, 330, 0.95)
    k = t - T('telecomando')
    ph = phone(LCD['home'][0])
    paste_scaled(c, ph, 300, 1050, 0.3, rot=-20)
    paste_scaled(c, TV, 790, 900, 0.85)
    d = ImageDraw.Draw(c)
    if t >= T('ve'):
        for i in range(4):
            r = 60 + ((k * 260 + i * 70) % 280)
            col = tuple(int(v * (1 - (r - 60) / 280)) for v in RED)
            d.arc((360 - r, 860 - r, 360 + r, 860 + r), 300, 360, fill=col, width=10)
    if t >= T('fare.'):
        d.rectangle((580, 800, 1000, 1000), fill=GREEN)
        draw_text(c, 'ON', 790, 860, 70, fill=BLUE, path=FONT_BOLD)
        stamp(c, 'SI PUÒ FARE', T('fare.'), t, CX, 1350, size=110)
    else:
        pop_text(c, 'TELECOMANDO TV?', CX, 560, 100, T('telecomando'), t, fill=GREEN)
    return c, 1.0, 0, 0


def sc_meme(t):
    c = background(t, (6, 12, 30))
    k = t - T('il', 3)
    p1.place_phone(c, phone(brain_bits(t)), 0.02 * k, 620, 1460)
    pop_text(c, 'INDISTRUTTIBILE', CX, 190, 130, T('indistruttibile.'), t, fill=WHITE)
    if t >= T('adesso'):
        d = ImageDraw.Draw(c)
        p = ease((t - T('adesso')) / 0.2)
        d.line((CX - 470, 270, CX - 470 + 940 * p, 270), fill=RED, width=16)
        pop_text(c, 'INSUPERABILE', CX, 370, 150, T('insuperabile.'), t, fill=GREEN)
    return c, 1.0 + 0.03 * k, 0, 0


def sc_next(t):
    c = background(t, (8, 18, 46))
    k = t - T('nella')
    for i, n in enumerate([3, 2, 4, 5]):
        a = k * 0.8 + i * math.pi / 2
        paste_scaled(c, CARDS[n], CX + 300 * math.cos(a), 1000 + 360 * math.sin(a), 0.5, alpha=0.75)
    s = back_ease((t - T('progettare')) / 0.4) if t >= T('progettare') else 0
    if s > 0:
        paste_scaled(c, p1.CHIP, CX, 1000, 0.75 * s)
    if t < T('intanto'):
        pop_text(c, 'PROSSIMA PARTE', CX, 170, 120, T('nella'), t)
        pop_text(c, 'PROGETTIAMO', CX, 320, 140, T('progettare'), t, fill=GREEN)
        pop_text(c, 'IL CERVELLO', CX, 470, 120, T('cervello', 1), t)
    else:
        pop_text(c, 'CONTINUA A', CX, 170, 130, T('intanto'), t)
        pop_text(c, 'COMMENTARE', CX, 320, 160, T('continuate'), t, fill=GREEN)
        arrow(c, t, 900, 1330)
    return c, 1.0 + 0.03 * k, 0, 0


def sc_like(t):
    c = background(t, (10, 22, 52))
    k = t - T('lascia')
    s = back_ease(k / 0.3)
    r = int(170 * s * (1 + 0.08 * math.sin(k * 10)))
    p1.heart(c, CX, 820, r, (255, 70, 110))
    for j in range(8):
        a = j * math.pi / 4 + k
        rr = 220 + 160 * ease(k / 0.6)
        p1.heart(c, CX + rr * math.cos(a), 800 + rr * math.sin(a) * 0.7, int(34 * (1 - ease(k / 1.2))), GREEN)
    pop_text(c, 'LASCIA UN LIKE', CX, 190, 130, T('lascia'), t)
    if t >= T('seguimi'):
        kk = back_ease((t - T('seguimi')) / 0.3)
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((CX - 300 * kk, 1150, CX + 300 * kk, 1290), 40, fill=RED)
        if kk > 0.8:
            draw_text(c, '+ SEGUI', CX, 1170, 90, fill=WHITE, path=FONT_BOLD)
        pop_text(c, 'SUPPORTA IL PROGETTO', CX, 1330, 80, T('supportare'), t, fill=GREEN)
    return c, 1.0, 0, 0


def sc_outro(t):
    c, z, dx, dy = p1.sc_outro(t)
    # la Parte 1 annunciava la 2: qui si copre e si scrive la 3
    k = t - OUTRO
    if k > 1.9:
        s = back_ease((k - 1.9) / 0.35)
        d = ImageDraw.Draw(c)
        w2, h2 = 380 * s, 70 * s
        d.rounded_rectangle((CX - w2, 1180 - h2, CX + w2, 1180 + h2), int(40 * s), fill=GREEN)
        if s > 0.8:
            draw_text(c, 'PARTE 3 IN ARRIVO', CX, 1145, 66, fill=BLUE, path=FONT_BOLD)
    return c, z, dx, dy


p1.OUTRO = OUTRO

SCENES = [
    (0.0, sc_hook), (T('solo') - 0.1, sc_trapianto), (T('ma') - 0.1, sc_domanda), (T('via') - 0.05, sc_cover),
    (T('via', 1) - 0.05, sc_batt), (T('vite') - 0.05, sc_viti), (T('fino') - 0.05, sc_scheda),
    (T('poi') - 0.05, sc_scanner), (T('ogni', 1) - 0.25, sc_ogni), (T('e', 1) - 0.1, sc_wall),
    (T('sensori?') - 0.1, sc_sensori), (T('claude') - 0.1, sc_claude), (T('più', 2) - 0.1, sc_snake),
    (T('telecomando') - 0.1, sc_tv), (T('il', 3) - 0.1, sc_meme), (T('nella') - 0.1, sc_next),
    (T('lascia') - 0.1, sc_like), (OUTRO, sc_outro),
]
CUTS = [s[0] for s in SCENES[1:]] + [1.55]
HITS = [T_BOOM, 0.05] + [T(w) for w in ['distrutto', 'cervello.', 'brutale?', 'cuore.', '2000.', '600', 'pazzesche!', 'può.',
                       'insuperabile.', 'like']]
HITS += [T('smartphone.', 2), T('snake', 1), T('fare.'), T('indistruttibile.')]


def scene_at(t):
    cur = SCENES[0]
    for s in SCENES:
        if t >= s[0]:
            cur = s
    return cur


def captions(c, t):
    line = None
    for ln in LINES:
        if ln[0][1] - 0.05 <= t <= ln[-1][2] + 0.35:
            line = ln
    if not line:
        return
    f = p1.font(FONT_BOLD, 66)
    words = [w[0] for w in line]
    widths = [p1.text_w(w, f) for w in words]
    sp = 22
    total = sum(widths) + sp * (len(words) - 1)
    size = 66
    if total > p1.SAFE_R - p1.SAFE_L - 40:
        size = int(66 * (p1.SAFE_R - p1.SAFE_L - 40) / total)
        f = p1.font(FONT_BOLD, size)
        widths = [p1.text_w(w, f) for w in words]
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
            p1.cap_word(d, x, y - 6 * k, w, f, BLUE, 0)
        else:
            col = WHITE if t >= a else (150, 160, 175)
            p1.cap_word(d, x, y, w, f, col, 5)
        x += wd + sp


def render(i):
    t = i / FPS
    start, fn = scene_at(t)
    c, z, dx, dy = fn(t)
    c = c.convert('RGB')
    hit = min([t - h for h in HITS if t >= h] or [9])
    shake = max(0, 1 - hit / 0.25)
    if t < T('solo'):
        shake = max(shake, 0.35)
    if shake > 0:
        rng = np.random.default_rng(i)
        dx += rng.uniform(-18, 18) * shake
        dy += rng.uniform(-18, 18) * shake
        z *= 1 + 0.05 * shake
    c = camera(c, z, dx, dy)
    since_cut = min([t - x for x in CUTS if t >= x] or [9])
    if since_cut < 0.08:
        c = p1.pixelate(c, 1 - since_cut / 0.08)
    if since_cut < 0.18 or shake > 0.6:
        c = p1.glitch(c, max(1 - since_cut / 0.18, shake * 0.6), i)
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


def music():
    p1.DUR_V, p1.OUTRO, p1.SR, p1.VOICE = DUR_V, OUTRO, SR, VOICE
    p1.HITS, p1.CUTS = HITS, CUTS
    return p1.music()


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
    os.makedirs(os.path.join(HERE, 'pubblicato'), exist_ok=True)
    dst = os.path.join(HERE, 'pubblicato', 'parte2.mp4')
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
