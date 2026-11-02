#!/usr/bin/env bash
# Retire ThemeTerm du shell et des réglages Cursor. Les fichiers du projet restent en place.
set -euo pipefail
cd "$(dirname "$0")"

python3 configure.py uninstall

echo
echo "✓ Désinstallé. Les nouveaux terminaux Cursor seront normaux."
echo "  Tu peux maintenant supprimer ce dossier : $(pwd)"
