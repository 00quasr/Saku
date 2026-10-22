"""Schritt 5: jede Teilaufgabe Themen zuordnen – je Aufgabe ein KI-Aufruf, ohne KI über Stichworte.

Zuordnungen mit quelle='manuell' (Korrektur in Bunseki) überschreibt die Pipeline nie.
"""

import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from saku import config, db
from saku.pipeline import inventar
from saku.sensei import client

TYPEN = ["erklaeren", "berechnen", "zeichnen", "code", "sql", "tabelle", "auswahl", "sonstiges"]
SCHEMA = {
    "type": "object",
    "properties": {
        "teilaufgaben": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kennung": {"type": "string", "description": "z. B. T123"},
                    "themen": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"thema_id": {"type": "integer"}, "gewicht": {"type": "number"}},
                            "required": ["thema_id", "gewicht"],
                            "additionalProperties": False,
                        },
                    },
                    "typ": {"type": "string", "enum": TYPEN},
                    "sicherheit": {"type": "number"},
                },
                "required": ["kennung", "themen", "typ", "sicherheit"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["teilaufgaben"],
    "additionalProperties": False,
}

SYSTEM = """Du ordnest Teilaufgaben aus IHK-Abschlussprüfungen der IT-Berufe (Fachinformatiker/-in Anwendungsentwicklung
und Systemintegration, Teil 1 und Teil 2) den Themen der folgenden Themenliste zu. Die Texte stammen teils aus einer Texterkennung und können verrauscht sein.

Regeln:
- Gib für jede Teilaufgabe 1 bis 3 passende Unterthemen (thema_id aus der Liste) mit Gewichten an, die zusammen 1 ergeben.
  Das Hauptthema bekommt das größte Gewicht.
- typ: erklaeren (beschreiben, erläutern, nennen), berechnen, zeichnen (Diagramme, Modelle), code (Pseudocode,
  Programmieren), sql, tabelle (Tabelle ausfüllen), auswahl (Ankreuzen, Ziffer eintragen), sonstiges.
- sicherheit: 0 bis 1, wie sicher die Zuordnung ist.
- Antworte für jede genannte Kennung (z. B. T123) genau einmal.

Themenliste (thema_id: Bereich › Thema › Unterthema – Stichworte):
"""


def bereiche_fuer(teil: str, beruf: str, bereich: str) -> list[str]:
    """Welche Bereiche der Themenliste zu einer Prüfung passen (kleinerer Prompt, genauere Treffer)."""
    ae, si = [inventar.PLANEN, inventar.ENTWICKLUNG], [inventar.KONZEPTION, inventar.NETZWERKE]
    if teil == "AP1":
        return [inventar.ARBEITSPLATZ]
    if bereich == inventar.WISO:
        return [inventar.WISO]
    if beruf == "IT":  # GA2: gemeinsam für alle IT-Berufe
        return ae + si
    return si if beruf == "1202" else ae


def _unterthemen(con: sqlite3.Connection, bereiche: list[str]) -> list[sqlite3.Row]:
    sql = ("SELECT u.id, u.name, u.stichworte, t.name AS thema, b.name AS bereich FROM thema u "
           "JOIN thema t ON t.id = u.eltern_id JOIN thema b ON b.id = t.eltern_id WHERE u.ebene = 3 ")
    zeilen = con.execute(sql + f"AND b.name IN ({','.join('?' * len(bereiche))}) ORDER BY b.position, t.position, u.position",
                         bereiche).fetchall()
    # Steht der Bereich (noch) nicht in der Themenliste, gilt die ganze Liste
    return zeilen or con.execute(sql + "ORDER BY b.position, t.position, u.position").fetchall()


def themenliste(con: sqlite3.Connection, bereiche: list[str]) -> str:
    return "\n".join(
        f"{z['id']}: {z['bereich']} › {z['thema']} › {z['name']}" + (f" – {z['stichworte']}" if z["stichworte"] else "")
        for z in _unterthemen(con, bereiche))


def _aufgabentext(a: sqlite3.Row, teile: list[sqlite3.Row]) -> str:
    kopf = f"## {a['termin']} · {a['bereich']} · Aufgabe {a['nummer']}\nEinleitung: {(a['einleitung'] or '')[:1500]}\n"
    return kopf + "\n".join(
        f"\n[T{t['id']}] Teilaufgabe {t['kennung']} ({t['punkte'] or '?'} Punkte)\nAufgabe: {(t['text'] or '')[:1500]}\n"
        f"Lösungshinweis: {(t['loesung_text'] or '–')[:800]}" for t in teile)


def pakete(aufgaben: list[sqlite3.Row], offen: dict[int, list], groesse: int = 12) -> list[list[sqlite3.Row]]:
    """Aufgaben einer Prüfung gebündelt, bis etwa `groesse` Teilaufgaben zusammen sind (spart Aufrufe)."""
    ergebnis, paket = [], []
    for a in aufgaben:
        if paket and (paket[-1]["pruefung_id"] != a["pruefung_id"] or sum(len(offen[x["id"]]) for x in paket) >= groesse):
            ergebnis.append(paket)
            paket = []
        if offen[a["id"]]:
            paket.append(a)
    return ergebnis + [paket] * bool(paket)


def regeln(themen: list[sqlite3.Row], text: str) -> list[tuple[int, float]]:
    """Ohne KI: Unterthemen nach Treffern ihrer Stichworte, höchstens zwei, Gewichte nach Treffern."""
    text = text.lower()
    treffer = []
    for th in themen:
        woerter = [w.strip().lower() for w in f"{th['name']},{th['stichworte'] or ''}".split(",") if len(w.strip()) > 2]
        anzahl = sum(len(re.findall(r"\b" + re.escape(w), text)) for w in woerter)
        if anzahl:
            treffer.append((anzahl, th["id"]))
    beste = sorted(treffer, reverse=True)[:2]
    summe = sum(n for n, _ in beste)
    return [(t_id, n / summe) for n, t_id in beste]


def _speichern(con: sqlite3.Connection, t_id: int, themen: list[tuple[int, float]], quelle: str,
               sicherheit: float | None, typ: str | None) -> None:
    if not themen:
        return  # nichts Besseres gefunden: bisherige Zuordnung behalten
    con.execute("DELETE FROM teilaufgabe_thema WHERE teilaufgabe_id = ? AND quelle <> 'manuell'", (t_id,))
    summe = sum(g for _, g in themen) or 1
    for th_id, gewicht in themen:
        con.execute("INSERT OR IGNORE INTO teilaufgabe_thema (teilaufgabe_id, thema_id, gewicht, quelle, sicherheit) "
                    "VALUES (?, ?, ?, ?, ?)", (t_id, th_id, min(1, max(0.01, gewicht / summe)), quelle, sicherheit))
    if typ:
        con.execute("UPDATE teilaufgabe SET typ = ? WHERE id = ?", (typ, t_id))


def ausfuehren(con: sqlite3.Connection, daten: Path, ohne_ki: bool, ki: str) -> None:
    if not ohne_ki and ki == "api" and not client.verfuegbar():
        print("  Kein API-Schlüssel: Zuordnung über Stichworte (oder --ki claude-code)", flush=True)
        ohne_ki = True
    aufgaben = con.execute(
        "SELECT a.id, a.nummer, a.einleitung, a.pruefung_id, v.termin, v.bereich, v.teil, v.beruf FROM aufgabe a "
        "JOIN v_teilaufgabe_alle v ON v.aufgabe_id = a.id GROUP BY a.id ORDER BY a.id").fetchall()
    # Teilaufgaben mit manueller Zuordnung bleiben, wie sie sind
    offen = {a["id"]: con.execute(
        "SELECT id, kennung, text, punkte, loesung_text FROM teilaufgabe WHERE aufgabe_id = ? AND id NOT IN "
        "(SELECT teilaufgabe_id FROM teilaufgabe_thema WHERE quelle = 'manuell') ORDER BY position", (a["id"],)).fetchall()
        for a in aufgaben}

    if ohne_ki:
        for a in aufgaben:
            themen = _unterthemen(con, bereiche_fuer(a["teil"], a["beruf"], a["bereich"]))
            for t in offen[a["id"]]:
                if con.execute("SELECT 1 FROM teilaufgabe_thema WHERE teilaufgabe_id = ? AND quelle = 'ki'", (t["id"],)).fetchone():
                    continue  # eine KI-Zuordnung ist besser als jede Stichwort-Regel
                _speichern(con, t["id"], regeln(themen, f"{t['text']} {t['loesung_text'] or ''}"), "regel", 0.4, None)
        con.commit()
        print(f"  {sum(map(len, offen.values()))} Teilaufgaben über Stichworte zugeordnet", flush=True)
        return

    def fragen(paket: list[sqlite3.Row]) -> dict | None:
        eigene = db.verbinden(config.db_pfad(daten))  # je Thread eine Verbindung
        try:
            a = paket[0]  # ein Paket gehört immer zu einer Prüfung
            system = SYSTEM + themenliste(eigene, bereiche_fuer(a["teil"], a["beruf"], a["bereich"]))
            text = "\n\n".join(_aufgabentext(a, offen[a["id"]]) for a in paket)
            return client.strukturiert(eigene, "klassifikation", "schnell", system, text, SCHEMA, ki=ki)
        except client.KiFehler as fehler:
            print(f"  Paket ab Aufgabe {paket[0]['id']}: {fehler}", flush=True)
            return None
        finally:
            eigene.close()

    gueltig = {z[0] for z in con.execute("SELECT id FROM thema WHERE ebene = 3")}
    liste = pakete(aufgaben, offen)
    erkannt = fertig = 0
    with ThreadPoolExecutor(4 if ki == "claude-code" else 8) as pool:
        for antwort in pool.map(fragen, liste):
            fertig += 1
            for z in (antwort or {}).get("teilaufgaben", []):
                t_id = int(z["kennung"].lstrip("Tt[").rstrip("]")) if z["kennung"].lstrip("Tt[").rstrip("]").isdigit() else None
                themen_z = [(th["thema_id"], th["gewicht"]) for th in z["themen"] if th["thema_id"] in gueltig and th["gewicht"] > 0]
                if t_id and themen_z:
                    _speichern(con, t_id, themen_z, "ki", max(0, min(1, z["sicherheit"])), z["typ"])
                    erkannt += 1
            con.commit()
            print(f"  {fertig}/{len(liste)} Pakete, {erkannt} Teilaufgaben zugeordnet", end="\r", flush=True)
    print(f"  {fertig} Pakete, {erkannt} Teilaufgaben zugeordnet{' ' * 20}", flush=True)
