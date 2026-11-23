from auri import keys
from auri.ui import App, TextView, Confirm, header, softkey
from auri.t9 import MultiTap
from auri.gfx import wrap


class Claude(App):
    title = 'Claude'

    def __init__(self, sys):
        super().__init__(sys)
        self.input = MultiTap()
        self.state = 'edit'
        self.session = None
        self._blink = 0

    def on_key(self, k):
        if self.state != 'edit':
            return
        now = self.sys.hal.ticks_ms()
        if k == keys.NAVI:
            if self.input.text.strip():
                self.state = 'send'
            return
        if k == keys.C and not self.input.text:
            self.sys.pop()
            return
        self.input.key(k, now)

    def on_long(self, k):
        if k == keys.C and not self.input.text:
            self.sys.home()
        else:
            self.input.long(k)

    def tick(self, now):
        if self.state == 'send':
            self.state = 'wait'
            return True
        if self.state == 'wait':
            self._ask({'text': self.input.text, 'session': self.session}, '/v1/chat')
            return True
        b = (now // 500) % 2
        if b != self._blink:
            self._blink = b
            return True
        return False

    def _ask(self, body, path):
        cfg = self.sys.config
        try:
            r = self.sys.hal.request('POST', cfg['bridge_url'] + path, body, cfg.get('token'))
        except Exception as e:
            self.state = 'edit'
            self.sys.push(TextView(self.sys, 'Errore', 'Bridge non raggiungibile.\n' + str(e)[:60]))
            return
        self.session = r.get('session', self.session)
        self.input = MultiTap()
        self.state = 'edit'
        self.sys.hal.vibrate(80)
        self.sys.push(TextView(self.sys, 'Claude', r.get('reply', '')))
        c = r.get('confirm')
        if c:
            def done(ok, cid=c.get('id')):
                self.state = 'wait_confirm'
                self._ask({'id': cid, 'ok': ok, 'session': self.session}, '/v1/confirm')
            self.sys.push(Confirm(self.sys, c.get('text', 'Procedo?'), done))

    def draw(self, g):
        header(g, 'Claude')
        if self.state in ('send', 'wait'):
            g.text_center('Sto pensando', 18)
            g.text_center('...', 28)
            return
        lines = wrap(self.input.text + ('_' if self._blink else ' '))
        for i, line in enumerate(lines[-3:]):
            g.text(line, 0, 10 + i * 10)
        if not self.input.text:
            g.text('Scrivi...', 0, 20)
        g.text('Abc' if self.input.upper else 'abc', 0, 40)
        softkey(g, 'Invia' if self.input.text.strip() else '')
