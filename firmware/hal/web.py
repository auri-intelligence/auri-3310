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
        try:
            return int(json.loads(str(js.auriNet()))['bars'])
        except Exception:
            return 4

    # --- connessioni (web/auri-conn.js): rete vera del dispositivo, Bluetooth del browser, GPS ---
    def net_info(self):
        try:
            return json.loads(str(js.auriNet()))
        except Exception:
            return {'online': True, 'tipo': '', 'eff': '', 'bars': 4, 'down': 0, 'bt': 0}

    def bt_set(self, on):
        pass        # il browser non lascia accendere/spegnere la radio: si ricorda solo la scelta

    def wifi_set(self, on):
        pass

    def loc_start(self):
        try:
            js.auriLocStart()
        except Exception:
            pass            # pagina senza GPS (vecchia o modalita' Nokia): loc_poll lo dice

    def loc_stop(self):
        try:
            js.auriLocStop()
        except Exception:
            pass

    def loc_poll(self):
        try:
            return json.loads(str(js.auriLocPoll()))
        except Exception:
            return {'on': False, 'err': 'no_gps', 'pos': None}

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

    def track(self, name):
        try:
            js.auriTrack(name)
        except Exception:
            pass

    def sensors(self):
        return json.loads(str(js.auriSensors()))

    def voice_start(self):
        return bool(js.auriVoiceStart())

    def voice_stop(self, url, params, token):
        js.auriVoiceStop(url, json.dumps(params), token or '')

    def voice_poll(self):
        r = str(js.auriVoicePoll())
        return json.loads(r) if r else None

    # --- cervello locale: il modello gira nel browser con WebGPU (web/auri-llm.js) ---
    def ai_ok(self):
        try:
            return bool(js.auriAiInfo)
        except Exception:
            return False      # pagina vecchia in cache, senza auri-llm.js

    def ai_info(self):
        return json.loads(str(js.auriAiInfo()))

    def ai_models(self):
        return json.loads(str(js.auriAiModels()))

    def ai_start(self, model=''):
        js.auriAiStart(model or '')

    def ai_ask(self, messages, opts=None):
        return str(js.auriAiAsk(json.dumps(messages), json.dumps(opts or {})))

    def ai_poll(self):
        return json.loads(str(js.auriAiPoll()))

    def ai_stop(self):
        js.auriAiStop()

    # --- fotocamera: telefono -> posteriore, computer -> webcam (web/auri-cam.js) ---
    def cam_ok(self):
        try:
            return bool(json.loads(str(js.auriCamInfo()))['ok'])
        except Exception:
            return False

    def cam_start(self):
        js.auriCamStart()

    def cam_stop(self):
        js.auriCamStop()

    def cam_switch(self):
        js.auriCamSwitch()

    def cam_mode(self, m):
        js.auriCamMode(m)

    def cam_poll(self):
        r = json.loads(str(js.auriCamPoll()))
        f = r.pop('frame', '')
        r['frame'] = ubinascii.unhexlify(f) if f else None
        return r

    # --- voce del browser: ascolto (push-to-talk) e lettura ad alta voce ---
    def hear_start(self, lang='it'):
        try:
            return bool(js.auriHearStart(lang))
        except Exception:
            return False

    def hear_stop(self):
        js.auriHearStop()

    def hear_poll(self):
        r = str(js.auriHearPoll())
        return json.loads(r) if r else {'text': '', 'done': 1, 'error': ''}

    def speak(self, text, lang='it'):
        try:
            js.auriSpeak(text, lang)
        except Exception:
            pass

    def speak_stop(self):
        try:
            js.auriSpeakStop()
        except Exception:
            pass

    def random(self, n):
        return int(js.Math.random() * n)

    def sleep_ms(self, ms):
        pass

    def running(self):
        return True

    def request(self, method, url, body=None, token=None):
        if not url:
            return None
        r = js.auriRequest(method, url, json.dumps(body) if body is not None else '', token or '')
        r = str(r)
        if r.startswith('ERR '):
            raise OSError(r[4:])
        return json.loads(r)

    def request_start(self, method, url, body=None, token=None):
        return int(js.auriFetch(method, url, json.dumps(body) if body is not None else '', token or ''))

    def request_poll(self, rid):
        """None = ancora in corso; altrimenti (risultato, errore)."""
        r = str(js.auriFetchPoll(rid))
        if not r:
            return None
        if r.startswith('ERR '):
            return None, r[4:]
        try:
            return json.loads(r[3:]), ''
        except ValueError:
            return None, 'json'

    def load(self, name, default):
        v = str(js.auriLoad(name))
        if not v:
            return default
        try:
            return json.loads(v)
        except ValueError:
            return default

    SEGRETI = ('token', 'wifi_password', 'password', 'scores_key')

    def save(self, name, obj):
        # il localStorage e' in chiaro: chiavi segrete mai salvate, anche se un'app per sbaglio le passa
        if isinstance(obj, dict) and any(k in obj for k in self.SEGRETI):
            obj = {k: v for k, v in obj.items() if k not in self.SEGRETI}
        js.auriSave(name, json.dumps(obj))
