"""Einstellungen aus .env und feste Pfade."""

import os
from pathlib import Path

from dotenv import load_dotenv

WURZEL = Path(__file__).resolve().parent.parent
load_dotenv(WURZEL / ".env")

DATEN = (WURZEL / os.getenv("SAKU_DATENORDNER", "data")).resolve()
SCHEMA = WURZEL / "db" / "schema.sql"
PORT = int(os.getenv("SAKU_PORT", "5050"))

API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODELLE = {
    "schnell": os.getenv("SAKU_MODELL_SCHNELL", "claude-haiku-5-5"),
    "stark": os.getenv("SAKU_MODELL_STARK", "claude-sonnet-5-5"),
}


def db_pfad(daten: Path | None = None) -> Path:
    return (daten or DATEN) / "saku.db"
