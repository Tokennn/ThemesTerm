#!/usr/bin/env python3
"""Ajoute ou retire ThemeTerm du shell et des réglages Cursor.

Appelé par install.sh (`configure.py install`) et uninstall.sh (`configure.py uninstall`).
Chaque fichier modifié est sauvegardé avant (suffixe .bak-asciiwall-DATE).
"""
import json
import os
import platform
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.expanduser("~/.config/asciiwall")
START, END = "# >>> asciiwall >>>", "# <<< asciiwall <<<"
BLOCK = START + r'''
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
  printf '\e]7777;%s\a' "$*"
}
''' + END + "\n"


def rc_file():
    shell = os.path.basename(os.environ.get("SHELL", "zsh"))
    if shell == "bash":
        # Sur Mac, les terminaux ouvrent un shell de connexion qui lit .bash_profile
        return os.path.expanduser("~/.bash_profile" if platform.system() == "Darwin" else "~/.bashrc")
    return os.path.expanduser("~/.zshrc")


def cursor_settings():
    if platform.system() == "Darwin":
        return (os.path.expanduser("~/Library/Application Support/Cursor/User/settings.json"),
                "terminal.integrated.env.osx")
    return os.path.expanduser("~/.config/Cursor/User/settings.json"), "terminal.integrated.env.linux"


def backup(path):
    if os.path.exists(path):
        dest = path + ".bak-asciiwall-" + time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, dest)
        print("  sauvegarde : " + dest)


def strip_block(text):
    while START in text and END in text:
        a = text.index(START)
        b = text.index(END, a) + len(END)
        text = text[:a] + text[b:].lstrip("\n")
    return text


def edit_rc(install):
    path = rc_file()
    old = open(path).read() if os.path.exists(path) else ""
    new = strip_block(old)
    if install:
        new = BLOCK.replace("@DIR@", HERE) + "\n" + new
    if new == old:
        print("✓ %s déjà à jour" % path)
        return
    backup(path)
    with open(path, "w") as f:
        f.write(new)
    print("✓ %s %s" % (path, "configuré" if install else "nettoyé"))


def edit_cursor(install):
    path, key = cursor_settings()
    if not os.path.isdir(os.path.dirname(path)):
        if install:
            print("! Cursor introuvable (%s). Installe Cursor, ouvre-le une fois, puis relance install.sh."
                  % os.path.dirname(path))
        return
    try:
        before = json.load(open(path)) if os.path.exists(path) else {}
    except json.JSONDecodeError:
        # settings.json avec des commentaires : on ne prend pas le risque de le réécrire
        action = 'ajoute' if install else 'retire'
        print('! %s contient des commentaires, modifie-le à la main :\n  %s "ASCIIWALL": "1" dans "%s"'
              % (path, action, key))
        return
    settings = json.loads(json.dumps(before))  # copie pour comparer à la fin
    env = settings.get(key, {})
    if install:
        env["ASCIIWALL"] = "1"
    else:
        env.pop("ASCIIWALL", None)
    if env:
        settings[key] = env
    else:
        settings.pop(key, None)
    if settings == before and os.path.exists(path):
        print("✓ réglages Cursor déjà à jour")
        return
    backup(path)
    with open(path, "w") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)
        f.write("\n")
    print("✓ réglages Cursor %s" % ("configurés" if install else "nettoyés"))


def main():
    if platform.system() == "Windows":
        sys.exit("Windows n'est pas encore pris en charge : utilise WSL (voir README).")
    if len(sys.argv) != 2 or sys.argv[1] not in ("install", "uninstall"):
        sys.exit("usage : configure.py install|uninstall")
    install = sys.argv[1] == "install"
    edit_rc(install)
    edit_cursor(install)
    if not install and os.path.isdir(CONFIG_DIR):
        shutil.rmtree(CONFIG_DIR)
        print("✓ fond mémorisé supprimé (%s)" % CONFIG_DIR)


if __name__ == "__main__":
    main()
