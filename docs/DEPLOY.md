# Saku im Netz (Railway)

Saku läuft auch auf einem Server, damit du unterwegs am Handy lernen kannst: **nur für dich, nur hinter einem Passwort.**
Lokal ändert sich nichts. Alles hier greift nur, wenn die Umgebungsvariablen gesetzt sind und Saku mit
`python -m saku server` startet.

> **Urheberrecht:** Die IHK-Aufgaben sind geschützt. Saku im Netz ist nur für dich privat in Ordnung. Gib Adresse und
> Passwort nicht weiter, mach das Repo nicht öffentlich und stelle den Dienst nicht öffentlich ohne Anmeldung.
> Saku startet im Server-Modus deshalb gar nicht erst ohne `SAKU_PASSWORT`.

Die Railway-Fakten unten stammen aus dem Railway-Skill (Stand Oktober 2026). Was dort nicht steht, ist als
**unsicher** markiert: im Zweifel im Railway-Dashboard oder in der [Railway-Doku](https://docs.railway.com) nachsehen.

## Was im Netz läuft und was zu Hause bleibt

| Im Netz (Railway) | Zu Hause (dein Mac) |
|---|---|
| Die Web-App: Heute, Lernpfad, Üben, Rechnen, Prüfung, Themen, Analyse, Einstellungen | Die Pipeline: PDFs einlesen, `python -m saku analyse --ki claude-code` (über dein Claude-Code-Abo) |
| Sensei, wenn du `ANTHROPIC_API_KEY` setzt (kostet API-Guthaben) | Die PDFs (`data/quellen`, `data/pdfs`) und `.env`, die nie hochgeladen werden |
| Suche nach Stichworten (Volltext) | Suche nach Bedeutung über das Vektormodell |
| Datenbank und Bilder auf einem Volume unter `/data` | Das Original von Katalog und Lernstand in `data/` |

**Vektorsuche:** Das Image enthält fastembed nicht. Das Modell wären 240 MB auf dem Volume und mehrere hundert MB
Arbeitsspeicher dauerhaft, und Railway rechnet Arbeitsspeicher nach Verbrauch ab. Ohne Modell fällt die Suche (⌘K,
Sensei-Kontext) wie vorgesehen auf die Volltextsuche zurück. Alles, was nur die gespeicherten Vektoren braucht, bleibt:
„Kam so ähnlich dran“, Aufgabenmuster und die ähnlichen Falschantworten im Grundwissen kommen fertig berechnet aus dem Paket.
Der Saku-Prozess selbst braucht so etwa 250–300 MB (gemessen mit den Demo-Daten auf dem Mac).

## Was Saku dafür mitbringt

- **`Dockerfile`** im Repo-Wurzelordner: Python 3.12, Abhängigkeiten ohne pywebview und fastembed, lädt beim Bauen die
  Oberflächen-Dateien (`python -m saku assets`) und startet `python -m saku server`. `SAKU_DATENORDNER=/data` ist dort
  schon gesetzt. Eine `railway.toml` gibt es bewusst nicht: `railway.json`/`railway.toml` sind laut Skill veraltet,
  neue Services können sie nicht mehr nutzen, und ab 1.12.2026 liest Railway sie gar nicht mehr.
- **`.dockerignore`**: `.env`, `data/`, PDFs und Datenbanken kommen nie ins Image.
- **`python -m saku server`**: gunicorn mit einem Prozess (SQLite ist eine Datei) und 16 Threads (Sensei streamt per
  SSE, jeder offene Stream belegt einen Thread), auf `0.0.0.0` und dem Port aus `PORT` (setzt Railway), sonst
  `SAKU_PORT`, sonst 5050. Hinter dem Proxy liest Saku Schema, Host und Absender-IP aus den `X-Forwarded-*`-Kopfzeilen
  (ProxyFix), damit CSRF-Schutz, sichere Cookies und die Sperre nach Fehlversuchen stimmen. Saku startet nicht, wenn
  `SAKU_PASSWORT` fehlt oder auf Railway kein Volume unter dem Datenordner hängt (der Lernstand wäre sonst beim nächsten
  Deploy weg). Die tägliche Sicherung nach `/data/backups` läuft auch, wenn der Server wochenlang durchläuft.
- **`python -m saku paket`**: baut zu Hause das Archiv für das Volume (siehe Schritt 6).
- **Einstellungen → Daten** (nur im Netz): „Paket übernehmen“, „Datenbank herunterladen“ und „Abmelden“.

## Umgebungsvariablen

| Variable | Pflicht | Bedeutung |
|---|---|---|
| `SAKU_PASSWORT` | ja | Passwort für die Anmeldung. Lang und zufällig, z. B. aus dem Passwort-Manager. Ein neues Passwort meldet alle Geräte ab. |
| `SAKU_GEHEIM` | empfohlen | Signiert das Sitzungs-Cookie. Fehlt es, würfelt Saku bei jedem Start ein neues: nach jedem Deploy oder Neustart musst du dich dann neu anmelden. Erzeugen: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SAKU_DATENORDNER` | nein | Steht im Dockerfile schon auf `/data`; nur ändern, wenn das Volume woanders hängt. |
| `ANTHROPIC_API_KEY` | nein | Schaltet Sensei ein. Jede Frage kostet API-Guthaben, siehe Sicherheit. |
| `SAKU_DOMAINS` | nein | Eigene Domain(s), durch Komma getrennt, z. B. `lernen.example.org`. Die Railway-Domain kommt automatisch aus `RAILWAY_PUBLIC_DOMAIN`. |

Saku beantwortet nur Anfragen an `localhost`, `127.0.0.1`, `RAILWAY_PUBLIC_DOMAIN` und `SAKU_DOMAINS`, alles andere
mit 400 (Schutz vor DNS-Rebinding). Railway setzt `RAILWAY_PUBLIC_DOMAIN`, sobald der Service eine öffentliche Domain
hat.

## Schritt für Schritt

1. **Repo privat auf GitHub** (falls noch nicht): Das Repo enthält keine Prüfungsdaten (`data/` steht in `.gitignore`),
   trotzdem privat lassen.

2. **Projekt und Service anlegen.** Im Railway-Dashboard ein neues Projekt aus dem GitHub-Repo erstellen
   („Deploy from GitHub repo“). Railway baut dann bei jedem Push. Railway erkennt das `Dockerfile` im Wurzelordner
   nach meinem Wissen von selbst (**unsicher**, im Skill nicht belegt). Steht im Build-Log „Railpack“, den Builder
   umstellen:
   ```bash
   railway environment edit --service-config <service> build.builder DOCKERFILE
   ```
   Ohne GitHub geht es auch mit der CLI, aber **nur aus einem frischen Klon**, damit `.env` und `data/` gar nicht erst
   hochgeladen werden (ob `railway up` die `.gitignore` beachtet, steht nicht im Skill):
   ```bash
   git clone <dein-repo> /tmp/saku-deploy && cd /tmp/saku-deploy
   railway up --detach -m "Saku"       # legt Projekt und Service an, wenn noch keins verknüpft ist
   railway deployment list --json      # warten, bis der neue Deploy SUCCESS meldet
   ```

3. **Volume unter `/data` anhängen.** Im Dashboard am Service ein Volume anlegen, Mount-Pfad **`/data`**
   (die genaue Stelle im Dashboard ist **unsicher**). Laut Skill wächst ein Volume nicht von selbst; auf Hobby und Pro
   lässt es sich ohne Ausfall vergrößern, bezahlt wird der belegte Platz. Plane gut das Dreifache des Pakets ein: beim
   Übernehmen liegen kurz Paket, entpackte Kopie, alte Bilder und Sicherung nebeneinander.

4. **Variablen setzen** (Dashboard → Variables oder CLI), danach neu deployen:
   ```bash
   railway variable set SAKU_PASSWORT='…' --service <service>
   railway variable set SAKU_GEHEIM='…' --service <service>
   railway variable set ANTHROPIC_API_KEY='…' --service <service>   # optional, für Sensei
   ```

5. **Öffentliche Domain erzeugen** (Dashboard → Settings → Networking, „Generate Domain“; Ort im Dashboard **unsicher**).
   Den Port musst du nicht angeben: Saku lauscht auf `PORT`, das Railway vorgibt. Ob es läuft:
   ```bash
   railway logs --service <service> --lines 100 --json   # „Listening at: http://0.0.0.0:…“
   ```
   Eine Healthcheck-Adresse nicht einrichten: ohne Anmeldung bekäme sie nur die Weiterleitung zur Anmeldung, und ob
   Railway sie unter der öffentlichen Domain aufruft, ist **unsicher** (sonst antwortet Saku mit 400).

6. **Paket bauen** (zu Hause, im Saku-Ordner):
   ```bash
   python -m saku paket            # schreibt data/saku-paket.tar.gz und sagt die Größe
   ```
   Drin ist genau, was die Web-App braucht: `saku.db` als stimmige Kopie (SQLite-Backup-API, auch während die App läuft),
   die Bildausschnitte unter `data/aufgaben`, auf die die Datenbank verweist (aus den Bildlisten und aus dem Markdown der
   Aufgaben), und die Projektdokumentation für das Fachgespräch (`data/projekt/text.md`). Nicht drin: `quellen/`,
   `pdfs/`, alle PDFs, `backups/`, `modelle/`, `bilder/` (nur Originale der Kopfbilder) und `.env`.

7. **Anmelden und Paket hochladen.** Die Railway-Adresse öffnen, mit `SAKU_PASSWORT` anmelden, dann
   **Einstellungen → Daten → Paket übernehmen**, die Datei wählen, „Hochladen“. Saku schreibt das Paket in Blöcken direkt
   auf das Volume (bis 2 GB), prüft jeden Eintrag (nur `saku.db`, `aufgaben/…png|jpg|webp` und die Projektdatei; keine
   Links, kein `../`), sichert die alte Datenbank nach `/data/backups/saku-vor-paket-…db` (mit Uhrzeit, die letzten drei
   bleiben), spielt die neue ein und bringt sie auf das
   aktuelle Schema. Ob Railways Proxy so große Uploads und so lange Anfragen zulässt, steht nicht im Skill
   (**unsicher**); bei einem Abbruch einfach noch einmal, es bleibt nichts Halbes liegen.

8. **Aufs Handy:** Seite im Browser öffnen, anmelden (30 Tage gültig), „Zum Home-Bildschirm“.

## Später: neue Prüfungen und Updates

- **Neuer Code:** `git push`, Railway baut neu. Die Daten auf dem Volume bleiben. Mit `SAKU_GEHEIM` bleibst du angemeldet.
- **Neue Prüfungen:** zu Hause `python -m saku analyse --ki claude-code`, dann `python -m saku paket` und wieder
  hochladen. **Der Lernstand im Netz geht dabei nicht verloren:** Saku nimmt ihn vor dem Einspielen mit und führt ihn mit
  dem aus dem Paket zusammen (wie `lernstand import`: Doppeltes wird übersprungen, bei Karten gilt der neuere Stand).
  Die Einstellungen (Prüfungstermin, Farbschema …) kommen aus dem Paket, ebenso Sensei-Gespräche und KI-Protokoll: die
  von hier und Lernstand zu Teilaufgaben, die das Paket nicht mehr kennt, stehen danach nur noch in der Sicherung von
  vor dem Paket. Ist das Paket aus einer neueren Saku-Version als
  der Server, lehnt Saku es ab: erst neu deployen.

## Lernstand zwischen zu Hause und dem Netz

- **Von zu Hause ins Netz:** steckt im Paket (Schritt 6 und 7).
- **Vom Netz nach Hause** (zum Weiterlernen am Mac oder vor einem neuen Paket): im Netz **Einstellungen → Daten →
  Lernstand exportieren**, zu Hause
  ```bash
  python -m saku lernstand import saku-lernstand-JJJJ-MM-TT.json
  ```
  Das führt zusammen, mehrfaches Importieren ändert nichts.
- **Komplette Sicherung:** im Netz **Einstellungen → Daten → Datenbank herunterladen** (`saku-JJJJ-MM-TT.db`, Katalog und
  Lernstand). Zum Zurückholen zu Hause: App schließen, die Datei als `data/saku.db` an ihren Platz legen. Lade sie
  ab und zu herunter: die Sicherungen in `/data/backups` liegen auf demselben Volume wie die Datenbank.

Wer abwechselnd an beiden Orten lernt: vor dem Wechsel exportieren und am anderen Ort importieren.

## Kosten

Der Railway-Skill nennt keine Preise, nur, wie man die echten Kosten abfragt. Grob nach meinem Wissen (**unsicher**,
auf railway.com/pricing prüfen): Der Hobby-Plan kostet etwa 5 US-$ im Monat, darin ist Verbrauch in gleicher Höhe
enthalten; abgerechnet werden Arbeitsspeicher, CPU, Volume-Platz und ausgehender Verkehr nach Verbrauch. Ein Prozess mit
rund 300 MB, der fast nur wartet, und ein Volume unter 1 GB sollten in diesem Rahmen bleiben. Prüfen und begrenzen:
```bash
railway usage --workspace <workspace> --json                           # bisheriger Verbrauch, Schätzung zum Monatsende
railway usage limit set --workspace <workspace> --target workspace --soft 5 --hard 10 --json
```
Ein hartes Limit hält den Dienst an, wenn es erreicht ist (ganze Dollar). Sensei kostet zusätzlich API-Guthaben bei
Anthropic, unabhängig von Railway.

## Sicherheit

- **Passwort:** lang und zufällig (20+ Zeichen aus dem Passwort-Manager). Saku vergleicht in konstanter Zeit, wartet nach
  jedem Fehlversuch eine Sekunde und sperrt eine IP nach 5 Fehlversuchen für 15 Minuten (im Speicher, ein Neustart
  vergisst die Sperre). Gebremst wird je IP aus `X-Forwarded-For` (der letzte Eintrag, den Railways Proxy anhängt);
  hängt Railway mehr als einen Proxy dazwischen, teilen sich alle eine IP: dann sperrt ein Angreifer auch dich für
  15 Minuten aus, kommt aber nicht schneller voran (**unsicher**, wie viele Proxy-Stufen Railway hat).
- **Sitzung:** signiertes Cookie (`Secure`, `HttpOnly`, `SameSite=Lax`), 30 Tage gültig. Abmelden in den Einstellungen;
  ein neues `SAKU_PASSWORT` oder `SAKU_GEHEIM` meldet alle Geräte ab (z. B. bei verlorenem Handy).
- **Alles hinter der Anmeldung:** jede Seite, die Bilder unter `/bild/…`, die Sensei-Streams und alle Downloads. Frei sind
  nur die Anmeldeseite und die Oberflächen-Dateien unter `/static` (CSS, Schriften, Icons; nichts aus den Prüfungen).
- **CSRF-Schutz** gilt weiter: schreibende Anfragen nur von derselben Herkunft.
- **API-Kosten:** Mit `ANTHROPIC_API_KEY` kann jeder mit deinem Passwort Sensei befragen. Setze bei Anthropic ein
  Ausgabenlimit für den Schlüssel, oder lass ihn im Netz weg.
- **Repo:** privat lassen; `.env` und `data/` sind in `.gitignore` und `.dockerignore`, `saku-paket*.tar.gz` ebenfalls.
- **Daten:** Die Datenbank liegt unverschlüsselt auf dem Railway-Volume.
