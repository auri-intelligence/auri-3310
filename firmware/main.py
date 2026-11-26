import json
import network
import ntptime

from auri.core import System
from hal.esp32 import ESP32Hal

with open('config.json') as f:
    cfg = json.load(f)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if cfg.get('wifi_ssid'):
    wlan.connect(cfg['wifi_ssid'], cfg.get('wifi_password', ''))

hal = ESP32Hal()
s = System(hal, cfg)
# woken by the Power key (or first power-up): real start-up sequence
s.power_on()
synced = False
import time
PASSO = 20                                   # ms: il sistema e i giochi contano su un ritmo regolare
prossimo = time.ticks_ms()
while True:
    if not synced and wlan.isconnected():
        try:
            ntptime.settime()
            synced = True
        except OSError:
            pass
    s.step()
    # passo fisso: si dorme solo il tempo che avanza (prima 20 ms fissi in piu' del lavoro, quindi i giochi
    # rallentavano quando il passo era pesante); se si e' in ritardo non si accumula
    prossimo = time.ticks_add(prossimo, PASSO)
    resto = time.ticks_diff(prossimo, time.ticks_ms())
    if resto > 0:
        hal.sleep_ms(resto)
    else:
        prossimo = time.ticks_ms()
