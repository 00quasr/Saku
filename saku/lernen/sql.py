"""SQL-Sandbox: eigene SQL-Antworten auf erfundenen Beispieldaten (Schritt sandbox) ausführen und mit der Musterlösung
vergleichen. Jede Ausführung bekommt eine frische Datenbank im Speicher; Zeitlimit, Autorisierer und Größengrenzen
schützen die App vor Endlosschleifen, Dateizugriffen und riesigen Ergebnissen."""

import re
import sqlite3
import time
from collections import Counter
from contextlib import closing

ZEIGEN = 50          # so viele Zeilen je Tabelle zeigt Saku
GRENZE = 5000        # mehr Zeilen liest Saku nicht
SEKUNDEN = 2         # je Ausführung
ANWEISUNGEN = 20     # ein kleines Skript, kein Programm
ZEICHEN = 20_000
# Speicher: Text je Wert, Spalten, Text und Blobs eines Ergebnisses zusammen (5000 Zeilen langer Texte wären sonst Gigabytes)
LAENGE, SPALTEN, BYTES = 100_000, 100, 20_000_000
ZU_GROSS = "Zu groß: Die Sandbox ist für kleine Beispieldaten gedacht."

_VERBOTEN = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA}
_FUNKTIONEN = {"load_extension", "fts3_tokenizer"}
_KOMMENTAR = re.compile(r"--[^\n]*|/\*.*?(?:\*/|$)", re.S)


class SqlFehler(Exception):
    """Die Anweisung läuft nicht (Syntax, Zeitlimit, gesperrt); die Meldung ist für die Anzeige gedacht."""


def laden(con: sqlite3.Connection, aufgabe_id: int) -> tuple[str, str] | None:
    """(ddl, daten) der Sandbox einer Aufgabe, None ohne Sandbox."""
    zeile = con.execute("SELECT ddl, daten FROM sql_sandbox WHERE aufgabe_id = ?", (aufgabe_id,)).fetchone()
    return (zeile[0], zeile[1]) if zeile else None


def anweisungen(sql: str) -> list[str]:
    """Skript in einzelne Anweisungen; Semikolons in Zeichenketten und Kommentaren trennen nicht, reine Kommentare fallen weg."""
    teile, start = [], 0
    for i, zeichen in enumerate(sql):
        if zeichen == ";" and sqlite3.complete_statement(sql[start:i + 1]):
            teile.append(sql[start:i + 1])
            start = i + 1
    teile.append(sql[start:])
    return [t.strip() for t in teile if _KOMMENTAR.sub("", t).strip(" \t\r\n;")]


def _erlaubt(aktion, _arg1, arg2, _db, _ausloeser) -> int:
    """Autorisierer: keine fremden Dateien (ATTACH, auch VACUUM INTO), keine PRAGMA (manche wirken prozessweit), keine Erweiterungen."""
    if aktion in _VERBOTEN or aktion == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in _FUNKTIONEN:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def _meldung(fehler: Exception) -> str:
    text = str(fehler)
    if text == "interrupted":
        return f"Abgebrochen: Die Anweisung lief länger als {SEKUNDEN} Sekunden (Endlosschleife?)."
    if "not authorized" in text or "authorization denied" in text:
        return "Nicht erlaubt: ATTACH, PRAGMA und Erweiterungen sind in der Sandbox gesperrt."
    if "database or disk is full" in text or "too big" in text:
        return ZU_GROSS
    return f"SQLite meldet: {text}"


def _bytes(zeile: tuple) -> int:
    return sum(len(w) for w in zeile if isinstance(w, (str, bytes)))


def _holen(cur: sqlite3.Cursor, frei: int = BYTES) -> list[tuple]:
    """Höchstens GRENZE + 1 Zeilen und frei Bytes an Text und Blobs."""
    zeilen = []
    for zeile in cur:
        frei -= _bytes(zeile)
        if frei < 0:
            raise SqlFehler(ZU_GROSS)
        zeilen.append(zeile)
        if len(zeilen) > GRENZE:
            break
    return zeilen


def _ausfuehren(con: sqlite3.Connection, sql: str) -> tuple[list[str], list[tuple]] | None:
    """Führt die Anweisungen nacheinander aus; Spalten und Zeilen (höchstens GRENZE + 1) der letzten, die Zeilen liefert."""
    ende = time.monotonic() + SEKUNDEN
    con.set_progress_handler(lambda: time.monotonic() > ende, 1000)
    ergebnis = None
    try:
        for teil in anweisungen(sql):
            cur = con.execute(teil)
            if cur.description:
                ergebnis = [d[0] for d in cur.description], _holen(cur)
    except (sqlite3.Error, ValueError) as fehler:  # ValueError: Nullzeichen im Text
        raise SqlFehler(_meldung(fehler)) from None
    finally:
        con.set_progress_handler(None, 0)
    return ergebnis


def _datenbank(ddl: str, daten: str) -> sqlite3.Connection:
    """Frische Datenbank im Speicher mit Tabellen und Beispieldaten, schon mit allen Grenzen."""
    con = sqlite3.connect(":memory:", isolation_level=None)
    con.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
    con.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, LAENGE)
    con.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, SPALTEN)
    con.execute("PRAGMA max_page_count = 5000")  # höchstens 20 MB, auch für temporäre Tabellen
    con.execute("PRAGMA temp.max_page_count = 5000")
    con.set_authorizer(_erlaubt)
    try:
        _ausfuehren(con, ddl)
        _ausfuehren(con, daten)
    except SqlFehler:
        con.close()
        raise
    return con


def _eigene(con: sqlite3.Connection, sql: str) -> tuple[list[str], list[tuple]] | None:
    teile = anweisungen(sql)
    if not teile:
        raise SqlFehler("Schreib erst eine SQL-Anweisung.")
    if len(sql) > ZEICHEN or len(teile) > ANWEISUNGEN:
        raise SqlFehler(f"Zu lang: höchstens {ANWEISUNGEN} Anweisungen.")
    return _ausfuehren(con, sql)


def _stand(con: sqlite3.Connection) -> dict[str, tuple[list[str], list[tuple]]]:
    """Alle Tabellen mit Spalten und Zeilen, zusammen in den Grenzen eines Ergebnisses: berechnete Spalten (b AS (…)) sind erst
    beim Lesen groß. SqlFehler, wenn das Lesen scheitert."""
    stand, frei = {}, BYTES
    try:
        for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
            cur = con.execute('SELECT * FROM "{}"'.format(name.replace('"', '""')))
            stand[name] = [d[0] for d in cur.description], _holen(cur, frei)
            frei -= sum(map(_bytes, stand[name][1]))
    except sqlite3.Error as fehler:
        raise SqlFehler(_meldung(fehler)) from None
    return stand


def _wert(w):
    """Zahlen mit kleiner Toleranz: auf zwei Nachkommastellen (AVG gegen ROUND(AVG, 2)), 5 und 5.0 sind gleich."""
    return round(float(w), 2) + 0.0 if isinstance(w, (int, float)) else w


def _fakten(stand: dict) -> Counter:
    """Spalten und Zeilen als vergleichbare Fakten; Namen ohne Groß/klein, Zeilen nach Spaltennamen ausgerichtet."""
    fakten = Counter()
    for tabelle, (spalten, zeilen) in stand.items():
        namen = [s.lower() for s in spalten]
        fakten.update(("spalte", tabelle.lower(), s) for s in namen)
        fakten.update(("zeile", tabelle.lower(), tuple(sorted(zip(namen, map(_wert, z))))) for z in zeilen)
    return fakten


def _zeilen(n: int) -> str:
    return f"{n} {'Zeile' if n == 1 else 'Zeilen'}"


def _abweichung(fehlen: int, zu_viel: int) -> str:
    """„2 Zeilen fehlen, 1 Zeile zu viel“"""
    teile = [f"{_zeilen(fehlen)} {'fehlt' if fehlen == 1 else 'fehlen'}"] if fehlen else []
    return ", ".join(teile + [f"{_zeilen(zu_viel)} zu viel"] * bool(zu_viel))


def _spalten(namen: set, wie: str) -> str:
    """„Spalte ort fehlt“, „Spalten a, b zu viel“"""
    wie = {"fehlt": "fehlen"}.get(wie, wie) if len(namen) > 1 else wie
    return f"Spalte{'n' * (len(namen) > 1)} {', '.join(sorted(namen))} {wie}"


def _tabelle(titel: str, spalten: list[str], zeilen: list[tuple]) -> dict:
    return {"titel": titel, "spalten": spalten, "zeilen": zeilen[:ZEIGEN],
            "weitere": max(0, min(len(zeilen), GRENZE) - ZEIGEN), "abgeschnitten": len(zeilen) > GRENZE}


def _stufe(treffer: int, soll: int, ist: int) -> int:
    """Nicht genau richtig ist höchstens „teilweise“: ab der Hälfte, sonst „nicht gewusst“."""
    return 2 if treffer / max(soll, ist, 1) >= 0.5 else 1


def _spalten_zuordnen(soll: list[tuple], ist: list[tuple], n_soll: int, n_ist: int) -> list[int] | None:
    """Je Spalte der Lösung die eigene Spalte mit denselben Werten: andere Reihenfolge und Namen sind egal."""
    def werte(zeilen, k):
        return Counter(z[k] for z in zeilen)
    frei, zuordnung = list(range(n_ist)), []
    for k in range(n_soll):
        ziel = werte(soll, k)
        treffer = next((j for j in sorted(frei, key=lambda j: j != k) if werte(ist, j) == ziel), None)
        if treffer is None:
            return None
        zuordnung.append(treffer)
        frei.remove(treffer)
    return zuordnung


def sortierung(sql: str, spalten: list[str]) -> list[int] | None:
    """Spalten, nach denen die Lösung sortiert (ORDER BY auf oberster Ebene); None ohne ORDER BY.
    Lässt sich ein Ausdruck keiner Ergebnisspalte zuordnen, zählt die ganze Zeile."""
    flach = sql
    while (neu := re.sub(r"\([^()]*\)", " ", flach)) != flach:  # Unterabfragen, OVER (…) und Funktionen fallen weg
        flach = neu
    treffer = re.search(r"\border\s+by\s+(.+?)(?:\blimit\b|\boffset\b|;|$)", flach, re.I | re.S)
    if not treffer:
        return None
    namen = [s.lower() for s in spalten]
    ergebnis = []
    for ausdruck in treffer[1].split(","):
        ausdruck = re.sub(r"\s+(asc|desc|nulls\s+first|nulls\s+last|collate\s+\w+)\b", " ", ausdruck, flags=re.I)
        name = ausdruck.strip().split(".")[-1].strip('"`[] ').lower()
        if name.isdigit() and 0 < int(name) <= len(namen):
            ergebnis.append(int(name) - 1)
        elif name in namen:
            ergebnis.append(namen.index(name))
        else:
            return list(range(len(spalten)))
    return ergebnis


def _ergebnisse_vergleichen(loesung: str, soll, ist) -> dict:
    """SELECT: Ergebnis-Mengen; die Reihenfolge nur, wenn die Lösung sortiert (Gleichstand im Sortierschlüssel ist egal)."""
    (s_spalten, s_roh), (i_spalten, i_roh) = soll, ist
    ergebnis = {"hinweise": [], "tabellen": [(_tabelle("Erwartet", s_spalten, s_roh), _tabelle("Dein Ergebnis", i_spalten, i_roh))]}
    if len(i_roh) > GRENZE:
        return ergebnis | {"ergebnis": 1, "hinweise": [f"Dein Ergebnis hat mehr als {GRENZE} Zeilen."]}
    s, i = [tuple(map(_wert, z)) for z in s_roh], [tuple(map(_wert, z)) for z in i_roh]
    hoechstens = 3
    zuordnung = _spalten_zuordnen(s, i, len(s_spalten), len(i_spalten))
    if zuordnung is not None:
        i = [tuple(z[k] for k in zuordnung) for z in i]
        if len(i_spalten) > len(s_spalten):  # zusätzliche Spalten kosten nur „teilweise“
            n = len(i_spalten) - len(s_spalten)
            ergebnis["hinweise"].append(f"{n} Spalte{'n' * (n > 1)} zu viel.")
            hoechstens = 2
    elif len(i_spalten) != len(s_spalten):
        return ergebnis | {"ergebnis": 1, "hinweise": [f"{len(s_spalten)} Spalten erwartet, {len(i_spalten)} geliefert."]}
    zaehler_s, zaehler_i = Counter(s), Counter(i)
    if zaehler_s != zaehler_i:
        ergebnis["hinweise"].append(_abweichung(sum((zaehler_s - zaehler_i).values()), sum((zaehler_i - zaehler_s).values())) + ".")
        return ergebnis | {"ergebnis": _stufe(sum((zaehler_s & zaehler_i).values()), len(s), len(i))}
    schluessel = sortierung(loesung, s_spalten)
    if schluessel is not None and [[z[k] for k in schluessel] for z in s] != [[z[k] for k in schluessel] for z in i]:
        ergebnis["hinweise"].append("Die Zeilen stimmen, die Reihenfolge nicht (ORDER BY).")
        hoechstens = 2
    return ergebnis | {"ergebnis": hoechstens}


def _staende_vergleichen(vorher: dict, soll: dict, ist: dict) -> dict:
    """UPDATE, INSERT, DELETE, CREATE, ALTER: alle Tabellen nach dem Ausführen. Bewertet werden die Änderungen gegenüber
    vorher, sonst wäre „nichts tun“ schon fast richtig."""
    a, s, i = _fakten(vorher), _fakten(soll), _fakten(ist)
    if s == i:
        return {"ergebnis": 3, "hinweise": [], "tabellen": []}
    hinweise, tabellen = ["Deine Anweisung ändert nichts."] if a == i else [], []
    s_namen, i_namen = {n.lower(): n for n in soll}, {n.lower(): n for n in ist}
    for name in sorted(s_namen.keys() | i_namen.keys()):
        erwartet = _tabelle(f"{s_namen[name]} erwartet", *soll[s_namen[name]]) if name in s_namen else None
        eigene = _tabelle(f"{i_namen[name]} bei dir", *ist[i_namen[name]]) if name in i_namen else None
        if not eigene:
            hinweise.append(f"Tabelle {s_namen[name]} fehlt.")
        elif not erwartet:
            hinweise.append(f"Tabelle {i_namen[name]} ist zu viel.")
        else:
            fs, fi = _fakten({name: soll[s_namen[name]]}), _fakten({name: ist[i_namen[name]]})
            if fs == fi:
                continue
            spalten_s, spalten_i = {f[2] for f in fs if f[0] == "spalte"}, {f[2] for f in fi if f[0] == "spalte"}
            if spalten_s != spalten_i:  # dann weicht ohnehin jede Zeile ab
                teile = [_spalten(spalten_s - spalten_i, "fehlt")] * bool(spalten_s - spalten_i)
                teile += [_spalten(spalten_i - spalten_s, "zu viel")] * bool(spalten_i - spalten_s)
            else:
                teile = [_abweichung(sum((fs - fi).values()), sum((fi - fs).values()))]
            hinweise.append(f"Tabelle {s_namen[name]}: {', '.join(teile)}.")
        tabellen.append((erwartet, eigene))
    treffer = sum(((s - a) & (i - a)).values()) + sum(((a - s) & (a - i)).values())
    return {"ergebnis": _stufe(treffer, sum(((s - a) + (a - s)).values()), sum(((i - a) + (a - i)).values())),
            "hinweise": hinweise, "tabellen": tabellen}


def pruefen(ddl: str, daten: str, loesung: str, eigene: str) -> dict:
    """Eigene Anweisung gegen die Lösung: {ergebnis 1–3, hinweise, tabellen [(erwartet, eigenes)]}.
    SqlFehler, wenn die eigene Anweisung nicht läuft (dann gibt es keine Bewertung)."""
    with closing(_datenbank(ddl, daten)) as con:
        vorher = _stand(con)
        soll = _ausfuehren(con, loesung)
        soll_stand = _stand(con)
    with closing(_datenbank(ddl, daten)) as con:
        ist = _eigene(con, eigene)
        ist_stand = _stand(con)
    if soll is None:
        return _staende_vergleichen(vorher, soll_stand, ist_stand)
    if ist is None:
        return {"ergebnis": 1, "hinweise": ["Deine Anweisung liefert kein Ergebnis, erwartet ist eine Abfrage (SELECT)."],
                "tabellen": [(_tabelle("Erwartet", *soll), None)]}
    return _ergebnisse_vergleichen(loesung, soll, ist)


def ausfuehren(ddl: str, daten: str, eigene: str) -> dict:
    """„Ausführen“: das Ergebnis der letzten Abfrage, sonst die geänderten Tabellen. SqlFehler, wenn sie nicht läuft."""
    with closing(_datenbank(ddl, daten)) as con:
        vorher, aenderungen = _stand(con), con.total_changes
        ergebnis = _eigene(con, eigene)
        if ergebnis:
            n = len(ergebnis[1])
            return {"meldung": f"mehr als {GRENZE} Zeilen" if n > GRENZE else _zeilen(n), "tabellen": [_tabelle("Ergebnis", *ergebnis)]}
        nachher, geaendert = _stand(con), con.total_changes - aenderungen
    return {"meldung": f"{_zeilen(geaendert)} geändert" if geaendert else "Ausgeführt.",
            "tabellen": [_tabelle(n, *werte) for n, werte in nachher.items() if vorher.get(n) != werte]}


def schluessel(ddl: str, daten: str, anweisung: str) -> set[tuple[str, str, str]]:
    """Nach der Anweisung je Tabelle und Spalte: Primärschlüssel, NOT NULL, Fremdschlüssel auf …, für CREATE TABLE (der
    Zustandsvergleich sieht nur Spalten und Zeilen). SqlFehler, wenn sie nicht läuft."""
    with closing(_datenbank(ddl, daten)) as con:
        _eigene(con, anweisung)
        con.set_authorizer(None)  # die Anweisung ist durch, das Schema liest nur Saku (PRAGMA bleibt ihr gesperrt)
        # main. und 'main': temporäre Tabellen (unsichtbar im Vergleich) verdecken weder die Funktion noch die Tabelle
        raus = set()
        for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall():
            for _, spalte, _, pflicht, _, pk in con.execute("SELECT * FROM main.pragma_table_info(?, 'main')", (t,)).fetchall():
                if pk or pflicht:
                    raus.add((t.lower(), spalte.lower(), "Primärschlüssel" if pk else "NOT NULL"))
            for ziel, spalte in con.execute("""SELECT "table", "from" FROM main.pragma_foreign_key_list(?, 'main')""", (t,)).fetchall():
                raus.add((t.lower(), spalte.lower(), f"Fremdschlüssel auf {ziel.lower()}"))
    return raus


def tabellen(ddl: str, daten: str) -> list[dict]:
    """Die Beispieldaten der Sandbox, Tabelle für Tabelle."""
    with closing(_datenbank(ddl, daten)) as con:
        return [_tabelle(n, *werte) for n, werte in _stand(con).items()]


def testen(ddl: str, daten: str, loesungen: dict[int, str]) -> None:
    """Für die Pipeline: Tabellen und Daten laden und jede Lösung auf frischen Daten ausführen. SqlFehler, wenn etwas
    nicht läuft oder eine Lösung nichts zeigt (leeres Ergebnis, keine Änderung): Dann taugt sie nicht zum Vergleichen."""
    try:
        with closing(_datenbank(ddl, daten)) as con:
            if not _stand(con):
                raise SqlFehler("ddl legt keine Tabelle an.")
    except SqlFehler as fehler:
        raise SqlFehler(f"Tabellen und Daten: {fehler}") from None
    for t_id, loesung in loesungen.items():
        with closing(_datenbank(ddl, daten)) as con:
            vorher = _fakten(_stand(con))
            try:
                ergebnis = _ausfuehren(con, loesung)
            except SqlFehler as fehler:
                raise SqlFehler(f"Lösung {t_id}: {fehler}") from None
            if ergebnis is not None and not ergebnis[1]:
                raise SqlFehler(f"Lösung {t_id} liefert keine Zeilen.")
            if ergebnis is None and _fakten(_stand(con)) == vorher:
                raise SqlFehler(f"Lösung {t_id} ändert nichts an den Daten.")
