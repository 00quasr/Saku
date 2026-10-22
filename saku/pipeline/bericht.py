"""Schritt 8: Zusammenfassung im Terminal (Details zeigt Bunseki)."""

import sqlite3
from pathlib import Path

from rich.console import Console
from rich.table import Table

KURZ = {"Planen eines Softwareproduktes": "Planen", "Entwicklung und Umsetzung von Algorithmen": "Entwicklung",
        "Konzeption und Administration von IT-Systemen": "Konzeption", "Analyse und Entwicklung von Netzwerken": "Netzwerke",
        "Einrichten eines IT-gestützten Arbeitsplatzes": "Arbeitsplatz",
        "Wirtschafts- und Sozialkunde": "WiSo", "Ganzheitliche Aufgabe I": "GA I", "Ganzheitliche Aufgabe II": "GA II"}


def _zahl(n: int | None) -> str:
    return f"{n or 0:,}".replace(",", ".")


def ausfuehren(con: sqlite3.Connection, daten: Path, ohne_ki: bool, ki: str) -> None:
    konsole = Console()
    tabelle = Table("Termin", "Teil", "Beruf", "Bereich", "Aufg.", "Teile", "Punkte", "Lösung", "Neu aufgebaut", "Dokumente",
                    title="Prüfungen", title_justify="left")
    for p in con.execute("""
        SELECT p.id, p.jahr, p.saison, p.bereich, p.format, p.teil, p.beruf, SUM(t.inhalt IS NOT NULL) AS aufbereitet,
               (SELECT COUNT(*) FROM aufgabe a WHERE a.pruefung_id = p.id) AS aufgaben,
               COUNT(t.id) AS teile, SUM(t.punkte IS NOT NULL) AS mit_punkten,
               SUM(t.loesung_text IS NOT NULL OR t.loesung_bilder <> '[]') AS mit_loesung,
               (SELECT group_concat(d.art, ', ') FROM dokument d WHERE d.pruefung_id = p.id) AS dokumente
        FROM pruefung p LEFT JOIN aufgabe a ON a.pruefung_id = p.id LEFT JOIN teilaufgabe t ON t.aufgabe_id = a.id
        GROUP BY p.id ORDER BY p.teil, p.jahr, p.saison IN ('Winter', 'Herbst'), p.beruf, p.bereich"""):
        termin = f"{p['saison']} {p['jahr']}" + (f"/{(p['jahr'] + 1) % 100:02d}" if p["saison"] == "Winter" else "")
        tabelle.add_row(termin + (" alt" if p["format"] == "frueher" else ""), p["teil"], p["beruf"], KURZ.get(p["bereich"], p["bereich"]),
                        str(p["aufgaben"]), str(p["teile"]), str(p["mit_punkten"] or 0), str(p["mit_loesung"] or 0),
                        str(p["aufbereitet"] or 0), p["dokumente"] or "")
    konsole.print(tabelle)

    g = con.execute("SELECT COUNT(*), SUM(punkte IS NOT NULL), SUM(loesung_text IS NOT NULL OR loesung_bilder <> '[]'), "
                    "SUM(id NOT IN (SELECT teilaufgabe_id FROM teilaufgabe_thema)) FROM teilaufgabe").fetchone()
    if g[0]:
        konsole.print(f"[bold]{g[0]}[/] Teilaufgaben · mit Punkten {100 * g[1] / g[0]:.0f} % · "
                      f"mit Lösung {100 * g[2] / g[0]:.0f} % · ohne Thema {g[3]}")
    ki_zahlen = con.execute("SELECT COUNT(*), SUM(aus_cache), SUM(tokens_ein), SUM(tokens_aus) FROM ki_aufruf").fetchone()
    if ki_zahlen[0]:
        konsole.print(f"KI: {_zahl(ki_zahlen[0])} Aufrufe, davon {_zahl(ki_zahlen[1])} aus dem Cache · "
                      f"{_zahl(ki_zahlen[2])} Tokens rein, {_zahl(ki_zahlen[3])} raus")
    pfade = ", ".join(f"{z[0]} {z[1]}" for z in con.execute("SELECT pfad, COUNT(*) FROM station GROUP BY pfad"))
    konsole.print(f"Lernpfade: {pfade or 'keine'} Stationen · Details unter Analyse (python -m saku start)")
