"""Test del cervello del telefono vero (formato llama2.c): py tools/test_llm_esp32.py

Costruisce un mini-modello finto (pesi a caso, 8 numeri di larghezza) e il suo tokenizer, poi lo fa
girare con hardware/cervello/prova_llm.py. Serve a controllare che la mappa dei pesi e il giro di
generazione siano giusti: sono gli stessi conti del modulo C che gira sull'ESP32-S3, quindi se qui
tornano, sulla microSD si copia un modello vero senza sorprese. Niente download, niente hardware.
"""
import os
import random
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'hardware', 'cervello'))
TMP = os.path.join(ROOT, 'tmp', 'cervello')
os.makedirs(TMP, exist_ok=True)

from prova_llm import Modello, Tokenizer, genera

DIM, HID, LAYERS, HEADS, KV, VOCAB, SEQ = 8, 16, 2, 2, 1, 16, 24
PAROLE = ['<unk>', '<s>', '</s>'] + ['<0x%02X>' % b for b in range(8)] + [' ', 'a', 'o', 'ao', ' ao']


def scrivi_modello(path, condiviso=True):
    head = DIM // HEADS
    n = [VOCAB * DIM, LAYERS * DIM, LAYERS * DIM * HEADS * head, LAYERS * DIM * KV * head,
         LAYERS * DIM * KV * head, LAYERS * HEADS * head * DIM, LAYERS * DIM,
         LAYERS * DIM * HID, LAYERS * HID * DIM, LAYERS * DIM * HID, DIM,
         SEQ * head // 2, SEQ * head // 2]
    if not condiviso:
        n.append(VOCAB * DIM)
    tot = sum(n)
    rng = random.Random(7)
    pesi = [rng.uniform(-0.3, 0.3) for _ in range(tot)]
    with open(path, 'wb') as f:
        f.write(struct.pack('<7i', DIM, HID, LAYERS, HEADS, KV, VOCAB if condiviso else -VOCAB, SEQ))
        f.write(struct.pack('<%df' % tot, *pesi))
    return tot


def scrivi_tokenizer(path):
    parole = PAROLE[:VOCAB] if VOCAB <= len(PAROLE) else PAROLE
    with open(path, 'wb') as f:
        f.write(struct.pack('<i', max(len(p) for p in parole)))
        for i, p in enumerate(parole):
            b = p.encode('utf-8')
            f.write(struct.pack('<fi', float(-i), len(b)))
            f.write(b)
    return len(parole)


def test_mappa_pesi():
    mp = os.path.join(TMP, 'mini.bin')
    scrivi_modello(mp)
    m = Modello(mp)
    assert (m.dim, m.layers, m.heads, m.vocab, m.seq) == (DIM, LAYERS, HEADS, VOCAB, SEQ)
    assert m.shared and m.kv_dim == DIM * KV // HEADS
    assert m.avanzo == 0, 'i pesi non finiscono dove dovrebbero: avanzano %d numeri' % m.avanzo
    print('ok  mappa dei pesi (pesi condivisi)')

    mp2 = os.path.join(TMP, 'mini_nc.bin')
    scrivi_modello(mp2, condiviso=False)
    m2 = Modello(mp2)
    assert not m2.shared and m2.avanzo == 0, m2.avanzo
    print('ok  mappa dei pesi (classificatore separato)')


def test_generazione():
    mp = os.path.join(TMP, 'mini.bin')
    tp = os.path.join(TMP, 'mini_tok.bin')
    scrivi_modello(mp)
    n = scrivi_tokenizer(tp)
    m = Modello(mp)
    t = Tokenizer(tp, m.vocab)
    assert len(t.parole) == min(n, VOCAB)
    tok = t.codifica('ao')
    assert tok[0] == 1, 'manca il token di inizio'
    assert all(0 <= x < m.vocab for x in tok), tok
    testo, secondi = genera(m, t, 'ao', passi=12, temp=0.8)
    assert isinstance(testo, str) and len(testo) > 0, 'non ha generato niente'
    testo2, _ = genera(m, t, 'ao', passi=12, temp=0.8)
    assert testo == testo2, 'con lo stesso seme deve uscire lo stesso testo'
    greedy, _ = genera(m, t, 'ao', passi=12, temp=0)
    assert isinstance(greedy, str)
    print('ok  generazione: "%s" (%.2f s), ripetibile col seme' % (testo.replace('\n', ' ')[:30], secondi))


def test_memoria():
    """Quanto peserebbe sull'ESP32-S3 un modello vero: conti, non promesse."""
    for nome, dim, layers, seq, kv_dim, pesi_mb in (
            ('stories260K', 64, 5, 512, 8, 1.0),
            ('stories15M', 288, 6, 256, 288, 57.9)):
        kv = layers * seq * kv_dim * 2 * 4 / 1024 / 1024
        print('    %-12s pesi %.1f MB + discorso %.2f MB -> %s'
              % (nome, pesi_mb, kv, 'entra negli 8 MB di PSRAM' if pesi_mb + kv < 7.5 else 'NON entra: serve la microSD a pezzi'))
    print('ok  conti della memoria')


if __name__ == '__main__':
    test_mappa_pesi()
    test_generazione()
    test_memoria()
    print('\ntutti i test passati. File finti in', TMP)
