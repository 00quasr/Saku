"""WiSo-Schnelltest: zufällige anklickbare WiSo-Teilaufgaben als Simulation, Saku wertet selbst aus (erfundene Demo-Prüfungen)."""

import json
import math
import random
import re

import pytest

from saku import db
from saku.lernen import hochrechnung, simulation
from saku.web import create_app
from tests.demo_daten import anlegen


@pytest.fixture
def wiso(tmp_path):
    anlegen(tmp_path, wiso=True)
    con = db.verbinden(tmp_path / "saku.db")
    db.setze_einstellung(con, "einfuehrung", "gesehen")
    app = create_app(tmp_path)
    app.config["TESTING"] = True
    yield con, app.test_client()
    con.close()


def _teilaufgaben(con, sim_id: int) -> list:
    return con.execute("SELECT t.id, t.aufgabe_id, t.position, t.punkte, t.antwort, v.bereich, v.termin_index "
                       "FROM simulation_teilaufgabe st JOIN teilaufgabe t ON t.id = st.teilaufgabe_id "
                       "JOIN v_teilaufgabe v ON v.teilaufgabe_id = t.id WHERE st.simulation_id = ? ORDER BY st.position",
                       (sim_id,)).fetchall()


def test_zusammenstellung(wiso):
    con, _ = wiso
    kandidaten = simulation.schnelltest_kandidaten(con)
    assert len(kandidaten) == 12 and simulation.minuten_je_punkt(con, simulation.WISO) == 0.6  # 60 Minuten für 100 Punkte
    sim_id = simulation.schnelltest(con, random.Random(3), anzahl=5)
    sim = con.execute("SELECT * FROM simulation WHERE id = ?", (sim_id,)).fetchone()
    teile = _teilaufgaben(con, sim_id)
    assert sim["bereich"] == simulation.SCHNELLTEST and len(teile) == 5
    assert sim["dauer_min"] == math.ceil(sum(t["punkte"] for t in teile) * 0.6)  # anteilig nach Punkten
    assert all(t["bereich"] == simulation.WISO and json.loads(t["antwort"])["art"] != "frei" for t in teile)
    aufgaben = [t["aufgabe_id"] for t in teile]
    assert aufgaben == sorted(aufgaben, key=aufgaben.index)  # Teilaufgaben einer Aufgabe stehen zusammen …
    for a in set(aufgaben):
        positionen = [t["position"] for t in teile if t["aufgabe_id"] == a]
        assert positionen == sorted(positionen)  # … und in ihrer Reihenfolge
    alle = _teilaufgaben(con, simulation.schnelltest(con, random.Random(4)))
    assert len(alle) == 12 and len({t["termin_index"] for t in alle}) == 2  # quer über alle Termine


def _richtig(antwort: dict, praefix: str) -> dict:
    """Formularfelder mit der richtigen Antwort, wie sie die Simulation abschickt."""
    felder = {f"{praefix}art": antwort["art"]}
    if antwort["art"] in ("einfach", "mehrfach"):
        felder[f"{praefix}wahl"] = antwort["richtig"]
    elif antwort["art"] == "zahl":
        felder[f"{praefix}zahl"] = antwort["richtig"][0].replace(".", ",")
    elif antwort["art"] == "reihenfolge":
        felder |= {f"{praefix}position-{w}": str(i) for i, w in enumerate(antwort["richtig"], start=1)}
    else:
        felder |= {f"{praefix}ziel-{w}": z for w, z in (r.split("=") for r in antwort["richtig"])}
    return felder


def test_abgeben_wertet_selbst_aus(wiso):
    con, client = wiso
    seite = client.get("/shiken/").get_data(as_text=True)
    assert 'id="schnelltest"' in seite and "WiSo gemischt" in seite and "12 Teilaufgaben zum Anklicken" in seite
    url = client.post("/shiken/neu", data={"bereich": simulation.SCHNELLTEST}).headers["Location"]
    sim_id = int(url.rsplit("/", 1)[1])
    html = client.get(url).get_data(as_text=True)
    assert "WiSo-Schnelltest" in html and f'name="antwort-{_teilaufgaben(con, sim_id)[0]["id"]}-art"' in html
    assert "Alles hier prüft Saku bei der Abgabe selbst" in html and "den Rest bewertest du" not in html
    teile = _teilaufgaben(con, sim_id)
    richtig = teile[:8]  # die ersten acht richtig, den Rest leer gelassen
    form = {}
    for t in richtig:
        form |= _richtig(json.loads(t["antwort"]), f"antwort-{t['id']}-")
    for t in teile[8:]:
        form[f"antwort-{t['id']}-art"] = json.loads(t["antwort"])["art"]
    antwort = client.post(f"/shiken/{sim_id}/abgeben", data=form)
    assert antwort.headers["Location"].endswith(f"/shiken/{sim_id}/auswertung")
    sim = con.execute("SELECT * FROM simulation WHERE id = ?", (sim_id,)).fetchone()
    erreicht, moeglich = sum(t["punkte"] for t in richtig), sum(t["punkte"] for t in teile)
    assert (sim["punkte_erreicht"], sim["punkte_moeglich"]) == (erreicht, moeglich)
    punkte_100 = simulation.umrechnen(erreicht, moeglich)
    assert sim["note"] == simulation.note(punkte_100) and sim["bestanden"] == int(punkte_100 >= 50)
    # jede Teilaufgabe zählt als Bewertung, der Fahrschul-Status ändert sich
    bewertungen = dict(con.execute("SELECT teilaufgabe_id, ergebnis FROM bewertung WHERE quelle = 'simulation'").fetchall())
    assert {t["id"]: bewertungen[t["id"]] for t in teile} == {t["id"]: 3 if t in richtig else 1 for t in teile}
    assert con.execute(f"SELECT COUNT(*) FROM v_teilaufgabe WHERE status <> 'neu' AND teilaufgabe_id IN "
                       f"({','.join(str(t['id']) for t in teile)})").fetchone()[0] == len(teile)
    html = " ".join(client.get(f"/shiken/{sim_id}/auswertung").get_data(as_text=True).split())
    assert f"{punkte_100}" in html and simulation.NOTEN[sim["note"]] in html
    # ein zweites Abgeben wertet nicht noch einmal aus
    client.post(f"/shiken/{sim_id}/abgeben", data=form)
    assert con.execute("SELECT COUNT(*) FROM bewertung WHERE quelle = 'simulation'").fetchone()[0] == len(teile)


def test_zaehlt_nicht_als_wiso_simulation_und_steht_in_der_palette(wiso):
    con, client = wiso
    sim_id = simulation.schnelltest(con, random.Random(1))
    con.execute("UPDATE simulation SET beendet_am = datetime('now') WHERE id = ?", (sim_id,))
    simulation.auswerten(con, sim_id, {t["id"]: t["punkte"] for t in _teilaufgaben(con, sim_id)})
    assert hochrechnung._simulation(con, simulation.WISO) is None  # Hochrechnung nur aus ganzen Simulationen
    html = client.get("/suche/", query_string={"q": "wiso"}, headers={"HX-Request": "true"}).get_data(as_text=True)
    assert re.search(r'href="/shiken/#schnelltest">.*WiSo-Schnelltest', html, re.S)


def test_ohne_wiso_kein_schnelltest(client):
    assert 'id="schnelltest"' not in client.get("/shiken/").get_data(as_text=True)  # Demo ohne WiSo-Prüfungen
    assert client.post("/shiken/neu", data={"bereich": simulation.SCHNELLTEST}).status_code == 400


def test_schnelltest_zaehlt_in_der_einzahl(wiso):
    con, client = wiso
    erste = simulation.schnelltest_kandidaten(con)[0]["teilaufgabe_id"]
    con.execute("UPDATE teilaufgabe SET antwort = NULL WHERE id <> ?", (erste,))  # nur eine anklickbare bleibt
    con.execute("UPDATE teilaufgabe SET punkte = 1 WHERE id = ?", (erste,))  # 0,6 Minuten
    con.commit()
    html = " ".join(client.get("/shiken/").get_data(as_text=True).split())
    assert "1 Teilaufgabe zum Anklicken · etwa 1 Minute · aus 1 Termin<" in html
