"""Prüfungssimulation (Shiken): Zusammenstellung, Umrechnung auf 100 Punkte und IHK-Notenschlüssel."""

import json
import math
import random
import sqlite3
from statistics import median

from saku.lernen import antwort
from saku.lernen.karten import bewerten, ergebnis_aus_punkten

# (ab Punkten, Note) nach KONZEPT.md
NOTENSCHLUESSEL = [(92, 1), (81, 2), (67, 3), (50, 4), (30, 5), (0, 6)]
NOTEN = {1: "sehr gut", 2: "gut", 3: "befriedigend", 4: "ausreichend", 5: "mangelhaft", 6: "ungenügend"}
BESTANDEN_AB = 50

_ENDE = "datetime(gestartet_am, '+' || dauer_min || ' minutes')"


def note(punkte: float) -> int:
    return next(n for grenze, n in NOTENSCHLUESSEL if punkte >= grenze)


def umrechnen(erreicht: float, moeglich: float) -> int:
    """Auf 100 Punkte umgerechnet, kaufmännisch auf ganze Punkte gerundet (wie bei der IHK)."""
    if not moeglich:
        return 0
    return math.floor(round(erreicht * 100 / moeglich, 6) + 0.5)


def aufbau(con: sqlite3.Connection, bereich: str) -> tuple[int, int]:
    """(Dauer in Minuten, Zahl der Aufgaben) wie in den echten Prüfungen des Bereichs (Median)."""
    pruefungen = con.execute(
        "SELECT p.id, p.dauer_min, (SELECT COUNT(*) FROM aufgabe a WHERE a.pruefung_id = p.id) AS aufgaben "
        "FROM pruefung p WHERE p.id IN (SELECT pruefung_id FROM v_teilaufgabe WHERE bereich = ?)", (bereich,)).fetchall()
    if not pruefungen:
        raise ValueError(f"Keine Prüfungen im Bereich {bereich!r}")
    return int(median(p["dauer_min"] or 90 for p in pruefungen)), max(1, round(median(p["aufgaben"] for p in pruefungen)))


def zusammenstellen(con: sqlite3.Connection, bereich: str, zufall: random.Random | None = None) -> int:
    """Neue Prüfung aus ganzen Aufgaben verschiedener Jahrgänge; bevorzugt, was noch nicht sitzt.
    Dauer und Zahl der Aufgaben richten sich nach den echten Prüfungen des Bereichs."""
    zufall = zufall or random.Random()
    dauer, anzahl = aufbau(con, bereich)

    # offen = Anteil der Punkte, die noch nicht sitzen (im Aufbau zählt halb)
    aufgaben = con.execute("""
        SELECT aufgabe_id, pruefung_id, aufgabe_nr,
               SUM(COALESCE(punkte, 0) * CASE status WHEN 'gruen' THEN 0 WHEN 'gelb' THEN 0.5 ELSE 1 END)
                 / NULLIF(SUM(COALESCE(punkte, 0)), 0) AS offen
        FROM v_teilaufgabe WHERE bereich = ? GROUP BY aufgabe_id
    """, (bereich,)).fetchall()
    kandidaten = sorted(aufgaben, key=lambda a: (-(a["offen"] or 0), zufall.random()))

    gewaehlt, genutzt = [], set()
    for a in kandidaten:  # erst höchstens eine Aufgabe je Prüfung, also aus verschiedenen Jahrgängen
        if len(gewaehlt) < anzahl and a["pruefung_id"] not in genutzt:
            gewaehlt.append(a)
            genutzt.add(a["pruefung_id"])
    for a in kandidaten:  # gibt es zu wenige Prüfungen, auch mehrere aus einer
        if len(gewaehlt) < anzahl and a not in gewaehlt:
            gewaehlt.append(a)
    gewaehlt.sort(key=lambda a: a["aufgabe_nr"])  # Aufbau wie im Original: Aufgabe 1 zuerst

    sim_id = con.execute("INSERT INTO simulation (bereich, dauer_min) VALUES (?, ?)", (bereich, dauer)).lastrowid or 0
    ids = [z[0] for a in gewaehlt
           for z in con.execute("SELECT id FROM teilaufgabe WHERE aufgabe_id = ? ORDER BY position", (a["aufgabe_id"],))]
    con.executemany("INSERT INTO simulation_teilaufgabe (simulation_id, teilaufgabe_id, position) VALUES (?, ?, ?)",
                    [(sim_id, t_id, pos) for pos, t_id in enumerate(ids)])
    con.commit()
    return sim_id


def laufende(con: sqlite3.Connection) -> sqlite3.Row | None:
    """Die laufende Simulation samt Restzeit in Sekunden (abgelaufene werden vorher beendet)."""
    con.execute(f"UPDATE simulation SET beendet_am = {_ENDE} WHERE beendet_am IS NULL AND {_ENDE} <= datetime('now')")
    con.commit()
    return con.execute(
        f"SELECT *, CAST((julianday({_ENDE}) - julianday('now')) * 86400 AS INTEGER) AS rest_s "
        "FROM simulation WHERE beendet_am IS NULL ORDER BY id DESC LIMIT 1").fetchone()


def auswerten(con: sqlite3.Connection, sim_id: int, punkte: dict[int, float]) -> None:
    """Speichert die vergebenen Punkte, Note und Ergebnis; jede Teilaufgabe fließt als Bewertung in den Lernstand."""
    zeilen = con.execute(
        "SELECT st.teilaufgabe_id, st.antwort, COALESCE(t.punkte, 0) AS maximal FROM simulation_teilaufgabe st "
        "JOIN teilaufgabe t ON t.id = st.teilaufgabe_id WHERE st.simulation_id = ?", (sim_id,)).fetchall()
    erreicht = moeglich = 0.0
    for z in zeilen:
        p = min(max(punkte.get(z["teilaufgabe_id"], 0.0), 0.0), z["maximal"])
        con.execute("UPDATE simulation_teilaufgabe SET punkte_erreicht = ?, quelle = 'selbst' "
                    "WHERE simulation_id = ? AND teilaufgabe_id = ?", (p, sim_id, z["teilaufgabe_id"]))
        erreicht, moeglich = erreicht + p, moeglich + z["maximal"]
        if z["maximal"]:
            bewerten(con, z["teilaufgabe_id"], ergebnis_aus_punkten(p, z["maximal"]), quelle="simulation", antwort=_als_text(z["antwort"]))
    punkte_100 = umrechnen(erreicht, moeglich)
    con.execute(
        "UPDATE simulation SET beendet_am = COALESCE(beendet_am, datetime('now')), punkte_erreicht = ?, "
        "punkte_moeglich = ?, note = ?, bestanden = ? WHERE id = ?",
        (erreicht, moeglich, note(punkte_100), int(punkte_100 >= BESTANDEN_AB), sim_id))
    con.commit()


def _als_text(eigene: str | None) -> str | None:
    """Anklickbare Antworten liegen als JSON vor (antwort.eingabe); in den Verlauf kommt „Gewählt: …“."""
    try:
        wert = json.loads(eigene or "")
    except ValueError:
        return eigene
    return antwort.zusammenfassung(wert) if isinstance(wert, dict) and "wahl" in wert else eigene


def kosten(con: sqlite3.Connection, sim_id: int, anzahl: int = 2) -> list[str]:
    """Die Themen, die in der Simulation die meisten Punkte gekostet haben."""
    return [z[0] for z in con.execute("""
        SELECT th.name, SUM((COALESCE(t.punkte, 0) - COALESCE(st.punkte_erreicht, 0)) * tt.gewicht) AS verlust
        FROM simulation_teilaufgabe st
        JOIN teilaufgabe t        ON t.id = st.teilaufgabe_id
        JOIN teilaufgabe_thema tt ON tt.teilaufgabe_id = t.id
        JOIN thema th             ON th.id = tt.thema_id
        WHERE st.simulation_id = ? GROUP BY th.id HAVING verlust > 0 ORDER BY verlust DESC LIMIT ?
    """, (sim_id, anzahl))]
