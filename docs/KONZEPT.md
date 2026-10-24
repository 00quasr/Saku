# Saku 咲く – Konzept

> **咲く (saku)** heißt „erblühen“. Saku ist ein persönlicher Trainer für die IHK-Abschlussprüfung Teil 2 (AP2): die Systematik einer Fahrschul-App, die Ruhe japanischer Gestaltung und ein KI-Tutor, der jede Aufgabe kennt.

## Die Idee

Wer für die AP2 lernt, sitzt vor einem Stapel alter Prüfungen und weiß nicht, wo er anfangen soll. Fahrschul-Apps haben dieses Problem längst gelöst: Es gibt einen festen Fragenkatalog, jede Frage hat einen Lernstand, und eine Anzeige sagt ehrlich, ob man bereit ist. Saku überträgt dieses Prinzip auf die AP2, und zwar mit den echten Prüfungen, die man gekauft hat.

Aus den PDFs wird ein Aufgabenkatalog, aus der Themenliste ein Lernpfad. Jede Teilaufgabe wird gelernt, bis sie sitzt. Wissen wächst dabei wie ein Garten: Themen keimen, knospen und blühen auf, bis zur vollen Blüte, 満開 (*mankai*). Das ist der Moment, in dem man prüfungsreif ist.

## Rahmen

| | |
|---|---|
| **Für wen** | Azubis vor der AP2, zuerst für den eigenen Gebrauch. Beruf und Prüfungsbereiche ergeben sich aus den Prüfungs-PDFs. |
| **Wo** | Nur lokal auf dem eigenen Rechner, ohne Konto und ohne Server im Internet |
| **Inhalte** | Selbst gekaufte IHK-Prüfungen samt Lösungshinweisen, ausschließlich privat genutzt |
| **KI** | Claude-API für Analyse und Tutor. Aufgabentexte werden dafür an die API übertragen. |
| **Entstehung** | Projekt im Python-Kurs |

## Leitsätze

1. **Echte Prüfungen statt ausgedachter Fragen.** Gelernt wird mit Original-Aufgaben. Die KI erklärt, ergänzt und prüft, aber der Lösungshinweis bleibt die Referenz.
2. **Lernen, wo die Punkte liegen.** Was in den Prüfungen oft und mit vielen Punkten vorkam, kommt im Lernpfad früher und zählt bei der Prüfungsreife mehr.
3. **Ehrlich messen.** Eine Teilaufgabe ist erst sicher, wenn sie zweimal hintereinander klappt. Die Prüfungsreife beschönigt nichts.
4. **Ruhe statt Reizüberflutung.** Eine Sache pro Bildschirm, viel Weißraum, alles per Tastatur bedienbar.
5. **Privat und lokal.** Prüfungen, Datenbank und Lernstand bleiben auf dem eigenen Rechner und landen nie im Git-Repo.

## Die Bereiche

| | Name | Bedeutung | Was dort passiert |
|---|---|---|---|
| 今日 | **Heute** | heute | Startseite: Tagesziel, fällige Wiederholungen, Countdown, Prüfungsreife |
| 道 | **Michi** | Weg | Der Lernpfad: Stationen in sinnvoller Reihenfolge, jede mit Einführung, Übungen und Mini-Test |
| 稽古 | **Keiko** | Übung | Der Fokusmodus: Aufgabe lesen, Lösung aufdecken, sich selbst bewerten |
| 試験 | **Shiken** | Prüfung | Prüfungssimulation mit Timer, Punkte-Hochrechnung, Note und Stempel |
| 庭 | **Niwa** | Garten | Der Knowledge Graph: alle Themen als Garten, der mit dem Wissen aufblüht |
| 先生 | **Sensei** | Lehrer | Der KI-Tutor, überall erreichbar: Tipps, Erklärungen, Antworten prüfen, Übungsvarianten |
| 分析 | **Bunseki** | Analyse | Auswertung aller Prüfungen: Inventar, Themen-Heatmap, Dauerbrenner, Lücken |
| ⌘K | **Suche** | | Befehlspalette: Volltextsuche über alle Prüfungen, Sprung zu jedem Bereich |

## Lernlogik: das Fahrschul-Prinzip

### Die Lerneinheit

Die kleinste Lerneinheit ist die **Teilaufgabe**, zum Beispiel Aufgabe 3 b. Sie entspricht einer Frage in der Fahrschul-App: Sie hat Punkte, ein oder mehrere Themen, einen Lösungshinweis und einen eigenen Lernstand. Angezeigt wird sie immer mit dem Kontext ihrer Aufgabe, also mit der Situationsbeschreibung, auf die sie sich bezieht.

### Ablauf in Keiko

1. Die Teilaufgabe erscheint als Bildausschnitt aus dem Original-PDF. Tabellen und Diagramme bleiben so erhalten.
2. Man überlegt sich die Antwort oder tippt sie ein.
3. Die **Leertaste** deckt den Lösungshinweis auf.
4. Man bewertet sich selbst: **1** Nicht gewusst · **2** Teilweise · **3** Gewusst. Alternativ prüft Sensei die getippte Antwort und schlägt eine Bewertung vor.
5. Die nächste Teilaufgabe erscheint. Darunter steht, wo es eine ähnliche Aufgabe schon einmal gab.

### Lernstand

| Status | Farbe | Bedeutung | Regel |
|---|---|---|---|
| Neu | Grau | noch nie bearbeitet | Startzustand |
| Wackelig | Rot | zuletzt nicht gewusst | nach Bewertung 1 |
| Im Aufbau | Gelb | auf dem Weg | nach Bewertung 2 oder nach einmal „Gewusst“ |
| Sicher | Grün | sitzt | **zweimal hintereinander „Gewusst“** |

Bewertung 1 oder 2 setzt die Serie zurück. Auch eine sichere Teilaufgabe wird wieder rot oder gelb, wenn sie bei einer Wiederholung danebengeht.

### Wiederholung

Wann eine Teilaufgabe wiederkommt, berechnet der FSRS-Algorithmus (wie in Anki) aus den bisherigen Bewertungen. Das längste Intervall endet am Prüfungstermin, damit vor der Prüfung nichts aus dem Blick gerät.

Zusätzlich gibt es wie in der Fahrschul-App:

- **Fehlerkorb:** alle roten Teilaufgaben zum gezielten Nacharbeiten
- **Markiert:** Teilaufgaben, die man sich merken will
- **Freies Üben:** jedes Thema jederzeit, unabhängig vom Lernpfad

## Lernpfad (Michi 道)

Der Lernpfad ist wie ein Weg aus Trittsteinen (飛び石 *tobi-ishi*) durch einen japanischen Garten angelegt. Jede **Station** bündelt ein Thema, meist mit 8 bis 15 Teilaufgaben.

Eine Station besteht aus drei Teilen:

1. **Einführung:** Sensei erklärt das Thema kurz und verständlich, abgestimmt auf das, was in den Prüfungen tatsächlich gefragt wurde.
2. **Übungen:** die echten Teilaufgaben des Themas, nach dem Fahrschul-Prinzip.
3. **Mini-Test:** fünf Teilaufgaben aus dem Thema. Ab 80 % der Punkte ist die Station geschafft, und die nächste wird freigeschaltet. Anklickbare Teilaufgaben und SQL mit Sandbox prüft Saku selbst (die Punkte sind vorbelegt und bleiben änderbar), den Rest bewertet man nach dem Lösungshinweis selbst.

Die **Reihenfolge** entsteht bei der Analyse. Grundlagen kommen vor den Themen, die darauf aufbauen; die Abhängigkeiten schlägt die KI vor. Unter den möglichen nächsten Themen kommt zuerst das, was in den Prüfungen die meisten Punkte bringt. Die Reihenfolge lässt sich jederzeit von Hand anpassen.

Gesperrt ist nur der Pfad selbst. In Keiko kann jedes Thema jederzeit geübt werden.

## Heute (今日)

Die Startseite beantwortet eine einzige Frage: *Was mache ich jetzt?*

- **Countdown:** Tage bis zur Prüfung
- **Tagesziel:** neue Teilaufgaben und fällige Wiederholungen für heute
- **Weiterlernen:** ein Knopf (oder Enter), der dort weitermacht, wo es am meisten bringt
- **Nächste Station** im Lernpfad
- **Prüfungsreife** als Ensō (siehe unten)
- **Lernserie:** wie viele Tage in Folge gelernt wurde
- **Wochenrückblick** (auch oben im Verlauf, sobald in den letzten 7 Tagen bewertet wurde): Bewertungen gegen die 7 Tage davor, neu sicher gewordene Teilaufgaben, Anteil „gewusst“, stärkstes und schwächstes Thema, Rechenübungen

So berechnet sich das Tagesziel:

```text
Lerntage  = Tage bis zur Prüfung − Puffer (Standard: 7 Tage für Simulationen), mindestens 1
Neu heute = aufrunden(Anzahl neuer Teilaufgaben ÷ Lerntage), mindestens 10
Heute     = Neu heute + fällige Wiederholungen
```

Ist das Tagesziel geschafft, geht es mit „Weiter üben“ in eine Extra-Runde mit 10 weiteren neuen Teilaufgaben. Mit ← geht es eine Karte zurück; deren Bewertung wird dabei zurückgenommen.

### Fahrplan (日程)

Countdown, Prüfungsreife und ⌘K führen zum Blick nach vorn (`/fahrplan`): *Schaffe ich bis zur Prüfung alles?*

- **Prognose:** Säulen für die nächsten 14 oder 30 Tage. Heute zählt, was das Tagesziel noch offen hat; danach die schon geplanten Wiederholungen (`karte.faellig_am`) und die neuen, die das Tagesziel an jenem Tag verlangen wird.
- **Tempo:** neue Teilaufgaben am Tag im Schnitt der letzten 7 Lerntage vor heute. Daraus das Datum, an dem alle einmal gesehen sind, verglichen mit dem Termin; reicht es nicht bis zum letzten Lerntag vor dem Puffer, steht dabei, wie viele am Tag es bräuchte.
- **Abdeckung:** Anteil der bisher erzielbaren Prüfungspunkte, die sicher sitzen, im Aufbau sind (gelb und rot) oder noch nie geübt wurden, gesamt, je Bereich und je Thema.
- **Was am meisten bringt:** die 8 Themen mit dem größten erwarteten Gewinn = Prüfungspunkte × (1 − Lernstand), jeweils mit „üben“.

## Prüfungsreife

Wie in der Fahrschul-App zeigt eine einzige Zahl, wie bereit man ist. Sie rechnet in Punkten und gewichtet dadurch automatisch nach Prüfungsrelevanz:

```text
Prüfungsreife = (Punkte sicherer Teilaufgaben + ½ × Punkte im Aufbau) ÷ Punkte aller Teilaufgaben
```

Ein Thema, das in jeder Prüfung 20 Punkte bringt, hat entsprechend viele Teilaufgaben und zählt deshalb viel stärker als ein Randthema. Ältere Prüfungen im früheren Format können mit geringerem Gewicht eingehen.

| Prüfungsreife | Anzeige |
|---|---|
| unter 50 % | Noch nicht bereit |
| 50 bis 79 % | Auf dem Weg |
| ab 80 % **und** die letzten zwei Simulationen bestanden | 満開 *mankai*, volle Blüte: prüfungsreif |

Dargestellt wird sie als **Ensō** (円相), der Zen-Kreis aus einem einzigen Pinselstrich. Er schließt sich, je näher man der Prüfungsreife kommt.

## Prüfungssimulation (Shiken 試験)

Saku stellt aus Aufgaben verschiedener Jahrgänge eine neue, vollständige Prüfung zusammen, also eine Prüfung, die es so nie gab. Aufbau, Punkte und Bearbeitungszeit übernimmt Saku aus den Deckblättern der echten Prüfungen. Bevorzugt werden Aufgaben, die noch nicht sitzen.

- Während der Simulation läuft ein Timer, und Sensei ist pausiert, wie im Prüfungsraum.
- Antworten werden in Textfelder getippt; anklickbare Teilaufgaben (Auswahl, Reihenfolge, Zuordnung, Zahl) werden angeklickt.
- Nach Ablauf der Zeit erscheinen die Lösungshinweise. Anklickbare Teilaufgaben und SQL mit Sandbox (verglichen mit der Musterlösung, mit Kurzhinweis wie „2 Zeilen fehlen“; läuft die Anweisung nicht, 0 Punkte mit der Meldung) bewertet Saku selbst vor. Die übrigen Punkte vergibt man selbst oder lässt sie von Sensei vorschlagen; jeder Vorschlag bleibt änderbar.
- Die Summe wird auf 100 Punkte umgerechnet und nach dem IHK-Notenschlüssel bewertet.

| Punkte | Note |
|---|---|
| 100 bis 92 | 1 – sehr gut |
| unter 92 bis 81 | 2 – gut |
| unter 81 bis 67 | 3 – befriedigend |
| unter 67 bis 50 | 4 – ausreichend |
| unter 50 bis 30 | 5 – mangelhaft |
| unter 30 bis 0 | 6 – ungenügend |

Ab 50 Punkten gilt die Simulation als bestanden, und ein roter Stempel 合格 (*gōkaku*, bestanden) landet auf dem Ergebnis. Unter 50 Punkten erscheint stattdessen ein grauer Stempel 再 (*sai*, noch einmal), zusammen mit den Themen, die die meisten Punkte gekostet haben.

> Die Hochrechnung ist eine Lernhilfe. Die tatsächlichen Bestehensregeln der AP2, etwa die Gewichtung der Prüfungsbereiche und die mündliche Ergänzungsprüfung, sind komplexer.

## Garten (Niwa 庭)

Der Knowledge Graph zeigt alle Themen als Garten:

- **Jeder Knoten ist ein Thema.** Seine Größe zeigt, wie viele Punkte das Thema in den Prüfungen gebracht hat.
- **Die Farbe zeigt den Lernstand**, von Rot über Gelb bis Grün.
- **Wachstumsstufen:** 種 Samen (0 %), 芽 Keim (bis 39 %), 蕾 Knospe (bis 79 %), 花 Blüte (ab 80 %)
- **Linien** verbinden Themen, die oft gemeinsam in einer Aufgabe vorkommen. Pfeile zeigen Voraussetzungen.
- **Ein Klick auf ein Thema** öffnet eine Seitenleiste mit allen Teilaufgaben, dem Lernstand und den Knöpfen „Üben“ und „Sensei erklärt“.

Wer lernt, sieht den Garten Woche für Woche aufblühen.

## Analyse (Bunseki 分析)

Das Ergebnis der Dokumentenanalyse, jederzeit abrufbar:

- **Inventar:** alle Prüfungen mit Termin, Prüfungsbereich, Seiten, Text oder Scan und ob die Lösung vorhanden ist
- **Themen-Heatmap:** Zeilen sind Themen, Spalten die Prüfungstermine, die Farbintensität zeigt die Punkte
- **Dauerbrenner:** Themen, die in mindestens 70 % der Prüfungen vorkamen
- **Lange nicht dran:** Themen, deren letzter Auftritt mehr als drei Termine zurückliegt (ein Hinweis, keine Vorhersage)
- **Nie geprüft:** Themen aus der Liste ohne eine einzige Aufgabe
- **Ohne Thema:** Teilaufgaben, die zu keinem Thema passen, ein Zeichen für Lücken in der Themenliste
- **KI-Nutzung:** Anzahl der Anfragen und verbrauchte Tokens

## Suche (⌘K)

**Strg + K** (Mac: ⌘K) öffnet überall eine Befehlspalette. Schon beim Tippen erscheinen passende Teilaufgaben aus allen Prüfungen. Die Suche findet auch Wortteile, „netz“ findet also „Firmennetzwerk“. Außerdem springt sie zu Bereichen und Themen.

## Sensei (先生)

Der KI-Tutor ist in jedem Bereich erreichbar und kennt immer den Kontext: die aktuelle Teilaufgabe, ihren Lösungshinweis und das Thema. Er gibt Tipps, erklärt, prüft getippte Antworten, erzeugt ähnliche Übungen, führt in Themen ein und beantwortet freie Fragen über alle Prüfungen mit Quellenangaben. Details stehen in [SENSEI.md](SENSEI.md).

## Bewusst nicht dabei

- Kein Online-Betrieb, keine Benutzerkonten, keine Synchronisation
- Keine Veröffentlichung von Prüfungsinhalten, auch nicht in Auszügen
- Keine Bewertung ohne Kontrolle: Vorschläge der KI bestätigt immer der Mensch
- Kein Ersatz für Ausbildung und Berufsschule

## Rechtliches und Daten

- Die IHK-Prüfungen sind urheberrechtlich geschützt. Saku verarbeitet sie ausschließlich für den privaten Gebrauch.
- PDFs, erzeugte Bildausschnitte und die Datenbank liegen in `data/` und sind per `.gitignore` vom Repo ausgeschlossen. Das Repo enthält keinerlei Prüfungsinhalte.
- Für Analyse und Tutor werden Aufgabentexte, Lösungshinweise und eigene Antworten an die Claude-API übertragen.
- Der API-Schlüssel steht nur in der lokalen `.env`-Datei.

---

Weiter: [Architektur](ARCHITEKTUR.md) · [Design](DESIGN.md) · [Sensei](SENSEI.md) · [Roadmap](ROADMAP.md)
