"""Niwa 庭: der Wissensgraph. Python liefert Knoten und Kanten, force-graph (d3-force auf Canvas) zeichnet im Browser.

Knoten im aktiven Umfang: Prüfungsbereiche, Themen, Unterthemen (auch nie geprüfte), Lernfelder und die
Fachbegriffe aus dem Schritt aufbereiten. Kanten: Gliederung, Lernfeld, Begriff → sein wichtigstes Thema und
Voraussetzungen. Begriffe untereinander verbindet nur die Notiz („kommt oft zusammen mit“), nicht der Graph.
"""

import json
import sqlite3
from collections import defaultdict

from saku.db import einstellung, setze_einstellung
from saku.pipeline import inventar

STUFEN = {  # Wachstumsstufe aus v_thema_lernstand → Kanji, Wort
    "samen": ("種", "Samen"),
    "keim": ("芽", "Keim"),
    "knospe": ("蕾", "Knospe"),
    "bluete": ("花", "Blüte"),
}
RANG = {stufe: i for i, stufe in enumerate(STUFEN)}

# shortcut: nur Begriffe, die mindestens zweimal drankamen, und davon die häufigsten; mehr macht den Graphen unlesbar
MAX_BEGRIFFE = 300
ART = {1: "bereich", 2: "thema", 3: "unterthema"}


def themen(con: sqlite3.Connection) -> list[sqlite3.Row]:
    """Themen der Ebene 2 im Umfang, die in den Prüfungen vorkamen, mit Lernstand (Liste unter dem Graphen)."""
    return con.execute(
        "SELECT * FROM v_thema_lernstand WHERE ebene = 2 AND punkte_gesamt > 0 ORDER BY punkte_gesamt DESC, name"
    ).fetchall()


def _im_umfang(con: sqlite3.Connection) -> list[sqlite3.Row]:
    bereiche = inventar.BEREICHE_JE_PFAD.get(con.execute("SELECT pfad FROM v_umfang").fetchone()[0], [])
    return con.execute(f"""
        SELECT th.id, th.name, th.ebene, th.eltern_id, l.punkte_gesamt, l.punkte_neu, l.beherrschung, l.stufe,
               s.teilaufgaben, s.termine
        FROM thema th
        JOIN v_thema_vorfahr v ON v.thema_id = th.id
        JOIN thema b ON b.id = v.vorfahr_id AND b.ebene = 1 AND b.name IN ({','.join('?' * len(bereiche))})
        JOIN v_thema_lernstand l ON l.thema_id = th.id
        JOIN v_themen_statistik s ON s.thema_id = th.id
        ORDER BY th.ebene, th.position""", bereiche).fetchall()


def graph(con: sqlite3.Connection) -> dict:
    """{knoten, kanten} für force-graph; ids mit Präfix: t (Thema), lf (Lernfeld), b (Begriff)."""
    knoten, kanten = [], []
    themen_ids = set()
    for t in _im_umfang(con):
        themen_ids.add(t["id"])
        knoten.append({"id": f"t{t['id']}", "name": t["name"], "art": ART[t["ebene"]], "wert": t["punkte_gesamt"] or 0,
                       "teilaufgaben": t["teilaufgaben"], "termine": t["termine"], "beherrschung": t["beherrschung"],
                       "geuebt": (t["punkte_neu"] or 0) < (t["punkte_gesamt"] or 0), "stufe": t["stufe"]})
        if t["eltern_id"]:
            kanten.append({"source": f"t{t['eltern_id']}", "target": f"t{t['id']}", "art": "teil"})

    lernfelder = set()
    for z in con.execute("SELECT tl.thema_id, lf.id, lf.nummer, lf.titel FROM thema_lernfeld tl "
                         "JOIN lernfeld lf ON lf.id = tl.lernfeld_id ORDER BY lf.id"):
        if z["thema_id"] not in themen_ids:
            continue
        if z["id"] not in lernfelder:
            lernfelder.add(z["id"])
            knoten.append({"id": f"lf{z['id']}", "name": f"LF{z['nummer']} {z['titel']}", "art": "lernfeld", "wert": 0})
        kanten.append({"source": f"lf{z['id']}", "target": f"t{z['thema_id']}", "art": "lernfeld"})

    for thema, voraussetzung in con.execute("SELECT thema_id, voraussetzung_id FROM thema_voraussetzung"):
        if thema in themen_ids and voraussetzung in themen_ids:
            kanten.append({"source": f"t{voraussetzung}", "target": f"t{thema}", "art": "voraussetzung"})

    umfang = "SELECT teilaufgabe_id FROM v_teilaufgabe"
    begriffe = {z["id"]: z for z in con.execute(
        f"SELECT b.id, b.name, COUNT(DISTINCT tb.teilaufgabe_id) AS n FROM begriff b "
        f"JOIN teilaufgabe_begriff tb ON tb.begriff_id = b.id WHERE tb.teilaufgabe_id IN ({umfang}) "
        f"GROUP BY b.id HAVING n >= 2 ORDER BY n DESC, b.name LIMIT {MAX_BEGRIFFE}")}
    knoten += [{"id": f"b{b['id']}", "name": b["name"], "art": "begriff", "wert": b["n"]} for b in begriffe.values()]
    # Begriff → das Thema, bei dem er am häufigsten vorkommt
    je_begriff = defaultdict(list)
    for b_id, t_id, n in con.execute(
            f"SELECT tb.begriff_id, tt.thema_id, COUNT(*) FROM teilaufgabe_begriff tb "
            f"JOIN teilaufgabe_thema tt ON tt.teilaufgabe_id = tb.teilaufgabe_id "
            f"WHERE tb.teilaufgabe_id IN ({umfang}) GROUP BY 1, 2 ORDER BY 3 DESC"):
        if b_id in begriffe and t_id in themen_ids and not je_begriff[b_id]:
            je_begriff[b_id].append(t_id)
            kanten.append({"source": f"t{t_id}", "target": f"b{b_id}", "art": "begriff"})
    return {"knoten": knoten, "kanten": kanten}


def aufgeblueht(con: sqlite3.Connection, daten: dict) -> list[str]:
    """Themen, die seit dem letzten Besuch eine Stufe aufgestiegen sind; merkt sich die neuen Stufen."""
    try:
        vorher = json.loads(einstellung(con, "niwa_stufen", "{}"))
    except json.JSONDecodeError:
        vorher = {}
    jetzt = {k["id"]: k["stufe"] for k in daten["knoten"] if k.get("stufe")}
    if jetzt != vorher:
        setze_einstellung(con, "niwa_stufen", json.dumps(vorher | jetzt))
    return [k for k, stufe in jetzt.items() if k in vorher and RANG[stufe] > RANG.get(vorher[k], 99)]


def lehrplan(con: sqlite3.Connection) -> list[dict]:
    """Lernfelder im Umfang mit ihren Themen und wie oft diese geprüft wurden (Statistik nur einmal rechnen)."""
    beruf = con.execute("SELECT beruf FROM v_umfang").fetchone()[0]
    themen = {t["id"]: t for t in _im_umfang(con)}
    zuordnung = defaultdict(list)
    for lf_id, t_id in con.execute("SELECT lernfeld_id, thema_id FROM thema_lernfeld"):
        if t_id in themen:
            t = themen[t_id]
            zuordnung[lf_id].append({"id": t_id, "name": t["name"], "teilaufgaben": t["teilaufgaben"], "termine": t["termine"]})
    felder = []
    for lf in con.execute("SELECT * FROM lernfeld WHERE beruf IN ('IT', ?) ORDER BY id", (beruf,)).fetchall():
        zeilen = sorted(zuordnung[lf["id"]], key=lambda z: (-z["teilaufgaben"], z["name"]))
        felder.append(dict(lf) | {"themen": zeilen, "teilaufgaben": sum(z["teilaufgaben"] for z in zeilen)})
    return felder
