"""Schritt 8: Vektoren (lokal, fastembed) für Teilaufgaben, Begriffe und Themen; daraus „Kam so ähnlich dran“
nach Bedeutung und die Aufgabenmuster (gleichartige Teilaufgaben über alle Termine)."""

import sqlite3
from collections import Counter
from pathlib import Path

import numpy as np

from saku.sensei import vektoren

AEHNLICH_AB, ANZAHL = 0.62, 3
# Muster: Kosinus-Abstand höchstens 0,38 im Cluster; nur was in mindestens drei Prüfungen vorkommt, ist ein Muster
MUSTER_ABSTAND, MUSTER_PRUEFUNGEN = 0.38, 3


def _teilaufgaben(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT t.id, t.inhalt, t.text, a.pruefung_id, a.einleitung_inhalt FROM teilaufgabe t "
        "JOIN aufgabe a ON a.id = t.aufgabe_id ORDER BY t.id").fetchall()


def aehnlichkeiten(matrix: np.ndarray, pruefungen: list[int]) -> list[tuple[int, int, float]]:
    """(i, j, Wert): je Zeile die ähnlichsten aus anderen Prüfungen ab AEHNLICH_AB."""
    werte = matrix @ matrix.T
    paare = []
    for i, zeile in enumerate(werte):
        kandidaten = [(w, j) for j, w in enumerate(zeile) if pruefungen[j] != pruefungen[i] and w >= AEHNLICH_AB]
        paare += [(i, j, round(float(min(w, 1.0)), 3)) for w, j in sorted(kandidaten, reverse=True)[:ANZAHL]]
    return paare


def muster(matrix: np.ndarray, pruefungen: list[int]) -> list[list[int]]:
    """Gruppen gleichartiger Teilaufgaben (Indizes), die in mindestens MUSTER_PRUEFUNGEN Prüfungen vorkommen."""
    from sklearn.cluster import AgglomerativeClustering
    if len(matrix) < 2:
        return []
    marken = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="average",
                                     distance_threshold=MUSTER_ABSTAND).fit_predict(matrix)
    gruppen: dict[int, list[int]] = {}
    for i, marke in enumerate(marken):
        gruppen.setdefault(int(marke), []).append(i)
    return [g for g in gruppen.values() if len({pruefungen[i] for i in g}) >= MUSTER_PRUEFUNGEN]


def _muster_name(con: sqlite3.Connection, ids: list[int]) -> str:
    """Name aus den häufigsten Fachbegriffen der Gruppe (sonst das Thema)."""
    begriffe = Counter(z[0] for z in con.execute(
        f"SELECT b.name FROM teilaufgabe_begriff tb JOIN begriff b ON b.id = tb.begriff_id "
        f"WHERE tb.teilaufgabe_id IN ({','.join('?' * len(ids))})", ids))
    namen = [n for n, _ in begriffe.most_common(2)]
    if namen:
        return " · ".join(namen)
    thema = con.execute(f"SELECT th.name FROM teilaufgabe_thema tt JOIN thema th ON th.id = tt.thema_id "
                        f"WHERE tt.teilaufgabe_id IN ({','.join('?' * len(ids))}) GROUP BY th.id ORDER BY COUNT(*) DESC LIMIT 1",
                        ids).fetchone()
    return thema[0] if thema else "Muster"


def ausfuehren(con: sqlite3.Connection, daten: Path, ohne_ki: bool, ki: str) -> None:
    zeilen = _teilaufgaben(con)
    texte = [vektoren.klartext(f"{(z['einleitung_inhalt'] or '')[:300]} {z['inhalt'] or z['text']}") for z in zeilen]
    matrix = vektoren.einbetten(texte)
    if matrix is None:
        print("  fastembed fehlt: Suche und Ähnlichkeit bleiben bei Volltext und TF-IDF", flush=True)
        return
    ids, pruefungen = [z["id"] for z in zeilen], [z["pruefung_id"] for z in zeilen]
    vektoren.speichern(con, "teilaufgabe", ids, matrix)

    begriffe = con.execute("SELECT id, name, erklaerung FROM begriff ORDER BY id").fetchall()
    if begriffe:
        vektoren.speichern(con, "begriff", [b["id"] for b in begriffe],
                           vektoren.einbetten([f"{b['name']}: {vektoren.klartext(b['erklaerung'])[:300]}" for b in begriffe]))
    themen = con.execute("SELECT id, name, stichworte FROM thema WHERE ebene > 1 ORDER BY id").fetchall()
    if themen:
        vektoren.speichern(con, "thema", [t["id"] for t in themen],
                           vektoren.einbetten([f"{t['name']}: {t['stichworte'] or ''}" for t in themen]))

    paare = aehnlichkeiten(matrix, pruefungen)
    con.execute("DELETE FROM aehnlichkeit")
    con.executemany("INSERT INTO aehnlichkeit (teilaufgabe_id, aehnlich_id, wert) VALUES (?, ?, ?)",
                    [(ids[i], ids[j], w) for i, j, w in paare])

    gruppen = muster(matrix, pruefungen)
    con.execute("UPDATE teilaufgabe SET muster_id = NULL")
    con.execute("DELETE FROM muster")
    for g in gruppen:
        mitglieder = [ids[i] for i in g]
        m_id = con.execute("INSERT INTO muster (name) VALUES (?)", (_muster_name(con, mitglieder),)).lastrowid
        con.executemany("UPDATE teilaufgabe SET muster_id = ? WHERE id = ?", [(m_id, t) for t in mitglieder])
    con.commit()
    print(f"  {len(ids)} Teilaufgaben, {len(begriffe)} Begriffe, {len(themen)} Themen als Vektoren · "
          f"{len(paare)} Ähnlichkeiten · {len(gruppen)} Muster", flush=True)
