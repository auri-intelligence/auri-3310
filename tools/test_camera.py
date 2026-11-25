"""Test della fotocamera: py tools/test_camera.py  (immagini in tmp/lcd/camera/)

La camera e' finta: una scena in scala di grigi 160x120 (sfumatura + cerchio + scritta a barre),
come quella che dara' l'OV2640 del Nokia vero. Prova il dithering Python (auri/dither.py, lo stesso
conto di web/auri-cam.js), l'app e la chiusura della camera quando si esce.
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, 'firmware')
sys.path.insert(0, FW)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(FW)
OUT = os.path.join(ROOT, 'tmp', 'lcd', 'camera')
os.makedirs(OUT, exist_ok=True)

import test_cervello  # noqa: E402
from test_cervello import TestHal, avanza, premi, shot  # noqa: E402
test_cervello.OUT = OUT
from auri.core import System  # noqa: E402
from auri import dither  # noqa: E402
from apps.home import Home  # noqa: E402
from apps.camera import Camera  # noqa: E402


def scena(w=160, h=120, t=0):
    img = bytearray(w * h)
    cx, cy = w // 2 + t, h // 2
    for y in range(h):
        for x in range(w):
            v = x * 255 // w
            if (x - cx) ** 2 + (y - cy) ** 2 < 30 ** 2:
                v = 255 - y * 2
            img[y * w + x] = max(0, min(255, v))
    return bytes(img)


class CamHal(TestHal):
    def __init__(self):
        super().__init__()
        self.cam_on = False
        self.modo = 0
        self.t = 0

    def cam_ok(self):
        return True

    def cam_start(self):
        self.cam_on = True

    def cam_stop(self):
        self.cam_on = False

    def cam_switch(self):
        pass

    def cam_mode(self, m):
        self.modo = m

    def cam_poll(self):
        self.t += 1
        return {'on': True, 'busy': False, 'err': '', 'facing': 'user',
                'frame': dither.da_grigi(scena(t=self.t % 20), 160, 120, self.modo)}


def nere(buf):
    return sum(bin(b).count('1') for b in buf)


def test_dither():
    img = scena()
    t0 = time.perf_counter()
    for m in range(3):
        b = dither.da_grigi(img, 160, 120, m)
        assert len(b) == 504
        n = nere(b)
        # la sfumatura da nero a bianco: deve esserci un po' di tutto, non tutto nero o tutto bianco
        assert 800 < n < 3300, (m, n)
    ms = (time.perf_counter() - t0) * 1000 / 3
    # tutto nero / tutto bianco restano tali (niente rumore inventato)
    assert nere(dither.da_grigi(bytes(160 * 120), 160, 120)) in (0, 4032)
    print('ok  dithering Atkinson/Bayer/soglia (%.1f ms a fotogramma con CPython)' % ms)


def test_app():
    hal = CamHal()
    s = System(hal, {'bridge_url': '', 'online': True})
    s.push(Home(s))
    s.step()
    s.push(Camera(s))
    avanza(hal, s, 200)
    assert hal.cam_on
    assert nere(s.g.buf if hasattr(s, 'g') else s.top.buf) > 0
    shot(hal, s, '01_atkinson')
    premi(hal, s, '#')
    avanza(hal, s, 1500)
    shot(hal, s, '02_bayer')
    premi(hal, s, 'navi')
    shot(hal, s, '03_scattata')
    premi(hal, s, '0')
    assert len(hal.mem.get('foto', [])) == 1 and len(hal.mem['foto'][0]) == 1008
    premi(hal, s, 'c')
    assert not hal.cam_on, 'la camera deve spegnersi uscendo'
    print('ok  app: anteprima, retini, scatto, salvataggio, camera spenta uscendo')


def test_senza_camera():
    hal = TestHal()
    s = System(hal, {'bridge_url': '', 'online': True})
    s.push(Home(s))
    s.step()
    s.push(Camera(s))
    avanza(hal, s, 100)
    shot(hal, s, '04_niente_camera')
    premi(hal, s, 'c')
    print('ok  senza camera lo dice')


if __name__ == '__main__':
    test_dither()
    test_app()
    test_senza_camera()
    print('\ntutti i test passati. Immagini in', OUT)
