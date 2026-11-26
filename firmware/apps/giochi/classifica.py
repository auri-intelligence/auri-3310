from auri import keys
from auri.ui import App, header, softkey, snake_load
from auri.net import Richiesta
from auri.gfx import W, H, wrap
from auri.i18n import t
from auri.t9 import MultiTap

# Base list: words are matched after normalising look-alike digits and symbols.
BAD = ('cazz', 'cazo', 'mink', 'minchi', 'stronz', 'merd', 'puttan', 'troi', 'figa', 'fica', 'vaffa', 'fanculo',
       'coglion', 'culo', 'frocio', 'negro', 'porcodio', 'diocan', 'madonn', 'bastard', 'zoccol', 'pompin',
       'fuck', 'fuk', 'shit', 'bitch', 'cunt', 'pussy', 'whore', 'slut', 'nigg', 'faggot', 'rape',
       'nazi', 'hitler', 'porn', 'sex', 'penis', 'vagina', 'tits', 'boob', 'wank', 'twat', 'asshole')
LEET = {'4': 'a', '@': 'a', '3': 'e', '0': 'o', '1': 'i', '!': 'i', '5': 's', '$': 's', '7': 't', '8': 'b',
        '9': 'g', '6': 'g', '2': 'z', 'k': 'c', 'y': 'i', 'j': 'i', 'x': 'cs'}


def normalize(s):
    out = ''
    for ch in s.lower():
        ch = LEET.get(ch, ch)
        if 'a' <= ch[0] <= 'z' and (not out or out[-1] != ch[-1]):
            out += ch
    return out


def is_bad(name):
    n = normalize(name)
    for w in BAD:
        if normalize(w) in n:
            return True
    return False


def valid(name):
    name = name.strip()
    return 3 <= len(name) <= 10 and not is_bad(name)


def sign(game, name, score, key):
    # FNV-1a: only stops casual tampering, the server must still validate
    h = 2166136261
    for ch in '%s|%s|%d|%s' % (game, name, score, key):
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return '%08x' % h


def player_name(sys):
    return sys.hal.load('g_nome', {}).get('nome', '')


def quote(s):
    return ''.join(c if c.isalpha() and ord(c) < 128 or c in '0123456789-_.' else '%%%02X' % b
                   for c in s for b in c.encode())


class NomeInput(App):
    def __init__(self, sys, done):
        super().__init__(sys)
        self.mt = MultiTap(player_name(sys))
        self.done = done
        self.err = ''

    def on_key(self, k):
        now = self.sys.hal.ticks_ms()
        if k == keys.NAVI:
            name = self.mt.text.strip()
            if not 3 <= len(name) <= 10:
                self.err = t('g_name_len')
            elif is_bad(name):
                self.err = t('g_name_bad')
            else:
                self.sys.hal.save('g_nome', {'nome': name})
                self.sys.pop()
                self.done(name)
            return
        if k == keys.C and not self.mt.text:
            self.sys.pop()
            return
        if len(self.mt.text) >= 10 and k in '0123456789' and not self.mt.pending(now):
            return
        self.err = ''
        self.mt.key(k, now)

    def on_long(self, k):
        if not self.mt.long(k):
            super().on_long(k)

    def tick(self, now):
        return True

    def draw(self, g):
        header(g, t('g_name'))
        g.rect(0, 13, W, 11)
        txt = self.mt.text[-12:]
        g.text(txt, 2, 15)
        if (self.sys.hal.ticks_ms() // 400) % 2:
            g.vline(2 + 6 * len(txt), 14, 9)
        g.text_center(self.err or t('g_name_len'), 27)
        softkey(g, 'OK')


def riga(pos, nome, punti):
    """'10 nome  12345' in 14 colonne: punti a destra, nome tagliato solo quanto serve, sempre uno spazio
    in mezzo (prima '%-6s%d' attaccava nome e punti: 'lcalif76')."""
    p = str(punti)
    n = nome[:max(1, 14 - 3 - 1 - len(p))]
    return '%2d %s%s%s' % (pos, n, ' ' * (14 - 3 - len(n) - len(p)), p)


class Classifica(App):
    def __init__(self, sys, game, score):
        super().__init__(sys)
        self.game = game
        self.score = score
        self.url = sys.config.get('scores_url', '')
        self.rows = sys.hal.load('g_' + game, {}).get('top', [])
        self.me = player_name(sys)
        self.world = False
        self.msg = '' if self.url else t('g_world_soon')
        self.pos = 0
        self.req = None           # richiesta in corso: lo schermo resta vivo (snake che gira)
        self.todo = 'name' if self.url and score > 0 else ('get' if self.url else '')
        if self.todo == 'name' and valid(player_name(sys)):
            self.todo = 'send'

    def _start(self):
        name = player_name(self.sys)
        # GET only: a simple request needs no CORS preflight, which Apps Script cannot answer
        q = 'gioco=' + self.game
        if self.todo == 'send' and valid(name):
            q += '&nome=%s&punti=%d&firma=%s' % (quote(name), self.score,
                                                sign(self.game, name, self.score, self.sys.config.get('scores_key', '')))
        self.req = Richiesta(self.sys.hal, 'GET', self.url + ('&' if '?' in self.url else '?') + q)

    def _end(self):
        r, self.req = self.req, None
        top = r.dati.get('top') if isinstance(r.dati, dict) else None
        if top:
            self.rows = [[int(e[1]), str(e[0])[:10]] for e in top[:10]]
            self.world = True
        self.msg = t('g_net_err') if r.errore else ''

    def tick(self, now):
        if self.todo == 'name':
            self.todo = 'send'
            self.sys.push(NomeInput(self.sys, lambda n: None))
            return True
        if self.todo and type(self.sys.top) is Classifica:
            self._start()
            self.todo = ''
            return True
        if self.req:
            if self.req.poll():
                self._end()
            return True          # ridisegna lo snake
        return False

    def on_key(self, k):
        n = len(self.rows) + (1 if self.msg else 0)
        if k in (keys.UP, '2'):
            self.pos = max(0, self.pos - 1)
        elif k in (keys.DOWN, '8'):
            self.pos = min(max(0, n - 3), self.pos + 1)
        elif k in (keys.NAVI, keys.C):
            self.req = None          # si puo' uscire anche mentre aspetta: il risultato si perde
            self.sys.pop()

    def draw(self, g):
        if self.req or self.todo == 'send' or self.todo == 'get':
            header(g, t('g_world'))
            snake_load(g, self.sys.hal.ticks_ms(), 25, t('g_sending'))
            return
        header(g, t('g_world') if self.world else t('g_rank'))
        lines = [riga(i + 1, e[1], e[0]) for i, e in enumerate(self.rows)]
        if not lines:
            lines = ['-']
        if self.msg:
            lines += wrap(self.msg)
        for i, line in enumerate(lines[self.pos:self.pos + 3]):
            mine = self.pos + i < len(self.rows) and self.rows[self.pos + i][1] == self.me[:10]
            if mine:
                g.round_fill(0, 10 + i * 9, W, 9)
            g.text(line[:14], 1, 11 + i * 9, 0 if mine else 1)
        softkey(g, t('back'))
