"""Keiko 稽古: der Fokusmodus. Aufgabe lesen, Lösung aufdecken, sich selbst bewerten."""

import math
import time
from datetime import date, datetime, timezone

from flask import Blueprint, abort, make_response, render_template, request, url_for

from saku.lernen import antwort, karten, rechnen, rueckblick, sql, tagesziel
from saku.web import db, seite_oder_fragment
from saku.web.routen.heute import datum_lang

bp = Blueprint("keiko", __name__, url_prefix="/keiko")

MODI = {"fehler": "Fehlerkorb", "markiert": "Markiert", "neu": "Neue Teilaufgaben"}
LEER = {
    "fehler": "Der Fehlerkorb ist leer. Gerade wackelt nichts.",
    "markiert": "Noch nichts markiert. Mit M merkst du dir eine Teilaufgabe.",
    "neu": "Keine neuen Teilaufgaben mehr: Du hast alle schon einmal bearbeitet.",
    "thema": "Zu diesem Thema gibt es keine Teilaufgaben.",
    None: "Für heute steht nichts an.",
}


def _ortszeit(zeitpunkt: str) -> datetime:
    """Zeitpunkt aus der Datenbank (UTC) in Ortszeit."""
    return datetime.fromisoformat(zeitpunkt).replace(tzinfo=timezone.utc).astimezone()


def tag(zeitpunkt: str, heute: date | None = None) -> str:
    """„heute“, „gestern“ oder „22.10.“"""
    d = _ortszeit(zeitpunkt).date()
    return {0: "heute", 1: "gestern"}.get(((heute or date.today()) - d).days, f"{d.day}.{d.month}.")


def wann(faellig_am: str, jetzt: datetime | None = None) -> str:
    """Wann eine Karte wieder dran ist: „in 10 min“, „heute um 18:30“, „morgen“, „am 3.11.“"""
    jetzt = jetzt or datetime.now().astimezone()
    termin = _ortszeit(faellig_am)
    minuten = math.ceil((termin - jetzt).total_seconds() / 60)
    if minuten < 60:
        return f"in {max(1, minuten)} min"
    tage = (termin.date() - jetzt.date()).days
    if tage == 0:
        return f"heute um {termin:%H:%M}"
    if tage == 1:
        return "morgen"
    return f"am {termin.day}.{termin.month}." + (str(termin.year) if termin.year != jetzt.year else "")


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
        "extra": request.values.get("extra") == "1",  # weiterüben nach geschafftem Tagesziel
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
        if not ziel["erreicht"]:
            ids = tagesziel.runde(con, ohne, ziel)
        elif zustand["extra"]:  # Extra-Runde: noch einmal so viele neue wie das Mindestziel
            ids = tagesziel.runde(con, ohne, ziel, neu=max(0, tagesziel.NEU_MINDESTENS - len(zustand["runde"])))
        else:
            ids = []
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
    return "Extra-Runde" if zustand["extra"] else "Weiterlernen"


def _stand(con, t: dict, zustand: dict, tagesrunde: bool, rundenname: str, geplant: bool) -> dict:
    """Was Saku über die Karte weiß: die letzten Bewertungen, der Weg bis „sicher“ und warum sie jetzt dran ist."""
    karte = con.execute("SELECT serie, faellig_am, faellig_am <= datetime('now') AS faellig FROM karte WHERE teilaufgabe_id = ?",
                        (t["id"],)).fetchone()
    letzte = con.execute("SELECT ergebnis, zeitpunkt FROM bewertung WHERE teilaufgabe_id = ? ORDER BY zeitpunkt DESC, id DESC LIMIT 3",
                         (t["id"],)).fetchall()
    warum = []
    if not geplant:
        warum.append("direkt geöffnet")
    elif t["status"] != "neu" and karte and karte["faellig"]:
        warum.append(f"fällig seit {tag(karte['faellig_am'])} {_ortszeit(karte['faellig_am']):%H:%M}")
    elif t["status"] == "neu" and tagesrunde:
        warum.append("neu in der Extra-Runde" if zustand["extra"] else "neu aus dem Tagesziel")
    if geplant and not tagesrunde:
        warum.append(f"Runde „{rundenname}“")
    if t["markiert"]:
        warum.append("markiert")
    return {
        "art": {"neu": "Neu", "rot": "Fehlerkorb"}.get(t["status"], "Wiederholung"),
        "letzte": [{"ergebnis": z["ergebnis"], "tag": tag(z["zeitpunkt"])} for z in reversed(letzte)],
        "noch": 2 - karte["serie"] if karte and t["status"] in ("rot", "gelb") else 0,
        "warum": warum,
    }


def _eben(con, t_id: int | None) -> dict | None:
    """Rückmeldung zur eben bewerteten Teilaufgabe: wann sie wiederkommt."""
    z = con.execute("SELECT v.termin, v.aufgabe_nr, v.kennung, k.status, k.faellig_am FROM v_teilaufgabe_alle v "
                    "JOIN karte k ON k.teilaufgabe_id = v.teilaufgabe_id WHERE v.teilaufgabe_id = ? AND k.faellig_am IS NOT NULL",
                    (t_id,)).fetchone() if t_id else None
    return dict(z) | {"wann": wann(z["faellig_am"])} if z else None


def _kontext(con, zustand: dict, erste: int | None = None, sicher_geworden: bool = False, eben: int | None = None) -> dict:
    """Alles für die nächste Karte, oder für den Abschluss, wenn die Runde fertig ist."""
    ziel = tagesziel.tagesziel(con)
    ids = schlange(con, zustand, ziel)
    geplant = erste is None or erste in ids  # sonst direkt geöffnet, z. B. aus Suche oder Verlauf
    if erste:
        ids = [erste] + [i for i in ids if i != erste]
    tagesrunde = not zustand["modus"] and not zustand["themen"] and not zustand["muster"]
    if tagesrunde and not (zustand["extra"] and ziel["erreicht"]):
        erledigt, gesamt = ziel["erledigt"], max(ziel["ziel"], ziel["erledigt"])
    else:
        erledigt, gesamt = len(zustand["runde"]), len(zustand["runde"]) + len(ids)
    kontext = {
        "zustand": zustand, "ziel": ziel, "erledigt": erledigt, "gesamt": gesamt, "tagesrunde": tagesrunde,
        "rundenname": _rundenname(con, zustand), "sicher_geworden": sicher_geworden, "eben": _eben(con, eben),
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
    ist_variante = tagesrunde and t["id"] in varianten(con, zustand["runde"])
    stand = _stand(con, t, zustand, tagesrunde, kontext["rundenname"], geplant)
    if ist_variante:  # das sagt schon der Hinweis „Ähnlich wie eben“
        stand["warum"] = []
    themen = [z[0] for z in con.execute(
        "SELECT th.name FROM teilaufgabe_thema tt JOIN thema th ON th.id = tt.thema_id "
        "WHERE tt.teilaufgabe_id = ? ORDER BY tt.gewicht DESC", (t["id"],))]
    return kontext | {
        "karte": t, "start": int(time.time()), "aehnlich": aehnlich, "muster": muster, "ist_variante": ist_variante,
        "rechenart": rechnen.passend(themen),
        "thema_pfad": [n for n in (thema["eltern"], thema["name"]) if n] if thema else [], "stand": stand,
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


def _naechste_karte(con, zustand: dict, sicher_geworden: bool = False, eben: int | None = None):
    kontext = _kontext(con, zustand, sicher_geworden=sicher_geworden, eben=eben)
    if kontext["karte"] is None and kontext["art"] == "tagesziel":
        # Die Tagesrunde ist fertig: die ganze Abschlussseite laden (お疲れ様), mit der Rückmeldung zur letzten Karte
        antwort = make_response("")
        antwort.headers["HX-Redirect"] = url_for("keiko.index", eben=eben)
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
    return render_template("keiko/index.html", **_kontext(con, _zustand(), erste, eben=request.args.get("eben", type=int)))


@bp.get("/<int:t_id>/loesung")
def loesung(t_id):
    # mit eigener Antwort holt sich die Lösung gleich den Bewertungsvorschlag von Sensei
    return render_template("keiko/_loesung.html", karte=_teilaufgabe_oder_404(db(), t_id),
                           antwort=request.args.get("antwort", "").strip(), zeichnung=request.args.get("zeichnung_da") == "1")


@bp.post("/<int:t_id>/pruefen")
def pruefen(t_id):
    """Anklickbare Aufgaben und SQL mit Sandbox sofort prüfen; die Bewertung schlägt Saku vor, ↵ übernimmt sie."""
    con = db()
    karte = _teilaufgabe_oder_404(con, t_id)
    if karte["loesung_sql"] and (sandbox := sql.laden(con, karte["aufgabe_id"])):
        eigene = request.form.get("antwort", "")
        try:
            vergleich = sql.pruefen(*sandbox, karte["loesung_sql"], eigene)
        except sql.SqlFehler as fehler:  # läuft nicht: keine Bewertung, Prüfen bleibt, das Feld auch
            return render_template("keiko/_sql.html", fehler=str(fehler), beim_pruefen=True)
        return render_template("keiko/_pruefung.html", karte=karte, ergebnis=vergleich["ergebnis"], vergleich=vergleich,
                               zusammenfassung=eigene.strip())
    if not antwort.pruefbar(karte["antwort"]):
        abort(400)
    eingabe = antwort.eingabe(request.form)
    ergebnis, werte = antwort.auswerten(karte["antwort"], eingabe)
    return render_template("keiko/_pruefung.html", karte=karte, ergebnis=ergebnis, werte=werte, eingabe=eingabe,
                           zusammenfassung=antwort.zusammenfassung(eingabe))


def _sandbox_oder_404(t_id: int) -> tuple[str, str]:
    con = db()
    return sql.laden(con, _teilaufgabe_oder_404(con, t_id)["aufgabe_id"]) or abort(404)


@bp.post("/<int:t_id>/sql")
def sql_ausfuehren(t_id):
    """SQL in der Sandbox ausführen: Ergebnis als Tabelle oder die Meldung von SQLite."""
    sandbox = _sandbox_oder_404(t_id)
    try:
        return render_template("keiko/_sql.html", **sql.ausfuehren(*sandbox, request.form.get("antwort", "")))
    except sql.SqlFehler as fehler:
        return render_template("keiko/_sql.html", fehler=str(fehler))


@bp.get("/<int:t_id>/tabellen")
def sql_tabellen(t_id):
    """Die erfundenen Beispieldaten der Sandbox."""
    return render_template("keiko/_sql.html", meldung="Beispieldaten", tabellen=sql.tabellen(*_sandbox_oder_404(t_id)))


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
    return _naechste_karte(con, zustand, sicher_geworden=neu == "gruen" and alt != "gruen", eben=t_id)


@bp.post("/zurueck")
def zurueck():
    """Die vorige Karte noch einmal; ihre Bewertung von eben wird zurückgenommen."""
    con = db()
    zustand = _zustand()
    if not zustand["runde"]:
        abort(400)
    vorige = zustand["runde"].pop()
    karten.zuruecknehmen(con, vorige)
    return render_template("keiko/_karte.html", **_kontext(con, zustand, erste=vorige))


@bp.post("/<int:t_id>/ueberspringen")
def ueberspringen(t_id):
    zustand = _zustand()
    zustand["runde"].append(t_id)
    return _naechste_karte(db(), zustand)


QUELLEN = {"selbst": "selbst", "sensei": "Sensei", "simulation": "Simulation", "stationstest": "Mini-Test"}
VERLAUF_SEITE = 100


@bp.get("/verlauf")
def verlauf():
    """Alle Bewertungen nach Tagen, neueste zuerst; Filter nach Ergebnis, ältere seitenweise."""
    con = db()
    ergebnis = request.args.get("ergebnis", type=int)
    ergebnis = ergebnis if ergebnis in (1, 2, 3) else None
    seite = max(0, request.args.get("seite", 0, type=int))
    # v_teilaufgabe_alle: auch was gerade nicht im Umfang ist, gehört zum Verlauf; verlinkt wird nur, was Üben öffnen kann
    zeilen = con.execute(
        "SELECT b.teilaufgabe_id, b.ergebnis, b.punkte, b.quelle, date(b.zeitpunkt, 'localtime') AS tag, "
        "strftime('%H:%M', b.zeitpunkt, 'localtime') AS uhrzeit, v.termin, v.aufgabe_nr, v.kennung, v.bereich, "
        "v.punkte AS maximal, u.teilaufgabe_id IS NOT NULL AS im_umfang "
        "FROM bewertung b JOIN v_teilaufgabe_alle v ON v.teilaufgabe_id = b.teilaufgabe_id "
        "LEFT JOIN v_teilaufgabe u ON u.teilaufgabe_id = b.teilaufgabe_id "
        "WHERE ?1 IS NULL OR b.ergebnis = ?1 ORDER BY b.zeitpunkt DESC, b.id DESC LIMIT ?2 OFFSET ?3",
        (ergebnis, VERLAUF_SEITE + 1, seite * VERLAUF_SEITE)).fetchall()
    weiter, zeilen = len(zeilen) > VERLAUF_SEITE, zeilen[:VERLAUF_SEITE]
    tage = list(dict.fromkeys(z["tag"] for z in zeilen))
    # Tageszusammenfassung immer über alle Bewertungen des Tages, auch wenn ein Filter gesetzt ist
    summen = {z["tag"]: z for z in con.execute(
        f"SELECT date(zeitpunkt, 'localtime') AS tag, COUNT(*) AS n, SUM(ergebnis = 3) AS gewusst, SUM(ergebnis = 2) AS teilweise, "
        f"SUM(ergebnis = 1) AS falsch, COUNT(DISTINCT teilaufgabe_id) AS teilaufgaben, SUM(dauer_s) AS dauer_s "
        f"FROM bewertung WHERE date(zeitpunkt, 'localtime') IN ({','.join('?' * len(tage))}) GROUP BY 1", tage)}
    heute = date.today()
    return render_template(
        "keiko/verlauf.html", ergebnis=ergebnis, seite=seite, weiter=weiter, quellen=QUELLEN, rueckblick=rueckblick.woche(con),
        zahlen=con.execute("SELECT COUNT(*), SUM(ergebnis = 1), SUM(ergebnis = 2), SUM(ergebnis = 3) FROM bewertung").fetchone(),
        tage=[{"name": _tagesname(date.fromisoformat(t), heute), "summe": summen[t], "zeilen": [z for z in zeilen if z["tag"] == t]}
              for t in tage])


def _tagesname(tag_: date, heute: date) -> str:
    """„Heute“, „Gestern“, „Mittwoch, 22. Oktober“, in anderen Jahren mit Jahr."""
    name = {0: "Heute", 1: "Gestern"}.get((heute - tag_).days, datum_lang(tag_))
    return name if tag_.year == heute.year else f"{name} {tag_.year}"


def _begriff_karte(con, runde: list[int], umgekehrt: bool, **kontext) -> dict:
    """Nächste Begriffs-Karte; umgekehrt mit Definition ohne Namen und Begriffen zur Wahl."""
    kontext |= karten.begriffe(con, runde) | {"runde": runde, "umgekehrt": umgekehrt}
    return kontext | (karten.auswahl(con, kontext["karte"]) if umgekehrt and kontext["karte"] else {})


@bp.get("/grundwissen")
def grundwissen():
    """Begriffs-Karten: Begriff lesen, Definition aufdecken, 1/2/3 bewerten; umgekehrt (modus=umgekehrt) die Definition
    lesen und unter vier Begriffen wählen."""
    runde = _zahlen(request.args.get("runde", "").split(","))
    return seite_oder_fragment("keiko/grundwissen.html", "keiko/_begriff.html",
                               **_begriff_karte(db(), runde, request.args.get("modus") == "umgekehrt"))


@bp.post("/grundwissen/<int:begriff_id>/bewerten")
def grundwissen_bewerten(begriff_id):
    """ergebnis 1–3 nach dem Aufdecken, oder umgekehrt wahl: der gewählte Begriff (richtig → 3, falsch → 1)."""
    con = db()
    begriff = con.execute("SELECT id, name FROM begriff WHERE id = ?", (begriff_id,)).fetchone()
    wahl = request.form.get("wahl", type=int)
    ergebnis = (3 if wahl == begriff_id else 1) if wahl is not None else request.form.get("ergebnis", type=int)
    if ergebnis not in (1, 2, 3) or begriff is None:
        abort(400)
    karten.begriff_bewerten(con, begriff_id, ergebnis)
    runde = _zahlen(request.form.get("runde", "").split(",")) + [begriff_id]
    if wahl is None:
        return render_template("keiko/_begriff.html", **_begriff_karte(con, runde, False))
    gewaehlt = con.execute("SELECT name FROM begriff WHERE id = ?", (wahl,)).fetchone()
    rueckmeldung = {"richtig": wahl == begriff_id, "name": begriff["name"], "gewaehlt": gewaehlt[0] if gewaehlt else None}
    return render_template("keiko/_begriff.html", **_begriff_karte(con, runde, True, rueckmeldung=rueckmeldung))


@bp.post("/<int:t_id>/markieren")
def markieren(t_id):
    con = db()
    _teilaufgabe_oder_404(con, t_id)
    return render_template("keiko/_markieren.html", t_id=t_id, markiert=karten.markieren(con, t_id))
