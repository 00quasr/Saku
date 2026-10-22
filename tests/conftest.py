import pytest

from saku import db
from saku.web import create_app
from tests.demo_daten import anlegen


@pytest.fixture
def daten(tmp_path):
    """Datenordner mit Demo-Datenbank (erfundene Prüfungen)."""
    anlegen(tmp_path)
    con = db.verbinden(tmp_path / "saku.db")
    db.setze_einstellung(con, "einfuehrung", "gesehen")  # sonst leitet Heute auf die Einführung um
    con.close()
    return tmp_path


@pytest.fixture
def con(daten):
    verbindung = db.verbinden(daten / "saku.db")
    yield verbindung
    verbindung.close()


@pytest.fixture
def app(daten):
    app = create_app(daten)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()
