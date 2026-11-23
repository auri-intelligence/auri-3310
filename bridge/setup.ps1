# Crea l'ambiente del bridge dentro questa cartella. Per rimuovere tutto: cancella .venv e models.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
python -m venv "$here\.venv"
& "$here\.venv\Scripts\python" -m pip install -r "$here\requirements.txt"
& "$here\.venv\Scripts\python" -c "from huggingface_hub import hf_hub_download as d; [d('rhasspy/piper-voices', f, local_dir=r'$here\models') for f in ('it/it_IT/paola/medium/it_IT-paola-medium.onnx', 'it/it_IT/paola/medium/it_IT-paola-medium.onnx.json')]"
if (-not (Test-Path "$here\config.json")) { Copy-Item "$here\config.example.json" "$here\config.json" }
