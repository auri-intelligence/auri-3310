"""Confronta byte per byte la grafica di AurI OS: MicroPython del browser (framebuf, come sul Nokia) contro
CPython (disegno in Python). Serve dopo ogni modifica a auri/gfx.py: py tools/confronta_framebuf.py
(serve.py acceso sulla porta 8000)."""
import os, sys, json, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import banco_telefono as B
import subprocess, urllib.request
ch = subprocess.Popen([B.CHROME, '--headless=new', '--remote-debugging-port=%d' % B.PORTA, '--user-data-dir=' + B.ROOT + '/tmp/banco-profilo2', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(40):
        try:
            tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json' % B.PORTA, timeout=2).read()); break
        except OSError: time.sleep(0.5)
    c = B.CDP([t for t in tabs if t['type'] == 'page'][0]['webSocketDebuggerUrl'])
    c('Runtime.enable'); c('Emulation.setCPUThrottlingRate', rate=1)
    c('Page.navigate', url='http://127.0.0.1:8000/web/#online&banco')
    B.aspetta(c, "typeof auriPy === 'function' && document.body.dataset.app === 'Spento'", 90)
    code = r'''
import js
exec(open('/web_scena.py').read())
from auri.gfx import Canvas, _fb
from auri import icons
js.window.auriMis = ('FB ' if _fb else 'PY ') + chr(10).join(scena(Canvas, icons))
'''
    src = open(os.path.join(ROOT, 'tools', 'scena_gfx.py')).read()
    c.js("auriPy(%s)" % json.dumps("open('/web_scena.py','w').write(%r)" % src))
    c.js("auriPy(%s)" % json.dumps(code))
    w = (c.js('window.auriMis') or '')
    sys.path.insert(0, os.path.join(ROOT, 'firmware')); sys.path.insert(0, os.path.join(ROOT, 'tools'))
    from auri.gfx import Canvas
    from auri import icons
    from scena_gfx import scena
    cp = scena(Canvas, icons)
    wl = w[3:].split(chr(10))
    print('browser:', 'framebuf' if w.startswith('FB') else 'SENZA framebuf')
    diverse = [b.split(':')[0] for a, b in zip(wl, cp) if a != b]
    print('funzioni grafiche confrontate: %d, diverse: %s' % (len(cp), diverse or 'nessuna'))
    if diverse or len(wl) != len(cp):
        sys.exit(1)
    print(c.js("auriLogRows().filter(r => r.l === 'ERR').map(r => r.m).join(' // ')"))
finally:
    ch.terminate()
