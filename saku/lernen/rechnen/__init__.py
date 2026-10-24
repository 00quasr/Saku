"""Rechentrainer 算: unbegrenzt neue Rechenaufgaben im Stil der AP1, sofort und exakt geprüft, mit Rechenweg.
Jede Art ist eine Funktion (rng) -> Aufgabe; derselbe Seed ergibt immer dieselbe Aufgabe. Keine KI, keine Prüfungstexte."""

import ipaddress
import random
import re
from datetime import date

from saku.lernen.antwort import zahl
# melden ihre Arten an; die Reihenfolge hier ist die Reihenfolge der Arten (nach Nutzen für die AP1)
from saku.lernen.rechnen import netzwerk, daten, hardware, komponenten, wirtschaft, wiso, projekt, programmieren, algorithmen  # noqa: F401, I001
from saku.lernen.rechnen.plan import faellig, im_umfang
from saku.lernen.rechnen.basis import ARTEN, GRUPPEN, Art, Aufgabe, Feld

__all__ = ["ARTEN", "GRUPPEN", "Art", "Aufgabe", "Feld", "erzeugen", "pruefen", "stimmt", "passend", "passende",
           "themen_je_art", "gemischt", "faellig", "im_umfang"]


def erzeugen(art: str, seed: int) -> Aufgabe:
    return ARTEN[art].erzeugen(random.Random(seed))


def _ipv4(text: str) -> list[int] | None:
    teile = re.sub(r"\s", "", text).split("/")[0].split(".")
    return [int(t) for t in teile] if len(teile) == 4 and all(t.isdecimal() for t in teile) else None  # isdigit ließe „²“ durch


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


def _ipv6(text: str) -> int | None:
    text = re.sub(r"\s", "", text).lower().split("/")[0]  # Präfixlänge dahinter egal, wie bei _ipv4
    for kandidat in (text, "::" + text):
        try:
            return int(ipaddress.IPv6Address(kandidat))
        except ValueError:
            continue
    return None


def _verhaeltnis(text: str) -> tuple[float, float, int] | None:
    """„16:10“, „16 / 10“, „16 zu 10“, „1,6:1“ → (16, 10, 0) bzw. (1.6, 1, 1): Zähler, Nenner, getippte Nachkommastellen."""
    m = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*(?::|/|zu)\s*(\d+(?:[.,]\d+)?)\s*", text, re.I)
    if not m:
        return None
    a, b = zahl(m[1]), zahl(m[2])
    stellen = max(len(t.replace(".", ",").split(",")[1]) if "," in t.replace(".", ",") else 0 for t in (m[1], m[2]))
    return (a, b, stellen) if a and b else None


def _verhaeltnis_gleich(eingabe: str, soll: str) -> bool:
    """a:b ≙ c:d, wenn a·d = b·c; mit Dezimalzahl getippt („1,78:1“) reicht es, auf die getippten Stellen zu stimmen."""
    ist, ziel = _verhaeltnis(eingabe), _verhaeltnis(soll)
    if not (ist and ziel):
        return False
    if not ist[2]:
        return ist[0] * ziel[1] == ist[1] * ziel[0]
    return abs(ist[0] / ist[1] - ziel[0] / ziel[1]) <= 0.5 * 10 ** -ist[2] + 1e-9


WOCHE = ("montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag")


def _wochentage(text: str) -> list[str]:
    """„Mo (voll), Dienstags und Mi“ → [mo, di, mi]: jedes Wort, das mit einem Wochentag beginnt, und Abkürzungen aus zwei
    oder ab vier Buchstaben; drei wären auch „die“ und „mit“."""
    return [w[:2] for w in re.findall(r"[a-zäöü]+", text.lower())
            if any(w.startswith(t) or t.startswith(w) and (len(w) == 2 or len(w) > 3) for t in WOCHE)]


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
    if feld.typ == "ipv6":  # nach Wert, gekürzt oder nicht; vier Blöcke sind eine Interface-ID
        return _ipv6(eingabe) is not None and _ipv6(eingabe) == _ipv6(soll)
    if feld.typ == "verhaeltnis":
        return _verhaeltnis_gleich(eingabe, soll)
    if feld.typ == "wochentage":
        return bool(_wochentage(eingabe)) and _wochentage(eingabe) == _wochentage(soll)
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
    return any(re.sub(r"\s", "", eingabe).casefold() == re.sub(r"\s", "", s).casefold() for s in (soll, *feld.auch))


def pruefen(aufgabe: Aufgabe, eingaben: dict[str, str]) -> dict[str, bool]:
    """Je Feld: richtig?"""
    return {f.name: stimmt(f, eingaben.get(f.name, ""), aufgabe.toleranz) for f in aufgabe.felder}


def passende(namen) -> list[Art]:
    """Alle Rechenarten, deren Stichwort in einem der Themennamen steckt (auch mitten im Wort: „Angebotskalkulation“), in der
    Reihenfolge der Namen. Nur Namen: die Stichwort-Spalte der Themen nennt Begriffe wie „Leasing“ oder „binäre Suche“ auch dort,
    wo nichts zu rechnen ist."""
    raus = []
    for name in namen:
        for a in ARTEN.values():
            if a not in raus and any(s.casefold() in (name or "").casefold() for s in a.themen):
                raus.append(a)
    return raus


def passend(namen) -> Art | None:
    """Die erste passende Rechenart (siehe passende)."""
    return next(iter(passende(namen)), None)


def themen_je_art(themen) -> dict[str, list[int]]:
    """Die Umkehrung von passende: je Rechenart die Themen (aus Paaren id, Name), zu denen sie passt."""
    raus = {}
    for t_id, name in themen:
        for a in passende([name]):
            raus.setdefault(a.slug, []).append(t_id)
    return raus


def gemischt(rng: random.Random, quoten: dict[str, float], ohne=()) -> str:
    """Zufällige Art für „Gemischt üben“: je schwächer die Quote der letzten Versuche, desto häufiger; Neues wie Schwaches.
    ohne: Arten, die schon dran sind (Sprint: keine Art doppelt)."""
    arten = [a for a in ARTEN if a not in ohne]
    return rng.choices(arten, weights=[1.25 - quoten.get(a, 0.0) for a in arten])[0]
