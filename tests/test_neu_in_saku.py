"""„Neu in Saku“ auf Heute: nur für bestehende Nutzer, einmal, wegklickbar (Demo-Daten, erfundene Prüfungen)."""

from saku import db
from saku.lernen import karten
from saku.web.routen.heute import NEU_IN_SAKU

HTMX = {"HX-Request": "true"}


def test_neu_fuer_bestehende_bis_verstanden(client, con):
    assert "Neu in Saku" not in client.get("/").get_data(as_text=True)  # noch nichts gelernt: alles ist neu, nichts davon „neu“

    karten.bewerten(con, 1, 3)
    html = client.get("/").get_data(as_text=True)
    assert "Neu in Saku" in html and 'id="neu-in-saku"' in html
    for link in ("/rechnen/probe", "/rechnen/algorithmus", "/rechnen/", "/fahrplan", "/niwa/"):
        assert f'href="{link}"' in html, link
    assert f'hx-vals=\'{{"neu_gesehen": "{NEU_IN_SAKU}"}}\'' in html and 'hx-post="/einstellungen/neu_gesehen"' in html
    assert "Probeprüfung" in html and NEU_IN_SAKU == "2026-10-25"  # die Versionsmarke bleibt: noch nicht gesehen

    assert client.post("/einstellungen/neu_gesehen", data={"neu_gesehen": "irgendwas"}, headers=HTMX).status_code == 400
    weg = client.post("/einstellungen/neu_gesehen", data={"neu_gesehen": NEU_IN_SAKU}, headers=HTMX)
    assert weg.status_code == 200 and weg.get_data(as_text=True) == ""  # hx-swap outerHTML: die Karte verschwindet
    assert "Neu in Saku" not in client.get("/").get_data(as_text=True)


def test_nach_der_einfuehrung_nicht(client, con):
    db.setze_einstellung(con, "einfuehrung", "")
    client.post("/willkommen/fertig", data={"ziel": "heute"})
    karten.bewerten(con, 1, 3)
    assert "Neu in Saku" not in client.get("/").get_data(as_text=True)


def test_neue_marke_zeigt_die_karte_noch_einmal(client, con):
    """Wer die Karte zur alten Marke weggeklickt hat, sieht sie zur neuen wieder – einmal."""
    karten.bewerten(con, 1, 3)
    db.setze_einstellung(con, "neu_gesehen", "2026-10")
    assert 'id="neu-in-saku"' in client.get("/").get_data(as_text=True)
