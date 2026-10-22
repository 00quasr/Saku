"""Niwa: Wissensgraph aus Themen, Lernfeldern und Begriffen, Notizen, der Garten blüht (Demo-Daten, erfunden)."""

from saku import niwa


def thema_id(con, name: str) -> int:
    return con.execute("SELECT id FROM thema WHERE name = ?", (name,)).fetchone()[0]


def begriffe_anlegen(con) -> int:
    """Zwei erfundene Begriffe an zwei Teilaufgaben: kommen also zweimal gemeinsam dran."""
    ids = [z[0] for z in con.execute("SELECT teilaufgabe_id FROM v_zuordnung WHERE thema_id = ? LIMIT 2",
                                     (thema_id(con, "Datenbanken"),))]
    for name in ("Primärschlüssel", "Fremdschlüssel"):
        b = con.execute("INSERT INTO begriff (name, slug) VALUES (?, ?)", (name, name.lower())).lastrowid
        con.executemany("INSERT INTO teilaufgabe_begriff (teilaufgabe_id, begriff_id) VALUES (?, ?)", [(t, b) for t in ids])
    con.commit()
    return b


def test_graph_mit_gliederung_lernfeld_und_begriffen(con):
    con.execute("INSERT INTO lernfeld (nummer, titel, jahr) VALUES ('5', 'Daten verwalten', 1)")
    con.execute("INSERT INTO thema_lernfeld (thema_id, lernfeld_id) SELECT ?, id FROM lernfeld", (thema_id(con, "Datenbanken"),))
    fremd = begriffe_anlegen(con)
    daten = niwa.graph(con)
    arten = {k["art"] for k in daten["knoten"]}
    assert arten == {"bereich", "thema", "unterthema", "lernfeld", "begriff"}
    db = next(k for k in daten["knoten"] if k["name"] == "Datenbanken")
    assert db["wert"] == 32 and db["stufe"] == "samen" and not db["geuebt"]
    kanten = {(k["source"], k["target"], k["art"]) for k in daten["kanten"]}
    assert any(a == "teil" and t == db["id"] for _, t, a in kanten)
    assert any(s.startswith("lf") and t == db["id"] for s, t, _ in kanten)
    assert not any(a == "gemeinsam" for *_, a in kanten)  # Begriffe untereinander nur in der Notiz
    # Begriff hängt am Thema, bei dem er vorkommt
    assert any(t == f"b{fremd}" and a == "begriff" for _, t, a in kanten)


def test_umfang_zeigt_nur_eigene_bereiche(con):
    con.execute("UPDATE einstellung SET wert = 'AP1' WHERE schluessel = 'teil'")
    assert niwa.graph(con)["knoten"] == []


def test_garten_blueht_einmal(con):
    assert niwa.aufgeblueht(con, niwa.graph(con)) == []  # erster Besuch: nur merken
    con.execute("INSERT INTO karte (teilaufgabe_id, status) SELECT z.teilaufgabe_id, 'gruen' FROM v_zuordnung z "
                "WHERE z.thema_id = ?", (thema_id(con, "Qualitätssicherung"),))
    assert f"t{thema_id(con, 'Qualitätssicherung')}" in niwa.aufgeblueht(con, niwa.graph(con))
    assert niwa.aufgeblueht(con, niwa.graph(con)) == []  # pulsiert nur einmal


def test_routen_und_notizen(client, con):
    db = thema_id(con, "Datenbanken")
    fremd = begriffe_anlegen(con)
    seite = client.get("/niwa/").get_data(as_text=True)
    assert 'id="graph-daten"' in seite and "force-graph.min.js" in seite and "Datenbanken" in seite

    fragment = client.get(f"/niwa/thema/{db}", headers={"HX-Request": "true"}).get_data(as_text=True)
    assert f'href="/keiko/?thema={db}"' in fragment and f'data-sensei-thema="{db}"' in fragment
    assert "4 Teilaufgaben" in fragment and "Sensei erklärt" in fragment and f'data-knoten="b{fremd}"' in fragment
    weiter = client.get(f"/niwa/thema/{db}")
    assert weiter.status_code == 302 and weiter.location.endswith(f"/niwa/?thema={db}")
    # Auswahl im onload-Attribut: JSON-Anführungszeichen dürfen das Attribut nicht beenden
    assert f"""getElementById("graph"), "t{db}")'""" in client.get(f"/niwa/?thema={db}").get_data(as_text=True)
    assert f"""getElementById("graph"), "b{fremd}")'""" in client.get(f"/niwa/?begriff={fremd}").get_data(as_text=True)
    assert client.get("/niwa/thema/9999", headers={"HX-Request": "true"}).status_code == 404

    notiz = client.get(f"/niwa/begriff/{fremd}").get_data(as_text=True)
    assert "Fremdschlüssel" in notiz and "2 Fundstellen" in notiz and f'data-knoten="b{fremd - 1}"' in notiz
    con.execute("UPDATE begriff SET erklaerung = 'Verweist auf einen **Primärschlüssel**.' WHERE id = ?", (fremd,))
    con.commit()
    assert "<strong>Primärschlüssel</strong>" in client.post(f"/niwa/begriff/{fremd}/erklaeren").get_data(as_text=True)
    assert client.get("/niwa/begriff/9999").status_code == 404
