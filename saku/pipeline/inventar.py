"""Schritt 1: PDFs erfassen, Deckblatt lesen (Regex, sonst KI), Text oder Scan erkennen."""

import hashlib
import re
import sqlite3
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pymupdf

from saku.pipeline import pdf

PLANEN = "Planen eines Softwareproduktes"
ENTWICKLUNG = "Entwicklung und Umsetzung von Algorithmen"
KONZEPTION = "Konzeption und Administration von IT-Systemen"
NETZWERKE = "Analyse und Entwicklung von Netzwerken"
ARBEITSPLATZ = "Einrichten eines IT-gestützten Arbeitsplatzes"  # AP1, gleich für alle IT-Berufe
WISO = "Wirtschafts- und Sozialkunde"
GA1 = "Ganzheitliche Aufgabe I"
GA2 = "Ganzheitliche Aufgabe II"
BEREICHE = [PLANEN, ENTWICKLUNG, KONZEPTION, NETZWERKE, ARBEITSPLATZ, WISO, GA1, GA2]
# Bereiche 1 bis 3 laut Deckblatt („1201 2“ = Entwicklung)
NUMMERN = {"1201": [PLANEN, ENTWICKLUNG, WISO], "1196": [PLANEN, ENTWICKLUNG, WISO],
           "1202": [KONZEPTION, NETZWERKE, WISO], "1197": [KONZEPTION, NETZWERKE, WISO], "6450": [PLANEN, ENTWICKLUNG, WISO]}
# Bereiche der Themenliste je Lernpfad (Lernpfad, Wissensgraph)
BEREICHE_JE_PFAD = {"AP1": [ARBEITSPLATZ], "AP2-1201": [PLANEN, ENTWICKLUNG, WISO], "AP2-1202": [KONZEPTION, NETZWERKE, WISO]}
UNSERE = ("1201", "1196", "1202", "1197")  # AE und SI nach AO 2020 und AO 1997
NACH_AO_2020 = {"1196": "1201", "1197": "1202"}

# AP1 findet im Frühjahr und Herbst statt; für die Sortierung zählt Frühjahr wie Sommer, Herbst wie Winter
TERMIN = re.compile(r"(Sommer|Winter|Frühjahr|Herbst)[\s_-]*(20\d\d)")
MONAT = re.compile(r"\d{1,2}\.\s*(Januar|März|April|Mai|Juni|September|Oktober|November|Dezember)\s*(20\d\d)")
BERUFE = [  # (Muster, Berufsnummer); die Liste aller IT-Berufe steht auf WiSo-Lösungen und GA2
    (r"1201\s*[-–]\s*1202|1190\s*[-–]\s*1196", "IT-Berufe"),
    (r"Anwen\w*\s*entw|Anwendungsentw|Fachinformatiker\s+Anwen|\b1201\b", "1201"),
    (r"\b1196\b", "1196"),
    (r"Systemintegration|\b120[2]\b|\b1197\b", "1202"),
    (r"Daten-\s*und\s*Prozess|\b1203\b", "1203"),
    (r"Digitale\s*Vernetzung|\b1204\b", "1204"),
    (r"System-?\s*Elektron|\b1205\b|\b1190\b", "1205"),
    (r"Digitalisierungsmanagement|\b6480\b", "6480"),
    (r"System-?\s*Kauf|System-?Management|\b6470\b|\b6440\b", "6470"),
    (r"Informatikkauf|\b6450\b", "6450"),
]


def _fuss(text: str) -> str | None:
    """Bereich aus der Fußzeile „ZPA FIA I 3“ (Planen) bzw. „ZPA FIA II 3“ (Entwicklung), per Mehrheit."""
    zwei = len(re.findall(r"ZPA\s*FIA\s*(?:II|Il|lI|ll|\|\||I\||\|I)\s*\d", text))
    eins = len(re.findall(r"ZPA\s*FIA\s*[I|l]\s*\d", text)) - zwei
    if zwei or eins:
        return ENTWICKLUNG if zwei > eins else PLANEN
    return None


def deckblatt(seiten: list[str], dateiname: str = "") -> dict:
    """Termin, Bereich, Beruf, Art und Format aus dem Text der Seiten (Deckblatt zuerst); fehlt etwas, ist es None."""
    kopf = "\n".join(seiten[:2])
    alles = "\n".join(seiten)
    erste = seiten[0][:800] if seiten else ""
    name = Path(dateiname).stem.replace("_", " ")

    jahr = saison = None
    if treffer := TERMIN.search(kopf) or TERMIN.search(name):
        saison, jahr = treffer.group(1), int(treffer.group(2))
    elif treffer := MONAT.search(kopf):
        saison = {"März": "Frühjahr", "September": "Herbst", "Oktober": "Herbst", "November": "Winter",
                  "Dezember": "Winter"}.get(treffer.group(1), "Sommer")
        jahr = int(treffer.group(2)) - (treffer.group(1) == "Januar")

    belegsatz = bool(re.search(r"Belegsatz\s+(?:Fach|IT|Kauf)|Der\s+Belegsatz\s+ist", erste))
    if belegsatz or re.search(r"Lösungsbogen", erste[:150]):
        art = "sonstiges"
    # das Deckblatt der Aufgaben nennt „die Lösungshinweise(n)“ auch, hat aber die Kopfleiste für den Namen
    elif not re.search(r"Kopfleiste", erste) and re.search(
            r"Lösungshinweise\b|Lösungserl\w*terungen|Vorläufige\s+Lösungen|Lösungen\s+IT|^\s*Lösungen", erste, re.M):
        art = "loesungen"
    else:
        art = "aufgaben"

    beruf = next((nr for muster, nr in BERUFE if re.search(muster, erste + " " + name)), None)
    teil1 = saison in ("Frühjahr", "Herbst") or bool(re.search(
        r"Teil\s*1\s+der\s+Abschluss|Zwischenprüfung|ZPA\s*IT\s*1|Einrichten\s+eines\s+IT", kopf))

    nummer = re.search(r"\b(1201|1202|1196|1197|6450)\s+([123])\b", erste)
    if teil1:
        bereich = ARBEITSPLATZ
    elif re.search(r"Ganzheitliche|ZPA\s*\w+\s*Ganz", alles):
        zwei = re.search(r"Kernqualifikation|Ganz\s*II|Ganzheitliche\s+Aufgabe\s*(?:II|Il|ll|I\|)", kopf)
        bereich = GA2 if zwei or (nummer and nummer.group(2) == "2") else GA1
    elif re.search(r"Wirtschafts-?\s*und\s|So\w{0,3}alkunde|30\s+Aufgaben", kopf) or beruf == "IT-Berufe" and art == "loesungen":
        bereich = WISO
    elif re.search(r"Planen\s+eines|Soft\w*produkt", erste):
        bereich = PLANEN
    elif re.search(r"Konzeption\s+und\s+Admin", erste):
        bereich = KONZEPTION
    elif re.search(r"Entwicklung\s+von\s+Netzwerk", erste):
        bereich = NETZWERKE
    elif re.search(r"Umsetzung|Algorithmen", erste):
        bereich = ENTWICKLUNG
    elif nummer:
        bereich = NUMMERN[nummer.group(1)][int(nummer.group(2)) - 1]
    else:
        bereich = _fuss(alles)
    # Scans mit unlesbarem Deckblatt: Bereich und Beruf aus dem Dateinamen („G1 (SI)“, „Teil-2-2-FIS“)
    fach = "1202" if re.search(r"SI|FIS", name) else "1201" if re.search(r"AE", name) else None
    if bereich is None and fach and (nr := re.search(r"\bG\s*([12])\b|-2-([12])\b", name)):
        bereich = NUMMERN[fach][int(nr.group(1) or nr.group(2)) - 1]
        beruf = beruf or fach
    if beruf == "IT-Berufe" and bereich == GA1:
        bereich = GA2
    genannt = [b for b in (PLANEN, ENTWICKLUNG, KONZEPTION, NETZWERKE, WISO) if re.search(b.split()[0] + r"\s+\w+\s+" + b.split()[2], kopf)]
    if art == "loesungen" and len(genannt) > 1 or belegsatz:
        bereich = None  # Lösungserläuterungen und Belegsätze gelten für mehrere Bereiche

    frueher = bool(re.search(r"A[O0]\s*1997|Ganzheitliche|\b1196\b|\b1190\b|System-?\s*Kauf", erste)) or "Ganz" in str(bereich)
    # Teil 2 nach AO 2020 gibt es erst seit Winter 2021/22, Teil 1 seit Herbst 2021
    frueher |= bool(jahr) and not teil1 and (jahr, saison) < (2021, "Winter")
    dauer = re.search(r"(\d{2,3})\s*Minuten", kopf)
    return {
        "jahr": jahr, "saison": saison, "bereich": bereich, "beruf": beruf, "art": art, "teil1": teil1, "belegsatz": belegsatz,
        "format": "frueher" if frueher else "aktuell",
        # nur plausible Bearbeitungszeiten; OCR liest sonst auch „15 Minuten“ aus dem Aufgabentext
        "dauer_min": int(dauer.group(1)) if dauer and 45 <= int(dauer.group(1)) <= 240
                     else (60 if bereich == WISO else 90 if bereich else None),
    }




def ausschluss(m: dict) -> str | None:
    """Grund, warum ein Dokument nicht zum Katalog (AE, SI, AP1, WiSo) gehört, sonst None."""
    if m["jahr"] is None or m["saison"] is None:
        return "kein Termin erkennbar"
    if m["format"] == "frueher" and m["jahr"] < 2022:
        return "früheres Format vor 2022"
    if m["art"] == "sonstiges":
        return "Belegsatz oder Lösungsbogen"  # shortcut: Belegsätze zeigt Saku noch nicht an
    if m["teil1"] or m["bereich"] in (WISO, GA2):
        return None
    if m["beruf"] not in UNSERE:
        return f"anderer Beruf ({m['beruf'] or 'unbekannt'})"
    return None


SYSTEM = """Du liest das Deckblatt einer IHK-Prüfung für IT-Berufe und gibst die Angaben strukturiert zurück.
Prüfungsbereiche: "Planen eines Softwareproduktes", "Entwicklung und Umsetzung von Algorithmen" (AE),
"Konzeption und Administration von IT-Systemen", "Analyse und Entwicklung von Netzwerken" (SI),
"Einrichten eines IT-gestützten Arbeitsplatzes" (AP1, Frühjahr oder Herbst), "Wirtschafts- und Sozialkunde",
"Ganzheitliche Aufgabe I", "Ganzheitliche Aufgabe II" oder "unbekannt".
Der Text stammt oft aus einer Texterkennung und ist verrauscht. Winter 2024/25 hat das Jahr 2024."""
SCHEMA = {
    "type": "object",
    "properties": {
        "jahr": {"type": "integer"},
        "saison": {"type": "string", "enum": ["Sommer", "Winter", "Frühjahr", "Herbst"]},
        "bereich": {"type": "string", "enum": BEREICHE + ["unbekannt"]},
        "beruf": {"type": "string", "description": "Berufsnummer, z. B. 1201, oder IT-Berufe"},
        "dauer_min": {"type": "integer"},
        "art": {"type": "string", "enum": ["aufgaben", "loesungen", "sonstiges"]},
        "format": {"type": "string", "enum": ["aktuell", "frueher"]},
    },
    "required": ["jahr", "saison", "bereich", "beruf", "dauer_min", "art", "format"],
    "additionalProperties": False,
}


def ordner(daten: Path, sha256: str) -> Path:
    """Ablage für Bildausschnitte und OCR-Ergebnis eines Dokuments."""
    return daten / "aufgaben" / sha256[:12]


def lesen(daten: Path, pfad: Path, sha256: str) -> tuple[bool, list[dict]]:
    """(Scan?, Seiten mit Zeilen); Scans werden einmal per OCR gelesen und zwischengespeichert."""
    with pymupdf.open(pfad) as doc:
        scan = pdf.ist_scan(doc)
    return scan, pdf.seiten(pfad, scan, ordner(daten, sha256) / "zeilen.json", daten)


def _vorlesen(auftrag: tuple[Path, Path, str]) -> None:
    lesen(*auftrag)


def ausfuehren(con: sqlite3.Connection, daten: Path, ohne_ki: bool, ki: str) -> None:
    from saku.sensei import client

    pdfs = sorted(p for p in (daten / "pdfs").rglob("*") if p.suffix.lower() == ".pdf")
    bekannt = {z["sha256"] for z in con.execute("SELECT sha256 FROM dokument")}
    neu = [(p, hashlib.sha256(p.read_bytes()).hexdigest()) for p in pdfs]
    neu = [(p, h) for p, h in neu if h not in bekannt]
    if not neu:
        return

    # Texterkennung parallel vorab, danach liegt alles im Zwischenspeicher
    with ProcessPoolExecutor(pdf.OCR_PROZESSE) as pool:
        list(pool.map(_vorlesen, [(daten, p, h) for p, h in neu]))

    for pfad, sha in neu:
        scan, seiten = lesen(daten, pfad, sha)
        name = str(pfad.relative_to(daten / "pdfs"))
        m = deckblatt([pdf.text(s) for s in seiten], name)
        if not ohne_ki and (m["jahr"] is None or m["bereich"] is None and m["art"] == "aufgaben"):
            antwort = client.strukturiert(con, "deckblatt", "schnell", SYSTEM, "\n".join(pdf.text(s) for s in seiten[:2])[:6000],
                                          SCHEMA, ki=ki)
            m |= {k: antwort[k] for k in ("jahr", "saison", "art", "format") if m.get(k) is None}
            m["bereich"] = m["bereich"] or (antwort["bereich"] if antwort["bereich"] in BEREICHE else None)
            m["beruf"] = m["beruf"] or antwort["beruf"]
        pruefung_id = None
        if not ausschluss(m):
            pruefung_id = pruefung_anlegen(con, m)
        con.execute(
            "INSERT INTO dokument (dateiname, sha256, seiten, art, hat_textebene, pruefung_id) VALUES (?, ?, ?, ?, ?, ?)",
            (name, sha, len(seiten), m["art"], int(not scan), pruefung_id),
        )
    con.commit()


def teil_und_beruf(m: dict) -> tuple[str, str]:
    """AP1, AP2 oder AP (AO 1997); Beruf 1201/1202 oder IT für alles, was alle IT-Berufe gleich schreiben."""
    teil = "AP1" if m.get("teil1") else "AP" if m["format"] == "frueher" else "AP2"
    if teil == "AP1" or m["bereich"] in (WISO, GA2):
        return teil, "IT"
    return teil, NACH_AO_2020.get(m.get("beruf"), m.get("beruf") if m.get("beruf") in UNSERE else "1201")


def pruefung_anlegen(con: sqlite3.Connection, m: dict) -> int:
    """Upsert über (Jahr, Saison, Teil, Bereich, Beruf). Dokumente für mehrere Bereiche hängen am ersten Bereich."""
    frueher = m["format"] == "frueher"
    teil, beruf = teil_und_beruf(m)
    bereich = m["bereich"] or (ARBEITSPLATZ if teil == "AP1" else GA1 if frueher else NUMMERN.get(beruf, [PLANEN])[0])
    dauer = m["dauer_min"] or (60 if bereich == WISO else 90)
    return con.execute(
        """INSERT INTO pruefung (jahr, saison, teil, bereich, beruf, format, gewicht, dauer_min, punkte_gesamt)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 100)
           ON CONFLICT (jahr, saison, teil, bereich, beruf) DO UPDATE SET
               format = excluded.format, gewicht = excluded.gewicht,
               dauer_min = COALESCE(pruefung.dauer_min, excluded.dauer_min)
           RETURNING id""",
        (m["jahr"], m["saison"], teil, bereich, beruf, m["format"], 0.5 if frueher else 1.0, dauer),
    ).fetchone()[0]
