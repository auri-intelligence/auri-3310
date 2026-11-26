"""Banco di prova "come il Nokia vero" (ESP32-S3 N8R8 con MicroPython): stesso AurI OS, stesso MicroPython,
ma CPU rallentata fino alla velocita' stimata dell'ESP32 e memoria di MicroPython limitata.

  py tools/banco_nokia.py [--esp 400] [--heap 1024] [--secondi 12] [--nota "..."]

--esp   velocita' bersaglio in migliaia di giri/s del ciclo di calibrazione (vedi CALIBRA). 400 e' una stima
        prudente per l'ESP32-S3 a 240 MHz con l'heap in PSRAM: da rimisurare sull'hardware vero (fase H0).
--heap  memoria di MicroPython in KB (1024 = caso peggiore realistico; 256 = estremo).

Il giro: accensione, ogni voce del menu principale con tasti a raffica, ogni gioco (partita con tasti a
raffica fino al game over), Impostazioni in profondita', AurI con un testo T9 lungo, batteria scarica,
uscite e rientri veloci. Per ogni app: passi, tempo medio e massimo di s.step(), memoria libera minima.
Rapporti in tmp/banco/nokia-<ora>.txt e storico in tmp/banco/storico_nokia.csv.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banco_telefono import CDP, CHROME, ROOT, aspetta  # noqa: E402

OUT = os.path.join(ROOT, 'tmp', 'banco')
PORTA = 9334

CALIBRA = r'''
import time, js
def _cal(n):
    a = time.ticks_us()
    x = 0
    for i in range(n):
        x = (x + i * 3) & 0xFFFF
    return time.ticks_diff(time.ticks_us(), a)
_cal(2000)
js.window.auriCal = 60000 * 1000000 // max(1, _cal(60000))   # giri al secondo
'''

STRUMENTI = r'''
import time, gc, js
_P = {}
_mem = [gc.mem_alloc()]          # picco di memoria USATA (l heap del browser si allarga da solo)
_orig = s.step
_k = [0]
def _step():
    a = time.ticks_us()
    _orig()
    d = time.ticks_diff(time.ticks_us(), a)
    n = type(s.top).__name__
    e = _P.get(n)
    if e is None:
        e = _P[n] = [0, 0, 0]
    e[0] += 1
    e[1] += d
    if d > e[2]:
        e[2] = d
    _k[0] += 1
    if _k[0] % 25 == 0:
        m = gc.mem_alloc()
        if m > _mem[0]:
            _mem[0] = m
js.window.auriStepFn = _step
def _dump():
    gc.collect()
    js.window.auriProf = json.dumps({'app': _P, 'mem_picco': _mem[0], 'mem_fine': gc.mem_alloc()})
import json
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--esp', type=float, default=400)
    ap.add_argument('--heap', type=int, default=1024)
    ap.add_argument('--secondi', type=float, default=12)
    ap.add_argument('--headless', action='store_true')
    ap.add_argument('--nota', default='')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    prof = os.path.join(ROOT, 'tmp', 'banco-profilo-nokia')
    args = [CHROME, '--remote-debugging-port=%d' % PORTA, '--user-data-dir=' + prof, '--no-first-run',
            '--no-default-browser-check', '--window-size=460,1000', 'about:blank']
    if a.headless:
        args.insert(1, '--headless=new')
    chrome = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rap = []

    def dice(s):
        print(s, flush=True)
        rap.append(s)

    c = None
    try:
        tabs = None
        for _ in range(40):
            try:
                tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORTA, timeout=2).read())
                break
            except OSError:
                time.sleep(0.5)
        c = CDP([t for t in tabs if t.get('type') == 'page'][0]['webSocketDebuggerUrl'])
        for d in ('Page', 'Runtime'):
            c(d + '.enable')
        c('Page.bringToFront')
        c('Emulation.setFocusEmulationEnabled', enabled=True)
        c('Page.navigate', url='http://127.0.0.1:8000/web/#nokia&banco&heap=%d' % a.heap)
        aspetta(c, "typeof auriPy === 'function' && document.body.dataset.app === 'Spento'", 90)

        # calibrazione: velocita' del MicroPython del browser senza freni -> freno per arrivare all'ESP32
        c.js("auriPy(%s)" % json.dumps(CALIBRA))
        veloce = c.js("window.auriCal") or 1
        freno = max(1.0, min(80.0, veloce / (a.esp * 1000)))
        c('Emulation.setCPUThrottlingRate', rate=freno)
        c.js("auriPy(%s)" % json.dumps(CALIBRA))
        dopo = c.js("window.auriCal") or 1
        dice('Banco Nokia: browser %dk giri/s -> freno CPU %.1fx -> %dk giri/s (bersaglio ESP32 %dk), heap %d KB %s'
             % (veloce // 1000, freno, dopo // 1000, a.esp, a.heap, ('- ' + a.nota) if a.nota else ''))

        c.js("auriLogClear()")
        c.js("auriPy(%s)" % json.dumps(STRUMENTI))
        t0 = time.time()
        c.js("auriPy('s.power_on()')")
        ok = aspetta(c, "document.body.dataset.app === 'Home'", 90)
        dice('Accensione fino alla Home: %.1f s%s' % (time.time() - t0, '' if ok else ' (NON arrivata)'))

        # tasti: pressione breve, a raffica (seme fisso: giri ripetibili)
        c.js(r"""window.banco = {
          seed: 12345,
          rnd() { this.seed = (this.seed * 1103515245 + 12345) & 0x7fffffff; return this.seed / 0x7fffffff; },
          async tap(k, ms = 90, gap = 120) { auriPress(k); await new Promise(r => setTimeout(r, ms)); auriRelease(k); await new Promise(r => setTimeout(r, gap)); },
          async raffica(n, tasti) { for (let i = 0; i < n; i++) await this.tap(tasti[Math.floor(this.rnd() * tasti.length)], 40 + this.rnd() * 120, 30 + this.rnd() * 150); },
          async lungo(k, ms = 1200) { auriPress(k); await new Promise(r => setTimeout(r, ms)); auriRelease(k); await new Promise(r => setTimeout(r, 300)); },
        };""")
        TASTI = "['navi','up','down','1','2','3','4','5','6','7','8','9','0','*','#']"

        def home():
            c.js("banco.lungo('c')")
            aspetta(c, "document.body.dataset.app === 'Home'", 15)

        # 1) ogni voce del menu principale, tasti a raffica dentro
        voci = c.js("auriPy('from apps.home import main_menu; js.window.auriVoci = len(main_menu(s).items)') && window.auriVoci") or 8
        for i in range(voci):
            home()
            c.js("(async () => { await banco.tap('navi', 90, 500); for (let j = 0; j < %d; j++) await banco.tap('down', 60, 250); await banco.tap('navi', 90, 800); })()" % i)
            time.sleep(1.5 + i * 0.3)
            app = c.js("document.body.dataset.app")
            c.js("banco.raffica(%d, %s)" % (int(a.secondi * 4), TASTI))
            time.sleep(a.secondi)
            dice('  menu %d -> %s (raffica %d s)' % (i, app, a.secondi))

        # 2) ogni gioco: partita con tasti a raffica
        giochi = ['volo', 'corsie', 'incastro', 'rompimuro', 'trefila', 'salisali', 'catapulta', 'snake']
        c.js("auriPy(\"s.hal.save('g_nome', {'nome': 'BANCO'})\")")
        for g in giochi:
            home()
            if g == 'snake':
                c.js("auriPy('from apps.snake import Snake; s.push(Snake(s))')")
            else:
                cls = {'volo': 'Volo', 'corsie': 'Corsie', 'incastro': 'Incastro', 'rompimuro': 'Rompimuro',
                       'trefila': 'TreFila', 'salisali': 'SaliSali', 'catapulta': 'Catapulta'}[g]
                c.js("auriPy(%s)" % json.dumps('from apps.giochi.%s import %s; s.push(%s(s))' % (g, cls, cls)))
            time.sleep(0.8)
            c.js("banco.tap('5')")
            c.js("banco.raffica(%d, ['2','4','5','6','8','navi','up','down'])" % int(a.secondi * 5))
            time.sleep(a.secondi + 1)
            dice('  gioco %s -> %s' % (g, c.js("document.body.dataset.app")))

        # 3) Impostazioni in profondita' (tutte le voci, avanti e indietro)
        home()
        c.js("auriPy('from apps.impostazioni import Impostazioni; s.push(Impostazioni(s))')")
        c.js("(async () => { for (let k = 1; k <= 10; k++) { await banco.tap(String(k % 10), 80, 600); await banco.raffica(6, ['up','down','navi']); await banco.tap('c', 80, 300); await banco.tap('c', 80, 300); } })()")
        time.sleep(a.secondi * 2)
        dice('  impostazioni a raffica -> %s' % c.js("document.body.dataset.app"))

        # 4) AurI: testo T9 lungo (sul Nokia senza bridge: deve dirlo, non rompersi)
        home()
        c.js("auriPy('s.assistant()')")
        time.sleep(1)
        c.js("(async () => { await banco.tap('navi', 90, 400); for (let j = 0; j < 60; j++) await banco.tap(String(2 + j % 8), 50, j % 3 ? 90 : 1100); await banco.tap('navi', 90, 500); })()")
        time.sleep(a.secondi + 8)
        dice('  AurI con testo lungo -> %s' % c.js("document.body.dataset.app"))

        # 5) batteria scarica, poi entrate e uscite veloci
        c.js("(() => { const i = [...document.querySelectorAll('label')].find(l => l.textContent.startsWith('Batteria')).querySelector('input'); i.value = 4; i.dispatchEvent(new Event('input')); })()")
        time.sleep(3)
        dice('  batteria al 4%% -> %s' % c.js("document.body.dataset.app"))
        c.js("(() => { const i = [...document.querySelectorAll('label')].find(l => l.textContent.startsWith('Batteria')).querySelector('input'); i.value = 80; i.dispatchEvent(new Event('input')); })()")
        home()
        c.js("(async () => { for (let j = 0; j < 25; j++) { await banco.tap('navi', 50, 60); await banco.tap('navi', 50, 60); await banco.tap('c', 50, 40); await banco.tap('c', 50, 40); } })()")
        time.sleep(10)

        # risultati
        c.js("auriPy('_dump()')")
        prof = json.loads(c.js("window.auriProf") or '{}')
        dice('')
        dice('%-14s %7s %9s %9s' % ('app', 'passi', 'medio ms', 'max ms'))
        peggiore = 0
        for n, (k, tot, mx) in sorted(prof.get('app', {}).items(), key=lambda kv: -kv[1][2]):
            dice('%-14s %7d %9.2f %9.1f' % (n[:14], k, tot / k / 1000, mx / 1000))
            peggiore = max(peggiore, mx / 1000)
        dice('Memoria MicroPython usata: picco %d KB, dopo la pulizia %d KB (budget ESP32: %d KB)'
             % (prof.get('mem_picco', 0) // 1024, prof.get('mem_fine', 0) // 1024, a.heap))
        reg = c.js("auriLogText()") or ''
        errori = [r for r in reg.splitlines() if ' ERR ' in r or ' ATT ' in r]
        dice('Errori e avvisi: %d' % len(errori))
        for e in errori[-15:]:
            dice('  ' + e[:220])
        stamp = time.strftime('%Y%m%d-%H%M%S')
        with open(os.path.join(OUT, 'nokia-%s.txt' % stamp), 'w', encoding='utf-8') as f:
            f.write('\n'.join(rap) + '\n\n--- registro ---\n' + reg)
        nuovo = not os.path.exists(os.path.join(OUT, 'storico_nokia.csv'))
        with open(os.path.join(OUT, 'storico_nokia.csv'), 'a', encoding='utf-8') as f:
            if nuovo:
                f.write('quando;esp_k;heap_kb;nota;peggior_passo_ms;mem_picco_kb;errori\n')
            f.write('%s;%g;%d;%s;%.1f;%d;%d\n' % (stamp, a.esp, a.heap, a.nota, peggiore,
                                                  prof.get("mem_picco", 0) // 1024, len(errori)))
        dice('Rapporto: tmp/banco/nokia-%s.txt' % stamp)
    finally:
        try:
            c.js("dispatchEvent(new Event('pagehide'))")
        except Exception:
            pass
        chrome.terminate()


if __name__ == '__main__':
    sys.exit(main())
