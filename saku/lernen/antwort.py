"""Anklickbare Aufgaben: automatisch prüfen, was sich prüfen lässt (Auswahl, Reihenfolge, Zuordnung, Zahl).
antwort ist das JSON aus dem Schritt aufbereiten: {art, optionen, ziele, richtig, einheit, vorlage}."""

import re

AUTOMATISCH = ("einfach", "mehrfach", "reihenfolge", "zuordnung", "zahl")


def pruefbar(antwort: dict | None) -> bool:
    return bool(antwort) and antwort["art"] in AUTOMATISCH and bool(antwort["richtig"])


def zahl(text: str | None) -> float | None:
    """Eingetippte Zahl, deutsch geschrieben: „1,5“, „1.024“ (= 1024), „1 024“, „1.234,5“, „2^16“; Einheit dahinter egal."""
    text = (text or "").replace("\u2212", "-").replace("\xa0", " ").replace("\u202f", " ")
    if potenz := re.match(r"\s*(\d+)\s*\^\s*(\d{1,3})", text):
        return float(int(potenz[1]) ** int(potenz[2]))
    treffer = re.search(r"-?\d[\d.,\s]*", text)
    if not treffer:
        return None
    t = re.sub(r"\s", "", treffer.group()).rstrip(".,")
    if "," in t and "." in t and t.rfind(".") > t.rfind(","):  # englisch: 1,234.5
        t = t.replace(",", "")
    elif "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?[1-9]\d{0,2}(\.\d{3})+", t):  # nur Tausenderpunkte
        t = t.replace(".", "")
    try:
        return float(t)
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
        ist = zahl(eingabe.get("zahl", ""))
        try:  # die Lösung steht mit Punkt als Dezimaltrenner da („1.125“ heißt 1,125)
            soll = float(richtig[0])
        except ValueError:
            soll = zahl(richtig[0])
        ok = ist is not None and soll is not None and abs(ist - soll) <= max(0.01, abs(soll) * 0.01)
        return (3 if ok else 1), {"zahl": ok}
    raise ValueError(f"nicht automatisch prüfbar: {art}")


def eingabe(form, praefix: str = "") -> dict:
    """Eingabe für auswerten aus einem Formular (MultiDict); praefix trennt mehrere Felder auf einer Seite (Simulation)."""
    def felder(art: str) -> dict:
        return {k.removeprefix(praefix + art): v for k, v in form.items() if k.startswith(praefix + art)}
    return {"wahl": form.getlist(praefix + "wahl"), "zahl": form.get(praefix + "zahl", ""),
            "position": felder("position-"), "ziel": felder("ziel-")}


def zusammenfassung(eingabe: dict) -> str:
    """„Gewählt: A, C“ für Verlauf und Sensei; leer, wenn nichts eingegeben ist."""
    text = ", ".join(eingabe["wahl"]) or eingabe["zahl"] or ", ".join(
        f"{k}={v}" for k, v in (eingabe["position"] | eingabe["ziel"]).items() if v)
    return f"Gewählt: {text}" if text else ""


def punkte(ergebnis: int, moeglich: float) -> float:
    """Punkte für ein automatisches Ergebnis, auf halbe Punkte gerundet: alles, die Hälfte oder nichts."""
    return round(moeglich * {3: 1, 2: 0.5, 1: 0}[ergebnis] * 2) / 2


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
