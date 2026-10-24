"""Wochenrückblick für Heute und den Verlauf: die letzten 7 Tage (mit heute) gegen die 7 davor."""

import sqlite3
from datetime import date, timedelta

from saku.lernen.tagesziel import sicher_geworden

MINDESTENS = 3  # Bewertungen eines Themas in der Woche, damit es als stärkstes oder schwächstes zählt
_TAG = "date(zeitpunkt, 'localtime')"


def woche(con: sqlite3.Connection, heute: date | None = None) -> dict | None:
    """Bewertungen (und die Woche davor), neu sicher gewordene Teilaufgaben, Quote ✓, stärkstes und schwächstes Thema
    (Ebene 2, nach Quote ✓) und Rechenübungen. None, wenn in den letzten 7 Tagen nichts bewertet wurde."""
    heute = heute or date.today()
    von = heute - timedelta(days=6)
    tage = (von.isoformat(), heute.isoformat())
    z = con.execute(f"SELECT SUM({_TAG} >= ?1), SUM({_TAG} >= ?1 AND ergebnis = 3), SUM({_TAG} < ?1) FROM bewertung "
                    f"WHERE {_TAG} BETWEEN ?2 AND ?3", (von.isoformat(), (von - timedelta(days=7)).isoformat(), heute.isoformat())).fetchone()
    if not z[0]:
        return None
    themen = con.execute(
        f"SELECT th.id, th.name, COUNT(*) AS n, AVG(b.ergebnis = 3) AS quote FROM bewertung b "
        "JOIN v_zuordnung z ON z.teilaufgabe_id = b.teilaufgabe_id JOIN thema th ON th.id = z.thema_id AND th.ebene = 2 "
        f"WHERE {_TAG.replace('zeitpunkt', 'b.zeitpunkt')} BETWEEN ?1 AND ?2 GROUP BY th.id HAVING COUNT(*) >= ?3",
        (*tage, MINDESTENS)).fetchall()
    staerkstes = max(themen, key=lambda t: (t["quote"], t["n"]), default=None)
    schwaechstes = min(themen, key=lambda t: (t["quote"], -t["n"]), default=None)
    return {
        "n": z[0], "davor": z[2] or 0, "quote": z[1] / z[0], "sicher": len(sicher_geworden(con, von, heute)),
        "staerkstes": staerkstes,
        "schwaechstes": schwaechstes if schwaechstes and schwaechstes["quote"] < staerkstes["quote"] else None,
        "rechnen": tuple(con.execute(f"SELECT COUNT(*), COALESCE(SUM(richtig), 0) FROM rechenuebung WHERE {_TAG} BETWEEN ?1 AND ?2",
                                     tage).fetchone()),
    }
