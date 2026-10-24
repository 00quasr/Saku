-- =====================================================================
-- Saku 咲く – Datenbankschema
-- SQLite 3.38 oder neuer, mit FTS5 (in Python enthalten)
-- =====================================================================
--
-- Konventionen
--   * Zeitpunkte in UTC im SQLite-Format 'YYYY-MM-DD HH:MM:SS'
--   * Listen (z. B. Bildpfade) als JSON-Arrays in TEXT-Spalten
--   * Bildpfade relativ zum Datenordner, z. B. 'aufgaben/3f2a…/2b-1.png'
--   * Gewichte in teilaufgabe_thema ergeben je Teilaufgabe zusammen 1
--   * Die Pipeline aktualisiert per Upsert (Termin, Bereich, Nummer, Kennung),
--     damit IDs und Lernstand bei einem erneuten Lauf erhalten bleiben
--   * Pro Verbindung setzen: PRAGMA foreign_keys = ON; PRAGMA journal_mode = WAL;
--   * Schema-Version in PRAGMA user_version, Migrationen erhöhen sie

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Katalog: Prüfungen, Dokumente, Aufgaben
-- ---------------------------------------------------------------------

-- Ein Prüfungstermin in einem Prüfungsbereich, z. B. Winter 2024/25, Bereich X
CREATE TABLE pruefung (
    id                       INTEGER PRIMARY KEY,
    jahr                     INTEGER NOT NULL,          -- Kalenderjahr des Termins (Winter 2024/25 → 2024)
    saison                   TEXT    NOT NULL CHECK (saison IN ('Sommer', 'Winter', 'Frühjahr', 'Herbst')),  -- AP1: Frühjahr/Herbst
    teil                     TEXT    NOT NULL DEFAULT 'AP2' CHECK (teil IN ('AP1', 'AP2', 'AP')),  -- AP = Prüfung nach AO 1997
    bereich                  TEXT    NOT NULL,          -- Prüfungsbereich laut Deckblatt
    beruf                    TEXT    NOT NULL DEFAULT 'IT',  -- 1201 AE, 1202 SI, IT = für alle IT-Berufe (AP1, WiSo, GA2)
    format                   TEXT    CHECK (format IN ('aktuell', 'frueher')),
    gewicht                  REAL    NOT NULL DEFAULT 1.0 CHECK (gewicht >= 0),  -- z. B. 0.5 für früheres Format
    dauer_min                INTEGER,                   -- Bearbeitungszeit laut Deckblatt
    punkte_gesamt            INTEGER,
    ausgangssituation        TEXT,
    ausgangssituation_bilder TEXT    NOT NULL DEFAULT '[]',
    ausgangssituation_inhalt TEXT,                      -- von Claude neu aufgebaut, Markdown
    UNIQUE (jahr, saison, teil, bereich, beruf)
);

-- Jede eingelesene PDF-Datei
CREATE TABLE dokument (
    id             INTEGER PRIMARY KEY,
    dateiname      TEXT    NOT NULL,
    sha256         TEXT    NOT NULL UNIQUE,             -- erkennt Dubletten und unveränderte Dateien
    seiten         INTEGER NOT NULL,
    art            TEXT    NOT NULL DEFAULT 'unbekannt'
                   CHECK (art IN ('aufgaben', 'loesungen', 'sonstiges', 'unbekannt')),
    hat_textebene  INTEGER NOT NULL DEFAULT 1 CHECK (hat_textebene IN (0, 1)),  -- 0 = Scan, OCR nötig
    pruefung_id    INTEGER REFERENCES pruefung(id) ON DELETE SET NULL,
    importiert_am  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Eine Aufgabe (früher: Handlungsschritt) mit ihrer Situationsbeschreibung
CREATE TABLE aufgabe (
    id                INTEGER PRIMARY KEY,
    pruefung_id       INTEGER NOT NULL REFERENCES pruefung(id) ON DELETE CASCADE,
    nummer            INTEGER NOT NULL,
    titel             TEXT,
    einleitung        TEXT,
    einleitung_bilder TEXT    NOT NULL DEFAULT '[]',
    einleitung_inhalt TEXT,                             -- von Claude neu aufgebaut, Markdown
    punkte            REAL,
    seite_von         INTEGER,
    seite_bis         INTEGER,
    UNIQUE (pruefung_id, nummer)
);

-- Die Lerneinheit: eine Teilaufgabe wie 3 b
CREATE TABLE teilaufgabe (
    id              INTEGER PRIMARY KEY,
    aufgabe_id      INTEGER NOT NULL REFERENCES aufgabe(id) ON DELETE CASCADE,
    kennung         TEXT    NOT NULL,                   -- 'a', 'b', 'ba' …
    position        INTEGER NOT NULL,
    text            TEXT    NOT NULL DEFAULT '',        -- für Suche und KI
    punkte          REAL,
    seite           INTEGER,
    bilder          TEXT    NOT NULL DEFAULT '[]',      -- Ausschnitte aus dem PDF
    typ             TEXT    CHECK (typ IN ('erklaeren', 'berechnen', 'zeichnen', 'code',
                                           'sql', 'tabelle', 'auswahl', 'sonstiges')),
    loesung_text    TEXT,
    loesung_bilder  TEXT    NOT NULL DEFAULT '[]',
    -- von Claude aus den Ausschnitten neu aufgebaut (Schritt aufbereiten); fehlt es, zeigt Saku die Ausschnitte
    inhalt          TEXT,                               -- Markdown, Abbildungen als ![…](/bild/…)
    antwort         TEXT,                               -- JSON {art, optionen, richtig, einheit, vorlage}
    loesung_inhalt  TEXT,                               -- Markdown
    muster_id       INTEGER REFERENCES muster(id) ON DELETE SET NULL,
    loesung_sql     TEXT,                               -- Musterlösung in SQLite (Schritt sandbox), nur bei SQL-Teilaufgaben
    UNIQUE (aufgabe_id, kennung)
);

-- SQL-Sandbox je Aufgabe (Schritt sandbox): erfundene Tabellen und Beispieldaten zum Ausführen und Prüfen in Üben
CREATE TABLE sql_sandbox (
    aufgabe_id  INTEGER PRIMARY KEY REFERENCES aufgabe(id) ON DELETE CASCADE,
    ddl         TEXT NOT NULL,                          -- CREATE TABLE …
    daten       TEXT NOT NULL,                          -- INSERT …
    erstellt    TEXT DEFAULT (datetime('now'))
);

-- „Kam so ähnlich auch dran“: TF-IDF-Ähnlichkeit zwischen Teilaufgaben
CREATE TABLE aehnlichkeit (
    teilaufgabe_id  INTEGER NOT NULL REFERENCES teilaufgabe(id) ON DELETE CASCADE,
    aehnlich_id     INTEGER NOT NULL REFERENCES teilaufgabe(id) ON DELETE CASCADE,
    wert            REAL    NOT NULL CHECK (wert BETWEEN 0 AND 1),
    PRIMARY KEY (teilaufgabe_id, aehnlich_id),
    CHECK (teilaufgabe_id <> aehnlich_id)
);

-- ---------------------------------------------------------------------
-- Themen
-- ---------------------------------------------------------------------

-- Hierarchie aus data/themen.md: 1 Prüfungsbereich · 2 Thema · 3 Unterthema
CREATE TABLE thema (
    id            INTEGER PRIMARY KEY,
    eltern_id     INTEGER REFERENCES thema(id) ON DELETE CASCADE,
    ebene         INTEGER NOT NULL CHECK (ebene BETWEEN 1 AND 3),
    name          TEXT    NOT NULL,
    slug          TEXT    NOT NULL UNIQUE,
    stichworte    TEXT,                                 -- helfen bei der Klassifikation
    position      INTEGER NOT NULL DEFAULT 0,
    beschreibung  TEXT
);

CREATE TABLE teilaufgabe_thema (
    teilaufgabe_id  INTEGER NOT NULL REFERENCES teilaufgabe(id) ON DELETE CASCADE,
    thema_id        INTEGER NOT NULL REFERENCES thema(id) ON DELETE CASCADE,
    gewicht         REAL    NOT NULL DEFAULT 1.0 CHECK (gewicht > 0 AND gewicht <= 1),
    quelle          TEXT    NOT NULL DEFAULT 'ki' CHECK (quelle IN ('ki', 'regel', 'manuell')),
    sicherheit      REAL    CHECK (sicherheit BETWEEN 0 AND 1),
    PRIMARY KEY (teilaufgabe_id, thema_id)
);

-- Voraussetzungen für den Lernpfad: thema_id baut auf voraussetzung_id auf
CREATE TABLE thema_voraussetzung (
    thema_id          INTEGER NOT NULL REFERENCES thema(id) ON DELETE CASCADE,
    voraussetzung_id  INTEGER NOT NULL REFERENCES thema(id) ON DELETE CASCADE,
    quelle            TEXT    NOT NULL DEFAULT 'ki' CHECK (quelle IN ('ki', 'manuell')),
    begruendung       TEXT,
    PRIMARY KEY (thema_id, voraussetzung_id),
    CHECK (thema_id <> voraussetzung_id)
);

-- Lernfelder aus dem Rahmenlehrplan (KMK 2019): 1–9 für alle, 10a–12a AE, 10b–12b SI
CREATE TABLE lernfeld (
    id            INTEGER PRIMARY KEY,
    nummer        TEXT    NOT NULL UNIQUE,              -- '1' … '9', '10a', '12b'
    titel         TEXT    NOT NULL,
    jahr          INTEGER NOT NULL,                     -- Ausbildungsjahr
    stunden       INTEGER,
    beruf         TEXT    NOT NULL DEFAULT 'IT',        -- IT, 1201, 1202
    beschreibung  TEXT
);

CREATE TABLE thema_lernfeld (
    thema_id     INTEGER NOT NULL REFERENCES thema(id) ON DELETE CASCADE,
    lernfeld_id  INTEGER NOT NULL REFERENCES lernfeld(id) ON DELETE CASCADE,
    PRIMARY KEY (thema_id, lernfeld_id)
);

-- Fachbegriffe als Index (Begriff ↔ Teilaufgaben): jeder Begriff ist eine Notiz mit Fundstellen
CREATE TABLE begriff (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    slug        TEXT    NOT NULL UNIQUE,
    erklaerung  TEXT                                    -- von Sensei auf Wunsch, Markdown
);

CREATE TABLE teilaufgabe_begriff (
    teilaufgabe_id  INTEGER NOT NULL REFERENCES teilaufgabe(id) ON DELETE CASCADE,
    begriff_id      INTEGER NOT NULL REFERENCES begriff(id) ON DELETE CASCADE,
    PRIMARY KEY (teilaufgabe_id, begriff_id)
);
CREATE INDEX idx_teilaufgabe_begriff ON teilaufgabe_begriff(begriff_id);

-- Vektoren (lokal, fastembed): art = teilaufgabe, begriff oder thema; daten = float32, normiert
CREATE TABLE vektor (
    art    TEXT    NOT NULL,
    id     INTEGER NOT NULL,
    daten  BLOB    NOT NULL,
    PRIMARY KEY (art, id)
);

-- Aufgabenmuster: gleichartige Teilaufgaben über alle Termine (Cluster der Vektoren)
CREATE TABLE muster (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL
);

-- Lücken aus den Bewertungen von Sensei („fehlt“), mit Operator der Aufgabe
CREATE TABLE luecke (
    id              INTEGER PRIMARY KEY,
    teilaufgabe_id  INTEGER NOT NULL REFERENCES teilaufgabe(id) ON DELETE CASCADE,
    text            TEXT    NOT NULL,
    operator        TEXT,
    zeitpunkt       TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Begriffs-Karten (Grundwissen): Lernstand je Fachbegriff wie bei den Teilaufgaben
CREATE TABLE begriff_karte (
    begriff_id   INTEGER PRIMARY KEY REFERENCES begriff(id) ON DELETE CASCADE,
    status       TEXT    NOT NULL DEFAULT 'neu' CHECK (status IN ('neu', 'rot', 'gelb', 'gruen')),
    serie        INTEGER NOT NULL DEFAULT 0,
    fsrs         TEXT,
    faellig_am   TEXT,
    geaendert_am TEXT
);

-- ---------------------------------------------------------------------
-- Lernpfad (Michi 道)
-- ---------------------------------------------------------------------

-- Je Lernpfad eigene Stationen: AP1 (alle IT-Berufe), AP2-1201 (AE), AP2-1202 (SI)
CREATE TABLE station (
    id           INTEGER PRIMARY KEY,
    pfad         TEXT    NOT NULL DEFAULT 'AP2-1201',
    position     INTEGER NOT NULL,
    titel        TEXT    NOT NULL,
    einfuehrung  TEXT,                                  -- von Sensei, Markdown
    quelle       TEXT    NOT NULL DEFAULT 'ki' CHECK (quelle IN ('ki', 'manuell')),
    UNIQUE (pfad, position)
);

CREATE TABLE station_thema (
    station_id  INTEGER NOT NULL REFERENCES station(id) ON DELETE CASCADE,
    thema_id    INTEGER NOT NULL REFERENCES thema(id) ON DELETE CASCADE,
    PRIMARY KEY (station_id, thema_id)
);

CREATE TABLE stationstest (
    id               INTEGER PRIMARY KEY,
    station_id       INTEGER NOT NULL REFERENCES station(id) ON DELETE CASCADE,
    gestartet_am     TEXT    NOT NULL DEFAULT (datetime('now')),
    beendet_am       TEXT,
    punkte_erreicht  REAL,
    punkte_moeglich  REAL,
    bestanden        INTEGER CHECK (bestanden IN (0, 1))
);

-- ---------------------------------------------------------------------
-- Lernstand (Keiko 稽古)
-- ---------------------------------------------------------------------

-- Fahrschul-Status und FSRS-Zustand je Teilaufgabe
CREATE TABLE karte (
    teilaufgabe_id  INTEGER PRIMARY KEY REFERENCES teilaufgabe(id) ON DELETE CASCADE,
    status          TEXT    NOT NULL DEFAULT 'neu' CHECK (status IN ('neu', 'rot', 'gelb', 'gruen')),
    serie           INTEGER NOT NULL DEFAULT 0 CHECK (serie >= 0),   -- „Gewusst“ in Folge
    fsrs            TEXT,                                            -- FSRS-Karte als JSON
    faellig_am      TEXT,
    markiert        INTEGER NOT NULL DEFAULT 0 CHECK (markiert IN (0, 1)),
    notiz           TEXT,
    geaendert_am    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Jede einzelne Bewertung, die Grundlage für Statistik und Lernserie
CREATE TABLE bewertung (
    id              INTEGER PRIMARY KEY,
    teilaufgabe_id  INTEGER NOT NULL REFERENCES teilaufgabe(id) ON DELETE CASCADE,
    zeitpunkt       TEXT    NOT NULL DEFAULT (datetime('now')),
    ergebnis        INTEGER NOT NULL CHECK (ergebnis IN (1, 2, 3)),  -- 1 nicht gewusst · 2 teilweise · 3 gewusst
    quelle          TEXT    NOT NULL DEFAULT 'selbst'
                    CHECK (quelle IN ('selbst', 'sensei', 'simulation', 'stationstest')),
    dauer_s         INTEGER,
    antwort         TEXT,
    punkte          REAL                                -- erreichte Punkte, wenn bekannt (Sensei, Auswahl, Selbsteinschätzung)
);

-- Rechentrainer (算 Rechnen): jede generierte Aufgabe, die geprüft wurde; „Rechenweg zeigen“ zählt als falsch
CREATE TABLE rechenuebung (
    id              INTEGER PRIMARY KEY,
    art             TEXT    NOT NULL,                   -- subnetz, datenmenge … (saku/lernen/rechnen)
    seed            INTEGER NOT NULL,                   -- erzeugt dieselbe Aufgabe wieder
    richtig         INTEGER NOT NULL CHECK (richtig IN (0, 1)),
    felder_richtig  INTEGER NOT NULL,
    felder_gesamt   INTEGER NOT NULL,
    dauer_s         INTEGER,
    zeitpunkt       TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------
-- Prüfungssimulation (Shiken 試験)
-- ---------------------------------------------------------------------

CREATE TABLE simulation (
    id               INTEGER PRIMARY KEY,
    bereich          TEXT    NOT NULL,
    gestartet_am     TEXT    NOT NULL DEFAULT (datetime('now')),
    beendet_am       TEXT,
    dauer_min        INTEGER NOT NULL,
    punkte_erreicht  REAL,
    punkte_moeglich  REAL,
    note             INTEGER CHECK (note BETWEEN 1 AND 6),
    bestanden        INTEGER CHECK (bestanden IN (0, 1))
);

CREATE TABLE simulation_teilaufgabe (
    simulation_id    INTEGER NOT NULL REFERENCES simulation(id) ON DELETE CASCADE,
    teilaufgabe_id   INTEGER NOT NULL REFERENCES teilaufgabe(id) ON DELETE CASCADE,
    position         INTEGER NOT NULL,
    antwort          TEXT,
    punkte_erreicht  REAL,
    quelle           TEXT    CHECK (quelle IN ('selbst', 'sensei')),
    PRIMARY KEY (simulation_id, teilaufgabe_id)
);

-- ---------------------------------------------------------------------
-- Sensei 先生 und KI
-- ---------------------------------------------------------------------

CREATE TABLE sensei_nachricht (
    id              INTEGER PRIMARY KEY,
    gespraech       TEXT    NOT NULL,                   -- UUID eines Gesprächs
    rolle           TEXT    NOT NULL CHECK (rolle IN ('user', 'assistant')),
    modus           TEXT    CHECK (modus IN ('tipp', 'erklaeren', 'pruefen', 'variante', 'thema', 'chat')),
    inhalt          TEXT    NOT NULL,
    teilaufgabe_id  INTEGER REFERENCES teilaufgabe(id) ON DELETE SET NULL,
    thema_id        INTEGER REFERENCES thema(id) ON DELETE SET NULL,
    zeitpunkt       TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Protokoll aller API-Aufrufe (Bunseki zeigt die Summen)
CREATE TABLE ki_aufruf (
    id          INTEGER PRIMARY KEY,
    zweck       TEXT    NOT NULL,                       -- deckblatt, klassifikation, lernpfad, tutor, suche …
    modell      TEXT    NOT NULL,
    tokens_ein  INTEGER NOT NULL DEFAULT 0,
    tokens_aus  INTEGER NOT NULL DEFAULT 0,
    aus_cache   INTEGER NOT NULL DEFAULT 0 CHECK (aus_cache IN (0, 1)),
    zeitpunkt   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Gleiche Anfrage, gleiche Antwort: spart Kosten bei erneuten Pipeline-Läufen
CREATE TABLE ki_cache (
    schluessel   TEXT PRIMARY KEY,                      -- SHA-256 über Modell, Systemprompt und Nachrichten
    modell       TEXT NOT NULL,
    antwort      TEXT NOT NULL,                         -- Antwort als JSON
    erstellt_am  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------
-- Einstellungen
-- ---------------------------------------------------------------------

CREATE TABLE einstellung (
    schluessel  TEXT PRIMARY KEY,
    wert        TEXT NOT NULL
);

INSERT INTO einstellung (schluessel, wert) VALUES
    ('pruefungstermin',        ''),        -- ISO-Datum, z. B. 2027-04-28
    ('puffer_tage',            '7'),       -- Tage vor der Prüfung nur für Simulationen
    ('stationstest_schwelle',  '0.8'),     -- Anteil der Punkte zum Bestehen einer Station
    ('pruefungstermin_ap1',    ''),        -- ISO-Datum der AP1
    ('farbschema',             'dunkel'),  -- system, hell, dunkel
    ('beruf',                  '1201'),    -- Berufsnummer laut Deckblatt: 1201 = AE, 1202 = SI
    ('teil',                   'AP2');     -- AP1 oder AP2: was Saku gerade zeigt

-- ---------------------------------------------------------------------
-- Volltextsuche (⌘K und Sensei-Chat)
-- Trigramm-Tokenizer: findet auch Wortteile, „netz“ findet „Firmennetzwerk“
-- Wird am Ende jedes Pipeline-Laufs neu aufgebaut.
-- ---------------------------------------------------------------------

CREATE VIRTUAL TABLE suche USING fts5(
    teilaufgabe_id UNINDEXED,
    titel,
    text,
    loesung,
    tokenize = 'trigram'
);

-- ---------------------------------------------------------------------
-- Indizes
-- ---------------------------------------------------------------------

CREATE INDEX idx_dokument_pruefung     ON dokument(pruefung_id);
CREATE INDEX idx_aufgabe_pruefung      ON aufgabe(pruefung_id);
CREATE INDEX idx_teilaufgabe_aufgabe   ON teilaufgabe(aufgabe_id);
CREATE INDEX idx_teilaufgabe_thema     ON teilaufgabe_thema(thema_id);
CREATE INDEX idx_thema_eltern          ON thema(eltern_id);
CREATE INDEX idx_karte_faellig         ON karte(faellig_am);
CREATE INDEX idx_bewertung_teilaufgabe ON bewertung(teilaufgabe_id, zeitpunkt);
CREATE INDEX idx_sensei_gespraech      ON sensei_nachricht(gespraech, zeitpunkt);
CREATE INDEX idx_aehnlichkeit_wert     ON aehnlichkeit(teilaufgabe_id, wert DESC);
CREATE INDEX idx_rechenuebung_art      ON rechenuebung(art, id);

-- ---------------------------------------------------------------------
-- Sichten
-- ---------------------------------------------------------------------

-- Was gerade gelernt wird: Beruf und Prüfungsteil aus den Einstellungen, dazu der Lernpfad
CREATE VIEW v_umfang AS
SELECT beruf, teil, CASE teil WHEN 'AP1' THEN 'AP1' ELSE 'AP2-' || beruf END AS pfad
FROM (SELECT COALESCE((SELECT wert FROM einstellung WHERE schluessel = 'beruf'), '1201') AS beruf,
             COALESCE((SELECT wert FROM einstellung WHERE schluessel = 'teil'), 'AP2')   AS teil);

-- Jede Teilaufgabe mit Termin und Lernstand; termin_index ist sortierbar.
-- v_teilaufgabe_alle für die Pipeline, v_teilaufgabe nur im Umfang (alle Bereiche der App lesen diese Sicht)
CREATE VIEW v_teilaufgabe_alle AS
SELECT
    t.id                                 AS teilaufgabe_id,
    t.kennung,
    t.punkte,
    COALESCE(t.punkte, 0) * p.gewicht    AS punkte_gewichtet,
    a.id                                 AS aufgabe_id,
    a.nummer                             AS aufgabe_nr,
    p.id                                 AS pruefung_id,
    p.jahr,
    p.saison,
    p.bereich,
    p.jahr * 2 + (p.saison IN ('Winter', 'Herbst')) AS termin_index,
    CASE p.saison
        WHEN 'Winter' THEN 'Winter ' || p.jahr || '/' || substr(CAST(p.jahr + 1 AS TEXT), 3, 2)
        ELSE p.saison || ' ' || p.jahr
    END                                  AS termin,
    COALESCE(k.status, 'neu')            AS status,
    p.teil,
    p.beruf
FROM teilaufgabe t
JOIN aufgabe  a ON a.id = t.aufgabe_id
JOIN pruefung p ON p.id = a.pruefung_id
LEFT JOIN karte k ON k.teilaufgabe_id = t.id;

-- AP1 gilt für alle IT-Berufe; in der AP2 gelten WiSo und GA2 (beruf IT) für alle, der Rest nur für den eigenen Beruf
CREATE VIEW v_teilaufgabe AS
SELECT v.*
FROM v_teilaufgabe_alle v
JOIN v_umfang u ON (v.teil = 'AP1') = (u.teil = 'AP1') AND v.beruf IN ('IT', u.beruf);

-- Stationen des aktiven Lernpfads
CREATE VIEW v_station AS
SELECT s.* FROM station s JOIN v_umfang u ON u.pfad = s.pfad;

-- Jedes Thema mit sich selbst und allen übergeordneten Themen
CREATE VIEW v_thema_vorfahr AS
WITH RECURSIVE kette(thema_id, vorfahr_id) AS (
    SELECT id, id FROM thema
    UNION ALL
    SELECT k.thema_id, t.eltern_id
    FROM kette k
    JOIN thema t ON t.id = k.vorfahr_id
    WHERE t.eltern_id IS NOT NULL
)
SELECT thema_id, vorfahr_id FROM kette;

-- Zuordnungen, nach oben durchgereicht: ein Prüfungsbereich erbt die Teilaufgaben seiner Themen
CREATE VIEW v_zuordnung AS
SELECT
    v.vorfahr_id       AS thema_id,
    tt.teilaufgabe_id,
    SUM(tt.gewicht)    AS gewicht
FROM teilaufgabe_thema tt
JOIN v_thema_vorfahr v ON v.thema_id = tt.thema_id
GROUP BY v.vorfahr_id, tt.teilaufgabe_id;

-- Bunseki: Häufigkeit, Punkte und Anteil je Thema
CREATE VIEW v_themen_statistik AS
WITH gesamt AS (
    SELECT SUM(punkte_gewichtet) AS punkte, COUNT(DISTINCT termin_index) AS termine
    FROM v_teilaufgabe
)
SELECT
    th.id                                                         AS thema_id,
    th.name,
    th.ebene,
    th.eltern_id,
    COUNT(i.teilaufgabe_id)                                       AS teilaufgaben,  -- nur im Umfang
    COUNT(DISTINCT i.termin_index)                                AS termine,
    ROUND(100.0 * COUNT(DISTINCT i.termin_index)
          / NULLIF((SELECT termine FROM gesamt), 0), 1)           AS termine_prozent,
    ROUND(COALESCE(SUM(i.punkte_gewichtet * z.gewicht), 0), 1)    AS punkte,
    ROUND(100.0 * COALESCE(SUM(i.punkte_gewichtet * z.gewicht), 0)
          / NULLIF((SELECT punkte FROM gesamt), 0), 2)            AS anteil_prozent,
    MIN(i.termin_index)                                           AS erster_termin,
    MAX(i.termin_index)                                           AS letzter_termin
FROM thema th
LEFT JOIN v_zuordnung   z ON z.thema_id = th.id
LEFT JOIN v_teilaufgabe i ON i.teilaufgabe_id = z.teilaufgabe_id
GROUP BY th.id;

-- Bunseki: Heatmap Thema × Termin
CREATE VIEW v_heatmap AS
SELECT
    z.thema_id,
    i.termin_index,
    i.termin,
    ROUND(SUM(i.punkte_gewichtet * z.gewicht), 1) AS punkte
FROM v_zuordnung z
JOIN v_teilaufgabe i ON i.teilaufgabe_id = z.teilaufgabe_id
GROUP BY z.thema_id, i.termin_index;

-- Niwa und Michi: Lernstand je Thema in Punkten, mit Wachstumsstufe
CREATE VIEW v_thema_lernstand AS
WITH summen AS (
    SELECT
        z.thema_id,
        SUM(i.punkte_gewichtet * z.gewicht)                                              AS gesamt,
        SUM(CASE i.status WHEN 'gruen' THEN i.punkte_gewichtet * z.gewicht ELSE 0 END)   AS gruen,
        SUM(CASE i.status WHEN 'gelb'  THEN i.punkte_gewichtet * z.gewicht ELSE 0 END)   AS gelb,
        SUM(CASE i.status WHEN 'rot'   THEN i.punkte_gewichtet * z.gewicht ELSE 0 END)   AS rot,
        SUM(CASE i.status WHEN 'neu'   THEN i.punkte_gewichtet * z.gewicht ELSE 0 END)   AS neu
    FROM v_zuordnung z
    JOIN v_teilaufgabe i ON i.teilaufgabe_id = z.teilaufgabe_id
    GROUP BY z.thema_id
),
basis AS (
    SELECT
        th.id    AS thema_id,
        th.name,
        th.ebene,
        COALESCE(s.gesamt, 0) AS gesamt,
        COALESCE(s.gruen, 0)  AS gruen,
        COALESCE(s.gelb, 0)   AS gelb,
        COALESCE(s.rot, 0)    AS rot,
        COALESCE(s.neu, 0)    AS neu,
        COALESCE((s.gruen + 0.5 * s.gelb) / NULLIF(s.gesamt, 0), 0) AS b
    FROM thema th
    LEFT JOIN summen s ON s.thema_id = th.id
)
SELECT
    thema_id,
    name,
    ebene,
    ROUND(gesamt, 1) AS punkte_gesamt,
    ROUND(gruen, 1)  AS punkte_gruen,
    ROUND(gelb, 1)   AS punkte_gelb,
    ROUND(rot, 1)    AS punkte_rot,
    ROUND(neu, 1)    AS punkte_neu,
    ROUND(b, 3)      AS beherrschung,
    CASE
        WHEN b = 0   THEN 'samen'    -- 種
        WHEN b < 0.4 THEN 'keim'     -- 芽
        WHEN b < 0.8 THEN 'knospe'   -- 蕾
        ELSE              'bluete'   -- 花
    END              AS stufe
FROM basis;

-- Heute: die Prüfungsreife in Prozent (Bedingung „letzte zwei Simulationen“ prüft die App)
CREATE VIEW v_pruefungsreife AS
SELECT
    ROUND(100.0 * SUM(CASE status
                          WHEN 'gruen' THEN punkte_gewichtet
                          WHEN 'gelb'  THEN 0.5 * punkte_gewichtet
                          ELSE 0
                      END)
          / NULLIF(SUM(punkte_gewichtet), 0), 1) AS prozent,
    SUM(status = 'neu')   AS neu,
    SUM(status = 'rot')   AS rot,
    SUM(status = 'gelb')  AS gelb,
    SUM(status = 'gruen') AS gruen
FROM v_teilaufgabe;

-- Heute: fällige Wiederholungen
CREATE VIEW v_faellig AS
SELECT teilaufgabe_id, status, faellig_am
FROM karte
WHERE teilaufgabe_id IN (SELECT teilaufgabe_id FROM v_teilaufgabe)
  AND status <> 'neu'
  AND faellig_am IS NOT NULL
  AND faellig_am <= datetime('now');

-- Heute: Lerntage für die Lernserie
CREATE VIEW v_lerntage AS
SELECT date(zeitpunkt, 'localtime') AS tag, COUNT(*) AS bewertungen
FROM bewertung
GROUP BY tag;

-- Bunseki: KI-Nutzung
CREATE VIEW v_ki_nutzung AS
SELECT
    zweck,
    modell,
    COUNT(*)          AS aufrufe,
    SUM(aus_cache)    AS aus_cache,
    SUM(tokens_ein)   AS tokens_ein,
    SUM(tokens_aus)   AS tokens_aus
FROM ki_aufruf
GROUP BY zweck, modell;

PRAGMA user_version = 7;
