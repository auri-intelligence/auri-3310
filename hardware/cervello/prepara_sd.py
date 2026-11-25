"""Prepara la microSD del Nokia AurI-3310: cervello locale e, se vuoi, tutto AurI OS.

    py hardware/cervello/prepara_sd.py E:\\                    # copia AurI OS e i pesi gia' scaricati
    py hardware/cervello/prepara_sd.py E:\\ --scarica mini --si  # scarica anche i pesi (1 MB)
    py hardware/cervello/prepara_sd.py --solo-pesi --scarica mini --si   # solo nella cartella del progetto

Sulla scheda nasce questa roba:
    /auri/cervello/stories260K.bin   i pesi del modello
    /auri/cervello/tok512.bin        il suo tokenizer
    /auri/os/                        AurI OS (auri, apps, hal, main.py) se usi --os

I pesi restano sempre anche in hardware/cervello/pesi/ (dentro Z:), cosi' la scheda si rifa' in un minuto.
Niente scarica niente senza --si: e' una regola del progetto.

Modelli (licenza MIT, da karpathy/tinyllamas e karpathy/llama2.c):
    mini   stories260K  ~1 MB    gira in PSRAM a circa 20 pezzi al secondo (racconti brevi in inglese)
    medio  stories15M   ~58 MB   NON entra negli 8 MB di PSRAM: per ora serve solo per le prove sul PC
"""
import os
import shutil
import sys
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(os.path.dirname(QUI))
PESI = os.path.join(QUI, 'pesi')
FIRMWARE = os.path.join(RADICE, 'firmware')

MODELLI = {
    'mini': [
        ('stories260K.bin', 'https://huggingface.co/karpathy/tinyllamas/resolve/main/stories260K/stories260K.bin'),
        ('tok512.bin', 'https://huggingface.co/karpathy/tinyllamas/resolve/main/stories260K/tok512.bin'),
    ],
    'medio': [
        ('stories15M.bin', 'https://huggingface.co/karpathy/tinyllamas/resolve/main/stories15M.bin'),
        ('tokenizer.bin', 'https://raw.githubusercontent.com/karpathy/llama2.c/master/tokenizer.bin'),
    ],
}
OS_FILES = ['main.py', 'config.json']
OS_DIRS = ['auri', 'apps', 'hal']


def scarica(nome):
    os.makedirs(PESI, exist_ok=True)
    for file, url in MODELLI[nome]:
        out = os.path.join(PESI, file)
        if os.path.exists(out):
            print('   c e gia:', file)
            continue
        print('   scarico', file, '...')
        with urllib.request.urlopen(url, timeout=120) as r, open(out, 'wb') as f:
            shutil.copyfileobj(r, f)
        print('   %s: %.1f MB' % (file, os.path.getsize(out) / 1e6))


def copia_pesi(dest, nome):
    cart = os.path.join(dest, 'auri', 'cervello')
    os.makedirs(cart, exist_ok=True)
    for file, _url in MODELLI[nome]:
        src = os.path.join(PESI, file)
        if not os.path.exists(src):
            print('   manca', file, '(usa --scarica %s --si)' % nome)
            continue
        shutil.copy2(src, os.path.join(cart, file))
        print('   copiato', file)


def copia_os(dest):
    cart = os.path.join(dest, 'auri', 'os')
    os.makedirs(cart, exist_ok=True)
    for d in OS_DIRS:
        s, t = os.path.join(FIRMWARE, d), os.path.join(cart, d)
        if os.path.exists(t):
            shutil.rmtree(t)
        shutil.copytree(s, t, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for f in OS_FILES:
        s = os.path.join(FIRMWARE, f)
        if os.path.exists(s):
            shutil.copy2(s, os.path.join(cart, f))
    print('   AurI OS copiato in /auri/os (il telefono ci aggiunge /sd/auri/os al percorso)')


def main(argv):
    if '--aiuto' in argv or '-h' in argv:
        print(__doc__)
        return 0
    dest = next((a for a in argv[1:] if not a.startswith('-')), None)
    nome = 'mini'
    if '--scarica' in argv:
        i = argv.index('--scarica')
        nome = argv[i + 1] if i + 1 < len(argv) else 'mini'
        if nome not in MODELLI:
            print('modello sconosciuto:', nome)
            return 1
        if '--si' not in argv:
            tot = {'mini': '1 MB', 'medio': '58 MB'}[nome]
            print('Per scaricare %s (%s, licenza MIT) aggiungi --si.' % (nome, tot))
            for f, u in MODELLI[nome]:
                print('  ', f, '<-', u)
            return 1
        print('Scarico i pesi in hardware/cervello/pesi (dentro Z:)')
        scarica(nome)

    if '--solo-pesi' in argv or not dest:
        if not dest:
            print('Niente scheda indicata: mi fermo ai file del progetto. Vedi --aiuto.')
        return 0

    if not os.path.isdir(dest):
        print('La scheda', dest, 'non si trova. Collegala e riprova.')
        return 1
    print('Preparo', dest)
    copia_pesi(dest, nome)
    if '--os' in argv:
        copia_os(dest)
    print('\nFatto. Sul telefono: la microSD si monta da sola su /sd, i pesi stanno in /sd/auri/cervello.')
    print('Il cervello si accende dal menu AurI (il caricamento dalla scheda dura qualche secondo).')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
