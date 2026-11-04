#!/usr/bin/env python3
"""Animation d'entrée à l'ouverture du terminal : lettres « ballon » élastiques.

Les lettres arrivent une par une avec un rebond de ressort, gigotent, puis se
dégonflent et laissent une ligne de bienvenue. Une touche passe l'animation.

Réglages (facultatifs) dans ~/.config/asciiwall/intro, une ligne clé=valeur :
  text=HELLO            mot affiché (lettres, chiffres, ! ? . -)
  color=multi           multi (une couleur par lettre) ou #3b5bff
  name=Quentin          prénom de la ligne de bienvenue (défaut : celui du compte)
  enabled=no            désactive l'animation
Aperçu : python3 intro.py
"""
import datetime
import math
import os
import platform
import pwd
import select
import sys
import time
import unicodedata

FPS = 40
LIGHT = (-0.5, -0.62, 0.62)  # lumière en haut à gauche (y vers le bas)
CARTOON = ["#3b5bff", "#ff4d8d", "#ffb703", "#2ec4b6", "#ff7a3d", "#8b5cf6"]
SHADOW = (28, 28, 38)
CONFIG = os.path.expanduser("~/.config/asciiwall/intro")

# Police 5×7, agrandie puis « gonflée » à l'affichage
FONT = {
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
    "C": [" ### ", "#   #", "#    ", "#    ", "#    ", "#   #", " ### "],
    "D": ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    "F": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    "G": [" ### ", "#   #", "#    ", "# ###", "#   #", "#   #", " ####"],
    "H": ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "I": [" ### ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "J": ["  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "],
    "K": ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
    "R": ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
    "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
    "W": ["#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"],
    "X": ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    "Y": ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "],
    "Z": ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
    "0": [" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    "3": ["#### ", "    #", "    #", " ### ", "    #", "    #", "#### "],
    "4": ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
    "5": ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    "6": [" ### ", "#    ", "#    ", "#### ", "#   #", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    "8": [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
    "9": [" ### ", "#   #", "#   #", " ####", "    #", "    #", " ### "],
    "!": ["  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "     ", "  #  "],
    "?": [" ### ", "#   #", "    #", "   # ", "  #  ", "     ", "  #  "],
    ".": ["     ", "     ", "     ", "     ", "     ", "     ", "  #  "],
    "-": ["     ", "     ", "     ", " ### ", "     ", "     ", "     "],
}
DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
          "septembre", "octobre", "novembre", "décembre"]


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def norm(v):
    n = math.sqrt(sum(c * c for c in v)) or 1
    return tuple(c / n for c in v)


def spring(t):
    # Ressort amorti (même réglage que ElasticMesh : ω = 15, ζ = 0.38) : 0 → 1 avec rebond
    if t <= 0:
        return 0.0
    w, z = 15.0, 0.38
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * t) * (math.cos(wd * t) + z * w / wd * math.sin(wd * t))


def back_in(u):
    # Petit gonflement avant de rétrécir (sortie « dégonflage »)
    u = min(max(u, 0.0), 1.0)
    c1 = 1.70158
    return (c1 + 1) * u ** 3 - c1 * u ** 2


# ---------------------------------------------------------------- lettres

class Letter:
    """Une lettre gonflée : pixels éclairés précalculés, centre, couleur."""

    def __init__(self, ch, scale, color):
        rows = FONT.get(ch, FONT["?"])
        d = scale // 2  # épaississement pour l'effet ballon
        pad = max(1, d)
        w, h = 5 * scale + 2 * pad, 7 * scale + 2 * pad
        mask = set()
        for y, row in enumerate(rows):
            for x, px in enumerate(row):
                if px == "#":
                    for sy in range(scale):
                        for sx in range(scale):
                            mask.add((pad + x * scale + sx, pad + y * scale + sy))
        # Épaissir d'un disque de rayon d
        mask = {(x + dx, y + dy) for x, y in mask
                for dx in range(-d, d + 1) for dy in range(-d, d + 1) if dx * dx + dy * dy <= d * d + 1}
        # Arrondir les coins : on retire les pixels qui ont peu de voisins
        if scale > 1:
            mask = {(x, y) for x, y in mask
                    if sum((x + dx, y + dy) in mask for dx in (-1, 0, 1) for dy in (-1, 0, 1)) > 4}
        self.w, self.h, self.color = w, h, color
        self.pixels = self.shade(mask, color)

    @staticmethod
    def shade(mask, color):
        # Distance au bord (chanfrein 2 passes) -> profil de tube arrondi -> normale -> lumière
        dist = {p: 0.0 if any((p[0] + dx, p[1] + dy) not in mask
                              for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) else 99.0 for p in mask}
        order = sorted(mask, key=lambda p: (p[1], p[0]))
        for seq in (order, order[::-1]):
            for p in seq:
                for dx, dy, c in ((-1, 0, 1), (0, -1, 1), (-1, -1, 1.4), (1, -1, 1.4),
                                  (1, 0, 1), (0, 1, 1), (1, 1, 1.4), (-1, 1, 1.4)):
                    q = (p[0] + dx, p[1] + dy)
                    if q in dist and dist[q] + c < dist[p]:
                        dist[p] = dist[q] + c
        radius = max(dist.values()) + 1
        height = {p: math.sqrt(max(0.0, 1 - (1 - (d + 0.5) / radius) ** 2)) * radius for p, d in dist.items()}
        light, half = norm(LIGHT), norm((LIGHT[0], LIGHT[1], LIGHT[2] + 1))
        out = {}
        for (x, y), hgt in height.items():
            gx = (height.get((x + 1, y), 0) - height.get((x - 1, y), 0)) / 2
            gy = (height.get((x, y + 1), 0) - height.get((x, y - 1), 0)) / 2
            n = norm((-gx, -gy, 1.0))
            diffuse = max(0.0, sum(a * b for a, b in zip(n, light)))
            spec = 0.85 * max(0.0, sum(a * b for a, b in zip(n, half))) ** 18
            rim = (1 - n[2]) ** 1.5
            # Ballon : cœur clair, bords sombres et saturés, grosse tache de brillance
            base = [c * (0.3 + 0.85 * diffuse) * (1 - 0.45 * rim) for c in color]
            out[(x, y)] = tuple(int(max(0, min(255, c + 255 * spec))) for c in base)
        return out


def layout(text, cols, colors):
    """Choisit la plus grande taille qui tient dans la largeur ; renvoie (lettres, positions, hauteur)."""
    chars = [c for c in text if c == " " or c in FONT]
    for scale in (3, 2, 1):
        pad = max(1, scale // 2)
        step = 5 * scale + 2 * pad + max(2, scale - 1)  # largeur d'une lettre + espacement
        width = sum(step if c != " " else 3 * scale for c in chars)
        if width <= cols - 4 or scale == 1:
            break
    if width > cols - 2:
        return None
    letters, xs, x = [], [], (cols - width) // 2
    for c in chars:
        if c == " ":
            x += 3 * scale
            continue
        letters.append(Letter(c, scale, colors[len(letters) % len(colors)]))
        xs.append(x)
        x += step
    height = 7 * scale + 2 * pad
    return letters, xs, height


# ---------------------------------------------------------------- couleurs du terminal

def truecolor():
    if os.environ.get("COLORTERM") in ("truecolor", "24bit"):
        return True
    prog = os.environ.get("TERM_PROGRAM", "")
    if prog in ("iTerm.app", "vscode", "WezTerm", "ghostty", "WarpTerminal"):
        return True
    if prog == "Apple_Terminal":  # Terminal de macOS : 24 bits depuis macOS 26
        try:
            return int(platform.mac_ver()[0].split(".")[0]) >= 26
        except ValueError:
            return False
    return False


def make_sgr(true):
    def to256(c):
        r, g, b = (round(v / 255 * 5) for v in c)
        return 16 + 36 * r + 6 * g + b

    if true:
        return (lambda c: "\x1b[38;2;%d;%d;%dm" % c), (lambda c: "\x1b[48;2;%d;%d;%dm" % c)
    return (lambda c: "\x1b[38;5;%dm" % to256(c)), (lambda c: "\x1b[48;5;%dm" % to256(c))


# ---------------------------------------------------------------- animation

def frame_pixels(letters, xs, top_px, t, timeline):
    """Pixels de l'image au temps t : {(x, y_pixel): couleur}."""
    t_in, t_hold, n = timeline
    canvas, shadow = {}, {}
    for i, (L, x0) in enumerate(zip(letters, xs)):
        if t < t_in + t_hold:
            p = spring(t - i * 0.07)
            if p < 0.08:
                continue
            size = 0.5 + 0.5 * p
            # Écrasement / étirement façon dessin animé pendant le rebond
            sx, sy = size * (1 + 0.22 * (p - 1)), size * (1 - 0.22 * (p - 1))
            wob = 0.035 * math.sin(t * 9 + i * 1.3) * min(1.0, max(0.0, t - i * 0.07 - 0.6) * 3)
            sx, sy = sx * (1 + wob), sy * (1 - wob)
        else:
            k = 1 - back_in((t - t_in - t_hold - i * 0.05) / 0.32)
            if k <= 0.02:
                continue
            sx = sy = k
        cx, cy = x0 + L.w / 2, top_px + L.h  # ancré en bas : les lettres rebondissent sur le sol
        for y in range(int(cy - L.h * sy) - 1, int(cy) + 2):
            for x in range(int(cx - L.w / 2 * sx) - 1, int(cx + L.w / 2 * sx) + 2):
                u = (x + 0.5 - cx) / sx + L.w / 2
                v = (y + 0.5 - cy) / sy + L.h
                col = L.pixels.get((int(u), int(v)))
                if col:
                    canvas[(x, y)] = col
                    shadow[(x + 1, y + 2)] = SHADOW
    for p in shadow:
        canvas.setdefault(p, SHADOW)
    return canvas


def draw(canvas, rows, cols, fg, bg, subtitle):
    out = ["\x1b8"]  # retour au coin haut-gauche de la zone réservée
    for r in range(rows):
        line, last = [], None
        for x in range(cols):
            top, bot = canvas.get((x, 2 * r)), canvas.get((x, 2 * r + 1))
            if top and bot:
                key, s = (top, bot), fg(top) + bg(bot) + "▀"
            elif top:
                key, s = (top, None), fg(top) + "\x1b[49m▀"
            elif bot:
                key, s = (None, bot), fg(bot) + "\x1b[49m▄"
            else:
                key, s = None, "\x1b[0m "
            line.append(s if key != last or key is None else s[-1])
            last = key
        out.append("".join(line) + "\x1b[0m\x1b[K")
        out.append("\x1b[1B\r")
    out.append("\x1b[K" + subtitle)
    return "".join(out)


def greeting(accent, fg, shown=None, name=None):
    now = datetime.datetime.now()
    if not name:
        try:
            name = pwd.getpwuid(os.getuid()).pw_gecos.split()[0]  # prénom du compte macOS
        except (KeyError, IndexError):
            name = os.environ.get("USER", "")
    hello = "Bonjour" if 5 <= now.hour < 18 else "Bonsoir"
    text = "%s %s  ·  %s %d %s  ·  %02d:%02d" % (hello, name, DAYS[now.weekday()], now.day,
                                                MONTHS[now.month - 1], now.hour, now.minute)
    if shown is not None:
        text = text[:shown]
    return "  " + fg(accent) + "●\x1b[0m " + fg((170, 170, 185)) + text + "\x1b[0m"


def read_config():
    cfg = {"text": "HELLO", "color": "multi"}
    try:
        for line in open(CONFIG, encoding="utf-8"):
            if "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip().lower()] = v.strip()
    except OSError:
        pass
    cfg["text"] = os.environ.get("ASCIIWALL_INTRO_TEXT", cfg["text"])
    return cfg


def main():
    cfg = read_config()
    if not (sys.stdin.isatty() and sys.stdout.isatty()) or cfg.get("enabled", "yes").lower() in ("no", "non", "off", "0"):
        return
    cols, term_rows = os.get_terminal_size(sys.stdout.fileno())
    text = unicodedata.normalize("NFKD", cfg["text"]).encode("ascii", "ignore").decode().upper()
    colors = [hex_rgb(c) for c in CARTOON] if cfg["color"] == "multi" else [hex_rgb(cfg["color"])]
    placed = layout(text, cols, colors) if text.strip() else None
    fg, bg = make_sgr(truecolor())
    if placed is None:  # fenêtre trop étroite : juste la ligne de bienvenue
        print(greeting(colors[0], fg, name=cfg.get("name")))
        return
    letters, xs, letter_h = placed
    top_px = 4  # marge au-dessus pour le rebond
    rows = (letter_h + top_px + 3) // 2 + 1
    if rows + 2 > term_rows:
        print(greeting(colors[0], fg, name=cfg.get("name")))
        return
    t_in = len(letters) * 0.07 + 0.85
    t_hold, t_out = 0.75, len(letters) * 0.05 + 0.4
    timeline = (t_in, t_hold, len(letters))

    import termios
    import tty
    saved = termios.tcgetattr(0)
    tty.setcbreak(0)
    # Réserve la zone (fait défiler si besoin), remonte et mémorise son coin
    sys.stdout.write("\x1b[?25l" + "\n" * rows + "\x1b[%dA\r\x1b7" % rows)
    t0 = time.time()
    try:
        while True:
            t = time.time() - t0
            if t > t_in + t_hold + t_out or select.select([0], [], [], 0)[0]:
                break
            typed = int(max(0.0, t - t_in + 0.4) * 70)  # sous-titre tapé à la machine
            sub = greeting(colors[0], fg, typed, cfg.get("name")) if typed > 0 else ""
            sys.stdout.write(draw(frame_pixels(letters, xs, top_px, t, timeline), rows, cols, fg, bg, sub))
            sys.stdout.flush()
            time.sleep(max(0.0, 1 / FPS - (time.time() - t0 - t)))
    finally:
        termios.tcflush(0, termios.TCIFLUSH)  # la touche qui a passé l'intro ne va pas au shell
        termios.tcsetattr(0, termios.TCSADRAIN, saved)
        # Efface la zone et ne garde que la ligne de bienvenue
        sys.stdout.write("\x1b8\x1b[J" + greeting(colors[0], fg, name=cfg.get("name")) + "\n\x1b[?25h")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyboardInterrupt):
        sys.stdout.write("\x1b[0m\x1b[?25h")
