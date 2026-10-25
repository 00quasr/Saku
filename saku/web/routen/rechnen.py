"""Rechnen 算: generierte Rechenaufgaben wie in der AP1. ↵ prüft sofort, der Rechenweg erklärt, ↵ holt die nächste."""

import json
import random
import time
from datetime import datetime, timezone

from flask import Blueprint, abort, make_response, redirect, render_template, request, url_for

from saku.db import einstellung
from saku.lernen import probepruefung, rechnen, simulation, sql
from saku.lernen.rechnen import pseudocode
from saku.web import db, ganzzahl, ist_fragment, seite_oder_fragment

bp = Blueprint("rechnen", __name__, url_prefix="/rechnen")

SEEDS = 10 ** 6
# Rechen-Sprint: so viele Aufgaben, so viele Minuten, so viele Punkte je Aufgabe (5 · 20 = 100 wie in der Prüfung)
SPRINT_AUFGABEN, SPRINT_MINUTEN, SPRINT_PUNKTE = 5, 15, 20


def stand(con) -> dict[str, dict]:
    """Je Art: wie viele Aufgaben gerechnet, die letzten zehn Ergebnisse (älteste zuerst, 1 = richtig) und wann zuletzt (UTC)."""
    stand = {a: {"anzahl": 0, "letzte": [], "zuletzt": None} for a in rechnen.ARTEN}
    for art, anzahl, zuletzt in con.execute("SELECT art, COUNT(*), MAX(zeitpunkt) FROM rechenuebung GROUP BY art"):
        if art in stand:
            stand[art] |= {"anzahl": anzahl, "zuletzt": datetime.fromisoformat(zuletzt)}
    for art, richtig in con.execute(
            "SELECT art, richtig FROM (SELECT id, art, richtig, ROW_NUMBER() OVER (PARTITION BY art ORDER BY id DESC) AS nr "
            "FROM rechenuebung) WHERE nr <= 10 ORDER BY id"):
        if art in stand:
            stand[art]["letzte"].append(richtig)
    return stand


def heute_gerechnet(con) -> tuple[int, int]:
    """(Aufgaben, davon richtig) seit heute früh, Ortszeit."""
    return tuple(con.execute("SELECT COUNT(*), COALESCE(SUM(richtig), 0) FROM rechenuebung "
                             "WHERE date(zeitpunkt, 'localtime') = date('now', 'localtime')").fetchone())


def tagesziel(con) -> int:
    """Rechenaufgaben am Tag aus den Einstellungen; 0 = aus. Das Tagesziel der Teilaufgaben bleibt davon unberührt."""
    return int(einstellung(con, "rechnen_ziel", "5") or 5)


def in_pruefungen(con) -> dict[str, dict]:
    """Je Rechenart die Teilaufgaben im Umfang, deren Themen zu ihr passen (rechnen.passende, umgekehrt): wie viele, zuletzt
    in welchem Termin und die Themen für „üben“. Eine Abfrage für alle Arten; Arten ohne solche Teilaufgaben fehlen."""
    je_thema, namen = {}, {}
    for t_id, name, teilaufgabe, index, termin in con.execute(
            "SELECT z.thema_id, th.name, v.teilaufgabe_id, v.termin_index, v.termin FROM v_zuordnung z "
            "JOIN thema th ON th.id = z.thema_id JOIN v_teilaufgabe v ON v.teilaufgabe_id = z.teilaufgabe_id"):
        je_thema.setdefault(t_id, []).append((index, termin, teilaufgabe))
        namen[t_id] = name
    raus = {}
    for art, themen in rechnen.themen_je_art(namen.items()).items():
        teile = [x for t in themen for x in je_thema[t]]
        raus[art] = {"themen": themen, "anzahl": len({x[2] for x in teile}), "zuletzt": max(teile)[1]}
    return raus


def _gruppen() -> list[tuple[str, list]]:
    """(Gruppe, Arten) in der Reihenfolge der Übersicht, leere Gruppen fallen weg."""
    gruppen = [(g, [a for a in rechnen.ARTEN.values() if a.gruppe == g]) for g in rechnen.GRUPPEN]
    return [(g, arten) for g, arten in gruppen if arten]


def _art_oder_404(art: str) -> rechnen.Art:
    if art not in rechnen.ARTEN:
        abort(404)
    return rechnen.ARTEN[art]


def _kontext(art: str, seed: int, gemischt: bool, eingaben: dict | None = None, werte: dict | None = None,
             aufgegeben: bool = False) -> dict:
    naechste = url_for("rechnen.gemischt") if gemischt else url_for("rechnen.aufgabe", art=art, seed=random.randrange(SEEDS))
    return {"art": rechnen.ARTEN[art], "aufgabe": rechnen.erzeugen(art, seed), "seed": seed, "gemischt": gemischt,
            "start": int(time.time()), "eingaben": eingaben or {}, "werte": werte, "aufgegeben": aufgegeben,
            "naechste": naechste, "stand": stand(db())[art],
            "in_pruefungen": in_pruefungen(db()).get(art) if werte is not None else None}  # erst nach dem Prüfen zu sehen


@bp.get("/")
def index():
    con = db()
    return render_template("rechnen/index.html", gruppen=_gruppen(), stand=stand(con), heute=heute_gerechnet(con),
                           ziel=tagesziel(con), faellige_arten=faellige(con),  # „faellig“ ist schon die Zahl in der Seitenleiste
                           in_pruefungen=in_pruefungen(con))


@bp.get("/formeln")
def formeln():
    """Formelsammlung aller Arten, gruppiert wie die Übersicht; druckbar als Spickzettel."""
    return render_template("rechnen/formeln.html", gruppen=_gruppen())


def _quoten(con) -> dict[str, float]:
    return {a: sum(s["letzte"]) / len(s["letzte"]) for a, s in stand(con).items() if s["letzte"]}


def _pfad(con) -> str:
    return con.execute("SELECT pfad FROM v_umfang").fetchone()[0]


def faellige(con) -> list[str]:
    """Fällige Arten im Umfang des aktiven Lernpfads (siehe rechnen.plan)."""
    s = stand(con)
    arten = rechnen.im_umfang(_pfad(con))
    jetzt = datetime.now(timezone.utc).replace(tzinfo=None)  # rechenuebung.zeitpunkt ist UTC ohne Zone
    return rechnen.faellig(arten, {a: x["letzte"] for a, x in s.items()}, {a: x["zuletzt"] for a, x in s.items()}, jetzt)


@bp.get("/gemischt")
def gemischt():
    """Bevorzugt eine fällige Art des Lernpfads, sonst eine aus dem Umfang; nach Gewicht: was zuletzt oft falsch war, kommt häufiger."""
    con = db()
    auswahl = faellige(con) or rechnen.im_umfang(_pfad(con))
    art = rechnen.gemischt(random.Random(), _quoten(con), ohne=[a for a in rechnen.ARTEN if a not in auswahl])
    return redirect(url_for("rechnen.aufgabe", art=art, seed=random.randrange(SEEDS), gemischt=1))


@bp.get("/sprint")
def sprint():
    """Startseite des Sprints: was kommt, wie lange, wie bewertet wird."""
    return render_template("rechnen/sprint.html", aufgaben=None, anzahl=SPRINT_AUFGABEN, minuten=SPRINT_MINUTEN, punkte=SPRINT_PUNKTE)


@bp.get("/sprint/neu")
def sprint_neu():
    """Fünf verschiedene Arten aus dem Umfang des Lernpfads, gewichtet wie „Gemischt üben“; Arten, Seeds und Startzeit stehen
    in der Adresse."""
    con = db()
    rng, arten, quoten = random.Random(), [], _quoten(con)
    ausserhalb = [a for a in rechnen.ARTEN if a not in rechnen.im_umfang(_pfad(con)) or not rechnen.ARTEN[a].sprint]
    for _ in range(SPRINT_AUFGABEN):
        arten.append(rechnen.gemischt(rng, quoten, ohne=arten + ausserhalb))
    return redirect(url_for("rechnen.sprint_lauf", a=[f"{art}:{rng.randrange(SEEDS)}" for art in arten], start=int(time.time())))


def _sprint_aufgaben() -> list[tuple]:
    """(Art, Seed, Aufgabe) aus a=art:seed; keine Datenbank nötig, die Aufgaben entstehen aus den Seeds neu."""
    paare = []
    for wert in request.values.getlist("a")[:SPRINT_AUFGABEN]:
        art, _, seed = wert.partition(":")
        if art not in rechnen.ARTEN or (seed := ganzzahl(seed)) is None:
            abort(400)
        paare.append((rechnen.ARTEN[art], seed, rechnen.erzeugen(art, seed)))
    if not paare:
        abort(400)
    return paare


@bp.route("/sprint/lauf", methods=["GET", "POST"])
def sprint_lauf():
    """GET: alle Aufgaben mit Timer; POST (Abgabe oder Zeit um): Punkte je Aufgabe anteilig nach Feldern, Note, Rechenwege."""
    if request.method == "GET" and not request.args.getlist("a"):  # Lesezeichen oder Zurück ohne Aufgaben
        return redirect(url_for("rechnen.sprint"))
    aufgaben = _sprint_aufgaben()
    start = request.values.get("start", type=int) or int(time.time())
    kontext = {"aufgaben": aufgaben, "start": start, "ende": start + SPRINT_MINUTEN * 60, "minuten": SPRINT_MINUTEN,
               "punkte": SPRINT_PUNKTE, "eingaben": [{} for _ in aufgaben], "werte": None}
    if request.method == "GET":
        return render_template("rechnen/sprint.html", **kontext)
    eingaben = [{f.name: request.form.get(f"a{i}-{f.name}", "")[:200] for f in a.felder}
                for i, (_, _, a) in enumerate(aufgaben, start=1)]
    werte = [probepruefung.bewerten(a, e) for (_, _, a), e in zip(aufgaben, eingaben)]
    punkte = [probepruefung.anteil(SPRINT_PUNKTE, w) for w in werte]
    dauer = min(max(int(time.time()) - start, 0), 3 * 3600)
    con = db()
    # Neu laden schickt das Formular noch einmal: dieselben Aufgaben seit dem Start nicht doppelt speichern
    schon = con.execute(f"SELECT COUNT(*) FROM rechenuebung WHERE zeitpunkt >= datetime(?, 'unixepoch') "
                        f"AND art || ':' || seed IN ({','.join('?' * len(aufgaben))})",
                        [start, *(f"{art.slug}:{seed}" for art, seed, _ in aufgaben)]).fetchone()[0]
    if not schon:
        con.executemany("INSERT INTO rechenuebung (art, seed, richtig, felder_richtig, felder_gesamt, dauer_s) VALUES (?, ?, ?, ?, ?, ?)",
                        [(art.slug, seed, int(all(w.values())), sum(w.values()), len(w), dauer // len(aufgaben))
                         for (art, seed, _), w in zip(aufgaben, werte)])
        con.commit()
    erreicht, moeglich = sum(punkte), SPRINT_PUNKTE * len(aufgaben)
    hundert = simulation.umrechnen(erreicht, moeglich)
    note = simulation.note(hundert)
    return render_template("rechnen/sprint.html", **kontext | {
        "eingaben": eingaben, "werte": werte, "punkte_je": punkte, "erreicht": erreicht, "moeglich": moeglich, "hundert": hundert,
        "note": note, "note_text": simulation.NOTEN[note], "bestanden": hundert >= simulation.BESTANDEN_AB, "dauer": dauer})


# --- Probeprüfung aus den Generatoren: wie die Simulation, aber unbegrenzt neu und sofort ausgewertet -------------------

def _probe_oder_404(con, pp_id: int):
    zeile = con.execute("SELECT * FROM probepruefung WHERE id = ?", (pp_id,)).fetchone()
    if zeile is None or not (aufgaben := json.loads(zeile["aufgaben"])) or any(art not in rechnen.ARTEN for art, *_ in aufgaben):
        abort(404)  # eine Art, die es nicht mehr gibt, ergäbe eine andere Prüfung
    return zeile


def _probe_eingaben(zeile) -> dict[str, str]:
    """Formularfelder a1-feld, a2-feld … aus der Abgabe oder dem Zwischenspeichern."""
    return {f"a{i}-{f.name}": request.form.get(f"a{i}-{f.name}", "")[:sql.ZEICHEN if f.typ in ("sql", "code") else 200]
            for i, x in enumerate(probepruefung.aufgaben(zeile), start=1) for f in x["aufgabe"].felder}


@bp.get("/probe")
def probe():
    """Startseite: wie die Prüfung aufgebaut ist, die laufende und der Verlauf mit Punkten und Note."""
    con = db()
    verlauf = con.execute("SELECT *, strftime('%d.%m.%Y', gestartet_am, 'localtime') AS datum FROM probepruefung "
                          "ORDER BY gestartet_am DESC, id DESC").fetchall()
    return render_template("rechnen/probe.html", aufgaben=None, verlauf=verlauf, laufend=probepruefung.laufende(con),
                           pfad=_pfad(con), anzahl=probepruefung.ANZAHL, minuten=probepruefung.MINUTEN, noten=simulation.NOTEN)


@bp.post("/probe/neu")
def probe_neu():
    con = db()
    laufend = probepruefung.laufende(con)
    pp_id = laufend["id"] if laufend else probepruefung.anlegen(con, _pfad(con), _quoten(con))
    return redirect(url_for("rechnen.probe_heft", pp_id=pp_id))


@bp.get("/probe/<int:pp_id>")
def probe_heft(pp_id):
    """Das Heft mit Restzeit; nach der Abgabe dasselbe Heft mit Punkten je Aufgabe, Note und Lösungswegen."""
    con = db()
    zeile = _probe_oder_404(con, pp_id)
    rest, gebraucht = con.execute(
        "SELECT CAST((julianday(gestartet_am, '+' || dauer_min || ' minutes') - julianday('now')) * 86400 AS INTEGER), "
        "CAST((julianday(beendet_am) - julianday(gestartet_am)) * 86400 AS INTEGER) FROM probepruefung WHERE id = ?", (pp_id,)).fetchone()
    fertig = zeile["note"] is not None
    return render_template("rechnen/probe.html", zeile=zeile, aufgaben=probepruefung.aufgaben(zeile), fertig=fertig, rest=max(0, rest),
                           gebraucht=min(gebraucht or 0, zeile["dauer_min"] * 60), note_text=simulation.NOTEN.get(zeile["note"]),
                           bestanden=fertig and zeile["punkte"] >= simulation.BESTANDEN_AB)


@bp.post("/probe/<int:pp_id>/speichern")
def probe_speichern(pp_id):
    con = db()
    zeile = _probe_oder_404(con, pp_id)
    if zeile["beendet_am"]:
        return "Schon abgegeben"
    probepruefung.speichern(con, pp_id, _probe_eingaben(zeile))
    return f"Gespeichert um {datetime.now():%H:%M}"


@bp.post("/probe/<int:pp_id>/abgeben")
def probe_abgeben(pp_id):
    """Abgabe oder Zeit um: die letzten Antworten speichern, dann einmal auswerten."""
    con = db()
    zeile = _probe_oder_404(con, pp_id)
    if not zeile["beendet_am"]:  # neu laden nach der Abgabe zeigt nur die Auswertung
        probepruefung.speichern(con, pp_id, _probe_eingaben(zeile))
        probepruefung.auswerten(con, pp_id)
    return redirect(url_for("rechnen.probe_heft", pp_id=pp_id))


@bp.get("/<art>")
def aufgabe(art):
    _art_oder_404(art)
    gemischt = request.args.get("gemischt") == "1"
    seed = request.args.get("seed", type=int)
    if seed is None:  # jede Aufgabe hat eine feste Adresse: derselbe Seed, dieselbe Aufgabe
        return redirect(url_for("rechnen.aufgabe", art=art, seed=random.randrange(SEEDS), gemischt=1 if gemischt else None))
    antwort = make_response(seite_oder_fragment("rechnen/aufgabe.html", "rechnen/_karte.html", **_kontext(art, seed, gemischt)))
    if ist_fragment():  # „Nächste Aufgabe“ tauscht nur die Karte, die Adresse zieht mit
        antwort.headers["HX-Push-Url"] = url_for("rechnen.aufgabe", art=art, seed=seed, gemischt=1 if gemischt else None)
    return antwort


@bp.post("/<art>/pruefen")
def pruefen(art):
    """Prüft alle Felder und speichert den Versuch; „Rechenweg zeigen“ (aufgeben=1) zählt als nicht gelöst."""
    _art_oder_404(art)
    seed = request.form.get("seed", type=int)
    if seed is None:
        abort(400)
    aufgabe = rechnen.erzeugen(art, seed)
    eingaben = {f.name: request.form.get(f"feld-{f.name}", "")[:sql.ZEICHEN if f.typ in ("sql", "code") else 200] for f in aufgabe.felder}
    aufgegeben = request.form.get("aufgeben") == "1"
    gemischt = request.form.get("gemischt") == "1"
    start = request.form.get("start", type=int)
    if not aufgegeben and not any(e.strip() for e in eingaben.values()):  # ↵ zu früh oder doppelt: nichts speichern
        return render_template("rechnen/_karte.html", **_kontext(art, seed, gemischt) | {"start": start or int(time.time()), "leer": True})
    vergleich = None
    if aufgabe.sandbox:  # SQL: was abweicht; beim Aufgeben das Ergebnis der Musterlösung
        feld = aufgabe.felder[0]
        if aufgegeben:
            vergleich = {"muster": sql.ausfuehren(*aufgabe.sandbox, feld.loesung)["tabellen"]}
        elif "fehler" in (vergleich := rechnen.sql_vergleich(aufgabe, eingaben[feld.name])):
            # läuft nicht: keine Bewertung, nichts gespeichert, die Anweisung bleibt zum Korrigieren stehen
            return render_template("rechnen/_karte.html", **_kontext(art, seed, gemischt, eingaben)
                                   | {"start": start or int(time.time()), "sql_fehler": vergleich["fehler"]})
    elif aufgabe.testfaelle and not aufgegeben:  # Pseudocode: je Testfall erwartet und erhalten
        if "fehler" in (vergleich := rechnen.code_vergleich(aufgabe, eingaben[aufgabe.felder[0].name])):
            # lässt sich nicht lesen: wie bei SQL keine Bewertung, der Code bleibt zum Korrigieren stehen
            return render_template("rechnen/_karte.html", **_kontext(art, seed, gemischt, eingaben)
                                   | {"start": start or int(time.time()), "code_fehler": vergleich["fehler"]})
    # SQL und Pseudocode haben ein Feld und sind schon verglichen: nicht noch einmal ausführen
    werte = ({aufgabe.felder[0].name: vergleich["ergebnis"] == 3} if vergleich and "ergebnis" in vergleich
             else rechnen.pruefen(aufgabe, eingaben))
    dauer = min(max(int(time.time()) - start, 0), 3600) if start else None
    con = db()
    con.execute("INSERT INTO rechenuebung (art, seed, richtig, felder_richtig, felder_gesamt, dauer_s) VALUES (?, ?, ?, ?, ?, ?)",
                (art, seed, int(not aufgegeben and all(werte.values())), sum(werte.values()), len(werte), dauer))
    con.commit()
    return render_template("rechnen/_karte.html", **_kontext(art, seed, gemischt, eingaben, werte, aufgegeben), vergleich=vergleich)


def _aufgabe_mit_oder_404(art: str, seed: int | None, merkmal: str) -> rechnen.Aufgabe:
    """Die Aufgabe, wenn sie das Merkmal hat (sandbox: SQL, testfaelle: Pseudocode)."""
    _art_oder_404(art)
    if seed is None:
        abort(400)
    aufgabe = rechnen.erzeugen(art, seed)
    return aufgabe if getattr(aufgabe, merkmal) else abort(404)


@bp.post("/<art>/sql")
def sql_ausfuehren(art):
    """SQL-Aufgabe: die eigene Anweisung in der Sandbox ausführen, wie in Üben (Ergebnis oder die Meldung von SQLite)."""
    aufgabe = _aufgabe_mit_oder_404(art, request.form.get("seed", type=int), "sandbox")
    try:
        eigene = request.form.get(request.form.get("praefix", "feld-") + aufgabe.felder[0].name, "")
        return render_template("keiko/_sql.html", **sql.ausfuehren(*aufgabe.sandbox, eigene))
    except sql.SqlFehler as fehler:
        return render_template("keiko/_sql.html", fehler=str(fehler))


@bp.get("/<art>/tabellen")
def sql_tabellen(art):
    """Die erfundenen Beispieldaten einer SQL-Aufgabe."""
    aufgabe = _aufgabe_mit_oder_404(art, request.args.get("seed", type=int), "sandbox")
    return render_template("keiko/_sql.html", meldung="Beispieldaten", tabellen=sql.tabellen(*aufgabe.sandbox))


@bp.post("/<art>/code")
def code_ausfuehren(art):
    """Pseudocode-Aufgabe: den eigenen Code mit dem Beispiel der Frage ausführen (Ausgabe oder die Meldung mit Zeilennummer)."""
    aufgabe = _aufgabe_mit_oder_404(art, request.form.get("seed", type=int), "testfaelle")
    faelle, ziel = aufgabe.testfaelle
    eigene = request.form.get(request.form.get("praefix", "feld-") + aufgabe.felder[0].name, "")[:sql.ZEICHEN]
    return render_template("rechnen/_code.html", **pseudocode.ausprobieren(eigene, faelle[0], ziel))
