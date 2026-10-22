"""Schritt: Wissen. Kurze Definitionen der Fachbegriffe (Begriffs-Karten) und je Thema eine Wissensseite:
was man können muss, typische Prüfungsfragen mit [T123], Fallen. Wiederaufnehmbar: nur, was noch fehlt."""

import os
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from saku import config, db
from saku.sensei import client

BEGRIFFE_JE_PAKET, AUFGABEN_JE_UNTERTHEMA = 50, 8

SYSTEM_BEGRIFFE = """Du schreibst Lernkarten für Auszubildende (Fachinformatiker/-in, IHK-Abschlussprüfung).
Je Begriff 2 bis 3 Sätze Markdown: präzise Definition, wofür man es braucht, bei Bedarf ein kurzes Beispiel.
Keine Einleitung, kein „X ist ein Begriff, der …“. Das Thema in Klammern hilft nur beim Einordnen mehrdeutiger Begriffe."""

SCHEMA_BEGRIFFE = {
    "type": "object",
    "properties": {"begriffe": {"type": "array", "items": {
        "type": "object", "properties": {"id": {"type": "integer"}, "erklaerung": {"type": "string"}},
        "required": ["id", "erklaerung"], "additionalProperties": False}}},
    "required": ["begriffe"], "additionalProperties": False,
}

SYSTEM_THEMEN = """Du schreibst Wissensseiten für Auszubildende (Fachinformatiker/-in) zur Vorbereitung auf die IHK-Prüfung.
Grundlage sind echte Prüfungsaufgaben, jeweils mit [T123] gekennzeichnet.

Zum Thema eine Übersicht (6 bis 10 Zeilen Markdown): worum es geht, was in den Prüfungen immer wieder verlangt wird,
welche Unterthemen am meisten Punkte bringen.

Je Unterthema eine Notiz in Markdown mit genau diesen Abschnitten (### als Überschrift):
### Das musst du können
3 bis 6 Stichpunkte, konkret und prüfungsnah (Formeln, Fachbegriffe, Abläufe).
### So wird gefragt
2 bis 4 typische Fragestellungen, je mit Verweis auf die passende Aufgabe als [T123]. Nur Aufgaben aus der Liste.
### Fallen
1 bis 3 häufige Fehler oder Verwechslungen.

Unterthemen ohne Aufgaben bekommen die Notiz aus dem Lehrplanwissen, ohne Abschnitt „So wird gefragt“.
Erfinde keine Prüfungsinhalte und keine Aufgabennummern."""

SCHEMA_THEMEN = {
    "type": "object",
    "properties": {
        "thema": {"type": "string"},
        "unterthemen": {"type": "array", "items": {
            "type": "object", "properties": {"id": {"type": "integer"}, "notiz": {"type": "string"}},
            "required": ["id", "notiz"], "additionalProperties": False}},
    },
    "required": ["thema", "unterthemen"], "additionalProperties": False,
}


def aufraeumen(text: str, uebersicht: bool = False) -> str:
    """T123 ohne Klammern (im Fließtext häufig) → [T123], damit die Notiz verlinkt; die Übersicht ohne eigene Überschrift."""
    text = re.sub(r"(?<![\[\w])T(\d+)(?![\]\w])", r"[T\1]", text.strip())
    return re.sub(r"\A#+ [^\n]*\n+", "", text) if uebersicht else text


def begriffe_auftrag(begriffe: list[sqlite3.Row]) -> str:
    return "\n".join(f"{b['id']}: {b['name']}" + (f" ({b['thema']})" if b["thema"] else "") for b in begriffe)


def themen_auftrag(con: sqlite3.Connection, thema: sqlite3.Row) -> str:
    """Thema, Unterthemen und je Unterthema die punktstärksten Aufgaben (gekürzt, mit Lösungshinweis)."""
    teile = [f"Thema: {thema['name']}" + (f" (Stichworte: {thema['stichworte']})" if thema["stichworte"] else "")]
    for u in con.execute("SELECT id, name, stichworte FROM thema WHERE eltern_id = ? ORDER BY position", (thema["id"],)):
        teile.append(f"\n## Unterthema {u['id']}: {u['name']}" + (f" (Stichworte: {u['stichworte']})" if u["stichworte"] else ""))
        for a in con.execute(
                "SELECT t.id, v.termin, t.punkte, COALESCE(t.inhalt, t.text) AS text, COALESCE(t.loesung_inhalt, t.loesung_text) AS loesung "
                "FROM teilaufgabe_thema tt JOIN teilaufgabe t ON t.id = tt.teilaufgabe_id "
                "JOIN v_teilaufgabe_alle v ON v.teilaufgabe_id = t.id WHERE tt.thema_id = ? "
                "ORDER BY tt.gewicht DESC, v.termin_index DESC LIMIT ?", (u["id"], AUFGABEN_JE_UNTERTHEMA)):
            loesung = f"\n  Lösung: {' '.join((a['loesung'] or '').split())[:200]}" if a["loesung"] else ""
            teile.append(f"- [T{a['id']}] {a['termin']}, {a['punkte'] or '?'} P.: {' '.join((a['text'] or '').split())[:350]}{loesung}")
    return "\n".join(teile)


def ausfuehren(con: sqlite3.Connection, daten: Path, ohne_ki: bool, ki: str) -> None:
    if ohne_ki or ki == "api" and not client.verfuegbar():
        print("  ohne KI: keine Wissensseiten und Begriffs-Definitionen", flush=True)
        return
    begriffe = con.execute(
        "SELECT b.id, b.name, (SELECT th.name FROM teilaufgabe_begriff tb JOIN teilaufgabe_thema tt ON tt.teilaufgabe_id = tb.teilaufgabe_id "
        "JOIN thema th ON th.id = tt.thema_id WHERE tb.begriff_id = b.id GROUP BY th.id ORDER BY COUNT(*) DESC LIMIT 1) AS thema "
        "FROM begriff b WHERE b.erklaerung IS NULL OR b.erklaerung = '' ORDER BY b.id").fetchall()
    themen = con.execute("SELECT id, name, stichworte FROM thema WHERE ebene = 2 AND (beschreibung IS NULL OR beschreibung = '') "
                         "ORDER BY id").fetchall()
    pakete = [("begriffe", begriffe[i:i + BEGRIFFE_JE_PAKET]) for i in range(0, len(begriffe), BEGRIFFE_JE_PAKET)]
    pakete += [("thema", th) for th in themen]

    def bearbeiten(paket) -> int:
        art, inhalt = paket
        eigene = db.verbinden(config.db_pfad(daten))  # je Thread eine Verbindung
        try:
            if art == "begriffe":
                antwort = client.strukturiert(eigene, "wissen", "schnell", SYSTEM_BEGRIFFE, begriffe_auftrag(inhalt),
                                              SCHEMA_BEGRIFFE, ki=ki, max_tokens=12000)
                erlaubt = {b["id"] for b in inhalt}
                zeilen = [(b["erklaerung"].strip(), b["id"]) for b in antwort["begriffe"] if b["id"] in erlaubt and b["erklaerung"].strip()]
                eigene.executemany("UPDATE begriff SET erklaerung = ? WHERE id = ?", zeilen)
            else:
                antwort = client.strukturiert(eigene, "wissen", "stark", SYSTEM_THEMEN, themen_auftrag(eigene, inhalt),
                                              SCHEMA_THEMEN, ki=ki, max_tokens=16000)
                erlaubt = {z[0] for z in eigene.execute("SELECT id FROM thema WHERE eltern_id = ?", (inhalt["id"],))}
                zeilen = [(aufraeumen(u["notiz"]), u["id"]) for u in antwort["unterthemen"] if u["id"] in erlaubt and u["notiz"].strip()]
                eigene.executemany("UPDATE thema SET beschreibung = ? WHERE id = ?",
                                   zeilen + [(aufraeumen(antwort["thema"], uebersicht=True), inhalt["id"])])
            eigene.commit()
            return len(zeilen)
        except (client.KiFehler, sqlite3.Error, KeyError, TypeError) as fehler:
            eigene.rollback()  # das Paket bleibt offen und kommt beim nächsten Lauf wieder dran
            print(f"\n  {art}: {type(fehler).__name__}: {fehler}", flush=True)
            return 0
        finally:
            eigene.close()

    fertig = gesamt = 0
    with ThreadPoolExecutor(int(os.getenv("SAKU_KI_PARALLEL", 3 if ki == "claude-code" else 6))) as pool:
        for anzahl in pool.map(bearbeiten, pakete):
            fertig += 1
            gesamt += anzahl
            print(f"  {fertig}/{len(pakete)} Pakete, {gesamt} Notizen", end="\r", flush=True)
    print(f"  {len(begriffe)} Begriffe und {len(themen)} Themen offen · {gesamt} Notizen geschrieben{' ' * 20}", flush=True)
