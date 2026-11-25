from auri.ui import IconMenu
from auri import icons
from apps.giochi import icone
from auri.i18n import t

# (module, class); the menu scene is the function of the same name in icone
GAMES = (
    ('volo', 'Volo'), ('corsie', 'Corsie'), ('incastro', 'Incastro'), ('rompimuro', 'Rompimuro'),
    ('trefila', 'TreFila'), ('salisali', 'SaliSali'), ('catapulta', 'Catapulta'),
)


def _opener(sys, mod, cls):
    def go():
        # imported on demand: on the ESP32 only the chosen game stays in RAM
        m = __import__('apps.giochi.' + mod, None, None, (cls,))
        sys.push(getattr(m, cls)(sys))
        # name first: every game counts for the world leaderboard
        from apps.giochi.classifica import NomeInput, valid, player_name
        if not valid(player_name(sys)):
            sys.push(NomeInput(sys, lambda n: None))
    return go


def menu(sys):
    def snake():
        from apps.snake import Snake
        sys.push(Snake(sys))
    items = [(t('g_' + m), getattr(icone, m), _opener(sys, m, c)) for m, c in GAMES]
    items.append((t('snake'), icons.SNAKE, snake))
    m = IconMenu(sys, items)
    m.kind = 'giochi'
    return m
