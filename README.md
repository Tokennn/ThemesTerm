# ThemesTerm

À l'ouverture de **n'importe quel terminal** (Terminal, iTerm, Warp, VS Code, Cursor…),
un écran te demande ce que tu veux :

- **Terminal classique** : ton shell normal, sans rien de plus ;
- **ThemesTerm** : une animation « hello » en lettres ballon, puis ton shell s'affiche
  **par-dessus un fond ASCII animé**, avec la ligne de saisie en jaune.

Le fond se choisit sur cet écran (aperçu en direct derrière) ou plus tard avec `fond`.
8 fonds : Claude Code (avec le petit personnage qui court et saute), Cloud Drift,
Honu Lagoon, Koi Pond, Jellyfish, Paper Boats, Fireflies, Moonlit.

Fonctionne sur **macOS**, **Linux** et **Windows 11 via WSL**.
Windows 11 avec **PowerShell** : fond animé dans les terminaux Cursor uniquement (voir plus bas).

## Prérequis

- **Python 3.8+** :
  - Mac : `xcode-select --install` (ou `brew install python`)
  - WSL / Ubuntu : `sudo apt install python3 python3-venv`
  - Windows : `winget install Python.Python.3.12`, puis rouvrir le terminal
- Windows PowerShell : **[Cursor](https://cursor.com)**, ouvert au moins une fois.

## Récupérer le projet

Le dépôt est privé : il faut avoir été invité dessus.

```bash
git clone https://github.com/Tokennn/ThemesTerm.git
```

Pas de git ? Sur la page du dépôt, **Code → Download ZIP**, puis décompresse-le.

> Le dossier doit rester à sa place après l'installation (le terminal y lance le script).
> Si tu le déplaces, relance l'installation depuis le nouvel emplacement.

## Installation

### Mac / Linux / WSL

```bash
cd ThemesTerm
./install.sh
```

Sous WSL, clone le projet **dans WSL** (pas dans `/mnt/c/…`).

Ensuite, **ouvre un nouveau terminal** : l'écran de choix apparaît.

### Windows 11 — PowerShell

Double-clic sur **`install.cmd`** dans le dossier (ou, dans PowerShell :
`powershell -ExecutionPolicy Bypass -File install.ps1`), puis ouvre un terminal **dans Cursor**.

Windows PowerShell bloque par défaut les scripts de profil : l'installation propose
d'autoriser les scripts locaux **pour ton compte uniquement**
(`Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`). Réponds `o` pour que l'animation démarre.

### Ce que fait l'installation

1. Crée un environnement Python isolé (`.venv`) avec `pyte` (et `pywinpty` sous Windows).
2. Ajoute un bloc entre `# >>> asciiwall >>>` et `# <<< asciiwall <<<` en haut de :
   - `~/.zshrc` (ou `~/.bash_profile` sur Mac / `~/.bashrc` sur Linux et WSL si ton shell est bash,
     ou `~/.config/fish/conf.d/asciiwall.fish` avec fish ; autres shells : non pris en charge)
   - sous Windows : les deux profils PowerShell (`Documents\PowerShell\…` et `Documents\WindowsPowerShell\…`)
3. Sous Windows uniquement : ajoute `"ASCIIWALL": "1"` dans les réglages Cursor
   (`terminal.integrated.env.windows`). Sur Mac / Linux / WSL, elle retire ce réglage
   s'il vient d'une ancienne version.

Chaque fichier modifié est sauvegardé avant (`…bak-asciiwall-DATE`).
L'installation peut être relancée sans risque : elle remplace sa configuration au lieu de la dupliquer.

## L'écran de choix (Mac / Linux / WSL)

| Touche | Effet |
|---|---|
| `←` `→` (ou `1` / `2`, `Tab`) | Terminal classique / ThemesTerm |
| `↑` `↓` | Changer de fond, avec aperçu en direct |
| `Entrée` | Ouvrir |
| `Échap` | Terminal classique |

Il s'affiche une fois par fenêtre ou onglet (pas dans les sous-shells) et retient ton dernier
choix. Réglages dans `~/.config/asciiwall/launcher` :

```
default=themesterm   # ou classic : le choix présélectionné
ask=no               # ne plus afficher l'écran : ouvrir directement le choix par défaut
```

Pour couper complètement dans une appli précise, définis la variable `ASCIIWALL=0` dans
son environnement (par ex. dans VS Code / Cursor : `"terminal.integrated.env.osx": {"ASCIIWALL": "0"}`).

## Dans une session ThemesTerm

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

## Animation « hello »

Pour la régler, crée `~/.config/asciiwall/intro` :

```
text=SALUT          # le mot affiché (lettres, chiffres, ! ? . -)
color=multi         # une couleur par lettre, ou une seule : #3b5bff
name=Quentin        # prénom de la ligne de bienvenue (défaut : celui du compte)
enabled=no          # pour la désactiver
```

Aperçu à tout moment : `python3 intro.py`. La taille des lettres s'adapte à la largeur
de la fenêtre ; si elle est trop étroite, seule la ligne de bienvenue s'affiche.

## Désinstallation

- Mac / Linux / WSL : `./uninstall.sh`
- Windows : double-clic sur **`uninstall.cmd`**

Retire le bloc du shell, le réglage Cursor et le fond mémorisé. Tu peux ensuite supprimer le dossier.

## Limites

- Dans une session ThemesTerm : pas de défilement à la molette dans l'historique.
- Les applications plein écran (`vim`, `less`, `htop`) marchent mais peuvent laisser des
  traces en sortant : `clear` pour nettoyer.
- Les terminaux ouverts par des outils (agent de Cursor, tâches VS Code…) peuvent afficher
  l'écran de choix s'ils sont interactifs : coupe-le pour ces applis avec `ASCIIWALL=0`.
- Warp a sa propre interface de saisie : l'écran de choix et ThemesTerm s'y lancent comme
  une application plein écran, à tester.
- Sous Windows, l'affichage passe par une couche de plus (ConPTY) : l'animation peut être
  un peu moins fluide que sur Mac.

## Fichiers

| Fichier | Rôle |
|---|---|
| `themesterm.py` | L'écran de choix à l'ouverture du terminal |
| `intro.py` | L'animation « hello » (lettres ballon) |
| `asciiterm.py` | Le shell affiché par-dessus le fond, menu `fond` |
| `asciiwall.py` | Les fonds animés (fonctionne aussi seul) |
| `configure.py` | Ajoute / retire la configuration (appelé par les scripts) |
| `install.sh` / `uninstall.sh` | Installation / désinstallation Mac, Linux, WSL |
| `install.cmd` / `uninstall.cmd` (+ `.ps1`) | Installation / désinstallation Windows PowerShell |
