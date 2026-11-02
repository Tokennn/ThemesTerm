# Installe ThemeTerm sous Windows : fond ASCII animé dans le terminal PowerShell de Cursor.
# Lancement : double-clic sur install.cmd (ou : powershell -ExecutionPolicy Bypass -File install.ps1)
# Relançable sans risque : il remplace sa propre configuration au lieu de la dupliquer.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# Fichiers téléchargés depuis Internet (ZIP) : retire le blocage Windows
Get-ChildItem -Recurse -File | Unblock-File

function Find-Python {
    # py (lanceur officiel) d'abord ; « python » peut n'être qu'un raccourci vers le Store
    foreach ($candidate in @(@('py', '-3'), @('python'), @('python3'))) {
        if (-not (Get-Command $candidate[0] -ErrorAction SilentlyContinue)) { continue }
        $rest = @($candidate | Select-Object -Skip 1)
        & $candidate[0] @rest -c "import sys; sys.exit(sys.version_info < (3, 8))" 2>$null
        if ($LASTEXITCODE -eq 0) { return ,$candidate }
    }
    return $null
}

$python = Find-Python
if (-not $python) {
    Write-Host "Python 3.8 ou plus est nécessaire. Installe-le avec :"
    Write-Host "  winget install Python.Python.3.12"
    Write-Host "puis ferme et rouvre le terminal, et relance l'installation."
    exit 1
}
$rest = @($python | Select-Object -Skip 1)

Write-Host "→ Environnement Python (.venv) et dépendances (pyte, pywinpty)"
& $python[0] @rest -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "création de .venv impossible" }
& .\.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "installation des dépendances impossible" }

Write-Host "→ Configuration de PowerShell et de Cursor"
& .\.venv\Scripts\python.exe configure.py install
if ($LASTEXITCODE -ne 0) { throw "configuration impossible" }

# Windows PowerShell refuse par défaut de lancer les profils (politique « Restricted »)
$policy = Get-ExecutionPolicy
if ($policy -in @('Restricted', 'AllSigned')) {
    Write-Host ""
    Write-Host "PowerShell bloque actuellement les scripts de profil (politique : $policy)."
    Write-Host "Pour que l'animation démarre, il faut autoriser les scripts locaux pour ton compte :"
    Write-Host "  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"
    $answer = Read-Host "Le faire maintenant ? [o/N]"
    if ($answer -match '^[oOyY]') {
        Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
        Write-Host "✓ Scripts locaux autorisés pour ton compte"
    } else {
        Write-Host "! Non modifié : l'animation ne démarrera pas tant que la politique reste $policy."
    }
}

Write-Host ""
Write-Host "✓ Installé. Ouvre un nouveau terminal PowerShell dans Cursor."
Write-Host "  Changer de fond : fond   (ou fond koi, fond 3, fond hasard)"
