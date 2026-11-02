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
START, END = "# >>> asciiwall >>>", "# <<< asciiwall <<<"
WINDOWS = os.name == "nt"
WSL = not WINDOWS and "microsoft" in platform.release().lower()

UNIX_BLOCK = START + r'''
# Terminal de Cursor : le shell tourne par-dessus un fond ASCII animé (ASCIIWALL est
# défini dans les réglages Cursor). Placé en tout début pour ne pas charger ce fichier
# deux fois. Si le script échoue, on continue avec un shell normal.
if [[ "$ASCIIWALL" == 1 && $- == *i* && -t 0 && -t 1 ]]; then
  unset ASCIIWALL
  "@DIR@/.venv/bin/python" "@DIR@/asciiterm.py" && exit
fi
unset ASCIIWALL

# Changer le fond animé : `fond` (menu), `fond koi`, `fond 3`, `fond hasard`
fond() {
  if [[ -z $ASCIITERM ]]; then
    echo "fond : disponible seulement dans un terminal Cursor avec fond animé" >&2
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


def shell_files():
    """Fichiers de démarrage du shell : [(chemin, bloc, encodage)]."""
    if WINDOWS:
        docs = windows_documents()
        block = POWERSHELL_BLOCK.replace("@DIR@", HERE)
        # PowerShell 7 et Windows PowerShell 5.1 ont chacun leur profil ; BOM pour 5.1
        return [(os.path.join(docs, d, "Microsoft.PowerShell_profile.ps1"), block, "utf-8-sig")
                for d in ("PowerShell", "WindowsPowerShell")]
    shell = os.path.basename(os.environ.get("SHELL", "zsh"))
    if shell == "bash":
        # Sur Mac, les terminaux ouvrent un shell de connexion qui lit .bash_profile
        rc = "~/.bash_profile" if platform.system() == "Darwin" else "~/.bashrc"
    else:
        rc = "~/.zshrc"
    return [(os.path.expanduser(rc), UNIX_BLOCK.replace("@DIR@", HERE), "utf-8")]


def cursor_targets():
    """Réglages Cursor à modifier : [(settings.json, clé, variables)]."""
    if platform.system() == "Darwin":
        return [(os.path.expanduser("~/Library/Application Support/Cursor/User/settings.json"),
                 "terminal.integrated.env.osx", {"ASCIIWALL": "1"})]
    if WINDOWS or WSL:
        path = os.path.join(windows_appdata(), "Cursor", "User", "settings.json")
        targets = [(path, "terminal.integrated.env.windows", {"ASCIIWALL": "1"})]
        if WSL:
            # WSLENV transmet ASCIIWALL de Windows au terminal WSL ; env.linux sert
            # quand Cursor est ouvert « dans » WSL (fenêtre distante)
            targets = [(path, "terminal.integrated.env.windows",
                        {"ASCIIWALL": "1", "WSLENV": "ASCIIWALL:${env:WSLENV}"}),
                       (path, "terminal.integrated.env.linux", {"ASCIIWALL": "1"})]
        return targets
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
    for path, block, encoding in shell_files():
        old = open(path, encoding="utf-8-sig").read() if os.path.exists(path) else ""
        new = strip_block(old)
        if install:
            new = block + "\n" + new
        if new == old:
            print("✓ %s déjà à jour" % path)
            continue
        if not install and not os.path.exists(path):
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
    edit_cursor(install)
    if not install and os.path.isdir(CONFIG_DIR):
        shutil.rmtree(CONFIG_DIR)
        print("✓ fond mémorisé supprimé (%s)" % CONFIG_DIR)


if __name__ == "__main__":
    main()
