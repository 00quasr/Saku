"""Welche Rechenarten sind heute dran? Ein einfacher Leitner-Gedanke statt FSRS, dazu der Prüfungsumfang je Lernpfad.
Reine Funktionen: die Versuche kommen von außen, die Datenbank liest die Route."""

from datetime import datetime, timedelta

from saku.lernen.rechnen.basis import ARTEN, GRUPPEN

# Gruppen je Lernpfad (v_umfang.pfad).
# AP1 „Einrichten eines IT-gestützten Arbeitsplatzes“ ist für alle IT-Berufe gleich und prüft die Grundlagen aus allen Gruppen,
#   auch Pseudocode; Algorithmen und Datenstrukturen (Sortieren, Hashing, Bäume …) kommen erst in der AP2 Anwendungsentwicklung.
#   Datenbanken gehören dazu: Lernfeld 5 „Software zur Verwaltung von Daten anpassen“ (Datenmodell, SQL-Abfragen) liegt in der AP1.
# AP2 Anwendungsentwicklung: „Entwicklung und Umsetzung von Algorithmen“ (Programmieren, Algorithmen), „Planen eines
#   Softwareproduktes“ (Projekt, Wirtschaft), Daten; Datenbanken (SQL, ER-Modell, Normalisierung) in fast jeder Prüfung; WiSo prüfen alle.
# AP2 Systemintegration: „Konzeption und Administration von IT-Systemen“ und „Analyse und Entwicklung von Netzwerken“
#   (Netzwerk, Strom & Hardware), Daten, Wirtschaft; WiSo prüfen alle. Datenbanken nicht: SQL schreiben oder normalisieren
#   prüft die AP2 Systemintegration kaum, das bleibt bei der AP1.
# IT-Sicherheit und Datenschutz verlangt die Verordnung von 2020 in der AP1 und in der AP2 beider Berufe.
# UML (Klassen-, Zustands-, Use-Case- und Sequenzdiagramm) gehört zum Softwareentwurf der Anwendungsentwicklung (Lernfelder 10a bis
#   12a, AP2 „Planen eines Softwareproduktes“); die AP1 verlangt Programmabläufe darstellen und lesen, das Aktivitätsdiagramm steht
#   deshalb beim Schreibtischtest (Programmieren) und ist in der AP1 und AP2 Anwendungsentwicklung dabei.
UMFANG = {
    "AP1": [g for g in GRUPPEN if g not in ("Algorithmen", "UML")],
    "AP2-1201": ["Programmieren", "Algorithmen", "Datenbanken", "Wirtschaft", "Projekt", "WiSo", "Daten & Medien", "IT-Sicherheit", "UML"],
    "AP2-1202": ["Netzwerk", "Strom & Hardware", "Daten & Medien", "Wirtschaft", "WiSo", "IT-Sicherheit"],
}

LETZTE = 5  # so viele Versuche zählen für die Quote
QUOTE = 0.8  # darunter ist eine Art fällig
PAUSE = timedelta(days=7)  # länger nicht gerechnet: wieder fällig


def im_umfang(pfad: str) -> list[str]:
    """Arten des Lernpfads in der Reihenfolge der Übersicht; ein unbekannter Pfad bekommt alle."""
    gruppen = UMFANG.get(pfad, GRUPPEN)
    return [a for a, art in ARTEN.items() if art.gruppe in gruppen]


def faellig(arten: list[str], letzte: dict[str, list[int]], zuletzt: dict[str, datetime], jetzt: datetime) -> list[str]:
    """Arten, die dran sind: noch nie gerechnet, in den letzten fünf Versuchen unter 80 % richtig, oder seit über sieben
    Tagen nicht mehr. letzte: Ergebnisse je Art, älteste zuerst (1 = richtig); zuletzt: Zeitpunkt des letzten Versuchs."""
    raus = []
    for art in arten:
        versuche = letzte.get(art, [])[-LETZTE:]
        if not versuche or sum(versuche) < QUOTE * len(versuche) or jetzt - zuletzt[art] > PAUSE:
            raus.append(art)
    return raus
