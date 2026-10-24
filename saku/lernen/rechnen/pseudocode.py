"""Eigener Pseudocode: gelesen in denselben Syntaxbaum, den programmieren.code schreibt und programmieren.Lauf ausführt, und
gegen Testfälle geprüft. Kein eval: jede Zeile wird in Wörter zerlegt und gelesen; Lauf begrenzt Schritte und Zahlen.

Verstanden wird die Schreibweise von code(), tolerant: Schlüsselwörter groß oder klein, FUER, ENDEWENN/ENDE_WENN, nur ENDE,
<- und := für ←, != <> ≠, <= ≤, >= ≥, == für =, UND/ODER/NICHT, WAHR/FALSCH, SONST WENN, DANN in eigener Zeile,
TUE am Ende von SOLANGE und FÜR, FÜR i VON 1 BIS n, AUSGABE(a, b), Kommentare mit //, ein ; am Zeilenende."""

import re

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, de, tabelle
from saku.lernen.rechnen.programmieren import GROESSTE, Fehler, Lauf, ausdruck, code, quelltext, setze, struktogramm, wenn

# Grenzen der Eingabe: Zeichen, Zeilen, Wörter je Zeile (ein Array-Wert mit Komma sind zwei), Schachtelung (Blöcke und Klammern)
ZEICHEN, ZEILEN, WOERTER, TIEFE = 5000, 300, 200, 20

SCHLUESSEL = {"WENN", "DANN", "SONST", "ENDE", "SOLANGE", "FUER", "BIS", "AUSGABE", "UND", "ODER", "NICHT", "DIV", "MOD",
              "WAHR", "FALSCH"}
_TEIL = re.compile(r"\s*(?:(\d+)|([^\W\d]\w*)|(←|<-|:=|<>|!=|≠|<=|≤|>=|≥|==|[-+*()\[\],<>=:])|(\S))")
_GLEICH = {"<-": "←", ":=": "←", "!=": "<>", "≠": "<>", "≤": "<=", "≥": ">=", "==": "="}
_HINWEIS = {"/": "„/“ gibt es hier nicht: ganzzahlig teilen mit DIV, den Rest mit MOD.",
            "%": "„%“ gibt es hier nicht: den Rest der Division mit MOD.",
            '"': "Texte in Anführungszeichen braucht es hier nicht: geben Sie nur die Werte aus.",
            "'": "Texte in Anführungszeichen braucht es hier nicht: geben Sie nur die Werte aus."}
_ENDE = re.compile(r"ende?[\s_]*(wenn|solange|f(?:ü|ue)r)?", re.I)
_STUFEN = [{"ODER"}, {"UND"}, None, {"=", "<>", "<", "<=", ">", ">="}, {"+", "-"}, {"*", "DIV", "MOD"}]  # wie RANG, None: NICHT
_NAME = {"WENN": "WENN", "SOLANGE": "SOLANGE", "FUER": "FÜR"}


def _schluessel(wort: str) -> str | None:
    """FÜR, für, Fuer → FUER; kein Schlüsselwort → None."""
    w = wort.upper().replace("Ü", "UE")
    return w if w in SCHLUESSEL else None


class _Zeile:
    """Die Wörter einer Zeile und ihre Ausdrücke, Vorrang wie programmieren.RANG."""

    def __init__(self, nr: int, text: str):
        self.nr, self.i, self.tiefe, self.teile = nr, 0, 0, []
        for zahl, wort, zeichen, rest in _TEIL.findall(text):
            if rest:
                self.fehler(_HINWEIS.get(rest, f"Das Zeichen „{rest}“ verstehe ich nicht."))
            self.teile.append(("zahl", zahl) if zahl else ("wort", wort) if wort else ("zeichen", _GLEICH.get(zeichen, zeichen)))
        if len(self.teile) > WOERTER:
            self.fehler("Die Zeile ist zu lang, teilen Sie die Rechnung auf.")

    def fehler(self, text: str):
        raise Fehler(f"Zeile {self.nr}: {text}")

    def jetzt(self) -> tuple[str, str] | None:
        return self.teile[self.i] if self.i < len(self.teile) else None

    def zeichen(self, z: str) -> bool:
        if self.jetzt() == ("zeichen", z):
            self.i += 1
            return True
        return False

    def wort(self, *woerter: str) -> bool:
        t = self.jetzt()
        if t and t[0] == "wort" and t[1].upper().replace("Ü", "UE") in woerter:
            self.i += 1
            return True
        return False

    def erwarte(self, z: str, wo: str):
        if not self.zeichen(z):
            self.fehler(f"{wo} fehlt „{z}“.")

    def ende(self):
        if (t := self.jetzt()) is not None:
            self.fehler(f"„{t[1]}“ verstehe ich hier nicht.")

    def rest_klammern(self) -> bool:
        """Steht der Rest der Zeile in einem Paar Klammern, wie bei AUSGABE(a, b)?"""
        if self.jetzt() != ("zeichen", "(") or self.teile[-1] != ("zeichen", ")"):
            return False
        tiefe = 0
        for n, t in enumerate(self.teile[self.i:-1]):
            tiefe += (t == ("zeichen", "(")) - (t == ("zeichen", ")"))
            if tiefe == 0 and n:
                return False
        return True

    def name(self) -> str:
        t = self.jetzt()
        if not t or t[0] != "wort":
            self.fehler("Hier fehlt ein Variablenname." if not t else f"„{t[1]}“ ist kein Variablenname.")
        if _schluessel(t[1]):
            self.fehler(f"„{t[1]}“ ist ein Schlüsselwort und kein Variablenname.")
        self.i += 1
        return t[1]

    def ziel(self):
        """Linke Seite einer Zuweisung: name oder name[index]."""
        name = self.name()
        if self.zeichen("["):
            index = self.ausdruck()
            self.erwarte("]", "Am Index")
            return ("[]", name, index)
        return name

    def tiefer(self):
        self.tiefe += 1
        if self.tiefe > TIEFE:
            self.fehler("Zu viele Klammern ineinander.")

    def ausdruck(self, stufe: int = 0):
        if stufe == 2:
            if self.wort("NICHT"):
                self.tiefer()
                wert = ("NICHT", self.ausdruck(2))
                self.tiefe -= 1
                return wert
            return self.ausdruck(3)
        if stufe == len(_STUFEN):
            return self.einzeln()
        links = self.ausdruck(stufe + 1)
        while (t := self.jetzt()) and (op := t[1] if t[0] == "zeichen" else _schluessel(t[1])) in _STUFEN[stufe]:
            self.i += 1
            links = (op, links, self.ausdruck(stufe + 1))
        return links

    def zahl(self, text: str) -> int:
        if len(text) > 13 or int(text) > GROESSTE:
            self.fehler("Die Zahl ist zu groß (höchstens 10¹²).")
        return int(text)

    def einzeln(self):
        t = self.jetzt()
        if t is None:
            self.fehler("Hier fehlt ein Wert.")
        if t[0] == "zahl":
            self.i += 1
            return self.zahl(t[1])
        if self.zeichen("-"):
            self.tiefer()
            wert = self.einzeln()
            self.tiefe -= 1
            return -wert if type(wert) is int else ("-", 0, wert)  # -5 bleibt eine Zahl
        if self.zeichen("("):
            self.tiefer()
            wert = self.ausdruck()
            self.erwarte(")", "Am Ende der Klammer")
            self.tiefe -= 1
            return wert
        if self.zeichen("["):
            werte = []
            while not self.zeichen("]"):
                if werte and not self.zeichen(","):
                    self.fehler("Im Array fehlt ein Komma oder „]“.")
                minus = self.zeichen("-")
                if not (z := self.jetzt()) or z[0] != "zahl":
                    self.fehler("Ein Array hier enthält nur ganze Zahlen, z. B. [3, 1, 2].")
                self.i += 1
                werte.append(-self.zahl(z[1]) if minus else self.zahl(z[1]))
            return ("liste", werte)
        if t[0] == "wort" and t[1].upper() in ("WAHR", "FALSCH"):
            self.i += 1
            return t[1].upper() == "WAHR"
        if t[0] == "wort" and t[1].casefold() in ("länge", "laenge") and self.teile[self.i + 1:self.i + 2] == [("zeichen", "(")]:
            self.i += 2
            name = self.name()
            self.erwarte(")", "Nach länge(…")
            return ("länge", name)
        if t[0] == "wort":
            name = self.name()
            if self.zeichen("["):
                index = self.ausdruck()
                self.erwarte("]", "Am Index")
                return ("[]", name, index)
            return name
        self.fehler(f"„{t[1]}“ verstehe ich hier nicht.")


class _Leser:
    """Liest Zeile für Zeile; orte: id(Anweisung) → Zeilennummer, für Fehler beim Ausführen."""

    def __init__(self, text: str):
        self.orte, self.pos = {}, 0
        self.zeilen = [(nr, z) for nr, roh in enumerate(text.splitlines(), start=1)
                       if (z := roh.split("//")[0].strip().rstrip(";").rstrip())]

    def naechste(self) -> tuple[int, str] | None:
        return self.zeilen[self.pos] if self.pos < len(self.zeilen) else None

    def block(self, tiefe: int, oben: bool = False) -> list:
        """Anweisungen bis zur Zeile, die den Block schließt (ENDE …, SONST); die liest der Aufrufer."""
        if tiefe > TIEFE:
            raise Fehler(f"Zeile {self.zeilen[self.pos - 1][0]}: Zu tief verschachtelt.")
        raus = []
        while (z := self.naechste()) is not None:
            nr, text = z
            if _ENDE.fullmatch(text) or re.match(r"sonst\b", text, re.I):
                if oben:
                    raise Fehler(f"Zeile {nr}: „{text}“ ohne passendes WENN, SOLANGE oder FÜR davor.")
                return raus
            self.pos += 1
            s = self.anweisung(_Zeile(nr, text), tiefe)
            self.orte[id(s)] = nr
            raus.append(s)
        return raus

    def schliessen(self, art: str, start: int):
        """Die ENDE-Zeile zu art (WENN, SOLANGE, FUER) aus Zeile start; nur ENDE schließt, was offen ist."""
        z, name = self.naechste(), _NAME[art]
        m = z and _ENDE.fullmatch(z[1])
        if not m or (m[1] and m[1].upper().replace("Ü", "UE") != art):
            wo = z[0] if z else self.zeilen[-1][0]
            raise Fehler(f"Zeile {wo}: ENDE {name} fehlt (zu {name} in Zeile {start})" +
                         (f", hier steht „{z[1]}“." if z else "."))
        self.pos += 1

    def anweisung(self, t: _Zeile, tiefe: int):
        erstes = t.teile[0]  # die Zeile ist nicht leer, also gibt es ein Wort
        kopf = _schluessel(erstes[1]) if erstes[0] == "wort" else None
        if kopf and t.teile[1:2] == [("zeichen", "←")]:
            t.fehler(f"„{erstes[1]}“ ist ein Schlüsselwort und kein Variablenname.")
        if kopf == "WENN":
            return self.wenn(t, tiefe)
        if kopf == "SOLANGE":
            t.i += 1
            bedingung = t.ausdruck()
            t.wort("TUE", "MACHE")
            t.ende()
            rumpf = self.block(tiefe + 1)
            self.schliessen("SOLANGE", t.nr)
            return ("solange", bedingung, rumpf)
        if kopf == "FUER":
            t.i += 1
            variable = t.name()
            if not (t.zeichen("←") or t.wort("VON")):
                t.fehler("FÜR braucht die Form FÜR i ← 1 BIS n.")
            von = t.ausdruck()
            if not t.wort("BIS"):
                t.fehler("FÜR braucht die Form FÜR i ← 1 BIS n.")
            bis = t.ausdruck()
            t.wort("TUE", "MACHE")
            t.ende()
            rumpf = self.block(tiefe + 1)
            self.schliessen("FUER", t.nr)
            return ("fuer", variable, von, bis, rumpf)
        if kopf == "AUSGABE":
            t.i += 1
            t.zeichen(":")
            klammern = t.rest_klammern()
            t.i += klammern
            if klammern:
                t.teile.pop()
            if t.jetzt() is None:
                t.fehler("Was soll AUSGABE ausgeben?")
            werte = [t.ausdruck()]
            while t.zeichen(","):
                werte.append(t.ausdruck())
            t.ende()
            return ("ausgabe", werte)
        if kopf:
            t.fehler(f"Eine Anweisung beginnt nicht mit „{erstes[1]}“.")
        ziel = t.ziel()
        if not t.zeichen("←"):
            if t.jetzt() == ("zeichen", "="):
                t.fehler("Zuweisung mit ← (oder <-, :=), = vergleicht nur.")
            t.fehler("Keine Anweisung: Zuweisung mit ←, oder WENN, SOLANGE, FÜR, AUSGABE.")
        wert = t.ausdruck()
        t.ende()
        return ("setze", ziel, wert)

    def wenn(self, t: _Zeile, tiefe: int):
        t.i += 1
        bedingung = t.ausdruck()
        t.wort("DANN")
        t.ende()
        if (z := self.naechste()) and z[1].casefold() == "dann":
            self.pos += 1
        dann, sonst = self.block(tiefe + 1), []
        if (z := self.naechste()) and (m := re.match(r"sonst\b\s*(.*)", z[1], re.I)):
            self.pos += 1
            if m[1]:  # SONST WENN …: ein WENN im SONST-Zweig, das ENDE WENN gilt für beide
                innen = _Zeile(z[0], m[1])
                if not innen.wort("WENN"):
                    innen.fehler("Hinter SONST steht in derselben Zeile nichts außer WENN.")
                innen.i -= 1
                sonst = [self.wenn(innen, tiefe + 1)]
                self.orte[id(sonst[0])] = z[0]
                return ("wenn", bedingung, dann, sonst)
            sonst = self.block(tiefe + 1)
        self.schliessen("WENN", t.nr)
        return ("wenn", bedingung, dann, sonst)


def parsen(text: str) -> tuple[list, dict[int, int]]:
    """Pseudocode → (Programm als Syntaxbaum, id(Anweisung) → Zeilennummer). Lässt er sich nicht lesen: Fehler mit Zeilennummer."""
    if len(text) > ZEICHEN or text.count("\n") >= ZEILEN:
        raise Fehler(f"Das Programm ist zu lang (höchstens {de(ZEICHEN, 0)} Zeichen und {ZEILEN} Zeilen).")
    leser = _Leser(text)
    programm = leser.block(0, oben=True)
    if not programm:
        raise Fehler("Das Programm hat noch keine Anweisung.")
    return programm, leser.orte


def wert(w) -> str:
    """Ein Wert, wie Saku ihn zeigt und vergleicht: 7, -3, WAHR, [1, 2], – (nie gesetzt)."""
    return "–" if w is None else "[" + ", ".join(map(wert, w)) + "]" if isinstance(w, list) else ausdruck(w)


def belegung(eingaben: dict) -> str:
    """Die Eingaben eines Testfalls als Pseudocode: zahlen ← [3, 1], n ← 4."""
    return ", ".join(f"{name} ← {wert(w)}" for name, w in eingaben.items())


def laufen(programm: list, eingaben: dict, orte: dict | None = None) -> Lauf:
    """Führt das Programm mit den Eingaben aus; bricht es ab: Fehler, mit Zeilennummer, wenn orte sie kennt."""
    try:
        return Lauf(programm, [], eingaben)
    except Fehler as f:
        nr = (orte or {}).get(id(f.anweisung))
        raise Fehler(f"Zeile {nr}: {f}" if nr else str(f)) from None
    except RecursionError:
        raise Fehler("Das Programm ist zu tief verschachtelt.") from None


def ergebnis(lauf: Lauf, ziel: str) -> str:
    """Was zählt: der Wert der Ergebnisvariable oder die Ausgabe (Werte mit Komma, leer: nichts ausgegeben)."""
    return wert(lauf.variablen.get(ziel)) if ziel else ", ".join(map(wert, lauf.ausgabe))


def vergleich(loesung: str, testfaelle: list[dict], ziel: str, eingabe: str) -> dict:
    """Eigener Pseudocode gegen die Musterlösung, Testfall für Testfall: {ergebnis 3 alle richtig, 2 einige, 1 keiner;
    faelle [{eingaben, erwartet, erhalten, ok, abbruch}]}. Lässt er sich nicht lesen: ergebnis 1 und die Meldung unter fehler."""
    try:
        programm, orte = parsen(eingabe)
    except Fehler as f:
        return {"ergebnis": 1, "faelle": [], "fehler": str(f)}
    muster, faelle = parsen(loesung)[0], []
    for eingaben in testfaelle:
        erwartet = ergebnis(laufen(muster, eingaben), ziel)
        try:
            erhalten, abbruch = ergebnis(laufen(programm, eingaben, orte), ziel), False
        except Fehler as f:
            erhalten, abbruch = str(f), True
        faelle.append({"eingaben": belegung(eingaben), "erwartet": erwartet, "erhalten": erhalten,
                       "ok": not abbruch and erhalten == erwartet, "abbruch": abbruch})
    richtig = sum(f["ok"] for f in faelle)
    return {"ergebnis": 3 if richtig == len(faelle) else 2 if richtig else 1, "faelle": faelle}


def ausprobieren(eingabe: str, eingaben: dict, ziel: str) -> dict:
    """„Ausführen“ für das Beispiel der Frage: {eingaben, ausgabe, ziel (Name, Wert) oder None} oder {fehler}."""
    try:
        programm, orte = parsen(eingabe)
        lauf = laufen(programm, eingaben, orte)
    except Fehler as f:
        return {"fehler": str(f)}
    return {"eingaben": belegung(eingaben), "ausgabe": ", ".join(map(wert, lauf.ausgabe)),
            "ziel": (ziel, wert(lauf.variablen.get(ziel))) if ziel else None}


# --- Algorithmus schreiben ---------------------------------------------------------
# Jeder Aufgabentyp: (rng) -> dict mit titel, kontext (nach „Die Firma …“), auftrag (nach „…, der …“), eingaben (Name →
# Beschreibung), ergebnis (was zählt), ziel (Ergebnisvariable oder ""), programm (Musterlösung als Syntaxbaum), faelle
# (Eingaben je Testfall, der erste ist das Beispiel; dazu Randfälle, an denen typische Fehler auffallen) und erklaerung.

FORMELN = """**Pseudocode, wie Saku ihn liest**

- Zuweisung `summe ← 0`, auch `<-` oder `:=`; `=` vergleicht nur
- Vergleiche `=`, `≠` (`<>`, `!=`), `<`, `≤` (`<=`), `>`, `≥` (`>=`); verknüpft mit `UND`, `ODER`, `NICHT`; Wahrheitswerte `WAHR`, `FALSCH`
- Rechnen mit `+`, `-`, `*`; `a DIV b` ganzzahlige Division (17 DIV 5 = 3), `a MOD b` Rest (17 MOD 5 = 2), kein `/`; negative Zahlen runden ab (−7 DIV 2 = −4, −7 MOD 2 = 1)
- Arrays: `zahlen ← [3, 1, 2]`, Zugriff `zahlen[i]` ab Index 0, `länge(zahlen)`, der letzte Index ist `länge(zahlen) - 1`
- `WENN Bedingung DANN` … `SONST` … `ENDE WENN`; auch `SONST WENN … DANN` mit einem gemeinsamen `ENDE WENN`
- `SOLANGE Bedingung` … `ENDE SOLANGE`: prüft vor jedem Durchlauf (kopfgesteuert)
- `FÜR i ← 1 BIS n` … `ENDE FÜR`: zählt einschließlich n; liegt `BIS` unter dem Start, läuft sie gar nicht
- `AUSGABE a, b` gibt Werte aus; Kommentare mit `//`
- Auch verstanden: Schlüsselwörter klein, `FUER`, `ENDEWENN`, `ENDE_WENN`, nur `ENDE`, `==`, `FÜR i VON 1 BIS n`, `TUE` am Ende von SOLANGE und FÜR, `DANN` in eigener Zeile, `AUSGABE(a, b)`, `;` am Zeilenende
- Grenzen: 20.000 Schritte (sonst Endlosschleife?), Zahlen bis 10¹², 200 Wörter je Zeile (ein Array also bis etwa 100 Werte), 5.000 Zeichen

**Struktogramm (Nassi-Shneiderman)**

- Anweisung: ein Rechteck; von oben nach unten gelesen
- Verzweigung: Bedingung im Kopf über einem Dreieck, links der Ja-Zweig, rechts der Nein-Zweig; ein leerer Zweig bleibt leer
- Kopfgesteuerte Schleife (SOLANGE) und Zählschleife (FÜR): oben der Kopf, darunter der Rumpf, eingerückt; links läuft der Rand der Schleife mit
- Schleifen und Verzweigungen dürfen ineinander stehen, jeder Block ist wieder ein Struktogramm

*Beispiel:* größter Wert: `max ← zahlen[0]`, dann `FÜR i ← 1 BIS länge(zahlen) - 1` mit `WENN zahlen[i] > max DANN max ← zahlen[i]`; im Struktogramm eine Zählschleife mit einer Verzweigung, deren Nein-Zweig leer bleibt"""

NOTATION_SCHREIBEN = ("Schreibweise wie im Schreibtischtest: `←` Zuweisung, `=` Vergleich, `DIV`, `MOD`, `UND`, `ODER`, `NICHT`, "
                      "`WENN … DANN … SONST … ENDE WENN`, `SOLANGE … ENDE SOLANGE`, `FÜR i ← a BIS b … ENDE FÜR`, `AUSGABE`, "
                      "Arrays ab Index 0 mit `länge(…)`. Alles Weitere steht im Merkblatt unter dem Editor.")
LETZTER = ("-", ("länge", "zahlen"), 1)
ARRAY_TEXT = "Array ganzer Zahlen"


def _durchlauf(rumpf: list, bis=LETZTER, von: int = 0) -> tuple:
    return ("fuer", "i", von, bis, rumpf)


def _x(i="i"):
    return ("[]", "zahlen", i)


def _summe(rng):
    zahlen = [rng.randint(-40, 90) for _ in range(rng.randint(5, 7))]
    return {"titel": "Summe", "kontext": "erfasst die Lagerbewegungen eines Artikels: Zugänge positiv, Abgänge negativ.",
            "auftrag": "die Bestandsänderung berechnet, also alle Werte addiert, und sie ausgibt",
            "eingaben": {"zahlen": f"{ARRAY_TEXT}, auch negativ, kann leer sein"}, "ergebnis": "die Summe mit `AUSGABE`, bei leerem Array 0",
            "ziel": "", "programm": [setze("summe", 0), _durchlauf([setze("summe", ("+", "summe", _x()))]), ("ausgabe", ["summe"])],
            "faelle": [{"zahlen": zahlen}, {"zahlen": []}, {"zahlen": [rng.randint(1, 99)]}, {"zahlen": [-5, -12, -3]}],
            "erklaerung": "Die Summe beginnt bei 0, nicht bei 1 oder beim ersten Wert (der fehlt beim leeren Array). Die Schleife "
                          "läuft über alle Indizes 0 bis länge(zahlen) − 1; ist das Array leer, läuft sie gar nicht."}


def _durchschnitt(rng):
    zahlen = [rng.randint(0, 30) for _ in range(rng.randint(5, 7))]
    summieren = [setze("summe", 0), _durchlauf([setze("summe", ("+", "summe", _x()))]),
                 ("ausgabe", [("DIV", "summe", ("länge", "zahlen"))])]
    return {"titel": "Durchschnitt", "kontext": "misst stündlich die Außentemperatur am Rechenzentrum, in ganzen Grad Celsius.",
            "auftrag": "den Durchschnitt der Messwerte ganzzahlig berechnet (Summe DIV Anzahl) und ausgibt",
            "eingaben": {"zahlen": f"{ARRAY_TEXT}, auch negativ, kann leer sein"},
            "ergebnis": "der ganzzahlige Durchschnitt mit `AUSGABE`; bei leerem Array 0 (nicht durch 0 teilen)", "ziel": "",
            "programm": [wenn(("=", ("länge", "zahlen"), 0), [("ausgabe", [0])], summieren)],
            "faelle": [{"zahlen": zahlen}, {"zahlen": []}, {"zahlen": [rng.randint(-9, 25)]}, {"zahlen": [-4, -2]}, {"zahlen": [7, 8]}],
            "erklaerung": "Erst prüfen, ob das Array leer ist: sonst teilt das Programm durch 0. Danach die Summe wie gewohnt "
                          "(Start 0, Index 0 bis länge(zahlen) − 1) und einmal am Ende ganzzahlig teilen: 15 DIV 2 = 7."}


def _extremwert(rng):
    groesste = rng.random() < 0.5
    name, op, wort = ("groesste", ">", "höchste") if groesste else ("kleinste", "<", "tiefste")
    zahlen = rng.sample(range(-15, 40), rng.randint(5, 7))
    vergleich = wenn((op, _x(), name), [setze(name, _x()), setze("position", "i")])
    extrem = max(zahlen) if groesste else min(zahlen)
    am_ende = [x for x in zahlen if x != extrem] + [extrem]
    abstand = -1 if groesste else 1
    gleich = [extrem + 5 * abstand, extrem, extrem + 9 * abstand, extrem]  # Gleichstand: die erste Position zählt
    vorzeichen = [-7, -3, -12] if groesste else [14, 8, 21]  # Startwert 0 statt zahlen[0] fällt auf
    return {"titel": "Maximum mit Position" if groesste else "Minimum mit Position",
            "kontext": "wertet die Temperaturen eines Kühlraums aus, in ganzen Grad Celsius, auch unter null.",
            "auftrag": f"die {wort} Temperatur und ihre Position im Array ausgibt; kommt sie mehrfach vor, zählt die erste Position",
            "eingaben": {"zahlen": f"{ARRAY_TEXT}, mindestens ein Wert"}, "ergebnis": f"`AUSGABE {name}, position`", "ziel": "",
            "programm": [setze(name, _x(0)), setze("position", 0), _durchlauf([vergleich], von=1), ("ausgabe", [name, "position"])],
            "faelle": [{"zahlen": zahlen}, {"zahlen": am_ende}, {"zahlen": [rng.randint(-9, 9)]}, {"zahlen": vorzeichen},
                       {"zahlen": gleich}],
            "erklaerung": f"Der Startwert ist der erste Wert des Arrays, nicht 0: sonst stimmt das Ergebnis nicht, wenn alle Werte "
                          f"{'negativ' if groesste else 'positiv'} sind. Die Schleife beginnt bei Index 1 und läuft bis zum letzten "
                          f"Index. `{op}` statt `{op}=`: bei Gleichstand bleibt die erste Position stehen."}


def _zaehlen(rng):
    grenze = rng.randint(20, 60)
    art_ = rng.choice(["über", "ab", "gerade"])
    zahlen = [rng.randint(5, 95) for _ in range(rng.randint(6, 8))]
    zahlen[rng.randrange(len(zahlen))] = grenze  # ein Wert genau auf der Grenze: > oder ≥ macht einen Unterschied
    if art_ == "gerade":
        bedingung, auftrag = ("=", ("MOD", _x(), 2), 0), "zählt, wie viele Bestellnummern gerade sind, und die Anzahl ausgibt"
        eingaben, faelle = {}, [{"zahlen": [-4, -3, 0, 7, 10]}, {"zahlen": [1, 3, 5]}]
    else:
        bedingung = (">" if art_ == "über" else ">=", _x(), "grenze")
        auftrag = (f"zählt, wie viele Bestellungen {'über der Grenze liegen (mehr als' if art_ == 'über' else 'die Grenze erreichen (mindestens'}"
                   " `grenze` Euro) und eine Freigabe brauchen, und die Anzahl ausgibt")
        eingaben, faelle = {"grenze": "ganze Zahl"}, [{"zahlen": [grenze, grenze - 1, grenze + 1], "grenze": grenze},
                                                     {"zahlen": [1, 2, 3], "grenze": 3}]
    rumpf = [wenn(bedingung, [setze("anzahl", ("+", "anzahl", 1))])]
    beispiel = {"zahlen": zahlen} | ({"grenze": grenze} if art_ != "gerade" else {})
    kontext = ("verteilt Bestellungen auf zwei Packstationen, gerade Bestellnummern gehen an Station A." if art_ == "gerade"
               else "prüft die Bestellwerte eines Tages in ganzen Euro.")
    return {"titel": "Zählen", "kontext": kontext, "auftrag": auftrag,
            "eingaben": {"zahlen": f"{ARRAY_TEXT}, kann leer sein"} | eingaben, "ergebnis": "die Anzahl mit `AUSGABE`", "ziel": "",
            "programm": [setze("anzahl", 0), _durchlauf(rumpf), ("ausgabe", ["anzahl"])],
            "faelle": [beispiel, *faelle, {"zahlen": []} | ({"grenze": 10} if art_ != "gerade" else {})],
            "erklaerung": "Zähler mit 0 beginnen, in der Schleife über alle Indizes je Treffer um 1 erhöhen und erst nach der "
                          "Schleife ausgeben. " + ("Gerade heißt: Rest 0 bei Division durch 2 (`zahlen[i] MOD 2 = 0`), "
                                                   "auch bei negativen Zahlen und bei 0." if art_ == "gerade" else
                                                   f"„{'mehr als' if art_ == 'über' else 'mindestens'}“ ist "
                                                   f"`{'>' if art_ == 'über' else '≥'}`: ein Wert genau auf der Grenze "
                                                   f"zählt {'nicht' if art_ == 'über' else 'mit'}.")}


def _filtern(rng):
    grenze = rng.randint(10, 30)
    unter = rng.random() < 0.5
    zahlen = [rng.randint(0, 50) for _ in range(rng.randint(6, 8))]
    zahlen[rng.randrange(len(zahlen))] = grenze
    zahlen[0] = rng.randint(0, grenze - 1) if unter else rng.randint(grenze + 1, 50)  # das Beispiel hat sicher eine Ausgabe
    bedingung = ("<" if unter else ">=", _x(), "grenze")
    # alle passen (der letzte auch: eine Schleife eins zu kurz fällt auf), keiner passt; die Grenze selbst in beiden
    alle = [grenze - 9, grenze - 4, grenze - 1] if unter else [grenze, grenze + 4, grenze + 9]
    keiner = [grenze, grenze + 5, grenze + 1] if unter else [grenze - 1, 0, grenze - 5]
    return {"titel": "Filtern",
            "kontext": "führt die Bestände ihres Lagers in Stück." if unter else "misst die Auslastung ihrer Server in Prozent.",
            "auftrag": ("alle Bestände unter dem Mindestbestand `grenze` ausgibt, in der Reihenfolge des Arrays" if unter else
                        "alle Messwerte ab dem Grenzwert `grenze` (einschließlich) ausgibt, in der Reihenfolge des Arrays"),
            "eingaben": {"zahlen": f"{ARRAY_TEXT}, kann leer sein", "grenze": "ganze Zahl"},
            "ergebnis": "jeder passende Wert mit `AUSGABE`; passt keiner, gibt das Programm nichts aus", "ziel": "",
            "programm": [_durchlauf([wenn(bedingung, [("ausgabe", [_x()])])])],
            "faelle": [{"zahlen": zahlen, "grenze": grenze}, {"zahlen": [], "grenze": 5}, {"zahlen": alle, "grenze": grenze},
                       {"zahlen": keiner, "grenze": grenze}],
            "erklaerung": "Eine Schleife über alle Indizes, darin eine Verzweigung ohne SONST: nur passende Werte gibt das Programm "
                          f"aus. „{'unter' if unter else 'ab … einschließlich'}“ ist `{'<' if unter else '≥'}`."}


def _umkehren(rng):
    zahlen = rng.sample(range(1, 60), rng.choice([5, 7]))
    hinten = ("-", LETZTER, "i")
    tauschen = [setze("tmp", _x()), setze(_x(), _x(hinten)), setze(_x(hinten), "tmp")]
    return {"titel": "Umkehren", "kontext": "speichert die Ankunftsreihenfolge von Paketen im Array `zahlen`.",
            "auftrag": "die Reihenfolge der Werte im Array `zahlen` selbst umkehrt (ohne zweites Array): der erste Wert tauscht "
                       "mit dem letzten, der zweite mit dem vorletzten und so weiter",
            "eingaben": {"zahlen": f"{ARRAY_TEXT}, kann leer sein"}, "ergebnis": "das Array `zahlen` nach dem Programm, ausgegeben wird nichts",
            "ziel": "zahlen", "programm": [_durchlauf(tauschen, bis=("-", ("DIV", ("länge", "zahlen"), 2), 1))],
            "faelle": [{"zahlen": zahlen}, {"zahlen": rng.sample(range(1, 60), 6)}, {"zahlen": []}, {"zahlen": [42]}, {"zahlen": [1, 2]}],
            "erklaerung": "Getauscht wird über eine Hilfsvariable `tmp`, sonst geht ein Wert verloren. Die Schleife läuft nur bis zur "
                          "Mitte (länge DIV 2 Tausche): bis zum Ende getauscht, stünde alles wieder an seinem Platz. Der Partner "
                          "von Index i ist länge(zahlen) − 1 − i."}


def _suchen(rng):
    zahlen = rng.sample(range(100, 999), rng.randint(6, 8))
    gesucht = zahlen[rng.randrange(1, len(zahlen) - 1)]
    rumpf = [wenn(("=", _x(), "gesucht"), [setze("position", "i")]), setze("i", ("+", "i", 1))]
    schleife = ("solange", ("UND", ("<", "i", ("länge", "zahlen")), ("=", "position", -1)), rumpf)
    andere = rng.sample(range(100, 999), 5)
    return {"titel": "Lineare Suche", "kontext": "verwaltet die Artikelnummern ihres Lagers in einem unsortierten Array.",
            "auftrag": "die Position (den Index) der gesuchten Artikelnummer ausgibt, bei mehreren die erste; fehlt sie, gibt es -1 aus",
            "eingaben": {"zahlen": f"{ARRAY_TEXT}, kann leer sein", "gesucht": "ganze Zahl"},
            "ergebnis": "die Position mit `AUSGABE`, nicht gefunden -1", "ziel": "",
            "programm": [setze("position", -1), setze("i", 0), schleife, ("ausgabe", ["position"])],
            "faelle": [{"zahlen": zahlen, "gesucht": gesucht}, {"zahlen": andere, "gesucht": andere[-1]},
                       {"zahlen": andere, "gesucht": andere[0]}, {"zahlen": andere, "gesucht": 1000},
                       {"zahlen": [], "gesucht": 5}, {"zahlen": [4, 7, 4, 7], "gesucht": 7}],
            "erklaerung": "Die Suche läuft, solange es noch Indizes gibt **und** nichts gefunden ist: so bleibt die erste Position "
                          "stehen. Bei `UND` wird rechts nur weitergeprüft, wenn links wahr ist, `zahlen[i]` liest also nie hinter "
                          "das Ende. Mit FÜR über alle Indizes geht es auch, dann aber nur setzen, solange `position = -1` ist."}


def _fakultaet(rng):
    return {"titel": "Fakultät", "kontext": "startet nach einem Update n Server nacheinander neu und will wissen, in wie vielen "
                                            "Reihenfolgen das möglich ist.",
            "auftrag": "n! = 1 · 2 · … · n berechnet und ausgibt (0! = 1)",
            "eingaben": {"n": "ganze Zahl von 0 bis 12"}, "ergebnis": "n! mit `AUSGABE`", "ziel": "",
            "programm": [setze("ergebnis", 1), ("fuer", "i", 2, "n", [setze("ergebnis", ("*", "ergebnis", "i"))]), ("ausgabe", ["ergebnis"])],
            "faelle": [{"n": rng.randint(4, 9)}, {"n": 0}, {"n": 1}, {"n": 12}],
            "erklaerung": "Beim Multiplizieren beginnt das Ergebnis mit 1, nicht mit 0. FÜR i ← 2 BIS n läuft für n = 0 und n = 1 "
                          "gar nicht, das Ergebnis bleibt 1; FÜR i ← 1 BIS n geht genauso."}


def _primzahl(rng):
    n = rng.randint(20, 199)
    rumpf = [wenn(("=", ("MOD", "n", "i"), 0), [setze("prim", False)]), setze("i", ("+", "i", 1))]
    schleife = ("solange", ("UND", ("<=", ("*", "i", "i"), "n"), "prim"), rumpf)
    return {"titel": "Primzahltest", "kontext": "braucht für einen Schlüsselgenerator Primzahlen.",
            "auftrag": "prüft, ob n eine Primzahl ist (genau zwei Teiler: 1 und sich selbst), und WAHR oder FALSCH ausgibt",
            "eingaben": {"n": "ganze Zahl ab 1"}, "ergebnis": "`AUSGABE WAHR` oder `AUSGABE FALSCH`", "ziel": "",
            "programm": [setze("prim", (">=", "n", 2)), setze("i", 2), schleife, ("ausgabe", ["prim"])],
            "faelle": [{"n": n}, {"n": 1}, {"n": 2}, {"n": rng.choice([49, 121, 169])}, {"n": rng.choice([97, 101, 113, 127])}],
            "erklaerung": "1 ist keine Primzahl, 2 schon. Probiert werden die Teiler ab 2; es reicht bis √n (i · i ≤ n), bis n − 1 "
                          "geht auch. Bei i · i < n fiele 49 = 7 · 7 durch. Sobald ein Teiler gefunden ist, endet die Schleife."}


def _quersumme(rng):
    rumpf = [setze("quersumme", ("+", "quersumme", ("MOD", "n", 10))), setze("n", ("DIV", "n", 10))]
    return {"titel": "Quersumme", "kontext": "bildet aus Kundennummern eine Prüfziffer und braucht dafür die Quersumme.",
            "auftrag": "die Quersumme von n (die Summe seiner Ziffern) berechnet und ausgibt",
            "eingaben": {"n": "ganze Zahl ab 0"}, "ergebnis": "die Quersumme mit `AUSGABE`", "ziel": "",
            "programm": [setze("quersumme", 0), ("solange", (">", "n", 0), rumpf), ("ausgabe", ["quersumme"])],
            "faelle": [{"n": rng.randint(1000, 999999)}, {"n": 0}, {"n": 7}, {"n": 1005}, {"n": 99999}],
            "erklaerung": "n MOD 10 ist die letzte Ziffer, n DIV 10 streicht sie. Das wiederholt sich, solange n > 0 ist; bei "
                          "n > 9 fehlte die erste Ziffer."}


def _binaer(rng):
    rumpf = [("ausgabe", [("MOD", "n", 2)]), setze("n", ("DIV", "n", 2))]
    return {"titel": "Dezimal → binär", "kontext": "zeigt in einer Schulung, wie ein Rechner Zahlen speichert.",
            "auftrag": "n mit der Restwertmethode in eine Binärzahl umrechnet und die Bits in der Reihenfolge ausgibt, in der sie "
                       "entstehen (das niederwertigste zuerst); für n = 0 gibt es 0 aus",
            "eingaben": {"n": "ganze Zahl ab 0"}, "ergebnis": "die Bits mit `AUSGABE`, eins nach dem anderen", "ziel": "",
            "programm": [wenn(("=", "n", 0), [("ausgabe", [0])]), ("solange", (">", "n", 0), rumpf)],
            "faelle": [{"n": rng.randint(9, 200)}, {"n": 0}, {"n": 1}, {"n": 8}, {"n": 255}],
            "erklaerung": "Restwertmethode: n MOD 2 ist das nächste Bit, dann n DIV 2, solange n > 0. Rückwärts gelesen ergeben die "
                          "Reste die Binärzahl. n = 0 braucht einen eigenen Fall, sonst läuft die Schleife nie."}


def _bubblesort(rng):
    zahlen = rng.sample(range(1, 50), 6)
    while zahlen.index(max(zahlen)) == len(zahlen) - 1:  # das Größte wandert sichtbar nach hinten
        rng.shuffle(zahlen)
    naechster = _x(("+", "i", 1))
    tauschen = wenn((">", _x(), naechster), [setze("tmp", _x()), setze(_x(), naechster), setze(naechster, "tmp")])
    return {"titel": "Bubblesort-Durchlauf", "kontext": "sortiert Ticketnummern aufsteigend und testet dafür Bubblesort.",
            "auftrag": "**einen** Durchlauf von Bubblesort ausführt: von vorn nach hinten je zwei Nachbarn vergleichen und "
                       "tauschen, wenn der linke größer ist",
            "eingaben": {"zahlen": f"{ARRAY_TEXT}, kann leer sein"},
            "ergebnis": "das Array `zahlen` nach dem Durchlauf, ausgegeben wird nichts", "ziel": "zahlen",
            "programm": [_durchlauf([tauschen], bis=("-", ("länge", "zahlen"), 2))],
            "faelle": [{"zahlen": zahlen}, {"zahlen": [9, 1, 2, 3]}, {"zahlen": [1, 2, 3]}, {"zahlen": [5, 5, 1]}, {"zahlen": []},
                       {"zahlen": [8]}],
            "erklaerung": "Verglichen wird zahlen[i] mit zahlen[i + 1], deshalb endet die Schleife beim vorletzten Index "
                          "(länge(zahlen) − 2); bis länge(zahlen) − 1 läse sie hinter das Ende. Nach einem Durchlauf steht der "
                          "größte Wert ganz hinten. Getauscht wird über `tmp`."}


def _teiler(rng):
    vollkommen = rng.random() < 0.5
    n = rng.choice([12, 18, 20, 24, 28, 30, 36, 45, 496] if vollkommen else range(10, 100))
    rumpf = [wenn(("=", ("MOD", "n", "i"), 0), [setze("summe", ("+", "summe", "i"))])]
    programm = [setze("summe", 0), ("fuer", "i", 1, ("-", "n", 1), rumpf), ("ausgabe", [("=", "summe", "n") if vollkommen else "summe"])]
    return {"titel": "Vollkommene Zahl" if vollkommen else "Teilersumme",
            "kontext": "baut für ihre Lern-App ein Rätsel um Teiler.",
            "auftrag": ("prüft, ob n vollkommen ist, also gleich der Summe seiner echten Teiler (alle Teiler außer n selbst, "
                        "6 = 1 + 2 + 3), und WAHR oder FALSCH ausgibt") if vollkommen else
                       "die Summe der echten Teiler von n berechnet (alle Teiler außer n selbst) und ausgibt",
            "eingaben": {"n": "ganze Zahl ab 1"}, "ziel": "", "programm": programm,
            "ergebnis": "`AUSGABE WAHR` oder `AUSGABE FALSCH`" if vollkommen else "die Teilersumme mit `AUSGABE`",
            "faelle": [{"n": n}, {"n": 1}, {"n": 6}, {"n": 28}, {"n": rng.choice([13, 17, 19, 23])}],
            "erklaerung": "Echte Teiler sind 1 bis n − 1: die Schleife endet vor n, sonst zählt n selbst mit. i ist ein Teiler, "
                          "wenn n MOD i = 0 ist. Für n = 1 läuft die Schleife nicht, die Summe bleibt 0."
                          + (" Zum Schluss genügt `AUSGABE summe = n`: der Vergleich ist schon WAHR oder FALSCH." if vollkommen else "")}


def _ggt(rng):
    g = rng.choice([2, 3, 4, 6, 8, 12])
    x, y = rng.sample(range(2, 15), 2)
    rumpf = [setze("rest", ("MOD", "a", "b")), setze("a", "b"), setze("b", "rest")]
    return {"titel": "GGT", "kontext": "kürzt Seitenverhältnisse von Bildschirmen und braucht dafür den größten gemeinsamen Teiler.",
            "auftrag": "den größten gemeinsamen Teiler von a und b mit dem Verfahren von Euklid berechnet und ausgibt",
            "eingaben": {"a": "ganze Zahl ab 1", "b": "ganze Zahl ab 1"}, "ergebnis": "der GGT mit `AUSGABE`", "ziel": "",
            "programm": [("solange", ("<>", "b", 0), rumpf), ("ausgabe", ["a"])],
            "faelle": [{"a": x * g, "b": y * g}, {"a": 1920, "b": 1080}, {"a": 7, "b": 7}, {"a": 9, "b": 27}, {"a": 17, "b": 5}],
            "erklaerung": "Euklid: Solange b nicht 0 ist, wird (a, b) zu (b, a MOD b); dann steht der GGT in a. Die Reihenfolge "
                          "der Zuweisungen zählt, deshalb die Hilfsvariable `rest`. Ist a kleiner als b, tauscht der erste "
                          "Durchlauf die beiden von selbst."}


AUFGABEN = [_summe, _durchschnitt, _extremwert, _zaehlen, _filtern, _umkehren, _suchen, _fakultaet, _primzahl, _quersumme,
            _binaer, _bubblesort, _teiler, _ggt]


def _ergebnis_text(text: str) -> str:
    return f"`{text}`" if text else "nichts"


@art("algorithmus", "Algorithmus schreiben", "Programmieren", "Eigenen Pseudocode schreiben, ausführen und gegen Testfälle prüfen; "
     "Musterlösung mit Struktogramm", ("Pseudocode", "Struktogramm", "Nassi-Shneiderman", "Kontrollstruktur"),
     formeln=FORMELN, sprint=False)  # Sprint: ohne Ausführen und in drei Minuten kein eigenes Programm
def algorithmus(rng):
    a = rng.choice(AUFGABEN)(rng)
    loesung = quelltext(a["programm"])
    ergebnisse = [ergebnis(laufen(a["programm"], f), a["ziel"]) for f in a["faelle"]]
    beispiel = (f"Aus `{belegung(a['faelle'][0])}` wird `{ergebnisse[0]}`." if a["ziel"] else
                f"Für `{belegung(a['faelle'][0])}` gibt das Programm {_ergebnis_text(ergebnisse[0])} aus.")
    frage = (f"Die {rng.choice(FIRMEN)} {a['kontext']} Schreiben Sie einen Algorithmus in Pseudocode, der {a['auftrag']}.\n\n"
             + "\n".join(f"- `{name}`: {text}" for name, text in a["eingaben"].items())
             + f"\n- Ergebnis: {a['ergebnis']}\n\n**Beispiel:** {beispiel}\n\n"
             "Die Eingaben sind schon belegt: weisen Sie ihnen keine festen Werte zu, Saku prüft mit weiteren Testfällen. "
             + NOTATION_SCHREIBEN)
    spalte = f"{a['ziel']} am Ende" if a["ziel"] else "Ausgabe"
    faelle = tabelle(["Eingaben", spalte], [[f"`{belegung(f)}`", f"`{e}`" if e else "(keine)"] for f, e in zip(a["faelle"], ergebnisse)])
    weg = (f"Eine mögliche Lösung, als Struktogramm unter den Testfällen:\n\n{code(a['programm'])}\n\n{a['erklaerung']}\n\n"
           f"Die Testfälle, mit denen Saku prüft:\n\n{faelle}")
    return Aufgabe(frage, [Feld("code", "Dein Pseudocode", loesung, typ="code")], weg, titel=a["titel"],
                   testfaelle=(a["faelle"], a["ziel"]), weg_struktogramm=struktogramm(a["programm"]))
