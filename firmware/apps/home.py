from auri import keys
from auri.ui import App, IconMenu, TextView, softkey
from auri import icons
from auri.gfx import W, Canvas
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
            # Su freccia: la console Claude dove c'e' il bridge, altrimenti l'assistente AurI.
            if self.sys.config.get('bridge_url'):
                from apps.claude import Claude
                self.sys.push(Claude(self.sys))
            else:
                self.sys.assistant()

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
        if self.sys.battery[1] and now // 500 != getattr(self, '_f', -1):
            self._f = now // 500
            return True
        t = self.sys.hal.localtime()
        if t[5] != getattr(self, '_sec', -1) or now - getattr(self, '_roll', -9999) < self.ROLL_MS + 40:
            self._sec = t[5]
            if t[4] == self._min:
                return True
        if t[4] != self._min:
            self._min = t[4]
            self._temp = self.sys.hal.sensors().get('temperature')
            return True
        return False

    def draw(self, g):
        hal = self.sys.hal
        st = self.sys.settings
        rssi = 0 if st['aereo'] or not st['wifi'] else hal.wifi_level()
        if st['aereo']:
            g.icon(('..#..', '..#..', '.###.', '#####', '..#..', '..#..', '.###.'), 2, 1)
        for i in range(4 if not st['aereo'] else 0):
            h = 2 + i * 2
            if i < rssi:
                g.fill_rect(i * 3, 8 - h, 2, h)
            else:
                g.pixel(i * 3, 7)
        if st['bt'] and not st['aereo']:
            g.icon(('.#.', '.##', '##.', '.#.', '##.', '.##', '.#.'), 14, 1)
        if st['gps'] and not st['aereo']:
            g.icon(('.#.', '#.#', '#.#', '.#.', '.#.'), 19, 2)
        pct, chg = self.sys.battery
        g.rect(W - 13, 1, 11, 7)
        g.vline(W - 2, 3, 3)
        fill = pct * 9 // 100
        if chg and pct < 100:
            fill = max(fill, (getattr(self, '_f', 0) % 4) * 3)
        g.fill_rect(W - 12, 2, fill, 5)
        g.logo_center(0)
        tm = hal.localtime()
        h = tm[3] if self.sys.settings['clock24'] else (tm[3] % 12 or 12)
        self._clock(g, '%02d%02d' % (h, tm[4]), tm[5])
        line = '%s %02d/%02d' % (days()[tm[6]], tm[2], tm[1])
        if self._temp is not None:
            line += ' %dC' % round(self._temp)
        g.text_center(line, 30)
        softkey(g, t('menu'))


    ROLL_MS = 350

    def _clock(self, g, digits, sec):
        # Big clock: changed digits roll up (old out at the top, new in from below), colon blinks every second.
        now = self.sys.hal.ticks_ms()
        if getattr(self, '_shown', None) != digits:
            self._old = getattr(self, '_shown', digits)
            self._shown = digits
            self._roll = now
        p = min(1, (now - getattr(self, '_roll', 0)) / self.ROLL_MS)
        p = 1 - (1 - p) * (1 - p)
        x0, y0 = (W - 57) // 2, 12
        tmp = getattr(self, '_tmp', None)
        if tmp is None:
            tmp = self._tmp = Canvas()      # una sola, riusata: niente memoria buttata 50 volte al secondo
        tmp.clear()
        for i, ch in enumerate(digits):
            x = x0 + i * 12 + (9 if i >= 2 else 0)
            if p < 1 and ch != self._old[i]:
                d = int(17 * p)
                tmp.char(self._old[i], x, y0 - d, 1, 2)
                tmp.char(ch, x, y0 + 17 - d, 1, 2)
            else:
                tmp.char(ch, x, y0, 1, 2)
        g.blit(tmp, y0, y0 + 16)
        if sec % 2 == 0 or p < 1:
            g.fill_rect(x0 + 25, y0 + 4, 2, 2)
            g.fill_rect(x0 + 25, y0 + 10, 2, 2)


def main_menu(sys):
    def open_claude():
        if sys.bridge_missing(t('claude')):
            return
        from apps.claude import Claude
        sys.push(Claude(sys))

    def open_casa():
        if sys.bridge_missing(t('home')):
            return
        from apps.casa import Casa
        sys.push(Casa(sys))

    def open_giochi():
        from apps.giochi import menu
        sys.push(menu(sys))

    def open_sensori():
        from apps.sensori import Sensori
        sys.push(Sensori(sys))

    def open_camera():
        from apps.camera import Camera
        sys.push(Camera(sys))

    def open_settings():
        from apps.impostazioni import Impostazioni
        sys.push(Impostazioni(sys))

    def open_info():
        sys.push(TextView(sys, t('info'), 'AurI OS %s\nAurI-3310\n%s' % (VERSION, t('about'))))

    def open_pet():
        from apps.pet import Pet
        sys.push(Pet(sys))

    items = [('AurI', icons.AURI, lambda: sys.assistant())]
    # La console Claude esiste solo dove c'e' il bridge: online al suo posto c'e' l'assistente AurI.
    if sys.config.get('bridge_url'):
        items.append((t('claude'), icons.CLAUDE, open_claude))
    items += [
        (t('home'), icons.HOME, open_casa),
        (t('games'), icons.GAMES, open_giochi), (t('pet'), icons.PET, open_pet),
        (t('camera'), icons.CAMERA, open_camera), (t('sensors'), icons.SENSORS, open_sensori), (t('settings'), icons.SETTINGS, open_settings),
        (t('info'), icons.INFO, open_info),
    ]
    return IconMenu(sys, items)
