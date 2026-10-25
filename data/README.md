# data/

Hier liegen alle privaten Daten. **Außer dieser Datei und `themen.example.md` landet nichts aus diesem Ordner im Git-Repo** (siehe `.gitignore`).

```text
data/
├── README.md             diese Datei
├── themen.example.md     Beispiel für das Format der Themenliste
├── themen.md             deine Themenliste                 (selbst anlegen)
├── quellen/              gekaufte Prüfungen, PDFs und ZIPs (selbst anlegen)
├── pdfs/                 Prüfungen und Lösungshinweise     (selbst anlegen oder per sammeln)
├── bilder/               Originale der Kopfzeilen-Bilder   (optional)
├── aufgaben/             Bildausschnitte                   (erzeugt die Pipeline)
├── tessdata/             deutsches Sprachpaket für Tesseract (nur für gescannte PDFs)
├── modelle/              Vektormodell von fastembed, ca. 220 MB (lädt der Schritt vektoren)
├── projekt/              Text der eigenen Projektdokumentation (Fachgespräch üben)
├── backups/              tägliche Sicherungen, die letzten 7 (erzeugt Saku)
└── saku.db               Katalog und Lernstand             (erzeugt python -m saku init)
```

## quellen/ und pdfs/

Neue Prüfungen am einfachsten unsortiert nach `quellen/` legen, auch als ZIP. `python -m saku.pipeline.sammeln` sucht daraus die Prüfungen für AE, SI, AP1 und WiSo heraus und kopiert sie nach `pdfs/`, danach `python -m saku analyse`.

In `pdfs/` liegen alle Prüfungen und Lösungshinweise als PDF, in beliebigen Unterordnern und mit beliebigen Dateinamen. Termin, Prüfungsbereich und Art liest die Pipeline aus dem Deckblatt. Dubletten werden über den Hash erkannt und übersprungen.

## themen.md

Die Themenliste mit den Prüfungsbereichen von AP1 und AP2. Das empfohlene Format steht in [themen.example.md](themen.example.md):

- `#` Prüfungsbereich
- `##` Thema
- `-` Unterthema, optional mit Stichworten nach einem Doppelpunkt

Eine Liste in einem anderen Format bringt die Pipeline einmalig mit der KI in diese Struktur.

## Sichern

Der Lernstand steckt komplett in `saku.db`. Saku sichert sie vor `start`, `init`, `analyse` und `lernstand import` einmal am Tag nach `backups/saku-JJJJ-MM-TT.db` (die letzten sieben bleiben), in den Einstellungen auch auf Knopfdruck. Zurückholen: App schließen, die Sicherung als `saku.db` an ihren Platz kopieren.

Unabhängig von der Datenbank nimmt `python -m saku lernstand export DATEI` den Lernstand als JSON-Datei mit; `lernstand import` übernimmt ihn auch in eine neu aufgebaute Datenbank.
