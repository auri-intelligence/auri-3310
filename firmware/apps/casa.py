from auri import keys
from auri.ui import App, Menu, TextView, header, snake_load
from auri.i18n import t
from auri.net import Richiesta


class Attesa(App):
    """Aspetta il bridge senza bloccare il telefono (snake che gira); poi si sostituisce con il risultato.
    fatto(dati, errore) ritorna l'app da mostrare al posto dell'attesa. C annulla."""

    def __init__(self, sys, titolo, metodo, percorso, corpo, fatto):
        super().__init__(sys)
        cfg = sys.config
        self.titolo = titolo
        self.fatto = fatto
        self.req = Richiesta(sys.hal, metodo, cfg['bridge_url'] + percorso, corpo, cfg.get('token'))

    def on_key(self, k):
        if k == keys.C:
            self.req = None
            self.sys.pop()

    def tick(self, now):
        if self.req is None:
            return False
        if self.req.poll():
            r, self.req = self.req, None
            dopo = self.fatto(r.dati if isinstance(r.dati, dict) else None, r.errore)
            self.sys.pop()
            if dopo is not None:
                self.sys.push(dopo)
        return True

    def draw(self, g):
        header(g, self.titolo)
        snake_load(g, self.sys.hal.ticks_ms(), 25, '...')


def Casa(sys):
    def toggle(eid, name):
        def run():
            def esito(r, errore):
                if errore or r is None:
                    return TextView(sys, t('error'), t('bridge_err'))
                return TextView(sys, name[:14], r.get('message', t('done')))
            sys.push(Attesa(sys, name[:13], 'POST', '/v1/home/toggle', {'id': eid}, esito))
        return run

    def elenco(r, errore):
        if errore or r is None:
            return TextView(sys, t('home'), t('bridge_down'))
        items = []
        for ent in r.get('entities', []):
            mark = '*' if ent.get('state') == 'on' else ' '
            items.append((mark + ent['name'], toggle(ent['id'], ent['name'])))
        if not items:
            return TextView(sys, t('home'), t('no_devices'))
        return Menu(sys, t('home'), items)

    return Attesa(sys, t('home'), 'GET', '/v1/home', None, elenco)
