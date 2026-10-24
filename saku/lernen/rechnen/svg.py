"""SVG-Bausteine für Diagramme (Aktivitätsdiagramm, UML): Formen, Linien, Pfeilspitzen und Beschriftungen in Pixeln.
Keine festen Farben: Linien und Schrift in currentColor, Flächen über Klassen (Aussehen in rechnen.css), so passt jedes Bild
hell und dunkel. Die Schrift ist dicktengleich (JetBrains Mono, 12 px, jedes Zeichen 0,6 em breit): jede Beschriftung lässt
sich vorab vermessen. Beschriftungen an Linien setzt das Bild selbst an die erste freie der vorgeschlagenen Stellen."""

import math

from markupsafe import Markup, escape

SCHRIFT = 12
ZEICHEN = 0.6 * SCHRIFT  # Breite eines Zeichens
ZEILE = 16  # Abstand der Grundlinien
OBEN, UNTEN = 10, 3  # so weit reicht Schrift über und unter die Grundlinie
RAND = 12  # Rand um das ganze Bild


def breite(text: str) -> float:
    return len(text) * ZEICHEN


def _z(x: float) -> str:
    return f"{round(x, 1):g}"


def _punkte(punkte) -> str:
    return " ".join(f"{_z(x)},{_z(y)}" for x, y in punkte)


def _ueberlappen(a, b, luft: float = 0) -> bool:
    return a[0] < b[2] + luft and b[0] < a[2] + luft and a[1] < b[3] + luft and b[1] < a[3] + luft


def schneidet(strecke, r) -> bool:
    """Läuft die Strecke durch das Innere des Rechtecks (x0, y0, x1, y1)? Liang-Barsky, Berühren zählt nicht."""
    (x0, y0), (x1, y1) = strecke
    dx, dy, t0, t1 = x1 - x0, y1 - y0, 0.0, 1.0
    for p, q in ((-dx, x0 - r[0]), (dx, r[2] - x0), (-dy, y0 - r[1]), (dy, r[3] - y0)):
        if p == 0:
            if q <= 0:
                return False
        elif p < 0:
            t0 = max(t0, q / p)
        else:
            t1 = min(t1, q / p)
    return t1 - t0 > 1e-6


def textrahmen(x: float, y: float, zeilen: list[str], anker: str = "start") -> tuple:
    """Rechteck um mehrzeiligen Text; y ist die Grundlinie der ersten Zeile."""
    b = max(map(breite, zeilen))
    links = {"start": x, "middle": x - b / 2, "end": x - b}[anker]
    return links, y - OBEN, links + b, y + (len(zeilen) - 1) * ZEILE + UNTEN


class Bild:
    """Sammelt Formen, Linien und Beschriftungen; svg() setzt die Beschriftungen und den Ausschnitt um alles herum.
    Ebenen: Flächen, Linien, Pfeilspitzen, Schrift (Spitzen decken das Linienende ab, Schrift liegt obenauf)."""

    def __init__(self):
        self.teile, self.formen, self.texte, self.strecken, self.offen = [], [], [], [], []
        self.rahmen = [math.inf, math.inf, -math.inf, -math.inf]

    def _teil(self, ebene: int, svg: str, *punkte):
        self.teile.append((ebene, svg))
        for x, y in punkte:
            self.rahmen = [min(self.rahmen[0], x), min(self.rahmen[1], y), max(self.rahmen[2], x), max(self.rahmen[3], y)]

    # --- Formen ------------------------------------------------------------------------------

    def kasten(self, x, y, b, h, rund: float = 0, klasse: str = ""):
        rx = f' rx="{_z(rund)}"' if rund else ""
        self._teil(0, f'<rect class="uml-kasten{klasse}" x="{_z(x)}" y="{_z(y)}" width="{_z(b)}" height="{_z(h)}"{rx}/>',
                   (x, y), (x + b, y + h))
        self.formen.append((x, y, x + b, y + h))

    def ellipse(self, cx, cy, rx, ry):
        self._teil(0, f'<ellipse class="uml-kasten" cx="{_z(cx)}" cy="{_z(cy)}" rx="{_z(rx)}" ry="{_z(ry)}"/>',
                   (cx - rx, cy - ry), (cx + rx, cy + ry))
        self.formen.append((cx - rx, cy - ry, cx + rx, cy + ry))

    def raute(self, cx, cy, b, h):
        punkte = [(cx, cy - h / 2), (cx + b / 2, cy), (cx, cy + h / 2), (cx - b / 2, cy)]
        self._teil(0, f'<polygon class="uml-kasten" points="{_punkte(punkte)}"/>', *punkte)
        self.formen.append((cx - b / 2, cy - h / 2, cx + b / 2, cy + h / 2))

    def kreis(self, cx, cy, r, voll: bool = False):
        klasse = "uml-voll" if voll else "uml-kasten"
        self._teil(0, f'<circle class="{klasse}" cx="{_z(cx)}" cy="{_z(cy)}" r="{_z(r)}"/>', (cx - r, cy - r), (cx + r, cy + r))
        self.formen.append((cx - r, cy - r, cx + r, cy + r))

    def strichmann(self, cx, oben):
        """Akteur: Kopf, Rumpf, Arme, Beine; 24 breit und 46 hoch."""
        k = oben + 7
        self._teil(0, f'<circle class="uml-kasten" cx="{_z(cx)}" cy="{_z(k)}" r="7"/>', (cx - 12, oben), (cx + 12, oben + 46))
        for punkte in ([(cx, k + 7), (cx, k + 25)], [(cx - 12, k + 13), (cx + 12, k + 13)],
                       [(cx - 11, oben + 46), (cx, k + 25), (cx + 11, oben + 46)]):
            self.teile.append((1, f'<polyline class="uml-linie" points="{_punkte(punkte)}"/>'))
        self.formen.append((cx - 12, oben, cx + 12, oben + 46))

    # --- Linien und Spitzen -------------------------------------------------------------------

    def linie(self, punkte: list, gestrichelt: bool = False):
        klasse = "uml-linie uml-strich" if gestrichelt else "uml-linie"
        self._teil(1, f'<polyline class="{klasse}" points="{_punkte(punkte)}"/>', *punkte)
        self.strecken += zip(punkte, punkte[1:])

    def spitze(self, von, nach, form: str = "offen"):
        """Pfeilspitze an nach, in Richtung von → nach: offen (Fluss, Nachricht, Abhängigkeit), dreieck (Vererbung, hohl),
        voll (synchrone Nachricht), raute und raute-voll (Aggregation, Komposition; die Spitze liegt am Ganzen)."""
        dx, dy = nach[0] - von[0], nach[1] - von[1]
        laenge = math.hypot(dx, dy)
        ux, uy = dx / laenge, dy / laenge

        def p(zurueck, quer):
            return nach[0] - ux * zurueck - uy * quer, nach[1] - uy * zurueck + ux * quer
        if form == "offen":
            self._teil(2, f'<polyline class="uml-linie" points="{_punkte([p(10, 5), nach, p(10, -5)])}"/>', nach)
        elif form in ("dreieck", "voll"):
            klasse = "uml-hohl" if form == "dreieck" else "uml-voll"
            self._teil(2, f'<polygon class="{klasse}" points="{_punkte([nach, p(12, 7), p(12, -7)])}"/>', nach)
        else:
            klasse = "uml-hohl" if form == "raute" else "uml-voll"
            self._teil(2, f'<polygon class="{klasse}" points="{_punkte([nach, p(10, 6), p(20, 0), p(10, -6)])}"/>', nach)

    def pfeil(self, punkte: list, form: str = "offen", gestrichelt: bool = False, anfang: str = ""):
        """Linie mit Spitze am Ende (form) und auf Wunsch am Anfang (anfang, etwa die Raute am Ganzen)."""
        self.linie(punkte, gestrichelt)
        if form:
            self.spitze(punkte[-2], punkte[-1], form)
        if anfang:
            self.spitze(punkte[1], punkte[0], anfang)

    # --- Schrift ----------------------------------------------------------------------------------

    def text(self, x, y, text: str, anker: str = "start", klasse: str = ""):
        """Text an fester Stelle (Inhalt eines Kastens); y ist die Grundlinie."""
        r = textrahmen(x, y, [text], anker)
        k = f' class="{klasse}"' if klasse else ""
        self._teil(3, f'<text{k} x="{_z(x)}" y="{_z(y)}" text-anchor="{anker}">{escape(text)}</text>', r[:2], r[2:])

    def beschriftung(self, kandidaten: list[tuple], zeilen: list[str], klasse: str = ""):
        """Beschriftung an einer Linie: kommt an die erste der Stellen (x, y der ersten Grundlinie, Anker), die nichts überdeckt;
        gesetzt wird erst in svg(), wenn alle Formen und Linien stehen."""
        self.offen.append((kandidaten, [z for z in zeilen if z], klasse))

    def frei(self, r) -> bool:
        return (not any(_ueberlappen(r, f) for f in self.formen) and not any(_ueberlappen(r, t, 2) for t in self.texte)
                and not any(schneidet(s, (r[0] - 2, r[1] - 2, r[2] + 2, r[3] + 2)) for s in self.strecken))

    def _setzen(self):
        for kandidaten, zeilen, klasse in self.offen:
            x, y, anker = next((k for k in kandidaten if self.frei(textrahmen(k[0], k[1], zeilen, k[2]))), kandidaten[0])
            for i, zeile in enumerate(zeilen):
                self.text(x, y + i * ZEILE, zeile, anker, klasse)
            self.texte.append(textrahmen(x, y, zeilen, anker))
        self.offen = []

    def svg(self, klasse: str, beschreibung: str) -> Markup:
        """Das fertige Bild; beschreibung ist die Textfassung für Screenreader (aria-label)."""
        self._setzen()
        x0, y0 = self.rahmen[0] - RAND, self.rahmen[1] - RAND
        b, h = self.rahmen[2] - self.rahmen[0] + 2 * RAND, self.rahmen[3] - self.rahmen[1] + 2 * RAND
        inhalt = "".join(svg for _, svg in sorted(self.teile, key=lambda t: t[0]))
        return Markup(f'<svg class="uml {klasse}" viewBox="{_z(x0)} {_z(y0)} {_z(b)} {_z(h)}" width="{_z(b)}" height="{_z(h)}" '
                      f'role="img" aria-label="{escape(beschreibung)}" font-family="JetBrains Mono, monospace" '
                      f'font-size="{SCHRIFT}">{inhalt}</svg>')
