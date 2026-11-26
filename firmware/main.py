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
ntp_t = prossimo
# watchdog: se il ciclo si pianta per 10 s il chip si riavvia da solo (il telefono non ha un tasto di reset)
try:
    from machine import WDT
    wdt = WDT(timeout=10000)
except Exception:
    wdt = None
while True:
    # ora da internet: un tentativo al minuto al massimo (ognuno puo' bloccare ~1 s se manca internet)
    if not synced and time.ticks_diff(time.ticks_ms(), ntp_t) >= 0 and wlan.isconnected():
        ntp_t = time.ticks_add(time.ticks_ms(), 60000)
        try:
            ntptime.settime()
            synced = True
        except Exception:
            pass
    try:
        s.step()
    except Exception as e:          # un'app che si rompe non deve congelare il telefono: si torna alla Home
        print('errore:', e)
        try:
            s.home()
            s.toast('Errore', 1500)
        except Exception:
            pass
    if wdt:
        wdt.feed()
    # passo fisso: si dorme solo il tempo che avanza (prima 20 ms fissi in piu' del lavoro, quindi i giochi
    # rallentavano quando il passo era pesante); se si e' in ritardo non si accumula
    prossimo = time.ticks_add(prossimo, PASSO)
    resto = time.ticks_diff(prossimo, time.ticks_ms())
    if resto > 0:
        hal.sleep_ms(resto)
    else:
        prossimo = time.ticks_ms()
