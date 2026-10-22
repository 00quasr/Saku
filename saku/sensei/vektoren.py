"""Lokale Vektoren mit fastembed (mehrsprachiges MiniLM, ONNX, offline und kostenlos).

Für Suche nach Bedeutung (⌘K, Sensei-Chat), „Kam so ähnlich dran“ und Aufgabenmuster. Fehlt das Modell oder
die Bibliothek, liefern die Funktionen nichts und Saku fällt auf die Volltextsuche zurück.
"""

import re
import sqlite3

import numpy as np

from saku import config

MODELL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_modell = None
_cache: dict[tuple, tuple[list[int], np.ndarray]] = {}


def modell():
    """Das Modell (einmal geladen, ca. 220 MB in data/modelle); None, wenn es nicht verfügbar ist."""
    global _modell
    if _modell is None:
        try:
            from fastembed import TextEmbedding
            _modell = TextEmbedding(MODELL, cache_dir=str(config.DATEN / "modelle"))
        except (ImportError, OSError, ValueError, RuntimeError):
            _modell = False
    return _modell or None


def klartext(markdown: str | None) -> str:
    """Markdown und Bildverweise weg, Leerraum zusammen: das Modell soll Inhalt sehen, keine Zeichen."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", markdown or "")
    text = re.sub(r"(\*\*|__|`+|^#+\s*|\|)", " ", text, flags=re.M)
    return re.sub(r"\s+", " ", text).strip()


def einbetten(texte: list[str]) -> np.ndarray | None:
    """(n, 384), Zeilen auf Länge 1 normiert; Skalarprodukt = Kosinus-Ähnlichkeit."""
    m = modell()
    if m is None or not texte:
        return None
    matrix = np.array(list(m.embed(texte, batch_size=64)), dtype=np.float32)
    return matrix / np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-9)


def speichern(con: sqlite3.Connection, art: str, ids: list[int], matrix: np.ndarray) -> None:
    con.execute("DELETE FROM vektor WHERE art = ?", (art,))
    con.executemany("INSERT INTO vektor (art, id, daten) VALUES (?, ?, ?)",
                    [(art, i, zeile.astype(np.float32).tobytes()) for i, zeile in zip(ids, matrix)])
    con.commit()
    _cache.clear()


def laden(con: sqlite3.Connection, art: str) -> tuple[list[int], np.ndarray]:
    """Alle Vektoren einer Art; zwischengespeichert, bis sich die Anzahl ändert."""
    anzahl = con.execute("SELECT COUNT(*) FROM vektor WHERE art = ?", (art,)).fetchone()[0]
    schluessel = (str(config.db_pfad()), art, anzahl)
    if schluessel not in _cache:
        zeilen = con.execute("SELECT id, daten FROM vektor WHERE art = ? ORDER BY id", (art,)).fetchall()
        matrix = np.frombuffer(b"".join(z[1] for z in zeilen), dtype=np.float32).reshape(len(zeilen), -1) \
            if zeilen else np.zeros((0, 0), dtype=np.float32)
        _cache[schluessel] = ([z[0] for z in zeilen], matrix)
    return _cache[schluessel]


def suchen(con: sqlite3.Connection, art: str, anfrage: str, n: int = 20, erlaubt: set[int] | None = None,
           schwelle: float = 0.3) -> list[tuple[int, float]]:
    """Die n ähnlichsten (id, Ähnlichkeit) zur Anfrage, optional nur unter `erlaubt` (z. B. dem Umfang)."""
    ids, matrix = laden(con, art)
    if not ids or not anfrage.strip():
        return []
    frage = einbetten([anfrage])
    if frage is None:
        return []
    werte = matrix @ frage[0]
    reihenfolge = np.argsort(-werte)
    treffer = [(ids[i], float(werte[i])) for i in reihenfolge if werte[i] >= schwelle and (erlaubt is None or ids[i] in erlaubt)]
    return treffer[:n]


def verschmelzen(*listen: list[int], k: int = 60) -> list[int]:
    """Reciprocal Rank Fusion: mehrere Trefferlisten (beste zuerst) zu einer; was in beiden vorn liegt, gewinnt."""
    punkte: dict[int, float] = {}
    for liste in listen:
        for rang, i in enumerate(liste):
            punkte[i] = punkte.get(i, 0) + 1 / (k + rang + 1)
    return sorted(punkte, key=lambda i: -punkte[i])
