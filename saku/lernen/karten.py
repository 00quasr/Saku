"""Fahrschul-Regeln und FSRS: eine Bewertung aktualisiert Status, Serie und Wiederholungstermin."""

import json
import re
import sqlite3
from datetime import date, datetime, timezone

from fsrs import Card, Rating, Scheduler

from saku.db import einstellung, liste
from saku.sensei import vektoren

# Eine Teilaufgabe samt Aufgabe, Prüfung und Lernstand – für Keiko, Mini-Test und Simulation
TEILAUFGABE_SQL = """
SELECT v.teilaufgabe_id, v.teilaufgabe_id AS id, v.kennung, v.punkte, v.aufgabe_id, v.aufgabe_nr,
       v.pruefung_id, v.termin, v.bereich, v.status,
       t.text, t.bilder, t.loesung_text, t.loesung_bilder, t.inhalt, t.antwort, t.loesung_inhalt,
       a.titel AS aufgabe_titel, a.einleitung, a.einleitung_bilder, a.einleitung_inhalt,
       p.ausgangssituation, p.ausgangssituation_bilder, p.ausgangssituation_inhalt,
       COALESCE(k.markiert, 0) AS markiert, t.loesung_sql,
       EXISTS (SELECT 1 FROM sql_sandbox s WHERE s.aufgabe_id = v.aufgabe_id) AS sandbox
FROM v_teilaufgabe v
JOIN teilaufgabe t ON t.id = v.teilaufgabe_id
JOIN aufgabe a     ON a.id = v.aufgabe_id
JOIN pruefung p    ON p.id = v.pruefung_id
LEFT JOIN karte k  ON k.teilaufgabe_id = v.teilaufgabe_id
"""
_LISTEN = ("bilder", "loesung_bilder", "einleitung_bilder", "ausgangssituation_bilder")


def termin_schluessel(con: sqlite3.Connection) -> str:
    """Jeder Prüfungsteil hat seinen eigenen Termin."""
    return "pruefungstermin_ap1" if einstellung(con, "teil", "AP2") == "AP1" else "pruefungstermin"


def lade(con: sqlite3.Connection, ids: list[int]) -> list[dict]:
    """Teilaufgaben in der Reihenfolge von ids, Bildlisten schon als Listen."""
    if not ids:
        return []
    zeilen = con.execute(
        f"{TEILAUFGABE_SQL} WHERE v.teilaufgabe_id IN ({','.join('?' * len(ids))})", ids
    ).fetchall()
    nach_id = {z["id"]: dict(z) | {s: liste(z[s]) for s in _LISTEN} | {"antwort": json.loads(z["antwort"] or "null")}
               for z in zeilen}
    return [nach_id[i] for i in ids if i in nach_id]


def fahrschul(serie: int, ergebnis: int) -> tuple[str, int]:
    """Neuer Status und neue Serie: sicher erst nach zweimal „Gewusst“ in Folge."""
    if ergebnis == 1:
        return "rot", 0
    if ergebnis == 2:
        return "gelb", 0
    serie += 1
    return ("gruen" if serie >= 2 else "gelb"), serie


def ergebnis_aus_punkten(erreicht: float, moeglich: float) -> int:
    """Punkte als Bewertung: ab 80 % gewusst, ab 40 % teilweise (wie der Vorschlag von Sensei)."""
    anteil = erreicht / moeglich if moeglich else 0
    return 3 if anteil >= 0.8 else 2 if anteil >= 0.4 else 1


def scheduler(con: sqlite3.Connection, heute: date | None = None) -> Scheduler:
    """Das längste Intervall endet am Prüfungstermin; ohne Termin gilt der Standard von FSRS."""
    termin = einstellung(con, termin_schluessel(con))
    if not termin:
        return Scheduler(enable_fuzzing=False)
    tage = (date.fromisoformat(termin) - (heute or date.today())).days
    return Scheduler(maximum_interval=max(1, tage), enable_fuzzing=False)


def sqlite_zeit(zeitpunkt: datetime) -> str:
    return zeitpunkt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def bewerten(con: sqlite3.Connection, teilaufgabe_id: int, ergebnis: int, *, quelle: str = "selbst",
             dauer_s: int | None = None, antwort: str | None = None, punkte: float | None = None,
             jetzt: datetime | None = None) -> tuple[str, str]:
    """Speichert eine Bewertung (1, 2, 3) und gibt (alter Status, neuer Status) zurück."""
    if ergebnis not in (1, 2, 3):
        raise ValueError(f"Bewertung muss 1, 2 oder 3 sein, nicht {ergebnis!r}")
    jetzt = jetzt or datetime.now(timezone.utc)
    karte = con.execute("SELECT status, serie, fsrs FROM karte WHERE teilaufgabe_id = ?", (teilaufgabe_id,)).fetchone()
    alt = karte["status"] if karte else "neu"
    status = _speichern_karte(con, "karte", "teilaufgabe_id", teilaufgabe_id, karte, ergebnis, jetzt)
    con.execute(
        "INSERT INTO bewertung (teilaufgabe_id, zeitpunkt, ergebnis, quelle, dauer_s, antwort, punkte) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (teilaufgabe_id, sqlite_zeit(jetzt), ergebnis, quelle, dauer_s, antwort or None, punkte),
    )
    con.commit()
    return alt, status


def _speichern_karte(con: sqlite3.Connection, tabelle: str, spalte: str, schluessel: int, karte, ergebnis: int,
                     jetzt: datetime) -> str:
    """Fahrschul-Status und FSRS-Termin nach einer Bewertung in karte bzw. begriff_karte schreiben."""
    status, serie = fahrschul(karte["serie"] if karte else 0, ergebnis)
    fsrs_karte = Card.from_dict(json.loads(karte["fsrs"])) if karte and karte["fsrs"] else Card()
    fsrs_karte, _ = scheduler(con, jetzt.astimezone().date()).review_card(fsrs_karte, Rating(ergebnis), jetzt)
    con.execute(
        f"INSERT INTO {tabelle} ({spalte}, status, serie, fsrs, faellig_am, geaendert_am) VALUES (?, ?, ?, ?, ?, ?) "
        f"ON CONFLICT ({spalte}) DO UPDATE SET status = excluded.status, serie = excluded.serie, "
        "fsrs = excluded.fsrs, faellig_am = excluded.faellig_am, geaendert_am = excluded.geaendert_am",
        (schluessel, status, serie, json.dumps(fsrs_karte.to_dict()), sqlite_zeit(fsrs_karte.due), sqlite_zeit(jetzt)),
    )
    return status


def zuruecknehmen(con: sqlite3.Connection, teilaufgabe_id: int) -> bool:
    """„Zurück“ in Üben: War die letzte Bewertung überhaupt (heute) diese Teilaufgabe, fällt sie weg und die Karte
    entsteht aus dem übrigen Verlauf neu. Sonst bleibt alles, z. B. nach Überspringen."""
    letzte = con.execute("SELECT id, teilaufgabe_id, date(zeitpunkt, 'localtime') = date('now', 'localtime') AS heute "
                         "FROM bewertung ORDER BY id DESC LIMIT 1").fetchone()
    if not letzte or letzte["teilaufgabe_id"] != teilaufgabe_id or not letzte["heute"]:
        return False
    con.execute("DELETE FROM bewertung WHERE id = ?", (letzte["id"],))
    con.execute("UPDATE karte SET status = 'neu', serie = 0, fsrs = NULL, faellig_am = NULL WHERE teilaufgabe_id = ?", (teilaufgabe_id,))
    # shortcut: der Verlauf wird mit dem heutigen Prüfungstermin nachgespielt; bei geändertem Termin weicht FSRS minimal ab
    for z in con.execute("SELECT ergebnis, zeitpunkt FROM bewertung WHERE teilaufgabe_id = ? ORDER BY zeitpunkt, id",
                         (teilaufgabe_id,)).fetchall():
        karte = con.execute("SELECT status, serie, fsrs FROM karte WHERE teilaufgabe_id = ?", (teilaufgabe_id,)).fetchone()
        _speichern_karte(con, "karte", "teilaufgabe_id", teilaufgabe_id, karte, z["ergebnis"],
                         datetime.fromisoformat(z["zeitpunkt"]).replace(tzinfo=timezone.utc))
    con.commit()
    return True


# Grundwissen: Begriffe mit Definition aus dem aktuellen Umfang; fällige zuerst, dann neue nach Häufigkeit
_BEGRIFFE_SQL = """
SELECT b.id, b.name, b.erklaerung, COALESCE(k.status, 'neu') AS status, k.faellig_am, COUNT(DISTINCT tb.teilaufgabe_id) AS n
FROM begriff b JOIN teilaufgabe_begriff tb ON tb.begriff_id = b.id
JOIN v_teilaufgabe v ON v.teilaufgabe_id = tb.teilaufgabe_id
LEFT JOIN begriff_karte k ON k.begriff_id = b.id
WHERE b.erklaerung IS NOT NULL AND b.erklaerung <> ''
GROUP BY b.id
"""


def begriffe(con: sqlite3.Connection, ohne: list[int]) -> dict:
    """Nächste Begriffs-Karte und wie viele fällig bzw. neu sind (ohne die schon in dieser Runde gezeigten)."""
    zeilen = [z for z in con.execute(
        f"SELECT * FROM ({_BEGRIFFE_SQL}) WHERE status = 'neu' OR faellig_am <= datetime('now') "
        "ORDER BY status = 'neu', faellig_am, n DESC, name").fetchall() if z["id"] not in ohne]
    return {"karte": zeilen[0] if zeilen else None, "faellig": sum(z["status"] != "neu" for z in zeilen),
            "neu": sum(z["status"] == "neu" for z in zeilen)}


# Begriffe, die in Teilaufgaben mit denselben Themen vorkommen, meiste gemeinsame Themen zuerst
_GLEICHE_THEMEN_SQL = """
SELECT tb2.begriff_id FROM teilaufgabe_begriff tb1
JOIN teilaufgabe_thema tt1 ON tt1.teilaufgabe_id = tb1.teilaufgabe_id
JOIN teilaufgabe_thema tt2 ON tt2.thema_id = tt1.thema_id
JOIN teilaufgabe_begriff tb2 ON tb2.teilaufgabe_id = tt2.teilaufgabe_id
WHERE tb1.begriff_id = ?1 AND tb2.begriff_id <> ?1
GROUP BY tb2.begriff_id ORDER BY COUNT(DISTINCT tt1.thema_id) DESC, tb2.begriff_id
"""


def ablenker(con: sqlite3.Connection, begriff_id: int, anzahl: int = 3) -> list[int]:
    """Falsche Antworten für „Definition → Begriff“, möglichst ähnlich: nach Vektor-Ähnlichkeit, sonst aus denselben
    Themen, sonst zufällig; nur Begriffe im Umfang."""
    umfang = {z[0] for z in con.execute(
        "SELECT DISTINCT tb.begriff_id FROM teilaufgabe_begriff tb JOIN v_teilaufgabe v ON v.teilaufgabe_id = tb.teilaufgabe_id "
        "WHERE tb.begriff_id <> ?", (begriff_id,))}
    themen = [z[0] for z in con.execute(_GLEICHE_THEMEN_SQL, (begriff_id,)) if z[0] in umfang]
    zufall = [z[0] for z in con.execute("SELECT id FROM begriff ORDER BY random()") if z[0] in umfang]
    return list(dict.fromkeys(vektoren.nachbarn(con, "begriff", begriff_id, umfang) + themen + zufall))[:anzahl]


def auswahl(con: sqlite3.Connection, karte) -> dict:
    """„Definition → Begriff“: die Definition ohne den gesuchten Namen und bis zu vier Begriffe zur Wahl, alphabetisch."""
    ids = [karte["id"], *ablenker(con, karte["id"])]
    optionen = con.execute(f"SELECT id, name FROM begriff WHERE id IN ({','.join('?' * len(ids))}) ORDER BY name COLLATE NOCASE",
                           ids).fetchall()
    return {"optionen": optionen, "definition": re.sub(re.escape(karte["name"]), "…", karte["erklaerung"], flags=re.I)}


def begriff_bewerten(con: sqlite3.Connection, begriff_id: int, ergebnis: int, jetzt: datetime | None = None) -> str:
    if ergebnis not in (1, 2, 3):
        raise ValueError(f"Bewertung muss 1, 2 oder 3 sein, nicht {ergebnis!r}")
    karte = con.execute("SELECT status, serie, fsrs FROM begriff_karte WHERE begriff_id = ?", (begriff_id,)).fetchone()
    status = _speichern_karte(con, "begriff_karte", "begriff_id", begriff_id, karte, ergebnis, jetzt or datetime.now(timezone.utc))
    con.commit()
    return status


def markieren(con: sqlite3.Connection, teilaufgabe_id: int) -> bool:
    """Schaltet die Markierung um und gibt den neuen Zustand zurück."""
    con.execute(
        "INSERT INTO karte (teilaufgabe_id, markiert) VALUES (?, 1) "
        "ON CONFLICT (teilaufgabe_id) DO UPDATE SET markiert = 1 - markiert",
        (teilaufgabe_id,),
    )
    con.commit()
    return bool(con.execute("SELECT markiert FROM karte WHERE teilaufgabe_id = ?", (teilaufgabe_id,)).fetchone()[0])
