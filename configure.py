#!/usr/bin/env python3
"""Ajoute ou retire ThemeTerm du shell et des réglages Cursor.

Appelé par install.sh / install.ps1 (`configure.py install`) et les scripts
uninstall (`configure.py uninstall`). Gère macOS, Linux, WSL et Windows (PowerShell).
Chaque fichier modifié est sauvegardé avant (suffixe .bak-asciiwall-DATE).
"""
import json
import os
import platform
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.expanduser("~/.config/asciiwall")
FISH_FILE = os.path.join(os.environ.get("XDG_CONFIG_HOME") or "~/.config", "fish", "conf.d", "asciiwall.fish")
START, END = "# >>> asciiwall >>>", "# <<< asciiwall <<<"
WINDOWS = os.name == "nt"
WSL = not WINDOWS and "microsoft" in platform.release().lower()

UNIX_BLOCK = START + r'''
# À l'ouverture de n'importe quel terminal (une fois par fenêtre/onglet) : écran de choix
# entre le terminal classique et ThemesTerm (hello + fond animé). Placé en tout début pour
# ne pas charger ce fichier deux fois. Code 0 = session ThemesTerm terminée -> on ferme ;
# 3 = terminal classique ; autre (erreur) -> on continue avec un shell normal.
# Désactiver dans une appli : variable ASCIIWALL=0 ; réglages : ~/.config/asciiwall/launcher
if [[ $- == *i* && -t 0 && -t 1 && -z $ASCIITERM && "$TERM" != dumb && "$ASCIIWALL" != 0 &&
      "$ASCIIWALL_TTY" != "$(tty)" ]]; then
  export ASCIIWALL_TTY="$(tty)"
  "@DIR@/.venv/bin/python" "@DIR@/themesterm.py"
  [[ $? == 0 ]] && exit
fi

# Changer le fond animé : `fond` (menu), `fond koi`, `fond 3`, `fond hasard`
fond() {
  if [[ -z $ASCIITERM ]]; then
    echo "fond : disponible seulement dans une session ThemesTerm" >&2
    return 1
  fi
  rm -f "$ASCIITERM/reply"
  printf '%s' "$*" > "$ASCIITERM/cmd.tmp" && mv -f "$ASCIITERM/cmd.tmp" "$ASCIITERM/cmd"
  local i
  for i in {1..20}; do
    if [[ -f "$ASCIITERM/reply" ]]; then
      cat "$ASCIITERM/reply"; rm -f "$ASCIITERM/reply"; return 0
    fi
    sleep 0.05
  done
}
''' + END + "\n"

POWERSHELL_BLOCK = START + r'''
# Terminal de Cursor : PowerShell tourne par-dessus un fond ASCII animé (ASCIIWALL est
# défini dans les réglages Cursor). Si le script échoue, on continue normalement.
if ($env:ASCIIWALL -eq '1' -and $Host.Name -eq 'ConsoleHost' -and
    -not [Console]::IsInputRedirected -and -not [Console]::IsOutputRedirected) {
    Remove-Item Env:ASCIIWALL
    & "@DIR@\.venv\Scripts\python.exe" "@DIR@\asciiterm.py"
    if ($LASTEXITCODE -eq 0) { exit }
}
Remove-Item Env:ASCIIWALL -ErrorAction SilentlyContinue

# Changer le fond animé : `fond` (menu), `fond koi`, `fond 3`, `fond hasard`
function fond {
    if (-not $env:ASCIITERM) {
        Write-Host "fond : disponible seulement dans un terminal Cursor avec fond animé"
        return
    }
    $reply = Join-Path $env:ASCIITERM 'reply'
    $tmp = Join-Path $env:ASCIITERM 'cmd.tmp'
    Remove-Item $reply -ErrorAction SilentlyContinue
    [IO.File]::WriteAllText($tmp, ($args -join ' '))
    Move-Item -Force $tmp (Join-Path $env:ASCIITERM 'cmd')
    for ($i = 0; $i -lt 20; $i++) {
        if (Test-Path $reply) {
            $msg = [IO.File]::ReadAllText($reply)
            Remove-Item $reply
            if ($msg) { Write-Host -NoNewline $msg }
            return
        }
        Start-Sleep -Milliseconds 50
    }
}
''' + END + "\n"


FISH_BLOCK = START + r"""
# Même chose que le bloc bash/zsh, en syntaxe fish (fichier conf.d, retiré à la désinstallation).
# Code 0 = session ThemesTerm terminée -> exec true ferme le terminal (exit ne quitte pas
# fish depuis un fichier de configuration).
if status is-interactive; and test -t 0; and test -t 1; and test -z "$ASCIITERM"
    and test "$TERM" != dumb; and test "$ASCIIWALL" != 0; and test "$ASCIIWALL_TTY" != (tty)
    set -gx ASCIIWALL_TTY (tty)
    "@DIR@/.venv/bin/python" "@DIR@/themesterm.py"
    test $status -eq 0; and exec true
end

# Changer le fond animé : `fond` (menu), `fond koi`, `fond 3`, `fond hasard`
function fond
    if test -z "$ASCIITERM"
        echo "fond : disponible seulement dans une session ThemesTerm" >&2
        return 1
    end
    rm -f "$ASCIITERM/reply"
    printf '%s' "$argv" > "$ASCIITERM/cmd.tmp"; and mv -f "$ASCIITERM/cmd.tmp" "$ASCIITERM/cmd"
    for i in (seq 20)
        if test -f "$ASCIITERM/reply"
            cat "$ASCIITERM/reply"; rm -f "$ASCIITERM/reply"; return 0
        end
        sleep 0.05
    end
end
""" + END + "\n"


# ---------------------------------------------------------------- où écrire

def windows_documents():
    # Dossier Documents réel (souvent redirigé vers OneDrive)
    out = subprocess.check_output(
        ["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('MyDocuments')"])
    return out.decode(errors="replace").strip()


def windows_appdata():
    if WINDOWS:
        return os.environ["APPDATA"]
    # Depuis WSL : on demande le chemin à Windows puis on le traduit en /mnt/c/…
    out = subprocess.check_output(["cmd.exe", "/c", "echo %APPDATA%"], cwd="/mnt/c",
                                  stderr=subprocess.DEVNULL)
    return subprocess.check_output(["wslpath", "-u", out.decode(errors="replace").strip()]).decode().strip()


def shell_files(install=True):
    """Fichiers de démarrage du shell : [(chemin, bloc, encodage)]."""
    if WINDOWS:
        docs = windows_documents()
        block = POWERSHELL_BLOCK.replace("@DIR@", HERE)
        # PowerShell 7 et Windows PowerShell 5.1 ont chacun leur profil ; BOM pour 5.1
        return [(os.path.join(docs, d, "Microsoft.PowerShell_profile.ps1"), block, "utf-8-sig")
                for d in ("PowerShell", "WindowsPowerShell")]
    unix = UNIX_BLOCK.replace("@DIR@", HERE)
    bash_rc = "~/.bash_profile" if platform.system() == "Darwin" else "~/.bashrc"
    files = {
        "zsh": [("~/.zshrc", unix)],
        # Sur Mac, les terminaux ouvrent un shell de connexion qui lit .bash_profile
        "bash": [(bash_rc, unix)],
        "fish": [(FISH_FILE, FISH_BLOCK.replace("@DIR@", HERE))],
    }
    if not install:  # on nettoie partout, même si l'utilisateur a changé de shell depuis
        return [(os.path.expanduser(p), b, "utf-8") for v in files.values() for p, b in v]
    shell = os.path.basename(os.environ.get("SHELL", ""))
    if shell not in files:
        print("! Shell « %s » non pris en charge : l'écran de choix marche avec bash, zsh et fish.\n"
              "  Lancer ThemesTerm à la main : \"%s/.venv/bin/python\" \"%s/themesterm.py\""
              % (shell or "inconnu", HERE, HERE))
        return []
    return [(os.path.expanduser(p), b, "utf-8") for p, b in files[shell]]


def cursor_targets():
    """Réglages Cursor : [(settings.json, clé, variables)].

    Windows : ASCIIWALL=1 déclenche le fond dans les terminaux PowerShell de Cursor.
    macOS / Linux / WSL : l'écran de choix s'affiche dans tous les terminaux, Cursor
    n'a plus besoin de réglage ; ce sont les anciens réglages, à retirer.
    """
    if platform.system() == "Darwin":
        return [(os.path.expanduser("~/Library/Application Support/Cursor/User/settings.json"),
                 "terminal.integrated.env.osx", {"ASCIIWALL": "1"})]
    if WINDOWS:
        path = os.path.join(windows_appdata(), "Cursor", "User", "settings.json")
        return [(path, "terminal.integrated.env.windows", {"ASCIIWALL": "1"})]
    if WSL:
        # ASCIIWALL de env.windows est laissé : il peut servir à l'installation PowerShell
        path = os.path.join(windows_appdata(), "Cursor", "User", "settings.json")
        return [(path, "terminal.integrated.env.windows", {"WSLENV": "ASCIIWALL:${env:WSLENV}"}),
                (path, "terminal.integrated.env.linux", {"ASCIIWALL": "1"})]
    return [(os.path.expanduser("~/.config/Cursor/User/settings.json"),
             "terminal.integrated.env.linux", {"ASCIIWALL": "1"})]


# ---------------------------------------------------------------- modifications

def backup(path):
    if os.path.exists(path):
        dest = path + ".bak-asciiwall-" + time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, dest)
        print("  sauvegarde : " + dest)


def strip_block(text):
    while START in text and END in text:
        a = text.index(START)
        b = text.index(END, a) + len(END)
        text = text[:a] + text[b:].lstrip("\r\n")
    return text


def edit_shell(install):
    for path, block, encoding in shell_files(install):
        old = open(path, encoding="utf-8-sig").read() if os.path.exists(path) else ""
        new = strip_block(old)
        if install:
            new = block + "\n" + new
        if new == old:
            if install:
                print("✓ %s déjà à jour" % path)
            continue
        if not install and not os.path.exists(path):
            continue
        if path == os.path.expanduser(FISH_FILE) and not new.strip():
            os.remove(path)  # fichier créé par nous : on le retire en entier
            print("✓ %s supprimé" % path)
            continue
        backup(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding=encoding) as f:
            f.write(new)
        print("✓ %s %s" % (path, "configuré" if install else "nettoyé"))


def edit_cursor(install):
    for path, key, variables in cursor_targets():
        if not os.path.isdir(os.path.dirname(path)):
            if install:
                print("! Cursor introuvable (%s). Installe Cursor, ouvre-le une fois, puis relance l'installation."
                      % os.path.dirname(path))
            return
        try:
            before = json.load(open(path, encoding="utf-8-sig")) if os.path.exists(path) else {}
        except json.JSONDecodeError:
            # settings.json avec des commentaires : on ne prend pas le risque de le réécrire
            print('! %s contient des commentaires, modifie-le à la main :\n  %s %s dans "%s"'
                  % (path, "ajoute" if install else "retire", json.dumps(variables), key))
            continue
        settings = json.loads(json.dumps(before))  # copie pour comparer à la fin
        env = settings.get(key, {})
        for name, value in variables.items():
            if install:
                env[name] = value
            elif env.get(name) == value:  # ne retire que ce qu'on a mis
                del env[name]
        if env:
            settings[key] = env
        else:
            settings.pop(key, None)
        if settings == before and os.path.exists(path):
            print("✓ réglages Cursor déjà à jour (%s)" % key)
            continue
        backup(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
            f.write("\n")
        print("✓ réglages Cursor %s (%s)" % ("configurés" if install else "nettoyés", key))


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("install", "uninstall"):
        sys.exit("usage : configure.py install|uninstall")
    install = sys.argv[1] == "install"
    edit_shell(install)
    edit_cursor(install and WINDOWS)  # hors Windows : on retire seulement les anciens réglages
    if not install and os.path.isdir(CONFIG_DIR):
        shutil.rmtree(CONFIG_DIR)
        print("✓ fond mémorisé supprimé (%s)" % CONFIG_DIR)


if __name__ == "__main__":
    main()
