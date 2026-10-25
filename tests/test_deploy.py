"""Saku im Netz (docs/DEPLOY.md): lokal ohne Variablen alles wie bisher; mit SAKU_PASSWORT nur nach der Anmeldung,
Host-Namen aus der Umgebung, ProxyFix hinter Railway, Paket bauen und hochladen (Demo-Daten)."""

import io
import json
import re
import sqlite3
import tarfile
from pathlib import Path

import pytest
from flask import request

from saku import config, db, paket
from saku.web import create_app
from saku.web.routen import anmeldung
from tests.demo_daten import anlegen

PASSWORT = "ein-langes-richtiges-passwort"


@pytest.fixture(autouse=True)
def frisch(monkeypatch):
    """Keine Fehlversuche aus anderen Tests, keine Sekunde Wartezeit, keine Umgebung von außen."""
    anmeldung._fehlversuche.clear()
    monkeypatch.setattr(anmeldung, "VERZOEGERUNG", 0)
    for name in ("SAKU_DOMAINS", "RAILWAY_PUBLIC_DOMAIN"):
        monkeypatch.delenv(name, raising=False)


def _app(daten, monkeypatch, passwort=PASSWORT, server=False):
    monkeypatch.setattr(config, "PASSWORT", passwort)
    app = create_app(daten, server=server)
    app.config["TESTING"] = True
    return app


def _anmelden(client, passwort=PASSWORT, **kwargs):
    return client.post("/anmelden", data={"passwort": passwort}, **kwargs)


def test_lokal_ohne_variablen_wie_bisher(client, app):
    assert client.get("/").status_code == 200
    assert client.get("/anmelden").headers["Location"] == "/"  # ohne Passwort keine Anmeldung
    assert client.get("/", base_url="http://saku.example.org").status_code == 400  # nur localhost
    assert not app.config["SESSION_COOKIE_SECURE"] and not app.config["SERVER"]
    assert "Paket übernehmen" not in client.get("/einstellungen").get_data(as_text=True)
    assert client.post("/einstellungen/paket", data=b"x").status_code == 404


def test_mit_passwort_leitet_jede_seite_zur_anmeldung(daten, con, monkeypatch):
    app = _app(daten, monkeypatch)
    client = app.test_client()
    routen = [r.rule for r in app.url_map.iter_rules() if "GET" in r.methods and not r.arguments]
    routen += ["/bild/aufgaben/x.png", "/sensei/stream/abc", "/keiko/1", "/einstellungen/saku.db", "/einstellungen/lernstand.json"]
    for url in routen:
        if url in ("/anmelden",) or url.startswith("/static"):
            continue
        antwort = client.get(url)
        assert antwort.status_code == 302 and antwort.headers["Location"] == "/anmelden", url
    htmx = client.get("/keiko/", headers={"HX-Request": "true"})
    assert htmx.status_code == 401 and htmx.headers["HX-Redirect"] == "/anmelden"
    assert client.post("/einstellungen/farbschema", data={"farbschema": "hell"}).status_code == 302
    assert db.einstellung(con, "farbschema") == "dunkel"  # nicht gespeichert
    assert client.get("/static/css/saku.css").status_code == 200  # die Anmeldeseite braucht ihr Aussehen
    seite = client.get("/anmelden")
    assert seite.status_code == 200 and 'type="password"' in seite.get_data(as_text=True)
    assert "Demo GmbH" not in seite.get_data(as_text=True)


def test_anmelden_falsch_richtig_abmelden(daten, monkeypatch):
    client = _app(daten, monkeypatch).test_client()
    falsch = _anmelden(client, "falsch")
    assert falsch.status_code == 401 and "stimmt nicht" in falsch.get_data(as_text=True)
    assert client.get("/").status_code == 302
    richtig = _anmelden(client)
    assert richtig.status_code == 302 and richtig.headers["Location"] == "/"
    assert client.get("/").status_code == 200
    assert "Abmelden" in client.get("/einstellungen").get_data(as_text=True)
    client.post("/abmelden")
    assert client.get("/").status_code == 302


def test_sperre_nach_fehlversuchen_je_ip(daten, monkeypatch):
    client = _app(daten, monkeypatch).test_client()
    for _ in range(anmeldung.VERSUCHE):
        assert _anmelden(client, "falsch").status_code == 401
    assert _anmelden(client).status_code == 429  # gesperrt, auch mit dem richtigen Passwort
    assert client.get("/").status_code == 302
    assert _anmelden(client, environ_base={"REMOTE_ADDR": "10.0.0.2"}).status_code == 302  # andere IP


def test_neues_passwort_meldet_ab(daten, monkeypatch):
    monkeypatch.setattr(config, "GEHEIM", "fest")
    client = _app(daten, monkeypatch).test_client()
    _anmelden(client)
    cookie = client.get_cookie("session").value
    neu = _app(daten, monkeypatch, passwort="ein-anderes-passwort").test_client()
    neu.set_cookie("session", cookie)
    assert neu.get("/").status_code == 302
    gleich = _app(daten, monkeypatch).test_client()  # gleiches Geheimnis und Passwort: Sitzung gilt nach dem Neustart
    gleich.set_cookie("session", cookie)
    assert gleich.get("/").status_code == 200


def test_hosts_aus_der_umgebung(daten, monkeypatch):
    monkeypatch.setenv("SAKU_DOMAINS", "saku.example.org, Lernen.Example.org,")
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "saku-production.up.railway.app")
    assert config.domains() == ["saku.example.org", "lernen.example.org", "saku-production.up.railway.app"]
    client = _app(daten, monkeypatch, passwort="").test_client()
    for host in ("saku.example.org", "lernen.example.org", "saku-production.up.railway.app", "localhost"):
        assert client.get("/", base_url=f"https://{host}").status_code == 200, host
    assert client.get("/", base_url="https://boese.example.com").status_code == 400


def test_proxyfix_hinter_railway(daten, monkeypatch):
    """TLS endet am Proxy: Saku sieht http, der Proxy sagt https und den Host. Daraus werden das sichere Cookie, die
    richtige Herkunft für den CSRF-Schutz und die IP für die Sperre."""
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "saku.up.railway.app")
    proxy = {"X-Forwarded-Proto": "https", "X-Forwarded-Host": "saku.up.railway.app", "X-Forwarded-For": "203.0.113.7",
             "Origin": "https://saku.up.railway.app", "Sec-Fetch-Site": "same-origin"}
    app = _app(daten, monkeypatch, server=True)
    app.add_url_rule("/adresse", "adresse", lambda: request.url)
    client = app.test_client()
    antwort = _anmelden(client, headers=proxy)
    assert antwort.status_code == 302
    cookie = antwort.headers["Set-Cookie"]
    assert all(teil in cookie for teil in ("Secure", "HttpOnly", "SameSite=Lax", "Expires="))
    assert client.get("/adresse", headers=proxy, base_url="https://localhost").text == "https://saku.up.railway.app/adresse"
    # ohne ProxyFix (lokal) wäre der Host localhost und die Herkunft fremd
    assert _app(daten, monkeypatch).test_client().post("/anmelden", data={"passwort": PASSWORT}, headers=proxy).status_code == 403
    _anmelden(app.test_client(), "falsch", headers=proxy)
    assert "203.0.113.7" in anmeldung._fehlversuche  # die IP des Browsers, nicht die des Proxys


def test_server_startet_nur_mit_passwort_und_volume(monkeypatch, tmp_path):
    from saku.__main__ import server
    monkeypatch.setattr(config, "PASSWORT", "")
    with pytest.raises(SystemExit, match="SAKU_PASSWORT"):
        server()
    monkeypatch.setattr(config, "PASSWORT", PASSWORT)
    monkeypatch.setattr(config, "DATEN", tmp_path / "data")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "x")
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    with pytest.raises(SystemExit, match="Volume"):
        server()
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(tmp_path / "anderswo"))
    with pytest.raises(SystemExit, match="Volume"):
        server()


# --- Paket ---------------------------------------------------------------------------------------------------------

def _paket_von(daten: Path, ziel: Path) -> set[str]:
    paket.bauen(ziel, daten)
    with tarfile.open(ziel) as tar:
        return set(tar.getnames())


def test_paket_enthaelt_nur_erlaubtes(daten, tmp_path):
    con = db.verbinden(daten / "saku.db")
    bilder = {p for (spalte,) in con.execute("SELECT bilder || loesung_bilder FROM teilaufgabe") for p in re.findall(r"aufgaben/[^\"]+", spalte)}
    # eine Abbildung nur im Markdown, wie sie aufbereiten anlegt
    (daten / "aufgaben" / "abb").mkdir(parents=True)
    (daten / "aufgaben" / "abb" / "1a-abb1.png").write_bytes(b"png")
    con.execute("UPDATE teilaufgabe SET inhalt = 'Siehe ![Netzplan](/bild/aufgaben/abb/1a-abb1.png).' WHERE id = 1")
    con.commit()
    con.close()
    for fremd in ("quellen/pruefung.pdf", "pdfs/a.pdf", "modelle/modell.onnx", "backups/saku-2026-01-01.db", ".env",
                  "aufgaben/unbenutzt.png", "bilder/heute.jpg", "themen.md"):
        (daten / fremd).parent.mkdir(parents=True, exist_ok=True)
        (daten / fremd).write_text("privat")
    (daten / "projekt").mkdir()
    (daten / "projekt" / "text.md").write_text("Mein Projekt")
    namen = _paket_von(daten, tmp_path / "saku-paket.tar.gz")
    assert namen == {"saku.db", "projekt/text.md", "aufgaben/abb/1a-abb1.png", *bilder}
    assert len(bilder) > 10 and all(paket.erlaubt(n) for n in namen)


def _tar(eintraege: dict[str, bytes], link: str | None = None) -> bytes:
    puffer = io.BytesIO()
    with tarfile.open(fileobj=puffer, mode="w:gz") as tar:
        for name, inhalt in eintraege.items():
            info = tarfile.TarInfo(name)
            info.size = len(inhalt)
            tar.addfile(info, io.BytesIO(inhalt))
        if link:
            info = tarfile.TarInfo(link)
            info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
            tar.addfile(info)
    return puffer.getvalue()


@pytest.fixture
def server(tmp_path, monkeypatch):
    """Saku im Netz mit eigener Demo-Datenbank und eigenem Lernstand, angemeldet."""
    daten = tmp_path / "volume"
    anlegen(daten)
    app = _app(daten, monkeypatch, server=True)
    client = app.test_client()
    with client.session_transaction() as sitzung:
        sitzung["angemeldet"] = True
    return client, daten


def _hochladen(client, inhalt: bytes):
    return client.post("/einstellungen/paket", data=inhalt, content_type="application/gzip")


def test_hochladen_lehnt_ab(server, monkeypatch, tmp_path):
    client, daten = server
    vorher = (daten / "saku.db").read_bytes()
    db_bytes = (daten / "saku.db").read_bytes()
    abgelehnt = {
        "Pfad-Ausbruch": _tar({"saku.db": db_bytes, "aufgaben/../../ausbruch.png": b"x"}),
        "absoluter Pfad": _tar({"saku.db": db_bytes, "/tmp/ausbruch.png": b"x"}),
        "fremde Datei": _tar({"saku.db": db_bytes, ".env": b"ANTHROPIC_API_KEY=x"}),
        "PDF": _tar({"saku.db": db_bytes, "quellen/a.pdf": b"%PDF"}),
        "Link": _tar({"saku.db": db_bytes}, link="aufgaben/link.png"),
        "ohne Datenbank": _tar({"aufgaben/a.png": b"x"}),
        "keine Datenbank": _tar({"saku.db": b"kein sqlite"}),
        "kein Archiv": b"nur Text",
    }
    for grund, inhalt in abgelehnt.items():
        assert _hochladen(client, inhalt).status_code == 400, grund
    assert not (tmp_path / "ausbruch.png").exists() and not list(tmp_path.rglob("ausbruch.png"))
    monkeypatch.setattr(paket, "GRENZE", 1000)
    assert _hochladen(client, _tar({"saku.db": db_bytes})).status_code == 413
    assert (daten / "saku.db").read_bytes() == vorher
    assert not list(daten.glob(".paket*"))  # nichts liegen geblieben
    abgemeldet = create_app(daten, server=True).test_client()
    assert abgemeldet.post("/einstellungen/paket", data=_tar({"saku.db": db_bytes})).status_code == 302


def test_hochladen_ersetzt_katalog_und_behaelt_lernstand(server, tmp_path):
    client, daten = server
    # zu Hause: Demo-Katalog mit einer Prüfung mehr und einer Bewertung
    zuhause = tmp_path / "zuhause"
    anlegen(zuhause)
    con = db.verbinden(zuhause / "saku.db")
    con.execute("INSERT INTO pruefung (jahr, saison, bereich, beruf) VALUES (2030, 'Sommer', 'Neu aus der Pipeline', '1201')")
    con.execute("INSERT INTO bewertung (teilaufgabe_id, zeitpunkt, ergebnis, quelle) VALUES (1, '2026-10-01 10:00:00', 3, 'selbst')")
    db.setze_einstellung(con, "farbschema", "hell")
    con.close()
    # im Netz: schon gelernt, eine alte Bilddatei
    con = db.verbinden(daten / "saku.db")
    con.execute("INSERT INTO bewertung (teilaufgabe_id, zeitpunkt, ergebnis, quelle) VALUES (2, '2026-10-20 08:00:00', 1, 'selbst')")
    con.commit()
    con.close()
    (daten / "aufgaben" / "alt.png").write_bytes(b"alt")

    archiv = tmp_path / "paket.tar.gz"
    namen = _paket_von(zuhause, archiv)
    antwort = _hochladen(client, archiv.read_bytes())
    assert antwort.status_code == 200, antwort.get_data(as_text=True)
    assert "1 Einträge dazu" in antwort.get_data(as_text=True)

    con = db.verbinden(daten / "saku.db")
    assert con.execute("SELECT COUNT(*) FROM pruefung WHERE bereich = 'Neu aus der Pipeline'").fetchone()[0] == 1
    assert {tuple(z) for z in con.execute("SELECT teilaufgabe_id, zeitpunkt FROM bewertung")} == {
        (1, "2026-10-01 10:00:00"), (2, "2026-10-20 08:00:00")}  # von zu Hause und von hier
    assert db.einstellung(con, "farbschema") == "hell"  # Einstellungen aus dem Paket
    con.close()
    assert not (daten / "aufgaben" / "alt.png").exists()
    assert all((daten / n).is_file() for n in namen if n.startswith("aufgaben/"))
    assert list((daten / "backups").glob("saku-*.db"))  # vorher gesichert
    assert client.get("/").headers["Location"] == "/willkommen"  # angemeldet; die Einführung war zu Hause noch nicht gesehen
    assert "Paket übernehmen" in client.get("/einstellungen").get_data(as_text=True)


def test_jedes_paket_sichert_vorher_eigens(server, tmp_path):
    """Was ein Paket nicht übernimmt (Sensei-Gespräche von hier), steckt nur in der Sicherung davor; ein zweites Paket am
    selben Tag darf sie nicht überschreiben. Die tägliche Sicherung bleibt dabei, wie sie war."""
    client, daten = server
    db.sichern(daten / "saku.db")  # die tägliche, am Morgen
    taeglich = next((daten / "backups").glob("saku-????-??-??.db")).read_bytes()
    con = db.verbinden(daten / "saku.db")
    con.execute("INSERT INTO sensei_nachricht (gespraech, rolle, inhalt) VALUES ('handy', 'user', 'Frage vom Handy')")
    con.commit()
    con.close()
    zuhause = tmp_path / "zuhause"
    anlegen(zuhause)
    archiv = tmp_path / "paket.tar.gz"
    paket.bauen(archiv, zuhause)
    for _ in range(2):
        assert _hochladen(client, archiv.read_bytes()).status_code == 200

    def frage_vom_handy(datei):
        con = sqlite3.connect(datei)
        try:
            return con.execute("SELECT COUNT(*) FROM sensei_nachricht WHERE gespraech = 'handy'").fetchone()[0]
        finally:
            con.close()

    assert not frage_vom_handy(daten / "saku.db")
    sicherungen = sorted((daten / "backups").glob("*.db"))
    assert any(map(frage_vom_handy, sicherungen)), [s.name for s in sicherungen]
    assert next((daten / "backups").glob("saku-????-??-??.db")).read_bytes() == taeglich


def test_datenbank_herunterladen(server):
    client, daten = server
    antwort = client.get("/einstellungen/saku.db")
    assert antwort.status_code == 200 and "attachment" in antwort.headers["Content-Disposition"]
    kopie = daten.parent / "kopie.db"
    kopie.write_bytes(antwort.data)
    con = sqlite3.connect(kopie)
    assert con.execute("SELECT COUNT(*) FROM teilaufgabe").fetchone()[0] > 10
    con.close()
    assert [p.name for p in daten.iterdir() if p.suffix == ".db"] == ["saku.db"]  # die Kopie ist wieder weg


def test_lernstand_wandert_als_datei(server, tmp_path):
    """Vom Netz nach Hause: Lernstand exportieren (Einstellungen), lokal importieren."""
    client, daten = server
    con = db.verbinden(daten / "saku.db")
    con.execute("INSERT INTO bewertung (teilaufgabe_id, zeitpunkt, ergebnis, quelle) VALUES (3, '2026-10-21 09:00:00', 2, 'selbst')")
    con.commit()
    con.close()
    datei = json.loads(client.get("/einstellungen/lernstand.json").data)
    zuhause = tmp_path / "zuhause"
    anlegen(zuhause)
    from saku.lernen import lernstand
    con = db.verbinden(zuhause / "saku.db")
    assert lernstand.importieren(con, datei)["bewertungen"][0] == 1
    con.close()
