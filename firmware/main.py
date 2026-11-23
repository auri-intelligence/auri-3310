import json
import network
import ntptime

from auri.core import System
from apps.home import Home
from hal.esp32 import ESP32Hal

with open('config.json') as f:
    cfg = json.load(f)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if cfg.get('wifi_ssid'):
    wlan.connect(cfg['wifi_ssid'], cfg.get('wifi_password', ''))

hal = ESP32Hal()
s = System(hal, cfg)
s.push(Home(s))
synced = False
while True:
    if not synced and wlan.isconnected():
        try:
            ntptime.settime()
            synced = True
        except OSError:
            pass
    s.step()
    hal.sleep_ms(20)
