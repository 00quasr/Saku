"""Anklickbare Aufgaben: automatisch prüfen, was sich prüfen lässt (Auswahl, Reihenfolge, Zuordnung, Zahl).
antwort ist das JSON aus dem Schritt aufbereiten: {art, optionen, ziele, richtig, einheit, vorlage}."""

import re

AUTOMATISCH = ("einfach", "mehrfach", "reihenfolge", "zuordnung", "zahl")


def pruefbar(antwort: dict | None) -> bool:
    return bool(antwort) and antwort["art"] in AUTOMATISCH and bool(antwort["richtig"])


def _zahl(text: str) -> float | None:
    text = re.sub(r"[^\d,.\-]", "", text or "")
    if "," in text:  # deutsch: 1.234,56
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _stufe(anteil: float) -> int:
    """Wie bei Sensei: ab 80 % gewusst, ab 40 % teilweise."""
    return 3 if anteil >= 0.8 else 2 if anteil >= 0.4 else 1


def auswerten(antwort: dict, eingabe: dict) -> tuple[int, dict[str, bool]]:
    """(Ergebnis 1–3, je Option/Feld richtig?) für die Eingabe aus dem Formular.
    eingabe: wahl (Liste), position {wert: Platz}, ziel {wert: Ziel}, zahl (Text)."""
    art, richtig = antwort["art"], [str(r).strip() for r in antwort["richtig"]]
    if art in ("einfach", "mehrfach"):
        gewaehlt, soll = set(eingabe.get("wahl", [])), set(richtig)
        werte = {o["wert"]: (o["wert"] in soll) == (o["wert"] in gewaehlt) for o in antwort["optionen"]}
        if gewaehlt == soll:
            return 3, werte
        treffer, falsch = len(gewaehlt & soll), len(gewaehlt - soll)
        return (2 if art == "mehrfach" and treffer > falsch else 1), werte
    if art == "reihenfolge":
        platz = eingabe.get("position", {})
        werte = {w: platz.get(w, "").strip() == str(i) for i, w in enumerate(richtig, start=1)}
        return _stufe(sum(werte.values()) / len(werte)), werte
    if art == "zuordnung":
        soll = dict(r.split("=", 1) for r in richtig if "=" in r)
        werte = {w: eingabe.get("ziel", {}).get(w, "").strip() == z.strip() for w, z in soll.items()}
        return _stufe(sum(werte.values()) / max(1, len(werte))), werte
    if art == "zahl":
        ist, soll = _zahl(eingabe.get("zahl", "")), _zahl(richtig[0])
        ok = ist is not None and soll is not None and abs(ist - soll) <= max(0.01, abs(soll) * 0.01)
        return (3 if ok else 1), {"zahl": ok}
    raise ValueError(f"nicht automatisch prüfbar: {art}")


def als_text(antwort: dict | None) -> str:
    """Auswahl, Ziele und Vorlage als Markdown (Sensei, Simulation, Mini-Test zeigen kein Antwortfeld)."""
    if not antwort:
        return ""
    teile = []
    if antwort["optionen"]:
        teile.append("\n".join(f"- **{o['wert']}** {o['text']}" for o in antwort["optionen"]))
    if antwort["ziele"]:
        teile.append("Zuordnen zu: " + " · ".join(f"**{z['wert']}** {z['text']}" for z in antwort["ziele"]))
    if antwort["vorlage"]:
        teile.append(antwort["vorlage"])
    return "\n\n".join(teile)


def tabelle(markdown: str) -> list[list[str]]:
    """Markdown-Tabelle → Zeilen mit Zellen (Trennzeile entfällt); leere Zellen werden Eingabefelder.
    Hat die Vorlage nur Beispielzeilen, kommen zwei leere Zeilen zum Ausfüllen dazu."""
    zeilen = []
    for zeile in (markdown or "").strip().splitlines():
        zeile = zeile.strip()
        if not zeile.startswith("|"):
            continue
        zellen = [z.strip() for z in zeile.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", z) for z in zellen if z):
            continue
        zeilen.append(zellen)
    if zeilen and not any("" in z for z in zeilen[1:]):
        zeilen += [[""] * len(zeilen[0]) for _ in range(2)]
    return zeilen
