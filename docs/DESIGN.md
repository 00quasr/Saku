# Design

Saku soll sich anfühlen wie ein aufgeräumter Schreibtisch in einem japanischen Teehaus: ruhig, klar, nichts lenkt ab. Die Systematik kommt aus der Fahrschul-App, die Ästhetik aus Japan, die Bausteine aus shadcn/ui über Basecoat.

## Vier Prinzipien

| Prinzip | Bedeutung | Was das in Saku heißt |
|---|---|---|
| 間 **Ma** | der Raum dazwischen | Weißraum ist Gestaltungsmittel. Eine Hauptaufgabe pro Bildschirm, 48 bis 96 px zwischen Abschnitten. |
| 簡素 **Kanso** | Schlichtheit | Nur, was hilft. Keine Dekoration ohne Funktion, genau eine Akzentfarbe. |
| 渋い **Shibui** | stille Eleganz | Gedeckte Farben, feine Linien statt Schatten, ruhige Typografie. |
| 侘寂 **Wabi-sabi** | Schönheit des Unvollkommenen | Pinselstrich-Ensō, leicht unregelmäßige Trittsteine, Stempel mit Tuschekanten. Bewusst nur an wenigen Stellen. |

## Farben

Die Palette stammt aus traditionellen japanischen Farben: Papier, Tusche und ein einziges Zinnoberrot.

### Hell: Washi (Papier)

| Token | Farbe | Name | Einsatz |
|---|---|---|---|
| `--washi` | `#F6F4EF` | 和紙 Washi-Papier | Hintergrund |
| `--washi-hell` | `#FBFAF7` | | Karten, Flächen |
| `--sumi` | `#1F1D1A` | 墨 Tusche | Text, primäre Knöpfe |
| `--sumi-mittel` | `#6B665D` | | Sekundärtext |
| `--linie` | `#E4DFD5` | | Linien, Rahmen |
| `--shu` | `#B8422B` | 朱 Zinnoberrot | **die** Akzentfarbe: Fokus, Stempel, aktuelle Station, Logo |
| `--ai` | `#2F4A63` | 藍 Indigo | alles von Sensei |
| `--beni` | `#A63A3A` | 紅 Karmin | Status „wackelig“, Fehler |
| `--yamabuki` | `#A97A22` | 山吹 Goldgelb | Status „im Aufbau“ (Füllung: Punkte, Balken) |
| `--yamabuki-text` | `#88621B` | | dasselbe Gelb als Schrift (4,5 : 1) |
| `--matcha` | `#547147` | 抹茶 Matcha | Status „sicher“ |

### Dunkel: Sumi (Tusche)

| Token | Farbe |
|---|---|
| `--washi` (Hintergrund) | `#141412` |
| `--washi-hell` (Flächen) | `#1C1B18` |
| `--sumi` (Text) | `#ECE8DF` |
| `--sumi-mittel` | `#A39E92` |
| `--linie` | `#2E2B27` |
| `--shu` | `#E06241` |
| `--ai` | `#8FA9C4` |
| `--beni` | `#D46A5E` |
| `--yamabuki` | `#D9AE4F` |
| `--matcha` | `#8DAA7A` |

Alle Textfarben erreichen mindestens 4,5 : 1 Kontrast, Statusfarben mindestens 3 : 1.

### Die Ampel

Die Fahrschul-Ampel nutzt gedeckte Töne statt grellem Rot, Gelb und Grün: 紅 Beni, 山吹 Yamabuki, 抹茶 Matcha. Neu ist grau (`--linie`). Zinnoberrot (`--shu`) ist nie eine Statusfarbe, damit der Akzent nicht mit „falsch“ verwechselt wird.

### Tuschestufen für die Heatmap

Die Heatmap in Bunseki färbt wie eine Tuschmalerei (墨の濃淡, *sumi no nōtan*): fünf Abstufungen von Papier zu Tusche.

```css
--tusche-1: color-mix(in oklab, var(--sumi)  8%, var(--washi));
--tusche-2: color-mix(in oklab, var(--sumi) 20%, var(--washi));
--tusche-3: color-mix(in oklab, var(--sumi) 38%, var(--washi));
--tusche-4: color-mix(in oklab, var(--sumi) 60%, var(--washi));
--tusche-5: color-mix(in oklab, var(--sumi) 85%, var(--washi));
```

### Anbindung an Basecoat

Basecoat versteht shadcn/ui-Themes. `saku/web/static/css/saku.css` setzt deshalb die shadcn-Variablen auf die Saku-Farben:

```css
:root {
  --background: var(--washi);         --foreground: var(--sumi);
  --card: var(--washi-hell);          --card-foreground: var(--sumi);
  --popover: var(--washi-hell);       --popover-foreground: var(--sumi);
  --primary: var(--sumi);             --primary-foreground: var(--washi);
  --secondary: #EDE9E1;               --secondary-foreground: var(--sumi);
  --muted: #EDE9E1;                   --muted-foreground: var(--sumi-mittel);
  --accent: #EDE9E1;                  --accent-foreground: var(--sumi);
  --destructive: var(--beni);
  --border: var(--linie);             --input: var(--linie);
  --ring: var(--shu);
  --radius: 0.375rem;
}

.dark {
  --secondary: #24221F;  --muted: #24221F;  --accent: #24221F;
  /* die Saku-Tokens bekommen hier ihre dunklen Werte */
}
```

**Standard ist Dunkel (Sumi).** Das dunkle Schema hängt an der Klasse `dark` auf `<html>`. Ist in den Einstellungen „Hell“ oder „Dunkel“ gewählt, setzt der Server die Klasse. Bei „System“ setzt eine Zeile im `<head>` sie passend zu `prefers-color-scheme`.

## Typografie

| Rolle | Schrift | Warum |
|---|---|---|
| Text und Oberfläche | **Inter** | sehr gut lesbar, tabellarische Ziffern |
| Titel und Kanji | **Shippori Mincho** | japanische Serifenschrift mit eleganten lateinischen Buchstaben |
| Code | **JetBrains Mono** | SQL, Pseudocode und Rechenwege |

| Stil | Schrift | Größe / Zeilenhöhe | Einsatz |
|---|---|---|---|
| Zahl groß | Inter 300, tabellarische Ziffern | 56 / 60 px | Prüfungsreife, Countdown |
| Titel | Shippori Mincho 600 | 32 / 40 px | Seitentitel |
| Überschrift | Shippori Mincho 600 | 22 / 30 px | Abschnitte |
| Text | Inter 400 | 16 / 26 px | Fließtext |
| Klein | Inter 400 | 13 / 20 px | Metadaten wie Termin und Punkte |
| Etikett | Inter 500, Versalien, Sperrung 0,12 em | 11 / 16 px | Bereichsnamen über Titeln |
| Code | JetBrains Mono 400 | 14 / 22 px | Codeblöcke |

Regeln:

- Zeilenlänge im Fließtext 60 bis 75 Zeichen
- Zahlen immer mit tabellarischen Ziffern (`font-variant-numeric: tabular-nums`), damit nichts springt
- Größen in `rem`, damit Strg + und Strg − alles mitskalieren
- Kanji nie allein: immer mit deutschem Wort daneben

Eine vollständige japanische Schrift ist mehrere Megabyte groß. Saku braucht nur rund 40 Zeichen, deshalb wird Shippori Mincho auf genau diese Zeichen plus lateinische Buchstaben reduziert:

```bash
pip install -r requirements-dev.txt
pyftsubset ShipporiMincho-SemiBold.ttf \
  --text-file=saku/web/static/fonts/zeichen.txt \
  --unicodes="U+0020-00FF,U+2013-2026" \
  --flavor=woff2 \
  --output-file=saku/web/static/fonts/shippori-mincho-saku.woff2
```

`zeichen.txt` enthält alle verwendeten Kanji und Kana. Kommt ein neues Zeichen dazu, wird der Befehl neu ausgeführt.

## Bereichs-Kopfzeilen

Jeder Bereich beginnt mit einem Bild: gläserne Prismen auf Schwarz, die im dunklen Schema weich in die Tusche auslaufen. Im hellen Schema sitzt das Bild als gerahmtes Fenster in der Inhaltsbreite. Keiko zeigt nur einen schmalen Streifen, damit der Fokusmodus ruhig bleibt.

| Bereich | Bild | Gedanke |
|---|---|---|
| 今日 Heute | Chevrons mit Licht in der Mitte | nach vorn |
| 道 Michi | Korridor aus Platten | der Weg |
| 稽古 Keiko | einzelner Würfel | Fokus |
| 試験 Shiken | Dreiecksraster in Rot und Gold | Struktur |
| 庭 Niwa | grüne Facetten | Garten |
| 先生 Sensei | Blau | Indigo `--ai` |
| 分析 Bunseki | Würfel mit Linse | Analyse |
| Willkommen, Leerzustand | violetter Würfel | Anfang |
| 満開, お疲れ様, 合格 | Stern aus Gold und Silber | Belohnung |

Makro: `{{ m.kopf('heute', '今日', 'Heute', 'Titel') }}` in `templates/_makros.html`.

## Layout und Abstände

- **Zwei Breiten:** Lesebreite 47,5 rem (Keiko, Michi, Verlauf, Texte von Sensei) und weit bis 110 rem, so breit wie das Bildband (Heute, Bunseki, Niwa), jeweils linksbündig neben der Seitenleiste; beide wachsen mit der Schrift
- **Navigation:** eine Seitenleiste links (232 px) mit Logo, dem Schalter für Beruf und Prüfungsteil, den Bereichen als Kanji und Wort und unten Sensei, Suche, Alle Seiten, Einstellungen und Tastenkürzel. Unter dem aktiven Bereich stehen seine Unterseiten eingerückt an einer Linie (z. B. Rechnen: Sprint, Probeprüfung, Formelsammlung), die aktuelle mit einem Strich in Zinnoberrot. Die Liste steht einmal in `SEITEN` (`saku/web/__init__.py`) und speist Seitenleiste, „Alle Seiten“ (`/seiten`, je Seite ein Satz) und ⌘K. Unter 1100 px bleiben nur die Zeichen (64 px), die Beschriftung steht im Tooltip, Unterseiten über „Alle Seiten“.
- **Handy (unter 720 px):** statt der Seitenleiste eine Tab-Leiste unten mit Heute, Üben, Rechnen, Prüfung und „Mehr“. „Mehr“ öffnet ein Blatt von unten mit allen Bereichen und Unterseiten, Sensei, Suche, Einstellungen und dem Umfang; Esc, daneben tippen und Zurück schließen es. Tippflächen mindestens 44 px, die Leiste hält Abstand zu `env(safe-area-inset-*)`, das Bildband ist niedriger. Auf Touch-Geräten ohne Maus verschwinden Tastenhinweise (`.taste`, ganze Sätze mit `.nur-tastatur`). Ein Satz verliert dabei nie Wörter: Tastenteile stehen in `.nur-tastatur`, nie im Platzhalter. Auf Touch und schmal sind Knöpfe und Felder 44 px hoch und Eingaben mindestens 16 px groß (sonst zoomt iOS). Tabellen mit Verlauf und Ergebnissen brechen schmal zu Zeilen um (Kopf nur vorgelesen, mehrdeutige Zellen nennen ihn per `data-titel`); die Notiz im Wissensgraph kommt als Blatt von unten.
- **Sensei:** ein Seitenpanel rechts (400 px), das über den Inhalt gleitet
- **Abstände:** nur aus der Reihe 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96 px
- **Flächen:** 1 px Linien in `--linie`, Ecken mit 6 px Radius, keine Schatten. Einzige Ausnahme sind schwebende Ebenen wie Suche und Sensei-Panel mit einem sehr weichen Schatten.
- **Zielgröße:** ein Desktop-Fenster ab 1024 px Breite und das Handy ab 360 px. Jede Seite passt ohne seitliches Scrollen; was breiter sein muss (Aufgaben-Tabellen, Diagramme, Code, die Reiter der Analyse), scrollt in seinem Kasten, und der Rand blendet aus, hinter dem noch etwas kommt (`saku.quer`). Dass der Rahmen mobil seitlich abschneidet, ist nur ein Sicherheitsnetz.

## Komponenten

**Aus Basecoat:** Button (primär in Tusche, sekundär, ghost), Card (nur Linie), Badge (Status), Progress (2 px hoch), Dialog (Suche), Tabs (Bunseki), Toast („Gespeichert“), Tooltip (Lesung und Bedeutung der Kanji), Input und Textarea (Antworten).

**Eigene Bausteine:**

| Baustein | Beschreibung |
|---|---|
| Ensō | Prüfungsreife als Pinselkreis, siehe unten |
| Hanko | Prüfungsstempel, siehe unten |
| Trittsteinpfad | der Lernpfad in Michi |
| Statuspunkt | 8 px Punkt in Ampelfarbe plus Symbol: ○ neu · ✕ wackelig · ◐ im Aufbau · ✓ sicher |
| Heatmap-Zelle | Quadrat in Tuschestufe, Tooltip mit Termin und Punkten |
| Bildausschnitt | Aufgabe aus dem PDF, passt sich dem Farbschema an |
| Sensei-Sprechblase | 2 px Linie links in Indigo (`--ai`), Etikett 先生 |
| Tastenhinweis | `<kbd>` in Klein, dezent umrandet |
| Formel | LaTeX in `$…$` (abgesetzt `$$…$$`) in Merkblättern und Rechenwegen, im Browser mit KaTeX gesetzt; Wörter darin in Inter, Zahlen deutsch (`3{,}47`, Einheiten in `\text{}`) |
| Sprungmarken | Abschnitte links, mitlaufend, der sichtbare markiert; schmal eine Reihe Chips oben (Einstellungen, Formelsammlung) |

**Bildausschnitte im Farbschema:** PDF-Ausschnitte haben einen weißen Hintergrund. Im hellen Schema verschmilzt er per `mix-blend-mode: multiply` mit dem Papier. Im dunklen Schema wird invertiert, sodass die Aufgabe hell auf Tusche erscheint. Ein Klick zeigt bei Bedarf das Original.

```css
.ausschnitt       { mix-blend-mode: multiply; }
.dark .ausschnitt { filter: invert(1) hue-rotate(180deg); mix-blend-mode: screen; }
```

## Bildschirme

Skizzen der drei wichtigsten Ansichten. Alle Inhalte sind Beispiele.

**Heute**

```text
 咲 Saku    今日 Heute   道 Michi   稽古 Keiko   試験 Shiken   庭 Niwa   …    ⌘K
 ──────────────────────────────────────────────────────────────────────────────

   おはよう · Guten Morgen
   Noch 38 Tage bis zur AP2

      ╭─────╮         Heute
      │ 64% │         12 neue Teilaufgaben · 18 Wiederholungen
      ╰──── ╯         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━──────────────   7 von 30
   Prüfungsreife
                      [ Weiterlernen  ↵ ]

   Nächste Station    ●────●────●────◐────○────○
                      Normalisierung · 4 von 9 sicher
```

**Keiko**

```text
 稽古 Keiko · Datenbanken › Normalisierung                              7 / 30
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━──────────────────────────────

   Winter 2024/25 · Aufgabe 3 b · 6 Punkte                       ☆ markieren

   ┌──────────────────────────────────────────────────────────────────┐
   │                                                                  │
   │   Aufgabe als Text, aus den PDF-Ausschnitten neu aufgebaut       │
   │                                                                  │
   └──────────────────────────────────────────────────────────────────┘

   Lösung zeigen  ␣                      先生  Tipp T · Erklären E · Prüfen P

   ── nach dem Aufdecken ──────────────────────────────────────────────

   Lösungshinweis
   ┌──────────────────────────────────────────────────────────────────┐
   │   Lösungshinweis als Text, das Original einen Klick entfernt    │
   └──────────────────────────────────────────────────────────────────┘

   Wie lief's?      1 Nicht gewusst      2 Teilweise      3 Gewusst

   Kam so ähnlich auch dran:  Sommer 2022 · 2 c   ·   Winter 2019/20 · 4 a
```

**Michi**

```text
 道 Michi · Lernpfad                                        Station 4 von 12

      ●   1  Grundlagen der Netzwerktechnik             花  sicher
      │
      ●   2  IPv4 und Subnetting                        花  sicher
      │
      ●   3  Routing                                    蕾  im Aufbau
      │
      ◐   4  Normalisierung              ← du bist hier
      ┊
      ○   5  SQL-Abfragen                                   gesperrt
      ┊
      ○   6  Projektplanung                                 gesperrt
```

## Signature-Momente

Sechs Stellen, an denen Saku bewusst mehr zeigt als nötig. Überall sonst gilt Kanso.

### 1. Ensō der Prüfungsreife

Ein Zen-Kreis aus einem Pinselstrich, der sich mit der Prüfungsreife schließt. Der Server setzt den Wert, CSS zeichnet den Strich beim Laden. Ein leichter Rauschfilter gibt ihm Tuschekanten.

```html
<svg class="enso" viewBox="0 0 120 120" role="img" aria-label="Prüfungsreife 64 Prozent">
  <defs>
    <filter id="pinsel">
      <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2"/>
      <feDisplacementMap in="SourceGraphic" scale="2.5"/>
    </filter>
  </defs>
  <circle class="enso-spur"   cx="60" cy="60" r="48"/>
  <circle class="enso-strich" cx="60" cy="60" r="48" pathLength="100" style="--wert: 64"/>
</svg>
```

```css
.enso-spur   { fill: none; stroke: var(--linie); stroke-width: 6; }
.enso-strich {
  fill: none; stroke: var(--sumi); stroke-width: 7; stroke-linecap: round;
  stroke-dasharray: 100; stroke-dashoffset: calc(100 - var(--wert));
  transform: rotate(-80deg); transform-origin: 50% 50%;
  filter: url(#pinsel);
  animation: enso-zeichnen 1.4s cubic-bezier(.65, 0, .35, 1) both;
}
@keyframes enso-zeichnen { from { stroke-dashoffset: 100; } }
```

Bei 満開 (prüfungsreif) schließt sich der Kreis und färbt sich Zinnoberrot.

### 2. Hanko-Stempel

Am Ende einer Simulation wird ein Stempel aufs Ergebnis gesetzt: 合格 in Zinnoberrot bei bestanden, 再 in Grau bei nicht bestanden.

```html
<div class="hanko" lang="ja" role="img" aria-label="Bestanden">合格</div>
```

```css
.hanko {
  display: inline-block; writing-mode: vertical-rl;
  font-family: "Shippori Mincho", serif; font-weight: 700;
  font-size: 2.25rem; letter-spacing: .15em; padding: .3em .15em;
  color: var(--shu); border: 3px solid currentColor; border-radius: .4rem;
  rotate: -6deg; filter: url(#pinsel);
  animation: stempeln .35s cubic-bezier(.2, .9, .3, 1.3) both;
}
@keyframes stempeln { from { scale: 1.6; rotate: -14deg; opacity: 0; } }
```

### 3. Tusche-Einblendung

Der Lösungshinweis erscheint nicht schlagartig, sondern wie Tusche, die ins Papier zieht:

```css
.tusche { animation: tusche .45s ease-out both; }
@keyframes tusche { from { opacity: 0; filter: blur(6px); } }
```

### 4. Der Garten blüht

In Niwa wechseln Themen ihre Wachstumsstufe: 種 Samen, 芽 Keim, 蕾 Knospe, 花 Blüte. Steigt ein Thema eine Stufe auf, pulsiert sein Knoten beim nächsten Öffnen des Gartens einmal sanft.

### 5. Trittsteine

Die Stationen in Michi sind keine perfekten Kreise, sondern leicht unregelmäßige Steine, wie Trittsteine in einem Garten:

```css
.stein               { border-radius: 48% 52% 45% 55% / 55% 45% 52% 48%; }
.stein:nth-child(3n+2) { border-radius: 55% 45% 50% 50% / 45% 55% 48% 52%; }
.stein:nth-child(3n)   { border-radius: 45% 55% 55% 45% / 50% 50% 45% 55%; }
```

### 6. お疲れ様 zum Abschluss

Ist das Tagesziel erreicht, zeigt Saku eine ruhige Abschlussseite: was heute sicher geworden ist, die Lernserie, und お疲れ様 (*otsukaresama*), der japanische Dank für getane Arbeit.

## Bewegung

| Was | Dauer | Kurve |
|---|---|---|
| Hover, Fokus | 150 ms | ease-out |
| Ein- und Ausblenden, Panels | 250 ms | ease-out rein, ease-in raus |
| Tusche-Einblendung | 450 ms | ease-out |
| Stempel | 350 ms | leicht federnd |
| Ensō | 1,4 s | ease-in-out |

- Bereichswechsel blenden den neuen Inhalt 150 ms ein, nur über die Deckkraft. Keine View-Transitions: In WebKit ruckeln dabei die Bilder.
- Bewegung nur mit Bedeutung: Sie zeigt, dass etwas erscheint, sich ändert oder geschafft ist.
- Bei `prefers-reduced-motion: reduce` sind alle Animationen aus:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
```

## Tastatur

| Taste | Wo | Aktion |
|---|---|---|
| `Strg K` / `⌘K` | überall | Suche öffnen |
| `S` | überall | Sensei öffnen oder schließen |
| `?` | überall | alle Tastenkürzel anzeigen |
| `Esc` | überall | schließen; in einem Eingabefeld: Feld verlassen |
| `Enter` | überall | der Knopf mit ↵: Los geht's, Prüfen, Übernehmen, Weiter, Nächste Aufgabe |
| `Leertaste` | Keiko, Grundwissen | Lösung zeigen, Definition aufdecken |
| `1` `2` `3` | Keiko, Grundwissen | Nicht gewusst, Teilweise, Gewusst; vor dem Prüfen wählen Ziffern die Antwort |
| `T` `E` `P` `V` | Keiko | Sensei: Tipp, Erklären, Prüfen, Variante |
| `M` | Keiko | markieren |
| `←` `→` | Keiko | zurück (Bewertung wird zurückgenommen), überspringen |
| `⌘↵` / `Strg ↵` | Keiko, SQL-Editor | SQL in der Sandbox ausführen |
| `U`, `1` – `4` | Grundwissen | Richtung umkehren; umgekehrt den Begriff wählen |
| `Leertaste` | Rechnen | Rechenweg zeigen |
| `0` – `3` | Verlauf | nach Ergebnis filtern |

Bedienelemente tragen ihre Taste als `data-taste`; `saku.js` klickt bei der passenden Taste das sichtbare Element. Die Hilfe (`?`) in `base.html` nennt alle Kürzel, ein Test gleicht sie mit den Templates ab. In Eingabefeldern sind die Einzeltasten abgeschaltet.

## Sprache und Ton

- Du-Form, kurze Sätze, ermutigend und ehrlich
- Japanische Wörter nur an festen Stellen: Bereichsnamen, Begrüßung, Abschluss, Stempel, Wachstumsstufen. Immer mit deutscher Übersetzung.
- Keine Ausrufezeichen-Flut, keine Übertreibungen
- Fehlermeldungen sagen, was passiert ist und was man tun kann

| Situation | Text |
|---|---|
| Begrüßung | おはよう · Guten Morgen (bis 11 Uhr), こんにちは · Hallo, こんばんは · Guten Abend |
| Noch keine Daten | Noch ist der Garten leer. Lege deine Prüfungen in `data/pdfs` und starte die Analyse. |
| Teilaufgabe wird sicher | Sicher. Das sitzt. |
| Tagesziel erreicht | Tagesziel geschafft. お疲れ様, gute Arbeit. |
| Start einer Simulation | 頑張って · Viel Erfolg. Die Zeit läuft, sobald du startest. |
| Bestanden | 合格 · Bestanden mit 74 Punkten, befriedigend. |
| Nicht bestanden | 再 · Noch nicht. Die meisten Punkte kosteten: Normalisierung, Subnetting. |
| Sensei nicht erreichbar | Sensei ist gerade nicht erreichbar. Der Lösungshinweis bleibt sichtbar, versuch es gleich noch einmal. |

## Barrierefreiheit

- Kontrast mindestens 4,5 : 1 für Text und 3 : 1 für Bedienelemente
- Status nie nur über Farbe: immer mit Symbol oder Text (○ ✕ ◐ ✓)
- Sichtbarer Fokusring: 2 px Zinnoberrot mit 2 px Abstand
- Alles per Tastatur erreichbar, in sinnvoller Reihenfolge
- Kanji mit `lang="ja"`; rein dekorative Kanji mit `aria-hidden="true"`, das deutsche Wort daneben trägt die Bedeutung
- Bildausschnitte mit Alternativtext: Termin, Kennung und Anfang des Aufgabentexts
- Animationen respektieren `prefers-reduced-motion`

## Icons

Lucide, dieselben Icons wie bei shadcn/ui: 18 px, Strichstärke 1,5, Farbe `currentColor`. Icons begleiten Text, sie ersetzen ihn nicht.
