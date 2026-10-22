"""Pipeline mit ERFUNDENEN Prüfungen, die das IHK-Layout nachahmen (keine echten Prüfungstexte)."""

import hashlib
import json

import pymupdf
import pytest

from saku import db
from saku.pipeline import inventar, klassifikation, lernpfad, loesungen, pdf, segmente, statistik, themen

BREITE, HOEHE = 595, 842


def _pdf(pfad, seiten: list):
    """PDF aus Seiten mit (x, y, Text); Seite 1 ist ein Deckblatt."""
    doc = pymupdf.open()
    for zeilen in seiten:
        seite = doc.new_page(width=BREITE, height=HOEHE)
        for x, y, text in zeilen:
            seite.insert_text((x, y), text, fontsize=10)
    doc.save(pfad)
    return pfad


DECKBLATT = [(40, 60, "Abschlussprüfung Sommer 2030"), (40, 80, "Fachinformatiker Anwendungsentwicklung 1201"),
             (40, 100, "Planen eines Softwareproduktes"), (40, 120, "90 Minuten Prüfungszeit")]
AUFGABEN = [DECKBLATT, [
    (40, 50, "Die Aufgaben 1 bis 2 beziehen sich auf die folgende Ausgangssituation:"),
    (40, 66, "Die Beispiel GmbH baut eine Lernplattform für Bienenzüchter."),
    (40, 120, "1. Aufgabe (10 Punkte)"),
    (40, 136, "Die Plattform braucht ein Datenmodell."),
    (40, 160, "a) Nennen Sie zwei Entitäten des Datenmodells."), (470, 160, "4 Punkte"),
    (40, 260, "b) Erläutern Sie den Begriff Normalform."), (470, 260, "6 Punkte"),
    (40, 400, "2. Aufgabe (8 Punkte)"),
    (40, 420, "a) Für das Imkerforum wird eine Anmeldung benötigt."),
    (52, 440, "aa) Beschreiben Sie das Verfahren Hashwert für Passwörter."), (470, 440, "5 Punkte"),
    (52, 520, "ab) Nennen Sie einen Angriff auf Passwörter."), (470, 520, "3 Punkte"),
    (40, 825, "ZPA FIA I 2"),
]]
LOESUNGEN = [[(40, 60, "Abschlussprüfung Sommer 2030 Lösungshinweise"), (40, 80, "Anwendungsentwicklung 1201")], [
    (40, 50, "1. Aufgabe (10 Punkte)"),
    (40, 70, "a) 4 Punkte"), (40, 86, "Bienenstock, Imker"),
    (40, 120, "b) 6 Punkte"), (40, 136, "Eine Normalform vermeidet Anomalien."),
    (40, 200, "2. Aufgabe (8 Punkte)"),
    (40, 220, "aa) 5 Punkte"), (40, 236, "Salt und langsame Hashfunktion"),
    (40, 280, "ab) 3 Punkte"), (40, 296, "Brute Force"),
]]


def test_rauschen():
    assert segmente._rauschen("ee...") and segmente._rauschen("DR DR RR DR a") and segmente._rauschen("ENEBEEESSSEESERNEEERNE")
    assert not segmente._rauschen("a) Nennen Sie zwei Entitäten des Datenmodells.")


def test_gliedern_und_blaetter(tmp_path):
    with pymupdf.open(_pdf(tmp_path / "a.pdf", AUFGABEN)) as doc:
        seiten = [{"breite": s.rect.width, "hoehe": s.rect.height, "zeilen": pdf._zeilen(s)} for s in doc]
    g = segmente.gliedern(seiten)
    assert "Bienenzüchter" in segmente.text(g["ausgang"])
    assert [(a["nr"], a["punkte"]) for a in g["aufgaben"]] == [(1, 10), (2, 8)]
    blaetter = segmente.blaetter(g["aufgaben"][1])
    assert [(b["kennung"], b["punkte"]) for b in blaetter] == [("aa", 5), ("ab", 3)]
    assert blaetter[0]["eltern"][0]["kennung"] == "a"  # Text von „a)“ gehört zu beiden Kindern


def test_fehlender_aufgabenkopf():
    """OCR verliert „2. Aufgabe“: ein neues „a)“ nach „b)“ beginnt trotzdem eine neue Aufgabe."""
    zeilen = [[40, 100, 300, 112, "1. Aufgabe (10 Punkte)"], [40, 120, 300, 132, "a) Erstens"], [40, 160, 300, 172, "b) Zweitens"],
              [40, 300, 300, 312, "a) Drittens"]]
    g = segmente.gliedern([{"breite": BREITE, "hoehe": HOEHE, "zeilen": zeilen}])
    assert [(a["nr"], [t["kennung"] for t in a["teile"]]) for a in g["aufgaben"]] == [(1, ["a", "b"]), (2, ["a"])]


def test_abschnitte_bei_zwei_pruefungsteilen():
    nummern = [1, 2, 3, 4, 1, 2]
    zeilen = [[40, 50 + 60 * i, 300, 62 + 60 * i, f"{n}. Aufgabe"] for i, n in enumerate(nummern)]
    zeilen += [[40, 70 + 60 * i, 300, 82 + 60 * i, "a) 2 Punkte"] for i in range(len(nummern))]
    g = segmente.gliedern([{"breite": BREITE, "hoehe": 2000, "zeilen": zeilen}])
    assert [len(a) for a in segmente.abschnitte(g)] == [4, 2]


def test_aufhellen():
    grau = pymupdf.Pixmap(pymupdf.csGRAY, 50, 50, bytes([170] * 2400 + [40] * 100), 0)
    hell = segmente.aufhellen(grau)
    assert hell.pixel(0, 0)[0] == 255 and hell.pixel(0, 49)[0] < 20  # Papier weiß, Tinte bleibt dunkel
    weiss = pymupdf.Pixmap(pymupdf.csGRAY, 10, 10, bytes([255] * 100), 0)
    assert segmente.aufhellen(weiss) is weiss


def test_zuordnen():
    teile = {(1, "a"): 1, (1, "ca"): 2, (1, "cb"): 3, (2, "b"): 4}
    assert loesungen.zuordnen(teile, 1, "a") == [1]
    assert loesungen.zuordnen(teile, 1, "c") == [2, 3]  # Lösung fasst Kinder zusammen
    assert loesungen.zuordnen(teile, 2, "ba") == [4]  # Aufgabe kennt nur den Eltern-Teil


def test_deckblatt():
    m = inventar.deckblatt(["Abschlussprüfung Winter 2024/25 Lösungshinweise Fachinformatiker Anwendungsentwicklung 1201 "
                            "Planen eines Softwareproduktes"])
    assert (m["jahr"], m["saison"], m["art"], m["beruf"], m["bereich"]) == (2024, "Winter", "loesungen", "1201", inventar.PLANEN)


def test_themenliste():
    eintraege = themen.lesen("<!-- Kommentar -->\n# Bereich\n## Thema\n- Unter: a, b\n- Zweites\n## Thema 2\n")
    assert [(e["ebene"], e["name"], e["stichworte"], e["eltern"]) for e in eintraege] == [
        (1, "Bereich", None, None), (2, "Thema", None, 0), (3, "Unter", "a, b", 1), (3, "Zweites", None, 1), (2, "Thema 2", None, 0)]
    with pytest.raises(ValueError):
        themen.lesen("- ohne Thema")


def test_reihenfolge_und_buendeln():
    # 2 setzt 1 voraus, Zyklus 1 → 3 → 1 wird aufgelöst; sonst die meisten Punkte zuerst
    folge = lernpfad.reihenfolge({1: 10, 2: 50, 3: 30}, [(2, 1), (3, 1), (1, 3)])
    assert folge.index(1) < folge.index(2) and len(folge) == 3
    assert lernpfad.buendeln([([1], 20), ([2], 3), ([3], 3), ([4], 3), ([5], 9)]) == [[1], [2, 3, 4], [5]]


def test_aehnlichkeiten():
    paare = statistik.aehnlichkeiten(["SQL Abfrage JOIN Kunde", "SQL Abfrage JOIN Kunde Bestellung", "Netzplan Puffer"], [1, 2, 1])
    assert (0, 1) in {(i, j) for i, j, _ in paare} and all(w >= statistik.SCHWELLE for *_, w in paare)


def test_regeln_ohne_ki():
    th = [{"id": 1, "name": "SQL", "stichworte": "SELECT, JOIN"}, {"id": 2, "name": "Netzplan", "stichworte": "Puffer"}]
    assert klassifikation.regeln(th, "Schreiben Sie ein SELECT mit JOIN") == [(1, 1.0)]


def test_pipeline_ende_zu_ende(tmp_path):
    """Inventar-Daten von Hand, dann Segmente, Lösungen, Themen, Klassifikation ohne KI, Statistik, Lernpfad."""
    daten = tmp_path
    (daten / "pdfs").mkdir()
    pfade = [_pdf(daten / "pdfs" / "aufgaben.pdf", AUFGABEN), _pdf(daten / "pdfs" / "loesungen.pdf", LOESUNGEN)]
    (daten / "themen.md").write_text("# Planen eines Softwareproduktes\n## Datenbanken\n- Datenmodell: Entität, Normalform\n"
                                     "## Sicherheit\n- Passwörter: Hashwert, Angriff\n", encoding="utf-8")
    db.init(daten / "saku.db")
    con = db.verbinden(daten / "saku.db")
    p_id = inventar.pruefung_anlegen(con, {"jahr": 2030, "saison": "Sommer", "bereich": inventar.PLANEN, "format": "aktuell", "dauer_min": 90})
    for pfad, art in zip(pfade, ("aufgaben", "loesungen")):
        con.execute("INSERT INTO dokument (dateiname, sha256, seiten, art, pruefung_id) VALUES (?, ?, 2, ?, ?)",
                    (pfad.name, hashlib.sha256(pfad.read_bytes()).hexdigest(), art, p_id))
    for schritt in (segmente, loesungen, themen, klassifikation, statistik, lernpfad):
        schritt.ausfuehren(con, daten, True, "api")

    teile = con.execute("SELECT t.kennung, t.punkte, t.loesung_text, t.bilder FROM teilaufgabe t ORDER BY t.id").fetchall()
    assert [(t["kennung"], t["punkte"]) for t in teile] == [("a", 4), ("b", 6), ("aa", 5), ("ab", 3)]
    assert all(t["loesung_text"] for t in teile) and "Brute Force" in teile[3]["loesung_text"]
    assert all((daten / b).exists() for t in teile for b in json.loads(t["bilder"]))
    assert con.execute("SELECT COUNT(*) FROM teilaufgabe_thema").fetchone()[0] >= 3
    assert con.execute("SELECT COUNT(*) FROM suche WHERE suche MATCH '\"Imker\"'").fetchone()[0] >= 1
    assert con.execute("SELECT COUNT(*) FROM station").fetchone()[0] >= 1
    # Ein zweiter Lauf behält IDs und Lernstand
    erste_id = con.execute("SELECT id FROM teilaufgabe WHERE kennung = 'aa'").fetchone()[0]
    con.execute("INSERT INTO karte (teilaufgabe_id, status) VALUES (?, 'gruen')", (erste_id,))
    segmente.ausfuehren(con, daten, True, "api")
    assert con.execute("SELECT status FROM karte JOIN teilaufgabe t ON t.id = teilaufgabe_id WHERE t.kennung = 'aa'").fetchone()[0] == "gruen"
    con.close()


def _leere_db(tmp_path):
    db.init(tmp_path / "saku.db")
    return db.verbinden(tmp_path / "saku.db")


def test_themen_mit_korrektur_bleiben(tmp_path):
    """Fällt ein Thema aus themen.md, bleibt es, solange eine manuelle Zuordnung daran hängt."""
    con = _leere_db(tmp_path)
    (tmp_path / "themen.md").write_text("# B\n## T\n- Alt\n- Weg\n", encoding="utf-8")
    themen.ausfuehren(con, tmp_path, True, "api")
    p_id = inventar.pruefung_anlegen(con, {"jahr": 2030, "saison": "Sommer", "bereich": inventar.PLANEN, "format": "aktuell", "dauer_min": 90})
    a_id = con.execute("INSERT INTO aufgabe (pruefung_id, nummer) VALUES (?, 1)", (p_id,)).lastrowid
    t_id = con.execute("INSERT INTO teilaufgabe (aufgabe_id, kennung, position) VALUES (?, 'a', 0)", (a_id,)).lastrowid
    alt = con.execute("SELECT id FROM thema WHERE name = 'Alt'").fetchone()[0]
    con.execute("INSERT INTO teilaufgabe_thema (teilaufgabe_id, thema_id, quelle) VALUES (?, ?, 'manuell')", (t_id, alt))
    (tmp_path / "themen.md").write_text("# B\n## T\n- Neu\n", encoding="utf-8")
    themen.ausfuehren(con, tmp_path, True, "api")
    namen = {z[0] for z in con.execute("SELECT name FROM thema")}
    assert {"Alt", "Neu"} <= namen and "Weg" not in namen
    (tmp_path / "themen.md").write_text("<!-- leer -->", encoding="utf-8")
    with pytest.raises(SystemExit):
        themen.ausfuehren(con, tmp_path, True, "api")


def test_ohne_ki_behaelt_ki_zuordnung(tmp_path):
    con = _leere_db(tmp_path)
    (tmp_path / "themen.md").write_text("# B\n## T\n- SQL: SELECT\n", encoding="utf-8")
    themen.ausfuehren(con, tmp_path, True, "api")
    p_id = inventar.pruefung_anlegen(con, {"jahr": 2030, "saison": "Sommer", "bereich": inventar.PLANEN, "format": "aktuell", "dauer_min": 90})
    a_id = con.execute("INSERT INTO aufgabe (pruefung_id, nummer) VALUES (?, 1)", (p_id,)).lastrowid
    t_id = con.execute("INSERT INTO teilaufgabe (aufgabe_id, kennung, position, text) VALUES (?, 'a', 0, 'kein Stichwort')", (a_id,)).lastrowid
    th = con.execute("SELECT id FROM thema WHERE ebene = 3").fetchone()[0]
    con.execute("INSERT INTO teilaufgabe_thema (teilaufgabe_id, thema_id, quelle) VALUES (?, ?, 'ki')", (t_id, th))
    klassifikation.ausfuehren(con, tmp_path, True, "api")
    assert [z[0] for z in con.execute("SELECT quelle FROM teilaufgabe_thema WHERE teilaufgabe_id = ?", (t_id,))] == ["ki"]


def test_lernpfad_neu_gebuendelt_behaelt_fortschritt(tmp_path):
    """Ändert sich die Bündelung, behalten Stationen mit gleichen Themen Einführung und bestandenen Mini-Test."""
    con = _leere_db(tmp_path)
    (tmp_path / "themen.md").write_text("# B\n## Eins\n- U1\n## Zwei\n- U2\n", encoding="utf-8")
    themen.ausfuehren(con, tmp_path, True, "api")
    eins, zwei = (con.execute("SELECT id FROM thema WHERE name = ?", (n,)).fetchone()[0] for n in ("Eins", "Zwei"))
    for pos, ids in enumerate([[eins], [eins, zwei]], start=1):  # alte Gliederung: Zwei hing an Eins
        s_id = con.execute("INSERT INTO station (position, titel, einfuehrung) VALUES (?, 't', ?)", (pos, f"E{pos}")).lastrowid
        con.executemany("INSERT INTO station_thema VALUES (?, ?)", [(s_id, i) for i in ids])
    con.execute("INSERT INTO stationstest (station_id, punkte_erreicht, punkte_moeglich, bestanden) VALUES (1, 5, 5, 1)")
    p_id = inventar.pruefung_anlegen(con, {"jahr": 2030, "saison": "Sommer", "bereich": inventar.PLANEN, "format": "aktuell", "dauer_min": 90})
    for nr, th in ((1, eins), (2, zwei)):
        a_id = con.execute("INSERT INTO aufgabe (pruefung_id, nummer) VALUES (?, ?)", (p_id, nr)).lastrowid
        for k in "abcdefghij":
            t_id = con.execute("INSERT INTO teilaufgabe (aufgabe_id, kennung, position, punkte) VALUES (?, ?, 0, 2)", (a_id, k)).lastrowid
            con.execute("INSERT INTO teilaufgabe_thema (teilaufgabe_id, thema_id, quelle) VALUES (?, ?, 'ki')", (t_id, th))
    con.commit()
    lernpfad.ausfuehren(con, tmp_path, True, "api")
    stationen = con.execute("SELECT s.id, s.einfuehrung, group_concat(st.thema_id) FROM station s "
                            "JOIN station_thema st ON st.station_id = s.id GROUP BY s.id").fetchall()
    eins_station = next(s for s in stationen if s[2] == str(eins))
    assert eins_station[1] == "E1"
    assert con.execute("SELECT bestanden FROM stationstest WHERE station_id = ?", (eins_station[0],)).fetchone()[0] == 1


def test_deckblatt_si_ap1_und_kopfleiste():
    """Erfundene Deckblätter: SI-Bereich über die Nummer, AP1 über Herbst, Aufgaben trotz „Lösungshinweisen“."""
    si = inventar.deckblatt(["Diese Kopfleiste bitte unbedingt ausfüllen! Abschlussprüfung Winter 2030/31 1202 2 "
                             "Für die Bewertung gilt die Vorgabe der Punkte in den Lösungshinweisen."], "x.pdf")
    assert (si["art"], si["bereich"], si["beruf"], si["saison"], si["teil1"]) == ("aufgaben", inventar.NETZWERKE, "1202", "Winter", False)
    assert inventar.teil_und_beruf(si) == ("AP2", "1202") and inventar.ausschluss(si) is None
    ap1 = inventar.deckblatt(["Abschlussprüfung Herbst 2030 Lösungshinweise IT-Berufe 1201 – 1202 – 1203"], "y.pdf")
    assert (ap1["art"], ap1["bereich"], ap1["teil1"]) == ("loesungen", inventar.ARBEITSPLATZ, True)
    assert inventar.teil_und_beruf(ap1) == ("AP1", "IT")
    scan = inventar.deckblatt(["kaum lesbar Sommer 2030"], "Sommer 2030 G1 (SI).pdf")
    assert (scan["bereich"], scan["beruf"]) == (inventar.KONZEPTION, "1202")
