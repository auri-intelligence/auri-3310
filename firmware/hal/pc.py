import json
import os
import random
import threading
import time
import urllib.request
import zlib
import struct

W, H = 84, 48
LIT = ((0x9d, 0xc8, 0x6a), (0x1c, 0x2b, 0x14))
DARK = ((0x7e, 0x8c, 0x6e), (0x22, 0x2a, 0x1e))
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.simdata')


class PCHal:
    def __init__(self, clock=None):
        self.queue = []
        self.buf = bytearray(W * H // 8)
        self.lit_until = 0
        self.on_show = None
        self.on_vibrate = None
        self._clock = clock
        self._t0 = time.monotonic()

    def ticks_ms(self):
        return int((time.monotonic() - self._t0) * 1000)

    def localtime(self):
        if self._clock:
            return self._clock
        return time.localtime()[:8]

    def events(self):
        ev, self.queue = self.queue, []
        return ev

    def press(self, k):
        self.queue.append(('down', k))

    def release(self, k):
        self.queue.append(('up', k))

    def show(self, buf):
        self.buf[:] = buf
        if self.on_show:
            self.on_show()

    def light(self, on):
        self.lit_until = self.ticks_ms() + 15000 if on else 0

    def lit(self):
        return self.ticks_ms() < self.lit_until

    def vibrate(self, ms):
        if self.on_vibrate:
            self.on_vibrate(ms)

    def beep(self, freq, ms):
        try:
            import winsound
            threading.Thread(target=winsound.Beep, args=(freq, ms), daemon=True).start()
        except ImportError:
            pass

    def wifi_level(self):
        return 4

    def battery_level(self):
        return 4

    def random(self, n):
        return random.randrange(n)

    def sleep_ms(self, ms):
        time.sleep(ms / 1000)

    def running(self):
        return True

    def request(self, method, url, body=None, token=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header('Content-Type', 'application/json')
        if token:
            req.add_header('Authorization', 'Bearer ' + token)
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())

    def load(self, name, default):
        try:
            with open(os.path.join(DATA_DIR, name + '.json')) as f:
                return json.load(f)
        except (OSError, ValueError):
            return default

    def save(self, name, obj):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(os.path.join(DATA_DIR, name + '.json'), 'w') as f:
            json.dump(obj, f)

    def pixel(self, x, y):
        return (self.buf[(y >> 3) * W + x] >> (y & 7)) & 1

    def save_png(self, path, scale=6, lit=True):
        bg, fg = LIT if lit else DARK
        rows = []
        for y in range(H * scale):
            row = bytearray([0])
            for x in range(W * scale):
                px, py = x // scale, y // scale
                gap = x % scale == scale - 1 or y % scale == scale - 1
                on = self.pixel(px, py)
                c = fg if on and not gap else bg
                row += bytes(c)
            rows.append(bytes(row))
        raw = zlib.compress(b''.join(rows), 9)

        def chunk(tag, data):
            return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W * scale, H * scale, 8, 2, 0, 0, 0))
        png += chunk(b'IDAT', raw) + chunk(b'IEND', b'')
        with open(path, 'wb') as f:
            f.write(png)
