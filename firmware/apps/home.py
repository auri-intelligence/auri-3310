from auri import keys
from auri.ui import App, Menu, TextView, softkey
from auri.gfx import W
from auri.core import VERSION

DAYS = ('Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom')


class Home(App):
    def __init__(self, sys):
        super().__init__(sys)
        self._min = -1

    def on_key(self, k):
        if k == keys.NAVI:
            self.sys.push(main_menu(self.sys))
        elif k == keys.UP:
            from apps.claude import Claude
            self.sys.push(Claude(self.sys))

    def on_long(self, k):
        pass

    def tick(self, now):
        t = self.sys.hal.localtime()
        if t[4] != self._min:
            self._min = t[4]
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
        g.text_center('Auri', 0)
        t = hal.localtime()
        g.text_center('%02d:%02d' % (t[3], t[4]), 12, 1, 2)
        g.text_center('%s %02d/%02d' % (DAYS[t[6]], t[2], t[1]), 30)
        softkey(g, 'Menu')


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

    def open_info():
        sys.push(TextView(sys, 'Info', 'Auri OS %s\nAuri-3310\nUn 3310 del 2000 con un cervello nuovo.' % VERSION))

    return Menu(sys, 'Menu', [
        ('1 Claude', open_claude),
        ('2 Casa', open_casa),
        ('3 Serpente', open_snake),
        ('4 Info', open_info),
    ])
