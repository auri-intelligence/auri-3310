"""Creates tools/video/parteN/ ready to work in:  .venv/Scripts/python nuova_parte.py 3"""
import os
import re
import sys

VIDEO = os.path.dirname(os.path.abspath(__file__))

MONTA = '''import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from base import *  # noqa: F401,F403

# whisper transcription errors -> copione text (on screen it is always "3310")
FIX = {{"'occhia": 'Nokia', 'Club': 'Claude', 'Cloud': 'Claude'}}


def rules(words):
    pass


v = Video(__file__, fix=FIX, rules=rules, static_boxes={{}}, no_monitor=('scanner',))
v.next_label = 'PARTE {nxt} IN ARRIVO'
T = v.T


def sc_hook(t):
    c = background(t).convert('RGBA')
    place_phone(c, phone(brain_bits(t)))
    # title fully visible from frame 0: most viewers leave within 1 s
    draw_text(c, 'TITOLO', CX, 175, 150, fill=WHITE, stroke=9, stroke_fill=(5, 12, 28))
    return c, 1.0, 0, 0


SCENES = [(0.0, sc_hook)]
HITS = [0.05]

if __name__ == '__main__':
    v.run(SCENES, HITS, shake_until=2.0, name='parte{n}')
'''

COPERTINA = '''import os
import sys

sys.argv = sys.argv[:1]
import monta as m
from base import *  # noqa: F401,F403

SQ0, SQ1 = 420, 1500  # everything important inside the central square (1:1 and 3:4 grids)
c = background(0).convert('RGBA')
place_phone(c, phone(brain_bits(0.6)), 0.0, 620, 1300)
c = c.convert('RGB')
draw_text(c, 'TITOLO', CX, SQ0 + 30, 150, fill=WHITE, stroke=10, stroke_fill=(5, 12, 30))
d = ImageDraw.Draw(c)
d.rounded_rectangle((CX - 150, 230, CX + 150, 316), radius=43, fill=GREEN)
draw_text(c, 'PARTE {n}', CX, 240, 54, fill=(5, 12, 30), path=FONT_BOLD)
out = os.path.join(m.v.here, 'pubblicato')
os.makedirs(out, exist_ok=True)
c.save(os.path.join(out, 'copertina_parte{n}.png'))
c.crop((0, SQ0, W, SQ1)).save(os.path.join(out, 'copertina_parte{n}_1x1.png'))
print(os.path.join(out, 'copertina_parte{n}.png'))
'''


def from_parte2(name, dict_name):
    s = open(os.path.join(VIDEO, 'parte2', name), encoding='utf-8').read()
    return re.sub(r'%s = \{.*?\n\}' % dict_name, '%s = {\n}' % dict_name, s, flags=re.S)


def main():
    n = int(sys.argv[1])
    d = os.path.join(VIDEO, 'parte%d' % n)
    if os.path.exists(d):
        raise SystemExit('%s esiste gia' % d)
    for sub in ('girato', 'commenti', 'out', 'pubblicato'):
        os.makedirs(os.path.join(d, sub))
    files = {
        'copione.txt': 'Scrivi qui il copione. "3310" va scritto "trentatré dieci" (lo legge il TTS).\n',
        'monta.py': MONTA.format(n=n, nxt=n + 1),
        'copertina.py': COPERTINA.format(n=n),
        'clips.py': from_parte2('clips.py', 'CLIPS'),
        'traccia.py': from_parte2('traccia.py', 'LOGHI'),
    }
    for k, v in files.items():
        open(os.path.join(d, k), 'w', encoding='utf-8').write(v)
    print(d)


if __name__ == '__main__':
    main()
