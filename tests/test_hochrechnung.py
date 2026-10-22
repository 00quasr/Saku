"""Hochrechnung nach AO 2020: Gewichtung, Bestehensregeln, Ergänzungsprüfung (erfundene Werte)."""

from saku import db
from saku.lernen import hochrechnung


def test_bestanden_mit_gewichtung():
    h = hochrechnung.berechnen({"ap1": 70, "projekt": 80, "pb2": 60, "pb3": 55, "wiso": 75})
    assert h["gesamt"] == 73.0 and h["teil2"] == 73.8 and h["note"] == 3 and h["bestanden"] is True


def test_regeln_und_ergaenzung():
    # Projekt gut, aber zwei schriftliche Bereiche unter 50: Regel 4 verletzt; einer davon ungenügend
    h = hochrechnung.berechnen({"ap1": 60, "projekt": 90, "pb2": 40, "pb3": 25, "wiso": 70})
    regeln = dict(h["regeln"])
    assert regeln["Mindestens zwei der übrigen Bereiche ausreichend"] is False
    assert regeln["Kein Bereich von Teil 2 ungenügend"] is False and h["bestanden"] is False
    assert h["ergaenzung"] == {"pb2": 70, "pb3": 100}  # (2 × 40 + 70) / 3 = 50; pb3 nur mit 100 Punkten mündlich
    offen = hochrechnung.berechnen({"ap1": None, "projekt": None, "pb2": 60, "pb3": 60, "wiso": 60})
    assert offen["gesamt"] is None and offen["bestanden"] is None


def test_stand_aus_eingabe_und_route(client, con):
    db.setze_einstellung(con, "note_projekt", "85")
    zeilen = {z["schluessel"]: z for z in hochrechnung.stand(con)["zeilen"]}
    assert zeilen["projekt"]["wert"] == 85 and zeilen["projekt"]["quelle"] == "eingabe"
    assert zeilen["pb2"]["quelle"] in (None, "lernstand", "simulation")
    assert "Hochrechnung deiner Abschlussprüfung" in client.get("/shiken/").get_data(as_text=True)
    assert client.post("/einstellungen/note_ap1", data={"note_ap1": "120"}).status_code == 400
    assert client.post("/einstellungen/note_ap1", data={"note_ap1": "72,5"}).headers["HX-Refresh"] == "true"
    assert db.einstellung(con, "note_ap1") == "72.5"
