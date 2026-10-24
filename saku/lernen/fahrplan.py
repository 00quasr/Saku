"""Fahrplan bis zur Prüfung: Prognose der Wiederholungen, Tempo, Abdeckung nach Prüfungsgewicht und was am meisten bringt.
Alles im aktiven Umfang (v_teilaufgabe); Tagesziel und Lerntage kommen aus tagesziel."""

import math
import sqlite3
from collections import Counter
from datetime import date, timedelta

from saku.lernen import tagesziel

TEMPO_LERNTAGE = 7  # Tempo = neue Teilaufgaben im Schnitt dieser Lerntage
_IM_UMFANG = "teilaufgabe_id IN (SELECT teilaufgabe_id FROM v_teilaufgabe)"


def prognose(con: sqlite3.Connection, heute: date | None = None, tage: int = 14, ziel: dict | None = None) -> list[dict]:
    """Je Tag ab heute: Wiederholungen und neue Teilaufgaben. Heute zählt, was das Tagesziel noch offen hat; danach die
    schon geplanten Wiederholungen (karte.faellig_am) und die neuen, die das Tagesziel an jenem Tag verlangen wird.
    Wiederholungen der künftig neuen sind noch nicht eingeplant."""
    heute = heute or date.today()
    ziel = ziel or tagesziel.tagesziel(con, heute)
    wdh = Counter()
    for z in con.execute(f"SELECT date(faellig_am, 'localtime') AS tag, COUNT(*) AS n FROM karte WHERE {_IM_UMFANG} "
                         "AND status <> 'neu' AND faellig_am IS NOT NULL GROUP BY tag"):
        wdh[(date.fromisoformat(z["tag"]) - heute).days] += z["n"]
    rest = con.execute("SELECT COUNT(*) FROM v_teilaufgabe WHERE status = 'neu'").fetchone()[0] - ziel["neu_offen"]
    pruefung = tagesziel.tage_bis_pruefung(con, heute)
    tage_liste = [{"tag": heute, "wdh": ziel["wdh_offen"], "neu": ziel["neu_offen"]}]
    for i in range(1, tage):
        tag = heute + timedelta(days=i)
        neu = tagesziel.neu_am_tag(rest, tagesziel.lerntage(con, tag))
        rest -= neu
        tage_liste.append({"tag": tag, "wdh": wdh[i], "neu": neu})
    return [t | {"summe": t["wdh"] + t["neu"], "heute": i == 0, "pruefung": i == pruefung} for i, t in enumerate(tage_liste)]


def tempo(con: sqlite3.Connection, heute: date | None = None) -> dict:
    """Neue Teilaufgaben am Tag im Schnitt der letzten Lerntage vor heute (stabil, solange heute gelernt wird) und das Datum,
    an dem bei diesem Tempo alle einmal gesehen sind, verglichen mit dem letzten Lerntag vor dem Puffer."""
    heute = heute or date.today()
    erste = Counter(date.fromisoformat(z[0]) for z in con.execute(
        f"SELECT date(MIN(zeitpunkt), 'localtime') FROM bewertung WHERE {_IM_UMFANG} GROUP BY teilaufgabe_id"))
    lerntage = [date.fromisoformat(z[0]) for z in con.execute(
        f"SELECT DISTINCT date(zeitpunkt, 'localtime') AS tag FROM bewertung WHERE {_IM_UMFANG} "
        "AND date(zeitpunkt, 'localtime') < ? ORDER BY tag DESC LIMIT ?", (heute.isoformat(), TEMPO_LERNTAGE))]
    # bei Tagesbeginn noch neu: heute zählt als erster Tag
    rest = con.execute("SELECT COUNT(*) FROM v_teilaufgabe WHERE status = 'neu'").fetchone()[0] + erste[heute]
    schnitt = sum(erste[t] for t in lerntage) / len(lerntage) if lerntage else None
    fertig = heute + timedelta(days=math.ceil(rest / schnitt) - 1) if schnitt and rest else None
    tage, lt = tagesziel.tage_bis_pruefung(con, heute), tagesziel.lerntage(con, heute)
    termin = heute + timedelta(days=tage) if tage is not None and tage >= 0 else None
    return {
        "schnitt": schnitt, "lerntage": len(lerntage), "rest": rest, "fertig": fertig, "termin": termin,
        "letzter": termin and heute + timedelta(days=lt - 1),  # letzter Lerntag vor dem Puffer
        "noetig": termin and math.ceil(rest / lt),
        "abstand": (termin - fertig).days if termin and fertig else None,  # > 0: vor der Prüfung durch
    }


def _anteile(gruen: float, gelb: float, rot: float, neu: float) -> dict:
    """Punkte in Prozent: sicher (grün), im Aufbau (gelb und rot, schon geübt), noch nie (neu); zusammen 100."""
    teile = {"sicher": gruen, "aufbau": gelb + rot, "nie": neu}
    summe = sum(teile.values())
    return {k: 100 * v / summe if summe else 0 for k, v in teile.items()} | {"punkte": summe}


def abdeckung(con: sqlite3.Connection) -> dict:
    """Wie viel der bisher erzielbaren Prüfungspunkte sitzt: gesamt, je Bereich und je Thema (Ebene 2)."""
    z = con.execute("SELECT TOTAL(punkte_gewichtet * (status = 'gruen')), TOTAL(punkte_gewichtet * (status = 'gelb')), "
                    "TOTAL(punkte_gewichtet * (status = 'rot')), TOTAL(punkte_gewichtet * (status = 'neu')) "
                    "FROM v_teilaufgabe").fetchone()
    bereiche = {}
    for t in con.execute(
            "SELECT l.thema_id, l.name, l.ebene, th.eltern_id, l.punkte_gruen, l.punkte_gelb, l.punkte_rot, l.punkte_neu "
            "FROM v_thema_lernstand l JOIN thema th ON th.id = l.thema_id WHERE l.ebene <= 2 AND l.punkte_gesamt > 0 "
            "ORDER BY l.ebene, CASE l.ebene WHEN 1 THEN th.position END, l.punkte_gesamt DESC, l.name"):
        eintrag = {"id": t["thema_id"], "name": t["name"]} | _anteile(t["punkte_gruen"], t["punkte_gelb"], t["punkte_rot"], t["punkte_neu"])
        if t["ebene"] == 1:
            bereiche[t["thema_id"]] = eintrag | {"themen": []}
        elif t["eltern_id"] in bereiche:
            bereiche[t["eltern_id"]]["themen"].append(eintrag)
    return {"gesamt": _anteile(*z), "bereiche": list(bereiche.values())}


def gewinn(con: sqlite3.Connection, anzahl: int = 8) -> list[dict]:
    """Themen (Ebene 2) nach erwartetem Gewinn = Prüfungspunkte × (1 − Lernstand), dazu Teilaufgaben und letzter Termin."""
    top = con.execute("SELECT thema_id, name, punkte_gesamt, beherrschung, punkte_gesamt * (1 - beherrschung) AS gewinn "
                      "FROM v_thema_lernstand WHERE ebene = 2 AND punkte_gesamt > 0 AND beherrschung < 1 "
                      "ORDER BY gewinn DESC, name LIMIT ?", (anzahl,)).fetchall()
    ids = [z["thema_id"] for z in top]
    info = {z["thema_id"]: z for z in con.execute(
        "SELECT z.thema_id, COUNT(*) AS teilaufgaben, MAX(v.termin_index) AS letzter_termin FROM v_zuordnung z "
        f"JOIN v_teilaufgabe v ON v.teilaufgabe_id = z.teilaufgabe_id WHERE z.thema_id IN ({','.join('?' * len(ids))}) "
        "GROUP BY z.thema_id", ids)}
    return [dict(z) | {"teilaufgaben": info[z["thema_id"]]["teilaufgaben"],
                       "letzter_termin": info[z["thema_id"]]["letzter_termin"]} for z in top]
