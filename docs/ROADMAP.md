# Roadmap

Saku wird in sechs Phasen gebaut. **Jede Phase endet mit etwas Lauffähigem**, sodass es zu jedem Zeitpunkt eine vorzeigbare Version gibt.

| Phase | Inhalt | Aufwand | Für die Kurs-Demo |
|---|---|---|---|
| 0 | Fundament | ½ Tag | Pflicht |
| 1 | Analyse | 1 Tag | Pflicht |
| 2 | Keiko und Fahrschul-Logik | 1 Tag | Pflicht |
| 3 | Sensei | ½ bis 1 Tag | Pflicht |
| 4 | Michi und Heute | ½ Tag | Kür |
| 5 | Niwa, Shiken und Feinschliff | 1 Tag | Kür |

Für die Kurs-Demo reichen die Phasen 0 bis 3 plus die Startseite mit dem Ensō. Michi, Niwa und Shiken folgen danach.

## Phase 0 · Fundament

- [x] Repo mit dieser Struktur, virtuelle Umgebung, `pip install -r requirements.txt`
- [x] `python -m saku init` legt `data/saku.db` aus `db/schema.sql` an
- [x] `python -m saku assets` lädt Basecoat, htmx, force-graph, Lucide und die Schriften
- [x] Flask-App mit Grundlayout, Navigation und Saku-Theme in Hell und Dunkel
- [x] `python -m saku start` öffnet das Fenster

**Fertig, wenn** das leere Saku im eigenen Fenster startet, im Saku-Look, hell und dunkel.

## Phase 1 · Analyse

- [x] Inventar: Hash, Deckblatt, Text oder Scan, Art des Dokuments, rich-Tabelle im Terminal
- [x] Segmentierung in Aufgaben und Teilaufgaben, Bildausschnitte rendern
- [x] Lösungshinweise zuordnen
- [x] Themenliste importieren
- [x] KI-Klassifikation mit Cache und Protokoll
- [x] Ähnlichkeiten (TF-IDF) und Suchindex
- [x] Bunseki, erste Version: Inventar, Heatmap, Dauerbrenner, Lücken

**Fertig, wenn** alle PDFs im Inventar stehen, mindestens 90 % der Teilaufgaben samt Punkten erkannt sind und Bunseki die Heatmap zeigt.

## Phase 2 · Keiko und Fahrschul-Logik

- [x] Lernkarte mit Bildausschnitt, Lösung per Leertaste, Bewertung mit 1, 2 und 3
- [x] Statusregeln (zweimal „Gewusst“ = sicher) und FSRS mit Prüfungstermin als längstem Intervall
- [x] Filter: Thema, Fehlerkorb, markiert, neu
- [x] „Kam so ähnlich auch dran“
- [x] Suche mit Strg + K

**Fertig, wenn** sich eine komplette Lernrunde nur mit der Tastatur durchspielen lässt und der Lernstand nach einem Neustart erhalten bleibt.

## Phase 3 · Sensei

- [x] Client mit Modellen aus `.env`, Cache und Protokoll in `ki_aufruf`
- [x] Tipp, Erklären, Antwort prüfen (mit Bewertungsvorschlag) und Ähnliche Übung
- [x] Streaming per Server-Sent Events
- [x] Frag Sensei: Chat mit Quellen über alle Prüfungen

**Fertig, wenn** Sensei in Keiko alle vier Modi beherrscht, Antworten Wort für Wort erscheinen und der Chat auf echte Teilaufgaben verlinkt.

## Phase 4 · Michi und Heute

- [x] Voraussetzungen und Stationen aus der Pipeline
- [x] Stationsseite mit Einführung, Übungen und Mini-Test, Freischalten der nächsten Station
- [x] Heute: Countdown, Tagesziel, Weiterlernen, Ensō, Lernserie

**Fertig, wenn** der Lernpfad vollständig ist und Heute immer genau einen sinnvollen nächsten Schritt anbietet.

## Phase 5 · Niwa, Shiken und Feinschliff

- [x] Garten mit force-graph (vorher vis-network) und Notiz je Thema
- [x] Simulation: Zusammenstellung, Timer, Antworten, Punkte, Note, Hanko-Stempel
- [x] Animationen, Leerzustände, Tastaturhilfe, Abschlussseite お疲れ様
- [x] Ausbaustufe: Rechenwerkzeug für Sensei (Zahlensysteme, `sensei/werkzeuge.py`)

**Fertig, wenn** eine komplette Simulation mit Auswertung durchläuft und der Garten den echten Lernstand zeigt.

## Ausbau nach den Phasen

- [x] 算 Rechnen: 27 Aufgabenarten in acht Gruppen, ohne KI und exakt geprüft, fällig nach Leitner, Tagesziel, Sprint mit Note, Formelsammlung
- [x] SQL-Sandbox: Pipeline-Schritt `sandbox`, SQL in Üben ausführen und mit der Musterlösung vergleichen
- [x] Automatische Auswertung in Simulation und Mini-Test (anklickbar und SQL), Stichpunkt-Abgleich bei freien Antworten
- [x] Fahrplan bis zur Prüfung, Verlauf mit Wochenrückblick, Grundwissen umgekehrt
- [x] Tägliche Sicherung, Lernstand-Export und -Import, Migrationen in Transaktionen
- [x] Link-Crawler als Regressionstest, CSRF-Schutz, Tastatur und Screenreader auf den neuen Seiten

## Stand

Alle Phasen sind umgesetzt. Analysiert sind 27 FIAE-Prüfungen aus 7 Terminen (Winter 2021/22 bis Winter 2024/25,
dazu die alten Ganzheitlichen Aufgaben von 2022 und 2023): 590 Teilaufgaben, 99 % mit Punkten, 71 % mit Lösungshinweis.
Die Erst-Klassifikation, die Voraussetzungen und die 50 Stationseinführungen hat Claude Code erzeugt
(`python -m saku analyse --ki claude-code`). Für Winter 2023/24 liegen nur die Lösungen vor, nicht die Aufgaben.

## Demo-Ablauf (5 Minuten)

1. **Terminal:** `python -m saku analyse` mit Fortschrittsbalken und Zusammenfassung
2. **Heute:** Das Fenster öffnet sich, der Ensō zeichnet sich, der Countdown läuft.
3. **Bunseki:** Die Heatmap zeigt, welche Themen immer drankommen.
4. **Suche:** Strg + K, „normal“ eingeben, Treffer aus allen Jahrgängen
5. **Keiko:** Teilaufgabe lösen, Antwort tippen, Sensei prüft und schlägt eine Bewertung vor
6. **Niwa:** Der Garten, ein Klick auf ein Thema
7. **Shiken:** Ergebnis einer vorbereiteten Simulation mit dem 合格-Stempel

## Risiken

| Risiko | Gegenmaßnahme |
|---|---|
| Das Layout der PDFs unterscheidet sich je Jahrgang | Muster je Format, KI als Rückfallebene, Korrektur in der App |
| Gescannte PDFs | Texterkennung mit Tesseract oder Claude liest das Seitenbild |
| Lösungshinweise fehlen | Im Inventar sichtbar; Sensei erklärt trotzdem, mit Hinweis |
| Die Zeit wird knapp | Jede Phase endet lauffähig, die Kür kommt zuletzt |
| API-Kosten | Schnelles Modell für Massenarbeit, Cache, Batch-API |

## Was noch gebraucht wird

- [x] Alle Prüfungs-PDFs samt Lösungshinweisen in `data/pdfs/`
- [x] Die AP2-Themenliste als `data/themen.md`
- [ ] Der Prüfungstermin (in der App unter Einstellungen)
- [ ] Ein API-Schlüssel der Claude-API in `.env` (für Sensei)
