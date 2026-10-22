"""Keiko 稽古: der Fokusmodus. Aufgabe lesen, Lösung aufdecken, sich selbst bewerten."""

import time

from flask import Blueprint, abort, make_response, render_template, request, url_for

from saku.lernen import antwort, karten, tagesziel
from saku.web import db

bp = Blueprint("keiko", __name__, url_prefix="/keiko")

MODI = {"fehler": "Fehlerkorb", "markiert": "Markiert", "neu": "Neue Teilaufgaben"}
LEER = {
    "fehler": "Der Fehlerkorb ist leer. Gerade wackelt nichts.",
    "markiert": "Noch nichts markiert. Mit M merkst du dir eine Teilaufgabe.",
    "neu": "Keine neuen Teilaufgaben mehr: Du hast alle schon einmal bearbeitet.",
    "thema": "Zu diesem Thema gibt es keine Teilaufgaben.",
    None: "Für heute steht nichts an.",
}


def _zahlen(werte) -> list[int]:
    return [int(x) for w in werte for x in str(w).replace(",", " ").split() if x.isdigit()]


def _zustand() -> dict:
    """Filter und Runde aus Adresse oder Formular; die Runde merkt sich, was schon dran war."""
    modus = request.values.get("modus")
    return {
        "modus": modus if modus in MODI else None,
        "themen": _zahlen(request.values.getlist("thema")),
        "muster": (_zahlen(request.values.getlist("muster")) or [None])[0],
        "runde": _zahlen(request.values.getlist("runde")),
    }


def varianten(con, runde: list[int]) -> list[int]:
    """Nach „nicht gewusst“ heute: ähnliche Teilaufgaben aus anderen Jahrgängen, die noch nicht sitzen."""
    falsch = [z[0] for z in con.execute(
        f"SELECT teilaufgabe_id FROM bewertung WHERE teilaufgabe_id IN ({','.join('?' * len(runde))}) "
        "AND date(zeitpunkt, 'localtime') = date('now', 'localtime') GROUP BY teilaufgabe_id "
        "HAVING MAX(id) = MAX(CASE WHEN ergebnis = 1 THEN id END)", runde)] if runde else []
    if not falsch:
        return []
    return list(dict.fromkeys(z[0] for z in con.execute(
        f"SELECT a.aehnlich_id FROM aehnlichkeit a JOIN v_teilaufgabe v ON v.teilaufgabe_id = a.aehnlich_id "
        f"WHERE a.teilaufgabe_id IN ({','.join('?' * len(falsch))}) AND v.status <> 'gruen' ORDER BY a.wert DESC", falsch)))


def schlange(con, zustand: dict, ziel: dict) -> list[int]:
    """Die noch offenen Teilaufgaben der Runde in Reihenfolge."""
    ohne = set(zustand["runde"])
    if not zustand["modus"] and not zustand["themen"] and not zustand["muster"]:
        ids = [] if ziel["erreicht"] else tagesziel.runde(con, ohne, ziel)
        # eine ähnliche Aufgabe zwei Karten später: dieselbe Idee aus einem anderen Jahrgang
        neu = [i for i in varianten(con, zustand["runde"]) if i not in ohne and i not in ids][:1]
        return ids[:2] + neu + ids[2:]
    bedingungen, werte = [], []
    if zustand["muster"]:
        bedingungen.append("v.teilaufgabe_id IN (SELECT id FROM teilaufgabe WHERE muster_id = ?)")
        werte.append(zustand["muster"])
    if zustand["modus"]:
        bedingungen.append({"fehler": "v.status = 'rot'", "markiert": "k.markiert = 1", "neu": "v.status = 'neu'"}[zustand["modus"]])
    if zustand["themen"]:
        bedingungen.append(f"v.teilaufgabe_id IN (SELECT teilaufgabe_id FROM v_zuordnung "
                           f"WHERE thema_id IN ({','.join('?' * len(zustand['themen']))}))")
        werte += zustand["themen"]
    # Freies Üben: erst, was wackelt, dann im Aufbau, dann Neues, zuletzt Sicheres
    ids = [z[0] for z in con.execute(
        "SELECT v.teilaufgabe_id FROM v_teilaufgabe v LEFT JOIN karte k ON k.teilaufgabe_id = v.teilaufgabe_id "
        f"WHERE {' AND '.join(bedingungen)} "
        "ORDER BY CASE v.status WHEN 'rot' THEN 0 WHEN 'gelb' THEN 1 WHEN 'neu' THEN 2 ELSE 3 END, "
        "v.termin_index DESC, v.aufgabe_nr, v.kennung", werte)]
    return [i for i in ids if i not in ohne]


def _rundenname(con, zustand: dict) -> str:
    if zustand["modus"]:
        return MODI[zustand["modus"]]
    if zustand["muster"]:
        name = con.execute("SELECT name FROM muster WHERE id = ?", (zustand["muster"],)).fetchone()
        return f"Muster: {name[0]}" if name else "Muster"
    if zustand["themen"]:
        namen = con.execute(f"SELECT name FROM thema WHERE id IN ({','.join('?' * len(zustand['themen']))}) ORDER BY ebene, position",
                            zustand["themen"]).fetchall()
        return " · ".join(n[0] for n in namen) or "Thema"
    return "Weiterlernen"


def _kontext(con, zustand: dict, erste: int | None = None, sicher_geworden: bool = False) -> dict:
    """Alles für die nächste Karte, oder für den Abschluss, wenn die Runde fertig ist."""
    ziel = tagesziel.tagesziel(con)
    ids = schlange(con, zustand, ziel)
    if erste:
        ids = [erste] + [i for i in ids if i != erste]
    tagesrunde = not zustand["modus"] and not zustand["themen"] and not zustand["muster"]
    if tagesrunde:
        erledigt, gesamt = ziel["erledigt"], max(ziel["ziel"], ziel["erledigt"])
    else:
        erledigt, gesamt = len(zustand["runde"]), len(zustand["runde"]) + len(ids)
    kontext = {
        "zustand": zustand, "ziel": ziel, "erledigt": erledigt, "gesamt": gesamt, "tagesrunde": tagesrunde,
        "rundenname": _rundenname(con, zustand), "sicher_geworden": sicher_geworden,
        "katalog_leer": not con.execute("SELECT 1 FROM teilaufgabe LIMIT 1").fetchone(),
    }
    karte = karten.lade(con, ids[:1])
    if not karte:
        return kontext | {"karte": None, **_abschluss(con, zustand, ziel, tagesrunde)}
    t = karte[0]
    thema = con.execute(
        "SELECT th.name, el.name AS eltern FROM teilaufgabe_thema tt JOIN thema th ON th.id = tt.thema_id "
        "LEFT JOIN thema el ON el.id = th.eltern_id AND el.ebene > 1 "
        "WHERE tt.teilaufgabe_id = ? ORDER BY tt.gewicht DESC LIMIT 1", (t["id"],)).fetchone()
    aehnlich = con.execute(
        "SELECT v.teilaufgabe_id, v.termin, v.aufgabe_nr, v.kennung FROM aehnlichkeit a "
        "JOIN v_teilaufgabe v ON v.teilaufgabe_id = a.aehnlich_id WHERE a.teilaufgabe_id = ? "
        "ORDER BY a.wert DESC LIMIT 3", (t["id"],)).fetchall()
    muster = con.execute(
        "SELECT m.id, m.name, COUNT(*) AS n, COUNT(DISTINCT v.pruefung_id) AS pruefungen, MAX(v.termin_index) AS zuletzt "
        "FROM teilaufgabe t JOIN muster m ON m.id = t.muster_id JOIN teilaufgabe x ON x.muster_id = m.id "
        "JOIN v_teilaufgabe v ON v.teilaufgabe_id = x.id WHERE t.id = ? GROUP BY m.id", (t["id"],)).fetchone()
    return kontext | {
        "karte": t, "start": int(time.time()), "aehnlich": aehnlich, "muster": muster,
        "ist_variante": tagesrunde and t["id"] in varianten(con, zustand["runde"]),
        "thema_pfad": [n for n in (thema["eltern"], thema["name"]) if n] if thema else [],
    }


def _abschluss(con, zustand: dict, ziel: dict, tagesrunde: bool) -> dict:
    if tagesrunde and ziel["erreicht"] and ziel["erledigt"]:
        art = "tagesziel"
    else:
        art = "runde" if zustand["runde"] else "leer"
    ids = tagesziel.heute_sicher(con)
    sicher = con.execute(
        f"SELECT teilaufgabe_id, termin, aufgabe_nr, kennung FROM v_teilaufgabe WHERE teilaufgabe_id IN ({','.join('?' * len(ids))}) "
        "ORDER BY termin_index DESC, aufgabe_nr, kennung", ids).fetchall()
    zahlen = con.execute("SELECT SUM(status = 'rot'), SUM(markiert = 1) FROM karte WHERE teilaufgabe_id IN (SELECT teilaufgabe_id FROM v_teilaufgabe)").fetchone()
    return {
        "art": art, "sicher_heute": sicher, "lernserie": tagesziel.lernserie(con),
        "leer_text": LEER["thema" if zustand["themen"] and not zustand["modus"] else zustand["modus"]],
        "rot": zahlen[0] or 0, "markiert": zahlen[1] or 0,
        "neu": con.execute("SELECT COUNT(*) FROM v_teilaufgabe WHERE status = 'neu'").fetchone()[0],
    }


def _naechste_karte(con, zustand: dict, sicher_geworden: bool = False):
    kontext = _kontext(con, zustand, sicher_geworden=sicher_geworden)
    if kontext["karte"] is None and kontext["art"] == "tagesziel":
        # Die Tagesrunde ist fertig: die ganze Abschlussseite laden (お疲れ様)
        antwort = make_response("")
        antwort.headers["HX-Redirect"] = url_for("keiko.index")
        return antwort
    return render_template("keiko/_karte.html", **kontext)


def _teilaufgabe_oder_404(con, t_id: int) -> dict:
    karte = karten.lade(con, [t_id])
    if not karte:
        abort(404)
    return karte[0]


@bp.get("/")
def index():
    con = db()
    erste = request.args.get("teilaufgabe", type=int)
    if erste and not karten.lade(con, [erste]):
        abort(404)
    return render_template("keiko/index.html", **_kontext(con, _zustand(), erste))


@bp.get("/<int:t_id>/loesung")
def loesung(t_id):
    # mit eigener Antwort holt sich die Lösung gleich den Bewertungsvorschlag von Sensei
    return render_template("keiko/_loesung.html", karte=_teilaufgabe_oder_404(db(), t_id),
                           antwort=request.args.get("antwort", "").strip(), zeichnung=request.args.get("zeichnung_da") == "1")


@bp.post("/<int:t_id>/pruefen")
def pruefen(t_id):
    """Anklickbare Aufgaben sofort prüfen; die Bewertung schlägt Saku vor, ↵ übernimmt sie."""
    karte = _teilaufgabe_oder_404(db(), t_id)
    if not antwort.pruefbar(karte["antwort"]):
        abort(400)
    form = request.form
    eingabe = {"wahl": form.getlist("wahl"), "zahl": form.get("zahl", ""),
               "position": {k.removeprefix("position-"): v for k, v in form.items() if k.startswith("position-")},
               "ziel": {k.removeprefix("ziel-"): v for k, v in form.items() if k.startswith("ziel-")}}
    ergebnis, werte = antwort.auswerten(karte["antwort"], eingabe)
    zusammenfassung = ", ".join(eingabe["wahl"]) or eingabe["zahl"] or ", ".join(
        f"{k}={v}" for k, v in (eingabe["position"] | eingabe["ziel"]).items() if v)
    return render_template("keiko/_pruefung.html", karte=karte, ergebnis=ergebnis, werte=werte, eingabe=eingabe,
                           zusammenfassung=f"Gewählt: {zusammenfassung}" if zusammenfassung else "")


@bp.post("/<int:t_id>/bewerten")
def bewerten(t_id):
    con = db()
    karte = _teilaufgabe_oder_404(con, t_id)
    ergebnis = request.form.get("ergebnis", type=int)
    punkte = request.form.get("punkte", type=float)
    if punkte is not None:  # Punkte gehen vor: daraus folgt Rot, Gelb oder Grün
        punkte = max(0.0, min(punkte, karte["punkte"] or punkte))
        ergebnis = karten.ergebnis_aus_punkten(punkte, karte["punkte"] or punkte) if karte["punkte"] else ergebnis
    if ergebnis not in (1, 2, 3):
        abort(400)
    start = request.form.get("start", type=int)
    dauer = min(max(int(time.time()) - start, 0), 3600) if start else None
    alt, neu = karten.bewerten(con, t_id, ergebnis, dauer_s=dauer, antwort=request.form.get("antwort", "").strip(),
                               punkte=punkte, quelle="sensei" if request.form.get("quelle") == "sensei" else "selbst")
    zustand = _zustand()
    zustand["runde"].append(t_id)
    return _naechste_karte(con, zustand, sicher_geworden=neu == "gruen" and alt != "gruen")


@bp.post("/<int:t_id>/ueberspringen")
def ueberspringen(t_id):
    zustand = _zustand()
    zustand["runde"].append(t_id)
    return _naechste_karte(db(), zustand)


@bp.get("/grundwissen")
def grundwissen():
    """Begriffs-Karten: Begriff lesen, Definition aufdecken, 1/2/3 bewerten."""
    return render_template("keiko/grundwissen.html", **karten.begriffe(db(), []), runde=[])


@bp.post("/grundwissen/<int:begriff_id>/bewerten")
def grundwissen_bewerten(begriff_id):
    con = db()
    ergebnis = request.form.get("ergebnis", type=int)
    if ergebnis not in (1, 2, 3) or not con.execute("SELECT 1 FROM begriff WHERE id = ?", (begriff_id,)).fetchone():
        abort(400)
    karten.begriff_bewerten(con, begriff_id, ergebnis)
    runde = _zahlen(request.form.get("runde", "").split(",")) + [begriff_id]
    return render_template("keiko/_begriff.html", **karten.begriffe(con, runde), runde=runde)


@bp.post("/<int:t_id>/markieren")
def markieren(t_id):
    con = db()
    _teilaufgabe_oder_404(con, t_id)
    return render_template("keiko/_markieren.html", t_id=t_id, markiert=karten.markieren(con, t_id))
