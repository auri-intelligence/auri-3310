from auri.ui import IconMenu
from auri import icons
from auri.i18n import t

# (module, class, icon, title key)
GAMES = (
    ('volo', 'Volo', 'G_VOLO'), ('corsie', 'Corsie', 'G_CORSIE'), ('incastro', 'Incastro', 'G_INCASTRO'),
    ('rompimuro', 'Rompimuro', 'G_ROMPIMURO'), ('trefila', 'TreFila', 'G_TREFILA'),
    ('salisali', 'SaliSali', 'G_SALISALI'), ('catapulta', 'Catapulta', 'G_CATAPULTA'),
)


def _opener(sys, mod, cls):
    def go():
        # imported on demand: on the ESP32 only the chosen game stays in RAM
        m = __import__('apps.giochi.' + mod, None, None, (cls,))
        sys.push(getattr(m, cls)(sys))
    return go


def menu(sys):
    def snake():
        from apps.snake import Snake
        sys.push(Snake(sys))
    items = [(t('g_' + m), getattr(icons, ic), _opener(sys, m, c)) for m, c, ic in GAMES]
    items.append((t('snake'), icons.SNAKE, snake))
    m = IconMenu(sys, items)
    m.kind = 'giochi'
    return m
