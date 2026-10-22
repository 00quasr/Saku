"""Lernlogik: Fahrschul-Regeln, FSRS-Obergrenze, Tagesziel, Notenschlüssel, Zusammenstellung, Freischaltung."""

import random
from datetime import date, datetime, time, timedelta, timezone

import pytest

from saku import db
from saku.lernen import karten, pfad, simulation, tagesziel


def _status(con, t_id):
    return tuple(con.execute("SELECT status, serie FROM karte WHERE teilaufgabe_id = ?", (t_id,)).fetchone())


def test_fahrschul_regeln():
    assert karten.fahrschul(0, 1) == ("rot", 0)
    assert karten.fahrschul(4, 2) == ("gelb", 0)
    assert karten.fahrschul(0, 3) == ("gelb", 1)
    assert karten.fahrschul(1, 3) == ("gruen", 2)
    assert karten.fahrschul(5, 1) == ("rot", 0)  # auch Sicheres fällt zurück


def test_bewerten_speichert_status_und_verlauf(con):
    assert karten.bewerten(con, 1, 3) == ("neu", "gelb")
    assert karten.bewerten(con, 1, 3) == ("gelb", "gruen")
    assert karten.bewerten(con, 1, 2, quelle="sensei", dauer_s=40, antwort="x") == ("gruen", "gelb")
    assert _status(con, 1) == ("gelb", 0)
    letzte = con.execute("SELECT ergebnis, quelle, dauer_s, antwort FROM bewertung ORDER BY id DESC").fetchone()
    assert tuple(letzte) == (2, "sensei", 40, "x")
    with pytest.raises(ValueError):
        karten.bewerten(con, 1, 4)


def _faellig_nach_drei_mal_gewusst(con) -> str:
    jetzt = datetime(2027, 1, 1, 10, tzinfo=timezone.utc)
    for _ in range(3):
        karten.bewerten(con, 1, 3, jetzt=jetzt)
        faellig = con.execute("SELECT faellig_am FROM karte WHERE teilaufgabe_id = 1").fetchone()[0]
        jetzt = datetime.fromisoformat(faellig).replace(tzinfo=timezone.utc)
    return faellig


def test_fsrs_endet_am_pruefungstermin(con):
    db.setze_einstellung(con, "pruefungstermin", "2027-01-10")
    assert _faellig_nach_drei_mal_gewusst(con)[:10] == "2027-01-10"


def test_fsrs_ohne_termin_ohne_obergrenze(con):
    db.setze_einstellung(con, "pruefungstermin", "")
    assert karten.scheduler(con).maximum_interval == 36500
    assert _faellig_nach_drei_mal_gewusst(con)[:10] > "2027-01-10"


def test_tagesziel(con):
    heute = date.today()
    db.setze_einstellung(con, "pruefungstermin", (heute + timedelta(days=17)).isoformat())  # 10 Lerntage
    ziel = tagesziel.tagesziel(con, heute)
    assert (ziel["neu"], ziel["wiederholungen"], ziel["ziel"]) == (10, 0, 10)  # aufrunden(14 / 10) = 2, aber mindestens 10

    karten.bewerten(con, 1, 3)
    con.execute("INSERT INTO karte (teilaufgabe_id, status, faellig_am) VALUES (2, 'gelb', datetime('now', '-1 day'))")
    ziel = tagesziel.tagesziel(con, heute)
    assert (ziel["neu"], ziel["wiederholungen"], ziel["erledigt"], ziel["neu_offen"]) == (10, 1, 1, 9)
    assert tagesziel.naechste_aktion(con, ziel) == ("wiederholen", 1)

    db.setze_einstellung(con, "pruefungstermin", (heute + timedelta(days=3)).isoformat())  # mindestens 1 Lerntag
    assert tagesziel.tagesziel(con, heute)["neu"] == 13  # der Termin verlangt mehr als das Mindestziel
    db.setze_einstellung(con, "pruefungstermin", "")
    assert tagesziel.tagesziel(con, heute)["neu"] == tagesziel.NEU_MINDESTENS


def test_zuruecknehmen_spielt_verlauf_nach(con):
    karten.bewerten(con, 1, 3, jetzt=datetime.now(timezone.utc) - timedelta(days=2))
    karten.bewerten(con, 1, 3)
    assert _status(con, 1) == ("gruen", 2)
    assert karten.zuruecknehmen(con, 1)
    assert _status(con, 1) == ("gelb", 1)  # wie nach der ersten Bewertung allein
    assert con.execute("SELECT faellig_am FROM karte WHERE teilaufgabe_id = 1").fetchone()[0]
    assert not karten.zuruecknehmen(con, 1)  # die übrige Bewertung ist nicht von heute
    karten.bewerten(con, 2, 1)
    assert not karten.zuruecknehmen(con, 1) and _status(con, 2) == ("rot", 0)  # zuletzt bewertet wurde eine andere


def test_naechste_aktion_reihenfolge(con):
    ziel = tagesziel.tagesziel(con)
    assert tagesziel.naechste_aktion(con, ziel)[0] == "neu"
    karten.bewerten(con, 3, 1)
    con.execute("UPDATE karte SET faellig_am = datetime('now', '+1 day')")
    assert tagesziel.naechste_aktion(con, tagesziel.tagesziel(con)) == ("fehler", 1)


def test_lernserie(con):
    heute = date.today()

    def gelernt(tag):
        zeit = datetime.combine(tag, time(12)).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        con.execute("INSERT INTO bewertung (teilaufgabe_id, zeitpunkt, ergebnis) VALUES (1, ?, 3)", (zeit,))

    for tage in (1, 2, 4):
        gelernt(heute - timedelta(days=tage))
    assert tagesziel.lernserie(con, heute) == 2  # heute noch nicht gelernt, die Lücke am 3. Tag beendet die Serie
    gelernt(heute)
    assert tagesziel.lernserie(con, heute) == 3


@pytest.mark.parametrize("punkte, note", [
    (100, 1), (92, 1), (91, 2), (81, 2), (80, 3), (67, 3), (66, 4), (50, 4), (49, 5), (30, 5), (29, 6), (0, 6)])
def test_notenschluessel(punkte, note):
    assert simulation.note(punkte) == note


def test_umrechnen_auf_100():
    assert simulation.umrechnen(34, 38) == 89
    assert simulation.umrechnen(49.5, 100) == 50  # kaufmännisch gerundet
    assert simulation.umrechnen(0, 0) == 0


ALGORITHMEN = "Entwicklung und Umsetzung von Algorithmen"


def test_zusammenstellung(con):
    sitzt = con.execute("SELECT id FROM aufgabe WHERE titel = 'Algorithmus'").fetchone()[0]
    con.execute("INSERT INTO karte (teilaufgabe_id, status) SELECT id, 'gruen' FROM teilaufgabe WHERE aufgabe_id = ?", (sitzt,))
    sim_id = simulation.zusammenstellen(con, ALGORITHMEN, random.Random(1))

    assert tuple(con.execute("SELECT dauer_min, beendet_am FROM simulation WHERE id = ?", (sim_id,)).fetchone()) == (90, None)
    aufgaben = con.execute(
        "SELECT a.id, a.pruefung_id, COUNT(*) AS gewaehlt, (SELECT COUNT(*) FROM teilaufgabe t WHERE t.aufgabe_id = a.id) AS alle "
        "FROM simulation_teilaufgabe st JOIN teilaufgabe t ON t.id = st.teilaufgabe_id JOIN aufgabe a ON a.id = t.aufgabe_id "
        "WHERE st.simulation_id = ? GROUP BY a.id", (sim_id,)).fetchall()
    assert len(aufgaben) == 2
    assert len({a["pruefung_id"] for a in aufgaben}) == 2  # verschiedene Jahrgänge
    assert all(a["gewaehlt"] == a["alle"] for a in aufgaben)  # ganze Aufgaben
    assert sitzt not in {a["id"] for a in aufgaben}  # was sitzt, bleibt draußen

    with pytest.raises(ValueError):
        simulation.zusammenstellen(con, "Gibt es nicht")


def test_auswerten_note_und_lernstand(con):
    sim_id = simulation.zusammenstellen(con, ALGORITHMEN, random.Random(2))
    ids = [z[0] for z in con.execute("SELECT teilaufgabe_id FROM simulation_teilaufgabe WHERE simulation_id = ?", (sim_id,))]
    simulation.auswerten(con, sim_id, {i: 99 for i in ids[:-1]})  # über dem Maximum wird gekappt, die letzte bleibt 0
    sim = con.execute("SELECT * FROM simulation WHERE id = ?", (sim_id,)).fetchone()
    letzte = con.execute("SELECT punkte FROM teilaufgabe WHERE id = ?", (ids[-1],)).fetchone()[0]
    assert sim["punkte_erreicht"] == sim["punkte_moeglich"] - letzte
    assert sim["beendet_am"] and sim["note"] == simulation.note(simulation.umrechnen(sim["punkte_erreicht"], sim["punkte_moeglich"]))
    assert con.execute("SELECT COUNT(*) FROM bewertung WHERE quelle = 'simulation'").fetchone()[0] == len(ids)
    assert _status(con, ids[-1]) == ("rot", 0)


def test_abgelaufene_simulation_endet(con):
    sim_id = simulation.zusammenstellen(con, ALGORITHMEN)
    assert simulation.laufende(con)["id"] == sim_id
    con.execute("UPDATE simulation SET gestartet_am = datetime('now', '-91 minutes')")
    assert simulation.laufende(con) is None
    assert con.execute("SELECT beendet_am FROM simulation").fetchone()[0]


def test_freischaltung_der_stationen(con):
    stationen = pfad.stationen(con)
    assert [(s["aktuell"], s["gesperrt"]) for s in stationen[:3]] == [(True, False), (False, True), (False, True)]

    ids = pfad.teilaufgaben(con, 1)
    maximal = dict(con.execute("SELECT id, punkte FROM teilaufgabe").fetchall())
    knapp = {i: maximal[i] * 0.79 for i in ids}
    assert not pfad.test_auswerten(con, 1, knapp)["bestanden"]
    assert pfad.stationen(con)[1]["gesperrt"]

    genau = {i: maximal[i] * 0.8 for i in ids} | {999: 50, 9: 50}  # fremde Teilaufgaben zählen nicht
    ergebnis = pfad.test_auswerten(con, 1, genau)
    assert ergebnis["bestanden"] and ergebnis["moeglich"] == sum(maximal[i] for i in ids)
    stationen = pfad.stationen(con)
    assert stationen[0]["bestanden"] and not stationen[0]["aktuell"]
    assert stationen[1]["aktuell"] and not stationen[1]["gesperrt"]
    assert stationen[2]["gesperrt"]
    assert con.execute("SELECT COUNT(*) FROM bewertung WHERE quelle = 'stationstest'").fetchone()[0] == 2 * len(ids)

    # Station 3 hat in der Demo keine Teilaufgaben und hält den Pfad nicht auf
    pfad.test_auswerten(con, 2, {i: maximal[i] for i in pfad.teilaufgaben(con, 2)})
    assert [s["aktuell"] for s in pfad.stationen(con)[:4]] == [False, False, False, True]


def test_ihk_termine_nur_kuenftige():
    from datetime import date
    from saku.lernen.tagesziel import ihk_termine
    assert [t["datum"] for t in ihk_termine("AP2", date(2026, 12, 1))][:1] == ["2027-04-28"]
    assert ihk_termine("AP1", date(2026, 10, 22))[0] == {"datum": "2027-02-24", "name": "Frühjahr 2027", "anzeige": "24.02.2027"}
    assert ihk_termine("AP3") == []
