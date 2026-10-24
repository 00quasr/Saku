"""Programmieren: Schreibtischtest und Fehlersuche in IHK-Pseudocode.
Ein Programm ist ein kleiner Syntaxbaum: derselbe Baum wird als Pseudocode geschrieben, als Struktogramm gezeichnet und
ausgeführt (kein eval), die Lösung kommt aus dem Ausführen. Eigenen Pseudocode liest pseudocode.parsen in denselben Baum.

Ausdrücke: Zahl, WAHR/FALSCH (True/False), Variablenname, ("[]", array, index), ("länge", array), ("liste", [zahlen]),
           ("NICHT", ausdruck), (op, links, rechts) mit op auch UND, ODER
Anweisungen: ("setze", ziel, ausdruck), ("ausgabe", [ausdrücke]), ("wenn", bedingung, dann, sonst),
             ("solange", bedingung, rumpf), ("fuer", variable, von, bis, rumpf)"""

import copy
import operator

from markupsafe import Markup, escape

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, de, tabelle
from saku.lernen.rechnen.svg import Bild, breite

# Formeln und Merksätze je Art: Formelsammlung und Karte zeigen sie nach dem Rechenweg
FORMELN = {
    "schreibtisch": """- Wertetabelle anlegen: eine Spalte je Variable, eine Zeile je Schleifendurchlauf
- Zeile für Zeile ausführen, nach jeder Zuweisung den neuen Wert eintragen
- `a DIV b` ganzzahlige Division (17 DIV 5 = 3), `a MOD b` Rest (17 MOD 5 = 2)
- `FÜR i ← 1 BIS n` läuft n-mal, einschließlich n; Arrays beginnen bei Index 0, der letzte ist länge − 1
- Typische Fehler: falscher Startwert (Summe mit 1 statt 0), Schleife einen Durchlauf zu kurz oder zu lang, falsche Abbruchbedingung, `>` statt `≥`
- Am Struktogramm genauso, von oben nach unten: Verzweigung links ja, rechts nein; der Rumpf einer Schleife steht eingerückt unter ihrem Kopf
- Am Aktivitätsdiagramm vom Startknoten ● den Pfeilen nach bis zum Endknoten ◉: Aktionen in abgerundeten Kästen, an der Raute (Entscheidung) gilt der Pfeil, dessen Wächter `[…]` zutrifft, eine zweite Raute führt die Zweige wieder zusammen
- Schleife im Aktivitätsdiagramm: Zusammenführung, Entscheidung, Rumpf, Pfeil zurück zur Zusammenführung; eine Zählschleife steht aufgelöst da (Startwert, `[i ≤ n]`, Rumpf, `i ← i + 1`)

*Beispiel:* `zahl ← 345`, `SOLANGE zahl > 0`: quersumme 5, 9, 12; zahl 34, 3, 0""",
}


RANG = {"ODER": 1, "UND": 2, "NICHT": 3, "=": 4, "<>": 4, "<": 4, "<=": 4, ">": 4, ">=": 4, "+": 5, "-": 5, "*": 6, "DIV": 6, "MOD": 6}
ZEICHEN = {"<>": "≠", "<=": "≤", ">=": "≥"}
OPS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "DIV": operator.floordiv, "MOD": operator.mod,
       "=": operator.eq, "<>": operator.ne, "<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}
NOTATION = ("Schreibweise: `←` Zuweisung, `=` Vergleich, `DIV` ganzzahlige Division, `MOD` Rest der Division, "
            "Arrays beginnen bei Index 0, `FÜR i ← a BIS b` zählt einschließlich b.")
# Grenzen beim Ausführen: Schritte (Anweisungen und Schleifendurchläufe), Betrag einer Zahl, Werte in der Ausgabe
SCHRITTE, GROESSTE, AUSGABEN = 20_000, 10 ** 12, 1000


def setze(ziel, wert):
    return ("setze", ziel, wert)


def wenn(bedingung, dann, sonst=()):
    return ("wenn", bedingung, list(dann), list(sonst))


# --- schreiben ------------------------------------------------------------

def ausdruck(e, rang: int = 0) -> str:
    if isinstance(e, bool):
        return "WAHR" if e else "FALSCH"
    if isinstance(e, int):
        return str(e)
    if isinstance(e, str):
        return e
    if e[0] == "[]":
        return f"{e[1]}[{ausdruck(e[2])}]"
    if e[0] == "länge":
        return f"länge({e[1]})"
    if e[0] == "liste":
        return "[" + ", ".join(map(str, e[1])) + "]"
    if e[0] == "NICHT":  # Klammern um alles außer einzelnen Werten, „NICHT a = b“ läse sich zweideutig
        text = f"NICHT {ausdruck(e[1], 99)}"
        return f"({text})" if RANG["NICHT"] < rang else text
    op, links, rechts = e
    r = RANG[op]
    text = f"{ausdruck(links, r)} {ZEICHEN.get(op, op)} {ausdruck(rechts, r + 1)}"  # rechts bei gleichem Rang klammern
    return f"({text})" if r < rang else text


def zeilen(block: list, tiefe: int = 0) -> list[tuple[str, tuple]]:
    """(Text, Anweisung) je Zeile; ENDE-Zeilen gehören zu ihrer Anweisung."""
    raus, ein = [], "    " * tiefe
    for s in block:
        if s[0] == "setze":
            ziel = s[1] if isinstance(s[1], str) else ausdruck(s[1])
            raus.append((f"{ein}{ziel} ← {ausdruck(s[2])}", s))
        elif s[0] == "ausgabe":
            raus.append((f"{ein}AUSGABE {', '.join(ausdruck(e) for e in s[1])}", s))
        elif s[0] == "wenn":
            raus += [(f"{ein}WENN {ausdruck(s[1])} DANN", s), *zeilen(s[2], tiefe + 1)]
            if s[3]:
                raus += [(f"{ein}SONST", s), *zeilen(s[3], tiefe + 1)]
            raus.append((f"{ein}ENDE WENN", s))
        elif s[0] == "solange":
            raus += [(f"{ein}SOLANGE {ausdruck(s[1])}", s), *zeilen(s[2], tiefe + 1), (f"{ein}ENDE SOLANGE", s)]
        else:
            raus += [(f"{ein}FÜR {s[1]} ← {ausdruck(s[2])} BIS {ausdruck(s[3])}", s), *zeilen(s[4], tiefe + 1),
                     (f"{ein}ENDE FÜR", s)]
    return raus


def code(programm: list) -> str:
    return "```\n" + "\n".join(f"{n:>2}  {text}" for n, (text, _) in enumerate(zeilen(programm), start=1)) + "\n```"


def quelltext(programm: list) -> str:
    """Der Pseudocode ohne Zeilennummern, so wie man ihn selbst tippt."""
    return "\n".join(text for text, _ in zeilen(programm))


def zeile_von(programm: list, anweisung) -> int:
    return next(n for n, (_, s) in enumerate(zeilen(programm), start=1) if s is anweisung)


# Dreieck der Verzweigung: von den oberen Ecken zur Mitte unten, gestreckt auf die Breite des Kastens
_DREIECK = ('<svg class="sg-dreieck" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
            '<path d="M0 0 L50 100 L100 0" vector-effect="non-scaling-stroke"/></svg>')


def _sg(block: list) -> str:
    teile = []
    for s in block:
        kopf = escape(zeilen([s])[0][0])  # die erste Zeile im Code: Anweisung oder Schleifenkopf
        if s[0] in ("setze", "ausgabe"):
            teile.append(f'<div class="sg sg-anweisung">{kopf}</div>')
        elif s[0] == "wenn":
            teile.append(f'<div class="sg sg-wenn"><div class="sg-bedingung">{_DREIECK}<span class="sg-text">{escape(ausdruck(s[1]))}</span>'
                         '<span class="sg-ja" aria-hidden="true">ja</span><span class="sg-nein" aria-hidden="true">nein</span></div>'
                         f'<div class="sg-zweige"><div class="sg-zweig" role="group" aria-label="ja">{_sg(s[2])}</div>'
                         f'<div class="sg-zweig" role="group" aria-label="nein">{_sg(s[3])}</div></div></div>')
        else:
            teile.append(f'<div class="sg sg-schleife"><div class="sg-kopf">{kopf}</div>'
                         f'<div class="sg-rumpf">{_sg(s[2] if s[0] == "solange" else s[4])}</div></div>')
    return "".join(teile)


def struktogramm(programm: list) -> Markup:
    """Nassi-Shneiderman-Diagramm als HTML (Aussehen in rechnen.css): Anweisung als Kasten, Verzweigung mit Dreieck, ja links
    und nein rechts, kopf- und zählergesteuerte Schleife mit Kopf und eingerücktem Rumpf. Texte wie im Pseudocode."""
    return Markup(f'<div class="struktogramm" role="group" aria-label="Struktogramm">{_sg(programm)}</div>')


# --- Aktivitätsdiagramm ---------------------------------------------------------
# Von oben nach unten auf einer Achse: Aktion als abgerundeter Kasten, Entscheidung und Zusammenführung als Raute, der Ja-Zweig
# links und der Nein-Zweig rechts, Schleife als Zusammenführung, Entscheidung, Rumpf und Rücksprung links; raus geht es rechts.

AKTION, RAUTE, ABSTAND = 30, 26, 24  # Höhe einer Aktion, Größe der Raute, Länge der Pfeile dazwischen
UMKEHR = {"=": "<>", "<>": "=", "<": ">=", "<=": ">", ">": "<=", ">=": "<"}


def nicht(bedingung):
    """Die verneinte Bedingung, so schlicht wie möglich: i < 5 → i >= 5, NICHT x → x."""
    if isinstance(bedingung, tuple) and bedingung[0] in UMKEHR:
        return (UMKEHR[bedingung[0]], *bedingung[1:])
    return bedingung[1] if isinstance(bedingung, tuple) and bedingung[0] == "NICHT" else ("NICHT", bedingung)


def _ohne_fuer(block: list) -> list:
    """FÜR, wie das Aktivitätsdiagramm es zeigt: Startwert, solange i ≤ bis, am Ende des Rumpfs i ← i + 1."""
    raus = []
    for s in block:
        if s[0] == "wenn":
            raus.append(("wenn", s[1], _ohne_fuer(s[2]), _ohne_fuer(s[3])))
        elif s[0] == "solange":
            raus.append(("solange", s[1], _ohne_fuer(s[2])))
        elif s[0] == "fuer":
            raus += [setze(s[1], s[2]), ("solange", ("<=", s[1], s[3]), [*_ohne_fuer(s[4]), setze(s[1], ("+", s[1], 1))])]
        else:
            raus.append(s)
    return raus


def _waechter(bedingung) -> tuple[str, str]:
    return f"[{ausdruck(bedingung)}]", f"[{ausdruck(nicht(bedingung))}]"


def _mass(s) -> tuple[float, float, float]:
    """(links, rechts, Höhe) einer Anweisung, gemessen von ihrer Achse und ihrem oberen Ende."""
    if s[0] in ("setze", "ausgabe"):
        b = breite(zeilen([s])[0][0]) + 24
        return b / 2, b / 2, AKTION
    ja, nein = _waechter(s[1])
    if s[0] == "wenn":
        (lj, rj, hj), (ln, rn, hn), (dl, dr) = _mass_block(s[2]), _mass_block(s[3]), _zweige(s)
        return max(dl + lj, RAUTE / 2 + 4 + breite(ja)), max(dr + rn, RAUTE / 2 + 4 + breite(nein)), 2 * RAUTE + 2 * ABSTAND + max(hj, hn)
    l, r, h = _mass_block(s[2])
    return max(l, RAUTE / 2) + 20, max(r + 20, RAUTE / 2 + breite(nein) + 14, breite(ja) + 20), 2 * RAUTE + 2 * ABSTAND + h + 32


def _zweige(s) -> tuple[float, float]:
    """Wie weit die Achsen von Ja- und Nein-Zweig links und rechts der Mitte stehen: weit genug, dass beide nebeneinander passen."""
    (_, rj, _), (ln, _, _) = _mass_block(s[2]), _mass_block(s[3])
    return max(rj + 10, RAUTE / 2 + 20), max(ln + 10, RAUTE / 2 + 20)


def _mass_block(block: list) -> tuple[float, float, float]:
    masse = [_mass(s) for s in block]
    return (max((m[0] for m in masse), default=0), max((m[1] for m in masse), default=0),
            sum(m[2] for m in masse) + ABSTAND * max(len(masse) - 1, 0))


def _zeichne_block(bild: Bild, block: list, x: float, y: float):
    for i, s in enumerate(block):
        if i:
            bild.pfeil([(x, y - ABSTAND), (x, y)])
        _zeichne(bild, s, x, y)
        y += _mass(s)[2] + ABSTAND


def _zeichne(bild: Bild, s, x: float, y: float):
    """Eine Anweisung mit dem Eingang oben an (x, y); der Ausgang liegt eine Höhe tiefer auf derselben Achse."""
    if s[0] in ("setze", "ausgabe"):
        text = zeilen([s])[0][0]
        b = breite(text) + 24
        bild.kasten(x - b / 2, y, b, AKTION, rund=10)
        bild.text(x, y + AKTION / 2 + 4, text, "middle")
        return
    ja, nein = _waechter(s[1])
    if s[0] == "wenn":
        (dl, dr), hoehe = _zweige(s), max(_mass_block(s[2])[2], _mass_block(s[3])[2])
        yd, yb = y + RAUTE / 2, y + RAUTE + ABSTAND  # Mitte der Entscheidung, Beginn der Zweige
        ym = yb + hoehe + ABSTAND + RAUTE / 2  # Mitte der Zusammenführung
        bild.raute(x, yd, RAUTE, RAUTE)
        bild.raute(x, ym, RAUTE, RAUTE)
        for zweig, seite, achse, waechter in ((s[2], -1, x - dl, ja), (s[3], 1, x + dr, nein)):
            ecke, anker = x + seite * RAUTE / 2, "end" if seite < 0 else "start"
            if zweig:
                bild.pfeil([(ecke, yd), (achse, yd), (achse, yb)])
                _zeichne_block(bild, zweig, achse, yb)
                bild.pfeil([(achse, yb + _mass_block(zweig)[2]), (achse, ym), (ecke, ym)])
            else:
                bild.pfeil([(ecke, yd), (achse, yd), (achse, ym), (ecke, ym)])
            bild.beschriftung([(ecke + seite * 4, yd - 5, anker), (ecke + seite * 4, yd + 15, anker)], [waechter])
        return
    l, r, h = _mass(s)
    yd = y + RAUTE + ABSTAND + RAUTE / 2  # Mitte der Entscheidung
    yb = yd + RAUTE / 2 + ABSTAND  # Beginn des Rumpfs
    zurueck, raus = yb + _mass_block(s[2])[2] + 16, y + h
    bild.raute(x, y + RAUTE / 2, RAUTE, RAUTE)
    bild.pfeil([(x, y + RAUTE), (x, yd - RAUTE / 2)])
    bild.raute(x, yd, RAUTE, RAUTE)
    bild.pfeil([(x, yd + RAUTE / 2), (x, yb)])
    _zeichne_block(bild, s[2], x, yb)
    bild.pfeil([(x, zurueck - 16), (x, zurueck), (x - l, zurueck), (x - l, y + RAUTE / 2), (x - RAUTE / 2, y + RAUTE / 2)])
    bild.linie([(x + RAUTE / 2, yd), (x + r, yd), (x + r, raus), (x, raus)])
    bild.beschriftung([(x + 6, yd + RAUTE / 2 + 14, "start")], [ja])
    bild.beschriftung([(x + RAUTE / 2 + 4, yd - 5, "start"), (x + r - 4, yd + 16, "end")], [nein])


def _beschreibung(block: list) -> str:
    teile = []
    for s in block:
        if s[0] in ("setze", "ausgabe"):
            teile.append(zeilen([s])[0][0])
            continue
        ja, nein = _waechter(s[1])
        if s[0] == "wenn":
            teile.append(f"Entscheidung, bei {ja}: {_beschreibung(s[2]) or 'nichts'}, bei {nein}: {_beschreibung(s[3]) or 'nichts'}; "
                         "Zusammenführung")
        else:
            teile.append(f"Schleife, solange {ja}: {_beschreibung(s[2])}, zurück zur Entscheidung; bei {nein} weiter")
    return "; ".join(teile)


def aktivitaetsdiagramm(programm: list) -> Markup:
    """UML-Aktivitätsdiagramm als SVG aus demselben Baum wie das Struktogramm: Start, Aktionen mit den Texten aus dem Pseudocode,
    Entscheidungen mit Wächtern, Zusammenführungen, Schleifen mit Rücksprung, Ende. Eine Zählschleife steht aufgelöst da."""
    block, bild = _ohne_fuer(programm), Bild()
    bild.kreis(0, 8, 8, voll=True)
    bild.pfeil([(0, 16), (0, 16 + ABSTAND)])
    _zeichne_block(bild, block, 0, 16 + ABSTAND)
    ende = 16 + ABSTAND + _mass_block(block)[2]
    bild.pfeil([(0, ende), (0, ende + ABSTAND)])
    bild.kreis(0, ende + ABSTAND + 10, 10)
    bild.kreis(0, ende + ABSTAND + 10, 5, voll=True)
    return bild.svg("uml-aktivitaet", f"Aktivitätsdiagramm: Start; {_beschreibung(block)}; Ende")


# --- ausführen ----------------------------------------------------------

class Fehler(RuntimeError):
    """Pseudocode lässt sich nicht lesen oder bricht beim Ausführen ab; anweisung: wo (für die Zeilennummer im eigenen Code)."""

    def __init__(self, text: str, anweisung=None):
        super().__init__(text)
        self.anweisung = anweisung


class Lauf:
    """Ein Durchlauf des Programms: Variablen, Ausgabe und je Durchlauf der äußeren Schleife die beobachteten Werte.
    variablen: Startwerte (vorgegebene Eingaben), werden kopiert. Fehler beim Ausführen: Fehler mit der Anweisung."""

    def __init__(self, programm: list, beobachten: list[str], variablen: dict | None = None):
        self.variablen, self.ausgabe, self.durchlaeufe, self.schritte = copy.deepcopy(variablen or {}), [], [], 0
        self.beobachten, self.jetzt = beobachten, None
        self.block(programm, aussen=True)

    def fehler(self, text: str):
        raise Fehler(text, self.jetzt)

    def schritt(self, anweisung):
        self.jetzt, self.schritte = anweisung, self.schritte + 1
        if self.schritte > SCHRITTE:
            self.fehler(f"mehr als {de(SCHRITTE, 0)} Schritte, Endlosschleife?")

    def array(self, name: str) -> list:
        w = self.wert(name)
        return w if isinstance(w, list) else self.fehler(f"{name} ist kein Array")

    def index(self, name: str, e) -> int:
        werte, i = self.array(name), self.wert(e)
        if isinstance(i, list) or not 0 <= i < len(werte):
            self.fehler(f"{name}[{ausdruck(e)}]: " + (f"{name} ist leer" if not werte else
                                                     f"Index {_wert(i)} liegt außerhalb von 0 bis {len(werte) - 1}"))
        return i

    def wert(self, e):
        if isinstance(e, int):
            return e
        if isinstance(e, str):
            return self.variablen[e] if e in self.variablen else self.fehler(f"{e} hat noch keinen Wert")
        if e[0] == "[]":
            return self.array(e[1])[self.index(e[1], e[2])]
        if e[0] == "länge":
            return len(self.array(e[1]))
        if e[0] == "liste":
            return list(e[1])
        if e[0] == "NICHT":
            return not self.wert(e[1])
        if e[0] in ("UND", "ODER"):  # kurz geschlossen: „i < länge(zahlen) UND zahlen[i] …“ liest nicht hinter das Ende
            links = bool(self.wert(e[1]))
            return links and bool(self.wert(e[2])) if e[0] == "UND" else links or bool(self.wert(e[2]))
        links, rechts = self.wert(e[1]), self.wert(e[2])
        if e[0] not in ("=", "<>") and (isinstance(links, list) or isinstance(rechts, list)):
            self.fehler(f"{ausdruck(e)}: mit einem ganzen Array lässt sich nicht rechnen, nur mit einzelnen Werten")
        if e[0] in ("DIV", "MOD") and rechts == 0:
            self.fehler(f"{ausdruck(e)}: Division durch 0")
        w = OPS[e[0]](links, rechts)
        return self.fehler(f"{ausdruck(e)}: Zahl zu groß (über 10¹²)") if abs(w) > GROESSTE else w

    def block(self, block: list, aussen: bool = False):
        for s in block:
            self.schritt(s)
            if s[0] == "setze":
                if isinstance(s[1], str):
                    self.variablen[s[1]] = self.wert(s[2])
                else:
                    w = self.wert(s[2])
                    if isinstance(w, list):
                        self.fehler("in ein Feld des Arrays passt nur ein einzelner Wert")
                    self.array(s[1][1])[self.index(s[1][1], s[1][2])] = w
            elif s[0] == "ausgabe":
                for e in s[1]:
                    w = self.wert(e)
                    self.ausgabe += w if isinstance(w, list) else [w]
                if len(self.ausgabe) > AUSGABEN:
                    self.fehler(f"mehr als {AUSGABEN} Werte ausgegeben")
            elif s[0] == "wenn":
                self.block(s[2] if self.wert(s[1]) else s[3])
            elif s[0] == "solange":
                while self.wert(s[1]):
                    self.block(s[2])
                    self.merken(aussen)
                    self.schritt(s)
            else:
                von, bis = self.wert(s[2]), self.wert(s[3])
                if isinstance(von, list) or isinstance(bis, list):
                    self.fehler("FÜR zählt nur von einer Zahl bis zu einer Zahl")
                for i in range(von, bis + 1):
                    self.variablen[s[1]] = i
                    self.block(s[4])
                    self.merken(aussen)
                    self.schritt(s)

    def merken(self, aussen: bool):
        if aussen:
            self.durchlaeufe.append({v: copy.copy(self.variablen.get(v)) for v in self.beobachten})


def ersetzen(block: list, alt, neu) -> list:
    """Kopie des Programms, in der die Anweisung alt durch neu ersetzt ist (auch verschachtelt)."""
    raus = []
    for s in block:
        if s is alt:
            raus.append(neu)
        elif s[0] == "wenn":
            raus.append(("wenn", s[1], ersetzen(s[2], alt, neu), ersetzen(s[3], alt, neu)))
        elif s[0] == "solange":
            raus.append(("solange", s[1], ersetzen(s[2], alt, neu)))
        elif s[0] == "fuer":
            raus.append(("fuer", *s[1:4], ersetzen(s[4], alt, neu)))
        else:
            raus.append(s)
    return raus


# --- Programme ------------------------------------------------------------
# Jede Familie: (rng) -> dict mit programm, zweck (für die Fehlersuche), beobachten (Spalten der Wertetabelle),
# endwerte (sinnvoll abfragbare Variablen) und fehler: Art → (alte Anweisung, fehlerhafte Anweisung)

def _summe_teilbar(rng):
    a, k = rng.randint(1, 6), rng.choice([2, 3])
    b = a + rng.randint(3, 5)
    pruefen = setze("summe", ("+", "summe", "i"))
    kopf_start = setze("summe", 0)
    rumpf = [wenn(("=", ("MOD", "i", k), 0), [pruefen], [setze("anzahl", ("+", "anzahl", 1))])]
    schleife = ("fuer", "i", a, b, rumpf)
    return {"programm": [kopf_start, setze("anzahl", 0), schleife, ("ausgabe", ["summe", "anzahl"])],
            "zweck": f"die Zahlen von {a} bis {b} addieren, die durch {k} teilbar sind, und die übrigen zählen",
            "beobachten": ["i", "summe", "anzahl"], "endwerte": ["summe", "anzahl"],
            "fehler": {"start": (kopf_start, setze("summe", 1)),
                       "grenze": (schleife, ("fuer", "i", a, b - 1, rumpf)),
                       "bedingung": (rumpf[0], wenn(("=", ("MOD", "i", k), 1), [pruefen], rumpf[0][3]))}}


def _quersumme(rng):
    n = rng.randint(1000, 99999)
    start = setze("quersumme", 0)
    rumpf = [setze("quersumme", ("+", "quersumme", ("MOD", "zahl", 10))), setze("zahl", ("DIV", "zahl", 10))]
    schleife = ("solange", (">", "zahl", 0), rumpf)
    return {"programm": [setze("zahl", n), start, schleife, ("ausgabe", ["quersumme"])],
            "zweck": f"die Quersumme von {n} berechnen", "beobachten": ["zahl", "quersumme"], "endwerte": ["zahl", "quersumme"],
            "fehler": {"abbruch": (schleife, ("solange", (">", "zahl", 9), rumpf)), "start": (start, setze("quersumme", 1))}}


def _binaer(rng):
    n = rng.randint(9, 63)
    rumpf = [setze("rest", ("MOD", "zahl", 2)), ("ausgabe", ["rest"]), setze("zahl", ("DIV", "zahl", 2))]
    schleife = ("solange", (">", "zahl", 0), rumpf)
    return {"programm": [setze("zahl", n), schleife],
            "zweck": f"die Binärdarstellung von {n} ausgeben, das niederwertigste Bit zuerst",
            "beobachten": ["rest", "zahl"], "endwerte": ["zahl", "rest"],
            "fehler": {"abbruch": (schleife, ("solange", (">", "zahl", 1), rumpf))}}


def _extremwert(rng):
    groesser = rng.random() < 0.5
    name, op = ("groesste", ">") if groesser else ("kleinste", "<")
    zahlen = rng.sample(range(2, 60), rng.randint(5, 6))
    extrem = max(zahlen) if groesser else min(zahlen)
    zahlen.remove(extrem)
    zahlen.append(extrem)  # am Ende: nur so fällt ein Durchlauf zu wenig auf
    if zahlen[0] == (max(zahlen[:-1]) if groesser else min(zahlen[:-1])):
        zahlen[0], zahlen[1] = zahlen[1], zahlen[0]
    vergleich = wenn((op, ("[]", "zahlen", "i"), name), [setze(name, ("[]", "zahlen", "i")), setze("position", "i")])
    schleife = ("fuer", "i", 1, ("-", ("länge", "zahlen"), 1), [vergleich])
    start = setze(name, ("[]", "zahlen", 0))
    gegenteil = "<" if groesser else ">"
    return {"programm": [setze("zahlen", ("liste", zahlen)), start, setze("position", 0), schleife, ("ausgabe", [name, "position"])],
            "zweck": f"den {'größten' if groesser else 'kleinsten'} Wert im Array und seine Position ausgeben",
            "beobachten": ["i", name, "position"], "endwerte": [name, "position"],
            "fehler": {"grenze": (schleife, ("fuer", "i", 1, ("-", ("länge", "zahlen"), 2), [vergleich])),
                       "vergleich": (vergleich, wenn((gegenteil, ("[]", "zahlen", "i"), name), vergleich[2])),
                       **({} if groesser else {"start": (start, setze(name, 0))})}}


def _filter(rng):
    grenze = rng.randint(10, 20)
    zahlen = [rng.randint(grenze, grenze + 15)] + [rng.randint(1, grenze + 15) for _ in range(rng.randint(4, 5))]
    zahlen[rng.randrange(1, len(zahlen))] = grenze  # ein Wert genau auf der Grenze: ≥ oder > macht einen Unterschied
    treffer = wenn((">=", ("[]", "zahlen", "i"), grenze),
                   [setze("summe", ("+", "summe", ("[]", "zahlen", "i"))), setze("anzahl", ("+", "anzahl", 1))])
    schleife = ("fuer", "i", 0, ("-", ("länge", "zahlen"), 1), [treffer])
    return {"programm": [setze("zahlen", ("liste", zahlen)), setze("summe", 0), setze("anzahl", 0), schleife,
                         ("ausgabe", [("DIV", "summe", "anzahl")])],
            "zweck": f"den ganzzahligen Durchschnitt aller Werte ab {grenze} (einschließlich) ausgeben",
            "beobachten": ["i", "summe", "anzahl"], "endwerte": ["summe", "anzahl"],
            "fehler": {"start": (schleife, ("fuer", "i", 1, schleife[3], [treffer])),
                       "vergleich": (treffer, wenn((">", ("[]", "zahlen", "i"), grenze), treffer[2]))}}


def _produkt(rng):
    if rng.random() < 0.5:
        n = rng.randint(4, 6)
        rumpf, zweck = [setze("ergebnis", ("*", "ergebnis", "i"))], f"die Fakultät {n}! berechnen"
    else:
        basis, n = rng.randint(2, 5), rng.randint(3, 5)
        rumpf, zweck = [setze("ergebnis", ("*", "ergebnis", basis))], f"die Potenz {basis} hoch {n} berechnen"
    start, schleife = setze("ergebnis", 1), ("fuer", "i", 1, n, rumpf)
    return {"programm": [start, schleife, ("ausgabe", ["ergebnis"])], "zweck": zweck,
            "beobachten": ["i", "ergebnis"], "endwerte": ["ergebnis"],
            "fehler": {"start": (start, setze("ergebnis", 0)), "grenze": (schleife, ("fuer", "i", 1, ("-", n, 1), rumpf))}}


def _umdrehen(rng):
    zahlen = rng.sample(range(1, 40), rng.randint(5, 6))
    hinten = ("-", ("-", ("länge", "zahlen"), 1), "i")
    rumpf = [setze("tmp", ("[]", "zahlen", "i")), setze(("[]", "zahlen", "i"), ("[]", "zahlen", hinten)),
             setze(("[]", "zahlen", hinten), "tmp")]
    schleife = ("fuer", "i", 0, ("-", ("DIV", ("länge", "zahlen"), 2), 1), rumpf)
    return {"programm": [setze("zahlen", ("liste", zahlen)), schleife, ("ausgabe", ["zahlen"])],
            "zweck": "die Reihenfolge der Werte im Array umkehren und das Array ausgeben",
            "beobachten": ["i", "tmp"], "endwerte": ["zahlen"],
            "fehler": {"grenze": (schleife, ("fuer", "i", 0, ("-", ("länge", "zahlen"), 1), rumpf))}}


def _collatz(rng):
    n = rng.choice([5, 8, 10, 16, 32, 64])
    rumpf = [wenn(("=", ("MOD", "n", 2), 0), [setze("n", ("DIV", "n", 2))], [setze("n", ("+", ("*", 3, "n"), 1))]),
             setze("schritte", ("+", "schritte", 1))]
    schleife = ("solange", ("<>", "n", 1), rumpf)
    return {"programm": [setze("n", n), setze("schritte", 0), schleife, ("ausgabe", ["schritte"])],
            "zweck": f"zählen, wie viele Schritte die Folge (gerade: halbieren, ungerade: 3 · n + 1) von {n} bis 1 braucht",
            "beobachten": ["n", "schritte"], "endwerte": ["n", "schritte"],
            "fehler": {"abbruch": (schleife, ("solange", (">", "n", 2), rumpf))}}


def _ggt(rng):
    g = rng.choice([2, 3, 4, 5, 6, 7, 8, 9, 12])
    x, y = rng.sample([p for p in range(2, 13)], 2)
    a, b = max(x, y) * g, min(x, y) * g
    rumpf = [setze("rest", ("MOD", "a", "b")), setze("a", "b"), setze("b", "rest")]
    return {"programm": [setze("a", a), setze("b", b), ("solange", ("<>", "b", 0), rumpf), ("ausgabe", ["a"])],
            "zweck": f"den größten gemeinsamen Teiler von {a} und {b} berechnen (Euklid)",
            "beobachten": ["a", "b", "rest"], "endwerte": ["a", "b"], "fehler": {}}


FAMILIEN = [_summe_teilbar, _quersumme, _binaer, _extremwert, _filter, _produkt, _umdrehen, _collatz, _ggt]
FEHLERART = {"start": "falscher Startwert", "grenze": "falsche Schleifengrenze",
             "abbruch": "falsche Abbruchbedingung", "vergleich": "falscher Vergleich", "bedingung": "falsche Bedingung"}


def _liste(werte) -> str:
    return ", ".join(map(str, werte))


def _wert(w) -> str:
    return "–" if w is None else f"[{_liste(w)}]" if isinstance(w, list) else ausdruck(w)  # ausdruck: WAHR/FALSCH


def _wertetabelle(lauf: Lauf) -> str:
    return tabelle(["Durchlauf", *lauf.beobachten], [[n, *(_wert(z[v]) for v in lauf.beobachten)]
                                                      for n, z in enumerate(lauf.durchlaeufe, start=1)])


@art("schreibtisch", "Schreibtischtest", "Programmieren", "Pseudocode von Hand ausführen: Wertetabelle, Ausgabe, Fehlersuche",
     ("Schreibtischtest", "Kontrollstruktur", "Pseudocode", "Struktogramm", "Programmcode", "Trace-Tabelle", "Aktivitätsdiagramm"),
     formeln=FORMELN["schreibtisch"])
def schreibtisch(rng):
    while True:
        p = rng.choice(FAMILIEN)(rng)
        lauf = Lauf(p["programm"], p["beobachten"])
        varianten = ["ausgabe", "endwerte"] + (["tabelle"] if 2 <= len(lauf.durchlaeufe) <= 6 else []) + (["fehler"] if p["fehler"] else [])
        variante = rng.choice(varianten)
        if variante != "fehler":
            break
        art_, (alt, neu) = rng.choice(list(p["fehler"].items()))
        falsch = ersetzen(p["programm"], alt, neu)
        try:
            fehllauf = Lauf(falsch, p["beobachten"])
        except (RuntimeError, ZeroDivisionError, IndexError):
            continue
        if fehllauf.ausgabe != lauf.ausgabe:
            return _fehlersuche(rng, p, lauf, falsch, fehllauf, zeile_von(falsch, neu), alt, neu, art_)
    weg = f"Wertetabelle, Werte am Ende jedes Durchlaufs:\n\n{_wertetabelle(lauf)}\n\nAusgabe: **{_liste(lauf.ausgabe)}**"
    firma = rng.choice(FIRMEN)
    namen = rng.sample(p["endwerte"], min(2, len(p["endwerte"]))) if variante == "endwerte" else []
    # am Struktogramm oder am Aktivitätsdiagramm; als Letztes gezogen, so bleiben alle übrigen Seeds dieselbe Aufgabe. Die
    # Wertetabelle einer Zählschleife nicht am Aktivitätsdiagramm: dort ist i am Ende des Durchlaufs schon um eins weiter
    zufall = rng.random()
    zaehlt = variante == "tabelle" and any(s[0] == "fuer" for _, s in zeilen(p["programm"]))
    diagramm = "Struktogramm" if zufall < 0.3 else "Aktivitätsdiagramm" if zufall < 0.5 and not zaehlt else ""
    if diagramm:
        einleitung = (f"Ein Auszubildender der {firma} hat ein Programm als {diagramm} entworfen (siehe unten). "
                      f"Es soll {p['zweck']}.\n\n{NOTATION}\n\n")
        weg += f"\n\nDasselbe Programm in Pseudocode:\n\n{code(p['programm'])}"
    else:
        einleitung = (f"Ein Auszubildender der {firma} hat ein Programm geschrieben. Es soll {p['zweck']}.\n\n"
                      f"{code(p['programm'])}\n\n{NOTATION}\n\n")
    bild = {"struktogramm": (struktogramm if diagramm == "Struktogramm" else aktivitaetsdiagramm)(p["programm"])} if diagramm else {}
    am = f" am {diagramm}" if diagramm else " bestimmen"
    if variante == "ausgabe":
        feld = Feld("ausgabe", "Ausgabe", _liste(lauf.ausgabe), typ="liste") if len(lauf.ausgabe) > 1 \
            else Feld("ausgabe", "Ausgabe", lauf.ausgabe[0], stellen=0)
        frage = einleitung + "Führen Sie einen Schreibtischtest durch: Welche Ausgabe erzeugt das Programm?" + \
            (" (Werte in der Reihenfolge der Ausgabe, durch Komma getrennt)" if len(lauf.ausgabe) > 1 else "")
        return Aufgabe(frage, [feld], weg, titel="Ausgabe" + am, **bild)
    if variante == "endwerte":
        felder = [Feld(n, f"{n} am Ende", _liste(lauf.variablen[n]), typ="liste") if isinstance(lauf.variablen[n], list)
                  else Feld(n, f"{n} am Ende", lauf.variablen[n], stellen=0) for n in namen]
        frage = einleitung + f"Welche Werte haben {' und '.join(f'`{n}`' for n in namen)} nach dem Ablauf des Programms?"
        return Aufgabe(frage, felder, weg, titel="Endwerte" + am, **bild)
    zellen = [[Feld(f"d{n}_{v}", f"{v} nach Durchlauf {n}", z[v], stellen=0) for v in lauf.beobachten]
              for n, z in enumerate(lauf.durchlaeufe, start=1)]
    frage = einleitung + ("Führen Sie einen Schreibtischtest durch und tragen Sie die Werte der Variablen **am Ende jedes "
                          "Durchlaufs** der Schleife in die Wertetabelle ein.")
    return Aufgabe(frage, [f for zeile in zellen for f in zeile], weg, titel="Wertetabelle" + (am if bild else ""), **bild,
                   tabelle=[["Durchlauf", *lauf.beobachten], *([str(n), *zeile] for n, zeile in enumerate(zellen, start=1))])


def _fehlersuche(rng, p, lauf, falsch, fehllauf, nummer, alt, neu, art_):
    richtig = next(t for t, s in zeilen(p["programm"]) if s is alt).strip()
    fehlerhaft = next(t for t, s in zeilen(falsch) if s is neu).strip()
    frage = (f"Im Code-Review der {rng.choice(FIRMEN)} fällt ein Programm auf. Es soll {p['zweck']}, enthält aber "
             f"**genau einen Fehler**.\n\n{code(falsch)}\n\n{NOTATION}\n\n"
             "In welcher Zeile steckt der Fehler?")
    weg = (f"Zeile **{nummer}**, {FEHLERART[art_]}: `{fehlerhaft}`, richtig wäre `{richtig}`.\n\n"
           f"Mit dem Fehler gibt das Programm **{_liste(fehllauf.ausgabe)}** aus, richtig wäre **{_liste(lauf.ausgabe)}**.\n\n"
           f"Wertetabelle des richtigen Programms:\n\n{_wertetabelle(lauf)}")
    return Aufgabe(frage, [Feld("zeile", "Fehlerhafte Zeile", nummer, stellen=0)], weg, titel="Fehlersuche")
