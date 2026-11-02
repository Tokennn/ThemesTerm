#!/usr/bin/env bash
# Installe ThemeTerm : fond ASCII animé dans le terminal de Cursor (macOS / Linux).
# Relançable sans risque : il remplace sa propre configuration au lieu de la dupliquer.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))'; then
  echo "Python 3.8 ou plus est nécessaire."
  echo "Sur Mac : xcode-select --install   (ou : brew install python)"
  exit 1
fi

echo "→ Environnement Python (.venv) et dépendance pyte"
python3 -m venv .venv
.venv/bin/pip install -q --disable-pip-version-check -r requirements.txt

echo "→ Configuration du shell et de Cursor"
.venv/bin/python configure.py install

echo
echo "✓ Installé. Ouvre un nouveau terminal dans Cursor."
echo "  Changer de fond : fond   (ou fond koi, fond 3, fond hasard)"
