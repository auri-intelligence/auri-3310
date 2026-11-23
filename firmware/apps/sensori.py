from auri.ui import App, header
from auri.i18n import t

LABELS = (('temperature', 'temp', '%.1fC'), ('humidity', 'hum', '%d%%'),
          ('pressure', 'press', '%dhPa'), ('light', 'light', '%dlx'))


class Sensori(App):
    title = 'Sensori'

    def __init__(self, sys):
        super().__init__(sys)
        self.data = {}
        self.last = -10000

    def tick(self, now):
        if now - self.last < 2000:
            return False
        self.last = now
        self.data = self.sys.hal.sensors()
        return True

    def draw(self, g):
        header(g, t('sensors'))
        y = 11
        for key, label, fmt in LABELS:
            if key in self.data:
                g.text(t(label), 0, y)
                v = fmt % self.data[key]
                g.text(v, 84 - len(v) * 6, y)
                y += 9
        if y == 11:
            g.text_center(t('no_sensors'), 22)


def push_telemetry(sys):
    # Sent by the home screen every few minutes; failures are silent so the phone keeps working offline.
    cfg = sys.config
    if not cfg.get('bridge_url'):
        return
    try:
        data = dict(sys.hal.sensors())
        data.pop('tilt', None)
        data['battery'] = sys.hal.battery_level() * 25
        sys.hal.request('POST', cfg['bridge_url'] + '/v1/sensors', data, cfg.get('token'))
    except Exception:
        pass
