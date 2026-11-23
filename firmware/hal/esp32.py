# Hardware layer for MicroPython on ESP32-S3. Untested until the bench prototype (phase H0).
import json
import time
import machine
import network
import random

from hal import board

W, H = 84, 48


class PCD8544:
    def __init__(self):
        self.spi = machine.SPI(1, baudrate=4_000_000, sck=machine.Pin(board.LCD_SCLK), mosi=machine.Pin(board.LCD_SDIN))
        self.dc = machine.Pin(board.LCD_DC, machine.Pin.OUT)
        self.ce = machine.Pin(board.LCD_SCE, machine.Pin.OUT, value=1)
        self.rst = machine.Pin(board.LCD_RES, machine.Pin.OUT, value=1)
        self.rst(0)
        time.sleep_ms(10)
        self.rst(1)
        self.cmd(0x21, 0x80 | board.LCD_VOP, 0x04, 0x14, 0x20, 0x0C)

    def cmd(self, *c):
        self.dc(0)
        self.ce(0)
        self.spi.write(bytes(c))
        self.ce(1)

    def show(self, buf):
        self.cmd(0x80, 0x40)
        self.dc(1)
        self.ce(0)
        self.spi.write(buf)
        self.ce(1)


class Keypad:
    def __init__(self):
        self.rows = [machine.Pin(p, machine.Pin.OUT, value=1) for p in board.KEY_ROWS]
        self.cols = [machine.Pin(p, machine.Pin.IN, machine.Pin.PULL_UP) for p in board.KEY_COLS]
        self.state = set()

    def scan(self):
        now = set()
        for r, rp in enumerate(self.rows):
            rp(0)
            for c, cp in enumerate(self.cols):
                if not cp():
                    k = board.KEYMAP[r][c]
                    if k:
                        now.add(k)
            rp(1)
        ev = [('down', k) for k in now - self.state] + [('up', k) for k in self.state - now]
        self.state = now
        return ev


class ESP32Hal:
    def __init__(self):
        self.lcd = PCD8544()
        self.keys = Keypad()
        self.bl = machine.PWM(machine.Pin(board.BACKLIGHT), freq=1000, duty_u16=0)
        self.vib = machine.Pin(board.VIBRA, machine.Pin.OUT, value=0)
        self.lit_until = 0
        self.wlan = network.WLAN(network.STA_IF)

    def ticks_ms(self):
        return time.ticks_ms()

    def localtime(self):
        return time.localtime(time.time() + board.TZ_OFFSET)

    def events(self):
        if self.lit_until and time.ticks_diff(time.ticks_ms(), self.lit_until) > 0:
            self.bl.duty_u16(0)
            self.lit_until = 0
        return self.keys.scan()

    def show(self, buf):
        self.lcd.show(buf)

    def light(self, on):
        self.bl.duty_u16(40000 if on else 0)
        self.lit_until = time.ticks_add(time.ticks_ms(), 15000) if on else 0

    def vibrate(self, ms):
        self.vib(1)
        time.sleep_ms(ms)
        self.vib(0)

    def beep(self, freq, ms):
        pass

    def wifi_level(self):
        if not self.wlan.isconnected():
            return 0
        rssi = self.wlan.status('rssi')
        return 4 if rssi > -55 else 3 if rssi > -65 else 2 if rssi > -75 else 1

    def battery_level(self):
        return 4

    def random(self, n):
        return random.getrandbits(16) % n

    def sleep_ms(self, ms):
        time.sleep_ms(ms)

    def running(self):
        return True

    def request(self, method, url, body=None, token=None):
        import requests
        h = {'Content-Type': 'application/json'}
        if token:
            h['Authorization'] = 'Bearer ' + token
        r = requests.request(method, url, data=json.dumps(body) if body is not None else None, headers=h)
        try:
            return r.json()
        finally:
            r.close()

    def load(self, name, default):
        try:
            with open('/data/' + name + '.json') as f:
                return json.load(f)
        except (OSError, ValueError):
            return default

    def save(self, name, obj):
        try:
            import os
            os.mkdir('/data')
        except OSError:
            pass
        with open('/data/' + name + '.json', 'w') as f:
            json.dump(obj, f)
