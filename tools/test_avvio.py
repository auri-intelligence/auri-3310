"""Accensione: la lista dei controlli scorre, ogni controllo ha la spunta, poi la Home.
py tools/test_avvio.py  (immagini in tmp/lcd/avvio/)"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import test_cervello as T  # noqa: E402

T.OUT = os.path.join(ROOT, 'tmp', 'lcd', 'avvio')
os.makedirs(T.OUT, exist_ok=True)
from auri.core import System  # noqa: E402


def main():
    hal = T.TestHal()
    s = System(hal, {'bridge_url': '', 'online': True})
    s.power_on()
    app = s.top
    for k, ms in enumerate((1500, 600, 700, 800, 900)):
        T.avanza(hal, s, ms)
        T.shot(hal, s, '%d_avvio' % k)
    assert len(app.checks) == app.total == 15, (len(app.checks), app.total)
    assert all(len(c) == 3 for c in app.checks)
    T.avanza(hal, s, 1500)
    assert type(s.top).__name__ == 'Home', type(s.top).__name__
    print('ok  accensione: %d controlli con spunta, poi la Home' % app.total)
    try:
        from PIL import Image
        import glob
        fs = sorted(glob.glob(os.path.join(T.OUT, '*_avvio.png')))
        ims = [Image.open(f) for f in fs]
        w, h = ims[0].size
        o = Image.new('RGB', (w * 3 + 20, (h + 10) * 2), 'white')
        for i, im in enumerate(ims):
            o.paste(im, ((i % 3) * (w + 10), (i // 3) * (h + 10)))
        o.save(os.path.join(T.OUT, 'foglio.png'))
    except ImportError:
        pass
    print('\ntutti i test passati. Immagini in', T.OUT)


if __name__ == '__main__':
    main()
