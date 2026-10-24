"""SQLite-Verbindung, Schema und Einstellungen."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from saku import config


def verbinden(pfad: Path | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(pfad or config.db_pfad())
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


# Kleine Änderungen an bestehenden Datenbanken: Version → Befehle (neue Datenbanken bekommen gleich schema.sql)
MIGRATIONEN = {
    3: ["ALTER TABLE bewertung ADD COLUMN punkte REAL"],
    4: [
        "CREATE TABLE vektor (art TEXT NOT NULL, id INTEGER NOT NULL, daten BLOB NOT NULL, PRIMARY KEY (art, id))",
        "CREATE TABLE muster (id INTEGER PRIMARY KEY, name TEXT NOT NULL)",
        "CREATE TABLE luecke (id INTEGER PRIMARY KEY, teilaufgabe_id INTEGER NOT NULL REFERENCES teilaufgabe(id) ON DELETE CASCADE, "
        "text TEXT NOT NULL, operator TEXT, zeitpunkt TEXT NOT NULL DEFAULT (datetime('now')))",
        "CREATE TABLE begriff_karte (begriff_id INTEGER PRIMARY KEY REFERENCES begriff(id) ON DELETE CASCADE, "
        "status TEXT NOT NULL DEFAULT 'neu' CHECK (status IN ('neu', 'rot', 'gelb', 'gruen')), serie INTEGER NOT NULL DEFAULT 0, "
        "fsrs TEXT, faellig_am TEXT, geaendert_am TEXT)",
        "ALTER TABLE teilaufgabe ADD COLUMN muster_id INTEGER REFERENCES muster(id) ON DELETE SET NULL",
    ],
}


def init(pfad: Path | None = None) -> bool:
    """Legt die Datenbank an, falls sie noch kein Schema hat, sonst bringt sie sie auf den neuesten Stand.
    True, wenn neu angelegt."""
    pfad = Path(pfad or config.db_pfad())
    pfad.parent.mkdir(parents=True, exist_ok=True)
    con = verbinden(pfad)
    try:
        version = con.execute("PRAGMA user_version").fetchone()[0]
        if not version:
            con.executescript(config.SCHEMA.read_text(encoding="utf-8"))
            return True
        for ziel, befehle in sorted(MIGRATIONEN.items()):
            if version < ziel:
                for befehl in befehle:
                    con.execute(befehl)
                con.execute(f"PRAGMA user_version = {ziel}")
                con.commit()
        return False
    finally:
        con.close()


def sichern(pfad: Path | None = None, erzwingen: bool = False, behalten: int = 7) -> Path | None:
    """Sicherung nach backups/saku-JJJJ-MM-TT.db neben der Datenbank, über die Backup-API von SQLite (sicher bei WAL).
    Eine je Tag (erzwingen überschreibt die von heute), die letzten `behalten` bleiben. None, wenn nichts zu tun war."""
    pfad = Path(pfad or config.db_pfad())
    ordner = pfad.parent / "backups"
    ziel = ordner / f"saku-{date.today().isoformat()}.db"
    if not pfad.exists() or (ziel.exists() and not erzwingen):
        return None
    ordner.mkdir(exist_ok=True)
    teil = ziel.with_suffix(".teil")  # erst fertig schreiben, dann umbenennen: nie eine halbe Sicherung
    teil.unlink(missing_ok=True)
    quelle, kopie = sqlite3.connect(pfad), sqlite3.connect(teil)
    try:
        quelle.backup(kopie)
    finally:
        kopie.close()
        quelle.close()
    teil.replace(ziel)
    for alt in sorted(ordner.glob("saku-????-??-??.db"))[:-behalten]:
        alt.unlink()
    return ziel


def taeglich_sichern(pfad: Path | None = None) -> None:
    """Beim Start und vor der Analyse; eine fehlgeschlagene Sicherung hält beides nicht auf."""
    try:
        sichern(pfad)
    except Exception:  # bewusst breit: ohne Sicherung weiterarbeiten ist besser als gar nicht
        logging.getLogger(__name__).exception("Sicherung der Datenbank fehlgeschlagen")


def letzte_sicherung(pfad: Path | None = None) -> Path | None:
    sicherungen = sorted((Path(pfad or config.db_pfad()).parent / "backups").glob("saku-????-??-??.db"))
    return sicherungen[-1] if sicherungen else None


def einstellung(con: sqlite3.Connection, schluessel: str, standard: str = "") -> str:
    zeile = con.execute("SELECT wert FROM einstellung WHERE schluessel = ?", (schluessel,)).fetchone()
    return zeile["wert"] if zeile else standard


def setze_einstellung(con: sqlite3.Connection, schluessel: str, wert: str) -> None:
    con.execute(
        "INSERT INTO einstellung (schluessel, wert) VALUES (?, ?) "
        "ON CONFLICT (schluessel) DO UPDATE SET wert = excluded.wert",
        (schluessel, wert),
    )
    con.commit()


@contextmanager
def umfang(con: sqlite3.Connection, beruf: str, teil: str):
    """Rechnet die Sichten (v_teilaufgabe …) vorübergehend für einen anderen Beruf und Prüfungsteil."""
    alt = einstellung(con, "beruf", "1201"), einstellung(con, "teil", "AP2")
    setze_einstellung(con, "beruf", beruf)
    setze_einstellung(con, "teil", teil)
    try:
        yield
    finally:
        setze_einstellung(con, "beruf", alt[0])
        setze_einstellung(con, "teil", alt[1])


def pfade(con: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """(Pfad, Beruf, Teil) für alles, was im Katalog steht: AP1, AP2-1201, AP2-1202."""
    teile = {(z[0], z[1]) for z in con.execute("SELECT DISTINCT teil, beruf FROM pruefung")}
    ergebnis = [("AP1", "1201", "AP1")] if any(t == "AP1" for t, _ in teile) else []
    return ergebnis + [(f"AP2-{b}", b, "AP2") for b in ("1201", "1202") if any(t in ("AP2", "AP") and r == b for t, r in teile)]


def liste(wert: str | None) -> list:
    """JSON-Liste aus einer TEXT-Spalte (z. B. Bildpfade)."""
    return json.loads(wert) if wert else []
