"""Shared engine for the AurI-3310 videos: graphics from parte1, real clips, captions, effects, audio, render.

A part's monta.py does:  v = Video(__file__, fix={...}); define scenes using v.T(...); v.run(SCENES, HITS)
"""
import importlib.util
import json
import math
import os
import subprocess
import sys
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

VIDEO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, VIDEO)

_spec = importlib.util.spec_from_file_location('p1', os.path.join(VIDEO, 'parte1', 'monta.py'))
p1 = importlib.util.module_from_spec(_spec)
_argv, sys.argv = sys.argv, sys.argv[:1]
_spec.loader.exec_module(p1)
sys.argv = _argv
from cervello import brain_bits  # noqa: E402

W, H, FPS, CX = p1.W, p1.H, p1.FPS, p1.CX
BLUE, GREEN, WHITE, LCD_BG, LCD_FG = p1.BLUE, p1.GREEN, p1.WHITE, p1.LCD_BG, p1.LCD_FG
RED = (255, 70, 90)
FONT_BIG, FONT_BOLD, FONT_MONO = p1.FONT_BIG, p1.FONT_BOLD, p1.FONT_MONO
ease, back_ease, pop_text, draw_text = p1.ease, p1.back_ease, p1.pop_text, p1.draw_text
paste_scaled, background, camera, phone, lcd_img = p1.paste_scaled, p1.background, p1.camera, p1.phone, p1.lcd_img
place_phone, phone_top, lcd_frame, heart, scan_beam = p1.place_phone, p1.phone_top, p1.lcd_frame, p1.heart, p1.scan_beam
LCD, PIECES, CHIP = p1.LCD, p1.PIECES, p1.CHIP
MONITOR_BOX = (360, 570, 300, 80)
STRIP = '.,?!:'


class Video:
    def __init__(self, monta_file, fix=None, rules=None, static_boxes=None, no_monitor=()):
        self.here = os.path.dirname(os.path.abspath(monta_file))
        self.out = os.path.join(self.here, 'out')
        raw = json.load(open(os.path.join(self.out, 'parole.json'), encoding='utf-8'))
        fix = fix or {}
        self.words = [[fix.get(w, w), a, b] for w, a, b in raw]
        if rules:
            rules(self.words)
        wf = wave.open(os.path.join(self.out, 'voce_Fenrir.wav'))
        self.sr = wf.getframerate()
        self.voice = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
        self.dur = len(self.voice) / self.sr
        self.outro = self.dur + 0.1
        self.dur_v = self.dur + 3.8
        self.nf = int(round(self.dur_v * FPS))
        self.lines, cur = [], []
        for w in self.words:
            cur.append(w)
            if w[0][-1] in STRIP or len(cur) >= 3:
                self.lines.append(cur)
                cur = []
        if cur:
            self.lines.append(cur)
        self.static = static_boxes or {}
        self.no_monitor = set(no_monitor)
        self._clips = {}
        self.cards = {}
        p1.OUTRO = self.outro

    def T(self, word, nth=0):
        """Start time of the nth occurrence of a word (case and punctuation ignored)."""
        hits = [x for x in self.words if x[0].lower().strip(STRIP) == word.lower().strip(STRIP)]
        if len(hits) <= nth:
            raise KeyError('%s #%d (found %d)' % (word, nth, len(hits)))
        return hits[nth][1]

    # ---------- real footage ----------
    def clip(self, name, k):
        if name not in self._clips:
            d = os.path.join(self.out, 'clip', name)
            files = sorted(f for f in os.listdir(d) if f.endswith('.jpg'))
            js = os.path.join(self.out, 'clip', name + '.json')
            self._clips[name] = ([os.path.join(d, f) for f in files], json.load(open(js)) if os.path.exists(js) else [])
        files, boxes = self._clips[name]
        i = min(len(files) - 1, max(0, int(k * FPS)))
        im = Image.open(files[i]).convert('RGB')
        if name not in self.no_monitor:
            blur_box(im, MONITOR_BOX, 0.2)
        for b in boxes:
            blur_box(im, b[i], 1.0)
        for b in self.static.get(name, []):
            blur_box(im, b, 0.3)
        return im

    def real(self, name, k, zoom=1.0):
        im = self.clip(name, k)
        if zoom != 1.0:
            im = camera(im, zoom)
        im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.25)).enhance(1.12)
        return im.convert('RGBA')

    # ---------- comment screenshots (commenti/N_nome.png) ----------
    def card(self, n):
        if n not in self.cards:
            self.cards[n] = load_card(os.path.join(self.here, 'commenti'), n)
        return self.cards[n]

    def card_in(self, c, n, t0, t, cy, scale=1.0):
        k = t - t0
        if k >= 0:
            paste_scaled(c, self.card(n), CX, cy, back_ease(k / 0.3) * scale, rot=6 * (1 - ease(k / 0.3)))

    # ---------- captions, render, audio ----------
    def captions(self, c, t):
        line = None
        for ln in self.lines:
            if ln[0][1] - 0.05 <= t <= ln[-1][2] + 0.35:
                line = ln
        if not line:
            return
        size, sp = 66, 22
        f = p1.font(FONT_BOLD, size)
        widths = [p1.text_w(w[0], f) for w in line]
        total = sum(widths) + sp * (len(line) - 1)
        if total > p1.SAFE_R - p1.SAFE_L - 40:
            size = int(66 * (p1.SAFE_R - p1.SAFE_L - 40) / total)
            f = p1.font(FONT_BOLD, size)
            widths = [p1.text_w(w[0], f) for w in line]
            total = sum(widths) + sp * (len(line) - 1)
        y, x = 1525, CX - total / 2
        d = ImageDraw.Draw(c)
        for (w, a, b), wd in zip(line, widths):
            nxt = [w2[1] for w2 in self.words if w2[1] > a]
            if a <= t < (nxt[0] if nxt else b + 0.5):
                k = ease((t - a) / 0.1)
                d.rounded_rectangle((x - 12, y - 6 - 6 * k, x + wd + 12, y + size * 1.25 + 4), 14, fill=GREEN)
                p1.cap_word(d, x, y - 6 * k, w, f, BLUE, 0)
            else:
                p1.cap_word(d, x, y, w, f, WHITE if t >= a else (150, 160, 175), 5)
            x += wd + sp

    def render(self, i, scenes, hits, cuts, shake_until=0.0):
        t = i / FPS
        fn = [s for s in scenes if t >= s[0]][-1][1]
        c, z, dx, dy = fn(t)
        c = c.convert('RGB')
        hit = min([t - h for h in hits if t >= h] or [9])
        shake = max(0, 1 - hit / 0.25)
        if t < shake_until:
            shake = max(shake, 0.35)
        if shake > 0:
            rng = np.random.default_rng(i)
            dx += rng.uniform(-18, 18) * shake
            dy += rng.uniform(-18, 18) * shake
            z *= 1 + 0.05 * shake
        c = camera(c, z, dx, dy)
        since_cut = min([t - x for x in cuts if t >= x] or [9])
        if since_cut < 0.08:
            c = p1.pixelate(c, 1 - since_cut / 0.08)
        if since_cut < 0.18 or shake > 0.6:
            c = p1.glitch(c, max(1 - since_cut / 0.18, shake * 0.6), i)
        if hit < 0.08:
            c = Image.blend(c, Image.new('RGB', (W, H), (230, 255, 210)), 0.6 * (1 - hit / 0.08))
        a = np.array(c)
        a[::4] = (a[::4] * 0.9).astype(np.uint8)
        c = Image.fromarray(a)
        self.captions(c, t)
        d = ImageDraw.Draw(c)
        d.rectangle((0, 1672, W, 1680), fill=(30, 45, 80))
        d.rectangle((0, 1672, int(W * t / self.dur_v), 1680), fill=GREEN)
        return c

    def run(self, scenes, hits, extra_cuts=(), shake_until=0.0, name='video'):
        """`monta.py 1.5 20` saves previews in out/prova/; `monta.py` renders pubblicato/<name>.mp4."""
        scenes = sorted(scenes + [(self.outro, self.sc_outro)], key=lambda s: s[0])
        cuts = [s[0] for s in scenes[1:]] + list(extra_cuts)
        r = lambda i: self.render(i, scenes, hits, cuts, shake_until)
        only = [float(x) for x in sys.argv[1:]]
        if only:
            os.makedirs(os.path.join(self.out, 'prova'), exist_ok=True)
            for s in only:
                r(int(s * FPS)).save(os.path.join(self.out, 'prova', '%05.2f.png' % s))
            sheet(os.path.join(self.out, 'prova'))
            return
        p1.DUR_V, p1.OUTRO, p1.SR, p1.VOICE, p1.HITS, p1.CUTS = self.dur_v, self.outro, self.sr, self.voice, hits, cuts
        mix = np.pad(self.voice, (0, int(self.dur_v * self.sr) - len(self.voice))) + p1.music()
        mix = mix / max(1.0, np.abs(mix).max() / 0.98)
        wav = os.path.join(self.out, 'mix.wav')
        with wave.open(wav, 'wb') as o:
            o.setnchannels(1)
            o.setsampwidth(2)
            o.setframerate(self.sr)
            o.writeframes((mix * 32767).astype(np.int16).tobytes())
        os.makedirs(os.path.join(self.here, 'pubblicato'), exist_ok=True)
        dst = os.path.join(self.here, 'pubblicato', name + '.mp4')
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        p = subprocess.Popen([ff, '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS),
                              '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                              '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                              '-t', '%.3f' % self.dur_v, '-movflags', '+faststart', dst], stdin=subprocess.PIPE)
        for i in range(self.nf):
            p.stdin.write(r(i).tobytes())
            if i % 300 == 0:
                print(i, '/', self.nf, flush=True)
        p.stdin.close()
        p.wait()
        print('ok', dst, round(self.dur_v, 1))

    def sc_outro(self, t, next_label=None):
        c, z, dx, dy = p1.sc_outro(t)
        k = t - self.outro
        label = next_label or getattr(self, 'next_label', None)
        if label and k > 1.9:
            s = back_ease((k - 1.9) / 0.35)
            d = ImageDraw.Draw(c)
            d.rounded_rectangle((CX - 380 * s, 1180 - 70 * s, CX + 380 * s, 1180 + 70 * s), int(40 * s), fill=GREEN)
            if s > 0.8:
                draw_text(c, label, CX, 1145, 66, fill=BLUE, path=FONT_BOLD)
        return c, z, dx, dy


# ---------- standalone helpers ----------
def blur_box(im, box, pad=0.6):
    x, y, w, h = box
    x0, y0 = max(0, int(x - w * pad / 2)), max(0, int(y - h * pad / 2))
    x1, y1 = min(W, int(x + w * (1 + pad / 2))), min(H, int(y + h * (1 + pad / 2)))
    if x1 <= x0 or y1 <= y0:
        return
    reg = im.crop((x0, y0, x1, y1))
    reg = reg.resize((max(1, reg.width // 18), max(1, reg.height // 18)), Image.BILINEAR)
    im.paste(reg.resize((x1 - x0, y1 - y0), Image.NEAREST).filter(ImageFilter.GaussianBlur(6)), (x0, y0))


def vignette_bands(c, top=0.55, bot=0.6):
    """Darkens top and bottom so titles and captions read over real footage."""
    a = np.zeros((H, 1), np.float32)
    a[:600, 0] = np.linspace(top, 0, 600)
    a[1350:, 0] = np.linspace(0, bot, H - 1350)
    ov = Image.fromarray((np.broadcast_to(a, (H, W)) * 255).astype(np.uint8))
    c.paste(Image.new('RGBA', (W, H), (4, 10, 26, 255)), (0, 0), ov)


def hud(c, t, label):
    d = ImageDraw.Draw(c)
    for (x, y, sx, sy) in [(60, 170, 1, 1), (W - 60, 170, -1, 1), (60, 1480, 1, -1), (W - 60, 1480, -1, -1)]:
        d.line((x, y, x + 70 * sx, y), fill=GREEN, width=6)
        d.line((x, y, x, y + 70 * sy), fill=GREEN, width=6)
    if int(t * 2) % 2 == 0:
        d.ellipse((100, 1405, 128, 1433), fill=RED)
    d.text((140, 1400), 'REC  %s' % label, font=p1.font(FONT_MONO, 34), fill=WHITE)


def load_card(folder, n):
    f = [x for x in sorted(os.listdir(folder)) if x.startswith(str(n) + '_')][0]
    im = Image.open(os.path.join(folder, f)).convert('RGB')
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 80, 2))
    pad = 26
    card = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    m = Image.new('L', card.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, card.width - 1, card.height - 1), 34, fill=255)
    card.paste(Image.new('RGBA', card.size, (20, 20, 22, 255)), (0, 0), m)
    card.paste(im, (pad, pad))
    ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), 34, outline=GREEN, width=4)
    return card


def stamp(c, txt, t0, t, cx, cy, col=GREEN, size=120, rot=-10):
    k = t - t0
    if k < 0:
        return
    layer = Image.new('RGBA', (900, 300))
    ImageDraw.Draw(layer).rounded_rectangle((20, 20, 880, 280), 30, outline=col, width=14)
    draw_text(layer, txt, 450, 150 - size * 0.62, size, fill=col, maxw=800)
    paste_scaled(c, layer, cx, cy, (2.2 - 1.2 * ease(k / 0.12)) * 0.8, rot=rot, shadow=False)


def arrow(c, t, x, y):
    d = ImageDraw.Draw(c)
    o = 20 * math.sin(t * 12)
    d.polygon([(x - 50, y + o), (x + 50, y + o), (x, y + 70 + o)], fill=GREEN)
    d.rectangle((x - 18, y - 80 + o, x + 18, y + o), fill=GREEN)


def text_lcd(lines):
    """Pixel-art text 84x48 for the display."""
    im = Image.new('L', (84, 48), 0)
    d = ImageDraw.Draw(im)
    f = p1.font(FONT_MONO, 11)
    for i, s in enumerate(lines):
        d.text(((84 - p1.text_w(s, f)) / 2, 2 + i * 15), s, font=f, fill=255)
    return np.array(im) > 110


def sheet(folder, cols=9):
    """Contact sheet of the previews, to check many frames with a single image."""
    fs = sorted(f for f in os.listdir(folder) if f[0].isdigit())
    if not fs:
        return
    rows = (len(fs) + cols - 1) // cols
    s = Image.new('RGB', (cols * 270, rows * 500), 'white')
    for i, f in enumerate(fs):
        s.paste(Image.open(os.path.join(folder, f)).resize((270, 480)), ((i % cols) * 270, (i // cols) * 500))
        ImageDraw.Draw(s).text(((i % cols) * 270 + 5, (i // cols) * 500 + 482), f, fill='black')
    s.save(os.path.join(folder, '_anteprime.png'))
