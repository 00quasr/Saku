"""Schritt 7: Lernpfad – Voraussetzungen (KI), Reihenfolge (networkx), Stationen und Einführungen.
Je Pfad (AP1, AP2-1201, AP2-1202) eigene Stationen; die Statistik rechnet dafür im jeweiligen Umfang."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import networkx as nx

from saku import config, db
from saku.pipeline import inventar
from saku.sensei import client, prompts

MIN_AUFGABEN, MAX_AUFGABEN = 8, 15

SYSTEM_VORAUSSETZUNG = """Du planst einen Lernpfad für eine IHK-Abschlussprüfung der IT-Berufe (Fachinformatiker/-in).
Nenne Voraussetzungen zwischen den Themen: „B setzt A voraus“, wenn man A verstehen muss,
um Aufgaben zu B zu lösen (z. B. SQL-Abfragen setzt das relationale Datenmodell voraus). Nur echte fachliche
Abhängigkeiten, höchstens drei je Thema, keine Ketten über Bereiche hinweg, wenn sie nicht zwingend sind."""
SCHEMA_VORAUSSETZUNG = {
    "type": "object",
    "properties": {"voraussetzungen": {"type": "array", "items": {
        "type": "object",
        "properties": {"thema_id": {"type": "integer"}, "voraussetzung_id": {"type": "integer"},
                       "begruendung": {"type": "string"}, "sicherheit": {"type": "number"}},
        "required": ["thema_id", "voraussetzung_id", "begruendung", "sicherheit"],
        "additionalProperties": False,
    }}},
    "required": ["voraussetzungen"],
    "additionalProperties": False,
}
SCHEMA_EINFUEHRUNG = {
    "type": "object",
    "properties": {"einfuehrung": {"type": "string", "description": "Markdown, höchstens 200 Wörter plus Aufgabentypen"}},
    "required": ["einfuehrung"],
    "additionalProperties": False,
}


def _themen(con: sqlite3.Connection) -> dict[int, sqlite3.Row]:
    """Themen der Ebene 2 mit Teilaufgaben, samt Punkten und Anzahl; nur aus den Bereichen des Lernpfads
    (die alte GA2 gilt für alle Berufe, ihre SI-Themen gehören trotzdem nicht in den AE-Pfad)."""
    pfad = con.execute("SELECT pfad FROM v_umfang").fetchone()[0]
    bereiche = inventar.BEREICHE_JE_PFAD.get(pfad) or [z[0] for z in con.execute("SELECT name FROM thema WHERE ebene = 1")]
    return {z["thema_id"]: z for z in con.execute(
        "SELECT s.thema_id, s.name, s.punkte, s.teilaufgaben, b.name AS bereich FROM v_themen_statistik s "
        f"JOIN thema b ON b.id = s.eltern_id WHERE s.ebene = 2 AND s.teilaufgaben > 0 "
        f"AND b.name IN ({','.join('?' * len(bereiche))})", bereiche)}


def voraussetzungen(con: sqlite3.Connection, themen: dict, ki: str) -> None:
    """Fragt die KI nach Voraussetzungen und ersetzt die bisherigen KI-Kanten (manuelle bleiben)."""
    liste = "\n".join(
        f"{t}: {th['bereich']} › {th['name']} ({', '.join(z[0] for z in con.execute('SELECT name FROM thema WHERE eltern_id = ? ORDER BY position', (t,)))})"
        for t, th in themen.items())
    antwort = client.strukturiert(con, "lernpfad", "stark", SYSTEM_VORAUSSETZUNG, f"Themen (id: Bereich › Thema (Unterthemen)):\n{liste}",
                                  SCHEMA_VORAUSSETZUNG, ki=ki, aufwand="medium", max_tokens=8000)
    con.execute(f"DELETE FROM thema_voraussetzung WHERE quelle = 'ki' AND thema_id IN ({','.join('?' * len(themen))})",
                list(themen))
    for v in antwort["voraussetzungen"]:
        if v["thema_id"] in themen and v["voraussetzung_id"] in themen and v["thema_id"] != v["voraussetzung_id"]:
            con.execute("INSERT OR IGNORE INTO thema_voraussetzung (thema_id, voraussetzung_id, quelle, begruendung) "
                        "VALUES (?, ?, 'ki', ?)", (v["thema_id"], v["voraussetzung_id"], v["begruendung"]))
    con.commit()


def reihenfolge(knoten: dict[int, float], kanten: list[tuple[int, int]]) -> list[int]:
    """Topologisch (Voraussetzung zuerst); bei freier Wahl das Thema mit den meisten Punkten.
    knoten: {id: punkte}, kanten: (thema, voraussetzung). Zyklen verlieren die zuletzt genannte Kante."""
    g = nx.DiGraph()
    g.add_nodes_from(knoten)
    g.add_edges_from((v, t) for t, v in kanten if t in knoten and v in knoten)
    while not nx.is_directed_acyclic_graph(g):
        g.remove_edge(*nx.find_cycle(g)[-1][:2])
    return list(nx.lexicographical_topological_sort(g, key=lambda n: (-knoten[n], n)))


def buendeln(einheiten: list[tuple[list[int], int]]) -> list[list[int]]:
    """Einheiten (Themen, Anzahl Teilaufgaben) zu Stationen mit möglichst 8 bis 15 Teilaufgaben."""
    stationen, aktuell, anzahl = [], [], 0
    for themen, n in einheiten:
        if aktuell and anzahl + n > MAX_AUFGABEN and anzahl >= MIN_AUFGABEN // 2:
            stationen.append(aktuell)
            aktuell, anzahl = [], 0
        aktuell, anzahl = aktuell + themen, anzahl + n
        if anzahl >= MIN_AUFGABEN:
            stationen.append(aktuell)
            aktuell, anzahl = [], 0
    if aktuell:
        stationen.append(aktuell)
    return stationen


def _einheiten(con: sqlite3.Connection, folge: list[int], themen: dict) -> list[tuple[list[int], int]]:
    """Große Themen (über 15 Teilaufgaben) werden in ihre Unterthemen zerlegt."""
    einheiten = []
    for t in folge:
        if themen[t]["teilaufgaben"] <= MAX_AUFGABEN:
            einheiten.append(([t], themen[t]["teilaufgaben"]))
            continue
        einheiten += [([k["thema_id"]], k["teilaufgaben"]) for k in con.execute(
            "SELECT thema_id, teilaufgaben FROM v_themen_statistik WHERE eltern_id = ? AND teilaufgaben > 0 "
            "ORDER BY punkte DESC", (t,))]
    return einheiten


def _titel(con: sqlite3.Connection, ids: list[int]) -> str:
    namen = [con.execute("SELECT name FROM thema WHERE id = ?", (i,)).fetchone()[0] for i in ids]
    return " · ".join(namen[:2]) + (" …" if len(namen) > 2 else "")


def _einfuehrung(daten: Path, ids: list[int], ki: str) -> str | None:
    con = db.verbinden(config.db_pfad(daten))  # je Thread eine Verbindung
    try:
        kontext = "\n".join(k for i in ids if (k := prompts.thema_kontext(con, i)))
        antwort = client.strukturiert(con, "einfuehrung", "stark", prompts.SYSTEM,
                                      f"{kontext}\n\n{prompts.ANWEISUNG['thema']}", SCHEMA_EINFUEHRUNG,
                                      ki=ki, aufwand="medium", max_tokens=4000)
        return antwort["einfuehrung"]
    except client.KiFehler as fehler:
        print(f"  Einführung: {fehler}", flush=True)
        return None
    finally:
        con.close()


def ausfuehren(con: sqlite3.Connection, daten: Path, ohne_ki: bool, ki: str) -> None:
    if not ohne_ki and ki == "api" and not client.verfuegbar():
        print("  Kein API-Schlüssel: Lernpfad ohne KI-Voraussetzungen und Einführungen", flush=True)
        ohne_ki = True
    for pfad, beruf, teil in db.pfade(con):
        with db.umfang(con, beruf, teil):
            _pfad(con, daten, pfad, ohne_ki, ki)


def _pfad(con: sqlite3.Connection, daten: Path, pfad: str, ohne_ki: bool, ki: str) -> None:
    if con.execute("SELECT 1 FROM station WHERE quelle = 'manuell' AND pfad = ?", (pfad,)).fetchone():
        print(f"  {pfad}: Stationen wurden von Hand angepasst, der Lernpfad bleibt unverändert", flush=True)
        return
    themen = _themen(con)
    if not themen:
        return
    if not ohne_ki:
        voraussetzungen(con, themen, ki)
    kanten = [(z[0], z[1]) for z in con.execute("SELECT thema_id, voraussetzung_id FROM thema_voraussetzung")]
    folge = reihenfolge({t: th["punkte"] for t, th in themen.items()}, kanten)
    neu = buendeln(_einheiten(con, folge, themen))

    alt = [sorted(z[0] for z in con.execute("SELECT thema_id FROM station_thema WHERE station_id = ?", (s[0],)))
           for s in con.execute("SELECT id FROM station WHERE pfad = ? ORDER BY position", (pfad,))]
    if alt != [sorted(s) for s in neu]:
        # Neue Gliederung: Stationen neu anlegen, Einführung und Mini-Tests gleicher Themen bleiben erhalten
        bisher = {}
        for s in con.execute("SELECT id, einfuehrung FROM station WHERE pfad = ?", (pfad,)).fetchall():
            themen_s = frozenset(z[0] for z in con.execute("SELECT thema_id FROM station_thema WHERE station_id = ?", (s[0],)))
            tests = con.execute("SELECT gestartet_am, beendet_am, punkte_erreicht, punkte_moeglich, bestanden "
                                "FROM stationstest WHERE station_id = ?", (s[0],)).fetchall()
            bisher[themen_s] = (s[1], [tuple(t) for t in tests])
        con.execute("DELETE FROM station WHERE pfad = ?", (pfad,))
        for pos, ids in enumerate(neu, start=1):
            einfuehrung, tests = bisher.get(frozenset(ids), (None, []))
            s_id = con.execute("INSERT INTO station (pfad, position, titel, einfuehrung) VALUES (?, ?, ?, ?)",
                               (pfad, pos, _titel(con, ids), einfuehrung)).lastrowid
            con.executemany("INSERT INTO station_thema (station_id, thema_id) VALUES (?, ?)", [(s_id, i) for i in ids])
            con.executemany("INSERT INTO stationstest (station_id, gestartet_am, beendet_am, punkte_erreicht, punkte_moeglich, "
                            "bestanden) VALUES (?, ?, ?, ?, ?, ?)", [(s_id, *t) for t in tests])
        con.commit()

    if not ohne_ki:
        offen = [(s[0], [z[0] for z in con.execute("SELECT thema_id FROM station_thema WHERE station_id = ?", (s[0],))])
                 for s in con.execute("SELECT id FROM station WHERE einfuehrung IS NULL AND pfad = ? ORDER BY position", (pfad,))]
        with ThreadPoolExecutor(4) as pool:
            texte = pool.map(lambda s: _einfuehrung(daten, s[1], ki), offen)
            for (s_id, _), text in zip(offen, texte):
                if text:
                    con.execute("UPDATE station SET einfuehrung = ? WHERE id = ?", (text, s_id))
                    con.commit()
    print(f"  {pfad}: {len(neu)} Stationen, {len(kanten)} Voraussetzungen", flush=True)
