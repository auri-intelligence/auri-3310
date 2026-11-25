# Fotocamera: quello che vede la camera, sul display 84x48 a 1 bit.
# Simulatore: telefono -> fotocamera posteriore, computer -> webcam. Nokia vero: OV2640.
# Tasti: Navi scatta/riprende, # cambia retino, * gira la camera, 0 salva, C esce.
from auri.ui import App
from auri.i18n import t
from binascii import hexlify

MODI = ('Atkinson', 'Bayer', 'Soglia')


class Camera(App):
    title = 'Camera'

    def __init__(self, sys):
        super().__init__(sys)
        self.hal = sys.hal
        self.ok = getattr(self.hal, 'cam_ok', lambda: False)()
        self.buf = None
        self.err = ''
        self.ferma = False
        self.modo = 0
        self.scritta = ''
        self.scritta_fino = 0
        if self.ok:
            self.hal.cam_start()

    def close(self):
        if self.ok:
            self.hal.cam_stop()

    def avviso(self, s, ms=1200):
        self.scritta = s
        self.scritta_fino = self.hal.ticks_ms() + ms

    def on_key(self, k):
        if k == 'c':
            self.sys.pop()
        elif not self.ok:
            return
        elif k == 'navi':
            self.ferma = not self.ferma
            if self.ferma:
                self.sys.vibrate(40)
                self.hal.beep(1800, 30, self.sys.settings['volume'])
            self.avviso(t('cam_shot') if self.ferma else '')
        elif k == '#':
            self.modo = (self.modo + 1) % len(MODI)
            self.hal.cam_mode(self.modo)
            self.avviso(MODI[self.modo])
        elif k == '*':
            self.hal.cam_switch()
            self.avviso(t('cam_flip'))
        elif k == '0' and self.buf:
            foto = self.hal.load('foto', [])
            foto = (foto + [hexlify(self.buf).decode()])[-10:]   # le ultime 10, 1 KB l'una
            self.hal.save('foto', foto)
            self.avviso(t('cam_saved'))
        self.sys.dirty = True

    def tick(self, now):
        if not self.ok:
            return False
        r = self.hal.cam_poll()
        cambiato = r.get('err', '') != self.err
        self.err = r.get('err', '')
        if r.get('frame') and not self.ferma:
            self.buf = r['frame']
            cambiato = True
        if self.scritta and now > self.scritta_fino and not self.ferma:
            self.scritta = ''
            cambiato = True
        return cambiato

    def draw(self, g):
        if not self.ok or self.err:
            g.text_center(t('camera'), 8)
            g.text_center(t('cam_' + (self.err or 'no_cam')), 22)
            g.text_center(t('back'), 38)
            return
        if not self.buf:
            g.text_center(t('camera'), 14)
            g.text_center('...', 26)
            return
        g.buf[:] = self.buf
        if self.scritta:
            w = len(self.scritta) * 6 + 4
            x = (84 - w) // 2
            g.fill_rect(x, 39, w, 9, 0)
            g.text(self.scritta, x + 2, 40)
