"""Schritt 4: data/themen.md einlesen (# Bereich, ## Thema [LF5, LF8], - Unterthema: Stichworte) und die Lernfelder."""

import re
import sqlite3
import unicodedata
from pathlib import Path

KOMMENTAR = re.compile(r"<!--.*?-->", re.S)
LF_TAG = re.compile(r"\s*\[(LF[^\]]*)\]\s*$")

# Rahmenlehrplan Fachinformatiker/-in (KMK, 13.12.2019): (Nummer, Titel, Ausbildungsjahr, Stunden, Beruf)
LERNFELDER = [
    ("1", "Das Unternehmen und die eigene Rolle im Betrieb beschreiben", 1, 40, "IT"),
    ("2", "Arbeitsplätze nach Kundenwunsch ausstatten", 1, 80, "IT"),
    ("3", "Clients in Netzwerke einbinden", 1, 80, "IT"),
    ("4", "Schutzbedarfsanalyse im eigenen Arbeitsbereich durchführen", 1, 40, "IT"),
    ("5", "Software zur Verwaltung von Daten anpassen", 1, 80, "IT"),
    ("6", "Serviceanfragen bearbeiten", 2, 40, "IT"),
    ("7", "Cyber-physische Systeme ergänzen", 2, 80, "IT"),
    ("8", "Daten systemübergreifend bereitstellen", 2, 80, "IT"),
    ("9", "Netzwerke und Dienste bereitstellen", 2, 80, "IT"),
    ("10a", "Benutzerschnittstellen gestalten und entwickeln", 3, 80, "1201"),
    ("11a", "Funktionalität in Anwendungen realisieren", 3, 80, "1201"),
    ("12a", "Kundenspezifische Anwendungsentwicklung durchführen", 3, 120, "1201"),
    ("10b", "Serverdienste bereitstellen und Administrationsaufgaben automatisieren", 3, 80, "1202"),
    ("11b", "Betrieb und Sicherheit vernetzter Systeme gewährleisten", 3, 80, "1202"),
    ("12b", "Kundenspezifische Systemintegration durchführen", 3, 120, "1202"),
]


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.replace("ß", "ss")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def lesen(text: str) -> list[dict]:
    """Einträge {ebene, name, stichworte, lernfelder, eltern (Index), position} in Dateireihenfolge."""
    eintraege, letzte, zaehler = [], {}, {}
    for zeile in KOMMENTAR.sub("", text).splitlines():
        lernfelder = []
        if treffer := re.match(r"^(#{1,2})\s+(.+)$", zeile.strip()):
            ebene, name, stichworte = len(treffer.group(1)), treffer.group(2).strip(), None
            if tag := LF_TAG.search(name):
                name = name[:tag.start()].strip()
                lernfelder = [lf.strip().removeprefix("LF") for lf in tag.group(1).split(",") if lf.strip()]
        elif treffer := re.match(r"^[-*]\s+(.+)$", zeile.strip()):
            ebene = 3
            name, _, stichworte = (s.strip() for s in treffer.group(1).partition(":"))
            stichworte = stichworte or None
        else:
            continue
        eltern = letzte.get(ebene - 1)
        if ebene > 1 and eltern is None:
            raise ValueError(f"„{name}“ steht ohne übergeordnetes Thema in der Themenliste")
        zaehler[eltern] = zaehler.get(eltern, -1) + 1
        letzte[ebene] = len(eintraege)
        eintraege.append({"ebene": ebene, "name": name, "stichworte": stichworte, "lernfelder": lernfelder,
                          "eltern": eltern, "position": zaehler[eltern]})
    return eintraege


def ausfuehren(con: sqlite3.Connection, daten: Path, ohne_ki: bool, ki: str) -> None:
    datei = daten / "themen.md"
    if not datei.exists():
        raise SystemExit(f"Die Themenliste fehlt: {datei} (Format siehe data/themen.example.md)")
    eintraege = lesen(datei.read_text(encoding="utf-8"))
    if not eintraege:
        raise SystemExit(f"Die Themenliste {datei} enthält keine Themen")
    ids, slugs = [], set()
    for e in eintraege:
        s = slug(e["name"])
        if s in slugs:  # gleicher Name an zwei Stellen: der Bereich macht ihn eindeutig
            s = f"{slug(eintraege[e['eltern']]['name'])}-{s}"
        slugs.add(s)
        ids.append(con.execute(
            """INSERT INTO thema (eltern_id, ebene, name, slug, stichworte, position) VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (slug) DO UPDATE SET eltern_id = excluded.eltern_id, ebene = excluded.ebene,
                 name = excluded.name, stichworte = excluded.stichworte, position = excluded.position
               RETURNING id""",
            (ids[e["eltern"]] if e["eltern"] is not None else None, e["ebene"], e["name"], s, e["stichworte"], e["position"]),
        ).fetchone()[0])
    # Lernfelder und ihre Themen
    con.executemany("INSERT INTO lernfeld (nummer, titel, jahr, stunden, beruf) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT (nummer) DO UPDATE SET titel = excluded.titel", LERNFELDER)
    lf_ids = {z[0]: z[1] for z in con.execute("SELECT nummer, id FROM lernfeld")}
    con.executemany("DELETE FROM thema_lernfeld WHERE thema_id = ?", [(i,) for i in ids])
    for e, t_id in zip(eintraege, ids):
        for lf in e["lernfelder"]:
            if lf not in lf_ids:
                raise SystemExit(f"Unbekanntes Lernfeld LF{lf} bei „{e['name']}“ (möglich: {', '.join(lf_ids)})")
            con.execute("INSERT OR IGNORE INTO thema_lernfeld (thema_id, lernfeld_id) VALUES (?, ?)", (t_id, lf_ids[lf]))
    # Themen, die nicht mehr in der Liste stehen, fallen weg (samt ihren Zuordnungen) – außer an ihnen
    # hängen Korrekturen aus Bunseki oder manuelle Voraussetzungen
    geschuetzt = {z[0] for z in con.execute(
        "SELECT v.vorfahr_id FROM v_thema_vorfahr v WHERE v.thema_id IN "
        "(SELECT thema_id FROM teilaufgabe_thema WHERE quelle = 'manuell' UNION "
        " SELECT thema_id FROM thema_voraussetzung WHERE quelle = 'manuell' UNION "
        " SELECT voraussetzung_id FROM thema_voraussetzung WHERE quelle = 'manuell')")}
    weg = [z[0] for z in con.execute(f"SELECT id FROM thema WHERE id NOT IN ({','.join('?' * len(ids))})", ids)]
    behalten = [i for i in weg if i in geschuetzt]
    con.executemany("DELETE FROM thema WHERE id = ?", [(i,) for i in weg if i not in geschuetzt])
    con.commit()
    if behalten:
        print(f"  {len(behalten)} Themen fehlen in der Liste, bleiben aber wegen manueller Zuordnungen erhalten", flush=True)
    print(f"  {len(ids)} Themen", flush=True)
