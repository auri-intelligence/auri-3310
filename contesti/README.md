# Contesti

Diario di lavoro di AurI-3310. Un file per giorno (`AAAA-MM-GG.md`).
Ogni sessione riparte leggendo l'ultimo file: stato, decisioni prese, cosa resta da fare.

Regole fisse del progetto:

- Scocca, display, tasti, altoparlante, vibrazione e, se passa i test, microfono restano quelli originali del 2000.
- Scheda madre originale e batteria BLC-1 non si toccano: restano reperti.
- Il nome si scrive sempre **AurI**: A e I maiuscole (Artificial Intelligence) in evidenza, "ur" minuscole e in secondo piano.
- Niente marchi o materiale di terzi nel repo: "Nokia 3310" solo come descrizione, logo coperto nelle immagini pubbliche.
- Commit e push a nome Luigi Califano, email `auri-intelligence@users.noreply.github.com`, mai trailer o firme di assistenti.
- Ogni scrittura fuori dal PC (commit, push, GitHub) si fa solo dopo conferma esplicita, una alla volta.
- Nessun dato personale online: niente nomi utente, percorsi del PC, email reali, token o chiavi in file pubblicati. `config.json` di bridge e firmware restano fuori da git.
- La voce appartiene all'assistente centrale AurI (come "Ok Google"/Bixby), non alla console Claude.
- Tutto il lavoro resta sul disco Z: (cartella del progetto). Mai salvare script, texture, video, screenshot o altri file utili nello scratchpad, in %TEMP% o in altre cartelle di C:, che si possono cancellare. File temporanei solo dentro il progetto (es. una cartella `tmp/` esclusa da git).
- Il bridge e i suoi modelli restano circoscritti in `bridge/.venv` e `bridge/models`: cancellando le due cartelle si rimuove tutto.
