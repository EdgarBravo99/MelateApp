$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

py -3 -m pip install -e ".[desktop,build]"
py -3 -m pytest
py -3 -m PyInstaller --noconfirm --name MelateApp --windowed --collect-all PySide6 melate_app_lab\desktop_app.py

Write-Host "Build listo en dist\MelateApp"
