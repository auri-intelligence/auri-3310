"""Compila AurI OS per il Nokia vero: ogni .py del firmware -> .mpy (bytecode di MicroPython).

  py tools/compila_mpy.py            -> build/mpy/ (pronto da copiare sull'ESP32 o sulla microSD)

Perche': sull'ESP32 un .py va compilato a ogni avvio (lento e mangia RAM: nel banco Nokia l'accensione ha
un passo da 1,1 s mentre carica i moduli); il .mpy e' gia' compilato. Fa anche da controllo: mpy-cross e'
il compilatore di MicroPython, quindi segnala la sintassi che CPython accetta e MicroPython no.
main.py resta .py (MicroPython lo cerca con quel nome). Le HAL del PC e del browser non servono al telefono.
mpy-cross sta in tools/mpy/.venv (py -m venv tools/mpy/.venv; tools/mpy/.venv/Scripts/python -m pip install mpy-cross).
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW = os.path.join(ROOT, 'firmware')
OUT = os.path.join(ROOT, 'build', 'mpy')
PY = os.path.join(ROOT, 'tools', 'mpy', '.venv', 'Scripts' if os.name == 'nt' else 'bin', 'python')
SALTA = {'hal/pc.py', 'hal/web.py', 'sim.py', 'serve.py'}


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    errori, fatti, prima, dopo = [], 0, 0, 0
    for cartella in ('auri', 'apps', 'hal'):
        for base, _d, files in os.walk(os.path.join(FW, cartella)):
            if '__pycache__' in base:
                continue
            for f in files:
                if not f.endswith('.py'):
                    continue
                src = os.path.join(base, f)
                rel = os.path.relpath(src, FW).replace('\\', '/')
                if rel in SALTA:
                    continue
                dst = os.path.join(OUT, rel[:-3] + '.mpy')
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                # -march=xtensawin: ESP32-S3; -O1 toglie gli assert e i docstring dal bytecode
                r = subprocess.run([PY, '-m', 'mpy_cross', '-march=xtensawin', '-O1', '-s', rel, '-o', dst, src],
                                   capture_output=True, text=True)
                if r.returncode:
                    errori.append('%s: %s' % (rel, (r.stderr or r.stdout).strip()))
                else:
                    fatti += 1
                    prima += os.path.getsize(src)
                    dopo += os.path.getsize(dst)
    shutil.copy(os.path.join(FW, 'main.py'), os.path.join(OUT, 'main.py'))
    shutil.copy(os.path.join(FW, 'config.example.json'), os.path.join(OUT, 'config.example.json'))
    print('%d moduli compilati: %d KB di .py -> %d KB di .mpy in build/mpy/' % (fatti, prima // 1024, dopo // 1024))
    for e in errori:
        print('ERRORE', e)
    return 1 if errori else 0


if __name__ == '__main__':
    sys.exit(main())
