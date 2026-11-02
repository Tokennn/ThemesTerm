#!/usr/bin/env python3
"""Fonds d'écran ASCII animés dans le terminal (sans dépendance).

Touches : 1 à 8 ou n = changer de thème (transition circulaire), q = quitter.
--splash N : thème au hasard, s'arrête après N secondes ou à la première touche.
"""
import math
import os
import random
import select
import shutil
import sys
import time

GLYPHS = "t%:;S$t:%"
FPS = 30


def glyph(x, y, t):
    # Caractère qui "scintille" : change toutes les ~0.3 s selon la position.
    return GLYPHS[hash((x, y, int(t * 3))) % len(GLYPHS)]


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def ellipse(cx, cy, rx, ry):
    # Cases contenues dans une ellipse (rx en colonnes, ry en lignes).
    for y in range(int(cy - ry), int(cy + ry) + 1):
        for x in range(int(cx - rx), int(cx + rx) + 1):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                yield x, y


# ---------------------------------------------------------------- thèmes

class Theme:
    top = (10, 40, 70)
    bottom = (5, 20, 40)
    dim = 0.55  # atténuation de l'animation sous le texte (asciiterm)

    def background(self, x, y, w, h, t):
        bg = mix(self.top, self.bottom, y / max(1, h - 1))
        # Grille de points discrète, comme dans la vidéo.
        ch = "·" if x % 4 == 0 and y % 2 == 0 else " "
        return ch, shade(bg, 1.6), bg

    def sprites(self, w, h, t):
        return []


class ClaudeCode(Theme):
    top, bottom = (52, 25, 15), (22, 10, 6)
    dim = 0.85  # orange bien visible même sous le texte
    # Personnage en pixels : 1 pixel = 1 demi-case (▀ / ▄), donc 2 pixels par case en hauteur
    CRAB = [" ####### ",
            " ####### ",  # yeux
            "#########",  # bras
            " ####### "]
    LEGS = {"a": (1, 3, 5, 7), "b": (2, 3, 5, 6), "air": (2, 6)}
    HOP = 0.9  # durée d'un saut (s)

    def crab(self, w, h, t):
        orange, eye, sw = (245, 125, 70), (30, 14, 8), len(self.CRAB[0])
        # Course aller-retour le long du bas du terminal
        span = max(1, w - sw)
        pos = (t * 10) % (2 * span)
        direction = 1 if pos < span else -1
        x0 = int(pos if direction > 0 else 2 * span - pos)
        # Saut régulier : arc de parabole, en demi-lignes pour qu'il soit fluide
        jt = (t + 1.3) % 3.2
        air = jt < self.HOP
        lift = int(8 * 4 * (jt / self.HOP) * (1 - jt / self.HOP)) if air else 0
        py0 = 2 * h - len(self.CRAB) - 1 - lift
        legs = "air" if air else ("a" if int(t * 8) % 2 else "b")
        eyes = (3 + direction, 5 + direction)  # il regarde là où il va
        pixels = {}
        for r, row in enumerate(self.CRAB + [""]):  # "" = ligne des pattes
            cols = [c for c, px in enumerate(row) if px == "#"] if row else self.LEGS[legs]
            for c in cols:
                pixels[(x0 + c, py0 + r)] = eye if r == 1 and c in eyes else orange
        # 2 pixels superposés -> une case : ▀ (couleur du haut) sur fond (couleur du bas)
        for (x, py), col in pixels.items():
            if py % 2 == 0:
                yield x, py // 2, "▀", col, pixels.get((x, py + 1))
            elif (x, py - 1) not in pixels:
                yield x, py // 2, "▄", col, None
        # Petite poussière soulevée derrière lui
        if not air:
            for i in range(3):
                if (int(t * 8) + i) % 2:
                    x = x0 - 2 - i * 3 if direction > 0 else x0 + sw + 1 + i * 3
                    yield x, h - 1, ".", shade(orange, 0.7 - i * 0.15), None

    def sprites(self, w, h, t):
        # Soleil-étoile orange qui tourne et dont les rayons respirent
        cx, cy, orange = w * 0.72, h * 0.32, (217, 119, 87)
        for k in range(12):
            a = k * math.pi / 6 + t * 0.15
            length = 6 + 2 * math.sin(t * 1.5 + k * 1.7)
            for d in range(1, int(length * 2)):
                x, y = int(cx + math.cos(a) * d), int(cy + math.sin(a) * d / 2)
                yield x, y, glyph(x, y, t), (255, 175, 130), shade(orange, 0.45 + 0.55 * (1 - d / (length * 2)))
        for x, y in ellipse(cx, cy, 3, 1.5):
            yield x, y, glyph(x, y, t), (255, 210, 180), orange
        # Poussières qui montent lentement
        for i in range(45):
            x = int((i * 37.3) % w + math.sin(t * 0.3 + i) * 2)
            y = int((i * 17.9 - t * 1.5) % h)
            yield x, y, ".", shade(orange, 0.6), None
        yield from self.crab(w, h, t)


class CloudDrift(Theme):
    top, bottom = (95, 160, 230), (185, 215, 250)
    dim = 1.0  # nuages blanc pur, même sous le texte

    def __init__(self):
        self.clouds = [(random.random(), random.random() * 0.8, 1.5 + random.random() * 3,
                        0.6 + random.random() * 0.8) for _ in range(7)]

    def background(self, x, y, w, h, t):
        bg = mix(self.top, self.bottom, y / max(1, h - 1))
        return " ", bg, bg

    def sprites(self, w, h, t):
        for fx, fy, speed, size in self.clouds:
            cx = (fx * (w + 50) + t * speed) % (w + 50) - 25
            cy = fy * h + 3
            # Nuage = 3 bosses arrondies, coupé à plat en dessous
            for ox, oy, r in [(-7, 0.5, 6), (0, -0.5, 8), (8, 0.5, 6)]:
                for x, y in ellipse(cx + ox * size, cy + oy * size, r * size, r * size / 2.5):
                    if y <= cy + 2 * size:
                        yield x, y, glyph(x, y, t), (236, 241, 248), (255, 255, 255)


class HonuLagoon(Theme):
    top, bottom = (60, 205, 200), (20, 120, 150)

    def sprites(self, w, h, t):
        # Algues qui ondulent en bas
        for i in range(0, w, 7):
            for d in range(int(4 + 3 * math.sin(i))):
                x = int(i + math.sin(t * 1.2 + d * 0.6 + i) * d * 0.3)
                yield x, h - 1 - d, glyph(x, d, t), (20, 90, 50), (60, 170, 90)
        # Bulles
        for i in range(12):
            x = int((i * 23.7) % w + math.sin(t + i) * 1.5)
            y = int((h - (t * 3 + i * 9.1)) % h)
            yield x, y, "o", (220, 250, 250), None
        # Tortue : traverse en diagonale et boucle
        p = (t * 0.06) % 1.4 - 0.2
        cx, cy = p * w, h * 0.75 - p * h * 0.5
        flap = math.sin(t * 2.5) * 1.5
        for sx in (-1, 1):  # nageoires avant et arrière
            for x, y in ellipse(cx + 5 + flap, cy + sx * 4.5, 3.5, 1):
                yield x, y, glyph(x, y, t), (50, 110, 70), (120, 190, 120)
            for x, y in ellipse(cx - 6 - flap / 2, cy + sx * 3.5, 2, 1):
                yield x, y, glyph(x, y, t), (50, 110, 70), (120, 190, 120)
        for x, y in ellipse(cx + 9, cy, 2.5, 1.2):  # tête
            yield x, y, glyph(x, y, t), (50, 110, 70), (140, 200, 130)
        for x, y in ellipse(cx, cy, 8, 3.5):  # carapace à motifs
            c = (110, 80, 40) if (x // 3 + y) % 2 else (150, 115, 55)
            yield x, y, glyph(x, y, t), shade(c, 0.6), c


class Jellyfish(Theme):
    top, bottom = (14, 45, 80), (4, 18, 38)

    def __init__(self):
        self.jellies = [(random.random(), random.random(), random.choice(
            [(170, 140, 220), (240, 170, 140), (240, 150, 200)])) for _ in range(4)]

    def sprites(self, w, h, t):
        for i, (fx, fy, col) in enumerate(self.jellies):
            cx = fx * w + math.sin(t * 0.4 + i) * 4
            cy = (fy * (h + 30) - t * 2.5) % (h + 30) - 10  # remonte puis boucle
            pulse = 1 + 0.15 * math.sin(t * 2 + i)
            rx, ry = 9 * pulse, 4 / pulse
            # Ombrelle : demi-ellipse (x doublé car une cellule est 2x plus haute que large)
            for y in range(int(cy - ry), int(cy) + 1):
                for x in range(int(cx - rx), int(cx + rx) + 1):
                    if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                        yield x, y, glyph(x, y, t), shade(col, 0.45), col
            # Tentacules qui ondulent
            for k in range(-3, 4, 2):
                for d in range(1, 12):
                    x = int(cx + k * 2 + math.sin(t * 2 + d * 0.5 + k) * d * 0.25)
                    y = int(cy + d)
                    yield x, y, glyph(x, y, t), col, shade(col, 0.35)


class KoiPond(Theme):
    top, bottom = (40, 140, 120), (20, 90, 85)

    def sprites(self, w, h, t):
        # Nénuphars fixes
        for (px, py) in [(0.1, 0.3), (0.85, 0.75), (0.6, 0.15)]:
            cx, cy = px * w, py * h
            for y in range(int(cy) - 3, int(cy) + 4):
                for x in range(int(cx) - 6, int(cx) + 7):
                    if ((x - cx) / 6) ** 2 + ((y - cy) / 3) ** 2 <= 1 and not (x > cx and abs(y - cy) < 1):
                        yield x, y, glyph(x, y, 0), (30, 90, 40), (90, 190, 80)
        # Kois : corps = suite de segments le long d'un chemin sinusoïdal
        for i, col in enumerate([(230, 120, 40), (240, 240, 230), (220, 80, 50)]):
            a = t * 0.25 + i * 2.1
            for s in range(18):
                b = a - s * 0.04
                x = w / 2 + math.cos(b) * w * 0.33 + math.sin(b * 3) * 3
                y = h / 2 + math.sin(b * 1.3) * h * 0.3
                thick = max(0, 2.2 * math.sin(math.pi * (s + 2) / 20))
                for dx in range(-int(thick * 2), int(thick * 2) + 1):
                    for dy in range(-int(thick), int(thick) + 1):
                        c = col if (s + dx) % 5 else (245, 245, 240)  # taches
                        yield int(x + dx), int(y + dy), glyph(dx, s, t), shade(c, 0.5), c


class Fireflies(Theme):
    top, bottom = (8, 30, 30), (4, 14, 16)

    def __init__(self):
        self.flies = [(random.random(), random.random(), random.random() * 6) for _ in range(40)]

    def sprites(self, w, h, t):
        for fx, fy, ph in self.flies:
            x = int(fx * w + math.sin(t * 0.5 + ph) * 6)
            y = int(fy * h * 0.8 + math.cos(t * 0.4 + ph) * 3)
            glow = max(0.0, math.sin(t * 1.5 + ph))
            if glow > 0.2:
                yield x, y, "*", (255, 255, 180), shade((120, 140, 30), glow)
        # Herbe en bas
        for x in range(w):
            hgt = 3 + int(2 * math.sin(x * 0.7) + math.sin(x * 0.23 + t))
            for y in range(h - hgt, h):
                yield x, y, glyph(x, y, t), (40, 200, 90), (6, 30, 14)


class PaperBoats(Theme):
    top, bottom = (70, 160, 160), (30, 100, 115)

    def __init__(self):
        self.boats = [(random.random(), random.random(), random.uniform(-0.6, 0.6)) for _ in range(6)]

    def sprites(self, w, h, t):
        for i, (fx, fy, a) in enumerate(self.boats):
            # Dérive lente, légère rotation, bouclage aux bords
            a += math.sin(t * 0.5 + i) * 0.15
            cx = (fx * (w + 30) + t * 1.2) % (w + 30) - 15
            cy = (fy * (h + 20) - t * 0.6) % (h + 20) - 10
            ca, sa = math.cos(a), math.sin(a)
            for y in range(int(cy) - 8, int(cy) + 9):
                for x in range(int(cx) - 14, int(cx) + 15):
                    # Repère du bateau (y x2 car les cases sont 2x plus hautes)
                    dx, dy = x - cx, (y - cy) * 2
                    u, v = dx * ca + dy * sa, -dx * sa + dy * ca
                    k = abs(u) / 8 + abs(v) / 14  # losange vu de dessus
                    if k <= 1:
                        c = (235, 238, 240) if u < 0 else (205, 210, 215)  # pli central
                        yield x, y, glyph(x, y, t), (120, 130, 140), c
                    elif 1.25 < k < 1.4 and (x + y + int(t * 4)) % 3 == 0:
                        yield x, y, "o", (150, 210, 210), None  # sillage


class Moonlit(Theme):
    top, bottom = (10, 14, 45), (35, 45, 105)

    def __init__(self):
        self.stars = [(random.random(), random.random() * 0.7, random.random() * 6) for _ in range(60)]
        self.clouds = [(random.random(), 0.15 + random.random() * 0.6, random.uniform(0.4, 1.2)) for _ in range(4)]

    def sprites(self, w, h, t):
        for fx, fy, ph in self.stars:
            k = 0.5 + 0.5 * math.sin(t * 2 + ph)
            yield int(fx * w), int(fy * h), "+" if k > 0.8 else ".", shade((255, 250, 220), 0.4 + 0.6 * k), None
        # Croissant de lune = disque moins un disque décalé
        mx, my = w * 0.8, h * 0.2
        for x, y in ellipse(mx, my, 8, 4):
            if ((x - mx - 3) / 7) ** 2 + ((y - my + 1) / 3.5) ** 2 > 1:
                yield x, y, glyph(x, y, t), (200, 190, 140), (245, 240, 205)
        # Nuages fins qui passent devant
        for fx, fy, speed in self.clouds:
            cx = (fx * (w + 60) + t * speed) % (w + 60) - 30
            for x, y in ellipse(cx, fy * h, 14, 1):
                yield x, y, glyph(x, y, t), (60, 70, 130), (85, 95, 160)


THEMES = [ClaudeCode, CloudDrift, HonuLagoon, KoiPond, Jellyfish, PaperBoats, Fireflies, Moonlit]
NAMES = ["Claude Code", "Cloud Drift", "Honu Lagoon", "Koi Pond", "Jellyfish", "Paper Boats", "Fireflies", "Moonlit"]


# ---------------------------------------------------------------- rendu

def render(theme, w, h, t):
    buf = [[theme.background(x, y, w, h, t) for x in range(w)] for y in range(h)]
    for x, y, ch, fg, bg in theme.sprites(w, h, t):
        if 0 <= x < w and 0 <= y < h:
            buf[y][x] = (ch, fg, bg or buf[y][x][2])  # bg None = garder le fond
    return buf


def to_ansi(buf):
    out, last = ["\x1b[H"], None
    for row in buf:
        for ch, fg, bg in row:
            if (fg, bg) != last:
                out.append("\x1b[38;2;%d;%d;%dm\x1b[48;2;%d;%d;%dm" % (*fg, *bg))
                last = (fg, bg)
            out.append(ch)
    return "".join(out)


def key_reader():
    # Renvoie (lire, restaurer) : lire() donne la touche pressée ou "" sans bloquer.
    if os.name == "nt":
        import msvcrt
        os.system("")  # active les séquences de couleur ANSI dans la console Windows
        sys.stdout.reconfigure(encoding="utf-8")
        if not sys.stdin.isatty():
            return (lambda: ""), (lambda: None)
        return (lambda: msvcrt.getwch() if msvcrt.kbhit() else ""), (lambda: None)
    if not sys.stdin.isatty():
        return (lambda: ""), (lambda: None)
    import termios
    import tty
    saved = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin)
    return ((lambda: sys.stdin.read(1) if select.select([sys.stdin], [], [], 0)[0] else ""),
            (lambda: termios.tcsetattr(sys.stdin, termios.TCSADRAIN, saved)))


def main():
    frames = int(sys.argv[sys.argv.index("--frames") + 1]) if "--frames" in sys.argv else None
    splash = float(sys.argv[sys.argv.index("--splash") + 1]) if "--splash" in sys.argv else None
    idx = random.randrange(len(THEMES)) if splash else 0
    theme, old, switch_t = THEMES[idx](), None, 0.0
    t0, n = time.time(), 0

    read_key, restore = key_reader()
    sys.stdout.write("\x1b[?1049h\x1b[?25l")  # écran alternatif + curseur caché
    try:
        while frames is None or n < frames:
            t = time.time() - t0
            w, h = shutil.get_terminal_size((100, 30))
            if splash and t > splash:
                break
            key = read_key()
            if key:
                if key == "q" or splash:
                    break
                if key == "n" or key in "12345678"[:len(THEMES)]:
                    idx = (idx + 1) % len(THEMES) if key == "n" else int(key) - 1
                    old, theme, switch_t = theme, THEMES[idx](), t

            buf = render(theme, w, h, t)
            if old is not None:
                # Transition : cercle qui grandit depuis le bas-droite
                r = (t - switch_t) * 60
                if r > math.hypot(w, h * 2):
                    old = None
                else:
                    prev = render(old, w, h, t)
                    for y in range(h):
                        for x in range(w):
                            d = math.hypot(x - w, (y - h) * 2)
                            if d > r:
                                buf[y][x] = prev[y][x]
                            elif d > r - 2:
                                buf[y][x] = ("o", (230, 240, 240), buf[y][x][2])

            sys.stdout.write(to_ansi(buf))
            sys.stdout.flush()
            n += 1
            time.sleep(max(0, 1 / FPS - (time.time() - t0 - t)))
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        restore()


if __name__ == "__main__":
    main()
