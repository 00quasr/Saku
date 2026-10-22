"""Schritt 3: Lösungshinweise segmentieren und den Teilaufgaben zuordnen.

Zugeordnet wird über Termin, Bereich, Aufgabennummer und Kennung. Die Punkte aus den Lösungshinweisen
sind die Referenz der IHK und ersetzen unsichere OCR-Punkte aus den Aufgaben.
"""

import json
import re
import sqlite3
from pathlib import Path

import pymupdf

from saku.pipeline import inventar, segmente

# WiSo: Lösungstabelle „10. a)  2“
TABELLE = re.compile(r"^(\d{1,2})\s*\.\s*(?:([a-h])\s*\))?$")


def _ziele(con: sqlite3.Connection, dok: sqlite3.Row, gruppen: list[list[dict]]) -> list[tuple[int, list[dict]]]:
    """(Prüfung, Aufgaben) je Abschnitt. Stehen die Lösungen beider Prüfungsteile in einem PDF,
    gehört der erste Abschnitt zu Teil 1 (Planen bzw. GA I), der zweite zu Teil 2."""
    if len(gruppen) < 2:
        return [(dok["pruefung_id"], gruppen[0] if gruppen else [])]
    eigene = con.execute("SELECT * FROM pruefung WHERE id = ?", (dok["pruefung_id"],)).fetchone()
    reihe = (inventar.GA1, inventar.GA2) if eigene["format"] == "frueher" else (inventar.PLANEN, inventar.ENTWICKLUNG)
    ids = [z[0] for b in reihe for z in con.execute(
        "SELECT id FROM pruefung WHERE jahr = ? AND saison = ? AND bereich = ?", (eigene["jahr"], eigene["saison"], b))]
    return list(zip(ids, gruppen))


def _teile(con: sqlite3.Connection, p_id: int) -> dict[tuple[int, str], int]:
    return {(z[0], z[1]): z[2] for z in con.execute(
        "SELECT a.nummer, t.kennung, t.id FROM teilaufgabe t JOIN aufgabe a ON a.id = t.aufgabe_id WHERE a.pruefung_id = ?",
        (p_id,))}


def zuordnen(teile: dict[tuple[int, str], int], nr: int, kennung: str) -> list[int]:
    """Teilaufgaben zu einer Lösung „nr kennung“: exakt, sonst Eltern (Aufgabe hat „c“, Lösung „ca“)
    oder Kinder (Aufgabe hat „ca“, „cb“, Lösung nur „c“)."""
    if (nr, kennung) in teile:
        return [teile[nr, kennung]]
    eltern = [t for (n, k), t in teile.items() if n == nr and kennung.startswith(k)]
    return eltern or [t for (n, k), t in teile.items() if n == nr and k.startswith(kennung)]


def _wiso(con: sqlite3.Connection, p_id: int, seiten: list[dict]) -> int:
    """Lösungstabelle der WiSo: neben jeder Aufgabennummer steht rechts die richtige Antwort."""
    teile, anzahl = _teile(con, p_id), 0
    for seite in seiten:
        for x0, y0, x1, y1, text in seite["zeilen"]:
            if not (treffer := TABELLE.match(text.strip())):
                continue
            werte = sorted((z for z in seite["zeilen"] if abs(z[1] - y0) < 4 and x1 < z[0] < x1 + 140), key=lambda z: z[0])
            if not werte:
                continue
            for t_id in zuordnen(teile, int(treffer.group(1)), treffer.group(2) or "a"):
                con.execute("UPDATE teilaufgabe SET loesung_text = ? WHERE id = ?", (f"Lösung: {werte[0][4]}", t_id))
                anzahl += 1
    return anzahl


def _speichern(con: sqlite3.Connection, daten: Path, dok: sqlite3.Row, seiten: list[dict], doc: pymupdf.Document) -> int:
    anzahl = 0
    ordner = inventar.ordner(daten, dok["sha256"])
    gliederung = segmente.gliedern(seiten)
    gruppen = segmente.abschnitte(gliederung)
    if not gruppen:
        return _wiso(con, dok["pruefung_id"], seiten)
    for p_id, aufgaben in _ziele(con, dok, gruppen):
        teile = _teile(con, p_id)
        gesammelt: dict[int, list[dict]] = {}
        for a in aufgaben:
            for t in a["teile"]:
                for t_id in zuordnen(teile, a["nr"], t["kennung"]):
                    gesammelt.setdefault(t_id, []).append(t | {"nr": a["nr"]})
        for t_id, loesungen in gesammelt.items():
            zeilen = [z for l in loesungen for z in l["zeilen"]]
            name = "L" + "-".join(f"{l['nr']}{l['kennung']}" for l in loesungen)
            punkte = [l["punkte"] for l in loesungen]
            con.execute(
                "UPDATE teilaufgabe SET loesung_text = ?, loesung_bilder = ?, punkte = COALESCE(?, punkte) WHERE id = ?",
                (segmente.text(zeilen), json.dumps(segmente.rendern(doc, seiten, zeilen, daten, ordner, name, gliederung["zeilen"], rechts=0.97)),
                 sum(punkte) if None not in punkte else None, t_id))
            anzahl += 1
    return anzahl


def ausfuehren(con: sqlite3.Connection, daten: Path, ohne_ki: bool, ki: str) -> None:
    dokumente = con.execute("SELECT * FROM dokument WHERE art = 'loesungen' AND pruefung_id IS NOT NULL ORDER BY dateiname").fetchall()
    for dok in dokumente:
        pfad = daten / "pdfs" / dok["dateiname"]
        _, seiten = inventar.lesen(daten, pfad, dok["sha256"])
        with pymupdf.open(pfad) as doc:
            anzahl = _speichern(con, daten, dok, seiten, doc)
        print(f"  {anzahl:3d} Lösungen  {dok['dateiname']}", flush=True)
        con.commit()
