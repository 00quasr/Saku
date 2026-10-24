"""Tagesziel, Lernserie, Prüfungsreife und die nächste sinnvolle Aktion (siehe KONZEPT.md, Heute)."""

import math
import sqlite3
from datetime import date, timedelta
from itertools import groupby

from saku.db import einstellung
from saku.lernen.karten import fahrschul, termin_schluessel

# Bundeseinheitliche schriftliche Termine der IT-Berufe (Stand 22.10.2026; Quellen: Handelskammer Hamburg,
# profiling-institut.de, IHK Bonn). Nur Vorschläge: maßgeblich ist die Einladung der eigenen IHK.
# shortcut: von Hand gepflegt; neue Termine nachtragen, sobald die IHKs sie veröffentlichen
IHK_TERMINE = {
    "AP1": [("2027-02-24", "Frühjahr 2027"), ("2027-09-29", "Herbst 2027")],
    "AP2": [("2026-11-25", "Winter 2026/27"), ("2027-04-28", "Sommer 2027"), ("2027-11-24", "Winter 2027/28, voraussichtlich")],
}


def ihk_termine(teil: str, heute: date | None = None) -> list[dict]:
    """Kommende offizielle Termine für AP1 oder AP2: [{datum, name, anzeige}]."""
    heute = heute or date.today()
    return [{"datum": d, "name": n, "anzeige": date.fromisoformat(d).strftime("%d.%m.%Y")}
            for d, n in IHK_TERMINE.get(teil, []) if date.fromisoformat(d) >= heute]


# Mindestens so viele neue Teilaufgaben am Tag (auch ohne Termin); mehr, wenn der Termin es verlangt.
# shortcut: fest; bei Bedarf in den Einstellungen anbieten
NEU_MINDESTENS = 10

_HEUTE = "date(zeitpunkt, 'localtime') = date('now', 'localtime')"

# Neue Teilaufgaben in der Reihenfolge des Lernpfads (frühe Station zuerst, ohne Station ans Ende)
NEU_IM_PFAD_SQL = """
SELECT v.teilaufgabe_id
FROM v_teilaufgabe v
JOIN teilaufgabe t ON t.id = v.teilaufgabe_id
LEFT JOIN v_zuordnung z    ON z.teilaufgabe_id = v.teilaufgabe_id
LEFT JOIN station_thema st ON st.thema_id = z.thema_id
LEFT JOIN v_station s      ON s.id = st.station_id
WHERE v.status = 'neu'
GROUP BY v.teilaufgabe_id
ORDER BY MIN(COALESCE(s.position, 1e9)), v.termin_index DESC, v.aufgabe_nr, t.position
"""


def tage_bis_pruefung(con: sqlite3.Connection, heute: date | None = None) -> int | None:
    termin = einstellung(con, termin_schluessel(con))
    return (date.fromisoformat(termin) - (heute or date.today())).days if termin else None


def lerntage(con: sqlite3.Connection, heute: date | None = None) -> int | None:
    """Tage bis zur Prüfung − Puffer, mindestens 1; None ohne Termin."""
    tage = tage_bis_pruefung(con, heute)
    return None if tage is None else max(1, tage - int(einstellung(con, "puffer_tage", "7") or 0))


def neu_am_tag(neue: int, lerntage: int | None) -> int:
    """aufrunden(neue ÷ Lerntage), mindestens NEU_MINDESTENS, höchstens alle neuen."""
    return min(max(NEU_MINDESTENS, math.ceil(neue / lerntage) if lerntage else 0), neue)


def tagesziel(con: sqlite3.Connection, heute: date | None = None) -> dict:
    """Lerntage = Tage bis Prüfung − Puffer (mind. 1), Neu heute = aufrunden(neue ÷ Lerntage), mindestens NEU_MINDESTENS,
    Heute = Neu heute + fällige Wiederholungen. Gerechnet ab Tagesbeginn, damit das Ziel beim Lernen stehen bleibt."""
    # heute bewertete Teilaufgaben; neu = die erste Bewertung überhaupt war heute
    bewertet = con.execute(
        "SELECT date(MIN(zeitpunkt), 'localtime') = date('now', 'localtime') AS neu FROM bewertung "
        "GROUP BY teilaufgabe_id HAVING date(MAX(zeitpunkt), 'localtime') = date('now', 'localtime')"
    ).fetchall()
    neu_erledigt = sum(z["neu"] for z in bewertet)
    wdh_erledigt = len(bewertet) - neu_erledigt

    neue = con.execute("SELECT COUNT(*) FROM v_teilaufgabe WHERE status = 'neu'").fetchone()[0]
    neu_ziel = neu_am_tag(neue + neu_erledigt, lerntage(con, heute))
    neu_offen = min(neue, max(0, neu_ziel - neu_erledigt))

    wdh_offen = con.execute(
        f"SELECT COUNT(*) FROM v_faellig WHERE teilaufgabe_id NOT IN (SELECT teilaufgabe_id FROM bewertung WHERE {_HEUTE})"
    ).fetchone()[0]
    return {
        "neu": neu_ziel,
        "wiederholungen": wdh_offen + wdh_erledigt,
        "ziel": neu_ziel + wdh_offen + wdh_erledigt,
        "erledigt": neu_erledigt + wdh_erledigt,
        "neu_offen": neu_offen,
        "wdh_offen": wdh_offen,
        "erreicht": neu_offen == 0 and wdh_offen == 0,
    }


def runde(con: sqlite3.Connection, ohne: set[int] | frozenset[int] = frozenset(), ziel: dict | None = None,
          neu: int | None = None) -> list[int]:
    """Weiterlernen: zuerst fällige Wiederholungen, dann der Fehlerkorb, dann neue Teilaufgaben im Pfad
    (so viele, wie das Tagesziel noch offen hat, oder `neu` für eine Extra-Runde)."""
    ziel = ziel or tagesziel(con)
    wiederholen = [z[0] for z in con.execute(
        "SELECT teilaufgabe_id FROM karte WHERE teilaufgabe_id IN (SELECT teilaufgabe_id FROM v_teilaufgabe) AND status <> 'neu' AND (status = 'rot' OR ("
        f"  faellig_am <= datetime('now') AND teilaufgabe_id NOT IN (SELECT teilaufgabe_id FROM bewertung WHERE {_HEUTE})"
        ")) ORDER BY status = 'rot', faellig_am"
    )]
    neue = [z[0] for z in con.execute(NEU_IM_PFAD_SQL) if z[0] not in ohne]
    return [i for i in wiederholen if i not in ohne] + neue[:ziel["neu_offen"] if neu is None else neu]


def naechste_aktion(con: sqlite3.Connection, ziel: dict) -> tuple[str, int] | None:
    """(Art, Anzahl) der nächsten sinnvollen Aktion: wiederholen, fehler oder neu; None, wenn nichts ansteht."""
    if ziel["wdh_offen"]:
        return "wiederholen", ziel["wdh_offen"]
    rot = con.execute("SELECT COUNT(*) FROM karte WHERE status = 'rot' AND teilaufgabe_id IN (SELECT teilaufgabe_id FROM v_teilaufgabe)").fetchone()[0]
    if rot:
        return "fehler", rot
    if ziel["neu_offen"]:
        return "neu", ziel["neu_offen"]
    return None


def heute_sicher(con: sqlite3.Connection) -> list[int]:
    """Teilaufgaben, die heute sicher geworden sind: jetzt grün, vor heute laut Verlauf noch nicht."""
    verlauf = con.execute(
        f"SELECT b.teilaufgabe_id, b.ergebnis, {_HEUTE.replace('zeitpunkt', 'b.zeitpunkt')} AS heute "
        "FROM bewertung b JOIN karte k ON k.teilaufgabe_id = b.teilaufgabe_id "
        f"WHERE k.status = 'gruen' AND b.teilaufgabe_id IN (SELECT teilaufgabe_id FROM bewertung WHERE {_HEUTE}) "
        "ORDER BY b.teilaufgabe_id, b.zeitpunkt, b.id").fetchall()
    ids = []
    for t_id, zeilen in groupby(verlauf, key=lambda z: z["teilaufgabe_id"]):
        status, serie = "neu", 0
        for z in zeilen:
            if z["heute"]:
                break
            status, serie = fahrschul(serie, z["ergebnis"])
        if status != "gruen":
            ids.append(t_id)
    return ids


def lernserie(con: sqlite3.Connection, heute: date | None = None) -> int:
    """Tage in Folge mit mindestens einer Bewertung; heute zählt mit, sobald heute gelernt wurde."""
    heute = heute or date.today()
    tage = {date.fromisoformat(z[0]) for z in con.execute("SELECT tag FROM v_lerntage")}
    tag = heute if heute in tage else heute - timedelta(days=1)
    serie = 0
    while tag in tage:
        serie += 1
        tag -= timedelta(days=1)
    return serie


def pruefungsreife(con: sqlite3.Connection) -> tuple[float, bool]:
    """(Prozent, mankai): volle Blüte ab 80 % und wenn die letzten zwei Simulationen bestanden sind."""
    prozent = con.execute("SELECT prozent FROM v_pruefungsreife").fetchone()[0] or 0
    letzte = [z[0] for z in con.execute(
        "SELECT bestanden FROM simulation WHERE note IS NOT NULL ORDER BY gestartet_am DESC, id DESC LIMIT 2"
    )]
    return prozent, prozent >= 80 and letzte == [1, 1]
