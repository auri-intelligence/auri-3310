from auri import keys
from auri.ui import App, Menu, TextView, Confirm, header
from auri.t9 import MultiTap
from auri.gfx import W, H, wrap
from auri import i18n
from auri.i18n import t

# AurI's own mascot: a tiny antenna robot.
MASCOT = (
    '.....#.....',
    '..#######..',
    '.#.......#.',
    '.#.##.##.#.',
    '.#.......#.',
    '..#######..',
    '.#.#...#.#.',
)
MODELS = (('Opus 5.5', 'claude-opus-5-5'), ('Sonnet 5.5', 'claude-sonnet-5-5'),
          ('Haiku 5.5', 'claude-haiku-5-5'), ('Fable 5.2', 'claude-fable-5-2'))
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')
PERMS = (('perm_ask', 'default'), ('perm_edits', 'acceptEdits'), ('perm_plan', 'plan'))
DOT = '·'


class Claude(App):
    title = 'Claude'

    def __init__(self, sys):
        super().__init__(sys)
        st = sys.hal.load('claude', {})
        self.model = st.get('model', 0)
        self.effort = st.get('effort', 'low')
        self.perm = st.get('perm', 0)
        self.remote = st.get('remote', False)
        self.session = st.get('session')
        self.info = {'version': '-', 'plan': 'Claude', 'cwd': '~'}
        self.log = []
        self.input = MultiTap()
        self.state = 'splash'
        self.scroll = 0
        self._blink = 0
        self._navi = False
        try:
            cfg = sys.config
            self.info.update(sys.hal.request('GET', cfg['bridge_url'] + '/v1/info', None, cfg.get('token')))
        except Exception:
            self.info['plan'] = t('offline')

    def _save(self):
        self.sys.hal.save('claude', {'model': self.model, 'effort': self.effort, 'perm': self.perm,
                                     'remote': self.remote, 'session': self.session})

    def on_key(self, k):
        if self.state == 'splash':
            self.state = 'chat'
            if k not in (keys.NAVI, keys.C):
                self.on_key(k)
            return
        if self.state != 'chat':
            return
        now = self.sys.hal.ticks_ms()
        if k == keys.NAVI:
            if self.input.text.strip():
                self.state = 'send'
            else:
                # Short press opens the options on release; holding it talks.
                self._navi = True
        elif k == keys.C and not self.input.text:
            self.sys.pop()
        elif k == keys.UP:
            self.scroll += 1
        elif k == keys.DOWN:
            self.scroll = max(0, self.scroll - 1)
        else:
            self.input.key(k, now)
            self.scroll = 0

    def on_long(self, k):
        if k == keys.NAVI and self.state == 'chat' and not self.input.text:
            # Voice belongs to the system-wide assistant, not to the console.
            self._navi = False
            self.sys.assistant(keys.NAVI)
        elif k == keys.C and not self.input.text:
            self.sys.home()
        else:
            self.input.long(k)

    def on_up(self, k):
        if k == keys.NAVI and self.state == 'listen':
            self.state = 'voice'
            self.sys.hal.voice_stop(self.sys.config['bridge_url'] + '/v1/voice', self._params(), self.sys.config.get('token'))
        elif k == keys.NAVI and self._navi:
            self._navi = False
            self.sys.push(self.options())

    def _params(self):
        return {'session': self.session, 'model': MODELS[self.model][1], 'effort': self.effort,
                'permission_mode': PERMS[self.perm][1], 'remote': self.remote, 'language': i18n.lang}

    def tick(self, now):
        if self.state == 'voice':
            r = self.sys.hal.voice_poll()
            if r is None:
                return False
            if r.get('transcript'):
                self.log.append(('>', r['transcript']))
            self._handle(r)
            return True
        if self.state == 'send':
            self.state = 'wait'
            self.log.append(('>', self.input.text))
            return True
        if self.state == 'wait':
            text = self.input.text
            self.input = MultiTap()
            self._ask('/v1/chat', {'text': text})
            return True
        b = (now // 500) % 2
        if b != self._blink:
            self._blink = b
            return self.state == 'chat'
        return False

    def _ask(self, path, body):
        cfg = self.sys.config
        body.update(self._params())
        try:
            r = self.sys.hal.request('POST', cfg['bridge_url'] + path, body, cfg.get('token'))
        except Exception as e:
            self.state = 'chat'
            self.log.append(('!', t('bridge_down')))
            return
        self._handle(r)

    def _handle(self, r):
        if r.get('error'):
            self.log.append(('!', t('bridge_err')))
        self.session = r.get('session', self.session)
        self._save()
        self.state = 'chat'
        if r.get('reply'):
            self.log.append(('*', r['reply']))
        self.sys.hal.vibrate(80)
        c = r.get('confirm')
        if c:
            def done(ok, cid=c.get('id')):
                self._ask('/v1/confirm', {'id': cid, 'ok': ok})
            self.sys.push(Confirm(self.sys, c.get('text', t('proceed_q')), done))

    def options(self):
        sys = self.sys

        def pick(title, items, cur, setter):
            def run():
                def chooser(i):
                    return lambda: (setter(i), self._save(), sys.pop(), sys.pop())
                m = Menu(sys, title, [(('>' if i == cur() else ' ') + label, chooser(i)) for i, label in enumerate(items)])
                m.sel = cur()
                sys.push(m)
            return run

        def set_model(i):
            self.model = i

        def set_effort(i):
            self.effort = EFFORTS[i]

        def set_perm(i):
            self.perm = i

        def toggle_remote():
            self.remote = not self.remote
            self._save()
            sys.pop()

        def new_session():
            self.session = None
            self.log = []
            self._save()
            sys.pop()

        def show_info():
            sys.push(TextView(sys, t('status'), 'Claude Code %s\n%s %s %s\n%s\n%s: %s\nRemote: %s' % (
                self.info['version'], MODELS[self.model][0], DOT, self.effort, self.info['plan'],
                t('session'), (self.session or t('new'))[:8], 'on' if self.remote else 'off')))

        return Menu(sys, t('options'), [
            (t('model'), pick(t('model'), [m[0] for m in MODELS], lambda: self.model, set_model)),
            (t('effort'), pick(t('effort'), EFFORTS, lambda: EFFORTS.index(self.effort), set_effort)),
            (t('perms'), pick(t('perms'), [t(p[0]) for p in PERMS], lambda: self.perm, set_perm)),
            ('Remote ' + ('on' if self.remote else 'off'), toggle_remote),
            (t('new_session'), new_session),
            (t('status'), show_info),
        ])

    def draw(self, g):
        if self.state == 'splash':
            g.icon(MASCOT, 0, 1)
            g.text('Claude Code', 14, 0)
            g.text('v' + str(self.info['version']), 14, 8)
            g.text(MODELS[self.model][0] + ' with', 0, 18)
            g.text(self.effort + ' effort', 0, 26)
            g.text(DOT + ' ' + str(self.info['plan']), 0, 34)
            cwd = str(self.info['cwd'])
            tail = (' ' + DOT + ' /rc') if self.remote else ''
            g.text(cwd[-(14 - len(tail)):] + tail, 0, 41)
            return
        g.icon(MASCOT, 0, 0)
        g.text('%s %s' % (MODELS[self.model][0].split()[0], self.effort[:3]), 14, 0)
        for x in range(0, W, 2):
            g.pixel(x, 8)
        lines = []
        for who, text in self.log:
            for i, l in enumerate(wrap(text, 12)):
                lines.append(((who if i == 0 else ' ') + ' ' + l))
        if self.state in ('wait', 'voice'):
            lines.append('* ...')
        elif self.state == 'listen':
            lines.append('* ' + t('listening'))
        body = 3
        end = max(0, len(lines) - self.scroll)
        for i, l in enumerate(lines[max(0, end - body):end]):
            g.text(l, 0, 10 + i * 9)
        for x in range(0, W, 2):
            g.pixel(x, H - 10)
        inp = self.input.text
        shown = ('> ' + inp)[-13:]
        g.text(shown + ('_' if self._blink else ''), 0, H - 8)
