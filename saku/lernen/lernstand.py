"""Lernstand exportieren und importieren, mit stabilen Schlüsseln statt IDs: übersteht einen Neuaufbau der Datenbank.
Teilaufgabe = [Jahr, Saison, Teil, Bereich, Beruf, Aufgabe, Kennung] (eindeutig laut Schema), Begriff = Name,
Thema = Slug, Station = Lernpfad und Slugs ihrer Themen (so erkennt auch die Pipeline eine Station wieder),
Rechenübung = Art, Seed und Zeitpunkt. Nicht dabei: Katalog (auch sql_sandbox), Vektoren, Sensei-Gespräche und KI-Protokoll."""

import json
import math
import re
import sqlite3
from datetime import datetime, timezone

FORMAT = "saku-lernstand"
VERSION = 1
_ZEIT = re.compile(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d")  # wie in der Datenbank (UTC)


def _passt(z: dict, **felder: str) -> bool:
    """Hat die Zeile aus der Datei die Form, mit der Saku später rechnet? zeit, int, zahl, text, json; mit „?“ auch leer.
    Sonst brächen nach dem Import Heute, Verlauf oder Rechnen ab (z. B. an einem Zeitpunkt „gestern“)."""
    for name, art in felder.items():
        wert = z.get(name)
        if wert is None and art.endswith("?"):
            continue
        art = art.rstrip("?")
        if art == "zeit":
            ok = isinstance(wert, str) and _ZEIT.fullmatch(wert)
        elif art in ("int", "zahl"):
            ok = isinstance(wert, (int, float) if art == "zahl" else int) and not isinstance(wert, bool) and math.isfinite(wert)
        elif art == "json":
            try:
                ok = isinstance(json.loads(wert), dict)
            except (TypeError, ValueError):
                ok = False
        else:
            ok = isinstance(wert, str)
        if not ok:
            return False
    return True


def _teilaufgaben(con: sqlite3.Connection) -> dict[int, list]:
    return {z[0]: list(z[1:]) for z in con.execute(
        "SELECT t.id, p.jahr, p.saison, p.teil, p.bereich, p.beruf, a.nummer, t.kennung FROM teilaufgabe t "
        "JOIN aufgabe a ON a.id = t.aufgabe_id JOIN pruefung p ON p.id = a.pruefung_id")}


def _stationen(con: sqlite3.Connection) -> dict[int, dict]:
    stationen = {}
    for s_id, pfad, slug in con.execute("SELECT s.id, s.pfad, th.slug FROM station s JOIN station_thema st ON st.station_id = s.id "
                                        "JOIN thema th ON th.id = st.thema_id ORDER BY th.slug"):
        stationen.setdefault(s_id, {"pfad": pfad, "themen": []})["themen"].append(slug)
    return stationen


def _einstellung_gueltig(schluessel: str, wert) -> bool:
    """Was die Einstellungen beim Speichern ablehnen, übernimmt auch der Import nicht (ein falscher Termin legte sonst Heute
    lahm); dazu, ob die Einführung gesehen ist. Zwischenspeicher wie niwa_stufen baut Saku selbst neu auf."""
    from saku.web.routen.kern import FELDER  # erst hier: der Lernstand hängt sonst schon beim Laden am Web
    if not isinstance(wert, str):
        return False
    if schluessel == "einfuehrung":
        return True
    try:
        return schluessel in FELDER and bool(FELDER[schluessel](wert))
    except ValueError:
        return False


def exportieren(con: sqlite3.Connection) -> dict:
    schluessel = _teilaufgaben(con)

    def mit_schluessel(sql: str, *werte) -> list[dict]:
        """Zeilen mit teilaufgabe_id; statt der ID steht der Schlüssel der Teilaufgabe drin."""
        return [{"teilaufgabe": schluessel[z["teilaufgabe_id"]]} | {k: z[k] for k in z.keys() if k != "teilaufgabe_id"}
                for z in con.execute(sql, werte)]

    stationen = _stationen(con)
    return {
        "format": FORMAT, "version": VERSION, "exportiert_am": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "einstellungen": {z[0]: z[1] for z in con.execute("SELECT schluessel, wert FROM einstellung ORDER BY schluessel")},
        "karten": mit_schluessel("SELECT teilaufgabe_id, status, serie, fsrs, faellig_am, markiert, notiz, geaendert_am FROM karte"),
        "bewertungen": mit_schluessel("SELECT teilaufgabe_id, zeitpunkt, ergebnis, quelle, dauer_s, antwort, punkte FROM bewertung "
                                      "ORDER BY zeitpunkt, id"),
        "luecken": mit_schluessel("SELECT teilaufgabe_id, text, operator, zeitpunkt FROM luecke ORDER BY id"),
        "begriff_karten": [dict(z) for z in con.execute(
            "SELECT b.name AS begriff, k.status, k.serie, k.fsrs, k.faellig_am, k.geaendert_am "
            "FROM begriff_karte k JOIN begriff b ON b.id = k.begriff_id ORDER BY b.name")],
        "simulationen": [
            {k: s[k] for k in s.keys() if k != "id"} | {"teilaufgaben": mit_schluessel(
                "SELECT teilaufgabe_id, position, antwort, punkte_erreicht, quelle FROM simulation_teilaufgabe "
                "WHERE simulation_id = ? ORDER BY position", s["id"])}
            for s in con.execute("SELECT * FROM simulation ORDER BY id").fetchall()],
        "stationstests": [stationen[z["station_id"]] | {k: z[k] for k in z.keys() if k not in ("id", "station_id")}
                          for z in con.execute("SELECT * FROM stationstest ORDER BY id").fetchall() if z["station_id"] in stationen],
        "rechenuebungen": [dict(z) for z in con.execute(
            "SELECT art, seed, richtig, felder_richtig, felder_gesamt, dauer_s, zeitpunkt FROM rechenuebung ORDER BY zeitpunkt, id")],
        # von Hand korrigierte Themen (Analyse); die der KI baut die Pipeline selbst wieder auf
        "zuordnungen": mit_schluessel("SELECT tt.teilaufgabe_id, th.slug AS thema FROM teilaufgabe_thema tt "
                                      "JOIN thema th ON th.id = tt.thema_id WHERE tt.quelle = 'manuell'"),
    }


def importieren(con: sqlite3.Connection, daten: dict) -> dict[str, list[int]]:
    """Übernimmt einen exportierten Lernstand. Mehrfach importieren ändert nichts: Vorhandenes, Älteres und alles, was der
    Katalog nicht kennt, wird übersprungen. Gibt je Bereich [übernommen, übersprungen] zurück."""
    if not isinstance(daten, dict) or daten.get("format") != FORMAT:
        raise ValueError("Das ist keine Lernstand-Datei von Saku.")
    if daten.get("version", 0) > VERSION:
        raise ValueError("Die Datei stammt aus einer neueren Saku-Version.")
    ids = {tuple(k): i for i, k in _teilaufgaben(con).items()}
    stationen = {(s["pfad"], tuple(s["themen"])): s_id for s_id, s in _stationen(con).items()}
    zahlen: dict[str, list[int]] = {}

    def zaehlen(bereich: str, uebernommen: bool) -> None:
        zahlen.setdefault(bereich, [0, 0])[0 if uebernommen else 1] += 1

    def teilaufgabe(z: dict) -> int | None:
        return ids.get(tuple(z["teilaufgabe"]))

    def einfuegen(sql: str, *werte) -> bool:
        return con.execute(sql, werte).rowcount > 0

    with con:  # alles oder nichts
        for schluessel, wert in daten.get("einstellungen", {}).items():
            zaehlen("einstellungen", _einstellung_gueltig(schluessel, wert) and einfuegen(
                "INSERT INTO einstellung (schluessel, wert) VALUES (?, ?) "
                "ON CONFLICT (schluessel) DO UPDATE SET wert = excluded.wert WHERE wert <> excluded.wert", schluessel, wert))

        # Karten nur, wenn die importierte neuer ist: ein Import überschreibt nichts, was danach gelernt wurde
        for z in daten.get("karten", []):
            t_id = teilaufgabe(z)
            zaehlen("karten", bool(t_id) and _passt(z, serie="int", fsrs="json?", faellig_am="zeit?", geaendert_am="zeit")
                    and einfuegen(
                "INSERT INTO karte (teilaufgabe_id, status, serie, fsrs, faellig_am, markiert, notiz, geaendert_am) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (teilaufgabe_id) DO UPDATE SET status = excluded.status, "
                "serie = excluded.serie, fsrs = excluded.fsrs, faellig_am = excluded.faellig_am, markiert = excluded.markiert, "
                "notiz = excluded.notiz, geaendert_am = excluded.geaendert_am WHERE excluded.geaendert_am > karte.geaendert_am",
                t_id, z["status"], z["serie"], z["fsrs"], z["faellig_am"], z["markiert"], z["notiz"], z["geaendert_am"]))

        for z in daten.get("bewertungen", []):
            t_id = teilaufgabe(z)
            zaehlen("bewertungen", bool(t_id) and _passt(z, zeitpunkt="zeit", dauer_s="int?", punkte="zahl?", antwort="text?")
                    and einfuegen(
                "INSERT INTO bewertung (teilaufgabe_id, zeitpunkt, ergebnis, quelle, dauer_s, antwort, punkte) "
                "SELECT ?1, ?2, ?3, ?4, ?5, ?6, ?7 WHERE NOT EXISTS (SELECT 1 FROM bewertung "
                "WHERE teilaufgabe_id = ?1 AND zeitpunkt = ?2 AND ergebnis = ?3 AND quelle = ?4)",
                t_id, z["zeitpunkt"], z["ergebnis"], z["quelle"], z["dauer_s"], z["antwort"], z["punkte"]))

        for z in daten.get("luecken", []):
            t_id = teilaufgabe(z)
            zaehlen("luecken", bool(t_id) and _passt(z, text="text", operator="text?", zeitpunkt="zeit") and einfuegen(
                "INSERT INTO luecke (teilaufgabe_id, text, operator, zeitpunkt) SELECT ?1, ?2, ?3, ?4 WHERE NOT EXISTS "
                "(SELECT 1 FROM luecke WHERE teilaufgabe_id = ?1 AND text = ?2 AND zeitpunkt = ?4)",
                t_id, z["text"], z["operator"], z["zeitpunkt"]))

        for z in daten.get("begriff_karten", []):
            begriff = con.execute("SELECT id FROM begriff WHERE name = ?", (z["begriff"],)).fetchone()
            zaehlen("begriff_karten", bool(begriff) and _passt(z, serie="int", fsrs="json?", faellig_am="zeit?", geaendert_am="zeit?")
                    and einfuegen(
                "INSERT INTO begriff_karte (begriff_id, status, serie, fsrs, faellig_am, geaendert_am) VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (begriff_id) DO UPDATE SET status = excluded.status, serie = excluded.serie, fsrs = excluded.fsrs, "
                "faellig_am = excluded.faellig_am, geaendert_am = excluded.geaendert_am "
                "WHERE excluded.geaendert_am > IFNULL(begriff_karte.geaendert_am, '')",
                begriff[0], z["status"], z["serie"], z["fsrs"], z["faellig_am"], z["geaendert_am"]))

        for s in daten.get("simulationen", []):
            if not _passt(s, bereich="text", gestartet_am="zeit", beendet_am="zeit?", dauer_min="int", punkte_erreicht="zahl?",
                          punkte_moeglich="zahl?") or not all(_passt(z, position="int", punkte_erreicht="zahl?", antwort="text?")
                                                              for z in s["teilaufgaben"]) or con.execute(
                    "SELECT 1 FROM simulation WHERE bereich = ? AND gestartet_am = ?", (s["bereich"], s["gestartet_am"])).fetchone():
                zaehlen("simulationen", False)
                continue
            sim_id = con.execute(
                "INSERT INTO simulation (bereich, gestartet_am, beendet_am, dauer_min, punkte_erreicht, punkte_moeglich, note, bestanden) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (s["bereich"], s["gestartet_am"], s["beendet_am"], s["dauer_min"],
                                                    s["punkte_erreicht"], s["punkte_moeglich"], s["note"], s["bestanden"])).lastrowid
            zaehlen("simulationen", True)
            for z in s["teilaufgaben"]:
                t_id = teilaufgabe(z)
                zaehlen("simulationen_teilaufgaben", bool(t_id) and einfuegen(
                    "INSERT INTO simulation_teilaufgabe (simulation_id, teilaufgabe_id, position, antwort, punkte_erreicht, quelle) "
                    "VALUES (?, ?, ?, ?, ?, ?)", sim_id, t_id, z["position"], z["antwort"], z["punkte_erreicht"], z["quelle"]))

        for z in daten.get("stationstests", []):
            s_id = stationen.get((z["pfad"], tuple(z["themen"])))
            zaehlen("stationstests", bool(s_id) and _passt(z, gestartet_am="zeit", beendet_am="zeit?", punkte_erreicht="zahl?",
                                                              punkte_moeglich="zahl?") and einfuegen(
                "INSERT INTO stationstest (station_id, gestartet_am, beendet_am, punkte_erreicht, punkte_moeglich, bestanden) "
                "SELECT ?1, ?2, ?3, ?4, ?5, ?6 WHERE NOT EXISTS (SELECT 1 FROM stationstest WHERE station_id = ?1 AND gestartet_am = ?2)",
                s_id, z["gestartet_am"], z["beendet_am"], z["punkte_erreicht"], z["punkte_moeglich"], z["bestanden"]))

        for z in daten.get("rechenuebungen", []):
            zaehlen("rechenuebungen", _passt(z, art="text", seed="int", felder_richtig="int", felder_gesamt="int", dauer_s="int?",
                                             zeitpunkt="zeit") and einfuegen(
                "INSERT INTO rechenuebung (art, seed, richtig, felder_richtig, felder_gesamt, dauer_s, zeitpunkt) "
                "SELECT ?1, ?2, ?3, ?4, ?5, ?6, ?7 WHERE NOT EXISTS "
                "(SELECT 1 FROM rechenuebung WHERE art = ?1 AND seed = ?2 AND zeitpunkt = ?7)",
                z["art"], z["seed"], z["richtig"], z["felder_richtig"], z["felder_gesamt"], z["dauer_s"], z["zeitpunkt"]))

        for z in daten.get("zuordnungen", []):
            t_id, thema = teilaufgabe(z), con.execute("SELECT id FROM thema WHERE slug = ?", (z["thema"],)).fetchone()
            neu = bool(t_id and thema) and not con.execute(
                "SELECT 1 FROM teilaufgabe_thema WHERE teilaufgabe_id = ? AND thema_id = ? AND quelle = 'manuell'", (t_id, thema[0])).fetchone()
            if neu:  # wie die Korrektur in der Analyse: die eigene Zuordnung ersetzt die der KI
                con.execute("DELETE FROM teilaufgabe_thema WHERE teilaufgabe_id = ?", (t_id,))
                con.execute("INSERT INTO teilaufgabe_thema (teilaufgabe_id, thema_id, gewicht, quelle, sicherheit) "
                            "VALUES (?, ?, 1.0, 'manuell', 1.0)", (t_id, thema[0]))
            zaehlen("zuordnungen", neu)
    return zahlen
