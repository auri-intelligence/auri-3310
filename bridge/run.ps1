$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$here\.venv\Scripts\python" "$here\auri_bridge.py" @args
