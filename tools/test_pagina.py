"""La pagina del simulatore si carica senza errori JavaScript, da computer e da telefono (emulato).
Un solo errore di sintassi in un file .js spegne voce e cervello: questo test lo ferma prima di pubblicare.
Serve Chrome; il server locale lo accende da solo se non c'e'. py tools/test_pagina.py"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from banco_telefono import CHROME, UA, CDP, aspetta  # noqa: E402

PORTA = 9334
FUNZIONI = ('auriHearStart', 'auriHearStop', 'auriMicLevel', 'auriAiInfo', 'auriAiStart', 'auriSpeak',
            'auriCamInfo', 'auriVoiceStart', 'auriLogRows', 'auriPy')


def server_acceso():
    try:
        socket.create_connection(('127.0.0.1', 8000), timeout=1).close()
        return True
    except OSError:
        return False


def prova(c, nome, telefono):
    if telefono:
        c('Emulation.setUserAgentOverride', userAgent=UA, platform='Linux armv8l')
        c('Emulation.setDeviceMetricsOverride', width=412, height=915, deviceScaleFactor=2.6, mobile=True)
    c('Page.navigate', url='http://127.0.0.1:8000/web/?%s#banco' % nome)
    if not aspetta(c, "typeof auriPy === 'function' && document.body.dataset.app === 'Spento'", 60):
        raise AssertionError('%s: AurI OS non si e acceso' % nome)
    time.sleep(1.5)
    mancano = c.js('%s.filter(f => typeof window[f] !== "function")' % json.dumps(list(FUNZIONI)))
    errori = c.js("auriLogRows().filter(r => r.a === 'js' || r.l === 'ERR').map(r => r.m)")
    assert not mancano, '%s: funzioni mancanti %s' % (nome, mancano)
    assert not errori, '%s: errori %s' % (nome, errori)
    if telefono:   # il pannello nasce chiuso sul telefono
        assert c.js("document.body.classList.contains('closed')"), '%s: pannello aperto' % nome


def main():
    if not os.path.exists(CHROME):
        print('ok  pagina: Chrome non installato, salto')
        return
    srv = None
    if not server_acceso():
        srv = subprocess.Popen([sys.executable, 'serve.py'], cwd=os.path.join(ROOT, 'firmware'),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    prof = os.path.join(ROOT, 'tmp', 'test-pagina-profilo')
    ch = subprocess.Popen([CHROME, '--headless=new', '--remote-debugging-port=%d' % PORTA, '--user-data-dir=' + prof,
                           '--no-first-run', '--no-default-browser-check', 'about:blank'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        for d in ('Page', 'Runtime'):
            c(d + '.enable')
        # registro pulito a ogni prova: niente errori vecchi di altre sessioni
        c('Page.addScriptToEvaluateOnNewDocument', source="try{localStorage.clear()}catch(e){}")
        prova(c, 'computer', False)
        prova(c, 'telefono', True)
        print('ok  pagina: si carica senza errori JS (computer e telefono), %d funzioni presenti' % len(FUNZIONI))
    finally:
        ch.terminate()
        if srv:
            srv.terminate()


if __name__ == '__main__':
    main()
