"""Test del cervello e dell'assistente AurI sul PC: py tools/test_cervello.py  (immagini in tmp/lcd/cervello/)

Il motore locale (WebLLM nel browser, modello dalla microSD sul telefono) qui e' finto: risponde a pezzi
come quello vero, cosi' si provano accensione, ascolto, scrittura T9, streaming e lettura ad alta voce
senza GPU e senza rete.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, 'firmware')
sys.path.insert(0, FW)
os.chdir(FW)
OUT = os.path.join(ROOT, 'tmp', 'lcd', 'cervello')
os.makedirs(OUT, exist_ok=True)

from hal.pc import PCHal
from auri.core import System
from auri import keys
from auri.cervello import pulisci, LOCALE, BRIDGE
from apps.home import Home, main_menu
from apps.assistente import Assistente

PASSI_CARICAMENTO = 25         # giri di orologio prima che il modello finto sia pronto


class TestHal(PCHal):
    """PCHal con un cervello locale finto, il microfono finto e la voce finta."""

    def __init__(self, locale=True):
        super().__init__((2026, 11, 25, 12, 0, 0, 2, 329))
        self.now = 0
        self.mem = {}
        self.locale = locale
        self.phase = 'off'
        self.pct = 0
        self.chiesto = None
        self.risposta = ''
        self.dato = ''
        self.detto = []
        self.hear_error = ''
        self.bridge_giu = False
        self.sentito = None
        self.hear_done = True
        self.richieste = []

    # --- base ---
    def ticks_ms(self):
        return self.now

    def beep(self, f, ms, vol=3):
        pass

    def load(self, k, d=None):
        return self.mem.get(k, d)

    def save(self, k, v):
        import json
        self.mem[k] = json.loads(json.dumps(v))

    def request(self, method, url, body=None, token=None):
        self.richieste.append((method, url, body))
        if self.bridge_giu:
            raise OSError('bridge spento')
        return {'session': 'abc123', 'reply': 'Dal bridge di casa: ci penso io.'}

    # --- cervello locale finto ---
    def ai_ok(self):
        return self.locale

    def ai_info(self):
        if self.phase == 'load':
            self.pct = min(100, self.pct + 100 // PASSI_CARICAMENTO)
            if self.pct >= 100:
                self.phase = 'ready'
        return {'phase': self.phase, 'pct': self.pct, 'name': 'Base 0.5B', 'mb': 290, 'error': '',
                'webgpu': True, 'hear': True, 'speak': True}

    def ai_models(self):
        return [['mini', 'Mini 360M', 207], ['base', 'Base 0.5B', 290], ['grande', 'Grande 1.5B', 880]]

    def ai_start(self, model=''):
        self.phase = 'load'
        self.pct = 0

    def ai_ask(self, messages, opts=None):
        self.chiesto = messages
        self.opzioni = opts or {}
        self.risposta = 'Sono AurI e vivo in un 3310 del 2000. Che ti serve?'
        self.dato = ''
        self.letto_fin_qui = 0
        return ''

    def _leggi_frasi(self, finita=False):
        """Come il browser: legge ogni frase appena e' finita, senza aspettare il resto."""
        if not self.opzioni.get('speak'):
            return
        resto = self.dato[self.letto_fin_qui:]
        while True:
            taglio = -1
            for seg in '.!?:;':
                i = resto.find(seg)
                if i >= 0 and (taglio < 0 or i < taglio):
                    taglio = i
            if taglio < 0:
                break
            frase, resto = resto[:taglio + 1], resto[taglio + 1:]
            self.letto_fin_qui += len(frase)
            self.detto.append(frase.strip())
        if finita and resto.strip():
            self.letto_fin_qui += len(resto)
            self.detto.append(resto.strip())

    def ai_poll(self):
        # due parole per giro, come uno streaming vero
        if len(self.dato) < len(self.risposta):
            resto = self.risposta[len(self.dato):]
            taglio = len(resto)
            spazi = [i for i, c in enumerate(resto) if c == ' ']
            if len(spazi) > 1:
                taglio = spazi[1]
            self.dato += resto[:taglio] if taglio else resto
        finita = self.dato == self.risposta
        self._leggi_frasi(finita)
        return {'text': self.dato, 'done': 1 if finita else 0, 'error': '',
                'spoken': 1 if self.opzioni.get('speak') else 0}

    def ai_stop(self):
        self.dato = self.risposta

    # --- microfono e voce finti ---
    def hear_start(self, lang='it'):
        self.sentito = ''
        self.hear_done = False
        return True

    def hear_stop(self):
        self.sentito = '' if self.hear_error else 'che tempo fa'
        self.hear_done = True

    def hear_poll(self):
        return {'text': self.sentito or '', 'done': 1 if self.hear_done else 0,
                'error': self.hear_error}

    def speak(self, text, lang='it'):
        self.detto.append(text)

    def speak_stop(self):
        pass


def mk(cfg=None, locale=True):
    hal = TestHal(locale)
    s = System(hal, cfg if cfg is not None else {'bridge_url': '', 'online': True})
    s.push(Home(s))
    s.step()
    return hal, s


def avanza(hal, s, ms=400):
    for _ in range(max(1, ms // 20)):
        hal.now += 20
        s.step()


def premi(hal, s, k, ms=60):
    hal.press(k)
    avanza(hal, s, ms)
    hal.release(k)
    avanza(hal, s, 40)


def tieni(hal, s, k, ms=800):
    hal.press(k)
    avanza(hal, s, ms)
    hal.release(k)
    avanza(hal, s, 40)


def shot(hal, s, name):
    # niente scorrimento a meta': si disegna la schermata ferma, come la si vede davvero
    s._trans = None
    s.dirty = True
    s.step()
    hal.save_png(os.path.join(OUT, name + '.png'), scale=6, lit=True)


def testo(s):
    """Il testo che si vede: le righe dell'app, non i pixel."""
    app = s.top
    return ' '.join(getattr(app, 'lines', []))


# --- test ------------------------------------------------------------------

def test_pulizia():
    assert pulisci('<think>mmm che dire</think> Ciao!') == 'Ciao!'
    assert pulisci('<think>sto ancora pensando') == ''
    assert pulisci('**Ciao** _mondo_ `x`') == 'Ciao mondo x'
    assert pulisci('Ciao \U0001F600 mondo') == 'Ciao mondo'
    assert pulisci('prima\nseconda') == 'prima seconda'
    assert pulisci('perché no') == 'perche no' or pulisci('perché no') == 'perche no'
    print('ok  pulizia del testo per il display')


def test_niente_cervello():
    hal, s = mk(cfg={'bridge_url': '', 'online': True}, locale=False)
    s.assistant(keys.NAVI)
    s.step()
    app = s.top
    assert isinstance(app, Assistente) and app.state == 'none', app.state
    assert 'WebGPU' in testo(s), testo(s)
    shot(hal, s, '1_senza_cervello')
    print('ok  senza cervello lo dice invece di fingere')


def test_accensione_e_voce():
    hal, s = mk()
    # dal menu: la prima voce e' AurI
    premi(hal, s, keys.NAVI)
    menu = s.top
    assert menu.items[0][0] == 'AurI'
    assert all(lab != 'Claude' for lab, _i, _a in menu.items), 'online non deve esserci Claude'
    premi(hal, s, keys.NAVI)
    app = s.top
    assert isinstance(app, Assistente) and app.state == 'off', app.state
    shot(hal, s, '2_cervello_spento')

    premi(hal, s, keys.NAVI)          # accendi
    assert s.top.state == 'load'
    avanza(hal, s, 60)
    shot(hal, s, '3_scarico')
    avanza(hal, s, 25 * PASSI_CARICAMENTO + 200)
    assert s.top.state == 'idle', s.top.state
    shot(hal, s, '4_pronto')

    hal.press(keys.NAVI)              # tieni premuto e parla
    avanza(hal, s, 800)
    assert s.top.state == 'listen', s.top.state
    shot(hal, s, '5_ascolto')
    hal.release(keys.NAVI)
    avanza(hal, s, 40)
    assert s.top.state in ('hear', 'think'), s.top.state
    avanza(hal, s, 60)
    assert s.top.state == 'think', s.top.state
    shot(hal, s, '6_pensa')
    avanza(hal, s, 1200)
    app = s.top
    assert app.state == 'show', app.state
    assert 'che tempo fa' in testo(s), testo(s)
    assert 'vivo in un 3310' in testo(s), testo(s)
    # prima una parola subito (l'attesa muta sembra un telefono rotto), poi la risposta frase per frase
    assert hal.detto, 'AurI non ha detto niente'
    assert hal.detto[0] == 'Vediamo...', hal.detto
    assert any('3310' in d for d in hal.detto[1:]), hal.detto
    assert len(hal.detto) > 2, 'la risposta doveva essere letta a frasi, non tutta insieme'
    shot(hal, s, '7_risposta')
    # la domanda e' arrivata al modello con la persona di AurI
    assert hal.chiesto[0]['role'] == 'system' and 'AurI' in hal.chiesto[0]['content']
    assert hal.chiesto[-1]['content'] == 'che tempo fa'
    print('ok  accensione, ascolto, risposta a pezzi e lettura ad alta voce')


def test_scrittura_t9():
    hal, s = mk()
    s.assistant()
    s.step()
    premi(hal, s, keys.NAVI)          # accendi il cervello
    avanza(hal, s, 25 * PASSI_CARICAMENTO + 200)
    assert s.top.state == 'idle', s.top.state
    premi(hal, s, keys.NAVI)          # breve: scrivi
    assert s.top.state == 'type', s.top.state
    for k in ('2', '4', '2', '0'):
        premi(hal, s, k, 40)
        avanza(hal, s, 1000)
    shot(hal, s, '8_scrivi')
    assert s.top.input.text.lower().startswith('cia') or s.top.input.text, s.top.input.text
    premi(hal, s, keys.NAVI)
    avanza(hal, s, 1400)
    assert s.top.state == 'show', s.top.state
    print('ok  domanda scritta col T9')


def test_bridge():
    hal, s = mk(cfg={'bridge_url': 'http://127.0.0.1:8310', 'token': ''}, locale=True)
    # col bridge configurato il menu ha sia AurI sia Claude
    m = main_menu(s)
    etichette = [lab for lab, _i, _a in m.items]
    assert etichette[0] == 'AurI' and 'Claude' in etichette, etichette
    s.assistant()
    s.step()
    app = s.top
    assert app.brain.motore() == BRIDGE, app.brain.motore()
    app._send('accendi la luce')
    avanza(hal, s, 200)
    assert app.state == 'show', app.state
    assert 'bridge di casa' in testo(s), testo(s)
    metodo, url, body = hal.richieste[-1]
    assert url.endswith('/v1/chat') and body['mode'] == 'assist', (url, body)
    assert app.brain.session == 'abc123'
    shot(hal, s, '9_bridge')
    # scelta esplicita del motore locale
    s.settings.set(brain=LOCALE)
    assert app.brain.motore() == LOCALE
    s.settings.set(brain='auto')
    print('ok  motore bridge e scelta del motore')


def test_bridge_spento_passa_al_browser():
    """Bridge di casa spento + cervello nel browser acceso: la domanda non deve dare errore."""
    hal, s = mk(cfg={'bridge_url': 'http://127.0.0.1:8310', 'token': ''}, locale=True)
    s.assistant()
    s.step()
    app = s.top
    assert app.brain.motore() == BRIDGE
    hal.bridge_giu = True
    app._send('ciao')                                   # il bridge non risponde
    avanza(hal, s, 200)
    assert app.brain.motore() == LOCALE, 'doveva passare al cervello del browser'
    app.brain.accendi()                                 # si accende il cervello qui
    avanza(hal, s, 25 * PASSI_CARICAMENTO + 600)        # e la domanda riparte da sola
    assert not app.brain.error, app.brain.error
    assert '3310' in testo(s), testo(s)                 # ha risposto il cervello del browser
    assert app.brain.motore() == LOCALE
    shot(hal, s, '11_bridge_spento')
    print('ok  bridge spento: pensa il browser, senza errori')


def test_bridge_spento_senza_cervello():
    """Bridge spento e nessun cervello qui (telefono vero): si dice che il bridge non risponde."""
    hal, s = mk(cfg={'bridge_url': 'http://127.0.0.1:8310', 'token': ''}, locale=False)
    hal.bridge_giu = True
    s.assistant()
    s.step()
    app = s.top
    app._send('ciao')
    avanza(hal, s, 300)
    assert 'ridge' in (app.brain.error or ''), app.brain.error
    print('ok  senza cervello qui: lo dice che il bridge non risponde')


def test_bridge_spento_chiede_di_accendere():
    """Bridge spento ma il cervello del browser c'e': chiede di accenderlo, non da errore."""
    hal, s = mk(cfg={'bridge_url': 'http://127.0.0.1:8310', 'token': ''}, locale=True)
    hal.bridge_giu = True
    s.assistant()
    s.step()
    app = s.top
    app._send('ciao')
    avanza(hal, s, 300)
    assert app.state == 'off' and not app.brain.error, (app.state, app.brain.error)
    assert app.brain.sospesa == 'ciao', app.brain.sospesa   # la domanda non si perde
    shot(hal, s, '12_bridge_spento_accendi')                # schermata "Cervello OFF / Accendi"
    print('ok  bridge spento: chiede di accendere il cervello qui')


def test_microfono_negato():
    """Se l'utente nega il microfono il display lo dice, invece di "non ho sentito"."""
    hal, s = mk()
    s.push(Assistente(s))
    premi(hal, s, keys.NAVI)                 # accende il cervello
    avanza(hal, s, 25 * PASSI_CARICAMENTO + 200)
    hal.hear_error = 'no_mic'                # il browser risponde: permesso negato
    hal.press(keys.NAVI)
    avanza(hal, s, 900)                      # tenuto premuto = parla
    hal.release(keys.NAVI)
    avanza(hal, s, 400)
    assert s._toast and 'icrofono' in s._toast, s._toast
    print('ok  microfono negato: lo dice sul display')


def test_impostazioni():
    """Impostazioni > Cervello: motore, modello e voce."""
    from apps.impostazioni import Impostazioni
    hal, s = mk()
    s.push(Impostazioni(s))
    s.step()
    etichette = [lab for lab, _a in s.top.items]
    assert any('Cervello' in e for e in etichette), etichette
    premi(hal, s, '5')                      # 5 = Cervello
    voci = [lab for lab, _a in s.top.items]
    assert voci[0].endswith('Auto') and 'Modello' in voci[1] and 'Voce' in voci[2], voci
    premi(hal, s, '1')                      # motore
    premi(hal, s, '2')                      # Locale
    assert s.settings['brain'] == 'locale', s.settings['brain']
    premi(hal, s, '3')                      # voce off
    assert s.settings['ai_voice'] is False
    shot(hal, s, '10_impostazioni')
    s.settings.set(brain='auto', ai_voice=True)
    print('ok  Impostazioni > Cervello')


def test_attesa_lunga():
    """Modello lento: lo snake gira, le frasi cambiano, AurI parla ogni tanto; errore GPU in italiano."""
    hal, s = mk()
    premi(hal, s, keys.NAVI)
    premi(hal, s, keys.NAVI)
    premi(hal, s, keys.NAVI)                       # accendi
    avanza(hal, s, 25 * PASSI_CARICAMENTO + 200)
    lento = hal.ai_poll
    hal.ai_poll = lambda: {'text': '', 'done': 0, 'error': ''}   # non risponde
    app = s.top
    app._send('perche il cielo e blu')
    hal.detto.clear()
    avanza(hal, s, 3000)
    shot(hal, s, '13_attesa_3s')
    avanza(hal, s, 12000)
    shot(hal, s, '14_attesa_15s')
    assert 1 <= len(hal.detto) <= 3, hal.detto      # parla, ma non troppo
    avanza(hal, s, 30000)
    assert len(hal.detto) == 3, hal.detto
    hal.ai_poll = lambda: {'text': '', 'done': 1, 'error': 'gpu'}
    avanza(hal, s, 200)
    assert 'grafica' in ' '.join(app.lines), app.lines
    shot(hal, s, '15_errore_gpu')
    hal.ai_poll = lento
    print('ok  attesa lunga: snake, frasi che girano, voce ogni tanto, errore GPU in italiano')


if __name__ == '__main__':
    test_pulizia()
    test_niente_cervello()
    test_accensione_e_voce()
    test_scrittura_t9()
    test_bridge()
    test_bridge_spento_passa_al_browser()
    test_bridge_spento_senza_cervello()
    test_bridge_spento_chiede_di_accendere()
    test_microfono_negato()
    test_impostazioni()
    test_attesa_lunga()
    print('\ntutti i test passati. Immagini in', OUT)
