<div align="center">

# 咲く Saku

Ein lokaler Trainer für die IHK-Abschlussprüfung der Fachinformatiker/-innen (AP1 und AP2):
die Systematik einer Fahrschul-App, die Ruhe japanischer Gestaltung und ein KI-Tutor, der jede Aufgabe kennt.

<img src="docs/bilder/heute.png" alt="Saku, Bereich Heute: Begrüßung, Countdown zur Prüfung, Tagesplan, Prüfungsreife und Lernstand" width="900">

</div>

---

## Was ist Saku?

Saku macht aus gekauften IHK-Prüfungen einen persönlichen Lernkatalog. Eine Pipeline liest alle Prüfungs-PDFs, zerlegt sie in Teilaufgaben, baut sie mit Claude als echten Text neu auf und ordnet sie den Themen aus Prüfungskatalog und Rahmenlehrplan zu. Gelernt wird danach wie in einer Fahrschul-App: Jede Teilaufgabe hat einen Lernstand, eine Teilaufgabe ist erst sicher, wenn sie zweimal hintereinander klappt, und eine Prüfungsreife-Anzeige sagt ehrlich, wie weit man ist.

Der Name kommt von 咲く (*saku*), „erblühen“. Wissen wächst in Saku wie ein Garten, bis zur vollen Blüte, 満開 (*mankai*), dem Moment der Prüfungsreife.

## Bereiche

| | | |
|---|---|---|
| 今 | **Heute** | Tagesplan, Countdown, Prüfungsreife als Ensō, Lernserie und Lernkalender, Wochenrückblick; dazu der **Fahrplan**: Wiederholungen der nächsten Tage, Tempo bis zur Prüfung, Abdeckung nach Prüfungsgewicht, was jetzt am meisten bringt |
| 道 | **Lernpfad** | Stationen, jede mit Einführung, Übungen, passendem Rechentraining und Mini-Test |
| 稽 | **Üben** | Fokusmodus: Aufgabe als echter Text, anklickbare Antworten, SQL in einer Sandbox ausführen und prüfen, Stichpunkt-Abgleich bei freien Antworten, Lösung per Leertaste, Bewertung mit 1, 2, 3; nach einem Fehler eine ähnliche Aufgabe aus einem anderen Jahrgang; **Verlauf** aller Bewertungen; **Grundwissen** als Begriffs-Karten, auch umgekehrt (Definition → Begriff) |
| 算 | **Rechnen** | Rechentrainer ohne KI, 27 Aufgabenarten in acht Gruppen: Netzwerk (Subnetting, VLSM, Routing-Tabelle, IPv6, EUI-64, Übertragungszeit), Daten & Medien (Datenmenge, Speichereinheiten, Zahlensysteme, Datensicherung), Strom & Hardware (Energie und USV, RAID, Verfügbarkeit, Monitor und Druck, Bus- und Speicherbandbreite), Wirtschaft (Kalkulation, Kauf/Leasing/Miete, Nutzwertanalyse), WiSo (Kündigungsfristen, Urlaub), Projekt (Netzplan), Programmieren (Schreibtischtest), Algorithmen (Sortieren, binäre Suche, Hashing, Suchbaum, Stack und Queue). ↵ prüft, danach steht der Rechenweg da; fällige Arten, Tagesziel, Sprint mit Note, Formelsammlung zum Drucken |
| 試 | **Prüfung** | Simulation mit Timer, Note und Hanko-Stempel; Anklickbares und SQL wertet Saku selbst aus; Hochrechnung der Gesamtnote; Fachgespräch üben |
| 庭 | **Themen** | Wissensgraph aus Themen, Lernfeldern und Fachbegriffen; je Thema eine Wissensseite (was du können musst, so wird gefragt, Fallen) |
| 先 | **Sensei** | KI-Tutor: Tipps, Erklärungen, Antworten prüfen, Übungsvarianten, Chat mit Quellen |
| 析 | **Analyse** | alle Prüfungen: Inventar, Heatmap, Dauerbrenner, lange nicht dran, Katalog als Checkliste, Zuordnung korrigieren |
| ⌘K | **Suche** | Befehlspalette und Suche nach Wort und Bedeutung über alle Prüfungen |

## So sieht Saku aus

Alle Bilder zeigen die erfundenen Demo-Daten, keine echten Prüfungsaufgaben.

<table>
  <tr>
    <td width="50%"><img src="docs/bilder/ueben.png" alt="Üben: freie Antwort mit Stichpunkt-Abgleich gegen die Musterlösung"><br><b>稽 Üben.</b> Aufgabe als Text; anklickbare Antworten prüft ↵ sofort. Bei freien Antworten zeigt der Stichpunkt-Abgleich, welche Punkte der Musterlösung drin sind, Sensei schlägt Punkte nach dem IHK-Schlüssel vor.</td>
    <td width="50%"><img src="docs/bilder/themen.png" alt="Themen: Wissensgraph aus Prüfungsbereichen, Themen und Begriffen, Farbe nach Lernstand"><br><b>庭 Themen.</b> Wissensgraph aus Themen, Lernfeldern und Fachbegriffen. Jede Notiz hat eine Wissensseite mit Verweisen auf echte Aufgaben.</td>
  </tr>
  <tr>
    <td><img src="docs/bilder/pruefung.png" alt="Prüfung: Hochrechnung der Abschlussnote nach Ausbildungsverordnung"><br><b>試 Prüfung.</b> Simulation im Heft-Layout und Hochrechnung der Gesamtnote samt Bestehensregeln der AO 2020.</td>
    <td><img src="docs/bilder/analyse.png" alt="Analyse: Kennzahlen und die Themen mit den meisten Punkten"><br><b>析 Analyse.</b> Was wie oft drankam, Heatmap, Dauerbrenner, Themen, die lange nicht dran waren, und der Katalog als Checkliste.</td>
  </tr>
  <tr>
    <td><img src="docs/bilder/suche.png" alt="Befehlspalette: Rechnen-Befehle, ein Thema und eine Teilaufgabe zur Suche „netz“"><br><b>⌘K.</b> Befehle (Simulation, Termin, AP1/AP2, AE/SI, Farbschema) und Suche nach Wort und Bedeutung.</td>
    <td><img src="docs/bilder/grundwissen.png" alt="Grundwissen: Begriffs-Karte mit aufgedeckter Definition"><br><b>Grundwissen.</b> Fachbegriffe als Lernkarten mit eigener Wiederholungsplanung.</td>
  </tr>
  <tr>
    <td><img src="docs/bilder/rechnen.png" alt="Rechnen: Subnetting-Aufgabe geprüft, 2 von 3 richtig, mit Rechenweg"><br><b>算 Rechnen.</b> Unbegrenzt neue Rechenaufgaben, ↵ prüft sofort, danach steht der Rechenweg da.</td>
    <td><img src="docs/bilder/fahrplan.png" alt="Fahrplan: Säulen der nächsten Wiederholungen, Tempo und Abdeckung"><br><b>Fahrplan.</b> Was auf dich zukommt, ob dein Tempo bis zur Prüfung reicht und wo die Punkte liegen.</td>
  </tr>
  <tr>
    <td><img src="docs/bilder/verlauf.png" alt="Verlauf: Wochenrückblick und Bewertungen nach Tagen"><br><b>Verlauf.</b> Jede Bewertung nach Tagen, oben der Rückblick auf die Woche.</td>
    <td><img src="docs/bilder/sql.png" alt="Üben: SQL-Anweisung geprüft, eine Zeile fehlt, erwartetes und eigenes Ergebnis nebeneinander"><br><b>SQL in Üben.</b> Anweisungen auf erfundenen Beispieldaten ausführen und mit der Musterlösung vergleichen.</td>
  </tr>
</table>

## Wie Saku funktioniert

Saku läuft komplett auf dem eigenen Rechner. Die Prüfungen werden einmal analysiert, danach lernt man nur noch in der App.

```mermaid
flowchart LR
    PDF["Prüfungs-PDFs<br>data/quellen"] --> P["Pipeline<br>python -m saku analyse"]
    KAT["Prüfungskataloge<br>und Rahmenlehrplan"] --> P
    P --> DB[("SQLite<br>data/saku.db")]
    DB <--> APP["Flask-App<br>127.0.0.1:5050"]
    APP --> FENSTER["pywebview-Fenster<br>htmx"]
    P -. "einmalig, Abo" .-> CC["Claude Code"]
    APP -. "Sensei, API" .-> API["Claude-API"]
```

### Die Pipeline

Jeder Schritt ist wiederholbar: Unveränderte PDFs werden übersprungen, KI-Antworten kommen beim zweiten Lauf aus dem Cache, und der Lernstand bleibt erhalten. Die KI-Schritte sind markiert.

```mermaid
flowchart TD
    A["1 Inventar<br>Deckblatt, Prüfungsteil, Text oder Scan"] --> B["2 Segmente<br>Aufgaben und Teilaufgaben, Ausschnitte"]
    B --> C["3 Lösungen<br>Lösungshinweise zuordnen"]
    C --> D["4 Aufbereiten ✦<br>Aufgabe als Markdown, Antwortart, Fachbegriffe"]
    D --> S["5 Sandbox ✦<br>SQL: Tabellen, Beispieldaten, Lösungen in SQLite"]
    S --> E["6 Themen<br>themen.md und Lernfelder"]
    E --> F["7 Klassifikation ✦<br>Teilaufgabe → Unterthemen"]
    F --> G["8 Statistik<br>Suchindex, Häufigkeiten"]
    G --> H["9 Wissen ✦<br>Wissensseiten, Begriffs-Definitionen"]
    H --> I["10 Vektoren<br>lokal: Ähnlichkeit, Aufgabenmuster"]
    I --> J["11 Lernpfad ✦<br>Voraussetzungen, Stationen, Einführungen"]
    J --> K["12 Bericht"]
```

✦ = Claude. Der Erstlauf geht über Claude Code (`--ki claude-code`), Vektoren rechnet [fastembed](https://github.com/qdrant/fastembed) lokal und kostenlos.

### Die Lernschleife

```mermaid
flowchart LR
    H["今 Heute<br>Tagesplan"] --> U["稽 Üben<br>Aufgabe lösen"]
    U --> B{"Bewertung<br>1 · 2 · 3 oder Punkte"}
    B -- "zweimal gewusst" --> G["sicher<br>grün"]
    B -- "teilweise" --> Y["im Aufbau<br>gelb"]
    B -- "nicht gewusst" --> R["Fehlerkorb<br>rot"]
    R --> V["ähnliche Aufgabe<br>aus anderem Jahrgang"]
    V --> U
    B --> L["Lücken<br>was Sensei vermisst hat"]
    G & Y & R --> F["FSRS plant die<br>nächste Wiederholung"]
    F --> H
    L --> H
```

Eine Teilaufgabe ist erst sicher, wenn sie zweimal hintereinander klappt. Die Prüfungsreife zählt, wie viele Prüfungspunkte sicher sitzen, und die Wiederholungen enden spätestens am Prüfungstag.

### Eine Anfrage in der App

```mermaid
sequenceDiagram
    participant F as Fenster (htmx)
    participant A as Flask
    participant D as SQLite
    participant S as Claude-API
    F->>A: Taste ↵ (POST /keiko/7/pruefen)
    A->>D: Aufgabe, Antwort, Lernstand
    A-->>F: HTML-Fragment, nur der Teil, der sich ändert
    F->>A: Sensei prüfen (P)
    A->>S: Aufgabe, Lösungshinweis, Antwort
    S-->>A: Punkte, richtig, fehlt (Schema)
    A->>D: Lücken speichern
    A-->>F: Punktevorschlag, ↵ übernimmt
```

## Stand

Alle Phasen der [Roadmap](docs/ROADMAP.md) sind umgesetzt, dazu Rechnen, Fahrplan, Verlauf, SQL-Sandbox und automatische Auswertung; 290 Tests laufen grün. Saku deckt **Fachinformatiker/-in Anwendungsentwicklung (1201) und Systemintegration (1202)** ab, jeweils **AP1 und AP2** samt WiSo; umgeschaltet wird oben in der Seitenleiste. Die Aufgaben baut Claude einmalig aus den PDF-Ausschnitten als echten Text neu auf (Tabellen, Code, anklickbare Antworten). Standard ist das dunkle Farbschema.

## Schnellstart

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # Windows: copy .env.example .env
                                   # für Sensei den API-Schlüssel in .env eintragen

# Prüfungen (PDFs, ZIPs) nach data/quellen/, Themenliste nach data/themen.md
python -m saku.pipeline.sammeln       # AE, SI, AP1 und WiSo nach data/pdfs/ kopieren
python -m saku init                    # Datenbank anlegen
python -m saku assets                  # Oberflächen-Dateien und Schriften laden (einmalig)
python -m saku analyse --ki claude-code  # Erstlauf: KI-Schritte über das lokale Claude Code
python -m saku start                   # App im eigenen Fenster öffnen
```

Beim ersten Start führt eine kurze Tour durch Saku: was die Analyse gefunden hat, Prüfungstermin, Lernweg, Tastatur und Sensei. Später erreichbar über die Einstellungen oder die Tastaturhilfe (`?`).

Ohne Prüfungs-PDFs lässt sich Saku mit erfundenen Demo-Daten ausprobieren:

```bash
python -m tests.demo_daten /tmp/saku-demo
SAKU_DATENORDNER=/tmp/saku-demo python -m saku start --browser
```

## Befehle

| Befehl | Was er tut |
|---|---|
| `python -m saku start` | App im eigenen Fenster öffnen; `--browser` öffnet sie im Standardbrowser |
| `python -m saku init` | Datenbank anlegen oder auf den neuesten Stand bringen |
| `python -m saku assets` | Basecoat, htmx, force-graph, Lucide und Schriften einmalig laden |
| `python -m saku analyse` | alle Schritte der Pipeline; `--schritt NAME` nur einen, `--ohne-ki` nur die lokalen, `--ki claude-code` KI über Claude Code statt API |
| `python -m saku analyse --schritt sandbox --ki claude-code` | nur die SQL-Sandboxen bauen; bearbeitet nur Aufgaben, die noch keine haben |
| `python -m saku lernstand export DATEI` | Lernstand als JSON-Datei mitnehmen (auch in den Einstellungen unter Daten) |
| `python -m saku lernstand import DATEI` | Lernstand übernehmen; mehrfach importieren ändert nichts |
| `python -m saku.pipeline.sammeln` | Prüfungen aus `data/quellen/` (auch ZIPs) nach `data/pdfs/` kopieren |
| `python -m saku paket [DATEI]` | Datenbank und benötigte Bilder als Archiv für Saku im Netz, sonst nach `data/saku-paket.tar.gz` ([Deploy](docs/DEPLOY.md)) |
| `python -m saku server` | Saku im Netz betreiben (gunicorn, nur mit `SAKU_PASSWORT`), z. B. auf Railway ([Deploy](docs/DEPLOY.md)) |

Die KI-Schritte der Analyse (Deckblätter, Aufgaben neu aufbauen, SQL-Sandboxen, Klassifikation, Wissensseiten und Begriffe, Lernpfad, Einführungen) laufen beim Erstlauf über das lokal installierte [Claude Code](https://code.claude.com) (`claude -p`, eigenes Login, kein API-Schlüssel nötig). Spätere Läufe und Sensei nutzen die Claude-API. Beide Wege teilen sich denselben Cache, eine schon beantwortete Anfrage kostet also nichts mehr. `python -m saku analyse --ohne-ki` läuft komplett lokal.

## Datensicherheit

- **Tägliche Sicherung:** Vor `start`, `init`, `analyse` und `lernstand import` sichert Saku die Datenbank einmal am Tag nach `data/backups/saku-JJJJ-MM-TT.db`; die letzten sieben bleiben. In den Einstellungen unter Daten gibt es außerdem „Jetzt sichern“.
- **Lernstand als Datei:** Der Export hängt nicht an internen IDs und übersteht einen Neuaufbau der Datenbank. Der Import übernimmt alles oder nichts; Zeilen und Einstellungen, die Saku nicht versteht, überspringt er.
- **Migrationen:** Ein neues Schema bringt `python -m saku init` (oder der nächste Start) auf die vorhandene Datenbank, nach der Sicherung und jede Migration in einer eigenen Transaktion.
- **Nur lokal:** Die App lauscht nur auf `127.0.0.1`, und schreibende Anfragen nimmt sie nur von sich selbst an (Schutz gegen fremde Webseiten im Browser). Im Netz (`python -m saku server`) nur hinter einem Passwort, siehe [Deploy](docs/DEPLOY.md).

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [Konzept](docs/KONZEPT.md) | Idee, Bereiche, Fahrschul-Lernlogik, Prüfungsreife |
| [Architektur](docs/ARCHITEKTUR.md) | Tech-Stack, Projektstruktur, Pipeline, Routen |
| [Design](docs/DESIGN.md) | Prinzipien, Farben, Typografie, Signature-Momente |
| [Sensei](docs/SENSEI.md) | KI-Tutor: Modi, Prompts, Chat mit Quellen, Kosten |
| [Roadmap](docs/ROADMAP.md) | Phasen, Demo-Ablauf, Risiken |
| [Deploy](docs/DEPLOY.md) | Saku privat im Netz (Railway): Login, Paket hochladen, Lernstand, Kosten |
| [Schema](db/schema.sql) | SQLite-Datenbank mit Sichten und Volltextsuche |

## Technik

Python 3.12+ · Flask · SQLite mit FTS5 · PyMuPDF · Claude-API und Claude Code · fastembed · scikit-learn · Basecoat (shadcn/ui-Look) · htmx · FSRS · networkx · force-graph · pywebview

## Daten und Urheberrecht

IHK-Prüfungen sind urheberrechtlich geschützt. **Dieses Repo enthält keinerlei Prüfungsinhalte.** PDFs, erzeugte Bildausschnitte, Themenliste, Modelle und die Datenbank liegen im Ordner `data/`, der per `.gitignore` ausgeschlossen ist. Tests und Bilder nutzen nur erfundene Aufgaben. Saku ist für den privaten Gebrauch mit selbst gekauften Prüfungen gedacht.

Für die KI-Funktionen werden Aufgabentexte an die Claude-API übertragen. Der API-Schlüssel steht nur in der lokalen `.env`.

## Bildnachweise

Die Bildbänder der Bereiche nutzen Fotos von [Unsplash](https://unsplash.com) (Unsplash-Lizenz): Ayumi Kubo (Heute, Einführung), Nguyen Minh (Lernpfad), Dino Sabic (Üben), Ricky T (Prüfung), Shigeki Wakabayashi (Themen), Masahiro Miyagi (Sensei), Andre Benz (Analyse) und Grant Lee (満開).
