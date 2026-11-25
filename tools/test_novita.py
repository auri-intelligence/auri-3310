"""Test di connessioni, posizione, classifica senza blocchi, snake di caricamento e suoni:
py tools/test_novita.py  (immagini in tmp/lcd/novita/)"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, 'firmware')
sys.path.insert(0, FW)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(FW)
OUT = os.path.join(ROOT, 'tmp', 'lcd', 'novita')
os.makedirs(OUT, exist_ok=True)

import test_cervello  # noqa: E402
from test_cervello import TestHal, avanza, premi, shot  # noqa: E402
test_cervello.OUT = OUT
from auri.core import System  # noqa: E402
from auri import sound  # noqa: E402
from apps.home import Home  # noqa: E402


class NetHal(TestHal):
    def __init__(self):
        super().__init__()
        self.loc_on = False
        self.fix = None
        self.req = {}
        self.rid = 0

    def net_info(self):
        return {'online': True, 'tipo': 'wifi', 'eff': '4g', 'bars': 3, 'down': 9.5, 'bt': 1, 'ssid': ''}

    def wifi_level(self):
        return 3

    def loc_start(self):
        self.loc_on = True

    def loc_stop(self):
        self.loc_on = False

    def loc_poll(self):
        return {'on': self.loc_on, 'err': '', 'pos': self.fix}

    # rete asincrona finta: risponde solo quando il test lo decide
    def request_start(self, method, url, body=None, token=None):
        self.rid += 1
        self.req[self.rid] = None
        self.url = url
        return self.rid

    def request_poll(self, rid):
        return self.req.get(rid)


def mk():
    hal = NetHal()
    s = System(hal, {'bridge_url': '', 'online': True, 'scores_url': 'https://script.finto/exec'})
    s.push(Home(s))
    s.step()
    return hal, s


def test_connessioni():
    hal, s = mk()
    from apps.connessioni import menu, Posizione
    s.push(menu(s))
    avanza(hal, s, 100)
    shot(hal, s, '01_connessioni')
    s.top.items[2][1]()                   # Bluetooth acceso
    s.top.items[3][1]()                   # Posizione accesa
    assert s.settings['bt'] and s.settings['gps']
    s.push(Posizione(s))
    avanza(hal, s, 200)
    assert hal.loc_on
    shot(hal, s, '02_cerco')
    hal.fix = {'lat': 41.89021, 'lon': 12.49223, 'acc': 12}
    avanza(hal, s, 200)
    shot(hal, s, '03_posizione')
    premi(hal, s, 'c')
    assert not hal.loc_on, 'il GPS si spegne uscendo'
    s.home()
    avanza(hal, s, 100)
    shot(hal, s, '04_home_bt_gps')
    s.settings.set(aereo=True)
    avanza(hal, s, 100)
    shot(hal, s, '05_home_aereo')
    print('ok  connessioni, posizione, icone di stato e modalita aereo')


def test_classifica_non_blocca():
    hal, s = mk()
    hal.save('g_nome', {'nome': 'LUIGI'})
    from apps.giochi.classifica import Classifica
    s.push(Classifica(s, 'volo', 120))
    avanza(hal, s, 100)
    assert hal.req, 'la richiesta deve partire'
    # mentre il server non risponde il telefono continua a disegnare (lo snake si muove)
    s.dirty = True
    s.step()
    a = bytes(s.g.buf) if hasattr(s, 'g') else None
    shot(hal, s, '06_classifica_attesa')
    avanza(hal, s, 300)
    hal.req[1] = ({'top': [['LUIGI', 120], ['ANNA', 90]]}, '')
    avanza(hal, s, 100)
    assert s.top.world and s.top.rows[0] == [120, 'LUIGI'], s.top.rows
    shot(hal, s, '07_classifica')
    print('ok  classifica mondiale senza bloccare lo schermo')


def test_suoni():
    for name, song, bpm in sound.RINGTONES:
        assert sound.parse(song, bpm), name
    assert sound.parse(sound.NOTIFY, 180)
    print('ok  suonerie (%s)' % ', '.join(r[0] for r in sound.RINGTONES))


if __name__ == '__main__':
    test_suoni()
    test_connessioni()
    test_classifica_non_blocca()
    print('\ntutti i test passati. Immagini in', OUT)
