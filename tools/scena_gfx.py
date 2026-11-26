def scena(Canvas, icons):
    ic = icons.AURI
    prove = [
        ('fill', lambda g: g.fill_rect(10, 5, 30, 20, 1)),
        ('hline0', lambda g: (g.fill_rect(0, 0, 84, 48, 1), g.hline(3, 7, 50, 0))),
        ('pixel', lambda g: [g.pixel(i, (i * 7) % 48, 1) for i in range(84)]),
        ('icon1', lambda g: g.icon(ic, 5, 3, 1)),
        ('icon0', lambda g: (g.fill_rect(0, 0, 84, 48, 1), g.icon(ic, 5, 3, 0))),
        ('icon2', lambda g: g.icon2(ic, 40, 10, 1, 2)),
        ('icon2_0', lambda g: (g.fill_rect(0, 0, 84, 48, 1), g.icon2(ic, 20, 18, 0, 2))),
        ('text1', lambda g: g.text('AurI 3310 xyz!', 0, 38, 1)),
        ('text0', lambda g: (g.fill_rect(0, 0, 84, 48, 1), g.text('Neg', 15, 9, 0))),
        ('char2x', lambda g: g.char('1', 50, 0, 1, 2)),
        ('char2x0', lambda g: (g.fill_rect(0, 0, 84, 48, 1), g.char('9', 70, 20, 0, 2))),
        ('dither', lambda g: g.dither(0, 30, 40, 8, 2)),
    ]
    out = []
    for nome, f in prove:
        g = Canvas()
        f(g)
        out.append(nome + ':' + bytes(g.buf).hex())
    t = Canvas(); t.char('4', 30, 5, 1, 2); t.char('2', 42, 20, 1, 2)
    g = Canvas(); g.fill_rect(0, 0, 84, 48, 1); g.blit(t, 12, 28)
    out.append('blit:' + bytes(g.buf).hex())
    return out
