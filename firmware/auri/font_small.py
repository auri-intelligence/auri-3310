# Carattere piccolo 3x5 (0x20-0x7E) disegnato per AurI: 21 lettere per riga invece di 14.
# Ogni lettera: 5 righe da 3 bit (bit 2 = colonna di sinistra). Le minuscole sono piccole maiuscole
# alte 4 pixel con le gambe (g, p, q, y) giu' di uno: si leggono meglio a questa misura.
W = 3
H = 6
ADV = 4
LINE = 6
_G = (
    # spazio ! " # $ % & ' ( ) * + , - . /
    "00000 22202 55000 57575 36736 51245 25356 22000 12221 42224 05250 02720 00024 00700 00002 11244"
    # 0-9
    " 75557 26227 71747 71317 55711 74717 74757 71122 75757 75717"
    # : ; < = > ? @
    " 02020 02024 12421 07070 42124 71302 25743"
    # A-Z
    " 25755 65656 34443 65556 74647 74644 34556 55755 72227 11152 55655 44447 57755 75555 25552"
    " 65644 25563 65655 34216 72222 55557 55522 55775 55255 55222 71247"
    # [ \ ] ^ _ `
    " 32223 44211 62226 25000 00007 42000"
    # a-z (riga 0 vuota: minuscole basse)
    " 06357 44656 03443 11353 03563 12722 35316 44655 20222 10115 04565 62223 07775 06555 02552"
    " 65644 35311 06544 03616 27221 05553 05552 05577 05255 55316 07247"
    # { | } ~
    " 32423 22222 62126 03600"
)
GLYPHS = _G.split()
# punti accesi di ogni lettera, calcolati una volta
PUNTI = []
for _g in GLYPHS:
    _p = []
    _desc = 1 if _g in () else 0
    for _r, _ch in enumerate(_g):
        _v = int(_ch)
        for _c in range(3):
            if _v & (4 >> _c):
                _p.append((_c, _r))
    PUNTI.append(tuple(_p))
# lettere con la gamba sotto la riga: si disegnano un pixel piu' in basso
GIU = set('gpqy')
