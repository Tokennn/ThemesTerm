#!/usr/bin/env python3
"""Ton shell par-dessus un fond ASCII animé, ligne de saisie en jaune.

Le shell tourne dans un pseudo-terminal (pty sous macOS/Linux, ConPTY via pywinpty
sous Windows) ; pyte décode ce qu'il affiche et on le dessine par-dessus l'animation
d'asciiwall.

Changer de fond :
  fond            menu (↑/↓, Entrée, Échap), aperçu en direct
  fond koi        par nom (même partiel), fond 3 par numéro, fond hasard
  Ctrl+]          fond suivant
La fonction shell `fond` dépose sa demande dans le dossier $ASCIITERM et y lit la réponse.
Le choix est mémorisé dans ~/.config/asciiwall/theme.
Quitter : `exit` dans le shell.
"""
import os
import queue
import random
import shutil
import sys
import tempfile
import threading
import time

import pyte

import asciiwall as aw

WINDOWS = os.name == "nt"
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


# ---------------------------------------------------------------- shell et clavier

class UnixShell:
    def __init__(self, rows, cols, env):
        import pty
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.environ.clear()
            os.environ.update(env)
            shell = env.get("SHELL") or "/bin/sh"  # /bin/zsh manque sur beaucoup de Linux
            os.execvp(shell, [shell, "-i"])
        self.resize(rows, cols)

    def read(self):
        return os.read(self.fd, 65536)  # OSError quand le shell s'est terminé

    def write(self, data):
        os.write(self.fd, data)

    def resize(self, rows, cols):
        import fcntl
        import struct
        import termios
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

    def close(self):
        import signal
        try:
            os.kill(self.pid, signal.SIGHUP)  # au cas où on sort sur une erreur
        except ProcessLookupError:
            pass
        os.waitpid(self.pid, 0)


class WindowsShell:
    def __init__(self, rows, cols, env):
        from winpty import PtyProcess
        shell = shutil.which("pwsh") or "powershell.exe"  # PowerShell 7 si installé
        self.proc = PtyProcess.spawn([shell, "-NoLogo"], dimensions=(rows, cols), env=env)

    def read(self):
        try:
            return self.proc.read(65536).encode()
        except EOFError:
            return b""

    def write(self, data):
        self.proc.write(data.decode(errors="replace"))

    def resize(self, rows, cols):
        self.proc.setwinsize(rows, cols)

    def close(self):
        if self.proc.isalive():
            self.proc.terminate(force=True)


class UnixConsole:
    """Clavier en mode brut : chaque touche arrive telle quelle (flèches = séquences ESC)."""

    def __enter__(self):
        import termios
        import tty
        self.saved = termios.tcgetattr(0)
        tty.setraw(0)
        return self

    def read(self):
        return os.read(0, 4096)

    def __exit__(self, *exc):
        import termios
        termios.tcsetattr(0, termios.TCSADRAIN, self.saved)


class WindowsConsole:
    """Console Windows en mode « terminal virtuel » : mêmes séquences ESC que sous Unix."""

    def __enter__(self):
        import ctypes
        self.k32 = ctypes.windll.kernel32
        self.hin, self.hout = self.k32.GetStdHandle(-10), self.k32.GetStdHandle(-11)
        self.modes = []
        for handle in (self.hin, self.hout):
            mode = ctypes.c_uint32()
            self.k32.GetConsoleMode(handle, ctypes.byref(mode))
            self.modes.append(mode.value)
        # Entrée : sans écho ni ligne ni Ctrl+C, + ENABLE_VIRTUAL_TERMINAL_INPUT
        self.k32.SetConsoleMode(self.hin, (self.modes[0] & ~0x7) | 0x200)
        # Sortie : ENABLE_PROCESSED_OUTPUT + ENABLE_VIRTUAL_TERMINAL_PROCESSING
        self.k32.SetConsoleMode(self.hout, self.modes[1] | 0x1 | 0x4)
        self.cp = self.k32.GetConsoleOutputCP(), self.k32.GetConsoleCP()
        self.k32.SetConsoleOutputCP(65001)
        self.k32.SetConsoleCP(65001)
        sys.stdout.reconfigure(encoding="utf-8")
        return self

    def read(self):
        return os.read(0, 4096)

    def __exit__(self, *exc):
        self.k32.SetConsoleMode(self.hin, self.modes[0])
        self.k32.SetConsoleMode(self.hout, self.modes[1])
        self.k32.SetConsoleOutputCP(self.cp[0])
        self.k32.SetConsoleCP(self.cp[1])


# ---------------------------------------------------------------- fond et menu

class Wall:
    """Fond affiché, menu de choix, demandes de la commande `fond`, mémorisation."""

    def __init__(self, ctl):
        self.ctl = ctl  # dossier d'échange avec la fonction shell `fond`
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

    def command(self, arg):
        # Traite `fond …` ; renvoie le texte que la fonction shell doit afficher.
        if not arg.strip():
            self.picker, self.before = self.idx, self.idx
            return ""
        choice = match_choice(arg)
        if choice is None:
            names = ", ".join(n.split()[0].lower() for n in aw.NAMES) + ", hasard"
            return ("fond : « %s » inconnu. Essaie : fond, fond 1-%d, ou %s\n"
                    % (arg.strip(), len(CHOICES), names))
        self.apply(choice)
        return ""

    def poll(self):
        # La fonction shell écrit cmd (via cmd.tmp + renommage) puis attend reply.
        path = os.path.join(self.ctl, "cmd")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8-sig") as f:
                arg = f.read()
            os.remove(path)
        except OSError:
            return
        tmp = os.path.join(self.ctl, "reply.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(self.command(arg))
        os.replace(tmp, os.path.join(self.ctl, "reply"))

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


# ---------------------------------------------------------------- rendu

class Screen(pyte.Screen):
    def __init__(self, cols, rows, shell):
        super().__init__(cols, rows)
        self.shell = shell

    def write_process_input(self, data):
        # Réponses aux questions du shell (position du curseur, type de terminal…)
        self.shell.write(data.encode())


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


def term_size():
    # os.get_terminal_size plutôt que shutil : ignore COLUMNS/LINES éventuellement figés
    try:
        return tuple(os.get_terminal_size(sys.stdout.fileno()))
    except OSError:
        return 100, 30


def pump(events, tag, read):
    # Lit en boucle (shell ou clavier) dans un thread et poste dans la file d'événements.
    while True:
        try:
            data = read()
        except (OSError, EOFError):
            data = b""
        events.put((tag, data))
        if not data:
            return


def main():
    if not sys.stdin.isatty():
        sys.exit("asciiterm doit être lancé dans un terminal")
    cols, rows = term_size()
    ctl = tempfile.mkdtemp(prefix="asciiwall-")
    env = dict(os.environ, ASCIITERM=ctl)
    env.pop("ASCIIWALL", None)  # pas de relance dans le shell interne

    shell = (WindowsShell if WINDOWS else UnixShell)(rows, cols, env)
    screen = Screen(cols, rows, shell)
    stream = pyte.ByteStream(screen)
    wall, t0, prev, next_frame = Wall(ctl), time.time(), None, 0.0
    events = queue.Queue()

    with (WindowsConsole if WINDOWS else UnixConsole)() as console:
        sys.stdout.write("\x1b[?1049h\x1b[?25l")  # écran alternatif + curseur caché
        threading.Thread(target=pump, args=(events, "shell", shell.read), daemon=True).start()
        threading.Thread(target=pump, args=(events, "key", console.read), daemon=True).start()
        try:
            while True:
                try:
                    tag, data = events.get(timeout=max(0, next_frame - time.time()))
                except queue.Empty:
                    tag = None
                if tag == "shell":
                    if not data:  # le shell s'est terminé
                        break
                    stream.feed(data)
                elif tag == "key" and data:
                    if wall.picker is not None:
                        wall.key(data)
                        data = b""
                    if b"\x1d" in data:  # Ctrl+]
                        wall.apply((wall.idx + 1) % len(aw.THEMES))
                        data = data.replace(b"\x1d", b"")
                    if data:
                        shell.write(data)
                wall.poll()
                size = term_size()
                if size != (cols, rows):
                    cols, rows = size
                    screen.resize(rows, cols)
                    shell.resize(rows, cols)
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
            shell.close()
            shutil.rmtree(ctl, ignore_errors=True)


if __name__ == "__main__":
    main()
