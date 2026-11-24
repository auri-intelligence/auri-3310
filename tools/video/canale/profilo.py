import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

_here = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(_here, '..', 'parte1'), os.path.join(_here, '..')]
sys.argv = sys.argv[:1]
import monta as m
from cervello import brain_bits

S = 1080
y, x = np.mgrid[0:S, 0:S].astype(np.float32)
r = np.hypot(x - S / 2, y - S / 2) / (S / 2)
bg = np.array(m.BLUE, np.float32) * (1.25 - 0.45 * r[..., None]) + np.array(m.BLUE2, np.float32) * 0.4 * (1 - r[..., None]).clip(0, 1)
img = Image.fromarray(bg.clip(0, 255).astype(np.uint8)).convert('RGBA')

ph = m.phone(brain_bits(0.3), on=1.0)
s = 860 / ph.height
ph = ph.resize((int(ph.width * s), int(ph.height * s)), Image.LANCZOS)
x0, y0 = (S - ph.width) // 2, (S - ph.height) // 2

# alone verde LCD dietro lo schermo
sx0, sy0, sx1, sy1 = [v * s for v in m.SCREEN]
glow = Image.new('RGBA', (S, S))
ImageDraw.Draw(glow).ellipse((x0 + sx0 - 120, y0 + sy0 - 120, x0 + sx1 + 120, y0 + sy1 + 120), fill=m.GREEN + (90,))
img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(90)))
sh = Image.new('RGBA', ph.size, (0, 0, 0, 0))
sh.putalpha(ph.getchannel('A').point(lambda v: int(v * 0.6)))
img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)), (x0 + 14, y0 + 20))
img.alpha_composite(ph, (x0, y0))

out = os.path.join(_here, 'profilo_3310reborn.png')
img = img.convert('RGB')
img.save(out)
img.resize((400, 400), Image.LANCZOS).save(os.path.join(m.OUT, 'profilo_3310reborn_400.png'))
# controllo del ritaglio circolare
mask = Image.new('L', (400, 400), 0)
ImageDraw.Draw(mask).ellipse((0, 0, 399, 399), fill=255)
chk = Image.new('RGB', (400, 400), 'white')
chk.paste(img.resize((400, 400), Image.LANCZOS), (0, 0), mask)
os.makedirs(os.path.join(m.OUT, 'prova'), exist_ok=True)
chk.save(os.path.join(m.OUT, 'prova', 'cerchio.png'))
print(out)
