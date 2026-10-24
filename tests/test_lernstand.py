"""Lernstand exportieren und in eine neu aufgebaute Datenbank (andere IDs) importieren – mit erfundenen Demo-Daten."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from saku import config, db
from saku.lernen import karten, lernstand, pfad, simulation
from tests import demo_daten


def _id(con, jahr, saison, nummer, kennung) -> int:
    return con.execute("SELECT t.id FROM teilaufgabe t JOIN aufgabe a ON a.id = t.aufgabe_id JOIN pruefung p ON p.id = a.pruefung_id "
                       "WHERE p.jahr = ? AND p.saison = ? AND a.nummer = ? AND t.kennung = ?", (jahr, saison, nummer, kennung)).fetchone()[0]


def _vergleichbar(con) -> dict:
    """Der Export ohne Zeitstempel, Listen sortiert: gleich, wenn der Lernstand gleich ist."""
    daten = lernstand.exportieren(con)
    del daten["exportiert_am"]
    return {k: sorted(v, key=lambda z: json.dumps(z, sort_keys=True)) if isinstance(v, list) else v for k, v in daten.items()}


def _begriffe(con, namen) -> None:
    for name in namen:
        con.execute("INSERT INTO begriff (name, slug) VALUES (?, ?)", (name, name.lower()))
    con.commit()


def test_lernstand_uebersteht_neuaufbau(tmp_path, monkeypatch):
    con = db.verbinden(demo_daten.anlegen(tmp_path / "alt"))
    _begriffe(con, ["Fremdschlüssel", "Primärschlüssel"])
    gestern = datetime.now(timezone.utc) - timedelta(days=1)
    t1, t2, t3 = _id(con, 2023, "Sommer", 1, "b"), _id(con, 2024, "Sommer", 1, "c"), _id(con, 2023, "Winter", 2, "a")
    karten.bewerten(con, t1, 1, jetzt=gestern, dauer_s=90, antwort="Weiß nicht")
    karten.bewerten(con, t1, 3, punkte=4)
    karten.bewerten(con, t2, 2, quelle="sensei")
    karten.markieren(con, t3)
    karten.begriff_bewerten(con, 2, 3)  # Primärschlüssel
    con.execute("INSERT INTO luecke (teilaufgabe_id, text, operator) VALUES (?, 'Begründung fehlt', 'erlaeutern')", (t2,))
    sim_id = simulation.zusammenstellen(con, "Planen eines Softwareproduktes")
    simulation.auswerten(con, sim_id, {t1: 4})
    pfad.test_auswerten(con, 1, {i: 99 for i in pfad.teilaufgaben(con, 1)})
    con.execute("DELETE FROM teilaufgabe_thema WHERE teilaufgabe_id = ?", (t3,))
    con.execute("INSERT INTO teilaufgabe_thema (teilaufgabe_id, thema_id, gewicht, quelle) "
                "SELECT ?, id, 1.0, 'manuell' FROM thema WHERE slug = 'er-modell'", (t3,))
    db.setze_einstellung(con, "farbschema", "hell")
    con.executemany("INSERT INTO rechenuebung (art, seed, richtig, felder_richtig, felder_gesamt, dauer_s, zeitpunkt) "
                    "VALUES (?, ?, ?, ?, 2, ?, ?)", [("subnetz", 7, 1, 2, 40, "2026-10-20 08:00:00"),
                                                     ("datenmenge", 7, 0, 1, None, "2026-10-20 08:00:00")])
    con.commit()
    vorher = _vergleichbar(con)
    datei = json.loads(json.dumps(lernstand.exportieren(con)))  # wie über die Datei

    # Neuaufbau: Prüfungen und Begriffe in anderer Reihenfolge, also andere IDs
    monkeypatch.setattr(demo_daten, "PRUEFUNGEN", demo_daten.PRUEFUNGEN[::-1])
    neu = db.verbinden(demo_daten.anlegen(tmp_path / "neu"))
    _begriffe(neu, ["Primärschlüssel", "Fremdschlüssel"])
    assert _id(neu, 2023, "Sommer", 1, "b") != t1
    datei["bewertungen"].append(datei["bewertungen"][0] | {"teilaufgabe": [1999, "Sommer", "AP2", "Gibt es nicht", "1201", 1, "a"]})

    zahlen = lernstand.importieren(neu, datei)
    assert _vergleichbar(neu) == vorher
    assert zahlen["bewertungen"] == [len(datei["bewertungen"]) - 1, 1]  # die unbekannte Teilaufgabe übersprungen
    assert zahlen["karten"] == [len(datei["karten"]), 0] and zahlen["simulationen"] == [1, 0] and zahlen["stationstests"] == [1, 0]
    assert zahlen["rechenuebungen"] == [2, 0] and len(datei["rechenuebungen"]) == 2
    karte = "SELECT status, serie, fsrs, faellig_am FROM karte WHERE teilaufgabe_id = ?"
    assert neu.execute(karte, (_id(neu, 2023, "Sommer", 1, "b"),)).fetchone()[:] == con.execute(karte, (t1,)).fetchone()[:]

    # zweimal importieren ändert nichts
    nochmal = lernstand.importieren(neu, datei)
    assert all(uebernommen == 0 for uebernommen, _ in nochmal.values()) and _vergleichbar(neu) == vorher

    # nach dem Export weitergelernt: ein späterer Import des alten Stands überschreibt die Karte nicht
    karten.bewerten(neu, _id(neu, 2024, "Sommer", 1, "c"), 1)
    lernstand.importieren(neu, datei)
    assert neu.execute("SELECT status FROM karte WHERE teilaufgabe_id = ?", (_id(neu, 2024, "Sommer", 1, "c"),)).fetchone()[0] == "rot"

    with pytest.raises(ValueError):
        lernstand.importieren(neu, {"format": "etwas anderes"})
    con.close()
    neu.close()


def test_lernstand_befehl_und_download(tmp_path, monkeypatch, client, daten, capsys):
    monkeypatch.setattr(config, "DATEN", daten)
    from saku.__main__ import lernstand_datei

    con = db.verbinden(config.db_pfad(daten))
    karten.bewerten(con, 1, 3)
    con.close()
    datei = tmp_path / "lernstand.json"
    lernstand_datei("export", datei)
    assert json.loads(datei.read_text(encoding="utf-8"))["bewertungen"][0]["teilaufgabe"][:2] == [2023, "Sommer"]
    lernstand_datei("import", datei)
    assert "bewertungen: 0 übernommen, 1 übersprungen" in capsys.readouterr().out

    datei.write_text("kein JSON", encoding="utf-8")
    with pytest.raises(SystemExit, match="nichts geändert"):
        lernstand_datei("import", datei)

    antwort = client.get("/einstellungen/lernstand.json")
    assert "attachment; filename=saku-lernstand-" in antwort.headers["Content-Disposition"]
    assert antwort.get_json()["format"] == "saku-lernstand"
    assert 'href="/einstellungen/lernstand.json"' in client.get("/einstellungen").get_data(as_text=True)


def test_import_prueft_einstellungen_wie_die_einstellungen(con, client):
    """Die Datei kommt vom Nutzer: Werte, die die Einstellungen ablehnen würden, dürfen auch der Import nicht setzen,
    sonst bricht Heute (Termin, Puffer) mit Fehler 500 ab."""
    datei = lernstand.exportieren(con)
    datei["einstellungen"] |= {"pruefungstermin": "bald", "puffer_tage": "viele", "farbschema": "lila",
                               "niwa_stufen": "[1]", "einfuehrung": "gesehen", "teil": "AP2"}
    zahlen = lernstand.importieren(con, datei)
    assert client.get("/").status_code == 200 and client.get("/einstellungen").status_code == 200
    assert client.get("/niwa/").status_code == 200
    werte = dict(con.execute("SELECT schluessel, wert FROM einstellung").fetchall())
    assert werte["pruefungstermin"] != "bald" and werte["puffer_tage"] == "7" and werte["farbschema"] != "lila"
    assert zahlen["einstellungen"][1] >= 4


@pytest.mark.parametrize("kaputt", [
    {"einstellungen": ["keine", "Zuordnung"]},
    {"bewertungen": [{"teilaufgabe": [2023, "Sommer", "AP2", "Planen eines Softwareproduktes", "1201", 1, "a"],
                      "zeitpunkt": "2026-10-01 10:00:00", "ergebnis": 7, "quelle": "selbst", "dauer_s": None, "antwort": None, "punkte": None}]},
    {"karten": "nicht einmal eine Liste"},
])
def test_kaputte_datei_bricht_ohne_aenderung_ab(daten, monkeypatch, tmp_path, kaputt):
    monkeypatch.setattr(config, "DATEN", daten)
    from saku.__main__ import lernstand_datei
    con = db.verbinden(config.db_pfad(daten))
    vorher = _vergleichbar(con)
    datei = tmp_path / "kaputt.json"
    datei.write_text(json.dumps({"format": "saku-lernstand", "version": 1} | kaputt), encoding="utf-8")
    with pytest.raises(SystemExit, match="nichts geändert"):
        lernstand_datei("import", datei)
    assert _vergleichbar(con) == vorher
    con.close()


def test_import_ueberspringt_falsche_typen(con, client):
    """Eine von Hand bearbeitete Datei: Zeitpunkte, Zahlen und JSON in falscher Form übernimmt der Import nicht, sonst brachen
    danach Heute (Lerntage), Rechnen (letzter Versuch) oder das Bewerten (Serie) ab."""
    karten.bewerten(con, 1, 3)
    datei = lernstand.exportieren(con)
    gut = datei["bewertungen"][0]
    datei["bewertungen"] = [gut | {"zeitpunkt": "gestern"}, gut | {"zeitpunkt": "2026-10-01 10:00:00", "punkte": "viele"}]
    datei["karten"] = [datei["karten"][0] | {"serie": "x", "geaendert_am": "2099-01-01 00:00:00"},
                       datei["karten"][0] | {"fsrs": "{kaputt", "geaendert_am": "2099-01-01 00:00:00"}]
    datei["rechenuebungen"] = [{"art": "subnetz", "seed": 1, "richtig": 1, "felder_richtig": 1, "felder_gesamt": 1,
                                "dauer_s": None, "zeitpunkt": "kaputt"}]
    zahlen = lernstand.importieren(con, datei)
    assert zahlen["bewertungen"] == [0, 2] and zahlen["karten"] == [0, 2] and zahlen["rechenuebungen"] == [0, 1]
    for url in ("/", "/keiko/verlauf", "/rechnen/", "/fahrplan"):
        assert client.get(url).status_code == 200, url
    assert client.post("/keiko/1/bewerten", data={"ergebnis": "3"}, headers={"HX-Request": "true"}).status_code == 200
