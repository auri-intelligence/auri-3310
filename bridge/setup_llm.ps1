# Scarica il cervello locale del bridge: llama.cpp (binari ufficiali) e un modello GGUF.
# Tutto dentro questa cartella (bridge\models\llm): per rimuoverlo, cancella models\llm.
#
#   .\setup_llm.ps1                 # Qwen3 1.7B Q4_K_M, circa 1,1 GB
#   .\setup_llm.ps1 -Modello piccolo  # Qwen3 0.6B Q4_K_M, circa 0,4 GB (PC lenti)
#   .\setup_llm.ps1 -SoloBinari     # solo llama.cpp, il modello ce l'hai gia'
#
# Niente chiavi, niente account: i modelli sono Apache 2.0 e restano sul tuo disco.
param(
  [ValidateSet('normale', 'piccolo')][string]$Modello = 'normale',
  [switch]$SoloBinari
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dir = Join-Path $here 'models\llm'
$bin = Join-Path $dir 'bin'
New-Item -ItemType Directory -Force -Path $dir, $bin | Out-Null

# --- llama.cpp: build CPU ufficiale per Windows -----------------------------
if (-not (Test-Path (Join-Path $bin 'llama-server.exe'))) {
  Write-Host 'Cerco l ultima build di llama.cpp...'
  $arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'win-cpu-arm64' } else { 'win-cpu-x64' }
  $rel = $null
  foreach ($r in (Invoke-RestMethod 'https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=10' -Headers @{ 'User-Agent' = 'auri-3310' })) {
    if ($r.assets | Where-Object { $_.name -like "*bin-$arch.zip" }) { $rel = $r; break }
  }
  if (-not $rel) { throw "Nessuna build $arch trovata nelle ultime release di llama.cpp" }
  $asset = $rel.assets | Where-Object { $_.name -like "*bin-$arch.zip" } | Select-Object -First 1
  $zip = Join-Path $dir $asset.name
  Write-Host "Scarico $($asset.name) ($([math]::Round($asset.size / 1MB)) MB)..."
  Invoke-WebRequest $asset.browser_download_url -OutFile $zip
  Expand-Archive $zip -DestinationPath $bin -Force
  Remove-Item $zip
  # alcune build mettono i file in una sottocartella: si appiattisce
  if (-not (Test-Path (Join-Path $bin 'llama-server.exe'))) {
    Get-ChildItem $bin -Recurse -File | Move-Item -Destination $bin -Force -ErrorAction SilentlyContinue
  }
  Write-Host "llama.cpp $($rel.tag_name) pronto in models\llm\bin"
}

# --- modello GGUF -----------------------------------------------------------
if (-not $SoloBinari) {
  $file = if ($Modello -eq 'piccolo') { 'Qwen3-0.6B-Q4_K_M.gguf' } else { 'Qwen3-1.7B-Q4_K_M.gguf' }
  $repo = if ($Modello -eq 'piccolo') { 'unsloth/Qwen3-0.6B-GGUF' } else { 'unsloth/Qwen3-1.7B-GGUF' }
  $out = Join-Path $dir $file
  if ((Test-Path $out) -and (Get-Item $out).Length -gt 100MB) {
    Write-Host "$file c e' gia' ($([math]::Round((Get-Item $out).Length / 1MB)) MB)."
  } else {
    Write-Host "Scarico $file da HuggingFace (Apache 2.0): circa 1 GB, ci vuole qualche minuto..."
    # curl scrive l avanzamento su stderr e PowerShell lo prenderebbe per un errore: qui va in silenzio
    $prima = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & curl.exe -L --no-progress-meter -o $out "https://huggingface.co/$repo/resolve/main/$file"
    $esito = $LASTEXITCODE
    $ErrorActionPreference = $prima
    if ($esito -ne 0 -or -not (Test-Path $out) -or (Get-Item $out).Length -lt 100MB) {
      if (Test-Path $out) { Remove-Item $out }
      throw "scaricamento di $file non riuscito (curl $esito)"
    }
    Write-Host "$file scaricato: $([math]::Round((Get-Item $out).Length / 1MB)) MB"
  }
  # scrive il percorso nel config del bridge, se c'e'
  $cfgPath = Join-Path $here 'config.json'
  if (Test-Path $cfgPath) {
    $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
    # i config piu' vecchi non hanno queste voci: si aggiungono, non si sovrascrivono
    foreach ($v in @(@{n='llm_model'; v="models/llm/$file"}, @{n='assist_engine'; v='auto'},
                     @{n='llm_autostart'; v=$true}, @{n='llm_url'; v='http://127.0.0.1:8080'})) {
      if ($cfg.PSObject.Properties.Name -contains $v.n) {
        if ($v.n -eq 'llm_model') { $cfg.llm_model = $v.v }
      } else {
        $cfg | Add-Member -NotePropertyName $v.n -NotePropertyValue $v.v
      }
    }
    $cfg | ConvertTo-Json -Depth 8 | Set-Content $cfgPath -Encoding utf8
    Write-Host "config.json aggiornato: llm_model = models/llm/$file"
  }
}

Write-Host ''
Write-Host 'Fatto. Il bridge avvia llama-server da solo alla prima domanda dell assistente.'
Write-Host 'Per provarlo a mano:'
Write-Host "  models\llm\bin\llama-server.exe -m models\llm\<modello>.gguf --host 127.0.0.1 --port 8080 -c 4096"
