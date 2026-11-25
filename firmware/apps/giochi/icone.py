from apps.giochi.base import PHONE, PHONE_BIG

# Menu scenes: 84x25 drawn from (x, y), the indestructible 3310 is the hero of each one.
HERO = ('.#######.', '#.......#', '#.#####.#', '#.#...#.#', '#.#...#.#', '#.#####.#', '#.......#',
        '#..###..#', '#.......#', '#.#.#.#.#', '#.......#', '#.#.#.#.#', '#.......#', '#.#.#.#.#',
        '#.......#', '.#.....#.', '..#####..')


def _wall(g, x, y, h):
    g.fill_rect(x, y, 7, h)
    g.dither(x + 1, y + 1, 5, h - 2, 1)
    for yy in range(y + 3, y + h, 5):
        g.hline(x, yy, 7, 0)


def volo(g, x, y):
    _wall(g, x + 44, y, 7)
    _wall(g, x + 44, y + 19, 6)
    _wall(g, x + 70, y, 12)
    _wall(g, x + 70, y + 12, 13)
    g.fill_rect(x + 70, y + 8, 7, 9, 0)          # the hole the phone smashed
    for yy in range(y + 8, y + 17, 2):
        g.pixel(x + 70, yy)
        g.pixel(x + 76, yy + 1)
    g.icon2(PHONE_BIG, x + 22, y + 6, 1, 1)
    for i, yy in enumerate((y + 9, y + 13, y + 17)):
        g.hline(x + 4 + i * 2, yy, 12 - i * 3)
    g.pixel(x + 33, y + 3)
    g.pixel(x + 35, y + 1)


def corsie(g, x, y):
    for j in range(26):
        g.pixel(x + 30 - j, y + j)
        g.pixel(x + 54 + j, y + j)
        if (j // 3) % 2 == 0:
            g.pixel(x + 42, y + j)
    g.rect(x + 46, y + 1, 7, 6)
    g.pixel(x + 49, y + 3)
    g.icon(HERO, x + 24, y + 7)
    for i in range(3):
        g.pixel(x + 26 + i * 2, y + 24 - (i % 2))
    g.fill_rect(x + 60, y + 3, 3, 3)
    g.pixel(x + 61, y + 2)
    g.pixel(x + 61, y + 6)


def incastro(g, x, y):
    cells = (0, 1, 2, 3, 5, 6, 7, 8, 9)
    for row, holes in ((15, ()), (19, ()), (23, (2,))):
        for c in cells:
            if c not in holes:
                g.fill_rect(x + 20 + c * 5, y + row, 4, 3 if row == 23 else 4)
    g.fill_rect(x + 41, y + 13, 4, 12, 0)
    g.icon(HERO, x + 39, y + 1)                    # the 3310 drilling its column
    for dx, dy in ((-4, 12), (-6, 9), (7, 10), (9, 13), (-3, 15), (8, 7)):
        g.pixel(x + 43 + dx, y + dy)
    g.fill_rect(x + 2, y + 2, 4, 4)
    g.fill_rect(x + 6, y + 2, 4, 4)
    g.fill_rect(x + 6, y + 6, 4, 4)
    g.fill_rect(x + 74, y + 4, 4, 4)
    g.fill_rect(x + 74, y + 8, 4, 4)
    g.fill_rect(x + 78, y + 8, 4, 4)


def rompimuro(g, x, y):
    for r in range(3):
        for c in range(7):
            if not (r == 2 and c in (3, 4)) and not (r == 1 and c == 4):
                g.fill_rect(x + c * 12, y + r * 5, 11, 4)
                if r:
                    g.dither(x + c * 12 + 1, y + r * 5 + 1, 9, 2, 2)
    g.icon2(PHONE_BIG, x + 44, y + 9, 1, 1)
    for dx, dy in ((-2, 2), (12, 1), (-4, 6), (14, 5), (-1, -1), (11, -2)):
        g.pixel(x + 44 + dx, y + 9 + dy)
    g.fill_rect(x + 32, y + 23, 18, 2)
    g.hline(x + 31, y + 24, 20)


def trefila(g, x, y):
    from apps.giochi.trefila import GEMS
    for i, gx in enumerate((2, 12, 62, 72)):
        g.icon(GEMS[i], x + gx, y + 9 + (i % 2) * 4)
    g.icon(GEMS[4], x + 4, y + 1)
    g.icon(GEMS[2], x + 73, y + 1)
    for a in range(8):
        dx, dy = ((14, 0), (10, 10), (0, 14), (-10, 10), (-14, 0), (-10, -10), (0, -14), (10, -10))[a]
        g.pixel(x + 42 + dx, y + 12 + dy // 2 + 1)
        g.pixel(x + 42 + dx * 2 // 3, y + 12 + dy // 3 + 1)
    g.icon(HERO, x + 38, y + 4)


def salisali(g, x, y):
    for px, py, w in ((4, 22, 16), (24, 15, 14), (50, 20, 14), (62, 7, 16)):
        g.hline(x + px, y + py, w)
        g.hline(x + px + 1, y + py + 1, w - 2)
    g.icon(('#.#', '.#.', '#.#', '###'), x + 29, y + 11)
    g.icon(HERO, x + 40, y + 1)
    for i in range(3):
        g.pixel(x + 42 + i * 3, y + 20 + i)
        g.pixel(x + 43 + i * 3, y + 23 + i % 2)
    g.rect(x + 68, y + 1, 4, 5)
    g.pixel(x + 69, y)


def catapulta(g, x, y):
    g.hline(x, y + 24, 84)
    g.vline(x + 8, y + 16, 8)
    g.icon(('#...#', '.#.#.', '..#..'), x + 6, y + 13)
    pts = ((14, 14), (20, 9), (27, 5), (34, 3), (41, 3))
    for px, py in pts:
        g.pixel(x + px, y + py)
    g.icon(PHONE, x + 46, y + 1)
    for c in range(3):
        for h in range(3 - c % 2):
            g.rect(x + 64 + c * 6, y + 18 - h * 6, 6, 6)
    for dx, dy in ((-3, 0), (-5, 4), (-2, 7)):
        g.pixel(x + 46 + dx, y + 1 + dy)
