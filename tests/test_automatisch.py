"""Automatisch prüfen in Mini-Test und Simulation: anklickbare Teilaufgaben und SQL mit Sandbox (Demo-Daten, erfundene Prüfungen)."""

import json
import re

from saku.lernen import antwort, karten

HTMX = {"HX-Request": "true"}
LAGER = 9    # Demo: Winter 2023/24, Aufgabe 2 a, Anzahl Artikel je Lager (Sandbox, 8 Punkte)
JOIN = 12    # Demo: Sommer 2024, Aufgabe 1 a, Kunde JOIN Ausleihe (Sandbox, 6 Punkte)
RICHTIG = "SELECT COUNT(*) AS anzahl, lager_id FROM artikel GROUP BY 2"
TEILWEISE = "SELECT lager_id, COUNT(*) FROM artikel WHERE lager_id IS NOT NULL GROUP BY lager_id"
FORMAT = {"ziele": [], "einheit": "", "vorlage": ""}


def _anklickbar(con):
    """Projektmanagement (Station 1): 1 a Auswahl (B richtig, 6 Punkte), 1 b Zahl (1024, 4 Punkte), 1 c bleibt frei (8 Punkte)."""
    con.execute("UPDATE teilaufgabe SET antwort = ? WHERE id = 1", (json.dumps(FORMAT | {
        "art": "einfach", "optionen": [{"wert": "A", "text": "Puffer"}, {"wert": "B", "text": "Kritischer Pfad"}], "richtig": ["B"]}),))
    con.execute("UPDATE teilaufgabe SET antwort = ? WHERE id = 2",
                (json.dumps(FORMAT | {"art": "zahl", "optionen": [], "richtig": ["1024"]}),))
    con.commit()


def test_vorschlag_anklickbar_und_sql(con):
    _anklickbar(con)
    t = karten.lade(con, [1, 3, LAGER])
    assert antwort.vorschlag(con, t[0], {"wahl": ["B"]}, None)["punkte"] == 6
    assert antwort.vorschlag(con, t[1], None, "freier Text") is None  # frei: Selbstbewertung

    sql = t[2]
    assert antwort.vorschlag(con, sql, None, RICHTIG) == {"punkte": 8, "werte": None, "hinweise": [], "fehler": False}
    assert antwort.vorschlag(con, sql, None, TEILWEISE) == {"punkte": 4, "werte": None, "hinweise": ["1 Zeile fehlt."], "fehler": False}
    kaputt = antwort.vorschlag(con, sql, None, "SELEC 1")
    assert (kaputt["punkte"], kaputt["fehler"]) == (0, True) and kaputt["hinweise"][0].startswith("SQLite meldet")
    assert antwort.vorschlag(con, sql, None, "")["hinweise"] == ["Schreib erst eine SQL-Anweisung."]

    con.execute("DELETE FROM sql_sandbox WHERE aufgabe_id = ?", (sql["aufgabe_id"],))
    assert antwort.vorschlag(con, sql, None, RICHTIG) is None  # ohne Sandbox: Selbstbewertung


def test_mini_test_prueft_anklickbar(client, con):
    _anklickbar(con)
    html = client.get("/michi/1/test").get_data(as_text=True)
    assert 'name="antwort-1-wahl"' in html and 'name="antwort-2-zahl"' in html and 'name="punkte-3"' in html
    assert 'name="punkte-1"' not in html and 'hx-post="/michi/1/test/1/pruefen"' in html and 'data-taste="B"' not in html

    geprueft = client.post("/michi/1/test/1/pruefen", data={"antwort-1-wahl": "B"}, headers=HTMX).get_data(as_text=True)
    assert re.search(r'id="punkte-1"[^>]*value="6"', geprueft) and "automatisch bewertet" in geprueft
    assert "wahl-option--richtig" in geprueft and "<html" not in geprueft
    assert client.post("/michi/1/test/3/pruefen", data={}, headers=HTMX).status_code == 400  # frei: nichts zu prüfen

    # 1 a nicht geprüft: Saku wertet beim Auswerten selbst aus (6); 1 b geprüft, falsch, aber selbst auf 2 gesetzt; 1 c selbst 8
    client.post("/michi/1/test", data={"teilaufgabe": ["1", "2", "3"], "antwort-1-wahl": "B", "punkte-2": "2", "punkte-3": "8"},
                headers=HTMX)
    assert con.execute("SELECT punkte_erreicht, punkte_moeglich FROM stationstest").fetchone()[:] == (16, 18)
    assert con.execute("SELECT status FROM karte WHERE teilaufgabe_id = 1").fetchone()[0] == "gelb"


def test_mini_test_prueft_sql(client, con):
    con.executemany("INSERT INTO stationstest (station_id, bestanden) VALUES (?, 1)", [(1,), (2,), (4,)])
    con.commit()
    html = client.get("/michi/5/test").get_data(as_text=True)  # Datenbanken: zwei SQL mit Sandbox, zwei frei
    assert f'name="antwort-{LAGER}"' in html and f'name="antwort-{JOIN}"' in html and "saku.editorTaste" in html
    assert 'name="punkte-10"' in html and f'name="punkte-{LAGER}"' not in html and f'hx-get="/keiko/{LAGER}/tabellen"' in html

    teilweise = client.post(f"/michi/5/test/{LAGER}/pruefen", data={f"antwort-{LAGER}": TEILWEISE}, headers=HTMX).get_data(as_text=True)
    assert re.search(rf'id="punkte-{LAGER}"[^>]*value="4"', teilweise) and "1 Zeile fehlt." in teilweise
    assert "WHERE lager_id IS NOT NULL" in teilweise  # die eigene Anweisung bleibt zu sehen
    kaputt = client.post(f"/michi/5/test/{LAGER}/pruefen", data={f"antwort-{LAGER}": "SELEC 1"}, headers=HTMX).get_data(as_text=True)
    assert re.search(rf'id="punkte-{LAGER}"[^>]*value="0"', kaputt) and "0 Punkte vorbelegt: SQLite meldet" in kaputt

    # LAGER nicht geprüft und richtig → 8; JOIN läuft nicht, aber selbst überschrieben mit 6; die freien selbst
    ergebnis = client.post("/michi/5/test", headers=HTMX, data={
        "teilaufgabe": [str(LAGER), str(JOIN), "10", "13"], f"antwort-{LAGER}": RICHTIG, f"antwort-{JOIN}": "SELEC",
        f"punkte-{JOIN}": "6", "punkte-10": "10", "punkte-13": "8"}).get_data(as_text=True)
    assert "Station geschafft" in ergebnis
    assert con.execute("SELECT punkte_erreicht FROM stationstest WHERE station_id = 5").fetchone()[0] == 32

    con.execute("DELETE FROM sql_sandbox WHERE aufgabe_id = (SELECT aufgabe_id FROM teilaufgabe WHERE id = ?)", (JOIN,))
    con.commit()
    ohne = client.get("/michi/5/test").get_data(as_text=True)
    assert f'name="punkte-{JOIN}"' in ohne and f'name="antwort-{JOIN}"' not in ohne  # ohne Sandbox: Selbstbewertung


def test_simulation_prueft_sql(client, con):
    url = client.post("/shiken/neu", data={"bereich": "Entwicklung und Umsetzung von Algorithmen"}).headers["Location"]
    sim_id = int(url.rsplit("/", 1)[1])
    con.execute("DELETE FROM simulation_teilaufgabe")
    con.executemany("INSERT INTO simulation_teilaufgabe (simulation_id, teilaufgabe_id, position) VALUES (?, ?, ?)",
                    [(sim_id, LAGER, 0), (sim_id, 10, 1), (sim_id, JOIN, 2)])
    con.commit()
    assert f'name="antwort-{LAGER}"' in client.get(url).get_data(as_text=True)
    client.post(url + "/speichern", data={f"antwort-{LAGER}": TEILWEISE, "antwort-10": "Tabellen trennen", f"antwort-{JOIN}": "SELEC"},
                headers=HTMX)
    client.post(url + "/abgeben", data={})

    auswertung = client.get(url + "/auswertung").get_data(as_text=True)
    assert re.search(rf'id="punkte-{LAGER}"[^>]*value="4"', auswertung) and "automatisch bewertet: 1 Zeile fehlt." in auswertung
    assert re.search(rf'id="punkte-{JOIN}"[^>]*value="0"', auswertung) and "0 Punkte vorbelegt: SQLite meldet" in auswertung
    assert not re.search(r'id="punkte-10"[^>]*value=', auswertung) and "Tabellen trennen" in auswertung  # frei: selbst bewerten
    assert "SQL mit Beispieldaten hat Saku schon automatisch bewertet" in auswertung

    client.post(url + "/auswertung", data={f"punkte-{LAGER}": "4", "punkte-10": "10", f"punkte-{JOIN}": "6"})
    fertig = client.get(url + "/auswertung").get_data(as_text=True)
    assert "automatisch bewertet" in fertig and "selbst bewertet, automatisch wären es 0" in fertig
    assert con.execute("SELECT punkte_erreicht FROM simulation WHERE id = ?", (sim_id,)).fetchone()[0] == 20
