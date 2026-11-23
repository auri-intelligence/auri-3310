from auri import keys
from auri.ui import App, Menu, TextView, softkey
from auri.gfx import W
from auri.core import VERSION
from auri.i18n import t, days


class Home(App):
    def __init__(self, sys):
        super().__init__(sys)
        self._min = -1
        self._navi = False
        self._temp = None
        self._sent = -300000

    def on_key(self, k):
        if k == keys.NAVI:
            # Menu opens on release, so that holding Navi can start the assistant instead.
            self._navi = True
        elif k == keys.UP:
            from apps.claude import Claude
            self.sys.push(Claude(self.sys))

    def on_long(self, k):
        if k == keys.NAVI:
            self._navi = False
            self.sys.assistant(keys.NAVI)

    def on_up(self, k):
        if k == keys.NAVI and self._navi:
            self._navi = False
            self.sys.push(main_menu(self.sys))

    def tick(self, now):
        if now - self._sent >= 300000:
            self._sent = now
            from apps.sensori import push_telemetry
            push_telemetry(self.sys)
        t = self.sys.hal.localtime()
        if t[4] != self._min:
            self._min = t[4]
            self._temp = self.sys.hal.sensors().get('temperature')
            return True
        return False

    def draw(self, g):
        hal = self.sys.hal
        rssi = hal.wifi_level()
        for i in range(4):
            h = 2 + i * 2
            if i < rssi:
                g.fill_rect(i * 3, 8 - h, 2, h)
            else:
                g.pixel(i * 3, 7)
        lvl = hal.battery_level()
        g.rect(W - 13, 1, 11, 7)
        g.vline(W - 2, 3, 3)
        g.fill_rect(W - 12, 2, lvl * 9 // 4, 5)
        g.logo_center(0)
        tm = hal.localtime()
        g.text_center('%02d:%02d' % (tm[3], tm[4]), 12, 1, 2)
        line = '%s %02d/%02d' % (days()[tm[6]], tm[2], tm[1])
        if self._temp is not None:
            line += ' %dC' % round(self._temp)
        g.text_center(line, 30)
        softkey(g, t('menu'))


def main_menu(sys):
    def open_claude():
        from apps.claude import Claude
        sys.push(Claude(sys))

    def open_casa():
        from apps.casa import Casa
        sys.push(Casa(sys))

    def open_snake():
        from apps.snake import Snake
        sys.push(Snake(sys))

    def open_sensori():
        from apps.sensori import Sensori
        sys.push(Sensori(sys))

    def open_settings():
        from apps.impostazioni import Impostazioni
        sys.push(Impostazioni(sys))

    def open_info():
        sys.push(TextView(sys, t('info'), 'AurI OS %s\nAurI-3310\n%s' % (VERSION, t('about'))))

    items = [(t('claude'), open_claude), (t('home'), open_casa), (t('snake'), open_snake),
             (t('sensors'), open_sensori), (t('settings'), open_settings), (t('info'), open_info)]
    return Menu(sys, t('menu'), [('%d %s' % (i + 1, n), f) for i, (n, f) in enumerate(items)])
