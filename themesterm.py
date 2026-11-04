#!/usr/bin/env python3
"""Écran de choix à l'ouverture d'un terminal : terminal classique ou ThemesTerm.

ThemesTerm = animation « hello » (intro.py) puis le shell par-dessus le fond animé
(asciiterm.py). Le fond se choisit directement sur cet écran, avec aperçu en direct.

Touches : ← → choisir · ↑ ↓ changer de fond · Entrée ouvrir · Échap terminal classique
Code de sortie : 3 = terminal classique (le shell continue normalement),
0 = session ThemesTerm terminée (le shell appelant se ferme aussi).

Réglages dans ~/.config/asciiwall/launcher (clé=valeur) :
  default=themesterm    choix présélectionné (mémorise le dernier choix)
  ask=no                ne plus afficher l'écran, ouvrir directement le choix par défaut
"""
import os
import random
import select
import sys
import time

import asciiterm as at
import asciiwall as aw

PREFS = os.path.expanduser("~/.config/asciiwall/launcher")
CLASSIC_EXIT = 3
FPS = 25
YELLOW = at.YELLOW
PANEL, PANEL_ON = (20, 23, 32), (34, 38, 52)
GREY, WHITE, MUTED = (110, 118, 135), (240, 240, 245), (150, 155, 170)


def read_prefs():
    prefs = {"default": "themesterm", "ask": "yes"}
    try:
        for line in open(PREFS, encoding="utf-8"):
            if "=" in line:
                k, v = line.split("=", 1)
                prefs[k.strip().lower()] = v.strip().lower()
    except OSError:
        pass
    return prefs


def save_pref(key, value):
    prefs = read_prefs()
    prefs[key] = value
    try:
        os.makedirs(os.path.dirname(PREFS), exist_ok=True)
        with open(PREFS, "w", encoding="utf-8") as f:
            f.writelines("%s=%s\n" % kv for kv in prefs.items())
    except OSError:
        pass


def put(buf, x, y, text, fg, bg=None):
    h, w = len(buf), len(buf[0]) if buf else 0
    for i, ch in enumerate(text):
        if 0 <= x + i < w and 0 <= y < h:
            buf[y][x + i] = (ch, fg, bg or buf[y][x + i][2])


class Chooser:
    def __init__(self, prefs):
        self.mode = 0 if prefs["default"] == "classic" else 1  # 0 classique, 1 ThemesTerm
        try:
            choice = at.match_choice(open(at.CONFIG).read())
        except OSError:
            choice = None
        self.choice = at.RANDOM if choice is None else choice
        self.idx = random.randrange(len(aw.THEMES)) if self.choice == at.RANDOM else self.choice
        self.theme = aw.THEMES[self.idx]()

    def cycle(self, step):
        self.mode = 1
        self.choice = (self.choice + step) % len(at.CHOICES)
        if self.choice != at.RANDOM:
            self.idx, self.theme = self.choice, aw.THEMES[self.choice]()

    def key(self, data):
        # Renvoie "classic" / "themesterm" quand l'écran doit se fermer, sinon None.
        if data in (b"\x1b[D", b"\x1bOD", b"1"):
            self.mode = 0
        elif data in (b"\x1b[C", b"\x1bOC", b"2"):
            self.mode = 1
        elif data == b"\t":
            self.mode = 1 - self.mode
        elif data in (b"\x1b[A", b"\x1bOA"):
            self.cycle(-1)
        elif data in (b"\x1b[B", b"\x1bOB"):
            self.cycle(1)
        elif data in (b"\r", b"\n"):
            return "themesterm" if self.mode else "classic"
        elif data in (b"\x1b", b"q", b"\x03", b"\x04"):
            return "classic"
        return None

    def frame(self, w, h, t):
        if self.mode:  # aperçu du fond choisi, assombri
            buf = [[(ch, aw.shade(fg, 0.5), aw.shade(bg, 0.5)) for ch, fg, bg in row]
                   for row in aw.render(self.theme, w, h, t)]
        else:
            buf = [[("·" if x % 4 == 0 and y % 2 == 0 else " ", (40, 44, 56), (13, 14, 19))
                    for x in range(w)] for y in range(h)]
        cw = min(32, (w - 6) // 2)
        x0, y0 = (w - 2 * cw - 4) // 2, max(2, h // 2 - 4)
        title = "  Quel terminal ?  "
        put(buf, (w - len(title)) // 2, y0 - 2, title, WHITE, PANEL)
        theme_name = at.CHOICES[self.choice]
        cards = [("Terminal classique", "Ton shell, tel quel", "[1]"),
                 ("ThemesTerm", "Fond animé + hello", "‹ %s ›" % theme_name)]
        for i, (name, desc, extra) in enumerate(cards):
            on = i == self.mode
            border, bg = (YELLOW, PANEL_ON) if on else (GREY, PANEL)
            x = x0 + i * (cw + 4)
            put(buf, x, y0, "╭" + "─" * (cw - 2) + "╮", border, bg)
            for r in range(1, 6):
                put(buf, x, y0 + r, "│" + " " * (cw - 2) + "│", border, bg)
            put(buf, x, y0 + 6, "╰" + "─" * (cw - 2) + "╯", border, bg)
            icon = ("▸ " if i == 0 else "✦ ")
            put(buf, x + 3, y0 + 2, (icon + name)[:cw - 5], YELLOW if on else WHITE, bg)
            put(buf, x + 3, y0 + 3, desc[:cw - 5], MUTED, bg)
            put(buf, x + 3, y0 + 4, extra[:cw - 5], WHITE if on else MUTED, bg)
            if i == 1:  # pastille aux couleurs du fond
                T = aw.THEMES[self.idx]
                for k in range(4):
                    put(buf, x + cw - 7 + k, y0 + 4, " ", WHITE, aw.mix(T.top, T.bottom, k / 3))
        hint = "  ← → choisir   ↑ ↓ fond   ⏎ ouvrir   esc classique  "
        put(buf, (w - len(hint)) // 2, y0 + 8, hint, MUTED, PANEL)
        return buf


def choose(prefs):
    """Affiche l'écran de choix ; renvoie "classic" ou "themesterm"."""
    import termios
    import tty
    w, h = at.term_size()
    if w < 50 or h < 14:  # fenêtre trop petite pour l'écran : choix par défaut
        return prefs["default"]
    chooser = Chooser(prefs)
    saved = termios.tcgetattr(0)
    tty.setcbreak(0)
    sys.stdout.write("\x1b[?1049h\x1b[?25l")
    t0, prev, result = time.time(), None, None
    try:
        while result is None:
            if select.select([0], [], [], 1 / FPS)[0]:
                result = chooser.key(os.read(0, 16))
            size = at.term_size()
            if size != (w, h):
                (w, h), prev = size, None
            buf = chooser.frame(w, h, time.time() - t0)
            sys.stdout.write(at.encode(buf, prev))
            sys.stdout.flush()
            prev = buf
    except KeyboardInterrupt:
        result = "classic"
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
        termios.tcflush(0, termios.TCIFLUSH)
        termios.tcsetattr(0, termios.TCSADRAIN, saved)
    if result == "themesterm":
        chooser_choice = chooser.choice
        try:
            os.makedirs(os.path.dirname(at.CONFIG), exist_ok=True)
            with open(at.CONFIG, "w") as f:
                f.write("hasard" if chooser_choice == at.RANDOM else aw.NAMES[chooser_choice])
        except OSError:
            pass
    return result


def main():
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return CLASSIC_EXIT
    prefs = read_prefs()
    if prefs["ask"] in ("no", "non", "0", "off"):
        result = prefs["default"]
    else:
        result = choose(prefs)
        save_pref("default", result)
    if result != "themesterm":
        return CLASSIC_EXIT
    import intro
    intro.main()
    at.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
