# Hardware layer for the browser simulator (MicroPython WebAssembly). The JS side lives in web/index.html.
import js
import json
import time
import ubinascii


class WebHal:
    def __init__(self):
        self.queue = []

    def ticks_ms(self):
        return time.ticks_ms()

    def localtime(self):
        return tuple(int(v) for v in str(js.auriTime()).split(','))

    def events(self):
        ev, self.queue = self.queue, []
        return ev

    def press(self, k):
        self.queue.append(('down', k))

    def release(self, k):
        self.queue.append(('up', k))

    def show(self, buf):
        js.auriShow(ubinascii.hexlify(buf).decode())

    def light(self, on, ms=15000):
        # ms < 0: always on
        js.auriLight(ms if on else 0)

    def vibrate(self, ms):
        js.auriVibrate(ms)

    def beep(self, freq, ms, vol=3):
        js.auriBeep(freq, ms, vol)

    def wifi_level(self):
        return 4

    def battery(self):
        # a stale cached page may lack the simulated battery: report full instead of crashing
        try:
            pct, chg = str(js.auriBattery()).split(',')
            return int(pct), chg == '1'
        except Exception:
            return 100, False

    def battery_level(self):
        return min(4, (self.battery()[0] + 12) // 25)

    def power_off(self):
        js.auriLight(0)

    def sensors(self):
        return json.loads(str(js.auriSensors()))

    def voice_start(self):
        return bool(js.auriVoiceStart())

    def voice_stop(self, url, params, token):
        js.auriVoiceStop(url, json.dumps(params), token or '')

    def voice_poll(self):
        r = str(js.auriVoicePoll())
        return json.loads(r) if r else None

    def random(self, n):
        return int(js.Math.random() * n)

    def sleep_ms(self, ms):
        pass

    def running(self):
        return True

    def request(self, method, url, body=None, token=None):
        r = js.auriRequest(method, url, json.dumps(body) if body is not None else '', token or '')
        r = str(r)
        if r.startswith('ERR '):
            raise OSError(r[4:])
        return json.loads(r)

    def load(self, name, default):
        v = str(js.auriLoad(name))
        if not v:
            return default
        try:
            return json.loads(v)
        except ValueError:
            return default

    def save(self, name, obj):
        js.auriSave(name, json.dumps(obj))
