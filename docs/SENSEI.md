# Sensei 先生 – der KI-Tutor

Sensei ist der KI-Tutor von Saku. Er läuft über die Claude-API und kennt in jedem Moment den Kontext: die Teilaufgabe, die Einleitung ihrer Aufgabe, den Lösungshinweis, das Thema und den eigenen Lernstand. Außerdem hilft dieselbe Anbindung der Pipeline beim Analysieren.

## Modi

| Modus | Taste | Was Sensei tut |
|---|---|---|
| Tipp | `T` | gibt einen Denkanstoß, ohne die Lösung zu verraten |
| Erklären | `E` | erklärt den Lösungsweg Schritt für Schritt |
| Antwort prüfen | `P` | vergleicht die getippte Antwort mit dem Lösungshinweis, schätzt die Punkte und schlägt eine Bewertung vor |
| Ähnliche Übung | `V` | erzeugt eine neue Übung zum selben Können, z. B. mit anderen Zahlen, samt Lösung |
| Thema erklären | – | Einführung für eine Station im Lernpfad oder ein Thema im Garten |
| Frag Sensei | `S` | freier Chat über alle Prüfungen, mit Quellenangaben |

Während einer Prüfungssimulation ist Sensei pausiert.

## Modelle

Zwei Rollen, beide in `.env` einstellbar:

| Rolle | Variable | Wofür |
|---|---|---|
| schnell | `SAKU_MODELL_SCHNELL` (Haiku) | Deckblätter lesen, Teilaufgaben klassifizieren, Suchbegriffe bilden |
| stark | `SAKU_MODELL_STARK` (Sonnet) | alle Tutor-Modi, Antworten prüfen, Lernpfad, Einführungen |

Aktuelle Modellnamen: [Claude-Dokumentation, Modellübersicht](https://platform.claude.com/docs/en/about-claude/models/overview).

## Kontext

Jede Anfrage zu einer Teilaufgabe bekommt einen Kontextblock. Die Kennung `T123` ist die ID der Teilaufgabe. Die App macht daraus einen Link wie „Winter 2024/25 · Aufgabe 3 b“.

```xml
<aufgabe kennung="T123" termin="Winter 2024/25" bereich="…" punkte="6" thema="…">
  <ausgangssituation>…</ausgangssituation>
  <einleitung>…</einleitung>
  <teilaufgabe>…</teilaufgabe>
  <loesungshinweis>…</loesungshinweis>
</aufgabe>
```

Bei Teilaufgaben, deren Inhalt vor allem aus einer Grafik besteht (Netzplan, Diagramm, Tabelle), wird zusätzlich der Bildausschnitt mitgeschickt.

## Systemprompt

```text
Du bist Sensei, ein geduldiger Tutor für die IHK-Abschlussprüfung Teil 2 (AP2).
Du hilfst einer Person in der Ausbildung, echte Prüfungsaufgaben zu verstehen und zu lösen.

Regeln:
- Antworte auf Deutsch, in der Du-Form, klar und knapp. Nutze Markdown sparsam.
- Der Lösungshinweis ist deine Referenz. Er zeigt eine mögliche Lösung;
  andere fachlich richtige Antworten sind ebenfalls gültig.
- Rechne Schritt für Schritt und prüfe jedes Ergebnis, bevor du es nennst.
- Wenn du dir unsicher bist, sag es offen.
- Beziehe dich nur auf Aufgaben aus dem Kontext und nenne sie mit ihrer Kennung
  in eckigen Klammern, z. B. [T123]. Erfinde keine Prüfungsinhalte.
```

## Anweisungen je Modus

**Tipp**
```text
Gib genau einen Denkanstoß in höchstens drei Sätzen.
Verrate weder das Ergebnis noch den vollständigen Lösungsweg.
```

**Erklären**
```text
Erkläre den Lösungsweg Schritt für Schritt: zuerst das Grundprinzip in einem Satz,
dann die Schritte, zum Schluss typische Fehler bei dieser Art von Aufgabe.
```

**Antwort prüfen** – Sensei muss über das Werkzeug `bewertung_abgeben` antworten (`tool_choice` auf dieses Werkzeug gesetzt). So kommt immer gültiges JSON zurück:

```json
{
  "name": "bewertung_abgeben",
  "description": "Bewertet eine Antwort im Vergleich zum Lösungshinweis.",
  "input_schema": {
    "type": "object",
    "properties": {
      "punkte":     { "type": "number", "description": "geschätzte Punkte" },
      "max_punkte": { "type": "number" },
      "richtig":    { "type": "array", "items": { "type": "string" } },
      "fehlt":      { "type": "array", "items": { "type": "string" } },
      "hinweis":    { "type": "string", "description": "ein Satz, wie die Antwort vollständig wird" }
    },
    "required": ["punkte", "max_punkte", "richtig", "fehlt", "hinweis"]
  }
}
```

Die App schlägt daraus eine Bewertung vor: ab 80 % der Punkte **3** Gewusst, ab 40 % **2** Teilweise, darunter **1** Nicht gewusst. Bestätigt wird mit der jeweiligen Taste, übernommen wird nie automatisch.

**Ähnliche Übung**
```text
Erstelle eine neue Aufgabe, die dieselbe Fähigkeit prüft, mit anderen Werten und
einer anderen Situation, im Stil einer AP2-Aufgabe. Gib danach unter der Überschrift
„Lösung“ eine vollständige Musterlösung.
```
Die Übung wird in der App deutlich als „KI-Übung, keine IHK-Aufgabe“ gekennzeichnet.

**Thema erklären**
```text
Erkläre das Thema in höchstens 200 Wörtern so, wie es in der AP2 gebraucht wird.
Nenne danach die typischen Aufgabentypen dazu, gestützt auf die Beispiele im Kontext.
```

## Frag Sensei: Chat mit Quellen

Der freie Chat nutzt Retrieval-Augmented Generation (RAG). Sensei bekommt nicht alle Prüfungen, sondern nur die passenden Teilaufgaben:

1. **Suchbegriffe:** Das schnelle Modell macht aus der Frage drei bis fünf Suchbegriffe.
2. **Suche:** Die FTS5-Tabelle `suche` liefert die besten acht Teilaufgaben samt Lösungshinweis (sortiert nach `bm25`).
3. **Antwort:** Das starke Modell antwortet mit diesen Kontextblöcken und nennt Quellen als `[T123]`.
4. **Anzeige:** Die App macht aus jeder Kennung einen Link, der die Teilaufgabe in Keiko öffnet.

Beispiel: „Was wurde zu RAID schon gefragt?“ ergibt eine Übersicht über alle RAID-Aufgaben mit Termin und Punkten, jede direkt anklickbar.

## Sensei in der Pipeline

**Deckblatt lesen** (schnell, nur wenn die Muster nicht greifen): Werkzeug `deckblatt` mit `jahr`, `saison`, `bereich`, `beruf`, `dauer_min`, `art`, `format`.

**Klassifikation** (schnell): Werkzeug `themen_zuordnen`

```json
{
  "name": "themen_zuordnen",
  "input_schema": {
    "type": "object",
    "properties": {
      "themen": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "thema_id": { "type": "integer" },
            "gewicht":  { "type": "number", "description": "Anteil, alle zusammen 1" }
          },
          "required": ["thema_id", "gewicht"]
        }
      },
      "typ": { "type": "string", "enum": ["erklaeren", "berechnen", "zeichnen", "code", "sql", "tabelle", "auswahl", "sonstiges"] },
      "sicherheit": { "type": "number", "description": "0 bis 1" }
    },
    "required": ["themen", "typ", "sicherheit"]
  }
}
```

Teilaufgaben mit einer Sicherheit unter 0,6 markiert Bunseki zur Kontrolle.

**Lernpfad** (stark): Werkzeug `voraussetzungen_vorschlagen` mit einer Liste aus `thema_id`, `voraussetzung_id` und `begruendung`.

## Kosten im Griff

- **Cache:** Anfragen mit identischem Inhalt werden aus `ki_cache` beantwortet. Ein zweiter Pipeline-Lauf kostet so fast nichts. Für den Chat gilt das nicht.
- **Prompt-Caching:** Gleichbleibende Teile wie Systemprompt und Themenliste werden bei der API als cachebar markiert.
- **Batch-API:** Die einmalige Klassifikation aller Teilaufgaben kann über die Batch-API laufen. Das ist günstiger, die Ergebnisse kommen aber zeitversetzt.
- **Protokoll:** Jeder Aufruf landet mit Tokens in `ki_aufruf`. Bunseki zeigt die Summen.

## Fehler und Grenzen

- **Kein API-Schlüssel:** Die Sensei-Knöpfe sind ausgegraut, mit einem Hinweis, wo der Schlüssel hingehört. Alles andere funktioniert weiter.
- **Keine Verbindung:** Eine freundliche Meldung, die Lösung bleibt sichtbar. Das SDK wiederholt fehlgeschlagene Anfragen automatisch.
- **KI kann sich irren:** Der Lösungshinweis bleibt immer sichtbar. Bewertungen und Punkte schlägt Sensei nur vor.
- **Fehlender Lösungshinweis:** Sensei erklärt trotzdem, aber mit dem sichtbaren Hinweis, dass es keine offizielle Lösung gibt.

## Ausbaustufe: Werkzeuge für exakte Rechnungen

Sprachmodelle können sich verrechnen. Für Rechenaufgaben bekommt Sensei deshalb Werkzeuge, die Python ausführt, zum Beispiel:

- `subnetz_berechnen`: Netzadresse, Broadcast, Hostbereich und Anzahl der Hosts mit Pythons `ipaddress`-Modul
- `zahlensystem_umrechnen`: Binär, Dezimal, Hexadezimal

Sensei ruft das Werkzeug auf, Saku rechnet in Python und gibt das exakte Ergebnis zurück. In der Kurspräsentation zeigt das gut, wie Python und KI zusammenarbeiten.
