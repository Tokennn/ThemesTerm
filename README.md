# ThemeTerm

Des fonds d'écran ASCII animés **derrière ton terminal Cursor** : ton shell habituel
s'affiche par-dessus l'animation, avec la ligne de saisie en jaune.

8 fonds : Claude Code (avec le petit personnage qui court et saute), Cloud Drift,
Honu Lagoon, Koi Pond, Jellyfish, Paper Boats, Fireflies, Moonlit.

Fonctionne sur **macOS**, **Linux**, **Windows 11 (PowerShell)** et **Windows 11 (WSL)**.

## Prérequis

- **[Cursor](https://cursor.com)**, ouvert au moins une fois.
- **Python 3.8+** :
  - Mac : `xcode-select --install` (ou `brew install python`)
  - Windows : `winget install Python.Python.3.12`, puis rouvrir le terminal
  - WSL / Ubuntu : `sudo apt install python3 python3-venv`

## Récupérer le projet

Le dépôt est privé : il faut avoir été invité dessus.

```bash
git clone https://github.com/Tokennn/ThemesTerm.git
```

Pas de git ? Sur la page du dépôt, **Code → Download ZIP**, puis décompresse-le.

> Le dossier doit rester à sa place après l'installation (le terminal y lance le script).
> Si tu le déplaces, relance l'installation depuis le nouvel emplacement.

## Installation

### Mac / Linux

```bash
cd ThemesTerm
./install.sh
```

### Windows 11 — PowerShell

Double-clic sur **`install.cmd`** dans le dossier (ou, dans PowerShell :
`powershell -ExecutionPolicy Bypass -File install.ps1`).

Windows PowerShell bloque par défaut les scripts de profil : l'installation propose
d'autoriser les scripts locaux **pour ton compte uniquement**
(`Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`). Réponds `o` pour que l'animation démarre.

### Windows 11 — WSL

Dans un terminal **WSL** (Ubuntu…), clone le projet **dans WSL** (pas dans `/mnt/c/…`), puis :

```bash
cd ThemesTerm
./install.sh
```

Le script détecte WSL et configure Cursor côté Windows pour que la variable `ASCIIWALL`
arrive jusque dans WSL (`WSLENV`).

Ensuite, partout : **ouvre un nouveau terminal dans Cursor**.

### Ce que fait l'installation

1. Crée un environnement Python isolé (`.venv`) avec `pyte` (et `pywinpty` sous Windows).
2. Ajoute un bloc entre `# >>> asciiwall >>>` et `# <<< asciiwall <<<` en haut de :
   - `~/.zshrc` (ou `~/.bash_profile` sur Mac / `~/.bashrc` sur Linux et WSL si ton shell est bash)
   - sous Windows : les deux profils PowerShell (`Documents\PowerShell\…` et `Documents\WindowsPowerShell\…`)
3. Ajoute `"ASCIIWALL": "1"` dans les réglages Cursor (`terminal.integrated.env.osx`,
   `.linux` ou `.windows`), pour que l'animation ne se lance **que** dans les terminaux de Cursor.

Chaque fichier modifié est sauvegardé avant (`…bak-asciiwall-DATE`).
L'installation peut être relancée sans risque : elle remplace sa configuration au lieu de la dupliquer.

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

Juste l'animation, dans n'importe quel terminal : `python3 asciiwall.py` (Windows : `py asciiwall.py`),
touches `1`–`8`, `n`, `q`.

## Désinstallation

- Mac / Linux / WSL : `./uninstall.sh`
- Windows : double-clic sur **`uninstall.cmd`**

Retire le bloc du shell, le réglage Cursor et le fond mémorisé. Tu peux ensuite supprimer le dossier.
Si tu as installé à la fois la version PowerShell et la version WSL, désinstaller l'une retire aussi
le réglage Cursor commun : relance l'installation de l'autre.

## Limites

- Pas de défilement à la molette dans l'historique du terminal.
- Les applications plein écran (`vim`, `less`, `htop`) marchent mais peuvent laisser des
  traces en sortant : `clear` pour nettoyer.
- Si l'agent de Cursor a du mal à lancer des commandes, désactive l'animation :
  `"ASCIIWALL": "0"` dans les réglages Cursor.
- Sous Windows, l'affichage passe par une couche de plus (ConPTY) : l'animation peut être
  un peu moins fluide que sur Mac.

## Fichiers

| Fichier | Rôle |
|---|---|
| `asciiwall.py` | Les fonds animés (fonctionne aussi seul) |
| `asciiterm.py` | Le shell affiché par-dessus le fond, menu `fond` |
| `configure.py` | Ajoute / retire la configuration (appelé par les scripts) |
| `install.sh` / `uninstall.sh` | Installation / désinstallation Mac, Linux, WSL |
| `install.cmd` / `uninstall.cmd` (+ `.ps1`) | Installation / désinstallation Windows PowerShell |
