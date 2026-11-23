"""AurI OS simulator.

  python sim.py                          opens the window
  python sim.py --shot out.png --keys "navi,down,navi" [--time 12:34]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from auri.core import System
from auri import keys
from apps.home import Home
from hal.pc import PCHal, W, H, LIT, DARK

SCALE = 6
KEYBOARD = {
    'Up': keys.UP, 'Down': keys.DOWN, 'Return': keys.NAVI, 'space': keys.NAVI, 'KP_Enter': keys.NAVI,
    'BackSpace': keys.C, 'Escape': keys.C, 'Delete': keys.C,
    'asterisk': keys.STAR, 'KP_Multiply': keys.STAR, 'numbersign': keys.HASH, 'KP_Divide': keys.HASH,
}
PAD = [
    [('C', keys.C), ('OK', keys.NAVI), ('▲', keys.UP), ('▼', keys.DOWN)],
    [('1', '1'), ('2 abc', '2'), ('3 def', '3')],
    [('4 ghi', '4'), ('5 jkl', '5'), ('6 mno', '6')],
    [('7 pqrs', '7'), ('8 tuv', '8'), ('9 wxyz', '9')],
    [('*', keys.STAR), ('0 ␣', '0'), ('#', keys.HASH)],
]


def load_config():
    for name in ('config.json', 'config.example.json'):
        try:
            with open(os.path.join(HERE, name)) as f:
                return json.load(f)
        except OSError:
            pass
    return {'bridge_url': 'http://127.0.0.1:8310'}


def headless(args):
    clock = None
    if args.time:
        h, m = args.time.split(':')
        clock = (2026, 11, 23, int(h), int(m), 0, 0, 327)
    hal = PCHal(clock)
    s = System(hal, load_config())
    s.push(Home(s))
    s.step()
    for k in [k for k in args.keys.split(',') if k]:
        if k.startswith('wait'):
            hal._t0 -= int(k[4:] or 1000) / 1000
            s.step()
            continue
        hal.press(k)
        s.step()
        hal.release(k)
        hal._t0 -= 0.05
        s.step()
    hal._t0 -= 1
    s.step()
    hal.save_png(args.shot)


def window():
    import tkinter as tk
    hal = PCHal()
    s = System(hal, load_config())
    s.push(Home(s))

    root = tk.Tk()
    root.title('AurI-3310')
    root.configure(bg='#2b2f33')
    root.resizable(False, False)
    lcd = tk.Canvas(root, width=W * SCALE, height=H * SCALE, highlightthickness=8, highlightbackground='#c9ccce', bg='black')
    lcd.pack(padx=24, pady=(24, 12))
    img = tk.PhotoImage(width=W, height=H)
    big = [None]
    item = lcd.create_image(0, 0, anchor='nw')

    def render():
        bg, fg = LIT if hal.lit() else DARK
        b = '#%02x%02x%02x' % bg
        f = '#%02x%02x%02x' % fg
        rows = ' '.join('{' + ' '.join(f if hal.pixel(x, y) else b for x in range(W)) + '}' for y in range(H))
        img.put(rows, to=(0, 0))
        big[0] = img.zoom(SCALE)
        lcd.itemconfigure(item, image=big[0])

    hal.on_show = render

    def shake(ms):
        x, y = root.winfo_x(), root.winfo_y()
        for i in range(6):
            root.after(i * 30, lambda d=(4 if i % 2 else -4): root.geometry('+%d+%d' % (x + d, y)))
        root.after(200, lambda: root.geometry('+%d+%d' % (x, y)))

    hal.on_vibrate = shake

    pad = tk.Frame(root, bg='#2b2f33')
    pad.pack(padx=24, pady=(0, 16))
    for r, row in enumerate(PAD):
        for c, (label, k) in enumerate(row):
            b = tk.Label(pad, text=label, width=6 if len(row) == 4 else 8, height=2, bg='#d9dcde', fg='#1d1f21',
                         font=('Segoe UI', 10, 'bold'), relief='raised', bd=2)
            b.grid(row=r, column=c * (4 // len(row)) if len(row) == 4 else c, columnspan=1 if len(row) == 4 else 1,
                   padx=3, pady=3, sticky='nsew')
            b.bind('<ButtonPress-1>', lambda e, k=k: hal.press(k))
            b.bind('<ButtonRelease-1>', lambda e, k=k: hal.release(k))
    tk.Label(root, text='Tastiera: frecce, Invio = OK, Backspace = C, 0-9, * e #',
             bg='#2b2f33', fg='#9aa0a6', font=('Segoe UI', 9)).pack(pady=(0, 12))

    held = set()

    def keymap(e):
        if e.keysym in KEYBOARD:
            return KEYBOARD[e.keysym]
        if e.char and e.char in '0123456789*#':
            return e.char
        return None

    def down(e):
        k = keymap(e)
        if k and k not in held:
            held.add(k)
            hal.press(k)

    def up(e):
        k = keymap(e)
        if k in held:
            held.discard(k)
            hal.release(k)

    root.bind('<KeyPress>', down)
    root.bind('<KeyRelease>', up)

    was_lit = [True]

    def loop():
        s.step()
        if hal.lit() != was_lit[0]:
            was_lit[0] = hal.lit()
            render()
        root.after(20, loop)

    hal.light(1)
    loop()
    root.mainloop()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--shot')
    p.add_argument('--keys', default='')
    p.add_argument('--time')
    a = p.parse_args()
    headless(a) if a.shot else window()
