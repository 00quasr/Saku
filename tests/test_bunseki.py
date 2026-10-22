"""Bunseki: Abfragen der Reiter, Korrektur der Zuordnung, Leerzustand."""

from saku import db
from saku.web import create_app
from saku.web.routen import bunseki


def thema_id(con, name: str) -> int:
    return con.execute("SELECT id FROM thema WHERE name = ?", (name,)).fetchone()[0]


def teilaufgabe_id(con, text_anfang: str) -> int:
    return con.execute("SELECT id FROM teilaufgabe WHERE text LIKE ?", (text_anfang + "%",)).fetchone()[0]


def pruefung(con, jahr: int, saison: str, thema: str) -> int:
    """Erfundene Prüfung mit einer Teilaufgabe zum Thema."""
    p = con.execute("INSERT INTO pruefung (jahr, saison, bereich) VALUES (?, ?, 'Demo')", (jahr, saison)).lastrowid
    a = con.execute("INSERT INTO aufgabe (pruefung_id, nummer) VALUES (?, 1)", (p,)).lastrowid
    t = con.execute("INSERT INTO teilaufgabe (aufgabe_id, kennung, position, text, punkte) VALUES (?, 'a', 0, 'Erfunden', 5)",
                    (a,)).lastrowid
    con.execute("INSERT INTO teilaufgabe_thema (teilaufgabe_id, thema_id, sicherheit) VALUES (?, ?, 0.9)", (t, thema_id(con, thema)))
    return t


def namen(zeilen) -> list[str]:
    return [z["name"] for z in zeilen]


def test_termin_name():
    assert bunseki.termin_name(2023 * 2 + 1) == "Winter 2023/24"
    assert bunseki.termin_name(2024 * 2) == "Sommer 2024"
    assert bunseki.termin_name(1999 * 2 + 1) == "Winter 1999/00"


def test_inventar(con):
    inventar = bunseki.inventar(con)
    assert [p["termin"] for p in inventar] == ["Sommer 2024", "Winter 2023/24", "Sommer 2023"]
    assert all(p["seiten"] == 12 and p["textebene"] == 1 and p["mit_loesung"] == p["teilaufgaben"] for p in inventar)
    assert sum(p["teilaufgaben"] for p in inventar) == 14


def test_heatmap(con):
    h = bunseki.heatmap(con)
    assert [t["termin"] for t in h["termine"]] == ["Sommer 2023", "Winter 2023/24", "Sommer 2024"]
    zeilen = {z["name"]: z for b in h["bereiche"] for z in b["zeilen"]}
    assert len(zeilen) == 7
    db_zellen = zeilen["Datenbanken"]["zellen"]
    assert [z["punkte"] for z in db_zellen] == [0, 18, 14]
    assert [z["stufe"] for z in db_zellen] == [0, 5, 4]  # 18 ist das Maximum
    assert all(z["stufe"] == 0 for z in zeilen["Arbeitsrecht"]["zellen"])
    assert all(0 <= z["stufe"] <= 5 for z in (zelle for zeile in zeilen.values() for zelle in zeile["zellen"]))


def test_dauerbrenner(con):
    assert bunseki.dauerbrenner(con) == []  # kein Unterthema in 3 von 3 Terminen
    for text in ("Ermitteln Sie", "Schreiben Sie eine SQL", "Verbinden Sie"):
        con.execute("INSERT INTO teilaufgabe_thema (teilaufgabe_id, thema_id, gewicht) VALUES (?, ?, 0.5)",
                    (teilaufgabe_id(con, text), thema_id(con, "Rekursion")))
    dauer = bunseki.dauerbrenner(con)
    assert namen(dauer) == ["Rekursion"]
    assert dauer[0]["termine_prozent"] == 100 and dauer[0]["eltern"] == "Algorithmen"


def test_lange_nicht_dran(con):
    assert bunseki.lange_nicht_dran(con) == []
    for jahr, saison in [(2024, "Winter"), (2025, "Sommer"), (2025, "Winter")]:
        pruefung(con, jahr, saison, "SQL")
    lange = {z["name"]: z for z in bunseki.lange_nicht_dran(con)}
    # zuletzt Sommer 2023 bzw. Winter 2023/24: 5 bzw. 4 Termine seitdem; Sommer 2024 (3 Termine) ist noch nicht „lange“
    assert lange["Netzplan"]["seitdem"] == 5 and lange["Rekursion"]["seitdem"] == 4
    assert "ER-Modell" not in lange and "SQL" not in lange and "Lastenheft und Pflichtenheft" not in lange
    assert bunseki.termin_name(lange["Rekursion"]["letzter_termin"]) == "Winter 2023/24"


def test_nie_geprueft(con):
    assert set(namen(bunseki.nie_geprueft(con))) == {"Lastenheft und Pflichtenheft", "Use-Case-Diagramm",
                                                     "Kündigung und Kündigungsschutz"}
    # nur Themen der Prüfungsbereiche im Umfang: die Demo hat keine AP1-Themen
    from saku.db import setze_einstellung
    setze_einstellung(con, "teil", "AP1")
    assert bunseki.nie_geprueft(con) == []


def test_ohne_thema(con):
    t = teilaufgabe_id(con, "Ermitteln Sie")
    con.execute("DELETE FROM teilaufgabe_thema WHERE teilaufgabe_id = ?", (t,))
    assert [z["teilaufgabe_id"] for z in bunseki.ohne_thema(con)] == [t]


def test_kontrolle_und_korrektur(client, con):
    t = teilaufgabe_id(con, "Bestimmen Sie die Laufzeitklasse")
    con.execute("UPDATE teilaufgabe_thema SET sicherheit = 0.4 WHERE teilaufgabe_id = ?", (t,))
    con.commit()
    kontrolle = bunseki.kontrolle(con)
    assert [z["teilaufgabe_id"] for z in kontrolle] == [t]
    assert kontrolle[0]["themen"] == "Sortieren und Suchen" and kontrolle[0]["haupt_id"] == thema_id(con, "Sortieren und Suchen")
    seite = client.get("/bunseki/").get_data(as_text=True)
    assert f'hx-post="/bunseki/zuordnung/{t}"' in seite

    antwort = client.post(f"/bunseki/zuordnung/{t}", data={"thema": thema_id(con, "Rekursion")})
    assert "Gespeichert: Rekursion" in antwort.get_data(as_text=True)
    zuordnung = con.execute("SELECT thema_id, gewicht, quelle, sicherheit FROM teilaufgabe_thema WHERE teilaufgabe_id = ?",
                            (t,)).fetchall()
    assert [tuple(z) for z in zuordnung] == [(thema_id(con, "Rekursion"), 1.0, "manuell", 1.0)]
    assert bunseki.kontrolle(con) == []

    bereich = thema_id(con, "Planen eines Softwareproduktes")
    assert client.post(f"/bunseki/zuordnung/{t}", data={"thema": bereich}).status_code == 400  # Ebene 1 nicht
    assert client.post("/bunseki/zuordnung/9999", data={"thema": thema_id(con, "SQL")}).status_code == 400


def test_ki_nutzung(client, con):
    con.executemany("INSERT INTO ki_aufruf (zweck, modell, tokens_ein, tokens_aus, aus_cache) VALUES (?, 'demo-modell', ?, ?, ?)",
                    [("tutor", 1200, 300, 0), ("tutor", 800, 200, 0), ("klassifikation", 0, 0, 1)])
    con.commit()
    nutzung = {z["zweck"]: z for z in bunseki.ki_nutzung(con)}
    assert nutzung["tutor"]["aufrufe"] == 2 and nutzung["tutor"]["tokens_ein"] == 2000
    seite = client.get("/bunseki/").get_data(as_text=True)
    assert "2.000" in seite and "Summe" in seite


def test_seite_mit_allen_reitern(client):
    seite = client.get("/bunseki/").get_data(as_text=True)
    for reiter in ("Inventar", "Heatmap", "Dauerbrenner", "Lange nicht dran", "Nie geprüft", "Ohne Thema", "Kontrolle", "KI-Nutzung"):
        assert f">\n        {reiter}" in seite, reiter
    assert seite.count('role="tabpanel"') == 10  # mit Überblick und Katalog
    assert 'data-tooltip="Winter 2023/24 · 18 Punkte"' in seite
    assert "keine Vorhersage" in seite


def test_leerzustand(tmp_path):
    db.init(tmp_path / "saku.db")
    seite = create_app(tmp_path).test_client().get("/bunseki/").get_data(as_text=True)
    assert "Noch ist nichts analysiert" in seite and 'role="tablist"' not in seite


def test_katalog_als_checkliste(con):
    katalog = bunseki.katalog(con)
    assert katalog and all(b["gesamt"] >= b["geprueft"] >= b["sicher"] for b in katalog)
    unterthemen = [u for b in katalog for t in b["themen"] for u in t["unterthemen"]]
    assert any(u["termine"] for u in unterthemen)
