"""Fahrplan bis zur Prüfung: Prognose, Tempo, Abdeckung nach Prüfungsgewicht, Gewinn (Demo-Daten, erfundene Prüfungen)."""

import re
from datetime import date, datetime, time, timedelta, timezone

import pytest

from saku import db
from saku.lernen import fahrplan, karten
from saku.web.routen.suche import befehle


def _mittag(tag: date) -> datetime:
    return datetime.combine(tag, time(12)).astimezone(timezone.utc)


def _faellig(con, t_id: int, tag: date):
    con.execute("INSERT INTO karte (teilaufgabe_id, status, faellig_am) VALUES (?, 'gelb', ?)",
                (t_id, karten.sqlite_zeit(_mittag(tag))))
    con.commit()


def test_prognose_zaehlt_faellige_am_richtigen_tag(con):
    heute = date.today()  # Demo: 14 Teilaufgaben, Termin in 60 Tagen, 7 Tage Puffer
    for t_id in (1, 2):
        _faellig(con, t_id, heute + timedelta(days=3))
    _faellig(con, 3, heute - timedelta(days=1))  # überfällig: zählt heute
    p = fahrplan.prognose(con, heute)
    assert len(p) == 14 and p[0]["heute"] and p[0]["tag"] == heute and not p[1]["heute"]
    assert [t["wdh"] for t in p[:5]] == [1, 0, 0, 2, 0]
    # 11 neue: heute das Mindestziel 10, morgen die letzte, danach keine mehr
    assert [t["neu"] for t in p[:3]] == [10, 1, 0] and p[3]["summe"] == 2
    assert len(fahrplan.prognose(con, heute, 30)) == 30

    db.setze_einstellung(con, "pruefungstermin", (heute + timedelta(days=5)).isoformat())
    assert [i for i, t in enumerate(fahrplan.prognose(con, heute)) if t["pruefung"]] == [5]
    db.setze_einstellung(con, "teil", "AP1")  # nichts im Umfang
    assert all(t["summe"] == 0 for t in fahrplan.prognose(con, heute))


def test_tempo_und_prognose_datum(con):
    heute = date.today()
    for t_id in (1, 2, 3):
        karten.bewerten(con, t_id, 3, jetzt=_mittag(heute - timedelta(days=1)))
    karten.bewerten(con, 4, 3, jetzt=_mittag(heute - timedelta(days=3)))
    karten.bewerten(con, 4, 3, jetzt=_mittag(heute - timedelta(days=1)))  # Wiederholung, nicht neu
    t = fahrplan.tempo(con, heute)
    # zwei Lerntage, 4 neue → 2 am Tag; 10 übrig → 5 Tage, heute zählt mit
    assert (t["schnitt"], t["lerntage"], t["rest"]) == (2.0, 2, 10)
    assert t["fertig"] == heute + timedelta(days=4)
    assert (t["termin"], t["letzter"], t["noetig"], t["abstand"]) == (
        heute + timedelta(days=60), heute + timedelta(days=52), 1, 56)

    karten.bewerten(con, 5, 3)  # heute gelernt: das Tempo bleibt bis morgen stehen
    assert fahrplan.tempo(con, heute) == t

    db.setze_einstellung(con, "pruefungstermin", (heute + timedelta(days=10)).isoformat())  # 3 Lerntage
    t = fahrplan.tempo(con, heute)
    assert (t["letzter"], t["noetig"], t["abstand"]) == (heute + timedelta(days=2), 4, 6)
    assert t["fertig"] > t["letzter"]


def test_abdeckung_summiert_auf_100(con):
    karten.bewerten(con, 1, 3)
    karten.bewerten(con, 1, 3)  # sicher, 6 Punkte
    karten.bewerten(con, 2, 3)  # im Aufbau, 4 Punkte
    karten.bewerten(con, 5, 1)  # wackelig zählt zum Aufbau, 6 Punkte
    a = fahrplan.abdeckung(con)
    g = a["gesamt"]
    assert g["punkte"] == 96 and g["sicher"] == pytest.approx(100 * 6 / 96) and g["aufbau"] == pytest.approx(100 * 10 / 96)
    assert [b["name"] for b in a["bereiche"]] == ["Planen eines Softwareproduktes", "Entwicklung und Umsetzung von Algorithmen"]
    for eintrag in [g, *a["bereiche"], *(th for b in a["bereiche"] for th in b["themen"])]:
        assert eintrag["sicher"] + eintrag["aufbau"] + eintrag["nie"] == pytest.approx(100)
    assert sum(b["punkte"] for b in a["bereiche"]) == pytest.approx(g["punkte"])

    db.setze_einstellung(con, "teil", "AP1")
    assert fahrplan.abdeckung(con) == {"gesamt": {"sicher": 0, "aufbau": 0, "nie": 0, "punkte": 0}, "bereiche": []}


def test_gewinn_reihenfolge(con):
    namen = lambda: [t["name"] for t in fahrplan.gewinn(con)]  # noqa: E731
    assert namen() == ["Datenbanken", "Algorithmen", "Projektmanagement", "Modellierung mit UML", "Qualitätssicherung"]
    for t_id in (9, 10, 12, 13):  # Datenbanken ganz sicher: bringt nichts mehr
        karten.bewerten(con, t_id, 3)
        karten.bewerten(con, t_id, 3)
    for t_id in (1, 2, 3):  # Projektmanagement im Aufbau: halber Lernstand
        karten.bewerten(con, t_id, 3)
    gewinn = fahrplan.gewinn(con)
    assert namen() == ["Algorithmen", "Modellierung mit UML", "Projektmanagement", "Qualitätssicherung"]
    assert [round(t["gewinn"]) for t in gewinn] == [24, 16, 9, 6]
    assert (gewinn[0]["teilaufgaben"], gewinn[0]["letzter_termin"]) == (4, 2024 * 2)
    assert len(fahrplan.gewinn(con, 2)) == 2


def test_leerzustaende(con, client):
    heute = date.today()
    db.setze_einstellung(con, "pruefungstermin", "")
    t = fahrplan.tempo(con, heute)
    assert (t["schnitt"], t["fertig"], t["termin"], t["noetig"], t["rest"]) == (None, None, None, None, 14)
    assert [p["neu"] for p in fahrplan.prognose(con, heute, 3)] == [10, 4, 0]  # ohne Termin das Mindestziel
    html = client.get("/fahrplan").get_data(as_text=True)
    assert "Noch kein Tempo." in html and "Noch kein Prüfungstermin." in html and 'href="/einstellungen#termin"' in html

    con.execute("DELETE FROM pruefung")
    con.commit()
    leer = client.get("/fahrplan")
    assert leer.status_code == 200 and "Noch gibt es keine Teilaufgaben" in leer.get_data(as_text=True)


def test_route_hell_und_dunkel_gleich(con, client):
    heute = date.today()
    for t_id in (1, 2, 3):
        karten.bewerten(con, t_id, 3, jetzt=_mittag(heute - timedelta(days=1)))
    karten.bewerten(con, 4, 3, jetzt=_mittag(heute - timedelta(days=2)))
    inhalt = {}
    for schema in ("hell", "dunkel"):
        db.setze_einstellung(con, "farbschema", schema)
        antwort = client.get("/fahrplan")
        assert antwort.status_code == 200
        html = antwort.get_data(as_text=True)
        inhalt[schema] = html[html.index("<main"):html.index("</main>")]
    assert inhalt["hell"] == inhalt["dunkel"]  # Farben nur über Tokens im CSS
    main = inhalt["hell"]
    assert not re.search(r'style="[^"]*#', main)
    assert 'id="prognose"' in main and main.count('class="saeule"') == 14 and 'class="saeule-heute"' in main
    fertig = (heute + timedelta(days=4)).strftime("%d.%m.%Y")
    assert f"Bei 2 neuen am Tag bist du am {fertig} durch – 56 Tage vor der Prüfung." in main
    assert 'id="abdeckung"' in main and "der Prüfungspunkte sitzen sicher" in main and 'role="img"' in main
    assert 'href="/keiko/?thema=' in main and "zuletzt Sommer 2024" in main
    assert client.get("/fahrplan?tage=30").get_data(as_text=True).count('class="saeule"') == 30

    start = client.get("/").get_data(as_text=True)
    assert 'href="/fahrplan"' in start and 'href="/fahrplan#abdeckung"' in start
    assert befehle("fahrplan")[0][3] == ("heute.fahrplan", {})
