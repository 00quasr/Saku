"""Schritt: SQL-Sandbox. Je Aufgabe mit SQL-Teilaufgaben erfindet Claude Tabellen (SQLite) und Beispieldaten und schreibt
die Musterlösungen in SQLite. Saku führt alles einmal aus; gespeichert wird nur, was läuft. Damit lassen sich SQL-Antworten
in Üben ausführen und automatisch prüfen. Wiederaufnehmbar: nur Aufgaben ohne Sandbox."""

import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from saku import config, db
from saku.lernen import sql
from saku.sensei import client

SYSTEM = """Du baust für eine Lern-App eine SQL-Sandbox zu einer Prüfungsaufgabe (IHK, Fachinformatiker/-in). Du bekommst
die Einleitung mit dem Datenmodell (meist Markdown-Tabellen), die Teilaufgaben und deren Musterlösungen. Die App führt
eigene Antworten in SQLite aus und vergleicht ihr Ergebnis mit dem der Musterlösung. Jede Lösung läuft für sich auf
frischen Daten.

- ddl: CREATE TABLE-Anweisungen für SQLite, genau die Tabellen und Spalten aus der Aufgabe, Namen wie dort, mit Primär-
  und Fremdschlüsseln und passenden Typen (INTEGER, REAL, TEXT; Datum als TEXT 'JJJJ-MM-TT'). Fehlt das Modell in der
  Einleitung, leite es aus Teilaufgaben und Musterlösungen ab. Tabellen, die eine Teilaufgabe erst anlegen soll, gehören
  nicht in ddl. Kein PRAGMA, kein ATTACH.
- daten: INSERT-Anweisungen mit erfundenen, realistischen Beispieldaten, je Tabelle 6 bis 15 Zeilen, passend zu den
  Fremdschlüsseln. Wähle sie so, dass jede Musterlösung ein nicht-leeres, aussagekräftiges Ergebnis liefert und typische
  Fehler auffallen: Zeilen, die eine Bedingung knapp verfehlen, NULL-Werte, Datensätze ohne Partner (LEFT JOIN),
  Gleichstand bei MAX/MIN/COUNT, Datumswerte an Monats- und Jahresgrenzen. Im Sortierschlüssel einer Lösung mit ORDER BY
  keinen Gleichstand, damit die Reihenfolge eindeutig ist. UPDATE und DELETE treffen mindestens eine Zeile, INSERT
  scheitert nicht an Schlüsseln. Bezieht sich eine Lösung auf das heutige Datum, erzeuge passende Werte relativ dazu,
  z. B. date('now', '-10 days').
- teilaufgaben: für jede SQL-Teilaufgabe (id wie angegeben) loesung_sql: die Musterlösung inhaltlich unverändert als in
  SQLite lauffähiges SQL, mehrere Anweisungen mit ; getrennt. Dialekt angleichen: MySQL- und SQL-Server-Funktionen
  (NOW(), CURDATE(), YEAR(), MONTH(), DATE_FORMAT, DATEDIFF, CONCAT, TOP n …) in SQLite-Entsprechungen (date(),
  strftime(), julianday(), ||, LIMIT n), `x` und [x] als "x", Texte in '…', TRUE/FALSE als 1/0, AUTO_INCREMENT weglassen.
  Nennt die Musterlösung mehrere Varianten, nimm die erste vollständige. Ohne Musterlösung oder ohne SQL darin bleibt
  loesung_sql leer: Löse nie selbst."""

SCHEMA = {
    "type": "object",
    "properties": {
        "ddl": {"type": "string"},
        "daten": {"type": "string"},
        "teilaufgaben": {"type": "array", "items": {
            "type": "object", "properties": {"id": {"type": "integer"}, "loesung_sql": {"type": "string"}},
            "required": ["id", "loesung_sql"], "additionalProperties": False}},
    },
    "required": ["ddl", "daten", "teilaufgaben"], "additionalProperties": False,
}

WEITERE = 1500  # Zeichen je Teilaufgabe ohne SQL: nur zum Verständnis des Datenmodells


def auftrag(aufgabe: sqlite3.Row, teile: list[sqlite3.Row]) -> str:
    """Einleitung und alle Teilaufgaben der Aufgabe; SQL-Teilaufgaben mit id und vollständiger Musterlösung."""
    zeilen = [f"## Einleitung\n{aufgabe['einleitung_inhalt'] or aufgabe['einleitung'] or '(keine)'}"]
    for t in teile:
        text, loesung = t["inhalt"] or t["text"], t["loesung_inhalt"] or t["loesung_text"] or "(keine)"
        if t["art"] == "sql":
            zeilen.append(f"\n## SQL-Teilaufgabe id {t['id']} ({t['kennung']})\n{text}\n\n### Musterlösung\n{loesung}")
        else:
            zeilen.append(f"\n## Teilaufgabe {t['kennung']} (kein SQL)\n{text[:WEITERE]}\n\n### Musterlösung\n{loesung[:WEITERE]}")
    return "\n".join(zeilen)


def ausfuehren(con: sqlite3.Connection, daten: Path, ohne_ki: bool, ki: str) -> None:
    if ohne_ki or ki == "api" and not client.verfuegbar():
        print("  ohne KI: keine SQL-Sandbox", flush=True)
        return
    aufgaben = con.execute(
        "SELECT a.id, a.einleitung, a.einleitung_inhalt FROM aufgabe a "
        "WHERE NOT EXISTS (SELECT 1 FROM sql_sandbox s WHERE s.aufgabe_id = a.id) "
        "AND EXISTS (SELECT 1 FROM teilaufgabe t WHERE t.aufgabe_id = a.id AND json_extract(t.antwort, '$.art') = 'sql') "
        "ORDER BY a.id").fetchall()

    def bearbeiten(aufgabe: sqlite3.Row) -> int:
        eigene = db.verbinden(config.db_pfad(daten))  # je Thread eine Verbindung
        try:
            teile = eigene.execute("SELECT id, kennung, text, inhalt, loesung_text, loesung_inhalt, json_extract(antwort, '$.art') AS art "
                                   "FROM teilaufgabe WHERE aufgabe_id = ? ORDER BY position", (aufgabe["id"],)).fetchall()
            erlaubt, text, fehler = {t["id"] for t in teile if t["art"] == "sql"}, auftrag(aufgabe, teile), None
            # ein zweiter Versuch mit der Fehlermeldung von SQLite (anderer Text, also nicht aus dem Cache)
            for nachtrag in ("", "\n\nDein erster Entwurf lief in SQLite nicht: {}\nKorrigiere ihn."):
                antwort = client.strukturiert(eigene, "sandbox", "stark", SYSTEM, text + nachtrag.format(fehler), SCHEMA,
                                              ki=ki, aufwand="medium", max_tokens=16000)
                loesungen = {t["id"]: t["loesung_sql"].strip() for t in antwort["teilaufgaben"]
                             if t["id"] in erlaubt and t["loesung_sql"].strip()}
                try:
                    sql.testen(antwort["ddl"], antwort["daten"], loesungen)
                    break
                except sql.SqlFehler as f:
                    fehler = str(f)
            else:
                print(f"\n  Aufgabe {aufgabe['id']} ohne Sandbox: {fehler}", flush=True)
                return 0
            eigene.execute("INSERT INTO sql_sandbox (aufgabe_id, ddl, daten) VALUES (?, ?, ?)",
                           (aufgabe["id"], antwort["ddl"].strip(), antwort["daten"].strip()))
            eigene.executemany("UPDATE teilaufgabe SET loesung_sql = ? WHERE id = ?", [(s, i) for i, s in loesungen.items()])
            eigene.commit()
            return 1
        except (client.KiFehler, sqlite3.Error, KeyError, TypeError, AttributeError) as f:
            eigene.rollback()  # die Aufgabe bleibt offen und kommt beim nächsten Lauf wieder dran
            print(f"\n  Aufgabe {aufgabe['id']}: {type(f).__name__}: {f}", flush=True)
            return 0
        finally:
            eigene.close()

    fertig = gesamt = 0
    with ThreadPoolExecutor(int(os.getenv("SAKU_KI_PARALLEL", 3))) as pool:
        for anzahl in pool.map(bearbeiten, aufgaben):
            fertig += 1
            gesamt += anzahl
            print(f"  {fertig}/{len(aufgaben)} Aufgaben, {gesamt} Sandboxen", end="\r", flush=True)
    print(f"  {len(aufgaben)} Aufgaben mit SQL offen · {gesamt} Sandboxen gebaut{' ' * 20}", flush=True)
