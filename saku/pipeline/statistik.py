"""Schritt 6: „Kam so ähnlich auch dran“ (TF-IDF) und der Suchindex (FTS5).

Häufigkeit, Punkte und Heatmap liegen als Sichten in der Datenbank, dafür muss nichts gespeichert werden.
"""

import sqlite3
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SCHWELLE = 0.3
ANZAHL = 3


def aehnlichkeiten(texte: list[str], pruefungen: list[int]) -> list[tuple[int, int, float]]:
    """(i, j, Wert): je Text die ähnlichsten aus anderen Prüfungen ab SCHWELLE."""
    if len(texte) < 2:
        return []
    matrix = cosine_similarity(TfidfVectorizer(sublinear_tf=True, min_df=1).fit_transform(texte))
    paare = []
    for i, zeile in enumerate(matrix):
        kandidaten = [(w, j) for j, w in enumerate(zeile) if pruefungen[j] != pruefungen[i] and w >= SCHWELLE]
        paare += [(i, j, round(float(min(w, 1.0)), 3)) for w, j in sorted(kandidaten, reverse=True)[:ANZAHL]]
    return paare


def ausfuehren(con: sqlite3.Connection, daten: Path, ohne_ki: bool, ki: str) -> None:
    zeilen = con.execute(
        "SELECT v.teilaufgabe_id, v.pruefung_id, v.termin, v.aufgabe_nr, v.kennung, a.einleitung, t.text, t.loesung_text "
        "FROM v_teilaufgabe_alle v JOIN teilaufgabe t ON t.id = v.teilaufgabe_id JOIN aufgabe a ON a.id = v.aufgabe_id "
        "ORDER BY v.teilaufgabe_id").fetchall()

    con.execute("DELETE FROM aehnlichkeit")
    paare = aehnlichkeiten([f"{z['einleitung'] or ''} {z['text']}" for z in zeilen], [z["pruefung_id"] for z in zeilen])
    con.executemany("INSERT INTO aehnlichkeit (teilaufgabe_id, aehnlich_id, wert) VALUES (?, ?, ?)",
                    [(zeilen[i]["teilaufgabe_id"], zeilen[j]["teilaufgabe_id"], w) for i, j, w in paare])

    con.execute("DELETE FROM suche")
    con.executemany("INSERT INTO suche (teilaufgabe_id, titel, text, loesung) VALUES (?, ?, ?, ?)", [
        (z["teilaufgabe_id"], f"{z['termin']} · Aufgabe {z['aufgabe_nr']} {z['kennung']}",
         f"{z['einleitung'] or ''}\n{z['text']}", z["loesung_text"] or "") for z in zeilen])
    con.commit()
    print(f"  {len(paare)} Ähnlichkeiten, {len(zeilen)} Teilaufgaben im Suchindex", flush=True)
