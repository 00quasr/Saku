"""Pipeline: aus Prüfungs-PDFs wird der Katalog (siehe docs/ARCHITEKTUR.md)."""

import importlib
from pathlib import Path

from saku import config, db

SCHRITTE = ["inventar", "segmente", "loesungen", "aufbereiten", "sandbox", "themen", "klassifikation", "statistik", "wissen", "vektoren", "lernpfad", "bericht"]


def ausfuehren(schritt: str | None = None, ohne_ki: bool = False, ki: str = "api", daten: Path | None = None) -> None:
    """Alle Schritte nacheinander oder nur `schritt`; jeder Schritt ist wiederholbar."""
    if schritt and schritt not in SCHRITTE:
        raise SystemExit(f"Unbekannter Schritt „{schritt}“. Möglich: {', '.join(SCHRITTE)}")
    daten = daten or config.DATEN
    db.init(config.db_pfad(daten))
    con = db.verbinden(config.db_pfad(daten))
    try:
        for name in [schritt] if schritt else SCHRITTE:
            print(f"· {name}", flush=True)
            importlib.import_module(f"saku.pipeline.{name}").ausfuehren(con, daten, ohne_ki, ki)
    finally:
        con.close()
