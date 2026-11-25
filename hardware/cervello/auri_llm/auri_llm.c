/*
 * auri_llm - un piccolo transformer (stile llama2.c) dentro MicroPython, per l'AurI-3310.
 *
 * I pesi arrivano dalla microSD a pezzi, dal lato Python (begin/feed/end), cosi' il modulo non ha
 * bisogno di conoscere il filesystem: funziona con la SD montata da MicroPython, con la flash
 * interna o con qualunque altra cosa si possa leggere da Python.
 *
 * Un passo per chiamata: next() fa un solo giro del modello e restituisce un pezzo di testo.
 * Cosi' AurI OS resta vivo (tasti, display, orologio) mentre il cervello pensa.
 *
 * Formato dei pesi: checkpoint di llama2.c (karpathy), float32, intestazione di 7 interi.
 * Formato del tokenizer: tokenizer.bin di llama2.c (lunghezza massima, poi punteggio+lunghezza+byte).
 *
 * MIT License - Copyright (c) 2026 Luigi Califano
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objstr.h"
#include "py/binary.h"

#ifdef ESP_PLATFORM
#include "esp_heap_caps.h"
/* Sull'ESP32-S3 i pesi stanno nella PSRAM esterna: la RAM interna non basterebbe mai. */
#define BIG_ALLOC(n) heap_caps_malloc((n), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT)
#define BIG_CALLOC(n, s) heap_caps_calloc((n), (s), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT)
#define BIG_FREE(p) heap_caps_free(p)
#else
#define BIG_ALLOC(n) malloc(n)
#define BIG_CALLOC(n, s) calloc((n), (s))
#define BIG_FREE(p) free(p)
#endif

typedef struct {
    int dim, hidden_dim, n_layers, n_heads, n_kv_heads, vocab_size, seq_len, shared;
} Config;

typedef struct {
    float *tok_emb, *rms_att, *wq, *wk, *wv, *wo, *rms_ffn, *w1, *w2, *w3, *rms_final, *wcls;
} Weights;

typedef struct {
    float *x, *xb, *xb2, *hb, *hb2, *q, *k, *v, *att, *logits, *kcache, *vcache;
} State;

static uint8_t *g_blob = NULL;      /* il file dei pesi, intero, in PSRAM */
static size_t g_blob_size = 0, g_blob_got = 0;
static Config g_cfg;
static Weights g_w;
static State g_s;
static int g_ready = 0;

static char **g_vocab = NULL;       /* tokenizer */
static float *g_scores = NULL;
static int g_vocab_n = 0;

static int *g_prompt = NULL;        /* generazione in corso */
static int g_prompt_n = 0, g_pos = 0, g_steps = 0, g_token = 0, g_running = 0;
static float g_temp = 0.9f, g_topp = 0.9f;
static unsigned long long g_rng = 1234567ULL;
static char g_piece[64];

/* --- matematica ------------------------------------------------------- */

static void rmsnorm(float *o, float *x, float *w, int size) {
    float ss = 0.0f;
    for (int j = 0; j < size; j++) ss += x[j] * x[j];
    ss = 1.0f / sqrtf(ss / size + 1e-5f);
    for (int j = 0; j < size; j++) o[j] = w[j] * (ss * x[j]);
}

static void softmax(float *x, int size) {
    float max = x[0];
    for (int i = 1; i < size; i++) if (x[i] > max) max = x[i];
    float sum = 0.0f;
    for (int i = 0; i < size; i++) { x[i] = expf(x[i] - max); sum += x[i]; }
    for (int i = 0; i < size; i++) x[i] /= sum;
}

static void matmul(float *out, float *x, float *w, int n, int d) {
    /* out[d] = w[d][n] . x[n] : qui dentro se ne va quasi tutto il tempo */
    for (int i = 0; i < d; i++) {
        float val = 0.0f;
        float *row = w + (size_t)i * n;
        for (int j = 0; j < n; j++) val += row[j] * x[j];
        out[i] = val;
    }
}

/* --- un giro del modello ------------------------------------------------ */

static float *forward(int token, int pos) {
    Config *p = &g_cfg;
    Weights *w = &g_w;
    State *s = &g_s;
    int dim = p->dim;
    int kv_dim = (p->dim * p->n_kv_heads) / p->n_heads;
    int kv_mul = p->n_heads / p->n_kv_heads;
    int hidden_dim = p->hidden_dim;
    int head_size = dim / p->n_heads;

    memcpy(s->x, w->tok_emb + (size_t)token * dim, dim * sizeof(float));

    for (int l = 0; l < p->n_layers; l++) {
        rmsnorm(s->xb, s->x, w->rms_att + (size_t)l * dim, dim);

        size_t loff = (size_t)l * p->seq_len * kv_dim;
        s->k = s->kcache + loff + (size_t)pos * kv_dim;
        s->v = s->vcache + loff + (size_t)pos * kv_dim;

        matmul(s->q, s->xb, w->wq + (size_t)l * dim * dim, dim, dim);
        matmul(s->k, s->xb, w->wk + (size_t)l * dim * kv_dim, dim, kv_dim);
        matmul(s->v, s->xb, w->wv + (size_t)l * dim * kv_dim, dim, kv_dim);

        /* RoPE: ogni coppia di numeri viene ruotata in base alla posizione */
        for (int i = 0; i < dim; i += 2) {
            int head_dim = i % head_size;
            float freq = 1.0f / powf(10000.0f, head_dim / (float)head_size);
            float val = pos * freq;
            float fcr = cosf(val), fci = sinf(val);
            int rotn = i < kv_dim ? 2 : 1;
            for (int v = 0; v < rotn; v++) {
                float *vec = v == 0 ? s->q : s->k;
                float v0 = vec[i], v1 = vec[i + 1];
                vec[i] = v0 * fcr - v1 * fci;
                vec[i + 1] = v0 * fci + v1 * fcr;
            }
        }

        for (int h = 0; h < p->n_heads; h++) {
            float *q = s->q + h * head_size;
            float *att = s->att + h * p->seq_len;
            for (int t = 0; t <= pos; t++) {
                float *k = s->kcache + loff + (size_t)t * kv_dim + (h / kv_mul) * head_size;
                float score = 0.0f;
                for (int i = 0; i < head_size; i++) score += q[i] * k[i];
                att[t] = score / sqrtf((float)head_size);
            }
            softmax(att, pos + 1);
            float *xb = s->xb + h * head_size;
            memset(xb, 0, head_size * sizeof(float));
            for (int t = 0; t <= pos; t++) {
                float *v = s->vcache + loff + (size_t)t * kv_dim + (h / kv_mul) * head_size;
                float a = att[t];
                for (int i = 0; i < head_size; i++) xb[i] += a * v[i];
            }
        }

        matmul(s->xb2, s->xb, w->wo + (size_t)l * dim * dim, dim, dim);
        for (int i = 0; i < dim; i++) s->x[i] += s->xb2[i];

        rmsnorm(s->xb, s->x, w->rms_ffn + (size_t)l * dim, dim);
        matmul(s->hb, s->xb, w->w1 + (size_t)l * dim * hidden_dim, dim, hidden_dim);
        matmul(s->hb2, s->xb, w->w3 + (size_t)l * dim * hidden_dim, dim, hidden_dim);
        for (int i = 0; i < hidden_dim; i++) {
            float v = s->hb[i];
            v *= (1.0f / (1.0f + expf(-v)));      /* SwiGLU */
            s->hb[i] = v * s->hb2[i];
        }
        matmul(s->xb, s->hb, w->w2 + (size_t)l * dim * hidden_dim, hidden_dim, dim);
        for (int i = 0; i < dim; i++) s->x[i] += s->xb[i];
    }

    rmsnorm(s->x, s->x, w->rms_final, dim);
    matmul(s->logits, s->x, w->wcls, dim, p->vocab_size);
    return s->logits;
}

/* --- scelta del prossimo pezzo ------------------------------------------ */

static float rnd(void) {
    g_rng ^= g_rng >> 12;
    g_rng ^= g_rng << 25;
    g_rng ^= g_rng >> 27;
    return ((g_rng * 0x2545F4914F6CDD1DULL) >> 40) / 16777216.0f;
}

static int sample_token(float *logits) {
    int n = g_cfg.vocab_size;
    if (g_temp <= 0.0f) {
        int best = 0;
        for (int i = 1; i < n; i++) if (logits[i] > logits[best]) best = i;
        return best;
    }
    for (int i = 0; i < n; i++) logits[i] /= g_temp;
    softmax(logits, n);
    float coin = rnd();
    if (g_topp <= 0.0f || g_topp >= 1.0f) {
        float cdf = 0.0f;
        for (int i = 0; i < n; i++) { cdf += logits[i]; if (coin < cdf) return i; }
        return n - 1;
    }
    /* top-p senza ordinare tutto: si taglia sotto soglia e si normalizza */
    float cutoff = (1.0f - g_topp) / (n - 1);
    float sum = 0.0f;
    for (int i = 0; i < n; i++) if (logits[i] >= cutoff) sum += logits[i];
    float cdf = 0.0f;
    coin *= sum;
    for (int i = 0; i < n; i++) {
        if (logits[i] < cutoff) continue;
        cdf += logits[i];
        if (coin < cdf) return i;
    }
    return n - 1;
}

/* --- tokenizer ---------------------------------------------------------- */

static int str_lookup(const char *str, int len) {
    for (int i = 0; i < g_vocab_n; i++) {
        if ((int)strlen(g_vocab[i]) == len && memcmp(g_vocab[i], str, len) == 0) return i;
    }
    return -1;
}

static void free_vocab(void) {
    if (g_vocab) {
        for (int i = 0; i < g_vocab_n; i++) BIG_FREE(g_vocab[i]);
        BIG_FREE(g_vocab);
        g_vocab = NULL;
    }
    if (g_scores) { BIG_FREE(g_scores); g_scores = NULL; }
    g_vocab_n = 0;
}

static int encode(const char *text, int text_len, int *tokens, int max_tokens) {
    /* BPE come llama2.c: prima i singoli caratteri, poi si uniscono le coppie migliori */
    int n = 0;
    if (n < max_tokens) tokens[n++] = 1;                 /* BOS */
    int dummy = str_lookup(" ", 1);
    if (text_len > 0 && dummy >= 0 && n < max_tokens) tokens[n++] = dummy;

    char buf[8];
    int blen = 0;
    for (int i = 0; i < text_len && n < max_tokens; i++) {
        unsigned char c = (unsigned char)text[i];
        if ((c & 0xC0) != 0x80) blen = 0;                /* inizio di un carattere */
        if (blen < (int)sizeof(buf) - 1) buf[blen++] = (char)c;
        buf[blen] = '\0';
        if (i + 1 < text_len && ((unsigned char)text[i + 1] & 0xC0) == 0x80 && blen < 4) continue;
        int id = str_lookup(buf, blen);
        if (id >= 0) {
            tokens[n++] = id;
        } else {
            /* ripiego di llama2.c: i byte grezzi stanno a partire dall'indice 3 */
            for (int k = 0; k < blen && n < max_tokens; k++) {
                int b = (unsigned char)buf[k] + 3;
                tokens[n++] = b < g_vocab_n ? b : 0;
            }
        }
        blen = 0;
    }

    while (1) {
        float best = -1e10f;
        int best_id = -1, best_idx = -1;
        for (int i = 0; i < n - 1; i++) {
            char pair[64];
            int l1 = (int)strlen(g_vocab[tokens[i]]), l2 = (int)strlen(g_vocab[tokens[i + 1]]);
            if (l1 + l2 >= (int)sizeof(pair)) continue;
            memcpy(pair, g_vocab[tokens[i]], l1);
            memcpy(pair + l1, g_vocab[tokens[i + 1]], l2);
            int id = str_lookup(pair, l1 + l2);
            if (id >= 0 && g_scores[id] > best) { best = g_scores[id]; best_id = id; best_idx = i; }
        }
        if (best_idx < 0) break;
        tokens[best_idx] = best_id;
        for (int i = best_idx + 1; i < n - 1; i++) tokens[i] = tokens[i + 1];
        n--;
    }
    return n;
}

static const char *decode_piece(int prev, int token) {
    if (token < 0 || token >= g_vocab_n) return "";
    const char *piece = g_vocab[token];
    if (prev == 1 && piece[0] == ' ') piece++;            /* dopo BOS niente spazio iniziale */
    unsigned int byte_val;
    if (sscanf(piece, "<0x%02X>", &byte_val) == 1) {
        g_piece[0] = (char)byte_val;
        g_piece[1] = '\0';
        return g_piece;
    }
    return piece;
}

/* --- memoria ------------------------------------------------------------- */

static void free_state(void) {
    float **p[] = {&g_s.x, &g_s.xb, &g_s.xb2, &g_s.hb, &g_s.hb2, &g_s.q,
                   &g_s.att, &g_s.logits, &g_s.kcache, &g_s.vcache};
    for (unsigned i = 0; i < sizeof(p) / sizeof(p[0]); i++) {
        if (*p[i]) { BIG_FREE(*p[i]); *p[i] = NULL; }
    }
    g_s.k = g_s.v = NULL;
}

static int alloc_state(void) {
    Config *c = &g_cfg;
    int kv_dim = (c->dim * c->n_kv_heads) / c->n_heads;
    g_s.x = BIG_CALLOC(c->dim, sizeof(float));
    g_s.xb = BIG_CALLOC(c->dim, sizeof(float));
    g_s.xb2 = BIG_CALLOC(c->dim, sizeof(float));
    g_s.hb = BIG_CALLOC(c->hidden_dim, sizeof(float));
    g_s.hb2 = BIG_CALLOC(c->hidden_dim, sizeof(float));
    g_s.q = BIG_CALLOC(c->dim, sizeof(float));
    g_s.att = BIG_CALLOC((size_t)c->n_heads * c->seq_len, sizeof(float));
    g_s.logits = BIG_CALLOC(c->vocab_size, sizeof(float));
    g_s.kcache = BIG_CALLOC((size_t)c->n_layers * c->seq_len * kv_dim, sizeof(float));
    g_s.vcache = BIG_CALLOC((size_t)c->n_layers * c->seq_len * kv_dim, sizeof(float));
    if (!g_s.x || !g_s.xb || !g_s.xb2 || !g_s.hb || !g_s.hb2 || !g_s.q ||
        !g_s.att || !g_s.logits || !g_s.kcache || !g_s.vcache) {
        free_state();
        return 0;
    }
    return 1;
}

static void map_weights(void) {
    Config *c = &g_cfg;
    float *p = (float *)(g_blob + 7 * sizeof(int));
    int head_size = c->dim / c->n_heads;
    size_t nl = (size_t)c->n_layers;
    g_w.tok_emb = p;    p += (size_t)c->vocab_size * c->dim;
    g_w.rms_att = p;    p += nl * c->dim;
    g_w.wq = p;         p += nl * c->dim * (c->n_heads * head_size);
    g_w.wk = p;         p += nl * c->dim * (c->n_kv_heads * head_size);
    g_w.wv = p;         p += nl * c->dim * (c->n_kv_heads * head_size);
    g_w.wo = p;         p += nl * (c->n_heads * head_size) * c->dim;
    g_w.rms_ffn = p;    p += nl * c->dim;
    g_w.w1 = p;         p += nl * c->dim * c->hidden_dim;
    g_w.w2 = p;         p += nl * c->hidden_dim * c->dim;
    g_w.w3 = p;         p += nl * c->dim * c->hidden_dim;
    g_w.rms_final = p;  p += c->dim;
    p += (size_t)c->seq_len * head_size / 2;      /* vecchie tabelle RoPE, non servono */
    p += (size_t)c->seq_len * head_size / 2;
    g_w.wcls = c->shared ? g_w.tok_emb : p;
}

/* --- funzioni viste da Python -------------------------------------------- */

static mp_obj_t auri_begin(mp_obj_t size_in) {
    size_t size = mp_obj_get_int(size_in);
    if (g_blob) { BIG_FREE(g_blob); g_blob = NULL; }
    free_state();
    g_ready = 0;
    g_blob = BIG_ALLOC(size);
    if (!g_blob) mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("pesi troppo grandi per la memoria"));
    g_blob_size = size;
    g_blob_got = 0;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(auri_begin_obj, auri_begin);

static mp_obj_t auri_feed(mp_obj_t buf_in) {
    mp_buffer_info_t b;
    mp_get_buffer_raise(buf_in, &b, MP_BUFFER_READ);
    if (!g_blob || g_blob_got + b.len > g_blob_size) {
        mp_raise_ValueError(MP_ERROR_TEXT("pezzo fuori misura"));
    }
    memcpy(g_blob + g_blob_got, b.buf, b.len);
    g_blob_got += b.len;
    return mp_obj_new_int(g_blob_got);
}
static MP_DEFINE_CONST_FUN_OBJ_1(auri_feed_obj, auri_feed);

static mp_obj_t auri_end(void) {
    if (!g_blob || g_blob_got < 7 * sizeof(int)) mp_raise_ValueError(MP_ERROR_TEXT("pesi incompleti"));
    int *h = (int *)g_blob;
    g_cfg.dim = h[0];
    g_cfg.hidden_dim = h[1];
    g_cfg.n_layers = h[2];
    g_cfg.n_heads = h[3];
    g_cfg.n_kv_heads = h[4];
    g_cfg.shared = h[5] > 0 ? 1 : 0;
    g_cfg.vocab_size = h[5] > 0 ? h[5] : -h[5];
    g_cfg.seq_len = h[6];
    if (g_cfg.dim <= 0 || g_cfg.n_heads <= 0 || g_cfg.n_layers <= 0 || g_cfg.vocab_size <= 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("file dei pesi non riconosciuto"));
    }
    map_weights();
    if (!alloc_state()) mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("memoria finita per lo stato"));
    g_ready = 1;
    return mp_obj_new_int(g_cfg.dim);
}
static MP_DEFINE_CONST_FUN_OBJ_0(auri_end_obj, auri_end);

static mp_obj_t auri_tokenizer(mp_obj_t buf_in) {
    mp_buffer_info_t b;
    mp_get_buffer_raise(buf_in, &b, MP_BUFFER_READ);
    free_vocab();
    uint8_t *p = (uint8_t *)b.buf;
    size_t off = 4;                                   /* max_token_length, non serve */
    int n = 0, cap = 1024;
    g_vocab = BIG_ALLOC(cap * sizeof(char *));
    g_scores = BIG_ALLOC(cap * sizeof(float));
    if (!g_vocab || !g_scores) mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("tokenizer troppo grande"));
    while (off + 8 <= b.len) {
        if (n == cap) {
            cap *= 2;
            char **nv = BIG_ALLOC(cap * sizeof(char *));
            float *ns = BIG_ALLOC(cap * sizeof(float));
            if (!nv || !ns) mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("tokenizer troppo grande"));
            memcpy(nv, g_vocab, n * sizeof(char *));
            memcpy(ns, g_scores, n * sizeof(float));
            BIG_FREE(g_vocab); BIG_FREE(g_scores);
            g_vocab = nv; g_scores = ns;
        }
        float score;
        int len;
        memcpy(&score, p + off, 4);
        memcpy(&len, p + off + 4, 4);
        off += 8;
        if (len < 0 || off + len > b.len) break;
        char *s = BIG_ALLOC(len + 1);
        if (!s) mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("tokenizer troppo grande"));
        memcpy(s, p + off, len);
        s[len] = '\0';
        off += len;
        g_vocab[n] = s;
        g_scores[n] = score;
        n++;
    }
    g_vocab_n = n;
    return mp_obj_new_int(n);
}
static MP_DEFINE_CONST_FUN_OBJ_1(auri_tokenizer_obj, auri_tokenizer);

static mp_obj_t auri_info(void) {
    mp_obj_t d = mp_obj_new_dict(0);
    mp_obj_dict_store(d, MP_OBJ_NEW_QSTR(MP_QSTR_dim), mp_obj_new_int(g_cfg.dim));
    mp_obj_dict_store(d, MP_OBJ_NEW_QSTR(MP_QSTR_layers), mp_obj_new_int(g_cfg.n_layers));
    mp_obj_dict_store(d, MP_OBJ_NEW_QSTR(MP_QSTR_heads), mp_obj_new_int(g_cfg.n_heads));
    mp_obj_dict_store(d, MP_OBJ_NEW_QSTR(MP_QSTR_vocab), mp_obj_new_int(g_cfg.vocab_size));
    mp_obj_dict_store(d, MP_OBJ_NEW_QSTR(MP_QSTR_seq), mp_obj_new_int(g_cfg.seq_len));
    mp_obj_dict_store(d, MP_OBJ_NEW_QSTR(MP_QSTR_bytes), mp_obj_new_int(g_blob_got));
    mp_obj_dict_store(d, MP_OBJ_NEW_QSTR(MP_QSTR_ready), mp_obj_new_bool(g_ready && g_vocab_n > 0));
    return d;
}
static MP_DEFINE_CONST_FUN_OBJ_0(auri_info_obj, auri_info);

static mp_obj_t auri_start(size_t n_args, const mp_obj_t *args) {
    if (!g_ready || g_vocab_n == 0) mp_raise_ValueError(MP_ERROR_TEXT("cervello non caricato"));
    size_t len;
    const char *text = mp_obj_str_get_data(args[0], &len);
    g_temp = n_args > 1 ? mp_obj_get_float(args[1]) : 0.9f;
    g_topp = n_args > 2 ? mp_obj_get_float(args[2]) : 0.9f;
    g_steps = n_args > 3 ? mp_obj_get_int(args[3]) : 120;
    if (n_args > 4) g_rng = (unsigned long long)mp_obj_get_int(args[4]) | 1ULL;
    if (g_steps > g_cfg.seq_len) g_steps = g_cfg.seq_len;

    if (g_prompt) { BIG_FREE(g_prompt); g_prompt = NULL; }
    g_prompt = BIG_ALLOC((len + 3) * sizeof(int));
    if (!g_prompt) mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("memoria finita"));
    g_prompt_n = encode(text, (int)len, g_prompt, (int)len + 3);
    if (g_prompt_n < 1) mp_raise_ValueError(MP_ERROR_TEXT("domanda vuota"));
    g_token = g_prompt[0];
    g_pos = 0;
    g_running = 1;
    return mp_obj_new_int(g_prompt_n);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(auri_start_obj, 1, 5, auri_start);

static mp_obj_t auri_next(void) {
    if (!g_running || g_pos >= g_steps) { g_running = 0; return mp_const_none; }
    float *logits = forward(g_token, g_pos);
    int next;
    if (g_pos < g_prompt_n - 1) {
        next = g_prompt[g_pos + 1];
    } else {
        next = sample_token(logits);
    }
    g_pos++;
    if (next == 1) { g_running = 0; return mp_const_none; }   /* BOS = fine del racconto */
    const char *piece = decode_piece(g_token, next);
    g_token = next;
    return mp_obj_new_str(piece, strlen(piece));
}
static MP_DEFINE_CONST_FUN_OBJ_0(auri_next_obj, auri_next);

static mp_obj_t auri_stop(void) {
    g_running = 0;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(auri_stop_obj, auri_stop);

static mp_obj_t auri_free(void) {
    g_running = 0;
    g_ready = 0;
    free_state();
    free_vocab();
    if (g_blob) { BIG_FREE(g_blob); g_blob = NULL; }
    if (g_prompt) { BIG_FREE(g_prompt); g_prompt = NULL; }
    g_blob_size = g_blob_got = 0;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(auri_free_obj, auri_free);

static const mp_rom_map_elem_t auri_llm_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_auri_llm) },
    { MP_ROM_QSTR(MP_QSTR_begin), MP_ROM_PTR(&auri_begin_obj) },
    { MP_ROM_QSTR(MP_QSTR_feed), MP_ROM_PTR(&auri_feed_obj) },
    { MP_ROM_QSTR(MP_QSTR_end), MP_ROM_PTR(&auri_end_obj) },
    { MP_ROM_QSTR(MP_QSTR_tokenizer), MP_ROM_PTR(&auri_tokenizer_obj) },
    { MP_ROM_QSTR(MP_QSTR_info), MP_ROM_PTR(&auri_info_obj) },
    { MP_ROM_QSTR(MP_QSTR_start), MP_ROM_PTR(&auri_start_obj) },
    { MP_ROM_QSTR(MP_QSTR_next), MP_ROM_PTR(&auri_next_obj) },
    { MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&auri_stop_obj) },
    { MP_ROM_QSTR(MP_QSTR_free), MP_ROM_PTR(&auri_free_obj) },
};
static MP_DEFINE_CONST_DICT(auri_llm_globals, auri_llm_globals_table);

const mp_obj_module_t auri_llm_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&auri_llm_globals,
};

MP_REGISTER_MODULE(MP_QSTR_auri_llm, auri_llm_user_cmodule);
