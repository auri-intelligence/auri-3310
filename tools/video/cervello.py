import math
import numpy as np
from PIL import Image, ImageDraw


def brain_bits(t=0.0, sparks=True):
    """Cervello di profilo 84x48 (fronte a sinistra), pieno, con circonvoluzioni chiare."""
    im = Image.new('L', (84, 48), 0)
    d = ImageDraw.Draw(im)
    for box in [(18, 8, 50, 34), (32, 5, 66, 31), (14, 14, 40, 36), (44, 12, 70, 34), (28, 20, 58, 38)]:
        d.ellipse(box, fill=255)
    d.ellipse((50, 30, 68, 41), fill=255)
    d.polygon([(46, 34), (52, 34), (51, 46), (47, 46)], fill=255)
    # solchi in chiaro: scissura di Silvio e circonvoluzioni
    d.arc((16, 22, 50, 36), 200, 340, fill=0)
    for (x, y, r, a, b) in [
        (24, 15, 4, 90, 360), (33, 11, 4, 0, 270), (42, 10, 4, 90, 360), (51, 11, 4, 0, 270), (60, 15, 4, 90, 360),
        (21, 23, 3, 270, 180), (29, 19, 4, 180, 450), (38, 18, 4, 0, 270), (47, 18, 4, 90, 360), (56, 21, 4, 180, 450),
        (64, 23, 3, 90, 300), (30, 32, 4, 180, 400), (40, 31, 4, 270, 520), (50, 28, 4, 0, 250),
    ]:
        d.arc((x - r, y - r, x + r, y + r), a, b, fill=0)
    d.arc((49, 29, 69, 42), 180, 360, fill=0)
    for y in (34, 37, 40):
        d.line((53, y, 66, y), fill=0)
    if sparks:
        rng = np.random.default_rng(int(t * 8))
        for _ in range(4):
            a = rng.uniform(-math.pi, 0.2)
            r = rng.uniform(30, 36)
            x, y = 42 + r * math.cos(a) * 1.15, 23 + r * math.sin(a) * 0.6
            d.line((x - 2, y, x + 2, y), fill=255)
            d.line((x, y - 2, x, y + 2), fill=255)
    return np.array(im) > 127


if __name__ == '__main__':
    import sys
    b = brain_bits(0.3)
    Image.fromarray((~b * 255).astype('uint8')).resize((84 * 8, 48 * 8), 0).save(sys.argv[1])
