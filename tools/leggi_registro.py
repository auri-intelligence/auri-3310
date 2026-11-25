"""Legge il registro che il simulatore pubblico manda da solo quando qualcosa va storto.

  py tools/leggi_registro.py [quante]      (predefinito 10 invii, i piu' recenti per ultimi)

La chiave sta in tools/classifica/chiave_registro.txt (fuori da git, mai online) e nelle Proprieta'
dello script Google (REGISTRO_CHIAVE). L'indirizzo e' quello della classifica: firmware/web/classifica.txt.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
url = open(os.path.join(ROOT, 'firmware', 'web', 'classifica.txt')).read().strip()
chiave = open(os.path.join(ROOT, 'tools', 'classifica', 'chiave_registro.txt')).read().strip()
n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
q = urllib.parse.urlencode({'leggi': chiave, 'n': n})
with urllib.request.urlopen(url + ('&' if '?' in url else '?') + q, timeout=30) as r:
    dati = json.loads(r.read())
if 'righe' not in dati:
    sys.exit('Risposta: %s (script aggiornato? chiave giusta?)' % dati)
for quando, sessione, motivo, testo in dati['righe']:
    print('=' * 70)
    print('%s  sessione %s  motivo: %s' % (quando, sessione, motivo))
    print(testo.replace(' | ', chr(10)))
