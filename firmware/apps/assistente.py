from auri import keys
from auri.ui import App
from auri.gfx import W, H, wrap
from auri import i18n
from auri.i18n import t


class Assistente(App):
    """System-wide voice assistant: hold Power (anywhere) or Navi (home), talk, release."""

    def __init__(self, sys, trigger):
        super().__init__(sys)
        self.trigger = trigger
        self.state = 'listen'
        self.lines = []
        self.pos = 0
        self.session = sys.hal.load('assist', {}).get('session')
        if not sys.hal.voice_start():
            self.state = 'show'
            self.lines = wrap(t('no_voice'))
        else:
            sys.hal.vibrate(40)

    def on_up(self, k):
        if self.state == 'listen' and k == self.trigger:
            self.state = 'wait'
            cfg = self.sys.config
            body = {'session': self.session, 'mode': 'assist', 'language': i18n.lang}
            self.sys.hal.voice_stop(cfg['bridge_url'] + '/v1/voice', body, cfg.get('token'))

    def on_key(self, k):
        if self.state != 'show':
            return
        if k == keys.UP:
            self.pos = max(0, self.pos - 1)
        elif k == keys.DOWN:
            self.pos = min(max(0, len(self.lines) - 4), self.pos + 1)
        else:
            self.sys.pop()

    def on_long(self, k):
        pass

    def tick(self, now):
        if self.state == 'listen':
            return (now // 150) % 2 == 0
        if self.state == 'wait':
            r = self.sys.hal.voice_poll()
            if r is None:
                return (now // 300) % 2 == 0
            self.session = r.get('session', self.session)
            self.sys.hal.save('assist', {'session': self.session})
            text = r.get('reply') or ''
            if r.get('error') and not text:
                text = t('bridge_err')
            heard = r.get('transcript')
            self.lines = (wrap('"' + heard + '"') if heard else []) + wrap(text)
            self.state = 'show'
            self.sys.hal.vibrate(60)
            return True
        return False

    def draw(self, g):
        g.logo(0, 0)
        g.text(t('assistant'), 22, 0)
        for x in range(0, W, 2):
            g.pixel(x, 9)
        if self.state == 'listen':
            g.text_center(t('listening'), 14)
            now = self.sys.hal.ticks_ms()
            for i in range(9):
                h = 2 + ((now // 90 + i * 7) % 9)
                g.fill_rect(15 + i * 6, 38 - h // 2, 3, h)
            return
        if self.state == 'wait':
            g.text_center(t('thinking'), 22)
            return
        for i, line in enumerate(self.lines[self.pos:self.pos + 4]):
            g.text(line, 0, 11 + i * 9)
