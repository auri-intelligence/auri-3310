"""Tutti i test di AurI OS in un colpo: py tools/tutti_i_test.py [--banchi]

Senza opzioni: i test sul PC (veloci, ~2 minuti) + la compilazione .mpy per il Nokia.
--banchi aggiunge le prove nel browser (serve.py acceso): grafica framebuf byte per byte, banco telefono
(cervello) e banco Nokia (tutte le app a raffica con la CPU dell'ESP32). Ci vogliono ~25 minuti.
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PC = ['test_cervello', 'test_bridge_cervello', 'test_camera', 'test_novita', 'test_llm_esp32', 'test_giochi',
      'test_esp32_finto', 'compila_mpy']
BANCHI = [['confronta_framebuf'], ['banco_telefono', '--modello', 'auto', '--nota', 'tutti_i_test'],
          ['banco_nokia', '--nota', 'tutti_i_test']]


def lancia(args):
    t0 = time.time()
    r = subprocess.run([sys.executable, '-u', os.path.join(ROOT, 'tools', args[0] + '.py')] + args[1:],
                       capture_output=True, text=True, cwd=ROOT)
    out = (r.stdout + r.stderr).strip().splitlines()
    esito = 'ok ' if r.returncode == 0 else 'NO '
    print('%s %-20s %5.0f s  %s' % (esito, args[0], time.time() - t0, out[-1][:90] if out else ''), flush=True)
    if r.returncode:
        print('\n'.join('      ' + x for x in out[-15:]))
    return r.returncode == 0


def main():
    prove = [[p] for p in PC] + (BANCHI if '--banchi' in sys.argv else [])
    falliti = [p[0] for p in prove if not lancia(p)]
    print('\n%s' % ('TUTTO VERDE' if not falliti else 'FALLITI: ' + ', '.join(falliti)))
    return 1 if falliti else 0


if __name__ == '__main__':
    sys.exit(main())
