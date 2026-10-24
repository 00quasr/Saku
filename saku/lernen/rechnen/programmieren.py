"""Programmieren: Schreibtischtest und Fehlersuche in IHK-Pseudocode.
Ein Programm ist ein kleiner Syntaxbaum: derselbe Baum wird als Pseudocode geschrieben und ausgeführt (kein eval),
die Lösung kommt aus dem Ausführen.

Ausdrücke: Zahl, Variablenname, ("[]", array, index), ("länge", array), ("liste", [zahlen]), (op, links, rechts)
Anweisungen: ("setze", ziel, ausdruck), ("ausgabe", [ausdrücke]), ("wenn", bedingung, dann, sonst),
             ("solange", bedingung, rumpf), ("fuer", variable, von, bis, rumpf)"""

import copy
import operator

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, tabelle

# Formeln und Merksätze je Art: Formelsammlung und Karte zeigen sie nach dem Rechenweg
FORMELN = {
    "schreibtisch": """- Wertetabelle anlegen: eine Spalte je Variable, eine Zeile je Schleifendurchlauf
- Zeile für Zeile ausführen, nach jeder Zuweisung den neuen Wert eintragen
- `a DIV b` ganzzahlige Division (17 DIV 5 = 3), `a MOD b` Rest (17 MOD 5 = 2)
- `FÜR i ← 1 BIS n` läuft n-mal, einschließlich n; Arrays beginnen bei Index 0, der letzte ist länge − 1
- Typische Fehler: falscher Startwert (Summe mit 1 statt 0), Schleife einen Durchlauf zu kurz oder zu lang, falsche Abbruchbedingung, `>` statt `≥`

*Beispiel:* `zahl ← 345`, `SOLANGE zahl > 0`: quersumme 5, 9, 12; zahl 34, 3, 0""",
}


RANG = {"=": 1, "<>": 1, "<": 1, "<=": 1, ">": 1, ">=": 1, "+": 2, "-": 2, "*": 3, "DIV": 3, "MOD": 3}
ZEICHEN = {"<>": "≠", "<=": "≤", ">=": "≥"}
OPS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "DIV": operator.floordiv, "MOD": operator.mod,
       "=": operator.eq, "<>": operator.ne, "<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}
NOTATION = ("Schreibweise: `←` Zuweisung, `=` Vergleich, `DIV` ganzzahlige Division, `MOD` Rest der Division, "
            "Arrays beginnen bei Index 0, `FÜR i ← a BIS b` zählt einschließlich b.")


def setze(ziel, wert):
    return ("setze", ziel, wert)


def wenn(bedingung, dann, sonst=()):
    return ("wenn", bedingung, list(dann), list(sonst))


# --- schreiben ------------------------------------------------------------

def ausdruck(e, rang: int = 0) -> str:
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


def zeile_von(programm: list, anweisung) -> int:
    return next(n for n, (_, s) in enumerate(zeilen(programm), start=1) if s is anweisung)


# --- ausführen ----------------------------------------------------------

class Lauf:
    """Ein Durchlauf des Programms: Variablen, Ausgabe und je Durchlauf der äußeren Schleife die beobachteten Werte."""

    def __init__(self, programm: list, beobachten: list[str]):
        self.variablen, self.ausgabe, self.durchlaeufe, self.schritte = {}, [], [], 0
        self.beobachten = beobachten
        self.block(programm, aussen=True)

    def wert(self, e):
        if isinstance(e, int):
            return e
        if isinstance(e, str):
            return self.variablen[e]
        if e[0] == "[]":
            return self.variablen[e[1]][self.wert(e[2])]
        if e[0] == "länge":
            return len(self.variablen[e[1]])
        if e[0] == "liste":
            return list(e[1])
        return OPS[e[0]](self.wert(e[1]), self.wert(e[2]))

    def block(self, block: list, aussen: bool = False):
        for s in block:
            self.schritte += 1
            if self.schritte > 5000:
                raise RuntimeError("Endlosschleife")
            if s[0] == "setze":
                if isinstance(s[1], str):
                    self.variablen[s[1]] = self.wert(s[2])
                else:
                    self.variablen[s[1][1]][self.wert(s[1][2])] = self.wert(s[2])
            elif s[0] == "ausgabe":
                for e in s[1]:
                    w = self.wert(e)
                    self.ausgabe += w if isinstance(w, list) else [w]
            elif s[0] == "wenn":
                self.block(s[2] if self.wert(s[1]) else s[3])
            elif s[0] == "solange":
                while self.wert(s[1]):
                    self.block(s[2])
                    self.merken(aussen)
            else:
                for i in range(self.wert(s[2]), self.wert(s[3]) + 1):
                    self.variablen[s[1]] = i
                    self.block(s[4])
                    self.merken(aussen)

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
    return "–" if w is None else f"[{_liste(w)}]" if isinstance(w, list) else str(w)


def _wertetabelle(lauf: Lauf) -> str:
    return tabelle(["Durchlauf", *lauf.beobachten], [[n, *(_wert(z[v]) for v in lauf.beobachten)]
                                                      for n, z in enumerate(lauf.durchlaeufe, start=1)])


@art("schreibtisch", "Schreibtischtest", "Programmieren", "Pseudocode von Hand ausführen: Wertetabelle, Ausgabe, Fehlersuche",
     ("Schreibtischtest", "Kontrollstruktur", "Pseudocode", "Struktogramm", "Programmcode", "Trace-Tabelle"),
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
    einleitung = (f"Ein Auszubildender der {rng.choice(FIRMEN)} hat ein Programm geschrieben. Es soll {p['zweck']}.\n\n"
                  f"{code(p['programm'])}\n\n{NOTATION}\n\n")
    if variante == "ausgabe":
        feld = Feld("ausgabe", "Ausgabe", _liste(lauf.ausgabe), typ="liste") if len(lauf.ausgabe) > 1 \
            else Feld("ausgabe", "Ausgabe", lauf.ausgabe[0], stellen=0)
        frage = einleitung + "Führen Sie einen Schreibtischtest durch: Welche Ausgabe erzeugt das Programm?" + \
            (" (Werte in der Reihenfolge der Ausgabe, durch Komma getrennt)" if len(lauf.ausgabe) > 1 else "")
        return Aufgabe(frage, [feld], weg, titel="Ausgabe bestimmen")
    if variante == "endwerte":
        namen = rng.sample(p["endwerte"], min(2, len(p["endwerte"])))
        felder = [Feld(n, f"{n} am Ende", _liste(lauf.variablen[n]), typ="liste") if isinstance(lauf.variablen[n], list)
                  else Feld(n, f"{n} am Ende", lauf.variablen[n], stellen=0) for n in namen]
        frage = einleitung + f"Welche Werte haben {' und '.join(f'`{n}`' for n in namen)} nach dem Ablauf des Programms?"
        return Aufgabe(frage, felder, weg, titel="Endwerte bestimmen")
    zellen = [[Feld(f"d{n}_{v}", f"{v} nach Durchlauf {n}", z[v], stellen=0) for v in lauf.beobachten]
              for n, z in enumerate(lauf.durchlaeufe, start=1)]
    frage = einleitung + ("Führen Sie einen Schreibtischtest durch und tragen Sie die Werte der Variablen **am Ende jedes "
                          "Durchlaufs** der Schleife in die Wertetabelle ein.")
    return Aufgabe(frage, [f for zeile in zellen for f in zeile], weg, titel="Wertetabelle",
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
