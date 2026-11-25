# Richieste di rete che non bloccano lo schermo.
# Nel simulatore la HAL ha request_start/request_poll (fetch del browser): il telefono continua a
# disegnare mentre aspetta. Dove non c'e' (PC, ESP32 per ora) si fa la richiesta normale al primo poll.


class Richiesta:
    def __init__(self, hal, method, url, body=None, token=None):
        self.hal = hal
        self.args = (method, url, body, token)
        self.fatto = False
        self.dati = None
        self.errore = ''
        self.rid = None
        if hasattr(hal, 'request_start'):
            try:
                self.rid = hal.request_start(method, url, body, token)
            except Exception as e:
                self._fine(None, str(e) or 'rete')

    def _fine(self, dati, errore):
        self.fatto, self.dati, self.errore = True, dati, errore

    def poll(self):
        """True quando ha finito (guardare .dati e .errore)."""
        if self.fatto:
            return True
        if self.rid is not None:
            r = self.hal.request_poll(self.rid)
            if r is not None:
                self._fine(*r)
            return self.fatto
        try:
            self._fine(self.hal.request(*self.args), '')
        except Exception as e:
            self._fine(None, str(e) or 'rete')
        return True
