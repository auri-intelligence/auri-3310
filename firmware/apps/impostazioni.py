from auri import i18n
from auri.ui import Menu
from auri.i18n import t


def Impostazioni(sys):
    def choose_lang():
        def pick(code):
            def run():
                st = sys.hal.load('settings', {})
                st['lang'] = code
                sys.hal.save('settings', st)
                i18n.set_lang(code)
                sys.home()
            return run
        m = Menu(sys, t('language'), [(('>' if c == i18n.lang else ' ') + name, pick(c)) for c, name in i18n.LANGS])
        m.sel = [c for c, _n in i18n.LANGS].index(i18n.lang)
        sys.push(m)

    return Menu(sys, t('settings'), [('1 ' + t('language'), choose_lang)])
