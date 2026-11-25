#!/usr/bin/env bash
# Scarica il cervello locale del bridge su Linux o Raspberry: llama.cpp e un modello GGUF.
# Tutto dentro questa cartella (bridge/models/llm): per rimuoverlo, cancella models/llm.
#
#   ./setup_llm.sh              # Qwen3 1.7B Q4_K_M, circa 1,1 GB
#   ./setup_llm.sh piccolo      # Qwen3 0.6B Q4_K_M, circa 0,4 GB (Raspberry Pi 4)
#   ./setup_llm.sh solo-binari  # solo llama.cpp
#
# Niente chiavi, niente account: i modelli sono Apache 2.0 e restano sul tuo disco.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dir="$here/models/llm"
bin="$dir/bin"
mkdir -p "$bin"
scelta="${1:-normale}"

if [ ! -x "$bin/llama-server" ]; then
  case "$(uname -m)" in
    aarch64|arm64) patt="bin-ubuntu-arm64.tar.gz" ;;
    *)             patt="bin-ubuntu-x64.tar.gz" ;;
  esac
  echo "Cerco l'ultima build di llama.cpp ($patt)..."
  url=$(curl -s 'https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=10' \
        | grep -o "https://[^\"]*$patt" | head -1)
  [ -n "$url" ] || { echo "Nessuna build $patt trovata"; exit 1; }
  echo "Scarico $url"
  curl -L --progress-bar -o "$dir/llama.tar.gz" "$url"
  tar -xzf "$dir/llama.tar.gz" -C "$bin" --strip-components=1
  rm "$dir/llama.tar.gz"
  chmod +x "$bin/llama-server" 2>/dev/null || true
  echo "llama.cpp pronto in models/llm/bin"
fi

if [ "$scelta" != "solo-binari" ]; then
  if [ "$scelta" = "piccolo" ]; then
    file="Qwen3-0.6B-Q4_K_M.gguf"; repo="unsloth/Qwen3-0.6B-GGUF"
  else
    file="Qwen3-1.7B-Q4_K_M.gguf"; repo="unsloth/Qwen3-1.7B-GGUF"
  fi
  if [ -f "$dir/$file" ]; then
    echo "$file c'e' gia'."
  else
    echo "Scarico $file da HuggingFace (Apache 2.0)..."
    curl -L --progress-bar -o "$dir/$file" "https://huggingface.co/$repo/resolve/main/$file"
  fi
  if [ -f "$here/config.json" ] && command -v python3 >/dev/null; then
    python3 - "$here/config.json" "models/llm/$file" <<'PY'
import json, sys
path, model = sys.argv[1], sys.argv[2]
with open(path) as f:
    cfg = json.load(f)
cfg['llm_model'] = model
cfg.setdefault('assist_engine', 'auto')
with open(path, 'w') as f:
    json.dump(cfg, f, indent=2)
print('config.json aggiornato: llm_model =', model)
PY
  fi
fi

echo
echo "Fatto. Il bridge avvia llama-server da solo alla prima domanda dell'assistente."
echo "Per provarlo a mano:"
echo "  models/llm/bin/llama-server -m models/llm/<modello>.gguf --host 127.0.0.1 --port 8080 -c 4096"
