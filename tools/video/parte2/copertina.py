"""Cover 1080x1920 for Part 2: real photo of the motherboard pulled out, brain on the LCD, title.
Everything that matters stays in the central square (y 420-1500) for the 1:1 and 3:4 grids."""
import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.argv = sys.argv[:1]
import monta as m
from cervello import brain_bits

W, H = 1080, 1920
SQ0, SQ1 = 420, 1500

photo = m.clip('scheda', 1.4)
photo = m.camera(photo, 1.25, 0, -60)
photo = ImageEnhance.Brightness(ImageEnhance.Color(photo).enhance(1.3)).enhance(0.55).convert('RGBA')
tint = Image.new('RGBA', (W, H), m.BLUE + (120,))
img = Image.alpha_composite(photo, tint)

ph = m.phone(brain_bits(0.6))
s = 560 / ph.height
ph = ph.resize((int(ph.width * s), int(ph.height * s)), Image.LANCZOS).rotate(10, resample=Image.BICUBIC, expand=True)
cx, cy = W // 2 + 190, 1060
glow = Image.new('RGBA', (W, H))
ImageDraw.Draw(glow).ellipse((cx - 300, cy - 300, cx + 300, cy + 260), fill=m.GREEN + (120,))
img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(100)))
img.alpha_composite(ph, (cx - ph.width // 2, cy - ph.height // 2))

c = img.convert('RGB')
m.draw_text(c, 'HO DISTRUTTO', W // 2, SQ0 + 30, 140, fill=m.WHITE, stroke=10, stroke_fill=(5, 12, 30))
m.draw_text(c, 'UN 3310', W // 2, SQ0 + 175, 170, fill=m.RED, stroke=10, stroke_fill=(5, 12, 30))
m.draw_text(c, 'TRAPIANTO', W // 2 - 150, SQ1 - 280, 120, fill=m.GREEN, stroke=9, stroke_fill=(5, 12, 30), maxw=560)
m.draw_text(c, 'DI CERVELLO', W // 2 - 150, SQ1 - 160, 100, fill=m.WHITE, stroke=9, stroke_fill=(5, 12, 30), maxw=560)

d = ImageDraw.Draw(c)
f = m.p1.font(m.FONT_BOLD, 54)
label = 'PARTE 2'
tw = m.p1.text_w(label, f)
d.rounded_rectangle((W // 2 - tw // 2 - 34, 230, W // 2 + tw // 2 + 34, 316), radius=43, fill=m.GREEN)
d.text((W // 2, 273), label, font=f, fill=(5, 12, 30), anchor='mm')
m.draw_text(c, 'le vostre idee dentro un 3310', W // 2, 1560, 60, fill=m.WHITE, path=m.FONT_BOLD, stroke=5,
            stroke_fill=(5, 12, 30))

os.makedirs(os.path.join(m.HERE, 'pubblicato'), exist_ok=True)
out = os.path.join(m.HERE, 'pubblicato', 'copertina_parte2.png')
c.save(out)
c.crop((0, SQ0, W, SQ1)).save(os.path.join(m.HERE, 'pubblicato', 'copertina_parte2_1x1.png'))
c.crop((0, 240, W, 1680)).resize((540, 720), Image.LANCZOS).save(os.path.join(m.HERE, 'pubblicato', 'copertina_parte2_3x4.png'))
print(out)
