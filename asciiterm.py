#!/usr/bin/env python3
"""Ton shell par-dessus un fond ASCII animé, ligne de saisie en jaune.

Le shell tourne dans un pseudo-terminal ; pyte décode ce qu'il affiche et on
le dessine par-dessus l'animation d'asciiwall.

Changer de fond :
  fond            menu (↑/↓, Entrée, Échap), aperçu en direct
  fond koi        par nom (même partiel), fond 3 par numéro, fond hasard
  Ctrl+]          fond suivant
Le choix est mémorisé dans ~/.config/asciiwall/theme.
Quitter : `exit` ou Ctrl+D dans le shell.
Nécessite pyte : .venv/bin/pip install pyte
"""
import fcntl
import os
import pty
import random
import re
import select
import shutil
import signal
import struct
import sys
import termios
import time
import tty

import pyte

import asciiwall as aw

FPS = 25
YELLOW = (255, 214, 10)
DEFAULT_FG = (235, 235, 235)
DARK_FG = (25, 30, 45)  # texte sur fond clair (nuages, ciel)
PALETTE = {
    "black": (60, 60, 60), "red": (235, 90, 80), "green": (120, 210, 100),
    "brown": (230, 190, 70), "blue": (100, 150, 240), "magenta": (210, 120, 210),
    "cyan": (90, 210, 220), "white": (220, 220, 220),
}
PALETTE.update({"bright" + k: aw.shade(v, 1.2) for k, v in list(PALETTE.items())})

CONFIG = os.path.expanduser("~/.config/asciiwall/theme")
CHOICES = aw.NAMES + ["Au hasard"]
RANDOM = len(aw.NAMES)  # index de « Au hasard » dans CHOICES
# Séquence envoyée par la fonction shell `fond` : ESC ] 7777 ; argument BEL
FOND_CMD = re.compile(rb"\x1b\]7777;([^\x07]*)\x07")
UP = (b"\x1b[A", b"\x1bOA", b"\x1b[D", b"\x1bOD")
DOWN = (b"\x1b[B", b"\x1bOB", b"\x1b[C", b"\x1bOC")


def color(name, default):
    # pyte donne soit un nom ANSI, soit un hex "rrggbb" (256 couleurs / truecolor)
    if name == "default":
        return default
    if name in PALETTE:
        return PALETTE[name]
    try:
        return tuple(int(name[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default


def luminance(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def match_choice(arg):
    # "3", "koi", "moon", "hasard" -> index dans CHOICES, None si inconnu
    a = arg.strip().lower().replace(" ", "")
    if a.isdigit() and 1 <= int(a) <= len(CHOICES):
        return int(a) - 1
    if a in ("random", "hasard"):
        return RANDOM
    for i, name in enumerate(CHOICES):
        if a and a in name.lower().replace(" ", ""):
            return i
    return None


class Wall:
    """Fond affiché, menu de choix et mémorisation du choix."""

    def __init__(self):
        try:
            choice = match_choice(open(CONFIG).read())
        except OSError:
            choice = None
        self.idx = random.randrange(len(aw.THEMES)) if choice in (None, RANDOM) else choice
        self.theme = aw.THEMES[self.idx]()
        self.picker = None  # ligne sélectionnée quand le menu est ouvert
        self.before = self.idx  # fond à remettre si on annule le menu

    def show(self, idx):
        if idx != self.idx:
            self.idx, self.theme = idx, aw.THEMES[idx]()

    def apply(self, choice):
        self.show(random.randrange(len(aw.THEMES)) if choice == RANDOM else choice)
        try:
            os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
            with open(CONFIG, "w") as f:
                f.write("hasard" if choice == RANDOM else aw.NAMES[choice])
        except OSError:
            pass

    def command(self, m):
        # Appelé pour chaque `fond …` vu dans la sortie du shell ; renvoie le texte à afficher.
        arg = m.group(1).decode(errors="replace")
        if not arg.strip():
            self.picker, self.before = self.idx, self.idx
            return b""
        choice = match_choice(arg)
        if choice is None:
            names = ", ".join(n.split()[0].lower() for n in aw.NAMES) + ", hasard"
            return ("fond : « %s » inconnu. Essaie : fond, fond 1-%d, ou %s\r\n"
                    % (arg, len(CHOICES), names)).encode()
        self.apply(choice)
        return b""

    def key(self, data):
        # Touches pendant que le menu est ouvert (elles ne vont pas au shell).
        n = len(CHOICES)
        if data in UP:
            self.picker = (self.picker - 1) % n
        elif data in DOWN:
            self.picker = (self.picker + 1) % n
        elif data.isdigit() and 1 <= int(data) <= n:
            self.picker = int(data) - 1
        elif data in (b"\r", b"\n"):
            self.apply(self.picker)
            self.picker = None
            return
        elif data in (b"\x1b", b"q", b"\x03"):
            self.show(self.before)
            self.picker = None
            return
        if self.picker != RANDOM:
            self.show(self.picker)  # aperçu en direct

    def draw_picker(self, buf, w, h):
        bw, bh = 36, len(CHOICES) + 3
        x0, y0 = max(0, (w - bw) // 2), max(0, (h - bh) // 2)
        panel, border = (18, 22, 30), (120, 130, 150)

        def put(x, y, text, fg, bg):
            for i, ch in enumerate(text):
                if 0 <= x + i < w and 0 <= y < h:
                    buf[y][x + i] = (ch, fg, bg)

        put(x0, y0, "╭─ Fond d'écran " + "─" * (bw - 17) + "╮", border, panel)
        for i, name in enumerate(CHOICES):
            y, on = y0 + 1 + i, i == self.picker
            fg, bg = ((20, 20, 20), YELLOW) if on else ((225, 225, 225), panel)
            put(x0, y, "│", border, panel)
            put(x0 + 1, y, ((" › " if on else "   ") + "%d  %s" % (i + 1, name)).ljust(27), fg, bg)
            for k in range(6):  # pastille aux couleurs du thème
                T = aw.THEMES[i] if i < RANDOM else aw.THEMES[k]
                put(x0 + 28 + k, y, " ", fg, aw.mix(T.top, T.bottom, k / 5) if i < RANDOM else T.top)
            put(x0 + 34, y, " ", fg, bg)
            put(x0 + 35, y, "│", border, panel)
        y = y0 + 1 + len(CHOICES)
        put(x0, y, "│" + "↑↓ choisir · ⏎ appliquer · esc".center(bw - 2) + "│", border, panel)
        put(x0, y + 1, "╰" + "─" * (bw - 2) + "╯", border, panel)


class Screen(pyte.Screen):
    def __init__(self, cols, rows, fd):
        super().__init__(cols, rows)
        self.fd = fd

    def write_process_input(self, data):
        # Réponses aux questions du shell (position du curseur, type de terminal…)
        os.write(self.fd, data.encode())


def set_size(fd, rows, cols):
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def compose(theme, screen, w, h, t):
    buf = aw.render(theme, w, h, t)
    cx, cy = screen.cursor.x, screen.cursor.y
    for y in range(h):
        line = screen.buffer[y]
        for x in range(w):
            ch, fg, bg = buf[y][x]
            fg, bg = aw.shade(fg, theme.dim), aw.shade(bg, theme.dim)
            c = line[x]
            if c.bg != "default":
                bg = color(c.bg, bg)
            if c.data != " ":  # "" = 2e moitié d'un caractère large
                ch = c.data
                fg = YELLOW if y == cy else color(c.fg, DEFAULT_FG)
                if c.bg == "default" and luminance(bg) > 170:
                    fg = DARK_FG  # sinon blanc/jaune sur blanc = illisible
                if c.reverse:
                    fg, bg = bg, fg
            if y == cy:
                bg = aw.mix(bg, YELLOW, 0.22)  # bandeau jaune sur la ligne de saisie
            buf[y][x] = (ch, fg, bg)
    if pyte.modes.DECTCEM in screen.mode and cy < h and cx < w:
        ch = buf[cy][cx][0]
        buf[cy][cx] = (ch if ch.strip() else " ", (20, 20, 20), YELLOW)
    return buf


def encode(buf, prev):
    # Ne renvoie que les lignes qui ont changé depuis l'image précédente.
    out, last = [], None
    for y, row in enumerate(buf):
        if prev is not None and y < len(prev) and prev[y] == row:
            continue
        out.append("\x1b[%d;1H" % (y + 1))
        for ch, fg, bg in row:
            if (fg, bg) != last:
                out.append("\x1b[38;2;%d;%d;%dm\x1b[48;2;%d;%d;%dm" % (*fg, *bg))
                last = (fg, bg)
            out.append(ch)
    return "".join(out)


def main():
    if not sys.stdin.isatty():
        sys.exit("asciiterm doit être lancé dans un terminal")
    cols, rows = shutil.get_terminal_size()

    pid, fd = pty.fork()
    if pid == 0:
        os.environ.pop("ASCIIWALL", None)  # pas de relance dans le shell interne
        os.environ["ASCIITERM"] = "1"
        shell = os.environ.get("SHELL", "/bin/zsh")
        os.execvp(shell, [shell, "-i"])

    set_size(fd, rows, cols)
    screen = Screen(cols, rows, fd)
    stream = pyte.ByteStream(screen)
    resized = [False]
    signal.signal(signal.SIGWINCH, lambda *_: resized.__setitem__(0, True))

    wall, t0, prev, next_frame = Wall(), time.time(), None, 0.0
    saved = termios.tcgetattr(0)
    tty.setraw(0)
    sys.stdout.write("\x1b[?1049h\x1b[?25l")
    try:
        while True:
            r, _, _ = select.select([0, fd], [], [], max(0, next_frame - time.time()))
            if 0 in r:
                data = os.read(0, 4096)
                if wall.picker is not None:
                    wall.key(data)
                    data = b""
                if b"\x1d" in data:  # Ctrl+]
                    wall.apply((wall.idx + 1) % len(aw.THEMES))
                    data = data.replace(b"\x1d", b"")
                if data:
                    os.write(fd, data)
            if fd in r:
                try:
                    data = os.read(fd, 65536)
                except OSError:  # le shell s'est terminé
                    break
                if not data:
                    break
                stream.feed(FOND_CMD.sub(wall.command, data))
            if resized[0]:
                resized[0] = False
                cols, rows = shutil.get_terminal_size()
                screen.resize(rows, cols)
                set_size(fd, rows, cols)
                prev = None
            if time.time() >= next_frame:
                buf = compose(wall.theme, screen, cols, rows, time.time() - t0)
                if wall.picker is not None:
                    wall.draw_picker(buf, cols, rows)
                sys.stdout.write(encode(buf, prev))
                sys.stdout.flush()
                prev, next_frame = buf, time.time() + 1 / FPS
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
        termios.tcsetattr(0, termios.TCSADRAIN, saved)
        try:
            os.kill(pid, signal.SIGHUP)  # au cas où on sort sur une erreur
        except ProcessLookupError:
            pass
        os.waitpid(pid, 0)


if __name__ == "__main__":
    main()
