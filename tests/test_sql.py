"""SQL-Sandbox: Vergleich, Sicherheit, Pipeline-Schritt (KI gemockt) und Üben (alles erfunden)."""

import re
import sqlite3
import time

import pytest

from saku import db
from saku.lernen import sql
from saku.pipeline import sandbox

DDL = "CREATE TABLE kunde (id INTEGER PRIMARY KEY, name TEXT, ort TEXT, umsatz REAL);"
DATEN = "INSERT INTO kunde VALUES (1, 'Ada', 'Köln', 120.5), (2, 'Bo', 'Bonn', 80), (3, 'Cem', 'Köln', 120.5), (4, 'Dana', NULL, 10);"


def pruefen(loesung: str, eigene: str) -> dict:
    return sql.pruefen(DDL, DATEN, loesung, eigene)


def test_anweisungen_und_sortierung():
    assert sql.anweisungen("SELECT ';'; -- a; b\nSELECT 2;\n-- Ende") == ["SELECT ';';", "-- a; b\nSELECT 2;"]
    assert sql.sortierung("SELECT a FROM t WHERE a IN (SELECT b FROM u ORDER BY b)", ["a"]) is None
    assert sql.sortierung("SELECT k.a, COUNT(*) AS n FROM t k GROUP BY k.a ORDER BY n DESC, k.a LIMIT 3", ["a", "n"]) == [1, 0]
    assert sql.sortierung("SELECT a, b FROM t ORDER BY length(a)", ["a", "b"]) == [0, 1]  # Ausdruck: die ganze Zeile zählt


def test_select_menge_reihenfolge_toleranz():
    koeln = "SELECT name, umsatz FROM kunde WHERE ort = 'Köln'"
    # Spaltennamen, Spalten- und Zeilenreihenfolge sind egal, solange die Lösung nicht sortiert
    assert pruefen(koeln, "SELECT umsatz AS u, name AS n FROM kunde WHERE ort LIKE 'K%' ORDER BY id DESC")["ergebnis"] == 3
    assert pruefen("SELECT AVG(umsatz) FROM kunde WHERE id IN (1, 2, 4)",
                   "SELECT ROUND(AVG(umsatz), 2) FROM kunde WHERE id <> 3")["ergebnis"] == 3  # 70.1666… gegen 70.17

    sortiert = "SELECT name, umsatz FROM kunde ORDER BY umsatz DESC"
    assert pruefen(sortiert, "SELECT name, umsatz FROM kunde ORDER BY umsatz DESC, name DESC")["ergebnis"] == 3  # Gleichstand Ada/Cem
    verkehrt = pruefen(sortiert, "SELECT name, umsatz FROM kunde ORDER BY umsatz")
    assert verkehrt["ergebnis"] == 2 and verkehrt["hinweise"] == ["Die Zeilen stimmen, die Reihenfolge nicht (ORDER BY)."]

    zu_viel = pruefen(koeln, "SELECT name, umsatz FROM kunde WHERE ort = 'Köln' OR ort IS NULL")
    assert zu_viel["ergebnis"] == 2 and zu_viel["hinweise"] == ["1 Zeile zu viel."]
    daneben = pruefen(koeln, "SELECT name, umsatz FROM kunde WHERE id = 2")
    assert daneben["ergebnis"] == 1 and daneben["hinweise"] == ["2 Zeilen fehlen, 1 Zeile zu viel."]
    assert [t["titel"] for t in daneben["tabellen"][0]] == ["Erwartet", "Dein Ergebnis"]
    spalte = pruefen(koeln, "SELECT id, name, umsatz FROM kunde WHERE ort = 'Köln'")
    assert spalte["ergebnis"] == 2 and spalte["hinweise"] == ["1 Spalte zu viel."]
    assert pruefen(koeln, "SELECT name FROM kunde")["hinweise"] == ["2 Spalten erwartet, 1 geliefert."]
    assert pruefen(koeln, "DELETE FROM kunde")["ergebnis"] == 1  # liefert kein Ergebnis


def test_dml_und_ddl_vergleichen_den_zustand():
    erhoehen = "UPDATE kunde SET umsatz = umsatz * 1.1 WHERE ort = 'Köln'"
    assert pruefen(erhoehen, "update kunde set umsatz = umsatz + umsatz / 10 where ort in ('Köln')")["ergebnis"] == 3
    halb = pruefen(erhoehen, "UPDATE kunde SET umsatz = umsatz * 1.1 WHERE id = 1")
    assert halb["ergebnis"] == 2 and halb["hinweise"] == ["Tabelle kunde: 1 Zeile fehlt, 1 Zeile zu viel."]
    assert [t["titel"] for t in halb["tabellen"][0]] == ["kunde erwartet", "kunde bei dir"]
    nichts = pruefen(erhoehen, "SELECT * FROM kunde")  # „nichts tun“ ist nicht fast richtig
    assert nichts["ergebnis"] == 1 and nichts["hinweise"][0] == "Deine Anweisung ändert nichts."
    assert pruefen("INSERT INTO kunde (id, name) VALUES (5, 'Eda')", "INSERT INTO kunde VALUES (5, 'Eda', NULL, NULL)")["ergebnis"] == 3

    anlegen = "CREATE TABLE bestellung (id INTEGER PRIMARY KEY, kunde_id INTEGER REFERENCES kunde(id), datum DATE)"
    assert pruefen(anlegen, "create table Bestellung (Datum varchar(10), ID int primary key, Kunde_ID int)")["ergebnis"] == 3
    fehlt = pruefen(anlegen, "CREATE TABLE bestellung (id INTEGER PRIMARY KEY, datum TEXT)")
    assert fehlt["ergebnis"] == 2 and fehlt["hinweise"] == ["Tabelle bestellung: Spalte kunde_id fehlt."]
    assert pruefen("ALTER TABLE kunde ADD COLUMN email TEXT", "ALTER TABLE kunde ADD email VARCHAR(100)")["ergebnis"] == 3


@pytest.mark.parametrize("anweisung", ["ATTACH DATABASE 'fremd.db' AS fremd", "VACUUM INTO 'kopie.db'",
                                       "SELECT load_extension('fremd')", "PRAGMA writable_schema = 1"])
def test_sandbox_sperrt_dateien_pragma_und_erweiterungen(anweisung, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(sql.SqlFehler, match="Nicht erlaubt"):
        sql.ausfuehren(DDL, DATEN, anweisung)
    assert not list(tmp_path.iterdir())


def test_endlosschleife_und_grenzen(monkeypatch):
    monkeypatch.setattr(sql, "SEKUNDEN", 0.3)
    start = time.monotonic()
    with pytest.raises(sql.SqlFehler, match="Abgebrochen"):
        sql.ausfuehren(DDL, DATEN, "WITH RECURSIVE r(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM r) SELECT COUNT(*) FROM r")
    assert time.monotonic() - start < 2
    gross = sql.ausfuehren(DDL, DATEN, "WITH RECURSIVE r(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM r LIMIT 6000) SELECT x FROM r")
    assert gross["meldung"] == "mehr als 5000 Zeilen" and len(gross["tabellen"][0]["zeilen"]) == sql.ZEIGEN
    with pytest.raises(sql.SqlFehler, match="Zu lang"):
        sql.ausfuehren(DDL, DATEN, "SELECT 1;" * (sql.ANWEISUNGEN + 1))
    with pytest.raises(sql.SqlFehler, match="Schreib erst"):
        sql.ausfuehren(DDL, DATEN, " -- nur ein Kommentar\n")
    # Skript: geänderte Tabellen statt Ergebnis
    skript = sql.ausfuehren(DDL, DATEN, "DELETE FROM kunde WHERE ort IS NULL; UPDATE kunde SET ort = 'Bonn' WHERE id = 1;")
    assert skript["meldung"] == "2 Zeilen geändert" and [t["titel"] for t in skript["tabellen"]] == ["kunde"]


def _pipeline_mock(monkeypatch, reparieren: dict) -> list[str]:
    """Lager-Aufgabe: gültige Antwort. Verleih-Aufgabe: Lösung greift auf eine fehlende Tabelle zu,
    erst mit reparieren["an"] klappt der zweite Versuch."""
    aufrufe = []

    def strukturiert(c, zweck, rolle, system, text, schema, **kw):
        aufrufe.append(text)
        assert (zweck, rolle, schema) == ("sandbox", "stark", sandbox.SCHEMA)
        ids = [int(i) for i in re.findall(r"SQL-Teilaufgabe id (\d+)", text)]
        if "Lager" in text:
            return {"ddl": "CREATE TABLE artikel (id INTEGER PRIMARY KEY, lager_id INTEGER);",
                    "daten": "INSERT INTO artikel VALUES (1, 1), (2, 1), (3, 2);",
                    "teilaufgaben": [{"id": ids[0], "loesung_sql": "SELECT lager_id, COUNT(*) FROM artikel GROUP BY lager_id"},
                                     {"id": 99999, "loesung_sql": "SELECT 1"}]}
        tabellen = "CREATE TABLE kunde (id INTEGER PRIMARY KEY);"
        if reparieren["an"] and "lief in SQLite nicht" in text:
            tabellen += "CREATE TABLE ausleihe (id INTEGER PRIMARY KEY, kunde_id INTEGER);"
        return {"ddl": tabellen, "daten": "INSERT INTO kunde VALUES (1); INSERT INTO ausleihe VALUES (1, 1);" if "ausleihe" in tabellen else
                "INSERT INTO kunde VALUES (1);",
                "teilaufgaben": [{"id": ids[0], "loesung_sql": "SELECT * FROM kunde k JOIN ausleihe a ON a.kunde_id = k.id"}]}

    monkeypatch.setattr(sandbox.client, "strukturiert", strukturiert)
    return aufrufe


def test_schritt_sandbox(con, daten, monkeypatch, capsys):
    con.execute("DELETE FROM sql_sandbox")
    con.execute("UPDATE teilaufgabe SET loesung_sql = NULL")
    con.commit()
    reparieren = {"an": False}
    aufrufe = _pipeline_mock(monkeypatch, reparieren)

    sandbox.ausfuehren(con, daten, False, "claude-code")
    lager = con.execute("SELECT t.id, t.aufgabe_id, t.loesung_sql FROM teilaufgabe t WHERE t.text LIKE '%Artikel je Lager%'").fetchone()
    verleih = con.execute("SELECT t.id, t.aufgabe_id, t.loesung_sql FROM teilaufgabe t WHERE t.text LIKE '%per JOIN%'").fetchone()
    assert lager["loesung_sql"].endswith("GROUP BY lager_id") and verleih["loesung_sql"] is None
    assert [z[0] for z in con.execute("SELECT aufgabe_id FROM sql_sandbox")] == [lager["aufgabe_id"]]
    assert "SQL-Teilaufgabe id" in aufrufe[0] and "(kein SQL)" in aufrufe[0]  # die anderen Teilaufgaben nur zum Verständnis
    zweiter = [a for a in aufrufe if "lief in SQLite nicht" in a]
    assert len(aufrufe) == 3 and "no such table: ausleihe" in zweiter[0]  # kaputt: ein zweiter Versuch mit der Meldung
    assert "ohne Sandbox" in capsys.readouterr().out

    reparieren["an"] = True
    sandbox.ausfuehren(con, daten, False, "claude-code")
    assert len(aufrufe) == 5 and sum("Lager" in a for a in aufrufe) == 1  # nur, was noch fehlt
    assert con.execute("SELECT loesung_sql FROM teilaufgabe WHERE id = ?", (verleih["id"],)).fetchone()[0].startswith("SELECT *")
    sandbox.ausfuehren(con, daten, True, "api")  # ohne KI: nichts zu tun
    assert len(aufrufe) == 5


def test_migration_7(tmp_path):
    alt = sqlite3.connect(tmp_path / "alt.db")
    alt.executescript("CREATE TABLE aufgabe (id INTEGER PRIMARY KEY); CREATE TABLE teilaufgabe (id INTEGER PRIMARY KEY); "
                      "INSERT INTO teilaufgabe VALUES (1); PRAGMA user_version = 6;")
    alt.close()
    db.init(tmp_path / "alt.db")
    con = sqlite3.connect(tmp_path / "alt.db")
    assert con.execute("SELECT id, loesung_sql FROM teilaufgabe").fetchall() == [(1, None)]
    assert con.execute("SELECT COUNT(*) FROM sql_sandbox").fetchone()[0] == 0


def test_ueben_fuehrt_sql_aus_und_prueft(client, con):
    t_id = con.execute("SELECT id FROM teilaufgabe WHERE loesung_sql LIKE '%GROUP BY%'").fetchone()[0]
    karte = client.get(f"/keiko/?teilaufgabe={t_id}").get_data(as_text=True)
    assert f'hx-post="/keiko/{t_id}/sql"' in karte and "Tabellen ansehen" in karte and f"/keiko/{t_id}/pruefen" in karte
    assert "⌘↵ führt aus" in karte and "Nur Lösung zeigen" in karte

    ergebnis = client.post(f"/keiko/{t_id}/sql", data={"antwort": "SELECT ort FROM lager ORDER BY id"}).get_data(as_text=True)
    assert "3 Zeilen" in ergebnis and "<td>Süd</td>" in ergebnis
    assert "no such table: gibtsnicht" in client.post(f"/keiko/{t_id}/sql", data={"antwort": "SELECT * FROM gibtsnicht"}).get_data(as_text=True)
    tabellen = client.get(f"/keiko/{t_id}/tabellen").get_data(as_text=True)
    assert "artikel" in tabellen and "Schraube" in tabellen and 'class="sql-null"' in tabellen

    richtig = client.post(f"/keiko/{t_id}/pruefen", data={"antwort": "SELECT COUNT(*) AS anzahl, lager_id FROM artikel GROUP BY 2"})
    html = richtig.get_data(as_text=True)
    assert "Richtig." in html and 'data-taste="Enter"' in html and "GROUP BY 2" in html  # die Anweisung geht mit in die Bewertung
    assert 'id="antwortfeld"' not in html and "Erwartet" not in html  # der Editor bleibt zum Weiterprobieren
    teilweise = client.post(f"/keiko/{t_id}/pruefen", data={
        "antwort": "SELECT lager_id, COUNT(*) FROM artikel WHERE lager_id IS NOT NULL GROUP BY lager_id"}).get_data(as_text=True)
    assert "Teilweise richtig." in teilweise and "1 Zeile fehlt." in teilweise and "Dein Ergebnis" in teilweise
    kaputt = client.post(f"/keiko/{t_id}/pruefen", data={"antwort": "SELEC 1"}).get_data(as_text=True)
    assert "SQLite meldet" in kaputt and "Nicht gewusst" not in kaputt and "lass dir die Lösung zeigen" in kaputt

    client.post(f"/keiko/{t_id}/bewerten", data={"ergebnis": 2, "antwort": "SELECT lager_id FROM artikel"})
    assert con.execute("SELECT ergebnis, antwort FROM bewertung WHERE teilaufgabe_id = ?", (t_id,)).fetchone()[:] == (2, "SELECT lager_id FROM artikel")

    # ohne Sandbox bleibt alles wie bisher: Editor ohne Ausführen, Lösung zeigen, Selbstbewertung
    ohne = con.execute("SELECT id, aufgabe_id FROM teilaufgabe WHERE loesung_sql LIKE '%JOIN%'").fetchone()
    con.execute("DELETE FROM sql_sandbox WHERE aufgabe_id = ?", (ohne["aufgabe_id"],))
    con.commit()
    karte = client.get(f"/keiko/?teilaufgabe={ohne['id']}").get_data(as_text=True)
    assert "Deine SQL-Anweisung" in karte and "Tabellen ansehen" not in karte and f"/keiko/{ohne['id']}/pruefen" not in karte
    assert client.post(f"/keiko/{ohne['id']}/sql", data={"antwort": "SELECT 1"}).status_code == 404
    assert client.post(f"/keiko/{ohne['id']}/pruefen", data={"antwort": "SELECT 1"}).status_code == 400
