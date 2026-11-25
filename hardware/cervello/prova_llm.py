"""Lo stesso cervello del modulo C, scritto in Python, per provarlo sul PC prima di montarlo.

    py hardware/cervello/prova_llm.py modello.bin tokenizer.bin "C era una volta"

Serve a tre cose:
  1. controllare che un file di pesi (formato llama2.c, float32) sia buono prima di copiarlo sulla microSD;
  2. avere un riferimento: se il modulo C sull'ESP32 dice cose diverse, l'errore e' nel C;
  3. capire quanta memoria serve davvero (lo dice alla fine).

Usa numpy se c'e' (molto piu' veloce), altrimenti funziona lo stesso, piano.
"""
import math
import os
import struct
import sys
import time

try:
    import numpy as np
except ImportError:
    np = None


class Modello:
    def __init__(self, path):
        with open(path, 'rb') as f:
            dati = f.read()
        (dim, hidden, layers, heads, kv_heads, vocab, seq) = struct.unpack('<7i', dati[:28])
        self.dim, self.hidden, self.layers = dim, hidden, layers
        self.heads, self.kv_heads, self.seq = heads, kv_heads, seq
        self.shared = vocab > 0
        self.vocab = abs(vocab)
        self.head = dim // heads
        self.kv_dim = dim * kv_heads // heads
        pesi = memoryview(dati)[28:]
        self.pesi = (np.frombuffer(dati, dtype=np.float32, offset=28) if np
                     else struct.unpack('<%df' % (len(pesi) // 4), pesi[:len(pesi) // 4 * 4]))
        o = 0

        def prendi(n):
            nonlocal o
            v = self.pesi[o:o + n]
            o += n
            return v

        nl, d, h = layers, dim, self.head
        self.tok_emb = prendi(self.vocab * d)
        self.rms_att = prendi(nl * d)
        self.wq = prendi(nl * d * heads * h)
        self.wk = prendi(nl * d * kv_heads * h)
        self.wv = prendi(nl * d * kv_heads * h)
        self.wo = prendi(nl * heads * h * d)
        self.rms_ffn = prendi(nl * d)
        self.w1 = prendi(nl * d * hidden)
        self.w2 = prendi(nl * hidden * d)
        self.w3 = prendi(nl * d * hidden)
        self.rms_final = prendi(d)
        o += seq * h // 2 * 2                      # vecchie tabelle RoPE: non servono piu'
        self.wcls = self.tok_emb if self.shared else prendi(self.vocab * d)
        self.avanzo = len(self.pesi) - o           # deve essere 0 (o 0 dopo wcls condiviso)
        self.kcache = [self._zeri(nl * seq * self.kv_dim)]
        self.vcache = [self._zeri(nl * seq * self.kv_dim)]

    @staticmethod
    def _zeri(n):
        return np.zeros(n, dtype=np.float32) if np else [0.0] * n

    # --- pezzi di matematica ---
    def _rmsnorm(self, x, w):
        if np is not None:
            ss = 1.0 / math.sqrt(float((x * x).sum()) / len(x) + 1e-5)
            return (w * x) * ss
        ss = 1.0 / math.sqrt(sum(v * v for v in x) / len(x) + 1e-5)
        return [w[i] * x[i] * ss for i in range(len(x))]

    def _matmul(self, x, w, n, d, off=0):
        if np is not None:
            return w[off:off + n * d].reshape(d, n) @ x
        return [sum(w[off + i * n + j] * x[j] for j in range(n)) for i in range(d)]

    @staticmethod
    def _softmax(x):
        if np is not None:
            x = np.asarray(x, dtype=np.float32)
            e = np.exp(x - x.max())
            return e / e.sum()
        m = max(x)
        e = [math.exp(v - m) for v in x]
        s = sum(e)
        return [v / s for v in e]

    def forward(self, token, pos):
        d, h, kv = self.dim, self.head, self.kv_dim
        kv_mul = self.heads // self.kv_heads
        x = (self.tok_emb[token * d:(token + 1) * d].copy() if np
             else list(self.tok_emb[token * d:(token + 1) * d]))
        kc, vc = self.kcache[0], self.vcache[0]
        for l in range(self.layers):
            xb = self._rmsnorm(x, self.rms_att[l * d:(l + 1) * d])
            q = self._matmul(xb, self.wq, d, d, l * d * d)
            k = self._matmul(xb, self.wk, d, kv, l * d * kv)
            v = self._matmul(xb, self.wv, d, kv, l * d * kv)
            for i in range(0, d, 2):                      # RoPE
                fr = 1.0 / (10000.0 ** ((i % h) / h))
                c, s = math.cos(pos * fr), math.sin(pos * fr)
                q0, q1 = q[i], q[i + 1]
                q[i], q[i + 1] = q0 * c - q1 * s, q0 * s + q1 * c
                if i < kv:
                    k0, k1 = k[i], k[i + 1]
                    k[i], k[i + 1] = k0 * c - k1 * s, k0 * s + k1 * c
            base = l * self.seq * kv + pos * kv
            kc[base:base + kv] = k
            vc[base:base + kv] = v
            xb = self._zeri(d)
            for hd in range(self.heads):
                off = (hd // kv_mul) * h
                punteggi = []
                for t in range(pos + 1):
                    b = l * self.seq * kv + t * kv + off
                    if np is not None:
                        punteggi.append(float(q[hd * h:(hd + 1) * h] @ kc[b:b + h]))
                    else:
                        punteggi.append(sum(q[hd * h + i] * kc[b + i] for i in range(h)))
                punteggi = self._softmax([p / math.sqrt(h) for p in punteggi])
                for t in range(pos + 1):
                    b = l * self.seq * kv + t * kv + off
                    a = punteggi[t]
                    for i in range(h):
                        xb[hd * h + i] += a * vc[b + i]
            o = self._matmul(xb, self.wo, d, d, l * d * d)
            for i in range(d):
                x[i] += o[i]
            xb = self._rmsnorm(x, self.rms_ffn[l * d:(l + 1) * d])
            hb = self._matmul(xb, self.w1, d, self.hidden, l * d * self.hidden)
            hb3 = self._matmul(xb, self.w3, d, self.hidden, l * d * self.hidden)
            for i in range(self.hidden):
                hb[i] = hb[i] * (1.0 / (1.0 + math.exp(-hb[i]))) * hb3[i]
            o = self._matmul(hb, self.w2, self.hidden, d, l * d * self.hidden)
            for i in range(d):
                x[i] += o[i]
        x = self._rmsnorm(x, self.rms_final)
        return self._matmul(x, self.wcls, d, self.vocab)


class Tokenizer:
    def __init__(self, path, vocab):
        self.parole, self.punti = [], []
        with open(path, 'rb') as f:
            dati = f.read()
        o = 4
        while o + 8 <= len(dati) and len(self.parole) < vocab:
            punto, lung = struct.unpack('<fi', dati[o:o + 8])
            o += 8
            self.parole.append(dati[o:o + lung].decode('utf-8', 'replace'))
            self.punti.append(punto)
            o += lung

    def codifica(self, testo):
        tok = [1]
        if testo and ' ' in self.parole:
            tok.append(self.parole.index(' '))
        for ch in testo:
            if ch in self.parole:
                tok.append(self.parole.index(ch))
            else:
                # ripiego di llama2.c: i byte grezzi stanno a partire dall'indice 3
                tok += [b + 3 if b + 3 < len(self.parole) else 0 for b in ch.encode('utf-8')]
        while True:
            meglio, idx, best = -1e10, -1, -1
            for i in range(len(tok) - 1):
                coppia = self.parole[tok[i]] + self.parole[tok[i + 1]]
                if coppia in self.parole:
                    j = self.parole.index(coppia)
                    if self.punti[j] > meglio:
                        meglio, idx, best = self.punti[j], i, j
            if idx < 0:
                break
            tok[idx:idx + 2] = [best]
        return tok

    def pezzo(self, prec, tok):
        p = self.parole[tok]
        if prec == 1 and p.startswith(' '):
            p = p[1:]
        if p.startswith('<0x') and p.endswith('>'):
            try:
                return chr(int(p[3:-1], 16))
            except ValueError:
                pass
        return p


def genera(modello, tok, testo, passi=60, temp=0.9, seme=1234567):
    rng = seme | 1
    tokens = tok.codifica(testo)
    corrente, out, t0 = tokens[0], [], time.time()
    for pos in range(min(passi, modello.seq)):
        logits = modello.forward(corrente, pos)
        if pos < len(tokens) - 1:
            nxt = tokens[pos + 1]
        elif temp <= 0:
            nxt = int(max(range(len(logits)), key=lambda i: logits[i]))
        else:
            p = Modello._softmax([v / temp for v in logits])
            rng ^= (rng >> 12) & 0xFFFFFFFFFFFFFFFF
            rng = (rng ^ (rng << 25)) & 0xFFFFFFFFFFFFFFFF
            rng ^= rng >> 27
            moneta = ((rng * 0x2545F4914F6CDD1D) >> 40 & 0xFFFFFF) / 16777216.0
            acc, nxt = 0.0, len(p) - 1
            for i, v in enumerate(p):
                acc += float(v)
                if moneta < acc:
                    nxt = i
                    break
        if nxt == 1:
            break
        out.append(tok.pezzo(corrente, nxt))
        corrente = nxt
    return ''.join(out), time.time() - t0


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    mp, tp = sys.argv[1], sys.argv[2]
    testo = sys.argv[3] if len(sys.argv) > 3 else ''
    m = Modello(mp)
    t = Tokenizer(tp, m.vocab)
    kb = os.path.getsize(mp) / 1024
    print('modello: dim %d, strati %d, teste %d, vocabolario %d, contesto %d, %.0f KB'
          % (m.dim, m.layers, m.heads, m.vocab, m.seq, kb))
    if m.avanzo not in (0, m.vocab * m.dim):
        print('ATTENZIONE: avanzano %d numeri, il formato non torna' % m.avanzo)
    testo_out, secondi = genera(m, t, testo)
    print('\n' + testo + testo_out)
    print('\n%.1f s%s' % (secondi, ' (con numpy)' if np is not None else ''))
    kv = m.layers * m.seq * m.kv_dim * 4 / 1024
    print('memoria sul telefono: %.0f KB di pesi + %.0f KB di memoria del discorso' % (kb, kv))
    return 0


if __name__ == '__main__':
    sys.exit(main())
