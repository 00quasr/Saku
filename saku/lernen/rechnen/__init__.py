"""Rechentrainer 算: unbegrenzt neue Rechenaufgaben im Stil der AP1, sofort und exakt geprüft, mit Rechenweg.
Jede Art ist eine Funktion (rng) -> Aufgabe; derselbe Seed ergibt immer dieselbe Aufgabe. Keine KI, keine Prüfungstexte."""

import random
import re
from datetime import date

from saku.lernen.antwort import zahl
# melden ihre Arten an; die Reihenfolge hier ist die Reihenfolge der Arten (nach Nutzen für die AP1)
from saku.lernen.rechnen import netzwerk, daten, hardware, wirtschaft, wiso, projekt, programmieren, algorithmen  # noqa: F401, I001
from saku.lernen.rechnen.basis import ARTEN, GRUPPEN, Art, Aufgabe, Feld

__all__ = ["ARTEN", "GRUPPEN", "Art", "Aufgabe", "Feld", "erzeugen", "pruefen", "stimmt", "passend", "gemischt"]


def erzeugen(art: str, seed: int) -> Aufgabe:
    return ARTEN[art].erzeugen(random.Random(seed))


def _ipv4(text: str) -> list[int] | None:
    teile = re.sub(r"\s", "", text).split("/")[0].split(".")
    return [int(t) for t in teile] if len(teile) == 4 and all(t.isdigit() for t in teile) else None


def _datum(text: str) -> date | None:
    """„3.3.2027“, „03.03.27“, „3. 3. 2027“ oder „2027-03-03“; zweistellige Jahre sind 20xx."""
    if m := re.fullmatch(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{2}|\d{4})", text):
        tag, monat, jahr = int(m[1]), int(m[2]), int(m[3])
    elif m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text):
        jahr, monat, tag = int(m[1]), int(m[2]), int(m[3])
    else:
        return None
    try:
        return date(jahr + 2000 if jahr < 100 else jahr, monat, tag)
    except ValueError:
        return None


def _ganzzahl(text: str, basis: int, praefix: str) -> int | None:
    text = re.sub(r"[\s_]", "", text).lower().removeprefix(praefix).removesuffix("h" if basis == 16 else "b")
    try:
        return int(text, basis)
    except ValueError:
        return None


def stimmt(feld: Feld, eingabe: str, toleranz: float = 0.0) -> bool:
    """Ist die Eingabe für dieses Feld richtig? Zahlen dürfen auf die angezeigten Stellen gerundet sein."""
    eingabe = (eingabe or "").strip()
    if not eingabe:
        return feld.typ != "zahl" and feld.loesung == ""
    if feld.typ == "zahl":
        ist, soll = zahl(eingabe), float(feld.loesung)
        return ist is not None and abs(ist - soll) <= max(toleranz * abs(soll), 0.5 * 10 ** -feld.stellen) + 1e-9
    soll = str(feld.loesung)
    if feld.typ == "ip":
        return _ipv4(eingabe) is not None and _ipv4(eingabe) == _ipv4(soll)
    if feld.typ == "datum":
        return _datum(eingabe) is not None and _datum(eingabe) == _datum(soll)
    if feld.typ == "liste":  # ohne Vorzeichen: „3-8-1“ ist eine Folge mit Bindestrichen (Listen sind nie negativ)
        return [int(x) for x in re.findall(r"\d+", eingabe)] == [int(x) for x in re.findall(r"\d+", soll)]
    if feld.typ == "pfad":
        return re.sub(r"[^A-Z0-9]", "", eingabe.upper()) == re.sub(r"[^A-Z0-9]", "", soll.upper())
    if feld.typ in ("binaer", "hex"):
        basis, praefix = (2, "0b") if feld.typ == "binaer" else (16, "0x")
        ist = _ganzzahl(eingabe, basis, praefix)
        return ist is not None and ist == int(soll, basis)
    return re.sub(r"\s", "", eingabe).casefold() == re.sub(r"\s", "", soll).casefold()


def pruefen(aufgabe: Aufgabe, eingaben: dict[str, str]) -> dict[str, bool]:
    """Je Feld: richtig?"""
    return {f.name: stimmt(f, eingaben.get(f.name, ""), aufgabe.toleranz) for f in aufgabe.felder}


def passend(namen) -> Art | None:
    """Die erste Rechenart, deren Stichwort in einem der Themennamen steckt (auch mitten im Wort: „Angebotskalkulation“).
    Nur Namen: die Stichwort-Spalte der Themen nennt Begriffe wie „Leasing“ oder „binäre Suche“ auch dort, wo nichts zu rechnen ist."""
    for name in namen:
        for a in ARTEN.values():
            if any(s.casefold() in (name or "").casefold() for s in a.themen):
                return a
    return None


def gemischt(rng: random.Random, quoten: dict[str, float], ohne=()) -> str:
    """Zufällige Art für „Gemischt üben“: je schwächer die Quote der letzten Versuche, desto häufiger; Neues wie Schwaches.
    ohne: Arten, die schon dran sind (Sprint: keine Art doppelt)."""
    arten = [a for a in ARTEN if a not in ohne]
    return rng.choices(arten, weights=[1.25 - quoten.get(a, 0.0) for a in arten])[0]
