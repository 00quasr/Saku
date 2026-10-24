"""Hochrechnung der Abschlussprüfung nach der Ausbildungsverordnung der IT-Berufe (2020, Fachinformatiker/-in).

Gewichtung: Teil 1 20 %, betriebliche Projektarbeit 50 %, zwei schriftliche Prüfungsbereiche je 10 %, WiSo 10 %.
Bestanden, wenn
  1. Teil 1 und Teil 2 zusammen mindestens „ausreichend“ (50 Punkte),
  2. Teil 2 allein mindestens „ausreichend“,
  3. die Projektarbeit mindestens „ausreichend“,
  4. mindestens zwei der übrigen Bereiche von Teil 2 mindestens „ausreichend“ und
  5. kein Bereich von Teil 2 „ungenügend“ (unter 30 Punkten).
Eine mündliche Ergänzungsprüfung ist in einem schriftlichen Bereich von Teil 2 möglich, der unter 50 liegt, wenn sie
den Ausschlag geben kann; schriftlich und mündlich zählen 2 : 1.
"""

import sqlite3

from saku.db import einstellung
from saku.lernen import probepruefung, simulation
from saku.pipeline import inventar

GEWICHTE = {"ap1": 0.2, "projekt": 0.5, "pb2": 0.1, "pb3": 0.1, "wiso": 0.1}
TEIL2 = ("projekt", "pb2", "pb3", "wiso")
SCHRIFTLICH = ("pb2", "pb3", "wiso")
AUSREICHEND, UNGENUEGEND = 50, 30
BEREICHE = {"1201": (inventar.PLANEN, inventar.ENTWICKLUNG), "1202": (inventar.KONZEPTION, inventar.NETZWERKE)}


def _gewichtet(werte: dict, schluessel) -> float | None:
    if any(werte.get(k) is None for k in schluessel):
        return None
    summe = sum(GEWICHTE[k] for k in schluessel)
    return round(sum(werte[k] * GEWICHTE[k] for k in schluessel) / summe, 1)


def berechnen(werte: dict[str, float | None]) -> dict:
    """Gesamt, Teil 2, Note und die Bestehensregeln (True, False oder None = noch offen)."""
    gesamt, teil2 = _gewichtet(werte, GEWICHTE), _gewichtet(werte, TEIL2)
    w = werte

    def mind(k, grenze=AUSREICHEND):
        return None if w.get(k) is None else w[k] >= grenze

    schriftlich_ok = [mind(k) for k in SCHRIFTLICH]
    regeln = [
        ("Teil 1 und Teil 2 zusammen mindestens ausreichend", None if gesamt is None else gesamt >= AUSREICHEND),
        ("Teil 2 mindestens ausreichend", None if teil2 is None else teil2 >= AUSREICHEND),
        ("Projektarbeit mindestens ausreichend", mind("projekt")),
        ("Mindestens zwei der übrigen Bereiche ausreichend",
         True if schriftlich_ok.count(True) >= 2 else None if None in schriftlich_ok else False),
        ("Kein Bereich von Teil 2 ungenügend",
         False if any(mind(k, UNGENUEGEND) is False for k in TEIL2) else None if any(w.get(k) is None for k in TEIL2) else True),
    ]
    # Ergänzungsprüfung: welche mündliche Punktzahl hebt den Bereich auf 50? (2 × schriftlich + mündlich) / 3 ≥ 50
    ergaenzung = {k: max(0, 3 * AUSREICHEND - 2 * w[k]) for k in SCHRIFTLICH
                  if w.get(k) is not None and w[k] < AUSREICHEND and 3 * AUSREICHEND - 2 * w[k] <= 100}
    werte_regeln = [r for _, r in regeln]
    return {
        "gesamt": gesamt, "teil2": teil2,
        "note": None if gesamt is None else simulation.note(gesamt),
        "regeln": regeln,
        "bestanden": False if False in werte_regeln else None if None in werte_regeln else True,
        "ergaenzung": ergaenzung,
    }


def _lernstand(con: sqlite3.Connection, bereich: str) -> float | None:
    """Punkte (0–100), die im Bereich sicher sitzen: grün voll, gelb halb; None ohne geübte Teilaufgabe."""
    z = con.execute(
        "SELECT SUM(punkte_gewichtet) AS alle, SUM(CASE status WHEN 'gruen' THEN punkte_gewichtet WHEN 'gelb' "
        "THEN 0.5 * punkte_gewichtet ELSE 0 END) AS sitzt, SUM(status <> 'neu') AS geuebt "
        "FROM v_teilaufgabe WHERE bereich = ?", (bereich,)).fetchone()
    return round(100 * z["sitzt"] / z["alle"], 1) if z["alle"] and z["geuebt"] else None


def _simulation(con: sqlite3.Connection, bereich: str) -> float | None:
    z = con.execute("SELECT punkte_erreicht, punkte_moeglich FROM simulation WHERE bereich = ? AND note IS NOT NULL "
                    "ORDER BY gestartet_am DESC, id DESC LIMIT 1", (bereich,)).fetchone()
    return simulation.umrechnen(z["punkte_erreicht"] or 0, z["punkte_moeglich"] or 0) if z else None


def stand(con: sqlite3.Connection) -> dict:
    """Werte je Bereich mit Herkunft: eigene Eingabe, letzte Simulation oder Lernstand; die AP1 ohne eigene Note geschätzt aus
    dem Schnitt der letzten drei Probeprüfungen."""
    beruf = einstellung(con, "beruf", "1201")
    pb2, pb3 = BEREICHE.get(beruf, BEREICHE["1201"])
    zeilen = []

    def eingabe(schluessel):
        wert = einstellung(con, f"note_{schluessel}")
        return float(wert) if wert else None

    for k, name, bereich in [("ap1", "AP1 · Einrichten eines IT-gestützten Arbeitsplatzes", None),
                             ("projekt", "Betriebliche Projektarbeit mit Präsentation und Fachgespräch", None),
                             ("pb2", pb2, pb2), ("pb3", pb3, pb3), ("wiso", inventar.WISO, inventar.WISO)]:
        wert, quelle = eingabe(k), "eingabe"
        if wert is None and k == "ap1":
            wert, quelle = probepruefung.schnitt(con), "probepruefung"
        if wert is None and bereich:
            wert, quelle = _simulation(con, bereich), "simulation"
            if wert is None:
                wert, quelle = _lernstand(con, bereich), "lernstand"
        zeilen.append({"schluessel": k, "name": name, "gewicht": GEWICHTE[k], "wert": wert,
                       "quelle": quelle if wert is not None else None, "eigen": eingabe(k),
                       "note": None if wert is None else simulation.note(wert)})
    return {"zeilen": zeilen, **berechnen({z["schluessel"]: z["wert"] for z in zeilen})}
