"""Bunseki 分析: Inventar, Heatmap, Dauerbrenner, Lücken, Kontrolle der Zuordnung und KI-Nutzung."""

import math
import sqlite3

from flask import Blueprint, abort, render_template, request

from saku.db import einstellung
from saku.pipeline.inventar import BEREICHE_JE_PFAD
from saku.web import db

bp = Blueprint("bunseki", __name__, url_prefix="/bunseki")

DAUERBRENNER = 70      # Prozent der Termine
LANGE_NICHT_DRAN = 3   # Termine seit dem letzten Auftritt
KONTROLLE = 0.6        # Sicherheit der Klassifikation

# Blätter der Themenliste: Unterthemen, oder Themen ohne Unterthemen
_BLATT = "s.ebene > 1 AND NOT EXISTS (SELECT 1 FROM thema k WHERE k.eltern_id = s.thema_id)"


def termin_name(index: int, ap1: bool = False) -> str:
    """termin_index (jahr * 2 + Winter/Herbst) → 'Sommer 2024', 'Winter 2024/25'; AP1: 'Frühjahr 2024', 'Herbst 2024'"""
    jahr, winter = divmod(index, 2)
    if ap1:
        return f"{'Herbst' if winter else 'Frühjahr'} {jahr}"
    return f"Winter {jahr}/{str(jahr + 1)[2:]}" if winter else f"Sommer {jahr}"


def inventar(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return con.execute("""
        SELECT p.id, p.jahr, p.saison, p.bereich, p.format,
               CASE p.saison WHEN 'Winter' THEN 'Winter ' || p.jahr || '/' || substr(CAST(p.jahr + 1 AS TEXT), 3, 2)
                    ELSE p.saison || ' ' || p.jahr END AS termin,
               (SELECT SUM(d.seiten) FROM dokument d WHERE d.pruefung_id = p.id AND d.art = 'aufgaben') AS seiten,
               (SELECT MIN(d.hat_textebene) FROM dokument d WHERE d.pruefung_id = p.id) AS textebene,
               (SELECT COUNT(*) FROM dokument d WHERE d.pruefung_id = p.id AND d.art = 'loesungen') AS loesungsdokumente,
               COUNT(t.id) AS teilaufgaben,
               COALESCE(SUM(t.loesung_text IS NOT NULL OR t.loesung_bilder <> '[]'), 0) AS mit_loesung
        FROM pruefung p
        JOIN v_umfang u ON (p.teil = 'AP1') = (u.teil = 'AP1') AND p.beruf IN ('IT', u.beruf)
        LEFT JOIN aufgabe a ON a.pruefung_id = p.id
        LEFT JOIN teilaufgabe t ON t.aufgabe_id = a.id
        GROUP BY p.id
        ORDER BY p.jahr * 2 + (p.saison IN ('Winter', 'Herbst')) DESC, p.bereich
    """).fetchall()


def heatmap(con: sqlite3.Connection) -> dict:
    """Themen der Ebene 2 × Termine, gruppiert nach Prüfungsbereich; stufe 1 bis 5 für die Tuschestufen."""
    termine = con.execute("SELECT DISTINCT termin_index, termin FROM v_teilaufgabe ORDER BY termin_index").fetchall()
    werte = {(z["thema_id"], z["termin_index"]): z["punkte"] for z in con.execute(
        "SELECT h.thema_id, h.termin_index, h.punkte FROM v_heatmap h JOIN thema th ON th.id = h.thema_id WHERE th.ebene = 2")}
    hoechster = max(werte.values(), default=0) or 1
    bereiche = []
    for bereich in con.execute("SELECT id, name FROM thema WHERE ebene = 1 ORDER BY position, id"):
        zeilen = []
        for th in con.execute("SELECT id, name FROM thema WHERE eltern_id = ? ORDER BY position, id", (bereich["id"],)):
            zellen = []
            for termin in termine:
                punkte = werte.get((th["id"], termin["termin_index"]), 0)
                zellen.append({"termin": termin["termin"], "punkte": punkte,
                               "stufe": math.ceil(5 * punkte / hoechster) if punkte else 0})
            zeilen.append({"id": th["id"], "name": th["name"], "zellen": zellen, "summe": sum(z["punkte"] for z in zellen)})
        bereiche.append({"name": bereich["name"], "zeilen": zeilen})
    return {"termine": termine, "bereiche": bereiche}


def _statistik(con: sqlite3.Connection, bedingung: str, ordnung: str, *parameter) -> list[sqlite3.Row]:
    # die Termine einmal ausrechnen statt je Thema (MATERIALIZED), sonst läuft v_teilaufgabe hunderte Male
    return con.execute(f"""
        WITH termine AS MATERIALIZED (SELECT DISTINCT termin_index FROM v_teilaufgabe)
        SELECT * FROM (
            SELECT s.*, e.name AS eltern,
                   (SELECT COUNT(*) FROM termine t WHERE t.termin_index > s.letzter_termin) AS seitdem,
                   (SELECT COUNT(*) FROM termine) AS alle_termine
            FROM v_themen_statistik s LEFT JOIN thema e ON e.id = s.eltern_id
            WHERE {_BLATT}
        ) WHERE {bedingung} ORDER BY {ordnung}
    """, parameter).fetchall()


def dauerbrenner(con):
    return _statistik(con, "termine_prozent >= ?", "termine_prozent DESC, punkte DESC, name", DAUERBRENNER)


def lange_nicht_dran(con):
    return _statistik(con, "seitdem > ?", "seitdem DESC, punkte DESC, name", LANGE_NICHT_DRAN)


def nie_geprueft(con):
    return _statistik(con, "teilaufgaben = 0", "eltern, name")


_TEILAUFGABEN = """
    SELECT v.teilaufgabe_id, v.termin, v.aufgabe_nr, v.kennung, v.punkte, v.bereich, t.text,
           MIN(tt.sicherheit) AS sicherheit,
           (SELECT tt2.thema_id FROM teilaufgabe_thema tt2 WHERE tt2.teilaufgabe_id = v.teilaufgabe_id
            ORDER BY tt2.gewicht DESC LIMIT 1) AS haupt_id,
           GROUP_CONCAT(th.name, ', ') AS themen
    FROM v_teilaufgabe v
    JOIN teilaufgabe t ON t.id = v.teilaufgabe_id
    LEFT JOIN teilaufgabe_thema tt ON tt.teilaufgabe_id = v.teilaufgabe_id
    LEFT JOIN thema th ON th.id = tt.thema_id
"""


def ohne_thema(con):
    return con.execute(_TEILAUFGABEN + " GROUP BY v.teilaufgabe_id HAVING COUNT(tt.thema_id) = 0 "
                       "ORDER BY v.termin_index DESC, v.aufgabe_nr, v.kennung").fetchall()


def kontrolle(con):
    """Unsichere KI-Zuordnungen; was einmal manuell bestätigt ist, taucht nicht mehr auf."""
    return con.execute(_TEILAUFGABEN + " GROUP BY v.teilaufgabe_id "
                       "HAVING MIN(tt.sicherheit) < ? AND SUM(tt.quelle = 'manuell') = 0 "
                       "ORDER BY sicherheit, v.termin_index DESC, v.aufgabe_nr, v.kennung", (KONTROLLE,)).fetchall()


def ki_nutzung(con):
    return con.execute("SELECT * FROM v_ki_nutzung ORDER BY aufrufe DESC, zweck").fetchall()


def themenwahl(con) -> list[dict]:
    """Auswahl für die Korrektur: je Prüfungsbereich die Themen und ihre Unterthemen."""
    alle = con.execute("SELECT id, eltern_id, ebene, name FROM thema ORDER BY position, id").fetchall()
    kinder = {}
    for th in alle:
        kinder.setdefault(th["eltern_id"], []).append(th)
    pfad = con.execute("SELECT pfad FROM v_umfang").fetchone()[0]
    erlaubt = BEREICHE_JE_PFAD.get(pfad)
    gruppen = []
    for bereich in kinder.get(None, []):
        if erlaubt and bereich["name"] not in erlaubt:
            continue
        optionen = []
        for th in kinder.get(bereich["id"], []):
            optionen.append((th["id"], th["name"]))
            optionen += [(u["id"], f"{th['name']} › {u['name']}") for u in kinder.get(th["id"], [])]
        gruppen.append({"name": bereich["name"], "optionen": optionen})
    return gruppen


KURZ = {"Planen eines Softwareproduktes": "Planen", "Entwicklung und Umsetzung von Algorithmen": "Entwicklung",
        "Konzeption und Administration von IT-Systemen": "Konzeption", "Analyse und Entwicklung von Netzwerken": "Netzwerke",
        "Einrichten eines IT-gestützten Arbeitsplatzes": "AP1", "Wirtschafts- und Sozialkunde": "WiSo",
        "Ganzheitliche Aufgabe I": "GA 1", "Ganzheitliche Aufgabe II": "GA 2"}


def matrix(inventar_: list) -> dict:
    """Inventar als Matrix: Termine (neueste zuerst) × Prüfungsbereiche; das frühere Format bekommt eigene Spalten."""
    spalten = sorted({(p["bereich"], p["format"]) for p in inventar_},
                     key=lambda s: (s[1] == "frueher", list(KURZ).index(s[0]) if s[0] in KURZ else 99))
    zeilen = {}
    for p in inventar_:
        zeilen.setdefault(p["termin"], {})[(p["bereich"], p["format"])] = p
    return {"spalten": [{"schluessel": s, "name": KURZ.get(s[0], s[0]) + (" alt" if s[1] == "frueher" else "")} for s in spalten],
            "zeilen": list(zeilen.items())}


def katalog(con) -> list[dict]:
    """Die Themenliste (aus den IHK-Prüfungskatalogen) als Checkliste: Bereich → Thema → Unterthema mit
    Terminen, in denen es drankam, und dem eigenen Lernstand."""
    from saku.niwa import _im_umfang
    zeilen = _im_umfang(con)
    kinder = {}
    for z in zeilen:
        kinder.setdefault(z["eltern_id"], []).append(dict(z))
    bereiche = []
    for b in [dict(z) for z in zeilen if z["ebene"] == 1]:
        themen = [t | {"unterthemen": kinder.get(t["id"], [])} for t in kinder.get(b["id"], [])]
        punkte = [u for t in themen for u in t["unterthemen"]] or themen
        bereiche.append(b | {"themen": themen, "gesamt": len(punkte),
                             "geprueft": sum(1 for u in punkte if u["termine"]),
                             "sicher": sum(1 for u in punkte if u["stufe"] in ("knospe", "bluete"))})
    return bereiche


@bp.get("/")
def index():
    con = db()
    if not con.execute("SELECT 1 FROM pruefung LIMIT 1").fetchone():
        return render_template("bunseki/index.html", leer=True)
    nutzung = ki_nutzung(con)
    return render_template(
        "bunseki/index.html", leer=False, inventar=(inv := inventar(con)), matrix=matrix(inv), heatmap=heatmap(con),
        top=_statistik(con, "teilaufgaben > 0", "punkte DESC, name")[:10], katalog=katalog(con),
        themen_gesamt=con.execute("SELECT COUNT(*) FROM v_themen_statistik WHERE ebene > 1 AND teilaufgaben > 0").fetchone()[0],
        dauerbrenner=dauerbrenner(con), lange_nicht_dran=lange_nicht_dran(con), nie_geprueft=nie_geprueft(con),
        ohne_thema=ohne_thema(con), kontrolle=kontrolle(con), themenwahl=themenwahl(con),
        ki_nutzung=nutzung, ki_summe={k: sum(z[k] or 0 for z in nutzung) for k in ("aufrufe", "aus_cache", "tokens_ein", "tokens_aus")},
        termin_name=lambda i: termin_name(i, einstellung(con, "teil") == "AP1"), grenzen={"dauerbrenner": DAUERBRENNER, "lange": LANGE_NICHT_DRAN, "kontrolle": KONTROLLE})


@bp.post("/zuordnung/<int:teilaufgabe_id>")
def zuordnung(teilaufgabe_id):
    """Korrigiert die Themenzuordnung einer Teilaufgabe; manuelle Zuordnungen überschreibt die Pipeline nie."""
    con = db()
    thema = con.execute("SELECT id, name FROM thema WHERE id = ? AND ebene > 1", (request.form.get("thema", type=int),)).fetchone()
    if thema is None or not con.execute("SELECT 1 FROM teilaufgabe WHERE id = ?", (teilaufgabe_id,)).fetchone():
        abort(400)
    con.execute("DELETE FROM teilaufgabe_thema WHERE teilaufgabe_id = ?", (teilaufgabe_id,))
    con.execute("INSERT INTO teilaufgabe_thema (teilaufgabe_id, thema_id, gewicht, quelle, sicherheit) "
                "VALUES (?, ?, 1.0, 'manuell', 1.0)", (teilaufgabe_id, thema["id"]))
    con.commit()
    return render_template("bunseki/_gespeichert.html", thema=thema)
