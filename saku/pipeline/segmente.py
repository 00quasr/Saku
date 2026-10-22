"""Schritt 2: Aufgaben und Teilaufgaben erkennen, Ausschnitte rendern.

Die Erkennung arbeitet auf Zeilen mit Koordinaten (pdf.seiten): Aufgabenköpfe „1. Aufgabe (28 Punkte)“,
Kennungen „a)“, „ca)“ am linken Rand, Punkte „4 Punkte“ rechtsbündig (in Lösungen direkt hinter der Kennung).
Dieselbe Erkennung zerlegt in Schritt 3 die Lösungshinweise.
"""

import json
import re
import sqlite3
from pathlib import Path

import numpy as np
import pymupdf

from saku.pipeline import inventar

AUFGABE = re.compile(r"^(?:\d\.\d\s+Aufgabe\s+(\d)|([1-9lI]\d?)\s*\.\s*(?:Aufgabe|Handlungsschritt)\b(?:\s*\((\d+)\s*Punkte?\))?)")
KENNUNG = re.compile(r"^([a-h][a-h]?)\s?[\)\]]\s*")
PUNKTE = re.compile(r"(\d{1,2}(?:,\d)?)\s*Punkte?\b")
KOPF_FUSS = re.compile(r"Korrekturrand|^ZPA\b|^Fortsetzung|^Seite \d|Kopfleiste|^\d{1,2}$")
START = re.compile(r"beziehen sich auf die folgende|^Ausgangssituation")
DPI = 200
KORREKTURRAND = 0.89  # rechts davon liegt der Korrekturrand (nur in Aufgabensätzen)
NACHLAUF = 36  # Punkte Luft unter der letzten Textzeile eines Ausschnitts


def _zahl(text: str) -> float:
    return float(text.replace(",", "."))


def _rauschen(text: str) -> bool:
    """OCR-Reste von Antwortlinien („ee...“, „———n“) und Karopapier („DR DR RR“, „ENEBEEESSEE“)."""
    buchstaben = sum(c.isalpha() for c in text)
    woerter = text.split()
    kurz = sum(len(w) <= 2 for w in woerter)
    return (buchstaben < 3 or buchstaben / len(text) < 0.45 or re.fullmatch(r"[\Wen1lI_]+", text) is not None
            or len(woerter) >= 3 and kurz / len(woerter) > 0.6 or re.fullmatch(r"[A-ZÄÖÜ]{12,}", text) is not None)


def zeilen(seiten: list[dict]) -> list[dict]:
    """Alle Inhaltszeilen in Lesereihenfolge, ohne Kopf, Fuß und Korrekturrand."""
    liste = []
    for nr, seite in enumerate(seiten):
        breite, hoehe = seite["breite"], seite["hoehe"]
        inhalt = [z for z in seite["zeilen"] if z[1] < hoehe * 0.95 and not KOPF_FUSS.search(z[4])]
        links = min((z[0] for z in inhalt if not _rauschen(z[4])), default=0)
        for x0, y0, x1, y1, text in sorted(inhalt, key=lambda z: (round(z[1] / 4), z[0])):
            liste.append({"seite": nr, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "text": text,
                          "links": x0 < min(links + 45, breite * 0.25), "rechts": x0 > breite * 0.6,
                          "rauschen": _rauschen(text)})
    return liste


def gliedern(seiten: list[dict]) -> dict:
    """{'ausgang': [Zeilen], 'aufgaben': [{nr, abschnitt, punkte, kopf: [Zeilen], teile: [{kennung, punkte, zeilen}]}]}

    Beginnt die Zählung nach mindestens drei Aufgaben wieder bei 1, folgt ein neuer Abschnitt
    (z. B. Lösungen beider Prüfungsteile in einem PDF)."""
    ergebnis = {"ausgang": [], "aufgaben": [], "zeilen": zeilen(seiten)}
    ziel = None  # Liste, in die die nächste Zeile gehört
    aufgabe = teil = None
    abschnitt = 0
    for z in ergebnis["zeilen"]:
        text = z["text"]
        if (kopf := AUFGABE.match(text)) and z["links"]:
            nr = int((kopf.group(1) or kopf.group(2)).replace("l", "1").replace("I", "1"))
            if nr == 1 and max((a["nr"] for a in ergebnis["aufgaben"] if a["abschnitt"] == abschnitt), default=0) >= 3:
                abschnitt += 1  # doppelte erste Seite (Aufgabe 1 noch einmal) ist kein neuer Abschnitt
            if not any(a["nr"] == nr and a["abschnitt"] == abschnitt for a in ergebnis["aufgaben"]):
                aufgabe = {"nr": nr, "abschnitt": abschnitt, "punkte": _zahl(kopf.group(3)) if kopf.group(3) else None,
                           "kopf": [z], "teile": []}
                ergebnis["aufgaben"].append(aufgabe)
                teil, ziel = None, aufgabe["kopf"]
                continue
        if aufgabe is None:
            if START.search(text):
                ziel = ergebnis["ausgang"]
            if ziel is not None:
                ziel.append(z)
            continue
        kennung = KENNUNG.match(text) if z["links"] else None
        if kennung and kennung.group(1)[0] == "a" and aufgabe["teile"] and aufgabe["teile"][-1]["kennung"][0] != "a":
            # „a)“ nach „c)“: der Kopf der nächsten Aufgabe fehlt (OCR hat ihn nicht gelesen)
            aufgabe = {"nr": aufgabe["nr"] + 1, "abschnitt": abschnitt, "punkte": None, "kopf": [], "teile": []}
            ergebnis["aufgaben"].append(aufgabe)
        if kennung and (not aufgabe["teile"] or kennung.group(1)[0] >= aufgabe["teile"][-1]["kennung"][0]) \
                and not any(t["kennung"] == kennung.group(1) for t in aufgabe["teile"]):
            punkte = PUNKTE.match(text[kennung.end():])  # Lösungen: „a) 4 Punkte“
            teil = {"kennung": kennung.group(1), "punkte": _zahl(punkte.group(1)) if punkte else None, "zeilen": [z]}
            aufgabe["teile"].append(teil)
            ziel = teil["zeilen"]
            continue
        if teil and z["rechts"] and teil["punkte"] is None and (punkte := PUNKTE.fullmatch(text.strip())):
            teil["punkte"] = _zahl(punkte.group(1))
        ziel.append(z)
    return ergebnis


def abschnitte(gliederung: dict) -> list[list[dict]]:
    """Die Abschnitte mit echten Teilaufgaben (Übersichtsseiten mit bloßen Aufgabenköpfen fallen weg)."""
    gruppen = {}
    for a in gliederung["aufgaben"]:
        gruppen.setdefault(a["abschnitt"], []).append(a)
    return [g for g in gruppen.values() if any(a["teile"] for a in g)]


def blaetter(aufgabe: dict) -> list[dict]:
    """Die lernbaren Teilaufgaben: Eltern wie „c)“ vor „ca)“, „cb)“ geben ihren Text an die Kinder weiter.
    Ohne Kennungen ist die ganze Aufgabe eine Teilaufgabe „a“ (z. B. WiSo)."""
    teile = aufgabe["teile"]
    if not teile:
        return [{"kennung": "a", "punkte": aufgabe["punkte"], "zeilen": aufgabe["kopf"][1:] or aufgabe["kopf"], "eltern": []}]
    ergebnis = []
    for t in teile:
        if any(a["kennung"] != t["kennung"] and a["kennung"].startswith(t["kennung"]) for a in teile):
            continue
        eltern = [e for e in teile if e["kennung"] != t["kennung"] and t["kennung"].startswith(e["kennung"])]
        ergebnis.append(t | {"eltern": eltern})
    return ergebnis


def text(zeilen: list[dict]) -> str:
    return "\n".join(z["text"] for z in zeilen if not z["rauschen"])


def bereiche(zeilen: list[dict], seiten: list[dict], alle: list[dict] = ()) -> list[tuple[int, float, float]]:
    """(Seite, y0, y1) je Seite, auf der die Zeilen liegen; unten bis kurz nach der letzten Textzeile,
    aber nie in die nächste fremde Zeile aus `alle` hinein."""
    eigene = {id(z) for z in zeilen}
    spannen = []
    for nr in sorted({z["seite"] for z in zeilen}):
        auf_seite = [z for z in zeilen if z["seite"] == nr]
        mit_text = [z for z in auf_seite if not z["rauschen"]] or auf_seite
        y0 = min(z["y0"] for z in auf_seite) - 4
        y1 = min(max(z["y1"] for z in mit_text) + NACHLAUF, seiten[nr]["hoehe"] * 0.95)
        unten = max(z["y0"] for z in auf_seite)
        danach = [z["y0"] for z in alle if z["seite"] == nr and z["y0"] > unten and id(z) not in eigene and not z["rauschen"]]
        if danach:
            y1 = min(y1, min(danach) - 2)
        spannen.append((nr, max(0, y0), y1))
    return spannen


def aufhellen(pix: pymupdf.Pixmap) -> pymupdf.Pixmap:
    """Graues Papier (Fotos, Scans) auf Weiß ziehen, damit Ausschnitte mit dem Farbschema verschmelzen."""
    grau = pymupdf.Pixmap(pymupdf.csGRAY, pix) if pix.n != 1 else pix
    werte = np.frombuffer(grau.samples, dtype=np.uint8).reshape(grau.height, grau.width)
    papier, tinte = np.percentile(werte, 90), np.percentile(werte, 1)
    if papier >= 245 or papier - tinte < 40:
        return pix
    gestreckt = np.clip((werte.astype(np.float32) - tinte) * 255 / (papier - tinte), 0, 255).astype(np.uint8)
    return pymupdf.Pixmap(pymupdf.csGRAY, grau.width, grau.height, gestreckt.tobytes(), 0)


def rendern(doc: pymupdf.Document, seiten: list[dict], zeilen: list[dict], daten: Path, ordner: Path, name: str,
            alle: list[dict] = (), rechts: float = KORREKTURRAND) -> list[str]:
    """Rendert die Zeilen als PNG-Ausschnitte (einer je Seite) und gibt die Pfade relativ zum Datenordner zurück.
    Seite und Rechteck jedes Ausschnitts stehen in ausschnitte.json: daraus schneidet aufbereiten Abbildungen als SVG."""
    pfade = []
    ordner.mkdir(parents=True, exist_ok=True)
    lage = ordner / "ausschnitte.json"
    rechtecke = json.loads(lage.read_text()) if lage.exists() else {}
    for i, (nr, y0, y1) in enumerate(bereiche(zeilen, seiten, alle), start=1):
        auf_seite = [z for z in zeilen if z["seite"] == nr]
        links = min((z["x0"] for z in auf_seite), default=0)
        # schräge Fotos reichen weiter nach rechts: dann bis zur breitesten Zeile, nie bis zum Seitenrand
        breite = seiten[nr]["breite"]
        rand = min(max([breite * rechts] + [z["x1"] + 6 for z in auf_seite if not z["rauschen"]]), breite * 0.98)
        rechteck = pymupdf.Rect(max(0, links - 14), y0, rand, y1) & doc[nr].rect
        if rechteck.is_empty or rechteck.height < 8 or rechteck.width < 40:
            continue
        pfad = ordner / f"{name}-{i}.png"
        aufhellen(doc[nr].get_pixmap(clip=rechteck, dpi=DPI)).save(pfad)
        pfade.append(str(pfad.relative_to(daten)))
        rechtecke[pfad.name] = [nr, *map(lambda w: round(w, 2), rechteck)]
    lage.write_text(json.dumps(rechtecke))
    return pfade


def _speichern(con: sqlite3.Connection, daten: Path, dok: sqlite3.Row, seiten: list[dict], doc: pymupdf.Document) -> int:
    """Schreibt Ausgangssituation, Aufgaben und Teilaufgaben einer Prüfung; gibt die Zahl der Teilaufgaben zurück."""
    ordner = inventar.ordner(daten, dok["sha256"])
    gliederung = gliedern(seiten)
    p_id = dok["pruefung_id"]
    if gliederung["ausgang"]:
        con.execute("UPDATE pruefung SET ausgangssituation = ?, ausgangssituation_bilder = ? WHERE id = ?",
                    (text(gliederung["ausgang"]), json.dumps(rendern(doc, seiten, gliederung["ausgang"], daten, ordner, "A", gliederung["zeilen"])), p_id))
    anzahl = 0
    # Ein Aufgabensatz hat einen Abschnitt; sonst zählt der mit den meisten Teilaufgaben
    aufgaben = max(abschnitte(gliederung) or [gliederung["aufgaben"]], key=lambda g: sum(len(a["teile"]) for a in g))
    for a in aufgaben:
        teile = blaetter(a)
        kopf = a["kopf"] if a["teile"] else a["kopf"][:1]
        seiten_nr = [z["seite"] + 1 for z in kopf] + [z["seite"] + 1 for t in teile for z in t["zeilen"]]
        punkte = a["punkte"] or sum(t["punkte"] or 0 for t in teile) or None
        a_id = con.execute(
            """INSERT INTO aufgabe (pruefung_id, nummer, einleitung, einleitung_bilder, punkte, seite_von, seite_bis)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (pruefung_id, nummer) DO UPDATE SET einleitung = excluded.einleitung,
                 einleitung_bilder = excluded.einleitung_bilder, punkte = excluded.punkte,
                 seite_von = excluded.seite_von, seite_bis = excluded.seite_bis
               RETURNING id""",
            (p_id, a["nr"], text(kopf), json.dumps(rendern(doc, seiten, kopf, daten, ordner, f"E{a['nr']}", gliederung["zeilen"]) if a["teile"] else []),
             punkte, min(seiten_nr), max(seiten_nr))).fetchone()[0]
        for pos, t in enumerate(teile):
            zeilen_alle = [z for e in t["eltern"] for z in e["zeilen"]] + t["zeilen"]
            bilder = rendern(doc, seiten, zeilen_alle, daten, ordner, f"{a['nr']}{t['kennung']}", gliederung["zeilen"])
            con.execute(
                """INSERT INTO teilaufgabe (aufgabe_id, kennung, position, text, punkte, seite, bilder)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT (aufgabe_id, kennung) DO UPDATE SET position = excluded.position, text = excluded.text,
                     punkte = COALESCE(excluded.punkte, teilaufgabe.punkte), seite = excluded.seite, bilder = excluded.bilder""",
                (a_id, t["kennung"], pos, text(zeilen_alle), t["punkte"], t["zeilen"][0]["seite"] + 1, json.dumps(bilder)))
        # Reste eines früheren Laufs mit anderer Gliederung weg, solange daran noch nicht gelernt wurde
        kennungen = [t["kennung"] for t in teile]
        con.execute(f"DELETE FROM teilaufgabe WHERE aufgabe_id = ? AND kennung NOT IN ({','.join('?' * len(kennungen))}) "
                    "AND id NOT IN (SELECT teilaufgabe_id FROM bewertung) AND id NOT IN (SELECT teilaufgabe_id FROM karte) "
                    "AND id NOT IN (SELECT teilaufgabe_id FROM simulation_teilaufgabe) "
                    "AND id NOT IN (SELECT teilaufgabe_id FROM teilaufgabe_thema WHERE quelle = 'manuell')", (a_id, *kennungen))
        anzahl += len(teile)
    return anzahl


def wiso_punkte(con: sqlite3.Connection) -> None:
    """WiSo-Aufgaben nennen keine Punkte: 100 Punkte gleichmäßig auf die Teilaufgaben verteilt."""
    for (p_id,) in con.execute("SELECT id FROM pruefung WHERE bereich = ?", (inventar.WISO,)).fetchall():
        ids = [z[0] for z in con.execute(
            "SELECT t.id FROM teilaufgabe t JOIN aufgabe a ON a.id = t.aufgabe_id WHERE a.pruefung_id = ?", (p_id,))]
        if ids:
            con.execute(f"UPDATE teilaufgabe SET punkte = ? WHERE id IN ({','.join('?' * len(ids))})",
                        (round(100 / len(ids), 2), *ids))


def ausfuehren(con: sqlite3.Connection, daten: Path, ohne_ki: bool, ki: str) -> None:
    dokumente = con.execute("SELECT * FROM dokument WHERE art = 'aufgaben' AND pruefung_id IS NOT NULL ORDER BY dateiname").fetchall()
    for dok in dokumente:
        pfad = daten / "pdfs" / dok["dateiname"]
        _, seiten = inventar.lesen(daten, pfad, dok["sha256"])
        with pymupdf.open(pfad) as doc:
            anzahl = _speichern(con, daten, dok, seiten, doc)
        print(f"  {anzahl:3d} Teilaufgaben  {dok['dateiname']}", flush=True)
        con.commit()
    wiso_punkte(con)
    con.commit()
