"""Demo-Datenbank mit ERFUNDENEN Prüfungen – für Tests und für die UI-Entwicklung ohne echte PDFs.

    python -m tests.demo_daten /tmp/saku-demo
    SAKU_DATENORDNER=/tmp/saku-demo python -m saku start --browser
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pymupdf

from saku import config, db
from saku.pipeline.inventar import WISO

THEMEN = {
    "Planen eines Softwareproduktes": {
        "Projektmanagement": ["Netzplan: Puffer, kritischer Pfad", "Wirtschaftlichkeit: Amortisation, Nutzwertanalyse"],
        "Modellierung mit UML": ["Klassendiagramm: Assoziation, Vererbung", "Sequenzdiagramm"],
        "Anforderungen": ["Lastenheft und Pflichtenheft", "Use-Case-Diagramm"],
    },
    "Entwicklung und Umsetzung von Algorithmen": {
        "Algorithmen": ["Pseudocode: Schleifen, Verzweigungen", "Sortieren und Suchen", "Rekursion"],
        "Datenbanken": ["SQL: SELECT, JOIN, GROUP BY", "Normalisierung: 1. NF bis 3. NF", "ER-Modell"],
        "Qualitätssicherung": ["Testverfahren: Blackbox, Whitebox"],
    },
    "Wirtschafts- und Sozialkunde": {
        "Arbeitsrecht": ["Kündigung und Kündigungsschutz"],
    },
}


def _wahl(art: str, optionen: list[str], richtig: list[str], ziele: list[str] = (), einheit: str = "") -> dict:
    """Antwortformat wie aus dem Schritt aufbereiten; Optionen und Ziele werden 1, 2, 3 …"""
    nummeriert = lambda texte: [{"wert": str(i), "text": t} for i, t in enumerate(texte, start=1)]
    return {"art": art, "optionen": nummeriert(optionen), "ziele": nummeriert(ziele), "richtig": richtig, "einheit": einheit, "vorlage": ""}


# (jahr, saison, bereich, aufgaben)  aufgabe = (titel, einleitung, [(kennung, punkte, text, loesung, [unterthema], antwort?)])
PRUEFUNGEN = [
    (2023, "Sommer", "Planen eines Softwareproduktes", [
        ("Projektplanung", "Die Demo GmbH plant ein Kundenportal.", [
            ("a", 6, "Ermitteln Sie den kritischen Pfad des Netzplans.", "Kritischer Pfad: A-C-E-F, Dauer 14 Tage.", ["Netzplan: Puffer, kritischer Pfad"]),
            ("b", 4, "Berechnen Sie den Gesamtpuffer des Vorgangs D.", "GP(D) = SAZ - FAZ = 3 Tage.", ["Netzplan: Puffer, kritischer Pfad"]),
            ("c", 8, "Führen Sie eine Nutzwertanalyse für zwei Anbieter durch.", "Anbieter B erreicht 7,4 Punkte und wird gewählt.", ["Wirtschaftlichkeit: Amortisation, Nutzwertanalyse"]),
        ]),
        ("Modellierung", "Das Portal verwaltet Kunden und Bestellungen.", [
            ("a", 10, "Erstellen Sie ein UML-Klassendiagramm für Kunde und Bestellung.", "Kunde 1 -- 0..* Bestellung, Attribute privat.", ["Klassendiagramm: Assoziation, Vererbung"]),
            ("b", 6, "Zeichnen Sie ein Sequenzdiagramm für den Login.", "Benutzer -> Portal: login(); Portal -> DB: pruefe().", ["Sequenzdiagramm"]),
        ]),
    ]),
    (2023, "Winter", "Entwicklung und Umsetzung von Algorithmen", [
        ("Algorithmus", "Ein Lagerprogramm soll Artikel sortieren.", [
            ("a", 8, "Schreiben Sie in Pseudocode einen Bubblesort.", "Zwei geschachtelte Schleifen, Tausch bei a[j] > a[j+1].", ["Sortieren und Suchen", "Pseudocode: Schleifen, Verzweigungen"]),
            ("b", 4, "Bestimmen Sie die Laufzeitklasse.", "O(n²) im schlechtesten Fall.", ["Sortieren und Suchen"]),
            ("c", 6, "Formulieren Sie die Fakultät rekursiv.", "fak(n) = 1 für n <= 1, sonst n * fak(n-1).", ["Rekursion"]),
        ]),
        ("Datenbank", "Die Lagerdaten liegen in einer relationalen Datenbank.", [
            ("a", 8, "Schreiben Sie eine SQL-Abfrage: Anzahl Artikel je Lager.", "SELECT lager_id, COUNT(*) FROM artikel GROUP BY lager_id;", ["SQL: SELECT, JOIN, GROUP BY"]),
            ("b", 10, "Überführen Sie die Tabelle in die 3. Normalform.", "Lager und Artikel trennen, Fremdschlüssel lager_id.", ["Normalisierung: 1. NF bis 3. NF"]),
            ("c", 6, "Nennen Sie zwei Whitebox-Testverfahren.", "Anweisungsüberdeckung, Zweigüberdeckung.", ["Testverfahren: Blackbox, Whitebox"]),
        ]),
    ]),
    (2024, "Sommer", "Entwicklung und Umsetzung von Algorithmen", [
        ("Abfragen", "Ein Fahrradverleih speichert Ausleihen.", [
            ("a", 6, "Verbinden Sie Kunde und Ausleihe per JOIN.", "SELECT * FROM kunde k JOIN ausleihe a ON a.kunde_id = k.id;", ["SQL: SELECT, JOIN, GROUP BY"]),
            ("b", 8, "Erstellen Sie ein ER-Modell für den Verleih.", "Kunde 1:n Ausleihe n:1 Fahrrad.", ["ER-Modell"]),
            ("c", 6, "Suchen Sie binär in einer sortierten Liste.", "Mitte vergleichen, Hälfte verwerfen, O(log n).", ["Sortieren und Suchen"]),
        ]),
    ]),
]

# Erfundene WiSo-Prüfungen, nur anklickbare Teilaufgaben wie in der echten Prüfung. Kommen nur mit anlegen(wiso=True) dazu
# (die Demo-Oberfläche, Tests zum WiSo-Schnelltest), damit die Zahlen der übrigen Tests bleiben.
WISO_THEMEN = {
    "Arbeitsrecht": ["Kündigung und Kündigungsschutz", "Arbeitszeit und Mitbestimmung: Arbeitszeitgesetz, Betriebsrat, JAV",
                     "Rechtsquellen: Rangfolge"],
    "Berufsausbildung": ["Ausbildungsvertrag: Probezeit, Pflichten"],
    "Betrieb und Soziales": ["Sozialversicherung: Zweige, Träger, Beiträge", "Rechtsformen und Gehalt"],
}
WISO_PRUEFUNGEN = [
    (2023, "Sommer", "Wirtschafts- und Sozialkunde", [
        ("Ausbildung", "Sie beginnen Ihre Ausbildung bei der Demo GmbH.", [
            ("a", 3, "Wie lange darf die Probezeit in der Ausbildung höchstens dauern?", "Vier Monate.", ["Ausbildungsvertrag: Probezeit, Pflichten"],
             _wahl("einfach", ["Einen Monat", "Vier Monate", "Sechs Monate", "Ein Jahr"], ["2"])),
            ("b", 4, "Welche Pflichten hat der Ausbildende? Wählen Sie zwei.", "Ausbildungsmittel bereitstellen, für die Berufsschule freistellen.",
             ["Ausbildungsvertrag: Probezeit, Pflichten"],
             _wahl("mehrfach", ["Ausbildungsmittel kostenlos bereitstellen", "Für die Berufsschule freistellen",
                                "Überstunden ohne Ausgleich anordnen", "Private Erledigungen übertragen"], ["1", "2"])),
        ]),
        ("Kündigung", "Ein Kollege möchte das Unternehmen verlassen.", [
            ("a", 3, "Die Grundkündigungsfrist beträgt vier Wochen. Wie viele Tage sind das?", "28 Tage.", ["Kündigung und Kündigungsschutz"],
             _wahl("zahl", [], ["28"], einheit="Tage")),
            ("b", 4, "Bringen Sie die Schritte einer Kündigung durch den Arbeitgeber in die richtige Reihenfolge.",
             "Betriebsrat anhören, Kündigung schriftlich übergeben, Frist läuft, Arbeitsverhältnis endet.", ["Kündigung und Kündigungsschutz"],
             _wahl("reihenfolge", ["Kündigungsfrist läuft", "Betriebsrat anhören", "Arbeitsverhältnis endet", "Kündigung schriftlich übergeben"],
                   ["2", "4", "1", "3"])),
        ]),
        ("Sozialversicherung", "Ihre erste Gehaltsabrechnung liegt vor.", [
            ("a", 4, "Ordnen Sie jeder Versicherung ihren Träger zu.", "Kranken: Krankenkasse, Rente: DRV, Unfall: Berufsgenossenschaft.",
             ["Sozialversicherung: Zweige, Träger, Beiträge"],
             _wahl("zuordnung", ["Krankenversicherung", "Rentenversicherung", "Unfallversicherung"], ["1=2", "2=3", "3=1"],
                   ziele=["Berufsgenossenschaft", "Krankenkasse", "Deutsche Rentenversicherung"])),
            ("b", 3, "Wer zahlt die Beiträge zur gesetzlichen Unfallversicherung?", "Der Arbeitgeber allein.",
             ["Sozialversicherung: Zweige, Träger, Beiträge"],
             _wahl("einfach", ["Arbeitnehmer allein", "Arbeitgeber allein", "Beide je zur Hälfte", "Der Staat"], ["2"])),
        ]),
    ]),
    (2023, "Winter", "Wirtschafts- und Sozialkunde", [
        ("Unternehmen", "Die Demo GmbH ist eine Gesellschaft mit beschränkter Haftung.", [
            ("a", 3, "Wie hoch ist das Mindeststammkapital einer GmbH?", "25.000 €.", ["Rechtsformen und Gehalt"],
             _wahl("einfach", ["1 €", "12.500 €", "25.000 €", "50.000 €"], ["3"])),
            ("b", 3, "Ein Gehalt von 3.000 € steigt um 4 %. Wie hoch ist es danach in Euro?", "3.120 €.", ["Rechtsformen und Gehalt"],
             _wahl("zahl", [], ["3120"], einheit="€")),
        ]),
        ("Mitbestimmung", "Im Betrieb arbeiten 60 Beschäftigte.", [
            ("a", 4, "Wer darf den Betriebsrat wählen? Wählen Sie alle zutreffenden.", "Arbeitnehmer und Auszubildende ab 16 Jahren.",
             ["Arbeitszeit und Mitbestimmung: Arbeitszeitgesetz, Betriebsrat, JAV"],
             _wahl("mehrfach", ["Arbeitnehmer ab 16 Jahren", "Auszubildende ab 16 Jahren", "Der Geschäftsführer", "Kunden des Betriebs"], ["1", "2"])),
            ("b", 3, "Welches Gremium vertritt die Auszubildenden unter 25 Jahren?", "Die Jugend- und Auszubildendenvertretung.",
             ["Arbeitszeit und Mitbestimmung: Arbeitszeitgesetz, Betriebsrat, JAV"],
             _wahl("einfach", ["Aufsichtsrat", "Jugend- und Auszubildendenvertretung", "Wirtschaftsausschuss", "Gewerkschaft"], ["2"])),
        ]),
        ("Arbeitsrecht", "Sie prüfen Ihren Arbeitsvertrag.", [
            ("a", 3, "Wie viele Stunden darf man werktäglich regelmäßig arbeiten (ohne Ausgleich)?", "8 Stunden.",
             ["Arbeitszeit und Mitbestimmung: Arbeitszeitgesetz, Betriebsrat, JAV"], _wahl("zahl", [], ["8"], einheit="Stunden")),
            ("b", 4, "Ordnen Sie die Rechtsquellen nach ihrem Rang, die höchste zuerst.", "Grundgesetz, Gesetz, Tarifvertrag, Arbeitsvertrag.",
             ["Rechtsquellen: Rangfolge"],
             _wahl("reihenfolge", ["Tarifvertrag", "Grundgesetz", "Arbeitsvertrag", "Gesetz (z. B. BGB)"], ["2", "4", "1", "3"])),
        ]),
    ]),
]

# Erfundene SQL-Sandboxen (wie aus dem Schritt sandbox): (Jahr, Saison, Aufgabe) → ddl, daten, {Kennung: Lösung in SQLite}
SANDBOXEN = {
    (2023, "Winter", 2): (
        "CREATE TABLE lager (id INTEGER PRIMARY KEY, ort TEXT NOT NULL);\n"
        "CREATE TABLE artikel (id INTEGER PRIMARY KEY, name TEXT NOT NULL, preis REAL, lager_id INTEGER REFERENCES lager(id));",
        "INSERT INTO lager VALUES (1, 'Nord'), (2, 'Süd'), (3, 'Ost');\n"
        "INSERT INTO artikel VALUES (1, 'Schraube', 0.1, 1), (2, 'Mutter', 0.05, 1), (3, 'Dübel', 0.2, 2), "
        "(4, 'Winkel', 1.5, 2), (5, 'Haken', 0.8, 1), (6, 'Kabel', NULL, NULL);",
        {"a": "SELECT lager_id, COUNT(*) FROM artikel GROUP BY lager_id;"}),
    (2024, "Sommer", 1): (
        "CREATE TABLE kunde (id INTEGER PRIMARY KEY, name TEXT NOT NULL);\n"
        "CREATE TABLE ausleihe (id INTEGER PRIMARY KEY, kunde_id INTEGER REFERENCES kunde(id), fahrrad TEXT, datum TEXT);",
        "INSERT INTO kunde VALUES (1, 'Ada'), (2, 'Bo'), (3, 'Cem');\n"
        "INSERT INTO ausleihe VALUES (1, 1, 'Stadtrad', '2024-05-31'), (2, 1, 'E-Bike', '2024-06-01'), (3, 2, 'Lastenrad', '2024-06-02');",
        {"a": "SELECT * FROM kunde k JOIN ausleihe a ON a.kunde_id = k.id;"}),
}
SQL_ANTWORT = json.dumps({"art": "sql", "optionen": [], "ziele": [], "richtig": [], "einheit": "", "vorlage": ""})


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def _bild(pfad: Path, zeilen: list[str]) -> None:
    """Rendert einen kleinen Ausschnitt wie aus einem PDF (schwarz auf weiß)."""
    doc = pymupdf.open()
    seite = doc.new_page(width=500, height=40 + 18 * len(zeilen))
    seite.insert_text((20, 30), "\n".join(zeilen), fontsize=11, lineheight=1.6)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    seite.get_pixmap(dpi=150).save(pfad)


def anlegen(daten: Path, pruefungstermin: date | None = None, wiso: bool = False) -> Path:
    pfad = config.db_pfad(daten)
    if pfad.exists():
        pfad.unlink()
    db.init(pfad)
    con = db.verbinden(pfad)
    termin = pruefungstermin or date.today() + timedelta(days=60)
    db.setze_einstellung(con, "pruefungstermin", termin.isoformat())

    unterthema = {}
    for p1, (bereich, themen) in enumerate((THEMEN | ({WISO: WISO_THEMEN} if wiso else {})).items()):
        b_id = con.execute("INSERT INTO thema (ebene, name, slug, position) VALUES (1, ?, ?, ?)",
                           (bereich, _slug(bereich), p1)).lastrowid
        for p2, (thema, unter) in enumerate(themen.items()):
            t_id = con.execute("INSERT INTO thema (eltern_id, ebene, name, slug, position) VALUES (?, 2, ?, ?, ?)",
                               (b_id, thema, _slug(thema), p2)).lastrowid
            for p3, name in enumerate(unter):
                titel, _, stichworte = name.partition(": ")
                unterthema[name] = con.execute(
                    "INSERT INTO thema (eltern_id, ebene, name, slug, stichworte, position) VALUES (?, 3, ?, ?, ?, ?)",
                    (t_id, titel, _slug(titel), stichworte or None, p3)).lastrowid

    alle = []
    for jahr, saison, bereich, aufgaben in PRUEFUNGEN + (WISO_PRUEFUNGEN if wiso else []):
        p_id = con.execute(
            "INSERT INTO pruefung (jahr, saison, bereich, beruf, format, dauer_min, punkte_gesamt, ausgangssituation) "
            "VALUES (?, ?, ?, '1201', 'aktuell', ?, 100, ?)",
            (jahr, saison, bereich, 60 if bereich == WISO else 90,
             f"Erfundene Ausgangssituation {saison} {jahr}: Sie arbeiten bei der Demo GmbH.")).lastrowid
        for nr, (titel, einleitung, teile) in enumerate(aufgaben, start=1):
            a_id = con.execute(
                "INSERT INTO aufgabe (pruefung_id, nummer, titel, einleitung, punkte) VALUES (?, ?, ?, ?, ?)",
                (p_id, nr, titel, einleitung, sum(t[1] for t in teile))).lastrowid
            for pos, (kennung, punkte, text, loesung, themen, *antwort) in enumerate(teile):
                ordner = Path("aufgaben") / "demo" / f"{jahr}-{saison}-{nr}{kennung}"
                _bild(daten / ordner / "aufgabe.png", [f"{nr}. Aufgabe {kennung})  ({punkte} Punkte)", text])
                _bild(daten / ordner / "loesung.png", ["Lösungshinweis", loesung])
                t_id = con.execute(
                    "INSERT INTO teilaufgabe (aufgabe_id, kennung, position, text, punkte, seite, bilder, typ, "
                    "loesung_text, loesung_bilder, antwort) VALUES (?, ?, ?, ?, ?, 2, ?, ?, ?, ?, ?)",
                    (a_id, kennung, pos, text, punkte, json.dumps([str(ordner / "aufgabe.png")]), "auswahl" if antwort else "erklaeren",
                     loesung, json.dumps([str(ordner / "loesung.png")]), json.dumps(antwort[0]) if antwort else None)).lastrowid
                for name in themen:
                    con.execute("INSERT INTO teilaufgabe_thema (teilaufgabe_id, thema_id, gewicht, sicherheit) "
                                "VALUES (?, ?, ?, 0.9)", (t_id, unterthema[name], 1 / len(themen)))
                con.execute("INSERT INTO suche (teilaufgabe_id, titel, text, loesung) VALUES (?, ?, ?, ?)",
                            (t_id, f"{saison} {jahr} · Aufgabe {nr} {kennung} · {titel}", f"{einleitung} {text}", loesung))
                alle.append((t_id, themen[0]))
            if bereich != WISO and (jahr, saison, nr) in SANDBOXEN:  # WiSo hat dieselben Termine, aber kein SQL
                ddl, daten_sql, loesungen = SANDBOXEN[(jahr, saison, nr)]
                con.execute("INSERT INTO sql_sandbox (aufgabe_id, ddl, daten) VALUES (?, ?, ?)", (a_id, ddl, daten_sql))
                for kennung, loesung in loesungen.items():
                    con.execute("UPDATE teilaufgabe SET typ = 'sql', antwort = ?, loesung_sql = ? WHERE aufgabe_id = ? AND kennung = ?",
                                (SQL_ANTWORT, loesung, a_id, kennung))

    # „Kam so ähnlich auch dran": gleiches erstes Unterthema
    for t_id, thema in alle:
        for anderes_id, anderes in alle:
            if t_id != anderes_id and thema == anderes:
                con.execute("INSERT INTO aehnlichkeit VALUES (?, ?, 0.6)", (t_id, anderes_id))

    # Lernpfad: eine Station je Thema (Ebene 2), Voraussetzung SQL vor Normalisierung
    stationen = con.execute("SELECT id, name FROM thema WHERE ebene = 2 ORDER BY eltern_id, position").fetchall()
    for pos, (th_id, name) in enumerate(stationen, start=1):
        s_id = con.execute("INSERT INTO station (position, titel, einfuehrung) VALUES (?, ?, ?)",
                           (pos, name, f"**{name}** – erfundene Einführung für die Demo.")).lastrowid
        con.execute("INSERT INTO station_thema VALUES (?, ?)", (s_id, th_id))
    con.execute("INSERT INTO thema_voraussetzung (thema_id, voraussetzung_id, begruendung) VALUES (?, ?, ?)",
                (unterthema["Normalisierung: 1. NF bis 3. NF"], unterthema["SQL: SELECT, JOIN, GROUP BY"], "Demo"))

    # Ein Dokument je Prüfung fürs Inventar
    for (p_id,) in con.execute("SELECT id FROM pruefung").fetchall():
        con.execute("INSERT INTO dokument (dateiname, sha256, seiten, art, pruefung_id) VALUES (?, ?, 12, 'aufgaben', ?)",
                    (f"demo-{p_id}.pdf", f"demo{p_id:060d}", p_id))
    con.commit()
    con.close()
    return pfad


if __name__ == "__main__":
    ziel = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/saku-demo")
    print(f"Demo-Datenbank: {anlegen(ziel, wiso=True)}")
