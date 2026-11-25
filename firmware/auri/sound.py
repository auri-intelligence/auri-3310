# Melodies in a compact RTTTL-like form: "e6:8 d#6:8 -:4", note+octave:fraction of a whole note, "." adds half.
NOTES = {'c': 0, 'c#': 1, 'd': 2, 'd#': 3, 'e': 4, 'f': 5, 'f#': 6, 'g': 7, 'g#': 8, 'a': 9, 'a#': 10, 'b': 11}

# Only original tunes or public-domain melodies. The classic 3310 sounds are rebuilt from their public
# sources, never copied: "Gran Vals" is Tarrega's 1902 waltz (public domain) in our own arrangement
# (a tone lower, different ending); the message tone spells "SMS" in Morse code, at our own pitch.
RINGTONES = (
    ('Gran Vals', 'd6:8 c6:8 e5:4 f#5:4 b5:8 a5:8 c5:4 d5:4 a5:8 g5:8 b4:4 d5:4 g5:4 -:8 g5:8 b5:2', 180),
    ('AurI', 'c6:8 e6:8 g6:8 c7:4 g6:8 c7:2', 160),
    ('Retro', 'e6:16 g6:16 e7:16 c7:16 d7:16 g7:8 -:16 g6:16 e7:8', 140),
    ('Ode alla gioia', 'e5:4 e5:4 f5:4 g5:4 g5:4 f5:4 e5:4 d5:4 c5:4 c5:4 d5:4 e5:4 e5:4. d5:8 d5:2', 160),
    ('Per Elisa', 'e6:16 d#6:16 e6:16 d#6:16 e6:16 b5:16 d6:16 c6:16 a5:8 -:16 c5:16 e5:16 a5:16 b5:8', 110),
    ('Valzer minuto', 'g#5:8 a5:8 c6:8 b5:8 d6:8 c6:8 a5:8 c6:8 e6:4 d6:8 c6:8 b5:4 a5:4', 200),
    ('Morse SMS', 'b6:32 -:32 b6:32 -:32 b6:32 -:16 b6:16 -:32 b6:16 -:16 b6:32 -:32 b6:32 -:32 b6:32', 125),
    ('Bip bip', 'a6:16 -:16 a6:16 -:8 a6:16 -:16 a6:16', 120),
)
BOOT = 'c5:16 g5:16 c6:16 e6:16 g6:8 c7:4'
SHUTDOWN = 'g6:16 e6:16 c6:16 g5:16 c5:4'
# messaggio in arrivo: "SMS" in Morse (... -- ...), come facevano i telefoni di allora
NOTIFY = 'b6:32 -:32 b6:32 -:32 b6:32 -:16 b6:16 -:32 b6:16 -:16 b6:32 -:32 b6:32 -:32 b6:32'
# batteria scarica: due note scendenti brevi
WARN = 'e6:16 -:32 c6:8'
# tasti: un "tic" corto e acuto, come la tastiera del 3310
KEY_TONE = (1760, 14)


def parse(song, bpm):
    whole = 240000 // bpm
    out = []
    for tok in song.split():
        n, d = tok.split(':')
        ms = whole // int(d.rstrip('.'))
        if d.endswith('.'):
            ms += ms // 2
        if n == '-':
            out.append((0, ms))
        else:
            semis = NOTES[n[:-1]] + 12 * (int(n[-1]) - 4) - 9
            out.append((int(440 * 2 ** (semis / 12)), ms))
    return out


class Player:
    """Non-blocking: the system loop calls tick() and the HAL plays one note at a time."""

    def __init__(self, hal):
        self.hal = hal
        self.queue = []
        self.next = 0
        self.vol = 0

    def play(self, song, vol, bpm=140):
        self.queue = parse(song, bpm) if vol else []
        self.vol = vol
        self.next = 0

    def stop(self):
        self.queue = []

    def busy(self):
        return bool(self.queue)

    def tick(self, now):
        if not self.queue or now < self.next:
            return
        f, ms = self.queue.pop(0)
        if f:
            self.hal.beep(f, max(10, ms - 12), self.vol)
        self.next = now + ms
