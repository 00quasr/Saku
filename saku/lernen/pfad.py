"""Lernpfad (Michi): Stationen, Wachstumsstufe, Freischaltung und Mini-Test."""

import sqlite3

from saku.db import einstellung
from saku.lernen.karten import bewerten, ergebnis_aus_punkten

STUFEN = {"samen": ("種", "Samen"), "keim": ("芽", "Keim"), "knospe": ("蕾", "Knospe"), "bluete": ("花", "Blüte")}

# Teilaufgaben einer Station: alles, was ihren Themen (samt Unterthemen) zugeordnet ist
_TEILAUFGABEN = """
SELECT DISTINCT z.teilaufgabe_id FROM station_thema st JOIN v_zuordnung z ON z.thema_id = st.thema_id
WHERE st.station_id = ?
"""


def stufe(beherrschung: float) -> str:
    """Wie v_thema_lernstand: 種 0 %, 芽 bis 39 %, 蕾 bis 79 %, 花 ab 80 %."""
    return "samen" if beherrschung <= 0 else "keim" if beherrschung < 0.4 else "knospe" if beherrschung < 0.8 else "bluete"


def stationen(con: sqlite3.Connection) -> list[dict]:
    """Alle Stationen in Pfad-Reihenfolge. Gesperrt ist alles nach der ersten nicht bestandenen Station."""
    zeilen = con.execute("""
        WITH ta AS (
            SELECT DISTINCT st.station_id, z.teilaufgabe_id
            FROM station_thema st JOIN v_zuordnung z ON z.thema_id = st.thema_id
        ), zahlen AS (
            SELECT ta.station_id, COUNT(*) AS gesamt, SUM(v.status = 'gruen') AS sicher
            FROM ta JOIN v_teilaufgabe v ON v.teilaufgabe_id = ta.teilaufgabe_id GROUP BY ta.station_id
        ), stand AS (
            SELECT st.station_id, group_concat(st.thema_id) AS themen,
                   (SUM(l.punkte_gruen) + 0.5 * SUM(l.punkte_gelb)) / NULLIF(SUM(l.punkte_gesamt), 0) AS beherrschung
            FROM station_thema st JOIN v_thema_lernstand l ON l.thema_id = st.thema_id GROUP BY st.station_id
        )
        SELECT s.id, s.position, s.titel, stand.themen,
               COALESCE(zahlen.gesamt, 0) AS gesamt, COALESCE(zahlen.sicher, 0) AS sicher,
               COALESCE(stand.beherrschung, 0) AS beherrschung,
               EXISTS (SELECT 1 FROM stationstest x WHERE x.station_id = s.id AND x.bestanden = 1) AS bestanden
        FROM v_station s
        LEFT JOIN zahlen ON zahlen.station_id = s.id
        LEFT JOIN stand  ON stand.station_id = s.id
        ORDER BY s.position
    """).fetchall()
    liste, frei = [], True
    for z in zeilen:
        s = dict(z) | {"themen": [int(t) for t in (z["themen"] or "").split(",") if t]}
        s["stufe"] = stufe(s["beherrschung"])
        s["bestanden"] = bool(s["bestanden"]) or not s["gesamt"]  # ohne Teilaufgaben gibt es nichts zu testen
        s["gesperrt"], s["aktuell"] = not frei, frei and not s["bestanden"]
        frei = frei and s["bestanden"]
        liste.append(s)
    return liste


def teilaufgaben(con: sqlite3.Connection, station_id: int) -> list[int]:
    """Teilaufgaben der Station, neueste Prüfung zuerst."""
    return [z[0] for z in con.execute(
        f"SELECT teilaufgabe_id FROM v_teilaufgabe WHERE teilaufgabe_id IN ({_TEILAUFGABEN}) "
        "ORDER BY termin_index DESC, aufgabe_nr, kennung", (station_id,))]


def testaufgaben(con: sqlite3.Connection, station_id: int, anzahl: int = 5) -> list[int]:
    """Fünf zufällige Teilaufgaben der Station (mit Punkten, sonst lässt sich nichts vergeben)."""
    return [z[0] for z in con.execute(
        f"SELECT id FROM teilaufgabe WHERE punkte > 0 AND id IN ({_TEILAUFGABEN}) ORDER BY random() LIMIT ?",
        (station_id, anzahl),
    )]


def test_auswerten(con: sqlite3.Connection, station_id: int, punkte: dict[int, float]) -> dict:
    """Speichert den Mini-Test: bestanden ab stationstest_schwelle; jede Teilaufgabe zählt als Bewertung."""
    erlaubt = set(teilaufgaben(con, station_id))
    maximal = dict(con.execute(
        f"SELECT id, punkte FROM teilaufgabe WHERE id IN ({','.join('?' * len(punkte))})", list(punkte)
    ).fetchall()) if punkte else {}
    erreicht = moeglich = 0.0
    for t_id, p in punkte.items():
        if t_id not in erlaubt or not maximal.get(t_id):
            continue
        p = min(max(p, 0.0), maximal[t_id])
        erreicht, moeglich = erreicht + p, moeglich + maximal[t_id]
        bewerten(con, t_id, ergebnis_aus_punkten(p, maximal[t_id]), quelle="stationstest")
    schwelle = float(einstellung(con, "stationstest_schwelle", "0.8"))
    bestanden = moeglich > 0 and erreicht / moeglich >= schwelle
    con.execute(
        "INSERT INTO stationstest (station_id, beendet_am, punkte_erreicht, punkte_moeglich, bestanden) "
        "VALUES (?, datetime('now'), ?, ?, ?)", (station_id, erreicht, moeglich, int(bestanden)))
    con.commit()
    return {"erreicht": erreicht, "moeglich": moeglich, "bestanden": bestanden, "schwelle": schwelle}
