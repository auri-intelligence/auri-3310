DEFAULTS = {
    'profile': 'normal', 'volume': 3, 'ringtone': 0, 'vibra': True, 'keytones': True,
    'light_s': 15, 'boot_anim': True, 'clock24': True, 'welcome': '',
}

# volume, vibration, key tones
PROFILES = (
    ('normal', 3, True, True), ('silent', 0, True, False),
    ('meeting', 1, True, False), ('outdoor', 5, True, True),
)


class Settings:
    def __init__(self, hal):
        self.hal = hal
        self.d = dict(DEFAULTS)
        self.d.update(hal.load('settings', {}))

    def __getitem__(self, k):
        return self.d.get(k, DEFAULTS.get(k))

    def set(self, **kw):
        tr = getattr(self.hal, 'track', None)
        if tr:
            for k, v in kw.items():
                tr('impostazione/%s=%s' % (k, v))
        self.d.update(kw)
        self.hal.save('settings', self.d)

    def profile(self, name):
        for n, vol, vib, kt in PROFILES:
            if n == name:
                self.set(profile=n, volume=vol, vibra=vib, keytones=kt)

    def reset(self):
        lang = self.d.get('lang')
        self.d = dict(DEFAULTS)
        if lang:
            self.d['lang'] = lang
        self.hal.save('settings', self.d)
