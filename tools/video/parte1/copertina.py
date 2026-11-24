"""Cover 1080x1920 for the TikTok/Reels post. Everything that matters stays in the central
1080x1080 square (y 420-1500), so the 1:1 and 3:4 grid thumbnails keep title and phone."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.argv = sys.argv[:1]
import monta as m
from cervello import brain_bits

W, H = 1080, 1920
SQ0, SQ1 = 420, 1500

y, x = np.mgrid[0:H, 0:W].astype(np.float32)
r = np.hypot((x - W / 2) / W, (y - 960) / H) * 2
bg = np.array(m.BLUE, np.float32) * (1.3 - 0.6 * r[..., None]) + np.array(m.BLUE2, np.float32) * 0.5 * (1 - r[..., None]).clip(0, 1)
img = Image.fromarray(bg.clip(0, 255).astype(np.uint8)).convert('RGBA')

# light grid, like the video background
grid = Image.new('RGBA', (W, H))
gd = ImageDraw.Draw(grid)
for gx in range(0, W, 40):
    gd.line((gx, 0, gx, H), fill=(255, 255, 255, 10))
for gy in range(0, H, 40):
    gd.line((0, gy, W, gy), fill=(255, 255, 255, 10))
img = Image.alpha_composite(img, grid)

ph = m.phone(brain_bits(0.6), on=1.0)
s = 640 / ph.height
ph = ph.resize((int(ph.width * s), int(ph.height * s)), Image.LANCZOS).rotate(-8, resample=Image.BICUBIC, expand=True)
cx, cy = W // 2, 960
x0, y0 = cx - ph.width // 2, cy - ph.height // 2

glow = Image.new('RGBA', (W, H))
ImageDraw.Draw(glow).ellipse((cx - 330, cy - 330, cx + 330, cy + 250), fill=m.GREEN + (110,))
img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(110)))

# sparks around the phone
sp = Image.new('RGBA', (W, H))
sd = ImageDraw.Draw(sp)
for ax, ay, l in ((cx - 300, cy - 230, 46), (cx + 290, cy - 260, 38), (cx - 330, cy + 120, 30), (cx + 320, cy + 90, 42)):
    sd.line((ax - l, ay, ax + l, ay), fill=m.GREEN + (230,), width=8)
    sd.line((ax, ay - l, ax, ay + l), fill=m.GREEN + (230,), width=8)
img = Image.alpha_composite(img, sp)

sh = Image.new('RGBA', ph.size, (0, 0, 0, 0))
sh.putalpha(ph.getchannel('A').point(lambda v: int(v * 0.6)))
img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(20)), (x0 + 18, y0 + 26))
img.alpha_composite(ph, (x0, y0))

c = img.convert('RGB')
m.draw_text(c, 'AI SU UN', W // 2, SQ0 + 40, 150, fill=m.GREEN, stroke=10, stroke_fill=(5, 12, 30))
m.draw_text(c, 'NOKIA 3310?', W // 2, SQ1 - 225, 170, fill=m.WHITE, stroke=10, stroke_fill=(5, 12, 30))

# outside the square: extras that may be cropped in the grid
d = ImageDraw.Draw(c)
f = m.font(m.FONT_BOLD, 54)
label = 'PARTE 1'
tw = m.text_w(label, f)
d.rounded_rectangle((W // 2 - tw // 2 - 34, 230, W // 2 + tw // 2 + 34, 316), radius=43, fill=m.GREEN)
d.text((W // 2, 273), label, font=f, fill=(5, 12, 30), anchor='mm')
m.draw_text(c, 'gli do un cervello nuovo', W // 2, 1560, 64, fill=m.WHITE, path=m.FONT_BOLD)

out = os.path.join(m.HERE, 'pubblicato', 'copertina_parte1.png')
c.save(out)
c.crop((0, SQ0, W, SQ1)).save(os.path.join(m.OUT, 'copertina_parte1_1x1.png'))
c.crop((0, 240, W, 1680)).resize((540, 720), Image.LANCZOS).save(os.path.join(m.OUT, 'copertina_parte1_3x4.png'))
print(out)
