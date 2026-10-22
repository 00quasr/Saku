# data/

Hier liegen alle privaten Daten. **Außer dieser Datei und `themen.example.md` landet nichts aus diesem Ordner im Git-Repo** (siehe `.gitignore`).

```text
data/
├── README.md             diese Datei
├── themen.example.md     Beispiel für das Format der Themenliste
├── themen.md             deine AP2-Themenliste            (selbst anlegen)
├── quellen/              gekaufte Prüfungen, PDFs und ZIPs (selbst anlegen)
├── pdfs/                 Prüfungen und Lösungshinweise     (selbst anlegen oder per sammeln)
├── bilder/               Originale der Kopfzeilen-Bilder   (optional)
├── aufgaben/             Bildausschnitte                   (erzeugt die Pipeline)
└── saku.db               Katalog und Lernstand             (erzeugt python -m saku init)
```

## quellen/ und pdfs/

Neue Prüfungen am einfachsten unsortiert nach `quellen/` legen, auch als ZIP. `python -m saku.pipeline.sammeln` sucht daraus die FIAE- und WiSo-Prüfungen heraus und kopiert sie nach `pdfs/`, danach `python -m saku analyse`.

In `pdfs/` liegen alle Prüfungen und Lösungshinweise als PDF, in beliebigen Unterordnern und mit beliebigen Dateinamen. Termin, Prüfungsbereich und Art liest die Pipeline aus dem Deckblatt. Dubletten werden über den Hash erkannt und übersprungen.

## themen.md

Die AP2-Themenliste. Das empfohlene Format steht in [themen.example.md](themen.example.md):

- `#` Prüfungsbereich
- `##` Thema
- `-` Unterthema, optional mit Stichworten nach einem Doppelpunkt

Eine Liste in einem anderen Format bringt die Pipeline einmalig mit der KI in diese Struktur.

## Sichern

Der Lernstand steckt komplett in `saku.db`. Zum Sichern genügt es, diese Datei zu kopieren, am besten während die App geschlossen ist.
