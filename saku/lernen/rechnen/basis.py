"""Bausteine der Rechenaufgaben: Feld, Aufgabe, die Liste der Arten und Zahlen in deutscher Schreibweise."""

from dataclasses import dataclass, field
from typing import Callable

GRUPPEN = ["Netzwerk", "Daten & Medien", "Strom & Hardware", "Wirtschaft", "Projekt", "Programmieren", "Algorithmen"]

# alles erfunden, wie in der Demo-Datenbank
FIRMEN = ["Demo GmbH", "Muster AG", "Beispiel KG", "Fiktiv Systemhaus GmbH", "Probe & Partner OHG"]
ABTEILUNGEN = ["Buchhaltung", "Vertrieb", "Entwicklung", "Lager", "Personal", "Marketing", "Support", "Geschäftsleitung"]

# Byte je Einheit: Dezimalpräfixe (SI) und Binärpräfixe (IEC)
BYTE = {"kB": 10 ** 3, "MB": 10 ** 6, "GB": 10 ** 9, "TB": 10 ** 12, "KiB": 2 ** 10, "MiB": 2 ** 20, "GiB": 2 ** 30, "TiB": 2 ** 40}
FAKTOR = {"kB": "10³", "MB": "10⁶", "GB": "10⁹", "TB": "10¹²", "KiB": "1.024", "MiB": "1.024²", "GiB": "1.024³", "TiB": "1.024⁴"}


@dataclass
class Feld:
    """Ein Eingabefeld. typ: zahl; text (Groß-/Kleinschreibung und Leerzeichen egal); ip (IPv4, führende Nullen egal);
    pfad (nur Buchstaben und Ziffern zählen, z. B. kritischer Pfad); binaer, hex (der Wert zählt);
    liste (Zahlenfolge wie „3, 8, 1“: nur die Zahlen zählen). Lösung "" heißt: das Feld bleibt leer.
    optionen: Auswahl statt Eingabe."""
    name: str
    label: str
    loesung: float | str
    einheit: str = ""
    typ: str = "zahl"
    stellen: int = 2  # so genau steht die Lösung da; wer auf diese Stellen rundet, liegt immer richtig
    optionen: list[str] = field(default_factory=list)

    @property
    def anzeige(self) -> str:
        if self.typ != "zahl":
            return str(self.loesung)
        return euro(self.loesung).removesuffix(" €") if self.einheit.startswith("€") else de(float(self.loesung), self.stellen)


@dataclass
class Aufgabe:
    frage: str  # Markdown
    felder: list[Feld]
    rechenweg: str  # Markdown, Schritt für Schritt wie in der Prüfung
    toleranz: float = 0.0  # relativ, 0.005 = 0,5 %
    titel: str = ""  # die Variante, z. B. „Netz teilen“
    art: str = ""
    themen: tuple[str, ...] = ()
    # Eingabetabelle (Wertetabelle, Array): erste Zeile Kopf, danach Zellen als Text oder Feld; die Felder stehen auch in felder
    tabelle: list[list] | None = None

    @property
    def loesung(self) -> dict:
        return {f.name: f.loesung for f in self.felder}

    @property
    def tabellen_felder(self) -> set[str]:
        return {z.name for zeile in self.tabelle or [] for z in zeile if isinstance(z, Feld)}


@dataclass(frozen=True)
class Art:
    slug: str
    titel: str
    gruppe: str
    beschreibung: str
    themen: tuple[str, ...]  # Stichworte, an denen passende Themen in der Datenbank erkannt werden
    erzeugen: Callable


ARTEN: dict[str, Art] = {}


def art(slug: str, titel: str, gruppe: str, beschreibung: str, themen: tuple[str, ...]):
    """Meldet einen Generator (rng) -> Aufgabe an; Art, Themen und fehlender Titel kommen von hier."""
    def anmelden(funktion):
        def erzeugen(rng):
            aufgabe = funktion(rng)
            aufgabe.art, aufgabe.themen, aufgabe.titel = slug, themen, aufgabe.titel or titel
            return aufgabe
        ARTEN[slug] = Art(slug, titel, gruppe, beschreibung, themen, erzeugen)
        return erzeugen
    return anmelden


def de(x: float, stellen: int = 2) -> str:
    """1024 → „1.024“, 1.81899 → „1,82“: gerundet, ohne Nullen am Ende."""
    text = f"{x:,.{stellen}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.translate(str.maketrans(",.", ".,"))


def euro(x) -> str:
    """Betrag mit Cent: 1234.5 → „1.234,50 €“ (auch Decimal)."""
    return f"{x:,.2f} €".translate(str.maketrans(",.", ".,"))


def hoch(n: int) -> str:
    """Exponent hochgestellt: 2 + hoch(5) → 2⁵."""
    return str(n).translate(str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻"))


def tabelle(kopf: list[str], zeilen: list[list]) -> str:
    """Markdown-Tabelle."""
    linien = [kopf, ["---"] * len(kopf), *zeilen]
    return "\n".join("| " + " | ".join(str(z) for z in zeile) + " |" for zeile in linien)


def schritte(*zeilen: str) -> str:
    """Nummerierter Rechenweg."""
    return "\n".join(f"{i}. {z}" for i, z in enumerate(zeilen, start=1))
