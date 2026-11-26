"""Banco di prova "come un telefono": Chrome guidato via DevTools Protocol (solo libreria standard).

  py tools/banco_telefono.py [--cpu 4] [--rete] [--modello mini] [--headless] [--nota "cosa ho cambiato"]

Condizioni: user agent Android + schermo 412x915 + tocco, CPU rallentata (--cpu, predefinito 4x come un
telefono di fascia media), rete 4G se --rete (lenta: il modello si riscarica). Il sito e' quello locale
(serve.py sulla porta 8000) in modalita' #online, cioe' senza bridge come il sito pubblico.

Giro fisso: accensione -> AurI -> cervello acceso -> 2 domande -> gioco Flappy 15 s.
Uscita: tmp/banco/<ora>.txt (rapporto + registro completo), tmp/banco/<ora>.png e una riga in
tmp/banco/storico.csv per confrontare prima/dopo ogni modifica.
"""
import argparse
import base64
import json
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'tmp', 'banco')
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORTA = 9333
UA = ('Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/158.0.0.0 Mobile Safari/537.36')


# --- WebSocket minimo (RFC 6455), quanto basta per il DevTools Protocol ---------------------
class WS:
    def __init__(self, url):
        assert url.startswith('ws://')
        host, path = url[5:].split('/', 1)
        h, p = host.split(':')
        self.s = socket.create_connection((h, int(p)), timeout=300)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(('GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                        'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n' % (path, host, key)).encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            buf += self.s.recv(4096)
        assert b' 101 ' in buf.split(b'\r\n')[0], buf[:200]
        self.rest = buf.split(b'\r\n\r\n', 1)[1]

    def _read(self, n):
        while len(self.rest) < n:
            d = self.s.recv(1 << 16)
            if not d:
                raise ConnectionError('chiuso')
            self.rest += d
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def send(self, text):
        data = text.encode()
        head = bytearray([0x81])
        n = len(data)
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head += struct.pack('>H', n)
        else:
            head.append(0x80 | 127)
            head += struct.pack('>Q', n)
        mask = os.urandom(4)
        self.s.sendall(bytes(head) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        msg = b''
        while True:
            b0, b1 = self._read(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack('>H', self._read(2))[0]
            elif n == 127:
                n = struct.unpack('>Q', self._read(8))[0]
            data = self._read(n)
            op = b0 & 0x0F
            if op == 9:                      # ping
                continue
            msg += data
            if b0 & 0x80:
                return msg.decode('utf-8', 'replace')


class CDP:
    def __init__(self, ws_url):
        self.ws = WS(ws_url)
        self.n = 0

    def __call__(self, method, **params):
        self.n += 1
        mid = self.n
        self.ws.send(json.dumps({'id': mid, 'method': method, 'params': params}))
        while True:
            r = json.loads(self.ws.recv())
            if r.get('id') == mid:
                if 'error' in r:
                    raise RuntimeError('%s: %s' % (method, r['error']))
                return r.get('result', {})

    def js(self, expr, wait=True):
        r = self('Runtime.evaluate', expression=expr, awaitPromise=wait, returnByValue=True)
        if 'exceptionDetails' in r:
            raise RuntimeError('JS: %s' % r['exceptionDetails'].get('exception', {}).get('description', r))
        return r.get('result', {}).get('value')


def aspetta(c, expr, secondi, passo=0.5):
    fine = time.time() + secondi
    while time.time() < fine:
        try:
            v = c.js(expr)
            if v:
                return v
        except RuntimeError:
            pass
        time.sleep(passo)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cpu', type=float, default=4)
    ap.add_argument('--rete', action='store_true')
    ap.add_argument('--modello', default='mini')
    ap.add_argument('--headless', action='store_true')
    ap.add_argument('--nota', default='')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    prof = os.path.join(ROOT, 'tmp', 'banco-profilo')      # resta: il modello scaricato si riusa
    args = [CHROME, '--remote-debugging-port=%d' % PORTA, '--user-data-dir=' + prof, '--no-first-run',
            '--no-default-browser-check', '--window-size=460,1000', '--enable-unsafe-webgpu',
            '--autoplay-policy=no-user-gesture-required', 'about:blank']
    if a.headless:
        args.insert(1, '--headless=new')
    chrome = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rapporto, misure = [], {}

    def dice(s):
        print(s, flush=True)
        rapporto.append(s)

    try:
        tabs = None
        for _ in range(40):
            try:
                tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORTA, timeout=2).read())
                break
            except OSError:
                time.sleep(0.5)
        page = [t for t in tabs if t.get('type') == 'page'][0]
        c = CDP(page['webSocketDebuggerUrl'])
        for d in ('Page', 'Runtime', 'Network'):
            c(d + '.enable')
        c('Emulation.setUserAgentOverride', userAgent=UA, platform='Linux armv8l')
        c('Emulation.setDeviceMetricsOverride', width=412, height=915, deviceScaleFactor=2.6, mobile=True)
        c('Emulation.setTouchEmulationEnabled', enabled=True, maxTouchPoints=5)
        c('Emulation.setCPUThrottlingRate', rate=a.cpu)
        c('Page.bringToFront')
        c('Emulation.setFocusEmulationEnabled', enabled=True)   # il browser disegna come se fosse in primo piano
        if a.rete:
            c('Network.emulateNetworkConditions', offline=False, latency=85,
              downloadThroughput=9 * 1024 * 1024 / 8, uploadThroughput=1.5 * 1024 * 1024 / 8)
        dice('Banco: CPU %gx, rete %s, modello %s %s' % (a.cpu, '4G' if a.rete else 'piena', a.modello,
                                                         ('- ' + a.nota) if a.nota else ''))
        t0 = time.time()
        c('Page.navigate', url='http://127.0.0.1:8000/web/#online&banco')
        aspetta(c, "typeof auriPy === 'function' && document.body.dataset.app === 'Spento'", 90)
        c.js("auriLogClear()")                    # ogni giro parte con il registro pulito
        c.js("auriPy('s.power_on()')")
        ok = aspetta(c, "document.body.dataset.app === 'Home'", 60)
        misure['avvio_s'] = round(time.time() - t0, 1)
        dice('Accensione fino alla Home: %s s%s' % (misure['avvio_s'], '' if ok else ' (NON arrivato)'))
        c.js("auriPy('s.assistant()')")
        aspetta(c, "document.body.dataset.app === 'Assistente'", 10)

        # cervello
        t1 = time.time()
        c.js("auriAiStart(%s)" % json.dumps(a.modello))
        fase = aspetta(c, "(() => { const i = JSON.parse(auriAiInfo()); return (i.phase === 'ready' || i.phase === 'err') && i.phase; })()", 600, 1)
        misure['cervello_s'] = round(time.time() - t1, 1)
        dice('Cervello %s: %s dopo %s s' % (a.modello, fase, misure['cervello_s']))

        # domande
        for n, dom in enumerate(('Ciao, chi sei?', 'Cosa sai fare?'), 1):
            t2 = time.time()
            prima = c.js("auriLogRows().filter(r => /Risposta finita|Errore durante/.test(r.m)).length")
            c.js("auriPy(%s)" % json.dumps("s.top._send(%r)" % dom))
            fatto = aspetta(c, "auriLogRows().filter(r => /Risposta finita|Errore durante/.test(r.m)).length > %d && 'fatto'" % prima, 180, 0.25)
            righe = c.js("auriLogRows().filter(r => r.a === 'cervello').slice(-3).map(r => r.m).join(' / ')") or ''
            dice('   registro: ' + righe[:200])
            risposta = c.js("JSON.parse(auriAiPoll()).text || JSON.parse(auriAiPoll()).error || ''") or ''
            misure['domanda%d_s' % n] = round(time.time() - t2, 1)
            dice('Domanda %d "%s": %s s, stato %s -> %s' % (n, dom, misure['domanda%d_s' % n], fatto, risposta[:120]))

        # gioco: Flappy 15 s premendo 5
        c.js("auriPy('from apps.giochi.volo import Volo; s.push(Volo(s))')")
        time.sleep(1)
        c.js("window.auriPerf && (window.auriPerf.max = 0)")
        c.js("(async () => { const w = ms => new Promise(r => setTimeout(r, ms)); for (let i = 0; i < 50; i++) { auriPress('5'); await w(60); auriRelease('5'); await w(240); } })()", wait=False)
        time.sleep(16)
        perf = c.js("JSON.stringify(window.auriPerf)")
        p = json.loads(perf) if perf else {}
        misure.update({'passo_ms': round(p.get('step', 0), 2), 'picco_ms': round(p.get('max', 0), 1),
                       'disegno_ms': round(p.get('draw', 0), 2)})
        dice('Gioco: passo medio %s ms, picco %s ms, disegno %s ms' % (misure['passo_ms'], misure['picco_ms'], misure['disegno_ms']))

        png = c('Page.captureScreenshot', format='png')['data']
        stamp = time.strftime('%Y%m%d-%H%M%S')
        open(os.path.join(OUT, stamp + '.png'), 'wb').write(base64.b64decode(png))
        registro = c.js("auriLogText()") or ''
        errori = [r for r in registro.splitlines() if ' ERR ' in r or ' ATT ' in r]
        misure['errori'] = len(errori)
        dice('Errori e avvisi: %d' % len(errori))
        for e in errori[-10:]:
            dice('  ' + e)
        with open(os.path.join(OUT, stamp + '.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(rapporto) + '\n\n--- registro ---\n' + registro)
        nuovo = not os.path.exists(os.path.join(OUT, 'storico.csv'))
        with open(os.path.join(OUT, 'storico.csv'), 'a', encoding='utf-8') as f:
            campi = ['avvio_s', 'cervello_s', 'domanda1_s', 'domanda2_s', 'passo_ms', 'picco_ms', 'disegno_ms', 'errori']
            if nuovo:
                f.write('quando;cpu;rete;modello;nota;' + ';'.join(campi) + '\n')
            f.write('%s;%g;%s;%s;%s;%s\n' % (stamp, a.cpu, int(a.rete), a.modello, a.nota,
                                             ';'.join(str(misure.get(k, '')) for k in campi)))
        dice('Rapporto: tmp/banco/%s.txt' % stamp)
    finally:
        try:
            c.js("dispatchEvent(new Event('pagehide'))")   # chiusura pulita: niente falso crash nel registro
            c('Page.navigate', url='about:blank')
            time.sleep(1)
        except Exception:
            pass
        chrome.terminate()


if __name__ == '__main__':
    sys.exit(main())
