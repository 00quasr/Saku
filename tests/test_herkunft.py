"""CSRF-Schutz: schreibende Anfragen nur von gleicher Herkunft; ohne Sec-Fetch-Site und Origin (Testclient, curl) wie bisher.
DNS-Rebinding: nur die lokalen Host-Namen."""

import pytest

HTMX = {"HX-Request": "true"}


@pytest.mark.parametrize("kopf", [
    {"Sec-Fetch-Site": "cross-site"},
    {"Sec-Fetch-Site": "same-site"},  # z. B. ein anderer Dienst auf localhost mit anderem Port
    {"Origin": "https://boese.example"},
    {"Origin": "http://localhost:3000"},
    {"Origin": "null"},
    {"Sec-Fetch-Site": "same-origin", "Origin": "https://boese.example"},
])
def test_fremde_herkunft_wird_abgelehnt(client, con, kopf):
    antwort = client.post("/keiko/1/bewerten", data={"ergebnis": "3"}, headers=HTMX | kopf)
    assert antwort.status_code == 403
    assert con.execute("SELECT COUNT(*) FROM bewertung").fetchone()[0] == 0
    assert client.post("/einstellungen/farbschema", data={"farbschema": "hell"}, headers=kopf).status_code == 403


@pytest.mark.parametrize("kopf", [
    {},  # Testclient, curl, alte Clients
    {"Sec-Fetch-Site": "same-origin", "Origin": "http://localhost"},  # htmx und Formulare im Browser und im App-Fenster
    {"Sec-Fetch-Site": "none"},  # selbst eingegeben
    {"Origin": "http://LOCALHOST"},
])
def test_gleiche_herkunft_und_ohne_kopfzeilen(client, con, kopf):
    assert client.post("/keiko/1/bewerten", data={"ergebnis": "3"}, headers=HTMX | kopf).status_code == 200
    assert client.post("/einstellungen/farbschema", data={"farbschema": "hell"}, headers=kopf).status_code == 200


def test_lesen_bleibt_frei(client):
    """GET (Seiten, Fragmente, Sensei-Streams) prüft der Schutz nicht: Links von außen auf Saku sollen funktionieren."""
    fremd = {"Sec-Fetch-Site": "cross-site", "Origin": "https://boese.example"}
    assert client.get("/", headers=fremd).status_code == 200
    assert client.get("/keiko/1/loesung", headers=HTMX | fremd).status_code == 200
    assert client.get("/sensei/stream/gibtsnicht", headers=fremd).status_code != 403


@pytest.mark.parametrize("host", ["boese.example:5050", "127.0.0.1.nip.io:5050", "localhost.boese.example"])
def test_fremder_host_name_wird_abgelehnt(client, con, host):
    """Eine fremde Seite, deren Name auf 127.0.0.1 umgebogen wird, ist für den Browser gleiche Herkunft – lesen und schreiben."""
    gleich = {"Host": host, "Sec-Fetch-Site": "same-origin", "Origin": f"http://{host}"}
    assert client.get("/", headers=gleich).status_code == 400
    assert client.post("/keiko/1/bewerten", data={"ergebnis": "3"}, headers=HTMX | gleich).status_code == 400
    assert con.execute("SELECT COUNT(*) FROM bewertung").fetchone()[0] == 0


@pytest.mark.parametrize("host", ["127.0.0.1:5050", "localhost:5050", "localhost"])  # Browser schicken den Namen klein
def test_lokale_host_namen(client, host):
    assert client.get("/", headers={"Host": host}).status_code < 400
