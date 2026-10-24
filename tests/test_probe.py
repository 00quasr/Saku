"""Probeprüfung aus den Generatoren: Zusammenstellung, Ablauf mit Auswertung, Verlauf, Hochrechnung (erfundene Daten)."""

import json
import random

import pytest
from markupsafe import escape

from saku import db
from saku.lernen import hochrechnung, probepruefung, rechnen
from saku.web.routen.rechnen import heute_gerechnet
from saku.web.routen.suche import befehle


@pytest.mark.parametrize("pfad", ["AP1", "AP2-1201", "AP2-1202"])
def test_zusammenstellung_100_punkte_alle_gruppen_nur_umfang(pfad):
    erlaubt = rechnen.im_umfang(pfad)
    gruppen = {rechnen.ARTEN[a].gruppe for a in erlaubt}
    for seed in range(300):
        quoten = {a: random.Random(seed * 7 + i).random() for i, a in enumerate(erlaubt)}
        aufgaben = probepruefung.zusammenstellen(pfad, quoten, random.Random(seed))
        arten = [a for a, _, _ in aufgaben]
        assert sum(p for *_, p in aufgaben) == 100 and all(p > 0 for *_, p in aufgaben)
        assert len(arten) == len(set(arten)) == probepruefung.ANZAHL and set(arten) <= set(erlaubt)
        assert {rechnen.ARTEN[a].gruppe for a in arten} == gruppen, (pfad, seed)
        assert aufgaben == probepruefung.zusammenstellen(pfad, quoten, random.Random(seed))  # reproduzierbar
        # mehr Aufwand, mehr Punkte: Pseudocode schreiben vor SQL vor einem Steckbrief
        for a, _, p in aufgaben:
            for b, _, q in aufgaben:
                if probepruefung.AUFWAND.get(a, 1) > probepruefung.AUFWAND.get(b, 1):
                    assert p > q, (a, b, aufgaben)


def test_schwaechere_arten_etwas_haeufiger():
    gezogen = [a for seed in range(400) for a, _, _ in probepruefung.zusammenstellen("AP1", {"ports": 0.0, "subnetz": 1.0},
                                                                                     random.Random(seed))]
    assert gezogen.count("ports") > 1.5 * gezogen.count("subnetz")


def test_verteilen():
    assert probepruefung.verteilen([1] * 7) == [15, 15, 14, 14, 14, 14, 14]
    assert probepruefung.verteilen([3, 2, 1, 1]) == [43, 29, 14, 14]


def _ap1(client, con) -> tuple[str, int]:
    db.setze_einstellung(con, "teil", "AP1")
    url = client.post("/rechnen/probe/neu").headers["Location"]
    return url, int(url.rsplit("/", 1)[1])


def _zeile(con, pp_id: int):
    return con.execute("SELECT * FROM probepruefung WHERE id = ?", (pp_id,)).fetchone()


def _musterloesungen(zeile) -> dict[str, str]:
    return {f"a{i}-{f.name}": f.loesung if f.typ in ("sql", "code") else f.anzeige
            for i, x in enumerate(probepruefung.aufgaben(zeile), start=1) for f in x["aufgabe"].felder}


def test_ablauf_alles_richtig_note_1_und_rechenuebung(client, con):
    url, pp_id = _ap1(client, con)
    html = client.get(url).get_data(as_text=True)
    assert html.count('class="heft-aufgabe"') == 12 and 'id="uhr"' in html and "shiken-laeuft" in html
    assert _zeile(con, pp_id)["pfad"] == "AP1" and "Einrichten eines IT-gestützten Arbeitsplatzes" in html
    assert '<span class="umfang-teil">AP1</span>' in html  # die Seitenleiste zeigt den Umfang weiter
    daten = _musterloesungen(_zeile(con, pp_id))
    assert client.post(url + "/speichern", data=daten).get_data(as_text=True).startswith("Gespeichert")
    assert json.loads(_zeile(con, pp_id)["eingaben"]) == daten
    seite = client.get(url).get_data(as_text=True)  # gespeichert steht im Feld: als value="…" oder im Textfeld (SQL, Pseudocode)
    assert all(str(escape(w)) in seite for w in daten.values())
    assert client.post("/rechnen/probe/neu").headers["Location"] == url  # die laufende statt einer zweiten

    client.post(url + "/abgeben", data=daten)
    zeile = _zeile(con, pp_id)
    assert zeile["punkte"] == 100 and zeile["note"] == 1 and zeile["beendet_am"]
    html = client.get(url).get_data(as_text=True)
    assert "Note 1 · sehr gut" in html and html.count("Ähnliches rechnen") == 12 and html.count("<summary>Lösungsweg</summary>") == 12
    assert "shiken-laeuft" not in html and 'id="uhr"' not in html
    zeilen = con.execute("SELECT art, seed, richtig FROM rechenuebung ORDER BY id").fetchall()
    assert [(z[0], z[1]) for z in zeilen] == [(a, s) for a, s, _ in json.loads(zeile["aufgaben"])] and all(z[2] for z in zeilen)
    assert heute_gerechnet(con) == (12, 12)  # Tagesziel; Lerntag:
    assert con.execute("SELECT bewertungen FROM v_lerntage WHERE tag = date('now', 'localtime')").fetchone()[0] == 12

    client.post(url + "/abgeben", data={})  # neu laden schickt noch einmal ab: nichts ändert sich
    assert con.execute("SELECT COUNT(*) FROM rechenuebung").fetchone()[0] == 12 and _zeile(con, pp_id)["punkte"] == 100
    assert client.post(url + "/speichern", data={}).get_data(as_text=True) == "Schon abgegeben"
    verlauf = client.get("/rechnen/probe").get_data(as_text=True)
    assert f'href="{url}"' in verlauf and "1 · sehr gut" in verlauf and "Bestanden" in verlauf


def test_leer_null_punkte_und_teilpunkte_anteilig(client, con):
    url, pp_id = _ap1(client, con)
    client.post(url + "/abgeben", data={})
    assert (_zeile(con, pp_id)["punkte"], _zeile(con, pp_id)["note"]) == (0, 6)
    assert con.execute("SELECT COUNT(*), SUM(richtig) FROM rechenuebung").fetchone()[:] == (12, 0)

    url, pp_id = _ap1(client, con)
    aufgaben = probepruefung.aufgaben(_zeile(con, pp_id))
    for i, x in enumerate(aufgaben, start=1):  # eine Aufgabe mit mehreren Feldern, davon nur das erste richtig
        f = x["aufgabe"].felder[0]
        werte = probepruefung.bewerten(x["aufgabe"], {f.name: f.anzeige})
        if f.typ not in ("sql", "code") and f.anzeige and 0 < sum(werte.values()) < len(werte):
            break
    else:
        pytest.skip("keine Aufgabe mit mehreren Feldern gezogen")
    client.post(url + "/abgeben", data={f"a{i}-{f.name}": f.anzeige})
    erwartet = round(x["punkte"] * sum(werte.values()) / len(werte), 1)
    assert 0 < _zeile(con, pp_id)["punkte"] == erwartet < x["punkte"]
    html = client.get(url).get_data(as_text=True)
    assert f"{erwartet:g}".replace(".", ",") + f" / {x['punkte']}" in html


def _probe(con, aufgaben, minuten_her: int = 0) -> int:
    pp_id = con.execute("INSERT INTO probepruefung (pfad, aufgaben, dauer_min, gestartet_am) VALUES "
                        "('AP1', ?, 90, datetime('now', ?))", (json.dumps(aufgaben), f"-{minuten_her} minutes")).lastrowid
    con.commit()
    return pp_id


def test_sql_und_pseudocode_im_heft_ausfuehren(client, con):
    pp_id = _probe(con, [["select", 5, 40], ["algorithmus", 5, 60]])
    html = client.get(f"/rechnen/probe/{pp_id}").get_data(as_text=True)
    assert 'id="a1-sql-ergebnis"' in html and 'hx-target="#a2-sql-ergebnis"' in html and '"praefix": "a2-"' in html
    sql, code = (rechnen.erzeugen(art, 5).felder[0] for art in ("select", "algorithmus"))
    antwort = client.post("/rechnen/select/sql", data={"seed": "5", "praefix": "a1-", f"a1-{sql.name}": sql.loesung}).get_data(as_text=True)
    assert "<table" in antwort and "sql-fehler" not in antwort
    antwort = client.post("/rechnen/algorithmus/code", data={"seed": "5", "praefix": "a2-", f"a2-{code.name}": code.loesung})
    assert "Ausgabe" in antwort.get_data(as_text=True)
    client.post(f"/rechnen/probe/{pp_id}/abgeben", data={f"a1-{sql.name}": sql.loesung})  # nur SQL richtig
    assert (_zeile(con, pp_id)["punkte"], _zeile(con, pp_id)["note"]) == (40, 5)


def test_zeit_um_und_routen_robust(client, con):
    abgelaufen = _probe(con, [["subnetz", 1, 100]], minuten_her=120)
    assert 'data-rest="0"' in client.get(f"/rechnen/probe/{abgelaufen}").get_data(as_text=True)  # die Seite gibt gleich ab
    assert "Nicht abgegeben" in client.get("/rechnen/probe").get_data(as_text=True)
    assert client.post("/rechnen/probe/neu").headers["Location"] != f"/rechnen/probe/{abgelaufen}"  # keine laufende mehr

    kaputt, leer = _probe(con, [["gibtsnicht", 1, 100]]), _probe(con, [])
    for url in ("/rechnen/probe/999", "/rechnen/probe/abc", "/rechnen/probe/-1", f"/rechnen/probe/{kaputt}", f"/rechnen/probe/{leer}"):
        assert client.get(url).status_code == 404, url
    for url in ("/rechnen/probe/999/speichern", "/rechnen/probe/999/abgeben", f"/rechnen/probe/{kaputt}/abgeben",
                f"/rechnen/probe/{leer}/abgeben"):
        assert client.post(url).status_code == 404, url
    assert client.get("/rechnen/probe/" + "9" * 30).status_code == 400  # größer als SQLite speichert
    assert client.get("/rechnen/probe").status_code == 200


def test_einstiege(client, con):
    assert 'action="/rechnen/probe/neu"' in client.get("/shiken/").get_data(as_text=True)
    con.execute("DELETE FROM pruefung")
    con.commit()
    leer = client.get("/shiken/").get_data(as_text=True)  # braucht keinen Katalog: auch auf der leeren Seite
    assert "Noch ist der Garten leer" in leer and 'action="/rechnen/probe/neu"' in leer
    assert 'href="/rechnen/probe"' in client.get("/rechnen/").get_data(as_text=True)
    assert befehle("probeprüfung")[0][3] == ("rechnen.probe", {})


def test_hochrechnung_schaetzt_ap1_aus_probepruefungen(con):
    def ap1():
        return next(z for z in hochrechnung.stand(con)["zeilen"] if z["schluessel"] == "ap1")
    assert ap1()["wert"] is None
    for pfad, punkte in [("AP1", 40), ("AP1", 60), ("AP1", 70), ("AP2-1201", 10), ("AP1", 80.5)]:
        con.execute("INSERT INTO probepruefung (pfad, aufgaben, dauer_min, beendet_am, punkte, note) "
                    "VALUES (?, '[]', 90, datetime('now'), ?, 3)", (pfad, punkte))
    con.execute("INSERT INTO probepruefung (pfad, aufgaben, dauer_min) VALUES ('AP1', '[]', 90)")  # läuft noch: zählt nicht
    con.commit()
    assert (ap1()["wert"], ap1()["quelle"]) == (70.2, "probepruefung")  # (60 + 70 + 80,5) / 3
    db.setze_einstellung(con, "note_ap1", "55")
    assert (ap1()["wert"], ap1()["quelle"]) == (55, "eingabe")  # eine eigene Note geht vor
