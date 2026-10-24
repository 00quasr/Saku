"""Datenbanken: SQL (Abfragen, Verknüpfen und Gruppieren, Daten ändern), ER-Modell → Tabellen und Normalisierung.
SQL-Aufgaben bringen Tabellen und Daten mit (Aufgabe.sandbox) und laufen in der Sandbox (lernen/sql): geprüft wird das Ergebnis
der eigenen Anweisung gegen das der Musterlösung. Alle Szenarien, Tabellen und Daten sind erfunden und so gewählt, dass typische
Fehler auffallen: NULL-Werte, Gleichstand, Grenzwerte, Datensätze ohne Partner."""

import re
from dataclasses import dataclass
from datetime import date, timedelta

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, euro, schritte, tabelle

FORMELN = {
    "select": """- Aufbau: SELECT Spalten FROM Tabelle WHERE Bedingung ORDER BY Spalte [ASC | DESC]
- Vergleich: =, <>, <, <=, >, >=; „mindestens“ ist >=, „mehr als“ ist >
- LIKE: % steht für beliebig viele Zeichen, _ für genau eins; 'B%' beginnt mit B, '%City%' enthält City
- BETWEEN a AND b schließt beide Grenzen ein; IN ('a', 'b') statt mehrerer OR
- Fehlende Werte sind NULL: prüfen mit IS NULL bzw. IS NOT NULL, = NULL ist nie wahr
- DISTINCT entfernt doppelte Zeilen; Rechnen in der Spaltenliste: preis * 1.19 AS brutto
- Text und Datum in einfache Anführungszeichen: '2027-05-03'

*Beispiel:* SELECT name, ort FROM kunde WHERE ort IN ('Talheim', 'Seeburg') ORDER BY name;""",
    "join": """- INNER JOIN b ON b.schluessel = a.fremdschluessel: nur Zeilen mit Partner
- LEFT JOIN: alle Zeilen der linken Tabelle, ohne Partner stehen rechts NULL; ohne Partner finden: … WHERE b.schluessel IS NULL oder NOT IN (SELECT …)
- Aggregatfunktionen: COUNT(*) zählt Zeilen, COUNT(spalte) nur Werte ungleich NULL, SUM, AVG, MIN, MAX
- GROUP BY: jede Spalte der Ausgabe, die nicht aggregiert ist; WHERE filtert Zeilen vor dem Gruppieren, HAVING danach die Gruppen
- Unterabfrage: WHERE preis > (SELECT AVG(preis) FROM artikel)
- Reihenfolge: SELECT … FROM … JOIN … WHERE … GROUP BY … HAVING … ORDER BY …

*Beispiel:* SELECT k.name, COUNT(a.ausleihe_nr) FROM kunde k LEFT JOIN ausleihe a ON a.kunden_nr = k.kunden_nr GROUP BY k.kunden_nr, k.name; zählt Kunden ohne Ausleihe mit 0""",
    "aendern": """- INSERT INTO tabelle (spalte1, spalte2) VALUES (wert1, wert2); ein fehlender Wert ist NULL, ohne Anführungszeichen
- UPDATE tabelle SET spalte = neuer Wert WHERE Bedingung; ohne WHERE ändert es jede Zeile
- Prozent: + 10 % ist preis * 1.1, − 10 % ist preis * 0.9
- DELETE FROM tabelle WHERE Bedingung; ohne WHERE ist die Tabelle danach leer
- CREATE TABLE name (spalte TYP [NOT NULL], …, PRIMARY KEY (spalte, …), FOREIGN KEY (spalte) REFERENCES andere (spalte))
- Datentypen hier INTEGER, REAL, TEXT; in der Prüfung auch INT, DECIMAL(8,2), VARCHAR(50), DATE

*Beispiel:* UPDATE artikel SET preis = preis * 1.05 WHERE kategorie = 'Papier';""",
    "ermodell": """- Jede Entität wird eine Tabelle mit eigenem Primärschlüssel
- 1 : n: der Primärschlüssel der 1-Seite kommt als Fremdschlüssel in die Tabelle der n-Seite
- 1 : 1: der Fremdschlüssel kommt in die Tabelle der Seite, die genau einen Partner hat (die andere darf ohne sein), mit UNIQUE
- n : m: eigene Zwischentabelle mit beiden Fremdschlüsseln, zusammen bilden sie ihren Primärschlüssel
- Tabellen = Entitäten + n:m-Beziehungen; Fremdschlüssel = je 1:n- und 1:1-Beziehung einer, je n:m-Beziehung zwei

*Beispiel:* Kunde 1 : n Auftrag, Auftrag n : m Artikel → kunde, auftrag (kunden_nr → kunde), artikel, auftrag_artikel = 4 Tabellen""",
    "normalform": """- 1. NF: jede Zelle enthält genau einen Wert (atomar), keine Wiederholungsgruppen
- 2. NF: 1. NF, und jede Nichtschlüsselspalte hängt vom ganzen Schlüssel ab, nicht nur von einem Teil; mit einspaltigem Schlüssel ist eine Tabelle in der 1. NF schon in der 2. NF
- 3. NF: 2. NF, und keine Nichtschlüsselspalte hängt von einer anderen Nichtschlüsselspalte ab (keine transitive Abhängigkeit)
- Zerlegen: je linke Seite einer Abhängigkeit eine Tabelle; ihr Schlüssel bleibt in der Ausgangstabelle als Fremdschlüssel
- Anomalien bei Redundanz: Einfügeanomalie (Neues lässt sich ohne fremden Schlüssel nicht erfassen), Änderungsanomalie (ein Wert steht mehrfach und wird nicht überall geändert), Löschanomalie (mit einer Zeile gehen andere Daten verloren)

*Beispiel:* position (bestell_nr, artikel_nr, bezeichnung, menge) mit artikel_nr → bezeichnung: 1. NF, nicht 2. NF; zerlegt in position (bestell_nr, artikel_nr, menge) und artikel (artikel_nr, bezeichnung)""",
}

# nur Themennamen zählen (rechnen.passende); nicht „JOIN“ (Joint Venture), nicht „ER-Modell“ (Client-Server-Modell)
THEMEN = {
    "select": ("SQL", "Datenbankabfrage", "Abfragesprache"),
    "join": ("SQL", "Joins", "Aggregatfunktion", "GROUP BY"),
    "aendern": ("SQL", "Datenmanipulation", "Datendefinition", "CREATE TABLE"),
    "ermodell": ("Entity-Relationship", "ER-Diagramm", "Datenbankmodell", "Datenmodell", "Relationenmodell", "Kardinalität"),
    "normalform": ("Normalisierung", "Normalform"),
}


# --- SQL: Szenarien ------------------------------------------------------------

@dataclass(frozen=True)
class Tabelle:
    name: str
    kurz: str  # Alias in Verknüpfungen
    spalten: tuple[str, ...]  # wie im CREATE TABLE, die erste ist der Primärschlüssel
    zeilen: tuple[tuple, ...]

    def spalte(self, i: int) -> str:
        return self.spalten[i].split()[0]

    def werte(self, i: int) -> list:
        return [z[i] for z in self.zeilen]


@dataclass(frozen=True)
class Szenario:
    """Drei Tabellen in festen Rollen, damit jede Vorlage zu jedem Szenario passt:
    wer: Schlüssel, Name, Merkmal (kommt mehrfach vor), optionale Angabe (teils NULL)
    was: Schlüssel, Bezeichnung, Kategorie, Preis
    vorgang: Schlüssel, → wer, → was, Datum, Menge, optionales Datum (NULL: noch offen)
    w: die Wörter für die Fragen; neu: Tabellen für CREATE TABLE (Name, wofür, Spalten mit pk, pflicht oder optional)."""
    wer: Tabelle
    was: Tabelle
    vorgang: Tabelle
    w: dict
    neu: tuple

    @property
    def tabellen(self) -> tuple[Tabelle, ...]:
        return self.wer, self.was, self.vorgang


# Je Szenario: zwei Datensätze ohne Vorgang (LEFT JOIN), ein Ding ohne Vorgang, Gleichstand bei Preis und Anzahl, NULL früh und spät
SZENARIEN = [
    Szenario(
        Tabelle("kunde", "k", ("kunden_nr INTEGER PRIMARY KEY", "name TEXT NOT NULL", "ort TEXT NOT NULL", "telefon TEXT"), (
            (1, "Brandt", "Talheim", "0170 0000101"), (2, "Yilmaz", "Bergdorf", None), (3, "Becker", "Talheim", "0170 0000103"),
            (4, "Nowak", "Seeburg", "0170 0000104"), (5, "Albers", "Bergdorf", None), (6, "Bauer", "Talheim", "0170 0000106"),
            (7, "Kraus", "Seeburg", "0170 0000107"), (8, "Schmitt", "Lindenau", None))),
        Tabelle("fahrrad", "f", ("rad_nr INTEGER PRIMARY KEY", "modell TEXT NOT NULL", "typ TEXT NOT NULL", "tagespreis REAL NOT NULL"), (
            (1, "City Classic", "Stadtrad", 9.0), (2, "City Comfort", "Stadtrad", 10.5), (3, "Trekking Tour", "Trekkingrad", 12.0),
            (4, "Trekking Pro", "Trekkingrad", 14.0), (5, "E-City Plus", "E-Bike", 24.0), (6, "E-Tour Max", "E-Bike", 28.0),
            (7, "Cargo Duo", "Lastenrad", 24.0), (8, "Flitzer 20", "Kinderrad", 6.0), (9, "Trekking Light", "Trekkingrad", 12.0))),
        Tabelle("ausleihe", "a", ("ausleihe_nr INTEGER PRIMARY KEY", "kunden_nr INTEGER NOT NULL REFERENCES kunde (kunden_nr)",
                                  "rad_nr INTEGER NOT NULL REFERENCES fahrrad (rad_nr)", "datum TEXT NOT NULL", "tage INTEGER NOT NULL",
                                  "rueckgabe TEXT"), (
            (1, 1, 3, "2027-05-03", 2, "2027-05-05"), (2, 2, 5, "2027-05-03", 1, "2027-05-04"), (3, 1, 1, "2027-05-07", 3, "2027-05-10"),
            (4, 3, 6, "2027-05-10", 2, None), (5, 4, 7, "2027-05-10", 1, "2027-05-11"), (6, 2, 2, "2027-05-14", 4, "2027-05-18"),
            (7, 5, 4, "2027-05-17", 2, None), (8, 1, 5, "2027-05-21", 1, "2027-05-22"), (9, 6, 9, "2027-05-21", 3, None),
            (10, 3, 3, "2027-05-24", 2, "2027-05-26"), (11, 4, 6, "2027-05-28", 1, None), (12, 2, 7, "2027-05-31", 2, "2027-06-02"))),
        dict(fuer="einen Fahrradverleih", wer="Kunden", wer_gen="des Kunden", je_wer="Kunde", wer_neu="einen neuen Kunden",
             name="Name", merkmal="Ort", angabe="Telefonnummer",
             was="Fahrräder", was_dat="Fahrrädern", was_gen="des Fahrrads", je_was="Fahrrad", text="Modell", text_akk="das Modell",
             kat="Typ", kats="Typen", kat_von="vom Typ", zahl="Tagespreis",
             vorgang="Ausleihe", vorgaenge="Ausleihen", datum="Ausleihdatum", leer="Rückgabedatum",
             offen="die noch nicht zurückgegeben sind", erledigt="die bereits zurückgegeben sind", umsatz="Tage · Tagespreis",
             rechnung=("Wochenpreis", "7 · Tagespreis", "tagespreis * 7", "wochenpreis"),
             anfaenge=("B",), teilwoerter=("City", "Trekking", "Tour"), neue_namen=("Ludwig", "Pohl", "Engel", "Kaya")),
        (("wartung", "die Wartungen der Fahrräder",
          (("wartung_nr", "INTEGER", "pk"), ("rad_nr", "INTEGER", "pflicht"), ("datum", "TEXT", "pflicht"), ("kosten", "REAL", "optional"))),
         ("merkliste", "die Fahrräder, die sich Kunden vormerken",
          (("kunden_nr", "INTEGER", "pk"), ("rad_nr", "INTEGER", "pk"), ("notiert_am", "TEXT", "optional"))))),
    Szenario(
        Tabelle("kunde", "k", ("kunden_nr INTEGER PRIMARY KEY", "name TEXT NOT NULL", "ort TEXT NOT NULL", "email TEXT"), (
            (1, "Stadtwerke Talheim", "Talheim", "it@stadtwerke-talheim.example"), (2, "Bäckerei Korn", "Bergdorf", None),
            (3, "Spedition Ott", "Seeburg", "info@ott.example"), (4, "Autohaus Lenz", "Talheim", "service@lenz.example"),
            (5, "Sanitär Seidel", "Bergdorf", None), (6, "Kanzlei Vogt", "Seeburg", "kanzlei@vogt.example"),
            (7, "Hotel Seeblick", "Seeburg", None), (8, "Gärtnerei Blum", "Lindenau", "blum@gaertnerei.example"))),
        Tabelle("kurs", "ku", ("kurs_nr INTEGER PRIMARY KEY", "titel TEXT NOT NULL", "bereich TEXT NOT NULL", "preis REAL NOT NULL"), (
            (1, "Excel Grundlagen", "Office", 390.0), (2, "Excel für Fortgeschrittene", "Office", 490.0),
            (3, "Netzwerk Grundlagen", "Netzwerk", 890.0), (4, "Firewall in der Praxis", "Sicherheit", 1290.0),
            (5, "Python Einstieg", "Programmierung", 990.0), (6, "Python für Datenanalyse", "Programmierung", 1290.0),
            (7, "Phishing erkennen", "Sicherheit", 290.0), (8, "SQL kompakt", "Programmierung", 690.0), (9, "WLAN planen", "Netzwerk", 890.0))),
        Tabelle("buchung", "b", ("buchung_nr INTEGER PRIMARY KEY", "kunden_nr INTEGER NOT NULL REFERENCES kunde (kunden_nr)",
                                 "kurs_nr INTEGER NOT NULL REFERENCES kurs (kurs_nr)", "datum TEXT NOT NULL", "plaetze INTEGER NOT NULL",
                                 "bezahlt_am TEXT"), (
            (1, 1, 1, "2027-03-01", 2, "2027-03-15"), (2, 2, 3, "2027-03-01", 3, None), (3, 3, 5, "2027-03-08", 1, "2027-03-19"),
            (4, 1, 7, "2027-03-12", 5, "2027-03-30"), (5, 4, 2, "2027-03-15", 1, "2027-04-02"), (6, 2, 4, "2027-03-22", 2, None),
            (7, 5, 6, "2027-03-29", 1, "2027-04-10"), (8, 3, 7, "2027-04-05", 4, None), (9, 2, 9, "2027-04-12", 2, "2027-04-20"),
            (10, 6, 1, "2027-04-12", 3, None), (11, 1, 3, "2027-04-19", 1, None))),
        dict(fuer="einen Schulungsanbieter", wer="Kunden", wer_gen="des Kunden", je_wer="Kunde", wer_neu="einen neuen Kunden",
             name="Name", merkmal="Ort", angabe="E-Mail-Adresse",
             was="Kurse", was_dat="Kursen", was_gen="des Kurses", je_was="Kurs", text="Titel", text_akk="den Titel",
             kat="Bereich", kats="Bereiche", kat_von="im Bereich", zahl="Preis",
             vorgang="Buchung", vorgaenge="Buchungen", datum="Buchungsdatum", leer="Zahlungsdatum",
             offen="die noch nicht bezahlt sind", erledigt="die bereits bezahlt sind", umsatz="Plätze · Preis",
             rechnung=("Bruttopreis", "Preis · 1,19", "preis * 1.19", "brutto"),
             anfaenge=("S",), teilwoerter=("Excel", "Python", "Grundlagen"), neue_namen=("Druckerei Haas", "Zahnarztpraxis Kern", "Brauerei Stern")),
        (("termin", "die Termine der Kurse",
          (("termin_nr", "INTEGER", "pk"), ("kurs_nr", "INTEGER", "pflicht"), ("beginn", "TEXT", "pflicht"), ("raum", "TEXT", "optional"))),
         ("warteliste", "Kunden auf der Warteliste ausgebuchter Kurse",
          (("kunden_nr", "INTEGER", "pk"), ("kurs_nr", "INTEGER", "pk"), ("plaetze", "INTEGER", "pflicht"))))),
    Szenario(
        Tabelle("tier", "t", ("tier_nr INTEGER PRIMARY KEY", "name TEXT NOT NULL", "tierart TEXT NOT NULL", "chip_nr TEXT"), (
            (1, "Bella", "Hund", "CH-4471"), (2, "Felix", "Katze", None), (3, "Bruno", "Hund", "CH-4473"), (4, "Luna", "Katze", "CH-4474"),
            (5, "Kiwi", "Wellensittich", None), (6, "Balu", "Hund", "CH-4476"), (7, "Momo", "Kaninchen", None), (8, "Nala", "Katze", "CH-4478"))),
        Tabelle("leistung", "l", ("leistung_nr INTEGER PRIMARY KEY", "bezeichnung TEXT NOT NULL", "bereich TEXT NOT NULL", "preis REAL NOT NULL"), (
            (1, "Impfung Grundimmunisierung", "Vorsorge", 45.0), (2, "Impfung Auffrischung", "Vorsorge", 35.0),
            (3, "Allgemeine Untersuchung", "Diagnostik", 25.0), (4, "Blutbild", "Diagnostik", 60.0), (5, "Röntgen", "Diagnostik", 85.0),
            (6, "Zahnsteinentfernung", "Zahnbehandlung", 120.0), (7, "Kastration", "Chirurgie", 180.0), (8, "Krallen kürzen", "Pflege", 15.0),
            (9, "Ultraschall", "Diagnostik", 85.0))),
        Tabelle("behandlung", "b", ("behandlung_nr INTEGER PRIMARY KEY", "tier_nr INTEGER NOT NULL REFERENCES tier (tier_nr)",
                                    "leistung_nr INTEGER NOT NULL REFERENCES leistung (leistung_nr)", "datum TEXT NOT NULL",
                                    "anzahl INTEGER NOT NULL", "abgerechnet_am TEXT"), (
            (1, 1, 1, "2027-02-01", 1, "2027-02-05"), (2, 2, 3, "2027-02-01", 1, None), (3, 3, 4, "2027-02-08", 1, "2027-02-12"),
            (4, 1, 3, "2027-02-15", 1, "2027-02-19"), (5, 4, 6, "2027-02-15", 1, None), (6, 5, 3, "2027-02-22", 1, "2027-02-26"),
            (7, 6, 5, "2027-03-01", 2, None), (8, 2, 7, "2027-03-08", 1, "2027-03-12"), (9, 3, 9, "2027-03-08", 1, None),
            (10, 1, 2, "2027-03-15", 2, "2027-03-19"), (11, 6, 4, "2027-03-22", 1, None))),
        dict(fuer="eine Tierarztpraxis", wer="Tiere", wer_gen="des Tiers", je_wer="Tier", wer_neu="ein neues Tier",
             name="Name", merkmal="Tierart", angabe="Chipnummer",
             was="Leistungen", was_dat="Leistungen", was_gen="der Leistung", je_was="Leistung", text="Bezeichnung", text_akk="die Bezeichnung",
             kat="Bereich", kats="Bereiche", kat_von="im Bereich", zahl="Preis",
             vorgang="Behandlung", vorgaenge="Behandlungen", datum="Behandlungsdatum", leer="Abrechnungsdatum",
             offen="die noch nicht abgerechnet sind", erledigt="die bereits abgerechnet sind", umsatz="Anzahl · Preis",
             rechnung=("Preis zum doppelten Satz", "Preis · 2", "preis * 2", "doppelt"),
             anfaenge=("B",), teilwoerter=("Impfung", "Untersuchung"), neue_namen=("Paul", "Frieda", "Tiger", "Lotte")),
        (("gewicht", "das bei jedem Besuch gemessene Gewicht der Tiere",
          (("messung_nr", "INTEGER", "pk"), ("tier_nr", "INTEGER", "pflicht"), ("datum", "TEXT", "pflicht"), ("kg", "REAL", "pflicht"))),
         ("unvertraeglichkeit", "Leistungen, die ein Tier nicht verträgt",
          (("tier_nr", "INTEGER", "pk"), ("leistung_nr", "INTEGER", "pk"), ("hinweis", "TEXT", "optional"))))),
    Szenario(
        Tabelle("kunde", "k", ("kunden_nr INTEGER PRIMARY KEY", "name TEXT NOT NULL", "ort TEXT NOT NULL", "email TEXT"), (
            (1, "Hoffmann", "Seeburg", "hoffmann@mail.example"), (2, "Weber", "Talheim", None), (3, "Wagner", "Seeburg", "wagner@mail.example"),
            (4, "Krüger", "Lindenau", "krueger@mail.example"), (5, "Wolf", "Talheim", None), (6, "Lange", "Bergdorf", "lange@mail.example"),
            (7, "Peters", "Seeburg", None), (8, "Winter", "Talheim", "winter@mail.example"))),
        Tabelle("artikel", "a", ("artikel_nr INTEGER PRIMARY KEY", "bezeichnung TEXT NOT NULL", "kategorie TEXT NOT NULL", "preis REAL NOT NULL"), (
            (1, "Kopierpapier A4", "Papier", 4.99), (2, "Kopierpapier A3", "Papier", 9.49), (3, "Notizblock A5", "Papier", 1.99),
            (4, "Kugelschreiber 10er", "Schreibwaren", 3.49), (5, "Textmarker 4er", "Schreibwaren", 3.49), (6, "Ordner A4 breit", "Ablage", 2.79),
            (7, "Druckerpatrone schwarz", "Technik", 24.9), (8, "USB-Stick 64 GB", "Technik", 9.49), (9, "Tischlocher", "Ablage", 12.9))),
        Tabelle("bestellung", "b", ("bestell_nr INTEGER PRIMARY KEY", "kunden_nr INTEGER NOT NULL REFERENCES kunde (kunden_nr)",
                                    "artikel_nr INTEGER NOT NULL REFERENCES artikel (artikel_nr)", "datum TEXT NOT NULL",
                                    "menge INTEGER NOT NULL", "versand_am TEXT"), (
            (1, 1, 1, "2027-06-01", 5, "2027-06-02"), (2, 2, 4, "2027-06-01", 2, None), (3, 1, 7, "2027-06-04", 1, "2027-06-05"),
            (4, 3, 1, "2027-06-07", 10, "2027-06-08"), (5, 4, 6, "2027-06-07", 6, "2027-06-09"), (6, 2, 5, "2027-06-10", 3, "2027-06-11"),
            (7, 5, 2, "2027-06-14", 2, None), (8, 1, 3, "2027-06-14", 20, "2027-06-16"), (9, 3, 8, "2027-06-18", 1, None),
            (10, 6, 7, "2027-06-21", 2, None), (11, 2, 1, "2027-06-25", 4, None))),
        dict(fuer="einen Onlineshop für Büromaterial", wer="Kunden", wer_gen="des Kunden", je_wer="Kunde", wer_neu="einen neuen Kunden",
             name="Name", merkmal="Ort", angabe="E-Mail-Adresse",
             was="Artikel", was_dat="Artikeln", was_gen="des Artikels", je_was="Artikel", text="Bezeichnung", text_akk="die Bezeichnung",
             kat="Kategorie", kats="Kategorien", kat_von="der Kategorie", zahl="Preis",
             vorgang="Bestellung", vorgaenge="Bestellungen", datum="Bestelldatum", leer="Versanddatum",
             offen="die noch nicht versandt sind", erledigt="die bereits versandt sind", umsatz="Menge · Preis",
             rechnung=("Rabattpreis", "Preis · 0,95", "preis * 0.95", "rabattpreis"),
             anfaenge=("W",), teilwoerter=("Kopierpapier", "A4"), neue_namen=("Schuster", "Vogel", "Arnold", "Franke")),
        (("bewertung", "die Bewertungen der Artikel",
          (("bewertung_nr", "INTEGER", "pk"), ("artikel_nr", "INTEGER", "pflicht"), ("kunden_nr", "INTEGER", "optional"),
           ("sterne", "INTEGER", "pflicht"), ("kommentar", "TEXT", "optional"))),
         ("merkliste", "die Artikel auf der Merkliste der Kunden",
          (("kunden_nr", "INTEGER", "pk"), ("artikel_nr", "INTEGER", "pk"), ("menge", "INTEGER", "optional"))))),
    Szenario(
        Tabelle("besucher", "be", ("besucher_nr INTEGER PRIMARY KEY", "name TEXT NOT NULL", "ort TEXT NOT NULL", "telefon TEXT"), (
            (1, "Meier", "Talheim", "0170 0000201"), (2, "Schulz", "Seeburg", "0170 0000202"), (3, "Fischer", "Talheim", None),
            (4, "Schäfer", "Bergdorf", "0170 0000204"), (5, "Klein", "Seeburg", None), (6, "Schröder", "Talheim", "0170 0000206"),
            (7, "Roth", "Lindenau", None), (8, "Simon", "Seeburg", "0170 0000208"))),
        Tabelle("vorstellung", "v", ("vorstellung_nr INTEGER PRIMARY KEY", "titel TEXT NOT NULL", "genre TEXT NOT NULL", "preis REAL NOT NULL"), (
            (1, "Kalter Kaffee", "Komödie", 24.0), (2, "Die Nacht am Fluss", "Drama", 32.0), (3, "Funkenflug", "Musical", 45.0),
            (4, "Kleiner Drache Fips", "Kinderstück", 12.0), (5, "Pfeffer und Salz", "Komödie", 24.0), (6, "Die Nacht der Diebe", "Drama", 28.0),
            (7, "Sternenstaub", "Musical", 39.0), (8, "Die Hafenbande", "Kinderstück", 12.0), (9, "Das Erbe der Tante Ilse", "Komödie", 18.0))),
        Tabelle("reservierung", "r", ("reservierung_nr INTEGER PRIMARY KEY", "besucher_nr INTEGER NOT NULL REFERENCES besucher (besucher_nr)",
                                      "vorstellung_nr INTEGER NOT NULL REFERENCES vorstellung (vorstellung_nr)", "datum TEXT NOT NULL",
                                      "plaetze INTEGER NOT NULL", "abgeholt_am TEXT"), (
            (1, 1, 3, "2027-09-01", 2, "2027-09-10"), (2, 2, 1, "2027-09-01", 4, None), (3, 3, 2, "2027-09-03", 2, "2027-09-12"),
            (4, 1, 4, "2027-09-06", 3, "2027-09-20"), (5, 4, 7, "2027-09-06", 2, "2027-09-25"), (6, 2, 6, "2027-09-09", 1, None),
            (7, 5, 3, "2027-09-13", 2, "2027-09-27"), (8, 1, 5, "2027-09-15", 2, None), (9, 6, 2, "2027-09-15", 6, None),
            (10, 3, 1, "2027-09-20", 1, "2027-09-28"), (11, 2, 7, "2027-09-24", 2, None))),
        dict(fuer="den Kartenvorverkauf eines Theaters", wer="Besucher", wer_gen="des Besuchers", je_wer="Besucher",
             wer_neu="einen neuen Besucher", name="Name", merkmal="Ort", angabe="Telefonnummer",
             was="Vorstellungen", was_dat="Vorstellungen", was_gen="der Vorstellung", je_was="Vorstellung", text="Titel",
             text_akk="den Titel", kat="Genre", kats="Genres", kat_von="des Genres", zahl="Preis",
             vorgang="Reservierung", vorgaenge="Reservierungen", datum="Reservierungsdatum", leer="Abholdatum",
             offen="deren Karten noch nicht abgeholt sind", erledigt="deren Karten bereits abgeholt sind", umsatz="Plätze · Preis",
             rechnung=("ermäßigten Preis", "Preis · 0,5", "preis * 0.5", "ermaessigt"),
             anfaenge=("Sch", "S"), teilwoerter=("Nacht",), neue_namen=("Hartmann", "Busch", "Jung", "Kühn")),
        (("termin", "die Spieltermine der Vorstellungen",
          (("termin_nr", "INTEGER", "pk"), ("vorstellung_nr", "INTEGER", "pflicht"), ("beginn", "TEXT", "pflicht"), ("saal", "TEXT", "optional"))),
         ("warteliste", "Besucher auf der Warteliste ausverkaufter Vorstellungen",
          (("besucher_nr", "INTEGER", "pk"), ("vorstellung_nr", "INTEGER", "pk"), ("eingetragen_am", "TEXT", "pflicht"))))),
]


def _q(wert) -> str:
    """Wert als SQL-Literal."""
    if wert is None:
        return "NULL"
    if isinstance(wert, str):
        return "'" + wert.replace("'", "''") + "'"
    return str(wert) if isinstance(wert, int) else f"{wert:g}"


def _de_datum(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d.%m.%Y")


def _sandbox(s: Szenario) -> tuple[str, str]:
    ddl = "\n".join(f"CREATE TABLE {t.name} (\n    " + ",\n    ".join(t.spalten) + "\n);" for t in s.tabellen)
    daten = "\n".join(f"INSERT INTO {t.name} VALUES\n" + ",\n".join("    (" + ", ".join(map(_q, z)) + ")" for z in t.zeilen) + ";"
                      for t in s.tabellen)
    return ddl, daten


def _schema(s: Szenario) -> str:
    def spalte(definition: str) -> str:
        name, ziel = definition.split()[0], re.search(r"REFERENCES (\w+)", definition)
        return f"**{name}**" if "PRIMARY KEY" in definition else f"{name} → {ziel[1]}" if ziel else name
    return "\n".join(f"- `{t.name}` ({', '.join(map(spalte, t.spalten))})" for t in s.tabellen)


def _sql_aufgabe(rng, vorlagen) -> Aufgabe:
    """Szenario und Vorlage auswürfeln; eine Vorlage (rng, s) liefert (Titel, Auftrag, Musterlösung, Erklärung in Schritten)."""
    s = rng.choice(SZENARIEN)
    titel, auftrag, loesung, erklaerung = rng.choice(vorlagen)(rng, s)
    frage = (f"Die {rng.choice(FIRMEN)} entwickelt für {s.w['fuer']} eine Datenbank mit diesen Tabellen (Primärschlüssel **fett**, "
             f"Fremdschlüssel mit →):\n\n{_schema(s)}\n\nDatumswerte stehen als Text im Format JJJJ-MM-TT, z. B. '2027-05-03'. "
             f"„Tabellen ansehen“ zeigt die Beispieldaten.\n\nErstellen Sie eine SQL-Anweisung, die {auftrag}")
    weg = f"Musterlösung:\n\n```sql\n{loesung}\n```\n\n" + schritte(*erklaerung)
    return Aufgabe(frage, [Feld("sql", "SQL-Anweisung", loesung, typ="sql")], weg, titel=titel, sandbox=_sandbox(s))


def _grenzen(rng, werte: list) -> tuple:
    """Zwei vorkommende Grenzen aus den sortierten Werten, mit Werten darunter und darüber: Grenzfehler fallen auf."""
    i = rng.randint(1, len(werte) // 2 - 1)
    return werte[i], werte[rng.randint(i + 1, len(werte) - 2)]


# --- SQL: Abfragen -------------------------------------------------------------

def _a_vergleich(rng, s):
    o, w = s.was, s.w
    text, zahl = o.spalte(1), o.spalte(3)
    werte = sorted(set(o.werte(3)))
    op, wort = rng.choice([(">=", "mindestens"), ("<=", "höchstens"), (">", "mehr als"), ("<", "weniger als")])
    x = rng.choice(werte[1:-1])  # vorkommender Wert: ob die Grenze dazugehört, macht einen Unterschied
    return ("Vergleich", f"{w['text']} und {w['zahl']} aller {w['was']} ausgibt, deren {w['zahl']} {wort} {euro(x)} beträgt.",
            f"SELECT {text}, {zahl}\nFROM {o.name}\nWHERE {zahl} {op} {_q(x)};",
            [f"FROM {o.name}: die Tabelle der {w['was']}",
             f"WHERE {zahl} {op} {_q(x)}: „{wort}“ heißt {op}, die Grenze {_q(x)} gehört {'' if '=' in op else 'nicht '}dazu",
             f"SELECT {text}, {zahl}: nur die verlangten Spalten"])


def _a_like(rng, s):
    w = s.w
    if rng.random() < 0.5:
        t, spalten, wer = s.wer, (1, 2), f"{w['name']} und {w['merkmal']} aller {w['wer']}"
        anfang = rng.choice(w["anfaenge"])
        muster, wie, label = f"{anfang}%", f"mit „{anfang}“ beginnt", w["name"]
        bedeutung = f"zuerst {anfang}, danach beliebig viel"
    else:
        t, spalten, wer = s.was, (1, 3), f"{w['text']} und {w['zahl']} aller {w['was']}"
        wort = rng.choice(w["teilwoerter"])
        muster, wie, label = f"%{wort}%", f"„{wort}“ enthält", w["text"]
        bedeutung = f"{wort} an beliebiger Stelle, davor und dahinter beliebig viel"
    a, b = (t.spalte(i) for i in spalten)
    return ("Muster mit LIKE", f"{wer} ausgibt, deren {label} {wie}.", f"SELECT {a}, {b}\nFROM {t.name}\nWHERE {a} LIKE '{muster}';",
            ["LIKE vergleicht mit einem Muster: % steht für beliebig viele Zeichen (auch keins), _ für genau eins",
             f"'{muster}': {bedeutung}", "= fände nur den genauen Text"])


def _a_between(rng, s):
    w = s.w
    if rng.random() < 0.5:
        v = s.vorgang
        von, bis = _grenzen(rng, sorted(set(v.werte(3))))
        return ("Bereich mit BETWEEN",
                f"Nummer und {w['datum']} aller {w['vorgaenge']} vom {_de_datum(von)} bis zum {_de_datum(bis)} (jeweils einschließlich) ausgibt.",
                f"SELECT {v.spalte(0)}, {v.spalte(3)}\nFROM {v.name}\nWHERE {v.spalte(3)} BETWEEN '{von}' AND '{bis}';",
                ["BETWEEN a AND b schließt beide Grenzen ein, wie >= a AND <= b",
                 "Datumswerte im Format JJJJ-MM-TT lassen sich als Text vergleichen und sortieren"])
    o = s.was
    von, bis = _grenzen(rng, sorted(set(o.werte(3))))
    return ("Bereich mit BETWEEN",
            f"{w['text']} und {w['zahl']} aller {w['was']} ausgibt, deren {w['zahl']} zwischen {euro(von)} und {euro(bis)} liegt "
            "(Grenzen eingeschlossen).",
            f"SELECT {o.spalte(1)}, {o.spalte(3)}\nFROM {o.name}\nWHERE {o.spalte(3)} BETWEEN {_q(von)} AND {_q(bis)};",
            ["BETWEEN a AND b schließt beide Grenzen ein, wie >= a AND <= b", f"Die Grenzen {_q(von)} und {_q(bis)} kommen in den Daten vor"])


def _a_in(rng, s):
    w = s.w
    if rng.random() < 0.5:
        t, spalten, label, wer = s.was, (1, 3), w["kat"], f"{w['text']} und {w['zahl']} aller {w['was']}"
    else:
        t, spalten, label, wer = s.wer, (1, 2), w["merkmal"], f"{w['name']} und {w['merkmal']} aller {w['wer']}"
    a, b = sorted(rng.sample(sorted(set(t.werte(2))), 2))
    spalte = t.spalte(2)
    return ("Liste mit IN", f"{wer} ausgibt, deren {label} „{a}“ oder „{b}“ ist.",
            f"SELECT {t.spalte(spalten[0])}, {t.spalte(spalten[1])}\nFROM {t.name}\nWHERE {spalte} IN ('{a}', '{b}');",
            [f"IN ('{a}', '{b}') ist kürzer als {spalte} = '{a}' OR {spalte} = '{b}', beides ist richtig",
             "Text steht in einfachen Anführungszeichen und muss genau stimmen"])


def _a_null(rng, s):
    w, mit = s.w, rng.random() < 0.35
    nicht = "NOT " if mit else ""
    if rng.random() < 0.5:
        t = s.wer
        auftrag = f"{w['name']} und {w['merkmal']} aller {w['wer']} {'mit' if mit else 'ohne'} {w['angabe']} ausgibt."
        sql = f"SELECT {t.spalte(1)}, {t.spalte(2)}\nFROM {t.name}\nWHERE {t.spalte(3)} IS {nicht}NULL;"
    else:
        t = s.vorgang
        auftrag = f"Nummer und {w['datum']} aller {w['vorgaenge']} ausgibt, {w['erledigt' if mit else 'offen']}."
        sql = f"SELECT {t.spalte(0)}, {t.spalte(3)}\nFROM {t.name}\nWHERE {t.spalte(5)} IS {nicht}NULL;"
    return ("Fehlende Werte", auftrag, sql,
            [f"Fehlt ein Wert, steht in {t.spalte(5 if t is s.vorgang else 3)} NULL",
             f"Prüfen geht nur mit IS {nicht}NULL; {'<> NULL' if mit else '= NULL'} ist nie wahr und liefert keine Zeile"])


def _a_sortiert(rng, s):
    w = s.w
    if rng.random() < 0.6:
        o, ab = s.was, rng.random() < 0.6
        text, kat, zahl = o.spalte(1), o.spalte(2), o.spalte(3)
        return ("Sortieren",
                f"{w['text']}, {w['kat']} und {w['zahl']} aller {w['was']} ausgibt, {'absteigend' if ab else 'aufsteigend'} nach "
                f"{w['zahl']} sortiert, bei Gleichstand alphabetisch nach {w['text']}.",
                f"SELECT {text}, {kat}, {zahl}\nFROM {o.name}\nORDER BY {zahl}{' DESC' if ab else ''}, {text};",
                [f"ORDER BY sortiert aufsteigend (ASC), DESC dreht um{'' if ab else '; ASC darf man weglassen'}",
                 f"Die zweite Spalte in ORDER BY entscheidet nur bei gleichem {w['zahl']}: hier gibt es Gleichstand"])
    p = s.wer
    return ("Sortieren", f"{w['name']} und {w['merkmal']} aller {w['wer']} ausgibt, zuerst nach {w['merkmal']}, dann nach {w['name']} "
            "alphabetisch sortiert.",
            f"SELECT {p.spalte(1)}, {p.spalte(2)}\nFROM {p.name}\nORDER BY {p.spalte(2)}, {p.spalte(1)};",
            [f"ORDER BY {p.spalte(2)}, {p.spalte(1)}: zuerst nach {p.spalte(2)}, bei gleichem Wert nach {p.spalte(1)}",
             "Ohne DESC wird aufsteigend sortiert, Text alphabetisch"])


def _a_distinct(rng, s):
    t = rng.choice([s.wer, s.was])
    spalte = t.spalte(2)
    if rng.random() < 0.6:
        return ("Ohne Doppelte", f"alle Werte der Spalte `{spalte}` der Tabelle `{t.name}` ohne Wiederholungen ausgibt, alphabetisch sortiert.",
                f"SELECT DISTINCT {spalte}\nFROM {t.name}\nORDER BY {spalte};",
                [f"DISTINCT streicht doppelte Zeilen aus dem Ergebnis; {spalte} kommt mehrfach vor", "ORDER BY sortiert alphabetisch"])
    return ("Ohne Doppelte", f"zählt, wie viele verschiedene Werte die Spalte `{spalte}` der Tabelle `{t.name}` enthält.",
            f"SELECT COUNT(DISTINCT {spalte}) AS anzahl\nFROM {t.name};",
            [f"COUNT(DISTINCT {spalte}) zählt jeden Wert nur einmal", f"COUNT({spalte}) zählte alle {len(t.zeilen)} Zeilen"])


def _a_rechnen(rng, s):
    o, w = s.was, s.w
    name, formel, ausdruck, alias = w["rechnung"]
    k = rng.choice(sorted(set(o.werte(2))))
    return ("Berechnete Spalte",
            f"für alle {w['was']} {w['kat_von']} „{k}“ {w['text']} und {name} ({formel}) ausgibt; die berechnete Spalte heißt {alias}.",
            f"SELECT {o.spalte(1)}, {ausdruck} AS {alias}\nFROM {o.name}\nWHERE {o.spalte(2)} = '{k}';",
            [f"Gerechnet wird direkt in der Spaltenliste: {ausdruck}", f"AS {alias} gibt der berechneten Spalte ihren Namen",
             "Dezimalzahlen schreibt SQL mit Punkt"])


@art("select", "SQL: Abfragen", "Datenbanken", "SELECT mit WHERE, LIKE, BETWEEN, IN, IS NULL, ORDER BY und DISTINCT, ausgeführt in der Sandbox",
     THEMEN["select"], formeln=FORMELN["select"], sprint=False)  # Sprint: 3 Minuten ohne Ausführen reichen für SQL nicht
def select(rng):
    return _sql_aufgabe(rng, [_a_vergleich, _a_like, _a_between, _a_in, _a_null, _a_sortiert, _a_distinct, _a_rechnen])


# --- SQL: Verknüpfen und Gruppieren --------------------------------------------

def _on(links: Tabelle, rechts: Tabelle, spalte: str) -> str:
    return f"{rechts.kurz}.{spalte} = {links.kurz}.{spalte}"


def _b_join(rng, s):
    w, v = s.w, s.vorgang
    d = rng.choice(sorted(set(v.werte(3)))[2:-2])
    if rng.random() < 0.5:
        t, spalte, was = s.wer, 1, f"den Namen {w['wer_gen']}"
    else:
        t, spalte, was = s.was, 1, f"{w['text_akk']} {w['was_gen']}"
    schluessel = t.spalte(0)
    return ("JOIN über zwei Tabellen", f"zu allen {w['vorgaenge']} ab dem {_de_datum(d)} (einschließlich) das {w['datum']} und {was} ausgibt.",
            f"SELECT {v.kurz}.{v.spalte(3)}, {t.kurz}.{t.spalte(spalte)}\nFROM {v.name} {v.kurz}\n"
            f"JOIN {t.name} {t.kurz} ON {_on(v, t, schluessel)}\nWHERE {v.kurz}.{v.spalte(3)} >= '{d}';",
            [f"JOIN … ON verbindet jede Zeile aus {v.name} mit der passenden aus {t.name}: Fremdschlüssel = Primärschlüssel ({schluessel})",
             f"WHERE … >= '{d}': „ab dem“ schließt den Tag ein", "Die Kürzel hinter den Tabellennamen sparen Schreibarbeit"])


def _b_join3(rng, s):
    w, p, o, v = s.w, s.wer, s.was, s.vorgang
    kategorie = dict(zip(o.werte(0), o.werte(2)))
    daten_je = {}
    for z in v.zeilen:
        daten_je.setdefault(kategorie[z[2]], set()).add(z[3])
    k = rng.choice(sorted(kat for kat, d in daten_je.items() if len(d) >= 2))
    return ("JOIN über drei Tabellen",
            f"zu allen {w['vorgaenge']} von {w['was_dat']} {w['kat_von']} „{k}“ den Namen {w['wer_gen']}, {w['text_akk']} {w['was_gen']} und das "
            f"{w['datum']} ausgibt, sortiert nach dem {w['datum']}.",
            f"SELECT {p.kurz}.{p.spalte(1)}, {o.kurz}.{o.spalte(1)}, {v.kurz}.{v.spalte(3)}\nFROM {v.name} {v.kurz}\n"
            f"JOIN {p.name} {p.kurz} ON {_on(v, p, p.spalte(0))}\nJOIN {o.name} {o.kurz} ON {_on(v, o, o.spalte(0))}\n"
            f"WHERE {o.kurz}.{o.spalte(2)} = '{k}'\nORDER BY {v.kurz}.{v.spalte(3)};",
            [f"{v.name} steht in der Mitte: zwei JOINs über die beiden Fremdschlüssel",
             f"WHERE filtert auf {o.spalte(2)} = '{k}' aus der verknüpften Tabelle {o.name}", "ORDER BY steht ganz am Ende"])


def _b_ohne(rng, s):
    w, v = s.w, s.vorgang
    if rng.random() < 0.55:
        t, ausgabe, auftrag = s.wer, (1, 2), f"{w['name']} und {w['merkmal']} aller {w['wer']} ausgibt, die noch keine {w['vorgang']} haben."
    else:
        t, ausgabe, auftrag = s.was, (1, 3), f"{w['text']} und {w['zahl']} aller {w['was']} ausgibt, die in keiner {w['vorgang']} vorkommen."
    schluessel = t.spalte(0)
    return ("Ohne Partner", auftrag,
            f"SELECT {t.kurz}.{t.spalte(ausgabe[0])}, {t.kurz}.{t.spalte(ausgabe[1])}\nFROM {t.name} {t.kurz}\n"
            f"LEFT JOIN {v.name} {v.kurz} ON {_on(t, v, schluessel)}\nWHERE {v.kurz}.{v.spalte(0)} IS NULL;",
            [f"LEFT JOIN behält jede Zeile aus {t.name}, auch ohne passende {w['vorgang']}; dann sind die Spalten von {v.name} NULL",
             f"WHERE {v.kurz}.{v.spalte(0)} IS NULL lässt genau diese übrig; ein INNER JOIN fände sie nie",
             f"Genauso richtig: WHERE {schluessel} NOT IN (SELECT {schluessel} FROM {v.name})"])


def _b_anzahl(rng, s):
    w, v = s.w, s.vorgang
    if rng.random() < 0.6:
        t, je, was, wer = s.wer, w["je_wer"], "den Namen", w["wer"]
    else:
        t, je, was, wer = s.was, w["je_was"], w["text_akk"], w["was"]
    sortiert = rng.random() < 0.4
    return ("Zählen mit LEFT JOIN",
            f"je {je} {was} und die Anzahl der {w['vorgaenge']} ausgibt{', absteigend nach der Anzahl' if sortiert else ''}; "
            f"{wer} ohne {w['vorgang']} erscheinen mit 0.",
            f"SELECT {t.kurz}.{t.spalte(1)}, COUNT({v.kurz}.{v.spalte(0)}) AS anzahl\nFROM {t.name} {t.kurz}\n"
            f"LEFT JOIN {v.name} {v.kurz} ON {_on(t, v, t.spalte(0))}\nGROUP BY {t.kurz}.{t.spalte(0)}, {t.kurz}.{t.spalte(1)}"
            + ("\nORDER BY anzahl DESC;" if sortiert else ";"),
            ["LEFT JOIN, sonst fallen die ohne Partner heraus",
             f"COUNT({v.kurz}.{v.spalte(0)}) zählt nur Werte ungleich NULL, also 0 ohne {w['vorgang']}; COUNT(*) zählte dort 1",
             f"GROUP BY über den Schlüssel {t.spalte(0)} und jede ausgegebene Spalte"])


def _b_gruppe(rng, s):
    o, w = s.was, s.w
    wort, funktion, alias = rng.choice([("den durchschnittlichen", "AVG", "durchschnitt"), ("den höchsten", "MAX", "hoechster"),
                                        ("den niedrigsten", "MIN", "niedrigster")])
    kat, zahl = o.spalte(2), o.spalte(3)
    return ("Gruppieren", f"je {w['kat']} die Anzahl der {w['was']} und {wort} {w['zahl']} ausgibt.",
            f"SELECT {kat}, COUNT(*) AS anzahl, {funktion}({zahl}) AS {alias}\nFROM {o.name}\nGROUP BY {kat};",
            [f"GROUP BY {kat}: eine Ergebniszeile je {w['kat']}", f"COUNT(*) zählt die Zeilen der Gruppe, {funktion}({zahl}) rechnet in der Gruppe",
             "Jede Spalte der Ausgabe ist gruppiert oder aggregiert"])


def _b_summe(rng, s):
    w, p, o, v = s.w, s.wer, s.was, s.vorgang
    produkt = f"{v.kurz}.{v.spalte(4)} * {o.kurz}.{o.spalte(3)}"
    join_o = f"JOIN {o.name} {o.kurz} ON {_on(v, o, o.spalte(0))}"
    if rng.random() < 0.5:
        return ("Summe über JOIN",
                f"je {w['je_wer']} mit mindestens einer {w['vorgang']} den Namen und den Umsatz ({w['umsatz']}) aller seiner "
                f"{w['vorgaenge']} ausgibt.",
                f"SELECT {p.kurz}.{p.spalte(1)}, SUM({produkt}) AS umsatz\nFROM {v.name} {v.kurz}\n"
                f"JOIN {p.name} {p.kurz} ON {_on(v, p, p.spalte(0))}\n{join_o}\nGROUP BY {p.kurz}.{p.spalte(0)}, {p.kurz}.{p.spalte(1)};",
                [f"Menge und Preis stehen in verschiedenen Tabellen: erst verknüpfen, dann SUM({produkt})",
                 f"GROUP BY je {w['je_wer']}; der INNER JOIN lässt die ohne {w['vorgang']} weg, wie verlangt"])
    return ("Summe über JOIN", f"je {w['kat']} den Umsatz ({w['umsatz']}) aller {w['vorgaenge']} ausgibt; {w['kats']} ohne "
            f"{w['vorgang']} entfallen.",
            f"SELECT {o.kurz}.{o.spalte(2)}, SUM({produkt}) AS umsatz\nFROM {v.name} {v.kurz}\n{join_o}\nGROUP BY {o.kurz}.{o.spalte(2)};",
            [f"Erst {v.name} mit {o.name} verknüpfen, dann je {o.spalte(2)} SUM({produkt})", "Ohne Partner entfällt die Gruppe beim INNER JOIN"])


def _b_having(rng, s):
    w, p, v = s.w, s.wer, s.vorgang
    anzahl = {}
    for z in v.zeilen:
        anzahl[z[1]] = anzahl.get(z[1], 0) + 1
    grenze = rng.choice([n for n in sorted(set(anzahl.values())) if n >= 2 and n > min(anzahl.values())])
    return ("Gruppen filtern mit HAVING",
            f"Name und Anzahl der {w['vorgaenge']} aller {w['wer']} mit mindestens {grenze} {w['vorgaenge']} ausgibt.",
            f"SELECT {p.kurz}.{p.spalte(1)}, COUNT(*) AS anzahl\nFROM {p.name} {p.kurz}\nJOIN {v.name} {v.kurz} ON {_on(p, v, p.spalte(0))}\n"
            f"GROUP BY {p.kurz}.{p.spalte(0)}, {p.kurz}.{p.spalte(1)}\nHAVING COUNT(*) >= {grenze};",
            ["WHERE filtert einzelne Zeilen vor dem Gruppieren, HAVING die fertigen Gruppen",
             f"„mindestens {grenze}“ heißt >= {grenze}; Gleichstand an der Grenze gehört dazu"])


def _b_unter(rng, s):
    o, w = s.was, s.w
    text, zahl = o.spalte(1), o.spalte(3)
    if rng.random() < 0.5:
        return ("Unterabfrage",
                f"{w['text']} und {w['zahl']} aller {w['was']} ausgibt, deren {w['zahl']} über dem Durchschnitt aller {w['was']} liegt.",
                f"SELECT {text}, {zahl}\nFROM {o.name}\nWHERE {zahl} > (SELECT AVG({zahl}) FROM {o.name});",
                [f"Die Unterabfrage in Klammern liefert einen Wert: den Durchschnitt aller {w['was']}",
                 "Aggregatfunktionen stehen nie direkt in WHERE, deshalb die Unterabfrage"])
    wort, funktion = rng.choice([("höchsten", "MAX"), ("niedrigsten", "MIN")])
    return ("Unterabfrage", f"{w['text']} und {w['zahl']} aller {w['was']} mit dem {wort} {w['zahl']} ausgibt; bei Gleichstand alle.",
            f"SELECT {text}, {zahl}\nFROM {o.name}\nWHERE {zahl} = (SELECT {funktion}({zahl}) FROM {o.name});",
            [f"Die Unterabfrage liefert den {wort} {w['zahl']}, WHERE vergleicht jede Zeile damit",
             "So kommen bei Gleichstand alle; ORDER BY mit LIMIT 1 zeigte nur eine Zeile"])


@art("join", "SQL: Verknüpfen und Gruppieren", "Datenbanken", "JOIN über zwei und drei Tabellen, LEFT JOIN, GROUP BY mit COUNT, SUM, AVG, "
     "HAVING und Unterabfragen", THEMEN["join"], formeln=FORMELN["join"], sprint=False)
def join(rng):
    return _sql_aufgabe(rng, [_b_join, _b_join3, _b_ohne, _b_anzahl, _b_gruppe, _b_summe, _b_having, _b_unter])


# --- SQL: Daten ändern ---------------------------------------------------------

def _werte_tabelle(t: Tabelle, zeile: tuple) -> str:
    return tabelle([t.spalte(i) for i in range(len(zeile))], [["NULL (leer)" if x is None else _q(x).strip("'") for x in zeile]])


def _insert(t: Tabelle, zeile: tuple) -> str:
    return f"INSERT INTO {t.name} ({', '.join(t.spalte(i) for i in range(len(zeile)))})\nVALUES ({', '.join(map(_q, zeile))});"


def _c_insert(rng, s):
    w = s.w
    erklaerung = ["Spaltenliste und VALUES in derselben Reihenfolge; die Spaltenliste darf fehlen, wenn alle Spalten in Tabellenreihenfolge kommen",
                  "Text in einfachen Anführungszeichen, Zahlen ohne; ein fehlender Wert ist NULL ohne Anführungszeichen ('NULL' wäre ein Text)"]
    if rng.random() < 0.5:
        p = s.wer
        zeile = (max(p.werte(0)) + 1, rng.choice(w["neue_namen"]), rng.choice(sorted(set(p.werte(2)))), None)
        return ("INSERT", f"{w['wer_neu']} mit diesen Werten anlegt (die {w['angabe']} ist noch unbekannt):\n\n{_werte_tabelle(p, zeile)}",
                _insert(p, zeile), erklaerung)
    v = s.vorgang
    datum = date.fromisoformat(max(v.werte(3))) + timedelta(days=rng.randint(1, 6))
    zeile = (max(v.werte(0)) + 1, rng.choice(s.wer.werte(0)), rng.choice(s.was.werte(0)), datum.isoformat(), rng.randint(1, 3), None)
    return ("INSERT", f"eine neue {w['vorgang']} mit diesen Werten erfasst:\n\n{_werte_tabelle(v, zeile)}", _insert(v, zeile), erklaerung)


def _c_update(rng, s):
    o, w = s.was, s.w
    k, zahl = rng.choice(sorted(set(o.werte(2)))), o.spalte(3)
    if rng.random() < 0.7:
        prozent, hoch = rng.choice([5, 10, 20]), rng.random() < 0.7
        faktor = 1 + prozent / 100 if hoch else 1 - prozent / 100
        auftrag, neu = f"um {prozent} % {'erhöht' if hoch else 'senkt'}", f"{zahl} * {faktor:g}"
        rechnung = f"{'+' if hoch else '−'} {prozent} % heißt mal {faktor:g}"
    else:
        plus = rng.choice([1, 2, 5])
        auftrag, neu, rechnung = f"um {euro(plus)} erhöht", f"{zahl} + {plus}", "Der neue Wert darf sich auf den alten beziehen"
    return ("UPDATE", f"den {w['zahl']} aller {w['was']} {w['kat_von']} „{k}“ {auftrag}.",
            f"UPDATE {o.name}\nSET {zahl} = {neu}\nWHERE {o.spalte(2)} = '{k}';",
            [f"SET {zahl} = {neu}: {rechnung}", f"WHERE {o.spalte(2)} = '{k}' – ohne WHERE änderte sich jede Zeile"])


def _c_update_einzeln(rng, s):
    w = s.w
    if rng.random() < 0.6:
        v = s.vorgang
        z = rng.choice([z for z in v.zeilen if z[5] is None])
        d = (date.fromisoformat(z[3]) + timedelta(days=rng.randint(2, 14))).isoformat()
        return ("UPDATE einer Zeile", f"bei der {w['vorgang']} Nr. {z[0]} als {w['leer']} den {_de_datum(d)} einträgt.",
                f"UPDATE {v.name}\nSET {v.spalte(5)} = '{d}'\nWHERE {v.spalte(0)} = {z[0]};",
                [f"Die Spalte {v.spalte(5)} ist noch NULL, UPDATE setzt den Wert", f"WHERE über den Primärschlüssel {v.spalte(0)} trifft genau eine Zeile",
                 "Das Datum im Format JJJJ-MM-TT, in Anführungszeichen"])
    o = s.was
    z = rng.choice(o.zeilen)
    neu = z[3] + rng.choice([-2, -1, 1, 2, 3]) * (0.5 if z[3] < 50 else 10)
    return ("UPDATE einer Zeile", f"den {w['zahl']} {w['was_gen']} Nr. {z[0]} („{z[1]}“) auf {euro(neu)} ändert.",
            f"UPDATE {o.name}\nSET {o.spalte(3)} = {_q(neu)}\nWHERE {o.spalte(0)} = {z[0]};",
            [f"SET {o.spalte(3)} = {_q(neu)}: Dezimalzahlen mit Punkt", f"WHERE über den Primärschlüssel {o.spalte(0)} trifft genau eine Zeile"])


def _c_delete(rng, s):
    w, v = s.w, s.vorgang
    fall = rng.choice(["alt", "wer", "was"])
    if fall == "alt":
        # Grenze so, dass davor Erledigtes und Offenes liegt: wer die Bedingung für NULL vergisst, löscht zu viel
        d = rng.choice([d for d in sorted(set(v.werte(3))) if {z[5] is None for z in v.zeilen if z[3] < d} == {True, False}])
        erledigt = w["erledigt"].removeprefix("die ")
        return ("DELETE", f"alle {w['vorgaenge']} vor dem {_de_datum(d)} löscht, {w['erledigt']}.",
                f"DELETE FROM {v.name}\nWHERE {v.spalte(3)} < '{d}'\n  AND {v.spalte(5)} IS NOT NULL;",
                [f"„vor dem“ heißt <, der Tag selbst bleibt", f"{erledigt[0].upper()}{erledigt[1:]}: {v.spalte(5)} ist gesetzt, also IS NOT NULL",
                 "Beide Bedingungen mit AND; ohne WHERE wäre die Tabelle leer"])
    t, wer = (s.wer, f"alle {w['wer']} löscht, die noch keine {w['vorgang']} haben.") if fall == "wer" else \
        (s.was, f"alle {w['was']} löscht, die in keiner {w['vorgang']} vorkommen.")
    schluessel = t.spalte(0)
    return ("DELETE", wer, f"DELETE FROM {t.name}\nWHERE {schluessel} NOT IN (SELECT {schluessel} FROM {v.name});",
            [f"Die Unterabfrage liefert alle {schluessel}, die in {v.name} vorkommen", "NOT IN lässt genau die übrig, die dort fehlen",
             "DELETE kennt keinen JOIN, die Unterabfrage ersetzt ihn"])


def _c_create(rng, s):
    name, wofuer, spalten = rng.choice(s.neu)
    ziele = {t.spalte(0): t.name for t in s.tabellen}
    pks = [c for c, _, e in spalten if e == "pk"]
    zeilen, kopf = [], []
    for c, typ, e in spalten:
        zeilen.append(f"{c} {typ}" + (" PRIMARY KEY" if e == "pk" and len(pks) == 1 else " NOT NULL" if e == "pflicht" else ""))
        eigenschaft = {"pk": "Primärschlüssel" if len(pks) == 1 else "Teil des Primärschlüssels", "pflicht": "Pflichtfeld",
                       "optional": "optional"}[e]
        kopf.append([c, typ, eigenschaft + (f", Fremdschlüssel auf {ziele[c]}" if c in ziele else "")])
    if len(pks) > 1:
        zeilen.append(f"PRIMARY KEY ({', '.join(pks)})")
    zeilen += [f"FOREIGN KEY ({c}) REFERENCES {ziele[c]} ({c})" for c, _, _ in spalten if c in ziele]
    return ("CREATE TABLE", f"die Tabelle `{name}` für {wofuer} anlegt:\n\n" + tabelle(["Spalte", "Datentyp", "Eigenschaft"], kopf),
            f"CREATE TABLE {name} (\n    " + ",\n    ".join(zeilen) + "\n);",
            ["Pflichtfelder bekommen NOT NULL, optionale nichts",
             "Ein zusammengesetzter Primärschlüssel steht als PRIMARY KEY (…) am Ende" if len(pks) > 1 else
             "PRIMARY KEY direkt hinter der Spalte oder als PRIMARY KEY (…) am Ende",
             "FOREIGN KEY (spalte) REFERENCES tabelle (spalte) verweist auf den Primärschlüssel der anderen Tabelle",
             "Saku prüft Spaltennamen, Primär- und Fremdschlüssel und NOT NULL; Datentypen wie INT oder VARCHAR(50) gehen auch"])


@art("aendern", "SQL: Daten ändern", "Datenbanken", "INSERT, UPDATE (auch mit Berechnung), DELETE und CREATE TABLE mit Schlüsseln, "
     "geprüft am Tabellenstand", THEMEN["aendern"], formeln=FORMELN["aendern"], sprint=False)
def aendern(rng):
    return _sql_aufgabe(rng, [_c_insert, _c_update, _c_update_einzeln, _c_delete, _c_create])


# --- ER-Modell → Tabellen -----------------------------------------------------

# (Titel, für wen, Entität: (Tabelle, Schlüssel), je Beziehung die Varianten (A, B, Kardinalität A : B, Satz)).
# 1:n und 1:1: der Fremdschlüssel steht in B (bei 1:1 die Seite mit genau einem Partner); n:m braucht eine Zwischentabelle.
ER = [
    ("Hausverwaltung", "eine Hausverwaltung",
     {"Haus": ("haus", "haus_nr"), "Wohnung": ("wohnung", "wohnung_nr"), "Mieter": ("mieter", "mieter_nr"),
      "Handwerker": ("handwerker", "handwerker_nr")},
     [[("Haus", "Wohnung", "1:n", "Ein Haus hat mehrere Wohnungen; jede Wohnung liegt in genau einem Haus.")],
      [("Wohnung", "Mieter", "1:n", "In einer Wohnung können mehrere Mieter wohnen; jeder Mieter wohnt in genau einer Wohnung."),
       ("Wohnung", "Mieter", "1:1", "Eine Wohnung hat höchstens einen Mieter; jeder Mieter mietet genau eine Wohnung.")],
      [("Haus", "Handwerker", "n:m", "Für ein Haus arbeiten mehrere Handwerker, und ein Handwerker arbeitet für mehrere Häuser."),
       ("Handwerker", "Haus", "1:n", "Ein Handwerker betreut mehrere Häuser; jedes Haus wird von genau einem Handwerker betreut.")]]),
    ("Sportverein", "einen Sportverein",
     {"Mitglied": ("mitglied", "mitglied_nr"), "Mannschaft": ("mannschaft", "mannschaft_nr"), "Trainer": ("trainer", "trainer_nr"),
      "Halle": ("halle", "halle_nr")},
     [[("Mannschaft", "Mitglied", "n:m", "Ein Mitglied kann in mehreren Mannschaften spielen, und eine Mannschaft hat mehrere Mitglieder."),
       ("Mannschaft", "Mitglied", "1:n", "Eine Mannschaft hat mehrere Mitglieder; jedes Mitglied spielt in genau einer Mannschaft.")],
      [("Trainer", "Mannschaft", "1:n", "Ein Trainer betreut mehrere Mannschaften; jede Mannschaft hat genau einen Trainer."),
       ("Trainer", "Mannschaft", "1:1", "Ein Trainer betreut höchstens eine Mannschaft; jede Mannschaft hat genau einen Trainer.")],
      [("Halle", "Mannschaft", "1:n", "In einer Halle trainieren mehrere Mannschaften; jede Mannschaft trainiert in genau einer Halle."),
       ("Halle", "Mannschaft", "n:m", "Eine Mannschaft trainiert in mehreren Hallen, und in einer Halle trainieren mehrere Mannschaften.")]]),
    ("Kfz-Werkstatt", "eine Kfz-Werkstatt",
     {"Kunde": ("kunde", "kunden_nr"), "Fahrzeug": ("fahrzeug", "fahrzeug_nr"), "Auftrag": ("auftrag", "auftrag_nr"),
      "Mechaniker": ("mechaniker", "mechaniker_nr"), "Ersatzteil": ("ersatzteil", "teil_nr")},
     [[("Kunde", "Fahrzeug", "1:n", "Ein Kunde kann mehrere Fahrzeuge besitzen; jedes Fahrzeug gehört genau einem Kunden.")],
      [("Fahrzeug", "Auftrag", "1:n", "Zu einem Fahrzeug gibt es mehrere Werkstattaufträge; jeder Auftrag betrifft genau ein Fahrzeug.")],
      [("Mechaniker", "Auftrag", "1:n", "Ein Mechaniker bearbeitet mehrere Aufträge; jeder Auftrag wird von genau einem Mechaniker bearbeitet."),
       ("Auftrag", "Mechaniker", "n:m", "An einem Auftrag arbeiten mehrere Mechaniker, und ein Mechaniker arbeitet an mehreren Aufträgen.")],
      [("Auftrag", "Ersatzteil", "n:m", "In einem Auftrag werden mehrere Ersatzteile verbaut, und ein Ersatzteil kommt in vielen Aufträgen vor.")]]),
    ("Hotel", "ein Hotel",
     {"Gast": ("gast", "gast_nr"), "Buchung": ("buchung", "buchung_nr"), "Zimmer": ("zimmer", "zimmer_nr"),
      "Kategorie": ("kategorie", "kategorie_nr")},
     [[("Gast", "Buchung", "1:n", "Ein Gast kann mehrere Buchungen haben; jede Buchung gehört zu genau einem Gast.")],
      [("Buchung", "Zimmer", "n:m", "Eine Buchung kann mehrere Zimmer umfassen, und ein Zimmer kommt in vielen Buchungen vor."),
       ("Zimmer", "Buchung", "1:n", "Jede Buchung gilt für genau ein Zimmer; ein Zimmer wird in vielen Buchungen gebucht.")],
      [("Kategorie", "Zimmer", "1:n", "Jedes Zimmer gehört zu genau einer Kategorie (z. B. Einzelzimmer); zu einer Kategorie gehören mehrere Zimmer.")]]),
    ("Berufsschule", "eine Berufsschule",
     {"Betrieb": ("betrieb", "betrieb_nr"), "Azubi": ("azubi", "azubi_nr"), "Klasse": ("klasse", "klasse_nr"),
      "Lehrkraft": ("lehrkraft", "lehrkraft_nr")},
     [[("Betrieb", "Azubi", "1:n", "Ein Ausbildungsbetrieb bildet mehrere Azubis aus; jeder Azubi hat genau einen Ausbildungsbetrieb.")],
      [("Klasse", "Azubi", "1:n", "Eine Klasse hat mehrere Azubis; jeder Azubi ist in genau einer Klasse.")],
      [("Lehrkraft", "Klasse", "n:m", "Eine Lehrkraft unterrichtet mehrere Klassen, und eine Klasse hat mehrere Lehrkräfte."),
       ("Lehrkraft", "Klasse", "1:1", "Jede Klasse hat genau eine Lehrkraft als Klassenleitung; eine Lehrkraft leitet höchstens eine Klasse.")]]),
    ("IT-Support", "den IT-Support eines Unternehmens",
     {"Abteilung": ("abteilung", "abteilung_nr"), "Mitarbeiter": ("mitarbeiter", "personal_nr"), "Ticket": ("ticket", "ticket_nr"),
      "Gerät": ("geraet", "inventar_nr")},
     [[("Abteilung", "Mitarbeiter", "1:n", "Eine Abteilung hat mehrere Mitarbeiter; jeder Mitarbeiter gehört zu genau einer Abteilung.")],
      [("Mitarbeiter", "Ticket", "1:n", "Ein Mitarbeiter meldet mehrere Tickets; jedes Ticket wird von genau einem Mitarbeiter gemeldet.")],
      [("Ticket", "Gerät", "n:m", "Ein Ticket kann mehrere Geräte betreffen, und zu einem Gerät gibt es mehrere Tickets."),
       ("Gerät", "Ticket", "1:n", "Jedes Ticket betrifft genau ein Gerät; zu einem Gerät gibt es mehrere Tickets.")],
      [("Mitarbeiter", "Gerät", "1:n", "Einem Mitarbeiter sind mehrere Geräte zugeordnet; jedes Gerät gehört genau einem Mitarbeiter.")]]),
]

KARDINALITAETEN = ["1 : 1", "1 : n", "n : 1", "n : m"]
ZWISCHENTABELLE = "eine eigene Zwischentabelle"


@art("ermodell", "ER-Modell → Tabellen", "Datenbanken", "Kardinalitäten erkennen, Fremdschlüssel setzen, Zwischentabellen für n:m",
     THEMEN["ermodell"], formeln=FORMELN["ermodell"])
def ermodell(rng):
    titel, fuer, ent, slots = rng.choice(ER)
    bez = [rng.choice(slot) for slot in slots]
    rng.shuffle(bez)  # wie im Gespräch: die Reihenfolge der Sätze wechselt
    nm = [b for b in bez if b[2] == "n:m"]
    fks = sum(2 if b[2] == "n:m" else 1 for b in bez)
    a, b, kard, _ = gefragt = rng.choice(bez)
    soll = {"1:1": "1 : 1", "1:n": "1 : n", "n:m": "n : m"}[kard]
    if kard == "1:n" and rng.random() < 0.35:  # auch andersherum gefragt, sonst wäre „n : 1“ nie richtig
        a, b, soll = b, a, "n : 1"
    felder = [Feld("kard", f"Kardinalität {a} : {b}", soll, typ="text", optionen=KARDINALITAETEN)]
    fa, fb, fkard, _ = rng.choice([x for x in bez if x[2] != "1:1" and x is not gefragt] or [x for x in bez if x[2] != "1:1"])
    orte = [ent[fa][0], ent[fb][0]]
    rng.shuffle(orte)
    felder.append(Feld("fk", f"Fremdschlüssel für {fa} – {fb} steht in", ZWISCHENTABELLE if fkard == "n:m" else ent[fb][0], typ="text",
                       optionen=[*orte, ZWISCHENTABELLE]))
    felder.append(Feld("tabellen", "Anzahl der Tabellen", len(ent) + len(nm), stellen=0))
    if nm:
        za, zb, _, _ = rng.choice(nm)
        ka, kb = ent[za][1], ent[zb][1]
        optionen = [f"{ka} und {kb} zusammen", f"nur {ka}", f"nur {kb}", "keiner nötig"]
        felder.append(Feld("zw_pk", f"Primärschlüssel der Zwischentabelle {ent[za][0]}_{ent[zb][0]}", optionen[0], typ="text",
                           optionen=sorted(optionen)))
    if rng.random() < 0.4:
        felder.append(Feld("fks", "Fremdschlüssel insgesamt", fks, stellen=0))

    frage = (f"Die {rng.choice(FIRMEN)} entwickelt für {fuer} eine Datenbank. Aus dem Gespräch mit dem Kunden:\n\n"
             + "\n".join(f"- {satz}" for *_, satz in bez)
             + f"\n\nJede Entität wird eine eigene Tabelle mit eigenem Primärschlüssel ("
             + ", ".join(f"{e}: `{k}`" for e, (_, k) in ent.items()) + "). Überführen Sie das ER-Modell in Tabellen.")
    weg, fremd = [], {t: [] for t, _ in ent.values()}
    for x, y, k, _ in bez:
        (tx, kx), (ty, ky) = ent[x], ent[y]
        if k == "n:m":
            weg.append(f"{x} – {y}, n : m: Zwischentabelle {tx}_{ty} mit den Fremdschlüsseln {kx} und {ky}, zusammen ihr Primärschlüssel")
        elif k == "1:n":
            weg.append(f"{x} – {y}, 1 : n: Fremdschlüssel {kx} in {ty}, der n-Seite")
            fremd[ty].append(f"{kx} → {tx}")
        else:
            weg.append(f"{x} – {y}, 1 : 1: Fremdschlüssel {kx} in {ty} (jede Zeile dort hat genau einen Partner), dazu UNIQUE")
            fremd[ty].append(f"{kx} → {tx}")
    weg.append(f"Tabellen: {len(ent)} Entitäten + {len(nm)} {'Zwischentabelle' if len(nm) == 1 else 'Zwischentabellen'} = "
               f"**{len(ent) + len(nm)}**; Fremdschlüssel: **{fks}**")
    liste = [f"- {t} (**{k}**{''.join(', ' + f for f in fremd[t])})" for t, k in ent.values()]
    liste += [f"- {ent[x][0]}_{ent[y][0]} (**{ent[x][1]} → {ent[x][0]}**, **{ent[y][1]} → {ent[y][0]}**)" for x, y, _, _ in nm]
    return Aufgabe(frage, felder, schritte(*weg) + "\n\nRelationales Modell (Primärschlüssel **fett**, Fremdschlüssel mit →):\n\n"
                   + "\n".join(liste), titel=titel)


# --- Normalisierung -----------------------------------------------------------

@dataclass(frozen=True)
class Block:
    """Eine Entität in der unnormalisierten Tabelle: Tabelle nach der Zerlegung, Name für die Sätze, Schlüssel, abhängige Spalten,
    Beispielwerte (Schlüssel, *Spalten) und der Satz für die Einfügeanomalie."""
    tabelle: str
    name: str
    schluessel: str
    spalten: tuple[str, ...]
    werte: tuple[tuple, ...]
    neu: str = ""


# (Titel, für wen, X, P: an X über einen Fremdschlüssel (transitiv), Y: mit X n:m, (Tabelle, Spalte und Werte der Beziehung X–Y))
NF = [
    ("Bestellungen", "einen Onlineshop",
     Block("bestellung", "Bestellung", "bestell_nr", ("datum",), ((1001, "02.03.2027"), (1002, "02.03.2027"), (1003, "05.03.2027"),
                                                                  (1004, "09.03.2027"), (1005, "11.03.2027"), (1006, "12.03.2027"))),
     Block("kunde", "Kunde", "kunden_nr", ("name", "ort"), ((11, "Weber", "Talheim"), (12, "Hoffmann", "Seeburg"), (13, "Krüger", "Bergdorf"),
                                                           (14, "Lange", "Talheim")),
           "Ein neuer Kunde soll erfasst werden, der noch nichts bestellt hat."),
     Block("artikel", "Artikel", "artikel_nr", ("bezeichnung", "preis"),
           (("A-12", "Locher", "12,90 €"), ("A-17", "Ordner A4", "2,79 €"), ("B-03", "Kopierpapier", "4,99 €"), ("B-08", "Notizblock", "1,99 €"),
            ("C-21", "Textmarker", "3,49 €")),
           "Ein neuer Artikel soll erfasst werden, bevor ihn jemand bestellt."),
     ("position", "menge", (1, 2, 3, 5, 10))),
    ("Kursteilnahmen", "einen Schulungsanbieter",
     Block("teilnehmer", "Teilnehmer", "teilnehmer_nr", ("name",), ((501, "Arslan"), (502, "Becker"), (503, "Lorenz"), (504, "Neumann"),
                                                                    (505, "Pohl"))),
     Block("firma", "Firma", "firma_nr", ("firma", "ort"), (("F1", "Autohaus Lenz", "Talheim"), ("F2", "Bäckerei Korn", "Bergdorf"),
                                                           ("F3", "Kanzlei Vogt", "Seeburg"), ("F4", "Hotel Seeblick", "Seeburg")),
           "Eine neue Firma soll erfasst werden, die noch niemanden angemeldet hat."),
     Block("kurs", "Kurs", "kurs_nr", ("kurstitel", "dauer"), ((31, "Excel Grundlagen", "2 Tage"), (32, "Netzwerk Grundlagen", "3 Tage"),
                                                               (33, "Python Einstieg", "3 Tage"), (34, "Phishing erkennen", "1 Tag"),
                                                               (35, "WLAN planen", "2 Tage")),
           "Ein neuer Kurs soll erfasst werden, für den sich noch niemand angemeldet hat."),
     ("teilnahme", "bezahlt", ("ja", "nein"))),
    ("Projektzeiten", "die Zeiterfassung eines IT-Dienstleisters",
     Block("mitarbeiter", "Mitarbeiter", "personal_nr", ("name",), ((201, "Albers"), (202, "Brandt"), (203, "Yilmaz"), (204, "Nowak"),
                                                                    (205, "Kraus"))),
     Block("abteilung", "Abteilung", "abteilung_nr", ("abteilung",), ((10, "Entwicklung"), (20, "Vertrieb"), (30, "Support"), (40, "Verwaltung")),
           "Eine neue Abteilung soll erfasst werden, die noch keine Mitarbeiter hat."),
     Block("projekt", "Projekt", "projekt_nr", ("projektname",), (("P-1", "Kundenportal"), ("P-2", "Lagerumzug"), ("P-3", "Webshop"),
                                                                 ("P-4", "Datensicherung"), ("P-5", "Telefonanlage")),
           "Ein neues Projekt soll erfasst werden, auf das noch niemand Stunden gebucht hat."),
     ("zeiterfassung", "stunden", (4, 6, 8, 12, 16, 20))),
    ("Werkstattaufträge", "eine Kfz-Werkstatt",
     Block("auftrag", "Auftrag", "auftrag_nr", ("datum",), ((7001, "14.04.2027"), (7002, "14.04.2027"), (7003, "16.04.2027"),
                                                            (7004, "20.04.2027"), (7005, "21.04.2027"))),
     Block("fahrzeug", "Fahrzeug", "fahrzeug_nr", ("modell", "baujahr"), ((1, "Kombi", 2019), (2, "Kleinwagen", 2022), (3, "Transporter", 2017),
                                                                         (4, "Cabrio", 2020)),
           "Ein neues Fahrzeug soll erfasst werden, für das es noch keinen Auftrag gibt."),
     Block("ersatzteil", "Ersatzteil", "teil_nr", ("bezeichnung", "preis"),
           (("T-10", "Bremsbelag", "39,00 €"), ("T-11", "Ölfilter", "12,50 €"), ("T-12", "Zündkerze", "8,90 €"), ("T-13", "Wischerblatt", "14,00 €"),
            ("T-14", "Luftfilter", "18,90 €")),
           "Ein neues Ersatzteil soll erfasst werden, das noch in keinem Auftrag verbaut wurde."),
     ("auftragsposition", "anzahl", (1, 2, 4))),
    ("Zeugnisnoten", "eine Berufsschule",
     Block("schueler", "Schüler", "schueler_nr", ("name",), ((1, "Lena"), (2, "Murat"), (3, "Sophie"), (4, "Jonas"), (5, "Elif"))),
     Block("klasse", "Klasse", "klasse", ("klassenleitung",), (("FI24a", "Frau Roth"), ("FI24b", "Herr Simon"), ("FI24c", "Frau Klein"),
                                                               ("FI24d", "Herr Brandt")),
           "Eine neue Klasse soll erfasst werden, in der noch kein Schüler ist."),
     Block("fach", "Fach", "fach_kz", ("fach",), (("DE", "Deutsch"), ("EN", "Englisch"), ("WI", "Wirtschaft"), ("DB", "Datenbanken"),
                                                  ("NW", "Netzwerke")),
           "Ein neues Fach soll erfasst werden, in dem noch niemand eine Note hat."),
     ("note", "note", (1, 2, 3, 4))),
]

NORMALFORMEN = ["nicht in der 1. NF", "1. NF", "2. NF", "3. NF"]
ANOMALIEN = ["Einfügeanomalie", "Änderungsanomalie", "Löschanomalie"]


def abhaengigkeiten(schluessel: tuple, fds: list[tuple[tuple, tuple]]) -> tuple[list, list]:
    """(teilweise, transitive) Abhängigkeiten von Nichtschlüsselspalten: linke Seite ein echter Teil des Schlüssels bzw. eine
    Nichtschlüsselspalte."""
    k = set(schluessel)
    teilweise = [(l, r) for l, r in fds if set(l) < k and set(r) - k]
    transitiv = [(l, r) for l, r in fds if not set(l) <= k and set(r) - k]
    return teilweise, transitiv


def _fd(l: tuple, r: tuple) -> str:
    return f"{', '.join(f'`{c}`' for c in l)} → {', '.join(f'`{c}`' for c in r)}"


@art("normalform", "Normalisierung", "Datenbanken", "Normalform bestimmen, in die 3. NF zerlegen, Anomalien erkennen",
     THEMEN["normalform"], formeln=FORMELN["normalform"])
def normalform(rng):
    titel, fuer, X, P, Y, (zw, zw_spalte, zw_werte) = rng.choice(NF)
    xk, pk, yk = X.schluessel, P.schluessel, Y.schluessel
    xs, ps, ys = sorted(rng.sample(X.werte, 4)), rng.sample(P.werte, 3), sorted(rng.sample(Y.werte, 4))
    # festes Muster: P[0] und Y[0] kommen mehrfach vor (Änderung), X[3] allein hat P[2] und Y[3] (Löschen)
    zu_p, zu_y = [ps[0], ps[1], ps[0], ps[2]], [[ys[0], ys[1]], [ys[0], ys[2]], [ys[1]], [ys[3]]]
    stufe = rng.choices([0, 1, 2, 3], weights=[2, 4, 2, 2])[0]
    mit_p, mit_y, atomar = stufe == 2 or stufe < 2 and rng.random() < 0.6, stufe < 2, stufe != 0
    if stufe < 2:
        kopf = [xk, *X.spalten, *([pk, *P.spalten] if mit_p else []), yk, *Y.spalten, zw_spalte]
        fds = [((xk,), (*X.spalten, pk) if mit_p else X.spalten), *([((pk,), P.spalten)] if mit_p else []),
               ((yk,), Y.spalten), ((xk, yk), (zw_spalte,))]
        zeilen = []
        for x, p, yy in zip(xs, zu_p, zu_y):
            vorne, hinten = [*x, *(p if mit_p else ())], [[*y, rng.choice(zw_werte)] for y in yy]
            if atomar:
                zeilen += [vorne + h for h in hinten]
            else:  # Wiederholungsgruppe: mehrere Werte in einer Zelle
                zeilen.append(vorne + ["<br>".join(str(h[i]) for h in hinten) for i in range(len(hinten[0]))])
        schluessel = (xk, yk) if atomar else (xk,)
    elif stufe == 2:
        kopf, fds = [xk, *X.spalten, pk, *P.spalten], [((xk,), (*X.spalten, pk)), ((pk,), P.spalten)]
        zeilen, schluessel = [[*x, *p] for x, p in zip(xs, zu_p)], (xk,)
    else:  # schon in der 3. NF: eine Entität für sich oder nur die Beziehung
        kopf, fds, zeilen, schluessel = rng.choice([
            ([xk, *X.spalten, pk], [((xk,), (*X.spalten, pk))], [[*x, p[0]] for x, p in zip(xs, zu_p)], (xk,)),
            ([pk, *P.spalten], [((pk,), P.spalten)], [list(p) for p in sorted(ps)], (pk,)),
            ([yk, *Y.spalten], [((yk,), Y.spalten)], [list(y) for y in ys], (yk,)),
            ([xk, yk, zw_spalte], [((xk, yk), (zw_spalte,))], [[x[0], y[0], rng.choice(zw_werte)] for x, yy in zip(xs, zu_y) for y in yy],
             (xk, yk))])
    teilweise, transitiv = abhaengigkeiten(schluessel, fds)
    nf = 0 if not atomar else 1 if teilweise else 2 if transitiv else 3

    fall = anomalie = anomalie_weg = ""
    if nf < 3:
        anomalie = rng.choice(ANOMALIEN)
        b, wert = rng.choice([(blk, w) for blk, w, da in ((P, ps[0], mit_p), (Y, ys[0], mit_y)) if da])
        fall, anomalie_weg = {
            "Einfügeanomalie": (b.neu, f"Ohne {X.name} fehlt ein Wert für `{xk}`, {'den Schlüssel' if schluessel == (xk,) else 'einen Teil des Schlüssels'}: "
                                       f"die Zeile lässt sich nicht anlegen → **Einfügeanomalie**"),
            "Änderungsanomalie": (f"Bei {b.name} {wert[0]} wird `{b.spalten[-1]}` geändert, aber nur in einer der Zeilen.",
                                  f"{b.name} {wert[0]} steht in mehreren Zeilen; danach widersprechen sie sich → **Änderungsanomalie**"),
            "Löschanomalie": (f"{X.name} {xs[3][0]} wird gelöscht, mit allen Zeilen dazu.",
                              f"Damit verschwinden auch die einzigen Angaben zu {(Y if mit_y else P).name} {(ys[3] if mit_y else ps[2])[0]} "
                              f"→ **Löschanomalie**"),
        }[anomalie]

    frage = (f"Die {rng.choice(FIRMEN)} soll für {fuer} Daten in eine Datenbank übernehmen. Bisher stehen sie in einer Tabelle:\n\n"
             f"{tabelle(kopf, zeilen)}\n\nPrimärschlüssel: {', '.join(f'`{c}`' for c in schluessel)}. Es gelten diese funktionalen "
             "Abhängigkeiten:\n\n" + "\n".join(f"- {_fd(l, r)}" for l, r in fds)
             + "\n\nIn welcher Normalform ist die Tabelle, und wie viele Tabellen entstehen bei der Zerlegung in die 3. NF?"
             + (f" Welche Anomalie tritt in diesem Fall auf?\n\n**Fall:** {fall}" if fall else ""))
    felder = [Feld("nf", "Normalform der Tabelle", NORMALFORMEN[nf], typ="text", optionen=NORMALFORMEN),
              Feld("tabellen", "Tabellen nach Zerlegung in die 3. NF", len(fds), stellen=0)]
    if fall:
        felder.append(Feld("anomalie", "Anomalie in diesem Fall", anomalie, typ="text", optionen=ANOMALIEN))

    if not atomar:
        weg = [f"In einer Zelle stehen mehrere Werte (`{yk}`, …): nicht atomar → **nicht in der 1. NF**",
               f"Je Wert eine eigene Zeile, dann ist der Schlüssel `{xk}`, `{yk}`; weiter mit den Abhängigkeiten"]
    else:
        weg = ["Jede Zelle enthält genau einen Wert → 1. NF"]
        if teilweise:
            weg.append("Teilweise vom Schlüssel abhängig: " + "; ".join(_fd(l, r) for l, r in teilweise) + " → **nicht in der 2. NF**")
        else:
            weg.append("Einspaltiger Schlüssel, teilweise Abhängigkeiten gibt es nicht → 2. NF" if len(schluessel) == 1
                       else "Alles hängt vom ganzen Schlüssel ab → 2. NF")
        if transitiv:
            weg.append(("Außerdem" if teilweise else "Aber") + " transitiv, Nichtschlüssel → Nichtschlüssel: "
                       + "; ".join(_fd(l, r) for l, r in transitiv) + (" → **nicht in der 3. NF**" if not teilweise else ""))
        elif not teilweise:
            weg.append("Keine Nichtschlüsselspalte hängt von einer anderen ab → **3. NF**")
    weg.append("Nichts zu zerlegen: es bleibt **1 Tabelle**" if nf == 3 else
               f"Zerlegung: je linke Seite einer Abhängigkeit eine Tabelle → **{len(fds)} Tabellen**")
    if fall:
        weg.append(anomalie_weg)
    namen = {(xk,): X.tabelle, (pk,): P.tabelle, (yk,): Y.tabelle, (xk, yk): zw}
    ziele = {xk: X.tabelle, pk: P.tabelle, yk: Y.tabelle}
    liste = [f"- {namen[l]} (" + ", ".join([f"**{c}**" + (f" → {ziele[c]}" if len(l) > 1 else "") for c in l]
                                          + [f"{c} → {ziele[c]}" if c in ziele else c for c in r]) + ")" for l, r in fds]
    return Aufgabe(frage, felder, schritte(*weg) + "\n\nIn der 3. NF (Primärschlüssel **fett**, Fremdschlüssel mit →):\n\n" + "\n".join(liste),
                   titel=titel)
