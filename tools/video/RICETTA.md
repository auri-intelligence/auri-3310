# Ricetta per una nuova parte (leggere solo questo, non il codice)

Stile grafico e colori: `STILE.md`. Esempio completo: `parte2/monta.py`.

## 1. Cartella
```
cd tools/video
.venv/Scripts/python nuova_parte.py 3     # crea parte3/ con monta.py, copertina.py, clips.py, traccia.py
```
Riprese dell'utente in `parte3/girato/` (rinominarle con nomi parlanti).

## 2. Copione e voce
- `parte3/copione.txt`. Scrivere "trentatré dieci" per 3310 (a schermo resta "3310"). Mai dire che una funzione è già fatta: si finge di costruirla ora.
- Struttura che funziona (dalle statistiche: si perde gente a 0:01):
  0-3 s gancio forte e titolo pieno dal primo fotogramma; 4-12 s domanda per i commenti; corpo a tagli di 1-2 s;
  commenti veri della parte prima con risposte; "nella prossima parte..."; like + segui. Meme: 3310 indistruttibile e insuperabile.
- Voce (niente accelerazione, all'utente non piace):
```
$env:GEMINI_API_KEY=[Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User')
.venv/Scripts/python voce.py parte3 --voice Fenrir
# accorcia solo i silenzi
ffmpeg -i out/voce_Fenrir.wav -af "silenceremove=stop_periods=-1:stop_duration=0.22:stop_threshold=-42dB:stop_silence=0.16" ...
# tempi parola per parola (dalla radice del repo)
$env:HF_HOME="bridge/models/hf"; bridge/.venv/Scripts/python tools/video/parole.py tools/video/parte3/out/voce_Fenrir.wav tools/video/parte3/out/parole.json
```
- Stampare le parole con i tempi e correggere gli errori di trascrizione in `FIX` / `rules` di `monta.py`.

## 3. Girato reale
- `clips.py`: `CLIPS = {'nome': ('file.mp4', inizio_s, fine_s, durata_finale_s)}` poi `python clips.py` (frame 1080x1920 gia' accelerati in `out/clip/nome/`).
- Fogli di controllo: `ffmpeg -i girato/x.mp4 -vf "fps=1,scale=180:-1,tile=10x3" -frames:v 1 out/prova/foglio.png`.
- Loghi NOKIA in movimento: riquadro sul primo frame in `traccia.py` `LOGHI`, poi `python traccia.py` (controllare `out/prova/traccia_*.png`). Loghi fermi: `static_boxes` in `Video(...)`. Il monitor SAMSUNG e' coperto da solo (tranne i clip in `no_monitor`).

## 4. Montaggio (`monta.py`, motore in `base.py`)
- `v.T('parola', n)`: inizio dell'n-esima occorrenza (maiuscole e punteggiatura ignorate). Attenzione alle parole ripetute (e, il, la, ma, più).
- Una scena e' `def sc_x(t): ... return c, zoom, dx, dy` con `c` RGBA 1080x1920. `SCENES = [(inizio, sc_x), ...]`, l'outro si aggiunge da solo.
- Pronti: `v.real(nome, k, zoom)`, `vignette_bands(c)`, `hud(c, t, 'TESTO')`, `pop_text`, `draw_text`, `stamp`, `arrow`,
  `v.card_in(c, n, t0, t, y)` (screenshot `commenti/n_nome.png`), `phone(bits)`, `place_phone`, `phone_top`, `lcd_img`,
  `lcd_frame('home'|'menu'|'snake'|'assist', i)`, `text_lcd(['RIGA1','RIGA2'])`, `brain_bits(t)`, `PIECES[...]`, `CHIP`, `heart`, `scan_beam`.
  Gancio distruttivo, sensori, TV, Snake, caduta: copiarli da `parte2/monta.py`.
- `HITS` = istanti di flash + scossa + bip. `v.run(SCENES, HITS, shake_until=...)`.
- Anteprime: `../.venv/Scripts/python monta.py 0 1.5 6 ...` poi guardare solo `out/prova/_anteprime.png`.
- Video completo (in background): `../.venv/Scripts/python monta.py` -> `pubblicato/parteN.mp4`.

## 5. Copertina e file da caricare
- `copertina.py` (titolo e telefono nel quadrato centrale y 420-1500, bollino "PARTE N").
- Copia < 10 MB per Claude in Chrome: ffmpeg 2 passate `-b:v 880k`, audio `-b:a 96k` -> `pubblicato/parteN_upload.mp4`.

## 6. Pubblicazione (sempre: testo esatto all'utente e suo ok, una piattaforma alla volta)
- TikTok Studio: carica video; scegliere un hashtag dal menu CANCELLA il testo. Quindi: prima gli hashtag uno alla volta
  (scrivi `#tag`, clic sul suggerimento), poi Ctrl+Home e scrivi la descrizione davanti. Verifica: gli hashtag devono essere span dentro `.mention`.
  Copertina: Modifica copertina > Carica copertina > Salva. Mostra di piu' > "Contenuti generati dall'IA" ON. Non toccare altro.
  Dopo Pubblica resta "in revisione / Solo io" per qualche minuto.
- Instagram: Crea > file > ritaglio "Originale" > Avanti > copertina "Seleziona dal computer" > Avanti > didascalia (hashtag come testo, ok) >
  etichetta IA ON e Facebook OFF verificati con `checked` via JS (a occhio ingannano; il clic su Facebook apre un dialogo: Annulla).
  Esc chiede di eliminare il post: non usarlo.
- Hashtag che funzionano: `#nokia3310 #3310 #techtok #retrotech #maker #tecnologia` (su Instagram senza #techtok). Massimo 6.
- Descrizione: gancio + domanda per i commenti + 👇.
