import json
import subprocess

from saku import config, db
from saku.sensei import client as ki


def test_schema_und_demo(con):
    assert con.execute("PRAGMA user_version").fetchone()[0] == 9
    assert db.einstellung(con, "farbschema") == "dunkel"
    assert con.execute("SELECT COUNT(*) FROM teilaufgabe").fetchone()[0] == 14
    reife = con.execute("SELECT prozent, neu FROM v_pruefungsreife").fetchone()
    assert reife["prozent"] == 0 and reife["neu"] == 14


def test_alle_bereiche_antworten(client):
    for pfad in ["/", "/michi/", "/keiko/", "/shiken/", "/niwa/", "/bunseki/", "/einstellungen"]:
        antwort = client.get(pfad)
        assert antwort.status_code == 200, pfad
        assert b'class="seitenleiste"' in antwort.data


def test_bild_nur_aus_datenordner(client, con):
    pfad = json.loads(con.execute("SELECT bilder FROM teilaufgabe LIMIT 1").fetchone()[0])[0]
    assert client.get("/bild/" + pfad).status_code == 200
    assert client.get("/bild/saku.db").status_code == 404
    assert client.get("/bild/aufgaben/../saku.db").status_code == 404


def test_markdown_ohne_html():
    from saku.web import markdown_zu_html
    assert "<script>" not in markdown_zu_html("**fett** <script>x</script>")
    assert "<strong>fett</strong>" in markdown_zu_html("**fett**")
    zelle = markdown_zu_html("| A |\n|---|\n| x<br>y<BR/>z |")
    assert "x<br>y<br>z" in zelle and "&lt;" not in zelle


def test_einstellungen_speichern(client, con):
    antwort = client.post("/einstellungen/pruefungstermin", data={"pruefungstermin": "2099-04-28"})
    assert antwort.headers["HX-Trigger"] == "gespeichert" and "Tage" in antwort.text
    assert db.einstellung(con, "pruefungstermin") == "2099-04-28"
    client.post("/einstellungen/farbschema", data={"farbschema": "hell"})
    assert db.einstellung(con, "farbschema") == "hell"
    assert client.post("/einstellungen/pruefungstermin", data={"pruefungstermin": "kein Datum"}).status_code == 400
    assert client.post("/einstellungen/puffer_tage", data={"puffer_tage": "99"}).status_code == 400
    assert client.post("/einstellungen/farbschema", data={"farbschema": "pink"}).status_code == 400
    assert client.post("/einstellungen/beruf", data={"beruf": "x"}).status_code == 400  # nicht freigegeben
    assert db.einstellung(con, "puffer_tage") == "7"


SCHEMA = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"], "additionalProperties": False}


def test_strukturiert_ueber_claude_code_mit_cache(con, monkeypatch):
    aufrufe = []

    def lauf(befehl, **kw):
        aufrufe.append(befehl)
        ausgabe = {"is_error": False, "structured_output": {"x": 7}, "usage": {"input_tokens": 3, "output_tokens": 5}}
        return subprocess.CompletedProcess(befehl, 0, stdout=json.dumps(ausgabe), stderr="")

    monkeypatch.setattr(subprocess, "run", lauf)
    assert ki.strukturiert(con, "test", "schnell", "sys", "frage", SCHEMA, ki="claude-code") == {"x": 7}
    assert ki.strukturiert(con, "test", "schnell", "sys", "frage", SCHEMA, ki="api") == {"x": 7}  # Cache
    assert len(aufrufe) == 1 and "--json-schema" in aufrufe[0]
    protokoll = con.execute("SELECT tokens_aus, aus_cache FROM ki_aufruf ORDER BY id").fetchall()
    assert [tuple(z) for z in protokoll] == [(5, 0), (0, 1)]


def test_ohne_schluessel_kein_stream(con, monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "")
    try:
        list(ki.stream(con, "test", "sys", [{"role": "user", "content": "hallo"}]))
    except ki.KiFehler:
        pass
    else:
        raise AssertionError("KiFehler erwartet")


def test_umfang_filtert_beruf_und_teil(client, con):
    alle = con.execute("SELECT COUNT(*) FROM v_teilaufgabe").fetchone()[0]
    assert alle and con.execute("SELECT pfad FROM v_umfang").fetchone()[0] == "AP2-1201"
    # erfundene WiSo-Prüfung gilt für alle IT-Berufe, eine AP1 nur im Teil 1
    for teil, bereich in (("AP2", "Wirtschafts- und Sozialkunde"), ("AP1", "Einrichten eines IT-gestützten Arbeitsplatzes")):
        p = con.execute("INSERT INTO pruefung (jahr, saison, teil, bereich, beruf) VALUES (2031, 'Sommer', ?, ?, 'IT')",
                        (teil, bereich)).lastrowid
        a = con.execute("INSERT INTO aufgabe (pruefung_id, nummer) VALUES (?, 1)", (p,)).lastrowid
        con.execute("INSERT INTO teilaufgabe (aufgabe_id, kennung, position) VALUES (?, 'a', 0)", (a,))
    con.commit()

    antwort = client.post("/umfang", data={"beruf": "1202"}, headers={"Referer": "http://localhost/michi/"})
    assert antwort.status_code == 302 and antwort.headers["Location"].endswith("/michi/")
    assert [z[0] for z in con.execute("SELECT DISTINCT bereich FROM v_teilaufgabe")] == ["Wirtschafts- und Sozialkunde"]
    client.post("/umfang", data={"teil": "AP1"})
    assert con.execute("SELECT pfad FROM v_umfang").fetchone()[0] == "AP1"
    assert [z[0] for z in con.execute("SELECT DISTINCT bereich FROM v_teilaufgabe")] == ["Einrichten eines IT-gestützten Arbeitsplatzes"]
    assert client.post("/umfang", data={"teil": "AP3"}).status_code == 400
    assert client.post("/umfang", data={"beruf": "1201"}, headers={"Referer": "https://boese.example/"}).headers["Location"] == "/"
    assert con.execute("SELECT pfad FROM v_umfang").fetchone()[0] == "AP1"  # Beruf gewechselt, Teil bleibt


def test_migrationen(tmp_path):
    """Eine Datenbank mit Version 2 bekommt die Spalte bewertung.punkte, ohne Daten zu verlieren."""
    import sqlite3
    pfad = tmp_path / "alt.db"
    alt = sqlite3.connect(pfad)
    alt.executescript("CREATE TABLE bewertung (id INTEGER PRIMARY KEY, ergebnis INTEGER); INSERT INTO bewertung (ergebnis) VALUES (3); "
                      "CREATE TABLE teilaufgabe (id INTEGER PRIMARY KEY); CREATE TABLE begriff (id INTEGER PRIMARY KEY); "
                      "PRAGMA user_version = 2;")
    alt.close()
    assert db.init(pfad) is False
    con = sqlite3.connect(pfad)
    assert con.execute("PRAGMA user_version").fetchone()[0] == 9
    assert con.execute("SELECT ergebnis, punkte FROM bewertung").fetchall() == [(3, None)]
    assert con.execute("SELECT COUNT(*) FROM rechenuebung").fetchone()[0] == 0


def test_sicherung_einmal_am_tag(daten, con):
    from datetime import date

    pfad = config.db_pfad(daten)
    ordner = daten / "backups"
    ordner.mkdir()
    for tag in range(1, 10):  # neun alte Sicherungen, sieben bleiben (mit der von heute)
        (ordner / f"saku-2020-01-0{tag}.db").write_bytes(b"alt")
    ziel = db.sichern(pfad)
    assert ziel == ordner / f"saku-{date.today().isoformat()}.db" and not list(ordner.glob("*.teil"))
    kopie = db.verbinden(ziel)
    assert kopie.execute("SELECT COUNT(*) FROM teilaufgabe").fetchone()[0] == 14
    kopie.close()
    assert len(list(ordner.glob("saku-*.db"))) == 7 and not (ordner / "saku-2020-01-03.db").exists()

    assert db.sichern(pfad) is None  # heute schon gesichert
    con.execute("DELETE FROM teilaufgabe WHERE id = 1")
    con.commit()
    db.sichern(pfad, erzwingen=True)
    kopie = db.verbinden(ziel)
    assert kopie.execute("SELECT COUNT(*) FROM teilaufgabe").fetchone()[0] == 13
    kopie.close()

    (daten / "kaputt").mkdir()
    (daten / "kaputt" / "backups").write_text("eine Datei, kein Ordner")
    (daten / "kaputt" / "saku.db").write_bytes(pfad.read_bytes())
    db.taeglich_sichern(daten / "kaputt" / "saku.db")  # Fehler wird nur gemeldet


def test_jetzt_sichern_in_den_einstellungen(client, daten):
    assert "Noch keine Sicherung" in client.get("/einstellungen").get_data(as_text=True)
    antwort = client.post("/einstellungen/sichern").get_data(as_text=True)
    assert antwort.startswith("Zuletzt am ") and "data/backups/saku-" in antwort
    assert db.letzte_sicherung(config.db_pfad(daten)).exists()
    assert "Jetzt sichern" in client.get("/einstellungen").get_data(as_text=True)
