"""L'assistente AurI: la voce e il cervello del telefono, come "Ok Google" sul 3310.

Si apre tenendo premuto Navi (o Power) da qualsiasi punto, oppure dal menu.
Tieni premuto Navi e parla, rilascia: AurI trascrive, pensa e risponde a voce e sul display.
Premi Navi breve per scrivere la domanda col T9, # per le opzioni.

Il cervello lo scegli in auri/cervello.py: il modello dentro il dispositivo (browser o microSD)
oppure quello del bridge di casa. Qui si disegna soltanto.
"""
from auri import keys
from auri.ui import App, Menu, softkey
from auri.gfx import W, H, wrap
from auri.cervello import Cervello, LOCALE, BRIDGE
from auri.t9 import MultiTap
from auri import i18n
from auri.i18n import t


class Assistente(App):
    title = 'AurI'

    def __init__(self, sys, trigger=None):
        super().__init__(sys)
        self.brain = Cervello(sys)
        self.trigger = trigger
        self.detti = 0             # frasi d attesa gia dette (anche quando la domanda arriva dalla voce)
        self.t_think = sys.hal.ticks_ms()
        self.lines = []
        self.pos = 0
        self.input = MultiTap()
        self.heard = ''
        self.blink = 0
        self._navi = False
        self._last = ''
        self.state = 'idle'
        if self.brain.motore() is None:
            self.state = 'none'
            self.lines = wrap(t('no_brain_web') if sys.config.get('online') else t('no_brain'))
        elif not self.brain.pronto():
            self.state = 'off'
        elif trigger is not None:
            self._listen()

    # --- passaggi di stato ------------------------------------------------
    def _listen(self):
        if not self.brain.ascolta():
            self.state = 'type'
            self.sys.toast(t('no_voice'))
            return
        self.sys.track('assistente/voce')
        self.heard = ''
        self.state = 'listen'
        self.sys.vibrate(40)

    def _send(self, testo):
        testo = (testo or '').strip()
        if not testo:
            self.state = 'idle'
            return
        self.sys.track('assistente/domanda')
        self.heard = testo
        self.lines = []
        self.pos = 0
        self._last = ''
        self.input = MultiTap()
        # un bip corto appena parte la domanda: sul telefono vero (che non ha la voce del browser)
        # e' il modo per far capire subito che AurI ha sentito e sta pensando
        try:
            self.sys.hal.beep(1200, 20, self.sys.settings['volume'])
        except Exception:
            pass
        self.brain.chiedi(testo)
        self._pensa()

    def _pensa(self):
        """Entra in "sto pensando": riparte il conto dei secondi e delle frasi d'attesa (T9, voce o bridge)."""
        if self.state != 'think':
            self.t_think = self.sys.hal.ticks_ms()
            self.detti = 0
        self.state = 'think'

    def _show(self):
        txt = self.brain.text or self.brain.error or t('no_answer')
        self.lines = (wrap('"' + self.heard + '"') if self.heard else []) + wrap(txt)
        self.pos = max(0, len(self.lines) - 3)
        self.state = 'show'

    # --- tasti -------------------------------------------------------------
    def on_key(self, k):
        if self.state == 'none':
            if k in (keys.UP, keys.DOWN):
                self._scroll(k)
            else:
                self.sys.pop()
            return
        if self.state == 'off':
            if k == keys.NAVI:
                self.brain.accendi()
                self.state = 'load'
            elif k == keys.HASH:
                self.sys.push(self.options())
            elif k == keys.C:
                self.sys.pop()
            return
        if self.state == 'load':
            if k == keys.C:
                self.sys.pop()
            return
        if self.state == 'think':
            if k == keys.C:
                self.brain.ferma()
                self._show()
            return
        if self.state == 'type':
            if k == keys.NAVI:
                self._send(self.input.text)
            elif k == keys.C and not self.input.text:
                self.state = 'idle'
            elif k == keys.HASH and not self.input.text:
                self.sys.push(self.options())
            else:
                self.input.key(k, self.sys.hal.ticks_ms())
            return
        if self.state == 'listen':
            return
        # idle / show
        if k == keys.NAVI:
            self._navi = True          # breve scrive, tenuto parla
        elif k in (keys.UP, keys.DOWN):
            self._scroll(k)
        elif k == keys.STAR:
            self.brain.leggi(self.brain.text or '')
        elif k == keys.HASH:
            self.sys.push(self.options())
        elif k == keys.C:
            self.brain.taci()
            self.sys.pop()

    def _scroll(self, k):
        if k == keys.UP:
            self.pos = max(0, self.pos - 1)
        else:
            self.pos = min(max(0, len(self.lines) - 3), self.pos + 1)

    def on_long(self, k):
        if self.state in ('idle', 'show', 'type') and k in (keys.NAVI, keys.POWER):
            self._navi = False
            if not self.input.text:
                self._listen()
        elif self.state == 'type':
            self.input.long(k)

    def on_up(self, k):
        if self.state == 'listen' and (k == self.trigger or k in (keys.NAVI, keys.POWER)):
            self.brain.basta_ascolto()
            r = self.brain.ascolto_poll()
            if r is None:
                self._pensa()       # la voce passa dal bridge: aspetta la risposta
            else:
                self.state = 'hear'        # riconoscimento nel browser: aspetta il testo
        elif k == keys.NAVI and self._navi:
            self._navi = False
            self.state = 'type'

    # --- giro di orologio ---------------------------------------------------
    def tick(self, now):
        if self.brain.sospesa:
            # domanda rimasta in sospeso perche' il bridge di casa non risponde: si segue il
            # cervello del browser finche' non e' pronto, poi la domanda riparte da sola
            fase = self.brain.info().get('phase')
            if self.brain.pronto():
                self._pensa()
            elif fase == 'load':
                self.state = 'load'
            elif self.state not in ('off', 'load'):
                self.state = 'off'
        if self.state == 'load':
            info = self.brain.info()
            if info.get('phase') == 'ready':
                # se c'era una domanda in sospeso riparte da sola, senza riscriverla
                if self.brain.sospesa:
                    self._pensa()
                else:
                    self.state = 'idle'
                self._last = None
                self.sys.vibrate(60)
                return True
            if info.get('phase') == 'err':
                self.state = 'none'
                err = info.get('error') or ''
                noti = ('no_webgpu', 'no_https')      # cause che sappiamo spiegare in poche parole
                self.lines = wrap(t(err) if err in noti else t('error') + ': ' + err)
                return True
            return True
        if self.state == 'listen':
            r = self.brain.ascolto_poll()
            if r is not None and r[0] != self.heard:
                self.heard = r[0]
                return True
            return (now // 150) % 2 == 0
        if self.state == 'hear':
            r = self.brain.ascolto_poll()
            if r is None:
                self._pensa()
                return True
            testo, finito = r
            if testo != self.heard:
                self.heard = testo
            if finito:
                if testo:
                    self._send(testo)
                else:
                    self.state = 'idle'
                    err = getattr(self.brain, 'hear_error', '')
                    self.sys.toast(t('no_mic') if err == 'no_mic' else t('not_heard'))
                return True
            return (now // 300) % 2 == 0
        if self.state == 'think':
            # il bridge di casa non ha risposto e il cervello del browser e' spento: si chiede
            # di accenderlo, la domanda resta in sospeso e parte da sola appena e' pronto
            if self.brain.in_attesa_di_cervello():
                self.state = 'off'
                return True
            nuovo = self.brain.poll()
            if not self.brain.text and not self.brain.done:
                # attesa lunga: una frase a voce dopo 5 s, poi ogni 8 s (massimo 3)
                el = now - getattr(self, 't_think', now)
                if self.detti < 3 and el > 5000 + self.detti * 8000:
                    from auri.cervello import attesa
                    self.brain.leggi(attesa(self.detti * 3 + 1)[1])
                    self.detti += 1
                return True       # lo snake gira: si ridisegna sempre
            if self.brain.text != self._last:
                self._last = self.brain.text
                self.lines = wrap(self.brain.text)
                self.pos = max(0, len(self.lines) - 3)
            if self.brain.done:
                if self.brain.da_leggere():
                    self.brain.leggi(self.brain.text)
                self._show()
                self.sys.vibrate(60)
                return True
            return nuovo or (now // 300) % 2 == 0
        b = (now // 500) % 2
        if b != self.blink:
            self.blink = b
            return self.state == 'type'
        return False

    # --- opzioni -------------------------------------------------------------
    def options(self):
        sys = self.sys
        st = sys.settings

        def modelli():
            try:
                lista = sys.hal.ai_models()
            except Exception:
                lista = []
            if not lista:
                sys.toast(t('no_brain'))
                return

            def pick(key):
                def run():
                    st.set(ai_model=key)
                    sys.pop()
                    sys.pop()
                    self.brain.accendi(key)
                    self.state = 'load'
                return run
            cur = st['ai_model']
            voci = [(('>' if cur == 'auto' else ' ') + t('ai_auto'), pick('auto'))]
            voci += [(('>' if k == cur else ' ') + '%s %dMB' % (name, mb), pick(k)) for k, name, mb in lista]
            sys.push(Menu(sys, t('ai_model'), voci))

        def motore():
            def pick(v):
                def run():
                    st.set(brain=v)
                    sys.pop()
                    sys.pop()
                    self.state = 'idle' if self.brain.pronto() else 'off'
                return run
            cur = st['brain']
            voci = (('auto', t('ai_auto')), (LOCALE, t('ai_local')), (BRIDGE, t('ai_bridge')))
            sys.push(Menu(sys, t('ai_engine'), [(('>' if v == cur else ' ') + lab, pick(v)) for v, lab in voci]))

        def voce():
            st.set(ai_voice=not st['ai_voice'])
            sys.pop()

        def nuova():
            self.brain.storia = []
            self.brain.session = None
            self.brain.text = ''
            self.heard = ''
            self.lines = []
            self.state = 'idle' if self.brain.pronto() else 'off'
            sys.pop()

        voci = [
            (t('ai_engine') + ': ' + self._engine_label(), motore),
            (t('ai_voice') + ' ' + (t('on') if st['ai_voice'] else t('off')), voce),
            (t('new_session'), nuova),
        ]
        if self.brain.motore() == LOCALE:
            info = self.brain.info()
            voci.insert(0, (t('ai_model') + ': ' + str(info.get('name', '?')), modelli))
        return Menu(sys, t('options'), voci)

    def _engine_label(self):
        m = self.brain.motore()
        return t('ai_local') if m == LOCALE else t('ai_bridge') if m == BRIDGE else '-'

    # --- disegno ---------------------------------------------------------------
    def _head(self, g):
        g.logo(0, 0)
        tag = 'loc' if self.brain.motore() == LOCALE else 'casa' if self.brain.motore() == BRIDGE else '--'
        g.text(tag, W - len(tag) * 6, 0)
        for x in range(0, W, 2):
            g.pixel(x, 9)

    def _body(self, g, lines, pos):
        for i, line in enumerate(lines[pos:pos + 3]):
            g.text(line, 0, 11 + i * 9)
        if len(lines) > 3:
            h = max(4, 27 * 3 // len(lines))
            g.vline(W - 1, 11 + (27 - h) * pos // max(1, len(lines) - 3), h)

    def draw(self, g):
        self._head(g)
        if self.state in ('none',):
            self._body(g, self.lines, self.pos)
            softkey(g, t('back'))
            return
        if self.state == 'off':
            info = self.brain.info()
            g.text_center(t('brain_off'), 12)
            g.text_center(str(info.get('name', '?'))[:14], 22)
            g.text_center('%d MB' % info.get('mb', 0), 31)
            softkey(g, t('turn_on'))
            return
        if self.state == 'load':
            info = self.brain.info()
            pct = int(info.get('pct', 0))
            g.text_center(t('brain_load'), 11)
            g.rect(8, 21, W - 16, 9)
            g.fill_rect(10, 23, (W - 20) * pct // 100, 5)
            g.text_center('%d%%' % pct, 32)
            softkey(g, str(info.get('name', ''))[:10])
            return
        if self.state == 'listen':
            g.text_center(t('listening'), 11)
            if self.heard:
                for i, line in enumerate(wrap(self.heard)[-2:]):
                    g.text(line, 0, 20 + i * 9)
            else:
                now = self.sys.hal.ticks_ms()
                for i in range(9):
                    h = 2 + ((now // 90 + i * 7) % 9)
                    g.fill_rect(15 + i * 6, 32 - h // 2, 3, h)
            softkey(g, t('release_send'))
            return
        if self.state == 'hear':
            g.text_center(t('listening'), 11)
            for i, line in enumerate(wrap(self.heard)[-2:]):
                g.text(line, 0, 22 + i * 9)
            return
        if self.state == 'think':
            if self.lines:
                self._body(g, self.lines, self.pos)
                if self.blink:
                    g.fill_rect(W - 4, 11 + min(2, len(self.lines) - 1 - self.pos) * 9 + 6, 3, 2)
            else:
                from auri.cervello import attesa
                from auri.ui import snake_load
                now = self.sys.hal.ticks_ms()
                el = now - getattr(self, 't_think', now)
                snake_load(g, now, 21)
                g.fill_rect(0, 30, W, 9, 0)
                g.text_center(t('thinking') if el < 2500 else attesa(el // 2500 - 1)[0], 31)
                if el > 3000:
                    g.text(str(el // 1000) + 's', 0, 11)
            softkey(g, 'C = ' + t('stop'))
            return
        if self.state == 'type':
            inp = self.input.text
            righe = wrap(inp)[-3:] if inp else []
            for i, line in enumerate(righe):
                g.text(line, 0, 12 + i * 9)
            if self.blink:
                w = len(righe[-1]) * 6 if righe else 0
                g.fill_rect(min(W - 3, w), 12 + max(0, len(righe) - 1) * 9, 2, 7)
            if not inp:
                g.text_center(t('write'), 22)
            softkey(g, t('send') if inp else t('back'))
            return
        # idle / show
        if self.lines:
            self._body(g, self.lines, self.pos)
            softkey(g, t('ask'))
        else:
            g.text_center(t('hold_navi'), 14)
            g.text_center(t('navi_write'), 24)
            g.text_center('# ' + t('options').lower(), 34)
