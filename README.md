# ThemeTerm

Des fonds d'écran ASCII animés **derrière ton terminal Cursor** : ton shell habituel
s'affiche par-dessus l'animation, avec la ligne de saisie en jaune.

8 fonds : Claude Code (avec le petit personnage qui court et saute), Cloud Drift,
Honu Lagoon, Koi Pond, Jellyfish, Paper Boats, Fireflies, Moonlit.

## Prérequis

- **macOS** (ou Linux). Windows : voir plus bas.
- **[Cursor](https://cursor.com)**, ouvert au moins une fois.
- **Python 3.8+**. Sur Mac, s'il manque : `xcode-select --install` (ou `brew install python`).

## Installation

```bash
git clone https://github.com/Tokennn/ThemesTerm.git
cd ThemesTerm
./install.sh
```

Le dépôt est privé : il faut avoir été invité dessus. Pas de git ? Sur la page du dépôt,
**Code → Download ZIP**, décompresse-le, puis dans le Terminal : `cd` vers le dossier et `./install.sh`.

Ouvre ensuite **un nouveau terminal dans Cursor**.

> Le dossier doit rester à sa place après l'installation (le shell y lance le script).
> Si tu le déplaces, relance `./install.sh` depuis le nouvel emplacement.

### Ce que fait `install.sh`

1. Crée un environnement Python isolé (`.venv`) et y installe `pyte`.
2. Ajoute un bloc en haut de `~/.zshrc` (ou `~/.bash_profile` si ton shell est bash),
   entre les lignes `# >>> asciiwall >>>` et `# <<< asciiwall <<<`.
3. Ajoute `"ASCIIWALL": "1"` dans `terminal.integrated.env.osx` des réglages Cursor,
   pour que l'animation ne se lance **que** dans les terminaux de Cursor.

Chaque fichier modifié est sauvegardé avant (`…bak-asciiwall-DATE`).
Le script peut être relancé sans risque : il remplace sa configuration au lieu de la dupliquer.

## Utilisation (dans un terminal Cursor)

| Commande | Effet |
|---|---|
| `fond` | Menu des fonds (↑ ↓, Entrée, Échap) avec aperçu en direct |
| `fond koi` / `fond moon` | Choisir par nom (même partiel) |
| `fond 3` | Choisir par numéro |
| `fond hasard` | Un fond au hasard à chaque nouveau terminal |
| `Ctrl + ]` | Fond suivant |
| `exit` | Fermer le terminal, comme d'habitude |

Le fond choisi est mémorisé dans `~/.config/asciiwall/theme`.

Juste l'animation, dans n'importe quel terminal : `python3 asciiwall.py`
(touches `1`–`8`, `n`, `q`).

## Désinstallation

```bash
cd ThemesTerm
./uninstall.sh
```

Retire le bloc du shell, le réglage Cursor et le fond mémorisé. Tu peux ensuite supprimer le dossier.

## Limites

- Pas de défilement à la molette dans l'historique du terminal.
- Les applications plein écran (`vim`, `less`, `htop`) marchent mais peuvent laisser des
  traces en sortant : `clear` pour nettoyer.
- Si l'agent de Cursor a du mal à lancer des commandes, désactive l'animation :
  `"ASCIIWALL": "0"` dans les réglages Cursor.

## Windows 11

Pas encore pris en charge nativement (le script utilise des fonctions propres à macOS/Linux).
En attendant, ça devrait fonctionner avec **WSL** (non testé) : utilise un terminal WSL dans Cursor, puis suis
les étapes Linux ci-dessus depuis WSL (Cursor sous Windows n'enverra pas `ASCIIWALL` à WSL :
ajoute `export ASCIIWALL=1` toi-même avant le bloc asciiwall dans `~/.zshrc` de WSL si besoin).

## Fichiers

| Fichier | Rôle |
|---|---|
| `asciiwall.py` | Les fonds animés (fonctionne aussi seul) |
| `asciiterm.py` | Le shell affiché par-dessus le fond, menu `fond` |
| `configure.py` | Ajoute / retire la configuration (appelé par les scripts) |
| `install.sh` / `uninstall.sh` | Installation / désinstallation |
