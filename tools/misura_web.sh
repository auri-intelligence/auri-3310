#!/bin/sh
# Misura le prestazioni del simulatore in Chrome headless, in tempo reale.
# Serve serve.py acceso sulla porta 8000 con l'uscita in un file: sh tools/misura_web.sh <log di serve.py>
# Per ogni scenario stampa l'ultima riga: app in cima, ms medi di s.step(), picco, ms del canvas.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$1"
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
PROF="$ROOT/tmp/chrome-misura"
mkdir -p "$PROF"
FLAP="navi,pausa:300"
for i in $(seq 1 40); do FLAP="$FLAP,5,pausa:250"; done
misura() {
  nome="$1"; tasti="$2"; secondi="$3"
  : > "$LOG.tmp"
  n0=$(wc -l < "$LOG")
  timeout "$secondi" "$CHROME" --headless=new --user-data-dir="$PROF" --window-size=1000,1200 \
    "http://127.0.0.1:8000/web/#misura&tasti=$tasti" >/dev/null 2>&1
  echo "$nome: $(tail -n +$((n0 + 1)) "$LOG" | grep -o '__misura?[^ ]*' | tail -1)"
}
misura home  "power:1700,pausa:9000,pausa:4000" 25
misura menu  "power:1700,pausa:9000,navi,down,down,down,down,down,down,up,up,up,pausa:1500" 28
misura gioco "power:1700,pausa:9000,navi,down,down,down,navi,pausa:800,navi,pausa:800,$FLAP" 40
