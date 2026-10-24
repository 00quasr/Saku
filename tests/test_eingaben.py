"""Eingaben von außen (Adresse, Formular): kaputte, riesige oder fehlende Werte enden nie mit Fehler 500 (Demo-Daten)."""

import pytest

from saku.lernen import rechnen

RIESIG = "9" * 30  # größer als 2^63: Python nimmt es als int, SQLite nicht
HTMX = {"HX-Request": "true"}


@pytest.mark.parametrize("methode, url, formular", [
    ("get", f"/keiko/?teilaufgabe={RIESIG}", None),
    ("get", f"/keiko/?thema=-{RIESIG}", None),
    ("get", f"/keiko/verlauf?seite={RIESIG}", None),
    ("get", f"/shiken/{RIESIG}", None),
    ("post", "/rechnen/subnetz/pruefen", {"seed": RIESIG, "feld-praefix": "24"}),
    ("post", "/rechnen/subnetz/pruefen", {"seed": "7", "feld-praefix": "24", "start": RIESIG}),
    ("post", "/rechnen/sprint/lauf", {"a": f"subnetz:{RIESIG}", "start": "1"}),
    ("post", "/rechnen/sprint/lauf", {"a": "subnetz:5", "start": f"-{RIESIG}"}),
    ("post", "/michi/1/test", {"teilaufgabe": RIESIG, f"punkte-{RIESIG}": "1"}),
    ("post", "/keiko/1/bewerten", {"ergebnis": "3", "runde": RIESIG}),
    ("post", "/keiko/zurueck", {"runde": RIESIG}),
    ("post", "/bunseki/zuordnung/1", {"thema": RIESIG}),
])
def test_riesige_zahlen_ohne_absturz(client, methode, url, formular):
    assert getattr(client, methode)(url, data=formular, headers=HTMX).status_code in (200, 400)


def test_kaputte_eingaben_in_jeder_rechenart(client):
    """Jede Rechenart mit Unsinn in allen Feldern: geprüft wird, Fehler gibt es keinen."""
    for art in rechnen.ARTEN:
        felder = [f.name for f in rechnen.erzeugen(art, 11).felder]
        for wert in ("x", "1e309", "nan", "2^999", "a" * 5000, "１２", "ffff:" * 20):
            antwort = client.post(f"/rechnen/{art}/pruefen", data={"seed": "11", **{f"feld-{f}": wert for f in felder}}, headers=HTMX)
            assert antwort.status_code == 200, (art, wert)
