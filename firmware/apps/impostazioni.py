from auri import i18n, keys
from auri.ui import App, Menu, TextView, Confirm, header, softkey
from auri.gfx import W
from auri.i18n import t
from auri.settings import PROFILES
from auri.sound import RINGTONES
from auri.core import VERSION


def onoff(v):
    return t('on') if v else t('off')


def submenu(sys, title, build):
    # Rebuilt after every change so the labels always show the current values.
    def open_():
        m = Menu(sys, title, build())
        m.rebuild = lambda: setattr(m, 'items', build())
        sys.push(m)
    return open_


def refresh(sys):
    m = sys.top
    if hasattr(m, 'rebuild'):
        m.rebuild()
        sys.dirty = True


class Volume(App):
    def __init__(self, sys):
        super().__init__(sys)
        self.v = sys.settings['volume']

    def on_key(self, k):
        if k in (keys.UP, keys.DOWN):
            self.v = max(0, min(5, self.v + (1 if k == keys.UP else -1)))
            if self.v:
                self.sys.hal.beep(880, 80, self.v)
        elif k == keys.NAVI:
            self.sys.settings.set(volume=self.v, profile='custom')
            self.sys.pop()
            refresh(self.sys)
        else:
            super().on_key(k)

    def draw(self, g):
        header(g, t('volume'))
        for i in range(5):
            h = 4 + i * 4
            x = 12 + i * 12
            if i < self.v:
                g.fill_rect(x, 34 - h, 9, h)
            else:
                g.rect(x, 34 - h, 9, h)
        softkey(g, 'OK')


def Impostazioni(sys):
    st = sys.settings

    def profiles():
        def pick(n):
            def run():
                st.profile(n)
                refresh(sys)
            return run
        cur = st['profile']
        return [(('>' if n == cur else ' ') + t('prof_' + n), pick(n)) for n, _v, _b, _k in PROFILES]

    def tones():
        def ringtone():
            def pick(i):
                def run():
                    st.set(ringtone=i)
                    name, song, bpm = RINGTONES[i]
                    sys.play(song, bpm)
                    refresh(sys)
                return run
            cur = st['ringtone']
            m = Menu(sys, t('ringtone'), [(('>' if i == cur else ' ') + r[0], pick(i)) for i, r in enumerate(RINGTONES)])
            m.sel = cur
            m.rebuild = lambda: setattr(m, 'items', [(('>' if i == st['ringtone'] else ' ') + r[0], pick(i)) for i, r in enumerate(RINGTONES)])
            sys.push(m)

        def toggle(key):
            def run():
                st.set(**{key: not st[key], 'profile': 'custom'})
                refresh(sys)
            return run

        return [
            ('1 ' + t('ringtone'), ringtone),
            ('2 %s %d' % (t('volume'), st['volume']), lambda: sys.push(Volume(sys))),
            ('3 %s %s' % (t('vibration'), onoff(st['vibra'])), toggle('vibra')),
            ('4 %s %s' % (t('keytones'), onoff(st['keytones'])), toggle('keytones')),
        ]

    def display():
        def light():
            steps = (5, 15, 30, 0)
            i = (steps.index(st['light_s']) + 1) % len(steps) if st['light_s'] in steps else 1
            st.set(light_s=steps[i])
            sys.light()
            refresh(sys)

        def anim():
            st.set(boot_anim=not st['boot_anim'])
            refresh(sys)

        ls = st['light_s']
        return [
            ('1 %s %s' % (t('backlight'), ('%ds' % ls) if ls else t('always')), light),
            ('2 %s %s' % (t('boot_anim'), onoff(st['boot_anim'])), anim),
        ]

    def clock():
        def fmt():
            st.set(clock24=not st['clock24'])
            refresh(sys)
        return [('1 %s %s' % (t('clock_fmt'), '24h' if st['clock24'] else '12h'), fmt)]

    def battery():
        pct, chg = sys.battery
        sys.push(TextView(sys, t('battery'), '%d%%\n%s' % (pct, t('charging') if chg else t('on_battery'))))

    def language():
        def pick(code):
            def run():
                st.set(lang=code)
                i18n.set_lang(code)
                sys.home()
            return run
        m = Menu(sys, t('language'), [(('>' if c == i18n.lang else ' ') + name, pick(c)) for c, name in i18n.LANGS])
        m.sel = [c for c, _n in i18n.LANGS].index(i18n.lang)
        sys.push(m)

    def info():
        pct, chg = sys.battery
        sys.push(TextView(sys, t('info'), 'AurI OS %s\nAurI-3310\n%s %d%%' % (VERSION, t('battery'), pct)))

    def reset():
        def done(ok):
            if ok:
                st.reset()
                sys.toast(t('done'))
        sys.push(Confirm(sys, t('reset_q'), done))

    items = [
        ('1 ' + t('profiles'), submenu(sys, t('profiles'), profiles)),
        ('2 ' + t('tones'), submenu(sys, t('tones'), tones)),
        ('3 ' + t('display'), submenu(sys, t('display'), display)),
        ('4 ' + t('clock'), submenu(sys, t('clock'), clock)),
        ('5 ' + t('battery'), battery),
        ('6 ' + t('language'), language),
        ('7 ' + t('info'), info),
        ('8 ' + t('reset'), reset),
    ]
    return Menu(sys, t('settings'), items)
