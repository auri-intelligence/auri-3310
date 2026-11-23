#!/bin/sh
# Crea l'ambiente del bridge dentro questa cartella (Raspberry Pi / Linux). Per rimuovere tutto: rm -rf .venv models
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c "from huggingface_hub import hf_hub_download as d; [d('rhasspy/piper-voices', f, local_dir='models') for f in ('it/it_IT/paola/medium/it_IT-paola-medium.onnx', 'it/it_IT/paola/medium/it_IT-paola-medium.onnx.json')]"
[ -f config.json ] || cp config.example.json config.json
