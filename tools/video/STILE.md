# Guida di stile dei video AurI-3310

Vale per ogni video verticale del progetto (TikTok, Reels, Shorts). Tutto il materiale si genera da noi: niente musica, immagini o loghi di terzi.

## Formato
- 1080x1920, 30 fps, MP4 H.264 (yuv420p, crf 18) + AAC 192 kbit/s 48 kHz.
- Durata = voce + circa 3,8 s di chiusura (outro), con l'ultimo fotogramma fermo.

## Colori
| Ruolo | Hex |
|---|---|
| Blu scuro 3310 (sfondo) | `#0B1A3A` |
| Blu secondario (sfumatura) | `#183468` |
| Verde accento (titoli, evidenziazione) | `#AAE85C` |
| Sfondo LCD | `#9DC86A` |
| Pixel LCD | `#1C2B14` |
| Bianco testo | `#F5F8F0` |
| Contorno testo | `#050C1C` |

Lo sfondo ha una griglia leggera ogni 24 px e righe di scansione ogni 4 px (luminosita' al 90%).

## Font
- Titoli: Impact, con contorno di 8 px, comparsa con rimbalzo (scala da 0,4 a 1 in 0,18 s).
- Didascalie, URL, pulsanti: Segoe UI Black.
- Codice e misure: Consolas Bold.

## Didascalie
- Sincronizzate parola per parola (faster-whisper, `word_timestamps=True`), 3 parole per riga o fino alla punteggiatura.
- Segoe UI Black 66 px (si riduce se la riga non ci sta), y = 1525, centrate su x = 540.
- Parola corrente: riquadro verde `#AAE85C` con testo blu; parole gia' dette bianche, quelle successive grigie.
- Correggere sempre a mano gli errori di trascrizione rispetto a `copione.txt` (vedi `FIX` in `monta.py`).

## Il nome AurI
- Si scrive sempre AurI: A e I grandi ed evidenziate (verde, o bianche se il testo e' gia' verde), "ur" piu' piccole (72%) e meno visibili (60% di luminosita').
- Vale per titoli, didascalie e logo (`auri_spans`, `draw_text`, `cap_word` in `monta.py`).

## Margini sicuri
- Niente testo nei 150 px in alto ne' nei 250 px in basso (y tra 150 e 1670).
- Testo dentro x 90-990, centrato su x = 540: se non ci sta si riduce il corpo, non si sposta.
- Telefono, immagini e titoli sempre centrati su x = 540.
- Barra di avanzamento sottile a y = 1672-1680.
- Impaginazione a fasce, mai testo sopra il telefono: titoli in 150-520, telefono in 545-1490 (`place_phone`), didascalie da 1520. Se serve il display grande si usa solo la meta' alta del telefono sfumata in basso (`phone_top`), mai i tasti sotto le didascalie.

## Cervello e immagine profilo
- Il cervello pixel art 84x48 (profilo, emisfero pieno con circonvoluzioni, cervelletto rigato, tronco, scintille) sta in `cervello.py` ed e' il simbolo del canale: si usa nel gancio e nell'immagine profilo.
- Immagine profilo "3310 Reborn": `canale/profilo.py` genera `canale/profilo_3310reborn.png` (1080x1080) e `canale/profilo_3310reborn_400.png`, telefono intero dentro il cerchio centrale, niente testo.

## Display LCD
- I fotogrammi del display sono veri: `gen_lcd.py` fa girare AurI OS (System + PCHal) e salva `parteN/out/lcd.npz` (84x48 monocromatico).
- Nella cover (`firmware/web/cover.webp`) la finestra LCD e': sinistra 15,24%, alto 26,01%, larghezza 68,46%, altezza 21,01% dell'immagine. Il pannello verde riempie tutta la finestra con angoli arrotondati (raggio 5% della larghezza) e l'immagine 84x48 sta centrata dentro. Mai bande grigie.
- Grafica nuova sul display (es. il cervello del gancio) va disegnata come pixel art 84x48.

## Voce
- Gemini TTS, voce Fenrir: `voce.py parteN --voice Fenrir` (chiave in `GEMINI_API_KEY`, mai su file).
- Prompt di stile (in `voce.py`): "Leggi in italiano come un creator di TikTok entusiasta che racconta un progetto maker: ritmo veloce e dinamico, apertura con sorpresa, pause brevi sui puntini, chiusura con suspense".

## Musica ed effetti
- Solo sintetizzata con numpy in `monta.py`: arpeggio chiptune a onda quadra (132 bpm, giro La min, Fa, Do, Sol), basso a dente di sega, hi-hat a rumore.
- Bip discendenti su tagli e colpi; musica bassa (x0,16) e abbassata sotto la voce.
- Nell'outro l'arpeggio si ferma e chiude con un accordo di La maggiore che sfuma fino a zero.

## Montaggio
- Struttura: gancio (0-3 s, il 3310 con un'immagine forte sul display e la domanda), corpo (una scena per frase, tagli ogni 1-2 s), invito all'interazione (commenti e like con icone disegnate da noi), suspense, outro (logo AurI che si compone dai pixel LCD, URL del repository, "Parte 2 in arrivo").
- Effetti: zoom lento continuo, scossa e flash verde sulle parole forti, pixelatura e glitch RGB nei primi 0,1-0,2 s di ogni taglio.

## Marchi
- "Nokia 3310" si puo' dire e scrivere come descrizione, ma nessun logo NOKIA visibile: usare solo foto e scansioni gia' coperte (`docs/photos/13`, `15`, `16`, `firmware/web/cover.webp`).
- Nessun logo ufficiale GitHub o TikTok: icone (git, fumetto, cuore) disegnate a mano nel codice.
- Repository: github.com/auri-intelligence/auri-3310

## Cartelle
- Radice: strumenti comuni (`voce.py`, `parole.py`, `gen_lcd.py`, `cervello.py`) e questa guida.
- `canale/`: immagine profilo.
- `parteN/`: `copione.txt`, `monta.py`, `copertina.py`, `out/` (voce, tempi, prove, rigenerabili), `girato/` (riprese reali), `pubblicato/` (video finale, file caricato, copertine).
- Video, audio e riprese restano fuori da git.

## Comandi
```
# voce (legge parteN/copione.txt, scrive parteN/out/voce_Fenrir.wav)
tools/video/.venv/Scripts/python tools/video/voce.py parte2 --voice Fenrir
# tempi parola per parola (venv del bridge, modello gia' scaricato)
$env:HF_HOME = "bridge/models/hf"
bridge/.venv/Scripts/python tools/video/parole.py tools/video/parte2/out/voce_Fenrir.wav tools/video/parte2/out/parole.json
# fotogrammi LCD veri
tools/video/.venv/Scripts/python tools/video/gen_lcd.py tools/video/parte2/out/lcd.npz
# anteprime di singoli istanti (in parteN/out/prova/)
tools/video/.venv/Scripts/python tools/video/parte2/monta.py 0 12.5 50
# video completo
tools/video/.venv/Scripts/python tools/video/parte2/monta.py
```
Controllo finale: estrarre almeno 10 fotogrammi (primo fotogramma e outro compresi) e verificare margini, centratura e LCD.
