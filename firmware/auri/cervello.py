"""Il cervello di AurI: lo stesso assistente, tre motori diversi.

- 'locale'  il modello gira sul dispositivo: nel browser con WebGPU (simulatore), sul telefono vero
            dalla microSD. Nessun server, nessuna chiave, nessun costo.
- 'bridge'  il modello gira sul PC o sul Raspberry di casa (llama.cpp o altro) e il telefono chiede
            via Wi-Fi: risposte piu' intelligenti, ma solo in rete di casa.
- nessuno   qui non c'e' cervello, e l'assistente lo dice invece di fingere.

L'app (apps/assistente.py) non sa quale motore sta usando: chiede, aspetta, mostra.
"""
from auri import i18n
from auri.gfx import FOLD

LOCALE = 'locale'
BRIDGE = 'bridge'

# Quanti messaggi di storia tenere (domanda + risposta = 2): il contesto di un modello piccolo e' corto.
STORIA = 6
# Un display da 14 colonne per 3 righe: risposte di una o due frasi.
MAX_TOKEN = 90       # due frasi brevi: risposte piu rapide e meno occasioni di perdersi

PERSONA = {
    'it': ("Ti chiami AurI. Sei l'assistente che vive dentro un vecchio telefono con lo schermo piccolo. "
           "Non hai altri nomi e non sei l'assistente di nessuna marca. Rispondi sempre in italiano con una "
           "o due frasi brevi, pronte da leggere ad alta voce. Solo testo semplice: niente elenchi, niente "
           "markdown, niente emoji. Se non sai una cosa, dillo in poche parole."),
    'en': ("Your name is AurI. You are the assistant living inside an old phone with a tiny screen. You have "
           "no other name and you are not any brand's assistant. Always answer in English with one or two "
           "short sentences, ready to be read aloud. Plain text only: no lists, no markdown, no emoji. "
           "If you don't know something, say so in a few words."),
    'es': ("Te llamas AurI. Eres el asistente que vive dentro de un telefono viejo de pantalla pequena. No "
           "tienes otro nombre. Responde siempre en espanol con una o "
           "dos frases cortas, listas para leer en voz alta. Solo texto simple: sin listas, sin markdown, sin "
           "emojis. Si no sabes algo, dilo en pocas palabras."),
    'fr': ("Tu t'appelles AurI. Tu es l'assistant qui vit dans un vieux telephone a petit ecran. Tu n'as pas "
           "d'autre nom. Reponds toujours en francais avec une ou deux "
           "phrases courtes, pretes a etre lues a voix haute. Texte simple seulement: pas de listes, pas de "
           "markdown, pas d'emoji. Si tu ne sais pas, dis-le en quelques mots."),
    'de': ("Du heisst AurI. Du bist der Assistent in einem alten Telefon mit kleinem Display. Du hast keinen "
           "anderen Namen. Antworte immer auf Deutsch mit einem oder zwei "
           "kurzen Saetzen, zum Vorlesen geeignet. Nur einfacher Text: keine Listen, kein Markdown, keine "
           "Emojis. Wenn du etwas nicht weisst, sag es kurz."),
    'pt': ("Chamas-te AurI. Es o assistente que vive dentro de um telefone antigo com um ecra pequeno. Nao "
           "tens outro nome. Responde sempre em portugues com "
           "uma ou duas frases curtas, prontas a ler em voz alta. Apenas texto simples: sem listas, sem "
           "markdown, sem emojis. Se nao sabes, di-lo em poucas palavras."),
}


# Un botta e risposta di esempio prima della domanda vera: con i modelli piccoli (0,5 miliardi di
# parametri) e' la differenza fra "sono AurI" e un modello che si inventa il nome di un altro assistente.
ESEMPIO = {
    # piu' esempi in italiano: nel banco di prova il Base 0.5B con il solo "Chi sei?" rispondeva vago
    'it': (('Chi sei?', "Sono AurI, l'assistente di questo telefono. Dimmi pure."),
           ('Cosa sai fare?', "Rispondo alle tue domande, ti spiego le cose e ti tengo compagnia. Prova a chiedermi qualcosa."),
           ('Quanto fa 7 per 8?', 'Fa 56.')),
    'en': ('Who are you?', "I'm AurI, the assistant in this phone. Go ahead, ask me."),
    'es': ('Quien eres?', 'Soy AurI, el asistente de este telefono. Dime.'),
    'fr': ('Qui es-tu?', "Je suis AurI, l'assistant de ce telephone. Vas-y, demande."),
    'de': ('Wer bist du?', 'Ich bin AurI, der Assistent dieses Telefons. Frag nur.'),
    'pt': ('Quem es tu?', 'Sou o AurI, o assistente deste telefone. Pergunta a vontade.'),
}


# Mentre il modello pensa, AurI dice subito una parola: l'attesa muta sembra un telefono rotto.
# E' il trucco che usano gli assistenti vocali, e qui serve davvero perche' il modello e' lento.
RIEMPITIVO = {
    'it': 'Vediamo...',
    'en': 'Let me see...',
    'es': 'Veamos...',
    'fr': 'Voyons...',
    'de': 'Mal sehen...',
    'pt': 'Vejamos...',
}


def riempitivo():
    return RIEMPITIVO.get(i18n.lang, RIEMPITIVO['it'])


# Se il modello ci mette tanto, AurI tiene compagnia: frasi che girano sul display (corte, 14 colonne)
# e ogni tanto una detta a voce. Prima c'era solo "Sto pensando" con un puntino: sembrava bloccato.
ATTESA = {
    'it': (('Ci penso...', 'Ci sto pensando, un attimo.'),
           ('Cerco parole', 'Sto cercando le parole giuste.'),
           ('Quasi...', 'Ci sono quasi.'),
           ('Tutto qui!', 'Ho un cervello tutto mio, gira qui dentro.'),
           ('Niente server', 'Nessun server: penso solo con questo telefono.'),
           ('Del 2000!', 'Non male per un telefono del duemila.'),
           ('Metto ordine', 'Metto in ordine i pensieri.'),
           ('Ancora poco', 'Ancora un momento.')),
    'en': (('Thinking...', 'Thinking, one moment.'),
           ('Finding words', 'Looking for the right words.'),
           ('Almost...', 'Almost there.'),
           ('All in here!', 'My brain runs right here, inside this phone.'),
           ('No servers', 'No servers: I think with this phone only.'),
           ('From 2000!', 'Not bad for a phone from the year two thousand.'),
           ('Nearly done', 'Just a moment more.')),
}


def attesa(i):
    """(testo per il display, frase da dire) numero i, a giro."""
    lista = ATTESA.get(i18n.lang, ATTESA['en' if i18n.lang != 'it' else 'it'])
    return lista[i % len(lista)]


# Gli errori del cervello del browser arrivano come codice: qui diventano parole che si capiscono.
ERRORI = {'gpu': 'ai_err_gpu', 'rete': 'ai_err_net', 'altro': 'ai_err_other'}


def persona():
    return PERSONA.get(i18n.lang, PERSONA['it'])


def esempio():
    """Coppie (domanda, risposta) di esempio per la lingua attuale."""
    e = ESEMPIO.get(i18n.lang, ESEMPIO['it'])
    return e if isinstance(e[0], tuple) else (e,)


def pulisci(txt):
    """Dal modello al display: via i ragionamenti, il markdown e i caratteri che il font non sa disegnare."""
    if not txt:
        return ''
    if '</think>' in txt:
        txt = txt.split('</think>')[-1]
    elif txt.lstrip()[:7] == '<think>':
        return ''          # sta ancora ragionando: non c'e' niente da mostrare
    out = []
    for ch in txt:
        if ch in '*_`#>|':
            continue
        if ch in '\r\n\t':
            ch = ' '
        if ord(ch) > 126 and ch not in FOLD:
            continue
        if ch == ' ' and (not out or out[-1] == ' '):
            continue
        out.append(ch)
    return ''.join(out).strip()


class Cervello:
    """Un giro di domanda e risposta, senza bloccare il telefono."""

    def __init__(self, sys):
        self._bridge_giu = False   # True quando il bridge di casa non risponde
        self.sospesa = None        # domanda in attesa che si accenda il cervello qui
        self.sys = sys
        self.hal = sys.hal
        self.storia = []
        self.session = self.hal.load('assist', {}).get('session')
        self.text = ''
        self.heard = ''
        self.done = True
        self.error = ''
        self._pending = None     # domanda in attesa di partire (motore bridge)

    # --- motori disponibili ---------------------------------------------
    def locale_ok(self):
        f = getattr(self.hal, 'ai_ok', None)
        return bool(f and f())

    def bridge_ok(self):
        return bool(self.sys.config.get('bridge_url'))

    def motore(self):
        pref = self.sys.settings['brain']
        # Il bridge non ha risposto e la scelta era "auto": da qui in poi si pensa nel browser,
        # invece di ripetere un errore a ogni domanda.
        if pref == 'auto' and self._bridge_giu and self.locale_ok():
            return LOCALE
        ordine = (LOCALE, BRIDGE) if pref == LOCALE else (BRIDGE, LOCALE)
        for m in ordine:
            if (m == LOCALE and self.locale_ok()) or (m == BRIDGE and self.bridge_ok()):
                return m
        return None

    # --- stato del modello locale ---------------------------------------
    def info(self):
        """Per il motore locale: {'phase': off|load|ready|gen|err, 'pct', 'name', 'mb', ...}."""
        if self.motore() != LOCALE:
            return {'phase': 'ready' if self.motore() else 'err', 'pct': 100, 'name': BRIDGE, 'mb': 0}
        try:
            return self.hal.ai_info()
        except Exception as e:
            return {'phase': 'err', 'pct': 0, 'name': '?', 'mb': 0, 'error': str(e)}

    def pronto(self):
        return self.info().get('phase') in ('ready', 'gen')

    def accendi(self, model=''):
        """Scarica e accende il modello locale (la prima volta sono alcune centinaia di MB).

        Si puo' accendere anche quando sta rispondendo il bridge: resta li' pronto per quando il
        bridge di casa non c'e'.
        """
        if self.locale_ok():
            # 'auto': sceglie il browser, che sa che scheda grafica c'e' e se e' un telefono
            self.hal.ai_start(model or self.sys.settings['ai_model'] or '')

    # --- ascolto ---------------------------------------------------------
    def ascolto_locale(self):
        return bool(getattr(self.hal, 'hear_start', None)) and self.motore() == LOCALE

    def ascolta(self):
        """Inizia ad ascoltare. True se il microfono e' partito."""
        self.heard = ''
        if self.ascolto_locale():
            return bool(self.hal.hear_start(i18n.lang))
        return bool(self.hal.voice_start())

    def basta_ascolto(self):
        """Fine della pressione: manda quello che ha sentito."""
        if self.ascolto_locale():
            self.hal.hear_stop()
            return
        cfg = self.sys.config
        body = {'session': self.session, 'mode': 'assist', 'language': i18n.lang}
        self.text = ''
        self.done = False
        self.error = ''
        self.hal.voice_stop(cfg['bridge_url'] + '/v1/voice', body, cfg.get('token'))

    def ascolto_poll(self):
        """Per il motore locale: (testo, finito) di quello che si sta sentendo, oppure None."""
        if not self.ascolto_locale():
            return None
        try:
            r = self.hal.hear_poll()
        except Exception:
            return ('', True)
        # 'no_mic' = permesso negato: il display lo dice invece di un generico "non ho sentito"
        self.hear_error = r.get('error') or ''
        return (r.get('text') or '', bool(r.get('done')))

    # --- domanda e risposta ----------------------------------------------
    def chiedi(self, testo):
        testo = (testo or '').strip()
        if not testo:
            return
        self.storia.append(('u', testo))
        self.text = ''
        self.done = False
        self.error = ''
        self.letto = False
        self.leggi(riempitivo())   # una parola subito, poi arriva la risposta
        if self.motore() == LOCALE:
            self._manda_locale()
        else:
            self._pending = testo

    def _manda_locale(self):
        """Manda al cervello del browser la conversazione fin qui."""
        msgs = [{'role': 'system', 'content': persona()}]
        for dom, ris in esempio():
            msgs += [{'role': 'user', 'content': dom}, {'role': 'assistant', 'content': ris}]
        for who, txt in self.storia[-STORIA:]:
            msgs.append({'role': 'user' if who == 'u' else 'assistant', 'content': txt})
        # 'speak' accende la lettura frase per frase nel browser: AurI comincia a parlare
        # appena ha finito la prima frase, non quando ha finito tutta la risposta.
        voce = bool(self.sys.settings['ai_voice'])
        err = self.hal.ai_ask(msgs, {'max_tokens': MAX_TOKEN, 'speak': voce, 'lang': i18n.lang})
        self.letto = voce          # la legge gia' il browser: l'app non deve rileggerla
        if err:
            self.error = err
            self.done = True

    def in_attesa_di_cervello(self):
        """C'e' una domanda in sospeso e il cervello del browser e' ancora da accendere."""
        return bool(self.sospesa) and not self.pronto()

    def poll(self):
        """Da chiamare a ogni giro: True se c'e' qualcosa di nuovo da disegnare."""
        if self.sospesa and self.motore() == LOCALE and self.pronto():
            self.sospesa = None
            self.done = False
            self._manda_locale()
            return True
        if self.sospesa:
            return False          # si aspetta che qualcuno accenda il cervello
        if self.done and self._pending is None:
            return False
        if self.motore() == LOCALE:
            return self._poll_locale()
        return self._poll_bridge()

    def _poll_locale(self):
        try:
            r = self.hal.ai_poll()
        except Exception as e:
            self.error = str(e)
            self.done = True
            return True
        testo = pulisci(r.get('text') or '')
        nuovo = testo != self.text or bool(r.get('done')) != self.done
        self.text = testo
        if r.get('error'):
            from auri.i18n import t
            e = r['error']
            self.error = t(ERRORI[e]) if e in ERRORI else e
        if r.get('done'):
            self._chiudi()
        return nuovo

    def _poll_bridge(self):
        if self._pending is not None:
            # la domanda parte in background: lo schermo (snake, frasi) e i tasti restano vivi
            from auri.net import Richiesta
            testo, self._pending = self._pending, None
            cfg = self.sys.config
            body = {'text': testo, 'session': self.session, 'mode': 'assist', 'language': i18n.lang}
            self._req_testo = testo
            self._req = Richiesta(self.hal, 'POST', cfg['bridge_url'] + '/v1/chat', body, cfg.get('token'))
            return True
        if getattr(self, '_req', None) is not None:
            if not self._req.poll():
                return False
            req, self._req = self._req, None
            testo = self._req_testo
            r = req.dati if not req.errore and isinstance(req.dati, dict) else None
            if r is None or r.get('error') == 'no_llm':
                from auri.i18n import t
                # Il bridge di casa e' spento: se qui c'e' un cervello si continua con quello,
                # cosi' chi apre il simulatore non sbatte contro un errore che non lo riguarda.
                if self.sys.settings['brain'] == 'auto' and self.locale_ok():
                    self._bridge_giu = True          # da adesso si pensa nel browser
                    if self.pronto():
                        self._manda_locale()         # la stessa domanda, pensata qui
                    else:
                        # il cervello c'e' ma e' spento: l'app mostra "Accendi" e la domanda
                        # resta in tasca, parte da sola appena il modello e' pronto
                        self.sospesa = testo
                    return True
                if r is not None:
                    self.error = pulisci(r.get('reply') or '') or t('bridge_err')
                else:
                    self.error = t('bridge_down')
                self.done = True
                return True
            self.session = r.get('session', self.session)
            self.text = pulisci(r.get('reply') or '')
            if r.get('error') and not self.text:
                from auri.i18n import t
                self.error = t('bridge_err')
            self._chiudi()
            return True
        # la voce passa dal bridge: la risposta (e l'audio) arrivano dal suo poll
        r = self.hal.voice_poll()
        if r is None:
            return False
        self.session = r.get('session', self.session)
        self.heard = r.get('transcript') or self.heard
        self.text = pulisci(r.get('reply') or '')
        if r.get('error') and not self.text:
            from auri.i18n import t
            self.error = t('bridge_err')
        self._chiudi()
        return True

    def _chiudi(self):
        self.done = True
        if self.text:
            self.storia.append(('a', self.text))
            del self.storia[:-STORIA]
        if self.session:
            self.hal.save('assist', {'session': self.session})

    def ferma(self):
        self.done = True
        self._req = None          # una risposta del bridge che arriva dopo lo stop si butta
        f = getattr(self.hal, 'ai_stop', None)
        if f and self.motore() == LOCALE:
            f()
        self.taci()

    # --- voce in uscita ---------------------------------------------------
    def leggi(self, testo):
        f = getattr(self.hal, 'speak', None)
        if f and testo and self.sys.settings['ai_voice']:
            f(testo, i18n.lang)

    def da_leggere(self):
        """True se la risposta non e' ancora stata letta (nel browser la legge gia' lui, a pezzi)."""
        return not getattr(self, 'letto', False)

    def taci(self):
        f = getattr(self.hal, 'speak_stop', None)
        if f:
            f()
