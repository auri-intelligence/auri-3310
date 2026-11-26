"""Texture vere per la vista "Telefono finito" del banco 3D, dalle scansioni del telefono smontato (docs/scans).
Ritaglia ogni pezzo, toglie lo sfondo (alfa), copre i marchi e le etichette con codici, scala in mm e salva in
firmware/web/tex/finito/ (WebP) piu' pezzi.json con le misure. Rifacibile: py tools/prepara_texture_finito.py
Le due scansioni "componenti" sono a ~600 dpi: la scala si ricava dalla scheda (112 mm) presente in entrambe."""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC = os.path.join(ROOT, 'docs', 'scans')
OUT = os.path.join(ROOT, 'firmware', 'web', 'tex', 'finito')
FONT = 'C:/Windows/Fonts/ariblk.ttf'
PCB_MM = 112.07          # lunghezza della scheda: 2647 px a 600 dpi
LATO = 1024              # lato lungo massimo delle texture

# riquadri dei pezzi nelle anteprime a 1/6 (x0, y0, x1, y1); 'fondo' = sfondo grigio da togliere
CF = {'retro_fuori': (0, 12, 203, 478), 'fronte_fuori': (215, 12, 414, 474), 'gomma_sopra': (438, 22, 607, 208),
      'bat_etichetta': (438, 220, 605, 448), 'pcb_cf': (604, 22, 779, 464), 'telaio_ui_sotto': (768, 28, 947, 472),
      'telaio_sotto': (952, 12, 1144, 468)}
CR = {'retro_dentro': (12, 22, 222, 482), 'fronte_dentro': (212, 18, 417, 478), 'gomma_sotto': (410, 8, 598, 218),
      'bat_dietro': (410, 218, 584, 468), 'pcb_cr': (588, 0, 762, 468), 'telaio_ui_sopra': (760, 32, 947, 472),
      'telaio_sopra': (943, 2, 1140, 468)}
# marchi e codici (coordinate dell'anteprima a 1/6): ('auri', box) = toppa + logo AurI, ('sfoca', box), ('toppa', box)
COPRI = {
    'retro_fuori': [('auri', (55, 76, 134, 101))],
    'fronte_fuori': [('auri', (282, 89, 350, 112))],
    'bat_etichetta': [('etichetta', (446, 226, 600, 444))],
    'telaio_ui_sotto': [('sfoca', (806, 145, 910, 215)), ('sfoca', (812, 216, 940, 242))],
    'telaio_sotto': [('toppa', (996, 92, 1074, 116)), ('sfoca', (975, 140, 1115, 335))],
    'telaio_ui_sopra': [('auri', (772, 112, 845, 138))],
    'telaio_sopra': [('sfoca', (985, 125, 1065, 155))],
    'gomma_sotto': [('sfoca', (505, 80, 565, 104))],
}


def logo_auri(w, h, colore):
    """Il logo come nel simulatore: A e I grandi, "ur" piccolo sulla stessa linea di base."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype(FONT, int(h * 0.9))
    small = ImageFont.truetype(FONT, int(h * 0.62))
    parti = [('A', big), ('ur', small), ('I', big)]
    larg = sum(d.textlength(t, font=f) for t, f in parti)
    x = (w - larg) / 2
    base = h * 0.92
    for t, f in parti:
        asc = f.getmetrics()[0]
        d.text((x, base - asc), t, font=f, fill=colore)
        x += d.textlength(t, font=f)
    return im


# pezzi pieni (gomma, batteria, telai): i buchi nella maschera sono solo riflessi simili allo sfondo
PIENI = {'gomma_sopra', 'gomma_sotto', 'bat_etichetta', 'bat_dietro', 'telaio_sotto', 'telaio_sopra', 'retro_fuori', 'retro_dentro'}


# pezzi con buchi veri (finestra del display, fori dei tasti) ma con parti chiare simili allo sfondo
TRAMA = {'fronte_fuori'}
# plastica tutta nera: e' pezzo solo cio' che e' scuro (i fori mostrano lo sfondo chiaro)
SCURI = {'fronte_dentro'}


def scontorna(rgb, fondo_bianco=False, pieno=False, trama=False, scuro=False):
    """Alfa: pixel lontani dal colore dello sfondo (stimato sul bordo). Tiene il pezzo piu' grande, bordi morbidi."""
    a = rgb.astype(np.int32)
    bordo = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3), a[:, :6].reshape(-1, 3), a[:, -6:].reshape(-1, 3)])
    bg = np.median(bordo, 0)
    dist = np.sqrt(((a - bg) ** 2).sum(2))
    soglia = 40 if fondo_bianco else 30
    m = dist > soglia
    if scuro:
        m = a.mean(2) < 110
    if pieno or trama:   # lo sfondo e' piatto: dove l'immagine ha trama (riflessi, bordi) e' pezzo anche se il colore somiglia
        g = a.mean(2).astype(np.float32)
        var = ndimage.uniform_filter(g * g, 9) - ndimage.uniform_filter(g, 9) ** 2
        m |= var > 30
    m = ndimage.binary_opening(m, iterations=2)
    lab, n = ndimage.label(m)
    if n > 1:
        size = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (1 + int(np.argmax(size)))
    m = ndimage.binary_closing(m, iterations=3)
    if pieno:
        m = ndimage.binary_fill_holes(ndimage.binary_closing(m, iterations=12))
    alfa = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    return alfa


def copri(im, azioni, ox, oy, k):
    """Copre marchi e codici: coordinate dell'anteprima 1/6 -> pixel del ritaglio (scala k)."""
    for tipo, (x0, y0, x1, y1) in azioni:
        b = (int((x0 * 6 - ox) * k), int((y0 * 6 - oy) * k), int((x1 * 6 - ox) * k), int((y1 * 6 - oy) * k))
        b = (max(0, b[0]), max(0, b[1]), min(im.width, b[2]), min(im.height, b[3]))
        if b[2] <= b[0] or b[3] <= b[1]:
            continue
        reg = im.crop(b)
        if tipo == 'etichetta':   # etichetta della batteria rifatta pulita, senza marchi ne' codici
            d = ImageDraw.Draw(im)
            d.rounded_rectangle(b, radius=6, fill=(198, 200, 198, 255))
            ww, hh = b[2] - b[0], b[3] - b[1]
            im.alpha_composite(logo_auri(int(ww * .5), int(hh * .14), (40, 42, 46, 255)), (b[0] + int(ww * .25), b[1] + int(hh * .18)))
            fnt = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', max(8, int(hh * .06)))
            for i, t in enumerate(('Li-ion  3,7 V', '1000 mAh', 'batteria ricaricabile')):
                d.text((b[0] + ww / 2, b[1] + hh * (.48 + i * .11)), t, font=fnt, fill=(40, 42, 46, 255), anchor='mm')
            continue
        if tipo == 'sfoca':
            im.paste(reg.filter(ImageFilter.GaussianBlur(max(6, (b[2] - b[0]) // 10))), b[:2])
            continue
        # toppa: colore medio dei bordi del riquadro
        arr = np.asarray(reg.convert('RGB')).astype(np.int32)
        col = tuple(int(v) for v in np.median(np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]]), 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle(b, radius=max(2, (b[3] - b[1]) // 4), fill=col + (255,))
        if tipo == 'auri':
            chiaro = sum(col) / 3 < 110
            logo = logo_auri(b[2] - b[0], b[3] - b[1], (225, 228, 232, 255) if chiaro else (25, 27, 30, 255))
            im.alpha_composite(logo, b[:2])


def salva(nome, im):
    im.save(os.path.join(OUT, nome + '.webp'), 'WEBP', quality=82, method=6)


def pezzi_scansione(file, riquadri, rif):
    src = Image.open(os.path.join(SC, file)).convert('RGB')
    # scala: altezza della scheda (mascherata) in questa scansione = 112 mm
    x0, y0, x1, y1 = (v * 6 for v in riquadri[rif])
    pcb = np.asarray(src.crop((x0, y0, x1, y1)))
    al = np.asarray(scontorna(pcb)) > 128
    rows = np.where(al.any(1))[0]
    mm_px = PCB_MM / (rows[-1] - rows[0] + 1)
    out = {}
    for nome, box in riquadri.items():
        if nome == rif:
            continue
        x0, y0, x1, y1 = (v * 6 for v in box)
        crop = src.crop((x0, y0, x1, y1))
        alfa = scontorna(np.asarray(crop), pieno=nome in PIENI, trama=nome in TRAMA, scuro=nome in SCURI)
        bb = alfa.point(lambda v: 255 if v > 128 else 0).getbbox()
        if nome in TRAMA or nome in SCURI:   # contorno robusto: righe/colonne piene almeno al 30%
            mm_ = np.asarray(alfa) > 128
            r_ = np.where(mm_.mean(1) > .3)[0]
            c_ = np.where(mm_.mean(0) > .3)[0]
            bb = (int(c_[0]), int(r_[0]), int(c_[-1]) + 1, int(r_[-1]) + 1)
        crop = crop.crop(bb)
        alfa = alfa.crop(bb)
        im = crop.convert('RGBA')
        im.putalpha(alfa)
        k = min(1.0, LATO / max(im.size))
        if k < 1:
            im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        copri(im, COPRI.get(nome, []), x0 + bb[0], y0 + bb[1], k)
        salva(nome, im)
        out[nome] = {'w': round(crop.width * mm_px, 1), 'l': round(crop.height * mm_px, 1)}
    return out


def pcb_scan(file, nome):
    src = Image.open(os.path.join(SC, file)).convert('RGB')
    alfa = scontorna(np.asarray(src), fondo_bianco=True)
    bb = alfa.point(lambda v: 255 if v > 128 else 0).getbbox()
    src, alfa = src.crop(bb), alfa.crop(bb)
    im = src.convert('RGBA')
    im.putalpha(alfa)
    k = LATO / max(im.size)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    salva(nome, im)
    mm = 25.4 / 600
    return {'w': round(src.width * mm, 1), 'l': round(src.height * mm, 1)}, im.getchannel('A')


def scheda_auri(alfa):
    """Lato componenti della NUOVA scheda AurI: stessa sagoma, maschera verde, piste di rame, serigrafia."""
    w, h = alfa.size
    rng = np.random.default_rng(3310)
    base = np.zeros((h, w, 3), np.float32) + np.array([24, 92, 52], np.float32)
    base += rng.normal(0, 3, (h, w, 1))
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert('RGBA')
    d = ImageDraw.Draw(im)
    s = w / 47.0          # px per mm
    rame = (46, 120, 66, 255)
    # piste: fasci ortogonali con curve a 45 gradi, come un vero routing
    for _ in range(70):
        x, y = rng.uniform(4, 43) * s, rng.uniform(6, 106) * s
        pts = [(x, y)]
        for _ in range(rng.integers(2, 5)):
            if rng.random() < .5:
                x += rng.uniform(-14, 14) * s
            else:
                y += rng.uniform(-18, 18) * s
            pts.append((x, y))
        d.line(pts, fill=rame, width=max(1, int(rng.choice([0.15, 0.2, 0.3]) * s)), joint='curve')
    for _ in range(260):     # vie
        x, y = rng.uniform(3, 44) * s, rng.uniform(4, 108) * s
        r = 0.3 * s
        d.ellipse((x - r, y - r, x + r, y + r), fill=(196, 160, 72, 255))
        d.ellipse((x - r / 2.5, y - r / 2.5, x + r / 2.5, y + r / 2.5), fill=(30, 40, 30, 255))
    f = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', int(1.6 * s))
    fp = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', int(1.1 * s))
    bianco = (236, 240, 236, 255)

    def ingombro(x, y, ww, hh, nome):   # serigrafia: contorno del pezzo e sigla
        d.rectangle(((x - ww / 2) * s, (y - hh / 2) * s, (x + ww / 2) * s, (y + hh / 2) * s), outline=bianco, width=max(1, int(.18 * s)))
        d.text(((x - ww / 2) * s, (y + hh / 2 + .4) * s), nome, font=fp, fill=bianco)
    for x, y, ww, hh, n in COMP_SERIGRAFIA:
        ingombro(x, y, ww, hh, n)
    d.text((5 * s, 100 * s), 'AurI-3310  rev A', font=f, fill=bianco)
    d.text((5 * s, 102.6 * s), 'ESP32-S3  4 strati  ENIG', font=fp, fill=bianco)
    im.putalpha(alfa)
    salva('pcb_auri', im)


# posizioni (mm dal bordo in alto a sinistra della scheda vista dal lato componenti): x, y, larghezza, altezza, sigla
COMP_SERIGRAFIA = [(23.5, 30, 18, 25.5, 'U1 ESP32-S3-WROOM-1'), (14, 61, 14, 15, 'J2 microSD'),
                   (33, 58, 3.2, 3.2, 'U3'), (33, 98, 4.7, 3.8, 'MK1'), (23.5, 107, 9, 7.4, 'J1 USB-C'),
                   (34, 76, 13, 13, 'BZ1'), (12, 84, 10, 10, 'M1'), (33, 66, 3, 1.6, 'U4 LDO')]


def piazzole_tasti(mm):
    """Centri delle piazzole dorate dei tasti (mm dal centro della scheda, lato tasti): li' vanno le cupole."""
    a = np.asarray(Image.open(os.path.join(OUT, 'pcb_tasti.webp')).convert('RGB')).astype(int)
    oro = (a[..., 0] > 150) & (a[..., 1] > 95) & (a[..., 1] < 190) & (a[..., 2] < 120) & (a[..., 0] - a[..., 2] > 70)
    oro = ndimage.binary_closing(oro, iterations=3)
    pieno = ndimage.binary_fill_holes(oro)
    lab, n = ndimage.label(pieno)
    h, w = oro.shape
    k = mm['l'] / h
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if 4.5 / k < ww < 9 / k and 4.5 / k < hh < 9 / k and sl[0].start > h * .4:
            cy, cx = ndimage.center_of_mass(lab == i)
            out.append([round((cx - w / 2) * k, 1), round((cy - h / 2) * k, 1), round(max(hh, ww) * k / 2, 1)])
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    mis = {}
    mis.update(pezzi_scansione('componenti fronte.png', CF, 'pcb_cf'))
    mis.update(pezzi_scansione('componenti retro.png', CR, 'pcb_cr'))
    # cover frontale vista da fuori: i fori (display, tasti) si vedono scuri come la plastica; si prendono
    # dalla scansione dell'interno (li' lo sfondo chiaro si vede bene), specchiata
    fu = Image.open(os.path.join(OUT, 'fronte_fuori.webp')).convert('RGBA')
    de = Image.open(os.path.join(OUT, 'fronte_dentro.webp')).convert('RGBA')
    # la scansione esterna ha un margine in fondo: stessa proporzione dell'interno, tagliando sotto
    fu = fu.crop((0, 0, fu.width, round(fu.width * de.height / de.width)))
    mis['fronte_fuori']['l'] = round(mis['fronte_fuori']['w'] * de.height / de.width, 1)
    buchi = de.getchannel('A').transpose(Image.FLIP_LEFT_RIGHT).resize(fu.size, Image.LANCZOS).filter(ImageFilter.MinFilter(17))   # fori un po' piu' larghi: dentro sono piu' stretti
    fu.putalpha(Image.fromarray(np.minimum(np.asarray(fu.getchannel('A')), np.asarray(buchi))))
    salva('fronte_fuori', fu)
    mis['pcb_tasti'], _ = pcb_scan('pcb_retro_600dpi.png', 'pcb_tasti')
    mis['tasti'] = piazzole_tasti(mis['pcb_tasti'])
    mis['pcb_orig'], alfa = pcb_scan('pcb_fronte_600dpi.png', 'pcb_orig')
    scheda_auri(alfa)
    mis['pcb_auri'] = mis['pcb_orig']
    mis['_serigrafia'] = COMP_SERIGRAFIA
    json.dump(mis, open(os.path.join(OUT, 'pezzi.json'), 'w'), indent=1)
    tot = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print(json.dumps(mis), '\ntotale %.2f MB' % (tot / 1e6))


if __name__ == '__main__':
    main()
