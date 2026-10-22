"""Schritt 4: Aufgaben neu aufbauen. Claude liest die Ausschnitte einer Aufgabe und schreibt sie als Markdown,
dazu die Antwortart (für anklickbare Aufgaben), den Lösungshinweis und die Fachbegriffe.
Abbildungen schneidet Saku aus dem Ausschnitt, bei Text-PDFs als SVG. Wiederaufnehmbar: nur Aufgaben ohne Inhalt."""

import json
import os
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pymupdf

from saku import config, db
from saku.pipeline import inventar, themen
from saku.sensei import client

ARTEN = ["frei", "einfach", "mehrfach", "reihenfolge", "zuordnung", "zahl", "code", "sql", "tabelle"]
_WAHL = {"type": "array", "items": {"type": "object", "properties": {"wert": {"type": "string"}, "text": {"type": "string"}},
                                    "required": ["wert", "text"], "additionalProperties": False}}
_ANTWORT = {"type": "object", "properties": {
    "art": {"type": "string", "enum": ARTEN}, "optionen": _WAHL, "ziele": _WAHL,
    "richtig": {"type": "array", "items": {"type": "string"}}, "einheit": {"type": "string"}, "vorlage": {"type": "string"}},
    "required": ["art", "optionen", "ziele", "richtig", "einheit", "vorlage"], "additionalProperties": False}
_TEIL = {"type": "object", "properties": {
    "kennung": {"type": "string"}, "inhalt": {"type": "string"}, "antwort": _ANTWORT, "loesung": {"type": "string"},
    "begriffe": {"type": "array", "items": {"type": "string"}}},
    "required": ["kennung", "inhalt", "antwort", "loesung", "begriffe"], "additionalProperties": False}
SCHEMA = {"type": "object", "properties": {
    "ausgangssituation": {"type": "string"},
    "aufgaben": {"type": "array", "items": {"type": "object", "properties": {
        "nummer": {"type": "integer"}, "einleitung": {"type": "string"}, "teilaufgaben": {"type": "array", "items": _TEIL}},
        "required": ["nummer", "einleitung", "teilaufgaben"], "additionalProperties": False}},
    "abbildungen": {"type": "array", "items": {"type": "object", "properties": {
        "nr": {"type": "integer"}, "bild": {"type": "string"}, "beschreibung": {"type": "string"},
        "box": {"type": "array", "items": {"type": "number"}}},
        "required": ["nr", "bild", "beschreibung", "box"], "additionalProperties": False}}},
    "required": ["ausgangssituation", "aufgaben", "abbildungen"], "additionalProperties": False}

SYSTEM = """Du baust Aufgaben aus IHK-Prüfungen der IT-Berufe für eine Lern-App neu auf. Du bekommst Bildausschnitte
(Scans, Fotos oder Seiten aus PDFs) und den erkannten Text dazu, der verrauscht sein kann. Maßgeblich sind die Bilder.

Regeln:
- inhalt: die Aufgabenstellung vollständig und wortgetreu als Markdown. Absätze, Aufzählungen, Tabellen als
  Markdown-Tabelle, Code, Pseudocode und SQL in ```-Blöcken mit Sprache. Die Kennung („a)“) nicht wiederholen.
- Weglassen: Punkteangaben („6 Punkte“), Antwortlinien, leere Kästchen, Korrekturrand, „Fortsetzung …“,
  Seitenzahlen, Kopf- und Fußzeilen (z. B. „ZPA FIA I 3“).
- Die App zeigt Auswahlmöglichkeiten und auszufüllende Tabellen selbst an: Was in optionen, ziele oder vorlage steht,
  kommt nicht noch einmal in den inhalt, ebenso wenig Anweisungen wie „Tragen Sie die Ziffer … in das Kästchen ein“.
- Abbildungen (Diagramme, Screenshots, Mockups, Netz- und Klassendiagramme, Grafiken), die sich nicht als Text oder
  Tabelle wiedergeben lassen: im Markdown an der richtigen Stelle ![kurze Beschreibung](abb:N) und in „abbildungen“
  mit nr N, bild (Name des Bildes, z. B. „3a-1“) und box [x0, y0, x1, y1] relativ zum Bild (0 bis 1), so dass die
  Abbildung ganz drin ist. Gilt genauso für Lösungshinweise, Einleitung und Ausgangssituation.
- antwort.art: einfach (genau eine Ziffer oder Option), mehrfach (mehrere), reihenfolge (Ziffern in eine Reihenfolge
  bringen), zuordnung (Aussagen Kategorien zuordnen), zahl (ein Zahlenwert), code, sql, tabelle (Tabelle ausfüllen),
  frei (Text). optionen: die Auswahlmöglichkeiten (wert = Ziffer oder Buchstabe, text). ziele: nur bei zuordnung die
  Kategorien. vorlage: bei tabelle die auszufüllende Tabelle als Markdown mit leeren Zellen, bei code ein vorgegebenes
  Gerüst, sonst leer. einheit: bei zahl die Einheit (z. B. „€“, „ms“), sonst leer.
- richtig: nur aus dem Lösungshinweis, nie raten. einfach/mehrfach: die richtigen Werte; reihenfolge: die Werte in
  richtiger Reihenfolge; zuordnung: „Wert=Ziel“, z. B. „a=2“; zahl: der Wert mit Punkt als Dezimaltrenner. Ohne
  Lösungshinweis eine leere Liste.
- loesung: der Lösungshinweis wortgetreu und übersichtlich als Markdown; leer, wenn keiner mitgeschickt wurde.
- begriffe: 3 bis 8 zentrale Fachbegriffe der Teilaufgabe in Grundform (z. B. „Fremdschlüssel“, „Subnetzmaske“),
  keine Allerweltswörter.
- einleitung: die Situation vor den Teilaufgaben als Markdown; ausgangssituation nur, wenn Bilder Z… dabei sind,
  sonst leer.
- Antworte für jede genannte Aufgabe und Teilaufgabe genau einmal, mit derselben Nummer und Kennung."""

GROESSE = 8  # Teilaufgaben je Aufruf (WiSo hat viele kleine Aufgaben)


def _bilder(wert: str) -> list[str]:
    return db.liste(wert)


def _teil(text: str | None, laenge: int = 1200) -> str:
    return re.sub(r"\s+", " ", text or "")[:laenge]


def auftrag(con: sqlite3.Connection, aufgaben: list[sqlite3.Row], daten: Path, mit_ausgang: bool) -> tuple[str, list]:
    """Text und (Name, Pfad) der Bilder für einen Aufruf."""
    p = con.execute("SELECT * FROM pruefung WHERE id = ?", (aufgaben[0]["pruefung_id"],)).fetchone()
    bilder, zeilen = [], [f"## Prüfung: {p['saison']} {p['jahr']} · {p['bereich']}"]

    def namen(praefix: str, pfade: list[str]) -> str:
        neu = [(f"{praefix}-{i}", daten / b) for i, b in enumerate(pfade, start=1)]
        bilder.extend(neu)
        return ", ".join(n for n, _ in neu) or "keine"

    if mit_ausgang:
        zeilen.append(f"Ausgangssituation – Bilder {namen('Z', _bilder(p['ausgangssituation_bilder']))}; "
                      f"erkannter Text: {_teil(p['ausgangssituation'], 1500)}")
    for a in aufgaben:
        zeilen.append(f"\n### Aufgabe {a['nummer']}\nEinleitung – Bilder {namen(f'E{a['nummer']}', _bilder(a['einleitung_bilder']))}; "
                      f"erkannter Text: {_teil(a['einleitung'])}")
        for t in con.execute("SELECT * FROM teilaufgabe WHERE aufgabe_id = ? ORDER BY position", (a["id"],)):
            k = f"{a['nummer']}{t['kennung']}"
            zeilen.append(f"Teilaufgabe {t['kennung']} ({t['punkte'] or '?'} Punkte) – Bilder {namen(k, _bilder(t['bilder']))}; "
                          f"erkannter Text: {_teil(t['text'])}")
            if t["loesung_text"] or t["loesung_bilder"] != "[]":
                zeilen.append(f"Lösungshinweis zu {t['kennung']} – Bilder {namen('L' + k, _bilder(t['loesung_bilder']))}; "
                              f"erkannter Text: {_teil(t['loesung_text'], 800)}")
    return "\n".join(zeilen), [(n, pfad) for n, pfad in bilder if pfad.exists()]


def _pdf(con: sqlite3.Connection, daten: Path, bild: Path) -> Path | None:
    """Das Text-PDF, aus dem ein Ausschnitt stammt (Ordner = Anfang des SHA-256); None bei Scans."""
    dok = con.execute("SELECT dateiname FROM dokument WHERE sha256 LIKE ? AND hat_textebene = 1",
                      (bild.parent.name + "%",)).fetchone()
    return daten / "pdfs" / dok[0] if dok else None


def abbildung(con: sqlite3.Connection, daten: Path, bild: Path, box: list[float], ziel: str) -> str | None:
    """Schneidet die Box (relativ, 0–1) aus dem Ausschnitt: aus Text-PDFs als SVG, sonst als PNG.
    Gibt den Pfad relativ zum Datenordner zurück, None bei unbrauchbarer Box."""
    if len(box) != 4:
        return None
    x0, y0, x1, y1 = (min(1.0, max(0.0, float(v))) for v in box)
    if x1 - x0 < 0.05 or y1 - y0 < 0.03:
        return None
    lage = bild.parent / "ausschnitte.json"
    rechteck = json.loads(lage.read_text()).get(bild.name) if lage.exists() else None
    if rechteck and (pdf := _pdf(con, daten, bild)) and pdf.exists():
        nr, rx0, ry0, rx1, ry1 = rechteck
        breite, hoehe = rx1 - rx0, ry1 - ry0
        with pymupdf.open(pdf) as doc:
            seite = doc[nr]
            seite.set_cropbox(pymupdf.Rect(rx0 + x0 * breite, ry0 + y0 * hoehe, rx0 + x1 * breite, ry0 + y1 * hoehe)
                              & seite.mediabox)
            svg = seite.get_svg_image(text_as_path=True)  # Schrift als Pfad: sieht aus wie im Original
        pfad = bild.parent / f"{ziel}.svg"
        pfad.write_text(svg, encoding="utf-8")
        return str(pfad.relative_to(daten))
    pix = pymupdf.Pixmap(str(bild))
    werte = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    teil = np.ascontiguousarray(werte[int(y0 * pix.height):int(y1 * pix.height), int(x0 * pix.width):int(x1 * pix.width)])
    pfad = bild.parent / f"{ziel}.png"
    pymupdf.Pixmap(pix.colorspace, teil.shape[1], teil.shape[0], teil.tobytes(), pix.alpha).save(pfad)
    return str(pfad.relative_to(daten))


def _ohne_bilder(markdown: str) -> str:
    """Klartext für Suche und Klassifikation: Abbildungen werden zu ihrer Beschreibung."""
    return re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", markdown).strip()


def speichern(con: sqlite3.Connection, daten: Path, aufgaben: list[sqlite3.Row], bilder: list, antwort: dict) -> int:
    """Schreibt Inhalt, Antwortart, Lösung und Begriffe; gibt die Zahl der aufgebauten Teilaufgaben zurück."""
    pfade = dict(bilder)
    urls = {}
    for abb in antwort["abbildungen"]:
        quelle = pfade.get(abb["bild"])
        if quelle is None:
            continue
        stamm = f"{quelle.stem}-abb{abb['nr']}"
        rel = abbildung(con, daten, quelle, abb["box"], stamm) or str(quelle.relative_to(daten))
        urls[abb["nr"]] = f"/bild/{rel}"

    def einsetzen(markdown: str) -> str:
        # abb:N → Bild-URL; unbekannte Nummern fallen samt Bild weg, die Beschreibung bleibt als Text
        return re.sub(r"!\[([^\]]*)\]\(abb:(\d+)\)",
                      lambda m: f"![{m.group(1)}]({urls[int(m.group(2))]})" if int(m.group(2)) in urls else m.group(1),
                      markdown or "").strip()

    if antwort["ausgangssituation"].strip():
        con.execute("UPDATE pruefung SET ausgangssituation_inhalt = ? WHERE id = ?",
                    (einsetzen(antwort["ausgangssituation"]), aufgaben[0]["pruefung_id"]))
    nach_nummer = {a["nummer"]: a for a in aufgaben}
    anzahl = 0
    for a_neu in antwort["aufgaben"]:
        a = nach_nummer.get(a_neu["nummer"])
        if a is None:
            continue
        con.execute("UPDATE aufgabe SET einleitung_inhalt = ? WHERE id = ?", (einsetzen(a_neu["einleitung"]) or None, a["id"]))
        teile = {z["kennung"]: z["id"] for z in con.execute("SELECT id, kennung FROM teilaufgabe WHERE aufgabe_id = ?", (a["id"],))}
        for t in a_neu["teilaufgaben"]:
            t_id = teile.get(t["kennung"].strip().rstrip(")").lower())
            if t_id is None or not t["inhalt"].strip():
                continue
            inhalt = einsetzen(t["inhalt"])
            con.execute("UPDATE teilaufgabe SET inhalt = ?, antwort = ?, loesung_inhalt = ?, text = ? WHERE id = ?",
                        (inhalt, json.dumps(t["antwort"], ensure_ascii=False), einsetzen(t["loesung"]) or None,
                         _ohne_bilder(inhalt), t_id))
            con.execute("DELETE FROM teilaufgabe_begriff WHERE teilaufgabe_id = ?", (t_id,))
            # gleiche Begriffe in anderer Schreibweise nur einmal, die erste Schreibweise zählt
            namen = {}
            for b in (b.strip() for b in t["begriffe"]):
                if 2 < len(b) <= 60:
                    namen.setdefault(b.casefold(), b)
            for name in namen.values():
                b_id = begriff_id(con, name)
                con.execute("INSERT OR IGNORE INTO teilaufgabe_begriff (teilaufgabe_id, begriff_id) VALUES (?, ?)", (t_id, b_id))
            anzahl += 1
    return anzahl


def begriff_id(con: sqlite3.Connection, name: str) -> int:
    """Begriff anlegen oder finden. Gleicher Slug bei anderem Namen („Client-Server“, „Client Server“): durchnummerieren."""
    basis = themen.slug(name) or "begriff"
    for nr in range(1, 50):
        try:
            return con.execute("INSERT INTO begriff (name, slug) VALUES (?, ?) ON CONFLICT (name) DO UPDATE SET name = name "
                               "RETURNING id", (name, basis if nr == 1 else f"{basis}-{nr}")).fetchone()[0]
        except sqlite3.IntegrityError:  # Slug vergeben, nächste Nummer
            continue
    raise ValueError(f"Kein freier Slug für „{name}“")


def pakete(aufgaben: list[sqlite3.Row], teile: dict[int, int]) -> list[list[sqlite3.Row]]:
    """Aufgaben einer Prüfung bündeln, bis etwa GROESSE Teilaufgaben zusammen sind."""
    ergebnis, paket = [], []
    for a in aufgaben:
        if paket and (paket[-1]["pruefung_id"] != a["pruefung_id"] or sum(teile[x["id"]] for x in paket) >= GROESSE):
            ergebnis.append(paket)
            paket = []
        paket.append(a)
    return ergebnis + [paket] * bool(paket)


def ausfuehren(con: sqlite3.Connection, daten: Path, ohne_ki: bool, ki: str) -> None:
    if ohne_ki or ki == "api" and not client.verfuegbar():
        print("  ohne KI: Aufgaben bleiben Ausschnitte", flush=True)
        return
    # aktuelle AP2 zuerst, dann AP1, WiSo und das frühere Format
    aufgaben = con.execute(f"""
        SELECT a.*, p.teil, p.bereich, (p.ausgangssituation_inhalt IS NULL AND p.ausgangssituation_bilder <> '[]') AS ausgang_offen
        FROM aufgabe a JOIN pruefung p ON p.id = a.pruefung_id
        WHERE EXISTS (SELECT 1 FROM teilaufgabe t WHERE t.aufgabe_id = a.id AND t.inhalt IS NULL)
        ORDER BY p.format = 'frueher', p.bereich = '{inventar.WISO}', p.teil = 'AP1', p.jahr DESC, p.saison, p.id, a.nummer
    """).fetchall()
    teile = {a["id"]: con.execute("SELECT COUNT(*) FROM teilaufgabe WHERE aufgabe_id = ?", (a["id"],)).fetchone()[0]
             for a in aufgaben}
    liste = pakete(aufgaben, teile)
    ausgang = {a["pruefung_id"] for a in aufgaben if a["ausgang_offen"]}

    def bearbeiten(paket: list[sqlite3.Row]) -> int:
        eigene = db.verbinden(config.db_pfad(daten))  # je Thread eine Verbindung
        try:
            mit_ausgang = paket[0]["pruefung_id"] in ausgang and paket[0]["nummer"] == min(
                a["nummer"] for a in aufgaben if a["pruefung_id"] == paket[0]["pruefung_id"])
            text, bilder = auftrag(eigene, paket, daten, mit_ausgang)
            antwort = client.strukturiert(eigene, "aufbereiten", "stark", SYSTEM, text, SCHEMA, ki=ki,
                                          aufwand="medium", max_tokens=16000, bilder=bilder)
            anzahl = speichern(eigene, daten, paket, bilder, antwort)
            eigene.commit()
            return anzahl
        except (client.KiFehler, sqlite3.Error, ValueError, KeyError, TypeError) as fehler:
            # ein kaputtes Paket hält den Lauf nicht auf; es bleibt offen und kommt beim nächsten Lauf wieder dran
            eigene.rollback()
            print(f"\n  Aufgabe {paket[0]['id']}: {type(fehler).__name__}: {fehler}", flush=True)
            return 0
        finally:
            eigene.close()

    fertig = gesamt = 0
    # shortcut: feste Parallelität; über SAKU_KI_PARALLEL anpassen, wenn der Rechner mehr verträgt
    with ThreadPoolExecutor(int(os.getenv("SAKU_KI_PARALLEL", 3 if ki == "claude-code" else 6))) as pool:
        for anzahl in pool.map(bearbeiten, liste):
            fertig += 1
            gesamt += anzahl
            print(f"  {fertig}/{len(liste)} Pakete, {gesamt} Teilaufgaben neu aufgebaut", end="\r", flush=True)
    print(f"  {fertig} Pakete, {gesamt} Teilaufgaben neu aufgebaut{' ' * 20}", flush=True)
