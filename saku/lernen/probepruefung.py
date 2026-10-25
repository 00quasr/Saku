"""Probeprüfung aus den Rechen-Generatoren: unbegrenzt neue Prüfungen im Umfang des Lernpfads, 100 Punkte in 90 Minuten,
von Saku sofort ausgewertet. Jede Aufgabe ist (Art, Seed, Punkte); dieselbe Zeile in probepruefung ergibt dieselbe Prüfung."""

import json
import random
import sqlite3

from saku.lernen import rechnen, simulation

MINUTEN, ANZAHL, SEEDS = 90, 12, 10 ** 6
# Punkte im Verhältnis zum Aufwand: eigenen Pseudocode schreiben dreifach; SQL schreiben und große Tabellen (VLSM,
# Schreibtischtest, Netzplan) doppelt; ein Steckbrief oder eine Rechnung mit wenigen Schritten einfach
AUFWAND = {"algorithmus": 3, "select": 2, "join": 2, "aendern": 2, "vlsm": 2, "schreibtisch": 2, "netzplan": 2}


def verteilen(gewichte: list[float], summe: int = 100) -> list[int]:
    """Ganze Punkte im Verhältnis der Gewichte, zusammen genau summe; die größten Reste bekommen je einen dazu."""
    roh = [summe * g / sum(gewichte) for g in gewichte]
    punkte = [int(r) for r in roh]
    for i in sorted(range(len(roh)), key=lambda i: punkte[i] - roh[i])[:summe - sum(punkte)]:
        punkte[i] += 1
    return punkte


def zusammenstellen(pfad: str, quoten: dict[str, float], rng: random.Random) -> list[tuple[str, int, int]]:
    """(Art, Seed, Punkte), nach Gruppen geordnet wie die Übersicht: erst aus jeder Gruppe des Umfangs eine Art, dann
    weitere bis ANZAHL, keine doppelt; beides gewichtet wie „Gemischt üben“ (was zuletzt oft falsch war, kommt häufiger)."""
    arten = rechnen.im_umfang(pfad)
    gewaehlt = []
    for gruppe in dict.fromkeys(rechnen.ARTEN[a].gruppe for a in arten):
        gewaehlt.append(rechnen.gemischt(rng, quoten, ohne=[a for a in rechnen.ARTEN if a not in arten or rechnen.ARTEN[a].gruppe != gruppe]))
    while len(gewaehlt) < min(ANZAHL, len(arten)):
        gewaehlt.append(rechnen.gemischt(rng, quoten, ohne=[a for a in rechnen.ARTEN if a not in arten] + gewaehlt))
    gewaehlt.sort(key=lambda a: (rechnen.GRUPPEN.index(rechnen.ARTEN[a].gruppe), arten.index(a)))
    return [(a, rng.randrange(SEEDS), p) for a, p in zip(gewaehlt, verteilen([AUFWAND.get(a, 1) for a in gewaehlt]))]


def bewerten(aufgabe: rechnen.Aufgabe, eingaben: dict[str, str]) -> dict[str, bool]:
    """Je Feld richtig? Ganz leer abgegeben zählt null, auch wo leere Zellen richtig wären (freie Plätze beim Hashing)."""
    if not any(v.strip() for v in eingaben.values()):
        return {f.name: False for f in aufgabe.felder}
    return rechnen.pruefen(aufgabe, eingaben)


def anteil(maximal: float, werte: dict[str, bool]) -> float:
    """Punkte anteilig nach richtigen Feldern, auf eine Stelle."""
    return round(maximal * sum(werte.values()) / len(werte), 1)


def anlegen(con: sqlite3.Connection, pfad: str, quoten: dict[str, float], rng: random.Random | None = None) -> int:
    pp_id = con.execute("INSERT INTO probepruefung (pfad, aufgaben, dauer_min) VALUES (?, ?, ?)",
                        (pfad, json.dumps(zusammenstellen(pfad, quoten, rng or random.Random())), MINUTEN)).lastrowid or 0
    con.commit()
    return pp_id


def laufende(con: sqlite3.Connection) -> sqlite3.Row | None:
    """Die jüngste nicht abgegebene Probeprüfung, deren Zeit noch läuft."""
    return con.execute("SELECT * FROM probepruefung WHERE beendet_am IS NULL "
                       "AND datetime(gestartet_am, '+' || dauer_min || ' minutes') > datetime('now') ORDER BY id DESC LIMIT 1").fetchone()


def aufgaben(zeile: sqlite3.Row) -> list[dict]:
    """Je Aufgabe Art, Seed, Punkte, die Aufgabe (aus dem Seed neu erzeugt) und die gespeicherten Eingaben; ist die Prüfung
    ausgewertet, auch werte (Feld richtig?) und erreicht. Die Formularfelder heißen a1-feld, a2-feld …"""
    alle = json.loads(zeile["eingaben"] or "{}")
    raus = []
    for i, (art, seed, punkte) in enumerate(json.loads(zeile["aufgaben"]), start=1):
        a = rechnen.erzeugen(art, seed)
        eingaben = {f.name: str(alle.get(f"a{i}-{f.name}", "")) for f in a.felder}  # str: von Hand bearbeiteter Lernstand
        werte = bewerten(a, eingaben) if zeile["note"] is not None else None
        raus.append({"art": rechnen.ARTEN[art], "seed": seed, "punkte": punkte, "aufgabe": a, "eingaben": eingaben,
                     "werte": werte, "erreicht": None if werte is None else anteil(punkte, werte)})
    return raus


def speichern(con: sqlite3.Connection, pp_id: int, eingaben: dict[str, str]) -> None:
    """Antworten bleiben änderbar, bis die Prüfung abgegeben ist (auch kurz nach Ablauf der Zeit)."""
    con.execute("UPDATE probepruefung SET eingaben = ? WHERE id = ? AND beendet_am IS NULL", (json.dumps(eingaben), pp_id))
    con.commit()


def auswerten(con: sqlite3.Connection, pp_id: int) -> None:
    """Einmal auswerten: Punkte je Aufgabe anteilig, Summe, Note nach IHK-Schlüssel; jede Aufgabe kommt als Versuch in
    rechenuebung (Fälligkeit, Tagesziel, Lerntage). Abgabe zweimal (Doppelklick, neu laden) zählt einmal."""
    if not con.execute("UPDATE probepruefung SET beendet_am = datetime('now') WHERE id = ? AND beendet_am IS NULL", (pp_id,)).rowcount:
        return
    zeile = con.execute("SELECT *, CAST((julianday(beendet_am) - julianday(gestartet_am)) * 86400 AS INTEGER) AS dauer_s "
                        "FROM probepruefung WHERE id = ?", (pp_id,)).fetchone()
    werte = [bewerten(x["aufgabe"], x["eingaben"]) for x in aufgaben(zeile)]
    teile = list(zip(json.loads(zeile["aufgaben"]), werte))
    dauer = min(max(zeile["dauer_s"], 0), zeile["dauer_min"] * 60) // len(teile)
    con.executemany("INSERT INTO rechenuebung (art, seed, richtig, felder_richtig, felder_gesamt, dauer_s) VALUES (?, ?, ?, ?, ?, ?)",
                    [(art, seed, int(all(w.values())), sum(w.values()), len(w), dauer) for (art, seed, _), w in teile])
    erreicht = round(sum(anteil(punkte, w) for (_, _, punkte), w in teile), 1)
    con.execute("UPDATE probepruefung SET punkte = ?, note = ? WHERE id = ?",
                (erreicht, simulation.note(simulation.umrechnen(erreicht, 100)), pp_id))
    con.commit()


def schnitt(con: sqlite3.Connection, pfad: str = "AP1", anzahl: int = 3) -> float | None:
    """Mittel der letzten ausgewerteten Probeprüfungen des Lernpfads (0–100), None ohne eine."""
    wert = con.execute("SELECT AVG(punkte) FROM (SELECT punkte FROM probepruefung WHERE pfad = ? AND note IS NOT NULL "
                       "ORDER BY gestartet_am DESC, id DESC LIMIT ?)", (pfad, anzahl)).fetchone()[0]
    return None if wert is None else round(wert, 1)
