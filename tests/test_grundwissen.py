"""Grundwissen umgekehrt: Definition lesen, unter vier Begriffen wählen (Demo-Daten, erfundene Begriffe)."""

import re

import numpy as np
import pytest

from saku import db
from saku.lernen import karten
from saku.sensei import vektoren

HTMX = {"HX-Request": "true"}
# Name: (Erklärung, Teilaufgabe der Demo); 9 und 12 sind SQL-Teilaufgaben, also dasselbe Thema
BEGRIFFE = {
    "Primärschlüssel": ("Ein Primärschlüssel kennzeichnet jeden Datensatz eindeutig.", 9),
    "Join": ("Verknüpft Zeilen zweier Tabellen über gleiche Werte.", 12),
    "Fremdschlüssel": ("Verweist auf den Schlüssel einer anderen Tabelle.", 10),
    "Normalform": ("Regeln gegen Redundanz in Tabellen.", 10),
    "Kritischer Pfad": ("Kette von Vorgängen ohne Puffer.", 1),
    "Rekursion": ("Eine Funktion ruft sich selbst auf.", 8),
    "Bubblesort": ("Vertauscht benachbarte Elemente, bis alles sortiert ist.", 6),
}


@pytest.fixture
def begriffe(con) -> dict[str, int]:
    ids = {}
    for name, (erklaerung, teilaufgabe) in BEGRIFFE.items():
        ids[name] = con.execute("INSERT INTO begriff (name, slug, erklaerung) VALUES (?, ?, ?)",
                                (name, name.lower().replace(" ", "-"), erklaerung)).lastrowid
        con.execute("INSERT INTO teilaufgabe_begriff VALUES (?, ?)", (teilaufgabe, ids[name]))
    con.commit()
    return ids


def test_ablenker_vektoren_dann_themen_dann_zufall(con, begriffe):
    p = begriffe["Primärschlüssel"]
    ohne = karten.ablenker(con, p)
    assert len(ohne) == 3 == len(set(ohne)) and p not in ohne
    assert ohne[0] == begriffe["Join"]  # ohne Vektoren: dasselbe Thema (SQL) zuerst

    # mit Vektoren: Fremdschlüssel liegt am nächsten, dann Normalform, der Rest steht senkrecht dazu
    richtung = {"Primärschlüssel": [1, 0, 0], "Fremdschlüssel": [0.9, 0.1, 0], "Normalform": [0.6, 0.4, 0]}
    matrix = np.array([richtung.get(name, [0, 0, 1]) for name in begriffe], dtype=np.float32)
    vektoren.speichern(con, "begriff", list(begriffe.values()), matrix / np.linalg.norm(matrix, axis=1, keepdims=True))
    assert karten.ablenker(con, p)[:2] == [begriffe["Fremdschlüssel"], begriffe["Normalform"]]

    db.setze_einstellung(con, "teil", "AP1")  # nur Begriffe im Umfang
    assert karten.ablenker(con, p) == []


def test_auswahl_verdeckt_den_namen(con, begriffe):
    karte = con.execute("SELECT id, name, erklaerung FROM begriff WHERE name = 'Primärschlüssel'").fetchone()
    a = karten.auswahl(con, karte)
    assert a["definition"] == "Ein … kennzeichnet jeden Datensatz eindeutig."
    namen = [o["name"] for o in a["optionen"]]
    assert len(namen) == 4 and "Primärschlüssel" in namen and namen == sorted(namen, key=str.casefold)


def test_umgekehrt_waehlen_und_umschalten(client, con, begriffe):
    html = client.get("/keiko/grundwissen?modus=umgekehrt").get_data(as_text=True)
    assert '<a href="/keiko/grundwissen" data-taste="u">' in html and 'modus=umgekehrt" aria-current="true"' in html
    assert all(f'data-taste="{n}"' in html for n in range(1, 5)) and 'data-taste=" "' not in html
    erste = int(re.search(r'/keiko/grundwissen/(\d+)/bewerten', html)[1])
    name = next(n for n, i in begriffe.items() if i == erste)
    assert name not in html.split('class="prosa begriff-definition">')[1].split("</div>")[0]  # verdeckt

    richtig = client.post(f"/keiko/grundwissen/{erste}/bewerten", data={"wahl": erste, "runde": ""}, headers=HTMX).get_data(as_text=True)
    assert f"Richtig: {name}." in richtig and 'name="runde" value="' + str(erste) + '"' in richtig and "<html" not in richtig
    assert con.execute("SELECT status FROM begriff_karte WHERE begriff_id = ?", (erste,)).fetchone()[0] == "gelb"

    zweite = int(re.search(r'/keiko/grundwissen/(\d+)/bewerten', richtig)[1])
    falsch = client.post(f"/keiko/grundwissen/{zweite}/bewerten", data={"wahl": erste, "runde": str(erste)}, headers=HTMX)
    assert f"nicht {name}." in falsch.get_data(as_text=True)
    assert con.execute("SELECT status FROM begriff_karte WHERE begriff_id = ?", (zweite,)).fetchone()[0] == "rot"

    # die andere Richtung bleibt wie gehabt: aufdecken und selbst bewerten
    normal = client.get("/keiko/grundwissen").get_data(as_text=True)
    assert 'data-taste=" "' in normal and 'modus=umgekehrt" data-taste="u"' in normal
    assert client.post("/keiko/grundwissen/999/bewerten", data={"wahl": 1}).status_code == 400
    weiter = client.get(f"/keiko/grundwissen?modus=umgekehrt&runde={erste},{zweite}", headers=HTMX).get_data(as_text=True)
    assert "<html" not in weiter and f"/keiko/grundwissen/{erste}/bewerten" not in weiter
