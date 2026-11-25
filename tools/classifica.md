# Classifica mondiale dei giochi AurI: opzioni di backend gratuite

Stato: solo progetto. Nessun account o servizio creato. Il telefono e il simulatore funzionano gia' senza: mostrano la classifica locale e la riga "Classifica mondiale in arrivo!".

## Contratto lato AurI (gia' implementato in `firmware/apps/giochi/classifica.py`)

Configurazione in `config.json`:

```json
{ "scores_url": "https://.../score", "scores_key": "segreto-condiviso" }
```

- Invio: `POST scores_url` con corpo JSON `{"gioco": "volo", "nome": "LUIGI", "punti": 42, "firma": "1a2b3c4d"}`
- Lettura: `GET scores_url?gioco=volo`
- Risposta attesa (a entrambe): `{"top": [["ANNA", 120], ["LUIGI", 42], ...]}` (massimo 10 righe)
- `firma` = FNV-1a 32 bit in esadecimale di `gioco|nome|punti|scores_key`. Ferma solo le manomissioni piu' banali: la chiave sta nel firmware (e nel simulatore web e' leggibile da chiunque), quindi il server deve comunque validare.
- Il nome (3-10 caratteri, T9) e' filtrato sul telefono contro parolacce italiane e inglesi di base, con normalizzazione 4->a, 3->e, 0->o, 1->i, @->a, 5->s e lettere ripetute. Il server deve ripetere lo stesso filtro.
- Tutta la rete passa da `hal.request`; nel simulatore web senza `scores_url` non parte nessuna richiesta.

## Opzione 1: Cloudflare Workers + KV (consigliata)

- Piano gratuito (da verificare sul sito al momento della creazione): circa 100.000 richieste Worker al giorno; KV circa 100.000 letture e 1.000 scritture al giorno.
- Pro: un unico endpoint HTTPS con la logica che vogliamo (validazione, limiti, filtro), nessun SDK sul telefono, CORS gestibile per il simulatore web.
- Contro: 1.000 scritture KV al giorno: salvare solo se il punteggio entra nella top 10 (quasi sempre si scrive poco). In alternativa D1 (SQLite) ha limiti gratuiti piu' alti in scrittura.
- Cosa fai tu: crei l'account Cloudflare, un Worker e un namespace KV, imposti il segreto `SCORES_KEY` come variabile cifrata; io poi preparo il codice del Worker (circa 60 righe) da incollare.

## Opzione 2: Firebase Realtime Database (piano Spark gratuito)

- Limiti indicativi: 1 GB di dati, 10 GB al mese di traffico, 100 connessioni simultanee.
- Pro: si scrive con una semplice REST (`PUT/POST .../scores/volo.json`), console comoda.
- Contro: senza funzioni lato server (Cloud Functions richiede il piano a pagamento) la validazione si fa solo con le Security Rules: si possono limitare tipo e intervallo dei campi, lunghezza del nome e un punteggio massimo per gioco, non verificare la firma. La top 10 va calcolata con `orderBy="punti"&limitToLast=10`, quindi la risposta va adattata (piccolo adattatore in `classifica.py`).
- Cosa fai tu: crei il progetto Firebase con il tuo account Google, attivi Realtime Database in modalita' bloccata e incolli le regole che ti preparo.

## Opzione 3: Google Apps Script su un Foglio Google

- Gratuito con un account Google; quote giornaliere generose per un uso hobbistico, ma ogni chiamata e' lenta (1-3 secondi) e c'e' un limite di esecuzioni contemporanee.
- Pro: i punteggi finiscono in un foglio che puoi leggere e ripulire a mano; la `doPost` puo' verificare firma, nome e limiti.
- Contro: lento, redirect HTTP verso `script.googleusercontent.com` (da seguire sull'ESP32), CORS scomodo dal simulatore web.
- Cosa fai tu: crei il foglio, Estensioni > Apps Script, incolli lo script, Pubblica come applicazione web "chiunque". Mi dai l'URL e lo metto in `scores_url`.

(Supabase piano gratuito e' un'altra strada valida: Postgres con 500 MB e API REST, ma i progetti inattivi per una settimana vengono messi in pausa.)

## Rischi e contromisure (valgono per tutte le opzioni)

| Rischio | Contromisura lato server |
|---|---|
| Spam di invii | massimo 1 invio ogni 30 s per IP e per nome; massimo 50 invii al giorno per IP |
| Punteggi falsi | tetto per gioco (es. volo 2000, trefila 200000), firma verificata, rifiuto di punti negativi o non interi |
| Nomi offensivi | stesso filtro del telefono (lista + normalizzazione), piu' una lista nera aggiornabile senza firmware |
| Chiave esposta | la firma e' solo un primo filtro: si puo' ruotare `scores_key`, e se servisse davvero si passa a una sessione di partita (seme casuale dal server, durata minima plausibile) |
| Costi | restare nei piani gratuiti: scrivere solo se il punteggio entra in top 10, cache della top 10 per 60 s |
| Dati personali | solo nickname e punti; nessun identificativo del dispositivo o email |
