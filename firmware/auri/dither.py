# Da immagine in scala di grigi (un byte per pixel, qualsiasi misura) al buffer del display 84x48.
# Stessi conti di web/auri-cam.js: ritaglio centrale 7:4, contrasto automatico, poi
# dithering Atkinson (0), Bayer 4x4 (1) o soglia (2). Usato sul Nokia vero con la fotocamera.
from array import array

W = 84
H = 48
BAYER = (0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5)


def riduci(src, sw, sh, specchio=False):
    """Ritaglio centrale con il rapporto del display e media a blocchi fino a 84x48."""
    cw, ch = sw, sw * H // W
    if ch > sh:
        ch, cw = sh, sh * W // H
    ox, oy = (sw - cw) // 2, (sh - ch) // 2
    g = array('h', bytes(W * H * 2))
    for y in range(H):
        y0 = oy + y * ch // H
        y1 = max(y0 + 1, oy + (y + 1) * ch // H)
        for x in range(W):
            x0 = ox + x * cw // W
            x1 = max(x0 + 1, ox + (x + 1) * cw // W)
            s = n = 0
            for yy in range(y0, y1, max(1, (y1 - y0) // 2)):
                r = yy * sw
                for xx in range(x0, x1, max(1, (x1 - x0) // 2)):
                    s += src[r + xx]
                    n += 1
            g[y * W + (W - 1 - x if specchio else x)] = s // n
    return g


def contrasto(g):
    hist = [0] * 256
    for v in g:
        hist[v] += 1
    cut = len(g) // 100
    lo = acc = 0
    while lo < 255:
        acc += hist[lo]
        if acc >= cut:
            break
        lo += 1
    hi, acc = 255, 0
    while hi > 0:
        acc += hist[hi]
        if acc >= cut:
            break
        hi -= 1
    span = max(24, hi - lo)
    for i in range(len(g)):
        v = (g[i] - lo) * 255 // span
        g[i] = 0 if v < 0 else (255 if v > 255 else v)


def a_display(g, modo=0, buf=None):
    """g: array di 84*48 grigi (viene modificato). Ritorna il buffer PCD8544 da 504 byte."""
    if buf is None:
        buf = bytearray(W * H // 8)
    else:
        for i in range(len(buf)):
            buf[i] = 0
    for y in range(H):
        for x in range(W):
            i = y * W + x
            v = g[i]
            if modo == 1:
                on = v < BAYER[(y & 3) * 4 + (x & 3)] * 16 + 8
            elif modo == 2:
                on = v < 128
            else:
                on = v < 128
                e = (v if on else v - 255) >> 3
                if e:
                    if x + 1 < W:
                        g[i + 1] += e
                    if x + 2 < W:
                        g[i + 2] += e
                    if y + 1 < H:
                        if x:
                            g[i + W - 1] += e
                        g[i + W] += e
                        if x + 1 < W:
                            g[i + W + 1] += e
                    if y + 2 < H:
                        g[i + 2 * W] += e
            if on:
                buf[(y >> 3) * W + x] |= 1 << (y & 7)
    return buf


def da_grigi(src, sw, sh, modo=0, specchio=False, buf=None):
    g = riduci(src, sw, sh, specchio)
    contrasto(g)
    return a_display(g, modo, buf)
