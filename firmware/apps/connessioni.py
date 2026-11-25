# Impostazioni > Connessioni: Wi-Fi, Bluetooth, Posizione e Modalita' aereo.
# Simulatore: la rete e il GPS veri del dispositivo (web/auri-conn.js). Nokia vero: WLAN e BLE dell'ESP32,
# la posizione arriva dal telefono vero solo con un modulo GPS (per ora non previsto) o dal bridge.
from auri.ui import App, Menu, header, softkey, snake_load
from auri.i18n import t


def onoff(v):
    return t('on') if v else t('off')


def net(sys):
    f = getattr(sys.hal, 'net_info', None)
    try:
        return f() if f else {}
    except Exception:
        return {}


class Rete(App):
    """Stato della rete: tipo, qualita', velocita' stimata."""

    def __init__(self, sys):
        super().__init__(sys)
        self.last = -5000
        self.info = {}

    def tick(self, now):
        if now - self.last < 1000:
            return False
        self.last = now
        self.info = net(self.sys)
        return True

    def draw(self, g):
        header(g, t('wifi'))
        st = self.sys.settings
        i = self.info
        if st['aereo']:
            lines = [t('aereo'), onoff(True)]
        elif not st['wifi']:
            lines = [t('wifi'), onoff(False)]
        else:
            lines = [t('net_on') if i.get('online', True) else t('net_off')]
            if i.get('ssid'):
                lines.append(i['ssid'][:14])
            tipo = i.get('tipo') or ''
            if tipo:
                lines.append(tipo[:14])
            if i.get('eff'):
                lines.append('%s %s' % (i['eff'], ('%.1fMb' % i['down']) if i.get('down') else ''))
        for n, s in enumerate(lines[:3]):
            g.text(s[:14], 0, 11 + n * 9)
        bars = i.get('bars', 0) if st['wifi'] and not st['aereo'] else 0
        for k in range(4):
            h = 2 + k * 3
            if k < bars:
                g.fill_rect(70 + k * 3, 39 - h, 2, h)
            else:
                g.pixel(70 + k * 3, 38)
        softkey(g, t('back'))


class Posizione(App):
    """Dove sono: latitudine, longitudine e precisione (GPS del telefono o rete del computer)."""

    def __init__(self, sys):
        super().__init__(sys)
        self.hal = sys.hal
        self.ok = hasattr(self.hal, 'loc_start')
        self.r = {}
        if self.ok and sys.settings['gps'] and not sys.settings['aereo']:
            self.hal.loc_start()

    def close(self):
        if self.ok:
            self.hal.loc_stop()

    def tick(self, now):
        if not self.ok:
            return False
        self.r = self.hal.loc_poll()
        return True

    def draw(self, g):
        header(g, t('gps'))
        st = self.sys.settings
        if not st['gps'] or st['aereo']:
            g.text_center(t('gps') + ' ' + onoff(False), 20)
            g.text_center(t('gps_hint'), 30)
            return
        err = self.r.get('err') if self.ok else 'no_gps'
        p = self.r.get('pos')
        if err and not p:
            g.text_center(t('loc_' + err), 22)
            return
        if not p:
            snake_load(g, self.hal.ticks_ms(), 25, t('gps_wait'))
            return
        g.text('N %9.5f' % p['lat'] if p['lat'] >= 0 else 'S %9.5f' % -p['lat'], 0, 11)
        g.text('E %9.5f' % p['lon'] if p['lon'] >= 0 else 'W %9.5f' % -p['lon'], 0, 20)
        g.text('+/- %dm' % p['acc'], 0, 29)
        softkey(g, t('back'))


def menu(sys):
    st = sys.settings

    def sw(key):
        def run():
            st.set(**{key: not st[key]})
            bt = getattr(sys.hal, 'bt_set', None)
            if bt and key in ('bt', 'aereo'):
                bt(st['bt'] and not st['aereo'])
            wifi = getattr(sys.hal, 'wifi_set', None)
            if wifi and key in ('wifi', 'aereo'):
                wifi(st['wifi'] and not st['aereo'])
            sys.toast('%s %s' % (t(key), onoff(st[key])), 900)
            m = sys.top
            if hasattr(m, 'rebuild'):
                m.rebuild()
            sys.dirty = True
        return run

    def bt_label():
        i = net(sys)
        if i.get('bt') == 0:
            return '3 %s %s' % (t('bt'), t('bt_none'))
        return '3 %s %s' % (t('bt'), onoff(st['bt']))

    def build():
        return [
            ('1 %s %s' % (t('wifi'), onoff(st['wifi'])), sw('wifi')),
            ('2 %s' % t('net_state'), lambda: sys.push(Rete(sys))),
            (bt_label(), sw('bt')),
            ('4 %s %s' % (t('gps'), onoff(st['gps'])), sw('gps')),
            ('5 %s' % t('gps_where'), lambda: sys.push(Posizione(sys))),
            ('6 %s %s' % (t('aereo'), onoff(st['aereo'])), sw('aereo')),
        ]
    m = Menu(sys, t('connections'), build())
    m.rebuild = lambda: setattr(m, 'items', build())
    return m
