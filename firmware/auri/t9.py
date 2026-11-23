from auri import keys

MAP = {
    '1': ".,?!'-1@:/()",
    '2': 'abc2', '3': 'def3', '4': 'ghi4', '5': 'jkl5',
    '6': 'mno6', '7': 'pqrs7', '8': 'tuv8', '9': 'wxyz9',
    '0': ' 0',
}
TIMEOUT_MS = 900


class MultiTap:
    def __init__(self, text=''):
        self.text = text
        self.upper = True
        self._key = None
        self._idx = 0
        self._t = 0
        self._cap = False

    def pending(self, now):
        return self._key is not None and now - self._t < TIMEOUT_MS

    def key(self, k, now):
        if k in MAP:
            chars = MAP[k]
            if self.pending(now) and k == self._key:
                self._idx = (self._idx + 1) % len(chars)
                ch = chars[self._idx]
                self.text = self.text[:-1] + (ch.upper() if self._cap else ch)
            else:
                self._idx = 0
                self._cap = self.upper
                self.upper = False
                ch = chars[0]
                self.text += ch.upper() if self._cap else ch
            self._key = k
            self._t = now
            if self.text and self.text[-1] in '.?!':
                self.upper = True
            return True
        self._key = None
        if k == keys.C:
            self.text = self.text[:-1]
            return True
        if k == keys.HASH:
            self.upper = not self.upper
            return True
        if k == keys.STAR:
            self.text += '*'
            return True
        return False

    def long(self, k):
        if k == keys.C:
            self.text = ''
            return True
        if k in MAP:
            self.text = self.text[:-1] + k
            self._key = None
            return True
        return False

