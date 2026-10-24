"""Routen der Lernbereiche: Heute, Keiko, Michi, Shiken und die Suche (Demo-Daten, erfundene Prüfungen)."""

import json
import re

from saku.lernen import pfad
from saku.web.routen.keiko import varianten
from saku.web.routen.suche import suchen

HTMX = {"HX-Request": "true"}


def test_heute_verlinkt_station_und_weiterlernen(client):
    html = client.get("/").get_data(as_text=True)
    assert 'href="/michi/1"' in html and 'data-taste="Enter"' in html
    assert 'class="enso' in html and 'id="suche-dialog"' in html


def test_keiko_runde_mit_tastatur(client, con):
    html = client.get("/keiko/").get_data(as_text=True)
    t_id = int(re.search(r'data-sensei-teilaufgabe="(\d+)"', html).group(1))
    assert 'data-taste=" "' in html and 'id="antwort"' in html
    loesung = client.get(f"/keiko/{t_id}/loesung", headers=HTMX).get_data(as_text=True)
    assert "tusche" in loesung and 'data-taste="3"' in loesung
    # Demo: 14 neue, der Termin verlangt 1 am Tag, das Mindestziel sind 10; nach der zehnten kommt お疲れ様
    runde = []
    for _ in range(10):
        antwort = client.post(f"/keiko/{t_id}/bewerten", data={"ergebnis": 3, "runde": ",".join(map(str, runde))}, headers=HTMX)
        runde.append(t_id)
        if "HX-Redirect" in antwort.headers:
            break
        t_id = int(re.search(r'data-sensei-teilaufgabe="(\d+)"', antwort.get_data(as_text=True)).group(1))
    assert antwort.headers["HX-Redirect"] == f"/keiko/?eben={runde[-1]}" and len(runde) == 10
    assert con.execute("SELECT status FROM karte WHERE teilaufgabe_id = ?", (runde[0],)).fetchone()[0] == "gelb"
    abschluss = client.get("/keiko/").get_data(as_text=True)
    assert "Tagesziel geschafft. <span lang=\"ja\">お疲れ様</span>" in abschluss and 'href="/keiko/?extra=1"' in abschluss
    # danach geht es weiter: Extra-Runde mit den restlichen neuen
    extra = client.get("/keiko/?extra=1").get_data(as_text=True)
    assert "Extra-Runde" in extra and 'name="extra" value="1"' in extra and "0 / 4" in extra

    naechste = client.post("/keiko/2/ueberspringen", data={"modus": "neu", "runde": ""}, headers=HTMX).get_data(as_text=True)
    assert 'name="runde" value="2"' in naechste and 'data-taste="ArrowRight"' in naechste


def test_michi_pfad_station_und_freischaltung(client, con):
    pfad_html = client.get("/michi/").get_data(as_text=True)
    assert "du bist hier" in pfad_html and pfad_html.count("gesperrt") >= 6

    station = client.get("/michi/1").get_data(as_text=True)
    assert "<strong>Projektmanagement</strong>" in station  # Einführung als Markdown
    assert "/keiko/?thema=" in station and "/keiko/?teilaufgabe=" in station
    assert client.get("/michi/2/test").status_code == 302  # gesperrt
    assert client.get("/michi/99").status_code == 404

    test = client.get("/michi/1/test").get_data(as_text=True)
    ids = re.findall(r'name="teilaufgabe" value="(\d+)"', test)
    assert 1 <= len(ids) <= 5 and "Lösung aufdecken" in test
    punkte = dict(con.execute("SELECT id, punkte FROM teilaufgabe").fetchall())
    daten = {"teilaufgabe": ids} | {f"punkte-{i}": str(punkte[int(i)]).replace(".", ",") for i in ids}
    ergebnis = client.post("/michi/1/test", data=daten, headers=HTMX).get_data(as_text=True)
    assert "Station geschafft" in ergebnis and "<html" not in ergebnis
    assert pfad.stationen(con)[1]["aktuell"]
    assert client.get("/michi/2/test").status_code == 200

    assert client.post("/michi/2/test", data={"teilaufgabe": "4", "punkte-4": "viel"}).status_code == 400


def test_shiken_simulation_bis_zum_hanko(client, con):
    assert "頑張って" in client.get("/shiken/").get_data(as_text=True)
    start = client.post("/shiken/neu", data={"bereich": "Entwicklung und Umsetzung von Algorithmen"})
    url = start.headers["Location"]
    assert client.post("/shiken/neu", data={"bereich": "Planen eines Softwareproduktes"}).headers["Location"] == url

    laufend = client.get(url).get_data(as_text=True)
    assert "shiken-laeuft" in laufend and 'role="timer"' in laufend
    ids = re.findall(r'name="antwort-(\d+)"', laufend)
    assert "Gespeichert" in client.post(url + "/speichern", data={f"antwort-{ids[0]}": "Meine Antwort"}, headers=HTMX).get_data(as_text=True)
    # mit Antwortformat (Optionen): die eigene Antwort darf das Format nicht überschreiben
    con.execute("UPDATE teilaufgabe SET inhalt = 'Welche Laufzeit?', antwort = ? WHERE id = ?",
                (json.dumps({"art": "einfach", "optionen": [{"wert": "1", "text": "O(n²)"}], "ziele": [], "richtig": ["1"],
                             "einheit": "", "vorlage": ""}), ids[0]))
    con.commit()
    wieder = client.get(url).get_data(as_text=True)
    assert "O(n²)" in wieder and ">Meine Antwort</textarea>" in wieder
    assert client.post(url + "/abgeben", data={}).headers["Location"].endswith("/auswertung")
    assert client.get(url).headers["Location"].endswith("/auswertung")

    auswertung = client.get(url + "/auswertung").get_data(as_text=True)
    assert "Meine Antwort" in auswertung and f'id="punkte-{ids[0]}"' in auswertung and "O(n²)" in auswertung
    punkte = dict(con.execute("SELECT id, punkte FROM teilaufgabe").fetchall())
    client.post(url + "/auswertung", data={f"punkte-{i}": punkte[int(i)] for i in ids})
    client.post(url + "/auswertung", data={f"punkte-{i}": 0 for i in ids})  # zweites Auswerten zählt nicht
    ergebnis = client.get(url + "/auswertung").get_data(as_text=True)
    assert "Bestanden mit 100 Punkten, sehr gut." in ergebnis and 'class="hanko"' in ergebnis
    assert con.execute("SELECT COUNT(*) FROM bewertung WHERE quelle = 'simulation'").fetchone()[0] == len(ids)
    assert "合格" in client.get("/shiken/").get_data(as_text=True)


def test_shiken_nicht_bestanden_und_zeitablauf(client, con):
    url = client.post("/shiken/neu", data={"bereich": "Planen eines Softwareproduktes"}).headers["Location"]
    con.execute("UPDATE simulation SET gestartet_am = datetime('now', '-2 hours')")
    con.commit()
    assert client.get(url).headers["Location"].endswith("/auswertung")  # Zeit abgelaufen: automatisch abgegeben
    client.post(url + "/auswertung", data={})
    ergebnis = client.get(url + "/auswertung").get_data(as_text=True)
    assert "Noch nicht. Die meisten Punkte kosteten:" in ergebnis and "hanko--sai" in ergebnis
    assert client.post("/shiken/neu", data={"bereich": "Gibt es nicht"}).status_code == 400


def test_suche_findet_wortteile(client, con):
    con.execute("INSERT INTO suche (teilaufgabe_id, titel, text, loesung) VALUES (4, 'Demo', 'Subnetting im Firmennetzwerk', '')")
    con.commit()
    assert 4 in [z["teilaufgabe_id"] for z in suchen(con, "subn")]
    assert {1, 4} <= {z["teilaufgabe_id"] for z in suchen(con, "netz")}
    assert suchen(con, "SQ")  # unter 3 Zeichen über LIKE
    assert suchen(con, '"%_') == []  # Sonderzeichen sind nur Text

    html = client.get("/suche/?q=netz", headers=HTMX).get_data(as_text=True)
    assert "/keiko/?teilaufgabe=1" in html and "Sommer 2023 · Aufgabe 1 a" in html
    assert "/keiko/?thema=" in client.get("/suche/?q=Daten").get_data(as_text=True)
    assert 'href="/keiko/"' in client.get("/suche/?q=üb").get_data(as_text=True)
    assert "Nichts gefunden" in client.get("/suche/?q=xyzxyz").get_data(as_text=True)


def test_punkte_nan_wird_abgewiesen(client, con):
    t_id = con.execute("SELECT teilaufgabe_id FROM v_zuordnung z JOIN station_thema st ON st.thema_id = z.thema_id "
                       "WHERE st.station_id = 1 LIMIT 1").fetchone()[0]
    antwort = client.post("/michi/1/test", data={"teilaufgabe": t_id, f"punkte-{t_id}": "nan"})
    assert antwort.status_code == 400


def test_einfuehrung_beim_ersten_start(client, con):
    con.execute("DELETE FROM einstellung WHERE schluessel = 'einfuehrung'")
    con.commit()
    assert client.get("/").headers["Location"] == "/willkommen"
    html = client.get("/willkommen").get_data(as_text=True)
    assert html.count('class="szene"') == 7 and 'data-zaehlen=' in html and 'class="leiste"' not in html

    assert client.post("/willkommen/termin", data={"pruefungstermin": "kein Datum"}).status_code == 400
    rechnung = client.post("/willkommen/termin", data={"pruefungstermin": "2099-01-01"}).get_data(as_text=True)
    assert "bis zur AP2" in rechnung and "neue Teilaufgabe" in rechnung
    assert con.execute("SELECT wert FROM einstellung WHERE schluessel = 'pruefungstermin'").fetchone()[0] == "2099-01-01"

    assert client.post("/willkommen/fertig", data={"ziel": "station"}).headers["Location"] == "/michi/1"
    assert client.get("/").status_code == 200


def test_anklickbare_aufgabe_pruefen(client, con):
    """Erfundene Auswahlaufgabe: Zifferntasten, Prüfen, Urteil und Bewertung mit ↵."""
    t_id = con.execute("SELECT id FROM teilaufgabe ORDER BY id LIMIT 1").fetchone()[0]
    antwort = {"art": "einfach", "optionen": [{"wert": "1", "text": "Kündigung"}, {"wert": "2", "text": "Befristung"}],
               "ziele": [], "richtig": ["2"], "einheit": "", "vorlage": ""}
    con.execute("UPDATE teilaufgabe SET inhalt = 'Welche **Vereinbarung** ist zulässig?', antwort = ?, "
                "loesung_inhalt = 'Nur die **2**.' WHERE id = ?", (json.dumps(antwort), t_id))
    con.commit()

    html = client.get(f"/keiko/?teilaufgabe={t_id}").get_data(as_text=True)
    assert "<strong>Vereinbarung</strong>" in html and 'data-taste="2"' in html and f"/keiko/{t_id}/pruefen" in html
    assert "Original ansehen" in html  # die Ausschnitte bleiben erreichbar

    falsch = client.post(f"/keiko/{t_id}/pruefen", data={"wahl": "1"}).get_data(as_text=True)
    assert "Leider falsch." in falsch and "wahl-option--falsch" in falsch and "wahl-option--richtig" in falsch
    assert '<div id="antwortfeld" hx-swap-oob="true"' in falsch  # markierte Optionen ersetzen das Feld
    assert 'data-taste="Enter"' in falsch and "Nicht gewusst" in falsch and "<strong>2</strong>" in falsch
    richtig = client.post(f"/keiko/{t_id}/pruefen", data={"wahl": "2"}).get_data(as_text=True)
    assert "Richtig." in richtig and 'data-taste="2"' not in richtig.split("hx-swap-oob")[-1]  # Optionen gesperrt

    tid_frei = con.execute("SELECT id FROM teilaufgabe WHERE antwort IS NULL LIMIT 1").fetchone()[0]
    assert client.post(f"/keiko/{tid_frei}/pruefen", data={}).status_code == 400

    # außerhalb von Üben (Sensei, Simulation, Mini-Test) stehen die Optionen als Text dabei
    from saku.sensei import prompts
    kontext = prompts.kontext(con, prompts.teilaufgabe(con, t_id))
    assert "**2** Befristung" in kontext and "Nur die **2**." in kontext


def test_loesung_mit_antwort_holt_vorschlag(client, con):
    t_id = con.execute("SELECT id FROM teilaufgabe ORDER BY id LIMIT 1").fetchone()[0]
    ohne = client.get(f"/keiko/{t_id}/loesung").get_data(as_text=True)
    mit = client.get(f"/keiko/{t_id}/loesung", query_string={"antwort": "Primärschlüssel"}).get_data(as_text=True)
    assert 'hx-trigger="load"' not in ohne
    # ohne API-Schlüssel (Tests) kein Vorschlag, mit Schlüssel holt die Lösung ihn automatisch
    assert ('hx-trigger="load"' in mit) == client.application.config["SENSEI_BEREIT"]


def test_variante_nach_fehler(client, con):
    t_id, aehnlich = con.execute("SELECT teilaufgabe_id, aehnlich_id FROM aehnlichkeit ORDER BY 1 LIMIT 1").fetchone()
    assert varianten(con, [t_id]) == []
    client.post(f"/keiko/{t_id}/bewerten", data={"ergebnis": 1, "runde": ""}, headers=HTMX)
    assert aehnlich in varianten(con, [t_id])
    client.post(f"/keiko/{t_id}/bewerten", data={"ergebnis": 3, "runde": ""}, headers=HTMX)
    assert varianten(con, [t_id]) == []  # danach gewusst: keine Variante mehr


def test_grundwissen_begriffs_karten(client, con):
    assert "Noch keine Begriffs-Karten" in client.get("/keiko/grundwissen").get_data(as_text=True)
    b_id = con.execute("INSERT INTO begriff (name, slug, erklaerung) VALUES ('Fremdschlüssel', 'fremdschluessel', "
                       "'Verweist auf den **Primärschlüssel** einer anderen Tabelle.')").lastrowid
    con.execute("INSERT INTO teilaufgabe_begriff (teilaufgabe_id, begriff_id) SELECT teilaufgabe_id, ? FROM v_teilaufgabe LIMIT 2", (b_id,))
    con.commit()
    html = client.get("/keiko/grundwissen").get_data(as_text=True)
    assert "Fremdschlüssel" in html and "<strong>Primärschlüssel</strong>" in html and "0 fällig · 1 neu" in html
    weiter = client.post(f"/keiko/grundwissen/{b_id}/bewerten", data={"ergebnis": 3, "runde": ""}, headers=HTMX).get_data(as_text=True)
    assert "Grundwissen für heute geschafft" in weiter
    assert con.execute("SELECT status FROM begriff_karte WHERE begriff_id = ?", (b_id,)).fetchone()[0] == "gelb"
    assert client.post(f"/keiko/grundwissen/{b_id}/bewerten", data={"ergebnis": 7}).status_code == 400


def test_befehlspalette(client, con):
    assert "Prüfung simulieren" in client.get("/").get_data(as_text=True)  # leere Palette zeigt die ersten Befehle
    html = client.get("/suche/", query_string={"q": "ap1"}).get_data(as_text=True)
    assert "Zu AP1 wechseln" in html and 'hx-post="/einstellungen/teil"' in html and "hx-vals='{\"teil\": \"AP1\"}'" in html
    assert "Farbschema dunkel" in client.get("/suche/", query_string={"q": "dunkel"}).get_data(as_text=True)
    assert client.post("/einstellungen/teil", data={"teil": "AP1"}).headers["HX-Refresh"] == "true"


def test_zurueck_nimmt_bewertung_zurueck(client, con):
    t_id = int(re.search(r'data-sensei-teilaufgabe="(\d+)"', client.get("/keiko/").get_data(as_text=True)).group(1))
    weiter = client.post(f"/keiko/{t_id}/bewerten", data={"ergebnis": 3, "runde": ""}, headers=HTMX).get_data(as_text=True)
    assert 'data-taste="ArrowLeft"' in weiter
    zurueck = client.post("/keiko/zurueck", data={"runde": str(t_id)}, headers=HTMX).get_data(as_text=True)
    assert f'data-sensei-teilaufgabe="{t_id}"' in zurueck and 'name="runde" value=""' in zurueck
    assert 'data-taste="ArrowLeft"' not in zurueck  # ganz am Anfang gibt es kein Zurück
    assert con.execute("SELECT COUNT(*) FROM bewertung").fetchone()[0] == 0
    assert con.execute("SELECT status FROM karte WHERE teilaufgabe_id = ?", (t_id,)).fetchone()[0] == "neu"
    assert client.post("/keiko/zurueck", data={"runde": ""}).status_code == 400


def test_karte_zeigt_verlauf_und_wann_sie_wiederkommt(client, con):
    html = client.get("/keiko/").get_data(as_text=True)
    t_id = int(re.search(r'data-sensei-teilaufgabe="(\d+)"', html).group(1))
    assert "Neu" in html and "neu aus dem Tagesziel" in html
    weiter = client.post(f"/keiko/{t_id}/bewerten", data={"ergebnis": 1, "runde": ""}, headers=HTMX).get_data(as_text=True)
    assert re.search(r"Aufgabe \d+ \w+: wieder dran in \d+ min · liegt im Fehlerkorb", weiter)

    karte = client.get(f"/keiko/?teilaufgabe={t_id}").get_data(as_text=True)
    assert "Fehlerkorb · zuletzt" in karte and "nicht gewusst</span> heute" in karte and "noch 2× „Gewusst“ bis sicher" in karte
    client.post(f"/keiko/{t_id}/bewerten", data={"ergebnis": 3, "runde": ""}, headers=HTMX)
    karte = client.get(f"/keiko/?teilaufgabe={t_id}").get_data(as_text=True)
    assert "Wiederholung · zuletzt" in karte and "gewusst</span> heute" in karte and "noch 1× „Gewusst“ bis sicher" in karte
    assert "direkt geöffnet" in karte  # gelb und noch nicht fällig: steht heute nicht an

    con.execute("UPDATE karte SET faellig_am = datetime('now', '-1 hour') WHERE teilaufgabe_id = ?", (t_id,))
    con.execute("DELETE FROM bewertung")  # sonst gilt sie als heute schon wiederholt
    con.commit()
    assert "fällig seit heute" in client.get(f"/keiko/?teilaufgabe={t_id}").get_data(as_text=True)


def test_wann_und_tag():
    from datetime import datetime, timedelta, timezone

    from saku.lernen.karten import sqlite_zeit
    from saku.web.routen.keiko import tag, wann

    jetzt = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc).astimezone()
    assert wann(sqlite_zeit(jetzt + timedelta(minutes=9, seconds=30)), jetzt) == "in 10 min"
    assert wann(sqlite_zeit(jetzt - timedelta(minutes=5)), jetzt) == "in 1 min"
    assert wann(sqlite_zeit(jetzt + timedelta(hours=2)), jetzt).startswith("heute um ")
    assert wann(sqlite_zeit(jetzt + timedelta(days=1)), jetzt) == "morgen"
    assert wann(sqlite_zeit(jetzt + timedelta(days=10)), jetzt) == "am 3.11."
    assert wann(sqlite_zeit(jetzt + timedelta(days=100)), jetzt) == "am 1.2.2027"
    assert tag(sqlite_zeit(jetzt), jetzt.date()) == "heute"
    assert tag(sqlite_zeit(jetzt - timedelta(days=1)), jetzt.date()) == "gestern"
    assert tag(sqlite_zeit(jetzt - timedelta(days=2)), jetzt.date()) == "22.10."


def test_verlauf_nach_tagen_mit_filter(client, con):
    assert "Noch keine Bewertung" in client.get("/keiko/verlauf").get_data(as_text=True)
    from datetime import datetime, timedelta, timezone

    from saku.lernen import karten
    jetzt = datetime.now(timezone.utc)
    karten.bewerten(con, 1, 1, jetzt=jetzt - timedelta(days=1), dauer_s=120)
    karten.bewerten(con, 1, 3, jetzt=jetzt, quelle="sensei", punkte=5)
    karten.bewerten(con, 2, 2, jetzt=jetzt, quelle="simulation")
    html = client.get("/keiko/verlauf").get_data(as_text=True)
    assert 'id="tag-1">Heute</h2>' in html and 'id="tag-2">Gestern</h2>' in html
    assert "2 Bewertungen · 2 Teilaufgaben" in html and "etwa 2 min" in html
    assert 'href="/keiko/?teilaufgabe=1"' in html and "Sommer 2023 · Aufgabe 1 a" in html
    assert "5 / 6" in html and "Sensei" in html and "Simulation" in html

    falsch = client.get("/keiko/verlauf?ergebnis=1").get_data(as_text=True)
    assert 'id="tag-1">Gestern</h2>' in falsch and 'aria-current="true"' in falsch
    assert "Keine Bewertung mit diesem Ergebnis" in client.get("/keiko/verlauf?ergebnis=2&seite=1").get_data(as_text=True)

    # Seiten: ältere Bewertungen auf der nächsten Seite
    from saku.web.routen import keiko
    keiko.VERLAUF_SEITE, alt = 2, keiko.VERLAUF_SEITE
    try:
        erste = client.get("/keiko/verlauf").get_data(as_text=True)
        assert "?seite=1" in erste and "Gestern</h2>" not in erste
        assert 'id="tag-1">Gestern</h2>' in client.get("/keiko/verlauf?seite=1").get_data(as_text=True)
    finally:
        keiko.VERLAUF_SEITE = alt

    assert "Verlauf" in client.get("/suche/", query_string={"q": "verlauf"}).get_data(as_text=True)
    assert 'href="/keiko/verlauf"' in client.get("/").get_data(as_text=True)


def test_shiken_wertet_anklickbare_aufgaben_aus(client, con):
    url = client.post("/shiken/neu", data={"bereich": "Entwicklung und Umsetzung von Algorithmen"}).headers["Location"]
    ids = [z[0] for z in con.execute("SELECT teilaufgabe_id FROM simulation_teilaufgabe ORDER BY position")]
    auswahl, zahl, leer = ids[:3]
    format_ = {"ziele": [], "einheit": "", "vorlage": ""}
    con.execute("UPDATE teilaufgabe SET antwort = ? WHERE id = ?", (json.dumps(format_ | {
        "art": "einfach", "optionen": [{"wert": "A", "text": "O(n)"}, {"wert": "B", "text": "O(n²)"}], "richtig": ["B"]}), auswahl))
    con.execute("UPDATE teilaufgabe SET antwort = ? WHERE id IN (?, ?)",
                (json.dumps(format_ | {"art": "zahl", "optionen": [], "richtig": ["1024"], "einheit": "Byte"}), zahl, leer))
    con.commit()

    heft = client.get(url).get_data(as_text=True)
    assert f'name="antwort-{auswahl}-wahl"' in heft and f'name="antwort-{zahl}-art"' in heft
    assert 'data-taste="A"' not in heft and f'name="antwort-{auswahl}"' not in heft  # keine Tasten, kein Freitext
    client.post(url + "/speichern", data={f"antwort-{auswahl}-art": "einfach", f"antwort-{auswahl}-wahl": "B",
                                          f"antwort-{zahl}-art": "zahl", f"antwort-{zahl}-zahl": "1024",
                                          f"antwort-{leer}-art": "zahl"}, headers=HTMX)
    gespeichert = json.loads(con.execute("SELECT antwort FROM simulation_teilaufgabe WHERE teilaufgabe_id = ?", (auswahl,)).fetchone()[0])
    assert gespeichert["wahl"] == ["B"]
    assert re.search(r'value="B"\s+checked', client.get(url).get_data(as_text=True))
    client.post(url + "/abgeben", data={})

    punkte = dict(con.execute("SELECT id, punkte FROM teilaufgabe").fetchall())
    auswertung = client.get(url + "/auswertung").get_data(as_text=True)
    assert f'name="punkte-{auswahl}"' in auswertung and re.search(rf'id="punkte-{auswahl}"[^>]*value="{punkte[auswahl]:g}"', auswertung)
    assert re.search(rf'id="punkte-{leer}"[^>]*value="0"', auswertung) and "automatisch bewertet" in auswertung
    assert "wahl-option--richtig" in auswertung and "zahl-eingabe--falsch" in auswertung

    # vorbelegt ist nur ein Vorschlag: hier überschreibt die eigene Bewertung die leere Antwort
    client.post(url + "/auswertung", data={f"punkte-{i}": punkte[i] if i in (auswahl, zahl) else 1 if i == leer else 0 for i in ids})
    assert con.execute("SELECT antwort FROM bewertung WHERE teilaufgabe_id = ?", (auswahl,)).fetchone()[0] == "Gewählt: B"
    fertig = client.get(url + "/auswertung").get_data(as_text=True)
    assert fertig.count("automatisch bewertet") == 2 and "selbst bewertet, automatisch wären es 0" in fertig
