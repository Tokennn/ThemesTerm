# Retire ThemeTerm des profils PowerShell et des réglages Cursor (Windows).
# Les fichiers du projet restent en place. Lancement : double-clic sur uninstall.cmd
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$python = '.\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }
& $python configure.py uninstall
if ($LASTEXITCODE -ne 0) { throw "désinstallation impossible" }

Write-Host ""
Write-Host "✓ Désinstallé. Les nouveaux terminaux Cursor seront normaux."
Write-Host "  Tu peux maintenant supprimer ce dossier : $PSScriptRoot"
