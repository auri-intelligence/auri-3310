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


class SHT40:
    ADDR = 0x44

    def __init__(self, i2c):
        self.i2c = i2c

    def read(self):
        self.i2c.writeto(self.ADDR, b'\xfd')
        time.sleep_ms(10)
        d = self.i2c.readfrom(self.ADDR, 6)
        t = -45 + 175 * ((d[0] << 8) | d[1]) / 65535
        h = -6 + 125 * ((d[3] << 8) | d[4]) / 65535
        return round(t, 1), round(max(0, min(100, h)))


class ESP32Hal:
    def __init__(self):
        self.lcd = PCD8544()
        self.keys = Keypad()
        self.pwr = machine.Pin(board.POWER_KEY, machine.Pin.IN, machine.Pin.PULL_UP)
        self.pwr_down = False
        self.adc = machine.ADC(machine.Pin(board.BAT_ADC))
        self.adc.atten(machine.ADC.ATTN_11DB)
        self.chg = machine.Pin(board.CHG_DET, machine.Pin.IN, machine.Pin.PULL_UP)
        self.spk = machine.PWM(machine.Pin(board.SPEAKER), freq=1000, duty_u16=0)
        self.tone_until = 0
        self.bl = machine.PWM(machine.Pin(board.BACKLIGHT), freq=1000, duty_u16=0)
        self.vib = machine.Pin(board.VIBRA, machine.Pin.OUT, value=0)
        self.lit_until = 0
        self.wlan = network.WLAN(network.STA_IF)
        self.i2c = machine.I2C(0, scl=machine.Pin(board.I2C_SCL), sda=machine.Pin(board.I2C_SDA), freq=400000)
        found = self.i2c.scan()
        self.sht = SHT40(self.i2c) if SHT40.ADDR in found else None

    def ticks_ms(self):
        return time.ticks_ms()

    def localtime(self):
        return time.localtime(time.time() + board.TZ_OFFSET)

    def events(self):
        if self.lit_until and time.ticks_diff(time.ticks_ms(), self.lit_until) > 0:
            self.bl.duty_u16(0)
            self.lit_until = 0
        if self.tone_until and time.ticks_diff(time.ticks_ms(), self.tone_until) > 0:
            self.spk.duty_u16(0)
            self.tone_until = 0
        ev = self.keys.scan()
        down = not self.pwr()
        if down != self.pwr_down:
            self.pwr_down = down
            ev.append(('down' if down else 'up', 'power'))
        return ev

    def show(self, buf):
        self.lcd.show(buf)

    def light(self, on, ms=15000):
        # ms < 0: always on
        self.bl.duty_u16(40000 if on else 0)
        self.lit_until = time.ticks_add(time.ticks_ms(), ms) if on and ms >= 0 else 0

    def vibrate(self, ms):
        self.vib(1)
        time.sleep_ms(ms)
        self.vib(0)

    def beep(self, freq, ms, vol=3):
        # non-blocking: events() switches the tone off when its time is up
        if not vol:
            return
        self.spk.freq(freq)
        self.spk.duty_u16(vol * 6000)
        self.tone_until = time.ticks_add(time.ticks_ms(), ms)

    def wifi_level(self):
        if not self.wlan.isconnected():
            return 0
        rssi = self.wlan.status('rssi')
        return 4 if rssi > -55 else 3 if rssi > -65 else 2 if rssi > -75 else 1

    def battery(self):
        mv = sum(self.adc.read_uv() for _ in range(8)) // 8000 * board.BAT_DIVIDER
        pct = (mv - board.BAT_EMPTY_MV) * 100 // (board.BAT_FULL_MV - board.BAT_EMPTY_MV)
        return int(max(0, min(100, pct))), not self.chg()

    def battery_level(self):
        return min(4, (self.battery()[0] + 12) // 25)

    def power_off(self):
        # LCD in power-down, everything off, then deep sleep until Power is pressed again.
        import esp32
        self.lcd.cmd(0x24)
        self.bl.duty_u16(0)
        self.spk.duty_u16(0)
        self.wlan.active(False)
        while not self.pwr():
            time.sleep_ms(10)
        esp32.wake_on_ext0(self.pwr, esp32.WAKEUP_ALL_LOW)
        machine.deepsleep()

    def sensors(self):
        out = {}
        if self.sht:
            out['temperature'], out['humidity'] = self.sht.read()
        return out

    def voice_start(self):
        return False

    def voice_stop(self, url, params, token):
        pass

    def voice_poll(self):
        return {'error': 'Microfono non ancora collegato'}

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
