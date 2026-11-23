from auri import keys
from auri.ui import App, Menu, TextView, Confirm, header
from auri.t9 import MultiTap
from auri.gfx import W, H, wrap

# Auri's own mascot: a tiny antenna robot.
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
PERMS = (('Chiedi sempre', 'default'), ('Accetta modifiche', 'acceptEdits'), ('Solo piano', 'plan'))
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
        try:
            cfg = sys.config
            self.info.update(sys.hal.request('GET', cfg['bridge_url'] + '/v1/info', None, cfg.get('token')))
        except Exception:
            self.info['plan'] = 'offline'

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
                self.sys.push(self.options())
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
        if k == keys.NAVI:
            self.sys.push(self.options())
        elif k == keys.C and not self.input.text:
            self.sys.home()
        else:
            self.input.long(k)

    def tick(self, now):
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
        body.update({'session': self.session, 'model': MODELS[self.model][1], 'effort': self.effort,
                     'permission_mode': PERMS[self.perm][1], 'remote': self.remote})
        try:
            r = self.sys.hal.request('POST', cfg['bridge_url'] + path, body, cfg.get('token'))
        except Exception as e:
            self.state = 'chat'
            self.log.append(('!', 'Bridge non raggiungibile'))
            return
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
            self.sys.push(Confirm(self.sys, c.get('text', 'Procedo?'), done))

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
            sys.push(TextView(sys, 'Stato', 'Claude Code %s\n%s %s %s\n%s\nSessione: %s\nRemote: %s' % (
                self.info['version'], MODELS[self.model][0], DOT, self.effort, self.info['plan'],
                (self.session or 'nuova')[:8], 'on' if self.remote else 'off')))

        return Menu(sys, 'Opzioni', [
            ('Modello', pick('Modello', [m[0] for m in MODELS], lambda: self.model, set_model)),
            ('Effort', pick('Effort', EFFORTS, lambda: EFFORTS.index(self.effort), set_effort)),
            ('Permessi', pick('Permessi', [p[0] for p in PERMS], lambda: self.perm, set_perm)),
            ('Remote ' + ('on' if self.remote else 'off'), toggle_remote),
            ('Nuova sessione', new_session),
            ('Stato', show_info),
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
        g.hline(0, 8, W)
        lines = []
        for who, text in self.log:
            for i, l in enumerate(wrap(text, 12)):
                lines.append(((who if i == 0 else ' ') + ' ' + l))
        if self.state == 'wait':
            lines.append('* ...')
        body = 3
        end = max(0, len(lines) - self.scroll)
        for i, l in enumerate(lines[max(0, end - body):end]):
            g.text(l, 0, 10 + i * 9)
        g.hline(0, H - 10, W)
        inp = self.input.text
        shown = ('> ' + inp)[-13:]
        g.text(shown + ('_' if self._blink else ''), 0, H - 8)
