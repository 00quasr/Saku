"""Wochenrückblick auf Heute und im Verlauf (Demo-Daten, erfundene Prüfungen)."""

from datetime import date, datetime, time, timedelta, timezone

import pytest

from saku.lernen import karten, rueckblick, tagesziel


def _am(tage_zurueck: int) -> datetime:
    return datetime.combine(date.today() - timedelta(days=tage_zurueck), time(12)).astimezone(timezone.utc)


@pytest.fixture
def woche(con):
    """Projektmanagement: 1 a, 1 b, 1 c; Modellierung mit UML: 2 a, 2 b. (Teilaufgabe, [(vor Tagen, Ergebnis)])"""
    for t_id, bewertungen in {
        1: [(10, 3), (2, 3)],          # in der Woche sicher geworden
        2: [(9, 3), (8, 3), (1, 3)],   # war schon vorher sicher
        3: [(3, 3), (1, 3)],           # in der Woche sicher geworden
        4: [(2, 3), (1, 1)],           # gewusst, dann nicht mehr
        5: [(4, 3), (3, 3), (1, 1)],   # in der Woche sicher und wieder herausgefallen
    }.items():
        for tage, ergebnis in bewertungen:
            karten.bewerten(con, t_id, ergebnis, jetzt=_am(tage))
    for tage, richtig in ((0, 1), (2, 0), (10, 1)):
        con.execute("INSERT INTO rechenuebung (art, seed, richtig, felder_richtig, felder_gesamt, zeitpunkt) "
                    "VALUES ('subnetz', 1, ?, 1, 1, ?)", (richtig, karten.sqlite_zeit(_am(tage))))
    con.commit()
    return con


def test_ohne_bewertungen_kein_rueckblick(con, client):
    assert rueckblick.woche(con) is None
    karten.bewerten(con, 1, 3, jetzt=_am(8))  # zu alt
    assert rueckblick.woche(con) is None
    assert "Diese Woche" not in client.get("/").get_data(as_text=True)
    assert "Diese Woche" not in client.get("/keiko/verlauf").get_data(as_text=True)


def test_woche_zahlen_sicher_themen_rechnen(woche):
    w = rueckblick.woche(woche)
    assert (w["n"], w["davor"], w["sicher"], w["rechnen"]) == (9, 3, 2, (2, 1))
    assert w["quote"] == pytest.approx(7 / 9)
    assert (w["staerkstes"]["name"], w["staerkstes"]["quote"], w["staerkstes"]["n"]) == ("Projektmanagement", 1, 4)
    assert (w["schwaechstes"]["name"], w["schwaechstes"]["quote"]) == ("Modellierung mit UML", pytest.approx(3 / 5))
    assert tagesziel.sicher_geworden(woche, date.today() - timedelta(days=6), date.today()) == [1, 3]

    vorwoche = rueckblick.woche(woche, date.today() - timedelta(days=7))  # heute als Parameter: eine Woche früher
    assert (vorwoche["n"], vorwoche["davor"], vorwoche["sicher"], vorwoche["rechnen"]) == (3, 0, 1, (1, 1))
    assert vorwoche["staerkstes"]["name"] == "Projektmanagement" and vorwoche["schwaechstes"] is None  # nur ein Thema


def test_heute_und_verlauf_zeigen_den_rueckblick(woche, client):
    for url in ("/", "/keiko/verlauf"):
        html = client.get(url).get_data(as_text=True)
        assert "Diese Woche" in html and '<span class="zahl">9</span> Bewertungen' in html and 'aria-hidden="true">↑</span> Vorwoche 3' in html
        assert '<span class="zahl">2</span> sicher geworden' in html and "78 %</span> gewusst" in html
        assert "Stärkstes Thema:" in html and "Projektmanagement</a>" in html and "Modellierung mit UML</a>" in html
        assert "50 % richtig" in html
    assert "Diese Woche" not in client.get("/keiko/verlauf?seite=1").get_data(as_text=True)  # nur oben auf der ersten Seite


def test_lernserie_und_kalender_zaehlen_uebungen(con, client):
    """v_lerntage zählt seit Migration 9 auch Rechenaufgaben: beschriftet ist die Zahl als Übungen, nicht als Bewertungen."""
    karten.bewerten(con, 1, 3)
    heute = date.today().strftime("%d.%m.")
    html = client.get("/").get_data(as_text=True)
    assert f'title="{heute}: 1 Übung"' in html and f'title="{heute}{date.today():%Y}: 1 Übung"' in html
    con.execute("INSERT INTO rechenuebung (art, seed, richtig, felder_richtig, felder_gesamt) VALUES ('subnetz', 1, 1, 1, 1)")
    con.commit()
    html = client.get("/").get_data(as_text=True)
    assert f'title="{heute}: 2 Übungen"' in html and f'title="{heute}{date.today():%Y}: 2 Übungen"' in html
    assert "2 Bewertungen" not in html
