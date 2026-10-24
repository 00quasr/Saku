"""Migrationen: eine Datenbank mit Version 4 (Schema vom Stand main, tests/daten/schema_v4.sql) mit Lernstand wird auf den
neuesten Stand gebracht und muss danach genauso aussehen wie eine neue Datenbank aus db/schema.sql."""

import sqlite3
from pathlib import Path

import pytest

from saku import db

SCHEMA_V4 = Path(__file__).parent / "daten" / "schema_v4.sql"


def _struktur(pfad: Path) -> dict:
    """Tabellen mit Spalten und Fremdschlüsseln, Indizes und Sichten (Whitespace egal), dazu die Version."""
    con = sqlite3.connect(pfad)
    try:
        struktur = {"version": con.execute("PRAGMA user_version").fetchone()[0]}
        for art, name, sql in con.execute("SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"):
            if art == "table":
                struktur[name] = (art, con.execute(f'PRAGMA table_xinfo("{name}")').fetchall(),
                                  con.execute(f'PRAGMA foreign_key_list("{name}")').fetchall())
            else:
                struktur[name] = (art, " ".join((sql or "").split()))
        return struktur
    finally:
        con.close()


def _v4_mit_lernstand(pfad: Path) -> None:
    con = sqlite3.connect(pfad)
    con.executescript(SCHEMA_V4.read_text(encoding="utf-8"))
    con.executescript("""
        INSERT INTO pruefung (id, jahr, saison, bereich) VALUES (1, 2023, 'Sommer', 'Erfundener Bereich');
        INSERT INTO aufgabe (id, pruefung_id, nummer) VALUES (1, 1, 1);
        INSERT INTO teilaufgabe (id, aufgabe_id, kennung, position, punkte) VALUES (1, 1, 'a', 0, 4);
        INSERT INTO karte (teilaufgabe_id, status, serie) VALUES (1, 'gelb', 1);
        INSERT INTO bewertung (teilaufgabe_id, zeitpunkt, ergebnis) VALUES (1, '2026-10-01 10:00:00', 3);
        UPDATE einstellung SET wert = '2027-02-24' WHERE schluessel = 'pruefungstermin_ap1';
    """)
    con.close()


def test_v4_migriert_wie_neue_datenbank(tmp_path):
    alt, neu = tmp_path / "alt.db", tmp_path / "neu.db"
    _v4_mit_lernstand(alt)
    assert _struktur(alt)["version"] == 4
    assert db.init(alt) is False and db.init(neu) is True
    assert _struktur(alt) == _struktur(neu)

    db.init(alt)  # ein zweiter Start ändert nichts
    con = sqlite3.connect(alt)
    assert con.execute("SELECT status, serie FROM karte").fetchall() == [("gelb", 1)]
    assert con.execute("SELECT tag, bewertungen FROM v_lerntage").fetchall() == [("2026-10-01", 1)]
    assert con.execute("SELECT wert FROM einstellung WHERE schluessel = 'pruefungstermin_ap1'").fetchone()[0] == "2027-02-24"
    con.close()


def test_abgebrochene_migration_laesst_sich_wiederholen(tmp_path, monkeypatch):
    """Bricht eine Migration mittendrin ab (Absturz, voller Datenträger), darf nichts halb angelegt bleiben, sonst
    scheitert jeder weitere Start an „table already exists“."""
    pfad = tmp_path / "alt.db"
    _v4_mit_lernstand(pfad)
    monkeypatch.setitem(db.MIGRATIONEN, 5, [*db.MIGRATIONEN[5], "SELECT * FROM gibt_es_nicht"])
    with pytest.raises(sqlite3.OperationalError):
        db.init(pfad)
    monkeypatch.undo()
    db.init(pfad)
    assert _struktur(pfad)["version"] == 10


def test_init_befehl_sichert_vor_der_migration(tmp_path, monkeypatch):
    """Wer nach einem Update `python -m saku init` aufruft (so steht es im README), migriert; vorher muss es eine Sicherung geben
    wie bei start, analyse und lernstand import."""
    from saku import __main__, config
    monkeypatch.setattr(config, "DATEN", tmp_path)
    _v4_mit_lernstand(config.db_pfad(tmp_path))
    monkeypatch.setattr("sys.argv", ["saku", "init"])
    __main__.main()
    sicherung = db.letzte_sicherung(config.db_pfad(tmp_path))
    assert sicherung and _struktur(sicherung)["version"] == 4 and _struktur(config.db_pfad(tmp_path))["version"] == 10
